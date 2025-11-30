from typing import AsyncGenerator

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from .agent import graph
from .cache_manager import CacheManager
from .config import get_s3_client, get_settings
from .logging_config import configure_uvicorn_logging, get_app_logger
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
from langchain_core.messages.human import HumanMessage
import os
from .models import PresignedUrlRequest, ChatRequest, DeleteFileRequest

# Initialize centralized logging
logger = get_app_logger()

LANGGRAPH_THREAD_ID = "thread-1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_uvicorn_logging()
    logger.info("FastAPI application started")
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as saver:
        app.state.graph = graph.compile(checkpointer=saver)
        yield
    logger.info("FastAPI application shutdown")


# Initialize FastAPI app
app = FastAPI(
    title="Invoice Chatbot Backend",
    description="AI-powered invoice knowledge graph and chat interface",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_cache_manager() -> CacheManager:
    """Return a new `CacheManager` instance.

    The function is kept small to make testing and future injection easier.
    """
    return CacheManager()


@app.post("/generate-presigned-url/")
async def generate_presigned_url(request: PresignedUrlRequest) -> dict[str, str]:
    try:
        s3_client = get_s3_client()
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.aws_s3_bucket_name,
                "Key": request.file_name,
                "ContentType": "application/pdf",
            },
            ExpiresIn=3600,  # 1 hour expiration
        )

        # Update cache and database with pending status
        cache_manager = _get_cache_manager()
        cache_manager.update_cache_and_database(
            file_name=request.file_name, indexing_status="pending"
        )

        logger.info(f"Generated presigned URL for file: {request.file_name}")
        return {"presigned_url": presigned_url}
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating presigned URL: {str(e)}",
        ) from e


@app.get("/list-pdfs")
async def list_pdfs() -> dict[str, list[dict]]:
    try:
        cache_manager = _get_cache_manager()
        files = cache_manager.get_cache()
        logger.debug(f"Listed {len(files)} PDF files from cache")
        return {"pdf_files": files}
    except Exception as e:
        logger.error(f"Error listing PDFs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing PDFs: {str(e)}",
        ) from e


@app.get("/get_file_link")
async def get_file_link(file_name: str) -> dict[str, str]:
    if not file_name or not file_name.strip():
        logger.warning("Get file link requested with empty file_name")
        raise HTTPException(
            status_code=400,
            detail="file_name parameter is required and cannot be empty",
        )

    try:
        s3_client = get_s3_client()
        download_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.aws_s3_bucket_name,
                "Key": file_name,
            },
            ExpiresIn=3600,  # 1 hour expiration
        )

        logger.info(f"Generated download link for file: {file_name} {download_url}")
        return {"download_url": download_url, "file_name": file_name}
    except (BotoCoreError, ClientError) as e:
        logger.error(
            f"Error generating download URL for {file_name}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error generating download URL: {str(e)}",
        ) from e


@app.delete("/delete_file/")
async def delete_file(request: DeleteFileRequest) -> dict[str, str]:
    if not request.file_name or not request.file_name.strip():
        logger.warning("Delete file requested with empty file_name")
        raise HTTPException(
            status_code=400, detail="file_name is required and cannot be empty"
        )

    try:
        s3_client = get_s3_client()
        # Perform delete
        s3_client.delete_object(
            Bucket=settings.aws_s3_bucket_name, Key=request.file_name
        )

        # Update cache/database to reflect deletion (set status to 'deleted')
        cache_manager = _get_cache_manager()
        try:
            cache_manager.delete_from_cache_and_database(file_name=request.file_name)
        except Exception:
            # Cache/db update should not block S3 deletion; log and continue
            logger.exception("Failed to update cache/database after S3 delete")

        logger.info(f"Deleted file from S3: {request.file_name}")
        return {"deleted": request.file_name}
    except (BotoCoreError, ClientError) as e:
        logger.error(
            f"Error deleting file {request.file_name}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting file: {str(e)}",
        ) from e


@app.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    logger.info(f"Chat request received: {request.user_input[:100]}")

    async def _message_generator() -> AsyncGenerator[str, None]:
        try:
            app_graph = app.state.graph
            config = {"configurable": {"thread_id": LANGGRAPH_THREAD_ID}}

            async for message_chunk in app_graph.astream(
                {"messages": request.user_input},
                stream_mode="messages",
                config=config,
            ):

                # Only yield content that isn't a tool call response
                if (
                    message_chunk[0].content
                    and "<toolcallresponse>" not in message_chunk[0].content
                    and type(message_chunk[0]) is not HumanMessage
                ):
                    yield f"{message_chunk[0].content} "

            logger.info("Chat streaming completed successfully")
        except Exception as e:
            logger.error(f"Error during chat streaming: {str(e)}", exc_info=True)
            yield f"Error: {str(e)}"

    return StreamingResponse(_message_generator(), media_type="text/event-stream")


@app.get("/chat_history")
async def chat_history() -> list[dict[str, str]]:
    config = {"configurable": {"thread_id": LANGGRAPH_THREAD_ID}}

    # Prepare empty result to return quickly in error cases
    chat_history_messages: list[dict[str, str]] = []

    # Access compiled graph from application state
    app_graph = app.state.graph

    try:
        # Get the current state of the chat session
        current_state = await app_graph.aget_state(config)

        # If messages exist, convert them into a simple serializable list
        if current_state and current_state.values.get("messages"):
            for message in current_state.values.get("messages"):
                if "<toolcallresponse>" not in message.content:
                    chat_history_messages.append(
                        {
                            "content": message.content,
                            "type": message.type,
                            "id": message.id,
                        }
                    )
        else:
            logger.info(f"No existing state found for session {LANGGRAPH_THREAD_ID}")
    except Exception as e:
        # Log the error but return an empty list so the frontend can stay robust
        logger.error(
            f"Error retrieving state for session {LANGGRAPH_THREAD_ID} from SQLite: {e}",
            exc_info=True,
        )

    return chat_history_messages


@app.delete("/clear_history")
async def clear_history():
    try:
        await app.state.graph.checkpointer.adelete_thread(LANGGRAPH_THREAD_ID)

        if os.path.exists("checkpoints.sqlite"):
            os.remove("checkpoints.sqlite")
        return {"status": "success", "message": "Chat history cleared."}
    except Exception as e:
        logger.error(f"Error while clearing chat history:{e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Unable to clear chat history at the moment. Please try again later.",
        )

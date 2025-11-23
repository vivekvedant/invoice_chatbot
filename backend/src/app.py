from typing import AsyncGenerator

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from .agent import graph
from .cache_manager import CacheManager
from .config import get_s3_client, get_settings
from .logging_config import configure_uvicorn_logging, get_app_logger
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
from langchain_core.messages.human import HumanMessage
import os

# Initialize centralized logging
logger = get_app_logger()


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


# ===== Request/Response Models =====


class PresignedUrlRequest(BaseModel):
    """Request model for creating a presigned S3 upload URL.

    Attributes:
        file_name: Name (and key) to use for the uploaded PDF file.

    Example:
        {"file_name": "invoices/2025-11-23/invoice123.pdf"}
    """

    file_name: str


class ChatRequest(BaseModel):
    """Request model for the chat endpoint.

    Attributes:
        user_input: Plain text message from the user. Keep it short; the
            backend will stream the assistant's reply as chunks.
    """

    user_input: str


class DeleteFileRequest(BaseModel):
    """Request model for deleting a processed file from S3.

    Attributes:
        file_name: Key of the file to delete. For safety, this is validated
            to be non-empty by the endpoint.
    """

    file_name: str


# ===== Utility =====


def _get_cache_manager() -> CacheManager:
    """Return a new `CacheManager` instance.

    The function is kept small to make testing and future injection easier.
    """
    return CacheManager()


# ===== Endpoints =====


@app.post("/generate-presigned-url/")
async def generate_presigned_url(request: PresignedUrlRequest) -> dict[str, str]:
    """Create a presigned URL clients can use to PUT a PDF to S3.

    The URL is short-lived (1 hour) and the function also marks the file
    as `pending` in the cache/database so the UI can show a progress state.

    Returns a JSON object: {"presigned_url": "https://..."}
    On error the endpoint returns a clear HTTP 500 with a helpful message.
    """
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
    """Return cached list of processed/uploaded PDF files and statuses.

    Response format: {"pdf_files": [ {"file_name": "...", "indexing_status": "..."}, ... ]}
    The endpoint prefers a fast Redis-backed cache; if the cache is stale the
    backend refreshes it in the background. Errors are communicated as HTTP
    status codes with short human-readable messages.
    """
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
    """Return a short-lived download link (presigned GET) for a file.

    Query parameter: `file_name` (required). Returns {"download_url": ..., "file_name": ...}.
    If the parameter is missing or the S3 request fails, the endpoint
    returns a 400 or 500 with a concise message suitable for showing to users.
    """
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
    """Delete a file from S3 and mark it as deleted in cache/database.

    Body: {"file_name": "..."}
    Success response: {"deleted": "<file_name>"}

    The endpoint attempts to update the cache/database after deleting from S3;
    cache/db failures are logged but do not cause the delete operation to fail.
    """
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
            cache_manager.update_cache_and_database(
                file_name=request.file_name, indexing_status="deleted"
            )
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
    """Stream an assistant response for the user's input via server-sent events.

    The endpoint returns a StreamingResponse with `media_type="text/event-stream"`.
    Each yielded string is a short piece of the assistant's reply; the client
    should concatenate them as they arrive. On error the stream yields a single
    "Error: ..." message so the frontend can show a friendly alert.
    """
    logger.info(f"Chat request received: {request.user_input[:100]}")

    async def _message_generator() -> AsyncGenerator[str, None]:
        """Yield textual chunks from the agent graph for SSE consumption.

        Each yielded string is safe to append to the user's chat window. Tool
        responses are filtered out so the client receives only user-facing text.
        """
        try:
            # Use the precompiled graph stored on the app state. The
            # saver used to compile this graph is kept open in the
            # application lifespan, so the checkpointer remains valid.
            app_graph = app.state.graph
            config = {"configurable": {"thread_id": "thread-1"}}

            async for message_chunk in app_graph.astream(
                {"user_prompt": request.user_input},
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
    """Return the conversation history for the current session thread.

    Returns a list of message dicts with the keys:
      - content: the message text
      - type: message role/type (e.g. 'human' or 'ai')
      - id: unique id for the message

    Notes:
      - The function reads the compiled graph state from `app.state.graph`.
      - If no history exists an empty list is returned so the UI can handle it
        without errors.
      - Errors are logged and an empty list is returned to avoid crashing the
        client; the frontend may show a brief notification when the list is
        empty.
    """
    config = {"configurable": {"thread_id": "thread-1"}}

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
                chat_history_messages.append(
                    {
                        "content": message.content,
                        "type": message.type,
                        "id": message.id,
                    }
                )
        else:
            logger.info("No existing state found for session thread-1")
    except Exception as e:
        # Log the error but return an empty list so the frontend can stay robust
        logger.error(
            f"Error retrieving state for session thread-1 from SQLite: {e}",
            exc_info=True,
        )

    return chat_history_messages


@app.delete("/clear_history")
async def clear_history():
    try:
        os.remove("checkpoints.sqlite")
        return {"status": "success", "message": "Chat history cleared."}
    except Exception as e:
        logger.error(f"Error while clearing chat history:{e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Unable to clear chat history at the moment. Please try again later.",
        )

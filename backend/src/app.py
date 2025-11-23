"""
FastAPI application for invoice chatbot backend.

Provides endpoints for:
  - Presigned URL generation for S3 file uploads
  - PDF listing from cache and database
  - Streaming chat responses via agentic workflow
  - Real-time indexing status updates
"""

from typing import AsyncGenerator

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from .agent import _graph
from .agent import get_graph_schema
from .cache_manager import CacheManager
from .config import get_s3_client, get_settings
from .logging_config import configure_uvicorn_logging, get_app_logger
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
from langchain_core.messages import AIMessage
from langchain_core.messages.human import HumanMessage

# Initialize centralized logging
logger = get_app_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_uvicorn_logging()
    logger.info("FastAPI application started")
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as saver:
        app.state.graph = _graph.compile(checkpointer=saver)
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
    """Request model for presigned URL generation."""

    file_name: str


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    user_input: str


class DeleteFileRequest(BaseModel):
    """Request model for deleting a file from S3."""

    file_name: str


# ===== Utility =====


def _get_cache_manager() -> CacheManager:
    """Get a CacheManager instance."""
    return CacheManager()


# ===== Endpoints =====


@app.post("/generate-presigned-url/")
async def generate_presigned_url(request: PresignedUrlRequest) -> dict[str, str]:
    """
    Generate a presigned URL for uploading a file to S3.

    Args:
        request: Contains the file name to upload.

    Returns:
        Dictionary with presigned_url key.

    Raises:
        HTTPException: If S3 presigned URL generation fails.
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
    """
    List all PDF files and their indexing status.

    Returns from Redis cache with automatic fallback to database refresh.

    Returns:
        Dictionary with pdf_files key containing list of file metadata.

    Raises:
        HTTPException: If cache/database query fails.
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
    """
    Generate a temporary presigned URL for downloading a file from S3.

    Allows clients to download processed PDF files with automatic expiration.

    Args:
        file_name: Name of the file to download (query parameter).

    Returns:
        Dictionary with download_url and file_name keys.

    Raises:
        HTTPException: If file_name is empty or S3 URL generation fails.
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
    """
    Delete a file from S3 given its file name.

    Accepts:
        JSON body with `file_name` key.

    Returns:
        dict with deleted file_name on success.

    Side effects:
        - Calls S3 DeleteObject
        - Updates cache/database status to "deleted"
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
    """
    Stream chat responses using agentic workflow.

    Integrates Neo4j graph schema, LLM with tools, and streaming message output.

    Args:
        request: User query text.

    Returns:
        StreamingResponse with text/event-stream content type.
    """
    logger.info(f"Chat request received: {request.user_input[:100]}")

    async def _message_generator() -> AsyncGenerator[str, None]:
        """Stream messages from the agentic workflow."""
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
async def chat_history():
    config = {"configurable": {"thread_id": "thread-1"}}

    # Initialize an empty list to store chat messages
    chat_history_messages = []

    # Access Compiled Graph from Application State
    app_graph = app.state.graph

    try:
        # Get the current state of the chat session
        current_state = await app_graph.aget_state(config)

        # Check if current state is valid
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
            logger.info(f"No existing state found for session thread-1")
    except Exception as e:
        logger.error(f"Error retrieving state for session thread-1 from SQLite: {e}")

    # Return conversation history
    return chat_history_messages

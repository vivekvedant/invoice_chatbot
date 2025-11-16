"""
FastAPI application for invoice chatbot backend.

Provides endpoints for:
  - Presigned URL generation for S3 file uploads
  - PDF listing from cache and database
  - Streaming chat responses via agentic workflow
  - Real-time indexing status updates
"""

import asyncio
import json
from typing import AsyncGenerator

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from .agent import app as agent_app
from .agent import get_graph_schema
from .cache_manager import CacheManager
from .config import get_s3_client, get_settings

# Initialize FastAPI app
app = FastAPI(
    title="Invoice Chatbot Backend",
    description="AI-powered invoice knowledge graph and chat interface",
    version="0.1.0",
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

        return {"presigned_url": presigned_url}
    except (BotoCoreError, ClientError) as e:
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
        return {"pdf_files": files}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing PDFs: {str(e)}",
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
    system_prompt = f"""
    neo4j graph schema: {get_graph_schema()}
    provide answer in sentence format.

    Final answer output:
    """

    async def _message_generator() -> AsyncGenerator[str, None]:
        """Stream messages from the agentic workflow."""
        async for message_chunk in agent_app.astream(
            {
                "messages": [
                    AIMessage(content=system_prompt),
                    HumanMessage(content=request.user_input),
                ]
            },
            stream_mode="messages",
        ):
            # Only yield content that isn't a tool call response
            if (
                message_chunk[0].content
                and "<toolcallresponse>" not in message_chunk[0].content
            ):
                yield f"{message_chunk[0].content} "

    return StreamingResponse(_message_generator(), media_type="text/event-stream")



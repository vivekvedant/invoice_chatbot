from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
import pathlib
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import time
from typing import AsyncIterator
from backend.agent import get_graph_schema
from langchain_core.messages import AIMessage, HumanMessage
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse
from backend.agent import app as agent

load_dotenv()

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# AWS S3 client
s3_client = boto3.client("s3")


class PresignedUrlRequest(BaseModel):
    file_name: str


class ChatRequest(BaseModel):
    user_input: str


@app.post("/generate-presigned-url/")
async def generate_presigned_url(request: PresignedUrlRequest):
    """
    Generate a presigned URL for uploading a file to S3.
    """
    print(os.getenv("AMAZON_S3_BUCKET_NAME"))
    try:
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": os.getenv("AMAZON_S3_BUCKET_NAME"),
                "Key": request.file_name,
                "ContentType": "application/pdf",
            },
            ExpiresIn=3600,  # URL expiration time in seconds (1 hour)
        )
        return {"presigned_url": presigned_url}
    except (BotoCoreError, ClientError) as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating presigned URL: {str(e)}"
        )


@app.get("/list-pdfs/")
async def list_pdfs():
    """
    List all PDF files available in the S3 invoices directory.
    """
    try:
        S3_BUCKET = os.getenv("AMAZON_S3_BUCKET_NAME")
        s3 = boto3.client("s3")
        pdf_files = []

        # List objects in the specified S3 prefix (folder)
        response = s3.list_objects_v2(Bucket=S3_BUCKET)

        # If the bucket/folder is empty
        if "Contents" not in response:
            return {"pdf_files": []}

        for obj in response["Contents"]:
            key = obj["Key"]
            if key.lower().endswith(".pdf"):
                pdf_files.append(
                    {
                        "name": key.split("/")[-1],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "s3_key": key,
                        "url": f"https://{S3_BUCKET}.s3.amazonaws.com/{key}",
                    }
                )

        return {"pdf_files": pdf_files}

    except ClientError as e:
        print(e)
        raise HTTPException(
            status_code=500, detail=f"AWS S3 error: {e.response['Error']['Message']}"
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error listing S3 PDFs: {str(e)}")


@app.post("/chat")
async def chat(request: ChatRequest):
    system_prompt = f"""
    neo4j graph schema: {get_graph_schema()}
    provide asnwer in sentence
    
    Final answer output
    """

    async def message_generator() -> AsyncGenerator[str, None]:
        async for message_chunk in agent.astream(
            {
                "messages": [
                    AIMessage(content=system_prompt),
                    HumanMessage(content=request.user_input),
                ]
            },
            stream_mode="messages",
        ):
            # print(message_chunk[0])
            if (
                message_chunk[0].content
                and "<toolcallresponse>" not in message_chunk[0].content
            ):
                yield f"{message_chunk[0].content} "

    return StreamingResponse(message_generator(), media_type="text/event-stream")

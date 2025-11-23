import os
from functools import lru_cache
from typing import Optional

import boto3
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_neo4j import Neo4jGraph
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables.

    Notes:
        - Values fall back to sensible defaults where applicable.
        - Use `get_settings()` for a cached Settings instance.
    """

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars not defined in model
    )

    # Neo4j Configuration
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")

    # AWS S3 Configuration
    aws_s3_bucket_name: str = os.getenv("AMAZON_S3_BUCKET_NAME", "invoices")
    aws_s3_prefix: Optional[str] = os.getenv("AMAZON_S3_PREFIX", None)
    aws_s3_sqs_queue_url: Optional[str] = os.getenv("AMAZON_S3_SQS_QUEUE_URL", None)

    # Redis Configuration
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    redis_db: int = 0

    # Database Configuration
    cocoindex_database_url: str = os.getenv(
        "COCOINDEX_DATABASE_URL", "postgresql://user:password@localhost/db"
    )

    # LLM Configuration
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    llm_model: str = "gemini-flash-lite-latest"

    # CORS Configuration
    cors_origins: list[str] = ["*"]

    def model_validate_env(self) -> None:
        """Validate critical environment variables at startup."""
        required_keys = [
            "NEO4J_URI",
            "AMAZON_S3_BUCKET_NAME",
            "REDIS_HOST",
            "COCOINDEX_DATABASE_URL",
        ]
        missing = [k for k in required_keys if not os.getenv(k)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached application settings singleton.
    Uses lru_cache to ensure only one Settings instance is created.
    """
    return Settings()


@lru_cache(maxsize=1)
def get_neo4j_graph() -> Neo4jGraph:
    """
    Get cached Neo4j graph instance.
    Reuses connection to avoid re-instantiation overhead.
    """
    settings = get_settings()
    return Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_user,
        password=settings.neo4j_password,
        enhanced_schema=True,
    )


@lru_cache(maxsize=1)
def get_s3_client():
    """
    Get cached AWS S3 client instance.
    Reuses boto3 session to maintain connection pooling.
    """
    return boto3.client("s3")


@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI:
    """
    Get cached LLM instance.
    Reuses ChatGoogleGenerativeAI to avoid repeated initialization.
    """
    settings = get_settings()
    return ChatGoogleGenerativeAI(model=settings.llm_model)

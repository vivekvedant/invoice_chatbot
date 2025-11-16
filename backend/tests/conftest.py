"""Pytest configuration and shared fixtures."""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables before running tests."""
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "password")
    os.environ.setdefault("AMAZON_S3_BUCKET_NAME", "test-bucket")
    os.environ.setdefault("REDIS_HOST", "localhost")
    os.environ.setdefault("REDIS_PORT", "6379")
    os.environ.setdefault("COCOINDEX_DATABASE_URL", "postgresql://test:test@localhost/test")
    os.environ.setdefault("GOOGLE_API_KEY", "test-key")

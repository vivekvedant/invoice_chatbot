"""Tests for the FastAPI application."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.app import app


@pytest.fixture
def client():
    """Fixture to provide a FastAPI test client."""
    return TestClient(app)


class TestPresignedUrlEndpoint:
    """Tests for the presigned URL endpoint."""

    @patch("src.app.get_s3_client")
    @patch("src.app._get_cache_manager")
    def test_generate_presigned_url_success(self, mock_cache_mgr, mock_s3_client, client):
        """Test successful presigned URL generation."""
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = (
            "https://s3.example.com/presigned_url"
        )
        mock_s3_client.return_value = mock_s3

        mock_cache_mgr.return_value = MagicMock()

        response = client.post(
            "/generate-presigned-url/",
            json={"file_name": "test_invoice.pdf"},
        )

        assert response.status_code == 200
        assert "presigned_url" in response.json()
        assert response.json()["presigned_url"] == "https://s3.example.com/presigned_url"

    @patch("src.app.get_s3_client")
    def test_generate_presigned_url_s3_error(self, mock_s3_client, client):
        """Test presigned URL generation with S3 error."""
        from botocore.exceptions import BotoCoreError

        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.side_effect = BotoCoreError()
        mock_s3_client.return_value = mock_s3

        response = client.post(
            "/generate-presigned-url/",
            json={"file_name": "test_invoice.pdf"},
        )

        assert response.status_code == 500
        assert "Error generating presigned URL" in response.json()["detail"]


class TestListPdfsEndpoint:
    """Tests for the list PDFs endpoint."""

    @patch("src.app._get_cache_manager")
    def test_list_pdfs_success(self, mock_cache_mgr, client):
        """Test successful PDF listing."""
        mock_cache = MagicMock()
        mock_cache.get_cache.return_value = [
            {
                "file_name": "invoice1.pdf",
                "status": "completed",
                "last_updated": "2025-01-15",
            },
            {
                "file_name": "invoice2.pdf",
                "status": "pending",
                "last_updated": "2025-01-16",
            },
        ]
        mock_cache_mgr.return_value = mock_cache

        response = client.get("/list-pdfs")

        assert response.status_code == 200
        data = response.json()
        assert "pdf_files" in data
        assert len(data["pdf_files"]) == 2

    @patch("src.app._get_cache_manager")
    def test_list_pdfs_empty(self, mock_cache_mgr, client):
        """Test listing PDFs when none exist."""
        mock_cache = MagicMock()
        mock_cache.get_cache.return_value = []
        mock_cache_mgr.return_value = mock_cache

        response = client.get("/list-pdfs")

        assert response.status_code == 200
        data = response.json()
        assert data["pdf_files"] == []

    @patch("src.app._get_cache_manager")
    def test_list_pdfs_error(self, mock_cache_mgr, client):
        """Test PDF listing with error."""
        mock_cache = MagicMock()
        mock_cache.get_cache.side_effect = Exception("DB connection failed")
        mock_cache_mgr.return_value = mock_cache

        response = client.get("/list-pdfs")

        assert response.status_code == 500
        assert "Error listing PDFs" in response.json()["detail"]


class TestChatEndpoint:
    """Tests for the chat endpoint."""

    @patch("src.app.agent_app")
    @patch("src.app.get_graph_schema")
    async def test_chat_stream(self, mock_schema, mock_agent, client):
        """Test chat endpoint streaming."""
        from unittest.mock import AsyncMock

        mock_schema.return_value = "Node: Invoice, Item"

        # Mock async generator
        async def mock_astream(*args, **kwargs):
            class MockMessage:
                content = "Test response"

            yield [MockMessage()]

        mock_agent.astream = mock_astream

        response = client.post(
            "/chat",
            json={"user_input": "What is in invoice 1?"},
        )

        # Streaming endpoint returns 200 with stream
        assert response.status_code == 200


class TestIndexingStatusEndpoint:
    """Tests for the indexing status endpoint."""

    @patch("src.app._get_cache_manager")
    def test_indexing_status_stream(self, mock_cache_mgr, client):
        """Test that indexing status endpoint returns streaming response."""
        mock_cache = MagicMock()
        mock_cache.get_cache.return_value = [
            {"file_name": "test.pdf", "status": "indexing", "last_updated": "2025-01-15"}
        ]
        mock_cache_mgr.return_value = mock_cache

        response = client.get("/indexing-status")

        # Streaming endpoint returns 200
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

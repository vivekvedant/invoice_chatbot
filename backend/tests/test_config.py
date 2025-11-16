"""Tests for configuration module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.config import Settings, get_settings, get_neo4j_graph, get_s3_client, get_llm


class TestSettings:
    """Test Settings model initialization."""

    def test_settings_creation(self):
        """Test that Settings can be instantiated."""
        settings = Settings()
        assert settings.neo4j_uri is not None
        assert settings.redis_host is not None
        assert settings.aws_s3_bucket_name is not None

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2  # Same object (lru_cache)

    @patch("src.config.Neo4jGraph")
    def test_neo4j_graph_cached(self, mock_neo4j):
        """Test that get_neo4j_graph returns cached instance."""
        # Mock the Neo4jGraph to avoid requiring real database
        mock_neo4j.return_value = MagicMock()
        
        graph1 = get_neo4j_graph()
        graph2 = get_neo4j_graph()
        assert graph1 is graph2  # Same object (lru_cache)

    def test_s3_client_cached(self):
        """Test that get_s3_client returns cached instance."""
        client1 = get_s3_client()
        client2 = get_s3_client()
        assert client1 is client2  # Same object (lru_cache)

    def test_llm_cached(self):
        """Test that get_llm returns cached instance."""
        llm1 = get_llm()
        llm2 = get_llm()
        assert llm1 is llm2  # Same object (lru_cache)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


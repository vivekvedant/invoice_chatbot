"""Tests for the cache manager module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import redis

from src.cache_manager import CacheManager


@pytest.fixture
def mock_redis():
    """Fixture to provide a mock Redis client."""
    with patch("src.cache_manager.redis.Redis") as mock:
        yield mock.return_value


@pytest.fixture
def mock_db_session():
    """Fixture to provide a mock database session context manager."""
    with patch("src.cache_manager._db_session") as mock:
        yield mock


@pytest.fixture
def cache_manager(mock_redis):
    """Fixture to provide a CacheManager instance with mocked Redis."""
    with patch("src.cache_manager.get_settings"):
        manager = CacheManager()
        manager.redis = mock_redis
        return manager


class TestCacheManager:
    """Tests for CacheManager class."""

    def test_cache_manager_init(self, cache_manager):
        """Test CacheManager initialization."""
        assert cache_manager.redis is not None
        assert cache_manager.DEFAULT_CACHE_KEY == "pdf_files_cache"

    def test_load_cache_hit(self, cache_manager):
        """Test loading from cache when data exists."""
        cache_data = [
            {
                "file_name": "invoice1.pdf",
                "status": "completed",
                "last_updated": "2025-01-15",
            }
        ]
        import json

        cache_manager.redis.get.return_value = json.dumps(cache_data)

        result = cache_manager._load_cache("test_key")
        assert result == cache_data
        cache_manager.redis.get.assert_called_once_with("test_key")

    def test_load_cache_miss(self, cache_manager):
        """Test loading from cache when data does not exist."""
        cache_manager.redis.get.return_value = None

        result = cache_manager._load_cache("test_key")
        assert result is None

    def test_save_cache(self, cache_manager):
        """Test saving data to cache."""
        data = [
            {
                "file_name": "invoice1.pdf",
                "status": "pending",
                "last_updated": "2025-01-15",
            }
        ]
        cache_manager._save_cache("test_key", data)

        cache_manager.redis.set.assert_called_once()
        args = cache_manager.redis.set.call_args
        assert args[0][0] == "test_key"

    def test_get_cache_with_cached_data(self, cache_manager, mock_db_session):
        """Test get_cache returns cached data without hitting DB."""
        cache_data = [
            {
                "file_name": "invoice1.pdf",
                "status": "completed",
                "last_updated": "2025-01-15",
            }
        ]
        import json

        cache_manager.redis.get.return_value = json.dumps(cache_data)

        result = cache_manager.get_cache()
        assert result == cache_data
        # Should not query DB
        mock_db_session.assert_not_called()

    def test_get_cache_force_update(self, cache_manager, mock_db_session):
        """Test get_cache forces update from DB."""
        cache_manager.redis.get.return_value = None
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_db_session.return_value.__enter__.return_value = mock_session

        result = cache_manager.get_cache(force_update=True)
        assert result == []

    def test_update_cache_and_database_new_file(
        self, cache_manager, mock_db_session
    ):
        """Test updating cache and database with a new file."""
        import json

        cache_data = []
        cache_manager.redis.get.return_value = json.dumps(cache_data)

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            None
        )
        mock_db_session.return_value.__enter__.return_value = mock_session

        cache_manager.update_cache_and_database(
            file_name="new_file.pdf", indexing_status="pending"
        )

        # Verify the file was added
        cache_manager.redis.set.assert_called()

    def test_update_cache_and_database_existing_file(
        self, cache_manager, mock_db_session
    ):
        """Test updating cache and database for an existing file."""
        import json

        cache_data = [
            {
                "file_name": "existing.pdf",
                "status": "pending",
                "last_updated": "2025-01-15",
            }
        ]
        cache_manager.redis.get.return_value = json.dumps(cache_data)

        mock_session = MagicMock()
        mock_file = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_file
        )
        mock_db_session.return_value.__enter__.return_value = mock_session

        cache_manager.update_cache_and_database(
            file_name="existing.pdf", indexing_status="completed"
        )

        # Verify the status was updated
        assert mock_file.status == "completed"
        assert mock_file.last_updated is not None

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

import redis
from sqlalchemy.orm import Session

from config import get_settings
from db_models import Files, get_session


@contextmanager
def _db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Ensures automatic commit, rollback on error, and cleanup.

    Yields:
        SQLAlchemy Session instance.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class CacheManager:
    """
    Manages file indexing status via Redis cache + PostgreSQL persistence.

    - Uses Redis for fast lookups
    - Falls back to PostgreSQL if cache miss
    - Auto-syncs between layers on updates
    """

    DEFAULT_CACHE_KEY = "pdf_files_cache"

    def __init__(self) -> None:
        """Initialize Redis client from config."""
        settings = get_settings()
        self.redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )

    # -----------------------------------------------------
    # =====================================================
    # Private Helpers
    # =====================================================

    def _load_cache(self, key: str) -> list[dict] | None:
        """
        Load cached data from Redis.

        Args:
            key: Redis cache key.

        Returns:
            Parsed JSON list or None if not found.
        """
        cached = self.redis.get(key)
        return json.loads(cached) if cached else None

    def _save_cache(self, key: str, data: list[dict]) -> None:
        """
        Save data to Redis cache.

        Args:
            key: Redis cache key.
            data: List of dictionaries to cache.
        """
        self.redis.set(key, json.dumps(data))

    def _fetch_files_from_db(self) -> list[dict]:
        """
        Fetch all file records from database.

        Returns:
            List of file metadata dictionaries.
        """
        with _db_session() as session:
            records = session.query(Files).all()
            return [record.to_dict() for record in records] if records else []

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------
    def get_cache(
        self, cache_key: str = DEFAULT_CACHE_KEY, force_update: bool = False
    ) -> list[dict]:
        """
        Return cached file info, rehydrating from DB when missing or forced.
        """

        if not force_update:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return cached

        fresh_data = self._fetch_files_from_db()
        self._save_cache(cache_key, fresh_data)
        return fresh_data

    def update_cache_and_database(self, file_name: str, indexing_status: str) -> None:
        """
        Update a file's indexing status in both Redis and DB.
        Auto-creates file record if missing.
        """

        cache_key = self.DEFAULT_CACHE_KEY
        cached_files = self.get_cache(cache_key)

        # Create lookup map for O(1) file index search
        index_map = {item["file_name"]: i for i, item in enumerate(cached_files)}

        timestamp = datetime.now(timezone.utc)
        unix_timestamp = int(timestamp.timestamp())

        # Existing entry update or new entry append
        if file_name in index_map:
            idx = index_map[file_name]
            cached_files[idx]["status"] = indexing_status
            cached_files[idx]["last_updated"] = unix_timestamp
        else:
            cached_files.append(
                {
                    "file_name": file_name,
                    "status": indexing_status,
                    "last_updated": unix_timestamp,
                }
            )

        # Sync to database
        with _db_session() as session:
            record = session.query(Files).filter_by(file_name=file_name).first()

            if record:
                record.status = indexing_status
                record.last_updated = unix_timestamp
            else:
                session.add(
                    Files(
                        file_name=file_name,
                        status=indexing_status,
                        last_updated=unix_timestamp,
                    )
                )

        # Save updated cache
        self._save_cache(cache_key, cached_files)

    def delete_from_cache_and_database(self, file_name: str) -> None:
        """
        Delete a file's record from both Redis cache and SQL database.
        Silent if record does not exist.
        """

        cache_key = self.DEFAULT_CACHE_KEY
        cached_files = self.get_cache(cache_key)

        # Build lookup map for O(1) lookup
        index_map = {item["file_name"]: i for i, item in enumerate(cached_files)}

        # Remove from cache if present
        if file_name in index_map:
            idx = index_map[file_name]
            cached_files.pop(idx)
            self._save_cache(cache_key, cached_files)

        # Remove from database
        with _db_session() as session:
            record = session.query(Files).filter_by(file_name=file_name).first()
            if record:
                session.delete(record)

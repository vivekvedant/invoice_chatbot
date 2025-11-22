"""
Database models and session factory for file indexing.

Uses SQLAlchemy ORM with PostgreSQL backend for persistence.
Provides session factory and declarative base for model definitions.
"""

from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import Column, DateTime, Integer, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings
from sqlalchemy import DateTime


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def utc_timestamp():
    return int(datetime.now(timezone.utc).timestamp())


class Files(Base):
    """
    File indexing status model.

    Tracks PDF files, their names, processing status, and timestamps.

    Attributes:
        id: Primary key.
        file_name: Name of the PDF file.
        status: Current indexing status (e.g., "pending", "indexing", "completed").
        created_at: Timestamp when record was created (UTC).
        last_updated: Timestamp of last status update (UTC).
    """

    __tablename__ = "file_index_status"
    __table_args__ = ({"schema": "custom_app"},)

    id = Column(Integer, primary_key=True)
    file_name = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    created_at = Column(
        Integer,
        default=utc_timestamp,
        nullable=False,
    )

    last_updated = Column(
        Integer,
        default=utc_timestamp,      # give initial value
        onupdate=utc_timestamp,     # update on update
        nullable=False,
    )

    def to_dict(self) -> dict[str, str | int | None]:
        """
        Convert model instance to dictionary.

        Returns:
            Dictionary representation of file record.
        """
        return {
            "id": self.id,
            "file_name": self.file_name,
            "status": self.status,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }


@lru_cache(maxsize=1)
def get_db_engine():
    """
    Get cached database engine instance.

    Lazy-loads engine to avoid connection attempts during import.
    Uses lru_cache to ensure single engine instance.

    Returns:
        SQLAlchemy Engine configured with PostgreSQL connection.
    """
    settings = get_settings()
    engine = create_engine(settings.cocoindex_database_url)

    # Create schema and tables
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS custom_app"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
    return engine


@lru_cache(maxsize=1)
def get_session_factory():
    """
    Get cached session factory instance.

    Returns:
        SQLAlchemy sessionmaker bound to the database engine.
    """
    return sessionmaker(bind=get_db_engine())


def get_session():
    """
    Create a new database session.

    Returns:
        New SQLAlchemy Session instance.
    """
    SessionFactory = get_session_factory()
    return SessionFactory()

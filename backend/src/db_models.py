"""
Database models and session factory for file indexing.

Uses SQLAlchemy ORM with PostgreSQL backend for persistence.
Provides session factory and declarative base for model definitions.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import Column, DateTime, Integer, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


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
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_updated = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
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
            "created_at": (
                self.created_at.strftime("%Y-%m-%d") if self.created_at else None
            ),
            "last_updated": (
                self.last_updated.strftime("%Y-%m-%d") if self.last_updated else None
            ),
        }


# Initialize database engine and session factory
_settings = get_settings()
engine = create_engine(_settings.cocoindex_database_url)

# Create schema and tables
with engine.begin() as conn:
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS custom_app"))
    conn.commit()

Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(bind=engine)



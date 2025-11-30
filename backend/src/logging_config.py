import logging
import os
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Define logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
API_LOG_FILE = LOGS_DIR / "api.log"
INDEXER_LOG_FILE = LOGS_DIR / "indexer.log"
COMBINED_LOG_FILE = LOGS_DIR / "combined.log"

# Logging configuration
LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5  # Keep 5 rotated log files
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def _create_rotating_handler(log_file: Path) -> RotatingFileHandler:
    """
    Create a rotating file handler for a specific log file.

    Args:
        log_file: Path to the log file.

    Returns:
        Configured RotatingFileHandler instance.
    """
    handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    handler.setFormatter(formatter)
    return handler


def _create_console_handler() -> logging.StreamHandler:
    """
    Create a console (stderr) handler with same formatting.

    Returns:
        Configured StreamHandler instance.
    """
    handler = logging.StreamHandler()
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    handler.setFormatter(formatter)
    return handler


@lru_cache(maxsize=1)
def get_app_logger(name: str = "invoice_chatbot.app") -> logging.Logger:
    """
    Get configured logger for FastAPI application.

    Logs to both `./logs/api.log` and console (stderr).

    Args:
        name: Logger name (defaults to "invoice_chatbot.app").

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Clear existing handlers to prevent duplicates
    logger.handlers.clear()

    # Add file handler (API-specific)
    logger.addHandler(_create_rotating_handler(API_LOG_FILE))

    # Add console handler
    logger.addHandler(_create_console_handler())

    return logger


@lru_cache(maxsize=1)
def get_indexer_logger(name: str = "invoice_chatbot.indexer") -> logging.Logger:
    """
    Get configured logger for indexing service.

    Logs to both `./logs/indexer.log` and console (stderr).

    Args:
        name: Logger name (defaults to "invoice_chatbot.indexer").

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Clear existing handlers to prevent duplicates
    logger.handlers.clear()

    # Add file handler (indexer-specific)
    logger.addHandler(_create_rotating_handler(INDEXER_LOG_FILE))

    # Add console handler
    logger.addHandler(_create_console_handler())

    return logger


@lru_cache(maxsize=1)
def get_logger(name: str = "invoice_chatbot") -> logging.Logger:
    """
    Get general-purpose logger for the project.

    Logs to `./logs/combined.log` and console (stderr).

    Args:
        name: Logger name (defaults to "invoice_chatbot").

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Clear existing handlers to prevent duplicates
    logger.handlers.clear()

    # Add file handler (combined)
    logger.addHandler(_create_rotating_handler(COMBINED_LOG_FILE))

    # Add console handler
    logger.addHandler(_create_console_handler())

    return logger


def configure_uvicorn_logging() -> None:
    """
    Configure uvicorn's built-in loggers to use our centralized logging.

    Call this in app startup to integrate uvicorn logs.
    """
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(LOG_LEVEL)
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(_create_rotating_handler(API_LOG_FILE))
    uvicorn_logger.addHandler(_create_console_handler())

    # Also configure uvicorn.access logs
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.setLevel(LOG_LEVEL)
    access_logger.handlers.clear()
    access_logger.addHandler(_create_rotating_handler(API_LOG_FILE))

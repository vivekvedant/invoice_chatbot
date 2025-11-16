"""
Invoice Chatbot Backend Package.

Provides FastAPI application, Neo4j integration, LLM-based agentic workflow,
and file indexing pipeline.
"""

from .cache_manager import CacheManager
from .config import get_llm, get_neo4j_graph, get_s3_client, get_settings
from .db_models import Files, SessionLocal, get_session
from .models import CypherQuery, Invoice, Item, Relationship

# Import agent exports separately to handle langgraph compatibility issues
try:
    from .agent import app as agent_app
    from .agent import get_graph_schema
except ImportError:
    agent_app = None
    get_graph_schema = None

__all__ = [
    "agent_app",
    "get_graph_schema",
    "CacheManager",
    "get_settings",
    "get_neo4j_graph",
    "get_s3_client",
    "get_llm",
    "Files",
    "SessionLocal",
    "get_session",
    "CypherQuery",
    "Invoice",
    "Item",
    "Relationship",
]

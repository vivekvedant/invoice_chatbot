"""Tests for the agent module."""

from unittest.mock import MagicMock, patch

import pytest

from src.agent import ChatbotState, get_graph_schema, run_cypher_query


class TestRunCypherQuery:
    """Tests for the run_cypher_query tool."""

    @patch("src.agent.get_neo4j_graph")
    def test_run_cypher_query_success(self, mock_get_graph):
        """Test executing a successful Cypher query."""
        mock_graph = MagicMock()
        mock_graph.query.return_value = [{"id": 1, "name": "Test"}]
        mock_get_graph.return_value = mock_graph

        result = run_cypher_query("MATCH (n) RETURN n LIMIT 1")

        assert "<toolcallresponse>" in result
        assert "[{'id': 1, 'name': 'Test'}]" in result
        mock_graph.query.assert_called_once_with(query="MATCH (n) RETURN n LIMIT 1")

    @patch("src.agent.get_neo4j_graph")
    def test_run_cypher_query_empty_result(self, mock_get_graph):
        """Test Cypher query that returns empty result."""
        mock_graph = MagicMock()
        mock_graph.query.return_value = []
        mock_get_graph.return_value = mock_graph

        result = run_cypher_query("MATCH (n:NonExistent) RETURN n")

        assert "<toolcallresponse>[]</toolcallresponse>" == result


class TestGetGraphSchema:
    """Tests for the get_graph_schema function."""

    @patch("src.agent.get_neo4j_graph")
    def test_get_graph_schema(self, mock_get_graph):
        """Test retrieving the graph schema."""
        mock_graph = MagicMock()
        mock_schema = "Node types: [Invoice, Item]\nRelationships: [HAS_ITEM]"
        mock_graph.schema = mock_schema
        mock_get_graph.return_value = mock_graph

        schema = get_graph_schema()

        assert schema == mock_schema
        mock_get_graph.assert_called_once()

    @patch("src.agent.get_neo4j_graph")
    def test_get_graph_schema_caching(self, mock_get_graph):
        """Test that get_graph_schema uses cached Neo4j graph."""
        mock_graph = MagicMock()
        mock_graph.schema = "Cached Schema"
        mock_get_graph.return_value = mock_graph

        schema1 = get_graph_schema()
        schema2 = get_graph_schema()

        assert schema1 == schema2
        # get_neo4j_graph should be called twice but return same instance
        assert mock_get_graph.call_count == 2


class TestChatbotState:
    """Tests for the ChatbotState TypedDict."""

    def test_chatbot_state_structure(self):
        """Test that ChatbotState has expected structure."""
        # ChatbotState is a TypedDict, verify it has the expected annotation
        assert hasattr(ChatbotState, "__annotations__")
        assert "messages" in ChatbotState.__annotations__


class TestAgentGraph:
    """Tests for the agent graph structure."""

    @patch("src.agent.get_llm")
    def test_agent_graph_has_app(self, mock_get_llm):
        """Test that agent module has compiled graph as 'app'."""
        from src import agent

        assert hasattr(agent, "app")
        assert hasattr(agent.app, "invoke")
        assert hasattr(agent.app, "astream")

    @patch("src.agent.get_llm")
    def test_agent_tools_list(self, mock_get_llm):
        """Test that agent has tools defined."""
        from src import agent

        assert hasattr(agent, "_tools")
        assert len(agent._tools) > 0
        # run_cypher_query should be in tools
        tool_names = [t.name for t in agent._tools]
        assert "run_cypher_query" in tool_names

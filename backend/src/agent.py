"""
Agent module for invoice chatbot.

Provides LangGraph-based agentic workflow with Neo4j graph querying capability.
Uses tools to execute Cypher queries and streams responses via tool node routing.
"""

from typing import Annotated, Any, TypedDict

from langchain.tools import tool
from langgraph.graph import END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from .config import get_llm, get_neo4j_graph


@tool
def run_cypher_query(query: str) -> str:
    """
    Execute a Neo4j Cypher query and return results.

    Args:
        query: Neo4j Cypher query string to execute.

    Returns:
        XML-wrapped result string with query response, suitable for LLM parsing.

    Raises:
        Exception: If query execution fails.
    """
    graph = get_neo4j_graph()
    result = graph.query(query=query)
    return f"<toolcallresponse>{result}</toolcallresponse>"


def get_graph_schema() -> str:
    """
    Get the schema of the Neo4j knowledge graph.

    Returns:
        Schema description string for the configured Neo4j database.
    """
    graph = get_neo4j_graph()
    return graph.schema


# Define tools available to the agent
_tools = [run_cypher_query]


class ChatbotState(TypedDict):
    """State schema for the chatbot agent.

    Attributes:
        messages: List of chat messages, accumulated via add_messages reducer.
    """

    messages: Annotated[list[Any], add_messages]


def _chatbot_node(state: ChatbotState) -> dict[str, list[Any]]:
    """
    Chatbot LLM node.

    Invokes the LLM with available tools and returns the response message.
    """
    llm = get_llm()
    llm_with_tools = llm.bind_tools(tools=_tools)
    return {
        "messages": [llm_with_tools.invoke(state["messages"])],
    }


def _tools_router(state: ChatbotState) -> str:
    """
    Router to decide if tool invocation is needed.

    Args:
        state: Current chatbot state.

    Returns:
        "tool_node" if last message has tool calls, else END to finish.
    """
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tool_node"
    return END


# Build the LangGraph
_tool_node = ToolNode(tools=_tools)
_graph = StateGraph(ChatbotState)

_graph.add_node("chatbot", _chatbot_node)
_graph.add_node("tool_node", _tool_node)
_graph.set_entry_point("chatbot")
_graph.add_conditional_edges("chatbot", _tools_router)
_graph.add_edge("tool_node", "chatbot")

# Compile the runnable app
app = _graph.compile()

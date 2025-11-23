"""
Agent module for invoice chatbot.

Provides LangGraph-based agentic workflow with Neo4j graph querying capability.
Uses tools to execute Cypher queries and streams responses via tool node routing.
"""

from typing import Annotated, Any, TypedDict

from langchain.tools import tool
from langgraph.graph import END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
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

    user_prompt: str
    messages: Annotated[list[BaseMessage], add_messages]
    response: str


def process_user_node(state: ChatbotState):
    messages = []

    messages.append(HumanMessage(content=state["user_prompt"]))
    return {"messages": messages}


def _chatbot_node(state: ChatbotState) -> dict[str, list[Any]]:
    """
    Chatbot LLM node.

    Invokes the LLM with available tools and returns the response message.
    """
    llm = get_llm()
    llm_with_tools = llm.bind_tools(tools=_tools)

    # if SystemMessage not in state["messages"]:
    system_prompt = f"""
    # Role:
    You are a assistant agent who will only answer the queries related to invoices from past
    conversation or fetch the relevant data from neo4j and generate the answer
    
    # Task:
    1. Understand the user input
    2. Understand neo4j graph schema
    3. Fetch the data
    4. Generate the Answer
    
    <Neo4j_schema>  {get_graph_schema()} </Neo4j_Schema>
    
    <Output_Format>Text </Output_Format>
    
    <Rules>
    1. Don't explain the answer
    2. If you don't have the context for the answer inform user do you have context for the answer.
    3. Don't provide Neo4j Cypher query
    4. Don't provide empty response
    </Rules>
    """
    response = llm_with_tools.invoke(
        [SystemMessage(content=system_prompt)] + state["messages"]
    )

    return {
        "response": response.content,
    }


def process_ai_response_node(state: ChatbotState):
    user_prompt = state["response"]
    return {"messages": [AIMessage(content=user_prompt)]}


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


_tool_node = ToolNode(tools=_tools)
_graph = StateGraph(ChatbotState)

_graph.add_node("process_user_node", process_user_node)
_graph.add_node("process_ai_response_node", process_ai_response_node)

_graph.add_node("chatbot", _chatbot_node)
_graph.add_node("tool_node", _tool_node)

_graph.set_entry_point("process_user_node")
_graph.add_edge("process_user_node", "chatbot")
_graph.add_edge("chatbot", "process_ai_response_node")
_graph.add_conditional_edges("process_ai_response_node", _tools_router)
_graph.add_edge("tool_node", "chatbot")

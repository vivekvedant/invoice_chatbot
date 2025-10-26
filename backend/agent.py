from langchain_neo4j import Neo4jGraph
import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from langgraph.graph import add_messages, StateGraph, END
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode


load_dotenv()


@tool
def run_cypher_query(query: str):
    """
    Runs neo4j cypher query

    Args:
        query (str): Neo4j cypher query

    Returns:
        str: result of the cypher query
    """
    print(query)
    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        enhanced_schema=True,
    )
    # print(graph.schema)
    return f"""<toolcallresponse>{graph.query(query=query)}</toolcallresponse>"""


def get_graph_schema():
    graph = Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD"),
        enhanced_schema=True,
    )
    return graph.schema


tools = [run_cypher_query]


class BasicChatBot(TypedDict):
    messages: Annotated[list, add_messages]
    # messages: list[str]


llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")

llm_with_tools = llm.bind_tools(tools=tools)


def chatbot(state: BasicChatBot):
    return {
        "messages": [llm_with_tools.invoke(state["messages"])],
    }


def tools_router(state: BasicChatBot):
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tool_node"
    else:
        return END


tool_node = ToolNode(tools=tools)

graph = StateGraph(BasicChatBot)

graph.add_node("chatbot", chatbot)
graph.add_node("tool_node", tool_node)
graph.set_entry_point("chatbot")

graph.add_conditional_edges("chatbot", tools_router)
graph.add_edge("tool_node", "chatbot")

app = graph.compile()


# system_prompt = """
# neo4j graph schema: {graph_schema}
# """.format(graph_schema = get_graph_schema())


# while True:
#     user_input = input("\nUser: ")
#     if user_input in ["exit", "end"]:
#         break
#     else:
#         for message_chunk, metadata in app.stream({"messages": [AIMessage(content = system_prompt),HumanMessage(content=user_input)]},
#             stream_mode="messages",
#         ):
#             if message_chunk.content:
#                 print(message_chunk.content, end="|", flush=True)


# print(get_graph_schema())

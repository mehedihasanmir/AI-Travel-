from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from tools import TRAVEL_TOOLS

llm = ChatOpenAI(model="gpt-4.1", temperature=0.5)
llm_with_tools = llm.bind_tools(TRAVEL_TOOLS)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


sys_msg = SystemMessage(
    content=(
        "You are an expert AI Travel Agent. Your goal is to help users plan amazing trips by "
        "checking weather, finding hotels, discovering local spots, searching the web, and providing map views. "
        "If the user asks for a trip plan, hitlist, itinerary getaway, or itinerary, you must use "
        "the generate_trip_plan tool. When generate_trip_plan returns JSON, output that exact JSON "
        "as your final response (optionally in a json code block), and do not summarize it. "
        "Use duckduckgo_web_search for broad web questions and google_places_search for place discovery."
    )
)


def agent_node(state: AgentState):
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(TRAVEL_TOOLS))
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

app = workflow.compile(checkpointer=MemorySaver())

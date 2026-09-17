"""
agent/graph.py
--------------
LangGraph StateGraph — the core reasoning loop for the agent.

Topology:
  START → agent_node → (tool_calls present?) → tool_node → agent_node (loop)
                     → (no tool_calls)        → END

Persistence:
  MemorySaver checkpointer keyed by thread_id — full conversation state
  survives across Streamlit reruns within the same session.
"""

import os
import pathlib

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.prompts import SYSTEM_PROMPT
from agent.state import AgentState
from agent.tools import ALL_TOOLS, flush_pending_side_effects

# Always load .env from the project root (parent of the agent/ folder)
_ENV_PATH = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)


def _build_llm_with_tools():
    """
    Instantiate a fresh Gemini LLM bound to all tools.
    Called once per graph compilation — NOT cached, to ensure the API key
    is always read fresh from the environment.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Please add it to your .env file and restart."
        )
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_output_tokens=2048,
        google_api_key=api_key,
    )
    return llm.bind_tools(ALL_TOOLS)


# ─────────────────────────────────────────────────────────────────────────────
# Nodes
# ─────────────────────────────────────────────────────────────────────────────

def agent_node(state: AgentState, llm_with_tools) -> dict:
    """
    Main reasoning node.
    Prepends the system prompt, invokes the LLM, returns the AIMessage.
    Also flushes any side effects accumulated by tool calls in the previous cycle.
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)

    # Flush state side-effects recorded by tool functions during this cycle
    side_effects = flush_pending_side_effects()

    update: dict = {"messages": [response]}
    if side_effects["actions_taken"]:
        update["actions_taken"] = side_effects["actions_taken"]
    if side_effects["action_log"]:
        update["action_log"] = side_effects["action_log"]
    if side_effects["escalated"]:
        update["escalated"] = True
    if "current_customer_ref" in side_effects:
        update["current_customer_ref"] = side_effects["current_customer_ref"]

    return update


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────────────

def create_agent(checkpointer: MemorySaver | None = None):
    """
    Build and compile the LangGraph StateGraph.

    Args:
        checkpointer: Optional MemorySaver. Pass one from the Streamlit session
                      so conversation state persists across reruns.

    Returns:
        Compiled LangGraph runnable (supports .invoke / .stream).
    """
    llm_with_tools = _build_llm_with_tools()

    # Bind the LLM into the agent node via closure
    def _agent_node(state: AgentState) -> dict:
        return agent_node(state, llm_with_tools)

    tool_node = ToolNode(ALL_TOOLS)
    graph = StateGraph(AgentState)

    graph.add_node("agent", _agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)

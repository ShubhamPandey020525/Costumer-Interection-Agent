"""
agent/state.py
--------------
LangGraph state definition for the Airline Disruption Resolution Agent.

Uses TypedDict with explicit reducers so that multiple tool calls in a single
agent loop can accumulate into lists without clobbering each other.
"""

import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Shared state threaded through every node of the LangGraph.

    Fields
    ------
    messages:
        Full conversation (HumanMessage, AIMessage, ToolMessage).
        Uses the LangGraph `add_messages` reducer — appends, never overwrites.
    actions_taken:
        Short human-readable labels for each action the agent has executed.
        Used to render action badges in the Streamlit UI.
        Reducer: list concatenation (append-only).
    action_log:
        Structured audit trail — each entry is a dict with keys:
            action      : str  — machine-readable action type constant
            details     : str  — human-readable description
            policy      : str  — policy rule that was applied
            timestamp   : str  — HH:MM:SS timestamp
        Reducer: list concatenation (append-only).
    escalated:
        True once the case has been handed to a human supervisor.
        No reducer — last write wins (only ever written True by escalate tool).
    current_customer_ref:
        Booking reference of the verified customer.
        No reducer — last write wins (only the lookup tool writes this).
    """

    messages: Annotated[list, add_messages]
    actions_taken: Annotated[list, operator.add]
    action_log: Annotated[list, operator.add]
    escalated: bool
    current_customer_ref: Optional[str]

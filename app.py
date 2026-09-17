"""
app.py
------
Streamlit UI for the SkyConnect Airlines Disruption Resolution Agent.

Layout:
  Sidebar  : Scenario presets | Dynamic PNR dropdown | Customer info card | Action & Decision Log
  Main     : System header | Chat window | Chat input
"""

import os
import uuid
import pathlib

# Load .env from the same directory as this file — works regardless of CWD
_ENV_PATH = pathlib.Path(__file__).parent / ".env"

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agent.graph import create_agent
from core.db_manager import get_booking_by_pnr, get_all_pnrs

load_dotenv(dotenv_path=_ENV_PATH, override=True)

st.set_page_config(
    page_title="SkyConnect | Disruption Resolution Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

#MainMenu, footer, header { display: none !important; }
.stDeployButton { display: none !important; }
div[data-testid="stDecoration"] { display: none !important; }

.stApp { background: #0d1117 !important; }

[data-testid="stSidebar"] {
    background: #161b22 !important;
    border-right: 1px solid #21262d !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 1rem 1rem 1rem 1rem; }

.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.25rem;
    background: #161b22;
    border-bottom: 1px solid #21262d;
    border-radius: 12px;
    margin-bottom: 1.25rem;
}
.app-logo { display: flex; align-items: center; gap: 0.6rem; }
.app-logo-icon { font-size: 1.6rem; }
.app-title-main {
    font-size: 1.1rem;
    font-weight: 800;
    color: #e6edf3;
    letter-spacing: -0.03em;
    line-height: 1.2;
}
.app-title-sub {
    font-size: 0.7rem;
    color: #8b949e;
    font-weight: 400;
    letter-spacing: 0.02em;
}
.clock-badge {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: #1c2333;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 0.35rem 0.9rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #c9d1d9;
}
.clock-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #3fb950;
    animation: blink 2s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.35} }

.scenario-section-title {
    font-size: 0.65rem;
    font-weight: 700;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.6rem;
}
.stButton > button {
    background: #1c2333 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #c9d1d9 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 0.8rem !important;
    width: 100% !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
    margin-bottom: 0.3rem !important;
}
.stButton > button:hover {
    background: #21262d !important;
    border-color: #58a6ff !important;
    color: #58a6ff !important;
}

.customer-card {
    background: #1c2333;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    margin: 1rem 0;
}
.customer-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
}
.customer-name {
    font-size: 0.9rem;
    font-weight: 700;
    color: #e6edf3;
}
.tier-badge {
    padding: 0.15rem 0.55rem;
    border-radius: 20px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.tier-gold   { background: #d2992225; color: #e3b341; border: 1px solid #d2992250; }
.tier-silver { background: #8b949e25; color: #8b949e; border: 1px solid #8b949e50; }
.tier-platinum { background: #58a6ff25; color: #79c0ff; border: 1px solid #58a6ff50; }
.tier-standard { background: #30363d50; color: #c9d1d9; border: 1px solid #30363d; }

.info-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.72rem;
    color: #8b949e;
    padding: 0.2rem 0;
    border-bottom: 1px solid #21262d;
}
.info-row:last-child { border-bottom: none; }
.info-label { color: #8b949e; }
.info-value { color: #c9d1d9; font-weight: 500; }

.flight-pill {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 0.4rem 0.6rem;
    margin-top: 0.5rem;
    font-size: 0.7rem;
}
.flight-pill-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.2rem;
}
.flight-number { font-weight: 700; color: #e6edf3; }
.flight-status-cancelled { color: #f85149; font-weight: 600; }
.flight-status-delayed   { color: #d29922; font-weight: 600; }
.flight-status-ok        { color: #3fb950; font-weight: 600; }
.flight-status-rebooked  { color: #a371f7; font-weight: 600; }
.flight-status-refund    { color: #58a6ff; font-weight: 600; }
.flight-route { color: #8b949e; }

.log-title {
    font-size: 0.65rem;
    font-weight: 700;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin: 1rem 0 0.6rem 0;
}
.log-item {
    display: flex;
    gap: 0.6rem;
    padding: 0.45rem 0;
    border-bottom: 1px solid #21262d;
}
.log-item:last-child { border-bottom: none; }
.log-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 0.35rem;
}
.dot-verified  { background: #58a6ff; }
.dot-issued    { background: #3fb950; }
.dot-rebooked  { background: #a371f7; }
.dot-refund    { background: #79c0ff; }
.dot-escalated { background: #f85149; }
.dot-default   { background: #8b949e; }
.log-body { flex: 1; }
.log-action  { font-size: 0.72rem; font-weight: 600; color: #e6edf3; }
.log-detail  { font-size: 0.68rem; color: #8b949e; margin-top: 0.1rem; }
.log-policy  { font-size: 0.62rem; color: #58a6ff; margin-top: 0.1rem; }
.log-time    { font-size: 0.6rem; color: #484f58; margin-top: 0.15rem; }

[data-testid="stChatMessage"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
    padding: 0.75rem 1rem !important;
    margin-bottom: 0.5rem !important;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    border-color: #388bfd30 !important;
}

.badge-row { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.6rem; }
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.18rem 0.55rem;
    border-radius: 20px;
    font-size: 0.67rem;
    font-weight: 600;
}
.badge-success   { background: #3fb95020; color: #3fb950; border: 1px solid #3fb95050; }
.badge-warning   { background: #d2992225; color: #e3b341; border: 1px solid #d2992260; }
.badge-escalated { background: #f8514920; color: #f85149; border: 1px solid #f8514960; }
.badge-info      { background: #58a6ff20; color: #79c0ff; border: 1px solid #58a6ff50; }

.empty-state {
    text-align: center;
    padding: 3rem 1.5rem;
    color: #484f58;
}
.empty-icon { font-size: 3rem; margin-bottom: 0.75rem; }
.empty-title { font-size: 1rem; font-weight: 600; color: #8b949e; margin-bottom: 0.4rem; }
.empty-sub { font-size: 0.8rem; color: #484f58; }

.escalation-banner {
    background: #f8514915;
    border: 1px solid #f8514940;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-size: 0.78rem;
    color: #f85149;
    font-weight: 500;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

[data-testid="stChatInput"] {
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
    background: #1c2333 !important;
}
[data-testid="stChatInput"] textarea {
    color: #c9d1d9 !important;
    background: transparent !important;
}
</style>
"""

SCENARIOS = [
    {
        "label": "✈ Scenario 1 — Priya Nair (Gold)",
        "subtitle": "Cancelled flight · Demands upgrade",
        "message": (
            "Hi, my booking reference is SK4821X. My flight SK-204 from Delhi to Goa "
            "has been cancelled and I'm absolutely furious! I want a full cash refund "
            "AND a free upgrade to business class on my return flight for all this trouble!"
        ),
    },
    {
        "label": "✈ Scenario 2 — Arvind Kulkarni (Silver)",
        "subtitle": "4-hour delay · Asks for hotel",
        "message": (
            "Hello, my PNR is TR1190B. My flight SK-118 from Mumbai to Bengaluru is "
            "delayed by 4 hours and I'm going to miss an important business meeting. "
            "I need hotel accommodation arranged — it's been such a long delay!"
        ),
    },
    {
        "label": "✈ Scenario 3 — Meher Kaur (Platinum)",
        "subtitle": "6-hour delay · Full-night hotel + ₹2k fare diff",
        "message": (
            "Hi, my booking reference is WL7742. My flight SK-305 from Delhi to "
            "Hyderabad is delayed by 6 hours! I need a full night's hotel stay, and I "
            "also want to be moved to an earlier flight — I'm told the fare difference "
            "is ₹2,000 but I expect the airline to cover that completely."
        ),
    },
]

BADGE_MAP = {
    "CUSTOMER_VERIFIED":        ("ℹ Booking Verified",          "info"),
    "DELAY_COMPENSATION_ISSUED":("✓ Compensation Applied",      "success"),
    "REFUND_INITIATED":         ("✓ Refund Initiated",          "success"),
    "FLIGHT_REBOOKED":          ("✓ Flight Rebooked",           "success"),
    "ESCALATED":                ("⚠ Transferred to Human Agent","escalated"),
}

LOG_DOT_MAP = {
    "CUSTOMER_VERIFIED":        "dot-verified",
    "DELAY_COMPENSATION_ISSUED":"dot-issued",
    "REFUND_INITIATED":         "dot-refund",
    "FLIGHT_REBOOKED":          "dot-rebooked",
    "ESCALATED":                "dot-escalated",
}

def _init_session():
    if "checkpointer" not in st.session_state:
        st.session_state.checkpointer = MemorySaver()
    if "graph" not in st.session_state:
        try:
            st.session_state.graph = create_agent(
                checkpointer=st.session_state.checkpointer
            )
        except RuntimeError as e:
            st.error(f"❌ {e}")
            st.stop()
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "display_messages" not in st.session_state:
        st.session_state.display_messages = []
    if "ui_action_log" not in st.session_state:
        st.session_state.ui_action_log = []
    if "current_pnr" not in st.session_state:
        st.session_state.current_pnr = None
    if "escalated" not in st.session_state:
        st.session_state.escalated = False

def _reset_conversation():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.display_messages = []
    st.session_state.ui_action_log = []
    st.session_state.current_pnr = None
    st.session_state.escalated = False

def _invoke_agent(user_input: str):
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    prev_log_len = len(st.session_state.ui_action_log)

    try:
        result = st.session_state.graph.invoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "actions_taken": [],
                "action_log": [],
                "escalated": False,
                "current_customer_ref": st.session_state.current_pnr,
            },
            config=config,
        )
    except Exception as e:
        err = str(e)
        # Surface a clean error to the UI without crashing
        st.error(f"Agent error: {err}")
        return f"I'm sorry, I encountered an error: {err}", [], False

    final_ai_msg = None
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", []):
            final_ai_msg = msg
            break

    response_text = ""
    if final_ai_msg:
        if isinstance(final_ai_msg.content, str):
            response_text = final_ai_msg.content
        elif isinstance(final_ai_msg.content, list):
            texts = []
            for item in final_ai_msg.content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
                elif isinstance(item, str):
                    texts.append(item)
            response_text = "\n".join(texts)
    else:
        response_text = "I'm processing your request…"

    full_log: list = result.get("action_log") or []
    st.session_state.ui_action_log = full_log
    new_entries = full_log[prev_log_len:]

    if result.get("escalated"):
        st.session_state.escalated = True

    ref = result.get("current_customer_ref")
    if ref:
        st.session_state.current_pnr = ref

    return response_text, new_entries, st.session_state.escalated

def _render_badges(entries: list[dict]) -> str:
    if not entries:
        return ""
    pills = []
    for entry in entries:
        label, css_class = BADGE_MAP.get(
            entry.get("action", ""), (entry.get("action", "Action"), "info")
        )
        pills.append(f'<span class="badge badge-{css_class}">{label}</span>')
    return f'<div class="badge-row">{"".join(pills)}</div>'

def _render_customer_card(pnr: str):
    info = get_booking_by_pnr(pnr)
    if not info:
        return

    tier = info["loyalty_tier"].lower()
    tier_css = f"tier-{tier}"

    flight_html = ""
    for b in info.get("bookings", []):
        status_lower = b["status"].lower()
        if "cancel" in status_lower:
            status_css, status_icon = "flight-status-cancelled", "✕ Cancelled"
        elif "delay" in status_lower:
            status_css, status_icon = "flight-status-delayed", f"⏱ Delayed +{b.get('delay_hours','?')}h"
        elif "rebook" in status_lower:
            status_css, status_icon = "flight-status-rebooked", "🔄 Rebooked"
        elif "refund" in status_lower:
            status_css, status_icon = "flight-status-refund", "💸 Refund Initiated"
        else:
            status_css, status_icon = "flight-status-ok", "✓ On Time"

        flight_html += f"""
        <div class="flight-pill">
            <div class="flight-pill-header">
                <span class="flight-number">{b['flight_id']}</span>
                <span class="{status_css}">{status_icon}</span>
            </div>
            <div class="flight-route">{b['route']} &bull; {b['scheduled_departure']}</div>
        </div>"""

    complaints = info.get("travel_history", {}).get("prior_complaints", [])
    complaint_label = f"{len(complaints)} prior" if complaints else "None"
    
    compensation = info.get("compensation_applied", [])
    comp_label = f"{len(compensation)} items" if compensation else "None"

    html = f"""
    <div class="customer-card">
        <div class="customer-card-header">
            <span class="customer-name">{info['name']}</span>
            <span class="tier-badge {tier_css}">{info['loyalty_tier']}</span>
        </div>
        <div class="info-row">
            <span class="info-label">PNR</span>
            <span class="info-value">{info['pnr']}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Email</span>
            <span class="info-value">{info['email']}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Flights (12m)</span>
            <span class="info-value">{info.get('travel_history', {}).get('flights_last_12_months', 0)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Complaints</span>
            <span class="info-value">{complaint_label}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Compensation</span>
            <span class="info-value">{comp_label}</span>
        </div>
        {flight_html}
    </div>"""

    st.markdown(html, unsafe_allow_html=True)

def _render_action_log():
    log = st.session_state.ui_action_log
    if not log:
        return

    items_html = ""
    for entry in reversed(log):
        action = entry.get("action", "ACTION")
        dot_css = LOG_DOT_MAP.get(action, "dot-default")
        items_html += f"""
        <div class="log-item">
            <div class="log-dot {dot_css}"></div>
            <div class="log-body">
                <div class="log-action">{action.replace("_", " ").title()}</div>
                <div class="log-detail">{entry.get('details', '')}</div>
                <div class="log-policy">{entry.get('policy', '')}</div>
                <div class="log-time">{entry.get('timestamp', '')}</div>
            </div>
        </div>"""

    st.markdown(
        f'<div class="log-title">Action &amp; Decision Log</div>'
        f'<div class="log-container">{items_html}</div>',
        unsafe_allow_html=True,
    )

def main():
    _init_session()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div class="scenario-section-title">Test Scenarios (Mandatory)</div>', unsafe_allow_html=True)

        for i, scenario in enumerate(SCENARIOS):
            if st.button(scenario["label"], key=f"scenario_{i}", help=scenario["subtitle"], use_container_width=True):
                _reset_conversation()
                st.session_state.display_messages.append({"role": "user", "content": scenario["message"], "badges": []})
                response_text, new_entries, escalated = _invoke_agent(scenario["message"])
                badges_html = _render_badges(new_entries)
                st.session_state.display_messages.append({"role": "assistant", "content": response_text, "badges_html": badges_html})
                st.rerun()

        st.divider()
        
        st.markdown('<div class="scenario-section-title">Synthetic Database testing</div>', unsafe_allow_html=True)
        all_pnrs = get_all_pnrs()
        selected_pnr = st.selectbox("Select any PNR to test (50 total):", options=["Select a PNR..."] + all_pnrs)
        
        if selected_pnr and selected_pnr != "Select a PNR...":
            if st.button(f"Load PNR {selected_pnr}", use_container_width=True):
                 _reset_conversation()
                 msg = f"Hi, my PNR is {selected_pnr}. What is the status of my flight?"
                 st.session_state.display_messages.append({"role": "user", "content": msg, "badges": []})
                 response_text, new_entries, escalated = _invoke_agent(msg)
                 badges_html = _render_badges(new_entries)
                 st.session_state.display_messages.append({"role": "assistant", "content": response_text, "badges_html": badges_html})
                 st.rerun()

        st.divider()

        if st.session_state.current_pnr:
            st.markdown('<div class="scenario-section-title">Active Customer</div>', unsafe_allow_html=True)
            _render_customer_card(st.session_state.current_pnr)
        else:
            st.markdown(
                '<div style="font-size:0.72rem;color:#484f58;text-align:center;padding:1rem 0;">'
                "Customer info appears here after verification."
                "</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        _render_action_log()

        if st.session_state.display_messages:
            st.divider()
            if st.button("🔄 New Conversation", use_container_width=True):
                _reset_conversation()
                st.rerun()

    st.markdown(
        """
        <div class="app-header">
            <div class="app-logo">
                <span class="app-logo-icon">✈️</span>
                <div>
                    <div class="app-title-main">SkyConnect Airlines</div>
                    <div class="app-title-sub">Disruption Resolution Agent · Powered by LangGraph + Gemini</div>
                </div>
            </div>
            <div class="clock-badge">
                <div class="clock-dot"></div>
                Wed, 23 Sep 2026
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.escalated:
        st.markdown(
            '<div class="escalation-banner">'
            "⚠️ This chat is being transferred to a human agent. "
            "Please hold on while they review your details to assist you further."
            "</div>",
            unsafe_allow_html=True,
        )

    if not st.session_state.display_messages:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">✈️</div>
                <div class="empty-title">SkyConnect Resolution Agent</div>
                <div class="empty-sub">
                    Select a scenario from the sidebar or type your query below.<br>
                    The agent will verify your identity and resolve your disruption.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.display_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                badges_html = msg.get("badges_html", "")
                if badges_html:
                    st.markdown(badges_html, unsafe_allow_html=True)

    user_input = st.chat_input("Type your message here…", disabled=st.session_state.escalated)

    if user_input:
        st.session_state.display_messages.append({"role": "user", "content": user_input, "badges_html": ""})
        with st.spinner("Agent is processing…"):
            response_text, new_entries, escalated = _invoke_agent(user_input)

        badges_html = _render_badges(new_entries)
        st.session_state.display_messages.append({"role": "assistant", "content": response_text, "badges_html": badges_html})
        st.rerun()

if __name__ == "__main__":
    main()

"""
agent/tools.py
--------------
Five LangChain tools for the Airline Disruption Resolution Agent.

Architecture note:
  Each tool returns a plain string (tool result) that goes back to the LLM.
  State side-effects (action_log, actions_taken, escalated, current_customer_ref)
  are stored in a thread-safe module-level list and flushed by the agent node
  after every tool execution cycle. This is the correct pattern for LangGraph 1.x
  where ToolNode does not accept Command returns from @tool-decorated functions.
"""

import datetime
import threading
from typing import Annotated

from langchain_core.tools import tool, InjectedToolCallId

from core.data import get_delay_compensation
from core.db_manager import get_booking_by_pnr, update_booking_status, update_customer_record

# ---------------------------------------------------------------------------
# Thread-safe side-effect store
# Collects state updates produced during a tool call so the agent node
# can flush them into LangGraph state after execution.
# ---------------------------------------------------------------------------
_side_effects_lock = threading.Lock()
_pending_actions_taken: list = []
_pending_action_log: list = []
_pending_escalated: bool = False
_pending_customer_ref: str | None = None


def _reset_pending():
    global _pending_actions_taken, _pending_action_log, _pending_escalated, _pending_customer_ref
    _pending_actions_taken = []
    _pending_action_log = []
    _pending_escalated = False
    _pending_customer_ref = None


def flush_pending_side_effects() -> dict:
    """
    Called by the agent node after tool execution to collect and reset
    all pending state updates from tool calls.
    Returns a dict suitable for merging into the AgentState update.
    """
    with _side_effects_lock:
        result = {
            "actions_taken": list(_pending_actions_taken),
            "action_log": list(_pending_action_log),
            "escalated": _pending_escalated,
        }
        if _pending_customer_ref is not None:
            result["current_customer_ref"] = _pending_customer_ref
        _reset_pending()
    return result


def _record(action_taken: str, log_entry: dict, escalated: bool = False, customer_ref: str | None = None):
    global _pending_escalated, _pending_customer_ref
    with _side_effects_lock:
        _pending_actions_taken.append(action_taken)
        _pending_action_log.append(log_entry)
        if escalated:
            _pending_escalated = True
        if customer_ref is not None:
            _pending_customer_ref = customer_ref


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _log_entry(action: str, details: str, policy: str) -> dict:
    return {
        "action": action,
        "details": details,
        "policy": policy,
        "timestamp": _now(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — lookup_customer_booking
# ─────────────────────────────────────────────────────────────────────────────

@tool
def lookup_customer_booking(booking_ref: str) -> str:
    """
    Look up a customer's profile and all flight bookings using their booking reference.
    Must be called FIRST before taking any action on behalf of a customer.

    Args:
        booking_ref: The customer's booking reference / PNR (e.g. SK4821X).
    """
    ref = booking_ref.strip().upper()
    customer = get_booking_by_pnr(ref)

    if not customer:
        return f"BOOKING NOT FOUND: No record found for reference '{ref}'. Please ask the customer to double-check their PNR."

    bookings = customer.get("bookings", [])

    flight_lines: list[str] = []
    for b in bookings:
        line = f"  • {b['flight_id']} | {b['route']} | {b['date']} {b['scheduled_departure']} | Status: {b['status']}"
        if b.get("status_reason"):
            line += f" ({b['status_reason']})"
        if b.get("delay_hours"):
            line += f" — delayed {b['delay_hours']}h, new departure {b['new_departure']}"
        flight_lines.append(line)

    complaints = customer.get("travel_history", {}).get("prior_complaints", [])
    complaint_str = (
        "; ".join(f"{c['issue']} → {c['resolution']}" for c in complaints)
        if complaints else "None"
    )

    content = (
        f"CUSTOMER VERIFIED\n"
        f"Name         : {customer['name']}\n"
        f"Loyalty Tier : {customer['loyalty_tier']}\n"
        f"Booking Ref  : {ref}\n"
        f"Email        : {customer['email']}\n"
        f"Phone        : {customer['phone']}\n\n"
        f"Flights:\n" + "\n".join(flight_lines) + "\n\n"
        f"Travel History (12 months): {customer.get('travel_history', {}).get('flights_last_12_months', 0)} flights\n"
        f"Prior Complaints: {complaint_str}\n"
        f"Compensation Applied: {', '.join(customer.get('compensation_applied', [])) or 'None'}\n"
        f"Escalated: {customer.get('escalated', False)}"
    )

    _record(
        action_taken=f"Booking verified: {customer['name']} ({ref})",
        log_entry=_log_entry(
            action="CUSTOMER_VERIFIED",
            details=f"{customer['name']} ({customer['loyalty_tier']} tier) — ref {ref}",
            policy="Identity verification (required before any action)",
        ),
        customer_ref=ref,
    )
    return content


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — apply_delay_compensation
# ─────────────────────────────────────────────────────────────────────────────

@tool
def apply_delay_compensation(booking_ref: str) -> str:
    """
    Apply the correct delay compensation to a customer's booking based on the delay duration.
    Automatically selects the right tier per policy and updates the database.

    Args:
        booking_ref: The customer's booking reference / PNR.
    """
    ref = booking_ref.strip().upper()
    customer = get_booking_by_pnr(ref)
    if not customer:
        return f"ERROR: Booking not found for reference '{ref}'. Cannot apply compensation."

    bookings = customer.get("bookings", [])
    delayed = next((b for b in bookings if b.get("delay_hours")), None)

    if not delayed:
        return f"ERROR: No delayed flight found for booking {ref}. Delay compensation cannot be applied."

    hours = delayed["delay_hours"]
    tier_label, compensation_items = get_delay_compensation(hours)
    comp_str = ", ".join(compensation_items)

    update_customer_record(ref, {"compensation_applied": compensation_items})

    hotel_note = ""
    if hours > 5:
        hotel_note = (
            f"\n\nIMPORTANT POLICY NOTE: Hotel accommodation covers ONLY the delayed hours "
            f"(approximately {hours} hours), NOT a full night's stay. "
            "If the customer requests a full night's hotel stay, that must be declined per policy."
        )

    content = (
        f"DELAY COMPENSATION APPLIED (Database Updated)\n"
        f"Flight        : {delayed['flight_id']} ({delayed['route']})\n"
        f"Scheduled     : {delayed['scheduled_departure']} → New departure: {delayed['new_departure']}\n"
        f"Delay         : {hours} hours\n"
        f"Policy tier   : {tier_label}\n"
        f"Compensation  : {comp_str}\n"
        f"Status        : Issued to booking {ref}"
        f"{hotel_note}"
    )

    _record(
        action_taken=f"Compensation issued: {comp_str}",
        log_entry=_log_entry(
            action="DELAY_COMPENSATION_ISSUED",
            details=f"Flight {delayed['flight_id']} delayed {hours}h. Applied: {comp_str}",
            policy=f"Delay Compensation Rule — {tier_label}",
        ),
    )
    return content


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3 — initiate_refund
# ─────────────────────────────────────────────────────────────────────────────

@tool
def initiate_refund(booking_ref: str) -> str:
    """
    Initiate a full refund for an airline-caused flight cancellation.
    Updates the flight status in the database to 'Refund Initiated'.

    Args:
        booking_ref: The customer's booking reference / PNR.
    """
    ref = booking_ref.strip().upper()
    customer = get_booking_by_pnr(ref)
    if not customer:
        return f"ERROR: Booking not found for reference '{ref}'. Cannot initiate refund."

    bookings = customer.get("bookings", [])
    cancelled = next(
        (b for b in bookings if b.get("status", "").lower() in ("cancelled", "refund initiated")),
        None
    )

    if not cancelled:
        return f"ERROR: No cancelled flight found for booking {ref}. Refund can only be initiated for airline-caused cancellations."

    update_booking_status(
        ref, cancelled["flight_id"], "Refund Initiated",
        {"status_reason": "Refund requested by customer"}
    )

    content = (
        f"REFUND INITIATED (Database Updated)\n"
        f"Flight        : {cancelled['flight_id']} ({cancelled['route']})\n"
        f"Date          : {cancelled['date']}\n"
        f"Reason        : Airline-caused cancellation\n"
        f"Refund amount : Full fare (100%)\n"
        f"Timeline      : 7 business days\n"
        f"Payment method: Original payment method on file ONLY\n\n"
        f"A confirmation will be sent to the registered email address."
    )

    _record(
        action_taken=f"Full refund initiated for {cancelled['flight_id']}",
        log_entry=_log_entry(
            action="REFUND_INITIATED",
            details=f"Full refund for {cancelled['flight_id']} ({ref}). 7 business days to original method.",
            policy="Refund Processing Rule + Cancellation Rebooking Rule",
        ),
    )
    return content


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4 — rebook_on_next_flight
# ─────────────────────────────────────────────────────────────────────────────

@tool
def rebook_on_next_flight(booking_ref: str) -> str:
    """
    Rebook a customer on the next available flight at no charge for airline-caused cancellations.
    Updates the flight status in the database to 'Rebooked'.

    Args:
        booking_ref: The customer's booking reference / PNR.
    """
    ref = booking_ref.strip().upper()
    customer = get_booking_by_pnr(ref)
    if not customer:
        return f"ERROR: Booking not found for reference '{ref}'. Cannot rebook."

    bookings = customer.get("bookings", [])
    cancelled = next(
        (b for b in bookings if b.get("status", "").lower() in ("cancelled", "rebooked")),
        None
    )

    if not cancelled:
        return f"ERROR: No cancelled flight found for booking {ref}. Rebooking is only available for airline-caused cancellations."

    tier = customer.get("loyalty_tier", "Standard")
    priority_note = ""
    if tier in ("Gold", "Platinum"):
        priority_note = f"\nPRIORITY REBOOKING: {tier} status — customer gets first access to available seats."

    update_booking_status(
        ref, cancelled["flight_id"], "Rebooked",
        {"status_reason": "Rebooked due to cancellation", "new_departure": "Next available flight"}
    )

    content = (
        f"FLIGHT REBOOKED (Database Updated)\n"
        f"Original flight  : {cancelled['flight_id']} ({cancelled['route']})\n"
        f"Original date    : {cancelled['date']} at {cancelled['scheduled_departure']}\n"
        f"New flight       : Next available departure within 24 hours\n"
        f"New booking ref  : {ref} (same reference, updated)\n"
        f"Fare difference  : None — no charge to customer\n"
        f"Status           : Confirmed{priority_note}\n\n"
        f"A confirmation with the new flight details will be sent to the registered email."
    )

    _record(
        action_taken=f"Rebooked: {cancelled['flight_id']} ({ref})",
        log_entry=_log_entry(
            action="FLIGHT_REBOOKED",
            details=f"{customer['name']} rebooked for {cancelled['route']}. Priority: {tier in ('Gold', 'Platinum')}.",
            policy="Cancellation Rebooking Rule + Loyalty Tier Rule",
        ),
    )
    return content


# ─────────────────────────────────────────────────────────────────────────────
# Tool 5 — escalate_to_supervisor
# ─────────────────────────────────────────────────────────────────────────────

@tool
def escalate_to_supervisor(reason: str, booking_ref: str) -> str:
    """
    Escalate the case to a human supervisor immediately.
    Call this for any prohibited request: legal threats, fare diff > Rs 1500,
    upgrade requests, refund to different payment method, extra compensation.
    Flags the customer profile in the database.

    Args:
        reason:      Clear description of why escalation is required.
        booking_ref: The customer's booking reference / PNR.
    """
    ref = booking_ref.strip().upper()
    customer = get_booking_by_pnr(ref)

    name = customer["name"] if customer else "Customer"

    if customer:
        update_customer_record(ref, {"escalated": True})

    esc_ref = f"ESC-{ref}-{_now().replace(':', '')}"

    content = (
        f"ESCALATED TO SPECIALIST SUPPORT TEAM (Database Flagged)\n\n"
        f"Customer      : {name} ({ref})\n"
        f"Reason        : {reason}\n"
        f"Escalation Ref: {esc_ref}\n\n"
        f"The case has been transferred to the specialist support team. "
        f"A senior agent will contact the customer directly."
    )

    _record(
        action_taken=f"⚠ Escalated: {reason[:60]}",
        log_entry=_log_entry(
            action="ESCALATED",
            details=f"Escalated for: {reason}. Ref: {esc_ref}",
            policy="Agent Authority — Mandatory Escalation Trigger",
        ),
        escalated=True,
    )
    return content


ALL_TOOLS = [
    lookup_customer_booking,
    apply_delay_compensation,
    initiate_refund,
    rebook_on_next_flight,
    escalate_to_supervisor,
]

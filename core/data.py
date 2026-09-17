"""
core/data.py
------------
SOURCE OF TRUTH — Business policies verbatim from:
  "Data Pack — Assignment 3: Customer-Facing Resolution Agent (Airline Disruption)"
Exercise date: Wednesday, 23 September 2026.

DO NOT add, invent, or modify any policy data.
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. SERVICE RULES / POLICIES
# ─────────────────────────────────────────────────────────────────────────────

POLICIES: dict = {
    "cancellation_rebooking": {
        "description": (
            "If a flight is cancelled by the airline, the customer is entitled to a "
            "free rebooking on the next available flight within 24 hours, or a full "
            "refund — customer's choice."
        ),
    },
    "delay_compensation": {
        "tiers": [
            {
                "label": "Under 3 hours",
                "min_hours_exclusive": 0,
                "max_hours_inclusive": 3,
                "compensation": ["₹500 meal voucher"],
            },
            {
                "label": "More than 3 hours",
                "min_hours_exclusive": 3,
                "max_hours_inclusive": 5,
                "compensation": ["Meal voucher", "Lounge access"],
            },
            {
                "label": "More than 5 hours",
                "min_hours_exclusive": 5,
                "max_hours_inclusive": float("inf"),
                "compensation": [
                    "Meal voucher",
                    "Hotel accommodation (covering only the delayed hours — NOT a full night's stay)",
                ],
            },
        ],
    },
    "refund_processing": {
        "description": (
            "Refunds for airline-caused cancellations are processed in full within "
            "7 business days. Refunds are issued to the original payment method ONLY."
        ),
    },
    "fare_difference": {
        "description": (
            "If a customer voluntarily chooses to rebook on a higher-fare flight "
            "(not airline-caused), they must pay the fare difference."
        ),
        "agent_waiver_limit_inr": 1500,  # Above this → supervisor approval required
    },
    "loyalty_tier": {
        "description": (
            "Gold and Platinum tier customers get priority rebooking (first access "
            "to next-available seats) but no additional compensation beyond the "
            "standard policy."
        ),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. AGENT AUTHORITY
# ─────────────────────────────────────────────────────────────────────────────

AGENT_AUTHORITY: dict = {
    "allowed": [
        "Rebook the customer on the next available flight within 24 hours at no charge (airline-caused disruption)",
        "Issue meal vouchers and lounge access per the delay compensation rule",
        "Arrange hotel accommodation for the delayed-hours portion, where the delay qualifies (>5h)",
        "Initiate a refund request for airline-caused cancellations",
        "Provide the customer's own booking and flight status information",
    ],
    "prohibited_must_escalate": [
        "Approving any compensation beyond the stated policy amounts",
        "Waiving a fare difference above ₹1,500",
        "Making exceptions for non-airline-caused disruptions (e.g., customer missed the flight)",
        "Handling threats of legal action or formal complaints — must be escalated immediately",
        "Processing refunds to a different payment method than the original",
    ],
}


def get_delay_compensation(delay_hours: float) -> tuple[str, list[str]]:
    """
    Return (tier_label, list_of_compensation_items) for a given delay in hours.
    Strictly applies the delay_compensation policy from the data pack.
    """
    for tier in POLICIES["delay_compensation"]["tiers"]:
        if tier["min_hours_exclusive"] < delay_hours <= tier["max_hours_inclusive"]:
            return tier["label"], tier["compensation"]
    # Fallback for exactly 0h (no delay)
    return "No delay", []

import sys
sys.path.insert(0, r'c:\Users\pande\Costumer-Interection-Agent')

from core.data import POLICIES, get_delay_compensation
from core.db_manager import get_booking_by_pnr, get_all_pnrs
print("core.data and core.db_manager OK")

from agent.state import AgentState
print("agent.state OK")

from agent.prompts import SYSTEM_PROMPT
print(f"agent.prompts OK — {len(SYSTEM_PROMPT)} chars")

from agent.tools import ALL_TOOLS
print(f"agent.tools OK — {len(ALL_TOOLS)} tools: {[t.name for t in ALL_TOOLS]}")

print()
print("Delay compensation policy checks:")
print("  2h ->", get_delay_compensation(2))
print("  4h ->", get_delay_compensation(4))
print("  6h ->", get_delay_compensation(6))

print()
print("Customer data checks (from DB):")
priya = get_booking_by_pnr("SK4821X")
if priya:
    print("  SK4821X ->", priya["name"], "|", priya["loyalty_tier"])
else:
    print("  SK4821X -> NOT FOUND (Run seed_db.py first!)")
    
arvind = get_booking_by_pnr("TR1190B")
if arvind:
    print("  TR1190B ->", arvind["name"], "| delay_hours:", arvind.get("bookings", [{}])[0].get("delay_hours"))
    
meher = get_booking_by_pnr("WL7742")
if meher:
    print("  WL7742  ->", meher["name"],  "| delay_hours:", meher.get("bookings", [{}])[0].get("delay_hours"))

print(f"Total records in DB: {len(get_all_pnrs())}")

from agent.graph import create_agent
print()
print("agent.graph import OK")

print()
print("ALL CHECKS PASSED")

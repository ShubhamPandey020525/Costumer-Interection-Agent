import json
import os
import threading

# Get absolute path to the database.json at project root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.json")
_lock = threading.Lock()

def _read_db() -> dict:
    if not os.path.exists(DB_PATH):
        return {"customers": {}}
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def _write_db(data: dict) -> None:
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def get_all_pnrs() -> list[str]:
    with _lock:
        data = _read_db()
        return list(data.get("customers", {}).keys())

def get_booking_by_pnr(pnr: str) -> dict | None:
    with _lock:
        data = _read_db()
        return data.get("customers", {}).get(pnr.upper())

def update_booking_status(pnr: str, flight_id: str, new_status: str, details: dict = None) -> bool:
    with _lock:
        data = _read_db()
        customer = data.get("customers", {}).get(pnr.upper())
        if not customer:
            return False
            
        updated = False
        for booking in customer.get("bookings", []):
            if booking.get("flight_id") == flight_id:
                booking["status"] = new_status
                if details:
                    # Update booking with details like new_departure, status_reason etc.
                    for k, v in details.items():
                        booking[k] = v
                updated = True
                
        if updated:
            _write_db(data)
        return updated

def update_customer_record(pnr: str, updates: dict) -> bool:
    with _lock:
        data = _read_db()
        customer = data.get("customers", {}).get(pnr.upper())
        if not customer:
            return False
            
        for k, v in updates.items():
            # If updating list (like compensation_applied), append instead of replace
            if isinstance(customer.get(k), list) and isinstance(v, list):
                 customer[k].extend(v)
            else:
                 customer[k] = v
                 
        _write_db(data)
        return True

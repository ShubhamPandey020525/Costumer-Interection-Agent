import json
import random
import os
import string

# Ensure we're saving to the project root
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")

# Mandatory profiles from Assignment 3
MANDATORY_PROFILES = [
    {
        "pnr": "SK4821X",
        "name": "Priya Nair",
        "loyalty_tier": "Gold",
        "email": "priya.nair@example.com",
        "phone": "+91-98xxxxxxx1",
        "travel_history": {
            "flights_last_12_months": 6,
            "prior_complaints": [
                {"issue": "delayed baggage", "resolution": "resolved with voucher"}
            ]
        },
        "escalated": False,
        "compensation_applied": [],
        "bookings": [
            {
                "flight_id": "SK-204",
                "route": "Delhi → Goa",
                "date": "Wed 23 Sep 2026",
                "scheduled_departure": "18:40",
                "status": "Cancelled",
                "status_reason": "operational reasons",
                "delay_hours": None,
                "new_departure": None
            },
            {
                "flight_id": "Return",
                "route": "Goa → Delhi",
                "date": "Fri 25 Sep 2026",
                "scheduled_departure": "16:20",
                "status": "Unaffected",
                "status_reason": None,
                "delay_hours": None,
                "new_departure": None
            }
        ]
    },
    {
        "pnr": "TR1190B",
        "name": "Arvind Kulkarni",
        "loyalty_tier": "Silver",
        "email": "arvind.kulkarni@example.com",
        "phone": "+91-98xxxxxxx2",
        "travel_history": {
            "flights_last_12_months": 3,
            "prior_complaints": []
        },
        "escalated": False,
        "compensation_applied": [],
        "bookings": [
            {
                "flight_id": "SK-118",
                "route": "Mumbai → Bengaluru",
                "date": "Wed 23 Sep 2026",
                "scheduled_departure": "07:10",
                "status": "Delayed",
                "status_reason": None,
                "delay_hours": 4,
                "new_departure": "11:10"
            }
        ]
    },
    {
        "pnr": "WL7742",
        "name": "Meher Kaur",
        "loyalty_tier": "Platinum",
        "email": "meher.kaur@example.com",
        "phone": "+91-98xxxxxxx3",
        "travel_history": {
            "flights_last_12_months": 10,
            "prior_complaints": [
                {"issue": "overbooking", "resolution": "resolved with a tier-status upgrade"}
            ]
        },
        "escalated": False,
        "compensation_applied": [],
        "bookings": [
            {
                "flight_id": "SK-305",
                "route": "Delhi → Hyderabad",
                "date": "Wed 23 Sep 2026",
                "scheduled_departure": "14:00",
                "status": "Delayed",
                "status_reason": None,
                "delay_hours": 6,
                "new_departure": "20:00"
            }
        ]
    }
]

# Helper data for synthetic generation
FIRST_NAMES = ["Amit", "Sneha", "Rahul", "Pooja", "Vikram", "Neha", "Rohan", "Anjali", "Suresh", "Kavita", "Raj", "Simran"]
LAST_NAMES = ["Sharma", "Patel", "Singh", "Gupta", "Kumar", "Desai", "Reddy", "Iyer", "Jain", "Bose"]
TIERS = ["Standard", "Silver", "Gold", "Platinum"]
ROUTES = ["Delhi → Mumbai", "Mumbai → Delhi", "Bengaluru → Hyderabad", "Chennai → Pune", "Kolkata → Delhi", "Hyderabad → Goa"]
FLIGHTS = ["SK-101", "SK-202", "SK-303", "SK-404", "SK-505", "SK-606"]

def generate_random_pnr():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_random_time():
    h = random.randint(0, 23)
    m = random.choice([0, 15, 30, 45])
    return f"{h:02d}:{m:02d}"

def add_hours_to_time(time_str, hours):
    h, m = map(int, time_str.split(':'))
    new_h = (h + hours) % 24
    return f"{new_h:02d}:{m:02d}"

def generate_synthetic_profile():
    pnr = generate_random_pnr()
    tier = random.choices(TIERS, weights=[50, 30, 15, 5])[0]
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    
    # 50% On Time, 30% Delayed, 20% Cancelled
    status_choice = random.choices(["Unaffected", "Delayed", "Cancelled"], weights=[50, 30, 20])[0]
    
    delay_hours = None
    new_dep = None
    reason = None
    
    sched_dep = generate_random_time()
    
    if status_choice == "Delayed":
        delay_hours = random.choice([1, 2, 3, 4, 5, 6, 8])
        new_dep = add_hours_to_time(sched_dep, delay_hours)
    elif status_choice == "Cancelled":
        reason = random.choice(["operational reasons", "weather conditions", "technical fault"])
        
    booking = {
        "flight_id": random.choice(FLIGHTS),
        "route": random.choice(ROUTES),
        "date": "Wed 23 Sep 2026",
        "scheduled_departure": sched_dep,
        "status": status_choice,
        "status_reason": reason,
        "delay_hours": delay_hours,
        "new_departure": new_dep
    }

    return {
        "pnr": pnr,
        "name": f"{first} {last}",
        "loyalty_tier": tier,
        "email": f"{first.lower()}.{last.lower()}@example.com",
        "phone": f"+91-98{random.randint(1000000, 9999999)}",
        "travel_history": {
            "flights_last_12_months": random.randint(0, 15),
            "prior_complaints": []
        },
        "escalated": False,
        "compensation_applied": [],
        "bookings": [booking]
    }

def main():
    db_data = {
        "customers": {p["pnr"]: p for p in MANDATORY_PROFILES}
    }
    
    # Generate 47 synthetic profiles
    while len(db_data["customers"]) < 50:
        new_prof = generate_synthetic_profile()
        if new_prof["pnr"] not in db_data["customers"]:
            db_data["customers"][new_prof["pnr"]] = new_prof
            
    with open(DB_PATH, 'w') as f:
        json.dump(db_data, f, indent=4)
        
    print(f"✅ Generated database.json with {len(db_data['customers'])} records.")
    print("Mandatory Profiles included: SK4821X, TR1190B, WL7742")

if __name__ == "__main__":
    main()

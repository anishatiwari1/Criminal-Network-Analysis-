"""
Criminal Network Dataset Generator (India)
Generates a synthetic but realistic Indian criminal-network dataset:
Indian names, states, districts and police stations, BNS/IPC sections,
NCRB crime heads and CCTNS-style FIR numbers.

All persons, phone numbers, gangs and incidents are FICTIONAL.
Run:  python generate_dataset.py
"""

import json
import random
import csv
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from india_reference import (
    STATES, LOCALITIES, CRIME_CATALOG, FIR_STATUSES, SEVERITY_BY_CATEGORY,
    NEW_LAWS_EFFECTIVE, build_ps_index, sections_for,
)

random.seed(42)

DATA_START = date(2022, 1, 1)
DATA_END = date(2026, 10, 20)

# ─── Entity Pools ────────────────────────────────────────────────────────────
FIRST_NAMES_M = [
    "Rahul", "Amit", "Suresh", "Rajesh", "Vikram", "Arjun", "Manoj", "Sanjay", "Deepak", "Ravi",
    "Anil", "Ramesh", "Sunil", "Ajay", "Vinod", "Pankaj", "Rakesh", "Mukesh", "Imran", "Salman",
    "Faizan", "Arif", "Harpreet", "Gurpreet", "Jaswinder", "Karthik", "Murugan", "Senthil", "Venkatesh",
    "Srinivas", "Prakash", "Naveen", "Sachin", "Ganesh", "Santosh", "Bablu", "Pappu", "Mohit",
    "Biswajit", "Subhash", "Anirban", "Rohit", "Nitin", "Shafiq", "Joseph", "Thomas", "Bhupinder",
    "Lokesh", "Dilip", "Kishore", "Vijay", "Hemant", "Bhavesh", "Jignesh", "Abhishek",
]
FIRST_NAMES_F = [
    "Priya", "Sunita", "Kavita", "Anjali", "Pooja", "Neha", "Rekha", "Meena", "Lakshmi", "Divya",
    "Shabana", "Rubina", "Harleen", "Simran", "Kamala", "Revathi", "Ananya", "Moumita", "Rina",
    "Sushma", "Geeta", "Jyoti", "Farzana", "Mary", "Bhavna", "Nirmala",
]
SURNAMES_BY_STATE = {
    "Maharashtra": ["Patil", "Jadhav", "Shinde", "Pawar", "Deshmukh", "Kulkarni", "Gaikwad", "Shaikh"],
    "Delhi": ["Sharma", "Gupta", "Malhotra", "Khanna", "Chauhan", "Qureshi", "Arora", "Bansal"],
    "Karnataka": ["Gowda", "Shetty", "Rao", "Hegde", "Naik", "Kumar", "Reddy"],
    "Tamil Nadu": ["Pillai", "Murugan", "Subramanian", "Rajendran", "Krishnan", "Selvam"],
    "West Bengal": ["Das", "Banerjee", "Chatterjee", "Ghosh", "Mondal", "Sarkar", "Mukherjee"],
    "Telangana": ["Reddy", "Rao", "Goud", "Naidu", "Yadav", "Ali"],
    "Uttar Pradesh": ["Yadav", "Mishra", "Tiwari", "Pandey", "Singh", "Shukla", "Ansari", "Verma"],
    "Gujarat": ["Patel", "Shah", "Desai", "Mehta", "Chaudhary", "Parmar", "Solanki"],
    "Rajasthan": ["Rathore", "Meena", "Gurjar", "Shekhawat", "Jain", "Choudhary"],
    "Madhya Pradesh": ["Tiwari", "Chouhan", "Dubey", "Saxena", "Raghuvanshi", "Khan"],
    "Bihar": ["Kumar", "Prasad", "Yadav", "Jha", "Sinha", "Paswan", "Thakur"],
    "Punjab": ["Singh", "Sandhu", "Gill", "Dhillon", "Brar", "Kaur", "Sidhu"],
    "Kerala": ["Nair", "Menon", "Pillai", "Varghese", "Kurian", "Thomas", "Kutty"],
    "Assam": ["Bora", "Kalita", "Das", "Baruah", "Gogoi", "Saikia"],
}

ALIASES = [
    "Chhotu", "Bablu", "Pappu", "Kaalia", "Langda", "Tiger", "Munna", "Guddu", "Lambu", "Tinku",
    "Golu", "Raju Cutting", "Bhai", "Pandit", "Sardar", "Anna", "Dada", "Netaji", "Seth", "Master",
    "Chikna", "Kallu", "Babua", "Mental", "Shooter", "Doctor", "Pahalwan", "Bunty", "Chintu", "Sonu",
]

# Fictional gangs (no real organisation is depicted).
ORGANIZATIONS = [
    "Kala Pathar Gang", "Konkan Coast Syndicate", "Ganga Ghat Network", "Deccan Riders",
    "Marwar Cartel", "Sundarban Smuggling Ring", "Malabar Hawala Ring", "Yamuna Paar Gang",
    "Purvanchal Shooters", "Chambal Valley Gang", "Jamtara-style Cyber Module", "Golden Triangle Couriers",
]

ROLES = ["Gang Leader", "Deputy", "Shooter", "Foot Soldier", "Associate", "Lookout (Khabri)",
         "Financier", "Courier (Carrier)", "Informant", "Enforcer", "Cyber Operator", "Smuggler",
         "Hawala Operator", "Supplier"]

PERSON_STATUSES = ["Active", "Fugitive", "Arrested", "On Bail", "Judicial Custody", "Deceased"]
PERSON_STATUS_WEIGHTS = [30, 12, 15, 20, 15, 3]

PHONE_PREFIXES = ["98", "97", "96", "95", "94", "93", "91", "90", "89", "88", "87", "86", "79", "70", "63"]

PS_INDEX = build_ps_index()
STATE_NAMES = list(STATES.keys())


def random_phone():
    return f"+91-{random.choice(PHONE_PREFIXES)}{random.randint(10000000, 99999999)}"


def random_date_obj(start=DATA_START, end=DATA_END):
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_date(start=DATA_START, end=DATA_END):
    return random_date_obj(start, end).strftime("%Y-%m-%d")


def random_amount():
    ranges = [(10000, 500000), (500000, 5000000), (5000000, 50000000)]
    return round(random.uniform(*random.choice(ranges)), 2)


def random_vehicle(state=None):
    s = STATES[state or random.choice(STATE_NAMES)]
    rto = random.choice(s["rto"])
    series = "".join(random.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(2))
    return f"{rto}{series}{random.randint(1, 9999):04d}"


def random_place(state=None):
    """Pick a police station record (state, district, PS) and a locality."""
    pool = [p for p in PS_INDEX if p["state"] == state] if state else PS_INDEX
    ps = random.choice(pool)
    locality = random.choice(LOCALITIES.get(ps["district"], [ps["ps_name"]]))
    return ps, locality


def pick_partner(person, persons, same_gang=0.8):
    """Pick another person, usually from the same gang, so networks form clusters."""
    others = [p for p in persons if p["id"] != person["id"]]
    gang = [p for p in others if person.get("organization") and p.get("organization") == person["organization"]]
    if gang and random.random() < same_gang:
        return random.choice(gang)
    return random.choice(others)


def pick_group(persons, k):
    first = random.choice(persons)
    group = [first]
    while len(group) < k:
        cand = pick_partner(first, persons)
        if cand not in group:
            group.append(cand)
    return group


# ─── Generate Persons ─────────────────────────────────────────────────────────
def generate_persons(n=60):
    persons = []
    used = set()
    for i in range(n):
        ps, locality = random_place()
        gender = random.choices(["Male", "Female"], weights=[82, 18])[0]
        while True:
            first = random.choice(FIRST_NAMES_M if gender == "Male" else FIRST_NAMES_F)
            last = random.choice(SURNAMES_BY_STATE[ps["state"]])
            if gender == "Female" and last == "Singh" and random.random() > 0.5:
                last = "Kaur"
            name = f"{first} {last}"
            if name not in used:
                used.add(name)
                break
        dob = date(random.randint(1965, 2004), random.randint(1, 12), random.randint(1, 28))
        persons.append({
            "id": f"P{str(i + 1).zfill(3)}",
            "name": name,
            "alias": random.choice(ALIASES) if random.random() > 0.35 else None,
            "age": DATA_END.year - dob.year,
            "gender": gender,
            "nationality": "Indian",
            "phone": random_phone(),
            "email": f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@{random.choice(['gmail.com', 'yahoo.co.in', 'rediffmail.com', 'outlook.com'])}",
            "location": ps["district"],
            "state": ps["state"],
            "district": ps["district"],
            "neighborhood": locality,
            "home_police_station": ps["police_station"],
            "role": random.choice(ROLES),
            "organization": random.choice(ORGANIZATIONS[:8]) if random.random() > 0.15 else None,
            "threat_score": round(random.uniform(0.1, 1.0), 2),
            "criminal_history": random.randint(0, 8),
            "known_associates": [],
            "date_of_birth": dob.strftime("%Y-%m-%d"),
            "arrest_count": random.randint(0, 5),
            "history_sheeter": random.random() > 0.7,
            "status": random.choices(PERSON_STATUSES, weights=PERSON_STATUS_WEIGHTS)[0],
        })
    return persons


# ─── Generate FIRs ────────────────────────────────────────────────────────────
def generate_firs(persons, n=160):
    # Draft incidents first, then number them per PS per year in date order,
    # the way FIR serials run in a real police-station register.
    drafts = []
    for _ in range(n):
        accused = pick_group(persons, random.randint(1, 4))
        # Crimes tend to happen in the home state of the main accused
        state = accused[0]["state"] if random.random() > 0.3 else None
        ps, locality = random_place(state)
        d = random_date_obj()
        options = [c for c in CRIME_CATALOG if d >= NEW_LAWS_EFFECTIVE or c["ipc"] or c.get("sll")]
        crime = random.choice(options)
        drafts.append((d, ps, locality, accused, crime))
    drafts.sort(key=lambda x: x[0])

    serials = {}
    firs = []
    for d, ps, locality, accused, crime in drafts:
        key = (ps["state"], ps["district"], ps["police_station"], d.year)
        if key not in serials:
            serials[key] = random.randint(20, 400)   # register already has earlier entries
        serials[key] += random.randint(1, 25)
        serial = serials[key]

        sections, regime = sections_for(crime, d, len(accused))
        words = ps["district"].replace(".", "").split()
        district_abbr = ("".join(w[0] for w in words) if len(words) > 1 else words[0][:3]).upper()
        ps_abbr = ps["ps_name"].replace(".", "").replace(" ", "")[:4].upper()

        status_pool = FIR_STATUSES if (DATA_END - d).days > 180 else FIR_STATUSES[:3]
        amount = None
        if crime["head"] in ("Economic Offences", "Cyber Crimes", "Offences Against Property") or random.random() > 0.7:
            lo, hi = {"Minor": (5000, 200000), "Major": (100000, 5000000), "Heinous": (1000000, 50000000)}[crime["category"]]
            amount = round(random.uniform(lo, hi), 2)

        firs.append({
            # Human-readable FIR reference: STATE/DISTRICT/PS/FIR No./Year
            "fir_id": f"{ps['state_abbr']}/{district_abbr}/{ps_abbr}/{serial:04d}/{d.year}",
            "fir_no": f"{serial:04d}/{d.year}",
            # CCTNS-style 17-digit ID: state(2) district(3) PS(3) year(4) serial(5)
            "cctns_id": f"{ps['state_code']}{ps['district_code']}{ps['ps_code']}{d.year}{serial:05d}",
            "date": d.strftime("%Y-%m-%d"),
            "time_of_occurrence": f"{random.randint(0, 23):02d}:{random.choice([0, 15, 30, 45]):02d}",
            "state": ps["state"],
            "state_abbr": ps["state_abbr"],
            "state_code": ps["state_code"],
            "district": ps["district"],
            "police_station": ps["police_station"],
            "location": ps["district"],
            "neighborhood": locality,
            "crime_category": crime["category"],
            "crime_head": crime["head"],
            "crime_type": crime["sub"],
            "sections": sections,
            "law_regime": regime,
            "cognizable": crime["cognizable"],
            "bailable": crime["bailable"],
            "triable_by": crime["court"],
            "max_punishment": crime["punishment"],
            "accused_ids": [p["id"] for p in accused],
            "accused_names": [p["name"] for p in accused],
            "complainant": f"{random.choice(FIRST_NAMES_M + FIRST_NAMES_F)} {random.choice(SURNAMES_BY_STATE[ps['state']])}",
            "description": f"Complaint received at {ps['police_station']} regarding {crime['sub'].lower()} near {locality}, {ps['district']}. "
                           f"{len(accused)} accused named; case registered u/s {', '.join(sections)}.",
            "severity": random.choice(SEVERITY_BY_CATEGORY[crime["category"]]),
            "status": random.choice(status_pool),
            "io_name": f"{random.choice(['SI', 'SI', 'Inspector', 'ASI'])} {random.choice(FIRST_NAMES_M)} {random.choice(SURNAMES_BY_STATE[ps['state']])}",
            "vehicle_involved": random_vehicle(ps["state"]) if random.random() > 0.5 else None,
            "amount_involved": amount,
        })
    firs.sort(key=lambda f: f["date"], reverse=True)
    return firs


# ─── Generate CDRs ────────────────────────────────────────────────────────────
def generate_cdrs(persons, n=400):
    cdrs = []
    for i in range(n):
        caller = random.choice(persons)
        receiver = pick_partner(caller, persons)
        ps, locality = random_place(caller["state"] if random.random() > 0.3 else None)
        cdrs.append({
            "cdr_id": f"CDR{str(i + 1).zfill(5)}",
            "datetime": f"{random_date()} {random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
            "caller_id": caller["id"],
            "caller_name": caller["name"],
            "caller_phone": caller["phone"],
            "receiver_id": receiver["id"],
            "receiver_name": receiver["name"],
            "receiver_phone": receiver["phone"],
            "duration_seconds": random.randint(10, 3600),
            "call_type": random.choice(["Voice", "SMS", "WhatsApp", "Telegram", "Signal", "VoIP"]),
            "operator": random.choice(["Jio", "Airtel", "Vi", "BSNL"]),
            "tower_location": f"{locality}, {ps['district']}",
            "state": ps["state"],
            "frequency": random.randint(1, 50),
            "suspicious": random.random() > 0.6,
        })
    return cdrs


# ─── Generate Financial Transactions ─────────────────────────────────────────
def generate_transactions(persons, n=250):
    txns = []
    channels = ["Cash", "UPI", "NEFT/RTGS", "Hawala", "Cryptocurrency", "Shell Company", "Benami Property"]
    for i in range(n):
        sender = random.choice(persons)
        receiver = pick_partner(sender, persons)
        ps, _ = random_place(sender["state"] if random.random() > 0.4 else None)
        channel = random.choice(channels)
        txns.append({
            "txn_id": f"TXN{str(i + 1).zfill(5)}",
            "date": random_date(),
            "sender_id": sender["id"],
            "sender_name": sender["name"],
            "receiver_id": receiver["id"],
            "receiver_name": receiver["name"],
            "amount": random_amount(),
            "currency": "USDT" if channel == "Cryptocurrency" else random.choices(["INR", "AED", "USD"], weights=[85, 10, 5])[0],
            "channel": channel,
            "purpose": random.choice(["Operational Funds", "Bribe", "Arms Purchase", "Drug Payment",
                                      "Layering", "Extortion Proceeds", "Unknown"]),
            "suspicious": random.random() > 0.5,
            "location": ps["district"],
            "state": ps["state"],
        })
    return txns


# ─── Generate Relationships ───────────────────────────────────────────────────
def generate_relationships(persons, n=180):
    rels = []
    rel_types = ["Associate", "Family", "Financial Dependency", "Command", "Communication",
                 "Co-accused", "Vehicle Sharing", "Jail Contact"]
    for i in range(n):
        p1 = random.choice(persons)
        p2 = pick_partner(p1, persons)
        rels.append({
            "rel_id": f"REL{str(i + 1).zfill(4)}",
            "person1_id": p1["id"],
            "person1_name": p1["name"],
            "person2_id": p2["id"],
            "person2_name": p2["name"],
            "relationship_type": random.choice(rel_types),
            "strength": round(random.uniform(0.1, 1.0), 2),
            "first_seen": random_date(date(2018, 1, 1), date(2022, 12, 31)),
            "last_seen": random_date(date(2023, 1, 1), DATA_END),
            "evidence": random.choice(["CDR", "FIR", "Surveillance", "Financial", "Informer", "Witness", "CCTV"]),
        })
    return rels


# ─── Generate Surveillance Reports ───────────────────────────────────────────
def generate_surveillance(persons, n=100):
    reports = []
    for i in range(n):
        subjects = pick_group(persons, random.randint(1, 3))
        ps, locality = random_place(subjects[0]["state"])
        reports.append({
            "report_id": f"SUR{str(i + 1).zfill(4)}",
            "date": random_date(),
            "location": ps["district"],
            "state": ps["state"],
            "neighborhood": locality,
            "subject_ids": [p["id"] for p in subjects],
            "subject_names": [p["name"] for p in subjects],
            "activity": random.choice(["Meeting", "Cash Handover", "Vehicle Transfer", "Consignment Movement", "Communication", "Recce"]),
            "vehicle": random_vehicle(ps["state"]) if random.random() > 0.4 else None,
            "description": f"Surveillance near {locality} ({ps['police_station']}) observed {len(subjects)} subject(s) in suspicious activity.",
            "risk_level": random.choice(["Low", "Medium", "High", "Critical"]),
            "officer": f"{random.choice(['HC', 'ASI', 'SI', 'Inspector'])} {random.choice(FIRST_NAMES_M)} {random.choice(SURNAMES_BY_STATE[ps['state']])}",
        })
    return reports


# ─── Main ─────────────────────────────────────────────────────────────────────
def main(out_dir=None):
    out_dir = out_dir or os.path.dirname(os.path.abspath(__file__))
    print("Generating Indian criminal network dataset...")

    persons = generate_persons(60)
    firs = generate_firs(persons, 160)
    cdrs = generate_cdrs(persons, 400)
    transactions = generate_transactions(persons, 250)
    relationships = generate_relationships(persons, 180)
    surveillance = generate_surveillance(persons, 100)

    datasets = {
        "persons": persons, "firs": firs, "cdrs": cdrs, "transactions": transactions,
        "relationships": relationships, "surveillance": surveillance,
    }
    for name, data in datasets.items():
        with open(os.path.join(out_dir, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        with open(os.path.join(out_dir, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            for row in data:
                writer.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v) for k, v in row.items()})
        print(f"[OK] Generated {len(data)} {name}")
    # Investigations are rebuilt from the new FIRs on next start
    inv = os.path.join(out_dir, "investigations.json")
    if os.path.exists(inv):
        os.remove(inv)
    print("[OK] All files saved!")


if __name__ == "__main__":
    main()

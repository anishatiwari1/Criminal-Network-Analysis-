"""
Adding new person records and finding how they connect to people already
in the portal.

When a record is saved, it is compared against existing persons, FIRs,
CDRs and surveillance reports. Every match becomes a relationship
(evidence "Auto-match"), so the new person appears in the network graph,
threat scoring and criminal groups as soon as the analyzer is rebuilt.
"""

import json
import os
import random
import re
from datetime import date, datetime
from difflib import SequenceMatcher

# Strength of each kind of match (0-1). Several matches with the same person
# combine as 1 - Π(1 - s).
MATCH_RULES = {
    "same_phone": (0.95, "Possible Same Identity", "Same mobile number"),
    "similar_name": (0.6, "Possible Same Identity", "Very similar name"),
    "contact_phone": (0.7, "Communication", "Contact number belongs to this person"),
    "cdr_contact": (0.6, "Communication", "Contact number appears in their call records"),
    "fir_vehicle": (0.75, "Vehicle Sharing", "Vehicle named in an FIR against this person"),
    "surveillance_vehicle": (0.55, "Vehicle Sharing", "Vehicle seen with this person under surveillance"),
    "same_gang": (0.5, "Associate", "Same gang / organisation"),
    "linked_fir": (0.8, "Co-accused", "Co-accused in the same FIR"),
    "associate": (0.9, "Associate", "Named as a known associate"),
    "same_alias_area": (0.45, "Associate", "Same alias in the same district"),
    "same_locality": (0.3, "Associate", "Lives in the same locality"),
}


def _norm_phone(p):
    digits = re.sub(r"\D", "", p or "")
    return digits[-10:] if len(digits) >= 10 else digits


def _norm_vehicle(v):
    return re.sub(r"[^A-Z0-9]", "", (v or "").upper())


def _load(data_dir, name):
    with open(os.path.join(data_dir, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def _save(data_dir, name, data):
    with open(os.path.join(data_dir, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_links(rec, persons, firs, cdrs, surveillance):
    """Return [{person, score, reasons:[...], relationship_type}] sorted by score."""
    hits = {}

    def hit(pid, rule, detail=""):
        strength, rel_type, label = MATCH_RULES[rule]
        h = hits.setdefault(pid, {"rules": {}, "reasons": []})
        if rule not in h["rules"] or h["rules"][rule][0] < strength:
            h["rules"][rule] = (strength, rel_type)
        reason = label + (f": {detail}" if detail else "")
        if reason not in h["reasons"]:
            h["reasons"].append(reason)

    by_id = {p["id"]: p for p in persons}
    phone = _norm_phone(rec.get("phone"))
    contacts = {_norm_phone(x) for x in rec.get("contact_numbers", []) if _norm_phone(x)}
    vehicle = _norm_vehicle(rec.get("vehicle"))
    name = (rec.get("name") or "").lower().strip()
    alias = (rec.get("alias") or "").lower().strip()

    for p in persons:
        pp = _norm_phone(p.get("phone"))
        if phone and pp == phone:
            hit(p["id"], "same_phone", p.get("phone", ""))
        if pp and pp in contacts:
            hit(p["id"], "contact_phone", p.get("phone", ""))
        if name and SequenceMatcher(None, name, p["name"].lower()).ratio() >= 0.85:
            hit(p["id"], "similar_name", p["name"])
        if rec.get("organization") and p.get("organization") == rec["organization"]:
            hit(p["id"], "same_gang", rec["organization"])
        if alias and (p.get("alias") or "").lower() == alias and p.get("district") == rec.get("district"):
            hit(p["id"], "same_alias_area", f"\"{p['alias']}\" in {p.get('district')}")
        if (rec.get("locality") and p.get("neighborhood") == rec["locality"]
                and p.get("district") == rec.get("district")):
            hit(p["id"], "same_locality", f"{rec['locality']}, {rec['district']}")

    # Contact numbers that show up in call records
    if contacts:
        cdr_hits = {}
        for c in cdrs:
            for side in ("caller", "receiver"):
                if _norm_phone(c.get(f"{side}_phone")) in contacts and c[f"{side}_id"] in by_id:
                    cdr_hits.setdefault(c[f"{side}_id"], []).append(c["datetime"][:10])
        for pid, dates in cdr_hits.items():
            hit(pid, "cdr_contact", f"{len(dates)} call record(s), latest {max(dates)}")

    if vehicle:
        for f in firs:
            if _norm_vehicle(f.get("vehicle_involved")) == vehicle:
                for pid in f.get("accused_ids", []):
                    hit(pid, "fir_vehicle", f"{f.get('vehicle_involved')} in FIR {f['fir_id']}")
        for s in surveillance:
            if _norm_vehicle(s.get("vehicle")) == vehicle:
                for pid in s.get("subject_ids", []):
                    hit(pid, "surveillance_vehicle", f"{s.get('vehicle')} in {s['report_id']}")

    if rec.get("linked_fir_id"):
        fir = next((f for f in firs if f["fir_id"] == rec["linked_fir_id"]), None)
        if fir:
            for pid in fir.get("accused_ids", []):
                hit(pid, "linked_fir", fir["fir_id"])

    for pid in rec.get("associate_ids", []):
        if pid in by_id:
            hit(pid, "associate")

    results = []
    for pid, h in hits.items():
        if pid not in by_id:
            continue
        miss = 1.0
        for strength, _ in h["rules"].values():
            miss *= (1 - strength)
        best_type = max(h["rules"].values(), key=lambda x: x[0])[1]
        p = by_id[pid]
        results.append({
            "person": {k: p.get(k) for k in ("id", "name", "alias", "district", "state", "organization",
                                              "status", "role", "computed_threat_score", "phone")},
            "score": round(1 - miss, 3),
            "relationship_type": best_type,
            "reasons": h["reasons"],
        })
    results.sort(key=lambda r: -r["score"])
    return results


def add_person(data_dir, rec, added_by):
    """Validate, save the person, create relationships for every link. Returns (person, links)."""
    rec = {k: (v.strip() if isinstance(v, str) else v) for k, v in rec.items()}
    if not rec.get("name"):
        raise ValueError("Name is required")
    if not rec.get("state") or not rec.get("district"):
        raise ValueError("State and district are required")

    persons = _load(data_dir, "persons")
    firs = _load(data_dir, "firs")
    cdrs = _load(data_dir, "cdrs")
    surveillance = _load(data_dir, "surveillance")
    relationships = _load(data_dir, "relationships")

    rec["contact_numbers"] = [x.strip() for x in rec.get("contact_numbers", []) if x and x.strip()]
    links = find_links(rec, persons, firs, cdrs, surveillance)

    next_num = max(int(p["id"][1:]) for p in persons if p["id"][1:].isdigit()) + 1
    pid = f"P{next_num:03d}"
    dob = rec.get("date_of_birth") or ""
    age = rec.get("age")
    if dob and not age:
        try:
            age = date.today().year - int(dob[:4])
        except ValueError:
            age = None
    person = {
        "id": pid,
        "name": rec["name"],
        "alias": rec.get("alias") or None,
        "age": int(age) if age not in (None, "") else None,
        "gender": rec.get("gender") or "Male",
        "nationality": rec.get("nationality") or "Indian",
        "phone": rec.get("phone") or "",
        "email": rec.get("email") or "",
        "location": rec["district"],
        "state": rec["state"],
        "district": rec["district"],
        "neighborhood": rec.get("locality") or "",
        "home_police_station": rec.get("home_police_station") or "",
        "role": rec.get("role") or "Associate",
        "organization": rec.get("organization") or None,
        "threat_score": 0.5,
        "criminal_history": int(rec.get("criminal_history") or 0),
        "known_associates": [l["person"]["id"] for l in links],
        "date_of_birth": dob,
        "arrest_count": int(rec.get("arrest_count") or 0),
        "history_sheeter": bool(rec.get("history_sheeter")),
        "status": rec.get("status") or "Active",
        "vehicle": rec.get("vehicle") or None,
        "contact_numbers": rec["contact_numbers"],
        "identification_marks": rec.get("identification_marks") or "",
        "notes": rec.get("notes") or "",
        "added_by": added_by,
        "added_on": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    persons.append(person)

    next_rel = len(relationships) + 1
    today = date.today().isoformat()
    for l in links:
        relationships.append({
            "rel_id": f"REL{next_rel:04d}",
            "person1_id": pid,
            "person1_name": person["name"],
            "person2_id": l["person"]["id"],
            "person2_name": l["person"]["name"],
            "relationship_type": l["relationship_type"],
            "strength": l["score"],
            "first_seen": today,
            "last_seen": today,
            "evidence": "Auto-match: " + "; ".join(l["reasons"]),
        })
        next_rel += 1

    # Add as accused in a linked FIR
    if rec.get("linked_fir_id"):
        for f in firs:
            if f["fir_id"] == rec["linked_fir_id"] and pid not in f["accused_ids"]:
                f["accused_ids"].append(pid)
                f["accused_names"].append(person["name"])
        _save(data_dir, "firs", firs)

    _save(data_dir, "persons", persons)
    _save(data_dir, "relationships", relationships)
    return person, links


def sample_record(persons, firs, surveillance, seed=None):
    """Dummy record that is deliberately linked to someone already in the portal."""
    rng = random.Random(seed)
    first = rng.choice(["Raju", "Sonu", "Imtiaz", "Vicky", "Dinesh", "Arvind", "Kuldeep", "Manish", "Salim",
                        "Ravi", "Prem", "Rupa", "Seema", "Javed", "Bittu", "Naresh", "Ganesh", "Lalit"])
    anchor = rng.choice([p for p in persons if p.get("organization")] or persons)
    anchor_firs = [f for f in firs if anchor["id"] in f.get("accused_ids", []) and f.get("vehicle_involved")]
    last = anchor["name"].split()[-1] if rng.random() > 0.4 else rng.choice(["Yadav", "Sharma", "Khan", "Patil", "Reddy", "Das"])
    others = [p for p in persons if p["id"] != anchor["id"] and p.get("state") == anchor.get("state")]
    contacts = [anchor["phone"]] + ([rng.choice(others)["phone"]] if others and rng.random() > 0.4 else [])
    year = rng.randint(1975, 2003)
    return {
        "name": f"{first} {last}",
        "alias": rng.choice(["Kaalu", "Pinku", "Lucky", "Jaggu", "Tiger", "Chhotu", "Nawab", "Bhola", "Shera", ""]),
        "gender": "Female" if first in ("Rupa", "Seema") else "Male",
        "date_of_birth": f"{year}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
        "phone": f"+91-{rng.choice(['98', '97', '88', '70', '63'])}{rng.randint(10000000, 99999999)}",
        "contact_numbers": contacts,
        "email": f"{first.lower()}{rng.randint(10, 99)}@gmail.com",
        "state": anchor["state"],
        "district": anchor["district"],
        "locality": anchor.get("neighborhood", ""),
        "home_police_station": anchor.get("home_police_station", ""),
        "role": rng.choice(["Courier (Carrier)", "Foot Soldier", "Lookout (Khabri)", "Shooter", "Supplier", "Hawala Operator"]),
        "organization": anchor.get("organization") or "",
        "vehicle": anchor_firs[0]["vehicle_involved"] if anchor_firs else "",
        "status": rng.choice(["Active", "Fugitive", "Arrested"]),
        "criminal_history": rng.randint(0, 4),
        "arrest_count": rng.randint(0, 3),
        "history_sheeter": rng.random() > 0.6,
        "identification_marks": rng.choice(["Mole on left cheek", "Scar above right eyebrow", "Tattoo 'Maa' on right forearm",
                                            "Limps on left leg", "Gold tooth, upper left"]),
        "notes": f"Informer input: seen meeting {anchor['name']} near {anchor.get('neighborhood', anchor['district'])}.",
        "associate_ids": [],
        "linked_fir_id": "",
    }

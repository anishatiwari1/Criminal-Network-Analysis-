"""
Investigation tracking.

One investigation per FIR, stored in data/investigations.json. Stages follow
the usual BNSS flow; the chargesheet deadline follows BNSS s.187(3):
90 days from arrest for offences punishable with death, life or 10+ years,
60 days for other offences (else the accused gets default bail).
"""

import json
import os
import random
from datetime import date, datetime, timedelta

STAGES = [
    "FIR Registered",
    "Scene Visit & Forensics",
    "Evidence Collection",
    "Arrest / Notice Served",
    "Custody & Remand",
    "Chargesheet Filed",
    "Under Trial",
    "Closed",
]

NEXT_ACTIONS = {
    0: ["Visit scene of crime", "Record complainant statement", "Forensic team visit if 7+ year offence (BNSS s.176(3))"],
    1: ["Collect CCTV footage", "Seize material evidence with video recording (BNSS s.105)", "Send exhibits to FSL"],
    2: ["Obtain CDRs and bank statements", "Record witness statements (BNSS s.180)", "Get BSA s.63 certificates for electronic records"],
    3: ["Produce accused before Magistrate within 24 hours", "Inform relative of arrest (BNSS s.48)", "Seek police custody if needed (BNSS s.187)"],
    4: ["Complete investigation before default-bail deadline", "Follow up FSL report", "Draft chargesheet"],
    5: ["Supply documents to accused (BNSS s.230)", "Track framing of charges", "Witness protection if required (BNSS s.398)"],
    6: ["Ensure witnesses attend", "Coordinate with Public Prosecutor"],
    7: [],
}

PRIORITY_BY_SEVERITY = {"Critical": "P1 - Urgent", "High": "P2 - High", "Medium": "P3 - Normal", "Low": "P4 - Low"}
STATUS_TO_STAGE = {"Registered": (0, 1), "Under Investigation": (2, 4), "Chargesheet Filed": (5, 5),
                   "Pending Trial": (6, 6)}


def _path(data_dir):
    return os.path.join(data_dir, "investigations.json")


def deadline_days(fir):
    """60 or 90 days to file chargesheet after arrest (BNSS s.187(3))."""
    p = (fir.get("max_punishment") or "").lower()
    if fir.get("crime_category") == "Heinous" or "life" in p or "death" in p or "10 years" in p or "14 years" in p or "20 years" in p:
        return 90
    return 60


def generate(firs, seed=11):
    """Dummy investigations for FIRs that are still open."""
    rng = random.Random(seed)
    today = date.today()
    out = []
    open_firs = [f for f in firs if f.get("status") in STATUS_TO_STAGE]
    open_firs.sort(key=lambda f: f["date"])
    for i, f in enumerate(open_firs, start=1):
        lo, hi = STATUS_TO_STAGE[f["status"]]
        stage = rng.randint(lo, hi)
        opened = datetime.strptime(f["date"], "%Y-%m-%d").date()
        age = max((today - opened).days, 1)
        updates = [{"date": f["date"], "stage": STAGES[0], "by": f.get("io_name", "IO"),
                    "note": f"FIR {f['fir_no']} registered at {f['police_station']} u/s {', '.join(f.get('sections', []))}."}]
        arrest_date = None
        for s in range(1, stage + 1):
            d = opened + timedelta(days=min(age, int(age * s / (stage + 1)) + rng.randint(0, 3)))
            if s == 3:
                arrest_date = d
            updates.append({"date": d.isoformat(), "stage": STAGES[s], "by": f.get("io_name", "IO"),
                            "note": {1: "Scene inspected; forensic team collected samples.",
                                     2: "CDRs requested from service providers; statements of 3 witnesses recorded.",
                                     3: f"{len(f['accused_ids'])} accused identified; arrests / notices under BNSS s.35.",
                                     4: "Accused produced before Magistrate; police custody granted.",
                                     5: "Chargesheet filed before the court.",
                                     6: "Charges framed; trial in progress."}[s]})
        # Recent cases: arrest a few days ago so deadlines are in the future
        if arrest_date and age < 150:
            arrest_date = max(opened, today - timedelta(days=rng.randint(5, deadline_days(f) + 20)))
            for k, u in enumerate(updates[4:], start=0):
                u["date"] = min(today, arrest_date + timedelta(days=k * 3)).isoformat()
        out.append(_new_case(i, f, stage, arrest_date, updates))
    return out


def _new_case(num, f, stage, arrest_date, updates):
    due = (arrest_date + timedelta(days=deadline_days(f))).isoformat() if arrest_date else None
    return {
        "case_id": f"INV-{f['date'][:4]}-{num:04d}",
        "fir_id": f["fir_id"],
        "fir_no": f["fir_no"],
        "crime_type": f["crime_type"],
        "crime_category": f["crime_category"],
        "sections": f.get("sections", []),
        "state": f["state"],
        "district": f["district"],
        "police_station": f["police_station"],
        "io_name": f.get("io_name", ""),
        "priority": PRIORITY_BY_SEVERITY.get(f.get("severity"), "P3 - Normal"),
        "opened_on": f["date"],
        "accused_ids": f.get("accused_ids", []),
        "accused_names": f.get("accused_names", []),
        "stage_index": stage,
        "stage": STAGES[stage],
        "arrest_date": arrest_date.isoformat() if arrest_date else None,
        "deadline_days": deadline_days(f),
        "chargesheet_due": due,
        "status": "Closed" if stage == 7 else "Open",
        "updates": updates,
    }


def load(data_dir, firs):
    path = _path(data_dir)
    if not os.path.exists(path):
        save(data_dir, generate(firs))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(data_dir, cases):
    with open(_path(data_dir), "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)


def enrich(case, today=None):
    """Add computed fields: days open, days to deadline, overdue flag, next actions."""
    today = today or date.today()
    c = dict(case)
    c["days_open"] = (today - datetime.strptime(c["opened_on"], "%Y-%m-%d").date()).days
    c["days_to_deadline"] = None
    c["overdue"] = False
    if c.get("chargesheet_due") and c["stage_index"] < 5 and c["status"] == "Open":
        left = (datetime.strptime(c["chargesheet_due"], "%Y-%m-%d").date() - today).days
        c["days_to_deadline"] = left
        c["overdue"] = left < 0
    c["next_actions"] = NEXT_ACTIONS.get(c["stage_index"], [])
    c["progress"] = round(c["stage_index"] / (len(STAGES) - 1) * 100)
    return c


def add_update(data_dir, cases, case_id, stage_index, note, by, arrest_date=None):
    case = next((c for c in cases if c["case_id"] == case_id), None)
    if not case:
        raise KeyError(case_id)
    stage_index = int(stage_index)
    if not 0 <= stage_index < len(STAGES):
        raise ValueError("Invalid stage")
    today = date.today().isoformat()
    if stage_index >= 3 and not case.get("arrest_date"):
        case["arrest_date"] = arrest_date or today
        due = datetime.strptime(case["arrest_date"], "%Y-%m-%d").date() + timedelta(days=case["deadline_days"])
        case["chargesheet_due"] = due.isoformat()
    case["stage_index"] = stage_index
    case["stage"] = STAGES[stage_index]
    case["status"] = "Closed" if stage_index == 7 else "Open"
    case["updates"].append({"date": today, "stage": STAGES[stage_index], "by": by, "note": note or "Stage updated."})
    save(data_dir, cases)
    return case


def open_case(data_dir, cases, fir, by):
    if any(c["fir_id"] == fir["fir_id"] for c in cases):
        raise ValueError("An investigation already exists for this FIR")
    num = max((int(c["case_id"].split("-")[-1]) for c in cases), default=0) + 1
    case = _new_case(num, fir, 0, None, [{
        "date": date.today().isoformat(), "stage": STAGES[0], "by": by,
        "note": f"Investigation opened for FIR {fir['fir_no']} ({fir['police_station']})."}])
    case["case_id"] = f"INV-{date.today().year}-{num:04d}"
    cases.append(case)
    save(data_dir, cases)
    return case

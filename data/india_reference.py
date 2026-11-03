"""
Indian reference data used by the dataset generator and the web app.

  * STATES            – states/UTs with Census-2011 state codes, vehicle RTO
                        prefixes, districts and real police-station names
  * CRIME_CATALOG     – crime hierarchy: Category (Heinous/Major/Minor)
                        -> NCRB crime head -> sub-category, with BNS 2023 and
                        legacy IPC 1860 sections / Special & Local Law (SLL)
                        sections, cognizable / bailable flags
  * FIR_STATUSES      – investigation / trial stages used by Indian police

All personal data generated from this file is synthetic.
"""

from datetime import date

# Date the three new criminal laws (BNS, BNSS, BSA) came into force.
NEW_LAWS_EFFECTIVE = date(2024, 7, 1)

# ─── States / Districts / Police Stations ────────────────────────────────────
# state_code = Census 2011 / LGD state code (used in CCTNS identifiers)
# district / PS codes are synthetic 3-digit codes, stable for this dataset.
STATES = {
    "Maharashtra": {
        "abbr": "MH", "state_code": "27", "rto": ["MH01", "MH02", "MH03", "MH12", "MH14", "MH31"],
        "districts": {
            "Mumbai City": ["Colaba", "Azad Maidan", "Dongri", "Byculla", "Dadar"],
            "Mumbai Suburban": ["Andheri", "Bandra", "Kurla", "Dharavi", "Malad"],
            "Pune City": ["Shivajinagar", "Kothrud", "Hadapsar", "Swargate"],
            "Nagpur City": ["Sitabuldi", "Sadar", "Kotwali"],
        },
    },
    "Delhi": {
        "abbr": "DL", "state_code": "07", "rto": ["DL01", "DL03", "DL04", "DL08", "DL09", "DL10"],
        "districts": {
            "New Delhi": ["Connaught Place", "Parliament Street", "Barakhamba Road", "Tilak Marg"],
            "South Delhi": ["Hauz Khas", "Saket", "Malviya Nagar", "Mehrauli"],
            "North East Delhi": ["Seelampur", "Jafrabad", "Welcome", "Bhajanpura"],
            "Central Delhi": ["Paharganj", "Karol Bagh", "Chandni Mahal", "Kamla Market"],
        },
    },
    "Karnataka": {
        "abbr": "KA", "state_code": "29", "rto": ["KA01", "KA03", "KA04", "KA05", "KA09", "KA51"],
        "districts": {
            "Bengaluru Urban": ["Koramangala", "Whitefield", "Jayanagar", "Indiranagar", "Hebbal"],
            "Mysuru": ["Lashkar", "Devaraja", "Vijayanagar"],
        },
    },
    "Tamil Nadu": {
        "abbr": "TN", "state_code": "33", "rto": ["TN01", "TN02", "TN07", "TN09", "TN37", "TN66"],
        "districts": {
            "Chennai": ["Mylapore", "T. Nagar", "Egmore", "Royapettah", "Washermanpet"],
            "Coimbatore": ["R.S. Puram", "Gandhipuram", "Peelamedu"],
            "Madurai": ["Thilagar Thidal", "Anna Nagar", "Tallakulam"],
        },
    },
    "West Bengal": {
        "abbr": "WB", "state_code": "19", "rto": ["WB01", "WB02", "WB06", "WB20", "WB24"],
        "districts": {
            "Kolkata": ["Park Street", "Bowbazar", "Lalbazar", "Shakespeare Sarani", "Tiljala"],
            "North 24 Parganas": ["Barasat", "Dum Dum", "Bidhannagar", "Basirhat"],
        },
    },
    "Telangana": {
        "abbr": "TS", "state_code": "36", "rto": ["TS07", "TS08", "TS09", "TS10", "TS11", "TS13"],
        "districts": {
            "Hyderabad": ["Charminar", "Banjara Hills", "Abids", "Golconda", "Chikkadpally"],
            "Rangareddy": ["Gachibowli", "Rajendranagar", "LB Nagar"],
        },
    },
    "Uttar Pradesh": {
        "abbr": "UP", "state_code": "09", "rto": ["UP14", "UP16", "UP32", "UP65", "UP78", "UP80"],
        "districts": {
            "Lucknow": ["Hazratganj", "Gomti Nagar", "Aminabad", "Chowk", "Alambagh"],
            "Kanpur Nagar": ["Kotwali", "Kalyanpur", "Swaroop Nagar", "Chamanganj"],
            "Varanasi": ["Dashashwamedh", "Kotwali", "Lanka", "Cantonment"],
            "Gautam Buddh Nagar": ["Sector 20 Noida", "Sector 39 Noida", "Knowledge Park"],
        },
    },
    "Gujarat": {
        "abbr": "GJ", "state_code": "24", "rto": ["GJ01", "GJ05", "GJ06", "GJ18", "GJ27"],
        "districts": {
            "Ahmedabad": ["Navrangpura", "Maninagar", "Kalupur", "Satellite", "Vatva"],
            "Surat": ["Athwalines", "Varachha", "Udhna", "Mahidharpura"],
        },
    },
    "Rajasthan": {
        "abbr": "RJ", "state_code": "08", "rto": ["RJ14", "RJ19", "RJ20", "RJ27", "RJ45"],
        "districts": {
            "Jaipur": ["Ashok Nagar", "Malviya Nagar", "Kotwali", "Sanganer", "Vidhyadhar Nagar"],
            "Jodhpur": ["Sardarpura", "Ratanada", "Udai Mandir"],
        },
    },
    "Madhya Pradesh": {
        "abbr": "MP", "state_code": "23", "rto": ["MP04", "MP09", "MP07", "MP20"],
        "districts": {
            "Bhopal": ["TT Nagar", "Habibganj", "Kohefiza", "Hanumanganj"],
            "Indore": ["Vijay Nagar", "MG Road", "Sanyogitaganj", "Palasia"],
        },
    },
    "Bihar": {
        "abbr": "BR", "state_code": "10", "rto": ["BR01", "BR02", "BR06", "BR10"],
        "districts": {
            "Patna": ["Kotwali", "Gandhi Maidan", "Kankarbagh", "Pirbahore", "Danapur"],
            "Gaya": ["Kotwali", "Civil Lines", "Rampur"],
        },
    },
    "Punjab": {
        "abbr": "PB", "state_code": "03", "rto": ["PB02", "PB08", "PB10", "PB65"],
        "districts": {
            "Ludhiana": ["Division No. 5", "Sarabha Nagar", "Model Town", "Division No. 2"],
            "Amritsar": ["Kotwali", "Civil Lines", "Ranjit Avenue", "Sultanwind"],
        },
    },
    "Kerala": {
        "abbr": "KL", "state_code": "32", "rto": ["KL01", "KL07", "KL11", "KL13"],
        "districts": {
            "Ernakulam": ["Ernakulam Central", "Ernakulam Town North", "Kalamassery", "Fort Kochi"],
            "Thiruvananthapuram": ["Museum", "Fort", "Thampanoor", "Vanchiyoor"],
        },
    },
    "Assam": {
        "abbr": "AS", "state_code": "18", "rto": ["AS01", "AS02", "AS12"],
        "districts": {
            "Kamrup Metropolitan": ["Paltan Bazaar", "Dispur", "Latasil", "Chandmari"],
        },
    },
}

# Localities used for "area" / neighbourhood text, keyed by district.
LOCALITIES = {
    "Mumbai City": ["Colaba Causeway", "Crawford Market", "Mohammed Ali Road", "Lalbaug", "Dadar TT"],
    "Mumbai Suburban": ["Andheri East", "Bandra West", "Kurla West", "Dharavi", "Malad Malvani"],
    "Pune City": ["FC Road", "Kothrud Depot", "Hadapsar Gaon", "Swargate Bus Stand"],
    "Nagpur City": ["Sitabuldi Main Road", "Sadar Bazaar", "Itwari"],
    "New Delhi": ["Connaught Place", "Janpath", "Gole Market", "Mandi House"],
    "South Delhi": ["Hauz Khas Village", "Saket", "Lajpat Nagar", "Mehrauli"],
    "North East Delhi": ["Seelampur", "Jafrabad", "Gokulpuri", "Bhajanpura"],
    "Central Delhi": ["Paharganj", "Karol Bagh", "Chandni Chowk", "Sadar Bazaar"],
    "Bengaluru Urban": ["Koramangala 5th Block", "Whitefield", "Jayanagar 4th Block", "Majestic", "Hebbal"],
    "Mysuru": ["Devaraja Market", "Lashkar Mohalla", "Vijayanagar"],
    "Chennai": ["Mylapore", "Pondy Bazaar", "Egmore", "Parrys Corner", "Washermanpet"],
    "Coimbatore": ["R.S. Puram", "Gandhipuram", "Ukkadam"],
    "Madurai": ["Meenakshi Amman Kovil St", "Anna Nagar", "Goripalayam"],
    "Kolkata": ["Park Street", "Bowbazar", "Burrabazar", "Esplanade", "Tiljala"],
    "North 24 Parganas": ["Barasat", "Dum Dum", "Salt Lake", "Basirhat"],
    "Hyderabad": ["Charminar", "Banjara Hills", "Abids", "Tolichowki", "Koti"],
    "Rangareddy": ["Gachibowli", "HITEC City", "LB Nagar"],
    "Lucknow": ["Hazratganj", "Gomti Nagar", "Aminabad", "Chowk", "Alambagh"],
    "Kanpur Nagar": ["Mall Road", "Kalyanpur", "Swaroop Nagar", "Chamanganj"],
    "Varanasi": ["Dashashwamedh Ghat", "Godowlia", "Lanka", "Cantt"],
    "Gautam Buddh Nagar": ["Sector 18 Noida", "Sector 62 Noida", "Greater Noida West"],
    "Ahmedabad": ["Navrangpura", "Maninagar", "Kalupur", "Satellite", "Vatva GIDC"],
    "Surat": ["Ring Road Textile Market", "Varachha", "Udhna", "Mahidharpura"],
    "Jaipur": ["Johari Bazaar", "Malviya Nagar", "MI Road", "Sanganer"],
    "Jodhpur": ["Sardarpura", "Ratanada", "Ghanta Ghar"],
    "Bhopal": ["New Market", "Habibganj", "Kohefiza", "Chowk Bazaar"],
    "Indore": ["Vijay Nagar", "Rajwada", "Sarafa Bazaar", "Palasia"],
    "Patna": ["Gandhi Maidan", "Kankarbagh", "Patna City", "Danapur"],
    "Gaya": ["Station Road", "Civil Lines", "Bodh Gaya Road"],
    "Ludhiana": ["Chaura Bazaar", "Sarabha Nagar", "Model Town", "Focal Point"],
    "Amritsar": ["Hall Bazaar", "Ranjit Avenue", "Lawrence Road", "Sultanwind"],
    "Ernakulam": ["MG Road", "Broadway", "Kalamassery", "Fort Kochi"],
    "Thiruvananthapuram": ["Palayam", "East Fort", "Thampanoor", "Vanchiyoor"],
    "Kamrup Metropolitan": ["Paltan Bazaar", "Dispur", "Fancy Bazaar", "Beltola"],
}


def build_ps_index():
    """Return a flat list of police stations with stable synthetic codes."""
    out = []
    for state, s in STATES.items():
        for d_idx, (district, stations) in enumerate(s["districts"].items(), start=1):
            for p_idx, ps in enumerate(stations, start=1):
                out.append({
                    "state": state,
                    "state_abbr": s["abbr"],
                    "state_code": s["state_code"],
                    "district": district,
                    "district_code": f"{d_idx * 10 + 1:03d}",
                    "police_station": f"{ps} PS",
                    "ps_name": ps,
                    "ps_code": f"{p_idx * 10 + 1:03d}",
                })
    return out


# ─── Crime hierarchy ─────────────────────────────────────────────────────────
# Category is derived from the maximum punishment (this project's labels):
#   Heinous : punishable with death / life imprisonment, or minimum ≥ 7 years
#   Major   : maximum punishment more than 3 years
#   Minor   : maximum punishment up to 3 years
# Crime heads follow the groupings used in NCRB "Crime in India".
CATEGORIES = ["Heinous", "Major", "Minor"]

CATEGORY_INFO = {
    "Heinous": "Punishable with death or life imprisonment, or a minimum of 7 years",
    "Major": "Maximum punishment above 3 years (non-heinous)",
    "Minor": "Maximum punishment up to 3 years",
}

# Each entry: sub-category, category, NCRB head, BNS section(s), IPC section(s)
# (for FIRs before 1 July 2024), special Act sections, punishment, flags.
CRIME_CATALOG = [
    # Offences affecting the human body
    {"sub": "Murder", "category": "Heinous", "head": "Offences Affecting the Human Body",
     "bns": "BNS 103(1)", "ipc": "IPC 302", "punishment": "Death or imprisonment for life + fine",
     "cognizable": True, "bailable": False, "court": "Court of Session"},
    {"sub": "Attempt to Murder", "category": "Heinous", "head": "Offences Affecting the Human Body",
     "bns": "BNS 109(1)", "ipc": "IPC 307", "punishment": "Up to 10 years; life if hurt is caused",
     "cognizable": True, "bailable": False, "court": "Court of Session"},
    {"sub": "Culpable Homicide not amounting to Murder", "category": "Heinous", "head": "Offences Affecting the Human Body",
     "bns": "BNS 105", "ipc": "IPC 304", "punishment": "Imprisonment for life, or 5–10 years",
     "cognizable": True, "bailable": False, "court": "Court of Session"},
    {"sub": "Kidnapping for Ransom", "category": "Heinous", "head": "Offences Affecting the Human Body",
     "bns": "BNS 140(2)", "ipc": "IPC 364A", "punishment": "Death or imprisonment for life + fine",
     "cognizable": True, "bailable": False, "court": "Court of Session"},
    {"sub": "Kidnapping & Abduction", "category": "Major", "head": "Offences Affecting the Human Body",
     "bns": "BNS 137(2)", "ipc": "IPC 363", "punishment": "Up to 7 years + fine",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class"},
    {"sub": "Grievous Hurt", "category": "Major", "head": "Offences Affecting the Human Body",
     "bns": "BNS 117(2)", "ipc": "IPC 325", "punishment": "Up to 7 years + fine",
     "cognizable": True, "bailable": True, "court": "Any Magistrate"},
    {"sub": "Death by Negligence (Rash Driving)", "category": "Major", "head": "Offences Affecting the Human Body",
     "bns": "BNS 106(1)", "ipc": "IPC 304A", "punishment": "Up to 5 years + fine",
     "cognizable": True, "bailable": True, "court": "Magistrate First Class"},
    {"sub": "Human Trafficking", "category": "Heinous", "head": "Offences Affecting the Human Body",
     "bns": "BNS 143", "ipc": "IPC 370", "punishment": "7–10 years; up to life for multiple victims",
     "cognizable": True, "bailable": False, "court": "Court of Session",
     "acts": ["Immoral Traffic (Prevention) Act 1956"]},

    # Offences against property
    {"sub": "Dacoity", "category": "Heinous", "head": "Offences Against Property",
     "bns": "BNS 310(2)", "ipc": "IPC 395", "punishment": "Imprisonment for life, or up to 10 years RI",
     "cognizable": True, "bailable": False, "court": "Court of Session"},
    {"sub": "Robbery", "category": "Major", "head": "Offences Against Property",
     "bns": "BNS 309(4)", "ipc": "IPC 392", "punishment": "Up to 10 years RI; 14 years on highway at night",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class"},
    {"sub": "Burglary (House-breaking by night)", "category": "Major", "head": "Offences Against Property",
     "bns": "BNS 331(4)", "ipc": "IPC 457", "punishment": "Up to 5 years; up to 14 years if theft intended",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class"},
    {"sub": "Extortion", "category": "Major", "head": "Offences Against Property",
     "bns": "BNS 308(2)", "ipc": "IPC 384", "punishment": "Up to 7 years + fine",
     "cognizable": True, "bailable": False, "court": "Any Magistrate"},
    {"sub": "Theft", "category": "Minor", "head": "Offences Against Property",
     "bns": "BNS 303(2)", "ipc": "IPC 379", "punishment": "Up to 3 years + fine",
     "cognizable": True, "bailable": False, "court": "Any Magistrate"},
    {"sub": "Motor Vehicle Theft", "category": "Minor", "head": "Offences Against Property",
     "bns": "BNS 303(2)", "ipc": "IPC 379", "punishment": "Up to 3 years + fine",
     "cognizable": True, "bailable": False, "court": "Any Magistrate"},
    {"sub": "Snatching (Chain / Mobile)", "category": "Minor", "head": "Offences Against Property",
     "bns": "BNS 304(2)", "ipc": "IPC 379/356", "punishment": "Up to 3 years + fine",
     "cognizable": True, "bailable": False, "court": "Any Magistrate"},

    # Crimes against women
    {"sub": "Dowry Death", "category": "Heinous", "head": "Crimes Against Women",
     "bns": "BNS 80(2)", "ipc": "IPC 304B", "punishment": "Minimum 7 years, up to life",
     "cognizable": True, "bailable": False, "court": "Court of Session",
     "acts": ["Dowry Prohibition Act 1961"]},
    {"sub": "Assault to Outrage Modesty", "category": "Major", "head": "Crimes Against Women",
     "bns": "BNS 74", "ipc": "IPC 354", "punishment": "1–5 years + fine",
     "cognizable": True, "bailable": False, "court": "Any Magistrate"},
    {"sub": "Cruelty by Husband or Relatives", "category": "Minor", "head": "Crimes Against Women",
     "bns": "BNS 85", "ipc": "IPC 498A", "punishment": "Up to 3 years + fine",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class"},
    {"sub": "Stalking", "category": "Minor", "head": "Crimes Against Women",
     "bns": "BNS 78(2)", "ipc": "IPC 354D", "punishment": "Up to 3 years (first conviction)",
     "cognizable": True, "bailable": True, "court": "Any Magistrate"},

    # Economic offences
    {"sub": "Counterfeit Currency (FICN)", "category": "Heinous", "head": "Economic Offences",
     "bns": "BNS 178", "ipc": "IPC 489A", "punishment": "Imprisonment for life, or up to 10 years",
     "cognizable": True, "bailable": False, "court": "Court of Session"},
    {"sub": "Cheating", "category": "Major", "head": "Economic Offences",
     "bns": "BNS 318(4)", "ipc": "IPC 420", "punishment": "Up to 7 years + fine",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class"},
    {"sub": "Criminal Breach of Trust", "category": "Major", "head": "Economic Offences",
     "bns": "BNS 316(2)", "ipc": "IPC 406", "punishment": "Up to 5 years + fine",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class"},
    {"sub": "Forgery for Cheating", "category": "Major", "head": "Economic Offences",
     "bns": "BNS 336(3)", "ipc": "IPC 468", "punishment": "Up to 7 years + fine",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class"},
    {"sub": "Money Laundering / Hawala", "category": "Major", "head": "Economic Offences",
     "bns": None, "ipc": None, "sll": "PMLA 2002 Sec 3 r/w 4", "punishment": "3–7 years (10 years if NDPS-linked)",
     "cognizable": True, "bailable": False, "court": "Special Court (PMLA)",
     "acts": ["Prevention of Money-Laundering Act 2002", "FEMA 1999"]},

    # Cyber crimes
    {"sub": "Online Fraud (Cheating by Personation)", "category": "Major", "head": "Cyber Crimes",
     "bns": "BNS 319(2)", "ipc": "IPC 419", "sll": "IT Act 2000 Sec 66D", "punishment": "Up to 5 years (BNS) / 3 years (IT Act)",
     "cognizable": True, "bailable": True, "court": "Magistrate First Class",
     "acts": ["Information Technology Act 2000"]},
    {"sub": "Identity Theft", "category": "Minor", "head": "Cyber Crimes",
     "bns": None, "ipc": None, "sll": "IT Act 2000 Sec 66C", "punishment": "Up to 3 years + fine up to ₹1 lakh",
     "cognizable": True, "bailable": True, "court": "Magistrate First Class",
     "acts": ["Information Technology Act 2000"]},
    {"sub": "Hacking / Computer-related Offence", "category": "Minor", "head": "Cyber Crimes",
     "bns": None, "ipc": None, "sll": "IT Act 2000 Sec 66", "punishment": "Up to 3 years or fine up to ₹5 lakh",
     "cognizable": True, "bailable": True, "court": "Magistrate First Class",
     "acts": ["Information Technology Act 2000"]},

    # Organised crime (new chapter in BNS)
    {"sub": "Organised Crime Syndicate Activity", "category": "Heinous", "head": "Organised Crime",
     "bns": "BNS 111(3)", "ipc": "IPC 120B", "punishment": "Minimum 5 years, up to life + fine ≥ ₹5 lakh",
     "cognizable": True, "bailable": False, "court": "Court of Session",
     "acts": ["State organised-crime laws (e.g. MCOCA 1999)"]},
    {"sub": "Petty Organised Crime", "category": "Major", "head": "Organised Crime",
     "bns": "BNS 112(2)", "ipc": None, "punishment": "1–7 years + fine",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class"},
    {"sub": "Rioting", "category": "Minor", "head": "Offences Against Public Tranquillity",
     "bns": "BNS 191(2)", "ipc": "IPC 147", "punishment": "Up to 2 years or fine",
     "cognizable": True, "bailable": True, "court": "Any Magistrate"},

    # Special & Local Laws
    {"sub": "Drug Trafficking (Commercial Qty)", "category": "Heinous", "head": "Special & Local Laws (SLL)",
     "bns": None, "ipc": None, "sll": "NDPS Act 1985 Sec 21(c)", "punishment": "10–20 years RI + fine ₹1–2 lakh",
     "cognizable": True, "bailable": False, "court": "Special Court (NDPS)",
     "acts": ["NDPS Act 1985"]},
    {"sub": "Drug Possession (Small Qty)", "category": "Minor", "head": "Special & Local Laws (SLL)",
     "bns": None, "ipc": None, "sll": "NDPS Act 1985 Sec 20(b)(ii)(A)", "punishment": "Up to 1 year or fine up to ₹10,000",
     "cognizable": True, "bailable": True, "court": "Special Court (NDPS)",
     "acts": ["NDPS Act 1985"]},
    {"sub": "Arms Manufacture / Sale", "category": "Heinous", "head": "Special & Local Laws (SLL)",
     "bns": None, "ipc": None, "sll": "Arms Act 1959 Sec 25(1)(a)", "punishment": "7 years to life + fine",
     "cognizable": True, "bailable": False, "court": "Court of Session",
     "acts": ["Arms Act 1959"]},
    {"sub": "Illegal Arms Possession", "category": "Minor", "head": "Special & Local Laws (SLL)",
     "bns": None, "ipc": None, "sll": "Arms Act 1959 Sec 25(1B)(a)", "punishment": "1–3 years + fine",
     "cognizable": True, "bailable": False, "court": "Magistrate First Class",
     "acts": ["Arms Act 1959"]},
    {"sub": "Gambling / Betting Racket", "category": "Minor", "head": "Special & Local Laws (SLL)",
     "bns": None, "ipc": None, "sll": "Public Gambling Act 1867 Sec 3/4 (or State Gaming Act)",
     "punishment": "Fine and/or short imprisonment (varies by State)",
     "cognizable": True, "bailable": True, "court": "Any Magistrate",
     "acts": ["Public Gambling Act 1867"]},
]

CRIME_BY_SUB = {c["sub"]: c for c in CRIME_CATALOG}


def crime_hierarchy():
    """Category -> Crime head -> [sub-categories]."""
    tree = {}
    for c in CRIME_CATALOG:
        tree.setdefault(c["category"], {}).setdefault(c["head"], []).append(c["sub"])
    return {cat: tree.get(cat, {}) for cat in CATEGORIES}


def sections_for(crime, fir_date, n_accused):
    """Sections invoked in an FIR, using IPC before 1 July 2024 and BNS after."""
    on_or_after_bns = fir_date >= NEW_LAWS_EFFECTIVE
    general = crime["bns"] if on_or_after_bns else crime["ipc"]
    secs = []
    if general:
        secs.append(general)
    if crime.get("sll"):
        secs.append(crime["sll"])
    if n_accused > 1 and general:
        secs.append("BNS 3(5)" if on_or_after_bns else "IPC 34")   # common intention
    regime = "BNS 2023" if on_or_after_bns else "IPC 1860"
    if not general and crime.get("sll"):
        regime = "Special Act"
    return secs, regime


FIR_STATUSES = [
    "Registered", "Under Investigation", "Chargesheet Filed",
    "Pending Trial", "Convicted", "Acquitted", "Final Report (Closure)",
]

# Severity used by the threat-scoring model, derived from category.
SEVERITY_BY_CATEGORY = {
    "Heinous": ["Critical", "Critical", "High"],
    "Major": ["High", "High", "Medium"],
    "Minor": ["Medium", "Low", "Low"],
}

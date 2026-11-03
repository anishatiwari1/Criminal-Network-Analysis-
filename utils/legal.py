"""
Legal reference for the "Possible Lawful Action" tab.

Static, curated content on India's current criminal laws (in force since
1 July 2024), the procedural steps police can take under BNSS 2023, crime-
specific options, official portals, and a live news feed (Google News RSS,
fetched by the server with a short cache and an offline fallback).

This is a reference aid for analysts, not legal advice.
"""

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

INDIA_CODE = "https://www.indiacode.nic.in/handle/123456789/"

LAWS = [
    {"short": "BNS 2023", "name": "Bharatiya Nyaya Sanhita, 2023", "replaces": "Indian Penal Code, 1860",
     "type": "Substantive criminal law", "in_force": "1 July 2024",
     "summary": "Defines offences and punishments. Adds organised crime (s.111), petty organised crime (s.112), "
                "terrorist act (s.113), snatching (s.304) and community service as a punishment.",
     "url": INDIA_CODE + "20062"},
    {"short": "BNSS 2023", "name": "Bharatiya Nagarik Suraksha Sanhita, 2023", "replaces": "Code of Criminal Procedure, 1973",
     "type": "Criminal procedure", "in_force": "1 July 2024",
     "summary": "Procedure for FIR, investigation, arrest, bail and trial. Zero FIR and e-FIR (s.173), mandatory "
                "forensics for 7+ year offences (s.176(3)), video-recorded search (s.105), trial in absentia (s.356).",
     "url": INDIA_CODE + "21180"},
    {"short": "BSA 2023", "name": "Bharatiya Sakshya Adhiniyam, 2023", "replaces": "Indian Evidence Act, 1872",
     "type": "Law of evidence", "in_force": "1 July 2024",
     "summary": "Rules of evidence. Electronic and digital records are treated as documents; admissibility of "
                "electronic records needs a certificate under s.63.",
     "url": INDIA_CODE + "20063"},
    {"short": "NDPS Act", "name": "Narcotic Drugs and Psychotropic Substances Act, 1985", "replaces": None,
     "type": "Special law", "in_force": "In force",
     "summary": "Drug offences graded by small / intermediate / commercial quantity. Strict bail conditions (s.37) "
                "and forfeiture of illegally acquired property (Chapter VA).",
     "url": INDIA_CODE + "15315"},
    {"short": "Arms Act", "name": "Arms Act, 1959", "replaces": None, "type": "Special law", "in_force": "In force",
     "summary": "Licensing of firearms; s.25 punishes illegal manufacture, sale and possession of arms.",
     "url": INDIA_CODE + "1398"},
    {"short": "PMLA", "name": "Prevention of Money-Laundering Act, 2002", "replaces": None, "type": "Special law",
     "in_force": "In force",
     "summary": "Money laundering (s.3, punishment s.4). Enforcement Directorate can provisionally attach "
                "proceeds of crime (s.5). Twin conditions for bail (s.45).",
     "url": INDIA_CODE + "2036"},
    {"short": "IT Act", "name": "Information Technology Act, 2000", "replaces": None, "type": "Special law",
     "in_force": "In force",
     "summary": "Cyber offences: s.66 (computer-related), 66C (identity theft), 66D (cheating by personation), "
                "67 (obscene content); blocking orders under s.69A.",
     "url": INDIA_CODE + "15412"},
    {"short": "UAPA", "name": "Unlawful Activities (Prevention) Act, 1967", "replaces": None, "type": "Special law",
     "in_force": "In force",
     "summary": "Terrorism, terror funding (s.17) and unlawful associations; investigated by State police or NIA.",
     "url": INDIA_CODE + "1470"},
    {"short": "POCSO", "name": "Protection of Children from Sexual Offences Act, 2012", "replaces": None,
     "type": "Special law", "in_force": "In force",
     "summary": "Sexual offences against children, mandatory reporting (s.19) and child-friendly procedure.",
     "url": INDIA_CODE + "2079"},
    {"short": "State laws", "name": "State organised-crime & Goonda Acts (e.g. MCOCA 1999, UP Gangsters Act 1986)",
     "replaces": None, "type": "State law", "in_force": "Varies by State",
     "summary": "Special procedure and preventive detention for organised gangs and habitual offenders; "
                "search the State's Act on India Code.",
     "url": "https://www.indiacode.nic.in/"},
]

# Procedural steps under BNSS / BSA, in the order they usually happen.
PROCEDURE = [
    {"step": "Register FIR", "law": "BNSS s.173",
     "detail": "Cognizable offence must be registered; can be a Zero FIR at any station or an e-FIR. Copy of FIR "
               "free to the informant. For 3–7 year offences a preliminary enquiry within 14 days is allowed (s.173(3))."},
    {"step": "Non-cognizable report", "law": "BNSS s.174",
     "detail": "For non-cognizable offences the information is entered in the station diary and the informant "
               "is referred to the Magistrate."},
    {"step": "Investigation & forensics", "law": "BNSS s.176",
     "detail": "Forensic expert must visit the crime scene for offences punishable with 7 years or more (s.176(3))."},
    {"step": "Search & seizure on video", "law": "BNSS s.105",
     "detail": "Search and seizure to be recorded by audio-video electronic means and sent to the Magistrate."},
    {"step": "Arrest or notice of appearance", "law": "BNSS s.35",
     "detail": "Arrest without warrant only on stated grounds; for offences up to 7 years a notice of appearance "
               "(s.35(3)) is the norm. Arrested person's relative must be informed (s.48)."},
    {"step": "Police custody / remand", "law": "BNSS s.187",
     "detail": "Produce before Magistrate within 24 hours; police custody up to 15 days in total, which may be "
               "taken in parts within the first 40 or 60 days."},
    {"step": "Bail", "law": "BNSS s.478 / 480 / 482",
     "detail": "Bail is a right in bailable offences (s.478); discretionary in non-bailable offences (s.480); "
               "anticipatory bail by Sessions Court / High Court (s.482)."},
    {"step": "Proclaimed offender & attachment", "law": "BNSS s.84 / 85",
     "detail": "Proclamation for an absconding accused and attachment of their property."},
    {"step": "Attach proceeds of crime", "law": "BNSS s.107",
     "detail": "Magistrate can order attachment, forfeiture or restoration of property derived from crime."},
    {"step": "Chargesheet (final report)", "law": "BNSS s.193",
     "detail": "Report on completion of investigation; informant/victim to be told of progress within 90 days. "
               "Default bail if not filed within 60/90 days of remand (s.187(3))."},
    {"step": "Electronic evidence", "law": "BSA s.63",
     "detail": "CDRs, CCTV, chats and bank statements need the s.63 certificate to be admissible."},
    {"step": "Trial in absentia", "law": "BNSS s.356",
     "detail": "A proclaimed offender who absconds can be tried and judged in absentia."},
    {"step": "Witness protection", "law": "BNSS s.398",
     "detail": "Every State to notify a Witness Protection Scheme."},
]

# Extra crime-head specific options.
HEAD_ACTIONS = {
    "Offences Affecting the Human Body": [
        "Dying declaration / medical-legal certificate; post-mortem for death cases.",
        "Victim compensation under the State Victim Compensation Scheme (BNSS s.396).",
    ],
    "Offences Against Property": [
        "Circulate stolen-property details on CCTNS and to nearby stations; check pawn shops and scrap dealers.",
        "Vehicle theft: flag the registration on the VAHAN / CCTNS vehicle search.",
        "Return of seized property to the owner on interim custody (BNSS s.497/503).",
    ],
    "Crimes Against Women": [
        "Statement of the victim by a woman police officer, video recorded where possible.",
        "Investigation of rape and certain sexual offences to be completed within 2 months (BNSS s.193(2)).",
        "Protection orders under the Protection of Women from Domestic Violence Act, 2005 where relevant.",
    ],
    "Economic Offences": [
        "Freeze bank accounts and attach proceeds (BNSS s.107); refer to Enforcement Directorate if a PMLA scheduled offence.",
        "Obtain bank KYC, statements and s.63 BSA certificates.",
        "For fake currency, send notes to the RBI / Currency Note Press for examination.",
    ],
    "Cyber Crimes": [
        "Report on the National Cyber Crime Reporting Portal (cybercrime.gov.in) or helpline 1930 for quick fund freezing.",
        "Preserve logs with the intermediary; request data under IT Act s.79 and BNSS s.94.",
        "Seek blocking of URLs / numbers through the designated nodal officer (IT Act s.69A).",
    ],
    "Organised Crime": [
        "Invoke BNS s.111 (organised crime) or s.112 (petty organised crime) and State organised-crime laws.",
        "Map the syndicate: continuing unlawful activity needs more than one chargesheet in 10 years.",
        "Attach property of the syndicate and proclaim absconding members (BNSS s.84/85/107).",
    ],
    "Offences Against Public Tranquillity": [
        "Preventive orders under BNSS s.163 (prohibitory orders) and security for keeping peace (s.126/129).",
        "Identify instigators from video footage and social media.",
    ],
    "Special & Local Laws (SLL)": [
        "NDPS: search and seizure as per s.42/43/50, inventory before a Magistrate (s.52A), forfeiture under Chapter VA.",
        "Arms Act: seize the weapon, send to FSL for ballistic report, check licence status.",
        "Preventive detention under the PIT-NDPS Act 1988 or State Goonda Act for repeat offenders.",
    ],
}

PORTALS = [
    {"name": "India Code (all Central & State Acts)", "url": "https://www.indiacode.nic.in/"},
    {"name": "BPR&D: New Criminal Laws resources", "url": "https://bprd.nic.in/page/new_criminal_laws"},
    {"name": "Ministry of Home Affairs", "url": "https://www.mha.gov.in/"},
    {"name": "NCRB: Crime in India reports", "url": "https://www.ncrb.gov.in/"},
    {"name": "Digital Police Portal (CCTNS, e-FIR services)", "url": "https://digitalpolice.gov.in/"},
    {"name": "National Cyber Crime Reporting Portal", "url": "https://cybercrime.gov.in/"},
    {"name": "eCourts Services (case status)", "url": "https://ecourts.gov.in/"},
    {"name": "NALSA: Free legal aid", "url": "https://nalsa.gov.in/"},
    {"name": "Press Information Bureau (official releases)", "url": "https://pib.gov.in/"},
]

HELPLINES = [
    {"name": "Emergency (Police / Fire / Ambulance)", "number": "112"},
    {"name": "Cyber fraud helpline", "number": "1930"},
    {"name": "Women helpline", "number": "181"},
    {"name": "Child helpline", "number": "1098"},
    {"name": "NALSA legal aid", "number": "15100"},
]

NEWS_TOPICS = {
    "new-laws": "Bharatiya Nyaya Sanhita OR BNSS OR \"Bharatiya Sakshya\"",
    "supreme-court": "Supreme Court criminal law judgment India",
    "cyber": "cyber fraud India police arrest",
    "ndps": "NDPS drugs seizure India",
    "organised": "organised crime gang India police",
    "women": "crime against women India court",
}

FALLBACK_NEWS = [
    {"title": "PIB: Press releases from the Ministry of Home Affairs", "link": "https://pib.gov.in/", "source": "PIB", "published": ""},
    {"title": "BPR&D: New Criminal Laws updates and handbooks", "link": "https://bprd.nic.in/page/new_criminal_laws", "source": "BPR&D", "published": ""},
    {"title": "MHA: Latest notifications", "link": "https://www.mha.gov.in/", "source": "MHA", "published": ""},
    {"title": "Google News: Bharatiya Nyaya Sanhita",
     "link": "https://news.google.com/search?q=Bharatiya%20Nyaya%20Sanhita&hl=en-IN&gl=IN&ceid=IN%3Aen",
     "source": "Google News", "published": ""},
]

_news_cache = {}
NEWS_TTL = 30 * 60


def fetch_news(topic="new-laws", limit=12):
    """Latest headlines from Google News RSS (India edition), cached for 30 minutes."""
    query = NEWS_TOPICS.get(topic, NEWS_TOPICS["new-laws"])
    cached = _news_cache.get(topic)
    if cached and time.time() - cached[0] < NEWS_TTL:
        return {"topic": topic, "live": True, "items": cached[1]}

    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 CrimeGraph/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            root = ET.fromstring(resp.read())
        items = []
        for item in root.iter("item"):
            source = item.find("source")
            items.append({
                "title": item.findtext("title", ""),
                "link": item.findtext("link", ""),
                "published": item.findtext("pubDate", ""),
                "source": source.text if source is not None else "",
            })
            if len(items) >= limit:
                break
        _news_cache[topic] = (time.time(), items)
        return {"topic": topic, "live": True, "items": items}
    except Exception as e:  # offline or blocked: show official links instead
        return {"topic": topic, "live": False, "error": str(e), "items": FALLBACK_NEWS}


def actions_for_fir(fir, crime):
    """Possible lawful actions for one FIR, based on its crime and status."""
    actions = []
    if not crime:
        return actions
    seven_plus = crime["category"] == "Heinous" or any(
        x in crime["punishment"] for x in ("7 years", "10 years", "14 years", "life"))
    actions.append(f"Offence is {'cognizable' if crime['cognizable'] else 'non-cognizable'} and "
                   f"{'bailable' if crime['bailable'] else 'non-bailable'}; triable by {crime['court']}.")
    if seven_plus:
        actions.append("Punishable with 7 years or more: forensic team visit is mandatory (BNSS s.176(3)) and "
                       "arrest without warrant is permitted on the grounds in BNSS s.35.")
    else:
        actions.append("Punishable with less than 7 years: issue notice of appearance (BNSS s.35(3)) unless arrest "
                       "is necessary for reasons recorded in writing.")
    if crime["bailable"]:
        actions.append("Accused is entitled to bail as of right (BNSS s.478).")
    else:
        actions.append("Bail is at the court's discretion (BNSS s.480); oppose bail with criminal antecedents if a history-sheeter.")
    if fir.get("amount_involved"):
        actions.append("Money involved: move to attach proceeds of crime (BNSS s.107) and freeze linked accounts.")
    if len(fir.get("accused_ids", [])) >= 3:
        actions.append("Three or more accused acting together: examine BNS s.111/112 (organised crime) and "
                       "BNS s.61 (criminal conspiracy).")
    if fir.get("status") in ("Registered", "Under Investigation"):
        actions.append("Inform the victim/informant of investigation progress within 90 days (BNSS s.193(3)).")
    actions.extend(HEAD_ACTIONS.get(crime["head"], []))
    return actions

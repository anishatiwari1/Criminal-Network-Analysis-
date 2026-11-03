"""
Flask web application for AI-Powered Criminal Network Analysis System
SIH26189 – Ministry of Home Affairs
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from datetime import timedelta
import json
import threading
import os
import sys

# Add parent dir to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from utils.analyzer import CriminalNetworkAnalyzer
from utils import legal, auth, records, investigations

sys.path.insert(0, os.path.join(BASE_DIR, "data"))
import india_reference as ref

app = Flask(__name__)
app.secret_key = auth.secret_key()
app.permanent_session_lifetime = timedelta(hours=8)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

# ─── Initialize Analyzer ─────────────────────────────────────────────────────
DATA_DIR = os.path.join(BASE_DIR, "data")
analyzer = CriminalNetworkAnalyzer(DATA_DIR)

def ensure_data():
    """Generate data if not present."""
    if not os.path.exists(os.path.join(DATA_DIR, "persons.json")):
        print("Generating dataset...")
        import generate_dataset
        generate_dataset.main(DATA_DIR)

ensure_data()
analyzer.run()
cases = investigations.load(DATA_DIR, analyzer.firs)
write_lock = threading.Lock()


def rebuild_analyzer():
    """Reload data and recompute the graph, scores and groups after an edit."""
    analyzer.__init__(DATA_DIR)
    analyzer.run()


# ─── Authentication (admins only) ────────────────────────────────────────────
@app.before_request
def require_login():
    if request.endpoint in ("login", "static") or session.get("user"):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Login required"}), 401
    return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = auth.authenticate(request.form.get("username"), request.form.get("password"))
        if user:
            session.clear()
            session.permanent = True
            session["user"] = user
            nxt = request.args.get("next", "/")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else "/")
        error = "Invalid username or password, or the account is not an admin."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/me")
def api_me():
    return jsonify(session.get("user"))

# ─── Filter helpers ───────────────────────────────────────────────────────────
def in_range(d, start, end):
    """d, start, end are 'YYYY-MM-DD' strings (d may include a time)."""
    d = (d or "")[:10]
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def filter_firs(args):
    """Apply query-string filters shared by /api/firs and /api/analytics."""
    start, end = args.get("start", ""), args.get("end", "")
    state, district = args.get("state", ""), args.get("district", "")
    category, head = args.get("category", ""), args.get("head", "")
    crime_type = args.get("crime_type", "")
    results = analyzer.firs
    if start or end:
        results = [f for f in results if in_range(f.get("date"), start, end)]
    if state:
        results = [f for f in results if f.get("state") == state]
    if district:
        results = [f for f in results if f.get("district") == district]
    if category:
        results = [f for f in results if f.get("crime_category") == category]
    if head:
        results = [f for f in results if f.get("crime_head") == head]
    if crime_type:
        results = [f for f in results if f.get("crime_type") == crime_type]
    return results


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", user=session.get("user"))

@app.route("/api/meta")
def api_meta():
    """Dropdown options: states/districts, crime hierarchy, years, statuses."""
    years = sorted({f["date"][:4] for f in analyzer.firs if f.get("date")}, reverse=True)
    dates = sorted(f["date"] for f in analyzer.firs if f.get("date"))
    return jsonify({
        "states": {st: list(v["districts"].keys()) for st, v in ref.STATES.items()},
        "police_stations": {d: [f"{ps} PS" for ps in stations]
                            for v in ref.STATES.values() for d, stations in v["districts"].items()},
        "localities": ref.LOCALITIES,
        "organizations": sorted({p["organization"] for p in analyzer.persons if p.get("organization")}),
        "roles": sorted({p["role"] for p in analyzer.persons if p.get("role")}),
        "crime_hierarchy": ref.crime_hierarchy(),
        "category_info": ref.CATEGORY_INFO,
        "fir_statuses": ref.FIR_STATUSES,
        "years": years,
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
    })

@app.route("/api/stats")
def api_stats():
    return jsonify(analyzer.get_network_stats())

@app.route("/api/graph")
def api_graph():
    return jsonify(analyzer.get_graph_data())

@app.route("/api/suspects")
def api_suspects():
    n = int(request.args.get("n", 10))
    suspects = analyzer.get_top_suspects(n)
    return jsonify(suspects)

@app.route("/api/persons")
def api_persons():
    search = request.args.get("search", "").lower()
    role = request.args.get("role", "")
    status = request.args.get("status", "")
    location = request.args.get("location", "")

    results = analyzer.persons
    if search:
        results = [p for p in results if search in p["name"].lower()
                   or search in (p.get("alias") or "").lower()
                   or search in p["id"].lower()]
    if role:
        results = [p for p in results if p.get("role") == role]
    if status:
        results = [p for p in results if p.get("status") == status]
    if location:
        results = [p for p in results if p.get("location") == location]

    sort_by = request.args.get("sort", "computed_threat_score")
    results = sorted(results, key=lambda p: p.get(sort_by, 0), reverse=True)
    return jsonify(results)

@app.route("/api/person/<pid>")
def api_person_detail(pid):
    person = next((p for p in analyzer.persons if p["id"] == pid), None)
    if not person:
        return jsonify({"error": "Not found"}), 404

    # Related FIRs
    related_firs = [f for f in analyzer.firs if pid in f.get("accused_ids", [])]
    # Related CDRs
    related_cdrs = [c for c in analyzer.cdrs if c["caller_id"] == pid or c["receiver_id"] == pid][:20]
    # Related transactions
    related_txns = [t for t in analyzer.transactions if t["sender_id"] == pid or t["receiver_id"] == pid][:20]
    # Network neighbors
    neighbors = analyzer.graph.neighbors(pid)
    neighbor_persons = [next((p for p in analyzer.persons if p["id"] == n), {"id": n, "name": n}) for n in neighbors]

    return jsonify({
        "person": person,
        "firs": related_firs,
        "cdrs": related_cdrs,
        "transactions": related_txns,
        "neighbors": neighbor_persons,
    })

@app.route("/api/firs")
def api_firs():
    severity = request.args.get("severity", "")
    status = request.args.get("status", "")
    search = request.args.get("search", "").lower()

    results = filter_firs(request.args)
    if severity:
        results = [f for f in results if f.get("severity") == severity]
    if status:
        results = [f for f in results if f.get("status") == status]
    if search:
        results = [f for f in results if search in f["fir_id"].lower()
                   or search in f.get("cctns_id", "")
                   or search in f.get("police_station", "").lower()
                   or any(search in s.lower() for s in f.get("sections", []))
                   or any(search in n.lower() for n in f.get("accused_names", []))]
    return jsonify(results)

@app.route("/api/fir/<path:fir_id>")
def api_fir_detail(fir_id):
    fir = next((f for f in analyzer.firs if f["fir_id"] == fir_id), None)
    if not fir:
        return jsonify({"error": "Not found"}), 404
    crime = ref.CRIME_BY_SUB.get(fir.get("crime_type"))
    accused = [next((p for p in analyzer.persons if p["id"] == pid), {"id": pid, "name": pid})
               for pid in fir.get("accused_ids", [])]
    return jsonify({
        "fir": fir,
        "crime": crime,
        "accused": accused,
        "lawful_actions": legal.actions_for_fir(fir, crime),
    })

@app.route("/api/legal")
def api_legal():
    return jsonify({
        "laws": legal.LAWS,
        "procedure": legal.PROCEDURE,
        "head_actions": legal.HEAD_ACTIONS,
        "portals": legal.PORTALS,
        "helplines": legal.HELPLINES,
        "news_topics": list(legal.NEWS_TOPICS.keys()),
        "crime_catalog": ref.CRIME_CATALOG,
        "category_info": ref.CATEGORY_INFO,
    })

@app.route("/api/news")
def api_news():
    return jsonify(legal.fetch_news(request.args.get("topic", "new-laws")))

# ─── Add records ──────────────────────────────────────────────────────────────
@app.route("/api/records/sample")
def api_record_sample():
    return jsonify(records.sample_record(analyzer.persons, analyzer.firs, analyzer.surveillance))


@app.route("/api/records/check", methods=["POST"])
def api_record_check():
    """Preview links for a record without saving it."""
    rec = request.get_json(force=True) or {}
    return jsonify(records.find_links(rec, analyzer.persons, analyzer.firs, analyzer.cdrs, analyzer.surveillance))


@app.route("/api/records", methods=["GET", "POST"])
def api_records():
    if request.method == "GET":
        added = [p for p in analyzer.persons if p.get("added_by")]
        return jsonify(sorted(added, key=lambda p: p.get("added_on", ""), reverse=True))
    rec = request.get_json(force=True) or {}
    with write_lock:
        try:
            person, links = records.add_person(DATA_DIR, rec, session["user"]["username"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        rebuild_analyzer()
    person = next(p for p in analyzer.persons if p["id"] == person["id"])
    return jsonify({"person": person, "links": links}), 201


# ─── Investigation tracking ──────────────────────────────────────────────────
@app.route("/api/investigations")
def api_investigations():
    from datetime import date
    today = date.today()
    items = [investigations.enrich(c, today) for c in cases]
    open_items = [c for c in items if c["status"] == "Open"]
    summary = {
        "open": len(open_items),
        "overdue": sum(1 for c in open_items if c["overdue"]),
        "due_15": sum(1 for c in open_items if c["days_to_deadline"] is not None and 0 <= c["days_to_deadline"] <= 15),
        "chargesheeted": sum(1 for c in items if c["stage_index"] >= 5),
        "closed": sum(1 for c in items if c["status"] == "Closed"),
    }
    without_case = [f for f in analyzer.firs if f["fir_id"] not in {c["fir_id"] for c in cases}]
    return jsonify({
        "stages": investigations.STAGES,
        "summary": summary,
        "items": sorted(items, key=lambda c: (c["status"] != "Open", not c["overdue"],
                                              c["days_to_deadline"] if c["days_to_deadline"] is not None else 9999,
                                              c["priority"])),
        "firs_without_case": [{"fir_id": f["fir_id"], "crime_type": f["crime_type"], "date": f["date"]}
                              for f in without_case],
    })


@app.route("/api/investigations/<case_id>/update", methods=["POST"])
def api_investigation_update(case_id):
    body = request.get_json(force=True) or {}
    with write_lock:
        try:
            case = investigations.add_update(DATA_DIR, cases, case_id, body.get("stage_index"),
                                             body.get("note", ""), session["user"]["name"], body.get("arrest_date"))
        except KeyError:
            return jsonify({"error": "Not found"}), 404
        except (ValueError, TypeError) as e:
            return jsonify({"error": str(e)}), 400
    return jsonify(investigations.enrich(case))


@app.route("/api/investigations", methods=["POST"])
def api_investigation_open():
    body = request.get_json(force=True) or {}
    fir = next((f for f in analyzer.firs if f["fir_id"] == body.get("fir_id")), None)
    if not fir:
        return jsonify({"error": "FIR not found"}), 404
    with write_lock:
        try:
            case = investigations.open_case(DATA_DIR, cases, fir, session["user"]["name"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    return jsonify(investigations.enrich(case)), 201


@app.route("/api/transactions")
def api_transactions():
    suspicious_only = request.args.get("suspicious", "false") == "true"
    results = analyzer.transactions
    if suspicious_only:
        results = [t for t in results if t.get("suspicious")]
    results = sorted(results, key=lambda t: t.get("amount", 0), reverse=True)
    return jsonify(results[:100])

@app.route("/api/cdrs")
def api_cdrs():
    suspicious_only = request.args.get("suspicious", "false") == "true"
    results = analyzer.cdrs
    if suspicious_only:
        results = [c for c in results if c.get("suspicious")]
    return jsonify(results[:100])

@app.route("/api/communities")
def api_communities():
    communities = analyzer.metrics.get("communities", [])
    result = []
    for i, comm in enumerate(communities):
        if len(comm) < 2:
            continue
        members = [next((p for p in analyzer.persons if p["id"] == pid), {"id": pid, "name": pid}) for pid in comm]
        avg_threat = sum(m.get("computed_threat_score", 0) for m in members) / len(members)
        result.append({
            "community_id": i,
            "size": len(comm),
            "members": members,
            "avg_threat_score": round(avg_threat, 3),
            "high_risk": avg_threat > 0.5,
        })
    result = sorted(result, key=lambda c: c["avg_threat_score"], reverse=True)
    return jsonify(result)

@app.route("/api/surveillance")
def api_surveillance():
    risk = request.args.get("risk_level", "")
    results = analyzer.surveillance
    if risk:
        results = [s for s in results if s.get("risk_level") == risk]
    return jsonify(results)

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").lower()
    if not q or len(q) < 2:
        return jsonify([])

    results = []
    for p in analyzer.persons:
        if q in p["name"].lower() or q in (p.get("alias") or "").lower() or q in p["id"].lower():
            results.append({"type": "person", "id": p["id"], "label": p["name"], "sublabel": p.get("role", "")})

    for f in analyzer.firs:
        if (q in f["fir_id"].lower() or q in f.get("crime_type", "").lower()
                or q in f.get("police_station", "").lower() or q in f.get("district", "").lower()):
            results.append({"type": "fir", "id": f["fir_id"], "label": f["fir_id"],
                            "sublabel": f"{f.get('crime_type', '')} · {f.get('police_station', '')}, {f.get('district', '')}"})

    return jsonify(results[:20])

@app.route("/api/filter_graph")
def api_filter_graph():
    """Return filtered graph based on criteria."""
    min_threat = float(request.args.get("min_threat", 0))
    community_id = request.args.get("community", "")
    location = request.args.get("location", "")

    graph_data = analyzer.get_graph_data()
    nodes = graph_data["nodes"]
    links = graph_data["links"]

    if min_threat > 0:
        nodes = [n for n in nodes if n.get("threat_score", 0) >= min_threat]
    if community_id:
        nodes = [n for n in nodes if str(n.get("community", "")) == community_id]
    if location:
        nodes = [n for n in nodes if n.get("location", "") == location]

    node_ids = {n["id"] for n in nodes}
    links = [l for l in links if l["source"] in node_ids and l["target"] in node_ids]

    return jsonify({"nodes": nodes, "links": links})

@app.route("/api/analytics")
def api_analytics():
    """Aggregate analytics for charts. Accepts start, end, state, district, category."""
    from collections import Counter
    args = request.args
    start, end = args.get("start", ""), args.get("end", "")
    state, district = args.get("state", ""), args.get("district", "")
    filtered = bool(start or end or state or district or args.get("category"))

    firs = filter_firs(args)
    # Persons: those accused in the filtered FIRs (all persons when unfiltered)
    if filtered:
        ids = {pid for f in firs for pid in f.get("accused_ids", [])}
        persons = [p for p in analyzer.persons if p["id"] in ids]
    else:
        persons = analyzer.persons
    txns = [t for t in analyzer.transactions
            if in_range(t.get("date"), start, end)
            and (not state or t.get("state") == state)
            and (not district or t.get("location") == district)]

    crime_counts = Counter(f.get("crime_type", "Unknown") for f in firs)
    severity_counts = Counter(f.get("severity", "Unknown") for f in firs)
    status_counts = Counter(p.get("status", "Unknown") for p in persons)
    # Group by district within a state, by state otherwise
    area_key = "district" if state else "state"
    area_counts = Counter(f.get(area_key, "Unknown") for f in firs)
    location_counts = Counter(f.get("district", "Unknown") for f in firs)
    category_counts = Counter(f.get("crime_category", "Unknown") for f in firs)
    head_counts = Counter(f.get("crime_head", "Unknown") for f in firs)
    regime_counts = Counter(f.get("law_regime", "Unknown") for f in firs)
    fir_status_counts = Counter(f.get("status", "Unknown") for f in firs)
    monthly = Counter(f["date"][:7] for f in firs if f.get("date"))
    channel_counts = Counter(t.get("channel", "Unknown") for t in txns)

    # Category -> sub-category counts for the hierarchy table
    hierarchy = {}
    for f in firs:
        cat = hierarchy.setdefault(f.get("crime_category", "Unknown"), {})
        cat[f.get("crime_type", "Unknown")] = cat.get(f.get("crime_type", "Unknown"), 0) + 1

    threat_bins = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for p in persons:
        score = p.get("computed_threat_score", 0)
        idx = min(int(score / 0.2), 4)
        threat_bins[list(threat_bins)[idx]] += 1

    return jsonify({
        "filters": {"start": start, "end": end, "state": state, "district": district,
                    "category": args.get("category", "")},
        "summary": {
            "firs": len(firs),
            "heinous": category_counts.get("Heinous", 0),
            "accused": len({pid for f in firs for pid in f.get("accused_ids", [])}),
            "amount": round(sum(f.get("amount_involved") or 0 for f in firs), 2),
            "suspicious_txns": sum(1 for t in txns if t.get("suspicious")),
        },
        "crime_types": dict(crime_counts),
        "crime_categories": {c: category_counts.get(c, 0) for c in ref.CATEGORIES},
        "crime_heads": dict(head_counts.most_common()),
        "crime_hierarchy_counts": hierarchy,
        "law_regime": dict(regime_counts),
        "fir_status": dict(fir_status_counts),
        "severity": dict(severity_counts),
        "person_status": dict(status_counts),
        "area_level": area_key,
        "area_activity": dict(area_counts.most_common(15)),
        "location_activity": dict(location_counts.most_common(10)),
        "monthly_firs": dict(sorted(monthly.items())),
        "transaction_channels": dict(channel_counts),
        "threat_distribution": threat_bins,
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  AI-Powered Criminal Network Analysis System")
    print("  SIH26189 – Ministry of Home Affairs")
    print("=" * 60)
    print(f"  Server: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)

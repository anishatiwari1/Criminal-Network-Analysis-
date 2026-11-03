# 🔍 CrimeGraph AI — Criminal Network Analysis System
### SIH26189 | Ministry of Home Affairs, India | Smart India Hackathon 2026

---

## 📌 Project Overview

**CrimeGraph AI** is an AI-powered criminal network analysis system that ingests multi-source intelligence data — FIRs, CDRs, financial transaction records, surveillance reports, and criminal histories — and automatically uncovers hidden criminal networks, ranks suspects by threat level, and presents actionable intelligence through an interactive visual dashboard.

---

## 🇮🇳 What's new in the India edition

| # | Change | Where |
|---|--------|-------|
| 1 | **All-Indian synthetic dataset**: Indian names and aliases, 14 States/UTs, 33 districts, ~120 real police-station names, Indian vehicle numbers (RTO codes), +91 mobiles, Jio/Airtel/Vi/BSNL CDRs, UPI/NEFT/Hawala transactions, fictional gangs | `data/india_reference.py`, `data/generate_dataset.py` |
| 2 | **Crime hierarchy**: Category (**Heinous / Major / Minor**) → **NCRB crime head** → **sub-category** (Robbery, Dacoity, Snatching, Cheating, Online Fraud, NDPS, Arms Act …) | `CRIME_CATALOG` in `data/india_reference.py` |
| 3 | **Real-style FIR identifiers** and sections: `STATE/DISTRICT/PS/FIR-No/YEAR` (e.g. `DL/NED/WELC/0186/2026`) plus a 17-digit CCTNS-style ID (Census state code + district + PS + year + serial). Sections are **IPC 1860** for FIRs before 1 July 2024 and **BNS 2023** after, with Special Acts (NDPS, Arms, PMLA, IT Act) | FIR Records tab, FIR detail popup |
| 4 | **Analytics filters**: period (last 30 days / 3 / 6 / 12 months, per year, before/after BNS, custom date range), State/UT, District (area), Category | Analytics tab, `/api/analytics` |
| 5 | **Possible Lawful Action tab**: BNS/BNSS/BSA and special Acts with links to official text on India Code, BNSS procedure steps, crime-wise actions, official portals & helplines, **live news** (Google News RSS, India edition) | Lawful Action tab, `utils/legal.py` |

Category rule used: **Heinous** = death / life imprisonment or minimum 7 years; **Major** = maximum above 3 years; **Minor** = maximum up to 3 years.

> FIR numbering differs slightly between States; the format here follows the common CCTNS pattern
> (State → District → Police Station → serial / year). All people, phone numbers, gangs and cases are fictional.

Also fixed: threat scores are now normalised (previously every suspect scored 100%), criminal groups are detected on strong ties
(previously everyone fell into one group), and D3 / Chart.js are bundled in `static/vendor/` so the app works offline.

---

## 🔐 Admin login, Add Record & Investigation tracking

**Login (admins only).** Every page and API needs an admin login. Demo accounts (created on first run in `data/admins.json`, passwords stored as hashes):

| Username | Password | Name |
|----------|----------|------|
| `admin` | `CrimeGraph@2026` | System Administrator |
| `sp.crime` | `SPCrime@2026` | SP Crime Branch |

Change a password or add an admin: `python -m utils.auth <username> <new-password> "Display Name"`.

**Add Record tab.** Enter a new suspect (identity, phone, numbers they call, state/district/PS, gang, vehicle, linked FIR, known associates).
*Fill sample data* creates a realistic dummy person who is deliberately connected to someone on record. *Check links* previews matches;
*Save record* stores the person and immediately shows who they are related to and why:

| Match | Strength |
|-------|----------|
| Same mobile number | 0.95 (possible same identity) |
| Named as known associate / co-accused in a linked FIR | 0.9 / 0.8 |
| Vehicle named in an FIR / seen in surveillance | 0.75 / 0.55 |
| Contact number belongs to a person / appears in their CDRs | 0.7 / 0.6 |
| Very similar name | 0.6 |
| Same gang, same alias in same district, same locality | 0.5 / 0.45 / 0.3 |

Each match becomes a relationship, so the person appears straight away in Suspects, the Network Graph, threat scoring and Criminal Groups.

**Investigations tab.** One case per open FIR: stage tracker (FIR → forensics → evidence → arrest → remand → chargesheet → trial → closed),
chargesheet deadline per BNSS s.187(3) (90 days from arrest for death / life / 10+ year offences, else 60), overdue alerts, next actions,
timeline of updates, and *Open investigation* for FIRs without a case. Data is saved in `data/investigations.json`
(delete it to regenerate the dummy cases).

---

## 🚀 How to run (Windows / macOS / Linux)

**Prerequisite:** Python 3.8 or newer. Check with `python --version` (Windows) or `python3 --version` (macOS/Linux).

```bash
# 1. Unzip and open a terminal in the project folder
cd criminal_network_analysis

# 2. (Recommended) create a virtual environment
python -m venv venv                 # macOS/Linux: python3 -m venv venv
venv\Scripts\activate               # macOS/Linux: source venv/bin/activate

# 3. Install the only dependency
pip install -r requirements.txt

# 4. Start the app
python run.py                       # macOS/Linux: python3 run.py
```

5. Open **http://127.0.0.1:5000** in your browser and sign in with `admin` / `CrimeGraph@2026`. Stop the server with `Ctrl + C`.

To generate a fresh dataset: `python data/generate_dataset.py` (then restart the app).
Live news needs internet; without it the news panel shows official links instead.

---

## 🏗️ Project Structure

```
criminal_network_analysis/
├── app.py                    # Flask web application (REST API + routes)
├── run.py                    # Quick-start launcher
├── requirements.txt          # Python dependencies
├── data/
│   ├── india_reference.py    # States, districts, police stations, crime hierarchy (BNS/IPC/NCRB)
│   ├── generate_dataset.py   # Synthetic Indian dataset generator
│   ├── persons.json          # 60 suspect profiles
│   ├── firs.json             # 160 FIR records (2022 – Oct 2026)
│   ├── cdrs.json             # 400 Call Detail Records
│   ├── transactions.json     # 250 financial transactions
│   ├── relationships.json    # 180 explicit relationships
│   └── surveillance.json     # 100 surveillance reports
├── utils/
│   ├── __init__.py
│   ├── analyzer.py           # Core analysis engine (graph + ML)
│   └── legal.py              # Laws, BNSS procedure, lawful actions, news feed
├── templates/
│   └── index.html            # Main SPA template
├── static/
│   ├── css/style.css         # Premium dark-mode UI styles
│   ├── js/app.js             # Frontend application (D3.js + Chart.js)
│   └── vendor/               # Bundled d3.min.js and chart.umd.min.js
└── notebooks/
    └── analysis_demo.ipynb   # Jupyter notebook walkthrough
```

---

## ⚙️ Tech Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | **Flask** (Python) | REST API server and template rendering |
| Graph Engine | **Pure Python** (built-in) | Custom graph class, BFS, force layout |
| Centrality | **Custom implementation** | Degree, Betweenness (Brandes), Closeness, PageRank |
| Community Detection | **Label Propagation** | Finding criminal clusters |
| Anomaly Scoring | **Composite weighted formula** | Multi-factor threat scoring |
| Dataset | **Synthetic generator** | Realistic Indian criminal network data |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Network Graph | **D3.js v7** | Interactive force-directed graph visualization |
| Charts | **Chart.js v4** | Bar, doughnut, polar area, line charts |
| UI Framework | **Vanilla CSS + HTML5** | Premium dark intelligence UI |
| Fonts | **Google Fonts (Inter, JetBrains Mono)** | Modern typography |

### Data Science
| Module | Purpose |
|--------|---------|
| `generate_dataset.py` | Synthetic data generation for all entity types |
| `analyzer.py` | Graph construction + all analytics algorithms |
| `analysis_demo.ipynb` | Interactive Jupyter exploration notebook |

---

## 📊 Features

### 1. 🖥️ Intelligence Dashboard
- Live KPI cards (high-risk suspects, FIR count, network nodes, transactions, groups, fugitives)
- Animated number counters
- Top 8 threat-ranked suspects
- Recent FIR feed
- Crime type donut chart
- Threat score distribution bar chart
- Top activity location heatmap bars
- Mini network graph overview

### 2. 🕸️ Network Graph (D3.js)
- Force-directed layout with 50 nodes and 880+ edges
- Node size proportional to threat score
- Color coding: Red (high risk), Orange (medium), Green (low), Purple (fugitive)
- Interactive drag, zoom, pan
- Hover tooltips with full suspect info
- Click-to-open suspect profile modal
- Threat filter slider (filter by minimum threat score)
- Glow effects for high-threat nodes

### 3. 👤 Suspect Database
- Cards for all 50 suspects
- AI threat score badge
- Graph centrality metrics per suspect
- Filter by role, status, location
- Sort by threat score, PageRank, betweenness, FIR count
- Click → detailed modal popup

### 4. 📄 FIR Records
- Full table of 100 FIRs
- Filter by crime type, severity, status
- Color-coded severity badges (Critical/High/Medium/Low)
- Search by FIR ID or accused name

### 5. 💰 Financial Intelligence
- Track 200 transactions across 6 channels
- Suspicious transaction flagging
- Hawala network detection
- Transaction channel polar chart
- KPIs: total, suspicious count, largest amount, hawala count

### 6. 📞 CDR Analysis
- 300 call detail records
- Filter suspicious calls only
- Duration, call type, tower location

### 7. 👥 Criminal Groups (Community Detection)
- Label propagation algorithm
- Groups ranked by average threat score
- Member chips with click-through to profiles
- High-risk group highlighting

### 8. 📈 Analytics
- Crime type breakdown (horizontal bar)
- Monthly FIR trend (line chart)
- Severity distribution (donut)
- Suspect status overview (donut)
- Top 10 activity locations (vertical bar)

### 9. 🔍 Global Search
- Live search across persons, FIRs
- Debounced API calls
- Click result → navigate to relevant tab/modal

### 10. 👤 Suspect Profile Modal
- Full personal details
- Graph metrics (PageRank, Betweenness, Closeness, Degree)
- Related FIRs with severity
- Known associates with click-through links

---

## 🧮 Algorithms

### Threat Scoring Formula
Each feature is divided by its maximum across all persons (so it lies in 0–1), then weighted:
```
score = 0.08 × criminal_history + 0.08 × arrest_count + 0.12 × fir_count
      + 0.14 × severe_firs + 0.12 × heinous_firs + 0.08 × suspicious_calls
      + 0.13 × large_suspicious_txns + 0.13 × betweenness + 0.12 × pagerank
      + 0.15 if Fugitive        (capped at 1.0)
```

### Graph Analytics
- **Degree Centrality** — How many direct connections a suspect has
- **Betweenness Centrality** — Brandes algorithm; identifies brokers/gatekeepers
- **Closeness Centrality** — BFS-based; identifies suspects central to the network
- **PageRank** — Iterative influence propagation (α=0.85, 50 iterations)
- **Community Detection** — Label propagation with random tie-breaking

### Dataset Schema
- **Persons**: 50 suspects with name, alias, role, location, phone, organization, criminal history, status
- **FIRs**: 100 records with crime type, severity, accused IDs, location, vehicle, amount
- **CDRs**: 300 records with caller/receiver IDs, duration, call type, tower location, suspicious flag
- **Transactions**: 200 records with sender/receiver, amount, currency, channel, purpose, suspicious flag
- **Relationships**: 150 explicit links with type, strength, evidence source
- **Surveillance**: 80 reports with subjects, activity, location, risk level

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Network-wide KPIs |
| `/api/graph` | GET | Full D3.js graph data |
| `/api/filter_graph` | GET | Filtered graph by threat/location |
| `/api/suspects?n=` | GET | Top N suspects |
| `/api/persons` | GET | All persons with filters |
| `/api/person/<id>` | GET | Single suspect full profile |
| `/api/firs` | GET | FIRs with filters |
| `/api/transactions` | GET | Financial records |
| `/api/cdrs` | GET | CDR records |
| `/api/communities` | GET | Detected criminal groups |
| `/api/surveillance` | GET | Surveillance reports |
| `/api/analytics` | GET | Aggregated analytics data |
| `/api/search?q=` | GET | Global entity search |
| `/api/meta` | GET | States/districts, crime hierarchy, years, FIR statuses |
| `/api/fir/<fir_id>` | GET | One FIR with sections and possible lawful actions |
| `/api/analytics?start=&end=&state=&district=&category=` | GET | Filtered analytics |
| `/api/legal` | GET | Laws, BNSS procedure, crime catalog, portals, helplines |
| `/api/news?topic=` | GET | Latest news (new-laws, supreme-court, cyber, ndps, organised, women) |

---

## 🎯 Use Cases

1. **Law Enforcement**: Identify most dangerous suspects and their network
2. **Financial Crimes Unit**: Track hawala, cryptocurrency, and money laundering flows
3. **Intelligence Agencies**: Map organizational hierarchies within criminal networks
4. **Prosecutors**: Build evidence chains showing co-accused relationships
5. **Surveillance Teams**: Prioritize targets based on AI threat scores

---

## 📝 Notes

- The dataset is entirely synthetic and generated for demonstration purposes
- No real criminal data is used
- The system is designed to be extended with real data sources
- All algorithms are implemented from scratch using Python standard library (no external ML libraries required)

---

*Built for Smart India Hackathon 2026 | SIH Problem ID: 26189 | Ministry of Home Affairs*

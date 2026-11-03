"""
Core analysis engine for criminal network analysis.
Graph analytics, centrality measures, community detection, anomaly scoring.
"""

import json
import math
import random
from collections import defaultdict, Counter
from itertools import combinations


# ─── Simple Graph Implementation ─────────────────────────────────────────────
class Graph:
    def __init__(self):
        self.nodes = {}          # id -> attributes dict
        self.edges = []          # list of (src, dst, weight, label, attributes)
        self.adj = defaultdict(dict)  # adjacency: node -> {neighbor: weight}

    def add_node(self, node_id, **attrs):
        self.nodes[node_id] = attrs

    def add_edge(self, src, dst, weight=1.0, label="", **attrs):
        self.edges.append((src, dst, weight, label, attrs))
        # undirected
        if dst not in self.adj[src] or self.adj[src][dst] < weight:
            self.adj[src][dst] = weight
        if src not in self.adj[dst] or self.adj[dst][src] < weight:
            self.adj[dst][src] = weight

    def neighbors(self, node_id):
        return list(self.adj.get(node_id, {}).keys())

    def degree(self, node_id):
        return len(self.adj.get(node_id, {}))

    def all_nodes(self):
        return list(self.nodes.keys())


# ─── Centrality Measures ──────────────────────────────────────────────────────
def degree_centrality(graph):
    n = len(graph.nodes)
    if n <= 1:
        return {nid: 0.0 for nid in graph.nodes}
    return {nid: graph.degree(nid) / (n - 1) for nid in graph.nodes}


def betweenness_centrality(graph, normalized=True):
    """Brandes algorithm (simplified) for betweenness centrality."""
    nodes = graph.all_nodes()
    betweenness = {n: 0.0 for n in nodes}

    for s in nodes:
        # BFS
        stack = []
        pred = {n: [] for n in nodes}
        sigma = {n: 0 for n in nodes}
        sigma[s] = 1
        dist = {n: -1 for n in nodes}
        dist[s] = 0
        queue = [s]
        while queue:
            v = queue.pop(0)
            stack.append(v)
            for w in graph.neighbors(v):
                if dist[w] < 0:
                    queue.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        delta = {n: 0.0 for n in nodes}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != s:
                betweenness[w] += delta[w]

    if normalized:
        n = len(nodes)
        factor = (n - 1) * (n - 2) if n > 2 else 1
        betweenness = {k: v / factor for k, v in betweenness.items()}

    return betweenness


def closeness_centrality(graph):
    """Closeness centrality via BFS shortest paths."""
    nodes = graph.all_nodes()
    closeness = {}
    n = len(nodes)

    for s in nodes:
        dist = {n: float('inf') for n in nodes}
        dist[s] = 0
        queue = [s]
        while queue:
            v = queue.pop(0)
            for w in graph.neighbors(v):
                if dist[w] == float('inf'):
                    dist[w] = dist[v] + 1
                    queue.append(w)
        reachable = [d for d in dist.values() if d < float('inf') and d > 0]
        if reachable:
            closeness[s] = len(reachable) / sum(reachable)
        else:
            closeness[s] = 0.0

    return closeness


def pagerank(graph, damping=0.85, iterations=50):
    """Simple PageRank."""
    nodes = graph.all_nodes()
    n = len(nodes)
    if n == 0:
        return {}
    rank = {node: 1.0 / n for node in nodes}

    for _ in range(iterations):
        new_rank = {}
        for node in nodes:
            incoming = 0.0
            for other in nodes:
                if node in graph.adj.get(other, {}):
                    deg = graph.degree(other)
                    if deg > 0:
                        incoming += rank[other] / deg
            new_rank[node] = (1 - damping) / n + damping * incoming
        rank = new_rank

    return rank


# ─── Community Detection (Label Propagation) ─────────────────────────────────
def community_detection(graph, iterations=20):
    """Simple label propagation community detection."""
    rng = random.Random(7)  # deterministic groups between runs
    nodes = sorted(graph.all_nodes())
    labels = {node: i for i, node in enumerate(nodes)}

    for _ in range(iterations):
        rng.shuffle(nodes)
        changed = False
        for node in nodes:
            neighbors = graph.neighbors(node)
            if not neighbors:
                continue
            # Weighted vote: strong ties (co-accused, family, command) count more
            label_counts = Counter()
            for n in neighbors:
                label_counts[labels[n]] += graph.adj[node][n]
            new_label = label_counts.most_common(1)[0][0]
            if new_label != labels[node]:
                labels[node] = new_label
                changed = True
        if not changed:
            break

    # Group by label
    communities = defaultdict(list)
    for node, label in labels.items():
        communities[label].append(node)
    return dict(labels), list(communities.values())


# ─── Anomaly Scoring ──────────────────────────────────────────────────────────
def anomaly_features(person, firs_data, cdrs_data, transactions_data, betweenness, pagerank_scores):
    """Raw risk features for one person (normalised across persons later)."""
    pid = person["id"]
    my_firs = [f for f in firs_data if pid in f.get("accused_ids", [])]
    return {
        "criminal_history": person.get("criminal_history", 0),
        "arrest_count": person.get("arrest_count", 0),
        "fir_count": len(my_firs),
        "severe_firs": sum(1 for f in my_firs if f.get("severity") in ["High", "Critical"]),
        "heinous_firs": sum(1 for f in my_firs if f.get("crime_category") == "Heinous"),
        "suspicious_calls": sum(1 for c in cdrs_data if (c["caller_id"] == pid or c["receiver_id"] == pid) and c.get("suspicious")),
        "large_txns": sum(1 for t in transactions_data if (t["sender_id"] == pid or t["receiver_id"] == pid)
                          and t.get("amount", 0) > 1_000_000 and t.get("suspicious")),
        "betweenness": betweenness.get(pid, 0),
        "pagerank": pagerank_scores.get(pid, 0),
    }


# Weights sum to 1.0; a fugitive / absconding status adds a flat 0.15.
ANOMALY_WEIGHTS = {
    "criminal_history": 0.08, "arrest_count": 0.08, "fir_count": 0.12, "severe_firs": 0.14,
    "heinous_firs": 0.12, "suspicious_calls": 0.08, "large_txns": 0.13, "betweenness": 0.13, "pagerank": 0.12,
}


def compute_anomaly_scores(persons, firs_data, cdrs_data, transactions_data, betweenness, pagerank_scores):
    """Composite anomaly/threat score in [0, 1]: each feature is scaled by its maximum."""
    feats = {p["id"]: anomaly_features(p, firs_data, cdrs_data, transactions_data, betweenness, pagerank_scores)
             for p in persons}
    maxima = {k: max((f[k] for f in feats.values()), default=0) or 1 for k in ANOMALY_WEIGHTS}
    scores = {}
    for p in persons:
        f = feats[p["id"]]
        score = sum(w * f[k] / maxima[k] for k, w in ANOMALY_WEIGHTS.items())
        if p.get("status") == "Fugitive":
            score += 0.15
        scores[p["id"]] = min(round(score, 3), 1.0)
    return scores


# ─── Main Analysis Engine ─────────────────────────────────────────────────────
class CriminalNetworkAnalyzer:
    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        self.graph = Graph()
        self.persons = []
        self.firs = []
        self.cdrs = []
        self.transactions = []
        self.relationships = []
        self.surveillance = []
        self.metrics = {}

    def load_data(self):
        import os
        def load_json(fname):
            path = os.path.join(self.data_dir, fname)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            return []

        self.persons = load_json("persons.json")
        self.firs = load_json("firs.json")
        self.cdrs = load_json("cdrs.json")
        self.transactions = load_json("transactions.json")
        self.relationships = load_json("relationships.json")
        self.surveillance = load_json("surveillance.json")
        print(f"Loaded: {len(self.persons)} persons, {len(self.firs)} FIRs, "
              f"{len(self.cdrs)} CDRs, {len(self.transactions)} transactions, "
              f"{len(self.relationships)} relationships, {len(self.surveillance)} surveillance reports")

    def build_graph(self):
        # Add person nodes
        for p in self.persons:
            self.graph.add_node(
                p["id"],
                name=p["name"],
                alias=p.get("alias"),
                role=p.get("role"),
                location=p.get("location"),
                status=p.get("status"),
                threat_score=p.get("threat_score", 0),
                organization=p.get("organization"),
            )

        # Edges from explicit relationships
        for rel in self.relationships:
            self.graph.add_edge(
                rel["person1_id"], rel["person2_id"],
                weight=rel.get("strength", 1.0),
                label=rel["relationship_type"],
                evidence=rel.get("evidence"),
            )

        # Edges from CDRs
        cdr_pairs = defaultdict(int)
        for cdr in self.cdrs:
            pair = tuple(sorted([cdr["caller_id"], cdr["receiver_id"]]))
            cdr_pairs[pair] += 1
        for (p1, p2), count in cdr_pairs.items():
            self.graph.add_edge(p1, p2, weight=min(count / 50, 1.0), label="CDR")

        # Edges from financial transactions
        txn_pairs = defaultdict(float)
        for txn in self.transactions:
            pair = tuple(sorted([txn["sender_id"], txn["receiver_id"]]))
            txn_pairs[pair] += txn.get("amount", 0)
        for (p1, p2), amount in txn_pairs.items():
            self.graph.add_edge(p1, p2, weight=min(amount / 50_000_000, 1.0), label="Financial")

        # Edges from FIR co-accused
        for fir in self.firs:
            accused = fir.get("accused_ids", [])
            for p1, p2 in combinations(accused, 2):
                self.graph.add_edge(p1, p2, weight=0.7, label="Co-accused")

        print(f"Graph built: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")

    def compute_metrics(self):
        print("Computing centrality measures...")
        deg = degree_centrality(self.graph)
        btw = betweenness_centrality(self.graph)
        clo = closeness_centrality(self.graph)
        pgr = pagerank(self.graph)

        print("Running community detection...")
        # Cluster on strong ties only: sum all evidence between a pair and keep
        # pairs with combined strength >= 1.0, otherwise one giant group forms.
        tie = defaultdict(float)
        for src, dst, weight, _, _ in self.graph.edges:
            tie[tuple(sorted((src, dst)))] += weight
        strong = Graph()
        for nid in self.graph.nodes:
            strong.add_node(nid)
        for (src, dst), weight in tie.items():
            if weight >= 1.0:
                strong.add_edge(src, dst, weight=weight)
        labels, communities = community_detection(strong)

        self.metrics = {
            "degree": deg,
            "betweenness": btw,
            "closeness": clo,
            "pagerank": pgr,
            "community_labels": labels,
            "communities": communities,
        }

        scores = compute_anomaly_scores(self.persons, self.firs, self.cdrs, self.transactions, btw, pgr)

        # Enrich persons with metrics
        for p in self.persons:
            pid = p["id"]
            p["degree_centrality"] = round(deg.get(pid, 0), 4)
            p["betweenness_centrality"] = round(btw.get(pid, 0), 4)
            p["closeness_centrality"] = round(clo.get(pid, 0), 4)
            p["pagerank"] = round(pgr.get(pid, 0), 4)
            p["community"] = labels.get(pid, -1)
            p["computed_threat_score"] = scores[pid]
            p["fir_count"] = sum(1 for f in self.firs if pid in f.get("accused_ids", []))
            p["cdr_count"] = sum(1 for c in self.cdrs if c["caller_id"] == pid or c["receiver_id"] == pid)
            p["txn_count"] = sum(1 for t in self.transactions if t["sender_id"] == pid or t["receiver_id"] == pid)

        print("Metrics computed!")

    def get_top_suspects(self, n=10):
        return sorted(self.persons, key=lambda p: p.get("computed_threat_score", 0), reverse=True)[:n]

    def get_network_stats(self):
        all_scores = [p.get("computed_threat_score", 0) for p in self.persons]
        communities = self.metrics.get("communities", [])
        return {
            "total_persons": len(self.persons),
            "total_firs": len(self.firs),
            "total_cdrs": len(self.cdrs),
            "total_transactions": len(self.transactions),
            "total_relationships": len(self.relationships),
            "total_surveillance": len(self.surveillance),
            "graph_nodes": len(self.graph.nodes),
            "graph_edges": len(self.graph.edges),
            "num_communities": len([c for c in communities if len(c) > 1]),
            "avg_threat_score": round(sum(all_scores) / len(all_scores), 3) if all_scores else 0,
            "high_risk_count": sum(1 for s in all_scores if s > 0.6),
            "fugitives": sum(1 for p in self.persons if p.get("status") == "Fugitive"),
            "active_suspects": sum(1 for p in self.persons if p.get("status") == "Active"),
        }

    def get_graph_data(self):
        """Return graph data suitable for D3.js visualization."""
        nodes = []
        for nid, attrs in self.graph.nodes.items():
            person = next((p for p in self.persons if p["id"] == nid), {})
            nodes.append({
                "id": nid,
                "name": attrs.get("name", nid),
                "alias": attrs.get("alias"),
                "role": attrs.get("role"),
                "location": attrs.get("location"),
                "status": attrs.get("status"),
                "organization": attrs.get("organization"),
                "threat_score": person.get("computed_threat_score", 0),
                "degree": self.graph.degree(nid),
                "community": person.get("community", 0),
                "pagerank": person.get("pagerank", 0),
                "betweenness": person.get("betweenness_centrality", 0),
                "fir_count": person.get("fir_count", 0),
            })

        links = []
        seen = set()
        for src, dst, weight, label, attrs in self.graph.edges:
            key = tuple(sorted([src, dst])) + (label,)
            if key not in seen:
                seen.add(key)
                links.append({
                    "source": src,
                    "target": dst,
                    "weight": weight,
                    "label": label,
                    "evidence": attrs.get("evidence", ""),
                })

        return {"nodes": nodes, "links": links}

    def run(self):
        self.load_data()
        self.build_graph()
        self.compute_metrics()
        return self


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../data")
    analyzer = CriminalNetworkAnalyzer(".")
    analyzer.run()
    stats = analyzer.get_network_stats()
    print("\n=== NETWORK STATISTICS ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\n=== TOP 5 SUSPECTS ===")
    for p in analyzer.get_top_suspects(5):
        print(f"  {p['name']} ({p['id']}) — Threat Score: {p['computed_threat_score']} | Role: {p['role']}")

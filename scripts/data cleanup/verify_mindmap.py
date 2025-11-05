#!/usr/bin/env python3
"""
verify_mindmap.py
-----------------
Verify structure, semantic relevance, and graph health of a mindmap JSON file.

Usage:
    python verify_mindmap.py d3_graph_data.json
"""

import json
import sys
import re
import numpy as np
import pandas as pd
import networkx as nx
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
path = DATA_DIR / "d3_graph_data.json"

def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    return nodes, links


# ---------- CHECK 1: STRUCTURAL VERIFICATION ----------
def structural_checks(nodes, links):
    print("\n=== STRUCTURAL VERIFICATION ===")

    ids = [n["id"] for n in nodes]
    names = [n["name"] for n in nodes]

    # Duplicate IDs
    dup_ids = {i for i in ids if ids.count(i) > 1}
    if dup_ids:
        print(f"❌ Duplicate IDs found: {dup_ids}")
    else:
        print("✅ No duplicate IDs.")

    # Duplicate names
    dup_names = {n for n in names if names.count(n) > 1}
    if dup_names:
        print(f"⚠️ Duplicate names found: {dup_names}")
    else:
        print("✅ No duplicate names.")

    # Check for orphan nodes (missing parents based on ID pattern)
    orphans = []
    for n in nodes:
        if "." in str(n["id"]):
            parent_id = ".".join(n["id"].split(".")[:-1])
            if parent_id not in ids:
                orphans.append(n["id"])
    if orphans:
        print(f"⚠️ Orphan nodes (missing parents): {orphans[:10]}{'...' if len(orphans) > 10 else ''}")
    else:
        print("✅ No orphan nodes detected.")

    # Link source/target validity
    link_errors = []
    for l in links:
        s, t = l.get("source"), l.get("target")
        if s not in ids or t not in ids:
            link_errors.append((s, t))
    if link_errors:
        print(f"⚠️ Invalid links referencing missing nodes: {len(link_errors)} found.")
    else:
        print("✅ All links reference valid nodes.")


# ---------- CHECK 2: SEMANTIC SIMILARITY ----------
def semantic_checks(nodes, threshold=0.25):
    print("\n=== SEMANTIC SIMILARITY VERIFICATION ===")

    # Build parent-child mapping based on ID structure (e.g., 1.2.3 is child of 1.2)
    id_to_node = {n["id"]: n for n in nodes}
    pairs = []
    for node in nodes:
        if "." in str(node["id"]):
            parent_id = ".".join(node["id"].split(".")[:-1])
            if parent_id in id_to_node:
                pairs.append((parent_id, node["id"]))

    parent_texts = [id_to_node[p[0]].get("description", "") for p in pairs]
    child_texts = [id_to_node[p[1]].get("description", "") for p in pairs]

    if not pairs:
        print("No hierarchical pairs found. Skipping similarity check.")
        return

    vectorizer = TfidfVectorizer(stop_words="english")
    all_texts = parent_texts + child_texts
    tfidf = vectorizer.fit_transform(all_texts)
    parent_vecs = tfidf[:len(parent_texts)]
    child_vecs = tfidf[len(parent_texts):]

    sims = cosine_similarity(parent_vecs, child_vecs).diagonal()
    low_sim = [(pairs[i], sims[i]) for i in range(len(sims)) if sims[i] < threshold]

    print(f"Checked {len(pairs)} parent–child pairs.")
    print(f"⚠️ {len(low_sim)} pairs below similarity threshold ({threshold}).")

    if low_sim:
        df = pd.DataFrame(low_sim, columns=["Pair", "Similarity"])
        print(df.head(10).to_string(index=False))


# ---------- CHECK 4: GRAPH METRICS ----------
def graph_metrics(nodes, links):
    print("\n=== GRAPH METRICS ===")

    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"], name=n["name"])
    for l in links:
        s, t = l.get("source"), l.get("target")
        if s in G and t in G:
            G.add_edge(s, t)

    print(f"Total nodes: {G.number_of_nodes()}")
    print(f"Total links: {G.number_of_edges()}")

    # Connectivity
    undirected = G.to_undirected()
    components = list(nx.connected_components(undirected))
    print(f"Connected components: {len(components)}")
    if len(components) > 1:
        largest = max(components, key=len)
        print(f"Largest component size: {len(largest)} nodes")

    # Degree statistics
    degrees = [d for _, d in G.degree()]
    print(f"Average degree: {np.mean(degrees):.2f}")
    print(f"Max degree: {np.max(degrees)}")

    # Centrality (in-degree)
    centrality = nx.in_degree_centrality(G)
    top10 = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nTop 10 nodes by in-degree centrality:")
    for node_id, val in top10:
        name = G.nodes[node_id]["name"]
        print(f"  {node_id:<10} {name:<40} {val:.3f}")


def main():
    #if len(sys.argv) < 2:
    #    print("Usage: python verify_mindmap.py d3_graph_data.json")
    #    sys.exit(1)

    nodes, links = load_data(path)
    print(f"Loaded {len(nodes)} nodes and {len(links)} links from {path}")

    structural_checks(nodes, links)
    semantic_checks(nodes)
    graph_metrics(nodes, links)


if __name__ == "__main__":
    main()

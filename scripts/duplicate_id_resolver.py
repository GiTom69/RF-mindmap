#!/usr/bin/env python3
"""
duplicate_id_resolver.py
------------------------
Interactive tool to detect and fix duplicate node IDs in a D3 mindmap JSON file.

Usage:
    python duplicate_id_resolver.py d3_graph_data.json
"""

import json
import sys
import copy
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
path = DATA_DIR / "d3_graph_data.json"

def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def save_data(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Cleaned data saved to: {path}")

def find_duplicates(nodes):
    id_map = {}
    for node in nodes:
        id_map.setdefault(node["id"], []).append(node)
    duplicates = {k: v for k, v in id_map.items() if len(v) > 1}
    return duplicates

def short_text(s, maxlen=120):
    s = s.replace("\n", " ")
    return (s[:maxlen] + "...") if len(s) > maxlen else s

def generate_unique_numeric_id(base_id, existing_ids):
    """
    Generate a unique numeric hierarchical ID by incrementing the last number.
    Example:
      base_id='2.3.2' -> tries '2.3.3', '2.3.4', ... until unique.
    If base_id has no '.', appends '.1', '.2', etc.
    """
    base_parts = base_id.split(".")
    if re.match(r"^\d+(\.\d+)*$", base_id):
        try:
            base_parts[-1] = str(int(base_parts[-1]) + 1)
        except ValueError:
            base_parts.append("1")
    else:
        # if ID has unexpected characters, just append ".1"
        base_parts.append("1")

    new_id = ".".join(base_parts)
    while new_id in existing_ids:
        parts = new_id.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new_id = ".".join(parts)

    return new_id


def resolve_duplicates(data):
    nodes = data["nodes"]
    links = data.get("links", [])
    duplicates = find_duplicates(nodes)

    if not duplicates:
        print("✅ No duplicate IDs found.")
        return data

    print(f"\nFound {len(duplicates)} duplicate ID groups.\n")

    all_ids = {n["id"] for n in nodes}
    new_nodes = []
    processed_ids = set()

    for dup_id, group in duplicates.items():
        print("=" * 80)
        print(f"⚠️ Duplicate ID: {dup_id} ({len(group)} nodes)")
        for i, node in enumerate(group, start=1):
            print(f"\nNode {i}:")
            print(f"  Name: {node.get('name', '(none)')}")
            print(f"  Description: {short_text(node.get('description', '(no description)'))}")
            print(f"  URLs: {', '.join(node.get('urls', [])) or '(none)'}")

        # user choice
        while True:
            choice = input(
                "\nChoose action:\n"
                "  [1] Keep first only\n"
                "  [2] Keep second only\n"
                "  [3] Merge both\n"
                "  [4] Assign new ID to second node\n"
                "Select [1-4]: "
            ).strip()

            if choice in {"1", "2", "3", "4"}:
                break
            print("Invalid input. Please choose 1–4.")

        if choice == "1":
            new_nodes.append(group[0])
            processed_ids.add(dup_id)

        elif choice == "2":
            new_nodes.append(group[-1])
            processed_ids.add(dup_id)

        elif choice == "3":
            merged = copy.deepcopy(group[0])
            merged["description"] += "\n\n" + group[-1].get("description", "")
            merged["urls"] = list(set(merged.get("urls", []) + group[-1].get("urls", [])))
            new_nodes.append(merged)
            processed_ids.add(dup_id)

        elif choice == "4":
            # keep first node
            new_nodes.append(group[0])

            # generate new unique hierarchical ID
            new_id = generate_unique_numeric_id(dup_id, all_ids)
            all_ids.add(new_id)

            # assign and add new node
            new_node = copy.deepcopy(group[-1])
            new_node["id"] = new_id
            new_nodes.append(new_node)
            processed_ids.update({dup_id, new_id})

            # update links referencing old duplicated ID
            for link in links:
                if link.get("source") == dup_id:
                    # leave one link pointing to first node, duplicate one for new node
                    links.append({"source": new_id, "target": link["target"], "type": link.get("type")})
                if link.get("target") == dup_id:
                    links.append({"source": link["source"], "target": new_id, "type": link.get("type")})

            print(f"✅ Assigned new ID '{new_id}' to second node")

        print(f"✅ Resolved duplicate ID '{dup_id}'\n")

    # Add non-duplicate nodes
    all_dup_ids = set(duplicates.keys())
    for node in nodes:
        if node["id"] not in all_dup_ids:
            new_nodes.append(node)

    data["nodes"] = new_nodes
    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python duplicate_id_resolver.py d3_graph_data.json")
        sys.exit(1)

    data = load_data(path)
    data = resolve_duplicates(data)

    out_path = path.with_name(path.stem + "_clean.json")
    save_data(data, out_path)


if __name__ == "__main__":
    main()

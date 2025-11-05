#!/usr/bin/env python3
"""
remove_duplicate_links.py
-------------------------
Remove duplicate links from a D3 mindmap JSON file.

Usage:
    python remove_duplicate_links.py d3_graph_data.json
"""

import json
import sys
import copy
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
path = DATA_DIR / "d3_graph_data.json"

def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Cleaned data saved to: {path}")


def normalize_link(link):
    """Return (src, dst) tuple with sorted IDs for duplicate detection."""
    s, t = link.get("source"), link.get("target")
    # If graph is directional, remove the `sorted()` call:
    return tuple(sorted([s, t]))


def remove_duplicate_links(data):
    links = data.get("links", [])
    print(f"Loaded {len(links)} links.")

    unique = []
    seen = {}
    removed_count = 0

    for link in links:
        key = normalize_link(link)
        link_type = link.get("type", "")

        if key not in seen:
            seen[key] = [link]
        else:
            seen[key].append(link)

    for key, group in seen.items():
        if len(group) == 1:
            unique.append(group[0])
            continue

        # Multiple links with same source-target pair
        types = {g.get("type") for g in group}
        if len(types) == 1:
            # Exact duplicates -> keep only one
            unique.append(group[0])
            removed_count += len(group) - 1
        else:
            print("=" * 80)
            print(f"⚠️ Found {len(group)} duplicate links between nodes {key[0]} ↔ {key[1]}")
            for i, g in enumerate(group, 1):
                print(f"\n[{i}] Type: {g.get('type', '(none)')}")
            while True:
                choice = input(
                    "\nChoose action:\n"
                    "  [1] Keep first link\n"
                    "  [2] Keep second link\n"
                    "  [3] Delete both\n"
                    "Select [1-3]: "
                ).strip()
                if choice in {"1", "2", "3"}:
                    break
                print("Invalid input. Please choose 1–3.")

            if choice == "1":
                unique.append(group[0])
                removed_count += len(group) - 1
            elif choice == "2":
                unique.append(group[-1])
                removed_count += len(group) - 1
            elif choice == "3":
                removed_count += len(group)

    print(f"\n✅ Removed {removed_count} duplicate links.")
    data["links"] = unique
    return data


def main():
    #if len(sys.argv) < 2:
    #    print("Usage: python verify_mindmap.py d3_graph_data.json")
    #    sys.exit(1)

    data = load_data(path)
    data = remove_duplicate_links(data)

    out_path = str(path).replace(".json", "_no_dupes.json")
    save_data(data, out_path)


if __name__ == "__main__":
    main()

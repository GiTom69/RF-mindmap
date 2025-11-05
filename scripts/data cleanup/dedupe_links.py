import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_deduped.json"


def load_graph(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_graph(graph, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Cleaned graph saved to: {filepath}")


def find_duplicates(links):
    seen = {}
    duplicates = []
    for link in links:
        key = tuple(sorted([link["source"], link["target"]]))  # undirected match
        if key in seen:
            existing = seen[key]
            if existing["type"] != link["type"]:
                duplicates.append((existing, link))
        else:
            seen[key] = link
    return duplicates


def prompt_user_choice(node_map, link_a, link_b):
    """Display duplicate link info and get user decision."""
    src_name = node_map.get(link_a["source"], link_a["source"])
    dst_name = node_map.get(link_a["target"], link_a["target"])
    print("\n⚠️ Duplicate link detected:")
    print(f"Source: {src_name} ({link_a['source']})")
    print(f"Target: {dst_name} ({link_a['target']})")
    print(f"1️⃣  Type A: {link_a['type']}")
    print(f"2️⃣  Type B: {link_b['type']}")
    print("Options:")
    print("  [1] Keep A only")
    print("  [2] Keep B only")
    print("  [3] Keep both")
    print("  [4] Delete both")

    while True:
        choice = input("Enter choice [1-4]: ").strip()
        if choice in {"1", "2", "3", "4"}:
            return int(choice)
        print("Invalid input. Please choose 1, 2, 3, or 4.")


def dedupe_links(graph):
    nodes = {n["id"]: n["name"] for n in graph["nodes"]}
    links = graph["links"]

    duplicates = find_duplicates(links)
    print(f"Found {len(duplicates)} duplicate link pairs with differing types.\n")

    new_links = []
    processed_pairs = set()

    for a, b in duplicates:
        key = tuple(sorted([a["source"], a["target"]]))
        if key in processed_pairs:
            continue
        processed_pairs.add(key)

        choice = prompt_user_choice(nodes, a, b)
        if choice == 1:
            new_links.append(a)
        elif choice == 2:
            new_links.append(b)
        elif choice == 3:
            new_links.extend([a, b])
        # choice 4 => delete both

    # Add all unique links that weren’t duplicates
    duplicate_ids = {tuple(sorted([a["source"], a["target"]])) for a, b in duplicates}
    for link in links:
        key = tuple(sorted([link["source"], link["target"]]))
        if key not in duplicate_ids:
            new_links.append(link)

    graph["links"] = new_links
    return graph


def main():
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    graph = load_graph(INPUT_FILE)
    cleaned_graph = dedupe_links(graph)
    save_graph(cleaned_graph, OUTPUT_FILE)


if __name__ == "__main__":
    main()

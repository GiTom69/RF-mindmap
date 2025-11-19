#!/usr/bin/env python3
"""
verify_sources.py

Simple script to verify the source field population in the graph data.
"""

import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPH_DATA_FILE = PROJECT_ROOT / "data" / "d3_graph_data_with_syllabus.json"

def main():
    with open(GRAPH_DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = data['nodes']
    
    # Count by source
    source_counter = Counter(node.get('source', 'unknown') for node in nodes)
    
    print("="*70)
    print("Source Field Distribution")
    print("="*70)
    print(f"Total nodes: {len(nodes)}\n")
    
    for source, count in source_counter.most_common():
        print(f"{source}: {count}")
    
    print("\n" + "="*70)
    print("Sample nodes by source:")
    print("="*70)
    
    for source in ["Pasternack - RF-Opedia", "Analog Devices Wiki", "Microwaves101", "original_dataset"]:
        sample = [n for n in nodes if n.get('source') == source][:3]
        if sample:
            print(f"\n--- {source} ---")
            for node in sample:
                print(f"  • {node['name']}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Add Missing Hierarchical Links

This script identifies nodes that should have parent-child relationships
based on their ID structure and adds missing 'sub topic' links.

Usage:
    python add_missing_hierarchical_links.py
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"

def add_missing_hierarchical_links():
    """Add missing parent-child links based on ID structure."""
    print("="*70)
    print("ADDING MISSING HIERARCHICAL LINKS")
    print("="*70)
    print()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = {n['id']: n for n in data['nodes']}
    existing_links = {(l['source'], l['target'], l['type']) for l in data['links']}
    
    new_links = []
    
    # For each node with a dot in its ID, ensure it has a parent link
    for node in data['nodes']:
        node_id = str(node['id'])
        
        if '.' in node_id and not node_id.startswith('syllabus'):
            # Extract parent ID
            parts = node_id.split('.')
            parent_id = '.'.join(parts[:-1])
            
            # Check if parent exists
            if parent_id in nodes:
                # Check if link already exists
                if (parent_id, node_id, 'sub topic') not in existing_links:
                    new_links.append({
                        'source': parent_id,
                        'target': node_id,
                        'type': 'sub topic',
                        'urls': []
                    })
                    existing_links.add((parent_id, node_id, 'sub topic'))
                    print(f"Added: {parent_id} → {node_id}")
    
    print()
    print(f"Added {len(new_links)} missing hierarchical links")
    
    # Add new links to data
    data['links'].extend(new_links)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved to: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    add_missing_hierarchical_links()

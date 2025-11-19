#!/usr/bin/env python3
"""
Assign Semantic Parents to Orphaned Nodes

This script finds nodes without parent links and assigns them to the most
semantically similar node at a higher hierarchical level.

Usage:
    python assign_semantic_parents.py
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"

def get_node_depth(node_id):
    """Calculate hierarchical depth of a node based on ID structure."""
    node_str = str(node_id)
    if node_str.startswith('syllabus'):
        parts = node_str.replace('syllabus-', '').split('.')
        return len(parts)
    elif '.' in node_str:
        return len(node_str.split('.'))
    else:
        return 0  # Root level

def assign_semantic_parents():
    """Assign semantic parents to orphaned nodes."""
    print("="*70)
    print("ASSIGNING SEMANTIC PARENTS TO ORPHANED NODES")
    print("="*70)
    print()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Find orphaned nodes (no incoming 'sub topic' links)
    incoming_links = {l['target'] for l in data['links'] if l['type'] == 'sub topic'}
    orphaned = [n for n in data['nodes'] if n['id'] not in incoming_links]
    
    # Filter out root-level nodes (they shouldn't have parents)
    orphaned = [n for n in orphaned if get_node_depth(n['id']) > 0]
    
    print(f"Found {len(orphaned)} orphaned nodes needing parents")
    
    if not orphaned:
        print("\n✓ No orphaned nodes found - all nodes have parents!")
        print("="*70)
        return
    
    # Load model
    print("\nLoading sentence transformer model...")
    model = SentenceTransformer('all-mpnet-base-v2')
    
    # Compute embeddings for all nodes
    print("Computing embeddings for all nodes...")
    texts = [f"{n['name']}. {n.get('description', '')}" for n in data['nodes']]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    
    # Normalize embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / norms
    
    # Build node index
    node_to_idx = {n['id']: i for i, n in enumerate(data['nodes'])}
    
    new_links = []
    assignments = []
    
    print("\nFinding semantic parents...")
    for orphan in orphaned:
        orphan_idx = node_to_idx[orphan['id']]
        orphan_embedding = normalized[orphan_idx]
        orphan_depth = get_node_depth(orphan['id'])
        
        # Compute similarities to all nodes
        similarities = np.dot(normalized, orphan_embedding)
        
        # Sort by similarity
        sorted_indices = np.argsort(similarities)[::-1]
        
        # Find best parent
        best_parent = None
        best_parent_idx = None
        best_similarity = 0
        
        for idx in sorted_indices[1:]:  # Skip self
            candidate = data['nodes'][idx]
            candidate_depth = get_node_depth(candidate['id'])
            
            # Parent must be at a shallower depth
            if candidate_depth >= orphan_depth:
                continue
            
            # Require minimum similarity
            if similarities[idx] < 0.25:
                break
            
            # Check if not already linked
            if (candidate['id'], orphan['id'], 'sub topic') in \
               {(l['source'], l['target'], l['type']) for l in data['links']}:
                continue
            
            best_parent = candidate['id']
            best_parent_idx = idx
            best_similarity = similarities[idx]
            break
        
        if best_parent:
            new_links.append({
                'source': best_parent,
                'target': orphan['id'],
                'type': 'sub topic',
                'similarity_score': float(best_similarity),
                'urls': []
            })
            
            parent_name = data['nodes'][best_parent_idx]['name']
            orphan_name = orphan['name']
            
            assignments.append((orphan_name, parent_name, best_similarity))
            
            if len(assignments) <= 20:  # Show first 20
                print(f"  '{orphan_name[:40]}' → '{parent_name[:40]}' (sim: {best_similarity:.3f})")
    
    if len(assignments) > 20:
        print(f"  ... and {len(assignments) - 20} more")
    
    print()
    print(f"Created {len(new_links)} semantic parent links")
    
    # Show statistics
    if new_links:
        similarities = [a[2] for a in assignments]
        print(f"\nSimilarity statistics:")
        print(f"  Min: {min(similarities):.3f}")
        print(f"  Max: {max(similarities):.3f}")
        print(f"  Mean: {np.mean(similarities):.3f}")
        print(f"  Median: {np.median(similarities):.3f}")
    
    # Add new links to data
    data['links'].extend(new_links)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved to: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    assign_semantic_parents()

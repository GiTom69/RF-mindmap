#!/usr/bin/env python3
"""
Connect Disconnected Components in RF Knowledge Graph

This script identifies disconnected components and connects them to the main
graph by finding the most semantically similar nodes in the largest component.

Usage:
    python connect_disconnected_components.py
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from collections import defaultdict, deque

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"

def find_connected_components(nodes, links):
    """Find all connected components using BFS."""
    node_ids = {n['id'] for n in nodes}
    
    # Build adjacency list (undirected)
    adj = defaultdict(set)
    for link in links:
        src, tgt = link['source'], link['target']
        if src in node_ids and tgt in node_ids:
            adj[src].add(tgt)
            adj[tgt].add(src)
    
    visited = set()
    components = []
    
    for node in nodes:
        node_id = node['id']
        if node_id not in visited:
            # BFS to find component
            component = []
            queue = deque([node_id])
            visited.add(node_id)
            
            while queue:
                current = queue.popleft()
                component.append(current)
                
                for neighbor in adj[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            
            components.append(component)
    
    # Sort by size (largest first)
    components.sort(key=len, reverse=True)
    return components

def connect_components():
    """Connect disconnected components to the main graph."""
    print("="*70)
    print("CONNECTING DISCONNECTED COMPONENTS")
    print("="*70)
    print()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = data['nodes']
    links = data['links']
    
    print(f"Total nodes: {len(nodes)}")
    print(f"Total links: {len(links)}")
    
    # Find connected components
    print("\nFinding connected components...")
    components = find_connected_components(nodes, links)
    
    print(f"Found {len(components)} connected components")
    print(f"Largest component: {len(components[0])} nodes")
    
    if len(components) <= 3:
        print("\n✓ Graph is well-connected (≤3 components). Nothing to do!")
        return
    
    # Show component size distribution
    print("\nComponent size distribution:")
    size_dist = defaultdict(int)
    for comp in components:
        size_dist[len(comp)] += 1
    
    for size in sorted(size_dist.keys(), reverse=True)[:10]:
        count = size_dist[size]
        print(f"  Size {size:3d}: {count:3d} component(s)")
    
    # Identify nodes in main component and small components
    id_to_node = {n['id']: n for n in nodes}
    
    main_component_ids = set(components[0])
    main_component_nodes = [id_to_node[nid] for nid in main_component_ids]
    
    small_components = components[1:]  # Everything except largest
    small_component_nodes = []
    
    for comp in small_components:
        for node_id in comp:
            small_component_nodes.append(id_to_node[node_id])
    
    print(f"\nMain component: {len(main_component_nodes)} nodes")
    print(f"Small components: {len(small_component_nodes)} nodes in {len(small_components)} components")
    
    # Load model
    print("\nLoading sentence transformer model...")
    model = SentenceTransformer('all-mpnet-base-v2')
    
    # Compute embeddings
    print("Computing embeddings...")
    
    main_texts = [f"{n['name']}. {n.get('description', '')}" for n in main_component_nodes]
    small_texts = [f"{n['name']}. {n.get('description', '')}" for n in small_component_nodes]
    
    print("  - Main component nodes...")
    main_embeddings = model.encode(main_texts, show_progress_bar=True, batch_size=32)
    
    print("  - Small component nodes...")
    small_embeddings = model.encode(small_texts, show_progress_bar=True, batch_size=32)
    
    # Normalize embeddings
    main_norms = np.linalg.norm(main_embeddings, axis=1, keepdims=True)
    small_norms = np.linalg.norm(small_embeddings, axis=1, keepdims=True)
    
    main_normalized = main_embeddings / main_norms
    small_normalized = small_embeddings / small_norms
    
    # Compute similarity matrix (small vs main)
    print("\nComputing similarity matrix...")
    similarity_matrix = np.dot(small_normalized, main_normalized.T)
    
    # For each small component, connect its most representative node to main component
    print("\nConnecting components...")
    new_links = []
    connections = []
    
    MIN_SIMILARITY = 0.25  # Minimum threshold for creating a link
    
    for i, comp in enumerate(small_components):
        # Find nodes from this component in small_component_nodes
        comp_node_indices = [j for j, n in enumerate(small_component_nodes) 
                            if n['id'] in comp]
        
        if not comp_node_indices:
            continue
        
        # For each node in this component, find best match in main component
        best_similarity = -1
        best_small_idx = None
        best_main_idx = None
        
        for small_idx in comp_node_indices:
            similarities = similarity_matrix[small_idx]
            max_sim_idx = np.argmax(similarities)
            max_sim = similarities[max_sim_idx]
            
            if max_sim > best_similarity:
                best_similarity = max_sim
                best_small_idx = small_idx
                best_main_idx = max_sim_idx
        
        # Create link if similarity is above threshold
        if best_similarity >= MIN_SIMILARITY:
            small_node = small_component_nodes[best_small_idx]
            main_node = main_component_nodes[best_main_idx]
            
            new_links.append({
                'source': small_node['id'],
                'target': main_node['id'],
                'type': 'semantically_similar',
                'similarity_score': float(best_similarity),
                'urls': []
            })
            
            connections.append((
                len(comp),
                small_node['name'],
                main_node['name'],
                best_similarity
            ))
            
            print(f"  [{i+1:3d}] Size {len(comp):2d}: '{small_node['name'][:35]}' → '{main_node['name'][:35]}' ({best_similarity:.3f})")
        else:
            print(f"  [{i+1:3d}] Size {len(comp):2d}: No good match found (best: {best_similarity:.3f})")
    
    print(f"\nCreated {len(new_links)} component bridge links")
    
    if connections:
        similarities = [c[3] for c in connections]
        print(f"\nSimilarity statistics:")
        print(f"  Min: {min(similarities):.3f}")
        print(f"  Max: {max(similarities):.3f}")
        print(f"  Mean: {np.mean(similarities):.3f}")
        print(f"  Median: {np.median(similarities):.3f}")
        
        # Show size distribution of connected components
        sizes = [c[0] for c in connections]
        print(f"\nConnected component sizes:")
        print(f"  Min: {min(sizes)}")
        print(f"  Max: {max(sizes)}")
        print(f"  Mean: {np.mean(sizes):.1f}")
    
    # Add new links to data
    data['links'].extend(new_links)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved to: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    connect_components()

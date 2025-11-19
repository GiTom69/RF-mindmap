#!/usr/bin/env python3
"""
Integrate Syllabus Topics with Main RF Knowledge Graph

This script maps syllabus concepts to existing RF topics by finding the most
semantically similar nodes and creating proper parent-child relationships.

Approach B: Re-integrate Syllabus as Top-Level Topics
- Maps each syllabus topic to the most similar existing RF concept
- Creates hierarchical links between syllabus and main graph
- Preserves syllabus structure while connecting it to the knowledge base

Usage:
    python integrate_syllabus_topics.py
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"

def integrate_syllabus():
    """Integrate syllabus topics with main knowledge graph."""
    print("="*70)
    print("INTEGRATING SYLLABUS TOPICS WITH MAIN GRAPH")
    print("="*70)
    print()
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Separate syllabus nodes from main graph nodes
    syllabus_nodes = [n for n in data['nodes'] if str(n['id']).startswith('syllabus')]
    main_nodes = [n for n in data['nodes'] if not str(n['id']).startswith('syllabus')]
    
    print(f"Found {len(syllabus_nodes)} syllabus nodes")
    print(f"Found {len(main_nodes)} main graph nodes")
    
    if not syllabus_nodes:
        print("\n✓ No syllabus nodes found - nothing to integrate!")
        return
    
    # Load model
    print("\nLoading sentence transformer model...")
    model = SentenceTransformer('all-mpnet-base-v2')
    
    # Compute embeddings
    print("Computing embeddings...")
    
    syllabus_texts = [f"{n['name']}. {n.get('description', '')}" for n in syllabus_nodes]
    main_texts = [f"{n['name']}. {n.get('description', '')}" for n in main_nodes]
    
    print("  - Syllabus nodes...")
    syllabus_embeddings = model.encode(syllabus_texts, show_progress_bar=True, batch_size=32)
    
    print("  - Main graph nodes...")
    main_embeddings = model.encode(main_texts, show_progress_bar=True, batch_size=32)
    
    # Normalize embeddings
    syllabus_norms = np.linalg.norm(syllabus_embeddings, axis=1, keepdims=True)
    main_norms = np.linalg.norm(main_embeddings, axis=1, keepdims=True)
    
    syllabus_normalized = syllabus_embeddings / syllabus_norms
    main_normalized = main_embeddings / main_norms
    
    # Compute similarity matrix (syllabus vs main)
    print("\nComputing similarity matrix...")
    similarity_matrix = np.dot(syllabus_normalized, main_normalized.T)
    
    # Find best matches and create bridge links
    print("\nFinding best semantic matches...")
    new_links = []
    mappings = []
    
    # Only map top-level syllabus nodes (depth 1) to avoid over-connection
    top_level_syllabus = [n for n in syllabus_nodes 
                          if str(n['id']).count('.') == 0 or 
                          str(n['id']).count('-') == 1 and '.' not in str(n['id'])]
    
    for syllabus_node in top_level_syllabus:
        syllabus_idx = syllabus_nodes.index(syllabus_node)
        
        # Get top 3 most similar main nodes
        similarities = similarity_matrix[syllabus_idx]
        top_indices = np.argsort(similarities)[::-1][:3]
        
        best_match_idx = top_indices[0]
        best_similarity = similarities[best_match_idx]
        
        # Only create link if similarity is reasonable
        if best_similarity >= 0.3:
            main_node = main_nodes[best_match_idx]
            
            # Create bidirectional relationship
            # Syllabus extends/relates to main concept
            new_links.append({
                'source': syllabus_node['id'],
                'target': main_node['id'],
                'type': 'extends',
                'similarity_score': float(best_similarity),
                'urls': []
            })
            
            mappings.append((
                syllabus_node['name'],
                main_node['name'],
                best_similarity
            ))
            
            print(f"  '{syllabus_node['name'][:45]}' ↔ '{main_node['name'][:45]}' ({best_similarity:.3f})")
    
    print()
    print(f"Created {len(new_links)} syllabus-to-main bridge links")
    
    if mappings:
        similarities = [m[2] for m in mappings]
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
    integrate_syllabus()

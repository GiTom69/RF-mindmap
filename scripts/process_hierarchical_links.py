#!/usr/bin/env python3
"""
Process Hierarchical Links

This script filters and prioritizes links in the knowledge graph to create
a more hierarchical, tree-like structure while preserving semantic connections.

Features:
1. Filters semantic links that duplicate hierarchical relationships
2. Limits semantic links per node to prevent over-connection
3. Prioritizes cross-cluster semantic links over within-cluster links
4. Generates a cleaner, more readable graph structure

Usage:
    python process_hierarchical_links.py
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Configure paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data_with_semantic_links.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_hierarchical.json"


def are_hierarchically_related(id1: str, id2: str) -> bool:
    """
    Check if two nodes are in a hierarchical relationship.
    
    Args:
        id1: First node ID
        id2: Second node ID
        
    Returns:
        True if nodes are parent-child or siblings
    """
    parts1 = str(id1).split('.')
    parts2 = str(id2).split('.')
    
    # One is parent of the other
    if parts1 == parts2[:len(parts1)] or parts2 == parts1[:len(parts2)]:
        return True
    
    # Share common parent (siblings)
    if len(parts1) > 1 and len(parts2) > 1:
        return parts1[:-1] == parts2[:-1]
    
    return False


def get_cluster_id(node_id: str, high_level_topics: List[Dict]) -> str:
    """
    Get the cluster/topic ID for a given node.
    
    Args:
        node_id: Node ID to look up
        high_level_topics: List of high-level topic structures
        
    Returns:
        Cluster ID or node's own ID if not in a cluster
    """
    for topic in high_level_topics:
        if node_id in topic.get('sub_topics', []) or node_id == topic['id']:
            return topic['id']
    return str(node_id)


def filter_semantic_links(graph_data: Dict, max_semantic_per_node: int = 3,
                          prioritize_cross_cluster: bool = True) -> Dict:
    """
    Filter semantic links to create hierarchical structure.
    
    Args:
        graph_data: Graph data dictionary
        max_semantic_per_node: Maximum semantic links per node
        prioritize_cross_cluster: Prefer links between different clusters
        
    Returns:
        Filtered graph data
    """
    print("="*70)
    print("PROCESSING HIERARCHICAL LINK STRUCTURE")
    print("="*70)
    
    nodes = {n['id']: n for n in graph_data['nodes']}
    links = graph_data['links']
    high_level_topics = graph_data.get('high_level_topics', [])
    
    # Separate link types
    hierarchical_links = []
    semantic_links = []
    logical_links = []
    
    for link in links:
        link_type = link.get('type', 'other')
        if link_type == 'sub topic':
            hierarchical_links.append(link)
        elif link_type == 'semantically_similar':
            semantic_links.append(link)
        else:
            logical_links.append(link)
    
    print(f"\nOriginal link counts:")
    print(f"  Hierarchical: {len(hierarchical_links)}")
    print(f"  Logical: {len(logical_links)}")
    print(f"  Semantic: {len(semantic_links)}")
    
    # Filter semantic links
    filtered_semantic = []
    semantic_count = defaultdict(int)
    
    # Sort semantic links by similarity score (highest first)
    semantic_links_sorted = sorted(
        semantic_links,
        key=lambda x: x.get('similarity_score', 0),
        reverse=True
    )
    
    # If prioritizing cross-cluster, sort by cluster difference first
    if prioritize_cross_cluster and high_level_topics:
        def get_sort_key(link):
            source_cluster = get_cluster_id(link['source'], high_level_topics)
            target_cluster = get_cluster_id(link['target'], high_level_topics)
            is_cross_cluster = source_cluster != target_cluster
            similarity = link.get('similarity_score', 0)
            # Prioritize: cross-cluster first, then by similarity
            return (is_cross_cluster, similarity)
        
        semantic_links_sorted = sorted(semantic_links_sorted, key=get_sort_key, reverse=True)
    
    for link in semantic_links_sorted:
        source_id = link['source']
        target_id = link['target']
        
        # Skip if hierarchically related (redundant)
        if are_hierarchically_related(source_id, target_id):
            continue
        
        # Check node limits
        if semantic_count[source_id] >= max_semantic_per_node:
            continue
        if semantic_count[target_id] >= max_semantic_per_node:
            continue
        
        # Add link
        filtered_semantic.append(link)
        semantic_count[source_id] += 1
        semantic_count[target_id] += 1
    
    print(f"\nFiltered link counts:")
    print(f"  Hierarchical: {len(hierarchical_links)} (unchanged)")
    print(f"  Logical: {len(logical_links)} (unchanged)")
    print(f"  Semantic: {len(filtered_semantic)} (reduced from {len(semantic_links)})")
    
    removed_count = len(semantic_links) - len(filtered_semantic)
    if removed_count > 0:
        print(f"\nRemoved {removed_count} semantic links:")
        print(f"  - Hierarchically redundant or over-connected nodes")
    
    # Analyze cross-cluster vs within-cluster
    if high_level_topics:
        cross_cluster = 0
        within_cluster = 0
        for link in filtered_semantic:
            source_cluster = get_cluster_id(link['source'], high_level_topics)
            target_cluster = get_cluster_id(link['target'], high_level_topics)
            if source_cluster != target_cluster:
                cross_cluster += 1
            else:
                within_cluster += 1
        
        if cross_cluster + within_cluster > 0:
            cross_pct = 100 * cross_cluster / (cross_cluster + within_cluster)
            print(f"\nSemantic link distribution:")
            print(f"  Cross-cluster: {cross_cluster} ({cross_pct:.1f}%)")
            print(f"  Within-cluster: {within_cluster} ({100-cross_pct:.1f}%)")
    
    # Rebuild links
    graph_data['links'] = hierarchical_links + logical_links + filtered_semantic
    
    return graph_data


def generate_statistics(graph_data: Dict):
    """Generate and print graph statistics."""
    nodes = graph_data['nodes']
    links = graph_data['links']
    
    print("\n" + "="*70)
    print("GRAPH STATISTICS")
    print("="*70)
    
    print(f"\nNodes: {len(nodes)}")
    
    # Link type distribution
    link_types = defaultdict(int)
    for link in links:
        link_types[link.get('type', 'other')] += 1
    
    print("\nLinks by type:")
    for link_type, count in sorted(link_types.items()):
        print(f"  {link_type}: {count}")
    
    print(f"\nTotal links: {len(links)}")
    print(f"Average links per node: {len(links) / len(nodes):.2f}")
    
    # Node degree distribution
    node_degrees = defaultdict(int)
    for link in links:
        node_degrees[link['source']] += 1
        node_degrees[link['target']] += 1
    
    if node_degrees:
        degrees = list(node_degrees.values())
        print(f"\nNode degree statistics:")
        print(f"  Min: {min(degrees)}")
        print(f"  Max: {max(degrees)}")
        print(f"  Mean: {sum(degrees) / len(degrees):.2f}")
        
        # Degree distribution
        degree_bins = [(0, 2), (3, 5), (6, 10), (11, 20), (21, 100)]
        print(f"\nDegree distribution:")
        for low, high in degree_bins:
            count = sum(1 for d in degrees if low <= d <= high)
            if count > 0:
                pct = 100 * count / len(degrees)
                print(f"  {low}-{high}: {count} nodes ({pct:.1f}%)")


def main():
    print("Processing hierarchical link structure...")
    print(f"Input: {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print()
    
    # Check input file
    if not INPUT_FILE.exists():
        print(f"Error: Input file not found: {INPUT_FILE}")
        print("Please run the semantic linker script first.")
        return
    
    # Load data
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    
    # Process links
    graph_data = filter_semantic_links(
        graph_data,
        max_semantic_per_node=3,
        prioritize_cross_cluster=True
    )
    
    # Generate statistics
    generate_statistics(graph_data)
    
    # Save output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print(f"✓ Saved hierarchical graph to: {OUTPUT_FILE}")
    print("="*70)


if __name__ == "__main__":
    main()

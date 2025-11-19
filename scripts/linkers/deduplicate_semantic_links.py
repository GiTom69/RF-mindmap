"""
Remove Duplicate Bidirectional Semantic Links

This script removes redundant semantic links where both A->B and B->A exist,
keeping only one link per node pair and marking it as bidirectional.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure paths
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "d3_graph_data_with_semantic_links.json"
OUTPUT_FILE = DATA_DIR / "d3_graph_data_with_semantic_links.json"


def deduplicate_semantic_links(data: Dict) -> Dict:
    """
    Remove duplicate bidirectional semantic links.
    
    For each pair of nodes with semantic links in both directions,
    keep only one link and mark it as bidirectional.
    
    Args:
        data: Graph data dictionary
        
    Returns:
        Updated graph data with deduplicated links
    """
    print("="*60)
    print("DEDUPLICATING SEMANTIC LINKS")
    print("="*60)
    
    links = data['links']
    original_count = len(links)
    
    # Track semantic links by node pairs (using sorted tuple as key)
    semantic_pairs: Dict[Tuple[str, str], Dict] = {}
    non_semantic_links = []
    duplicate_count = 0
    
    for link in links:
        if link.get('type') == 'semantically_similar':
            source = link['source']
            target = link['target']
            
            # Create normalized key (sorted to catch both directions)
            pair_key = tuple(sorted([source, target]))
            
            if pair_key in semantic_pairs:
                # Duplicate found - keep the existing one
                duplicate_count += 1
                print(f"Found duplicate: {source} <-> {target}")
            else:
                # First time seeing this pair - store it
                # Ensure the link has the is_bidirectional flag
                link['is_bidirectional'] = True
                semantic_pairs[pair_key] = link
        else:
            # Keep all non-semantic links as-is
            non_semantic_links.append(link)
    
    # Reconstruct links list
    deduplicated_links = non_semantic_links + list(semantic_pairs.values())
    data['links'] = deduplicated_links
    
    # Statistics
    semantic_count = len(semantic_pairs)
    print(f"\n{'='*60}")
    print("RESULTS")
    print("="*60)
    print(f"Original total links: {original_count:,}")
    print(f"Duplicate semantic links removed: {duplicate_count:,}")
    print(f"Unique semantic link pairs: {semantic_count:,}")
    print(f"Non-semantic links: {len(non_semantic_links):,}")
    print(f"Final total links: {len(deduplicated_links):,}")
    print(f"Links saved: {original_count - len(deduplicated_links):,}")
    
    return data


def main():
    """Main execution function."""
    print(f"Loading data from: {INPUT_FILE}")
    
    if not INPUT_FILE.exists():
        print(f"Error: Input file not found: {INPUT_FILE}")
        return
    
    # Load data
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data['nodes'])} nodes and {len(data['links'])} links")
    
    # Deduplicate
    data = deduplicate_semantic_links(data)
    
    # Save
    save = input(f"\nSave deduplicated data to {OUTPUT_FILE}? (y/n): ").lower()
    if save == 'y':
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved to: {OUTPUT_FILE}")
    else:
        print("\nData not saved.")


if __name__ == "__main__":
    main()

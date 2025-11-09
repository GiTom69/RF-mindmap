import json
import os
from pathlib import Path

# --- Configuration ---
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "nodes_with_new_sequential_ids.json"
OUTPUT_NEW_IDS_FILE = DATA_DIR / "nodes_with_new_sequential_ids.json"

# --- Helper Functions ---

def load_data(file_path):
    """Loads the JSON data using UTF-8 encoding."""
    try:
        # Use UTF-8 for reliable character decoding (fixes the prior UnicodeDecodeError)
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{file_path}' not found.")
        return None
    except UnicodeDecodeError as e:
        print(f"Error: Failed to decode file using UTF-8. Details: {e}")
        return None


def reassign_sequential_ids(data):
    """
    Replaces all existing, mixed-format IDs with a simple, unique, sequential integer ID.
    It also creates a map for old ID (string) to the new ID (integer).
    """
    original_nodes = data.get("nodes", [])
    original_links = data.get("links", [])
    
    # 1. CREATE NEW ID SYSTEM FOR NODES
    print(f"Total original nodes: {len(original_nodes)}")
    
    # Create a map to track old ID (the unreliable one) to the new sequential ID
    old_to_new_id_map = {}
    new_nodes = []
    
    for index, node in enumerate(original_nodes):
        # The new ID will be a sequential integer, converted to a string for JSON consistency
        new_id = str(index)
        
        # Store the mapping
        # Note: If duplicate old IDs exist, this map will only store the last occurrence.
        # This is a key reason why the name-deduplication script is needed, but for now, we map the instance.
        old_id_key = str(node.get("id")) # Ensure key is always a string
        old_to_new_id_map[old_id_key] = new_id
        
        # Create a clean new node dictionary
        new_node = {
            "id": new_id, # Use the new sequential ID
            "name": node.get("name", "Unnamed Node"),
            "description": node.get("description", ""),
            "urls": node.get("urls", [])
            # You might want to keep the old 'id' for debugging, e.g.:
            # "original_id": old_id_key 
        }
        new_nodes.append(new_node)
        
    print(f"Assigned {len(new_nodes)} new sequential IDs (0 to {len(new_nodes) - 1}).")
    
    # 2. UPDATE LINKS WITH NEW IDs
    new_links = []
    unmapped_links_count = 0

    print(f"Total original links: {len(original_links)}")
    
    for link in original_links:
        source_id = str(link.get("source"))
        target_id = str(link.get("target"))
        
        new_source_id = old_to_new_id_map.get(source_id)
        new_target_id = old_to_new_id_map.get(target_id)
        
        if new_source_id and new_target_id:
            # Only keep the link if BOTH old IDs mapped to a new, valid node ID
            new_links.append({
                "source": new_source_id,
                "target": new_target_id,
                "type": link.get("type", "related to"),
                "urls": link.get("urls", [])
            })
        else:
            # If a link points to an old ID that was duplicated or missing, it is dropped
            unmapped_links_count += 1
            # You might want to log these dropped links for manual inspection
            
    print(f"Links successfully re-mapped: {len(new_links)}")
    print(f"Links dropped (due to unmapped/duplicate old IDs): {unmapped_links_count}")

    return new_nodes, new_links

# --- Main Execution ---
if __name__ == "__main__":
    
    data = load_data(INPUT_FILE)
    if data is None:
        exit()
        
    # PHASE 1: REASSIGN IDs
    cleaned_nodes, remapped_links = reassign_sequential_ids(data)

    # PHASE 2: OUTPUT
    final_data = {
        "nodes": cleaned_nodes,
        "links": remapped_links
    }
    
    with open(OUTPUT_NEW_IDS_FILE, 'w', encoding='utf-8') as f:
        # ensure_ascii=False for clean handling of special characters
        json.dump(final_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- SUCCESS ---")
    print(f"Data with new sequential IDs saved to: {OUTPUT_NEW_IDS_FILE}")
    print("Next Step: Run the name deduplication/merging script on this new file.")
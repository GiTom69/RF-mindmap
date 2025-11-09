import json
import uuid
import numpy as np
from pathlib import Path
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- Configuration ---
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INPUT_FILE = DATA_DIR / "nodes_with_new_sequential_ids.json"
OUTPUT_CLEANED_FILE = DATA_DIR / "cleaned_nodes_ready_for_linking_.json"
SIMILARITY_THRESHOLD = 0.8  # Threshold to decide if two descriptions are the "same concept"

MIN_LENGTH_RATIO_TO_KEEP = 0.5
non_canonical_desc_len_max = 50
# --- Helper Functions ---


def load_data(file_path):
    """Loads the JSON data from the file, explicitly using UTF-8 encoding."""
    try:
        # FIX: Explicitly specify encoding='utf-8' for reliable file reading
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{file_path}' not found.")
        return None
    except UnicodeDecodeError as e:
        print(f"Error: Failed to decode file using UTF-8. The file might be corrupted or in a non-standard encoding.")
        print(f"Details: {e}")
        return None

def score_node(node):
    """
    Scores a node based on the completeness of its metadata.
    A higher score means it is a better candidate for the Canonical Node.
    """
    score = 0
    # Prioritize description length
    score += len(node.get("description", ""))
    # Give high weight to existing URLs
    score += len(node.get("urls", [])) * 10
    # Simple check for existing links (even if we ignore them, the node might be more 'real')
    # Note: This requires pre-calculating incoming/outgoing links, but for simplicity, we rely on the node's own metadata.
    
    return score

def check_group_similarity(nodes_group):
    """
    Calculates the pairwise semantic similarity of descriptions within a group.
    Uses TF-IDF for simplicity, but should be replaced by your existing Sentence-BERT/SciBERT script.
    """
    descriptions = [node.get("description", "").strip() or "NO_DESCRIPTION" for node in nodes_group]
    
    # Simple check: if all descriptions are empty/placeholder, they are "similar"
    if all(d == "NO_DESCRIPTION" for d in descriptions):
        return 1.0
    
    # Use your custom semantic script here for better results
    # --- PLACEHOLDER FOR ADVANCED SEMANTIC SIMILARITY ---
    
    # Fallback to TF-IDF for a working example
    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform(descriptions)
        # Calculate all-pairs similarity within the group
        sim_matrix = cosine_similarity(tfidf_matrix)
        
        # We need the minimum similarity to ensure ALL pairs are similar enough to merge
        # Exclude self-similarity (the diagonal of 1s)
        # Flatten and take the minimum non-self-similarity value
        np.fill_diagonal(sim_matrix, 2.0) # Set diagonal to > 1.0 for min() to ignore
        min_sim = sim_matrix.min()
        
        return min_sim
    except ValueError:
        # Happens if there's only one node after filtering, or if tokenization fails
        return 1.0


def process_duplicates(data):
    """
    Core function to assign new IDs and resolve duplicate names (merge or rename/discard).
    """
    original_nodes = data.get("nodes", [])
    
    # 1. GENERATE NEW UNIQUE IDs and Group by Name
    name_groups = defaultdict(list)
    
    for node in original_nodes:
        node['new_id'] = str(uuid.uuid4())
        name_groups[node['name']].append(node)
        
    new_nodes_list = []
    
    merged_count = 0
    renamed_count = 0
    discarded_count = 0
    
    print(f"\n--- Starting Duplicate Resolution on {len(name_groups)} Unique Names ---")

    # 2. RESOLVE DUPLICATE NAMES
    for name, group in name_groups.items():
        if len(group) == 1:
            new_nodes_list.append(group[0])
            continue

        print(f"\nProcessing duplicate group: '{name}' ({len(group)} instances)")
        
        # Sort by score to find the best candidate for Canonical Node
        group.sort(key=score_node, reverse=True)
        canonical_node = group[0]
        canonical_desc_len = len(canonical_node.get("description", "")) # Get length for comparison
        
        min_sim = check_group_similarity(group)
        
        if min_sim >= SIMILARITY_THRESHOLD:
            # --- MERGE SCENARIO (Same Concept) ---
            
            # (Aggregation logic remains the same as before)
            all_urls = set(canonical_node.get("urls", []))
            all_descriptions = canonical_node.get("description", "")
            
            for i, non_canonical_node in enumerate(group[1:]):
                all_urls.update(non_canonical_node.get("urls", []))
                
                desc = non_canonical_node.get("description", "")
                if desc and desc.strip() != all_descriptions.strip():
                    all_descriptions += f"\n\n--- MERGED DESCRIPTION FROM DUPLICATE (Index {i+1}) ---\n" + desc

            canonical_node["description"] = all_descriptions
            canonical_node["urls"] = list(all_urls)
            
            new_nodes_list.append(canonical_node)
            merged_count += len(group) - 1
            print(f"  -> Decision: MERGED. {len(group)-1} nodes consolidated into the best candidate.")
            
        else:
            # --- DISAMBIGUATE/RENAME OR DISCARD SCENARIO (Different Concepts) ---
            print(f"  -> Decision: RENAME/DISCARD. Low similarity ({min_sim:.2f}) suggests different concepts.")
            
            # Keep the Canonical Node (best score, longest description)
            new_nodes_list.append(canonical_node)
            
            # Process the remaining non-canonical nodes
            for i, non_canonical_node in enumerate(group[1:]):
                original_name = non_canonical_node['name']
                non_canonical_desc_len = len(non_canonical_node.get("description", ""))
                
                # NEW LOGIC: Check description length against the canonical node
                if non_canonical_desc_len < (canonical_desc_len * MIN_LENGTH_RATIO_TO_KEEP) and non_canonical_desc_len < non_canonical_desc_len_max:
                    # If significantly shorter AND very short (e.g., less than 10 chars), discard it.
                    discarded_count += 1
                    print(f"     Discarded: '{original_name}' (Description too short: {non_canonical_desc_len} chars vs canonical {canonical_desc_len} chars).")
                else:
                    # Otherwise, rename to keep it, as it's a distinct concept with sufficient information
                    non_canonical_node['name'] = f"{original_name} (Concept {i+1} - ID {non_canonical_node['id']})"
                    new_nodes_list.append(non_canonical_node)
                    renamed_count += 1
                    print(f"     Renamed: '{original_name}' -> '{non_canonical_node['name']}' (Kept: {non_canonical_desc_len} chars).")

    print(f"\n--- Resolution Complete ---")
    print(f"Total Nodes: {len(original_nodes)}")
    print(f"Nodes Merged: {merged_count}")
    print(f"Nodes Renamed: {renamed_count}")
    print(f"Nodes Discarded: {discarded_count}")
    print(f"Final Clean Nodes: {len(new_nodes_list)}")
    
    id_map = {node['id']: node['new_id'] for node in new_nodes_list}

    return new_nodes_list, id_map


def rebuild_links_framework(cleaned_nodes, id_map):
    """
    PHASE 3: LINK GENERATION FRAMEWORK (Placeholder)
    This is where you integrate your existing Semantic Similarity script.
    """
    print("\n--- PHASE 3: Link Rebuilding Framework ---")
    print(f"Total nodes to analyze for links: {len(cleaned_nodes)}")
    
    new_links = []
    
    # 1. Vectorize all clean node descriptions
    # Replace this simple text extraction with your semantic model (Sentence-BERT/SciBERT)
    descriptions = [node.get("description", "") for node in cleaned_nodes]
    
    # Your script would calculate the embeddings here:
    # embeddings = your_semantic_model.encode(descriptions)
    
    # 2. Calculate All-Pairs Similarity (Idea 5)
    # similarity_matrix = cosine_similarity(embeddings)
    
    # 3. Iterate through the matrix to generate links (Idea 6)
    CLEAN_NODE_IDS = [node['new_id'] for node in cleaned_nodes]
    LINK_THRESHOLD = 0.75 # Example threshold
    K_NEAREST = 5         # Example K for dynamic thresholding
    
    for i, node_A in enumerate(cleaned_nodes):
        pass
        # In a real implementation, you'd use the similarity_matrix here.
        
        # FOR EXAMPLE ONLY: Generate a dummy link for the first 10 nodes to show structure
        # if i < 10 and i + 1 < len(cleaned_nodes):
        #      node_B = cleaned_nodes[i + 1]
        #      new_links.append({
        #          "source": node_A['new_id'],
        #          "target": node_B['new_id'],
        #          "type": "related to (SIMULATED)",
        #          "urls": []
        #      })
             
    print(f"Simulated new links generated: {len(new_links)}")
    return new_links

# --- Main Execution ---
if __name__ == "__main__":
    
    data = load_data(INPUT_FILE)
    if data is None:
        exit()
        
    # --- PHASE 1 & 2: CLEANING AND CANONICALIZATION ---
    cleaned_nodes, id_map = process_duplicates(data)

    # --- PHASE 3: LINK REBUILDING ---
    # The new_links list will contain your rebuilt graph connections
    new_links = rebuild_links_framework(cleaned_nodes, id_map)
    
    # --- PHASE 4: OUTPUT ---
    final_data = {
        "nodes": [
            {
                "id": node['new_id'],
                "name": node['name'],
                "description": node['description'],
                "urls": node['urls']
            }
            for node in cleaned_nodes
        ],
        "links": new_links
    }
    
    with open(OUTPUT_CLEANED_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n--- SUCCESS ---")
    print(f"Cleaned data saved to: {OUTPUT_CLEANED_FILE}")
    print("Next Steps: Replace the placeholder in `rebuild_links_framework` with your actual semantic script.")
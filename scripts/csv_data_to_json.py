import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

def convert_csv_to_d3_json():
    """
    Reads graph data from topics.csv and links.csv using pandas,
    transforms it into a D3.js-compatible JSON format, and saves it
    to d3_graph_data.json.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    TOPICS_FILE = DATA_DIR / "topics.csv"
    LINKS_FILE = DATA_DIR / 'links.csv'
    OUTPUT_FILE = DATA_DIR / 'd3_graph_data.json'
    URLS_FILE = DATA_DIR / 'urls.csv'  # NEW: File containing URLs to embed

    try:
        # --- Step 1: Read all source CSV files ---
        topics_df = pd.read_csv(TOPICS_FILE)
        links_df = pd.read_csv(LINKS_FILE)
        
        # --- NEW: Process URLs into a lookup map ---
        url_map = defaultdict(list)
        try:
            urls_df = pd.read_csv(URLS_FILE)
            # Ensure identifiers are strings for consistent matching
            urls_df['Identifier'] = urls_df['Identifier'].astype(str)
            for index, row in urls_df.iterrows():
                url_map[row['Identifier']].append(row['URL'])
            print(f"Successfully processed {len(urls_df)} entries from {URLS_FILE}")
        except FileNotFoundError:
            print(f"Warning: {URLS_FILE} not found. No URLs will be added to the graph data.")
        # --- END OF NEW SECTION ---

        # --- Step 2: Process nodes and embed URLs ---
        topics_df['Index'] = topics_df['Index'].astype(str)
        nodes_df = topics_df[['Index', 'Topic', 'Description / Key Concepts']].rename(columns={
            'Index': 'id',
            'Topic': 'name',
            'Description / Key Concepts': 'description'
        })
        nodes_list = nodes_df.to_dict(orient='records')

        # Add the 'urls' key to each node object
        for node in nodes_list:
            node['urls'] = url_map.get(node['id'], [])

        # --- Step 3: Process links (explicit and hierarchical) ---
        links_df['Source Index'] = links_df['Source Index'].astype(str)
        links_df['Target Index'] = links_df['Target Index'].astype(str)
        explicit_links_df = links_df[['Source Index', 'Target Index', 'Relation Type']].rename(columns={
            'Source Index': 'source',
            'Target Index': 'target',
            'Relation Type': 'type'
        })
        links_list = explicit_links_df.to_dict(orient='records')
        
        hierarchical_links = []
        node_id_set = set(nodes_df['id'])
        for node in nodes_list:
            child_id = node['id']
            if '.' in child_id:
                parent_id = '.'.join(child_id.split('.')[:-1])
                if parent_id in node_id_set:
                    hierarchical_links.append({
                        'source': parent_id,
                        'target': child_id,
                        'type': 'sub topic'
                    })
        
        all_links = links_list + hierarchical_links
        
        # --- NEW: Embed URLs into each link object ---
        for link in all_links:
            # Reconstruct the composite ID format used in urls.csv
            link_identifier = f"{link['source']}|{link['target']}|{link['type']}"
            link['urls'] = url_map.get(link_identifier, [])
        # --- END OF NEW SECTION ---

        # Step 4: Combine into the final JSON object
        d3_graph_data = {
            'nodes': nodes_list,
            'links': all_links
        }

        # Step 5: Save the JSON object to the output file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(d3_graph_data, f, ensure_ascii=False, indent=4)
        
        print(f"Successfully merged all data and saved to {OUTPUT_FILE}")

    except FileNotFoundError as e:
        print(f"Error: Could not find a required file - {e}. Please ensure '{TOPICS_FILE}' and '{LINKS_FILE}' exist.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    convert_csv_to_d3_json()
import pandas as pd
import json
from pathlib import Path

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

    try:
        # Step 1: Read CSV files into pandas DataFrames
        topics_df = pd.read_csv(TOPICS_FILE)
        links_df = pd.read_csv(LINKS_FILE)

        # Step 2: Process nodes from topics.csv
        topics_df['Index'] = topics_df['Index'].astype(str)
        nodes_df = topics_df[['Index', 'Topic', 'Description / Key Concepts']].rename(columns={
            'Index': 'id',
            'Topic': 'name',
            'Description / Key Concepts': 'description'
        })
        nodes_list = nodes_df.to_dict(orient='records')

        # Step 3: Process explicit links from links.csv
        links_df['Source Index'] = links_df['Source Index'].astype(str)
        links_df['Target Index'] = links_df['Target Index'].astype(str)
        explicit_links_df = links_df[['Source Index', 'Target Index', 'Relation Type']].rename(columns={
            'Source Index': 'source',
            'Target Index': 'target',
            'Relation Type': 'type'
        })
        links_list = explicit_links_df.to_dict(orient='records')

        # --- NEW: Generate Hierarchical Links ---
        print("Generating hierarchical 'sub topic' links...")
        hierarchical_links = []
        # Create a set of all valid node IDs for fast parent lookups
        node_id_set = set(nodes_df['id'])

        for node in nodes_list:
            child_id = node['id']
            # A child node must have a '.' in its ID
            if '.' in child_id:
                # Calculate parent ID by removing the last segment
                parent_id = '.'.join(child_id.split('.')[:-1])
                
                # Verify the calculated parent ID actually exists before creating a link
                if parent_id in node_id_set:
                    hierarchical_links.append({
                        'source': parent_id,
                        'target': child_id,
                        'type': 'sub topic'
                    })
        
        print(f"Generated {len(hierarchical_links)} hierarchical links.")

        # Combine the explicit links from links.csv with the new hierarchical ones
        all_links = links_list + hierarchical_links
        # --- END OF NEW SECTION ---

        # Step 4: Combine into a single D3.js-compatible JSON object
        d3_graph_data = {
            'nodes': nodes_list,
            'links': all_links
        }

        # Step 5: Save the JSON object to the output file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(d3_graph_data, f, ensure_ascii=False, indent=4)
        
        print(f"Successfully converted data and saved to {OUTPUT_FILE}")

    except FileNotFoundError as e:
        print(f"Error: Could not find the file - {e}. Please ensure that '{TOPICS_FILE}' and '{LINKS_FILE}' are in the correct directory.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    convert_csv_to_d3_json()
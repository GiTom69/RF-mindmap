import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from tqdm import tqdm

def main():
    """
    Main function to run the link sanity check, analyze links using the Gemini API,
    and generate a Markdown report.
    """
    print("--- Starting Link Sanity Check Script ---")

    # --- Setup Paths ---
    # Assumes this script is in 'scripts/', so we go up one level for the project root
    project_root = Path(__file__).resolve().parent.parent
    data_file = project_root / "data" / "d3_graph_data.json"
    output_file = project_root / "data" / "link_review_report.md"
    env_file = project_root / ".env"

    # --- Handle API Key ---
    print(f"Loading API key from {env_file}...")
    load_dotenv(dotenv_path=env_file)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("Error: GEMINI_API_KEY not found in .env file. Please check your configuration.")
        return

    # --- Initialize Gemini ---
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        print("Successfully initialized Gemini API with 'gemini-flash-latest' model.")
    except Exception as e:
        print(f"Error initializing Gemini API: {e}")
        return

    # --- Load Data ---
    print(f"Loading graph data from {data_file}...")
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The data file was not found at {data_file}.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {data_file}. Please check its format.")
        return

    # Create a dictionary for fast node lookups by ID
    node_map = {node['id']: node for node in graph_data.get('nodes', [])}
    links_to_review = graph_data.get('links', [])
    
    if not links_to_review:
        print("No links found in the data file. Exiting.")
        return
    
    print(f"Found {len(node_map)} nodes and {len(links_to_review)} links to review.")

    # --- Prepare for Report Generation ---
    report_lines = [
        "# Link Sanity Check Report",
        "\nThis report was automatically generated to review the logical soundness of the links in `d3_graph_data.json`.",
        "\n---"
    ]

    # --- Iterate and Analyze ---
    print("Beginning analysis of links... (Note: A ~16 second delay between requests is required to respect API rate limits)")
    with tqdm(total=len(links_to_review), desc="Analyzing Links") as pbar:
        for link in links_to_review:
            source_id = link.get('source')
            target_id = link.get('target')
            link_type = link.get('type')

            # Look up full node details
            source_node = node_map.get(source_id)
            target_node = node_map.get(target_id)

            if not source_node or not target_node:
                pbar.update(1)
                continue # Skip links with non-existent nodes

            # Construct the prompt for the Gemini API
            prompt = (
                'You are a subject matter expert in science and engineering. Your task is to analyze a '
                'conceptual link between two topics from a mind map and determine its logical soundness.\n\n'
                'Analyze the following relationship:\n'
                f'- Source Topic: "{source_node["name"]}"\n'
                f'- Source Description: "{source_node["description"]}"\n'
                f'- Target Topic: "{target_node["name"]}"\n'
                f'- Target Description: "{target_node["description"]}"\n'
                f'- Relationship: "{source_node["name"]}" **{link_type}** "{target_node["name"]}"\n\n'
                'Based on this information, evaluate the logical soundness of this link.\n'
                'Respond with a simple JSON object with two keys:\n'
                '1. "confidence": A string, either "High", "Medium", or "Low".\n'
                '2. "justification": A brief, one-sentence justification for your confidence score.'
            )

            try:
                # API Call and Response Parsing
                response = model.generate_content(prompt)
                
                # Clean the response text to extract the JSON object
                cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
                ai_result = json.loads(cleaned_text)

                confidence = ai_result.get("confidence", "N/A").upper()
                justification = ai_result.get("justification", "No justification provided.")

                # Format the result for the Markdown report
                report_lines.append(f"\n### Link: `{source_id}` → `{target_id}` (\"{link_type}\")")
                report_lines.append(f"- **Source:** {source_node['name']}")
                report_lines.append(f"- **Target:** {target_node['name']}")
                report_lines.append(f"- **AI Confidence:** {confidence}")
                report_lines.append(f"- **Justification:** {justification}")
                report_lines.append("\n---")

            except Exception as e:
                print(f"\nAn error occurred while processing link {source_id} -> {target_id}: {e}")
                report_lines.append(f"\n### Link: `{source_id}` → `{target_id}` (\"{link_type}\")")
                report_lines.append("- **Error:** Could not get AI analysis for this link.")
                report_lines.append("\n---")
            
            pbar.update(1)
            # Rate Limiting: 4 requests/minute = 15s/request. 16s is a safe buffer.
            time.sleep(16)

    # --- Generate Markdown Report ---
    print(f"\nAnalysis complete. Writing report to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        print("Report successfully generated.")
    except Exception as e:
        print(f"Error writing report file: {e}")

    print("\n--- Script Finished ---")

if __name__ == '__main__':
    main()
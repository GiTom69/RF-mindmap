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
    and generate a Markdown report with immediate saving after each analysis.
    """
    print("--- Starting Link Sanity Check Script (Optimized with Immediate Save) ---")

    # --- Configuration and Paths ---
    project_root = Path(__file__).resolve().parent.parent
    data_file = project_root / "data" / "d3_graph_data.json"
    output_file = project_root / "data" / "link_review_report.md"
    env_file = project_root / ".env"
    TARGET_INTERVAL = 16.0  # seconds

    # --- Handle API Key ---
    print(f"Loading API key from {env_file}...")
    load_dotenv(dotenv_path=env_file)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
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
        print(f"Error: Could not decode JSON from {data_file}.")
        return

    node_map = {node['id']: node for node in graph_data.get('nodes', [])}
    links_to_review = graph_data.get('links', [])
    
    if not links_to_review:
        print("No links found in the data file. Exiting.")
        return
    
    print(f"Found {len(node_map)} nodes and {len(links_to_review)} links to review.")

    # --- Create Initial Report File ---
    print(f"Initializing report file at {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Link Sanity Check Report\n")
            f.write("\nThis report was automatically generated to review the logical soundness of the links in `d3_graph_data.json`.\n")
            f.write("\n---\n")
    except Exception as e:
        print(f"Error: Could not create the initial report file: {e}")
        return

    # --- Iterate, Analyze, and Append to Report ---
    print(f"Beginning analysis... Results will be saved immediately. Target interval: {TARGET_INTERVAL}s.")
    with tqdm(total=len(links_to_review), desc="Analyzing Links") as pbar:
        for link in links_to_review:
            start_time = time.monotonic()

            source_id = link.get('source')
            target_id = link.get('target')
            link_type = link.get('type')

            source_node = node_map.get(source_id)
            target_node = node_map.get(target_id)

            if not source_node or not target_node:
                pbar.update(1)
                continue

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
            
            report_block = "" # Initialize an empty string for the report content
            try:
                response = model.generate_content(prompt)
                cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
                ai_result = json.loads(cleaned_text)

                confidence = ai_result.get("confidence", "N/A").upper()
                justification = ai_result.get("justification", "No justification provided.")

                report_block = (
                    f"\n### Link: `{source_id}` → `{target_id}` (\"{link_type}\")\n"
                    f"- **Source:** {source_node['name']}\n"
                    f"- **Target:** {target_node['name']}\n"
                    f"- **AI Confidence:** {confidence}\n"
                    f"- **Justification:** {justification}\n"
                    f"\n---\n"
                )

            except Exception as e:
                print(f"\nAn error occurred while processing link {source_id} -> {target_id}: {e}")
                report_block = (
                    f"\n### Link: `{source_id}` → `{target_id}` (\"{link_type}\")\n"
                    f"- **Error:** Could not get AI analysis for this link.\n"
                    f"\n---\n"
                )
            
            # --- Append the result to the report file ---
            try:
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.write(report_block)
            except Exception as e:
                print(f"Error: Could not append to report file: {e}")

            pbar.update(1)
            
            # Dynamic Delay Logic
            end_time = time.monotonic()
            elapsed_time = end_time - start_time
            delay_needed = TARGET_INTERVAL - elapsed_time
            if delay_needed > 0:
                time.sleep(delay_needed)

    print("\n--- Script Finished ---")

if __name__ == '__main__':
    main()
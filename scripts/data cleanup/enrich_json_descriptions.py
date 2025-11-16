import json
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from google.api_core import exceptions as google_exceptions
import random


# --- Constants ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
JSON_FILE_IN = DATA_DIR / "d3_graph_data.json"
JSON_FILE_OUT = DATA_DIR / "d3_graph_data_better_described.json"
DESCRIPTION_WORD_LIMIT = 15
API_RETRY_DELAY = 1 # seconds to wait between API calls

# --- Rate Limiting & Retry Config ---
# Free tier can be as low as 5 Requests Per Minute (RPM).
# 60 seconds / 5 requests = 12 seconds per request.
# We'll use this as our base delay to be safe.
BASE_REQUEST_DELAY = 12  # seconds
MAX_RETRIES = 5

def load_nodes_from_json(filepath):
    """
    Safely loads and parses the JSON node file.
    """
    if not os.path.exists(filepath):
        print(f"Error: Input file not found at '{filepath}'")
        return None
    
    try:
        with open(filepath, 'r',encoding='utf-8') as f:
            data = json.load(f)
            if 'nodes' not in data or not isinstance(data['nodes'], list):
                print(f"Error: JSON file must have a top-level 'nodes' key containing a list.")
                return None
            return data
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{filepath}'.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}")
        return None

def save_nodes_to_json(filepath, data):
    """
    Saves the modified node data to a new JSON file.
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\nSuccessfully saved updated nodes to '{filepath}'")
    except IOError as e:
        print(f"Error: Could not write to output file '{filepath}'. {e}")
    except Exception as e:
        print(f"An unexpected error occurred while saving the file: {e}")

def filter_nodes_for_update(nodes_list):
    """
    Iterates over nodes and queues those with short descriptions.
    """
    queued_nodes = []
    for node in nodes_list:
        description = node.get('description', '').strip()
        
        # Count words in the description
        word_count = len(description.split())
        
        # Queue if description is empty or below the limit
        if word_count < DESCRIPTION_WORD_LIMIT:
            queued_nodes.append(node)
            
    return queued_nodes

def configure_gemini_model():
    """
    Loads API key from .env and configures the Gemini model.
    """
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("Error: 'GEMINI_API_KEY' not found in your .env file.")
        print("Please create a .env file and add your API key.")
        return None
        
    try:
        genai.configure(api_key=api_key)
        
        # Define the AI's role and constraints
        system_instruction = (
            "You are an expert in electrical engineering. Your task is to write "
            "clear, detailed, and informative descriptions for technical topics. "
            "The description should be 3-4 sentences long, explaining the core "
            "concept, its importance, and a key application. "
            "Do not just repeat the topic name in the description."
        )
        
        model = genai.GenerativeModel(
            model_name='gemini-flash-latest',
            system_instruction=system_instruction
        )
        return model
    except Exception as e:
        print(f"Error configuring Gemini model: {e}")
        return None

def get_new_description(model, topic_name):
    """
    Calls the Gemini API with robust rate limit handling and exponential backoff.
    """
    prompt = (
        f"Write a detailed, in-depth description for the electrical engineering topic: '{topic_name}'."
    )
    
    current_retries = 0
    backoff_time = BASE_REQUEST_DELAY
    
    while current_retries < MAX_RETRIES:
        try:
            # Add a delay *before* the request to respect the rate limit
            # On the first try (current_retries == 0), this is our base delay
            # On subsequent retries, this is our exponential backoff delay
            # Add "jitter" (a small random amount) to avoid thundering herd
            jitter = random.uniform(0, 1)
            sleep_duration = backoff_time + jitter
            
            if current_retries > 0:
                print(f"  [Rate Limit Hit] Retrying in {sleep_duration:.2f} seconds...")
            else:
                 # This is the normal, non-retry delay
                 print(f"  Waiting {sleep_duration:.2f}s to respect rate limit...")
                 
            time.sleep(sleep_duration)

            # Make the API call
            response = model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            else:
                print(f"  [API Warning] Received no text in response for '{topic_name}'.")
                return None # Don't retry on empty response

        except (google_exceptions.ResourceExhausted, google_exceptions.InternalServerError) as e:
            # This block catches 429 "Too Many Requests" and 500/503 "Internal Server Error"
            print(f"  [API Error] Rate limit or service unavailable for '{topic_name}'.")
            current_retries += 1
            backoff_time *= 2 # Exponential backoff
            
            if "429" not in str(e):
                 print(f"  [API Error] Service internal error, will retry: {e}")

        except Exception as e:
            # Handle other unexpected errors
            print(f"  [API Error] Failed to generate description for '{topic_name}': {e}")
            return None # Don't retry on unknown errors

    print(f"  [API Error] Max retries reached for '{topic_name}'. Skipping.")
    return None

def main():
    """
    Main execution logic.
    """
    # 1. Load data
    all_nodes_data = load_nodes_from_json(JSON_FILE_IN)
    if all_nodes_data is None:
        return # Error already printed
        
    nodes_list = all_nodes_data.get('nodes', [])
    total_nodes = len(nodes_list)
    
    # 2. Filter and summarize
    queued_nodes = filter_nodes_for_update(nodes_list)
    
    print("--- Node Processing Summary ---")
    print(f"Total nodes found: {total_nodes}")
    print(f"Nodes queued for description update: {len(queued_nodes)}")
    
    if not queued_nodes:
        print("All node descriptions meet the length requirement. Exiting.")
        return
        
    print("\nQueued topics:")
    for node in queued_nodes:
        print(f"  - {node.get('name', 'Unnamed Node')}")

    # 3. Configure Gemini API
    print("\nConfiguring Gemini API...")
    model = configure_gemini_model()
    
    if model is None:
        print("Exiting due to API configuration error.")
        return

    # 4. Batch process queued nodes
    print("\n--- Starting Batch Description Generation ---")
    processed_count = 0
    for node in queued_nodes:
        topic_name = node.get('name')
        if not topic_name:
            print("  Skipping node with no name.")
            continue
            
        print(f"Processing '{topic_name}'...")
        
        # 5. Get new description
        # This function now handles all delay and retry logic
        new_description = get_new_description(model, topic_name)
        
        if new_description:
            # 6. Replace old description
            old_description = node['description']
            node['description'] = new_description
            processed_count += 1
            print(f"  ...Success. Replaced old description:\n      '{old_description}'")
            print(f"      with new:\n      '{new_description[:60]}...'")
        else:
            print(f"  ...Failed. Keeping original description for '{topic_name}'.")
        
        # The delay logic is now *inside* get_new_description()
        # so no time.sleep() is needed here.

    # 7. Final summary and save
    print("\n--- Batch Processing Complete ---")
    print(f"Successfully updated {processed_count} out of {len(queued_nodes)} queued nodes.")
    
    # 8. Save the updated data
    save_nodes_to_json(JSON_FILE_OUT, all_nodes_data)

if __name__ == "__main__":
    main()
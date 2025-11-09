import os
import csv
import time
import re
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from tqdm import tqdm

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TOPICS_FILE = DATA_DIR / "topics.csv"
OUTPUT_TOPICS_FILE = DATA_DIR / "topics_described.csv"
BATCH_SIZE = 20 # Number of topics to process in a single API call

def save_topics_to_csv(filepath, topics_list, fieldnames):
    """Helper function to write the list of topics to a CSV file."""
    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(topics_list)
    except Exception as e:
        print(f"\nAn error occurred while writing to the file: {e}")

def main():
    print("--- Starting High-Speed Gemini Description Population Script ---")

    # --- Step 1: Load API Key ---
    load_dotenv()
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
        return

    # --- Step 2: Read Topics and Identify Missing Descriptions ---
    print(f"Reading topics from {TOPICS_FILE}...")
    try:
        with open(TOPICS_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            topics = list(reader)
            fieldnames = reader.fieldnames
    except FileNotFoundError:
        print(f"Error: The file {TOPICS_FILE} was not found.")
        return

    topics_to_update = []
    for topic in topics:
        description = topic.get("Description / Key Concepts", "")
        if description and "missing" in description.strip().lower():
            topics_to_update.append(topic)


    if not topics_to_update:
        print("No topics with 'MISSING' description found. Exiting.")
        return

    print(f"Found {len(topics_to_update)} topics to update. Processing in batches of {BATCH_SIZE}.")

    # --- Step 3: Initialize Gemini API ---
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('models/gemini-flash-latest')
        print("Successfully initialized Gemini API.")
    except Exception as e:
        print(f"Error initializing Gemini API: {e}")
        return

    # --- Step 4: Process in Batches ---
    with tqdm(total=len(topics_to_update), desc="Populating Descriptions") as pbar:
        for i in range(0, len(topics_to_update), BATCH_SIZE):
            batch = topics_to_update[i:i + BATCH_SIZE]
            
            # Construct a prompt with all topics in the batch
            prompt_lines = [
                "You are a subject matter expert in RF (Radio Frequency) Communications. "
                "Your task is to write a concise, single-paragraph explanation for each topic in the following list. "
                "Format your response by starting each explanation with the topic's unique index in brackets (e.g., '[1.1.1]'). "
                "Do not add any other text before or after the list of descriptions.\n",
                "TOPICS TO DESCRIBE:"
            ]
            for topic in batch:
                prompt_lines.append(f"[{topic.get('Index')}] {topic.get('Topic')}")
            
            prompt_lines.append("\nDESCRIPTIONS:")
            prompt = "\n".join(prompt_lines)

            try:
                response = model.generate_content(prompt)
                
                # --- Parse the single, multi-part response ---
                # This regex splits the text by the [Index] markers
                parts = re.split(r'\[(.*?)\]', response.text)
                
                updates_from_batch = {}
                # Start from 1, skipping the initial empty string from the split
                for j in range(1, len(parts), 2):
                    index = parts[j].strip()
                    description = parts[j+1].strip().replace('\n', ' ')
                    updates_from_batch[index] = description
                
                # Apply the updates to the main topics list
                for original_topic in topics:
                    idx = original_topic.get("Index")
                    if idx in updates_from_batch:
                        original_topic["Description / Key Concepts"] = updates_from_batch[idx]
                
                # Save progress after each successful batch
                save_topics_to_csv(OUTPUT_TOPICS_FILE, topics, fieldnames)

            except Exception as e:
                print(f"\nAn error occurred processing a batch: {e}")

            pbar.update(len(batch))
            
            # We still wait, but only once per batch, making it much faster overall
            if i + BATCH_SIZE < len(topics_to_update):
                 time.sleep(16)

    print(f"\n--- Script Finished. Final output saved to {OUTPUT_TOPICS_FILE} ---")

if __name__ == "__main__":
    main()
import json
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from google.api_core import exceptions as google_exceptions
import random


# --- Constants ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JSON_FILE_IN = DATA_DIR / "d3_graph_data.json"

def load_nodes_from_json(filepath):
    """
    Safely loads and parses the JSON node file.
    """
    if not os.path.exists(filepath):
        print(f"Error: Input file not found at '{filepath}'")
        return None
    
    try:
        with open(filepath, 'r',encoding="utf-8") as f:
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

def get_description_length(node):
    pass


def main():
    nodes = load_nodes_from_json(JSON_FILE_IN)
    nodes_desc_lengths = []

    for node in nodes['nodes']:
        nodes_desc_lengths.append(len(node['description']))

    HIST_BIN_SIZE = 5
    hist_bins = [[i, i+HIST_BIN_SIZE,0] for i in range(min(nodes_desc_lengths), max(nodes_desc_lengths), HIST_BIN_SIZE)]

    for index, length in enumerate(nodes_desc_lengths):
        for bin in hist_bins: # bin is a tuple (start, end)
            if bin[0] <= length < bin[1]:
                hist_bins[length%5][2] += 1
                break
    
    for bin in hist_bins:
        print(f"Length {bin[0]} to {bin[1]}: {bin[2]/5} nodes")
    
    # for bin in hist_bins:
    #     print(f"{bin[0]}\t->\t{bin[1]}:\t{'='*bin[2]/5}")


if __name__ == "__main__":
    main()
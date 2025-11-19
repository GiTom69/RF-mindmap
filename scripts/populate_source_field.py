#!/usr/bin/env python3
"""
populate_source_field.py

Populates the "source" field for topics in the d3_graph_data_with_syllabus.json file
based on which glossary extractor script generated them.

Maps:
- "RF-Opedia - Glossary of RF Terms.json" -> "Pasternack - RF-Opedia"
- "Glossary of Electronic Terms used in text_ [Analog Devices Wiki].json" -> "Analog Devices Wiki"
- "microwave_acronyms.json" -> "Microwaves101"

Usage:
    python populate_source_field.py
"""

import json
from pathlib import Path
from typing import Dict, Set, List, Any
from datetime import datetime
import shutil

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GLOSSARY_DIR = PROJECT_ROOT / "scripts" / "glossary extractors"

# Main graph data file
GRAPH_DATA_FILE = DATA_DIR / "d3_graph_data_with_syllabus.json"

# Glossary source files (these are created by the glossary extractor scripts)
# If they don't exist in the glossary extractors directory, check the scripts directory and old data
OLD_DATA_DIR = DATA_DIR / "old data"

GLOSSARY_FILES = {
    "Pasternack - RF-Opedia": [
        GLOSSARY_DIR / "RF-Opedia - Glossary of RF Terms.json",
        PROJECT_ROOT / "scripts" / "RF-Opedia - Glossary of RF Terms.json",
        OLD_DATA_DIR / "RF-Opedia - Glossary of RF Terms.json"
    ],
    "Analog Devices Wiki": [
        GLOSSARY_DIR / "Glossary of Electronic Terms used in text_ [Analog Devices Wiki].json",
        PROJECT_ROOT / "scripts" / "Glossary of Electronic Terms used in text_ [Analog Devices Wiki].json",
        OLD_DATA_DIR / "Glossary of Electronic Terms used in text_ [Analog Devices Wiki].json"
    ],
    "Microwaves101": [
        GLOSSARY_DIR / "microwave_acronyms.json",
        PROJECT_ROOT / "scripts" / "microwave_acronyms.json",
        OLD_DATA_DIR / "microwave_acronyms.json"
    ]
}


def load_json_file(path: Path) -> Any:
    """Load JSON data from a file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(path: Path, data: Any) -> None:
    """Save JSON data to a file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def backup_file(path: Path) -> None:
    """Create a timestamped backup of a file."""
    if not path.exists():
        return
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = path.parent / f"{path.stem}_backup_{timestamp}{path.suffix}"
    shutil.copy2(path, backup_path)
    print(f"Created backup: {backup_path.name}")


def load_glossary_terms(source_name: str, paths: List[Path]) -> Set[str]:
    """
    Load term names from a glossary JSON file.
    Tries multiple possible paths and returns a set of term names.
    """
    terms = set()
    
    for path in paths:
        if path.exists():
            print(f"Loading {source_name} from: {path}")
            try:
                data = load_json_file(path)
                
                # Handle both list and dict structures
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'name' in item:
                            terms.add(item['name'])
                elif isinstance(data, dict):
                    # If it's a dict, it might have a 'terms' key or be a single term
                    if 'terms' in data and isinstance(data['terms'], list):
                        for item in data['terms']:
                            if isinstance(item, dict) and 'name' in item:
                                terms.add(item['name'])
                    elif 'name' in data:
                        terms.add(data['name'])
                
                print(f"  Loaded {len(terms)} terms from {source_name}")
                return terms
            except Exception as e:
                print(f"  Warning: Failed to load {path}: {e}")
                continue
    
    if not terms:
        print(f"  Warning: No file found for {source_name}")
    
    return terms


def populate_sources(graph_data: Dict[str, Any], source_mappings: Dict[str, Set[str]]) -> int:
    """
    Update the source field for nodes in the graph data based on term name matches.
    Returns the count of updated nodes.
    """
    updated_count = 0
    nodes = graph_data.get('nodes', [])
    
    for node in nodes:
        node_name = node.get('name', '')
        current_source = node.get('source', 'original_dataset')
        
        # Only update if current source is 'original_dataset' to avoid overwriting
        # any manually set sources or sources from other processes
        if current_source == 'original_dataset':
            # Check each source mapping for a match
            for source_name, term_names in source_mappings.items():
                if node_name in term_names:
                    node['source'] = source_name
                    updated_count += 1
                    break  # Stop after first match
    
    return updated_count


def main():
    print("="*70)
    print("Populating source fields for glossary-extracted topics")
    print("="*70)
    print()
    
    # Check if main graph data file exists
    if not GRAPH_DATA_FILE.exists():
        print(f"Error: Graph data file not found: {GRAPH_DATA_FILE}")
        return
    
    print(f"Loading graph data from: {GRAPH_DATA_FILE}")
    graph_data = load_json_file(GRAPH_DATA_FILE)
    total_nodes = len(graph_data.get('nodes', []))
    print(f"Total nodes in graph: {total_nodes}")
    print()
    
    # Load all glossary term names
    print("Loading glossary sources...")
    print("-" * 70)
    source_mappings = {}
    
    for source_name, paths in GLOSSARY_FILES.items():
        terms = load_glossary_terms(source_name, paths)
        if terms:
            source_mappings[source_name] = terms
    
    print()
    
    if not source_mappings:
        print("Warning: No glossary files were found. No updates will be made.")
        return
    
    # Create backup before modifying
    backup_file(GRAPH_DATA_FILE)
    
    # Update source fields
    print("Updating source fields...")
    print("-" * 70)
    updated_count = populate_sources(graph_data, source_mappings)
    
    # Save updated graph data
    save_json_file(GRAPH_DATA_FILE, graph_data)
    
    print()
    print("="*70)
    print(f"Update complete!")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Nodes updated: {updated_count}")
    print(f"  Nodes unchanged: {total_nodes - updated_count}")
    print("="*70)
    
    # Show breakdown by source
    if updated_count > 0:
        print()
        print("Breakdown by source:")
        print("-" * 70)
        for source_name, terms in source_mappings.items():
            count = sum(1 for node in graph_data['nodes'] if node.get('source') == source_name)
            print(f"  {source_name}: {count} nodes")


if __name__ == "__main__":
    main()

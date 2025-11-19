"""
Update Node Categories Script

This script reads the classification results from the CSV file and updates
the "category" field in each node of the mind map JSON data.
"""

import json
import csv
from pathlib import Path
from datetime import datetime


def load_classifications(csv_path: Path) -> dict:
    """Load classifications from CSV file into a dictionary."""
    classifications = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = row['id']
            classification_label = row['classification_label']
            classifications[node_id] = classification_label
    
    return classifications


def update_node_categories(json_path: Path, classifications: dict) -> dict:
    """Update the category field in each node with the classification."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated_count = 0
    not_found_count = 0
    
    for node in data.get('nodes', []):
        node_id = node.get('id')
        
        if node_id in classifications:
            node['category'] = classifications[node_id]
            updated_count += 1
        else:
            not_found_count += 1
            print(f"Warning: Node {node_id} ({node.get('name', 'Unknown')}) not found in classifications")
    
    return data, updated_count, not_found_count


def save_updated_data(data: dict, output_path: Path, backup: bool = True):
    """Save the updated JSON data with optional backup."""
    if backup and output_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = output_path.parent / f"{output_path.stem}_backup_{timestamp}{output_path.suffix}"
        
        # Create backup
        with open(output_path, 'r', encoding='utf-8') as f:
            original_data = f.read()
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_data)
        
        print(f"✓ Created backup: {backup_path}")
    
    # Save updated data
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved updated data to: {output_path}")


def main():
    """Main execution function."""
    # Define paths
    project_root = Path(__file__).parent.parent
    csv_path = project_root / 'output' / 'classifications' / 'topic_classifications.csv'
    json_path = project_root / 'data' / 'd3_graph_data_with_syllabus.json'
    
    print("Update Node Categories Script")
    print("=" * 50)
    print(f"Loading classifications from: {csv_path}")
    
    # Load classifications
    classifications = load_classifications(csv_path)
    print(f"✓ Loaded {len(classifications)} classifications")
    
    # Load and update JSON data
    print(f"\nUpdating nodes in: {json_path}")
    data, updated_count, not_found_count = update_node_categories(json_path, classifications)
    
    print(f"✓ Updated {updated_count} nodes")
    if not_found_count > 0:
        print(f"⚠ {not_found_count} nodes not found in classifications")
    
    # Save updated data
    print("\nSaving updated data...")
    save_updated_data(data, json_path, backup=True)
    
    print("\n✓ Update complete!")


if __name__ == "__main__":
    main()

"""
Topic Classification Script

This script classifies topics from the mind map data into one of the following categories:
- Core concept in RF engineering
- Core concept in Electrical engineering  
- Core concept in System design
- Useful term in RF engineering
- Useful term in Electrical engineering
- Useful term in System design
- Other (mechanical engineering, chemical, unrelated terms)
"""

import json
import csv
from pathlib import Path
from typing import Dict, List
from collections import Counter


# Define classification categories
CATEGORIES = {
    "rf_core": "Core concept in RF engineering",
    "ee_core": "Core concept in Electrical engineering",
    "system_core": "Core concept in System design",
    "rf_useful": "Useful term in RF engineering",
    "ee_useful": "Useful term in Electrical engineering",
    "system_useful": "Useful term in System design",
    "other": "Other (mechanical, chemical, unrelated)"
}


def load_mindmap_data(filepath: str) -> Dict:
    """Load the mind map JSON data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def classify_topic(name: str, description: str) -> str:
    """
    Classify a topic based on its name and description.
    
    This is a rule-based classifier. You may want to enhance this with:
    - Machine learning models
    - LLM-based classification
    - Manual review and correction
    """
    name_lower = name.lower()
    desc_lower = description.lower() if description else ""
    combined = f"{name_lower} {desc_lower}"
    
    # RF Engineering Core Concepts
    rf_core_keywords = [
        'antenna', 'modulation', 'demodulation', 'frequency', 'wavelength',
        'propagation', 'transmission line', 'impedance matching', 'smith chart',
        's-parameters', 'noise figure', 'intermodulation', 'mixer', 'oscillator',
        'phase noise', 'spectrum', 'carrier', 'rf filter', 'amplifier gain',
        'power amplifier', 'low noise amplifier', 'matching network', 'vswr',
        'return loss', 'insertion loss', 'isolation', 'coupling', 'directivity',
        'link budget', 'friis', 'path loss', 'fading', 'doppler', 'beamforming',
        'mimo', 'ofdm', 'qam', 'psk', 'fsk', 'ask', 'ber', 'snr', 'evm',
        'acpr', 'aclr', 'spurious', 'harmonic', 'intermod', 'ip3', 'p1db'
    ]
    
    # RF Engineering Useful Terms
    rf_useful_keywords = [
        'connector', 'coaxial', 'waveguide', 'balun', 'diplexer', 'duplexer',
        'circulator', 'isolator', 'attenuator', 'termination', 'sma', 'n-type',
        'bnc', 'uhf connector', 'rf cable', 'pigtail', 'adapter', 'coupler',
        'power divider', 'splitter', 'combiner', 'hybrid', 'rat race',
        'wilkinson', 'lange', 'branch line'
    ]
    
    # Electrical Engineering Core Concepts
    ee_core_keywords = [
        'voltage', 'current', 'resistance', 'capacitance', 'inductance',
        'transformer', 'transistor', 'diode', 'mosfet', 'bjt', 'jfet',
        'operational amplifier', 'op-amp', 'feedback', 'oscillation',
        'filter design', 'analog circuit', 'digital circuit', 'logic gate',
        'semiconductor', 'p-n junction', 'doping', 'band gap', 'fermi level',
        'electron', 'hole', 'charge carrier', 'power supply', 'regulator',
        'rectifier', 'inverter', 'converter', 'switching', 'pwm'
    ]
    
    # Electrical Engineering Useful Terms
    ee_useful_keywords = [
        'ampere', 'volt', 'ohm', 'farad', 'henry', 'watt', 'joule',
        'coulomb', 'siemens', 'mho', 'resistor', 'capacitor', 'inductor',
        'potentiometer', 'thermistor', 'varistor', 'fuse', 'relay',
        'switch', 'battery', 'cell', 'ground', 'chassis', 'earth'
    ]
    
    # System Design Core Concepts
    system_core_keywords = [
        'architecture', 'topology', 'block diagram', 'signal flow',
        'interface', 'protocol', 'communication system', 'transceiver',
        'receiver', 'transmitter', 'baseband', 'if stage', 'heterodyne',
        'homodyne', 'superheterodyne', 'direct conversion', 'upconversion',
        'downconversion', 'channelization', 'multiplexing', 'fdma', 'tdma',
        'cdma', 'duplexing', 'fdd', 'tdd', 'half-duplex', 'full-duplex'
    ]
    
    # System Design Useful Terms  
    system_useful_keywords = [
        'ber', 'per', 'throughput', 'latency', 'jitter', 'clock',
        'synchronization', 'timing', 'control loop', 'agc', 'afc',
        'pll', 'dll', 'calibration', 'tuning', 'bandwidth', 'data rate'
    ]
    
    # Other domains
    mechanical_keywords = [
        'mechanical', 'thermal', 'housing', 'enclosure', 'mounting',
        'heatsink', 'cooling', 'fan', 'temperature', 'stress', 'strain',
        'torque', 'vibration', 'shock', 'material', 'alloy', 'metal',
        'machining', 'fabrication', 'assembly'
    ]
    
    chemical_keywords = [
        'chemical', 'etching', 'plating', 'coating', 'substrate',
        'dielectric constant', 'loss tangent', 'pcb material', 'epoxy',
        'resin', 'laminate', 'metallization'
    ]
    
    # Count keyword matches for each category
    scores = {
        "rf_core": sum(1 for kw in rf_core_keywords if kw in combined),
        "rf_useful": sum(1 for kw in rf_useful_keywords if kw in combined),
        "ee_core": sum(1 for kw in ee_core_keywords if kw in combined),
        "ee_useful": sum(1 for kw in ee_useful_keywords if kw in combined),
        "system_core": sum(1 for kw in system_core_keywords if kw in combined),
        "system_useful": sum(1 for kw in system_useful_keywords if kw in combined),
    }
    
    # Check for other domains
    mechanical_score = sum(1 for kw in mechanical_keywords if kw in combined)
    chemical_score = sum(1 for kw in chemical_keywords if kw in combined)
    
    if mechanical_score > 0 or chemical_score > 0:
        return "other"
    
    # Get the category with highest score
    max_score = max(scores.values())
    
    if max_score == 0:
        # No keywords matched - try to infer from context
        if any(term in combined for term in ['rf', 'radio', 'wireless', 'microwave', 'ghz', 'mhz']):
            return "rf_useful"
        elif any(term in combined for term in ['circuit', 'electronic', 'electrical']):
            return "ee_useful"
        elif any(term in combined for term in ['system', 'design', 'architecture']):
            return "system_useful"
        else:
            return "other"
    
    # Return category with highest score
    return max(scores.items(), key=lambda x: x[1])[0]


def classify_all_topics(data: Dict) -> List[Dict]:
    """Classify all topics in the mind map data."""
    results = []
    
    for node in data.get('nodes', []):
        name = node.get('name', '')
        description = node.get('description', '')
        node_id = node.get('id', '')
        
        classification = classify_topic(name, description)
        
        results.append({
            'id': node_id,
            'name': name,
            'description': description[:100] + '...' if len(description) > 100 else description,
            'classification': classification,
            'classification_label': CATEGORIES[classification]
        })
    
    return results


def save_results(results: List[Dict], output_dir: Path):
    """Save classification results to CSV and JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as CSV
    csv_path = output_dir / 'topic_classifications.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'name', 'classification', 'classification_label', 'description']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"✓ Saved CSV results to: {csv_path}")
    
    # Save as JSON
    json_path = output_dir / 'topic_classifications.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved JSON results to: {json_path}")
    
    # Generate summary statistics
    classification_counts = Counter(r['classification'] for r in results)
    
    summary_path = output_dir / 'classification_summary.txt'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("Topic Classification Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total topics classified: {len(results)}\n\n")
        
        for cat_key, cat_label in CATEGORIES.items():
            count = classification_counts.get(cat_key, 0)
            percentage = (count / len(results) * 100) if len(results) > 0 else 0
            f.write(f"{cat_label}: {count} ({percentage:.1f}%)\n")
    
    print(f"✓ Saved summary to: {summary_path}")
    
    # Print summary to console
    print("\n" + "=" * 50)
    print("Classification Summary")
    print("=" * 50)
    for cat_key, cat_label in CATEGORIES.items():
        count = classification_counts.get(cat_key, 0)
        percentage = (count / len(results) * 100) if len(results) > 0 else 0
        print(f"{cat_label}: {count} ({percentage:.1f}%)")


def main():
    """Main execution function."""
    # Define paths
    project_root = Path(__file__).parent.parent
    data_file = project_root / 'data' / 'd3_graph_data_with_syllabus.json'
    output_dir = project_root / 'output' / 'classifications'
    
    print("Topic Classification Script")
    print("=" * 50)
    print(f"Loading data from: {data_file}")
    
    # Load data
    data = load_mindmap_data(data_file)
    print(f"✓ Loaded {len(data.get('nodes', []))} topics")
    
    # Classify topics
    print("\nClassifying topics...")
    results = classify_all_topics(data)
    print(f"✓ Classified {len(results)} topics")
    
    # Save results
    print("\nSaving results...")
    save_results(results, output_dir)
    
    print("\n✓ Classification complete!")


if __name__ == "__main__":
    main()

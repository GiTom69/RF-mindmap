"""Quick stats for merged graph."""
import json
from pathlib import Path

data_file = Path(r"c:\Users\Tom\Desktop\WORK\Tom and RF knowlegde\RF-mindmap\data\d3_graph_data_with_syllabus.json")

with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("\n" + "="*60)
print("MERGED GRAPH STATISTICS")
print("="*60)

print(f"\n=== NODE STATISTICS ===")
print(f"Total Nodes: {len(data['nodes'])}")

sources = {}
for node in data['nodes']:
    src = node.get('source', 'unknown')
    sources[src] = sources.get(src, 0) + 1

print(f"\nBy Source:")
for src, count in sorted(sources.items()):
    print(f"  {src}: {count}")

categories = {}
for node in data['nodes']:
    cat = node.get('category', 'unknown')
    categories[cat] = categories.get(cat, 0) + 1

print(f"\nBy Category:")
for cat, count in sorted(categories.items()):
    print(f"  {cat}: {count}")

# Count syllabus nodes with professional foundations
prof_foundations = [n for n in data['nodes'] if n.get('professional_foundation')]
print(f"\nNodes with Professional Foundations: {len(prof_foundations)}")

print(f"\n=== LINK STATISTICS ===")
print(f"Total Links: {len(data['links'])}")

link_types = {}
for link in data['links']:
    lt = link.get('type', 'unknown')
    link_types[lt] = link_types.get(lt, 0) + 1

print(f"\nBy Type:")
for lt, count in sorted(link_types.items()):
    print(f"  {lt}: {count}")

print("\n" + "="*60)

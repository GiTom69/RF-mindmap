import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
input_file = DATA_DIR / "topics.csv"
output_file = DATA_DIR / "topics_split.csv"

def increment_index(index):
    """Increment the last number in a dotted index (e.g. '1.6.2.1' -> '1.6.2.2')."""
    parts = index.split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    return '.'.join(parts)

seen_indices = set()
collision_count = 0

with open(input_file, newline='', encoding='utf-8') as infile, \
     open(output_file, 'w', newline='', encoding='utf-8') as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    header = next(reader)
    writer.writerow(header)

    for row in reader:
        if not row or len(row) < 2:
            continue

        original_index = row[0].strip()
        index = original_index

        # Increment the last index until it's unique
        while index in seen_indices:
            index = increment_index(index)
            collision_count += 1

        seen_indices.add(index)
        row[0] = index
        writer.writerow(row)

print(f"Fixed indices saved to {output_file}")
print(f"Collisions fixed: {collision_count}")

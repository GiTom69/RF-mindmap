import csv
from pathlib import Path

# --- CONFIGURATION ---
# Assumes the script is in 'scripts/' and data is in 'data/'
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
input_file = DATA_DIR / "topics.csv"
output_file = DATA_DIR / "topics_split.csv"
FIELDNAMES = ["Index", "Topic", "Description / Key Concepts"]

with open(input_file, newline='', encoding='utf-8') as infile, \
     open(output_file, 'w', newline='', encoding='utf-8') as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    # Write header
    header = next(reader)
    writer.writerow(header)

    for row in reader:
        # Skip empty lines
        if not row or len(row) < 2:
            continue

        index, topic = row[0], row[1]
        rest = row[2:] if len(row) > 2 else []

        # Check if there are 3 or more commas in the line (=> 4+ items)
        if len(row) >= 4:
            # First line: keep the main topic
            writer.writerow([index, topic])

            # Subtopics (everything after topic)
            subtopics = row[2:]
            for i, subtopic in enumerate(subtopics, start=1):
                sub_index = f"{index}.{i}"
                writer.writerow([sub_index, subtopic.strip(), "MISSING"])
        else:
            # Write unchanged
            writer.writerow(row)

print(f"✅ Split entries saved to {output_file}")

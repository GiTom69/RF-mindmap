#!/usr/bin/env python3
"""
Extract glossary terms from a local copy of "RF-Opedia - Glossary of RF Terms.htm"
and write them to glossary.json.

The parser uses a heuristic: many entries in the provided file appear as
lines starting with an asterisk *Term* followed by a description block.
This script attempts to find those patterns in the file text and extract
name + description pairs robustly.

Output: glossary.json (list of objects)
"""

import re
import json
import html
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
INPUT_FILE = project_root / "data" / "RF-Opedia - Glossary of RF Terms.htm"

OUTPUT_FILE = "RF-Opedia - Glossary of RF Terms.json"

def load_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r'(?i)<\s*br\s*/?\s*>', '\n', raw)
    raw = re.sub(r'(?i)</p\s*>', '\n', raw)
    raw = re.sub(r'<[^>]+>', '', raw)
    return html.unescape(raw)

def clean_description(desc: str) -> str:
    # Replace any newline with a single space, collapse multiple spaces, strip
    s = desc.replace('\r', ' ').replace('\n', ' ')
    s = re.sub(r'\s{2,}', ' ', s)
    return s.strip()

def extract_terms(text: str):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    pattern = re.compile(
        r'(?m)^[ \t]*\*(?P<name>[^\*]{1,120}?)\*\s*(?:\t| )*\n(?P<desc>.*?)(?=(?:\n[ \t]*\*[^\*]+\*\s*\n)|\Z)',
        re.DOTALL
    )

    results = []
    seen_names = set()
    for m in pattern.finditer(text):
        name = m.group('name').strip()
        desc = m.group('desc').strip()
        desc = re.sub(r'\n{2,}', '\n\n', desc)
        desc = re.sub(r'\*\s*$', '', desc).strip()
        if not name or len(name) < 2:
            continue
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        # sanitize description: remove newline characters
        desc = clean_description(desc)
        results.append((name, desc))
    return results

def build_json_entries(pairs):
    entries = []
    for idx, (name, desc) in enumerate(pairs, start=1):
        entry = {
            "id": str(idx),
            "name": name,
            "description": desc,
            "urls": []
        }
        entries.append(entry)
    return entries

def main():
    p = Path(INPUT_FILE)
    if not p.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return

    text = load_text(p)
    pairs = extract_terms(text)
    entries = build_json_entries(pairs)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)

    print(f"Extracted {len(entries)} entries -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
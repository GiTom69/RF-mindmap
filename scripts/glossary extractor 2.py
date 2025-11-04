#!/usr/bin/env python3
"""
glossary_extract.py

Usage:
    python3 glossary_extract.py <input.txt>

Output:
    glossary.json  -> JSON array of objects:
    {
        "id": "1",
        "name": "TERM",
        "description": "sanitized description (no newlines)",
        "urls": []
    }
"""
import re
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
INPUT_FILE = project_root / "data" / "Glossary of Electronic Terms used in text_ [Analog Devices Wiki].txt"

OUTPUT_FILE = "Glossary of Electronic Terms used in text_ [Analog Devices Wiki].json"

# Regex patterns
TERM_MARKER_RE = re.compile(r'^\*+([^*\n][^*]*[^*\n]?)\*+\s*$')    # line like *term*
INLINE_TERM_RE = re.compile(r'^\*([^*]+)\*\s*(.+)$')             # *term* definition
SINGLE_LINE_TERM_RE = re.compile(r'^[A-Z][A-Za-z0-9 \-()/%]{0,60}$')
SKIP_LINE_RE = re.compile(r'^(https?://|Page Tools|Table of Contents|Last modified:|Return to|Back to Top|Analog|Manage Cookie|Powered by|Cookie Policy|Contact Us|Who We Are)', re.IGNORECASE)

def normalize_whitespace(s: str) -> str:
    # remove newlines, collapse whitespace, trim
    s = s.replace('\r', ' ').replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def find_glossary_start(lines):
    for i, L in enumerate(lines):
        if re.search(r'Glossary of ', L, re.IGNORECASE):
            return i
        if re.match(r'^\s*A\s*$', L):
            return i
    return 0

def parse_glossary(text: str):
    lines = text.splitlines()
    start = find_glossary_start(lines)
    lines = lines[start:]
    entries = []
    cur_term = None
    cur_def_lines = []
    i = 0
    n = len(lines)

    while i < n:
        L = lines[i].rstrip()
        i += 1
        if not L:
            if cur_term and cur_def_lines:
                cur_def_lines.append('')  # preserve paragraph boundary (will be removed later)
            continue
        if SKIP_LINE_RE.match(L):
            continue
        # standalone *term* line
        m = TERM_MARKER_RE.match(L)
        if m:
            if cur_term:
                entries.append((cur_term, '\n'.join(cur_def_lines)))
            cur_term = m.group(1).strip()
            cur_def_lines = []
            continue
        # inline *term*definition
        m2 = INLINE_TERM_RE.match(L)
        if m2:
            if cur_term:
                entries.append((cur_term, '\n'.join(cur_def_lines)))
            cur_term = m2.group(1).strip()
            cur_def_lines = [m2.group(2).strip()]
            continue
        # title-like single line followed by blank -> treat as term header
        if SINGLE_LINE_TERM_RE.match(L):
            # peek ahead to see if next non-empty looks like definition text
            j = i
            while j < n and lines[j].strip() == '':
                j += 1
            if j < n and lines[j].strip():
                if cur_term:
                    entries.append((cur_term, '\n'.join(cur_def_lines)))
                cur_term = L.strip()
                cur_def_lines = []
                while i < n and lines[i].strip() == '':
                    i += 1
                continue
        # accumulate definition if inside an entry
        if cur_term:
            cur_def_lines.append(L)
        else:
            # skip preamble before first term
            continue

    if cur_term:
        entries.append((cur_term, '\n'.join(cur_def_lines)))

    # post-process: normalize and deduplicate
    cleaned = []
    seen = {}
    for term, def_block in entries:
        t = normalize_whitespace(term)
        d = normalize_whitespace(def_block)
        if not t:
            continue
        key = t.lower()
        if key in seen:
            idx = seen[key]
            if cleaned[idx]['description'] and d and d != cleaned[idx]['description']:
                cleaned[idx]['description'] = cleaned[idx]['description'] + ' ' + d
            elif not cleaned[idx]['description'] and d:
                cleaned[idx]['description'] = d
        else:
            seen[key] = len(cleaned)
            cleaned.append({'term': t, 'definition': d})
    return cleaned

def build_output_struct(entries):
    output = []
    for idx, item in enumerate(entries, start=1):
        entry = {
            "id": str(idx),
            "name": item['term'],
            "description": item['definition'],
            "urls": []
        }
        output.append(entry)
    return output

def main():
    p = Path(INPUT_FILE)
    if not p.exists():
        print(f"Input file not found: {INPUT_FILE}")
        return

    raw = INPUT_FILE.read_text(encoding='utf-8', errors='ignore')
    parsed = parse_glossary(raw)
    structured = build_output_struct(parsed)
    out_path = Path('glossary.json')
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(structured, f, ensure_ascii=False, indent=4)
    print(f"Wrote {len(structured)} entries -> {out_path}")

if __name__ == '__main__':
    main()

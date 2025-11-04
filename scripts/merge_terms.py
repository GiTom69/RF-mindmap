#!/usr/bin/env python3
"""
merge_terms.py

Merge one or more JSON files of terms into a master JSON file.
Each term object is expected to follow:
{
  "id": "1",
  "name": "TERM",
  "description": "sanitized description (no newlines)",
  "urls": []
}

Behavior:
- If master file exists, load its terms and preserve its id scheme (stringified integers).
- New terms get ids starting from (max_existing_id + 1) as strings.
- Skip input terms whose "name" already exists in master (case-sensitive).
- If master does not exist, it will be created.
- Creates a dated backup of the master before overwriting.
"""
import argparse
import json
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any

def load_json_file(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(path: str, data: Any) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)
    os.replace(tmp, path)

def ensure_terms_list(obj: Any) -> List[Dict[str, Any]]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        # If the dict looks like one term, return [obj].
        # If it contains a top-level 'terms' key, try that
        if 'terms' in obj and isinstance(obj['terms'], list):
            return obj['terms']
        return [obj]
    raise ValueError('Unsupported JSON structure for terms.')

def max_id(terms: List[Dict[str, Any]]) -> int:
    maxv = 0
    for t in terms:
        tid = t.get('id')
        if tid is None:
            continue
        try:
            n = int(str(tid))
            if n > maxv:
                maxv = n
        except ValueError:
            continue
    return maxv

def term_key(term: Dict[str, Any]) -> str:
    return term.get('name', '').strip()

def merge_terms(master_terms: List[Dict[str, Any]],
                new_terms: List[Dict[str, Any]],
                start_id: int) -> (List[Dict[str, Any]], int, int):
    """
    Append new_terms to master_terms assigning ids from start_id+1 upward.
    Skip terms whose name already exists in master_terms.
    Returns (updated_master_terms, next_id, count_added)
    """
    existing_names = {term_key(t) for t in master_terms if term_key(t)}
    next_id = start_id
    added = 0
    for t in new_terms:
        name = term_key(t)
        if not name:
            # skip malformed term without a name
            continue
        if name in existing_names:
            continue
        next_id += 1
        t_copy = dict(t)  # don't mutate original
        t_copy['id'] = str(next_id)
        master_terms.append(t_copy)
        existing_names.add(name)
        added += 1
    return master_terms, next_id, added

def backup_file(path: str) -> None:
    if not os.path.exists(path):
        return
    ts = datetime.now().strftime('%Y%m%dT%H%M%S')
    backup_path = f"{path}.bak.{ts}"
    shutil.copy2(path, backup_path)

def main():
    parser = argparse.ArgumentParser(description='Merge JSON term files into a master file.')
    parser.add_argument('inputs', nargs='+', help='Input JSON files to merge')
    parser.add_argument('--master', '-m', required=True, help='Path to master JSON file to update')
    parser.add_argument('--allow-duplicates', action='store_true', help='Allow duplicate names (do not skip by name)')
    args = parser.parse_args()

    master_path = args.master

    # Load or initialize master
    if os.path.exists(master_path):
        master_raw = load_json_file(master_path)
        master_terms = ensure_terms_list(master_raw)
    else:
        master_terms = []

    start = max_id(master_terms)

    total_added = 0
    for input_path in args.inputs:
        if not os.path.exists(input_path):
            print(f"Skipping missing file: {input_path}")
            continue
        try:
            data = load_json_file(input_path)
        except Exception as e:
            print(f"Failed to read {input_path}: {e}")
            continue
        new_terms = ensure_terms_list(data)
        if args.allow_duplicates:
            # If duplicates allowed, treat existing_names as empty so merge always appends
            updated, start, added = merge_terms(master_terms, new_terms, start_id=start - 0)
            # Note: merge_terms checks existing names; to truly allow duplicates, we hack by clearing existing_names
            # Simpler: reassign ids directly for all new_terms and append
            # We'll handle that case below instead of the merge function
        else:
            master_terms, start, added = merge_terms(master_terms, new_terms, start)
            total_added += added

    # If allow_duplicates was set, reassign ids properly for all input terms and append them
    if args.allow_duplicates:
        # recompute start from original master (before these inputs)
        if os.path.exists(master_path):
            orig = ensure_terms_list(load_json_file(master_path))
            orig_start = max_id(orig)
        else:
            orig_start = 0
        next_id = orig_start
        # collect all inputs again and append everything regardless of name
        for input_path in args.inputs:
            if not os.path.exists(input_path):
                continue
            data = load_json_file(input_path)
            new_terms = ensure_terms_list(data)
            for t in new_terms:
                name = term_key(t)
                if not name:
                    continue
                next_id += 1
                t_copy = dict(t)
                t_copy['id'] = str(next_id)
                master_terms.append(t_copy)
                total_added += 1
        start = next_id

    # Backup master then save
    backup_file(master_path)
    # Save as a top-level list
    save_json_file(master_path, master_terms)

    print(f"Merging complete. Master file: {master_path}")
    print(f"Total terms now in master: {len(master_terms)}")
    print(f"New terms added: {total_added}")

if __name__ == '__main__':
    main()

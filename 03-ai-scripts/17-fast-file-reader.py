#!/usr/bin/env python3
import os
import sys
import json
import re
import argparse
from pathlib import Path
import hashlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CACHE_DIR = Path("tmp/cache")

def get_cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    hash_key = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{hash_key}.json"

def read_disk_cache(key: str):
    cache_file = get_cache_path(key)
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def write_disk_cache(key: str, data):
    cache_file = get_cache_path(key)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

def list_folder(folder_path: str, extensions=None):
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist.", file=sys.stderr)
        return []

    cache_key = f"list:{folder_path}:{','.join(sorted(extensions or []))}"
    cached = read_disk_cache(cache_key)
    if cached is not None:
        for item in cached:
            print(item)
        return cached

    ext_set = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions} if extensions else None
    results = []
    for root, _, files in os.walk(folder):
        for f in files:
            p = Path(root) / f
            if ext_set:
                if p.suffix.lower() in ext_set:
                    results.append(str(p.as_posix()))
            else:
                results.append(str(p.as_posix()))
    results.sort()
    write_disk_cache(cache_key, results)
    for item in results:
        print(item)
    return results

def read_file(file_path: str, max_bytes: int = None):
    p = Path(file_path)
    if not p.exists():
        print(f"Error: File '{file_path}' does not exist.", file=sys.stderr)
        return None
    try:
        size = p.stat().st_size
        bytes_to_read = min(size, max_bytes) if max_bytes else size
        with open(p, "rb") as f:
            raw = f.read(bytes_to_read)
        text = raw.decode("utf-8", errors="replace")
        print(text)
        return text
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}", file=sys.stderr)
        return None

def search_pattern(pattern: str, search_path: str = ".", extensions=None):
    base = Path(search_path)
    if not base.exists():
        print(f"Error: Search path '{search_path}' does not exist.", file=sys.stderr)
        return []
    ext_set = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions} if extensions else None
    regex = re.compile(pattern)
    results = []
    for root, _, files in os.walk(base):
        if ".git" in root or "tmp" in root or "node_modules" in root:
            continue
        for f in files:
            p = Path(root) / f
            if ext_set and p.suffix.lower() not in ext_set:
                continue
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_idx, line in enumerate(fh, 1):
                        if regex.search(line):
                            match_str = f"{p.as_posix()}:{line_idx}: {line.strip()}"
                            results.append(match_str)
                            print(match_str)
            except Exception:
                continue
    return results

def main():
    parser = argparse.ArgumentParser(description="Fast file reader and explorer.")
    parser.add_argument("--list-folder", type=str)
    parser.add_argument("--read-file", type=str)
    parser.add_argument("--max-bytes", type=int)
    parser.add_argument("--search-pattern", type=str)
    parser.add_argument("--path", type=str, default=".")
    parser.add_argument("--ext", type=str)
    args = parser.parse_args()
    extensions = [ext.strip() for ext in args.ext.split(",")] if args.ext else None
    if args.list_folder:
        list_folder(args.list_folder, extensions=extensions)
    elif args.read_file:
        read_file(args.read_file, max_bytes=args.max_bytes)
    elif args.search_pattern:
        search_pattern(args.search_pattern, search_path=args.path, extensions=extensions)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

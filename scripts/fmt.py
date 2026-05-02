#!/usr/bin/env python3
"""Check DocOps JSONL formatting without rewriting files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dol import compact_json, docops_dir, read_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DocOps JSONL files")
    parser.add_argument("--check", action="store_true", help="validate k.jsonl and ev.jsonl")
    args = parser.parse_args()
    root = docops_dir()
    files = [root / "k.jsonl", root / "ev.jsonl"]
    bad = []
    for path in files:
        try:
            read_jsonl(path)
        except (OSError, json.JSONDecodeError) as exc:
            bad.append({"file": str(path), "why": str(exc)})
    print(compact_json({"ok": not bad, "bad": bad, "mode": "check" if args.check else "noop"}))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())

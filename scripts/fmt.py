#!/usr/bin/env python3
"""Check DocOps JSONL formatting without rewriting files."""

from __future__ import annotations

import argparse
from dol import compact_json, validate_workspace


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DocOps JSONL files")
    parser.add_argument("--check", action="store_true", help="validate k.jsonl and ev.jsonl")
    args = parser.parse_args()
    result = validate_workspace()
    result["mode"] = "check" if args.check else "validate"
    print(compact_json(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

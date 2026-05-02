#!/usr/bin/env python3
"""Thin entrypoint for DocOps card promotion."""

from __future__ import annotations

import argparse

from dol import print_json, run_promote


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote or retire a candidate card")
    parser.add_argument("id")
    parser.add_argument("--to", choices=["acc", "ret"], default="acc")
    args = parser.parse_args()
    result = run_promote(args.id, args.to)
    print_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

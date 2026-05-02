#!/usr/bin/env python3
"""Thin entrypoint for deterministic DocOps lint."""

from __future__ import annotations

import argparse

from dol import print_json, run_lint


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DocOps Logic lint")
    parser.add_argument("--soft", action="store_true")
    args = parser.parse_args()
    result = run_lint(soft=args.soft)
    print_json(result)
    return 0 if args.soft or result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

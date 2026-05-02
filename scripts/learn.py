#!/usr/bin/env python3
"""Thin entrypoint for DocOps candidate learning."""

from __future__ import annotations

from dol import print_json, run_learn


def main() -> int:
    print_json(run_learn())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

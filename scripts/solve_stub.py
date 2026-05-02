#!/usr/bin/env python3
"""CP-SAT-compatible solver stub for Phase 1."""

from __future__ import annotations

import argparse

from dol import SOLVE_MODES, print_json, run_solve_stub


def main() -> int:
    parser = argparse.ArgumentParser(description="DocOps Logic solver stub")
    parser.add_argument("--mode", choices=sorted(SOLVE_MODES), default="check")
    args = parser.parse_args()
    print_json(run_solve_stub(args.mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

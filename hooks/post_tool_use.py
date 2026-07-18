#!/usr/bin/env python3
"""Record a safe, compact signature after supported Codex tool calls."""

from __future__ import annotations

from hook_common import command_signature, has_docops, load_dol, read_hook_input, workspace


def main() -> int:
    data = read_hook_input()
    root = workspace(data)
    if not has_docops(root):
        return 0
    dol = load_dol()
    dol.append_event(
        "cmd",
        root,
        cmd=command_signature(data),
        summary="PostToolUse",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

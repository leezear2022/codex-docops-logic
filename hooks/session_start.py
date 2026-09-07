#!/usr/bin/env python3
"""Load compact DocOps context at Codex session start."""

from __future__ import annotations

from hook_common import emit_additional_context, emit_continue, has_docops, load_dol, read_hook_input, workspace


def main() -> int:
    data = read_hook_input()
    root = workspace(data)
    if not has_docops(root):
        emit_continue()
        return 0

    context = load_dol().render_session_context(root)
    emit_additional_context(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

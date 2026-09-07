#!/usr/bin/env python3
"""Surface soft deterministic DocOps reminders when a Codex turn stops."""

from __future__ import annotations

from hook_common import emit_continue, emit_system_message, has_docops, load_dol, read_hook_input, workspace


def main() -> int:
    data = read_hook_input()
    root = workspace(data)
    if not has_docops(root):
        emit_continue()
        return 0
    result = load_dol().run_lint(root, soft=True)
    if result.get("miss"):
        fixes = ", ".join(str(item) for item in result.get("fix", []))
        emit_system_message(f"DocOps lint reminder: {result.get('why')}. Fix: {fixes}")
    else:
        emit_continue()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

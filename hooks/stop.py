#!/usr/bin/env python3
"""Surface soft deterministic DocOps reminders when a Codex turn stops."""

from __future__ import annotations

from hook_common import emit_json, has_docops, load_dol, read_hook_input, workspace


def main() -> int:
    data = read_hook_input()
    root = workspace(data)
    if not has_docops(root):
        emit_json({"continue": True})
        return 0
    result = load_dol().run_lint(root, soft=True)
    output = {"continue": True}
    if result.get("miss"):
        fixes = ", ".join(str(item) for item in result.get("fix", []))
        output["systemMessage"] = f"DocOps lint reminder: {result.get('why')}. Fix: {fixes}"
    emit_json(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

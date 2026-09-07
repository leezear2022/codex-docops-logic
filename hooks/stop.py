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
    dol = load_dol()
    compacted = None
    if dol.projection_bool(root, "retention.auto_compact_current", False):
        try:
            compact_result = dol.run_compact(root, apply=True)
            if compact_result.get("changed"):
                compacted = (
                    f"DocOps compacted {compact_result['changed']} current document(s), "
                    f"saving about {compact_result['estimated_token_reduction']} startup tokens."
                )
        except (OSError, UnicodeError, ValueError) as exc:
            compacted = f"DocOps auto-compact failed safely: {exc}"
    result = dol.run_lint(root, soft=True)
    if result.get("miss"):
        fixes = ", ".join(str(item) for item in result.get("fix", []))
        prefix = f"{compacted} " if compacted else ""
        emit_system_message(f"{prefix}DocOps lint reminder: {result.get('why')}. Fix: {fixes}")
    elif compacted:
        emit_system_message(compacted)
    else:
        emit_continue()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Load compact DocOps context at Codex session start."""

from __future__ import annotations

from hook_common import emit_json, has_docops, read_hook_input, workspace


def main() -> int:
    data = read_hook_input()
    root = workspace(data)
    if not has_docops(root):
        emit_json({"continue": True})
        return 0

    docops = root / ".docops"
    state = (docops / "s.md").read_text(encoding="utf-8").strip()
    rules = (docops / "c.yaml").read_text(encoding="utf-8").strip()
    cards_path = docops / "k.jsonl"
    cards = cards_path.read_text(encoding="utf-8").splitlines()[-20:] if cards_path.exists() else []
    context = "\n".join([
        "DOCOPS STATE",
        state,
        "",
        "DOCOPS RULES",
        rules,
        "",
        "DOCOPS KB TAIL",
        *cards,
    ])
    emit_json({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

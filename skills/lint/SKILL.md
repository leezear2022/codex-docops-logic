---
name: docops-lint
description: Run deterministic DocOps Logic symbolic consistency checks.
---

# lint

Use before handoff, after changes, or when deciding if a claim has enough evidence.

Read:
- .docops/s.md
- .docops/c.yaml
- .docops/projection.yaml
- .docops/k.jsonl
- .docops/ev.jsonl

Write:
- none

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" lint --soft
python "<plugin-root>/scripts/lint.py" --soft
```

Rules:
- Script output is source of truth.
- LLM may explain results but must not decide compliance freely.
- R008 reports managed current documents that exceed configured line or token budgets.
- Preview `compact --dry-run` before applying any rewrite.

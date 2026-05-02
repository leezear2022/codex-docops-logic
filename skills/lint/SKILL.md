---
name: docops-lint
description: Run deterministic DocOps Logic symbolic consistency checks.
---

# lint

Use before handoff, after changes, or when deciding if a claim has enough evidence.

Read:
- .docops/s.md
- .docops/c.yaml
- .docops/k.jsonl
- .docops/ev.jsonl

Write:
- none

Prefer:
```bash
python3 codex-docops-logic/scripts/dol.py lint --soft
python3 codex-docops-logic/scripts/lint.py --soft
```

Rules:
- Script output is source of truth.
- LLM may explain results but must not decide compliance freely.

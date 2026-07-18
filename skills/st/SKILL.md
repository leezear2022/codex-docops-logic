---
name: docops-st
description: Activate and track DocOps Logic stages with short CP-ready state.
---

# st

Use when starting or switching implementation stages.

Read:
- .docops/s.md
- .docops/c.yaml

Write:
- .docops/s.md
- .docops/ev.jsonl
- optional docs/workstreams/<topic>/control/stages/

Prefer:
```bash
python3 "<plugin-root>/scripts/dol.py" st act s03
python3 "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- Before activation, stage plan edits may be in place.
- After activation, bump revision for exit criteria, validation, rollback, PR slicing, or dependency order changes.

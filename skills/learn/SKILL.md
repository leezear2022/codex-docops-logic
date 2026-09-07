---
name: docops-learn
description: Extract candidate DocOps Logic knowledge cards from repeated failures or repeated commands.
---

# learn

Use after repeated failures, rollbacks, corrections, or repeated commands.

Read:
- .docops/ev.jsonl
- .docops/k.jsonl

Write:
- .docops/k.jsonl
- .docops/ev.jsonl

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" learn
python "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- fail.same>=2 suggests L.cand.
- cmd.same>=3 suggests S.cand.
- Never auto-promote hard rules.

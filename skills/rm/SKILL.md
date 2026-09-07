---
name: docops-rm
description: Create or bump DocOps Logic roadmap versions with CP-ready history.
---

# rm

Use when roadmap order, scope, validation strategy, rollback strategy, assumptions, or exit criteria change.

Read:
- .docops/s.md
- .docops/c.yaml
- .docops/ev.jsonl

Write:
- .docops/s.md
- .docops/ev.jsonl
- optional docs/workstreams/<topic>/control/roadmap/

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" rm bump v02
python "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- Versions are v01, v02, v03.
- rm.bump requires rm.hist.
- Minor wording edits do not bump.

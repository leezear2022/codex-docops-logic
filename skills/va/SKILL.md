---
name: docops-va
description: Add deterministic validation evidence for a DocOps Logic change.
---

# va

Use after tests, builds, reviews, benchmarks, or an explicit validation deferral.

Read:
- .docops/s.md
- .docops/ev.jsonl
- .docops/c.yaml

Write:
- .docops/ev.jsonl
- .docops/s.md
- optional docs/workstreams/<topic>/evidence/validation/

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" va add --stage s03 --pr 128 --result pass
python "<plugin-root>/scripts/dol.py" va add --stage s03 --result def
python "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- Use result pass, fail, mix, or def.
- Performance claims need benchmark evidence; Phase 1 lint checks symbols only.

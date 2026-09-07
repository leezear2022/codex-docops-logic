---
name: docops-solve
description: Use the DocOps Logic Phase 1 solver stub and reserve the CP-SAT interface for Phase 2.
---

# solve

Use when checking, repairing, planning, or explaining symbolic conflicts.

Read:
- .docops/s.md
- .docops/c.yaml
- .docops/k.jsonl
- .docops/ev.jsonl

Write:
- none in Phase 1

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" solve --stub --mode check
python "<plugin-root>/scripts/dol.py" solve --stub --mode repair
python "<plugin-root>/scripts/solve_stub.py" --mode conflict
```

Rules:
- Phase 1 uses stub only.
- Do not claim CP-SAT or OR-Tools is implemented.
- Future modes: check, repair, plan, schedule, conflict.

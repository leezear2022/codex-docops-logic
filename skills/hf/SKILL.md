---
name: docops-hf
description: Update a compact handoff summary for paused or transferable DocOps Logic work.
---

# hf

Use before handoff, after long pauses, or when blockers need transfer.

Read:
- .docops/s.md
- .docops/ev.jsonl
- .docops/c.yaml

Write:
- .docops/handoff.md
- .docops/ev.jsonl
- optional docs/workstreams/<topic>/transfer/handoff.md

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" hf upd
python "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- Keep handoff short.
- Include next read targets and blockers.

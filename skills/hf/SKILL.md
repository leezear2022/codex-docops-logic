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
```bash
python3 codex-docops-logic/scripts/dol.py hf upd
python3 codex-docops-logic/scripts/dol.py lint --soft
```

Rules:
- Keep handoff short.
- Include next read targets and blockers.

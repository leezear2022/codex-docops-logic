---
name: docops-prom
description: Promote or retire candidate DocOps Logic cards without rewriting JSONL history.
---

# prom

Use when a candidate knowledge card is explicitly accepted or retired.

Read:
- .docops/k.jsonl

Write:
- .docops/k.jsonl
- .docops/ev.jsonl

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" prom L002
python "<plugin-root>/scripts/dol.py" prom L002 --to ret
```

Rules:
- Only cand can be promoted.
- Promotion appends a new card row with same id and new st.
- Do not turn user P cards into hard repo rules.

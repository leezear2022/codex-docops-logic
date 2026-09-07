---
name: docops-status
description: Read or update the compact DocOps Logic state file .docops/s.md.
---

# status

Use when reporting current topic, roadmap, stage, health, blockers, or next step.

Read:
- .docops/s.md
- .docops/c.yaml
- last 20 lines of .docops/k.jsonl

Write:
- .docops/s.md only when state changes

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" status
python "<plugin-root>/scripts/dol.py" st act <stage>
python "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- Keep s.md short.
- Put long explanation in optional workstream docs, not s.md.

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
```bash
python3 codex-docops-logic/scripts/dol.py status
python3 codex-docops-logic/scripts/dol.py st act <stage>
python3 codex-docops-logic/scripts/dol.py lint --soft
```

Rules:
- Keep s.md short.
- Put long explanation in optional workstream docs, not s.md.

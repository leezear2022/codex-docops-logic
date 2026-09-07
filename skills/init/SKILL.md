---
name: docops-init
description: Initialize DocOps Logic state for a topic with low-token .docops files and short AGENTS guidance.
---

# init

Use when starting DocOps Logic for a repo or new topic.

Read:
- AGENTS.md if present

Write:
- .docops/s.md
- .docops/k.jsonl
- .docops/c.yaml
- .docops/p.yaml
- .docops/ev.jsonl
- AGENTS.md only if missing or safely appendable

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" init <topic>
python "<plugin-root>/scripts/dol.py" status
python "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- Keep default context to AGENTS.md, .docops/s.md, .docops/c.yaml, and tail .docops/k.jsonl.
- Do not create long docs unless explicitly enabled.

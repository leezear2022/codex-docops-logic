---
name: docops-kb
description: Add or inspect symbolic DocOps Logic knowledge cards in .docops/k.jsonl.
---

# kb

Use for rules, conventions, lessons, counterexamples, diagnosis, env facts, script candidates, preferences, assumptions, or questions.

Read:
- .docops/k.jsonl
- .docops/c.yaml

Write:
- .docops/k.jsonl
- .docops/ev.jsonl

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" kb add --ty L --k bench.noise --v "repeat benchmark before perf claim"
python "<plugin-root>/scripts/dol.py" prom L002
```

Rules:
- Types: R C L X D E S P A Q.
- Learning creates cand only.
- P user preference is cost weight, not hard rule.

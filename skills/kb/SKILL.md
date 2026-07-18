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
```bash
python3 "<plugin-root>/scripts/dol.py" kb add --ty L --k bench.noise --v "repeat benchmark before perf claim"
python3 "<plugin-root>/scripts/dol.py" prom L002
```

Rules:
- Types: R C L X D E S P A Q.
- Learning creates cand only.
- P user preference is cost weight, not hard rule.

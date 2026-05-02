---
name: docops-ch
description: Log a compact DocOps Logic change event and update current state.
---

# ch

Use after code, plan, schema, docs, or workflow changes.

Read:
- .docops/s.md
- .docops/ev.jsonl

Write:
- .docops/ev.jsonl
- .docops/s.md
- optional docs/workstreams/<topic>/execution/changes/

Prefer:
```bash
python3 codex-docops-logic/scripts/dol.py ch add --stage s03 --pr 128 --slug simd-intrin-rewrite
python3 codex-docops-logic/scripts/dol.py lint --soft
```

Rules:
- A fix claim needs later va.pass or va.def.
- Use short slugs.

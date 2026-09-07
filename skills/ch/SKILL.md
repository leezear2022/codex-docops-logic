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
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" ch add --stage s03 --pr 128 --slug simd-intrin-rewrite
python "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- A fix claim needs later va.pass or va.def.
- Use short slugs.

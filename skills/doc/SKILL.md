---
name: docops-doc
description: Create standalone small plan and small changelog documents for DocOps Logic work.
---

# doc

Use whenever a small plan or small changelog is requested or implied.

Read:
- .docops/s.md
- docs/planning/ if present

Write:
- docs/planning/<topic>/*_PLAN_YYYY_MM_DD.md
- docs/planning/<topic>/*_CHANGELOG_YYYY_MM_DD.md
- .docops/ev.jsonl

Prefer:
- On Windows, prefer `& "<plugin-root>\scripts\dol.ps1" ...`; use `dol.cmd` from Command Prompt.
- On Linux/macOS, use `python "<plugin-root>/scripts/dol.py" ...`.

```bash
python "<plugin-root>/scripts/dol.py" doc new --kind plan --topic cpim-metal --slug metal-gac-v3-policy --title "Metal GAC v3 Policy Plan"
python "<plugin-root>/scripts/dol.py" doc new --kind changelog --topic cpim-metal --slug metal-gac-v3-policy --title "Metal GAC v3 Policy Changelog"
python "<plugin-root>/scripts/dol.py" doc new --kind plan --topic cpim-metal --dir docs/planning/metal_gac --slug metal-gac-v3-policy
python "<plugin-root>/scripts/dol.py" lint --soft
```

Rules:
- Every small plan must be a standalone document.
- Every small changelog must be a standalone document.
- Do not put multiple small plans or multiple small changelogs into one aggregate file.
- Aggregate documents may be indexes only.
- Link the new document from the project index or roadmap when appropriate.

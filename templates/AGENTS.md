# AGENTS.md

Use DocOps Logic for long work.

Read first:
- .docops/s.md
- .docops/c.yaml
- last 20 lines of .docops/k.jsonl
- docs/current/status.md and next_steps.md only after the compact control plane
- topic and archived evidence only when required

Rules:
- keep README static
- update s.md after work
- log ch for code/plan changes
- write each small plan and small changelog as a standalone doc
- claim fix only with va
- use short tokens
- keep managed current docs within .docops/projection.yaml budgets
- run `dol compact --dry-run` before `dol compact --apply`

Before handoff:
- dol lint --soft

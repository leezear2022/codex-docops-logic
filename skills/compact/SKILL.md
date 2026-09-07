---
name: docops-compact
description: Archive and compact managed current DocOps documents while preserving exact history and reducing startup token use.
---

# compact

Use when `docs/current/status.md` or `docs/current/next_steps.md` exceeds the
configured line or estimated-token budget.

Read:
- `.docops/s.md`
- `.docops/projection.yaml`
- only the two configured managed current documents

Write on `--apply`:
- compact current projections
- exact byte-for-byte snapshots below `docs/archive/current-snapshots/`
- `docs/archive/current_history_index.md`
- `.docops/compact.jsonl` and `.docops/ev.jsonl`

Run dry-run first and require a positive estimated token reduction:

```bash
python "<plugin-root>/scripts/dol.py" compact --dry-run
python "<plugin-root>/scripts/dol.py" compact --apply
```

Rules:
- Never compact topics, rules, experiment receipts, or arbitrary evidence.
- Never overwrite an unmanaged archive index.
- Preserve each preimage byte-for-byte and record its SHA-256.
- Navigate to archived history only when the current question requires it.
- Automatic Stop-hook compaction is opt-in with
  `retention.auto_compact_current: true`.

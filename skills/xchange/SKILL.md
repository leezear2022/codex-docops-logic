---
name: docops-exchange
description: Cross-agent document exchange - deliver work as the executor and answer audit findings.
---

# exchange

Use when a task is executed by one coding agent (you) and audited by another
agent (for example Kimi Code) through documents in `.docops/exchange/<task-id>/`.
This is an asynchronous document protocol, not a chat; agents never need to be
online at the same time.

Read:
- .docops/exchange/<task-id>/request.md (+ .json)
- latest round audit: .docops/exchange/<task-id>/rNNN/audit.md (+ .json)

Write:
- delivery / response docs via the CLI only (never edit old rounds)

Prefer:
```bash
# after finishing the work and running tests
python3 "<plugin-root>/scripts/dol.py" exchange deliver <task-id> \
  --result-commit <sha> --files a.py,b.py \
  --claims "what changed and why" \
  --va "python3 -m unittest discover -s tests=pass"

# when an audit report exists
python3 "<plugin-root>/scripts/dol.py" exchange status <task-id>
python3 "<plugin-root>/scripts/dol.py" exchange respond <task-id> \
  --finding F1 --action accept --note "fixed in <sha>"
python3 "<plugin-root>/scripts/dol.py" exchange respond <task-id> \
  --finding F2 --action dispute --note "evidence why the finding is wrong"

# after accepting/disputing, open the next round (deliver again), or close
python3 "<plugin-root>/scripts/dol.py" exchange close <task-id>
```

Rules:
- Deliver only from in_progress, changes_requested, or disputed; each deliver
  starts a new round and never overwrites an old one.
- Record real validation commands and results; approval is rejected unless
  every recorded result passes and the audit carries no blocker/major finding.
- Every finding needs exactly one response with a non-empty evidence --note
  before the next round can start; responses are immutable per finding.
- Dispute a finding only with concrete evidence in --note.
- Audit approval does not replace project CI or human review.
- If you are the auditor instead, follow templates/kimi-auditor.md.

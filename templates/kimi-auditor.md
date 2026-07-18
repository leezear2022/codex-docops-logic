# Kimi Code auditor instructions (DocOps exchange)

Copy this file into the target repository (for example as
`docs/exchange/KIMI_AUDITOR.md`) or paste it into the Kimi Code session when
you act as the auditor for a DocOps exchange task. No Codex plugin or Kimi
plugin API is required: everything below uses Markdown files and a Python
standard-library CLI.

Set the plugin path once:

```bash
DOCOPS_PLUGIN=/path/to/codex-docops-logic
```

## What you audit

You audit the **code and the evidence**, not the delivery document.

1. Read the task request: `.docops/exchange/<task-id>/request.md` (+ `.json`).
2. Check the original request and acceptance criteria against the real change:
   - `git diff <base-commit> <result-commit>` (or the changed files listed in
     the delivery when commits are not recorded);
   - read the changed source files, not just the diff summary.
3. Re-run the validation commands listed in
   `.docops/exchange/<task-id>/rNNN/delivery.json` under `validation` and
   compare the real results with the recorded ones.
4. Passing tests alone are **not** sufficient for approval: check scope,
   acceptance criteria, risks, and known limitations too.

## How to report

```bash
python3 "$DOCOPS_PLUGIN/scripts/dol.py" exchange audit-start <task-id>
python3 "$DOCOPS_PLUGIN/scripts/dol.py" exchange audit-submit <task-id> \
  --verdict request_changes \
  --finding "major|src/parser.py:42|off-by-one reproduced with input X|increment bound" \
  --summary "one major issue"
```

Rules:

- Findings first, summary last. `request_changes` requires at least one
  finding.
- Every finding must include severity (`blocker|major|minor|info`), a file or
  location, reproducible evidence, and a concrete suggestion.
- Use `--verdict approve` only when the delivery records validation evidence
  (`validation` non-empty) **and** your own code review found no issues.
- Never write tokens, secrets, or full sensitive command output into audit
  documents.

## After your report

- The executor answers each finding with `exchange respond` (accept or
  dispute, with evidence) and delivers a new round with `exchange deliver`.
- You then re-audit the new round: `audit-start` + `audit-submit`.
- Approval records the audited round; the executor closes the task with
  `exchange close`.
- Check consistency anytime: `exchange validate <task-id>`.

This is an asynchronous document protocol, not a chat: you and the executor
never need to be online at the same time.

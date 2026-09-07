# DocOps Logic

DocOps Logic is a low-token Codex and Kimi Code workflow plugin for long,
multi-stage engineering work. It keeps current state, evidence, handoffs, and
reusable knowledge in compact, deterministic files instead of repeatedly
loading long planning documents.

Phase 1 is intentionally local and dependency-free. The `solve` command is a
repair suggestion stub; CP-SAT and OR-Tools are not implemented.

## What it creates

Running `init` in a target repository creates:

```text
.docops/
├── s.md       # current topic, roadmap, stage, health, blocker, next step
├── c.yaml     # deterministic symbolic rules
├── k.jsonl    # append-only knowledge cards
├── ev.jsonl   # append-only workflow events
└── p.yaml     # compact user preferences
```

It also creates or safely appends a short DocOps section to `AGENTS.md`.

## Requirements

- Codex or Kimi Code with plugin support
- Python 3.11 or newer
- No third-party Python packages
- Windows, Linux, and macOS are supported; CI runs on Windows and Linux

On Windows, verify that `python --version` resolves to Python 3.11 or newer
before enabling lifecycle hooks. Manual CLI use can also set
`DOCOPS_PYTHON=C:\path\to\python.exe`; the supplied `dol.ps1` and `dol.cmd`
launchers prefer that explicit interpreter.

See [Windows setup and troubleshooting](docs/WINDOWS.md) for complete Codex,
Kimi Code, PowerShell, path-with-spaces, and Python launcher guidance.

## Install as a Codex plugin

### Windows PowerShell

Clone the repository at the default personal plugin source path:

```powershell
New-Item -ItemType Directory -Force "$HOME\plugins", "$HOME\.agents\plugins"
git clone https://github.com/leezear2022/codex-docops-logic.git "$HOME\plugins\docops-logic"
```

The default personal marketplace file is
`$HOME\.agents\plugins\marketplace.json`. Use the same JSON shown below and
keep `source.path` as `./plugins/docops-logic`.

### Linux / macOS

```bash
mkdir -p ~/plugins ~/.agents/plugins
git clone https://github.com/leezear2022/codex-docops-logic.git ~/plugins/docops-logic
```

Create `~/.agents/plugins/marketplace.json` if it does not exist:

```json
{
  "name": "personal",
  "interface": {"displayName": "Personal"},
  "plugins": [
    {
      "name": "docops-logic",
      "source": {"source": "local", "path": "./plugins/docops-logic"},
      "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
      "category": "Coding"
    }
  ]
}
```

Then install and confirm discovery:

```bash
codex plugin add docops-logic@personal
codex plugin list
```

After installation, start a new Codex task so Codex discovers the plugin's
skills and hooks. In the interactive CLI, open `/hooks`, review the three
DocOps commands, and trust their current hash. Codex intentionally skips
non-managed hooks until this one-time trust review is complete.

The plugin uses the standard layout:

```text
.codex-plugin/plugin.json
skills/*/SKILL.md
hooks/hooks.json
scripts/*.py
```

Codex automatically discovers `hooks/hooks.json`; no explicit `hooks` field is
needed in the plugin manifest. If your personal marketplace already contains
other entries, append the `docops-logic` object instead of replacing the file.

## Install as a Kimi Code plugin

The repository ships a native `kimi.plugin.json` that reuses the same Skills,
Python CLI, and lifecycle hooks. In Kimi Code, run:

```text
/plugins install C:\path\to\codex-docops-logic
/reload
```

Use a GitHub repository URL instead of a local path when installing from a
remote checkout. Kimi plugin hooks receive plain context/reminder text, while
Codex hooks retain the Codex JSON response shape.

## Five-minute workflow

From the repository you want to manage, set the checkout or installed plugin
path once, then invoke the Windows launcher:

```powershell
$DOL = "C:\path\to\codex-docops-logic\scripts\dol.ps1"
& $DOL init rpc-7004
& $DOL status
& $DOL ch add --stage s01 --slug parser-fix
& $DOL lint
& $DOL va add --stage s01 --result pass
& $DOL lint
```

The `.cmd` launcher is available for Command Prompt:

```bat
set "DOL=C:\path\to\codex-docops-logic\scripts\dol.cmd"
call "%DOL%" status
```

On Linux or macOS:

```bash
DOCOPS_PLUGIN=/path/to/codex-docops-logic
python "$DOCOPS_PLUGIN/scripts/dol.py" init rpc-7004
python "$DOCOPS_PLUGIN/scripts/dol.py" status
python "$DOCOPS_PLUGIN/scripts/dol.py" ch add --stage s01 --slug parser-fix
python "$DOCOPS_PLUGIN/scripts/dol.py" lint
python "$DOCOPS_PLUGIN/scripts/dol.py" va add --stage s01 --result pass
python "$DOCOPS_PLUGIN/scripts/dol.py" lint
```

The first lint intentionally fails because a change claim needs later
validation. The second passes after `va add` records evidence.

## Commands

| Command | Purpose |
| --- | --- |
| `init <topic>` | Initialize compact state in the current repository |
| `status` | Print current state |
| `st act sNN` | Activate a stage |
| `rm bump vNN` | Bump the roadmap and record history |
| `ch add` | Record a change claim |
| `va add` | Record validation evidence or an explicit deferral |
| `kb add` | Append a symbolic knowledge card |
| `learn` | Suggest candidate cards from repeated events |
| `prom` | Accept or retire a candidate card append-only |
| `hf upd` | Refresh a compact handoff |
| `doc new` | Create one standalone plan or changelog |
| `exchange ...` | Cross-agent delivery, audit, response, and closure protocol |
| `validate` | Validate state and JSONL rows against repository contracts |
| `lint` | Evaluate deterministic workflow rules |
| `solve --stub` | Report Phase 1 repair suggestions |

Run `& $DOL --help` on Windows, or
`python "$DOCOPS_PLUGIN/scripts/dol.py" --help` on Linux/macOS, for all
options.

## Standalone microdocuments

Each small plan and changelog gets its own file:

```powershell
& $DOL doc new `
  --kind plan --topic parser --slug recovery --title "Parser recovery plan"
```

The default location is `docs/planning/<topic>/`. Existing files are not
overwritten unless `--force` is supplied.

## Cross-agent exchange (executor -> auditor)

`exchange` is an asynchronous document protocol for two coding agents: one
executes a task (for example Codex), another audits the real code (for example
Kimi Code). Documents live in `.docops/exchange/<task-id>/` with one `rNNN/`
directory per round, so history is append-only and the agents never need to be
online at the same time. It works in any repository; `init` is not required.

```powershell
$DOL = "C:\path\to\codex-docops-logic\scripts\dol.ps1"

# 1. create the task (any side, or the user)
& $DOL exchange new --id rpc-7004 --title "Fix RPC timeout" `
  --from user --to codex --acc "timeout retried" --base-commit abc123

# 2. Codex executes, then delivers with evidence
& $DOL exchange start rpc-7004
& $DOL exchange deliver rpc-7004 --result-commit def456 `
  --files src/rpc.py --claims "bounded retry with backoff" `
  --va "python -m unittest discover -s tests=pass"

# 3. hand the repo to Kimi Code (see templates/kimi-auditor.md); it reads the
#    request, reviews the real diff, re-runs the validation, then reports
& $DOL exchange audit-start rpc-7004
& $DOL exchange audit-submit rpc-7004 --verdict request_changes `
  --finding "major|src/rpc.py:88|retry unbounded under flood|cap retries at 3"

# 4. Codex answers every finding (accept with a fix, or dispute with evidence)
& $DOL exchange respond rpc-7004 --finding F1 `
  --action accept --note "capped at 3 in def789"

# 5. next round: deliver again (never overwrites round 1), re-audit, approve
& $DOL exchange deliver rpc-7004 --result-commit def789 `
  --files src/rpc.py --claims "cap retries at 3" `
  --va "python -m unittest discover -s tests=pass"
& $DOL exchange audit-start rpc-7004
& $DOL exchange audit-submit rpc-7004 --verdict approve
& $DOL exchange close rpc-7004

# anytime: machine-readable state and consistency checks
& $DOL exchange status rpc-7004
& $DOL exchange validate --all
```

Notes:

- This is an asynchronous document protocol, not a real-time message system;
  the two agents never need to be online at the same time.
- Git commit hashes are recommended evidence, not strictly required; empty
  `base_commit`/`result_commit` means "not recorded".
- Approval requires recorded validation evidence with **all results passing**
  (`fail`/`mix` block approval; use `not_applicable` with a reason for steps
  that do not apply, e.g. `--va "docs-only change, no tests applicable=not_applicable"`),
  and an approving audit may not carry `blocker`/`major` findings. Approval
  never replaces the project's own CI or human review.
- Every finding must be answered with exactly one immutable, evidence-backed
  response (`response-F<n>` documents, non-empty `--note`); a new round cannot
  start while findings are unanswered.
- The state machine (`requested -> ... -> approved -> closed`) rejects illegal
  transitions with actionable errors; there is no `--force` and no way to
  overwrite a previous round. Each Markdown document is pinned by a
  `md_sha256` in its sidecar, so after-the-fact edits are detected by
  `exchange validate`.
- `exchange validate` cross-checks the state index against the documents on
  disk in both directions and enforces per-status invariants.
- Kimi Code can install `kimi.plugin.json`, but installation is optional:
  `templates/kimi-auditor.md` plus this CLI and the exchange documents are
  enough to audit.

## Automatic hooks

When trusted and enabled, the plugin:

- loads `.docops/s.md`, `.docops/c.yaml`, and the last 20 knowledge cards at
  session start;
- records compact Bash, PowerShell, command-shell, and file-edit events after
  supported tool calls;
- runs soft lint at turn stop and surfaces actionable reminders.

Hooks only act when the current repository already contains `.docops/`.

## Development

```powershell
python -m unittest discover -s tests -v
python -m compileall -q scripts hooks
python scripts/dol.py --help
```

Plugin validation is performed with Codex's `plugin-creator` validator before
installation. CI runs the standard-library test suite on Windows and Ubuntu
for supported Python versions.

## Limitations

- Phase 1 parses the deliberately small generated YAML subset without PyYAML.
- Rule linting is symbolic, not a general YAML or constraint solver.
- Performance claims require benchmark events, but benchmark orchestration is
  not yet provided.
- Hooks are guardrails and do not cover every possible hosted tool path.

## License

[MIT](LICENSE)

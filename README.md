# DocOps Logic

DocOps Logic is a low-token Codex workflow plugin for long, multi-stage
engineering work. It keeps current state, evidence, handoffs, and reusable
knowledge in compact, deterministic files instead of repeatedly loading long
planning documents.

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

- Codex with plugin support
- Python 3.11 or newer
- No third-party Python packages

## Install as a Codex plugin

For personal local development, clone the repository at the default personal
plugin source path:

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

After installation, start a new Codex thread so Codex discovers the plugin's
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

## Five-minute workflow

From the repository you want to manage, set the checkout or installed plugin
path once, then invoke the CLI:

```bash
DOCOPS_PLUGIN=/path/to/codex-docops-logic
python3 "$DOCOPS_PLUGIN/scripts/dol.py" init rpc-7004
python3 "$DOCOPS_PLUGIN/scripts/dol.py" status
python3 "$DOCOPS_PLUGIN/scripts/dol.py" ch add --stage s01 --slug parser-fix
python3 "$DOCOPS_PLUGIN/scripts/dol.py" lint
python3 "$DOCOPS_PLUGIN/scripts/dol.py" va add --stage s01 --result pass
python3 "$DOCOPS_PLUGIN/scripts/dol.py" lint
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
| `validate` | Validate state and JSONL rows against repository contracts |
| `lint` | Evaluate deterministic workflow rules |
| `solve --stub` | Report Phase 1 repair suggestions |

Run `python3 "$DOCOPS_PLUGIN/scripts/dol.py" --help` for all options.

## Standalone microdocuments

Each small plan and changelog gets its own file:

```bash
python3 "$DOCOPS_PLUGIN/scripts/dol.py" doc new \
  --kind plan --topic parser --slug recovery --title "Parser recovery plan"
```

The default location is `docs/planning/<topic>/`. Existing files are not
overwritten unless `--force` is supplied.

## Automatic hooks

When trusted and enabled, the plugin:

- loads `.docops/s.md`, `.docops/c.yaml`, and the last 20 knowledge cards at
  session start;
- records compact Bash and file-edit events after supported tool calls;
- runs soft lint at turn stop and surfaces actionable reminders.

Hooks only act when the current repository already contains `.docops/`.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py hooks/*.py
python3 scripts/dol.py --help
```

Plugin validation is performed with Codex's `plugin-creator` validator before
installation. CI runs the standard-library test suite on supported Python
versions.

## Limitations

- Phase 1 parses the deliberately small generated YAML subset without PyYAML.
- Rule linting is symbolic, not a general YAML or constraint solver.
- Performance claims require benchmark events, but benchmark orchestration is
  not yet provided.
- Hooks are guardrails and do not cover every possible hosted tool path.

## License

[MIT](LICENSE)

# Windows support

DocOps Logic treats Windows as a first-class platform. The Python core uses
`pathlib`, UTF-8 files, atomic replacement, and exclusive lock files; Windows
CI runs the same contract, hook, exchange, and tamper-detection tests as Linux.

## Prerequisites

- Windows 10 or newer
- Python 3.11 or newer
- Codex or Kimi Code when using the plugin integration
- Git when Codex and Kimi exchange work through commits

Check the interpreter that lifecycle hooks will use:

```powershell
python --version
python -c "import sys; assert sys.version_info >= (3, 11)"
```

If `python` opens Microsoft Store or reports that it is not found, install
Python from python.org and enable **Add python.exe to PATH**. Windows launchers
also support an explicit interpreter:

```powershell
$env:DOCOPS_PYTHON = "C:\path\to\python.exe"
```

`DOCOPS_PYTHON` affects `dol.ps1` and `dol.cmd`. Lifecycle hook manifests call
`python` directly so the host process must have a real Python 3.11+ command on
its `PATH`.

## CLI launchers

PowerShell:

```powershell
$DOL = "C:\path\to\codex-docops-logic\scripts\dol.ps1"
& $DOL --help
& $DOL init demo
& $DOL status
```

Command Prompt:

```bat
set "DOL=C:\path\to\codex-docops-logic\scripts\dol.cmd"
call "%DOL%" --help
call "%DOL%" status
```

Both launchers:

1. use `DOCOPS_PYTHON` when set;
2. otherwise try a working Python Launcher for Windows (`py -3`);
3. otherwise try `python`;
4. reject interpreters older than Python 3.11.

Paths containing spaces are quoted and covered by automated tests.

## Codex installation

Clone under the default personal plugin source:

```powershell
New-Item -ItemType Directory -Force "$HOME\plugins", "$HOME\.agents\plugins"
git clone https://github.com/leezear2022/codex-docops-logic.git "$HOME\plugins\docops-logic"
```

The personal marketplace file is:

```text
C:\Users\<user>\.agents\plugins\marketplace.json
```

After the marketplace entry points to `./plugins/docops-logic`:

```powershell
codex plugin add docops-logic@personal
codex plugin list
```

Start a new Codex task, open `/hooks`, and trust the current hashes. The Codex
hook manifest quotes `${PLUGIN_ROOT}`, so managed plugin paths containing spaces
remain valid.

## Kimi Code installation

The repository includes `kimi.plugin.json` with the same Skills and three
lifecycle hooks:

```text
/plugins install C:\path\to\codex-docops-logic
/reload
```

Kimi hooks use the Kimi stdout contract:

- `SessionStart` prints compact DocOps state, rules, and recent knowledge.
- `PostToolUse` records a redacted executable signature.
- `Stop` prints a soft deterministic lint reminder when evidence is missing.

Codex continues to receive its JSON hook response shape. The shared Python
scripts detect the host through `KIMI_PLUGIN_ROOT`.

## PowerShell tool events

The PostToolUse hook recognizes:

- `PowerShell` and `pwsh`
- `cmd`
- `Shell`
- `exec_command` and `write_stdin`
- `Bash`
- file edit tools such as `apply_patch`, `Edit`, and `Write`

Only the tool name and executable basename are persisted. Full commands,
arguments, tokens, and secrets are not written to `.docops/ev.jsonl`.

## Codex-to-Kimi exchange

Both agents must see the same target repository.

- On the same machine, open the same checkout.
- On different machines, push/pull the request, delivery, audit, response, and
  closure documents together with the relevant code commits.
- Exchange is asynchronous; it does not wake the other agent automatically.

Use `templates/kimi-auditor.md` for the Kimi audit prompt and run:

```powershell
& $DOL exchange status <task-id>
& $DOL exchange validate <task-id>
```

## Execution policy

If PowerShell blocks `dol.ps1`, either use the signed/approved policy required
by your organization or run the `.cmd` launcher. For a one-process development
session:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dol.ps1 --help
```

Do not weaken machine-wide execution policy solely for this plugin.

## Validation

Run from the plugin repository:

```powershell
python -m compileall -q scripts hooks
python -m unittest discover -s tests -v
python scripts\dol.py --help
```

Windows-specific tests cover both launchers, workspace and plugin paths
containing spaces, PowerShell/Command Prompt hook signatures, native Kimi hook
output, and the ordinary exchange state machine.

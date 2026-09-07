from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dol  # noqa: E402


class HookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        dol.init_docops("hook-demo", self.workspace)
        self.env = dict(os.environ)
        self.env["PLUGIN_ROOT"] = str(ROOT)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_hook(
        self,
        name: str,
        payload: dict,
        *,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "hooks" / name)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env or self.env,
            check=False,
        )

    def test_hook_manifest_uses_current_event_shape(self) -> None:
        manifest = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest), {"hooks"})
        self.assertEqual(set(manifest["hooks"]), {"SessionStart", "PostToolUse", "Stop"})
        for groups in manifest["hooks"].values():
            for group in groups:
                self.assertIsInstance(group["hooks"], list)
                self.assertEqual(group["hooks"][0]["type"], "command")
                self.assertIn("${PLUGIN_ROOT}", group["hooks"][0]["command"])
                self.assertIn('python "', group["hooks"][0]["command"])
                self.assertNotIn("python3", group["hooks"][0]["command"])
        matcher = manifest["hooks"]["PostToolUse"][0]["matcher"]
        for tool_name in ["Bash", "PowerShell", "exec_command", "apply_patch"]:
            self.assertIn(tool_name, matcher)

    def test_session_start_returns_compact_context(self) -> None:
        result = self.run_hook("session_start.py", {"cwd": str(self.workspace), "hook_event_name": "SessionStart"})
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("DOCOPS STATE", context)
        self.assertIn("tp=hook-demo", context)
        self.assertIn("DOCOPS KB TAIL", context)

        docops = self.workspace / ".docops"
        legacy = "\n".join([
            (docops / "s.md").read_text(encoding="utf-8"),
            (docops / "c.yaml").read_text(encoding="utf-8"),
            (docops / "k.jsonl").read_text(encoding="utf-8"),
        ])
        self.assertLess(dol.estimated_tokens(context), dol.estimated_tokens(legacy))

    def test_post_tool_use_records_redacted_signature(self) -> None:
        before = len(dol.read_jsonl(self.workspace / ".docops" / "ev.jsonl"))
        result = self.run_hook("post_tool_use.py", {
            "cwd": str(self.workspace),
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "python3 secret-script.py --token super-secret"},
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        events = dol.read_jsonl(self.workspace / ".docops" / "ev.jsonl")
        self.assertEqual(len(events), before + 1)
        self.assertEqual(events[-1]["cmd"], "Bash:python3")
        self.assertNotIn("super-secret", json.dumps(events[-1]))

    def test_post_tool_use_recognizes_windows_shell_tools(self) -> None:
        cases = [
            (
                "PowerShell",
                "& 'C:\\Program Files\\Python311\\python.exe' .\\script.py --token secret",
                "PowerShell:python.exe",
            ),
            (
                "exec_command",
                "C:\\Python311\\python.exe .\\script.py --token secret",
                "exec_command:python.exe",
            ),
            (
                "cmd",
                'cmd.exe /c "C:\\Tools\\runner.cmd" --secret value',
                "cmd:runner.cmd",
            ),
        ]
        for tool_name, command, expected in cases:
            with self.subTest(tool_name=tool_name):
                result = self.run_hook("post_tool_use.py", {
                    "cwd": str(self.workspace),
                    "hook_event_name": "PostToolUse",
                    "tool_name": tool_name,
                    "tool_input": {"command": command},
                })
                self.assertEqual(result.returncode, 0, result.stderr)
                event = dol.read_jsonl(self.workspace / ".docops" / "ev.jsonl")[-1]
                self.assertEqual(event["cmd"], expected)
                self.assertNotIn("secret", json.dumps(event))

    def test_kimi_host_receives_plain_context_and_message(self) -> None:
        env = dict(self.env)
        env["KIMI_PLUGIN_ROOT"] = str(ROOT)
        start = self.run_hook(
            "session_start.py",
            {"cwd": str(self.workspace), "hook_event_name": "SessionStart"},
            env=env,
        )
        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertIn("DOCOPS STATE", start.stdout)
        self.assertFalse(start.stdout.lstrip().startswith("{"))

        dol.append_event("ch", self.workspace, st="s01", slug="kimi-unvalidated")
        stop = self.run_hook(
            "stop.py",
            {"cwd": str(self.workspace), "hook_event_name": "Stop"},
            env=env,
        )
        self.assertEqual(stop.returncode, 0, stop.stderr)
        self.assertIn("DocOps lint reminder", stop.stdout)
        self.assertFalse(stop.stdout.lstrip().startswith("{"))

    def test_stop_surfaces_lint_reminder_without_blocking(self) -> None:
        dol.append_event("ch", self.workspace, st="s01", slug="unvalidated")
        result = self.run_hook("stop.py", {"cwd": str(self.workspace), "hook_event_name": "Stop"})
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(output["continue"])
        self.assertIn("DocOps lint reminder", output["systemMessage"])

    def test_stop_auto_compacts_only_when_opted_in(self) -> None:
        projection = self.workspace / ".docops/projection.yaml"
        projection.write_text(
            projection.read_text(encoding="utf-8").replace(
                "auto_compact_current: false", "auto_compact_current: true"
            ),
            encoding="utf-8",
        )
        current = self.workspace / "docs/current"
        current.mkdir(parents=True)
        (current / "status.md").write_text("# status\n" + "long detail\n" * 240, encoding="utf-8")
        (current / "next_steps.md").write_text("# next\n" + "long detail\n" * 240, encoding="utf-8")

        result = self.run_hook("stop.py", {"cwd": str(self.workspace), "hook_event_name": "Stop"})
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertIn("DocOps compacted 2 current document(s)", output["systemMessage"])
        self.assertEqual(dol.compact_budget_issues(self.workspace), [])
        self.assertEqual(len(dol.read_jsonl(self.workspace / ".docops/compact.jsonl")), 2)

    def test_hooks_are_noops_without_docops(self) -> None:
        empty = self.workspace / "empty"
        empty.mkdir()
        for name in ["session_start.py", "post_tool_use.py", "stop.py"]:
            with self.subTest(name=name):
                result = self.run_hook(name, {"cwd": str(empty)})
                self.assertEqual(result.returncode, 0, result.stderr)

        kimi_env = dict(self.env)
        kimi_env["KIMI_PLUGIN_ROOT"] = str(ROOT)
        result = self.run_hook("session_start.py", {"cwd": str(empty)}, env=kimi_env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()

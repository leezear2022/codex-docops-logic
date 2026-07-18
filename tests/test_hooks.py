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

    def run_hook(self, name: str, payload: dict) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "hooks" / name)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=self.env,
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

    def test_session_start_returns_compact_context(self) -> None:
        result = self.run_hook("session_start.py", {"cwd": str(self.workspace), "hook_event_name": "SessionStart"})
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("DOCOPS STATE", context)
        self.assertIn("tp: hook-demo", context)
        self.assertIn("DOCOPS KB TAIL", context)

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

    def test_stop_surfaces_lint_reminder_without_blocking(self) -> None:
        dol.append_event("ch", self.workspace, st="s01", slug="unvalidated")
        result = self.run_hook("stop.py", {"cwd": str(self.workspace), "hook_event_name": "Stop"})
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(output["continue"])
        self.assertIn("DocOps lint reminder", output["systemMessage"])

    def test_hooks_are_noops_without_docops(self) -> None:
        empty = self.workspace / "empty"
        empty.mkdir()
        for name in ["session_start.py", "post_tool_use.py", "stop.py"]:
            with self.subTest(name=name):
                result = self.run_hook(name, {"cwd": str(empty)})
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOL = ROOT / "scripts" / "dol.py"


class WindowsCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / "workspace with spaces"
        self.workspace.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(DOL), *args],
            cwd=self.workspace,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_cli_handles_workspace_paths_with_spaces(self) -> None:
        init = self.run_cli("init", "windows-demo")
        self.assertEqual(init.returncode, 0, init.stderr)
        status = self.run_cli("status")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("tp: windows-demo", status.stdout)

        create = self.run_cli(
            "exchange",
            "new",
            "--id",
            "windows-exchange",
            "--title",
            "Windows path test",
            "--from",
            "user",
            "--to",
            "codex",
        )
        self.assertEqual(create.returncode, 0, create.stderr)
        state_path = self.workspace / ".docops" / "exchange" / "windows-exchange" / "state.json"
        self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))["status"], "requested")

    @unittest.skipUnless(os.name == "nt", "Windows launcher smoke tests")
    def test_cmd_launcher_works(self) -> None:
        launcher_dir = Path(self.temp.name) / "plugin root with spaces" / "scripts"
        launcher_dir.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts" / "dol.cmd", launcher_dir / "dol.cmd")
        shutil.copy2(DOL, launcher_dir / "dol.py")
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", str(launcher_dir / "dol.cmd"), "--help"],
            cwd=self.workspace,
            text=True,
            capture_output=True,
            env={**os.environ, "DOCOPS_PYTHON": sys.executable},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DocOps Logic Phase 1 CLI", result.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows launcher smoke tests")
    def test_powershell_launcher_works(self) -> None:
        launcher_dir = Path(self.temp.name) / "plugin root with spaces" / "scripts"
        launcher_dir.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts" / "dol.ps1", launcher_dir / "dol.ps1")
        shutil.copy2(DOL, launcher_dir / "dol.py")
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(launcher_dir / "dol.ps1"),
                "--help",
            ],
            cwd=self.workspace,
            text=True,
            capture_output=True,
            env={**os.environ, "DOCOPS_PYTHON": sys.executable},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DocOps Logic Phase 1 CLI", result.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows launcher smoke tests")
    def test_launchers_discover_python_on_path(self) -> None:
        launcher_dir = Path(self.temp.name) / "plugin root with spaces" / "scripts"
        launcher_dir.mkdir(parents=True)
        for filename in ("dol.cmd", "dol.ps1", "dol.py"):
            source = DOL if filename == "dol.py" else ROOT / "scripts" / filename
            shutil.copy2(source, launcher_dir / filename)

        env = dict(os.environ)
        env.pop("DOCOPS_PYTHON", None)
        env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), env.get("PATH", "")])
        commands = [
            ["cmd.exe", "/d", "/c", str(launcher_dir / "dol.cmd"), "--help"],
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(launcher_dir / "dol.ps1"),
                "--help",
            ],
        ]
        for command in commands:
            with self.subTest(command=command[0]):
                result = subprocess.run(
                    command,
                    cwd=self.workspace,
                    text=True,
                    capture_output=True,
                    env=env,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("DocOps Logic Phase 1 CLI", result.stdout)


if __name__ == "__main__":
    unittest.main()

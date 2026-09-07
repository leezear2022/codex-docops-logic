from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.kimi_manifest = json.loads((ROOT / "kimi.plugin.json").read_text(encoding="utf-8"))

    def test_manifest_required_fields_and_version(self) -> None:
        self.assertEqual(self.manifest["name"], "docops-logic")
        self.assertRegex(
            self.manifest["version"],
            r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$",
        )
        self.assertTrue(self.manifest["description"])
        self.assertTrue(self.manifest["author"]["name"])

    def test_manifest_component_paths_and_interface(self) -> None:
        self.assertTrue((ROOT / self.manifest["skills"]).is_dir())
        self.assertNotIn("hooks", self.manifest)
        self.assertTrue((ROOT / "hooks" / "hooks.json").is_file())
        interface = self.manifest["interface"]
        for key in ["displayName", "shortDescription", "longDescription", "developerName", "category"]:
            self.assertTrue(interface[key])
        self.assertLessEqual(len(interface["defaultPrompt"]), 3)
        self.assertTrue(all(len(prompt) <= 128 for prompt in interface["defaultPrompt"]))

    def test_skill_names_are_unique_and_complete(self) -> None:
        names: set[str] = set()
        skill_files = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertTrue(skill_files)
        for path in skill_files:
            text = path.read_text(encoding="utf-8")
            match = re.match(r"---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---", text)
            self.assertIsNotNone(match, path)
            assert match is not None
            name, description = match.groups()
            self.assertTrue(name.startswith("docops-"))
            self.assertTrue(description)
            self.assertNotIn(name, names)
            names.add(name)

    def test_public_metadata_targets_exist_in_checkout(self) -> None:
        self.assertTrue((ROOT / "README.md").is_file())
        self.assertTrue((ROOT / "LICENSE").is_file())
        self.assertTrue((ROOT / "PRIVACY.md").is_file())

    def test_kimi_manifest_reuses_skills_and_has_cross_platform_hooks(self) -> None:
        self.assertEqual(self.kimi_manifest["name"], "docops-logic")
        self.assertEqual(
            self.kimi_manifest["version"],
            self.manifest["version"].split("+", 1)[0],
        )
        self.assertTrue((ROOT / self.kimi_manifest["skills"]).is_dir())
        self.assertEqual(
            {hook["event"] for hook in self.kimi_manifest["hooks"]},
            {"SessionStart", "PostToolUse", "Stop"},
        )
        for hook in self.kimi_manifest["hooks"]:
            self.assertTrue(hook["command"].startswith('python "'))
            self.assertNotIn("python3", hook["command"])
            self.assertGreaterEqual(hook["timeout"], 1)

    def test_windows_launchers_are_shipped(self) -> None:
        self.assertTrue((ROOT / "scripts" / "dol.ps1").is_file())
        self.assertTrue((ROOT / "scripts" / "dol.cmd").is_file())


if __name__ == "__main__":
    unittest.main()

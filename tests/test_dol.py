from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dol  # noqa: E402


@contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class DocOpsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def init(self, topic: str = "demo") -> dict:
        return dol.init_docops(topic, self.root)

    def test_init_is_non_destructive_and_idempotent(self) -> None:
        first = self.init()
        state_before = (self.root / ".docops" / "s.md").read_text(encoding="utf-8")
        second = self.init("different")
        state_after = (self.root / ".docops" / "s.md").read_text(encoding="utf-8")

        self.assertEqual(first["agents"], "created")
        self.assertEqual(second["agents"], "kept")
        self.assertEqual(second["created"], [])
        self.assertEqual(state_before, state_after)
        self.assertEqual(len(dol.read_jsonl(self.root / ".docops" / "ev.jsonl")), 2)
        self.assertTrue(dol.validate_workspace(self.root)["ok"])

    def test_change_requires_later_validation(self) -> None:
        self.init()
        dol.append_event("ch", self.root, st="s01", slug="parser-fix")
        lint = dol.run_lint(self.root)
        self.assertFalse(lint["ok"])
        self.assertIn("R001", lint["rule"])

        dol.append_event("va", self.root, st="s01", result="pass")
        self.assertTrue(dol.run_lint(self.root)["ok"])

    def test_learning_and_append_only_promotion(self) -> None:
        self.init()
        for _ in range(2):
            dol.append_event("va", self.root, st="s01", result="fail")
        result = dol.run_learn(self.root)
        self.assertEqual(len(result["made"]), 1)
        card_id = result["made"][0]
        before = len(dol.read_jsonl(self.root / ".docops" / "k.jsonl"))

        promoted = dol.run_promote(card_id, "acc", self.root)
        after = len(dol.read_jsonl(self.root / ".docops" / "k.jsonl"))
        self.assertTrue(promoted["ok"])
        self.assertEqual(after, before + 1)
        self.assertEqual(dol.latest_cards(self.root)[card_id]["st"], "acc")

    def test_validate_reports_corrupt_and_invalid_rows(self) -> None:
        self.init()
        with (self.root / ".docops" / "ev.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("not-json\n")
        result = dol.validate_workspace(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(any(item["path"] == ".docops/ev.jsonl" for item in result["errors"]))

    def test_document_filename_is_not_redundant(self) -> None:
        self.assertEqual(
            dol.doc_filename("demo", "demo-plan", "plan", "2026-07-18"),
            "DEMO_PLAN_2026_07_18.md",
        )
        self.assertEqual(
            dol.doc_filename("解析器", "恢复-plan", "plan", "2026-07-18"),
            "解析器_恢复_PLAN_2026_07_18.md",
        )

    def test_doc_refuses_overwrite_without_force(self) -> None:
        self.init()
        with working_directory(self.root):
            parser = dol.build_parser()
            args = parser.parse_args(["doc", "new", "--kind", "plan", "--slug", "demo-plan", "--date", "2026-07-18"])
            self.assertEqual(dol.cmd_doc_new(args), 0)
            self.assertEqual(dol.cmd_doc_new(args), 1)
            args.force = True
            self.assertEqual(dol.cmd_doc_new(args), 0)

    def test_stage_roadmap_and_date_arguments_are_strict(self) -> None:
        self.assertEqual(dol.stage_arg("s03"), "s03")
        self.assertEqual(dol.roadmap_arg("v02"), "v02")
        self.assertEqual(dol.date_arg("2026-07-18"), "2026-07-18")
        for function, bad in [(dol.stage_arg, "3"), (dol.roadmap_arg, "next"), (dol.date_arg, "2026-02-30")]:
            with self.assertRaises(argparse.ArgumentTypeError):
                function(bad)

    def test_event_schema_covers_every_emitted_event_type(self) -> None:
        schema = json.loads((ROOT / "schemas" / "ev.schema.json").read_text(encoding="utf-8"))
        schema_types = set(schema["properties"]["ty"]["enum"])
        self.assertEqual(schema_types, dol.EVENT_TYPES)

    def test_all_json_contracts_are_valid_json(self) -> None:
        for path in sorted((ROOT / "schemas").glob("*.json")):
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

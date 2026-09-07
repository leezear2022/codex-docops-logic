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

    def write_long_current_docs(self) -> tuple[bytes, bytes]:
        current = self.root / "docs" / "current"
        current.mkdir(parents=True)
        status = ("# Status\r\n\r\n" + "historical status detail\r\n" * 240).encode("utf-8")
        next_steps = ("# Next\r\n\r\n" + "historical next detail\r\n" * 220).encode("utf-8")
        (current / "status.md").write_bytes(status)
        (current / "next_steps.md").write_bytes(next_steps)
        return status, next_steps

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

    def test_compact_dry_run_is_read_only_and_reduces_tokens(self) -> None:
        self.init()
        originals = self.write_long_current_docs()
        result = dol.run_compact(self.root)

        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["changed"], 0)
        self.assertEqual(result["needs_compaction"], 2)
        self.assertGreater(result["estimated_token_reduction"], 0)
        self.assertEqual((self.root / "docs/current/status.md").read_bytes(), originals[0])
        self.assertFalse((self.root / ".docops/compact.jsonl").exists())

    def test_compact_apply_preserves_exact_history_and_is_idempotent(self) -> None:
        self.init()
        dol.update_state(self.root, next="Run the focused regression.", blk="None")
        originals = self.write_long_current_docs()
        result = dol.run_compact(self.root, apply=True)

        self.assertEqual(result["changed"], 2)
        rows = dol.read_jsonl(self.root / ".docops/compact.jsonl")
        self.assertEqual(len(rows), 2)
        for row, original in zip(rows, originals):
            snapshot = self.root / row["snapshot"]
            self.assertEqual(snapshot.read_bytes(), original)
            self.assertEqual(dol.sha256_bytes(original), row["sha256"])
        index = (self.root / "docs/archive/current_history_index.md").read_text(encoding="utf-8")
        self.assertIn("Current Projection History", index)
        self.assertIn("status.", index)
        self.assertEqual(dol.compact_budget_issues(self.root), [])
        second = dol.run_compact(self.root, apply=True)
        self.assertEqual(second["changed"], 0)
        self.assertEqual(len(dol.read_jsonl(self.root / ".docops/compact.jsonl")), 2)

    def test_compact_rejects_paths_outside_repository(self) -> None:
        self.init()
        with self.assertRaises(ValueError):
            dol.run_compact(self.root, status_path="../outside.md")

    def test_lint_enforces_current_document_budget(self) -> None:
        self.init()
        self.write_long_current_docs()
        result = dol.run_lint(self.root)
        self.assertIn("R008", result["rule"])
        dol.run_compact(self.root, apply=True)
        self.assertNotIn("R008", dol.run_lint(self.root)["rule"])

    def test_handoff_projects_state_and_read_order(self) -> None:
        self.init()
        dol.update_state(self.root, next="Run E2 comparison", blk="Missing resolver")
        with working_directory(self.root):
            args = dol.build_parser().parse_args(["hf", "upd"])
            self.assertEqual(dol.cmd_hf_upd(args), 0)
        handoff = (self.root / ".docops/handoff.md").read_text(encoding="utf-8")
        self.assertIn("next: Run E2 comparison", handoff)
        self.assertIn("blk: Missing resolver", handoff)
        self.assertIn("- docs/current/status.md", handoff)


if __name__ == "__main__":
    unittest.main()

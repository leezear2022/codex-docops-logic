from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
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


class ExchangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.task = "rpc-7004"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *argv: str) -> tuple[int, dict]:
        buf = io.StringIO()
        with working_directory(self.root), redirect_stdout(buf):
            rc = dol.main(list(argv))
        out = buf.getvalue().strip()
        return rc, json.loads(out) if out.startswith("{") else {"raw": out}

    def task_dir(self, task: str | None = None) -> Path:
        return self.root / ".docops" / "exchange" / (task or self.task)

    def state(self, task: str | None = None) -> dict:
        return json.loads((self.task_dir(task) / "state.json").read_text(encoding="utf-8"))

    def sidecar(self, doc_id: str) -> dict:
        path = dol.doc_sidecar(self.task_dir(doc_id.split("/")[0]), doc_id, "json")
        assert path is not None
        return json.loads(path.read_text(encoding="utf-8"))

    def new_task(self, **extra: str) -> tuple[int, dict]:
        argv = [
            "exchange", "new",
            "--id", self.task,
            "--title", extra.get("title", "Fix RPC 7004 timeout"),
            "--from", "user",
            "--to", "codex",
            "--request", extra.get("request", "Retry idempotent calls on timeout."),
            "--acc", "timeout retried",
            "--base-commit", "abc123",
        ]
        return self.cli(*argv)

    def deliver(self, *extra: str) -> tuple[int, dict]:
        return self.cli(
            "exchange", "deliver", self.task,
            "--result-commit", "def456",
            "--files", "src/rpc.py,tests/test_rpc.py",
            "--claims", "added bounded retry with backoff",
            "--va", "python3 -m unittest discover -s tests=pass",
            *extra,
        )

    def audit_round_one(self, verdict: str = "approve", *extra: str) -> tuple[int, dict]:
        rc, _ = self.cli("exchange", "audit-start", self.task)
        assert rc == 0
        argv = ["exchange", "audit-submit", self.task, "--verdict", verdict, *extra]
        return self.cli(*argv)

    def test_happy_path_to_closed(self) -> None:
        self.assertEqual(self.new_task()[0], 0)
        self.assertEqual(self.cli("exchange", "start", self.task)[0], 0)
        rc, out = self.deliver()
        self.assertEqual(rc, 0)
        self.assertEqual(out["round"], 1)
        rc, out = self.audit_round_one("approve")
        self.assertEqual(rc, 0)
        self.assertEqual(out["status"], "approved")
        rc, out = self.cli("exchange", "close", self.task, "--note", "shipped")
        self.assertEqual(rc, 0)
        self.assertEqual(out["resolution"], "approved")

        state = self.state()
        self.assertEqual(state["status"], "closed")
        self.assertEqual(state["approved_round"], 1)
        for doc in ["request", "r001/delivery", "r001/audit", "closure"]:
            base = self.task_dir() / doc
            directory, name = base.parent, base.name
            self.assertTrue((directory / f"{name}.json").is_file(), doc)
            self.assertTrue((directory / f"{name}.md").is_file(), doc)
        rc, out = self.cli("exchange", "validate", self.task)
        self.assertEqual(rc, 0, out)

    def test_changes_requested_then_next_round_approved(self) -> None:
        self.new_task()
        self.cli("exchange", "start", self.task)
        self.deliver()
        rc, _ = self.audit_round_one(
            "request_changes",
            "--finding", "major|src/rpc.py:88|retry unbounded with input flood|cap retries at 3",
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self.state()["status"], "changes_requested")

        rc, _ = self.cli("exchange", "respond", self.task, "--finding", "F1",
                         "--action", "accept", "--note", "capped at 3 in def789")
        self.assertEqual(rc, 0)
        self.assertEqual(self.state()["status"], "changes_requested")

        audit_before = (self.task_dir() / "r001" / "audit.json").read_text(encoding="utf-8")
        rc, out = self.cli("exchange", "deliver", self.task,
                           "--result-commit", "def789",
                           "--files", "src/rpc.py",
                           "--claims", "cap retries at 3",
                           "--va", "python3 -m unittest discover -s tests=pass")
        self.assertEqual(rc, 0)
        self.assertEqual(out["round"], 2)
        self.assertEqual(self.state()["status"], "ready_for_audit")
        self.assertEqual(
            (self.task_dir() / "r001" / "audit.json").read_text(encoding="utf-8"),
            audit_before,
            "round 1 documents must never be overwritten",
        )

        self.cli("exchange", "audit-start", self.task)
        rc, out = self.cli("exchange", "audit-submit", self.task, "--verdict", "approve")
        self.assertEqual(rc, 0)
        self.assertEqual(self.state()["approved_round"], 2)
        rc, out = self.cli("exchange", "validate")
        self.assertEqual(rc, 0, out)

    def test_disputed_flow(self) -> None:
        self.new_task()
        self.cli("exchange", "start", self.task)
        self.deliver()
        self.audit_round_one(
            "request_changes",
            "--finding", "major|src/rpc.py:88|unbounded retry|cap retries",
            "--finding", "minor|src/rpc.py:90|log leaks url|redact query",
        )
        rc, out = self.cli("exchange", "respond", self.task, "--finding", "F1",
                           "--action", "dispute",
                           "--note", "bounded by caller deadline, see rpc.py:40")
        self.assertEqual(rc, 0)
        self.assertEqual(self.state()["status"], "disputed")
        rc, _ = self.cli("exchange", "respond", self.task, "--finding", "F2",
                         "--action", "accept", "--note", "redacted in def999")
        self.assertEqual(rc, 0)
        self.assertEqual(self.state()["status"], "disputed")

        rc, out = self.cli("exchange", "deliver", self.task,
                           "--result-commit", "def999",
                           "--files", "src/rpc.py",
                           "--claims", "redact query; dispute F1 with deadline evidence",
                           "--va", "python3 -m unittest discover -s tests=pass")
        self.assertEqual(rc, 0)
        self.assertEqual(out["round"], 2)
        self.cli("exchange", "audit-start", self.task)
        rc, _ = self.cli("exchange", "audit-submit", self.task, "--verdict", "approve")
        self.assertEqual(rc, 0)
        response = self.sidecar(f"{self.task}/r001/response")
        self.assertEqual(len(response["responses"]), 2)
        self.assertEqual(response["responses"][0]["action"], "dispute")

    def test_illegal_transitions_are_rejected(self) -> None:
        self.new_task()
        rc, out = self.cli("exchange", "deliver", self.task)
        self.assertEqual(rc, 1)
        self.assertIn("illegal transition", out["why"])
        rc, _ = self.cli("exchange", "close", self.task)
        self.assertEqual(rc, 0)
        rc, out = self.cli("exchange", "start", self.task)
        self.assertEqual(rc, 1)
        self.assertIn("terminal", str(out["fix"]))

    def test_duplicate_task_and_locked_task(self) -> None:
        self.assertEqual(self.new_task()[0], 0)
        rc, out = self.new_task()
        self.assertEqual(rc, 1)
        self.assertIn("already exists", out["why"])
        (self.task_dir() / ".lock").write_text("other writer", encoding="utf-8")
        rc, out = self.cli("exchange", "start", self.task)
        self.assertEqual(rc, 1)
        self.assertIn("locked", out["why"])
        (self.task_dir() / ".lock").unlink()
        self.assertEqual(self.cli("exchange", "start", self.task)[0], 0)

    def test_path_traversal_task_ids_rejected(self) -> None:
        for bad in ["../evil", "a/b", "..", ".hidden", "a b"]:
            with self.subTest(bad=bad), working_directory(self.root):
                with self.assertRaises(SystemExit):
                    dol.main(["exchange", "new", "--id", bad, "--title", "t",
                              "--from", "u", "--to", "c"])
        self.assertFalse((self.root / ".docops" / "exchange").exists() and
                         any((self.root / ".docops" / "exchange").iterdir()))

    def test_audit_requires_delivery(self) -> None:
        self.new_task()
        self.cli("exchange", "start", self.task)
        rc, out = self.cli("exchange", "audit-start", self.task)
        self.assertEqual(rc, 1)
        self.assertIn("no delivery", out["why"])
        rc, out = self.cli("exchange", "audit-submit", self.task, "--verdict", "approve")
        self.assertEqual(rc, 1)

    def test_approve_requires_validation_evidence(self) -> None:
        self.new_task()
        self.cli("exchange", "start", self.task)
        self.cli("exchange", "deliver", self.task, "--claims", "no evidence recorded")
        self.cli("exchange", "audit-start", self.task)
        rc, out = self.cli("exchange", "audit-submit", self.task, "--verdict", "approve")
        self.assertEqual(rc, 1)
        self.assertIn("validation", str(out["miss"]))
        rc, _ = self.cli("exchange", "audit-submit", self.task, "--verdict", "request_changes",
                         "--finding", "blocker|delivery|no validation evidence|record --va results")
        self.assertEqual(rc, 0)

    def test_request_changes_requires_finding(self) -> None:
        self.new_task()
        self.cli("exchange", "start", self.task)
        self.deliver()
        self.cli("exchange", "audit-start", self.task)
        rc, out = self.cli("exchange", "audit-submit", self.task, "--verdict", "request_changes")
        self.assertEqual(rc, 1)
        self.assertIn("finding", out["why"])

    def test_respond_rejects_unknown_finding(self) -> None:
        self.new_task()
        self.cli("exchange", "start", self.task)
        self.deliver()
        self.audit_round_one("request_changes",
                             "--finding", "minor|a.py:1|evidence|advice")
        rc, out = self.cli("exchange", "respond", self.task, "--finding", "F9",
                           "--action", "accept", "--note", "n/a")
        self.assertEqual(rc, 1)
        self.assertIn("unknown finding", out["why"])

    def test_validate_detects_tampering(self) -> None:
        self.new_task()
        self.cli("exchange", "start", self.task)
        self.deliver()
        self.audit_round_one("approve")
        self.cli("exchange", "close", self.task)
        rc, out = self.cli("exchange", "validate", "--all")
        self.assertEqual(rc, 0, out)

        (self.task_dir() / "r001" / "delivery.json").unlink()
        rc, out = self.cli("exchange", "validate", self.task)
        self.assertEqual(rc, 1)
        self.assertTrue(any("delivery" in err["path"] for err in out["errors"]))

    def test_schema_matches_validator_contract(self) -> None:
        schema = json.loads((ROOT / "schemas" / "exchange.schema.json").read_text(encoding="utf-8"))
        defs = schema["$defs"]
        for doc_type, required in dol.EXCHANGE_REQUIRED.items():
            with self.subTest(doc_type=doc_type):
                self.assertEqual(set(defs[doc_type]["required"]), set(required))
        self.assertEqual(set(defs["state"]["properties"]["status"]["enum"]), set(dol.EXCHANGE_STATUSES))
        self.assertEqual(set(defs["state"]["required"]), set(dol.EXCHANGE_STATE_REQUIRED))

    def test_chinese_title_and_body(self) -> None:
        rc, _ = self.cli(
            "exchange", "new",
            "--id", "parser-fix",
            "--title", "修复解析器超时问题",
            "--from", "用户",
            "--to", "codex",
            "--request", "对幂等请求增加有界重试,避免雪崩。",
            "--acc", "超时场景可重试",
            "--acc", "不改变现有成功路径",
        )
        self.assertEqual(rc, 0)
        self.cli("exchange", "start", "parser-fix")
        rc, _ = self.cli("exchange", "deliver", "parser-fix",
                         "--files", "src/解析器.py",
                         "--claims", "实现了指数退避重试",
                         "--va", "python3 -m unittest discover -s tests=pass")
        self.assertEqual(rc, 0)
        request = self.sidecar("parser-fix/request")
        self.assertEqual(request["title"], "修复解析器超时问题")
        self.assertIn("幂等", request["request"])
        delivery = self.sidecar("parser-fix/r001/delivery")
        self.assertIn("指数退避", delivery["claims"][0])
        md = (self.task_dir("parser-fix") / "request.md").read_text(encoding="utf-8")
        self.assertIn("修复解析器超时问题", md)
        rc, out = self.cli("exchange", "validate", "parser-fix")
        self.assertEqual(rc, 0, out)

    def test_status_lists_tasks(self) -> None:
        self.new_task()
        rc, out = self.cli("exchange", "status")
        self.assertEqual(rc, 0)
        self.assertEqual(out["tasks"][0]["task"], self.task)
        self.assertEqual(out["tasks"][0]["status"], "requested")
        rc, out = self.cli("exchange", "status", self.task)
        self.assertEqual(rc, 0)
        self.assertEqual(out["round"], 0)


if __name__ == "__main__":
    unittest.main()

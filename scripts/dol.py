#!/usr/bin/env python3
"""DocOps Logic Phase 1 CLI.

Python standard library only. The script writes only below the current working
directory and keeps JSONL records append-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DOCOPS = ".docops"
STATE_ORDER = [
    "tp",
    "rm",
    "st",
    "stat",
    "health",
    "pr",
    "last_ch",
    "last_va",
    "blk",
    "next",
    "updated",
]
CARD_TYPES = {"R", "C", "L", "X", "D", "E", "S", "P", "A", "Q"}
VA_RESULTS = {"pass", "fail", "mix", "def"}
SOLVE_MODES = {"check", "repair", "plan", "conflict"}
DOC_KINDS = {"plan", "changelog"}
EVENT_TYPES = {"init", "tp", "rm", "st", "pr", "ss", "ch", "va", "rk", "dc", "hf", "ls", "kb", "learn", "prom", "cmd", "doc"}
STATE_STATUSES = {"active", "blocked", "done", "paused"}
HEALTH_STATUSES = {"green", "yellow", "red"}
CARD_STATUSES = {"cand", "acc", "ret", "blk", "pass", "fail", "mix", "def"}
STAGE_RE = re.compile(r"^s[0-9]{2}$")
ROADMAP_RE = re.compile(r"^v[0-9]{2}$")
EVENT_ID_RE = re.compile(r"^ev[0-9]{6}$")
CARD_ID_RE = re.compile(r"^[RCLXDESPAQ][0-9]{3}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return Path.cwd().resolve()


def docops_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / DOCOPS


def compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def print_json(data: Any) -> None:
    print(compact_json(data))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)


def write_if_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False
    write_text(path, text)
    return True


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(compact_json(obj) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def read_state(root: Path | None = None) -> dict[str, str]:
    path = docops_dir(root) / "s.md"
    state: dict[str, str] = {}
    if not path.exists():
        return state
    for line in read_text(path).splitlines():
        if ":" not in line or line.startswith("#"):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            state[key] = value.strip()
    return state


def render_state(state: dict[str, str]) -> str:
    values = {
        "tp": state.get("tp", ""),
        "rm": state.get("rm", "v01"),
        "st": state.get("st", "s01"),
        "stat": state.get("stat", "active"),
        "health": state.get("health", "green"),
        "pr": state.get("pr", "[]"),
        "last_ch": state.get("last_ch", ""),
        "last_va": state.get("last_va", ""),
        "blk": state.get("blk", ""),
        "next": state.get("next", ""),
        "updated": state.get("updated", now_iso()),
    }
    lines = ["# s", ""]
    for key in STATE_ORDER:
        value = values.get(key, "")
        lines.append(f"{key}: {value}".rstrip())
    return "\n".join(lines) + "\n"


def write_state(state: dict[str, str], root: Path | None = None) -> None:
    write_text(docops_dir(root) / "s.md", render_state(state))


def update_state(root: Path | None = None, **fields: Any) -> dict[str, str]:
    state = read_state(root)
    for key, value in fields.items():
        if value is None:
            continue
        state[key] = str(value)
    state["updated"] = now_iso()
    write_state(state, root)
    return state


def event_path(root: Path | None = None) -> Path:
    return docops_dir(root) / "ev.jsonl"


def card_path(root: Path | None = None) -> Path:
    return docops_dir(root) / "k.jsonl"


def append_event(ty: str, root: Path | None = None, **fields: Any) -> dict[str, Any]:
    events = read_jsonl(event_path(root))
    obj: dict[str, Any] = {
        "id": f"ev{len(events) + 1:06d}",
        "ts": now_iso(),
        "ty": ty,
    }
    obj.update({k: v for k, v in fields.items() if v is not None and v != ""})
    append_jsonl(event_path(root), obj)
    return obj


def load_template(name: str) -> str:
    return read_text(plugin_root() / "templates" / name)


def render_template(name: str, **values: str) -> str:
    text = load_template(name)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def default_cards() -> list[dict[str, Any]]:
    return [
        {"id": "R001", "ty": "R", "k": "fix.needs.va", "sc": "repo", "if": "claim.fix", "req": "va.pass|va.def", "sev": "b", "st": "acc"},
        {"id": "C001", "ty": "C", "k": "readme.static", "sc": "repo", "v": "README is nav only", "st": "acc"},
        {"id": "L001", "ty": "L", "k": "bench.noise", "sc": "repo", "if": "claim.perf", "req": "va.bench.runs>=3", "conf": 0.8, "st": "cand"},
        {"id": "X001", "ty": "X", "k": "unit.not.perf", "sc": "repo", "if": "claim.perf", "bad": "unit.only", "req": "bench", "st": "acc"},
        {"id": "D001", "ty": "D", "k": "fixture.fail", "sc": "repo", "seq": "env->fixture->parser", "st": "cand"},
        {"id": "P001", "ty": "P", "k": "token.mode", "sc": "user", "v": "short", "cost": "long_doc:+2", "st": "acc"},
        {"id": "C002", "ty": "C", "k": "doc.separate.microdocs", "sc": "repo", "v": "small plans and small changelogs require standalone docs", "st": "acc"},
    ]


def default_c_yaml() -> str:
    return """v: 1

rule:
  - id: R001
    if: claim.fix
    req: va.pass|va.def
    sev: b

  - id: R002
    if: claim.perf
    req: va.bench.runs>=3
    sev: b

  - id: R003
    if: rm.bump
    req: rm.hist
    sev: b

  - id: R004
    if: st.close
    req: va.final&ls
    sev: b

  - id: R005
    if: pause.days>1
    req: hf
    sev: w

  - id: R006
    if: fail.same>=2
    make: L.cand
    sev: s

  - id: R007
    if: cmd.same>=3
    make: S.cand
    sev: s
"""


def default_p_yaml() -> str:
    return """u:
  lang: zh
  tok: low
  style: direct
  prefer:
    - tree
    - table
    - cp_ready
  avoid:
    - generic
    - long_readme
    - duplicate_docs
"""


def ensure_agents(root: Path) -> str:
    path = root / "AGENTS.md"
    if not path.exists():
        write_text(path, load_template("AGENTS.md"))
        return "created"
    text = read_text(path)
    if "DocOps Logic" in text or ".docops/s.md" in text:
        return "kept"
    section = """

## DocOps Logic

Read first:
- .docops/s.md
- .docops/c.yaml
- last 20 lines of .docops/k.jsonl

Before handoff:
- dol lint --soft
"""
    append_text(path, section)
    return "appended"


def init_docops(topic: str, root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    d = docops_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    state = {
        "tp": topic,
        "rm": "v01",
        "st": "s01",
        "stat": "active",
        "health": "green",
        "pr": "[]",
        "last_ch": "",
        "last_va": "",
        "blk": "",
        "next": "",
        "updated": now_iso(),
    }
    if write_if_missing(d / "s.md", render_state(state)):
        created.append(".docops/s.md")
    if not (d / "k.jsonl").exists():
        for card in default_cards():
            append_jsonl(d / "k.jsonl", card)
        created.append(".docops/k.jsonl")
    if write_if_missing(d / "c.yaml", default_c_yaml()):
        created.append(".docops/c.yaml")
    if write_if_missing(d / "p.yaml", default_p_yaml()):
        created.append(".docops/p.yaml")
    if write_if_missing(d / "ev.jsonl", ""):
        created.append(".docops/ev.jsonl")
    agents = ensure_agents(root)
    event = append_event("init", root, tp=topic)
    return {"ok": True, "created": created, "agents": agents, "event": event["id"]}


def parse_rules(root: Path | None = None) -> dict[str, dict[str, str]]:
    path = docops_dir(root) / "c.yaml"
    rules: dict[str, dict[str, str]] = {}
    if not path.exists():
        return rules
    current: dict[str, str] | None = None
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- id:"):
            rid = line.split(":", 1)[1].strip()
            current = {"id": rid}
            rules[rid] = current
            continue
        if current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.strip()] = value.strip().strip('"').strip("'")
    return rules


def long_docs_enabled(root: Path | None = None) -> bool:
    if os.environ.get("DOCOPS_LONG_DOCS") in {"1", "true", "yes"}:
        return True
    path = docops_dir(root) / "p.yaml"
    if not path.exists():
        return False
    for line in read_text(path).splitlines():
        if line.strip().lower() == "long_docs: true":
            return True
    return False


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w]+", "-", value, flags=re.UNICODE).replace("_", "-")
    return value.strip("-") or "item"


def current_topic(root: Path | None = None) -> str:
    return read_state(root).get("tp", "topic") or "topic"


def maybe_write_long_doc(kind: str, event: dict[str, Any], root: Path | None = None) -> str | None:
    if not long_docs_enabled(root):
        return None
    root = root or repo_root()
    topic = slugify(current_topic(root))
    mapping = {
        "ch": ("execution/changes", "change.md"),
        "va": ("evidence/validation", "validation.md"),
        "st": ("control/stages", "stage.md"),
        "rm": ("control/roadmap/versions", "roadmap.md"),
    }
    if kind not in mapping:
        return None
    subdir, template = mapping[kind]
    name = event.get("slug") or event.get("st") or event.get("rm") or event["id"]
    path = root / "docs" / "workstreams" / topic / subdir / f"{slugify(str(name))}.md"
    text = render_template(
        template,
        id=str(event["id"]),
        topic=current_topic(root),
        stage=str(event.get("st", "")),
        roadmap=str(event.get("rm", "")),
        result=str(event.get("result", "")),
        slug=str(event.get("slug", "")),
        updated=now_iso(),
    )
    write_if_missing(path, text)
    return str(path.relative_to(root))


def upper_slug(value: str) -> str:
    slug = slugify(value)
    return slug.replace("-", "_").upper()


def doc_filename(topic: str, slug: str, kind: str, doc_date: str) -> str:
    suffix = "PLAN" if kind == "plan" else "CHANGELOG"
    topic_slug = slugify(topic)
    item_slug = slugify(slug)
    if item_slug == topic_slug:
        item_slug = ""
    elif item_slug.startswith(topic_slug + "-"):
        item_slug = item_slug[len(topic_slug) + 1:]
    kind_slug = slugify(kind)
    if item_slug == kind_slug:
        item_slug = ""
    elif item_slug.endswith("-" + kind_slug):
        item_slug = item_slug[: -(len(kind_slug) + 1)]
    parts = [upper_slug(topic_slug)]
    if item_slug:
        parts.append(upper_slug(item_slug))
    parts.extend([suffix, doc_date.replace("-", "_")])
    return "_".join(parts) + ".md"


def stage_arg(value: str) -> str:
    if not STAGE_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("stage must match sNN (for example s03)")
    return value


def roadmap_arg(value: str) -> str:
    if not ROADMAP_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("roadmap must match vNN (for example v02)")
    return value


def date_arg(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be a real YYYY-MM-DD date") from exc
    return value


def cmd_doc_new(args: argparse.Namespace) -> int:
    root = repo_root()
    topic = args.topic or current_topic(root)
    doc_date = args.date or now_iso()[:10]
    title = args.title or f"{topic} {args.slug} {args.kind}"
    directory = root / args.dir if args.dir else root / "docs" / "planning" / slugify(topic)
    path = directory / doc_filename(topic, args.slug, args.kind, doc_date)
    if path.exists() and not args.force:
        print_json({
            "ok": False,
            "miss": ["path.exists"],
            "path": str(path.relative_to(root)),
            "fix": ["use --force or a new --slug"],
        })
        return 1

    template = "small-plan.md" if args.kind == "plan" else "small-changelog.md"
    text = render_template(
        template,
        title=title,
        topic=topic,
        slug=args.slug,
        stage=args.stage or read_state(root).get("st", ""),
        status=args.status,
        updated=now_iso(),
    )
    write_text(path, text)
    event = append_event(
        "doc",
        kind=args.kind,
        topic=slugify(topic),
        slug=slugify(args.slug),
        path=str(path.relative_to(root)),
    )
    print_json({
        "ok": True,
        "doc": str(path.relative_to(root)),
        "kind": args.kind,
        "event": event["id"],
    })
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = read_state()
    if not state:
        print_json({"ok": False, "miss": [".docops/s.md"], "fix": ["dol init <topic>"]})
        return 1
    print(render_state(state).strip())
    return 0


def validate_workspace(root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    errors: list[dict[str, str]] = []

    def issue(path: str, why: str) -> None:
        errors.append({"path": path, "why": why})

    state = read_state(root)
    required_state = {"tp", "rm", "st", "stat", "health", "updated"}
    for key in sorted(required_state - set(state)):
        issue(".docops/s.md", f"missing state field: {key}")
    if state.get("rm") and not ROADMAP_RE.fullmatch(state["rm"]):
        issue(".docops/s.md", "rm must match vNN")
    if state.get("st") and not STAGE_RE.fullmatch(state["st"]):
        issue(".docops/s.md", "st must match sNN")
    if state.get("stat") and state["stat"] not in STATE_STATUSES:
        issue(".docops/s.md", "invalid stat")
    if state.get("health") and state["health"] not in HEALTH_STATUSES:
        issue(".docops/s.md", "invalid health")

    cards_file = card_path(root)
    if not cards_file.exists():
        issue(".docops/k.jsonl", "missing knowledge file")
    try:
        cards = read_jsonl(cards_file)
    except (OSError, json.JSONDecodeError) as exc:
        issue(".docops/k.jsonl", str(exc))
        cards = []
    for index, card in enumerate(cards, 1):
        label = f".docops/k.jsonl:{index}"
        if not {"id", "ty", "k", "st"}.issubset(card):
            issue(label, "missing required card field")
            continue
        if not CARD_ID_RE.fullmatch(str(card["id"])):
            issue(label, "invalid card id")
        if card["ty"] not in CARD_TYPES or not str(card["id"]).startswith(str(card["ty"])):
            issue(label, "card id/type mismatch")
        if card["st"] not in CARD_STATUSES:
            issue(label, "invalid card status")
        if card.get("sev") is not None and card["sev"] not in {"b", "w", "s", "i"}:
            issue(label, "invalid card severity")
        if card.get("conf") is not None and not isinstance(card["conf"], (int, float)):
            issue(label, "card confidence must be numeric")
        for key in ["k", "sc", "if", "req", "bad", "seq", "v", "cost"]:
            if card.get(key) is not None and not isinstance(card[key], str):
                issue(label, f"card field must be a string: {key}")

    events_file = event_path(root)
    if not events_file.exists():
        issue(".docops/ev.jsonl", "missing event file")
    try:
        events = read_jsonl(events_file)
    except (OSError, json.JSONDecodeError) as exc:
        issue(".docops/ev.jsonl", str(exc))
        events = []
    seen_event_ids: set[str] = set()
    for index, event in enumerate(events, 1):
        label = f".docops/ev.jsonl:{index}"
        if not {"id", "ts", "ty"}.issubset(event):
            issue(label, "missing required event field")
            continue
        event_id = str(event["id"])
        if not EVENT_ID_RE.fullmatch(event_id):
            issue(label, "invalid event id")
        if event_id in seen_event_ids:
            issue(label, "duplicate event id")
        seen_event_ids.add(event_id)
        if event["ty"] not in EVENT_TYPES:
            issue(label, "invalid event type")
        if event.get("result") is not None and event["result"] not in VA_RESULTS:
            issue(label, "invalid validation result")
        if event.get("st") is not None and not STAGE_RE.fullmatch(str(event["st"])):
            issue(label, "invalid stage")
        if event.get("rm") is not None and not ROADMAP_RE.fullmatch(str(event["rm"])):
            issue(label, "invalid roadmap")
        if event.get("pr") is not None and not isinstance(event["pr"], int):
            issue(label, "pr must be an integer")
        if event.get("hist") is not None and not isinstance(event["hist"], bool):
            issue(label, "hist must be boolean")
        for key in ["ts", "slug", "action", "cmd", "card"]:
            if event.get(key) is not None and not isinstance(event[key], str):
                issue(label, f"event field must be a string: {key}")

    rules_path = docops_dir(root) / "c.yaml"
    if not rules_path.exists():
        issue(".docops/c.yaml", "missing constraint file")
    else:
        rules = parse_rules(root)
        if not rules:
            issue(".docops/c.yaml", "no rules parsed")
        for rule_id, rule in rules.items():
            if not re.fullmatch(r"R[0-9]{3}", rule_id):
                issue(".docops/c.yaml", f"invalid rule id: {rule_id}")
            if not {"if", "sev"}.issubset(rule):
                issue(".docops/c.yaml", f"incomplete rule: {rule_id}")
            if rule.get("sev") not in {"b", "w", "s", "i"}:
                issue(".docops/c.yaml", f"invalid severity: {rule_id}")

    profile_path = docops_dir(root) / "p.yaml"
    if not profile_path.exists():
        issue(".docops/p.yaml", "missing profile file")
    else:
        profile_text = read_text(profile_path)
        if not any(line.strip() == "u:" for line in profile_text.splitlines()):
            issue(".docops/p.yaml", "missing user profile root")
        for line in profile_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("tok:"):
                token_mode = stripped.split(":", 1)[1].strip()
                if token_mode not in {"low", "med", "high"}:
                    issue(".docops/p.yaml", "invalid token mode")

    return {"ok": not errors, "errors": errors, "checked": ["s", "c", "k", "ev", "p"]}


def cmd_validate(args: argparse.Namespace) -> int:
    result = validate_workspace()
    print_json(result)
    return 0 if result["ok"] else 1


def cmd_init(args: argparse.Namespace) -> int:
    print_json(init_docops(args.topic))
    return 0


def cmd_st_act(args: argparse.Namespace) -> int:
    state = update_state(st=args.stage, stat="active")
    event = append_event("st", st=args.stage, action="act")
    doc = maybe_write_long_doc("st", event)
    print_json({"ok": True, "st": state["st"], "event": event["id"], "doc": doc})
    return 0


def cmd_rm_bump(args: argparse.Namespace) -> int:
    state = update_state(rm=args.version)
    event = append_event("rm", rm=args.version, action="bump", hist=True)
    doc = maybe_write_long_doc("rm", event)
    print_json({"ok": True, "rm": state["rm"], "hist": True, "event": event["id"], "doc": doc})
    return 0


def cmd_ch_add(args: argparse.Namespace) -> int:
    state = read_state()
    stage = args.stage or state.get("st") or "s01"
    event = append_event("ch", st=stage, pr=args.pr, slug=args.slug or "change")
    update_state(last_ch=event["id"], st=stage)
    doc = maybe_write_long_doc("ch", event)
    print_json({"ok": True, "ch": event["id"], "st": stage, "pr": args.pr, "doc": doc})
    return 0


def cmd_va_add(args: argparse.Namespace) -> int:
    state = read_state()
    stage = args.stage or state.get("st") or "s01"
    health = {"pass": "green", "fail": "red", "mix": "yellow", "def": "yellow"}[args.result]
    event = append_event("va", st=stage, pr=args.pr, result=args.result)
    update_state(last_va=event["id"], st=stage, health=health)
    doc = maybe_write_long_doc("va", event)
    print_json({"ok": True, "va": event["id"], "result": args.result, "doc": doc})
    return 0


def cmd_hf_upd(args: argparse.Namespace) -> int:
    state = read_state()
    root = repo_root()
    summary = render_template(
        "handoff.md",
        id="hf",
        topic=state.get("tp", ""),
        stage=state.get("st", ""),
        roadmap=state.get("rm", ""),
        result=state.get("health", ""),
        slug="handoff",
        updated=now_iso(),
    )
    path = docops_dir(root) / "handoff.md"
    write_text(path, summary)
    long_doc = None
    if long_docs_enabled(root):
        topic = slugify(current_topic(root))
        long_path = root / "docs" / "workstreams" / topic / "transfer" / "handoff.md"
        write_text(long_path, summary)
        long_doc = str(long_path.relative_to(root))
    event = append_event("hf", path=str(path.relative_to(root)))
    print_json({"ok": True, "hf": str(path.relative_to(root)), "doc": long_doc, "event": event["id"]})
    return 0


def cmd_ev_add(args: argparse.Namespace) -> int:
    event = append_event(
        args.ty,
        cmd=args.cmd,
        path=args.path,
        summary=args.summary,
    )
    print_json({"ok": True, "event": event["id"], "ty": event["ty"]})
    return 0


def latest_cards(root: Path | None = None) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for card in read_jsonl(card_path(root)):
        cid = str(card.get("id", ""))
        if cid:
            cards[cid] = card
    return cards


def next_card_id(ty: str, root: Path | None = None) -> str:
    max_num = 0
    for cid in latest_cards(root):
        if cid.startswith(ty):
            tail = cid[len(ty):]
            if tail.isdigit():
                max_num = max(max_num, int(tail))
    return f"{ty}{max_num + 1:03d}"


def add_card(ty: str, key: str, value: str, root: Path | None = None, st: str = "cand") -> dict[str, Any]:
    if ty not in CARD_TYPES:
        raise ValueError(f"bad card type: {ty}")
    card: dict[str, Any] = {
        "id": next_card_id(ty, root),
        "ty": ty,
        "k": key,
        "sc": "user" if ty == "P" else "repo",
        "v": value,
        "st": st,
    }
    append_jsonl(card_path(root), card)
    append_event("kb", root, card=card["id"], action="add", k=key)
    return card


def cmd_kb_add(args: argparse.Namespace) -> int:
    card = add_card(args.ty, args.k, args.v)
    print_json({"ok": True, "card": card["id"], "st": card["st"]})
    return 0


def event_key(event: dict[str, Any]) -> str:
    parts = [str(event.get("st", "")), str(event.get("pr", "")), str(event.get("slug", ""))]
    return ".".join(p for p in parts if p) or str(event.get("ty", "event"))


def run_learn(root: Path | None = None) -> dict[str, Any]:
    events = read_jsonl(event_path(root))
    cards_by_key = {str(c.get("k")) for c in latest_cards(root).values()}
    made: list[str] = []

    fail_counts: Counter[str] = Counter()
    for event in events:
        if event.get("ty") == "va" and event.get("result") == "fail":
            fail_counts[event_key(event)] += 1
    for key, count in sorted(fail_counts.items()):
        card_key = "fail." + slugify(key).replace("-", ".")
        if count >= 2 and card_key not in cards_by_key:
            card = add_card("L", card_key, f"same failure repeated {count} times", root, st="cand")
            made.append(card["id"])
            cards_by_key.add(card_key)

    cmd_counts: Counter[str] = Counter()
    for event in events:
        if event.get("ty") == "cmd" and event.get("cmd"):
            cmd_counts[str(event["cmd"])] += 1
    for cmd, count in sorted(cmd_counts.items()):
        card_key = "cmd." + slugify(cmd).replace("-", ".")
        if count >= 3 and card_key not in cards_by_key:
            card = add_card("S", card_key, cmd, root, st="cand")
            made.append(card["id"])
            cards_by_key.add(card_key)

    append_event("learn", root, made=",".join(made))
    return {"ok": True, "made": made}


def cmd_learn(args: argparse.Namespace) -> int:
    print_json(run_learn())
    return 0


def run_promote(card_id: str, to_status: str = "acc", root: Path | None = None) -> dict[str, Any]:
    if to_status not in {"acc", "ret"}:
        return {"ok": False, "miss": ["status"], "fix": ["use acc or ret"]}
    cards = latest_cards(root)
    card = cards.get(card_id)
    if not card:
        return {"ok": False, "miss": [card_id], "fix": ["dol kb add"]}
    if card.get("st") != "cand":
        return {"ok": False, "miss": ["cand"], "fix": ["prom only cand cards"]}
    promoted = dict(card)
    promoted["st"] = to_status
    promoted["prom_ts"] = now_iso()
    append_jsonl(card_path(root), promoted)
    event = append_event("prom", root, card=card_id, st=to_status)
    return {"ok": True, "card": card_id, "st": to_status, "event": event["id"]}


def cmd_prom(args: argparse.Namespace) -> int:
    result = run_promote(args.id, args.to)
    print_json(result)
    return 0 if result.get("ok") else 1


def event_index(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = []
    for idx, event in enumerate(events):
        item = dict(event)
        item["_idx"] = idx
        indexed.append(item)
    return indexed


def is_perf_claim(event: dict[str, Any]) -> bool:
    claim = str(event.get("claim", ""))
    slug = str(event.get("slug", ""))
    text = f"{claim} {slug}".lower()
    return any(token in text for token in ["claim.perf", "perf", "benchmark", "latency", "speedup"])


def parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def add_issue(issues: list[dict[str, Any]], rid: str, sev: str, miss: str, why: str, fix: str) -> None:
    issues.append({"rule": rid, "sev": sev, "miss": miss, "why": why, "fix": fix})


def run_lint(root: Path | None = None, soft: bool = False) -> dict[str, Any]:
    rules = parse_rules(root)
    enabled = set(rules) or {"R001", "R002", "R003", "R004", "R005", "R006", "R007"}
    events = event_index(read_jsonl(event_path(root)))
    state = read_state(root)
    issues: list[dict[str, Any]] = []

    if "R001" in enabled:
        ch_events = [e for e in events if e.get("ty") == "ch"]
        good_va = [e for e in events if e.get("ty") == "va" and e.get("result") in {"pass", "def"}]
        if ch_events:
            last_ch = max(int(e["_idx"]) for e in ch_events)
            last_good_va = max([int(e["_idx"]) for e in good_va], default=-1)
            if last_good_va < last_ch:
                add_issue(issues, "R001", "b", "va", "ch exists but no va.pass or va.def", "va.add or mark def")

    if "R002" in enabled:
        perf_ch = [e for e in events if e.get("ty") == "ch" and is_perf_claim(e)]
        if perf_ch:
            bench_runs = sum(1 for e in events if e.get("ty") == "va" and e.get("bench") is True)
            if bench_runs < 3:
                add_issue(issues, "R002", "b", "bench", "claim.perf needs va.bench.runs>=3", "run bench 3 times")

    if "R003" in enabled:
        bad_rm = [e for e in events if e.get("ty") == "rm" and e.get("action") == "bump" and not e.get("hist")]
        if bad_rm:
            add_issue(issues, "R003", "b", "rm.hist", "rm.bump requires rm.hist", "record roadmap history")

    if "R004" in enabled:
        st_close = [e for e in events if e.get("ty") == "st" and e.get("action") == "close"]
        if st_close:
            has_final = any(e.get("ty") == "va" and e.get("final") is True for e in events)
            has_lesson = any(e.get("ty") in {"ls", "learn"} for e in events)
            if not (has_final and has_lesson):
                add_issue(issues, "R004", "b", "va.final&ls", "st.close requires va.final and lesson", "add final va and lesson")

    if "R005" in enabled:
        updated = parse_dt(state.get("updated", ""))
        if updated is not None:
            age_days = (datetime.now(timezone.utc) - updated).total_seconds() / 86400
            has_hf = any(e.get("ty") == "hf" for e in events)
            if age_days > 1 and not has_hf:
                add_issue(issues, "R005", "w", "hf", "pause.days>1 requires hf", "hf.upd")

    cards = latest_cards(root)
    keys = {str(c.get("k")) for c in cards.values()}
    if "R006" in enabled:
        counts: Counter[str] = Counter()
        for e in events:
            if e.get("ty") == "va" and e.get("result") == "fail":
                counts[event_key(e)] += 1
        if any(v >= 2 for v in counts.values()) and not any(k.startswith("fail.") for k in keys):
            add_issue(issues, "R006", "s", "L.cand", "fail.same>=2 suggests lesson", "dol learn")

    if "R007" in enabled:
        counts = Counter(str(e.get("cmd")) for e in events if e.get("ty") == "cmd" and e.get("cmd"))
        if any(v >= 3 for v in counts.values()) and not any(k.startswith("cmd.") for k in keys):
            add_issue(issues, "R007", "s", "S.cand", "cmd.same>=3 suggests script", "dol learn")

    block = any(i["sev"] == "b" for i in issues)
    miss = []
    rule = []
    fix = []
    why = []
    for item in issues:
        if item["miss"] not in miss:
            miss.append(item["miss"])
        if item["rule"] not in rule:
            rule.append(item["rule"])
        if item["fix"] not in fix:
            fix.append(item["fix"])
        if item["why"] not in why:
            why.append(item["why"])
    return {
        "ok": not block,
        "miss": miss,
        "rule": rule,
        "why": "; ".join(why) if why else "ok",
        "fix": fix,
        "soft": bool(soft),
    }


def cmd_lint(args: argparse.Namespace) -> int:
    result = run_lint(soft=args.soft)
    print_json(result)
    return 0 if args.soft or result.get("ok") else 1


def run_solve_stub(mode: str, root: Path | None = None) -> dict[str, Any]:
    lint = run_lint(root, soft=True)
    fix_map = {
        "va": "va.add",
        "bench": "va.bench",
        "rm.hist": "rm.hist",
        "va.final&ls": "va.final+learn",
        "hf": "hf.upd",
        "L.cand": "learn",
        "S.cand": "learn",
    }
    fixes = [fix_map.get(m, str(m)) for m in lint.get("miss", [])]
    if mode == "check":
        status = "ok" if lint.get("ok") else "violated"
    elif mode == "conflict":
        status = "none" if lint.get("ok") else "conflict"
    else:
        status = "feasible"
    return {
        "solver": "stub",
        "mode": mode,
        "status": status,
        "fix": fixes,
        "cost": len(fixes),
        "rules": lint.get("rule", []),
    }


def cmd_solve(args: argparse.Namespace) -> int:
    if not args.stub:
        print_json({"ok": False, "miss": ["--stub"], "fix": ["use --stub in Phase 1"]})
        return 2
    print_json(run_solve_stub(args.mode))
    return 0


# --- cross-agent exchange (executor delivery -> auditor report) -----------
#
# Asynchronous document protocol living in .docops/exchange/<task-id>/.
# Structured fields live in *.json sidecars (stdlib json only); Markdown
# files carry the human narrative. Every round gets its own rNNN/ directory
# so history is append-only by construction.

EXCHANGE = "exchange"
EXCHANGE_STATUSES = [
    "requested",
    "in_progress",
    "ready_for_audit",
    "auditing",
    "changes_requested",
    "disputed",
    "approved",
    "closed",
]
EXCHANGE_TRANSITIONS = {
    "requested": {"in_progress", "closed"},
    "in_progress": {"ready_for_audit", "closed"},
    "ready_for_audit": {"auditing"},
    "auditing": {"approved", "changes_requested"},
    "changes_requested": {"changes_requested", "disputed", "ready_for_audit"},
    "disputed": {"disputed", "ready_for_audit"},
    "approved": {"closed"},
    "closed": set(),
}
EXCHANGE_DOC_TYPES = {"request", "delivery", "audit", "response", "closure"}
EXCHANGE_REQUIRED = {
    "request": ["doc", "type", "task", "round", "from", "to", "executor", "auditor", "ts", "title", "request", "scope", "acceptance", "base_commit"],
    "delivery": ["doc", "type", "task", "round", "from", "to", "ts", "base_commit", "result_commit", "changed_files", "claims", "validation", "limitations", "risks", "open_questions"],
    "audit": ["doc", "type", "task", "round", "from", "to", "ts", "verdict", "delivery", "findings", "summary"],
    "response": ["doc", "type", "task", "round", "from", "to", "ts", "audit", "responses"],
    "closure": ["doc", "type", "task", "round", "from", "ts", "resolution", "approved_round", "note"],
}
EXCHANGE_STATE_REQUIRED = ["task", "title", "status", "round", "executor", "auditor", "approved_round", "docs", "created", "updated"]
FINDING_SEVERITIES = {"blocker", "major", "minor", "info"}
AUDIT_VERDICTS = {"approve", "request_changes"}
RESPONSE_ACTIONS = {"accept", "dispute"}
EXCHANGE_VA_RESULTS = {"pass", "fail", "mix"}
CLOSURE_RESOLUTIONS = {"approved", "cancelled"}
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ROUND_RE = re.compile(r"^r[0-9]{3}$")
MAX_FIELD = 8192


class ExchangeError(Exception):
    """Actionable exchange protocol failure."""

    def __init__(self, why: str, miss: list[str] | None = None, fix: list[str] | None = None):
        super().__init__(why)
        self.why = why
        self.miss = miss or []
        self.fix = fix or []


def clip(value: str) -> str:
    value = str(value)
    return value if len(value) <= MAX_FIELD else value[:MAX_FIELD] + "...(truncated)"


def exchange_root(root: Path | None = None) -> Path:
    return docops_dir(root) / EXCHANGE


def task_path(task_id: str, root: Path | None = None) -> Path:
    base = exchange_root(root).resolve()
    path = (base / task_id).resolve()
    if path.parent != base:
        raise ExchangeError("task id escapes the exchange directory", miss=[task_id])
    return path


def task_id_arg(value: str) -> str:
    if not TASK_ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("task id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    return value


def write_file_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, obj: dict[str, Any]) -> None:
    write_file_atomic(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


@contextmanager
def task_lock(tdir: Path):
    lock = tdir / ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ExchangeError(
            "task is locked by another writer",
            miss=[str(lock)],
            fix=["retry in a few seconds; delete a stale .lock only if no writer is active"],
        ) from exc
    os.write(fd, f"{os.getpid()} {now_iso()}\n".encode("utf-8"))
    os.close(fd)
    try:
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def read_task_state(tdir: Path) -> dict[str, Any]:
    path = tdir / "state.json"
    if not path.is_file():
        raise ExchangeError("exchange task not found", miss=[str(path)], fix=["dol exchange new --id <task> ..."])
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise ExchangeError(f"corrupt state.json: {exc}", miss=[str(path)]) from exc


def write_task_state(tdir: Path, state: dict[str, Any]) -> None:
    state["updated"] = now_iso()
    state["rev"] = int(state.get("rev", 0)) + 1
    write_json_atomic(tdir / "state.json", state)


def transition(state: dict[str, Any], target: str) -> None:
    current = state.get("status", "")
    if target not in EXCHANGE_TRANSITIONS.get(current, set()):
        allowed = sorted(EXCHANGE_TRANSITIONS.get(current, set()))
        raise ExchangeError(
            f"illegal transition {current} -> {target}",
            miss=[f"status:{current}"],
            fix=[f"allowed targets from {current}: {allowed or 'none (terminal state)'}"],
        )
    state["status"] = target


def doc_sidecar(tdir: Path, doc_id: str, ext: str) -> Path | None:
    parts = doc_id.split("/")
    if len(parts) == 2 and parts[1] in {"request", "closure"}:
        return tdir / f"{parts[1]}.{ext}"
    if len(parts) == 3 and ROUND_RE.fullmatch(parts[1]) and parts[2] in {"delivery", "audit", "response"}:
        return tdir / parts[1] / f"{parts[2]}.{ext}"
    return None


def write_exchange_doc(tdir: Path, state: dict[str, Any], doc_type: str, rnd: int,
                       meta: dict[str, Any], md_text: str, extend: bool = False) -> None:
    json_path = doc_sidecar(tdir, meta["doc"], "json")
    md_path = doc_sidecar(tdir, meta["doc"], "md")
    assert json_path is not None and md_path is not None
    if not extend and (json_path.exists() or md_path.exists()):
        raise ExchangeError(
            "document already exists; exchange history is append-only",
            miss=[str(json_path)],
            fix=["open a new round with dol exchange deliver"],
        )
    write_json_atomic(json_path, meta)
    write_file_atomic(md_path, md_text)
    if meta["doc"] not in state["docs"]:
        state["docs"].append(meta["doc"])


def md_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def parse_va(entries: list[str]) -> list[dict[str, str]]:
    va: list[dict[str, str]] = []
    for entry in entries or []:
        if "=" not in entry:
            raise ExchangeError(
                "validation must be 'cmd=result'",
                miss=[entry],
                fix=["--va 'python3 -m unittest discover -s tests=pass'"],
            )
        command, result = entry.rsplit("=", 1)
        result = result.strip()
        if result not in EXCHANGE_VA_RESULTS:
            raise ExchangeError(f"invalid validation result: {result}", fix=[f"use one of {sorted(EXCHANGE_VA_RESULTS)}"])
        va.append({"cmd": clip(command.strip()), "result": result})
    return va


def parse_findings(specs: list[str]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for index, spec in enumerate(specs or [], 1):
        parts = [part.strip() for part in spec.split("|", 3)]
        if len(parts) != 4:
            raise ExchangeError("finding must be 'severity|path|evidence|advice'", miss=[spec])
        severity, fpath, evidence, advice = parts
        if severity not in FINDING_SEVERITIES:
            raise ExchangeError(f"invalid severity: {severity}", fix=[f"use one of {sorted(FINDING_SEVERITIES)}"])
        findings.append({
            "id": f"F{index}",
            "severity": severity,
            "path": clip(fpath),
            "evidence": clip(evidence),
            "advice": clip(advice),
        })
    return findings


def render_findings_md(findings: list[dict[str, str]]) -> str:
    if not findings:
        return "(no findings)"
    blocks = []
    for finding in findings:
        blocks.append(
            f"### {finding['id']} [{finding['severity']}] {finding['path']}\n\n"
            f"- evidence: {finding['evidence']}\n"
            f"- advice: {finding['advice']}"
        )
    return "\n\n".join(blocks)


def render_response_doc(meta: dict[str, Any]) -> str:
    lines = "\n".join(
        f"- {item['finding']}: {item['action']}; {item['note']} ({item['ts']})"
        for item in meta["responses"]
    )
    return render_template(
        "exchange-response.md",
        doc=meta["doc"],
        round=str(meta["round"]),
        audit=meta["audit"],
        from_agent=meta["from"],
        to_agent=meta["to"],
        ts=meta["ts"],
        responses=lines,
    )


def cmd_exchange_new(args: argparse.Namespace) -> int:
    root = repo_root()
    tdir = task_path(args.id, root)
    if tdir.exists():
        raise ExchangeError("task already exists", miss=[str(tdir)], fix=["choose another --id"])
    request_text = clip(args.request)
    if args.request_file:
        rfile = Path(args.request_file)
        if not rfile.is_file():
            raise ExchangeError("request file not found", miss=[args.request_file])
        request_text = clip(read_text(rfile))
    tdir.mkdir(parents=True)
    ts = now_iso()
    state: dict[str, Any] = {
        "task": args.id,
        "title": clip(args.title),
        "status": "requested",
        "round": 0,
        "executor": args.executor,
        "auditor": args.auditor,
        "approved_round": None,
        "docs": [],
        "rev": 0,
        "created": ts,
        "updated": ts,
    }
    meta = {
        "doc": f"{args.id}/request",
        "type": "request",
        "task": args.id,
        "round": 0,
        "from": args.from_agent,
        "to": args.to_agent,
        "executor": args.executor,
        "auditor": args.auditor,
        "ts": ts,
        "title": clip(args.title),
        "request": request_text,
        "scope": clip(args.scope),
        "acceptance": [clip(item) for item in args.acc],
        "base_commit": args.base_commit,
    }
    body = render_template(
        "exchange-request.md",
        title=meta["title"],
        task=args.id,
        doc=meta["doc"],
        from_agent=meta["from"],
        to_agent=meta["to"],
        executor=meta["executor"],
        auditor=meta["auditor"],
        base_commit=meta["base_commit"] or "(not recorded)",
        ts=ts,
        request=meta["request"] or "(see conversation)",
        scope=meta["scope"] or "(unspecified)",
        acceptance=md_list(meta["acceptance"]),
    )
    with task_lock(tdir):
        write_exchange_doc(tdir, state, "request", 0, meta, body)
        write_task_state(tdir, state)
    print_json({"ok": True, "task": args.id, "status": "requested", "doc": meta["doc"]})
    return 0


def cmd_exchange_start(args: argparse.Namespace) -> int:
    tdir = task_path(args.task, repo_root())
    with task_lock(tdir):
        state = read_task_state(tdir)
        transition(state, "in_progress")
        write_task_state(tdir, state)
    print_json({"ok": True, "task": args.task, "status": "in_progress"})
    return 0


def cmd_exchange_deliver(args: argparse.Namespace) -> int:
    tdir = task_path(args.task, repo_root())
    files = [item.strip() for item in args.files.split(",") if item.strip()]
    va = parse_va(args.va)
    with task_lock(tdir):
        state = read_task_state(tdir)
        transition(state, "ready_for_audit")
        rnd = int(state["round"]) + 1
        meta = {
            "doc": f"{args.task}/r{rnd:03d}/delivery",
            "type": "delivery",
            "task": args.task,
            "round": rnd,
            "from": state["executor"],
            "to": state["auditor"],
            "ts": now_iso(),
            "base_commit": args.base_commit,
            "result_commit": args.result_commit,
            "changed_files": files,
            "claims": [clip(item) for item in args.claims],
            "validation": va,
            "limitations": [clip(item) for item in args.limits],
            "risks": [clip(item) for item in args.risks],
            "open_questions": [clip(item) for item in args.question],
        }
        va_lines = "\n".join(f"- `{v['cmd']}` -> {v['result']}" for v in va) or "- (none recorded)"
        body = render_template(
            "exchange-delivery.md",
            doc=meta["doc"],
            round=str(rnd),
            from_agent=meta["from"],
            to_agent=meta["to"],
            base_commit=meta["base_commit"] or "(not recorded)",
            result_commit=meta["result_commit"] or "(not recorded)",
            ts=meta["ts"],
            changed_files=md_list(files),
            claims=md_list(meta["claims"]),
            validation=va_lines,
            limitations=md_list(meta["limitations"]),
            risks=md_list(meta["risks"]),
            open_questions=md_list(meta["open_questions"]),
        )
        write_exchange_doc(tdir, state, "delivery", rnd, meta, body)
        state["round"] = rnd
        write_task_state(tdir, state)
    print_json({"ok": True, "task": args.task, "status": "ready_for_audit", "round": rnd, "doc": meta["doc"]})
    return 0


def cmd_exchange_audit_start(args: argparse.Namespace) -> int:
    tdir = task_path(args.task, repo_root())
    with task_lock(tdir):
        state = read_task_state(tdir)
        if int(state.get("round", 0)) < 1:
            raise ExchangeError("no delivery to audit", fix=[f"dol exchange deliver {args.task} ..."])
        transition(state, "auditing")
        write_task_state(tdir, state)
    print_json({"ok": True, "task": args.task, "status": "auditing", "round": state["round"]})
    return 0


def cmd_exchange_audit_submit(args: argparse.Namespace) -> int:
    tdir = task_path(args.task, repo_root())
    findings = parse_findings(args.finding)
    with task_lock(tdir):
        state = read_task_state(tdir)
        if state.get("status") != "auditing":
            raise ExchangeError(
                f"cannot submit an audit from status {state.get('status')}",
                fix=[f"dol exchange audit-start {args.task}"],
            )
        rnd = int(state["round"])
        delivery_path = tdir / f"r{rnd:03d}" / "delivery.json"
        if not delivery_path.is_file():
            raise ExchangeError("no delivery for the current round", miss=[str(delivery_path)])
        delivery = json.loads(read_text(delivery_path))
        if args.verdict == "approve" and not delivery.get("validation"):
            raise ExchangeError(
                "approve requires recorded validation evidence",
                miss=["delivery.validation"],
                fix=["use --verdict request_changes, or redeliver with --va cmd=result"],
            )
        if args.verdict == "request_changes" and not findings:
            raise ExchangeError(
                "request_changes requires at least one --finding",
                fix=["--finding 'severity|path|evidence|advice'"],
            )
        meta = {
            "doc": f"{args.task}/r{rnd:03d}/audit",
            "type": "audit",
            "task": args.task,
            "round": rnd,
            "from": state["auditor"],
            "to": state["executor"],
            "ts": now_iso(),
            "verdict": args.verdict,
            "delivery": delivery["doc"],
            "findings": findings,
            "summary": clip(args.summary),
        }
        body = render_template(
            "exchange-audit.md",
            doc=meta["doc"],
            round=str(rnd),
            delivery=meta["delivery"],
            verdict=args.verdict,
            from_agent=meta["from"],
            to_agent=meta["to"],
            ts=meta["ts"],
            findings=render_findings_md(findings),
            summary=meta["summary"] or "(none)",
        )
        target = "approved" if args.verdict == "approve" else "changes_requested"
        transition(state, target)
        if target == "approved":
            state["approved_round"] = rnd
        write_exchange_doc(tdir, state, "audit", rnd, meta, body)
        write_task_state(tdir, state)
    print_json({"ok": True, "task": args.task, "status": target, "round": rnd, "doc": meta["doc"], "findings": len(findings)})
    return 0


def cmd_exchange_respond(args: argparse.Namespace) -> int:
    tdir = task_path(args.task, repo_root())
    with task_lock(tdir):
        state = read_task_state(tdir)
        if state.get("status") not in {"changes_requested", "disputed"}:
            raise ExchangeError(
                f"cannot respond from status {state.get('status')}",
                fix=["responses are only allowed after an audit requested changes"],
            )
        rnd = int(state["round"])
        audit_path = tdir / f"r{rnd:03d}" / "audit.json"
        if not audit_path.is_file():
            raise ExchangeError("no audit for the current round", miss=[str(audit_path)])
        audit = json.loads(read_text(audit_path))
        known = {finding["id"] for finding in audit.get("findings", [])}
        if args.finding not in known:
            raise ExchangeError(f"unknown finding: {args.finding}", fix=[f"known findings: {sorted(known)}"])
        resp_path = tdir / f"r{rnd:03d}" / "response.json"
        if resp_path.exists():
            meta = json.loads(read_text(resp_path))
        else:
            meta = {
                "doc": f"{args.task}/r{rnd:03d}/response",
                "type": "response",
                "task": args.task,
                "round": rnd,
                "from": state["executor"],
                "to": state["auditor"],
                "ts": now_iso(),
                "audit": audit["doc"],
                "responses": [],
            }
        meta["responses"].append({
            "finding": args.finding,
            "action": args.action,
            "note": clip(args.note),
            "ts": now_iso(),
        })
        write_exchange_doc(tdir, state, "response", rnd, meta, render_response_doc(meta), extend=True)
        transition(state, "disputed" if args.action == "dispute" else state["status"])
        write_task_state(tdir, state)
    print_json({"ok": True, "task": args.task, "status": state["status"], "doc": meta["doc"], "responses": len(meta["responses"])})
    return 0


def cmd_exchange_close(args: argparse.Namespace) -> int:
    tdir = task_path(args.task, repo_root())
    with task_lock(tdir):
        state = read_task_state(tdir)
        resolution = "approved" if state.get("status") == "approved" else "cancelled"
        transition(state, "closed")
        meta = {
            "doc": f"{args.task}/closure",
            "type": "closure",
            "task": args.task,
            "round": int(state["round"]),
            "from": state["executor"],
            "ts": now_iso(),
            "resolution": resolution,
            "approved_round": state.get("approved_round"),
            "note": clip(args.note),
        }
        body = render_template(
            "exchange-closure.md",
            doc=meta["doc"],
            resolution=resolution,
            approved_round=str(meta["approved_round"] if meta["approved_round"] is not None else "-"),
            from_agent=meta["from"],
            ts=meta["ts"],
            note=meta["note"] or "(none)",
        )
        write_exchange_doc(tdir, state, "closure", int(state["round"]), meta, body)
        write_task_state(tdir, state)
    print_json({"ok": True, "task": args.task, "status": "closed", "resolution": resolution, "doc": meta["doc"]})
    return 0


def cmd_exchange_status(args: argparse.Namespace) -> int:
    root = repo_root()
    if args.task:
        print_json(read_task_state(task_path(args.task, root)))
        return 0
    base = exchange_root(root)
    tasks: list[dict[str, Any]] = []
    if base.exists():
        for path in sorted(base.glob("*")):
            state_path = path / "state.json"
            if not state_path.is_file():
                continue
            try:
                state = json.loads(read_text(state_path))
            except json.JSONDecodeError:
                tasks.append({"task": path.name, "status": "corrupt"})
                continue
            tasks.append({
                "task": state.get("task", path.name),
                "status": state.get("status"),
                "round": state.get("round"),
                "updated": state.get("updated"),
            })
    print_json({"ok": True, "tasks": tasks})
    return 0


def validate_exchange(root: Path | None = None, task_id: str | None = None) -> dict[str, Any]:
    root = root or repo_root()
    errors: list[dict[str, str]] = []

    def issue(path: Any, why: str) -> None:
        errors.append({"path": str(path), "why": why})

    base = exchange_root(root)
    if task_id:
        if not TASK_ID_RE.fullmatch(task_id):
            issue(base / task_id, "invalid task id")
            return {"ok": False, "errors": errors, "tasks": 0}
        names = [task_id]
    elif base.exists():
        names = sorted(path.name for path in base.glob("*") if (path / "state.json").is_file())
    else:
        names = []

    for name in names:
        tdir = base / name
        state_path = tdir / "state.json"
        if not state_path.is_file():
            issue(state_path, "missing state.json")
            continue
        try:
            state = json.loads(read_text(state_path))
        except json.JSONDecodeError as exc:
            issue(state_path, f"invalid json: {exc}")
            continue
        for key in EXCHANGE_STATE_REQUIRED:
            if key not in state:
                issue(state_path, f"missing state field: {key}")
        status = state.get("status")
        if status not in EXCHANGE_STATUSES:
            issue(state_path, f"invalid status: {status}")
        if not isinstance(state.get("round"), int) or state["round"] < 0:
            issue(state_path, "round must be a non-negative integer")
        docs = state.get("docs", [])
        if not isinstance(docs, list) or len(docs) != len(set(docs)):
            issue(state_path, "doc index must be a list of unique ids")
            docs = []
        if f"{name}/request" not in docs:
            issue(state_path, "missing request doc in index")

        deliveries: dict[int, dict[str, Any]] = {}
        audits: dict[int, dict[str, Any]] = {}
        responses: dict[int, dict[str, Any]] = {}
        for doc_id in docs:
            if not isinstance(doc_id, str) or not doc_id.startswith(name + "/"):
                issue(state_path, f"doc id outside task: {doc_id}")
                continue
            json_path = doc_sidecar(tdir, doc_id, "json")
            md_path = doc_sidecar(tdir, doc_id, "md")
            if json_path is None or md_path is None:
                issue(state_path, f"malformed doc id: {doc_id}")
                continue
            if not json_path.is_file():
                issue(json_path, "missing doc sidecar")
                continue
            if not md_path.is_file():
                issue(md_path, "missing doc markdown")
            try:
                meta = json.loads(read_text(json_path))
            except json.JSONDecodeError as exc:
                issue(json_path, f"invalid json: {exc}")
                continue
            dtype = meta.get("type")
            if dtype not in EXCHANGE_DOC_TYPES:
                issue(json_path, f"invalid doc type: {dtype}")
                continue
            if meta.get("doc") != doc_id:
                issue(json_path, "doc field does not match the index id")
            for key in EXCHANGE_REQUIRED[dtype]:
                if key not in meta:
                    issue(json_path, f"missing field: {key}")
            parts = doc_id.split("/")
            if len(parts) == 3 and meta.get("round") != int(parts[1][1:]):
                issue(json_path, "round does not match the round directory")
            if dtype == "request" and meta.get("round") != 0:
                issue(json_path, "request round must be 0")
            if dtype == "delivery":
                deliveries[int(meta.get("round", -1))] = meta
                for va in meta.get("validation", []):
                    if va.get("result") not in EXCHANGE_VA_RESULTS:
                        issue(json_path, f"invalid validation result: {va.get('result')}")
            elif dtype == "audit":
                audits[int(meta.get("round", -1))] = meta
                if meta.get("verdict") not in AUDIT_VERDICTS:
                    issue(json_path, f"invalid verdict: {meta.get('verdict')}")
                for finding in meta.get("findings", []):
                    for key in ["id", "severity", "path", "evidence", "advice"]:
                        if key not in finding:
                            issue(json_path, f"finding missing field: {key}")
                    if finding.get("severity") not in FINDING_SEVERITIES:
                        issue(json_path, f"invalid finding severity: {finding.get('severity')}")
            elif dtype == "response":
                responses[int(meta.get("round", -1))] = meta
            elif dtype == "closure" and meta.get("resolution") not in CLOSURE_RESOLUTIONS:
                issue(json_path, f"invalid closure resolution: {meta.get('resolution')}")

        for rnd, audit in audits.items():
            delivery = deliveries.get(rnd)
            if delivery is None:
                issue(tdir / f"r{rnd:03d}" / "audit.json", "audit without a delivery in the same round")
                continue
            if str(delivery.get("ts", "")) > str(audit.get("ts", "")):
                issue(tdir / f"r{rnd:03d}" / "audit.json", "audit predates its delivery")
            if audit.get("delivery") != delivery.get("doc"):
                issue(tdir / f"r{rnd:03d}" / "audit.json", "audit does not reference the round delivery")
            if audit.get("verdict") == "approve" and not delivery.get("validation"):
                issue(tdir / f"r{rnd:03d}" / "audit.json", "approved without validation evidence")
        for rnd, response in responses.items():
            audit = audits.get(rnd)
            if audit is None:
                issue(tdir / f"r{rnd:03d}" / "response.json", "response without an audit in the same round")
                continue
            if response.get("audit") != audit.get("doc"):
                issue(tdir / f"r{rnd:03d}" / "response.json", "response does not reference the round audit")
            known = {finding.get("id") for finding in audit.get("findings", [])}
            for item in response.get("responses", []):
                if item.get("finding") not in known:
                    issue(tdir / f"r{rnd:03d}" / "response.json", f"unknown finding: {item.get('finding')}")
                if item.get("action") not in RESPONSE_ACTIONS:
                    issue(tdir / f"r{rnd:03d}" / "response.json", f"invalid response action: {item.get('action')}")

        current_round = state.get("round", 0)
        if status == "approved":
            approved_round = state.get("approved_round")
            if not isinstance(approved_round, int) or audits.get(approved_round, {}).get("verdict") != "approve":
                issue(state_path, "approved without a matching approve audit round")
        if status == "changes_requested" and audits.get(current_round, {}).get("verdict") != "request_changes":
            issue(state_path, "changes_requested without a request_changes audit in the current round")
        if status == "closed" and f"{name}/closure" not in docs:
            issue(state_path, "closed without a closure doc")

    return {"ok": not errors, "errors": errors, "tasks": len(names)}


def cmd_exchange_validate(args: argparse.Namespace) -> int:
    result = validate_exchange(repo_root(), args.task if args.task else None)
    print_json(result)
    return 0 if result["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dol", description="DocOps Logic Phase 1 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="initialize .docops for a topic")
    p.add_argument("topic")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status", help="print short .docops/s.md state")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("validate", help="validate .docops files against repository contracts")
    p.set_defaults(func=cmd_validate)

    p_st = sub.add_parser("st", help="stage commands")
    st_sub = p_st.add_subparsers(dest="st_cmd", required=True)
    p = st_sub.add_parser("act", help="activate stage")
    p.add_argument("stage", type=stage_arg)
    p.set_defaults(func=cmd_st_act)

    p_rm = sub.add_parser("rm", help="roadmap commands")
    rm_sub = p_rm.add_subparsers(dest="rm_cmd", required=True)
    p = rm_sub.add_parser("bump", help="bump roadmap version")
    p.add_argument("version", type=roadmap_arg)
    p.set_defaults(func=cmd_rm_bump)

    p_ch = sub.add_parser("ch", help="change commands")
    ch_sub = p_ch.add_subparsers(dest="ch_cmd", required=True)
    p = ch_sub.add_parser("add", help="add change event")
    p.add_argument("--stage", type=stage_arg)
    p.add_argument("--pr", type=int)
    p.add_argument("--slug")
    p.set_defaults(func=cmd_ch_add)

    p_va = sub.add_parser("va", help="validation commands")
    va_sub = p_va.add_subparsers(dest="va_cmd", required=True)
    p = va_sub.add_parser("add", help="add validation event")
    p.add_argument("--stage", type=stage_arg)
    p.add_argument("--pr", type=int)
    p.add_argument("--result", choices=sorted(VA_RESULTS), default="pass")
    p.set_defaults(func=cmd_va_add)

    p_hf = sub.add_parser("hf", help="handoff commands")
    hf_sub = p_hf.add_subparsers(dest="hf_cmd", required=True)
    p = hf_sub.add_parser("upd", help="update handoff summary")
    p.set_defaults(func=cmd_hf_upd)

    p_doc = sub.add_parser("doc", help="standalone small plan/changelog docs")
    doc_sub = p_doc.add_subparsers(dest="doc_cmd", required=True)
    p = doc_sub.add_parser("new", help="create a standalone small plan or changelog")
    p.add_argument("--kind", required=True, choices=sorted(DOC_KINDS))
    p.add_argument("--topic", help="topic directory; defaults to .docops tp")
    p.add_argument("--slug", required=True, help="short stable slug for filename")
    p.add_argument("--title", help="document title")
    p.add_argument("--dir", help="output directory relative to repo root")
    p.add_argument("--stage", type=stage_arg)
    p.add_argument("--status", default="active")
    p.add_argument("--date", type=date_arg, help="YYYY-MM-DD; defaults to today UTC")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_doc_new)

    p_ev = sub.add_parser("ev", help="event commands for hooks")
    ev_sub = p_ev.add_subparsers(dest="ev_cmd", required=True)
    p = ev_sub.add_parser("add", help="append a hook event")
    p.add_argument("--ty", default="cmd", choices=["cmd"])
    p.add_argument("--cmd")
    p.add_argument("--path")
    p.add_argument("--summary")
    p.set_defaults(func=cmd_ev_add)

    p_kb = sub.add_parser("kb", help="knowledge card commands")
    kb_sub = p_kb.add_subparsers(dest="kb_cmd", required=True)
    p = kb_sub.add_parser("add", help="append a knowledge card")
    p.add_argument("--ty", required=True, choices=sorted(CARD_TYPES))
    p.add_argument("--k", required=True)
    p.add_argument("--v", required=True)
    p.set_defaults(func=cmd_kb_add)

    p = sub.add_parser("learn", help="create candidate cards from events")
    p.set_defaults(func=cmd_learn)

    p = sub.add_parser("prom", help="promote or retire a candidate card")
    p.add_argument("id")
    p.add_argument("--to", choices=["acc", "ret"], default="acc")
    p.set_defaults(func=cmd_prom)

    p = sub.add_parser("lint", help="check symbolic DocOps rules")
    p.add_argument("--soft", action="store_true")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("solve", help="Phase 1 solver stub")
    p.add_argument("--stub", action="store_true")
    p.add_argument("--mode", choices=sorted(SOLVE_MODES), default="check")
    p.set_defaults(func=cmd_solve)

    p_x = sub.add_parser("exchange", help="cross-agent delivery and audit protocol")
    x_sub = p_x.add_subparsers(dest="x_cmd", required=True)

    p = x_sub.add_parser("new", help="create an exchange task and request doc")
    p.add_argument("--id", required=True, type=task_id_arg)
    p.add_argument("--title", required=True)
    p.add_argument("--from", dest="from_agent", required=True)
    p.add_argument("--to", dest="to_agent", required=True)
    p.add_argument("--executor", default="codex")
    p.add_argument("--auditor", default="kimi")
    p.add_argument("--base-commit", default="")
    p.add_argument("--request", default="")
    p.add_argument("--request-file")
    p.add_argument("--scope", default="")
    p.add_argument("--acc", action="append", default=[], help="acceptance criterion; repeatable")
    p.set_defaults(func=cmd_exchange_new)

    p = x_sub.add_parser("start", help="mark a task in progress")
    p.add_argument("task", type=task_id_arg)
    p.set_defaults(func=cmd_exchange_start)

    p = x_sub.add_parser("deliver", help="submit an executor delivery for the next round")
    p.add_argument("task", type=task_id_arg)
    p.add_argument("--result-commit", default="")
    p.add_argument("--base-commit", default="")
    p.add_argument("--files", default="", help="comma-separated changed files")
    p.add_argument("--claims", action="append", default=[])
    p.add_argument("--va", action="append", default=[], help="'cmd=result' with result in pass|fail|mix")
    p.add_argument("--limits", action="append", default=[])
    p.add_argument("--risks", action="append", default=[])
    p.add_argument("--question", action="append", default=[])
    p.set_defaults(func=cmd_exchange_deliver)

    p = x_sub.add_parser("audit-start", help="begin auditing the current round")
    p.add_argument("task", type=task_id_arg)
    p.set_defaults(func=cmd_exchange_audit_start)

    p = x_sub.add_parser("audit-submit", help="submit an audit report for the current round")
    p.add_argument("task", type=task_id_arg)
    p.add_argument("--verdict", required=True, choices=sorted(AUDIT_VERDICTS))
    p.add_argument("--finding", action="append", default=[], help="'severity|path|evidence|advice'; repeatable")
    p.add_argument("--summary", default="")
    p.set_defaults(func=cmd_exchange_audit_submit)

    p = x_sub.add_parser("respond", help="respond to one audit finding")
    p.add_argument("task", type=task_id_arg)
    p.add_argument("--finding", required=True)
    p.add_argument("--action", required=True, choices=sorted(RESPONSE_ACTIONS))
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_exchange_respond)

    p = x_sub.add_parser("close", help="close an approved task or cancel an unstarted one")
    p.add_argument("task", type=task_id_arg)
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_exchange_close)

    p = x_sub.add_parser("status", help="show one task or list all exchange tasks")
    p.add_argument("task", nargs="?", type=task_id_arg)
    p.set_defaults(func=cmd_exchange_status)

    p = x_sub.add_parser("validate", help="validate exchange docs and the state machine")
    p.add_argument("task", nargs="?", type=task_id_arg)
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_exchange_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ExchangeError as exc:
        print_json({"ok": False, "miss": exc.miss, "why": exc.why, "fix": exc.fix})
        return 1
    except FileNotFoundError as exc:
        print_json({"ok": False, "miss": [str(exc.filename)], "fix": ["dol init <topic>"]})
        return 1
    except json.JSONDecodeError as exc:
        print_json({"ok": False, "miss": ["jsonl"], "why": str(exc), "fix": ["check .docops/*.jsonl"]})
        return 1
    except ValueError as exc:
        print_json({"ok": False, "miss": ["arg"], "why": str(exc), "fix": ["dol --help"]})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

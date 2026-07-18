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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
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

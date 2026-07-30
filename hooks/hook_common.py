#!/usr/bin/env python3
"""Shared helpers for DocOps Logic lifecycle hooks."""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def read_hook_input() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def workspace(input_data: dict[str, Any]) -> Path:
    raw = input_data.get("cwd")
    if isinstance(raw, str) and raw:
        return Path(raw).resolve()
    return Path.cwd().resolve()


def has_docops(root: Path) -> bool:
    return (root / ".docops" / "s.md").is_file()


def plugin_root() -> Path:
    configured = os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[1]


def load_dol() -> ModuleType:
    path = plugin_root() / "scripts" / "dol.py"
    spec = importlib.util.spec_from_file_location("docops_logic_dol", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def emit_json(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def command_signature(input_data: dict[str, Any]) -> str:
    tool_name = str(input_data.get("tool_name") or "tool")
    if tool_name != "Bash":
        return tool_name[:80]
    tool_input = input_data.get("tool_input")
    command = ""
    if isinstance(tool_input, dict):
        raw = tool_input.get("command") or tool_input.get("cmd")
        if isinstance(raw, str):
            command = raw.splitlines()[0]
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    executable = Path(words[0]).name if words else "command"
    return f"Bash:{executable}"[:80]

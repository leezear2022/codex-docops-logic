#!/usr/bin/env python3
"""Shared helpers for DocOps Logic lifecycle hooks."""

from __future__ import annotations

import importlib.util
import json
import ntpath
import os
import re
import shlex
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


SHELL_TOOLS = {
    "bash",
    "cmd",
    "commandprompt",
    "exec_command",
    "powershell",
    "pwsh",
    "shell",
    "write_stdin",
}


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
    configured = (
        os.environ.get("PLUGIN_ROOT")
        or os.environ.get("KIMI_PLUGIN_ROOT")
        or os.environ.get("CLAUDE_PLUGIN_ROOT")
    )
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


def is_kimi_host() -> bool:
    return bool(os.environ.get("KIMI_PLUGIN_ROOT"))


def emit_continue() -> None:
    if not is_kimi_host():
        emit_json({"continue": True})


def emit_additional_context(context: str) -> None:
    if is_kimi_host():
        print(context)
        return
    emit_json({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    })


def emit_system_message(message: str) -> None:
    if is_kimi_host():
        print(message)
        return
    emit_json({"continue": True, "systemMessage": message})


def _command_words(command: str, tool_name: str) -> list[str]:
    windows_style = (
        os.name == "nt"
        or tool_name.casefold() in {"cmd", "commandprompt", "powershell", "pwsh"}
        or bool(re.search(r"(?:^|[\s'\"&])[A-Za-z]:\\", command))
    )
    try:
        return shlex.split(command, posix=not windows_style)
    except ValueError:
        return command.split()


def _executable_name(words: list[str]) -> str:
    tokens = [word.strip("\"'") for word in words]
    while tokens and tokens[0] in {"&", "call"}:
        tokens.pop(0)
    if not tokens:
        return "command"

    first = ntpath.basename(tokens[0])
    if first.casefold() in {"cmd", "cmd.exe"} and len(tokens) >= 3 and tokens[1].casefold() in {"/c", "/k"}:
        first = ntpath.basename(tokens[2].strip("\"'"))
    return first or "command"


def command_signature(input_data: dict[str, Any]) -> str:
    tool_name = str(input_data.get("tool_name") or "tool")
    if tool_name.casefold() not in SHELL_TOOLS:
        return tool_name[:80]
    tool_input = input_data.get("tool_input")
    command = ""
    if isinstance(tool_input, dict):
        raw = tool_input.get("command") or tool_input.get("cmd")
        if isinstance(raw, str):
            command = raw.splitlines()[0]
    executable = _executable_name(_command_words(command, tool_name))
    return f"{tool_name}:{executable}"[:80]

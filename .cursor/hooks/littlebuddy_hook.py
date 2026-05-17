#!/usr/bin/env python3
"""Cursor hooks → little-buddy show_status via daemon socket."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("LITTLEBUDDY_MCP_DIR", str(_ROOT / ".littlebuddy-mcp"))

from littlebuddy_mcp.daemon_client import show_via_daemon
from littlebuddy_mcp.protocol import clip_msg
from littlebuddy_mcp.statuses import CURSOR_STATUS_PRESETS, MAX_MSG_CJK

_LAST_STATUS_FILE = Path(os.environ["LITTLEBUDDY_MCP_DIR"]) / "hook_last_status"

def _read_stdin_json() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _blob(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).lower()


def _skip_littlebuddy(data: dict) -> bool:
    return "littlebuddy" in _blob(data)


def _skip_self_hook(data: dict) -> bool:
    b = _blob(data)
    return "littlebuddy_hook" in b


def _shell_msg(data: dict) -> str | None:
    cmd = (data.get("command") or "").strip()
    if not cmd:
        return "终端"
    base = Path(cmd.split()[0]).name if cmd.split() else cmd
    return clip_msg(base) if base else "终端"


def _should_skip_duplicate(status: str) -> bool:
    try:
        return _LAST_STATUS_FILE.read_text(encoding="utf-8").strip() == status
    except OSError:
        return False


def _mark_status(status: str) -> None:
    _LAST_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LAST_STATUS_FILE.write_text(status, encoding="utf-8")


async def _push(status: str, msg: str | None = None, *, force: bool = False) -> None:
    if not force and _should_skip_duplicate(status):
        return
    m, emoji, color = CURSOR_STATUS_PRESETS[status]
    if msg:
        m = clip_msg(msg, MAX_MSG_CJK)
    await show_via_daemon(msg=m, emoji=emoji, color=color, size=4, gap=6)
    _mark_status(status)


async def _dispatch(event: str, data: dict) -> None:
    handlers: dict[
        str,
        tuple[
            str,
            Callable[[dict], str | None] | None,
            bool,
            Callable[[dict], bool] | None,
        ],
    ] = {
        "beforeSubmitPrompt": ("thinking", None, True, None),
        "preToolUse": ("tool", None, False, _skip_littlebuddy),
        "postToolUse": ("thinking", None, False, _skip_littlebuddy),
        "postToolUseFailure": ("retry", None, True, _skip_littlebuddy),
        "subagentStart": ("agent", None, True, None),
        "subagentStop": ("done", lambda _: "子任务完成", True, None),
        "beforeShellExecution": ("tool", _shell_msg, False, _skip_self_hook),
        "afterShellExecution": ("thinking", None, False, _skip_self_hook),
        "beforeMCPExecution": ("tool", None, False, _skip_littlebuddy),
        "afterMCPExecution": ("thinking", None, False, _skip_littlebuddy),
        "beforeReadFile": ("read_docs", None, False, None),
        "afterFileEdit": ("applying", None, False, None),
        "preCompact": ("session", lambda _: "压缩上下文", True, None),
        "stop": ("done", None, True, None),
        "afterAgentResponse": ("chatting", None, True, None),
    }

    spec = handlers.get(event)
    if not spec:
        return
    status, msg_fn, force, skip_fn = spec
    if skip_fn and skip_fn(data):
        return
    msg = msg_fn(data) if msg_fn else None
    await _push(status, msg, force=force)


async def _run(event: str) -> None:
    await _dispatch(event, _read_stdin_json())


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(0)
    try:
        asyncio.run(_run(sys.argv[1]))
    except (RuntimeError, OSError, json.JSONDecodeError):
        sys.exit(0)


if __name__ == "__main__":
    main()

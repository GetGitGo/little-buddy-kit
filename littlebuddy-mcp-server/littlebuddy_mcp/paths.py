"""Runtime paths for daemon socket, pid, logs (configurable via LITTLEBUDDY_MCP_DIR)."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_DIR = Path.home() / ".littlebuddy-mcp"


def resolve_cache_dir() -> Path:
    """Daemon 状态目录。优先 LITTLEBUDDY_MCP_DIR（相对路径相对进程 cwd）。"""
    raw = os.environ.get("LITTLEBUDDY_MCP_DIR", "").strip()
    if not raw:
        return _DEFAULT_DIR.resolve()
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


CACHE_DIR = resolve_cache_dir()
LAST_DEVICE_FILE = CACHE_DIR / "last_device"
DAEMON_PID_FILE = CACHE_DIR / "daemon.pid"
DAEMON_SOCK = CACHE_DIR / "daemon.sock"
DAEMON_LOG = CACHE_DIR / "daemon.log"

"""MCP stdio server：转发到常驻 BLE daemon。"""

from __future__ import annotations

import asyncio
import json
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .daemon_client import DaemonError, show_via_daemon
from .protocol import DEFAULT_MSG_SIZE
from .service import ensure_daemon_running
from .statuses import (
    COLOR_GREEN,
    CURSOR_EMOJI_NAMES,
    CURSOR_STATUS_PRESETS,
    LEVEL_COLORS,
)

app = Server("littlebuddy")
_STATUS_IDS = sorted(CURSOR_STATUS_PRESETS.keys())

# Cursor 启动 MCP 时在后台拉起 daemon（不阻塞 MCP 握手）
_boot_task: asyncio.Task[None] | None = None


def _auto_start_enabled() -> bool:
    return os.environ.get("LITTLEBUDDY_AUTO_START", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _default_scan_on_start() -> bool:
    return os.environ.get("LITTLEBUDDY_START_SCAN", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _spawn_daemon_boot() -> None:
    """随 Cursor 拉起 MCP 时自动启动 daemon（仅一次）。"""
    global _boot_task
    if not _auto_start_enabled():
        return
    if _boot_task is not None and not _boot_task.done():
        return

    async def _run() -> None:
        await ensure_daemon_running(scan=_default_scan_on_start())

    _boot_task = asyncio.create_task(_run())


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="littlebuddy_show_status",
            description="在 M5 上显示 Cursor/Claude 预设状态（经常驻 daemon，低延迟）",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": _STATUS_IDS},
                    "msg": {"type": "string"},
                },
                "required": ["status"],
            },
        ),
        Tool(
            name="littlebuddy_show",
            description="自定义显示到 little-buddy",
            inputSchema={
                "type": "object",
                "properties": {
                    "msg": {"type": "string"},
                    "emoji": {"type": "string", "enum": list(CURSOR_EMOJI_NAMES)},
                    "color": {
                        "type": "string",
                        "enum": list(LEVEL_COLORS),
                        "default": COLOR_GREEN,
                    },
                    "size": {
                        "type": "integer",
                        "enum": [1, 2, 3, 4, 5, 6],
                        "default": DEFAULT_MSG_SIZE,
                    },
                },
                "required": ["msg"],
            },
        ),
        Tool(
            name="littlebuddy_list_statuses",
            description="列出预设（无需 BLE）",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "littlebuddy_list_statuses":
            rows = [
                {
                    "id": sid,
                    "msg": CURSOR_STATUS_PRESETS[sid][0],
                    "emoji": CURSOR_STATUS_PRESETS[sid][1],
                    "color": CURSOR_STATUS_PRESETS[sid][2],
                }
                for sid in _STATUS_IDS
            ]
            return [
                TextContent(
                    type="text",
                    text=json.dumps(rows, ensure_ascii=False, indent=2),
                )
            ]

        if name == "littlebuddy_show_status":
            status = arguments["status"]
            preset = CURSOR_STATUS_PRESETS.get(status)
            if not preset:
                raise ValueError(f"未知 status: {status!r}")
            msg, emoji, color = preset
            if arguments.get("msg"):
                msg = arguments["msg"]
            await show_via_daemon(
                msg=msg, emoji=emoji, color=color, size=DEFAULT_MSG_SIZE, gap=6
            )
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"ok": True, "status": status, "queued": True},
                        ensure_ascii=False,
                    ),
                )
            ]

        if name == "littlebuddy_show":
            fields: dict = {"msg": arguments["msg"]}
            if arguments.get("emoji"):
                fields["emoji"] = arguments["emoji"]
            fields["color"] = arguments.get("color", COLOR_GREEN)
            fields["size"] = int(arguments.get("size", DEFAULT_MSG_SIZE))
            await show_via_daemon(**fields)
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"ok": True, "queued": True}, ensure_ascii=False),
                )
            ]

        raise ValueError(f"未知工具: {name}")
    except (ValueError, RuntimeError, DaemonError) as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False),
            )
        ]


async def _async_main() -> None:
    # Cursor 连接 MCP 时即后台：结束旧 daemon → 连 M5 → 监听 socket
    _spawn_daemon_boot()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()

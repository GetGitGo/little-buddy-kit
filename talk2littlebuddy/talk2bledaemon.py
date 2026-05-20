#!/usr/bin/env python3
"""
经 littlebuddy daemon（Unix socket）显示到 M5，不直连 BLE。

与 talk.py 类似，但走 daemon 已有连接；daemon 运行时可与 Cursor/hook 并存。

环境：
  export LITTLEBUDDY_MCP_DIR=/path/to/little-buddy-kit/.littlebuddy-mcp   # 与 install.md / mcp.json 一致

示例：
  littlebuddy-service start
  python talk2bledaemon.py --msg "一二三四五六七" --emoji brain
  python talk2bledaemon.py --status thinking
  python talk2bledaemon.py --demo
  python talk2bledaemon.py --ping
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("LITTLEBUDDY_MCP_DIR", str(_ROOT / ".littlebuddy-mcp"))

from littlebuddy_mcp.daemon_client import (  # noqa: E402
    DaemonError,
    daemon_request,
    enqueue_show,
    ping_daemon,
    reconnect_daemon,
)
from littlebuddy_mcp.paths import DAEMON_SOCK  # noqa: E402
from littlebuddy_mcp.protocol import (  # noqa: E402
    DEFAULT_MSG_SIZE,
    MAX_MSG_CJK,
    clip_msg,
    cjk_len,
    make_payload,
)
from littlebuddy_mcp.statuses import (  # noqa: E402
    COLOR_GREEN,
    CURSOR_EMOJI_NAMES,
    CURSOR_STATUS_PRESETS,
    LEVEL_COLORS,
)

DEMO_INTERVAL_S = 1.8


def _require_socket() -> None:
    if not DAEMON_SOCK.is_socket():
        raise RuntimeError(
            f"daemon 未运行（无 socket: {DAEMON_SOCK}）。\n"
            "请先: littlebuddy-service start"
        )


def _validate_show_fields(
    msg: str,
    *,
    emoji: str | None,
    size: int,
    color: str,
) -> str:
    if emoji and emoji not in CURSOR_EMOJI_NAMES:
        raise ValueError(
            f"未知 emoji: {emoji!r}，可选: {', '.join(CURSOR_EMOJI_NAMES)}"
        )
    if color not in LEVEL_COLORS:
        raise ValueError(f"color 必须是 {LEVEL_COLORS} 之一，收到 {color!r}")
    if size < 1 or size > 6:
        raise ValueError("size 必须是 1–6")
    m = clip_msg(msg, MAX_MSG_CJK)
    if cjk_len(m) > MAX_MSG_CJK:
        raise ValueError(f"msg 汉字不宜超过 {MAX_MSG_CJK} 字: {msg!r}")
    return m


async def send_show_daemon(
    msg: str,
    *,
    emoji: str | None = None,
    size: int = DEFAULT_MSG_SIZE,
    color: str = COLOR_GREEN,
    gap: int = 6,
) -> dict:
    _require_socket()
    msg = _validate_show_fields(msg, emoji=emoji, size=size, color=color)
    payload = make_payload(msg, emoji=emoji, size=size, color=color, gap=gap)
    await enqueue_show(**payload)
    return payload


async def run_demo() -> None:
    items = list(CURSOR_STATUS_PRESETS.items())
    n = len(items)
    for i, (sid, (msg, emoji, color)) in enumerate(items, 1):
        print(f"\n--- [{i}/{n}] {sid} {emoji} [{color}]: {msg} ---")
        payload = await send_show_daemon(msg, emoji=emoji, size=DEFAULT_MSG_SIZE, color=color)
        print(f"[daemon→M5] {json.dumps(payload, ensure_ascii=False)}")
        await asyncio.sleep(DEMO_INTERVAL_S)
    print(f"\n演示结束（{n} 条预设）。")


async def main() -> None:
    emoji_help = ", ".join(CURSOR_EMOJI_NAMES[:8]) + ", …"
    status_ids = sorted(CURSOR_STATUS_PRESETS.keys())
    parser = argparse.ArgumentParser(
        description="经 daemon socket 测试 little-buddy（不直连 BLE）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--msg", help=f"显示文案（最多 {MAX_MSG_CJK} 汉字）；\\n 为多行")
    parser.add_argument(
        "--status",
        choices=status_ids,
        help="使用 MCP 预设 status（可配合 --msg 覆盖文案）",
    )
    parser.add_argument("--emoji", choices=CURSOR_EMOJI_NAMES, help=f"emoji: {emoji_help}")
    parser.add_argument("--size", type=int, choices=[1, 2, 3, 4, 5, 6], default=DEFAULT_MSG_SIZE)
    parser.add_argument("--color", choices=LEVEL_COLORS, default=COLOR_GREEN)
    parser.add_argument("--gap", type=int, default=6)
    parser.add_argument("--demo", action="store_true", help="按 statuses 预设轮播")
    parser.add_argument("--ping", action="store_true", help="查询 daemon / BLE 状态")
    parser.add_argument("--reconnect", action="store_true", help="让 daemon 重连 BLE")
    parser.add_argument("--scan", action="store_true", help="配合 --reconnect 强制扫描")
    parser.add_argument("--address", metavar="MAC", help="配合 --reconnect 指定地址")
    parser.add_argument("--list-emoji", action="store_true")
    parser.add_argument("--list-statuses", action="store_true")
    args = parser.parse_args()

    if args.list_emoji:
        for name in CURSOR_EMOJI_NAMES:
            print(name)
        return

    if args.list_statuses:
        for sid in status_ids:
            msg, emoji, color = CURSOR_STATUS_PRESETS[sid]
            print(f"{sid}\t{msg}\t{emoji}\t{color}")
        return

    if args.ping:
        _require_socket()
        try:
            resp = await daemon_request("ping", timeout=2.0)
        except DaemonError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        print(json.dumps(resp, ensure_ascii=False, indent=2))
        return

    if args.reconnect:
        _require_socket()
        try:
            resp = await reconnect_daemon(
                force_scan=args.scan,
                address=args.address,
            )
        except DaemonError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        print(json.dumps(resp, ensure_ascii=False, indent=2))
        return

    if args.demo:
        try:
            if not await ping_daemon(timeout=0.8):
                raise RuntimeError("daemon ping 失败")
            await run_demo()
        except (RuntimeError, ValueError) as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        return

    if args.status is not None or args.msg is not None:
        if args.status is not None:
            msg, emoji, color = CURSOR_STATUS_PRESETS[args.status]
            if args.msg is not None:
                msg = args.msg.replace("\\n", "\n")
            if args.emoji is not None:
                emoji = args.emoji
            if any(a.startswith("--color") for a in sys.argv):
                color = args.color
        else:
            msg = args.msg.replace("\\n", "\n")
            emoji = args.emoji
            color = args.color

        try:
            payload = await send_show_daemon(
                msg,
                emoji=emoji,
                size=args.size,
                color=color,
                gap=args.gap,
            )
            print(f"已排队: {json.dumps(payload, ensure_ascii=False)}")
            print(f"socket: {DAEMON_SOCK}")
        except (RuntimeError, ValueError) as e:
            print(e, file=sys.stderr)
            sys.exit(1 if isinstance(e, RuntimeError) else 2)
        return

    parser.print_help()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCtrl+C 退出。")

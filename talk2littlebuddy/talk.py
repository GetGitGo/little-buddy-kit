#!/usr/bin/env python3
"""
little-buddy 显示协议（Windows / macOS / Linux 用法相同）：

  {"msg":"文案","emoji":"rocket","size":4,"color":"green","gap":6,"datetime":"2026-5-17 10:06"}

color：green / yellow / red。背景固定黑底，协议无 bg。
emoji：见 EMOJI_NAMES（70 个，Twemoji 40×40 位图）

依赖：pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime

from bleak import BleakClient
from bleak.exc import BleakError

from little_ble import (
    NUS_RX_CHAR_UUID,
    NUS_TX_CHAR_UUID,
    find_little_device,
    resolve_connect_target,
    save_last_device,
)

EMOJI_NAMES = (
    # 原有 10
    "rocket",
    "fire",
    "check",
    "cross",
    "warn",
    "computer",
    "bug",
    "coffee",
    "thumbsup",
    "eyes",
    # 新增 20
    "gear",
    "hammer",
    "wrench",
    "package",
    "merge",
    "branch",
    "lock",
    "passkey",
    "shield",
    "zap",
    "hourglass",
    "stop",
    "recycle",
    "memo",
    "link",
    "save",
    "robot",
    "chartup",
    "chartdown",
    "target",
    # 第二批 +20
    "clipboard",
    "bell",
    "calendar",
    "alarm",
    "timer",
    "inbox",
    "outbox",
    "email",
    "phone",
    "globe",
    "cloud",
    "storage",
    "testtube",
    "microscope",
    "megaphone",
    "wip",
    "party",
    "siren",
    "sparkles",
    "search",
    # Cursor / Claude Code 状态 +20
    "brain",
    "thought",
    "bulb",
    "wand",
    "plug",
    "pause",
    "retry",
    "blocked",
    "pin",
    "book",
    "puzzle",
    "crystal",
    "agent",
    "stream",
    "chat",
    "notebook",
    "trophy",
    "broom",
    "pencil",
    "scroll",
)

COLOR_GREEN = "green"
COLOR_YELLOW = "yellow"
COLOR_RED = "red"
LEVEL_COLORS = (COLOR_GREEN, COLOR_YELLOW, COLOR_RED)

# (msg, emoji, color) — msg 不超过 4 个汉字
EMOJI_DEMOS: tuple[tuple[str, str, str], ...] = (
    ("发布上线", "rocket", COLOR_GREEN),
    ("性能拉满", "fire", COLOR_YELLOW),
    ("测试通过", "check", COLOR_GREEN),
    ("编译失败", "cross", COLOR_RED),
    ("磁盘将满", "warn", COLOR_YELLOW),
    ("正在构建", "computer", COLOR_GREEN),
    ("程序出错", "bug", COLOR_RED),
    ("休息一下", "coffee", COLOR_GREEN),
    ("给你点赞", "thumbsup", COLOR_GREEN),
    ("请审代码", "eyes", COLOR_YELLOW),
    ("正在配置", "gear", COLOR_GREEN),
    ("紧急修复", "hammer", COLOR_YELLOW),
    ("调试一下", "wrench", COLOR_YELLOW),
    ("构建完成", "package", COLOR_GREEN),
    ("合并成功", "merge", COLOR_GREEN),
    ("新建分支", "branch", COLOR_GREEN),
    ("仓库锁定", "lock", COLOR_YELLOW),
    ("密钥就绪", "passkey", COLOR_GREEN),
    ("安全防护", "shield", COLOR_GREEN),
    ("性能爆表", "zap", COLOR_YELLOW),
    ("排队等待", "hourglass", COLOR_YELLOW),
    ("任务停止", "stop", COLOR_RED),
    ("重新部署", "recycle", COLOR_YELLOW),
    ("更新文档", "memo", COLOR_GREEN),
    ("链路正常", "link", COLOR_GREEN),
    ("数据落盘", "save", COLOR_GREEN),
    ("自动执行", "robot", COLOR_GREEN),
    ("指标上涨", "chartup", COLOR_GREEN),
    ("指标下跌", "chartdown", COLOR_RED),
    ("目标达成", "target", COLOR_GREEN),
    ("复制好了", "clipboard", COLOR_GREEN),
    ("有新通知", "bell", COLOR_YELLOW),
    ("日程已满", "calendar", COLOR_YELLOW),
    ("快到点了", "alarm", COLOR_YELLOW),
    ("请求超时", "timer", COLOR_RED),
    ("收到消息", "inbox", COLOR_GREEN),
    ("已经发出", "outbox", COLOR_GREEN),
    ("未读邮件", "email", COLOR_YELLOW),
    ("电话找你", "phone", COLOR_YELLOW),
    ("全网可达", "globe", COLOR_GREEN),
    ("同步云端", "cloud", COLOR_GREEN),
    ("写入存储", "storage", COLOR_GREEN),
    ("单元测试", "testtube", COLOR_GREEN),
    ("深入排查", "microscope", COLOR_YELLOW),
    ("全员通知", "megaphone", COLOR_YELLOW),
    ("维护当中", "wip", COLOR_YELLOW),
    ("版本庆祝", "party", COLOR_GREEN),
    ("严重告警", "siren", COLOR_RED),
    ("亮点功能", "sparkles", COLOR_GREEN),
    ("全文检索", "search", COLOR_GREEN),
    # Cursor / Claude Code 常见状态
    ("正在思考", "brain", COLOR_YELLOW),
    ("深度推理", "thought", COLOR_YELLOW),
    ("突然想到", "bulb", COLOR_GREEN),
    ("一键修好", "wand", COLOR_GREEN),
    ("调用工具", "plug", COLOR_GREEN),
    ("稍等一下", "pause", COLOR_YELLOW),
    ("正在重试", "retry", COLOR_YELLOW),
    ("操作取消", "blocked", COLOR_RED),
    ("钉住上文", "pin", COLOR_YELLOW),
    ("查阅资料", "book", COLOR_GREEN),
    ("拆解问题", "puzzle", COLOR_YELLOW),
    ("制定计划", "crystal", COLOR_GREEN),
    ("代理执行", "agent", COLOR_GREEN),
    ("流式输出", "stream", COLOR_GREEN),
    ("继续对话", "chat", COLOR_GREEN),
    ("记录会话", "notebook", COLOR_GREEN),
    ("圆满完成", "trophy", COLOR_GREEN),
    ("整理代码", "broom", COLOR_GREEN),
    ("生成代码", "pencil", COLOR_GREEN),
    ("应用修改", "scroll", COLOR_GREEN),
)

DEMO_INTERVAL_S = 1.8

PAIRING_HINT = """
连接失败（含 CBError 14 配对信息过期）：
  macOS：系统设置 → 蓝牙 → 设备 ⓘ → 忽略此设备
  Windows：设置 → 蓝牙和其他设备 → 找到设备 → 删除/移除
  然后重新上电 M5，再运行 python talk.py
"""


def _cjk_len(msg: str) -> int:
    return sum(1 for c in msg if "\u4e00" <= c <= "\u9fff")


def format_device_datetime(when: datetime | None = None) -> str:
    """设备屏显用本地时间，形如 2026-5-17 10:06（月日时不补零，分补零）。"""
    dt = when or datetime.now()
    return f"{dt.year}-{dt.month}-{dt.day} {dt.hour}:{dt.minute:02d}"


def make_payload(
    msg: str,
    *,
    emoji: str | None = None,
    size: int = 4,
    color: str = COLOR_GREEN,
    gap: int = 6,
    datetime: str | None = None,
) -> dict:
    if color not in LEVEL_COLORS:
        raise ValueError(f"color 必须是 {LEVEL_COLORS} 之一，收到 {color!r}")
    p: dict = {
        "msg": msg,
        "size": size,
        "color": color,
        "gap": gap,
        "datetime": datetime if datetime is not None else format_device_datetime(),
    }
    if emoji:
        p["emoji"] = emoji
    return p


async def send_show(client: BleakClient, **kwargs) -> None:
    if kwargs.get("emoji") and kwargs["emoji"] not in EMOJI_NAMES:
        raise ValueError(f"未知 emoji: {kwargs['emoji']!r}，可选: {', '.join(EMOJI_NAMES)}")
    msg = kwargs.get("msg", "")
    if _cjk_len(msg) > 4:
        raise ValueError(f"msg 汉字不宜超过 4 字（当前 {_cjk_len(msg)}）: {msg!r}")
    payload = make_payload(**kwargs)
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n"
    await client.write_gatt_char(NUS_RX_CHAR_UUID, line.encode("utf-8"), response=False)
    print(f"[host→M5] {line.strip()}")


# Cursor / Claude Code 状态 emoji（与 EMOJI_DEMOS 中 AI 段一致）
CURSOR_EMOJI_NAMES: tuple[str, ...] = (
    "brain",
    "thought",
    "bulb",
    "wand",
    "plug",
    "pause",
    "retry",
    "blocked",
    "pin",
    "book",
    "puzzle",
    "crystal",
    "agent",
    "stream",
    "chat",
    "notebook",
    "trophy",
    "broom",
    "pencil",
    "scroll",
)

# MCP / IDE 状态预设：id → (msg, emoji, color)
CURSOR_STATUS_PRESETS: dict[str, tuple[str, str, str]] = {
    "thinking": ("正在思考", "brain", COLOR_YELLOW),
    "reasoning": ("深度推理", "thought", COLOR_YELLOW),
    "idea": ("突然想到", "bulb", COLOR_GREEN),
    "autofix": ("一键修好", "wand", COLOR_GREEN),
    "tool": ("调用工具", "plug", COLOR_GREEN),
    "pause": ("稍等一下", "pause", COLOR_YELLOW),
    "retry": ("正在重试", "retry", COLOR_YELLOW),
    "cancelled": ("操作取消", "blocked", COLOR_RED),
    "context_pin": ("钉住上文", "pin", COLOR_YELLOW),
    "read_docs": ("查阅资料", "book", COLOR_GREEN),
    "decompose": ("拆解问题", "puzzle", COLOR_YELLOW),
    "plan": ("制定计划", "crystal", COLOR_GREEN),
    "agent": ("代理执行", "agent", COLOR_GREEN),
    "streaming": ("流式输出", "stream", COLOR_GREEN),
    "chatting": ("继续对话", "chat", COLOR_GREEN),
    "session": ("记录会话", "notebook", COLOR_GREEN),
    "done": ("圆满完成", "trophy", COLOR_GREEN),
    "format": ("整理代码", "broom", COLOR_GREEN),
    "generating": ("生成代码", "pencil", COLOR_GREEN),
    "applying": ("应用修改", "scroll", COLOR_GREEN),
}


async def display_message(
    msg: str,
    *,
    emoji: str | None = None,
    size: int = 4,
    color: str = COLOR_GREEN,
    gap: int = 6,
    address: str | None = None,
    force_scan: bool = False,
    allow_any_nus: bool = False,
) -> dict:
    """连接 little-buddy 并发送一条显示（供 MCP / 脚本复用）。"""
    target = await resolve_connect_target(
        address=address,
        force_scan=force_scan,
        allow_any_nus=allow_any_nus,
    )
    if not target:
        raise RuntimeError("未找到 little-buddy 设备。可先运行 talk.py --scan")

    addr, label = target
    last_err: BleakError | None = None

    async def _once() -> dict:
        async with BleakClient(addr, timeout=15.0, pair=False) as client:
            save_last_device(label, addr)
            await send_show(
                client,
                msg=msg,
                emoji=emoji,
                size=size,
                color=color,
                gap=gap,
            )
        return make_payload(msg, emoji=emoji, size=size, color=color, gap=gap)

    for attempt in range(2):
        try:
            return await _once()
        except BleakError as e:
            last_err = e
            if attempt == 0 and "pairing" in str(e).lower():
                await asyncio.sleep(3)
                continue
            break

    raise RuntimeError(f"BLE 连接失败: {last_err}")


def _explain_connect_error(exc: BaseException) -> None:
    if "pairing" in str(exc).lower() or "Code=14" in str(exc):
        print(PAIRING_HINT, file=sys.stderr)
    else:
        print(f"连接错误: {exc}", file=sys.stderr)


async def run_demo(client: BleakClient) -> None:
    n = len(EMOJI_DEMOS)
    for i, (msg, emoji, color) in enumerate(EMOJI_DEMOS, 1):
        print(f"\n--- [{i}/{n}] {emoji} [{color}]: {msg} ---")
        await send_show(
            client,
            msg=msg,
            emoji=emoji,
            size=4,
            color=color,
            gap=6,
        )
        await asyncio.sleep(DEMO_INTERVAL_S)
    print(f"\n演示结束（{n}/{n} emoji）。")


async def main() -> None:
    emoji_help = ", ".join(EMOJI_NAMES)
    color_help = " / ".join(LEVEL_COLORS)
    parser = argparse.ArgumentParser(
        description="BLE 测试 little-buddy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--msg", help="显示文案（建议≤4汉字）；\\n 为多行")
    parser.add_argument("--emoji", choices=EMOJI_NAMES, help=f"位图 emoji: {emoji_help}")
    parser.add_argument("--size", type=int, choices=[1, 2, 3, 4, 5, 6], default=4)
    parser.add_argument(
        "--color",
        choices=LEVEL_COLORS,
        default=COLOR_GREEN,
        help=f"重要程度颜色: {color_help}",
    )
    parser.add_argument("--gap", type=int, default=6)
    parser.add_argument("--address", metavar="MAC", help="指定地址直连（不扫描）")
    parser.add_argument(
        "--scan",
        action="store_true",
        help="强制 BLE 扫描（默认用上次成功地址直连）",
    )
    parser.add_argument("--any-nus", action="store_true")
    parser.add_argument("--list-emoji", action="store_true", help="列出 emoji 名称并退出")
    args = parser.parse_args()

    if args.list_emoji:
        for name in EMOJI_NAMES:
            print(name)
        return

    if args.msg is not None:
        msg = args.msg.replace("\\n", "\n")
        try:
            payload = await display_message(
                msg,
                emoji=args.emoji,
                size=args.size,
                color=args.color,
                gap=args.gap,
                address=args.address,
                force_scan=args.scan,
                allow_any_nus=args.any_nus,
            )
            print(f"已发送: {payload}")
        except (RuntimeError, ValueError) as e:
            print(e, file=sys.stderr)
            sys.exit(1 if isinstance(e, RuntimeError) else 2)
        return

    target = await resolve_connect_target(
        address=args.address,
        force_scan=args.scan,
        allow_any_nus=args.any_nus,
    )
    if not target:
        print("未找到设备。可运行: python scan.py 或 python talk.py --scan")
        return

    async def _use_client(client: BleakClient) -> None:
        try:
            await client.start_notify(
                NUS_TX_CHAR_UUID,
                lambda _s, data: print(f"[M5→host] {data!r}"),
            )
        except Exception as e:
            print(f"[warn] 未订阅 TX: {e}")
        await run_demo(client)

    async def _try_connect(connect_addr: str, connect_label: str) -> bool:
        print(f"连接 {connect_label} @ {connect_addr}…")
        try:
            async with BleakClient(connect_addr, timeout=15.0, pair=False) as client:
                save_last_device(connect_label, connect_addr)
                await _use_client(client)
            return True
        except BleakError as e:
            nonlocal last_err
            last_err = e
            return False

    addr, label = target
    last_err: BleakError | None = None

    if await _try_connect(addr, label):
        return
    if last_err and "pairing" in str(last_err).lower():
        print("\n[重试] 请先在蓝牙设置中忽略该设备…")
        await asyncio.sleep(3)
        if await _try_connect(addr, label):
            return

    if not args.scan and not args.address:
        print("直连失败，改为扫描…")
        found = await find_little_device(allow_any_nus=args.any_nus)
        if found:
            addr, label = found[0].address, found[1]
            if await _try_connect(addr, label):
                return

    if last_err:
        _explain_connect_error(last_err)
        sys.exit(1)
    print("未找到设备。", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCtrl+C 退出。")
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(2)

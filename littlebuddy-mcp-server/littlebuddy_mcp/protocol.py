"""little-buddy 显示协议：JSON 行经 NUS RX 下发。"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from bleak import BleakClient
from bleak.exc import BleakError

from .ble import NUS_RX_CHAR_UUID, resolve_connect_target, save_last_device
from .statuses import COLOR_GREEN, CURSOR_EMOJI_NAMES, LEVEL_COLORS

MAX_MSG_CJK = 7
DEFAULT_MSG_SIZE = 4


def cjk_len(msg: str) -> int:
    return sum(1 for c in msg if "\u4e00" <= c <= "\u9fff")


def clip_msg(msg: str, max_cjk: int = MAX_MSG_CJK) -> str:
    """截断到最多 max_cjk 个汉字（非汉字不计入限额）。"""
    n = 0
    out: list[str] = []
    for c in msg:
        if "\u4e00" <= c <= "\u9fff":
            if n >= max_cjk:
                break
            n += 1
        out.append(c)
    return "".join(out)


def format_device_datetime(when: datetime | None = None) -> str:
    """设备屏显用本地时间，形如 2026-5-17 10:06（月日时不补零，分补零）。"""
    dt = when or datetime.now()
    return f"{dt.year}-{dt.month}-{dt.day} {dt.hour}:{dt.minute:02d}"


def make_payload(
    msg: str,
    *,
    emoji: str | None = None,
    size: int = DEFAULT_MSG_SIZE,
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


async def send_show(client: BleakClient, **kwargs) -> dict:
    if kwargs.get("emoji") and kwargs["emoji"] not in CURSOR_EMOJI_NAMES:
        raise ValueError(
            f"未知 emoji: {kwargs['emoji']!r}，可选: {', '.join(CURSOR_EMOJI_NAMES)}"
        )
    msg = kwargs.get("msg", "")
    if cjk_len(msg) > MAX_MSG_CJK:
        raise ValueError(
            f"msg 汉字不宜超过 {MAX_MSG_CJK} 字（当前 {cjk_len(msg)}）: {msg!r}"
        )
    payload = make_payload(**kwargs)
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n"
    await client.write_gatt_char(NUS_RX_CHAR_UUID, line.encode("utf-8"), response=False)
    return payload


async def display_message(
    msg: str,
    *,
    emoji: str | None = None,
    size: int = DEFAULT_MSG_SIZE,
    color: str = COLOR_GREEN,
    gap: int = 6,
    address: str | None = None,
    force_scan: bool = False,
    allow_any_nus: bool = False,
) -> dict:
    target = await resolve_connect_target(
        address=address,
        force_scan=force_scan,
        allow_any_nus=allow_any_nus,
    )
    if not target:
        raise RuntimeError(
            "未找到 little-buddy。请确认设备显示 BLE wait，或调用时设 force_scan=true"
        )

    addr, label = target
    last_err: BleakError | None = None

    async def _once() -> dict:
        async with BleakClient(addr, timeout=15.0, pair=False) as client:
            save_last_device(label, addr)
            return await send_show(
                client,
                msg=msg,
                emoji=emoji,
                size=size,
                color=color,
                gap=gap,
            )

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

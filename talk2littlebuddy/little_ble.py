"""little-buddy BLE 扫描识别（名称 + 广播 manufacturer 标签）。"""

from __future__ import annotations

import sys
from pathlib import Path

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

_LAST_DEVICE_FILE = Path(__file__).resolve().parent / ".last_device"

NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

# 与 little-buddy/src/ble_bridge.cpp 一致
LB_MFG_COMPANY_ID = 0xFFFF
LB_MFG_PAYLOAD = b"LB01"

_PROBE_TIMEOUT_S = 10.0


def has_lb_mfg(adv) -> bool:
    mfg = getattr(adv, "manufacturer_data", None) or {}
    for cid, data in mfg.items():
        if cid == LB_MFG_COMPANY_ID and data == LB_MFG_PAYLOAD:
            return True
        if LB_MFG_PAYLOAD in data:
            return True
    return False


def names_for(device, adv) -> tuple[str, str, str]:
    """(cached_name, local_name, label_for_print)"""
    cached = (device.name or "").strip()
    local = (getattr(adv, "local_name", None) or "").strip()
    label = local or cached or "(no name)"
    return cached, local, label


def is_little_buddy(device, adv) -> bool:
    cached, local, _ = names_for(device, adv)
    if local.startswith("Little") or cached.startswith("Little"):
        return True
    return has_lb_mfg(adv)


def is_claude_buddy(device, adv) -> bool:
    cached, local, _ = names_for(device, adv)
    label = local or cached
    return label.startswith("Claude")


def _has_nus(adv) -> bool:
    uuids = [s.lower() for s in getattr(adv, "service_uuids", []) or []]
    return NUS_SERVICE_UUID in uuids


def _adv_rssi(adv) -> int:
    rssi = getattr(adv, "rssi", None)
    if rssi is None:
        return -128
    try:
        return int(rssi)
    except (TypeError, ValueError):
        return -128


def _pick_strongest_little(
    little: list[tuple[object, str, object]],
) -> tuple[object, str, int] | None:
    if not little:
        return None
    device, label, adv = max(little, key=lambda row: _adv_rssi(row[2]))
    return device, label, _adv_rssi(adv)


async def probe_connect(address: str, *, timeout: float = _PROBE_TIMEOUT_S) -> bool:
    try:
        async with BleakClient(address, timeout=timeout, pair=False) as client:
            return client.is_connected
    except BleakError:
        return False


async def find_little_device(
    timeout: float = 15.0,
    *,
    allow_any_nus: bool = False,
    address: str | None = None,
):
    devices = await BleakScanner.discover(return_adv=True, timeout=timeout)
    little: list[tuple[object, str, object]] = []
    other_nus: list[tuple[object, str, object]] = []

    for _uuid, (device, adv) in devices.items():
        if address and device.address.lower() != address.lower():
            continue
        _cached, _local, label = names_for(device, adv)
        if is_little_buddy(device, adv):
            little.append((device, label, adv))
        elif _has_nus(adv):
            other_nus.append((device, label, adv))

    if address:
        for device, label, _adv in little:
            return device, label
        for device, label, adv in other_nus:
            if allow_any_nus:
                print(
                    f"[warn] {address} 为 {label!r}（buddy），非 little-buddy",
                    file=sys.stderr,
                )
                return device, label
            print(
                f"{address} 仍是 buddy（{label!r}），无 LB01 标签。\n"
                "  请确认屏幕为「BLE wait」并执行:\n"
                "    cd ../little-buddy && pio run -t erase && pio run -t upload",
                file=sys.stderr,
            )
            return None
        print(f"未找到地址 {address!r} 的 NUS 设备。", file=sys.stderr)
        return None

    picked = _pick_strongest_little(little)
    if picked:
        device, label, rssi = picked
        if len(little) > 1:
            print(
                f"扫描到 {len(little)} 台 little-buddy，选 RSSI 最强 "
                f"({rssi} dBm): {label} @ {device.address}",  # type: ignore[attr-defined]
                file=sys.stderr,
            )
        return device, label

    if allow_any_nus and other_nus:
        print(
            f"[warn] 使用 {other_nus[0][1]!r} @ {other_nus[0][0].address}",  # type: ignore[attr-defined]
            file=sys.stderr,
        )
        return other_nus[0][0], other_nus[0][1]

    if other_nus:
        print("扫描到 NUS，但无 little-buddy 特征：", file=sys.stderr)
        for device, label, adv in other_nus:
            print(f"  - {label} @ {device.address}", file=sys.stderr)  # type: ignore[attr-defined]
            print(f"    {format_adv_debug(device, adv)}", file=sys.stderr)
    return None


def load_last_device() -> tuple[str, str] | None:
    """(label, address)"""
    if not _LAST_DEVICE_FILE.is_file():
        return None
    lines = [
        ln.strip()
        for ln in _LAST_DEVICE_FILE.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if len(lines) >= 2:
        return lines[0], lines[1]
    if len(lines) == 1:
        return "Little", lines[0]
    return None


def save_last_device(label: str, address: str) -> None:
    _LAST_DEVICE_FILE.write_text(f"{label}\n{address}\n", encoding="utf-8")


async def _scan_and_pick(
    *,
    allow_any_nus: bool = False,
    address: str | None = None,
    verbose: bool = True,
) -> tuple[str, str] | None:
    if verbose:
        print("扫描 little-buddy…")
    found = await find_little_device(allow_any_nus=allow_any_nus, address=address)
    if not found:
        return None
    device, label = found
    addr = device.address  # type: ignore[attr-defined]
    save_last_device(label, addr)
    return addr, label


async def resolve_connect_target(
    *,
    address: str | None = None,
    force_scan: bool = False,
    allow_any_nus: bool = False,
) -> tuple[str, str] | None:
    """
    返回 (ble_address, label)。

    策略：
    1. 指定 address（且非 force_scan）→ 使用该地址
    2. force_scan 或仅指定 address 且 force_scan → 扫描；多台 RSSI 最强
    3. last_device 存在且探测可连 → 用缓存
    4. 否则扫描；仅一台用该台，多台 RSSI 最强
    """
    if address and not force_scan:
        print(f"直连指定地址: {address}")
        return address, address

    if force_scan or address:
        return await _scan_and_pick(allow_any_nus=allow_any_nus, address=address)

    cached = load_last_device()
    if cached:
        label, addr = cached
        if await probe_connect(addr):
            print(f"直连缓存: {label} @ {addr}")
            return addr, label
        print(f"缓存不可达 {label} @ {addr}，重新扫描…", file=sys.stderr)

    return await _scan_and_pick(allow_any_nus=allow_any_nus)


def format_adv_debug(device, adv) -> str:
    cached, local, _ = names_for(device, adv)
    parts = [f"label={local or cached or '?'!r}"]
    if cached and local and cached != local:
        parts.append(f"cached={cached!r}")
        parts.append(f"local={local!r}")
    if has_lb_mfg(adv):
        parts.append("mfg=LB01")
    rssi = getattr(adv, "rssi", None)
    if rssi is not None:
        parts.append(f"rssi={rssi}")
    return "  ".join(parts)

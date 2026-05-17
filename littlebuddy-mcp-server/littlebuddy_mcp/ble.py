"""little-buddy BLE 扫描与连接（与 little-buddy 固件 NUS / LB01 一致）。"""

from __future__ import annotations

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

from .paths import CACHE_DIR, LAST_DEVICE_FILE

NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

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
    cached = (device.name or "").strip()
    local = (getattr(adv, "local_name", None) or "").strip()
    label = local or cached or "(no name)"
    return cached, local, label


def is_little_buddy(device, adv) -> bool:
    cached, local, _ = names_for(device, adv)
    if local.startswith("Little") or cached.startswith("Little"):
        return True
    return has_lb_mfg(adv)


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
) -> tuple[object, str] | None:
    if not little:
        return None
    device, label, _adv = max(little, key=lambda row: _adv_rssi(row[2]))
    return device, label


async def probe_connect(address: str, *, timeout: float = _PROBE_TIMEOUT_S) -> bool:
    """短时连接探测地址是否可达（成功后断开）。"""
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
        for device, label, _adv in other_nus:
            if allow_any_nus:
                return device, label
        return None

    picked = _pick_strongest_little(little)
    if picked:
        return picked

    if allow_any_nus and other_nus:
        device, label, _adv = other_nus[0]
        return device, label

    return None


def load_last_device() -> tuple[str, str] | None:
    if not LAST_DEVICE_FILE.is_file():
        return None
    lines = [
        ln.strip()
        for ln in LAST_DEVICE_FILE.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    if len(lines) >= 2:
        return lines[0], lines[1]
    if len(lines) == 1:
        return "Little", lines[0]
    return None


def save_last_device(label: str, address: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_DEVICE_FILE.write_text(f"{label}\n{address}\n", encoding="utf-8")


async def _scan_and_pick(
    *,
    allow_any_nus: bool = False,
    address: str | None = None,
) -> tuple[str, str] | None:
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
    1. 指定 address → 使用该地址（不探测缓存）
    2. force_scan → 扫描；多台时 RSSI 最强
    3. 有 last_device 且探测可连 → 用缓存
    4. 否则扫描；仅一台用该台，多台用 RSSI 最强
    """
    if address and not force_scan:
        return address, address

    if force_scan or address:
        return await _scan_and_pick(allow_any_nus=allow_any_nus, address=address)

    cached = load_last_device()
    if cached:
        label, addr = cached
        if await probe_connect(addr):
            return addr, label

    return await _scan_and_pick(allow_any_nus=allow_any_nus)

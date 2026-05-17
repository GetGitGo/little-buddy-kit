import asyncio

from bleak import BleakScanner

from little_ble import (
    format_adv_debug,
    is_claude_buddy,
    is_little_buddy,
    names_for,
    _has_nus,
)


async def main() -> None:
    print("扫描 NUS 设备（little-buddy: Little-* 或广播 mfg LB01）…")
    devices = await BleakScanner.discover(return_adv=True, timeout=15.0)

    little = []
    buddy = []
    other = []

    for _uuid, (device, adv) in devices.items():
        cached, local, label = names_for(device, adv)
        row = (label, device.address, adv.rssi, cached, local, format_adv_debug(device, adv))
        if is_little_buddy(device, adv):
            little.append(row)
        elif _has_nus(adv):
            if is_claude_buddy(device, adv):
                buddy.append(row)
            else:
                other.append(row)

    if little:
        print("\n=== little-buddy（talk.py 会连）===")
        for label, addr, rssi, _c, _l, dbg in little:
            print("-" * 50)
            print(f"  {label}")
            print(f"  {dbg}")
            print(f"  地址: {addr}")
            print(f"  RSSI: {rssi} dBm")

    if buddy:
        print("\n=== claude-desktop-buddy（需改烧 little-buddy）===")
        for label, addr, rssi, cached, local, dbg in buddy:
            print(f"  {label} @ {addr}  RSSI {rssi} dBm")
            print(f"    {dbg}")
            if cached.startswith("Claude") and local.startswith("Little"):
                print("    → local_name 已是 Little，但系统缓存名仍为 Claude；可 python talk.py --address ...")

    if not little:
        print("\n未发现 little-buddy。")
        print("  1. 看屏幕：应为「BLE wait」（不是宠物/时钟）")
        print("  2. 串口: pio device monitor — 应有「=== Little Buddy ===」")
        print("  3. 擦除重烧:")
        print("       cd ../little-buddy && pio run -t erase && pio run -t upload")
        print("  4. 确认 USB 口（Stick S3 两个口，用能上传的那个）")

    if other:
        print("\n=== 其它 NUS ===")
        for label, addr, rssi, *_ in other:
            print(f"  {label} @ {addr}  RSSI {rssi} dBm")

    if not little and not buddy and not other:
        print("附近未发现 BLE 设备（检查 Mac 蓝牙/权限，或延长扫描）。")


if __name__ == "__main__":
    asyncio.run(main())

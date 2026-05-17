#!/usr/bin/env python3
"""常驻 BLE 守护进程：启动时连接 M5，经 Unix socket 接收显示请求。"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError

from .ble import resolve_connect_target, save_last_device
from .paths import CACHE_DIR, DAEMON_LOG, DAEMON_PID_FILE, DAEMON_SOCK
from .protocol import send_show
from .service import kill_existing_daemon

log = logging.getLogger("littlebuddy.daemon")


class BleHub:
    def __init__(self) -> None:
        self._client: BleakClient | None = None
        self._addr: str | None = None
        self._label: str | None = None
        self._io_lock = asyncio.Lock()
        self._pending: dict[str, Any] | None = None
        self._waiters: list[asyncio.Future[dict]] = []
        self._flush_task: asyncio.Task[None] | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def connect(
        self,
        *,
        address: str | None = None,
        force_scan: bool = False,
        allow_any_nus: bool = False,
    ) -> dict:
        async with self._io_lock:
            await self._disconnect_unlocked()
            target = await resolve_connect_target(
                address=address,
                force_scan=force_scan,
                allow_any_nus=allow_any_nus,
            )
            if not target:
                raise RuntimeError(
                    "未找到 little-buddy。请确认 M5 显示 BLE wait，或 --scan"
                )
            addr, label = target
            last_err: BleakError | None = None
            for attempt in range(2):
                try:
                    client = BleakClient(addr, timeout=15.0, pair=False)
                    await client.connect()
                    self._client = client
                    self._addr = addr
                    self._label = label
                    save_last_device(label, addr)
                    log.info("BLE 已连接 %s @ %s", label, addr)
                    return {"address": addr, "label": label}
                except BleakError as e:
                    last_err = e
                    if attempt == 0 and "pairing" in str(e).lower():
                        await asyncio.sleep(3)
                        continue
                    break
            raise RuntimeError(f"BLE 连接失败: {last_err}")

    async def _disconnect_unlocked(self) -> None:
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._client = None

    async def disconnect(self) -> None:
        async with self._io_lock:
            await self._disconnect_unlocked()

    async def _send_show_unlocked(self, **kwargs: Any) -> dict:
        if not self.connected:
            await self._connect_unlocked(address=self._addr)
        assert self._client is not None
        try:
            return await send_show(self._client, **kwargs)
        except BleakError as e:
            log.warning("BLE 发送失败: %s", e)
            raise RuntimeError(f"BLE 发送失败: {e}") from e

    async def _connect_unlocked(
        self,
        *,
        address: str | None = None,
        force_scan: bool = False,
        allow_any_nus: bool = False,
    ) -> None:
        target = await resolve_connect_target(
            address=address,
            force_scan=force_scan,
            allow_any_nus=allow_any_nus,
        )
        if not target:
            raise RuntimeError("未找到 little-buddy。请确认 M5 显示 BLE wait，或 --scan")
        addr, label = target
        client = BleakClient(addr, timeout=15.0, pair=False)
        await client.connect()
        self._client = client
        self._addr = addr
        self._label = label
        save_last_device(label, addr)

    def _schedule_flush(self) -> None:
        if self._flush_task is not None and not self._flush_task.done():
            return
        self._flush_task = asyncio.create_task(self._run_flush())

    async def _run_flush(self) -> None:
        try:
            while self._pending is not None:
                batch = self._pending
                self._pending = None
                waiters = self._waiters
                self._waiters = []
                try:
                    async with self._io_lock:
                        result = await self._send_show_unlocked(**batch)
                except Exception as e:
                    for w in waiters:
                        if not w.done():
                            w.set_exception(e)
                    if self._pending is None:
                        break
                    continue
                for w in waiters:
                    if not w.done():
                        w.set_result(result)
        finally:
            if self._pending is not None:
                self._schedule_flush()

    async def show(self, **kwargs: Any) -> dict:
        """合并并发 show：只保留最新一条，逐批刷新到设备。"""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict] = loop.create_future()
        self._pending = dict(kwargs)
        self._waiters.append(fut)
        self._schedule_flush()
        return await fut

    def status(self) -> dict:
        return {
            "connected": self.connected,
            "address": self._addr,
            "label": self._label,
        }


async def _handle_request(hub: BleHub, raw: bytes) -> dict:
    try:
        req = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"无效 JSON: {e}"}

    op = req.get("op")
    try:
        if op == "ping":
            return {"ok": True, "pid": os.getpid(), **hub.status()}
        if op == "status":
            return {"ok": True, **hub.status()}
        if op == "reconnect":
            info = await hub.connect(
                address=req.get("address"),
                force_scan=bool(req.get("force_scan", False)),
                allow_any_nus=bool(req.get("allow_any_nus", False)),
            )
            return {"ok": True, **info}
        if op == "shutdown":
            asyncio.get_running_loop().call_soon(
                lambda: os.kill(os.getpid(), signal.SIGTERM)
            )
            return {"ok": True}
        return {"ok": False, "error": f"未知 op: {op!r}"}
    except (ValueError, RuntimeError) as e:
        return {"ok": False, "error": str(e)}


def _parse_show_fields(req: dict) -> dict[str, Any] | None:
    fields = {
        k: req[k]
        for k in ("msg", "emoji", "size", "color", "gap", "datetime")
        if k in req and req[k] is not None
    }
    if "msg" not in fields:
        return None
    return fields


async def _client_handler(
    hub: BleHub, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    try:
        line = await reader.readline()
        if not line:
            return
        try:
            req = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            return

        if req.get("op") == "show":
            fields = _parse_show_fields(req)
            if fields is not None:
                asyncio.create_task(hub.show(**fields))
            return

        resp = await _handle_request(hub, line)
        writer.write((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
        await writer.drain()
    except Exception:
        log.exception("请求处理异常")
        err = {"ok": False, "error": "internal error"}
        writer.write((json.dumps(err, ensure_ascii=False) + "\n").encode("utf-8"))
        await writer.drain()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def _run_server(hub: BleHub) -> None:
    if DAEMON_SOCK.exists():
        DAEMON_SOCK.unlink()
    server = await asyncio.start_unix_server(
        lambda r, w: asyncio.create_task(_client_handler(hub, r, w)),
        path=str(DAEMON_SOCK),
    )
    log.info("监听 %s", DAEMON_SOCK)
    async with server:
        await server.serve_forever()


async def _async_main(*, force_scan: bool, address: str | None) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(DAEMON_LOG, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )

    killed = kill_existing_daemon()
    if killed:
        log.info("已终止旧 daemon pid=%s", killed)

    DAEMON_PID_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    hub = BleHub()
    await hub.connect(address=address, force_scan=force_scan)
    await _run_server(hub)


def main() -> None:
    parser = argparse.ArgumentParser(description="little-buddy BLE 常驻守护进程")
    parser.add_argument("--scan", action="store_true", help="启动时强制 BLE 扫描")
    parser.add_argument("--address", help="指定 BLE 地址")
    args = parser.parse_args()

    try:
        asyncio.run(_async_main(force_scan=args.scan, address=args.address))
    except KeyboardInterrupt:
        pass
    finally:
        if DAEMON_SOCK.exists():
            try:
                DAEMON_SOCK.unlink()
            except OSError:
                pass
        if DAEMON_PID_FILE.exists():
            try:
                if int(DAEMON_PID_FILE.read_text().strip()) == os.getpid():
                    DAEMON_PID_FILE.unlink()
            except (ValueError, OSError):
                pass


if __name__ == "__main__":
    main()

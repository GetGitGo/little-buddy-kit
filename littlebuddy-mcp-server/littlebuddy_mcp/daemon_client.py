"""与常驻 daemon 通信（Unix socket，JSON 行协议）。"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from .paths import DAEMON_SOCK

_DEFAULT_TIMEOUT = 2.0
_START_TIMEOUT = 45.0


class DaemonError(RuntimeError):
    pass


async def _open_connection() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    if not DAEMON_SOCK.is_socket():
        raise DaemonError("daemon 未运行（无 socket）")
    return await asyncio.open_unix_connection(str(DAEMON_SOCK))


async def daemon_request(
    op: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    **fields: Any,
) -> dict:
    body: dict[str, Any] = {"op": op, **fields}
    reader, writer = await asyncio.wait_for(_open_connection(), timeout=timeout)
    try:
        writer.write((json.dumps(body, ensure_ascii=False) + "\n").encode("utf-8"))
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not line:
            raise DaemonError("daemon 无响应")
        return json.loads(line.decode("utf-8"))
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def ping_daemon(*, timeout: float = 0.5) -> bool:
    try:
        resp = await daemon_request("ping", timeout=timeout)
        return bool(resp.get("ok"))
    except Exception:
        return False


async def enqueue_show(**kwargs: Any) -> None:
    """尽力写入 show 请求；不读 daemon 响应，失败静默忽略。"""
    if not DAEMON_SOCK.is_socket():
        return
    body: dict[str, Any] = {"op": "show", **kwargs}
    try:
        _reader, writer = await asyncio.wait_for(_open_connection(), timeout=0.8)
        try:
            writer.write((json.dumps(body, ensure_ascii=False) + "\n").encode("utf-8"))
            await writer.drain()
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    except Exception:
        pass


async def show_via_daemon(**kwargs: Any) -> None:
    """Fire-and-forget：表达显示意图即可，不等待执行结果。"""
    await enqueue_show(**kwargs)


async def reconnect_daemon(**kwargs: Any) -> dict:
    resp = await daemon_request("reconnect", timeout=_START_TIMEOUT, **kwargs)
    if not resp.get("ok"):
        raise DaemonError(resp.get("error") or "daemon reconnect 失败")
    return resp

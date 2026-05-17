"""daemon 生命周期：检测旧进程、启动、等待就绪。"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from typing import Any

from .paths import CACHE_DIR, DAEMON_LOG, DAEMON_PID_FILE, DAEMON_SOCK


def read_daemon_pid() -> int | None:
    if not DAEMON_PID_FILE.is_file():
        return None
    try:
        return int(DAEMON_PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_existing_daemon(*, grace_s: float = 2.0) -> int | None:
    """终止已有 daemon（非当前进程）；返回被结束的 pid。"""
    pid = read_daemon_pid()
    me = os.getpid()
    killed: int | None = None

    if pid is not None and pid != me and pid_alive(pid):
        killed = pid
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.monotonic() + grace_s
        while time.monotonic() < deadline and pid_alive(pid):
            time.sleep(0.1)
        if pid_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    if DAEMON_SOCK.exists():
        try:
            DAEMON_SOCK.unlink()
        except OSError:
            pass

    cur = read_daemon_pid()
    if cur is not None and (not pid_alive(cur) or cur == me):
        try:
            DAEMON_PID_FILE.unlink()
        except OSError:
            pass

    return killed


def _daemon_cmd(*, scan: bool, address: str | None) -> list[str]:
    cmd = [sys.executable, "-m", "littlebuddy_mcp.daemon"]
    if scan:
        cmd.append("--scan")
    if address:
        cmd.extend(["--address", address])
    return cmd


def start_daemon_process(
    *,
    scan: bool = False,
    address: str | None = None,
    kill_old: bool = True,
) -> subprocess.Popen[Any]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if kill_old:
        kill_existing_daemon()
    log_out = open(CACHE_DIR / "daemon.stdout", "a", encoding="utf-8")
    env = os.environ.copy()
    env["LITTLEBUDDY_MCP_DIR"] = str(CACHE_DIR)
    return subprocess.Popen(
        _daemon_cmd(scan=scan, address=address),
        stdin=subprocess.DEVNULL,
        stdout=log_out,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=env,
    )


async def wait_daemon_ready(*, timeout_s: float = 45.0) -> bool:
    import asyncio

    from .daemon_client import ping_daemon

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if DAEMON_SOCK.is_socket():
            try:
                if await ping_daemon(timeout=1.0):
                    return True
            except Exception:
                pass
        await asyncio.sleep(0.25)
    return False


def wait_daemon_ready_sync(*, timeout_s: float = 45.0) -> bool:
    import asyncio

    return asyncio.run(wait_daemon_ready(timeout_s=timeout_s))


def daemon_status() -> dict:
    pid = read_daemon_pid()
    alive = pid is not None and pid_alive(pid)
    return {"pid": pid, "alive": alive, "socket": DAEMON_SOCK.is_socket()}


async def ensure_daemon_running(
    *,
    scan: bool = False,
    address: str | None = None,
    restart: bool = False,
) -> None:
    from .daemon_client import ping_daemon

    if not restart and await ping_daemon(timeout=0.8):
        return

    # daemon 可能仍在启动中，先短时等待，避免误杀已连上的进程
    if not restart and await wait_daemon_ready(timeout_s=8.0):
        return

    if restart:
        kill_existing_daemon()
    elif daemon_status()["alive"] and await ping_daemon(timeout=2.0):
        return

    start_daemon_process(scan=scan, address=address, kill_old=True)
    if not await wait_daemon_ready():
        raise RuntimeError(
            f"littlebuddy daemon 启动失败。请查看 {DAEMON_LOG}"
        )


def cmd_start(*, scan: bool = False, address: str | None = None, restart: bool = False) -> int:
    if not restart:
        st = daemon_status()
        if st["alive"] and st["socket"]:
            import asyncio

            from .daemon_client import ping_daemon

            if asyncio.run(ping_daemon()):
                print(f"daemon 已在运行 pid={st['pid']}")
                return 0

    print("启动 littlebuddy daemon…")
    start_daemon_process(scan=scan, address=address, kill_old=True)
    if wait_daemon_ready_sync():
        print(f"daemon 就绪 pid={read_daemon_pid()} socket={DAEMON_SOCK}")
        return 0
    print(f"daemon 启动超时，查看 {DAEMON_LOG}", file=sys.stderr)
    return 1


def cmd_stop() -> int:
    killed = kill_existing_daemon()
    if killed:
        print(f"已停止 daemon pid={killed}")
        return 0
    print("无运行中的 daemon")
    return 0


def cmd_status() -> int:
    import asyncio

    from .daemon_client import ping_daemon

    st = daemon_status()
    print(f"pid={st['pid']} alive={st['alive']} socket={st['socket']}")
    if st["alive"] and st["socket"]:
        ok = asyncio.run(ping_daemon())
        print(f"ping={'ok' if ok else 'fail'}")
    return 0


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="littlebuddy BLE 常驻服务")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_start = sub.add_parser("start", help="启动 daemon（会先结束旧进程）")
    p_start.add_argument("--scan", action="store_true")
    p_start.add_argument("--address")
    sub.add_parser("stop", help="停止 daemon")
    p_restart = sub.add_parser("restart", help="重启 daemon")
    p_restart.add_argument("--scan", action="store_true")
    p_restart.add_argument("--address")
    sub.add_parser("status", help="查看状态")
    args = parser.parse_args()

    if args.cmd == "start":
        sys.exit(cmd_start(scan=args.scan, address=getattr(args, "address", None)))
    if args.cmd == "stop":
        sys.exit(cmd_stop())
    if args.cmd == "restart":
        sys.exit(cmd_start(scan=args.scan, address=getattr(args, "address", None), restart=True))
    if args.cmd == "status":
        sys.exit(cmd_status())


if __name__ == "__main__":
    main()

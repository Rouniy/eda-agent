"""Keep the Altium network MCP endpoint and dashboard available."""

from __future__ import annotations

import logging
import msvcrt
import os
import asyncio
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time

import psutil
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eda_agent.bridge.altium_bridge import get_bridge
from eda_agent.config import get_config


SCRIPTS = ROOT / "scripts"
PYTHON = Path(sys.executable).with_name("python.exe")
# Probe over loopback: the machine's LAN address can change while the
# server is healthy and still listening on all interfaces.
MCP_HOST = "127.0.0.1"
MCP_PORT = 14701
DASHBOARD_PORT = 8766
POLL_SECONDS = 60
MCP_FAILURE_LIMIT = 3
MAX_SCRIPT_LAUNCHES_PER_PROCESS = 3


class ScriptLaunchBudget:
    """Bound URI launch attempts until Altium or the bridge recovers."""

    def __init__(self) -> None:
        self.altium_pid: int | None = None
        self.attempts = 0

    def observe(self, altium_pid: int | None, *, ping_ok: bool = False) -> None:
        if altium_pid != self.altium_pid or ping_ok:
            self.altium_pid = altium_pid
            self.attempts = 0

    def allow_launch(self) -> bool:
        return self.altium_pid is not None and self.attempts < MAX_SCRIPT_LAUNCHES_PER_PROCESS

    def record_launch(self) -> None:
        self.attempts += 1


def listener(port: int) -> int | None:
    for conn in psutil.net_connections(kind="tcp"):
        if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
            return conn.pid
    return None


def active_altium_command(workspace: Path) -> bool:
    # DelphiScript removes its progress marker when the command returns.
    # Do not interrupt a long-running command just because its ping timed out.
    return any(workspace.glob("progress_*.json"))


def pending_script_launcher() -> bool:
    """A URI launch still waiting in X2 must not be launched again."""
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            if (proc.info["name"] or "").lower() != "x2.exe":
                continue
            if any("dxpprocess://ScriptingSystem:RunScript" in arg
                   for arg in (proc.info["cmdline"] or [])):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


async def _check_mcp() -> None:
    url = f"http://{MCP_HOST}:{MCP_PORT}/mcp"
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            if not tools.tools:
                raise RuntimeError("MCP returned no tools")


def mcp_healthy() -> bool:
    try:
        asyncio.run(asyncio.wait_for(_check_mcp(), timeout=10))
        return True
    except Exception as exc:
        logging.warning("MCP protocol check failed: %s", exc)
        return False


def write_status(workspace: Path, status: dict) -> None:
    """Publish the last completed check for operators without using Altium."""
    destination = workspace / "altium-mcp-supervisor-status.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)


def our_mcp_process(pid: int) -> bool:
    try:
        return any("serve-altium-http.py" in arg for arg in psutil.Process(pid).cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def start(args: list[str], log_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    lan_hosts = {"127.0.0.1"}
    for addresses in psutil.net_if_addrs().values():
        lan_hosts.update(address.address for address in addresses
                         if address.family == socket.AF_INET)
    env["EDA_AGENT_DASHBOARD_ALLOWED_HOSTS"] = ",".join(sorted(lan_hosts))
    with log_path.open("ab") as output:
        proc = subprocess.Popen(
            [str(PYTHON), *args],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    logging.info("started %s pid=%s", args[0], proc.pid)


def main() -> None:
    workspace = get_config().workspace_dir
    workspace.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=workspace / "altium-mcp-supervisor.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("mcp.client").setLevel(logging.WARNING)

    # A second copy, including one launched at sign-in, exits immediately.
    with (workspace / "altium-mcp-supervisor.lock").open("a+b") as lock:
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return

        bridge = get_bridge()
        failed_pings = 0
        failed_mcp_checks = 0
        last_blocking_dialog = ""
        last_script_launch = 0.0
        last_mcp_restart = 0.0
        script_launch_budget = ScriptLaunchBudget()
        while True:
            status = {
                "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "check_interval_seconds": POLL_SECONDS,
                "mcp_port": MCP_PORT,
                "mcp_listening": False,
                "mcp_protocol_ok": False,
                "altium_running": False,
                "altium_pid": None,
                "altium_command_active": False,
                "script_responsive": None,
                "bridge_usable": None,
                "dialog": None,
            }
            try:
                mcp_pid = listener(MCP_PORT)
                status["mcp_listening"] = mcp_pid is not None
                if not mcp_pid:
                    start(
                        [str(SCRIPTS / "serve-altium-http.py")],
                        workspace / "altium-http.log",
                    )
                    failed_mcp_checks = 0
                else:
                    status["mcp_protocol_ok"] = mcp_healthy()
                    if status["mcp_protocol_ok"]:
                        failed_mcp_checks = 0
                    else:
                        failed_mcp_checks += 1
                        if (
                            failed_mcp_checks >= MCP_FAILURE_LIMIT
                            and not active_altium_command(workspace)
                            and our_mcp_process(mcp_pid)
                            and time.monotonic() - last_mcp_restart > 120
                        ):
                            psutil.Process(mcp_pid).terminate()
                            try:
                                psutil.Process(mcp_pid).wait(timeout=5)
                            except psutil.TimeoutExpired:
                                psutil.Process(mcp_pid).kill()
                            start(
                                [str(SCRIPTS / "serve-altium-http.py")],
                                workspace / "altium-http.log",
                            )
                            logging.warning("restarted unresponsive MCP pid=%s", mcp_pid)
                            failed_mcp_checks = 0
                            last_mcp_restart = time.monotonic()
                if not listener(DASHBOARD_PORT):
                    start(
                        ["-m", "eda_agent", "dashboard", "--host", "0.0.0.0", "--port", "8766"],
                        workspace / "altium-dashboard.log",
                    )

                altium_status = bridge.get_altium_status()
                altium_pid = altium_status.get("pid")
                status["altium_running"] = altium_pid is not None
                status["altium_pid"] = altium_pid
                status["altium_command_active"] = active_altium_command(workspace)
                script_launch_budget.observe(altium_pid)
                dialog = bridge._dialog_probe() if altium_pid is not None else None
                if dialog and dialog.get("dialog_count"):
                    status["dialog"] = dialog
                    dialog_summary = dialog.get("summary", "")
                    if dialog_summary != last_blocking_dialog:
                        logging.error("Altium is blocked by a dialog: %s; details=%s",
                                      dialog_summary, dialog.get("dialogs", []))
                    last_blocking_dialog = dialog_summary
                elif altium_pid is not None and not status["altium_command_active"]:
                    if bridge.ping():
                        status["script_responsive"] = True
                        script_launch_budget.observe(altium_pid, ping_ok=True)
                        failed_pings = 0
                        last_blocking_dialog = ""
                    else:
                        status["script_responsive"] = False
                        failed_pings += 1
                        logging.warning("Altium script ping failed (%s)", failed_pings)
                        dialog = bridge._dialog_probe()
                        if dialog and dialog.get("dialog_count"):
                            status["dialog"] = dialog
                            dialog_summary = dialog.get("summary", "")
                            if dialog_summary != last_blocking_dialog:
                                logging.error("Altium is blocked by a dialog: %s; details=%s",
                                              dialog_summary, dialog.get("dialogs", []))
                            last_blocking_dialog = dialog_summary
                        if (failed_pings >= 2
                                and time.monotonic() - last_script_launch > 120
                                and script_launch_budget.allow_launch()
                                and not status["dialog"]
                                and not pending_script_launcher()):
                            subprocess.run(
                                [
                                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                                    "-File", str(SCRIPTS / "start-altium-bridge.ps1"),
                                ],
                                cwd=ROOT,
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                timeout=15,
                                check=False,
                            )
                            last_script_launch = time.monotonic()
                            script_launch_budget.record_launch()
                            logging.info("requested Altium script restart (%s/%s for pid %s)",
                                         script_launch_budget.attempts,
                                         MAX_SCRIPT_LAUNCHES_PER_PROCESS, altium_pid)
                            if not script_launch_budget.allow_launch():
                                logging.error("Altium script restart attempts exhausted for pid %s; "
                                              "waiting for recovery or a new Altium process", altium_pid)
                elif altium_pid is None:
                    failed_pings = 0
            except Exception:
                logging.exception("supervisor check failed")
                status["check_error"] = "supervisor check failed; see altium-mcp-supervisor.log"
            if not status["mcp_protocol_ok"] or not status["altium_running"] or status["dialog"]:
                status["bridge_usable"] = False
            elif status["script_responsive"] is not None:
                status["bridge_usable"] = status["script_responsive"]
            try:
                write_status(workspace, status)
            except Exception:
                logging.exception("could not publish supervisor status")
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

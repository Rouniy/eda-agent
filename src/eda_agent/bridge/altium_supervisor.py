# SPDX-License-Identifier: Apache-2.0
"""External supervisor for restarting the DelphiScript worker via Altium UI.

This module is inert until explicitly called. It never runs during import or
server startup, which keeps offline tests and normal MCP operation isolated
from the user's desktop.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from ..atomicfile import discard, replace_with_retry
from .dialog_diagnostics import diagnose_dialogs


RESTART_STATUS_FILE = "restart_status.json"


def _atomic_status(workspace: Path, payload: dict[str, Any]) -> None:
    path = workspace / RESTART_STATUS_FILE
    workspace.mkdir(parents=True, exist_ok=True)
    tmp = workspace / f".{RESTART_STATUS_FILE}.{uuid.uuid4().hex}.tmp"
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        replace_with_retry(tmp, path)
    finally:
        discard(tmp)


def read_restart_status(workspace: Path) -> Optional[dict[str, Any]]:
    path = workspace / RESTART_STATUS_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class AltiumBridgeSupervisor:
    """Stop/relaunch the worker and verify recovery with a ping callback."""

    def __init__(
        self,
        inspector: Any,
        workspace_dir: Path,
        ping: Callable[[], dict[str, Any]],
        *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.inspector = inspector
        self.workspace = Path(workspace_dir)
        self.ping = ping
        self.sleep = sleep
        self.clock = clock

    def restart(
        self,
        *,
        launch_hotkey: str,
        expected_script_version: str = "",
        stop_delay_seconds: float = 1.0,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        if not launch_hotkey.strip():
            return self._finish(False, "setup_required",
                "Assign an Altium custom command for StartMCPServer and provide its hotkey")
        dialogs = self.inspector.list_dialogs()
        diagnosed = diagnose_dialogs(dialogs)
        protected = [d for d in diagnosed if not d["automation_safe"]]
        if protected:
            return self._finish(False, "blocked_by_dialog",
                "A protected Altium dialog is open", dialogs=protected)

        hwnd = self.inspector.main_window_handle()
        windows = self.inspector.list_windows()
        status_windows = [w for w in windows if w.get("title") == "EDA Agent MCP"]
        script_fault = any(
            d.get("kind") in {"compile_error", "runtime_error"}
            for d in diagnosed
        )
        _atomic_status(self.workspace, {
            "state": "stopping", "success": False, "window_handle": hwnd,
        })
        try:
            if script_fault or not status_windows:
                stop_result = self.inspector.send_hotkey(hwnd, "ctrl+f3")
            else:
                status = status_windows[0]
                stop_result = self.inspector.close_window(
                    int(status["handle"]), "EDA Agent MCP"
                )
            self.sleep(max(0.1, stop_delay_seconds))
            _atomic_status(self.workspace, {
                "state": "starting", "success": False, "window_handle": hwnd,
                "launch_hotkey": launch_hotkey, "stop_hotkey": stop_result,
            })
            launch_result = self.inspector.send_hotkey(hwnd, launch_hotkey)
        except Exception as exc:
            return self._finish(False, "error", f"hotkey dispatch failed: {exc}")

        deadline = self.clock() + max(1.0, timeout_seconds)
        attempts = 0
        last_error = ""
        while self.clock() < deadline:
            attempts += 1
            try:
                response = self.ping()
                running_version = str(response.get("script_version", ""))
                if expected_script_version and running_version != expected_script_version:
                    last_error = (
                        f"version mismatch: expected {expected_script_version}, "
                        f"running {running_version or '<unknown>'}"
                    )
                else:
                    return self._finish(True, "running", "Bridge restarted",
                        attempts=attempts, ping=response,
                        launch_hotkey_result=launch_result)
            except Exception as exc:  # retry is the point of the supervisor
                last_error = str(exc)
            self.sleep(0.25)
        return self._finish(False, "timeout", last_error or "No ping response",
            attempts=attempts, dialogs=diagnose_dialogs(self.inspector.list_dialogs()))

    def _finish(self, success: bool, state: str, message: str, **extra: Any) -> dict[str, Any]:
        result = {"success": success, "state": state, "message": message, **extra}
        _atomic_status(self.workspace, result)
        return result

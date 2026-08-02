# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Altium process detection and management."""

import logging
import sys
import time
import psutil
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("eda_agent.bridge.process")


# ---------------------------------------------------------------------------
# Native Windows process-name scan.
#
# psutil.process_iter -- even fetching only "name" -- measured ~2.2s on the
# target machine, and is_altium_running() is on the hot path of every bridge
# call. The Toolhelp snapshot API enumerates process names straight from the
# kernel snapshot in tens of milliseconds. Falls back to psutil if the
# native path is unavailable (non-Windows, ctypes failure).
# ---------------------------------------------------------------------------

_TH32CS_SNAPPROCESS = 0x00000002
_th_kernel32 = None
if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes

        class _PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_wchar * 260),
            ]

        _th_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        _th_kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        _th_kernel32.CreateToolhelp32Snapshot.argtypes = [
            wintypes.DWORD, wintypes.DWORD]
        _th_kernel32.Process32FirstW.restype = wintypes.BOOL
        _th_kernel32.Process32FirstW.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
        _th_kernel32.Process32NextW.restype = wintypes.BOOL
        _th_kernel32.Process32NextW.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(_PROCESSENTRY32W)]
        _th_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        _th_invalid_handle = ctypes.c_void_p(-1).value
    except Exception as _e:  # pragma: no cover - platform dependent
        _th_kernel32 = None
        logger.debug("Toolhelp process scan unavailable: %s", _e)


def _scan_process_names_native(wanted_upper: set) -> Optional[bool]:
    """Return True/False if any wanted process name is running, via the
    Toolhelp snapshot. Returns None if the native path is unavailable."""
    if _th_kernel32 is None:
        return None
    try:
        snap = _th_kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        if not snap or snap == _th_invalid_handle:
            return None
        try:
            entry = _PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
            ok = _th_kernel32.Process32FirstW(snap, ctypes.byref(entry))
            while ok:
                if entry.szExeFile.upper() in wanted_upper:
                    return True
                ok = _th_kernel32.Process32NextW(snap, ctypes.byref(entry))
            return False
        finally:
            _th_kernel32.CloseHandle(snap)
    except Exception as e:
        logger.debug("native process scan failed: %s", e)
        return None


def _pids_with_visible_window() -> set[int]:
    """PIDs that own at least one visible, titled top-level window.

    Used to tell a live Altium editor apart from the windowless husks a
    crash leaves behind. Returns an empty set off Windows or on any
    ctypes failure, which degrades the caller to its size-based
    tie-break rather than breaking it.
    """
    if sys.platform != "win32":
        return set()
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return set()

    pids: set[int] = set()
    try:
        user32 = ctypes.windll.user32
        enum_proc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )

        def _collect(hwnd, _lparam):
            try:
                if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value:
                        pids.add(int(pid.value))
            except Exception:
                pass
            return True

        user32.EnumWindows(enum_proc(_collect), 0)
    except Exception as e:
        logger.debug("visible-window scan failed: %s", e)
        return set()
    return pids


@dataclass
class AltiumProcessInfo:
    """Information about a running Altium process."""

    pid: int
    name: str
    exe_path: str
    version: Optional[str] = None
    cmdline: Optional[list[str]] = None


class AltiumProcessManager:
    """Manages detection and interaction with Altium Designer process."""

    PROCESS_NAMES = ["X2.exe", "DXP.exe"]  # Altium Designer executable names

    # is_altium_running() is on the hot path -- every bridge call hits it
    # (twice: once in _bridge_call, once inside send_command). A full
    # process_iter that fetches exe/cmdline opens every process on Windows
    # and costs seconds; cache the cheap name-only result for this long.
    _RUNNING_TTL = 3.0

    def __init__(self):
        self._running_cache: Optional[tuple[float, bool]] = None

    def find_altium_process(self) -> Optional[AltiumProcessInfo]:
        """Find a running Altium Designer process, with full info.

        Fetches exe + cmdline, so this is the SLOW path -- only call it
        when that detail is actually needed (status display, version
        probe). For a plain "is it running?" check use is_altium_running.

        A machine can carry several X2.exe processes at once: crashed or
        half-torn-down instances linger for hours with no window, and
        Altium itself spawns helpers under the same image name. Returning
        the first PID the kernel happens to list then attaches every
        Win32 tool (app_list_dialogs, app_click_dialog_button,
        app_restart_altium_bridge) to a windowless husk, while the
        file-based IPC keeps talking to the real editor. The two halves
        disagree silently: dialogs read as "none open" while a modal
        actually blocks the bridge. So rank candidates by whether they
        own a visible titled top-level window first, then by resident
        size -- the loaded editor dwarfs an idle instance.
        """
        candidates: list[AltiumProcessInfo] = []
        wanted = {n.upper() for n in self.PROCESS_NAMES}
        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                proc_name = proc.info["name"] or ""
                if proc_name.upper() not in wanted:
                    continue
                candidates.append(
                    AltiumProcessInfo(
                        pid=proc.info["pid"],
                        name=proc.info["name"],
                        exe_path=proc.info["exe"] or "",
                        cmdline=proc.info["cmdline"],
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if not candidates:
            return None
        if len(candidates) == 1:
            logger.debug("Found Altium process: PID=%d", candidates[0].pid)
            return candidates[0]

        gui_pids = _pids_with_visible_window()

        def _rss(pid: int) -> int:
            try:
                return psutil.Process(pid).memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                return 0

        best = max(candidates, key=lambda c: (c.pid in gui_pids, _rss(c.pid)))
        logger.debug(
            "Found Altium process: PID=%d (%d candidates, %d with a window)",
            best.pid,
            len(candidates),
            len(gui_pids & {c.pid for c in candidates}),
        )
        return best

    def _scan_running(self) -> bool:
        """Is any Altium process running? Native Toolhelp scan first
        (~tens of ms); tasklist.exe for WSL; psutil as last resort.
        """
        wanted = {n.upper() for n in self.PROCESS_NAMES}
        native = _scan_process_names_native(wanted)
        if native is not None:
            return native
        # WSL fallback: query Windows process list via tasklist.exe
        import subprocess as _sp
        import os as _os
        tasklist = "/mnt/c/Windows/System32/tasklist.exe"
        if _os.path.exists(tasklist):
            try:
                for proc_name in self.PROCESS_NAMES:
                    r = _sp.run(
                        [tasklist, "/FI", "IMAGENAME eq " + proc_name, "/FO", "CSV", "/NH"],
                        capture_output=True, text=True, timeout=5,
                    )
                    if proc_name.upper() in r.stdout.upper():
                        return True
                return False
            except Exception as e:
                logger.debug("tasklist.exe scan failed: %s", e)
        # Last resort: psutil (Linux processes only, won't see Altium on Windows)
        try:
            for proc in psutil.process_iter(["name"]):
                name = (proc.info.get("name") or "").upper()
                if name in wanted:
                    return True
        except Exception as e:
            logger.debug("process scan failed: %s", e)
        return False

    def is_altium_running(self) -> bool:
        """Check if Altium Designer is running.

        Fast path: a name-only process scan, cached for _RUNNING_TTL
        seconds. Altium does not start/stop within a few seconds, so the
        cache is safe and removes seconds of latency from every bridge
        call.
        """
        now = time.monotonic()
        cached = self._running_cache
        if cached is not None and (now - cached[0]) < self._RUNNING_TTL:
            return cached[1]
        val = self._scan_running()
        self._running_cache = (now, val)
        return val

    def get_altium_info(self) -> Optional[AltiumProcessInfo]:
        """Get information about the running Altium process.

        Returns:
            AltiumProcessInfo if Altium is running, None otherwise.
        """
        return self.find_altium_process()

    def get_altium_pid(self) -> Optional[int]:
        """Get the PID of the running Altium process.

        Returns:
            PID if Altium is running, None otherwise.
        """
        process = self.find_altium_process()
        return process.pid if process else None

    def refresh(self) -> None:
        """Re-scan for the Altium process."""
        self.find_altium_process()

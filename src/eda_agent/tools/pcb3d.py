# SPDX-License-Identifier: Apache-2.0
"""Combined native bridge and Win32 controls for Altium PCB 3-D views."""

from __future__ import annotations

import asyncio
import ctypes
import math
from ctypes import wintypes
from pathlib import Path
from typing import Any

from ..ui import menu, windows
from .uiauto import _altium_pid

_COMPARE_DIR = Path(r"D:\shared\xo-altium\compare")
_LAST_VIEW: dict[tuple[int, str], tuple[int, int, float]] = {}


def _applied_angle(value: int) -> int:
    """Round to a 30-degree key step and use the shortest equivalent turn."""
    steps = round(value / 30)
    return ((steps + 6) % 12 - 6) * 30


def _applied_zoom(value: float) -> float:
    return min((0.25, 0.5, 1.0, 2.0, 4.0),
               key=lambda option: abs(math.log2(value / option)))

async def _show_focused_pcb_3d() -> dict[str, Any]:
    """Make the focused PcbDoc's 3-D view visible before a 3-D operation."""
    from ..bridge import get_bridge

    bridge = get_bridge()
    active = await bridge.send_command_async("application.get_active_document")
    if str(active.get("document_kind", "")).lower() not in {"pcb", "pcbdoc"}:
        raise ValueError("focus a PcbDoc before a 3-D operation")
    await bridge.send_command_async("generic.switch_view", {"mode": "3d"})
    return active


def _pcb_canvas_hwnd(pid: int) -> int:
    """Find the one visible PCB editor canvas in the Altium process."""
    import win32gui
    import win32process

    canvases: list[int] = []

    def find_window(hwnd, unused):
        _, owner = win32process.GetWindowThreadProcessId(hwnd)
        if owner != pid or not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.GetClassName(hwnd) != "TDocumentForm":
            return
        pcb_tabs = []
        window_canvases = []

        def find_canvas(child, unused_child):
            if not win32gui.IsWindowVisible(child):
                return
            tab_title = win32gui.GetWindowText(child).removesuffix(" *")
            if (win32gui.GetClassName(child) == "TdxTabSheet" and
                    tab_title.lower().endswith(".pcbdoc")):
                pcb_tabs.append(child)
            if win32gui.GetClassName(child) == "View_Graphical":
                window_canvases.append(child)

        win32gui.EnumChildWindows(hwnd, find_canvas, None)
        if pcb_tabs:
            canvases.extend(window_canvases)

    win32gui.EnumWindows(find_window, None)
    if len(canvases) != 1:
        raise ValueError(f"expected one visible PCB canvas, found {len(canvases)}")
    return canvases[0]


def register_pcb3d_tools(mcp):
    @mcp.tool()
    async def pcb_3d_center() -> dict[str, Any]:
        """Show the focused PCB in 3-D and fit the board in the canvas.

        Uses Altium's PCB:Zoom Action=Board, which centers the board and
        preserves its current 3-D orientation on the tested editor.
        """
        from ..bridge import get_bridge

        try:
            active = await _show_focused_pcb_3d()
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        result = await get_bridge().send_command_async(
            "generic.zoom", {"action": "board"})
        pid, _ = _altium_pid()
        _LAST_VIEW.pop((pid, str(active.get("file_path", "")).casefold()), None)
        return {"success": True, "board_path": active.get("file_path"),
                "mode_requested": "3d", "center_command": result,
                "camera_readback_available": False}

    @mcp.tool()
    async def pcb_3d_set_view(yaw_deg: int = 0, pitch_deg: int = 0,
                              zoom_factor: float = 1.0) -> dict[str, Any]:
        """Set a repeatable 3-D board angle and zoom relative to Fit Board.

        Angles are rounded to Altium's 30-degree numpad rotation step.
        Zoom is rounded to 0.25, 0.5, 1, 2, or 4 relative to Fit Board.
        A repeated call with the same requested controls is a no-op in this
        MCP process. It uses the editor's PageUp/PageDown
        shortcuts with the pointer anchored at the canvas center. Altium has
        no verified script camera readback here, so the reported angles and
        zoom are requested controls, not measured absolute camera values.
        """
        import win32gui

        from ..bridge import get_bridge

        if any(not isinstance(v, int) or isinstance(v, bool)
               for v in (yaw_deg, pitch_deg)):
            return {"success": False, "error":
                    "yaw_deg and pitch_deg must be integers"}
        factors = {0.25: -2, 0.5: -1, 1.0: 0, 2.0: 1, 4.0: 2}
        if not isinstance(zoom_factor, (int, float)) or isinstance(zoom_factor, bool) or not math.isfinite(zoom_factor) or not 0.25 <= zoom_factor <= 4:
            return {"success": False, "error":
                    "zoom_factor must be finite and within 0.25..4"}
        applied_yaw = _applied_angle(yaw_deg)
        applied_pitch = _applied_angle(pitch_deg)
        applied_zoom = _applied_zoom(zoom_factor)
        pid, problem = _altium_pid()
        if problem is not None:
            return problem
        try:
            active = await _show_focused_pcb_3d()
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        cache_key = (pid, str(active.get("file_path", "")).casefold())
        requested = (yaw_deg, pitch_deg, float(zoom_factor))
        common = {"success": True, "board_path": active.get("file_path"),
                  "yaw_deg_requested": yaw_deg, "pitch_deg_requested": pitch_deg,
                  "zoom_factor_requested": zoom_factor,
                  "yaw_deg_applied": applied_yaw, "pitch_deg_applied": applied_pitch,
                  "zoom_factor_applied": applied_zoom,
                  "camera_readback_available": False,
                  "rotation_step_assumed_deg": 30}
        if _LAST_VIEW.get(cache_key) == requested:
            return {**common, "unchanged": True, "camera_reset": False}
        canvas = _pcb_canvas_hwnd(pid)
        left, top, right, bottom = win32gui.GetWindowRect(canvas)
        anchor = ((left + right) // 2, (top + bottom) // 2)
        frame = menu.frame(pid)
        if frame is None:
            return {"success": False, "error": "Altium frame is unavailable"}
        pointer = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pointer))
        original = (pointer.x, pointer.y)
        keys: list[str] = ["0"]
        keys.extend(["num6" if applied_yaw > 0 else "num4"] * (abs(applied_yaw) // 30))
        keys.extend(["num8" if applied_pitch > 0 else "num2"] * (abs(applied_pitch) // 30))
        try:
            windows.require_foreground(frame.hwnd, "3-D view control")
            windows.require_point_in_app(*anchor, frame.hwnd, "3-D zoom anchor")
            ctypes.windll.user32.SetCursorPos(*anchor)
            for key in keys:
                rotation = windows.send_keys(key, target=frame.hwnd)
                if not rotation.get("ok"):
                    return {"success": False, "error": rotation.get("reason")}
                await asyncio.sleep(0.8)
            centered = await get_bridge().send_command_async(
                "generic.zoom", {"action": "board"})
            await asyncio.sleep(0.25)
            zoom_steps = factors[applied_zoom]
            if zoom_steps:
                zoom_key = "pageup" if zoom_steps > 0 else "pagedown"
                for _ in range(abs(zoom_steps)):
                    zoomed = windows.send_keys(zoom_key, target=frame.hwnd)
                    if not zoomed.get("ok"):
                        return {"success": False, "error": zoomed.get("reason")}
                    await asyncio.sleep(0.2)
        finally:
            ctypes.windll.user32.SetCursorPos(*original)
        _LAST_VIEW[cache_key] = requested
        return {**common, "mode_requested": "3d", "unchanged": False,
                "camera_reset": True, "rotation_keys": keys,
                "center_command": centered}

    @mcp.tool()
    async def pcb_3d_capture(output_path: str = "", width_px: int = 0,
                             height_px: int = 0) -> dict[str, Any]:
        """Capture the visible PCB editor canvas without side panels.

        Switches the focused PcbDoc to 3-D first, then captures the current
        camera without moving it. Altium does not expose camera readback here.
        """
        from pathlib import Path
        from ..bridge.windows_ui import WindowsUiInspector

        pid, problem = _altium_pid()
        if problem is not None:
            return problem
        if width_px < 0 or height_px < 0 or width_px > 8192 or height_px > 8192:
            return {"success": False, "error": "width_px and height_px must be 0..8192"}
        try:
            active = await _show_focused_pcb_3d()
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        board_path = str(active.get("file_path", ""))
        view = _LAST_VIEW.get((pid, board_path.casefold()))
        if not output_path:
            yaw, pitch, zoom = ((_applied_angle(view[0]), _applied_angle(view[1]),
                                 _applied_zoom(view[2])) if view is not None else
                                ("unknown", "unknown", "unknown"))
            filename = f"{Path(board_path).stem}-{yaw}-{pitch}-{zoom}.png"
            path = _COMPARE_DIR / filename
        elif Path(output_path).is_absolute():
            path = Path(output_path).expanduser().resolve()
        else:
            path = (_COMPARE_DIR / output_path).resolve()
            if not path.is_relative_to(_COMPARE_DIR):
                return {"success": False, "error": "relative output_path must stay under compare"}
        if path.suffix.lower() != ".png":
            return {"success": False, "error": "output_path must end in .png"}
        path.parent.mkdir(parents=True, exist_ok=True)
        canvas = _pcb_canvas_hwnd(pid)
        capture = WindowsUiInspector(pid).capture_window(canvas, path)
        if width_px or height_px:
            from PIL import Image
            with Image.open(path) as current:
                target_width = width_px or round(current.width * height_px / current.height)
                target_height = height_px or round(current.height * width_px / current.width)
                resized = current.resize((target_width, target_height), Image.Resampling.LANCZOS)
                resized.save(path, format="PNG")
            capture["width"] = target_width
            capture["height"] = target_height
        capture["view_mode_verified"] = False
        return capture


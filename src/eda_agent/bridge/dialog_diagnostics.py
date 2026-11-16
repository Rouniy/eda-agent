# SPDX-License-Identifier: Apache-2.0
"""Pure classification of native Altium dialog inventories."""

from __future__ import annotations

import re
from typing import Any, Iterable


_LINE_PATTERNS = (
    re.compile(r"(?P<file>[^\r\n:]+\.(?:pas|dfm))\s*[:(]\s*(?P<line>\d+)", re.I),
    re.compile(r"line\s+(?P<line>\d+)", re.I),
)
_SYMBOL = re.compile(
    r"(?:undeclared identifier|unknown identifier|identifier expected)\s*[:\-]?\s*['\"]?(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)",
    re.I,
)


def _dialog_text(dialog: dict[str, Any]) -> str:
    parts = [str(dialog.get("title", ""))]
    for control in dialog.get("controls", []):
        if control.get("text"):
            parts.append(str(control["text"]))
    return "\n".join(parts).strip()


def classify_dialog(dialog: dict[str, Any]) -> dict[str, Any]:
    text = _dialog_text(dialog)
    lower = text.lower()
    if any(x in lower for x in ("compile error", "compilation error", "undeclared identifier", "syntax error")):
        kind, severity = "compile_error", "error"
    elif any(x in lower for x in ("runtime error", "access violation", "exception", "could not convert variant")):
        kind, severity = "runtime_error", "error"
    elif any(x in lower for x in ("save changes", "modified document", "сохранить изменения")):
        kind, severity = "save_confirmation", "warning"
    elif any(x in lower for x in ("license", "activation", "sign in", "войти")):
        kind, severity = "protected_system_dialog", "warning"
    elif any(x in lower for x in ("extensions and updates", "update available")):
        kind, severity = "update_dialog", "info"
    else:
        kind, severity = "unknown_dialog", "info"

    file_name = None
    line = None
    for pattern in _LINE_PATTERNS:
        match = pattern.search(text)
        if match:
            file_name = match.groupdict().get("file")
            value = match.groupdict().get("line")
            line = int(value) if value else None
            break
    symbol_match = _SYMBOL.search(text)
    buttons = [
        c for c in dialog.get("controls", [])
        if str(c.get("class_name", "")).lower() == "button"
    ]
    return {
        "kind": kind,
        "severity": severity,
        "dialog_handle": dialog.get("handle"),
        "title": dialog.get("title", ""),
        "text": text,
        "file": file_name.strip() if file_name else None,
        "line": line,
        "symbol": symbol_match.group("symbol") if symbol_match else None,
        "buttons": [{"handle": b.get("handle"), "caption": b.get("text", "")} for b in buttons],
        "automation_safe": kind not in {"save_confirmation", "protected_system_dialog", "update_dialog"},
    }


def diagnose_dialogs(dialogs: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [classify_dialog(dialog) for dialog in dialogs]


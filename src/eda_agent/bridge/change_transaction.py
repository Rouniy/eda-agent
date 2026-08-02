# SPDX-License-Identifier: Apache-2.0
"""Validation helpers for checkpoint-backed multi-command changes."""

from __future__ import annotations

import re
from typing import Any


ALLOWED_PREFIXES = (
    "application.", "generic.", "library.", "pcb.", "project.", "audit.",
)
BLOCKED_COMMANDS = {
    "application.stop_server",
    "application.close_document",
    "application.reload_document",
    "application.open_document",
    "project.close",
    "project.open",
}
_DESTRUCTIVE = re.compile(r"(?:^|[._])(delete|remove|clear|prune|restore)(?:$|[._])", re.I)
_READISH = re.compile(
    r"(?:^|[._])(get|list|query|audit|check|validate|compare|snapshot|ping|run_drc|run_erc)(?:$|[._])",
    re.I,
)


def command_is_destructive(command: str) -> bool:
    return bool(_DESTRUCTIVE.search(command))


def validate_change_plan(
    operations: list[dict[str, Any]],
    validations: list[dict[str, Any]],
    *,
    allow_destructive: bool,
) -> list[str]:
    errors: list[str] = []
    if not operations:
        errors.append("operations must be non-empty")
    for group_name, entries in (("operations", operations), ("validations", validations)):
        for index, entry in enumerate(entries):
            command = str(entry.get("command", "")).strip()
            if not command:
                errors.append(f"{group_name}[{index}].command is required")
                continue
            if not command.startswith(ALLOWED_PREFIXES):
                errors.append(f"{command}: command domain is not allowed")
            if command in BLOCKED_COMMANDS:
                errors.append(f"{command}: lifecycle commands cannot run inside a change transaction")
            if group_name == "validations" and not _READISH.search(command):
                errors.append(f"{command}: validation command is not read-only/audit-like")
            if command_is_destructive(command) and not allow_destructive:
                errors.append(f"{command}: allow_destructive=true is required")
            params = entry.get("params", {})
            if params is not None and not isinstance(params, dict):
                errors.append(f"{group_name}[{index}].params must be an object")
    return errors


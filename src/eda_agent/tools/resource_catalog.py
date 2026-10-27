# SPDX-License-Identifier: Apache-2.0
"""Read-only catalog of installed Altium resource definitions.

RCS describes factory menus and launchers. It does not describe the final
runtime menu after extensions, enablement rules and user customisation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_FILES = {
    "pcb": ("AdvPcb.rcs", "MNPCBMenu", "MNPCBPopup"),
    "sch": ("advsch.rcs", "MNSchematicMenu", "MNSchematicPopup"),
    "pcblib": ("AdvPcb.rcs", "MNPCBLibMenu", "MNPCBLibPopup"),
    "schlib": ("advsch.rcs", "MNSchLibMenu", "MNSchematicLibPopup"),
    "project": ("WorkspaceManager.rcs", "MNProjectView", None),
}
_ATTR = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*(?:'([^']*)'|([^\s]+))")
_HEAD = re.compile(r"^\s*(TreeCopy|Tree|Separator|Link|PL|End)\b(?:\s+([^\s]+))?", re.I)


def _system_dir() -> Path:
    # Resolve from the running X2 executable, not a caller-supplied path.
    import psutil

    candidates = []
    for proc in psutil.process_iter(("name", "exe")):
        try:
            if (proc.info["name"] or "").lower() == "x2.exe" and proc.info["exe"]:
                candidates.append(Path(proc.info["exe"]).parent / "System")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if len(candidates) != 1 or not candidates[0].is_dir():
        raise RuntimeError("Expected one running Altium installation with a System directory")
    return candidates[0]


def _line_parts(line: str) -> tuple[str, str, dict[str, str]] | None:
    if line.lstrip().startswith("//"):
        return None
    match = _HEAD.match(line)
    if not match:
        return None
    attrs = {m.group(1).lower(): m.group(2) if m.group(2) is not None else m.group(3)
             for m in _ATTR.finditer(line[match.end():])}
    return match.group(1).lower(), (match.group(2) or "").strip("'"), attrs


def _read(path: Path) -> str:
    # cp1252 preserves the older single-byte RCS captions on this host.
    return path.read_text(encoding="cp1252", errors="replace")


def _resources(system: Path) -> tuple[dict[str, dict[str, str]], dict[str, list]]:
    launchers: dict[str, dict[str, str]] = {}
    trees: dict[str, list] = {}
    for path in system.glob("*.rcs"):
        stack: list[list] = []
        for line in _read(path).splitlines():
            item = _line_parts(line)
            if not item:
                continue
            kind, ident, attrs = item
            if kind == "pl":
                launchers[ident.lower()] = attrs
            elif kind == "tree":
                node = [kind, ident, attrs, []]
                trees[ident.lower()] = node
                if stack:
                    stack[-1].append(node)
                stack.append(node[3])
            elif kind == "end":
                if stack:
                    stack.pop()
            elif stack:
                stack[-1].append([kind, ident, attrs, []])
    return launchers, trees


def _caption(value: str) -> str:
    return value.replace("&&", "\0").replace("&", "").replace("\0", "&").strip()


def _accelerator(attrs: dict[str, str]) -> str:
    popup = attrs.get("popup", "")
    if popup:
        return popup.upper()
    raw = attrs.get("caption", "")
    match = re.search(r"(?<!&)&(?!&)(.)", raw)
    return match.group(1).upper() if match else ""


def _menu_rows(root: list, launchers: dict, trees: dict, *, context: bool,
               shortcuts: bool) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def walk(children: list, path: list[str], keys: list[str], seen: set[str]) -> None:
        for kind, ident, attrs, sub in children:
            if kind == "treecopy":
                target = attrs.get("originalid", "").lower()
                if target in trees and target not in seen:
                    copied = trees[target]
                    label = _caption(copied[2].get("caption", ""))
                    walk(copied[3], path + ([label] if label else []),
                         keys + ([_accelerator(copied[2])] if label else []), seen | {target})
            elif kind == "tree":
                label = _caption(attrs.get("caption", ""))
                walk(sub, path + ([label] if label else []),
                     keys + ([_accelerator(attrs)] if label else []), seen)
            elif kind == "link":
                pl = launchers.get(attrs.get("plid", "").lower())
                if not pl:
                    continue
                label = _caption(attrs.get("caption", pl.get("caption", "")))
                if not label:
                    continue
                key = _accelerator(attrs) or _accelerator(pl)
                row = {
                    "path": "|".join(path + [label]),
                    "caption": label,
                    "process": pl.get("command", ""),
                    "parameters": pl.get("params", ""),
                    "shortcut": ",".join(k for k in keys + [key] if k),
                    "shortcut2": pl.get("shortcut2", "") if shortcuts else "",
                }
                if shortcuts:
                    row["key"] = pl.get("shortcut1", "")
                rows.append(row)

    walk(root[3], [], [], {root[1].lower()})
    return rows


def dump_menu_tree(editor: str, include_context_menus: bool,
                   include_shortcuts: bool) -> dict[str, Any]:
    if editor not in (*_FILES, "all"):
        return {"ok": False, "error": "editor must be pcb, sch, pcblib, schlib, project or all"}
    system = _system_dir()
    launchers, trees = _resources(system)
    editors = list(_FILES) if editor == "all" else [editor]
    menus: list[dict[str, Any]] = []
    missing = []
    for kind in editors:
        _, main, popup = _FILES[kind]
        for root_id, context in ((main, False), (popup, True)):
            if not root_id or (context and not include_context_menus):
                continue
            root = trees.get(root_id.lower())
            if root is None:
                missing.append(root_id)
                continue
            for row in _menu_rows(root, launchers, trees, context=context,
                                  shortcuts=include_shortcuts):
                row["editor"] = kind
                row["context_menu"] = context
                menus.append(row)
    shortcuts = []
    if include_shortcuts:
        seen = set()
        for row in menus:
            for key in (row.get("key"), row.get("shortcut2")):
                token = (row["editor"], key, row["process"], row["parameters"])
                if key and token not in seen:
                    shortcuts.append({"editor": row["editor"], "key": key,
                                      "process": row["process"],
                                      "parameters": row["parameters"]})
                    seen.add(token)
    return {"ok": not missing, "editor": editor, "menus": menus,
            "shortcuts": shortcuts, "source": "installed factory RCS resources",
            "live_customizations_included": False, "missing_roots": missing}


def list_panel_catalog() -> dict[str, Any]:
    system = _system_dir()
    launchers, _ = _resources(system)
    panels: dict[str, dict[str, Any]] = {}
    for attrs in launchers.values():
        params = attrs.get("params", "")
        if not re.search(r"\bObjectKind\s*=\s*Panel\b", params, re.I):
            continue
        name = _caption(attrs.get("caption", ""))
        if not name:
            continue
        # RCS launchers do not encode the default dock or all editor filters.
        panels.setdefault(name.casefold(), {"name": name, "editor_kinds": [],
                                            "default_dock": None})
    return {"ok": True, "panels": sorted(panels.values(), key=lambda p: p["name"].casefold()),
            "source": "installed factory RCS launchers",
            "complete_live_catalog": False}


def read_resource_file(name: str) -> dict[str, Any]:
    system = _system_dir()
    if not name or Path(name).name != name or not name.lower().endswith(".rcs"):
        return {"ok": False, "error": "name must be a bare .rcs filename"}
    matches = [p for p in system.glob("*.rcs") if p.name.casefold() == name.casefold()]
    if len(matches) != 1:
        return {"ok": False, "error": "RCS resource not found"}
    path = matches[0]
    return {"ok": True, "name": path.name, "text": _read(path),
            "source": "installed factory RCS resource"}


def register_resource_catalog_tools(mcp) -> None:
    @mcp.tool()
    async def app_dump_menu_tree(editor: str = "all", include_context_menus: bool = False,
                                 include_shortcuts: bool = True) -> dict[str, Any]:
        """Read installed Altium RCS menu definitions without focus or clicks.

        Returns factory entries; live extensions and user customisations may differ.
        """
        return dump_menu_tree(editor, include_context_menus, include_shortcuts)

    @mcp.tool()
    async def app_list_panel_catalog() -> dict[str, Any]:
        """Read factory panel launchers from installed RCS resources, without clicks."""
        return list_panel_catalog()

    @mcp.tool()
    async def app_read_resource_file(name: str) -> dict[str, Any]:
        """Read one installed System/*.rcs file by bare filename, without clicks."""
        return read_resource_file(name)

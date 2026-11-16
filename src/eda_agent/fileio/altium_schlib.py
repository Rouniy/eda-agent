# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Headless .SchLib reader (roadmap V1: library hygiene).

An Altium ``.SchLib`` is an OLE compound document with one storage per
component (``<CompName>/Data``), whose first record is the same
``|KEY=VALUE|`` ASCII header as a schematic component (RECORD=1:
``LibReference``, ``ComponentDescription``). The rest of each Data stream is
Altium's BINARY pin format, not reverse-engineered here (same discipline as
the PcbDoc reader: no guessing a binary layout without ground truth). So this
reader covers the component *header* level, which is enough for the highest-
value library-hygiene checks (undocumented or unnamed parts).
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

_NON_COMPONENT_STREAMS = {"Storage", "FileHeader"}


def read_schlib_components(path: str | Path) -> list[dict[str, Any]]:
    """Return each library component's header ``{name, storage_name,
    lib_reference, description, alias_list}``.

    Enumerates the per-component storages and parses the first (ASCII)
    record of each ``Data`` stream. Raises ValueError if the file is not a
    valid SchLib OLE container.
    """
    import olefile

    path = str(path)
    if not olefile.isOleFile(path):
        raise ValueError(f"not an OLE compound file (not a .SchLib?): {path}")
    ole = olefile.OleFileIO(path)
    try:
        comp_storages = sorted(
            entry[0] for entry in ole.listdir()
            if len(entry) == 2 and entry[1] == "Data"
            and entry[0] not in _NON_COMPONENT_STREAMS
        )
        out: list[dict[str, Any]] = []
        for storage_name in comp_storages:
            data = ole.openstream([storage_name, "Data"]).read()
            hdr = _parse_first_record(data)
            lib_reference = hdr.get("LIBREFERENCE", "")
            out.append({
                "name": lib_reference or storage_name,
                "storage_name": storage_name,
                "lib_reference": lib_reference,
                "description": hdr.get("COMPONENTDESCRIPTION", ""),
                "alias_list": hdr.get("ALIASLIST", ""),
            })
        return out
    finally:
        ole.close()


def _parse_first_record(data: bytes) -> dict[str, str]:
    if len(data) < 4:
        return {}
    length = struct.unpack("<I", data[:4])[0]
    payload = data[4:4 + length].rstrip(b"\x00")
    text = payload.decode("latin-1", "replace")
    fields: dict[str, str] = {}
    for part in text.split("|"):
        if "=" in part:
            key, value = part.split("=", 1)
            fields[key.upper()] = value
    return fields

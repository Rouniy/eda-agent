# SPDX-License-Identifier: Apache-2.0
"""sch_place_dblib_components: database-library placement.

``sch_place_components`` loads a bare SchLib symbol, so a DbLib part placed
through it has no footprint, no table name and no database link. This tool
goes through ``LoadComponentFromDatabaseLibrary`` instead. These tests pin
the wire payload and the Pascal handler it reaches; the live behaviour
(full path + bare key value loads the record, part B of a dual op-amp
needs an explicit part id) was measured on Altium 21.3.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from eda_agent.tools import generic as g
from eda_agent.tools.generic import DBLIB_PLACEMENT_KEYS
from tests.pascal_source import load

GENERIC_PAS = Path(__file__).resolve().parents[1] / "scripts" / "altium" / "Generic.pas"
DBLIB = "D:\\Lib\\Celestial.DbLib"


class _Sent:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []


@pytest.fixture
def tool(monkeypatch):
    sent = _Sent()

    class FakeBridge:
        async def send_command_async(self, command, params=None, timeout=None):
            sent.calls.append((command, params))
            return {"ok": True, "success": True, "count": 99}

    monkeypatch.setattr("eda_agent.tools.generic.get_bridge", lambda: FakeBridge())
    captured = {}

    class DummyMcp:
        def tool(self):
            def decorator(fn):
                captured[fn.__name__] = fn
                return fn
            return decorator

    g.register_generic_tools(DummyMcp())
    return captured["sch_place_dblib_components"], sent


def _run(coro):
    return asyncio.run(coro)


def test_payload_carries_table_key_and_defaults(tool):
    fn, sent = tool
    _run(fn(dblib_path=DBLIB, placements=[{
        "table": "Capacitors - Ceramic - 0603",
        "part_number": "C0603C104K5RAC7411",
        "x": 2000, "y": 3000, "designator": "C2"}]))
    command, params = sent.calls[-1]
    assert command == "generic.place_dblib_components"
    op = params["placements"]
    assert f"dblib_path={DBLIB}" in op
    assert "table=Capacitors - Ceramic - 0603" in op
    assert "key_field=Part Number" in op
    assert "key_value=C0603C104K5RAC7411" in op
    assert "part_id=1" in op, "part A must be the default sub-part"
    assert "designator=C2" in op


def test_second_sub_part_shares_the_designator(tool):
    fn, sent = tool
    _run(fn(dblib_path=DBLIB, placements=[
        {"table": "T", "part_number": "LM2904DR", "x": 0, "y": 0, "designator": "U3"},
        {"table": "T", "part_number": "LM2904DR", "x": 1500, "y": 0,
         "designator": "U3", "part_id": 2},
    ]))
    ops = sent.calls[-1][1]["placements"].split("~~")
    assert len(ops) == 2
    assert "part_id=1" in ops[0] and "part_id=2" in ops[1]


def test_per_placement_dblib_overrides_the_top_level_one(tool):
    fn, sent = tool
    _run(fn(dblib_path=DBLIB, placements=[{
        "table": "T", "part_number": "P", "dblib_path": "E:\\Other.DbLib"}]))
    assert "dblib_path=E:\\Other.DbLib" in sent.calls[-1][1]["placements"]


def test_unknown_key_is_rejected_before_the_bridge(tool):
    fn, sent = tool
    out = _run(fn(dblib_path=DBLIB, placements=[{
        "table": "T", "part_number": "P", "library_path": "x.SchLib"}]))
    assert out["error"] == "UNKNOWN_PLACEMENT_KEYS"
    assert "library_path" in out["reason"]
    assert sent.calls == []


@pytest.mark.parametrize("placement", [
    {"part_number": "P"},                      # no table
    {"table": "T"},                            # no key
])
def test_missing_fields_are_rejected(tool, placement):
    fn, sent = tool
    out = _run(fn(dblib_path=DBLIB, placements=[placement]))
    assert out["error"] == "MISSING_FIELD"
    assert sent.calls == []


def test_missing_dblib_path_is_rejected(tool):
    fn, sent = tool
    out = _run(fn(placements=[{"table": "T", "part_number": "P"}]))
    assert out["error"] == "MISSING_FIELD"
    assert sent.calls == []


def test_documented_keys_are_all_accepted():
    assert DBLIB_PLACEMENT_KEYS == {
        "dblib_path", "table", "part_number", "key_field", "keys",
        "x", "y", "rotation", "designator", "part_id"}


def test_native_command_receives_exact_sheet(tool):
    fn, sent = tool
    _run(fn(dblib_path=DBLIB, placements=[
        {"table": "T", "part_number": "P"}]))
    assert sent.calls[-1][1]["sheet_path"] == ""


def test_invalid_part_or_rotation_never_reaches_bridge(tool):
    fn, sent = tool
    for bad in ({"part_id": 0}, {"rotation": 45}):
        out = _run(fn(dblib_path=DBLIB, placements=[
            {"table": "T", "part_number": "P", **bad}]))
        assert out["error"] == "BAD_ROTATION_OR_PART_ID"
    assert sent.calls == []


def test_pascal_handler_loads_from_the_database_and_sets_the_part():
    funcs = load(GENERIC_PAS)
    handler = funcs["Gen_PlaceDbLibComponents"]
    assert "TryLoadDbLibComponent" in handler
    assert "LoadComponentFromDatabaseLibrary" in funcs["TryLoadDbLibComponent"]
    assert "CurrentPartID" in handler
    assert "LOAD_FAILED" in handler and "MISSING_FIELD" in handler
    assert "GetSchDocumentByPath" in handler
    assert "SHEET_MISMATCH" in handler
    assert "PART_REFUSED" in handler
    assert "DATABASE_LINK_MISSING" in handler
    assert "WRONG_DOC_KIND" in handler

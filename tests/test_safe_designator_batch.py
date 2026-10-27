"""A designator batch must refuse collisions before sending any write."""

import copy
import pytest

from eda_agent.tools import generic


class Capture:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class Bridge:
    def __init__(self):
        self.rows = [
            {"UniqueId": "A", "Designator.Text": "R1", "_doc": r"C:\qa\A.SchDoc"},
            {"UniqueId": "B", "Designator.Text": "R2", "_doc": r"C:\qa\A.SchDoc"},
            {"UniqueId": "C", "Designator.Text": "C1", "_doc": r"C:\qa\B.SchDoc"},
        ]
        self.batches = []
        self.fail_after_first_op = False

    async def send_command_async(self, command, params, **kwargs):
        if command == "project.load_project_sheets":
            return {"total_sheets": 2, "loaded": 0, "already_loaded": 2, "failed": 0}
        if command == "generic.query_objects":
            return {"objects": copy.deepcopy(self.rows), "count": len(self.rows),
                    "sheets_processed": 2}
        if command == "generic.batch_modify":
            ops = params["operations"].split("~~")
            self.batches.append(ops)
            for op in ops[:1] if self.fail_after_first_op else ops:
                uid = op.split("filter=UniqueId=", 1)[1].split(";", 1)[0]
                name = op.split("set=Designator.Text=", 1)[1]
                for row in self.rows:
                    if row["UniqueId"] == uid:
                        row["Designator.Text"] = name
            return {"operations_processed": len(ops), "operations_skipped": 0}
        raise AssertionError(command)


def make_tool(monkeypatch, bridge):
    monkeypatch.setattr(generic, "get_bridge", lambda: bridge)
    c = Capture()
    generic.register_generic_tools(c)
    return c.tools["sch_batch_rename_designators"]


@pytest.mark.asyncio
async def test_swap_uses_unique_intermediate_names_and_verifies(monkeypatch):
    bridge = Bridge()
    tool = make_tool(monkeypatch, bridge)
    plan = await tool(r"C:\qa\Board.PrjPcb", [
        {"unique_id": "A", "to": "R2"}, {"unique_id": "B", "to": "R1"}])
    assert plan["ok"] and plan["dry_run"] and not bridge.batches
    result = await tool(r"C:\qa\Board.PrjPcb", [
        {"unique_id": "A", "to": "R2"}, {"unique_id": "B", "to": "R1"}],
        dry_run=False, expected_snapshot=plan["snapshot"])
    assert result["ok"] and result["verified"] and len(bridge.batches) == 2
    assert all("ZZZ" in op for op in bridge.batches[0])
    assert [r["Designator.Text"] for r in bridge.rows] == ["R2", "R1", "C1"]


@pytest.mark.asyncio
async def test_collision_and_stale_snapshot_refuse_before_write(monkeypatch):
    bridge = Bridge()
    tool = make_tool(monkeypatch, bridge)
    collision = await tool(r"C:\qa\Board.PrjPcb", [
        {"unique_id": "A", "to": "C1"}])
    assert collision["reason"] == "final designator collision"
    stale = await tool(r"C:\qa\Board.PrjPcb", [
        {"unique_id": "A", "to": "R9"}], dry_run=False,
        expected_snapshot="old")
    assert stale["reason"] == "snapshot changed or was not supplied"
    assert not bridge.batches


@pytest.mark.asyncio
async def test_partial_first_phase_stops_before_final_names(monkeypatch):
    bridge = Bridge()
    bridge.fail_after_first_op = True
    tool = make_tool(monkeypatch, bridge)
    renames = [{"unique_id": "A", "to": "R2"},
               {"unique_id": "B", "to": "R1"}]
    plan = await tool(r"C:\qa\Board.PrjPcb", renames)
    result = await tool(r"C:\qa\Board.PrjPcb", renames, dry_run=False,
                        expected_snapshot=plan["snapshot"])
    assert not result["ok"] and result["phase"] == "temporary"
    assert len(bridge.batches) == 1
    assert len({r["Designator.Text"] for r in bridge.rows}) == 3

# SPDX-License-Identifier: Apache-2.0
"""xSignal reads are board-scoped and complete."""

import asyncio

from eda_agent.tools import pcb


PATH = r"D:\scratch\Board.PcbDoc"


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class _Bridge:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    async def send_command_async(self, command, params, timeout=None):
        self.calls.append((command, params))
        return self.reply


def _get(monkeypatch, reply):
    bridge = _Bridge(reply)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    return mcp.tools["pcb_get_xsignals"], bridge


def test_exact_board_complete_read(monkeypatch):
    pair = {"name": "U1.3-U2.2", "length_mils": 821.0, "path": ["U1.3", "U2.2"]}
    get, bridge = _get(monkeypatch, {"board_path": PATH, "count": 1, "xsignals": [pair]})
    assert asyncio.run(get(PATH))["xsignals"] == [pair]
    assert bridge.calls == [("pcb.get_xsignals", {"board_path": PATH})]


def test_wrong_board_or_missing_pair_is_not_a_complete_read(monkeypatch):
    for reply in ({"board_path": r"D:\scratch\Other.PcbDoc", "count": 0, "xsignals": []},
                  {"board_path": PATH, "count": 1, "xsignals": []}):
        get, _ = _get(monkeypatch, reply)
        assert asyncio.run(get(PATH))["ok"] is False


def test_relative_board_path_is_refused_locally(monkeypatch):
    get, bridge = _get(monkeypatch, {"board_path": PATH, "count": 0, "xsignals": []})
    assert asyncio.run(get("Board.PcbDoc"))["ok"] is False
    assert not bridge.calls


def test_create_requires_fresh_count_and_verifies_new_pair(monkeypatch):
    reply = {"board_path": PATH, "count_before": 1, "count_after": 2,
             "returned_pairs": True, "class_assigned": True,
             "class_membership_verified": True,
             "created": [{"name": "U1.1-U2.2"}]}
    bridge = _Bridge(reply)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    create = mcp.tools["pcb_create_xsignals"]
    assert asyncio.run(create(PATH, 1, ["U1.1", "U2.2"], "CLK"))["count_after"] == 2
    assert bridge.calls == [("pcb.create_xsignals", {
        "board_path": PATH, "expected_count": "1", "pins": "U1.1\tU2.2", "class_name": "CLK"})]
    bridge.reply = {**reply, "created": []}
    assert asyncio.run(create(PATH, 1, ["U1.1", "U2.2"], "CLK"))["ok"] is False
    bridge.reply = {**reply, "class_membership_verified": False}
    assert asyncio.run(create(PATH, 1, ["U1.1", "U2.2"], "CLK"))["ok"] is False


def test_delete_checks_readback_and_rejects_empty_request(monkeypatch):
    reply = {"board_path": PATH, "count_before": 2, "count_after": 1,
             "deleted": ["U1.1-U2.2"]}
    bridge = _Bridge(reply)
    monkeypatch.setattr(pcb, "get_bridge", lambda: bridge)
    mcp = _Mcp()
    pcb.register_pcb_tools(mcp)
    delete = mcp.tools["pcb_delete_xsignals"]
    assert asyncio.run(delete(PATH, 2, ["U1.1-U2.2"]))["count_after"] == 1
    assert bridge.calls == [("pcb.delete_xsignals", {
        "board_path": PATH, "expected_count": "2", "names": "U1.1-U2.2", "all": "false"})]
    assert asyncio.run(delete(PATH, 2))["ok"] is False
    assert len(bridge.calls) == 1

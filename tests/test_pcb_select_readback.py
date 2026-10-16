"""PCB selection must not repeat the 2026-10-16 false-success incident."""

import asyncio

from eda_agent.tools import generic


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(function):
            self.tools[function.__name__] = function
            return function
        return register


class _Bridge:
    def __init__(self, version, selected):
        self.version = version
        self.selected = selected
        self.commands = []

    async def send_command_async(self, command, params=None):
        self.commands.append(command)
        if command == "application.ping":
            return {"script_version": self.version}
        if command == "application.get_active_document":
            return {"document_kind": "PCB", "file_path": r"C:\board.PcbDoc"}
        if command == "pcb.select_component":
            return {"selected": True}
        if command == "generic.query_objects":
            return {"objects": [{"Designator": "FD4",
                                 "Selected": "true" if self.selected else "false"}]}
        raise AssertionError(command)


def test_old_loaded_script_cannot_claim_selection(monkeypatch):
    mcp = _Mcp()
    generic.register_generic_tools(mcp)
    bridge = _Bridge("2026.10.14.5", selected=False)
    monkeypatch.setattr(generic, "get_bridge", lambda: bridge)

    result = asyncio.run(mcp.tools["pcb_select"]("FD4"))

    assert result["success"] is False
    assert "pcb.select_component" not in bridge.commands


def test_match_is_not_success_when_second_read_is_unselected(monkeypatch):
    mcp = _Mcp()
    generic.register_generic_tools(mcp)
    bridge = _Bridge("2026.10.16.3", selected=False)
    monkeypatch.setattr(generic, "get_bridge", lambda: bridge)

    result = asyncio.run(mcp.tools["pcb_select"]("FD4"))

    assert result["success"] is False
    assert result["selected"] is False
    assert bridge.commands.index("generic.query_objects") > bridge.commands.index("pcb.select_component")

"""The public Owner alias uses the native Component property."""

import asyncio

from eda_agent.tools import pcb as pcb_mod


def test_owner_property_and_filter_translate_to_component(monkeypatch):
    registered = {}

    class DummyMcp:
        def tool(self, *args, **kwargs):
            def register(fn):
                registered[fn.__name__] = fn
                return fn
            return register

    class Bridge:
        async def send_command_async(self, command, params):
            assert command == "pcb.query_region"
            assert params["properties"] == "ObjectId,Component"
            assert params["filter"] == "Component=C1|Layer=TopLayer"
            return {"objects": [{"ObjectId": "1", "Component": "C1"}], "count": 1}

    monkeypatch.setattr(pcb_mod, "get_bridge", lambda: Bridge())
    pcb_mod.register_pcb_tools(DummyMcp())
    out = asyncio.run(registered["pcb_query_region"](
        object_type="ePadObject", x1=0, y1=0, x2=10, y2=10,
        properties="ObjectId,Owner", filter="Owner=C1|Layer=TopLayer",
    ))
    assert out["objects"] == [{"ObjectId": "1", "Owner": "C1"}]

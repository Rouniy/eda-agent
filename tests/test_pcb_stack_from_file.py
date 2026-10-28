# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""The saved stack, read from the file, catches what the legacy read missed.

Found on the Rosen controller (AD 25.8.1, 2026-10-27). A 4- to 6-layer change
through pcb_add_layer / pcb_remove_layer / pcb_modify_layer read back as
intended in pcb_get_layer_stackup. The saved V9 stack held two dielectrics
between L1 and L2, one of them -0.3944 mil, summing to 1.77 mil where the
legacy view said 4.33. The records below copy that board's pattern (names
generic, values as found).
"""
from __future__ import annotations

import asyncio
import base64
import zlib

import pytest

from eda_agent.fileio import altium_pcb_stack as stack
from eda_agent.tools import pcb as pcb_tools
from eda_agent.tools import metadata


_TOP, _BOT = 16777217, 16842751


def _v9(entries):
    out = []
    for i, e in enumerate(entries):
        for k, v in e.items():
            out.append(f"V9_STACK_LAYER{i}_{k}={v}")
    return out


def _legacy(chain):
    out = []
    numbers = [n for n, *_ in chain]
    for i, (n, name, cop, dt, h) in enumerate(chain):
        prev = numbers[i - 1] if i else 0
        nxt = numbers[i + 1] if i + 1 < len(numbers) else 0
        out += [f"LAYER{n}NAME={name}", f"LAYER{n}PREV={prev}", f"LAYER{n}NEXT={nxt}",
                f"LAYER{n}COPTHICK={cop}", f"LAYER{n}DIELTYPE={dt}",
                f"LAYER{n}DIELHEIGHT={h}"]
    return out


def _data(v9, legacy) -> bytes:
    return ("|RECORD=Board|" + "|".join(v9 + legacy) + "|").encode("latin-1")


def _cu(name, layer_id, t="1.378mil"):
    return {"NAME": name, "LAYERID": layer_id, "COPTHICK": t}


def _diel(name, n, t, kind="2", dk="4.000"):
    return {"NAME": name, "LAYERID": 17039360 + n, "DIELTYPE": kind,
            "DIELHEIGHT": t, "DIELCONST": dk, "DIELMATERIAL": "FR-4"}


MASK_TOP = {"NAME": "Top Solder", "LAYERID": 16973834, "DIELTYPE": "3",
            "DIELHEIGHT": "0.4mil", "DIELCONST": "3.500"}
MASK_BOT = {"NAME": "Bottom Solder", "LAYERID": 16973835, "DIELTYPE": "3",
            "DIELHEIGHT": "0.4mil", "DIELCONST": "3.500"}

BROKEN = _data(
    _v9([{"NAME": "Top Overlay", "LAYERID": 16973830}, MASK_TOP,
         _cu("L1", _TOP), _diel("Dielectric 1", 1, "-0.3944mil"),
         _diel("Dielectric 2", 4, "2.165mil"), _cu("L2", _TOP + 1),
         _diel("Dielectric 6", 6, "3.937mil", "1"), _cu("L3", _BOT),
         MASK_BOT]),
    _legacy([(1, "L1", "1.378mil", 2, "4.33mil"),
             (2, "L2", "1.378mil", 1, "3.937mil"),
             (32, "L3", "1.378mil", 0, "12.6mil")]))

GOOD = _data(
    _v9([MASK_TOP, _cu("Top", _TOP, "0.7mil"),
         _diel("Dielectric 1", 1, "4.7244mil"), _diel("Dielectric 2", 4, "4.7244mil"),
         _cu("Plane", 16842753, "0.7mil"), _diel("Dielectric 3", 2, "55.1181mil", "1", "4.550"),
         _cu("Bottom", _BOT, "0.7mil"), MASK_BOT]),
    _legacy([(1, "Top", "0.7mil", 2, "9.4488mil"),
             (39, "Plane", "0.7mil", 1, "55.1181mil"),
             (32, "Bottom", "0.7mil", 0, "12.6mil")]))


def _read(monkeypatch, data):
    monkeypatch.setattr(stack, "read_board_data", lambda path: data)
    return stack.read_stack("board.PcbDoc")


def test_the_broken_write_is_caught(monkeypatch):
    out = _read(monkeypatch, BROKEN)
    assert out["ok"] is False
    checks = [(f["severity"], f["check"]) for f in out["findings"]]
    assert ("error", "thickness") in checks
    assert ("error", "views_disagree") in checks
    disagree = next(f for f in out["findings"] if f["check"] == "views_disagree")
    assert "1.7706" in disagree["detail"] and "4.33" in disagree["detail"]


def test_a_good_stack_with_split_prepreg_passes(monkeypatch):
    out = _read(monkeypatch, GOOD)
    assert out["ok"] is True
    assert [f["check"] for f in out["findings"]] == ["split_dielectric"]
    assert out["summary"]["copper_layers"] == 3
    assert out["summary"]["dielectric_layers"] == 3
    assert out["summary"]["board_mils"] == pytest.approx(2.1 + 64.5669, abs=1e-3)


def test_additive_and_nonconductive_copper_are_reported(monkeypatch):
    data = _data(
        _v9([_cu("Top", _TOP), _diel("D1", 1, "4mil"),
             dict(_cu("Mid", _TOP + 1), ISADDITIVELAYER="TRUE",
                  ELECTRICALRESISTIVITY="2147483647"),
             _diel("D2", 2, "4mil"), _cu("Bottom", _BOT)]),
        _legacy([(1, "Top", "1.378mil", 1, "4mil"),
                 (2, "Mid", "1.378mil", 1, "4mil"),
                 (32, "Bottom", "1.378mil", 0, "0mil")]))
    out = _read(monkeypatch, data)
    assert out["ok"] is False
    assert {f["check"] for f in out["findings"] if f["severity"] == "error"} == {
        "additive", "non_conductive"}


def test_stale_manager_model_is_a_warning(monkeypatch):
    xml = ('<StackupDocument><Layer Id="aaa" TypeId="x" Name="Top">'
           '<Property Name="Thickness" Type="LengthValue">0.01778mm</Property>'
           '</Layer></StackupDocument>')
    model = base64.b64encode(zlib.compress(xml.encode())).decode()
    data = _data(
        _v9([dict(_cu("Top", _TOP), ID="{AAA}"), _diel("D1", 1, "4mil"),
             _cu("Bottom", _BOT)]) + [f"V9_STACKCUSTOMDATA={model}"],
        _legacy([(1, "Top", "1.378mil", 1, "4mil"),
                 (32, "Bottom", "1.378mil", 0, "0mil")]))
    out = _read(monkeypatch, data)
    assert out["ok"] is True
    assert [f["check"] for f in out["findings"]] == ["stack_manager_model_stale"]
    assert out["findings"][0]["layers"][0].startswith("Top thickness:")


def test_manager_model_material_dk_and_loss_are_compared(monkeypatch):
    properties = (('<Property Name="Thickness" Type="LengthValue">4mil</Property>')
                  + '<Property Name="Material" Type="String">OLD</Property>'
                  + '<Property Name="DielectricConstant" Type="Float">4.2</Property>'
                  + '<Property Name="LossTangent" Type="Float">0.03</Property>')
    xml = ('<StackupDocument><Layer Id="bbb" TypeId="x" Name="D1">'
           + properties + '</Layer></StackupDocument>')
    model = base64.b64encode(zlib.compress(xml.encode())).decode()
    data = _data(
        _v9([_cu("Top", _TOP), dict(_diel("D1", 1, "4mil", dk="4.000"),
                                     ID="{BBB}", DIELLOSSTANGENT="0.010"),
             _cu("Bottom", _BOT)]) + [f"V9_STACKCUSTOMDATA={model}"],
        _legacy([(1, "Top", "1.378mil", 1, "4mil"),
                 (32, "Bottom", "1.378mil", 0, "0mil")]))
    out = _read(monkeypatch, data)
    assert out["ok"] is True
    assert out["layers"][1]["loss_tangent"] == pytest.approx(0.01)
    warning = next(f for f in out["findings"] if f["check"] == "stack_manager_model_stale")
    assert len(warning["layers"]) == 3
    assert all(any(field in line for line in warning["layers"])
               for field in ("dielectric_constant", "loss_tangent", "material"))


def test_manager_reset_refuses_an_open_board(monkeypatch, tmp_path):
    board = tmp_path / "board.PcbDoc"
    board.write_bytes(b"scratch")
    calls = []

    class Registry:
        def __init__(self):
            self.tools = {}

        def tool(self, *args, **kwargs):
            def register(fn):
                self.tools[fn.__name__] = fn
                return fn
            return register

    class Bridge:
        async def send_command_async(self, command, params=None):
            return [{"file_path": str(board), "loaded": True}]

    monkeypatch.setattr(pcb_tools, "get_bridge", lambda: Bridge())
    monkeypatch.setattr(stack, "reset_manager_model",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    registry = Registry()
    pcb_tools.register_pcb_tools(registry)
    apply = asyncio.run(registry.tools["pcb_reset_stack_manager_model"](
        str(board), expected_sha256="a" * 64, dry_run=False))
    assert apply["ok"] is False and "open in Altium" in apply["reason"]
    assert calls == []
    assert board.read_bytes() == b"scratch"


def test_kinds_come_from_the_layer_id():
    layers = stack.physical_stack(stack.board_keys(GOOD))
    assert [l["kind"] for l in layers] == [
        "solder_mask", "copper", "dielectric", "dielectric", "copper",
        "dielectric", "copper", "solder_mask"]
    assert layers[5]["dielectric_type"] == "core"
    assert layers[5]["dielectric_constant"] == pytest.approx(4.55)


def test_copper_against_copper_is_an_error():
    layers = [{"name": "A", "kind": "copper", "thickness_mils": 1.0},
              {"name": "B", "kind": "copper", "thickness_mils": 1.0}]
    assert "no_dielectric" in {f["check"] for f in stack.check(layers, [])}


def test_copper_order_differing_between_views_is_an_error(monkeypatch):
    data = _data(
        _v9([_cu("Top", _TOP), _diel("D1", 1, "5mil"), _cu("Bottom", _BOT)]),
        _legacy([(1, "Bottom", "1.378mil", 2, "5mil"),
                 (32, "Top", "1.378mil", 0, "0mil")]))
    out = _read(monkeypatch, data)
    assert out["ok"] is False and out["findings"][0]["check"] == "views_disagree"


@pytest.mark.parametrize("text,mils", [
    ("1.378mil", 1.378), ("0.035mm", 0.035 / 0.0254), ("35um", 35 / 25.4),
    ("12", 12.0), ("-0.3944mil", -0.3944), ("", None), ("abc", None)])
def test_units(text, mils):
    got = stack.to_mils(text)
    assert got == (pytest.approx(mils) if mils is not None else None)


def test_expected_stack_mismatches_are_listed():
    layers = stack.physical_stack(stack.board_keys(GOOD))
    expected = [{"kind": "copper", "name": "Top"},
                {"kind": "dielectric", "thickness_mils": 4.7244},
                {"kind": "dielectric", "thickness_mils": 4.7244},
                {"kind": "copper", "name": "Plane"},
                {"kind": "dielectric", "thickness_mils": 37.4, "dielectric_type": "core"},
                {"kind": "copper", "name": "Bottom"}]
    out = stack.compare_expected(layers, expected)
    assert [(m["check"], m["order"]) for m in out] == [("thickness_mils", 4)]


def test_offline_tool_checks_saved_stack_without_bridge(monkeypatch, tmp_path):
    board = tmp_path / "saved.PcbDoc"
    board.write_bytes(b"fixture bytes")
    monkeypatch.setattr(stack, "read_board_data", lambda path: GOOD)

    class Registry:
        def __init__(self):
            self.tools = {}

        def tool(self, *args, **kwargs):
            def register(fn):
                self.tools[fn.__name__] = fn
                return fn
            return register

    registry = Registry()
    pcb_tools.register_pcb_tools(registry)
    out = asyncio.run(registry.tools["pcb_stack_from_file"](
        str(board), expected=[{"kind": "copper", "name": "Wrong"}]))
    assert out["ok"] is False
    assert out["summary"]["copper_layers"] == 3
    assert {m["check"] for m in out["mismatches"]} == {"count", "name"}
    assert metadata.maturity_of("pcb_stack_from_file") == metadata.OFFLINE


def test_missing_saved_stack_is_not_reported_as_healthy(monkeypatch):
    monkeypatch.setattr(stack, "read_board_data", lambda path: b"|RECORD=Board|")
    out = stack.read_stack("unused.PcbDoc")
    assert out["ok"] is False
    assert {f["check"] for f in out["findings"]} == {
        "missing_physical_stack", "missing_legacy_chain"}


def test_legacy_stack_writes_need_explicit_opt_in(monkeypatch):
    class Registry:
        def __init__(self):
            self.tools = {}

        def tool(self, *args, **kwargs):
            def register(fn):
                self.tools[fn.__name__] = fn
                return fn
            return register

    registry = Registry()
    pcb_tools.register_pcb_tools(registry)
    calls = [
        ("pcb_add_layer", {"layer": "MidLayer1"}),
        ("pcb_remove_layer", {"layer": "MidLayer1"}),
        ("pcb_modify_layer", {"layer": "TopLayer", "dielectric_height_mils": 4.2}),
        ("pcb_configure_multilayer_stackup", {"operations": [
            {"action": "add", "layer": "MidLayer1"}], "dry_run": False}),
    ]
    for name, kwargs in calls:
        out = asyncio.run(registry.tools[name](**kwargs))
        assert out["error"] == "LEGACY_STACK_WRITE"

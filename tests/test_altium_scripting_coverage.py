# SPDX-License-Identifier: Apache-2.0
"""Keep the official-Altium audit traceable from docs to callable code."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERIC_PY = ROOT / "src" / "eda_agent" / "tools" / "generic.py"
PCB_PY = ROOT / "src" / "eda_agent" / "tools" / "pcb.py"
GENERIC_PAS = ROOT / "scripts" / "altium" / "Generic.pas"
PCB_PAS = ROOT / "scripts" / "altium" / "PCB.pas"
COVERAGE = ROOT / "docs" / "ALTIUM_SCRIPTING_COVERAGE.md"
REFERENCE = ROOT / "docs" / "TOOL_REFERENCE.md"


# Public name -> (wrapper source, bridge command, Pascal source, API marker).
AUDITED_TOOLS = {
    "pcb_query_region": (PCB_PY, "pcb.query_region", PCB_PAS,
                         "SpatialIterator_Create"),
    "sch_query_region": (GENERIC_PY, "generic.query_region", GENERIC_PAS,
                         "AddFilter_Area"),
    "pcb_get_used_layers": (PCB_PY, "pcb.get_used_layers", PCB_PAS,
                            "LayerIsUsed"),
    "pcb_get_drill_layer_pairs": (
        PCB_PY, "pcb.get_drill_layer_pairs", PCB_PAS,
        "DrillLayerPairsCount"),
    "pcb_get_internal_planes": (
        PCB_PY, "pcb.get_internal_planes", PCB_PAS,
        "InternalPlaneNetName"),
    "pcb_get_special_strings": (
        PCB_PY, "pcb.get_special_strings", PCB_PAS, "ConvertedString"),
    "sch_get_component_models": (
        GENERIC_PY, "generic.get_component_models", GENERIC_PAS,
        "ISch_Implementation"),
    "obj_measure_distance": (
        GENERIC_PY, "generic.measure_distance", GENERIC_PAS,
        "Gen_MeasureDistance"),
    "sch_place_compile_mask": (
        GENERIC_PY, "generic.place_compile_mask", GENERIC_PAS,
        "eCompileMask"),
}


def test_every_audited_public_tool_has_the_full_trace():
    """A docs row must lead to a wrapper, command, and real API call."""
    coverage = COVERAGE.read_text(encoding="utf-8")
    reference = REFERENCE.read_text(encoding="utf-8")
    cache: dict[Path, str] = {}

    for tool, (py_path, command, pas_path, marker) in AUDITED_TOOLS.items():
        py = cache.setdefault(py_path, py_path.read_text(encoding="utf-8"))
        pas = cache.setdefault(pas_path, pas_path.read_text(encoding="utf-8"))
        assert f"async def {tool}(" in py
        assert f'"{command}"' in py
        assert marker in pas
        assert f"`{tool}`" in coverage
        assert f"`{tool}`" in reference


def test_live_broken_fillet_is_documented_but_not_public():
    """Do not re-advertise the AD26 iterator deadlock by accident."""
    py = PCB_PY.read_text(encoding="utf-8")
    coverage = COVERAGE.read_text(encoding="utf-8")
    assert "async def pcb_fillet_corners(" not in py
    assert "PCB_FilletCorners" in coverage
    assert "two passes" in coverage


def test_coverage_uses_official_altium_sources():
    text = COVERAGE.read_text(encoding="utf-8")
    assert text.count("https://www.altium.com/documentation/") >= 10
    assert "all Altium methods" in text

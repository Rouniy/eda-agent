# SPDX-License-Identifier: Apache-2.0
"""RCS parsing must report only paths and commands supported by source text."""

from eda_agent.tools import resource_catalog as catalog


def test_menu_tree_resolves_launcher_and_accelerator(monkeypatch, tmp_path):
    (tmp_path / "AdvPcb.rcs").write_text(
        "PL PLPCB:Rules Command='PCB:EditRules' Caption='&Rules...' Params='' End\n"
        "Tree MNPCBMenu Caption='PCB Menu' TopLevel=True\n"
        "  Tree MNDesign Caption='&Design' Popup='D'\n"
        "    Link MNRules PLID='PLPCB:Rules' End\n"
        "  End\n"
        "End\n", encoding="cp1252")
    monkeypatch.setattr(catalog, "_system_dir", lambda: tmp_path)
    result = catalog.dump_menu_tree("pcb", False, True)
    assert result["menus"] == [{
        "path": "Design|Rules...", "caption": "Rules...",
        "process": "PCB:EditRules", "parameters": "", "shortcut": "D,R",
        "shortcut2": "", "key": "", "editor": "pcb", "context_menu": False,
    }]


def test_raw_resource_refuses_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(catalog, "_system_dir", lambda: tmp_path)
    assert catalog.read_resource_file("../secret.rcs")["ok"] is False

# SPDX-License-Identifier: Apache-2.0
"""A session closes only the documents it opened.

The Pascal dispatcher reports, per reply, which of the documents a command
named were not loaded before it and are now (``opened_documents``). The
bridge keeps that list per session, and app_close_opened_documents closes
from it alone: a document the person had open, a project, or one that reads
modified is never closed by it.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from eda_agent.bridge import altium_bridge as ab
from eda_agent.tools import application as app_mod
from eda_agent.tools.registry import ToolRegistry

from tests.conftest import install_bridge_fake
from tests.pascal_source import load

_ALTIUM = Path(__file__).resolve().parents[1] / "scripts" / "altium"

LIB = r"R:\Lib\Passive.SchLib"
BOARD = r"R:\Proj\Board.PcbDoc"
MINE_EDITED = r"R:\Proj\Edited.SchDoc"
USERS = r"R:\Proj\Users.SchDoc"


def _tools():
    registry = ToolRegistry()
    app_mod.register_application_tools(registry)
    return {t.name: t.fn for t in asyncio.run(registry.list_tools())}


class _Bridge:
    def __init__(self, docs):
        self.docs = {d["file_path"]: d for d in docs}
        self.closed = []

    async def send_command_async(self, command, params=None, *a, **k):
        if command == "application.get_open_documents":
            return list(self.docs.values())
        if command == "application.close_document":
            self.closed.append(params["file_path"])
            self.docs.pop(params["file_path"], None)
            return {"closed": True, "file_path": params["file_path"]}
        raise AssertionError(command)


def _doc(path, modified=False, loaded=True):
    return {"file_path": path, "loaded": loaded, "modified": modified}


def test_a_reply_carries_what_its_command_opened():
    got = ab.CommandResponse.from_dict(
        {"id": "x", "success": True, "data": {}, "opened_documents": [LIB]})
    assert got.opened_documents == [LIB]
    assert ab.CommandResponse.from_dict({"id": "x", "success": True}).opened_documents == []


def test_the_list_keeps_each_document_once(tmp_path):
    ab.note_opened_docs(tmp_path, [LIB], "application.set_active_document")
    ab.note_opened_docs(tmp_path, [LIB.lower(), BOARD], "generic.query_objects")
    rows = ab.read_opened_docs(tmp_path)
    assert [r["path"] for r in rows] == [LIB, BOARD]
    assert rows[0]["command"] == "application.set_active_document"


def test_only_what_the_session_opened_is_closed(monkeypatch, tmp_path):
    fake = _Bridge([_doc(LIB), _doc(BOARD), _doc(MINE_EDITED, modified=True), _doc(USERS)])
    workspace = install_bridge_fake(monkeypatch, tmp_path, fake)
    ab.note_opened_docs(workspace, [LIB, BOARD, MINE_EDITED, r"R:\Gone.SchDoc"], "test")
    close = _tools()["app_close_opened_documents"]

    dry = asyncio.run(close())
    assert dry["dry_run"] and sorted(dry["would_close"]) == sorted([LIB, BOARD])
    assert dry["already_closed"] == [r"R:\Gone.SchDoc"]      # no longer open: dropped
    assert fake.closed == []

    out = asyncio.run(close(dry_run=False, keep=[BOARD]))
    assert fake.closed == [LIB]                     # never USERS: the person opened it
    assert out["kept"] == [BOARD] and out["kept_modified"] == [MINE_EDITED]
    assert sorted(out["remaining"]) == sorted([BOARD, MINE_EDITED])
    assert [r["path"] for r in ab.read_opened_docs(workspace)] == [BOARD, MINE_EDITED]


def test_the_dispatcher_reports_opened_documents():
    units = load(_ALTIUM / "StatusForm.pas")
    status = units["ProcessSingleRequest"]
    main = units["OpenedDocsField"] + units["DocIsLoaded"]
    # noted before the handler runs, reported after it, in the one place every command passes
    before = status.index("NamedWereLoaded := LoadedFlags(NamedDocs)")
    handler = status.index("ResponseContent := ProcessCommand(Command, Params, RequestId)")
    after = status.index("OpenedField := OpenedDocsField(NamedDocs, NamedWereLoaded)")
    assert before < handler < after
    assert '"opened_documents":[' in main
    assert "If Client.GetDocumentByPath(FilePath) <> Nil Then Result := True" in main
    # never the comparison assigned straight to a Boolean: that stopped the loop live
    assert ":= Client.GetDocumentByPath(FilePath) <> Nil" not in main

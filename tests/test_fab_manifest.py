# SPDX-License-Identifier: Apache-2.0
"""A fabrication manifest must detect changed board and package bytes."""

from eda_agent.fileio.fab_manifest import seal_package, sha256_file, verify_package


def test_fab_manifest_binds_saved_board_and_all_export_files(tmp_path):
    board = tmp_path / "Main.PcbDoc"
    outjob = tmp_path / "Job1.OutJob"
    package = tmp_path / "export"
    package.mkdir()
    (package / "Gerber").mkdir()
    board.write_bytes(b"board revision 1")
    outjob.write_bytes(b"job revision 1")
    copper = package / "Gerber" / "Main.GTL"
    copper.write_bytes(b"copper")

    sealed = seal_package(package, board, outjob,
                          sha256_file(board), sha256_file(outjob))
    assert sealed["file_count"] == 1
    assert verify_package(package, board)["verified"] is True

    copper.write_bytes(b"changed copper")
    assert "changed=['Gerber/Main.GTL']" in verify_package(package, board)["reason"]
    copper.write_bytes(b"copper")
    (package / "NC Drill").mkdir()
    (package / "NC Drill" / "Main.TXT").write_bytes(b"drill")
    assert "added=['NC Drill/Main.TXT']" in verify_package(package, board)["reason"]
    (package / "NC Drill" / "Main.TXT").unlink()
    board.write_bytes(b"board revision 2")
    assert "saved board hash differs" in verify_package(package, board)["reason"]


def test_fab_manifest_refuses_board_changed_during_export(tmp_path):
    board = tmp_path / "Main.PcbDoc"
    outjob = tmp_path / "Job1.OutJob"
    package = tmp_path / "export"
    package.mkdir()
    board.write_bytes(b"before")
    outjob.write_bytes(b"job")
    (package / "Main.GTL").write_bytes(b"copper")
    before = sha256_file(board)
    board.write_bytes(b"after")
    try:
        seal_package(package, board, outjob, before, sha256_file(outjob))
    except ValueError as exc:
        assert "board changed" in str(exc)
    else:
        raise AssertionError("changed board was sealed")
    assert verify_package(package, board, required=True)["verified"] is False

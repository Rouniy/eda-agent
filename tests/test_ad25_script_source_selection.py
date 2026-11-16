# SPDX-License-Identifier: Apache-2.0
"""A stale installed script project must not shadow a usable source tree."""

from eda_agent import cli


def test_ad25_unsafe_bundle_falls_back_to_source_project(tmp_path, monkeypatch):
    package = tmp_path / "repo" / "src" / "eda_agent"
    bundled = package / "scripts"
    source = tmp_path / "repo" / "scripts" / "altium"
    bundled.mkdir(parents=True)
    source.mkdir(parents=True)
    (bundled / "Altium_API.PrjScr").write_text(
        "[Design]\nUserID=0xFFFFFFFF\nFSMCodingStyle=eFMSDropDownList_OneProcess\n",
        encoding="utf-8",
    )
    (source / "Altium_API.PrjScr").write_text(
        "[Design]\nVersion=1.0\n[Document1]\nDocumentPath=Main.pas\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "get_package_root", lambda: package)

    assert cli.get_bundled_scripts_path() == source

    (bundled / "Altium_API.PrjScr").write_text(
        "[Design]\nVersion=1.0\n", encoding="utf-8",
    )
    assert cli.get_bundled_scripts_path() == bundled

# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 George Saliba <george.saliba@salitronic.com>
"""Check release artifacts and smoke-test the installed wheel.

Run after ``python -m build``: ``python scripts/verify_distribution.py dist``.
It checks the wheel and sdist payloads and wheel metadata, installs the
wheel into a fresh virtual environment, and runs the first user commands.
"""

from __future__ import annotations

import email
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile
from pathlib import Path

REQUIRED = [
    "eda_agent/scripts/Main.pas",
    "eda_agent/scripts/Altium_API.PrjScr",
    "eda_agent/scripts/StatusForm.dfm",
    "eda_agent/easyeda_extension/main.js",
    "eda_agent/easyeda_extension/extension.json",
    "eda_agent/easyeda_extension/build.py",
    "eda_agent/server.py",
]

SDIST_REQUIRED = [
    "/README.md",
    "/LICENSE",
    "/NOTICE",
    "/pyproject.toml",
    "/scripts/altium/Altium_API.PrjScr",
    "/scripts/altium/Main.pas",
    "/extensions/easyeda/main.js",
    "/extensions/easyeda/extension.json",
    "/extensions/easyeda/build.py",
    "/src/eda_agent/server.py",
]


def _require_suffixes(kind: str, names: set[str], suffixes: list[str]) -> None:
    missing = [suffix for suffix in suffixes
               if not any(name.replace("\\", "/").endswith(suffix)
                          for name in names)]
    if missing:
        raise ValueError(f"{kind} is missing: {missing}")


def _check_wheel_metadata(archive: zipfile.ZipFile, names: set[str]) -> None:
    project = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml")
                            .read_text(encoding="utf-8"))["project"]
    metadata_paths = [n for n in names if n.endswith(".dist-info/METADATA")]
    entry_paths = [n for n in names if n.endswith(".dist-info/entry_points.txt")]
    if len(metadata_paths) != 1 or len(entry_paths) != 1:
        raise ValueError("wheel needs one METADATA and one entry_points.txt")
    metadata = email.message_from_bytes(archive.read(metadata_paths[0]))
    for field, expected in (("Version", project["version"]),
                            ("Requires-Python", project["requires-python"])):
        if metadata.get(field) != expected:
            raise ValueError(f"wheel {field}={metadata.get(field)!r}, expected {expected!r}")
    entries = archive.read(entry_paths[0]).decode("utf-8")
    if "eda-agent = eda_agent.server:main" not in entries:
        raise ValueError("wheel is missing the eda-agent console entry point")


def main(dist: str) -> int:
    wheels = sorted(Path(dist).glob("eda_agent-*.whl"))
    sdists = sorted(Path(dist).glob("eda_agent-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        print(f"expected one wheel and one sdist in {dist}; "
              f"found {len(wheels)} wheel(s), {len(sdists)} sdist(s)")
        return 1
    wheel = wheels[0]
    try:
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
            _require_suffixes("wheel", names, REQUIRED + ["/LICENSE", "/NOTICE"])
            _check_wheel_metadata(archive, names)
        with tarfile.open(sdists[0], "r:gz") as archive:
            _require_suffixes("sdist", set(archive.getnames()), SDIST_REQUIRED)
    except (ValueError, OSError, zipfile.BadZipFile, tarfile.TarError) as exc:
        print(f"distribution verification failed: {exc}")
        return 1
    print(f"{wheel.name}: {len(names)} files; {sdists[0].name}: payload present; "
          "wheel metadata matches pyproject.toml")

    with tempfile.TemporaryDirectory() as tmp:
        venv.create(tmp, with_pip=True)
        bindir = Path(tmp) / ("Scripts" if sys.platform == "win32" else "bin")
        python = bindir / ("python.exe" if sys.platform == "win32" else "python")
        subprocess.run([str(python), "-m", "pip", "install", "-q", str(wheel)],
                       check=True)
        exe = bindir / ("eda-agent.exe" if sys.platform == "win32" else "eda-agent")
        for args in (["--version"], ["scripts-path"],
                     ["easyeda-extension", "path"]):
            done = subprocess.run([str(exe), *args], capture_output=True,
                                  text=True)
            print(f"eda-agent {' '.join(args)} -> {done.returncode}: "
                  f"{(done.stdout or done.stderr).strip()}")
            if done.returncode != 0:
                return 1
            if args[0] == "easyeda-extension" and "site-packages" not in done.stdout:
                print("the installed command found a source checkout, not "
                      "the wheel's own copy")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "dist"))

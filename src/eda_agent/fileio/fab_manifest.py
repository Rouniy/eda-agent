# SPDX-License-Identifier: Apache-2.0
"""Bind an OutJob package to the saved board and exact exported files."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

MANIFEST_NAME = "eda-fab-manifest.json"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_files(directory: Path) -> dict[str, str]:
    return {path.relative_to(directory).as_posix(): sha256_file(path)
            for path in sorted(directory.rglob("*"))
            if path.is_file() and path.name != MANIFEST_NAME}


def seal_package(directory: str | Path, board_path: str | Path,
                 outjob_path: str | Path, board_hash_before: str,
                 outjob_hash_before: str) -> dict:
    """Write a sidecar only if source files stayed byte-identical during export."""
    directory, board_path, outjob_path = map(Path, (directory, board_path, outjob_path))
    if not directory.is_dir():
        raise ValueError("export output directory does not exist")
    if sha256_file(board_path) != board_hash_before:
        raise ValueError("saved board changed during export")
    if sha256_file(outjob_path) != outjob_hash_before:
        raise ValueError("OutJob changed during export")
    files = _package_files(directory)
    if not files:
        raise ValueError("export produced no package files")
    record = {
        "schema": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "board_name": board_path.name,
        "board_sha256": board_hash_before,
        "outjob_name": outjob_path.name,
        "outjob_sha256": outjob_hash_before,
        "files_sha256": files,
    }
    target = directory / MANIFEST_NAME
    temporary = directory / (MANIFEST_NAME + ".tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    temporary.replace(target)
    return {"sealed": True, "path": str(target), "file_count": len(files),
            "board_sha256": board_hash_before, "outjob_sha256": outjob_hash_before}


def verify_package(directory: str | Path, board_path: str | Path,
                   *, required: bool = False) -> dict:
    """Verify a sidecar and every file; absence remains explicit."""
    directory, board_path = Path(directory), Path(board_path)
    target = directory / MANIFEST_NAME
    if not target.is_file():
        return {"verified": False, "reason": "no fab manifest",
                "required": required}
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
        if record.get("schema") != 1 or not isinstance(record.get("files_sha256"), dict):
            raise ValueError("unsupported manifest schema")
        if record.get("board_name") != board_path.name:
            raise ValueError("board filename differs from export record")
        if sha256_file(board_path) != record.get("board_sha256"):
            raise ValueError("saved board hash differs from export record")
        files = _package_files(directory)
        if files != record["files_sha256"]:
            missing = sorted(set(record["files_sha256"]) - set(files))
            added = sorted(set(files) - set(record["files_sha256"]))
            changed = sorted(key for key in files.keys() & record["files_sha256"].keys()
                             if files[key] != record["files_sha256"][key])
            raise ValueError(f"package files differ: missing={missing}, added={added}, changed={changed}")
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        return {"verified": False, "reason": str(exc), "path": str(target)}
    return {"verified": True, "path": str(target),
            "file_count": len(files), "board_sha256": record["board_sha256"],
            "outjob_sha256": record["outjob_sha256"],
            "created_utc": record["created_utc"]}

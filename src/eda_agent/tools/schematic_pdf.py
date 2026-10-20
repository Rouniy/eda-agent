"""Stage a read-only schematic project for silent Altium PDF publishing."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import os
import shutil
import uuid


DEFAULT_EXPORT_ROOT = Path(r"D:\AI\ALTIUM\testprojects\_screens")
TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "schematic-pdf.OutJob"
COLOR_PAGE_OPTION = "|PrintKind=0|"


def export_root() -> Path:
    return Path(os.environ.get("EDA_AGENT_SCHEMATIC_PDF_ROOT", DEFAULT_EXPORT_ROOT)).resolve()


def checked_output_path(output_path: str) -> Path:
    root = export_root()
    target = Path(output_path).resolve()
    if target.suffix.lower() != ".pdf" or target == root or not target.is_relative_to(root):
        raise ValueError(f"output_path must be a PDF under {root}")
    if "\n" in output_path or "\r" in output_path:
        raise ValueError("output_path contains a line break")
    return target


def _read_project(path: Path) -> ConfigParser:
    raw = path.read_bytes()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("cp1252")
    project = ConfigParser(interpolation=None, strict=False)
    project.optionxform = str
    project.read_string(content)
    return project


def stage_schematic_project(project_path: str, output_path: str) -> tuple[Path, Path, Path, int]:
    """Copy only project schematics into a disposable project below _screens."""
    source = Path(project_path).resolve(strict=True)
    if source.suffix.lower() not in (".prjpcb", ".prjpcbd"):
        raise ValueError("project_path must name a .PrjPcb project")
    target = checked_output_path(output_path)
    root = export_root()
    root.mkdir(parents=True, exist_ok=True)
    project = _read_project(source)
    sheet_records: list[dict[str, str]] = []
    for section in list(project.sections()):
        if section.startswith("Document") and section[8:].isdigit():
            record = dict(project[section])
            project.remove_section(section)
            if record.get("DocumentPath", "").lower().endswith(".schdoc"):
                sheet_records.append(record)
    if not sheet_records:
        raise ValueError("project has no SchDoc members")

    validated_sheets: list[tuple[dict[str, str], Path, Path]] = []
    for record in sheet_records:
        relative = Path(record["DocumentPath"])
        original = (source.parent / relative).resolve(strict=True)
        if relative.is_absolute() or not original.is_relative_to(source.parent):
            raise ValueError(f"external SchDoc path is not supported: {relative}")
        validated_sheets.append((record, relative, original))

    job = TEMPLATE.read_text(encoding="utf-8")
    page_options = [line for line in job.splitlines() if line.startswith("PageOptions")]
    if len(page_options) != 1 or COLOR_PAGE_OPTION not in page_options[0]:
        raise ValueError("schematic PDF OutJob must explicitly use Color (PrintKind=0)")

    stage = root / "_pdf_stage" / uuid.uuid4().hex
    stage.mkdir(parents=True)
    first_sheet: Path | None = None
    for index, (record, relative, original) in enumerate(validated_sheets, 1):
        copy = stage / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, copy)
        if first_sheet is None:
            first_sheet = copy
        project[f"Document{index}"] = record
    project[f"Document{len(sheet_records) + 1}"] = {"DocumentPath": "Documentation.OutJob"}
    staged_project = stage / source.name
    with staged_project.open("w", encoding="utf-8", newline="\r\n") as file:
        project.write(file, space_around_delimiters=False)

    temporary_pdf = stage / "output" / target.name
    temporary_pdf.parent.mkdir()
    job = job.replace("__OUTPUT_PATH__", str(temporary_pdf))
    job = job.replace("__OUTPUT_DIR__", str(temporary_pdf.parent))
    job = job.replace("__OUTPUT_NAME__", target.name)
    (stage / "Documentation.OutJob").write_text(job, encoding="utf-8", newline="\r\n")
    assert first_sheet is not None
    return staged_project, first_sheet, temporary_pdf, len(sheet_records)


def remove_stage(staged_project: Path) -> None:
    """Remove only a UUID child of our private staging directory."""
    base = (export_root() / "_pdf_stage").resolve()
    stage = staged_project.parent.resolve()
    if stage.parent != base or len(stage.name) != 32:
        raise ValueError(f"refusing to remove unexpected stage path: {stage}")
    shutil.rmtree(stage)

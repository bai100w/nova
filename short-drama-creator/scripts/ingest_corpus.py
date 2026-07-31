#!/usr/bin/env python3
"""Build a normalized, searchable local corpus from PDF and DOCX scripts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_FORMATS = {".docx", ".pdf"}
EPISODE_HEADING = re.compile(r"^\s*第\s*[0-9一二三四五六七八九十百千零〇两]+\s*集(?:\s|$)")


def _configure_utf8_stdio() -> None:
    """Keep CLI output decodable as UTF-8 regardless of the Windows code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict", newline="\n")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")


def _extract_docx(path: Path) -> str:
    from docx import Document

    document = Document(path)
    blocks: list[str] = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            blocks.append("\t".join(cell.text for cell in row.cells))
    return _normalize_text("\n".join(blocks))


def _extract_pdf(path: Path) -> str:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(path) as document:
        for page in document.pages:
            pages.append(page.extract_text() or "")
    return _normalize_text("\n".join(pages))


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    raise ValueError(f"Unsupported source format: {path.suffix}")


def _source_id(source_file: str, digest: str) -> str:
    identity = f"{source_file}\0{digest}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()[:16]


def _episode_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if EPISODE_HEADING.match(line))


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _load_existing_catalog(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"Catalog must contain a JSON array: {path}")
    return value


def ingest_corpus(source_dir: str | Path, output_dir: str | Path) -> list[dict[str, Any]]:
    """Import supported scripts and return the complete catalog."""
    source_root = Path(source_dir)
    output_root = Path(output_dir)
    if not source_root.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")

    catalog_path = output_root / "catalog.json"
    existing = _load_existing_catalog(catalog_path)
    existing_by_file = {
        str(record.get("source_file")): record
        for record in existing
        if record.get("source_file")
    }
    imported_at = _utc_timestamp()
    records_by_file = dict(existing_by_file)

    sources = sorted(
        (
            path
            for path in source_root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_FORMATS
        ),
        key=lambda path: path.relative_to(source_root).as_posix().casefold(),
    )
    for source_path in sources:
        source_file = source_path.relative_to(source_root).as_posix()
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        identifier = _source_id(source_file, digest)
        previous = existing_by_file.get(source_file)

        if previous and previous.get("sha256") == digest:
            record = dict(previous)
            text_path = output_root / str(record["text_path"])
            if not text_path.exists():
                _atomic_write_text(text_path, extract_text(source_path))
            records_by_file[source_file] = record
            continue

        text = extract_text(source_path)
        relative_text_path = Path("corpus") / f"{identifier}.txt"
        _atomic_write_text(output_root / relative_text_path, text)
        record = {
            "source_id": identifier,
            "title": source_path.stem,
            "source_file": source_file,
            "source_format": source_path.suffix.lower().lstrip("."),
            "sha256": digest,
            "characters": len(text),
            "lines": len(text.splitlines()),
            "episode_count": _episode_count(text),
            "text_path": relative_text_path.as_posix(),
            "imported_at": imported_at,
        }
        records_by_file[source_file] = record

        if previous and previous.get("text_path") != record["text_path"]:
            old_text_path = output_root / str(previous.get("text_path", ""))
            if old_text_path.is_file() and old_text_path.parent == output_root / "corpus":
                old_text_path.unlink()

    catalog = sorted(
        records_by_file.values(),
        key=lambda record: str(record["source_file"]).casefold(),
    )
    catalog_json = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    _atomic_write_text(catalog_path, catalog_json)
    return catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, help="Directory containing PDF/DOCX files")
    parser.add_argument("--output-dir", required=True, help="Library output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        catalog = ingest_corpus(args.source_dir, args.output_dir)
    except (FileNotFoundError, ValueError, OSError) as error:
        parser.error(str(error))
    print(f"已导入 {len(catalog)} 个剧本来源。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

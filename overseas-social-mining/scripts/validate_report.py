#!/usr/bin/env python3
"""Validate an overseas-social-mining HTML report using only the standard library."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_SECTIONS = (
    "summary",
    "entity",
    "routing",
    "evidence",
    "trends",
    "ugc",
    "nodes",
    "language",
    "voc",
    "scripts",
    "entity-deep-dive",
    "opportunities",
    "roadmap",
    "sources",
)

REQUIRED_FIELDS = (
    "original-tag",
    "entity-type",
    "market",
    "language",
    "window",
    "primary-platforms",
    "collected-platform-count",
    "sample-count",
    "confidence",
    "generation-date",
    "refresh-date",
)

UNRESOLVED_MARKERS = (
    "待填入",
    "待定",
    "待评",
    "尚未路由",
    "尚未评估",
    "条件模块尚未选择",
    "https://example.com",
    "报告模板",
)


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.id_counts: dict[str, int] = {}
        self.nav_links: set[str] = set()
        self.internal_links: set[str] = set()
        self.fields: set[str] = set()
        self.external_link_errors: list[str] = []
        self._nav_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "nav":
            self._nav_depth += 1
        if values.get("id"):
            element_id = values["id"] or ""
            self.id_counts[element_id] = self.id_counts.get(element_id, 0) + 1
        if values.get("data-field"):
            self.fields.add(values["data-field"] or "")
        if tag == "a" and values.get("href"):
            href = values["href"] or ""
            if href.startswith("#"):
                self.internal_links.add(href)
            if self._nav_depth and href.startswith("#"):
                self.nav_links.add(href)
            if urlparse(href).scheme in {"http", "https"}:
                rel = set((values.get("rel") or "").split())
                if values.get("target") != "_blank" or not {"noopener", "noreferrer"}.issubset(rel):
                    self.external_link_errors.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav" and self._nav_depth:
            self._nav_depth -= 1


def validate(path: Path, allow_template_markers: bool = False) -> list[str]:
    errors: list[str] = []
    if path.suffix.lower() != ".html":
        errors.append("report must use the .html extension")
    if not path.is_file():
        return [f"report not found: {path}"]

    text = path.read_text(encoding="utf-8")
    parser = ReportParser()
    parser.feed(text)

    for section_id in REQUIRED_SECTIONS:
        if section_id not in parser.id_counts:
            errors.append(f"missing section id: {section_id}")
        if f"#{section_id}" not in parser.nav_links:
            errors.append(f"missing navigation link: #{section_id}")
    for field in REQUIRED_FIELDS:
        if field not in parser.fields:
            errors.append(f"missing metadata field: {field}")
    for href in parser.external_link_errors:
        errors.append(f"external link lacks target/rel safety: {href}")
    for element_id, count in sorted(parser.id_counts.items()):
        if count > 1:
            errors.append(f"duplicate id: {element_id}")
    for href in sorted(parser.internal_links):
        if href[1:] not in parser.id_counts:
            errors.append(f"broken internal link: {href}")

    if not allow_template_markers:
        for marker in UNRESOLVED_MARKERS:
            if marker in text:
                errors.append(f"unresolved template marker: {marker}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--template",
        action="store_true",
        help="Allow template empty-state markers while still checking structure.",
    )
    args = parser.parse_args()

    errors = validate(args.report, allow_template_markers=args.template)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: report structure is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

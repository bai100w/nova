#!/usr/bin/env python3
"""Validate the minimum structure and episode hooks of a short-drama script."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EPISODE_HEADING = re.compile(r"^\s*第\s*[0-9一二三四五六七八九十百千零〇两]+\s*集(?:\s|$)")
SCENE_HEADING = re.compile(
    r"^\s*(?:场次\s*[:：]?\s*)?"
    r"(?:\d+\s*[-－—.．]\s*)?\d+"
    r"(?:\s*[-－—.．]\s*\d+)?"
    r"(?:\s+|[、:：])"
    r".*(?:日|夜|晨|昏|早|晚)"
    r".*(?:内|外)"
    r".+\S\s*$"
)
CHARACTER_COLUMN = re.compile(r"^\s*(?:人物|角色)\s*[:：]\s*\S+")
STRONG_END_PUNCTUATION = re.compile(r"[!?？！…]\s*[”’」』）)]?\s*$")
HOOK_WORDS = re.compile(
    r"突然|猛然|却|竟然|竟是|原来|发现|冲入|闯入|枪响|爆炸|"
    r"血|死亡|杀|秘密|真相|身份|证据|曝光|失踪|倒下|昏迷|"
    r"门外|身后|危险|等等|住手|不可能"
)
SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown"}


def _configure_utf8_stdio() -> None:
    """Keep CLI output decodable as UTF-8 regardless of the Windows code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict", newline="\n")


def _issue(
    code: str, severity: str, message: str, line: int | None = None
) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    if line is not None:
        issue["line"] = line
    return issue


def _episode_ranges(lines: list[str]) -> list[tuple[int, int, int]]:
    starts = [index for index, line in enumerate(lines) if EPISODE_HEADING.match(line)]
    return [
        (start, starts[position + 1] if position + 1 < len(starts) else len(lines), position + 1)
        for position, start in enumerate(starts)
    ]


def _is_strong_ending(line: str) -> bool:
    return bool(STRONG_END_PUNCTUATION.search(line) or HOOK_WORDS.search(line))


def validate_text(text: str) -> list[dict[str, Any]]:
    """Return ordered validation issues for UTF-8 script text."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    ranges = _episode_ranges(lines)
    if not ranges:
        return [_issue("E001", "error", "缺少“第X集”剧集标题。", 1)]

    issues: list[dict[str, Any]] = []
    for start, end, ordinal in ranges:
        body = lines[start + 1 : end]
        if not any(SCENE_HEADING.match(line) for line in body):
            issues.append(
                _issue(
                    "E002",
                    "error",
                    f"第{ordinal}个剧集缺少场景标题（如“1-1 日 内 客厅”）。",
                    start + 1,
                )
            )
        if not any(CHARACTER_COLUMN.match(line) for line in body):
            issues.append(
                _issue(
                    "E003",
                    "error",
                    f"第{ordinal}个剧集缺少“人物：”栏。",
                    start + 1,
                )
            )

        meaningful = [
            (index, lines[index].strip())
            for index in range(start + 1, end)
            if lines[index].strip()
        ]
        if meaningful:
            ending_index, ending = meaningful[-1]
            if not _is_strong_ending(ending):
                issues.append(
                    _issue(
                        "W001",
                        "warning",
                        f"第{ordinal}个剧集结尾较弱，建议加入未完成行动、危险、揭示或选择钩子。",
                        ending_index + 1,
                    )
                )
        else:
            issues.append(
                _issue(
                    "W001",
                    "warning",
                    f"第{ordinal}个剧集没有可识别的集尾钩子。",
                    start + 1,
                )
            )
    return issues


def result_for(path: Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    error_count = sum(issue["severity"] == "error" for issue in issues)
    warning_count = sum(issue["severity"] == "warning" for issue in issues)
    status = "error" if error_count else "warning" if warning_count else "pass"
    return {
        "file": str(path),
        "status": status,
        "errors": error_count,
        "warnings": warning_count,
        "issues": issues,
    }


def _render_human(result: dict[str, Any]) -> str:
    heading = {
        "pass": "PASS",
        "warning": "WARNING",
        "error": "ERROR",
    }[result["status"]]
    lines = [
        f"{heading}: {result['file']}",
        f"errors={result['errors']} warnings={result['warnings']}",
    ]
    for issue in result["issues"]:
        location = f"line {issue['line']}: " if "line" in issue else ""
        lines.append(
            f"[{issue['severity'].upper()} {issue['code']}] {location}{issue['message']}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", help="UTF-8 .txt, .md, or .markdown script")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    path = Path(args.script)
    if not path.is_file():
        parser.error(f"Script file does not exist: {path}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        parser.error("Script must be a .txt, .md, or .markdown file")

    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        parser.error(str(error))

    result = result_for(path, validate_text(text))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_render_human(result))
    if result["errors"]:
        return 2
    if result["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

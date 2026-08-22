#!/usr/bin/env python3
"""Validate local Markdown links without third-party dependencies."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def local_target(markdown_file: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or target.startswith("#"):
        return None

    relative_path = unquote(parsed.path)
    if not relative_path:
        return None
    return (markdown_file.parent / relative_path).resolve()


def main() -> int:
    failures: list[str] = []
    markdown_files = sorted(ROOT.rglob("*.md"))

    for markdown_file in markdown_files:
        content = markdown_file.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(content):
            target = local_target(markdown_file, match.group(1))
            if target is not None and not target.exists():
                failures.append(
                    f"{markdown_file.relative_to(ROOT)}: missing {target.relative_to(ROOT)}"
                )

    if failures:
        print("Documentation validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1

    print(f"Validated {len(markdown_files)} Markdown files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
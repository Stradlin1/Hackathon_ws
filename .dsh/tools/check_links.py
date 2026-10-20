#!/usr/bin/env python3
"""Verify every relative Markdown link and heading anchor in the knowledge base.

Run from anywhere: python .dsh/tools/check_links.py
Exit code 0 = all targets exist, 1 = at least one broken link/anchor.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
FENCE = re.compile(r"^```")


def slug(heading: str) -> str:
    """GitHub-style slug: lowercase, drop punctuation, each space becomes a hyphen."""
    text = heading.strip().lower()
    kept = []
    for char in text:
        if char.isalnum() or char in "-_" or char.isspace():
            kept.append(char)
    # Do NOT collapse whitespace runs: each space is its own hyphen ("A + B" -> "a--b").
    return "".join(kept).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", line)
        if match:
            found.add(slug(match.group(2)))
    return found


def main() -> int:
    markdown = sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.parts and ".venv" not in path.parts and "node_modules" not in path.parts
    )
    broken: list[str] = []
    checked = 0
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        in_fence = False
        for number, line in enumerate(text.splitlines(), 1):
            if FENCE.match(line.strip()):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for target in LINK.findall(line):
                if "://" in target or target.startswith("mailto:"):
                    continue
                relative, _, fragment = target.partition("#")
                checked += 1
                destination = (path.parent / relative).resolve() if relative else path
                if not destination.exists():
                    broken.append(f"{path.relative_to(ROOT)}:{number}: missing file {target}")
                    continue
                if fragment and destination.suffix == ".md":
                    if unicodedata.normalize("NFC", fragment) not in anchors(destination):
                        broken.append(f"{path.relative_to(ROOT)}:{number}: missing anchor {target}")
    for item in broken:
        print(item)
    print(f"{len(markdown)} Markdown files, {checked} relative links, {len(broken)} broken.")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())

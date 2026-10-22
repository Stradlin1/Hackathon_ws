#!/usr/bin/env python3
"""Build the self-hosted Chinese serif subset used by the interface.

pioneer-wiki's look depends on a serif face; this machine only ships a sans CJK
font. Download Noto Serif SC (OFL) once, keep only the characters this project
actually prints, and write two copies:

    static/fonts/noto-serif-sc-subset.woff2        (Streamlit, served at /app/static/)
    showcase/assets/fonts/noto-serif-sc-subset.woff2 (stage page, relative URL)

Only the generation step needs fontTools and brotli:

    python -m venv /tmp/fontenv
    /tmp/fontenv/bin/pip install fonttools brotli
    /tmp/fontenv/bin/python tools/build_font.py

Runtime never imports fontTools.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".cache"
SOURCE_URL = "https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-sc/files/noto-serif-sc-chinese-simplified-400-normal.woff2"
LICENSE_URL = "https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-sc/LICENSE"
TARGETS = (
    ROOT / "static" / "fonts" / "noto-serif-sc-subset.woff2",
    ROOT / "showcase" / "assets" / "fonts" / "noto-serif-sc-subset.woff2",
)
SCAN = (
    "app.py",
    "ui/*.py",
    "state/*.py",
    "matching/*.py",
    "showcase/index.html",
    "showcase/SCRIPT.md",
)
EXTRA = (
    "".join(chr(code) for code in range(32, 127))
    + "　、。〃々〈〉《》「」『』【】〔〕〖〗〝〞–—‘’“”…‰′″※·×÷≥≤％＋－"
)


def fetch(url: str, target: Path) -> Path:
    if target.exists() and target.stat().st_size > 0:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print("downloading " + url)
    with urllib.request.urlopen(url, timeout=120) as response:
        target.write_bytes(response.read())
    return target


def characters() -> str:
    seen = set(EXTRA)
    for pattern in SCAN:
        for path in ROOT.glob(pattern):
            text = path.read_text(encoding="utf-8", errors="ignore")
            seen.update(text)
    seen = {char for char in seen if char.isprintable() or char in "\u3000\n\t"}
    seen.discard("\n")
    seen.discard("\t")
    return "".join(sorted(seen))


def main() -> int:
    try:
        from fontTools import subset
    except ImportError:
        print("fontTools is missing. Run: python -m venv /tmp/fontenv && /tmp/fontenv/bin/pip install fonttools brotli", file=sys.stderr)
        return 1
    try:
        import brotli  # noqa: F401  (woff2 writer needs it)
    except ImportError:
        print("brotli is missing. Run: /tmp/fontenv/bin/pip install brotli", file=sys.stderr)
        return 1

    source = fetch(SOURCE_URL, CACHE / "noto-serif-sc-400.woff2")
    text = characters()
    print("keeping %d distinct characters" % len(text))
    for target in TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)

    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = []
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.notdef_outline = True
    options.recalc_bounds = True

    for target in TARGETS:
        font = subset.load_font(str(source), options)
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text=text)
        subsetter.subset(font)
        subset.save_font(font, str(target), options)
        print("%s: %d KB" % (target.relative_to(ROOT), target.stat().st_size // 1024))

    write_license(TARGETS[0].parent)

    if any(target.stat().st_size > 250 * 1024 for target in TARGETS):
        print("warning: subset is over the 250 KB budget; trim the scanned files", file=sys.stderr)
    return 0


def write_license(directory: Path) -> None:
    license_file = fetch(LICENSE_URL, CACHE / "noto-serif-sc-LICENSE.txt")
    text = license_file.read_text(encoding="utf-8", errors="ignore")
    (directory / "OFL.txt").write_text(text, encoding="utf-8")
    (ROOT / "showcase" / "assets" / "fonts" / "OFL.txt").write_text(text, encoding="utf-8")
    print("wrote OFL.txt next to the subset")


if __name__ == "__main__":
    raise SystemExit(main())

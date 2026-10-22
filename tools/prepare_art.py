#!/usr/bin/env python3
"""Turn the generated plates into transparent cut-outs that print on the page.

Mirrors tools/prepare-plates.mjs from pioneer-wiki, without Node or numpy:

1. estimate the paper ground from the border pixels (60th percentile per channel);
2. divide every pixel by 94% of that ground so the ground clips to white;
3. colour-to-alpha against white, giving the least opaque ink that reproduces the
   pixel when laid over paper;
4. fade the outermost 3% of the sheet so no rectangle can ever show;
5. write static/art/<slug>.webp (longest edge <= 1400, quality 82) and a
   128 px mark-icon.png for the page icon.

Run "python tools/prepare_art.py" after "tools/generate_art.py".
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "static" / "art" / "src"
OUT = ROOT / "static" / "art"
MANIFEST = OUT / "manifest.json"
FEATHER = 0.03
# Display sizes: a big plate for the auth page, a compact mark, medium vignettes.
MAX_EDGE = {
    "frontispiece": 1200,
    "mark": 640,
    "fleuron": 900,
}
DEFAULT_MAX_EDGE = 900


def ground_colour(image: Image.Image) -> tuple[int, int, int]:
    """Median-ish paper colour sampled from a 2% border band."""
    width, height = image.size
    band = max(4, round(min(width, height) * 0.02))
    pixels = image.load()
    samples: tuple[list[int], list[int], list[int]] = ([], [], [])
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if band < x < width - band and band < y < height - band:
                continue
            red, green, blue = pixels[x, y][:3]
            samples[0].append(red)
            samples[1].append(green)
            samples[2].append(blue)
    ground = []
    for channel in samples:
        channel.sort()
        ground.append(channel[int(len(channel) * 0.6)] if channel else 255)
    return tuple(ground)  # type: ignore[return-value]


def cut_out(source: Image.Image, ground: tuple[int, int, int]) -> Image.Image:
    """Colour-to-alpha, then a soft edge so the plate has no visible rectangle."""
    width, height = source.size
    pixels = source.load()
    result = Image.new("RGBA", (width, height))
    target = result.load()
    scale = [max(1, ground[0] * 0.94), max(1, ground[1] * 0.94), max(1, ground[2] * 0.94)]
    feather = max(1, round(min(width, height) * FEATHER))
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y][:3]
            p0 = min(1.0, red / scale[0])
            p1 = min(1.0, green / scale[1])
            p2 = min(1.0, blue / scale[2])
            alpha = 1.0 - min(p0, p1, p2)
            if alpha <= 0.0:
                target[x, y] = (0, 0, 0, 0)
                continue
            edge = min(x, width - 1 - x, y, height - 1 - y)
            if edge < feather:
                alpha *= edge / feather
            if alpha <= 0.0:
                target[x, y] = (0, 0, 0, 0)
                continue
            inverse = 1.0 - alpha
            colour = [
                round(255 * max(0.0, min(1.0, (value - inverse) / alpha)))
                for value in (p0, p1, p2)
            ]
            target[x, y] = (colour[0], colour[1], colour[2], round(alpha * 255))
    return result


def main() -> int:
    if not SRC.exists():
        print("No raw plates: run tools/generate_art.py first.")
        return 1
    slugs = sorted(path.stem for path in SRC.glob("*.png"))
    if not slugs:
        print("static/art/src is empty: run tools/generate_art.py first.")
        return 1

    sizes = {}
    for slug in slugs:
        source = Image.open(SRC / (slug + ".png")).convert("RGB")
        ground = ground_colour(source)
        plate = cut_out(source, ground)
        if slug == "fleuron":
            # The ornament sits in a very wide empty sheet; trim it for a divider rule.
            bounds = plate.getbbox()
            if bounds:
                padding = max(2, round((bounds[2] - bounds[0]) * 0.04))
                plate = ImageOps.expand(plate.crop(bounds), border=padding, fill=(0, 0, 0, 0))
        limit = MAX_EDGE.get(slug, DEFAULT_MAX_EDGE)
        plate.thumbnail((limit, limit), Image.LANCZOS)
        target = OUT / (slug + ".webp")
        plate.save(target, "WEBP", quality=80, method=6)
        sizes[slug] = {
            "width": plate.width,
            "height": plate.height,
            "ground": "rgb(%d %d %d)" % ground,
            "bytes": target.stat().st_size,
        }
        print("%s: %dx%d ground %s -> %d KB" % (slug, plate.width, plate.height, ground, target.stat().st_size // 1024))

    mark = Image.open(OUT / "mark.webp").convert("RGBA")
    icon = ImageOps.contain(mark, (128, 128), Image.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    canvas.paste(icon, ((128 - icon.width) // 2, (128 - icon.height) // 2), icon)
    canvas.save(OUT / "mark-icon.png")
    print("mark-icon.png: 128x128")

    (OUT / "sizes.json").write_text(json.dumps(sizes, indent=2) + "\n", encoding="utf-8")
    write_attribution(sizes)
    print("wrote static/art/sizes.json and ATTRIBUTION.md")
    return 0


def write_attribution(sizes: dict) -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    models = sorted({entry.get("model", "") for entry in entries if entry.get("model")})
    lines = [
        "# 生成插图（static/art/）",
        "",
        "本目录的插图由生图模型生成，供 Picture is All You Need 的界面与上台展示页使用。",
        "做法与 pioneer-wiki 的插图流程一致。",
        "",
        "- 许可：CC BY 4.0（与 pioneer-wiki 的插图相同）",
        "- 模型：" + (", ".join(models) or "见 manifest.json"),
        "- 提示词、生成时间与 license 逐条记录在 manifest.json；这里是裁切后的 webp（纸底已转透明），原始 PNG 不入库。",
        "- 重新生成：python tools/generate_art.py --env-file <含 PW_IMAGE_API_KEY 的文件>，再运行 python tools/prepare_art.py。",
        "",
        "| 文件 | 尺寸 | 字节 |",
        "| --- | --- | --- |",
    ]
    for slug, info in sorted(sizes.items()):
        lines.append("| %s.webp | %dx%d | %d |" % (slug, info["width"], info["height"], info["bytes"]))
    (OUT / "ATTRIBUTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

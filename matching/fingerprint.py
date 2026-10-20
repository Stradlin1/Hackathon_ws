"""Evidence-checked generative fingerprints for lost and found items.

The language model can propose structured attributes, but only attributes backed by
literal source evidence are accepted. When weights are unavailable the app keeps
working with conservative rule-based extraction.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Callable

FIELDS = ("category", "color", "material", "shape", "brand", "mark")

VOCAB = {
    "category": {
        "earbuds": ("earbuds", "earphones", "airpods", "入耳式耳机", "蓝牙耳机", "无线耳机", "耳机"),
        "headphones": ("headphones", "headset", "头戴式耳机"),
        "umbrella": ("umbrella", "雨伞", "伞"),
        "water bottle": ("water bottle", "bottle", "保温杯", "水瓶", "水壶"),
        "cup": ("mug", "coffee cup", "cup", "马克杯", "杯子", "水杯"),
        "keys": ("keyring", "keychain", "keys", "钥匙串", "钥匙"),
        "wallet": ("wallet", "钱包", "卡包"),
        "backpack": ("backpack", "rucksack", "双肩包", "背包", "书包"),
        "bag": ("handbag", "tote bag", "bag", "手提包", "包包"),
        "phone": ("smartphone", "mobile phone", "phone", "手机"),
        "laptop": ("laptop", "notebook computer", "笔记本电脑", "电脑"),
        "book": ("textbook", "book", "课本", "书籍", "书"),
        "glasses": ("glasses", "spectacles", "eyeglasses", "眼镜"),
        "watch": ("watch", "手表"),
        "notebook": ("notebook", "记事本", "笔记本"),
    },
    "color": {
        "black": ("black", "黑色", "黑"),
        "white": ("white", "白色", "白"),
        "red": ("red", "红色", "红"),
        "blue": ("blue", "蓝色", "蓝"),
        "green": ("green", "绿色", "绿"),
        "yellow": ("yellow", "黄色", "黄"),
        "purple": ("purple", "紫色", "紫"),
        "pink": ("pink", "粉色", "粉"),
        "orange": ("orange", "橙色", "橘色", "橙"),
        "gray": ("grey", "gray", "灰色", "灰"),
        "brown": ("brown", "棕色", "褐色", "棕"),
        "gold": ("golden", "gold", "金色"),
        "silver": ("silver", "银色"),
    },
    "material": {
        "plastic": ("plastic", "塑料"),
        "metal": ("metal", "metallic", "金属", "不锈钢"),
        "glass": ("glass", "玻璃"),
        "leather": ("leather", "皮革", "真皮"),
        "fabric": ("fabric", "cloth", "布料", "织物"),
        "ceramic": ("ceramic", "porcelain", "陶瓷"),
        "wood": ("wooden", "wood", "木质", "木头"),
        "rubber": ("rubber", "橡胶"),
    },
    "shape": {
        "oval": ("oval", "elliptical", "椭圆"),
        "rectangular": ("rectangular", "rectangle", "长方形", "矩形"),
        "square": ("square", "正方形"),
        "round": ("round", "circular", "圆形", "圆的"),
        "cylindrical": ("cylindrical", "cylinder", "圆柱"),
        "foldable": ("foldable", "folding", "折叠"),
        "curved handle": ("curved handle", "hook handle", "弯钩手柄", "弯柄", "弯钩"),
        "straight handle": ("straight handle", "直柄", "直手柄"),
    },
    "brand": {
        "apple": ("apple", "苹果牌"),
        "sony": ("sony", "索尼"),
        "jbl": ("jbl",),
        "bose": ("bose",),
        "samsung": ("samsung", "三星"),
        "xiaomi": ("xiaomi", "小米"),
        "huawei": ("huawei", "华为"),
        "nike": ("nike", "耐克"),
        "adidas": ("adidas", "阿迪达斯"),
        "logitech": ("logitech", "罗技"),
    },
    "mark": {
        "scratch": ("scratched", "scratch", "划痕", "刮痕", "划伤"),
        "sticker": ("sticker", "贴纸", "贴画"),
        "crack": ("cracked", "crack", "裂纹", "裂痕"),
        "dent": ("dented", "dent", "凹痕"),
        "strap": ("lanyard", "strap", "挂绳", "挂带"),
        "logo": ("logo", "标志", "图案"),
        "engraving": ("engraving", "engraved", "刻字", "名字刻印"),
        "keychain": ("keychain", "钥匙扣"),
    },
}

VALUE_ZH = {
    "category": {
        "earbuds": "入耳式耳机", "headphones": "头戴式耳机", "umbrella": "雨伞",
        "water bottle": "水瓶", "cup": "杯子", "keys": "钥匙", "wallet": "钱包",
        "backpack": "双肩包", "bag": "包", "phone": "手机", "laptop": "笔记本电脑",
        "book": "书", "glasses": "眼镜", "watch": "手表", "notebook": "笔记本",
    },
    "color": {
        "black": "黑色", "white": "白色", "red": "红色", "blue": "蓝色",
        "green": "绿色", "yellow": "黄色", "purple": "紫色", "pink": "粉色",
        "orange": "橙色", "gray": "灰色", "brown": "棕色", "gold": "金色",
        "silver": "银色",
    },
    "material": {
        "plastic": "塑料", "metal": "金属", "glass": "玻璃", "leather": "皮革",
        "fabric": "布料", "ceramic": "陶瓷", "wood": "木质", "rubber": "橡胶",
    },
    "shape": {
        "oval": "椭圆形", "rectangular": "长方形", "square": "正方形",
        "round": "圆形", "cylindrical": "圆柱形", "foldable": "可折叠",
        "curved handle": "弯钩手柄", "straight handle": "直手柄",
    },
    "brand": {
        "apple": "苹果", "sony": "索尼", "jbl": "JBL", "bose": "Bose",
        "samsung": "三星", "xiaomi": "小米", "huawei": "华为",
        "nike": "耐克", "adidas": "阿迪达斯", "logitech": "罗技",
    },
    "mark": {
        "scratch": "划痕", "sticker": "贴纸", "crack": "裂纹", "dent": "凹痕",
        "strap": "挂绳", "logo": "标志", "engraving": "刻字", "keychain": "钥匙扣",
        "no special mark": "无特殊标记",
    },
}


def display_value(field: str, value: str) -> str:
    """Translate a canonical attribute value for display; storage keeps the English value."""
    if not isinstance(value, str) or not value:
        return value
    direct = VALUE_ZH.get(field, {}).get(value)
    if direct:
        return direct
    if field == "mark":
        color, _, mark = value.partition(" ")
        if color in VALUE_ZH["color"] and mark in VALUE_ZH["mark"]:
            return VALUE_ZH["color"][color] + VALUE_ZH["mark"][mark]
    return value


UNKNOWN = {"", "unknown", "none", "null", "n/a", "not specified", "未知", "不详", "不记得", "不知道"}
SKIP_ANSWERS = {"", "不记得", "不知道", "不清楚", "记不清", "无法确定", "跳过", "unknown", "skip", "not sure", "no idea"}


def _has(text: str, token: str) -> bool:
    token = token.lower()
    if token.isascii() and re.search(r"[a-z]", token):
        return re.search(r"(?<![a-z])" + re.escape(token) + r"(?![a-z])", text) is not None
    return token in text


def extract_known(text: str) -> dict[str, str]:
    """Normalize observable attributes without inventing missing facts."""
    s = (text or "").lower()
    found: dict[str, str] = {}
    for field, entries in VOCAB.items():
        matches = [
            (len(alias), canonical, alias)
            for canonical, aliases in entries.items()
            for alias in aliases if _has(s, alias)
        ]
        if not matches:
            continue
        _, value, _ = max(matches, key=lambda m: m[0])
        if field == "mark":
            if any(_has(s, neg) for neg in ("没有特殊标记", "无特殊标记", "no special marks")):
                found[field] = "no special mark"
                continue
            # Only associate a color with the mark if it immediately precedes
            # the mark; the item's overall color is not necessarily its color.
            mark_alias = next(m[2] for m in matches if m[1] == value)
            mark_pos = s.find(mark_alias)
            prefix = s[max(0, mark_pos - 15):mark_pos]
            nearby_colors = []
            for color, aliases in VOCAB["color"].items():
                for alias in aliases:
                    pos = prefix.rfind(alias)
                    if pos >= 0 and _has(prefix, alias):
                        distance = len(prefix) - (pos + len(alias))
                        if 0 <= distance <= 3:
                            nearby_colors.append((distance, color))
            if nearby_colors:
                value = min(nearby_colors)[1] + " " + value
        found[field] = value
    return found


def extract_colors(text: str) -> list[str]:
    s = (text or "").lower()
    return [canonical for canonical, variants in VOCAB["color"].items() if any(_has(s, a) for a in variants)]


def normalize_answer(field: str, answer: str) -> str | None:
    if field not in FIELDS:
        raise ValueError("不支持的属性")
    raw = " ".join((answer or "").strip().split())
    if not raw or raw.lower() in SKIP_ANSWERS:
        return None
    if field == "mark":
        lowered = raw.lower()
        if any(k in lowered for k in ("没有特殊标记", "无特殊标记", "无标记", "no mark", "nothing special")):
            return "no special mark"
        if any(k in lowered for k in ("没有划痕", "没有贴纸", "no scratches", "no sticker")):
            return None
    known = extract_known(raw)
    if field in known:
        return known[field]
    if field == "mark":
        return raw.lower()[:80]
    if field == "brand" and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9 ._-]{1,39}", raw):
        return raw.lower()
    # Do not turn an unrecognized color, shape or category into a guessed value.
    return None


def _extract_json_object(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        value = json.loads(text[start:end + 1])
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


@lru_cache(maxsize=1)
def _load_generator():
    name = os.environ.get("FINGERPRINT_TEXT_MODEL", "google/flan-t5-small")
    if name.lower() in ("off", "none", "disabled"):
        return None
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
    except ImportError:
        return None
    device = 0 if torch.cuda.is_available() else -1
    try:
        tokenizer = AutoTokenizer.from_pretrained(name, local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(name, local_files_only=True)
    except (OSError, ValueError, AttributeError):
        tokenizer = AutoTokenizer.from_pretrained(name)
        model = AutoModelForSeq2SeqLM.from_pretrained(name)
    try:
        return pipeline("text2text-generation", model=model, tokenizer=tokenizer, device=device)
    except (OSError, RuntimeError, ValueError):
        return None


def _model_attributes(source: str, generator: Callable | None) -> dict:
    if generator is None:
        return {}
    prompt = (
        "Extract only explicitly stated properties of a lost or found object. "
        "Do not infer missing features. Output JSON with keys category,color,material,shape,brand,mark. "
        "Set missing fields to unknown. Description: " + source[:500]
    )
    try:
        result = generator(prompt, max_new_tokens=112, do_sample=False, truncation=True)
        output = result[0]["generated_text"] if isinstance(result, list) else str(result)
        return _extract_json_object(output)
    except (TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError):
        return {}


def fingerprint_from_text(
    description: str,
    caption: str = "",
    *,
    generator: Callable | None = None,
    generate: bool = True,
) -> dict:
    """Create a fingerprint and validate generative proposals against source text.

    `generator` is dependency-injected for tests. `generate=False` avoids loading
    weights while indexing legacy data or running offline tests.
    """
    description = (description or "").strip()[:1000]
    caption = (caption or "").strip()[:500]
    main = extract_known(description)
    visual = extract_known(caption)
    # Explicit user information has priority over auto-generated captions.
    observed = {**visual, **main}
    source = description + (". " + caption if caption else "")
    proposer = generator if generator is not None else (_load_generator() if generate else None)
    proposals = _model_attributes(source, proposer) if generate else {}
    generated_verified = False
    for field in FIELDS:
        proposal = proposals.get(field)
        if not isinstance(proposal, str) or proposal.strip().lower() in UNKNOWN:
            continue
        # Validate a proposal by applying the same literal-evidence extractor to
        # its own phrase AND checking the value is actually present in the input.
        proposed = extract_known(proposal).get(field)
        if proposed is not None and observed.get(field) == proposed:
            generated_verified = True
        elif field not in observed and len(proposal) <= 50 and _has(source.lower(), proposal.strip().lower()):
            # Generative extraction adds open-vocabulary details (e.g. a brand
            # that is not in VOCAB), but only when its actual words appear in
            # the supplied report or generated image caption.
            observed[field] = proposal.strip().lower()
            generated_verified = True
    method = "generative_verified" if generated_verified else ("vision_caption_rules" if caption else "rules")
    return {"attributes": observed, "method": method, "caption": caption}

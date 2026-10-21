from types import SimpleNamespace

from PIL import Image, ImageChops, ImageDraw

from matching.content_hash import (ImageHashes, find_similar_text, hamming_distance,
                                   image_dhash, publication_text, text_fingerprint,
                                   watermark)


def pattern(left_black=True):
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    if left_black:
        draw.rectangle([(0, 0), (32, 64)], fill="black")
    else:
        draw.rectangle([(32, 0), (64, 64)], fill="black")
    return image


def test_text_fingerprint_is_normalised():
    a = text_fingerprint("黑色耳机，充电盒有红色贴纸")
    b = text_fingerprint("  黑色耳机， 充电盒有红色贴纸 ")
    c = text_fingerprint("透明水杯")
    assert a == b
    assert a != c
    assert len(a) == 10


def test_dhash_is_stable_across_resize_and_differs_between_patterns():
    left = pattern(True)
    right = pattern(False)
    resized = left.resize((32, 32))
    assert hamming_distance(image_dhash(left), image_dhash(resized)) <= 2
    assert hamming_distance(image_dhash(left), image_dhash(right)) > 10


def test_watermark_keeps_size_and_changes_the_bottom():
    image = pattern(True)
    marked = watermark(image, 1234567890123, 1_700_000_000)
    assert marked.size == image.size
    difference = ImageChops.difference(image.convert("RGB"), marked)
    assert difference.getbbox() is not None
    assert difference.getbbox()[1] >= image.height // 2


def test_publication_text_contains_time_and_fingerprint():
    line = publication_text(1, "黑色耳机", 1_700_000_000)
    assert "首次发布于" in line
    assert "内容指纹" in line
    assert text_fingerprint("黑色耳机") in line


def test_find_similar_text_flags_copies_and_ignores_short_text():
    items = [
        SimpleNamespace(id=1, description="黑色耳机，充电盒盖内侧有一张红色贴纸"),
        SimpleNamespace(id=2, description="透明水杯"),
    ]
    exact = find_similar_text(" 黑色耳机， 充电盒盖内侧有一张红色贴纸 ", items)
    assert exact["item_id"] == 1
    assert exact["ratio"] == 1.0

    unrelated = find_similar_text("白色机械键盘，塑料键帽，带白色数据线", items)
    assert unrelated is None
    assert find_similar_text("水杯", items) is None


def test_image_hashes_put_find_and_delete(tmp_path):
    hashes = ImageHashes(tmp_path / "items.db")
    image = pattern(True)
    hashes.put(10, image)
    assert hashes.get(10) == image_dhash(image)
    hits = hashes.find_near(image)
    assert hits[0]["item_id"] == 10
    assert hits[0]["distance"] == 0
    assert hashes.find_near(image, exclude_item_id=10) == []

    hashes.delete(10)
    assert hashes.get(10) is None

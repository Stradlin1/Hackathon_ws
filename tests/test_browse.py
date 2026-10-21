from datetime import datetime

from state.browse import ALL, category_options, filter_records, location_options


class Item:
    def __init__(self, id, description, time=0, location="", image=None):
        self.id = id
        self.description = description
        self.time = time
        self.location = location
        self.image = image


def record(item_id, description, time=0, location="", direction="found", **attributes):
    return {"item": Item(item_id, description, time, location),
            "attributes": attributes, "direction": direction}


def test_filters_combine_keyword_category_and_location():
    now = datetime.now().timestamp()
    records = [
        record(1, "黑色雨伞", now, "图书馆", category="umbrella", color="black"),
        record(2, "白色水杯", now - 10 * 86400, "食堂", category="cup", color="white"),
        record(3, "黑色鼠标", now, "图书馆", category="mouse", color="black"),
    ]
    selected = filter_records(records, keyword="黑色", category="mouse", location="图书馆")
    assert [row["item"].id for row in selected] == [3]

    recent = filter_records(records, cutoff=now - 3 * 86400)
    assert [row["item"].id for row in recent] == [3, 1]


def test_keyword_searches_attribute_display_values():
    now = datetime.now().timestamp()
    records = [
        record(1, "透明的圆柱形容器", now, "图书馆", category="cup", color="green"),
    ]
    assert [row["item"].id for row in filter_records(records, keyword="绿色")] == [1]
    assert [row["item"].id for row in filter_records(records, keyword="杯子")] == [1]
    assert filter_records(records, keyword="鼠标") == []


def test_keyword_is_case_insensitive():
    records = [record(1, "Black UMBRELLA", 1, "图书馆", category="umbrella", color="black")]
    assert [row["item"].id for row in filter_records(records, keyword="black")] == [1]


def test_time_filter_skips_rows_without_a_timestamp():
    records = [record(1, "旧记录", 0, "图书馆", category="cup")]
    assert filter_records(records, cutoff=1) == []
    assert [row["item"].id for row in filter_records(records, cutoff=None)] == [1]


def test_options_include_all_and_are_stable():
    records = [
        record(1, "鼠标", 1, "图书馆", category="mouse"),
        record(2, "水杯", 2, "食堂", category="cup"),
        record(3, "没有指纹", 3, "图书馆"),
    ]
    categories = category_options(records)
    assert categories[0] == ALL
    assert set(categories[1:]) == {"mouse", "cup"}
    assert location_options(records) == [ALL, "图书馆", "食堂"]


def test_filters_by_direction():
    records = [
        record(1, "丢失的雨伞", 1, "图书馆", direction="lost", category="umbrella"),
        record(2, "捡到的雨伞", 2, "图书馆", direction="found", category="umbrella"),
    ]
    assert [row["item"].id for row in filter_records(records, direction="lost")] == [1]
    assert [row["item"].id for row in filter_records(records, direction="found")] == [2]
    assert len(filter_records(records)) == 2


def test_sorts_by_publication_time_before_item_date():
    records = [
        record(1, "先发布但日期晚", 500, direction="lost"),
        record(2, "后发布但日期早", 100, direction="found"),
    ]
    records[0]["published_at"] = 1000
    records[1]["published_at"] = 2000
    assert [row["item"].id for row in filter_records(records)] == [2, 1]

from matching.report_meta import ReportMeta


def test_publish_records_time_and_visibility(tmp_path):
    meta = ReportMeta(tmp_path / "items.db")
    assert meta.get(1) is None
    assert meta.is_public(1) is True

    meta.publish(1, public=False)
    record = meta.get(1)
    assert record["public"] == 0
    assert record["published_at"] > 0
    first_published = record["published_at"]

    meta.publish(1, public=True)
    assert meta.get(1)["public"] == 1
    assert meta.get(1)["published_at"] == first_published
    assert meta.is_public(1) is True


def test_set_public_creates_or_updates_a_row(tmp_path):
    meta = ReportMeta(tmp_path / "items.db")
    meta.set_public(2, False)
    assert meta.is_public(2) is False
    meta.set_public(2, True)
    assert meta.is_public(2) is True
    assert meta.get(2)["published_at"] > 0

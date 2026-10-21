"""Public feed of unmatched lost and found reports.

Both directions are shown so a finder can also look for an owner, not only an
owner looking for a finder. The feed is discovery only: no contact details, no
request buttons, and only reports that are still active. Publication time comes
from `report_meta`, because `items.time` is the lost/found date, not the moment
the report was posted.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from db_manager import Database
from matching.content_hash import publication_text, watermark
from matching.engine import DISPLAY
from matching.fingerprint import display_value, fingerprint_from_text
from matching.report_meta import ReportMeta
from matching.storage import FingerprintStore
from ui.components import card, empty, page_header, pill, pills, topbar

ALL = "全部"
DIRECTIONS = {"全部": None, "失物": "lost", "拾获": "found"}
# Label -> days back. None means no time filter.
RANGES = {
    "全部": None,
    "最近 24 小时": 1,
    "最近 3 天": 3,
    "最近 7 天": 7,
    "最近 30 天": 30,
}
LIMIT = 60


def filter_records(records: list[dict], *, keyword: str = "", category: str = ALL,
                   location: str = ALL, cutoff: float | None = None,
                   direction: str | None = None) -> list[dict]:
    """Filter loaded records and return them newest first.

    Keyword matches the description, location, and attribute values in both
    canonical and Chinese display forms. Time and location are filters here,
    not ranking signals.
    """
    needle = (keyword or "").strip().casefold()
    selected = []
    for record in records:
        item = record["item"]
        attributes = record["attributes"]
        if direction and record.get("direction") != direction:
            continue
        if cutoff is not None and (not item.time or item.time < cutoff):
            continue
        if category != ALL and attributes.get("category") != category:
            continue
        if location != ALL and item.location != location:
            continue
        if needle:
            parts = [item.description or "", item.location or ""]
            for key, value in attributes.items():
                parts.append(str(value))
                parts.append(str(display_value(key, value)))
            if needle not in " ".join(parts).casefold():
                continue
        selected.append(record)
    return sorted(selected, key=lambda r: (r.get("published_at") or r["item"].time or 0,
                                           r["item"].id), reverse=True)


def load_records(db, store, meta=None) -> list[dict]:
    """Attach direction, fingerprint and publication metadata to both sides."""
    meta = meta or ReportMeta()
    records = []
    sources = (("lost", db.get_unmatched_lost_items()),
               ("found", db.get_unmatched_found_items()))
    for direction, items in sources:
        for item in items:
            info = meta.get(item.id)
            if info is not None and not info["public"]:
                continue
            fingerprint = store.get(item.id)
            attributes = (fingerprint or {}).get("attributes") or {}
            if not attributes:
                # Legacy rows may predate item_fingerprints; rules are free and offline.
                attributes = fingerprint_from_text(item.description or "", generate=False).get(
                    "attributes", {})
            records.append({
                "item": item,
                "attributes": attributes,
                "direction": direction,
                "published_at": info["published_at"] if info else None,
            })
    return records


def category_options(records: list[dict]) -> list[str]:
    values = {record["attributes"].get("category") for record in records}
    values.discard(None)
    values.discard("")
    return [ALL] + sorted(values, key=lambda value: display_value("category", value))


def location_options(records: list[dict]) -> list[str]:
    values = {record["item"].location for record in records if record["item"].location}
    return [ALL] + sorted(values)


def _date_text(value) -> str:
    if not value:
        return "未填写"
    try:
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return "未填写"


def _category_label(value: str) -> str:
    return ALL if value == ALL else display_value("category", value)


def _render_card(record: dict) -> None:
    item, attributes, direction = record["item"], record["attributes"], record["direction"]
    with st.container(border=True, key=f"browse-{item.id}"):
        badge = pill("失物", "lost") if direction == "lost" else pill("拾获", "found")
        st.markdown(badge, unsafe_allow_html=True)
        if item.image is not None:
            st.image(watermark(item.image, item.id, record.get("published_at")),
                     use_container_width=True)
        st.write(item.description or "（没有描述）")
        st.caption(f"地点：{item.location or '未知'} · 日期：{_date_text(item.time)}")
        st.caption(publication_text(item.id, item.description or "",
                                    record.get("published_at")))
        chips = "".join(
            pill(f"{DISPLAY.get(key, key)}：{display_value(key, value)}", "brand")
            for key, value in list(attributes.items())[:6]
        )
        if chips:
            pills(chips)


def _report_cta() -> None:
    st.write("")
    st.caption("看到像自己的东西？先登记，系统会用证据和它比对。")
    left, right = st.columns(2, gap="small")
    with left:
        if st.button("我丢了东西，去登记", key="browse-report-lost", use_container_width=True):
            st.session_state.report_mode_pending = "lost"
            st.session_state.state = "report"
            st.rerun()
    with right:
        if st.button("我捡到东西，去登记", key="browse-report-found", use_container_width=True):
            st.session_state.report_mode_pending = "found"
            st.session_state.state = "report"
            st.rerun()


def browse(authenticator):
    topbar("browse", authenticator)
    page_header("search", "近期丢失 / 拾获",
                "所有已登录用户登记的未配对失物与拾获；联系方式仍然只在双方确认后可见。")

    db = Database()
    try:
        records = load_records(db, FingerprintStore(), ReportMeta())
    finally:
        db.close()

    if not records:
        empty("search", "还没有公开的失物或拾获", "等有人登记后，这里会出现。")
        _report_cta()
        return

    with card("browse-filters"):
        st.markdown("### 筛选")
        columns = st.columns([1.1, 2, 1.1, 1.1, 1.2], gap="medium")
        with columns[0]:
            direction_label = st.selectbox("方向", list(DIRECTIONS), key="browse-direction")
        with columns[1]:
            keyword = st.text_input(
                "关键词",
                placeholder="描述、地点或属性，例如 黑色 / 图书馆",
                key="browse-keyword",
            )
        with columns[2]:
            category = st.selectbox(
                "类型",
                category_options(records),
                format_func=_category_label,
                key="browse-category",
            )
        with columns[3]:
            location = st.selectbox("地点", location_options(records), key="browse-location")
        with columns[4]:
            range_label = st.selectbox("时间", list(RANGES), key="browse-range")

    days = RANGES[range_label]
    cutoff = (datetime.now().timestamp() - days * 86400) if days else None
    matched = filter_records(records, keyword=keyword, category=category,
                             location=location, cutoff=cutoff,
                             direction=DIRECTIONS[direction_label])
    visible = matched[:LIMIT]

    if not matched:
        empty("search", "没有符合条件的记录", "换个关键词，或把时间范围放宽。")
    else:
        lost_count = sum(1 for record in matched if record["direction"] == "lost")
        found_count = len(matched) - lost_count
        suffix = f"（最多显示最近 {LIMIT} 件）" if len(matched) > LIMIT else ""
        st.caption(f"共 {len(matched)} 件（失物 {lost_count} · 拾获 {found_count}）{suffix}")
        st.caption("发布时间用于标明先后；描述会公开展示，请勿写门牌号、证件号等敏感信息。")
        for start in range(0, len(visible), 3):
            columns = st.columns(3, gap="medium")
            for column, record in zip(columns, visible[start:start + 3]):
                with column:
                    _render_card(record)

    _report_cta()

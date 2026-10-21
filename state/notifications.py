"""In-app alerts for subscribed lost reports.

A notification is created when a newly registered found item scores above the
evidence threshold against a lost report the user subscribed to. The page only
shows item descriptions and attributes; contact details still require acceptance
through `MatchRequests`.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

import streamlit as st

from db_manager import Database
from matching.content_hash import publication_text, watermark
from matching.fingerprint import fingerprint_from_text
from matching.lifecycle import status_label
from matching.notifications import Notifications
from matching.report_meta import ReportMeta
from matching.storage import FingerprintStore
from matching.workflow import build_session
from ui.components import empty, page_header, pill, topbar


def _stamp_text(value) -> str:
    if not value:
        return "未知"
    try:
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return "未知"


def _date_text(value) -> str:
    if not value:
        return "未填写"
    try:
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return "未填写"


def _open_lost_match(lost_id: int) -> None:
    """Rebuild a match session for an existing lost report and open it."""
    username = st.session_state.username
    db = Database()
    try:
        if not db.lost_item_exists(lost_id, username):
            st.error("这条失物不属于当前账号。")
            return
        if not db.item_exists(lost_id):
            st.error("这条失物记录已经不存在。")
            return
        if db.get_lost_item_matches(lost_id):
            st.info("这条失物已经配对成功，不再显示候选。")
            return
        lost = db.get_item(lost_id)
        if lost.emb is None:
            st.error("这条失物没有可用的向量，无法重新匹配；可以撤销后重新登记。")
            return
        store = FingerprintStore()
        fingerprint = store.get(lost_id) or fingerprint_from_text(
            lost.description or "", generate=False)
        try:
            session = build_session(direction="lost", item_id=lost_id,
                                    query_embedding=lost.emb, fingerprint=fingerprint,
                                    username=username, db=db, store=store,
                                    query_time=lost.time, query_location=lost.location)
        except (OSError, ValueError, RuntimeError, ImportError) as error:
            st.error(f"无法打开候选：{error}")
            return
    finally:
        db.close()
    st.session_state.match_session = session
    st.session_state.state = "interactive_match"
    st.rerun()


def notifications(authenticator):
    topbar("notifications", authenticator)
    page_header("bell", "通知", "有人捡到可能与你失物相关的物品时，会出现在这里。")

    username = st.session_state.username
    store = Notifications()
    try:
        unread = store.unread_count(username)
        records = store.list(username)
    except sqlite3.Error:
        st.error("通知读取失败，请稍后重试。")
        return
    st.session_state.unread_notifications = unread

    if unread:
        st.caption(f"未读 {unread} 条。")
        if st.button("全部标为已读", key="notifications-read-all"):
            store.mark_all_read(username)
            st.session_state.unread_notifications = 0
            st.rerun()
    else:
        st.caption("没有未读通知。")

    if not records:
        empty("bell", "还没有通知",
              "登记失物时勾选「有新拾获时通知我」，之后有相关拾获会在这里提醒。")
        if st.button("去登记物品", key="notifications-lost", use_container_width=True):
            st.session_state.report_mode_pending = "lost"
            st.session_state.state = "report"
            st.rerun()
        return

    db = Database()
    report_meta = ReportMeta()
    try:
        for record in records:
            found = db.get_item(record["found_item_id"]) if db.item_exists(
                record["found_item_id"]) else None
            lost = (db.get_item(record["lost_item_id"])
                    if record["lost_item_id"] and db.item_exists(record["lost_item_id"])
                    else None)
            meta = report_meta.get(found.id) if found is not None else None
            published_at = meta.get("published_at") if meta else None
            found_status = db.get_item_status(record["found_item_id"]) if found is not None else None
            lost_status = db.get_item_status(record["lost_item_id"]) if lost is not None else None
            with st.container(border=True, key=f'notification-{record["id"]}'):
                badge = pill("未读", "warn") if record["read_at"] is None else pill("已读", "ok")
                st.markdown(badge, unsafe_allow_html=True)
                st.caption(f"收到时间：{_stamp_text(record['created_at'])}")

                columns = st.columns([1, 3], gap="medium")
                with columns[0]:
                    if found is not None and found.image is not None:
                        st.image(watermark(found.image, found.id, published_at), width=160)
                with columns[1]:
                    st.write(found.description if found is not None else "（拾获记录已删除）")
                    if found is not None:
                        st.caption(f"地点：{found.location or '未知'} · 日期：{_date_text(found.time)}")
                        st.caption(publication_text(found.id, found.description or "",
                                                    published_at))
                    if record["score"] is not None:
                        st.caption(f"排序指标 {record['score']:.3f} · 不是所有权概率")
                    if found_status:
                        st.caption(f"这条拾获已标记为{status_label(found_status, False)}。")
                    if lost is not None:
                        st.caption(f"对应你的失物：{lost.description}")
                        if lost_status:
                            st.caption(f"这件失物已标记为{status_label(lost_status, True)}，不再显示候选。")
                    elif record["lost_item_id"]:
                        st.caption("对应失物已经被撤销或删除。")

                actions = st.columns([2, 1, 1], gap="small")
                with actions[0]:
                    if record["lost_item_id"] and lost is not None and not lost_status:
                        if st.button("查看这件失物的候选", key=f'open-{record["id"]}',
                                     type="primary", use_container_width=True):
                            store.mark_read(username, record["id"])
                            _open_lost_match(record["lost_item_id"])
                with actions[1]:
                    if st.button("浏览近期动态", key=f'go-browse-{record["id"]}',
                                 use_container_width=True):
                        st.session_state.state = "browse"
                        st.rerun()
                with actions[2]:
                    if record["read_at"] is None:
                        if st.button("标为已读", key=f'read-{record["id"]}',
                                     use_container_width=True):
                            store.mark_read(username, record["id"])
                            st.rerun()
    finally:
        db.close()

    st.write("")
    if st.button("前往我的记录", key="notifications-profile", use_container_width=True):
        st.session_state.state = "profile"
        st.rerun()

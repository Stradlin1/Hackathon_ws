"""Home: pick a direction and see your own counters."""

from __future__ import annotations

import streamlit as st

from db_manager import Database
from matching.requests import MatchRequests
from ui.components import card, page_header, pill, pills_html, stat_row, topbar


def _counts(username: str):
    """(lost, found, pending). A broken database must not break the home page."""
    lost = found = pending = 0
    try:
        db = Database()
        try:
            lost = len(db.get_user_lost_items(username))
            found = len(db.get_user_found_items(username))
        finally:
            db.close()
        pending = len(MatchRequests().incoming(username))
    except Exception:
        pass
    return lost, found, pending


def lost_or_found(authenticator):
    topbar('lost_or_found', authenticator)
    name = st.session_state.get('name') or st.session_state.get('username') or ''
    page_header('home', f'你好，{name}', '登记物品，AI 帮你收敛候选，最后由双方确认。')

    left, right = st.columns(2, gap='large')
    with left:
        with card('lost'):
            st.markdown(
                pills_html('lost', '登记失物', '写下颜色、品牌、划痕或贴纸，越具体越容易匹配。',
                           art_name='card-lost'),
                unsafe_allow_html=True,
            )
            if st.button('开始登记失物', key='cta-lost', type='primary', use_container_width=True):
                st.session_state.report_mode_pending = 'lost'
                st.session_state.state = 'report'
                st.rerun()
    with right:
        with card('found'):
            st.markdown(
                pills_html('found', '登记拾获', '上传一张照片，AI 会先生成描述，你可以随时修改。',
                           art_name='card-found'),
                unsafe_allow_html=True,
            )
            if st.button('开始登记拾获', key='cta-found', type='primary', use_container_width=True):
                st.session_state.report_mode_pending = 'found'
                st.session_state.state = 'report'
                st.rerun()

    st.write('')
    st.caption('不急着登记？先看看大家最近的丢失与拾获。')
    if st.button('浏览近期动态', key='cta-browse', use_container_width=True):
        st.session_state.state = 'browse'
        st.rerun()

    username = st.session_state.get('username', '')
    lost, found, pending = _counts(username)
    stat_row([
        (lost, '我的失物', '已登记'),
        (found, '我的拾获', '已登记'),
        (pending, '待我确认', '对方在等你'),
    ])
    st.caption('排序指标只表示相似程度，不代表所有权；联系方式需双方确认后可见。')

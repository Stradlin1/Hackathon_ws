"""Item history and two-party approval of proposed matches."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from db_manager import Database
from matching.engine import DISPLAY
from matching.fingerprint import FIELDS, display_value, normalize_answer
from matching.requests import MatchRequests
from matching.storage import FingerprintStore
from ui.components import card, empty, esc, page_header, pill, pills, stat_row, status_badge, topbar

STATUS_DISPLAY = {'pending': '待确认', 'accepted': '已接受', 'rejected': '已拒绝'}


def _date_text(item) -> str:
    return datetime.fromtimestamp(item.time).strftime('%Y-%m-%d') if item.time else '未填写'


@st.dialog('补全物品信息')
def _enrich_dialog(item_id: int) -> None:
    """Let the owner add or correct attributes; saved values are shared with matches."""
    store = FingerprintStore()
    fingerprint = store.get(item_id) or {}
    attributes = fingerprint.get('attributes') or {}
    values = {}
    with st.form(f'enrich-{item_id}'):
        st.caption('留空表示不确定；写「无标记」表示没有特殊标记。保存后立刻参与匹配，对方也能看到。')
        for field in FIELDS:
            values[field] = st.text_input(
                DISPLAY.get(field, field),
                value=display_value(field, attributes.get(field, '')),
                key=f'enrich-input-{item_id}-{field}',
            )
        submitted = st.form_submit_button('保存', type='primary', use_container_width=True)
    if not submitted:
        return
    updates = {}
    unknown = []
    for field, raw in values.items():
        text = (raw or '').strip()
        if not text:
            continue
        normalized = normalize_answer(field, text)
        if normalized:
            updates[field] = normalized
        else:
            unknown.append(DISPLAY.get(field, field))
    if updates:
        store.merge(item_id, updates)
    if unknown:
        st.warning('这些没看懂，已跳过：' + '、'.join(unknown))
    else:
        st.rerun()


def _item_card(key, item, show_image=False):
    with st.container(border=True, key=key):
        cols = st.columns([1, 3], gap='medium') if show_image and item.image is not None else None
        if cols is None:
            st.write(item.description)
            st.caption(f'地点：{item.location} | 日期：{_date_text(item)} | #{item.id}')
        else:
            with cols[0]:
                st.image(item.image, width=160)
            with cols[1]:
                st.write(item.description)
                st.caption(f'地点：{item.location} | 日期：{_date_text(item)} | #{item.id}')
        attributes = (FingerprintStore().get(item.id) or {}).get('attributes') or {}
        chips = ''.join(pill(f'{DISPLAY.get(field, field)}：{display_value(field, value)}')
                        for field, value in attributes.items())
        if chips:
            pills(chips)
        if st.button('补全信息', key=f'enrich-{item.id}', type='secondary'):
            _enrich_dialog(item.id)


def profile(authenticator):
    topbar('profile', authenticator)
    page_header('folder', '我的物品与请求', '你登记的东西、别人发来的请求，以及已经确认的匹配。')

    username = st.session_state.username
    db = Database()
    try:
        lost_items = db.get_user_lost_items(username)
        found_items = db.get_user_found_items(username)
    finally:
        db.close()

    requests = MatchRequests()
    incoming = requests.incoming(username)

    stat_row([
        (len(lost_items), '我的失物', '已登记'),
        (len(found_items), '我的拾获', '已登记'),
        (len(incoming), '待我确认', '对方在等你'),
    ])

    st.markdown('### 我的失物')
    if not lost_items:
        empty('clipboard', '还没有登记失物', '从首页点「登记失物」开始。')
    for item in lost_items:
        _item_card(f'profile-lost-{item.id}', item)

    st.markdown('### 我的拾获')
    if not found_items:
        empty('camera', '还没有登记拾获物品', '从首页点「登记拾获」上传一张照片。')
    for item in found_items:
        _item_card(f'profile-found-{item.id}', item, show_image=True)

    st.markdown('### 等待你确认的请求')
    if not incoming:
        empty('inbox', '暂无待确认请求', '对方发起请求后会出现在这里。')
    for req in incoming:
        found, lost = req['found_item_id'], req['lost_item_id']
        with st.container(border=True, key=f'req-{found}-{lost}'):
            st.write(f'拾获：{req["found_desc"]}')
            st.write(f'丢失：{req["lost_desc"]}')
            st.caption('接受之后，双方才会看到彼此的联系方式。')
            left, right = st.columns(2, gap='small')
            with left:
                if st.button('接受匹配', key=f'accept-{found}-{lost}', type='primary',
                             use_container_width=True):
                    if requests.respond(username, found, lost, True):
                        st.rerun()
            with right:
                if st.button('拒绝匹配', key=f'reject-{found}-{lost}', use_container_width=True):
                    if requests.respond(username, found, lost, False):
                        st.rerun()

    st.markdown('### 我发出的请求')
    outgoing = requests.outgoing(username)
    if not outgoing:
        empty('inbox', '还没有发出请求', '在匹配结果里选中候选后发送。')
    for req in outgoing:
        st.markdown(
            f'拾获 #{req["found_item_id"]} / 失物 #{req["lost_item_id"]}　'
            + status_badge(req['status']),
            unsafe_allow_html=True,
        )

    st.markdown('### 已确认的匹配')
    accepted = requests.accepted(username)
    if not accepted:
        empty('handshake', '暂无双方确认的匹配', '双方都同意后，联系方式会出现在这里。')
    for req in accepted:
        with st.container(border=True, key=f'accepted-{req["found_item_id"]}-{req["lost_item_id"]}'):
            st.write(f'拾获 #{req["found_item_id"]} / 失物 #{req["lost_item_id"]}')
            st.markdown(
                f'<div class="pill pill-ok">联系方式</div> '
                f'<strong>{esc(req["contact_username"])}</strong> · {esc(req["contact_email"])}',
                unsafe_allow_html=True,
            )

    st.write('')
    if st.button('继续登记物品', type='primary', use_container_width=True):
        st.session_state.state = 'lost_or_found'
        st.rerun()

"""Item history and two-party approval of proposed matches."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from db_manager import Database
from matching.requests import MatchRequests

STATUS_DISPLAY = {'pending': '待确认', 'accepted': '已接受', 'rejected': '已拒绝'}


def profile(authenticator):
    authenticator.logout(button_name='退出登录', location='sidebar')
    username = st.session_state.username
    st.title('我的物品与请求')
    db = Database()
    try:
        lost_items = db.get_user_lost_items(username)
        found_items = db.get_user_found_items(username)
        st.subheader('我的失物')
        for item in lost_items:
            st.write(f'#{item.id}：{item.description}')
            date_text = (datetime.fromtimestamp(item.time).strftime('%Y-%m-%d')
                         if item.time else '未填写')
            st.caption(f'地点：{item.location} | 日期：{date_text}')
        st.subheader('我的拾获')
        for item in found_items:
            st.write(f'#{item.id}：{item.description}')
            if item.image is not None:
                st.image(item.image, width=250)
    finally:
        db.close()

    requests = MatchRequests()
    st.subheader('等待你确认的请求')
    incoming = requests.incoming(username)
    if not incoming:
        st.write('暂无待确认请求。')
    for req in incoming:
        found, lost = req['found_item_id'], req['lost_item_id']
        st.write(f'拾获：{req["found_desc"]} | 丢失：{req["lost_desc"]}')
        a, b = st.columns(2)
        with a:
            if st.button('接受匹配', key=f'accept-{found}-{lost}'):
                if requests.respond(username, found, lost, True):
                    st.rerun()
        with b:
            if st.button('拒绝匹配', key=f'reject-{found}-{lost}'):
                if requests.respond(username, found, lost, False):
                    st.rerun()

    st.subheader('我发出的请求')
    for req in requests.outgoing(username):
        st.write(f'拾获 #{req["found_item_id"]} / 失物 #{req["lost_item_id"]}：{STATUS_DISPLAY.get(req["status"], req["status"])}')

    st.subheader('已确认的匹配')
    accepted = requests.accepted(username)
    if not accepted:
        st.write('暂无双方确认的匹配。')
    for req in accepted:
        st.write(f'拾获 #{req["found_item_id"]} / 失物 #{req["lost_item_id"]}')
        st.write(f'联系方式：{req["contact_username"]}（{req["contact_email"]}）')

    if st.button('继续登记物品'):
        st.session_state.state = 'lost_or_found'
        st.rerun()

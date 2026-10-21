"""Login page: brand panel on the left, the app's own Chinese form on the right."""

from __future__ import annotations

import streamlit as st

from db_manager import Database, User
from ui.components import LOGO, auth_point


def _remember_user(username: str, config: dict) -> None:
    """Mirror the authenticated account into the local users table and session."""
    account = config.get('credentials', {}).get('usernames', {}).get(username, {})
    user = User(username, '', account.get('email', ''))
    st.session_state.user = user
    db = Database()
    try:
        db.insert_user(user)
    finally:
        db.close()


def login(authenticator, config):
    st.session_state.state = 'login'

    left, right = st.columns([1.15, 1], gap='large', vertical_alignment='center')
    with left:
        st.image(str(LOGO), width=88)
        st.markdown('<div class="auth-title">404NotFound</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="auth-lead">丢了东西，或者捡到东西——让一段描述和一张照片重新对上。</p>',
            unsafe_allow_html=True,
        )
        auth_point('search', '跨模态检索', '文字描述与物品照片落在同一个向量空间')
        auth_point('layers', '证据重排', '一致的特征加分，矛盾的特征扣分')
        auth_point('lock', '双方确认', '只有对方接受之后才交换联系方式')

    with right:
        registered = st.session_state.pop('registered_username', None)
        if registered:
            st.success(f'账号「{registered}」注册成功，请登录。')

        with st.form('login_form'):
            st.markdown('<div class="auth-card-title">欢迎回来</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-card-sub">登录后即可登记物品、查看匹配</div>',
                        unsafe_allow_html=True)
            username = st.text_input('用户名', placeholder='例如 alice', max_chars=20)
            password = st.text_input('密码', type='password', placeholder='至少 8 位')
            submitted = st.form_submit_button('登录', type='primary', use_container_width=True)

        if submitted:
            username = (username or '').strip().lower()
            if not username or not password:
                st.warning('请输入用户名和密码')
            elif authenticator.authentication_controller.login(username, password):
                _remember_user(username, config)
                # The library writes its cookie in this run, which ends in st.rerun();
                # app.py rewrites it on the next run so it actually reaches the browser.
                st.session_state.auth_cookie_pending = True
                st.session_state.state = 'lost_or_found'
                st.rerun()
            else:
                st.error('用户名或密码错误')

        st.markdown('<div class="auth-alt">还没有账号？</div>', unsafe_allow_html=True)
        if st.button('注册账号', type='tertiary', use_container_width=True):
            st.session_state.state = 'register'
            st.rerun()

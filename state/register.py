"""Local account registration with a Chinese-friendly form."""

from __future__ import annotations

import re
from pathlib import Path

import bcrypt
import streamlit as st
import yaml

from db_manager import Database, User
from ui.components import LOGO, auth_point

CONFIG_PATH = Path('config_auth.yaml')
USERNAME_PATTERN = re.compile(r'^[a-z0-9_-]{3,20}$')
EMAIL_PATTERN = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')


def validate_registration(name, email, username, password, repeat, usernames):
    """Return (name, username, email, error); error is None when the input is valid."""
    name = (name or '').strip()
    email = (email or '').strip()
    username = (username or '').strip().lower()
    password = password or ''
    repeat = repeat or ''

    if not name:
        return name, username, email, '请填写姓名。'
    if len(name) > 40:
        return name, username, email, '姓名最多 40 个字符。'
    if not USERNAME_PATTERN.fullmatch(username):
        return name, username, email, '用户名需为 3–20 位字母、数字、下划线或连字符。'
    if any(existing.lower() == username for existing in usernames):
        return name, username, email, '这个用户名已经被注册。'
    if not EMAIL_PATTERN.fullmatch(email):
        return name, username, email, '邮箱格式不正确。'
    if any(isinstance(entry, dict) and str(entry.get('email', '')).lower() == email.lower()
           for entry in usernames.values()):
        return name, username, email, '这个邮箱已经被使用。'
    if len(password) < 8:
        return name, username, email, '密码至少 8 位。'
    if len(password) > 64:
        return name, username, email, '密码最多 64 位。'
    if len(password.encode('utf-8')) > 72:
        return name, username, email, '密码过长，请控制在 72 字节以内。'
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return name, username, email, '密码需要同时包含字母和数字。'
    if password != repeat:
        return name, username, email, '两次输入的密码不一致。'
    return name, username, email, None


def _insert_user(username: str, email: str) -> None:
    """Best-effort mirror into the local users table; login will retry if this fails."""
    try:
        db = Database()
        try:
            db.insert_user(User(username, '', email))
        finally:
            db.close()
    except Exception:
        pass


def register(_authenticator, config):
    left, right = st.columns([1.05, 1], gap='large', vertical_alignment='center')
    with left:
        st.image(str(LOGO), width=72)
        st.markdown('<div class="auth-title">创建本地账号</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="auth-lead">账号只保存在这台机器的 config_auth.yaml 里，密码以 bcrypt 哈希保存。</p>',
            unsafe_allow_html=True,
        )
        auth_point('user', '中文姓名', '可以用中文，配对结果里会显示它')
        auth_point('lock', '密码规则', '至少 8 位，同时包含字母和数字')
        auth_point('check', '不需要验证码', '本机演示环境省掉这一步')

    with right:
        with st.form('register_form'):
            st.markdown('<div class="auth-card-title">填写账号信息</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-card-sub">用户名注册后不可修改</div>', unsafe_allow_html=True)
            name = st.text_input('姓名', max_chars=40, help='可以使用中文')
            email = st.text_input('邮箱', max_chars=254, placeholder='name@example.com')
            username = st.text_input('用户名', max_chars=20, help='3–20 位字母、数字、下划线或连字符')
            password = st.text_input('密码', type='password', max_chars=64,
                                     help='至少 8 位，且同时包含字母和数字')
            repeat = st.text_input('确认密码', type='password', max_chars=64)
            submitted = st.form_submit_button('注册', type='primary', use_container_width=True)

        if submitted:
            usernames = config.setdefault('credentials', {}).setdefault('usernames', {})
            name, username, email, error = validate_registration(
                name, email, username, password, repeat, usernames
            )
            if error is None:
                try:
                    db = Database()
                    try:
                        if db.username_exists(username):
                            error = '这个用户名已经被注册。'
                    finally:
                        db.close()
                except Exception:
                    pass

            if error:
                st.error(error)
            else:
                usernames[username] = {
                    'email': email,
                    'name': name,
                    'password': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode(),
                }
                try:
                    CONFIG_PATH.write_text(
                        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding='utf-8'
                    )
                    CONFIG_PATH.chmod(0o600)
                except (OSError, yaml.YAMLError) as exc:
                    usernames.pop(username, None)
                    st.error(f'保存账号失败：{exc}')
                else:
                    _insert_user(username, email)
                    st.session_state.registered_username = username
                    st.session_state.state = 'login'
                    st.rerun()

        if st.button('返回登录', use_container_width=True):
            st.session_state.state = 'login'
            st.rerun()

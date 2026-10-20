"""Local account registration."""

import streamlit as st
import yaml

from db_manager import Database, User


def register(authenticator, config):
    st.title('注册账号')
    try:
        registered = authenticator.register_user(
            pre_authorization=False,
            fields={
                'Form name': '注册账号',
                'Name': '姓名',
                'Email': '邮箱',
                'Username': '用户名',
                'Password': '密码',
                'Repeat password': '确认密码',
                'Register': '注册',
                'Captcha': '验证码',
            },
            key='注册',
        )
        if registered and registered[0]:
            email, username, _ = registered
            with open('config_auth.yaml', 'w', encoding='utf-8') as file:
                yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)
            db = Database()
            try:
                db.insert_user(User(username, '', email))
            finally:
                db.close()
            st.success('账号注册成功，请登录。')
            st.session_state.state = 'login'
            st.rerun()
    except Exception as error:
        st.error(f'注册失败：{error}')
    if st.button('返回登录'):
        st.session_state.state = 'login'
        st.rerun()

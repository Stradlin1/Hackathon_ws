import streamlit as st
from db_manager import Database, User


def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state


def login(authenticator, config):
    st.session_state.state = 'login'

    st.title('404NotFound')
    registered = st.session_state.pop('registered_username', None)
    if registered:
        st.success(f'账号「{registered}」注册成功，请登录。')
    st.write('这里可以登记丢失的物品，也可以登记你捡到的东西，并用 AI 辅助匹配找到可能的失主。')

    try:
        authenticator.login(fields={
            'Form name': '登录',
            'Username': '用户名',
            'Password': '密码',
            'Login': '登录',
            'Captcha': '验证码',
        })
    except Exception as exc:
        st.error(exc)

    st.button('注册账号', on_click=change_state, args=['register'])

    if st.session_state.get('authentication_status'):
        authenticator.logout(button_name='退出登录')

        username = st.session_state.get('username', '')
        account = config.get('credentials', {}).get('usernames', {}).get(username, {})
        user = User(username, '', account.get('email', ''))
        st.session_state.user = user

        db = Database()
        db.insert_user(user)
        db.close()

        st.write(f'欢迎，*{st.session_state.get("name", username)}*')
        change_state('lost_or_found')
        st.rerun()
    elif st.session_state.get('authentication_status') is False:
        st.error('用户名或密码错误')
    else:
        st.warning('请输入用户名和密码')

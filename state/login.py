import streamlit as st
from db_manager import Database, User


def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state


def login(authenticator, config):
    st.session_state.state = 'login'

    st.title('404NotFound')
    st.write('This is a web app that helps you find your lost items or report items you found.')

    try:
        authenticator.login()
    except Exception as exc:
        st.error(exc)

    st.button('Register User', on_click=change_state, args=['register'])

    if st.session_state.get('authentication_status'):
        authenticator.logout()

        username = st.session_state.get('username', '')
        account = config.get('credentials', {}).get('usernames', {}).get(username, {})
        user = User(username, '', account.get('email', ''))
        st.session_state.user = user

        db = Database()
        db.insert_user(user)
        db.close()

        st.write(f'Welcome *{st.session_state.get("name", username)}*')
        change_state('lost_or_found')
        st.rerun()
    elif st.session_state.get('authentication_status') is False:
        st.error('Username/password is incorrect')
    else:
        st.warning('Please enter your username and password')

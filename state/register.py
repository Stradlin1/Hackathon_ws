"""Local account registration."""

import streamlit as st
import yaml

from db_manager import Database, User


def register(authenticator, config):
    st.title('Register an account')
    try:
        registered = authenticator.register_user(pre_authorization=False)
        if registered and registered[0]:
            email, username, _ = registered
            with open('config_auth.yaml', 'w', encoding='utf-8') as file:
                yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)
            db = Database()
            try:
                db.insert_user(User(username, '', email))
            finally:
                db.close()
            st.success('Account registered. You can now sign in.')
            st.session_state.state = 'login'
            st.rerun()
    except Exception as error:
        st.error(f'Account registration failed: {error}')
    if st.button('Back to sign in'):
        st.session_state.state = 'login'
        st.rerun()

"""Streamlit entry point for multimodal lost-and-found matching."""

from pathlib import Path

import streamlit as st
import streamlit_authenticator as stauth
import yaml

from state.found import found
from state.interactive_match import interactive_match
from state.login import login
from state.lost import lost
from state.lost_or_found import lost_or_found
from state.profile import profile
from state.register import register

st.set_page_config(page_title='404NotFound · 失物招领', page_icon='🔎')
config_file = Path(__file__).with_name('config_auth.yaml')
if not config_file.exists():
    st.error('缺少 config_auth.yaml。请复制 config_auth.example.yaml 并配置本地账号。')
    st.stop()
with config_file.open(encoding='utf-8') as file:
    config = yaml.safe_load(file)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

# Only authenticated users may access reports, matchmaking or contact details.
state = st.session_state.get('state', 'login')
if state == 'register':
    register(authenticator, config)
elif state == 'login' or not st.session_state.get('authentication_status'):
    login(authenticator, config)
elif state == 'lost_or_found':
    lost_or_found(authenticator)
elif state == 'lost':
    lost(authenticator)
elif state == 'found':
    found(authenticator)
elif state == 'interactive_match':
    interactive_match(authenticator)
elif state == 'profile':
    profile(authenticator)
else:
    st.session_state.state = 'lost_or_found'
    st.rerun()

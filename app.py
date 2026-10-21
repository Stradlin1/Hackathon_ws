"""Streamlit entry point for multimodal lost-and-found matching."""

from datetime import datetime
from pathlib import Path

import jwt
import streamlit as st
import streamlit_authenticator as stauth
import yaml

from db_manager import User
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


def _request_cookie():
    """Return the re-authentication cookie carried by the current request, if any."""
    try:
        return st.context.cookies.get(config['cookie']['name'])
    except Exception:  # no request context, e.g. bare script execution
        return None


def _restore_from_cookie() -> None:
    """Sign the session back in from the request cookie before rendering anything.

    streamlit-authenticator restores the session inside login(), which draws the login
    form first and only redirects on the following run, so a refresh flashes the login
    page. The cookie is the library's own HS256 token (username/exp_date), so reading
    it from the request headers restores the same session state without a detour.
    """
    if st.session_state.get('authentication_status') or st.session_state.get('logout'):
        return
    raw = _request_cookie()
    if not raw:
        return
    try:
        token = jwt.decode(raw, config['cookie']['key'], algorithms=['HS256'])
    except jwt.InvalidTokenError:
        return
    if token.get('exp_date', 0) <= datetime.now().timestamp():
        return
    try:
        authenticator.authentication_controller.login(token=token)
    except Exception:
        return
    account = config['credentials']['usernames'][token['username']]
    st.session_state.user = User(token['username'], '', account.get('email', ''))


_restore_from_cookie()

# The password check renders the re-authentication cookie in the same run that ends in
# st.rerun(), and Streamlit drops elements rendered by an aborted run, so that write
# never reaches the browser and a refresh would log the user out. Write it in a run
# that renders normally instead: the run right after login, or the first run of an
# already signed-in session that has no cookie yet (a session older than this fix).
pending = st.session_state.pop('auth_cookie_pending', False)
missing_cookie = (
    st.session_state.get('authentication_status')
    and st.session_state.get('state') != 'login'
    and not _request_cookie()
    and not st.session_state.get('auth_cookie_synced')
)
if pending or missing_cookie:
    st.session_state.auth_cookie_synced = True
    authenticator.cookie_controller.set_cookie()

# Only authenticated users may access reports, matchmaking or contact details.
state = st.session_state.get('state', 'login')
if state == 'login' and st.session_state.get('authentication_status'):
    # A refresh restored the session above: never show the login page again.
    state = st.session_state.state = 'lost_or_found'
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

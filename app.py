# set environment variable before:
    # for windows: $env:STREAMLIT_SERVER_ENABLE_STATIC_SERVING = 'true'
    # for linux: export STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true
# run with streamlit run app.py

import streamlit as st
# import folium

import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from streamlit_extras.stylable_container import stylable_container

from state.login import login
from state.register import register
from state.lost_or_found import lost_or_found
from state.lost import lost
from state.found import found
from state.profile import profile
from state.this_your_item import this_your_item
from state.this_description_matches import this_description_matches
from state.someone_found import someone_found
from state.someone_lost import someone_lost

def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state

# authenticate setup
with open('./config_auth.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

col1, col2, col3 = st.columns(3)

with col1:
    pass
with col3:
    pass
with col2:
    with stylable_container(
                key="logo",
                css_styles="""
                    button {
                        display: inline-block;  /* Allows width adjustment */
                        width: 150px;  /* Set a width for the logo */
                        aspect-ratio: 1 / 1;  /* Keep a 1:1 ratio */
                        border: none;  /* Remove border */
                        background-image: url('./app/static/logo_rounded.png');
                        background-size: cover;
                        background-position: center;                    
                        top: 50%;  /* Align to the top */
                        left: 50%;  /* Align to the left */
                        margin: 10px;  /* Add some spacing from the edges */
                    }
                    """,
    ):
        if 'state' not in st.session_state or st.session_state.state == 'login':
            st.button(label="", key="logo", on_click=change_state, args=["login"])
        else:
            st.button(label="", key="logo", on_click=change_state, args=["lost_or_found"])

# state machine
if 'state' not in st.session_state or st.session_state.state == 'login':
    login(authenticator, config)

elif st.session_state.state == 'register':
    register(authenticator, config)

elif st.session_state.state == 'lost_or_found':
    lost_or_found(authenticator)

elif st.session_state.state == 'lost':
    lost(authenticator)

elif st.session_state.state == 'found':
    found(authenticator)

elif st.session_state.state == 'profile':
    profile(authenticator)

elif st.session_state.state == 'this_your_item':
    this_your_item(authenticator)

elif st.session_state.state == 'this_description_matches':
    this_description_matches(authenticator)

elif st.session_state.state == 'someone_found':
    someone_found(authenticator)

elif st.session_state.state == 'someone_lost':
    someone_lost(authenticator)

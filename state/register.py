import streamlit as st
import yaml
from db_manager import *

def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state

def register(authenticator, config):
    st.session_state.state = 'register'

    st.title('404NotFound')

    st.write('This is a web app that helps you find your lost items or report items you found.')

    try:
        email_of_registered_user, \
        username_of_registered_user, \
        name_of_registered_user = authenticator.register_user()
        if email_of_registered_user:
            st.success('User registered successfully')
            
            
            with open('./config_auth.yaml', 'w') as file:
                yaml.dump(config, file, default_flow_style=False)

            # get database and add user to it
            db = Database()
            u = User(username_of_registered_user, '', email_of_registered_user)
            st.session_state.user = u
            db.insert_user(u)
            db.close()

            change_state('login')
            st.rerun()
    except Exception as e:
        st.error(e)

    st.button('Login User', on_click=change_state, args=['login'])
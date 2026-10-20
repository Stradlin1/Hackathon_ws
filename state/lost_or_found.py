"""Main menu for creating an item report."""

import streamlit as st


def lost_or_found(authenticator):
    authenticator.logout(button_name='退出登录', location='sidebar')
    st.title('404NotFound')
    st.write('登记丢失或拾获的物品，用 AI 辅助匹配帮你找到可能的失主。')
    left, right = st.columns(2)
    with left:
        if st.button('我丢了东西', use_container_width=True):
            st.session_state.state = 'lost'
            st.rerun()
    with right:
        if st.button('我捡到东西', use_container_width=True):
            st.session_state.state = 'found'
            st.rerun()
    if st.button('我的物品与请求'):
        st.session_state.state = 'profile'
        st.rerun()

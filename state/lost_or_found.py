import streamlit as st
# import streamlit_extras

from streamlit_extras.stylable_container import stylable_container


def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state

def lost_or_found(authenticator):

    # go back to profile page
    st.sidebar.markdown(st.session_state.username)
    st.sidebar.button(
        label = 'Your Profile',
        on_click=change_state, 
        args=['profile'],
    )

    # logout
    authenticator.logout(location='sidebar', callback=lambda _: change_state("login"))

    # title
    st.title('Have you lost or found an item?')

    col1, col2 = st.columns(2)
    
    # Define buttons in the left and right columns
    with col1:
        with stylable_container(
            key="lost_button",
            css_styles="""
                button {
                    border-radius: 10px;
                    padding: 30px 60px;  /* Increase padding for a larger button */
                    display: inline-block;  /* Allows width adjustment */
                    width: 100%;  /* Full width of the column */
                    aspect-ratio : 1 / 1; /* Set aspect ratio to 1:1 */
                    border: 3px solid lightgray;  /* Optional: add border to match the design */
                    background-image: url('./app/static/lost.png');
                    background-size: cover;
                    background-position: center;
                }
                """,
        ):
            st.button(label="", key="lost_button", on_click=change_state, args=["lost"])

    with col2:
        with stylable_container(
            key="found_button",
            css_styles="""
                button {
                    border-radius: 10px;
                    padding: 30px 60px;  /* Increase padding for a larger button */
                    display: inline-block;  /* Allows width adjustment */
                    width: 100%;  /* Full width of the column */
                    aspect-ratio : 1 / 1; /* Set aspect ratio to 1:1 */
                    border: 3px solid lightgray;  /* Optional: add border to match the design */
                    background-image: url('./app/static/found.png');
                    background-size: cover;
                    background-position: center;
                }
                """,
        ):
            st.button(label="", key="found_button",  on_click=change_state, args=["found"])

import streamlit as st
from streamlit_extras.stylable_container import stylable_container
from db_manager import Database

def change_state(state):
    if 'state' in st.session_state:
        st.session_state.state = state

def profile(authenticator):

    # sidebar stuff
    st.sidebar.markdown(st.session_state.username)
    authenticator.logout(location='sidebar', callback=lambda _: change_state("login"))
    st.sidebar.write('Other Options')
    st.sidebar.button(
        label = 'Report an Item',
        on_click=change_state, 
        args=['lost_or_found'],
    )
    
    # title
    st.title(f'{st.session_state.username}')


    # get items
    db = Database()
    lost_items = db.get_user_lost_items(st.session_state.username)
    lost_items_matches = [db.get_lost_item_matches(item.id) for item in lost_items]
    found_items = db.get_user_found_items(st.session_state.username)
    found_items_matches = [db.get_found_item_matches(item.id) for item in found_items]
    db.close()

    # lost items
    st.subheader('Items you lost')
    for item, matches in zip(lost_items, lost_items_matches):
        status = 'found' if len(matches) > 0 else 'not found yet'
        st.write(f"""
        <div style="border: 1px solid black; padding: 10px; margin: 10px; border-radius: 10px;">
            <p style="padding-left: 2em; text-indent: -2em"><strong>Description:</strong> {item.description}</p>
            <p><strong>Status:</strong> {status}</p>
        </div>
        """, unsafe_allow_html=True)

    # displaying found items with image and status
    st.subheader('Items you found')
    for item, matches in zip(found_items, found_items_matches):
        status = 'claimed' if len(matches) > 0 else 'not claimed yet'

        # Start the bordered div
        st.write(f"""
        <div style="border: 1px solid black; padding: 1px; margin: 1px; border-radius: 1px; text-align: center;">
        """, unsafe_allow_html=True)

        # Display the image using Streamlit
        if item.image is not None:
            st.image(item.image, use_column_width=True)
        else:
            st.write('<p><em>No image available</em></p>', unsafe_allow_html=True)

        # Add description and status inside the div
        st.write(f"""
            <p style="padding-left: 2em; text-indent: -2em"><strong>Description:</strong> {item.description}</p>
            <p><strong>Status:</strong> {status}</p>
        </div>
        """, unsafe_allow_html=True)



    # report lost or found item
    st.subheader('Report a lost or found item')
    st.button('Report', on_click=change_state, args=['lost_or_found'])
    
    # st.button("go to this your item", on_click=change_state, args=['this_your_item'])
    # st.button("go to someone_lost", on_click=change_state, args=['someone_lost'])
    # st.button("go to someone_found", on_click=change_state, args=['someone_found'])
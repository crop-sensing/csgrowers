import streamlit as st

st.set_page_config(initial_sidebar_state="expanded")

def get_authorized_pages():
    user = st.user

    if not user.is_logged_in:
        return [st.Page("pages/login.py", title="Login")]

    email = user.email
    pages = []

    pages.append(st.Page("pages/homepage.py", title="Home", icon="🏠"))

    if email.endswith("@ucdavis.edu"):
        pages.append(st.Page("pages/CAP_001.py", title="CAP_001", icon="🌳"))
        pages.append(st.Page("pages/CAP_002.py", title="CAP_002", icon="🌳"))

    if email in ["crpetrosian@ucdavis.edu"]:
        pages.append(st.Page("pages/OAK_001.py", title="OAK_001", icon="🍇"))
        pages.append(st.Page("pages/WIN_001.py", title="WIN_001", icon="🌳"))

    return pages

pg = st.navigation(get_authorized_pages(), position="sidebar", expanded=True)
pg.run()
import streamlit as st
 ## , position = "hidden" to hide nav bar

# Define pages and who can access them
def get_authorized_pages():
    user = st.user

    if not user.is_logged_in:
        return [st.Page("login.py", title="Login")]

    email = user.email

    pages = []

    # Everyone authenticated gets these
    pages.append(st.Page("homepage.py", title="Home", icon="🏠"))

    # Company domain gets analytics
    if email.endswith("@ucdavis.edu"):
        pages.append(st.Page("pages/CAP_002.py", title="CAP_002", icon="📊"))

    # Only specific admins
    if email in ["crpetrosian@ucdavis.edu"]:
        pages.append(st.Page("pages/WIN_001.py", title="WIN_001", icon="⚙️"))

    return pages


pg = st.navigation(get_authorized_pages())
pg.run()

import streamlit as st

origin = "streamlit"

st.set_page_config(initial_sidebar_state="expanded")
admin_domains = ["@ucdavis.edu", "@usda.gov", "kyleknipper7@gmail.com"]

def get_authorized_pages():
    try:
      user = st.user
    except Exception:
        return [st.Page("pages/login.py", title="Login")]
    if not user.is_logged_in:
        return [st.Page("pages/login.py", title="Login")]

    email = user.email
    pages = []

    pages.append(st.Page("pages/homepage.py", title="Home", icon="🏠"))

    if any(email.endswith(domain) for domain in admin_domains):
        pages.append(st.Page("pages/CAP_001.py", title="Capay - Independence", icon="🌳"))
        pages.append(st.Page("pages/CAP_002.py", title="Capay - Nonpareil", icon="🌳"))
        pages.append(st.Page("pages/OAK_001.py", title="OAK_001", icon="🍇"))
        pages.append(st.Page("pages/WIN_001.py", title="WIN_001", icon="🌳"))

    elif any(email.endswith(domain) for domain in st.secrets["emails"]["capay"]):
        pages.append(st.Page("pages/CAP_001.py", title="Capay - Independence", icon="🌳"))
        pages.append(st.Page("pages/CAP_002.py", title="Capay - Nonpareil", icon="🌳"))

    return pages


if origin == "streamlit":
  pg = st.navigation(get_authorized_pages(), position="sidebar", expanded=True)
else:
  pg = st.navigation([st.Page("pages/homepage.py"), st.Page("pages/CAP_001.py", title = "Capay - Independence"), st.Page("pages/CAP_002.py", title = "Capay - Nonpareil")])
pg.run()
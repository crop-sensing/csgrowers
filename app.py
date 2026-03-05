import streamlit as st

pg = st.navigation([st.Page("homepage.py"), st.Page("Capay_002.py")], position = "hidden") ## , position = "hidden" to hide nav bar
pg.run()
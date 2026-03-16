import streamlit as st
st.set_page_config(layout = "wide", initial_sidebar_state = "expanded")
st.header(f"Hello! Welcome to CSGrowers! user here")
if st.button("Log out"):
    st.logout()
st.subheader("⬅️Your block(s) will appear in the sidebar on the left.⬅️")
st.write("")
st.subheader("General Information:")

faq, data_issues = st.tabs(["FAQ", "Known Issues"])

with faq.expander("Test"):
    st.write("Test")

with data_issues.container(border = True):
    st.write("OpenET: Recent data (last 120 days) is not final. CSGrowers refreshes its OpenET database every month.")
with data_issues.container(border = True):
    st.write("OpenET: Recent FrET data has duplicate values. Issue is resolved for data older than 120 days. OpenET is aware of the issue.")
with data_issues.container(border = True):
    st.write("CAP_001: Soil Sensors are down due to sliced wires. Since: 9/2025.")
with data_issues.container(border = True):
    st.write("CAP_001: Unstable tower connection. Since: 1/2025.")

st.subheader("Credits:")
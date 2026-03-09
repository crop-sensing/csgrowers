import streamlit as st
st.write("Homepage")

if not st.user.is_logged_in:
    st.session_state.redirect_page = None  # home has no redirect needed
    st.button("Log in with Google", on_click=st.login)
    st.stop()

# After login, check if we need to redirect
if st.session_state.get("redirect_page"):
    page = st.session_state.redirect_page
    del st.session_state.redirect_page
    st.switch_page(f"pages/{page}.py")
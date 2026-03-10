import streamlit as st

st.title("Welcome")
st.write("Please log in to continue.")

if st.button("Log in with Google"):
    st.login()
import streamlit as st
st.set_page_config(layout = "wide", initial_sidebar_state = "expanded")
# st.header(f"Hello! Welcome to CSGrowers, {st.user.name}!")
st.write("")
if st.button("Log Out"):
    st.logout()
st.sidebar.subheader("Use the navigational sidebar to select your desired site.")
st.write("")
st.subheader("General Information:")

faq, data_issues = st.tabs(["FAQ", "Known Issues"])

faq_content = {
    "Why can I not see data from today?": "Our data updates at about 9:30am PT daily, due to UCD restriction, data updates can potentially lag, especially during the weekend.",
    "How far back does your data go?": "As of March 2026, the sites that are a part of our pilot project have towers that were set up in the summer of 2025. August 1st was about the time that all towers were online and had their intitial issues resolved. OpenET and CIMIS have an older database, but we only display data from these resources for days correspond with tower data."
}

for question, answer in faq_content.items():
    with faq.expander(question):
        st.write(answer)

with data_issues.container(border = True):
    st.write("**OpenET**: Recent data (last 120 days) is not final. CSGrowers refreshes its OpenET database every month. **[Issue Posted 3/13/2026]**")
with data_issues.container(border = True):
    st.write("**OpenET**: Recent FrET data has duplicate values. Issue is resolved for data older than 120 days. OpenET is aware of the issue. **[Issue Posted 3/13/2026]**")
with data_issues.container(border = True):
    st.write("**CAP_001**: New FLORAPULSE and Soil Sensors have been installed on 4/7/2026, data from these sensors before this date may not be accurate or complete. **[Issue Updated 4/9/2026]**")
with data_issues.container(border = True):
    st.write("**CAP_001**: Unstable tower connection between 1/2026 - 4/2026, data during this period may have gaps. **[Issue Updated 4/9/2026]**")
with data_issues.container(border = True):
    st.write("**Bug**: Irrigation upload via CSV temporarily disabled after of overhaul of soil moisture depletion system. A more user friendly irrigation information sharing system coming soon. **[Issue Posted 4/9/2026]**")

st.subheader("Resources:")
st.write("""
         - For more information on our data and how this app works check out our GitHub [here](https://github.com/crop-sensing/csgrowers).
         
         - Currently a bug reporting system is a work in progress. If you have any issues, direct your message to Audrey (crpetrosian@ucdavis.edu) with the subject line 'CSGrowers Bug Report'. 
         
         - If you still have questions after reading the tutorial and readme you may email Audrey (same email).""")

st.subheader("Credits:")
st.write("""
- This app and repository was created and is managed by Audrey Petrosian.

- Consultation on content and science provided by Nicolas Bambach (PhD) and Kyle Knipper (PhD).

- The towers were set-up and are monitored primarily by Sebastian Castro-Bustamante (MSc) and Karem Meza Capcha (PhD). Special thanks to our technicians (Peter Tolentino, Madeline Do, Tessa Guentensperger, and Carlos Perez) for all their work in and out of the field to help make projects like this possible.

- Refernce ET provided by the California Irrigation Management Information System (CIMIS) a part of the California Department of Water Resoures, CIMIS can be accessed [here](https://cimis.water.ca.gov/Default.aspx).

- Satelitte ET (ETa) and Fractional ET (FrET) are provided by OpenET, based on it's paper:
>Melton, F., et al., 2021. OpenET: Filling a Critical Data Gap in Water Management for the Western United States. Journal of the American Water Resources Association, 2021 Nov 2. doi:10.1111/1752-1688.12956

- Special thanks to Mina Swintek for feedback on content, user interface, and bug testing.""")
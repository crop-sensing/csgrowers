import streamlit as st
import json
st.set_page_config(layout = "wide", initial_sidebar_state = "expanded")
st.header(f"Hello! Welcome to CSGrowers, {st.user.name}!")
st.write("")
if st.button("Log Out"):
    st.logout()

email = st.user.email
# email = "cpetrosi"

admin_emails = ["@ucdavis.edu", "@usda.gov", "kyleknipper7@gmail.com"]

st.sidebar.subheader("Use the navigational sidebar to select your desired site.")
st.write("")
st.subheader("General Information:")

faq, data_issues = st.tabs(["FAQ", "Known Issues"])

faq_content = {
    "What is the latency of your data?": """Our app updates itself throughout the day. Tower data is collected locally daily and is added within an hour of collection. Evapotranspiration data has a latency of a day.""",
    "How far back does your data go?": "As of March 2026, the sites that are a part of our pilot project have towers that were set up in the summer of 2025. August 1st was about the time that all towers were online and had their intitial issues resolved. OpenET and CIMIS have an older database, but we only display data from these resources for days correspond with tower data.",
    "Can I download the data I see on your website?": "Yes! If you hover over your desired table, click the down arrow to download the current table.",
    "Who can view the pages for my site?": "CSGrowers team members (certain Crop Sensing Group members, including UC Davis and USDA employees) and you, the grower, are currently the only ones who have access to your orchard's page(s), data, and known issues specific to your site. We are using Google's OAuth service to whitelist specific users to allow them to access this app and further permissions are setup on the backend so growers' pages stay private from each other."
}

for question, answer in faq_content.items():
    with faq.expander(question):
        st.write(answer)

with data_issues.container(border = True):
    st.write("**OpenET**: Recent data (last 120 days) is not final. CSGrowers refreshes its OpenET backlog daily. **[Issue Posted 3/13/2026]**")
with data_issues.container(border = True):
    st.write("**OpenET**: Recent FrET data show repeat values. Issue is often resolved within a week or so, can take up to 120 days to resolve. OpenET is aware of the issue. **[Issue Updated 6/23/2026]**")
with data_issues.container(border = True):
    st.write("**All Towers**: There is a data gap of of 1-2 weeks in early April 2026. This has produced some visual bugs in some graphs during this time. **[Issue Updated 6/23/2026]**")
if email.endswith("@capayfarms.com") or any(email.endswith(domain) for domain in admin_emails):
  with data_issues.container(border = True):
      st.write("**CAP_IND**: New FLORAPULSE and Soil Sensors have been installed on 4/7/2026, data from these sensors before this date may not be accurate or complete. **[Issue Updated 4/9/2026]**")
  with data_issues.container(border = True):
      st.write("**CAP_IND**: Water Potential data before April 2026 has been removed from Capay Independence due to low data quality. **[Issue Added 5/6/26]**")

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
         
- Project funded by the Almond Board of California, ID #WATER16-Bambach

- Refernce ET provided by the California Irrigation Management Information System (CIMIS) a part of the California Department of Water Resoures, CIMIS can be accessed [here](https://cimis.water.ca.gov/Default.aspx).

- Satelitte ET (ETa) and Fractional ET (FrET) are provided by OpenET, based on it's paper:
>Melton, F., et al., 2021. OpenET: Filling a Critical Data Gap in Water Management for the Western United States. Journal of the American Water Resources Association, 2021 Nov 2. doi:10.1111/1752-1688.12956
         
- Precipitation data collected from the California Department of Water Resources via the California Data Exchange Center.

- Special thanks to Mina Swintek for feedback on content, user interface, and bug testing.""")

badge_color = {
    "feature": "green",
    "bug fix": "red",
    "improvement": "blue"
}

with open("changelog.json", "r") as f:
    changelog = json.load(f)

st.subheader("Changelog:")

for i, release in enumerate(changelog):
    with st.expander(f"v{release['version']} — {release['date']}"):
        for change in release["changes"]:
            col1, col2 = st.columns([1, 6])
            with col1:
                st.badge(change["type"], color=badge_color[change["type"]])
            with col2:
                st.markdown(change["text"])
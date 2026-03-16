import folium as fl
from streamlit_folium import st_folium
import streamlit as st
import pandas as pd
import plotly
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import json
from supabase import create_client
from io import StringIO

## Must be first line
st.set_page_config(layout = "wide")
warnings.filterwarnings("ignore")
st.title("CSGrowers - Capay_002")

origin = "local" ## streamlit or local

site = "CAP_002"
curr_page = "CAP_002"

years_active = ["2025", "2026"]

if origin == "streamlit":
  if "current_page" not in st.session_state:
          st.session_state.current_page = curr_page
  
  ## Uses Google OAuth to verify user email, details in hidden toml file
  if not st.user.is_logged_in:
      st.session_state.redirect_page = curr_page
      st.button("Log in with Google", on_click=st.login)
      st.stop()
  
  email = st.user.email

  if st.session_state.get("current_page") != curr_page:
    # Page has changed, clear cache
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.current_page = curr_page
else:
  email = "crpetrosian@ucdavis.edu"

## Import supabase credentials
client = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["key"]
)

## Does most API pulls in a single function, and caches it
@st.cache_data
def data_set_up():
    ## ET Import
    res = client.table("static_dataframes").select("data").eq("dataset_name", "et_both").eq("site", site).execute()
    et_both = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    et_both["date"] = pd.to_datetime(et_both["date"], unit = "ms")
    
    ## DL General Import
    res = client.table("static_dataframes").select("data").eq("dataset_name", "dl_gen").eq("site", site).execute()
    dl_gen = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    dl_gen["TIMESTAMP"] = pd.to_datetime(dl_gen["TIMESTAMP"], unit = "ms")

    ## DL Water Potential Import
    res = client.table("water_potential").select("data").eq("dataset_name", "wp").eq("site", site).eq("username", "ALL").execute()
    dl_flo = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    dl_flo["TIMESTAMP"] = pd.to_datetime(dl_gen["TIMESTAMP"], unit = "ms")
    
    try:
      res = client.table("water_potential").select("data").eq("dataset_name", "pb").eq("site", site).eq("username", email).execute()
      pb = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    except:
      res = client.table("water_potential").select("data").eq("dataset_name", "pb").eq("site", site).eq("username", "default").execute()
      pb = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    pb["TIMESTAMP"] = pd.to_datetime(pb["TIMESTAMP"], unit = "ms")

    dl_flo = dl_flo.merge(pb, on = "TIMESTAMP", how = "outer")
    
    ## DL Soil
    res = client.table("static_dataframes").select("data").eq("dataset_name", "dl_soil_all").eq("site", site).execute()
    dl_soil_all = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    dl_soil_all["TIMESTAMP"] = pd.to_datetime(dl_soil_all["TIMESTAMP"], unit = "ms")
    depths = ["5cm", "10cm", "20cm", "30cm", "40cm", "50cm", "60cm", "75cm", "100cm"]

    
    irr_dict = dict()
    
    for year in years_active:
      try:
          ## Retrieve Saved Irrigation
          res = client.table("irrigation").select("data").eq("dataset_name", "saved_irr").eq("site", site).eq("username", email).eq("irr_year", int(year)).execute()
          user_irr = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
          user_irr["Start Date"] = pd.to_datetime(user_irr["Start Date"], unit = "ms")
          user_irr["End Date"] = pd.to_datetime(user_irr["End Date"], unit = "ms")
          irr_dict[f"user_irr_{year}"] = user_irr
    
          ## Retrieve Template
          res = client.table("irrigation").select("data").eq("dataset_name", "template").eq("site", "ALL").eq("username", "ALL").eq("irr_year", int(year)).execute()
          template_irr = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
          template_irr["Start Date"] = pd.to_datetime(template_irr["Start Date"])
          template_irr["End Date"] = pd.to_datetime(template_irr["End Date"])
          irr_dict[f"template_{year}"] = template_irr

      except IndexError:
          ## Retrieve Template
          res = client.table("irrigation").select("data").eq("dataset_name", "template").eq("site", "ALL").eq("username", "ALL").eq("irr_year", int(year)).execute()
          template_irr = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
          template_irr["Start Date"] = pd.to_datetime(template_irr["Start Date"])
          template_irr["End Date"] = pd.to_datetime(template_irr["End Date"])
          irr_dict[f"user_irr_{year}"] = template_irr
          irr_dict[f"template_{year}"] = template_irr

    ## Retrieve Crop Coefficient
    try:
      res = client.table("headers").select("value").eq("data_type", "crop_coeff").eq("site", site).eq("username", email).execute()
      sql_crop_coeff = str(res.data[0]["value"])
    except:
      sql_crop_coeff = 1
    
    ## Gets last week, filters et data
    today = pd.Timestamp.today().normalize()
    days_since_sunday = (today.weekday() + 1) % 7 
    last_sunday = today - pd.Timedelta(days=days_since_sunday)
    start_date = last_sunday - pd.Timedelta(days=6)
    et_last_week = et_both[(et_both['date'] >= start_date) & (et_both['date'] < last_sunday)]

    return et_both, dl_gen, dl_soil_all, dl_flo, irr_dict, depths, et_last_week, sql_crop_coeff, ""

et_both, dl_gen, dl_soil_all, dl_flo, irr_dict, depths, et_last_week, sql_crop_coeff, default_val = data_set_up()

## Checks column names, time values, and amount of rows in a data frame.
## Returns specific error codes if user df fails test.
def user_upload_check(df, year_input, cols = ["Start Date", "End Date", "Irrigation"]):
  year_input = str(year_input)
  checks = 1
  codes = []
  cols = set(cols)
  if (set(df.columns) == cols) == False:
    checks -= 1
    codes.append("Your columns do not match the template.")
  try:
    df["Irrigation"] = df["Irrigation"].apply(pd.to_numeric)
  except:
    codes.append("There is an invalid data type in your dataset.")
    checks -= 1
  try:
    temp_time = pd.to_datetime(df["Start Date"])
    trues = [time.strftime("%Y") == year_input for time in temp_time]
    if sum(trues) < len(df) - 1:
      checks -= 1
      codes.append("More than one value in your Start Date column falls outside of 2025.")
  except:
    checks -= 1
    codes.append("One or more values in your Start Date column is invalid.")
  try:
    temp_time = pd.to_datetime(df["End Date"])
    trues = [time.strftime("%Y") == year_input for time in temp_time]
    if sum(trues) < len(df):
      checks -= 1
      codes.append("At least one value in your End Date column falls outside of 2025.")
  except:
    checks -= 1
    codes.append("At least one value in your End Date column is invalid")
  # max_bool = [0 <= i < 200 for i in df.loc[:, "Irrigation"].apply(max)]
  # min_bool = [0 <= i < 200 for i in df.loc[:, "Irrigation"].apply(min)]
  # if (sum(max_bool) != len(df.columns) - 1) or (sum(min_bool) != len(df.columns) - 1):
  #   checks -= 1
  #   codes.append("One of your values is below 0 or above 200.")
  if checks == 1:
    return True, codes
  else:
    return False, codes

## Uploads irrigation data to proper database
def supabase_upload(df, year, site = site, username = email):
    json_data = json.loads(df.to_json())
    client.table("irrigation").upsert({
          "dataset_name": "saved_irr",
          "data": json_data,
          "site": site,
          "username": username,
          "irr_year": year
    }, on_conflict="dataset_name,site,username,irr_year").execute()
    st.cache_resource.clear()
    st.rerun()
    return None

## Uploads pressure bomb data to proper place
def pressure_bomb_upload(df):
    ## A cautious step to ensure we have the most up to date water potential timestamp
    res = client.table("water_potential").select("data").eq("dataset_name", "wp").eq("site", site).eq("username", "ALL").execute()
    dl_flo = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    dl_flo["TIMESTAMP"] = pd.to_datetime(dl_flo["TIMESTAMP"], unit = "ms")
    df = df[["TIMESTAMP", "Pressure_Bomb"]]
    temp = dl_flo.merge(df, on = "TIMESTAMP", how = "outer")
    temp = temp[["TIMESTAMP", "Pressure_Bomb"]]
    json_data = json.loads(temp.to_json())
    client.table("water_potential").upsert({
          "dataset_name": "pb",
          "data": json_data,
          "site": site,
          "username": email
          }, on_conflict = "dataset_name,site,username").execute()
    st.cache_resource.clear()
    st.rerun()
    return None

## Does a check on validity of data, WIP
def pb_check(wp):
  try:
    wp["Pressure_Bomb"] = wp["Pressure_Bomb"].astype(float)
  except:
    return "Fail"
  return wp_tab.success("Success")
col1, col2, col3, col4, col5 = st.columns(5)

## Imports mapbox credentials
token = st.secrets["mapbox"]["token"]
tileurl = 'https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}@2x.png?access_token=' + str(token)

## Creates small map and marker of current site (CAP_002 in this case)
with col1.container(border = True, height = 290):
  m = fl.Map()
  m = fl.Map(location=[float(st.secrets[site]["center_lat"]), float(st.secrets[site]["center_long"])], zoom_start = 13, tiles = tileurl, attr = "Mapbox", scrollWheelZoom = False, height = 290)
  fl.Marker(location = [float(st.secrets[site]["true_lat"]), float(st.secrets[site]["true_long"])], popup = "CAP_002").add_to(m)
  st_folium(m, height = 230, returned_objects=[])

## Either saves crop coeff to supabase or returns empty WIP
def crop_coeff_check(cc):
  try:
    cc = float(cc)
  except:
    return None
  client.table("headers").upsert({
          "data_type": "crop_coeff",
          "value": cc,
          "site": site,
          "username": email
          }, on_conflict = "data_type,site,username").execute()
  return "success"

with col2.container(border = True, height = 290):
  eto_mean = et_last_week["eto"].mean()
  st.markdown(f"""
              #### ETo (Last 7 Days): {eto_mean:.3f}
              """
              )
  
  #### Crop Coeffecient:
  ## Loads last user input, allows user to reset crop coeff
  if "crop_coeff" not in st.session_state:
    st.session_state["crop_coeff"] = sql_crop_coeff
  button_col1, button_col2 = st.columns(2)
  if button_col1.button("Reset Value", width = "stretch"):
    st.session_state["crop_coeff"] = "1"
  if button_col2.button("Save Value", width = "stretch"):
    if crop_coeff_check(st.session_state["user_cc"]) == "success":
      st.success("Save Successful")
  cc = st.text_input("Crop Coefficient:", value = st.session_state["crop_coeff"])
  ## Stores current value in text input to make saving possible
  st.session_state["user_cc"] = cc
  ## Gives user message automatically if value is invalid
  try:
    cc = float(cc)
  except:
    st.toast("Input must be a number.")
    cc = 1
  st.markdown(f"""
              #### Adjusted ETo: **{eto_mean * cc:.3f}**""")

## Static text display summary ET info
with col3.container(border = True, height = 137):
  eta_mean = et_last_week["eta"].mean()
  st.markdown(f"""
           #### ETa (Last 7 Days):
           #### {eta_mean:.3f}
           """)

with col3.container(border = True, height = 138):
  fret_mean = et_last_week["etof"].mean()
  st.markdown(f"""
           #### FrET (Last 7 Days):
           #### {fret_mean:.3f}
           """)

## Function that checks validity of user SWC input before allowing a save, currently WIP
def target_check(val):
  val = str(val)
  if val == "":
    return ["Fail", "Save Failed - Input is empty"]
  if val[-1] == "%":
    val = val[0:-1]
  try:
    val = float(val)
  except:
    return ["Fail","Save Failed - Input is not numeric"]
  if (val < 0) or (val > 100):
    return ["Fail", "Save Failed - Input smaller than 0 or larger than 100"]
  else:
    client.table("headers").upsert({
          ## id,
          "data_type": "soil_target",
          "value": val,
          "site": site,
          "username": email
          }, on_conflict="data_type,site,username").execute()
    return ["Success", "Save Successful"]

with col4.container(border = True, height = 290):
  st.markdown("""
           #### Soil Moisture Depletion:
           #### Placeholder
           """)
  ## Similar to Crop Coeff logic, but allows user to manually load data instead of automatic
  soil_button1, soil_button2 = st.columns(2)
  if soil_button1.button("Load Target", width = "stretch"):
    try:
      res = client.table("headers").select("value").eq("data_type", "soil_target").eq("site", site).eq("username", email).execute()
      default_val = str(res.data[0]["value"])+"%"
    except:
      st.error("No target saved.")
      default_val = ""
  else:
    default_val = ""
  if soil_button2.button("Save Target", width = "stretch"):
    msg = target_check(st.session_state["user_soil"])
    if msg[0] == "Fail":
      st.error(msg[1])
    else:
      st.success(msg[1])
  soil_input = st.text_input("Soil Moisture Target:", placeholder = "Ex. 15%", value = default_val)
  st.session_state["user_soil"] = str(soil_input)
## Tutorial/Credits/Glossary Set Up
with col5.container(border = True, height = 290):
  @st.dialog("Tutorial", width = "large")
  def show_tutorial():
      st.subheader("Introduction")
      st.write("The CSGrowers App is a pilot program developed to give growers a dashboard to view nearly live data and the ability to save irrigation data, pressure bomb data, and custimizations to data and data visualizatoins.")
      st.write("The following tutorial will give you the basics on how to interface with this app. For more information on our methods of gathering, maniupulating, and storing data visit the [GitHub Repository](https://github.com/crop-sensing/csgrowers)" \
      " for CSGrowers.")
      st.subheader("Overview")
      st.write("The CSGrowers dashboard consists of three main components: data summary/target setting, data tables, and data visualizations. " \
      "The targets and inputs you give in the first two components affect the data tables and visualizations. " \
      "Along with these three main parts, we also allow you to select the date range of data you would like to view. " \
      "All together, these can give you a versatile experience to view and manipulate your data.")
      st.subheader("Data Summary / Target Setting")
      st.write("At the top of the page you will see five columns of containers: a map, ETo data/crop coefficient customizer, ETa/FrET, Soil Mostiure Depletion/Target setting, and the box that contains general information. "\
               "The map displays a marker of the where the tower is at the site you are currently viewing. The ETo box shows summary data from the last seven days of ETo data from CIMIS (see credits for more information), " \
               "an input for a custom crop coefficient if you choose (or you can use our standard value), and there is an updated ETo value based on this coefficient. "\
               "This coefficient will also update the ETo values you see on the rest of the app. If you choose to use a custom crop coefficient, you can save it to the cloud and it will be loaded automatically next time you sign into the app. " \
               "The ETa/FrET boxes work indentically to the ETo box, but they display ETa and FrET from OpenET (for more information see glossary). "\
               "The Soil Moisture Depletion box functions similarly to the ETo box, where there is the soil depletion for the last week is displayed. "\
               "You can set, save, and load a custom soil mositure target with the buttons above the input box.")
  @st.dialog("Credits")
  def show_credits():
      st.write("Built by: **Audrey Petrosian**")
      st.write("Support: **Nicolas Bambach**, **Kyle Knipper**, **Mina Swintek**")
      st.subheader("Data:")
      st.write("Reference ET (ETo): [CIMIS](https://cimis.water.ca.gov/)")
      st.write("ETa/FrET: [OpenET](https://etdata.org/)")
      st.write("Tower Data: **Sebastian Castro-Bustamante** and **Karem Meza Capcha**")
  @st.dialog("Glossary")
  def show_glossary():
      st.write("**ET**: Evapotranspiration")
      st.write("**ETa**: ensemble ET, gathered through satelitte via OpenET")
      st.write("**ETo**: reference ET, via CIMIS")
      st.write("**FrET**: fractional ET, a ratio of ETo/ETa, via OpenET")
      st.write("**SWC**: Soil Water Content, via SAWS Towers")
      st.write("**VPD**: Vapor Pressure Deficit, via SAWS Towers")
      st.write("**WP**: Water Potential, gatered via SAWS Towers")

  ## Shows tutorial/credits on click
  st.write("#### CSGrowers Information:")
  if st.button("Tutorial", use_container_width=True):
    show_tutorial()
  if st.button("Credits", use_container_width=True):
    show_credits()
  if st.button("Glossary", use_container_width=True):
    show_glossary()
  
date1, date2 = st.columns(2)
date_start = date1.date_input("Start Date", value = datetime.date(int(datetime.date.today().strftime("%Y")), 1, 1))
date_end = date2.date_input("End Date", value = datetime.date.today())

## Allows user to select dates to later be used to filter data
# date_range = st.date_input("Enter Date Range", value = (datetime.date(2026, 1, 1), datetime.date(2026, 2, 28)),
#                            format = "YYYY-MM-DD", min_value=datetime.date(2025, 8, 1), max_value=datetime.date.today(),
#                            help = "Applies a date range filter to all data except irrigation. We recommend you use the built-in UI to select the dates.")

## Function that does the filtering
def time_restrict(date_start = date_start, date_end = date_end,
                  et_both = et_both, dl_soil_all = dl_soil_all, dl_flo = dl_flo, dl_gen = dl_gen):
  start = pd.to_datetime(date_start)
  end = pd.to_datetime(date_end)
  et_both = et_both[(et_both["date"] >= start) & (et_both["date"] <= end)]
  dl_soil_all = dl_soil_all[(dl_soil_all["TIMESTAMP"] >= start) & (dl_soil_all["TIMESTAMP"] <= end)]
  dl_flo = dl_flo[(dl_flo["TIMESTAMP"] >= start) & (dl_flo["TIMESTAMP"] <= end)]
  dl_gen = dl_gen[(dl_gen["TIMESTAMP"] >= start) & (dl_gen["TIMESTAMP"] <= end)]
  return et_both, dl_soil_all, dl_flo, dl_gen

et_both, dl_soil_all, dl_flo, dl_gen = time_restrict()

## Initialize data table tabs
irr_tab, et_tab, soil_tab, wp_tab, weather_tab = st.tabs(["Irrigation", "Evapotranspiration", "Soil Moisture", "Water Potential", "Weather"])

irr_year = irr_tab.radio("Year:", years_active, horizontal = True)
## Irrigation data editor/button initilization
user_file = None
app_df = irr_tab.data_editor(irr_dict[f"user_irr_{irr_year}"],
                             column_config = {
                               "Start Date": st.column_config.DateColumn(),
                               "End Date": st.column_config.DateColumn(),
                               "Irrigation": st.column_config.NumberColumn(min_value = 0, max_value = 100)
                             },
                             hide_index = True)
popup = irr_tab.popover("Upload Data")
popup.download_button(label = "Download Template File (Selected Year)", data = irr_dict[f"template_{irr_year}"].to_csv().encode("utf-8"), file_name = f"csgrowers_irrigation_template_{irr_year}.csv")
user_file = popup.file_uploader("Upload Data", type = "csv")

## Only triggers if user uploads a csv
## Runs a check on upload, uploads to Box if successful
if user_file is not None:
  if st.session_state.get("last_uploaded_file") != user_file.name:
    st.session_state["last_uploaded_file"] = user_file.name
    user_df = pd.read_csv(user_file, index_col = [0])
    file_check, codes = user_upload_check(user_df, year_input = irr_year)
    if file_check == True:
      irr_tab.success('File upload successful')
      supabase_upload(user_df, year = irr_year)
    else:
      irr_tab.error("ERROR: " +  " ERROR: ".join(codes))   

## Allows user to download and save current data frame, will only save if DF passes check.
down_popup = irr_tab.popover("Download & Save")
if down_popup.download_button("Download & Save (this will overwrite your file in the cloud)", data = app_df.to_csv().encode('utf-8'), file_name = 'user_water_input.csv'):
  checkdown, codes = user_upload_check(app_df, year_input = irr_year)
  if checkdown == True:
    supabase_upload(app_df, year = irr_year)
    irr_tab.success('File save successful')
  else:
    irr_tab.error("ERROR: " +  " ERROR: ".join(codes) + " --- file did not save to cloud.")

## Allows user to save current data frame, will only save if DF passes check.
if down_popup.button("Save (this will overwrite your file in the cloud)"):
  checkdown, codes = user_upload_check(app_df, year_input = irr_year)
  if checkdown == True:
    supabase_upload(app_df, year = irr_year)
    irr_tab.success('File save successful')
  else:
    irr_tab.error("ERROR: " +  " ERROR: ".join(codes) + " --- file did not save to cloud.")

## Displays ET data
et_both = et_both[["date", "eto", "eta", "etof"]]
et_both["eto"] = et_both["eto"]*cc
et_tab.dataframe(et_both.rename(columns = {"date": "Date", "eto": "ETo", "eta": "ETa", "etof": "FrET"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

## Rearrange and show soil data
soil_cols = list(dl_soil_all.columns)
soil_cols = soil_cols[-1::] + soil_cols[0:-1]
dl_soil_all = dl_soil_all[soil_cols]
soil_tab.dataframe(dl_soil_all.rename(columns = {"TIMESTAMP": "Date"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

## Water Potential Data Frame that uses earlier functions to check data upon save.
app_wp = wp_tab.data_editor(dl_flo.rename(columns = {"TIMESTAMP": "Date"}), disabled = ["Date", "WP"], hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})
if wp_tab.button("Save Pressure Bomb Data"):
  if pb_check(app_wp) == "Fail":
    wp_tab.error("Upload Failed Check Inputs")
  else:
    pressure_bomb_upload(app_wp.rename(columns = {"Date": "TIMESTAMP"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})
    wp_tab.success("Upload Successful!")

## Weather data is rearranged and displayed
dl_gen = dl_gen[["TIMESTAMP", "VPD", "Air_Temperature (C)", "Air_Temperature (F)", "Relative_Humidity (%)"]]
weather_tab.dataframe(dl_gen.rename(columns = {"TIMESTAMP": "Date"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

## Irrigation Visualization
def irr_vis(irr = app_df):
  irr_plot = go.Figure()

  irr_plot.add_trace(go.Bar(x = pd.to_datetime(irr["End Date"]), y = irr["Irrigation"], name = "Irrigation (in)", showlegend = True))
  irr_plot.update_layout(
    margin = dict(t = 0, b = 25, r = 150),
    yaxis_title = "Irrigation Applied (in)"
  )
  return irr_plot

st.subheader("Applied Irrigation")
st.plotly_chart(irr_vis())

## ET Visualization
def et_vis(et = et_both):
  et_plot = make_subplots(specs=[[{"secondary_y": True}]])
  
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["eto"], name = "ETo via CIMIS"), secondary_y=False)
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["eta"], name = "ETa via OpenET"), secondary_y=False)
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["etof"], name = "FrET via OpenET"), secondary_y=True)
  et_plot.update_layout(
    margin = dict(t = 0, b = 25),
    hovermode = "x unified"
  )
  et_plot.update_yaxes(title_text = "ETa & ETo (mm)", secondary_y=False)
  et_plot.update_yaxes(title_text = "FrET (mm)", secondary_y=True)
  return et_plot

st.subheader("Evapotranspiration")
st.plotly_chart(et_vis())

## Soil Heat Map Visualization along with depth filtering
st.subheader("Soil Moisture Content")
heat_select = st.selectbox("Soil Moisture Depth:", ["All", "Near Surface", "Mid Surface", "Deep Surface"])
def heat_map(dl_soil_all = dl_soil_all, filter = heat_select, depths = depths):
  if filter == "All":
    depths = depths
  elif filter == "Near Surface":
    depths = depths[0:3]
  elif filter == "Mid Surface":
    depths = depths[3:6]
  else:
    depths = depths[6:]
  depth_cols = [f"SWC_{d}" for d in depths]
  z = dl_soil_all[depth_cols].T.values
  heatmap = go.Figure(data=go.Heatmap(
      z = z,
      x = dl_soil_all["TIMESTAMP"],
      y = depth_cols,
      colorscale = "RdYlBu",
      colorbar = dict(title = "Soil Water Content"),
      hoverongaps = False
  ))
  ## Adds black vertical lines for each depth.
  for i, col in enumerate(depth_cols):
      heatmap.add_trace(go.Scatter(
          x = dl_soil_all["TIMESTAMP"],
          y = [col] * len(dl_soil_all),          
          mode = "lines",
          line = dict(color = "grey", width = 1),
          showlegend = False,
          hoverinfo = "skip"
      ))

  heatmap.update_layout(
    margin = dict(t = 0, b = 25),
    yaxis = dict(autorange = "reversed")
  )

  return heatmap


st.plotly_chart(heat_map())

## Water Potential visualization
def water_potential(wp = dl_flo, dl_gen = dl_gen):
  wp_plot = go.Figure()

  wp_plot.add_trace(go.Scatter(x = wp["TIMESTAMP"], y = wp["WP"], mode = "lines", name = "Observed"))
  wp_plot.add_trace(go.Scatter(x = dl_gen["TIMESTAMP"], y = ((dl_gen["VPD"]*-0.12)-0.41), mode = "lines", name = "Baseline"))
  wp_plot.add_trace(go.Scatter(x = wp["TIMESTAMP"], y = wp["Pressure_Bomb"], mode = "markers", name = "User Pressure Bomb"))

  wp_plot.update_layout(
    yaxis_title = "Water Potential (Bar)",
    hovermode = "x unified",
    margin = dict(t = 0)
  )

  return wp_plot

st.subheader("Water Potential")
st.plotly_chart(water_potential())

## Weather Plot
def weather_plot(dl_gen = dl_gen):
  weather = go.Figure()

  weather.add_trace(go.Scatter(x=dl_gen["TIMESTAMP"], y=dl_gen["Air_Temperature (F)"], mode="lines", name="Air Temperature (F)", line=dict(color="red")))
  # weather.add_trace(go.Scatter(x=dl_gen["TIMESTAMP"], y=dl_gen["Air_Temperature (C)"], mode="lines", name="Air Temperature (C)"))
  weather.add_trace(go.Scatter(x=dl_gen["TIMESTAMP"], y=dl_gen["Relative_Humidity (%)"], mode="lines", name="Relative Humidity (%)"))

  weather.update_layout(
    yaxis_title = "Value",
    hovermode = "x unified",
    margin = dict(t = 0)
  )
  return weather

st.subheader("Weather")
st.plotly_chart(weather_plot())


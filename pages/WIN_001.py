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
import numpy as np

## Must be first line
st.set_page_config(layout = "wide")
warnings.filterwarnings("ignore")
st.title("CSGrowers - Winters")

origin = "streamlit" ## streamlit or local

site = "WIN_001"
curr_page = "WIN_001"

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

    dl_flo = pd.merge(dl_flo, pb, on = "TIMESTAMP", how = "outer")
    
    ## DL Soil
    res = client.table("static_dataframes").select("data").eq("dataset_name", "dl_soil_all").eq("site", site).execute()
    dl_soil_all = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    dl_soil_all["TIMESTAMP"] = pd.to_datetime(dl_soil_all["TIMESTAMP"], unit = "ms")
    depths = ["5cm", "10cm", "20cm", "30cm", "40cm", "50cm", "60cm", "75cm", "100cm"]
    
    ## Irrigation
    irr_temp_new = pd.DataFrame()
    irr_temp_new["date"] = dl_gen["TIMESTAMP"]
    irr_temp_new["irr"] = 0
    irr_temp_new["precip"] = 0

    try:
      ## Retrieve Saved Irrigation
      res = client.table("irrigation").select("data").eq("dataset_name", "saved_irr").eq("site", site).eq("username", email).execute()
      user_irr = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
      user_irr["date"] = pd.to_datetime(user_irr["date"], unit = "ms")

    except IndexError:
      user_irr = irr_temp_new

    ## Retrieve Crop Coefficient
    try:
      res = client.table("headers").select("value").eq("data_type", "crop_coeff").eq("site", site).eq("username", email).execute()
      sql_crop_coeff = str(res.data[0]["value"][0])
    except:
      sql_crop_coeff = 1
    
    ## Retrieve Soil Panel
    try:
      res = client.table("headers").select("value").eq("data_type", "soil_panel").eq("site", site).eq("username", email).execute()
      sql_soil_panel = res.data[0]["value"]
    except:
      sql_soil_panel = ["0.29", "0.15", "0.45"]
    
    ## Gets last week, filters et data
    today = pd.Timestamp.today().normalize()
    days_since_sunday = (today.weekday() + 1) % 7 
    last_sunday = today - pd.Timedelta(days=days_since_sunday)
    start_date = last_sunday - pd.Timedelta(days=6)
    et_last_week = et_both[(et_both['date'] >= start_date) & (et_both['date'] < last_sunday)]

    return et_both, dl_gen, dl_soil_all, dl_flo, user_irr, irr_temp_new, depths, et_last_week, sql_crop_coeff, sql_soil_panel, ""

et_both, dl_gen, dl_soil_all, dl_flo, user_irr, template, depths, et_last_week, sql_crop_coeff, sql_soil_panel, default_val = data_set_up()

DEFAULTS = {
    "def_fc": 0.23,
    "def_wilt_p": 0.11,
    "def_mad": 0.45
}

## Checks column names, time values, and amount of rows in a data frame.
## Returns specific error codes if user df fails test.
def user_upload_check(df, cols = ["Date", "Irrigation", "Precipitation"]):
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
  if checks == 1:
    return True, codes
  else:
    return False, codes

## Uploads irrigation data to proper database
def supabase_upload(df, site = site, username = email, template = template):
    df_dates = template.set_index("date")
    df_data = df.set_index("Date")
    df_dates = df_dates.replace(0, pd.NA)
    df_merged = df_dates.combine_first(df_data)
    df_merged = df_merged.fillna(0).reset_index()
    
    df_merged = df_merged[["date", "Irrigation", "Precipitation"]].rename(columns={"Irrigation": "irr", "Precipitation": "precip"})
    json_data = json.loads(df_merged.to_json())
    client.table("irrigation").upsert({
          "dataset_name": "saved_irr",
          "data": json_data,
          "site": site,
          "username": username,
    }, on_conflict="dataset_name,site,username").execute()
    st.cache_data.clear()
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
col1, col2, col3, col4 = st.columns([.22, .22, .22, .34])

SENSOR_DEPTHS_CM = [5, 10, 20, 40, 50, 60, 75, 100] 
LAYER_BOUNDS_MM  = [50, 100, 200, 400, 500, 600, 750, 1000] 

def layer_thickness_in_rz(rz_mm: float) -> np.ndarray:
    thick = np.zeros(len(SENSOR_DEPTHS_CM))
    for i in range(len(SENSOR_DEPTHS_CM)):
        top = LAYER_BOUNDS_MM[i]
        if top >= rz_mm:
            break
        bot = min(LAYER_BOUNDS_MM[i + 1], rz_mm)
        thick[i] = bot - top
    return thick


def compute_storage(df: pd.DataFrame, rz_mm: float) -> pd.Series:
    thick = layer_thickness_in_rz(rz_mm)
    swc_cols = [f"SWC_{d}cm" for d in SENSOR_DEPTHS_CM]
    storage = (df[swc_cols].values * thick).sum(axis=1)
    return pd.Series(storage, index=df.index, name="Storage_mm")


def water_balance(df: pd.DataFrame, fc: float, wp: float,
                  rz_cm: float, mad: float) -> pd.DataFrame:
    rz_mm  = rz_cm * 10
    taw_mm = (fc - wp) * rz_mm
    raw_mm = mad * taw_mm

    df = df.copy()
    df["Storage_mm"] = compute_storage(df, rz_mm)
    df["dStorage_mm"] = df["Storage_mm"].shift(1) - df["Storage_mm"]
    df["WB_depl_mm"]  = df["eta"] - df["irr"]*25.4 - df["precip"]*25.4

    # FAO-56 Dr tracking – initialise from first sensor reading
    dr_vals = []
    dr = max(0.0, fc * rz_mm - float(df["Storage_mm"].iloc[0]))
    for _, row in df.iterrows():
        dr = float(np.clip(dr + row["WB_depl_mm"], 0, taw_mm))
        dr_vals.append(dr)
    df["Dr_mm"]  = dr_vals
    df["TAW_mm"] = taw_mm
    df["RAW_mm"] = raw_mm
    return df

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
          "value": [cc],
          "site": site,
          "username": email
          }, on_conflict = "data_type,site,username").execute()
  return "success"

with col3.container(border = True, height = 290):
  eto = (et_last_week["eto"]/25.4)
  eto_sum = eto.sum()
  st.markdown(f"""
              #### ETo (Last 7 Days): {eto_sum:.3f} in.
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
  eto_cc = eto*cc
  eto_cc = eto_cc.sum()
  st.markdown(f"""
              #### ETc (Last 7 Days): **{eto_cc:.3f} in.**""")

## Static text display summary ET info
with col2.container(border = True, height = 137):
  eta_sum = et_last_week["eta"].sum()/25.4
  st.markdown(f"""
           #### ETa (Last 7 Days):
           #### {eta_sum:.3f} in.
           """)

with col2.container(border = True, height = 138):
  fret_mean = et_last_week["etof"].mean()/25.4
  st.markdown(f"""
           #### FrET (Last 7 Days):
           #### {fret_mean:.3f} in.
           """)

## Function that checks validity of user SWC input before allowing a save, currently WIP
def sm_upload(fc, wilt_p, mad):
  client.table("headers").upsert({
          ## id,
          "data_type": "soil_panel",
          "value": [fc, wilt_p, mad],
          "site": site,
          "username": email
        }, on_conflict="data_type,site,username").execute()
  
def status(dr_val, raw_mm):
    if dr_val > raw_mm:
      return "Irrigate"
    elif dr_val > raw_mm * 0.7:
      return "Monitor"
    return "Adequate"

with col4.container(border = True, height = 290):
  for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val
  @st.dialog("Soil Depletion Panel", width = "medium")
  def show_soil_popup(sql_soil_panel = sql_soil_panel):
    if st.button("Reset Values to Default"):
      for key, val in DEFAULTS.items():
          st.session_state[key] = val
    try:
      fc = st.number_input("Field Capacity θ_FC (m³/m³)", 0.10, 0.60, float(st.session_state["sm_input"]["fc"]), 0.01,
                          format="%.3f", key = "def_fc")
      wilt_p = st.number_input("Wilting Point θ_WP (m³/m³)", 0.02, 0.40, float(st.session_state["sm_input"]["wilt_p"]), 0.01,
                                          format="%.3f", key = "def_wilt_p")
      mad = st.slider("Depletion fraction p (MAD)", 0.30, 0.70, float(st.session_state["sm_input"]["mad"]), 0.05, key = "def_mad")
    except:
      fc = st.number_input("Field Capacity θ_FC (m³/m³)", 0.10, 0.60, float(sql_soil_panel[0]), 0.01,
                                          format="%.3f", key = "def_fc")
      wilt_p = st.number_input("Wilting Point θ_WP (m³/m³)", 0.02, 0.40, float(sql_soil_panel[1]), 0.01,
                                          format="%.3f", key = "def_wilt_p")
      mad = st.slider("Depletion fraction p (MAD)", 0.30, 0.70, float(sql_soil_panel[2]), 0.05, key = "def_mad")
    if st.button("Save"):
      st.session_state["sm_input"] = {
        "fc": fc,
        "wilt_p": wilt_p,
        "mad": mad
      }
      sm_upload(fc=fc, wilt_p=wilt_p, mad=mad)
      st.rerun()
    
  if st.button("Open Soil Moisture Panel", use_container_width=True):
    show_soil_popup()

  soil_calc_df = dl_soil_all.rename(columns = {"TIMESTAMP": "date"})
  soil_calc_df = pd.merge(soil_calc_df, et_both, on = ["date"])
  soil_calc_df = pd.merge(soil_calc_df, user_irr.rename(columns = {"Date": "date"}), on = ["date"])
  

  if "sm_input" in st.session_state:
    dr_val = []
    taw_mm = []
    raw_mm = []
    for depth_cm in [5, 10, 20, 40, 50, 60, 75, 100]:
      sm_result = st.session_state["sm_input"]
      wb_results = water_balance(soil_calc_df, fc = sm_result["fc"], wp = sm_result["wilt_p"], rz_cm = depth_cm, mad = sm_result["mad"])
      last = wb_results.iloc[-7:-1]
      dr_val.append(float(last["Dr_mm"].sum()/25.4))
      taw_mm.append(float(last["TAW_mm"].sum()/25.4))
      raw_mm.append(float(last["RAW_mm"].sum()/25.4))
  else:
    dr_val = []
    taw_mm = []
    raw_mm = []
    for depth_cm in [5, 10, 20, 40, 50, 60, 75, 100]:
      wb_results = water_balance(soil_calc_df, fc = 0.4, wp = 0.2, rz_cm = depth_cm, mad = 0.5)
      last = wb_results.iloc[-7:-1]
      dr_val.append(float(last["Dr_mm"].sum()/25.4))
      taw_mm.append(float(last["TAW_mm"].sum()/25.4))
      raw_mm.append(float(last["RAW_mm"].sum()/25.4))

  dr_color = "inverse" if np.mean(dr_val) > np.mean(raw_mm) else "normal"
  r1, r2, r3 = st.columns(3)
  r1.metric("RZD (in)", f"{np.mean(dr_val):.1f}", width = "content",
      delta=f"{'Above' if dr_val > raw_mm else 'Below'} RAW", delta_color=dr_color)
  r2.metric("TAW (in)", f"{np.mean(taw_mm):.1f}", width = "content")
  r3.metric("RAW / MAD (in)", f"{np.mean(raw_mm):.1f}", width = "content")
  status_emoji = {"Irrigate": "🔴", "Monitor": "🟡", "Adequate": "🟢"}
  st.metric("Latest Status", f"{status_emoji[status(np.mean(dr_val), np.mean(raw_mm))]} {status(np.mean(dr_val), np.mean(raw_mm))}")


  
date1, date2 = st.columns(2)
date_start = date1.date_input("Start Date", value = datetime.date(int(datetime.date.today().strftime("%Y")), 1, 1))
date_end = date2.date_input("End Date", value = datetime.date.today())

## Function that does the filtering
def time_restrict(date_start = date_start, date_end = date_end,
                  et_both = et_both, dl_soil_all = dl_soil_all, dl_flo = dl_flo, dl_gen = dl_gen, user_irr = user_irr):
  start = pd.to_datetime(date_start)
  end = pd.to_datetime(date_end)
  et_both = et_both[(et_both["date"] >= start) & (et_both["date"] <= end)]
  et_both["eto"] = et_both["eto"]/25.4
  et_both["eta"] = et_both["eta"]/25.4
  et_both["etof"] = et_both["etof"]/25.4
  dl_soil_all = dl_soil_all[(dl_soil_all["TIMESTAMP"] >= start) & (dl_soil_all["TIMESTAMP"] <= end)]
  dl_flo = dl_flo[(dl_flo["TIMESTAMP"] >= start) & (dl_flo["TIMESTAMP"] <= end)]
  dl_gen = dl_gen[(dl_gen["TIMESTAMP"] >= start) & (dl_gen["TIMESTAMP"] <= end)]
  user_irr = user_irr[(user_irr["date"] >= start) & (user_irr["date"] <= end)]
  return et_both, dl_soil_all, dl_flo, dl_gen, user_irr

et_both, dl_soil_all, dl_flo, dl_gen, user_irr = time_restrict()

## Initialize data table tabs
irr_tab, et_tab, soil_tab, wp_tab, weather_tab = st.tabs(["Irrigation", "Evapotranspiration", "Soil Moisture", "Water Potential", "Weather"])

# irr_year = irr_tab.radio("Year:", years_active, horizontal = True)
## Irrigation data editor/button initilization
user_file = None
app_df = irr_tab.data_editor(user_irr.rename(columns = {"date": "Date", "irr": "Irrigation", "precip": "Precipitation"}),
                             column_config = {
                               "Date": st.column_config.DateColumn(),
                               "Irrigation": st.column_config.NumberColumn(min_value = 0, max_value = 100),
                               "Precipitation": st.column_config.NumberColumn(min_value = 0, max_value = 10)
                             },
                             hide_index = True,
                             disabled = ["date"])
# popup = irr_tab.popover("Upload Data")
# popup.download_button(label = "Download Template File (Selected Year)", data = template.to_csv().encode("utf-8"), file_name = f"csgrowers_irrigation_template.csv")
# user_file = popup.file_uploader("Upload Data", type = "csv")

## Only triggers if user uploads a csv
## Runs a check on upload, uploads to Box if successful

## Temporarily disabled

# if user_file is not None:
#   if st.session_state.get("last_uploaded_file") != user_file.name:
#     st.session_state["last_uploaded_file"] = user_file.name
#     user_df = pd.read_csv(user_file, index_col = [0])
#     file_check, codes = user_upload_check(user_df)
#     if file_check == True:
#       irr_tab.success('File upload successful')
#       supabase_upload(user_df)
#     else:
#       irr_tab.error("ERROR: " +  " ERROR: ".join(codes))   

## Allows user to download and save current data frame, will only save if DF passes check.
down_popup = irr_tab.popover("Download & Save")
if down_popup.download_button("Download & Save", data = app_df.to_csv().encode('utf-8'), file_name = 'user_water_input.csv'):
  checkdown, codes = user_upload_check(app_df)
  if checkdown == True:
    supabase_upload(app_df)
    irr_tab.success('File save successful')
  else:
    irr_tab.error("ERROR: " +  " ERROR: ".join(codes) + " --- file did not save to cloud.")

## Allows user to save current data frame, will only save if DF passes check.
if down_popup.button("Save"):
  checkdown, codes = user_upload_check(app_df)
  if checkdown == True:
    supabase_upload(app_df)
    irr_tab.success('File save successful')
  else:
    irr_tab.error("ERROR: " +  " ERROR: ".join(codes) + " --- file did not save to cloud.")

## Displays ET data
et_both = et_both[["date", "eto", "eta", "etof"]]
et_both["eto"] = et_both["eto"]*cc
et_tab.dataframe(et_both.rename(columns = {"date": "Date", "eto": "ETc", "eta": "ETa", "etof": "FrET"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

## Rearrange and show soil data
soil_cols = list(dl_soil_all.columns)
soil_cols = soil_cols[-1::] + soil_cols[0:-1]
dl_soil_all = dl_soil_all[soil_cols]
soil_tab.dataframe(dl_soil_all.rename(columns = {"TIMESTAMP": "Date"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

## Water Potential Data Frame that uses earlier functions to check data upon save.
app_wp = wp_tab.data_editor(dl_flo.rename(columns = {"TIMESTAMP": "Date"}), disabled = ["Date", "WP_mean", "WP_std", "WP_min", "WP_max"], hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})
if wp_tab.button("Save Pressure Bomb Data"):
  if pb_check(app_wp) == "Fail":
    wp_tab.error("Upload Failed Check Inputs")
  else:
    pressure_bomb_upload(app_wp.rename(columns = {"Date": "TIMESTAMP"}))
    wp_tab.success("Upload Successful!")

## Weather data is rearranged and displayed
dl_gen = dl_gen[["TIMESTAMP", "VPD", "Air_Temperature (C)", "Air_Temperature (F)", "Relative_Humidity (%)"]]
weather_tab.dataframe(dl_gen.rename(columns = {"TIMESTAMP": "Date"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

bottom_margin = 0

## Irrigation Visualization
def irr_vis(irr = app_df):
  irr_plot = go.Figure()

  irr_plot.add_trace(go.Bar(x = pd.to_datetime(irr["Date"]), y = irr["Irrigation"], name = "Irrigation (in)", showlegend = True))
  irr_plot.update_layout(
    margin = dict(t = 0, b = bottom_margin, r = 150),
    yaxis_title = "Irrigation Applied (in)"
  )
  return irr_plot

irr_tab.subheader("Applied Irrigation")
irr_tab.plotly_chart(irr_vis())

## ET Visualization
def et_vis(et = et_both):
  et_plot = make_subplots(specs=[[{"secondary_y": True}]])
  
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["eto"], name = "ETc via CIMIS"), secondary_y=False)
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["eta"], name = "ETa via OpenET"), secondary_y=False)
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["etof"], name = "FrET via OpenET", mode = "markers"), secondary_y=True)
  et_plot.update_layout(
    margin = dict(t = 0),
    hovermode = "x unified"
  )
  et_plot.update_yaxes(title_text = "ETa & ETc (mm)", secondary_y=False)
  et_plot.update_yaxes(title_text = "FrET (mm)", secondary_y=True)
  return et_plot

et_tab.subheader("Evapotranspiration")
et_tab.plotly_chart(et_vis())

## Soil Heat Map Visualization along with depth filtering
soil_tab.subheader("Soil Moisture Content")
heat_select = soil_tab.selectbox("Soil Moisture Depth:", ["All", "Near Surface", "Mid Surface", "Deep Surface"])
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
      hoverongaps = False,
      zmin = 0,
      zmax = 50
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
    margin = dict(t = 0, b = bottom_margin),
    yaxis = dict(autorange = "reversed")
  )

  return heatmap


soil_tab.plotly_chart(heat_map())

## Water Potential visualization
def water_potential(wp = dl_flo, dl_gen = dl_gen):
  wp_plot = go.Figure()
  wp["WP_high"] = wp["WP_mean"] + wp["WP_std"]
  wp["WP_low"] = wp["WP_mean"] - wp["WP_std"]
  wp_plot.add_trace(go.Scatter(x = wp["TIMESTAMP"], y = wp["Pressure_Bomb"], line=dict(color="#9b2335"), mode = "markers", name = "User Pressure Bomb"))
  wp_plot.add_trace(go.Scatter(x = wp["TIMESTAMP"], y = wp["WP_min"], line=dict(color="#2ca89a"), name = "Min. WP"))
  wp_plot.add_trace(go.Scatter(x = wp["TIMESTAMP"], y = wp["WP_max"], line=dict(color="#2ca89a", dash = "dash"), name = "Max. WP"))
  wp_plot.add_trace(go.Scatter(x = wp["TIMESTAMP"], y = wp["WP_low"], line=dict(width=0), showlegend=False, name = "Obs. - 1 SD"))
  wp_plot.add_trace(go.Scatter(x = wp["TIMESTAMP"], y = wp["WP_high"], fill = "tonexty", line=dict(width=0), fillcolor="rgba(26, 111, 175, 0.42)", showlegend=False, name = "Obs. + 1 SD"))
  wp_plot.add_trace(go.Scatter(x = wp["TIMESTAMP"], y = wp["WP_mean"], mode = "lines", line=dict(color="#1a6faf", width=2), name = "Observed WP"))
  wp_plot.add_trace(go.Scatter(x = dl_gen["TIMESTAMP"], y = (((dl_gen["VPD"]*-0.12)-0.41)*10), line=dict(color="#e07b39", width=2), mode = "lines", name = "Baseline WP"))

  wp_plot.update_layout(
    yaxis_title = "Water Potential (Bar)",
    hovermode = "x unified",
    margin = dict(t = 0, b = bottom_margin)
  )

  # wp_plot.update_xaxes(
  #   dtick = 7*24*60*60*1000,
  #   tickformat="%b\n%d\n%Y",
  #   title = "Date"
  # )

  return wp_plot

wp_tab.subheader("Water Potential")
wp_tab.plotly_chart(water_potential())

## Weather Plot
def weather_plot(dl_gen = dl_gen):
  weather = make_subplots(specs=[[{"secondary_y": True}]])

  weather.add_trace(go.Scatter(x=dl_gen["TIMESTAMP"], y=dl_gen["Air_Temperature (F)"], mode="lines", name="Air Temperature (F)", line=dict(color="red")), secondary_y=False)
  # weather.add_trace(go.Scatter(x=dl_gen["TIMESTAMP"], y=dl_gen["Air_Temperature (C)"], mode="lines", name="Air Temperature (C)"))
  weather.add_trace(go.Scatter(x=dl_gen["TIMESTAMP"], y=dl_gen["VPD"], mode="lines", name="VPD (kPa)"), secondary_y=True)

  weather.update_layout(
    yaxis_title = "Value",
    hovermode = "x unified",
    margin = dict(t = 0, b = bottom_margin)
  )
  weather.update_yaxes(title_text = "Air Temperature (F)", secondary_y=False)
  weather.update_yaxes(title_text = "VPD (kPa)", secondary_y=True)

  # weather.update_xaxes(
  #   dtick = 7*24*60*60*1000,
  #   tickformat="%b\n%d\n%Y",
  #   title = "Date"
  # )
  return weather

weather_tab.subheader("Weather")
weather_tab.plotly_chart(weather_plot())

st.write("")
st.write("")
st.write("")
st.write("")
st.write("")
st.write("")
st.write("")
st.write("")
st.write("")
st.divider()
st.write("")
st.write("")
st.write("")
## Tutorial/Credits/Glossary Set Up
text_col1, text_col2, text_col3, text_col4, text_col5, text_col6, text_col7 = st.columns(7)
info_col1, info_col2, info_col3, info_col4, info_col5, info_col6 = st.columns(6)

@st.dialog("Tutorial", width = "large")
def show_tutorial():
    st.subheader("Introduction")
    st.write("The CSGrowers App is a pilot program developed to give growers a dashboard to view nearly live data and the ability to save irrigation data, pressure bomb data, and customizations to data and data visualizatoins.")
    st.write("The following tutorial will give you the basics on how to interface with this app. For more information on our methods of gathering, manipulating, and storing data visit the [GitHub Repository](https://github.com/crop-sensing/csgrowers)" \
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
@st.dialog("Glossary")
def show_glossary():
    st.write("**ET**: Evapotranspiration")
    st.write("**ETa**: Ensemble ET, gathered through satelite via OpenET")
    st.write("**ETo**: Reference ET, via CIMIS")
    st.write("**FrET**: Fractional ET, a ratio of ETo/ETa, via OpenET")
    st.write("**SWC**: Soil Water Content, via SAWS Towers")
    st.write("**VPD**: Vapor Pressure Deficit, via SAWS Towers")
    st.write("**WP**: Water Potential, gathered via SAWS Towers")

  ## Shows tutorial/credits on click

if info_col3.button("Get Started", use_container_width=True):
  show_tutorial()
if info_col4.button("Glossary", use_container_width=True):
  show_glossary()
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
import re
import time

## Must be first line
st.set_page_config(layout = "wide")
warnings.filterwarnings("ignore")
st.title("CSGrowers - Capay Independence")

origin = "streamlit" ## streamlit or local

site = "CAP_001"
curr_page = "CAP_001"

years_active = ["2025", "2026"]

DEFAULTS = {
    "def_fc": float(st.secrets[site]["def_fc"]),
    "def_wilt_p": float(st.secrets[site]["def_wilt_p"]),
    "def_mad": float(st.secrets[site]["def_mad"])
}

et_dict = {
         1: 0.4,
         2: 0.41,
         3: 0.62,
         4: 0.8,
         5: 0.94,
         6: 1.05,
         7: 1.11,
         8: 1.11,
         9: 1.06,
         10: 0.92,
         11: 0.69,
         12: 0.43
      }

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
    res = client.table("water_potential").select("data").eq("dataset_name", "wp_hourly").eq("site", site).eq("username", "ALL").execute()
    dl_flo_hourly = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
    dl_flo_hourly["TIMESTAMP"] = pd.to_datetime(dl_flo_hourly["TIMESTAMP"], unit = "ms")

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
    irr_temp_new["date"] = et_both["date"]
    irr_temp_new["irr"] = 0
    irr_temp_new["precip"] = et_both["pr"] / 25.4

    try:
      ## Retrieve Saved Irrigation
      res = client.table("irrigation").select("data").eq("dataset_name", "saved_irr").eq("site", site).eq("username", email).execute()
      user_irr = pd.read_json(StringIO(json.dumps(res.data[0]["data"])))
      user_irr["date"] = pd.to_datetime(user_irr["date"], unit = "ms")
      user_irr = pd.concat([user_irr, irr_temp_new[irr_temp_new["date"] > user_irr.date.max()]])

    except IndexError:
      user_irr = irr_temp_new

    ## Retrieve Crop Coefficient
    try:
      res = client.table("headers").select("value").eq("data_type", "crop_coeff").eq("site", site).eq("username", email).execute()
      sql_crop_coeff = str(res.data[0]["value"][0])
    except:
      sql_crop_coeff = et_dict[datetime.datetime.today().month]
    
    ## Retrieve Soil Panel
    try:
      res = client.table("headers").select("value").eq("data_type", "soil_panel").eq("site", site).eq("username", email).execute()
      sql_soil_panel = res.data[0]["value"]
    except:
      sql_soil_panel = ["0.23", "0.11", "0.45"]
    
    ## Gets last week, filters et data
    today = pd.Timestamp.today().normalize()
    days_since_sunday = (today.weekday() + 1) % 7 
    last_sunday = today - pd.Timedelta(days=days_since_sunday)
    start_date = last_sunday - pd.Timedelta(days=6)
    et_last_week = et_both[(et_both['date'] >= start_date) & (et_both['date'] < last_sunday)]

    return et_both, dl_gen, dl_soil_all, dl_flo, user_irr, irr_temp_new, depths, et_last_week, sql_crop_coeff, sql_soil_panel, "", dl_flo_hourly

et_both, dl_gen, dl_soil_all, dl_flo, user_irr, template, depths, et_last_week, sql_crop_coeff, sql_soil_panel, default_val, dl_flo_hourly = data_set_up()

## Checks column names, time values, and amount of rows in a data frame.
## Returns specific error codes if user df fails test.
def user_upload_check(df, cols = ["Date", "Irrigation (in)", "Precipitation (in)"]):
  checks = 1
  codes = []
  cols = set(cols)
  if (set(df.columns) == cols) == False:
    checks -= 1
    codes.append("Your columns do not match the template.")
  try:
    df["Irrigation (in)"] = df["Irrigation (in)"].apply(pd.to_numeric)
  except:
    codes.append("There is an invalid data type in your dataset.")
    checks -= 1
  if checks == 1:
    return True, codes
  else:
    return False, codes

## Uploads irrigation data to proper database
def supabase_upload(df, site = site, username = email, template = template):
    ## Takes user df and standardizes names
    df = df.rename(columns = {"Date": "date", "Irrigation (in)": "irr", "Precipitation (in)": "preip", "irrigation": "irr", "pr": "precip"})
    df_dates = template.set_index("date")
    df_data = df.set_index("date")
    ## Replaces template 0s with NAs to make it easier for next line
    df_dates = df_dates.replace(0, pd.NA)
    ## Merges template and user irrigation dfs, user data gets priority
    df_merged = df_dates.combine_first(df_data)
    ## Replaces NAs with 0s (so that when the df is loaded back water balance eq can run)
    df_merged = df_merged.fillna(0).reset_index()
    df_merged = df_merged[["date", "irr", "precip"]]
    json_data = json.loads(df_merged.to_json())
    client.table("irrigation").upsert({
          "dataset_name": "saved_irr",
          "data": json_data,
          "site": site,
          "username": username,
    }, on_conflict="dataset_name,site,username").execute()
    ## Rerun app and requery supabase upon reload
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
    layer_tops = [0] + LAYER_BOUNDS_MM[:-1]
    for i in range(len(SENSOR_DEPTHS_CM)):
        top = layer_tops[i]
        if top >= rz_mm:
            break
        bot = min(LAYER_BOUNDS_MM[i], rz_mm)
        thick[i] = bot - top
    return thick


def compute_storage(df: pd.DataFrame, rz_mm: float) -> pd.Series:
    thick = layer_thickness_in_rz(rz_mm)
    swc_cols = [f"SWC_{d}cm" for d in SENSOR_DEPTHS_CM]
    df[swc_cols] = df[swc_cols].ffill()  # carry last known reading forward
    df[swc_cols] = df[swc_cols] / 100.0
    storage = (df[swc_cols].values * thick).sum(axis=1)
    return pd.Series(storage, index=df.index, name="Storage_mm")


def water_balance(df: pd.DataFrame, fc: float, wp: float,
                  rz_cm: float, mad: float) -> pd.DataFrame:
    rz_mm  = rz_cm * 10
    taw_mm = (fc - wp) * rz_mm
    raw_mm = mad * taw_mm

    df = df.copy()
    df["Storage_mm"] = compute_storage(df, rz_mm)
    df["dStorage_mm"] = df["Storage_mm"] - df["Storage_mm"].shift(1)
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
  fl.Marker(location = [float(st.secrets[site]["true_lat"]), float(st.secrets[site]["true_long"])], popup = site).add_to(m)
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
              #### ETo Total (Last 7 Days): {eto_sum:.3f} in.
              """
              )
  
  #### Crop Coeffecient:
  ## Loads last user input, allows user to reset crop coeff
  if "crop_coeff" not in st.session_state:
    st.session_state["crop_coeff"] = sql_crop_coeff
  button_col1, button_col2 = st.columns(2)
  if button_col1.button("Reset Value", width = "stretch"):
    st.session_state["crop_coeff"] = et_dict[datetime.datetime.today().month]
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
              #### ETc Total (Last 7 Days): **{eto_cc:.3f} in.**""")

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
      mad = st.slider("Depletion Fraction (MAD)", 0.30, 0.70, float(sql_soil_panel[2]), 0.05, key = "def_mad")
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
    sm_result = st.session_state["sm_input"]
    wb_results = water_balance(soil_calc_df, fc=sm_result["fc"], wp=sm_result["wilt_p"],
                                                                    rz_cm=100, mad=sm_result["mad"])
    last = wb_results.iloc[-7:-1]
  
    dr_val  = float(last["Dr_mm"].mean() / 25.4)
    taw_val = float(last["TAW_mm"].iloc[0] / 25.4)
    raw_val = float(last["RAW_mm"].iloc[0] / 25.4)
  else:
    dr_val = []
    taw_mm = []
    raw_mm = []
    wb_results = water_balance(soil_calc_df, fc=0.23, wp=0.11, rz_cm=100, mad=0.45)
    last = wb_results.iloc[-7:-1]
    
    dr_val  = float(last["Dr_mm"].mean() / 25.4)
    taw_val = float(last["TAW_mm"].iloc[0] / 25.4)
    raw_val = float(last["RAW_mm"].iloc[0] / 25.4)
  dr_color = "inverse" if np.sum(dr_val) > np.sum(raw_val) else "normal"
  r1, r2, r3 = st.columns(3)
  r1.metric("RZD (in)", f"{np.sum(dr_val):.1f}", width = "content",
      delta=f"{'Above' if dr_val > raw_val else 'Below'} RAW", delta_color=dr_color)
  r2.metric("TAW (in)", f"{taw_val:.1f}", width = "content")
  r3.metric("RAW (in)", f"{np.sum(raw_val):.1f}", width = "content")
  status_emoji = {"Irrigate": "🔴", "Monitor": "🟡", "Adequate": "🟢"}
  st.metric("Latest Status", f"{status_emoji[status(np.sum(dr_val), np.sum(raw_val))]} {status(np.sum(dr_val), np.sum(raw_val))}")
  
date1, date2 = st.columns(2)
date_start = date1.date_input("Start Date", value = datetime.date.today()-datetime.timedelta(days=30))
date_end = date2.date_input("End Date", value = datetime.date.today())

## Function that does the filtering
def time_restrict(date_start = date_start, date_end = date_end,
                  et_both = et_both, dl_soil_all = dl_soil_all, dl_flo = dl_flo, dl_gen = dl_gen, user_irr = user_irr, dl_flo_hourly = dl_flo_hourly):
  start = pd.to_datetime(date_start)
  end = pd.to_datetime(date_end)
  et_both = et_both[(et_both["date"] >= start) & (et_both["date"] <= end)]
  et_both["eto"] = et_both["eto"]/25.4
  et_both["eta"] = et_both["eta"]/25.4
  et_both["etof"] = et_both["etof"]/25.4
  dl_soil_all = dl_soil_all[(dl_soil_all["TIMESTAMP"] >= start) & (dl_soil_all["TIMESTAMP"] <= end)]
  dl_flo = dl_flo[(dl_flo["TIMESTAMP"] >= start) & (dl_flo["TIMESTAMP"] <= end)]
  dl_flo_hourly = dl_flo_hourly[(dl_flo_hourly["TIMESTAMP"] >= start) & (dl_flo_hourly["TIMESTAMP"] <= end)]
  dl_gen = dl_gen[(dl_gen["TIMESTAMP"] >= start) & (dl_gen["TIMESTAMP"] <= end)]
  user_irr = user_irr[(user_irr["date"] >= start) & (user_irr["date"] <= end)]
  return et_both, dl_soil_all, dl_flo, dl_gen, user_irr, dl_flo_hourly

et_both, dl_soil_all, dl_flo, dl_gen, user_irr, dl_flo_hourly = time_restrict()

## Initialize data table tabs
irr_tab, et_tab, soil_tab, wp_tab, weather_tab = st.tabs(["Irrigation", "Evapotranspiration", "Soil Moisture", "Water Potential", "Weather"])


bottom_margin = 0

## Irrigation Visualization
def irr_vis(irr = user_irr):
  irr_plot = go.Figure()

  irr_plot.add_trace(go.Bar(x = pd.to_datetime(irr["date"]), y = irr["irr"], name = "Irrigation (in)", showlegend = True))
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
  
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["eto"]*cc, name = "ETc via CIMIS"), secondary_y=False)
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["eta"], name = "ETa via OpenET"), secondary_y=False)
  et_plot.add_trace(go.Scatter(x = et["date"], y = et["etof"], name = "FrET via OpenET", mode = "markers"), secondary_y=True)
  et_plot.update_layout(
    margin = dict(t = 0),
    hovermode = "x unified"
  )
  et_plot.update_yaxes(title_text = "ETa & ETc (in)", secondary_y=False)
  et_plot.update_yaxes(title_text = "FrET (in)", secondary_y=True)
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
      zmax = 30
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

### Irrigation Upload Start
UNIT_PATTERNS = {
    "mm":        r"\bmm\b|millimeters?|millimetres?",
    "cm":        r"\bcm\b|centimeters?|centimetres?",
    "inches":    r"\bin\b|inch|inches",
    "liters":    r"\bl\b|litres?|liters?",
    "gallons":   r"\bgal\b|gallons?",
    "m³":        r"\bm3\b|m³|cubic\s*meters?|cubic\s*metres?",
    "ft³":       r"\bft3\b|ft³|cubic\s*feet|cubic\s*foot",
    "acre-feet": r"acre[\s\-]feet|acre[\s\-]ft",
}
 
def detect_unit_from_text(text: str) -> str | None:
    text = text.lower()
    for unit, pattern in UNIT_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return unit
    return None
 
def infer_unit(col_name: str, df: pd.DataFrame) -> str:
    found = detect_unit_from_text(col_name)
    if found:
        return found
    if df[col_name].dtype == object:
        for val in df[col_name].dropna().astype(str).head(20):
            found = detect_unit_from_text(val)
            if found:
                return found
    try:
        median = pd.to_numeric(df[col_name], errors="coerce").dropna().median()
        if median < 5:    return "inches (estimated)"
        if median < 50:   return "mm (estimated)"
        if median < 500:  return "liters (estimated)"
        return "gallons (estimated)"
    except Exception:
        return "unknown"

 
DATE_KEYWORDS  = ["date", "day", "time", "timestamp", "dt", "fecha"]
IRRIG_KEYWORDS = ["irrig", "water", "flow", "amount", "depth", "volume",
                  "applied", "mm", "inch", "gallon", "litre", "liter"]
 
def score_column(col: str, keywords: list[str]) -> int:
    return sum(kw in col.lower() for kw in keywords)
 
def find_best_column(cols: list[str], keywords: list[str]) -> str | None:
    scores = {c: score_column(c, keywords) for c in cols}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None
 
def auto_detect_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    date_col = next(
        (c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])), None
    ) or find_best_column(list(df.columns), DATE_KEYWORDS)
 
    irrig_candidates = [c for c in df.columns if c != date_col]
    irrig_col = find_best_column(irrig_candidates, IRRIG_KEYWORDS) or next(
        (c for c in irrig_candidates if pd.api.types.is_numeric_dtype(df[c])), None
    )
    return date_col, irrig_col
 
def read_raw_file(uploaded_file) -> pd.DataFrame | None:
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file, parse_dates=True)
        elif name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file, parse_dates=True)
    except Exception as e:
        st.error(f"Could not read file: {e}")
    return None
 
def _column_selector_form(
    df_raw: pd.DataFrame,
    suggested_date: str | None,
    suggested_irrig: str | None,
) -> tuple[str | None, str | None, str | None, bool]:
    """
    Renders a styled form card for column confirmation.
    Returns (date_col, irrig_col, unit_override, confirmed).
    confirmed=False means the user hasn't submitted yet.
    """
    cols = list(df_raw.columns)
 
    # CSS to style the form like a modal card
    st.markdown("""
    <style>
    div[data-testid="stForm"] {
        border: border: 1px solid var(--border-color, rgba(128,128,128,0.3));
        border-radius: 12px;
        padding: 1.5rem 1.75rem;
        background: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 100%;
        margin: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
 
    with st.form("column_selection_form", clear_on_submit=False):
        st.markdown("### Confirm your columns")
        st.caption("We've made our best guess below — adjust if anything looks off.")
 
        with st.expander("Preview raw file (first 5 rows)", expanded=False):
            st.dataframe(df_raw.head(), use_container_width=True)
 
        st.divider()
 
        date_idx  = cols.index(suggested_date)  if suggested_date  in cols else 0
        irrig_idx = cols.index(suggested_irrig) if suggested_irrig in cols else (1 if len(cols) > 1 else 0)
 
        chosen_date = st.selectbox(
            "Date column",
            options=cols,
            index=date_idx,
            help="Column containing the date or timestamp for each reading.",
        )
        chosen_irrig = st.selectbox(
            "Irrigation column",
            options=cols,
            index=irrig_idx,
            help="Column containing how much water was applied each day.",
        )
 
        unit_options = [
            "auto-detect", "mm", "cm", "inches",
            "liters", "gallons", "m³", "ft³", "acre-feet", "other",
        ]
        chosen_unit = st.selectbox(
            "Units (optional override)",
            options=unit_options,
            index=0,
            help="Leave on auto-detect unless you want to force a specific unit.",
        )
 
        submitted = st.form_submit_button("✅ Confirm & Load", use_container_width=True)
 
    if submitted:
        if chosen_date == chosen_irrig:
            st.error("Date and irrigation columns must be different. Please adjust your selection.")
            return None, None, None, False
        unit_override = chosen_unit if chosen_unit not in ("auto-detect", "other") else None
        return chosen_date, chosen_irrig, unit_override, True
 
    return None, None, None, False
 
def build_irrigation_df(
    df_raw: pd.DataFrame,
    date_col: str,
    irrig_col: str,
    unit_override: str | None = None,
) -> tuple[pd.DataFrame | None, str]:
 
    df = df_raw[[date_col, irrig_col]].copy()
    df.columns = ["date", "irrigation"]
 
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates  = df["date"].isna().sum()
 
    df["irrigation"] = (
        df["irrigation"].astype(str)
        .str.extract(r"([\d.]+)", expand=False)
        .astype(float)
    )
 
    df.dropna(subset=["date", "irrigation"], inplace=True)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
 
    if df.empty:
        return None, "No valid rows remain after cleaning. Check your date and value formats."
 
    unit = unit_override if unit_override else infer_unit(irrig_col, df_raw)
 
    df.attrs["unit"]               = unit
    df.attrs["original_date_col"]  = date_col
    df.attrs["original_irrig_col"] = irrig_col
    df.attrs["skipped_rows"]       = bad_dates
 
    msg = (
        f"✅ Loaded **{len(df)} rows** — "
        f"date: `{date_col}`, irrigation: `{irrig_col}`, units: **{unit}**"
    )
    if bad_dates:
        msg += f"  ⚠️ {bad_dates} row(s) had unparseable dates and were dropped."
    return df, msg
 
def irrigation_uploader() -> pd.DataFrame | None:
    """
    Drop-in Streamlit component. Renders a file uploader, then a column-
    selection form (styled as a modal card), and returns a clean DataFrame
    with columns ['date', 'irrigation'] once the user confirms.
 
    Usage:
        df = irrigation_uploader()
        if df is not None:
            unit = df.attrs["unit"]
            st.line_chart(df.set_index("date")["irrigation"])
    """
    st.subheader("Upload Irrigation Data")
    st.caption("Accepted formats: CSV, Excel (.xlsx / .xls)")
 
    uploaded = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "xls"],
        help="File should contain at least one date column and one irrigation/water column.",
    )
 
    if uploaded is None:
        st.info("Upload a CSV or Excel file to get started.")
        return None
 
    # Cache the raw parse in session_state so Streamlit re-runs don't re-read the file
    file_key = f"_irrig_raw_{uploaded.name}_{uploaded.size}"
    if file_key not in st.session_state:
        df_raw = read_raw_file(uploaded)
        if df_raw is None:
            return None
        st.session_state[file_key] = df_raw
    df_raw = st.session_state[file_key]
 
    # Auto-suggest columns, then let the user confirm
    suggested_date, suggested_irrig = auto_detect_columns(df_raw)
    date_col, irrig_col, unit_override, confirmed = _column_selector_form(
        df_raw, suggested_date, suggested_irrig
    )
 
    if not confirmed:
        return None
 
    # Build and return the final DataFrame
    df, message = build_irrigation_df(df_raw, date_col, irrig_col, unit_override)
 
    if df is None:
        st.error(message)
        return None
 
    st.success(message)
    with st.expander("Preview cleaned data", expanded=True):
        st.dataframe(df, use_container_width=True)
 
    return df

with irr_tab:
  df = irrigation_uploader()

## Irrigation data editor/button initilization
if df is None:
  user_file = None
  user_irr["irr"] = user_irr["irr"].astype(float)
  user_irr["precip"] = user_irr["precip"].astype(float)
  try:
    app_df = irr_tab.data_editor(user_irr.rename(columns = {"date": "Date", "irr": "Irrigation (in)", "precip": "Precipitation (in)"}).sort_values(by = "Date", ascending=False),
                                          column_config = {
                                          "Date": st.column_config.DateColumn(),
                                          "Irrigation (in)": st.column_config.NumberColumn(min_value = 0, max_value = 10, step = .001, format = "%.3f"),
                                          "Precipitation (in)": st.column_config.NumberColumn(min_value = 0, max_value = 10, step = .001, format = "%.3f")},
                                          hide_index = True,
                                          disabled = ["Date"])
  except:
     st.write("name fail")
     app_df = irr_tab.data_editor(user_irr.rename(columns = {"date": "Date", "precip": "Precipitation (in)"}).sort_values(by = "Date", ascending=False),
                                          column_config = {
                                          "Date": st.column_config.DateColumn(),
                                          "Irrigation (in)": st.column_config.NumberColumn(min_value = 0, max_value = 10, step = .001, format = "%.3f"),
                                          "Precipitation (in)": st.column_config.NumberColumn(min_value = 0, max_value = 10, step = .001, format = "%.3f")},
                                          hide_index = True,
                                          disabled = ["Date"])
  
else:
  time.sleep(3)
  supabase_upload(df.merge(et_both[["date","pr"]], on = "date", how = "outer"))

if irr_tab.button("Save"):
  checkdown, codes = user_upload_check(app_df)
  if checkdown == True:
    supabase_upload(app_df)
    irr_tab.success('File save successful')
  else:
    irr_tab.error("ERROR: " +  " ERROR: ".join(codes) + " --- file did not save to cloud.")

## Displays ET data
et_both = et_both[["date", "eto", "eta", "etof"]]
et_both["eto"] = et_both["eto"]*cc
et_tab.dataframe(et_both.iloc[::-1].rename(columns = {"date": "Date", "eto": "ETc", "eta": "ETa", "etof": "FrET"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

## Rearrange and show soil data
soil_cols = list(dl_soil_all.columns)
soil_cols = soil_cols[-1::] + soil_cols[0:-1]
dl_soil_all = dl_soil_all[soil_cols]
soil_tab.dataframe(dl_soil_all.iloc[::-1].rename(columns = {"TIMESTAMP": "Date"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

## Water Potential Data Frame that uses earlier functions to check data upon save.
app_wp = wp_tab.data_editor(dl_flo.iloc[::-1].rename(columns = {"TIMESTAMP": "Date"}), disabled = ["Date", "WP_mean", "WP_std", "WP_min", "WP_max", "WP"], hide_index = True,
                 column_config={"Date": st.column_config.DateColumn(),
                                "Precipitation (in)": st.column_config.NumberColumn(min_value = -20, max_value = 10, step = .001, format = "%.3f")})
if wp_tab.button("Save Pressure Bomb Data"):
  if pb_check(app_wp) == "Fail":
    wp_tab.error("Upload Failed Check Inputs")
  else:
    pressure_bomb_upload(app_wp.rename(columns = {"Date": "TIMESTAMP"}))
    wp_tab.success("Upload Successful!")

## Weather data is rearranged and displayed
dl_gen = dl_gen[["TIMESTAMP", "VPD", "Air_Temperature (C)", "Air_Temperature (F)", "Relative_Humidity (%)"]]
weather_tab.dataframe(dl_gen[::-1].rename(columns = {"TIMESTAMP": "Date"}), hide_index = True,
                 column_config={"Date": st.column_config.DateColumn()})

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
info_col1, info_col2, info_col3, info_col4, info_col5, info_col6, info_col7 = st.columns(7)

with open("tutorial.json", "r") as f:
    slide_content = json.load(f)

@st.dialog("Tutorial", width="large")
def tutorial_dialog():
    if "slide" not in st.session_state:
        st.session_state.slide = 0

    def next_slide():
        st.session_state.slide += 1

    def back_slide():
        st.session_state.slide -= 1

    def reset_slide():
        st.session_state.slide = 0

    slide = slide_content[st.session_state.slide]
    total = len(slide_content)
    current = st.session_state.slide

    st.markdown(f"### {slide['title']}")
    if "image" in slide:
      st.image(slide["image"])
    st.write(slide["content"])
    st.progress((current + 1) / total)
    st.caption(f"Step {current + 1} of {total}")
    st.divider()

    col1, col2, col3 = st.columns([1, 5, 1])

    with col1:
        if current > 0:
            st.button("← Back", on_click=back_slide)

    with col3:
        if current < total - 1:
            st.button("Next →", on_click=next_slide)
        else:
            if st.button("✅ Done"):
                reset_slide()
                st.rerun()

@st.dialog("Glossary")
def show_glossary():
    st.write("**ET**: Evapotranspiration")
    st.write("**ETa**: Ensemble ET, gathered through satelite via OpenET")
    st.write("**ETc**: Crop ET, Reference ET * Crop Coefficient, where Crop Coefficient is decided based on crop and time of year")
    st.write("**ETo**: Reference ET, via CIMIS")
    st.write("**FrET**: Fractional ET, a ratio of ETo/ETa, via OpenET")
    st.write("**MAD**: Management Allowed Depletion")
    st.write("**RAW**: Readily Available Water")
    st.write("**RZD**: Root Zone Depletion")
    st.write("**TAW**: Total Available Water")
    st.write("**SWC**: Soil Water Content, via SAWS Towers")
    st.write("**VPD**: Vapor Pressure Deficit, via SAWS Towers")
    st.write("**WP**: Water Potential, gathered via SAWS Towers")


def send_bug_report_email(title, feedback, description, severity, reporter_email):
    client.table("bug_report").upsert({
      "title": title,
      "feedback_type": feedback,
      "description": description,
      "severity": severity,
      "return_email": reporter_email
  }).execute()
    return True

@st.dialog("Feedback", width = "large")
def bug_report_widget():
  with st.form("bug_report_form", clear_on_submit=True):
    title = st.text_input("Short Summary", max_chars=120)
    feedback_type = st.selectbox(
      "What type of feedback are you reporting?",
      ["Bug", "Feature Request", "Improvement"]
    )
    description = st.text_area(
      f"Description:", height=140
    )
    
    severity = st.select_slider(
      "Severity",
      options=["N/A","Low", "Medium", "High", "Critical"],
      value="N/A",
    )
    reporter_email = st.text_input(
      "Your e-mail:"
    )

    submitted = st.form_submit_button("Submit bug report")

    if submitted:
      if not title.strip():
          st.error("Please enter a short summary before submitting.")
          return


      with st.spinner("Sending report..."):
          try:
              send_bug_report_email(title, feedback_type, description, severity, reporter_email)
              st.success("Form has been successfully submitted!")
          except:
              st.error("Form failed to submit.")

  ## Shows tutorial/credits on click

if info_col3.button("Get Started", use_container_width=True):
    st.session_state.next_clicked = 0
    st.session_state.slide = 0  # always start from slide 1
    tutorial_dialog()
if info_col4.button("Glossary", use_container_width=True):
  show_glossary()
if info_col5.button("Feedback", use_container_width=True):
   bug_report_widget()
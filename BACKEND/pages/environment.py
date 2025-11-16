import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from PIL import Image

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(layout="wide")
st.title("ENVIRONMENT DASHBOARD")

# ==============================
# ROLES
# ==============================
roles = ["Environment Ops", "City Planner", "Emergency Response"]
role = st.sidebar.selectbox("Select Your Role", roles)

# ==============================
# SESSION STATE FOR ACTUATORS & HISTORY
# ==============================
if "act_purifier" not in st.session_state:
    st.session_state.act_purifier = False
if "act_dehumidifier" not in st.session_state:
    st.session_state.act_dehumidifier = False
if "act_flood_pumps" not in st.session_state:
    st.session_state.act_flood_pumps = 0
if "history" not in st.session_state:
    st.session_state.history = []

# ==============================
# SIDEBAR CONTROL PANEL
# ==============================
with st.sidebar:
    st.header("Control Panel")
    situation = st.selectbox("Situation Mode", [
        "Normal", "Heatwave", "Flood", "Pollution Spike"
    ])
    st.write("---")
    st.write("### Manual Overrides")
    humidity_control = st.slider("Dehumidifier", 30, 100, 60)
    aqi_control = st.slider("Air Purifier Level", 0, 100, 0)
    st.write("---")
    st.write("### Actuators")
    st.session_state.act_purifier = st.checkbox("Air Purifier", value=st.session_state.act_purifier)
    st.session_state.act_dehumidifier = st.checkbox("Dehumidifier", value=st.session_state.act_dehumidifier)
    st.session_state.act_flood_pumps = st.select_slider(
        "Flood Pump Level", options=[0,1,2,3], value=st.session_state.act_flood_pumps
    )
    st.write("---")
    st.subheader("Accessibility Options")
    high_contrast = st.checkbox("High Contrast Mode")
    large_fonts = st.checkbox("Large Fonts")

# ==============================
# SIMULATE ENVIRONMENT
# ==============================
def simulate_environment(situation):
    base_temp, base_humidity, base_aqi = 28, 65, 40
    if situation == "Heatwave": return base_temp+10, base_humidity-10, base_aqi+20
    elif situation == "Flood": return base_temp-3, base_humidity+20, base_aqi+5
    elif situation == "Pollution Spike": return base_temp+2, base_humidity-5, base_aqi+60
    return base_temp, base_humidity, base_aqi

temp_value, humidity_value, aqi_value = simulate_environment(situation)

# ==============================
# APPLY OVERRIDES & ACTUATOR EFFECTS
# ==============================
humidity_value = (humidity_value + humidity_control)/2
aqi_value = max(0, aqi_value - aqi_control)
if st.session_state.act_purifier: aqi_value = max(0, aqi_value - 15)
if st.session_state.act_dehumidifier: humidity_value = max(0, humidity_value - 10)
if st.session_state.act_flood_pumps > 0: humidity_value = max(0, humidity_value - st.session_state.act_flood_pumps*4)

# ==============================
# SAVE TO HISTORY
# ==============================
st.session_state.history.append({
    "temp": temp_value,
    "humidity": humidity_value,
    "aqi": aqi_value
})
hist_df = pd.DataFrame(st.session_state.history[-24:])  # last 24 readings

# ==============================
# HELPER FUNCTION: STAT CARD
# ==============================
def stat_card(title, value, unit="", threshold=None, color="#2196f3"):
    if threshold and value > threshold: color = "#f44336"
    font_size = "24px" if large_fonts else "16px"
    st.markdown(f"""
        <div style="border:2px solid {color}; padding:10px; border-radius:12px; text-align:center;">
            <h3 style="font-size:{font_size};">{title}</h3>
            <h1 style="font-size:{font_size};">{value}{unit}</h1>
        </div>
    """, unsafe_allow_html=True)

# ==============================
# ROW 1: REAL-TIME STATS
# ==============================
if role in ["Environment Ops", "Emergency Response"]:
    stat1, stat2, stat3, stat4 = st.columns(4)
    with stat1: stat_card("Temperature", temp_value, "°C", threshold=35)
    with stat2: stat_card("Humidity", humidity_value, "%", threshold=80)
    with stat3: stat_card("AQI", aqi_value, "", threshold=150)
    # Flood tank gauge
    with stat4:
        max_capacity, base_level = 5000, 3200
        current_level = max(0, base_level - st.session_state.act_flood_pumps*300)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_level,
            gauge={'axis': {'range':[0,max_capacity]},
                   'bar': {'color': "blue"},
                   'steps':[{'range':[0,max_capacity*0.5],'color':'green'},
                            {'range':[max_capacity*0.5,max_capacity*0.8],'color':'yellow'},
                            {'range':[max_capacity*0.8,max_capacity],'color':'red'}]},
            title={'text':"Flood Tank (L)"}))
        fig_gauge.update_layout(height=250, margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig_gauge, use_container_width=True)

# ==============================
# ALERTS
# ==============================
if aqi_value > 150: st.warning("AQI Alert! Health risk high!")
if humidity_value > 80: st.warning("Humidity Alert! Flood risk elevated!")
if temp_value > 35: st.warning("Temperature Alert! Heatwave conditions!")

# ==============================
# ROW 2: ACTUATORS STATUS
# ==============================
if role in ["Environment Ops", "Emergency Response"]:
    st.divider()
    st.subheader("Actuator Status")
    act1, act2, act3 = st.columns(3)
    with act1:
        color = "#4CAF50" if st.session_state.act_purifier else "#F44336"
        status = "ACTIVE" if st.session_state.act_purifier else "OFFLINE"
        st.markdown(f"<div style='border:2px solid {color}; padding:12px; border-radius:10px; text-align:center;'><h4>Air Purifier</h4><h2 style='color:{color}'>{status}</h2></div>", unsafe_allow_html=True)
    with act2:
        color = "#4CAF50" if st.session_state.act_dehumidifier else "#F44336"
        status = "ACTIVE" if st.session_state.act_dehumidifier else "OFFLINE"
        st.markdown(f"<div style='border:2px solid {color}; padding:12px; border-radius:10px; text-align:center;'><h4>Dehumidifier</h4><h2 style='color:{color}'>{status}</h2></div>", unsafe_allow_html=True)
    with act3:
        levels = {0:"OFF",1:"LOW",2:"MEDIUM",3:"HIGH"}
        colors = {0:"#F44336",1:"#FFC107",2:"#2196F3",3:"#4CAF50"}
        pump_level = st.session_state.act_flood_pumps
        st.markdown(f"<div style='border:2px solid {colors[pump_level]}; padding:12px; border-radius:10px; text-align:center;'><h4>Flood Pumps</h4><h2 style='color:{colors[pump_level]}'>{levels[pump_level]}</h2></div>", unsafe_allow_html=True)

# ==============================
# EMERGENCY RESPONSE HEATMAP WITH CITIZEN REPORTS
# ==============================
if role == "Emergency Response":
    st.divider()
    st.subheader("Emergency Response Heatmap")

    # --- Sidebar filters for citizen reports
    issues_to_show = st.sidebar.multiselect(
        "Show Citizen Issues",
        ["Smoke", "Flood", "Air Quality"],
        default=["Smoke", "Flood", "Air Quality"]
    )
    severity_threshold = st.sidebar.slider("Minimum Severity", 1, 5, 2)

    # --- Simulated citizen reports (replace with live data later)
    citizen_reports = [
        {"sector": "A1", "issue": "Smoke", "severity": 3},
        {"sector": "B2", "issue": "Flood", "severity": 2},
        {"sector": "C3", "issue": "Air Quality", "severity": 1},
        {"sector": "A2", "issue": "Flood", "severity": 4},
        {"sector": "B3", "issue": "Smoke", "severity": 5}
    ]
    # Filter reports
    filtered_reports = [
        r for r in citizen_reports
        if r["issue"] in issues_to_show and r["severity"] >= severity_threshold
    ]

    # --- Heatmap setup
    try:
        map_img = Image.open(r"C:\Users\User\Desktop\DASHBOARD\ortigas_dashboard\map.png")
        sectors = ["A1","A2","A3","B1","B2","B3","C1","C2","C3"]
        rows = [0,0,0,1,1,1,2,2,2]
        cols = [0,1,2,0,1,2,0,1,2]

        # Sensor AQI per sector
        if situation=="Normal": sector_aqi = np.random.randint(40,60,len(sectors))
        elif situation=="Heatwave": sector_aqi = np.random.randint(50,80,len(sectors))
        elif situation=="Flood": sector_aqi = np.random.randint(30,60,len(sectors))
        else: sector_aqi = np.random.randint(150,300,len(sectors))

        fig_map = go.Figure()
        fig_map.add_layout_image(dict(
            source=map_img, xref="x", yref="y", x=0, y=3, sizex=3, sizey=3,
            sizing="stretch", opacity=1, layer="below"))

        # Draw sensor AQI sectors
        for i, aqi in enumerate(sector_aqi):
            if aqi<=50: color="Green"
            elif aqi<=100: color="Yellow"
            elif aqi<=150: color="Orange"
            elif aqi<=200: color="Red"
            elif aqi<=300: color="Purple"
            else: color="Maroon"
            fig_map.add_shape(type="rect",
                              x0=cols[i], y0=2-rows[i], x1=cols[i]+1, y1=3-rows[i],
                              line=dict(color="black", width=3),
                              fillcolor=color, opacity=0.5)
            fig_map.add_annotation(x=cols[i]+0.5, y=2-rows[i]+0.5,
                                   text=f"{sectors[i]}<br>{aqi}", showarrow=False,
                                   font=dict(color="black", size=12))

        # Map citizen reports
        sector_coords = {s:(c,r) for s,c,r in zip(sectors, cols, rows)}
        for report in filtered_reports:
            x, y = sector_coords[report["sector"]]
            y = 2 - y  # invert row for plotting
            issue_color = {"Smoke":"red","Flood":"blue","Air Quality":"purple"}[report["issue"]]
            size = report["severity"] * 10
            fig_map.add_trace(go.Scatter(
                x=[x+0.5], y=[y+0.5],
                mode="markers+text",
                marker=dict(size=size, color=issue_color, opacity=0.7),
                text=[report["issue"]],
                textposition="top center",
                showlegend=False
            ))

        fig_map.update_xaxes(visible=False, range=[0,3])
        fig_map.update_yaxes(visible=False, range=[0,3])
        fig_map.update_layout(width=600, height=600, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_map, use_container_width=True)

    except:
        st.error("Map image not found.")


# ==============================
# ROW 3: HEATMAP + HOURLY TRENDS
# ==============================
if role in ["Environment Ops", "City Planner"]:
    st.divider()
    row3_map, row3_hour = st.columns([2.5,1.3])

    # --- Heatmap
    with row3_map:
        st.subheader("Air Quality Heat Map")
        try:
            map_img = Image.open(r"C:\Users\User\Desktop\DASHBOARD\ortigas_dashboard\map.png")
            sectors = ["A1","A2","A3","B1","B2","B3","C1","C2","C3"]
            rows = [0,0,0,1,1,1,2,2,2]
            cols = [0,1,2,0,1,2,0,1,2]
            if situation=="Normal": sector_aqi = np.random.randint(40,60,len(sectors))
            elif situation=="Heatwave": sector_aqi = np.random.randint(50,80,len(sectors))
            elif situation=="Flood": sector_aqi = np.random.randint(30,60,len(sectors))
            else: sector_aqi = np.random.randint(150,300,len(sectors))

            fig_map = go.Figure()
            fig_map.add_layout_image(dict(source=map_img, xref="x", yref="y", x=0, y=3, sizex=3, sizey=3,
                                          sizing="stretch", opacity=1, layer="below"))
            for i, aqi in enumerate(sector_aqi):
                if aqi<=50: color="Green"
                elif aqi<=100: color="Yellow"
                elif aqi<=150: color="Orange"
                elif aqi<=200: color="Red"
                elif aqi<=300: color="Purple"
                else: color="Maroon"
                fig_map.add_shape(type="rect", x0=cols[i], y0=2-rows[i], x1=cols[i]+1, y1=3-rows[i],
                                  line=dict(color="black", width=3), fillcolor=color, opacity=0.5)
                fig_map.add_annotation(x=cols[i]+0.5, y=2-rows[i]+0.5,
                                       text=f"{sectors[i]}<br>{aqi}", showarrow=False,
                                       font=dict(color="black", size=12))
            fig_map.update_xaxes(visible=False, range=[0,3])
            fig_map.update_yaxes(visible=False, range=[0,3])
            fig_map.update_layout(width=600, height=600, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_map, use_container_width=True)
        except:
            st.error("Map image not found.")

    # --- Hourly Temperature Trend
    with row3_hour:
        st.subheader("Hourly Temperature Trend")
        hours = np.arange(24)
        temp_variation = temp_value + np.random.normal(0,1,30)
        fig_hour_temp = go.Figure()
        fig_hour_temp.add_trace(go.Scatter(x=hours, y=temp_variation, mode='lines+markers'))
        fig_hour_temp.update_layout(height=260, margin=dict(l=10,r=10,t=30,b=10))
        st.plotly_chart(fig_hour_temp, use_container_width=True)

        st.subheader("Hourly AQI Trend")
        aqi_variation = aqi_value + np.random.normal(0,5,24)
        fig_hour_aqi = go.Figure()
        fig_hour_aqi.add_trace(go.Scatter(x=hours, y=aqi_variation, mode='lines+markers'))
        fig_hour_aqi.update_layout(height=260, margin=dict(l=10,r=10,t=30,b=10))
        st.plotly_chart(fig_hour_aqi, use_container_width=True)

# ==============================
# ROW 4: WEEKLY TRENDS
# ==============================
if role in ["City Planner"]:
    st.divider()
    row4_col1, row4_col2 = st.columns(2)
    with row4_col1:
        st.subheader("Weekly Temperature")
        temp_week = temp_value + np.random.normal(0,1.5,7)
        fig_week_temp = go.Figure()
        fig_week_temp.add_trace(go.Bar(x=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], y=temp_week))
        fig_week_temp.update_layout(height=260, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_week_temp, use_container_width=True)
    with row4_col2:
        st.subheader("Weekly AQI")
        aqi_week = aqi_value + np.random.normal(0,5,7)
        fig_week_aqi = go.Figure()
        fig_week_aqi.add_trace(go.Bar(x=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], y=aqi_week))
        fig_week_aqi.update_layout(height=260, margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_week_aqi, use_container_width=True)

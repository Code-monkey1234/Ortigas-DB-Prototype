import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(layout="wide", page_title="System Health Dashboard")
st.title("SYSTEM HEALTH DASHBOARD")
st.divider()


# ==============================
# SESSION STATE FOR ACTUATORS
# ==============================
if "act_purifier" not in st.session_state:
    st.session_state.act_purifier = False
if "act_dehumidifier" not in st.session_state:
    st.session_state.act_dehumidifier = False
if "act_flood_pumps" not in st.session_state:
    st.session_state.act_flood_pumps = 0  # 0=off,1=low,2=medium,3=high

# ==============================
# SIMULATED ENVIRONMENT VALUES
# ==============================
def simulate_environment():
    temp = 28 + np.random.normal(0, 1)
    humidity = 65 + np.random.normal(0, 5)
    aqi = 40 + np.random.normal(0, 10)
    flood_tank_max = 5000
    flood_tank_current = 3200 - st.session_state.act_flood_pumps*300
    return temp, humidity, aqi, flood_tank_current, flood_tank_max

temp_value, humidity_value, aqi_value, flood_tank_current, flood_tank_max = simulate_environment()

# ==============================
# HEALTH SCORE LOGIC
# ==============================
def calculate_health_score():
    score = 100
    score -= 15 if not st.session_state.act_purifier else 0
    score -= 15 if not st.session_state.act_dehumidifier else 0
    score -= 20 if st.session_state.act_flood_pumps == 0 else 0
    score -= 15 if not (20 <= temp_value <= 30) else 0
    score -= 15 if not (40 <= humidity_value <= 70) else 0
    score -= 20 if aqi_value > 100 else 0
    return max(score, 0)

health_score = calculate_health_score()

# Health color and status
def health_status(score):
    if score >= 80: return "GOOD", "#4CAF50"
    elif score >= 50: return "WARNING", "#FFC107"
    else: return "CRITICAL", "#F44336"

status_text, status_color = health_status(health_score)

# ==============================
# ACTUATOR STATUS MODULE
# ==============================
st.subheader("Actuator Status")
col1, col2, col3 = st.columns(3)

def actuator_card(column, name, active):
    color = "#4CAF50" if active else "#F44336"
    status = "ACTIVE" if active else "OFFLINE"
    with column:
        st.markdown(f"""
        <div style="border:2px solid {color}; padding:12px; border-radius:10px; text-align:center;">
            <h4>{name}</h4>
            <h2 style="color:{color};">{status}</h2>
        </div>
        """, unsafe_allow_html=True)

actuator_card(col1, "Air Purifier", st.session_state.act_purifier)
actuator_card(col2, "Dehumidifier", st.session_state.act_dehumidifier)

pump_level = st.session_state.act_flood_pumps
pump_levels = {0:"OFF",1:"LOW",2:"MEDIUM",3:"HIGH"}
pump_colors = {0:"#F44336",1:"#FFC107",2:"#2196F3",3:"#4CAF50"}

with col3:
    st.markdown(f"""
        <div style="border:2px solid {pump_colors[pump_level]}; padding:12px; border-radius:10px; text-align:center;">
            <h4>Flood Pumps</h4>
            <h2 style="color:{pump_colors[pump_level]};">{pump_levels[pump_level]}</h2>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ==============================
# ALERTS
# ==============================
st.subheader("System Alerts")
if health_score < 50:
    st.error("⚠️ System critical! Immediate action required.")
elif health_score < 80:
    st.warning("⚠️ Some metrics outside ideal range. Monitor system.")
else:
    st.success("✅ All systems within optimal range.")


# ==============================
# OVERALL SYSTEM HEALTH MODULE
# ==============================
st.subheader("Overall System Health")
st.markdown(f"""
<div style="border:2px solid {status_color}; padding:15px; border-radius:12px; text-align:center;">
    <h2 style="color:{status_color};">{status_text}</h2>
    <h3 style="color:{status_color};">{health_score}%</h3>
</div>
""", unsafe_allow_html=True)

# ==============================
# REAL-TIME GAUGE METRICS
# ==============================
st.subheader("Key System Metrics")
col_temp, col_hum, col_aqi, col_tank = st.columns(4)

def gauge(column, value, title, max_value, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        gauge={'axis':{'range':[0,max_value]}, 'bar':{'color':color}},
        title={'text':title}
    ))
    fig.update_layout(height=250)
    st.plotly_chart(fig, use_container_width=True)

with col_temp:
    gauge(col_temp, temp_value, "Temperature °C", 50, "orange")
with col_hum:
    gauge(col_hum, humidity_value, "Humidity %", 100, "blue")
with col_aqi:
    gauge(col_aqi, aqi_value, "AQI", 300, "green")
with col_tank:
    gauge(col_tank, flood_tank_current, "Flood Tank L", flood_tank_max, "blue")

st.divider()

# ==============================
# HISTORICAL DATA MODULE
# ==============================
st.subheader("Historical Trends (Simulated)")
hours = [datetime.now() - timedelta(hours=i) for i in reversed(range(24))]
temp_history = [28 + np.random.normal(0,1) for _ in range(24)]
humidity_history = [65 + np.random.normal(0,5) for _ in range(24)]
aqi_history = [40 + np.random.normal(0,10) for _ in range(24)]

fig_hist = go.Figure()
fig_hist.add_trace(go.Scatter(x=hours, y=temp_history, mode="lines+markers", name="Temp °C"))
fig_hist.add_trace(go.Scatter(x=hours, y=humidity_history, mode="lines+markers", name="Humidity %"))
fig_hist.add_trace(go.Scatter(x=hours, y=aqi_history, mode="lines+markers", name="AQI"))
fig_hist.update_layout(xaxis_title="Time", yaxis_title="Value", template="plotly_white", height=400)
st.plotly_chart(fig_hist, use_container_width=True)


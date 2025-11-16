import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import uuid

st.set_page_config(layout="wide", page_title="Home Dashboard")
st.title("Home Dashboard")
st.divider()



# ==========================================
# SIMULATED REAL-TIME ENVIRONMENT DATA
# ==========================================
env_temp = 28 + np.random.normal(0, 1, 24)
env_humidity = 60 + np.random.normal(0, 5, 24)
env_aqi = 75 + np.random.normal(0, 10, 24)
hours = [datetime.now() - timedelta(hours=i) for i in reversed(range(24))]

# Waste (weekly trend)
days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
waste_avg_fill = 70 + np.random.randint(-10, 10, size=7)
overflow_alerts = 2
trucks_active = 4

# System Health (historic)
cpu_load = 55 + np.random.randint(-5,5,24)
memory_usage = 65 + np.random.randint(-5,5,24)
uptime_days = 120

# Citizen Feedback (weekly)
total_feedback = np.random.randint(100,200,7)
avg_satisfaction = 78 + np.random.randint(-5,5,7)
avg_response_days = 3 + np.random.randint(-1,1,7)

# ==========================================
# ALERTS & HIGHLIGHTS
# ==========================================
st.subheader("Alerts & Highlights")
alerts = []
if env_aqi[-1] > 100: alerts.append("⚠️ AQI critically high!")
if waste_avg_fill[-1] > 80: alerts.append("⚠️ Waste overflow risk!")
if cpu_load[-1] > 85: alerts.append("⚠️ CPU load high!")
if memory_usage[-1] > 85: alerts.append("⚠️ Memory usage high!")

if alerts:
    for a in alerts: st.error(a)
else:
    st.success("✅ All systems operating within normal parameters.")



# ==========================================
# ROW 1 — ENVIRONMENT CHARTS
# ==========================================
st.subheader("Environment Overview")
env_col1, env_col2, env_col3 = st.columns(3)

with env_col1:
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(x=hours, y=env_temp, mode='lines+markers', name='Temperature', line=dict(color='orange')))
    fig_temp.update_layout(title="Temperature (°C) - Last 24h", xaxis_title="Time", yaxis_title="°C", height=300)
    st.plotly_chart(fig_temp, use_container_width=True)

with env_col2:
    fig_hum = go.Figure()
    fig_hum.add_trace(go.Scatter(x=hours, y=env_humidity, mode='lines+markers', name='Humidity', line=dict(color='blue')))
    fig_hum.update_layout(title="Humidity (%) - Last 24h", xaxis_title="Time", yaxis_title="%", height=300)
    st.plotly_chart(fig_hum, use_container_width=True)

with env_col3:
    fig_aqi = go.Figure()
    fig_aqi.add_trace(go.Scatter(x=hours, y=env_aqi, mode='lines+markers', name='AQI', line=dict(color='green')))
    fig_aqi.update_layout(title="Air Quality Index - Last 24h", xaxis_title="Time", yaxis_title="AQI", height=300)
    st.plotly_chart(fig_aqi, use_container_width=True)

# ==========================================
# ROW 2 — WASTE TREND
# ==========================================
st.divider()
st.subheader("Waste Management Trend")
fig_waste = go.Figure()
fig_waste.add_trace(go.Bar(x=days, y=waste_avg_fill, name="Average Fill %", marker_color="orange"))
fig_waste.add_trace(go.Scatter(x=days, y=[80]*7, mode='lines', name='Threshold', line=dict(color='red', dash='dash')))
fig_waste.update_layout(title="Waste Bin Fill Trend (Week)", yaxis_title="Fill %", height=350)
st.plotly_chart(fig_waste, use_container_width=True)

# ==========================================
# ROW 3 — SYSTEM HEALTH
# ==========================================
st.divider()
st.subheader("System Health Overview")
sys_col1, sys_col2 = st.columns(2)

with sys_col1:
    fig_cpu = go.Figure()
    fig_cpu.add_trace(go.Scatter(x=hours, y=cpu_load, mode='lines', name='CPU Load', line=dict(color='purple')))
    fig_cpu.update_layout(title="CPU Load (%) - Last 24h", yaxis_title="%", height=300)
    st.plotly_chart(fig_cpu, use_container_width=True)

with sys_col2:
    fig_mem = go.Figure()
    fig_mem.add_trace(go.Scatter(x=hours, y=memory_usage, mode='lines', name='Memory Usage', line=dict(color='darkblue')))
    fig_mem.update_layout(title="Memory Usage (%) - Last 24h", yaxis_title="%", height=300)
    st.plotly_chart(fig_mem, use_container_width=True)

# ==========================================
# ROW 4 — CITIZEN FEEDBACK
# ==========================================
st.divider()
st.subheader("Citizen Feedback Trends")
feed_col1, feed_col2 = st.columns(2)

with feed_col1:
    fig_feedback = go.Figure()
    fig_feedback.add_trace(go.Bar(x=days, y=total_feedback, name="Total Feedback", marker_color="green"))
    fig_feedback.update_layout(title="Total Feedback Received (Week)", yaxis_title="Number of Feedbacks", height=300)
    st.plotly_chart(fig_feedback, use_container_width=True)

with feed_col2:
    fig_satisfaction = go.Figure()
    fig_satisfaction.add_trace(go.Scatter(x=days, y=avg_satisfaction, mode='lines+markers', name="Satisfaction", line=dict(color='lime')))
    fig_satisfaction.update_layout(title="Average Satisfaction (%)", yaxis_title="%", height=300)
    st.plotly_chart(fig_satisfaction, use_container_width=True)

citF_data = pd.DataFrame({
    "Sector": ["A1", "B2", "C1", "C3"],
    "Issue": ["Overflow", "Missed Pickup", "Illegal Dumping", "Overflowing"],
    "Severity": [2, 4, 3, 3],
    "Comment": [
        "Bins are full",
        "Collection missed today",
        "Someone littered",
        "Overflowing near park"
    ],
    "Timestamp": [datetime.now() - timedelta(hours=i) for i in range(4)]
})

# ============================================================
# PUSH DASHBOARD CITIZEN FEEDBACK TO ADMIN PANEL SESSION
# ============================================================
if "reports" not in st.session_state:
    st.session_state.reports = []

for _, row in citF_data.iterrows():
    # Check to avoid duplicates
    if not any(r.get("location_text") == row["Sector"] and r.get("description") == row["Comment"]
               for r in st.session_state.reports):
        st.session_state.reports.append({
            "id": str(uuid.uuid4())[:8],
            "ts": row["Timestamp"],
            "name": "Citizen",
            "category": "General Issue",
            "location_text": row["Sector"],
            "severity": ["Minor","Major","Critical"][min(max(row["Severity"]-1,0),2)],
            "description": row["Comment"],
            "status": "Submitted",
            "assigned_to": "",
            "response_time_days": None
        })


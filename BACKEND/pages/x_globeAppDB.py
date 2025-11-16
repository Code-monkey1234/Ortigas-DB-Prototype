import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import uuid
# ============================================================
# AUTO REFRESH (every 10 seconds)
# ============================================================

st_autorefresh(interval=30_000, key="refresh")


# ============================================================
# PAGE SETUP
# ============================================================
st.set_page_config(page_title="GlobeOne — City Insights", layout="wide")
st.title("GlobeOne App: City Insights Dashboard")

# ============================================================
# REWARDS SECTION
# ============================================================
st.subheader("Your Impact & Rewards")
st.markdown("""
- Report issues → earn Points  
- Conserve energy → get GlobeOne Rewards  
- Join community cleanups and events  
""")

# ============================================================
# RANDOM GENERATOR
# ============================================================
rng = np.random.default_rng(int(datetime.now().timestamp()) % (2**32 - 1))


# ============================================================
# UTILITY — METRIC WITH DELTA ARROWS
# ============================================================
def metric_with_delta(label, current, previous, unit=""):
    diff = current - previous
    if diff > 0:
        arrow = f"▲ {diff:.1f}{unit}"
    elif diff < 0:
        arrow = f"▼ {abs(diff):.1f}{unit}"
    else:
        arrow = "—"
    st.metric(label, f"{current:.1f}{unit}", arrow)


# ============================================================
# SIMULATED DATA
# ============================================================

# --- Environment ---
env_data = pd.DataFrame({
    "Hour": [f"{h}:00" for h in range(24)],
    "Temperature (°C)": rng.normal(31, 2, 24),
    "Humidity (%)": rng.normal(65, 5, 24),
    "AQI": rng.integers(30, 150, 24)
})

# --- Energy ---
ene_data = pd.DataFrame({
    "Hour": [f"{h}:00" for h in range(24)],
    "Consumption (kW)": rng.normal(500, 50, 24),
    "Renewable Share (%)": rng.normal(40, 10, 24)
})

# --- Traffic ---
traf_data = pd.DataFrame({
    "Sector": [f"{a}{b}" for a in "ABC" for b in "123"],
    "Avg Speed (km/h)": rng.integers(20, 60, 9),
    "Congestion (%)": rng.integers(30, 100, 9)
})

# --- Waste ---
waste_data = pd.DataFrame({
    "Sector": [f"{a}{b}" for a in "ABC" for b in "123"],
    "Bin Fill (%)": rng.integers(40, 120, 9),
    "Overflow Alerts": rng.integers(0, 2, 9)
})

# --- Citizen Feedback ---
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
# SESSION STATE FOR DELTAS
# ============================================================
if "prev" not in st.session_state:
    st.session_state.prev = {}

def get_prev(key, value):
    if key not in st.session_state.prev:
        st.session_state.prev[key] = value
    old = st.session_state.prev[key]
    st.session_state.prev[key] = value
    return old


# ============================================================
# ALERT SYSTEM
# ============================================================
def check_alerts():
    alerts = []

    if env_data["Temperature (°C)"].iloc[-1] > 35:
        alerts.append("High temperature detected — stay hydrated.")

    if env_data["AQI"].iloc[-1] > 100:
        alerts.append("Unhealthy air quality — wear a mask. Sensitive groups: pregnant women, seniors, infants, respiratory issues.")

    if waste_data["Bin Fill (%)"].max() > 100:
        alerts.append("Waste overflow detected.")

    if traf_data["Congestion (%)"].max() > 90:
        alerts.append("Heavy traffic detected — reroute recommended.")

    return alerts

for alert in check_alerts():
    st.warning(alert)

st.divider()

# ============================================================
# ENVIRONMENT SECTION
# ============================================================
st.subheader("Environment")

current_temp = env_data["Temperature (°C)"].iloc[-1]
current_hum = env_data["Humidity (%)"].iloc[-1]
current_aqi = env_data["AQI"].iloc[-1]

col1, col2, col3 = st.columns(3)
with col1:
  metric_with_delta("Temperature", current_temp, get_prev("temp", current_temp), "°C")
with col2:
  metric_with_delta("Humidity", current_hum, get_prev("hum", current_hum), "%")
with col3:
  metric_with_delta("AQI", current_aqi, get_prev("aqi", current_aqi), "")

fig_env = go.Figure()
fig_env.add_trace(go.Scatter(x=env_data["Hour"], y=env_data["Temperature (°C)"], name="Temperature"))
fig_env.add_trace(go.Scatter(x=env_data["Hour"], y=env_data["Humidity (%)"], name="Humidity"))
fig_env.add_trace(go.Scatter(x=env_data["Hour"], y=env_data["AQI"], name="AQI"))
fig_env.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))

st.plotly_chart(fig_env, use_container_width=True)
st.divider()

# ============================================================
# ENERGY SECTION
# ============================================================
st.subheader("Energy")

current_cons = ene_data["Consumption (kW)"].iloc[-1]
current_ren = ene_data["Renewable Share (%)"].iloc[-1]

col1, col2 = st.columns(2)
with col1:
  metric_with_delta("Consumption", current_cons, get_prev("cons", current_cons), " kW")
with col2:
  metric_with_delta("Renewable Share", current_ren, get_prev("ren", current_ren), "%")

fig_energy = go.Figure()
fig_energy.add_trace(go.Bar(x=ene_data["Hour"], y=ene_data["Consumption (kW)"], name="Consumption"))
fig_energy.add_trace(go.Scatter(x=ene_data["Hour"], y=ene_data["Renewable Share (%)"], name="Renewables", yaxis="y2"))
fig_energy.update_layout(
    yaxis=dict(title="Consumption (kW)"),
    yaxis2=dict(title="Renewables (%)", overlaying="y", side="right"),
    height=300, margin=dict(l=20, r=20, t=30, b=20)
)
st.plotly_chart(fig_energy, use_container_width=True)
st.divider()

# ============================================================
# TRAFFIC SECTION
# ============================================================
st.subheader("Traffic")

fig_traffic = go.Figure()
fig_traffic.add_trace(go.Bar(x=traf_data["Sector"], y=traf_data["Congestion (%)"], name="Congestion"))
fig_traffic.add_trace(go.Scatter(x=traf_data["Sector"], y=traf_data["Avg Speed (km/h)"], name="Speed", yaxis="y2"))
fig_traffic.update_layout(
    yaxis=dict(title="Congestion (%)"),
    yaxis2=dict(title="Avg Speed (km/h)", overlaying="y", side="right"),
    height=300, margin=dict(l=20, r=20, t=30, b=20)
)
st.plotly_chart(fig_traffic, use_container_width=True)
st.divider()

# ============================================================
# WASTE SECTION
# ============================================================
st.subheader("Waste Management")

fig_waste = go.Figure()
fig_waste.add_trace(go.Bar(x=waste_data["Sector"], y=waste_data["Bin Fill (%)"], name="Bin Fill"))
fig_waste.add_trace(go.Scatter(x=waste_data["Sector"], y=waste_data["Overflow Alerts"], name="Alerts", yaxis="y2"))
fig_waste.update_layout(
    yaxis=dict(title="Bin Fill (%)"),
    yaxis2=dict(title="Alerts", overlaying="y", side="right"),
    height=300, margin=dict(l=20, r=20, t=30, b=20)
)
st.plotly_chart(fig_waste, use_container_width=True)

st.divider()
# ===========================
# TABS: Add a Submit Feedback Tab
# ===========================
tab1, tab2 = st.tabs(["Dashboard", "Submit Feedback"])

# -----------------------------
# Tab 1: Keep dashboard
# -----------------------------
with tab1:
    st.subheader("Citizen Feedback")
    # Merge existing static data with submitted feedback from session_state
    all_feedback = citF_data.copy()
    if "appDB" in st.session_state and st.session_state.appDB:
        extra_feedback = pd.DataFrame(st.session_state.appDB)
        all_feedback = pd.concat([all_feedback, extra_feedback], ignore_index=True)
    st.dataframe(all_feedback.sort_values(by="Timestamp", ascending=False), use_container_width=True)

# -----------------------------
# Tab 2: Form for citizens
# -----------------------------
with tab2:
    st.subheader("Submit a New Feedback")
    
    if "reports" not in st.session_state:
        st.session_state.reports = []

    with st.form("feedback_form", clear_on_submit=True):
        sector = st.selectbox("Sector", ["A1","A2","A3","B1","B2","B3","C1","C2","C3"])
        issue_type = st.selectbox("Issue Type", ["Overflow","Missed Pickup","Illegal Dumping","Other"])
        severity = st.slider("Severity (1=Minor, 5=Critical)", 1, 5, 2)
        comment = st.text_area("Describe the issue")
        submitted = st.form_submit_button("Submit Feedback")

        if submitted:
            # Convert numeric severity to string for admin
            severity_str = ["Minor","Minor","Major","Major","Critical"][severity-1]
            
            st.session_state.reports.append({
                "id": str(uuid.uuid4())[:8],
                "ts": datetime.now(),
                "name": "Citizen",
                "category": issue_type,
                "location_text": sector,
                "severity": severity_str,
                "description": comment,
                "status": "Submitted",
                "assigned_to": "",
                "response_time_days": None
            })
            st.success("✅ Feedback submitted successfully!")

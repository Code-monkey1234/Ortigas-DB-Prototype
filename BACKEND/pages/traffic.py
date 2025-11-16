import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
import time
from datetime import datetime

# ==============================
# PAGE LAYOUT
# ==============================
st.set_page_config(layout="wide")
st.title("TRAFFIC DASHBOARD")
st.divider()

# ==============================
# SESSION STATE (history, reports)
# ==============================
if "traffic_history" not in st.session_state:
    # store last 24 aggregate congestion values and per-sector loads
    st.session_state.traffic_history = []  # list of dicts {ts, avg_cong, sector_loads(list9), incidents}
if "citizen_reports" not in st.session_state:
    # example persisted citizen reports
    st.session_state.citizen_reports = [
        {"id": 1, "sector": "A1", "issue": "Accident", "severity": 4, "comment": "Multi-car crash", "ts": datetime.now()},
        {"id": 2, "sector": "B2", "issue": "Heavy Traffic", "severity": 2, "comment": "Slow moving", "ts": datetime.now()},
        {"id": 3, "sector": "C3", "issue": "Road Hazard", "severity": 3, "comment": "Debris on road", "ts": datetime.now()}
    ]
    st.session_state.next_report_id = 4

# ==============================
# SIDEBAR: Controls + Citizen Input
# ==============================
with st.sidebar:
    st.header("⚙ Traffic Control Panel")

    # Situation
    situation = st.selectbox("Situation Mode", [
        "Normal",
        "Rush Hour",
        "Accident/Incident",
        "Road Construction"
    ])

    st.write("---")
    st.subheader("Manual Overrides")
    green_light_boost = st.slider("Traffic Light Optimization (%)", 0, 50, 0)
    lane_closure = st.slider("Closed Lanes Impact (%)", 0, 50, 0)
    emergency_reroute = st.checkbox("Enable Emergency Rerouting")

    st.write("---")
    st.subheader("Fusion Weights (sensor vs citizen vs incidents)")
    weight_sensor = st.slider("Sensor Weight", 0.0, 1.0, 0.6, 0.05)
    weight_citizen = st.slider("Citizen Reports Weight", 0.0, 1.0, 0.3, 0.05)
    weight_incident = st.slider("Incident Weight", 0.0, 1.0, 0.1, 0.05)

    # Make sure weights sum to 1-ish visually (no enforcement necessary)
    st.caption(f"Sum of weights: {weight_sensor + weight_citizen + weight_incident:.2f}")

    st.write("---")
    st.subheader("Citizen Reports (Filter & Add)")
    issues_to_show = st.multiselect("Show Issues", ["Accident", "Heavy Traffic", "Road Hazard"], default=["Accident","Heavy Traffic","Road Hazard"])
    severity_threshold = st.slider("Minimum Severity to Display", 1, 5, 1)

    st.write("Add a report (simulated citizen input):")
    new_sector = st.selectbox("Sector", ["A1","A2","A3","B1","B2","B3","C1","C2","C3"], index=4)
    new_issue = st.selectbox("Issue Type", ["Accident","Heavy Traffic","Road Hazard"])
    new_severity = st.slider("Severity", 1, 5, 3)
    new_comment = st.text_input("Comment (optional)","")
    if st.button("Submit Report"):
        st.session_state.citizen_reports.append({
            "id": st.session_state.next_report_id,
            "sector": new_sector,
            "issue": new_issue,
            "severity": new_severity,
            "comment": new_comment,
            "ts": datetime.now()
        })
        st.session_state.next_report_id += 1
        st.success("Report added (simulated).")

    st.write("---")
    st.subheader("Simulation Options")
    simulate_new_step = st.checkbox("Simulate new timestep (append history)", value=True)
    map_img_path = st.text_input("Map image path (optional)", value=r"C:\Users\User\Desktop\DASHBOARD\ortigas_dashboard\map.png")

# ==============================
# SIMULATION: base KPI values by situation
# ==============================
def simulate_base_traffic(situation):
    # returns baseline avg congestion percentage, base sector multiplier, base incidents
    if situation == "Normal":
        avg_cong = np.random.randint(35, 55)
        base_sector = 0.8
        incidents = np.random.randint(0, 2)
    elif situation == "Rush Hour":
        avg_cong = np.random.randint(60, 85)
        base_sector = 1.2
        incidents = np.random.randint(0, 3)
    elif situation == "Accident/Incident":
        avg_cong = np.random.randint(55, 90)
        base_sector = 1.1
        incidents = np.random.randint(1, 4)
    else:  # Road Construction
        avg_cong = np.random.randint(50, 80)
        base_sector = 1.0
        incidents = np.random.randint(0, 2)
    return float(avg_cong), float(base_sector), int(incidents)

base_avg_cong, base_sector_multiplier, base_incidents = simulate_base_traffic(situation)

# ==============================
# Generate per-sector sensor loads (simulated) and incorporate lane_closure/green_light_boost
# ==============================
sectors = ["A1","A2","A3","B1","B2","B3","C1","C2","C3"]
rows = [0,0,0,1,1,1,2,2,2]
cols = [0,1,2,0,1,2,0,1,2]

# generate base vehicle load per sector influenced by avg congestion and base_sector_multiplier
base_load = base_avg_cong * 6  # scale factor to get vehicle numbers per sector
np_random_seed = int(time.time()) % (2**32 - 1)
rng = np.random.default_rng(np_random_seed)
vehicle_load = rng.integers(low=max(50, int(base_load-80)), high=int(base_load+80), size=len(sectors)).astype(float)

# Apply lane_closure: randomly pick sectors to penalize
if lane_closure > 0:
    # convert lane_closure% to multiplier for some sectors
    closed_count = int(np.clip(np.round(lane_closure/20), 0, 3))  # 0..3 closed sectors influenced
    if closed_count > 0:
        closed_sectors_idx = rng.choice(len(sectors), size=closed_count, replace=False)
        for idx in closed_sectors_idx:
            vehicle_load[idx] *= (1 + lane_closure/100)  # increase load due to closure

# Apply green_light_boost improvement (reduce loads)
if green_light_boost > 0:
    vehicle_load *= np.clip(1 - green_light_boost/100, 0.5, 1.0)

# Emergency reroute effect reduces some sector loads randomly
if emergency_reroute:
    reroute_idx = rng.choice(len(sectors), size=2, replace=False)
    for idx in reroute_idx:
        vehicle_load[idx] *= 0.85  # 15% reduction from reroute

# ==============================
# Integrate Citizen Reports into sector scores
# ==============================
# Filter reports shown based on sidebar control
filtered_reports = [r for r in st.session_state.citizen_reports if r["issue"] in issues_to_show and r["severity"] >= severity_threshold]

# count reports per sector and accumulate severity per sector
report_count = {s:0 for s in sectors}
report_severity_sum = {s:0 for s in sectors}
incident_count_from_reports = 0
for r in st.session_state.citizen_reports:
    sec = r["sector"]
    if sec in report_count:
        report_count[sec] += 1
        report_severity_sum[sec] += r["severity"]
    # treat Accident as an incident contributor
    if r["issue"] == "Accident" and r["severity"] >= 3:
        incident_count_from_reports += 1

# Build sector_score: normalized sensor load (0..1), normalized citizen severity (0..1), incident presence
# Normalization helpers
max_sensor = max(1.0, vehicle_load.max())
sensor_norm = vehicle_load / max_sensor  # 0..1

# citizen_norm: severity sum per sector divided by (max possible severity per sector)
max_possible_severity = 5 * 5  # assume up to 5 reports each severity 5 as a rough cap
citizen_norm = np.array([report_severity_sum[s]/max_possible_severity for s in sectors])

# incidents_norm: 1 if at least one severe accident report exists in sector else 0
incidents_norm = np.array([1.0 if any((r["sector"]==s and r["issue"]=="Accident" and r["severity"]>=3) for r in st.session_state.citizen_reports) else 0.0 for s in sectors])

# Fusion model per sector
sector_scores = (weight_sensor * sensor_norm) + (weight_citizen * citizen_norm) + (weight_incident * incidents_norm)
# Map sector_scores to a 0..100 congestion proxy per sector
sector_congestion_pct = np.clip(sector_scores * 120, 0, 200)  # allow high values for localized spikes

# Aggregate KPIs derived from sector scores
agg_avg_congestion = float(np.mean(sector_congestion_pct))
agg_peak_load = float(np.max(vehicle_load))
agg_incidents = int(base_incidents + incident_count_from_reports)

# Small smoothing using base_avg_cong to keep semi-realistic continuity
avg_congestion = (agg_avg_congestion * 0.8) + (base_avg_cong * 0.2)

# Ensure types
avg_congestion = float(np.clip(avg_congestion, 0, 200))
peak_load = float(np.clip(agg_peak_load, 0, 2000))
incidents_count = int(np.clip(agg_incidents, 0, 50))

# Append to history if simulate_new_step checked
if simulate_new_step:
    st.session_state.traffic_history.append({
        "ts": datetime.now(),
        "avg_congestion": avg_congestion,
        "sector_loads": sector_congestion_pct.tolist(),
        "incidents": incidents_count
    })
    # keep last 24
    st.session_state.traffic_history = st.session_state.traffic_history[-24:]

# Build a simple DataFrame for last 24 hours (or steps)
history_df = pd.DataFrame([{
    "ts": rec["ts"],
    "avg_congestion": rec["avg_congestion"],
    "incidents": rec["incidents"]
} for rec in st.session_state.traffic_history])

# ==============================
# TOP KPI BOXES
# ==============================
kpi_cols = st.columns(3)

def kpi_box(column, title, value, unit="", color="#4CAF50"):
    with column:
        st.markdown(
            f"""
            <div style="border:2px solid {color}; padding:15px; border-radius:10px; text-align:center;">
                <h3 style="margin-bottom:5px;">{title}</h3>
                <h1 style="margin-top:0; margin-bottom:10px;">{value:.0f}{unit}</h1>
            </div>
            """,
            unsafe_allow_html=True
        )

kpi_box(kpi_cols[0], "Avg Congestion", avg_congestion, "%", "#FFC107")
kpi_box(kpi_cols[1], "Peak Road Load (sample)", peak_load, " veh/hr", "#FF9800")
kpi_box(kpi_cols[2], "Incidents (est.)", incidents_count, "", "#F44336")

# ==============================
# STATUS ALERTS
# ==============================
st.subheader("Traffic Alerts / Status")
alerts = []
if avg_congestion < 50:
    alerts.append("Traffic is flowing smoothly.")
elif avg_congestion < 85:
    alerts.append("Moderate congestion. Monitor critical sectors.")
else:
    alerts.append("Heavy congestion! Consider rerouting or traffic controls.")

if incidents_count > 0:
    alerts.append(f"{incidents_count} incident(s) estimated (including citizen reports).")

if lane_closure > 0:
    alerts.append(f"Lane closures impacting traffic by ~{lane_closure}%.")

for alert in alerts:
    st.info(alert)

st.divider()

# ==============================
# TRAFFIC HEAT MAP (with citizen overlays)
# ==============================
heat_map_col, color_guide = st.columns(2)
with heat_map_col:
    st.subheader("Traffic Heat Map (Sensor + Citizen Fusion)")
    try:
        map_img = Image.open(map_img_path) if map_img_path else None
    except:
        map_img = None

    fig_map = go.Figure()

    # add background map if exists
    if map_img is not None:
        fig_map.add_layout_image(
            dict(source=map_img, xref="x", yref="y", x=0, y=3, sizex=3, sizey=3,
                 sizing="stretch", opacity=1, layer="below"))

    # draw sector rectangles and annotations based on sector_congestion_pct and vehicle_load
    for i, s in enumerate(sectors):
        load = sector_congestion_pct[i]
        # color mapping
        if load < 60:
            color = "green"
        elif load < 85:
            color = "yellow"
        elif load < 120:
            color = "orange"
        else:
            color = "red"
        fig_map.add_shape(
            type="rect",
            x0=cols[i], y0=2-rows[i], x1=cols[i]+1, y1=3-rows[i],
            line=dict(color="black", width=2),
            fillcolor=color,
            opacity=0.55
        )
        # annotation shows sector name and computed load (veh or %)
        fig_map.add_annotation(
            x=cols[i]+0.5, y=2-rows[i]+0.5,
            text=f"{s}<br>{int(load)}%",
            showarrow=False,
            font=dict(color="black", size=11)
        )

    # overlay citizen reports (filtered)
    sector_coords = {s:(c,r) for s,c,r in zip(sectors, cols, rows)}
    for r in filtered_reports:
        x, y = sector_coords[r["sector"]]
        y_plot = 2 - y  # invert row index to match plot y orientation
        issue_color = {"Accident":"red","Heavy Traffic":"orange","Road Hazard":"blue"}.get(r["issue"], "purple")
        marker_size = r["severity"] * 10 + 8
        # add marker trace per report
        fig_map.add_trace(go.Scatter(
            x=[x+0.5], y=[y_plot+0.5],
            mode="markers+text",
            marker=dict(size=marker_size, color=issue_color, opacity=0.8, line=dict(color="black", width=1)),
            text=[f"{r['issue']} ({r['severity']})"],
            textposition="top center",
            hovertemplate=f"Sector: {r['sector']}<br>Issue: {r['issue']}<br>Severity: {r['severity']}<br>Comment: {r.get('comment','')}",
            showlegend=False
        ))

    fig_map.update_xaxes(visible=False, range=[0,3])
    fig_map.update_yaxes(visible=False, range=[0,3])
    fig_map.update_layout(height=450, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_map, use_container_width=True)

with color_guide:
    st.subheader("Heat Map Color Guide")
    st.markdown("""
    <div style="display:flex; gap:10px; flex-direction:column;">
      <div style="display:flex; gap:10px;">
        <div style="background-color:green; width:80px; height:28px; text-align:center; color:white; line-height:28px;">Low (&lt;60%)</div>
        <div style="background-color:yellow; width:120px; height:28px; text-align:center; color:purple; line-height:28px;">Moderate (60-84%)</div>
        <div style="background-color:orange; width:120px; height:28px; text-align:center; color:white; line-height:28px;">Elevated (85-119%)</div>
        <div style="background-color:red; width:80px; height:28px; text-align:center; color:white; line-height:28px;">Critical (≥120%)</div>
      </div>
      <p style='font-size:12px; margin-top:8px;'>Citizen markers: size ~ severity, color = issue type. Hover markers for details.</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ==============================
# TRENDS: Hourly & Weekly (use history_df if available)
# ==============================
trend_cols = st.columns(2)

# Hourly / recent history (last up to 24 steps)
with trend_cols[0]:
    st.subheader("Avg Congestion - Recent Steps (last 24)")
    if len(st.session_state.traffic_history) > 0:
        df_hist = pd.DataFrame([{"ts": rec["ts"], "avg_congestion": rec["avg_congestion"]} for rec in st.session_state.traffic_history])
        df_hist['label'] = df_hist['ts'].dt.strftime("%H:%M:%S")
        fig_24h = go.Figure()
        fig_24h.add_trace(go.Scatter(
            x=df_hist['label'], y=df_hist['avg_congestion'],
            mode="lines+markers", name="Avg Congestion"
        ))
        fig_24h.update_layout(xaxis_title="Time", yaxis_title="Congestion (%)", height=400)
        st.plotly_chart(fig_24h, use_container_width=True)
    else:
        # fallback simulated line if no history
        hours = [f"{h}:00" for h in range(24)]
        congestion_24h = np.clip(np.random.normal(base_avg_cong, 5, 24), 0, 200)
        fig_24h = go.Figure()
        fig_24h.add_trace(go.Scatter(x=hours, y=congestion_24h, mode="lines+markers"))
        fig_24h.update_layout(xaxis_title="Hour", yaxis_title="Congestion (%)", height=400)
        st.plotly_chart(fig_24h, use_container_width=True)

# Weekly (simulated but influenced by base_avg_cong)
with trend_cols[1]:
    st.subheader("Avg Congestion - Last 7 Days (simulated)")
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    congestion_week = np.clip(np.random.normal(base_avg_cong, 6, 7), 0, 200)
    fig_week = go.Figure()
    fig_week.add_trace(go.Bar(x=days, y=congestion_week, marker_color="crimson"))
    fig_week.update_layout(xaxis_title="Day", yaxis_title="Congestion (%)", height=400)
    st.plotly_chart(fig_week, use_container_width=True)

st.divider()

# ==============================
# Citizen Reports Table & Controls
# ==============================
st.subheader("Citizen Reports (All)")
reports_df = pd.DataFrame([{
    "id": r["id"],
    "ts": r["ts"].strftime("%Y-%m-%d %H:%M:%S"),
    "sector": r["sector"],
    "issue": r["issue"],
    "severity": r["severity"],
    "comment": r.get("comment","")
} for r in st.session_state.citizen_reports])

# Allow deletion of a report (simulate moderation)
col1, col2 = st.columns([2,1])
with col1:
    st.dataframe(reports_df.sort_values(by="ts", ascending=False), use_container_width=True)
with col2:
    st.write("Moderation")
    remove_id = st.number_input("Remove report id (enter id)", min_value=0, step=1, value=0)
    if st.button("Remove Report"):
        before = len(st.session_state.citizen_reports)
        st.session_state.citizen_reports = [r for r in st.session_state.citizen_reports if r["id"] != remove_id]
        after = len(st.session_state.citizen_reports)
        if after < before:
            st.success(f"Removed report id {remove_id}")
        else:
            st.info("No report with that id.")

st.divider()

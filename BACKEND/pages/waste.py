import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from PIL import Image
from datetime import datetime, timedelta
import random

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(page_title="Waste Management Dashboard", layout="wide")
st.title("WASTE MANAGEMENT DASHBOARD")
st.divider()

# ----------------------------
# Sector definitions
# ----------------------------
SECTORS = ["A1","A2","A3","B1","B2","B3","C1","C2","C3"]
ROWS = [0,0,0,1,1,1,2,2,2]
COLS = [0,1,2,0,1,2,0,1,2]

# Sector types: impacts base daily generation (commercial generates more)
SECTOR_TYPE = {
    "A1":"Residential","A2":"Commercial","A3":"Residential",
    "B1":"Residential","B2":"Commercial","B3":"Residential",
    "C1":"Residential","C2":"Commercial","C3":"Residential"
}
TYPE_BASE_MULT = {"Residential":1.0, "Commercial":1.6}

# ----------------------------
# Session state initialization
# ----------------------------
if "waste_history" not in st.session_state:
    # list of dicts with timestamp and sector fills (percent), trucks_active, etc.
    st.session_state.waste_history = []

if "citizen_reports" not in st.session_state:
    st.session_state.citizen_reports = [
        {"id":1, "sector":"B2", "issue":"Overflow", "severity":4, "comment":"Bins overflowing near mall", "ts":datetime.now()},
        {"id":2, "sector":"A3", "issue":"Missed Pickup", "severity":3, "comment":"No collection today", "ts":datetime.now()}
    ]
    st.session_state.next_report_id = 3

# ----------------------------
# Sidebar controls
# ----------------------------
with st.sidebar:
    st.header("⚙ Waste Management Controls")

    scenario = st.selectbox("Scenario Mode", [
        "Normal","High Waste Generation","Overflow Alerts","Maintenance Issue"
    ])

    st.write("---")
    st.subheader("Operational Overrides")
    extra_trucks = st.slider("Deploy Extra Trucks", 0, 5, 0)
    recycling_boost_pct = st.slider("Recycling Efficiency Boost (%)", 0, 50, 0)
    early_collection = st.checkbox("Schedule Early Collection (reduce hours since last collect)")

    st.write("---")
    st.subheader("Fusion Weights (Sensor / HoursSinceCollection / CitizenReports)")
    w_sensor = st.slider("Sensor Fill Weight", 0.0, 1.0, 0.6, 0.05)
    w_hours = st.slider("Hours Since Collection Weight", 0.0, 1.0, 0.25, 0.05)
    w_citizen = st.slider("Citizen Report Weight", 0.0, 1.0, 0.15, 0.05)
    st.caption(f"Sum (visual): {w_sensor + w_hours + w_citizen:.2f}")

    st.write("---")
    st.subheader("Citizen Reports (Filter & Submit)")
    issues_to_show = st.multiselect("Show issues", ["Overflow","Missed Pickup","Illegal Dumping"], default=["Overflow","Missed Pickup","Illegal Dumping"])
    severity_threshold = st.slider("Min Severity to display", 1, 5, 1)

    st.write("Submit a simulated citizen report:")
    new_sector = st.selectbox("Sector", SECTORS, index=1)
    new_issue = st.selectbox("Issue Type", ["Overflow","Missed Pickup","Illegal Dumping"])
    new_severity = st.slider("Severity", 1, 5, 3)
    new_comment = st.text_input("Comment (optional)", "")
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
        st.success("Citizen report added (simulated).")

    st.write("---")
    st.subheader("Simulation Options")
    simulate_step = st.checkbox("Simulate one timestep (append to history)", value=True)
    map_img_path = st.text_input("Map image path (optional)", value=r"C:\Users\User\Desktop\DASHBOARD\ortigas_dashboard\map.png")

# ----------------------------
# Semi-realistic generation helpers
# ----------------------------
def daily_pattern(hour):
    """Return multiplier for given hour to simulate daily waste generation curve."""
    # peak morning (7-9) and evening (17-20) for residential; commercial midday (10-16)
    if 6 <= hour <= 9:
        return 1.25
    if 17 <= hour <= 20:
        return 1.2
    if 10 <= hour <= 16:
        return 1.0
    if 0 <= hour <= 4:
        return 0.6
    return 0.8

def simulate_sector_sensor_fill(sector, base_avg_fill, hours_since_collection, hour_of_day, rng):
    """Return percent fill for sector based on base avg, sector type, hours since last collection, and noise."""
    ttype = SECTOR_TYPE.get(sector, "Residential")
    type_mult = TYPE_BASE_MULT.get(ttype, 1.0)
    # hours since collection increases fill linearly up to cap
    hours_factor = 1 + min(hours_since_collection / 24.0, 1.2)
    pattern = daily_pattern(hour_of_day)
    noise = rng.normal(0, 5)  # small noise (percent)
    fill = base_avg_fill * type_mult * hours_factor * pattern + noise
    # clamp between 0 and 200% (allow overflow >100 for critical)
    return float(np.clip(fill, 0, 200))

# ----------------------------
# Determine scenario base parameters
# ----------------------------
base_avg_fill = 55  # baseline percent
trucks_active = random.randint(3,5)
last_collection_hours = {s: random.randint(6,24) for s in SECTORS}  # hours since last collection per sector

if scenario == "High Waste Generation":
    base_avg_fill += 20
    trucks_active += 2
elif scenario == "Overflow Alerts":
    base_avg_fill += 30
elif scenario == "Maintenance Issue":
    trucks_active = max(1, trucks_active - 1)

# Extra trucks affect effective collection (reduce hours since collection)
effective_trucks = trucks_active + extra_trucks

# If early collection selected, reduce hours since collection by some value
if early_collection:
    for s in SECTORS:
        last_collection_hours[s] = max(0, last_collection_hours[s] - 8)

# Recycling efficiency (affects effective fill of recyclable portion)
recycling_efficiency = round(min(0.99, 0.3 + random.random() * 0.4 + recycling_boost_pct/100), 2)

# ----------------------------
# Map citizen reports aggregated per sector
# ----------------------------
# Filter shown reports for UI overlay, but fusion uses all reports
filtered_reports = [r for r in st.session_state.citizen_reports if r["issue"] in issues_to_show and r["severity"] >= severity_threshold]

# For fusion, compute per-sector citizen complaint score (sum severity normalized)
max_possible = 5 * 5  # rough cap: 5 reports severity 5 each
citizen_severity_sum = {s:0 for s in SECTORS}
for r in st.session_state.citizen_reports:
    if r["sector"] in citizen_severity_sum:
        citizen_severity_sum[r["sector"]] += r["severity"]

citizen_norm = np.array([citizen_severity_sum[s]/max_possible for s in SECTORS])  # 0..~1

# ----------------------------
# Build sensor fills for current timestep
# ----------------------------
hour_now = datetime.now().hour
rng = np.random.default_rng(int(datetime.now().timestamp()) % (2**32 - 1))

sector_sensor_fill = []
for s in SECTORS:
    fill = simulate_sector_sensor_fill(s, base_avg_fill, last_collection_hours[s], hour_now, rng)
    sector_sensor_fill.append(fill)

sector_sensor_fill = np.array(sector_sensor_fill)  # percent, can exceed 100

# ----------------------------
# Trucks effect: model collections reducing fills for some sectors
# naive model: each truck collects from N sectors per timestep, reducing their fill
# ----------------------------
# trucks service capacity per timestep (approx sectors handled)
# capacity: number of sectors a single truck can service in this timestep
truck_capacity_sectors = 2
capacity = effective_trucks * truck_capacity_sectors
# choose sectors with highest fills to be collected
collect_order_idx = np.argsort(-sector_sensor_fill)  # desc
collected_idx = collect_order_idx[:int(min(capacity, len(SECTORS)))]
# apply collection reduction
for idx in collected_idx:
    # collection reduces fill by a percent proportional to truck effectiveness
    reduction = 40 + rng.integers(0,20)  # reduce 40-60%
    sector_sensor_fill[idx] = max(0, sector_sensor_fill[idx] - reduction)
    last_collection_hours[SECTORS[idx]] = 0  # reset hours since collection

# non-collected sectors increase hours since last collection by 1 hour (for fusion logic)
for s in SECTORS:
    last_collection_hours[s] = min(72, last_collection_hours[s] + 1)  # cap at 72 hrs

# ----------------------------
# Fusion model: sector risk score
# SectorScore = w_sensor * sensor_norm + w_hours * hours_norm + w_citizen * citizen_norm
# We need normalized components
# ----------------------------
# sensor normalization (0..1) relative to a plausible max (200%)
sensor_norm = sector_sensor_fill / 200.0  # now 0..1

# hours normalization (0..1). Assume 0..72 mapped to 0..1
hours_norm = np.array([last_collection_hours[s]/72.0 for s in SECTORS])
hours_norm = np.clip(hours_norm, 0, 1)

# citizen_norm already computed above

# sector score
sector_score = (w_sensor * sensor_norm) + (w_hours * hours_norm) + (w_citizen * citizen_norm)
# map to 0..100 risk percent and allow weighting sensitivity
sector_risk_pct = np.clip(sector_score * 120, 0, 200)  # could exceed 100 for urgent

# ----------------------------
# Aggregate KPIs derived from sector risk / sensor fills
# ----------------------------
agg_avg_fill = float(np.mean(sector_sensor_fill))
agg_overflow_alerts = int(np.sum(sector_sensor_fill > 85))  # sectors above threshold
agg_trucks_active = effective_trucks
agg_recycling_eff = recycling_efficiency
agg_last_collection_avg = float(np.mean([last_collection_hours[s] for s in SECTORS]))

# Append to history if simulate_step checked
if simulate_step:
    st.session_state.waste_history.append({
        "ts": datetime.now(),
        "sector_sensor_fill": sector_sensor_fill.tolist(),
        "sector_risk_pct": sector_risk_pct.tolist(),
        "trucks_active": effective_trucks,
        "avg_fill": agg_avg_fill,
        "overflow_alerts": agg_overflow_alerts
    })
    st.session_state.waste_history = st.session_state.waste_history[-24:]

# Build small history df for KPIs chart
history_df = pd.DataFrame([{"ts": rec["ts"], "avg_fill": rec["avg_fill"], "overflow_alerts": rec["overflow_alerts"]} for rec in st.session_state.waste_history])

# ----------------------------
# KPI Boxes
# ----------------------------
kpi_cols = st.columns(4)
def kpi_box(column, title, value, unit="", color="#4CAF50"):
    with column:
        st.markdown(
            f"""
            <div style="border:2px solid {color}; padding:12px; border-radius:10px; text-align:center;">
                <h4 style="margin-bottom:6px;">{title}</h4>
                <h2 style="margin-top:0; margin-bottom:6px;">{value}{unit}</h2>
            </div>
            """, unsafe_allow_html=True
        )

kpi_box(kpi_cols[0], "Avg Bin Fill", f"{agg_avg_fill:.0f}", "%", "#FFC107")
kpi_box(kpi_cols[1], "Overflow Alerts (sectors)", agg_overflow_alerts, "", "#F44336")
kpi_box(kpi_cols[2], "Trucks Active", agg_trucks_active, "", "#4CAF50")
kpi_box(kpi_cols[3], "Recycling Eff.", f"{int(agg_recycling_eff*100)}%", "", "#2196F3")

# ----------------------------
# Control logic / alerts
# ----------------------------
st.subheader("Control Logic Simulation")
if agg_overflow_alerts >= 4:
    st.error("🚨 Multiple overflow sectors detected — dispatch emergency crews.")
elif agg_avg_fill > 85:
    st.warning("⚠️ Average fill very high. Schedule immediate collections.")
elif agg_avg_fill > 70:
    st.info("🔔 Above normal fill — consider deploying extra trucks.")
else:
    st.success("✅ Waste levels within acceptable range.")

st.info(f"🕒 Average hours since collection: {agg_last_collection_avg:.0f} hrs")

st.divider()

# ----------------------------
# Heatmap: sector risk + citizen overlays
# ----------------------------
heat_col, guide_col = st.columns([3,1])
with heat_col:
    st.subheader("City Sector Bin Fill & Risk Heat Map")
    # try to load image
    try:
        map_img = Image.open(map_img_path) if map_img_path else None
    except:
        map_img = None
        st.warning("Map not found at provided path — drawing grid only.")

    fig_map = go.Figure()
    if map_img is not None:
        fig_map.add_layout_image(dict(source=map_img, xref="x", yref="y", x=0, y=3, sizex=3, sizey=3, sizing="stretch", opacity=1, layer="below"))

    # draw sectors with color based on sector_risk_pct
    for i, s in enumerate(SECTORS):
        risk = sector_risk_pct[i]
        fillpct = sector_sensor_fill[i]
        # color mapping: green <60, yellow 60-84, orange 85-119, red >=120
        if risk < 60:
            color = "green"
        elif risk < 85:
            color = "yellow"
        elif risk < 120:
            color = "orange"
        else:
            color = "red"

        fig_map.add_shape(type="rect", x0=COLS[i], y0=2-ROWS[i], x1=COLS[i]+1, y1=3-ROWS[i],
                          line=dict(color="black", width=2), fillcolor=color, opacity=0.5)
        fig_map.add_annotation(x=COLS[i]+0.5, y=2-ROWS[i]+0.5,
                               text=f"{s}<br>{int(fillpct)}% / R{int(risk)}",
                               showarrow=False, font=dict(color="black", size=11))

    # overlay filtered citizen reports as markers (size ~ severity, color by issue)
    sector_coords = {s:(c,r) for s,c,r in zip(SECTORS, COLS, ROWS)}
    issue_color_map = {"Overflow":"red","Missed Pickup":"orange","Illegal Dumping":"purple"}
    for r in filtered_reports:
        x, y = sector_coords[r["sector"]]
        y_plot = 2 - y
        color = issue_color_map.get(r["issue"], "black")
        size = r["severity"] * 10 + 6
        fig_map.add_trace(go.Scatter(
            x=[x+0.5], y=[y_plot+0.5],
            mode="markers+text",
            marker=dict(size=size, color=color, opacity=0.85, line=dict(color="black", width=1)),
            text=[f"{r['issue']} ({r['severity']})"],
            textposition="top center",
            hovertemplate=f"Sector: {r['sector']}<br>Issue: {r['issue']}<br>Severity: {r['severity']}<br>Comment: {r.get('comment','')}",
            showlegend=False
        ))

    fig_map.update_xaxes(visible=False, range=[0,3])
    fig_map.update_yaxes(visible=False, range=[0,3])
    fig_map.update_layout(height=520, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_map, use_container_width=True)

with guide_col:
    st.subheader("Legend / Guide")
    st.markdown("""
    <div style="display:flex; flex-direction:column; gap:10px;">
      <div><b>Risk color:</b></div>
      <div style="display:flex; gap:6px;">
        <div style="background-color:green; width:60px; height:26px; text-align:center; color:white; line-height:26px;">Low</div>
        <div style="background-color:yellow; width:80px; height:26px; text-align:center; color:purple; line-height:26px;">Moderate</div>
        <div style="background-color:orange; width:80px; height:26px; text-align:center; color:white; line-height:26px;">Elevated</div>
        <div style="background-color:red; width:60px; height:26px; text-align:center; color:white; line-height:26px;">Critical</div>
      </div>
      <p style="font-size:13px;">Text: SensorFill% / Risk%</p>
      <p style="font-size:13px;">Citizen markers: size ~ severity</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ----------------------------
# Trends: 24-hour (stacked by waste type) & 7-day (simulated)
# ----------------------------
trend_col1, trend_col2 = st.columns(2)
with trend_col1:
    st.subheader("Waste Collected - Last 24 Steps (kg) — simulated curve influenced by scenario")
    # generate semi-realistic hourly curves for each waste type (stacked), influenced by scenario
    hours = [f"{h}:00" for h in range(24)]
    rng2 = np.random.default_rng(int(datetime.now().timestamp()) % (2**32 - 1) + 7)
    waste_types = ["Organic","Recyclable","Hazardous","General"]
    hourly_data = {}
    for wt in waste_types:
        base = 80 if wt=="Organic" else 50 if wt=="General" else 30 if wt=="Recyclable" else 10
        # scenario multiplier
        scen_mult = 1.0
        if scenario == "High Waste Generation": scen_mult = 1.25
        if scenario == "Overflow Alerts": scen_mult = 1.1
        if scenario == "Maintenance Issue": scen_mult = 0.95
        series = []
        for h in range(24):
            pattern = daily_pattern(h)
            noise = rng2.normal(0, base*0.08)
            value = max(0, (base * scen_mult * pattern) + noise)
            series.append(value)
        hourly_data[wt] = series

    fig_24 = go.Figure()
    for wt in waste_types:
        fig_24.add_trace(go.Bar(x=hours, y=hourly_data[wt], name=wt))
    fig_24.update_layout(barmode="stack", xaxis_title="Hour", yaxis_title="Waste (kg)", height=420)
    st.plotly_chart(fig_24, use_container_width=True)

with trend_col2:
    st.subheader("Waste Collected - Last 7 Days (kg) — simulated")
    days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    rng3 = np.random.default_rng(int(datetime.now().timestamp()) % (2**32 - 1) + 11)
    weekly = {}
    for wt in waste_types:
        base = 1200 if wt=="Organic" else 700 if wt=="General" else 400 if wt=="Recyclable" else 100
        series = [max(0, rng3.normal(base, base*0.12)) for _ in range(7)]
        weekly[wt] = series
    fig_week = go.Figure()
    for wt in waste_types:
        fig_week.add_trace(go.Bar(x=days, y=weekly[wt], name=wt))
    fig_week.update_layout(barmode="stack", xaxis_title="Day", yaxis_title="Waste (kg)", height=420)
    st.plotly_chart(fig_week, use_container_width=True)

st.divider()

# ----------------------------
# Citizen Reports table and moderation
# ----------------------------
st.subheader("Citizen Reports (All)")
reports_table = pd.DataFrame([{
    "id": r["id"],
    "ts": r["ts"].strftime("%Y-%m-%d %H:%M:%S"),
    "sector": r["sector"],
    "issue": r["issue"],
    "severity": r["severity"],
    "comment": r.get("comment","")
} for r in st.session_state.citizen_reports])

colA, colB = st.columns([3,1])
with colA:
    st.dataframe(reports_table.sort_values(by="ts", ascending=False), use_container_width=True)
with colB:
    st.write("Moderation")
    remove_id = st.number_input("Remove report id", min_value=0, step=1, value=0)
    if st.button("Remove Report"):
        before = len(st.session_state.citizen_reports)
        st.session_state.citizen_reports = [r for r in st.session_state.citizen_reports if r["id"] != remove_id]
        after = len(st.session_state.citizen_reports)
        if after < before:
            st.success(f"Removed report id {remove_id}")
        else:
            st.info("No report with that id.")

st.divider()

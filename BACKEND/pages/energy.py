# energy_streetlights.py
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="Streetlight Energy Dashboard")
st.title("STREETLIGHT ENERGY DASHBOARD: Solar + Kinetic Tiles")
st.divider()

# -----------------------
# Config / Sectors
# -----------------------
SECTORS = ["A1","A2","A3","B1","B2","B3","C1","C2","C3"]
ROWS = [0,0,0,1,1,1,2,2,2]
COLS = [0,1,2,0,1,2,0,1,2]

# per-sector properties (streetlight cluster)
if "sectors" not in st.session_state:
    st.session_state.sectors = {
        s: {
            "storage": float(np.random.randint(40, 90)),  # storage % (0-100)
            "battery_capacity_kWh": 20 + random.randint(0,30),  # capacity per sector
            "kinetic_enabled": True if random.random() < 0.4 else False,
            "ped_activity": random.uniform(0.1, 1.0),  # 0..1 intensity
            "light_dim_level": 1.0,  # 1.0 = full, 0.0 = off
        } for s in SECTORS
    }

# session history
if "energy_history" not in st.session_state:
    st.session_state.energy_history = []  # each entry: ts, total_gen, total_cons, avg_storage

# -----------------------
# Sidebar Controls
# -----------------------
with st.sidebar:
    st.header("Controls")
    cloudiness = st.slider("Cloudiness (0 sunny - 1 overcast)", 0.0, 1.0, 0.25, 0.05)
    global_kinetic_toggle = st.checkbox("Enable Kinetic Tiles Globally", value=True)
    dim_threshold = st.slider("Auto-dim threshold (%) — storage below this % will dim lights", 0, 80, 30)
    critical_threshold = st.slider("Critical shutdown threshold (%) — below this % turn non-essential lights off", 0, 50, 15)
    manual_force_dim = st.checkbox("Manual: Force dim all lights (50%)", value=False)
    simulate_step = st.checkbox("Simulate one timestep (append to history)", value=True)

    st.write("---")
    st.subheader("Per-sector kinetic control (override)")
    # allow toggling kinetic per sector
    for s in SECTORS:
        key = f"kinetic_{s}"
        cur = st.session_state.sectors[s]["kinetic_enabled"]
        st.session_state.sectors[s]["kinetic_enabled"] = st.checkbox(f"{s} kinetic", value=cur, key=key)

# -----------------------
# Helper functions
# -----------------------
def solar_generation_kW_per_panel(hour, cloudiness):
    """
    Rough solar generation profile per panel (kW) by hour and cloudiness.
    Peak around noon. Values chosen for plausibility not accuracy.
    """
    # sun factor: 0 at night, peak 1 at 12:00
    if hour < 6 or hour > 18:
        sun = 0.0
    else:
        sun = max(0.0, np.cos((hour - 12) * np.pi / 12) * 1.0)  # approx bell curve
    # effect of cloudiness: multiply by (1 - cloudiness*0.8)
    return 0.2 * sun * (1 - cloudiness * 0.8)  # e.g., max ~0.2 kW per panel

def kinetic_generation_kW(ped_activity):
    """
    Kinetic tile generation per cluster (kW). Depends on activity 0..1.
    """
    # small amount per activity
    return 0.01 + 0.09 * ped_activity  # between 0.01 and 0.10 kW

def sector_light_consumption_kW(dim_level):
    """
    Consumption of streetlight cluster depending on dim level.
    Assume full brightness ~1.5 kW per sector cluster.
    """
    base_full = 1.5
    return base_full * max(0.0, dim_level)  # scale

# color mapping for storage / risk
def storage_to_color(pct):
    if pct >= 60:
        return "green"
    if pct >= 35:
        return "yellow"
    if pct >= 15:
        return "orange"
    return "red"

# -----------------------
# Simulation timestep
# -----------------------
hour_now = datetime.now().hour
rng = np.random.default_rng(int(datetime.now().timestamp()) % (2**32 - 1))

# global totals
total_generation_kW = 0.0
total_consumption_kW = 0.0
total_storage_pct = 0.0
outage_count = 0

# iterate sectors and compute per-sector gen/cons/storage updates
for s in SECTORS:
    sec = st.session_state.sectors[s]
    # solar panels per sector (assume 30-80 panels per sector cluster)
    panels = 30 + (hash(s) % 50)  # deterministic-ish per sector
    solar_per_panel = solar_generation_kW_per_panel(hour_now, cloudiness)
    solar_gen = panels * solar_per_panel  # kW

    # kinetic generation if enabled (and global toggle)
    kinetic_gen = 0.0
    if global_kinetic_toggle and sec["kinetic_enabled"]:
        # ped_activity fluctuates a bit
        sec["ped_activity"] = max(0.0, min(1.0, sec["ped_activity"] + rng.normal(0, 0.05)))
        kinetic_gen = kinetic_generation_kW(sec["ped_activity"])

    # generation sum
    gen_kW = solar_gen + kinetic_gen

    # determine desired dim level:
    if manual_force_dim:
        dim = 0.5
    else:
        # auto-dim: full brightness unless storage below threshold
        if sec["storage"] < critical_threshold:
            dim = 0.0  # shut non-essential lights
        elif sec["storage"] < dim_threshold:
            dim = 0.5  # dim to half
        else:
            dim = 1.0

    sec["light_dim_level"] = dim

    # consumption based on dim
    cons_kW = sector_light_consumption_kW(dim)

    # battery behavior (kWh): convert kW * timestep_hours (assume 1 hour per timestep)
    timestep_hours = 1.0
    net_kW = gen_kW - cons_kW
    battery_capacity_kWh = sec["battery_capacity_kWh"]
    # current stored energy in kWh = storage% * capacity / 100
    stored_kWh = sec["storage"] * battery_capacity_kWh / 100.0

    # charge/discharge with efficiency
    efficiency = 0.95
    if net_kW > 0:
        # charge battery, limited by capacity
        charge_kWh = min(net_kW * timestep_hours * efficiency, battery_capacity_kWh - stored_kWh)
        stored_kWh += charge_kWh
    else:
        # discharge to meet consumption
        need_kWh = min(-net_kW * timestep_hours / efficiency, stored_kWh)
        stored_kWh -= need_kWh
        # if battery couldn't cover all deficit, that becomes an outage (partial)
        deficit_kWh = -net_kW * timestep_hours / efficiency - need_kWh
        if deficit_kWh > 0:
            # interpret as outage impact; increment outage counter later
            sec.setdefault("last_outage_kWh", 0.0)
            sec["last_outage_kWh"] += deficit_kWh

    # update storage percent
    sec["storage"] = float(np.clip((stored_kWh / battery_capacity_kWh) * 100.0, 0.0, 100.0))

    # accumulate totals for KPIs
    total_generation_kW += gen_kW
    total_consumption_kW += cons_kW
    total_storage_pct += sec["storage"]
    # mark outage if last_outage_kWh exists (meaning battery couldn't meet)
    if sec.get("last_outage_kWh", 0.0) > 0.0:
        outage_count += 1
        # decay the outage marker to avoid permanent counting
        sec["last_outage_kWh"] = max(0.0, sec["last_outage_kWh"] - rng.uniform(0.1, 0.5))

# compute aggregated metrics
avg_storage_pct = total_storage_pct / len(SECTORS)
# append to history
if simulate_step:
    st.session_state.energy_history.append({
        "ts": datetime.now(),
        "total_generation_kW": total_generation_kW,
        "total_consumption_kW": total_consumption_kW,
        "avg_storage_pct": avg_storage_pct,
        "outages": outage_count
    })
    st.session_state.energy_history = st.session_state.energy_history[-24:]


# -----------------------
# KPI boxes
# -----------------------
col_gen, col_cons, col_storage, col_out, col_money = st.columns(5)  # added 5th column for money saved

# cost of electricity per kWh (adjust as needed)
ELECTRICITY_COST_PER_KWH = 13.4702  # in your local currency

# compute money saved from renewable generation actually used
energy_used_from_renewables_kWh = min(total_generation_kW, total_consumption_kW)  # kW over 1 hour = kWh
money_saved = energy_used_from_renewables_kWh * ELECTRICITY_COST_PER_KWH

def kpi_box(column, title, value, unit="", color="#4CAF50"):
    with column:
        st.markdown(
            f"<div style='border:2px solid {color}; padding:12px; border-radius:10px; text-align:center;'>"
            f"<h4 style='margin-bottom:6px'>{title}</h4>"
            f"<h2 style='margin-top:0'>{value}{unit}</h2>"
            "</div>",
            unsafe_allow_html=True
        )

kpi_box(col_gen, "Total Generation (kW)", f"{total_generation_kW:.1f}", "", "#4CAF50")
kpi_box(col_cons, "Total Consumption (kW)", f"{total_consumption_kW:.2f}", "", "#FFC107")
storage_color = "#4CAF50" if avg_storage_pct > 50 else "#FFC107" if avg_storage_pct > 25 else "#F44336"
kpi_box(col_storage, "Avg Storage %", f"{avg_storage_pct:.0f}%", "", storage_color)
kpi_box(col_out, "Sectors with Outage", f"{outage_count}", "", "#F44336")
kpi_box(col_money, "Money Saved", f"₱{money_saved:.2f}", "", "#2196F3")  # new KPI box

# -----------------------
# Sector map visualization (uses storage->color and dim state)
# -----------------------
st.subheader("Per-sector Storage / Light Status Map")
map_col, legend_col = st.columns([3,1])
with map_col:
    fig_map = go.Figure()
    # optional background map (no path required)
    # try to load if available (non-fatal)
    try:
        map_img = Image.open(r"C:\Users\User\Desktop\DASHBOARD\ortigas_dashboard\map.png")
        fig_map.add_layout_image(dict(source=map_img, xref="x", yref="y", x=0, y=3, sizex=3, sizey=3, sizing="stretch", opacity=1, layer="below"))
    except:
        map_img = None

    for i, s in enumerate(SECTORS):
        stsec = st.session_state.sectors[s]
        color = storage_to_color(stsec["storage"])
        dim = stsec["light_dim_level"]
        # rectangle color and text
        fig_map.add_shape(type="rect", x0=COLS[i], y0=2-ROWS[i], x1=COLS[i]+1, y1=3-ROWS[i],
                          line=dict(color="black", width=2),
                          fillcolor=color, opacity=0.6)
        status_text = f"{s}<br>Storage:{int(stsec['storage'])}%<br>Dim:{int(dim*100)}%"
        fig_map.add_annotation(x=COLS[i]+0.5, y=2-ROWS[i]+0.5, text=status_text, showarrow=False, font=dict(size=11))

        # overlay a small marker showing kinetic status if enabled
        if stsec["kinetic_enabled"]:
            x = COLS[i] + 0.75
            y = 2 - ROWS[i] + 0.75
            fig_map.add_trace(go.Scatter(x=[x], y=[y], mode="markers",
                                         marker=dict(size=10, color="blue"),
                                         showlegend=False,
                                         hoverinfo="skip"))

    fig_map.update_xaxes(visible=False, range=[0,3])
    fig_map.update_yaxes(visible=False, range=[0,3])
    fig_map.update_layout(height=520, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_map, use_container_width=True)

with legend_col:
    st.markdown("""
    **Legend**  
    - Green: storage healthy (>60%)  
    - Yellow: moderate (35–59%)  
    - Orange: low (15–34%)  
    - Red: critical (<15%)  
    - Blue dot: kinetic tiles enabled in sector  
    """)
    st.write("---")
    st.write("Manual overrides:")
    if st.button("Charge all storages +10%"):
        for s in SECTORS:
            st.session_state.sectors[s]["storage"] = min(100.0, st.session_state.sectors[s]["storage"] + 10.0)
    if st.button("Discharge all storages -10%"):
        for s in SECTORS:
            st.session_state.sectors[s]["storage"] = max(0.0, st.session_state.sectors[s]["storage"] - 10.0)

st.divider()

# -----------------------
# Hourly Trends (history)
# -----------------------
st.subheader("Recent Timeline")
if len(st.session_state.energy_history) > 0:
    hist_df = pd.DataFrame(st.session_state.energy_history)
    hist_df["label"] = hist_df["ts"].apply(lambda x: x.strftime("%H:%M"))
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Bar(x=hist_df["label"], y=hist_df["total_generation_kW"], name="Generation"))
    fig_hist.add_trace(go.Bar(x=hist_df["label"], y=hist_df["total_consumption_kW"], name="Consumption"))
    fig_hist.update_layout(barmode="group", xaxis_title="Time", yaxis_title="kW", height=360)
    st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.info("No history yet — check 'Simulate one timestep' in sidebar and re-run to capture steps.")

st.divider()

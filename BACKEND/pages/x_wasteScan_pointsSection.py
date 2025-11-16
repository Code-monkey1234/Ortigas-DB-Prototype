# x_waste_pointsSection.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="Globe Rewards: Waste Points")
st.title("Waste Scan to Points")
st.divider()

# -----------------------
# Session state: waste history
# -----------------------
if "waste_history" not in st.session_state:
    st.session_state.waste_history = []

# -----------------------
# Simulate waste scan
# -----------------------
def simulate_waste_scan():
    points = 0.2  # 5–15 points per proper disposal
    ts = datetime.now()
    return {"ts": ts, "points": points}

# Button to simulate waste scan
if st.button("Scan Waste Properly"):
    st.session_state.waste_history.append(simulate_waste_scan())
    # keep last 50 entries
    st.session_state.waste_history = st.session_state.waste_history[-50:]

# -----------------------
# Aggregate data
# -----------------------
if st.session_state.waste_history:
    df = pd.DataFrame(st.session_state.waste_history)
    df["date"] = df["ts"].dt.strftime("%Y-%m-%d")
    df["time"] = df["ts"].dt.strftime("%H:%M:%S")
    
    total_scans = len(df)
    total_points = df["points"].sum()
    total_points = round(total_points, 2)
    
    # -----------------------
    # KPI numbers
    # -----------------------
    col1, col2 = st.columns(2)
    col1.metric("Total Scans", total_scans)
    col2.metric("Total Points Earned", total_points)
    
    st.divider()
    
    # -----------------------
    # History table
    # -----------------------
    st.subheader("Waste Scan History")
    st.dataframe(
        df.sort_values(by="ts", ascending=False)[["date", "time", "points"]],
        height=300
    )
else:
    st.info("No waste scans yet. Press 'Scan Waste Properly' to add entries.")

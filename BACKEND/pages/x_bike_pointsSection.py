# x_bike_pointsSection.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

st.set_page_config(layout="wide", page_title="Globe Rewards: Bike Points")
st.title("Bike to Points")
st.divider()

# -----------------------
# Session state: history
# -----------------------
if "bike_history" not in st.session_state:
    st.session_state.bike_history = []

# -----------------------
# Simulate bike activity
# -----------------------
def simulate_bike():
    # random distance (km) per session
    distance = round(random.uniform(1.0, 10.0), 2)  # 1–10 km
    steps_equivalent = distance * 1312  # rough approximation: 1 km bike ~1312 steps
    calories = round(distance * 35, 1)  # ~35 kcal per km biking
    points = 0.2  # 10 points per km
    
    ts = datetime.now()
    return {"ts": ts, "distance_km": distance, "steps_equivalent": int(steps_equivalent), "calories": calories, "points": points}

# Simulate new bike entry
if st.button("Simulate Bike Ride"):
    st.session_state.bike_history.append(simulate_bike())
    # keep last 50 entries
    st.session_state.bike_history = st.session_state.bike_history[-50:]

# -----------------------
# Aggregate data
# -----------------------
if st.session_state.bike_history:
    df = pd.DataFrame(st.session_state.bike_history)
    # add date/time for table
    df["date"] = df["ts"].dt.strftime("%Y-%m-%d")
    df["time"] = df["ts"].dt.strftime("%H:%M:%S")
    
    # total stats
    total_distance = df["distance_km"].sum()
    total_steps_equiv = df["steps_equivalent"].sum()
    total_calories = df["calories"].sum()
    total_points = df["points"].sum()
    total_points = round(total_points, 2)
    
    # -----------------------
    # KPI numbers
    # -----------------------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Distance", f"{total_distance:.1f} km")
    col2.metric("Steps Equivalent", f"{total_steps_equiv}")
    col3.metric("Calories Burned", f"{total_calories:.1f} kcal")
    col4.metric("Points Earned", f"{total_points}")
    
    st.divider()
    
    # -----------------------
    # History table
    # -----------------------
    st.subheader("Bike History")
    st.dataframe(
        df.sort_values(by="ts", ascending=False)[["date", "time", "distance_km", "steps_equivalent", "calories", "points"]],
        height=300
    )
else:
    st.info("No bike activity yet. Press 'Simulate Bike Ride' to add entries.")

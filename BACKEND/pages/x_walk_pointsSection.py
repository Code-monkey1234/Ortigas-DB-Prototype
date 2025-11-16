# x_walk_pointsSection.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

st.set_page_config(layout="wide", page_title="Globe Rewards: Walk Points")
st.title("Walk to Points")
st.divider()

# -----------------------
# Session state: history
# -----------------------
if "walk_history" not in st.session_state:
    st.session_state.walk_history = []

# -----------------------
# Simulate steps detection
# -----------------------
def simulate_walk():
    # random steps for this timestep
    steps = random.randint(500, 3000)  # 500–3000 steps per check
    calories = round(steps * 0.04, 2)  # simple approximation: 0.04 kcal per step
    points = steps // 1000  # 1 point per 1000 steps
    ts = datetime.now()
    return {"ts": ts, "steps": steps, "calories": calories, "points": points}

# Simulate new step entry
if st.button("Simulate Walk"):
    st.session_state.walk_history.append(simulate_walk())
    # keep only last 50 entries
    st.session_state.walk_history = st.session_state.walk_history[-50:]

# -----------------------
# Aggregate data
# -----------------------
if st.session_state.walk_history:
    df = pd.DataFrame(st.session_state.walk_history)
    # add date/time for table
    df["date"] = df["ts"].dt.strftime("%Y-%m-%d")
    df["time"] = df["ts"].dt.strftime("%H:%M:%S")
    
    # total stats
    total_steps = df["steps"].sum()
    total_calories = df["calories"].sum()
    total_points = df["points"].sum()
    
    # -----------------------
    # KPI numbers
    # -----------------------
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Steps", f"{total_steps}")
    col2.metric("Calories Burned", f"{total_calories:.1f} kcal")
    col3.metric("Points Earned", f"{total_points}")
    
    st.divider()
    
    # -----------------------
    # History table
    # -----------------------
    st.subheader("Walk History")
    st.dataframe(
        df.sort_values(by="ts", ascending=False)[["date", "time", "steps", "calories", "points"]],
        height=300
    )
else:
    st.info("No walk data yet. Press 'Simulate Walk' to add entries.")

# globe_rewards_shop.py
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Globe Rewards Shop", layout="wide")
st.title("Globe Rewards Shop")

# ---------------------
# User points (simulate)
# ---------------------
if "points_balance" not in st.session_state:
    st.session_state.points_balance = 1250  # starting points

if "redeem_history" not in st.session_state:
    st.session_state.redeem_history = []

st.subheader(f"Your Points: {st.session_state.points_balance}")

st.divider()

# ---------------------
# Reward catalog
# ---------------------
REWARDS = [
    # Food
    {"name": "Yumburger", "category": "Food", "points": 150, "image": r"C:\Users\User\Desktop\LATEST ORTIGAS DASHBOARD - Copy\BACKEND\yumburger.png"},
    {"name": "Snack Pack", "category": "Food", "points": 800, "image": r"C:\Users\User\Desktop\LATEST ORTIGAS DASHBOARD - Copy\BACKEND\snackpack.png"},
    # Eco Items
    {"name": "Reusable Bottle", "category": "Eco", "points": 200, "image": r"C:\Users\User\Desktop\LATEST ORTIGAS DASHBOARD - Copy\BACKEND\reusable_bottle.png"},
    {"name": "Seed Pack", "category": "Eco", "points": 120, "image": r"C:\Users\User\Desktop\LATEST ORTIGAS DASHBOARD - Copy\BACKEND\seedpack.png"},
    # Charity
    {"name": "Tree Planting", "category": "Charity", "points": 500, "image": r"C:\Users\User\Desktop\LATEST ORTIGAS DASHBOARD - Copy\BACKEND\tree_planting.png"},
    {"name": "School Kit Donation", "category": "Charity", "points": 400, "image": r"C:\Users\User\Desktop\LATEST ORTIGAS DASHBOARD - Copy\BACKEND\donation.png"},
    # Digital / Lifestyle
    {"name": "Lazada ₱149 discount", "category": "Digital", "points": 250, "image": r"C:\Users\User\Desktop\LATEST ORTIGAS DASHBOARD - Copy\BACKEND\discount.png"},
    {"name": "Shoppee ₱149 discount", "category": "Digital", "points": 50, "image": r"C:\Users\User\Desktop\LATEST ORTIGAS DASHBOARD - Copy\BACKEND\discount.png"},
]

# ---------------------
# Category Tabs
# ---------------------
categories = ["Food", "Eco", "Charity", "Digital"]
tab1, tab2, tab3, tab4 = st.tabs(categories)

tab_mapping = {tab1: "Food", tab2: "Eco", tab3: "Charity", tab4: "Digital"}

for tab, cat in tab_mapping.items():
    with tab:
        st.subheader(f"{cat} Rewards")
        cols = st.columns(3)
        for idx, reward in enumerate([r for r in REWARDS if r["category"] == cat]):
            col = cols[idx % 3]
            with col:
                st.image(reward["image"], use_container_width=True)
                st.markdown(f"**{reward['name']}**")
                st.markdown(f"Points: {reward['points']}")
                if st.button("Redeem", key=f"redeem_{reward['name']}"):
                    if st.session_state.points_balance >= reward["points"]:
                        st.session_state.points_balance -= reward["points"]
                        st.session_state.redeem_history.append({
                            "reward": reward["name"],
                            "category": reward["category"],
                            "points": reward["points"],
                            "time": datetime.now()
                        })
                        st.success(f"Redeemed {reward['name']}!")
                    else:
                        st.error("Not enough points!")

st.divider()

# ---------------------
# Redeem History
# ---------------------
st.subheader("Redemption History")
if st.session_state.redeem_history:
    for h in reversed(st.session_state.redeem_history[-10:]):  # show last 10
        st.markdown(f"{h['time'].strftime('%Y-%m-%d %H:%M')} - {h['reward']} ({h['points']} pts)")
else:
    st.info("No redemptions yet.")

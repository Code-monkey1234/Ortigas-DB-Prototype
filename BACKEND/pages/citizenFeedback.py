import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import uuid

st.set_page_config(layout="wide", page_title="Citizen Reports — Admin Mode")
st.title("Citizen Feedback: Admin Panel (Free text locations)")

# -------------------------
# Initialize session state
# -------------------------
if "reports" not in st.session_state:
    st.session_state.reports = [
        {
            "id": str(uuid.uuid4())[:8],
            "ts": datetime.now(),
            "name": "Juan D.",
            "category": "Waste Management",
            "location_text": "Near 7-11 along Main St.",
            "severity": "Major",
            "description": "Garbage bin overflowing for 3 days.",
            "status": "Submitted",
            "assigned_to": "",
            "response_time_days": None
        },
        {
            "id": str(uuid.uuid4())[:8],
            "ts": datetime.now(),
            "name": "Maria S.",
            "category": "Streetlight",
            "location_text": "C1 - corner lamppost flickering",
            "severity": "Minor",
            "description": "Light flickers at night.",
            "status": "Submitted",
            "assigned_to": "",
            "response_time_days": None
        }
    ]

# -------------------------
# Left = filters (optional), right = reports list
# -------------------------
left, right = st.columns([1, 2])

# -------------------------
# Filters (left column)
# -------------------------
with left:
    st.subheader("Filters")
    reports_df = pd.DataFrame(st.session_state.reports)
    categories = ["All"] + sorted(reports_df["category"].unique().tolist())
    severities = ["All","Critical","Major","Minor"]
    statuses = ["All","Submitted","Verified","Assigned","In Progress","Resolved"]

    filter_category = st.multiselect("Category", categories, default="All")
    filter_severity = st.multiselect("Severity", severities, default="All")
    filter_status = st.multiselect("Status", statuses, default="All")
    search_text = st.text_input("Search (name/location/description)")
    sort_by = st.selectbox("Sort by", ["Newest","Severity (Critical→Minor)","Status"])

# -------------------------
# Prepare filtered list
# -------------------------
reports_df = pd.DataFrame(st.session_state.reports)
if reports_df.empty:
    filtered = []
else:
    mask = pd.Series(True, index=reports_df.index)

    if "All" not in filter_category:
        mask &= reports_df["category"].isin(filter_category)
    if "All" not in filter_severity:
        mask &= reports_df["severity"].isin(filter_severity)
    if "All" not in filter_status:
        mask &= reports_df["status"].isin(filter_status)
    if search_text.strip():
        q = search_text.strip().lower()
        mask &= (reports_df["location_text"].str.lower().str.contains(q) |
                 reports_df["description"].str.lower().str.contains(q) |
                 reports_df["name"].str.lower().str.contains(q))

    filtered_df = reports_df[mask].copy()

    # Sorting
    if sort_by == "Newest":
        filtered_df = filtered_df.sort_values(by="ts", ascending=False)
    elif sort_by == "Severity (Critical→Minor)":
        filtered_df["s_rank"] = filtered_df["severity"].map({"Critical":3,"Major":2,"Minor":1})
        filtered_df = filtered_df.sort_values(by="s_rank", ascending=False)
    elif sort_by == "Status":
        status_order = {"Submitted":0,"Verified":1,"Assigned":2,"In Progress":3,"Resolved":4}
        filtered_df["st_rank"] = filtered_df["status"].map(status_order)
        filtered_df = filtered_df.sort_values(by=["st_rank","ts"], ascending=[True,False])

    filtered = filtered_df.to_dict("records")

# -------------------------
# Right column: Reports list + admin tools
# -------------------------
with right:
    st.subheader("Reports List")
    st.write(f"Showing **{len(filtered)}** report(s) matching filters.")
    st.write("---")

    # Export CSV of filtered
    if filtered:
        export_df = pd.DataFrame(filtered).drop(columns=["description"])  # keep export compact
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("Export filtered list (CSV)", csv, "reports_filtered.csv", "text/csv")

    # Bulk actions
    st.write("### Bulk actions (admin)")
    colba1, colba2, colba3 = st.columns(3)
    with colba1:
        if st.button("Mark all visible as Verified"):
            changed = 0
            for r in st.session_state.reports:
                if r["id"] in [rec["id"] for rec in filtered]:
                    if r["status"] == "Submitted":
                        r["status"] = "Verified"
                        r["response_time_days"] = np.random.randint(0,2)
                        changed += 1
            st.success(f"{changed} report(s) verified.")
    with colba2:
        if st.button("Assign visible to Team A"):
            changed = 0
            for r in st.session_state.reports:
                if r["id"] in [rec["id"] for rec in filtered]:
                    r["assigned_to"] = "Team A"
                    if r["status"] == "Verified":
                        r["status"] = "Assigned"
                    changed += 1
            st.success(f"{changed} report(s) assigned to Team A.")
    with colba3:
        if st.button("Resolve visible"):
            changed = 0
            for r in st.session_state.reports:
                if r["id"] in [rec["id"] for rec in filtered] and r["status"] != "Resolved":
                    r["status"] = "Resolved"
                    r["response_time_days"] = np.random.randint(0,5)
                    changed += 1
            st.success(f"{changed} report(s) resolved.")

    st.write("---")

    # Display each report as expandable card
    for rec in filtered:
        severity_color = {"Critical":"#d32f2f","Major":"#f57c00","Minor":"#1976d2"}.get(rec["severity"], "#666")
        st.markdown(f"""
            <div style="border:1px solid #ddd; padding:12px; border-radius:8px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-weight:700; color:{severity_color};">[{rec['severity']}]</span>
                        <span style="font-weight:700; margin-left:8px;">{rec['category']}</span>
                        <span style="color:#666; margin-left:8px;">— {rec['location_text']}</span>
                    </div>
                    <div style="text-align:right; color:#666;">
                        <div style="font-size:12px;">Status: <b>{rec['status']}</b></div>
                        <div style="font-size:12px;">Reported: {rec['ts'].strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </div>
                </div>
                <p style="margin-top:8px; margin-bottom:6px;">{rec['description']}</p>
                <div style="font-size:12px; color:#444;">
                    <b>Reporter:</b> {rec['name'] or 'Anonymous'} &nbsp; | &nbsp; <b>Assigned to:</b> {rec.get('assigned_to','') or '-'}
                    &nbsp; | &nbsp; <b>Response days:</b> {rec.get('response_time_days') if rec.get('response_time_days') is not None else '-'}
                </div>
            </div>
        """, unsafe_allow_html=True)

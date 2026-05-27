"""Cohort aggregate dashboard page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.queries import cohort_names, cohort_summary

st.title("Cohorts")
st.caption("Cohort SQL returns aggregate summaries for dashboard use.")

names = cohort_names()
selected = st.selectbox("Cohort", names)
if selected:
    summary = cohort_summary(selected)
    st.dataframe(summary, hide_index=True, use_container_width=True)
    st.download_button(
        "Download aggregate summary",
        summary.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected}_aggregate_summary.csv",
        mime="text/csv",
    )

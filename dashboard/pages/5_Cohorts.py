"""Cohort aggregate dashboard page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.queries import cohort_detail_tables, cohort_names, cohort_summary

st.title("Cohorts")
st.caption("Cohort SQL returns aggregate summaries for dashboard use.")
st.warning("Aggregate cohort metrics only. No patient-level rows are shown.")

names = cohort_names()
selected = st.selectbox("Cohort", names)
if selected:
    summary = cohort_summary(selected)
    details = cohort_detail_tables(selected)

    st.subheader("Cohort Summary")
    st.dataframe(summary, hide_index=True, use_container_width=True)

    st.subheader("Aggregate Demographics")
    st.dataframe(details["demographics"], hide_index=True, use_container_width=True)

    st.subheader("Aggregate Outcomes")
    st.dataframe(details["outcomes"], hide_index=True, use_container_width=True)

    st.subheader("Feature Completeness")
    st.dataframe(details["feature_completeness"], hide_index=True, use_container_width=True)

    st.download_button(
        "Download aggregate summary",
        summary.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected}_aggregate_summary.csv",
        mime="text/csv",
    )

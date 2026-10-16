"""Cohort aggregate dashboard page."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import streamlit as st

from dashboard.components.queries import cohort_detail_tables, cohort_names, cohort_summary, get_config, query_df
from dashboard.components.study_guardrails import render_cohort_guardrails
from src.core.paths import project_root
from src.research.study_service import load_and_validate, preview_study

st.title("Cohorts")
st.caption("Cohort SQL returns aggregate summaries for dashboard use.")
st.warning("Aggregate cohort metrics only. No patient-level rows are shown.")

templates, builder = st.tabs(["Saved cohort templates", "Timed study builder"])

with templates:
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

with builder:
    st.caption("The supported builder keeps the registered prospective task and changes only reviewed cohort criteria.")
    base = load_and_validate(project_root() / "configs/studies/icu_mortality_24h.yaml")
    units = query_df("SELECT DISTINCT first_careunit FROM silver_icustays WHERE first_careunit IS NOT NULL ORDER BY 1")
    unit_choices = ["All care units", *units.iloc[:, 0].astype(str).tolist()]
    minimum_age = st.slider("Minimum age", min_value=18, max_value=90, value=base.minimum_age)
    care_unit = st.selectbox("Care unit", unit_choices)
    spec = replace(base, minimum_age=minimum_age, care_unit=None if care_unit == "All care units" else care_unit)
    render_cohort_guardrails(spec)
    if st.button("Preview timed cohort"):
        preview = preview_study(get_config(), spec)
        st.caption(f"Definition hash: {preview['definition_hash']} | First-ever ICU stay per patient | 24-hour prediction horizon")
        st.code("Index time (t0) = first ICU admission, selected by intime then stay_id. The care-unit filter is applied after that selection; later ICU stays never enter the cohort.")
        st.dataframe(pd.DataFrame(preview["cohort_flow"]), hide_index=True, use_container_width=True)

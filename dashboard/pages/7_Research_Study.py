"""Shared-service UI for the timed synthetic ICU study."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.queries import get_config
from dashboard.components.study_guardrails import render_cohort_guardrails
from src.core.paths import project_root
from src.research.study_service import load_and_validate, preview_study, publish_run, run_study

st.title("Research Study Builder")
st.caption("Invented synthetic data only. Cohort flow, feature timing, and results are aggregate-only.")

study_path = project_root() / "configs/studies/icu_mortality_24h.yaml"
spec = load_and_validate(study_path)
config = get_config()
st.code(study_path.read_text(), language="yaml")
render_cohort_guardrails(spec)

if st.button("Preview cohort and timing"):
    preview = preview_study(config, spec)
    st.caption(f"Definition hash: {preview['definition_hash']} | Dataset snapshot: {preview['dataset_snapshot']}")
    st.subheader("Cohort flow")
    st.dataframe(pd.DataFrame(preview["cohort_flow"]), hide_index=True, use_container_width=True)
    st.subheader("Laboratory timing audit")
    st.dataframe(pd.DataFrame(preview["timing_audit"]), hide_index=True, use_container_width=True)

if st.button("Run timed study"):
    result = run_study(config, spec)
    st.session_state["latest_study_run_id"] = result["run_id"]
    st.success(f"Completed run {result['run_id']}")
    st.json(result["evaluation"])

run_id = st.session_state.get("latest_study_run_id")
if run_id:
    st.caption(f"Latest local run: {run_id}")
    if st.button("Publish aggregate package", key=f"publish-{run_id}"):
        st.success(f"Published: {publish_run(config, run_id)}")

st.info("The target is death strictly after prediction time and on or before hospital discharge. Measurements must occur before the 24-hour prediction time and have known availability by then.")

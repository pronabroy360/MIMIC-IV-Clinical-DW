"""Aggregate timing and provenance explorer for the supported synthetic study."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import yaml

from dashboard.components.queries import get_config
from dashboard.components.study_guardrails import render_cohort_guardrails
from src.core.db import connect
from src.core.paths import project_root
from src.research.features import build_prospective_feature_table, feature_audit
from src.research.study_service import load_and_validate, preview_study

st.title("Feature Timing Explorer")
st.caption("Invented synthetic data only. All timing views are aggregate-only.")

spec = load_and_validate(project_root() / "configs/studies/icu_mortality_24h.yaml")
config = get_config()
registry = yaml.safe_load((project_root() / "configs/research/prospective_feature_registry.yaml").read_text())
render_cohort_guardrails(spec)
st.subheader("Prospective timing contract")
st.json(registry["timing_policy"])

if st.button("Inspect timing and feature coverage"):
    preview = preview_study(config, spec)
    with connect(config) as con:
        build_prospective_feature_table(con, spec)
        audit = feature_audit(con, spec)
    st.subheader("Event exclusion audit")
    st.dataframe(pd.DataFrame(preview["timing_audit"]), hide_index=True, use_container_width=True)
    st.subheader("Active feature coverage")
    st.dataframe(pd.DataFrame(audit), hide_index=True, use_container_width=True)

st.subheader("Registered feature lineage")
st.dataframe(pd.DataFrame(registry["features"]), hide_index=True, use_container_width=True)
st.info("An event must be measured from ICU admission through, but excluding, 24 hours and must be available by the prediction time. Delayed results appear in the Data Quality Laboratory as excluded observations.")

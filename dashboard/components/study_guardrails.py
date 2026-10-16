"""Shared explanation of the prospective cohort contract."""

from __future__ import annotations

import streamlit as st

from src.research.contracts import StudySpec


def render_cohort_guardrails(spec: StudySpec) -> None:
    """Show the non-negotiable time and stay rules before a study is run."""
    st.subheader("Prospective cohort contract")
    index, prediction, outcome, inclusion = st.columns(4)
    index.metric("1. Index time (t0)", "ICU admission")
    prediction.metric("2. Prediction window", f"[t0, t0 + {spec.horizon_hours} h)")
    outcome.metric("3. Outcome window", f"After t0 + {spec.horizon_hours} h through discharge")
    inclusion.metric("4. Inclusion / exclusion", "First ICU stay; adult; alive and in ICU at t0 + 24 h")
    st.info(
        "One patient contributes only their first-ever ICU stay, ordered by ICU admission time and then stay ID. "
        "All later ICU stays are excluded before any features are built."
    )
    st.warning(
        "Post-outcome information is prohibited: diagnosis codes, procedure codes, discharge fields, whole-stay summaries, "
        "and events measured or available at/after prediction time are excluded from predictors. "
        "Deaths at or before prediction time are exclusions, not positive labels."
    )

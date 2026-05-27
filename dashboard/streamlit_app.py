"""Streamlit dashboard entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.queries import overview_metrics  # noqa: E402

st.set_page_config(page_title="MIMIC-IV Clinical Warehouse", layout="wide")
st.title("MIMIC-IV Clinical Data Warehouse")
st.caption("Aggregate analytics only. No patient-level rows or raw identifiers are displayed.")

metrics = overview_metrics()
cols = st.columns(4)
cols[0].metric("Patients", f"{int(metrics.get('patients') or 0):,}")
cols[1].metric("Admissions", f"{int(metrics.get('admissions') or 0):,}")
cols[2].metric("ICU stays", f"{int(metrics.get('icu_stays') or 0):,}")
cols[3].metric("Lab events", f"{int(metrics.get('lab_events') or 0):,}")

cols = st.columns(4)
cols[0].metric("Medication events", f"{int(metrics.get('medication_events') or 0):,}")
cols[1].metric("24h chart events", f"{int(metrics.get('chart_events_24h') or 0):,}")
cols[2].metric("Avg hospital LOS", f"{(metrics.get('avg_hospital_los') or 0):.2f} days")
cols[3].metric("Avg ICU LOS", f"{(metrics.get('avg_icu_los') or 0):.2f} days")

st.metric("Aggregate mortality rate", f"{100 * (metrics.get('mortality_rate') or 0):.2f}%")
st.info(
    "This dashboard is for research engineering demonstration. It is not clinical decision support."
)

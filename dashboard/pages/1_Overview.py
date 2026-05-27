"""Overview dashboard page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.queries import overview_metrics

st.title("Overview")
st.caption("Aggregate warehouse summary.")

metrics = overview_metrics()
cols = st.columns(3)
cols[0].metric("Patients", f"{int(metrics.get('patients') or 0):,}")
cols[1].metric("Admissions", f"{int(metrics.get('admissions') or 0):,}")
cols[2].metric("ICU stays", f"{int(metrics.get('icu_stays') or 0):,}")

cols = st.columns(3)
cols[0].metric("Average hospital LOS", f"{(metrics.get('avg_hospital_los') or 0):.2f}")
cols[1].metric("Average ICU LOS", f"{(metrics.get('avg_icu_los') or 0):.2f}")
cols[2].metric("Mortality rate", f"{100 * (metrics.get('mortality_rate') or 0):.2f}%")

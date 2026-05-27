"""Admissions aggregate dashboard page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.charts import bar_chart
from dashboard.components.queries import query_df

st.title("Admissions")

by_type = query_df(
    """
    SELECT admission_type, count(*) AS admissions,
           avg(hospital_los_days) AS avg_los_days,
           avg(in_hospital_mortality_flag) AS mortality_rate
    FROM gold_admission_summary
    GROUP BY admission_type
    ORDER BY admissions DESC
    LIMIT 50
    """
)
bar_chart(by_type, "admission_type", "admissions", "Admissions by type")
st.dataframe(by_type, hide_index=True, use_container_width=True)

by_race = query_df(
    """
    SELECT race, count(*) AS admissions
    FROM gold_admission_summary
    GROUP BY race
    ORDER BY admissions DESC
    LIMIT 50
    """
)
bar_chart(by_race, "race", "admissions", "Admissions by race category")

by_insurance = query_df(
    """
    SELECT insurance, count(*) AS admissions
    FROM gold_admission_summary
    GROUP BY insurance
    ORDER BY admissions DESC
    LIMIT 50
    """
)
bar_chart(by_insurance, "insurance", "admissions", "Admissions by insurance")

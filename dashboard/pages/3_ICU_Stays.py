"""ICU stay aggregate dashboard page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.charts import bar_chart, histogram
from dashboard.components.queries import query_df

st.title("ICU Stays")

careunit = query_df(
    """
    SELECT first_careunit, count(*) AS stays,
           avg(icu_los_days) AS avg_icu_los_days,
           avg(icu_mortality_flag) AS icu_mortality_rate
    FROM gold_icu_stay_summary
    GROUP BY first_careunit
    ORDER BY stays DESC
    LIMIT 50
    """
)
bar_chart(careunit, "first_careunit", "stays", "ICU stays by care unit")
st.dataframe(careunit, hide_index=True, use_container_width=True)

los = query_df("SELECT icu_los_days FROM gold_icu_stay_summary WHERE icu_los_days IS NOT NULL LIMIT 10000")
histogram(los, "icu_los_days", "ICU LOS distribution")

first_repeat = query_df(
    """
    SELECT
        CASE WHEN is_first_icu_stay = 1 THEN 'First ICU stay' ELSE 'Repeat ICU stay' END AS stay_type,
        count(*) AS stays
    FROM gold_icu_stay_summary
    GROUP BY stay_type
    ORDER BY stays DESC
    LIMIT 10
    """
)
bar_chart(first_repeat, "stay_type", "stays", "First vs repeat ICU stays")

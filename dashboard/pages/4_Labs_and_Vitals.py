"""Labs and vitals aggregate dashboard page."""

from __future__ import annotations

import streamlit as st

from dashboard.components.charts import bar_chart
from dashboard.components.queries import query_df

st.title("Labs and Vitals")
st.warning("Aggregate analytics only. Patient-level rows and raw identifiers are not displayed.")

common_labs = query_df(
    """
    SELECT
        lab_label,
        count(*) AS event_count,
        avg(is_abnormal) AS abnormal_rate
    FROM silver_labs
    WHERE lab_label IS NOT NULL
    GROUP BY lab_label
    ORDER BY event_count DESC
    LIMIT 15
    """
)
st.subheader("Most common lab tests")
bar_chart(common_labs, "lab_label", "event_count", "Top lab tests by event count")
st.dataframe(common_labs, hide_index=True, use_container_width=True)

lab_completeness = query_df(
    """
    SELECT
        avg(CASE WHEN lactate_mean IS NOT NULL THEN 1 ELSE 0 END) AS lactate_24h,
        avg(CASE WHEN creatinine_mean IS NOT NULL THEN 1 ELSE 0 END) AS creatinine_24h,
        avg(CASE WHEN wbc_mean IS NOT NULL THEN 1 ELSE 0 END) AS wbc_24h,
        avg(CASE WHEN hemoglobin_mean IS NOT NULL THEN 1 ELSE 0 END) AS hemoglobin_24h
    FROM gold_first_24h_features
    LIMIT 100
    """
)
st.subheader("First-24-hour lab completeness")
st.dataframe(lab_completeness, hide_index=True, use_container_width=True)

vitals = query_df(
    """
    SELECT
        avg(has_heart_rate_24h) AS heart_rate_24h,
        avg(has_blood_pressure_24h) AS blood_pressure_24h,
        avg(has_resp_rate_24h) AS resp_rate_24h,
        avg(has_temperature_24h) AS temperature_24h,
        avg(has_spo2_24h) AS spo2_24h
    FROM gold_vital_features
    LIMIT 100
    """
)
st.subheader("First-24-hour vital availability")
st.dataframe(vitals, hide_index=True, use_container_width=True)

lab_summary = query_df(
    """
    SELECT
        'distinct tests per ICU stay' AS metric,
        avg(distinct_lab_tests) AS value
    FROM gold_lab_features
    UNION ALL
    SELECT
        'abnormal lab rate',
        avg(abnormal_lab_rate)
    FROM gold_lab_features
    LIMIT 100
    """
)
bar_chart(lab_summary, "metric", "value", "Lab feature summary")

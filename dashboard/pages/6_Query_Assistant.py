"""Guarded aggregate query assistant dashboard page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.queries import ask_demo_question, safe_query_df

st.title("Query Assistant")
st.caption("Read-only aggregate SQL only. Raw identifiers and patient-level rows are blocked.")

question = st.text_input(
    "Ask an aggregate question",
    value="What is the average ICU length of stay by care unit?",
)
if st.button("Generate aggregate answer"):
    result = ask_demo_question(question)
    if not result["allowed"]:
        st.error("; ".join(result["reasons"]))
        st.caption("For a cohort or prediction study, use the Research Study Builder page.")
    else:
        st.code(result["sql"], language="sql")
        st.dataframe(pd.DataFrame(result["rows"]), hide_index=True, use_container_width=True)
        st.caption(result["explanation"])

with st.expander("Run guarded SQL"):
    sql = st.text_area(
        "SQL",
        value="SELECT first_careunit, avg(icu_los_days) AS avg_icu_los_days FROM gold_icu_stay_summary GROUP BY first_careunit LIMIT 100",
    )
    if st.button("Run guarded SQL"):
        try:
            st.dataframe(safe_query_df(sql), hide_index=True, use_container_width=True)
        except ValueError as exc:
            st.error(str(exc))

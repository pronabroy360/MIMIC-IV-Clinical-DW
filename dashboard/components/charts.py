"""Small Streamlit chart helpers."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str) -> None:
    """Render a compact bar chart when data is available."""
    if df.empty or x not in df or y not in df:
        st.info("No aggregate data available yet.")
        return
    st.plotly_chart(px.bar(df, x=x, y=y, title=title), use_container_width=True)


def histogram(df: pd.DataFrame, x: str, title: str) -> None:
    """Render a histogram when data is available."""
    if df.empty or x not in df:
        st.info("No aggregate data available yet.")
        return
    st.plotly_chart(px.histogram(df, x=x, title=title), use_container_width=True)

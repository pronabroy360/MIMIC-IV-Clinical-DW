"""Controlled invented-data scenario demonstrations."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.queries import get_config
from src.cli import ingest, run_validation
from src.core.paths import project_root
from src.research.scenarios import available_scenarios, prepare_scenario
from src.research.study_service import load_and_validate, run_study

st.title("Data Quality Laboratory")
st.caption("Each scenario copies the invented source into an isolated workspace. The baseline source is not modified.")

scenario = st.selectbox("Scenario", sorted(available_scenarios()))
st.write(available_scenarios()[scenario]["description"])
if st.button("Run controlled scenario"):
    config = get_config()
    scenario_config = prepare_scenario(config, scenario)
    ingest(scenario_config)
    from src.transform.build_gold import build_gold
    build_gold(scenario_config)
    results, report = run_validation(scenario_config)
    st.subheader("Quality gates")
    st.dataframe(pd.DataFrame([result.__dict__ for result in results]), hide_index=True, use_container_width=True)
    failures = [result for result in results if result.status == "fail"]
    if failures:
        st.error(f"Scenario blocked by {len(failures)} quality failure(s). Report: {report}")
    else:
        spec = load_and_validate(project_root() / "configs/studies/icu_mortality_24h.yaml")
        result = run_study(scenario_config, spec)
        st.success(f"Scenario study completed: {result['run_id']}")
        st.json(result["evaluation"])

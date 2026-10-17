"""Controlled invented-data scenario demonstrations."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.queries import get_config
from src.cli import ingest, run_validation
from src.core.paths import project_root
from src.research.scenarios import available_scenarios, prepare_scenario
from src.research.comparison import compare_frozen_scenario
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

st.divider()
st.subheader("Paired frozen-model comparison")
st.caption("Fits preprocessing and the model on baseline training patients only. It compares the same eligible test patients when possible and reports exclusions separately.")
if st.button("Compare against baseline", key="paired-scenario-comparison"):
    config = get_config()
    from src.ingest.load_demo import load_local_files
    from src.transform.build_gold import build_gold
    load_local_files(config)
    build_gold(config)
    scenario_config = prepare_scenario(config, scenario)
    ingest(scenario_config)
    build_gold(scenario_config)
    results, report = run_validation(scenario_config)
    failures = [result for result in results if result.status == "fail"]
    if failures:
        st.error(f"blocked_by_quality: {len(failures)} blocking failure(s). See {report}")
    else:
        spec = load_and_validate(project_root() / "configs/studies/icu_mortality_24h.yaml")
        output = config.outputs_public_path / "studies" / f"scenario_comparison_{scenario}.json"
        comparison = compare_frozen_scenario(config, scenario_config, spec, output)
        st.json(comparison)

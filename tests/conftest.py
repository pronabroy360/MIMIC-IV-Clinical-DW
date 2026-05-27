from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import LLMConfig, WarehouseConfig


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join("" if value is None else str(value) for value in row))
    path.write_text("\n".join(lines) + "\n")


@pytest.fixture()
def synthetic_config(tmp_path: Path) -> WarehouseConfig:
    raw = tmp_path / "raw" / "mimic-iv-demo" / "2.2"
    return WarehouseConfig(
        mode="demo",
        database_path=tmp_path / "processed" / "mimic_demo.duckdb",
        raw_data_path=raw,
        public_mode=True,
        outputs_private_path=tmp_path / "outputs" / "private",
        outputs_public_path=tmp_path / "outputs" / "public",
        llm=LLMConfig(),
    )


@pytest.fixture()
def synthetic_raw_data(synthetic_config: WarehouseConfig) -> Path:
    raw = synthetic_config.raw_data_path
    assert raw is not None

    write_csv(
        raw / "hosp" / "patients.csv",
        ["subject_id", "gender", "anchor_age", "anchor_year", "anchor_year_group", "dod"],
        [[100, "M", 65, 2120, "2017 - 2019", ""]],
    )
    write_csv(
        raw / "hosp" / "admissions.csv",
        [
            "subject_id",
            "hadm_id",
            "admittime",
            "dischtime",
            "deathtime",
            "admission_type",
            "admission_location",
            "discharge_location",
            "insurance",
            "language",
            "marital_status",
            "race",
            "hospital_expire_flag",
        ],
        [
            [
                100,
                200,
                "2120-01-01 00:00:00",
                "2120-01-05 00:00:00",
                "",
                "URGENT",
                "TRANSFER",
                "HOME",
                "Medicare",
                "ENGLISH",
                "MARRIED",
                "WHITE",
                0,
            ]
        ],
    )
    write_csv(
        raw / "icu" / "icustays.csv",
        ["subject_id", "hadm_id", "stay_id", "first_careunit", "last_careunit", "intime", "outtime", "los"],
        [[100, 200, 300, "MICU", "MICU", "2120-01-01 12:00:00", "2120-01-03 12:00:00", 2.0]],
    )
    write_csv(
        raw / "icu" / "d_items.csv",
        ["itemid", "label", "abbreviation", "linksto", "category", "unitname", "param_type"],
        [
            [220045, "Heart Rate", "HR", "chartevents", "Routine Vital Signs", "bpm", "Numeric"],
            [220179, "Non Invasive Blood Pressure systolic", "NBPs", "chartevents", "Routine Vital Signs", "mmHg", "Numeric"],
        ],
    )
    write_csv(
        raw / "icu" / "chartevents.csv",
        ["subject_id", "hadm_id", "stay_id", "caregiver_id", "charttime", "storetime", "itemid", "value", "valuenum", "valueuom", "warning"],
        [
            [100, 200, 300, 1, "2120-01-01 13:00:00", "2120-01-01 13:05:00", 220045, 80, 80, "bpm", 0],
            [100, 200, 300, 1, "2120-01-01 14:00:00", "2120-01-01 14:05:00", 220179, 120, 120, "mmHg", 0],
        ],
    )
    write_csv(
        raw / "hosp" / "d_labitems.csv",
        ["itemid", "label", "fluid", "category"],
        [[50813, "Lactate", "Blood", "Chemistry"], [50912, "Creatinine", "Blood", "Chemistry"]],
    )
    write_csv(
        raw / "hosp" / "labevents.csv",
        ["labevent_id", "subject_id", "hadm_id", "specimen_id", "itemid", "charttime", "storetime", "value", "valuenum", "valueuom", "flag"],
        [
            [1, 100, 200, 10, 50813, "2120-01-01 15:00:00", "2120-01-01 15:30:00", 2.5, 2.5, "mmol/L", "abnormal"],
            [2, 100, 200, 11, 50912, "2120-01-01 16:00:00", "2120-01-01 16:30:00", 1.1, 1.1, "mg/dL", ""],
        ],
    )
    write_csv(
        raw / "hosp" / "diagnoses_icd.csv",
        ["subject_id", "hadm_id", "seq_num", "icd_code", "icd_version"],
        [[100, 200, 1, "A419", 10], [100, 200, 2, "I509", 10]],
    )
    write_csv(
        raw / "hosp" / "d_icd_diagnoses.csv",
        ["icd_code", "icd_version", "long_title"],
        [["A419", 10, "Sepsis unspecified organism"], ["I509", 10, "Heart failure unspecified"]],
    )
    write_csv(
        raw / "hosp" / "procedures_icd.csv",
        ["subject_id", "hadm_id", "seq_num", "chartdate", "icd_code", "icd_version"],
        [[100, 200, 1, "2120-01-02", "5A1955Z", 10]],
    )
    write_csv(
        raw / "hosp" / "d_icd_procedures.csv",
        ["icd_code", "icd_version", "long_title"],
        [["5A1955Z", 10, "Respiratory ventilation"]],
    )
    write_csv(
        raw / "icu" / "procedureevents.csv",
        ["subject_id", "hadm_id", "stay_id", "caregiver_id", "starttime", "endtime", "storetime", "itemid", "value", "valueuom", "location", "statusdescription"],
        [[100, 200, 300, 1, "2120-01-01 18:00:00", "2120-01-01 19:00:00", "2120-01-01 19:05:00", 999, 1, "event", "ICU", "Finished"]],
    )
    write_csv(
        raw / "hosp" / "microbiologyevents.csv",
        ["microevent_id", "subject_id", "hadm_id", "chartdate", "charttime", "spec_type_desc", "test_name", "org_name", "ab_name", "interpretation"],
        [[1, 100, 200, "2120-01-01", "2120-01-01 17:00:00", "Blood", "Culture", "", "", ""]],
    )
    write_csv(
        raw / "hosp" / "prescriptions.csv",
        ["subject_id", "hadm_id", "pharmacy_id", "starttime", "stoptime", "drug", "route"],
        [[100, 200, 1, "2120-01-01 13:00:00", "2120-01-02 13:00:00", "Vancomycin", "IV"]],
    )
    return raw

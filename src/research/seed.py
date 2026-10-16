"""Create a deterministic, entirely invented MIMIC-shaped teaching cohort."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from src.core.config import WarehouseConfig

DISEASES = (
    ("I509", "Heart failure unspecified"),
    ("J189", "Pneumonia unspecified organism"),
    ("A419", "Sepsis unspecified organism"),
    ("E119", "Type 2 diabetes mellitus"),
    ("J960", "Acute respiratory failure"),
)
LABS = (
    (51301, "White Blood Cells", 8.0),
    (51222, "Hemoglobin", 13.0),
    (51265, "Platelet Count", 220.0),
    (50912, "Creatinine", 1.0),
    (51006, "Urea Nitrogen", 18.0),
    (50983, "Sodium", 138.0),
    (50971, "Potassium", 4.0),
    (50931, "Glucose", 105.0),
    (50813, "Lactate", 1.4),
)
VITALS = (
    (220045, "Heart Rate", 82.0),
    (220179, "Non Invasive Blood Pressure systolic", 120.0),
    (220180, "Non Invasive Blood Pressure diastolic", 70.0),
    (220181, "Non Invasive Blood Pressure mean", 85.0),
    (220210, "Respiratory Rate", 18.0),
    (223761, "Temperature Fahrenheit", 98.6),
    (220277, "O2 saturation pulseoxymetry", 97.0),
)
SOURCE_FILES = frozenset({
    "hosp/patients.csv", "hosp/admissions.csv", "icu/icustays.csv",
    "hosp/diagnoses_icd.csv", "hosp/d_icd_diagnoses.csv",
    "hosp/d_labitems.csv", "hosp/labevents.csv",
    "icu/d_items.csv", "icu/chartevents.csv",
    "hosp/procedures_icd.csv", "hosp/d_icd_procedures.csv", "hosp/services.csv",
    "icu/inputevents.csv",
})
POPULATED_BRONZE_TABLES = frozenset({
    "bronze_hosp_patients", "bronze_hosp_admissions", "bronze_icu_icustays",
    "bronze_hosp_diagnoses_icd", "bronze_hosp_d_icd_diagnoses",
    "bronze_hosp_d_labitems", "bronze_hosp_labevents",
    "bronze_icu_d_items", "bronze_icu_chartevents",
    "bronze_hosp_procedures_icd", "bronze_hosp_d_icd_procedures", "bronze_hosp_services",
    "bronze_icu_inputevents",
})

PROCEDURES = (("5A1955Z", "Respiratory ventilation, 24-96 consecutive hours"),)
NOREPINEPHRINE_ITEM = 221906


def _stamp(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _write(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def seed_research_cohort(config: WarehouseConfig, patients: int = 1000, seed: int = 42) -> Path:
    """Replace only the configured synthetic source folder with invented records.

    This generator learns no values or distributions from MIMIC-IV or another
    repository. Its small set of arbitrary patterns exists to exercise software.
    """
    if config.mode != "demo" or config.raw_data_path is None or "research-synthetic" not in config.raw_data_path.parts:
        raise ValueError("Use the isolated research_synthetic config to seed this cohort")
    if patients < 100:
        raise ValueError("At least 100 synthetic patients are needed for the teaching models")

    rng = random.Random(seed)
    raw = config.raw_data_path
    unexpected = sorted(
        str(path.relative_to(raw)) for path in raw.rglob("*.csv*")
        if str(path.relative_to(raw)) not in SOURCE_FILES
    ) if raw.exists() else []
    if unexpected:
        raise ValueError(f"Unexpected files in synthetic source folder: {', '.join(unexpected)}")
    patient_rows: list[list[object]] = []
    admission_rows: list[list[object]] = []
    icu_rows: list[list[object]] = []
    diagnosis_rows: list[list[object]] = []
    procedure_rows: list[list[object]] = []
    service_rows: list[list[object]] = []
    lab_rows: list[list[object]] = []
    chart_rows: list[list[object]] = []
    input_rows: list[list[object]] = []
    lab_id = 1

    for index in range(patients):
        subject_id = 8_000_001 + index
        hadm_id = 9_000_001 + 2 * index
        stay_id = 10_000_001 + 2 * index
        age = 21 + (index * 37) % 68
        gender = "F" if index % 2 else "M"
        disease_index = index % len(DISEASES)
        disease_code, _ = DISEASES[disease_index]
        severity = (index * 13 % 11) / 10 + rng.uniform(-0.18, 0.18)
        admission = datetime(2120, 1, 1) + timedelta(days=index % 330, hours=index % 19)
        los_days = 2.5 + 2.4 * severity + disease_index * 0.3 + rng.uniform(0, 3)
        discharge = admission + timedelta(days=los_days)
        died = index % 13 == 0 or (severity > 0.85 and index % 17 == 0)
        death_time = discharge - timedelta(hours=2) if died else None
        patient_rows.append([subject_id, gender, age, 2120, "2017 - 2019", _stamp(death_time)])
        admission_rows.append([
            subject_id, hadm_id, _stamp(admission), _stamp(discharge), _stamp(death_time),
            "URGENT" if index % 3 else "EW EMER.", "EMERGENCY ROOM",
            "DIED" if died else "HOME", "Private" if index % 3 else "Medicare",
            "ENGLISH", "MARRIED" if index % 2 else "SINGLE",
            ("WHITE", "BLACK/AFRICAN AMERICAN", "ASIAN", "OTHER")[index % 4], int(died),
        ])
        diagnosis_rows.append([subject_id, hadm_id, 1, disease_code, 10])
        secondary_codes = [code for offset, (code, _) in enumerate(DISEASES)
                           if code != disease_code and (index + offset) % 7 == 0]
        for sequence, code in enumerate(secondary_codes, start=2):
            diagnosis_rows.append([subject_id, hadm_id, sequence, code, 10])
        service_rows.append([subject_id, hadm_id, _stamp(admission), "", "MED" if index % 3 else "CSURG"])

        if index % 5 != 4:
            intime = admission + timedelta(hours=4)
            outtime = min(discharge - timedelta(hours=4), intime + timedelta(days=1.5 + severity))
            icu_rows.append([
                subject_id, hadm_id, stay_id,
                ("MICU", "SICU", "CCU")[index % 3],
                ("MICU", "SICU", "CCU")[index % 3],
                _stamp(intime), _stamp(outtime), round((outtime - intime).total_seconds() / 86400, 4),
            ])
            for itemid, _, base_value in VITALS:
                if (index + itemid) % 19 == 0:
                    continue
                shift = severity * (10 if itemid == 220045 else 2)
                value = round(base_value + shift + rng.uniform(-2, 2), 2)
                chart_rows.append([
                    subject_id, hadm_id, stay_id, 700001, _stamp(intime + timedelta(hours=3)),
                    _stamp(intime + timedelta(hours=3, minutes=5)), itemid,
                    value, value, "synthetic_unit", 0,
                ])
            for itemid, _, base_value in LABS:
                if (index + itemid) % 23 == 0:
                    continue
                shift = severity * (0.6 if itemid in (50912, 50813) else 1.5)
                value = round(base_value + shift + rng.uniform(-0.5, 0.5), 2)
                lab_rows.append([
                    lab_id, subject_id, hadm_id, 700000 + lab_id, itemid,
                    _stamp(intime + timedelta(hours=5)),
                    _stamp(intime + timedelta(hours=5, minutes=30)),
                    value, value, "synthetic_unit", "",
                ])
                lab_id += 1
            if severity > 0.72:
                input_rows.append([
                    subject_id, hadm_id, stay_id, 700001, _stamp(intime + timedelta(hours=6)),
                    _stamp(intime + timedelta(hours=8)), _stamp(intime + timedelta(hours=8, minutes=5)),
                    NOREPINEPHRINE_ITEM, 4.0, "mg", 0.04, "mcg/kg/min", index + 1, index + 1,
                    "Continuous IV", "", "Medication", "Synthetic vasopressor", 70.0, 4.0, "mg",
                    0, 0, "Changed", 4.0, 0.04,
                ])
            if severity > 0.82:
                procedure_rows.append([subject_id, hadm_id, 1, admission.date().isoformat(), "5A1955Z", 10])

        # A later urgent admission is the only source of the readmission label.
        if not died and index % 5 == 0:
            later = discharge + timedelta(days=2 + index % 27)
            later_discharge = later + timedelta(days=2 + index % 4)
            admission_rows.append([
                subject_id, hadm_id + 1, _stamp(later), _stamp(later_discharge), "",
                "URGENT", "EMERGENCY ROOM", "HOME", "Private", "ENGLISH",
                "SINGLE", ("WHITE", "BLACK/AFRICAN AMERICAN", "ASIAN", "OTHER")[index % 4], 0,
            ])
            diagnosis_rows.append([subject_id, hadm_id + 1, 1, disease_code, 10])
            service_rows.append([subject_id, hadm_id + 1, _stamp(later), "", "MED"])

    _write(raw / "hosp/patients.csv", ["subject_id", "gender", "anchor_age", "anchor_year", "anchor_year_group", "dod"], patient_rows)
    _write(raw / "hosp/admissions.csv", ["subject_id", "hadm_id", "admittime", "dischtime", "deathtime", "admission_type", "admission_location", "discharge_location", "insurance", "language", "marital_status", "race", "hospital_expire_flag"], admission_rows)
    _write(raw / "icu/icustays.csv", ["subject_id", "hadm_id", "stay_id", "first_careunit", "last_careunit", "intime", "outtime", "los"], icu_rows)
    _write(raw / "hosp/diagnoses_icd.csv", ["subject_id", "hadm_id", "seq_num", "icd_code", "icd_version"], diagnosis_rows)
    _write(raw / "hosp/d_icd_diagnoses.csv", ["icd_code", "icd_version", "long_title"], [[code, 10, label] for code, label in DISEASES])
    _write(raw / "hosp/procedures_icd.csv", ["subject_id", "hadm_id", "seq_num", "chartdate", "icd_code", "icd_version"], procedure_rows)
    _write(raw / "hosp/d_icd_procedures.csv", ["icd_code", "icd_version", "long_title"], [[code, 10, label] for code, label in PROCEDURES])
    _write(raw / "hosp/services.csv", ["subject_id", "hadm_id", "transfertime", "prev_service", "curr_service"], service_rows)
    _write(raw / "hosp/d_labitems.csv", ["itemid", "label", "fluid", "category"], [[itemid, label, "Blood", "Synthetic"] for itemid, label, _ in LABS])
    _write(raw / "hosp/labevents.csv", ["labevent_id", "subject_id", "hadm_id", "specimen_id", "itemid", "charttime", "storetime", "value", "valuenum", "valueuom", "flag"], lab_rows)
    _write(raw / "icu/d_items.csv", ["itemid", "label", "abbreviation", "linksto", "category", "unitname", "param_type"], [[itemid, label, label[:4], "chartevents", "Synthetic", "synthetic_unit", "Numeric"] for itemid, label, _ in VITALS] + [[NOREPINEPHRINE_ITEM, "Norepinephrine", "NORE", "inputevents", "Synthetic", "mcg/kg/min", "Numeric"]])
    _write(raw / "icu/chartevents.csv", ["subject_id", "hadm_id", "stay_id", "caregiver_id", "charttime", "storetime", "itemid", "value", "valuenum", "valueuom", "warning"], chart_rows)
    _write(raw / "icu/inputevents.csv", ["subject_id", "hadm_id", "stay_id", "caregiver_id", "starttime", "endtime", "storetime", "itemid", "amount", "amountuom", "rate", "rateuom", "orderid", "linkorderid", "ordercategoryname", "secondaryordercategoryname", "ordercomponenttypedescription", "ordercategorydescription", "patientweight", "totalamount", "totalamountuom", "isopenbag", "continueinnextdept", "statusdescription", "originalamount", "originalrate"], input_rows)
    return raw

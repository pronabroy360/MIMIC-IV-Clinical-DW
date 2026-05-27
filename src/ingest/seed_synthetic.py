"""Generate a tiny public-safe synthetic MIMIC-like demo dataset."""

from __future__ import annotations

import csv
from pathlib import Path

from src.core.config import WarehouseConfig


def _write_csv(path: Path, header: list[str], rows: list[list[object]], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def seed_synthetic_demo_data(config: WarehouseConfig, overwrite: bool = False) -> Path:
    """Write deterministic fake CSVs that exercise the full local pipeline."""
    if config.raw_data_path is None:
        raise ValueError("raw_data_path is required for synthetic seeding")

    raw = config.raw_data_path

    patients = [
        [900001, "M", 68, 2120, "2017 - 2019", ""],
        [900002, "F", 54, 2120, "2017 - 2019", ""],
        [900003, "M", 77, 2120, "2017 - 2019", "2120-03-08 08:30:00"],
        [900004, "F", 43, 2120, "2017 - 2019", ""],
        [900005, "M", 61, 2120, "2017 - 2019", ""],
        [900006, "F", 72, 2120, "2017 - 2019", ""],
    ]
    admissions = [
        [900001, 910001, "2120-01-01 00:00:00", "2120-01-06 12:00:00", "", "URGENT", "TRANSFER", "HOME", "Medicare", "ENGLISH", "MARRIED", "WHITE", 0],
        [900002, 910002, "2120-01-03 08:00:00", "2120-01-08 10:00:00", "", "EW EMER.", "EMERGENCY ROOM", "REHAB", "Private", "ENGLISH", "SINGLE", "BLACK/AFRICAN AMERICAN", 0],
        [900003, 910003, "2120-03-02 14:00:00", "2120-03-09 09:00:00", "2120-03-08 08:30:00", "URGENT", "TRANSFER", "DIED", "Medicare", "ENGLISH", "WIDOWED", "HISPANIC/LATINO", 1],
        [900004, 910004, "2120-04-10 11:00:00", "2120-04-12 15:00:00", "", "ELECTIVE", "PHYSICIAN REFERRAL", "HOME", "Private", "ENGLISH", "MARRIED", "ASIAN", 0],
        [900005, 910005, "2120-05-05 07:00:00", "2120-05-11 18:00:00", "", "EW EMER.", "EMERGENCY ROOM", "SNF", "Medicaid", "ENGLISH", "DIVORCED", "WHITE", 0],
        [900006, 910006, "2120-06-15 04:00:00", "2120-06-19 12:00:00", "", "URGENT", "TRANSFER", "HOME HEALTH CARE", "Medicare", "SPANISH", "MARRIED", "OTHER", 0],
        [900001, 910007, "2120-07-01 05:00:00", "2120-07-03 10:00:00", "", "OBSERVATION ADMIT", "CLINIC REFERRAL", "HOME", "Medicare", "ENGLISH", "MARRIED", "WHITE", 0],
    ]
    icustays = [
        [900001, 910001, 920001, "MICU", "MICU", "2120-01-01 09:00:00", "2120-01-04 09:00:00", 3.0],
        [900002, 910002, 920002, "SICU", "SICU", "2120-01-03 13:00:00", "2120-01-06 08:00:00", 2.79],
        [900003, 910003, 920003, "MICU", "MICU", "2120-03-02 18:00:00", "2120-03-08 08:30:00", 5.60],
        [900004, 910004, 920004, "CSRU", "CSRU", "2120-04-10 15:00:00", "2120-04-11 20:00:00", 1.21],
        [900005, 910005, 920005, "MICU", "TSICU", "2120-05-05 10:00:00", "2120-05-09 11:00:00", 4.04],
        [900006, 910006, 920006, "CCU", "CCU", "2120-06-15 09:00:00", "2120-06-17 12:00:00", 2.13],
        [900001, 910007, 920007, "SICU", "SICU", "2120-07-01 08:00:00", "2120-07-02 08:00:00", 1.0],
    ]

    d_items = [
        [220045, "Heart Rate", "HR", "chartevents", "Routine Vital Signs", "bpm", "Numeric"],
        [220179, "Non Invasive Blood Pressure systolic", "NBPs", "chartevents", "Routine Vital Signs", "mmHg", "Numeric"],
        [220180, "Non Invasive Blood Pressure diastolic", "NBPd", "chartevents", "Routine Vital Signs", "mmHg", "Numeric"],
        [220181, "Non Invasive Blood Pressure mean", "NBPm", "chartevents", "Routine Vital Signs", "mmHg", "Numeric"],
        [220210, "Respiratory Rate", "RR", "chartevents", "Routine Vital Signs", "insp/min", "Numeric"],
        [223761, "Temperature Fahrenheit", "Temp", "chartevents", "Routine Vital Signs", "degF", "Numeric"],
        [220277, "O2 saturation pulseoxymetry", "SpO2", "chartevents", "Routine Vital Signs", "%", "Numeric"],
        [225792, "Invasive Ventilation", "Vent", "procedureevents", "Respiratory", "", "Process"],
        [226559, "Foley", "Urine", "outputevents", "Output", "mL", "Numeric"],
        [225158, "NaCl 0.9%", "NS", "inputevents", "Fluids", "mL", "Numeric"],
    ]
    d_labitems = [
        [51301, "White Blood Cells", "Blood", "Hematology"],
        [51222, "Hemoglobin", "Blood", "Hematology"],
        [51265, "Platelet Count", "Blood", "Hematology"],
        [50912, "Creatinine", "Blood", "Chemistry"],
        [51006, "Urea Nitrogen", "Blood", "Chemistry"],
        [50983, "Sodium", "Blood", "Chemistry"],
        [50971, "Potassium", "Blood", "Chemistry"],
        [50931, "Glucose", "Blood", "Chemistry"],
        [50813, "Lactate", "Blood", "Chemistry"],
    ]

    lab_rows: list[list[object]] = []
    lab_id = 1
    for idx, (_, hadm_id, stay_id, *_rest) in enumerate(icustays, start=1):
        subject_id = icustays[idx - 1][0]
        base_date = admissions[idx - 1][2].split(" ")[0]
        values = {
            51301: 7.2 + idx,
            51222: 13.5 - idx * 0.4,
            51265: 180 + idx * 15,
            50912: 0.8 + idx * 0.2,
            51006: 14 + idx * 3,
            50983: 136 + idx,
            50971: 3.8 + idx * 0.1,
            50931: 95 + idx * 12,
            50813: 1.1 + idx * 0.35,
        }
        for itemid, value in values.items():
            flag = "abnormal" if itemid in {50813, 50912, 51006} and value > 2.0 else ""
            lab_rows.append(
                [
                    lab_id,
                    subject_id,
                    hadm_id,
                    800000 + lab_id,
                    itemid,
                    f"{base_date} 14:00:00",
                    f"{base_date} 14:30:00",
                    value,
                    value,
                    "synthetic_unit",
                    flag,
                ]
            )
            lab_id += 1

    chart_rows: list[list[object]] = []
    event_id = 1
    vital_values = {
        220045: [84, 92, 105, 76, 98, 88, 79],
        220179: [122, 110, 95, 130, 101, 118, 126],
        220180: [68, 62, 54, 75, 58, 66, 70],
        220181: [82, 75, 65, 91, 70, 83, 88],
        220210: [18, 22, 28, 16, 24, 20, 17],
        223761: [98.6, 99.2, 101.1, 98.1, 100.3, 98.8, 98.4],
        220277: [97, 95, 91, 99, 93, 96, 98],
    }
    for stay in icustays:
        subject_id, hadm_id, stay_id = stay[0], stay[1], stay[2]
        date = str(stay[5]).split(" ")[0]
        for itemid, values in vital_values.items():
            value = values[event_id % len(values)]
            chart_rows.append(
                [
                    subject_id,
                    hadm_id,
                    stay_id,
                    700001,
                    f"{date} 12:00:00",
                    f"{date} 12:05:00",
                    itemid,
                    value,
                    value,
                    "synthetic_unit",
                    0,
                ]
            )
        event_id += 1

    diagnoses = [
        [900001, 910001, 1, "I509", 10],
        [900001, 910001, 2, "J189", 10],
        [900002, 910002, 1, "E119", 10],
        [900003, 910003, 1, "A419", 10],
        [900003, 910003, 2, "N179", 10],
        [900004, 910004, 1, "Z951", 10],
        [900005, 910005, 1, "J960", 10],
        [900005, 910005, 2, "A419", 10],
        [900006, 910006, 1, "I509", 10],
        [900001, 910007, 1, "R079", 10],
    ]
    d_diagnoses = [
        ["I509", 10, "Heart failure unspecified"],
        ["J189", 10, "Pneumonia unspecified organism"],
        ["E119", 10, "Type 2 diabetes mellitus without complications"],
        ["A419", 10, "Sepsis unspecified organism"],
        ["N179", 10, "Acute kidney failure unspecified"],
        ["Z951", 10, "Presence of aortocoronary bypass graft"],
        ["J960", 10, "Acute respiratory failure"],
        ["R079", 10, "Chest pain unspecified"],
    ]
    procedures = [
        [900003, 910003, 1, "2120-03-03", "5A1955Z", 10],
        [900005, 910005, 1, "2120-05-06", "5A1955Z", 10],
        [900004, 910004, 1, "2120-04-10", "021009W", 10],
    ]
    d_procedures = [
        ["5A1955Z", 10, "Respiratory ventilation"],
        ["021009W", 10, "Bypass coronary artery"],
    ]

    micro = [
        [1, 900003, 910003, "2120-03-03", "2120-03-03 09:00:00", "Blood", "Culture", "Synthetic organism A", "Vancomycin", "S"],
        [2, 900005, 910005, "2120-05-06", "2120-05-06 10:00:00", "Sputum", "Culture", "", "", ""],
    ]
    prescriptions = [
        [900001, 910001, 1, "2120-01-01 10:00:00", "2120-01-03 10:00:00", "Furosemide", "IV"],
        [900003, 910003, 2, "2120-03-02 20:00:00", "2120-03-06 20:00:00", "Vancomycin", "IV"],
        [900005, 910005, 3, "2120-05-05 12:00:00", "2120-05-08 12:00:00", "Norepinephrine", "IV"],
        [900006, 910006, 4, "2120-06-15 12:00:00", "2120-06-16 12:00:00", "Ceftriaxone", "IV"],
    ]
    inputevents = [
        [900003, 910003, 920003, 700001, "2120-03-02 20:00:00", "2120-03-02 22:00:00", "2120-03-02 22:05:00", 225158, 500, "mL", 250, "mL/h", 1, 1, "Fluids", "", "", "", 80, 500, "mL", 0, 0, "Finished", 500, 250],
        [900005, 910005, 920005, 700001, "2120-05-05 12:00:00", "2120-05-05 18:00:00", "2120-05-05 18:05:00", 225158, 1000, "mL", 166, "mL/h", 2, 2, "Fluids", "", "", "", 95, 1000, "mL", 0, 0, "Finished", 1000, 166],
    ]
    outputevents = [
        [900003, 910003, 920003, 700001, "2120-03-02 21:00:00", "2120-03-02 21:05:00", 226559, 120, "mL"],
        [900005, 910005, 920005, 700001, "2120-05-05 18:00:00", "2120-05-05 18:05:00", 226559, 300, "mL"],
        [900006, 910006, 920006, 700001, "2120-06-15 18:00:00", "2120-06-15 18:05:00", 226559, 250, "mL"],
    ]
    procedureevents = [
        [900003, 910003, 920003, 700001, "2120-03-02 19:00:00", "2120-03-04 19:00:00", "2120-03-04 19:05:00", 225792, 1, "event", "ICU", "Respiratory", 1, 1, "Ventilation", "", "Respiratory", 80, 0, 0, "Finished", 1, 0],
        [900005, 910005, 920005, 700001, "2120-05-05 14:00:00", "2120-05-06 14:00:00", "2120-05-06 14:05:00", 225792, 1, "event", "ICU", "Respiratory", 2, 2, "Ventilation", "", "Respiratory", 95, 0, 0, "Finished", 1, 0],
    ]
    transfers = [
        [900001, 910001, 930001, "admit", "Medicine", "2120-01-01 00:00:00", "2120-01-01 09:00:00"],
        [900001, 910001, 930002, "transfer", "MICU", "2120-01-01 09:00:00", "2120-01-04 09:00:00"],
    ]

    _write_csv(raw / "hosp" / "patients.csv", ["subject_id", "gender", "anchor_age", "anchor_year", "anchor_year_group", "dod"], patients, overwrite)
    _write_csv(raw / "hosp" / "admissions.csv", ["subject_id", "hadm_id", "admittime", "dischtime", "deathtime", "admission_type", "admission_location", "discharge_location", "insurance", "language", "marital_status", "race", "hospital_expire_flag"], admissions, overwrite)
    _write_csv(raw / "hosp" / "transfers.csv", ["subject_id", "hadm_id", "transfer_id", "eventtype", "careunit", "intime", "outtime"], transfers, overwrite)
    _write_csv(raw / "icu" / "icustays.csv", ["subject_id", "hadm_id", "stay_id", "first_careunit", "last_careunit", "intime", "outtime", "los"], icustays, overwrite)
    _write_csv(raw / "icu" / "d_items.csv", ["itemid", "label", "abbreviation", "linksto", "category", "unitname", "param_type"], d_items, overwrite)
    _write_csv(raw / "hosp" / "d_labitems.csv", ["itemid", "label", "fluid", "category"], d_labitems, overwrite)
    _write_csv(raw / "hosp" / "labevents.csv", ["labevent_id", "subject_id", "hadm_id", "specimen_id", "itemid", "charttime", "storetime", "value", "valuenum", "valueuom", "flag"], lab_rows, overwrite)
    _write_csv(raw / "icu" / "chartevents.csv", ["subject_id", "hadm_id", "stay_id", "caregiver_id", "charttime", "storetime", "itemid", "value", "valuenum", "valueuom", "warning"], chart_rows, overwrite)
    _write_csv(raw / "hosp" / "diagnoses_icd.csv", ["subject_id", "hadm_id", "seq_num", "icd_code", "icd_version"], diagnoses, overwrite)
    _write_csv(raw / "hosp" / "d_icd_diagnoses.csv", ["icd_code", "icd_version", "long_title"], d_diagnoses, overwrite)
    _write_csv(raw / "hosp" / "procedures_icd.csv", ["subject_id", "hadm_id", "seq_num", "chartdate", "icd_code", "icd_version"], procedures, overwrite)
    _write_csv(raw / "hosp" / "d_icd_procedures.csv", ["icd_code", "icd_version", "long_title"], d_procedures, overwrite)
    _write_csv(raw / "hosp" / "microbiologyevents.csv", ["microevent_id", "subject_id", "hadm_id", "chartdate", "charttime", "spec_type_desc", "test_name", "org_name", "ab_name", "interpretation"], micro, overwrite)
    _write_csv(raw / "hosp" / "prescriptions.csv", ["subject_id", "hadm_id", "pharmacy_id", "starttime", "stoptime", "drug", "route"], prescriptions, overwrite)
    _write_csv(raw / "icu" / "inputevents.csv", ["subject_id", "hadm_id", "stay_id", "caregiver_id", "starttime", "endtime", "storetime", "itemid", "amount", "amountuom", "rate", "rateuom", "orderid", "linkorderid", "ordercategoryname", "secondaryordercategoryname", "ordercomponenttypedescription", "ordercategorydescription", "patientweight", "totalamount", "totalamountuom", "isopenbag", "continueinnextdept", "statusdescription", "originalamount", "originalrate"], inputevents, overwrite)
    _write_csv(raw / "icu" / "outputevents.csv", ["subject_id", "hadm_id", "stay_id", "caregiver_id", "charttime", "storetime", "itemid", "value", "valueuom"], outputevents, overwrite)
    _write_csv(raw / "icu" / "procedureevents.csv", ["subject_id", "hadm_id", "stay_id", "caregiver_id", "starttime", "endtime", "storetime", "itemid", "value", "valueuom", "location", "locationcategory", "orderid", "linkorderid", "ordercategoryname", "secondaryordercategoryname", "ordercategorydescription", "patientweight", "isopenbag", "continueinnextdept", "statusdescription", "originalamount", "originalrate"], procedureevents, overwrite)

    return raw

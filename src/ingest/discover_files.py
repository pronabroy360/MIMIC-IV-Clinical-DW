"""Discover MIMIC-IV CSV/GZ files and define expected raw schemas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


EXPECTED_TABLES: dict[str, tuple[str, ...]] = {
    "hosp": (
        "admissions",
        "patients",
        "transfers",
        "labevents",
        "d_labitems",
        "microbiologyevents",
        "poe",
        "poe_detail",
        "prescriptions",
        "pharmacy",
        "emar",
        "emar_detail",
        "diagnoses_icd",
        "d_icd_diagnoses",
        "procedures_icd",
        "d_icd_procedures",
        "drgcodes",
        "services",
        "provider",
        "hcpcsevents",
        "d_hcpcs",
        "omr",
    ),
    "icu": (
        "icustays",
        "d_items",
        "chartevents",
        "inputevents",
        "ingredientevents",
        "outputevents",
        "procedureevents",
        "datetimeevents",
        "caregiver",
    ),
}


METADATA_COLUMNS: dict[str, str] = {
    "source_file": "VARCHAR",
    "loaded_at": "TIMESTAMP",
    "source_module": "VARCHAR",
    "pipeline_run_id": "VARCHAR",
}


RAW_SCHEMAS: dict[tuple[str, str], dict[str, str]] = {
    ("hosp", "patients"): {
        "subject_id": "BIGINT",
        "gender": "VARCHAR",
        "anchor_age": "INTEGER",
        "anchor_year": "INTEGER",
        "anchor_year_group": "VARCHAR",
        "dod": "TIMESTAMP",
    },
    ("hosp", "admissions"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "admittime": "TIMESTAMP",
        "dischtime": "TIMESTAMP",
        "deathtime": "TIMESTAMP",
        "admission_type": "VARCHAR",
        "admit_provider_id": "VARCHAR",
        "admission_location": "VARCHAR",
        "discharge_location": "VARCHAR",
        "insurance": "VARCHAR",
        "language": "VARCHAR",
        "marital_status": "VARCHAR",
        "race": "VARCHAR",
        "edregtime": "TIMESTAMP",
        "edouttime": "TIMESTAMP",
        "hospital_expire_flag": "INTEGER",
    },
    ("hosp", "transfers"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "transfer_id": "BIGINT",
        "eventtype": "VARCHAR",
        "careunit": "VARCHAR",
        "intime": "TIMESTAMP",
        "outtime": "TIMESTAMP",
    },
    ("hosp", "labevents"): {
        "labevent_id": "BIGINT",
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "specimen_id": "BIGINT",
        "itemid": "INTEGER",
        "order_provider_id": "VARCHAR",
        "charttime": "TIMESTAMP",
        "storetime": "TIMESTAMP",
        "value": "VARCHAR",
        "valuenum": "DOUBLE",
        "valueuom": "VARCHAR",
        "ref_range_lower": "DOUBLE",
        "ref_range_upper": "DOUBLE",
        "flag": "VARCHAR",
        "priority": "VARCHAR",
        "comments": "VARCHAR",
    },
    ("hosp", "d_labitems"): {
        "itemid": "INTEGER",
        "label": "VARCHAR",
        "fluid": "VARCHAR",
        "category": "VARCHAR",
    },
    ("hosp", "microbiologyevents"): {
        "microevent_id": "BIGINT",
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "micro_specimen_id": "BIGINT",
        "order_provider_id": "VARCHAR",
        "chartdate": "DATE",
        "charttime": "TIMESTAMP",
        "spec_itemid": "INTEGER",
        "spec_type_desc": "VARCHAR",
        "test_seq": "INTEGER",
        "storedate": "DATE",
        "storetime": "TIMESTAMP",
        "test_itemid": "INTEGER",
        "test_name": "VARCHAR",
        "org_itemid": "INTEGER",
        "org_name": "VARCHAR",
        "isolate_num": "INTEGER",
        "quantity": "VARCHAR",
        "ab_itemid": "INTEGER",
        "ab_name": "VARCHAR",
        "dilution_text": "VARCHAR",
        "dilution_comparison": "VARCHAR",
        "dilution_value": "DOUBLE",
        "interpretation": "VARCHAR",
        "comments": "VARCHAR",
    },
    ("hosp", "poe"): {
        "poe_id": "VARCHAR",
        "poe_seq": "INTEGER",
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "ordertime": "TIMESTAMP",
        "order_type": "VARCHAR",
        "order_subtype": "VARCHAR",
        "transaction_type": "VARCHAR",
        "discontinue_of_poe_id": "VARCHAR",
        "discontinued_by_poe_id": "VARCHAR",
        "order_provider_id": "VARCHAR",
        "order_status": "VARCHAR",
    },
    ("hosp", "poe_detail"): {
        "poe_id": "VARCHAR",
        "poe_seq": "INTEGER",
        "subject_id": "BIGINT",
        "field_name": "VARCHAR",
        "field_value": "VARCHAR",
    },
    ("hosp", "prescriptions"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "pharmacy_id": "BIGINT",
        "poe_id": "VARCHAR",
        "poe_seq": "INTEGER",
        "order_provider_id": "VARCHAR",
        "starttime": "TIMESTAMP",
        "stoptime": "TIMESTAMP",
        "drug_type": "VARCHAR",
        "drug": "VARCHAR",
        "formulary_drug_cd": "VARCHAR",
        "gsn": "VARCHAR",
        "ndc": "VARCHAR",
        "prod_strength": "VARCHAR",
        "form_rx": "VARCHAR",
        "dose_val_rx": "VARCHAR",
        "dose_unit_rx": "VARCHAR",
        "form_val_disp": "VARCHAR",
        "form_unit_disp": "VARCHAR",
        "doses_per_24_hrs": "DOUBLE",
        "route": "VARCHAR",
    },
    ("hosp", "pharmacy"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "pharmacy_id": "BIGINT",
        "poe_id": "VARCHAR",
        "starttime": "TIMESTAMP",
        "stoptime": "TIMESTAMP",
        "medication": "VARCHAR",
        "proc_type": "VARCHAR",
        "status": "VARCHAR",
        "entertime": "TIMESTAMP",
        "verifiedtime": "TIMESTAMP",
        "route": "VARCHAR",
        "frequency": "VARCHAR",
        "disp_sched": "VARCHAR",
        "infusion_type": "VARCHAR",
        "sliding_scale": "VARCHAR",
        "lockout_interval": "VARCHAR",
        "basal_rate": "DOUBLE",
        "one_hr_max": "VARCHAR",
        "doses_per_24_hrs": "DOUBLE",
        "duration": "DOUBLE",
        "duration_interval": "VARCHAR",
        "expiration_value": "DOUBLE",
        "expiration_unit": "VARCHAR",
        "expirationdate": "TIMESTAMP",
        "dispensation": "VARCHAR",
        "fill_quantity": "VARCHAR",
    },
    ("hosp", "emar"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "emar_id": "VARCHAR",
        "emar_seq": "INTEGER",
        "poe_id": "VARCHAR",
        "pharmacy_id": "BIGINT",
        "charttime": "TIMESTAMP",
        "medication": "VARCHAR",
        "event_txt": "VARCHAR",
        "scheduletime": "TIMESTAMP",
        "storetime": "TIMESTAMP",
    },
    ("hosp", "emar_detail"): {
        "subject_id": "BIGINT",
        "emar_id": "VARCHAR",
        "emar_seq": "INTEGER",
        "parent_field_ordinal": "VARCHAR",
        "administration_type": "VARCHAR",
        "pharmacy_id": "BIGINT",
        "barcode_type": "VARCHAR",
        "reason_for_no_barcode": "VARCHAR",
        "complete_dose_not_given": "VARCHAR",
        "dose_due": "VARCHAR",
        "dose_due_unit": "VARCHAR",
        "dose_given": "VARCHAR",
        "dose_given_unit": "VARCHAR",
        "will_remainder_of_dose_be_given": "VARCHAR",
        "product_amount_given": "VARCHAR",
        "product_unit": "VARCHAR",
        "product_code": "VARCHAR",
        "product_description": "VARCHAR",
        "product_description_other": "VARCHAR",
        "prior_infusion_rate": "VARCHAR",
        "infusion_rate": "VARCHAR",
        "infusion_rate_adjustment": "VARCHAR",
        "infusion_rate_adjustment_amount": "VARCHAR",
        "infusion_rate_unit": "VARCHAR",
        "route": "VARCHAR",
        "infusion_complete": "VARCHAR",
        "completion_interval": "VARCHAR",
        "new_iv_bag_hung": "VARCHAR",
        "continued_infusion_in_other_location": "VARCHAR",
        "restart_interval": "VARCHAR",
        "side": "VARCHAR",
        "site": "VARCHAR",
        "non_formulary_visual_verification": "VARCHAR",
    },
    ("hosp", "diagnoses_icd"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "seq_num": "INTEGER",
        "icd_code": "VARCHAR",
        "icd_version": "INTEGER",
    },
    ("hosp", "d_icd_diagnoses"): {
        "icd_code": "VARCHAR",
        "icd_version": "INTEGER",
        "long_title": "VARCHAR",
    },
    ("hosp", "procedures_icd"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "seq_num": "INTEGER",
        "chartdate": "DATE",
        "icd_code": "VARCHAR",
        "icd_version": "INTEGER",
    },
    ("hosp", "d_icd_procedures"): {
        "icd_code": "VARCHAR",
        "icd_version": "INTEGER",
        "long_title": "VARCHAR",
    },
    ("hosp", "drgcodes"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "drg_type": "VARCHAR",
        "drg_code": "VARCHAR",
        "description": "VARCHAR",
        "drg_severity": "INTEGER",
        "drg_mortality": "INTEGER",
    },
    ("hosp", "services"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "transfertime": "TIMESTAMP",
        "prev_service": "VARCHAR",
        "curr_service": "VARCHAR",
    },
    ("hosp", "provider"): {"provider_id": "VARCHAR", "provider_type": "VARCHAR"},
    ("hosp", "hcpcsevents"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "chartdate": "DATE",
        "hcpcs_cd": "VARCHAR",
        "seq_num": "INTEGER",
        "short_description": "VARCHAR",
    },
    ("hosp", "d_hcpcs"): {
        "code": "VARCHAR",
        "category": "INTEGER",
        "long_description": "VARCHAR",
        "short_description": "VARCHAR",
    },
    ("hosp", "omr"): {
        "subject_id": "BIGINT",
        "chartdate": "DATE",
        "seq_num": "INTEGER",
        "result_name": "VARCHAR",
        "result_value": "VARCHAR",
    },
    ("icu", "icustays"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "stay_id": "BIGINT",
        "first_careunit": "VARCHAR",
        "last_careunit": "VARCHAR",
        "intime": "TIMESTAMP",
        "outtime": "TIMESTAMP",
        "los": "DOUBLE",
    },
    ("icu", "d_items"): {
        "itemid": "INTEGER",
        "label": "VARCHAR",
        "abbreviation": "VARCHAR",
        "linksto": "VARCHAR",
        "category": "VARCHAR",
        "unitname": "VARCHAR",
        "param_type": "VARCHAR",
        "lownormalvalue": "DOUBLE",
        "highnormalvalue": "DOUBLE",
    },
    ("icu", "chartevents"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "stay_id": "BIGINT",
        "caregiver_id": "BIGINT",
        "charttime": "TIMESTAMP",
        "storetime": "TIMESTAMP",
        "itemid": "INTEGER",
        "value": "VARCHAR",
        "valuenum": "DOUBLE",
        "valueuom": "VARCHAR",
        "warning": "INTEGER",
    },
    ("icu", "inputevents"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "stay_id": "BIGINT",
        "caregiver_id": "BIGINT",
        "starttime": "TIMESTAMP",
        "endtime": "TIMESTAMP",
        "storetime": "TIMESTAMP",
        "itemid": "INTEGER",
        "amount": "DOUBLE",
        "amountuom": "VARCHAR",
        "rate": "DOUBLE",
        "rateuom": "VARCHAR",
        "orderid": "BIGINT",
        "linkorderid": "BIGINT",
        "ordercategoryname": "VARCHAR",
        "secondaryordercategoryname": "VARCHAR",
        "ordercomponenttypedescription": "VARCHAR",
        "ordercategorydescription": "VARCHAR",
        "patientweight": "DOUBLE",
        "totalamount": "DOUBLE",
        "totalamountuom": "VARCHAR",
        "isopenbag": "INTEGER",
        "continueinnextdept": "INTEGER",
        "statusdescription": "VARCHAR",
        "originalamount": "DOUBLE",
        "originalrate": "DOUBLE",
    },
    ("icu", "ingredientevents"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "stay_id": "BIGINT",
        "caregiver_id": "BIGINT",
        "starttime": "TIMESTAMP",
        "endtime": "TIMESTAMP",
        "storetime": "TIMESTAMP",
        "itemid": "INTEGER",
        "amount": "DOUBLE",
        "amountuom": "VARCHAR",
        "rate": "DOUBLE",
        "rateuom": "VARCHAR",
        "orderid": "BIGINT",
        "linkorderid": "BIGINT",
        "statusdescription": "VARCHAR",
        "originalamount": "DOUBLE",
        "originalrate": "DOUBLE",
    },
    ("icu", "outputevents"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "stay_id": "BIGINT",
        "caregiver_id": "BIGINT",
        "charttime": "TIMESTAMP",
        "storetime": "TIMESTAMP",
        "itemid": "INTEGER",
        "value": "DOUBLE",
        "valueuom": "VARCHAR",
    },
    ("icu", "procedureevents"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "stay_id": "BIGINT",
        "caregiver_id": "BIGINT",
        "starttime": "TIMESTAMP",
        "endtime": "TIMESTAMP",
        "storetime": "TIMESTAMP",
        "itemid": "INTEGER",
        "value": "DOUBLE",
        "valueuom": "VARCHAR",
        "location": "VARCHAR",
        "locationcategory": "VARCHAR",
        "orderid": "BIGINT",
        "linkorderid": "BIGINT",
        "ordercategoryname": "VARCHAR",
        "secondaryordercategoryname": "VARCHAR",
        "ordercategorydescription": "VARCHAR",
        "patientweight": "DOUBLE",
        "isopenbag": "INTEGER",
        "continueinnextdept": "INTEGER",
        "statusdescription": "VARCHAR",
        "originalamount": "DOUBLE",
        "originalrate": "DOUBLE",
    },
    ("icu", "datetimeevents"): {
        "subject_id": "BIGINT",
        "hadm_id": "BIGINT",
        "stay_id": "BIGINT",
        "caregiver_id": "BIGINT",
        "charttime": "TIMESTAMP",
        "storetime": "TIMESTAMP",
        "itemid": "INTEGER",
        "value": "TIMESTAMP",
        "valueuom": "VARCHAR",
        "warning": "INTEGER",
    },
    ("icu", "caregiver"): {"caregiver_id": "BIGINT"},
}


@dataclass(frozen=True)
class FileInventoryEntry:
    """A discovered or expected MIMIC source file."""

    module: str
    table: str
    path: Path | None
    found: bool
    expected: bool = True

    @property
    def bronze_table(self) -> str:
        return f"bronze_{self.module}_{self.table}"


def to_snake_case(value: str) -> str:
    """Normalize a source column to lower snake case."""
    value = value.strip().replace("-", "_").replace("/", "_")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    value = re.sub(r"[^0-9a-zA-Z_]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_").lower()


def discover_mimic_files(raw_data_path: str | Path | None) -> list[FileInventoryEntry]:
    """Discover expected and additional MIMIC-IV files under hosp/ and icu/."""
    if raw_data_path is None:
        base = None
    else:
        base = Path(raw_data_path)

    entries: list[FileInventoryEntry] = []
    seen: set[tuple[str, str]] = set()

    for module, tables in EXPECTED_TABLES.items():
        for table in tables:
            found_path = None
            if base is not None:
                module_dir = base / module
                for suffix in (".csv.gz", ".csv"):
                    candidate = module_dir / f"{table}{suffix}"
                    if candidate.exists():
                        found_path = candidate
                        break
            entries.append(
                FileInventoryEntry(module=module, table=table, path=found_path, found=found_path is not None)
            )
            seen.add((module, table))

    if base is not None:
        for module in EXPECTED_TABLES:
            module_dir = base / module
            if not module_dir.exists():
                continue
            for path in sorted(list(module_dir.glob("*.csv")) + list(module_dir.glob("*.csv.gz"))):
                table = path.name.removesuffix(".gz").removesuffix(".csv")
                table = to_snake_case(table)
                if (module, table) not in seen:
                    entries.append(
                        FileInventoryEntry(
                            module=module, table=table, path=path, found=True, expected=False
                        )
                    )
                    seen.add((module, table))

    return entries


def expected_bronze_schema(module: str, table: str) -> dict[str, str]:
    """Return a raw schema plus ingestion metadata for a Bronze table."""
    schema = dict(RAW_SCHEMAS.get((module, table), {}))
    if not schema:
        schema = {"_placeholder": "VARCHAR"}
    schema.update(METADATA_COLUMNS)
    return schema

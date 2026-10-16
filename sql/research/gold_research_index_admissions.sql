-- Private modeling table: one index admission per patient. Public reports only
-- contain aggregates. Outcomes and identifiers never enter predictor columns.
CREATE OR REPLACE TABLE gold_research_index_admissions AS
WITH index_admissions AS (
    SELECT *
    FROM silver_admissions
    WHERE admittime IS NOT NULL AND dischtime IS NOT NULL
    QUALIFY row_number() OVER (PARTITION BY subject_id ORDER BY admittime, hadm_id) = 1
),
first_icu AS (
    SELECT *
    FROM silver_icustays
    QUALIFY row_number() OVER (PARTITION BY hadm_id ORDER BY intime NULLS LAST, stay_id) = 1
),
primary_diagnosis AS (
    SELECT hadm_id, icd_code
    FROM silver_diagnoses
    QUALIFY row_number() OVER (PARTITION BY hadm_id ORDER BY seq_num NULLS LAST, icd_code) = 1
),
diagnosis_flags AS (
    SELECT
        hadm_id,
        max(CASE WHEN icd_code = 'E119' THEN 1 ELSE 0 END) AS diabetes_flag,
        max(CASE WHEN icd_code = 'I509' THEN 1 ELSE 0 END) AS heart_failure_flag,
        max(CASE WHEN icd_code = 'J960' THEN 1 ELSE 0 END) AS respiratory_failure_flag,
        max(CASE WHEN icd_code = 'A419' THEN 1 ELSE 0 END) AS sepsis_proxy_flag
    FROM silver_diagnoses
    GROUP BY hadm_id
),
initial_service AS (
    SELECT hadm_id, curr_service
    FROM silver_services
    QUALIFY row_number() OVER (PARTITION BY hadm_id ORDER BY transfertime NULLS LAST, curr_service) = 1
),
interventions AS (
    SELECT
        icu.stay_id,
        max(CASE WHEN lower(inp.input_label) LIKE '%norepinephrine%'
                  AND inp.starttime <= icu.intime + INTERVAL '24 hours' THEN 1 ELSE 0 END) AS vasopressor_first_24h_flag
    FROM first_icu icu
    LEFT JOIN silver_input_events inp ON icu.stay_id = inp.stay_id
    GROUP BY icu.stay_id
),
ventilation AS (
    SELECT hadm_id,
        max(CASE WHEN lower(coalesce(procedure_label, '')) LIKE '%ventilation%' THEN 1 ELSE 0 END) AS ventilation_procedure_flag
    FROM silver_procedures
    GROUP BY hadm_id
),
next_urgent_admission AS (
    SELECT
        idx.hadm_id,
        min(later.admittime) AS next_urgent_admittime
    FROM index_admissions idx
    LEFT JOIN silver_admissions later
      ON later.subject_id = idx.subject_id
     AND later.hadm_id <> idx.hadm_id
     AND later.admittime > idx.dischtime
     AND later.admittime <= idx.dischtime + INTERVAL '30 days'
     AND later.admission_type IN ('URGENT', 'EW EMER.', 'DIRECT EMER.')
    GROUP BY idx.hadm_id
)
SELECT
    idx.subject_id,
    idx.hadm_id,
    icu.stay_id,
    idx.admittime AS index_admittime,
    idx.dischtime AS index_dischtime,
    coalesce(icu.intime + INTERVAL '24 hours', idx.admittime + INTERVAL '24 hours') AS prediction_time,
    idx.age_at_admission,
    p.gender,
    idx.race,
    idx.admission_type,
    icu.first_careunit,
    svc.curr_service AS initial_service,
    f.heart_rate_min,
    f.heart_rate_max,
    f.heart_rate_mean,
    f.sbp_min,
    f.sbp_max,
    f.sbp_mean,
    f.dbp_min,
    f.dbp_max,
    f.dbp_mean,
    f.mbp_min,
    f.mbp_max,
    f.mbp_mean,
    f.resp_rate_min,
    f.resp_rate_max,
    f.resp_rate_mean,
    f.temperature_min,
    f.temperature_max,
    f.temperature_mean,
    f.spo2_min,
    f.spo2_max,
    f.spo2_mean,
    f.wbc_min,
    f.wbc_max,
    f.wbc_mean,
    f.hemoglobin_min,
    f.hemoglobin_max,
    f.hemoglobin_mean,
    f.platelet_min,
    f.platelet_max,
    f.platelet_mean,
    f.creatinine_min,
    f.creatinine_max,
    f.creatinine_mean,
    f.bun_min,
    f.bun_max,
    f.bun_mean,
    f.sodium_min,
    f.sodium_max,
    f.sodium_mean,
    f.potassium_min,
    f.potassium_max,
    f.potassium_mean,
    f.glucose_min,
    f.glucose_max,
    f.glucose_mean,
    f.lactate_min,
    f.lactate_max,
    f.lactate_mean,
    f.chart_event_count_24h,
    f.lab_event_count_24h,
    f.input_event_count_24h,
    f.output_event_count_24h,
    f.procedure_event_count_24h,
    lab.total_lab_events AS total_lab_events_icu,
    lab.abnormal_lab_rate,
    lab.lactate_measured_during_icu,
    lab.creatinine_measured_during_icu,
    vital.has_heart_rate_24h,
    vital.has_blood_pressure_24h,
    vital.has_resp_rate_24h,
    vital.has_temperature_24h,
    coalesce(flags.diabetes_flag, 0) AS diabetes_flag,
    coalesce(flags.heart_failure_flag, 0) AS heart_failure_flag,
    coalesce(flags.respiratory_failure_flag, 0) AS respiratory_failure_flag,
    coalesce(flags.sepsis_proxy_flag, 0) AS sepsis_proxy_flag,
    coalesce(flags.diabetes_flag, 0) + coalesce(flags.heart_failure_flag, 0)
      + coalesce(flags.respiratory_failure_flag, 0) + coalesce(flags.sepsis_proxy_flag, 0) AS comorbidity_count,
    coalesce(interventions.vasopressor_first_24h_flag, 0) AS vasopressor_first_24h_flag,
    coalesce(ventilation.ventilation_procedure_flag, 0) AS ventilation_procedure_flag,
    idx.hospital_los_days,
    idx.in_hospital_mortality_flag,
    CASE
      WHEN idx.in_hospital_mortality_flag = 1 THEN NULL
      WHEN next_urgent_admittime IS NOT NULL THEN 1
      ELSE 0
    END AS urgent_readmitted_30d,
    CASE
      WHEN d.icd_code = 'I509' THEN 'heart_failure'
      WHEN d.icd_code = 'J189' THEN 'pneumonia'
      WHEN d.icd_code = 'A419' THEN 'sepsis'
      WHEN d.icd_code = 'E119' THEN 'diabetes'
      WHEN d.icd_code = 'J960' THEN 'respiratory_failure'
      ELSE NULL
    END AS primary_disease_class
FROM index_admissions idx
LEFT JOIN silver_patients p ON idx.subject_id = p.subject_id
LEFT JOIN first_icu icu ON idx.hadm_id = icu.hadm_id
LEFT JOIN gold_first_24h_features f ON icu.stay_id = f.stay_id
LEFT JOIN gold_lab_features lab ON icu.stay_id = lab.stay_id
LEFT JOIN gold_vital_features vital ON icu.stay_id = vital.stay_id
LEFT JOIN primary_diagnosis d ON idx.hadm_id = d.hadm_id
LEFT JOIN diagnosis_flags flags ON idx.hadm_id = flags.hadm_id
LEFT JOIN initial_service svc ON idx.hadm_id = svc.hadm_id
LEFT JOIN interventions ON icu.stay_id = interventions.stay_id
LEFT JOIN ventilation ON idx.hadm_id = ventilation.hadm_id
LEFT JOIN next_urgent_admission n ON idx.hadm_id = n.hadm_id;

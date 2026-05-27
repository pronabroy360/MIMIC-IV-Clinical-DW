CREATE OR REPLACE TABLE gold_admission_summary AS
WITH diagnosis_counts AS (
    SELECT hadm_id, count(*) AS diagnosis_count
    FROM silver_diagnoses
    GROUP BY hadm_id
),
procedure_counts AS (
    SELECT hadm_id, count(*) AS procedure_count
    FROM silver_procedures
    GROUP BY hadm_id
),
lab_counts AS (
    SELECT hadm_id, count(*) AS lab_event_count
    FROM silver_labs
    GROUP BY hadm_id
),
micro_counts AS (
    SELECT hadm_id, count(*) AS microbiology_event_count
    FROM silver_microbiology
    GROUP BY hadm_id
),
med_counts AS (
    SELECT hadm_id, count(*) AS medication_count
    FROM silver_medications
    GROUP BY hadm_id
),
icu_counts AS (
    SELECT hadm_id, count(*) AS icu_stay_count
    FROM silver_icustays
    GROUP BY hadm_id
)
SELECT
    a.subject_id,
    a.hadm_id,
    a.admittime,
    a.dischtime,
    a.admission_type,
    a.admission_location,
    a.discharge_location,
    a.insurance,
    a.race,
    a.hospital_los_days,
    a.in_hospital_mortality_flag,
    coalesce(i.icu_stay_count, 0) AS icu_stay_count,
    coalesce(d.diagnosis_count, 0) AS diagnosis_count,
    coalesce(p.procedure_count, 0) AS procedure_count,
    coalesce(l.lab_event_count, 0) AS lab_event_count,
    coalesce(micro.microbiology_event_count, 0) AS microbiology_event_count,
    coalesce(med.medication_count, 0) AS medication_count
FROM silver_admissions a
LEFT JOIN icu_counts i ON a.hadm_id = i.hadm_id
LEFT JOIN diagnosis_counts d ON a.hadm_id = d.hadm_id
LEFT JOIN procedure_counts p ON a.hadm_id = p.hadm_id
LEFT JOIN lab_counts l ON a.hadm_id = l.hadm_id
LEFT JOIN micro_counts micro ON a.hadm_id = micro.hadm_id
LEFT JOIN med_counts med ON a.hadm_id = med.hadm_id;

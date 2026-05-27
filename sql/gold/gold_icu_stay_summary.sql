CREATE OR REPLACE TABLE gold_icu_stay_summary AS
WITH diagnosis_counts AS (
    SELECT hadm_id, count(*) AS diagnosis_count
    FROM silver_diagnoses
    GROUP BY hadm_id
),
lab_24h AS (
    SELECT i.stay_id, count(l.itemid) AS lab_count_first_24h
    FROM silver_icustays i
    LEFT JOIN silver_labs l
        ON i.hadm_id = l.hadm_id
       AND l.charttime >= i.intime
       AND l.charttime < i.intime + INTERVAL '24 hours'
    GROUP BY i.stay_id
),
vital_24h AS (
    SELECT i.stay_id, count(c.itemid) AS vital_count_first_24h
    FROM silver_icustays i
    LEFT JOIN silver_chart_events c
        ON i.stay_id = c.stay_id
       AND c.charttime >= i.intime
       AND c.charttime < i.intime + INTERVAL '24 hours'
       AND c.valuenum IS NOT NULL
    GROUP BY i.stay_id
),
input_counts AS (
    SELECT stay_id, count(*) AS input_event_count
    FROM silver_input_events
    GROUP BY stay_id
),
output_counts AS (
    SELECT stay_id, count(*) AS output_event_count
    FROM silver_output_events
    GROUP BY stay_id
),
procedure_counts AS (
    SELECT stay_id, count(*) AS procedure_event_count
    FROM silver_procedure_events
    GROUP BY stay_id
)
SELECT
    i.subject_id,
    i.hadm_id,
    i.stay_id,
    i.intime,
    i.outtime,
    i.first_careunit,
    i.last_careunit,
    i.icu_los_days,
    i.is_first_icu_stay,
    CASE
        WHEN p.dod IS NOT NULL AND i.intime IS NOT NULL AND i.outtime IS NOT NULL
         AND p.dod BETWEEN i.intime AND i.outtime THEN 1
        WHEN a.deathtime IS NOT NULL AND i.intime IS NOT NULL AND i.outtime IS NOT NULL
         AND a.deathtime BETWEEN i.intime AND i.outtime THEN 1
        ELSE 0
    END AS icu_mortality_flag,
    coalesce(a.in_hospital_mortality_flag, 0) AS hospital_mortality_flag,
    a.age_at_admission,
    p.gender,
    a.race,
    a.admission_type,
    coalesce(d.diagnosis_count, 0) AS diagnosis_count,
    coalesce(l.lab_count_first_24h, 0) AS lab_count_first_24h,
    coalesce(v.vital_count_first_24h, 0) AS vital_count_first_24h,
    coalesce(inp.input_event_count, 0) AS input_event_count,
    coalesce(outp.output_event_count, 0) AS output_event_count,
    coalesce(proc.procedure_event_count, 0) AS procedure_event_count
FROM silver_icustays i
LEFT JOIN silver_admissions a ON i.hadm_id = a.hadm_id
LEFT JOIN silver_patients p ON i.subject_id = p.subject_id
LEFT JOIN diagnosis_counts d ON i.hadm_id = d.hadm_id
LEFT JOIN lab_24h l ON i.stay_id = l.stay_id
LEFT JOIN vital_24h v ON i.stay_id = v.stay_id
LEFT JOIN input_counts inp ON i.stay_id = inp.stay_id
LEFT JOIN output_counts outp ON i.stay_id = outp.stay_id
LEFT JOIN procedure_counts proc ON i.stay_id = proc.stay_id;

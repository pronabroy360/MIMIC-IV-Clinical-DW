CREATE OR REPLACE TABLE gold_first_24h_features AS
WITH vital_events AS (
    SELECT
        i.stay_id,
        lower(c.chart_label) AS label,
        c.valuenum
    FROM silver_icustays i
    JOIN silver_chart_events c
        ON i.stay_id = c.stay_id
       AND c.charttime >= i.intime
       AND c.charttime < i.intime + INTERVAL '24 hours'
    WHERE c.valuenum IS NOT NULL
),
vitals AS (
    SELECT
        stay_id,
        min(valuenum) FILTER (WHERE label LIKE '%heart rate%') AS heart_rate_min,
        max(valuenum) FILTER (WHERE label LIKE '%heart rate%') AS heart_rate_max,
        avg(valuenum) FILTER (WHERE label LIKE '%heart rate%') AS heart_rate_mean,
        min(valuenum) FILTER (WHERE label LIKE '%systolic%' OR label IN ('arterial blood pressure systolic', 'non invasive blood pressure systolic')) AS sbp_min,
        max(valuenum) FILTER (WHERE label LIKE '%systolic%' OR label IN ('arterial blood pressure systolic', 'non invasive blood pressure systolic')) AS sbp_max,
        avg(valuenum) FILTER (WHERE label LIKE '%systolic%' OR label IN ('arterial blood pressure systolic', 'non invasive blood pressure systolic')) AS sbp_mean,
        min(valuenum) FILTER (WHERE label LIKE '%diastolic%' OR label IN ('arterial blood pressure diastolic', 'non invasive blood pressure diastolic')) AS dbp_min,
        max(valuenum) FILTER (WHERE label LIKE '%diastolic%' OR label IN ('arterial blood pressure diastolic', 'non invasive blood pressure diastolic')) AS dbp_max,
        avg(valuenum) FILTER (WHERE label LIKE '%diastolic%' OR label IN ('arterial blood pressure diastolic', 'non invasive blood pressure diastolic')) AS dbp_mean,
        min(valuenum) FILTER (WHERE label LIKE '%mean%blood pressure%' OR label IN ('arterial blood pressure mean', 'non invasive blood pressure mean')) AS mbp_min,
        max(valuenum) FILTER (WHERE label LIKE '%mean%blood pressure%' OR label IN ('arterial blood pressure mean', 'non invasive blood pressure mean')) AS mbp_max,
        avg(valuenum) FILTER (WHERE label LIKE '%mean%blood pressure%' OR label IN ('arterial blood pressure mean', 'non invasive blood pressure mean')) AS mbp_mean,
        min(valuenum) FILTER (WHERE label LIKE '%respiratory rate%') AS resp_rate_min,
        max(valuenum) FILTER (WHERE label LIKE '%respiratory rate%') AS resp_rate_max,
        avg(valuenum) FILTER (WHERE label LIKE '%respiratory rate%') AS resp_rate_mean,
        min(valuenum) FILTER (WHERE label LIKE '%temperature%') AS temperature_min,
        max(valuenum) FILTER (WHERE label LIKE '%temperature%') AS temperature_max,
        avg(valuenum) FILTER (WHERE label LIKE '%temperature%') AS temperature_mean,
        min(valuenum) FILTER (WHERE label LIKE '%o2 saturation%' OR label LIKE '%spo2%') AS spo2_min,
        max(valuenum) FILTER (WHERE label LIKE '%o2 saturation%' OR label LIKE '%spo2%') AS spo2_max,
        avg(valuenum) FILTER (WHERE label LIKE '%o2 saturation%' OR label LIKE '%spo2%') AS spo2_mean,
        count(*) AS chart_event_count_24h
    FROM vital_events
    GROUP BY stay_id
),
lab_events AS (
    SELECT
        i.stay_id,
        lower(l.lab_label) AS label,
        l.valuenum
    FROM silver_icustays i
    JOIN silver_labs l
        ON i.hadm_id = l.hadm_id
       AND l.charttime >= i.intime
       AND l.charttime < i.intime + INTERVAL '24 hours'
    WHERE l.valuenum IS NOT NULL
),
labs AS (
    SELECT
        stay_id,
        min(valuenum) FILTER (WHERE label LIKE '%white blood%' OR label LIKE '%wbc%') AS wbc_min,
        max(valuenum) FILTER (WHERE label LIKE '%white blood%' OR label LIKE '%wbc%') AS wbc_max,
        avg(valuenum) FILTER (WHERE label LIKE '%white blood%' OR label LIKE '%wbc%') AS wbc_mean,
        min(valuenum) FILTER (WHERE label LIKE '%hemoglobin%') AS hemoglobin_min,
        max(valuenum) FILTER (WHERE label LIKE '%hemoglobin%') AS hemoglobin_max,
        avg(valuenum) FILTER (WHERE label LIKE '%hemoglobin%') AS hemoglobin_mean,
        min(valuenum) FILTER (WHERE label LIKE '%platelet%') AS platelet_min,
        max(valuenum) FILTER (WHERE label LIKE '%platelet%') AS platelet_max,
        avg(valuenum) FILTER (WHERE label LIKE '%platelet%') AS platelet_mean,
        min(valuenum) FILTER (WHERE label LIKE '%creatinine%') AS creatinine_min,
        max(valuenum) FILTER (WHERE label LIKE '%creatinine%') AS creatinine_max,
        avg(valuenum) FILTER (WHERE label LIKE '%creatinine%') AS creatinine_mean,
        min(valuenum) FILTER (WHERE label LIKE '%urea nitrogen%' OR label LIKE '%bun%') AS bun_min,
        max(valuenum) FILTER (WHERE label LIKE '%urea nitrogen%' OR label LIKE '%bun%') AS bun_max,
        avg(valuenum) FILTER (WHERE label LIKE '%urea nitrogen%' OR label LIKE '%bun%') AS bun_mean,
        min(valuenum) FILTER (WHERE label LIKE '%sodium%') AS sodium_min,
        max(valuenum) FILTER (WHERE label LIKE '%sodium%') AS sodium_max,
        avg(valuenum) FILTER (WHERE label LIKE '%sodium%') AS sodium_mean,
        min(valuenum) FILTER (WHERE label LIKE '%potassium%') AS potassium_min,
        max(valuenum) FILTER (WHERE label LIKE '%potassium%') AS potassium_max,
        avg(valuenum) FILTER (WHERE label LIKE '%potassium%') AS potassium_mean,
        min(valuenum) FILTER (WHERE label LIKE '%glucose%') AS glucose_min,
        max(valuenum) FILTER (WHERE label LIKE '%glucose%') AS glucose_max,
        avg(valuenum) FILTER (WHERE label LIKE '%glucose%') AS glucose_mean,
        min(valuenum) FILTER (WHERE label LIKE '%lactate%') AS lactate_min,
        max(valuenum) FILTER (WHERE label LIKE '%lactate%') AS lactate_max,
        avg(valuenum) FILTER (WHERE label LIKE '%lactate%') AS lactate_mean,
        count(*) AS lab_event_count_24h
    FROM lab_events
    GROUP BY stay_id
),
input_counts AS (
    SELECT i.stay_id, count(inp.itemid) AS input_event_count_24h
    FROM silver_icustays i
    LEFT JOIN silver_input_events inp
        ON i.stay_id = inp.stay_id
       AND inp.starttime >= i.intime
       AND inp.starttime < i.intime + INTERVAL '24 hours'
    GROUP BY i.stay_id
),
output_counts AS (
    SELECT i.stay_id, count(outp.itemid) AS output_event_count_24h
    FROM silver_icustays i
    LEFT JOIN silver_output_events outp
        ON i.stay_id = outp.stay_id
       AND outp.charttime >= i.intime
       AND outp.charttime < i.intime + INTERVAL '24 hours'
    GROUP BY i.stay_id
),
procedure_counts AS (
    SELECT i.stay_id, count(proc.itemid) AS procedure_event_count_24h
    FROM silver_icustays i
    LEFT JOIN silver_procedure_events proc
        ON i.stay_id = proc.stay_id
       AND proc.starttime >= i.intime
       AND proc.starttime < i.intime + INTERVAL '24 hours'
    GROUP BY i.stay_id
)
SELECT
    s.subject_id,
    s.hadm_id,
    s.stay_id,
    v.heart_rate_min,
    v.heart_rate_max,
    v.heart_rate_mean,
    v.sbp_min,
    v.sbp_max,
    v.sbp_mean,
    v.dbp_min,
    v.dbp_max,
    v.dbp_mean,
    v.mbp_min,
    v.mbp_max,
    v.mbp_mean,
    v.resp_rate_min,
    v.resp_rate_max,
    v.resp_rate_mean,
    v.temperature_min,
    v.temperature_max,
    v.temperature_mean,
    v.spo2_min,
    v.spo2_max,
    v.spo2_mean,
    l.wbc_min,
    l.wbc_max,
    l.wbc_mean,
    l.hemoglobin_min,
    l.hemoglobin_max,
    l.hemoglobin_mean,
    l.platelet_min,
    l.platelet_max,
    l.platelet_mean,
    l.creatinine_min,
    l.creatinine_max,
    l.creatinine_mean,
    l.bun_min,
    l.bun_max,
    l.bun_mean,
    l.sodium_min,
    l.sodium_max,
    l.sodium_mean,
    l.potassium_min,
    l.potassium_max,
    l.potassium_mean,
    l.glucose_min,
    l.glucose_max,
    l.glucose_mean,
    l.lactate_min,
    l.lactate_max,
    l.lactate_mean,
    coalesce(v.chart_event_count_24h, 0) AS chart_event_count_24h,
    coalesce(l.lab_event_count_24h, 0) AS lab_event_count_24h,
    coalesce(inp.input_event_count_24h, 0) AS input_event_count_24h,
    coalesce(outp.output_event_count_24h, 0) AS output_event_count_24h,
    coalesce(proc.procedure_event_count_24h, 0) AS procedure_event_count_24h,
    s.icu_mortality_flag,
    s.hospital_mortality_flag,
    s.icu_los_days,
    a.hospital_los_days
FROM gold_icu_stay_summary s
LEFT JOIN gold_admission_summary a ON s.hadm_id = a.hadm_id
LEFT JOIN vitals v ON s.stay_id = v.stay_id
LEFT JOIN labs l ON s.stay_id = l.stay_id
LEFT JOIN input_counts inp ON s.stay_id = inp.stay_id
LEFT JOIN output_counts outp ON s.stay_id = outp.stay_id
LEFT JOIN procedure_counts proc ON s.stay_id = proc.stay_id;

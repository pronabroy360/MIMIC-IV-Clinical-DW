CREATE OR REPLACE TABLE gold_vital_features AS
WITH stay_vitals AS (
    SELECT
        i.stay_id,
        i.subject_id,
        i.hadm_id,
        lower(c.chart_label) AS chart_label,
        c.valuenum,
        c.charttime
    FROM silver_icustays i
    LEFT JOIN silver_chart_events c
        ON i.stay_id = c.stay_id
       AND c.charttime >= i.intime
       AND c.charttime < i.intime + INTERVAL '24 hours'
)
SELECT
    subject_id,
    hadm_id,
    stay_id,
    count(chart_label) AS vital_event_count_24h,
    max(CASE WHEN chart_label LIKE '%heart rate%' THEN 1 ELSE 0 END) AS has_heart_rate_24h,
    max(CASE WHEN chart_label LIKE '%blood pressure%' OR chart_label LIKE '%systolic%' THEN 1 ELSE 0 END) AS has_blood_pressure_24h,
    max(CASE WHEN chart_label LIKE '%respiratory rate%' THEN 1 ELSE 0 END) AS has_resp_rate_24h,
    max(CASE WHEN chart_label LIKE '%temperature%' THEN 1 ELSE 0 END) AS has_temperature_24h,
    max(CASE WHEN chart_label LIKE '%o2 saturation%' OR chart_label LIKE '%spo2%' THEN 1 ELSE 0 END) AS has_spo2_24h
FROM stay_vitals
GROUP BY subject_id, hadm_id, stay_id;

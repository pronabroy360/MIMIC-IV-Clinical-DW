CREATE OR REPLACE TABLE silver_diagnoses AS
SELECT
    try_cast(d.subject_id AS BIGINT) AS subject_id,
    try_cast(d.hadm_id AS BIGINT) AS hadm_id,
    try_cast(d.seq_num AS INTEGER) AS seq_num,
    cast(d.icd_code AS VARCHAR) AS icd_code,
    try_cast(d.icd_version AS INTEGER) AS icd_version,
    cast(dd.long_title AS VARCHAR) AS diagnosis_label
FROM bronze_hosp_diagnoses_icd d
LEFT JOIN bronze_hosp_d_icd_diagnoses dd
    ON cast(d.icd_code AS VARCHAR) = cast(dd.icd_code AS VARCHAR)
   AND try_cast(d.icd_version AS INTEGER) = try_cast(dd.icd_version AS INTEGER)
WHERE try_cast(d.subject_id AS BIGINT) IS NOT NULL
  AND try_cast(d.hadm_id AS BIGINT) IS NOT NULL;

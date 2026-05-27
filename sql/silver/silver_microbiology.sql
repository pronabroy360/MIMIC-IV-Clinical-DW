CREATE OR REPLACE TABLE silver_microbiology AS
SELECT
    try_cast(subject_id AS BIGINT) AS subject_id,
    try_cast(hadm_id AS BIGINT) AS hadm_id,
    try_cast(microevent_id AS BIGINT) AS microevent_id,
    try_cast(chartdate AS DATE) AS chartdate,
    try_cast(charttime AS TIMESTAMP) AS charttime,
    cast(spec_type_desc AS VARCHAR) AS specimen_type,
    cast(test_name AS VARCHAR) AS test_name,
    cast(org_name AS VARCHAR) AS organism_name,
    cast(ab_name AS VARCHAR) AS antibiotic_name,
    cast(interpretation AS VARCHAR) AS interpretation
FROM bronze_hosp_microbiologyevents
WHERE try_cast(subject_id AS BIGINT) IS NOT NULL;

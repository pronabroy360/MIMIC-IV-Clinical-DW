CREATE OR REPLACE TABLE silver_provider_orders AS
SELECT
    cast(poe_id AS VARCHAR) AS poe_id,
    try_cast(poe_seq AS INTEGER) AS poe_seq,
    try_cast(subject_id AS BIGINT) AS subject_id,
    try_cast(hadm_id AS BIGINT) AS hadm_id,
    try_cast(ordertime AS TIMESTAMP) AS ordertime,
    cast(order_type AS VARCHAR) AS order_type,
    cast(order_subtype AS VARCHAR) AS order_subtype,
    cast(transaction_type AS VARCHAR) AS transaction_type,
    cast(order_status AS VARCHAR) AS order_status
FROM bronze_hosp_poe
WHERE try_cast(subject_id AS BIGINT) IS NOT NULL;

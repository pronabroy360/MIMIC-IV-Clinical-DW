-- Bronze ICU tables are created by the Python ingestion layer so large CSV/GZ
-- files can be loaded directly by DuckDB. No row-level exports are produced.
SELECT 1 AS bronze_icu_layer_ready;

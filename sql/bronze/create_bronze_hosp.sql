-- Bronze Hosp tables are created by the Python ingestion layer so CSV/GZ files
-- can be discovered dynamically. This file is intentionally lightweight and
-- exists to keep layer execution explicit and auditable.
SELECT 1 AS bronze_hosp_layer_ready;

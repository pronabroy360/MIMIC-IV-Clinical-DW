# Project Overview

This project builds a reproducible clinical data warehouse and analytics layer using MIMIC-IV structured EHR data. It is designed to demonstrate production-style clinical data engineering for biomedical informatics, healthcare AI, EHR data mining, clinical NLP, and responsible medical LLM research.

The core use cases are:

- ingest MIMIC-IV demo or credentialed full local files into DuckDB;
- seed a tiny synthetic, public-safe local demo when real files are unavailable;
- transform hospital and ICU tables into Bronze, Silver, and Gold warehouse layers;
- define reusable ICU and diagnosis-based cohorts;
- engineer first-24-hour ICU features without future leakage;
- validate schemas, keys, date ranges, and aggregate volumes;
- expose aggregate dashboards, API endpoints, and guarded natural-language SQL.

This is not a clinical decision support product. It does not diagnose, treat, predict outcomes for real-time care, or recommend interventions.

## Research Framing

The project emphasizes reproducible cohort construction, transparent feature windows, and privacy-safe query interfaces. It is meant to be a professor-facing artifact showing readiness for research in clinical data warehousing, ICU analytics, and schema-grounded LLM systems.

## Limitations

Demo mode is small and useful for engineering validation only. The synthetic seed is fake data for software demonstration only. Full analyses require credentialed MIMIC-IV access and careful study-specific validation. MIMIC-IV is single-center and deidentified with shifted dates, so results may not generalize to other health systems.

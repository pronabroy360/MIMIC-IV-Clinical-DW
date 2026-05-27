# Limitations And Ethics

This repository is for research engineering demonstration and education. It is not for clinical care.

MIMIC-IV is deidentified but restricted. Users must comply with the applicable Data Use Agreement and must not attempt re-identification of patients, providers, or institutions.

Important limitations:

- single-center source data;
- shifted dates and deidentified records;
- possible coding, measurement, and documentation bias;
- limited generalizability to other hospitals;
- demo data is too small for clinical conclusions;
- diagnosis and ventilation cohorts in this repo are transparent proxies, not validated phenotypes.

LLM use is limited to schema-grounded aggregate SQL. The assistant must not expose patient-level records or claim clinical authority.

# Cohort Definitions

Cohort SQL templates live under `sql/cohorts/`. Each template defines private row-level logic in CTEs but returns aggregate summaries for dashboard/API use.

## Adult First ICU Stay

First ICU stay per subject, age at admission at least 18, valid ICU intime/outtime, and ICU length of stay greater than zero.

## Sepsis-Like Proxy

Diagnosis-based proxy using sepsis, septic, infection, pneumonia, and bacteremia terms plus simple organ dysfunction label proxies. This does not claim Sepsis-3 compliance.

## Heart Failure

Diagnosis-based proxy using ICD labels and broad heart failure code patterns.

## Ventilation-Like Proxy

Procedure and chart label proxy using ventilation and intubation terms.

## High Lab Utilization

Top quartile of lab event counts within ICU stays in the currently loaded dataset.

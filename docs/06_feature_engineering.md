# Feature Engineering

The first-24-hour feature table uses:

```text
icu_intime <= event_time < icu_intime + 24 hours
```

This prevents later ICU events from leaking into early prediction-style feature rows.

## Feature Groups

Vitals are derived from ICU chart events using transparent label matching for heart rate, blood pressure, respiratory rate, temperature, and oxygen saturation.

Labs are derived from hospital lab events linked to ICU stays by admission and time window. Features include WBC, hemoglobin, platelets, creatinine, BUN, sodium, potassium, glucose, and lactate.

Utilization features count chart, lab, input, output, and procedure events in the first 24 hours.

## Missingness

Missing measurements are preserved as nulls. Completeness is reported as aggregate rates rather than imputed silently.

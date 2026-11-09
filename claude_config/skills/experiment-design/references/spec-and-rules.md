# Spec and decision-rule schemas

## check
```json
{"check": "target_proxy", "params": {"threshold": 0.98, "max_future_lag": 3, "exclude": []}, "data_via": "profile"}
```
- `data_via: "profile"` → data is read from the confirmed `data_source` file, without the adapter. It is a raw-data fact, so it can be Verified.
- `pmi checks` lists the available checks, the profile fields they need and which ones need the adapter's split.

| check | params |
|---|---|
| static_patterns | `patterns` (filter), `files` |
| key_uniqueness | — |
| target_proxy | `threshold`, `max_future_lag`, `exclude`, `columns` |
| temporal_overlap | `tolerance_share` |
| split_duplicates | `exclude`, `tolerance_rows` |
| entity_overlap | `expect_disjoint` (if true, overlap = defect) |
| missing_rates | `max_rate` |

Rule: `{"type": "defect_found"}`

## baseline
`pmi baseline [--replicates 3] [--min-gap 0.05]`. This command creates the hypothesis and the experiment itself.
Rule: `{"type": "baseline_gap", "min_relative_gap": 0.05}`
- gap ≤ `policy.evidence.baseline_reproduction_rel_tol` → reproduced (Rejected) and adapter fidelity = confirmed
- gap ≥ min_relative_gap → not reproducible. Without a human-confirmed adapter the result is Inconclusive, because the gap may come from the adapter.

## amplify
```json
{"injector": "missing|outliers|shift|time_lag", "columns": ["..."], "where": "test|train|both",
 "replicates": 3, "seed": 0, "metrics": ["mae","bias"], "levels": [0.1, 0.3],
 "params": {"kind": "additive|multiplicative"}}
```
- Without `levels`, levels are computed automatically: a relative ladder (1×, 2×, 3×, 5× of the measured base) or an absolute ladder (A1..An, `config/amplification.yaml`).
- Labels: `"1x","2x","3x","5x"` for the relative ladder, `"A1","A2",...` for the absolute ladder. `"max"` can be used for the last level.
- `time_lag` requires `time_column` and `entity_keys` to be confirmed.

Rule: `{"type": "eaf", "metric": "mae", "level": "3x", "min_eaf": 1.2}`
- pass: mean EAF ≥ min_eaf **and** minimum EAF ≥ noise floor. A model crash in any replicate also counts as pass.
- fail: maximum EAF < min_eaf
- otherwise: inconclusive

## ablation
```json
{"features": ["f1","f2"], "mode": "individual|cumulative", "where": "test|both", "replicates": 3}
```
- `where: test`: trained model, feature held constant. Measures how much the model relies on that feature.
- `where: both`: retrain without the feature. Measures whether other features can compensate for the information.
- Rule: `{"type":"eaf","metric":"mae","level":"<feature name or +feature>","min_eaf":1.5}`

## EAF
`EAF = loss(stress) / loss(1×)`, computed per seed. For higher-is-better metrics (accuracy, r2, auc, f1) loss = 1 − value. For signed metrics (bias) loss = |value|.

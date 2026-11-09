---
name: leakage-hunting
description: Search for the leakage types that invalidate an evaluation (target, look-ahead, temporal split, preprocessing, duplicates/groups, tuning on test) without domain assumptions, and test each with pmi checks. Use first in every project that reports high performance.
---

# Leakage hunting

If there is leakage, every other finding (amplification included) rests on a fake success. That is why leakage is hunted first.

## 1. Static traces
`pmi scan` → `static_suspicions`. For each one, open the code in the copy and read the context:
- `preprocessing_fit_before_split`: is the fitted object really a transformer? Does the fitted data include test rows?
- `random_split_with_temporal_data`: are rows really observations that must be predicted forward in time? Or is the date just an attribute in cross-sectional data? The answer depends on `prediction_horizon` and `business_context`.
- `negative_shift_future_values`: does the result of `shift(-k)` build the target (legitimate) or a feature (leakage)?
- `fit_on_evaluation_data`: is fitting or tuning done with test data?

A static trace is a hypothesis. Register it with `--kind defect --refs <location>`.

## 2. Data traces
- `check target_proxy` (`data_via: profile`): finds features equal or nearly equal to the target or to a **future** value of the target. It automatically separates features explained by a past-lag relationship (legitimate lags).
- `check key_uniqueness`: duplicate rows can pierce the split.

## 3. Split traces (adapter required; fidelity matters)
- `check temporal_overlap`: are there training dates after the start of the test period? Second indicator: share of test rows older than the latest training row.
- `check split_duplicates`: does a test row appear verbatim in training?
- `check entity_overlap` (`expect_disjoint: true` only if the project claims to generalise to new entities): tests the claim of generalising to unseen units.

## 4. Measuring impact
Once a leak is Verified, measure its impact:
- `ablation` (`where: both`): remove the leaky feature and retrain. The EAF gives a lower bound on the fake success the leak provides. If other features also feed on the leak, this is a lower bound.
- Re-evaluation with a correct split = stage 6 (counterfactual). For now, write it as a `--fix` proposal.

## Decoys
- A **past** lag feature with 0.9+ correlation to the target is not leakage.
- In cross-sectional data (each row an independent unit), a random split can be legitimate. Have `unit_of_analysis` confirmed first.
- Target encoding done within train is not leakage; done on all data, it is.

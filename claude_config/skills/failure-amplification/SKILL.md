---
name: failure-amplification
description: Find a model's robustness curve, Error Amplification Factor and unacceptability threshold by scaling a problem's condition (not the error) 1×→2×→3×→5× in a controlled way. Use in the Amplify phase, for verified defects and critical inputs.
---

# Failure amplification

## Principle
**The condition that causes the error is amplified, not the error rate.** When the missing share grows 3×, the error may grow 1.4× or 5×. This relationship is discovered by experiment.

- `1×` is the project **as it is**: whatever the measured base condition is.
- If the base > 0, a **relative ladder** is used: 2×, 3×, 5× = base × N. The realised condition is measured separately as `condition_realized` and reported.
- If the base = 0, or the condition has no natural base (shift, lag), an **absolute ladder** is used: A1, A2... These cannot be described as "N times".
- Levels beyond the physical/logical limit are clamped and flagged `limit_exceeded`. The report shows "EXCEEDED".

## What to amplify
1. **Verified defects:** what happens if the size of the defect grows?
2. **Business-critical inputs from the profile:** which features may arrive late or missing at prediction time? Derive this from `feature_availability` and `business_context`.
3. **Features with the highest EAF in ablation:** stress first what the model depends on.

## Injector ↔ problem family
| Problem | Injector | Condition measure |
|---|---|---|
| Missing data | `missing` | share of missing cells |
| Outliers | `outliers` | share of rows with robust-z > threshold |
| Distribution shift | `shift` | shift in std units (or multiplicative) |
| Delayed/stale feature | `time_lag` | number of periods (within entity) |
| Feature dependency | `ablation` | removed feature(s) |

Not yet supported (stockout/censoring, leakage scope, subgroup representation, compound scenarios) will come later. Register them as hypotheses and report "no test tool".

## Failure threshold discovery
- If `acceptable_threshold` is confirmed (`{"metric":"mae","max":5.0}`), the result's `threshold.first_level` shows the first level at which performance becomes unacceptable.
- If not confirmed, only the curve is reported. Do not invent a threshold; ask the human.

## Reading the results
- **Is the EAF curve monotonic?** If not, it may be noise or interaction. Increase replicates or accept Inconclusive.
- **Elasticity:** log(EAF)/log(N). Below 1 means error grows slower than the input corruption; above 1 means error grows faster than the condition.
- **Failures > 0:** the model crashed under the condition, e.g. it cannot handle NaN. This is a separate and strong finding.
- **Low EAF for where=test but high for where=train:** the problem is training-data quality, not production inputs.

## Reporting language
"When the missing share (measured base 4.8%) was raised to 3×, MAE EAF=1.35 [1.31, 1.40] (E-012, Simulated)." Do not write this as "production will get 35% worse".

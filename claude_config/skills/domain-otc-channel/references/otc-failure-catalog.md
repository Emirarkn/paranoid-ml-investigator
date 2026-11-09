# OTC channel failure catalog

For each family: its counterpart in the general catalog (`skeptical-hypotheses/references/failure-catalog.md`), signals, falsification test and current tool status.

| # | Family | General counterpart | Signal | Falsification test | Tool |
|---|---|---|---|---|---|
| O1 | Sell-in modelled as demand | B2 proxy target | Target column is wholesaler loading, but the decision concerns consumer demand | Refuted if the user confirms the target matches the decision need | Human question → Suspected / Rejected |
| O2 | Sales during stockout = demand | B1 censored target | Stock flag or runs of zero sales; jump after the stockout | Refuted if model error and bias do not change when stockout rows are removed | Partial: no segment metric yet (stage 5) |
| O3 | Channel stock wave | B1 + C2 | Sell-in peak before a price increase or promotion, then several low sell-in periods; sell-out flat | Refuted if the cumulative sell-in minus sell-out gap oscillates around zero | Data analysis, Suspected |
| O4 | Sell-out / panel delay | A2 / D4 | Market data arrives after period end but is used as a feature in the same period | Refuted if `amplify time_lag` at the real delay gives EAF ≈ 1 | ✅ `time_lag` |
| O5 | Promotion calendar leakage | A2 | Promotion feature derived from executed promotions (not the plan) | Refuted if `feature_availability` = known_at_prediction is confirmed | Human question + ablation |
| O6 | Overfitting to a single season | B4 | The test period covers a single season | Refuted if rolling-origin errors are similar across seasons | Stage 5 (walk-forward) |
| O7 | Returns and correction rows | C2 | Negative quantities, period-end corrections | Refuted if the metric does not change when negative rows are removed | Data scan (`share_negative`) |
| O8 | New product effect | B4 | Entities with short history distort the aggregate metric | Segment metric (stage 5) | Suspected |
| O9 | Wholesaler / region aggregation mismatch | B4 | Model at national level, decision at wholesaler level | Refuted if the decision level equals the profile level | Human question |

## Typical stress scenarios for the channel (amplify)
| Scenario | Injector | Realism note |
|---|---|---|
| Sell-out report arrives incomplete (some wholesalers don't report) | `missing` (sell-out features, `where=test`) | 5× is often unrealistic; write the limit in the report |
| Panel data arrives 1–3 periods late | `time_lag` | Learn the real delay from the human |
| Price shock | `shift` (price index, multiplicative) | If prices are regulated, ask the user for the bounds |
| Promotion information is lost | `ablation` (promotion feature) | — |

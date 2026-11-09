# Failure catalog (domain-agnostic)

For each family: which success observation it can explain, the typical signals, and the `pmi` test available today. Domain examples in parentheses are **examples only**. If a family does not fit the project, dismiss it with a reason.

## A. Evaluation validity (these first)
| Family | Signal | pmi test |
|---|---|---|
| A1 Target leakage | Feature derived from the target, column nearly equal to the target | `check target_proxy` (+ future-lag check when time/entity are confirmed) |
| A2 Look-ahead information | `shift(-k)`, joins on future dates, period-end totals | `check static_patterns` (negative_shift), `check target_proxy` |
| A3 Temporal split violation | Random split / shuffled KFold on a time series | `check static_patterns`, `check temporal_overlap` |
| A4 Preprocessing leakage | Scaler/encoder/imputer fitted on all data before the split | `check static_patterns` (preprocessing_fit_before_split); impact via ablation/adapter comparison (stage 6) |
| A5 Row/group duplicates | Same row or same entity in train and test | `check split_duplicates`, `check entity_overlap` |
| A6 Report not reproducible | Reported metric produced with different data/code | `pmi baseline` |
| A7 Tuning on test | Hyperparameters/thresholds chosen by looking at the test set | `check static_patterns` (fit_on_evaluation_data); code reading |

## B. Target and metric definition
| Family | Signal | pmi test |
|---|---|---|
| B1 Censored/truncated target | The observed value is a lower bound of the true quantity (e.g. sales ≠ demand under supply constraints, capacity ceiling, survivorship) | Data check + human question; for now `missing_rates`/`key_uniqueness` and code reading; usually ends Suspected/Inconclusive |
| B2 Proxy target | What is modelled is not what the business decision needs | Human question (`business_context`) |
| B3 Metric–business mismatch | Average error is good but bad in a business-critical segment, or bias is signed | `baseline` metric set; segment analysis in stage 5+ |
| B4 Aggregation fallacy | Good in aggregate, bad in sub-units | Stage 5+ (segment backtest) |

## C. Data quality and structure
| Family | Signal | pmi test |
|---|---|---|
| C1 Missing data | High missing share, or changing over time | `check missing_rates`; robustness via `amplify missing` |
| C2 Outliers | Tails, sentinel values (e.g. -1, 9999) | `amplify outliers`; data scan |
| C3 Key uniqueness | (entity, time) duplicates, double counting | `check key_uniqueness` |
| C4 Constant/ID columns | A column with `unique_ratio≈1` used as a feature | scan `id_like_columns` + code reading |

## D. Robustness (sensitivity) — all at most Simulated
| Family | Question | pmi test |
|---|---|---|
| D1 Missing inputs | What if the missing share becomes 2×/3×/5×? | `amplify missing` |
| D2 Outliers/shocks | What if the outlier share grows? | `amplify outliers` |
| D3 Distribution shift | What if an input distribution shifts by k·std? | `amplify shift` |
| D4 Delayed/stale inputs | What if a feature arrives k periods late? | `amplify time_lag` (time + entity must be confirmed) |
| D5 Feature dependency | What if a critical feature disappears? | `ablation` (individual / cumulative) |
| D6 Training-data quality | What if the training data is corrupted? | `amplify ... where=train` |

## E. LLM / RAG components (stage 7+)
Hallucination, answers outside the sources, overconfidence on ambiguous tasks. There is no pmi test for these yet. If present, register them as hypotheses; if they cannot be tested they stay Suspected and appear in the report as "no test tool".

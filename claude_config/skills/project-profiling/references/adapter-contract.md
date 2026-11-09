# Adapter contract

```python
class Adapter:
    sources: dict[str, str]          # {"load_data": "src/data.py:12", "split": "train.py:40", ...}
    target: str                      # must equal the confirmed profile target
    def load_data(self) -> pd.DataFrame          # one row per prediction unit; includes the target column
    def split(self, df) -> (train_index, test_index)   # index LABELS, disjoint, the project's protocol
    def fit(self, train_df, seed=0) -> model     # seed=0 == the project's own configuration
    def predict(self, model, df) -> 1-D array
    def predict_proba(self, model, df) -> 1-D array   # optional, positive-class probability for classification
```

`pmi adapter validate` checks: target exists, `load_data` returns a DataFrame, the index is unique, the split is disjoint and non-empty, prediction length is right, predictions are finite. It also checks whether any `TODO` is left in `sources`.

## Patterns

**If the project has functions, import them** (`TARGET_ROOT` is already on `sys.path`):
```python
from src.features import build_features      # project module from the copy
def load_data(self):
    raw = pd.read_csv(TARGET_ROOT / "data/raw.csv")
    return build_features(raw)
```

**If the project is a single script**, move the relevant lines into the adapter and record the line numbers in `sources`.

**Rolling-origin / backtest protocol:** the contract currently expects a single train/test split. If the project has several folds, pick the fold where the reported metric is computed and note it in `sources["split"]`. Multi-fold support is stage 5+ work.

**If the project's preprocessing is fitted on all data** (e.g. scaler fit, then split): `fit()` only sees train. If an exact mirror is needed, apply the same global transformation inside `load_data` and state it explicitly in `sources`. This is probably a hypothesis (`preprocessing_fit_before_split`).

## Surrogate config
```json
{"data_source": "data/table.csv", "target": "y", "features": ["a","b"],
 "task_type": "regression",
 "split": {"kind": "temporal", "time_column": "date", "test_fraction": 0.2}}
```
HistGradientBoosting handles NaN natively. Missing-data tests run with a surrogate therefore say almost nothing about the project's own model.

"""Generate synthetic benchmark projects with PLANTED defects and harmless DECOYS.

    python examples/make_examples.py <output_dir>

The projects deliberately use different vocabularies (store/week, customer/signup) so the
harness is tested on learning a project, not on recognising one domain.

The answer key is written to <output_dir>/_answer_key.json. The agent must NOT read it during
an investigation (denied in .claude/settings.json); it is only used to score the agent
(Detection Quality / False Positive Control, design doc section 11).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RETAIL_TRAIN = '''import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("data/store_week.csv")
df["week_start"] = pd.to_datetime(df["week_start"])

FEATURES = ["promo_flag", "price", "temp_c", "units_lag1", "units_next_wk"]
y = df["units_sold"]

scaler = StandardScaler()
X = scaler.fit_transform(df[FEATURES])
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=60, random_state=42)
model.fit(X_train, y_train)
print("MAE", round(mean_absolute_error(y_test, model.predict(X_test)), 4))
'''

CHURN_MODEL = '''import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

data = pd.read_csv("data/customers.csv")
target = "churned"
cols = ["tenure_m", "monthly_fee", "n_tickets"]

train, test = train_test_split(data, test_size=0.25, random_state=7, stratify=data[target])
clf = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=500))
clf.fit(train[cols], train[target])
print("accuracy", round(accuracy_score(test[target], clf.predict(test[cols])), 4))
'''


def retail(root: Path, rng: np.random.Generator) -> dict:
    stores, weeks = [f"S{i:02d}" for i in range(1, 9)], pd.date_range("2023-01-02", periods=104, freq="7D")
    rows = []
    for s_i, s in enumerate(stores):
        level = 40 + 10 * s_i
        prev = level
        for w in weeks:
            promo = int(rng.random() < 0.2)
            price = round(10 + rng.normal(0, 0.8) - 1.5 * promo, 2)
            temp = round(15 + 10 * np.sin(2 * np.pi * w.dayofyear / 365) + rng.normal(0, 2), 1)
            units = max(0, round(0.6 * prev + 0.4 * level + 12 * promo - 2 * (price - 10) + 0.3 * temp + rng.normal(0, 4)))
            rows.append({"store_code": s, "week_start": w.date().isoformat(), "promo_flag": promo,
                         "price": price, "temp_c": temp, "units_sold": units})
            prev = units
    df = pd.DataFrame(rows)
    g = df.groupby("store_code")["units_sold"]
    df["units_lag1"] = g.shift(1).fillna(g.transform("first"))            # legitimate past feature (DECOY)
    df["units_next_wk"] = g.shift(-1).fillna(df["units_sold"])            # FUTURE target as feature (DEFECT)
    (root / "data").mkdir(parents=True, exist_ok=True)
    df.to_csv(root / "data" / "store_week.csv", index=False)
    (root / "train.py").write_text(RETAIL_TRAIN, encoding="utf-8")
    (root / "README.md").write_text("# Weekly store demand\nModel quality: see train.py output.\n", encoding="utf-8")
    return {"defects": ["future-target feature units_next_wk (target_proxy, future lag 1)",
                        "scaler fitted before split (train.py:14)",
                        "random split on weekly time series (train.py:15) -> temporal_overlap"],
            "decoys": ["units_lag1 correlates strongly with target but is a legitimate PAST value"]}


def churn(root: Path, rng: np.random.Generator) -> dict:
    n = 1200
    tenure = rng.integers(1, 72, n)
    fee = np.round(rng.normal(55, 15, n), 2)
    tickets = rng.poisson(1 + 3 * (rng.random(n) < 0.3), n)
    logit = -1.2 - 0.04 * tenure + 0.02 * (fee - 55) + 0.45 * tickets
    churned = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    signup = pd.Timestamp("2021-01-01") + pd.to_timedelta(rng.integers(0, 900, n), unit="D")
    df = pd.DataFrame({"customer_ref": [f"C{i:05d}" for i in range(n)], "signup_dt": signup.date.astype(str),
                       "plan": rng.choice(["basic", "plus", "pro"], n), "tenure_m": tenure,
                       "monthly_fee": fee, "n_tickets": tickets, "churned": churned})
    df.loc[rng.random(n) < 0.05, "monthly_fee"] = np.nan                   # 5% genuinely missing
    (root / "data").mkdir(parents=True, exist_ok=True)
    df.to_csv(root / "data" / "customers.csv", index=False)
    (root / "model.py").write_text(CHURN_MODEL, encoding="utf-8")
    return {"defects": [],
            "decoys": ["n_tickets is strongly (legitimately) related to churn",
                       "customer_ref is an id-like column that is NOT used as a feature",
                       "monthly_fee has 5% missing values, handled by an imputer fitted on train only"]}

OTC_FORECAST = '''import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

# Monthly demand forecast per product x wholesaler (used for next-month replenishment plan)
df = pd.read_csv("data/channel_monthly.csv")

FEATURE_COLS = ["promo_flag", "price_index", "sell_out_lag1", "sell_out_units", "month_of_year"]
df["month_of_year"] = df["period"] % 100
target = "sell_in_units"   # demand

X_train, X_test, y_train, y_test = train_test_split(df[FEATURE_COLS], df[target], test_size=0.2, random_state=11)
model = GradientBoostingRegressor(random_state=11).fit(X_train, y_train)
pred = model.predict(X_test)
wape = (abs(pred - y_test)).sum() / abs(y_test).sum()
print("WAPE", round(wape, 4))
'''


def otc_channel(root: Path, rng: np.random.Generator) -> dict:
    """Generic OTC channel panel: manufacturer -> wholesaler -> pharmacy. Fully synthetic."""
    products = [f"P{i:03d}" for i in range(1, 13)]
    wholesalers = ["W1", "W2", "W3", "W4"]
    periods = [y * 100 + m for y in (2023, 2024, 2025) for m in range(1, 13)]
    rows = []
    for pi, p in enumerate(products):
        base = 200 + 60 * pi
        winter = pi % 3 == 0                      # some products peak in cold season
        for w_i, w in enumerate(wholesalers):
            share = (0.4, 0.3, 0.2, 0.1)[w_i]
            prev_so = None
            for t, per in enumerate(periods):
                m = per % 100
                season = 1 + (0.6 if winter and m in (11, 12, 1, 2) else 0.0)
                promo = int(rng.random() < 0.15)
                price = round(1.0 + 0.08 * (t // 12) + rng.normal(0, 0.01), 3)
                demand = base * share * season * (1 + 0.35 * promo) * (1.1 - 0.5 * (price - 1)) * rng.lognormal(0, 0.12)
                oos = int(rng.random() < 0.06)
                sell_out = demand * (rng.uniform(0.3, 0.6) if oos else 1.0)      # censored when out of stock
                loading = 1.4 if m == 1 else (0.75 if m == 2 else 1.0)          # pre-price-increase loading
                sell_in = sell_out * loading * rng.lognormal(0, 0.08)
                rows.append({"period": per, "product_code": p, "wholesaler": w, "promo_flag": promo,
                             "price_index": price, "oos_flag": oos, "sell_in_units": round(sell_in),
                             "sell_out_units": round(sell_out),
                             "sell_out_lag1": round(prev_so if prev_so is not None else sell_out)})
                prev_so = sell_out
    df = pd.DataFrame(rows)
    (root / "data").mkdir(parents=True, exist_ok=True)
    df.to_csv(root / "data" / "channel_monthly.csv", index=False)
    (root / "forecast.py").write_text(OTC_FORECAST, encoding="utf-8")
    (root / "README.md").write_text("# Channel demand forecast\nMonthly forecast per product and wholesaler.\n",
                                    encoding="utf-8")
    return {"defects": ["O1 proxy target: sell_in_units modelled as 'demand' (forecast.py:10)",
                        "O4 same-month sell_out_units used as a feature (not known when forecasting next month)",
                        "O2 sell_out censored in oos_flag months; oos_flag ignored",
                        "A3 random split on a monthly panel (forecast.py:12) -> temporal_overlap"],
            "decoys": ["sell_out_lag1 correlates strongly with sell_out_units but is a legitimate past value",
                       "January sell-in spikes are channel loading (O3), not a data error"]}


def main(out: str) -> None:
    out_dir = Path(out)
    rng = np.random.default_rng(20261109)
    key = {"retail_weekly": retail(out_dir / "retail_weekly", rng),
           "churn_tabular": churn(out_dir / "churn_tabular", rng),
           "otc_channel": otc_channel(out_dir / "otc_channel", np.random.default_rng(20261110))}
    (out_dir / "_answer_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(json.dumps({"written": [str(out_dir / k) for k in key]}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "examples/projects")

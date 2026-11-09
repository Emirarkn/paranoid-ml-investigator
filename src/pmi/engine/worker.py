"""Experiment worker — executed as a SEPARATE PROCESS:

    python -m pmi.engine.worker <job.json> <out.json>

Project code (via the adapter) only ever runs here: network guard, timeout (parent), and
a working directory inside the run workspace. Everything measured is written to artifacts.
"""
from __future__ import annotations

import json
import math
import os
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _sha(path: Path) -> str:
    from pmi.core.config import file_sha256
    return file_sha256(path)


def _finite(x: float) -> float | None:
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else float(x)


class Job:
    def __init__(self, job: dict[str, Any]):
        self.job = job
        self.spec = job.get("spec", {})
        self.profile = job.get("profile", {})
        self.amp = job.get("amp", {})
        self.art = Path(job["artifacts_dir"])
        self.art.mkdir(parents=True, exist_ok=True)
        self.artifacts: list[dict[str, str]] = []
        self._adapter = None

    # ---- helpers -----------------------------------------------------------
    @property
    def adapter(self):
        if self._adapter is None:
            from pmi.engine.adapter import get_adapter
            self._adapter = get_adapter(self.job)
        return self._adapter

    def save(self, name: str, df: pd.DataFrame | None = None, obj: Any = None) -> Path:
        p = self.art / name
        if df is not None:
            df.to_csv(p, index=False, compression="gzip" if name.endswith(".gz") else None)
        else:
            p.write_text(json.dumps(obj, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
        self.artifacts.append({"path": p.name, "sha256": _sha(p)})
        return p

    def metric_names(self) -> list[str]:
        from pmi.engine import metrics as M
        names = list(self.spec.get("metrics") or [])
        pm = self.profile.get("primary_metric")
        if pm:
            names.insert(0, M.canonical_name(pm))
        if not names:
            names = M.available(self.profile.get("task_type"))[:4]
        seen, out = set(), []
        for n in names:
            c = M.canonical_name(n)
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def data_and_split(self, need_split: bool):
        if self.job.get("adapter"):
            from pmi.engine.adapter import split_indices
            df = self.adapter.load_data()
            if need_split:
                tr, te = split_indices(self.adapter, df)
                return df, tr, te
            return df, None, None
        if need_split:
            raise RuntimeError("This experiment needs the project's split: register an adapter first "
                               "(pmi adapter validate).")
        src = self.profile.get("data_source")
        if not src:
            raise RuntimeError("No adapter and no confirmed data_source in the profile.")
        from pmi.profiling.loaders import load_table
        return load_table(Path(self.job["workspace"]) / "target" / src), None, None

    # ---- job types ---------------------------------------------------------
    def validate(self) -> dict[str, Any]:
        from pmi.engine.adapter import validate
        return validate(self.adapter)

    def check(self) -> dict[str, Any]:
        from pmi.auditors.checks import CHECKS
        chk = CHECKS[self.spec["check"]]
        ctx: dict[str, Any] = {"profile": self.profile, "workspace": self.job["workspace"]}
        if chk.needs_data or chk.needs_split:
            df, tr, te = self.data_and_split(chk.needs_split)
            ctx.update(df=df, train_idx=tr, test_idx=te)
            ctx["data_via"] = "adapter" if self.job.get("adapter") else "profile.data_source"
        res = chk.fn(ctx, self.spec.get("params", {}))
        res["data_via"] = ctx.get("data_via", "code")
        self.save("check_result.json", obj=res)
        return res

    def _fit_predict(self, train_df, test_df, seed):
        from pmi.engine.adapter import predict
        model = self.adapter.fit(train_df, seed=seed)
        return model, *predict(self.adapter, model, test_df)

    def _metrics(self, y, p, proba) -> dict[str, float | None]:
        from pmi.engine import metrics as M
        return {k: _finite(v) for k, v in M.compute(self.metric_names(), y, p, proba).items()}

    def baseline(self) -> dict[str, Any]:
        from pmi.engine import metrics as M
        df, tr, te = self.data_and_split(True)
        y = df.loc[te, self.adapter.target]
        seeds = list(self.job["seeds"])
        rows, per_seed = [], []
        for s in seeds:
            _, p, proba = self._fit_predict(df.loc[tr], df.loc[te], s)
            per_seed.append({"seed": s, "metrics": self._metrics(y, p, proba)})
            rows.append(pd.DataFrame({"level": "baseline", "seed": s, "row": list(map(str, te)),
                                      "y_true": y.to_numpy(), "y_pred": p,
                                      "proba": proba if proba is not None else np.nan}))
        self.save("predictions.csv.gz", df=pd.concat(rows, ignore_index=True))
        names = self.metric_names()
        summary = {n: {"mean": _finite(float(np.nanmean([r["metrics"].get(n, np.nan) for r in per_seed]))),
                       "min": _finite(float(np.nanmin([r["metrics"].get(n, np.nan) for r in per_seed]))),
                       "max": _finite(float(np.nanmax([r["metrics"].get(n, np.nan) for r in per_seed])))}
                   for n in names if any(n in r["metrics"] for r in per_seed)}
        res: dict[str, Any] = {"n_train": len(tr), "n_test": len(te), "metrics": summary, "per_seed": per_seed}
        rep = self.profile.get("reported_metric")
        if isinstance(rep, dict) and rep.get("metric") is not None and rep.get("value") is not None:
            m = M.canonical_name(rep["metric"])
            # the project's own configuration corresponds to the FIRST seed (adapter: seed=0 -> project seed)
            got = per_seed[0]["metrics"].get(m)
            if got is None:
                res["reproduction"] = {"metric": m, "error": "metric not computed (check metric name / proba)"}
            else:
                gap = abs(got - float(rep["value"])) / max(abs(float(rep["value"])), 1e-12)
                res["reproduction"] = {"metric": m, "reported": float(rep["value"]), "reproduced": got,
                                       "reproduced_seed": per_seed[0]["seed"], "relative_gap": round(gap, 6),
                                       "seed_spread": summary.get(m)}
        else:
            res["reproduction"] = {"error": "profile.reported_metric not confirmed; nothing to compare"}
        self.save("baseline.json", obj=res)
        return res

    def amplify(self) -> dict[str, Any]:
        from pmi.engine import metrics as M
        from pmi.engine.injectors import INJECTORS, build_levels
        inj = INJECTORS[self.spec["injector"]]
        where = self.spec.get("where", "test")
        df, tr, te = self.data_and_split(True)
        target = self.adapter.target
        cols = list(self.spec["columns"])
        if target in cols:
            raise RuntimeError("The target column cannot be an injection column (label noise is a separate family).")
        missing_cols = [c for c in cols if c not in df.columns]
        if missing_cols:
            raise RuntimeError(f"Columns not in data: {missing_cols}")
        if inj.numeric_only:
            bad = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]
            if bad:
                raise RuntimeError(f"Injector '{inj.name}' needs numeric columns; not numeric: {bad}")
        rows_for = {"test": te, "train": tr, "both": tr.append(te)}[where]
        ctx = {"profile": self.profile, "amp": self.amp, "train_rows": tr, "params": self.spec.get("params", {})}
        base = inj.base_condition(df, rows_for, cols, ctx)
        levels, ladder_note = build_levels(inj, base, self.amp, self.spec.get("levels"))
        names = self.metric_names()
        seeds = list(self.job["seeds"])
        y = df.loc[te, target]

        records, preds = [], []
        base_models = {}
        for li, lv in enumerate(levels):
            for s in seeds:
                rng = np.random.default_rng([int(s), li, 7919])
                rec: dict[str, Any] = {"level": lv["label"], "seed": s, "condition_target": lv["condition"]}
                try:
                    d = df
                    if lv["inject"]:
                        d = inj.apply(df, rows_for, cols, lv["condition"], rng, ctx)
                    rec["condition_realized"] = _finite(inj.base_condition(d, rows_for, cols, ctx))
                    if where == "test" and s in base_models:
                        from pmi.engine.adapter import predict
                        p, proba = predict(self.adapter, base_models[s], d.loc[te])
                    else:
                        model, p, proba = self._fit_predict(d.loc[tr], d.loc[te], s)
                        if not lv["inject"]:
                            base_models[s] = model
                    rec["metrics"] = self._metrics(y, p, proba)
                    preds.append(pd.DataFrame({"level": lv["label"], "seed": s, "row": list(map(str, te)),
                                               "y_true": y.to_numpy(), "y_pred": p,
                                               "proba": proba if proba is not None else np.nan}))
                except Exception as exc:  # a crash under stress IS an observation
                    rec["failure"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                records.append(rec)

        base_by_seed = {r["seed"]: r for r in records if r["level"] == "1x" and "metrics" in r}
        for r in records:
            b = base_by_seed.get(r["seed"])
            r["eaf"] = {}
            for n in names:
                if "metrics" in r and b and n in r["metrics"]:
                    lb, lx = M.as_loss(n, b["metrics"][n]), M.as_loss(n, r["metrics"][n])
                    r["eaf"][n] = _finite(lx / lb) if lb not in (0, None) and lb == lb else None
        table = []
        for lv in levels:
            rs = [r for r in records if r["level"] == lv["label"]]
            row = dict(lv, failures=sum("failure" in r for r in rs), replicates=len(rs))
            for n in names:
                vals = [r["metrics"][n] for r in rs if "metrics" in r and r["metrics"].get(n) is not None]
                eafs = [r["eaf"][n] for r in rs if r.get("eaf", {}).get(n) is not None]
                row[n] = {"mean": _finite(float(np.mean(vals))) if vals else None,
                          "min": _finite(float(np.min(vals))) if vals else None,
                          "max": _finite(float(np.max(vals))) if vals else None}
                row[f"eaf_{n}"] = {"mean": _finite(float(np.mean(eafs))) if eafs else None,
                                   "min": _finite(float(np.min(eafs))) if eafs else None,
                                   "max": _finite(float(np.max(eafs))) if eafs else None}
            row["condition_realized_mean"] = _finite(float(np.mean(
                [r["condition_realized"] for r in rs if r.get("condition_realized") is not None]))) \
                if any(r.get("condition_realized") is not None for r in rs) else None
            table.append(row)

        prim = names[0]
        base_losses = [M.as_loss(prim, r["metrics"][prim]) for r in base_by_seed.values() if prim in r["metrics"]]
        noise = float(np.std(base_losses) / np.mean(base_losses)) if len(base_losses) > 1 and np.mean(base_losses) else 0.0
        threshold = self._threshold(table)
        res = {"injector": inj.name, "where": where, "columns": cols, "base_condition": base,
               "ladder": ladder_note, "metrics": names, "primary_metric": prim, "levels": table,
               "baseline_noise_rel_std": round(noise, 6), "threshold": threshold,
               "n_test": len(te), "n_train": len(tr)}
        self.save("records.json", obj=records)
        if preds:
            self.save("predictions.csv.gz", df=pd.concat(preds, ignore_index=True))
        self.save("amplification.json", obj=res)
        return res

    def _threshold(self, table: list[dict]) -> dict[str, Any]:
        thr = self.profile.get("acceptable_threshold")
        if not isinstance(thr, dict) or "metric" not in thr:
            return {"status": "not_set", "note": "profile.acceptable_threshold not confirmed; curve only"}
        from pmi.engine.metrics import canonical_name
        m = canonical_name(thr["metric"])
        for row in table:
            v = (row.get(m) or {}).get("mean")
            crossed = (row["failures"] > 0) or (v is not None and (
                ("max" in thr and v > float(thr["max"])) or ("min" in thr and v < float(thr["min"]))))
            if crossed:
                return {"status": "crossed", "metric": m, "first_level": row["label"],
                        "condition": row["condition"], "value": v, "rule": thr}
        return {"status": "not_crossed", "metric": m, "rule": thr}

    def ablation(self) -> dict[str, Any]:
        from pmi.engine import metrics as M
        from pmi.engine.injectors import neutralize
        where = self.spec.get("where", "test")
        mode = self.spec.get("mode", "individual")
        df, tr, te = self.data_and_split(True)
        target = self.adapter.target
        feats = list(self.spec["features"])
        if target in feats:
            raise RuntimeError("Target cannot be ablated.")
        names, seeds = self.metric_names(), list(self.job["seeds"])
        y = df.loc[te, target]
        steps = [("none", [])] + ([(f, [f]) for f in feats] if mode == "individual"
                                  else [(f"+{f}", feats[:i + 1]) for i, f in enumerate(feats)])
        records, preds, base_models = [], [], {}
        for label, removed in steps:
            for s in seeds:
                rec: dict[str, Any] = {"step": label, "removed": removed, "seed": s}
                try:
                    d = df
                    rows = te if where == "test" else tr.append(te)
                    for f in removed:
                        d = neutralize(d, rows, f, tr)
                    if where == "test" and s in base_models:
                        from pmi.engine.adapter import predict
                        p, proba = predict(self.adapter, base_models[s], d.loc[te])
                    else:
                        model, p, proba = self._fit_predict(d.loc[tr], d.loc[te], s)
                        if not removed:
                            base_models[s] = model
                    rec["metrics"] = self._metrics(y, p, proba)
                    preds.append(pd.DataFrame({"level": label, "seed": s, "row": list(map(str, te)),
                                               "y_true": y.to_numpy(), "y_pred": p,
                                               "proba": proba if proba is not None else np.nan}))
                except Exception as exc:
                    rec["failure"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                records.append(rec)
        base = {r["seed"]: r for r in records if r["step"] == "none" and "metrics" in r}
        table = []
        for label, removed in steps:
            rs = [r for r in records if r["step"] == label]
            row: dict[str, Any] = {"step": label, "removed": removed, "failures": sum("failure" in r for r in rs)}
            for n in names:
                eafs = []
                for r in rs:
                    b = base.get(r["seed"])
                    if "metrics" in r and b and n in r["metrics"]:
                        lb = M.as_loss(n, b["metrics"][n])
                        if lb:
                            eafs.append(M.as_loss(n, r["metrics"][n]) / lb)
                vals = [r["metrics"][n] for r in rs if "metrics" in r and r["metrics"].get(n) is not None]
                row[n] = {"mean": _finite(float(np.mean(vals))) if vals else None}
                row[f"eaf_{n}"] = {"mean": _finite(float(np.mean(eafs))) if eafs else None,
                                   "min": _finite(float(np.min(eafs))) if eafs else None,
                                   "max": _finite(float(np.max(eafs))) if eafs else None}
            table.append(row)
        res = {"where": where, "mode": mode, "features": feats, "metrics": names, "primary_metric": names[0],
               "steps": table, "n_test": len(te)}
        self.save("records.json", obj=records)
        if preds:
            self.save("predictions.csv.gz", df=pd.concat(preds, ignore_index=True))
        self.save("ablation.json", obj=res)
        return res


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    job_path, out_path = Path(argv[0]), Path(argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if job.get("network", "blocked") == "blocked":
        from pmi.engine import netguard
        netguard.install()
    os.chdir(job["workspace"])
    out: dict[str, Any]
    try:
        j = Job(job)
        result = getattr(j, job["type"])()
        out = {"ok": True, "result": result, "artifacts": j.artifacts}
    except Exception as exc:
        out = {"ok": False, "error": f"{type(exc).__name__}: {exc}",
               "traceback": traceback.format_exc()[-4000:]}
    out_path.write_text(json.dumps(out, default=str, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

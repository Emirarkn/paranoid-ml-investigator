"""Run directory = one investigation of one target project.

runs/<run_id>/
  manifest.json        immutable facts about the run (target, versions, policy hashes)
  snapshot.json        sha256 of every target file at init (integrity reference)
  ledger.sqlite        hypotheses / experiments / status events (written only by pmi)
  profile.json         learned project profile (fields have status + evidence)
  adapter.json         adapter registration (kind, sha256, fidelity)
  budget.json          human-approved budget extensions
  scan/                inventory, data scan, code scan outputs
  artifacts/E-xxx/     experiment evidence files (hashed into the ledger)
  workspace/target/    isolated COPY of the project (never edited)
  workspace/pmi_adapter.py   the only executable file the agent writes
  workspace/scratch/   agent scratch space
  notes/               agent narrative (must cite H-/E- ids; checked by pmi check-claims)
"""
from __future__ import annotations

import json
import platform
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

from pmi import __version__
from pmi.core.config import PMIError, file_sha256, load_policy, text_sha256
from pmi.core.snapshot import copy_to_workspace, diff_snapshot, take_snapshot


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pkg_versions() -> dict[str, str]:
    out = {}
    for name in ("numpy", "pandas", "sklearn", "yaml"):
        try:
            mod = __import__(name)
            out[name] = getattr(mod, "__version__", "?")
        except Exception:  # pragma: no cover
            out[name] = "missing"
    return out


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class Run:
    root: Path      # harness root
    dir: Path       # runs/<run_id>

    # ---- paths -------------------------------------------------------------
    @property
    def id(self) -> str:
        return self.dir.name

    @property
    def manifest_path(self) -> Path:
        return self.dir / "manifest.json"

    @property
    def snapshot_path(self) -> Path:
        return self.dir / "snapshot.json"

    @property
    def ledger_path(self) -> Path:
        return self.dir / "ledger.sqlite"

    @property
    def profile_path(self) -> Path:
        return self.dir / "profile.json"

    @property
    def adapter_meta_path(self) -> Path:
        return self.dir / "adapter.json"

    @property
    def workspace(self) -> Path:
        return self.dir / "workspace"

    @property
    def target_copy(self) -> Path:
        return self.workspace / "target"

    @property
    def adapter_path(self) -> Path:
        return self.workspace / "pmi_adapter.py"

    @property
    def artifacts(self) -> Path:
        return self.dir / "artifacts"

    @property
    def scan_dir(self) -> Path:
        return self.dir / "scan"

    @property
    def manifest(self) -> dict[str, Any]:
        return read_json(self.manifest_path, {})

    @property
    def target_path(self) -> Path:
        return Path(self.manifest["target_path"])

    @property
    def policy(self) -> dict[str, Any]:
        return load_policy(self.root)

    # ---- lifecycle ---------------------------------------------------------
    @classmethod
    def create(cls, root: Path, target: Path, name: str | None = None) -> "Run":
        target = target.expanduser().resolve()
        if not target.is_dir():
            raise PMIError(f"Target project folder not found: {target}")
        if root == target or root in target.parents or target in root.parents:
            raise PMIError("Target must not contain / be contained in the harness folder.")
        policy = load_policy(root)
        slug = re.sub(r"[^A-Za-z0-9_-]+", "-", name or target.name).strip("-")[:40] or "run"
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + slug
        rdir = root / "runs" / run_id
        if rdir.exists():
            raise PMIError(f"Run already exists: {rdir}")
        for sub in ("artifacts", "scan", "notes", "workspace/scratch"):
            (rdir / sub).mkdir(parents=True, exist_ok=True)
        run = cls(root, rdir)

        snap = take_snapshot(target, policy)
        write_json(run.snapshot_path, snap)
        copy_info = copy_to_workspace(target, run.target_copy, snap, policy)

        tmpl = resources.files("pmi").joinpath("templates/adapter_template.py").read_text(encoding="utf-8")
        run.adapter_path.write_text(tmpl, encoding="utf-8")

        manifest = {
            "run_id": run_id,
            "created_at": utcnow(),
            "target_path": str(target),
            "target_name": target.name,
            "target_files": len(snap),
            "snapshot_sha256": file_sha256(run.snapshot_path),
            "workspace_copy": copy_info,
            "pmi_version": __version__,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": _pkg_versions(),
            "policy_sha256": file_sha256(root / "config" / "policy.yaml"),
            "amplification_sha256": file_sha256(root / "config" / "amplification.yaml"),
        }
        write_json(run.manifest_path, manifest)
        write_json(run.dir / "budget.json", {"extra_experiments": 0, "extra_minutes": 0, "events": []})
        (root / "runs" / "CURRENT").write_text(run_id, encoding="utf-8")
        return run

    @classmethod
    def load(cls, root: Path, run_id: str | None = None) -> "Run":
        runs = root / "runs"
        if run_id is None:
            cur = runs / "CURRENT"
            if not cur.is_file():
                raise PMIError("No active run. Start one with: pmi init --target <project folder>")
            run_id = cur.read_text(encoding="utf-8").strip()
        rdir = runs / run_id
        if not (rdir / "manifest.json").is_file():
            raise PMIError(f"Run not found: {run_id}")
        return cls(root, rdir)

    # ---- integrity ---------------------------------------------------------
    def integrity(self) -> dict[str, Any]:
        """Re-hash the ORIGINAL project and the workspace copy and compare to the snapshot."""
        snap = read_json(self.snapshot_path, {})
        result: dict[str, Any] = {"snapshot_file_ok": file_sha256(self.snapshot_path) == self.manifest.get("snapshot_sha256")}
        if self.target_path.is_dir():
            result["target"] = diff_snapshot(snap, take_snapshot(self.target_path, self.policy))
        else:
            result["target"] = {"error": "original target folder not reachable"}
        copied = {k: v for k, v in snap.items() if (self.target_copy / k).is_file()}
        ws_now = {k: {"sha256": file_sha256(self.target_copy / k)} for k in copied}
        result["workspace_copy"] = diff_snapshot(copied, ws_now)
        t = result["target"]
        result["ok"] = bool(result["snapshot_file_ok"]) and "error" not in t and not any(t.values()) \
            and not any(result["workspace_copy"].values())
        return result

    # ---- budgets -----------------------------------------------------------
    def budget_state(self, n_experiments: int) -> dict[str, Any]:
        b = self.policy.get("budgets", {})
        ext = read_json(self.dir / "budget.json", {"extra_experiments": 0, "extra_minutes": 0})
        created = datetime.strptime(self.manifest["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        minutes = (datetime.now(timezone.utc) - created).total_seconds() / 60
        max_exp = int(b.get("max_experiments_per_run", 60)) + int(ext.get("extra_experiments", 0))
        max_min = float(b.get("max_wall_minutes_per_run", 480)) + float(ext.get("extra_minutes", 0))
        return {
            "experiments_used": n_experiments, "experiments_max": max_exp,
            "minutes_used": round(minutes, 1), "minutes_max": max_min,
            "exhausted": n_experiments >= max_exp or minutes >= max_min,
        }

    def extend_budget(self, experiments: int, minutes: float, reason: str) -> dict[str, Any]:
        path = self.dir / "budget.json"
        ext = read_json(path, {"extra_experiments": 0, "extra_minutes": 0, "events": []})
        ext["extra_experiments"] = int(ext.get("extra_experiments", 0)) + int(experiments)
        ext["extra_minutes"] = float(ext.get("extra_minutes", 0)) + float(minutes)
        ext.setdefault("events", []).append({"at": utcnow(), "experiments": experiments,
                                             "minutes": minutes, "reason": reason})
        write_json(path, ext)
        return ext

    # ---- adapter -----------------------------------------------------------
    @property
    def adapter_meta(self) -> dict[str, Any]:
        return read_json(self.adapter_meta_path, {})

    def adapter_hash(self) -> str | None:
        return file_sha256(self.adapter_path) if self.adapter_path.is_file() else None

    def adapter_fidelity(self) -> str:
        """confirmed | unconfirmed | mismatch | stale | none."""
        meta = self.adapter_meta
        if not meta:
            return "none"
        if meta.get("sha256") != self.adapter_hash() and meta.get("kind") == "target":
            return "stale"
        return meta.get("fidelity", "unconfirmed")


def copy_template(dest: Path) -> None:
    tmpl = resources.files("pmi").joinpath("templates/adapter_template.py").read_text(encoding="utf-8")
    dest.write_text(tmpl, encoding="utf-8")


def safe_rmtree_inside(path: Path, root: Path) -> None:  # pragma: no cover - utility
    if root.resolve() in path.resolve().parents:
        shutil.rmtree(path)

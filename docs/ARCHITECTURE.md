# Architecture: design document ↔ implementation

Source design: `docs/system_design_v1.md`. This file shows where each component lives and which stage it is in.

```
                ┌──────────────── Layer A — Intelligence (Claude Code) ──────────────────┐
  user ───────► │ CLAUDE.md (character + rules)   skills/ (methods)   agents/ (roles)    │
                │ project-cartographer · hypothesis-skeptic · experiment-designer        │
                │ evidence-verifier · claim-auditor                                       │
                └───────────────┬────────────────────────────────────────────────────────┘
                                │ only via the `pmi` CLI (permissions + guard hook)
                ┌───────────────▼──────── Layer B — Experimental Harness (Python) ───────┐
                │ core/ run, snapshot, policy   profiling/ inventory, data/code scan,    │
                │ auditors/checks   engine/ adapter, injectors, worker(subprocess),      │
                │ metrics(primary+independent)  evidence/ ledger(hash chain), verify     │
                └───────────────┬────────────────────────────────────────────────────────┘
                ┌───────────────▼──────── Layer C — Decision & Reporting ────────────────┐
                │ reporting/report (ledger-only)  reporting/claims (hallucination audit) │
                └─────────────────────────────────────────────────────────────────────────┘
```

| Design component | Implementation | Status |
|---|---|---|
| Project Understanding Module | `profiling/*`, `pmi scan`, `profile.json`, subagent `project-cartographer` | ✅ v0.1 |
| Skeptical Hypothesis Engine | skill `skeptical-hypotheses`, subagent `hypothesis-skeptic`, `pmi hypothesis` | ✅ v0.1 |
| Experimental Planner | skill `experiment-design`, subagent `experiment-designer`, pre-registration | ✅ v0.1 |
| Structural Auditor | `auditors/checks.py` (7 checks), `profiling/code_scan.py` (AST) | ✅ v0.1 |
| Fault Injection Engine | `engine/injectors.py` (missing, outliers, shift, time_lag, neutralize) | ✅ v0.1 |
| Failure Amplification Engine | `worker.amplify`, `build_levels`, EAF, threshold discovery | ✅ v0.1 |
| Backtesting Engine | single split (adapter); no multi-fold rolling-origin yet | ⏳ Stage 5 |
| Consequence Simulation Engine | — | ⏳ Stage 5 |
| Evidence Verification Engine | `evidence/verify.py` (hashes, replication, independent recompute, caps) | ✅ v0.1 |
| Root Cause Analyzer | hypothesis `mechanism` + evidence-verifier | 🟡 partial |
| Solution Planner | `hypothesis --fix` (untested proposal) | 🟡 partial |
| Counterfactual Tester | — | ⏳ Stage 6 |
| Report Generator | `reporting/report.py` + `audit-reporting` skill | ✅ v0.1 |
| Agent hallucination tests | `pmi check-claims`, subagent `claim-auditor`, guard hook | 🟡 basic (red-team benchmark in Stage 7) |

## Key design decisions
1. **Domain-agnostic profile.** The schema contains no domain vocabulary (enforced by a test). Time axis, unit and target are learned from the project and finalised by human confirmation. Analyses that need an unconfirmed field are blocked.
2. **Adapter fidelity gate.** All model-based evidence depends on the adapter really mirroring the project. This is proven either by reproducing the reported metric (`pmi baseline`) or by human declaration. Otherwise the result is at most Inconclusive.
3. **Pre-registration.** Spec and decision rule are hashed before the experiment runs. An experiment runs only once.
4. **Two metric implementations.** Experiments measure with numpy; verify recomputes with sklearn/pandas.
5. **Tamper-evident ledger.** Every event contains the hash of the previous event.
6. **The condition is amplified, not the error.** Relative and absolute ladders are labelled differently, physical limits are flagged, and the realised condition is measured separately.

## Run folder
See the docstring of `src/pmi/core/run.py`.

# Roadmap status

| Stage | Scope | Status | How the acceptance criterion is tested |
|---|---|---|---|
| 1 Foundation | run, snapshot, workspace copy, integrity, CLI, policy | ✅ | `tests/test_foundation.py`: target hashes unchanged, modifications detected, secret files not copied |
| 2 Structural Intelligence | inventory, data scan, AST code scan, profile (candidate → confirmed) | ✅ | `tests/test_profiling.py`: correct target, time, grain, entity and task candidates across projects with different vocabularies; no domain words in the schema |
| 3 Hypothesis & Evidence | ledger, pre-registration, verify, caps, hash chain | ✅ | `tests/test_evidence.py`: Suspected/Verified/Rejected never mix, tampering detected, fidelity gate works |
| 4 Amplification MVP | missing, outliers/shift, time_lag, ablation; EAF; threshold | ✅ (MVP) | `tests/test_amplification.py`: relative/absolute ladders, limit flag, identical numbers for identical seeds, independent recompute |
| OTC pack | channel skill, failure catalog, synthetic benchmark | ✅ v0.1 (knowledge layer) | `tests/test_profiling.py` (OTC tests) |
| 5 Consequence | rolling-origin backtest, segment metrics, business simulation (scenarios A/B/C, Monte Carlo) | ⏳ | — |
| 6 Repair & Retest | fixes in isolated copies `workspace/repairs/<fix>`, counterfactual comparison, side-effect scan | ⏳ | — |
| 7 Agent Red Team | benchmark with misleading docs, fake metrics, broken references; hardened claim checker | 🟡 basic `check-claims` exists | — |
| 8 Hardening | large files, recovery from interrupted runs, performance, HTML report | ⏳ | — |

## Remaining extensions from stage 4
- Stockout / censored target injector. Needs a "constraint indicator" field in the profile, defined in a domain-agnostic way.
- Leakage-scope amplification: varying the share of leaked information
- Subgroup representation (bias) injector
- Compound scenarios: two injectors applied together
- Day-first / decimal-comma parsing for localised CSV and Excel files

## Benchmark (section 11)
`examples/make_examples.py` generates three synthetic projects with real defects and decoys; the answer key is hidden. The goal is 20 scenarios. MVP thresholds will be set after the first benchmark results.

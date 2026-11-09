---
name: evidence-protocol
description: PMI evidence statuses (Verified, Simulated, Suspected, Inconclusive, Rejected), pmi verify's status rules, status caps, evidence integrity, and which wording may be used about findings. Use in the Verify phase and before describing any finding to the user.
---

# Evidence protocol

## Who decides the status?
Only `pmi verify H-xxx`. Writing to the ledger directly is blocked. Even if it were written, the hash chain catches it (`pmi integrity`).

## What pmi verify does
For every completed experiment of the hypothesis:
1. Do the artifact files match their recorded sha256? If not → inconclusive.
2. The pre-registered rule is evaluated on the recorded result → pass / fail / inconclusive.
3. **Replication:** checks are re-executed in a fresh worker and must give exactly the same result. For model experiments every metric is recomputed from the saved predictions with an **independent implementation** (sklearn/pandas).
4. A **cap** is applied:
   - check via data/code → Verified
   - check via adapter → Verified if fidelity is `confirmed`, otherwise Inconclusive
   - amplify / ablation / `kind=sensitivity` → Simulated
   - surrogate → Simulated
   - baseline gap → Inconclusive without a human-confirmed adapter
5. Combination: pass and fail together → Inconclusive (conflict). Only pass → the highest cap. Only fail → Rejected.

## Mandatory fields of a finding record
Finding ID, problem description, source file/line, affected data, hypothesis/mechanism, test procedure (spec + rule), baseline measurement, experiment measurement, evidence file, uncertainty and proposed fix. `pmi report` generates all of these from the ledger. A missing field appears as "—" in the report, so fill the fields when registering the hypothesis.

## Wording rules
| You may write | You may not write |
|---|---|
| "H-002 verified (E-002): `units_next_wk` exactly equals the target's value one period later." | "The model is definitely leaky and its real performance is very low." (not measured) |
| "In a controlled experiment (E-006, Simulated), MAE EAF=1.43 when promo information is delayed by 2 periods." | "If promo is delayed in production, error rises 43%." |
| "H-004 tested, not supported (Rejected, E-004)." | Dropping H-004 from the report |
| "Inconclusive: adapter fidelity unconfirmed." | "Probably true." |

## Correlation ≠ causation
"Error rises as X rises" can be written as "amplifying X increased the error" only if it rests on an **interventional** experiment such as amplify or ablation. An observational relationship is never presented as a cause.

## Integrity
Run `pmi integrity` before every report. If `ok:false`, do not publish; tell the human.

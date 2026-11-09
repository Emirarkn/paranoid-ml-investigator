---
name: investigate
description: PMI master playbook. Defines the phases, gates, budget management and stop conditions for auditing an ML/AI project end to end. Load first for requests like "audit this project", "find the bugs", "run stress tests".
---

# Investigate — end-to-end audit

## Pre-flight
1. `pmi status`. If a run is active, continue where it left off.
2. If there is no run, ask the user for the target folder and run `pmi init --target "<folder>"`. This is a human gate.
3. Turn the user's request into **research questions** and write them to `runs/<id>/notes/plan.md`. For example, "find the bugs, run 2× and 3× stress tests" becomes: (a) is the evaluation valid? (b) which conditions make performance unacceptable when grown 2×/3×?

## Phase flow and exit criteria

| Phase | Exit criterion (before moving to the next phase) |
|---|---|
| Discover | `target`, `task_type`, `data_source` confirmed. For time series, `time_column` and `entity_keys` are confirmed too. Unconfirmed fields and the reasons are listed. |
| Connect | `pmi adapter validate` succeeded. `pmi baseline` ran. Fidelity became `confirmed` or human confirmation was obtained; otherwise the reason is reported. |
| Challenge | 4–8 prioritised hypotheses registered, each with a falsification test. At least one is a decoy check. |
| Experiment | At least one pre-registered experiment ran for each P1–P2 hypothesis. |
| Amplify | Severity ladders ran for verified defects and critical inputs. The threshold was found where possible. |
| Verify | `pmi verify` ran for every hypothesis with an experiment. P1–P2 Verified/Simulated findings went through `evidence-verifier` review. |
| Report | `pmi report` generated. `notes/findings.md` written and `pmi check-claims` is clean. |

## Priority rule
Audit the evaluation itself first (leakage, split, baseline reproduction), robustness (amplification) second. A stress test on top of an invalid evaluation means nothing. The report is written in this order.

## Budget
- Run `pmi budget show` every 10 experiments.
- When the budget is exhausted, stop. Tell the human what you learned, what remains open and how many more experiments are needed.

## Stop conditions
- `pmi integrity` or the hash chain is broken → stop and tell the human.
- The adapter cannot mirror the project (validate fails, fidelity mismatch) → stop model-based experiments. Continue only with static and data checks, and report this explicitly.
- The user's question is answered and the expected value of the remaining hypotheses is low → finish.

## Continuity across sessions
At the end of each phase, append a short dated note to `runs/<id>/notes/progress.md`: what was done, what's next, which human decision is pending. In a new session, read this file first.

## Closing message (to the user)
1. Is the evaluation valid? (Verified defects)
2. The 3 most critical findings, with statuses
3. Robustness profile: which condition, at which level, which EAF (Simulated)
4. Untested proposals and next steps
5. Path to `runs/<id>/report.md`

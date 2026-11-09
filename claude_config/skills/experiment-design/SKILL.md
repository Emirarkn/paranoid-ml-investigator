---
name: experiment-design
description: Turn a hypothesis into a pre-registered pmi experiment. Experiment type choice, spec writing, decision rule and threshold rationale, replicates, choice of where, and a realism note. Use before pmi experiment plan.
---

# Experiment design

## Principle: rule first, data second
The decision rule is recorded and hashed **before** the experiment. Changing the threshold after looking at the result is p-hacking. If a new threshold is needed, plan a new experiment; both stay in the report. `pmi verify` evaluates all experiments of a hypothesis. Conflicting evidence yields Inconclusive.

## Choosing the type
| Question | Type | Rule | Status cap |
|---|---|---|---|
| Is the defect in the project right now? | `check` | `defect_found` | Verified (via data/code, or through a fidelity-confirmed adapter) |
| Does the reported performance hold? | `baseline` (`pmi baseline`) | `baseline_gap` | Verified only with a human-confirmed adapter |
| What happens as the condition grows? | `amplify` | `eaf` | Simulated |
| Which input does the model depend on? | `ablation` | `eaf` | Simulated |

Full schemas and examples: `references/spec-and-rules.md`

## Choosing the threshold
1. If the human gave a threshold (`acceptable_threshold`), use it and cite it.
2. If not, use a conventional threshold and say so explicitly. For example: "EAF ≥ 1.2 (20% error increase), conventional because no business threshold was given."
3. The noise floor is applied automatically: the minimum EAF must be ≥ 1 + 2 × (seed noise).

## Choosing `where`
- `test`: the model is trained; inputs arriving in production are corrupted. The most common choice.
- `train`: training data is corrupted, test is clean. Measures the effect of data quality on learning.
- `both`: a persistent data-quality problem. The model is retrained.

## Realism note (mandatory)
For every amplify plan, write: is the 5× level possible in the real world? Which event would cause it? Is a `limit_exceeded` expected? This note goes under `notes/`.

## Flow
```
pmi experiment plan --hypothesis H-003 --type amplify \
  --spec '{"injector":"missing","columns":["x1"],"where":"test","replicates":3}' \
  --rule '{"type":"eaf","metric":"mae","level":"3x","min_eaf":1.2}'
pmi experiment run E-007
pmi verify H-003
```
A failed experiment (`state=failed`) is evidence too. Read the error message. Does it come from the adapter, or from the model crashing under the condition? Model crashes are also counted as `failures` inside amplify, and they are a finding.

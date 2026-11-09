---
name: skeptical-hypotheses
description: Systematically generate alternative explanations for a model's reported success, giving each a falsification test, a kind (defect/sensitivity) and a priority. Use in the Challenge phase, before pmi hypothesis add.
---

# Skeptical hypotheses

## The core move
Treat "the model works well" as an **observation** and list every mechanism that could produce it. Real learning is only one of them. The others are leakage, an easy test set, the wrong metric, a censored target, and so on.

Families and the typical test for each: `references/failure-catalog.md`

## Hypothesis quality checklist
- [ ] **Testable:** it is clear which `pmi` experiment will test it.
- [ ] **Falsifiable:** `--falsification` states which result kills the hypothesis.
- [ ] **Mechanistic:** the "why" is explained through a code or data path.
- [ ] **Sourced:** `--refs` has file:line (the location of the static suspicion, if it came from one).
- [ ] **Right kind:** `defect` = "this defect is in the project right now" (can be Verified). `sensitivity` = "the model breaks if the condition grows" (at most Simulated).
- [ ] **In the project's language:** no invented concepts.

## Prioritisation (1 = highest)
`priority ≈ impact × likelihood × testability`
- **Impact:** does it invalidate the evaluation (P1)? Change a business decision (P2)? Cosmetic (P4–5)?
- **Likelihood:** is there a static signal, a data observation or a structural reason?
- **Testability:** can it be tested now with the existing checks/injectors?

## Decoys (false-positive control)
In every round, register at least one "looks suspicious but is probably legitimate" case. These should come out Rejected. If they don't, either your judgement or the test is wrong. Two examples:
- High correlation between a lag feature derived from past values and the target
- An ID-like column that does not enter the model

## Registration
```
pmi hypothesis add --title "..." --statement "..." --mechanism "..." --expected "..." \
  --falsification "..." --kind defect|sensitivity --priority N --refs file.py:12 --affected "..."
```
If you have a fix idea, add it with `--fix`. It is a **proposal** and appears in the report labelled "untested".

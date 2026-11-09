---
name: project-profiling
description: Learn a project without domain assumptions, fill the profile fields (target, time axis, unit, evaluation protocol, metric, business context) with evidence and have a human confirm them; then write a pmi_adapter.py that mirrors the project. Use in the Discover and Connect phases.
---

# Project profiling + adapter

## Why it matters
PMI brings no ready-made concepts to any project. "Weekly", "store", "customer" — everything is learned **from this project**. `pmi` blocks analyses that need an unconfirmed profile field. That block is not a bug; it is the design.

## Steps
1. Run `pmi scan`. It produces an inventory, a table scan and an AST code scan, and fills candidate values with evidence.
2. Run the `project-cartographer` subagent to understand the project in depth.
3. Cross-check the candidates against code and data:
   - The scan says "temporal" but the code never uses the date → write this contradiction as a question.
   - Several target candidates → which one feeds the reported metric?
   - Grain is "irregular" → events, or missing periods? Look at the data.
4. Present the **confirmation package** to the human in a single message. For each field give the value, the evidence, and "if you confirm this, these analyses unlock".
5. For each confirmation: `pmi profile set <field> '<value>' --evidence "<file:line | data observation | user: ...>"`
   - Give lists and dicts as JSON: `'["store_code"]'`, `'{"metric":"mae","value":4.30,"source":"train.py output"}'`
   - If there is no time axis, explicitly confirm `none` for `time_column` and `[]` for `entity_keys`.
6. `reported_metric`: the performance the project itself claims. Found in report files, the README, notebook outputs or script output. If you cannot find it, do not invent it; ask the human.

## Writing the adapter
Contract and examples: `references/adapter-contract.md`. In short:
- Edit `runs/<id>/workspace/pmi_adapter.py`. It is the only executable file you can write.
- Mirror the project's **own** data loading, split, preprocessing and model steps. Do not fix the project. If there is a bug, copy it as-is, because the project itself is what we audit.
- Write `file:line` in the `sources` entry of each method.
- `split()` must return index labels; no `reset_index`.
- `fit(train_df, seed)`: `seed=0` must reproduce the project's own configuration exactly (e.g. random_state). Other seeds are for noise measurement.
- Then run `pmi adapter validate`. This is a human gate, because project code runs for the first time. Then run `pmi baseline`.
  - Fidelity `confirmed` → continue.
  - `mismatch` → explain the gap. Is the cause the adapter (mirroring error) or the project report (produced with different data/code)? Do not decide without evidence.
  - No reported metric → ask the human. `pmi adapter confirm --evidence "..."` is used only if the human checked the adapter line by line.
- If the project has no runnable pipeline (data only): `pmi adapter validate --surrogate '<json>'`. Results then describe a surrogate model, not the project's model, and are at most Simulated.

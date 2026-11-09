# Domain packs

The PMI core is domain-agnostic. The profile schema contains no industry vocabulary, and a test enforces this (`tests/test_profiling.py`). Industry knowledge is added through **domain packs**.

What a pack contains:

| Part | Location | Role |
|---|---|---|
| Agent knowledge | `claude_config/skills/domain-<name>/` | Channel and business model, profile mapping, industry-specific hypothesis families |
| Pack notes and design | `domain_packs/<name>/README.md` | Scope and consequence-simulation design |
| Benchmark | a project in `examples/make_examples.py` | Synthetic project with a hidden answer key, real defects and decoys |
| (Stage 5) Consequence model | `src/pmi/domains/<name>/` | Translating forecast error into business metrics |

Rules:
1. A pack is activated only after the profile is confirmed and a human agrees. It is never inferred from column names.
2. A pack cannot relax core rules (pre-registration, status caps, human gates).
3. A pack cannot add industry words to the core.

Available packs: `otc_channel`

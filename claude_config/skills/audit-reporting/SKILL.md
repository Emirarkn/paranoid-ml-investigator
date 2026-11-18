---
name: audit-reporting
description: Present the audit result to the user. Generate pmi report (measurement report) and notes/findings.md (agent interpretation), audit them with claim-auditor and pmi check-claims, and write the closing message. Use in the Report phase.
---

# Audit reporting

## Two layers
1. **`pmi report`** → `runs/<id>/report.md`. Generated entirely from the ledger. Do not touch it; editing is blocked.
2. **`runs/<id>/notes/findings.md`** → your interpretation: priority order, mechanism explanation, business-impact discussion and next steps.

## findings.md template
```markdown
# Audit interpretation — <project>  (run <id>)

## Short answer
<3–5 sentences answering the user's question. Every claim with an H-/E- id.>

## Is the evaluation valid?
<Verified defects; Rejected ones too, as "checked, no problem">

## Most critical findings
1. H-xxx [Status] — what, why it matters, evidence (E-xxx), uncertainty

## Robustness profile (Simulated)
| Condition | Base | Level | EAF (E-xxx) | Threshold |

## Untested / open questions
<Suspected + Inconclusive + "no test tool" + information expected from the human>

## Proposed fixes (untested)
<--fix records; to be tested with counterfactuals in stage 6>
```

## Writing rules
- Every number comes from a recorded result and is written **in the same sentence** as its E-id. Round numbers to the recorded precision.
- The word "verified" is used only together with H-ids whose status is Verified.
- Words like "improved" or "fixed" are never written without an E-id. Until stage 6 they should not be written at all.
- If you give a file:line reference, give one you opened and checked in the copy.

## Audit
1. `pmi check-claims runs/<id>/notes/findings.md` → issue count must be 0.
2. `claim-auditor` subagent → catches exaggerations the automatic check misses.
3. `evidence-verifier` subagent for P1–P2 Verified/Simulated findings.
4. `pmi integrity` → ok.

## Prophecy layer (after the audit above)
Hand the run to the `prophet` subagent. It writes `notes/prophecies.md` with the `prophecy` skill and must reach
0 issues in `pmi check-claims runs/<id>/notes/prophecies.md`. Prophecies never enter `findings.md` or `report.md`.

## Closing message
Keep it short: the short answer, the 3 most critical findings, the report path and the decisions expected from the human. Do not repeat the report content in the message.
Last, under its own heading **Kehanetler (spekülatif)**: the three darkest prophecies, one line each with their
basis (H-id or DAYANAKSIZ) and early warning sign, and the path to `notes/prophecies.md`.

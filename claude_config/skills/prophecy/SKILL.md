---
name: prophecy
description: Template and rules for the prophecy layer (notes/prophecies.md). Turns audit findings into exaggerated worst-case consequence chains, each with basis, assumptions, early warning sign and falsifier. Use in phase 8 (Prophecy), by the prophet subagent, after `pmi report`.
---

# Prophecy layer

The measurement layer answers "what is true?". The prophecy layer answers "if we ignore this, how bad can it get?".
It is deliberately dark and exaggerated. It is never evidence, and it never feeds back into statuses or the report.

## Where it lives
- File: `runs/<id>/notes/prophecies.md` (only this file; `pmi report` never includes it)
- Audit: `pmi check-claims runs/<id>/notes/prophecies.md` (prophecy rules by file name; or `--mode prophecy`)

## Template (field names are checked by check-claims)
```markdown
# Kehanetler — <proje>  (koşu <id>)
> Bu dosya spekülatiftir. Ölçülen gerçekler report.md ve findings.md içindedir.

## Kehanet 1: <karanlık başlık>
> <isteğe bağlı dörtlük, 4 kısa satır>

Dayanak: H-011 [Suspected]
Zincir: <bulgu> → <ilk etki> → <ikinci etki> → <felaket>
En kötü sonuç: <abartılı, somut, iş diliyle>
Varsayım: <spekülatif sayıların dayandığı varsayımlar; ör. talep yılda %5 büyür>
Erken uyarı: <ne, nerede, ne zaman izlenir; ör. Ocak–Mart 2027 sell-out'u planın %5 üstündeyse>
Çürütme: <hangi gözlem bu kehaneti boşa çıkarır>
```

Field rules (enforced by `pmi check-claims`):
| Field | Rule |
|---|---|
| `Dayanak:` | Required. At least one known H-id, or the word `DAYANAKSIZ` |
| `H-xxx [Status]` | The tag must equal the ledger status |
| `Çürütme:` | Required |
| `Varsayım:` | Required in any block that uses a number without an E-id (years and numbers ≤ 10 excepted) |
| `E-xxx` | A number in the same sentence must be that experiment's recorded value |
| Verification words | Forbidden everywhere in the file ("doğrulandı", "kanıtlandı", "verified", "proven") |

## Writing the chain
1. Start from the finding as measured (status, E-id, number). Do not restate it as stronger than it is.
2. Ask "who acts on this output, and what do they do wrong if it is off?" Read the project's own plans and documents.
3. Push two or three steps further than is comfortable: operational → financial → reputational.
4. End with a concrete image (empty shelf in a named month, a budget line, a decision taken on a wrong number).
5. Then the sober part: assumptions, early warning sign, falsifier.

## Choosing what to prophesy
- One prophecy per P1–P2 hypothesis, whatever its status (Rejected ones get "the comeback" prophecy).
- Simulated amplification curves are natural material: "at 3× the error is …; in a bad year 3× is not exotic".
- Up to two `DAYANAKSIZ` prophecies for risks nobody tested; they are useful as a to-test list.
- Domain packs give disaster seeds (OTC: censored demand, channel loading, delayed sell-out, price shocks).

## Closing message placement
In the user message, prophecies come last, under their own heading "Kehanetler (spekülatif)", after the measured
findings. Never mix a prophecy sentence into the findings section.

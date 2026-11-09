# Mimari: tasarım dokümanı ↔ uygulama

Kaynak tasarım: `docs/system_design_v1.md`. Bu dosya her bileşenin nerede yaşadığını ve hangi aşamada olduğunu gösterir.

```
                ┌──────────────── Katman A — Intelligence (Claude Code) ─────────────────┐
  kullanıcı ──► │ CLAUDE.md (karakter + kurallar)   skills/ (yöntem)   agents/ (rol)     │
                │ project-cartographer · hypothesis-skeptic · experiment-designer        │
                │ evidence-verifier · claim-auditor                                       │
                └───────────────┬────────────────────────────────────────────────────────┘
                                │ yalnızca `pmi` CLI (permissions + guard hook)
                ┌───────────────▼──────── Katman B — Experimental Harness (Python) ──────┐
                │ core/ run, snapshot, policy   profiling/ inventory, data/code scan,    │
                │ auditors/checks   engine/ adapter, injectors, worker(subprocess),      │
                │ metrics(primary+independent)  evidence/ ledger(hash chain), verify     │
                └───────────────┬────────────────────────────────────────────────────────┘
                ┌───────────────▼──────── Katman C — Decision & Reporting ───────────────┐
                │ reporting/report (ledger-only)  reporting/claims (halüsinasyon denetimi)│
                └─────────────────────────────────────────────────────────────────────────┘
```

| Doküman bileşeni | Uygulama | Durum |
|---|---|---|
| Project Understanding Module | `profiling/*`, `pmi scan`, `profile.json`, subagent `project-cartographer` | ✅ v0.1 |
| Skeptical Hypothesis Engine | skill `skeptical-hypotheses`, subagent `hypothesis-skeptic`, `pmi hypothesis` | ✅ v0.1 |
| Experimental Planner | skill `experiment-design`, subagent `experiment-designer`, ön-kayıt | ✅ v0.1 |
| Structural Auditor | `auditors/checks.py` (7 check), `profiling/code_scan.py` (AST) | ✅ v0.1 |
| Fault Injection Engine | `engine/injectors.py` (missing, outliers, shift, time_lag, neutralize) | ✅ v0.1 |
| Failure Amplification Engine | `worker.amplify`, `build_levels`, EAF, eşik keşfi | ✅ v0.1 |
| Backtesting Engine | tek split (adapter). Rolling-origin çoklu fold yok | ⏳ Aşama 5 |
| Consequence Simulation Engine | — | ⏳ Aşama 5 |
| Evidence Verification Engine | `evidence/verify.py` (hash, replikasyon, bağımsız yeniden hesap, tavan) | ✅ v0.1 |
| Root Cause Analyzer | hipotez `mechanism` + evidence-verifier | 🟡 kısmi |
| Solution Planner | `hypothesis --fix` (test edilmemiş öneri) | 🟡 kısmi |
| Counterfactual Tester | — | ⏳ Aşama 6 |
| Report Generator | `reporting/report.py` + `audit-reporting` skill | ✅ v0.1 |
| Agent hallucination tests | `pmi check-claims`, subagent `claim-auditor`, guard hook | 🟡 temel (Aşama 7'de red-team benchmark) |

## Kritik tasarım kararları
1. **Domain-bağımsız profil.** Şemada domain kelimesi yoktur (test ediliyor). Zaman ekseni, birim ve hedef projeden öğrenilir ve insan onayıyla kesinleşir. Onaysız alana ihtiyaç duyan analiz bloke edilir.
2. **Adapter fidelity kapısı.** Model tabanlı her kanıt, adapter'ın projeyi gerçekten taklit ettiğine bağlıdır. Bu ya raporlanan metriğin yeniden üretilmesiyle (`pmi baseline`) ya da insan beyanıyla kanıtlanır. Kanıtlanmazsa sonuç en fazla Inconclusive olur.
3. **Ön-kayıt.** Spec ve karar kuralı deney çalışmadan önce hash'lenir. Bir deney yalnızca bir kez çalışır.
4. **İki metrik implementasyonu.** Deney numpy ile ölçer, verify sklearn/pandas ile yeniden hesaplar.
5. **Tamper-evident ledger.** Her olay bir önceki olayın hash'ini içerir.
6. **Koşul büyütülür, hata değil.** Göreli ve mutlak merdivenler ayrı etiketlenir, fiziksel sınırlar işaretlenir ve gerçekleşen koşul ayrıca ölçülür.

## Run klasörü
`src/pmi/core/run.py` docstring'ine bakın.

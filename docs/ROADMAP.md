# Roadmap durumu

| Aşama | Kapsam | Durum | Kabul kriteri nasıl test ediliyor |
|---|---|---|---|
| 1 Foundation | run, snapshot, workspace kopyası, integrity, CLI, policy | ✅ | `tests/test_foundation.py`: hedef hash'leri değişmiyor, değişiklik yakalanıyor, secret dosyaları kopyalanmıyor |
| 2 Structural Intelligence | inventory, data scan, AST code scan, profil (aday → onay) | ✅ | `tests/test_profiling.py`: iki farklı sözlüklü projede target, zaman, grain, entity ve task doğru aday; şemada domain kelimesi yok |
| 3 Hypothesis & Evidence | ledger, ön-kayıt, verify, tavanlar, hash zinciri | ✅ | `tests/test_evidence.py`: Suspected/Verified/Rejected karışmıyor, tamper yakalanıyor, fidelity kapısı çalışıyor |
| 4 Amplification MVP | missing, outliers/shift, time_lag, ablation; EAF; eşik | ✅ (MVP) | `tests/test_amplification.py`: göreli/mutlak merdiven, limit bayrağı, aynı seed ile aynı sayılar, bağımsız yeniden hesap |
| 5 Consequence | rolling-origin backtest, segment metrikleri, iş simülasyonu (senaryo A/B/C, Monte Carlo) | ⏳ | — |
| 6 Repair & Retest | `workspace/repairs/<fix>` izole kopyalarda düzeltme, counterfactual karşılaştırma, yan etki taraması | ⏳ | — |
| 7 Agent Red Team | yanıltıcı doküman, sahte metrik ve bozuk referans içeren benchmark; claim-checker sertleştirme | 🟡 temel `check-claims` var | — |
| OTC paketi | kanal skill'i, hata kataloğu, sentetik benchmark | ✅ v0.1 (bilgi katmanı) | `tests/test_profiling.py` (otc testleri) |
| 8 Hardening | büyük dosya, kesilen işlem toparlama, performans, HTML rapor | ⏳ | — |

## Aşama 4'ten kalan genişletmeler
- Stockout / sansürlü hedef injector'ü. Bunun için profilde "kısıt göstergesi" alanı gerekir ve bu alan domain-bağımsız tanımlanmalıdır.
- Leakage kapsamı amplification: sızıntılı bilginin oranını değiştirmek
- Alt grup temsili (bias) injector'ü
- Birleşik senaryolar: iki injector'ün birlikte uygulanması

## Benchmark (Bölüm 11)
`examples/make_examples.py` iki sentetik proje üretir: gerçek kusurlar ve tuzaklar içerir, cevap anahtarı gizlidir. Hedef 20 senaryoya çıkmak. MVP eşikleri ilk benchmark sonuçlarından sonra belirlenecek.

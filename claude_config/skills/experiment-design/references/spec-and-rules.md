# Spec ve karar kuralı şemaları

## check
```json
{"check": "target_proxy", "params": {"threshold": 0.98, "max_future_lag": 3, "exclude": []}, "data_via": "profile"}
```
- `data_via: "profile"` → veri onaylı `data_source` dosyasından okunur, adapter kullanılmaz. Ham veri gerçeği olduğu için Verified olabilir.
- `pmi checks` komutu mevcut check'leri, gerekli profil alanlarını ve hangilerinin adapter split'ine ihtiyaç duyduğunu listeler.

| check | params |
|---|---|
| static_patterns | `patterns` (filtre), `files` |
| key_uniqueness | — |
| target_proxy | `threshold`, `max_future_lag`, `exclude`, `columns` |
| temporal_overlap | `tolerance_share` |
| split_duplicates | `exclude`, `tolerance_rows` |
| entity_overlap | `expect_disjoint` (true ise kesişim = kusur) |
| missing_rates | `max_rate` |

Kural: `{"type": "defect_found"}`

## baseline
`pmi baseline [--replicates 3] [--min-gap 0.05]`. Bu komut hipotezi ve deneyi kendisi oluşturur.
Kural: `{"type": "baseline_gap", "min_relative_gap": 0.05}`
- gap ≤ `policy.evidence.baseline_reproduction_rel_tol` → yeniden üretildi (Rejected) ve adapter fidelity = confirmed
- gap ≥ min_relative_gap → yeniden üretilemedi. İnsan-onaylı adapter yoksa sonuç Inconclusive olur, çünkü fark adapter'dan kaynaklanıyor olabilir.

## amplify
```json
{"injector": "missing|outliers|shift|time_lag", "columns": ["..."], "where": "test|train|both",
 "replicates": 3, "seed": 0, "metrics": ["mae","bias"], "levels": [0.1, 0.3],
 "params": {"kind": "additive|multiplicative"}}
```
- `levels` verilmezse seviyeler otomatik hesaplanır: göreli merdiven (1×, 2×, 3×, 5× ölçülen taban) ya da mutlak merdiven (A1..An, `config/amplification.yaml`).
- Etiketler: göreli merdivende `"1x","2x","3x","5x"`, mutlak merdivende `"A1","A2",...`. Son seviye için `"max"` kullanılabilir.
- `time_lag` için `time_column` ve `entity_keys` onaylı olmalıdır.

Kural: `{"type": "eaf", "metric": "mae", "level": "3x", "min_eaf": 1.2}`
- pass: ortalama EAF ≥ min_eaf **ve** en düşük EAF ≥ gürültü tabanı. Herhangi bir replicate'te model çökerse de pass sayılır.
- fail: en yüksek EAF < min_eaf
- diğer durumlar: inconclusive

## ablation
```json
{"features": ["f1","f2"], "mode": "individual|cumulative", "where": "test|both", "replicates": 3}
```
- `where: test`: eğitilmiş model, feature sabitlenir. Modelin o feature'a ne kadar dayandığını ölçer.
- `where: both`: feature olmadan yeniden eğitim. Bilginin başka feature'larla telafi edilip edilemediğini ölçer.
- Kural: `{"type":"eaf","metric":"mae","level":"<feature adı veya +feature>","min_eaf":1.5}`

## EAF
`EAF = loss(stres) / loss(1×)`, seed bazında hesaplanır. Yüksek-iyi metriklerde (accuracy, r2, auc, f1) loss = 1 − değer. İşaretli metriklerde (bias) loss = |değer|.

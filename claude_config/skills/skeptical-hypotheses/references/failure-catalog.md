# Failure catalog (domain-bağımsız)

Her aile için şu bilgiler var: hangi başarı gözlemini açıklayabileceği, tipik işaretler ve bugün kullanılabilen `pmi` testi. Parantez içindeki domain örnekleri sadece **örnektir**. Projeye uymuyorsa o aileyi gerekçesiyle ele.

## A. Değerlendirme geçerliliği (önce bunlar)
| Aile | İşaret | pmi testi |
|---|---|---|
| A1 Hedef sızıntısı (target leakage) | Hedeften türetilmiş feature, hedefle neredeyse eşit sütun | `check target_proxy` (+ zaman/entity onaylıysa gelecek-lag kontrolü) |
| A2 Gelecek bilgisi (look-ahead) | `shift(-k)`, ileri tarihli join, dönem sonu toplamları | `check static_patterns` (negative_shift), `check target_proxy` |
| A3 Zamansal split ihlali | Zaman serisinde rastgele split / shuffled KFold | `check static_patterns`, `check temporal_overlap` |
| A4 Preprocessing sızıntısı | scaler/encoder/imputer split'ten önce tüm veriye fit | `check static_patterns` (preprocessing_fit_before_split); etkisi için ablation/adapter karşılaştırması (Aşama 6) |
| A5 Satır/grup kopyası | Aynı satır veya aynı entity train ve test'te | `check split_duplicates`, `check entity_overlap` |
| A6 Rapor yeniden üretilemiyor | Raporlanan metrik farklı veri/kod ile üretilmiş | `pmi baseline` |
| A7 Test üzerinde ayar | Hiperparametre/eşik test seti görülerek seçilmiş | `check static_patterns` (fit_on_evaluation_data); kod okuma |

## B. Hedef ve metrik tanımı
| Aile | İşaret | pmi testi |
|---|---|---|
| B1 Sansürlü/kesilmiş hedef | Gözlenen değer gerçek büyüklüğün alt sınırı (ör. arz kısıtında satış ≠ talep, kapasite tavanı, survivorship) | Veri check'i + insan sorusu; şimdilik `missing_rates`/`key_uniqueness` ve kod okuma; sonuç çoğunlukla Suspected/Inconclusive |
| B2 Vekil hedef | Modellenen şey iş kararının ihtiyaç duyduğu şey değil | İnsan sorusu (`business_context`) |
| B3 Metrik-iş uyumsuzluğu | Ortalama hata iyi ama iş açısından kritik segmentte kötü, ya da bias işaretli | `baseline` metrik seti; segment analizi Aşama 5+ |
| B4 Toplulaştırma yanılgısı | Toplamda iyi, alt birimlerde kötü | Aşama 5+ (segment backtest) |

## C. Veri kalitesi ve yapı
| Aile | İşaret | pmi testi |
|---|---|---|
| C1 Eksik veri | Eksik oranı yüksek veya zaman içinde değişiyor | `check missing_rates`; dayanıklılık için `amplify missing` |
| C2 Aykırı değer | Kuyruklar, sentinel değerler (ör. -1, 9999) | `amplify outliers`; veri taraması |
| C3 Anahtar tekilliği | (entity, zaman) tekrarları, çift sayım | `check key_uniqueness` |
| C4 Sabit/ID sütunları | `unique_ratio≈1` olan sütun feature olarak kullanılıyor | scan `id_like_columns` + kod okuma |

## D. Dayanıklılık (sensitivity) — hepsi en fazla Simulated
| Aile | Soru | pmi testi |
|---|---|---|
| D1 Eksik girdi | Eksik oranı 2×/3×/5× olursa? | `amplify missing` |
| D2 Aykırı/şok | Aykırı payı büyürse? | `amplify outliers` |
| D3 Dağılım kayması | Girdi dağılımı k·std kayarsa? | `amplify shift` |
| D4 Gecikmeli/bayat girdi | Feature k dönem geç gelirse? | `amplify time_lag` (zaman+entity onaylı olmalı) |
| D5 Feature bağımlılığı | Kritik feature kaybolursa? | `ablation` (individual / cumulative) |
| D6 Eğitim verisi kalitesi | Eğitim verisi bozuksa? | `amplify ... where=train` |

## E. LLM / RAG bileşenleri (Aşama 7+)
Halüsinasyon, kaynak dışı cevap, belirsiz görevde aşırı güven. Bunlar için şu an pmi testi yok. Varsa hipotez olarak kaydet; test edilemiyorsa Suspected kalır ve raporda "test aracı yok" diye görünür.

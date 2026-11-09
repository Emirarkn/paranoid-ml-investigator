# OTC kanal hata kataloğu

Her ailede şu bilgiler var: genel katalogdaki karşılığı (`skeptical-hypotheses/references/failure-catalog.md`), işaretleri, yanlışlama testi ve bugünkü araç durumu.

| # | Aile | Genel karşılık | İşaret | Yanlışlama testi | Araç |
|---|---|---|---|---|---|
| O1 | Sell-in'in talep diye modellenmesi | B2 vekil hedef | Target sütunu depo yüklemesi, ama karar tüketici talebiyle ilgili | Kullanıcı target'ın karar ihtiyacıyla aynı olduğunu onaylarsa çürür | İnsan sorusu → Suspected / Rejected |
| O2 | Stok kesintisinde satış = talep | B1 sansürlü hedef | Stok işareti veya sıfır satış dizileri; kesinti sonrasında sıçrama | Kesinti satırları çıkarıldığında model hatası ve bias değişmiyorsa çürür | Kısmen: segment metriği yok (Aşama 5) |
| O3 | Kanal stoku dalgası | B1 + C2 | Fiyat artışı veya kampanya öncesinde sell-in zirvesi, ardından birkaç dönem düşük sell-in; sell-out düz | Sell-in ile sell-out arasındaki fark birikimli olarak sıfır etrafında dolaşıyorsa çürür | Veri analizi, Suspected |
| O4 | Sell-out / panel gecikmesi | A2 / D4 | Pazar verisi dönem sonundan sonra geliyor, ama feature olarak aynı dönemde kullanılıyor | `amplify time_lag` ile gecikme gerçek değerine çekildiğinde EAF ≈ 1 ise çürür | ✅ `time_lag` |
| O5 | Kampanya takvimi sızıntısı | A2 | Kampanya feature'ı fiilen gerçekleşen kampanyadan türetilmiş (plan değil) | `feature_availability` = known_at_prediction onaylanırsa çürür | İnsan sorusu + ablation |
| O6 | Tek sezona aşırı uyum | B4 | Test dönemi tek bir sezonu kapsıyor | Rolling-origin ile farklı sezonlarda hata benzerse çürür | Aşama 5 (walk-forward) |
| O7 | İade ve düzeltme satırları | C2 | Negatif miktarlar, dönem sonu düzeltmeleri | Negatif satırlar çıkarıldığında metrik değişmiyorsa çürür | Veri taraması (`share_negative`) |
| O8 | Yeni ürün etkisi | B4 | Geçmişi kısa entity'ler toplam metriği bozuyor | Segment metriği (Aşama 5) | Suspected |
| O9 | Depo / bölge toplulaştırma uyumsuzluğu | B4 | Model ulusal seviyede, karar depo seviyesinde | Karar seviyesi profil ile aynıysa çürür | İnsan sorusu |

## Kanal için tipik stres senaryoları (amplify)
| Senaryo | Injector | Gerçekçilik notu |
|---|---|---|
| Sell-out raporu eksik gelir (bazı depolar raporlamaz) | `missing` (sell-out feature'ları, `where=test`) | 5× çoğu zaman gerçekçi değildir, sınırı raporda yaz |
| Panel verisi 1–3 dönem gecikir | `time_lag` | Gerçek gecikmeyi insandan öğren |
| Fiyat şoku | `shift` (fiyat endeksi, multiplicative) | Fiyatlar düzenleniyorsa sınırları kullanıcıya sor |
| Kampanya bilgisi kaybolur | `ablation` (kampanya feature'ı) | — |

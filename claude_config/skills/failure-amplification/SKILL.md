---
name: failure-amplification
description: Bir problemin koşulunu (hatayı değil) kontrollü biçimde 1×→2×→3×→5× büyüterek modelin dayanıklılık eğrisini, Error Amplification Factor'ü ve kabul edilemezlik eşiğini bulmak. Amplify fazında, doğrulanmış kusurlar ve kritik girdiler için kullan.
---

# Failure amplification

## Prensip
**Hatanın oluşmasına neden olan koşul büyütülür, hata oranı değil.** Eksik oranı 3× arttığında hata 1.4× da artabilir, 5× da. Bu ilişki deneyle keşfedilir.

- `1×` projenin **olduğu gibi** halidir. Ölçülen taban koşul neyse odur.
- Taban > 0 ise **göreli merdiven** kullanılır: 2×, 3×, 5× = taban × N. Gerçekleşen koşul `condition_realized` olarak ayrıca ölçülür ve raporlanır.
- Taban = 0 ise ya da koşulun doğal bir tabanı yoksa (shift, lag) **mutlak merdiven** kullanılır: A1, A2... Bunlar "N kat" diye anlatılamaz.
- Fiziksel/mantıksal sınırı aşan seviyeler kırpılır ve `limit_exceeded` olarak işaretlenir. Raporda "AŞILDI" görünür.

## Seçim: neyi büyütmeli?
1. **Doğrulanmış (Verified) kusurlar:** Kusurun büyüklüğü artarsa ne olur?
2. **Profilde iş açısından kritik girdiler:** Hangi feature'lar tahmin anında gecikebilir ya da eksik gelebilir? Bunu `feature_availability` ve `business_context` alanlarından çıkar.
3. **Ablation'da en yüksek EAF'ye sahip feature'lar:** Model neye bağımlıysa ilk orayı stresle.

## Injector ↔ problem ailesi
| Problem | Injector | Koşul ölçüsü |
|---|---|---|
| Eksik veri | `missing` | eksik hücre payı |
| Aykırı değer | `outliers` | robust-z > eşik olan satır payı |
| Dağılım kayması | `shift` | std birimi kayma (veya çarpımsal) |
| Gecikmeli/bayat feature | `time_lag` | dönem sayısı (entity içinde) |
| Feature bağımlılığı | `ablation` | kaldırılan feature(lar) |

Henüz desteklenmeyenler (stockout/sansür, leakage kapsamı, alt grup temsili, birleşik senaryolar) Aşama 4+ kapsamında eklenecek. Bunları hipotez olarak kaydet ve "test aracı yok" diye raporla.

## Failure threshold discovery
- `acceptable_threshold` onaylıysa (`{"metric":"mae","max":5.0}`) sonuçta `threshold.first_level` alanı, kabul edilemez hale gelinen ilk seviyeyi gösterir.
- Onaylı değilse yalnızca eğri raporlanır. Eşik uydurma, insana sor.

## Okuma
- **EAF eğrisi monoton mu?** Değilse gürültü ya da etkileşim olabilir. Replicate sayısını artır veya Inconclusive kabul et.
- **Esneklik:** log(EAF)/log(N). 1'den küçükse girdi bozulmasına göre hata yavaş büyüyor demektir, büyükse hata koşuldan hızlı büyüyordur.
- **Failures > 0:** Model koşul altında çöktü, örneğin NaN değerleri işleyemiyor. Bu ayrı ve güçlü bir bulgudur.
- **where=test için düşük EAF ama where=train için yüksek EAF:** Sorun üretim girdisinde değil, eğitim verisi kalitesinde.

## Raporlama dili
"Eksik oranı (ölçülen taban %4.8) 3×'e çıkarıldığında MAE EAF=1.35 [1.31, 1.40] (E-012, Simulated)." Bu cümleyi "üretimde %35 kötüleşecek" diye yazma.

---
name: skeptical-hypotheses
description: Bir modelin raporlanan başarısını açıklayabilecek alternatif açıklamaları sistematik biçimde üretmek, her birine yanlışlama testi, tür (defect/sensitivity) ve öncelik vermek. Challenge fazında, pmi hypothesis add öncesinde kullan.
---

# Skeptical hypotheses

## Temel hareket
"Model iyi çalışıyor" iddiasını bir **gözlem** olarak al ve onu üretebilecek tüm mekanizmaları listele. Gerçek öğrenme bunlardan yalnızca biridir. Diğerleri sızıntı, kolay test seti, yanlış metrik, sansürlü hedef ve benzerleridir.

Aileler ve her ailenin tipik testi: `references/failure-catalog.md`

## Hipotez kalitesi kontrol listesi
- [ ] **Test edilebilir:** Hangi `pmi` deneyiyle sınanacağı belli.
- [ ] **Yanlışlanabilir:** `--falsification` alanında hangi sonucun hipotezi öldüreceği yazılı.
- [ ] **Mekanizmalı:** "Neden" sorusu kod veya veri yolu üzerinden açıklanmış.
- [ ] **Kaynaklı:** `--refs` alanında dosya:satır var (statik şüpheden geliyorsa onun konumu).
- [ ] **Doğru tür seçilmiş:** `defect` = "bu kusur projede şu an var" (Verified olabilir). `sensitivity` = "koşul büyürse model kırılır" (en fazla Simulated).
- [ ] **Projenin dilinde:** Kavram uydurulmamış.

## Önceliklendirme (1 = en yüksek)
`öncelik ≈ etki × olasılık × test edilebilirlik`
- **Etki:** Değerlendirmeyi geçersiz kılar mı (P1)? İş kararını değiştirir mi (P2)? Kozmetik mi (P4–5)?
- **Olasılık:** Statik bir işaret, veri gözlemi veya yapısal bir neden var mı?
- **Test edilebilirlik:** Mevcut check/injector ile şimdi test edilebiliyor mu?

## Tuzaklar (false positive kontrolü)
Her turda en az bir "şüpheli görünüyor ama muhtemelen meşru" durumu kayda al. Bunlar Rejected çıkmalıdır. Rejected çıkmazsa ya senin yargın ya da test yanlıştır. İki örnek:
- Geçmiş değerden türetilmiş lag feature ile target arasındaki yüksek korelasyon
- ID benzeri ama modele girmeyen bir sütun

## Kayıt
```
pmi hypothesis add --title "..." --statement "..." --mechanism "..." --expected "..." \
  --falsification "..." --kind defect|sensitivity --priority N --refs file.py:12 --affected "..."
```
Düzeltme fikrin varsa `--fix` ile ekle. Bu bir **öneridir** ve raporda "test edilmedi" etiketiyle görünür.

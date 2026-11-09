---
name: experiment-design
description: Bir hipotezi ön-kayıtlı (pre-registered) bir pmi deneyine çevirmek. Deney tipi seçimi, spec yazımı, karar kuralı ve eşik gerekçesi, replicates, where seçimi ve gerçekçilik notu. pmi experiment plan öncesinde kullan.
---

# Experiment design

## İlke: önce kural, sonra veri
Karar kuralı deneyden **önce** kaydedilir ve hash'lenir. Sonuca bakıp eşiği değiştirmek p-hacking'dir. Yeni bir eşik gerekiyorsa yeni bir deney planlanır ve iki deney de raporda kalır. `pmi verify` hipotezin tüm deneylerini değerlendirir. Çelişkili kanıt varsa sonuç Inconclusive olur.

## Tip seçimi
| Soru | Tip | Kural | Statü tavanı |
|---|---|---|---|
| Kusur projede şu an var mı? | `check` | `defect_found` | Verified (veri/kod üzerinden, ya da fidelity onaylı adapter ile) |
| Raporlanan performans tutuyor mu? | `baseline` (`pmi baseline`) | `baseline_gap` | Verified sadece insan-onaylı adapter ile |
| Koşul büyüyünce ne olur? | `amplify` | `eaf` | Simulated |
| Model hangi girdiye bağımlı? | `ablation` | `eaf` | Simulated |

Tam şema ve örnekler: `references/spec-and-rules.md`

## Eşik seçimi
1. İnsan bir eşik verdiyse (`acceptable_threshold`) onu kullan ve kaynak olarak göster.
2. Vermediyse konvansiyonel bir eşik kullan ve bunu açıkça söyle. Örneğin: "EAF ≥ 1.2 (hatada %20 artış), iş eşiği verilmediği için konvansiyonel."
3. Gürültü tabanı otomatik uygulanır: en düşük EAF ≥ 1 + 2 × (seed gürültüsü) olmalı.

## `where` seçimi
- `test`: Model eğitilmiş, üretimde gelen girdi bozuluyor. En yaygın seçenek.
- `train`: Eğitim verisi bozuk, test temiz. Veri kalitesinin öğrenmeye etkisini ölçer.
- `both`: Kalıcı bir veri kalitesi sorunu. Model yeniden eğitilir.

## Gerçekçilik notu (zorunlu)
Her amplify planında şunları yaz: 5× seviyesi gerçek dünyada mümkün mü? Hangi olay buna yol açar? `limit_exceeded` beklentisi var mı? Bu not `notes/` altına gider.

## Akış
```
pmi experiment plan --hypothesis H-003 --type amplify \
  --spec '{"injector":"missing","columns":["x1"],"where":"test","replicates":3}' \
  --rule '{"type":"eaf","metric":"mae","level":"3x","min_eaf":1.2}'
pmi experiment run E-007
pmi verify H-003
```
Başarısız bir deney (`state=failed`) de kanıttır. Hata mesajını oku. Adapter'dan mı kaynaklanıyor, yoksa modelin koşul altında çökmesinden mi? Model çöküşü amplify içinde ayrıca `failures` olarak sayılır ve bu bir bulgudur.

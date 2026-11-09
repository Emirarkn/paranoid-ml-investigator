---
name: investigate
description: PMI ana oyun kitabı. Bir ML/AI projesini baştan sona denetlemek için fazları, kapıları, bütçe yönetimini ve durma koşullarını tanımlar. "Bu projeyi denetle", "hataları bul", "stres testi uygula" gibi isteklerde ilk yüklenecek skill.
---

# Investigate — uçtan uca denetim

## Ön kontrol
1. `pmi status`. Aktif bir run varsa kaldığı yerden devam et.
2. Run yoksa kullanıcıdan hedef klasörü iste ve `pmi init --target "<klasör>"` çalıştır. Bu bir insan kapısıdır.
3. Kullanıcının isteğini **araştırma sorularına** çevir ve `runs/<id>/notes/plan.md` dosyasına yaz. Örneğin "hataları bul, 2× ve 3× stres testi uygula" şunlara dönüşür: (a) değerlendirme geçerli mi? (b) hangi koşullar 2×/3× büyüyünce performans kabul edilemez olur?

## Faz akışı ve çıkış kriterleri

| Faz | Çıkış kriteri (bir sonraki faza geçmeden önce) |
|---|---|
| Discover | `target`, `task_type`, `data_source` onaylı. Zaman serisiyse `time_column`, `entity_keys` de onaylı. Onaysız alanlar ve nedenleri listelendi. |
| Bağla | `pmi adapter validate` başarılı. `pmi baseline` çalıştı. Fidelity `confirmed` oldu veya insan onayı alındı. Olmadıysa nedeni raporlandı. |
| Challenge | 4–8 önceliklendirilmiş hipotez kayıtlı. Her birinin yanlışlama testi var. En az biri tuzak kontrolü. |
| Experiment | P1–P2 hipotezlerin her biri için en az bir ön-kayıtlı deney çalıştı. |
| Amplify | Doğrulanmış kusurlar ve kritik girdiler için severity ladder çalıştı. Varsa eşik bulundu. |
| Verify | Deneyi olan her hipotez için `pmi verify` çalıştı. P1–P2 Verified/Simulated bulgular `evidence-verifier` incelemesinden geçti. |
| Report | `pmi report` üretildi. `notes/findings.md` yazıldı ve `pmi check-claims` temiz. |

## Öncelik kuralı
Önce değerlendirmenin kendisini denetle (leakage, split, baseline reproduction), sonra dayanıklılığı (amplification). Geçersiz bir değerlendirme üzerinde yapılan stres testinin anlamı yoktur. Rapor bu sırayla yazılır.

## Bütçe
- `pmi budget show` komutunu her 10 deneyde bir çalıştır.
- Bütçe dolarsa dur. Ne öğrendiğini, neyin açık kaldığını ve kaç deney daha gerektiğini insana yaz.

## Durma koşulları
- `pmi integrity` veya hash zinciri bozuldu → dur, insana bildir.
- Adapter projeyi taklit edemiyor (validate başarısız, fidelity mismatch) → model tabanlı deneyleri durdur. Yalnızca statik ve veri check'leriyle devam et ve bunu açıkça raporla.
- Kullanıcının sorusu cevaplandı ve kalan hipotezlerin beklenen değeri düşük → bitir.

## Oturumlar arası süreklilik
Her fazın sonunda `runs/<id>/notes/progress.md` dosyasına tarihli, kısa bir not ekle: ne yapıldı, sıradaki adım ne, hangi insan kararı bekleniyor. Yeni oturumda önce bu dosyayı oku.

## Kapanış mesajı (kullanıcıya)
1. Değerlendirme geçerli mi? (Verified kusurlar)
2. En kritik 3 bulgu, statüleriyle
3. Dayanıklılık profili: hangi koşul, hangi seviyede, hangi EAF (Simulated)
4. Test edilmemiş öneriler ve sonraki adımlar
5. `runs/<id>/report.md` yolu

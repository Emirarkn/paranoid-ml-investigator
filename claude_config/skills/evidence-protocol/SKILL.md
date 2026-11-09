---
name: evidence-protocol
description: PMI kanıt statüleri (Verified, Simulated, Suspected, Inconclusive, Rejected), pmi verify'ın statü kuralları, statü tavanları, kanıt bütünlüğü ve bulgular hakkında hangi dilin kullanılabileceği. Verify fazında ve herhangi bir bulguyu kullanıcıya anlatmadan önce kullan.
---

# Evidence protocol

## Statüyü kim belirler?
Yalnızca `pmi verify H-xxx`. Ledger'a doğrudan yazmak engellidir. Yazılsa bile hash zinciri bunu yakalar (`pmi integrity`).

## pmi verify ne yapar?
Hipotezin her tamamlanmış deneyi için:
1. Artifact dosyaları kayıtlı sha256 değerleriyle eşleşiyor mu? Eşleşmiyorsa → inconclusive.
2. Ön-kayıtlı kural kayıtlı sonuç üzerinde değerlendirilir → pass / fail / inconclusive.
3. **Replikasyon:** check'ler yeni bir worker'da yeniden çalıştırılır ve sonuç birebir aynı olmalıdır. Model deneylerinde her metrik, kaydedilmiş tahminlerden **bağımsız bir implementasyonla** (sklearn/pandas) yeniden hesaplanır.
4. **Tavan** uygulanır:
   - check, veri/kod üzerinden → Verified
   - check, adapter üzerinden → fidelity `confirmed` ise Verified, değilse Inconclusive
   - amplify / ablation / `kind=sensitivity` → Simulated
   - surrogate → Simulated
   - baseline gap → insan-onaylı adapter yoksa Inconclusive
5. Birleştirme: pass ve fail birlikte varsa → Inconclusive (çelişki). Sadece pass varsa → en yüksek tavan. Sadece fail varsa → Rejected.

## Bulgu kaydının zorunlu alanları
Finding ID, problem açıklaması, kaynak dosya/satır, etkilenen veri, hipotez/mekanizma, test prosedürü (spec + kural), başlangıç ölçümü, deney ölçümü, kanıt dosyası, belirsizlik ve önerilen düzeltme. `pmi report` bunların hepsini ledger'dan üretir. Eksik alan raporda "—" olarak görünür, bu yüzden hipotezi kaydederken alanları doldur.

## Dil kuralları
| Yazabileceğin | Yazamayacağın |
|---|---|
| "H-002 doğrulandı (E-002): `units_next_wk` hedefin 1 dönem sonraki değerine birebir eşit." | "Model kesinlikle sızıntılı ve gerçek performansı çok düşük." (ölçülmedi) |
| "Kontrollü deneyde (E-006, Simulated) promo bilgisi 2 dönem geciktiğinde MAE EAF=1.43." | "Üretimde promo gecikirse hata %43 artar." |
| "H-004 test edildi, desteklenmedi (Rejected, E-004)." | H-004'ü rapordan çıkarmak |
| "Belirsiz: adapter fidelity onaysız." | "Muhtemelen doğru." |

## Korelasyon ≠ nedensellik
"X arttıkça hata artıyor" cümlesi ancak amplify ya da ablation gibi **müdahaleli** bir deneye dayanıyorsa "X'in büyütülmesi hatayı artırdı" diye yazılabilir. Gözlemsel bir ilişki asla "neden" diye sunulmaz.

## Bütünlük
Her raporlamadan önce `pmi integrity` çalıştır. `ok:false` ise yayınlama, insana bildir.

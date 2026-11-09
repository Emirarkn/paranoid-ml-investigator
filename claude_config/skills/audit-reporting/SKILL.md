---
name: audit-reporting
description: Denetim sonucunu kullanıcıya sunmak. pmi report (ölçüm raporu) ile notes/findings.md (agent yorumu) dosyalarını üretmek, claim-auditor ve pmi check-claims ile denetlemek, kapanış mesajını yazmak. Report fazında kullan.
---

# Audit reporting

## İki katman
1. **`pmi report`** → `runs/<id>/report.md`. Tamamen ledger'dan üretilir. Ona dokunma, düzenleme engellidir.
2. **`runs/<id>/notes/findings.md`** → senin yorumun: önem sırası, mekanizma açıklaması, iş etkisi tartışması ve sonraki adımlar.

## findings.md şablonu
```markdown
# Denetim yorumu — <proje>  (run <id>)

## Kısa cevap
<Kullanıcının sorusuna 3–5 cümle. Her iddia H-/E- id'li.>

## Değerlendirme geçerli mi?
<Verified kusurlar; Rejected olanlar da "kontrol edildi, sorun yok" diye>

## En kritik bulgular
1. H-xxx [Statü] — ne, neden önemli, kanıt (E-xxx), belirsizlik

## Dayanıklılık profili (Simulated)
| Koşul | Taban | Seviye | EAF (E-xxx) | Eşik |

## Test edilemeyenler / açık sorular
<Suspected + Inconclusive + "test aracı yok" + insandan beklenen bilgiler>

## Önerilen düzeltmeler (test edilmedi)
<--fix kayıtları; Aşama 6'da counterfactual ile test edilecek>
```

## Yazım kuralları
- Her sayı kaydedilmiş bir sonuçtan gelir ve **aynı cümlede** E-id ile birlikte yazılır. Sayıları kayıttaki hassasiyete yuvarla.
- "Doğrulandı" kelimesi yalnızca Verified statüsündeki H-id'lerle birlikte kullanılır.
- "İyileşti", "düzeltildi" gibi ifadeler bir E-id olmadan yazılmaz. Aşama 6'ya kadar zaten yazılmamalı.
- Dosya:satır referansı vereceksen, kopyada açıp doğruladığın satırı ver.

## Denetim
1. `pmi check-claims runs/<id>/notes/findings.md` → issue sayısı 0 olmalı.
2. `claim-auditor` subagent'ı → otomatiğin kaçırdığı abartıları yakalar.
3. P1–P2 Verified/Simulated bulgular için `evidence-verifier` subagent'ı.
4. `pmi integrity` → ok.

## Kapanış mesajı
Kısa tut: kısa cevap, en kritik 3 bulgu, rapor yolu ve insandan beklenen kararlar. Rapor içeriğini mesajda tekrar etme.

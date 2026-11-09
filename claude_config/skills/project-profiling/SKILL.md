---
name: project-profiling
description: Bir projeyi domain varsayımı olmadan öğrenmek ve profil alanlarını (target, zaman ekseni, birim, değerlendirme protokolü, metrik, iş bağlamı) kanıtla doldurup insana onaylatmak; ardından projeyi taklit eden pmi_adapter.py yazmak. Discover ve Bağla fazlarında kullan.
---

# Project profiling + adapter

## Neden önemli
PMI hiçbir projeye hazır kavramla gelmez. "Haftalık", "mağaza", "müşteri" gibi her şey **bu projeden** öğrenilir. Onaysız profil alanına ihtiyaç duyan analizleri `pmi` bloke eder. Bu engel bir hata değil, tasarımın kendisidir.

## Adımlar
1. `pmi scan` çalıştır. Envanter, tablo taraması ve AST kod taraması üretir ve aday değerleri kanıtlarıyla doldurur.
2. Projeyi derinlemesine anlamak için `project-cartographer` subagent'ını çalıştır.
3. Adayları kod ve veriyle çapraz kontrol et:
   - Tarama "temporal" diyor ama kod tarihi hiç kullanmıyorsa → bu çelişkiyi soru olarak yaz.
   - Birden fazla target adayı varsa → hangisi raporlanan metriğe giriyor?
   - Grain "irregular" ise → olaylar mı, eksik dönemler mi? Veriye bak.
4. **Onay paketini** tek mesajda insana sun. Her alan için değer, kanıt ve "bunu onaylarsan şu analizler açılır" bilgisini ver.
5. Her onay için: `pmi profile set <alan> '<değer>' --evidence "<dosya:satır | veri gözlemi | user: ...>"`
   - Liste ve sözlükleri JSON olarak ver: `'["store_code"]'`, `'{"metric":"mae","value":4.30,"source":"train.py output"}'`
   - Zaman ekseni yoksa `time_column` için `none` ve `entity_keys` için `[]` değerlerini açıkça onaylat.
6. `reported_metric`: projenin kendi iddia ettiği performans. Rapor dosyası, README, notebook çıktısı veya script çıktısında bulunur. Bulamazsan uydurma, insana sor.

## Adapter yazımı
Sözleşme ve örnek: `references/adapter-contract.md`. Kısaca:
- `runs/<id>/workspace/pmi_adapter.py` dosyasını düzenle. Bu dosya senin yazabildiğin tek çalıştırılabilir dosyadır.
- Projenin **kendi** veri okuma, split, preprocessing ve model adımlarını taklit et. Projeyi düzeltme. Hata varsa o hatayı da aynen kopyala, çünkü denetleyeceğimiz şey projenin kendisi.
- Her metodun `sources` girdisine `dosya:satır` yaz.
- `split()` index etiketlerini döndürmeli, `reset_index` kullanılmamalı.
- `fit(train_df, seed)`: `seed=0` projenin kendi konfigürasyonunu (ör. random_state) birebir vermeli. Diğer seed'ler gürültü ölçümü içindir.
- Ardından `pmi adapter validate` çalıştır. Bu bir insan kapısıdır, çünkü proje kodu ilk kez çalışır. Sonra `pmi baseline` çalıştır.
  - Fidelity `confirmed` → devam.
  - `mismatch` → farkı açıkla. Sebep adapter mı (taklit hatası), yoksa proje raporu mu (rapor farklı veri/kodla üretilmiş)? Kanıtlamadan karar verme.
  - Raporlanmış metrik yoksa → insana sor. `pmi adapter confirm --evidence "..."` yalnızca insan adapter'ı satır satır kontrol ettiyse kullanılır.
- Projenin çalıştırılabilir bir pipeline'ı yoksa (sadece veri varsa): `pmi adapter validate --surrogate '<json>'`. Bu durumda sonuçlar projenin modelini değil, bir vekil modeli anlatır ve en fazla Simulated olur.

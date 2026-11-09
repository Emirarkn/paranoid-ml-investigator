---
name: leakage-hunting
description: Değerlendirmeyi geçersiz kılan sızıntı türlerini (hedef, gelecek bilgisi, zamansal split, preprocessing, kopya/grup, test üzerinde ayar) domain varsayımı olmadan aramak ve her birini pmi check'leriyle test etmek. Yüksek performans raporlayan her projede ilk iş olarak kullan.
---

# Leakage hunting

Sızıntı varsa diğer bütün bulgular (amplification dahil) yanlış bir başarı üzerine kurulmuş olur. Bu yüzden önce sızıntı aranır.

## 1. Statik iz
`pmi scan` → `static_suspicions`. Her biri için kopyadaki kodu aç ve bağlamını oku:
- `preprocessing_fit_before_split`: Fit edilen nesne gerçekten bir transformer mı? Fit edilen veri test satırlarını içeriyor mu?
- `random_split_with_temporal_data`: Satırlar gerçekten zamanda ileriye tahmin edilmesi gereken gözlemler mi? Yoksa kesitsel veride tarih sadece bir öznitelik mi? Cevap `prediction_horizon` ve `business_context` alanlarına bağlıdır.
- `negative_shift_future_values`: `shift(-k)` sonucu target'ı mı oluşturuyor (meşru), yoksa bir feature'ı mı (sızıntı)?
- `fit_on_evaluation_data`: Test verisiyle fit veya ayar yapılıyor mu?

Statik iz hipotezdir. Kayıt: `--kind defect --refs <konum>`.

## 2. Veri izi
- `check target_proxy` (`data_via: profile`): Hedefe veya hedefin **gelecek** değerine eşit ya da neredeyse eşit feature'ları bulur. Geçmiş-lag ilişkisiyle açıklanabilen feature'ları (meşru lag'ler) otomatik olarak ayırır.
- `check key_uniqueness`: Çift satırlar split'i delebilir.

## 3. Split izi (adapter gerekli, fidelity önemli)
- `check temporal_overlap`: Eğitimde test başlangıcından sonraki tarihler var mı? İkinci gösterge: en son eğitim satırından daha eski test satırlarının payı.
- `check split_duplicates`: Test satırı eğitimde birebir var mı?
- `check entity_overlap` (`expect_disjoint: true` yalnızca proje yeni entity'lere genelleme iddia ediyorsa): Görülmemiş birimlere genelleme iddiası test edilir.

## 4. Etki ölçümü
Bir sızıntı Verified olduysa etkisini ölç:
- `ablation` (`where: both`): Sızıntılı feature'ı çıkar ve yeniden eğit. EAF, sızıntının sağladığı sahte başarının bir alt sınırını verir. Başka feature'lar da sızıntıdan besleniyorsa bu bir alt sınırdır.
- Doğru split ile yeniden değerlendirme = Aşama 6 (counterfactual). Şimdilik `--fix` önerisi olarak yaz.

## Tuzaklar
- Hedefle 0.9+ korelasyonlu **geçmiş** lag feature'ı sızıntı değildir.
- Kesitsel veride (her satır bağımsız bir birim) rastgele split meşru olabilir. Önce `unit_of_analysis` alanını onaylat.
- Target encoding train içinde yapılıyorsa sızıntı değildir, tüm veride yapılıyorsa sızıntıdır.

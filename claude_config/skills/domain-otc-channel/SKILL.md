---
name: domain-otc-channel
description: OTC (reçetesiz ürün) / consumer health kanal paketi. Projenin bu alanda olduğu profilde ONAYLANDIKTAN sonra yüklenir. Üretici → depo/distribütör → eczane/perakende → tüketici zincirindeki veri tiplerini (sell-in, sell-out, stok, kampanya, fiyat), kanala özgü hata ailelerini ve bunların pmi ile nasıl test edileceğini anlatır. Proje bu alanda değilse kullanma.
---

# Domain paketi: OTC kanal

Bu paket çekirdeğin yerine geçmez, onun üstüne bir **bilgi katmanı** ekler. Çekirdek kurallar (profil onayı, ön-kayıt, statü protokolü) aynen geçerlidir.

## Ne zaman yüklenir?
Sadece `business_context` veya `unit_of_analysis` alanı onaylandıktan sonra ve projenin gerçekten bir kanal/dağıtım tahmini olduğu belli olduğunda yüklenir. Sütun adında "sell_in" geçmesi yeterli bir kanıt değildir. Kullanıcıya sor.

## Kanal modeli (genel)
```
Üretici ──sell-in──► Depo / distribütör ──(depo çıkışı)──► Eczane / perakende ──sell-out / offtake──► Tüketici
            ▲ siparişler, kampanya yüklemeleri          ▲ kanal stoku                          ▲ gerçek talep (çoğu zaman gözlenmez)
```
Projede hangi okun ölçüldüğünü **projeden öğren**. Aynı isim (ör. "satış") farklı projelerde farklı oklara karşılık gelebilir.

## Profil eşlemesi (onay paketine ekle)
| Kanal kavramı | Genel profil alanı | İnsana sorulacak |
|---|---|---|
| Neyin tahmin edildiği (sell-in mi, sell-out mu, talep mi?) | `target` + `business_context` | "Bu tahmin hangi kararı besliyor: üretim/ithalat mı, depo yüklemesi mi, eczane bulunurluğu mu?" |
| Ürün × depo / bölge / eczane | `entity_keys` | Toplulaştırma seviyesi karar seviyesiyle aynı mı? |
| Dönem (çoğu zaman ay veya hafta) | `time_column`, `time_grain` | Veriden öğrenilir. Varsayma. |
| Stok kesintisi işareti, kanal stok günü | `feature_availability` | Bu bilgi tahmin anında var mı? |
| Kampanya takvimi, fiyat değişimi | `feature_availability` | Kampanya kararı tahminden önce mi kesinleşiyor? |
| Panel / pazar verisi | `feature_availability` | Kaç dönem gecikmeyle geliyor? |

## OTC'ye özgü hipotez aileleri
Ayrıntı ve testler: `references/otc-failure-catalog.md`. Öncelik sırası:
1. **Vekil hedef:** sell-in "talep" diye modellenmiş.
2. **Sansürlü talep:** stok kesintisi dönemlerinde satış, talebin alt sınırıdır.
3. **Kanal stoku dalgaları:** fiyat artışı veya kampanya öncesi yüklemeler, sonrasında boşalmalar.
4. **Gecikmeli bilgi:** panel ve sell-out verisi geç geliyor, ama modelde tahmin anında biliniyormuş gibi kullanılıyor.
5. **Mevsimsellik ve epidemiyoloji:** soğuk algınlığı ve alerji gibi mevsimler yıldan yıla kayar; tek bir sezon başarısı genelleme sayılmaz.
6. **İadeler ve son kullanma tarihi:** negatif veya düzeltme satırları hedefi bozar.
7. **Yeni ürün ve kanibalizasyon:** geçmişi olmayan ürünler, toplam metriği gizlice kötüleştirir.

## Bugünkü pmi ile test edilebilenler
- Gecikmeli bilgi → `amplify time_lag` (panel/sell-out feature'ları), `check target_proxy` (gelecek-lag)
- Rastgele split ile aylık panel → `check temporal_overlap`, `check static_patterns`
- Kampanya ve fiyat feature bağımlılığı → `ablation`
- Eksik sell-out raporlaması → `amplify missing` (sell-out feature'ları)
- Anahtar tekilliği (ürün × depo × dönem) → `check key_uniqueness`

## Henüz test edilemeyenler (Suspected olarak kaydet, raporda "araç yok" de)
Sansürlü talebin büyütülmesi, kanal stoku simülasyonu, servis seviyesi ve kayıp satış etkisi. Bunlar Aşama 5'teki **kanal sonuç simülasyonu** ile gelecek (`domain_packs/otc_channel/README.md`).

## Yasaklar
- Şirket, marka veya ürün adı uydurma ya da başka projelerden taşıma. Sadece projede gördüğün isimleri kullan.
- Sektör "genel bilgisi"ni (ör. "kış aylarında satış artar") kanıt yerine koyma. Veride göster ya da hipotez olarak kaydet.

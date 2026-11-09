# Domain paketi: OTC kanal

Reçetesiz ürünler (OTC) ve consumer health için bir uzmanlık katmanı: üretici → depo/distribütör → eczane/perakende → tüketici zincirindeki tahmin projelerini denetler.

## Bugün içerdikleri (v0.1)
- **Agent skill'i:** `claude_config/skills/domain-otc-channel/`. Kanal modeli, profil eşlemesi, 9 hata ailesi (O1–O9) ve bunların pmi ile test yolları.
- **Benchmark:** `examples/make_examples.py` → `otc_channel` projesi. Aylık `yyyymm` dönem, ürün × depo paneli, sell-in/sell-out ve stok kesintisi işareti içerir. Gerçek kusurlar ve tuzaklar gömülüdür.
- **Gerçek veri yok.** Paketteki her şey genel kanal bilgisi ve sentetik veridir. Hiçbir şirkete, markaya veya iç veriye dayanmaz.

## Aşama 5 tasarımı: kanal sonuç simülasyonu
Amaç: tahmin hatasının sonraki dönemlere ve kanala nasıl yayıldığını senaryo bazında göstermek. Örnek zincir: eksik forecast → eksik sell-in → depo stoku düşer → eczanede kesinti → gözlenen sell-out düşer → sonraki forecast yeniden düşük kalır.

Tasarım ilkeleri:
1. **Parametreler öğrenilir, varsayılmaz.** Sipariş politikası, tedarik süresi, hedef stok günü, min sipariş ve maliyetler profilin yeni bir bölümüne (`consequence_params`) kanıtla ve insan onayıyla girer. Eksik parametre varsa simülasyon çalışmaz.
2. **Üç senaryo** (tasarım dokümanı §6): A = müdahalesiz, B = amplified failure (pmi amplify sonuçlarını girdi olarak kullanır), C = düzeltilmiş sistem (Aşama 6 counterfactual çıktısı).
3. **Talep belirsizliği:** tek sonuç yerine Monte Carlo aralıkları (talep senaryoları, seed'li).
4. **Çıktılar:** kesinti dönemi sayısı, kayıp satış (aralık olarak), stok fazlası, stok tutma maliyeti, depolar arası yanlış tahsis, SKU bazında bias, servis seviyesi.
5. **Statü:** tüm sonuçlar en fazla `Simulated` olabilir ve raporda "varsayıma bağlı senaryo" etiketi taşır.
6. **Geri besleme döngüsü:** kesinti sırasında gözlenen sell-out, sonraki dönemin eğitim verisine sansürlü olarak girer. Simülatör bunu açıkça modeller (O2).

## Yol haritası
- [ ] `consequence_params` profil bölümü ve onay akışı
- [ ] Depo-eczane iki kademeli stok simülatörü
- [ ] Sansürlü talep injector'ü: stok kesintisi süresini ve etkilenen entity sayısını büyütür
- [ ] Segment metrikleri (yeni ürün, sezon, depo)
- [ ] Walk-forward backtest (1/3/6/12 dönem ufku)

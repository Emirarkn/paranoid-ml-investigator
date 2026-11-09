# Domain paketleri

PMI'nin çekirdeği domain-bağımsızdır. Profil şemasında tek bir sektör kelimesi yoktur ve bu bir test ile kontrol edilir (`tests/test_profiling.py`). Sektör bilgisi **domain paketleri** ile eklenir.

Bir paketin içeriği:

| Parça | Yer | Görev |
|---|---|---|
| Agent bilgisi | `claude_config/skills/domain-<ad>/` | Kanal ve iş modeli, profil eşlemesi, sektöre özgü hipotez aileleri |
| Paket notları ve tasarım | `domain_packs/<ad>/README.md` | Kapsam ve sonuç simülasyonu tasarımı |
| Benchmark | `examples/make_examples.py` içinde bir proje | Gizli cevap anahtarlı, gerçek kusurlar ve tuzaklar içeren sentetik proje |
| (Aşama 5) Sonuç modeli | `src/pmi/domains/<ad>/` | Tahmin hatasının iş metriğine dönüşümü |

Kurallar:
1. Paket ancak profil onaylandıktan sonra ve insan teyidiyle devreye girer. Sütun adından tahmin edilmez.
2. Paket çekirdek kuralları (ön-kayıt, statü tavanları, insan kapıları) gevşetemez.
3. Paket, çekirdeğe sektör kelimesi ekleyemez.

Mevcut paketler: `otc_channel`

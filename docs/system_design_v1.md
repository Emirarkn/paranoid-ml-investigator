# PARANOID ML INVESTIGATOR
## Autonomous ML/AI Failure Discovery, Amplification & Consequence Analysis System

**Proje Türü:** AI Agent / ML Auditing / Adversarial Testing

**Doküman:** Sistem Tasarım Raporu ve Geliştirme Roadmap'i

**Versiyon:** 1.0 — Kasım 2026

**Hedef:** Yerel ortamda çalışabilen, farklı ML/AI projelerinde tekrar kullanılabilecek bir kalite kontrol ve araştırma sistemi geliştirmek.

---

# 1. Yönetici Özeti

Paranoid ML Investigator, makine öğrenmesi, derin öğrenme, tahminleme ve yapay zekâ projelerini bağımsız olarak incelemek üzere tasarlanan bir AI agent sistemidir.

Geleneksel kod inceleme araçları mevcut hataları ve bilinen yazılım problemlerini tespit etmeye odaklanır. Bu proje ise daha ileri bir soruyu araştırır:

**"Bu sistemin doğru çalıştığını düşünüyoruz. Peki hangi varsayımlar yanlışsa, hangi koşullarda veya hangi değişiklikler sonucunda başarısız olur?"**

Agent yalnızca hata raporlamaz. Hataların oluşma mekanizmalarını araştırır, gizli varsayımları sorgular, kontrollü deneyler tasarlar ve problemleri büyüterek modelin dayanıklılık sınırlarını belirlemeye çalışır.

Örneğin veri setindeki eksik gözlem oranı %5 ise bunun %10, %15 ve %25 olması halinde modelin nasıl davrandığını inceler.

Ayrıca bulunan problemlerin gelecekte neye dönüşebileceğini simüle eder. Yanlış tahminlerin stok kararlarına, maliyetlere ve sonraki dönemlere olan olası etkilerini hesaplar.

Sistemin temel yaklaşımı:

**Discover → Challenge → Amplify → Experiment → Verify → Predict Consequences → Repair → Retest**

Amaç mümkün olduğunca çok hata uydurmak değildir. Amaç, önemli zayıflıkları kanıtlarla ortaya çıkarmak ve sistemin güvenilirliğini artırmaktır.

# 2. Problem Tanımı

ML ve AI projelerinde başarısızlıklar yalnızca yanlış algoritma seçiminden kaynaklanmaz.

Yapısal hatalar, verilerin hazırlanması, hedef değişkenin tanımlanması, modelin eğitilmesi, performansın ölçülmesi ve sonuçların iş süreçlerine aktarılması sırasında oluşabilir.

Örneğin yüksek doğruluk gösteren bir model aşağıdaki sorunları barındırabilir:

- Gelecekteki bilgilerin yanlışlıkla eğitim verisine dahil edilmesi.
- Eksik, hatalı veya yanlı veriler.
- İş hedefiyle uyumsuz optimizasyon metrikleri.
- Modelin öğrenmesi gereken ilişki yerine tesadüfi korelasyonları öğrenmesi.
- Eğitim ve gerçek kullanım koşulları arasında farklılıklar.
- Eksik değerlendirme senaryoları.
- Küçük veri bozulmalarının büyük tahmin hatalarına dönüşmesi.
- LLM tabanlı bileşenlerde doğrulanmamış sonuçların kesin bilgi olarak sunulması.

Mevcut test yaklaşımlarının bir kısmı önceden tanımlanmış kontrol listelerine dayanır.

Paranoid ML Investigator'ın temel farkı, önceden yazılmamış hata hipotezlerini de geliştirmesi ve deneylerle sınamasıdır.

# 3. Agent'ın Çalışma Mantığı

Sistemin davranışı bilimsel bir araştırmacının yaklaşımına benzemelidir.

Önce mevcut projeyi anlamalı, ardından modelin başarısını açıklayan alternatif hipotezler üretmelidir.

Örneğin bir forecasting modelinin düşük hata oranı göstermesi, gerçekten başarılı olduğu anlamına gelmeyebilir.

Agent şu soruları araştırabilir:

"Model geçmiş verileri mi öğrendi, yoksa geleceğe ilişkin bilgileri yanlışlıkla kullandı mı?"

"Yüksek tahmin doğruluğu yalnızca belirli SKU'larda mı gerçekleşiyor?"

"Stok bulunmadığında gerçekleşen satışları gerçek talep olarak öğreniyor olabilir mi?"

"Modelin başarısı kampanya dönemlerinin yanlış kodlanmasına mı bağlı?"

Her hipotez için şu döngü izlenir:

1. Hipotezi açık biçimde tanımla.
2. Hipotezin yanlış olduğunu gösterebilecek bir karşıt test tasarla.
3. Testi izole ortamda çalıştır.
4. Başlangıç ve deney sonuçlarını karşılaştır.
5. Kanıt varsa bulguyu doğrula; yoksa şüpheli veya reddedilmiş olarak sınıflandır.
6. Doğrulanan problemin etkisini büyütme testine geçir.
7. Çözüm öner ve çözümün kendisini yeniden sorgula.

**Agent'ın şüpheci olması, bulgularının kesin doğru olduğu anlamına gelmez.**

Dolayısıyla agent'ın iddiaları ile Python üzerinden ölçülen deney sonuçları birbirinden ayrılmalıdır.

# 4. Sistem Mimarisi

Sistem üç ana katmandan oluşacaktır.

## Katman A — Intelligence Layer

Bu katman LLM destekli düşünme ve araştırma işlemlerini yürütür.

**Project Understanding Module**

Projenin kaynak kodlarını, klasör yapısını, veri dosyalarını, model eğitim süreçlerini, konfigürasyonlarını ve mevcut performans raporlarını inceler.

Amaç modelin hangi girdilerden hangi çıktıları ürettiğini anlamaktır.

**Skeptical Hypothesis Engine**

Projede bulunabilecek mantıksal boşlukları, gizli bağımlılıkları ve hata ihtimallerini araştırır.

Her şüphe için neden, beklenen etki ve doğrulama yöntemi üretir.

**Experimental Planner**

Hipotezi çalıştırılabilir bir teste dönüştürür.

Hangi parametrenin değiştirileceğini, hangi dosyaların kullanılacağını ve hangi başarısızlık kriterlerinin değerlendirileceğini tanımlar.

## Katman B — Experimental Harness

Bu katman LLM'in yalnızca yorum yaptığı değil, test sonuçlarının gerçek kodlarla üretildiği bölümdür.

**Structural Auditor**

Veri şemaları, formüller, kod bağımlılıkları, zaman sıralaması, hedef değişken tanımları ve değerlendirme yöntemlerindeki tutarsızlıkları araştırır.

**Fault Injection Engine**

Kontrollü biçimde veri eksiltir, geciktirir, bozar veya senaryo değişiklikleri uygular.

**Failure Amplification Engine**

Sorunun şiddetini 1×, 2×, 3× ve 5× seviyelerine taşıyarak modelin dayanıklılığını ölçer.

**Backtesting Engine**

Modelleri geçmiş dönemlerde, o tarihte gerçekten erişilebilir bilgilerle yeniden değerlendirir.

**Consequence Simulation Engine**

Tahmin hatalarının sonraki dönemlere ve iş süreçlerine nasıl yayılabileceğini simüle eder.

**Evidence Verification Engine**

Sonuçları yeniden hesaplar, kanıtları karşılaştırır ve doğrulanamayan bulguları ayırır.

## Katman C — Decision & Reporting Layer

**Root Cause Analyzer**

Bulgunun temel nedenini açıklar. Belirtiyle kök nedeni birbirinden ayırır.

**Solution Planner**

Düzeltme seçeneklerini, beklenen faydalarını ve olası yan etkilerini tanımlar.

**Counterfactual Tester**

Önerilen düzeltme uygulanmış olsaydı sonuçların nasıl değişeceğini aynı test koşullarında değerlendirir.

**Report Generator**

Deneylerin tamamını anlaşılır, kanıta dayalı bir rapora dönüştürür.

---

# 5. Failure Amplification Engine

Bu motor sistemin temel farklılaştırıcı özelliğidir.

## 5.1. Hata büyütme prensibi

Agent önce bir problemin başlangıç seviyesini ölçer.

Daha sonra problemi kontrollü biçimde artırır ve modelin verdiği tepkiyi ölçer.

Örnek:

Bir veri setinin %5'inde eksik stok bilgisi bulunmaktadır.

| Deney | Eksik veri | Problemin şiddeti |
|---|---:|---:|
| Baseline | %5 | 1× |
| Test A | %10 | 2× |
| Test B | %15 | 3× |
| Test C | %25 | 5× |

Önemli nokta: **Hata oranı otomatik olarak 2× veya 3× yapılmaz. Hatanın oluşmasına neden olan koşul büyütülür.**

Örneğin eksik veri 3× artarken tahmin hatası 1.4×, 2.8× veya 5× artabilir. Sistem bu ilişkiyi deneysel olarak keşfeder.

Temel ölçüm:

**Error Amplification Factor = Stress Test Error / Baseline Error**

Örneğin baseline WAPE %12 ve stres testi WAPE %30 ise:

**Error Amplification Factor = 2.5×**

Bu, modelin ilgili veri bozulmasına karşı hassasiyetini gösterir.

Test sonuçları gerçek verilerden üretilmediği sürece varsayımsal olarak işaretlenir.

## 5.2. Büyütülecek problem kategorileri

Her hata aynı şekilde büyütülemez. Bu nedenle Fault Injection Engine, problem türüne uygun strateji seçmelidir.

| Problem | Amplification yöntemi |
|---|---|
| Eksik veri | Eksik kayıt oranını artırma |
| Outlier | Aykırı değerlerin sayısını veya büyüklüğünü artırma |
| Data leakage | Gelecekten gelen bilginin kapsamını değiştirme |
| Feature dependency | Kritik değişkenleri sırayla kaldırma |
| Stockout | Kesinti süresi ve etkilenen ürün sayısını artırma |
| Data drift | Veri dağılımını kontrollü kaydırma |
| Model bias | Belirli alt grupların veri temsilini değiştirme |
| Formül hatası | Yanlış formülü farklı büyüklükte girdilerle test etme |
| LLM hallucination | Belirsiz, çelişkili veya eksik kanıtlı görev sayısını artırma |

Mümkün olduğunda testler gerçekçi sınırlar içinde yapılmalıdır.

Bir parametre 5× büyütülemiyorsa sistem fiziksel veya mantıksal sınırın aşıldığını belirtmelidir.

## 5.3. Failure Threshold Discovery

Bu özellik modelin hangi noktada güvenilmez hale geldiğini araştıracaktır.

Örneğin:

- Veri eksikliği hangi seviyede WAPE'yi kabul edilemez düzeye çıkarıyor?
- Kaç dönemlik stok kesintisinde model sistematik olarak eksik tahmin üretiyor?
- Hangi veri kayması seviyesinde tahmin aralıklarının kapsama oranı düşüyor?
- Hangi SKU'lar diğerlerinden önce başarısız oluyor?

Bu sonuçlardan bir dayanıklılık profili çıkarılacaktır.

**Hedef yalnızca hatayı göstermek değil, hatanın hangi koşullarda kritik hale geldiğini belirlemektir.**

# 6. Consequence Simulation Engine

Bu motor bir hata giderilmediğinde sonraki aşamalarda neler yaşanabileceğini analiz eder.

Örneğin demand forecasting modelindeki sistematik eksik tahmini ele alalım.

Olası süreç:

**Eksik demand forecast → Eksik sell-in planı → Yetersiz depo stoku → Stockout → Düşük gerçekleşen sell-out → Sonraki tahminlerde yeni sapma**

Bu döngü her koşulda gerçekleşmek zorunda değildir. Gerçekleşip gerçekleşmeyeceği stok politikası, sevkiyat süresi, talep, sipariş kararları ve diğer iş kurallarına bağlıdır.

Bu nedenle motor önce neden-sonuç varsayımlarını açıkça tanımlamalıdır.

Ardından üç farklı senaryo oluşturacaktır.

**Senaryo A — No Intervention**

Problem giderilmez ve mevcut sistemle devam edilir.

**Senaryo B — Amplified Failure**

Problem 2×, 3× veya daha yüksek şiddete ulaşır.

**Senaryo C — Corrected System**

Önerilen müdahale uygulanır ve aynı koşullar altında sonuçları yeniden simüle edilir.

İşletme verileri yeterliyse 3, 6 ve 12 aylık etkiler hesaplanabilir.

Örnek çıktılar:

- Beklenen stok fazlası.
- Stokout yaşayan dönem sayısı.
- Olası kayıp satış miktarı.
- Stok tutma maliyeti.
- Depolar arasında yanlış tahsis edilen miktarlar.
- SKU bazında forecast bias.
- Servis seviyesi üzerindeki etkiler.

Geleceğe ilişkin bu değerler kesin sonuç değil, varsayımlara bağlı senaryolardır.

Talep belirsizliği mevcutsa tek sonuç yerine farklı talep senaryoları veya Monte Carlo simülasyonlarıyla sonuç aralıkları oluşturulmalıdır.

# 7. Evidence & Hallucination Control

Sistemin en önemli güvenilirlik mekanizmasıdır.

Agent'ın problem ararken hayalî problemler üretmesini önlemek için bütün iddialar kanıt statüsüne sahip olacaktır.

| Statü | Anlamı |
|---|---|
| Verified | Gerçek kod, veri veya tekrar edilebilir deneyle doğrulandı |
| Suspected | Makul hipotez, yeterli kanıt yok |
| Simulated | Yalnızca kontrollü deney koşullarında gözlemlendi |
| Rejected | Yapılan deney hipotezi desteklemedi |
| Inconclusive | Test sonucu değerlendirme için yetersiz |

Her bulgu en az şu bilgileri içermelidir:

**Finding ID, problem açıklaması, kaynak dosya/satır, etkilenen veri, hipotez, test prosedürü, başlangıç ölçümü, deney ölçümü, kanıt dosyası, belirsizlik ve önerilen düzeltme.**

Ek olarak agent'ın kendi halüsinasyonlarını araştıran testler olacaktır.

Örnekler:

- Kaynak kodda bulunmayan bir fonksiyonun var olduğunu iddia etmesi.
- Çalıştırmadığı bir test için performans sonucu vermesi.
- Simülasyon sonucunu gerçek üretim verisi olarak sunması.
- Korelasyonu kanıtlanmış nedensellik olarak yorumlaması.
- Yanlış veya mevcut olmayan dosya satırlarına referans üretmesi.
- Düzeltme yapılmadan performansın iyileştiğini söylemesi.

**Raporlama kuralı:** Kanıt bulunmayan hiçbir iddia Verified statüsüne geçirilemez.

Önemli bulguların bağımsız bir hesaplama veya ikinci değerlendirme aşamasından geçmesi gerekir.

# 8. Teknik Mimari ve Teknoloji Seçimi

İlk sürüm yerel çalışan bir Python uygulaması olarak geliştirilmelidir.

Web arayüzü, bulut altyapısı veya çoklu agent organizasyonu başlangıç için zorunlu değildir.

| Bileşen | Önerilen teknoloji |
|---|---|
| Temel dil | Python |
| Agent orchestration | Başlangıçta Python state machine; ihtiyaçta LangGraph |
| LLM bağlantısı | Değiştirilebilir model adaptörü |
| Yerel LLM seçeneği | Ollama |
| Veri işleme | pandas, NumPy |
| Modelleme ve test | scikit-learn, statsmodels |
| Forecast backtesting | MLForecast veya özel rolling-origin testleri |
| Veri kalite kontrolleri | Great Expectations / Evidently |
| Otomatik test | pytest |
| Deney kayıtları | SQLite + JSON/Parquet |
| Rapor | Markdown + HTML |
| Versiyonlama | Git |

**Kendi harness'ımız temel sistem olacak; açık kaynak kütüphaneler yalnızca hesaplama ve kontrol araçları olarak kullanılacaktır.**

## 8.1. Önerilen repo yapısı

Proje adı: `paranoid-ml-investigator`

- `src/core/`: Orchestration, durum yönetimi, çalışma kuralları.
- `src/agents/`: Project analyzer, hypothesis investigator, solution planner.
- `src/auditors/`: Veri, kod, model ve evaluation denetimleri.
- `src/amplification/`: Fault injector, severity controller, threshold detector.
- `src/simulation/`: Consequence simulator, inventory simulator, scenario manager.
- `src/verification/`: Kanıt doğrulama, metrikler, tekrar deneyleri.
- `src/reporting/`: Rapor oluşturma, bulgu kayıtları.
- `src/adapters/`: LLM, model, veri ve forecasting framework bağlantıları.
- `config/`: Agent politikaları, hata seviyeleri, test bütçeleri.
- `tests/`: Unit, integration, adversarial ve hallucination testleri.
- `examples/`: Sentetik forecasting ve ML projeleri.
- `runs/`: Deney sonuçları, loglar ve raporlar.

Bu ayrım sayesinde agent'ın düşünme mekanizması ile hesaplama motorları birbirine sıkı biçimde bağlanmaz.

## 8.2. Harness çalışma kuralları

Harness şu güvenlik ve doğruluk kurallarını zorunlu olarak uygulamalıdır:

- Orijinal proje dosyaları başlangıçta salt okunur olmalı.
- Testler ayrı çalışma klasörlerinde yürütülmeli.
- Çalıştırılacak kod için izinli komut ve kaynak sınırları tanımlanmalı.
- Gerekirse ağ erişimi tamamen kapatılmalı.
- Bütün veri değişiklikleri kayıt altına alınmalı.
- Deneylerin random seed, model versiyonu ve parametreleri saklanmalı.
- Eğitim ve test dönemleri birbirine karıştırılmamalı.
- Gelecekte bilinmeyecek feature'lar test aşamasında kullanılmamalı.
- Agent model değişikliklerini üretim ortamına otomatik aktarmamalı.
- Belirlenmiş çalışma süresi, deney sayısı veya maliyet sınırına ulaşıldığında süreç durmalı.

# 9. Roadmap — Geliştirme Aşamaları

Roadmap sekiz aşamaya ayrılmıştır. İlk aşamalarda çalışan bir çekirdek sistem kurulacak, daha karmaşık yetenekler bunun üzerine eklenecektir.

| Aşama | Geliştirme | Somut çıktı |
|---|---|---|
| 1 | Sistem sözleşmesi ve repo altyapısı | Çalışan Python proje iskeleti |
| 2 | Project intelligence ve veri denetimi | Dosyaları analiz eden auditor |
| 3 | Hypothesis & evidence sistemi | Kanıta bağlanan hipotez kayıtları |
| 4 | Failure amplification | 1×, 2×, 3×, 5× stres testleri |
| 5 | Consequence simulation | Gelecek etki senaryoları |
| 6 | Solution & counterfactual | Müdahale öncesi/sonrası karşılaştırma |
| 7 | Agent hallucination & red teaming | Yanlış iddiaları yakalayan testler |
| 8 | Entegrasyon ve kalite kontrol | Kullanılabilir, tekrarlanabilir MVP |

## Aşama 1 — Foundation

Önce proje standartları tanımlanır.

Girdi türleri, desteklenen model aileleri, güvenlik sınırları, bulgu kayıt şeması ve çıktı formatları belirlenir.

Tek bir komutla örnek proje taranabilmelidir.

**Kabul kriteri:** Sistem dosyaları güvenle okuyabilmeli, proje envanterini çıkarabilmeli ve hiçbir orijinal dosyayı değiştirmemelidir.

## Aşama 2 — Structural Intelligence

Agent proje yapısını, veri akışını ve model eğitim mantığını analiz eder.

İlk sürümde Python dosyaları, CSV/Excel verileri, model konfigürasyonları ve performans çıktıları desteklenmelidir.

**Kabul kriteri:** Kullanılan target, feature'lar, veri dönemi, model ve değerlendirme yöntemi doğru tanımlanmalıdır.

## Aşama 3 — Hypothesis Engine

Agent şüphe üretir, fakat her hipotezin nasıl test edileceğini de açıklamak zorundadır.

İlk sürümde sınırlı sayıda, önceliklendirilmiş hipotez çalıştırılır.

**Kabul kriteri:** Şüpheli, doğrulanmış ve reddedilmiş hipotezler karışmamalıdır.

## Aşama 4 — Amplification MVP

Üç hata ailesiyle başlanmalıdır:

1. Missing data amplification.
2. Outlier / distribution shift amplification.
3. Forecast feature ve zamanlama bozulmaları.

Daha sonra stockout, leakage ve birleşik hata senaryoları eklenir.

**Kabul kriteri:** Aynı model üzerinde farklı şiddetteki deneyler otomatik çalıştırılabilmeli, hata değişimi doğru hesaplanmalı ve sonuçlar tekrar üretilebilmelidir.

## Aşama 5 — Consequence Engine

Önce forecasting alanına özel basit bir stok simülasyonu geliştirilir.

Forecast çıktısı, sipariş planı ve stok hareketleri arasındaki ilişki tanımlanır.

**Kabul kriteri:** Aynı varsayımlar altında müdahalesiz ve düzeltilmiş senaryolar karşılaştırılabilmelidir.

## Aşama 6 — Repair & Retest

Agent çözüm önerir ve önerilen düzeltme izole ortamda uygulanır.

Düzeltilmiş model orijinal modelle aynı zamansal değerlendirme koşullarında karşılaştırılır.

**Kabul kriteri:** Bir sorunun giderilmesi başka SKU, dönem veya performans metriğinde ciddi bozulma yaratıyorsa rapor bunu göstermelidir.

## Aşama 7 — Agent Red Team

Agent'a kasıtlı olarak eksik belgeler, yanıltıcı metrikler, sahte hata ipuçları ve bozuk dosya referansları verilir.

Amaç agent'ın kendisinin ne zaman güvenilmez hale geldiğini bulmaktır.

**Kabul kriteri:** Agent çalıştırmadığı deneyleri çalıştırılmış gibi sunmamalı; bilinmeyen veya doğrulanamayan bilgileri açıkça işaretlemelidir.

## Aşama 8 — Production Hardening

Son aşamada kod düzeni, izlenebilirlik, performans, hata yönetimi ve raporların anlaşılabilirliği değerlendirilir.

Büyük dosyalar, başarısız deneyler ve yarıda kesilen işlemler için toparlanma mekanizmaları eklenir.

**Kabul kriteri:** Kullanıcı aynı girdiyi ve aynı deney ayarlarını verdiğinde aynı sayısal test sonuçlarını elde edebilmelidir. LLM yorumları farklılaşabilse de kanıt kayıtları değişmemelidir.

# 10. İlk Pilot: Demand Forecasting

İlk gerçek uygulama alanı ürün ve ay bazlı demand forecasting projesi olmalıdır.

Örnek girdiler:

- Geçmiş dönem sell-out.
- Ürün/depo bazlı sell-in.
- Biliniyorsa stokout dönemleri.
- Stok ve kampanya bilgileri.
- Kullanılan model kodları.
- Geçmiş tahminler ve gerçekleşmeler.
- Mevcut performans raporları.

Agent önce mevcut modelin geçmiş dönemlerdeki doğruluğunu bağımsız olarak değerlendirir.

Ardından aşağıdaki soruları araştırır:

**A. Model gerçekten geleceği tahmin edebiliyor mu?**

Rolling-origin backtest uygulanır. Özellikle 1, 3, 6 ve 12 aylık tahmin ufukları birbirinden ayrılır.

**B. Satışla talep birbirine karıştırılmış mı?**

Stockout dönemlerinde gerçekleşen satışın gerçek talebi eksik gösterip göstermediği araştırılır. Gerçek talep doğrudan gözlenemiyorsa bu durum açıkça belirtilir.

**C. Sell-in ile sell-out ilişkisi doğru kurulmuş mu?**

Depo yüklemelerinin sonraki aylardaki satışlarla ilişkisi incelenir. Sell-in'in gerçekleşmiş tüketici talebi yerine yanlışlıkla kullanılma ihtimali test edilir.

**D. Model hangi koşullarda başarısız oluyor?**

Anomaliler, stok kesintileri, veri eksikleri ve yüksek hacim değişimleri artırılarak stres testleri uygulanır.

**E. Hatalar planlamaya nasıl yansıyor?**

Stok bulunurluğu, fazla stok, kayıp satış ve sonraki dönem tahminleri üzerindeki etkiler senaryo bazında hesaplanır.

İlk pilotun sonunda SKU ve ay seviyesinde aşağıdaki çıktılar oluşturulmalıdır:

- Baseline forecast.
- Baseline WAPE, MAE, Bias ve uygun diğer metrikler.
- En önemli doğrulanmış problemler.
- Amplification deneyleri ve hata duyarlılık eğrileri.
- Kritik başarısızlık eşikleri.
- Müdahalesiz ve düzeltilmiş senaryolar.
- Çözüm önerileri ve yeniden test sonuçları.

# 11. Başarı Kriterleri

Sistem yalnızca bulduğu sorun sayısıyla değerlendirilmemelidir.

Başarı beş ayrı boyutta ölçülmelidir.

**Detection Quality:** Bilerek oluşturulmuş sorunların ne kadarını bulabiliyor?

**False Positive Control:** Gerçekte bulunmayan problemleri ne sıklıkla doğrulanmış olarak bildiriyor?

**Evidence Reliability:** Her önemli bulgu gerçek test ve dosya kayıtlarıyla destekleniyor mu?

**Experiment Reproducibility:** Sayısal deneyler aynı koşullarda tekrar üretilebiliyor mu?

**Remediation Quality:** Önerilen düzeltmeler bağımsız değerlendirme verisinde gerçekten iyileşme sağlıyor mu?

Başlangıç benchmark'ı için bilinen hatalara sahip sentetik projeler hazırlanmalıdır.

Örneğin 20 kontrollü problem senaryosu oluşturulabilir. Bunların bir bölümü gerçek hata, bir bölümü yanıltıcı ama hatasız senaryo olmalıdır.

Agent'ın bunları ayırt etme başarısı ölçülür.

MVP kabul eşikleri ilk benchmark sonuçlarına göre kararlaştırılmalıdır; deney yapılmadan başarı oranı vaat edilmemelidir.

# 12. Riskler ve Kontroller

**Risk 1 — Aşırı şüphecilik**

Agent her yerde problem aradığı için yanlış bulgular oluşturabilir.

Kontrol: Kanıt statüleri, bağımsız doğrulama ve reddedilmiş hipotezlerin kayıt altına alınması.

**Risk 2 — Gerçekçi olmayan amplification**

5× bozulma gerçek hayatta mümkün olmayan bir senaryo oluşturabilir.

Kontrol: Her deneyin gerçekçilik seviyesi, varsayımları ve fiziksel sınırları raporlanır.

**Risk 3 — Test verisine aşırı uyum**

Agent çok sayıda düzeltme denerken test verisini dolaylı olarak optimizasyon için kullanabilir.

Kontrol: Geliştirme backtest'leri ile son bağımsız değerlendirme dönemi ayrılır. Nihai değerlendirme verisi önceden dondurulur.

**Risk 4 — Yanlış nedensellik**

Bir değişkenin artmasıyla forecast hatasının artması, her zaman gerçek hayattaki neden-sonuç ilişkisini kanıtlamaz.

Kontrol: Kontrollü müdahaleler, alternatif açıklamalar ve nedensel varsayımlar açıkça belgelenir.

**Risk 5 — Kontrolsüz agent davranışı**

Agent projeyi bozabilir, yanlış komut çalıştırabilir veya hassas verileri dışarı aktarabilir.

Kontrol: Yerel sandbox, izinli araçlar, salt okunur kaynaklar, ağ kısıtlamaları ve insan onayı.

# 13. Nihai Ürün Vizyonu

Proje tamamlandığında hedef, kullanıcının yalnızca bir ML/AI projesini seçerek denetim başlatabilmesidir.

Örnek kullanım:

**Kullanıcı:** "Bu forecasting projesini denetle. Hataları bul, 2× ve 3× stres testleri uygula ve 12 aylık stok planına olası etkilerini göster."

**Agent:** Projeyi tarar, hipotezleri önceliklendirir, deneyleri çalıştırır, bulguları doğrular ve sonuçları açıklanabilir bir rapora dönüştürür.

**Kullanıcı:** "En kritik iki sorunun çözümünü dene."

**Agent:** Çözümü ayrı bir ortamda uygular, model performansını yeniden ölçer, yan etkileri inceler ve karşılaştırmalı sonuç üretir.

Uzun vadede sistem şu alanlara genişletilebilir:

- Regression ve classification modelleri.
- Deep learning.
- Time-series forecasting.
- Optimizasyon algoritmaları.
- LLM tabanlı uygulamalar.
- RAG sistemleri.
- AI agent ve multi-agent mimarileri.

## Nihai Mimari Kararı

**Sıfırdan özel bir agent harness geliştirilecek, ancak istatistiksel test ve veri işleme kütüphaneleri yeniden yazılmayacaktır.**

İlk sürümde tek orchestrator agent, bağımsız Python modülleri, izole deney ortamı ve kanıt kayıt sistemi bulunacaktır.

Çoklu agent mimarisi, görsel arayüz ve daha karmaşık otomasyonlar ancak ilk çekirdek sistemin başarılı şekilde doğrulanmasından sonra eklenecektir.

Projenin merkezi ilkesi:

**Assume nothing. Challenge everything. Amplify weaknesses. Verify the evidence. Predict the consequences. Test every fix.**

*Hiçbir varsayımı sorgulamadan kabul etme. Zayıflıkları görünür hale getir. Kanıtları doğrula. Olası sonuçları hesapla. Her çözümü yeniden test et.*
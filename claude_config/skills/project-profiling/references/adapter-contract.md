# Adapter sözleşmesi

```python
class Adapter:
    sources: dict[str, str]          # {"load_data": "src/data.py:12", "split": "train.py:40", ...}
    target: str                      # onaylı profil target'ı ile aynı olmalı
    def load_data(self) -> pd.DataFrame          # tahmin birimi başına bir satır; target sütunu içinde
    def split(self, df) -> (train_index, test_index)   # index ETİKETLERİ, ayrık, projenin protokolü
    def fit(self, train_df, seed=0) -> model     # seed=0 == projenin kendi ayarı
    def predict(self, model, df) -> 1-D array
    def predict_proba(self, model, df) -> 1-D array   # opsiyonel, sınıflandırma pozitif sınıf olasılığı
```

`pmi adapter validate` şunları kontrol eder: target var mı, `load_data` bir DataFrame döndürüyor mu, index unique mi, split ayrık ve boş değil mi, predict uzunluğu doğru mu, tahminler sonlu mu. Ayrıca `sources` alanında `TODO` kalıp kalmadığına bakar.

## Desenler

**Projede fonksiyonlar varsa onları import et** (`TARGET_ROOT` zaten `sys.path` içinde):
```python
from src.features import build_features      # kopyadaki proje modülü
def load_data(self):
    raw = pd.read_csv(TARGET_ROOT / "data/raw.csv")
    return build_features(raw)
```

**Proje tek script ise** ilgili satırları adapter'a taşı ve satır numaralarını `sources` alanına yaz.

**Rolling-origin / backtest protokolü:** Sözleşme şu an tek bir train/test ayrımı bekliyor. Projede birden çok fold varsa, raporlanan metriğin hesaplandığı fold'u seç ve bunu `sources["split"]` alanına not et. Çoklu fold desteği Aşama 5+ işidir.

**Projenin preprocessing'i tüm veriye fit ediliyorsa** (ör. scaler fit, ardından split): `fit()` yalnızca train görür. Birebir taklit gerekiyorsa `load_data` içinde aynı global dönüşümü uygula ve bunu `sources` alanında açıkça belirt. Bu durum muhtemelen bir hipotezdir (`preprocessing_fit_before_split`).

## Surrogate config
```json
{"data_source": "data/table.csv", "target": "y", "features": ["a","b"],
 "task_type": "regression",
 "split": {"kind": "temporal", "time_column": "date", "test_fraction": 0.2}}
```
HistGradientBoosting NaN değerleri kendi içinde işler. Bu yüzden surrogate ile yapılan missing-data testleri projenin modeli hakkında neredeyse hiçbir şey söylemez.

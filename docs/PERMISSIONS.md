# İzin ve güvenlik modeli

Agent'a güvenmek yerine, agent'ın **yapamayacaklarını** katmanlı biçimde tanımlıyoruz. Her katman bir öncekinin kaçırdığını yakalar.

| Katman | Nerede | Ne yapar | Sınırı |
|---|---|---|---|
| 1. Claude Code permissions | `.claude/settings.json` | allow / ask / deny listeleri | Bash'te dolaylı komutları yakalayamaz |
| 2. Guard hook | `.claude/hooks/guard.py` (PreToolUse) | Orijinal projeye, workspace kopyasına, kanıt dosyalarına ve harness'a yazmayı engeller, cevap anahtarı okumayı engeller | Sezgiseldir; dolaylı bir Bash yazımı geçebilir |
| 3. Harness kuralları | `src/pmi` + `config/policy.yaml` | Statü yalnızca `pmi verify` ile değişir. Ön-kayıt zorunludur. Profil onayı gerekir. Bütçe, timeout ve replicate sınırları vardır. | — |
| 4. Bütünlük (backstop) | `pmi integrity` | Orijinal proje ve workspace kopyası sha256 snapshot ile karşılaştırılır. Ledger hash zinciri ve artifact hash'leri kontrol edilir. | Yazmayı engellemez, **tespit eder** |
| 5. İnsan kapıları | `ask` kuralları | init, profile set, adapter validate/confirm, budget extend, keyfi `python`, `git` | — |

## Agent'ın yazabildiği yerler
- `runs/<id>/workspace/pmi_adapter.py` (çalıştırılabilir olan tek dosya)
- `runs/<id>/workspace/scratch/**`
- `runs/<id>/notes/**`

## Asla yazamadığı yerler
- İncelenen orijinal proje (yolu `runs/*/manifest.json` dosyasından okunur)
- `runs/<id>/workspace/target/**` (baseline kopyası)
- `ledger.sqlite`, `manifest.json`, `snapshot.json`, `profile.json`, `adapter.json`, `budget.json`, `report.md`, `artifacts/**`, `scan/**`
- Harness: `src/`, `config/`, `.claude/`, `claude_config/`, `setup_claude_config.py`, `tests/`, `CLAUDE.md`, `pyproject.toml`. Bu kural `PMI_DEV_MODE=1` ile kalkar.

## İnsan kapıları
| Komut | Neden |
|---|---|
| `pmi init` | Hangi projenin denetleneceği insanın kararıdır |
| `pmi use` | Aktif run'ı değiştirmek |
| `pmi profile set` | Projeyle ilgili gerçekler agent tahminiyle değil, insan onayıyla kesinleşir |
| `pmi adapter validate` | Proje kodu ilk kez çalışır |
| `pmi adapter confirm` | Adapter'ın projeyi doğru taklit ettiği, sadece raporlanan metrik yoksa insan beyanıyla kabul edilir |
| `pmi budget extend` | Maliyet ve süre sınırı |
| `python ...`, `git ...` | Keyfi kod çalıştırma ve repo değişikliği |

## Proje kodunun çalıştırılması
Proje kodu yalnızca `python -m pmi.engine.worker` alt sürecinde, `cwd = workspace` ile çalışır:
- **Ağ:** `execution.network: blocked` ise socket katmanı yamalanır (connect, create_connection, getaddrinfo). Bu bir **OS sandbox'ı değildir**. Native uzantılar veya proje kodunun açtığı alt süreçler bu engeli aşabilir. Güvenilmeyen bir proje için worker'ı ayrıca ağsız bir container/VM içinde çalıştırın.
- **Zaman:** `timeout_seconds_per_experiment`
- **Ortam:** HTTP(S)_PROXY değişkenleri temizlenir.

## Harness geliştirme
Harness'ı geliştirmek için oturumu şöyle başlatın:
```bash
PMI_DEV_MODE=1 claude          # Git Bash / Linux / macOS
$env:PMI_DEV_MODE=1; claude     # PowerShell
```
Bu modda bile orijinal projeler ve kanıt dosyaları korunur.

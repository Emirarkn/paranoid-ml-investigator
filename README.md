# Paranoid ML Investigator

ML/AI projelerini bağımsız denetleyen, şüpheci bir agent ve onun deterministik harness'ı.

- **Agent (Katman A):** Claude Code. Karakteri `CLAUDE.md`, yöntemleri `.claude/skills/` ve rolleri `.claude/agents/` altında tanımlı.
- **Harness (Katman B/C):** `pmi` Python paketi. Ölçer, kaydeder ve kanıt statüsünü belirler. Agent statü atayamaz.

> Assume nothing. Challenge everything. Amplify weaknesses. Verify the evidence.

## Kurulum (Windows / PowerShell)
```powershell
git clone https://github.com/Emirarkn/paranoid-ml-investigator.git
cd paranoid-ml-investigator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,excel]"
python setup_claude_config.py   # claude_config/ -> .claude/ (subagent, skill, hook, permission)
python -m pytest -q             # 27 test geçmeli
```
Claude Code'u bu klasörde, venv aktifken başlatın (`claude`). Bu sayede `pmi` komutu ve hook'lardaki `python` aynı ortamı kullanır.

> `claude_config/` agent konfigürasyonunun kaynağıdır. Claude Code ise bu dosyaları `.claude/` altından okur. `claude_config/` içinde bir şeyi değiştirdiğinizde `python setup_claude_config.py --force` ile `.claude/` klasörünü güncelleyin.

## Kullanım
Claude Code içinde:
```
Şu projeyi denetle: C:\...\benim_projem. Hataları bul, kritik girdiler için 2× ve 3× stres testi uygula.
```
Agent sırasıyla şunları yapar: `pmi init` (onay ister) → `pmi scan` → profil onay paketi (onay ister) → adapter → `pmi adapter validate` (onay ister) → `pmi baseline` → hipotezler → ön-kayıtlı deneyler → `pmi verify` → `pmi report` + `notes/findings.md` → `pmi check-claims`.

Elle deneme:
```powershell
python examples\make_examples.py C:\temp\pmi_examples
pmi init --target C:\temp\pmi_examples\retail_weekly
pmi scan
pmi profile show
```

## Uzmanlık: OTC kanal paketi
Çekirdek her ML/AI projesinde çalışır. **OTC (reçetesiz ürün) / consumer health kanalı** için ek bir domain paketi gelir: `claude_config/skills/domain-otc-channel/` ve `domain_packs/otc_channel/`.
- Üretici → depo → eczane → tüketici zinciri; sell-in, sell-out, stok kesintisi, kanal stoku, kampanya ve panel gecikmesi
- 9 kanala özgü hata ailesi (vekil hedef, sansürlü talep, kanal yüklemesi, gecikmeli bilgi…) ve bunların pmi ile test yolları
- Sentetik benchmark projesi (`examples/make_examples.py` → `otc_channel`)
- Aşama 5 tasarımı: kanal sonuç simülasyonu (stok, kesinti, kayıp satış, servis seviyesi)

Paket yalnızca profil onaylandıktan sonra ve insan teyidiyle devreye girer. Bkz. `domain_packs/README.md`.

**Gizlilik:** Repoda gerçek veri yoktur. Tüm örnek veriler kodla üretilen sentetik verilerdir. Denetlenen projeler `runs/` altına kopyalanır ve bu klasör git'e girmez (`.gitignore`).

## Dosya haritası
| Yol | İçerik |
|---|---|
| `CLAUDE.md` | Agent anayasası: karakter, mutlak kurallar, döngü, insan kapıları |
| `claude_config/settings.json` → `.claude/` | Permission listesi (allow/ask/deny) ve hook tanımları |
| `claude_config/hooks/` | `guard.py` (yazma koruması), `session_start.py` (kaldığı yerden devam) |
| `claude_config/agents/` | 5 subagent: cartographer, skeptic, designer, verifier, claim-auditor |
| `claude_config/skills/` | 8 skill: investigate, project-profiling, skeptical-hypotheses, experiment-design, failure-amplification, leakage-hunting, evidence-protocol, audit-reporting |
| `setup_claude_config.py` | `claude_config/` → `.claude/` kurulumu |
| `config/` | `policy.yaml` (bütçe, ağ, timeout, kanıt eşikleri), `amplification.yaml` |
| `src/pmi/` | Harness |
| `tests/` | Aşama 1–4 kabul testleri |
| `examples/` | Gizli cevap anahtarlı sentetik benchmark üreticisi (retail, churn, OTC kanal) |
| `domain_packs/` | Sektör paketleri (`otc_channel`) |
| `docs/` | Tasarım dokümanı, mimari eşleme, izin modeli, roadmap |
| `runs/` | Her denetim (git'e girmez) |

## Komutlar
`pmi --help` · `pmi checks` · `pmi injectors` · `pmi status` · `pmi integrity`

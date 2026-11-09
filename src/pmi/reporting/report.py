"""Report Generator — built ONLY from the ledger, profile and artifacts.

No number in this report comes from the LLM. The agent's own interpretation lives in
runs/<id>/notes/*.md and must pass `pmi check-claims`.
"""
from __future__ import annotations

import json
from typing import Any

from pmi.core.run import Run
from pmi.evidence.ledger import Ledger
from pmi.profiling.profile import load_profile

STATUS_ORDER = ["Verified", "Simulated", "Suspected", "Inconclusive", "Rejected"]
STATUS_TR = {"Verified": "Doğrulandı — gerçek kod/veri + tekrar edilebilir test",
             "Simulated": "Simüle — yalnızca kontrollü deney koşullarında gözlendi",
             "Suspected": "Şüpheli — makul hipotez, henüz test edilmedi",
             "Inconclusive": "Belirsiz — test sonucu karar için yetersiz",
             "Rejected": "Reddedildi — deney hipotezi desteklemedi"}


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _exp_block(run: Run, e: dict[str, Any]) -> list[str]:
    L = [f"- **{e['id']}** `{e['type']}` — durum: {e['state']}, adapter: {e.get('adapter_kind') or '—'} "
         f"(fidelity: {e.get('adapter_fidelity') or '—'})"]
    L.append(f"  - Ön-kayıtlı karar kuralı: `{json.dumps(e['decision_rule'], ensure_ascii=False)}`")
    L.append(f"  - Spec: `{json.dumps(e['spec'], ensure_ascii=False)}`")
    if e["state"] == "failed":
        L.append(f"  - Hata: `{e['error']}`")
        return L
    r = e["result"] or {}
    if e["type"] == "check":
        L.append(f"  - Sonuç: defect_found={r.get('defect_found')} — {r.get('summary', '')}")
        refs = r.get("refs") or []
        if refs:
            L.append(f"  - Referanslar: {', '.join('`' + x + '`' for x in refs[:12])}")
    elif e["type"] == "baseline":
        mets = r.get("metrics", {})
        L.append("  - Baseline: " + ", ".join(f"{k}={_fmt(v.get('mean'))} [{_fmt(v.get('min'))}, {_fmt(v.get('max'))}]"
                                            for k, v in mets.items()))
        L.append(f"  - Yeniden üretim: `{json.dumps(r.get('reproduction'), ensure_ascii=False)}`")
    elif e["type"] == "amplify":
        prim = r.get("primary_metric")
        L.append(f"  - Injector `{r.get('injector')}` @ `{r.get('where')}` sütunlar {r.get('columns')}; "
                 f"base condition={_fmt(r.get('base_condition'))}; {r.get('ladder')}")
        L.append(f"  - Baseline seed-gürültüsü (rel. std): {_fmt(r.get('baseline_noise_rel_std'))}")
        L.append("")
        L.append(f"  | Seviye | Koşul (hedef) | Koşul (gerçekleşen) | {prim} ort. [min,max] | EAF ort. [min,max] | Hata | Limit |")
        L.append("  |---|---|---|---|---|---|---|")
        for row in r.get("levels", []):
            m, ea = row.get(prim) or {}, row.get(f"eaf_{prim}") or {}
            L.append(f"  | {row['label']} | {_fmt(row.get('condition'))} | {_fmt(row.get('condition_realized_mean'))} | "
                     f"{_fmt(m.get('mean'))} [{_fmt(m.get('min'))}, {_fmt(m.get('max'))}] | "
                     f"{_fmt(ea.get('mean'))} [{_fmt(ea.get('min'))}, {_fmt(ea.get('max'))}] | "
                     f"{row.get('failures', 0)}/{row.get('replicates', 0)} | {'AŞILDI' if row.get('limit_exceeded') else ''} |")
        L.append("")
        L.append(f"  - Eşik keşfi: `{json.dumps(r.get('threshold'), ensure_ascii=False)}`")
    elif e["type"] == "ablation":
        prim = r.get("primary_metric")
        L.append(f"  - Ablation `{r.get('mode')}` @ `{r.get('where')}`")
        L.append(f"  | Adım | {prim} | EAF ort. [min,max] | Hata |")
        L.append("  |---|---|---|---|")
        for row in r.get("steps", []):
            ea = row.get(f"eaf_{prim}") or {}
            L.append(f"  | {row['step']} | {_fmt((row.get(prim) or {}).get('mean'))} | "
                     f"{_fmt(ea.get('mean'))} [{_fmt(ea.get('min'))}, {_fmt(ea.get('max'))}] | {row.get('failures', 0)} |")
    arts = e.get("artifacts") or []
    if arts:
        L.append("  - Kanıt dosyaları: " + ", ".join(f"`artifacts/{e['id']}/{a['path']}` (sha256 {a['sha256'][:12]}…)"
                                                for a in arts))
    return L


def build_report(run: Run, ledger: Ledger) -> str:
    m = run.manifest
    prof = load_profile(run.profile_path)
    integ = run.integrity()
    chain = ledger.verify_chain()
    hyps = ledger.list_hypotheses()
    budget = run.budget_state(ledger.count_experiments())
    L: list[str] = [f"# Paranoid ML Investigator — Denetim Raporu", "",
                    f"- Run: `{run.id}`  •  Hedef: `{m['target_path']}`  •  Oluşturma: {m['created_at']}",
                    f"- pmi {m['pmi_version']}  •  Python {m['python']}  •  Paketler: {m['packages']}",
                    f"- Hedef bütünlüğü (orijinal dosyalara dokunulmadı mı?): **{'OK' if integ['ok'] else 'BOZULDU'}**"
                    + ("" if integ["ok"] else f" — `{json.dumps(integ, ensure_ascii=False)[:400]}`"),
                    f"- Kanıt defteri hash zinciri: **{'OK' if chain['ok'] else 'BOZULDU'}**"
                    + ("" if chain["ok"] else f" — {chain['problems'][:5]}"),
                    f"- Adapter: {run.adapter_meta.get('kind', 'yok')} / fidelity **{run.adapter_fidelity()}**",
                    f"- Bütçe: {budget['experiments_used']}/{budget['experiments_max']} deney, "
                    f"{budget['minutes_used']}/{budget['minutes_max']} dk", "",
                    "> Bu rapor yalnızca kanıt defterinden üretilmiştir. Rakamların tamamı Python deneylerinden gelir; "
                    "LLM yorumları `notes/` altındadır ve ayrı denetlenir. Simüle sonuçlar varsayımsal stres "
                    "senaryolarıdır, gerçek üretim verisi değildir. Korelasyon nedensellik kanıtı değildir.", ""]

    L += ["## 1. Öğrenilen proje profili", "", "| Alan | Durum | Değer | Kanıt |", "|---|---|---|---|"]
    for k, f in prof["fields"].items():
        val = f["value"] if f["status"] == "confirmed" else (f["candidates"][0]["value"] if f.get("candidates") else None)
        ev = f["evidence"] if f["status"] == "confirmed" else (f["candidates"][0]["evidence"] if f.get("candidates") else "")
        tag = {"confirmed": "onaylı", "proposed": "aday (onaysız)", "unknown": "bilinmiyor"}[f["status"]]
        L.append(f"| {k} | {tag} | `{_fmt(val)}` | {str(ev or '')[:120]} |")
    unknown = [k for k, f in prof["fields"].items() if f["status"] != "confirmed"]
    if unknown:
        L += ["", f"Onaysız alanlar ({', '.join(unknown)}) gerektiren analizler **çalıştırılmadı**."]

    counts = {s: sum(h["status"] == s for h in hyps) for s in STATUS_ORDER}
    L += ["", "## 2. Özet", "", "| Statü | Anlamı | Adet |", "|---|---|---|"]
    L += [f"| {s} | {STATUS_TR[s]} | {counts[s]} |" for s in STATUS_ORDER]

    L += ["", "## 3. Bulgular", ""]
    for s in STATUS_ORDER:
        group = sorted([h for h in hyps if h["status"] == s], key=lambda h: (h["priority"], h["id"]))
        if not group:
            continue
        L += [f"### {s}", ""]
        for h in group:
            exps = ledger.list_experiments(h["id"])
            L += [f"#### {h['id']} — {h['title']}  `[{h['status']}]`", "",
                  f"- **Problem / iddia:** {h['statement']}",
                  f"- **Mekanizma (hipotez):** {h['mechanism']}",
                  f"- **Beklenen etki:** {h['expected_effect']}",
                  f"- **Yanlışlama testi:** {h['falsification_test']}",
                  f"- **Tür / öncelik:** {h['kind']} / P{h['priority']}",
                  f"- **Kaynak dosya/satır:** {', '.join('`' + r + '`' for r in h['refs']) or '—'}",
                  f"- **Etkilenen veri:** {h['affected_data'] or '—'}",
                  f"- **Statü gerekçesi (pmi verify):** {h['status_reason']}",
                  f"- **Önerilen düzeltme (öneri — test edilmedi):** {h['proposed_fix'] or '—'}",
                  "- **Deneyler:**"]
            if not exps:
                L.append("  - (henüz deney yok)")
            for e in exps:
                L += ["  " + x if not x.startswith("  ") else x for x in _exp_block(run, e)]
            L.append("")
    L += ["## 4. Sınırlar ve belirsizlik", "",
          "- Amplification sonuçları, koşul kontrollü biçimde büyütüldüğünde modelin tepkisini ölçer; gerçek "
          "dünyada bu seviyelerin oluşma olasılığını söylemez. `AŞILDI` işaretli seviyeler fiziksel/mantıksal sınırda "
          "kırpılmıştır.",
          "- `A1/A2/A3` etiketli seviyeler mutlak merdivendir (taban koşul 0); 'N kat' olarak yorumlanamaz.",
          "- Adapter fidelity 'confirmed' değilse, adapter üzerinden yapılan deneyler en fazla Inconclusive olabilir.",
          "- Ağ engeli (network guard) işletim sistemi seviyesinde bir sandbox değildir; bkz. docs/PERMISSIONS.md.", ""]
    return "\n".join(L)

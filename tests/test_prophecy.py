"""Prophecy layer: check-claims lets exaggerated consequences through but still blocks changed facts."""
from __future__ import annotations

from tests.test_evidence import _hyp, _setup_retail

GOOD = """# Kehanetler — retail (koşu test)
> Bu dosya spekülatiftir.

## Kehanet 1: Sızıntı bütün planı yutar
> Gelecek haftanın satışı bugünün sütununda,
> model kâhin sanılır, depo boş kalır.

Dayanak: {hid} [Suspected]
Zincir: sızıntı → şişkin skor → yanlış sipariş → boş raflar → kaybedilen müşteriler
En kötü sonuç: Bütün mağaza ağı aynı hafta stoksuz kalır ve yaklaşık 250 bin birim satış uçar gider; bu düzeltilmezse daha da kötüleşir.
Varsayım: haftalık talep 250 bin birim, model üretimde sızıntısız çalışır
Erken uyarı: üretimdeki ilk dört haftanın hatası testtekinin iki katını aşarsa
Çürütme: sızıntılı özellik çıkarılınca hata değişmezse bu kehanet boşa çıkar

## Kehanet 2: Kimsenin bakmadığı yer
Dayanak: DAYANAKSIZ
Zincir: mağaza kodları yeniden numaralanır → eşleme kırılır → sessiz çöküş
En kötü sonuç: Model yanlış mağazalara stok yollar.
Erken uyarı: yeni mağaza kodu görüldüğünde
Çürütme: mağaza kodları değişmezse
"""


def _write(run_dir, name, text):
    p = run_dir / "notes" / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def _issues(pmi, path, *extra):
    rc, out = pmi("check-claims", path, *extra)
    return rc, " | ".join(i["issue"] for i in out["issues"])


def test_prophecy_passes_with_drama(harness, projects, pmi):
    run_dir = _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    path = _write(run_dir, "prophecies.md", GOOD.format(hid=hid))
    rc, issues = _issues(pmi, path)
    assert rc == 0, issues
    # the same text under findings rules is rejected (improvement word without an E-id)
    rc, issues = _issues(pmi, path, "--mode", "findings")
    assert rc == 1 and "improvement claim" in issues


def test_prophecy_blocks_changed_facts(harness, projects, pmi):
    run_dir = _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    pmi("experiment", "plan", "--hypothesis", hid, "--type", "check",
        "--spec", '{"check":"target_proxy","data_via":"profile"}', "--rule", '{"type":"defect_found"}')
    pmi("experiment", "run", "E-001")
    bad = GOOD.format(hid=hid)
    cases = {
        "status": (bad.replace(f"{hid} [Suspected]", f"{hid} [Verified]"), "tagged [Verified]"),
        "verify_word": (bad.replace("Bütün mağaza ağı", "Sızıntı doğrulandı ve bütün mağaza ağı"), "cannot claim verification"),
        "no_basis": (bad.replace(f"Dayanak: {hid} [Suspected]\n", ""), "without a 'Dayanak:' line"),
        "bad_basis": (bad.replace(f"Dayanak: {hid} [Suspected]", "Dayanak: önsezi"), "must cite a known H-id"),
        "unknown_id": (bad.replace(f"Dayanak: {hid} [Suspected]", "Dayanak: H-999"), "unknown id H-999"),
        "no_falsifier": (bad.replace("Çürütme: mağaza kodları değişmezse\n", ""), "without a 'Çürütme:' line"),
        "no_assumption": (bad.replace("Varsayım: haftalık talep 250 bin birim, model üretimde sızıntısız çalışır\n", ""),
                          "speculative number 250"),
        "wrong_number": (bad.replace("Model yanlış mağazalara stok yollar.",
                                     "E-001 korelasyonu 0.4321 bulmuştu."), "number 0.4321 not found"),
        "empty": ("# Kehanetler\nHiç kehanet yok.\n", "no '## Kehanet' block"),
    }
    for name, (text, expected) in cases.items():
        rc, issues = _issues(pmi, _write(run_dir, "prophecies.md", text))
        assert rc == 1 and expected in issues, (name, issues)


def test_findings_rules_unchanged(harness, projects, pmi):
    """A findings file is still held to calibrated wording, whatever it says about prophecies."""
    run_dir = _setup_retail(harness, projects, pmi)
    hid = _hyp(pmi)
    rc, issues = _issues(pmi, _write(run_dir, "findings.md", f"{hid} is verified. The model improved.\n"))
    assert rc == 1 and "described as verified" in issues and "improvement claim" in issues

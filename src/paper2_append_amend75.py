#!/usr/bin/env python3
"""
paper2_append_amend75.py  —  record 75 del ledger
Tipo: protocol — documentazione, nessuna misura nuova modifica valori congelati.

Contenuto:
  A. 6.0b chiusa: provenienza di +3.90/+0.20 (Tab. 12 riga 1, Paper 1)
     verificata su results/paper1/rev_n4n5_report.json.
  B. P1-2, documentazione corretta: i numeri +2.8175/0.4581/z=-7.108/3/2000
     sono l'unione step6 (idx 0-199) + n1b (idx 200-1999), validata con
     paper2_valida_unione_p1_2.py (G1/G2/G3 tutti PASSATI).
     Il testo del manoscritto (+2.82 ± 0.46) è invariato.
  C. Falsa premessa corretta: +3.90/+0.20 non sono due emisferi ma
     mock_mean e desi della stessa cella nello stesso report NGC.
  D. Due percorsi nuovi entrano nella popolazione citata dal ledger:
     results/paper1/rev_n4n5_report.json e src/paper1_rev_n4n5.py.

Ancore:
  ledger atteso  : 0e6dccc392ec934d09729e80bfef43cdc283aede60da2151d7a2023b79a08518
  ledger righe   : 74
  reference_sha  : 865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc
  file_sha256    : 332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d
  script         : cafabd43d2ee8fe00583dabb279981caf3aa2ce380c689f4d00b238d2326bdb8  (9071 byte)
  log            : de72023d02adb3592f406b3f996cbfe02fe9d69a3b3b9ec33b08a3b060bc3fe6 (2913 byte)

Uso:
  python src\\paper2_append_amend75.py selftest
  python src\\paper2_append_amend75.py dry-run
  python src\\paper2_append_amend75.py apply
  python src\\paper2_append_amend75.py verify
"""

import hashlib, json, sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "src" / "paper2_v1_amendments.jsonl"

# ── ancore ────────────────────────────────────────────────────────────────
LEDGER_SHA_ATTESO  = "0e6dccc392ec934d09729e80bfef43cdc283aede60da2151d7a2023b79a08518"
LEDGER_RIGHE_ATTESE = 74
REF_SELF_SHA       = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"
REF_FILE_SHA       = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
SCRIPT_SHA         = "cafabd43d2ee8fe00583dabb279981caf3aa2ce380c689f4d00b238d2326bdb8"
LOG_SHA            = "de72023d02adb3592f406b3f996cbfe02fe9d69a3b3b9ec33b08a3b060bc3fe6"

# ── record ────────────────────────────────────────────────────────────────
RECORD = {
    "type": "protocol",
    "utc": "2026-09-18T00:00:00+00:00",
    "item": "6.0b / P1-2_documentazione",
    "key": "provenienza_riga1_tab12_e_documentazione_P1-2_corretta",
    "document": "papers/paper2/modifiche_paper1.md (P1-2) · checklist_paper2.md (6.0b)",
    "reference_file": "src/paper2_v1_reference.json",
    "reference_file_sha256": REF_FILE_SHA,
    "reference_self_sha256": REF_SELF_SHA,
    "numbering_rule": "The number of an amendment is its 1-based POSITION in this file. This is record 75.",
    "old_value": {
        "6.0b_stato": "aperta — checklist rev. 3.31 dichiarava la provenienza non verificata su file",
        "P1-2_documentazione": {
            "mock_mean": 2.8175,
            "mock_sd": 0.4581,
            "z": -7.108,
            "rango": "3/2000",
            "n": "non dichiarato (scritto '2000' ma senza fonte)",
            "nota": "i valori non si riproducono da nessun singolo registro"
        },
        "premessa_falsa": (
            "+3.90 e +0.20 descritti come 'in emisferi diversi, quindi non sullo stesso record'; "
            "questa premessa rendeva impossibile la ricerca per valore con lo strumento esistente"
        )
    },
    "new_value": {
        "A_provenienza_riga1_tab12": {
            "file": "results/paper1/rev_n4n5_report.json",
            "sha256": "d0e8284b499be1a3bc93eee2372b94f44b407972c07065a569cbd429f61e7cd6",
            "byte": 5902,
            "campo": "momenti.P10.agg.kurt",
            "produttore": "src/paper1_rev_n4n5.py",
            "produttore_sha256": "029e32fe929f7e7802a721d2b3168ea173d4afb6baeac017e6e1d44050cdeb9f",
            "valori": {
                "mock_mean": 3.902956198001257,
                "mock_sd": 0.5983209563067237,
                "desi": 0.20448735601308332,
                "z": -6.181412840388943,
                "n_mock": 200,
                "pubblicati_Tab12": "+3.90 (mock) / +0.20 (DESI)"
            },
            "restrizione": "field_r > P10 di paper1_rev_n4n5.py (non inside mask)",
            "difetto_noto": "P10 calcolato su field_r > 0 (320342 voxel), non dentro maschera congelata (307805); corretto da paper1_rev_n4b_clean.py"
        },
        "B_validazione_unione_P1-2": {
            "fonte": "step6 (idx 0-199, n=200) + n1b (idx 200-1999, n=1800)",
            "step6_misure": {
                "source_file": "results/paper1/paper1_step6_NGC.json",
                "campo": "onepoint.restrictions.footprint pieno.nu.kurt_excess",
                "mock_mean": 2.76384938163661,
                "mock_std": 0.47179461207878376,
                "n": 200,
                "rank": "0/200"
            },
            "n1b_misure": {
                "source_file": "results/paper1/n1b_spectra_NGC.jsonl",
                "campo": "kurt_in_mask",
                "mock_mean": 2.82347840309143,
                "mock_std": 0.456249550694065,
                "n": 1800,
                "idx_range": "200-1999",
                "rank": "3/1800"
            },
            "unione": {
                "N": 2000,
                "media": 2.817515500945948,
                "sd": 0.45805659005182564,
                "z": -7.107703143478438,
                "rango": "3/2000",
                "desi": -0.43821476405642734
            },
            "scarti_vs_pubblicato": {
                "media": 1.55e-05,
                "sd": 4.34e-05,
                "z": 2.97e-04,
                "nota": "tutti sotto mezza unita dell'ultima cifra quotata"
            },
            "gate_G1": {
                "status": "PASSATO",
                "desc": "disgiunzione strutturale: {0..199} inter {200..1999} = vuoto"
            },
            "gate_G2": {
                "status": "PASSATO",
                "desc": "spectral_summary riproduce n1b_spectra_NGC.jsonl su 5 campioni",
                "scarto_massimo": "3.08e-07",
                "tolleranza": "5e-07"
            },
            "gate_G3": {
                "status": "PASSATO",
                "desc": "i due stimatori (step6 moments(), n1b spectral_summary) sono aritmeticamente identici: diff = 0.0"
            },
            "strumento_validazione": {
                "script": "src/paper2_valida_unione_p1_2.py",
                "sha256": SCRIPT_SHA,
                "byte": 9071,
                "commit": "01543c6",
                "log_sha256": LOG_SHA
            },
            "conclusione": "VALIDATA"
        },
        "C_premessa_corretta": {
            "errata": "+3.90 e +0.20 descritti come valori in emisferi diversi",
            "corretta": (
                "+3.90 e +0.20 sono mock_mean e desi della stessa cella "
                "(momenti.P10.agg.kurt) nello stesso file NGC. "
                "La Tab. 12 del Paper 1 ha una sola colonna DESI e una sola colonna mocks, "
                "con didascalia '(NGC)'. Le coppie sono mock/DESI, non NGC/SGC."
            )
        },
        "D_testo_manoscritto_P1-2": {
            "stato": "INVARIATO",
            "valore_pubblicato": "+2.82 +/- 0.46",
            "arrotondamento_da_unione": "round(2.817516, 2) = 2.82; round(0.458057, 2) = 0.46",
            "documentazione_corretta": {
                "mock_mean": 2.817515500945948,
                "mock_sd": 0.45805659005182564,
                "z": -7.107703143478438,
                "rango": "3/2000",
                "n": 2000,
                "fonte": "unione step6 (200) + n1b (1800), validata"
            }
        },
        "E_percorsi_nuovi_nella_popolazione": [
            {
                "path": "results/paper1/rev_n4n5_report.json",
                "sha256": "d0e8284b499be1a3bc93eee2372b94f44b407972c07065a569cbd429f61e7cd6",
                "byte": 5902,
                "ruolo": "fonte primaria dei valori +3.90/+0.20 di Tab. 12 riga 1"
            },
            {
                "path": "src/paper1_rev_n4n5.py",
                "sha256": "029e32fe929f7e7802a721d2b3168ea173d4afb6baeac017e6e1d44050cdeb9f",
                "byte": 13141,
                "ruolo": "produttore di rev_n4n5_report.json, dichiarato dal campo 'script'"
            }
        ]
    },
    "reason": (
        "6.0b richiedeva di trovare lo script che produce +3.90/+0.20 o dichiarare "
        "la provenienza non ricostruibile. La provenienza e' nel record 50 dall'8 settembre "
        "e ora verificata su file: rev_n4n5_report.json, campo momenti.P10.agg.kurt, "
        "produttore paper1_rev_n4n5.py. "
        "P1-2 documentava numeri (2.8175/0.4581/-7.108/3/2000) che non si riproducevano "
        "da nessun singolo registro. La validazione con tre gate mostra che sono l'unione "
        "di due implementazioni disgiunte e con lo stesso stimatore. "
        "Il testo del manoscritto (+2.82 +/- 0.46) e' invariato. "
        "Due percorsi non censiti entrano nella popolazione citata dal ledger "
        "e vanno tracciati nel censimento del rilascio."
    ),
    "rules": {
        "marker": "emendamento-75-provenienza-tab12-riga1-e-P1-2-documentazione",
        "no_frozen_value_modified": (
            "Nessun valore congelato e' modificato. La correzione riguarda la documentazione "
            "interna di P1-2 (i numeri di supporto, non il testo del manoscritto) "
            "e la chiusura della voce 6.0b della checklist."
        ),
        "manuscript_text_unchanged": "+2.82 +/- 0.46 resta invariato nel testo sostitutivo di P1-2",
        "two_new_paths_for_census": (
            "rev_n4n5_report.json e paper1_rev_n4n5.py entrano come percorsi citati "
            "e devono risultare tracciati nel prossimo censimento del rilascio"
        )
    },
    "evidence": (
        "rev_n4n5_report.json sha256=d0e8284b… 5902 byte: "
        "momenti.P10.agg.kurt mock_mean=3.902956198001257 desi=0.20448735601308332 "
        "z=-6.181412840388943 (corrispondono a +3.90/+0.20 della Tab. 12). "
        "paper1_step6_NGC.json onepoint.restrictions['footprint pieno'].nu.kurt_excess: "
        "mock_mean=2.76384938163661 mock_std=0.47179461207878376 desi=-0.43821476405642734 "
        "rank=0/200. "
        "n1b_spectra_NGC.jsonl 1800 record idx 200-1999: "
        "kurt_in_mask mean=2.82347840309143 std=0.456249550694065 sotto_desi=3. "
        "paper2_valida_unione_p1_2.py cafabd43… commit 01543c6: "
        "G1 PASSATO (disgiunzione), G2 PASSATO (5/5 scarto max 3.08e-07 < 5e-07), "
        "G3 PASSATO (diff aritmetica 0.0). "
        "Tab. 12 Paper 1 (MN262388P_Proof_hi.pdf): intestazione 'mocks | DESI', "
        "didascalia '(NGC)': le coppie sono mock/DESI sullo stesso emisfero."
    )
}

# ── utilità ───────────────────────────────────────────────────────────────
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def righe_ledger(p: Path) -> int:
    return sum(1 for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip())

# ── comandi ───────────────────────────────────────────────────────────────
def selftest():
    # 1. il record è JSON serializzabile
    s = json.dumps(RECORD, ensure_ascii=False)
    r = json.loads(s)
    assert r["numbering_rule"].endswith("record 75."), "numerazione"

    # 2. i valori dell'unione si riproducono dall'aritmetica
    import math
    n1,m1,v1 = 200, 2.76384938163661, 0.47179461207878376
    n2,m2,v2 = 1800, 2.82347840309143, 0.456249550694065
    N = n1+n2; M = (n1*m1+n2*m2)/N
    V = ((n1-1)*v1**2+(n2-1)*v2**2+n1*(m1-M)**2+n2*(m2-M)**2)/(N-1)
    S = math.sqrt(V)
    assert abs(M - RECORD["new_value"]["B_validazione_unione_P1-2"]["unione"]["media"]) < 1e-12
    assert abs(S - RECORD["new_value"]["B_validazione_unione_P1-2"]["unione"]["sd"]) < 1e-12

    # 3. le due ancore del report sono presenti
    assert RECORD["new_value"]["A_provenienza_riga1_tab12"]["sha256"] == \
           "d0e8284b499be1a3bc93eee2372b94f44b407972c07065a569cbd429f61e7cd6"
    assert RECORD["new_value"]["A_provenienza_riga1_tab12"]["valori"]["mock_mean"] == \
           3.902956198001257

    print("selftest: 3/3 OK")

def verify_ledger():
    if not LEDGER.exists():
        raise FileNotFoundError(f"ledger non trovato: {LEDGER}")
    sha = sha256_file(LEDGER)
    rig = righe_ledger(LEDGER)
    if sha != LEDGER_SHA_ATTESO:
        raise AssertionError(
            f"sha ledger: atteso {LEDGER_SHA_ATTESO[:12]}…  trovato {sha[:12]}…\n"
            "Probabilmente il ledger è cambiato dall'ancora. Non procedere."
        )
    if rig != LEDGER_RIGHE_ATTESE:
        raise AssertionError(f"righe ledger: attese {LEDGER_RIGHE_ATTESE}, trovate {rig}")
    print(f"ledger: sha OK ({sha[:12]}…)  righe {rig}  —  ancora verificata")

def dry_run():
    verify_ledger()
    line = json.dumps(RECORD, ensure_ascii=False, separators=(",", ":"))
    print("DRY-RUN: la riga che verrebbe appesa (prime 200 car):")
    print(" ", line[:200], "…")
    print(f"  lunghezza riga: {len(line.encode())} byte")
    print("  OK — nessuna modifica")

def apply():
    verify_ledger()
    line = json.dumps(RECORD, ensure_ascii=False, separators=(",", ":"))
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    sha_nuovo = sha256_file(LEDGER)
    rig_nuovo = righe_ledger(LEDGER)
    print(f"[apply] appeso record 75")
    print(f"  ledger: {rig_nuovo} righe  sha {sha_nuovo[:12]}…")

def verify_post():
    sha = sha256_file(LEDGER)
    rig = righe_ledger(LEDGER)
    print(f"verify: {rig} righe  sha {sha[:12]}…  {'OK' if rig == LEDGER_RIGHE_ATTESE+1 else 'ANOMALIA'}")
    # rileggi l'ultimo record
    lines = [ln for ln in LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
    last = json.loads(lines[-1])
    assert last["numbering_rule"].endswith("record 75."), "ultimo record non è il 75"
    assert last["item"] == "6.0b / P1-2_documentazione"
    print(f"  ultimo record: item='{last['item']}'  tipo='{last['type']}'")
    print(f"  ledger sha: {sha}")

# ── main ──────────────────────────────────────────────────────────────────
CMDS = {"selftest": selftest, "dry-run": dry_run, "apply": apply, "verify": verify_post}

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=list(CMDS))
    args = ap.parse_args()
    CMDS[args.cmd]()

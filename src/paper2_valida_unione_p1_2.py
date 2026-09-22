#!/usr/bin/env python3
"""
paper2_valida_unione_p1_2.py
Valida l'unione step6 (idx 0–199, n=200) + n1b (idx 200–1999, n=1800)
come fonte dei numeri +2.8175 / +0.4581 / -7.108 / rango 3/2000
scritti nella documentazione di P1-2.

Gate dichiarati (prima del run):
  G1 disgiunzione  : {0..199} ∩ {200..1999} = ∅               [PASSATO da indici]
  G2 riproduzione  : spectral_summary(test2_XXXX.npz["delta"], mask)
                     riproduce n1b_spectra_NGC.jsonl su 5 campioni
                     con scarto relativo < 5e-7
  G3 stesso stimatore: le due implementazioni di kurt_excess
                     sono aritmeticamente identiche (diff = 0.0) [PASSATO]

Esito: stampa un blocco JSON con tutti i gate e i valori finali.

Uso:
  python src\\paper2_valida_unione_p1_2.py selftest
  python src\\paper2_valida_unione_p1_2.py run
"""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

# ── valori congelati (fonte: misure di questa sessione) ────────────────────
# step6: paper1_step6_NGC.json, onepoint.restrictions["footprint pieno"].nu.kurt_excess
STEP6_MEAN  = 2.76384938163661
STEP6_STD   = 0.47179461207878376
STEP6_N     = 200
STEP6_DESI  = -0.43821476405642734   # stesso valore in n1b: viene da DESI, non dal mock

# n1b: media e sd misurate su n1b_spectra_NGC.jsonl (1800 record, idx 200–1999)
N1B_MEAN    = 2.82347840309143
N1B_STD     = 0.456249550694065
N1B_N       = 1800
N1B_DESI    = STEP6_DESI             # stesso campo, stesso stima per DESI

# valori pubblicati in P1-2 (documentazione interna)
PUBBL_MEAN  = 2.8175
PUBBL_STD   = 0.4581
PUBBL_Z     = -7.108
PUBBL_RANGO = "3/2000"

# cancelli G2
CAMPIONI_G2 = [200, 500, 1000, 1500, 1999]
TOL_G2 = 5e-7   # scarto relativo massimo ammesso

# ── stimatori locali (copie esatte dai due script originali) ───────────────
def _kurt_n1b(nu_masked: np.ndarray) -> float:
    """Copia esatta di spectral_summary kurt_in_mask (paper1_rev_n1b_spectral.py:174)."""
    v = np.asarray(nu_masked, dtype=np.float64)
    sd = float(v.std())   # ddof=0
    return float(((v - v.mean()) ** 4).mean() / sd ** 4 - 3.0) if sd > 0 else float("nan")

def _kurt_step6(x: np.ndarray) -> float:
    """Copia esatta di moments() kurt_excess (paper1_step6_onepoint_betti.py:82)."""
    x = np.asarray(x, dtype=np.float64)
    mu = x.mean()
    d = x - mu
    v = (d ** 2).mean()   # ddof=0
    s = math.sqrt(v)
    return float((d ** 4).mean() / s ** 4 - 3.0)

# ── aritmetica dell'unione ─────────────────────────────────────────────────
def calcola_unione():
    n1, m1, v1 = STEP6_N, STEP6_MEAN, STEP6_STD
    n2, m2, v2 = N1B_N, N1B_MEAN, N1B_STD
    N = n1 + n2
    M = (n1 * m1 + n2 * m2) / N
    V = ((n1-1)*v1**2 + (n2-1)*v2**2 + n1*(m1-M)**2 + n2*(m2-M)**2) / (N-1)
    S = math.sqrt(V)
    z = (STEP6_DESI - M) / S
    return N, M, S, z

# ── selftest ───────────────────────────────────────────────────────────────
def selftest():
    # G3: i due stimatori sono aritmeticamente identici
    rng = np.random.default_rng(2026)
    x = rng.normal(size=50_000)
    diff = abs(_kurt_n1b(x) - _kurt_step6(x))
    assert diff == 0.0, f"G3 FALLITO: diff={diff}"

    # unione: scarto sotto mezza unità dell'ultima cifra quotata
    N, M, S, z = calcola_unione()
    assert N == 2000,                      f"N={N}"
    assert abs(M - PUBBL_MEAN) < 5e-5,     f"media {M}"
    assert abs(S - PUBBL_STD)  < 5e-5,     f"sd {S}"
    assert abs(z - PUBBL_Z)    < 1e-3,     f"z {z}"

    # G1: disgiunzione per costruzione (verifica aritmetica)
    step6_set = set(range(200))
    n1b_set   = set(range(200, 2000))
    assert step6_set.isdisjoint(n1b_set),  "G1 aritmetica fallita"
    assert step6_set | n1b_set == set(range(2000)), "unione non è {0..1999}"

    print("selftest: 7/7 OK")
    return True

# ── G2: riproduzione n1b su 5 campioni ────────────────────────────────────
def gate_g2():
    mask_path   = ROOT / "data" / "processed" / "phase6_fields" / "bgs_ngc_mask_128.npy"
    fields_dir  = ROOT / "results" / "phase8_test2_fields"
    jsonl_path  = ROOT / "results" / "paper1" / "n1b_spectra_NGC.jsonl"

    if not mask_path.exists():
        return [], False, f"maschera non trovata: {mask_path}"
    if not jsonl_path.exists():
        return [], False, f"JSONL non trovato: {jsonl_path}"

    mask = np.load(mask_path).astype(bool)

    # leggi valori congelati dal JSONL
    congelato = {}
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        congelato[r["idx"]] = r

    risultati = []
    for idx in CAMPIONI_G2:
        p = fields_dir / f"test2_{idx:04d}.npz"
        if not p.exists():
            risultati.append({"idx": idx, "ok": False, "msg": f"non trovato: {p}"})
            print(f"  G2 idx={idx}: NON TROVATO")
            continue

        nu_arr = np.load(p)["delta"]          # chiave "delta", contenuto: ν
        v = nu_arr.astype(np.float64)[mask]
        calcolato = _kurt_n1b(v)

        atteso = congelato.get(idx, {}).get("kurt_in_mask")
        if atteso is None:
            risultati.append({"idx": idx, "ok": False, "msg": "non nel JSONL"})
            print(f"  G2 idx={idx}: non nel JSONL")
            continue

        scarto = abs(calcolato - atteso) / (abs(atteso) if atteso != 0 else 1.0)
        ok = scarto < TOL_G2
        risultati.append({
            "idx": idx,
            "calcolato": round(calcolato, 10),
            "atteso":    round(atteso, 10),
            "scarto_rel": f"{scarto:.2e}",
            "ok": ok
        })
        print(f"  G2 idx={idx:4d}: calc={calcolato:.8f}  att={atteso:.8f}"
              f"  scarto={scarto:.2e}  {'OK' if ok else 'FALLITO'}")

    passati = sum(1 for r in risultati if r.get("ok"))
    ok_totale = (passati == len(CAMPIONI_G2))
    return risultati, ok_totale, f"{passati}/{len(CAMPIONI_G2)}"

# ── main ──────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["selftest", "run"])
    args = ap.parse_args()

    if args.cmd == "selftest":
        selftest()
        return

    # run
    print("=" * 68)
    print("paper2_valida_unione_p1_2.py  —  validazione unione P1-2")
    print("=" * 68)

    print("\n[0] selftest...")
    selftest()

    print("\n[G1] disgiunzione step6 / n1b")
    print("  step6 : idx 0–199  (200 valori, delta_0000..delta_0199.npy)")
    print("  n1b   : idx 200–1999 (1800 record, test2_0200..test2_1999.npz)")
    print("  intersezione : ∅   unione : {0..1999}   G1: PASSATO (strutturale)")

    print("\n[G2] riproduzione n1b su 5 campioni...")
    g2_res, g2_ok, g2_msg = gate_g2()
    print(f"  G2: {'PASSATO' if g2_ok else 'FALLITO'} ({g2_msg})")

    print("\n[G3] stesso stimatore")
    print("  entrambi: ddof=0, excess kurtosis of Fisher, diff aritmetica = 0.0")
    print("  G3: PASSATO (selftest)")

    print("\n[unione]")
    N, M, S, z = calcola_unione()
    print(f"  n={N}  media={M:.15f}")
    print(f"  sd={S:.15f}")
    print(f"  z={z:.6f}  rango=3/{N}")
    print(f"  testo P1-2 (2 dec): +{round(M,2):.2f} ± {round(S,2):.2f}  INVARIATO")

    conclusione = "VALIDATA" if g2_ok else "NON VALIDATA"
    print(f"\nCONCLUSIONE: unione {conclusione}")

    esito = {
        "G1_disgiunzione":       {"status": "PASSATO",
                                  "step6_idx": "0–199", "n1b_idx": "200–1999",
                                  "intersezione": "∅"},
        "G2_riproduzione_n1b":   {"status": "PASSATO" if g2_ok else "FALLITO",
                                  "campioni": g2_res,
                                  "tolleranza_relativa": TOL_G2},
        "G3_stesso_stimatore":   {"status": "PASSATO",
                                  "diff_aritmetica": 0.0},
        "unione": {
            "n_step6": STEP6_N, "mean_step6": STEP6_MEAN, "std_step6": STEP6_STD,
            "n_n1b":   N1B_N,   "mean_n1b":   N1B_MEAN,   "std_n1b":   N1B_STD,
            "N": N, "media": M, "sd": S, "z": z,
            "rango": f"3/{N}", "desi": STEP6_DESI
        },
        "scarti_vs_pubblicato": {
            "media": abs(M - PUBBL_MEAN),
            "sd":    abs(S - PUBBL_STD),
            "z":     abs(z - PUBBL_Z)
        },
        "conclusione": conclusione
    }
    print("\n" + json.dumps(esito, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()



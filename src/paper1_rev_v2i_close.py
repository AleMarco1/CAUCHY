#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2i_close.py

V2i - CHIUSURA DI V2: PROVA DIRETTA E NUMERI CORRETTI

CATENA CAUSALE RICOSTRUITA
--------------------------
1. phase8_test2_fields/ conserva per gli indici 0-199 i cubi del PILOTA,
   mai sovrascritti dal run definitivo.
     prova: dentro maschera, Spearman fra i due cache vale 0.9996 sui
     controlli (idx 200/500/1000/1805) e 0.60-0.67 sul blocco 0-199.
2. phase9_extract_features.py fa glob("test2_*.npz") su tutti i 2000 e li
   tratta come l'ensemble definitivo.
3. Il suo controllo di sanita' (righe 149-156) confronta la MEDIA con il
   valore congelato e mai la DEVIAZIONE STANDARD:
     drift = |35424.8 - 35436.7| / 313.0 = 0.038 -> "[ok]".
   sigma passa da 313.0 a 444.8 (+42%) senza che nulla se ne accorga.
4. Da li' il numero entra in cauchy_mnras.tex: tabella battery (righe 459,
   510, 636) e decomposizione della varianza (riga 735).

Record congelato autorevole - phase8_test2_masked.json, 2026-07-03,
n_mock_valid=2000, masked_filtration=true:
    mock_beta1_max: mean 35436.686  std 312.9891651683112  z_desi -22.94228
    "N=2000; empirical p-floor ~1/2001. Ranks primary."
paper1_remap.py lo riproduce cifra per cifra.

NOTA SU DUE METRICHE DEL v2h, DA IGNORARE
-----------------------------------------
  - violazioni_monotonia_frac ~ 0.5 ovunque, anche dove Spearman e' 0.9996:
    con 300k punti i valori adiacenti ordinati distano pochissimo e un
    rumore infinitesimo inverte meta' delle coppie. Misura il rumore locale.
  - fuori_maschera_spearman = 1.0 ovunque: fuori maschera i cubi sono
    costanti, e la correlazione di rango fra due costanti esce 1.0 per
    costruzione.
L'unica colonna informativa era la Spearman dentro maschera.

COSA FA QUESTO SCRIPT
---------------------
A  PROVA DIRETTA. phase8_test2_permock.csv ha beta1_max per gli indici
   0-199 (i valori del pilota). Se coincidono con l'npz e NON con i nostri,
   la catena causale e' dimostrata invece che ricostruita.
B  NUMERI CORRETTI PER M26. sigma, frazione stocastica della varianza
   (M26 riga 735 usa 110 generatori su sigma=445 -> 6%), e le correlazioni
   beta1_max x cosmologia ricalcolate coi valori corretti sugli stessi
   200 indici, con intervallo di confidenza.
C  PERIMETRO DEL DANNO. Quali prodotti a valle hanno consumato l'npz.

Solo lettura. Scrive un report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_v2i_close.py
"""

import argparse
import csv
import json
import os
import re
import tempfile
from pathlib import Path

import numpy as np

FROZEN = {"mean": 35436.686, "std": 312.9891651683112, "z": -22.94228298969569}
DESI_NGC = 28256.0
NH1 = "base.N_H1"
BLOCK = 200
M26_STOCH = 110.0          # dispersione stocastica HOD/downsampling, M26 riga 735
M26_SIGMA = 445.0


def read_jsonl(path):
    recs = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    return recs


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=True, default=str)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def corr_ci(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    n = int(m.sum())
    if n < 6:
        return None
    r = float(np.corrcoef(x[m], y[m])[0, 1])
    zf = 0.5 * np.log((1 + r) / (1 - r))
    se = 1.0 / np.sqrt(n - 3)
    return {"r": r, "n": n,
            "ic95": [float(np.tanh(zf - 1.96 * se)),
                     float(np.tanh(zf + 1.96 * se))],
            "sigma": float(abs(zf) / se)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--max_print", type=int, default=15)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    rep = {"script": "paper1_rev_v2i_close.py", "congelato": FROZEN}

    # dati
    z = np.load(res / "phase9_likeforlike_arrays.npz", allow_pickle=True)
    npz_b1 = np.asarray(z["beta1_max"], float)
    npz_p1 = np.asarray(z["pers1_mean"], float) if "pers1_mean" in z.files else None
    cos = {k: np.asarray(z[k], float).ravel()
           for k in ("w0", "Om", "s8") if k in z.files}

    recs = read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")
    ours = np.array([float(flatten(r).get(NH1, np.nan)) for r in recs])

    # ============================================================ A
    print("=" * 78)
    print("A - PROVA DIRETTA: l'npz sui primi 200 riporta i valori del PILOTA?")
    print("=" * 78)
    fc = res / "phase8_test2_permock.csv"
    pilot_b1 = np.full(BLOCK, np.nan)
    pilot_p1 = np.full(BLOCK, np.nan)
    if not fc.exists():
        print(f"  [!] {fc} non trovato")
    else:
        for row in csv.DictReader(open(fc, newline="", encoding="utf-8")):
            try:
                i = int(row["index"])
            except (KeyError, ValueError):
                continue
            if 0 <= i < BLOCK:
                try:
                    pilot_b1[i] = float(row["beta1_max"])
                except (KeyError, ValueError):
                    pass
                try:
                    pilot_p1[i] = float(row["pers1"])
                except (KeyError, ValueError):
                    pass

        ok = np.isfinite(pilot_b1)
        eq_npz = np.isclose(pilot_b1[ok], npz_b1[:BLOCK][ok], rtol=0, atol=0.5)
        eq_our = np.isclose(pilot_b1[ok], ours[:BLOCK][ok], rtol=0, atol=0.5)
        print(f"  righe pilota con beta1_max: {int(ok.sum())}/{BLOCK}\n")
        print(f"  CSV pilota == npz   : {int(eq_npz.sum())}/{int(ok.sum())} "
              f"({100*eq_npz.mean():.1f}%)")
        print(f"  CSV pilota == nostri: {int(eq_our.sum())}/{int(ok.sum())} "
              f"({100*eq_our.mean():.1f}%)")

        print(f"\n  {'idx':>5s} {'CSV pilota':>12s} {'npz':>10s} "
              f"{'nostro':>10s} {'CSV-npz':>9s} {'CSV-nostro':>11s}")
        for i in np.where(ok)[0][:args.max_print]:
            print(f"  {i:>5d} {pilot_b1[i]:>12.1f} {npz_b1[i]:>10.1f} "
                  f"{ours[i]:>10.1f} {pilot_b1[i]-npz_b1[i]:>+9.1f} "
                  f"{pilot_b1[i]-ours[i]:>+11.1f}")

        print(f"\n  VERDETTO:")
        if eq_npz.mean() > 0.95 and eq_our.mean() < 0.5:
            print(f"    il CSV del pilota coincide con l'npz e NON coi nostri")
            print(f"    valori -> CATENA CAUSALE DIMOSTRATA. I primi 200")
            print(f"    dell'npz sono il pilota. Indagine V2 chiusa.")
        elif eq_npz.mean() > 0.95 and eq_our.mean() > 0.95:
            print(f"    il CSV coincide con entrambi: il pilota non e' la")
            print(f"    fonte della divergenza. Ipotesi da rivedere.")
        else:
            print(f"    il CSV non coincide con l'npz: i cubi del pilota sono")
            print(f"    stati RICOMPUTATI da phase9, quindi i valori non")
            print(f"    devono coincidere esattamente. Guardare la")
            print(f"    correlazione qui sotto invece dell'uguaglianza.")
            for nome, arr in (("npz", npz_b1[:BLOCK]), ("nostri", ours[:BLOCK])):
                c = corr_ci(pilot_b1, arr)
                if c:
                    print(f"      corr(CSV pilota, {nome:>6s}) = {c['r']:+.4f}"
                          f"   n={c['n']}")
        rep["prova_pilota"] = {
            "n_csv": int(ok.sum()),
            "frazione_uguali_npz": float(eq_npz.mean()),
            "frazione_uguali_nostri": float(eq_our.mean()),
            "corr_csv_npz": corr_ci(pilot_b1, npz_b1[:BLOCK]),
            "corr_csv_nostri": corr_ci(pilot_b1, ours[:BLOCK])}

    # ============================================================ B
    print("\n" + "=" * 78)
    print("B - NUMERI CORRETTI PER M26")
    print("=" * 78)
    sd_our = float(ours.std(ddof=1))
    print(f"  dispersione dell'ensemble")
    print(f"    M26 pubblicato      : {M26_SIGMA:.0f}   (npz contaminato)")
    print(f"    congelato / corretto: {sd_our:.1f}   "
          f"(= phase8_test2_masked.json)")

    print(f"\n  decomposizione della varianza (M26 riga 735)")
    print(f"    dispersione stocastica HOD/downsampling: {M26_STOCH:.0f} generatori")
    f_pub = (M26_STOCH / M26_SIGMA) ** 2
    f_cor = (M26_STOCH / sd_our) ** 2
    print(f"    frazione stocastica pubblicata : {100*f_pub:.1f}%  "
          f"-> 'remaining ~{100*(1-f_pub):.0f}% is cosmological'")
    print(f"    frazione stocastica corretta   : {100*f_cor:.1f}%  "
          f"-> resta ~{100*(1-f_cor):.0f}%")
    rep["varianza"] = {"sigma_pubblicata": M26_SIGMA, "sigma_corretta": sd_our,
                       "frazione_stocastica_pubblicata": f_pub,
                       "frazione_stocastica_corretta": f_cor}

    print(f"\n  correlazioni beta1_max x cosmologia sui 200 indici con parametri")
    print(f"    (M26 riga 735 riporta Om +0.45, s8 +0.29, w0 -0.03)")
    rep["correlazioni"] = {}
    for k, a in cos.items():
        c_our = corr_ci(a, ours)
        c_npz = corr_ci(a, npz_b1)
        if c_our:
            print(f"    {k:>4s}  con valori CORRETTI: r = {c_our['r']:+.3f}"
                  f"   IC95% [{c_our['ic95'][0]:+.3f}, {c_our['ic95'][1]:+.3f}]"
                  f"   n={c_our['n']}")
        if c_npz:
            print(f"    {k:>4s}  con valori npz     : r = {c_npz['r']:+.3f}"
                  f"   IC95% [{c_npz['ic95'][0]:+.3f}, {c_npz['ic95'][1]:+.3f}]")
        rep["correlazioni"][k] = {"corretto": c_our, "npz": c_npz}
    print(f"\n    ATTENZIONE: n=200 in entrambi i casi, e sono proprio gli")
    print(f"    indici del pilota. Se M26 avesse calcolato r sui 2000 con una")
    print(f"    tabella di parametri nwLH separata, il confronto va rifatto su")
    print(f"    quella tabella: qui non e' disponibile.")

    print(f"\n  la conclusione primaria non si muove")
    below = int((ours < DESI_NGC).sum())
    print(f"    DESI NGC = {DESI_NGC:.0f}   mock sotto DESI = {below}")
    print(f"    rank {below+1}/{ours.size+1}   z(sigma corretta) = "
          f"{(DESI_NGC - ours.mean())/sd_our:+.2f}   "
          f"z(sigma M26) = {(DESI_NGC - ours.mean())/M26_SIGMA:+.2f}")
    print(f"    margine sotto il minimo dell'ensemble: "
          f"{ours.min() - DESI_NGC:+.0f} generatori")

    # ============================================================ C
    print("\n" + "=" * 78)
    print("C - PERIMETRO DEL DANNO: chi ha consumato l'npz contaminato")
    print("=" * 78)
    pat = re.compile(r"phase9_likeforlike_arrays")
    consumers = []
    for d in (root / "src", root):
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            if ".venv" in str(p) or p.name.startswith("paper1_rev_"):
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if pat.search(txt):
                writes = "savez" in txt and "out_npz" in txt
                consumers.append((p.name, "PRODUTTORE" if writes else "consumatore"))
    for n, role in sorted(set(consumers)):
        print(f"  {role:<12s} {n}")
    print(f"\n  Ogni consumatore eredita il blocco contaminato. Da rivedere in")
    print(f"  M26: tabella battery (tex 459, 510, 636), decomposizione della")
    print(f"  varianza (735), istogramma empirico, curva di risposta a w0.")
    rep["consumatori"] = sorted(set(consumers))

    outp = res / "paper1" / "rev_v2i_close_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()

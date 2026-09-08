#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 — cancello 5.3: il residuo beyond-two-point.

PERCHE' ESISTE
  Il 5.3 verifica la stabilita' su ensemble v2 del residuo di 1710.5 generatori
  a 6.8 sigma, che e' l'unico numero della serie a stare in un manoscritto GIA'
  SOTTOMESSO (Paper 1, MN-26-2388-P). Se v2 lo sposta, il Paper 1 va corretto.

  Ma prima di confrontarlo con v2 bisogna poterlo RIPRODURRE su v1, e finora non
  si poteva: `paper1_rev2_residual_significance.py` ha `load_pairs()` che solleva
  NotImplementedError. Il codice che ha prodotto 1710.4900000000016 e' stato
  adattato in locale e l'adattamento non e' stato salvato. Il JSON dichiara la
  sorgente in una stringa e nessuno puo' rieseguirlo: e' esattamente il tipo di
  buco che il 5.3 esiste per prevenire.

DOVE STA IL NUMERO, E DOVE NON STA
  Il JSON congelato dichiara come sorgente "n2_persistence_NGC.jsonl:n_tot +
  n10_phases_NGC.jsonl:N_H1 (unione su idx)". L'unione NON serve, e non e'
  nemmeno praticabile: n2_persistence usa indici interi (200, 201, ...) e
  per_mock_NGC_R5 chiavi stringa (delta_0000), che non si parlano. Tutto esce da
  n10_phases_NGC.jsonl da solo, perche' ogni record `mock_pr` porta GIA' la
  coppia appaiata nella stessa riga: N_H1_orig e N_H1. Verificato: la media dei
  guadagni riproduce gain_mock_mean = 3752.91 all'ultima cifra.

LE DUE SIGMA, CHE NON SONO LA STESSA COSA
  n10_phases stampa se_pr = sqrt(sem_mock^2 + sem_desi^2) = 40.62, la SEM
  PROCEDURALE. Il reference dichiara invece che 6.8 sigma viene dalla
  DISPERSIONE MOCK-TO-MOCK di Delta_N, sigma_Delta = 250.5, ed e' la
  ricalibrazione che il Referee 3 ha imposto. 1710.5/250.5 = 6.83 contro
  1710.5/40.6 = 42.1. Su v2 confrontare 6.8 con un 42 ricalcolato dalla SEM
  farebbe concludere che il residuo e' cresciuto di un fattore sei.
  Questo cancello riproduce ENTRAMBE e le tiene separate.

PREDIZIONE PER SGC, dichiarata prima del run
  SGC non e' pubblicato: misurarlo aggiunge un risultato che il Paper 1 non
  riporta, quindi la predizione va scritta prima o l'esito si legge a posteriori.
    - frazione spettrale attesa nell'intervallo 0.70-0.82 (NGC: 0.7625);
    - residuo beyond-two-point presente a piu' di 3 sigma_Delta.
  Ragione: il deficit SGC vale 19.19% contro 20.26%, i due emisferi condividono
  la stessa suite di 2000 mock, e non c'e' motivo strutturale perche' la
  decomposizione cambi natura. Se esce fuori intervallo, e' un risultato e va
  riportato come tale — non riparato.

  CAVEAT DI CONFRONTABILITA': il rango 1/101 nasce da 50 realizzazioni di DESI
  randomizzato e 100 mock. Su v2, o su SGC, il rango e' confrontabile solo a
  PARITA' di quelle numerosita'. Se cambiano, si riporta il residuo e non il
  rango.

Uso:
    python src\\paper2_gate53.py selftest
    python src\\paper2_gate53.py gate --region NGC
    python src\\paper2_gate53.py gate --region SGC --phases results\\paper1\\n10_phases_SGC.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

# Bersagli congelati: results/paper1/paper1_rev2_residual_significance.json e
# n10_report_NGC.json. Riprodotti all'ultima cifra o il cancello fallisce.
TARGETS_NGC = {
    "desi": 28256.0,
    "desi_phi_mean": 33719.4,
    "mock_mean": 35458.92,
    "mock_phi_mean": 39211.83,
    "gain_mock_mean": 3752.91,
    "gain_mock_sd": 250.47869705180057,
    "gain_desi": 5463.4000000000015,
    "residual": 1710.4900000000016,
    "z_residual": 6.828884133193417,
    "corr_N_Nphi": 0.6810786759807066,
    "rank": "1/101",
    "spectral_fraction": 0.7625282524309588,
    "sem_procedural": 40.61998845329711,
    "sd_deconvolved": 195.16807545489525,
    "z_deconvolved": 8.764189512107517,
    "sd_draw_published": 157.0,
    "sd_draw_exact": 157.009813810007,
    "n_mock": 100,
    "n_desi_draws": 50,
}
TOL_REL = 1e-9
# Il JSON congelato dichiara `sd_draw_assumed: 157.0`: e' la sd delle 50
# estrazioni DESI arrotondata. La sd vera vale 157.009813810007.
SD_DRAW_PUBLISHED = 157.0
SGC_PRED = {"spectral_fraction_range": [0.70, 0.82], "min_z_residual": 3.0}


def load_pairs(path):
    """La `load_pairs` che mancava. Quattro righe, e chiude il buco.

    Ogni record `mock_pr` porta la coppia appaiata nella STESSA riga, quindi
    l'appaiamento e' garantito per costruzione e non per join su indice — che
    era il punto su cui il docstring originale metteva in guardia.
    """
    rows = [json.loads(l) for l in
            Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    mock = sorted((r for r in rows if r.get("tipo") == "mock_pr"),
                  key=lambda r: r["idx"])
    desi = [r["N_H1"] for r in rows if r.get("tipo") == "desi_pr"]
    if not mock or not desi:
        sys.exit(f"[FATAL] {path}: mock_pr={len(mock)} desi_pr={len(desi)}")
    N = np.array([r["N_H1_orig"] for r in mock], float)
    N_phi = np.array([r["N_H1"] for r in mock], float)
    return N, N_phi, np.array(desi, float)


def compute(N, N_phi, desi_pr, desi_orig):
    """L'aritmetica di paper1_rev2_residual_significance.py, ricostruita."""
    dN = N_phi - N
    desi_phi = float(desi_pr.mean())
    dN_desi = desi_phi - desi_orig
    residual = dN_desi - float(dN.mean())
    sd = float(dN.std(ddof=1))
    n_ge = int((dN >= dN_desi).sum())
    # DUE deconvoluzioni, e il campo congelato dice quale usa: il JSON di
    # riferimento porta `sd_draw_assumed: 157.0`, cioe' la sd delle estrazioni
    # DESI ARROTONDATA a tre cifre. La sd vera e' 157.009813810007, e la
    # riporta n10_report_NGC.json. Lo scarto e' 6.3e-5 relativo e sposta la
    # deconvoluta di 4e-5: nulla di fisico, ma un cancello a 1e-9 non puo'
    # pretendere che i due numeri coincidano. Si riproducono ENTRAMBI e si
    # dichiara quale ha prodotto il valore pubblicato.
    sd_draw = float(desi_pr.std(ddof=1))
    var_dec = sd ** 2 - sd_draw ** 2
    out = {
        "n_mock": int(N.size), "n_desi_draws": int(desi_pr.size),
        "desi": desi_orig, "desi_phi_mean": desi_phi,
        "mock_mean": float(N.mean()), "mock_phi_mean": float(N_phi.mean()),
        "gain_mock_mean": float(dN.mean()), "gain_mock_sd": sd,
        "gain_desi": dN_desi, "residual": residual,
        "z_residual": residual / sd,
        "corr_N_Nphi": float(np.corrcoef(N, N_phi)[0, 1]),
        "rank": f"{n_ge + 1}/{N.size + 1}",
        # Frazione spettrale: si legge sui DEFICIT, non sui guadagni.
        "spectral_fraction": (float(N_phi.mean()) - desi_phi)
                             / (float(N.mean()) - desi_orig),
        # SEM procedurale: NON e' il metro del 6.8 sigma. Riportata a parte.
        "sem_procedural": float(np.sqrt((N_phi.std(ddof=1) / np.sqrt(N.size)) ** 2
                                        + (desi_pr.std(ddof=1)
                                           / np.sqrt(desi_pr.size)) ** 2)),
        "sd_draw_exact": sd_draw,
    }
    out["sd_deconvolved_exact"] = float(np.sqrt(var_dec)) if var_dec > 0 else float("nan")
    out["z_deconvolved_exact"] = (residual / out["sd_deconvolved_exact"]
                                  if var_dec > 0 else float("nan"))
    # Variante del manoscritto: sd delle estrazioni arrotondata a 157.0.
    v2 = sd ** 2 - SD_DRAW_PUBLISHED ** 2
    out["sd_draw_published"] = SD_DRAW_PUBLISHED
    out["sd_deconvolved"] = float(np.sqrt(v2)) if v2 > 0 else float("nan")
    out["z_deconvolved"] = residual / out["sd_deconvolved"] if v2 > 0 else float("nan")
    return out


def check(got, targets, tol=TOL_REL):
    fails = []
    for k, exp in targets.items():
        if k not in got:
            fails.append(f"{k}: assente")
            continue
        g = got[k]
        if isinstance(exp, str):
            ok = (g == exp)
            d = ""
        else:
            d = abs(g - exp) / max(abs(exp), 1e-30)
            ok = d <= tol
        if not ok:
            fails.append(f"{k}: {g!r} atteso {exp!r}"
                         + (f" (rel {d:.2e})" if d != "" else ""))
    return fails


def cmd_gate(a):
    reg = a.region
    path = a.phases or f"results/paper1/n10_phases_{reg}.jsonl"
    if not Path(path).exists():
        print(f"[FATAL] {path} non esiste.")
        if reg == "SGC":
            print("  Il file SGC va PRODOTTO: 50 realizzazioni DESI a fasi")
            print("  randomizzate e 100 mock, con paper1_rev_n10_phases.py.")
            print(f"  Predizione gia' dichiarata: frazione spettrale in "
                  f"{SGC_PRED['spectral_fraction_range']}, "
                  f"z > {SGC_PRED['min_z_residual']}.")
        return 2

    N, N_phi, desi_pr = load_pairs(path)
    got = compute(N, N_phi, desi_pr, a.desi)
    print("=" * 76)
    print(f"5.3 — residuo beyond-two-point, {reg}   ({path})")
    print("=" * 76)
    print(f"  {got['n_mock']} mock appaiati, {got['n_desi_draws']} realizzazioni "
          f"di DESI randomizzato")
    for k in ("mock_mean", "mock_phi_mean", "desi", "desi_phi_mean",
              "gain_mock_mean", "gain_desi", "residual"):
        print(f"    {k:>18} {got[k]:14.4f}")
    print(f"\n  DUE sigma, e non sono la stessa cosa:")
    print(f"    dispersione mock-to-mock  sigma_Delta = {got['gain_mock_sd']:.4f}"
          f"   ->  z = {got['z_residual']:.4f}   <-- il metro del manoscritto")
    print(f"    SEM procedurale                       = {got['sem_procedural']:.4f}"
          f"   ->  z = {got['residual']/got['sem_procedural']:.1f}   "
          f"(NON si usa)")
    print(f"    deconvoluta, sd estrazioni 157.0 (pubblicata) = "
          f"{got['sd_deconvolved']:.4f}   ->  z = {got['z_deconvolved']:.4f}")
    print(f"    deconvoluta, sd estrazioni {got['sd_draw_exact']:.6f} (esatta)   = "
          f"{got['sd_deconvolved_exact']:.4f}   ->  "
          f"z = {got['z_deconvolved_exact']:.4f}")
    print(f"\n  frazione spettrale {got['spectral_fraction']:.6f}   "
          f"residuo di fase {1-got['spectral_fraction']:.6f}   "
          f"rango {got['rank']}   corr {got['corr_N_Nphi']:.6f}")

    if reg == "NGC":
        fails = check(got, TARGETS_NGC)
        print(f"\n  cancello contro i valori congelati: "
              f"{'SUPERATO' if not fails else 'FALLITO'}")
        for f in fails:
            print(f"    [FAIL] {f}")
        if not fails:
            print("    Il numero pubblicato e' ora RIPRODUCIBILE da un solo file.")
    else:
        lo, hi = SGC_PRED["spectral_fraction_range"]
        sf, z = got["spectral_fraction"], abs(got["z_residual"])
        in_r = lo <= sf <= hi
        ok_z = z > SGC_PRED["min_z_residual"]
        print(f"\n  contro la predizione dichiarata prima del run:")
        print(f"    frazione spettrale {sf:.4f} in [{lo}, {hi}]: "
              f"{'CONFERMATA' if in_r else 'SMENTITA'}")
        print(f"    |z| = {z:.2f} > {SGC_PRED['min_z_residual']}: "
              f"{'CONFERMATA' if ok_z else 'SMENTITA'}")
        if not (in_r and ok_z):
            print("    Una predizione smentita e' un risultato: si riporta, "
                  "non si ripara.")
        print(f"\n  Il rango {got['rank']} e' confrontabile con l'1/101 di NGC "
              f"solo a parita' di numerosita'")
        print(f"  ({got['n_mock']} mock, {got['n_desi_draws']} estrazioni "
              f"contro 100 e 50).")
        fails = []

    got.update({"schema": "paper2_gate53_v1", "region": reg, "source": str(path),
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "pass": not fails, "fails": fails})
    if a.out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(got, sort_keys=True, default=float) + "\n")
        print(f"\n[scritto] {a.out}")
    return 1 if fails else 0


def cmd_selftest(a):
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    rng = np.random.default_rng(53)
    n = 100
    N = rng.normal(35000, 258, n)
    gain = rng.normal(3750, 250, n)
    N_phi = N + gain
    desi, desi_phi_true = 28256.0, 33719.4
    desi_pr = desi_phi_true + rng.normal(0, 157, 50)
    got = compute(N, N_phi, desi_pr, desi)

    expect("1. il residuo e' guadagno DESI meno guadagno medio dei mock",
           abs(got["residual"] - ((desi_pr.mean() - desi) - gain.mean())) < 1e-9)
    expect("2. z usa la dispersione mock-to-mock, non la SEM",
           abs(got["z_residual"] - got["residual"] / gain.std(ddof=1)) < 1e-9)
    expect("3. e la SEM procedurale e' molto piu' piccola: fattore ~6",
           got["sem_procedural"] < got["gain_mock_sd"] / 4,
           f"(sd {got['gain_mock_sd']:.1f} contro sem {got['sem_procedural']:.1f})")
    expect("4. la deconvoluta toglie il rumore di estrazione di DESI",
           got["sd_deconvolved"] < got["gain_mock_sd"]
           and got["sd_deconvolved_exact"] < got["gain_mock_sd"])
    expect("4b. le due deconvoluzioni differiscono, e il campo dice quale e' quale",
           got["sd_draw_published"] == 157.0
           and got["sd_draw_exact"] != got["sd_draw_published"],
           f"(esatta {got['sd_draw_exact']:.6f})")
    expect("5. il rango e' empirico e su n+1",
           got["rank"].endswith(f"/{n+1}"))

    # appaiamento: mescolare N_phi rispetto a N deve GONFIARE sigma_Delta
    perm = rng.permutation(n)
    bad = compute(N, N_phi[perm], desi_pr, desi)
    expect("6. rompendo l'appaiamento sigma_Delta cresce e z cala",
           bad["gain_mock_sd"] > got["gain_mock_sd"]
           and abs(bad["z_residual"]) < abs(got["z_residual"]),
           f"(sd {got['gain_mock_sd']:.0f} -> {bad['gain_mock_sd']:.0f})")
    expect("7. ma la MEDIA del guadagno non cambia: per questo un confronto "
           "di medie non basta",
           abs(bad["gain_mock_mean"] - got["gain_mock_mean"]) < 1e-9)

    expect("8. il cancello NGC ha tutti i bersagli congelati",
           {"residual", "z_residual", "gain_mock_sd", "spectral_fraction",
            "rank", "sem_procedural"} <= set(TARGETS_NGC))
    expect("9. e distingue le due sigma nei bersagli",
           abs(TARGETS_NGC["gain_mock_sd"] / TARGETS_NGC["sem_procedural"] - 6.17)
           < 0.05,
           f"({TARGETS_NGC['gain_mock_sd']/TARGETS_NGC['sem_procedural']:.2f})")
    bad_t = dict(TARGETS_NGC); bad_t["residual"] = 1711.0
    expect("10. e un bersaglio spostato di 0.5 su 1710 viene intercettato",
           check({**got, "residual": 1710.49}, {"residual": bad_t["residual"]}))
    expect("11. la predizione SGC e' dichiarata nel file, non altrove",
           SGC_PRED["spectral_fraction_range"] == [0.70, 0.82]
           and SGC_PRED["min_z_residual"] == 3.0)

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    q = sub.add_parser("gate")
    q.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    q.add_argument("--phases", default=None)
    q.add_argument("--desi", type=float, default=None)
    q.add_argument("--out", default="results/paper2/gate53.jsonl")
    a = p.parse_args()
    if a.cmd == "selftest":
        return cmd_selftest(a)
    if a.desi is None:
        a.desi = 28256.0 if a.region == "NGC" else 15122.0
    return cmd_gate(a)


if __name__ == "__main__":
    sys.exit(main())

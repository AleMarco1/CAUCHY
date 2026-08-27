#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_compD_nonlinear.py — Paper 2, Componente D, item D6

La misura D5 dice che i sette parametri LCDM lasciano non spiegato il ~62% della
varianza cosmologica di N_H1.  Ma R^2 e' LINEARE: una dipendenza quadratica o di
interazione apparirebbe identica a "varianza non parametrizzata".  Prima di
rivendicare D5 vanno esclusi due scenari, in quest'ordine.

  TEST A — non linearita' nei parametri.
      Modelli annidati: lineare (7 termini) -> + quadrati (14) -> + interazioni (35).
      R^2 grezzo gonfia con i termini; si usa R^2 VALIDATO INCROCIATO (k-fold),
      che non premia l'overfitting.

  TEST B — il due punti.
      Regressione su P(k) dal cache results/phase7_pk_nwlh_cache.npz, in componenti
      principali di log P(k), con CV.  Poi la domanda che conta:

  TEST C — quanta parte del divario chiude P(k)?
      Residui della regressione sui 7 parametri, regrediti su P(k).

TETTI, e non sono lo stesso per tutti i predittori:
  * predittori funzione dei soli PARAMETRI  -> R^2_max = (sigma_cos/sigma_tot)^2 = 0.698
  * predittori MISURATI sulla stessa realizzazione (P(k) del campo) -> il termine di
    realizzazione e' condiviso, quindi R^2_max = (sigma_cos^2+sigma_real^2)/sigma_tot^2
    = 0.832.  Confrontare P(k) col tetto 0.698 sarebbe scorretto.

LETTURA:
  P(k) chiude il divario  -> N_H1 e' una statistica del due punti, e i parametri
                             fallivano solo perche' la mappa parametri -> P(k) non
                             e' lineare.
  P(k) NON lo chiude      -> la parte non spiegata e' OLTRE il due punti, e si
                             collega al residuo beyond-two-point di 1710 generatori
                             del Paper 1.

Uso:
    python src\\paper2_compD_nonlinear.py --selftest
    python src\\paper2_compD_nonlinear.py --region NGC ^
        --params data\\raw\\quijote\\3D_cubes\\latin_hypercube_nwLH\\latin_hypercube_nwLH_params.txt ^
        --pk results\\phase7_pk_nwlh_cache.npz ^
        --out results\\paper2\\compD_nonlinear_NGC.jsonl

Sola lettura sugli ingressi.  JSONL append-only, atomico.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time

import numpy as np

FROZEN = {
    "NGC": {"path": "results/paper1/per_mock_NGC_R5.jsonl", "mean": 35436.686, "sd": 312.989},
    "SGC": {"path": "results/paper1/per_mock_SGC_R5.jsonl", "mean": 18712.968, "sd": 197.787},
}
FIELD = ("base", "N_H1")
TOL = 0.05

SIGMA_COS, SIGMA_FIXED, SIGMA_REAL, SIGMA_TOT = 261.5, 172.0, 114.6, 313.0
CEIL_PARAMS = (SIGMA_COS / SIGMA_TOT) ** 2                       # 0.698
CEIL_MEASURED = (SIGMA_COS ** 2 + SIGMA_REAL ** 2) / SIGMA_TOT ** 2   # 0.832

NAMES7 = ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "M_nu", "w0"]
PARAM_RANGES = {"Omega_m": (0.10, 0.50), "Omega_b": (0.03, 0.07), "h": (0.50, 0.90),
                "n_s": (0.80, 1.20), "sigma_8": (0.60, 1.00), "M_nu": (0.00, 1.00),
                "w0": (-1.30, -0.70)}

PREDICTIONS = """
PREDIZIONI DICHIARATE PRIMA DEL RUN
  Q1  I termini quadratici aggiungono < 0.05 di R^2 validato incrociato.
      Se aggiungessero molto, D5 diventa banale: e' non linearita', non
      "qualcosa di non parametrizzato".
  Q2  Le interazioni aggiungono < 0.03 oltre i quadratici.
  Q3  P(k) spiega SOSTANZIALMENTE piu' dei parametri: R^2_cv(P(k)) > 0.50,
      coerente con il 76.3% a due punti del Paper 1.
  Q4  La regressione dei residui su P(k) chiude piu' della meta' del divario
      lasciato dai sette parametri.
  Q5  R^2_cv(P(k)) resta SOTTO il tetto 0.832 dei predittori misurati.
      Se lo superasse, P(k) starebbe catturando anche il termine HOD, il che
      significherebbe che il cache non e' quello che credo.
Se una qualunque e' smentita, va registrata come smentita, non riscritta.
"""


# ---------------------------------------------------------------- I/O

def dig(rec, path):
    cur = rec
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def load_nh1(path):
    val = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            v = dig(json.loads(line), FIELD)
            if v is not None:
                val.append(float(v))
    return np.asarray(val, float)


def infer_names(raw):
    lo, hi = raw.min(axis=0), raw.max(axis=0)
    out, used = [], set()
    for j in range(raw.shape[1]):
        best, sc = None, None
        for nm, (a, b) in PARAM_RANGES.items():
            if nm in used:
                continue
            s = (abs(lo[j] - a) + abs(hi[j] - b)) / (b - a)
            if sc is None or s < sc:
                best, sc = nm, s
        out.append(best)
        used.add(best)
    return out


def append_atomic(path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


# ---------------------------------------------------------------- algebra

def zscore(X):
    m, s = X.mean(axis=0), X.std(axis=0)
    s = np.where(s > 0, s, 1.0)
    return (X - m) / s


def design(P, order):
    """order=1 lineare; 2 +quadrati; 3 +interazioni."""
    Z = zscore(P)
    cols = [Z]
    if order >= 2:
        cols.append(Z ** 2)
    if order >= 3:
        k = Z.shape[1]
        cols.append(np.column_stack([Z[:, i] * Z[:, j]
                                     for i, j in itertools.combinations(range(k), 2)]))
    return np.column_stack(cols)


def r2_fit(y, X):
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ beta
    return 1.0 - float((res ** 2).sum()) / float(((y - y.mean()) ** 2).sum())


def r2_cv(y, X, k=5, seed=0):
    """R^2 fuori campione: non premia l'overfitting."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(y))
    folds = np.array_split(idx, k)
    pred = np.empty_like(y)
    for f in folds:
        tr = np.setdiff1d(idx, f, assume_unique=False)
        A = np.column_stack([np.ones(len(tr)), X[tr]])
        beta, *_ = np.linalg.lstsq(A, y[tr], rcond=None)
        pred[f] = np.column_stack([np.ones(len(f)), X[f]]) @ beta
    res = y - pred
    return 1.0 - float((res ** 2).sum()) / float(((y - y.mean()) ** 2).sum())


def pca(X, ncomp):
    Z = zscore(X)
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    return U[:, :ncomp] * S[:ncomp], (S ** 2 / (S ** 2).sum())[:ncomp]


# ---------------------------------------------------------------- P(k)

def load_pk(path, n):
    """
    Il cache ha struttura ignota: si cerca l'array (n, nk) e, se c'e', il vettore k.
    Restituisce (Pk, kvec, diagnostica).
    """
    z = np.load(path, allow_pickle=False)
    keys = list(z.files)
    print("[pk] %s: chiavi = %s" % (os.path.basename(path), ", ".join(keys)))
    Pk = kv = None
    for key in keys:
        a = np.asarray(z[key])
        print("      %-20s shape=%s dtype=%s" % (key, a.shape, a.dtype))
        if a.ndim == 2 and n in a.shape and Pk is None:
            Pk = a if a.shape[0] == n else a.T
            pk_key = key
        elif a.ndim == 1 and kv is None and a.size > 5 and np.all(np.diff(a) > 0):
            kv = a
    if Pk is None:
        raise SystemExit("nessun array (%d, nk) trovato: passare --pk-key" % n)
    if kv is not None and kv.size != Pk.shape[1]:
        kv = None
    print("      -> uso '%s' come P(k): %d mock x %d bin" % (pk_key, *Pk.shape))
    if kv is not None:
        print("      -> vettore k trovato: %.4f - %.4f" % (kv.min(), kv.max()))
    else:
        print("      -> nessun vettore k identificato (non e' bloccante)")
    return Pk, kv


# ---------------------------------------------------------------- run

def run(a):
    print(PREDICTIONS)
    f = FROZEN[a.region]
    y = load_nh1(a.nh1 or f["path"])
    n = len(y)
    m, s = float(y.mean()), float(y.std(ddof=1))
    print("[gate] %s  n=%d  media=%.4f (atteso %.3f)  sd=%.4f (atteso %.3f)"
          % (a.region, n, m, f["mean"], s, f["sd"]))
    if abs(m - f["mean"]) > TOL or abs(s - f["sd"]) > TOL:
        sys.exit(3)
    print("       superato.\n")

    raw = np.genfromtxt(a.params)
    names = infer_names(raw)
    if names != NAMES7[:len(names)]:
        print("[param] ordine dedotto dai valori: %s" % ", ".join(names))
    P = raw[:n, :]

    rec = {"schema": "paper2_compD_nonlinear_v1", "region": a.region, "n": n,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "ceil_params": CEIL_PARAMS, "ceil_measured": CEIL_MEASURED}

    # ---------------- TEST A
    print("=" * 72)
    print("TEST A — non linearita' nei parametri")
    print("=" * 72)
    print("%-28s %6s %10s %10s" % ("modello", "termini", "R2", "R2 cv(5)"))
    prev_cv = 0.0
    for order, label in ((1, "lineare"), (2, "+ quadrati"), (3, "+ interazioni")):
        X = design(P, order)
        r2, rcv = r2_fit(y, X), r2_cv(y, X)
        print("%-28s %6d %10.4f %10.4f   (+%.4f cv)"
              % (label, X.shape[1], r2, rcv, rcv - prev_cv))
        rec["A_order%d" % order] = {"terms": int(X.shape[1]), "r2": r2, "r2_cv": rcv}
        prev_cv = rcv
    gain_quad = rec["A_order2"]["r2_cv"] - rec["A_order1"]["r2_cv"]
    gain_int = rec["A_order3"]["r2_cv"] - rec["A_order2"]["r2_cv"]
    print("\n  tetto per predittori parametrici: %.4f" % CEIL_PARAMS)
    print("  divario residuo dopo il modello completo: %.4f della varianza totale,"
          % (CEIL_PARAMS - rec["A_order3"]["r2_cv"]))
    print("  cioe' il %.1f%% della varianza cosmologica."
          % (100 * (CEIL_PARAMS - rec["A_order3"]["r2_cv"]) / CEIL_PARAMS))
    print("\n  Q1 (quadrati < 0.05): %s  (+%.4f)"
          % ("confermata" if gain_quad < 0.05 else "SMENTITA", gain_quad))
    print("  Q2 (interazioni < 0.03): %s  (+%.4f)"
          % ("confermata" if gain_int < 0.03 else "SMENTITA", gain_int))

    # ---------------- TEST B e C
    if a.pk and os.path.exists(a.pk):
        print("\n" + "=" * 72)
        print("TEST B — il due punti")
        print("=" * 72)
        Pk, kv = load_pk(a.pk, n)
        L = np.log(np.clip(Pk, 1e-30, None))
        print("\n%-10s %10s %10s %12s" % ("n comp.", "R2", "R2 cv(5)", "var. spiegata"))
        best = None
        for nc in [c for c in (1, 2, 3, 5, 8, 12, 20, 30) if c < min(L.shape)]:
            C, ev = pca(L, nc)
            r2, rcv = r2_fit(y, C), r2_cv(y, C)
            print("%-10d %10.4f %10.4f %12.4f" % (nc, r2, rcv, float(ev.sum())))
            rec["B_ncomp%d" % nc] = {"r2": r2, "r2_cv": rcv}
            if best is None or rcv > best[1]:
                best = (nc, rcv)
        print("\n  migliore: %d componenti, R2 cv = %.4f" % best)
        print("  tetto per predittori MISURATI: %.4f  (non 0.698)" % CEIL_MEASURED)
        print("  quota del tetto raggiunta: %.1f%%" % (100 * best[1] / CEIL_MEASURED))
        print("\n  Q3 (R2 cv > 0.50): %s  (%.4f)"
              % ("confermata" if best[1] > 0.50 else "SMENTITA", best[1]))
        print("  Q5 (sotto il tetto 0.832): %s  (%.4f)"
              % ("confermata" if best[1] < CEIL_MEASURED else "SMENTITA", best[1]))
        rec["B_best_ncomp"], rec["B_best_r2cv"] = int(best[0]), float(best[1])

        print("\n" + "=" * 72)
        print("TEST C — quanta parte del divario chiude P(k)")
        print("=" * 72)
        Xlin = design(P, 1)
        A = np.column_stack([np.ones(n), Xlin])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ beta
        gap_before = CEIL_PARAMS - rec["A_order1"]["r2_cv"]
        C, _ = pca(L, best[0])
        r2_res = r2_cv(resid, C)
        var_frac = float((resid ** 2).sum()) / float(((y - y.mean()) ** 2).sum())
        closed = r2_res * var_frac
        print("  varianza residua dopo i 7 parametri: %.4f del totale" % var_frac)
        print("  R2 cv dei residui su P(k):           %.4f" % r2_res)
        print("  varianza totale chiusa da P(k):      %.4f" % closed)
        print("  divario cosmologico da chiudere:     %.4f" % gap_before)
        frac = closed / gap_before if gap_before > 0 else float("nan")
        print("  quota del divario chiusa:            %.1f%%" % (100 * frac))
        rec["C_resid_r2cv"], rec["C_gap_closed_frac"] = r2_res, float(frac)
        print("\n  Q4 (chiude > meta' del divario): %s  (%.1f%%)"
              % ("confermata" if frac > 0.5 else "SMENTITA", 100 * frac))
        print("\n  LETTURA:")
        if frac > 0.7:
            print("    P(k) chiude il divario: N_H1 e' in larga misura una statistica")
            print("    del DUE PUNTI, e i sette parametri fallivano solo perche' la mappa")
            print("    parametri -> P(k) non e' lineare.  D5 va riformulata di conseguenza.")
        elif frac > 0.3:
            print("    P(k) chiude una parte sostanziale ma non tutto.  Riportare entrambi")
            print("    i numeri: quota a due punti e quota residua.")
        else:
            print("    P(k) NON chiude il divario: la parte non spiegata e' OLTRE il due")
            print("    punti, e va collegata al residuo beyond-two-point di 1710 generatori")
            print("    del Paper 1.  E' l'esito piu' forte, e il piu' da verificare.")
    else:
        print("\n[pk] cache non fornito o inesistente: TEST B e C saltati.")
        print("     Attesi in %s" % (a.pk or "results/phase7_pk_nwlh_cache.npz"))

    if a.out:
        append_atomic(a.out, rec)
        print("\nscritto in %s" % a.out)


# ---------------------------------------------------------------- selftest

def selftest():
    print("=== selftest ===")
    rng = np.random.default_rng(3)
    n = 2000
    P = rng.uniform(-1, 1, (n, 7))
    ok = True

    # caso 1: risposta puramente lineare -> i quadrati non devono aggiungere nulla
    y1 = 35436.0 + 300 * (0.45 * P[:, 3] + 0.18 * P[:, 0]) + rng.normal(0, 172, n)
    g = r2_cv(y1, design(P, 2)) - r2_cv(y1, design(P, 1))
    print("  lineare puro : guadagno dai quadrati = %+.4f  (deve essere ~0)" % g)
    ok &= abs(g) < 0.01

    # caso 2: risposta quadratica nascosta -> i quadrati devono catturarla
    y2 = 35436.0 + 300 * (0.5 * P[:, 3] ** 2 + 0.2 * P[:, 0]) + rng.normal(0, 172, n)
    g2 = r2_cv(y2, design(P, 2)) - r2_cv(y2, design(P, 1))
    print("  quadratico   : guadagno dai quadrati = %+.4f  (deve essere grande)" % g2)
    ok &= g2 > 0.05

    # caso 3: la CV non premia l'overfitting
    ynoise = rng.normal(0, 1, n)
    r2g, r2c = r2_fit(ynoise, design(P, 3)), r2_cv(ynoise, design(P, 3))
    print("  rumore puro  : R2 grezzo = %+.4f, R2 cv = %+.4f  (cv deve essere <= 0)"
          % (r2g, r2c))
    ok &= (r2g > 0.005 and r2c < 0.01)

    # caso 4: PCA + regressione su un predittore ad alta dimensione
    B = rng.normal(0, 1, (n, 60))
    y4 = 35436.0 + 400 * B[:, :3].sum(axis=1) / 3 + rng.normal(0, 172, n)
    C, ev = pca(B, 8)
    print("  PCA          : R2 cv su 8 componenti = %.4f (var. spiegata %.3f)"
          % (r2_cv(y4, C), float(ev.sum())))

    print("  tetti: parametri %.4f, misurati %.4f" % (CEIL_PARAMS, CEIL_MEASURED))
    print("=== selftest %s ===" % ("PASSATO" if ok else "FALLITO"))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    p.add_argument("--nh1", default=None)
    p.add_argument("--params",
                   default="data/raw/quijote/3D_cubes/latin_hypercube_nwLH/"
                           "latin_hypercube_nwLH_params.txt")
    p.add_argument("--pk", default="results/phase7_pk_nwlh_cache.npz")
    p.add_argument("--out", default=None)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not os.path.exists(a.params):
        raise SystemExit("file parametri non trovato: %s" % a.params)
    run(a)


if __name__ == "__main__":
    main()

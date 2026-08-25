#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n1c_bandpower.py

N1c - N_H1 CONTRO LO SPETTRO BINNATO COMPLETO

STATO DA N1b (tutti i cancelli superati, misura affidabile)
-----------------------------------------------------------
  f_half mock = 0.68023  vs 0.680 pubblicato da M26     -> allineato
  f_half DESI = 0.57540  vs 0.570 pubblicato da M26     -> allineato
  sigma dentro maschera: DESI 2.686, mock 2.086 +/- 0.113
  relazione N_H1 = 24445 + 16174 * f_half, dispersione 250.7
  DESI: predetto 33752, osservato 28256, residuo -5496 = -21.9 dispersioni
  frazione del deficit spiegata da f_half: 23.6%

DUE PROBLEMI DI N1b
-------------------
1. EXTRAPOLAZIONE. f_half di DESI e' 13.8 sigma sotto la media dei mock e fuori
   dal loro intervallo [0.663, 0.697]. La relazione e' calibrata su un'ampiezza
   di 0.035 e si extrapola di 0.105: tre volte. Per spiegare tutto il deficit
   servirebbe una pendenza di 68600 contro le 16174 misurate, cioe' una
   relazione 4.2 volte piu' ripida fuori che dentro. Non impossibile per una
   risposta non lineare, e non accettabile come assunzione.

2. BANDA SCELTA A MANO. f_three_q correla a r = +0.790 contro 0.443 di f_half:
   e' un predittore molto migliore e non era nell'analisi del piano. Una
   singola banda e' un riassunto povero di P(k).

COSA FA QUESTO SCRIPT
---------------------
Regredisce N_H1 sull'INTERO spettro binnato (16 bande logaritmiche in k), che e'
la forma corretta della domanda di Referee 3: la funzione a due punti predice
N_H1? Con in piu':

  - PCA sulle potenze di banda standardizzate, per stabilita' (le bande sono
    fortemente correlate fra loro)
  - R^2 in validazione incrociata K-fold, per non spacciare overfitting per
    potere predittivo
  - DISTANZA DI MAHALANOBIS di DESI nello spazio delle bande: misura quanto si
    sta extrapolando, invece di dichiararlo a parole
  - la posizione di DESI: predizione, residuo in unita' della dispersione
    attorno alla relazione, frazione del deficit spiegata

Risponde anche a R3.4 ("valore aggiunto rispetto a P(k)+PDF"): se le bande
spiegano una frazione X della varianza di N_H1 fra i mock e DESI cade comunque
fuori, quella X e' la quantificazione richiesta. Aggiungendo i momenti del campo
(sigma, curtosi) si copre anche la PDF.

Sorgente dei campi: results/phase8_test2_fields/test2_XXXX.npz['delta'] (che
contiene nu), indici >= 200. Append-only JSONL, resumable.

USO
---
  python src\\paper1_rev_n1c_bandpower.py --k 50
  python src\\paper1_rev_n1c_bandpower.py
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

DESI_NH1 = 28256.0
NH1 = "base.N_H1"
N_BINS = 16
MIN_IDX = 200


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


def read_jsonl(path):
    recs = []
    if not Path(path).exists():
        return recs
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    return recs


def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")
        f.flush(); os.fsync(f.fileno())


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


_G = {}


def bandsetup(ngrid, cell, nbins):
    key = (ngrid, round(cell, 9), nbins)
    if key in _G:
        return _G[key]
    kf = 2.0 * np.pi * np.fft.fftfreq(ngrid, d=cell)
    kz = 2.0 * np.pi * np.fft.rfftfreq(ngrid, d=cell)
    KX, KY, KZ = np.meshgrid(kf, kf, kz, indexing="ij")
    kmag = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
    w = np.full(kmag.shape, 2.0)
    w[..., 0] = 1.0
    if ngrid % 2 == 0:
        w[..., -1] = 1.0
    knq = np.pi / cell
    kmin = 2.0 * np.pi / (ngrid * cell) * 1.5
    edges = np.logspace(np.log10(kmin), np.log10(knq), nbins + 1)
    lab = np.digitize(kmag, edges) - 1
    valid = (lab >= 0) & (lab < nbins) & (kmag > 0)
    kc = np.array([kmag[valid & (lab == b)].mean() if (valid & (lab == b)).any()
                   else np.nan for b in range(nbins)])
    _G[key] = (kmag, w, lab, valid, edges, kc)
    return _G[key]


def band_summary(nu, cell, mask, nbins=N_BINS):
    ngrid = nu.shape[0]
    kmag, w, lab, valid, edges, kc = bandsetup(ngrid, cell, nbins)
    F = np.fft.rfftn(nu.astype(np.float64))
    P = (F.real ** 2 + F.imag ** 2) * w
    bp = np.full(nbins, np.nan)
    for b in range(nbins):
        s = valid & (lab == b)
        if s.any():
            bp[b] = float(P[s].sum() / w[s].sum())
    v = nu[mask]
    sd = float(v.std())
    return {"bp": bp.tolist(), "k_centers": kc.tolist(),
            "sigma_in_mask": sd,
            "kurt_in_mask": (float(((v - v.mean()) ** 4).mean() / sd ** 4 - 3.0)
                             if sd > 0 else np.nan),
            "skew_in_mask": (float(((v - v.mean()) ** 3).mean() / sd ** 3)
                             if sd > 0 else np.nan)}


def cv_r2(X, y, k=5, seed=0):
    """R^2 in validazione incrociata K-fold su regressione lineare."""
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    order = rng.permutation(n)
    folds = np.array_split(order, k)
    pred = np.empty(n)
    for f in folds:
        tr = np.setdiff1d(order, f)
        A = np.column_stack([np.ones(tr.size), X[tr]])
        b, *_ = np.linalg.lstsq(A, y[tr], rcond=None)
        pred[f] = np.column_stack([np.ones(f.size), X[f]]) @ b
    ss = ((y - y.mean()) ** 2).sum()
    return 1.0 - ((y - pred) ** 2).sum() / ss, pred


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=0)
    ap.add_argument("--min_idx", type=int, default=MIN_IDX)
    ap.add_argument("--n_pc", type=int, default=0,
                    help="0 = scelta automatica al 99% di varianza")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    fields = res / "phase8_test2_fields"
    outj = res / "paper1" / "n1c_bands_NGC.jsonl"
    desi_cache = res / "paper1" / "n1_desi_nu_NGC.npy"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    mask = np.load(root / "data" / "processed" / "phase6_fields" /
                   "bgs_ngc_mask_128.npy").astype(bool)

    print("=" * 78)
    print(f"N1c - spettro binnato ({N_BINS} bande), indici >= {args.min_idx}")
    print("=" * 78)

    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            kk = int(fl.get("key", j))
        except (TypeError, ValueError):
            kk = j
        nh1[kk] = float(fl.get(NH1, np.nan))

    # -------------------------------------------------- DESI
    if not desi_cache.exists():
        print("  [FATAL] cache del campo nu di DESI assente: esegui prima N1b")
        return
    nu_d = np.load(desi_cache)
    chk = float(M.compute_tda_features(nu_d, mask, M.N_THRESH, masked=True)[4])
    print(f"\n[A] DESI: N_H1 = {chk:.0f}  atteso {DESI_NH1:.0f}  "
          f"{'OK' if abs(chk-DESI_NH1)<0.5 else 'FALLITO'}")
    if abs(chk - DESI_NH1) > 0.5:
        return
    d = band_summary(nu_d, M.CELL, mask)

    # -------------------------------------------------- mock
    allf = [(int(p.stem.split("_")[1]), p)
            for p in sorted(fields.glob("test2_*.npz"))]
    usable = [(i, p) for i, p in allf if i >= args.min_idx]
    done = {r["idx"] for r in read_jsonl(outj)}
    todo = [(i, p) for i, p in usable if i not in done]
    if args.k > 0:
        todo = todo[:args.k]
    print(f"\n[B] BANDE: {len(usable)} campi, {len(done)} fatti, "
          f"{len(todo)} da fare")
    t0 = time.time()
    for n, (i, p) in enumerate(todo, 1):
        s = band_summary(np.load(p)["delta"], M.CELL, mask)
        s["idx"] = i
        append_jsonl(outj, s)
        if n % 50 == 0 or n == 1:
            print(f"    [{n}/{len(todo)}] idx={i}  ETA "
                  f"{(time.time()-t0)/n*(len(todo)-n)/60:.1f} min")

    recs = read_jsonl(outj)
    spec = {r["idx"]: r for r in recs}
    idx = sorted(i for i in spec if i in nh1 and np.isfinite(nh1[i]))
    if len(idx) < 40:
        print(f"  solo {len(idx)} campi: troppo pochi.")
        return

    y = np.array([nh1[i] for i in idx])
    B = np.log10(np.array([spec[i]["bp"] for i in idx], float))
    bd = np.log10(np.array(d["bp"], float))
    kc = np.array(spec[idx[0]]["k_centers"], float)
    good = np.all(np.isfinite(B), axis=0) & np.isfinite(bd)
    B, bd, kc = B[:, good], bd[good], kc[good]
    print(f"\n[C] ANALISI   mock={len(idx)}   bande valide={int(good.sum())}")
    print(f"  N_H1 mock {y.mean():.1f} +/- {y.std(ddof=1):.1f}")

    # -------------------------------------------------- extrapolazione
    mu, sd = B.mean(axis=0), B.std(axis=0, ddof=1)
    zd = (bd - mu) / sd
    print(f"\n  DESI banda per banda (z rispetto ai mock):")
    print(f"    {'k [h/Mpc]':>11s} {'mock log10P':>12s} {'DESI':>10s} {'z':>8s}")
    for j in range(len(kc)):
        print(f"    {kc[j]:>11.4f} {mu[j]:>12.4f} {bd[j]:>10.4f} {zd[j]:>+8.2f}")

    C = np.cov(B, rowvar=False)
    Ci = np.linalg.pinv(C)
    dv = bd - mu
    maha = float(np.sqrt(max(dv @ Ci @ dv, 0.0)))
    print(f"\n  distanza di Mahalanobis di DESI nello spazio delle bande: "
          f"{maha:.1f}")
    print(f"    (per riferimento, i mock stanno tipicamente a "
          f"{np.median([np.sqrt((b-mu)@Ci@(b-mu)) for b in B]):.1f})")
    print(f"  -> misura quanto si sta extrapolando. Un valore molto grande")
    print(f"     significa che la relazione dei mock non e' calibrata dove")
    print(f"     DESI vive, e va detto nel paper.")

    # -------------------------------------------------- PCA + regressione
    Bs = (B - mu) / sd
    U, S, Vt = np.linalg.svd(Bs, full_matrices=False)
    ev = S ** 2 / (S ** 2).sum()
    npc = args.n_pc or int(np.searchsorted(np.cumsum(ev), 0.99) + 1)
    npc = max(1, min(npc, Bs.shape[1]))
    # guardrail: con pochi mock, 15 componenti producono overfitting e un
    # R^2 validato negativo. Serve almeno ~20 mock per componente.
    cap = max(1, Bs.shape[0] // 20)
    if npc > cap:
        print(f"\n  *** {Bs.shape[0]} mock non bastano per {npc} componenti:")
        print(f"      limito a {cap} (regola: >=20 mock per componente).")
        print(f"      Per l'analisi definitiva serve il set completo (~1800),")
        print(f"      non un pilota: con 50 mock questo test non e' eseguibile.")
        npc = cap
    print(f"\n  PCA: {npc} componenti spiegano "
          f"{100*np.cumsum(ev)[npc-1]:.2f}% della varianza spettrale")
    Z = Bs @ Vt[:npc].T
    zd_pc = ((bd - mu) / sd) @ Vt[:npc].T

    A = np.column_stack([np.ones(Z.shape[0]), Z])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred_in = A @ beta
    r2 = 1.0 - ((y - pred_in) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    r2cv, _ = cv_r2(Z, y, k=5, seed=1)
    sr = float(np.std(y - pred_in, ddof=npc + 1))
    print(f"  R^2 in campione   = {r2:.4f}")
    print(f"  R^2 validato (5-fold) = {r2cv:.4f}   <- questo e' il numero onesto")
    print(f"  dispersione attorno alla relazione = {sr:.1f}")

    pred_desi = float(beta[0] + zd_pc @ beta[1:])
    resid = DESI_NH1 - pred_desi
    deficit = float(y.mean()) - DESI_NH1
    frac = (float(y.mean()) - pred_desi) / deficit if deficit else np.nan

    print("\n" + "=" * 78)
    print("RISULTATO: N_H1 CONTRO LO SPETTRO COMPLETO")
    print("=" * 78)
    print(f"  media mock            : {y.mean():.0f}")
    print(f"  predetto per DESI     : {pred_desi:.0f}")
    print(f"  osservato             : {DESI_NH1:.0f}")
    print(f"  deficit totale        : {deficit:.0f}")
    print(f"  residuo dalla relazione: {resid:+.0f}  = {resid/sr:+.1f} dispersioni")
    print(f"  frazione del deficit spiegata dallo SPETTRO: {100*frac:.1f}%")

    # -------------------------------------------------- + momenti (PDF)
    print(f"\n  aggiungendo i momenti del campo (copre R3.4: P(k)+PDF):")
    mom = np.column_stack([[spec[i]["sigma_in_mask"] for i in idx],
                           [spec[i]["kurt_in_mask"] for i in idx],
                           [spec[i]["skew_in_mask"] for i in idx]])
    md = np.array([d["sigma_in_mask"], d["kurt_in_mask"], d["skew_in_mask"]])
    mm, ms = mom.mean(axis=0), mom.std(axis=0, ddof=1)
    Z2 = np.column_stack([Z, (mom - mm) / ms])
    zd2 = np.concatenate([zd_pc, (md - mm) / ms])
    A2 = np.column_stack([np.ones(Z2.shape[0]), Z2])
    b2, *_ = np.linalg.lstsq(A2, y, rcond=None)
    p2 = A2 @ b2
    r2_2 = 1.0 - ((y - p2) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    r2cv2, _ = cv_r2(Z2, y, k=5, seed=1)
    sr2 = float(np.std(y - p2, ddof=Z2.shape[1] + 1))
    pd2 = float(b2[0] + zd2 @ b2[1:])
    frac2 = (float(y.mean()) - pd2) / deficit if deficit else np.nan
    print(f"    R^2 validato = {r2cv2:.4f}  (solo spettro: {r2cv:.4f})")
    print(f"    predetto {pd2:.0f}   residuo {DESI_NH1-pd2:+.0f} = "
          f"{(DESI_NH1-pd2)/sr2:+.1f} dispersioni")
    print(f"    frazione del deficit spiegata da P(k)+PDF: {100*frac2:.1f}%")

    print("\n" + "=" * 78)
    print("LETTURA")
    print("=" * 78)
    print(f"  Il residuo di DESI e' il contenuto NON riconducibile al due-punti")
    print(f"  ne' alla PDF, misurato: {DESI_NH1-pd2:+.0f} generatori.")
    print(f"  R^2 validato di {r2cv2:.3f} e' anche la risposta a R3.4: e' quanto")
    print(f"  P(k)+PDF predicono di N_H1 fra i mock.")
    if maha > 10:
        print(f"\n  MA la distanza di Mahalanobis {maha:.0f} dice che DESI vive")
        print(f"  molto fuori dallo spazio spettrale campionato dai mock. La")
        print(f"  predizione e' un'EXTRAPOLAZIONE e la frazione qui sopra")
        print(f"  dipende da un'assunzione di linearita' su quella distanza.")
        print(f"  Nel paper va dichiarato, e N10 (fasi randomizzate a spettro")
        print(f"  FISSATO, senza extrapolare) diventa il test decisivo.")

    atomic_write_json(res / "paper1" / "n1c_report_NGC.json", {
        "script": "paper1_rev_n1c_bandpower.py", "n_mock": len(idx),
        "n_bande": int(good.sum()), "n_pc": npc,
        "k_centers": kc.tolist(), "desi_z_per_banda": zd.tolist(),
        "mahalanobis_desi": maha,
        "r2_in_campione": float(r2), "r2_cv": float(r2cv),
        "dispersione": sr, "mock_nh1_mean": float(y.mean()),
        "nh1_predetto_spettro": pred_desi,
        "residuo_spettro": float(resid),
        "residuo_in_sigma": float(resid / sr),
        "frazione_deficit_spettro": float(frac),
        "r2_cv_spettro_piu_pdf": float(r2cv2),
        "nh1_predetto_spettro_pdf": pd2,
        "frazione_deficit_spettro_pdf": float(frac2),
        "residuo_spettro_pdf": float(DESI_NH1 - pd2)})
    print(f"\n  report: {res/'paper1'/'n1c_report_NGC.json'}")


if __name__ == "__main__":
    main()

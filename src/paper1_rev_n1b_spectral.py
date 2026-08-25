#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n1b_spectral.py

N1b - PIANO (P_small, N_H1): VERSIONE CORRETTA

PERCHE' LA PRIMA VERSIONE ERA INVALIDA
--------------------------------------
paper1_rev_n1_spectral.py ha letto i campi dei mock da
data/processed/paper1_mock_deltas/NGC/delta_XXXX.npy, che contengono DELTA e non
NU. Il nome lo diceva. Diagnosi dal report:

    sigma dentro maschera:  DESI 2.69   mock 54.2      -> fattore 20
    f_half:                 DESI 0.5754 mock 0.868
    M26 quota:              DESI 0.570  mock 0.680

Il campo nu e' log(1+delta) lisciato e centrato: 2.69 e' plausibile per DESI
(delta arriva a ~150, log(151)=5.0), 54 non lo e'. Coerente con quanto gia'
visto in v2h: fra i due cache Pearson 0.35 e Spearman 0.9996, cioe' una
relazione monotona fortemente non lineare - il logaritmo. Stesso N_H1 per
invarianza monotona, ampiezze incomparabili.

Conseguenza: la prima versione correlava lo spettro dei DELTA dei mock con lo
spettro del NU di DESI. Da qui correlazioni negative dove la fisica ne vuole
positive, frazione di deficit spiegata -57% e residuo a -46 sigma.

Due conferme utili si salvano:
  - f_half di DESI = 0.5754 contro 0.570 di M26: il lato dati e' corretto
    all'1%, e l'autocontrollo su N_H1 = 28256 era passato.
  - mock a 0.868 contro 0.680: conferma la diagnosi dal lato opposto.

LA FONTE GIUSTA
---------------
phase8_test2_masked.py salva:
    np.savez(out_fields / f"test2_{i:04d}.npz", delta=nu)
La chiave si chiama 'delta' ma contiene NU. Sono i campi che hanno prodotto i
valori congelati di N_H1, quindi per costruzione quelli giusti.

Vincolo noto: gli indici 0-199 sono i cubi del run con HOD diverso (vedi
paper1_sigma_discrepancy_resolution.md). Si parte da 200: 1800 mock puliti.

AUTOCONTROLLO SU ENTRAMBI I LATI
--------------------------------
L'errore della prima versione e' stato validare il lato DESI e non quello mock.
Qui:
  A. DESI: build_field ricostruito -> compute_tda_features deve dare 28256
  B. MOCK: su --n_check campi, compute_tda_features deve dare ESATTAMENTE il
     valore in per_mock_NGC_R5.jsonl
  C. COERENZA: sigma dentro maschera di DESI e dei mock entro un fattore 3
Se uno dei tre fallisce, lo script si ferma prima di calcolare spettri.

Validazione attesa in aggiunta: la f_half media dei mock deve venire ~0.68,
riproducendo il numero di M26. Se viene, l'intero impianto e' allineato.

Append-only JSONL, resumable.

USO
---
  python src\\paper1_rev_n1b_spectral.py --k 50     # pilota
  python src\\paper1_rev_n1b_spectral.py            # tutti
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

DESI_NH1 = {"NGC": 28256.0, "SGC": 15122.0}
M26_FHALF = {"desi": 0.570, "mock": 0.680}
NH1 = "base.N_H1"
MIN_IDX = 200          # 0-199 contaminati dal run con HOD diverso


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


_KC = {}


def kgrid(ngrid, cell):
    key = (ngrid, round(cell, 9))
    if key in _KC:
        return _KC[key]
    kf = 2.0 * np.pi * np.fft.fftfreq(ngrid, d=cell)
    kz = 2.0 * np.pi * np.fft.rfftfreq(ngrid, d=cell)
    KX, KY, KZ = np.meshgrid(kf, kf, kz, indexing="ij")
    kmag = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
    w = np.full(kmag.shape, 2.0)
    w[..., 0] = 1.0
    if ngrid % 2 == 0:
        w[..., -1] = 1.0
    _KC[key] = (kmag, w)
    return kmag, w


def spectral_summary(nu, cell, mask):
    ngrid = nu.shape[0]
    kmag, w = kgrid(ngrid, cell)
    F = np.fft.rfftn(nu.astype(np.float64))
    P = (F.real ** 2 + F.imag ** 2) * w
    knq = np.pi / cell
    pos = kmag > 0
    tot = float(P[pos].sum())
    out = {"P_tot": tot}
    for fr, nm in ((0.5, "f_half"), (0.25, "f_quarter"), (0.75, "f_three_q")):
        sel = pos & (kmag > fr * knq)
        out[nm] = float(P[sel].sum()) / tot if tot > 0 else np.nan
        if nm == "f_half":
            out["P_small_abs"] = float(P[sel].sum())
    b1 = pos & (kmag > 0.10 * knq) & (kmag <= 0.20 * knq)
    b2 = pos & (kmag > 0.40 * knq) & (kmag <= 0.80 * knq)
    if b1.any() and b2.any():
        p1, p2 = P[b1].mean(), P[b2].mean()
        k1, k2 = kmag[b1].mean(), kmag[b2].mean()
        out["slope_eff"] = (float(np.log(p2 / p1) / np.log(k2 / k1))
                            if p1 > 0 and p2 > 0 else np.nan)
    else:
        out["slope_eff"] = np.nan
    v = nu[mask]
    sd = float(v.std())
    out["sigma_in_mask"] = sd
    out["kurt_in_mask"] = (float(((v - v.mean()) ** 4).mean() / sd ** 4 - 3.0)
                           if sd > 0 else np.nan)
    return out


def corr_ci(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    n = int(m.sum())
    if n < 8:
        return None
    r = float(np.corrcoef(x[m], y[m])[0, 1])
    r = min(max(r, -0.999999), 0.999999)
    zf = 0.5 * np.log((1 + r) / (1 - r))
    se = 1.0 / np.sqrt(n - 3)
    return {"r": r, "n": n, "sigma": float(abs(zf) / se),
            "ic95": [float(np.tanh(zf - 1.96 * se)),
                     float(np.tanh(zf + 1.96 * se))]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=0)
    ap.add_argument("--min_idx", type=int, default=MIN_IDX)
    ap.add_argument("--n_check", type=int, default=3)
    ap.add_argument("--analyze_only", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    fields = res / "phase8_test2_fields"
    outj = res / "paper1" / "n1b_spectra_NGC.jsonl"
    desi_cache = res / "paper1" / "n1_desi_nu_NGC.npy"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M

    mask = np.load(root / "data" / "processed" / "phase6_fields" /
                   "bgs_ngc_mask_128.npy").astype(bool)
    print("=" * 78)
    print("N1b - NGC   (campi nu da phase8_test2_fields, indici >= "
          f"{args.min_idx})")
    print("=" * 78)

    # riferimento N_H1 congelato
    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            k = int(fl.get("key", j))
        except (TypeError, ValueError):
            k = j
        nh1[k] = float(fl.get(NH1, np.nan))

    # ---------------------------------------------------- A. autocontrollo DESI
    print("\n[A] AUTOCONTROLLO DESI")
    if desi_cache.exists():
        nu_d = np.load(desi_cache)
        print(f"  da cache: {desi_cache}")
    else:
        print("  ricostruzione da FITS...")
        fr, swr = M.load_desi_random_field()
        fd, swd = M.load_desi_data_field()
        nu_d = M.build_field(fd, fr, swd / swr, mask)
        np.save(desi_cache, nu_d)
    v = float(M.compute_tda_features(nu_d, mask, M.N_THRESH, masked=True)[4])
    print(f"  N_H1 = {v:.0f}  atteso {DESI_NH1['NGC']:.0f}   "
          f"{'OK' if abs(v-DESI_NH1['NGC'])<0.5 else 'FALLITO'}")
    if abs(v - DESI_NH1["NGC"]) > 0.5:
        print("  *** mi fermo ***")
        return
    d_spec = spectral_summary(nu_d, M.CELL, mask)
    print(f"  f_half = {d_spec['f_half']:.5f}  (M26 quota {M26_FHALF['desi']})")
    print(f"  sigma dentro maschera = {d_spec['sigma_in_mask']:.4f}")

    # ---------------------------------------------------- B. autocontrollo MOCK
    print(f"\n[B] AUTOCONTROLLO MOCK  (l'errore della prima versione)")
    if not fields.exists():
        print(f"  [FATAL] {fields} non trovata")
        return
    allf = sorted(fields.glob("test2_*.npz"))
    usable = [(int(p.stem.split("_")[1]), p) for p in allf]
    usable = [(i, p) for i, p in usable if i >= args.min_idx]
    print(f"  {len(allf)} campi totali, {len(usable)} con indice >= "
          f"{args.min_idx}")
    if not usable:
        print("  [FATAL] nessun campo utilizzabile")
        return

    ok = True
    for i, p in usable[:args.n_check]:
        nu = np.load(p)["delta"]
        got = float(M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)[4])
        exp = nh1.get(i, np.nan)
        s = spectral_summary(nu, M.CELL, mask)
        buono = np.isfinite(exp) and abs(got - exp) < 0.5
        print(f"  idx {i}: N_H1 ricalcolato {got:.0f}  JSONL {exp:.0f}  "
              f"{'OK' if buono else '*** DISCORDE ***'}   "
              f"sigma={s['sigma_in_mask']:.4f}  f_half={s['f_half']:.5f}")
        ok &= buono
        rap = s["sigma_in_mask"] / d_spec["sigma_in_mask"]
        if not (1/3 < rap < 3):
            print(f"    *** sigma incompatibile con DESI (rapporto "
                  f"{rap:.2f}): campo di natura diversa ***")
            ok = False
    if not ok:
        print("\n  *** AUTOCONTROLLO MOCK FALLITO: mi fermo. ***")
        print("  Non calcolo spettri di campi che non riproducono i valori")
        print("  congelati o che hanno ampiezza incompatibile con DESI.")
        return
    print("  autocontrollo mock superato.")

    # ---------------------------------------------------- spettri
    if not args.analyze_only:
        print("\n[C] SPETTRI (append-only, resumable)")
        done = {r["idx"] for r in read_jsonl(outj)}
        todo = [(i, p) for i, p in usable if i not in done]
        if args.k > 0:
            todo = todo[:args.k]
        print(f"  {len(done)} gia' fatti, {len(todo)} da fare")
        t0 = time.time()
        for n, (i, p) in enumerate(todo, 1):
            s = spectral_summary(np.load(p)["delta"], M.CELL, mask)
            s["idx"] = i
            append_jsonl(outj, s)
            if n % 50 == 0 or n == 1:
                el = time.time() - t0
                print(f"    [{n}/{len(todo)}] idx={i} f_half={s['f_half']:.5f} "
                      f"ETA {el/n*(len(todo)-n)/60:.1f} min")
        if todo:
            print(f"  fatto in {(time.time()-t0)/60:.1f} min")

    # ---------------------------------------------------- analisi
    print("\n[D] ANALISI")
    spec = {r["idx"]: r for r in read_jsonl(outj)}
    idx = sorted(i for i in spec if i in nh1 and np.isfinite(nh1[i]))
    if len(idx) < 30:
        print(f"  solo {len(idx)} spettri: troppo pochi.")
        return
    y = np.array([nh1[i] for i in idx])
    print(f"  mock: {len(idx)}   N_H1 {y.mean():.1f} +/- {y.std(ddof=1):.1f}")

    fh = np.array([spec[i]["f_half"] for i in idx])
    print(f"  f_half mock: {fh.mean():.5f} +/- {fh.std(ddof=1):.5f}")
    print(f"  M26 quota ~{M26_FHALF['mock']} -> "
          f"{'ALLINEATO' if abs(fh.mean()-M26_FHALF['mock'])<0.03 else 'NON allineato: verificare'}")

    rep = {"script": "paper1_rev_n1b_spectral.py", "n_mock": len(idx),
           "min_idx": args.min_idx, "desi": d_spec,
           "desi_nh1": DESI_NH1["NGC"], "m26_fhalf_citato": M26_FHALF,
           "mock_nh1_mean": float(y.mean()),
           "mock_nh1_std": float(y.std(ddof=1)),
           "correlazioni": {}, "piano": {}}

    print(f"\n  correlazioni con N_H1:")
    for v in ("f_half", "f_quarter", "f_three_q", "slope_eff",
              "sigma_in_mask", "P_small_abs", "kurt_in_mask"):
        x = np.array([spec[i].get(v, np.nan) for i in idx], float)
        c = corr_ci(x, y)
        if c:
            print(f"    {v:>14s} r={c['r']:+.4f} "
                  f"[{c['ic95'][0]:+.4f},{c['ic95'][1]:+.4f}] {c['sigma']:.1f}s")
            rep["correlazioni"][v] = c

    print("\n" + "=" * 78)
    print("DOVE CADE DESI")
    print("=" * 78)
    for v in ("f_half", "f_quarter", "sigma_in_mask"):
        x = np.array([spec[i].get(v, np.nan) for i in idx], float)
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 30 or v not in d_spec:
            continue
        xx, yy = x[m], y[m]
        xd = float(d_spec[v])
        below = int((xx < xd).sum())
        fuori = xd < xx.min() or xd > xx.max()
        A = np.column_stack([np.ones(xx.size), xx])
        b, *_ = np.linalg.lstsq(A, yy, rcond=None)
        sr = float(np.std(yy - A @ b, ddof=2))
        pred = float(b[0] + b[1] * xd)
        obs = DESI_NH1["NGC"]
        defi = float(yy.mean()) - obs
        frac = (float(yy.mean()) - pred) / defi if defi else np.nan
        print(f"\n  --- {v}")
        print(f"    mock  {xx.mean():.5f} +/- {xx.std(ddof=1):.5f}   "
              f"range [{xx.min():.5f}, {xx.max():.5f}]")
        print(f"    DESI  {xd:.5f}   rank {below+1}/{xx.size+1}"
              f"   {'*** FUORI RANGE ***' if fuori else ''}")
        print(f"    relazione: N_H1 = {b[0]:.1f} + {b[1]:.1f} x {v}   "
              f"(dispersione {sr:.1f})")
        print(f"    predetto {pred:.0f}   osservato {obs:.0f}   "
              f"residuo {obs-pred:+.0f} = {(obs-pred)/sr:+.2f} disp.")
        print(f"    frazione del deficit spiegata: {100*frac:.1f}%")
        rep["piano"][v] = {
            "mock_mean": float(xx.mean()), "mock_std": float(xx.std(ddof=1)),
            "mock_min": float(xx.min()), "mock_max": float(xx.max()),
            "desi": xd, "rank_desi": f"{below+1}/{xx.size+1}",
            "desi_fuori_range": bool(fuori), "intercetta": float(b[0]),
            "pendenza": float(b[1]), "dispersione_relazione": sr,
            "nh1_predetto": pred, "nh1_osservato": obs,
            "residuo": float(obs - pred),
            "residuo_in_sigma": float((obs - pred) / sr),
            "frazione_deficit_spiegata": float(frac)}

    p = rep["piano"].get("f_half")
    if p:
        fr, rs = p["frazione_deficit_spiegata"], abs(p["residuo_in_sigma"])
        print("\n" + "=" * 78)
        print("LETTURA")
        print("=" * 78)
        print(f"  spettro spiega {100*fr:.1f}% del deficit; residuo {rs:.1f} disp.")
        if fr > 1.15:
            print("  -> LO SPETTRO SOVRAPREDICE: DESI ha PIU' loop di quanti la")
            print("     sua potenza a piccola scala ne preveda. Il due-punti")
            print("     basta e avanza; da capire perche' la topologia sia meno")
            print("     depressa dello spettro.")
        elif fr < 0.0:
            print("  -> SEGNO SBAGLIATO: la relazione predice piu' loop della")
            print("     media alla posizione di DESI. Esaminare la relazione")
            print("     prima di concludere.")
        elif fr > 0.8 and rs < 3:
            print("  -> DESI GIACE SULLA RELAZIONE. Il deficit e' predetto dallo")
            print("     spettro: titolo, abstract e Sez. 7 vanno riscritti")
            print("     sull'origine spettrale.")
        elif fr < 0.5 and rs > 3:
            print("  -> DESI FUORI DALLA RELAZIONE. E' la prova che Referee 3")
            print("     chiede: lo spettro spiega solo una parte del deficit.")
        else:
            print("  -> INTERMEDIO. Quotare la frazione come risultato")
            print("     principale e riformulare la tesi in termini")
            print("     quantitativi invece che dicotomici.")
        if p["desi_fuori_range"]:
            print("\n  DESI e' fuori dall'intervallo spettrale dei mock: la")
            print("  relazione va extrapolata, va dichiarato, e N10 (fasi")
            print("  randomizzate a spettro fissato) diventa piu' necessario.")

    atomic_write_json(res / "paper1" / "n1b_report_NGC.json", rep)
    print(f"\n  report: {res/'paper1'/'n1b_report_NGC.json'}")


if __name__ == "__main__":
    main()

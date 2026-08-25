#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v3b_pilot_box.py

PILOTA per il punto 7.2: DISPERSIONE FRA REALIZZAZIONI A COSMOLOGIA FISSA

OBIETTIVO
---------
M26 (tex riga 735) attribuisce ~94% della varianza dell'ensemble alla
cosmologia, avendo misurato solo il termine HOD/downsampling (110 generatori)
con cosmologia E realizzazione entrambe fisse (indice nwLH 1805, 50 semi).
La dispersione fra REALIZZAZIONI DELLE CONDIZIONI INIZIALI a cosmologia fissa
non e' mai stata misurata: il 94% e' un residuo, non un'attribuzione.

Su disco ci sono 2000 campi phase0 per ciascuna suite (fiducial, lhc, nwlh),
prodotti dalla stessa phase0 con la stessa griglia. Differiscono per una cosa
sola: in 'fiducial' la cosmologia e' fissa e varia solo la realizzazione, in
'nwlh' variano entrambe. Calcolando N_H1 su entrambe con impostazioni
identiche la decomposizione si ottiene come rapporto fra varianze MISURATE:

    sigma^2(realizzazione) = sigma^2(fiducial)
    sigma^2(cosmologia)    = sigma^2(nwlh) - sigma^2(fiducial)

Confronto controllato, non inferenza per esclusione - cioe' esattamente il
difetto che stiamo correggendo in M26.

DUE AVVERTENZE, ENTRAMBE DA DICHIARARE NEL PAPER
------------------------------------------------
1. build_field e' specifico del cut-sky (vuole field_r, alpha, maschera). In
   scatola i random non esistono: si usa l'analogo periodico
       nu = log(1 + clip(delta, -1)) -> gaussian_filter -> sottrazione media
   fedele nella sostanza ma NON identico byte per byte. Il valore assoluto di
   N_H1 non sara' quello del paper; la FRAZIONE di varianza si'.

2. SCALA DI LISCIATURA. In scatola la cella e' 1000/128 = 7.8125 Mpc/h contro
   i 15.6044 del cut-sky. A parita' di R=5 Mpc/h fisici, sigma_px = 0.64
   invece di 0.3204: il doppio. Sapendo che questa statistica cambia
   comportamento con la scala - fino a invertire il segno del deficit sopra
   ~15 Mpc/h - una decomposizione misurata a 0.64 non si trasferisce
   automaticamente a 0.32. Il pilota gira quindi a ENTRAMBE le scale:
     0.3204  appaia il filtro in unita' di PIXEL
     0.6400  appaia il filtro in unita' FISICHE
   Se il rapporto sigma^2(fid)/sigma^2(nwlh) e' stabile fra le due, la
   conclusione regge; se non lo e', e' un risultato da dichiarare.

3. La scatola e' PERIODICA: la lisciatura va in mode='wrap', mentre il
   cut-sky usa il default 'reflect'. Il pilota misura quanto pesa la scelta.

COSA FA
-------
A  ispeziona un campo per suite: shape, dtype, statistiche, e se e' davvero
   un delta (min >= -1, media ~ 0)
B  verifica se esistono cataloghi di aloni FIDUCIALI (per un'eventuale via
   cut-sky piu' avanti); read_halo_catalog e' cablato su
   data/raw/quijote/3D_cubes/latin_hypercube_nwLH_hod
C  calcola N_H1 su K campi per suite, a 2 scale, con compute_tda_features
   IMPORTATA da phase8 (byte-identica), e cronometra per pianificare la
   produzione

Non scrive nulla oltre al report. NON e' la produzione: K=3 di default.

USO
---
  python src\\paper1_rev_v3b_pilot_box.py
  python src\\paper1_rev_v3b_pilot_box.py --k 5
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

BOXSIZE = 1000.0
NGRID = 128
R_SMOOTH = 5.0
CELL_BOX = BOXSIZE / NGRID              # 7.8125 Mpc/h
SIGMA_PX_CUTSKY = 0.3204385518606827    # R_SMOOTH / 15.6044 (cut-sky)
SIGMA_PX_BOX = R_SMOOTH / CELL_BOX      # 0.64
SUITES = ("fiducial", "nwlh", "lhc")


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


def build_field_box(delta, sigma_px, mode="wrap"):
    """Analogo periodico di build_field: stesse operazioni, senza random.
       log(1 + clip(delta, -1+1e-3)) -> gaussian_filter -> sottrazione media."""
    d = np.asarray(delta, np.float64)
    nu = np.log(1.0 + np.clip(d, -1.0 + 1e-3, None))
    nu = gaussian_filter(nu, sigma=sigma_px, mode=mode)
    nu -= nu.mean()
    return nu.astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=3, help="campi per suite (PILOTA)")
    ap.add_argument("--n_thresh", type=int, default=100)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    fdir = root / "data" / "processed" / "phase0_fields"
    rep = {"script": "paper1_rev_v3b_pilot_box.py",
           "cella_box": CELL_BOX, "cella_cutsky": 15.604397786848559,
           "sigma_px_testate": [SIGMA_PX_CUTSKY, SIGMA_PX_BOX]}

    # ---------------------------------------------------------- import phase8
    # phase8_cutsky_mocks fa parse_args([]) quando importato, quindi l'import
    # e' sicuro e non consuma il nostro sys.argv.
    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
    except Exception as e:
        print(f"[FATAL] import di phase8_cutsky_mocks fallito: {e}")
        return
    print("=" * 78)
    print("compute_tda_features importata da phase8_cutsky_mocks (byte-identica)")
    print(f"  N_THRESH modulo = {M.N_THRESH}   SIGMA_PX cut-sky = {M.SIGMA_PX:.7f}")
    print(f"  CELL cut-sky    = {M.CELL:.6f} Mpc/h   CELL box = {CELL_BOX:.6f}")
    print(f"  ZMIN, ZMAX      = {M.ZMIN}, {M.ZMAX}")
    print(f"  nota: feats[4] = len(p1) = numero totale di generatori H1 finiti")
    print(f"        feats[1] = picco della curva di Betti-1 (quantita' diversa)")

    # ============================================================ A
    print("\n" + "=" * 78)
    print("A - COSA CONTENGONO I CAMPI phase0")
    print("=" * 78)
    rep["campi"] = {}
    for s in SUITES:
        d = fdir / s
        if not d.exists():
            print(f"\n  [assente] {d}")
            continue
        files = sorted(d.glob("field_*.npy"))
        print(f"\n  {s}: {len(files)} file")
        if not files:
            continue
        a = np.load(files[0])
        frac_lt = float((a < -1.0).mean())
        print(f"    {files[0].name}: shape={a.shape} dtype={a.dtype}")
        print(f"    min={a.min():.4f}  max={a.max():.4f}  "
              f"media={a.mean():.6f}  sd={a.std():.4f}")
        print(f"    frazione < -1: {frac_lt:.3e}   "
              f"-> {'coerente con un delta' if frac_lt < 1e-9 and a.min() >= -1.001 else 'NON e un delta puro: verificare'}")
        rep["campi"][s] = {"n_file": len(files), "shape": list(a.shape),
                           "dtype": str(a.dtype), "min": float(a.min()),
                           "max": float(a.max()), "mean": float(a.mean()),
                           "std": float(a.std()), "frac_lt_m1": frac_lt}

    # ============================================================ B
    print("\n" + "=" * 78)
    print("B - ESISTONO CATALOGHI DI ALONI FIDUCIALI? (via cut-sky futura)")
    print("=" * 78)
    print(f"  read_halo_catalog e' cablato su:")
    print(f"    {M.HOD_CATALOG_DIR}")
    cubes = root / "data" / "raw" / "quijote" / "3D_cubes"
    if cubes.exists():
        for d in sorted(q for q in cubes.iterdir() if q.is_dir()):
            try:
                n = sum(1 for _ in d.iterdir())
            except Exception:
                n = -1
            print(f"    [presente] {d.name}   ({n} sottodirectory)")
            rep.setdefault("cataloghi", {})[d.name] = n
    else:
        print(f"    [assente] {cubes}")
    print(f"\n  Se non esiste un equivalente 'fiducial_hod', la via cut-sky per")
    print(f"  il 7.2 richiede una popolazione HOD nuova: molto piu' costosa")
    print(f"  della via in scatola. Il pilota qui sotto misura quest'ultima.")

    # ============================================================ C
    print("\n" + "=" * 78)
    print(f"C - PILOTA: N_H1 su K={args.k} campi per suite, a 2 scale")
    print("=" * 78)
    mask_full = np.ones((NGRID, NGRID, NGRID), dtype=bool)
    rep["pilota"] = {}
    timings = []

    for sig, etichetta in ((SIGMA_PX_CUTSKY, "0.3204 (appaiato in pixel)"),
                           (SIGMA_PX_BOX, "0.6400 (appaiato in fisico)")):
        print(f"\n  --- sigma_px = {etichetta}")
        print(f"      {'suite':>10s} {'idx':>5s} {'N_H1':>10s} {'b1_peak':>10s} "
              f"{'<pers1>':>10s} {'sec':>7s}")
        for s in ("fiducial", "nwlh"):
            d = fdir / s
            if not d.exists():
                continue
            files = sorted(d.glob("field_*.npy"))[:args.k]
            vals = []
            for p in files:
                t0 = time.time()
                a = np.load(p)
                nu = build_field_box(a, sig, mode="wrap")
                f = M.compute_tda_features(nu, mask_full, args.n_thresh,
                                           masked=False)
                dt = time.time() - t0
                timings.append(dt)
                vals.append(float(f[4]))
                print(f"      {s:>10s} {p.stem.split('_')[1]:>5s} "
                      f"{f[4]:>10.0f} {f[1]:>10.0f} {f[5]:>10.5f} {dt:>7.1f}")
            if vals:
                rep["pilota"][f"{s}_sigma{sig:.4f}"] = {
                    "n": len(vals), "valori": vals,
                    "media": float(np.mean(vals)),
                    "sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else None}

        # sensibilita' al mode della lisciatura, su un solo campo
        d = fdir / "fiducial"
        if d.exists():
            fs = sorted(d.glob("field_*.npy"))
            if fs:
                a = np.load(fs[0])
                vv = {}
                for mode in ("wrap", "reflect"):
                    nu = build_field_box(a, sig, mode=mode)
                    vv[mode] = float(M.compute_tda_features(
                        nu, mask_full, args.n_thresh, masked=False)[4])
                dd = vv["wrap"] - vv["reflect"]
                print(f"      mode: wrap={vv['wrap']:.0f}  "
                      f"reflect={vv['reflect']:.0f}  differenza={dd:+.0f} "
                      f"({100*abs(dd)/max(vv['wrap'],1):.2f}%)")
                rep.setdefault("mode_lisciatura", {})[f"sigma{sig:.4f}"] = vv

    # ---------------------------------------------------------- pianificazione
    print("\n" + "=" * 78)
    print("PIANIFICAZIONE DELLA PRODUZIONE")
    print("=" * 78)
    if timings:
        med = float(np.median(timings))
        print(f"  tempo mediano per campo: {med:.1f} s")
        for n in (200, 500, 2000):
            tot = med * n * 2 / 3600.0     # due suite
            print(f"    {n} campi x 2 suite x 1 scala: {tot:.1f} h")
        print(f"\n  con 2 scale il costo raddoppia. Una via intermedia sensata:")
        print(f"  N=500 per suite a entrambe le scale, che da' un errore")
        print(f"  frazionario su sigma di 1/sqrt(2*499) = 3.2% - piu' che")
        print(f"  sufficiente per un rapporto di varianze.")
        rep["timing"] = {"mediano_s": med, "n_misure": len(timings)}

    print("\n  PROSSIMO PASSO, in base a questo pilota:")
    print("    - i campi sono delta e le due suite sono confrontabili")
    print("      -> produzione a N=500 per suite, entrambe le scale")
    print("    - i valori di N_H1 in scatola sono di ordine molto diverso da")
    print("      35000 -> atteso: cella e volume diversi. Conta il RAPPORTO")
    print("      delle varianze, non il valore assoluto.")
    print("    - se wrap e reflect differiscono di piu' dell'1%, dichiarare la")
    print("      scelta nel protocollo prima della produzione.")

    outp = root / "results" / "paper1" / "rev_v3b_pilot_box_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()

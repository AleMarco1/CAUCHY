#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n9_resolution.py

N9 - SEMANTICA DELLA SCALA E CONVERGENZA IN RISOLUZIONE

Referee 1 §5:
  "Tutte le conclusioni vivono su una griglia 128^3 con cella 15.6 h^-1Mpc e
  smoothing sub-pixel: la scala effettiva della statistica e' la cella, non i
  '5 h^-1Mpc' del titolo di R. Le espressioni 'at the 5 h^-1Mpc scale'
  (Sez. 7.1) sono fuorvianti. Serve o un test di convergenza in risoluzione
  (dati e mock a 256^3, sigma_px rimatchato per costruzione, come la vostra
  stessa M26 prescrive) o una riformulazione esplicita: la statistica e'
  definita sulla griglia, e la scala fisica citata e' nominale."

E' un'alternativa, ma la riformulazione va fatta comunque: la parte A mostra con
numeri che il kernel e' sub-pixel e che il limite di risoluzione E' la cella.
Il test di convergenza serve a stabilire se il DEFICIT FRAZIONARIO sopravviva
al raddoppio della risoluzione, che e' la domanda scientifica sotto la
questione semantica.

PARTE A - SEMANTICA DELLA SCALA (aritmetica, nessun run)
--------------------------------------------------------
Cella 15.6044, sigma_px 0.3204: il kernel gaussiano ha FWHM = 2.355 sigma =
0.755 celle = 11.8 Mpc/h, MENO di una cella. La frazione di peso nel voxel
centrale e' erf(0.5/(sigma*sqrt2))^3 ~ 0.68: la lisciatura e' quasi l'identita'.

PARTE B - IL CANCELLO A 128^3
-----------------------------
Cambiare risoluzione richiede di iniettare NGRID, CELL e SIGMA_PX nel modulo -
lo stesso schema che phase9_sgc_likeforlike.py usa per l'SGC. Se sbaglio un
globale, il confronto misura il mio errore invece della convergenza.

Quindi si ricostruisce PRIMA tutto a 128^3 con lo stesso meccanismo di
iniezione, e si pretende:
    DESI      -> 28256 esatto
    un mock   -> il valore in per_mock_NGC_R5.jsonl, esatto
Solo se il cancello passa si sale a 256^3.

PARTE C - 256^3
---------------
  cella   = BOX_SIZE / 256 = 7.802 Mpc/h
  sigma_px rimatchato = R_SMOOTH / cella = 0.6409  (lisciatura FISICA invariata)
  maschera: la 128^3 congelata replicata 2x2x2, cosi' la regione FISICA e'
    identica e l'unica cosa che cambia e' la risoluzione del campo. Ricostruire
    la maschera con un criterio di soglia diverso confonderebbe due effetti.

Confronto: il deficit FRAZIONARIO (media_mock - DESI)/media_mock a 128^3 e a
256^3. Appaiato sugli stessi cataloghi di aloni e sugli stessi seed.

COSTO E MEMORIA
---------------
256^3 = 16.7 milioni di celle, otto volte 128^3. gudhi impiega molto piu' tempo
e diverse GB di memoria. Il test e' appaiato e su pochi mock perche' serve una
FRAZIONE, non un rank: --k 8 di default. Se la memoria non basta, --ngrid2 192.

USO
---
  python src\\paper1_rev_n9_resolution.py --stage A        # solo aritmetica
  python src\\paper1_rev_n9_resolution.py --stage AB       # + cancello
  python src\\paper1_rev_n9_resolution.py --k 8            # tutto
"""

import argparse
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

NH1 = "base.N_H1"
DESI_NH1 = 28256.0
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


class Inject:
    """Imposta NGRID/CELL/SIGMA_PX nel modulo e li ripristina all'uscita.
    Stesso schema di phase9_sgc_likeforlike.py, che inietta la geometria SGC."""

    def __init__(self, M, ngrid, r_smooth):
        self.M, self.ngrid, self.r = M, ngrid, r_smooth
        self.old = {}

    def __enter__(self):
        M = self.M
        for k in ("NGRID", "CELL", "SIGMA_PX"):
            self.old[k] = getattr(M, k)
        cell = float(M.BOX_SIZE) / self.ngrid
        M.NGRID = self.ngrid
        M.CELL = cell
        M.SIGMA_PX = self.r / cell
        return {"ngrid": self.ngrid, "cell": cell, "sigma_px": M.SIGMA_PX}

    def __exit__(self, *a):
        for k, v in self.old.items():
            setattr(self.M, k, v)
        return False


def upsample_mask(mask, factor):
    m = mask
    for ax in (0, 1, 2):
        m = np.repeat(m, factor, axis=ax)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--stage", default="ABC", choices=["A", "AB", "ABC"])
    ap.add_argument("--ngrid2", type=int, default=256)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--min_idx", type=int, default=MIN_IDX)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    outj = res / "paper1" / f"n9_res{args.ngrid2}_NGC.jsonl"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    import phase8_test2_masked as T2

    R_SM = float(getattr(M, "R_SMOOTH", 5.0))
    mask128 = np.load(root / "data" / "processed" / "phase6_fields" /
                      "bgs_ngc_mask_128.npy").astype(bool)
    rep = {"script": "paper1_rev_n9_resolution.py"}

    # ============================================================ A
    print("=" * 78)
    print("A - SEMANTICA DELLA SCALA")
    print("=" * 78)
    cell = float(M.BOX_SIZE) / 128
    sig = R_SM / cell
    fwhm_cell = 2.0 * math.sqrt(2.0 * math.log(2.0)) * sig
    w_centro = math.erf(0.5 / (sig * math.sqrt(2.0))) ** 3
    k_nyq = math.pi / cell
    print(f"  BOX_SIZE = {M.BOX_SIZE:.2f} Mpc/h   NGRID = 128")
    print(f"  cella           = {cell:.4f} Mpc/h")
    print(f"  R_smooth        = {R_SM:.2f} Mpc/h   ->  sigma_px = {sig:.5f}")
    print(f"  FWHM del kernel = {fwhm_cell:.4f} celle = "
          f"{fwhm_cell*cell:.2f} Mpc/h")
    print(f"  peso del kernel nel voxel centrale (3D) = {w_centro:.4f}")
    print(f"  Nyquist         = {k_nyq:.5f} h/Mpc  ->  lambda = "
          f"{2*math.pi/k_nyq:.1f} Mpc/h")
    print(f"\n  LETTURA: la FWHM del kernel e' {fwhm_cell:.2f} celle, quindi")
    print(f"  MINORE di un voxel, e il {100*w_centro:.0f}% del peso sta nel")
    print(f"  voxel centrale: la lisciatura e' quasi l'identita'. Il limite di")
    print(f"  risoluzione effettivo e' la CELLA ({cell:.1f} Mpc/h), non i")
    print(f"  {R_SM:.0f} Mpc/h nominali. Il referee ha ragione sulla semantica,")
    print(f"  e la riformulazione va fatta comunque.")
    rep["scala"] = {"cell": cell, "sigma_px": sig, "fwhm_celle": fwhm_cell,
                    "fwhm_mpc": fwhm_cell * cell, "peso_centrale": w_centro,
                    "k_nyquist": k_nyq}

    mir = res / "paper1" / "paper1_mirror_lfl_NGC.json"
    if mir.exists():
        J = json.load(open(mir, encoding="utf-8"))
        print(f"\n  risposta alla lisciatura (dalla scansione esistente):")
        print(f"    {'R':>5s} {'sigma_px':>9s} {'mock N_H1':>11s} "
              f"{'sub-cella?':>11s}")
        for k in ("R5", "R10", "R12", "R15", "R17", "R20", "R30"):
            if k in J.get("results", {}):
                r = J["results"][k]
                sp = r["sigma_px"]
                print(f"    {k:>5s} {sp:>9.4f} "
                      f"{r['mock_baseline_mean']:>11.1f} "
                      f"{'si' if sp < 0.5 else 'no':>11s}")
        print(f"\n    N_H1 varia fortemente gia' fra sigma_px 0.32 e 0.64, cioe'")
        print(f"    dentro il regime sub-pixel: la statistica NON e' insensibile")
        print(f"    alla lisciatura sotto la cella. E' un argomento che attenua")
        print(f"    - non annulla - l'obiezione del referee, e va riportato.")

    if args.stage == "A":
        atomic_write_json(res / "paper1" / "n9_report_NGC.json", rep)
        print(f"\n  report: {res/'paper1'/'n9_report_NGC.json'}")
        return

    # ============================================================ B
    print("\n" + "=" * 78)
    print("B - CANCELLO A 128^3 (l'iniezione dei globali e' corretta?)")
    print("=" * 78)
    nz_z, nz_target = M.load_bgs_nz()
    hod = M.HOD_MEDIAN

    def run_desi(ngrid, mask):
        with Inject(M, ngrid, R_SM) as g:
            fr, swr = M.load_desi_random_field()
            fd, swd = M.load_desi_data_field()
            nu = M.build_field(fd, fr, swd / swr, mask)
            v = float(M.compute_tda_features(nu, mask, M.N_THRESH,
                                             masked=True)[4])
        return v, g, fr, swr

    def run_mock(i, ngrid, mask, fr, swr):
        with Inject(M, ngrid, R_SM):
            rng = np.random.default_rng(args.seed + i)
            ph, mh, vh = M.read_halo_catalog(i, args.snapnum)
            if ph is None or len(ph) < 50:
                return None
            pg, vg = T2.populate_with_virial(ph, mh, vh, hod, rng)
            if len(pg) < 100:
                return None
            ps = M.carve_cutsky(pg, vg, mask, nz_z, nz_target, rng)
            if ps is None or len(ps) < 100:
                return None
            nu = M.voxelize_mock(ps, fr, swr, mask)
            if nu is None:
                return None
            return float(M.compute_tda_features(nu, mask, M.N_THRESH,
                                                masked=True)[4])

    t0 = time.time()
    v128, g128, fr128, swr128 = run_desi(128, mask128)
    print(f"  DESI a 128^3: N_H1 = {v128:.0f}   atteso {DESI_NH1:.0f}   "
          f"{'OK' if abs(v128-DESI_NH1) < 0.5 else '*** FALLITO ***'}"
          f"   ({time.time()-t0:.0f} s)")
    if abs(v128 - DESI_NH1) > 0.5:
        print("  L'iniezione dei globali non riproduce il valore congelato.")
        print("  Mi fermo: qualunque confronto a 256^3 misurerebbe il mio errore.")
        return

    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            kk = int(str(fl.get("key", j)).split("_")[-1])
        except (TypeError, ValueError):
            kk = j
        nh1[kk] = float(fl.get(NH1, np.nan))

    i0 = args.min_idx
    m128 = run_mock(i0, 128, mask128, fr128, swr128)
    exp = nh1.get(i0, np.nan)
    ok = m128 is not None and np.isfinite(exp) and abs(m128 - exp) < 0.5
    print(f"  mock {i0} a 128^3: N_H1 = "
          f"{m128 if m128 is not None else float('nan'):.0f}   "
          f"JSONL {exp:.0f}   {'OK' if ok else '*** FALLITO ***'}")
    if not ok:
        print("  Mi fermo.")
        return
    print("  cancello superato: l'iniezione riproduce la catena congelata.")
    rep["gate_128"] = {"desi": v128, "mock_idx": i0, "mock": m128,
                       "mock_atteso": exp}

    if args.stage == "AB":
        atomic_write_json(res / "paper1" / "n9_report_NGC.json", rep)
        print(f"\n  report: {res/'paper1'/'n9_report_NGC.json'}")
        return

    # ============================================================ C
    n2 = args.ngrid2
    if n2 % 128 != 0:
        print(f"\n[!] --ngrid2 deve essere multiplo di 128 per replicare la "
              f"maschera senza interpolazione.")
        return
    fac = n2 // 128
    mask2 = upsample_mask(mask128, fac)
    print("\n" + "=" * 78)
    print(f"C - CONVERGENZA A {n2}^3")
    print("=" * 78)
    print(f"  maschera 128^3 replicata {fac}x{fac}x{fac}: regione FISICA "
          f"identica")
    print(f"  riempimento {100*mask2.mean():.4f}% "
          f"(era {100*mask128.mean():.4f}%)")
    print(f"  memoria stimata per array float64: "
          f"{n2**3*8/1024**3:.2f} GB ciascuno")

    t0 = time.time()
    v2, g2, fr2, swr2 = run_desi(n2, mask2)
    print(f"\n  cella {g2['cell']:.4f} Mpc/h   sigma_px rimatchato "
          f"{g2['sigma_px']:.5f}")
    print(f"  DESI a {n2}^3: N_H1 = {v2:.0f}   ({time.time()-t0:.0f} s)")
    rep["desi"] = {"n128": v128, f"n{n2}": v2, "geom": g2}

    done = {r["idx"] for r in read_jsonl(outj)}
    t0 = time.time(); cnt = 0
    for i in range(args.min_idx, args.min_idx + args.k):
        if i in done:
            continue
        a = nh1.get(i, np.nan)
        b = run_mock(i, n2, mask2, fr2, swr2)
        if b is None:
            continue
        append_jsonl(outj, {"idx": i, "n128": float(a) if np.isfinite(a) else None,
                            f"n{n2}": b})
        cnt += 1
        print(f"    mock {i}: 128^3 = {a:.0f}   {n2}^3 = {b:.0f}   "
              f"({(time.time()-t0)/cnt:.0f} s/mock)")

    recs = [r for r in read_jsonl(outj) if r.get("n128") is not None]
    if len(recs) < 3:
        print("\n  troppi pochi mock per il confronto.")
        atomic_write_json(res / "paper1" / "n9_report_NGC.json", rep)
        return
    a = np.array([r["n128"] for r in recs], float)
    b = np.array([r[f"n{n2}"] for r in recs], float)

    print("\n" + "=" * 78)
    print("RISULTATO")
    print("=" * 78)
    print(f"  {len(recs)} mock appaiati")
    d128 = (a.mean() - DESI_NH1) / a.mean()
    d2 = (b.mean() - v2) / b.mean()
    print(f"\n  {'':>10s} {'mock':>12s} {'DESI':>10s} {'deficit':>10s} "
          f"{'frazione':>10s}")
    print(f"  {'128^3':>10s} {a.mean():>12.1f} {DESI_NH1:>10.0f} "
          f"{a.mean()-DESI_NH1:>10.0f} {100*d128:>9.2f}%")
    print(f"  {str(n2)+'^3':>10s} {b.mean():>12.1f} {v2:>10.0f} "
          f"{b.mean()-v2:>10.0f} {100*d2:>9.2f}%")
    sem128 = a.std(ddof=1) / np.sqrt(a.size) / a.mean()
    sem2 = b.std(ddof=1) / np.sqrt(b.size) / b.mean()
    err = np.sqrt(sem128 ** 2 + sem2 ** 2)
    print(f"\n  differenza fra le due frazioni: {100*(d2-d128):+.2f}% "
          f"+/- {100*err:.2f}%")
    print(f"  rapporto N_H1({n2}^3)/N_H1(128^3) sui mock: "
          f"{(b/a).mean():.3f} +/- {(b/a).std(ddof=1)/np.sqrt(a.size):.3f}")
    print(f"  lo stesso per DESI: {v2/DESI_NH1:.3f}")

    print("\n  LETTURA:")
    if abs(d2 - d128) < 3 * err and abs(d2 - d128) < 0.03:
        print(f"    Il deficit frazionario e' CONVERGENTE: {100*d128:.1f}% a")
        print(f"    128^3 contro {100*d2:.1f}% a {n2}^3. La conclusione non")
        print(f"    dipende dalla risoluzione, e resta da correggere solo la")
        print(f"    semantica ('5 Mpc/h' e' nominale: la scala e' la cella).")
    else:
        print(f"    Il deficit frazionario NON converge: {100*d128:.1f}% ->")
        print(f"    {100*d2:.1f}%. La statistica e' legata alla griglia, e la")
        print(f"    scala fisica citata e' priva di significato. Serve o una")
        print(f"    caratterizzazione della dipendenza dalla risoluzione, o")
        print(f"    l'ammissione che il risultato vale a griglia fissata.")
    print(f"\n    Nota: con {len(recs)} mock l'errore sulla frazione e' "
          f"{100*err:.2f}%. Serve solo a")
    print(f"    stabilire la convergenza, non a rimpiazzare il rank a 128^3.")

    rep["convergenza"] = {
        "n_mock": len(recs), "mock_128": float(a.mean()),
        f"mock_{n2}": float(b.mean()), "desi_128": DESI_NH1, f"desi_{n2}": v2,
        "frazione_128": float(d128), f"frazione_{n2}": float(d2),
        "differenza": float(d2 - d128), "errore": float(err)}
    atomic_write_json(res / "paper1" / "n9_report_NGC.json", rep)
    print(f"\n  report: {res/'paper1'/'n9_report_NGC.json'}")


if __name__ == "__main__":
    main()

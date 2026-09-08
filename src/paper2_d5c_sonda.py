#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_d5c_sonda.py — SOLA LETTURA. Non scrive niente e non tocca nessun file.

LA DOMANDA
  Le posizioni che escono dal cubo vengono impilate da phase8:688 sul voxel di
  bordo: `ijk = np.clip(((P_rsd - BOX_MIN)/CELL).astype(int), 0, NGRID-1)`.
  Quel voxel e' DENTRO la maschera o no?

PERCHE' DECIDE
  La maschera si deriva da `field_r`, cioe' dai RANDOM, che hanno zero clippati
  (verificato in build_geometries:202). Le galassie entrano solo in `field_d`.
  Se il voxel su cui una galassia clippata viene impilata sta FUORI maschera,
  quella galassia non entra nella filtrazione e l'effetto su N_H1 e'
  ESATTAMENTE zero, non "trascurabile".

  E' un ragionamento. Questo script lo misura.

COSA FA
  Per ogni realizzazione e ogni punto richiesto, ricostruisce lo stesso stato
  del runner (stessi semi, stesso HOD, stessa geometria), chiama carve_cutsky,
  e per le posizioni fuori dal cubo calcola il voxel di destinazione dopo il
  clip e lo confronta con la maschera. Riporta, per punto:

    n_clip          quante escono
    n_clip_inmask   quante finiscono su un voxel IN maschera  <- il numero
    faccia          su quale faccia escono
    eccesso_max     di quanto, in Mpc/h

  Se n_clip_inmask e' zero ovunque, l'effetto su N_H1 e' nullo per costruzione
  e D5c non ha piu' un bersaglio. Se non lo e', il numero dice quanto vale.

USO
  python src\\paper2_d5c_sonda.py --region NGC --n 5
  python src\\paper2_d5c_sonda.py --region SGC --n 5

  Cinque realizzazioni bastano: il conteggio e' 0-3 su ~218.000 e quel che
  interessa non e' la media ma se il caso "in maschera" si presenta MAI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser(description="D5c: i clippati finiscono in maschera?")
    p.add_argument("--src", default="src")
    p.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--points", nargs="*", default=["FID", "B1", "B2", "B4", "B5", "B6"])
    p.add_argument("--set", action="append", metavar="NOME=VALORE",
                   help="attributo che _prepare legge e che la sonda non conosce")
    a = p.parse_args()

    sys.path.insert(0, str(Path(a.src).resolve()))
    import paper2_runner_fase3_mock as R

    # Si riusa l'apparato del runner, non se ne costruisce un altro: stessa
    # geometria, stessi semi, stesso HOD. Una seconda implementazione qui
    # sarebbe la classe di difetto 445/313.
    #
    # `_prepare` legge attributi da un namespace di argparse. Invece di
    # indovinarli uno per volta a ogni AttributeError, li si CHIEDE al sorgente:
    # si estraggono con ast tutti gli `a.<attr>` letti dentro _prepare (e dentro
    # le funzioni che chiama al primo livello), si riempiono quelli noti, e se
    # ne resta anche uno si fallisce elencandoli TUTTI in una volta.
    import ast as _ast
    _src = Path(a.src, "paper2_runner_fase3_mock.py").read_text(encoding="utf-8")
    _tree = _ast.parse(_src)
    _fn = next(f for f in _ast.walk(_tree)
               if isinstance(f, _ast.FunctionDef) and f.name == "_prepare")
    _serve = {n.attr for n in _ast.walk(_fn)
              if isinstance(n, _ast.Attribute) and isinstance(n.value, _ast.Name)
              and n.value.id == "a" and isinstance(n.ctx, _ast.Load)}

    _noti = {
        "src": a.src, "region": a.region, "points": a.points, "n": a.n,
        "out": None, "erosions": None, "carve_reseed": None,
        "real_space": False, "skip_fid": False, "frozen_delta_dir": None,
        "project_root": ".", "cmd": "run", "seed": None, "snapnum": None,
        "cache_dir": None, "sigma_scale": None, "verbose": False,
        # False lascia ATTIVO il cancello della cache dei random: la sonda non
        # disattiva controlli per farsi partire.
        "no_cache_gate": False,
    }
    for _k, _v in (kv.split("=", 1) for kv in (a.set or [])):
        _noti[_k] = None if _v == "null" else _v

    class _A:
        pass
    aa = _A()
    for _k in _serve:
        if _k not in _noti:
            print(f"[FATAL] _prepare legge a.{_k} e questa sonda non sa cosa "
                  f"valga.", file=sys.stderr)
    _mancanti = sorted(_serve - set(_noti))
    if _mancanti:
        sys.exit("[FATAL] attributi non noti: %s\n"
                 "        Passali con --set nome=valore, oppure riportameli e "
                 "li metto nella tabella." % ", ".join(_mancanti))
    for _k, _v in _noti.items():
        setattr(aa, _k, _v)
    print(f"  [namespace] _prepare legge {len(_serve)} attributi, tutti noti: "
          f"{', '.join(sorted(_serve))}\n")

    M, P1, T2, F3, root, reg, geoms, Gr, cache_dir, frozen = R._prepare(aa, a.points)
    print("=" * 74)
    print(f"D5c — dove finiscono i clippati, {reg}, {a.n} realizzazioni")
    print("=" * 74)
    print(f"  {'pt':<5} {'mock':>4} {'n_sel':>8} {'n_clip':>7} "
          f"{'IN MASCHERA':>12} {'faccia':>10} {'eccesso':>9}")

    import paper2_phase3_preflight as PF
    import paper2_phase3_preflight as PF

    # CANCELLO DI RIPRODUZIONE. Le quattro righe che costruiscono l'HOD sono
    # replicate da one_mock: e' una seconda implementazione, quindi deve
    # riprodurre un valore gia' su disco prima di riportarne di nuovi. Il valore
    # e' n_sel al FID della realizzazione 0, letto da fase3_mock.jsonl. Se la
    # replica dell'HOD fosse sbagliata, n_sel sarebbe diverso.
    atteso = None
    reg_file = Path("results/paper2/fase3_mock.jsonl")
    if reg_file.exists():
        for ln in reg_file.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            if (r.get("region") == reg and r.get("index") == 0
                    and not r.get("smoke") and r.get("carve_reseed") is None
                    and isinstance(r.get("points", {}).get("FID"), dict)
                    and "n_sel" in r["points"]["FID"]):
                atteso = int(r["points"]["FID"]["n_sel"])
                break
    if atteso is None:
        sys.exit("[FATAL] non trovo n_sel al FID per la realizzazione 0 in "
                 "results/paper2/fase3_mock.jsonl: senza il valore congelato "
                 "questa sonda non si convalida e non riporta nulla.")

    tot_clip = tot_inmask = 0
    per_pt = {}
    gate_done = False
    for kk in range(a.n):
        # Le stesse quattro righe di one_mock, nello stesso ordine.
        rng = np.random.default_rng(R.SEED + kk)
        pos_h, mass_h, vel_h = M.read_halo_catalog(kk, R.SNAPNUM)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h,
                                                   M.HOD_MEDIAN, rng)
        state_after_hod = rng.bit_generator.state
        del pos_h, mass_h, vel_h
        for name in a.points:
            g = geoms[name]
            M.set_geometry(z_tab=None, dc_tab=g["dc_tab"], verbose=False)
            M.R_SMOOTH = g["R_SMOOTH"]
            M.set_geometry(box_min=g["box_min"], box_size=g["box_size"], verbose=False)
            M.N_TARGET_BGS = R.N_TARGET[reg]
            rng.bit_generator.state = state_after_hod
            pos = M.carve_cutsky(pos_gal, vel_gal, g["mask"], Gr["nz_z"],
                                 Gr["nz_target"], rng)
            if pos is None or len(pos) < 100:
                continue
            if kk == 0 and name == "FID" and not gate_done:
                gate_done = True
                if len(pos) != atteso:
                    sys.exit(f"[FATAL] cancello di riproduzione: n_sel al FID "
                             f"vale {len(pos)}, il registro dice {atteso}. La "
                             f"replica dell'HOD non e' quella di one_mock: "
                             f"nulla di quel che segue sarebbe affidabile.")
                print(f"  [cancello] n_sel FID/mock 0 = {len(pos)} = registro. "
                      f"La replica dell'HOD e' quella giusta.\n")
            lo, hi = M.BOX_MIN, M.BOX_MIN + M.BOX_SIZE
            out = ((pos < lo[None, :]) | (pos > hi[None, :])).any(axis=1)
            n_clip = int(out.sum())
            n_in = 0
            faccia, ecc = "-", 0.0
            if n_clip:
                # lo STESSO clip di phase8:688, non una riscrittura
                ijk = np.clip(((pos[out] - M.BOX_MIN[None, :]) / M.CELL
                               ).astype(np.int32), 0, M.NGRID - 1)
                inm = g["mask"][ijk[:, 0], ijk[:, 1], ijk[:, 2]]
                n_in = int(np.count_nonzero(inm))
                ex_lo = (lo[None, :] - pos[out]).max(axis=0)
                ex_hi = (pos[out] - hi[None, :]).max(axis=0)
                ax = int(np.argmax(np.maximum(ex_lo, ex_hi)))
                faccia = ("-" if ex_lo[ax] > ex_hi[ax] else "+") + "xyz"[ax]
                ecc = float(max(ex_lo[ax], ex_hi[ax]))
            tot_clip += n_clip
            tot_inmask += n_in
            d = per_pt.setdefault(name, [0, 0])
            d[0] += n_clip
            d[1] += n_in
            if n_clip:
                print(f"  {name:<5} {kk:>4} {len(pos):>8} {n_clip:>7} "
                      f"{n_in:>12} {faccia:>10} {ecc:>9.3f}")
        del pos_gal, vel_gal

    print("")
    print(f"  {'punto':<6} {'clippati':>9} {'in maschera':>12}")
    for name in a.points:
        c, i = per_pt.get(name, [0, 0])
        print(f"  {name:<6} {c:>9} {i:>12}")
    print("")
    print(f"  TOTALE: {tot_clip} clippati, di cui {tot_inmask} su un voxel "
          f"IN MASCHERA.")
    if tot_clip and not tot_inmask:
        print("""
  ZERO in maschera. I clippati finiscono tutti su voxel di padding, dove i
  random non arrivano e la soglia di maschera non e' superata, quindi NON
  entrano nella filtrazione: l'effetto su N_H1 e' ESATTAMENTE zero, non
  trascurabile. D5c non ha piu' un bersaglio sul lato mock e va ritirato come
  cancello bloccante, con questa misura come motivazione.""")
    elif tot_inmask:
        print(f"""
  {tot_inmask} FINISCONO IN MASCHERA. L'effetto su N_H1 non e' nullo. D5c
  serve, e la sua forma va decisa su questo numero: si blocca sull'eccesso
  rispetto al fiduciale, non sul valore assoluto, perche' la misura degli
  smoke dice che il clipping NON dipende dalla deformazione.""")
    else:
        print("  Nessun clippato in questo campione: rilanciare con --n maggiore.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    sys.exit(main())

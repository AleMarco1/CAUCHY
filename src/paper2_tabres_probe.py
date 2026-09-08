#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Probe: la risoluzione della tabella D_C basta a rendere l'iniezione innocua?

IL PROBLEMA, MISURATO
  set_geometry(dc_tab=...) sostituisce comoving_distance con un'interpolazione
  lineare sulla tabella iniettata. Con 4001 nodi su [0, 0.6] l'errore relativo
  su D_C vale 2.86e-9. Sul lato dati non muove un generatore (cancello 2.1-D2 e
  D3: 28256 esatto), ma sul lato mock sposta il campo delta del 3.2% nelle celle
  quasi vuote al bordo, dove delta e' vicino a -1: 243010 celle su 307805
  differiscono dai congelati di v1, pur lasciando N_H1 invariato.

  Misurato il 29 ago:
    comoving_distance NATIVA   -> L = 1997.3629167166155, delta BIT-IDENTICO
    tabella a 4001 nodi        -> L = 1997.3629110094512, 243010 celle diverse

  I due valori del lato del cubo dell'item 0.5 non sono due versioni: sono la
  stessa quantita' calcolata in due modi.

L'IPOTESI DA VERIFICARE
  L'errore dell'interpolazione lineare scala come N^-2. Da 4001 a 40001 nodi
  dovrebbe scendere di cento volte, a ~3e-11, sotto la risoluzione di float32
  (1 ULP = 1.19e-7 relativo). Se e' cosi', l'iniezione dell'identita' diventa
  indistinguibile dal calcolo nativo, il congelato torna DERIVABILE, e il
  problema smette di esistere invece di essere dichiarato.

  Cosa deve reggere, e va verificato e non assunto:
    - il lato dati continua a dare N_H1 = 28256 e 307805 voxel;
    - il lato mock torna bit-identico ai congelati di v1;
    - il lato del cubo converge a 1997.3629167166155.

PERCHE' UN PROCESSO FRESCO PER OGNI RISOLUZIONE
  Dopo la prima iniezione `comoving_distance` E' GIA' l'interpolatore: costruire
  una tabella nuova con quella darebbe l'interpolazione di un'interpolazione.
  Ogni chiamata di questo script inietta UNA volta, partendo dalla nativa.

Uso, una riga per risoluzione:
    python src\\paper2_tabres_probe.py --nodes 4001
    python src\\paper2_tabres_probe.py --nodes 10001
    python src\\paper2_tabres_probe.py --nodes 40001
    python src\\paper2_tabres_probe.py --nodes 100001
    python src\\paper2_tabres_probe.py --nodes 0        # nativa, riferimento
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

SIGMA_FID_NGC = 0.32042249039652254
FROZEN_L = 1997.3629167166155
FROZEN_VOX = 307805
FROZEN_NH1_DATA = 28256
FROZEN_NH1_MOCK0 = 35318
ULP_F32 = 2.0 ** -23          # 1.19e-7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", type=int, default=4001,
                    help="nodi della tabella; 0 = nessuna iniezione (nativa)")
    ap.add_argument("--zmax-tab", type=float, default=0.6)
    ap.add_argument("--mock", type=int, default=0)
    ap.add_argument("--src", default="src")
    ap.add_argument("--project_root", default=".")
    ap.add_argument("--out", default="results/paper2/tabres_probe.jsonl")
    a = ap.parse_args()

    sys.path.insert(0, a.src)
    import phase8_cutsky_mocks as M
    import paper1_remap as P1
    import phase8_test2_masked as T2
    import paper2_data_geometry as GEO
    import paper2_phase3_preflight as PF

    root = Path(a.project_root).resolve()
    G = P1.setup_region(M, "NGC", root / "data/raw/desi_dr1",
                        root / "data/processed/phase6_fields")

    rec = {"nodes": a.nodes, "mock": a.mock,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # --- l'iniezione, UNA volta, partendo dalla nativa ----------------------
    if a.nodes > 0:
        z_tab = np.linspace(0.0, a.zmax_tab, a.nodes)
        dc_tab = np.asarray(M.comoving_distance(z_tab), dtype=np.float64)
        # Cancello: la tabella deve essere costruita dalla NATIVA, non da una
        # interpolazione. Se D_C(0) != 0 o non e' crescente, qualcosa e' gia'
        # stato iniettato in questo processo.
        if dc_tab[0] != 0.0 or not np.all(np.diff(dc_tab) > 0):
            sys.exit("[FATAL] la tabella non viene dalla nativa.")
        M.set_geometry(z_tab=z_tab, dc_tab=dc_tab, verbose=False)
        rec["dz"] = float(a.zmax_tab / (a.nodes - 1))

    # --- geometria derivata --------------------------------------------------
    cache = PF.Cache(GEO, M, "NGC", "ran", verbose=False)
    pos_r, w_r = cache.positions()
    o = GEO.derive_box(pos_r, pad=5.0)
    bmin, L = (o[0], float(o[1])) if isinstance(o, tuple) else (o, None)
    bmin = np.asarray(bmin, float)
    rec["L"] = L
    rec["L_rel_vs_frozen"] = abs(L - FROZEN_L) / FROZEN_L

    M.R_SMOOTH = SIGMA_FID_NGC * (L / M.NGRID)
    M.set_geometry(box_min=bmin, box_size=L, verbose=False)
    rec["R_SMOOTH"] = float(M.R_SMOOTH)
    rec["sigma_px"] = float(M.SIGMA_PX)

    field_r = M.cic_3d(pos_r, w_r, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    mask = field_r > 0.01 * float(field_r.mean())
    sum_wr = float(w_r.sum())
    rec["n_valid_voxels"] = int(mask.sum())
    rec["mask_matches_frozen"] = bool(np.array_equal(mask, G["mask"]))
    rec["field_r_matches_frozen"] = bool(
        np.array_equal(field_r.astype(np.float32),
                       np.asarray(G["field_r"]).astype(np.float32)))
    del pos_r

    # --- lato dati: deve restare 28256 --------------------------------------
    field_d, sum_wd = M.load_desi_data_field()
    alpha_d = sum_wd / sum_wr
    nu_d = M.build_field(field_d, field_r, alpha_d, mask)
    rec["N_H1_data"] = int(round(float(
        M.compute_tda_features(nu_d, mask, M.N_THRESH, masked=True)[4])))
    del field_d, nu_d

    # --- lato mock: deve tornare bit-identico ai congelati -------------------
    rng = np.random.default_rng(42 + a.mock)
    ph, mh, vh = M.read_halo_catalog(a.mock, 3)
    pg, vg = T2.populate_with_virial(ph, mh, vh, M.HOD_MEDIAN, rng)
    M.N_TARGET_BGS = 217614
    ps = M.carve_cutsky(pg, vg, mask, G["nz_z"], G["nz_target"], rng)
    wd = np.ones(len(ps))
    fd = M.cic_3d(ps, wd, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    alpha_m = float(wd.sum()) / sum_wr
    delta = P1.compute_delta(fd, field_r, alpha_m, mask, M.NGRID).astype(np.float32)
    rec["n_sel"] = int(len(ps))

    fzp = root / "data/processed/paper1_mock_deltas/NGC" / ("delta_%04d.npy" % a.mock)
    fz = np.asarray(np.load(fzp))
    d = np.abs(delta.astype(np.float64) - fz.astype(np.float64))
    nz = fz != 0
    rec["delta_identical"] = bool(np.array_equal(delta, fz))
    rec["cells_differing"] = int((d > 0).sum())
    rec["max_rel"] = float((d[nz] / np.abs(fz[nz].astype(np.float64))).max()) \
        if nz.any() else 0.0
    rec["within_1ulp_f32"] = bool(rec["max_rel"] < 2 * ULP_F32)

    nu_m = M.build_field(fd, field_r, alpha_m, mask)
    rec["N_H1_mock"] = int(round(float(
        M.compute_tda_features(nu_m, mask, M.N_THRESH, masked=True)[4])))

    # --- verdetto ------------------------------------------------------------
    rec["gates"] = {
        "L == congelato": rec["L_rel_vs_frozen"] == 0.0,
        "voxel == 307805": rec["n_valid_voxels"] == FROZEN_VOX,
        "maschera == congelata": rec["mask_matches_frozen"],
        "N_H1 dati == 28256": rec["N_H1_data"] == FROZEN_NH1_DATA,
        "N_H1 mock == 35318": rec["N_H1_mock"] == FROZEN_NH1_MOCK0,
        "delta bit-identico": rec["delta_identical"],
    }
    rec["pass"] = all(rec["gates"].values())

    lab = "NATIVA" if a.nodes == 0 else f"{a.nodes} nodi (dz={rec['dz']:.3e})"
    print("=" * 74)
    print(f"tabella D_C: {lab}")
    print("=" * 74)
    print(f"  L                {L!r}   rel vs congelato {rec['L_rel_vs_frozen']:.3e}")
    print(f"  R_SMOOTH         {rec['R_SMOOTH']!r}")
    print(f"  voxel            {rec['n_valid_voxels']}  "
          f"maschera identica: {rec['mask_matches_frozen']}")
    print(f"  N_H1 dati        {rec['N_H1_data']} (atteso {FROZEN_NH1_DATA})")
    print(f"  N_H1 mock {a.mock}    {rec['N_H1_mock']} (atteso {FROZEN_NH1_MOCK0})  "
          f"n_sel={rec['n_sel']}")
    print(f"  delta            identico={rec['delta_identical']}  "
          f"celle={rec['cells_differing']}  max_rel={rec['max_rel']:.3e}  "
          f"entro 1 ULP f32: {rec['within_1ulp_f32']}")
    print("\n  cancelli:")
    for k, v in rec["gates"].items():
        print(f"    [{'ok ' if v else 'NO '}] {k}")
    print(f"\n  {'TUTTI SUPERATI' if rec['pass'] else 'non tutti superati'}")

    if a.out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 - Cancello 2.1-M: la maschera e' riproducibile dai random?

PERCHE' ESISTE
--------------
La maschera NON e' una quantita' derivata a runtime: e' un file .npy caricato da
disco (paper1_remap.py:211-214 per NGC, 239-247 per SGC), condiviso da ~30
script fra M26, Paper 1 e tutte le sue revisioni. Sotto una geometria iniettata
il box e i campi CIC cambiano, ma np.load restituisce lo stesso array: la
maschera resta ferma mentre il footprint si muove. Nel gauge a cubo costante le
galassie si spostano di 0.1-0.6 voxel contro un bordo statico, che e' la
contaminazione di bordo gia' responsabile di tre risultati ritirati.

Se la maschera e' riproducibile dai random, la Fase 3 puo' farla muovere con la
geometria. Se non lo e', il gauge a cubo costante va ripensato: non si misura
uno spostamento di 0.3 voxel contro un bordo che non si sa ricostruire.

REGOLA DI DECISIONE, DICHIARATA PRIMA DELL'ESECUZIONE
-----------------------------------------------------
Regola del produttore, phase6_bgs_voxelize.py:182-183:
        rand_threshold = 0.01 * field_r.mean()      # media sul CUBO INTERO
        mask           = field_r > rand_threshold

  M1  soglia    |thr_ricalcolata - thr_congelata| / thr_congelata <= 1e-6
  M2  conteggio mask.sum() == 307805 (NGC) / 172225 (SGC), ESATTO
  M3  identita' np.array_equal(mask_ricalcolata, mask_congelata), VERO
                (M2 senza M3 significa stesso numero di voxel in posti diversi:
                 e' un FALLIMENTO, non un successo parziale)

Diagnostiche riportate ma FUORI dal verdetto:
  D1  popolazione del percentile: count_nonzero(field_r > 0).
      Da rev_n4n5_report.json i tre conteggi P5/P10/P15 sono spaziati di 16017
      esatti, il che implica 320340. Se D1 conferma, la maschera congelata sta a
      P3.913 e l'etichetta "P10" del paper e' da correggere (item R2.6).
  D2  peso FKP medio = field_r.sum() / N_rand, atteso ~0.309 (P1 §4.1).
  D3  SOLO SGC: la geometria ottenuta con set_geometry() coincide con quella che
      paper1_remap.py:229-230 produce riassegnando a mano? Se si', il runner
      della Fase 2 puo' usare la via sanzionata invece della riassegnazione
      manuale, che il modulo sconsiglia (phase8_cutsky_mocks.py:167-169).

ESITI
  M1+M2+M3 -> PASSA. La maschera e' una funzione dei random: la Fase 3 la
              ricalcola per ogni punto della griglia.
  M1 ok, M3 no -> la regola e' giusta ma l'input no: i random caricati oggi non
              sono quelli con cui la maschera fu costruita. Problema di
              provenienza, non di regola.
  M1 no    -> la regola del produttore non e' quella che ha prodotto il file.
              Il 3.0 va riscritto e il gauge a cubo costante riesaminato.

USO
  python src\\paper2_gate21m.py --region NGC
  python src\\paper2_gate21m.py --region SGC
Una regione per invocazione: il ramo SGC riscrive le globali di geometria del
modulo e non le ripristina, quindi il processo deve morire subito dopo.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

FROZEN = {
    "NGC": {"n_valid_voxels": 307805, "mask_threshold": 0.020012933760881424,
            "box_size": 1997.3629167166155, "cell": 15.604397786848558,
            "sigma_px": 0.32042249039652254, "N_rand": 13248857,
            "mask_file": "bgs_ngc_mask_128.npy"},
    "SGC": {"n_valid_voxels": 172225, "mask_threshold": 0.008570596575737,
            "box_size": 1904.4501607158168, "cell": 14.878516880592318,
            "sigma_px": 0.3360550006514459, "N_rand": 5432939,
            "mask_file": "bgs_sgc_mask_128.npy"},
}
PERCENTILE_POP_EXPECTED = {"NGC": 320340, "SGC": None}   # SGC non ancora misurato
TOL_THR_REL = 1e-6
LOG = "results/paper2/gate21.jsonl"


def now():
    return datetime.now(timezone.utc).isoformat()


def line(ok):
    return "PASSA" if ok else "FALLITO"


def append_jsonl(path, rec):
    import os
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def load_region(M, region, root):
    """Ricarica field_r e la maschera congelata SENZA importare paper1_remap."""
    fld_dir = root / "data" / "processed" / "phase6_fields"
    desi_dir = root / "data" / "raw" / "desi_dr1"
    mask_path = fld_dir / FROZEN[region]["mask_file"]
    if not mask_path.exists():
        sys.exit("[FATAL] maschera assente: %s" % mask_path)
    mask_frozen = np.load(mask_path).astype(bool)
    geom_note = None

    if region == "NGC":
        # geometria fiduciale gia' nelle globali del modulo all'import
        field_r, sum_wr = M.load_desi_random_field()
    else:
        sys.path.insert(0, str(root / "src"))
        import phase9_sgc_likeforlike as S
        ran = desi_dir / "BGS_BRIGHT-21.5_SGC_0_clustering.ran.fits"
        if not ran.exists():
            sys.exit("[FATAL] random SGC assente: %s" % ran)
        pos_r, w_r = S.sgc_positions(ran, wkeys=("WEIGHT_FKP",), M=M)
        box_min = pos_r.min(axis=0) - 5.0
        box_size = float(((pos_r.max(axis=0) + 5.0) - box_min).max())
        # D3: via sanzionata invece della riassegnazione a mano di
        # paper1_remap.py:229-230. set_geometry ricalcola CELL e SIGMA_PX
        # sempre (phase8:319-321) e le asserisce (324-325).
        M.set_geometry(box_min=box_min, box_size=box_size, verbose=True)
        f = FROZEN["SGC"]
        geom_note = {
            "box_size": {"got": float(M.BOX_SIZE), "ref": f["box_size"]},
            "cell": {"got": float(M.CELL), "ref": f["cell"]},
            "sigma_px": {"got": float(M.SIGMA_PX), "ref": f["sigma_px"]},
        }
        for k, v in geom_note.items():
            e = abs(v["got"] - v["ref"]) / abs(v["ref"])
            v["rel"] = e
            v["pass"] = e <= TOL_THR_REL
        field_r = M.cic_3d(pos_r, w_r, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
        sum_wr = float(w_r.sum())
    return field_r, sum_wr, mask_frozen, geom_note


def main():
    ap = argparse.ArgumentParser(description="Cancello 2.1-M: maschera dai random")
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", choices=["NGC", "SGC"], required=True)
    ap.add_argument("--dump", default=None,
                    help="salva la maschera ricalcolata a questo percorso. "
                         "MAI il nome congelato: e' letto da ~30 script.")
    args = ap.parse_args()
    root = Path(args.project_root).resolve()
    region = args.region
    f = FROZEN[region]

    if args.dump and Path(args.dump).name in (v["mask_file"] for v in FROZEN.values()):
        sys.exit("[FATAL] --dump non puo' usare il nome della maschera congelata.")

    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
    except Exception as e:
        sys.exit("[FATAL] import di phase8_cutsky_mocks fallito: %s" % e)

    print("=" * 70)
    print("CANCELLO 2.1-M  |  %s  |  maschera riproducibile dai random?" % region)
    print("=" * 70)

    field_r, sum_wr, mask_frozen, geom = load_region(M, region, root)

    # --- la regola del produttore, phase6_bgs_voxelize.py:182-183 ------------
    thr = 0.01 * float(field_r.mean())
    mask_re = field_r > thr

    e_thr = abs(thr - f["mask_threshold"]) / abs(f["mask_threshold"])
    m1 = e_thr <= TOL_THR_REL
    n_re = int(mask_re.sum())
    m2 = (n_re == f["n_valid_voxels"])
    m3 = bool(np.array_equal(mask_re, mask_frozen))

    print("\n[M1] soglia     = %.18g" % thr)
    print("     congelata  = %.18g   rel %.3e   %s" % (f["mask_threshold"], e_thr, line(m1)))
    print("[M2] voxel      = %d   atteso %d   scarto %+d   %s"
          % (n_re, f["n_valid_voxels"], n_re - f["n_valid_voxels"], line(m2)))
    print("[M3] identita'  = %s   %s" % (m3, line(m3)))
    if not m3:
        only_re = int((mask_re & ~mask_frozen).sum())
        only_fr = int((mask_frozen & ~mask_re).sum())
        inter = int((mask_re & mask_frozen).sum())
        union = int((mask_re | mask_frozen).sum())
        print("     solo ricalcolata %d | solo congelata %d | Jaccard %.6f"
              % (only_re, only_fr, inter / union if union else 0.0))

    # --- diagnostiche, fuori dal verdetto ------------------------------------
    pop = int(np.count_nonzero(field_r > 0))
    exp_pop = PERCENTILE_POP_EXPECTED[region]
    print("\n[D1] voxel con field_r > 0 = %d%s" % (
        pop, ("   atteso %d   %s" % (exp_pop, "OK" if pop == exp_pop else "DIVERSO"))
        if exp_pop else "   (nessun atteso registrato)"))
    if pop:
        pct = 100.0 * (1.0 - f["n_valid_voxels"] / pop)
        print("     la maschera congelata sta al percentile P%.3f di questa popolazione" % pct)
    wfkp = sum_wr / f["N_rand"]
    print("[D2] peso FKP medio = %.6f  (P1 §4.1 quota 0.309, scarto %+.2f%%)"
          % (wfkp, 100 * (wfkp / 0.309 - 1)))
    if geom:
        print("[D3] set_geometry() contro la riassegnazione manuale:")
        for k, v in geom.items():
            print("     %-9s %.17g  atteso %.17g  rel %.2e  %s"
                  % (k, v["got"], v["ref"], v["rel"], line(v["pass"])))

    if args.dump:
        np.save(args.dump, mask_re)
        print("\n     maschera ricalcolata salvata in %s" % args.dump)

    ok = m1 and m2 and m3
    print("\n=== 2.1-M %s %s ===" % (region, line(ok)))
    if not ok:
        if not m1:
            print("    ESITO: la regola del produttore non e' quella che ha prodotto il file.")
            print("           Il 3.0 va riscritto e il gauge a cubo costante riesaminato.")
        elif not m3:
            print("    ESITO: regola giusta, input diverso. I random caricati oggi non sono")
            print("           quelli con cui la maschera fu costruita. Provenienza, non regola.")

    append_jsonl(root / LOG, {
        "ts": now(), "gate": "2.1-M", "region": region,
        "threshold": thr, "threshold_ref": f["mask_threshold"], "rel_threshold": e_thr,
        "n_voxels": n_re, "n_voxels_ref": f["n_valid_voxels"],
        "array_equal": m3, "M1": m1, "M2": m2, "M3": m3,
        "nonzero_population": pop, "mean_fkp_weight": wfkp,
        "geometry_set_geometry": geom, "pass": bool(ok)})
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

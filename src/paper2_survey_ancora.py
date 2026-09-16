#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_survey_ancora.py

Il cancello del runner di 4.2a si e' fermato su SGC idx 24: ramo unitario 18684
contro 18592 congelato. Accertato:

  - DETERMINISTICO: due esecuzioni indipendenti danno 18684 entrambe;
  - NON sistematico: NGC ha riprodotto 190 realizzazioni su 190 a scarto zero,
    e SGC 24 su 25;
  - il registro e' PULITO: 2000 righe, 2000 chiavi distinte, nessun indice
    ripetuto o mancante, un solo record per l'indice 24.

Resta una domanda sola, e decide il da farsi: **la 24 e' isolata o e' la prima
di molte?** Una su venticinque farebbero ~80 fermate su 2000, e allora la
questione non e' come passarci sopra ma quale delle due catene sia quella
giusta. Una su duemila e' un'anomalia da registrare e superare.

COSA FA
-------
Ricostruisce il RAMO UNITARIO — quello dell'ancora — su un intervallo di indici,
e per ognuno riporta lo scarto contro per_mock_<REG>_R5.jsonl. **Non si ferma**:
e' una sonda, non un cancello, e serve proprio a contare le eccezioni.

Una sola chiamata TDA per realizzazione, a k=0, perche' l'ancora e' li': ~15 s
invece dei 90 del runner completo.

Riporta anche n_gal, n_sel e alpha, perche' se il carving diverge lo si vede
li' e non nel N_H1.

NON SCRIVE NEI REGISTRI DI PRODUZIONE. L'uscita e' un file a parte, e il nome
deve contenere 'survey'.

USO
    python src\\paper2_survey_ancora.py selftest
    python src\\paper2_survey_ancora.py sonda --region SGC --da 0 --n 60 ^
        --out results\\paper2\\survey_ancora_SGC.jsonl

Uscita: 0 se la sonda gira. Il numero di eccezioni NON entra nel codice di
uscita: contarle e' lo scopo, non un fallimento.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SEED = 42
SNAPNUM = 3
TOL = 3          # la stessa del runner: il reference dichiara shift <= 3 sui pareggi
ROOT_DEFAULT = "."


def now():
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path, rec):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def classifica(scarto, tol=TOL):
    if scarto is None:
        return "SENZA ANCORA"
    if abs(scarto) <= tol:
        return "esatto" if scarto == 0 else "entro pareggi"
    return "DIVERGE"


def sonda(root, region, da, n, out_path):
    out = Path(out_path)
    if "survey" not in out.name.lower():
        raise SystemExit("il nome di uscita deve contenere 'survey': non e' un "
                         "registro di produzione")
    if da >= n:
        raise SystemExit("RIFIUTO: --da %d non e' minore di --n %d" % (da, n))

    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M            # noqa: E402
    import paper1_remap as P1                  # noqa: E402
    import phase8_test2_masked as T2           # noqa: E402
    import paper2_phase3_preflight as PF       # noqa: E402
    import paper2_runner_fase3 as F3           # noqa: E402
    import paper2_runner_fase3_mock as R3      # noqa: E402
    import paper2_data_geometry as GEO         # noqa: E402
    import paper2_item13a_15a as I13           # noqa: E402
    import paper2_runner_4_2a as RUN           # noqa: E402

    print("=" * 78)
    print("SONDA SULL'ANCORA per_mock  |  %s  |  indici %d..%d  |  1 TDA/mock"
          % (region, da, n - 1))
    print("=" * 78)

    z_tab = np.asarray(M._Z_TAB, float).copy()
    dc_fid = np.asarray(M._DC_TAB, float).copy()
    M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
    Gr = P1.setup_region(M, region, root / "data" / "raw" / "desi_dr1",
                         root / "data" / "processed" / "phase6_fields")
    cache_r = PF.Cache(GEO, M, region, "ran")
    geoms = R3.build_geometries(M, GEO, PF, I13, F3, region, cache_r,
                                z_tab, dc_fid, ["FID"])
    g = geoms["FID"]
    nh1, _ = RUN.carica_ancore(root, region)
    print("  ancore lette: %d record" % len(nh1))

    esiti = []
    t0 = time.time()
    for kk in range(da, n):
        rng = np.random.default_rng(SEED + kk)
        try:
            pos_h, mass_h, vel_h = M.read_halo_catalog(kk, SNAPNUM)
        except Exception as e:
            print("  [%4d] catalogo: %s" % (kk, e))
            continue
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h,
                                                   M.HOD_MEDIAN, rng)
        stato = rng.bit_generator.state
        del pos_h, mass_h, vel_h
        M.set_geometry(z_tab=None, dc_tab=g["dc_tab"], verbose=False)
        M.R_SMOOTH = g["R_SMOOTH"]
        M.set_geometry(box_min=g["box_min"], box_size=g["box_size"], verbose=False)
        M.N_TARGET_BGS = R3.N_TARGET[region]
        rng.bit_generator.state = stato
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], Gr["nz_z"],
                                 Gr["nz_target"], rng)
        if pos_sel is None or len(pos_sel) < 100:
            print("  [%4d] carve vuoto" % kk)
            continue
        cl = PF.clipped_per_face(pos_sel, M.BOX_MIN, M.BOX_SIZE)
        w = np.ones(len(pos_sel))
        fd = M.cic_3d(pos_sel, w, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
        alpha = float(w.sum()) / g["sum_wr"]
        nu = M.build_field(fd, g["field_r"], alpha, g["mask"])
        v = int(round(float(M.compute_tda_features(nu, g["mask"], M.N_THRESH,
                                                   masked=True)[4])))
        atteso = nh1.get(kk)
        scarto = None if atteso is None else int(v - round(atteso))
        cl_n = int(cl["n_clipped"])
        rec = {"schema": "paper2_survey_ancora", "region": region, "index": kk,
               "utc": now(), "N_H1_k0": v,
               "atteso": None if atteso is None else float(atteso),
               "scarto": scarto, "classe": classifica(scarto),
               "n_gal": int(len(pos_gal)), "n_sel": int(len(pos_sel)),
               "alpha": alpha, "d5c_n_clipped": cl_n}
        append_jsonl(out, rec)
        esiti.append(rec)
        if rec["classe"] == "DIVERGE" or (kk - da) % 10 == 0:
            el = time.time() - t0
            print("  [%4d] N_H1 %6d  atteso %6s  scarto %+5s  %-14s  "
                  "n_gal %7d  n_sel %7d  clip %d   %.0f s/mock"
                  % (kk, v, "%.0f" % atteso if atteso else "-",
                     scarto if scarto is not None else "-", rec["classe"],
                     rec["n_gal"], rec["n_sel"], cl_n,
                     el / max(len(esiti), 1)))
        del pos_gal, vel_gal, pos_sel, fd, nu

    # --- sommario ------------------------------------------------------------
    div = [r for r in esiti if r["classe"] == "DIVERGE"]
    print("\n" + "=" * 78)
    print("  realizzazioni sondate : %d" % len(esiti))
    print("  esatte (scarto 0)     : %d" % sum(1 for r in esiti if r["scarto"] == 0))
    print("  entro i pareggi (<=%d) : %d" % (TOL, sum(
        1 for r in esiti if r["scarto"] is not None and 0 < abs(r["scarto"]) <= TOL)))
    print("  DIVERGENTI            : %d   indici %s"
          % (len(div), [r["index"] for r in div][:20]))
    if div:
        sc = np.array([r["scarto"] for r in div], float)
        print("  scarti divergenti     : media %+.1f  sd %.1f  min %+d  max %+d"
              % (sc.mean(), sc.std(ddof=1) if sc.size > 1 else 0.0,
                 int(sc.min()), int(sc.max())))
        buoni = [r for r in esiti if r["classe"] != "DIVERGE"]
        if buoni:
            ns_d = np.array([r["n_sel"] for r in div], float)
            ns_b = np.array([r["n_sel"] for r in buoni], float)
            print("  n_sel divergenti %.1f +/- %.1f  contro %.1f +/- %.1f dei buoni"
                  % (ns_d.mean(), ns_d.std(ddof=1) if ns_d.size > 1 else 0.0,
                     ns_b.mean(), ns_b.std(ddof=1)))
            print("  -> se n_sel dei divergenti sta nella distribuzione dei buoni,")
            print("     il carving NON e' il meccanismo e va cercato a valle")
        frazione = len(div) / len(esiti)
        print("\n  frazione divergente %.1f%%  ->  su 2000 sarebbero ~%d fermate"
              % (100 * frazione, int(round(frazione * 2000))))
    else:
        print("\n  Nessuna divergenza in questo intervallo.")
    print("  uscita: %s" % out)
    return 0


# ---------------------------------------------------------------------------

def selftest():
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, n))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, n, det))

    print("selftest paper2_survey_ancora")

    chk("la tolleranza e' quella del runner e del reference", TOL == 3)
    chk("scarto 0 e' esatto", classifica(0) == "esatto")
    chk("scarto 3 e' ancora dentro i pareggi", classifica(3) == "entro pareggi")
    chk("scarto -3 pure, il segno non conta", classifica(-3) == "entro pareggi")
    chk("scarto 4 DIVERGE", classifica(4) == "DIVERGE")
    chk("scarto 92, il caso vero, DIVERGE", classifica(92) == "DIVERGE")
    chk("senza ancora non e' una divergenza", classifica(None) == "SENZA ANCORA")

    class A:
        pass

    def _rif(nome, da=0, n=5):
        x = A()
        try:
            sonda("/nonesiste", "SGC", da, n, nome)
        except SystemExit as e:
            return str(e)
        except Exception as e:
            return "ALTRO:" + type(e).__name__
        return ""
    chk("un nome senza 'survey' e' rifiutato",
        "survey" in _rif("/t/ensemble_v2_SGC.jsonl"))
    chk("e la validazione viene PRIMA dell'import dei moduli",
        "ALTRO" not in _rif("/t/ensemble_v2_SGC.jsonl"))
    chk("--da oltre --n e' rifiutato",
        "--da" in _rif("/t/survey_x.jsonl", da=10, n=5))

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sonda")
    s.add_argument("--root", default=ROOT_DEFAULT)
    s.add_argument("--region", choices=["NGC", "SGC"], required=True)
    s.add_argument("--da", type=int, default=0)
    s.add_argument("--n", type=int, required=True)
    s.add_argument("--out", required=True)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "sonda":
        return sonda(a.root, a.region, a.da, a.n, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

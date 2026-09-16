#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_cammini_desi.py

Due cammini producono delta di DESI, e danno soglie dei patologici diverse:
2 ULP di float32 in NGC, 26 in SGC. Questo strumento misura la differenza e —
soprattutto — se sposta il conteggio che 4.2c usa.

I DUE CAMMINI
-------------
  A  ANALITICO : setup_region chiamata SENZA aver prima impostato la tabella
                 delle distanze. E' il cammino di step6 e della riga DESI di v1
                 (che infatti riproduce i 28 valori di step6 a 0.000e+00).
  B  TABELLA   : set_geometry(z_tab=..., dc_tab=...) PRIMA di setup_region. E'
                 il cammino di produzione di paper2_runner_fase3_mock, e quindi
                 del runner di 4.2a. set_geometry sostituisce comoving_distance
                 con un'interpolazione a 4001 nodi, che sposta le posizioni e
                 quindi field_r, cioe' il DENOMINATORE di delta (D4a).

Nessuno dei due e' sbagliato. La domanda non e' quale sia giusto: e' se la
differenza raggiunga una quantita' che decide qualcosa.

LA DOMANDA CHE DECIDE, E COME SI RISPONDE
-----------------------------------------
La soglia dei patologici e' DICHIARATA nel record 54 ed e' lato dati: v1 e v2
contano entrambi sopra quella, quindi la ricomputazione e' una spia e non un
ingrediente. Cio' che conta e' quanti voxel di un campo MOCK cadono fra le due
soglie: se nessuno, la differenza di cammino non puo' spostare n_patologici, e
la spia si puo' leggere per quel che e'.

Si misura sui delta v1 GIA' IN CACHE — nessuna TDA, nessun carving, secondi.

USO
    python src\\paper2_cammini_desi.py selftest
    python src\\paper2_cammini_desi.py confronta --region SGC --n-mock 5
    python src\\paper2_cammini_desi.py confronta --region NGC --n-mock 5

NGC serve da controllo: il runner ha gia' misurato zero voxel fra le due
soglie su cinque realizzazioni, quindi se questo strumento non ritrova quello
zero, il difetto e' nello strumento.

Uscita: 0 sempre che la misura riesca. Il verdetto sta nel testo e nel JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT_DEFAULT = "."


def ulp32(x):
    return float(np.spacing(np.float32(x)))


def distanza_ulp(a, b):
    u = ulp32(a)
    return abs(float(b) - float(a)) / u if u > 0 else float("inf")


def fra_le_due(valori, s1, s2):
    """Quanti valori cadono nell'intervallo semiaperto fra le due soglie."""
    lo, hi = (s1, s2) if s1 <= s2 else (s2, s1)
    v = np.asarray(valori)
    return int(((v > lo) & (v <= hi)).sum())


def istantanea_geometria(M):
    return {"box_min": [float(x) for x in np.atleast_1d(M.BOX_MIN)],
            "box_size": float(M.BOX_SIZE), "sigma_px": float(M.SIGMA_PX),
            "ngrid": int(M.NGRID),
            "r_smooth": float(getattr(M, "R_SMOOTH", float("nan")))}


def confronta_campi(dA, dB, mask):
    a = np.asarray(dA, dtype=np.float64)[mask]
    b = np.asarray(dB, dtype=np.float64)[mask]
    d = np.abs(a - b)
    iA, iB = int(np.argmax(a)), int(np.argmax(b))
    return {"n_voxel": int(a.size),
            "max_abs_diff": float(d.max()), "media_abs_diff": float(d.mean()),
            "n_celle_diverse": int((d > 0).sum()),
            "frac_celle_diverse": float((d > 0).sum() / a.size),
            "max_A": float(a.max()), "max_B": float(b.max()),
            "argmax_A": iA, "argmax_B": iB,
            "stesso_voxel_al_massimo": bool(iA == iB),
            "diff_al_voxel_del_massimo_A": float(abs(a[iA] - b[iA]))}


def confronta(root, region, n_mock=5, out_path=None):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M          # noqa: E402
    import paper1_remap as P1                # noqa: E402

    raw = root / "data" / "raw" / "desi_dr1"
    ph6 = root / "data" / "processed" / "phase6_fields"

    print("=" * 78)
    print("DUE CAMMINI PER delta DI DESI  |  %s" % region)
    print("=" * 78)

    # --- A: analitico. DEVE venire per primo: una volta impostata la tabella,
    #     comoving_distance resta sostituita per il resto del processo.
    print("\n[A] cammino ANALITICO (step6, riga DESI di v1)")
    GA = P1.setup_region(M, region, raw, ph6)
    geoA = istantanea_geometria(M)
    aA = GA["sum_wd"] / GA["sum_wr"]
    dA = P1.compute_delta(GA["field_d"], GA["field_r"], aA, GA["mask"], M.NGRID)
    print("    box_size %.9f  sigma_px %.9f  alpha %.9e"
          % (geoA["box_size"], geoA["sigma_px"], aA))

    # --- B: tabella
    print("\n[B] cammino con TABELLA (produzione: R3 e runner di 4.2a)")
    z_tab = np.asarray(M._Z_TAB, float).copy()
    dc_fid = np.asarray(M._DC_TAB, float).copy()
    M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
    GB = P1.setup_region(M, region, raw, ph6)
    geoB = istantanea_geometria(M)
    aB = GB["sum_wd"] / GB["sum_wr"]
    dB = P1.compute_delta(GB["field_d"], GB["field_r"], aB, GB["mask"], M.NGRID)
    print("    box_size %.9f  sigma_px %.9f  alpha %.9e"
          % (geoB["box_size"], geoB["sigma_px"], aB))

    stessa_maschera = bool(np.array_equal(GA["mask"], GB["mask"]))
    print("\n  maschere identiche: %s  (%d contro %d voxel)"
          % (stessa_maschera, int(GA["mask"].sum()), int(GB["mask"].sum())))
    if not stessa_maschera:
        print("  [!] maschere diverse: il confronto sotto usa quella di A")

    c = confronta_campi(dA, dB, GA["mask"])
    sA, sB = c["max_A"], c["max_B"]
    n_ulp = distanza_ulp(sA, sB)

    print("\n--- il campo delta di DESI, dentro maschera ---")
    print("    max|Delta|           %.6e" % c["max_abs_diff"])
    print("    media|Delta|         %.6e" % c["media_abs_diff"])
    print("    celle diverse        %d su %d (%.4f%%)"
          % (c["n_celle_diverse"], c["n_voxel"], 100 * c["frac_celle_diverse"]))
    print("\n--- il massimo, che E' la soglia dei patologici ---")
    print("    A %.12f   B %.12f" % (sA, sB))
    print("    distanza %.6e assoluta, %.3e relativa, %.1f ULP di float32"
          % (abs(sB - sA), abs(sB - sA) / abs(sA), n_ulp))
    print("    stesso voxel al massimo: %s" % c["stesso_voxel_al_massimo"])
    if not c["stesso_voxel_al_massimo"]:
        print("    [!] il massimo cambia VOXEL fra i due cammini: non e' il")
        print("        valore di una cella che si muove, e' un'altra cella che vince")
    print("    scarto al voxel del massimo di A: %.6e"
          % c["diff_al_voxel_del_massimo_A"])

    # --- la misura che decide: i mock in cache -------------------------------
    print("\n--- quanti voxel di un mock cadono FRA le due soglie ---")
    cache = root / "data" / "processed" / "paper1_mock_deltas" / region
    conteggi, esiti = [], []
    for kk in range(n_mock):
        fp = cache / ("delta_%04d.npy" % kk)
        if not fp.is_file():
            print("    [!] assente: %s" % fp)
            continue
        a = np.load(fp)
        v = np.asarray(a, dtype=np.float64)[GA["mask"]]
        n_fra = fra_le_due(v, sA, sB)
        n_a = int((v > sA).sum())
        n_b = int((v > sB).sum())
        conteggi.append(n_fra)
        esiti.append({"idx": kk, "n_pat_A": n_a, "n_pat_B": n_b,
                      "n_fra_le_due": n_fra})
        print("    delta_%04d  n_pat con A %5d   con B %5d   fra le due %d"
              % (kk, n_a, n_b, n_fra))
        del a, v

    verdetto = None
    if conteggi:
        m = max(conteggi)
        if m == 0:
            verdetto = "IRRILEVANTE"
            print("\n  VERDETTO: nessun voxel cade fra le due soglie su %d mock."
                  % len(conteggi))
            print("  La differenza di cammino NON puo' spostare n_patologici, e la")
            print("  spia dei %.0f ULP si legge per quel che e': una differenza di" % n_ulp)
            print("  cammino su un estremo, senza conseguenze sulla regola di 4.2c.")
        else:
            verdetto = "SPOSTA"
            print("\n  VERDETTO: fino a %d voxel cadono fra le due soglie." % m)
            print("  La soglia CANONICA resta quella del record 54 — e' dichiarata")
            print("  e lato dati — ma va scritto che il conteggio dipende dal")
            print("  cammino a quel livello, e di quanto.")
    else:
        print("\n  VERDETTO: nessun mock in cache, la misura non e' stata fatta.")

    rapporto = {"schema": "paper2_cammini_desi_v1", "region": region,
                "utc": datetime.now(timezone.utc).isoformat(),
                "geometria_A": geoA, "geometria_B": geoB,
                "alpha_A": float(aA), "alpha_B": float(aB),
                "maschere_identiche": stessa_maschera,
                "campo": c, "soglia_A": sA, "soglia_B": sB,
                "ulp": n_ulp, "mock": esiti, "verdetto": verdetto}
    if out_path:
        op = Path(out_path)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps(rapporto, indent=2, ensure_ascii=True),
                      encoding="utf-8")
        print("\nscritto: %s" % op)
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

    print("selftest paper2_cammini_desi")

    # ULP: i due casi veri di questa sessione
    chk("NGC: 125.474151611328 -> 125.474166870117 vale 2 ULP",
        abs(distanza_ulp(125.474151611328, 125.474166870117) - 2.0) < 0.01,
        distanza_ulp(125.474151611328, 125.474166870117))
    chk("SGC: 161.669647216797 -> 161.670043945312 vale 26 ULP",
        abs(distanza_ulp(161.669647216797, 161.670043945312) - 26.0) < 0.01,
        distanza_ulp(161.669647216797, 161.670043945312))
    chk("la distanza e' simmetrica",
        abs(distanza_ulp(1.0, 1.0 + 4 * ulp32(1.0)) - 4.0) < 1e-6)
    chk("distanza nulla a valori uguali", distanza_ulp(3.5, 3.5) == 0.0)

    # conteggio fra le due soglie
    v = np.array([1.0, 100.0, 161.6696475, 161.6699, 161.67005, 200.0])
    s1, s2 = 161.669647216797, 161.670043945312
    atteso = int(((v > min(s1, s2)) & (v <= max(s1, s2))).sum())
    chk("il conteggio fra le due soglie e' calcolato, non atteso a memoria",
        fra_le_due(v, s1, s2) == atteso and atteso == 2, (fra_le_due(v, s1, s2), atteso))
    chk("l'ordine delle due soglie non conta",
        fra_le_due(v, s1, s2) == fra_le_due(v, s2, s1))
    chk("con valori lontani il conteggio e' zero",
        fra_le_due(np.array([1.0, 2.0, 300.0]), s1, s2) == 0)
    chk("l'intervallo e' semiaperto: il limite basso escluso, l'alto incluso",
        fra_le_due(np.array([s1]), s1, s2) == 0
        and fra_le_due(np.array([s2]), s1, s2) == 1)
    chk("e la differenza dei due conteggi e' esattamente quelli in mezzo",
        int((v > min(s1, s2)).sum()) - int((v > max(s1, s2)).sum())
        == fra_le_due(v, s1, s2))

    # confronto dei campi
    m = np.zeros((4, 4, 4), dtype=bool); m[0] = True
    A = np.zeros((4, 4, 4)); B = np.zeros((4, 4, 4))
    A[0, 0, 0] = 10.0; B[0, 0, 0] = 10.0 + 1e-6
    A[0, 1, 1] = 5.0;  B[0, 1, 1] = 5.0
    c = confronta_campi(A, B, m)
    chk("confronta_campi conta le celle diverse", c["n_celle_diverse"] == 1, c)
    chk("e trova lo stesso voxel al massimo", c["stesso_voxel_al_massimo"])
    chk("i due massimi differiscono di quanto la cella differisce",
        abs((c["max_B"] - c["max_A"]) - 1e-6) < 1e-15)
    B2 = B.copy(); B2[0, 0, 0] = 1.0; B2[0, 1, 1] = 99.0
    c2 = confronta_campi(A, B2, m)
    chk("se il massimo cambia cella lo dice",
        not c2["stesso_voxel_al_massimo"], c2)
    chk("il numero di voxel e' quello della maschera",
        c["n_voxel"] == int(m.sum()) == 16)

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("confronta")
    c.add_argument("--root", default=ROOT_DEFAULT)
    c.add_argument("--region", choices=["NGC", "SGC"], required=True)
    c.add_argument("--n-mock", dest="n_mock", type=int, default=5)
    c.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "confronta":
        return confronta(a.root, a.region, a.n_mock, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

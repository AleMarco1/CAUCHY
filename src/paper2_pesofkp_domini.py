#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_pesofkp_domini.py

Z-FKP: quale media di w_FKP vale 0.309, e quale vale 0.3168.

LA DOMANDA
----------
Paper 1 §7.2 scrive: «We extract the radial FKP weight w_FKP(z) from the random
catalogue (mean in-mask weight 0.309)». Il cancello 2.1-M ha misurato 0.3168
(NGC) e 0.3308 (SGC), e la checklist registra lo scarto come filo aperto,
notando che e' lo stesso peso che entra nell'ensemble v2.

Ma «peso medio in maschera» non identifica una quantita': identifica una
famiglia. La media si puo' prendere sui punti del random, sui punti dei dati,
sui bin della tabella, sui voxel della maschera senza pesare, o sui voxel
pesando per il conteggio. Sono numeri diversi della stessa cosa, e i due casi
sciolti in questa serie — 313 contro 445, e la mediana a n=100 sotto
un'intestazione n=200 — avevano entrambi questa forma: non «uno dei due e'
sbagliato», ma «sono medie su domini diversi».

SOLO NGC, E NON PER FRETTA
--------------------------
0.309 e' un numero NGC: Paper 1 §7.2 descrive il test di n6, e n6 come n10 ha
NGC nel corpo del codice (uscita, maschera, sorgente). Lo 0.3308 dell'SGC non
ha un valore pubblicato con cui essere in disaccordo: non e' una discrepanza,
e' un emisfero mai quotato. Estendere a SGC richiede la via S.sgc_positions ed
e' una domanda diversa.

LA TOLLERANZA E' LA QUOTAZIONE
------------------------------
0.309 ha tre decimali, quindi ammette mezza unita' dell'ultima cifra: 0.0005.
Un dominio «riproduce» il valore quotato se dista non piu' di quello. Lo 0.3168
dista 0.0078, cioe' 15.6 mezze unita': qualunque sia il dominio giusto, i due
numeri non sono lo stesso arrotondamento. Regola dichiarata prima di misurare.

NON CALCOLA NULLA DI PROPRIO
----------------------------
setup_region, cic_3d e la tabella w_FKP(z) sono importati; le colonne del FITS
si leggono con astropy come fa la pipeline. L'unica aritmetica qui e' la media,
in sette domini nominati.

USO
    python src\\paper2_pesofkp_domini.py selftest
    python src\\paper2_pesofkp_domini.py misura --out results\\paper2\\pesofkp_domini_NGC.json

Uscita: 0 sempre che la misura riesca; il verdetto sta nel testo e nel JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

QUOTATO_P1 = 0.309       # Paper 1 §7.2, «mean in-mask weight»
DECIMALI_P1 = 3
GATE_21M = 0.3168        # cancello 2.1-M, NGC
DECIMALI_21M = 4
REGIONE = "NGC"
ROOT_DEFAULT = r"D:\projects\cauchy"


def ammesso(decimali):
    """Mezza unita' dell'ultima cifra quotata."""
    return 0.5 * 10.0 ** (-decimali)


def distanza_in_mezze_unita(valore, quotato, decimali):
    return abs(float(valore) - float(quotato)) / ammesso(decimali)


def media_per_voxel(campo_pesato, campo_conteggio, maschera, pesata_dal_conteggio):
    """
    Peso medio per voxel dentro maschera.
      pesata_dal_conteggio=False : media semplice dei rapporti voxel per voxel
      pesata_dal_conteggio=True  : somma dei pesi / somma dei conteggi
    Sono due numeri diversi, ed e' esattamente la distinzione che puo' valere
    qualche punto percentuale.
    """
    sel = maschera & (campo_conteggio > 0)
    if not sel.any():
        return float("nan"), 0
    if pesata_dal_conteggio:
        return (float(campo_pesato[sel].sum() / campo_conteggio[sel].sum()),
                int(sel.sum()))
    return float((campo_pesato[sel] / campo_conteggio[sel]).mean()), int(sel.sum())


def misura(root, out_path=None):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M          # noqa: E402
    import paper1_remap as P1                # noqa: E402
    from astropy.io import fits              # noqa: E402

    print("=" * 78)
    print("Z-FKP — DOMINI DI MEDIA DEL PESO FKP  |  %s" % REGIONE)
    print("quotato Paper 1 §7.2: %.3f   cancello 2.1-M: %.4f" % (QUOTATO_P1, GATE_21M))
    print("tolleranza = mezza unita' dell'ultima cifra: %.4f e %.5f"
          % (ammesso(DECIMALI_P1), ammesso(DECIMALI_21M)))
    print("=" * 78)

    dom = {}

    # --- catalogo dei random -------------------------------------------------
    with fits.open(M.RAN_FITS) as h:
        r = h["LSS"].data
        mz = (r["Z"] >= M.ZMIN) & (r["Z"] <= M.ZMAX)
        z_r = r["Z"][mz].astype(np.float64)
        w_r = r["WEIGHT_FKP"][mz].astype(np.float64)
        ra_r = r["RA"][mz].astype(np.float64)
        dec_r = r["DEC"][mz].astype(np.float64)
    print("  random: %d punti in z ∈ [%.2f, %.2f]" % (z_r.size, M.ZMIN, M.ZMAX))
    dom["1_random_punti_media"] = float(w_r.mean())
    dom["2_random_punti_mediana"] = float(np.median(w_r))

    # --- tabella w_FKP(z) a 60 bin, mediana per bin --------------------------
    cache = root / "results" / "paper1" / "n6_wfkp_table.npz"
    if cache.is_file():
        d = np.load(cache)
        zt, wt = d["z"], d["w"]
        print("  tabella: %d bin, dalla cache di n6" % len(zt))
        dom["3_tabella_media_sui_bin"] = float(wt.mean())
        dom["4_tabella_interpolata_sui_random"] = float(np.interp(z_r, zt, wt).mean())
    else:
        print("  [!] cache della tabella assente: %s" % cache)
        dom["3_tabella_media_sui_bin"] = None
        dom["4_tabella_interpolata_sui_random"] = None

    # --- catalogo dei dati ---------------------------------------------------
    dat = M.DESI_DIR / "BGS_BRIGHT-21.5_NGC_clustering.dat.fits"
    with fits.open(dat) as h:
        dd = h["LSS"].data
        mzd = (dd["Z"] >= M.ZMIN) & (dd["Z"] <= M.ZMAX)
        w_d = dd["WEIGHT_FKP"][mzd].astype(np.float64)
    print("  dati  : %d punti" % w_d.size)
    dom["5_dati_punti_media"] = float(w_d.mean())

    # --- voxel dentro maschera ----------------------------------------------
    G = P1.setup_region(M, REGIONE, root / "data" / "raw" / "desi_dr1",
                        root / "data" / "processed" / "phase6_fields")
    mask = G["mask"]
    field_wr = np.asarray(G["field_r"], dtype=np.float64)   # CIC con WEIGHT_FKP

    dC = M.comoving_distance(z_r)
    rr, dr = np.radians(ra_r), np.radians(dec_r)
    pos_r = np.column_stack([dC * np.cos(dr) * np.cos(rr),
                             dC * np.cos(dr) * np.sin(rr),
                             dC * np.sin(dr)])
    field_1r = M.cic_3d(pos_r, np.ones(len(pos_r)), M.NGRID, M.BOX_MIN, M.BOX_SIZE)

    v6, n6v = media_per_voxel(field_wr, field_1r, mask, False)
    v7, n7v = media_per_voxel(field_wr, field_1r, mask, True)
    dom["6_voxel_in_maschera_media_semplice"] = v6
    dom["7_voxel_in_maschera_pesata_dal_conteggio"] = v7
    print("  voxel : %d in maschera con random dentro (su %d di maschera)"
          % (n6v, int(mask.sum())))

    # --- galassie mock, dal registro di n6 -----------------------------------
    reg = root / "results" / "paper1" / "n6_fkp_NGC.jsonl"
    if reg.is_file():
        vals = []
        with reg.open("r", encoding="utf-8") as fh:
            for riga in fh:
                riga = riga.strip()
                if riga:
                    rec = json.loads(riga)
                    if "wfkp_mean" in rec:
                        vals.append(float(rec["wfkp_mean"]))
        if vals:
            dom["8_galassie_mock_media_su_%d_realizzazioni" % len(vals)] = \
                float(np.mean(vals))

    # --- verdetto ------------------------------------------------------------
    print("\n%-46s %10s %12s %12s" % ("dominio", "media", "da 0.309", "da 0.3168"))
    print("%s" % ("-" * 84))
    esiti = {}
    for k in sorted(dom):
        v = dom[k]
        if v is None:
            print("%-46s %10s" % (k, "assente"))
            continue
        d1 = distanza_in_mezze_unita(v, QUOTATO_P1, DECIMALI_P1)
        d2 = distanza_in_mezze_unita(v, GATE_21M, DECIMALI_21M)
        esiti[k] = {"valore": v, "mezze_unita_da_P1": d1, "mezze_unita_da_21M": d2,
                    "riproduce_P1": d1 <= 1.0, "riproduce_21M": d2 <= 1.0}
        marca1 = " <-- 0.309" if d1 <= 1.0 else ""
        marca2 = " <-- 0.3168" if d2 <= 1.0 else ""
        print("%-46s %10.6f %12.1f %12.1f%s%s" % (k, v, d1, d2, marca1, marca2))

    p1 = [k for k, e in esiti.items() if e["riproduce_P1"]]
    g21 = [k for k, e in esiti.items() if e["riproduce_21M"]]
    print("\n  riproduce 0.309 di Paper 1 §7.2 : %s" % (", ".join(p1) or "NESSUNO"))
    print("  riproduce 0.3168 di 2.1-M       : %s" % (", ".join(g21) or "NESSUNO"))
    if p1 and g21:
        print("\n  Z-FKP si scioglie: i due numeri sono medie su domini diversi,")
        print("  entrambe corrette. Va scritto QUALE dominio ciascuno usa.")
    elif not p1:
        print("\n  Nessuno dei sette domini riproduce 0.309: il valore quotato viene")
        print("  da un calcolo che non e' fra questi, e va cercato nel codice che")
        print("  lo ha prodotto prima di usarlo come riferimento.")

    rapporto = {"schema": "paper2_pesofkp_domini_v1", "region": REGIONE,
                "utc": datetime.now(timezone.utc).isoformat(),
                "quotato_P1": QUOTATO_P1, "decimali_P1": DECIMALI_P1,
                "gate_21M": GATE_21M, "decimali_21M": DECIMALI_21M,
                "n_random": int(z_r.size), "n_dati": int(w_d.size),
                "n_voxel_maschera": int(mask.sum()), "n_voxel_con_random": n6v,
                "domini": esiti,
                "riproducono_P1": p1, "riproducono_21M": g21}
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

    print("selftest paper2_pesofkp_domini")

    chk("valori quotati e loro decimali dichiarati",
        QUOTATO_P1 == 0.309 and DECIMALI_P1 == 3
        and GATE_21M == 0.3168 and DECIMALI_21M == 4)
    chk("solo NGC, dichiarato", REGIONE == "NGC")
    chk("ammesso a 3 decimali e' 0.0005", ammesso(3) == 0.0005)
    chk("ammesso a 4 decimali e' 0.00005", ammesso(4) == 0.00005)

    chk("0.3168 dista da 0.309 piu' di una mezza unita'",
        distanza_in_mezze_unita(GATE_21M, QUOTATO_P1, DECIMALI_P1) > 1.0,
        distanza_in_mezze_unita(GATE_21M, QUOTATO_P1, DECIMALI_P1))
    chk("e la distanza vale circa 15.6 mezze unita'",
        abs(distanza_in_mezze_unita(GATE_21M, QUOTATO_P1, DECIMALI_P1) - 15.6) < 0.1)
    chk("0.30949 riprodurrebbe 0.309, 0.30951 no",
        distanza_in_mezze_unita(0.30949, QUOTATO_P1, DECIMALI_P1) <= 1.0
        and distanza_in_mezze_unita(0.30951 + 1e-9, QUOTATO_P1, DECIMALI_P1) > 1.0)

    # media per voxel: le due varianti devono differire quando i conteggi variano
    m = np.zeros((4, 4, 4), dtype=bool); m[:2] = True
    conteggio = np.zeros((4, 4, 4)); conteggio[:2] = 1.0; conteggio[0] = 9.0
    pesato = np.zeros((4, 4, 4)); pesato[:2] = 0.5; pesato[0] = 0.9  # 0.1 per unita'
    semplice, n1 = media_per_voxel(pesato, conteggio, m, False)
    pesata, n2 = media_per_voxel(pesato, conteggio, m, True)
    chk("media semplice per voxel: (0.1 + 0.5)/2 = 0.30",
        abs(semplice - 0.30) < 1e-12, semplice)
    chk("media pesata dal conteggio: 1.4/10 = 0.14",
        abs(pesata - 0.14) < 1e-12, pesata)
    chk("le due varianti NON coincidono quando i conteggi variano",
        abs(semplice - pesata) > 0.1)
    chk("contano gli stessi voxel", n1 == n2 == 32, (n1, n2))

    conteggio2 = np.ones((4, 4, 4))
    pesato2 = np.full((4, 4, 4), 0.4)
    a, _ = media_per_voxel(pesato2, conteggio2, m, False)
    b, _ = media_per_voxel(pesato2, conteggio2, m, True)
    chk("a conteggi uguali le due varianti coincidono", abs(a - b) < 1e-12)

    vuota = np.zeros((4, 4, 4), dtype=bool)
    v, n = media_per_voxel(pesato, conteggio, vuota, False)
    chk("maschera vuota: nan e zero voxel, non un'eccezione",
        np.isnan(v) and n == 0)

    zero = np.zeros((4, 4, 4))
    v2, n3 = media_per_voxel(pesato, zero, m, False)
    chk("voxel senza random sono esclusi, non divisi per zero",
        np.isnan(v2) and n3 == 0)

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("misura")
    m.add_argument("--root", default=ROOT_DEFAULT)
    m.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "misura":
        return misura(a.root, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

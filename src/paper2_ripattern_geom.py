#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_ripattern_geom.py - la diagnostica geometrica del ripattern. Item 3.2d.

QUANTIFICA CIO' CHE IL REFEREE NOMINA E CHE NON ESISTEVA
--------------------------------------------------------
    «sotto deformazione cambia QUALI celle del box finiscono dove»

Per ogni voxel in-survey si calcola la cella del box periodico da cui proviene, a
B1 e a B5, e si riporta la frazione di voxel la cui cella sorgente CAMBIA.

Nessun mock: e' sola geometria. Il tiling e' una traslazione per multipli interi
di L_box, quindi il punto P dell'embedding cube proviene da UNA sola posizione
nel box, mod(P, L_box), e la sua cella e' floor(mod(P, L_box) / passo).

L'ASSUNZIONE, dichiarata
------------------------
Si confronta il voxel di indice (i,j,k) a B1 con lo STESSO indice a B5. E' la
lettura giusta perche' nel gauge dell'emendamento 13 il lato del cubo e' fisso e
la cella pure: fra i due punti la griglia trasla senza deformarsi, quindi
l'indice individua la stessa posizione nella griglia. Se L o cell differissero
fra i due punti il confronto per indice non avrebbe senso, e lo strumento SI
FERMA invece di produrre un numero.

DUE VIE, E IL CONFRONTO FRA LORO
--------------------------------
La geometria si prende in due modi e si confrontano:
  * RIDERIVATA, dal percorso canonico -- paper2_runner_fase3_mock._prepare, la
    stessa funzione che i run usano;
  * DEPOSITATA, da results/paper2/fase3.jsonl, campi box_min, box_size, cell.
Se non coincidono lo strumento si ferma: una diagnostica che gira su una
geometria diversa da quella dei run non dice niente sui run.

Sottocomandi
------------
  geom       confronta riderivata e depositata. Non calcola il ripattern.
  run        il confronto, poi la diagnostica. Scrive solo con --out.
  selftest   geometria sintetica a ripattern NOTO. Non tocca niente.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import types

import numpy as np

DEFAULT_FASE3 = os.path.join("results", "paper2", "fase3.jsonl")
PUNTI = ("B1", "B5")
TOL_REL = 1e-9


def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Geometria depositata
# ---------------------------------------------------------------------------

def leggi_depositata(path, region, punti=PUNTI):
    """box_min, box_size, cell per punto, dal registro del lato dati."""
    if not os.path.isfile(path):
        fail("registro assente: %s" % path)
    out = {}
    with open(path, "rb") as fh:
        raw = fh.read()
    for ln in raw.replace(b"\r\n", b"\n").split(b"\n"):
        if not ln.strip():
            continue
        r = json.loads(ln.decode("utf-8"))
        if r.get("region") != region or r.get("point") not in punti:
            continue
        if r.get("gauge") != "regauged":
            continue
        for k in ("box_min", "box_size", "cell", "n_valid_voxels"):
            if k not in r:
                fail("campo %r assente per %s/%s: il registro non ha la forma "
                     "attesa." % (k, region, r.get("point")))
        out[r["point"]] = {
            "box_min": np.asarray(r["box_min"], float),
            "box_size": float(r["box_size"]),
            "cell": float(r["cell"]),
            "n_valid_voxels": int(r["n_valid_voxels"]),
        }
    manca = [p for p in punti if p not in out]
    if manca:
        fail("punti assenti dal registro depositato: %s" % manca)
    return out


# ---------------------------------------------------------------------------
# Geometria riderivata, dal percorso canonico
# ---------------------------------------------------------------------------

def riderivata(srcdir, root, region, punti=PUNTI):
    srcdir = os.path.abspath(srcdir)
    if srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    try:
        import paper2_runner_fase3_mock as R
    except Exception as exc:
        fail("non riesco a importare paper2_runner_fase3_mock: %s" % exc)
    if not hasattr(R, "_prepare"):
        fail("paper2_runner_fase3_mock non espone _prepare: la firma e' "
             "cambiata, non indovino.")
    a = types.SimpleNamespace(src=srcdir, project_root=root, region=region,
                              no_cache_gate=False, points=list(punti) + ["FID"])
    out = R._prepare(a, a.points)
    M, geoms = out[0], out[6]
    manca = [p for p in punti if p not in geoms]
    if manca:
        fail("build_geometries non ha prodotto %s" % manca)
    res = {}
    for p in punti:
        g = geoms[p]
        for k in ("box_min", "box_size", "mask"):
            if k not in g:
                fail("la geometria riderivata di %s non ha %r" % (p, k))
        bs = float(g["box_size"])
        res[p] = {
            "box_min": np.asarray(g["box_min"], float),
            "box_size": bs,
            "cell": bs / float(M.NGRID),
            "mask": np.asarray(g["mask"]),
            "ngrid": int(M.NGRID),
        }
    res["_BOXSIZE_MOCK"] = float(M.BOXSIZE_MOCK)
    return res


def confronta(dep, rid, punti=PUNTI):
    """(righe, problemi). Il cancello: le due vie devono coincidere."""
    righe, bad = [], []
    for p in punti:
        d, r = dep[p], rid[p]
        dbm = float(np.max(np.abs(d["box_min"] - r["box_min"])))
        dbs = abs(d["box_size"] - r["box_size"]) / d["box_size"]
        dc = abs(d["cell"] - r["cell"]) / d["cell"]
        nv = int(r["mask"].sum())
        righe.append((p, dbm, dbs, dc, d["n_valid_voxels"], nv))
        if dbm > TOL_REL * d["box_size"]:
            bad.append("%s: box_min differisce di %.3e" % (p, dbm))
        if dbs > TOL_REL:
            bad.append("%s: box_size rel %.3e" % (p, dbs))
        if dc > TOL_REL:
            bad.append("%s: cell rel %.3e" % (p, dc))
        if nv != d["n_valid_voxels"]:
            bad.append("%s: voxel in maschera %d contro %d depositati"
                       % (p, nv, d["n_valid_voxels"]))
    return righe, bad


# ---------------------------------------------------------------------------
# La diagnostica
# ---------------------------------------------------------------------------

def celle_sorgente(box_min, cell, ngrid, boxsize_mock, mask):
    """Indice lineare della cella del box periodico per ogni voxel in maschera.

    Il passo del box e' L_box / nb con nb il numero intero di celle piu' vicino,
    come in rev1_r11_tiling: una cella del box e' un elemento di risoluzione
    della griglia d'analisi.
    """
    nb = int(round(boxsize_mock / cell))
    passo = boxsize_mock / nb
    idx = np.nonzero(mask)
    out = np.empty(len(idx[0]), dtype=np.int64)
    centri = [box_min[ax] + (idx[ax].astype(np.float64) + 0.5) * cell
              for ax in range(3)]
    cid = [np.clip((np.mod(c, boxsize_mock) / passo).astype(np.int64), 0, nb - 1)
           for c in centri]
    out[:] = (cid[0] * nb + cid[1]) * nb + cid[2]
    return out, idx, nb


def diagnostica(rid, punti=PUNTI):
    a, b = punti
    ga, gb = rid[a], rid[b]
    if ga["ngrid"] != gb["ngrid"]:
        fail("NGRID diverso fra i due punti: il confronto per indice non ha senso.")
    if abs(ga["cell"] - gb["cell"]) / ga["cell"] > 1e-12:
        fail("la cella differisce fra %s e %s (%.12g contro %.12g): fra i due "
             "punti la griglia non trasla soltanto, e il confronto per indice "
             "non ha senso. Non produco un numero." % (a, b, ga["cell"], gb["cell"]))
    comune = ga["mask"] & gb["mask"]
    n_com = int(comune.sum())
    if n_com == 0:
        fail("nessun voxel in maschera a entrambi i punti.")
    ca, _, nb = celle_sorgente(ga["box_min"], ga["cell"], ga["ngrid"],
                               rid["_BOXSIZE_MOCK"], comune)
    cb, _, _ = celle_sorgente(gb["box_min"], gb["cell"], gb["ngrid"],
                              rid["_BOXSIZE_MOCK"], comune)
    diverse = ca != cb
    shift = float(np.max(np.abs(gb["box_min"] - ga["box_min"]))) / ga["cell"]
    # LARGHEZZA DELLA BANDA DI FASE. I centri di voxel non riempiono la cella
    # del box in modo uniforme: la fase deriva di |1 - cell/passo| per voxel.
    # Se la banda e' molto piu' stretta di 1 la quantita' e' quasi BINARIA -- i
    # centri si spostano tutti insieme -- e un 0% o un 100% non discrimina. Se
    # e' dell'ordine di 1 la quantita' misura davvero. Va riportata SEMPRE.
    passo_box = rid["_BOXSIZE_MOCK"] / nb
    # La fase e' CIRCOLARE: max - min la sovrastima quando avvolge lo zero.
    # Il primo giro riportava 0.999 su due assi e 0.167 sul terzo -- non tre
    # geometrie diverse, ma due che avvolgevano. La banda circolare e'
    # 1 - (il piu' grande vuoto fra fasi consecutive ordinate).
    fasi = []
    for ax in range(3):
        c = ga["box_min"][ax] + (np.arange(ga["ngrid"]) + 0.5) * ga["cell"]
        f = np.sort(np.mod(c, passo_box) / passo_box)
        if f.size < 2:
            fasi.append(0.0)
            continue
        vuoti = np.diff(f)
        vuoti = np.append(vuoti, 1.0 - f[-1] + f[0])   # il vuoto che avvolge
        fasi.append(float(1.0 - vuoti.max()))
    banda = float(max(fasi))
    return {
        "n_voxel_comuni": n_com,
        "n_solo_%s" % a: int((ga["mask"] & ~gb["mask"]).sum()),
        "n_solo_%s" % b: int((gb["mask"] & ~ga["mask"]).sum()),
        "frazione_cella_cambiata": float(diverse.mean()),
        "n_cella_cambiata": int(diverse.sum()),
        "celle_distinte_%s" % a: int(np.unique(ca).size),
        "celle_distinte_%s" % b: int(np.unique(cb).size),
        "n_celle_box": nb ** 3,
        "passo_box": rid["_BOXSIZE_MOCK"] / nb,
        "spostamento_box_min_voxel": shift,
        "banda_di_fase": banda,
        "banda_di_fase_per_asse": fasi,
        "quasi_binaria": bool(banda < 0.2),
    }


# ---------------------------------------------------------------------------
# Sottocomandi
# ---------------------------------------------------------------------------

def _prep(args):
    dep = leggi_depositata(args.fase3, args.region)
    rid = riderivata(args.src, args.project_root, args.region)
    righe, bad = confronta(dep, rid)
    print("=== GEOMETRIA: riderivata contro depositata, %s ===" % args.region)
    print("  %-4s %14s %12s %12s %10s %10s"
          % ("pt", "d box_min", "d box_size", "d cell", "voxel dep", "voxel rid"))
    for p, dbm, dbs, dc, nvd, nvr in righe:
        print("  %-4s %14.3e %12.3e %12.3e %10d %10d"
              % (p, dbm, dbs, dc, nvd, nvr))
    if bad:
        print("")
        for x in bad:
            print("  DISCORDE: %s" % x)
        fail("le due vie non coincidono: una diagnostica su una geometria "
             "diversa da quella dei run non dice niente sui run.")
    print("  [ok] le due vie coincidono entro %.0e" % TOL_REL)
    return dep, rid


def cmd_scan(args):
    """La frazione dipende dalla FASE ASSOLUTA della griglia, che e' arbitraria.

    Si trasla in blocco ENTRAMBE le griglie di uno stesso offset -- il che
    equivale a un'origine dell'embedding diversa -- e si guarda quanto la
    frazione si muove. Lo spostamento RELATIVO fra B1 e B5, che e' fisico,
    resta invariato per costruzione.

    La tabella offset -> frazione serve a SCEGLIERE le configurazioni del test
    del §C prima di spendere ore di macchina.
    """
    dep, rid = _prep(args)
    base = diagnostica(rid)
    nb = int(round(rid["_BOXSIZE_MOCK"] / rid["B1"]["cell"]))
    passo = rid["_BOXSIZE_MOCK"] / nb
    n = args.n_scan
    fr = []
    for k in range(n):
        off = passo * k / n
        r2 = {"_BOXSIZE_MOCK": rid["_BOXSIZE_MOCK"]}
        for p_ in PUNTI:
            g = rid[p_]
            r2[p_] = dict(g, box_min=g["box_min"] + off)
        fr.append(diagnostica(r2)["frazione_cella_cambiata"])
    fr = np.asarray(fr)
    print("")
    print("=== STABILITA' ALLA FASE ASSOLUTA, %s ===" % args.region)
    print("  %d traslazioni in blocco su un passo del box (%.6f)" % (n, passo))
    print("  lo spostamento RELATIVO fra B1 e B5 e' invariato per costruzione")
    print("")
    print("  frazione osservata     : %.2f%%" % (100 * base["frazione_cella_cambiata"]))
    print("  sullo scan  min / max  : %.2f%% / %.2f%%" % (100 * fr.min(), 100 * fr.max()))
    print("  mediana / scarto tipo  : %.2f%% / %.2f%%"
          % (100 * float(np.median(fr)), 100 * float(fr.std())))
    print("  escursione             : %.2f punti percentuali"
          % (100 * (fr.max() - fr.min())))
    print("")
    print("  offset (h^-1 Mpc)   frazione  |   offset   frazione")
    meta = (n + 1) // 2
    for k in range(meta):
        riga = "  %15.4f  %9.2f%%" % (passo * k / n, 100 * fr[k])
        j = k + meta
        if j < n:
            riga += "  | %9.4f %9.2f%%" % (passo * j / n, 100 * fr[j])
        print(riga)
    i_lo, i_hi = int(np.argmin(fr)), int(np.argmax(fr))
    print("")
    print("  DUE CONFIGURAZIONI per il test del §C:")
    print("    offset %.6f  ->  frazione %.2f%%" % (passo * i_lo / n, 100 * fr[i_lo]))
    print("    offset %.6f  ->  frazione %.2f%%" % (passo * i_hi / n, 100 * fr[i_hi]))
    print("    Lo spostamento RELATIVO e' lo stesso nelle due: cambia la fase, e")
    print("    con essa quanto ripattern c'e'. Se Delta_ripattern segue la")
    print("    frazione, il meccanismo e' il ripattern. Se non la segue, la")
    print("    frazione non e' la leva.")
    print("")
    stabile = (fr.max() - fr.min()) < 0.15
    if stabile:
        print("  STABILE: la frazione non dipende sensibilmente dalla fase.")
    else:
        print("  NON stabile: la frazione si muove di %.0f punti percentuali al"
              % (100 * (fr.max() - fr.min())))
        print("  variare di una scelta ARBITRARIA (l'origine dell'embedding). Il")
        print("  valore osservato va riportato CON questo intervallo.")
    if args.out:
        rec = {"schema": "paper2_ripattern_geom_scan_v1", "region": args.region,
               "n_scan": n, "passo_box": passo,
               "frazione_osservata": base["frazione_cella_cambiata"],
               "scan_min": float(fr.min()), "scan_max": float(fr.max()),
               "scan_mediana": float(np.median(fr)), "scan_sd": float(fr.std()),
               "stabile": bool(stabile),
               "banda_di_fase": base["banda_di_fase"],
               "spostamento_box_min_voxel": base["spostamento_box_min_voxel"],
               "offset_frazione": [[float(passo * k / n), float(fr[k])]
                                   for k in range(n)],
               "offset_lo": float(passo * i_lo / n),
               "offset_hi": float(passo * i_hi / n),
               "frazione_lo": float(fr.min()), "frazione_hi": float(fr.max())}
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print("  scritto in %s" % args.out)
    return 0


def cmd_geom(args):
    _prep(args)
    return 0


def cmd_run(args):
    dep, rid = _prep(args)
    d = diagnostica(rid)
    print("")
    print("=== RIPATTERN GEOMETRICO  B1 -> B5,  %s ===" % args.region)
    print("  voxel in maschera a ENTRAMBI i punti : %d" % d["n_voxel_comuni"])
    print("  solo B1 / solo B5                    : %d / %d"
          % (d["n_solo_B1"], d["n_solo_B5"]))
    print("  griglia del box                      : %d celle, passo %.6f"
          % (d["n_celle_box"], d["passo_box"]))
    print("  celle distinte usate  B1 / B5        : %d / %d"
          % (d["celle_distinte_B1"], d["celle_distinte_B5"]))
    print("  spostamento di box_min               : %.4f voxel"
          % d["spostamento_box_min_voxel"])
    print("  banda di fase, per asse              : %s"
          % ", ".join("%.3f" % f for f in d["banda_di_fase_per_asse"]))
    print("")
    print("  VOXEL LA CUI CELLA SORGENTE CAMBIA   : %d  =  %.2f%%"
          % (d["n_cella_cambiata"], 100.0 * d["frazione_cella_cambiata"]))
    print("")
    if d["quasi_binaria"]:
        print("  ATTENZIONE: banda di fase %.3f, molto minore di 1. I centri di"
              % d["banda_di_fase"])
        print("  voxel stanno quasi tutti alla stessa fase dentro la cella del")
        print("  box, quindi si spostano INSIEME e la quantita' e' quasi")
        print("  BINARIA: un 0%% o un 100%% qui non discrimina, e va letto come")
        print("  tale invece che come una misura di quanto ripattern ci sia.")
        print("")
    print("  Lettura DICHIARATA prima del calcolo (item 3.2d §5): questa")
    print("  quantita' e' DESCRITTIVA. Non ha soglia e non decide niente: dice")
    print("  quanto ripattern c'e' da rilevare, non se rilevarlo importi. Il")
    print("  verdetto resta quello del run, emendamento 44.")
    if args.out:
        rec = dict(d)
        rec.update({"schema": "paper2_ripattern_geom_v1", "region": args.region,
                    "punti": list(PUNTI),
                    "voxel_depositati": {p: dep[p]["n_valid_voxels"] for p in PUNTI},
                    "lettura": "descrittiva, senza soglia, dichiarata nell'item 3.2d"})
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print("  scritto in %s" % args.out)
    return 0


def cmd_selftest(args):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # Numeri REALISTICI: cell e passo del box sono INCOMMENSURABILI
    # (15.6044 contro 15.625), ed e' questo che rende la quantita' non
    # degenere. Con cell == passo tutti i centri stanno alla stessa fase e
    # mezzo passo li farebbe saltare TUTTI insieme: il sintetico darebbe 100%
    # e non 50%. Un fixture troppo regolare valida uno scenario che non e'
    # quello vero.
    NG, CELL, LBOX = 32, 15.604397786848558, 1000.0
    L = NG * CELL
    mask = np.zeros((NG, NG, NG), bool)
    mask[4:28, 4:28, 4:28] = True

    def geom(shift):
        return {"box_min": np.array([shift, 0.0, 0.0]), "box_size": L,
                "cell": CELL, "mask": mask, "ngrid": NG}

    # 1. spostamento NULLO -> nessuna cella cambia
    rid = {"B1": geom(0.0), "B5": geom(0.0), "_BOXSIZE_MOCK": LBOX}
    d = diagnostica(rid)
    chk("1  spostamento nullo: nessuna cella sorgente cambia",
        d["n_cella_cambiata"] == 0, "%.4f%%" % (100 * d["frazione_cella_cambiata"]))

    # 2. spostamento di UNA cella del box -> TUTTE cambiano
    passo = LBOX / round(LBOX / CELL)
    rid2 = {"B1": geom(0.0), "B5": geom(passo), "_BOXSIZE_MOCK": LBOX}
    d2 = diagnostica(rid2)
    chk("2  spostamento di un passo del box: TUTTE le celle cambiano",
        d2["frazione_cella_cambiata"] == 1.0,
        "%.2f%%" % (100 * d2["frazione_cella_cambiata"]))

    # 3. La banda di fase decide se la quantita' MISURA o e' binaria. Due
    #    regimi, entrambi provati: rapporto cell/passo vicino a 1 -> banda
    #    stretta -> quasi binaria; rapporto lontano da 1 -> banda larga ->
    #    valori intermedi. La prima versione di questo controllo pretendeva
    #    "circa meta'" e falliva: l'attesa era mia e non giustificata.
    def scan(cell, lbox, n=20):
        def g(sh):
            return {"box_min": np.array([sh, 0.0, 0.0]), "box_size": NG * cell,
                    "cell": cell, "mask": mask, "ngrid": NG}
        ps = lbox / round(lbox / cell)
        outs = [diagnostica({"B1": g(0.0), "B5": g(ps * k / n),
                             "_BOXSIZE_MOCK": lbox}) for k in range(1, n)]
        return ([o["frazione_cella_cambiata"] for o in outs],
                outs[0]["banda_di_fase"])

    fr_s, banda_s = scan(CELL, LBOX)
    # Per una banda LARGA serve un nb piccolo: `nb = round(L_box/cell)` fa
    # inseguire il passo alla cella, quindi il rapporto resta vicino a 1 per
    # costruzione e la banda vale al piu' N/(2*nb). Con nb = 8 invece di 64 la
    # banda diventa dell'ordine di 1. Nel caso reale nb = 64 e N = 128, quindi
    # il massimo possibile e' 1.0 e l'osservato e' 0.17: informativa, ma non
    # al suo massimo.
    fr_l, banda_l = scan(11.8, 100.0)
    chk("3  banda STRETTA (%.3f): la quantita' e' quasi binaria" % banda_s,
        banda_s < 0.2 and sum(1 for f in fr_s if 0.02 < f < 0.98) <= 2,
        "intermedi %d su %d" % (sum(1 for f in fr_s if 0.02 < f < 0.98), len(fr_s)))
    chk("3a banda LARGA (%.3f): compaiono valori intermedi" % banda_l,
        banda_l > 0.5 and sum(1 for f in fr_l if 0.02 < f < 0.98) >= 5,
        "intermedi %d su %d, min %.2f max %.2f"
        % (sum(1 for f in fr_l if 0.02 < f < 0.98), len(fr_l),
           min(fr_l), max(fr_l)))
    # 3c la banda e' CIRCOLARE: una fase che avvolge lo zero non deve dare 1.
    cerchio = np.array([0.98, 0.99, 0.00, 0.01, 0.02])
    vuoti = np.append(np.diff(np.sort(cerchio)),
                      1.0 - np.sort(cerchio)[-1] + np.sort(cerchio)[0])
    chk("3c la banda e' circolare: fasi attorno a zero danno %.2f, non ~1"
        % (1.0 - vuoti.max()), abs((1.0 - vuoti.max()) - 0.04) < 1e-9,
        "max-min direbbe %.2f" % (cerchio.max() - cerchio.min()))
    chk("3b lo strumento DICHIARA da se' quando e' quasi binaria",
        diagnostica({"B1": geom(0.0), "B5": geom(0.0),
                     "_BOXSIZE_MOCK": LBOX})["quasi_binaria"] is True)

    # 3d una traslazione IN BLOCCO non cambia lo spostamento relativo: e' la
    #    proprieta' su cui poggia lo scan.
    sh = passo * 0.3
    a0 = diagnostica({"B1": geom(0.0), "B5": geom(sh), "_BOXSIZE_MOCK": LBOX})
    a1 = diagnostica({"B1": geom(passo * 0.47), "B5": geom(passo * 0.47 + sh),
                      "_BOXSIZE_MOCK": LBOX})
    chk("3d traslare in blocco lascia invariato lo spostamento RELATIVO",
        abs(a0["spostamento_box_min_voxel"]
            - a1["spostamento_box_min_voxel"]) < 1e-9,
        "%.6f contro %.6f" % (a0["spostamento_box_min_voxel"],
                              a1["spostamento_box_min_voxel"]))

    # 4. maschere diverse: si usa l'INTERSEZIONE e i due esclusivi si contano
    m2 = mask.copy()
    m2[4, 4, 4] = False
    r4 = {"B1": geom(0.0), "B5": dict(geom(0.0), mask=m2), "_BOXSIZE_MOCK": LBOX}
    d4 = diagnostica(r4)
    chk("4  maschere diverse: intersezione, e gli esclusivi contati",
        d4["n_voxel_comuni"] == int(mask.sum()) - 1 and d4["n_solo_B1"] == 1
        and d4["n_solo_B5"] == 0)

    # 5. celle diverse fra i punti: SI FERMA invece di produrre un numero
    r5 = {"B1": geom(0.0), "B5": dict(geom(0.0), cell=CELL * 1.01),
          "_BOXSIZE_MOCK": LBOX}
    chk("5  cella diversa fra i punti: ARRESTA, non produce un numero",
        _exits(lambda: diagnostica(r5)))

    # 6. il cancello geometrico respinge una discordanza
    dep = {p: {"box_min": np.zeros(3), "box_size": L, "cell": CELL,
               "n_valid_voxels": int(mask.sum())} for p in PUNTI}
    _, bad = confronta(dep, {"B1": geom(0.0), "B5": geom(0.0)})
    chk("6  cancello geometrico: due vie coincidenti passano", not bad, str(bad))
    _, bad2 = confronta(dep, {"B1": geom(0.0), "B5": geom(1.0)})
    chk("6b cancello geometrico: box_min discorde viene respinto",
        any("box_min" in x for x in bad2), str(bad2))
    dep_bad = {p: dict(v, n_valid_voxels=v["n_valid_voxels"] + 1)
               for p, v in dep.items()}
    _, bad3 = confronta(dep_bad, {"B1": geom(0.0), "B5": geom(0.0)})
    chk("6c cancello geometrico: conteggio voxel discorde viene respinto",
        len(bad3) == 2, str(bad3[:1]))

    # 7. il conteggio delle celle distinte e' sensato
    chk("7  celle distinte <= voxel e <= celle del box",
        d["celle_distinte_B1"] <= d["n_voxel_comuni"]
        and d["celle_distinte_B1"] <= d["n_celle_box"],
        "%d distinte su %d voxel, %d celle del box"
        % (d["celle_distinte_B1"], d["n_voxel_comuni"], d["n_celle_box"]))

    print("=== SELFTEST paper2_ripattern_geom ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def _exits(fn):
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def main():
    # Le opzioni stanno sul SOTTOCOMANDO. argparse vuole quelle del padre PRIMA
    # del sottocomando, e `--out` dopo `run` verrebbe rifiutato. Stesso errore
    # gia' commesso in paper2_surrogato_fit.py: qui e' corretto alla fonte.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--src", default="src")
    common.add_argument("--project_root", default=".")
    common.add_argument("--fase3", default=DEFAULT_FASE3)
    common.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    common.add_argument("--out", default=None)
    common.add_argument("--n-scan", type=int, default=32,
                        dest="n_scan", metavar="N")

    p = argparse.ArgumentParser(
        description="Diagnostica geometrica del ripattern (item 3.2d)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("geom", parents=[common]).set_defaults(func=cmd_geom)
    sub.add_parser("run", parents=[common]).set_defaults(func=cmd_run)
    sub.add_parser("scan", parents=[common]).set_defaults(func=cmd_scan)
    sub.add_parser("selftest", parents=[common]).set_defaults(func=cmd_selftest)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

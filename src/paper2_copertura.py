#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_copertura.py — il deficit sopravvive se si tolgono i voxel mal coperti?

DA DOVE NASCE LA DOMANDA
------------------------
La misura di P1-7 (src/paper2_pareggi.py, 10 settembre) ha mostrato che l'1.65%
dei voxel in maschera di DESI ha delta = -1 ESATTO — nessuna galassia — con
field_r mediano 0.079 contro 16.59 del resto del campo. Nei mock la stessa
frazione vale 0.21-0.27%.

delta = (n_d - alpha*n_r) / (alpha*n_r): con il denominatore prossimo a zero il
campo non e' ben definito. E i mock, ritagliati da un cubo pieno con
carve_cutsky, hanno molte meno di quelle regioni dei dati veri.

Quindi: **una parte del deficit vive nei voxel dove il campo e' instabile, e che
i mock non riproducono?** Se si', tocca il risultato centrale del Paper 1, non
una riga della Tabella 12.

PERCHE' IL LADDER DI EROSIONE NON RISPONDE
------------------------------------------
Il ladder esiste gia' e dice che il deficit NON collassa:

    NGC   k=0 20.26%   k=1 25.46%   k=2 20.63%   k=3 18.68%
    SGC   k=0 19.19%   k=1 27.19%   k=2 20.06%   k=3 17.31%

Ma l'erosione toglie il bordo GEOMETRICO — voxel a distanza crescente dal
contorno della maschera — mentre i voxel mal coperti comprendono buchi interni
e frange di field_r che stanno lontani dal contorno. Sono due tagli diversi, e
il secondo non e' mai stato fatto.

COSA FA
-------
Ricalcola N_H1 di DESI e dei mock su maschere ristrette per COPERTURA, a una
scala di percentili di field_r, e riporta il deficit a ogni taglio. Le
restrizioni vengono da S6.build_restrictions — la stessa funzione che step6 usa
per «field_r > P10» — e non sono riscritte.

LA RESTRIZIONE E' SULLA FILTRAZIONE, NON SULLE STATISTICHE
----------------------------------------------------------
step6 dichiara, in onepoint_stats: «nu viene costruito SEMPRE con la maschera
PIENA (lo smoothing usa tutta l'informazione disponibile) e solo DOPO si
restringe l'insieme dei voxel su cui si calcolano le statistiche».

Qui e' diverso, e va detto: nu si costruisce sulla maschera piena come li', ma
la sottomaschera va a compute_tda_features come DOMINIO DELLA FILTRAZIONE. Sono
due cose distinte: restringere la filtrazione elimina i loop che attraversano il
bordo del taglio, restringere le statistiche a valle no.

Per una conta di generatori la prima e' la scelta giusta — un loop che passa per
voxel esclusi non e' una struttura del sottoinsieme — ma non e' quello che step6
fa per i suoi momenti, e i due numeri non sono confrontabili fra loro.

CANCELLI
--------
  1. a footprint pieno N_H1 di DESI deve dare il valore congelato: 28256 / 15122,
     tolleranza ZERO;
  2. ogni restrizione deve togliere voxel, e in ordine monotono;
  3. per ogni taglio si riporta quanti dei voxel RIMOSSI hanno delta = -1: se il
     taglio non li prende, non sta misurando quello che dice.

USO
    python src\\paper2_copertura.py selftest
    python src\\paper2_copertura.py corri --region NGC --n-mock 30
    python src\\paper2_copertura.py corri --region SGC --n-mock 30 --versione v2

Uscita: 0 se i cancelli passano, 1 se no, 2 su errore d'uso.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

DESI_NH1 = {"NGC": 28256, "SGC": 15122}
N_VOXEL = {"NGC": 307805, "SGC": 172225}
MASCHERA = {"NGC": "bgs_ngc_mask_128.npy", "SGC": "bgs_sgc_mask_128.npy"}
SIGMA_PX_ATTESA = {"NGC": 0.32042249039652254, "SGC": 0.33605500065144590}
PERCENTILI = (1, 5, 10, 25, 50)
MIN_IDX_CUBI = 200
ROOT_DEFAULT = "."


def specs_restrizioni(percentili=PERCENTILI):
    """
    La sintassi che build_restrictions ACCETTA, non quella che restituisce.
    Letta da paper1_step6_onepoint_betti.py:221-235:
        none | full | 0      -> footprint pieno
        erosion<k>           -> erosione di k voxel
        fieldr<p>            -> field_r sopra il percentile p
    L'etichetta «field_r > P10» e' cio' che la funzione RITORNA. Il primo
    tentativo passava quella come specifica: sei avvisi e zero restrizioni.
    """
    return ["full"] + ["fieldr%d" % p for p in percentili]


def etichette_attese(percentili=PERCENTILI):
    """Le etichette che build_restrictions produce, per riscontrarle."""
    return ["footprint pieno"] + ["field_r > P%g" % p for p in percentili]


def deficit(n_mock, n_desi):
    return (n_mock - n_desi) / n_mock


def percorsi(root, region, versione):
    d = Path(root)
    return {"nu_congelata": d / "results" / "paper1" / ("n1_desi_nu_%s.npy" % region),
            "nu_nuova": d / "results" / "paper2" / ("n1_desi_nu_%s.npy" % region),
            "cubi": d / "results" / "phase8_test2_fields",
            "delta_v1": d / "data" / "processed" / "paper1_mock_deltas" / region,
            "delta_v2": d / "data" / "processed" / "paper2_mock_deltas_v2" / region,
            "maschera": d / "data" / "processed" / "phase6_fields" / MASCHERA[region],
            "out": d / "results" / "paper2" / ("copertura_%s_%s.json"
                                               % (versione, region))}


def sorgente(P, region, versione, n_mock):
    if versione == "v1" and region == "NGC" and P["cubi"].is_dir():
        f = [(int(p.stem.split("_")[1]), p)
             for p in sorted(P["cubi"].glob("test2_*.npz"))]
        f = [(i, p) for i, p in f if i >= MIN_IDX_CUBI]
        return f[:n_mock], "cubi congelati test2_*.npz"
    cache = P["delta_v1"] if versione == "v1" else P["delta_v2"]
    f = [(int(p.stem.split("_")[-1]), p) for p in sorted(cache.glob("delta_*.npy"))]
    return f[:n_mock], "nu da %s" % cache


def carica_nu(path, mask, P1, sigma_px):
    if path.suffix == ".npz":
        with np.load(path) as Z:
            return np.asarray(Z["delta"])
    return P1.build_nu(np.asarray(np.load(path), dtype=np.float64), mask, sigma_px)


def corri(root, region, versione, n_mock, out_path=None):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M              # noqa: E402
    import paper1_remap as P1                    # noqa: E402
    import paper1_step6_onepoint_betti as S6     # noqa: E402
    for f, mod in ((S6.build_restrictions, "paper1_step6_onepoint_betti"),
                   (P1.build_nu, "paper1_remap")):
        if f.__module__ != mod:
            raise SystemExit("RIFIUTO: %s viene da %s, atteso %s"
                             % (f.__name__, f.__module__, mod))

    P = percorsi(root, region, versione)
    print("=" * 78)
    print("IL DEFICIT SOTTO TAGLI IN COPERTURA  |  %s  |  %s" % (region, versione))
    print("=" * 78)

    G = P1.setup_region(M, region, root / "data" / "raw" / "desi_dr1",
                        root / "data" / "processed" / "phase6_fields")
    mask = np.load(P["maschera"]).astype(bool)
    if int(mask.sum()) != N_VOXEL[region] or not np.array_equal(mask, G["mask"]):
        raise SystemExit("RIFIUTO: maschera incoerente con la congelata (2.1-M)")
    sigma_px = float(M.SIGMA_PX)
    if abs(sigma_px - SIGMA_PX_ATTESA[region]) / SIGMA_PX_ATTESA[region] > 1e-9:
        raise SystemExit("RIFIUTO: sigma_px %.9f, atteso %.9f"
                         % (sigma_px, SIGMA_PX_ATTESA[region]))
    field_r = np.asarray(G["field_r"], float)
    alpha = G["sum_wd"] / G["sum_wr"]
    delta_d = np.asarray(P1.compute_delta(G["field_d"], field_r, alpha, mask,
                                          M.NGRID), dtype=np.float64)

    specs = specs_restrizioni()
    subs = S6.build_restrictions(mask, field_r, specs)
    if len(subs) != len(specs):
        raise SystemExit("RIFIUTO: %d restrizioni da %d specifiche: la sintassi "
                         "non e' quella attesa" % (len(subs), len(specs)))
    att = etichette_attese()
    got = [lab for lab, _ in subs]
    if got != att:
        raise SystemExit("RIFIUTO: etichette %s, attese %s: build_restrictions "
                         "non ha interpretato le specifiche come previsto"
                         % (got, att))

    # --- cancello 2: i tagli tolgono voxel, in ordine ----------------------
    conteggi = [int(np.asarray(sm).sum()) for _, sm in subs]
    if conteggi[0] != N_VOXEL[region]:
        raise SystemExit("RIFIUTO: il footprint pieno ha %d voxel, attesi %d"
                         % (conteggi[0], N_VOXEL[region]))
    if any(b >= a for a, b in zip(conteggi, conteggi[1:])):
        raise SystemExit("RIFIUTO: i tagli non sono monotoni: %s" % conteggi)

    # --- cancello 3: i tagli prendono davvero i voxel vuoti ----------------
    vuoti = (delta_d <= -1.0 + 1e-12) & mask
    n_vuoti = int(vuoti.sum())
    print("  voxel con delta = -1 in maschera: %d (%.3f%%)"
          % (n_vuoti, 100 * n_vuoti / conteggi[0]))
    print("\n  %-18s %9s %9s   %s" % ("taglio", "voxel", "rimossi", "dei rimossi, vuoti"))
    for (lab, sm), n in zip(subs, conteggi):
        sm = np.asarray(sm)
        rim = int(conteggi[0] - n)
        vr = int((vuoti & mask & ~sm).sum())
        print("  %-18s %9d %9d   %s" % (lab, n, rim,
              "%d (%.1f%% dei rimossi, %.1f%% dei vuoti)"
              % (vr, 100 * vr / rim, 100 * vr / n_vuoti) if rim else "-"))

    # --- DESI ---------------------------------------------------------------
    cache = (P["nu_congelata"] if P["nu_congelata"].is_file() else P["nu_nuova"])
    nu_d = np.load(cache)
    print("\n  DESI da %s" % cache)
    n_desi = {}
    for lab, sm in subs:
        v = int(round(float(M.compute_tda_features(nu_d, np.asarray(sm),
                                                   M.N_THRESH, masked=True)[4])))
        n_desi[lab] = v
        print("    %-18s N_H1 %7d" % (lab, v))
    if n_desi[subs[0][0]] != DESI_NH1[region]:
        raise SystemExit("RIFIUTO: a footprint pieno N_H1 = %d, congelato %d"
                         % (n_desi[subs[0][0]], DESI_NH1[region]))
    print("    cancello 1: il footprint pieno riproduce %d, esatto" % DESI_NH1[region])
    del nu_d

    # --- mock ---------------------------------------------------------------
    files, descr = sorgente(P, region, versione, n_mock)
    if not files:
        raise SystemExit("RIFIUTO: nessun campo mock (%s)" % descr)
    print("\n  %d mock — %s" % (len(files), descr))
    acc = {lab: [] for lab, _ in subs}
    t0 = time.time()
    for j, (i, p) in enumerate(files, 1):
        nu = carica_nu(p, mask, P1, sigma_px)
        for lab, sm in subs:
            acc[lab].append(float(M.compute_tda_features(nu, np.asarray(sm),
                                                         M.N_THRESH, masked=True)[4]))
        del nu
        if j % 5 == 0:
            el = time.time() - t0
            print("    %d/%d  %.1f s/mock  ETA %.1f min"
                  % (j, len(files), el / j, el / j * (len(files) - j) / 60))

    # --- il deficit a ogni taglio, con il RANGO ----------------------------
    # Il Paper 1 §7.1 dichiara «the empirical rank at 1/2001 in every variant».
    # Trenta mock non bastano a dire 1/2001, ma bastano a vedere se DESI resta
    # sotto TUTTI: un solo mock che scenda sotto N_DESI a un taglio smentirebbe
    # l'affermazione, e con trenta campioni si vedrebbe. Il rango si riporta
    # come 1/(n_sotto+1) su n+1, dichiarando la dimensione del campione.
    print("\n" + "=" * 78)
    print("  %-18s %9s %10s %8s %9s %8s %10s %9s"
          % ("taglio", "voxel", "<N>_mock", "N_DESI", "D", "SEM(D)",
             "rango", "min mock"))
    righe = []
    for (lab, sm), n in zip(subs, conteggi):
        a = np.array(acc[lab], float)
        D = deficit(a.mean(), n_desi[lab])
        semD = float(a.std(ddof=1) / np.sqrt(a.size) * n_desi[lab] / a.mean() ** 2)
        sotto = int((a <= n_desi[lab]).sum())
        rango = "%d/%d" % (sotto + 1, a.size + 1)
        margine = float(a.min() - n_desi[lab])
        z = float((n_desi[lab] - a.mean()) / a.std(ddof=1)) if a.size > 1 else None
        righe.append({"taglio": lab, "n_voxel": n, "mock_media": float(a.mean()),
                      "mock_sd": float(a.std(ddof=1)), "n_desi": n_desi[lab],
                      "deficit": D, "sem_deficit": semD,
                      "n_mock_sotto_desi": sotto, "rango": rango,
                      "mock_minimo": float(a.min()),
                      "margine_sul_minimo": margine, "z": z})
        print("  %-18s %9d %10.1f %8d %8.2f%% %7.2f%% %10s %9.0f"
              % (lab, n, a.mean(), n_desi[lab], 100 * D, 100 * semD,
                 rango, a.min()))

    # --- il rango: DESI resta sotto tutti? ---------------------------------
    rotti = [r for r in righe if r["n_mock_sotto_desi"] > 0]
    print("\n  rango empirico su %d mock: DESI sotto TUTTI in %d tagli su %d"
          % (len(files), len(righe) - len(rotti), len(righe)))
    if rotti:
        print("  *** in %d tagli almeno un mock scende sotto DESI: ***"
              % len(rotti))
        for r in rotti:
            print("      %-18s %d mock sotto, minimo %.0f contro N_DESI %d"
                  % (r["taglio"], r["n_mock_sotto_desi"], r["mock_minimo"],
                     r["n_desi"]))
        print("  L'affermazione «rank 1/2001 in every variant» del §7.1 non vale")
        print("  a questi tagli, e va verificata sull'ensemble completo.")
    else:
        peggio = min(righe, key=lambda r: r["margine_sul_minimo"])
        print("  margine piu' stretto: %s, il mock piu' basso sta %.0f generatori"
              % (peggio["taglio"], peggio["margine_sul_minimo"]))
        print("  sopra DESI (%.1f sd). Con %d mock non si dimostra 1/2001, ma"
              % (peggio["z"] and -peggio["z"] or 0, len(files)))
        print("  nessun campione lo contraddice.")

    D0, Dl = righe[0]["deficit"], righe[-1]["deficit"]
    se = float(np.sqrt(righe[0]["sem_deficit"] ** 2 + righe[-1]["sem_deficit"] ** 2))
    print("\n  D dal footprint pieno all'ultimo taglio: %.2f%% -> %.2f%%  "
          "(%+.2f%% +/- %.2f%%)" % (100 * D0, 100 * Dl, 100 * (Dl - D0), 100 * se))
    if Dl > 0.5 * D0:
        print("  Il deficit SOPRAVVIVE ai tagli in copertura: i voxel mal coperti")
        print("  non lo producono. Il risultato del Paper 1 non dipende da loro.")
    else:
        print("  Il deficit si DIMEZZA o piu' togliendo i voxel mal coperti: una")
        print("  parte sostanziale vive dove il campo non e' ben definito, e va")
        print("  detto nel Paper 1 prima che lo dica un referee.")

    rec = {"schema": "paper2_copertura_v1", "region": region, "versione": versione,
           "utc": datetime.now(timezone.utc).isoformat(), "sorgente": descr,
           "n_mock": len(files), "percentili": list(PERCENTILI),
           "n_voxel_vuoti": n_vuoti, "righe": righe,
           "deficit_massimo": max(r["deficit"] for r in righe),
           "taglio_del_massimo": max(righe, key=lambda r: r["deficit"])["taglio"],
           "tagli_con_mock_sotto_desi": [r["taglio"] for r in righe
                                         if r["n_mock_sotto_desi"] > 0],
           "deficit_pieno": D0, "deficit_ultimo": Dl,
           "variazione": Dl - D0, "sem_variazione": se}
    dest = Path(out_path) if out_path else P["out"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rec, indent=2, ensure_ascii=True), encoding="utf-8")
    print("\n  scritto: %s" % dest)
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

    print("selftest paper2_copertura")

    chk("i valori congelati di DESI", DESI_NH1 == {"NGC": 28256, "SGC": 15122})
    chk("sigma_px per emisfero, diverse",
        SIGMA_PX_ATTESA["NGC"] != SIGMA_PX_ATTESA["SGC"])
    s = specs_restrizioni()
    chk("la specifica del footprint pieno e' quella che step6 ACCETTA",
        s[0] == "full" and s[0] in ("none", "full", "0"), s[0])
    chk("le altre sono fieldr<p>, senza spazi ne' P",
        s[1:] == ["fieldr1", "fieldr5", "fieldr10", "fieldr25", "fieldr50"], s)
    chk("nessuna specifica contiene lo spazio o il '>' dell'ETICHETTA",
        not any(" " in x or ">" in x for x in s[1:]))
    e = etichette_attese()
    chk("le etichette attese sono quelle che la funzione ritorna",
        e == ["footprint pieno", "field_r > P1", "field_r > P5",
              "field_r > P10", "field_r > P25", "field_r > P50"], e)
    chk("specifica ed etichetta sono cose diverse, e non si scambiano",
        s != e and len(s) == len(e))
    chk("P10 c'e', ed e' la restrizione che step6 usa gia'",
        "fieldr10" in s and "field_r > P10" in e)

    # il deficit: la stessa formula di paper2_prominenza_v1
    chk("D = 1 - N_DESI/N_mock", abs(deficit(100.0, 80.0) - 0.2) < 1e-12)
    chk("D = 0 se coincidono", deficit(50.0, 50.0) == 0.0)
    # i valori veri del ladder, riprodotti
    for k, (m, d, atteso) in enumerate(((35434.5, 28256, 0.2026),
                                        (31914.3, 23790, 0.2546),
                                        (25281.5, 20066, 0.2063),
                                        (17647.8, 14352, 0.1868))):
        chk("D a k=%d riproduce il %.2f%% del ladder" % (k, 100 * atteso),
            abs(deficit(m, d) - atteso) < 5e-5, deficit(m, d))

    # monotonia dei tagli
    c = [307805, 304000, 292000, 277000, 231000, 154000]
    chk("tagli monotoni: nessuno cresce", not any(b >= a for a, b in zip(c, c[1:])))
    c2 = [307805, 304000, 304000]
    chk("due tagli uguali sono rifiutati",
        any(b >= a for a, b in zip(c2, c2[1:])))

    # il criterio del verdetto
    # il rango: la forma, e il caso che smentirebbe il §7.1
    a = np.array([35000., 35200., 35400.], float)
    chk("con DESI sotto tutti il rango e' 1 su n+1",
        "%d/%d" % (int((a <= 28256).sum()) + 1, a.size + 1) == "1/4")
    chk("un mock sotto DESI si conta", int((a <= 35100).sum()) == 1)
    chk("e allora il rango non e' piu' 1",
        "%d/%d" % (int((a <= 35100).sum()) + 1, a.size + 1) == "2/4")
    chk("il margine sul minimo e' quello che avvisa per primo",
        abs(float(a.min() - 28256) - 6744.0) < 1e-9)
    chk("il massimo di D si riporta, e puo' NON essere l'ultimo taglio",
        max([0.2033, 0.2864, 0.2292]) == 0.2864)
    chk("il 31.22%% di SGC a P25 sta SOPRA il 29%% dichiarato dal Paper 1 §7.1",
        0.3122 > 0.29)

    chk("se D resta sopra meta' il deficit sopravvive", 0.18 > 0.5 * 0.2026)
    chk("se scende sotto meta' no", not (0.09 > 0.5 * 0.2026))

    P = percorsi("/b", "SGC", "v2")
    chk("l'uscita sta in results/paper2 e distingue la versione",
        P["out"].parent.name == "paper2"
        and P["out"].name == "copertura_v2_SGC.json")
    chk("la cache nu si cerca prima fra le congelate",
        P["nu_congelata"].parent.name == "paper1")

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("corri")
    c.add_argument("--root", default=ROOT_DEFAULT)
    c.add_argument("--region", choices=["NGC", "SGC"], required=True)
    c.add_argument("--versione", choices=["v1", "v2"], default="v1")
    c.add_argument("--n-mock", dest="n_mock", type=int, default=30)
    c.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "corri":
        return corri(a.root, a.region, a.versione, a.n_mock, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

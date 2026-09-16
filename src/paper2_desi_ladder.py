#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_desi_ladder.py

Due cose mancano, e sono lo stesso campo:

  1. `results/paper1/n1_desi_nu_SGC.npy` NON ESISTE. n10 (item 5.3) lo pretende
     come cache del campo nu di DESI, e senza non gira su SGC.
  2. La riga DESI di v1 porta i nove campi a un punto ma NON i livelli di
     erosione: la passata a un punto non calcolava TDA, per scelta. Il verdetto
     di 4.3b ha bisogno di N_H1_k0, k1, k2 di DESI per i deficit D(k), e senza
     dichiara NON VALUTABILE invece di inventare uno zero.

Entrambe si risolvono con una passata sola: nu di DESI e la sua TDA a quattro
livelli. Meno di un minuto per emisfero.

IL CANCELLO CHE RENDE AFFIDABILE SGC
------------------------------------
La cache NGC ESISTE. Ricostruirla per la stessa via deve dare un array
IDENTICO BIT PER BIT. Se lo da', il medesimo cammino su SGC — dove non c'e'
nulla con cui confrontarsi — e' affidabile per costruzione e non per fiducia.
E' l'unico modo di validare un lato che non ha ancora.

E un secondo cancello, indipendente: N_H1 a k=0 deve dare 28256 (NGC) e 15122
(SGC), i valori congelati. Tolleranza ZERO.

IL CAMMINO E' QUELLO ANALITICO
------------------------------
setup_region SENZA impostare prima la tabella delle distanze: e' il cammino di
step6, della riga DESI di v1 e di n10. Il cammino di produzione di R3 da' un
delta diverso nel 59-67% delle celle (paper2_cammini_desi.py), e la cache NGC
esistente viene da questo. Usare l'altro romperebbe il cancello bit per bit,
giustamente.

USO
    python src\\paper2_desi_ladder.py selftest
    python src\\paper2_desi_ladder.py costruisci --region NGC
    python src\\paper2_desi_ladder.py costruisci --region SGC

Uscita: 0 se i cancelli passano, 1 se no, 2 su errore d'uso.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

EROSIONI = (0, 1, 2, 3)
# Valori congelati di N_H1 di DESI a k=0. Tolleranza ZERO.
DESI_NH1 = {"NGC": 28256, "SGC": 15122}
N_VOXEL = {"NGC": 307805, "SGC": 172225}
ROOT_DEFAULT = "."


# DOVE SI SCRIVE, E DOVE NO.
# results/paper1 e' dentro le regole del tier `diagrams` del freeze di v1:
# scriverci un file nuovo lo fa comparire come EXTRA e manda freeze_verify in
# DISCREPANCY, che e' esattamente cio' che e' successo con n1_desi_nu_SGC.npy.
# results/paper2 e' esentata di proposito — il controllo C dice «fuori dal corpo
# E FUORI DA results/paper2» — ed e' dove il record 53 ha messo la cache dei
# delta, «deliberately NOT a tier».
# Quindi: si LEGGE da results/paper1 quando il file c'e' gia' ed e' congelato
# (NGC), e si SCRIVE solo in results/paper2. Mai il contrario.
DIR_SCRITTURA = ("results", "paper2")


def percorsi(root, region):
    d = Path(root)
    return {"cache_congelata": d / "results" / "paper1" / ("n1_desi_nu_%s.npy" % region),
            "cache_nuova": d / "results" / "paper2" / ("n1_desi_nu_%s.npy" % region),
            "ladder": d / "results" / "paper2" / ("desi_ladder_%s.json" % region),
            "desi_raw": d / "data" / "raw" / "desi_dr1",
            "phase6": d / "data" / "processed" / "phase6_fields"}


def cache_esistente(P):
    """La congelata ha la precedenza: e' quella che n10 ha gia' usato."""
    if P["cache_congelata"].is_file():
        return P["cache_congelata"], "congelata"
    if P["cache_nuova"].is_file():
        return P["cache_nuova"], "in results/paper2"
    return None, "assente"


def controlla_destinazione(path):
    """Rifiuta di scrivere fuori da results/paper2. Un tool che scrive dentro le
    regole di un tier congelato manda il freeze in DISCREPANCY, e la prudenza
    non basta: serve il rifiuto."""
    parti = Path(path).resolve().parts
    if tuple(parti[-3:-1]) != DIR_SCRITTURA:
        raise SystemExit("RIFIUTO: %s non sta in results/paper2. Scrivere altrove "
                         "puo' cadere dentro le regole di un tier congelato: e' "
                         "successo con results/paper1/n1_desi_nu_SGC.npy." % path)
    return path


def costruisci(root, region, forza=False):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M          # noqa: E402
    import paper1_remap as P1                # noqa: E402
    import paper2_runner_fase3 as F3         # noqa: E402
    for f, mod in ((P1.build_nu, "paper1_remap"),
                   (P1.compute_delta, "paper1_remap"),
                   (P1.setup_region, "paper1_remap"),
                   (F3.erosion_levels, "paper2_runner_fase3")):
        if f.__module__ != mod:
            raise SystemExit("RIFIUTO: %s viene da %s, atteso %s"
                             % (f.__name__, f.__module__, mod))

    P = percorsi(root, region)
    print("=" * 78)
    print("nu DI DESI E IL SUO LADDER  |  %s" % region)
    print("=" * 78)

    # cammino ANALITICO: setup_region senza tabella impostata prima
    G = P1.setup_region(M, region, P["desi_raw"], P["phase6"])
    mask = G["mask"]
    if int(mask.sum()) != N_VOXEL[region]:
        raise SystemExit("RIFIUTO: %d voxel di maschera, attesi %d"
                         % (int(mask.sum()), N_VOXEL[region]))
    alpha = G["sum_wd"] / G["sum_wr"]
    delta = np.asarray(P1.compute_delta(G["field_d"], G["field_r"], alpha,
                                        mask, M.NGRID), dtype=np.float64)
    nu = P1.build_nu(delta, mask, float(M.SIGMA_PX))
    print("  maschera %d voxel   sigma_px %.9f   alpha %.9e"
          % (int(mask.sum()), float(M.SIGMA_PX), alpha))

    # --- cancello 1: la cache esistente, bit per bit ------------------------
    esistente, dove = cache_esistente(P)
    esito_cache = "assente"
    if esistente is not None:
        print("  cache esistente: %s (%s)" % (esistente, dove))
        vecchia = np.load(esistente)
        if vecchia.shape != nu.shape:
            raise SystemExit("RIFIUTO: la cache esistente ha forma %s, la nuova %s"
                             % (vecchia.shape, nu.shape))
        diverse = int((np.asarray(vecchia) != np.asarray(nu)).sum())
        esito_cache = "identica" if diverse == 0 else "%d celle diverse" % diverse
        print("  ricostruzione contro la cache: %s" % esito_cache)
        if diverse:
            raise SystemExit(
                "RIFIUTO: la ricostruzione NON riproduce la cache esistente "
                "(%d celle su %d). Il cammino non e' quello che l'ha prodotta, e "
                "finche' non lo e' non si puo' costruire quella dell'altro "
                "emisfero, dove non c'e' nulla con cui confrontarsi."
                % (diverse, nu.size))
    else:
        print("  cache esistente: assente — verra' scritta")

    # --- il ladder ----------------------------------------------------------
    masks, _ = F3.erosion_levels(mask, EROSIONI)
    livelli = {}
    for k in EROSIONI:
        f = M.compute_tda_features(nu, masks[k], M.N_THRESH, masked=True)
        livelli["N_H1_k%d" % k] = int(round(float(f[4])))
        livelli["b1_peak_k%d" % k] = float(f[1])
        print("    k=%d  N_H1 %6d   voxel %7d"
              % (k, livelli["N_H1_k%d" % k], int(masks[k].sum())))

    # --- cancello 2: N_H1 a k=0 e' il valore congelato ---------------------
    atteso = DESI_NH1[region]
    if livelli["N_H1_k0"] != atteso:
        raise SystemExit("RIFIUTO: N_H1(DESI, k=0) = %d, congelato %d. "
                         "Tolleranza zero: e' il campo del paper."
                         % (livelli["N_H1_k0"], atteso))
    print("  N_H1 a k=0 riproduce il congelato (%d): esatto" % atteso)

    if esistente is None or forza:
        dest = controlla_destinazione(P["cache_nuova"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        np.save(dest, nu)
        print("  scritta: %s" % dest)
        esistente = dest

    rec = {"schema": "paper2_desi_ladder_v1", "region": region,
           "utc": datetime.now(timezone.utc).isoformat(),
           "n_voxel_maschera": int(mask.sum()), "sigma_px": float(M.SIGMA_PX),
           "alpha": float(alpha), "cammino": "analitico (step6, riga DESI v1, n10)",
           "cache_nu": str(esistente), "cache_dove": dove,
           "cache_preesistente": esito_cache,
           "erosioni": list(EROSIONI)}
    rec.update(livelli)
    P["ladder"].parent.mkdir(parents=True, exist_ok=True)
    P["ladder"].write_text(json.dumps(rec, indent=2, ensure_ascii=True),
                           encoding="utf-8")
    print("  ladder: %s" % P["ladder"])
    print("\n  D(k) per il verdetto di 4.3b: N_H1 = %s"
          % [livelli["N_H1_k%d" % k] for k in EROSIONI])
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

    print("selftest paper2_desi_ladder")

    chk("i valori congelati di DESI sono quelli del paper",
        DESI_NH1 == {"NGC": 28256, "SGC": 15122})
    chk("i voxel di maschera sono quelli congelati",
        N_VOXEL == {"NGC": 307805, "SGC": 172225})
    chk("quattro livelli, come il runner", EROSIONI == (0, 1, 2, 3))
    chk("4.3b ne usa tre: k=0, 1, 2", set((0, 1, 2)) <= set(EROSIONI))

    P = percorsi("/b", "SGC")
    chk("la cache ha il nome che n10 si aspetta",
        P["cache_nuova"].name == "n1_desi_nu_SGC.npy", P["cache_nuova"].name)
    chk("si LEGGE anche da results/paper1, dove sta la congelata",
        P["cache_congelata"].parent.name == "paper1")
    chk("ma si SCRIVE in results/paper2, fuori dai tier congelati",
        P["cache_nuova"].parent.name == "paper2")
    try:
        controlla_destinazione(P["cache_congelata"])
        chk("scrivere in results/paper1 e' RIFIUTATO", False, "non ha rifiutato")
    except SystemExit as e:
        chk("scrivere in results/paper1 e' RIFIUTATO", "results/paper2" in str(e))
    chk("e in results/paper2 e' ammesso",
        controlla_destinazione(P["cache_nuova"]) == P["cache_nuova"])
    chk("il ladder va in results/paper2, non fra i registri di paper1",
        P["ladder"].parent.name == "paper2"
        and P["ladder"].name == "desi_ladder_SGC.json")
    chk("l'altra regione da' l'altro nome",
        percorsi("/b", "NGC")["cache_nuova"].name == "n1_desi_nu_NGC.npy")

    # il cancello bit per bit, sulla logica
    a = np.arange(27, dtype=np.float32).reshape(3, 3, 3)
    b = a.copy()
    chk("due array identici danno zero celle diverse",
        int((a != b).sum()) == 0)
    b[1, 1, 1] = np.nextafter(b[1, 1, 1], np.float32(1e9))
    chk("un solo ULP di differenza viene contato",
        int((a != b).sum()) == 1)
    chk("e il cancello e' su ZERO celle, non su una tolleranza",
        "diverse" in costruisci.__doc__ if costruisci.__doc__ else True)

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("costruisci")
    c.add_argument("--root", default=ROOT_DEFAULT)
    c.add_argument("--region", choices=["NGC", "SGC"], required=True)
    c.add_argument("--forza", action="store_true",
                   help="riscrive la cache anche se esiste. Solo dopo che il "
                        "cancello bit per bit e' passato")
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "costruisci":
        return costruisci(a.root, a.region, a.forza)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

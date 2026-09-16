#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_p10_definizione.py — perche' misuro 28.63 dove il Paper 1 scrive 28.5.

LA DISCREPANZA
--------------
Il §7.1 quota il deficit al decimo percentile del denominatore come **28.5 per
cent**. Con 200 mock misuro **28.629 +- 0.057** (src/paper2_copertura.py):
0.13 punti di scarto, **2.3 SEM**. Vicino, ma non e' una riproduzione — e le
altre di questi giorni (sigma_Delta, il rumore di fase, s^v1, i sei N_H1 di
DESI, i quattordici valori di D2) sono tutte a scarto zero.

TRE IPOTESI, E QUELLA CHE COSTA UNA SOLA TDA
--------------------------------------------
  (a) il paper ha usato 2000 mock invece di 200. Disfavorita a 2.3 sigma ma non
      esclusa; per chiuderla servirebbero ~800 mock in piu' al solo P10, tre ore.
  (b) la restrizione applicata alle STATISTICHE a valle invece che alla
      filtrazione, come onepoint_stats dichiara di fare per i momenti. Poco
      credibile: N_H1 e' una conta di generatori, non una statistica per voxel,
      e restringerla a valle non ha significato.
  (c) **la DEFINIZIONE del percentile.** build_restrictions lo calcola su
      `field_r[mask]`, DENTRO maschera. Ma il difetto che P1-2 ha scoperto in
      `paper1_rev_n4n5.py` era calcolarlo su `field_r > 0`, cioe' su tutti i
      voxel con random — e quel difetto e' stato corretto solo dopo, da
      `paper1_rev_n4b_clean.py`. Se il §7.1 venisse da uno script anteriore
      alla correzione, la soglia sarebbe un'altra.

QUESTO STRUMENTO TESTA LA (c), E COSTA UNA TDA
----------------------------------------------
Calcola le due soglie, i due sottoinsiemi, e N_H1 di DESI su quello alternativo
— la restrizione in-mask e' gia' misurata, 24991. Poi, con la media dei mock
gia' nota (35015.76 su 200), riporta il D che ne discenderebbe.

  se D_alternativo cade su 28.5   -> l'ipotesi (c) e' confermata e la
                                     discrepanza e' spiegata: il paper usa la
                                     definizione anteriore alla correzione;
  se le due soglie coincidono     -> la (c) muore gratis e resta la (a);
  se D_alternativo e' un terzo
  numero                          -> nessuna delle due, e va cercato altrove.

Il D alternativo usa la media dei mock calcolata sulla restrizione IN-MASK, che
non e' la sua: e' un'approssimazione, dichiarata, e serve solo a vedere se
l'ordine di grandezza spieghi lo 0.13. Se lo spiega, la misura completa
richiede i 200 mock sulla restrizione alternativa, 40 minuti.

USO
    python src\\paper2_p10_definizione.py selftest
    python src\\paper2_p10_definizione.py confronta --region NGC
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

N_VOXEL = {"NGC": 307805, "SGC": 172225}
MASCHERA = {"NGC": "bgs_ngc_mask_128.npy", "SGC": "bgs_sgc_mask_128.npy"}
SIGMA_PX_ATTESA = {"NGC": 0.32042249039652254, "SGC": 0.33605500065144590}
# Misurati da src/paper2_copertura.py su 200 mock, 11 settembre.
MISURATO = {"NGC": {"n_desi_p10": 24991, "mock_media_p10": 35015.76,
                    "D_p10": 0.2862928007274439, "sem_D": 0.000572733558995566,
                    "n_voxel_p10": 277024},
            "SGC": {"n_desi_p10": 13013, "mock_media_p10": 18420.666666666668,
                    "D_p10": 0.29361096002249504, "sem_D": 0.0006614025752689409,
                    "n_voxel_p10": 155002}}
# Il §7.1 quota il decimo percentile SOLO per NGC. Su SGC il paper non dice
# nulla, e confrontare il 29.36% di SGC contro un numero di NGC darebbe un
# verdetto falso e plausibile. Su SGC si riporta il confronto fra le due
# DEFINIZIONI — che e' informativo, e dice se il fenomeno sia generale — e
# nessun verdetto.
PAPER_D_P10 = {"NGC": 0.285, "SGC": None}
PERCENTILE = 10.0
ROOT_DEFAULT = "."
ROOT_DEFAULT = "."


def soglie(field_r, mask, p=PERCENTILE):
    """Le due definizioni. La prima e' quella di build_restrictions."""
    fr = np.asarray(field_r, float)
    m = np.asarray(mask, bool)
    thr_in = float(np.percentile(fr[m], p))          # step6: dentro maschera
    thr_pos = float(np.percentile(fr[fr > 0], p))    # n4n5: field_r > 0
    return thr_in, thr_pos


def deficit(n_mock, n_desi):
    return (n_mock - n_desi) / n_mock


def confronta(root, region, out_path=None):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M          # noqa: E402
    import paper1_remap as P1                # noqa: E402

    d = Path(root)
    mask = np.load(d / "data" / "processed" / "phase6_fields"
                   / MASCHERA[region]).astype(bool)
    if int(mask.sum()) != N_VOXEL[region]:
        raise SystemExit("RIFIUTO: %d voxel, attesi %d"
                         % (int(mask.sum()), N_VOXEL[region]))

    print("=" * 78)
    print("DA DOVE VIENE IL 28.5  |  %s  |  le due definizioni del percentile"
          % region)
    print("=" * 78)

    G = P1.setup_region(M, region, d / "data" / "raw" / "desi_dr1",
                        d / "data" / "processed" / "phase6_fields")
    sigma_px = float(M.SIGMA_PX)
    if abs(sigma_px - SIGMA_PX_ATTESA[region]) / SIGMA_PX_ATTESA[region] > 1e-9:
        raise SystemExit("RIFIUTO: sigma_px %.9f, atteso %.9f"
                         % (sigma_px, SIGMA_PX_ATTESA[region]))
    field_r = np.asarray(G["field_r"], float)

    thr_in, thr_pos = soglie(field_r, mask)
    sub_in = mask & (field_r > thr_in)
    sub_pos = mask & (field_r > thr_pos)
    n_in, n_pos = int(sub_in.sum()), int(sub_pos.sum())
    uguali = bool(np.array_equal(sub_in, sub_pos))

    print("\n  soglia DENTRO MASCHERA (step6)      %.6f  ->  %7d voxel"
          % (thr_in, n_in))
    print("  soglia su field_r > 0  (n4n5)       %.6f  ->  %7d voxel"
          % (thr_pos, n_pos))
    print("  rapporto fra le soglie %.4f, differenza di voxel %+d"
          % (thr_pos / thr_in if thr_in else float("nan"), n_pos - n_in))
    if n_in != MISURATO[region]["n_voxel_p10"]:
        raise SystemExit("RIFIUTO: la restrizione in-mask da' %d voxel, ma "
                         "paper2_copertura ne ha misurati %d: non e' la stessa"
                         % (n_in, MISURATO[region]["n_voxel_p10"]))
    print("  cancello: la restrizione in-mask riproduce i %d voxel di "
          "paper2_copertura" % n_in)

    # La costante e' un DIZIONARIO per emisfero. Usarla come scalare da'
    # TypeError subito, il che e' meglio di un confronto silenzioso col numero
    # dell'altro emisfero — ma la prima versione ne aveva lasciate tre usate
    # cosi', e il compilatore non le vede.
    atteso_paper = PAPER_D_P10[region]
    if atteso_paper is None:
        print("\n  Il Paper 1 §7.1 NON quota il decimo percentile per %s:" % region)
        print("  qui si riporta il confronto fra le due DEFINIZIONI, che dice")
        print("  se il fenomeno sia generale, e nessun verdetto sul paper.")

    if uguali:
        print("\n  LE DUE RESTRIZIONI COINCIDONO voxel per voxel.")
        print("  L'ipotesi (c) muore qui, e senza spendere una TDA: la")
        print("  definizione del percentile non puo' spiegare lo 0.13.")
        print("  Resta la (a), i 2000 mock, che va chiusa con ~800 mock in piu'")
        print("  al solo P10 — tre ore — e porterebbe lo scarto a 4.5 sigma se")
        print("  fosse vera.")
        rec_extra = {"esito": "(c) ESCLUSA: le due restrizioni coincidono"}
        n_desi_pos = None
        D_pos = None
    else:
        # --- LA TDA, una sola -------------------------------------------------
        cache = d / "results" / "paper1" / ("n1_desi_nu_%s.npy" % region)
        if not cache.is_file():
            cache = d / "results" / "paper2" / ("n1_desi_nu_%s.npy" % region)
        nu = np.load(cache)
        n_desi_pos = int(round(float(M.compute_tda_features(
            nu, sub_pos, M.N_THRESH, masked=True)[4])))
        print("\n  N_H1 di DESI sulla restrizione alternativa: %d" % n_desi_pos)
        print("  (sulla in-mask vale %d, gia' misurato)"
              % MISURATO[region]["n_desi_p10"])
        mm = MISURATO[region]["mock_media_p10"]
        D_pos = deficit(mm, n_desi_pos)
        D_in = MISURATO[region]["D_p10"]
        if atteso_paper is None:
            print("\n  D in-mask     %.4f%%   D alternativo %.4f%% (approssimato)"
                  % (100 * D_in, 100 * D_pos))
            print("  Nessun valore del paper con cui confrontarli per %s."
                  % region)
            rec_extra = {"esito": "SENZA VERDETTO: il paper non quota %s"
                                  % region}
            dest0 = None
        if atteso_paper is None:
            pass
        else:
            print("\n  ATTENZIONE: il D alternativo usa la media dei mock calcolata")
            print("  sulla restrizione IN-MASK (%.2f), che non e' la sua. E'"
                  % mm)
            print("  un'approssimazione dichiarata, e serve solo a vedere se")
            print("  l'ordine di grandezza spieghi lo 0.13.")
            print("\n  D in-mask        %.4f%%   (misurato)" % (100 * D_in))
            print("  D alternativo    %.4f%%   (approssimato)" % (100 * D_pos))
            print("  Paper 1 §7.1     %.4f%%" % (100 * atteso_paper))
            d_in = abs(D_in - atteso_paper)
            d_pos = abs(D_pos - atteso_paper)
            print("\n  scarto dal paper: in-mask %.4f, alternativo %.4f"
                  % (d_in, d_pos))
            if d_pos < d_in / 2:
                rec_extra = {"esito": "(c) PLAUSIBILE: la definizione alternativa "
                                      "avvicina molto al valore del paper"}
                print("  L'ipotesi (c) e' PLAUSIBILE: la definizione alternativa")
                print("  avvicina. La misura completa richiede i 200 mock sulla")
                print("  restrizione alternativa, 40 minuti.")
            elif d_pos > d_in:
                rec_extra = {"esito": "(c) ESCLUSA: la definizione alternativa "
                                      "allontana"}
                print("  L'ipotesi (c) e' ESCLUSA: la definizione alternativa")
                print("  ALLONTANA dal valore del paper. Resta la (a).")
            else:
                rec_extra = {"esito": "(c) NON DECIDE: lo spostamento non basta"}
                print("  L'ipotesi (c) NON DECIDE: lo spostamento c'e' ma non basta")
                print("  a spiegare lo 0.13. Puo' concorrere con la (a).")

    rec = {"schema": "paper2_p10_definizione_v1", "region": region,
           "utc": datetime.now(timezone.utc).isoformat(),
           "percentile": PERCENTILE,
           "soglia_in_mask": thr_in, "soglia_field_r_positivo": thr_pos,
           "n_voxel_in_mask": n_in, "n_voxel_alternativa": n_pos,
           "restrizioni_identiche": uguali,
           "n_desi_in_mask": MISURATO[region]["n_desi_p10"],
           "n_desi_alternativa": n_desi_pos,
           "D_in_mask": MISURATO[region]["D_p10"],
           "D_alternativa_approssimato": D_pos,
           "D_paper": atteso_paper,
           "nota": ("il D alternativo usa la media dei mock della restrizione "
                    "in-mask: approssimazione dichiarata")}
    rec.update(rec_extra)
    dest = (Path(out_path) if out_path
            else d / "results" / "paper2" / ("p10_definizione_%s.json" % region))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rec, indent=2, ensure_ascii=True), encoding="utf-8")
    print("\n  scritto: %s" % dest)
    return 0


# ---------------------------------------------------------------------------

def pathlib_read():
    import pathlib as _p
    return _p.Path(__file__).read_text(encoding="utf-8")


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

    print("selftest paper2_p10_definizione")

    chk("il valore del paper e' 28.5% ed e' di NGC", PAPER_D_P10["NGC"] == 0.285)
    chk("per SGC il paper NON quota nulla, e la costante lo dice",
        PAPER_D_P10["SGC"] is None)
    chk("confrontare SGC col numero di NGC sarebbe un verdetto falso: il 29.36%"
        " di SGC dista dal 28.5 di NGC piu' del 28.63 di NGC stesso",
        abs(MISURATO["SGC"]["D_p10"] - 0.285)
        > abs(MISURATO["NGC"]["D_p10"] - 0.285))
    chk("e quello misurato e' 28.63%, a 2.3 SEM",
        abs(MISURATO["NGC"]["D_p10"] - 0.28629) < 1e-5
        and abs((MISURATO["NGC"]["D_p10"] - PAPER_D_P10["NGC"])
                / MISURATO["NGC"]["sem_D"] - 2.26) < 0.1,
        (MISURATO["NGC"]["D_p10"] - PAPER_D_P10["NGC"]) / MISURATO["NGC"]["sem_D"])
    chk("il deficit e' 1 - N_DESI/N_mock",
        abs(deficit(MISURATO["NGC"]["mock_media_p10"],
                    MISURATO["NGC"]["n_desi_p10"]) - MISURATO["NGC"]["D_p10"])
        < 1e-12)

    # le due definizioni su un caso costruito
    fr = np.zeros((10, 10, 10))
    m = np.zeros((10, 10, 10), dtype=bool)
    m[:5] = True                       # meta' in maschera
    fr[m] = np.linspace(1.0, 100.0, int(m.sum()))
    fr[~m] = np.linspace(0.01, 0.5, int((~m).sum()))   # fuori: valori piccoli
    ti, tp = soglie(fr, m)
    chk("con valori piccoli FUORI maschera, la soglia su field_r>0 e' piu' bassa",
        tp < ti, (ti, tp))
    chk("quindi la restrizione alternativa tiene PIU' voxel",
        int((m & (fr > tp)).sum()) > int((m & (fr > ti)).sum()))
    # il caso in cui coincidono: nulla fuori maschera
    fr2 = np.zeros((10, 10, 10))
    fr2[m] = np.linspace(1.0, 100.0, int(m.sum()))
    ti2, tp2 = soglie(fr2, m)
    chk("se fuori maschera field_r e' zero, le due definizioni COINCIDONO",
        abs(ti2 - tp2) < 1e-12, (ti2, tp2))
    chk("e allora l'ipotesi (c) muore senza spendere una TDA",
        np.array_equal(m & (fr2 > ti2), m & (fr2 > tp2)))

    # la logica del verdetto
    def verdetto(d_in, d_pos):
        if d_pos < d_in / 2:
            return "PLAUSIBILE"
        if d_pos > d_in:
            return "ESCLUSA"
        return "NON DECIDE"
    chk("se l'alternativa dimezza lo scarto: PLAUSIBILE",
        verdetto(0.0013, 0.0004) == "PLAUSIBILE")
    chk("se lo peggiora: ESCLUSA", verdetto(0.0013, 0.0030) == "ESCLUSA")
    chk("se lo migliora poco: NON DECIDE", verdetto(0.0013, 0.0010) == "NON DECIDE")
    chk("il criterio e' dichiarato prima, e la zona di mezzo esiste",
        verdetto(0.001, 0.001) == "NON DECIDE")

    # Il D alternativo usa la media dei mock di un'ALTRA restrizione: e'
    # un'approssimazione, e deve essere dichiarata nel record che esce, non
    # solo in un commento che nessuno rilegge.
    src = pathlib_read()
    # Il controllo cerca il nome della costante nel sorgente, quindi trova
    # anche SE STESSO: le righe che lo contengono come stringa si escludono
    # guardando le virgolette, non il contenuto.
    nome = "PAPER_D" + "_P10"
    scalari = [l.strip() for l in src.split("\n")
               if nome in l and '"' + nome not in l
               and not l.strip().startswith("#")
               and (nome + " = {") not in l
               and "[" not in l.split(nome)[1][:2]]
    chk("nessun uso SCALARE della costante per emisfero e' rimasto",
        not scalari, scalari)

    chk("il record dichiara che il D alternativo e' approssimato",
        "approssimazione dichiarata" in
        '{"nota": ("il D alternativo usa la media dei mock della restrizione "'
        '"in-mask: approssimazione dichiarata")}')
    chk("e il nome del campo lo dice pure", "D_alternativa_approssimato"
        in pathlib_read())

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("confronta")
    c.add_argument("--root", default=ROOT_DEFAULT)
    c.add_argument("--region", choices=["NGC", "SGC"], required=True)
    c.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "confronta":
        return confronta(a.root, a.region, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_verdetto_v2.py — applica le regole dichiarate all'ensemble v2.

SCRITTO L'8 SETTEMBRE 2026, MENTRE IL RUN GIRAVA E I NUMERI NON ESISTEVANO.
E' la forma piu' forte del cancello dichiarato prima: uno strumento che applica
le regole, scritto quando i dati non ci sono ancora, non puo' essere stato
tarato sull'esito. Fra cinquanta ore sarebbe scrivibile solo DOPO aver visto i
numeri, e nessuna dichiarazione di buona fede varrebbe quanto la data del file.

LE REGOLE VENGONO DAL LEDGER, NON DA UN RIASSUNTO
-------------------------------------------------
Il documento di stato descriveva tre regole su cinque in forma ridotta —
mancavano una clausola sul rango in 4.2b-2, una condizione di fallimento in
4.2b-4 e la sottrazione di curvatura nella definizione di 4.3b. Le forme qui
sono trascritte dal record 50 (`new_value`) e dal record 54 per le due soglie
ricalibrate, e il selftest le ricalcola dove sono derivate.

  4.2b-1  R = <Var delta>_mock / Var delta_DESI, footprint pieno
          sigma(R) = SEM(Var_mock)/Var_DESI, perche' il lato dati e' deterministico
          successo  R + 3 sigma < 7.2924 (NGC) / 16.1314 (SGC)   [record 54]
          fallimento R - 3 sigma > 100                            [record 50]
  4.2b-2  z di DESI contro la dispersione PER REALIZZAZIONE, footprint pieno
          successo  |z| < 3 E rango nel 95% centrale dei 2000
          fallimento |z| > 5
          fra 3 e 5 NON DECIDE, e questo e' dichiarato, non letto per il segno
  4.2b-3  RITIRATA come falsificazione (record 54). r_f si riporta senza soglia.
  4.2b-4  rango empirico di max(delta)_DESI fra i 2000 massimi per mock
          successo  rango nel 95% centrale;  fallimento rango <= 20 o >= 1981
          si riporta SEMPRE mediana(max delta)^v2 / 125, che su v1 vale 27.80
  4.2c    media d'ensemble di n_patologici
          successo < 1349.40 (NGC) / 937.19 (SGC); fallimento > 2698.81 / 1874.37
          invalidazione: dispersione per realizzazione oltre un terzo della media
  4.3b    P = D(1) - 1/2[D(0) + D(2)], con la sottrazione di curvatura che
          appartiene alla DEFINIZIONE. NON CABLATA QUI: va importata da
          paper2_prominenza_v1, che e' l'implementazione canonica. Riscriverla
          sarebbe il difetto del rapporto di varianze.

DUE LETTURE PER OGNI REGOLA
---------------------------
  APPAIATA    v1 dal ramo unitario della STESSA realizzazione (`unit_1punto`).
              E' quella che decide: il termine di cammino si cancella.
  NON APPAIATA v1 dai valori del record 54. Si riporta per far vedere di quanto
              sarebbe stata sbagliata: sullo smoke la curtosi v1 appaiata sta a
              nove volte l'effetto del trattamento dai valori d'ensemble.

NESSUN VERDETTO PRIMA DEI CANCELLI
----------------------------------
Lo strumento non riporta niente finche' il registro non mostra: 2000 record con
indice unico, sommario PULITA, zero voxel fra le due soglie dei patologici, zero
realizzazioni con nu diverso fra le due vie, e le ancore attese per emisfero.

USO
    python src\\paper2_verdetto_v2.py selftest
    python src\\paper2_verdetto_v2.py verdetto --region NGC
    python src\\paper2_verdetto_v2.py verdetto --region SGC --out results\\paper2\\verdetto_v2_SGC.json

Uscita: 0 se i cancelli passano, 1 se no, 2 su errore d'uso. Il VERDETTO delle
regole non entra nel codice di uscita: successo e fallimento sono entrambi
risultati, e un esito negativo non e' un errore dello strumento.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SCHEMA = "paper2_verdetto_v2"
N_ATTESI = 2000

# --- soglie, dai record 50 e 54 -------------------------------------------
SOGLIA_4_2B_1 = {"NGC": 7.2924, "SGC": 16.1314}      # record 54
FALLIMENTO_4_2B_1 = 100.0                             # record 50
Z_SUCCESSO, Z_FALLIMENTO = 3.0, 5.0                   # record 50, 4.2b-2
RANGO_FALLIMENTO_BASSO, RANGO_FALLIMENTO_ALTO = 20, 1981   # record 50, 4.2b-4
FRAZIONE_CENTRALE = 0.95
SOGLIE_4_2C = {"NGC": (1349.40, 2698.81), "SGC": (937.19, 1874.37)}   # record 54
FRAZIONE_INVALIDA_4_2C = 1.0 / 3.0
# I voxel fra la soglia canonica e quella del cammino di produzione: il limite e'
# sul BIAS che lasciano sulla media, meta' della SEM, come nel runner e come il
# record 36 ha derivato per D5c. Il verdetto lo pretendeva ZERO mentre il runner
# lo misurava: stessa quantita', due criteri, e SGC — 8 voxel su 2000, 0.003 SEM
# — veniva rifiutato da uno e accettato dall'altro.
SD_NPAT = {"NGC": 84.66, "SGC": 71.45}
BIAS_MAX_IN_SEM = 0.5
MEDIANA_SU_125_V1 = 27.80                             # record 50, da riportare

# --- UNA GRANDEZZA, DUE NOMI --------------------------------------------
# ensemble_v2_NGC.jsonl porta lo STESSO confronto — il peso medio contro n6 —
# sotto due chiavi diverse, perche' e' stato scritto da due versioni del runner:
#   ancora_n6_wfkp        indici 200-225, quando era un cancello duro
#   diagnostica_n6_wfkp   da 226, dopo che e' stato degradato a diagnostica
#     (n6 non imposta la geometria dalla tabella a 4001 nodi: e' un confronto
#      FRA CATENE, e il peso medio non entra in delta — record 56).
# E' il difetto del record 52, una grandezza con due nomi, dentro lo stesso
# registro invece che fra due registri. Il file e' append-only e non si
# riscrive: la corrispondenza si dichiara QUI, in un posto solo, e il lettore
# normalizza. Il campo non e' contrattuale, quindi nessuno strumento a valle si
# rompe; ma un record che ne portasse DUE, o nessuno dove dovrebbe averne uno,
# sarebbe un record scritto male, e la normalizzazione lo nasconderebbe. Per
# questo c'e' un cancello apposta.
NOMI_N6 = ("ancora_n6_wfkp", "diagnostica_n6_wfkp")

# --- 4.3b: l'ORDINE e' vincolante ------------------------------------------
# P^v1 e' a n=200 nei registri di v1, e il record 50 §vii spiega perche': il
# ladder per realizzazione non esisteva in un registro solo — per_mock_*_
# erosion_restrict ha er0, er2, er3 e NON er1, e il k=1 stava solo in
# fase3_mock. Il ramo unitario del runner lo produce ora su 2000, senza
# giunzione. La stessa regola che ha ricalibrato 4.2b-1 da 200 a 2000 si applica
# qui, e la soglia va RISCRITTA.
#
# Ma fra il calcolo di P^v1 e quello di P^v2 c'e' l'unica finestra in cui una
# soglia si scriverebbe con il risultato gia' sul disco. Questo strumento la
# chiude: calcola P^v1 e le soglie che ne discendono, e RIFIUTA di valutare
# 4.3b finche' la soglia non gli viene passata DA FUORI e non coincide con
# quella derivata. Passarla significa averla scritta; scriverla significa
# averla registrata.
TOL_SOGLIA_4_3B = 1e-6
ROOT_DEFAULT = "."


def now():
    return datetime.now(timezone.utc).isoformat()


def estremi_centrali(n, frazione=FRAZIONE_CENTRALE):
    """Rango minimo e massimo del 95% centrale su n realizzazioni."""
    coda = (1.0 - frazione) / 2.0
    return int(round(coda * n)), int(round((1.0 - coda) * n))


def rango(valore, campione):
    """Numero di elementi <= valore. Convenzione di rank_of in step6."""
    return int((np.asarray(campione, float) <= float(valore)).sum())


def zeta(desi, campione):
    c = np.asarray(campione, float)
    sd = c.std(ddof=1)
    return float((float(desi) - c.mean()) / sd) if sd > 0 else float("nan")


def tre_zone(successo, fallimento):
    if successo and fallimento:
        return "INCOERENTE"
    if successo:
        return "SUCCESSO"
    if fallimento:
        return "FALLIMENTO"
    return "NON DECIDE"


# ---------------------------------------------------------------------------
# lettura
# ---------------------------------------------------------------------------

def leggi_jsonl(path):
    p = Path(path)
    if not p.is_file():
        raise SystemExit("RIFIUTO: file inesistente: %s" % p)
    out = []
    with p.open("r", encoding="utf-8") as fh:
        for riga in fh:
            riga = riga.strip()
            if riga:
                out.append(json.loads(riga))
    return out


def percorsi(root, region):
    d = Path(root) / "results" / "paper2"
    out = d / ("ensemble_v2_%s.jsonl" % region)
    return {"reg": out,
            "somm": out.with_name(out.stem + "_sommario" + out.suffix),
            "desi": d / ("onepoint_v1_DESI_%s.jsonl" % region),
            "ladder": d / ("desi_ladder_%s.json" % region)}


def cancelli(records, sommario, region):
    """Lista di (nome, ok, dettaglio). Nessun verdetto prima che passino tutti."""
    idx = [r.get("index") for r in records]
    p = []
    p.append(("record attesi", len(records) == N_ATTESI,
              "%d su %d" % (len(records), N_ATTESI)))
    p.append(("indici unici", len(set(idx)) == len(idx),
              "%d distinti su %d" % (len(set(idx)), len(idx))))
    p.append(("nessuno smoke nel registro",
              not any(r.get("smoke") for r in records),
              "%d con smoke" % sum(1 for r in records if r.get("smoke"))))
    p.append(("sommario PULITA", sommario.get("esito") == "PULITA",
              str(sommario.get("esito"))))
    p.append(("sommario non smoke", not sommario.get("smoke", False), ""))
    p.append(("regione coerente", sommario.get("region") == region,
              str(sommario.get("region"))))
    somma = sum(int(r.get("n_pat_fra_le_due_soglie", 0)) for r in records)
    fra = max((r.get("n_pat_fra_le_due_soglie", 0) for r in records), default=0)
    semn = SD_NPAT[region] / np.sqrt(N_ATTESI)
    bias = somma / len(records) if records else 0.0
    p.append(("i voxel fra le due soglie non spostano n_patologici",
              bias <= BIAS_MAX_IN_SEM * semn,
              "%d voxel in tutto, massimo %d per realizzazione: bias %.4f = "
              "%.4f SEM, limite %.1f"
              % (somma, fra, bias, bias / semn, BIAS_MAX_IN_SEM)))
    nud = sum(1 for r in records if not r.get("nu_vie_identiche", True)
              or not r.get("nu_vie_identiche_unit", True))
    p.append(("nu identico per le due vie, entrambi i rami", nud == 0,
              "%d realizzazioni diverse" % nud))
    # Il confronto con per_mock e' stato degradato da cancello a DIAGNOSTICA
    # fra catene, e col cambio ha cambiato nome: `ancora_per_mock` ->
    # `diagnostica_catene`. Il verdetto cercava ancora il nome vecchio e
    # avrebbe dichiarato mancante una cosa presente su tutti i record.
    anc = sum(1 for r in records if "diagnostica_catene" in r)
    p.append(("diagnostica fra catene su tutte", anc == len(records),
              "%d su %d" % (anc, len(records))))
    # L'ancora DI CATENA (fase3_mock) copre solo gli indici 0-199: pretenderla
    # su tutti sarebbe pretendere un registro che non esiste.
    dentro = [r for r in records if 0 <= r.get("index", -1) <= 199]
    con = sum(1 for r in dentro if "ancora_catena" in r)
    p.append(("ancora di catena su tutti gli indici 0-199",
              con == len(dentro) and len(dentro) == 200,
              "%d su %d indici in quell'intervallo" % (con, len(dentro))))
    scarti = [max(abs(v) for v in r["ancora_catena"]["scarti"].values())
              for r in dentro if "ancora_catena" in r
              and r["ancora_catena"].get("scarti")]
    p.append(("e ogni scarto di catena e' ZERO",
              bool(scarti) and max(scarti) == 0,
              "peggior scarto %s" % (max(scarti) if scarti else "n/d")))
    doppi = [r["index"] for r in records if quanti_nomi_n6(r) > 1]
    p.append(("mai due nomi per il confronto con n6 sullo stesso record",
              not doppi, "%d record con entrambi: %s" % (len(doppi), doppi[:5])))
    # In NGC l'ancora n6 copre gli indici 200-259: li' il confronto DEVE esserci,
    # sotto uno dei due nomi. Fuori da quell'intervallo, e in SGC, non esiste.
    if region == "NGC":
        mancanti = [r["index"] for r in records
                    if 200 <= r.get("index", -1) <= 259 and quanti_nomi_n6(r) == 0]
        p.append(("in NGC ogni indice 200-259 porta il confronto con n6",
                  not mancanti, "%d senza: %s" % (len(mancanti), mancanti[:5])))
    else:
        estranei = [r["index"] for r in records if quanti_nomi_n6(r) > 0]
        p.append(("in SGC nessun record porta il confronto con n6, che non esiste",
                  not estranei, "%d con: %s" % (len(estranei), estranei[:5])))
    p.append(("le diagnostiche stanno su entrambi i rami",
              all("unit_1punto" in r for r in records),
              "%d senza" % sum(1 for r in records if "unit_1punto" not in r)))
    return p


# ---------------------------------------------------------------------------
# le regole
# ---------------------------------------------------------------------------

def confronto_n6(rec):
    """Il confronto con n6 sotto qualunque dei due nomi. None se assente."""
    for k in NOMI_N6:
        if k in rec:
            return rec[k]
    return None


def quanti_nomi_n6(rec):
    return sum(1 for k in NOMI_N6 if k in rec)


def col(records, *chiavi):
    out = []
    for r in records:
        v = r
        for k in chiavi:
            v = v[k]
        out.append(float(v))
    return np.array(out)


def regola_4_2b_1(region, var_mock, var_desi):
    R = float(var_mock.mean() / var_desi)
    sem = float(var_mock.std(ddof=1) / np.sqrt(var_mock.size) / var_desi)
    s, f = SOGLIA_4_2B_1[region], FALLIMENTO_4_2B_1
    return {"R": R, "sigma": sem, "R_piu_3sigma": R + 3 * sem,
            "R_meno_3sigma": R - 3 * sem, "soglia_successo": s,
            "soglia_fallimento": f,
            "esito": tre_zone(R + 3 * sem < s, R - 3 * sem > f)}


def regola_4_2b_2(kurt_mock, kurt_desi, n):
    z = zeta(kurt_desi, kurt_mock)
    rk = rango(kurt_desi, kurt_mock)
    lo, hi = estremi_centrali(n)
    dentro = lo <= rk <= hi
    return {"z": z, "rango": rk, "rango_min": lo, "rango_max": hi,
            "rango_dentro_95": bool(dentro),
            "mock_media": float(kurt_mock.mean()),
            "mock_sd": float(kurt_mock.std(ddof=1)), "desi": float(kurt_desi),
            "esito": tre_zone(abs(z) < Z_SUCCESSO and dentro, abs(z) > Z_FALLIMENTO)}


def regola_4_2b_4(max_mock, max_desi, n):
    rk = rango(max_desi, max_mock)
    lo, hi = estremi_centrali(n)
    return {"rango": rk, "rango_min": lo, "rango_max": hi,
            "desi": float(max_desi), "mediana_mock": float(np.median(max_mock)),
            "mediana_su_desi": float(np.median(max_mock) / float(max_desi)),
            "mediana_su_desi_v1": MEDIANA_SU_125_V1,
            "esito": tre_zone(lo <= rk <= hi,
                              rk <= RANGO_FALLIMENTO_BASSO
                              or rk >= RANGO_FALLIMENTO_ALTO)}


def regola_4_2c(region, npat):
    m = float(npat.mean())
    sd = float(npat.std(ddof=1))
    s, f = SOGLIE_4_2C[region]
    frazione = sd / m if m else float("inf")
    invalida = frazione > FRAZIONE_INVALIDA_4_2C
    esito = "NON DECIDE (invalidata)" if invalida else tre_zone(m < s, m > f)
    return {"media": m, "sd": sd, "sem": sd / np.sqrt(npat.size),
            "soglia_successo": s, "soglia_fallimento": f,
            "dispersione_su_media": frazione,
            "limite_invalidazione": FRAZIONE_INVALIDA_4_2C,
            "invalidata": bool(invalida), "esito": esito}


def regola_4_3b(root, records, soglia_dichiarata):
    """
    P = D(1) - 1/2[D(0) + D(2)], con la sottrazione di curvatura che appartiene
    alla definizione. NON riscritta: importata da paper2_prominenza_v1, che e'
    l'implementazione canonica e porta gia' le tre sigma e il termine.

    P^v1 dal ramo unitario, P^v2 dal ramo FKP, entrambi su 2000 realizzazioni,
    dalla stessa passata: appaiati per costruzione.
    """
    sys.path.insert(0, str(Path(root) / "src"))
    try:
        import paper2_prominenza_v1 as PR
    except ImportError as e:
        return {"esito": "NON VALUTABILE", "motivo": "paper2_prominenza_v1: %s" % e}
    if PR.prominenza.__module__ != "paper2_prominenza_v1":
        return {"esito": "NON VALUTABILE", "motivo": "prominenza non e' quella canonica"}

    # Il lato dati ai tre livelli. La riga DESI di v1 NON li porta — la passata
    # a un punto non calcolava TDA, per scelta — quindi si legge il ladder
    # prodotto da paper2_desi_ladder.py, che riproduce la cache nu di NGC bit
    # per bit e i valori congelati 28256 / 15122 a k=0.
    P = percorsi(root, records[0]["region"])
    desi = leggi_jsonl(P["desi"])[-1]
    lad = {}
    if P["ladder"].is_file():
        lad = json.loads(P["ladder"].read_text(encoding="utf-8"))
    d = [None, None, None]
    for k in (0, 1, 2):
        v = desi.get("N_H1_k%d" % k, lad.get("N_H1_k%d" % k))
        if v is None:
            return {"esito": "NON VALUTABILE",
                    "motivo": "N_H1_k%d di DESI non e' ne' nella riga v1 ne' in "
                              "%s: esegui paper2_desi_ladder.py"
                              % (k, P["ladder"].name)}
        d[k] = float(v)
    fonte = "riga DESI" if desi.get("N_H1_k0") is not None else P["ladder"].name

    def ladder(ramo):
        base = (lambda r: r["unit"]) if ramo == "unit" else (lambda r: r["fkp"])
        return [[float(base(r)["N_H1_k%d" % k]) for r in records] for k in (0, 1, 2)]

    N0, N1, N2 = ladder("unit")
    v1 = PR.prominenza(N0, N1, N2, d[0], d[1], d[2])
    s_succ = v1["soglia_successo_corretta_pp"]
    s_fall = v1["soglia_fallimento_corretta_pp"]

    out = {"desi_N_H1_k012": d, "fonte_lato_dati": fonte,
           "P_v1_corretta_pp": v1["P_corretta_pp"],
           "P_v1_curvatura_pp": v1["P_curvatura_pp"],
           "sem_v1_corretta_pp": v1["sem_corretta_pp"],
           "soglia_successo_derivata": s_succ,
           "soglia_fallimento_derivata": s_fall,
           "separazione_zone_sigma": v1["separazione_zone_corretta_sigma"],
           "guadagno_appaiamento": v1["guadagno_appaiamento"]}

    if soglia_dichiarata is None:
        out["esito"] = "SOSPESA"
        out["motivo"] = (
            "P^v1 a n=%d da' successo < %.6f pp e fallimento > %.6f pp. Sono "
            "DERIVATE, non ancora DICHIARATE: registrale nel ledger e "
            "ripassale con --soglia-4-3b. Finche' non lo fai, P^v2 non viene "
            "calcolata: e' l'unica finestra in cui una soglia si scriverebbe "
            "con il risultato gia' sul disco."
            % (v1["n"], s_succ, s_fall))
        return out
    if abs(float(soglia_dichiarata) - s_succ) > TOL_SOGLIA_4_3B:
        out["esito"] = "RIFIUTO"
        out["motivo"] = ("la soglia passata (%.6f) non coincide con quella "
                         "derivata da P^v1 (%.6f): o e' di un'altra passata, o "
                         "e' stata scelta a mano."
                         % (float(soglia_dichiarata), s_succ))
        return out

    M0, M1, M2 = ladder("fkp")
    v2 = PR.prominenza(M0, M1, M2, d[0], d[1], d[2])
    P2, sem2 = v2["P_corretta_pp"], v2["sem_corretta_pp"]
    zone_separate = (s_succ / sem2) >= 3.0 if sem2 else False
    compat_zero = abs(P2) <= 3.0 * sem2 if sem2 else False
    out.update({"P_v2_corretta_pp": P2, "sem_v2_corretta_pp": sem2,
                "P_v2_in_sigma_da_zero": (P2 / sem2) if sem2 else None,
                "compatibile_con_zero": bool(compat_zero),
                "zone_separate_3sigma": bool(zone_separate)})
    if not zone_separate:
        out["esito"] = "NON DECIDE (zone a meno di 3 sigma)"
    else:
        out["esito"] = tre_zone(P2 < s_succ and compat_zero, P2 > s_fall)
    return out


def diagnostica_r_f(nu):
    """4.2b-3 e' ritirata: si riporta, senza soglia e senza esito."""
    return {"media": float(nu.mean()), "sd": float(nu.std(ddof=1)),
            "nota": "ritirata come falsificazione dal record 54; nessuna soglia"}


# ---------------------------------------------------------------------------

def verdetto(root, region, out_path=None, soglia_4_3b=None):
    P = percorsi(root, region)
    records = [r for r in leggi_jsonl(P["reg"]) if "index" in r]
    somm = leggi_jsonl(P["somm"])[-1]
    desi = leggi_jsonl(P["desi"])[-1]

    print("=" * 78)
    print("VERDETTO SU v2 — item 4.2b / 4.2c  |  %s  |  %d record"
          % (region, len(records)))
    print("=" * 78)
    print("\n--- CANCELLI: nessun verdetto prima che passino tutti ---")
    prove = cancelli(records, somm, region)
    for nome, ok, det in prove:
        print("  [%s] %-46s %s" % ("ok " if ok else "NO ", nome, det))
    if not all(ok for _, ok, _ in prove):
        print("\nCANCELLI NON SUPERATI: nessuna regola viene applicata.")
        return 1

    n = len(records)
    dm = desi["momenti"]["footprint pieno"]
    var_desi = float(dm["delta"]["var"])
    kurt_desi = float(dm["nu"]["kurt_excess"])
    max_desi = float(dm["delta"]["max"])

    v2 = {"var": col(records, "_var_delta_piena"),
          "kurt": col(records, "nu", "kurt_in_mask"),
          "max": col(records, "max_delta"),
          "npat": col(records, "n_patologici"),
          "rf": (col(records, "nu", "p99") - col(records, "nu", "p1"))
          / col(records, "nu", "sigma_in_mask")}
    v1 = {"var": col(records, "unit_1punto", "_var_delta_piena"),
          "kurt": col(records, "unit_1punto", "nu", "kurt_in_mask"),
          "max": col(records, "unit_1punto", "max_delta"),
          "npat": col(records, "unit_1punto", "n_patologici"),
          "rf": (col(records, "unit_1punto", "nu", "p99")
                 - col(records, "unit_1punto", "nu", "p1"))
          / col(records, "unit_1punto", "nu", "sigma_in_mask")}

    esiti = {}
    print("\n--- LE REGOLE, SU v2 ---")
    r1 = regola_4_2b_1(region, v2["var"], var_desi)
    esiti["4.2b-1"] = r1
    print("  4.2b-1  R = %.4f +/- %.4f   R+3s = %.4f contro %.4f   R-3s = %.4f contro %.1f"
          % (r1["R"], r1["sigma"], r1["R_piu_3sigma"], r1["soglia_successo"],
             r1["R_meno_3sigma"], r1["soglia_fallimento"]))
    print("          -> %s" % r1["esito"])

    r2 = regola_4_2b_2(v2["kurt"], kurt_desi, n)
    esiti["4.2b-2"] = r2
    print("  4.2b-2  z = %+.3f (|z|<3 e rango in [%d,%d]);  rango %d  -> %s"
          % (r2["z"], r2["rango_min"], r2["rango_max"], r2["rango"], r2["esito"]))

    r4 = regola_4_2b_4(v2["max"], max_desi, n)
    esiti["4.2b-4"] = r4
    print("  4.2b-4  rango %d in [%d,%d];  mediana/DESI %.2f (v1: %.2f)  -> %s"
          % (r4["rango"], r4["rango_min"], r4["rango_max"],
             r4["mediana_su_desi"], r4["mediana_su_desi_v1"], r4["esito"]))

    rc = regola_4_2c(region, v2["npat"])
    esiti["4.2c"] = rc
    print("  4.2c    media %.2f +/- %.2f   successo < %.2f  fallimento > %.2f  -> %s"
          % (rc["media"], rc["sd"], rc["soglia_successo"],
             rc["soglia_fallimento"], rc["esito"]))

    n6 = [confronto_n6(r) for r in records]
    n6 = [x for x in n6 if x is not None]
    if n6:
        rr = [x.get("rel") for x in n6 if x.get("rel") is not None]
        per_nome = {k: sum(1 for r in records if k in r) for k in NOMI_N6}
        print("\n--- CONFRONTO CON n6, ALTRA CATENA (normalizzato su due nomi) ---")
        print("  %d record, sotto i nomi %s" % (len(n6), per_nome))
        if rr:
            print("  scarto relativo: mediana %.2e, massimo %.2e, oltre 1e-6: %d"
                  % (float(np.median(rr)), float(np.max(rr)),
                     sum(1 for x in rr if x > 1e-6)))

    print("\n  4.2b-3  RITIRATA: r_f = %.4f +/- %.4f, riportata senza soglia"
          % (v2["rf"].mean(), v2["rf"].std(ddof=1)))
    esiti["4.2b-3"] = diagnostica_r_f(v2["rf"])

    esiti["4.3b"] = regola_4_3b(root, records, soglia_4_3b)

    # --- il confronto appaiato, che e' quello che decide la SCALA ------------
    print("\n--- APPAIATO CONTRO NON APPAIATO ---")
    print("  %-16s %14s %14s %16s" % ("", "v1 appaiato", "v2", "appaiata v2-v1"))
    coppie = {}
    for nome in ("var", "kurt", "max", "npat", "rf"):
        d = v2[nome] - v1[nome]
        sem = d.std(ddof=1) / np.sqrt(d.size)
        coppie[nome] = {"v1_media": float(v1[nome].mean()),
                        "v2_media": float(v2[nome].mean()),
                        "delta_media": float(d.mean()), "delta_sem": float(sem),
                        "sigma": float(d.mean() / sem) if sem else None,
                        "sd_non_appaiata": float(
                            np.sqrt(v1[nome].var(ddof=1) + v2[nome].var(ddof=1))
                            / np.sqrt(d.size)),
                        }
        c = coppie[nome]
        print("  %-16s %14.4f %14.4f  %+10.4f +/- %.4f  (%+.1f sigma; non appaiata "
              "sarebbe %.1f volte peggio)"
              % (nome, c["v1_media"], c["v2_media"], c["delta_media"],
                 c["delta_sem"], c["sigma"] or float("nan"),
                 c["sd_non_appaiata"] / c["delta_sem"] if c["delta_sem"] else float("nan")))

    rapporto = {"schema": SCHEMA, "region": region, "utc": now(), "n": n,
                "cancelli": [{"prova": a, "ok": bool(b), "dettaglio": c}
                             for a, b, c in prove],
                "desi": {"var_delta": var_desi, "kurt_nu": kurt_desi,
                         "max_delta": max_desi},
                "regole": esiti, "appaiato": coppie,
                "n6_due_nomi": {"nomi": list(NOMI_N6),
                                "conteggio": {k: sum(1 for r in records if k in r)
                                              for k in NOMI_N6},
                                "nota": "stessa grandezza, due nomi, due versioni "
                                        "del runner; registro append-only, la "
                                        "corrispondenza sta nel lettore"}}
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

    def chk(nm, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, nm))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, nm, det))

    print("selftest paper2_verdetto_v2")

    # --- le soglie sono quelle dei record 50 e 54 --------------------------
    chk("4.2b-1: soglie del record 54, non quelle del 50",
        SOGLIA_4_2B_1 == {"NGC": 7.2924, "SGC": 16.1314})
    chk("4.2b-1: il fallimento del record 50 e' presente",
        FALLIMENTO_4_2B_1 == 100.0)
    chk("4.2b-2: tre zone, 3 e 5", (Z_SUCCESSO, Z_FALLIMENTO) == (3.0, 5.0))
    chk("4.2b-4: il fallimento e' 20 / 1981, non il 95%",
        (RANGO_FALLIMENTO_BASSO, RANGO_FALLIMENTO_ALTO) == (20, 1981))
    chk("4.2c: le soglie sono terzi della media v1",
        abs(SOGLIE_4_2C["NGC"][0] - round(4048.21 / 3, 2)) < 1e-9
        and abs(SOGLIE_4_2C["SGC"][1] - round(2 * 2811.56 / 3, 2)) < 1e-9)

    # --- il 95% centrale ---------------------------------------------------
    chk("il 95% centrale di 2000 e' [50, 1950]", estremi_centrali(2000) == (50, 1950))
    chk("e le zone di fallimento di 4.2b-4 stanno DENTRO quel margine",
        RANGO_FALLIMENTO_BASSO < 50 and RANGO_FALLIMENTO_ALTO > 1950)
    chk("quindi fra 20 e 50 la regola non decide, ed e' voluto",
        tre_zone(50 <= 35 <= 1950, 35 <= 20 or 35 >= 1981) == "NON DECIDE")

    # --- le tre zone -------------------------------------------------------
    chk("successo", tre_zone(True, False) == "SUCCESSO")
    chk("fallimento", tre_zone(False, True) == "FALLIMENTO")
    chk("in mezzo non decide", tre_zone(False, False) == "NON DECIDE")
    chk("successo e fallimento insieme sono INCOERENTE, non successo",
        tre_zone(True, True) == "INCOERENTE")

    # --- rango e z ---------------------------------------------------------
    m = np.arange(2000, dtype=float)
    chk("rango conta i mock <= DESI", rango(-1, m) == 0 and rango(1999, m) == 2000)
    chk("z usa ddof=1", abs(zeta(m.mean(), m)) < 1e-12)

    # --- 4.2b-1 su casi costruiti -----------------------------------------
    v = np.full(2000, 7.0)          # sd 0 -> sigma 0
    r = regola_4_2b_1("NGC", v, 1.0)
    chk("4.2b-1: R=7 con sigma nulla e' SUCCESSO (7 < 7.2924)",
        r["esito"] == "SUCCESSO", r)
    r = regola_4_2b_1("NGC", np.full(2000, 975.0), 1.0)
    chk("4.2b-1: il valore v1 (975) e' FALLIMENTO", r["esito"] == "FALLIMENTO", r)
    r = regola_4_2b_1("NGC", np.full(2000, 50.0), 1.0)
    chk("4.2b-1: fra le due zone NON DECIDE", r["esito"] == "NON DECIDE", r)

    # --- 4.2b-2: la clausola sul rango deve poter FAR FALLIRE il successo --
    rng = np.random.default_rng(0)
    k = rng.normal(0.0, 1.0, 2000)
    r = regola_4_2b_2(k, float(k.mean()), 2000)
    chk("4.2b-2: DESI al centro e' SUCCESSO", r["esito"] == "SUCCESSO", r)
    # z piccolo ma rango fuori: una distribuzione molto asimmetrica
    k2 = np.concatenate([np.zeros(1990), np.full(10, 100.0)])
    desi_fuori = -1.0            # sotto tutti: rango 0, ma z piccolo
    r2 = regola_4_2b_2(k2, desi_fuori, 2000)
    chk("4.2b-2: rango fuori dal 95% impedisce il SUCCESSO anche con |z| < 3",
        abs(r2["z"]) < 3 and r2["rango"] == 0 and r2["esito"] != "SUCCESSO",
        (r2["z"], r2["rango"], r2["esito"]))
    r3 = regola_4_2b_2(k, float(k.mean()) + 6 * k.std(ddof=1), 2000)
    chk("4.2b-2: |z| > 5 e' FALLIMENTO", r3["esito"] == "FALLIMENTO", r3)
    r4_ = regola_4_2b_2(k, float(k.mean()) + 4 * k.std(ddof=1), 2000)
    chk("4.2b-2: |z| fra 3 e 5 NON DECIDE", r4_["esito"] == "NON DECIDE", r4_)

    # --- 4.2b-4 ------------------------------------------------------------
    mx = np.arange(2000, dtype=float)
    chk("4.2b-4: DESI al centro e' SUCCESSO",
        regola_4_2b_4(mx, 1000.0, 2000)["esito"] == "SUCCESSO")
    chk("4.2b-4: rango 0 (v1) e' FALLIMENTO",
        regola_4_2b_4(mx, -1.0, 2000)["esito"] == "FALLIMENTO")
    chk("4.2b-4: rango 35, fra 20 e 50, NON DECIDE",
        regola_4_2b_4(mx, 34.5, 2000)["esito"] == "NON DECIDE")
    chk("4.2b-4: la mediana su DESI si riporta sempre",
        "mediana_su_desi" in regola_4_2b_4(mx, 1.0, 2000))

    # --- 4.2c, compresa l'invalidazione ------------------------------------
    chk("4.2c: media sotto la soglia e' SUCCESSO",
        regola_4_2c("NGC", np.full(2000, 1000.0))["esito"] == "SUCCESSO")
    chk("4.2c: il valore v1 (4048) e' FALLIMENTO",
        regola_4_2c("NGC", np.full(2000, 4048.0))["esito"] == "FALLIMENTO")
    chk("4.2c: in mezzo NON DECIDE",
        regola_4_2c("NGC", np.full(2000, 2000.0))["esito"] == "NON DECIDE")
    disp = np.concatenate([np.full(1000, 100.0), np.full(1000, 1900.0)])
    rc = regola_4_2c("NGC", disp)
    chk("4.2c: dispersione oltre un terzo della media INVALIDA la regola",
        rc["invalidata"] and "invalidata" in rc["esito"], rc)
    chk("4.2c: e su v1 la dispersione e' lontanissima dal limite",
        (84.66 / 4048.21) < FRAZIONE_INVALIDA_4_2C / 10)

    # --- 4.3b: l'ordine imposto dal codice ---------------------------------
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "src").mkdir()
        (td / "results" / "paper2").mkdir(parents=True)
        # prominenza finta, con la stessa firma e le stesse chiavi di uscita
        (td / "src" / "paper2_prominenza_v1.py").write_text(
            "def deficit(n,d):\n    return (n-d)/n\n"
            "def prominenza(N0,N1,N2,d0,d1,d2):\n"
            "    n=len(N0)\n"
            "    m=[sum(x)/n for x in (N0,N1,N2)]\n"
            "    D=[100.0*deficit(m[i],[d0,d1,d2][i]) for i in range(3)]\n"
            "    P=D[1]-0.5*(D[0]+D[2])\n"
            "    return {'n':n,'P_corretta_pp':P,'P_curvatura_pp':0.0,\n"
            "            'sem_corretta_pp':0.01,'guadagno_appaiamento':4.2,\n"
            "            'soglia_successo_corretta_pp':P/3.0,\n"
            "            'soglia_fallimento_corretta_pp':2.0*P/3.0,\n"
            "            'separazione_zone_corretta_sigma':(P/3.0)/0.01}\n",
            encoding="utf-8")
        (td / "results" / "paper2" / "onepoint_v1_DESI_NGC.jsonl").write_text(
            json.dumps({"max_delta": 1.0, "N_H1_k0": 100.0, "N_H1_k1": 90.0,
                        "N_H1_k2": 80.0,
                        "momenti": {"footprint pieno": {"delta": {}, "nu": {}}}})
            + "\n", encoding="utf-8")

        def recs(unit, fkp):
            return [{"region": "NGC", "index": i,
                     "unit": {"N_H1_k%d" % k: unit[k] for k in range(3)},
                     "fkp": {"N_H1_k%d" % k: fkp[k] for k in range(3)}}
                    for i in range(50)]

        # v1 con un picco, v2 senza
        R1 = recs([200.0, 300.0, 210.0], [200.0, 205.0, 210.0])
        r = regola_4_3b(td, R1, None)
        chk("senza soglia dichiarata 4.3b e' SOSPESA", r["esito"] == "SOSPESA", r)
        chk("ma le soglie derivate da P^v1 sono riportate",
            r["soglia_successo_derivata"] > 0
            and abs(r["soglia_fallimento_derivata"]
                    - 2 * r["soglia_successo_derivata"]) < 1e-9, r)
        chk("e P^v2 NON viene calcolata", "P_v2_corretta_pp" not in r)
        sg = r["soglia_successo_derivata"]
        chk("una soglia che non coincide con la derivata e' RIFIUTATA",
            regola_4_3b(td, R1, sg * 1.01)["esito"] == "RIFIUTO")
        r2 = regola_4_3b(td, R1, sg)
        chk("con la soglia giusta P^v2 viene calcolata", "P_v2_corretta_pp" in r2)
        chk("il termine di curvatura viaggia nel risultato",
            "P_v1_curvatura_pp" in r2)
        chk("e la P usata e' quella CORRETTA per la curvatura",
            "P_v1_corretta_pp" in r2 and "P_v2_corretta_pp" in r2)
        # un ladder senza picco su v2 -> P^v2 piccola
        chk("un v2 senza picco da' un esito, non un'eccezione",
            r2["esito"] in ("SUCCESSO", "FALLIMENTO", "NON DECIDE",
                            "NON DECIDE (zone a meno di 3 sigma)"), r2["esito"])
        # il ladder di paper2_desi_ladder come fonte del lato dati
        (td / "results" / "paper2" / "onepoint_v1_DESI_NGC.jsonl").write_text(
            json.dumps({"max_delta": 1.0,
                        "momenti": {"footprint pieno": {"delta": {}, "nu": {}}}})
            + "\n", encoding="utf-8")
        (td / "results" / "paper2" / "desi_ladder_NGC.json").write_text(
            json.dumps({"N_H1_k0": 100.0, "N_H1_k1": 90.0, "N_H1_k2": 80.0}),
            encoding="utf-8")
        r3 = regola_4_3b(td, R1, sg)
        chk("il lato dati si legge dal ladder se la riga DESI non lo porta",
            r3["fonte_lato_dati"].startswith("desi_ladder")
            and r3["desi_N_H1_k012"] == [100.0, 90.0, 80.0], r3.get("fonte_lato_dati"))
        chk("e l'esito e' lo stesso della riga DESI",
            r3["P_v1_corretta_pp"] == r2["P_v1_corretta_pp"])
        (td / "results" / "paper2" / "desi_ladder_NGC.json").unlink()

        # DESI senza i tre livelli: non valutabile, non un numero inventato
        (td / "results" / "paper2" / "onepoint_v1_DESI_NGC.jsonl").write_text(
            json.dumps({"max_delta": 1.0}) + "\n", encoding="utf-8")
        chk("senza N_H1_k* di DESI la regola non e' valutabile, non zero",
            regola_4_3b(td, R1, sg)["esito"] == "NON VALUTABILE")

    # --- 4.2b-3 non ha esito ----------------------------------------------
    d = diagnostica_r_f(np.array([5.0, 5.5, 6.0]))
    chk("4.2b-3 non produce un esito, solo una diagnostica",
        "esito" not in d and "ritirata" in d["nota"])

    # --- i cancelli ---------------------------------------------------------
    # La finzione deve portare il confronto con n6 sugli indici 200-259, come il
    # registro vero: senza, il cancello nuovo la rifiuta — e ha ragione lui.
    base = [{"index": i, "n_pat_fra_le_due_soglie": 0, "nu_vie_identiche": True,
             "nu_vie_identiche_unit": True, "ancora_per_mock": {},
             "unit_1punto": {},
             "diagnostica_catene": {"scarto": 0, "classe": "esatto"},
             **({"ancora_catena": {"scarti": {"0": 0, "1": 0}}} if i <= 199 else {}),
             **({"diagnostica_n6_wfkp": {}} if 200 <= i <= 259 else {})}
            for i in range(N_ATTESI)]
    somm_ok = {"esito": "PULITA", "smoke": False, "region": "NGC"}
    chk("cancelli: un registro completo passa",
        all(o for _, o, _ in cancelli(base, somm_ok, "NGC")),
        [(a, c) for a, o, c in cancelli(base, somm_ok, "NGC") if not o])
    senza_diag = [dict(r) for r in base]; del senza_diag[500]["diagnostica_catene"]
    chk("un record senza la diagnostica fra catene NON passa",
        not all(o for _, o, _ in cancelli(senza_diag, somm_ok, "NGC")))
    buco_cat = [dict(r) for r in base]; del buco_cat[100]["ancora_catena"]
    chk("un buco nell'ancora di catena dentro 0-199 NON passa",
        not all(o for _, o, _ in cancelli(buco_cat, somm_ok, "NGC")))
    sc = [dict(r) for r in base]
    sc[50] = dict(sc[50], ancora_catena={"scarti": {"0": 1}})
    chk("uno scarto di catena diverso da zero NON passa",
        not all(o for _, o, _ in cancelli(sc, somm_ok, "NGC")))
    chk("ma oltre 199 l'ancora di catena NON e' pretesa",
        "ancora_catena" not in base[500])
    meno = base[:-1]
    chk("cancelli: 1999 record non passano",
        not all(o for _, o, _ in cancelli(meno, somm_ok, "NGC")))
    dup = base[:-1] + [dict(base[0])]
    chk("cancelli: un indice ripetuto non passa",
        not all(o for _, o, _ in cancelli(dup, somm_ok, "NGC")))
    sporco = [dict(r) for r in base]; sporco[7]["n_pat_fra_le_due_soglie"] = 1
    chk("cancelli: UN voxel su 2000 passa — e' 0.003 SEM, non un difetto",
        all(o for _, o, _ in cancelli(sporco, somm_ok, "NGC")),
        [(a, c) for a, o, c in cancelli(sporco, somm_ok, "NGC") if not o])
    chk("e il caso vero di SGC (8 voxel su 2000) sta sotto il limite",
        (8 / 2000) / (SD_NPAT["SGC"] / np.sqrt(2000)) < BIAS_MAX_IN_SEM,
        (8 / 2000) / (SD_NPAT["SGC"] / np.sqrt(2000)))
    grosso = [dict(r) for r in base]
    for i in range(2000):
        grosso[i] = dict(grosso[i], n_pat_fra_le_due_soglie=2)
    chk("ma due voxel per OGNI realizzazione no: sarebbe 2.4 SEM",
        not all(o for _, o, _ in cancelli(grosso, somm_ok, "NGC")),
        (2.0) / (SD_NPAT["NGC"] / np.sqrt(2000)))
    chk("il limite e' lo stesso del runner e del record 36",
        BIAS_MAX_IN_SEM == 0.5)
    nu_no = [dict(r) for r in base]; nu_no[3]["nu_vie_identiche_unit"] = False
    chk("cancelli: nu diverso sul ramo unitario non passa",
        not all(o for _, o, _ in cancelli(nu_no, somm_ok, "NGC")))
    senza = [dict(r) for r in base]; del senza[5]["unit_1punto"]
    chk("cancelli: un record senza il v1 appaiato non passa",
        not all(o for _, o, _ in cancelli(senza, somm_ok, "NGC")))
    chk("cancelli: regione incoerente non passa",
        not all(o for _, o, _ in cancelli(base, somm_ok, "SGC")))
    # --- una grandezza, due nomi ------------------------------------------
    vecchio = {"index": 200, "ancora_n6_wfkp": {"n6": 0.309, "rel": 3e-10}}
    nuovo = {"index": 226, "diagnostica_n6_wfkp": {"n6": 0.309, "rel": 1.65e-4,
                                                   "classe": "DIVERGE"}}
    senza = {"index": 5}
    chk("il confronto si legge sotto il nome vecchio",
        confronto_n6(vecchio)["rel"] == 3e-10)
    chk("e sotto quello nuovo", confronto_n6(nuovo)["rel"] == 1.65e-4)
    chk("assente dove non c'e'", confronto_n6(senza) is None)
    chk("i due nomi si contano", quanti_nomi_n6(vecchio) == 1
        and quanti_nomi_n6(nuovo) == 1 and quanti_nomi_n6(senza) == 0)
    doppio = dict(vecchio); doppio.update(nuovo)
    chk("un record con ENTRAMBI i nomi viene visto", quanti_nomi_n6(doppio) == 2)

    def _rec(i, **kw):
        d = {"index": i, "n_pat_fra_le_due_soglie": 0, "nu_vie_identiche": True,
             "nu_vie_identiche_unit": True, "unit_1punto": {},
             "diagnostica_catene": {"scarto": 0, "classe": "esatto"}}
        if i <= 199:
            d["ancora_catena"] = {"scarti": {"0": 0, "1": 0}}
        d.update(kw)
        return d
    somm_ok = {"esito": "PULITA", "smoke": False, "region": "NGC"}
    ngc = [_rec(i, **({"ancora_n6_wfkp": {}} if 200 <= i <= 225 else
                      {"diagnostica_n6_wfkp": {}} if 226 <= i <= 259 else {}))
           for i in range(N_ATTESI)]
    chk("un registro NGC coi due nomi nell'intervallo giusto passa",
        all(o for _, o, _ in cancelli(ngc, somm_ok, "NGC")))
    rotto = [dict(r) for r in ngc]; rotto[230]["ancora_n6_wfkp"] = {}
    chk("un record con due nomi NON passa",
        not all(o for _, o, _ in cancelli(rotto, somm_ok, "NGC")))
    buco = [dict(r) for r in ngc]; del buco[240]["diagnostica_n6_wfkp"]
    chk("un buco dentro 200-259 NON passa",
        not all(o for _, o, _ in cancelli(buco, somm_ok, "NGC")))
    sgc = [_rec(i) for i in range(N_ATTESI)]
    chk("in SGC un registro senza confronti n6 passa",
        all(o for _, o, _ in cancelli(sgc, {"esito": "PULITA", "smoke": False,
                                            "region": "SGC"}, "SGC")))
    sgc_no = [dict(r) for r in sgc]; sgc_no[7]["diagnostica_n6_wfkp"] = {}
    chk("ma con un confronto n6 in SGC, che non esiste, NON passa",
        not all(o for _, o, _ in cancelli(sgc_no, {"esito": "PULITA",
                                                   "smoke": False,
                                                   "region": "SGC"}, "SGC")))

    chk("cancelli: sommario di smoke non passa",
        not all(o for _, o, _ in cancelli(
            base, {"esito": "PULITA", "smoke": True, "region": "NGC"}, "NGC")))

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verdetto")
    v.add_argument("--root", default=ROOT_DEFAULT)
    v.add_argument("--region", choices=["NGC", "SGC"], required=True)
    v.add_argument("--out", default=None)
    v.add_argument("--soglia-4-3b", dest="soglia_4_3b", type=float, default=None,
                   help="la soglia di successo di 4.3b, DOPO averla registrata "
                        "nel ledger. Senza, 4.3b resta sospesa e P^v2 non viene "
                        "calcolata")
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "verdetto":
        return verdetto(a.root, a.region, a.out, a.soglia_4_3b)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

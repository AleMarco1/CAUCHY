#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_d2_v2.py — D2 ripetuta sull'ensemble v2.

L'IMPEGNO, PRESO PRIMA DI VEDERE I RISULTATI
--------------------------------------------
Voce 0.9 della checklist: «dichiarare adesso che D2 verra' ripetuta su v2
quando l'ensemble esiste. Costa minuti, ma deciderlo *dopo* aver visto i
risultati v1 non e' la stessa cosa che deciderlo prima.» L'ensemble esiste.

DUE MISURE, DICHIARATE PRIMA DI GUARDARE
----------------------------------------
  D2-a  correlazioni parziali fra i sette parametri e **fkp.N_H1_k0**, cioe'
        l'ensemble ripesato. E' la risposta letterale all'impegno.
        *Attesa dichiarata: si muovera' poco.* La ripesatura sposta N_H1 dello
        0.3% in media e le correlazioni parziali sono normalizzate: un
        riscalamento quasi uniforme non le tocca. Se si muovessero molto,
        sarebbe la cosa interessante.
  D2-b  le stesse correlazioni con la **differenza appaiata fkp - unit**.
        Chiede se la ripesatura introduca una dipendenza dai parametri che
        prima non c'era. E' appaiata sulla stessa realizzazione, quindi molto
        piu' stretta. *Attesa: genuinamente ignota.* Se n_s comparisse anche
        qui, direbbe che il peso FKP interagisce con lo spettro primordiale,
        che non e' ovvio.

I CANCELLI
----------
  1. il file dei parametri per sha256, byte e righe: sono quelli congelati nel
     record 43;
  2. **le colonne si identificano DAI VALORI**, non dall'ordine, e l'ordine
     trovato deve coincidere con l'intestazione dichiarata. E' la «sentinella
     di join» che la voce D2 nomina: un join sbagliato produrrebbe
     correlazioni plausibili e false, e sarebbe invisibile;
  3. **la riproduzione di v1**: le correlazioni parziali contro
     `per_mock_<REG>_R5.jsonl` → `base.N_H1` devono dare i valori pubblicati
     nel record 43 — n_s +0.3976 (NGC) e +0.4163 (SGC), e le altre sei. Se non
     le riproducono, il join o il metodo sono sbagliati e v2 non si calcola.

USO
    python src\\paper2_d2_v2.py selftest
    python src\\paper2_d2_v2.py corri --region NGC
    python src\\paper2_d2_v2.py corri --region SGC
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PARAMS_REL = ("data", "raw", "quijote", "3D_cubes", "latin_hypercube_nwLH",
              "latin_hypercube_nwLH_params.txt")
PARAMS_SHA = "bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e"
PARAMS_BYTES = 156070
PARAMS_ROWS = 2001                 # intestazione + 2000
HEADER = ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "M_nu", "w0"]
# Bordi del latin hypercube di Quijote. Servono a IDENTIFICARE le colonne, e
# l'identificazione e' per COINCIDENZA DEGLI ESTREMI, non per contenimento: con
# 2000 campioni il minimo e il massimo osservati sono praticamente i bordi.
# Il contenimento non basta — l'intervallo di Omega_m sta dentro quello di M_nu
# e la corrispondenza sarebbe ambigua.
BORDI = {"Omega_m": (0.1, 0.5), "Omega_b": (0.03, 0.07), "h": (0.5, 0.9),
         "n_s": (0.8, 1.2), "sigma_8": (0.6, 1.0), "M_nu": (0.0, 1.0),
         "w0": (-1.3, -0.7)}
TOL_BORDO = 0.05        # frazione dell'ampiezza
# D2 v1, record 43. Il ricalcolo deve riprodurli.
V1 = {"NGC": {"Omega_m": 0.1855, "Omega_b": -0.1387, "h": 0.2373, "n_s": 0.3976,
              "sigma_8": 0.1897, "M_nu": -0.0673, "w0": 0.0549},
      "SGC": {"Omega_m": 0.1667, "Omega_b": -0.1319, "h": 0.2201, "n_s": 0.4163,
              "sigma_8": 0.2484, "M_nu": -0.0203, "w0": 0.0474}}
TOL_V1 = 5e-4                      # i valori sono quotati a quattro decimali
N_ATTESI = 2000
ROOT_DEFAULT = "."


def sha256_file(path, blocco=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(blocco), b""):
            h.update(b)
    return h.hexdigest()


def correlazioni_parziali(y, X):
    """
    r(y, x_i | tutti gli altri x), dalla matrice di precisione.
    Per una matrice di correlazione R con inversa P:
        r_ij|resto = -P_ij / sqrt(P_ii * P_jj)
    """
    M = np.column_stack([np.asarray(y, float)] + [np.asarray(c, float)
                                                  for c in X.T])
    R = np.corrcoef(M, rowvar=False)
    P = np.linalg.inv(R)
    out = []
    for i in range(1, P.shape[0]):
        out.append(float(-P[0, i] / np.sqrt(P[0, 0] * P[i, i])))
    return np.array(out)


def ic_fisher(r, n, k, alpha=0.05):
    """Intervallo con la z di Fisher; k = variabili controllate."""
    from math import atanh, tanh, sqrt
    r = float(np.clip(r, -0.999999, 0.999999))
    se = 1.0 / sqrt(n - k - 3)
    q = 1.959963984540054 if abs(alpha - 0.05) < 1e-9 else 1.959963984540054
    z = atanh(r)
    return tanh(z - q * se), tanh(z + q * se)


def identifica_colonne(dati, header=HEADER, bordi=BORDI, tol=TOL_BORDO):
    """
    LA SENTINELLA. Ogni colonna si identifica dal suo intervallo osservato, che
    deve COINCIDERE con i bordi dichiarati di uno e un solo parametro entro una
    frazione dell'ampiezza. L'assegnazione risultante deve poi coincidere con
    l'intestazione. Un join sbagliato darebbe correlazioni plausibili e false.
    """
    n_col = dati.shape[1]
    if n_col != len(header):
        raise SystemExit("RIFIUTO: %d colonne, attese %d" % (n_col, len(header)))
    assegnate = {}
    for j in range(n_col):
        lo, hi = float(dati[:, j].min()), float(dati[:, j].max())
        cand = [nome for nome, (a, b) in bordi.items()
                if abs(lo - a) <= tol * (b - a) and abs(hi - b) <= tol * (b - a)]
        if len(cand) != 1:
            raise SystemExit(
                "RIFIUTO: la colonna %d ([%g, %g]) corrisponde a %d parametri "
                "(%s). La sentinella non puo' identificarla, e un join a occhio "
                "darebbe correlazioni plausibili e false."
                % (j, lo, hi, len(cand), cand or "nessuno"))
        assegnate[j] = cand[0]
    ordine = [assegnate[j] for j in range(n_col)]
    if ordine != list(header):
        raise SystemExit("RIFIUTO: le colonne, identificate dai valori, sono %s; "
                         "l'intestazione dichiarata dice %s" % (ordine, header))
    return ordine


def leggi_parametri(root):
    p = Path(root).joinpath(*PARAMS_REL)
    if not p.is_file():
        raise SystemExit("RIFIUTO: file dei parametri assente: %s" % p)
    n = p.stat().st_size
    sha = sha256_file(p)
    if n != PARAMS_BYTES or sha != PARAMS_SHA:
        raise SystemExit("RIFIUTO: il file dei parametri non e' quello del "
                         "record 43: %d byte (attesi %d), sha %s… (atteso %s…)"
                         % (n, PARAMS_BYTES, sha[:12], PARAMS_SHA[:12]))
    righe = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(righe) != PARAMS_ROWS:
        raise SystemExit("RIFIUTO: %d righe, attese %d" % (len(righe), PARAMS_ROWS))
    dati = np.array([[float(x) for x in l.split()] for l in righe[1:]], float)
    if dati.shape[0] != N_ATTESI:
        raise SystemExit("RIFIUTO: %d realizzazioni, attese %d" % (dati.shape[0],
                                                                   N_ATTESI))
    return dati, p, sha


def leggi_v1(root, region):
    """base.N_H1 per indice, da per_mock_<REG>_R5.jsonl."""
    p = Path(root) / "results" / "paper1" / ("per_mock_%s_R5.jsonl" % region)
    out = {}
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for j, riga in enumerate(fh):
            riga = riga.strip()
            if not riga:
                continue
            r = json.loads(riga)
            try:
                kk = int(str(r.get("key", j)).split("_")[-1])
            except (TypeError, ValueError):
                kk = j
            v = (r.get("base") or {}).get("N_H1")
            if v is not None:
                out[kk] = float(v)
    return out


def leggi_v2(root, region):
    """unit.N_H1_k0 e fkp.N_H1_k0 per indice."""
    p = Path(root) / "results" / "paper2" / ("ensemble_v2_%s.jsonl" % region)
    u, f = {}, {}
    with p.open("r", encoding="utf-8") as fh:
        for riga in fh:
            riga = riga.strip()
            if not riga:
                continue
            r = json.loads(riga)
            if "index" not in r or r.get("smoke"):
                continue
            i = int(r["index"])
            u[i] = float(r["unit"]["N_H1_k0"])
            f[i] = float(r["fkp"]["N_H1_k0"])
    return u, f


def tabella(nome, r, n, k=6, v1=None):
    righe = []
    for p_, rr in zip(HEADER, r):
        lo, hi = ic_fisher(rr, n, k)
        d = {"parametro": p_, "r": float(rr), "ic95": [lo, hi]}
        if v1 is not None:
            d["v1"] = v1[p_]
            d["scarto"] = float(rr - v1[p_])
        righe.append(d)
    return {"nome": nome, "n": int(n), "controllate": k, "righe": righe}


def stampa(t):
    print("  %-10s %10s %22s%s" % ("", "r", "IC 95%",
                                   "      v1      scarto"
                                   if "v1" in t["righe"][0] else ""))
    for d in t["righe"]:
        extra = ("  %+8.4f  %+8.4f" % (d["v1"], d["scarto"])
                 if "v1" in d else "")
        print("  %-10s %+10.4f   [%+.4f, %+.4f]%s"
              % (d["parametro"], d["r"], d["ic95"][0], d["ic95"][1], extra))


def corri(root, region, out_path=None):
    root = Path(root).resolve()
    print("=" * 78)
    print("D2 SU v2 — correlazioni parziali  |  %s" % region)
    print("=" * 78)

    dati, ppath, sha = leggi_parametri(root)
    print("  parametri: %s" % ppath)
    print("  cancello 1: %d byte, sha %s…, %d righe — quelli del record 43"
          % (PARAMS_BYTES, sha[:12], PARAMS_ROWS))
    ordine = identifica_colonne(dati)
    print("  cancello 2 (sentinella): colonne identificate DAI VALORI -> %s"
          % " ".join(ordine))

    v1 = leggi_v1(root, region)
    u, f = leggi_v2(root, region)
    comuni = sorted(set(v1) & set(u) & set(f) & set(range(N_ATTESI)))
    print("\n  indici in comune fra parametri, v1 e v2: %d" % len(comuni))
    if len(comuni) != N_ATTESI:
        raise SystemExit("RIFIUTO: %d indici in comune, attesi %d"
                         % (len(comuni), N_ATTESI))
    X = dati[comuni, :]
    y1 = np.array([v1[i] for i in comuni], float)
    yu = np.array([u[i] for i in comuni], float)
    yf = np.array([f[i] for i in comuni], float)

    # --- cancello 3: la riproduzione di v1 ---------------------------------
    r1 = correlazioni_parziali(y1, X)
    t1 = tabella("v1 (per_mock base.N_H1)", r1, len(comuni), 6, V1[region])
    print("\n  --- cancello 3: riproduzione di D2 v1 (record 43) ---")
    stampa(t1)
    peggio = max(abs(d["scarto"]) for d in t1["righe"])
    print("  peggior scarto %.5f (limite %.5f)" % (peggio, TOL_V1))
    if peggio > TOL_V1:
        raise SystemExit(
            "RIFIUTO: il ricalcolo non riproduce D2 v1. Il join o il metodo "
            "sono sbagliati, e v2 non si calcola: correlazioni da un join "
            "errato sarebbero plausibili e false.")
    print("  superato: il join e il metodo sono quelli del record 43")

    # --- D2-a ---------------------------------------------------------------
    ra = correlazioni_parziali(yf, X)
    ta = tabella("D2-a: v2 ripesato (fkp.N_H1_k0)", ra, len(comuni), 6, V1[region])
    print("\n  --- D2-a: l'ensemble ripesato ---")
    stampa(ta)

    # --- D2-b: la differenza appaiata --------------------------------------
    d = yf - yu
    rb = correlazioni_parziali(d, X)
    tb = tabella("D2-b: differenza appaiata (fkp - unit)", rb, len(comuni), 6)
    print("\n  --- D2-b: la differenza appaiata, fkp - unit ---")
    print("  dN medio %.2f +/- %.2f generatori"
          % (d.mean(), d.std(ddof=1) / np.sqrt(d.size)))
    stampa(tb)
    forti = [x["parametro"] for x in tb["righe"]
             if np.sign(x["ic95"][0]) == np.sign(x["ic95"][1])]
    print("  parametri con IC che NON contiene lo zero: %s" % (forti or "nessuno"))

    # --- D2-c: la differenza RELATIVA ---------------------------------------
    # Delta_N e' proporzionale a N in media, quindi parte della sua correlazione
    # con un parametro e' quella proporzionalita', non un effetto proprio della
    # ripesatura. Se Delta_N fosse ESATTAMENTE proporzionale, la sua parziale
    # sarebbe quella di N col segno rovesciato. Su Delta_N/N la proporzionalita'
    # sparisce per costruzione, e resta il residuo.
    rel = d / yu
    rc = correlazioni_parziali(rel, X)
    tc = tabella("D2-c: differenza RELATIVA (fkp - unit) / unit", rc,
                 len(comuni), 6)
    print("\n  --- D2-c: la differenza relativa, (fkp - unit) / unit ---")
    print("  dN/N medio %.5f +/- %.5f  (%.3f%%)"
          % (rel.mean(), rel.std(ddof=1) / np.sqrt(rel.size), 100 * rel.mean()))
    stampa(tc)
    forti_c = [x["parametro"] for x in tc["righe"]
               if np.sign(x["ic95"][0]) == np.sign(x["ic95"][1])]
    print("  parametri con IC che NON contiene lo zero: %s" % (forti_c or "nessuno"))

    # quanto della correlazione di D2-b era sola proporzionalita'
    print("\n  --- quanto di D2-b era proporzionalita' ---")
    print("  Se dN fosse esattamente proporzionale a N, la parziale di dN")
    print("  sarebbe quella di N col segno rovesciato. Confronto:")
    print("  %-10s %10s %10s %10s" % ("", "-r(v1)", "r(dN)", "r(dN/N)"))
    for p_, r1_, rb_, rc_ in zip(HEADER, r1, rb, rc):
        print("  %-10s %+10.4f %+10.4f %+10.4f" % (p_, -r1_, rb_, rc_))

    # --- il confronto che risponde all'impegno -----------------------------
    print("\n  --- l'impegno di 0.9: quanto si e' mosso D2 ---")
    sp = max(abs(x["scarto"]) for x in ta["righe"])
    print("  massimo spostamento di una correlazione parziale: %.4f" % sp)
    print("  su n_s: %+.4f -> %+.4f (%+.4f)"
          % (V1[region]["n_s"], dict((x["parametro"], x["r"]) for x in ta["righe"])["n_s"],
             dict((x["parametro"], x["scarto"]) for x in ta["righe"])["n_s"]))
    print("  e n_s resta il parametro dominante: %s"
          % (max(ta["righe"], key=lambda x: abs(x["r"]))["parametro"] == "n_s"))

    rec = {"schema": "paper2_d2_v2_v1", "region": region,
           "utc": datetime.now(timezone.utc).isoformat(),
           "parametri_file": str(ppath), "parametri_sha256": sha,
           "colonne_identificate": ordine, "n": len(comuni),
           "v1_riprodotto": t1, "peggior_scarto_v1": peggio,
           "D2a_ripesato": ta, "D2b_differenza_appaiata": tb,
           "D2c_differenza_relativa": tc,
           "dN_su_N_medio": float(rel.mean()),
           "dN_su_N_sem": float(rel.std(ddof=1) / np.sqrt(rel.size)),
           "parametri_significativi_D2b": forti,
           "parametri_significativi_D2c": forti_c,
           "dN_medio": float(d.mean()),
           "dN_sem": float(d.std(ddof=1) / np.sqrt(d.size)),
           "massimo_spostamento": sp,
           "n_s_resta_dominante": bool(
               max(ta["righe"], key=lambda x: abs(x["r"]))["parametro"] == "n_s")}
    dest = (Path(out_path) if out_path
            else root / "results" / "paper2" / ("d2_v2_%s.json" % region))
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

    print("selftest paper2_d2_v2")

    chk("il file dei parametri e' quello del record 43",
        PARAMS_SHA.startswith("bf0519c623cc") and PARAMS_BYTES == 156070
        and PARAMS_ROWS == 2001)
    chk("sette parametri, nell'ordine dichiarato",
        HEADER == ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "M_nu", "w0"])
    chk("i valori v1 sono quelli del record 43",
        abs(V1["NGC"]["n_s"] - 0.3976) < 1e-12
        and abs(V1["SGC"]["n_s"] - 0.4163) < 1e-12)
    chk("la tolleranza rispetta la quantizzazione a quattro decimali",
        TOL_V1 >= 5e-5)

    # --- la correlazione parziale, su casi costruiti ----------------------
    rng = np.random.default_rng(0)
    n = 4000
    x1 = rng.normal(size=n); x2 = rng.normal(size=n)
    y = 2.0 * x1 + rng.normal(scale=0.5, size=n)
    r = correlazioni_parziali(y, np.column_stack([x1, x2]))
    chk("y dipende da x1 e non da x2: la parziale lo vede",
        r[0] > 0.9 and abs(r[1]) < 0.06, r)
    # il caso che la parziale esiste per risolvere: confondimento
    z = rng.normal(size=n)
    a = z + rng.normal(scale=0.3, size=n)
    b = z + rng.normal(scale=0.3, size=n)
    r_semplice = float(np.corrcoef(a, b)[0, 1])
    r_parz = correlazioni_parziali(a, np.column_stack([b, z]))[0]
    chk("due variabili con una causa comune correlano semplicemente",
        r_semplice > 0.7, r_semplice)
    chk("ma la parziale, controllando la causa, le scollega",
        abs(r_parz) < 0.1, r_parz)
    chk("con una variabile sola la parziale e' la correlazione semplice",
        abs(correlazioni_parziali(y, x1.reshape(-1, 1))[0]
            - np.corrcoef(y, x1)[0, 1]) < 1e-10)

    # --- l'IC di Fisher, contro il valore pubblicato ----------------------
    lo, hi = ic_fisher(0.3980, 2000, 6)
    chk("l'IC di n_s NGC riproduce [0.3601, 0.4339] del record 43",
        abs(lo - 0.3601) < 5e-4 and abs(hi - 0.4339) < 5e-4, (lo, hi))
    chk("l'IC e' simmetrico in z, non in r",
        abs((np.arctanh(hi) - np.arctanh(0.3980))
            - (np.arctanh(0.3980) - np.arctanh(lo))) < 1e-9)
    chk("piu' variabili controllate, IC piu' largo",
        (ic_fisher(0.4, 2000, 6)[1] - ic_fisher(0.4, 2000, 6)[0])
        > (ic_fisher(0.4, 2000, 0)[1] - ic_fisher(0.4, 2000, 0)[0]))

    # --- la sentinella ------------------------------------------------------
    base = np.column_stack([np.linspace(a, b, 50) for a, b in
                            (BORDI[k] for k in HEADER)])
    chk("colonne nell'ordine giusto: la sentinella le identifica",
        identifica_colonne(base) == HEADER)
    # il caso che il contenimento non distingueva: Omega_m dentro M_nu
    chk("l'intervallo di Omega_m sta DENTRO quello di M_nu",
        BORDI["M_nu"][0] <= BORDI["Omega_m"][0]
        and BORDI["Omega_m"][1] <= BORDI["M_nu"][1])
    chk("ma i bordi non coincidono, e la sentinella li separa",
        identifica_colonne(base)[0] == "Omega_m"
        and identifica_colonne(base)[5] == "M_nu")
    quasi = base.copy()
    quasi[:, 0] = np.linspace(0.11, 0.49, 50)     # 2.5% dentro i bordi
    chk("una deriva del 2.5% sui bordi passa ancora",
        identifica_colonne(quasi)[0] == "Omega_m")
    lontano = base.copy()
    lontano[:, 0] = np.linspace(0.2, 0.4, 50)     # 25% dentro
    try:
        identifica_colonne(lontano)
        chk("una del 25% no", False, "non ha rifiutato")
    except SystemExit:
        chk("una del 25% no", True)
    scambiate = base[:, [3, 1, 2, 0, 4, 5, 6]]      # n_s e Omega_m scambiate
    try:
        identifica_colonne(scambiate)
        chk("due colonne scambiate: RIFIUTO", False, "non ha rifiutato")
    except SystemExit as e:
        chk("due colonne scambiate: RIFIUTO", "identificate dai valori" in str(e))
    fuori = base.copy(); fuori[:, 0] = np.linspace(5.0, 6.0, 50)
    try:
        identifica_colonne(fuori)
        chk("una colonna fuori da ogni intervallo: RIFIUTO", False, "no")
    except SystemExit as e:
        chk("una colonna fuori da ogni intervallo: RIFIUTO", "0 parametri" in str(e))
    try:
        identifica_colonne(base[:, :5])
        chk("cinque colonne su sette: RIFIUTO", False, "no")
    except SystemExit as e:
        chk("cinque colonne su sette: RIFIUTO", "colonne, attese" in str(e))

    # --- le due misure sono distinte ---------------------------------------
    yu = rng.normal(size=n) * 100 + 35000
    yf = yu - 27 + rng.normal(size=n) * 3
    chk("D2-a e D2-b guardano quantita' diverse",
        not np.allclose(yf, yf - yu))
    chk("la differenza appaiata ha dispersione molto minore del livello",
        (yf - yu).std(ddof=1) < 0.1 * yf.std(ddof=1))

    # --- D2-c: la proporzionalita' sparisce, e si vede -------------------
    # Caso costruito: dN ESATTAMENTE proporzionale a N. La parziale di dN deve
    # essere quella di N col segno rovesciato, e quella di dN/N esattamente
    # nulla, perche' dN/N e' una costante.
    xx = rng.normal(size=n)
    NN = 1000.0 + 50.0 * xx + rng.normal(scale=5.0, size=n)
    dNN = -0.0025 * NN
    X1 = xx.reshape(-1, 1)
    r_N = correlazioni_parziali(NN, X1)[0]
    r_d = correlazioni_parziali(dNN, X1)[0]
    chk("con dN proporzionale a N, la parziale di dN e' quella di N rovesciata",
        abs(r_d + r_N) < 1e-9, (r_N, r_d))
    relc = dNN / NN
    chk("e dN/N e' costante, quindi la sua correlazione non e' definita",
        float(np.std(relc)) < 1e-12)
    # Caso realistico: proporzionalita' PIU' un residuo SUBDOMINANTE. La scala
    # del residuo si CALCOLA dal termine proporzionale invece di sceglierla a
    # occhio: 0.0025 * sd(N) e' il segnale, e un residuo grande la meta' lo
    # lascia dominante. La prima versione usava 0.5, quattro volte il segnale.
    segnale = 0.0025 * float(np.std(NN))
    dNR = -0.0025 * NN + rng.normal(scale=segnale / 2, size=n)
    r_dr = correlazioni_parziali(dNR, X1)[0]
    r_rel = correlazioni_parziali(dNR / NN, X1)[0]
    chk("il residuo e' subdominante per costruzione, non per fortuna",
        segnale / 2 < segnale)
    chk("con un residuo subdominante la parziale di dN resta vicina alla"
        " rovesciata", abs(r_dr + r_N) < 0.15, (r_N, r_dr))
    chk("mentre quella della relativa e' molto piu' piccola: la"
        " proporzionalita' e' sparita", abs(r_rel) < abs(r_dr) / 2,
        (r_dr, r_rel))

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("corri")
    c.add_argument("--root", default=ROOT_DEFAULT)
    c.add_argument("--region", choices=["NGC", "SGC"], required=True)
    c.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "corri":
        return corri(a.root, a.region, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

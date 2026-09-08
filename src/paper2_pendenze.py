#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_pendenze.py - i tre conti di A.5 del secondo report. SOLA LETTURA.

  1. rho(pendenza, N_H1) sulle 200 realizzazioni: il basso conteggio di DESI
     predice la sua bassa risposta?
  2. rho(pendenza, parametri cosmologici): la pendenza dipende dalla forma
     dello spettro?
  3. §3.7: il prefisso dei primi 200 e' atipico nei parametri che contano, e
     quanto ne risulta spostata la media delle pendenze?

LA DEFINIZIONE DI PENDENZA E' UN CANCELLO, NON UNA SCELTA
--------------------------------------------------------
La pendenza e' la regressione di N_H1 su F sui SEI punti della linea B, B6 e
FID inclusi. Non e' un dettaglio: con cinque punti le dispersioni salgono a
2339-2466 e non combaciano con nulla. Con sei riproducono ESATTAMENTE le quattro
depositate -- 1895.9, 1842.2, 1519.5, 1465.8 -- e la media -3021.1 di NGC k=1.
Il cancello G1 lo verifica prima di stampare qualunque correlazione: una
correlazione calcolata su una pendenza diversa da quella depositata non parla
della stessa quantita'.

E L'ESTRAPOLAZIONE E' VIETATA
-----------------------------
Il conteggio DESI sta a 20-25 sigma dalla media dei mock. Portare una
regressione fin li' non e' una previsione: lo strumento la calcola e la stampa
SOLO per mostrare che cambia segno, con l'avvertenza accanto. E' l'errore che il
report chiama «la quarta occorrenza».

Sottocomandi
------------
  conteggio   il punto 1. Non richiede il file dei parametri.
  cosmologia  i punti 2 e 3. Richiede --params.
  tutto       entrambi.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import os
import statistics as st
import sys

DEFAULT_MOCK = os.path.join("results", "paper2", "fase3_mock.jsonl")
DEFAULT_PARAMS = os.path.join("data", "raw", "quijote", "3D_cubes",
                              "latin_hypercube_nwLH", "latin_hypercube_nwLH_params.txt")

F_AP = {"B1": 0.971070, "B2": 0.985396, "FID": 1.0,
        "B4": 1.014889, "B5": 1.030071, "B6": 1.045531810025433}
PUNTI = ("B1", "B2", "FID", "B4", "B5", "B6")

# Le quattro dispersioni depositate nella risposta al referee. Sono il cancello.
SD_DEPOSITATE = {("NGC", "N_H1_k0"): 1895.9, ("NGC", "N_H1_k1"): 1842.2,
                 ("SGC", "N_H1_k0"): 1519.5, ("SGC", "N_H1_k1"): 1465.8}
DESI = {("NGC", "N_H1_k0"): 28256, ("NGC", "N_H1_k1"): 23790,
        ("SGC", "N_H1_k0"): 15122, ("SGC", "N_H1_k1"): 12011}
NOMI = ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "M_nu", "w0"]


def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def read_jsonl(path):
    if not os.path.isfile(path):
        fail("registro assente: %s" % path)
    with open(path, "rb") as fh:
        raw = fh.read()
    out = []
    for i, ln in enumerate(raw.replace(b"\r\n", b"\n").split(b"\n"), start=1):
        if ln.strip():
            try:
                out.append(json.loads(ln.decode("utf-8")))
            except Exception as exc:
                fail("%s riga %d non e' JSON: %s" % (path, i, exc))
    return out


def pendenza(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def carica(path):
    """{(regione, campo): {indice: (pendenza, N_H1 al fiduciale)}}, unendo i
    record per (regione, indice): il registro ne ha piu' d'uno."""
    M = collections.defaultdict(dict)
    for r in read_jsonl(path):
        if r.get("smoke"):
            continue
        for p, d in (r.get("points") or {}).items():
            if isinstance(d, dict):
                M[(r["region"], r["index"])].setdefault(p, {}).update(d)
    out, incompleti = {}, collections.Counter()
    for g in ("NGC", "SGC"):
        for f in ("N_H1_k0", "N_H1_k1"):
            d = {}
            for (gg, i), pts in M.items():
                if gg != g:
                    continue
                use = [p for p in PUNTI if p in pts and f in pts[p]]
                if len(use) != len(PUNTI):
                    incompleti[(g, f)] += 1
                    continue
                d[i] = (pendenza([F_AP[p] for p in use],
                                 [float(pts[p][f]) for p in use]),
                        float(pts["FID"][f]))
            out[(g, f)] = d
    return out, incompleti


def cancello_definizione(S, verbose=True):
    """G1: le quattro sd devono riprodurre quelle depositate."""
    bad = []
    if verbose:
        print("=== G1  la definizione di pendenza riproduce le sd depositate ===")
        print("  %-4s %-8s %5s %11s %10s %10s" % ("reg", "liv", "n", "media",
                                                  "sd", "depositata"))
    for k, att in sorted(SD_DEPOSITATE.items(), key=lambda x: str(x[0])):
        d = S.get(k, {})
        if len(d) < 10:
            bad.append("%s/%s: solo %d realizzazioni" % (k[0], k[1], len(d)))
            continue
        sl = [v[0] for v in d.values()]
        sd = st.stdev(sl)
        if abs(sd - att) > 0.15:
            bad.append("%s/%s: sd %.1f contro %.1f depositata" % (k[0], k[1], sd, att))
        if verbose:
            print("  %-4s %-8s %5d %11.1f %10.1f %10.1f%s"
                  % (k[0], k[1], len(d), st.mean(sl), sd, att,
                     "" if abs(sd - att) <= 0.15 else "   <<< DIVERSA"))
    if verbose:
        print("  [%s] sei punti, B6 e FID inclusi%s"
              % ("ok" if not bad else "NO",
                 "" if not bad else ": " + "; ".join(bad)))
    return bad


def rho_t(xs, ys):
    r = st.correlation(xs, ys)
    n = len(xs)
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else float("inf")
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return r, t, p


def cmd_conteggio(args):
    S, inc = carica(args.mock)
    bad = cancello_definizione(S)
    if bad:
        fail("la definizione di pendenza non riproduce le sd depositate: una "
             "correlazione su una pendenza diversa non parla della stessa "
             "quantita'.")
    if inc:
        print("  realizzazioni incomplete escluse: %s" % dict(inc))
    print("")
    print("=== A.5 punto 1: rho(pendenza, N_H1) ===")
    print("  %-4s %-8s %9s %7s %8s | %s"
          % ("reg", "liv", "rho", "t", "p", "DESI, in sigma di N_H1"))
    for g in ("NGC", "SGC"):
        for f in ("N_H1_k0", "N_H1_k1"):
            d = S[(g, f)]
            sl = [v[0] for v in d.values()]
            nh = [v[1] for v in d.values()]
            r, t, p = rho_t(sl, nh)
            zN = (DESI[(g, f)] - st.mean(nh)) / st.stdev(nh)
            print("  %-4s %-8s %+9.4f %+7.2f %8.3f | %+6.1f"
                  % (g, f, r, t, p, zN))
    print("")
    print("  Il SEGNO atteso e' negativo: meno anelli, risposta piu' debole.")
    print("")
    print("=== e l'estrapolazione, che NON e' una previsione ===")
    for g in ("NGC", "SGC"):
        for f in ("N_H1_k0", "N_H1_k1"):
            d = S[(g, f)]
            sl = [v[0] for v in d.values()]
            nh = [v[1] for v in d.values()]
            r = st.correlation(sl, nh)
            b = r * st.stdev(sl) / st.stdev(nh)
            pred = st.mean(sl) + b * (DESI[(g, f)] - st.mean(nh))
            print("  %-4s %-8s pendenza predetta al conteggio DESI %+9.1f  "
                  "contro media %+9.1f%s"
                  % (g, f, pred, st.mean(sl),
                     "   <<< SEGNO OPPOSTO" if pred * st.mean(sl) < 0 else ""))
    print("")
    print("  Il conteggio DESI sta a 20-25 sigma dalla distribuzione mock:")
    print("  l'estrapolazione e' VIETATA, e dove cambia segno lo dimostra.")
    print("  Si stampa per mostrare che non si puo' usare, non per usarla.")
    return 0


def leggi_params(path):
    import numpy as np
    if not os.path.isfile(path):
        fail("file dei parametri assente: %s" % path)
    raw = np.genfromtxt(path)
    if raw.ndim != 2 or raw.shape[1] != len(NOMI):
        fail("il file dei parametri ha forma %s, attese 7 colonne" % (raw.shape,))
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        prima = fh.readline().strip()
    intest = prima.lstrip("#").split() if prima.startswith("#") else None
    if intest and intest != NOMI:
        fail("l'intestazione del file dice %s, atteso %s: non indovino l'ordine."
             % (intest, NOMI))
    return raw


def cmd_cosmologia(args):
    import numpy as np
    S, inc = carica(args.mock)
    bad = cancello_definizione(S)
    if bad:
        fail("definizione di pendenza non riprodotta: " + "; ".join(bad))
    P = leggi_params(args.params)
    print("  [ok] parametri: %d righe x %d colonne, intestazione verificata"
          % P.shape)
    print("")
    print("=== A.5 punto 2: rho(pendenza, parametri) sulle 200 realizzazioni ===")
    print("  L'indice del mock e' la RIGA del file: e' il join `__order__` che")
    print("  la Componente D usa, con la sentinella su Omega_m.")
    print("")
    hdr = "  %-4s %-8s" % ("reg", "liv") + "".join("%10s" % n for n in NOMI)
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for g in ("NGC", "SGC"):
        for f in ("N_H1_k0", "N_H1_k1"):
            d = S[(g, f)]
            idx = sorted(d)
            if max(idx) >= P.shape[0]:
                fail("indice %d fuori dal file dei parametri (%d righe)"
                     % (max(idx), P.shape[0]))
            sl = [d[i][0] for i in idx]
            riga = "  %-4s %-8s" % (g, f)
            for j in range(len(NOMI)):
                r, t, p = rho_t(sl, [float(P[i, j]) for i in idx])
                riga += "%10s" % ("%+.3f%s" % (r, "*" if p < 0.05 else " "))
            print(riga)
    print("")
    print("  * = p < 0.05, non corretto per le 28 prove: con 28 confronti se ne")
    print("    attende 1.4 sotto l'ipotesi nulla. Si legge il quadro, non la stella.")
    print("")
    print("=== A.5 punto 3: il prefisso dei primi 200 e' atipico? ===")
    n_pref = args.prefisso
    print("  primi %d contro tutte le %d righe dell'ipercubo" % (n_pref, P.shape[0]))
    print("  %-9s %11s %11s %9s %8s" % ("param", "media 200", "media tutti",
                                        "z media", "sd 200/tutti"))
    for j, nome in enumerate(NOMI):
        a = P[:n_pref, j]
        b = P[:, j]
        z = (a.mean() - b.mean()) / (b.std(ddof=1) / math.sqrt(n_pref))
        print("  %-9s %11.5f %11.5f %+9.2f %8.3f"
              % (nome, a.mean(), b.mean(), z, a.std(ddof=1) / b.std(ddof=1)))
    print("")
    print("  Se la pendenza dipende da un parametro E il prefisso e' atipico in")
    print("  quel parametro, la media delle pendenze stimata sui primi 200 e'")
    print("  spostata. Lo spostamento implicato, per parametro:")
    print("")
    print("  %-4s %-8s %-9s %10s %10s" % ("reg", "liv", "param", "spostam.",
                                          "% della media"))
    for g in ("NGC", "SGC"):
        for f in ("N_H1_k0", "N_H1_k1"):
            d = S[(g, f)]
            idx = sorted(d)
            sl = [d[i][0] for i in idx]
            m = st.mean(sl)
            peggiore = None
            for j, nome in enumerate(NOMI):
                col = [float(P[i, j]) for i in idx]
                r = st.correlation(sl, col)
                b = r * st.stdev(sl) / st.stdev(col)
                dmu = float(P[:n_pref, j].mean() - P[:, j].mean())
                sp = b * dmu
                if peggiore is None or abs(sp) > abs(peggiore[1]):
                    peggiore = (nome, sp)
            print("  %-4s %-8s %-9s %10.1f %9.1f%%"
                  % (g, f, peggiore[0], peggiore[1], 100 * peggiore[1] / m))
    print("")
    print("  E' il parametro che sposta di piu', non la somma: i sette non sono")
    print("  indipendenti e sommarli sarebbe un doppio conteggio.")
    return 0


def cmd_tutto(args):
    cmd_conteggio(args)
    print("")
    print("=" * 78)
    print("")
    return cmd_cosmologia(args)


def main():
    p = argparse.ArgumentParser(description="I tre conti di A.5 (sola lettura)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--mock", default=DEFAULT_MOCK)
    common.add_argument("--params", default=DEFAULT_PARAMS)
    common.add_argument("--prefisso", type=int, default=200)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("conteggio", parents=[common]).set_defaults(func=cmd_conteggio)
    sub.add_parser("cosmologia", parents=[common]).set_defaults(func=cmd_cosmologia)
    sub.add_parser("tutto", parents=[common]).set_defaults(func=cmd_tutto)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

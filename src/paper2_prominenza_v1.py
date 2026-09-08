#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_prominenza_v1.py — la soglia mancante di 4.3b.

Calcola la prominenza del picco di erosione

    P = D(k=1) - 1/2 [ D(k=0) + D(k=2) ],   D(k) = (<N>_mock(k) - N_DESI(k)) / <N>_mock(k)

e la sua incertezza APPAIATA sulle realizzazioni. Il lato DESI e' deterministico, quindi
l'incertezza viene solo dal lato mock; l'appaiamento conta perche' i livelli di erosione
condividono l'84.6% del footprint.

Riporta tre sigma, non una:
  - appaiata     : sd(p_i)/sqrt(n) sulla quantita' per realizzazione. E' quella che decide.
  - jackknife    : su P definita sulle medie d'ensemble. Deve concordare con la precedente.
  - non appaiata : propagata come se i tre livelli fossero indipendenti. E' il numero
                   sbagliato, riportato per far vedere di quanto sbaglia.

Uso:
    python paper2_prominenza_v1.py selftest
    python paper2_prominenza_v1.py scopri --root D:\\projects\\cauchy
    python paper2_prominenza_v1.py calcola --file results\\paper1\\per_mock_NGC_R5.jsonl ^
        --k0 base.N_H1_k0 --k1 base.N_H1_k1 --k2 base.N_H1_k2 ^
        --desi-k0 28256 --desi-k1 ... --desi-k2 ... --etichetta NGC --out logs\\prominenza.jsonl
"""

import argparse
import json
import math
import os
import statistics as st
import sys
import tempfile

SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", "node_modules", ".venv", "venv"}


class Rifiuto(Exception):
    pass


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(flatten(v, key))
            elif not isinstance(v, list):
                out[key] = v
    return out


def leggi_colonne(path, chiavi):
    """Estrae le colonne richieste. Rifiuta se un record ne ha alcune e non altre."""
    colonne = {k: [] for k in chiavi}
    n_record = 0
    incompleti = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                raise Rifiuto(f"riga {i}: JSON malformato")
            piatto = flatten(rec)
            presenti = [k for k in chiavi if k in piatto and piatto[k] is not None]
            if not presenti:
                continue
            n_record += 1
            if len(presenti) != len(chiavi):
                incompleti.append({"riga": i, "mancanti": [k for k in chiavi if k not in presenti]})
                continue
            for k in chiavi:
                colonne[k].append(float(piatto[k]))
    if incompleti:
        raise Rifiuto(f"{len(incompleti)} record su {n_record} non hanno tutti e tre i livelli; "
                      f"primo: riga {incompleti[0]['riga']}, mancano {incompleti[0]['mancanti']}")
    n = len(colonne[chiavi[0]])
    if n < 3:
        raise Rifiuto(f"servono almeno 3 realizzazioni, trovate {n}")
    return colonne, n


def deficit(n_mock, n_desi):
    return (n_mock - n_desi) / n_mock


def prominenza(N0, N1, N2, d0, d1, d2):
    """Restituisce il dizionario completo dei risultati. Tutto in punti percentuali."""
    n = len(N0)

    def P_ens(idx):
        m0 = sum(N0[i] for i in idx) / len(idx)
        m1 = sum(N1[i] for i in idx) / len(idx)
        m2 = sum(N2[i] for i in idx) / len(idx)
        D0, D1, D2 = deficit(m0, d0), deficit(m1, d1), deficit(m2, d2)
        return 100.0 * (D1 - 0.5 * (D0 + D2)), (100.0 * D0, 100.0 * D1, 100.0 * D2)

    tutti = list(range(n))
    P, (D0, D1, D2) = P_ens(tutti)

    # per realizzazione
    p = [100.0 * (deficit(N1[i], d1) - 0.5 * (deficit(N0[i], d0) + deficit(N2[i], d2)))
         for i in range(n)]
    sem_appaiata = st.stdev(p) / math.sqrt(n)

    # jackknife sulla definizione d'ensemble
    jk = [P_ens([j for j in tutti if j != i])[0] for i in range(n)]
    media_jk = sum(jk) / n
    sem_jk = math.sqrt((n - 1) / n * sum((v - media_jk) ** 2 for v in jk))

    # non appaiata: come se i tre livelli fossero indipendenti
    d_k = []
    for N, dd in ((N0, d0), (N1, d1), (N2, d2)):
        vals = [100.0 * deficit(x, dd) for x in N]
        d_k.append(st.stdev(vals) / math.sqrt(n))
    sem_non_appaiata = math.sqrt(d_k[1] ** 2 + 0.25 * (d_k[0] ** 2 + d_k[2] ** 2))

    def corr(a, b):
        return st.correlation(a, b) if hasattr(st, "correlation") else float("nan")

    # Termine di curvatura della DEFINIZIONE: D = 1 - N_DESI/N e' convessa in N, quindi una
    # rampa perfettamente lineare fra k0 e k2 produce gia' una prominenza non nulla. La si
    # isola sostituendo N1 con la media dei due estremi, e la si sottrae.
    N1_lin = [0.5 * (N0[i] + N2[i]) for i in range(n)]
    m0 = sum(N0) / n
    m1 = sum(N1) / n
    m1l = sum(N1_lin) / n
    m2 = sum(N2) / n
    P_curv = 100.0 * (deficit(m1l, d1) - 0.5 * (deficit(m0, d0) + deficit(m2, d2)))

    # P corretta per realizzazione, e la sua SEM appaiata: e' la parte del picco che sta
    # sul lato MOCK, cioe' l'unica su cui un cambio di pesatura puo' agire.
    p_corr = [100.0 * (deficit(N1[i], d1) - deficit(N1_lin[i], d1)) for i in range(n)]
    sem_corretta = st.stdev(p_corr) / math.sqrt(n)
    P_corr_ens = P - P_curv

    return {
        "n": n,
        "D_k0_pp": D0, "D_k1_pp": D1, "D_k2_pp": D2,
        "P_pp": P,
        "P_curvatura_pp": P_curv,
        "P_corretta_pp": P_corr_ens,
        "P_corretta_per_realizzazione_pp": sum(p_corr) / n,
        "sem_corretta_pp": sem_corretta,
        "mock_dev_k1": m1 - m1l,
        "desi_dev_k1": d1 - 0.5 * (d0 + d2),
        "soglia_successo_corretta_pp": P_corr_ens / 3.0,
        "soglia_fallimento_corretta_pp": 2.0 * P_corr_ens / 3.0,
        "separazione_zone_corretta_sigma": (P_corr_ens / 3.0) / sem_corretta if sem_corretta else float("inf"),
        "sem_appaiata_pp": sem_appaiata,
        "sem_jackknife_pp": sem_jk,
        "sem_non_appaiata_pp": sem_non_appaiata,
        "guadagno_appaiamento": sem_non_appaiata / sem_appaiata if sem_appaiata else float("inf"),
        "r_k0_k1": corr(N0, N1), "r_k1_k2": corr(N1, N2),
        "soglia_successo_pp": P / 3.0,
        "soglia_fallimento_pp": 2.0 * P / 3.0,
        "separazione_zone_sigma": (P / 3.0) / sem_appaiata if sem_appaiata else float("inf"),
    }


def cmd_calcola(args):
    chiavi = [args.k0, args.k1, args.k2]
    if len(set(chiavi)) != 3:
        print("RIFIUTO: le tre chiavi devono essere distinte")
        return 2
    try:
        col, n = leggi_colonne(args.file, chiavi)
        r = prominenza(col[args.k0], col[args.k1], col[args.k2],
                       args.desi_k0, args.desi_k1, args.desi_k2)
    except Rifiuto as e:
        print(f"RIFIUTO: {e}")
        return 2

    r["etichetta"] = args.etichetta
    r["file"] = os.path.abspath(args.file)
    r["chiavi"] = chiavi
    r["desi"] = [args.desi_k0, args.desi_k1, args.desi_k2]

    print(f"{args.etichetta}  n = {r['n']}")
    print(f"  deficit  k0 {r['D_k0_pp']:7.3f} pp   k1 {r['D_k1_pp']:7.3f} pp   k2 {r['D_k2_pp']:7.3f} pp")
    print(f"  P        {r['P_pp']:+.4f} pp = lato mock {r['P_corretta_pp']:+.4f} + "
          f"residuo a mock lineare {r['P_curvatura_pp']:+.4f}")
    print(f"  scarti   mock(k1) - lineare {r['mock_dev_k1']:+.1f} gen   "
          f"DESI(k1) - lineare {r['desi_dev_k1']:+.1f} gen")
    print(f"  sigma    appaiata {r['sem_appaiata_pp']:.4f}   jackknife {r['sem_jackknife_pp']:.4f}"
          f"   non appaiata {r['sem_non_appaiata_pp']:.4f}  (x{r['guadagno_appaiamento']:.1f})")
    print(f"  correlaz k0-k1 {r['r_k0_k1']:.4f}   k1-k2 {r['r_k1_k2']:.4f}")
    print(f"  soglie   successo < {r['soglia_successo_pp']:.4f} pp   "
          f"fallimento > {r['soglia_fallimento_pp']:.4f} pp")
    print(f"  le due zone distano {r['separazione_zone_sigma']:.1f} sigma", end="  ")
    print("[REGOLA VALIDA]" if r["separazione_zone_sigma"] >= 3.0
          else "[REGOLA NON DECIDE: separazione < 3 sigma, va ridichiarata]")
    scarto = abs(r["sem_appaiata_pp"] - r["sem_jackknife_pp"]) / max(r["sem_appaiata_pp"], 1e-12)
    print(f"  appaiata vs jackknife: scarto relativo {scarto:.3%}", end="  ")
    print("[concordi]" if scarto < 0.05 else "[DISCORDI: le due definizioni di P non coincidono]")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  registro: {os.path.abspath(args.out)}")
    return 0


def cmd_scopri(args):
    import re
    rx = re.compile(r"k[_\-]?[0123](?![0-9])|erosion|erosione|N_H1", re.I)
    trovati = []
    for dirpath, dirnames, filenames in os.walk(os.path.abspath(args.root)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.lower().endswith(".jsonl"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    prima = fh.readline().strip()
                if not prima:
                    continue
                piatto = flatten(json.loads(prima))
            except Exception:
                continue
            chiavi = [k for k in piatto if rx.search(k)]
            if len(chiavi) >= 2:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    n = sum(1 for line in fh if line.strip())
                trovati.append((os.path.relpath(full, args.root), n, chiavi))
    for rel, n, chiavi in sorted(trovati, key=lambda t: -t[1]):
        print(f"{n:6d}  {rel}")
        print(f"        {chiavi}")
    if not trovati:
        print("nessun registro con almeno due chiavi di erosione")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="prominenza_")
    p = os.path.join(base, "ladder.jsonl")

    # Fixture: livelli fortemente correlati per costruzione, piu' un picco a k1.
    # N_i(k) = base_i + offset_k, con base_i che varia molto e offset_k fisso.
    basi = [35000 + 137 * i - 3 * i * i for i in range(40)]
    off = {"k0": 0.0, "k1": 900.0, "k2": 200.0}
    with open(p, "w", encoding="utf-8", newline="") as fh:
        for i, b in enumerate(basi):
            fh.write(json.dumps({"idx": i, "base": {"N_H1_k0": b + off["k0"],
                                                    "N_H1_k1": b + off["k1"],
                                                    "N_H1_k2": b + off["k2"]}}) + "\n")
    chiavi = ["base.N_H1_k0", "base.N_H1_k1", "base.N_H1_k2"]
    col, n = leggi_colonne(p, chiavi)
    ok("1 quaranta realizzazioni lette", n == 40)

    r = prominenza(col[chiavi[0]], col[chiavi[1]], col[chiavi[2]], 28000.0, 28000.0, 28000.0)
    ok("2 P positiva col picco a k1", r["P_pp"] > 0)
    ok("3 appaiata e jackknife concordi entro il 5%",
       abs(r["sem_appaiata_pp"] - r["sem_jackknife_pp"]) / r["sem_appaiata_pp"] < 0.05)
    ok("4 l'appaiamento guadagna almeno un fattore 3", r["guadagno_appaiamento"] > 3.0)
    ok("5 livelli quasi perfettamente correlati", r["r_k0_k1"] > 0.999)

    # Controllo COMPORTAMENTALE: senza picco, P deve andare a zero.
    piatto = {"k0": 0.0, "k1": 100.0, "k2": 200.0}   # rampa lineare: prominenza nulla
    p2 = os.path.join(base, "rampa.jsonl")
    with open(p2, "w", encoding="utf-8", newline="") as fh:
        for i, b in enumerate(basi):
            fh.write(json.dumps({"idx": i, "base": {"N_H1_k0": b + piatto["k0"],
                                                    "N_H1_k1": b + piatto["k1"],
                                                    "N_H1_k2": b + piatto["k2"]}}) + "\n")
    col2, _ = leggi_colonne(p2, chiavi)
    r2 = prominenza(col2[chiavi[0]], col2[chiavi[1]], col2[chiavi[2]], 28000.0, 28000.0, 28000.0)
    ok("6 su una rampa lineare P coincide col termine di curvatura",
       abs(r2["P_corretta_pp"]) < 1e-9 and abs(r2["P_pp"]) > 0)
    ok("7 i due fixture danno numeri diversi", abs(r["P_pp"] - r2["P_pp"]) > 0.1)

    # Il lato DESI conta: cambiarlo deve cambiare P.
    r3 = prominenza(col[chiavi[0]], col[chiavi[1]], col[chiavi[2]], 28000.0, 27000.0, 28000.0)
    ok("8 cambiare N_DESI(k1) cambia P", abs(r3["P_pp"] - r["P_pp"]) > 0.5)
    ok("8b col lato dati costante il residuo a mock lineare e' trascurabile",
       0 < abs(r["P_curvatura_pp"]) < 0.01 * abs(r["P_pp"]))
    # Un lato dati LINEARE nei livelli lascia il residuo trascurabile...
    r_lin = prominenza(col[chiavi[0]], col[chiavi[1]], col[chiavi[2]], 28000.0, 25000.0, 22000.0)
    ok("8c lato dati lineare: residuo ancora trascurabile",
       abs(r_lin["P_curvatura_pp"]) < 0.05 * abs(r_lin["P_pp"])
       and abs(r_lin["desi_dev_k1"]) < 1e-9)
    # ...ma un lato dati che DEVIA dalla propria interpolazione lo rende dominante.
    # E' il caso reale: e' lo scarto di DESI a k=1, non la convessita', a produrlo.
    r_dev = prominenza(col[chiavi[0]], col[chiavi[1]], col[chiavi[2]], 28000.0, 25000.0, 25000.0)
    ok("8c2 lato dati deviante: il residuo diventa dominante",
       r_dev["desi_dev_k1"] < -1000 and abs(r_dev["P_curvatura_pp"]) > 0.5 * abs(r_dev["P_pp"]))
    # La parte lato mock dipende SOLO da d1: cambiare d0 e d2 non la muove.
    r_d02 = prominenza(col[chiavi[0]], col[chiavi[1]], col[chiavi[2]], 30000.0, 25000.0, 20000.0)
    ok("8d la parte lato mock non dipende da d0 ne' da d2",
       abs(r_d02["P_corretta_pp"] - r_lin["P_corretta_pp"]) < 1e-9
       and abs(r_d02["P_pp"] - r_lin["P_pp"]) > 1e-6)
    ok("8e P corretta d'ensemble e per realizzazione concordano",
       abs(r["P_corretta_pp"] - r["P_corretta_per_realizzazione_pp"]) < 0.05 * abs(r["P_corretta_pp"]))

    # Rifiuti
    p3 = os.path.join(base, "incompleto.jsonl")
    with open(p3, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"base": {"N_H1_k0": 1.0, "N_H1_k1": 2.0, "N_H1_k2": 3.0}}) + "\n")
        fh.write(json.dumps({"base": {"N_H1_k0": 1.0, "N_H1_k2": 3.0}}) + "\n")
    try:
        leggi_colonne(p3, chiavi)
        ok("9 rifiuta i record incompleti", False)
    except Rifiuto as e:
        ok("9 rifiuta i record incompleti", "non hanno tutti e tre" in str(e))

    p4 = os.path.join(base, "corto.jsonl")
    with open(p4, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"base": {"N_H1_k0": 1.0, "N_H1_k1": 2.0, "N_H1_k2": 3.0}}) + "\n")
    try:
        leggi_colonne(p4, chiavi)
        ok("10 rifiuta se le realizzazioni sono meno di tre", False)
    except Rifiuto as e:
        ok("10 rifiuta se le realizzazioni sono meno di tre", "almeno 3" in str(e))

    p5 = os.path.join(base, "rotto.jsonl")
    with open(p5, "w", encoding="utf-8", newline="") as fh:
        fh.write('{"base": {"N_H1_k0": 1.0, "N_H1_k1": 2.0, "N_H1_k2": 3.0}}\n')
        fh.write("non-json\n")
    try:
        leggi_colonne(p5, chiavi)
        ok("11 rifiuta il JSON malformato", False)
    except Rifiuto as e:
        ok("11 rifiuta il JSON malformato", "malformato" in str(e))

    # Registro su disco, append-only e senza CRLF
    class A:
        pass
    a = A(); a.file = p; a.k0, a.k1, a.k2 = chiavi
    a.desi_k0 = a.desi_k1 = a.desi_k2 = 28000.0
    a.etichetta = "TEST"; a.out = os.path.join(base, "logs", "prom.jsonl")
    rc = cmd_calcola(a); rc2 = cmd_calcola(a)
    ok("12 calcola: esito 0 due volte", rc == 0 and rc2 == 0)
    with open(a.out, "rb") as fh:
        raw = fh.read()
    ok("13 registro append-only: due righe", raw.decode("utf-8").count("\n") == 2)
    ok("14 registro senza CRLF", b"\r\n" not in raw)

    # La separazione delle zone e' calcolata, non asserita
    ok("15 separazione zone coerente con P e sigma",
       abs(r["separazione_zone_sigma"] - (r["P_pp"] / 3.0) / r["sem_appaiata_pp"]) < 1e-9)

    passati = sum(1 for _, c in controlli if c)
    print()
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print(f"selftest: {passati}/{len(controlli)}")
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_c = sub.add_parser("calcola")
    p_c.add_argument("--file", required=True)
    p_c.add_argument("--k0", required=True, help="chiave piatta di N_H1 a k=0")
    p_c.add_argument("--k1", required=True)
    p_c.add_argument("--k2", required=True)
    p_c.add_argument("--desi-k0", type=float, required=True)
    p_c.add_argument("--desi-k1", type=float, required=True)
    p_c.add_argument("--desi-k2", type=float, required=True)
    p_c.add_argument("--etichetta", default="")
    p_c.add_argument("--out", default=None)
    p_c.set_defaults(func=cmd_calcola)

    p_s = sub.add_parser("scopri")
    p_s.add_argument("--root", required=True)
    p_s.set_defaults(func=cmd_scopri)

    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

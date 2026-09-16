#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_boxcox_v2.py — item 4.2b-5, la passata Box-Cox.

Il record 50 §viii la mette DENTRO la specifica di uscita di 4.2a: «the Box-Cox
pass at eps in {0, 0.25, 0.5, 1.0} on the SAME 50 mocks as v1». Il runner di
4.2a non la fa, quindi 4.2a resta incompleta rispetto alla propria specifica
finche' questa passata non esiste.

LA REGOLA, DAL RECORD 50
------------------------
  s = <N_H1(eps=1) - N_H1(eps=0)> APPAIATA sugli stessi 50 mock: e' la parte
  della quantita' su cui v2 puo' agire. La predizione originale — l'escursione
  del deficit da 20.3% a 17.6% — e' stata ritirata perche' l'84.3% e' lato dati
  e la ripesatura dei mock non lo tocca.
  v1 NGC: s = -183.32 +/- 11.124102898936275 (-16.5 sigma); l'appaiamento
  cancella il 95% della varianza (11.12 contro 48.25, r = 0.958).
  successo  |s^v2| < 45.8 gen  (25% di |s^v1|)
  fallimento |s^v2| > 137.5    (75%)
  se sigma(s^v2) > 15 la regola NON DECIDE, dichiarato prima del risultato.

NIENTE E' RISCRITTO
-------------------
  transform, field_from_delta, beta1_pers1  <- rev1_r14_monotone
  cioe' la trasformazione, la costruzione del campo da un delta grezzo e la
  TDA. `beta1_pers1` usa compute_tda_features(..., masked=True)[4], lo stesso
  del runner di 4.2a: i numeri sono confrontabili per costruzione.

I 50 MOCK SONO I PRIMI 50, E SI EREDITA
---------------------------------------
rev1_r14_monotone.py:527 fa sorted(mock_dir.glob("*.npy"))[:n_mocks]: ordine
alfabetico, quindi delta_0000..delta_0049. Non si sceglie: si eredita, come il
record 50 impone («on the SAME 50 mocks as v1»).

QUATTRO RAMI, PERCHE' s^v1 PER SGC NON ESISTE
----------------------------------------------
  NGC v1  ricalcolato -> DEVE riprodurre -183.32 +/- 11.12. E' il cancello che
          rende affidabile il ramo SGC, dove non c'e' termine di paragone: la
          stessa struttura che ha validato la cache di nu di DESI, dove NGC
          identica bit per bit ha coperto la costruzione di SGC.
  SGC v1  da calcolare: il record 50 quota solo NGC.
  NGC v2  dalla cache dei delta v2.
  SGC v2  idem.

L'ORDINE E' VINCOLANTE PER SGC
------------------------------
La soglia SGC non esiste e va DERIVATA da s^v1 SGC. Fra il suo calcolo e quello
di s^v2 c'e' l'unica finestra in cui una soglia si scriverebbe con il risultato
gia' sul disco. Questo strumento la chiude come fa il verdetto per 4.3b: calcola
i v1, stampa le soglie che ne discendono, e RIFIUTA di calcolare i v2 finche'
non gli vengono ripassate da fuori e non coincidono.

DUE CANCELLI CHE SI PAGANO DA SOLI
----------------------------------
  A eps=0 `transform` da' log(1 + clip(delta, -1+1e-3)), che e' LETTERALMENTE
  la prima riga di P1.build_nu. Quindi:
    1. field_from_delta(delta, mask, 0.0) deve dare lo stesso array di
       P1.build_nu(delta, mask, sigma_px), BIT PER BIT;
    2. sul ramo v2, N_H1 a eps=0 deve riprodurre il fkp.N_H1_k0 gia' scritto in
       ensemble_v2_<REG>.jsonl per quelle realizzazioni. E' piu' forte del
       provenance gate di v1, che verifica una proprieta' del campo: qui si
       confronta un numero gia' depositato.

USO
    python src\\paper2_boxcox_v2.py selftest
    python src\\paper2_boxcox_v2.py passata --region NGC --versione v1
    python src\\paper2_boxcox_v2.py passata --region SGC --versione v1
    python src\\paper2_boxcox_v2.py passata --region NGC --versione v2 --soglia 45.8
    python src\\paper2_boxcox_v2.py passata --region SGC --versione v2 --soglia <derivata>

Uscita: 0 se i cancelli passano, 1 se no, 2 su errore d'uso.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

EPS = (0.0, 0.25, 0.5, 1.0)
N_MOCK = 50
# record 50: v1 NGC. Il ricalcolo deve riprodurli.
S_V1_NGC = -183.32
SEM_V1_NGC = 11.124102898936275
TOL_S_V1 = 3.0                 # generatori, su |s| ~ 183: e' un cancello, non un fit
FRAZ_SUCCESSO = 0.25           # record 50: 45.8 e' il 25% di |s^v1| NGC
FRAZ_FALLIMENTO = 0.75         # 137.5 e' il 75%
SIGMA_MAX_INVALIDA = 15.0      # se sigma(s^v2) la supera, la regola non decide
TOL_SOGLIA = 1e-6
ROOT_DEFAULT = "."


def importa_r14():
    """
    rev1_r14_monotone fa parse_args A LIVELLO DI MODULO: appena lo si importa,
    il suo parser gira sulla riga di comando di CHI importa, non trova --mode e
    uccide il processo. Le funzioni che servono — transform, field_from_delta,
    beta1_pers1 — non usano ARGS, ma l'import va comunque superato.

    Non si modifica quel file: e' di Paper 1, ha gia' girato e i suoi risultati
    sono depositati. Si sostituisce sys.argv per la durata del solo import, con
    argomenti che il suo parser accetta, e lo si rimette subito.
    """
    salvato = sys.argv[:]
    sys.argv = [salvato[0], "--mode", "inspect"]
    try:
        import rev1_r14_monotone as R14
    finally:
        sys.argv = salvato
    return R14


def now():
    return datetime.now(timezone.utc).isoformat()


def percorsi(root, region, versione):
    d = Path(root)
    cache = (d / "data" / "processed" / "paper1_mock_deltas" / region
             if versione == "v1" else
             d / "data" / "processed" / "paper2_mock_deltas_v2" / region)
    return {"cache": cache,
            "ensemble": d / "results" / "paper2" / ("ensemble_v2_%s.jsonl" % region),
            "out": d / "results" / "paper2" / ("boxcox_%s_%s.json" % (versione, region))}


def soglie_da_s(s_v1):
    a = abs(float(s_v1))
    return a * FRAZ_SUCCESSO, a * FRAZ_FALLIMENTO


def esito(s_v2, sigma_v2, succ, fall):
    if sigma_v2 > SIGMA_MAX_INVALIDA:
        return "NON DECIDE (sigma %.1f > %.0f, invalidata)" % (sigma_v2,
                                                               SIGMA_MAX_INVALIDA)
    a = abs(float(s_v2))
    if a < succ:
        return "SUCCESSO"
    if a > fall:
        return "FALLIMENTO"
    return "NON DECIDE"


def leggi_ensemble_k0(path, n):
    """fkp.N_H1_k0 per indice, dal registro dell'ensemble v2."""
    out = {}
    p = Path(path)
    if not p.is_file():
        return out
    with p.open("r", encoding="utf-8") as fh:
        for riga in fh:
            riga = riga.strip()
            if not riga:
                continue
            r = json.loads(riga)
            if "index" in r and r.get("index") < n and not r.get("smoke"):
                v = (r.get("fkp") or {}).get("N_H1_k0")
                if v is not None:
                    out[int(r["index"])] = int(v)
    return out


def passata(root, region, versione, soglia=None, n_mock=N_MOCK):
    # Le validazioni che non costano nulla PRIMA degli import di progetto, che
    # costano secondi e falliscono fuori dalla radice. Stesso difetto gia'
    # corretto nel runner di 4.2a.
    if versione == "v2" and soglia is None:
        raise SystemExit(
            "RIFIUTO: il ramo v2 richiede --soglia, la soglia di successo "
            "derivata da s^v1 e REGISTRATA. Senza, si sceglierebbe la soglia "
            "avendo il risultato sul disco.")
    if versione == "v1" and soglia is not None:
        raise SystemExit("RIFIUTO: il ramo v1 DERIVA la soglia, non la riceve.")
    if n_mock < 3:
        raise SystemExit("RIFIUTO: --n-mock %d: servono almeno tre coppie" % n_mock)
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M          # noqa: E402
    import paper1_remap as P1                # noqa: E402
    R14 = importa_r14()
    for f, mod in ((R14.transform, "rev1_r14_monotone"),
                   (R14.field_from_delta, "rev1_r14_monotone"),
                   (R14.beta1_pers1, "rev1_r14_monotone"),
                   (P1.build_nu, "paper1_remap")):
        if f.__module__ != mod:
            raise SystemExit("RIFIUTO: %s viene da %s, atteso %s"
                             % (f.__name__, f.__module__, mod))

    P = percorsi(root, region, versione)
    if not P["cache"].is_dir():
        raise SystemExit("RIFIUTO: cache inesistente: %s" % P["cache"])
    files = sorted(P["cache"].glob("delta_*.npy"))[:n_mock]
    if len(files) < n_mock:
        raise SystemExit("RIFIUTO: %d campi in %s, ne servono %d. I primi %d si "
                         "ereditano da v1, non si scelgono."
                         % (len(files), P["cache"], n_mock, n_mock))

    print("=" * 78)
    print("BOX-COX — item 4.2b-5  |  %s  |  %s  |  %d mock  |  eps %s"
          % (region, versione, len(files), list(EPS)))
    print("=" * 78)

    G = P1.setup_region(M, region, root / "data" / "raw" / "desi_dr1",
                        root / "data" / "processed" / "phase6_fields")
    mask = G["mask"]
    print("  maschera %d voxel   sigma_px %.9f" % (int(mask.sum()), float(M.SIGMA_PX)))

    # --- cancello A: a eps=0 le due costruzioni di nu coincidono ------------
    d0 = np.load(files[0])
    a = R14.field_from_delta(d0, mask, 0.0, M)
    b = P1.build_nu(np.asarray(d0, dtype=np.float64), mask, float(M.SIGMA_PX))
    diverse = int((np.asarray(a) != np.asarray(b)).sum())
    print("  cancello A: field_from_delta(eps=0) contro build_nu -> %s"
          % ("identici bit per bit" if diverse == 0 else "%d celle diverse" % diverse))
    if diverse:
        raise SystemExit("RIFIUTO: a eps=0 le due costruzioni devono coincidere: "
                         "transform(d,0) e' log(1+clip(d,-1+1e-3)), la prima riga "
                         "di build_nu. %d celle diverse su %d." % (diverse, a.size))
    del a, b, d0

    ens = leggi_ensemble_k0(P["ensemble"], n_mock) if versione == "v2" else {}
    if versione == "v2":
        print("  cancello B: %d valori di fkp.N_H1_k0 dal registro dell'ensemble"
              % len(ens))

    # --- il ciclo -----------------------------------------------------------
    per_eps = {e: [] for e in EPS}
    idx_usati = []
    t0 = time.time()
    for fp in files:
        kk = int(fp.stem.split("_")[-1])
        delta = np.load(fp)
        riga = {}
        for e in EPS:
            nu = R14.field_from_delta(delta, mask, e, M)
            n, _ = R14.beta1_pers1(nu, mask, M)
            riga[e] = int(n)
            per_eps[e].append(int(n))
            del nu
        idx_usati.append(kk)
        if versione == "v2" and kk in ens and riga[0.0] != ens[kk]:
            raise SystemExit(
                "RIFIUTO: idx %d, a eps=0 la passata da' %d ma il registro "
                "dell'ensemble porta fkp.N_H1_k0 = %d. Sono lo stesso campo e "
                "la stessa TDA: se differiscono, uno dei due non e' quello che "
                "dice di essere." % (kk, riga[0.0], ens[kk]))
        del delta
        if len(idx_usati) % 10 == 0:
            el = time.time() - t0
            print("    %d/%d   %.1f s/mock   ETA %.1f min"
                  % (len(idx_usati), len(files), el / len(idx_usati),
                     el / len(idx_usati) * (len(files) - len(idx_usati)) / 60))

    # --- s appaiata ---------------------------------------------------------
    n0 = np.array(per_eps[0.0], float)
    n1 = np.array(per_eps[1.0], float)
    d = n1 - n0
    s = float(d.mean())
    sem = float(d.std(ddof=1) / np.sqrt(d.size))
    sem_non_app = float(np.sqrt(n0.var(ddof=1) + n1.var(ddof=1)) / np.sqrt(d.size))

    print("\n  eps      <N_H1>        sd        spostamento appaiato contro eps=0")
    for e in EPS:
        v = np.array(per_eps[e], float)
        dd = v - n0
        extra = ("" if e == 0.0 else
                 "   %+9.2f +/- %.2f" % (dd.mean(),
                                         dd.std(ddof=1) / np.sqrt(dd.size)))
        print("  %-6.2f %10.2f %9.2f%s" % (e, v.mean(), v.std(ddof=1), extra))
    print("\n  s = <N(eps=1) - N(eps=0)> = %+.2f +/- %.2f   (%.1f sigma)"
          % (s, sem, s / sem if sem else float("nan")))
    print("  appaiamento: SEM %.2f contro %.2f non appaiata, guadagno %.1fx"
          % (sem, sem_non_app, sem_non_app / sem if sem else float("nan")))

    rec = {"schema": "paper2_boxcox_v1", "region": region, "versione": versione,
           "utc": now(), "eps": list(EPS), "n_mock": len(files),
           "indici": idx_usati, "cache": str(P["cache"]),
           "N_H1_per_eps": {str(e): per_eps[e] for e in EPS},
           "s": s, "sem_appaiata": sem, "sem_non_appaiata": sem_non_app,
           "guadagno_appaiamento": sem_non_app / sem if sem else None}

    if versione == "v1":
        # --- cancello C: NGC deve riprodurre il record 50 -------------------
        if region == "NGC":
            scarto = abs(s - S_V1_NGC)
            print("\n  cancello C: s^v1 NGC = %+.2f contro %+.2f del record 50, "
                  "scarto %.2f (limite %.1f)" % (s, S_V1_NGC, scarto, TOL_S_V1))
            rec["cancello_record50"] = {"atteso": S_V1_NGC, "scarto": scarto,
                                        "ok": bool(scarto <= TOL_S_V1)}
            if scarto > TOL_S_V1:
                raise SystemExit(
                    "RIFIUTO: il ricalcolo di s^v1 NGC non riproduce il record "
                    "50. Finche' non lo fa, il ramo SGC — che non ha termine di "
                    "paragone — non e' affidabile e non va calcolato.")
            print("            superato: il ramo SGC e' coperto dallo stesso cammino")
        succ, fall = soglie_da_s(s)
        rec.update({"soglia_successo_derivata": succ,
                    "soglia_fallimento_derivata": fall})
        print("\n  SOGLIE DERIVATE da |s^v1| = %.2f:" % abs(s))
        print("    successo   |s^v2| < %.4f gen   (%.0f%%)" % (succ, 100 * FRAZ_SUCCESSO))
        print("    fallimento |s^v2| > %.4f gen   (%.0f%%)" % (fall, 100 * FRAZ_FALLIMENTO))
        print("  Sono DERIVATE, non ancora DICHIARATE: registrale, poi ripassale")
        print("  con --soglia. Finche' non lo fai, il ramo v2 non si calcola.")
    else:
        succ = float(soglia)
        fall = succ * FRAZ_FALLIMENTO / FRAZ_SUCCESSO
        rec.update({"soglia_successo": succ, "soglia_fallimento": fall,
                    "sigma_max_invalida": SIGMA_MAX_INVALIDA,
                    "esito": esito(s, sem, succ, fall)})
        print("\n  soglie dichiarate: successo < %.4f, fallimento > %.4f" % (succ, fall))
        print("  sigma(s^v2) = %.2f, limite di invalidazione %.0f" % (sem, SIGMA_MAX_INVALIDA))
        print("\n  ESITO 4.2b-5: %s" % rec["esito"])

    P["out"].parent.mkdir(parents=True, exist_ok=True)
    P["out"].write_text(json.dumps(rec, indent=2, ensure_ascii=True),
                        encoding="utf-8")
    print("\n  scritto: %s" % P["out"])
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

    print("selftest paper2_boxcox_v2")

    chk("eps e' quello del record 50", EPS == (0.0, 0.25, 0.5, 1.0))
    chk("eps=0 c'e', ed e' la baseline", 0.0 in EPS)
    chk("i mock sono 50, come v1", N_MOCK == 50)
    chk("s^v1 NGC e la sua SEM sono quelli del record 50",
        S_V1_NGC == -183.32 and abs(SEM_V1_NGC - 11.124102898936275) < 1e-15)
    chk("le frazioni sono un quarto e tre quarti", (FRAZ_SUCCESSO, FRAZ_FALLIMENTO) == (0.25, 0.75))

    # le soglie del record 50 si RIDERIVANO dai suoi numeri
    su, fa = soglie_da_s(S_V1_NGC)
    chk("45.8 si riderivano da |s^v1| NGC", abs(su - 45.83) < 0.01, su)
    chk("137.5 pure", abs(fa - 137.49) < 0.01, fa)
    chk("e il rapporto fra le due e' tre", abs(fa / su - 3.0) < 1e-12)

    # le tre zone, piu' l'invalidazione
    chk("|s| sotto la soglia e' SUCCESSO", esito(-30.0, 5.0, su, fa) == "SUCCESSO")
    chk("il valore v1 e' FALLIMENTO", esito(S_V1_NGC, 11.1, su, fa) == "FALLIMENTO")
    chk("in mezzo NON DECIDE", esito(-90.0, 5.0, su, fa) == "NON DECIDE")
    chk("il segno non conta: e' il modulo",
        esito(+30.0, 5.0, su, fa) == esito(-30.0, 5.0, su, fa))
    chk("sigma oltre 15 invalida, anche con |s| piccolo",
        "invalidata" in esito(-1.0, 20.0, su, fa))
    chk("e la SEM di v1 (11.12) sta sotto il limite di invalidazione",
        SEM_V1_NGC < SIGMA_MAX_INVALIDA)

    # la trasformazione, riprodotta qui SOLO per verificarne le proprieta'
    def tr(x, e):
        y = 1.0 + np.clip(x, -1.0 + 1e-3, None)
        return np.log(y) if e == 0.0 else (np.power(y, e) - 1.0) / e
    d = np.array([-0.999, -0.5, 0.0, 1.0, 10.0, 150.0])
    chk("a eps=0 la trasformazione e' il logaritmo di 1+delta",
        np.allclose(tr(d, 0.0), np.log(1 + np.clip(d, -1 + 1e-3, None))))
    chk("il clip a -1+1e-3 impedisce il logaritmo di zero",
        np.isfinite(tr(np.array([-1.0, -2.0]), 0.0)).all())
    for e in (0.25, 0.5, 1.0):
        chk("a eps=%.2f e' monotona crescente" % e,
            bool(np.all(np.diff(tr(d, e)) > 0)))
    chk("a eps=1 e' affine in delta: (1+d)-1 = d",
        np.allclose(tr(d, 1.0), np.clip(d, -1 + 1e-3, None)))
    chk("il limite per eps->0 e' il logaritmo",
        np.allclose(tr(d, 1e-9), tr(d, 0.0), atol=1e-6))

    # lettura del registro dell'ensemble
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "e.jsonl"
        f.write_text("\n".join(json.dumps(r) for r in [
            {"index": 0, "fkp": {"N_H1_k0": 111}},
            {"index": 1, "fkp": {"N_H1_k0": 222}, "smoke": True},
            {"index": 60, "fkp": {"N_H1_k0": 333}},
            {"schema": "sommario"},
        ]) + "\n", encoding="utf-8")
        e = leggi_ensemble_k0(f, 50)
        chk("legge fkp.N_H1_k0 per indice", e.get(0) == 111)
        chk("scarta i record di smoke", 1 not in e)
        chk("e quelli oltre i primi 50", 60 not in e)
        chk("e il sommario non ha indice, quindi non entra", len(e) == 1, e)

    # i rifiuti, e devono venire PRIMA degli import di progetto
    def _rif(reg, ver, sog=None, nm=N_MOCK):
        try:
            passata("/nonesiste", reg, ver, sog, nm)
        except SystemExit as ex:
            return str(ex)
        except Exception as ex:
            return "ALTRO:" + type(ex).__name__
        return ""
    m = _rif("NGC", "v2", None)
    chk("v2 senza --soglia e' rifiutato", "REGISTRATA" in m, m)
    chk("e il rifiuto arriva prima dell'import di progetto", "ALTRO" not in m, m)
    m2 = _rif("NGC", "v1", 45.8)
    chk("v1 CON --soglia e' rifiutato: la deriva, non la riceve",
        "DERIVA" in m2, m2)
    chk("meno di tre coppie e' rifiutato", "tre coppie" in _rif("NGC", "v1", None, 2))

    # l'import di rev1_r14_monotone non deve consumare la nostra riga di comando
    _argv = sys.argv[:]
    try:
        importa_r14()
    except SystemExit as ex:
        chk("l'import di r14 non uccide il processo", False, "SystemExit: %s" % ex)
    except ImportError:
        chk("l'import di r14 non uccide il processo (modulo assente qui)", True)
    else:
        chk("l'import di r14 non uccide il processo", True)
    chk("e sys.argv viene ripristinato", sys.argv == _argv, sys.argv)

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("passata")
    q.add_argument("--root", default=ROOT_DEFAULT)
    q.add_argument("--region", choices=["NGC", "SGC"], required=True)
    q.add_argument("--versione", choices=["v1", "v2"], required=True)
    q.add_argument("--soglia", type=float, default=None,
                   help="soglia di successo, derivata da s^v1 e REGISTRATA. "
                        "Obbligatoria per --versione v2")
    q.add_argument("--n-mock", dest="n_mock", type=int, default=N_MOCK)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "passata":
        return passata(a.root, a.region, a.versione, a.soglia, a.n_mock)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

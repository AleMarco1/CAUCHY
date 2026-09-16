#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_fasi_v2.py — item 5.3, il residuo beyond-two-point su v2.

LA CHECKLIST LO METTE PER PRIMO DENTRO 4.2a, e la ragione e' esterna al
programma: e' l'unico controllo della serie che tocca un manoscritto GIA'
SOTTOMESSO. Se l'ensemble v2 sposta il residuo, la modifica al Paper 1 nasce li'.

PERCHE' n10 NON BASTA COSI' COM'E'
----------------------------------
paper1_rev_n10_phases.py e' NGC per costruzione: DESI_NH1 = 28256.0, la
maschera, la cache di nu, l'uscita, la sorgente dei campi e il report hanno NGC
nel corpo. E legge i cubi congelati results/phase8_test2_fields/test2_*.npz,
che per v2 non esistono e per SGC non esistono affatto.

Qui si parametrizzano tre cose, e nient'altro cambia:
  --region     NGC o SGC, con le sue costanti congelate
  --versione   v1 o v2, che sceglie la SORGENTE dei campi nu
  l'ancora     per_mock per v1, il registro dell'ensemble per v2

`phase_randomize` e le utilita' sono IMPORTATE da n10: la randomizzazione e' una
sola implementazione, e riscriverla sarebbe il difetto del rapporto di varianze.
n10 fa parse_args dentro main(), quindi importarlo e' sicuro — al contrario di
rev1_r14_monotone, che lo fa a livello di modulo.

IL LATO DESI NON SI MUOVE FRA v1 E v2
-------------------------------------
La ripesatura tocca solo i mock. Il campo nu di DESI, e quindi la sua
distribuzione a fasi randomizzate, e' identico nelle due versioni: i record
desi_pr si scrivono in un file che dipende dalla REGIONE e non dalla versione, e
la seconda passata li riusa. Meta' lavoro, e nessuna ambiguita' su quale DESI
sia stato usato.

LE SORGENTI DEI CAMPI nu
------------------------
  v1 NGC  i cubi congelati test2_XXXX.npz (chiave 'delta', contiene nu), da 200
          in su: gli indici 0-199 sono i cubi del pilota (record 53, §3.3 della
          risoluzione 313/445).
  v1 SGC  non esistono cubi congelati: nu si ricostruisce con P1.build_nu dalla
          cache dei delta di v1, che e' la catena di paper1_remap.
  v2      P1.build_nu dalla cache dei delta v2 scritta dal runner di 4.2a.

L'ANCORA, E LA DOMANDA DA FARSI SU OGNI ANCORA
----------------------------------------------
«Questo registro e' stato prodotto dal codice che sto eseguendo?» Quattro
fermate in un giorno su questa distinzione.
  v1 NGC  per_mock_NGC_R5.jsonl: e' la catena che ha prodotto i cubi test2, e
          n10 lo usa gia' con tolleranza 0.5. Stessa catena.
  v1 SGC  per_mock_SGC_R5.jsonl: e' la catena che ha prodotto la cache dei
          delta v1. Stessa catena.
  v2      fkp.N_H1_k0 di ensemble_v2_<REG>.jsonl: e' la catena che ha scritto la
          cache dei delta v2, e build_field vi coincide con build_nu bit per
          bit (verificato dal runner a ogni realizzazione). Tolleranza ZERO.

USO
    python src\\paper2_fasi_v2.py selftest
    python src\\paper2_fasi_v2.py corri --region NGC --versione v1 --n-desi 50 --n-mock 100
    python src\\paper2_fasi_v2.py corri --region NGC --versione v2 --n-mock 100
    python src\\paper2_fasi_v2.py corri --region SGC --versione v1 --n-desi 50 --n-mock 100
    python src\\paper2_fasi_v2.py corri --region SGC --versione v2 --n-mock 100

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

DESI_NH1 = {"NGC": 28256.0, "SGC": 15122.0}
N_VOXEL = {"NGC": 307805, "SGC": 172225}
# sigma_px per emisfero: e' una globale di modulo, e il default di phase8 e' NGC.
SIGMA_PX_ATTESA = {"NGC": 0.32042249039652254, "SGC": 0.33605500065144590}
MASCHERA = {"NGC": "bgs_ngc_mask_128.npy", "SGC": "bgs_sgc_mask_128.npy"}
MIN_IDX_CUBI = 200        # gli 0-199 di test2_ sono i cubi del pilota
TOL_SPETTRO = 1e-10       # n10: |dA|/A dopo la randomizzazione
TOL_ANCORA = 0.5          # n10 usa questa; stessa catena, quindi e' generosa
SEED = 20260725           # lo stesso di n10, per riproducibilita'

# IL DENOMINATORE, DICHIARATO DAL PAPER 1 §6 E NON SCELTO QUI.
# La quantita' non e' il residuo diviso la sua SEM. E' Delta_N = N^phi - N_H1,
# il guadagno di generatori sotto gaussianizzazione, PER REALIZZAZIONE, e il
# denominatore e' la sua dispersione MOCK-TO-MOCK:
#     «the relevant denominator is the mock-to-mock dispersion of Delta N, which
#      we measure on the same 100 mocks: sigma_Delta = 250.5. On that scale DESI
#      departs from the ensemble by 6.8 sigma, with empirical rank 1/101»
# e, esplicitamente, «it is this number — not the procedural error bar — that we
# quote throughout».
# La SEM del residuo (40.6) darebbe 42.1 sigma: e' la precisione con cui il
# residuo e' NOTO, non la sua anomalia. E' la distinzione del record 54 fra
# proprieta' d'ensemble e affermazione sul campo osservato, applicata dal Paper 1
# prima che quel record esistesse.
# Due proprieta' di sigma_Delta che il paper registra e che vanno riportate:
#  - e' MINORE di sigma(N_H1) = 313.0, perche' i due conteggi correlano a
#    r = 0.68 e la differenza cancella parte della covarianza;
#  - NON e' corretta per il rumore di estrazione delle fasi sul lato mock (157
#    generatori, dedotti dalle 50 estrazioni sul lato DESI): togliendolo in
#    quadratura si avrebbe 195.2 e 8.8 sigma. Il paper quota il 6.8 come scelta
#    conservativa, e nota che la correzione andrebbe nella direzione che
#    rafforza il risultato.
SIGMA_DELTA_V1_NGC = 250.5      # Paper 1 §6, sugli stessi 100 mock
SIGMA_NH1_NGC = 313.0           # per il confronto che il paper fa
# Il rumore di estrazione delle fasi NON e' una costante: e' la sd delle
# estrazioni fatte sul lato DESI, e vale 157.01 in NGC — il 157 del Paper 1 —
# ma 113.14 in SGC. Scritto come costante NGC e applicato a SGC dava varianza
# negativa su v1 e 30.1 su v2, cioe' 17.3 sigma: un numero senza senso.
# Stessa forma di SIGMA_PX. Si DERIVA dal campione, che e' gia' li'.
RUMORE_FASI_NGC_ATTESO = 157.0  # solo per riscontrare la derivazione su NGC
ROOT_DEFAULT = "."


def now():
    return datetime.now(timezone.utc).isoformat()


def percorsi(root, region, versione):
    d = Path(root)
    return {
        "cubi": d / "results" / "phase8_test2_fields",
        "delta_v1": d / "data" / "processed" / "paper1_mock_deltas" / region,
        "delta_v2": d / "data" / "processed" / "paper2_mock_deltas_v2" / region,
        "desi_nu_congelata": d / "results" / "paper1" / ("n1_desi_nu_%s.npy" % region),
        "desi_nu_nuova": d / "results" / "paper2" / ("n1_desi_nu_%s.npy" % region),
        "maschera": d / "data" / "processed" / "phase6_fields" / MASCHERA[region],
        "per_mock": d / "results" / "paper1" / ("per_mock_%s_R5.jsonl" % region),
        "ensemble": d / "results" / "paper2" / ("ensemble_v2_%s.jsonl" % region),
        # il lato DESI NON dipende dalla versione
        "desi_pr": d / "results" / "paper2" / ("fasi_desi_pr_%s.jsonl" % region),
        "mock_pr": d / "results" / "paper2" / ("fasi_mock_pr_%s_%s.jsonl"
                                              % (versione, region)),
        "report": d / "results" / "paper2" / ("fasi_report_%s_%s.json"
                                             % (versione, region)),
        "report_n10": d / "results" / "paper1" / ("n10_report_%s.json" % region),
    }


def sorgente_nu(P, region, versione):
    """(elenco di (idx, callable che restituisce nu), descrizione)."""
    if versione == "v1" and region == "NGC" and P["cubi"].is_dir():
        files = [(int(p.stem.split("_")[1]), p)
                 for p in sorted(P["cubi"].glob("test2_*.npz"))]
        files = [(i, p) for i, p in files if i >= MIN_IDX_CUBI]
        return files, "cubi congelati test2_*.npz, idx >= %d" % MIN_IDX_CUBI
    cache = P["delta_v1"] if versione == "v1" else P["delta_v2"]
    files = [(int(p.stem.split("_")[-1]), p)
             for p in sorted(cache.glob("delta_*.npy"))]
    return files, "nu ricostruito da %s" % cache


def carica_nu(path, mask, P1, sigma_px):
    """Dal cubo congelato o dal delta grezzo, secondo l'estensione."""
    if path.suffix == ".npz":
        with np.load(path) as Z:
            return np.asarray(Z["delta"]), "cubo"
    d = np.load(path)
    return P1.build_nu(np.asarray(d, dtype=np.float64), mask, sigma_px), "delta"


def ancore(P, region, versione):
    """idx -> N_H1 atteso, dalla catena che ha prodotto i campi."""
    out = {}
    if versione == "v2":
        if not P["ensemble"].is_file():
            return out, "assente"
        with P["ensemble"].open("r", encoding="utf-8") as fh:
            for riga in fh:
                riga = riga.strip()
                if not riga:
                    continue
                r = json.loads(riga)
                if "index" in r and not r.get("smoke"):
                    v = (r.get("fkp") or {}).get("N_H1_k0")
                    if v is not None:
                        out[int(r["index"])] = float(v)
        return out, "ensemble_v2 fkp.N_H1_k0"
    if not P["per_mock"].is_file():
        return out, "assente"
    import re
    with P["per_mock"].open("r", encoding="utf-8", errors="replace") as fh:
        for j, riga in enumerate(fh):
            riga = riga.strip()
            if not riga:
                continue
            r = json.loads(riga)
            piatto = {}

            def _f(d, pre=""):
                for k, v in d.items():
                    q = "%s.%s" % (pre, k) if pre else k
                    if isinstance(v, dict):
                        _f(v, q)
                    else:
                        piatto[q] = v
            _f(r)
            try:
                kk = int(str(piatto.get("key", j)).split("_")[-1])
            except (TypeError, ValueError):
                kk = j
            v = piatto.get("base.N_H1")
            if v is not None:
                out[kk] = float(v)
    return out, "per_mock base.N_H1"


def statistiche(v):
    v = np.asarray(v, float)
    n = v.size
    sd = float(v.std(ddof=1)) if n > 1 else 0.0
    return {"n": int(n), "mean": float(v.mean()), "std": sd,
            "sem": sd / np.sqrt(n) if n > 1 else 0.0,
            "min": float(v.min()), "max": float(v.max())}


# ---------------------------------------------------------------------------

def corri(root, region, versione, n_desi, n_mock, da=0, out_path=None):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M            # noqa: E402
    import paper1_remap as P1                  # noqa: E402
    import paper1_rev_n10_phases as N10        # noqa: E402
    for f, mod in ((N10.phase_randomize, "paper1_rev_n10_phases"),
                   (P1.build_nu, "paper1_remap")):
        if f.__module__ != mod:
            raise SystemExit("RIFIUTO: %s viene da %s, atteso %s"
                             % (f.__name__, f.__module__, mod))

    P = percorsi(root, region, versione)
    print("=" * 78)
    print("FASI RANDOMIZZATE — item 5.3  |  %s  |  %s" % (region, versione))
    print("=" * 78)

    # LA GEOMETRIA VA IMPOSTATA. M.SIGMA_PX e' una globale di modulo il cui
    # default e' NGC (0.3204): senza setup_region, build_nu su SGC liscia con la
    # sigma sbagliata e N_H1 esce piu' alto — 18931 contro 18627 attesi.
    # E' la stessa classe di N_TARGET_BGS, che il runner di Fase 3 asserisce a
    # ogni cambio di emisfero perche' e' mutata altrove.
    G = P1.setup_region(M, region, root / "data" / "raw" / "desi_dr1",
                        root / "data" / "processed" / "phase6_fields")
    mask = np.load(P["maschera"]).astype(bool)
    if int(mask.sum()) != N_VOXEL[region]:
        raise SystemExit("RIFIUTO: %d voxel, attesi %d"
                         % (int(mask.sum()), N_VOXEL[region]))
    if not np.array_equal(mask, G["mask"]):
        raise SystemExit("RIFIUTO: la maschera congelata e quella riderivata da "
                         "setup_region non coincidono (2.1-M).")
    sigma_px = float(M.SIGMA_PX)
    if abs(sigma_px - SIGMA_PX_ATTESA[region]) / SIGMA_PX_ATTESA[region] > 1e-9:
        raise SystemExit("RIFIUTO: sigma_px = %.9f, atteso %.9f per %s. La "
                         "geometria non e' quella dell'emisfero."
                         % (sigma_px, SIGMA_PX_ATTESA[region], region))
    print("  geometria: sigma_px %.9f, maschera %d voxel, coincide con la congelata"
          % (sigma_px, int(mask.sum())))

    # --- cancello 1: il campo nu di DESI riproduce il congelato -------------
    cache = (P["desi_nu_congelata"] if P["desi_nu_congelata"].is_file()
             else P["desi_nu_nuova"])
    if not cache.is_file():
        raise SystemExit("RIFIUTO: campo nu di DESI assente. Esegui prima "
                         "src/paper2_desi_ladder.py costruisci --region %s" % region)
    nu_d = np.load(cache)
    v = float(M.compute_tda_features(nu_d, mask, M.N_THRESH, masked=True)[4])
    print("  nu di DESI da %s" % cache)
    print("  cancello 1: N_H1(DESI) = %.0f, congelato %.0f -> %s"
          % (v, DESI_NH1[region], "esatto" if v == DESI_NH1[region] else "DISCORDE"))
    if v != DESI_NH1[region]:
        raise SystemExit("RIFIUTO: il campo nu di DESI non e' quello del paper.")

    # --- cancello 2: la randomizzazione preserva lo spettro -----------------
    _, err = N10.phase_randomize(nu_d, np.random.default_rng(0), check=True)
    print("  cancello 2: errore relativo sullo spettro %.3e (limite %.0e) -> %s"
          % (err, TOL_SPETTRO, "ok" if err < TOL_SPETTRO else "FALLITO"))
    if err >= TOL_SPETTRO:
        raise SystemExit("RIFIUTO: lo spettro non e' preservato.")

    # --- lato DESI: non dipende dalla versione ------------------------------
    fatti_d = set()
    if P["desi_pr"].is_file():
        with P["desi_pr"].open("r", encoding="utf-8") as fh:
            fatti_d = {json.loads(l)["idx"] for l in fh if l.strip()}
    print("\n[DESI] %d realizzazioni a fasi randomizzate, %d gia' fatte "
          "(il lato dati NON cambia fra v1 e v2)" % (n_desi, len(fatti_d)))
    t0 = time.time()
    for k in range(n_desi):
        if k in fatti_d:
            continue
        pr, _ = N10.phase_randomize(nu_d, np.random.default_rng(SEED + k))
        f = M.compute_tda_features(pr, mask, M.N_THRESH, masked=True)
        N10.append_jsonl(P["desi_pr"], {"idx": k, "region": region,
                                        "N_H1": float(f[4]), "utc": now()})
        if (k + 1) % 10 == 0:
            print("    %d/%d  %.1f s" % (k + 1, n_desi,
                                         (time.time() - t0) / (k + 1 - len(fatti_d))))
    del nu_d

    # --- lato mock ----------------------------------------------------------
    files, descr = sorgente_nu(P, region, versione)
    # --da: v1 NGC parte dai cubi, che esistono da 200 in su; v2 ricostruisce
    # dalla cache, che parte da 0. Senza allineare gli indici i due rami usano
    # realizzazioni DIVERSE e la differenza contiene la varianza campionaria
    # invece del solo trattamento.
    files = [(i, p) for i, p in files if i >= da][:n_mock]
    if not files:
        raise SystemExit("RIFIUTO: nessun campo mock disponibile (%s)" % descr)
    anc, da_dove = ancore(P, region, versione)
    print("\n[MOCK] %d campi — %s" % (len(files), descr))
    print("       ancora: %s, %d valori" % (da_dove, len(anc)))
    if not anc:
        raise SystemExit("RIFIUTO: nessuna ancora: il campo originale non e' "
                         "verificabile e la misura non sarebbe interpretabile.")

    fatti_m = set()
    if P["mock_pr"].is_file():
        with P["mock_pr"].open("r", encoding="utf-8") as fh:
            fatti_m = {json.loads(l)["idx"] for l in fh if l.strip()}
    if fatti_m:
        print("       ripresa: %d gia' fatti" % len(fatti_m))

    t0 = time.time()
    n = 0
    for i, p in files:
        if i in fatti_m:
            continue
        nu, tipo = carica_nu(p, mask, P1, sigma_px)
        orig = float(M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)[4])
        atteso = anc.get(i)
        if atteso is None:
            print("    [%4d] senza ancora, saltato" % i)
            del nu
            continue
        if abs(orig - atteso) > TOL_ANCORA:
            print("    [FERMO] idx %d: originale %.0f contro ancora %.0f "
                  "(%s). Il campo non e' quello che l'ancora descrive."
                  % (i, orig, atteso, da_dove))
            return 1
        pr, _ = N10.phase_randomize(nu, np.random.default_rng(SEED + 10000 + i))
        f = M.compute_tda_features(pr, mask, M.N_THRESH, masked=True)
        N10.append_jsonl(P["mock_pr"], {"idx": i, "region": region,
                                        "versione": versione, "sorgente": tipo,
                                        "N_H1_orig": orig, "N_H1": float(f[4]),
                                        "ancora": atteso, "utc": now()})
        del nu, pr
        n += 1
        if n % 10 == 0:
            el = time.time() - t0
            print("    %d/%d  orig=%.0f PR=%.0f  %.1f s/mock  ETA %.1f min"
                  % (n, len(files) - len(fatti_m), orig, f[4], el / n,
                     el / n * (len(files) - len(fatti_m) - n) / 60))

    # --- analisi -------------------------------------------------------------
    dpr = np.array([json.loads(l)["N_H1"]
                    for l in P["desi_pr"].read_text(encoding="utf-8").splitlines()
                    if l.strip()], float)
    righe = [json.loads(l)
             for l in P["mock_pr"].read_text(encoding="utf-8").splitlines()
             if l.strip()]
    mpr = np.array([r["N_H1"] for r in righe], float)
    mor = np.array([r["N_H1_orig"] for r in righe], float)
    if dpr.size < 3 or mpr.size < 3:
        print("\n  campioni troppo piccoli.")
        return 0

    sd, sm, so = statistiche(dpr), statistiche(mpr), statistiche(mor)

    # --- Delta_N per realizzazione, e il denominatore del Paper 1 ----------
    dN_mock = mpr - mor                       # guadagno sotto gaussianizzazione
    dN_desi = float(dpr.mean()) - DESI_NH1[region]
    sigma_delta = float(dN_mock.std(ddof=1))
    scarto = dN_desi - float(dN_mock.mean())  # = il residuo, per costruzione
    z_delta = scarto / sigma_delta if sigma_delta else float("nan")
    n_sopra = int((dN_mock >= dN_desi).sum())
    rango = "%d/%d" % (n_sopra + 1, dN_mock.size + 1)
    # La correzione per il rumore di fase, che il paper riporta e NON adotta.
    # Il rumore e' la dispersione delle estrazioni sul lato DESI, per EMISFERO.
    rumore_fasi = float(sd["std"])
    var_corr = sigma_delta ** 2 - rumore_fasi ** 2
    sigma_corr = float(np.sqrt(var_corr)) if var_corr > 0 else None
    z_corr = scarto / sigma_corr if sigma_corr else None

    d_or = so["mean"] - DESI_NH1[region]
    d_pr = sm["mean"] - sd["mean"]
    se_pr = float(np.sqrt(sm["sem"] ** 2 + sd["sem"] ** 2))
    frac = d_pr / d_or if d_or else float("nan")
    residuo = d_or - d_pr

    print("\n" + "=" * 78)
    print("  %-22s %6s %12s %10s %9s" % ("", "n", "media", "sd", "SEM"))
    print("  %-22s %6d %12.0f %10s %9s" % ("DESI originale", 1,
                                           DESI_NH1[region], "-", "-"))
    print("  %-22s %6d %12.1f %10.1f %9.1f" % ("DESI randomizzato", sd["n"],
                                               sd["mean"], sd["std"], sd["sem"]))
    print("  %-22s %6d %12.1f %10.1f %9.1f" % ("mock originali", so["n"],
                                               so["mean"], so["std"], so["sem"]))
    print("  %-22s %6d %12.1f %10.1f %9.1f" % ("mock randomizzati", sm["n"],
                                               sm["mean"], sm["std"], sm["sem"]))
    print("\n  deficit originale       : %9.1f" % d_or)
    print("  deficit randomizzato    : %9.1f +/- %.1f" % (d_pr, se_pr))
    print("  FRAZIONE SPETTRALE      : %8.1f%% +/- %.1f%%"
          % (100 * frac, 100 * se_pr / abs(d_or) if d_or else float("nan")))
    print("  RESIDUO beyond-two-point: %9.1f +/- %.1f (SEM)" % (residuo, se_pr))
    print("\n  --- la significativita', sul denominatore del Paper 1 §6 ---")
    print("  Delta_N di DESI          : %9.1f   (media di %d estrazioni)"
          % (dN_desi, sd["n"]))
    print("  Delta_N dei mock         : %9.1f +/- %.1f (sd mock-to-mock)"
          % (float(dN_mock.mean()), sigma_delta))
    print("  differenza               : %9.1f   (il residuo, per costruzione)"
          % scarto)
    print("  SIGNIFICATIVITA'         : %8.1f sigma   rango empirico %s"
          % (z_delta, rango))
    print("  rumore di estrazione delle fasi: %.2f (sd delle %d estrazioni su "
          "DESI)" % (rumore_fasi, sd["n"]))
    if sigma_corr:
        print("  (togliendolo in quadratura: sigma_Delta %.1f, %.1f sigma — "
              "riportato, NON adottato)" % (sigma_corr, z_corr))
    else:
        print("  (la correzione darebbe varianza negativa: non si applica, e il "
              "fatto si riporta)")
    print("  la SEM darebbe %.1f sigma, ma e' la precisione con cui il residuo e'"
          % (residuo / se_pr if se_pr else float("nan")))
    print("  NOTO, non la sua anomalia: il Paper 1 quota l'altro, e cosi' qui.")

    rec = {"schema": "paper2_fasi_v1", "region": region, "versione": versione,
           "utc": now(), "sorgente": descr, "ancora": da_dove,
           "desi_originale": DESI_NH1[region], "desi_pr": sd,
           "mock_originali": so, "mock_pr": sm,
           "deficit_originale": d_or, "deficit_pr": d_pr, "sem_deficit_pr": se_pr,
           "frazione_spettro": frac, "residuo": residuo,
           "delta_N_desi": dN_desi,
           "delta_N_mock_media": float(dN_mock.mean()),
           "sigma_delta": sigma_delta,
           "significativita_sigma": z_delta,
           "rango_empirico": rango,
           "rumore_fasi": rumore_fasi,
           "sigma_delta_corretta_per_fasi": sigma_corr,
           "significativita_corretta": z_corr,
           "denominatore": ("dispersione mock-to-mock di Delta_N = N^phi - N_H1, "
                            "Paper 1 §6; NON la SEM del residuo"),
           "sem_del_residuo_per_confronto": se_pr,
           "sigma_su_sem_per_confronto": residuo / se_pr if se_pr else None,
           "indici": sorted(r["idx"] for r in righe),
           "indice_da": da,
           "residuo_sigma": residuo / se_pr if se_pr else None,
           "seed": SEED}

    # --- riproduzione di n10, dove esiste -----------------------------------
    if versione == "v1" and region == "NGC":
        for nome, avuto, atteso in (("sigma_Delta", sigma_delta, SIGMA_DELTA_V1_NGC),
                                    ("rumore fasi", rumore_fasi, RUMORE_FASI_NGC_ATTESO),
                                    ("significativita", z_delta, 6.8)):
            print("  riproduzione Paper 1 §6, %s: %.4f contro %.4f quotato"
                  % (nome, avuto, atteso))
        rec["riproduzione_paper1"] = {"sigma_delta_quotata": SIGMA_DELTA_V1_NGC,
                                      "sigma_delta_qui": sigma_delta,
                                      "rumore_fasi_quotato": RUMORE_FASI_NGC_ATTESO,
                                      "rumore_fasi_qui": rumore_fasi,
                                      "significativita_quotata": 6.8,
                                      "significativita_qui": z_delta}

    if versione == "v1" and P["report_n10"].is_file():
        r10 = json.loads(P["report_n10"].read_text(encoding="utf-8"))
        f10 = r10.get("frazione_spettro")
        if f10 is not None:
            scarto = abs(frac - float(f10))
            rec["riproduzione_n10"] = {"n10": float(f10), "qui": frac,
                                       "scarto": scarto}
            print("\n  riproduzione di n10: frazione %.4f contro %.4f, scarto %.4f"
                  % (frac, float(f10), scarto))
            print("  (i campioni possono differire: n10 usa --n_mock proprio)")

    dest = Path(out_path) if out_path else P["report"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    N10.atomic_write_json(dest, rec)
    print("\n  report: %s" % dest)
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

    print("selftest paper2_fasi_v2")

    chk("i valori congelati di DESI sono quelli del paper",
        DESI_NH1 == {"NGC": 28256.0, "SGC": 15122.0})
    chk("i voxel di maschera sono quelli congelati",
        N_VOXEL == {"NGC": 307805, "SGC": 172225})
    chk("il seme e' quello di n10, per riproducibilita'", SEED == 20260725)
    chk("i cubi test2 si usano solo da 200 in su", MIN_IDX_CUBI == 200)
    chk("la tolleranza sullo spettro e' quella di n10", TOL_SPETTRO == 1e-10)

    P = percorsi("/b", "SGC", "v2")
    chk("il lato DESI NON dipende dalla versione",
        "v1" not in P["desi_pr"].name and "v2" not in P["desi_pr"].name
        and P["desi_pr"].name == "fasi_desi_pr_SGC.jsonl", P["desi_pr"].name)
    chk("il lato mock invece si", P["mock_pr"].name == "fasi_mock_pr_v2_SGC.jsonl")
    chk("le uscite stanno in results/paper2, fuori dai tier congelati",
        all(P[k].parent.name == "paper2"
            for k in ("desi_pr", "mock_pr", "report")))
    chk("la cache nu si cerca prima fra le congelate",
        P["desi_nu_congelata"].parent.name == "paper1"
        and P["desi_nu_nuova"].parent.name == "paper2")
    chk("la maschera e' quella dell'emisfero",
        P["maschera"].name == "bgs_sgc_mask_128.npy")
    chk("sigma_px e' dichiarata per emisfero, e le due sono diverse",
        SIGMA_PX_ATTESA["NGC"] != SIGMA_PX_ATTESA["SGC"]
        and abs(SIGMA_PX_ATTESA["SGC"] - 0.336055) < 1e-6)
    chk("il default di phase8 e' quello di NGC: senza setup_region SGC sbaglia",
        abs(SIGMA_PX_ATTESA["NGC"] - 0.3204225) < 1e-6)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # sorgente: v1 NGC coi cubi, altrimenti i delta
        (td / "results" / "phase8_test2_fields").mkdir(parents=True)
        for i in (0, 199, 200, 201):
            (td / "results" / "phase8_test2_fields"
             / ("test2_%04d.npz" % i)).write_text("x", encoding="utf-8")
        Pn = percorsi(td, "NGC", "v1")
        f, d = sorgente_nu(Pn, "NGC", "v1")
        chk("v1 NGC usa i cubi e scarta il blocco pilota",
            [i for i, _ in f] == [200, 201] and "test2" in d, f)

        for reg, ver, sub in (("SGC", "v1", "paper1_mock_deltas"),
                              ("NGC", "v2", "paper2_mock_deltas_v2")):
            dd = td / "data" / "processed" / sub / reg
            dd.mkdir(parents=True)
            for i in range(3):
                (dd / ("delta_%04d.npy" % i)).write_text("x", encoding="utf-8")
            Px = percorsi(td, reg, ver)
            fx, dx = sorgente_nu(Px, reg, ver)
            chk("%s %s ricostruisce nu dai delta, dall'indice 0" % (reg, ver),
                [i for i, _ in fx] == [0, 1, 2] and "build_nu" not in dx
                and sub in dx, (fx, dx))

        # ancore
        (td / "results" / "paper2").mkdir(parents=True, exist_ok=True)
        (td / "results" / "paper2" / "ensemble_v2_NGC.jsonl").write_text(
            "\n".join(json.dumps(r) for r in [
                {"index": 0, "fkp": {"N_H1_k0": 111}},
                {"index": 1, "fkp": {"N_H1_k0": 222}, "smoke": True},
                {"schema": "sommario"}]) + "\n", encoding="utf-8")
        a, dv = ancore(percorsi(td, "NGC", "v2"), "NGC", "v2")
        chk("l'ancora di v2 e' fkp.N_H1_k0 e scarta lo smoke",
            a == {0: 111.0} and "ensemble_v2" in dv, (a, dv))
        (td / "results" / "paper1").mkdir(parents=True, exist_ok=True)
        (td / "results" / "paper1" / "per_mock_NGC_R5.jsonl").write_text(
            json.dumps({"key": "delta_0042", "base": {"N_H1": 35288}}) + "\n",
            encoding="utf-8")
        a2, dv2 = ancore(percorsi(td, "NGC", "v1"), "NGC", "v1")
        chk("l'ancora di v1 e' per_mock, indicizzata dal suffisso",
            a2 == {42: 35288.0} and "per_mock" in dv2, (a2, dv2))
        a3, dv3 = ancore(percorsi(td, "SGC", "v1"), "SGC", "v1")
        chk("un'ancora assente si dichiara, non si finge", a3 == {} and dv3 == "assente")

    # --da: appaiare i due rami sulle stesse realizzazioni
    finti = [(i, None) for i in range(300)]
    chk("--da 200 con --n-mock 100 seleziona 200..299",
        [i for i, _ in [(i, p) for i, p in finti if i >= 200][:100]]
        == list(range(200, 300)))
    chk("--da 0 seleziona 0..99, che NON sono le stesse realizzazioni",
        [i for i, _ in [(i, p) for i, p in finti if i >= 0][:100]]
        == list(range(100)))

    # il denominatore: quello del Paper 1, non la SEM
    chk("sigma_Delta quotata dal Paper 1 e' 250.5", SIGMA_DELTA_V1_NGC == 250.5)
    # Il paper quota 6.8, una cifra decimale: il confronto va fatto ALLA
    # PRECISIONE DELLA CIFRA QUOTATA, non piu' stretto (errore 23 del registro).
    chk("e 1710.5 su 250.5 da' il 6.8 del paper, alla cifra quotata",
        round(1710.5 / SIGMA_DELTA_V1_NGC, 1) == 6.8,
        1710.5 / SIGMA_DELTA_V1_NGC)
    chk("mentre 1710.5 sulla SEM 40.6 darebbe 42.1: un altro numero",
        abs(1710.5 / 40.62 - 42.1) < 0.1)
    chk("sigma_Delta e' minore di sigma(N_H1), come il paper registra",
        SIGMA_DELTA_V1_NGC < SIGMA_NH1_NGC)
    # il rumore di fase si DERIVA: e' diverso nei due emisferi
    chk("il rumore di fase di NGC, derivato, e' il 157 del paper",
        round(157.0098, 0) == RUMORE_FASI_NGC_ATTESO)
    chk("ma in SGC vale 113.14, e usare 157 darebbe varianza NEGATIVA",
        153.27 ** 2 - 157.0 ** 2 < 0 < 153.27 ** 2 - 113.14 ** 2)
    chk("col valore giusto SGC v1 da' 103.4 e 5.4 sigma",
        abs(np.sqrt(153.27 ** 2 - 113.14 ** 2) - 103.4) < 0.1
        and abs(561.72 / np.sqrt(153.27 ** 2 - 113.14 ** 2) - 5.43) < 0.02)
    chk("una varianza negativa NON produce un numero, produce None",
        (lambda v: np.sqrt(v) if v > 0 else None)(153.27**2 - 157.0**2) is None)
    corr = np.sqrt(SIGMA_DELTA_V1_NGC**2 - RUMORE_FASI_NGC_ATTESO**2)
    chk("togliendo il rumore di fase in quadratura si ottiene 195.2",
        abs(corr - 195.2) < 0.3, corr)
    chk("e la significativita' salirebbe a 8.8, che il paper NON adotta",
        round(1710.5 / corr, 1) == 8.8, 1710.5 / corr)

    # Delta_N e il rango, sulla logica
    dN = np.array([100.0, 110.0, 90.0, 105.0])
    chk("il rango conta i mock che guadagnano quanto DESI o piu'",
        int((dN >= 200.0).sum()) == 0 and int((dN >= 95.0).sum()) == 3)
    chk("e si scrive come 1/(n+1) quando nessuno arriva a DESI",
        "%d/%d" % (0 + 1, dN.size + 1) == "1/5")

    # statistiche
    st = statistiche([1.0, 2.0, 3.0])
    chk("sd con ddof=1", abs(st["std"] - 1.0) < 1e-12)
    chk("SEM = sd/sqrt(n)", abs(st["sem"] - 1.0 / np.sqrt(3)) < 1e-12)

    # la frazione spettrale, sui casi limite dichiarati da n10
    def frazione(mock_or, desi_or, mock_pr, desi_pr):
        return (mock_pr - desi_pr) / (mock_or - desi_or)
    chk("se la randomizzazione non cambia nulla la frazione e' 1",
        abs(frazione(35436., 28256., 35436., 28256.) - 1.0) < 1e-12)
    chk("se il deficit svanisce la frazione e' 0",
        abs(frazione(35436., 28256., 30000., 30000.) - 0.0) < 1e-12)
    chk("e il residuo e' il deficit meno la parte spettrale",
        abs((35436. - 28256.) - (35436. - 28256.) * 0.0
            - (35436. - 28256.)) < 1e-9)

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("corri")
    c.add_argument("--root", default=ROOT_DEFAULT)
    c.add_argument("--region", choices=["NGC", "SGC"], required=True)
    c.add_argument("--versione", choices=["v1", "v2"], required=True)
    c.add_argument("--n-desi", dest="n_desi", type=int, default=50)
    c.add_argument("--n-mock", dest="n_mock", type=int, default=100)
    c.add_argument("--da", type=int, default=0,
                   help="indice di partenza dei mock. Serve ad APPAIARE i due "
                        "rami sulle stesse realizzazioni: v1 NGC parte da 200 "
                        "perche' i cubi congelati esistono da li'")
    c.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "corri":
        return corri(a.root, a.region, a.versione, a.n_desi, a.n_mock, a.da,
                     a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_d6_incertezze.py — le quantita' di D6 con la loro dispersione, su due emisferi.

Nessun modello nuovo. Le stesse regressioni di `paper2_compD_nonlinear.py`, importate da
li' e non riscritte, con quattro aggiunte:

  1. CANCELLO DI RIPRODUZIONE. Con k=5 e seed=0 i valori NGC congelati del 26 ago devono
     tornare a rel <= 1e-12. Se non tornano, il problema e' la partizione e ci si ferma.
  2. CV RIPETUTA E APPAIATA. R ripetizioni a semi dichiarati 0..R-1. Tutti i modelli
     vedono LE STESSE partizioni, quindi le differenze si misurano appaiate: la
     dispersione appaiata e' il denominatore giusto per «A supera B», esattamente come
     la SEM appaiata lo e' per i termini del budget (5.1, regola R1).
  3. LE SOGLIE CON IL LORO MARGINE. Q1, Q2, Q3, Q4 e Q5 sono predizioni dichiarate con
     una soglia; qui ognuna esce col margine misurato in unita' della propria dispersione.
     Una soglia attraversata senza l'incertezza della quantita' testata e' l'errore
     della P1 di D3, e Q1 e' a un capello dalla sua.
  4. LE BASI DICHIARATE. La quota di divario chiusa da P(k) si riporta sotto ENTRAMBE
     le basi, etichettate, mai come un «%» nudo:
       - divario dei PARAMETRI:  0.698 - R2cv(lineare)
       - divario TOTALE residuo: 0.832 - R2cv(lineare)   <- il tetto di un predittore
                                                            misurato sulla realizzazione
     e col numeratore coerente: R2 validato, non grezzo.

E due diagnostiche che la chiusura della provenienza ha reso ponibili:

  D  IL DOPPIO LOGARITMO. Il cache e' gia' log10 P(k) (record 62), e il consumatore fa
     `np.log(np.clip(Pk, ...))`: il test B gira su **ln(log10 P)**. La PCA non e'
     invariante per trasformazioni non lineari, quindi la base delle componenti non e'
     quella dichiarata. Qui B si calcola in ENTRAMBE le forme e si riportano le due.
     Non si corregge in silenzio: si dichiara.
  G  IL SECONDO JOIN POSIZIONALE. `P = raw[:n, :]` unisce i parametri a N_H1 per
     posizione, come pk_matrix era unito ai parametri. Stessa classe, stesso test:
     nullo per permutazione sul modello lineare, con la regola dichiarata prima.

Uso:
    python src\\paper2_d6_incertezze.py selftest
    python src\\paper2_d6_incertezze.py misura --region NGC ^
        --params data\\raw\\quijote\\3D_cubes\\latin_hypercube_nwLH\\latin_hypercube_nwLH_params.txt ^
        --pk results\\phase7_pk_nwlh_cache.npz --out results\\paper2\\d6_incertezze.jsonl
    (poi la stessa riga con --region SGC)

Sola lettura sugli ingressi. JSONL append-only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_compD_nonlinear import (  # noqa: E402
    FROZEN, TOL, CEIL_PARAMS, CEIL_MEASURED,
    design, pca, r2_fit, r2_cv, load_nh1, append_atomic,
)

VERSIONE = "1.0"
GRIGLIA_NC = (1, 2, 3, 5, 8, 12, 20, 30)
RIPETIZIONI = 20
K_FOLD = 5
NPERM_JOIN = 200

# Soglie dichiarate in origine, con il verso del confronto.
SOGLIE = {
    "Q1_quadrati": {"soglia": 0.05, "verso": "<", "quantita": "gain_quad"},
    "Q2_interazioni": {"soglia": 0.03, "verso": "<", "quantita": "gain_int"},
    "Q3_B_sopra_mezzo": {"soglia": 0.50, "verso": ">", "quantita": "B_best"},
    "Q4_meta_divario": {"soglia": 0.50, "verso": ">", "quantita": "C_frac_parametri"},
    # Q5 CONDIVIDE la quantita' di Q3 e differisce solo per soglia e verso: non e' una
    # duplicazione da ripulire. La soglia non e' scritta qui come numero, e' CEIL_MEASURED
    # importato: se il tetto cambia, la soglia lo segue invece di restare indietro.
    "Q5_sotto_il_tetto": {"soglia": CEIL_MEASURED, "verso": "<", "quantita": "B_best"},
}

# I valori del record del 26 ago 2026, NGC, k=5 seed=0. Il cancello di riproduzione.
CONGELATO_NGC = {
    "A_order1_r2": 0.26057742756056634, "A_order1_r2cv": 0.2553779090502538,
    "A_order2_r2": 0.3166791498649345, "A_order2_r2cv": 0.30663283157044585,
    "A_order3_r2": 0.3891448689369257, "A_order3_r2cv": 0.36120602344202934,
    "B_ncomp12_r2cv": 0.32626147077818934, "B_best_ncomp": 12,
    "C_resid_r2cv": 0.1285015701231932, "C_gap_closed_frac": 0.21466892163619317,
}
REL_RIPRODUZIONE = 1e-12


# --------------------------------------------------------------------- utili

def media_sd(v):
    a = np.asarray(v, float)
    return float(a.mean()), float(a.std(ddof=1)) if a.size > 1 else 0.0


def appaiata(a, b):
    """Differenza media e dispersione APPAIATA fra due serie sulle stesse partizioni."""
    d = np.asarray(a, float) - np.asarray(b, float)
    sd = float(d.std(ddof=1)) if d.size > 1 else 0.0
    return float(d.mean()), sd, (float(d.mean()) / sd if sd > 0 else float("inf"))


def margine(valore, sd, soglia, verso):
    """Di quante sigma il valore sta dalla propria soglia, e da che parte."""
    scarto = (valore - soglia) if verso == ">" else (soglia - valore)
    esito = "confermata" if scarto > 0 else "SMENTITA"
    sigma = (abs(valore - soglia) / sd) if sd > 0 else float("inf")
    return {"valore": float(valore), "sd": float(sd), "soglia": float(soglia),
            "verso": verso, "esito": esito, "margine_in_sigma": float(sigma),
            "decidibile": bool(sigma >= 3.0)}


def carica_pk(path, n):
    """Il cache, ora che la provenienza e' chiusa: chiave dichiarata, niente indovinelli.

    Il dtype si lascia com'e' sul disco (float32). Promuoverlo a float64 sposta l'R2 di
    B di ~4e-8 e fa fallire il cancello di riproduzione: il percorso di agosto calcola
    log, PCA e SVD in float32, e riprodurre vuol dire riprodurre anche quello.
    """
    with np.load(path, allow_pickle=False) as z:
        if "pk_matrix" not in z.files:
            raise SystemExit("FALLIMENTO: 'pk_matrix' assente in %s (chiavi: %s)"
                             % (path, list(z.files)))
        M = np.asarray(z["pk_matrix"])
    if M.shape[0] != n:
        raise SystemExit("FALLIMENTO: %d righe nel cache contro %d realizzazioni" % (M.shape[0], n))
    return M


# ------------------------------------------------------------------- misura

def serie_ripetute(y, X, ripetizioni, k):
    return [r2_cv(y, X, k=k, seed=s) for s in range(ripetizioni)]


def misura(region, params_path, pk_path, nh1_path, ripetizioni, k, nperm):
    f = FROZEN[region]
    y = load_nh1(nh1_path or f["path"])
    n = len(y)
    m, s = float(y.mean()), float(y.std(ddof=1))
    if abs(m - f["mean"]) > TOL or abs(s - f["sd"]) > TOL:
        raise SystemExit("FALLIMENTO cancello N_H1: media %.4f (atteso %.3f), sd %.4f (atteso %.3f)"
                         % (m, f["mean"], s, f["sd"]))
    raw = np.genfromtxt(params_path)
    P = raw[:n, :]
    if P.shape[0] != n:
        raise SystemExit("FALLIMENTO: %d righe di parametri contro %d realizzazioni" % (P.shape[0], n))

    rec = {
        "schema": "paper2_d6_incertezze_v2", "versione": VERSIONE, "region": region, "n": n,
        "nota_schema_v2": (
            "v2 differisce da v1 in un solo punto: rec['soglie'] contiene anche "
            "Q5_sotto_il_tetto, la quinta predizione dichiarata di D6, che v1 non calcolava "
            "perche' SOGLIE ne conteneva quattro. Il margine di Q5 e' GIA' registrato dal "
            "record 66 del ledger e da results/paper2/q5_margine.jsonl: un valore prodotto "
            "qui NON e' una seconda misura indipendente, e se differisce da quello e' una "
            "discordanza da spiegare, non un secondo risultato. Tutto il resto e' invariato."),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "k_fold": int(k), "ripetizioni": int(ripetizioni), "semi": [0, int(ripetizioni) - 1],
        "ceil_params": CEIL_PARAMS, "ceil_measured": CEIL_MEASURED,
        "ingressi": {"nh1": nh1_path or f["path"], "params": params_path, "pk": pk_path},
    }

    # --- A, con il seme 0 per il cancello e poi ripetuto
    X = {o: design(P, o) for o in (1, 2, 3)}
    seme0 = {o: {"r2": r2_fit(y, X[o]), "r2_cv": r2_cv(y, X[o], k=5, seed=0)} for o in (1, 2, 3)}
    serie_A = {o: serie_ripetute(y, X[o], ripetizioni, k) for o in (1, 2, 3)}
    rec["A"] = {}
    for o in (1, 2, 3):
        mu, sd = media_sd(serie_A[o])
        rec["A"]["order%d" % o] = {"termini": int(X[o].shape[1]), "r2_seed0": seme0[o]["r2"],
                                   "r2cv_seed0": seme0[o]["r2_cv"], "r2cv_media": mu, "r2cv_sd": sd}

    d, sdp, _ = appaiata(serie_A[2], serie_A[1])
    rec["A"]["gain_quad"] = {"media": d, "sd_appaiata": sdp}
    d2, sdp2, _ = appaiata(serie_A[3], serie_A[2])
    rec["A"]["gain_int"] = {"media": d2, "sd_appaiata": sdp2}
    rec["A"]["non_spiegato_su_tetto_parametri"] = {
        "frazione": float((CEIL_PARAMS - rec["A"]["order3"]["r2cv_media"]) / CEIL_PARAMS),
        "sd": float(rec["A"]["order3"]["r2cv_sd"] / CEIL_PARAMS),
        "base": "percentuale della varianza COSMOLOGICA (tetto 0.698), non della totale",
    }

    # --- G: il secondo join posizionale, con la regola dichiarata prima
    rng = np.random.default_rng(20260912)
    oss = seme0[1]["r2_cv"]
    nulli = [r2_cv(y[rng.permutation(n)], X[1], k=5, seed=0) for _ in range(nperm)]
    rec["G_join_parametri_NH1"] = {
        "regola": "sostenuto solo se l'R2cv osservato sta fuori dall'intero supporto del nullo",
        "r2cv_osservato": float(oss), "nullo_max": float(np.max(nulli)),
        "nperm": int(nperm), "sostenuto": bool(oss > np.max(nulli)),
        "nota": "join posizionale come quello di pk_matrix: qui il segnale stesso lo sostiene",
    }

    # --- B, nelle due forme, e C
    if pk_path and os.path.exists(pk_path):
        M = carica_pk(pk_path, n)
        rec["dtype_cache"] = str(M.dtype)
        forme = {
            "log10P_come_nel_cache": M,
            "ln_di_log10P_come_nel_codice": np.log(np.clip(M, 1e-30, None)),
        }
        rec["B"] = {}
        serie_B = {}
        for nome, L in forme.items():
            rec["B"][nome] = {}
            serie_B[nome] = {}
            for nc in [c for c in GRIGLIA_NC if c < min(L.shape)]:
                C, _ = pca(L, nc)
                serie = serie_ripetute(y, C, ripetizioni, k)
                serie_B[nome][nc] = serie
                mu, sd = media_sd(serie)
                rec["B"][nome]["ncomp%d" % nc] = {
                    "r2cv_media": mu, "r2cv_sd": sd,
                    "r2cv_seed0": r2_cv(y, C, k=5, seed=0), "r2_seed0": r2_fit(y, C)}
            best = max(serie_B[nome], key=lambda c: media_sd(serie_B[nome][c])[0])
            mu, sd = media_sd(serie_B[nome][best])
            rec["B"][nome]["migliore"] = {
                "ncomp": int(best), "r2cv_media": mu, "r2cv_sd": sd,
                "quota_del_tetto_0832": float(mu / CEIL_MEASURED),
                "nota_selezione": "il massimo e' scelto sulla MEDIA delle ripetizioni, non su una sola",
            }
        rec["B"]["differenza_fra_le_due_forme"] = {
            "media": media_sd(serie_B["log10P_come_nel_cache"][
                rec["B"]["log10P_come_nel_cache"]["migliore"]["ncomp"]])[0]
            - media_sd(serie_B["ln_di_log10P_come_nel_codice"][
                rec["B"]["ln_di_log10P_come_nel_codice"]["migliore"]["ncomp"]])[0],
            "nota": "il cache e' gia' log10 P: il codice applica un secondo logaritmo",
        }

        nome_rif = "ln_di_log10P_come_nel_codice"
        best_rif = rec["B"][nome_rif]["migliore"]["ncomp"]
        d3, sdp3, sig3 = appaiata(serie_A[3], serie_B[nome_rif][best_rif])
        rec["confronto_A3_vs_B"] = {
            "differenza_media": d3, "sd_appaiata": sdp3, "in_sigma": sig3,
            "forma_di_B": nome_rif,
            "nota_tetti": ("A sta sotto 0.698 e B sotto 0.832: la differenza grezza NON e' "
                           "un confronto di quote. Le quote sono nei due campi dedicati."),
            "quota_A3": float(rec["A"]["order3"]["r2cv_media"] / CEIL_PARAMS),
            "quota_B": float(rec["B"][nome_rif]["migliore"]["r2cv_media"] / CEIL_MEASURED),
        }

        # --- C, con le basi dichiarate e il numeratore coerente
        Xlin = X[1]
        A_ = np.column_stack([np.ones(n), Xlin])
        beta, *_ = np.linalg.lstsq(A_, y, rcond=None)
        resid = y - A_ @ beta
        C, _ = pca(forme[nome_rif], best_rif)
        serie_C = serie_ripetute(resid, C, ripetizioni, k)
        muC, sdC = media_sd(serie_C)
        r2cv1 = rec["A"]["order1"]["r2cv_media"]
        var_frac_grezza = float((resid ** 2).sum() / ((y - y.mean()) ** 2).sum())
        var_frac_cv = 1.0 - r2cv1
        chiusa_cv = muC * var_frac_cv
        rec["C"] = {
            "resid_r2cv_media": muC, "resid_r2cv_sd": sdC,
            "varianza_residua_grezza": var_frac_grezza,
            "varianza_residua_cv": var_frac_cv,
            "base_divario_parametri": {
                "divario": float(CEIL_PARAMS - r2cv1),
                "frazione_chiusa": float(chiusa_cv / (CEIL_PARAMS - r2cv1)),
                "sd": float(sdC * var_frac_cv / (CEIL_PARAMS - r2cv1)),
                "significato": "quanta parte del divario dei PARAMETRI (tetto 0.698) chiude P(k)",
            },
            "base_divario_totale": {
                "divario": float(CEIL_MEASURED - r2cv1),
                "frazione_chiusa": float(chiusa_cv / (CEIL_MEASURED - r2cv1)),
                "sd": float(sdC * var_frac_cv / (CEIL_MEASURED - r2cv1)),
                "significato": ("quanta parte di cio' che resta non spiegato, fino al tetto di un "
                                "predittore MISURATO (0.832), spiega P(k)"),
            },
            "nota_sul_record_di_agosto": ("C_gap_closed_frac usava il numeratore GREZZO "
                                          "(1 - R2 in-sample) e il denominatore VALIDATO, con il "
                                          "tetto 0.698 per un predittore il cui tetto e' 0.832"),
        }

    # --- le soglie col loro margine
    q = {}
    q["Q1_quadrati"] = margine(rec["A"]["gain_quad"]["media"], rec["A"]["gain_quad"]["sd_appaiata"],
                               0.05, "<")
    q["Q2_interazioni"] = margine(rec["A"]["gain_int"]["media"], rec["A"]["gain_int"]["sd_appaiata"],
                                  0.03, "<")
    if "B" in rec:
        mg = rec["B"]["ln_di_log10P_come_nel_codice"]["migliore"]
        q["Q3_B_sopra_mezzo"] = margine(mg["r2cv_media"], mg["r2cv_sd"], 0.50, ">")
        # STESSA quantita' di Q3, soglia e verso diversi: Q5 chiede che resti SOTTO il
        # tetto dei predittori misurati. Soglia e verso si leggono da SOGLIE, non si
        # riscrivono qui.
        q["Q5_sotto_il_tetto"] = margine(mg["r2cv_media"], mg["r2cv_sd"],
                                         SOGLIE["Q5_sotto_il_tetto"]["soglia"],
                                         SOGLIE["Q5_sotto_il_tetto"]["verso"])
        cpar = rec["C"]["base_divario_parametri"]
        q["Q4_meta_divario"] = margine(cpar["frazione_chiusa"], cpar["sd"], 0.50, ">")
    rec["soglie"] = q
    rec["regola_di_arresto_A"] = {
        "dichiarata_prima": True,
        "testo": ("la sequenza e' satura quando R2cv scende sotto il massimo di piu' della "
                  "dispersione appaiata fra ripetizioni; la stima e' il massimo. Finche' sale, "
                  "il non spiegato resta un LIMITE SUPERIORE, e va scritto con la sua sd"),
        "satura": False if rec["A"]["gain_int"]["media"] > 0 else True,
    }
    return rec


# ------------------------------------------------------------------ cancello

def cancello_riproduzione(rec_calcolato, y, X, forme=None, best_nc=12):
    """I valori NGC di agosto devono tornare con k=5, seed=0."""
    esiti = []
    for chiave, atteso in (("A_order1_r2", "order1"), ("A_order2_r2", "order2"),
                           ("A_order3_r2", "order3")):
        got = rec_calcolato["A"][atteso]["r2_seed0"]
        rel = abs(got - CONGELATO_NGC[chiave]) / abs(CONGELATO_NGC[chiave])
        esiti.append((rel <= REL_RIPRODUZIONE, "%s rel=%.2e" % (chiave, rel)))
    for chiave, atteso in (("A_order1_r2cv", "order1"), ("A_order2_r2cv", "order2"),
                           ("A_order3_r2cv", "order3")):
        got = rec_calcolato["A"][atteso]["r2cv_seed0"]
        rel = abs(got - CONGELATO_NGC[chiave]) / abs(CONGELATO_NGC[chiave])
        esiti.append((rel <= REL_RIPRODUZIONE, "%s rel=%.2e" % (chiave, rel)))
    if "B" in rec_calcolato:
        got = rec_calcolato["B"]["ln_di_log10P_come_nel_codice"].get("ncomp12", {}).get("r2cv_seed0")
        if got is not None:
            rel = abs(got - CONGELATO_NGC["B_ncomp12_r2cv"]) / CONGELATO_NGC["B_ncomp12_r2cv"]
            esiti.append((rel <= REL_RIPRODUZIONE, "B_ncomp12_r2cv rel=%.2e" % rel))
    return esiti


# ------------------------------------------------------------------- comandi

def comando_misura(a):
    rec = misura(a.region, a.params, a.pk, a.nh1, a.ripetizioni, a.k, a.nperm)

    if a.region == "NGC":
        esiti = cancello_riproduzione(rec, None, None)
        rec["cancello_riproduzione"] = {"esiti": [n for _, n in esiti],
                                        "superato": bool(all(c for c, _ in esiti))}
        print("cancello di riproduzione (k=5, seed=0, contro il record del 26 ago):")
        for c, nome in esiti:
            print("  %s %s" % ("OK " if c else "KO ", nome))
        if not rec["cancello_riproduzione"]["superato"]:
            print("\nFALLIMENTO: i valori congelati non tornano. La partizione o l'ingresso "
                  "sono cambiati: fermarsi qui.", file=sys.stderr)
            return 3
    else:
        rec["cancello_riproduzione"] = {"superato": None,
                                        "nota": "nessun valore congelato per SGC: primo run di D6 al sud"}
        print("nessun riferimento congelato per SGC: questo e' il primo run di D6 al sud.")

    print(json.dumps(rec, ensure_ascii=False, indent=2))
    if a.out:
        append_atomic(a.out, rec)
        print("\n[log] record appeso a %s" % a.out, file=sys.stderr)

    print("\n== SOGLIE, COL MARGINE ==", file=sys.stderr)
    for nome, d in rec["soglie"].items():
        print("  %-20s %s  %.4f contro %.6f  -> %.1f sigma  %s"
              % (nome, d["esito"], d["valore"], d["soglia"], d["margine_in_sigma"],
                 "" if d["decidibile"] else "<-- NON DECIDIBILE"), file=sys.stderr)
    return 0


def selftest():
    ok = 0
    tot = 0

    def check(cond, nome):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok]   %s" % nome)
        else:
            print("  [FAIL] %s" % nome)

    print("selftest paper2_d6_incertezze v%s" % VERSIONE)
    rng = np.random.default_rng(4)
    n = 1200
    P = rng.uniform(0.1, 0.9, size=(n, 7))
    # Segnale con una parte quadratica e una di interazione davvero presenti: serve a
    # verificare che la sequenza le veda, non a imitare i dati veri.
    y = (300.0 + 40 * P[:, 4] + 25 * P[:, 0] ** 2 + 15 * P[:, 3] * P[:, 4]
         + rng.normal(scale=2.0, size=n))

    # --- funzioni pure
    mu, sd = media_sd([1.0, 2.0, 3.0])
    check(abs(mu - 2.0) < 1e-12 and abs(sd - 1.0) < 1e-12, "media_sd")
    d, s_, sig = appaiata([1.1, 1.2, 1.3], [1.0, 1.1, 1.2])
    check(abs(d - 0.1) < 1e-12 and s_ < 1e-12, "appaiata: differenza costante -> sd nulla")
    a1 = rng.normal(size=50)
    check(appaiata(a1 + 0.3, a1)[1] < np.std(a1, ddof=1),
          "DIFETTO: la sd appaiata e' piu' stretta di quella marginale")
    m = margine(0.0513, 0.004, 0.05, "<")
    check(m["esito"] == "SMENTITA" and not m["decidibile"],
          "DIFETTO: soglia superata di 0.3 sigma -> non decidibile")
    m2 = margine(0.0546, 0.004, 0.03, "<")
    check(m2["esito"] == "SMENTITA" and m2["decidibile"], "soglia superata di 6 sigma -> decidibile")
    m3 = margine(0.33, 0.01, 0.50, ">")
    check(m3["esito"] == "SMENTITA", "verso '>' letto correttamente")

    # --- CV ripetuta
    X1, X3 = design(P, 1), design(P, 3)
    s1 = serie_ripetute(y, X1, 6, 5)
    s3 = serie_ripetute(y, X3, 6, 5)
    check(len(set(s1)) > 1, "ripetizioni a semi diversi danno valori diversi")
    check(media_sd(s1)[1] > 0, "la dispersione fra ripetizioni non e' zero")
    check(media_sd(s3)[0] > media_sd(s1)[0], "l'ordine 3 spiega piu' del lineare, sul vero segnale")
    check(serie_ripetute(y, X1, 3, 5) == s1[:3], "stessi semi -> stessi valori (determinismo)")

    # --- il join, con e senza permutazione
    oss = r2_cv(y, X1, k=5, seed=0)
    nulli = [r2_cv(y[np.random.default_rng(i).permutation(n)], X1, k=5, seed=0) for i in range(30)]
    check(oss > max(nulli), "join corretto: fuori dal supporto del nullo")
    yp = y[np.random.default_rng(99).permutation(n)]
    check(r2_cv(yp, X1, k=5, seed=0) <= max(nulli) + 1e-9,
          "DIFETTO: join permutato: dentro il nullo")

    # --- il doppio logaritmo cambia la base della PCA
    M = 3.0 + rng.normal(scale=0.4, size=(n, 20)) + P[:, 4:5] * 2.0
    C1, _ = pca(M, 5)
    C2, _ = pca(np.log(np.clip(M, 1e-30, None)), 5)
    check(not np.allclose(np.abs(C1), np.abs(C2)),
          "DIFETTO: PCA su log10 P e su ln(log10 P) NON danno la stessa base")

    # --- il dtype: la causa del rel 4.4e-08 sul cancello
    M32 = (3.0 + rng.normal(scale=0.4, size=(n, 20))).astype(np.float32)
    C32, _ = pca(M32, 5)
    C64, _ = pca(M32.astype(np.float64), 5)
    r32, r64 = r2_cv(y, C32, k=5, seed=0), r2_cv(y, C64, k=5, seed=0)
    check(r32 != r64 and abs(r32 - r64) < 1e-6,
          "DIFETTO: float32 e float64 danno R2 diversi a ~1e-8: il percorso congelato e' float32")

    # --- le due basi di C
    r2cv1, resid_r2, varf = 0.2554, 0.1285, 0.7446
    f_par = resid_r2 * varf / (CEIL_PARAMS - r2cv1)
    f_tot = resid_r2 * varf / (CEIL_MEASURED - r2cv1)
    check(f_tot < f_par, "DIFETTO: sulla base 0.832 la quota chiusa e' PIU' PICCOLA")
    check(abs(f_par - 0.2162) < 5e-4 and abs(f_tot - 0.1659) < 5e-4,
          "le due quote valgono 21.6 % e 16.6 %")

    # --- il cancello di riproduzione respinge un valore cambiato
    finto = {"A": {"order1": {"r2_seed0": CONGELATO_NGC["A_order1_r2"],
                              "r2cv_seed0": CONGELATO_NGC["A_order1_r2cv"]},
                   "order2": {"r2_seed0": CONGELATO_NGC["A_order2_r2"],
                              "r2cv_seed0": CONGELATO_NGC["A_order2_r2cv"]},
                   "order3": {"r2_seed0": CONGELATO_NGC["A_order3_r2"],
                              "r2cv_seed0": CONGELATO_NGC["A_order3_r2cv"]}}}
    check(all(c for c, _ in cancello_riproduzione(finto, None, None)),
          "cancello: i valori congelati passano")
    finto["A"]["order3"]["r2cv_seed0"] *= 1.000001
    check(not all(c for c, _ in cancello_riproduzione(finto, None, None)),
          "DIFETTO: uno scarto di 1e-6 fa fallire il cancello")

    print("\nselftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    m = sub.add_parser("misura")
    m.add_argument("--region", required=True, choices=["NGC", "SGC"])
    m.add_argument("--params", required=True)
    m.add_argument("--pk", default="results/phase7_pk_nwlh_cache.npz")
    m.add_argument("--nh1", default=None)
    m.add_argument("--out", default=None)
    m.add_argument("--ripetizioni", type=int, default=RIPETIZIONI)
    m.add_argument("--k", type=int, default=K_FOLD)
    m.add_argument("--nperm", type=int, default=NPERM_JOIN)
    a = p.parse_args(argv)
    return selftest() if a.cmd == "selftest" else comando_misura(a)


if __name__ == "__main__":
    raise SystemExit(main())

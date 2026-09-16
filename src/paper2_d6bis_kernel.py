#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_d6bis_kernel.py — D6-bis: la stessa classe di modelli ai due lati, e due denominatori.

PERCHE' ESISTE
--------------
Il confronto di D6 non e' un confronto di informazione. Da una parte un polinomio di 35
termini nei sette parametri; dall'altra una regressione LINEARE su 12 componenti principali
di P(k). Se il secondo resta indietro, cio' che si e' misurato e' la differenza fra due
classi di modelli, non fra due contenuti informativi — e solo la seconda lettura
autorizzerebbe «la parte non spiegata e' oltre il due punti».

Qui i due lati ricevono lo STESSO stimatore: kernel ridge con nucleo gaussiano, che e' la
forma piu' semplice di «funzione qualsiasi, con la flessibilita' scelta dai dati».

  P   i sette parametri          -> tetto 0.698 (predittori parametrici)
  K   log10 P(k), 110 bin        -> tetto 0.832 (misurati sulla stessa realizzazione)
  PK  i due insiemi assieme      -> tetto 0.832

I DUE DENOMINATORI, E PERCHE' NON SONO LO STESSO
------------------------------------------------
Lo strumento precedente riportava una sola dispersione: quella fra PARTIZIONI della stessa
coorte di 2000 realizzazioni. Ha due difetti, e il secondo e' grave.

  1. si restringe con le ripetizioni. Un margine «in sigma» calcolato cosi' si puo'
     fabbricare facendo girare piu' a lungo lo strumento;
  2. non contiene l'incertezza di avere 2000 realizzazioni e non altre, che e' quella di
     cui un referee chiede conto, e che NON si restringe ripetendo la CV.

Quindi si riportano entrambe, etichettate, mai mescolate:

  sd_partizione  ripetizioni della CV a semi dichiarati, coorte fissa
  sd_ensemble    bootstrap sulle 2000 realizzazioni, una CV per risorsa; contiene
                 entrambe le sorgenti ed e' quella su cui si misura un margine da soglia

Il bootstrap assegna i fold PER REALIZZAZIONE DI ORIGINE: tutte le copie di una
realizzazione finiscono nello stesso fold, altrimenti la stessa riga starebbe in
addestramento e in prova e l'R2 sarebbe gonfio. Il selftest lo verifica.

SCELTE DICHIARATE PRIMA
-----------------------
  - griglia di iperparametri fissa (LUNGHEZZE x ALPHA), dichiarata qui sotto;
  - la selezione e' il massimo sulla griglia della media fra ripetizioni, ed e'
    OTTIMISTA: e' la stessa scelta gia' fatta per il numero di componenti di B, quindi
    coerente con cio' che esiste, non una concessione nuova;
  - le colonne si standardizzano sull'intera coorte: e' informazione sul disegno LH, non
    su y. Dichiarato, non nascosto;
  - nel blocco PK ciascun gruppo di colonne e' diviso per la radice del proprio numero di
    colonne, altrimenti i 110 bin schiaccerebbero i 7 parametri nella distanza.

Uso:
    python src\\paper2_d6bis_kernel.py selftest
    python src\\paper2_d6bis_kernel.py griglia --region NGC --params ... --pk ...
    python src\\paper2_d6bis_kernel.py misura  --region NGC --params ... --pk ... --out results\\paper2\\d6bis.jsonl
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
    FROZEN, TOL, CEIL_PARAMS, CEIL_MEASURED, design, r2_cv, load_nh1, append_atomic,
)

VERSIONE = "1.0"
# Griglia v1, dichiarata prima del primo run del 13 set.
GRIGLIA_V1 = {"lunghezze": (0.25, 0.5, 1.0, 2.0, 4.0), "alpha": (1e-4, 1e-3, 1e-2, 1e-1)}
# Griglia v2: estesa PERCHE' il massimo cadeva sul bordo in tutti e tre gli ingressi
# (P a alpha=1e-4, K e PK a lunghezza=4.0) e in quel caso a scegliere e' la griglia, non i
# dati. L'estensione e' la risposta che lo strumento stesso prescriveva, non una ricerca
# di un numero migliore: si registra qui insieme alla ragione.
LUNGHEZZE = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)   # in unita' della mediana delle distanze
ALPHA = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1)
K_FOLD = 5
RIP_GRIGLIA = 5
RIPETIZIONI = 20
BOOTSTRAP = 100
TETTI = {"P": CEIL_PARAMS, "K": CEIL_MEASURED, "PK": CEIL_MEASURED}


# ------------------------------------------------------------------- nucleo

def zscore_colonne(X):
    m, s = X.mean(0), X.std(0, ddof=0)
    return (X - m) / np.where(s > 0, s, 1.0)


def blocchi(*parti):
    """Ogni blocco z-scorato e diviso per sqrt(n_colonne), cosi' nessuno domina la distanza."""
    out = []
    for P in parti:
        Z = zscore_colonne(np.asarray(P, dtype=np.float64))
        out.append(Z / np.sqrt(Z.shape[1]))
    return np.column_stack(out)


def dist2(X):
    q = (X ** 2).sum(1)
    D = q[:, None] + q[None, :] - 2.0 * (X @ X.T)
    np.maximum(D, 0.0, out=D)
    return D


def fold_di(n, k, seed):
    """Un fold per ogni realizzazione di origine, dalla partizione di quel seme."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    f = np.empty(n, dtype=np.int64)
    for j, parte in enumerate(np.array_split(idx, k)):
        f[parte] = j
    return f


def r2_krr(y, K, fold, k, alpha, righe=None):
    """R2 fuori campione con kernel ridge. La regolarizzazione si applica alla diagonale
    del blocco RICAMPIONATO, non a quella di K: con le ripetizioni del bootstrap due righe
    identiche renderebbero il blocco singolare, e l'alpha su K non basterebbe.

    `righe` sono gli indici di origine da usare (per il bootstrap, con ripetizioni):
    i fold seguono la realizzazione di ORIGINE, non la copia.
    """
    if righe is None:
        righe = np.arange(len(y))
    yv = y[righe]
    fv = fold[righe]
    pred = np.empty(len(righe))
    for j in range(k):
        te = np.where(fv == j)[0]
        tr = np.where(fv != j)[0]
        if te.size == 0 or tr.size < 2:
            return float("nan")
        itr, ite = righe[tr], righe[te]
        A = K[np.ix_(itr, itr)].copy()
        A[np.diag_indices_from(A)] += alpha
        mu = yv[tr].mean()
        try:
            a = np.linalg.solve(A, yv[tr] - mu)
        except np.linalg.LinAlgError:
            return float("nan")
        pred[te] = K[np.ix_(ite, itr)] @ a + mu
    r = yv - pred
    den = float(((yv - yv.mean()) ** 2).sum())
    return 1.0 - float(r @ r) / den if den > 0 else float("nan")


def costruisci_K(D2, lung, mediana):
    """Il nucleo puro. L'alpha entra al momento della soluzione, sul blocco ricampionato."""
    return np.exp(-D2 / (2.0 * (lung ** 2) * mediana))


# --------------------------------------------------------------- ingressi

def carica(region, params_path, pk_path, nh1_path):
    f = FROZEN[region]
    y = load_nh1(nh1_path or f["path"])
    n = len(y)
    m, s = float(y.mean()), float(y.std(ddof=1))
    if abs(m - f["mean"]) > TOL or abs(s - f["sd"]) > TOL:
        raise SystemExit("FALLIMENTO cancello N_H1: media %.4f sd %.4f" % (m, s))
    P = np.genfromtxt(params_path)[:n, :]
    with np.load(pk_path, allow_pickle=False) as z:
        if "pk_matrix" not in z.files:
            raise SystemExit("FALLIMENTO: 'pk_matrix' assente")
        M = np.asarray(z["pk_matrix"])          # float32, come sul disco: log10 P(k)
    if M.shape[0] != n or P.shape[0] != n:
        raise SystemExit("FALLIMENTO: righe discordanti")
    ingressi = {"P": blocchi(P), "K": blocchi(M), "PK": blocchi(P, M)}
    return y, P, M, ingressi, n


def prepara(ingressi):
    fuori = {}
    for nome, X in ingressi.items():
        D2 = dist2(X)
        med = float(np.median(D2[np.triu_indices_from(D2, k=1)]))
        fuori[nome] = (D2, med)
    return fuori


# ----------------------------------------------------------------- comandi

def scan_griglia(y, pre, k, rip):
    esiti = {}
    for nome, (D2, med) in pre.items():
        esiti[nome] = []
        for lung in LUNGHEZZE:
            for al in ALPHA:
                K = costruisci_K(D2, lung, med)
                v = [r2_krr(y, K, fold_di(len(y), k, s), k, al) for s in range(rip)]
                nan = int(np.count_nonzero(~np.isfinite(v)))
                esiti[nome].append({"lunghezza": lung, "alpha": al,
                                    "r2cv_media": float(np.nanmean(v)) if nan < len(v) else float("nan"),
                                    "r2cv_sd": float(np.nanstd(v, ddof=1)) if nan < len(v) - 1 else float("nan"),
                                    "non_risolti": nan})
        esiti[nome].sort(key=lambda d: (-d["r2cv_media"]) if np.isfinite(d["r2cv_media"]) else np.inf)
    return esiti


def e_bordo(d):
    return (d["lunghezza"] in (LUNGHEZZE[0], LUNGHEZZE[-1])
            or d["alpha"] in (ALPHA[0], ALPHA[-1]))


def sul_bordo_o_interno(lista, bordi, nome):
    """REGOLA DICHIARATA. Se il massimo sta sul bordo, a scegliere e' la griglia e non i
    dati. In quel caso si guarda il miglior punto INTERNO: se dista meno di una sd fra
    ripetizioni, e' indistinguibile e si usa quello, registrando lo scambio. Se dista di
    piu', il bordo resta e la griglia va estesa davvero.
    """
    best = lista[0]
    if not e_bordo(best):
        bordi[nome] = {"sul_bordo": False, "lunghezza": best["lunghezza"],
                       "alpha": best["alpha"], "nota": "massimo interno alla griglia"}
        return best
    interni = [d for d in lista if not e_bordo(d) and np.isfinite(d["r2cv_media"])]
    if interni and (best["r2cv_media"] - interni[0]["r2cv_media"]) < best["r2cv_sd"]:
        bordi[nome] = {
            "sul_bordo": True, "lunghezza": interni[0]["lunghezza"], "alpha": interni[0]["alpha"],
            "scambiato_con_interno": True,
            "bordo_scartato": {"lunghezza": best["lunghezza"], "alpha": best["alpha"],
                               "r2cv_media": best["r2cv_media"]},
            "distanza_in_sd": float((best["r2cv_media"] - interni[0]["r2cv_media"]) / best["r2cv_sd"]),
            "nota": ("il massimo stava sul bordo ma il miglior punto interno dista meno di una sd: "
                     "usato l'interno, per regola dichiarata")}
        return interni[0]
    bordi[nome] = {"sul_bordo": True, "lunghezza": best["lunghezza"], "alpha": best["alpha"],
                   "scambiato_con_interno": False,
                   "nota": "il massimo sta sul bordo e batte ogni punto interno di oltre una sd: "
                           "la griglia va estesa prima di leggere questo numero"}
    return best


def comando_griglia(a):
    y, _P, _M, ingressi, n = carica(a.region, a.params, a.pk, a.nh1)
    pre = prepara(ingressi)
    t0 = time.time()
    esiti = scan_griglia(y, pre, a.k, a.rip_griglia)
    print("griglia, %d ripetizioni per punto, %.0f s\n" % (a.rip_griglia, time.time() - t0))
    for nome, lista in esiti.items():
        print("  %-3s  tetto %.4f" % (nome, TETTI[nome]))
        for d in lista[:5]:
            print("        lung=%-5.2f alpha=%-7g  R2cv = %.4f +- %.4f   quota %.1f%%"
                  % (d["lunghezza"], d["alpha"], d["r2cv_media"], d["r2cv_sd"],
                     100 * d["r2cv_media"] / TETTI[nome]))
        print()
    print("il massimo sulla griglia e' OTTIMISTA: la selezione e' fatta sugli stessi dati.")
    return 0


def misura(a):
    y, P, _M, ingressi, n = carica(a.region, a.params, a.pk, a.nh1)
    pre = prepara(ingressi)
    rec = {"schema": "paper2_d6bis_kernel_v1", "versione": VERSIONE, "region": a.region, "n": n,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "k_fold": a.k, "ripetizioni": a.ripetizioni, "bootstrap": a.bootstrap,
           "griglia": {"lunghezze": list(LUNGHEZZE), "alpha": list(ALPHA),
                       "v1_dichiarata_prima": {k: list(v) for k, v in GRIGLIA_V1.items()},
                       "perche_estesa": ("nel run del 13 set il massimo cadeva sul bordo in tutti "
                                         "e tre gli ingressi: griglia estesa, non numero cercato"),
                       "selezione": "massimo sulla media delle ripetizioni, OTTIMISTA e dichiarato tale"},
           "tetti": TETTI,
           "ingressi": {"nh1": a.nh1 or FROZEN[a.region]["path"], "params": a.params, "pk": a.pk},
           "denominatori": {
               "sd_partizione": "ripetizioni della CV, coorte fissa: si restringe ripetendo",
               "sd_ensemble": ("bootstrap sulle 2000 realizzazioni, fold per realizzazione di "
                               "origine: contiene anche il campionamento della coorte, ed e' "
                               "quella su cui si misura un margine da soglia")}}

    griglia = scan_griglia(y, pre, a.k, a.rip_griglia)
    rec["griglia_esiti"] = {nome: lista[:5] for nome, lista in griglia.items()}

    serie_rip, serie_boot, scelti = {}, {}, {}
    bordi = {}
    for nome, (D2, med) in pre.items():
        best = sul_bordo_o_interno(griglia[nome], bordi, nome)
        scelti[nome] = best
        K = costruisci_K(D2, best["lunghezza"], med)
        al = best["alpha"]
        serie_rip[nome] = [r2_krr(y, K, fold_di(n, a.k, s), a.k, al) for s in range(a.ripetizioni)]
        boot = []
        for b in range(a.bootstrap):
            rng = np.random.default_rng(10_000 + b)
            righe = rng.integers(0, n, n)
            boot.append(r2_krr(y, K, fold_di(n, a.k, b), a.k, al, righe=righe))
        serie_boot[nome] = boot

    # il polinomio di terzo grado, per continuita' con D6
    X3 = design(P, 3)
    serie_rip["A3_poly"] = [r2_cv(y, X3, k=a.k, seed=s) for s in range(a.ripetizioni)]
    scelti["A3_poly"] = {"nota": "35 termini, la sequenza dichiarata di D6"}
    TETTI_LOC = dict(TETTI, A3_poly=CEIL_PARAMS)

    rec["bordo_griglia"] = bordi
    rec["stime"] = {}
    for nome in serie_rip:
        v = np.asarray(serie_rip[nome], float)
        d = {"r2cv_media": float(np.nanmean(v)),
             "sd_partizione": float(np.nanstd(v, ddof=1)),
             "quota_del_tetto": float(np.nanmean(v) / TETTI_LOC[nome]),
             "tetto": TETTI_LOC[nome], "iperparametri": scelti[nome]}
        if nome in serie_boot:
            b = np.asarray(serie_boot[nome], float)
            d["sd_ensemble"] = float(np.nanstd(b, ddof=1))
            d["bootstrap_media"] = float(np.nanmean(b))
            d["rapporto_sd"] = float(np.nanstd(b, ddof=1) / np.nanstd(v, ddof=1))
        rec["stime"][nome] = d

    def appaia(u, v):
        d = np.asarray(u, float) - np.asarray(v, float)
        sd = float(np.nanstd(d, ddof=1))
        return {"differenza": float(np.nanmean(d)), "sd_appaiata": sd,
                "in_sigma": float(abs(np.nanmean(d)) / sd) if sd > 0 else float("inf")}

    rec["confronti"] = {
        "K_meno_P": appaia(serie_rip["K"], serie_rip["P"]),
        "PK_meno_P": appaia(serie_rip["PK"], serie_rip["P"]),
        "PK_meno_K": appaia(serie_rip["PK"], serie_rip["K"]),
        "P_kernel_meno_A3_poly": appaia(serie_rip["P"], serie_rip["A3_poly"]),
        "nota": ("le differenze grezze non sono confronti di quote quando i tetti "
                 "differiscono: P sta sotto 0.698, K e PK sotto 0.832"),
    }
    rec["confronti_bootstrap"] = {
        "K_meno_P": appaia(serie_boot["K"], serie_boot["P"]),
        "PK_meno_P": appaia(serie_boot["PK"], serie_boot["P"]),
    }
    rec["lettura_possibile"] = {
        "se_PK_supera_P": "P(k) aggiunge informazione oltre i parametri",
        "se_PK_uguale_P": ("P(k) non aggiunge nulla che i parametri non abbiano: la parte non "
                           "spiegata non e' catturata dal due punti con questo stimatore"),
        "limite_da_dichiarare_comunque": ("kernel ridge gaussiano e' una classe ampia ma non "
                                          "universale a n finito: «non catturata da questo "
                                          "stimatore» non e' «non presente»"),
    }
    return rec


def comando_misura(a):
    t0 = time.time()
    rec = misura(a)
    rec["secondi"] = round(time.time() - t0, 1)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    if a.out:
        append_atomic(a.out, rec)
        print("\n[log] record appeso a %s" % a.out, file=sys.stderr)
    for nome, d in rec.get("bordo_griglia", {}).items():
        if d["sul_bordo"] and not d.get("scambiato_con_interno"):
            print("  ATTENZIONE %s: il massimo sta sul bordo e batte l'interno: estendere la griglia"
                  % nome, file=sys.stderr)
        elif d.get("scambiato_con_interno"):
            print("  nota %s: massimo sul bordo a %.2f sd dall'interno -> usato il punto interno "
                  "(lung=%.2f alpha=%g)" % (nome, d["distanza_in_sd"], d["lunghezza"], d["alpha"]),
                  file=sys.stderr)
    print("\n== STIME ==", file=sys.stderr)
    for nome, d in rec["stime"].items():
        print("  %-8s R2cv %.4f  sd_part %.4f  sd_ens %s  quota %.1f%% del tetto %.3f"
              % (nome, d["r2cv_media"], d["sd_partizione"],
                 ("%.4f" % d["sd_ensemble"]) if "sd_ensemble" in d else "   —  ",
                 100 * d["quota_del_tetto"], d["tetto"]), file=sys.stderr)
    for nome, d in rec["confronti"].items():
        if isinstance(d, dict):
            print("  %-22s %+.4f +- %.4f  (%.1f sigma, partizione)"
                  % (nome, d["differenza"], d["sd_appaiata"], d["in_sigma"]), file=sys.stderr)
    return 0


# ------------------------------------------------------------------ selftest

def selftest():
    ok = tot = 0

    def check(cond, nome):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok]   %s" % nome)
        else:
            print("  [FAIL] %s" % nome)

    print("selftest paper2_d6bis_kernel v%s" % VERSIONE)
    rng = np.random.default_rng(7)
    n, k = 400, 5

    # --- blocchi e distanze
    A = rng.normal(size=(n, 4)) * 10 + 3
    B = rng.normal(size=(n, 40))
    X = blocchi(A, B)
    check(X.shape == (n, 44), "blocchi: colonne concatenate")
    # Il contributo di un blocco alla distanza e' la sua norma di Frobenius, non la norma
    # media di colonna: dividendo per sqrt(d) i due blocchi pesano uguale in totale.
    na, nb = np.linalg.norm(X[:, :4]), np.linalg.norm(X[:, 4:])
    check(abs(na / nb - 1) < 1e-9 and abs(na / np.sqrt(n) - 1) < 1e-9,
          "blocchi: i due gruppi pesano uguale nella distanza (Frobenius = sqrt(n))")
    D2 = dist2(X)
    check(np.all(D2 >= 0) and abs(D2.trace()) < 1e-8, "dist2: non negativa, diagonale nulla")
    check(np.allclose(D2, D2.T), "dist2: simmetrica")

    # --- fold per realizzazione
    f = fold_di(n, k, 3)
    check(len(np.unique(f)) == k and np.bincount(f).min() >= n // k - 1, "fold: k gruppi bilanciati")
    check(np.array_equal(f, fold_di(n, k, 3)), "fold: stesso seme, stessa partizione")

    # --- kernel ridge su un segnale non lineare
    Z = rng.uniform(-1, 1, size=(n, 3))
    y = np.sin(3 * Z[:, 0]) + Z[:, 1] ** 2 + 0.1 * rng.normal(size=n)
    Xz = blocchi(Z)
    D2z = dist2(Xz)
    med = float(np.median(D2z[np.triu_indices_from(D2z, k=1)]))
    K = costruisci_K(D2z, 1.0, med)
    AL = 1e-3
    r_krr = r2_krr(y, K, fold_di(n, k, 0), k, AL)
    r_lin = r2_cv(y, design(Z, 1), k=k, seed=0)
    check(r_krr > r_lin + 0.2, "kernel ridge batte il lineare su un segnale non lineare")
    check(r_krr < 1.0, "e non e' un R2 di uno")

    ypuro = rng.normal(size=n)
    r_nullo = r2_krr(ypuro, K, fold_di(n, k, 0), k, AL)
    check(r_nullo < 0.1, "DIFETTO: su rumore puro l'R2 fuori campione non e' alto")

    # --- il bootstrap, e il difetto che deve evitare
    b = np.random.default_rng(1).integers(0, n, n)
    fold = fold_di(n, k, 0)
    fv = fold[b]
    for j in range(k):
        orig_te = set(b[fv == j])
        orig_tr = set(b[fv != j])
        if orig_te & orig_tr:
            break
    else:
        j = -1
    check(j == -1, "DIFETTO: nessuna realizzazione sta in addestramento E in prova")

    r_boot = [r2_krr(y, K, fold_di(n, k, i), k, AL,
                     righe=np.random.default_rng(i).integers(0, n, n)) for i in range(12)]
    r_rip = [r2_krr(y, K, fold_di(n, k, i), k, AL) for i in range(12)]
    sd_b, sd_r = float(np.std(r_boot, ddof=1)), float(np.std(r_rip, ddof=1))
    check(sd_b > sd_r, "DIFETTO: la sd del bootstrap e' PIU' LARGA di quella fra partizioni")
    check(abs(np.mean(r_boot) - np.mean(r_rip)) < 0.15, "e le due medie restano vicine")

    # --- fold assegnati alla copia invece che all'origine: R2 gonfiato
    bb = np.random.default_rng(1).integers(0, n, n)
    fold_copia = fold_di(n, k, 0)[np.arange(n)]  # per posizione nella risorsa, NON per origine
    yv = y[bb]
    pred = np.empty(n)
    for j in range(k):
        te = np.where(fold_copia == j)[0]
        tr = np.where(fold_copia != j)[0]
        A_ = K[np.ix_(bb[tr], bb[tr])].copy()
        A_[np.diag_indices_from(A_)] += AL
        mu = yv[tr].mean()
        a_ = np.linalg.solve(A_, yv[tr] - mu)
        pred[te] = K[np.ix_(bb[te], bb[tr])] @ a_ + mu
    r_gonfio = 1 - float(((yv - pred) ** 2).sum()) / float(((yv - yv.mean()) ** 2).sum())
    r_giusto = r2_krr(y, K, fold_di(n, k, 0), k, AL, righe=bb)
    check(r_gonfio > r_giusto, "DIFETTO riprodotto: fold sulla copia gonfia l'R2 rispetto ai fold sull'origine")

    # --- griglia
    pre = {"Z": (D2z, med)}
    es = scan_griglia(y, pre, k, 2)
    check(len(es["Z"]) == len(LUNGHEZZE) * len(ALPHA), "griglia: tutti i punti valutati")
    check(es["Z"][0]["r2cv_media"] >= es["Z"][-1]["r2cv_media"], "griglia: ordinata per R2 decrescente")

    # --- la regola sul bordo
    b = {}
    lista = [{"lunghezza": LUNGHEZZE[-1], "alpha": 1e-3, "r2cv_media": 0.40, "r2cv_sd": 0.02},
             {"lunghezza": 2.0, "alpha": 1e-3, "r2cv_media": 0.39, "r2cv_sd": 0.02}]
    scelto = sul_bordo_o_interno(lista, b, "X")
    check(scelto["lunghezza"] == 2.0 and b["X"]["scambiato_con_interno"],
          "bordo: interno entro una sd -> si usa l'interno, e lo si registra")
    b2 = {}
    lista2 = [{"lunghezza": LUNGHEZZE[-1], "alpha": 1e-3, "r2cv_media": 0.50, "r2cv_sd": 0.01},
              {"lunghezza": 2.0, "alpha": 1e-3, "r2cv_media": 0.39, "r2cv_sd": 0.01}]
    scelto2 = sul_bordo_o_interno(lista2, b2, "X")
    check(scelto2["lunghezza"] == LUNGHEZZE[-1] and not b2["X"]["scambiato_con_interno"],
          "DIFETTO: bordo che batte l'interno di piu' di una sd -> resta, e va estesa")
    b3 = {}
    sul_bordo_o_interno([{"lunghezza": 2.0, "alpha": 1e-3, "r2cv_media": 0.4, "r2cv_sd": 0.01}], b3, "X")
    check(b3["X"]["sul_bordo"] is False, "massimo interno: nessuno scambio")

    # --- tetti
    check(TETTI["P"] < TETTI["K"] and TETTI["K"] == TETTI["PK"],
          "tetti: 0.698 per i parametri, 0.832 per tutto cio' che tocca P(k)")

    print("\nselftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for nome in ("griglia", "misura"):
        s = sub.add_parser(nome)
        s.add_argument("--region", required=True, choices=["NGC", "SGC"])
        s.add_argument("--params", required=True)
        s.add_argument("--pk", default="results/phase7_pk_nwlh_cache.npz")
        s.add_argument("--nh1", default=None)
        s.add_argument("--k", type=int, default=K_FOLD)
        s.add_argument("--rip-griglia", type=int, default=RIP_GRIGLIA, dest="rip_griglia")
        if nome == "misura":
            s.add_argument("--ripetizioni", type=int, default=RIPETIZIONI)
            s.add_argument("--bootstrap", type=int, default=BOOTSTRAP)
            s.add_argument("--out", default=None)
    a = p.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    return comando_griglia(a) if a.cmd == "griglia" else comando_misura(a)


if __name__ == "__main__":
    raise SystemExit(main())

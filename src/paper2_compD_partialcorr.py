#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_compD_partialcorr.py — Paper 2, Componente D, misura M1

Correlazione parziale di N_H1 con i parametri cosmologici su TUTTI i 2000 mock,
non sui 200 etichettati.  A n = 2000 l'errore su r scende a ~0.022: una
correlazione di 0.05 diventa misurabile.

Tre cose che questo script fa e che una regressione ingenua non farebbe.

1.  SENTINELLA DI JOIN.  Il rischio dominante qui non e' un errore numerico: e'
    un allineamento sbagliato fra i record N_H1 e le righe dei parametri.  Un
    join scrambled manda TUTTE le correlazioni a zero -- cioe' produce
    esattamente la conclusione che stiamo testando, in modo falso.   Omega_m
    correla a +0.150 a n = 200: se a n = 2000 non risulta chiaramente positiva,
    lo script si ferma e dichiara sospetto il join invece di concludere.

2.  TETTO DI R^2.  Dalla decomposizione della varianza di M26 R1 §5.5,
    sigma_cos / sigma_tot = 261.5 / 313.0, quindi la quota di varianza che
    QUALUNQUE funzione dei parametri cosmologici puo' spiegare e' al massimo
    (261.5/313.0)^2 = 0.698.  Confrontare l'R^2 osservato con quel tetto e' la
    misura piu' informativa dell'intero esperimento:

      R^2 ~ 0.698  ->  i parametri LCDM descrivono tutta la risposta cosmologica
      R^2 << 0.698 ->  N_H1 risponde a qualcosa delle condizioni iniziali che i
                       parametri LCDM non parametrizzano.  Che e' la tesi del
                       paper, e un'affermazione molto piu' forte di
                       "insensibile a w0".

3.  DISATTENUAZIONE.  N_H1 = C(cosmologia) + E(HOD + realizzazione), con E
    indipendente.  Quindi r_osservato = r_vero * sigma_cos/sigma_tot = r * 0.835.
    Le correlazioni vanno riportate in entrambe le forme, etichettate.

Uso (da D:\\projects\\cauchy):
    python src\\paper2_compD_partialcorr.py --selftest
    python src\\paper2_compD_partialcorr.py --region NGC --out results\\paper2\\compD_NGC.jsonl
    python src\\paper2_compD_partialcorr.py --region SGC --out results\\paper2\\compD_SGC.jsonl

Sola lettura sugli ingressi.  Output JSONL append-only, atomico.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

# --------------------------------------------------------------------------
# congelati
# --------------------------------------------------------------------------

FROZEN = {
    "NGC": {"path": "results/paper1/per_mock_NGC_R5.jsonl",
            "mean": 35436.686, "sd": 312.989, "n": 2000, "desi": 28256},
    "SGC": {"path": "results/paper1/per_mock_SGC_R5.jsonl",
            "mean": 18712.968, "sd": 197.787, "n": 2000, "desi": 15122},
}
FIELD = ("base", "N_H1")          # campo annidato, non "N_H1" al primo livello
MEAN_TOL, SD_TOL = 0.05, 0.05     # assoluti, in generatori

# decomposizione della varianza, M26 R1 §5.5
SIGMA_COS, SIGMA_FIXED, SIGMA_TOT = 261.5, 172.0, 313.0
R2_CEILING = (SIGMA_COS / SIGMA_TOT) ** 2          # 0.698
ATTEN = SIGMA_COS / SIGMA_TOT                      # 0.835

# valori di riferimento a n = 200 (correlazioni grezze, canovaccio Paper 5 §2.1)
REF_N200 = {"Omega_m": 0.150, "sigma_8": 0.137, "w0": 0.011}
SENTINEL = "Omega_m"
SENTINEL_MIN_R = 0.05             # sotto questo, il join e' sospetto

DEFAULT_NAMES = {
    5: ["Omega_m", "Omega_b", "h", "n_s", "sigma_8"],
    6: ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "w0"],
    7: ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "M_nu", "w0"],
}

INDEX_KEYS = ["mock", "imock", "mock_id", "index", "idx", "i",
              "realization", "realisation", "sim", "seed"]

# intervalli nominali del Latin hypercube nwLH di Quijote.  Servono a
# IDENTIFICARE le colonne dai valori invece che dalla posizione: se l'ordine
# nel file non fosse quello atteso, le etichette finirebbero sui parametri
# sbagliati e nessun cancello se ne accorgerebbe.
PARAM_RANGES = {
    "Omega_m": (0.10, 0.50),
    "Omega_b": (0.03, 0.07),
    "h":       (0.50, 0.90),
    "n_s":     (0.80, 1.20),
    "sigma_8": (0.60, 1.00),
    "M_nu":    (0.00, 1.00),
    "w0":      (-1.30, -0.70),
}

# D-T3: soglia ASSOLUTA sul punteggio di infer_names, dichiarata dal disegno
# e non dall'output. Con 2000 campioni un Latin hypercube lascia ai bordi
# lacune dell'ordine di 1/2000 dello span, quindi il punteggio vero sta sotto
# 1e-2; sulla suite nwLH il concorrente piu' vicino (M_nu contro Omega_m) sta
# a 0.60. La soglia e' un ordine di grandezza sopra il primo, sei volte sotto
# il secondo. Oltre la soglia si ARRESTA: non si avvisa.
INFER_SCORE_MAX = 0.1


# --------------------------------------------------------------------------
# predizioni, dichiarate prima di guardare i risultati
# --------------------------------------------------------------------------

PREDICTIONS = """
PREDIZIONI DICHIARATE PRIMA DEL RUN
  P1  r(N_H1, w0) parziale resta compatibile con zero: |r| < 0.05 a n = 2000.
  P2  r(N_H1, n_s) parziale resta il piu' grande in modulo fra i parametri,
      e sopravvive a n = 2000 sopra +0.25.
  P3  r(N_H1, sigma_8) parziale e' piu' piccolo di r(n_s) -- coerente con
      l'invarianza monotona, che chiude il canale di ampiezza per teorema.
  P4  R^2 multivariato < 0.698 (il tetto).  Sub-predizione: R^2 < 0.40, cioe'
      i sei parametri NON esauriscono la varianza cosmologica.
  P5  La matrice di disegno del Latin hypercube e' quasi ortogonale: |r| fra
      parametri < 0.10.  Se non lo fosse, parziale e grezza divergerebbero.
Se una qualunque di queste e' smentita, va registrata come smentita, non riscritta.
"""


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------

def dig(rec, path):
    cur = rec
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def load_nh1(path):
    """Restituisce (indici, valori).  Se manca un indice esplicito, usa l'ordine."""
    idx, val, key = [], [], None
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            v = dig(rec, FIELD)
            if v is None:
                continue
            if key is None:
                for k in INDEX_KEYS:
                    if k in rec and isinstance(rec[k], (int, float)):
                        key = k
                        break
                else:
                    key = "__order__"
                print("[join] chiave di indice: %s" % key)
            idx.append(int(rec[key]) if key != "__order__" else len(val))
            val.append(float(v))
    return np.asarray(idx, int), np.asarray(val, float)


def infer_names(raw):
    """
    Assegna i nomi confrontando (min, max) di ogni colonna con gli intervalli
    nominali.  Con 2000 campioni un Latin hypercube riempie quasi esattamente il
    suo intervallo, quindi il riconoscimento e' netto.
    """
    ncol = raw.shape[1]
    lo, hi = raw.min(axis=0), raw.max(axis=0)
    assigned, used = [], set()
    for j in range(ncol):
        best, score = None, None
        for nm, (a, b) in PARAM_RANGES.items():
            if nm in used:
                continue
            span = b - a
            sc = (abs(lo[j] - a) + abs(hi[j] - b)) / span
            if score is None or sc < score:
                best, score = nm, sc
        assigned.append((best, score))
        used.add(best)
    return assigned


def load_params(path, names=None):
    raw = np.genfromtxt(path)
    if raw.ndim == 1:
        raw = raw[:, None]
    ncol = raw.shape[1]
    if names:
        nm = list(names)
    elif ncol in DEFAULT_NAMES:
        nm = DEFAULT_NAMES[ncol]
    else:
        nm = ["p%d" % i for i in range(ncol)]
    if len(nm) != ncol:
        raise SystemExit("nomi (%d) e colonne (%d) non coincidono" % (len(nm), ncol))
    print("[param] %s: %d righe x %d colonne" % (os.path.basename(path), raw.shape[0], ncol))

    inferred = infer_names(raw)
    print("    colonna  posizionale   dai valori   scarto   min        max")
    mismatch = []
    for j in range(ncol):
        gi, sc = inferred[j]
        flag = "" if gi == nm[j] else "   <<< DISCORDANTE"
        print("    %7d  %-12s %-12s %7.3f  %9.4f  %9.4f%s"
              % (j, nm[j], gi, sc, raw[:, j].min(), raw[:, j].max(), flag))
        if gi != nm[j]:
            mismatch.append((j, nm[j], gi))
    if mismatch and not names:
        print("\n    Le etichette posizionali NON coincidono con quelle dedotte dai valori.")
        print("    Uso quelle dedotte dai valori: un ordine di colonne diverso da quello")
        print("    atteso metterebbe le correlazioni sui parametri sbagliati.")
        nm = [g for g, _ in inferred]
        print("    -> %s" % ", ".join(nm))
    elif mismatch:
        print("\n    --names esplicito: rispetto la tua scelta nonostante la discordanza.")
    else:
        print("    -> etichette confermate su tutte le colonne.")
    return raw, nm


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_param_header(path):
    """LA TERZA FONTE: i nomi scritti nel file.

    DEFAULT_NAMES guarda la POSIZIONE, infer_names guarda gli ESTREMI delle
    colonne. L'intestazione non e' ne' l'uno ne' l'altro, ed e' l'unica delle
    tre verificabile da fuori senza fidarsi di PARAM_RANGES. Il file la porta
    ('#Omega_m Omega_b h n_s sigma_8 M_nu w0') e finora non veniva letta:
    np.genfromtxt la scarta come commento.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                toks = s.lstrip("#").split()
                return toks or None
            return None
    return None


def load_params_checked(path, names=None):
    """D-T3. Avvolge load_params e aggiunge i due cancelli che mancavano.

    Che cosa NON aggiunge, e va detto per non rivendicare troppo: infer_names
    difende gia' da una permutazione di colonne, perche' guarda gli ESTREMI e non
    la posizione, e su questa suite gli intervalli sono separabili - Omega_m
    contro M_nu, la coppia piu' vicina, da' 0.60 contro ~0. La difesa c'e'.

    Quello che aggiunge:

    (a) UNA TERZA FONTE INDIPENDENTE DA PARAM_RANGES. Posizione e valori non sono
        indipendenti dalla tabella degli intervalli: se PARAM_RANGES fosse
        sbagliata, l'identificazione dai valori sarebbe sbagliata insieme a lei e
        nessuno se ne accorgerebbe. L'intestazione del file e' l'unica delle tre
        che non dipende da quella tabella. Il risultato citabile della Componente
        D e' un ORDINAMENTO di parametri: uno scambio lascia intatta la
        conclusione negativa su w0 e distrugge quella positiva.

    (b) SOGLIA CON ARRESTO. Il verdetto di infer_names era sempre completo e mai
        gated: ogni colonna riceveva un nome qualunque fosse il punteggio, e
        l'ultima colonna non sceglieva affatto perche' le restava un solo nome.

    (c) L'ESITO NEL RECORD. Quale fonte abbia deciso le etichette finiva a
        terminale; ora e' un campo depositato.

    Non reimplementa l'etichettatura: chiama load_params e la verifica.
    """
    raw, nm = load_params(path, names)
    ncol = raw.shape[1]
    inferred = infer_names(raw)
    scores = [round(float(sc), 12) for _, sc in inferred]
    by_values = [g for g, _ in inferred]
    by_position = list(DEFAULT_NAMES.get(ncol, [])) or None
    header = read_param_header(path)

    print("\n[D-T3] confronto a tre fonti")
    print("    usate       : %s" % ", ".join(nm))
    print("    posizionali : %s" % (", ".join(by_position) if by_position else "assenti"))
    print("    dai valori  : %s" % ", ".join(by_values))
    print("    intestazione: %s" % (", ".join(header) if header else "assente"))
    print("    punteggi    : %s   (max %.4g, soglia %.4g)"
          % (" ".join("%.3g" % s for s in scores), max(scores), INFER_SCORE_MAX))

    if max(scores) > INFER_SCORE_MAX:
        raise SystemExit(
            "[D-T3] CANCELLO FALLITO: punteggio massimo di infer_names %.4g > soglia %.4g.\n"
            "    L'identificazione dai valori non e' netta su questo file, quindi la\n"
            "    difesa contro una permutazione di colonne non regge. Arresto."
            % (max(scores), INFER_SCORE_MAX))

    if header is not None and len(header) == ncol and list(header) != list(nm):
        raise SystemExit(
            "[D-T3] CANCELLO FALLITO: l'intestazione del file dice %s\n"
            "    ma le etichette in uso sono %s.\n"
            "    Il risultato della Componente D e' un ordinamento di parametri: una\n"
            "    permutazione lo distrugge senza toccare la conclusione su w0. Arresto."
            % (", ".join(header), ", ".join(nm)))

    if header is not None and len(header) != ncol:
        raise SystemExit(
            "[D-T3] CANCELLO FALLITO: l'intestazione ha %d nomi e il file %d colonne."
            % (len(header), ncol))

    agree = [s for s, v in (("header", header), ("position", by_position),
                            ("values", by_values)) if v is not None and list(v) == list(nm)]
    source = "+".join(agree) if agree else "explicit"
    print("    -> fonti che concordano con le etichette in uso: %s" % source)

    diag = {
        "names_used": list(nm),
        "names_by_position": by_position,
        "names_by_values": by_values,
        "names_from_header": list(header) if header else None,
        "names_source": source,
        "infer_scores": scores,
        "infer_score_max": max(scores),
        "infer_score_threshold": INFER_SCORE_MAX,
    }
    return raw, nm, diag


# --------------------------------------------------------------------------
# statistica
# --------------------------------------------------------------------------

def pearson(x, y):
    x = x - x.mean()
    y = y - y.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else 0.0


def resid_on(y, X):
    """Residui di y sulla regressione lineare su X (con intercetta)."""
    A = np.column_stack([np.ones(len(y)), X]) if X.size else np.ones((len(y), 1))
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def partial_corr(y, P, j):
    """r(y, P[:,j] | tutte le altre colonne di P)."""
    others = np.delete(P, j, axis=1)
    return pearson(resid_on(y, others), resid_on(P[:, j], others))


def perm_p(y, x, r_obs, n=20000, seed=0):
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n):
        if abs(pearson(rng.permutation(y), x)) >= abs(r_obs):
            cnt += 1
    return (cnt + 1) / (n + 1)


def fisher_ci(r, n, z=1.959963985):
    if abs(r) >= 1:
        return (r, r)
    a = np.arctanh(r)
    s = 1.0 / np.sqrt(n - 3)
    return float(np.tanh(a - z * s)), float(np.tanh(a + z * s))


def r2_multi(y, P):
    A = np.column_stack([np.ones(len(y)), P])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ beta
    ss_res = float((res * res).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot, beta


# --------------------------------------------------------------------------
# cancelli
# --------------------------------------------------------------------------

def gate_ensemble(region, val):
    f = FROZEN[region]
    m, s, n = float(val.mean()), float(val.std(ddof=1)), len(val)
    print("\n[gate] ensemble v1, regione %s" % region)
    print("    n     = %6d          atteso %6d" % (n, f["n"]))
    print("    media = %12.4f  atteso %12.3f   scarto %+.4f" % (m, f["mean"], m - f["mean"]))
    print("    sd    = %12.4f  atteso %12.3f   scarto %+.4f" % (s, f["sd"], s - f["sd"]))
    bad = (n != f["n"] or abs(m - f["mean"]) > MEAN_TOL or abs(s - f["sd"]) > SD_TOL)
    if bad:
        print("    CANCELLO FALLITO. Non produrre correlazioni.", file=sys.stderr)
        sys.exit(3)
    print("    [gate] superato.")


def gate_join(names, P, y):
    """La sentinella: se Omega_m non correla, il join e' sospetto."""
    print("\n[gate] sentinella di join (%s)" % SENTINEL)
    if SENTINEL not in names:
        print("    %s assente fra i parametri: sentinella non applicabile." % SENTINEL)
        print("    ATTENZIONE: nessuna difesa contro un allineamento sbagliato.")
        return
    j = names.index(SENTINEL)
    r = pearson(y, P[:, j])
    lo, hi = fisher_ci(r, len(y))
    print("    r(N_H1, %s) = %+.4f  IC95%% [%+.4f, %+.4f]   riferimento n=200: %+.3f"
          % (SENTINEL, r, lo, hi, REF_N200[SENTINEL]))
    if r < SENTINEL_MIN_R:
        print("\n    CANCELLO FALLITO: la sentinella non correla.", file=sys.stderr)
        print("    Un join scrambled manda TUTTE le correlazioni a zero, cioe'", file=sys.stderr)
        print("    produce la conclusione 'insensibile' in modo falso.", file=sys.stderr)
        print("    Verificare l'allineamento indice-record prima di concludere.", file=sys.stderr)
        sys.exit(4)
    print("    [gate] superato: il join regge.")


def report_design(names, P):
    print("\n[disegno] ortogonalita' del Latin hypercube")
    k = len(names)
    C = np.corrcoef(P, rowvar=False)
    worst, wi, wj = 0.0, 0, 1
    for i in range(k):
        for j in range(i + 1, k):
            if abs(C[i, j]) > abs(worst):
                worst, wi, wj = C[i, j], i, j
    print("    massima correlazione fra parametri: r(%s, %s) = %+.4f"
          % (names[wi], names[wj], worst))
    print("    -> P5 %s" % ("confermata" if abs(worst) < 0.10 else "SMENTITA"))
    return float(worst), (names[wi], names[wj])


# --------------------------------------------------------------------------

def run(args):
    print(PREDICTIONS)
    f = FROZEN[args.region]
    nh1_path = args.nh1 or f["path"]
    idx, val = load_nh1(nh1_path)
    order = np.argsort(idx)
    idx, val = idx[order], val[order]
    gate_ensemble(args.region, val)

    P_all, names, names_diag = load_params_checked(args.params, args.names)
    if P_all.shape[0] < idx.max() + 1:
        raise SystemExit("il file parametri ha %d righe ma l'indice massimo e' %d"
                         % (P_all.shape[0], idx.max()))
    P = P_all[idx, :]
    y = val

    gate_join(names, P, y)
    worst, worst_pair = report_design(names, P)

    print("\n[risultati] n = %d" % len(y))
    hdr = "%-10s %9s %9s %20s %10s %10s %12s" % (
        "parametro", "r grezza", "r parz.", "IC95% (parziale)", "p perm.",
        "r disatt.", "pendenza")
    print(hdr); print("-" * len(hdr))
    rows = []
    for j, nm in enumerate(names):
        r_raw = pearson(y, P[:, j])
        r_par = partial_corr(y, P, j)
        lo, hi = fisher_ci(r_par, len(y))
        pp = perm_p(y, P[:, j], r_raw, n=args.perm, seed=j)
        slope = r_raw * y.std(ddof=1) / P[:, j].std(ddof=1)
        span = float(P[:, j].max() - P[:, j].min())
        rows.append({"param": nm, "r_raw": r_raw, "r_partial": r_par,
                     "ci95_lo": lo, "ci95_hi": hi, "perm_p": pp,
                     "r_disattenuata": r_par / ATTEN,
                     "slope_gen_per_unit": slope,
                     "span": span, "excursion_gen": slope * span})
        print("%-10s %+9.4f %+9.4f  [%+7.4f, %+7.4f] %10.4f %+10.4f %12.1f"
              % (nm, r_raw, r_par, lo, hi, pp, r_par / ATTEN, slope))

    r2, beta = r2_multi(y, P)
    print("\n[tetto di R^2]")
    print("    R^2 osservato (%d parametri) = %.4f" % (len(names), r2))
    print("    tetto dalla decomposizione   = %.4f   (sigma_cos/sigma_tot)^2" % R2_CEILING)
    print("    quota del tetto raggiunta    = %.1f%%" % (100 * r2 / R2_CEILING))
    if r2 / R2_CEILING < 0.6:
        gap = R2_CEILING - r2
        print("\n    LETTURA: i parametri LCDM campionati NON esauriscono la varianza")
        print("    cosmologica di N_H1.  Non spiegato: %.1f%% della varianza TOTALE,"
              % (100 * gap))
        print("    cioe' il %.1f%% della varianza COSMOLOGICA." % (100 * gap / R2_CEILING))
        print("    ATTENZIONE: R^2 e' LINEARE.  Una dipendenza non lineare dai parametri")
        print("    apparirebbe qui come varianza 'non spiegata'.  Prima di affermare che")
        print("    la statistica risponde a qualcosa di non parametrizzato, va escluso")
        print("    il termine quadratico: vedi paper2_compD_nonlinear.py.")
    else:
        print("\n    LETTURA: i parametri LCDM descrivono la maggior parte della")
        print("    risposta cosmologica.  L'insensibilita' e' selettiva, non globale.")

    # escursione su w0 e vincolo implicito
    extra = {}
    if "w0" in names:
        rw = [r for r in rows if r["param"] == "w0"][0]
        exc = abs(rw["excursion_gen"])
        sig1 = (SIGMA_TOT / abs(rw["slope_gen_per_unit"])) if rw["slope_gen_per_unit"] else float("inf")
        print("\n[leva su w0]")
        print("    pendenza      = %.1f generatori per unita' di w0" % rw["slope_gen_per_unit"])
        print("    escursione    = %.1f generatori su Delta w0 = %.2f" % (exc, rw["span"]))
        print("    in unita' di sigma_tot: %.2f" % (exc / SIGMA_TOT))
        print("    vincolo 1sigma implicito su w0: +/- %.2f   (BAO DESI: +/- 0.06)" % sig1)
        extra = {"w0_excursion_gen": exc, "w0_sigma1_implied": sig1}

    # distanza del deficit
    print("\n[distanza del deficit]")
    gap = f["mean"] - f["desi"]
    print("    deficit DESI = %.1f generatori" % gap)
    best = max(abs(r["excursion_gen"]) for r in rows)
    print("    massima escursione parametrica sulla griglia = %.1f (%s)"
          % (best, max(rows, key=lambda r: abs(r["excursion_gen"]))["param"]))
    print("    fattore mancante = %.1f x" % (gap / best if best else float("inf")))

    rec = {"schema": "paper2_compD_v1", "region": args.region,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "n": len(y), "nh1_path": nh1_path, "params_path": args.params,
           "r2_multi": r2, "r2_ceiling": R2_CEILING,
           "attenuation": ATTEN, "design_worst_r": worst,
           "design_worst_pair": list(worst_pair),
           "rows": rows, "deficit_gen": gap}
    # D-T3: quale fonte ha deciso le etichette non e' piu' un messaggio a
    # terminale. D-T1: config_hash riassume PERCORSI e conteggio, non i byte;
    # questi due campi sono i byte, e sono nuovi per non cambiare il
    # significato di config_hash ne' il suo valore sui record depositati.
    rec.update(names_diag)
    rec["params_sha256"] = sha256_file(args.params)
    rec["nh1_sha256"] = sha256_file(nh1_path)
    rec.update(extra)
    rec["config_hash"] = hashlib.sha256(
        json.dumps({k: rec[k] for k in ("nh1_path", "params_path", "n")},
                   sort_keys=True).encode()).hexdigest()[:16]

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print("\nscritto in %s" % args.out)

    print("\n[verifica delle predizioni]")
    check(rows, "w0", lambda r: abs(r["r_partial"]) < 0.05, "P1")
    check(rows, "n_s", lambda r: r["r_partial"] > 0.25, "P2")
    if "n_s" in names and "sigma_8" in names:
        rn = [r for r in rows if r["param"] == "n_s"][0]["r_partial"]
        rs = [r for r in rows if r["param"] == "sigma_8"][0]["r_partial"]
        print("    P3  |r(sigma_8)| < |r(n_s)|: %s  (%.4f contro %.4f)"
              % ("confermata" if abs(rs) < abs(rn) else "SMENTITA", abs(rs), abs(rn)))
    print("    P4  R^2 < 0.40: %s  (%.4f)" % ("confermata" if r2 < 0.40 else "SMENTITA", r2))
    print("    P5  disegno quasi ortogonale: %s  (%.4f)"
          % ("confermata" if abs(worst) < 0.10 else "SMENTITA", worst))


def check(rows, name, cond, tag):
    r = [x for x in rows if x["param"] == name]
    if not r:
        print("    %s  %s assente" % (tag, name))
        return
    print("    %s  %s: %s  (r_parz = %+.4f)"
          % (tag, name, "confermata" if cond(r[0]) else "SMENTITA", r[0]["r_partial"]))


# --------------------------------------------------------------------------

def selftest():
    print("=== selftest ===")
    rng = np.random.default_rng(4)
    n = 2000
    P = rng.uniform(-1, 1, (n, 6))
    names = DEFAULT_NAMES[6]
    # segnale noto: n_s forte, Omega_m medio, w0 nullo, piu' rumore "fixed"
    C = 300 * (0.45 * P[:, 3] + 0.18 * P[:, 0])
    y = 35436.686 + C + rng.normal(0, 172.0, n)
    print("  costruito: n_s con peso 0.45, Omega_m 0.18, w0 0, rumore fixed 172")
    for j, nm in enumerate(names):
        print("    r_parz(%-9s) = %+.4f" % (nm, partial_corr(y, P, j)))
    r2, _ = r2_multi(y, P)
    print("  R^2 = %.4f" % r2)
    print("  varianza cosmologica iniettata / totale = %.4f"
          % (C.var() / y.var()))
    print("  -> R^2 deve avvicinarsi a quel valore: scarto %.4f"
          % abs(r2 - C.var() / y.var()))

    # sentinella: join scrambled
    perm = rng.permutation(n)
    r_ok = pearson(y, P[:, 0])
    r_bad = pearson(y[perm], P[:, 0])
    print("  sentinella: r(Omega_m) con join buono %+.4f, scrambled %+.4f"
          % (r_ok, r_bad))
    ok = (abs(r_bad) < 0.05 < abs(r_ok)) and abs(r2 - C.var() / y.var()) < 0.03
    print("=== selftest %s ===" % ("PASSATO" if ok else "FALLITO"))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    p.add_argument("--nh1", default=None, help="override del per_mock JSONL")
    p.add_argument("--params", default="data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt")
    p.add_argument("--names", nargs="*", default=None)
    p.add_argument("--perm", type=int, default=20000)
    p.add_argument("--out", default=None)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not os.path.exists(a.params):
        raise SystemExit("file parametri non trovato: %s\n"
                         "  passarlo con --params <path>" % a.params)
    run(a)


if __name__ == "__main__":
    main()

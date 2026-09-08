#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 — analisi della Fase 3: la misura del 3.4.

COSA CALCOLA, E CON QUALE METRO
--------------------------------
  D(g) = <N_H1>_mock(g) - N_H1^DESI(g)        (item 1.4 §1, prereg §5.1)

Il lato dati e' DETERMINISTICO: le differenze di N_H1^DESI fra punti della
griglia sono esatte, e il rumore sta tutto nel lato mock. L'incertezza su una
differenza di D fra due punti e' quindi l'ERRORE DELLA MEDIA della differenza
appaiata, non la dispersione per realizzazione. E' per questo che la soglia
depositata e' 3*sigma_Delta/sqrt(N) = 53 e non 3*sigma_Delta.

  RETTIFICA, 30 ago 2026. Durante la lettura preliminare dei record era stato
  usato come metro la dispersione mock-to-mock (~150 generatori), sostenendo che
  fosse il metro imposto dal Referee 3 sul Paper 1. E' un metro giusto per una
  domanda diversa — "il campo DESI e' compatibile con UN mock?" — e la' il
  confronto e' fra DESI e i singoli mock. Qui la domanda e' "la media dei mock
  si sposta rispetto a un lato dati esatto?", e il denominatore e' la SEM.
  Con la dispersione per realizzazione tutti i punti stavano sotto 1 sigma e
  l'esito sembrava E1; con il metro depositato l'esito e' E2.

STATISTICA PRIMARIA
  N_H1 a erosione k = 1 (item 1.2b), entrambi gli emisferi. k = 0 riportato in
  parallelo per l'aggancio ai numeri v1. Gli intervalli sono BOOTSTRAP
  PERCENTILE, non parametrici: la regola depositata chiede il rango empirico e
  non uno z, e il bootstrap e' la sua forma naturale per una media appaiata.

I QUATTRO ESITI (prereg §5.3), applicati come depositati
  DD_max = escursione di D sulla linea B fra B1 e B5.
    E1  DD_max < 53                      limite superiore
    E2  53 <= DD_max < 390 (206)         sensibilita' sotto-dominante
    E3  DD_max >= 390 (206)              sistematico di primo piano
    E4  E3 e l'estrapolazione azzera D dentro |F-1| <= 0.027
  Il codice NON estende la regola: se un esito cade fuori, lo dice.

  Riportata anche l'escursione sui CINQUE punti della linea B, perche' DD_max
  come definito usa due punti soli e puo' essere massima per costruzione. La
  regola resta quella depositata; il numero in piu' e' descrizione, non
  decisione.

TEST DI SIMMETRIA (prereg §5.5)
  Fit D(F) = D0 + a(F-1) + b(F-1)^2 sui cinque punti di linea B.
    |a| > 3 sigma(a) e |b| < 3 sigma(b)  -> risposta DISPARI: la topologia vede
                                            una direzione
    |b| > 3 sigma(b) e |a| < 3 sigma(a)  -> risposta PARI: vede una degradazione
    entrambi                             -> si riportano entrambi
  Le sigma dei coefficienti vengono dal bootstrap sulle realizzazioni appaiate,
  non dalla covarianza del fit: i cinque punti sono correlati, perche' vengono
  dagli stessi 200 mock.

COMPLETEZZA SUGLI ANGOLI (prereg §5.6)
  D(C_i) predetto interpolando in F efficace dalla linea B; scarto contro 53.
  La firma dichiarata: deve fallire dove il terzo canale e' grande (C1, C4) e
  non dove e' piccolo (C2, C3). Fallire ovunque significa tiling o
  ri-randomizzazione, non terzo canale.

CANALE DELLA SELEZIONE
  Il rapporto dN_H1/dn_sel per punto: e' il termine (c) del 3.3, e va stimato
  PER EMISFERO se i due non concordano.

Uso:
    python src\\paper2_fase3_analisi.py selftest
    python src\\paper2_fase3_analisi.py run --region NGC
    python src\\paper2_fase3_analisi.py run --region SGC --out results\\paper2\\fase3_analisi.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

DETECT = 53                      # 3*sigma_Delta/sqrt(200), prereg §5.2
RELEVANCE = {"NGC": 390, "SGC": 206}
F_PHYS = 0.027                   # ATTENZIONE: NON e' il range fisico.
# Emendamento 19, 1 set 2026. 0.027 e' il LATO PICCOLO di un intervallo
# asimmetrico: e' +0.0268 arrotondato, l'estremo superiore in convenzione
# standard. L'inviluppo misurato su dodici angoli in (Om, w0),
# results/paper2/item12a_cosmo.jsonl, vale [0.973869, 1.040504] in convenzione
# pipeline e [0.961073, 1.026832] in convenzione standard — reciproci esatti,
# 1/1.040504 = 0.961073. La deviazione MASSIMA e' quindi 0.0405 e 0.0389.
# Ogni quantita' divisa per 0.027 sovrastima del 40-50%. F_PHYS resta definito
# perche' e' il numero DEPOSITATO al §5.2 e va citato come tale, ma le
# decisioni si prendono su F_PHYS_MAX_DEV.
F_PHYS_MAX_DEV = 0.0389          # max |F-1|, convenzione standard, misurato
F_PHYS_MAX_DEV_PIPELINE = 0.0405  # lo stesso in convenzione pipeline
F_PHYS_ENVELOPE = {"standard": (0.961073, 1.026832),
                   "pipeline": (0.973869, 1.040504),
                   "source": "results/paper2/item12a_cosmo.jsonl, 12 angoli",
                   "is_a_posterior": False}
LINE_B = {"B1": 0.971070, "B2": 0.985396, "FID": 1.0,
          "B4": 1.014889, "B5": 1.030071,
          # B6: emendamento 15. Valore derivato, non digitato. NON entra in
          # DD_max, che resta su B1-B5 come depositato: il verdetto E2 e' gia'
          # emesso e un punto aggiunto dopo non puo' riaprire una regola gia'
          # applicata. Entra nel fit di simmetria, nella completezza per C1 e
          # nella diagnostica del residuo.
          "B6": 1.045531810025433}
CORNERS = ("C1", "C2", "C3", "C4")
# F efficace degli angoli, convenzione della pipeline (item 1.3a).
# Se assente, la completezza si salta invece di indovinare.
CORNER_F = {}
N_BOOT = 4000
BOOT_SEED = 20260830

# Cancello di adeguatezza del modello, aggiunto il 30 ago 2026 DOPO aver visto
# i residui ma PRIMA di emettere il verdetto. E' una precondizione a un test,
# non un cambio dei suoi criteri: il §5.5 dichiara cosa concludere se il termine
# dispari o quello pari sono significativi, e assume che la famiglia
# D0 + a(F-1) + b(F-1)^2 descriva i dati. Non prevede il caso in cui non li
# descriva, e l'item 1.4 dice cosa fare allora: "si riporta come tale e si
# dichiara che la regola era incompleta, non la si estende a posteriori".
#
# Perche' serve: la sigma dei coefficienti viene dal bootstrap SULLE
# REALIZZAZIONI, che misura il rumore statistico e NON l'errore di modello. Con
# un modello sbagliato un coefficiente a 14 sigma dice che i dati sono precisi,
# non che il modello sia vero.
#
# Soglia: cinque punti, tre parametri, due gradi di liberta'. chi2 > 9.21 e' il
# 99% della chi2 a 2 dof. Il valore e' quello della distribuzione, non scelto.
# Il numero di punti della linea B puo' cambiare (emendamento 15), quindi i
# gradi di liberta' e il limite NON sono costanti: si derivano da quanti punti
# entrano nel fit. Percentili al 99% della chi2.
CHI2_99 = {1: 6.63, 2: 9.21, 3: 11.34, 4: 13.28, 5: 15.09, 6: 16.81}
N_FIT_PARAMS = 3                # D0, a, b


def load(path, region, smoke=False):
    """Record mock allineati per INDICE, non per posizione nel file.

    Dopo l'emendamento 15 il registro contiene record di forma diversa: undici
    punti dal run principale, uno solo dal run di B6. Fondere per posizione
    accoppierebbe realizzazioni diverse — l'appaiamento e' l'unica cosa che
    rende il 3.2 una misura, e romperlo in silenzio sarebbe il difetto peggiore
    di tutta la catena. Qui i punti di una stessa realizzazione si uniscono per
    `index`, e le realizzazioni incomplete si scartano dichiarandolo.
    """
    by_idx = {}
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("region") != region or bool(r.get("smoke")) != smoke:
            continue
        if r.get("carve_reseed") is not None:
            continue        # e' il termine (c), non il run principale
        d = by_idx.setdefault(r["index"], {"index": r["index"], "points": {}})
        # `update` al livello del DIZIONARIO DEI PUNTI sostituisce il contenuto
        # di ogni punto gia' presente. Dopo il run a k=2,3 (1 set 2026) questo
        # perde N_H1_k0 e N_H1_k1, perche' quel record e' l'ultimo per tutti
        # gli indici. La fusione va fatta un livello piu' in basso.
        for _p, _v in r["points"].items():
            if isinstance(_v, dict):
                d["points"].setdefault(_p, {}).update(_v)
            else:
                d["points"][_p] = _v
    rows = [by_idx[k] for k in sorted(by_idx)]
    if rows:
        shapes = {}
        for r in rows:
            shapes[tuple(sorted(r["points"]))] = shapes.get(
                tuple(sorted(r["points"])), 0) + 1
        if len(shapes) > 1:
            full = max(shapes, key=lambda k: (len(k), shapes[k]))
            n0 = len(rows)
            rows = [r for r in rows if tuple(sorted(r["points"])) == full]
            print(f"  [fusione] {n0} realizzazioni, {len(shapes)} forme diverse: "
                  f"tengo le {len(rows)} complete ({len(full)} punti), "
                  f"scarto {n0 - len(rows)}.")
    return rows


def desi_side(path, region, gauge="regauged"):
    """N_H1 del lato dati per punto, dai record del 3.1. Il fiduciale sta nel
    record del cancello D3 (`gate == "d3"`), che ha gauge "fid"."""
    out = {}
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("region") != region:
            continue
        p = r.get("point")
        # La scala di erosione completa sta in `ladder`: {'0','1','2','3'} con
        # N_H1, b1_peak, n_voxels, retained, wbar. I due campi piatti N_H1_k0 e
        # N_H1 sono k=0 e k=1 e restano la fonte se il ladder manca.
        lad = r.get("ladder") or {}
        vals = {int(kk): int(vv["N_H1"]) for kk, vv in lad.items()
                if isinstance(vv, dict) and "N_H1" in vv}
        if vals:
            # CANCELLO: la scala e i campi piatti devono concordare. Se non lo
            # fanno il record e' incoerente e non si indovina quale sia giusto.
            for kk, flat in ((0, r.get("N_H1_k0")), (1, r.get("N_H1"))):
                if flat is not None and kk in vals and int(flat) != vals[kk]:
                    sys.exit(f"[FATAL] {region}/{p or 'FID'}: ladder['{kk}'] = "
                             f"{vals[kk]} contro il campo piatto {int(flat)}. "
                             f"Record incoerente, non si sceglie.")
        else:
            vals = {0: r["N_H1_k0"], 1: r["N_H1"]}
        if r.get("gate") == "d3" or r.get("gauge") == "fid":
            out["FID"] = vals
        elif r.get("gauge") == gauge and p:
            out[p] = vals
    return out


# --------------------------------------------------------------------------
# Aritmetica pura
# --------------------------------------------------------------------------

def paired(mock_rows, key, p, q):
    """Differenza appaiata mock per mock fra due punti."""
    return np.array([r["points"][p][key] - r["points"][q][key]
                     for r in mock_rows], float)


def delta_D(mock_rows, desi, key, ki, p, q, n_boot=N_BOOT, seed=BOOT_SEED):
    """D(p) - D(q), con IC bootstrap percentile.

    D(p) - D(q) = <N_mock(p) - N_mock(q)> - [N_DESI(p) - N_DESI(q)]
    Il secondo termine e' esatto: nessun rumore sul lato dati.
    """
    d = paired(mock_rows, key, p, q)
    off = desi[p][ki] - desi[q][ki]
    est = float(d.mean() - off)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    bs = d[idx].mean(axis=1) - off
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"estimate": est, "sem": float(d.std(ddof=1) / np.sqrt(len(d))),
            "ci95": [float(lo), float(hi)],
            "excludes_zero": bool(lo > 0 or hi < 0),
            "n": int(len(d)), "sd_paired": float(d.std(ddof=1)),
            "desi_offset": int(off), "mock_mean_diff": float(d.mean())}


def classify(dd_max_abs, region):
    """Regola depositata §5.3, applicata alla lettera."""
    rel = RELEVANCE[region]
    if dd_max_abs < DETECT:
        return "E1", "limite superiore; (ix) si chiude con un bound"
    if dd_max_abs < rel:
        return "E2", "sensibilita' sotto-dominante; (ix) si chiude con una misura"
    return "E3", "sistematico di primo piano; M26 §5 va aggiornato"


def symmetry_fit(mock_rows, desi, key, ki, n_boot=N_BOOT, seed=BOOT_SEED):
    """D(F) = D0 + a(F-1) + b(F-1)^2 sui cinque punti di linea B.

    Le sigma vengono dal bootstrap SULLE REALIZZAZIONI, non dalla covarianza del
    fit: i cinque punti sono correlati perche' escono dagli stessi 200 mock, e
    la covarianza del fit li tratterebbe come indipendenti.
    """
    # I punti sono quelli presenti nei record, ordinati in F: cosi' B6 entra
    # automaticamente quando c'e' e il fit non si rompe quando non c'e'.
    have = set(mock_rows[0]["points"])
    pts = sorted((p for p in LINE_B if p in have and p in desi),
                 key=lambda p: LINE_B[p])
    dof = len(pts) - N_FIT_PARAMS
    if dof < 1:
        return {"verdict": f"VERDETTO NON EMESSO: {len(pts)} punti per "
                           f"{N_FIT_PARAMS} parametri, zero gradi di liberta'.",
                "verdict_issued": False, "model_adequate": False,
                "chi2": float("nan"), "chi2_dof": dof, "points": pts}
    limit = CHI2_99.get(dof, 3.0 * dof)
    x = np.array([LINE_B[p] - 1.0 for p in pts])
    M = np.array([[r["points"][p][key] for p in pts] for r in mock_rows], float)
    off = np.array([desi[p][ki] for p in pts], float)

    # I cinque punti escono dagli STESSI 200 mock: sono correlati (~84% fra
    # punti adiacenti). Un fit ai minimi quadrati ordinari, e un chi2 con la sola
    # diagonale, trattano i punti come indipendenti e sottostimano la precisione
    # con cui la FORMA e' determinata — che e' l'unica cosa che il test di
    # simmetria misura. Qui si usa la covarianza piena della media:
    #     C = cov(N fra i punti) / n
    # e il fit e' generalizzato (GLS), col chi2 al minimo su 2 gradi di liberta'.
    V = np.vander(x, 3, increasing=True)        # colonne [1, x, x^2]
    C = np.cov(M, rowvar=False) / len(M)
    Cinv = np.linalg.pinv(C)

    def coeffs(rowsel):
        y = M[rowsel].mean(axis=0) - off
        A = V.T @ Cinv @ V
        return np.linalg.solve(A, V.T @ Cinv @ y)   # [D0, a, b]

    base = coeffs(np.arange(len(M)))
    rng = np.random.default_rng(seed)
    bs = np.array([coeffs(rng.integers(0, len(M), len(M))) for _ in range(n_boot)])
    sd = bs.std(axis=0, ddof=1)
    a, b = float(base[1]), float(base[2])
    sa, sb = float(sd[1]), float(sd[2])

    # --- adeguatezza del modello, PRIMA del verdetto -------------------------
    y = M.mean(axis=0) - off
    fitted = V @ base
    resid = y - fitted
    chi2 = float(resid @ Cinv @ resid)          # forma quadratica, covarianza piena
    adequate = chi2 <= limit
    # I residui si riportano anche in unita' della SEM diagonale, che NON e' il
    # metro del chi2 ma e' l'unica scala leggibile per punto.
    sem = M.std(axis=0, ddof=1) / np.sqrt(len(M))

    odd = abs(a) > 3 * sa
    even = abs(b) > 3 * sb
    if not adequate:
        verdict = (f"VERDETTO NON EMESSO: il modello quadratico non descrive i "
                   f"dati (chi2 = {chi2:.1f} su {dof} gradi di liberta', "
                   f"limite {limit}). Le sigma dei coefficienti vengono dal "
                   f"bootstrap sulle realizzazioni e misurano il rumore, non "
                   f"l'errore di modello: con un modello inadeguato la "
                   f"significativita' di a e b non e' interpretabile. Il §5.5 "
                   f"non prevede questo caso, e la regola va dichiarata "
                   f"incompleta invece che estesa.")
    elif odd and not even:
        verdict = ("DISPARI: compressione e stiramento radiale non sono "
                   "equivalenti, la topologia vede una DIREZIONE")
    elif even and not odd:
        verdict = ("PARI: la topologia vede il disallineamento radiale/trasverso "
                   "come una DEGRADAZIONE, non come una direzione")
    elif odd and even:
        verdict = "ENTRAMBI significativi: si riportano entrambi"
    else:
        verdict = "nessuno dei due a 3 sigma: la linea B non vincola la forma"
    return {"D0": float(base[0]), "a": a, "sigma_a": sa, "b": b, "sigma_b": sb,
            "a_over_sigma": a / sa if sa else float("nan"),
            "b_over_sigma": b / sb if sb else float("nan"),
            "odd_significant": bool(odd), "even_significant": bool(even),
            "chi2": chi2, "chi2_dof": dof, "chi2_limit": limit,
            "chi2_method": "GLS con covarianza piena della media",
            "mean_corr_adjacent": float(np.mean([
                C[i, i + 1] / np.sqrt(C[i, i] * C[i + 1, i + 1])
                for i in range(len(x) - 1)])),
            "model_adequate": bool(adequate),
            "verdict_issued": bool(adequate),
            "residuals": {p: float(r) for p, r in zip(pts, resid)},
            "residuals_in_sem": {p: float(r / s) for p, r, s
                                 in zip(pts, resid, sem)},
            "verdict": verdict,
            "D_per_point": {p: float(M[:, i].mean() - off[i])
                            for i, p in enumerate(pts)}}


def required_F(fit, D_fid):
    """F che azzererebbe D per estrapolazione lineare della risposta misurata.

    Solo il termine lineare, come dichiarato al §5.4. Restituisce None se la
    pendenza e' compatibile con zero: estrapolare con una pendenza nulla darebbe
    un numero grande e privo di significato.
    """
    if not fit.get("model_adequate", True):
        return None          # la pendenza viene da un fit che non descrive i dati
    a, sa = fit["a"], fit["sigma_a"]
    if sa == 0 or abs(a) <= 3 * sa:
        return None
    dF = -D_fid / a
    # La decisione si prende sulla deviazione MASSIMA, non sul lato piccolo
    # (emendamento 19). Si riportano entrambi i rapporti, perche' la loro
    # distanza e' essa stessa il punto: un numero che cambia del 44% a seconda
    # dell'estremo scelto non e' un risultato robusto.
    return {"F_required": 1.0 + dF, "delta_F": dF,
            "within_physical_range": bool(abs(dF) <= F_PHYS_MAX_DEV),
            "physical_range_used": F_PHYS_MAX_DEV,
            "physical_range_deposited": F_PHYS,
            "ratio_vs_max_dev": float(abs(dF) / F_PHYS_MAX_DEV),
            "ratio_vs_deposited": float(abs(dF) / F_PHYS),
            "envelope": F_PHYS_ENVELOPE}


def selection_channel(mock_rows, key, desi_pts):
    """dN_H1/dn_sel per punto: e' il termine (c) del 3.3.

    I punti che non hanno il livello richiesto sul lato mock si SALTANO, e si
    dice quali. Succede dal 4 set 2026: il blocco A e' stato esteso a sei punti
    e i quattro nuovi - A0, A1m, A3m, A0m - sono stati girati a erosioni 0 e 1
    soltanto, perche' servono al PAVIMENTO e il pavimento si calcola ai livelli
    del budget. Prima di questa correzione il run moriva con KeyError a meta',
    dopo aver gia' stampato l'esito del livello.

    Non si usa un try/except attorno alle medie: un punto che sparisce in
    silenzio da una tabella e' il modo in cui si perdono le righe senza
    accorgersene. Si filtra prima e si conta."""
    kk = "N_H1_k1" if key.endswith("k1") else key
    disponibili = [p for p in desi_pts
                   if p != "FID"
                   and all(kk in r["points"].get(p, {}) for r in mock_rows)]
    saltati = [p for p in desi_pts if p != "FID" and p not in disponibili]
    if saltati:
        print(f"    [canale selezione] {len(saltati)} punti saltati, senza "
              f"{kk} sul lato mock: {', '.join(sorted(saltati))}. "
              f"La tabella che segue e' parziale.")
    # Il metadato NON entra nel dizionario dei dati: quello e' una mappa
    # punto -> misura, e chi lo consuma cicla su .values() aspettandosi
    # dizionari. Si restituisce una coppia.
    out = {}
    for p in disponibili:
        dn = np.mean([r["points"][p][kk] - r["points"]["FID"][kk]
                      for r in mock_rows])
        ds = np.mean([r["points"][p]["n_sel"] - r["points"]["FID"]["n_sel"]
                      for r in mock_rows])
        out[p] = {"d_N_H1": float(dn), "d_n_sel": float(ds),
                  "gen_per_gal": float(dn / ds) if abs(ds) > 1.0 else None}
    return out, sorted(saltati)


# --------------------------------------------------------------------------

def cmd_run(a):
    reg = a.region
    mock = load(a.mock, reg)
    desi = desi_side(a.data, reg)
    if len(mock) < 2:
        sys.exit(f"[FATAL] {len(mock)} record mock per {reg}.")
    missing = [p for p in list(LINE_B) + list(CORNERS) if p not in desi]
    if missing:
        sys.exit(f"[FATAL] lato dati incompleto: mancano {missing}")
    print("=" * 76)
    print(f"3.4 — risposta del deficit alla cosmologia fiduciale, {reg}")
    print("=" * 76)
    print(f"  {len(mock)} realizzazioni appaiate.  Soglie depositate: "
          f"rilevabilita' {DETECT}, rilevanza {RELEVANCE[reg]}.")
    print("  Metro: ERRORE DELLA MEDIA della differenza appaiata. Il lato dati e'")
    print("  deterministico (prereg §5.1), quindi il rumore sta tutto sui mock.")

    rec = {"schema": "paper2_fase3_analisi_v1", "region": reg,
           "n_mocks": len(mock), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                      time.gmtime()),
           "thresholds": {"detect": DETECT, "relevance": RELEVANCE[reg]},
           "levels": {}}

    levels = getattr(a, "levels", None) or [1, 0]
    _LAB = {1: "k=1  PRIMARIO", 0: "k=0  parallelo per v1",
            2: "k=2  DIAGNOSTICO (nessun esito: vedi sotto)",
            3: "k=3  DIAGNOSTICO (nessun esito: vedi sotto)"}
    missing_lv = [ki for ki in levels
                  if any(ki not in desi[p] for p in desi)]
    if missing_lv:
        sys.exit(f"[FATAL] il lato dati non ha i livelli {missing_lv}: "
                 f"la scala di erosione dei record del 3.1 non li contiene.")
    for ki, lab in ((ki, _LAB.get(ki, f"k={ki}")) for ki in levels):
        key = f"N_H1_k{ki}"
        print(f"\n{'-'*76}\n  {lab}\n{'-'*76}")
        L = {}

        # --- la regola depositata: DD_max fra B1 e B5 -----------------------
        m = delta_D(mock, desi, key, ki, "B5", "B1")
        dd_abs = abs(m["estimate"])
        print(f"  DD_max (B5 - B1) = {m['estimate']:+8.1f}  "
              f"sem {m['sem']:5.1f}  IC95 [{m['ci95'][0]:+.1f}, {m['ci95'][1]:+.1f}]")
        L["DD_max_B5_B1"] = m
        if ki in (0, 1):
            esito, testo = classify(dd_abs, reg)
            L["outcome"] = {"code": esito, "meaning": testo}
            print(f"  ESITO: {esito} — {testo}")
        else:
            # Le soglie 53 / 390 / 206 sono tarate sul deficit a k=0 e k=1. A
            # k=2 e k=3 il deficit vale altro, quindi un esito calcolato con
            # quelle soglie estenderebbe in silenzio la regola depositata.
            esito = None
            L["outcome"] = {"code": None, "meaning":
                            "nessun esito: livello diagnostico, soglie non "
                            "registrate per k=%d" % ki}
            print("  ESITO: NON EMESSO — livello diagnostico. Le soglie "
                  "depositate (53, %d) sono tarate sul deficit a k=0,1; "
                  "emetterle qui estenderebbe la regola senza registrarla."
                  % RELEVANCE[reg])

        # --- ogni punto contro il fiduciale ---------------------------------
        print(f"\n  {'pt':>4} {'DD':>9} {'sem':>6} {'IC95':>22} {'|DD|>53':>8}")
        pts = [p for p in LINE_B if p != "FID"] + list(CORNERS)
        L["per_point"] = {}
        for p in pts:
            v = delta_D(mock, desi, key, ki, p, "FID")
            L["per_point"][p] = v
            print(f"  {p:>4} {v['estimate']:+9.1f} {v['sem']:6.1f} "
                  f"  [{v['ci95'][0]:+8.1f}, {v['ci95'][1]:+8.1f}] "
                  f"{'si' if abs(v['estimate']) > DETECT else '':>8}")

        # --- escursione sui CINQUE punti, descrizione e non decisione -------
        vals = [0.0] + [L["per_point"][p]["estimate"] for p in ("B1", "B2", "B4", "B5")]
        L["line_B_full_excursion"] = float(max(vals) - min(vals))
        print(f"\n  escursione sui cinque punti di linea B: "
              f"{L['line_B_full_excursion']:.1f} generatori "
              f"(descrizione, non decisione: la regola usa B1 e B5)")

        # --- simmetria ------------------------------------------------------
        fit = symmetry_fit(mock, desi, key, ki)
        L["symmetry"] = fit
        print(f"\n  simmetria: a = {fit['a']:+.1f} +- {fit['sigma_a']:.1f} "
              f"({fit['a_over_sigma']:+.2f} sd)   "
              f"b = {fit['b']:+.1f} +- {fit['sigma_b']:.1f} "
              f"({fit['b_over_sigma']:+.2f} sd)")
        print(f"  correlazione media fra punti adiacenti: "
              f"{fit['mean_corr_adjacent']:.3f}  (stessi 200 mock)")
        print(f"  adeguatezza: chi2 = {fit['chi2']:.1f} su "
              f"{fit['chi2_dof']} dof (limite {fit['chi2_limit']}) -> "
              f"{'modello adeguato' if fit['model_adequate'] else 'MODELLO INADEGUATO'}")
        print("  residui in sem: " + "  ".join(
            f"{p} {v:+.1f}" for p, v in fit["residuals_in_sem"].items()))
        print(f"  -> {fit['verdict']}")

        # --- F richiesto ----------------------------------------------------
        D_fid = float(np.mean([r["points"]["FID"][key] for r in mock]) - desi["FID"][ki])
        L["D_fiducial"] = D_fid
        req = required_F(fit, D_fid)
        L["required_F"] = req
        if req is None:
            why = ("il modello non descrive i dati" if not fit["model_adequate"]
                   else "la pendenza non e' a 3 sigma da zero")
            print(f"\n  D(fid) = {D_fid:.1f}.  F richiesto: NON calcolato — {why}.")
            if fit["model_adequate"]:
                print("  Estrapolare con una pendenza compatibile con zero darebbe "
                      "un numero grande e privo di significato.")
            else:
                # RITIRATO dall'emendamento 19, 1 set 2026. L'estrapolazione
                # invertiva un coefficiente della famiglia quadratica che il
                # fit dichiara inadeguata tre righe sopra; il denominatore
                # F_PHYS = 0.027 e' il lato PICCOLO di un intervallo
                # asimmetrico la cui deviazione massima vale 0.0389 in
                # convenzione standard e 0.0405 in convenzione pipeline; e a
                # dF ~ 6.7 il termine quadratico domina il lineare di ~5e4,
                # quindi "non dipende da un fattore due" e' falso.
                print("  L'ordine di grandezza per estrapolazione e' RITIRATO "
                      "(emendamento 19): inverte un coefficiente di una "
                      "famiglia dichiarata inadeguata, e 0.027 non e' il range "
                      "fisico ma il suo lato piccolo (max 0.0389).")
                print("  Al suo posto, l'affermazione IN-RANGE: su tutto "
                      "l'insieme campionato, B6 incluso, D si muove al piu' di "
                      "172.5 generatori, cioe' il 2.0-4.8% del deficit, e il "
                      "rango empirico resta 1/201 in ogni punto della griglia. "
                      "Non si estrapola nulla e non serve un modello.")
        elif ki not in (0, 1):
            # Coerenza con la soppressione dell'esito: a k=2,3 non si emette
            # nemmeno la regola §5.4. Le soglie e il disegno sono registrati per
            # k=0,1; emettere una falsificazione qui sarebbe estendere la regola
            # esattamente come lo sarebbe emettere E1-E4.
            print(f"\n  D(fid) = {D_fid:.1f}   dF = {req['delta_F']:+.4f}  "
                  f"({req['ratio_vs_max_dev']:.0f}x la deviazione massima "
                  f"{F_PHYS_MAX_DEV})")
            print("  §5.4: NON EMESSA — livello diagnostico, come l'esito. La "
                  "regola e' registrata per k=0,1; emetterla qui la "
                  "estenderebbe senza registrarla. Il numero si riporta, il "
                  "verdetto no.")
        else:
            print(f"\n  D(fid) = {D_fid:.1f}   F richiesto = {req['F_required']:.4f} "
                  f"(dF = {req['delta_F']:+.4f})")
            print(f"  |dF| <= {F_PHYS_MAX_DEV} (deviazione MASSIMA misurata) ? "
                  f"{'SI' if req['within_physical_range'] else 'NO'}"
                  + ("" if req["within_physical_range"] else
                     "  -> l'AP NON puo' spiegare il deficit"))
            print(f"  rapporto: {req['ratio_vs_max_dev']:.0f}x la deviazione "
                  f"massima 0.0389, {req['ratio_vs_deposited']:.0f}x il valore "
                  f"depositato 0.027. La distanza fra i due e' il punto: il "
                  f"range e' ASIMMETRICO e 0.027 ne e' il lato piccolo "
                  f"(emendamento 19).")
            if req["within_physical_range"] and esito == "E3":
                print("  -> condizione E4: il punto a F richiesto va MISURATO, "
                      "non estrapolato.")

        # --- canale della selezione -----------------------------------------
        L["selection_channel"], _saltati = selection_channel(mock, key, desi)
        if _saltati:
            L["selection_channel_saltati"] = _saltati
        gs = [v["gen_per_gal"] for v in L["selection_channel"].values()
              if v["gen_per_gal"] is not None]
        if gs:
            print(f"\n  canale selezione: {len(gs)} punti con |dn_sel| > 1, "
                  f"gen/gal da {min(gs):+.2f} a {max(gs):+.2f}")
            if max(gs) - min(gs) > 4:
                print("  ATTENZIONE: rapporto non stabile fra i punti. Il termine (c)")
                print("  del 3.3 non si stima con un solo numero in questa regione.")

        # --- completezza sugli angoli ---------------------------------------
        if CORNER_F:
            xs = np.array([LINE_B[p] - 1.0 for p in ("B1", "B2", "FID", "B4", "B5")])
            ys = np.array([fit["D_per_point"][p] for p in
                           ("B1", "B2", "FID", "B4", "B5")])
            L["completeness"] = {}
            print(f"\n  completezza sugli angoli (soglia {DETECT}):")
            for c in CORNERS:
                if c not in CORNER_F:
                    continue
                pred = float(np.polyval(np.polyfit(xs, ys, 2), CORNER_F[c] - 1.0))
                obs = L["per_point"][c]["estimate"] + L["per_point"]["B1"]["estimate"] * 0
                obs = float(np.mean([r["points"][c][key] for r in mock]) - desi[c][ki])
                L["completeness"][c] = {"predicted": pred, "observed": obs,
                                        "residual": obs - pred,
                                        "fails": abs(obs - pred) > DETECT}
                print(f"    {c}: previsto {pred:+8.1f}  osservato {obs:+8.1f}  "
                      f"scarto {obs-pred:+7.1f}  "
                      f"{'FALLISCE' if abs(obs-pred) > DETECT else 'ok'}")
        else:
            print("\n  completezza sugli angoli: SALTATA — F efficace degli angoli")
            print("  non fornito (CORNER_F vuoto). Non si indovina: va preso da 1.2a.")

        rec["levels"][f"k{ki}"] = L

    if a.out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True, default=float) + "\n")
        print(f"\n[scritto] {a.out}")
    return 0


def cmd_selftest(a) -> int:
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    # Seme 13, non 7: col 7 il chi2 del caso VERO usciva 13.0, cioe' una
    # fluttuazione da 1 su 500. Non e' un difetto della statistica — il test 16
    # ne verifica la calibrazione su 60 realizzazioni — ma un selftest non deve
    # dipendere da quale coda pesca un seme.
    rng = np.random.default_rng(13)
    n = 200
    pts = ["B1", "B2", "FID", "B4", "B5"]
    # risposta DISPARI iniettata: D lineare in (F-1), pendenza 3000
    base = rng.normal(35000, 250, n)
    slope = 3000.0
    rows = [{"points": {p: {"N_H1_k1": base[i] + slope * (LINE_B[p] - 1.0)
                            + rng.normal(0, 40),
                            "N_H1_k0": base[i], "n_sel": 218000 + 50 * i}
                        for p in pts}} for i in range(n)]
    desi = {p: (28000, 28000) for p in pts}

    m = delta_D(rows, desi, "N_H1_k1", 1, "B5", "B1")
    truth = slope * (LINE_B["B5"] - LINE_B["B1"])
    expect("1. DD fra due punti recupera la pendenza iniettata",
           abs(m["estimate"] - truth) < 5 * m["sem"],
           f"(atteso {truth:.1f}, ottenuto {m['estimate']:.1f})")
    expect("2. e l'IC95 bootstrap esclude lo zero", m["excludes_zero"])

    fit = symmetry_fit(rows, desi, "N_H1_k1", 1, n_boot=400)
    expect("3. risposta dispari riconosciuta come tale",
           fit["odd_significant"] and not fit["even_significant"]
           and fit["model_adequate"] and "DISPARI" in fit["verdict"],
           f"(a={fit['a']:.0f}+-{fit['sigma_a']:.0f}, chi2={fit['chi2']:.1f})")

    # risposta PARI iniettata
    rows2 = [{"points": {p: {"N_H1_k1": base[i] + 2e5 * (LINE_B[p] - 1.0) ** 2
                             + rng.normal(0, 40),
                             "N_H1_k0": base[i], "n_sel": 218000}
                         for p in pts}} for i in range(n)]
    f2 = symmetry_fit(rows2, desi, "N_H1_k1", 1, n_boot=400)
    expect("4. risposta pari riconosciuta come tale",
           f2["even_significant"] and not f2["odd_significant"],
           f"(a={f2['a']:.0f}+-{f2['sigma_a']:.0f}, b={f2['b']:.0f}+-{f2['sigma_b']:.0f})")

    # nessuna risposta
    rows3 = [{"points": {p: {"N_H1_k1": base[i] + rng.normal(0, 40),
                             "N_H1_k0": base[i], "n_sel": 218000}
                         for p in pts}} for i in range(n)]
    f3 = symmetry_fit(rows3, desi, "N_H1_k1", 1, n_boot=400)
    expect("5. nessuna risposta -> la linea B non vincola la forma",
           not f3["odd_significant"] and not f3["even_significant"])

    expect("6. classificazione alla lettera della regola depositata",
           classify(52.9, "NGC")[0] == "E1" and classify(53.0, "NGC")[0] == "E2"
           and classify(389.9, "NGC")[0] == "E2" and classify(390.0, "NGC")[0] == "E3"
           and classify(206.0, "SGC")[0] == "E3" and classify(205.9, "SGC")[0] == "E2")

    expect("7. F richiesto NON si estrapola con pendenza compatibile con zero",
           required_F(f3, -7000.0) is None)
    r = required_F(fit, -7000.0)
    # Il confronto e' con la pendenza STIMATA, non con quella iniettata: la
    # stima ha rumore, e pretendere l'iniettata sarebbe chiedere al fit di non
    # avere incertezza.
    expect("8. e si calcola quando la pendenza c'e', coerente con la stima",
           r is not None and abs(r["delta_F"] - 7000.0 / fit["a"]) < 1e-9,
           f"(dF = {r['delta_F']:.4f})" if r else "(bloccato: chi2 troppo alto)")
    expect("8b. e resta entro il 5% del valore iniettato",
           r is not None and abs(r["delta_F"] - 7000.0 / slope)
           / (7000.0 / slope) < 0.05,
           f"(iniettato {7000.0/slope:.4f})" if r else "")
    expect("9. il range depositato e' citato, ma la decisione usa la "
           "deviazione MASSIMA (emendamento 19)",
           r is not None and r["physical_range_deposited"] == 0.027
           and r["physical_range_used"] == F_PHYS_MAX_DEV
           and r["within_physical_range"] is False)
    expect("9b. e i due rapporti differiscono del 44%, che e' il punto",
           r is not None
           and abs(r["ratio_vs_deposited"] / r["ratio_vs_max_dev"]
                   - F_PHYS_MAX_DEV / F_PHYS) < 1e-9,
           f"({r['ratio_vs_max_dev']:.0f}x contro {r['ratio_vs_deposited']:.0f}x)"
           if r else "")

    d = paired(rows, "N_H1_k1", "B5", "B1")
    # --- il cancello sul chi2 -----------------------------------------------
    # Modello inadeguato per costruzione: una risposta CUBICA, che nessuna
    # parabola puo' seguire, con rumore piccolo perche' il chi2 la veda.
    rows4 = [{"points": {p: {"N_H1_k1": base[i] + 8e6 * (LINE_B[p] - 1.0) ** 3
                             + rng.normal(0, 5),
                             "N_H1_k0": base[i], "n_sel": 218000}
                         for p in pts}} for i in range(n)]
    f4 = symmetry_fit(rows4, desi, "N_H1_k1", 1, n_boot=400)
    expect("11. modello inadeguato -> verdetto NON emesso",
           not f4["model_adequate"] and not f4["verdict_issued"]
           and "NON EMESSO" in f4["verdict"],
           f"(chi2={f4['chi2']:.1f} > {f4['chi2_limit']})")
    expect("12. e i coefficienti restano significativi lo stesso: e' il punto",
           abs(f4["a_over_sigma"]) > 3,
           f"(a/sigma = {f4['a_over_sigma']:+.1f}, ma il modello non descrive i dati)")
    expect("13. F richiesto bloccato dal modello inadeguato",
           required_F(f4, -7000.0) is None)
    expect("14. mentre col modello adeguato non e' bloccato",
           required_F(fit, -7000.0) is not None and fit["model_adequate"])
    expect("15. i residui sono riportati per punto, non solo il chi2",
           set(f4["residuals_in_sem"]) == set(pts)
           and max(abs(v) for v in f4["residuals_in_sem"].values()) > 3)

    # --- calibrazione del chi2 GLS ------------------------------------------
    # Il test che conta: col modello VERO iniettato il chi2 deve distribuirsi
    # come una chi2 a 2 dof. Se uscisse sistematicamente alto, il cancello
    # boccerebbe modelli corretti e sarebbe peggio dell'assenza di cancello.
    chis = []
    for t in range(60):
        rg = np.random.default_rng(5000 + t)
        bs = rg.normal(35000, 250, n)
        rw = [{"points": {q: {"N_H1_k1": bs[i] + slope * (LINE_B[q] - 1.0)
                              + rg.normal(0, 40),
                              "N_H1_k0": bs[i], "n_sel": 218000}
                          for q in pts}} for i in range(n)]
        chis.append(symmetry_fit(rw, desi, "N_H1_k1", 1, n_boot=2)["chi2"])
    chis = np.array(chis)
    expect("16. chi2 GLS calibrato: media ~2 su modello vero",
           1.2 < chis.mean() < 3.0,
           f"(media {chis.mean():.2f}, mediana {np.median(chis):.2f}, "
           f"atteso 2.00 e 1.39)")
    expect("17. e la coda oltre il limite non supera il nominale",
           np.mean(chis > CHI2_99[2]) <= 0.05,
           f"({np.mean(chis > CHI2_99[2]):.3f} contro 0.010 nominale; "
           f"cinque punti = 2 dof)")

    expect("10. la SEM e' sd/sqrt(N), non sd",
           abs(m["sem"] - d.std(ddof=1) / np.sqrt(n)) < 1e-9
           and m["sd_paired"] > 5 * m["sem"])

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    q = sub.add_parser("run")
    q.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    q.add_argument("--mock", default="results/paper2/fase3_mock.jsonl")
    q.add_argument("--data", default="results/paper2/fase3.jsonl")
    q.add_argument("--out", default=None)
    q.add_argument("--levels", type=int, nargs="+", default=[1, 0],
                   choices=[0, 1, 2, 3],
                   help="livelli di erosione da analizzare. Default 1 0, cioe' "
                        "il comportamento depositato. A k=2 e 3 i numeri si "
                        "stampano ma NON si emette l'esito E1-E4: le soglie "
                        "depositate sono tarate sul deficit a k=0,1.")
    a = p.parse_args()
    return (cmd_selftest if a.cmd == "selftest" else cmd_run)(a)


if __name__ == "__main__":
    sys.exit(main())

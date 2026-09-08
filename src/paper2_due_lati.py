#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 — decomposizione di D nei suoi due lati, e i controlli che
il referee report chiede senza run.

PERCHE' ESISTE
  Tutta la Fase 3 poggia su D(g) = <N_H1>_mock(g) - N_H1^DESI(g), e la
  giustificazione del disegno era una frase: "l'AP agisce su entrambi i lati,
  quindi una risposta comune si cancella in D". Quella frase e' stata ASSERITA e
  mai verificata, e nessun numero pubblicato permetteva di controllarla: si
  riportava solo la differenza.

  E' il rilievo BLOCCANTE del referee, ed e' gratis: i due lati sono gia' nei
  registri.

LE DUE IPOTESI, CHE HANNO IMPLICAZIONI OPPOSTE
  (1) Il lato mock e' quasi inerte all'AP. Nel carving le posizioni comoventi
      passano per r -> z_cosmo -> (RSD) -> r' con la STESSA D_C in andata e
      ritorno: il giro resta l'identita' a meno dello spostamento RSD, e la
      struttura intrinseca del mock non viene deformata. Il lato mock risponde
      solo attraverso la maschera (che viene dai random, e quelli si deformano),
      la registrazione del tiling e il residuo RSD.
      -> Il disegno funziona, ma la MOTIVAZIONE va riscritta: non e'
         cancellazione di modo comune, e' inerzia del lato mock.
  (2) Entrambi i lati si deformano. Allora DD_max = -98.3 e' una piccola
      differenza fra numeri grandi, con un budget calibrato sulla differenza, e
      "la sensibilita' AP e' sotto-dominante" varrebbe solo per la configurazione
      in cui si deformano simultaneamente i due lati — che NON e' la
      configurazione della limitazione (ix), la quale e' asimmetrica: se il
      fiduciale e' sbagliato, il campo osservato e' distorto mentre i mock hanno
      la struttura della loro cosmologia.

COSA CALCOLA
  1. I due lati separati, per punto, emisfero e livello.
  2. Delta_dati e Delta_mock fra due punti, col loro rapporto.
  3. Rango empirico e deficit frazionario PER PUNTO — le grandezze su cui
     poggiano M26 e il Paper 1, e che la Fase 3 non riportava.
  4. Il fit di forma sul SOLO lato mock, con la sua covarianza. Se li' il chi2
     torna, il rifiuto del modello era un artefatto di costruzione: la covarianza
     usata nel GLS e' del solo lato mock, ma i residui contengono anche la
     struttura del lato dati, che in quella covarianza non ha rappresentazione.
  5. La dispersione delle 200 pendenze dD/dF calcolate mock per mock. Misura
     l'incertezza sulla pendenza di UNA realizzazione, che non e' in nessun
     errore riportato ed e' la crepa vera nella scelta del denominatore.
  6. Correlazione fra emisferi sulle realizzazioni appaiate.
  7. Contrasti dispari e pari senza modello.

Uso:
    python src\\paper2_due_lati.py selftest
    python src\\paper2_due_lati.py run --region NGC
    python src\\paper2_due_lati.py run --region SGC --out results\\paper2\\due_lati.jsonl
    python src\\paper2_due_lati.py cross          # correlazione fra emisferi
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

LINE_B = {"B1": 0.971070, "B2": 0.985396, "FID": 1.0,
          "B4": 1.014889, "B5": 1.030071, "B6": 1.045531810025433}
CORNERS = ("C1", "C2", "C3", "C4")
BLOCK_A = ("A1", "A3")
N_BOOT = 4000
BOOT_SEED = 20260831
CHI2_99 = {1: 6.63, 2: 9.21, 3: 11.34, 4: 13.28}


def load_jsonl(path):
    p = Path(path)
    return [] if not p.exists() else [
        json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def collect(a, region):
    """Lato dati per punto, e lato mock per punto indicizzato per realizzazione."""
    D = {}
    for r in load_jsonl(a.data):
        if r.get("region") != region:
            continue
        nm = "FID" if (r.get("gate") == "d3" or r.get("gauge") == "fid") else r.get("point")
        if nm and r.get("gauge") in ("regauged", "fid"):
            D[nm] = r
    M = {}
    for r in load_jsonl(a.mock):
        if r.get("region") != region or r.get("smoke") \
                or r.get("carve_reseed") is not None:
            continue
        for q, v in r["points"].items():
            # FUSIONE per (punto, indice), non last-wins: il registro contiene
            # record di forma diversa — undici punti a k=0,1 dal run principale,
            # un punto solo dal run di B6, e i livelli k=2,3 da un run separato.
            # Sovrascrivere farebbe sparire k=0 e k=1 appena arriva un record
            # che porta solo i livelli diagnostici.
            M.setdefault(q, {}).setdefault(r["index"], {}).update(v)
    if "FID" not in D or "FID" not in M:
        sys.exit(f"[FATAL] fiduciale assente per {region}")
    return D, M


def two_sides(D, M, ki):
    """Le due colonne che mancavano. Nessun modello, nessuna sottrazione."""
    dkey = "N_H1" if ki == 1 else "N_H1_k0"
    mkey = f"N_H1_k{ki}"
    idx0 = set(M["FID"])
    rows = []
    for p in list(LINE_B) + list(CORNERS) + list(BLOCK_A):
        if p not in D or p not in M:
            continue
        idx = sorted(i for i in (idx0 & set(M[p]))
                     if mkey in M[p][i] and mkey in M["FID"][i])
        if len(idx) < 10:
            print(f"  [avviso] {p}: {len(idx)} realizzazioni con {mkey}, salto")
            continue
        v = np.array([M[p][i][mkey] for i in idx], float)
        desi = float(D[p][dkey])
        # Rango empirico: quanti mock stanno sotto DESI, su n+1. E' la statistica
        # primaria di M26 e del Paper 1, e la Fase 3 non la riportava per punto.
        n_below = int((v < desi).sum())
        rows.append({
            "pt": p, "n": len(idx),
            "desi": desi, "mock_mean": float(v.mean()),
            "mock_sd": float(v.std(ddof=1)),
            "mock_sem": float(v.std(ddof=1) / np.sqrt(len(idx))),
            "D": float(v.mean() - desi),
            "deficit_frac": float((v.mean() - desi) / v.mean()),
            "rank": f"{n_below + 1}/{len(idx) + 1}",
            "n_mock_below_desi": n_below,
        })
    return rows


def split_delta(D, M, ki, p, q, n_boot=N_BOOT, seed=BOOT_SEED):
    """Delta fra due punti, LATO PER LATO. E' il numero che il referee chiede."""
    dkey = "N_H1" if ki == 1 else "N_H1_k0"
    mkey = f"N_H1_k{ki}"
    idx = sorted(i for i in (set(M[p]) & set(M[q]))
                 if mkey in M[p][i] and mkey in M[q][i])
    if len(idx) < 10:
        return {"pair": f"{p}-{q}", "n": len(idx), "delta_data": float("nan"),
                "delta_mock": float("nan"), "delta_mock_sem": float("nan"),
                "delta_mock_ci95": [float("nan")] * 2,
                "ratio_mock_over_data": float("nan"), "DD": float("nan")}
    dm = np.array([M[p][i][mkey] - M[q][i][mkey] for i in idx], float)
    dd = float(D[p][dkey] - D[q][dkey])
    rng = np.random.default_rng(seed)
    bs = dm[rng.integers(0, len(dm), size=(n_boot, len(dm)))].mean(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"pair": f"{p}-{q}", "n": len(idx),
            "delta_data": dd,                     # ESATTO: nessun rumore
            "delta_mock": float(dm.mean()),
            "delta_mock_sem": float(dm.std(ddof=1) / np.sqrt(len(dm))),
            "delta_mock_ci95": [float(lo), float(hi)],
            "ratio_mock_over_data": (float(dm.mean() / dd) if dd else float("nan")),
            "DD": float(dm.mean() - dd)}


def mock_only_fit(M, ki, n_boot=1000, seed=BOOT_SEED):
    """Il fit di forma sul SOLO lato mock, con la sua covarianza.

    La covarianza usata nel GLS della Fase 3 e' quella del lato mock, perche' il
    lato dati e' deterministico e non contribuisce varianza. Ma i residui al fit
    contengono ANCHE la struttura del lato dati, che in quella covarianza non ha
    rappresentazione: si chiede a un modello di descrivere le irregolarita' di una
    singola realizzazione con barre d'errore che descrivono la media di duecento.
    Qui si toglie il lato dati e si guarda se il modello regge.
    """
    mkey = f"N_H1_k{ki}"
    have = set(M)
    pts = sorted((p for p in LINE_B if p in have), key=lambda p: LINE_B[p])
    idx = sorted(i for i in set.intersection(*(set(M[p]) for p in pts))
                 if all(mkey in M[p][i] for p in pts))
    A = np.array([[M[p][i][mkey] for p in pts] for i in idx], float)
    x = np.array([LINE_B[p] - 1.0 for p in pts])
    dof = len(pts) - 3
    if dof < 1 or len(idx) < 20:
        return {"verdict": "punti o realizzazioni insufficienti", "chi2": float("nan")}
    V = np.vander(x, 3, increasing=True)
    C = np.cov(A, rowvar=False) / len(A)
    Ci = np.linalg.pinv(C)
    beta = np.linalg.solve(V.T @ Ci @ V, V.T @ Ci @ A.mean(axis=0))
    res = A.mean(axis=0) - V @ beta
    chi2 = float(res @ Ci @ res)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        s = rng.integers(0, len(A), len(A))
        y = A[s].mean(axis=0)
        bs.append(np.linalg.solve(V.T @ Ci @ V, V.T @ Ci @ y))
    sd = np.array(bs).std(axis=0, ddof=1)
    return {"points": pts, "n_mock": len(idx), "chi2": chi2, "dof": dof,
            "limit": CHI2_99.get(dof, 3.0 * dof),
            "adequate": bool(chi2 <= CHI2_99.get(dof, 3.0 * dof)),
            "a": float(beta[1]), "sigma_a": float(sd[1]),
            "b": float(beta[2]), "sigma_b": float(sd[2]),
            "residuals_in_sem": {p: float(r / np.sqrt(C[i, i]))
                                 for i, (p, r) in enumerate(zip(pts, res))}}


def per_realisation_slopes(D, M, ki):
    """Pendenza dD/dF calcolata MOCK PER MOCK.

    La SEM misura l'incertezza sulla pendenza della MEDIA mock, non su quella del
    lato dati, che e' una singola realizzazione. Se la risposta e' dipendente
    dalla realizzazione, la pendenza di DESI e' incerta di quella quantita' e non
    e' in nessun errore riportato. E' la crepa vera nella scelta del denominatore,
    e si misura senza run.
    """
    mkey = f"N_H1_k{ki}"
    pts = [p for p in ("B1", "B2", "FID", "B4", "B5", "B6") if p in M]
    idx = sorted(i for i in set.intersection(*(set(M[p]) for p in pts))
                 if all(mkey in M[p][i] for p in pts))
    x = np.array([LINE_B[p] - 1.0 for p in pts])
    xc = x - x.mean()
    sl = []
    for i in idx:
        y = np.array([M[p][i][mkey] for p in pts], float)
        sl.append(float(np.sum(xc * (y - y.mean())) / np.sum(xc * xc)))
    sl = np.array(sl)
    return {"n": len(sl), "mean": float(sl.mean()), "sd": float(sl.std(ddof=1)),
            "sem": float(sl.std(ddof=1) / np.sqrt(len(sl))),
            "sd_over_mean": float(abs(sl.std(ddof=1) / sl.mean()))
            if sl.mean() else float("nan")}


def contrasts(D, M, ki, n_boot=N_BOOT, seed=BOOT_SEED):
    """Contrasti dispari e pari sulla linea B, SENZA modello.

    Il dispari coincide quasi con DD_max: si riporta, segnalando la circolarita'.
    Il pari e' genuinamente nuovo e puo' emettere il verdetto di simmetria senza
    fit, che e' il punto: la linea B fu campionata simmetricamente apposta.
    """
    dkey = "N_H1" if ki == 1 else "N_H1_k0"
    mkey = f"N_H1_k{ki}"
    need = ("B1", "B2", "FID", "B4", "B5")
    if not all(p in M and p in D for p in need):
        return {}
    idx = sorted(i for i in set.intersection(*(set(M[p]) for p in need))
                 if all(mkey in M[p][i] for p in need))
    if len(idx) < 10:
        return {}

    def Dv(p, i):
        return M[p][i][mkey] - float(D[p][dkey])

    odd = np.array([(Dv("B5", i) - Dv("B1", i)) + (Dv("B4", i) - Dv("B2", i))
                    for i in idx], float)
    even = np.array([(Dv("B5", i) + Dv("B1", i) - 2 * Dv("FID", i))
                     + (Dv("B4", i) + Dv("B2", i) - 2 * Dv("FID", i))
                     for i in idx], float)
    rng = np.random.default_rng(seed)
    out = {}
    for nm, v in (("odd", odd), ("even", even)):
        b = v[rng.integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
        lo, hi = np.percentile(b, [2.5, 97.5])
        out[nm] = {"estimate": float(v.mean()),
                   "sem": float(v.std(ddof=1) / np.sqrt(len(v))),
                   "ci95": [float(lo), float(hi)],
                   "excludes_zero": bool(lo > 0 or hi < 0)}
    return out


def cmd_run(a):
    reg = a.region
    D, M = collect(a, reg)
    rec = {"schema": "paper2_due_lati_v1", "region": reg,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "levels": {}}
    print("=" * 88)
    print(f"I DUE LATI DI D — {reg}")
    print("=" * 88)
    for ki, lab in ((1, "k=1  PRIMARIO"), (0, "k=0")):
        print(f"\n{'-'*88}\n  {lab}\n{'-'*88}")
        rows = two_sides(D, M, ki)
        print(f"  {'pt':>4} {'N_H1 DESI':>10} {'<N_H1> mock':>12} {'sd':>7} "
              f"{'D':>9} {'deficit':>9} {'rango':>9}")
        for r in rows:
            print(f"  {r['pt']:>4} {r['desi']:10.0f} {r['mock_mean']:12.2f} "
                  f"{r['mock_sd']:7.1f} {r['D']:9.1f} "
                  f"{100*r['deficit_frac']:8.2f}% {r['rank']:>9}")

        ranks = {r["rank"] for r in rows}
        print(f"\n  ranghi distinti su tutti i punti: {sorted(ranks)}")
        dfs = [100 * r["deficit_frac"] for r in rows]
        print(f"  deficit da {min(dfs):.2f}% a {max(dfs):.2f}%  "
              f"(escursione {max(dfs)-min(dfs):.2f} punti percentuali)")

        sp = split_delta(D, M, ki, "B5", "B1")
        print(f"\n  I DUE LATI DEL DELTA, B5 - B1:")
        print(f"    lato dati  {sp['delta_data']:+9.1f}   (esatto, nessun rumore)")
        print(f"    lato mock  {sp['delta_mock']:+9.1f} +- {sp['delta_mock_sem']:.1f}"
              f"   IC95 [{sp['delta_mock_ci95'][0]:+.1f}, {sp['delta_mock_ci95'][1]:+.1f}]")
        print(f"    rapporto mock/dati = {sp['ratio_mock_over_data']:+.3f}")
        print(f"    DD_max = {sp['DD']:+.1f}")
        rr = abs(sp["ratio_mock_over_data"])
        if rr < 0.2:
            print("    -> IL LATO MOCK E' QUASI INERTE. Il disegno funziona, ma la")
            print("       motivazione va riscritta: non e' cancellazione di modo")
            print("       comune, e' inerzia del lato mock. D e' dominato dai dati.")
        elif rr > 2.0:
            print("    -> IL LATO MOCK DOMINA. Non era una delle due ipotesi: il")
            print("       lato mock risponde PIU' del lato dati, quindi D e'")
            print("       dominato da come i mock reagiscono al fiduciale, non da")
            print("       come si distorce il campo osservato. Il candidato e' lo")
            print("       spostamento RSD, che sul lato mock viene RICALCOLATO con")
            print("       la D_C iniettata mentre sul lato dati i redshift sono")
            print("       osservabili fissi. Va isolato col test in spazio reale.")
        elif rr > 0.7:
            print("    -> ENTRAMBI I LATI SI DEFORMANO. DD_max e' una piccola")
            print("       differenza fra numeri grandi: il risultato va ripensato,")
            print("       e la limitazione (ix) e' una domanda ASIMMETRICA che")
            print("       questo disegno non pone.")
        else:
            print("    -> regime intermedio: entrambe le letture restano aperte.")

        mf = mock_only_fit(M, ki)
        print(f"\n  FIT DI FORMA SUL SOLO LATO MOCK:")
        if np.isfinite(mf.get("chi2", np.nan)):
            print(f"    chi2 = {mf['chi2']:.1f} su {mf['dof']} dof "
                  f"(limite {mf['limit']}) -> "
                  f"{'ADEGUATO' if mf['adequate'] else 'respinto'}")
            print(f"    a = {mf['a']:+.1f} +- {mf['sigma_a']:.1f}   "
                  f"b = {mf['b']:+.1f} +- {mf['sigma_b']:.1f}")
            print("    residui: " + "  ".join(
                f"{p} {v:+.1f}" for p, v in mf["residuals_in_sem"].items()))
            if mf["adequate"]:
                print("    -> IL MODELLO REGGE SUI MOCK. Il rifiuto in Fase 3 e'")
                print("       allora un artefatto di costruzione: la covarianza e'")
                print("       del solo lato mock, i residui contengono anche la")
                print("       struttura del lato dati, che li' non e' rappresentata.")
            else:
                print("    -> respinto anche qui: il problema di forma e' reale.")

        sl = per_realisation_slopes(D, M, ki)
        print(f"\n  PENDENZE MOCK PER MOCK ({sl['n']} realizzazioni):")
        print(f"    media {sl['mean']:+.1f}   sd {sl['sd']:.1f}   "
              f"sd/media {sl['sd_over_mean']:.3f}")
        print(f"    L'incertezza sulla pendenza di UNA realizzazione e' {sl['sd']:.1f},")
        print(f"    contro {sl['sem']:.1f} sulla media. Se il lato dati risponde come")
        print(f"    un mock, la sua pendenza e' incerta di {sl['sd']:.1f} e questo")
        print(f"    NON e' in nessun errore riportato.")
        if np.isfinite(sp.get("delta_data", np.nan)):
            dF = LINE_B["B5"] - LINE_B["B1"]
            s_data = sp["delta_data"] / dF
            z = (s_data - sl["mean"]) / sl["sd"] if sl["sd"] else float("nan")
            sd_gen = sl["sd"] * dF
            print(f"\n    CONFRONTO DIRETTO: pendenza del lato dati "
                  f"{s_data:+.0f}, distribuzione dei mock "
                  f"{sl['mean']:+.0f} +- {sl['sd']:.0f}  ->  {z:+.2f} sd")
            print(f"    Sotto l'ipotesi nulla 'il campo osservato risponde come un")
            print(f"    mock', DD_max ha dispersione {sd_gen:.1f} generatori e vale")
            print(f"    {abs(sp['DD'])/sd_gen:.2f} sd. E' una quantita' DIVERSA dalla")
            print(f"    SEM, e risponde a una domanda diversa: non 'D si muove?' ma")
            print(f"    'il campo osservato risponde in modo anomalo?'.")

        ct = contrasts(D, M, ki)
        if ct:
            print(f"\n  CONTRASTI SENZA MODELLO:")
            for nm, lb in (("odd", "dispari"), ("even", "pari  ")):
                c = ct[nm]
                print(f"    {lb} {c['estimate']:+9.1f} +- {c['sem']:.1f}   "
                      f"IC95 [{c['ci95'][0]:+.1f}, {c['ci95'][1]:+.1f}]   "
                      f"{'esclude zero' if c['excludes_zero'] else 'compatibile con zero'}")
            print("    (il dispari coincide quasi con DD_max: si riporta segnalando")
            print("     la circolarita'. Il pari e' nuovo ed e' quello che decide.)")

        rec["levels"][f"k{ki}"] = {"two_sides": rows, "split_B5_B1": sp,
                                   "mock_only_fit": mf, "per_realisation": sl,
                                   "contrasts": ct}
    if a.out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True, default=float) + "\n")
        print(f"\n[scritto] {a.out}")
    return 0


def cmd_cross(a):
    """Correlazione fra emisferi sulle realizzazioni appaiate."""
    print("=" * 88)
    print("CORRELAZIONE FRA EMISFERI — quanto vale l'accordo NGC/SGC")
    print("=" * 88)
    print("  I due emisferi condividono le stesse 200 realizzazioni, la stessa")
    print("  HOD, lo stesso fiduciale e la stessa pipeline. Cio' che NON")
    print("  condividono — maschera, random, n(z), cella, sigma_px, regione di")
    print("  cielo — e' quello che l'accordo effettivamente testa.\n")
    ctx = {}
    for reg in ("NGC", "SGC"):
        aa = argparse.Namespace(**vars(a)); aa.region = reg
        ctx[reg] = collect(aa, reg)
    for ki in (1, 0):
        mkey = f"N_H1_k{ki}"
        dkey = "N_H1" if ki == 1 else "N_H1_k0"
        out = []
        for p in ("B1", "B5", "B6", "C1", "C4"):
            try:
                idx = sorted(
                    i for i in (set(ctx["NGC"][1][p]) & set(ctx["SGC"][1][p])
                                & set(ctx["NGC"][1]["FID"]) & set(ctx["SGC"][1]["FID"]))
                    if all(mkey in ctx[rg][1][q][i]
                           for rg in ("NGC", "SGC") for q in (p, "FID")))
            except KeyError:
                continue
            if len(idx) < 20:
                continue
            v = {}
            for reg in ("NGC", "SGC"):
                D, M = ctx[reg]
                v[reg] = np.array(
                    [(M[p][i][mkey] - M["FID"][i][mkey])
                     - (float(D[p][dkey]) - float(D["FID"][dkey])) for i in idx],
                    float)
            r = float(np.corrcoef(v["NGC"], v["SGC"])[0, 1])
            out.append((p, r, len(idx)))
        if out:
            rs = [o[1] for o in out]
            neff = 2.0 / (1.0 + float(np.mean(rs)))
            print(f"  k={ki}:  " + "   ".join(f"{p} r={r:+.3f}" for p, r, _ in out))
            print(f"        r medio {np.mean(rs):+.3f}  ->  misure effettivamente "
                  f"indipendenti ~ {neff:.2f} su 2")
    return 0


def cmd_selftest(a):
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    rng = np.random.default_rng(831)
    n = 200
    pts = ["B1", "B2", "FID", "B4", "B5"]
    base = rng.normal(35000, 260, n)

    # Caso 1: lato mock INERTE, lato dati che risponde.
    Mi = {p: {i: {"N_H1_k1": base[i] + rng.normal(0, 30)} for i in range(n)}
          for p in pts}
    Di = {p: {"N_H1": 28000 - 2000.0 * (LINE_B[p] - 1.0)} for p in pts}
    sp = split_delta(Di, Mi, 1, "B5", "B1")
    expect("1. lato mock inerte -> rapporto mock/dati vicino a zero",
           abs(sp["ratio_mock_over_data"]) < 0.15,
           f"(rapporto {sp['ratio_mock_over_data']:+.3f})")
    expect("2. e il lato dati e' esatto, senza barra d'errore",
           "delta_data" in sp and "delta_data_sem" not in sp)

    # Caso 2: entrambi i lati rispondono, quasi cancellandosi.
    Mb = {p: {i: {"N_H1_k1": base[i] - 1900.0 * (LINE_B[p] - 1.0)
                  + rng.normal(0, 30)} for i in range(n)} for p in pts}
    sp2 = split_delta(Di, Mb, 1, "B5", "B1")
    expect("3. entrambi i lati -> rapporto vicino a uno, DD piccolo",
           abs(sp2["ratio_mock_over_data"] - 1.0) < 0.2 and abs(sp2["DD"]) < 30,
           f"(rapporto {sp2['ratio_mock_over_data']:+.3f}, DD {sp2['DD']:+.1f})")
    expect("4. e i due casi danno lo STESSO DD_max a meno del segno: "
           "la differenza non li distingue",
           abs(abs(sp["DD"]) - abs(sp2["DD"] - sp["DD"])) >= 0,
           "(e' il punto del referee: D nasconde quale dei due si muove)")

    # rango empirico
    Mr = {"FID": {i: {"N_H1_k1": 35000 + rng.normal(0, 260)} for i in range(n)}}
    Dr = {"FID": {"N_H1": 28256.0}}
    rows = two_sides(Dr, Mr, 1)
    expect("5. il rango e' empirico su n+1 e DESI sta sotto tutti",
           rows[0]["rank"] == f"1/{n+1}", f"({rows[0]['rank']})")
    expect("6. e il deficit frazionario e' (mock - desi)/mock",
           abs(rows[0]["deficit_frac"]
               - (rows[0]["mock_mean"] - 28256.0) / rows[0]["mock_mean"]) < 1e-12)

    # fit sul solo lato mock: modello vero iniettato
    Mq = {p: {i: {"N_H1_k1": base[i] + 3000.0 * (LINE_B[p] - 1.0)
                  + rng.normal(0, 30)} for i in range(n)} for p in pts}
    mf = mock_only_fit(Mq, 1, n_boot=200)
    expect("7. fit sul solo lato mock: modello vero -> adeguato",
           mf["adequate"], f"(chi2 {mf['chi2']:.1f} su {mf['dof']} dof)")
    Mc = {p: {i: {"N_H1_k1": base[i] + 8e6 * (LINE_B[p] - 1.0) ** 3
                  + rng.normal(0, 5)} for i in range(n)} for p in pts}
    mfc = mock_only_fit(Mc, 1, n_boot=200)
    expect("8. e modello cubico -> respinto anche sui soli mock",
           not mfc["adequate"], f"(chi2 {mfc['chi2']:.1f})")

    sl = per_realisation_slopes(Di, Mq, 1)
    expect("9. le pendenze per realizzazione recuperano quella iniettata",
           abs(sl["mean"] - 3000.0) < 5 * sl["sem"], f"(media {sl['mean']:.0f})")
    expect("10. e la loro sd e' molto maggiore della SEM: e' la crepa",
           sl["sd"] > 5 * sl["sem"], f"(sd {sl['sd']:.0f} contro sem {sl['sem']:.0f})")

    ct = contrasts(Di, Mq, 1)
    expect("11. risposta lineare -> contrasto dispari esclude zero, pari no",
           ct["odd"]["excludes_zero"] and not ct["even"]["excludes_zero"],
           f"(dispari {ct['odd']['estimate']:+.0f}, pari {ct['even']['estimate']:+.0f})")
    Me = {p: {i: {"N_H1_k1": base[i] + 2e5 * (LINE_B[p] - 1.0) ** 2
                  + rng.normal(0, 30)} for i in range(n)} for p in pts}
    ct2 = contrasts(Di, Me, 1)
    expect("12. risposta quadratica -> il PARI esclude zero",
           ct2["even"]["excludes_zero"],
           f"(pari {ct2['even']['estimate']:+.0f})")

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for nm in ("run", "cross"):
        q = sub.add_parser(nm)
        q.add_argument("--data", default="results/paper2/fase3.jsonl")
        q.add_argument("--mock", default="results/paper2/fase3_mock.jsonl")
        q.add_argument("--out", default=None)
        if nm == "run":
            q.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
        else:
            q.set_defaults(region=None)
    a = p.parse_args()
    return {"selftest": cmd_selftest, "run": cmd_run, "cross": cmd_cross}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

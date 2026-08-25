#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verifica_outlier_m26.py — chiude la discrepanza sul rank fra i due paper.

LA DOMANDA
----------
M26 riporta rank 1/2000: un mock sta sotto il dato, ed e' identificato come
Om = 0.103, s8 = 0.675, w0 = -1.26. Paper 1 riporta rank 1/2001: nessun
mock sotto il dato, con il minimo dell'ensemble 2970 generatori sopra.
Le due affermazioni non possono essere entrambe vere sullo stesso ensemble.

L'ipotesi da verificare e' che quel mock sia una delle 200 voci sovrascritte
dalla run con HOD diverso: nell'ensemble pulito il suo valore risale sopra
il dato, il rank diventa 1/2001 e la dispersione scende da 445 a 313.

LE TRE COSE DA STABILIRE
------------------------
  A. Nell'ensemble pulito, qual e' il minimo di N_H1 e a quale indice?
     Esiste un mock sotto 28256?
  B. Qual e' l'indice del mock con Om = 0.103, s8 = 0.675, w0 = -1.26?
     Cade sotto 200, cioe' nell'intervallo sovrascritto?
  C. Che valore ha quel mock nell'ensemble pulito?

Se A dice "nessuno sotto il dato", B dice "indice < 200" e C dice "sopra
il dato", l'ipotesi e' confermata e la correzione va nella nota a M26.
Se A trovasse un mock sotto il dato, allora e' paper 1 a dover cambiare.

USO
---
  python src/verifica_outlier_m26.py --root .
  # oppure indicando i file a mano:
  python src/verifica_outlier_m26.py --root . \
      --mock results/paper1/per_mock_NGC_R5.jsonl:base.N_H1 \
      --params data/quijote/latin_hypercube_params.txt

Il file dei parametri e' quello della suite nwLH: sette colonne
(Om, Ob, h, ns, s8, Mnu, w0), una riga per cosmologia, nell'ordine degli
indici. Se hai gia' usato quei parametri per la Tabella 6 (risposta di
N_H1 alla cosmologia), il file e' quello.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

DESI_NGC = 28256.0
# media dell'ensemble NGC alla scala canonica R = 5. E' il valore congelato
# del manoscritto e viene usato come GATE: se il file letto non lo riproduce,
# non e' l'ensemble giusto e lo script si ferma invece di dare un verdetto.
MEAN_ATTESA = 35436.7
TOLL_MEDIA = 0.02          # 2 per cento
TARGET = dict(Om=0.103, s8=0.675, w0=-1.26)
TOL = dict(Om=0.004, s8=0.010, w0=0.02)
RANGE_SOVRASCRITTO = 200


# ------------------------------------------------------------ lettura
def flatten(o, pre=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(flatten(v, f"{pre}{k}."))
    elif not isinstance(o, (list, tuple)):
        out[pre[:-1]] = o
    return out


def load_mocks(spec, root):
    """Restituisce (indici, valori) di N_H1 per mock."""
    fn, key = spec.rsplit(":", 1)
    p = Path(fn)
    if not p.is_absolute():
        p = root / p
    idx, val = [], []
    for i, line in enumerate(p.open(encoding="utf-8", errors="replace")):
        line = line.strip()
        if not line:
            continue
        try:
            row = flatten(json.loads(line))
        except json.JSONDecodeError:
            continue
        v = row.get(key)
        if not isinstance(v, (int, float)):
            continue
        # l'indice: preferisco un campo esplicito, altrimenti la posizione
        k = None
        for cand in ("i", "idx", "index", "mock_id", "imock", "cosmo_id"):
            if isinstance(row.get(cand), (int, float)):
                k = int(row[cand]); break
        if k is None:
            key_s = str(row.get("key", ""))
            digits = "".join(c for c in key_s if c.isdigit())
            k = int(digits) if digits else i
        idx.append(k); val.append(float(v))
    return np.array(idx), np.array(val)


def load_params(path):
    """Legge la tabella dei parametri nwLH. Ritorna array (N, >=7)."""
    p = Path(path)
    if p.suffix.lower() in (".npy",):
        return np.load(p)
    if p.suffix.lower() in (".npz",):
        d = np.load(p)
        for k in d.files:
            a = d[k]
            if a.ndim == 2 and a.shape[1] >= 7:
                return a
        raise SystemExit(f"nessun array (N,>=7) in {p}")
    # testo o csv
    letta = None
    for delim in (None, ",", ";", "\t"):
        try:
            a = np.genfromtxt(p, delimiter=delim, comments="#")
            if a.ndim == 2 and a.shape[1] >= 2:
                letta = a
                if a.shape[1] >= 7:
                    return a
        except Exception:
            continue
    if letta is not None and letta.shape[1] == 5:
        raise SystemExit(f"""
{p}
ha CINQUE colonne (Omega_m, Omega_b, h, n_s, sigma_8): e' il latin
hypercube standard di Quijote, non la suite nwLH.

M26 dichiara di usare nwLH, che ne ha SETTE: i due in piu' sono M_nu e
w_0, e senza w_0 non si puo' identificare l'outlier, che e' caratterizzato
anche da w_0 = -1.26.

Cerca un file con sette colonne. Nell'albero di Quijote la suite sta di
norma in una cartella distinta, con 'nwLH' o 'wCDM' nel nome, accanto a
quella del latin_hypercube che hai gia' trovato. In alternativa: guarda da
quale percorso legge i parametri lo script che ha prodotto la Tabella 6 del
paper (la risposta di N_H1 ai sette parametri) — quella tabella non si puo'
essere prodotta senza il file giusto.""")
    raise SystemExit(f"non riesco a leggere {p} come tabella numerica "
                     f"(letta forma {None if letta is None else letta.shape})")


def n_colonne(p):
    """Numero di colonne, o None se illeggibile."""
    try:
        if p.suffix.lower() == ".npy":
            a = np.load(p)
            return a.shape[1] if a.ndim == 2 else None
        for delim in (None, ",", ";", "\t"):
            a = np.genfromtxt(p, delimiter=delim, comments="#", max_rows=5)
            if a.ndim == 2 and a.shape[1] >= 2:
                return a.shape[1]
    except Exception:
        pass
    return None


def find_params(root):
    """Candidati per i parametri, con i file a 7 colonne in cima."""
    hits = []
    for pat in ("*.txt", "*.dat", "*.csv", "*.npy"):
        for p in root.rglob(pat):
            low = (p.name + " " + str(p.parent)).lower()
            if not any(h in low for h in ("latin", "hypercube", "nwlh",
                                          "wcdm", "cosmo", "param")):
                continue
            try:
                if not 1000 < p.stat().st_size < 20_000_000:
                    continue
            except OSError:
                continue
            c = n_colonne(p)
            if c:
                hits.append((0 if c >= 7 else 1, c, p))
    hits.sort(key=lambda t: (t[0], str(t[2])))
    return hits[:25]


def find_mocks(root):
    """Candidati per l'ensemble NGC, con R5 in cima e le altre scale in fondo."""
    hits = []
    for p in root.rglob("per_mock*NGC*.jsonl"):
        try:
            n = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if n < 1500:
            continue
        low = p.name.lower()
        # la scala canonica e' R = 5: qualsiasi altra R e' un ensemble diverso
        altra_scala = any(f"r{k}" in low for k in (10, 12, 15, 17, 20, 30))
        punteggio = (0 if ("r5" in low and not altra_scala) else
                     2 if altra_scala else 1)
        hits.append((punteggio, p, n))
    hits.sort()
    return [(p, n, punteggio) for punteggio, p, n in hits]


# ------------------------------------------------------------ analisi
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--mock", help="FILE:CHIAVE con N_H1 per mock (NGC)")
    ap.add_argument("--params", help="tabella dei parametri nwLH")
    ap.add_argument("--desi", type=float, default=DESI_NGC)
    a = ap.parse_args()
    root = Path(a.root).resolve()

    # ---------------- A: il minimo dell'ensemble pulito ----------------
    spec = a.mock
    if not spec:
        cands = find_mocks(root)
        if not cands:
            raise SystemExit("nessun per_mock*NGC*.jsonl con >1500 righe: "
                             "indicarlo con --mock FILE:CHIAVE")
        print("candidati trovati:")
        for p, nn, pt in cands:
            eti = {0: "  <- scala canonica R=5",
                   2: "  <- ALTRA SCALA DI SMOOTHING, non confrontabile",
                   1: ""}[pt]
            print(f"    {p}   ({nn} righe){eti}")
        p, n, pt = cands[0]
        if pt != 0:
            raise SystemExit(
                "\nNessun file alla scala canonica R = 5. Tutti i risultati "
                "del paper\nsono quotati a R = 5; confrontare il conteggio "
                "DESI con un ensemble\nprodotto a un'altra scala non "
                "significa nulla. Indica il file giusto\ncon --mock "
                "FILE:CHIAVE.")
        spec = f"{p}:base.N_H1"
        print(f"\n(uso {p.name}, {n} righe, campo base.N_H1)")
    idx, val = load_mocks(spec, root)
    if val.size < 100:
        raise SystemExit(f"solo {val.size} valori letti: campo sbagliato?")

    scarto = abs(val.mean() - MEAN_ATTESA) / MEAN_ATTESA
    if scarto > TOLL_MEDIA:
        raise SystemExit(f"""
GATE FALLITO, mi fermo qui.
  media letta   : {val.mean():.1f}
  media attesa  : {MEAN_ATTESA:.1f}   (ensemble NGC congelato, R = 5)
  scarto        : {scarto*100:.1f} per cento

Il file non contiene l'ensemble su cui poggia il paper. Le cause tipiche
sono due: un'altra scala di smoothing (le medie a R = 10 stanno intorno a
15000, non a 35000), oppure un campo diverso da base.N_H1.
Nessun verdetto sul rank e' possibile da qui: un confronto fra il conteggio
DESI a R = 5 e un ensemble prodotto altrove e' privo di significato.

Indica il file giusto con:
    --mock results/paper1/per_mock_NGC_R5.jsonl:base.N_H1""")

    o = np.argsort(val)
    print("\n" + "=" * 68)
    print("A. L'ENSEMBLE PULITO")
    print("=" * 68)
    print(f"  gate sulla media: superato ({val.mean():.1f} contro "
          f"{MEAN_ATTESA:.1f} atteso)")
    print(f"  n mock          : {val.size}")
    print(f"  media +/- sd    : {val.mean():.1f} +/- {val.std(ddof=1):.1f}"
          f"      (il paper dichiara 35436.7 +/- 313.0)")
    print(f"  DESI            : {a.desi:.0f}")
    print(f"  minimo          : {val[o[0]]:.1f}  a indice {idx[o[0]]}")
    print(f"  margine sopra DESI: {val[o[0]] - a.desi:+.1f}"
          f"      (il paper dichiara +2970)")
    sotto = int((val < a.desi).sum())
    print(f"  mock sotto DESI : {sotto}")
    print("\n  cinque piu' bassi:")
    for j in o[:5]:
        print(f"      indice {idx[j]:5d}   N_H1 = {val[j]:9.1f}"
              f"   {'SOTTO IL DATO' if val[j] < a.desi else ''}")

    if sotto == 0:
        print(f"\n  --> rank empirico 1/{val.size+1}: paper 1 e' coerente con "
              f"il proprio ensemble.")
    else:
        print(f"\n  --> rank empirico {sotto+1}/{val.size+1}: paper 1 va "
              f"corretto, non M26.")

    # ---------------- B e C: l'outlier di M26 ----------------
    print("\n" + "=" * 68)
    print("B. L'OUTLIER DI M26 (Om=0.103, s8=0.675, w0=-1.26)")
    print("=" * 68)
    ppath = a.params
    if not ppath:
        cands = find_params(root)
        if cands:
            print("  file di parametri trovati:")
            for pri, c, p in cands:
                eti = "  <- SETTE colonne, e' nwLH" if c >= 7 else \
                      f"  <- {c} colonne, non nwLH"
                print(f"    {p}{eti}")
            if cands[0][0] != 0:
                print("""
  Nessun file a sette colonne. Senza w_0 l'outlier non e' identificabile:
  la sua firma include w_0 = -1.26. Vedi il messaggio dettagliato piu' sotto.""")
        if not cands:
            print("""  Tabella dei parametri non trovata. Indicala con --params.
  E' il file della suite nwLH con sette colonne per cosmologia
  (Om, Ob, h, ns, s8, Mnu, w0). Se hai prodotto la Tabella 6 del paper
  (risposta di N_H1 ai sette parametri) quel file esiste: cerca da dove
  lo script della Tabella 6 legge i parametri.""")
            return
        ppath = cands[0][2]
        print(f"\n  (uso {ppath})")
    P = load_params(ppath)
    print(f"  tabella: {P.shape[0]} righe x {P.shape[1]} colonne")

    # colonne nwLH: Om, Ob, h, ns, s8, Mnu, w0
    cOm, cs8, cw0 = 0, 4, 6
    sel = (np.abs(P[:, cOm] - TARGET["Om"]) < TOL["Om"]) & \
          (np.abs(P[:, cs8] - TARGET["s8"]) < TOL["s8"]) & \
          (np.abs(P[:, cw0] - TARGET["w0"]) < TOL["w0"])
    match = np.where(sel)[0]

    if match.size == 0:
        print("\n  Nessuna riga corrisponde. Possibili cause: ordine delle"
              "\n  colonne diverso, oppure tolleranze troppo strette."
              "\n  Le cinque righe con Om piu' basso:")
        for k in np.argsort(P[:, cOm])[:5]:
            print(f"      indice {k:5d}  Om={P[k,cOm]:.4f}  s8={P[k,cs8]:.4f}"
                  f"  w0={P[k,cw0]:.4f}")
        return

    print(f"\n  corrispondenze: {match.size}")
    for k in match:
        print(f"      INDICE {k}   Om={P[k,cOm]:.4f}  s8={P[k,cs8]:.4f}"
              f"  w0={P[k,cw0]:.4f}")
        dentro = k < RANGE_SOVRASCRITTO
        print(f"        indice < {RANGE_SOVRASCRITTO}? "
              f"{'SI, nell intervallo sovrascritto' if dentro else 'NO'}")
        m = idx == k
        if m.any():
            v = float(val[m][0])
            print(f"        N_H1 nell ensemble pulito: {v:.1f}"
                  f"   ({'sotto' if v < a.desi else 'sopra'} il dato,"
                  f" {v - a.desi:+.1f})")
        else:
            print("        indice non presente nel file per-mock letto")

    # ---------------- il verdetto, e cosa scrivere ----------------
    k = int(match[0])
    dentro = k < RANGE_SOVRASCRITTO
    m = idx == k
    sopra = bool(m.any() and val[m][0] > a.desi)

    print("\n" + "=" * 68)
    print("VERDETTO")
    print("=" * 68)
    if sotto == 0 and dentro and sopra:
        print(f"""IPOTESI CONFERMATA.
Il mock e' l'indice {k}, dentro l'intervallo 0-199 sovrascritto, e
nell'ensemble pulito sta sopra il dato. Il rank 1/2000 di M26 e' un
effetto della contaminazione; il valore corretto e' 1/2001.

Da scrivere nel punto 5 della nota a M26, al posto del segnaposto:

  \\emph{{Verified.}} The cosmology in question is index {k} of the nwLH
  suite, which falls inside the overwritten range 0--199; in the clean
  ensemble its generator count is {float(val[m][0]):.0f}, above the observed
  {a.desi:.0f} rather than below it. The hypothesis is confirmed: the
  rank of MN-26-2100-P should read $1/2001$ with
  $p\\le5.0\\times10^{{-4}}$, and the sentence identifying an extreme
  low-$\\Omega_m$ cosmology below the data should be removed.

Nel paper 1 non cambia nulla: abstract, Sez. 2.5 e conclusione (i)
restano come sono.""")
    elif sotto == 0 and not dentro:
        print(f"""IPOTESI NON CONFERMATA, MA PAPER 1 REGGE.
Il mock e' l'indice {k}, FUORI dall'intervallo sovrascritto, eppure
nell'ensemble pulito nessun mock sta sotto il dato. La differenza fra i
due paper non e' spiegata dalla contaminazione: va cercata altrove
(HOD della run, taglio in massa degli aloni, versione della maschera).
NON spedire la nota finche' non e' chiarito, e riportami questo output.""")
    elif sotto > 0:
        print(f"""E' PAPER 1 A DOVER CAMBIARE.
Nell'ensemble pulito {sotto} mock stanno sotto il dato: il rank e'
{sotto+1}/{val.size+1}, non 1/2001. Vanno corretti abstract, Sez. 2.5
(rank e margine sopra il minimo) e conclusione (i). Il punto 5 della
nota a M26 va tolto: su questo M26 aveva ragione.
Riportami questo output e li sistemo.""")
    else:
        print("""CASO MISTO. Riportami l'output completo: la combinazione
non rientra fra quelle previste e va guardata a mano.""")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_fase0_close.py — chiude le voci eseguibili della Fase 0

Cinque sottocomandi, indipendenti fra loro.

  q4       0.5 Q4 — dove vive sigma_px: costante di G1 impostabile, o ricalcolo
           interno di data_side?  Da questo dipende dove va l'override del 2.2.

  label    0.9 — etichetta v1 sui record della Componente D.  Non modifica i
           record esistenti: ne accoda di nuovi con `"ensemble": "v1"` e un
           campo `supersedes` che punta all'originale.

  erosion  0.11 — cancello contro `paper1_mask_erosion.py`.  Se l'elemento
           strutturante differisce, i livelli k di 1.2b non sono confrontabili
           con quelli del Paper 1.

  amend    0.12 — emenda il reference set SENZA TOCCARLO.

           Correzione rispetto alla formulazione del 25 ago: annotare dentro
           `paper2_v1_reference.json` ne cambierebbe `_self_sha256`, che e' la
           costante di cancello di meta' toolchain, e cambierebbe il digest del
           tier `records`.  Emendare rompendo il gate e' esattamente cio' che
           l'immutabilita' doveva impedire.
           Gli emendamenti vivono quindi in un file SORELLA, append-only:
           `src/paper2_v1_amendments.jsonl`.  Il reference resta byte-identico;
           chi legge sovrappone gli emendamenti.

  inputs   0.13 — sha256 dei due ingressi della Componente D che stanno fuori
           dal freeze, registrati nello stesso file di emendamenti.

Uso:
    python src\\paper2_fase0_close.py q4
    python src\\paper2_fase0_close.py erosion --region NGC
    python src\\paper2_fase0_close.py label --dry-run
    python src\\paper2_fase0_close.py amend --apply
    python src\\paper2_fase0_close.py inputs --apply
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import sys
import time

import numpy as np

REFERENCE = "src/paper2_v1_reference.json"
AMENDMENTS = "src/paper2_v1_amendments.jsonl"
COMPD_RECORDS = ["results/paper2/compD_NGC.jsonl", "results/paper2/compD_SGC.jsonl",
                 "results/paper2/compD_nonlinear_NGC.jsonl",
                 "results/paper2/compD_nonlinear_SGC.jsonl"]
COMPD_INPUTS = [
    ("latin_hypercube_nwLH_params",
     "data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt",
     "join dei parametri per D2; sta sotto data/raw, fuori da --roots results"),
    ("phase7_pk_nwlh_cache",
     "results/phase7_pk_nwlh_cache.npz",
     "P(k) per D6; estensione .npz, fuori dalle estensioni del tier records"),
]

AMENDMENT_3 = {
    "key": "practical_rule",
    "supersedes": "amendment del 26 ago che identificava d_med con la mediana della distanza "
                  "al primo vicino fra le galassie",
    "old": "sigma_px <~ d_med, d_med = median 1-NN separation in grid units",
    "new": ("sigma_px <~ d_med/9, d_med = median Euclidean distance to the mask boundary "
            "in grid units (scipy.ndimage.distance_transform_edt)"),
    "reason": ("RITRATTAZIONE. L'identificazione col primo vicino era una coincidenza numerica "
               "(0.33126 contro 0.333, 0.5%). La definizione vera e' in chiaro in "
               "paper1_mask_erosion.py:19 ('il footprint NGC ha profondita' mediana di soli 3 "
               "voxel') e :78 (import distance_transform_edt): misurata su NGC da' 3.000 voxel "
               "esatti, quindi 3/9 = 0.33333 contro il congelato 0.333, scarto +0.0003. "
               "Il '/9' e' letterale e va mantenuto."),
    "evidence": "results/paper2/dmed_NGC.jsonl, results/paper2/dmed_SGC.jsonl",
}
AMENDMENT_4 = {
    "key": "practical_limit_SGC",
    "supersedes": "amendment del 26 ago con valore 0.3798",
    "old": 0.37980,
    "new": 0.31422,
    "reason": ("RITRATTAZIONE. Il valore 0.3798 discendeva dall'identificazione sbagliata. "
               "Con la definizione corretta: d_med(SGC) = 2.828 voxel = 2*sqrt(2) esatto, "
               "quindi limite 0.31422. Il sigma_px fiduciale SGC e' 0.33606, cioe' -6.9% "
               "OLTRE il limite: il limite pratico e' violato in tutti gli 11 punti della "
               "griglia AP, fiduciale compreso. Non e' un criterio di esclusione utilizzabile "
               "in SGC (escluderebbe un risultato pubblicato); e' un caveat da dichiarare, e "
               "il rimedio operativo e' l'erosione, che il Paper 1 ha gia' eseguito e superato."),
    "evidence": "results/paper2/dmed_SGC.jsonl, results/paper2/item12b_SGC.jsonl",
}
AMENDMENT_1 = {
    "key": "practical_rule",
    "old": "sigma_px <~ d_med/9",
    "new": "sigma_px <~ d_med, d_med = median 1-NN separation in grid units",
    "reason": ("item 1.2b: la formula '/9' non e' riproducibile da nessuna quantita' misurata "
               "(spaziatura media 1.12 voxel, 50-esimo vicino 2.19, mentre d_med/9=0.333 "
               "implicherebbe 3.00). Il valore 0.333 e' invece riprodotto allo 0.5% dalla "
               "mediana della distanza al primo vicino in unita' di griglia: NGC 0.33126."),
    "evidence": "results/paper2/item12b_NGC.jsonl, results/paper2/item12b_SGC.jsonl",
}
AMENDMENT_2 = {
    "key": "practical_limit_SGC",
    "old": None,
    "new": 0.37980,
    "reason": ("il reference set congela solo `practical_limit_NGC`; il nome stesso dichiara che "
               "il limite e' per regione. Il valore SGC mancava e la tabella di triage aveva "
               "trasferito quello NGC senza autorizzazione."),
    "evidence": "results/paper2/item12b_SGC.jsonl",
}


# --------------------------------------------------------------------------

def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def append_atomic(path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------
# q4
# --------------------------------------------------------------------------

def cmd_q4(a):
    if a.src not in sys.path:
        sys.path.insert(0, a.src)
    G = __import__(a.geom_module)
    M = getattr(G, "M", None) or __import__(a.const_module)
    print("=" * 72)
    print("0.5 Q4 — dove vive sigma_px")
    print("=" * 72)

    print("\n[1] costanti di modulo che somigliano a sigma_px o a R")
    found = []
    for name in dir(M):
        if name.startswith("__"):
            continue
        if not re.search(r"sigma|sig_?px|R_SMOOTH|SMOOTH|KERNEL", name, re.I):
            continue
        v = getattr(M, name)
        if isinstance(v, (int, float, np.floating)):
            print("    %-22s = %r" % (name, v))
            found.append(name)
    if not found:
        print("    nessuna")

    print("\n[2] set_geometry accetta sigma_px?")
    setg = getattr(M, "set_geometry", None) or getattr(G, "set_geometry", None)
    if setg is None:
        print("    set_geometry non trovata")
    else:
        pars = list(inspect.signature(setg).parameters)
        print("    parametri: %s" % ", ".join(pars))
        hit = [p for p in pars if re.search(r"sigma|smooth|R\b", p, re.I)]
        print("    -> %s" % ("IMPOSTABILE via %s" % ", ".join(hit) if hit
                             else "NON impostabile: sigma_px non e' fra i parametri"))

    print("\n[3] come data_side lo calcola")
    src_file = getattr(G, "__file__", None)
    if src_file and os.path.exists(src_file):
        with open(src_file, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        for i, line in enumerate(lines, 1):
            if re.search(r"sigma_?px", line):
                print("    %s:%d" % (os.path.basename(src_file), i))
                print("        %s" % line.strip()[:110])

    print("\n[4] verdetto")
    print("    Se sigma_px NON e' impostabile e data_side lo ricalcola da R/cell,")
    print("    l'override del cancello 2.2 va fatto A VALLE, sul kernel di lisciatura,")
    print("    e va scritto nel manoscritto: cambia cosa significa 'sigma_px fisso in")
    print("    unita' di griglia' per chi rifa' il lavoro.")
    print("    Se invece e' impostabile, l'override e' una riga in set_geometry.")


# --------------------------------------------------------------------------
# label
# --------------------------------------------------------------------------

def cmd_label(a):
    print("=" * 72)
    print("0.9 — etichetta v1 sui record della Componente D")
    print("=" * 72)
    total = 0
    for path in COMPD_RECORDS:
        if not os.path.exists(path):
            print("  %-44s assente" % path)
            continue
        recs = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
        todo = [r for r in recs if "ensemble" not in r]
        print("  %-44s %3d record, %3d senza etichetta" % (path, len(recs), len(todo)))
        for r in todo:
            new = dict(r)
            new["ensemble"] = "v1"
            new["supersedes"] = {"schema": r.get("schema"), "utc": r.get("utc")}
            new["amended_utc"] = now()
            new["amend_reason"] = ("item 0.9: i numeri della Componente D leggono "
                                   "per_mock_*_R5.jsonl -> base.N_H1, che e' ensemble v1. "
                                   "L'etichetta mancava.")
            if not a.dry_run:
                append_atomic(path, new)
            total += 1
    print("\n  %d record %s" % (total, "da accodare (--dry-run)" if a.dry_run else "accodati"))
    print("\n  DICHIARAZIONE DA REGISTRARE, e va fatta ADESSO:")
    print("    D2 (correlazioni parziali) e D6 (non linearita' + P(k)) verranno")
    print("    RIPETUTE su ensemble v2 quando esistera', con le stesse predizioni")
    print("    P1-P5 e Q1-Q5 gia' depositate.  Deciderlo dopo aver visto i")
    print("    risultati v2 non sarebbe la stessa cosa.")
    if not a.dry_run:
        append_atomic(AMENDMENTS, {
            "type": "declaration", "item": "0.9", "utc": now(),
            "text": ("D2 e D6 saranno ripetute su ensemble v2 con le predizioni P1-P5 e "
                     "Q1-Q5 invariate; i risultati v1 restano nel record con etichetta "
                     "ensemble=v1."),
        })
        print("\n  dichiarazione registrata in %s" % AMENDMENTS)


# --------------------------------------------------------------------------
# erosion
# --------------------------------------------------------------------------

def erode_internal(mask, k):
    m = mask.copy()
    for _ in range(k):
        e = m.copy()
        for ax in range(3):
            for sh in (1, -1):
                e &= np.roll(m, sh, axis=ax)
        for ax in range(3):
            for pos in (0, -1):
                idx = [slice(None)] * 3
                idx[ax] = pos
                e[tuple(idx)] = False
        m = e
    return m


def cmd_erosion(a):
    print("=" * 72)
    print("0.11 — cancello contro paper1_mask_erosion.py")
    print("=" * 72)
    if a.src not in sys.path:
        sys.path.insert(0, a.src)

    print("\n[1] anatomia di paper1_mask_erosion.py")
    path = os.path.join(a.src, "paper1_mask_erosion.py")
    if not os.path.exists(path):
        print("    non trovato in %s" % a.src)
        return
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    keys = ("def ", "roll", "binary_erosion", "structure", "generate_binary",
            "neighbour", "vicin", "w_bar", "w <", "erod")
    shown = set()
    for i, line in enumerate(lines):
        if any(k in line for k in keys):
            for j in range(max(0, i - 1), min(len(lines), i + 2)):
                if j not in shown:
                    print("    %4d: %s" % (j + 1, lines[j][:110]))
                    shown.add(j)
            if len(shown) > 60:
                print("    ... (troncato)")
                break

    print("\n[2] funzioni importabili")
    try:
        P1 = __import__("paper1_mask_erosion")
    except Exception as exc:
        print("    import fallito (%s: %s): confronto solo sul sorgente." %
              (type(exc).__name__, exc))
        P1 = None
    cand = []
    if P1 is not None:
        for name in dir(P1):
            obj = getattr(P1, name)
            if callable(obj) and re.search(r"erod|erosion|restrict|mask", name, re.I):
                try:
                    sig = str(inspect.signature(obj))
                except (TypeError, ValueError):
                    sig = "(?)"
                print("    %s%s" % (name, sig))
                cand.append((name, obj))
        if not cand:
            print("    nessuna funzione di erosione esportata")

    print("\n[3] confronto numerico sulla maschera fiduciale")
    G = __import__(a.geom_module)
    ds = G.data_side(a.region)
    mask = None
    for v in (ds.values() if isinstance(ds, dict) else []):
        arr = v if isinstance(v, np.ndarray) else None
        if arr is not None and arr.dtype == bool and arr.ndim == 3:
            mask = arr
        elif isinstance(v, (list, tuple)):
            for x in v:
                if isinstance(x, np.ndarray) and x.dtype == bool and x.ndim == 3:
                    mask = x
    if mask is None:
        print("    maschera non trovata")
        return
    print("    k=0: %d voxel" % mask.sum())
    mine = {k: int(erode_internal(mask, k).sum()) for k in (1, 2, 3)}
    for k in (1, 2, 3):
        print("    k=%d: interna = %d" % (k, mine[k]))
    ok = False
    for name, fn in cand:
        for call in (lambda: fn(mask, 1), lambda: fn(mask, k=1), lambda: fn(mask=mask, k=1)):
            try:
                out = np.asarray(call(), bool)
            except Exception:
                continue
            if out.shape == mask.shape:
                n = int(out.sum())
                same = (n == mine[1])
                print("    %-20s k=1 -> %d voxel   %s" % (name, n, "COINCIDE" if same else "DIVERGE"))
                ok = ok or same
                break
    print("\n[4] verdetto")
    if ok:
        print("    L'erosione interna coincide con quella del Paper 1: i w̄ di 1.2b sono")
        print("    confrontabili, 0.11 e' chiusa.")
    else:
        print("    NON confermato. Finche' non lo e', i w̄ di 1.2b restano una misura")
        print("    interna coerente (la scalinata e la scelta k=1 reggono comunque),")
        print("    ma NON vanno confrontati con i numeri del Paper 1.")


# --------------------------------------------------------------------------
# amend / inputs
# --------------------------------------------------------------------------

def cmd_amend(a):
    print("=" * 72)
    print("0.12 — emendamenti al reference set, senza toccarlo")
    print("=" * 72)
    if not os.path.exists(REFERENCE):
        print("  reference non trovato: %s" % REFERENCE)
        return
    digest = sha256_file(REFERENCE)
    print("\n  reference: %s" % REFERENCE)
    print("  sha256   : %s" % digest)
    print("  -> NON viene modificato. Gli emendamenti vanno in %s" % AMENDMENTS)

    with open(REFERENCE, encoding="utf-8") as fh:
        ref = json.load(fh)

    def find(key, obj=ref, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = "%s.%s" % (path, k) if path else k
                if k == key:
                    return p, v
                r = find(key, v, p)
                if r:
                    return r
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                r = find(key, v, "%s[%d]" % (path, i))
                if r:
                    return r
        return None

    seen = set()
    if os.path.exists(AMENDMENTS):
        with open(AMENDMENTS, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("type") == "amendment":
                    seen.add((r.get("key"), json.dumps(r.get("new_value"), sort_keys=True)))

    for am in (AMENDMENT_1, AMENDMENT_2, AMENDMENT_3, AMENDMENT_4):
        sig = (am["key"], json.dumps(am["new"], sort_keys=True))
        if sig in seen:
            print("\n  [skip] gia' registrato: %s -> %r" % (am["key"], am["new"]))
            continue
        seen.add(sig)
        hit = find(am["key"])
        print("\n  chiave %-22s %s" % (am["key"], ("trovata in %s = %r" % hit) if hit
                                       else "ASSENTE nel reference (emendamento additivo)"))
        print("    da : %r" % (hit[1] if hit else None))
        print("    a  : %r" % am["new"])
        print("    motivo: %s" % am["reason"])
        if a.apply:
            append_atomic(AMENDMENTS, {
                "type": "amendment",
                "item": "1.2b" if "supersedes" not in am else "1.2b-rettifica",
                "supersedes": am.get("supersedes"), "utc": now(),
                "reference_file": REFERENCE, "reference_sha256": digest,
                "json_path": hit[0] if hit else None,
                "key": am["key"], "old_value": hit[1] if hit else None,
                "new_value": am["new"], "reason": am["reason"],
                "evidence": am["evidence"],
            })
    if a.apply:
        print("\n  emendamenti registrati in %s" % AMENDMENTS)
        print("  Il reference resta byte-identico: sha256 invariato, tier `records` intatto.")
    else:
        print("\n  (nulla scritto: rilanciare con --apply)")


def cmd_inputs(a):
    print("=" * 72)
    print("0.13 — sha256 degli ingressi della Componente D")
    print("=" * 72)
    for name, path, why in COMPD_INPUTS:
        if not os.path.exists(path):
            print("\n  %-28s ASSENTE: %s" % (name, path))
            continue
        d = sha256_file(path)
        sz = os.path.getsize(path)
        print("\n  %-28s %s" % (name, path))
        print("    dimensione %d B" % sz)
        print("    sha256     %s" % d)
        print("    perche'    %s" % why)
        if a.apply:
            append_atomic(AMENDMENTS, {
                "type": "input_hash", "item": "0.13", "utc": now(),
                "name": name, "path": path, "bytes": sz, "sha256": d, "reason": why,
            })
    if a.apply:
        print("\n  registrati in %s" % AMENDMENTS)
    else:
        print("\n  (nulla scritto: rilanciare con --apply)")


# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", default="src")
    p.add_argument("--geom-module", default="paper2_data_geometry")
    p.add_argument("--const-module", default="phase8_cutsky_mocks")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("q4")
    lp = sub.add_parser("label"); lp.add_argument("--dry-run", action="store_true")
    ep = sub.add_parser("erosion"); ep.add_argument("--region", default="NGC")
    ap = sub.add_parser("amend"); ap.add_argument("--apply", action="store_true")
    ip = sub.add_parser("inputs"); ip.add_argument("--apply", action="store_true")
    a = p.parse_args()
    {"q4": cmd_q4, "label": cmd_label, "erosion": cmd_erosion,
     "amend": cmd_amend, "inputs": cmd_inputs}[a.cmd](a)


if __name__ == "__main__":
    main()

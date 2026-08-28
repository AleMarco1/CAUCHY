#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 - Cancello 2.1: chiusura M26 / Paper 1.

Regola di decisione DICHIARATA PRIMA DELL'ESECUZIONE (checklist rev. 3.3 §2.1,
rivista nella sessione del 27 ago 2026):

  2.1-E  ensemble   n = 2000 esatti per regione; media e sd con ddof=1 contro i
                    valori a precisione piena dei record del Paper 1,
                    tolleranza RELATIVA 1e-12.
                    Riferimento operativo = Paper 1 (mock_baseline_mean).
                    M26 (frozen_reference.mock_baseline) e' SUPERSEDED: viene
                    riportato per memoria, non entra nel verdetto.

  2.1-G  geometria  box, cella, sigma_px, n_valid_voxels, mask_threshold contro
                    la tabella congelata, tolleranza RELATIVA 1e-6;
                    inoltre sigma_px_used == sigma_px_canonical (bit-identici).

  2.1-D1 chiusura   N_H1(DESI) == 28256 (NGC) / 15122 (SGC), differenza INTERA
                    ESATTAMENTE ZERO. Nessuna tolleranza relativa.
                    Il messaggio "test di chiusura SUPERATO" di paper1_remap.py
                    NON e' il verdetto: quel ramo stampa SUPERATO anche con
                    sigma_scale != 1.0 e non esce mai con codice != 0.

  2.1-P  provenienza  gli sha256 dei file protetti devono essere byte-identici
                    prima e dopo ogni esecuzione. Un rerun al tag di default
                    riscriverebbe l'ingresso congelato del 2.1-E.

Esiti dichiarati:
  1  E ok, G ok, D1 ok           -> PASSA, si apre il 2.2
  2  E fallito, D1 ok            -> difetto di provenienza dell'ensemble
                                    (famiglia mock 0-199). Stop, audit indici.
  3  D1 != 0 con |delta| <= 5    -> CASO PEGGIORE: deriva di codice alla stessa
                                    scala della predizione 2.2a. Stop, tracciare
                                    al commit prima di aprire il 2.2.
  4  D1 != 0 con |delta| > 5     -> contaminazione di stato globale. Rigirare
                                    dopo data_side fiduciale pulito.
  5  G fallito                   -> non si guarda D1. Rigirare.
  6  P fallito                   -> l'esecuzione ha toccato un file congelato.
                                    Il risultato e' NULLO qualunque sia.

Uso:
    python src\\paper2_gate21.py snapshot
    python src\\paper2_gate21.py ensemble
    python src\\paper2_gate21.py desi --region NGC --tag g21
    python src\\paper2_gate21.py desi --region SGC --tag g21
    python src\\paper2_gate21.py verdict

Nessun glob su results/paper1: solo R = 5 e' affidabile, i percorsi sono
espliciti.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# congelati - valori a precisione piena, estratti dai record del Paper 1
# (paper1_remap_{REGION}_R5.json, schema 3.0, run del 2026-07-23/25)
# --------------------------------------------------------------------------

FIELD = ("base", "N_H1")            # campo ANNIDATO, non "N_H1" al primo livello

FROZEN = {
    "NGC": {
        "per_mock":   "results/paper1/per_mock_NGC_R5.jsonl",
        "remap_json": "results/paper1/paper1_remap_NGC_R5.json",
        "n": 2000,
        "mean": 35436.686,
        "sd": 312.9891651683112,          # ddof = 1
        "desi": 28256,
        "m26_baseline": 35467.15,         # superseded, fuori dal verdetto
        "box_size": 1997.3629167166155,
        "cell": 15.604397786848558,
        "sigma_px": 0.32042249039652254,
        "n_valid_voxels": 307805,
        "mask_threshold": 0.020012933760881424,
        "N_data": 217614,
        "N_rand": 13248857,
    },
    "SGC": {
        "per_mock":   "results/paper1/per_mock_SGC_R5.jsonl",
        "remap_json": "results/paper1/paper1_remap_SGC_R5.json",
        "n": 2000,
        "mean": 18712.9675,
        "sd": 197.7873817207103,          # ddof = 1
        "desi": 15122,
        "m26_baseline": 18693.595,
        "box_size": 1904.4501607158168,
        "cell": 14.878516880592318,
        "sigma_px": 0.3360550006514459,
        "n_valid_voxels": 172225,
        "mask_threshold": 0.008570596575737,
        "N_data": 82429,
        "N_rand": 5432939,
    },
}

# arrotondamenti citati in checklist rev. 3.3, verificati come controllo secondario
QUOTED = {"NGC": (35436.686, 312.989), "SGC": (18712.968, 197.787)}

TOL_ENSEMBLE_REL = 1e-12
TOL_GEOM_REL = 1e-6
DDOF = 1                              # paper2_compD_partialcorr.py:275

# file la cui integrita' deve sopravvivere a ogni esecuzione.
# Percorsi da paper1_remap.py:653-658.
#   Le due maschere sono nodi CONDIVISI: caricate da ~30 script (tutti i
#   paper1_rev_*, sei phase6, phase8, otto phase9, alcuni via rglob senza
#   percorso fisso). Non vanno mai rigenerate sul posto.
#   Le due scale nulle si sovrascrivono da sole: il nome dipende solo da
#   regione e conteggio della cache (paper1_remap.py:449), e la condizione di
#   riuso (455) include Q.size == mask.sum(), quindi una maschera diversa
#   innesca ricalcolo e atomic_save_npy sul bersaglio congelato del Paper 1.
PROTECTED = [
    "results/paper1/per_mock_NGC_R5.jsonl",
    "results/paper1/per_mock_SGC_R5.jsonl",
    "results/paper1/paper1_remap_NGC_R5.json",
    "results/paper1/paper1_remap_SGC_R5.json",
    "src/paper2_v1_reference.json",
    "data/processed/phase6_fields/bgs_ngc_mask_128.npy",
    "data/processed/phase6_fields/bgs_sgc_mask_128.npy",
    "results/paper1/null_ladder_NGC_n2000.npy",
    "results/paper1/null_ladder_NGC_n2000.json",
    "results/paper1/null_ladder_SGC_n2000.npy",
    "results/paper1/null_ladder_SGC_n2000.json",
]

LOG = "results/paper2/gate21.jsonl"
SNAP = "results/paper2/gate21_snapshot.json"


# --------------------------------------------------------------------------
# infrastruttura
# --------------------------------------------------------------------------

def now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def append_jsonl(path, rec):
    """Append-only con fsync sul file e sulla directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    try:
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except (OSError, AttributeError):
        pass          # Windows non consente fsync su directory: non fatale


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def half_up(x, nd):
    """Arrotondamento half-away-from-zero sulla rappresentazione decimale esatta."""
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))


def relerr(got, ref):
    if ref == 0:
        return abs(got)
    return abs(got - ref) / abs(ref)


def line(ok):
    return "PASSA" if ok else "FALLITO"


# --------------------------------------------------------------------------
# 2.1-P  provenienza
# --------------------------------------------------------------------------

def take_snapshot(root):
    out = {}
    missing = []
    for rel in PROTECTED:
        p = root / rel
        if not p.exists():
            missing.append(rel)
            continue
        out[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    return out, missing


def cmd_snapshot(args, root):
    snap, missing = take_snapshot(root)
    if missing:
        print("  [!] file protetti assenti: %s" % ", ".join(missing), file=sys.stderr)
    atomic_write_json(root / SNAP, {"taken": now(), "files": snap})
    print("\n[2.1-P] istantanea di %d file protetti -> %s" % (len(snap), SNAP))
    for rel, v in sorted(snap.items()):
        print("    %-46s %s  %10d B" % (rel, v["sha256"][:16] + "...", v["bytes"]))
    if missing:
        return 4
    return 0


def check_snapshot(root, verbose=True):
    """True se tutti i file protetti sono byte-identici all'istantanea."""
    p = root / SNAP
    if not p.exists():
        raise SystemExit("[FATAL] nessuna istantanea: lanciare prima 'snapshot'.")
    ref = json.loads(p.read_text(encoding="utf-8"))["files"]
    now_, _ = take_snapshot(root)
    bad = []
    for rel, v in ref.items():
        cur = now_.get(rel)
        if cur is None or cur["sha256"] != v["sha256"]:
            bad.append(rel)
    if verbose:
        print("\n[2.1-P] provenienza: %s (%d file)" % (line(not bad), len(ref)))
        for rel in bad:
            print("    ALTERATO: %s" % rel)
    return (not bad), bad


# --------------------------------------------------------------------------
# 2.1-E  ensemble  +  2.1-G  geometria
# --------------------------------------------------------------------------

def read_per_mock(path):
    """Legge base.N_H1 record per record. Nessun glob, nessun campo di primo livello."""
    vals, bad = [], 0
    with open(path, "r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            rec = json.loads(ln)
            node = rec
            for k in FIELD:
                if not isinstance(node, dict) or k not in node:
                    node = None
                    break
                node = node[k]
            if node is None:
                bad += 1
                continue
            vals.append(float(node))
    return np.asarray(vals, dtype=np.float64), bad


def gate_ensemble(root, region):
    f = FROZEN[region]
    p = root / f["per_mock"]
    if not p.exists():
        raise SystemExit("[FATAL] assente: %s" % p)
    val, bad = read_per_mock(p)
    n = len(val)
    m = float(val.mean())
    s = float(val.std(ddof=DDOF))

    ok_n = (n == f["n"]) and (bad == 0)
    e_m, e_s = relerr(m, f["mean"]), relerr(s, f["sd"])
    ok_m = e_m <= TOL_ENSEMBLE_REL
    ok_s = e_s <= TOL_ENSEMBLE_REL
    qm, qs = QUOTED[region]
    # round() e' half-to-even sul binario: su SGC la media cade esattamente sul
    # mezzo ULP (18712.9675) e darebbe ...967 contro il ...968 della checklist.
    ok_q = (half_up(m, 3) == qm) and (half_up(s, 3) == qs)

    print("\n[2.1-E] ensemble v1, %s   (ddof=%d)" % (region, DDOF))
    print("    n      = %6d          atteso %6d            record scartati %d" % (n, f["n"], bad))
    print("    media  = %.10f   atteso %.10f   rel %.3e" % (m, f["mean"], e_m))
    print("    sd     = %.10f   atteso %.10f   rel %.3e" % (s, f["sd"], e_s))
    print("    arrotondamenti di checklist (%.3f / %.3f): %s" % (qm, qs, line(ok_q)))
    print("    M26 superseded = %.3f  (scarto %+.4f = %+.3f sd, fuori dal verdetto)"
          % (f["m26_baseline"], m - f["m26_baseline"], (m - f["m26_baseline"]) / s))
    ok = ok_n and ok_m and ok_s and ok_q
    print("    -> 2.1-E %s" % line(ok))
    return ok, {"n": n, "bad_records": bad, "mean": m, "sd": s,
                "rel_mean": e_m, "rel_sd": e_s, "rounding_ok": ok_q, "pass": ok}


def gate_geometry(root, region):
    f = FROZEN[region]
    p = root / f["remap_json"]
    if not p.exists():
        raise SystemExit("[FATAL] assente: %s" % p)
    d = json.loads(p.read_text(encoding="utf-8"))
    meta = d["meta"]

    checks = [
        ("box_size", meta["box_size"], f["box_size"]),
        ("cell", meta["cell"], f["cell"]),
        ("sigma_px_canonical", meta["sigma_px_canonical"], f["sigma_px"]),
        ("sigma_px_used", meta["sigma_px_used"], f["sigma_px"]),
    ]
    print("\n[2.1-G] geometria fiduciale, %s" % region)
    ok = True
    detail = {}
    for name, got, ref in checks:
        e = relerr(got, ref)
        good = e <= TOL_GEOM_REL
        ok &= good
        detail[name] = {"got": got, "ref": ref, "rel": e, "pass": good}
        print("    %-20s %.17g   atteso %.17g   rel %.2e  %s"
              % (name, got, ref, e, line(good)))

    ident = (meta["sigma_px_used"] == meta["sigma_px_canonical"])
    ok &= ident
    detail["used_eq_canonical"] = ident
    print("    sigma_px_used == canonical (bit): %s   -> sigma_scale era 1.0" % line(ident))

    cell_from_box = meta["box_size"] / meta["ngrid"]
    e_cell = relerr(cell_from_box, meta["cell"])
    ok &= (e_cell <= TOL_GEOM_REL)
    detail["cell_closure"] = e_cell
    print("    coerenza cella = box/ngrid: rel %.2e  %s" % (e_cell, line(e_cell <= TOL_GEOM_REL)))

    ref_desi = d.get("frozen_reference", {}).get("desi_N_H1")
    print("    frozen_reference.desi_N_H1 = %s (M26 e Paper 1 coincidono qui)" % ref_desi)
    print("    -> 2.1-G %s" % line(ok))
    return bool(ok), detail


def cmd_ensemble(args, root):
    ok_p, _ = check_snapshot(root)
    res, allok = {}, True
    for region in ("NGC", "SGC"):
        e_ok, e = gate_ensemble(root, region)
        g_ok, g = gate_geometry(root, region)
        res[region] = {"ensemble": e, "geometry": g}
        allok &= (e_ok and g_ok)
    ok_p2, bad = check_snapshot(root)
    append_jsonl(root / LOG, {"ts": now(), "gate": "2.1-E+G", "regions": res,
                              "provenance_before": ok_p, "provenance_after": ok_p2,
                              "provenance_altered": bad, "pass": bool(allok and ok_p2)})
    print("\n=== 2.1-E + 2.1-G: %s ===" % line(allok and ok_p2))
    return 0 if (allok and ok_p2) else 1


# --------------------------------------------------------------------------
# 2.1-D1  chiusura DESI via --stage selfcheck
# --------------------------------------------------------------------------

RE_NH1 = re.compile(r"N_H1\(DESI\s+(NGC|SGC)\)\s*=\s*([0-9]+)")


def cmd_desi(args, root):
    region = args.region
    f = FROZEN[region]
    if args.tag.strip().upper() == "R5":
        raise SystemExit("[FATAL] tag 'R5' riscriverebbe l'output congelato. Usare un tag distinto.")

    ok_p, _ = check_snapshot(root)
    if not ok_p:
        raise SystemExit("[FATAL] i file protetti sono gia' alterati PRIMA del run. Stop.")

    # --curves_dir: senza, paper1_remap.py scrive curves_DESI_{region}_{tag}.npz in
    # results/paper1, cioe' DENTRO il tier congelato 'diagrams' (radice results/paper1,
    # estensioni .npy/.npz). Non e' una modifica ma un'AGGIUNTA, quindi check_snapshot
    # la manca per costruzione: confronta digest di percorsi noti, non l'insieme.
    # Rilevata il 28 ago 2026 da paper2_freeze_verify.py (direzione disco -> manifest).
    cmd = [sys.executable, str(root / "src" / "paper1_remap.py"),
           "--stage", "selfcheck", "--region", region, "--tag", args.tag,
           "--project_root", str(root),
           "--curves_dir", str(root / "results" / "paper2")]
    print("\n[2.1-D1] %s" % " ".join(cmd))
    pr = subprocess.run(cmd, capture_output=True, text=True)
    out = pr.stdout + pr.stderr
    print(out)

    hits = RE_NH1.findall(out)
    if len(hits) != 1:
        raise SystemExit("[FATAL] N_H1 non estraibile dallo stdout (%d occorrenze)." % len(hits))
    reg_seen, got = hits[0][0], int(hits[0][1])
    if reg_seen != region:
        raise SystemExit("[FATAL] regione stampata (%s) != richiesta (%s)." % (reg_seen, region))

    delta = got - f["desi"]
    ok = (delta == 0)
    ok_p2, bad = check_snapshot(root)

    print("[2.1-D1] N_H1 = %d   congelato = %d   delta = %+d   -> %s"
          % (got, f["desi"], delta, line(ok)))
    if not ok:
        branch = 3 if abs(delta) <= 5 else 4
        print("    ESITO %d: %s" % (branch,
              "deriva alla scala della predizione 2.2a. Tracciare al commit."
              if branch == 3 else
              "contaminazione di stato globale. Rigirare dopo data_side fiduciale."))
    if pr.returncode != 0:
        print("    [nota] paper1_remap.py e' uscito con codice %d" % pr.returncode)
    print("    [nota] il messaggio 'test di chiusura SUPERATO' del sorgente NON e' il verdetto:")
    print("           quel ramo stampa SUPERATO anche con sigma_scale != 1.0 e non esce mai != 0.")

    append_jsonl(root / LOG, {"ts": now(), "gate": "2.1-D1", "region": region,
                              "tag": args.tag, "N_H1": got, "frozen": f["desi"],
                              "delta": delta, "returncode": pr.returncode,
                              "provenance_before": ok_p, "provenance_after": ok_p2,
                              "provenance_altered": bad, "pass": bool(ok and ok_p2)})
    return 0 if (ok and ok_p2) else 1


# --------------------------------------------------------------------------
# verdetto
# --------------------------------------------------------------------------

def cmd_verdict(args, root):
    p = root / LOG
    if not p.exists():
        raise SystemExit("[FATAL] nessun registro: %s" % p)
    seen = {}
    with open(p, "r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                r = json.loads(ln)
                key = (r["gate"], r.get("region", "-"))
                seen[key] = r          # l'ultimo vince, lo storico resta nel file
    need = [("2.1-E+G", "-"), ("2.1-D1", "NGC"), ("2.1-D1", "SGC")]
    print("\n=== VERDETTO CANCELLO 2.1 ===")
    allok = True
    for key in need:
        r = seen.get(key)
        if r is None:
            print("  %-14s %-4s  NON ESEGUITO" % key)
            allok = False
            continue
        print("  %-14s %-4s  %s   (%s)" % (key[0], key[1], line(r["pass"]), r["ts"]))
        allok &= bool(r["pass"])
    print("\n  2.1 %s%s" % (line(allok),
          " - si apre il 2.2" if allok else " - il 2.2 NON va lanciato"))
    return 0 if allok else 1


def main():
    ap = argparse.ArgumentParser(description="Cancello 2.1 - chiusura M26/Paper 1")
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("snapshot")
    sub.add_parser("ensemble")
    d = sub.add_parser("desi")
    d.add_argument("--region", choices=["NGC", "SGC"], required=True)
    d.add_argument("--tag", default="g21")
    sub.add_parser("verdict")
    args = ap.parse_args()
    root = Path(args.project_root)
    fn = {"snapshot": cmd_snapshot, "ensemble": cmd_ensemble,
          "desi": cmd_desi, "verdict": cmd_verdict}[args.cmd]
    sys.exit(fn(args, root))


if __name__ == "__main__":
    main()

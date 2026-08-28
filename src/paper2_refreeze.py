#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_refreeze.py — ricongelamento guardato dei cinque tier dell'ensemble v1.

Perche' serve uno strumento invece di cinque comandi a mano
-----------------------------------------------------------
Il ricongelamento deve cambiare TRE cose nelle intestazioni — `git.dirty` da True a
False, `reference_sha256` da 865aa2ef a 332939bc, e la dichiarazione della directory
esclusa — e NON deve cambiare i cinque `aggregate_sha256`. Quell'invarianza e' il
cancello: se un aggregate si muove, il congelamento dipendeva da git o dai metadati, e
allora non era un congelamento. L'item 0.1 chiamava questo "ultimo passo, meccanico" e
non e' mai stato eseguito.

Meccanica di paper2_freeze_v1.py che questo driver deve rispettare
------------------------------------------------------------------
1. `append_jsonl(jsonl, rec)` (riga 324): lo scrittore ACCODA sempre, un record alla
   volta. `--force` azzera `existing`, che e' l'accumulatore in memoria, NON il file.
   Un file rimosso dal disco non riceve un record nuovo, quindi la sua vecchia riga
   resta sola e VINCE il last-wins. **Per ricostruire un tier il corpo va rimosso
   prima.** Qui si rinomina, non si cancella.
2. `iter_files(..., exclude_dirs=[out])`: la directory di output e' sempre esclusa dal
   cammino. Per i cinque tier v1 `--out` DEVE restare results/paper2, altrimenti
   `records` inizierebbe a includere i propri manifest.
3. `include_ext` nell'intestazione e' `sorted(resolve_include(args))`. Tutti e cinque i
   tier hanno insiemi piu' piccoli di DEFAULT_INCLUDE, quindi furono creati con
   `--only-ext`, e passare `--only-ext` con la lista registrata li riproduce esattamente.
   Il driver lo verifica invece di assumerlo.
4. I corpi NON torneranno byte-identici: ogni record porta `mtime_utc` e `scanned_at`.
   L'aggregate dipende solo da `rel:sha256`, quindi e' quello il cancello.

Sicurezza
---------
Ogni tier e' un'operazione atomica dal punto di vista dell'utente: backup di
intestazione e corpo, freeze, confronto dell'aggregate, e **ripristino automatico** se
l'aggregate non torna. Il primo tier che fallisce ferma tutto. I backup non vengono mai
cancellati.

  python src\\paper2_refreeze.py selftest
  python src\\paper2_refreeze.py plan
  python src\\paper2_refreeze.py run --tier features
  python src\\paper2_refreeze.py run

Uscita: 0 tutto invariato, 1 aggregate cambiato o preflight fallito, 2 errore d'uso.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "cauchy.paper2.v1_manifest"
TIER_ORDER = ("features", "fields", "diagrams", "superseded", "records")

# --------------------------------------------------------------------------------------
# CANCELLO. Dichiarati prima di toccare qualunque cosa, verificati prima e dopo.
# Fonte: le intestazioni sul disco, verificate file per file il 28 ago 2026
# (34 836 file, 28 745 619 580 byte, zero mismatch).
# --------------------------------------------------------------------------------------
EXPECTED = {
    "records":    {"aggregate": "5364cf2ef1cac16c66e2f80dcd897bee8d14324100f15d0c9b471085f4b876f0",
                   "n_files": 224,   "total_bytes": 20710671},
    "features":   {"aggregate": "b0601f36c89430b3133b46e6107a0c13f50f55a8626fefcc808a6ec3d8d21fcc",
                   "n_files": 12189, "total_bytes": 24326788},
    "fields":     {"aggregate": "bf176f95a3b9e31d0c78590a2d7eef1fdc6ecd2bbf5efc4388358ca5724a2c34",
                   "n_files": 2202,  "total_bytes": 18472477342},
    "diagrams":   {"aggregate": "3a746c95e009b89a3a66408880b3085abe41e5f1e5c9ac12ee05009ae08f4929",
                   "n_files": 16221, "total_bytes": 4488929201},
    "superseded": {"aggregate": "f2cf37627a44e4475a8a19b19d7631b0a094098e509220f1f5a0267bffb33764",
                   "n_files": 4000,  "total_bytes": 5739175578},
}
# Derivati da EXPECTED, non ridichiarati: due costanti indipendenti possono divergere,
# e i totali sono esattamente la somma dei tier (34 836 file, 28 745 619 580 byte).
TOTAL_FILES = sum(v["n_files"] for v in EXPECTED.values())
TOTAL_BYTES = sum(v["total_bytes"] for v in EXPECTED.values())
assert (TOTAL_FILES, TOTAL_BYTES) == (34836, 28745619580), \
    "i tier attesi non sommano ai totali dichiarati nella consegna"

# DEFAULT_INCLUDE di paper2_freeze_v1.py:54-57, replicato per il controllo di punto 3.
DEFAULT_INCLUDE = {".json", ".jsonl", ".npy", ".npz", ".csv", ".txt", ".h5", ".hdf5",
                   ".fits", ".pkl", ".parquet", ".yaml", ".yml", ".tex", ".md"}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp() -> str:
    # microsecondi: due run nello stesso secondo condividerebbero la cartella di backup
    # e il secondo sovrascriverebbe il primo, che e' l'unica copia di sicurezza.
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def aggregate_digest(records) -> str:
    """paper2_freeze_v1.py:235-238, replicato per il controllo indipendente."""
    lines = sorted(f"{r['rel']}:{r['sha256']}" for r in records)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def read_body(path: Path):
    """Last-wins sui percorsi: il JSONL e' accodato, righe successive superano."""
    by_rel = {}
    n = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            n += 1
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "rel" in r and "sha256" in r:
                by_rel[r["rel"]] = r
    return list(by_rel.values()), n


def manifest_paths(mdir: Path, tier: str):
    return (mdir / f"ensemble_v1_manifest_{tier}.jsonl",
            mdir / f"ensemble_v1_freeze_{tier}.json")


def load_header(mdir: Path, tier: str):
    _, hp = manifest_paths(mdir, tier)
    if not hp.is_file():
        raise SystemExit(f"intestazione assente: {hp}")
    h = json.loads(hp.read_text(encoding="utf-8"))
    if h.get("schema") != SCHEMA:
        raise SystemExit(f"{hp.name}: schema inatteso {h.get('schema')!r}")
    return h


def build_cmd(python: str, tool: Path, hdr: dict, tier: str, ref: Path, out: Path):
    inc = list(hdr.get("include_ext") or [])
    if not inc:
        raise SystemExit(f"{tier}: include_ext vuoto nell'intestazione")
    if set(inc) >= DEFAULT_INCLUDE:
        raise SystemExit(
            f"{tier}: include_ext contiene l'insieme di default, quindi il tier NON fu "
            f"creato con --only-ext e la ricostruzione del comando non e' fedele. "
            f"Ricostruire a mano.")
    cmd = [python, str(tool), "freeze",
           "--roots", *[str(r) for r in hdr.get("roots", [])],
           "--ref", str(ref),
           "--out", str(out),
           "--base", str(hdr.get("base", ".")),
           "--only-ext", *inc,
           "--label", tier]
    exc = list(hdr.get("exclude_pat") or [])
    if exc:
        cmd += ["--exclude", *exc]
    return cmd


def git_dirty(base: Path):
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=str(base),
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"git non eseguibile: {exc}"
    if r.returncode != 0:
        return None, f"git status uscito con {r.returncode}: {r.stderr[:200]}"
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    return lines, None


# --------------------------------------------------------------------------- preflight

def preflight(base: Path, mdir: Path, tiers, expected, allow_dirty: bool, quiet=False,
              require_git: bool = True, totals=None):
    """Nessuna scrittura. Ritorna (ok, report)."""
    rep = {"utc": utcnow(), "checks": [], "tiers": {}}

    def add(name, ok, detail):
        rep["checks"].append({"check": name, "ok": bool(ok), "detail": detail})

    dirty, err = git_dirty(base)
    if err:
        # Fuori da un repository il controllo non si applica; dentro, un git illeggibile
        # e' un problema, perche' il freeze registra commit e dirty nell'intestazione.
        add("git status leggibile", not require_git, err)
    else:
        add("albero git pulito", not dirty or allow_dirty,
            f"{len(dirty)} percorsi non committati"
            + (" (--allow-dirty)" if dirty and allow_dirty else "")
            + (f": {dirty[:5]}" if dirty else ""))

    tot_f = tot_b = 0
    for tier in tiers:
        bp, hp = manifest_paths(mdir, tier)
        h = load_header(mdir, tier)
        recs, n_lines = read_body(bp)
        agg = aggregate_digest(recs)
        exp = expected[tier]
        tb = sum(r.get("bytes", 0) for r in recs)
        rep["tiers"][tier] = {"aggregate_now": agg, "n_files": len(recs),
                              "lines": n_lines, "total_bytes": tb,
                              "header_aggregate": h.get("aggregate_sha256"),
                              "reference_sha256": h.get("reference_sha256"),
                              "dirty_at_freeze": h.get("git", {}).get("dirty")}
        add(f"{tier}: aggregate atteso", agg == exp["aggregate"],
            f"{agg[:12]}… atteso {exp['aggregate'][:12]}…")
        add(f"{tier}: intestazione concorde col corpo",
            h.get("aggregate_sha256") == agg and h.get("n_files") == len(recs),
            f"header n_files={h.get('n_files')} corpo={len(recs)} righe={n_lines}")
        add(f"{tier}: conteggio atteso", len(recs) == exp["n_files"],
            f"{len(recs)} contro {exp['n_files']}")
        tot_f += len(recs)
        tot_b += tb
    # I totali si controllano solo quando sono tutti e cinque i tier reali: su un
    # sottoinsieme, o su un insieme sintetico, confrontarli col totale dichiarato
    # fallirebbe per costruzione.
    if totals:
        tf, tb = totals
        add("totale file", tot_f == tf, f"{tot_f} contro {tf}")
        add("totale byte", tot_b == tb, f"{tot_b:,} contro {tb:,}")

    rep["ok"] = all(c["ok"] for c in rep["checks"])
    if not quiet:
        for c in rep["checks"]:
            print(f"  [{'ok' if c['ok'] else 'FAIL'}] {c['check']}: {c['detail']}")
    return rep["ok"], rep


# ------------------------------------------------------------------------------ refreeze

def refreeze_tier(base: Path, mdir: Path, tier: str, hdr: dict, cmd, expected,
                  backup_dir: Path, quiet=False):
    """Backup, freeze, confronto, ripristino su fallimento. Ritorna un record."""
    bp, hp = manifest_paths(mdir, tier)
    backup_dir.mkdir(parents=True, exist_ok=True)
    b_body = backup_dir / bp.name
    b_head = backup_dir / hp.name
    shutil.copy2(bp, b_body)
    shutil.copy2(hp, b_head)

    def restore():
        shutil.copy2(b_body, bp)
        shutil.copy2(b_head, hp)

    # il corpo va RIMOSSO, non solo ignorato: append_jsonl accoda e --force azzera
    # soltanto l'accumulatore in memoria, quindi una riga stantia sopravviverebbe.
    bp.unlink()

    rec = {"tier": tier, "cmd": cmd, "utc": utcnow(),
           "backup": {"body": str(b_body), "header": str(b_head)}}
    try:
        r = subprocess.run(cmd, cwd=str(base), capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as exc:
        restore()
        rec.update(status="ERRORE_LANCIO", error=str(exc)[:300])
        return rec
    rec["returncode"] = r.returncode
    rec["stdout_tail"] = r.stdout[-1500:]
    rec["stderr_tail"] = r.stderr[-1500:]
    if r.returncode != 0:
        restore()
        rec["status"] = "FREEZE_FALLITO"
        return rec

    if not bp.is_file():
        restore()
        rec["status"] = "CORPO_NON_SCRITTO"
        return rec

    recs, n_lines = read_body(bp)
    agg = aggregate_digest(recs)
    tb = sum(x.get("bytes", 0) for x in recs)
    new_h = json.loads(hp.read_text(encoding="utf-8"))
    exp = expected[tier]
    rec.update({"aggregate_new": agg, "aggregate_expected": exp["aggregate"],
                "n_files": len(recs), "lines": n_lines, "total_bytes": tb,
                "header_aggregate": new_h.get("aggregate_sha256"),
                "reference_sha256": new_h.get("reference_sha256"),
                "exclude_dirs": new_h.get("exclude_dirs"),
                "git_dirty": new_h.get("git", {}).get("dirty")})

    invariant = (agg == exp["aggregate"]
                 and new_h.get("aggregate_sha256") == exp["aggregate"]
                 and len(recs) == exp["n_files"]
                 and tb == exp["total_bytes"])
    if not invariant:
        restore()
        rec["status"] = "AGGREGATE_CAMBIATO"
        return rec
    rec["status"] = "INVARIATO"
    return rec


def cmd_plan(args) -> int:
    base = Path(args.base).resolve()
    mdir = base / args.manifest_dir
    tiers = args.tier or list(TIER_ORDER)
    totals = (TOTAL_FILES, TOTAL_BYTES) if set(tiers) == set(EXPECTED) else None
    print(f"=== PREFLIGHT === {utcnow()}")
    ok, _ = preflight(base, mdir, tiers, EXPECTED, args.allow_dirty, totals=totals)
    print(f"\n=== COMANDI ({len(tiers)} tier, nell'ordine) ===")
    for tier in tiers:
        h = load_header(mdir, tier)
        cmd = build_cmd(sys.executable, Path(args.tool), h, tier,
                        Path(args.ref), mdir)
        print(f"\n  [{tier}]  corpo -> {args.backup_dir}/")
        print("  " + " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd))
    print(f"\npreflight: {'OK' if ok else 'FALLITO'}")
    return 0 if ok else 1


def cmd_run(args) -> int:
    base = Path(args.base).resolve()
    mdir = base / args.manifest_dir
    tiers = args.tier or list(TIER_ORDER)
    out_log = Path(args.out) if args.out else base / "logs" / "refreeze.jsonl"

    totals = (TOTAL_FILES, TOTAL_BYTES) if set(tiers) == set(EXPECTED) else None
    print(f"=== PREFLIGHT === {utcnow()}")
    ok, pre = preflight(base, mdir, tiers, EXPECTED, args.allow_dirty, totals=totals)
    if not ok:
        print("\npreflight FALLITO: nulla e' stato toccato.")
        return 1

    backup_dir = base / args.backup_dir / stamp()
    print(f"\n=== RICONGELAMENTO === backup in {backup_dir}")
    results = []
    for tier in tiers:
        h = load_header(mdir, tier)
        cmd = build_cmd(sys.executable, Path(args.tool), h, tier, Path(args.ref), mdir)
        print(f"\n  [{tier}] ...")
        rec = refreeze_tier(base, mdir, tier, h, cmd, EXPECTED, backup_dir)
        results.append(rec)
        if rec["status"] == "INVARIATO":
            print(f"    INVARIATO  aggregate {rec['aggregate_new'][:12]}…  "
                  f"{rec['n_files']} file  righe={rec['lines']}  "
                  f"dirty={rec.get('git_dirty')}  ref={str(rec.get('reference_sha256'))[:12]}…")
        else:
            print(f"    {rec['status']} — ripristinato dal backup, mi fermo qui.")
            if rec.get("aggregate_new"):
                print(f"    atteso {rec['aggregate_expected']}")
                print(f"    ottenuto {rec['aggregate_new']}")
            if rec.get("stderr_tail"):
                print("    stderr:", rec["stderr_tail"][-500:])
            break

    print("\n=== VERIFICA FINALE ===")
    ok2, post = preflight(base, mdir, tiers, EXPECTED, allow_dirty=True, quiet=False,
                          totals=totals)

    status = ("INVARIATO" if all(r["status"] == "INVARIATO" for r in results) and ok2
              else "FERMATO")
    payload = {"utc": utcnow(), "status": status, "base": str(base),
               "tiers": tiers, "backup_dir": str(backup_dir),
               "preflight": pre, "results": results, "postflight": post}
    out_log.parent.mkdir(parents=True, exist_ok=True)
    with open(out_log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    print(f"\nESITO: {status}   record appeso a {out_log}")
    return 0 if status == "INVARIATO" else 1


# ------------------------------------------------------------------------------ selftest

STUB = r'''
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
SCHEMA = "cauchy.paper2.v1_manifest"
def sha(p):
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b); n += len(b)
    return h.hexdigest(), n
ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
sp = sub.add_parser("freeze")
for a in ("--roots",): sp.add_argument(a, nargs="+", required=True)
sp.add_argument("--ref", required=True); sp.add_argument("--out", required=True)
sp.add_argument("--base", default="."); sp.add_argument("--only-ext", nargs="*", dest="only_ext")
sp.add_argument("--exclude", nargs="*"); sp.add_argument("--label", required=True)
sp.add_argument("--force", action="store_true"); sp.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
base = Path(a.base).resolve(); out = Path(a.out).resolve()
exts = {e.lower() for e in (a.only_ext or [])}
jsonl = out / f"ensemble_v1_manifest_{a.label}.jsonl"
summary = out / f"ensemble_v1_freeze_{a.label}.json"
existing = {}
if jsonl.exists():
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line); existing[r["rel"]] = r
found = []
for root in a.roots:
    rp = Path(root)
    rp = rp if rp.is_absolute() else base / rp
    for dp, dns, fns in os.walk(rp):
        if out == Path(dp).resolve() or out in Path(dp).resolve().parents:
            continue
        for fn in sorted(fns):
            p = Path(dp) / fn
            if p.suffix.lower() not in exts: continue
            if a.exclude and any(x in p.as_posix() for x in a.exclude): continue
            if out == p.resolve().parent or out in p.resolve().parents: continue
            found.append(p)
for p in found:
    rel = p.resolve().relative_to(base).as_posix()
    if rel in existing: continue
    d, n = sha(p)
    rec = {"rel": rel, "sha256": d, "bytes": n, "mtime_utc": "x", "scanned_at": "y"}
    with open(jsonl, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec) + "\n")
    existing[rel] = rec
recs = list(existing.values())
agg = hashlib.sha256("\n".join(sorted(f"{r['rel']}:{r['sha256']}" for r in recs)).encode()).hexdigest()
doc = {"schema": SCHEMA, "schema_version": "1.0", "ensemble": "v1", "tier": a.label,
       "include_ext": sorted(exts), "exclude_pat": list(a.exclude or []),
       "exclude_dirs": [out.relative_to(base).as_posix() if out.is_relative_to(base) else out.as_posix()],
       "base": base.as_posix(), "roots": [Path(r).as_posix() for r in a.roots],
       "n_files": len(recs), "total_bytes": sum(r["bytes"] for r in recs),
       "aggregate_sha256": agg, "reference_sha256": "NEW" * 21 + "x",
       "git": {"commit": "c" * 40, "dirty": False},
       "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
summary.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print("AGGREGATE DIGEST", agg)
'''


def cmd_selftest(args) -> int:
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")
        ok = ok and bool(cond)

    tmp = Path(tempfile.mkdtemp(prefix="refrz_"))
    try:
        base = tmp / "cauchy"
        (base / "src").mkdir(parents=True)
        tool = base / "src" / "stub_freeze.py"
        tool.write_text(STUB, encoding="utf-8")
        (base / "src" / "ref.json").write_text('{"r":1}', encoding="utf-8")
        mdir = base / "results" / "paper2"
        mdir.mkdir(parents=True)
        for i in range(5):
            p = base / f"results/tierA/a{i}.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'{{"i":{i}}}\n')

        def freeze(label="alpha"):
            subprocess.run([sys.executable, str(tool), "freeze",
                            "--roots", str(base / "results/tierA"),
                            "--ref", str(base / "src/ref.json"),
                            "--out", str(mdir), "--base", str(base),
                            "--only-ext", ".jsonl", "--label", label],
                           cwd=str(base), capture_output=True, text=True, check=True)

        freeze()
        h0 = json.loads((mdir / "ensemble_v1_freeze_alpha.json").read_text())
        exp = {"alpha": {"aggregate": h0["aggregate_sha256"],
                         "n_files": h0["n_files"], "total_bytes": h0["total_bytes"]}}

        def run(tiers=("alpha",), allow_dirty=True):
            bdir = base / "backup"
            recs = []
            for t in tiers:
                h = load_header(mdir, t)
                cmd = build_cmd(sys.executable, tool, h, t,
                                base / "src/ref.json", mdir)
                recs.append(refreeze_tier(base, mdir, t, h, cmd, exp,
                                          bdir / stamp(), quiet=True))
            return recs

        # 1. ricongelamento a contenuto invariato
        r = run()[0]
        expect("1. contenuto invariato -> INVARIATO", r["status"] == "INVARIATO",
               f"({r['status']})")
        expect("1b. il corpo NON e' byte-identico ma l'aggregate si'",
               r["aggregate_new"] == exp["alpha"]["aggregate"])
        expect("1c. l'intestazione nuova porta dirty=False e ref aggiornato",
               r["git_dirty"] is False and r["reference_sha256"].startswith("NEW"))
        expect("1d. exclude_dirs ora dichiarato", bool(r["exclude_dirs"]))

        # 2. il corpo va rimosso, non riusato: altrimenti resta la voce stantia
        body = mdir / "ensemble_v1_manifest_alpha.jsonl"
        lines = body.read_text().splitlines(True)
        (base / "results/tierA/a4.jsonl").unlink()
        body.write_text("".join(lines))            # corpo vecchio, con a4
        recs_stale, _ = read_body(body)
        expect("2. senza rimozione del corpo la voce stantia sopravvive",
               any(x["rel"].endswith("a4.jsonl") for x in recs_stale))
        r = run()[0]
        expect("2b. rimuovendo il corpo, il file sparito esce dal manifest "
               "e l'aggregate CAMBIA -> ripristino",
               r["status"] == "AGGREGATE_CAMBIATO")
        after, _ = read_body(body)
        expect("2c. dopo il ripristino il corpo e' quello di prima",
               len(after) == 5 and aggregate_digest(after) == exp["alpha"]["aggregate"])
        (base / "results/tierA/a4.jsonl").write_text('{"i":4}\n')

        # 3. un file aggiunto sposta l'aggregate e viene fermato
        (base / "results/tierA/INTRUSO.jsonl").write_text('{"z":1}\n')
        r = run()[0]
        expect("3. file nuovo -> AGGREGATE_CAMBIATO e ripristino",
               r["status"] == "AGGREGATE_CAMBIATO")
        cur, _ = read_body(body)
        expect("3b. ripristinato: 5 voci, aggregate originale",
               len(cur) == 5 and aggregate_digest(cur) == exp["alpha"]["aggregate"])
        (base / "results/tierA/INTRUSO.jsonl").unlink()

        # 4. un byte cambiato dentro un file: stesso conteggio, aggregate diverso
        p = base / "results/tierA/a2.jsonl"
        keep = p.read_text(); p.write_text('{"i":99}\n')
        r = run()[0]
        expect("4. contenuto modificato a parita' di conteggio -> fermato",
               r["status"] == "AGGREGATE_CAMBIATO" and r["n_files"] == 5)
        p.write_text(keep)
        cur, _ = read_body(body)
        expect("4b. ripristinato", aggregate_digest(cur) == exp["alpha"]["aggregate"])

        # 5. il preflight rifiuta di partire se lo stato di partenza non e' l'atteso
        bad = {"alpha": {"aggregate": "0" * 64, "n_files": 5,
                         "total_bytes": exp["alpha"]["total_bytes"]}}
        okp, _ = preflight(base, mdir, ["alpha"], bad, allow_dirty=True, quiet=True,
                           require_git=False)
        expect("5. preflight blocca se l'aggregate di partenza non e' quello atteso",
               not okp)
        okp, _ = preflight(base, mdir, ["alpha"], exp, allow_dirty=True, quiet=True,
                           require_git=False)
        expect("5b. preflight passa sullo stato buono", okp)

        # 6. include_ext pari al default: comando non ricostruibile, si rifiuta
        h = load_header(mdir, "alpha")
        h["include_ext"] = sorted(DEFAULT_INCLUDE)
        (mdir / "ensemble_v1_freeze_alpha.json").write_text(json.dumps(h))
        try:
            build_cmd(sys.executable, tool, h, "alpha", base / "src/ref.json", mdir)
            caught = False
        except SystemExit:
            caught = True
        expect("6. include_ext = default -> rifiuta di indovinare il comando", caught)

        # 7. i backup non vengono mai cancellati
        n_bk = len(list((base / "backup").rglob("*.jsonl")))
        expect("7. backup conservati, uno per run", n_bk == 4, f"({n_bk} copie)")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("selftest"); p.set_defaults(func=cmd_selftest)
    for name, fn in (("plan", cmd_plan), ("run", cmd_run)):
        p = sub.add_parser(name)
        p.add_argument("--base", default=".")
        p.add_argument("--manifest-dir", default="results/paper2")
        p.add_argument("--tool", default="src/paper2_freeze_v1.py")
        p.add_argument("--ref", default="src/paper2_v1_reference.json")
        p.add_argument("--tier", nargs="+", default=None,
                       help=f"sottoinsieme, nell'ordine dato. Default: {' '.join(TIER_ORDER)}")
        p.add_argument("--backup-dir", default="backup/refreeze")
        p.add_argument("--allow-dirty", action="store_true")
        if name == "run":
            p.add_argument("--out", default=None)
        p.set_defaults(func=fn)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

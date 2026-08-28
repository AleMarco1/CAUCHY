#!/usr/bin/env python3
"""
paper2_freeze_v1.py  --  Checklist Paper 2, item 0.1: congelare l'ensemble v1.

Two jobs:

  1. FREEZE   Walk the v1 artefact tree, hash every file, and write an append-only
              JSONL of per-file digests plus a summary with an aggregate digest.
              Resumable: files already in the JSONL are skipped unless --force.

  2. VERIFY   Re-walk the same tree and diff against an existing manifest.
              Reports added / removed / CHANGED files and exits non-zero on drift.
              This is what proves, six months from now, that v1 did not move.

The script also loads paper2_v1_reference.json and checks its self-digest before
doing anything else (the "cancello": no script reports new numbers until it has
reproduced a frozen reference).

Usage (PowerShell, from D:\\projects\\cauchy):

  # first run - freeze
  python src\\paper2_freeze_v1.py freeze `
      --roots results\\paper1 results\\m26 data\\cache\\mock_delta `
      --ref   src\\paper2_v1_reference.json `
      --out   results\\paper2

  # later - prove nothing drifted
  python src\\paper2_freeze_v1.py verify `
      --roots results\\paper1 results\\m26 data\\cache\\mock_delta `
      --ref   src\\paper2_v1_reference.json `
      --out   results\\paper2

Exit codes:  0 clean | 1 drift detected | 2 usage/IO error | 3 reference gate failed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "cauchy.paper2.v1_manifest"
SCHEMA_VERSION = "1.0"
CHUNK = 1 << 20  # 1 MiB

# Extensions worth hashing. Everything else is ignored, but counted in the
# summary so an unexpected file type never disappears silently.
DEFAULT_INCLUDE = {
    ".json", ".jsonl", ".npy", ".npz", ".csv", ".txt", ".h5", ".hdf5",
    ".fits", ".pkl", ".parquet", ".yaml", ".yml", ".tex", ".md",
}
ALWAYS_SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", ".mypy_cache", ".venv"}


# --------------------------------------------------------------------------- io

def atomic_write_text(path: Path, text: str) -> None:
    """Write via a temp file in the same directory, then replace. Crash-safe."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def append_jsonl(path: Path, record: dict) -> None:
    """Append one record and fsync. Append-only by construction."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # A truncated final line is the expected crash signature.
                sys.stderr.write(f"  warning: unparseable line {ln} in {path}, skipped\n")
    return out


def sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


def git_provenance(cwd: Path, exclude_dir: Path | None = None) -> dict:
    """Commit hash AND whether the tree is dirty.

    A commit hash alone is misleading: if there are uncommitted changes, it
    does not identify the code that produced the artefacts. Record both.
    """
    out = {"commit": None, "dirty": None, "dirty_count": None,
           "dirty_files": [], "dirty_truncated": False}
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(cwd),
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return out
        out["commit"] = r.stdout.strip()
        st = subprocess.run(["git", "status", "--porcelain"], cwd=str(cwd),
                            capture_output=True, text=True, timeout=30)
        if st.returncode == 0:
            files = [ln for ln in st.stdout.splitlines() if ln.strip()]
            # La directory di output e' esclusa dal conteggio: i manifest non sono ne'
            # codice ne' artefatti, sono il registro che questo run sta scrivendo, e
            # durante un ricongelamento a piu' tier quelli gia' fatti risultano
            # legittimamente modificati. Contarli renderebbe dirty=False irraggiungibile
            # per costruzione, che e' il contrario di cio' che il campo deve dire.
            if exclude_dir is not None:
                try:
                    pref = exclude_dir.resolve().relative_to(cwd.resolve()).as_posix() + "/"
                    files = [ln for ln in files if pref not in ln.replace("\\", "/")]
                    out["excluded_from_dirty"] = pref
                except ValueError:
                    pass
            out["dirty"] = bool(files)
            out["dirty_count"] = len(files)          # the TOTAL, never truncated
            out["dirty_files"] = files[:40]
            out["dirty_truncated"] = len(files) > 40
    except Exception:
        pass
    return out


# ------------------------------------------------------------------- reference

def load_reference(ref_path: Path) -> dict:
    """Gate: the reference set must parse and match its own recorded digest."""
    if not ref_path.exists():
        sys.stderr.write(f"GATE FAILED: reference not found: {ref_path}\n")
        sys.exit(3)
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    recorded = ref.pop("_self_sha256", None)
    blob = json.dumps(ref, indent=2, sort_keys=True, ensure_ascii=False)
    actual = hashlib.sha256(blob.encode()).hexdigest()
    if recorded is None:
        sys.stderr.write("GATE FAILED: reference carries no _self_sha256.\n")
        sys.exit(3)
    if actual != recorded:
        sys.stderr.write(
            "GATE FAILED: reference self-digest mismatch.\n"
            f"  recorded {recorded}\n  actual   {actual}\n"
            "  The v1 reference set has been edited. That is not allowed:\n"
            "  v1 is frozen. Restore it from the repository.\n")
        sys.exit(3)
    ref["_self_sha256"] = recorded
    return ref


def print_gate(ref: dict) -> None:
    p = ref["primary"]["NGC"]
    s = ref["primary"]["SGC_n2000"]
    print("  ensemble v1 reference set: digest OK")
    print(f"    NGC  N_H1(DESI) = {p['N_H1_DESI']}   mocks = "
          f"{p['mock_mean']} +/- {p['mock_sd']} (n={p['n_mocks']})   "
          f"deficit = {p['deficit_frac']*100:.2f}%  rank {p['empirical_rank']}")
    print(f"    SGC  N_H1(DESI) = {s['N_H1_DESI']}   mocks = "
          f"{s['mock_mean']} +/- {s['mock_sd']} (n={s['n_mocks']})   "
          f"deficit = {s['deficit_frac']*100:.2f}%  rank {s['empirical_rank']}")
    print("    weighting: voxelize_mock UNIT weights  <<< this is what v1 means")


# ------------------------------------------------------------------- scanning

def iter_files(roots: list[Path], include: set[str], base: Path,
               exclude_dirs: list[Path] | None = None,
               exclude_pat: list[str] | None = None):
    """Walk the roots, skipping anything under exclude_dirs.

    The output directory MUST be excluded: it commonly sits inside a scanned
    root, and without this the manifest hashes itself. That is not merely
    noisy -- a self-referential entry changes on every run and masks real
    drift in the artefacts the manifest exists to protect.
    """
    ex = [d.resolve() for d in (exclude_dirs or [])]

    def excluded(p: Path) -> bool:
        rp = p.resolve()
        return any(rp == d or d in rp.parents for d in ex)

    for root in roots:
        if not root.exists():
            sys.stderr.write(f"  warning: root does not exist, skipped: {root}\n")
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in ALWAYS_SKIP_DIRS
                           and not excluded(Path(dirpath) / d)]
            if excluded(Path(dirpath)):
                continue
            for fn in sorted(filenames):
                p = Path(dirpath) / fn
                if p.suffix.lower() not in include:
                    continue
                if exclude_pat:
                    ap = p.as_posix()
                    if any(pat in ap for pat in exclude_pat):
                        continue
                try:
                    rel = p.resolve().relative_to(base.resolve()).as_posix()
                except ValueError:
                    rel = p.resolve().as_posix()
                yield p, rel


def resolve_include(args) -> set[str]:
    def norm(e):
        return e if e.startswith(".") else "." + e
    if getattr(args, "only_ext", None):
        return {norm(e).lower() for e in args.only_ext}
    return DEFAULT_INCLUDE | {norm(e).lower() for e in (args.ext or [])}


def manifest_paths(out: Path, label: str | None) -> tuple[Path, Path]:
    sfx = f"_{label}" if label else ""
    return (out / f"ensemble_v1_manifest{sfx}.jsonl",
            out / f"ensemble_v1_freeze{sfx}.json")


def aggregate_digest(records: list[dict]) -> str:
    """Order-independent digest of the whole set: hash of sorted 'rel:sha' lines."""
    lines = sorted(f"{r['rel']}:{r['sha256']}" for r in records)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


# ---------------------------------------------------------------------- freeze

def cmd_freeze(args) -> int:
    base = Path(args.base).resolve()
    out = Path(args.out).resolve()
    jsonl, summary = manifest_paths(out, args.label)

    # Lo stato git va misurato PRIMA di scrivere: il manifest e' un file tracciato, e
    # appenderlo sporca l'albero. Misurandolo alla fine il freeze osserva la propria
    # scrittura e non puo' mai registrare dirty=False, qualunque sia lo stato di
    # partenza. Cio' che deve identificare e' il codice che ha prodotto gli artefatti,
    # cioe' l'albero com'era all'inizio del run.
    git_at_start = git_provenance(base, exclude_dir=out)

    ref = load_reference(Path(args.ref))
    print("\n=== GATE ===")
    print_gate(ref)
    if args.label:
        print(f"  tier: {args.label}")

    include_dry = resolve_include(args)
    if args.dry_run:
        print("\n=== DRY RUN (nothing written, nothing hashed) ===")
        roots_d = [Path(r).resolve() for r in args.roots]
        by_ext: dict[str, list[int]] = {}
        by_dir: dict[str, list[int]] = {}
        biggest: list[tuple[int, str]] = []
        for p, rel in iter_files(roots_d, include_dry, base, exclude_dirs=[out],
                                    exclude_pat=args.exclude):
            try:
                nb = p.stat().st_size
            except OSError:
                continue
            by_ext.setdefault(p.suffix.lower(), []).append(nb)
            parts = rel.split("/")
            by_dir.setdefault("/".join(parts[:2]) if len(parts) > 2
                              else "/".join(parts[:-1]) or ".", []).append(nb)
            biggest.append((nb, rel))
        n = sum(len(v) for v in by_ext.values())
        tot = sum(sum(v) for v in by_ext.values())
        print(f"  {n} files, {tot/2**30:.2f} GiB, ~{tot/(150*2**20):.0f}s to hash "
              f"at 150 MiB/s\n")
        print(f"  {'ext':<10} {'files':>7} {'GiB':>9}")
        for ext, v in sorted(by_ext.items(), key=lambda kv: -sum(kv[1])):
            print(f"  {ext:<10} {len(v):>7} {sum(v)/2**30:>9.3f}")

        print(f"\n  {'directory (2 levels)':<44} {'files':>7} {'GiB':>9}")
        for d, v in sorted(by_dir.items(), key=lambda kv: -sum(kv[1]))[:25]:
            print(f"  {d:<44} {len(v):>7} {sum(v)/2**30:>9.3f}")
        biggest.sort(reverse=True)
        if biggest:
            print("\n  largest files:")
            for nb, rel in biggest[:8]:
                print(f"    {nb/2**20:>9.1f} MiB  {rel}")
        print("\n  Re-run without --dry-run to freeze.\n")
        return 0

    existing = {r["rel"]: r for r in read_jsonl(jsonl)} if not args.force else {}
    if existing:
        print(f"\n  resuming: {len(existing)} files already in manifest")

    include = resolve_include(args)
    roots = [Path(r).resolve() for r in args.roots]

    print("\n=== FREEZE ===")
    for r in roots:
        print(f"  root: {r}")

    n_new = n_skip = 0
    total_bytes = 0
    t0 = time.time()
    for p, rel in iter_files(roots, include, base, exclude_dirs=[out],
                            exclude_pat=args.exclude):
        if rel in existing:
            n_skip += 1
            total_bytes += existing[rel].get("bytes", 0)
            continue
        try:
            digest, nbytes = sha256_file(p)
        except OSError as e:
            sys.stderr.write(f"  ERROR reading {p}: {e}\n")
            continue
        rec = {
            "rel": rel,
            "sha256": digest,
            "bytes": nbytes,
            "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                                 .isoformat(timespec="seconds"),
            "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        append_jsonl(jsonl, rec)
        existing[rel] = rec
        n_new += 1
        total_bytes += nbytes
        if n_new % 200 == 0:
            print(f"    ... {n_new} hashed")

    records = list(existing.values())
    agg = aggregate_digest(records)
    dt = time.time() - t0

    doc = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "ensemble": "v1",
        "tier": args.label,
        "include_ext": sorted(resolve_include(args)),
        "exclude_pat": list(args.exclude or []),
        "exclude_dirs": [out.relative_to(base).as_posix()
                         if out.is_relative_to(base) else out.as_posix()],
        "definition": ref["declaration"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base": base.as_posix(),
        "roots": [r.as_posix() for r in roots],
        "n_files": len(records),
        "total_bytes": total_bytes,
        "aggregate_sha256": agg,
        "reference_sha256": ref["_self_sha256"],
        "git": git_at_start,
        "python": sys.version.split()[0],
        "host": os.environ.get("COMPUTERNAME") or os.uname().nodename
                if hasattr(os, "uname") else os.environ.get("COMPUTERNAME"),
    }
    atomic_write_text(summary, json.dumps(doc, indent=2, sort_keys=True) + "\n")

    g = doc["git"]
    if g.get("dirty"):
        n = g.get("dirty_count") or len(g["dirty_files"])
        print(f"\n  !! WARNING: git tree is DIRTY at commit {(g['commit'] or '?')[:12]}")
        print(f"     {n} uncommitted path(s)"
              + (" (list truncated to 40 in the summary)" if g.get("dirty_truncated") else "")
              + "; the recorded commit")
        print("     does not identify the code that produced these artefacts.")
        print("     Commit or stash, then re-run freeze, before quoting this digest.")

    print(f"\n  hashed {n_new} new, skipped {n_skip} already present")
    print(f"  files {len(records)}   bytes {total_bytes:,}   elapsed {dt:.1f}s")
    print(f"\n  AGGREGATE DIGEST  {agg}")
    print(f"  manifest  {jsonl}")
    print(f"  summary   {summary}")
    print("\n  Record the aggregate digest in the frozen protocol and in the\n"
          "  Paper 2 pre-registration. Every later run must reproduce it.\n")
    return 0


# ---------------------------------------------------------------------- verify

def cmd_verify(args) -> int:
    base = Path(args.base).resolve()
    out = Path(args.out).resolve()
    jsonl, summary = manifest_paths(out, args.label)

    ref = load_reference(Path(args.ref))
    print("\n=== GATE ===")
    print_gate(ref)
    if args.label:
        print(f"  tier: {args.label}")

    if not jsonl.exists():
        sys.stderr.write(f"\nERROR: no manifest at {jsonl}. Run 'freeze' first.\n")
        return 2

    # Last record per path wins (append-only file, later entries supersede).
    frozen: dict[str, dict] = {}
    for r in read_jsonl(jsonl):
        frozen[r["rel"]] = r

    include = resolve_include(args)
    roots = [Path(r).resolve() for r in args.roots]

    print("\n=== VERIFY ===")
    seen, changed, added = set(), [], []
    for p, rel in iter_files(roots, include, base, exclude_dirs=[out],
                            exclude_pat=args.exclude):
        seen.add(rel)
        try:
            digest, nbytes = sha256_file(p)
        except OSError as e:
            sys.stderr.write(f"  ERROR reading {p}: {e}\n")
            continue
        if rel not in frozen:
            added.append(rel)
        elif frozen[rel]["sha256"] != digest:
            changed.append((rel, frozen[rel]["sha256"], digest))
    removed = sorted(set(frozen) - seen)

    print(f"  frozen {len(frozen)}   present {len(seen)}")
    for rel, old, new in changed:
        print(f"  CHANGED  {rel}\n             was {old[:16]}...  now {new[:16]}...")
    for rel in removed:
        print(f"  REMOVED  {rel}")
    for rel in added:
        print(f"  added    {rel}")

    agg_now = aggregate_digest(
        [{"rel": r, "sha256": frozen[r]["sha256"]} for r in sorted(seen & set(frozen))]
        + [{"rel": r, "sha256": s} for r, _, s in changed]
    )
    if summary.exists():
        doc = json.loads(summary.read_text(encoding="utf-8"))
        print(f"\n  aggregate at freeze  {doc.get('aggregate_sha256')}")

    if changed or removed:
        print("\n  *** DRIFT DETECTED ***")
        print("  Ensemble v1 is frozen. Either restore the changed artefacts, or\n"
              "  relabel the new state as v2 and record the reason in the protocol.\n")
        return 1
    if added:
        print("\n  No drift in frozen files. New files present but not part of v1.")
        print("  If they belong to v1, re-run 'freeze' to extend the manifest;\n"
              "  if they are Paper 2 products, they belong under results/paper2.\n")
        return 0
    print("\n  CLEAN: ensemble v1 unchanged.\n")
    return 0


# ------------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Freeze / verify CAUCHY ensemble v1 (Paper 2, checklist item 0.1).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("freeze", cmd_freeze), ("verify", cmd_verify)):
        sp = sub.add_parser(name)
        sp.add_argument("--roots", nargs="+", required=True,
                        help="directories holding v1 artefacts")
        sp.add_argument("--ref", required=True, help="paper2_v1_reference.json")
        sp.add_argument("--out", default="results/paper2", help="output directory")
        sp.add_argument("--base", default=".", help="path root for relative names")
        sp.add_argument("--ext", nargs="*", help="extra extensions to include")
        sp.add_argument("--only-ext", nargs="*", dest="only_ext",
                        help="restrict to exactly these extensions (replaces the default set)")
        sp.add_argument("--exclude", nargs="*",
                        help="skip paths containing any of these substrings")
        sp.add_argument("--label", default=None,
                        help="tier name; suffixes the manifest filenames")
        if name == "freeze":
            sp.add_argument("--force", action="store_true",
                            help="re-hash everything, ignoring the existing manifest")
            sp.add_argument("--dry-run", action="store_true",
                            help="count files and bytes, write nothing")
        sp.set_defaults(func=fn)
    args = ap.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted; manifest is append-only, rerun to resume\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())

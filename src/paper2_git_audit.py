#!/usr/bin/env python3
"""
paper2_git_audit.py  --  pre-release check on the CAUCHY repository.

Answers three questions before anything is pushed or archived:

  1. Which large blobs are in the history?  GitHub rejects any file over
     100 MiB and warns above 50 MiB. A blob that entered the history once is
     there forever unless the history is rewritten, so this must be known
     BEFORE the first push, not after a rejected one.
  2. What is tracked under results/ ?  The freeze established that only a
     small fraction of results/ belongs in version control.
  3. Are the excluded directories actually ignored?

Read-only: runs git plumbing commands and prints. Changes nothing.

Usage, from D:\\projects\\cauchy :

    python src\\paper2_git_audit.py
    python src\\paper2_git_audit.py --top 30 --json audit.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

GITHUB_HARD_MIB = 100.0   # push rejected above this
GITHUB_WARN_MIB = 50.0    # warning above this

# Directories the freeze established as excluded from v1 / from the repo.
SHOULD_BE_IGNORED = [
    "results/phase2_tau_fields",
    "results/phase1_persistence_diagrams",
    "results/phase8_test2_fields",
    "results/phase8_cutsky_fields",
    "results/paper1",
]


def git(args: list[str], stdin: bytes | None = None) -> bytes:
    r = subprocess.run(["git"] + args, capture_output=True, input=stdin)
    if r.returncode != 0:
        sys.stderr.write(f"git {' '.join(args)} failed:\n{r.stderr.decode(errors='replace')}\n")
        sys.exit(2)
    return r.stdout


def mib(n: int) -> float:
    return n / 1024 / 1024


def largest_blobs(top: int) -> list[tuple[int, str, str]]:
    """Every blob ever committed, biggest first. Binary pipes, no shell."""
    objs = git(["rev-list", "--objects", "--all"])
    info = git(["cat-file", "--batch-check=%(objecttype) %(objectname) %(objectsize) %(rest)"],
               stdin=objs)
    out = []
    for line in info.decode("utf-8", errors="replace").splitlines():
        parts = line.split(" ", 3)
        if len(parts) < 3 or parts[0] != "blob":
            continue
        path = parts[3] if len(parts) > 3 else "<unnamed>"
        try:
            out.append((int(parts[2]), parts[1], path))
        except ValueError:
            continue
    out.sort(reverse=True)
    # a blob can appear under several paths; keep the first (largest) mention
    seen, uniq = set(), []
    for sz, oid, path in out:
        if oid in seen:
            continue
        seen.add(oid)
        uniq.append((sz, oid, path))
        if len(uniq) >= top:
            break
    return uniq


def tracked_under(prefix: str) -> list[str]:
    out = git(["ls-files", prefix]).decode("utf-8", errors="replace")
    return [l for l in out.splitlines() if l.strip()]


def check_ignored(paths: list[str]) -> dict[str, bool]:
    res = {}
    for p in paths:
        r = subprocess.run(["git", "check-ignore", "-q", p], capture_output=True)
        # 0 = ignored, 1 = not ignored, 128 = error (e.g. path absent)
        res[p] = (r.returncode == 0)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-release audit of the CAUCHY git repository.")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--json", default=None, help="also write the findings here")
    args = ap.parse_args()

    report: dict = {}
    problems: list[str] = []

    print("\n=== 1. LARGEST BLOBS IN THE HISTORY ===")
    blobs = largest_blobs(args.top)
    print(f"  {'MiB':>9}  {'blob':<12}  path")
    for sz, oid, path in blobs:
        m = mib(sz)
        flag = ""
        if m >= GITHUB_HARD_MIB:
            flag = "  <<< OVER GITHUB HARD LIMIT (push will be REJECTED)"
            problems.append(f"blob over 100 MiB: {path} ({m:.1f} MiB)")
        elif m >= GITHUB_WARN_MIB:
            flag = "  <-- over GitHub warning threshold"
            problems.append(f"blob over 50 MiB: {path} ({m:.1f} MiB)")
        print(f"  {m:>9.1f}  {oid[:12]}  {path}{flag}")
    report["largest_blobs"] = [{"bytes": s, "oid": o, "path": p} for s, o, p in blobs]

    print("\n=== 2. TRACKED UNDER results/ ===")
    tr = tracked_under("results")
    by_ext: dict[str, int] = {}
    for f in tr:
        by_ext[Path(f).suffix.lower() or "<none>"] = by_ext.get(Path(f).suffix.lower() or "<none>", 0) + 1
    print(f"  {len(tr)} tracked files")
    for e, n in sorted(by_ext.items(), key=lambda kv: -kv[1]):
        note = ""
        if e == ".pkl":
            note = "  <<< Branch B graphs? should not be tracked"
            problems.append(f"{n} .pkl tracked under results/")
        if e == ".npz":
            note = "  <-- check these are the small feature records, not fields"
        print(f"    {e:<8} {n:>5}{note}")
    report["tracked_results"] = {"n": len(tr), "by_ext": by_ext}

    big_tracked = []
    for f in tr:
        p = Path(f)
        if p.exists() and p.stat().st_size > 10 * 1024 * 1024:
            big_tracked.append((p.stat().st_size, f))
    if big_tracked:
        print("\n  tracked files over 10 MiB on disk:")
        for sz, f in sorted(big_tracked, reverse=True):
            print(f"    {mib(sz):>9.1f} MiB  {f}")
    report["big_tracked"] = [{"bytes": s, "path": f} for s, f in sorted(big_tracked, reverse=True)]

    print("\n=== 3. IGNORE COVERAGE ===")
    ign = check_ignored(SHOULD_BE_IGNORED)
    for p, is_ign in ign.items():
        state = "ignored" if is_ign else "NOT ignored"
        mark = "" if is_ign else "   <-- check whether this is intended"
        print(f"  {state:<12} {p}{mark}")
    report["ignored"] = ign

    print("\n=== 4. PACK STATE ===")
    co = git(["count-objects", "-vH"]).decode()
    for line in co.splitlines():
        print("  " + line)
    npacks = 0
    for line in co.splitlines():
        if line.startswith("packs:"):
            npacks = int(line.split(":")[1])
    if npacks > 4:
        print(f"\n  {npacks} packfiles; 'git gc' would consolidate them (cosmetic, not urgent).")

    print("\n" + "=" * 70)
    if problems:
        print("PROBLEMS FOUND:")
        for p in problems:
            print("  - " + p)
        print("\nA blob already in the history stays there. Removing it requires rewriting")
        print("history (git filter-repo / BFG) and a force-push, which is safe only if")
        print("nobody else has cloned the repository.")
    else:
        print("No blocking problems found. Safe to tag and push.")

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nfindings written to {args.json}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

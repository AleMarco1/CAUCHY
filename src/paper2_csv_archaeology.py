#!/usr/bin/env python3
"""
paper2_csv_archaeology.py  --  recover the canonical per-mock pilot, if it survives.

results/phase8_test2_permock.csv was overwritten by a run with a different HOD
(the path collision that paper1_rev_fix_phase8_paths.py later fixed by adding a
suffix). The copy that reached the freeze is byte-identical to the _hodfit twin,
so the canonical content is not on disk.

Four scripts read that path:
    phase8_w0_exclusion.py, phase9_extract_features.py,
    paper1_rev_v2g_frozen.py, paper1_rev_v2i_close.py

This walks every version of the file ever committed and classifies each by its
numbers, so the decision is made on evidence:

  mean ~35437, sd ~313   -> canonical baseline pilot   -> RESTORE THIS ONE
  mean ~35305, sd ~1033  -> HOD refit                  -> the contaminated one

Read-only: uses `git show` to extract blobs, writes nothing to the repository.

Usage, from D:\\projects\\cauchy :

    python src\\paper2_csv_archaeology.py
    python src\\paper2_csv_archaeology.py --path results/phase8_test2_permock.csv
    python src\\paper2_csv_archaeology.py --extract-to recovered.csv --commit <sha>
"""

from __future__ import annotations

import argparse
import statistics as st
import subprocess
import sys
from pathlib import Path

SIGNATURES = [
    ("CANONICAL baseline pilot", 35436.7, 313.0),
    ("HOD refit (contaminated)", 35305.0, 1033.0),
    ("concentrated HOD",         35048.0, 1220.0),
]


def git(args: list[str]) -> tuple[int, bytes]:
    r = subprocess.run(["git"] + args, capture_output=True)
    return r.returncode, r.stdout


def commits_touching(path: str) -> list[tuple[str, str, str]]:
    code, out = git(["log", "--all", "--follow",
                     "--format=%H\x1f%ad\x1f%s", "--date=short", "--", path])
    if code != 0:
        # --follow needs a single path and fails on some histories; retry without
        code, out = git(["log", "--all", "--format=%H\x1f%ad\x1f%s",
                         "--date=short", "--", path])
    rows = []
    for line in out.decode("utf-8", errors="replace").splitlines():
        parts = line.split("\x1f")
        if len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def blob_at(commit: str, path: str) -> bytes | None:
    code, out = git(["show", f"{commit}:{path}"])
    return out if code == 0 else None


def analyse(blob: bytes) -> dict | None:
    txt = blob.decode("utf-8", errors="replace")
    lines = [l for l in txt.splitlines() if l.strip()]
    if len(lines) < 4:
        return None
    cols = [c.strip() for c in lines[0].split(",")]
    data: dict[str, list[float]] = {c: [] for c in cols}
    for l in lines[1:]:
        for c, v in zip(cols, l.split(",")):
            try:
                data[c].append(float(v))
            except ValueError:
                pass
    res = {"rows": len(lines) - 1, "columns": cols, "bytes": len(blob), "cols": {}}
    for c, v in data.items():
        if len(v) >= 3 and 1e4 < st.mean(v) < 1e5:
            res["cols"][c] = {"n": len(v), "mean": st.mean(v),
                              "sd": st.stdev(v), "min": min(v), "max": max(v)}
    return res


def classify(colstats: dict) -> tuple[str, float] | None:
    best = None
    for c, s in colstats.items():
        for name, mu, sd in SIGNATURES:
            dm, ds = abs(s["mean"] - mu) / mu, abs(s["sd"] - sd) / sd
            if dm < 0.03 and ds < 0.5:
                score = dm + 0.5 * ds
                if best is None or score < best[1]:
                    best = (f"{name}  [col '{c}': mean {s['mean']:.1f}, sd {s['sd']:.1f}]", score)
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description="Find a pre-overwrite version of the per-mock CSV.")
    ap.add_argument("--path", default="results/phase8_test2_permock.csv")
    ap.add_argument("--also", nargs="*",
                    default=["results/phase8_test2_permock_hodfit.csv"],
                    help="other paths to classify for comparison")
    ap.add_argument("--extract-to", default=None)
    ap.add_argument("--commit", default=None)
    args = ap.parse_args()

    if args.extract_to:
        if not args.commit:
            sys.stderr.write("--extract-to needs --commit\n")
            return 2
        blob = blob_at(args.commit, args.path)
        if blob is None:
            sys.stderr.write(f"{args.path} not present at {args.commit}\n")
            return 2
        Path(args.extract_to).write_bytes(blob)
        info = analyse(blob)
        print(f"wrote {len(blob):,} bytes to {args.extract_to}")
        if info:
            print(f"  {info['rows']} rows, columns {info['columns']}")
            c = classify(info["cols"])
            print(f"  classified as: {c[0] if c else 'no match'}")
        return 0

    print(f"\nhistory of {args.path}\n" + "=" * 78)
    rows = commits_touching(args.path)
    if not rows:
        print("  no commit touches this path (was it ever tracked under this name?)")
    seen_blobs: dict[bytes, str] = {}
    for sha, date, subj in rows:
        blob = blob_at(sha, args.path)
        line = f"  {sha[:10]}  {date}  {subj[:52]}"
        if blob is None:
            print(line + "\n      (absent at this commit)")
            continue
        info = analyse(blob)
        if info is None:
            print(line + f"\n      {len(blob):,} bytes, unparseable as CSV")
            continue
        c = classify(info["cols"])
        dup = seen_blobs.get(blob)
        seen_blobs.setdefault(blob, sha[:10])
        print(line)
        print(f"      {info['bytes']:,} bytes, {info['rows']} rows, cols {info['columns']}")
        for cn, s in info["cols"].items():
            print(f"        {cn:<12} n={s['n']:>4}  mean={s['mean']:>11.2f}"
                  f"  sd={s['sd']:>9.2f}  min={s['min']:>10.2f}")
        print(f"      >>> {c[0] if c else 'no signature matched'}"
              + (f"   (identical to blob at {dup})" if dup else ""))

    print("\n" + "=" * 78)
    print("comparison targets")
    print("=" * 78)
    for p in args.also:
        fp = Path(p)
        if fp.exists():
            info = analyse(fp.read_bytes())
            c = classify(info["cols"]) if info else None
            print(f"  {p}  (on disk)")
            if info:
                print(f"      {info['bytes']:,} bytes, {info['rows']} rows")
                print(f"      >>> {c[0] if c else 'no signature matched'}")
        else:
            print(f"  {p}  -- not on disk")

    print("\nreading:")
    print("  A version classified CANONICAL is the pilot the four dependent scripts")
    print("  expect. Restore it with:")
    print(f"     python src\\paper2_csv_archaeology.py --commit <sha> "
          f"--extract-to {args.path}")
    print("  If every version is the HOD refit, the canonical pilot never reached git")
    print("  and the four scripts cannot be re-run without regenerating it. Leaving the")
    print("  file absent is then the honest state: phase8_w0_exclusion.py already fails")
    print("  loudly on a missing source rather than reading the wrong numbers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

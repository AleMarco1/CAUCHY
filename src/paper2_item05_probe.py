#!/usr/bin/env python3
"""
paper2_item05_probe.py  --  Paper 2, checklist item 0.5.

Three binary questions decide whether Proposition 2 applies to the pipeline
as it stands:

  Q1  Are the embedding cube and dx RECOMPUTED from the random catalogue on
      every run, or hard-coded to L = 1997.36 / dx = 15.604 ?
  Q2  Is sigma_px computed as R/dx at runtime, or frozen at 0.3204 ?
  Q3  Is the mask re-derived from the randoms AFTER re-voxelisation, or
      loaded from a file ?

This probe greps the source tree for the constructs that answer them and
prints each hit with context, classified as LITERAL (a hard-coded constant),
DERIVED (computed from data), or LOADED (read from disk).

The classification is a first ordering, not a verdict: read the context.

Usage, from D:\\projects\\cauchy :

    python src\\paper2_item05_probe.py
    python src\\paper2_item05_probe.py --roots src results/paper1/src_bundle_phase9.txt
    python src\\paper2_item05_probe.py --context 3 --max-hits 8 --json probe05.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# The frozen constants of ensemble v1. Seeing any of these as a literal in the
# source is the signal that the quantity is not derived.
CONSTANTS = {
    "1997.36": "L_box NGC", "1997.4": "L_box NGC", "1997.": "L_box NGC",
    "15.604": "dx NGC", "15.60": "dx NGC", "15.6": "dx NGC",
    "0.3204": "sigma_px NGC", "0.320": "sigma_px NGC",
    "1904.5": "L_box SGC", "14.88": "dx SGC",
    "0.3361": "sigma_px SGC", "0.336": "sigma_px SGC",
    "307805": "in-mask voxels NGC", "172225": "in-mask voxels SGC",
}

QUESTIONS = {
    "Q1_box_and_dx": {
        "title": "Embedding cube and dx: derived from the randoms, or hard-coded?",
        "patterns": [
            r"\b(box_?min|box_?max|box_?size|boxsize|L_?box|Lbox|bbox|bounding)\b",
            r"\b(cell_?size|dx|delta_?x|voxel_?size|grid_?spacing)\s*=",
            r"1997\.|15\.60|15\.604|1904\.5|14\.88",
        ],
        "derived_hints": [
            r"\.min\(|\.max\(|np\.min|np\.max|np\.ptp|\.ptp\(",
            r"(rand|random)\w*\s*\[",
            r"percentile|quantile",
        ],
    },
    "Q2_sigma_px": {
        "title": "sigma_px: computed as R/dx at runtime, or frozen?",
        "patterns": [
            r"\b(sigma_?px|sigma_?pix|smooth\w*|R_?smooth|gaussian_filter)\b",
            r"0\.320|0\.3204|0\.336|0\.3361",
            r"\bR\s*/\s*(dx|cell|delta_?x|voxel)",
        ],
        "derived_hints": [r"/\s*(dx|cell_?size|delta_?x|voxel_?size)"],
    },
    "Q3_mask": {
        "title": "Mask: re-derived from the randoms, or loaded from file?",
        "patterns": [
            r"\bmask\b",
            r"0\.01\s*\*|1\s*%|0\.01\s*\*\s*(mean|np\.mean)",
            r"(rand|random)\w*_?(cic|dens|field)",
        ],
        "derived_hints": [r"np\.mean|\.mean\(|>\s*0\.01|threshold|thresh"],
        "loaded_hints": [r"np\.load|np\.loadtxt|json\.load|open\(|read_|fits\."],
    },
}

SKIP_LINE = re.compile(r"^\s*#|^\s*$")


def classify(line: str, q: dict) -> str:
    if any(re.search(p, line) for p in q.get("loaded_hints", [])):
        return "LOADED "
    if any(re.search(p, line) for p in q.get("derived_hints", [])):
        return "DERIVED"
    for c in CONSTANTS:
        if c in line:
            return "LITERAL"
    return "       "


def iter_sources(roots: list[str]):
    for r in roots:
        p = Path(r)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*.py")):
                if "__pycache__" not in f.parts:
                    yield f
            for f in sorted(p.rglob("*.txt")):
                if "bundle" in f.name.lower():
                    yield f
        else:
            sys.stderr.write(f"  (skipped, not found: {r})\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Locate box / dx / sigma_px / mask definitions.")
    ap.add_argument("--roots", nargs="+",
                    default=["src", "results/paper1/src_bundle_phase9.txt"])
    ap.add_argument("--context", type=int, default=2, help="context lines around each hit")
    ap.add_argument("--max-hits", type=int, default=6, help="max hits per question per file")
    ap.add_argument("--files-first", action="store_true",
                    help="only list which files match, without context")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    files = list(iter_sources(args.roots))
    print(f"\nscanning {len(files)} source files\n")

    findings: dict[str, dict] = {q: {} for q in QUESTIONS}
    const_hits: dict[str, list] = {}
    seen_const: set[tuple[str, int]] = set()

    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for qname, q in QUESTIONS.items():
            hits = []
            for i, line in enumerate(lines):
                if SKIP_LINE.match(line):
                    continue
                if any(re.search(p, line, re.I) for p in q["patterns"]):
                    hits.append((i + 1, line.rstrip(), classify(line, q)))
            if hits:
                findings[qname][str(f)] = hits
        # constants anywhere, comments included: a literal in a comment still tells us something
        for i, line in enumerate(lines):
            # longest constant first, and one hit per line: '1997.36' and '1997.'
            # both match the same text and would otherwise be counted twice.
            for c in sorted(CONSTANTS, key=len, reverse=True):
                if c in line:
                    key = (str(f), i + 1)
                    if key not in seen_const:
                        seen_const.add(key)
                        const_hits.setdefault(CONSTANTS[c], []).append(
                            (str(f), i + 1, line.strip()[:110]))
                    break

    # ---- ranking: the file with the most Q1 hits is where the geometry lives
    print("=" * 78)
    print("FILES BY RELEVANCE (Q1 hits = where the geometry is defined)")
    print("=" * 78)
    score = {}
    for qname in QUESTIONS:
        for f, hits in findings[qname].items():
            score.setdefault(f, {})[qname] = len(hits)
    for f, s in sorted(score.items(), key=lambda kv: -kv[1].get("Q1_box_and_dx", 0))[:15]:
        print(f"  Q1={s.get('Q1_box_and_dx',0):>3}  Q2={s.get('Q2_sigma_px',0):>3}"
              f"  Q3={s.get('Q3_mask',0):>3}   {f}")

    if args.files_first:
        return 0

    for qname, q in QUESTIONS.items():
        print("\n" + "=" * 78)
        print(f"{qname}  --  {q['title']}")
        print("=" * 78)
        ranked = sorted(findings[qname].items(), key=lambda kv: -len(kv[1]))
        for f, hits in ranked[:4]:
            print(f"\n--- {f}")
            try:
                lines = Path(f).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            shown = 0
            for ln, text, cls in hits:
                if shown >= args.max_hits:
                    print(f"      ... {len(hits)-shown} more hits in this file")
                    break
                print(f"  [{cls}] {ln}:")
                lo, hi = max(0, ln - 1 - args.context), min(len(lines), ln + args.context)
                for k in range(lo, hi):
                    pref = ">>" if k == ln - 1 else "  "
                    print(f"     {pref} {k+1:>5} | {lines[k].rstrip()[:118]}")
                shown += 1

    print("\n" + "=" * 78)
    print("FROZEN CONSTANTS APPEARING AS LITERALS IN THE SOURCE")
    print("=" * 78)
    if not const_hits:
        print("  none found -- consistent with everything being derived at runtime")
    for what, hits in sorted(const_hits.items()):
        print(f"\n  {what}  ({len(hits)} occurrence(s))")
        for f, ln, text in hits[:6]:
            print(f"     {f}:{ln}  {text}")
        if len(hits) > 6:
            print(f"     ... {len(hits)-6} more")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"findings": {k: {f: v for f, v in d.items()} for k, d in findings.items()},
             "constants": const_hits}, indent=2), encoding="utf-8")
        print(f"\nwritten to {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

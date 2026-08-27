#!/usr/bin/env python3
"""
paper2_provenance_audit.py  --  close the three provenance ambiguities left by
the ensemble v1 freeze, and locate the canonical 2000-mock record.

  A  Two byte-identical CSVs with contradictory names:
       results/phase8_test2_permock.csv        (restored from git)
       results/phase8_test2_permock_hodfit.csv (never tracked)
     One of the two names is wrong. Decided by the numbers: mean ~35305 with
     sd ~1033 is the HOD refit (M26 Table 1, N=200); mean ~35437 with sd ~313
     is the baseline.

  B  Four erosion records, the older ones LARGER than the newer ones:
       paper1_erosion_{NGC,SGC}_restrict.json      26 Jul
       paper1_erosion_{NGC,SGC}_restrict_bak.json  24 Jul
     The 24->26 Jul window is when the ladder excursion was corrected from
     2.0/2.7 to 6.8/9.8 percentage points. Which file backs Paper 1 Tables
     9-10 must be known before Component C re-runs the ladder on v2.

  D  Six *_manifest.json files byte-identical at 30890 bytes, plus
     phase_r51_manifest_v3.json identical to its base. Benign if they list the
     same 2000 simulations; a copy-paste defect if each was meant to differ.

  E  (bonus) Where does the canonical 2000-mock ensemble live? Gate 2.1 has to
     reproduce 35436.7 +/- 313.0, and needs to know which file to ask.

Read-only. Prints a report; writes JSON with --json.

Usage, from D:\\projects\\cauchy :

    python src\\paper2_provenance_audit.py
    python src\\paper2_provenance_audit.py --json results\\paper2\\provenance_audit.json
"""

from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

# Frozen signatures the audit compares against (M26 R1 + Paper 1).
SIGNATURES = [
    ("baseline v1, N=2000",      35436.7, 313.0, 2000),
    ("HOD refit to w_p + nbar",  35305.0, 1033.0, 200),
    ("concentrated HOD",         35048.0, 1220.0, 30),
    ("fixed-cosmology ensemble", None,    172.0, 200),
    ("SGC baseline, N=2000",     18713.0, 197.8, 2000),
    ("SGC baseline, N=200",      18694.0, 178.0, 200),
]
DESI = {"NGC": 28256, "SGC": 15122}

# Paper 1 Tables 9-10, for section B.
LADDER = {
    "NGC": {0: 0.202, 1: 0.254, 2: 0.206, 3: 0.186, "excursion_pp": 6.8},
    "SGC": {0: 0.191, 1: 0.271, 2: 0.200, 3: 0.173, "excursion_pp": 9.8},
}
RETRACTED_EXCURSION = (2.0, 2.7)


def rule(t=""):
    print("\n" + "=" * 78)
    if t:
        print(t)
        print("=" * 78)


def read_text(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ------------------------------------------------------------------ section A

def section_a(root: Path, out: dict) -> None:
    rule("A  --  the two byte-identical CSVs")
    paths = [root / "results" / "phase8_test2_permock.csv",
             root / "results" / "phase8_test2_permock_hodfit.csv"]
    for p in paths:
        if not p.exists():
            print(f"  MISSING: {p}")
            continue
        txt = read_text(p)
        if txt is None:
            continue
        lines = [l for l in txt.splitlines() if l.strip()]
        header = lines[0] if lines else ""
        cols = [c.strip() for c in header.split(",")]
        print(f"\n--- {p.name}   {p.stat().st_size:,} bytes, {len(lines)-1} data rows")
        print(f"    columns: {cols}")
        for l in lines[1:4]:
            print(f"    | {l[:110]}")

        # numeric summary of every column that parses
        data: dict[str, list[float]] = {c: [] for c in cols}
        for l in lines[1:]:
            parts = l.split(",")
            for c, v in zip(cols, parts):
                try:
                    data[c].append(float(v))
                except ValueError:
                    pass
        print(f"\n    {'column':<24}{'n':>7}{'mean':>13}{'sd':>11}{'min':>11}{'max':>11}")
        summary = {}
        for c, v in data.items():
            if len(v) < 3:
                continue
            m, s = st.mean(v), st.stdev(v)
            summary[c] = {"n": len(v), "mean": m, "sd": s, "min": min(v), "max": max(v)}
            print(f"    {c:<24}{len(v):>7}{m:>13.2f}{s:>11.2f}{min(v):>11.2f}{max(v):>11.2f}")

        # match against the frozen signatures
        print("\n    match against frozen signatures:")
        best = None
        for c, s in summary.items():
            if not (1e4 < s["mean"] < 1e5):
                continue
            for name, mu, sd, n in SIGNATURES:
                if mu is None:
                    continue
                dm = abs(s["mean"] - mu) / mu
                ds = abs(s["sd"] - sd) / sd
                score = dm + 0.5 * ds
                if dm < 0.03 and ds < 0.6:
                    print(f"      column '{c}' ~ {name}"
                          f"   (mean off {100*dm:.2f}%, sd off {100*ds:.0f}%)")
                    if best is None or score < best[0]:
                        best = (score, name, c)
        if best:
            print(f"      >>> BEST: {best[1]}  (via column '{best[2]}')")
        else:
            print("      no signature matched; read the numbers above by hand")
        out.setdefault("A", {})[p.name] = {
            "bytes": p.stat().st_size, "rows": len(lines) - 1,
            "columns": cols, "summary": summary,
            "best_match": best[1] if best else None,
        }


# ------------------------------------------------------------------ section B

def flatten(o, prefix="") -> dict:
    """Flatten nested dicts/lists to dotted paths, keeping scalars."""
    flat = {}
    if isinstance(o, dict):
        for k, v in o.items():
            flat.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(o, list):
        if o and all(isinstance(x, (int, float)) for x in o):
            flat[prefix] = o
        else:
            for i, v in enumerate(o[:12]):
                flat.update(flatten(v, f"{prefix}[{i}]"))
    else:
        flat[prefix] = o
    return flat


def section_b(root: Path, out: dict) -> None:
    rule("B  --  the erosion records: which one backs Paper 1 Tables 9-10?")
    for cap in ("NGC", "SGC"):
        cur = root / "results" / "paper1" / f"paper1_erosion_{cap}_restrict.json"
        bak = root / "results" / "paper1" / f"paper1_erosion_{cap}_restrict_bak.json"
        print(f"\n--- {cap}")
        docs = {}
        for tag, p in (("current", cur), ("bak", bak)):
            if not p.exists():
                print(f"    MISSING: {p}")
                continue
            try:
                docs[tag] = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError as e:
                print(f"    UNPARSEABLE {p.name}: {e}")
        if len(docs) < 2:
            continue

        fa, fb = flatten(docs["current"]), flatten(docs["bak"])
        only_cur = sorted(set(fa) - set(fb))
        only_bak = sorted(set(fb) - set(fa))
        both_diff = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])

        print(f"    keys: current {len(fa)}, bak {len(fb)}")
        if only_bak:
            print(f"    only in BAK ({len(only_bak)}):     {', '.join(only_bak[:10])}"
                  + (" ..." if len(only_bak) > 10 else ""))
        if only_cur:
            print(f"    only in CURRENT ({len(only_cur)}): {', '.join(only_cur[:10])}"
                  + (" ..." if len(only_cur) > 10 else ""))
        if both_diff:
            print(f"    differing values ({len(both_diff)}):")
            for k in both_diff[:18]:
                va, vb = fa[k], fb[k]
                sa = f"{va:.6g}" if isinstance(va, float) else str(va)[:44]
                sb = f"{vb:.6g}" if isinstance(vb, float) else str(vb)[:44]
                print(f"      {k:<44} current={sa:<20} bak={sb}")
            if len(both_diff) > 18:
                print(f"      ... {len(both_diff)-18} more")

        # which one reproduces the published ladder?
        print(f"\n    published ladder {cap} (Paper 1 Tab. 9-10): "
              + ", ".join(f"k{k}={100*v:.1f}%" for k, v in LADDER[cap].items()
                          if isinstance(k, int))
              + f", excursion {LADDER[cap]['excursion_pp']} pp")
        for tag, doc in docs.items():
            f = flatten(doc)
            hits = []
            for k, v in f.items():
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                for kk, target in LADDER[cap].items():
                    if not isinstance(kk, int):
                        continue
                    if abs(v - target) < 0.003 or abs(v - 100 * target) < 0.3:
                        hits.append(f"k{kk}~{k}")
            exc = [f"{k}={v:.3g}" for k, v in f.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)
                   and (abs(v - LADDER[cap]["excursion_pp"]) < 0.4
                        or any(abs(v - r) < 0.3 for r in RETRACTED_EXCURSION))]
            print(f"      {tag:<8} ladder matches: {', '.join(hits[:6]) or 'none'}")
            print(f"      {'':8} excursion-like values: {', '.join(exc[:6]) or 'none'}")
        out.setdefault("B", {})[cap] = {
            "only_bak": only_bak, "only_current": only_cur,
            "n_differing": len(both_diff),
        }


# ------------------------------------------------------------------ section C

IDENTICAL_MANIFESTS = [
    "phase5_hod_b3_manifest.json", "phase6_mock_manifest_z05.json",
    "phase6_mock_manifest_z05_R10.json", "phase_b3_cal135_manifest.json",
    "phase_b3_cal135_v2_manifest.json", "phase_oc1_pk_hod_manifest.json",
    "phase_r51_manifest.json", "phase_r51_manifest_v3.json",
]


def describe(o, depth=0):
    """Structure of a document with long lists collapsed.

    Scalars are kept in full: they are what would have to differ between runs
    that the manifests are supposed to describe separately.
    """
    if depth > 3:
        return "<deeper>"
    if isinstance(o, dict):
        return {k: describe(v, depth + 1) for k, v in list(o.items())[:40]}
    if isinstance(o, list):
        if not o:
            return "list[0]"
        if all(isinstance(x, (str, int, float, bool)) for x in o):
            return {"list_len": len(o), "first": o[0], "last": o[-1],
                    "n_unique": len(set(map(str, o)))}
        return {"list_len": len(o), "first_item": describe(o[0], depth + 1)}
    return o


def section_c(root: Path, out: dict) -> None:
    rule("C  --  the identical *_manifest.json files")
    for name in IDENTICAL_MANIFESTS:
        p = root / "results" / name
        if not p.exists():
            print(f"  MISSING: {name}")
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            print(f"  UNPARSEABLE: {name}")
            continue
        print(f"\n--- {name}   {p.stat().st_size:,} bytes")
        if isinstance(d, dict):
            print(f"    dict, {len(d)} keys: {', '.join(list(d)[:10])}")
            for k, v in list(d.items())[:6]:
                if isinstance(v, list):
                    print(f"      {k}: list[{len(v)}], first = {str(v[0])[:70] if v else '-'}")
                elif isinstance(v, dict):
                    print(f"      {k}: dict[{len(v)}], keys = {list(v)[:6]}")
                else:
                    print(f"      {k}: {str(v)[:80]}")
        elif isinstance(d, list):
            print(f"    list[{len(d)}], first = {str(d[0])[:90] if d else '-'}")
        out.setdefault("C", {})[name] = {"bytes": p.stat().st_size,
                                         "structure": describe(d)}
    print("\n  Reading: if these list the SAME 2000 simulation inputs, being identical")
    print("  is correct and expected. If any was meant to describe a different run")
    print("  (different HOD, different smoothing), it was copied and not regenerated.")


# ------------------------------------------------------------------ section E

def numeric_series(obj):
    """Yield (path, list-of-numbers) for every numeric list found."""
    def walk(o, prefix=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
        elif isinstance(o, list):
            nums = [x for x in o if isinstance(x, (int, float))
                    and not isinstance(x, bool)]
            if len(nums) >= 30 and len(nums) >= 0.9 * len(o):
                yield prefix, nums
            else:
                for i, v in enumerate(o[:3]):
                    yield from walk(v, f"{prefix}[{i}]")
    yield from walk(obj)


def section_e(root: Path, out: dict) -> None:
    rule("E  --  where does the canonical ensemble live? (prerequisite for gate 2.1)")
    cands = []
    files = list((root / "results").glob("*.json")) + \
            list((root / "results").glob("*.jsonl")) + \
            list((root / "results" / "paper1").glob("*.json")) + \
            list((root / "results" / "paper1").glob("*.jsonl"))
    for p in sorted(files):
        txt = read_text(p)
        if txt is None:
            continue
        series: list[tuple[str, list]] = []
        if p.suffix == ".jsonl":
            recs = []
            for l in txt.splitlines():
                l = l.strip()
                if not l:
                    continue
                try:
                    recs.append(json.loads(l))
                except json.JSONDecodeError:
                    pass
            if recs and isinstance(recs[0], dict):
                # Flatten one level of nesting: per_mock_*.jsonl stores the
                # measurement under base/remap/null, not at the top level, and
                # the first version of this probe missed it entirely.
                def leaves(rec, pref=""):
                    for k, v in rec.items():
                        p2 = f"{pref}.{k}" if pref else k
                        if isinstance(v, dict):
                            yield from leaves(v, p2)
                        elif isinstance(v, (int, float)) and not isinstance(v, bool):
                            yield p2, v
                keys = [k for k, _ in leaves(recs[0])]
                for k in keys:
                    vals = [v for r in recs for kk, v in leaves(r) if kk == k]
                    if len(vals) >= 30:
                        series.append((k, vals))
        else:
            try:
                series = list(numeric_series(json.loads(txt)))
            except json.JSONDecodeError:
                continue
        for key, vals in series:
            v = [x for x in vals if 1e4 < x < 2e5]
            if len(v) < 30:
                continue
            m, s = st.mean(v), st.stdev(v)
            for name, mu, sd, n in SIGNATURES:
                if mu is None:
                    continue
                if abs(m - mu) / mu < 0.01 and abs(s - sd) / sd < 0.35:
                    cap = "SGC" if mu < 25000 else "NGC"
                    below = sum(1 for x in v if x < DESI[cap])
                    cands.append((p, key, len(v), m, s, min(v), name, cap, below))
    if not cands:
        print("  no series matched a frozen signature -- widen the search or check by hand")
    for p, key, n, m, s, mn, name, cap, below in sorted(cands, key=lambda c: -c[2]):
        rel = p.relative_to(root).as_posix()
        print(f"\n  {rel}   field '{key}'")
        print(f"     n={n}  mean={m:.1f}  sd={s:.1f}  min={mn:.0f}")
        print(f"     matches: {name}")
        print(f"     DESI {cap} = {DESI[cap]}: {below} of {n} mocks below"
              f"  -> rank {below+1}/{n+1}")
    out["E"] = [{"file": p.relative_to(root).as_posix(), "field": k, "n": n,
                 "mean": m, "sd": s, "min": mn, "match": nm, "cap": cap,
                 "n_below_desi": b}
                for p, k, n, m, s, mn, nm, cap, b in cands]


def main() -> int:
    ap = argparse.ArgumentParser(description="Close the v1 provenance ambiguities.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", default=None)
    ap.add_argument("--only", nargs="*", choices=list("ABCE"),
                    help="run only these sections")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out: dict = {}
    todo = args.only or list("ABCE")
    if "A" in todo: section_a(root, out)
    if "B" in todo: section_b(root, out)
    if "C" in todo: section_c(root, out)
    if "E" in todo: section_e(root, out)
    rule("done")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        print(f"written to {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

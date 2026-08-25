#!/usr/bin/env python3
"""
paper2_inspect_results.py  --  Paper 2, checklist item 0.1, probe step.

Reads NOTHING in bulk. For each top-level directory under the given root it
samples a couple of files and reports what is actually inside them: npz keys,
array shapes and dtypes, JSON top-level keys, JSONL first-record keys.

The question it answers: which directories hold the v1 mock delta/nu FIELDS
(and therefore must be frozen), which hold summary records (cheap, freeze
them too), and which belong to Branch B or to superseded phases (exclude).

Usage, from D:\\projects\\cauchy :

    python src\\paper2_inspect_results.py --root results

    # more samples per directory, and go two levels deep
    python src\\paper2_inspect_results.py --root results --samples 3 --depth 2

Writes results/paper2/results_inventory.json alongside the printed report,
unless --no-write is given.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

FIELD_EXT = {".npz", ".npy"}
REC_EXT = {".json", ".jsonl", ".csv", ".txt", ".md"}
SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", ".venv", "paper2"}

# A 128^3 float32 array is exactly 8 MiB; 256^3 is 64 MiB. Recognising these
# on sight is the whole point of the probe.
KNOWN_SHAPES = {
    (128, 128, 128): "128^3 grid  <-- analysis grid of M26 / Paper 1",
    (256, 256, 256): "256^3 grid  <-- resolution test of Paper 1 sec.8.3",
    (64, 64, 64): "64^3 grid",
}


def human(n: float) -> str:
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PiB"


def peek_npz(p: Path) -> list[str]:
    try:
        import numpy as np
    except ImportError:
        return ["numpy not available"]
    out = []
    try:
        with np.load(p, allow_pickle=False, mmap_mode=None) as z:
            for k in list(z.files)[:6]:
                a = z[k]
                shp = tuple(a.shape)
                note = KNOWN_SHAPES.get(shp, "")
                out.append(f"{k}: {shp} {a.dtype}" + (f"   {note}" if note else ""))
            if len(z.files) > 6:
                out.append(f"... {len(z.files)-6} more keys")
    except Exception as e:
        out.append(f"<unreadable: {type(e).__name__}: {e}>")
    return out


def peek_npy(p: Path) -> list[str]:
    try:
        import numpy as np
        a = np.load(p, allow_pickle=False, mmap_mode="r")
        shp = tuple(a.shape)
        return [f"array: {shp} {a.dtype}" + (f"   {KNOWN_SHAPES.get(shp,'')}")]
    except Exception as e:
        return [f"<unreadable: {type(e).__name__}: {e}>"]


def peek_json(p: Path) -> list[str]:
    try:
        d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return [f"<unparseable: {type(e).__name__}>"]
    if isinstance(d, dict):
        ks = list(d.keys())
        return [f"dict, {len(ks)} keys: " + ", ".join(map(str, ks[:12]))
                + (" ..." if len(ks) > 12 else "")]
    if isinstance(d, list):
        head = d[0] if d else None
        if isinstance(head, dict):
            return [f"list[{len(d)}], first-record keys: "
                    + ", ".join(map(str, list(head.keys())[:12]))]
        return [f"list[{len(d)}] of {type(head).__name__}"]
    return [f"{type(d).__name__}"]


def peek_jsonl(p: Path) -> list[str]:
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip()
            n = 1 + sum(1 for _ in fh)
    except Exception as e:
        return [f"<unreadable: {type(e).__name__}>"]
    try:
        rec = json.loads(first)
        ks = ", ".join(map(str, list(rec.keys())[:12])) if isinstance(rec, dict) else "?"
    except Exception:
        ks = "<first line unparseable>"
    return [f"{n} records; first-record keys: {ks}"]


def peek(p: Path) -> list[str]:
    s = p.suffix.lower()
    if s == ".npz":
        return peek_npz(p)
    if s == ".npy":
        return peek_npy(p)
    if s == ".json":
        return peek_json(p)
    if s == ".jsonl":
        return peek_jsonl(p)
    if s in (".txt", ".md", ".csv"):
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:160]
            return [repr(head.replace("\n", " ")[:150])]
        except Exception:
            return ["<unreadable>"]
    return [f"({s} not sampled)"]


def classify(n_files: int, total: int, exts: set[str], name: str,
             peeked: list[str] | None = None) -> str:
    """First guess, ordered by reliability of the evidence.

    Array SHAPE beats file size: a compressed field of a nearly-empty grid can
    be small, and a directory of summary records can be large if there are many
    of them. Shape is what says "this is a 128^3 field".
    """
    lname = name.lower()
    avg = total / max(n_files, 1)
    blob = " ".join(peeked or [])

    if "tau_field" in lname or "phase7" in lname or "graph" in lname:
        return "BRANCH B?  (GNN / tension field) -> probably EXCLUDE"
    if "(128, 128, 128)" in blob or "(256, 256, 256)" in blob:
        return "FIELD CACHE (grid-shaped arrays seen) -> Tier B"
    if "diagram" in lname or "persistence" in lname:
        return "PERSISTENCE DIAGRAMS -> Tier B if like-for-like, EXCLUDE if superseded"
    if exts & FIELD_EXT and avg < 64 * 1024:
        return "small .npz = summary records, NOT fields -> Tier A"
    if exts & FIELD_EXT and avg > 4 * 1024**2:
        return "large binaries, shape unread -> inspect"
    if exts & REC_EXT and not (exts & FIELD_EXT):
        return "RECORDS -> Tier A (freeze, instant)"
    return "mixed -> inspect"


def main() -> int:
    ap = argparse.ArgumentParser(description="Inventory the results tree (Paper 2 item 0.1).")
    ap.add_argument("--root", default="results")
    ap.add_argument("--samples", type=int, default=2, help="files sampled per directory")
    ap.add_argument("--depth", type=int, default=1, help="1 = top-level dirs, 2 = one level deeper")
    ap.add_argument("--out", default=None, help="where to write the JSON inventory")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        sys.stderr.write(f"root not found: {root}\n")
        return 2

    # group files by directory, truncated to --depth components below root
    groups: dict[str, dict] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel = Path(dirpath).resolve().relative_to(root)
        parts = rel.parts
        key = "/".join(parts[: args.depth]) if parts else "."
        g = groups.setdefault(key, {"n": 0, "bytes": 0, "exts": set(),
                                    "samples": [], "names": []})
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            try:
                sz = p.stat().st_size
            except OSError:
                continue
            g["n"] += 1
            g["bytes"] += sz
            g["exts"].add(p.suffix.lower())
            if len(g["names"]) < 2:
                g["names"].append(fn)
            g["last"] = fn
            if len(g["samples"]) < args.samples and p.suffix.lower() in (FIELD_EXT | REC_EXT):
                g["samples"].append(p)

    print(f"\nINVENTORY OF {root}\n" + "=" * 78)
    inventory = {}
    for key, g in sorted(groups.items(), key=lambda kv: -kv[1]["bytes"]):
        if g["n"] == 0:
            continue
        avg = g["bytes"] / g["n"]
        peeked: list[tuple[str, list[str]]] = []
        for sp in g["samples"]:
            try:
                srel = sp.relative_to(root).as_posix()
            except ValueError:
                srel = sp.name
            peeked.append((srel, peek(sp)))
        flat = [ln for _, lines in peeked for ln in lines]
        guess = classify(g["n"], g["bytes"], g["exts"], key, flat)
        print(f"\n{key or '.'}")
        print(f"  {g['n']} files, {human(g['bytes'])}, avg {human(avg)}"
              f"   ext: {', '.join(sorted(e for e in g['exts'] if e))}")
        print(f"  names: {g['names'][0] if g['names'] else '-'}"
              f" ... {g.get('last','-')}")
        print(f"  GUESS: {guess}")
        for (srel, lines), sp in zip(peeked, g["samples"]):
            print(f"  -- {srel}  ({human(sp.stat().st_size)})")
            for line in lines:
                print(f"       {line}")
        inventory[key] = {
            "n_files": g["n"], "bytes": g["bytes"], "avg_bytes": avg,
            "ext": sorted(e for e in g["exts"] if e),
            "first_name": g["names"][0] if g["names"] else None,
            "last_name": g.get("last"),
            "guess": guess,
            "sample_peek": {srel: lines for srel, lines in peeked},
        }

    tot_n = sum(v["n_files"] for v in inventory.values())
    tot_b = sum(v["bytes"] for v in inventory.values())
    print("\n" + "=" * 78)
    print(f"TOTAL {tot_n} files, {human(tot_b)}")

    if not args.no_write:
        out = Path(args.out) if args.out else root / "paper2" / "results_inventory.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, out)
        print(f"inventory written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

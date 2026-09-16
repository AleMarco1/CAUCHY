#!/usr/bin/env python3
"""
find_fig1_source.py — CAUCHY / MN-26-2100-P

Locates the frozen record and the script behind Figure 1 and Table B1
of the MNRAS manuscript (sigma_px sensitivity of <pers_1>).

Target values, read directly from the vector data of the accepted proof:

    sigma_px   mean     std
    0.216      0.106    0.005
    0.640      0.238    0.019
    1.280      0.394    0.015

The manuscript text instead quotes delta = +0.153 and +8.42 sigma, which
match phase6_sigma_px_test.json exactly (means 0.30318 / 0.15017 / 0.08363).
This script finds every file that could have produced either family.

Usage:
    python find_fig1_source.py                 # scans D:\\projects\\cauchy
    python find_fig1_source.py <root>          # scans <root>

Read-only: it never writes or modifies anything.
"""

import json
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"D:\projects\cauchy"

TEXT_EXT = {".py", ".json", ".tex", ".md", ".txt", ".csv", ".ipynb", ".log"}
SKIP_DIR = {".git", "__pycache__", "node_modules", ".ipynb_checkpoints",
            "venv", ".venv", "env", "site-packages"}
MAX_BYTES = 20 * 1024 * 1024        # skip anything larger

# values plotted in Figure 1 / printed in Table B1
NEW = [0.106, 0.238, 0.394]
NEW_STD = [0.005, 0.019, 0.015]
# values in phase6_sigma_px_test.json, which the manuscript text quotes
OLD = [0.30318, 0.15017, 0.08363]

TOKENS = ["sigma_px", "sigma-px", "0.216", "1.6875", "8.42", "8.415",
          "0.1530", "0.153", "b2_mean_persistence", "pers1", "pers_1"]

hits_new, hits_old, hits_token, hits_fig = [], [], [], []


def near(x, target, rel=0.02):
    """True if x matches target to within rel (default 2%)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return False
    return abs(x - target) <= rel * abs(target)


def walk_json(node, out):
    """Collect every numeric leaf in a parsed JSON tree."""
    if isinstance(node, dict):
        for v in node.values():
            walk_json(v, out)
    elif isinstance(node, list):
        for v in node:
            walk_json(v, out)
    elif isinstance(node, (int, float)):
        out.append(node)


def scan_json(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:
        return
    nums = []
    walk_json(data, nums)
    if not nums:
        return
    n_new = sum(any(near(v, t) for v in nums) for t in NEW)
    n_std = sum(any(near(v, t, rel=0.05) for v in nums) for t in NEW_STD)
    n_old = sum(any(near(v, t) for v in nums) for t in OLD)
    if n_new >= 2:
        hits_new.append((path, n_new, n_std))
    if n_old >= 2:
        hits_old.append((path, n_old))


def scan_text(path, ext):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            src = f.read()
    except Exception:
        return
    found = [t for t in TOKENS if t in src]
    if found:
        hits_token.append((path, found))
    if ext == ".py" and "savefig" in src:
        low = src.lower()
        if "sigma_px" in low or "smoothing" in low or "\\sigma_{\\rm px}" in src:
            hits_fig.append(path)
    if ext == ".tex":
        for m in re.finditer(r"\\includegraphics[^{]*\{([^}]+)\}", src):
            hits_fig.append(f"{path}  ->  \\includegraphics{{{m.group(1)}}}")


def main():
    if not os.path.isdir(ROOT):
        print(f"[ERROR] root not found: {ROOT}")
        sys.exit(1)

    print(f"scanning {os.path.abspath(ROOT)}\n")
    n = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT:
                continue
            path = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
            except OSError:
                continue
            n += 1
            if ext == ".json":
                scan_json(path)
            scan_text(path, ext)

    rel = lambda p: os.path.relpath(p, ROOT)

    print(f"{n} files inspected\n")

    print("=" * 72)
    print("A. RECORDS CARRYING THE FIGURE 1 / TABLE B1 VALUES  (0.106 / 0.238 / 0.394)")
    print("=" * 72)
    if hits_new:
        for p, k, s in sorted(hits_new, key=lambda t: -t[1]):
            print(f"  [{k}/3 means, {s}/3 stds]  {rel(p)}")
    else:
        print("  none — the figure was probably drawn from an unsaved computation,")
        print("  or from an .npz/.npy array rather than a JSON record.")

    print("\n" + "=" * 72)
    print("B. RECORDS CARRYING THE TEXT VALUES  (0.30318 / 0.15017 / 0.08363)")
    print("=" * 72)
    for p, k in sorted(hits_old, key=lambda t: -t[1]) or [("(none)", 0)]:
        print(f"  [{k}/3 means]  {rel(p) if p != '(none)' else p}")

    print("\n" + "=" * 72)
    print("C. FIGURE GENERATORS AND \\includegraphics TARGETS")
    print("=" * 72)
    for p in sorted(set(hits_fig)):
        print("  " + (rel(p) if os.path.exists(p.split("  ->")[0]) else p))

    print("\n" + "=" * 72)
    print("D. FILES MENTIONING sigma_px / 0.216 / 8.42 / 0.153")
    print("=" * 72)
    for p, found in sorted(hits_token):
        print(f"  {rel(p)}\n      {', '.join(found)}")


if __name__ == "__main__":
    main()

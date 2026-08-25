#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_pipeline_code.py
---------------------
Step 1 / slot [C1]-[C2] del Paper 1.

Trova AUTOMATICAMENTE, dentro il progetto CAUCHY, il codice che definisce:
  * la trasformazione  delta -> nu  (log-transform, smoothing, standardizzazione)
  * la filtrazione / omologia persistente (GUDHI, cubical complex, Betti)
  * il calcolo di beta1max

e produce:
  1) pipeline_code_report.json  -> classifica dei file per rilevanza, con
                                   keyword trovate, funzioni/classi e n. di riga
  2) pipeline_code_bundle.md    -> il SORGENTE COMPLETO dei file migliori,
                                   concatenato in un unico file da caricare
  3) (bonus) elenco dei .json in results/ che contengono chiavi tipo
     beta1 / b1_max / betti  -> serve a chiudere lo slot [C2]

Solo standard library. Non modifica nulla: apre i file in sola lettura.

USO (Windows):
    python find_pipeline_code.py

Opzioni:
    python find_pipeline_code.py --root "D:\\projects\\cauchy" --top 8
"""

import argparse
import io
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
DEFAULT_ROOT = r"D:\projects\cauchy"
DEFAULT_TOP = 8                     # quanti file finiscono nel bundle
MAX_FILE_BYTES = 400_000            # non bundlare file .py enormi
MAX_BUNDLE_BYTES = 2_000_000        # tetto totale del bundle
MAX_SCAN_BYTES = 2_000_000          # non leggere .py oltre questa soglia

SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".ipynb_checkpoints",
    "node_modules", ".venv", "venv", "env", ".env", "site-packages",
    ".mypy_cache", ".pytest_cache", ".tox", "dist", "build", ".idea", ".vscode",
}

# Keyword pesate. Il punteggio guida la classifica.
KEYWORDS = {
    # --- decisive: omologia persistente ---
    "gudhi": 12,
    "cubicalcomplex": 12,
    "cubical_complex": 12,
    "persistence": 10,
    "persistence_intervals": 10,
    "betti": 10,
    "b1_max": 10,
    "beta1max": 10,
    "beta1_max": 10,
    "b1max": 10,
    "persistence_diagram": 8,
    "ripser": 8,
    "top_dimensional_cells": 8,
    # --- decisive: costruzione del campo nu ---
    "log1p": 8,
    "np.log(1": 8,
    "log_transform": 8,
    "gaussian_filter": 8,
    "sigma_px": 8,
    "smoothing": 6,
    "smooth": 4,
    "standardize": 6,
    "standardis": 6,
    "nu_field": 8,
    "filtration": 8,
    "superlevel": 8,
    "sublevel": 8,
    # --- contesto ---
    "voxel": 3,
    "mask": 3,
    "carve": 4,
    "cut_sky": 4,
    "cutsky": 4,
    "delta_128": 4,
    "field_prep": 5,
    "phase1": 3,
    "phase6": 3,
    "fvec": 4,
    "feature_vector": 4,
}

# Nomi di funzione/classe che vogliamo estrarre esplicitamente
DEF_RE = re.compile(r"^\s*(?:def|class)\s+([A-Za-z_]\w*)", re.M)

INTERESTING_DEF_HINTS = (
    "nu", "field", "smooth", "log", "filtr", "persist", "betti", "b1",
    "topol", "prep", "mask", "carve", "standard", "feature", "fvec",
)

# chiavi cercate nei json di results per lo slot [C2]
JSON_C2_KEYS = ("b1_max", "beta1", "b1max", "betti", "beta_1", "b1 ")


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def read_text(path, limit=MAX_SCAN_BYTES):
    """Legge un file di testo in modo tollerante agli encoding."""
    try:
        with open(path, "rb") as f:
            raw = f.read(limit)
    except OSError:
        return None
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f}{u}" if u == "B" else f"{n:.1f}{u}"
        n /= 1024.0


def score_source(text):
    """Punteggio di rilevanza + dettaglio delle keyword trovate."""
    low = text.lower()
    score = 0
    hits = {}
    for kw, w in KEYWORDS.items():
        c = low.count(kw)
        if c:
            # saturazione: 3 occorrenze valgono quanto molte di piu'
            eff = min(c, 3)
            score += w * eff
            hits[kw] = c
    return score, hits


def find_defs(text):
    """Estrae nomi di funzioni/classi con il numero di riga."""
    out = []
    for m in DEF_RE.finditer(text):
        name = m.group(1)
        line = text.count("\n", 0, m.start()) + 1
        out.append({"name": name, "line": line})
    return out


def interesting_defs(defs):
    return [d for d in defs
            if any(h in d["name"].lower() for h in INTERESTING_DEF_HINTS)]


def keyword_context(text, max_snippets=6):
    """Righe di codice attorno alle keyword piu' decisive (per il report)."""
    lines = text.splitlines()
    low_lines = [l.lower() for l in lines]
    decisive = ("gudhi", "cubical", "persistence", "betti", "gaussian_filter",
                "log1p", "superlevel", "sublevel", "sigma_px", "filtration")
    snips = []
    for i, ll in enumerate(low_lines):
        if any(d in ll for d in decisive):
            snips.append({"line": i + 1, "code": lines[i].strip()[:200]})
            if len(snips) >= max_snippets:
                break
    return snips


# ---------------------------------------------------------------------------
# Scansione principale
# ---------------------------------------------------------------------------
def scan_python(root):
    results = []
    n_seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if not (fn.endswith(".py") or fn.endswith(".ipynb")):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(fp)
            except OSError:
                continue
            n_seen += 1
            text = read_text(fp)
            if text is None:
                continue
            score, hits = score_source(text)
            if score <= 0:
                continue
            defs = find_defs(text)
            results.append({
                "path": fp,
                "rel": os.path.relpath(fp, root).replace("\\", "/"),
                "size_bytes": size,
                "size_h": human(size),
                "score": score,
                "keyword_hits": dict(sorted(hits.items(), key=lambda x: -x[1])),
                "n_defs": len(defs),
                "defs_interesting": interesting_defs(defs)[:25],
                "context": keyword_context(text),
            })
    results.sort(key=lambda r: -r["score"])
    return results, n_seen


def scan_results_json(root):
    """Bonus [C2]: json in results/ che sembrano contenere valori di Betti."""
    out = []
    rdir = os.path.join(root, "results")
    if not os.path.isdir(rdir):
        return out
    for dirpath, dirnames, filenames in os.walk(rdir):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(fp) > 20_000_000:
                    continue
            except OSError:
                continue
            text = read_text(fp, limit=1_000_000)
            if not text:
                continue
            low = text.lower()
            found = [k.strip() for k in JSON_C2_KEYS if k in low]
            if not found:
                continue
            # prova a estrarre le chiavi di primo livello e i numeri plausibili
            preview_keys, numbers = [], {}
            try:
                d = json.loads(text)
                if isinstance(d, dict):
                    preview_keys = list(d.keys())[:30]

                    def crawl(o, prefix="", depth=0):
                        if depth > 3 or len(numbers) > 25:
                            return
                        if isinstance(o, dict):
                            for k, v in o.items():
                                kl = str(k).lower()
                                p = f"{prefix}.{k}" if prefix else str(k)
                                if isinstance(v, (int, float)) and any(
                                        t in kl for t in ("b1", "beta1", "betti", "deficit", "max")):
                                    numbers[p] = v
                                elif isinstance(v, (dict, list)):
                                    crawl(v, p, depth + 1)
                    crawl(d)
            except Exception:  # noqa: BLE001
                pass
            out.append({
                "path": fp,
                "rel": os.path.relpath(fp, root).replace("\\", "/"),
                "size_h": human(os.path.getsize(fp)),
                "matched_terms": found,
                "top_level_keys": preview_keys,
                "candidate_numbers": numbers,
            })
    # i piu' promettenti prima: chi ha numeri estratti
    out.sort(key=lambda r: (-len(r["candidate_numbers"]), -len(r["matched_terms"])))
    return out


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------
def write_bundle(results, root, top, out_path):
    chosen, total = [], 0
    for r in results:
        if len(chosen) >= top:
            break
        if r["size_bytes"] > MAX_FILE_BYTES:
            continue
        if total + r["size_bytes"] > MAX_BUNDLE_BYTES:
            continue
        chosen.append(r)
        total += r["size_bytes"]

    buf = io.StringIO()
    buf.write("# CAUCHY — bundle codice pipeline (slot [C1])\n\n")
    buf.write(f"Generato: {datetime.now(timezone.utc).isoformat()}\n\n")
    buf.write(f"Root: `{root}`\n\n")
    buf.write("File inclusi, in ordine di rilevanza:\n\n")
    for i, r in enumerate(chosen, 1):
        buf.write(f"{i}. `{r['rel']}` — score {r['score']}, {r['size_h']}\n")
    buf.write("\n---\n")

    for r in chosen:
        text = read_text(r["path"]) or ""
        buf.write(f"\n\n## FILE: {r['rel']}\n")
        buf.write(f"<!-- score={r['score']} size={r['size_h']} "
                  f"keywords={list(r['keyword_hits'])[:10]} -->\n\n")
        buf.write("```python\n")
        buf.write(text)
        if not text.endswith("\n"):
            buf.write("\n")
        buf.write("```\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    return chosen, total


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Trova il codice della pipeline CAUCHY (filtrazione/persistenza).")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="Root del progetto.")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP,
                    help="Quanti file includere nel bundle (default 8).")
    ap.add_argument("--report", default="pipeline_code_report.json")
    ap.add_argument("--bundle", default="pipeline_code_bundle.md")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print(f"[errore] root non trovata: {args.root}")
        sys.exit(1)

    print(f"[scan] .py/.ipynb sotto {args.root} ...", flush=True)
    results, n_seen = scan_python(args.root)
    print(f"       {n_seen} file esaminati, {len(results)} rilevanti.\n")

    print("=== TOP 15 CANDIDATI ===")
    for i, r in enumerate(results[:15], 1):
        kws = ", ".join(list(r["keyword_hits"])[:6])
        print(f"{i:2d}. [{r['score']:4d}] {r['rel']}  ({r['size_h']})")
        print(f"        keywords: {kws}")
        if r["defs_interesting"]:
            names = ", ".join(d["name"] for d in r["defs_interesting"][:6])
            print(f"        funzioni: {names}")

    print("\n[scan] json in results/ per lo slot [C2] ...", flush=True)
    jres = scan_results_json(args.root)
    print(f"       {len(jres)} json candidati.")
    for r in jres[:10]:
        print(f"   - {r['rel']}  ({r['size_h']})  termini={r['matched_terms']}")
        if r["candidate_numbers"]:
            for k, v in list(r["candidate_numbers"].items())[:6]:
                print(f"        {k} = {v}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": args.root,
        "n_python_files_seen": n_seen,
        "n_relevant": len(results),
        "ranked_python": results[:60],
        "candidate_result_jsons": jres[:40],
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    chosen, total = write_bundle(results, args.root, args.top, args.bundle)

    print("\n" + "=" * 70)
    print(f"[ok] report : {os.path.abspath(args.report)}")
    print(f"[ok] bundle : {os.path.abspath(args.bundle)}  "
          f"({len(chosen)} file, {human(total)})")
    print("\nCarica a Claude il BUNDLE (e, se piccolo, anche il report).")


if __name__ == "__main__":
    main()

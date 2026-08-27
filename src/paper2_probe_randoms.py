#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_probe_randoms.py — dove sono i random, e come si raggiungono

Domanda a cui risponde: il catalogo random e' un file leggibile per path con
colonne RA/DEC/Z, oppure e' raggiungibile solo attraverso `positions()` di
`paper2_data_geometry.py`?

**Sola lettura.** Non scrive nulla, non modifica nulla, non carica dati pesanti
a meno che non si passi --call. Nessun glob su results/paper1/ per contenuto:
i file vengono solo elencati e ispezionati nell'intestazione.

Uso (PowerShell, da D:\\projects\\cauchy):

    python src\\paper2_probe_randoms.py
    python src\\paper2_probe_randoms.py --call --region NGC     # se il primo non decide
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import os
import re
import sys

RA_NAMES = ["RA", "TARGET_RA", "RA_DEG", "ra"]
DEC_NAMES = ["DEC", "TARGET_DEC", "DEC_DEG", "dec"]
Z_NAMES = ["Z", "Z_COSMO", "Z_OBS", "Z_RSD", "REDSHIFT", "z"]

DATA_EXT = (".fits", ".fits.gz", ".fit", ".npy", ".npz", ".h5", ".hdf5",
            ".parquet", ".csv", ".dat", ".txt")
NAME_HINTS = ("random", "randoms", "ran_", "_ran", "rand")

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".idea"}


def human(nbytes):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024 or u == "TB":
            return "%.1f %s" % (nbytes, u)
        nbytes /= 1024.0


# ---------------------------------------------------------------- modulo

def probe_module(modname, srcdir):
    print("[1] modulo %s" % modname)
    if srcdir and srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    try:
        mod = importlib.import_module(modname)
    except Exception as exc:
        print("    IMPORT FALLITO: %s: %s" % (type(exc).__name__, exc))
        return None, None
    src_file = getattr(mod, "__file__", None)
    print("    file: %s" % src_file)
    for fn in ("positions", "derive_box", "build_mask", "data_side"):
        obj = getattr(mod, fn, None)
        if obj is None:
            print("    %-12s ASSENTE" % fn)
            continue
        try:
            sig = str(inspect.signature(obj))
        except (TypeError, ValueError):
            sig = "(firma non ispezionabile)"
        doc = (inspect.getdoc(obj) or "").splitlines()
        print("    %-12s %s" % (fn, sig))
        if doc:
            print("                 # %s" % doc[0][:90])
    return mod, src_file


def probe_constants(mod):
    print("\n[2] costanti di modulo che sembrano path")
    found = []
    for name in dir(mod):
        if name.startswith("_"):
            continue
        val = getattr(mod, name)
        cands = []
        if isinstance(val, str):
            cands = [val]
        elif isinstance(val, dict):
            cands = [v for v in val.values() if isinstance(v, str)]
        elif isinstance(val, (list, tuple)):
            cands = [v for v in val if isinstance(v, str)]
        for c in cands:
            if looks_like_path(c):
                exists = os.path.exists(c)
                print("    %-24s %s   [%s]" % (name, c,
                      ("esiste, " + human(os.path.getsize(c))) if os.path.isfile(c)
                      else ("directory" if os.path.isdir(c) else "NON ESISTE")))
                if exists and os.path.isfile(c):
                    found.append(c)
    if not found:
        print("    nessuna")
    return found


def looks_like_path(s):
    if len(s) < 5 or "\n" in s:
        return False
    if s.lower().endswith(DATA_EXT):
        return True
    return ("/" in s or "\\" in s) and not s.startswith("http")


def probe_source_literals(src_file):
    print("\n[3] path letterali nel sorgente")
    if not src_file or not os.path.exists(src_file):
        print("    sorgente non disponibile")
        return []
    with open(src_file, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    lits = set(re.findall(r"""['"]([^'"\n]{5,200})['"]""", text))
    hits = []
    for s in sorted(lits):
        if looks_like_path(s):
            st = ("esiste, " + human(os.path.getsize(s))) if os.path.isfile(s) else \
                 ("directory" if os.path.isdir(s) else "non risolvibile da qui")
            print("    %-60s [%s]" % (s[:60], st))
            if os.path.isfile(s):
                hits.append(s)
    if not hits:
        print("    nessun path letterale risolvibile")
    # righe che nominano i random, utili anche se il path e' composto
    print("\n[3b] righe del sorgente che nominano i random")
    n = 0
    for i, line in enumerate(text.splitlines(), 1):
        if any(h in line.lower() for h in NAME_HINTS) and not line.strip().startswith("#"):
            print("    %4d: %s" % (i, line.strip()[:100]))
            n += 1
            if n >= 12:
                print("    ... (troncato)")
                break
    if n == 0:
        print("    nessuna")
    return hits


# ---------------------------------------------------------------- disco

def scan_disk(roots, max_files=40):
    print("\n[4] file candidati sul disco")
    hits, seen = [], set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                low = fn.lower()
                if not low.endswith(DATA_EXT):
                    continue
                if not any(h in low for h in NAME_HINTS):
                    continue
                p = os.path.join(dirpath, fn)
                ap = os.path.abspath(p)
                if ap in seen:
                    continue
                seen.add(ap)
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    continue
                hits.append((sz, p))
    hits.sort(reverse=True)
    if not hits:
        print("    nessuno sotto: %s" % ", ".join(roots))
    for sz, p in hits[:max_files]:
        print("    %10s  %s" % (human(sz), p))
    if len(hits) > max_files:
        print("    ... altri %d" % (len(hits) - max_files))
    return [p for _, p in hits]


# ---------------------------------------------------------------- colonne

def columns_of(path):
    """Nomi di colonna senza caricare i dati, dove possibile."""
    low = path.lower()
    try:
        if low.endswith((".fits", ".fit", ".fits.gz")):
            try:
                import fitsio
                with fitsio.FITS(path) as f:
                    for h in f[1:]:
                        try:
                            return list(h.get_colnames()), "fitsio"
                        except Exception:
                            continue
            except ImportError:
                from astropy.io import fits
                with fits.open(path, memmap=True) as hdul:
                    for h in hdul[1:]:
                        if getattr(h, "columns", None) is not None:
                            return list(h.columns.names), "astropy"
        elif low.endswith(".npy"):
            import numpy as np
            a = np.load(path, mmap_mode="r", allow_pickle=False)
            return (list(a.dtype.names) if a.dtype.names else
                    ["<array %s %s>" % (a.shape, a.dtype)]), "numpy"
        elif low.endswith(".npz"):
            import numpy as np
            with np.load(path, allow_pickle=False) as z:
                return list(z.files), "numpy"
        elif low.endswith((".h5", ".hdf5")):
            import h5py
            with h5py.File(path, "r") as f:
                return list(f.keys()), "h5py"
        elif low.endswith(".parquet"):
            import pyarrow.parquet as pq
            return list(pq.ParquetFile(path).schema.names), "pyarrow"
        else:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                head = fh.readline().strip()
            return [c.strip() for c in re.split(r"[,\s;]+", head) if c], "testo"
    except Exception as exc:
        return ["<errore: %s: %s>" % (type(exc).__name__, exc)], "?"
    return ["<nessuna tabella>"], "?"


def match_cols(cols):
    def pick(names):
        for n in names:
            if n in cols:
                return n
        low = {c.lower(): c for c in cols}
        for n in names:
            if n.lower() in low:
                return low[n.lower()]
        return None
    return pick(RA_NAMES), pick(DEC_NAMES), pick(Z_NAMES)


def probe_columns(paths, limit=6):
    print("\n[5] colonne dei candidati")
    usable = []
    for p in paths[:limit]:
        cols, how = columns_of(p)
        ra, dec, z = match_cols(cols)
        print("    %s  [%s]" % (p, how))
        print("        colonne: %s" % (", ".join(cols[:18]) + (" ..." if len(cols) > 18 else "")))
        print("        RA=%s  DEC=%s  Z=%s  ->  %s"
              % (ra, dec, z, "USABILE" if all((ra, dec, z)) else "manca qualcosa"))
        if all((ra, dec, z)):
            usable.append((p, ra, dec, z))
    if not paths:
        print("    nessun candidato da ispezionare")
    return usable


# ---------------------------------------------------------------- chiamata

def call_positions(mod, region):
    print("\n[6] chiamata a positions()  (--call attivo)")
    if mod is None or not hasattr(mod, "positions"):
        print("    positions() non disponibile")
        return None
    import numpy as np
    attempts = [
        {"region": region, "kind": "randoms"},
        {"region": region, "kind": "random"},
        {"region": region, "which": "randoms"},
        {"region": region},
    ]
    for kw in attempts:
        try:
            out = mod.positions(**kw)
        except TypeError as exc:
            print("    positions(%s) -> TypeError: %s" % (kw, exc))
            continue
        except Exception as exc:
            print("    positions(%s) -> %s: %s" % (kw, type(exc).__name__, exc))
            continue
        print("    positions(%s) OK" % kw)
        describe_positions(out, np)
        return out
    print("    nessuna combinazione di argomenti ha funzionato")
    return None


def describe_positions(out, np):
    def desc(a, label=""):
        a = np.asarray(a)
        if a.dtype.names:
            print("        %s array strutturato %s, colonne: %s"
                  % (label, a.shape, ", ".join(a.dtype.names[:15])))
            return
        print("        %s shape=%s dtype=%s" % (label, a.shape, a.dtype))
        if a.ndim == 2 and a.shape[1] == 3:
            mn, mx = a.min(axis=0), a.max(axis=0)
            print("           min=%s" % np.array2string(mn, precision=2))
            print("           max=%s" % np.array2string(mx, precision=2))
            span = float(np.max(mx - mn))
            if span > 100:
                print("           -> estensione %.1f: sembrano COMOVENTI in h^-1 Mpc"
                      % span)
                print("           -> per l'item 1.2a serve anche z, oppure RA/Dec/z grezzi")
            else:
                print("           -> estensione %.3f: sembrano versori o coordinate normalizzate"
                      % span)
        elif a.ndim == 1:
            print("           min=%.4f max=%.4f" % (float(a.min()), float(a.max())))

    if isinstance(out, tuple):
        print("        tupla di %d elementi" % len(out))
        for i, el in enumerate(out):
            desc(el, "[%d]" % i)
    elif isinstance(out, dict):
        print("        dict, chiavi: %s" % ", ".join(map(str, out.keys())))
        for k, v in list(out.items())[:6]:
            desc(v, str(k))
    else:
        desc(out)


# ---------------------------------------------------------------- verdetto

def verdict(usable, mod, called):
    print("\n" + "=" * 70)
    print("VERDETTO")
    print("=" * 70)
    if usable:
        p, ra, dec, z = usable[0]
        print("CASO A — file leggibile per path. L'item 1.2a gira cosi':\n")
        print("  python src\\paper2_item12a_apgrid.py --region NGC `")
        print("      --randoms \"%s\" `" % p)
        print("      --ra-col %s --dec-col %s --z-col %s `" % (ra, dec, z))
        print("      --out results\\paper2\\item12a_NGC.jsonl")
        print("\n  (ripetere con --region SGC e il random corrispondente)")
        if len(usable) > 1:
            print("\n  Altri file usabili trovati: %d. Scegliere quello della regione giusta,"
                  % (len(usable) - 1))
            print("  e verificare che sia lo STESSO da cui e' derivato l'ensemble v1.")
    elif mod is not None and hasattr(mod, "positions"):
        print("CASO B — nessun file usabile trovato per path, ma positions() esiste.")
        print("Serve un adattatore nello script 1.2a. Riportare:")
        print("  * la firma di positions() dal blocco [1]")
        print("  * l'output del blocco [6] (rilanciare con --call se non l'hai fatto)")
        print("In particolare: positions() restituisce RA/Dec/z, oppure gia' xyz comoventi?")
        print("Se restituisce xyz comoventi calcolati con la fiducia Quijote, l'item 1.2a")
        print("non puo' usarli: deve ricalcolare D_C(z) per ogni geometria, quindi gli")
        print("servono i redshift.")
    else:
        print("CASO C — ne' file usabili, ne' positions(). Controllare --src e --module.")
    print()


def main():
    p = argparse.ArgumentParser(description="sonda: dove sono i random")
    p.add_argument("--module", default="paper2_data_geometry")
    p.add_argument("--src", default="src")
    p.add_argument("--roots", nargs="*", default=None,
                   help="directory in cui cercare (default: . e data/ se esiste)")
    p.add_argument("--region", default="NGC")
    p.add_argument("--call", action="store_true",
                   help="chiama davvero positions(); puo' caricare un catalogo grosso")
    a = p.parse_args()

    roots = a.roots
    if roots is None:
        roots = ["."]
        for extra in ("data", "..\\data", "../data", "D:\\data"):
            if os.path.isdir(extra):
                roots.append(extra)

    print("=" * 70)
    print("paper2_probe_randoms — sola lettura")
    print("cwd: %s" % os.getcwd())
    print("=" * 70 + "\n")

    mod, src_file = probe_module(a.module, a.src)
    const_paths = probe_constants(mod) if mod else []
    lit_paths = probe_source_literals(src_file) if src_file else []
    disk_paths = scan_disk(roots)

    seen, ordered = set(), []
    for x in const_paths + lit_paths + disk_paths:
        xa = os.path.abspath(x)
        if xa not in seen:
            seen.add(xa)
            ordered.append(x)

    usable = probe_columns(ordered)
    called = call_positions(mod, a.region) if a.call else None
    if not a.call:
        print("\n[6] chiamata a positions(): saltata (usare --call)")
    verdict(usable, mod, called)


if __name__ == "__main__":
    main()

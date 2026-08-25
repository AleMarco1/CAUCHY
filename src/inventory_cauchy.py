#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inventory_cauchy.py
-------------------
Step 0 del Paper 1: inventario congelato della struttura dati CAUCHY.

Scansiona ricorsivamente le radici indicate, conta i file per cartella,
campiona alcuni file per sottocartella e produce un report JSON che
descrive struttura, formati e convenzioni di naming.

Caratteristiche:
  * Solo standard library (nessuna dipendenza da installare).
  * Per i file .npy legge l'HEADER (shape + dtype) SENZA caricare l'array:
    questo rivela la risoluzione della griglia dei campi voxelizzati.
  * Per .npz elenca i nomi degli array contenuti (senza decomprimere i dati).
  * Riconosce le magic bytes dei formati comuni in cosmologia
    (FITS, HDF5, gzip, npy, ...).
  * Robusto a errori di permessi / file lockati.

Uso (Windows, PowerShell o cmd):
    python inventory_cauchy.py

Oppure specificando radici e parametri:
    python inventory_cauchy.py --roots "D:\\projects\\cauchy\\data" "D:\\projects\\cauchy\\results" --samples 5 --out inventory_report.json

Poi consegna il file inventory_report.json a Claude.
"""

import argparse
import json
import os
import sys
import struct
import ast
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configurazione di default
# ---------------------------------------------------------------------------
DEFAULT_ROOTS = [
    r"D:\projects\cauchy\data",
    r"D:\projects\cauchy\results",
]
DEFAULT_SAMPLES = 5          # file campione minimi per (sotto)cartella
DEFAULT_OUT = "inventory_report.json"
MAGIC_READ_BYTES = 16        # byte letti dall'inizio per il riconoscimento formato
MAX_NPY_HEADER = 4096        # limite di sicurezza per l'header .npy


# ---------------------------------------------------------------------------
# Riconoscimento formato tramite magic bytes / estensione
# ---------------------------------------------------------------------------
def sniff_format(path, head):
    """Restituisce una breve etichetta del formato del file."""
    ext = os.path.splitext(path)[1].lower()

    if head[:6] == b"\x93NUMPY":
        return "npy"
    if head[:4] == b"PK\x03\x04":
        # zip container: .npz oppure zip generico
        return "npz" if ext == ".npz" else "zip"
    if head[:6] == b"SIMPLE" or head[:8] == b"SIMPLE  ":
        return "fits"
    if head[:8] == b"\x89HDF\r\n\x1a\n":
        return "hdf5"
    if head[:2] == b"\x1f\x8b":
        return "gzip"           # potrebbe essere .fits.gz, .npy.gz, ecc.
    if head[:4] == b"\x50\x4b\x05\x06":
        return "zip(empty)"
    if ext in (".txt", ".dat", ".csv", ".json", ".yaml", ".yml", ".md", ".log", ".cfg", ".ini"):
        return "text/" + ext.lstrip(".")
    return ext.lstrip(".") if ext else "no-ext"


def read_npy_header(path):
    """
    Legge shape e dtype da un file .npy leggendo SOLO l'header
    (nessun caricamento dell'array in memoria).
    Ritorna un dict {shape, dtype, fortran_order} oppure {error}.
    """
    try:
        with open(path, "rb") as f:
            magic = f.read(6)
            if magic != b"\x93NUMPY":
                return {"error": "not-npy-magic"}
            major, minor = f.read(1), f.read(1)
            ver = (major[0], minor[0])
            if ver[0] == 1:
                (hlen,) = struct.unpack("<H", f.read(2))
            else:
                (hlen,) = struct.unpack("<I", f.read(4))
            hlen = min(hlen, MAX_NPY_HEADER)
            header = f.read(hlen).decode("latin1").strip()
            # header è un literal dict Python: {'descr':..., 'fortran_order':..., 'shape':...}
            d = ast.literal_eval(header)
            return {
                "shape": list(d.get("shape", [])),
                "dtype": str(d.get("descr", "")),
                "fortran_order": bool(d.get("fortran_order", False)),
                "npy_version": f"{ver[0]}.{ver[1]}",
            }
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def read_npz_members(path):
    """Elenca i nomi degli array in un .npz senza decomprimere i dati."""
    try:
        import zipfile
        with zipfile.ZipFile(path, "r") as z:
            names = [n[:-4] if n.endswith(".npy") else n for n in z.namelist()]
        return names[:50]
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def describe_file(path):
    """Metadati di un singolo file: nome, size, formato, e (se .npy) shape/dtype."""
    info = {"name": os.path.basename(path)}
    try:
        st = os.stat(path)
        info["size_bytes"] = st.st_size
        info["mtime"] = datetime.fromtimestamp(
            st.st_mtime, tz=timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError as e:
        info["error"] = f"stat failed: {e}"
        return info

    head = b""
    try:
        with open(path, "rb") as f:
            head = f.read(MAGIC_READ_BYTES)
    except OSError as e:
        info["fmt"] = "unreadable"
        info["error"] = f"open failed: {e}"
        return info

    fmt = sniff_format(path, head)
    info["fmt"] = fmt

    if fmt == "npy":
        info["npy"] = read_npy_header(path)
    elif fmt == "npz":
        info["npz_members"] = read_npz_members(path)

    return info


def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024.0


# ---------------------------------------------------------------------------
# Scansione
# ---------------------------------------------------------------------------
def scan_root(root, samples_per_dir):
    """
    Percorre 'root' con os.walk. Per ogni cartella registra:
      - conteggio file
      - dimensione totale
      - istogramma per estensione
      - fino a 'samples_per_dir' file campione descritti in dettaglio
        (privilegiando estensioni diverse per massimizzare l'informazione)
    """
    dirs_out = {}
    global_ext_counts = defaultdict(int)
    global_ext_bytes = defaultdict(int)
    grand_total_files = 0
    grand_total_bytes = 0
    errors = []

    if not os.path.isdir(root):
        return {
            "exists": False,
            "note": "cartella non trovata",
            "dirs": {},
            "summary": {},
        }

    for dirpath, dirnames, filenames in os.walk(root):
        # ordine deterministico
        dirnames.sort()
        filenames.sort()

        file_count = len(filenames)
        grand_total_files += file_count

        ext_counts = defaultdict(int)
        ext_bytes = defaultdict(int)
        dir_bytes = 0
        by_ext_examples = defaultdict(list)

        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower() or "<none>"
            ext_counts[ext] += 1
            global_ext_counts[ext] += 1
            fp = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                sz = 0
            dir_bytes += sz
            ext_bytes[ext] += sz
            global_ext_bytes[ext] += sz
            if len(by_ext_examples[ext]) < 3:
                by_ext_examples[ext].append(fn)

        grand_total_bytes += dir_bytes

        # --- selezione campioni: uno per estensione (round-robin) fino al minimo ---
        chosen = []
        # prima passata: un file per ciascuna estensione (diversità di formato)
        for ext in sorted(by_ext_examples.keys()):
            chosen.append(by_ext_examples[ext][0])
        # seconda passata: riempi fino a samples_per_dir con altri esempi
        if len(chosen) < samples_per_dir:
            for ext in sorted(by_ext_examples.keys()):
                for fn in by_ext_examples[ext][1:]:
                    if len(chosen) >= samples_per_dir:
                        break
                    if fn not in chosen:
                        chosen.append(fn)
                if len(chosen) >= samples_per_dir:
                    break
        chosen = chosen[:max(samples_per_dir, 0)] if samples_per_dir else chosen

        sample_details = []
        for fn in chosen:
            fp = os.path.join(dirpath, fn)
            try:
                sample_details.append(describe_file(fp))
            except Exception as e:  # noqa: BLE001
                errors.append(f"{fp}: {type(e).__name__}: {e}")

        rel = os.path.relpath(dirpath, root)
        rel = "." if rel == os.curdir else rel.replace("\\", "/")

        dirs_out[rel] = {
            "n_files": file_count,
            "n_subdirs": len(dirnames),
            "total_bytes": dir_bytes,
            "total_size_h": human_size(dir_bytes),
            "ext_counts": dict(sorted(ext_counts.items(), key=lambda x: -x[1])),
            "ext_bytes_h": {k: human_size(v) for k, v in
                            sorted(ext_bytes.items(), key=lambda x: -x[1])},
            "samples": sample_details,
        }

    summary = {
        "n_dirs": len(dirs_out),
        "grand_total_files": grand_total_files,
        "grand_total_bytes": grand_total_bytes,
        "grand_total_size_h": human_size(grand_total_bytes),
        "ext_counts_global": dict(sorted(global_ext_counts.items(),
                                          key=lambda x: -x[1])),
        "ext_bytes_global_h": {k: human_size(v) for k, v in
                               sorted(global_ext_bytes.items(),
                                      key=lambda x: -x[1])},
    }

    return {
        "exists": True,
        "summary": summary,
        "dirs": dirs_out,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Inventario CAUCHY (Step 0).")
    ap.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS,
                    help="Cartelle radice da scansionare.")
    ap.add_argument("--samples", type=int, default=DEFAULT_SAMPLES,
                    help="File campione minimi per cartella (default 5).")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help="Percorso del report JSON in output.")
    args = ap.parse_args()

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": os.path.basename(__file__),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "samples_per_dir": args.samples,
        "roots": {},
    }

    for root in args.roots:
        print(f"[scan] {root} ...", flush=True)
        report["roots"][root] = scan_root(root, args.samples)
        s = report["roots"][root].get("summary", {})
        if s:
            print(f"       {s.get('grand_total_files', 0)} file in "
                  f"{s.get('n_dirs', 0)} cartelle "
                  f"({s.get('grand_total_size_h', '?')})", flush=True)
        else:
            print("       (cartella non trovata)", flush=True)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[ok] Report scritto in: {os.path.abspath(args.out)}")
    print("Consegna questo file JSON a Claude.")


if __name__ == "__main__":
    main()

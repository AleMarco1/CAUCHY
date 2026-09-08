#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_ricognizione_4_2a.py

RICOGNIZIONE DI SOLA LETTURA per la passata a un punto su v1 (item 4.2a, spec p.3).

Cosa fa:
  - localizza i registri a un punto di v1 e i manifest della cache dei delta;
  - ne stampa conteggio, schema (chiavi con prefisso), campo indice e copertura;
  - sonda la cache dei delta: nomi, conteggio, byte, intestazione npy;
  - cerca nel sorgente i punti di ingresso canonici (nu, maschera, geometria).

Cosa NON fa, per costruzione:
  - non importa nessun modulo del progetto (niente stato di geometria, niente FITS);
  - non calcola nessuna quantita' fisica;
  - non scrive nulla fuori dal file passato a --out.

Uso:
    python src\\paper2_ricognizione_4_2a.py selftest
    python src\\paper2_ricognizione_4_2a.py scan --root . --out logs\\ricognizione_4_2a.json

Uscita: 0 se tutto bene, 1 se il selftest fallisce, 2 su errore d'uso.
Tutte le stampe sono ASCII puro: PowerShell non deve indovinare un encoding.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# --------------------------------------------------------------------------
# bersagli della ricognizione
# --------------------------------------------------------------------------

REGISTRI = [
    "n1_spectra_NGC.jsonl",
    "n1_spectra_SGC.jsonl",
    "n1b_spectra_NGC.jsonl",
    "n1b_spectra_SGC.jsonl",
    "cachedelta_manifest_NGC.jsonl",
    "cachedelta_manifest_SGC.jsonl",
    "fase3_mock.jsonl",
    "paper2_v1_reference.json",
]

# (etichetta, regex) -- il perche' di ciascuno sta nel messaggio di scan
GREP = [
    ("scrive_n1_spectra",   r"n1b?_spectra"),
    ("def_build_field",     r"def\s+build_field\s*\("),
    ("def_set_geometry",    r"def\s+set_geometry\s*\("),
    ("def_compute_delta",   r"def\s+compute_delta\s*\("),
    ("usa_sigma_in_mask",   r"sigma_in_mask|kurt_in_mask"),
    ("maschera_field_r",    r"field_r\s*>"),
    ("sigma_px",            r"R_SMOOTH|sigma_px|SIGMA_PX"),
    ("percentili",          r"percentile\s*\(|nanpercentile\s*\("),
    ("max_delta",           r"max_delta"),
    ("patologici",          r"patolog|patholog"),
    ("delta_dir",           r"frozen[-_]delta[-_]dir|paper1_mock_deltas"),
    ("delta_sha256",        r"delta_sha256"),
]

CANDIDATI_IDX = ("idx", "index", "imock", "i_mock", "mock", "mock_idx",
                 "realization", "realisation", "seed")

ESCLUDI_DIR = {".git", "node_modules", "__pycache__", ".venv", "venv",
               ".mypy_cache", ".pytest_cache", "site-packages"}

BYTE_ATTESI_CAMPO = 8_388_736  # 128^3 float32 + intestazione npy


# --------------------------------------------------------------------------
# primitive
# --------------------------------------------------------------------------

def flat_keys(obj, prefix=""):
    """Chiavi con prefisso puntato. I dict annidati si aprono; le liste no."""
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = "%s.%s" % (prefix, k) if prefix else str(k)
            if isinstance(v, dict) and v:
                out |= flat_keys(v, p)
            else:
                out.add(p)
    return out


def _tronca(v, n=60):
    s = repr(v)
    return s if len(s) <= n else s[: n - 3] + "..."


def scan_jsonl(path, campione=3):
    """Conteggio, schema, campo indice, copertura. Legge tutto il file una volta."""
    info = {
        "path": str(path), "esiste": True, "n_record": 0, "n_righe_vuote": 0,
        "n_righe_illeggibili": 0, "chiavi": [], "chiavi_per_record_variabili": False,
        "campo_idx": None, "idx_min": None, "idx_max": None, "idx_distinti": 0,
        "idx_mancanti_nel_range": None, "primo_record": {}, "byte": None,
    }
    p = Path(path)
    info["byte"] = p.stat().st_size
    chiavi_union, chiavi_inter, idx_vals, primo = set(), None, [], None

    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for riga in fh:
            riga = riga.strip()
            if not riga:
                info["n_righe_vuote"] += 1
                continue
            try:
                rec = json.loads(riga)
            except Exception:
                info["n_righe_illeggibili"] += 1
                continue
            if not isinstance(rec, dict):
                info["n_righe_illeggibili"] += 1
                continue
            info["n_record"] += 1
            k = flat_keys(rec)
            chiavi_union |= k
            chiavi_inter = k if chiavi_inter is None else (chiavi_inter & k)
            if primo is None:
                primo = rec

    info["chiavi"] = sorted(chiavi_union)
    info["chiavi_per_record_variabili"] = bool(
        chiavi_inter is not None and chiavi_inter != chiavi_union)
    if primo is not None:
        info["primo_record"] = {k: _tronca(v) for k, v in
                                sorted(_appiattisci_valori(primo).items())}

    # campo indice: prima corrispondenza esatta nell'ordine dei candidati
    for cand in CANDIDATI_IDX:
        if cand in chiavi_union:
            info["campo_idx"] = cand
            break
    if info["campo_idx"]:
        with p.open("r", encoding="utf-8", errors="replace") as fh:
            for riga in fh:
                riga = riga.strip()
                if not riga:
                    continue
                try:
                    rec = json.loads(riga)
                except Exception:
                    continue
                v = rec.get(info["campo_idx"]) if isinstance(rec, dict) else None
                if isinstance(v, int):
                    idx_vals.append(v)
        if idx_vals:
            info["idx_min"] = min(idx_vals)
            info["idx_max"] = max(idx_vals)
            info["idx_distinti"] = len(set(idx_vals))
            atteso = info["idx_max"] - info["idx_min"] + 1
            info["idx_mancanti_nel_range"] = atteso - info["idx_distinti"]
    return info


def _appiattisci_valori(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = "%s.%s" % (prefix, k) if prefix else str(k)
            if isinstance(v, dict) and v:
                out.update(_appiattisci_valori(v, p))
            else:
                out[p] = v
    return out


def npy_header(path):
    """Forma, dtype e byte di un .npy, senza caricare l'array."""
    import numpy as np
    p = Path(path)
    with p.open("rb") as fh:
        version = np.lib.format.read_magic(fh)
        if version == (1, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(fh)
        else:
            shape, fortran, dtype = np.lib.format.read_array_header_2_0(fh)
    return {"path": str(p), "shape": list(shape), "dtype": str(dtype),
            "fortran": bool(fortran), "byte": p.stat().st_size}


def trova_file(root, nomi):
    """Cerca per nome esatto sotto root, saltando le directory escluse."""
    voluti = set(nomi)
    trovati = {n: [] for n in voluti}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ESCLUDI_DIR]
        for f in filenames:
            if f in voluti:
                trovati[f].append(str(Path(dirpath) / f))
    return trovati


def grep_sorgenti(root, coppie, max_hit=12):
    """Cerca le regex nei soli .py. Ritorna file:riga:testo, troncato."""
    esiti = {et: [] for et, _ in coppie}
    compilate = [(et, re.compile(rx)) for et, rx in coppie]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ESCLUDI_DIR]
        for f in filenames:
            if not f.endswith(".py"):
                continue
            fp = Path(dirpath) / f
            try:
                testo = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for n, riga in enumerate(testo.splitlines(), 1):
                for et, rx in compilate:
                    if len(esiti[et]) >= max_hit:
                        continue
                    if rx.search(riga):
                        esiti[et].append("%s:%d: %s" % (fp, n, riga.strip()[:140]))
    return esiti


def sonda_cache(root, region):
    d = Path(root) / "data" / "processed" / "paper1_mock_deltas" / region
    info = {"dir": str(d), "esiste": d.is_dir(), "n_file": 0,
            "byte_distinti": [], "primi": [], "ultimo": None, "header": None}
    if not d.is_dir():
        return info
    files = sorted(p for p in d.iterdir() if p.is_file())
    info["n_file"] = len(files)
    info["primi"] = [p.name for p in files[:3]]
    info["ultimo"] = files[-1].name if files else None
    info["byte_distinti"] = sorted({p.stat().st_size for p in files})[:5]
    if files:
        try:
            info["header"] = npy_header(files[0])
        except Exception as e:
            info["header"] = {"errore": "%s: %s" % (type(e).__name__, e)}
    return info


# --------------------------------------------------------------------------
# scan
# --------------------------------------------------------------------------

def scan(root, out_path=None):
    root = str(Path(root).resolve())
    rapporto = {"root": root, "registri": {}, "cache": {}, "sorgenti": {}}

    print("=" * 78)
    print("RICOGNIZIONE 4.2a -- sola lettura, nessun import di progetto")
    print("root:", root)
    print("=" * 78)

    trovati = trova_file(root, REGISTRI)
    print("\n--- REGISTRI ---")
    for nome in REGISTRI:
        paths = trovati.get(nome, [])
        if not paths:
            print("  [ASSENTE] %s" % nome)
            rapporto["registri"][nome] = {"esiste": False}
            continue
        if len(paths) > 1:
            print("  [ATTENZIONE] %s trovato in %d posti: %s"
                  % (nome, len(paths), paths))
        p = paths[0]
        if nome.endswith(".jsonl"):
            info = scan_jsonl(p)
            info["copie"] = paths
            rapporto["registri"][nome] = info
            print("  [OK] %s" % nome)
            print("       path      : %s" % p)
            print("       record    : %d  (vuote %d, illeggibili %d, byte %d)"
                  % (info["n_record"], info["n_righe_vuote"],
                     info["n_righe_illeggibili"], info["byte"]))
            if info["campo_idx"]:
                print("       idx       : campo '%s', da %s a %s, distinti %d, "
                      "mancanti nel range %s"
                      % (info["campo_idx"], info["idx_min"], info["idx_max"],
                         info["idx_distinti"], info["idx_mancanti_nel_range"]))
            else:
                print("       idx       : NESSUN campo indice riconosciuto")
            if info["chiavi_per_record_variabili"]:
                print("       [ATTENZIONE] lo schema NON e' costante fra i record")
            print("       chiavi    : %s" % ", ".join(info["chiavi"]))
            print("       record 0  :")
            for k, v in info["primo_record"].items():
                print("           %-34s %s" % (k, v))
        else:
            rapporto["registri"][nome] = {"esiste": True, "path": p,
                                          "byte": Path(p).stat().st_size}
            print("  [OK] %s  (%s, %d byte) -- non aperto, non e' jsonl"
                  % (nome, p, Path(p).stat().st_size))

    print("\n--- CACHE DEI DELTA ---")
    for region in ("NGC", "SGC"):
        info = sonda_cache(root, region)
        rapporto["cache"][region] = info
        if not info["esiste"]:
            print("  [ASSENTE] %s" % info["dir"])
            continue
        print("  [OK] %s" % region)
        print("       dir   : %s" % info["dir"])
        print("       file  : %d, primi %s, ultimo %s"
              % (info["n_file"], info["primi"], info["ultimo"]))
        print("       byte  : distinti %s (attesi %d per campo)"
              % (info["byte_distinti"], BYTE_ATTESI_CAMPO))
        if info["header"]:
            print("       npy   : %s" % info["header"])
        if info["byte_distinti"] and info["byte_distinti"] != [BYTE_ATTESI_CAMPO]:
            print("       [ATTENZIONE] byte non uniformi o diversi dall'atteso")

    print("\n--- SORGENTI (grep, solo .py) ---")
    esiti = grep_sorgenti(root, GREP)
    rapporto["sorgenti"] = esiti
    for etichetta, _ in GREP:
        hit = esiti[etichetta]
        print("  %s: %d" % (etichetta, len(hit)))
        for h in hit:
            print("      %s" % h)

    if out_path:
        op = Path(out_path)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps(rapporto, indent=2, ensure_ascii=True),
                      encoding="utf-8")
        print("\nrapporto scritto in %s" % op)
    print("\nFINE RICOGNIZIONE")
    return 0


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------

def selftest():
    ok, tot = 0, 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, n))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, n, det))

    print("selftest paper2_ricognizione_4_2a")

    # 1-3: flat_keys
    d = {"a": 1, "b": {"c": 2, "d": {"e": 3}}, "f": [1, 2, 3], "g": {}}
    k = flat_keys(d)
    chk("flat_keys apre i dict annidati", k == {"a", "b.c", "b.d.e", "f", "g"}, k)
    chk("flat_keys non apre le liste", "f.0" not in k)
    chk("flat_keys tiene i dict vuoti come foglia", "g" in k)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # 4-8: scan_jsonl
        f = td / "r.jsonl"
        righe = [
            json.dumps({"idx": 0, "base": {"N_H1": 10}, "sigma_in_mask": 1.5}),
            "",
            json.dumps({"idx": 2, "base": {"N_H1": 12}, "sigma_in_mask": 1.7}),
            "{non json",
            json.dumps({"idx": 3, "base": {"N_H1": 13}, "sigma_in_mask": 1.9,
                        "extra": 1}),
        ]
        f.write_text("\n".join(righe) + "\n", encoding="utf-8")
        i = scan_jsonl(f)
        chk("scan_jsonl conta i record buoni", i["n_record"] == 3, i["n_record"])
        chk("scan_jsonl conta vuote e illeggibili",
            i["n_righe_vuote"] == 1 and i["n_righe_illeggibili"] == 1, i)
        chk("scan_jsonl trova il campo idx", i["campo_idx"] == "idx", i["campo_idx"])
        chk("scan_jsonl misura il buco nel range",
            i["idx_min"] == 0 and i["idx_max"] == 3
            and i["idx_distinti"] == 3 and i["idx_mancanti_nel_range"] == 1, i)
        chk("scan_jsonl segnala schema non costante",
            i["chiavi_per_record_variabili"] is True, i["chiavi"])
        chk("scan_jsonl usa il prefisso per gli annidati",
            "base.N_H1" in i["chiavi"] and "N_H1" not in i["chiavi"], i["chiavi"])

        # 10-12: npy_header
        try:
            import numpy as np
            a = np.zeros((4, 4, 4), dtype=np.float32)
            fn = td / "d.npy"
            np.save(fn, a)
            h = npy_header(fn)
            chk("npy_header legge forma e dtype",
                h["shape"] == [4, 4, 4] and h["dtype"] == "float32", h)
            chk("npy_header non carica l'array (byte coerenti)",
                h["byte"] == fn.stat().st_size, h)
            b = np.zeros((128, 128, 128), dtype=np.float32)
            fn2 = td / "d128.npy"
            np.save(fn2, b)
            chk("128^3 float32 pesa %d byte" % BYTE_ATTESI_CAMPO,
                fn2.stat().st_size == BYTE_ATTESI_CAMPO, fn2.stat().st_size)
        except ImportError:
            chk("numpy assente: tre controlli npy saltati", False, "numpy mancante")

        # 13-15: grep e trova_file
        src = td / "src"
        src.mkdir()
        (src / "m.py").write_text("def build_field(delta):\n    return delta\n",
                                  encoding="utf-8")
        (src / "note.txt").write_text("def build_field(x): pass\n", encoding="utf-8")
        g = grep_sorgenti(td, [("bf", r"def\s+build_field\s*\(")])
        chk("grep trova nel .py", len(g["bf"]) == 1, g)
        chk("grep ignora i non-.py", all("note.txt" not in h for h in g["bf"]), g)
        (td / "pycache_finto").mkdir()
        t = trova_file(td, ["m.py", "inesistente.jsonl"])
        chk("trova_file per nome esatto",
            len(t["m.py"]) == 1 and t["inesistente.jsonl"] == [], t)

        # 16: troncamento
        chk("i valori lunghi vengono troncati",
            len(_tronca("x" * 500)) == 60, len(_tronca("x" * 500)))

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("scan", help="ricognizione di sola lettura")
    s.add_argument("--root", default=".")
    s.add_argument("--out", default=None)
    sub.add_parser("selftest", help="controlli interni")
    a = ap.parse_args(argv)
    if a.cmd == "scan":
        return scan(a.root, a.out)
    if a.cmd == "selftest":
        return selftest()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

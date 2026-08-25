#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2f_srcdump.py

V2f - CHI SCRIVE COSA: bundle dei sorgenti rilevanti

PERCHE'
-------
Accertato finora:
  - w0 in phase9_likeforlike_arrays.npz varia da -1.299 a -0.701 sui primi
    200 mock, con 200 valori distinti; NaN sui restanti 1800.
    Il Latin hypercube standard di Quijote NON varia w0.
  - esiste src\\phase9_w0_response_curve.py, il file con piu' corrispondenze.
  - il blocco 0-199 e' anomalo SOLO in M26, e lo e' in DUE statistiche
    indipendenti (N_H1: sigma_MAD 350.6 vs 262.4; mean_pers1: 0.0359 vs
    0.0231), a posizione invariata. Firma di 200 cosmologie diverse
    mescolate a 1800 realizzazioni della stessa.
  - le nostre catene sono pulite (KS p = 0.37 NGC, 0.16 SGC).

Restano due letture con conseguenze molto diverse:
  (i)  l'npz mescola due sorgenti PER COSTRUZIONE e la tabella battery di
       M26 e' stata calcolata su un ensemble non omogeneo -> errore in un
       paper ancora in review.
  (ii) l'npz e' un file di LAVORO (curva di risposta a w0 + like-for-like
       parcheggiati insieme) che NOI abbiamo letto come se fosse l'ensemble
       di riferimento, mentre la tabella battery viene da un altro file
       -> l'errore e' nostro.

Il report JSON del v2e conserva solo i CONTEGGI per file, non le righe: il
codice serve per intero. Questo script lo raccoglie in un unico bundle.

Solo lettura. Scrive un file di testo da caricare in chat.

USO
---
  python src\\paper1_rev_v2f_srcdump.py
  python src\\paper1_rev_v2f_srcdump.py --max_files 6 --max_kb 120
"""

import argparse
import re
from pathlib import Path

import numpy as np

# file da includere sempre se esistono
PRIORITY = ["phase9_w0_response_curve.py", "phase9_extract_features.py",
            "phase9b_majors.py", "phase9_sgc_likeforlike.py",
            "phase8_cutsky_mocks.py"]

# pattern che identificano scritture su disco e sorgenti di dati
WRITE_PAT = re.compile(
    r"(np\.savez\w*|np\.save|savez_compressed|to_json|json\.dump|"
    r"open\s*\(|\.npz|\.npy|\.jsonl)", re.I)
DATA_PAT = re.compile(
    r"(latin|hypercube|nwLH|fiducial|fiduciale|quijote|w0|wa\b|"
    r"likeforlike|like_for_like|battery|baseline|B3)", re.I)
PATHLIT = re.compile(r"""["']([A-Za-z]:[\\/][^"']{3,}|(?:\.{0,2}[\\/])?"""
                     r"""(?:data|results|mocks|sims)[\\/][^"']{3,})["']""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--max_files", type=int, default=5)
    ap.add_argument("--max_kb", type=int, default=100,
                    help="salta i file piu' grandi di cosi'")
    ap.add_argument("--out", default="results\\paper1\\src_bundle_phase9.txt")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    srcs = []
    for d in (root / "src", root):
        if d.exists():
            srcs += [p for p in d.rglob("*.py")
                     if ".venv" not in str(p) and "site-packages" not in str(p)
                     and not p.name.startswith("paper1_rev_")]
    srcs = sorted(set(srcs))

    # ---------------------------------------------------------- indice scritture
    print("=" * 78)
    print("INDICE: quale sorgente scrive quale file")
    print("=" * 78)
    index_lines = []
    for p in srcs:
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for i, L in enumerate(lines):
            if WRITE_PAT.search(L) and re.search(r"\.npz|\.npy|\.jsonl|\.json", L):
                s = L.strip()[:130]
                index_lines.append(f"  {p.name:<34s} {i+1:>5d}| {s}")
    for L in index_lines[:120]:
        print(L)
    if len(index_lines) > 120:
        print(f"  ... e altre {len(index_lines) - 120} righe")

    # ---------------------------------------------------------- percorsi dati
    print("\n" + "=" * 78)
    print("PERCORSI DI DATI CITATI NEI SORGENTI")
    print("=" * 78)
    paths = {}
    for p in srcs:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in PATHLIT.finditer(txt):
            paths.setdefault(m.group(1), set()).add(p.name)
    for k in sorted(paths):
        print(f"  {k}")
        print(f"      <- {', '.join(sorted(paths[k])[:6])}")

    # ---------------------------------------------------------- selezione file
    def score(p):
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return 1e9
        s = 0
        if p.name in PRIORITY:
            s -= 1000 - PRIORITY.index(p.name)
        if "phase9_likeforlike_arrays" in txt:
            s -= 500
        s -= 3 * len(DATA_PAT.findall(txt))
        return s

    chosen = [p for p in sorted(srcs, key=score)
              if p.stat().st_size <= args.max_kb * 1024][:args.max_files]

    # ---------------------------------------------------------- bundle
    outp = root.joinpath(*[q for q in args.out.replace("\\", "/").split("/") if q])
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, "w", encoding="utf-8") as f:
        f.write("BUNDLE SORGENTI PHASE9 - CAUCHY Paper 1 revisione\n")
        f.write(f"project_root: {root}\n")
        f.write(f"file inclusi: {len(chosen)}\n\n")
        f.write("INDICE DELLE SCRITTURE SU DISCO\n")
        f.write("-" * 78 + "\n")
        for L in index_lines:
            f.write(L + "\n")
        f.write("\nPERCORSI DI DATI CITATI\n")
        f.write("-" * 78 + "\n")
        for k in sorted(paths):
            f.write(f"{k}\n    <- {', '.join(sorted(paths[k]))}\n")
        for p in chosen:
            f.write("\n\n" + "=" * 78 + "\n")
            f.write(f"FILE: {p}\n")
            f.write(f"bytes: {p.stat().st_size}\n")
            f.write("=" * 78 + "\n")
            try:
                for i, L in enumerate(
                        p.read_text(encoding="utf-8",
                                    errors="replace").splitlines()):
                    f.write(f"{i+1:>5d}| {L}\n")
            except Exception as e:
                f.write(f"[illeggibile: {e}]\n")

    print("\n" + "=" * 78)
    print("FILE INCLUSI NEL BUNDLE")
    print("=" * 78)
    for p in chosen:
        print(f"  {p}   ({p.stat().st_size/1024:.1f} kB)")
    print(f"\nbundle scritto in: {outp}")
    print(f"dimensione: {outp.stat().st_size/1024:.1f} kB")
    print("\nCaricalo in chat. Le domande a cui deve rispondere:")
    print("  1. quale script scrive phase9_likeforlike_arrays.npz, e con che")
    print("     contenuto: e' un prodotto finale o un file di lavoro?")
    print("  2. da quali directory vengono i mock 0-199 e i restanti 1800?")
    print("  3. w0/Om/s8 sono allineati con beta1_max[0:200], o sono array")
    print("     di un altro esperimento parcheggiati nello stesso npz?")
    print("  4. su quale file e' calcolata la tabella battery B3 di M26")
    print("     (35425 +/- 445): questo npz o un altro?")


if __name__ == "__main__":
    main()

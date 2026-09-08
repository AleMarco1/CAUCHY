#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_maschera_intersezione_patch.py — §3.2 del referee, record 24.

IL DISEGNO, IN DUE PASSATE
  Passata 1  `--mask-intersect-out FILE`: a ogni punto la maschera si deriva
             normalmente e si accumula l'AND logico. A fine run l'intersezione
             si scrive su FILE. Nessun risultato si riporta: e' una passata di
             sola geometria, e i suoi record portano `mask_pass = "derive"`.
  Passata 2  `--mask-fixed FILE`: la maschera si CARICA e non si deriva. Allora
             n_valid_voxels e' costante per costruzione e il termine (e) non
             esiste, invece di essere sottratto. E' il senso del test.

CANCELLO D6, tolleranza zero (record 24)
  In passata 2, n_valid_voxels deve essere IDENTICO a tutti i punti. E' costante
  per costruzione, quindi qualunque variazione significa che la modalita' non fa
  quel che dice. Il controllo e' cumulativo dentro il processo: il primo punto
  fissa il valore, ogni punto successivo lo confronta, e alla prima differenza
  si ferma.

CIO' CHE NON RIPRODURRA', DICHIARATO PRIMA (record 24)
  L'intersezione e' piu' piccola di ogni singola maschera, quindi N_H1 scende a
  OGNI punto e il fiduciale NON dara' 28256 o 15122. Non e' un difetto: e' il
  disegno. Il codice lo stampa all'avvio della passata 2, cosi' non serve
  ricordarselo, e il cancello di riproduzione abituale non si applica: al suo
  posto c'e' D6.

CINQUE MODIFICHE
  A  due flag: --mask-intersect-out e --mask-fixed, mutuamente esclusivi
  B  la maschera si carica invece di derivarla, se --mask-fixed
  C  l'AND si accumula e si scrive, se --mask-intersect-out
  D  CANCELLO D6 sul conteggio voxel, in passata 2
  E  la scrittura dell'intersezione viene CHIAMATA, nel finally
  F  mask_pass nel record, cosi' le due passate non si confondono in lettura

Uso:
    python src\\paper2_maschera_intersezione_patch.py selftest
    python src\\paper2_maschera_intersezione_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_runner_fase3.py")

B_OLD = '''    field_r = M.cic_3d(pos_r, w_r, M.NGRID, M.BOX_MIN, M.BOX_SIZE)'''

B_NEW = '''    field_r = M.cic_3d(pos_r, w_r, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    # §3.2 / record 24. In passata 2 la maschera si CARICA. La regola esplicita
    # 0.01*field_r.mean() qui non si applica: l'intersezione non e' la maschera
    # di questo punto, e' quella comune a tutti. Il controllo che resta e' D6.
    _mfix = getattr(one_point, "_mask_fixed", None)'''

C_OLD = '''    mask, thr_reported = F2.unpack_mask(G.build_mask(field_r, "v1_fullcube"))
    thr = 0.01 * float(field_r.mean())
    if not np.array_equal(mask, field_r > thr):
        sys.exit("[FATAL] build_mask('v1_fullcube') non coincide con la regola "
                 "esplicita 0.01*field_r.mean(). Il 2.1-M vale per la seconda.")
    rec.update(mask_threshold=thr, mask_threshold_reported=thr_reported,
               n_valid_voxels=int(mask.sum()))'''

C_NEW = '''    mask, thr_reported = F2.unpack_mask(G.build_mask(field_r, "v1_fullcube"))
    thr = 0.01 * float(field_r.mean())
    if not np.array_equal(mask, field_r > thr):
        sys.exit("[FATAL] build_mask('v1_fullcube') non coincide con la regola "
                 "esplicita 0.01*field_r.mean(). Il 2.1-M vale per la seconda.")
    rec.update(mask_threshold=thr, mask_threshold_reported=thr_reported)
    # Passata 1: si accumula l'AND. La maschera del punto e' quella derivata,
    # quindi la passata 1 e' identica al comportamento di sempre a parte
    # l'accumulo, che non tocca nulla.
    _acc = getattr(one_point, "_mask_acc", None)
    if _acc is not None:
        one_point._mask_acc = mask.copy() if _acc is True else (_acc & mask)
        rec["mask_pass"] = "derive"
    # Passata 2: si sostituisce, e da qui in poi `mask` E' l'intersezione.
    if _mfix is not None:
        if _mfix.shape != mask.shape:
            sys.exit(f"[FATAL] maschera fissa di forma {_mfix.shape} contro "
                     f"{mask.shape} attesa: non e' l'intersezione di questa "
                     f"geometria.")
        if not np.all(mask[_mfix]):
            sys.exit("[FATAL] la maschera fissa NON e' contenuta in quella di "
                     "questo punto: non e' un'intersezione dei dodici punti.")
        mask = _mfix
        rec["mask_pass"] = "fixed"
    rec.update(n_valid_voxels=int(mask.sum()))
    # CANCELLO D6, tolleranza zero (record 24). In passata 2 il conteggio e'
    # costante PER COSTRUZIONE: se varia, la modalita' non fa quel che dice.
    if _mfix is not None:
        _n = int(mask.sum())
        _first = getattr(one_point, "_d6_n", None)
        if _first is None:
            one_point._d6_n = _n
        elif _n != _first:
            sys.exit(f"[FATAL] D6: n_valid_voxels = {_n} contro {_first} del "
                     f"primo punto. Con maschera fissa e' costante per "
                     f"costruzione. Tolleranza zero, record 24.")'''

# I flag vanno SOLO al sottocomando `run`: d3 e symmetry non c'entrano, e
# ancorarsi a `--out` li darebbe a tutti e tre.
D_OLD = '''        if nm == "run":
            q.add_argument("--points", nargs="*", default=None)'''

D_NEW = '''        if nm == "run":
            q.add_argument("--points", nargs="*", default=None)
            q.add_argument("--mask-intersect-out", default=None, metavar="FILE",
                           help="§3.2 passata 1: accumula l'AND delle maschere "
                                "dei punti e lo scrive in FILE.")
            q.add_argument("--mask-fixed", default=None, metavar="FILE",
                           help="§3.2 passata 2: CARICA la maschera invece di "
                                "derivarla. n_valid_voxels diventa costante per "
                                "costruzione e il termine (e) non esiste. "
                                "Usare un --out SEPARATO: e' un diagnostico, "
                                "non una ri-misura.")'''

E_OLD = '''def cmd_run(a):'''

E_NEW = '''def _setup_maschera(a):
    """§3.2, record 24. Prepara la passata 1 o la 2 e stampa cosa aspettarsi."""
    if getattr(a, "mask_intersect_out", None) and getattr(a, "mask_fixed", None):
        sys.exit("[FATAL] --mask-intersect-out e --mask-fixed sono le due "
                 "passate dello stesso test e non si usano insieme.")
    one_point._mask_acc = True if getattr(a, "mask_intersect_out", None) else None
    one_point._mask_fixed = None
    one_point._d6_n = None
    if getattr(a, "mask_fixed", None):
        one_point._mask_fixed = np.load(a.mask_fixed)
        print("=" * 74)
        print("  §3.2 PASSATA 2 — maschera FISSA da %s" % a.mask_fixed)
        print("  voxel dell'intersezione: %d" % int(one_point._mask_fixed.sum()))
        print("  DICHIARATO PRIMA DEL RUN (record 24): l'intersezione e' piu'")
        print("  piccola di ogni singola maschera, quindi N_H1 SCENDE a ogni")
        print("  punto e il fiduciale NON riprodurra' 28256 / 15122. Non e' un")
        print("  difetto. Il cancello di riproduzione non si applica: c'e' D6.")
        print("  E' un DIAGNOSTICO del residuo, non una ri-misura di D.")
        print("=" * 74)
    elif getattr(a, "mask_intersect_out", None):
        print("=" * 74)
        print("  §3.2 PASSATA 1 — accumulo dell'AND, uscita in %s"
              % a.mask_intersect_out)
        print("  Nessun risultato si riporta da questa passata.")
        print("=" * 74)


def _scrivi_intersezione(a):
    acc = getattr(one_point, "_mask_acc", None)
    if getattr(a, "mask_intersect_out", None) and acc is not None and acc is not True:
        np.save(a.mask_intersect_out, acc)
        print("\\n  [§3.2] intersezione scritta in %s: %d voxel"
              % (a.mask_intersect_out, int(acc.sum())))


def cmd_run(a):
    _setup_maschera(a)'''

# La funzione che SCRIVE l'intersezione va anche CHIAMATA: definirla e basta
# lascerebbe la passata 1 ad accumulare senza produrre nulla. Va nel `finally`,
# cosi' scrive anche se un punto fallisce a meta'.
F_OLD = '''    finally:
        M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
        print("\\n[restore] geometria fiduciale ripristinata.")
    return 0'''

F_NEW = '''    finally:
        M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
        print("\\n[restore] geometria fiduciale ripristinata.")
        _scrivi_intersezione(a)
    return 0'''

EDITS = [
    ("A  due flag, --mask-intersect-out e --mask-fixed", D_OLD, D_NEW),
    ("E  e la scrittura dell'intersezione viene CHIAMATA", F_OLD, F_NEW),
    ("B  la maschera fissa si legge prima di build_mask", B_OLD, B_NEW),
    ("C  accumulo, sostituzione e CANCELLO D6", C_OLD, C_NEW),
    ("D  setup delle due passate in cmd_run", E_OLD, E_NEW),
]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    for name, old, new in EDITS:
        if s.count(old) != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, s.count(old)))
        s = s.replace(old, new, 1)
    return s


def _nomi_liberi(src, funcname):
    import ast
    import builtins
    tree = ast.parse(src)
    glob = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    glob |= {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            glob |= {(al.asname or al.name.split(".")[0]) for al in n.names}
        elif isinstance(n, ast.Assign):
            glob |= {t.id for t in ast.walk(n) if isinstance(t, ast.Name)}
    fn = next((f for f in ast.walk(tree)
               if isinstance(f, ast.FunctionDef) and f.name == funcname), None)
    if fn is None:
        return {"<funzione %s non trovata>" % funcname}
    bound = set(glob) | set(dir(builtins))
    a = fn.args
    for arg in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
        bound.add(arg.arg)
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            bound.add(extra.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound |= {(al.asname or al.name.split(".")[0]) for al in node.names}
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
            for arg in list(node.args.args) + list(node.args.kwonlyargs):
                bound.add(arg.arg)
        elif isinstance(node, ast.comprehension):
            bound |= {t.id for t in ast.walk(node.target) if isinstance(t, ast.Name)}
    usati = {node.id for node in ast.walk(fn)
             if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    return usati - bound


def _parses(src):
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        print("      [sintassi] %s" % exc)
        return False


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # 1-3: la semantica dell'intersezione, verificata e non asserita
    try:
        import numpy as np
        rng = np.random.default_rng(1)
        ms = [rng.random((12, 12, 12)) > 0.3 for _ in range(12)]
        acc = None
        for m in ms:
            acc = m.copy() if acc is None else (acc & m)
        chk("1  l'AND cumulativo e' l'intersezione dei dodici",
            np.array_equal(acc, np.all(np.stack(ms), axis=0)))
        chk("2  ed e' contenuta in OGNI maschera, quindi mai piu' grande",
            all(bool(np.all(m[acc])) for m in ms)
            and int(acc.sum()) <= min(int(m.sum()) for m in ms))
        chk("3  ed e' STRETTAMENTE piu' piccola: N_H1 scendera', come dichiarato",
            int(acc.sum()) < min(int(m.sum()) for m in ms),
            "%d contro il minimo %d" % (int(acc.sum()),
                                        min(int(m.sum()) for m in ms)))
    except Exception as exc:
        chk("1  semantica dell'intersezione", False, str(exc))

    ok = os.path.isfile(path)
    chk("4  runner dati presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("5  idempotenza: la modalita' non c'e' ancora",
        ("--mask-fixed" not in s) and ("D6" not in s))
    for i, (name, old, new) in enumerate(EDITS, start=6):
        c = s.count(old)
        chk("%-2d ancora %s" % (i, name), c == 1, "occorrenze=%d" % c)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("10 il risultato e' Python valido", _parses(out))
        chk("11 SCOPE: one_point, ogni nome legato",
            not _nomi_liberi(out, "one_point"),
            ", ".join(sorted(_nomi_liberi(out, "one_point"))))
        chk("12 SCOPE: _setup_maschera, ogni nome legato",
            not _nomi_liberi(out, "_setup_maschera"),
            ", ".join(sorted(_nomi_liberi(out, "_setup_maschera"))))
        chk("13 D6: tolleranza zero, cumulativo, arresto duro",
            ("D6: n_valid_voxels" in out) and ("Tolleranza zero, record 24" in out)
            and ("_d6_n" in out))
        chk("14 la maschera fissa e' verificata CONTENUTA in quella del punto",
            "non e' un'intersezione dei dodici punti" in out
            and "np.all(mask[_mfix])" in out)
        chk("15 cio' che non riprodurra' si STAMPA, non si ricorda",
            ("NON riprodurra' 28256" in out) and ("Non e' un" in out))
        chk("16 e che e' un DIAGNOSTICO, non una ri-misura",
            "DIAGNOSTICO del residuo, non una ri-misura" in out)
        chk("17 le due passate non si usano insieme",
            "non si usano insieme" in out)
        chk("18 e si distinguono in lettura: mask_pass nel record",
            out.count('rec["mask_pass"] = "derive"') == 1
            and out.count('rec["mask_pass"] = "fixed"') == 1)
        chk("19 senza flag il comportamento e' invariato",
            "_mask_acc = True if getattr(a, \"mask_intersect_out\", None) else None" in out
            and "if _acc is not None:" in out and "if _mfix is not None:" in out)
        chk("20 la regola esplicita 2.1-M resta verificata sulla maschera DERIVATA",
            out.index("Il 2.1-M vale per la seconda") < out.index("_acc = getattr"))
        # Il difetto che questo controllo esiste per prendere: definire
        # _scrivi_intersezione senza chiamarla lascerebbe la passata 1 ad
        # accumulare e non produrre nulla, in silenzio.
        chk("21 _scrivi_intersezione e' DEFINITA e anche CHIAMATA",
            out.count("def _scrivi_intersezione") == 1
            and out.count("        _scrivi_intersezione(a)") == 1)
        chk("22 ed e' nel finally, cosi' scrive anche se un punto fallisce",
            "_scrivi_intersezione(a)" in out.split("finally:")[1][:400])
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_maschera_intersezione_patch ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def cmd_apply(a):
    if selftest(a.path):
        print("")
        fail("selftest fallito: nessuna scrittura.")
    s = read(a.path)
    out = apply_all(s)
    diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                     fromfile="prima", tofile="dopo", n=2))
    print("\n=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff))
    print("righe: %d -> %d" % (s.count("\n"), out.count("\n")))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_intersezione"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("[backup] %s" % bak)
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    print(r"""
PRIMA:
  python src\paper2_fase3_runner_selftest.py     (se esiste)
  python src\paper2_runner_fase3.py selftest

POI, quattro comandi, un quarto d'ora in tutto.

Passata 1, deriva e interseca:
  python src\paper2_runner_fase3.py run --region NGC ^
      --mask-intersect-out results\paper2\mask_inter_NGC.npy ^
      --out results\paper2\fase3_maskpass1.jsonl
  python src\paper2_runner_fase3.py run --region SGC ^
      --mask-intersect-out results\paper2\mask_inter_SGC.npy ^
      --out results\paper2\fase3_maskpass1.jsonl

Passata 2, con l'intersezione fissa:
  python src\paper2_runner_fase3.py run --region NGC ^
      --mask-fixed results\paper2\mask_inter_NGC.npy ^
      --out results\paper2\fase3_intersezione.jsonl
  python src\paper2_runner_fase3.py run --region SGC ^
      --mask-fixed results\paper2\mask_inter_SGC.npy ^
      --out results\paper2\fase3_intersezione.jsonl

DA GUARDARE:
  - passata 2 deve stampare l'avviso, e n_valid_voxels deve essere IDENTICO ai
    dodici punti. Se D6 spara, fermati e mandami il messaggio.
  - N_H1 al fiduciale sara' MINORE di 28256 / 15122. E' atteso e dichiarato.
  - registri SEPARATI: fase3.jsonl non si tocca.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="§3.2 maschera-intersezione, record 24")
    p.add_argument("--path", default=DEFAULT_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(func=lambda a: 1 if selftest(a.path) else 0)
    ap = sub.add_parser("apply")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(func=cmd_apply)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

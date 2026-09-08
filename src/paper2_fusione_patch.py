#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_fusione_patch.py (rev.2) — corregge il difetto di fusione a valle.

REV.2: tolleranza per file. `paper2_due_lati.py` era gia' stato corretto ieri,
e la rev.1, tutto-o-niente, bloccava anche budget e analisi che il fix lo
devono ancora ricevere. Ora ogni file e' valutato da solo: 'da patchare',
'gia' corretto', 'assente' o 'ancore non trovate'. Solo l'ultimo caso ferma.

IL DIFETTO
  Dopo il run a k=2,3 il registro `fase3_mock.jsonl` contiene TRE record per
  (regione, indice), non uno:

    200 record x 11 punti, erosioni [0,1]   run principale
    200 record x  1 punto,  erosioni [0,1]   emendamento 15, il solo B6
    200 record x 12 punti,  erosioni [2,3]   run del 1 set 2026

  Tre script fondono i punti sostituendo il dizionario per punto invece di
  unirlo. Il record [2,3] e' l'ULTIMO per tutti e 400 gli indici, quindi
  sostituisce {N_H1_k0, N_H1_k1} con {N_H1_k2, N_H1_k3}:

    celle con N_H1_k0 sopravvissute: 0 su 2400, in entrambi gli emisferi.

  Nessuno dei tre mente in silenzio: cadono con KeyError su 'N_H1_k1'. Ma
  `due_lati.jsonl` e `fase3_budget.jsonl` sono stati generati PRIMA che il run
  appendesse, quindi i loro numeri restano validi e i due file NON vanno
  rigenerati finche' questa patch non e' applicata.

LA CORREZIONE
  Fusione per UNIONE al livello del singolo punto:

      d.setdefault(p, {}).update(v)      invece di      d[p] = v

  Cosi' N_H1_k0 e N_H1_k1 del primo record sopravvivono all'arrivo di
  N_H1_k2 e N_H1_k3 del terzo. L'appaiamento per indice non e' toccato.

COSA NON FA
  Non aggiunge --level: quello viene dopo, e richiede prima di sapere se il
  lato dati ha k=2 e k=3 nel suo ladder. Una cosa per volta.

Uso:
    python src\\paper2_fusione_patch.py selftest
    python src\\paper2_fusione_patch.py apply
    python src\\paper2_fusione_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

FILES = {
    "due_lati": os.path.join("src", "paper2_due_lati.py"),
    "budget": os.path.join("src", "paper2_fase3_budget.py"),
    "analisi": os.path.join("src", "paper2_fase3_analisi.py"),
}

MERGE_NOTE = ("# FUSIONE PER UNIONE, non per sostituzione (1 set 2026). Il registro ha\n"
              "        # piu' record per (regione, indice): 11 punti a k=0,1 dal run\n"
              "        # principale, il solo B6 dall'emendamento 15, e 12 punti a k=2,3.\n"
              "        # Sostituire il dizionario del punto perderebbe N_H1_k0 e N_H1_k1,\n"
              "        # perche' il record k=2,3 e' l'ultimo per tutti gli indici.\n")

EDITS = {
    "due_lati": [(
        "collect(): unione invece di last-wins",
        '''        for q, v in r["points"].items():
            M.setdefault(q, {})[r["index"]] = v''',
        '''        for q, v in r["points"].items():
            # FUSIONE PER UNIONE, non per sostituzione (1 set 2026). Il registro
            # ha piu' record per (regione, indice): 11 punti a k=0,1 dal run
            # principale, il solo B6 dall'emendamento 15, e 12 punti a k=2,3.
            # Sostituire il dizionario del punto perderebbe N_H1_k0 e N_H1_k1,
            # perche' il record k=2,3 e' l'ultimo per tutti gli indici.
            if isinstance(v, dict):
                M.setdefault(q, {}).setdefault(r["index"], {}).update(v)
            else:
                M.setdefault(q, {})[r["index"]] = v''')],
    "budget": [(
        "gather(): unione invece di last-wins",
        '''        for q, v in r["points"].items():
            mk.setdefault(q, {})[r["index"]] = v''',
        '''        for q, v in r["points"].items():
            # FUSIONE PER UNIONE: vedi paper2_fusione_patch.py, 1 set 2026.
            if isinstance(v, dict):
                mk.setdefault(q, {}).setdefault(r["index"], {}).update(v)
            else:
                mk.setdefault(q, {})[r["index"]] = v''')],
    "analisi": [(
        "load(): unione al livello del singolo punto",
        '''        d = by_idx.setdefault(r["index"], {"index": r["index"], "points": {}})
        d["points"].update(r["points"])''',
        '''        d = by_idx.setdefault(r["index"], {"index": r["index"], "points": {}})
        # `update` al livello del DIZIONARIO DEI PUNTI sostituisce il contenuto
        # di ogni punto gia' presente. Dopo il run a k=2,3 (1 set 2026) questo
        # perde N_H1_k0 e N_H1_k1, perche' quel record e' l'ultimo per tutti
        # gli indici. La fusione va fatta un livello piu' in basso.
        for _p, _v in r["points"].items():
            if isinstance(_v, dict):
                d["points"].setdefault(_p, {}).update(_v)
            else:
                d["points"][_p] = _v''')],
}


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def _parses(src):
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        print("      [sintassi] %s" % exc)
        return False


def apply_one(s, edits, label):
    for name, old, new in edits:
        if s.count(old) != 1:
            fail("ancora non unica in %s per '%s' (occorrenze=%d)"
                 % (label, name, s.count(old)))
        s = s.replace(old, new, 1)
    return s


def semantics_check():
    """La correzione deve fare quel che dice, su record che imitano i veri."""
    recs = [
        {"index": 7, "points": {p: {"N_H1_k0": 100.0, "N_H1_k1": 90.0}
                                for p in ("B1", "B5")}, "erosions": [0, 1]},
        {"index": 7, "points": {"B6": {"N_H1_k0": 80.0, "N_H1_k1": 70.0}},
         "erosions": [0, 1]},
        {"index": 7, "points": {p: {"N_H1_k2": 60.0, "N_H1_k3": 50.0}
                                for p in ("B1", "B5", "B6")}, "erosions": [2, 3]},
    ]
    lw, un = {}, {}
    for r in recs:
        for q, v in r["points"].items():
            lw.setdefault(q, {})[r["index"]] = v
            un.setdefault(q, {}).setdefault(r["index"], {}).update(v)
    lw_keys = sorted(lw["B1"][7])
    un_keys = sorted(un["B1"][7])
    b6_keys = sorted(un["B6"][7])
    return lw_keys, un_keys, b6_keys


def needed(path, label):
    """Un file va patchato solo se le sue ancore ci sono e non e' gia' corretto.
    Il tutto-o-niente della rev.1 bloccava anche i file sani: paper2_due_lati.py
    era gia' stato corretto ieri e ha impedito la scrittura sugli altri due."""
    if not os.path.isfile(path):
        return "assente"
    s = read(path)
    if "FUSIONE PER UNIONE" in s or 'setdefault(r["index"], {}).update' in s \
            or 'setdefault(_p, {}).update' in s:
        return "gia' corretto"
    if all(s.count(o) == 1 for _, o, _ in EDITS[label]):
        return "da patchare"
    return "ancore non trovate"


def selftest(paths):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    lw, un, b6 = semantics_check()
    chk("1  il difetto e' riprodotto: last-wins perde k0 e k1",
        lw == ["N_H1_k2", "N_H1_k3"], "last-wins -> %s" % lw)
    chk("2  l'unione li tiene tutti e quattro",
        un == ["N_H1_k0", "N_H1_k1", "N_H1_k2", "N_H1_k3"], "unione -> %s" % un)
    chk("3  e li tiene anche per B6, che arriva da un record separato",
        b6 == ["N_H1_k0", "N_H1_k1", "N_H1_k2", "N_H1_k3"], "B6 -> %s" % b6)

    n = 4
    todo = []
    for label, path in paths.items():
        st = needed(path, label)
        chk("%-2d %-9s -> %s" % (n, label, st),
            st in ("da patchare", "gia' corretto"), path)
        n += 1
        if st != "da patchare":
            continue
        todo.append(label)
        out = apply_one(read(path), EDITS[label], label)
        chk("%-2d %-9s: il risultato e' Python valido" % (n, label), _parses(out))
        n += 1
        chk("%-2d %-9s: l'appaiamento per indice non e' toccato" % (n, label),
            out.count('r["index"]') >= read(path).count('r["index"]'))
        n += 1
    chk("%-2d almeno un file da patchare" % n, bool(todo),
        "da patchare: %s" % (", ".join(todo) if todo else "nessuno"))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_fusione_patch ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def cmd_apply(a):
    paths = {k: getattr(a, k) for k in FILES}
    if selftest(paths):
        print("")
        fail("selftest fallito: nessuna scrittura. I file gia' corretti o assenti "
             "non fanno fallire nulla; fallisce solo un'ancora non trovata.")
    print("")
    for label, path in paths.items():
        st = needed(path, label)
        if st != "da patchare":
            print("=== %s: %s -> %s, salto ===\n" % (label, path, st))
            continue
        s = read(path)
        out = apply_one(s, EDITS[label], label)
        diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                         fromfile=label + " prima",
                                         tofile=label + " dopo", n=2))
        print("=== %s: %s (%d righe di diff) ===" % (label, path, len(diff)))
        sys.stdout.write("".join(diff))
        print("")
        if a.write:
            bak = path + ".pre_fusione"
            if not os.path.exists(bak):
                with open(bak, "w", encoding="utf-8", newline="") as f:
                    f.write(s)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(out)
            os.replace(tmp, path)
            print("[OK] %s aggiornato (backup in %s)" % (path, bak))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
    else:
        print("\nDopo la scrittura, nell'ordine:")
        print("  python src\\paper2_fase3_analisi.py selftest")
        print("  python src\\paper2_fase3_budget.py selftest")
        print("  python src\\paper2_due_lati.py selftest")
        print("  python src\\paper2_due_lati.py run --region NGC")
        print("Il run di due_lati deve riprodurre DD_max = -98.3 e -114.0.")
        print("Se non li riproduce, NON usare l'output: la fusione non e' quella.")
    return 0


def main():
    p = argparse.ArgumentParser(description="fusione per unione nei tre script a valle")
    for k, v in FILES.items():
        p.add_argument("--" + k, default=v)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(
        func=lambda a: 1 if selftest({k: getattr(a, k) for k in FILES}) else 0)
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

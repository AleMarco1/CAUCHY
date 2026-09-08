#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_gather_k23_patch.py — gather regge k=2,3 sul blocco A. Due difetti.

DIFETTO 1, IL CRASH
    KeyError: 'N_H1_k2'  in gather, riga 198

  Il blocco A ha sei punti e i quattro nuovi - A0, A1m, A3m, A0m - sono stati
  girati sul lato mock a erosioni 0 e 1 SOLTANTO, perche' servono al pavimento e
  il pavimento si calcola ai livelli del budget. gather li attraversa comunque.
  E' lo stesso difetto gia' corretto in selection_channel, nello stesso giorno,
  in un'altra funzione: il consumatore dava per scontato che ogni punto avesse
  ogni livello.

DIFETTO 2, PEGGIORE, ED E' SILENZIOSO
    dkey = "N_H1" if ki == 1 else "N_H1_k0"

  A ki = 2 e 3 questo prende il lato dati a k=0. Non solleva niente: produce un
  Delta D sbagliato, calcolato fra un lato mock a k=2 e un lato dati a k=0, e lo
  scrive nel registro come se fosse una misura. Un crash si vede; questo no.

  Il lato dati ha la scala completa nel campo `ladder`, con le chiavi '0', '1',
  '2', '3'. Si legge da li', e se manca ci si ferma invece di ripiegare su k=0.

TRE MODIFICHE
  A  una funzione _desi(p) che sceglie la fonte per livello, con arresto duro se
     la scala non ha il livello richiesto
  B  i punti del blocco A senza la chiave si SALTANO e si DICHIARANO, come in
     selection_channel
  C  la vecchia dkey sparisce, cosi' non puo' essere riusata per sbaglio

Uso:
    python src\\paper2_gather_k23_patch.py selftest
    python src\\paper2_gather_k23_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_budget.py")

A_OLD = '''    key = f"N_H1_k{ki}"
    dkey = "N_H1" if ki == 1 else "N_H1_k0"
    for p in BLOCK_A:
        if p not in D or p not in mk or "FID" not in mk:
            continue
        idx = sorted(set(mk[p]) & set(mk["FID"]))
        if len(idx) < 10:
            continue
        d = np.array([mk[p][i][key] - mk["FID"][i][key] for i in idx], float)
        dd = float(d.mean() - (D[p][dkey] - D["FID"][dkey]))'''

A_NEW = '''    key = f"N_H1_k{ki}"

    def _desi(p):
        """Lato dati al livello ki.

        A k=0 e k=1 i due campi piatti; a k=2 e k=3 la SCALA `ladder`. La forma
        precedente era `dkey = "N_H1" if ki == 1 else "N_H1_k0"`, che a ki=2,3
        prendeva il lato dati a k=0 SENZA DIRLO: un Delta D fra un lato mock a
        k=2 e un lato dati a k=0, scritto nel registro come una misura. Un crash
        si vede, quello no."""
        if ki == 1:
            return D[p]["N_H1"]
        if ki == 0:
            return D[p]["N_H1_k0"]
        lad = D[p].get("ladder") or {}
        if str(ki) not in lad or "N_H1" not in lad[str(ki)]:
            sys.exit(f"[FATAL] il lato dati non ha il livello k={ki} per {p}: "
                     f"la scala di erosione dei record del 3.1 non lo contiene. "
                     f"Non si ripiega su k=0.")
        return lad[str(ki)]["N_H1"]

    # I punti del blocco A senza la chiave sul lato mock si saltano e si
    # dichiarano: A0, A1m, A3m e A0m sono girati a erosioni 0 e 1 soltanto,
    # perche' servono al PAVIMENTO. Stesso trattamento di selection_channel.
    _senza = []
    for p in BLOCK_A:
        if p not in D or p not in mk or "FID" not in mk:
            continue
        idx = sorted(set(mk[p]) & set(mk["FID"]))
        idx = [i for i in idx if key in mk[p][i] and key in mk["FID"][i]]
        if len(idx) < 10:
            if p in mk:
                _senza.append(p)
            continue
        d = np.array([mk[p][i][key] - mk["FID"][i][key] for i in idx], float)
        dd = float(d.mean() - (_desi(p) - _desi("FID")))'''

B_OLD = '''            "n_mock": len(idx),
        })
    return rows'''

B_NEW = '''            "n_mock": len(idx),
        })
    if _senza:
        print(f"    [blocco A] {len(_senza)} punti saltati a k={ki}, senza "
              f"{key} sul lato mock: {', '.join(sorted(_senza))}. "
              f"Il pavimento a questo livello si calcola sui restanti.")
    return rows'''

EDITS = [
    ("A  _desi per livello, e il blocco A filtrato", A_OLD, A_NEW),
    ("B  i saltati si dichiarano", B_OLD, B_NEW),
]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    for name, old, new in EDITS:
        n = s.count(old)
        if n != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, n))
        s = s.replace(old, new, 1)
    return s


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

    # 1 — il difetto silenzioso, riprodotto: la vecchia dkey a ki=2 da' k=0
    def vecchia(ki):
        return "N_H1" if ki == 1 else "N_H1_k0"
    chk("1  il difetto SILENZIOSO e' riprodotto: a ki=2 la vecchia dkey da' k=0",
        vecchia(2) == "N_H1_k0" and vecchia(3) == "N_H1_k0",
        "nessun errore sollevato: un DD sbagliato finirebbe nel registro")
    chk("2  e a ki=0,1 era invece corretta: si conserva quel comportamento",
        vecchia(1) == "N_H1" and vecchia(0) == "N_H1_k0")

    ok = os.path.isfile(path)
    chk("3  budget presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("4  prerequisito: --levels e' gia' applicato", "--levels" in s)
    chk("5  idempotenza: la correzione non c'e' ancora",
        "def _desi(p):" not in s)
    for i, (name, old, new) in enumerate(EDITS, start=6):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("8  il risultato e' Python valido", _parses(out))
        # La vecchia forma resta nella DOCSTRING che spiega perche' e' stata
        # tolta: e' storia, non codice. Quel che conta e' che non sia piu' USATA.
        # Il controllo com'era sarebbe stato soddisfatto solo cancellando la
        # spiegazione - lo stesso inciampo dell'avviso di D5c.
        _codice = "\n".join(l for l in out.splitlines()
                            if not l.lstrip().startswith("#")
                            and "precedente era" not in l)
        chk("9  la vecchia dkey non e' piu' USATA (resta in docstring)",
            ("D[p][dkey]" not in out) and ("dkey =" not in _codice.split("def _desi")[0][-2000:])
            and ('dkey = "N_H1" if ki == 1' in out),
            "tolta dal codice, conservata come storia")
        chk("10 a k=2,3 si legge dalla SCALA, non da un campo piatto",
            'lad[str(ki)]["N_H1"]' in out)
        chk("11 e se la scala non ha il livello ci si FERMA, non si ripiega",
            ("Non si ripiega su k=0" in out)
            and ("sys.exit" in out.split("def _desi")[1][:900]))
        chk("12 i punti senza la chiave si filtrano PRIMA della media",
            "idx = [i for i in idx if key in mk[p][i]" in out
            and out.index("idx = [i for i in idx if key") < out.index("d = np.array("))
        chk("13 e i saltati si contano e si stampano, non spariscono",
            ("[blocco A]" in out) and ("punti saltati a k=" in out)
            and ("_senza.append(p)" in out))
        chk("14 a k=0,1 nulla cambia: tutti i punti hanno la chiave",
            'if ki == 1:' in out and 'return D[p]["N_H1"]' in out
            and 'return D[p]["N_H1_k0"]' in out)
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_gather_k23_patch ===")
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
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_gatherk23"
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
POI, e il primo comando e' il controllo che conta:
  python src\paper2_fase3_budget.py selftest
  python src\paper2_fase3_budget.py run --region NGC
  python src\paper2_fase3_budget.py run --region SGC

Senza --levels NULLA deve cambiare: pavimenti 32.96 / 51.13 / 27.51 / 34.61,
sistematico 41.9 / 60.3 / 53.7 / 42.1. La correzione tocca solo la scelta della
fonte, e a k=0,1 la fonte e' la stessa di prima.

E POI i quattro livelli:
  python src\paper2_fase3_budget.py run --region NGC --levels 1 0 2 3
  python src\paper2_fase3_budget.py run --region SGC --levels 1 0 2 3

A k=2 e k=3 devono comparire DUE righe:
  '[blocco A] 4 punti saltati a k=2 ... A0, A0m, A1m, A3m'
  '[k=2] Il budget a questo livello DESCRIVE e non CLASSIFICA'
Il pavimento a quei livelli si calcolera' sui DUE punti depositati, non sui sei:
i quattro nuovi non hanno quelle erosioni. Va detto quando lo si riporta.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="gather a k=2,3: fonte per livello e blocco A filtrato")
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

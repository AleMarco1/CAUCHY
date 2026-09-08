#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_item32e_patch.py - allinea paper2_item32e_surrogato.md all'esito del fit.

Il §3 e' gia' stato sostituito a mano ("firma confermata, non ritirata"). Restano
tre passaggi scritti PRIMA che il fitter girasse, e che ora lo contraddicono:

  1. §2, riga ~35 : "Nessuno script lo ricalcola."   -> non e' piu' vero.
                     Si tiene come STORIA, chiusa: e' la ragione per cui il
                     fitter e' stato scritto.
  2. §4, riga ~83 : "sostituiscono lo 0.082 con una quantita' ricalcolabile" e
                     "la firma non ne dipende piu'"  -> non lo sostituiscono, lo
                     CONFERMANO; e la firma ci dipende, ed e' confermata.
  3. §7, riga ~121: "il ritiro della firma numerica e la sua sostituzione con
                     l'ordinamento"  -> e' il testo vecchio.

I tre si muovono INSIEME o non si muovono: §2 e §7 stanno in punti distanti, e
un documento in cui §3 dice "confermata" e §7 dice "ritiro" e' peggio di uno
sbagliato in modo uniforme -- il lettore non sa quale dei due credere.

Sottocomandi
------------
  inspect / patch / verify / selftest.  Scrive solo con `patch --apply`.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "paper2_item32e_surrogato.md"


EDITS = [

    ("1. \u00a72: lo 0.082 aveva provenienza documentale (storia, chiusa)",
     "**Lo 0.082 voxel ha provenienza documentale, non di codice.** Sta in\n"
     "`paper2_item12a_emenda_gauge.md` in una tabella con il confronto fra gauge "
     "\u2014 0.165 vox (22.4%)\n"
     "vecchio contro 0.082 vox (14.5%) nuovo \u2014 ed \u00e8 ripreso da checklist 1.3, "
     "item 1.2b, item 1.4 e \u00a75.6\n"
     "della pre-registrazione. Nessuno script lo ricalcola.",
     "**Lo 0.082 voxel AVEVA provenienza documentale, non di codice.** Sta in\n"
     "`paper2_item12a_emenda_gauge.md` in una tabella con il confronto fra gauge "
     "\u2014 0.165 vox (22.4%)\n"
     "vecchio contro 0.082 vox (14.5%) nuovo \u2014 ed \u00e8 ripreso da checklist 1.3, "
     "item 1.2b, item 1.4 e \u00a75.6\n"
     "della pre-registrazione. **Nessuno script lo ricalcolava, ed \u00e8 la ragione "
     "per cui il fitter\n"
     "\u00e8 stato scritto.** Ora lo ricalcola, e il \u00a73 riporta l'esito.",
     "Nessuno script lo ricalcolava, ed"),

    ("2. \u00a74: il fitter CONFERMA lo 0.082, non lo sostituisce",
     "Il fitter produce **due** cose: i quattro residui a due parametri \u2014 che "
     "sostituiscono lo 0.082 con\n"
     "una quantit\u00e0 ricalcolabile \u2014 e i quattro `dc_tab` dei surrogati. Serve due "
     "volte, ed \u00e8 la ragione per\n"
     "cui si scrive nonostante la firma non ne dipenda pi\u00f9.",
     "Il fitter produce **due** cose: i quattro residui a due parametri \u2014 che "
     "**confermano** lo 0.082\n"
     "e gli danno provenienza di codice \u2014 e i quattro `dc_tab` dei surrogati. "
     "Serve due volte, ed \u00e8 la\n"
     "ragione per cui si scrive.",
     "**confermano** lo 0.082"),

    ("3. \u00a77: registrare la CONFERMA, non il ritiro",
     "Emendamento, **prima** del primo run, con: i quattro punti *C*_aff aggiunti "
     "alla griglia dichiarata,\n"
     "la definizione del surrogato, il **ritiro** della firma numerica e la sua "
     "sostituzione con\n"
     "l'ordinamento, la soglia al pavimento del blocco A, e i tre cancelli del "
     "fitter.",
     "Emendamento, **prima** del primo run, con: i quattro punti *C*_aff aggiunti "
     "alla griglia dichiarata,\n"
     "la definizione del surrogato, la **conferma** della firma numerica con la "
     "provenienza di codice\n"
     "ora stabilita, i quattro esponenti *p* e i quattro residui, la soglia al "
     "pavimento del blocco A,\n"
     "e i tre cancelli del fitter.",
     "la **conferma** della firma numerica"),
]


def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_target(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    txt = raw.decode("utf-8")
    n_crlf = txt.count("\r\n")
    n_lf = txt.count("\n") - n_crlf
    return txt, ("\r\n" if n_crlf >= n_lf else "\n"), n_crlf, n_lf


def norm(t):
    return t.replace("\r\n", "\n")


def plan(txt):
    n = norm(txt)
    ok, done, bad = [], [], []
    for name, old, new, marker in EDITS:
        if marker in n:
            done.append(name)
        elif n.count(old) == 1:
            ok.append(name)
        else:
            bad.append("%s: %d occorrenze dell'ancora" % (name, n.count(old)))
    return ok, done, bad


def apply_all(txt):
    ok, done, bad = plan(txt)
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    if not ok:
        return None, done
    if len(ok) != len(EDITS):
        fail("applicazione PARZIALE gia' presente (%s). I tre passaggi si "
             "muovono insieme: non proseguo." % ", ".join(done))
    n = norm(txt)
    for name, old, new, marker in EDITS:
        n = n.replace(old, new, 1)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    n = norm(txt)
    print("  §3 gia' corretto a mano: %s"
          % ("firma dichiarata: confermata, non ritirata" in n))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    if n_crlf and n_lf and not args.allow_eol_normalise:
        fail("fine riga MISTI (CRLF=%d, LF=%d): --allow-eol-normalise per procedere."
             % (n_crlf, n_lf))
    new_n, done = apply_all(txt)
    print("=== PATCH %s ===" % args.target)
    print("  sha256 prima : %s" % sha256_file(args.target))
    if new_n is None:
        print("  [OK] niente da fare (%s)." % ", ".join(done))
        return 0
    out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
    print("  %d -> %d byte, %d passaggi"
          % (len(txt.encode("utf-8")), len(out.encode("utf-8")), len(EDITS)))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".pre32e"
    if args.backup and not os.path.exists(bak):
        with open(bak, "wb") as fh:
            fh.write(txt.encode("utf-8"))
        print("  copia    : %s" % bak)
    tmp = args.target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(out.encode("utf-8"))
    os.replace(tmp, args.target)
    print("  sha256 dopo  : %s" % sha256_file(args.target))
    print("  [OK] scritto")
    return cmd_verify(args)


def cmd_verify(args):
    n = norm(read_target(args.target)[0])
    ok = True
    print("")
    print("=== VERIFY ===")
    checks = [
        ("§3 dice CONFERMATA", "confermata, non ritirata" in n),
        ("§2 non afferma piu' che nessuno script ricalcola",
         "Nessuno script lo ricalcola." not in n),
        ("§2 spiega perche' il fitter e' stato scritto",
         "\u00e8 la ragione per cui il fitter" in n),
        ("§4 dice CONFERMANO, non sostituiscono",
         "**confermano** lo 0.082" in n
         and "sostituiscono lo 0.082" not in n),
        ("§4 non dice piu' che la firma non ne dipende",
         "la firma non ne dipenda" not in n),
        ("§7 registra la conferma, non il ritiro",
         "la **conferma** della firma numerica" in n
         and "il **ritiro** della firma numerica" not in n),
        ("nessun 'ritiro'/'ritirata' residuo sulla firma",
         "ritiro** della firma" not in n and "RITIRATA" not in n),
        ("i quattro residui restano citati",
         all(v in n for v in ("0.0822", "0.0473", "0.0062", "0.0051"))),
        ("la soglia resta il pavimento del blocco A",
         "pavimento del blocco A" in n and "51.13" in n),
    ]
    for name, cond in checks:
        print("  [%s] %s" % ("ok" if cond else "NO", name))
        ok &= bool(cond)
    print("  esito: %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def cmd_selftest(args):
    import tempfile
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    corpo = ("# Item 3.2e\n\n## 2. blah\n\n"
             + EDITS[0][1] + "\n\n## 3. La firma dichiarata: confermata, non ritirata\n\n"
             "0.0822, 0.0473, 0.0062, 0.0051\n\n## 4. blah\n\n"
             + EDITS[1][1] + "\n\n## 5. soglia\n\npavimento del blocco A, 51.13\n\n"
             "## 7. Registrazione\n\n" + EDITS[2][1] + "\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "d_%s.md" % lab)
            with open(p, "wb") as fh:
                fh.write(corpo.replace("\n", eol).encode("utf-8"))

            txt, det, _, _ = read_target(p)
            chk("1%s fine riga rilevato" % lab, det == eol, repr(det))
            ok, done, bad = plan(txt)
            chk("2%s le tre ancore sono uniche" % lab,
                len(ok) == 3 and not bad, "ok=%d bad=%s" % (len(ok), bad))

            new_n, _ = apply_all(txt)
            out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
            with open(p, "wb") as fh:
                fh.write(out.encode("utf-8"))

            class A:
                target = p
            chk("3%s verify passa dopo la patch" % lab, cmd_verify(A()) == 0)
            chk("4%s fine riga preservati" % lab,
                (read_target(p)[0].count("\r\n") == 0) if eol == "\n"
                else (read_target(p)[0].count("\n")
                      == read_target(p)[0].count("\r\n")))
            ok2, done2, bad2 = plan(read_target(p)[0])
            chk("5%s idempotenza" % lab, not ok2 and not bad2,
                "ok=%s bad=%s" % (ok2, bad2))

        # applicazione parziale: DEVE fermarsi
        p2 = os.path.join(td, "parziale.md")
        parziale = corpo.replace(EDITS[2][1], EDITS[2][2])
        with open(p2, "wb") as fh:
            fh.write(parziale.encode("utf-8"))
        chk("6  applicazione parziale gia' presente: si ferma",
            _exits(lambda: apply_all(read_target(p2)[0])))

        # ancora mancante: DEVE segnalare
        p3 = os.path.join(td, "rotto.md")
        with open(p3, "wb") as fh:
            fh.write(corpo.replace("Nessuno script lo ricalcola.",
                                   "altro testo.").encode("utf-8"))
        _, _, bad3 = plan(read_target(p3)[0])
        chk("7  ancora mancante: segnalata", len(bad3) == 1, str(bad3))

    print("=== SELFTEST paper2_item32e_patch ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def _exits(fn):
    try:
        fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(
        description="Allinea l'item 3.2e all'esito del fit del surrogato")
    p.add_argument("--target", default=DEFAULT_TARGET)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    pa = sub.add_parser("patch")
    pa.add_argument("--apply", action="store_true")
    pa.add_argument("--backup", action="store_true", default=True)
    pa.add_argument("--allow-eol-normalise", action="store_true")
    pa.set_defaults(func=cmd_patch)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_risposta_46b_patch.py - aggiunge al §4.6 la sottosezione sulla scala
geometrica del ripattern, e sul perche' quel numero dica meno di quanto sembri.

UNA SOLA MODIFICA, e la ragione per cui e' una sola
---------------------------------------------------
La sottosezione entra prima di «Cosa questo NON stabilisce». Non tocca la
tabella finale ne' la Risposta 8: il verdetto del §4.6 non cambia, e non deve
sembrare che cambi.

COSA DICE, E COSA NON DICE PIU'
-------------------------------
La prima lettura di questi numeri era: NGC ha poco ripattern e nessun effetto,
SGC ne ha quasi totale ed e' l'unico a 2 sigma; quindi il ripattern spiega la
differenza fra emisferi. Lo SCAN la falsifica. Traslando in blocco entrambe le
griglie di una frazione di cella del box -- una scelta arbitraria, che lascia
invariato lo spostamento RELATIVO fra B1 e B5 -- la frazione spazia fra 0 e 15%
in NGC e fra 0 e 100% in SGC. Il contrasto apparente fra emisferi e' in gran
parte un accidente della fase.

Sopravvive lo spostamento RELATIVO di box_min, 0.0076 contro 0.3822 voxel: un
fattore cinquanta, indipendente dalla fase.

La sottosezione riporta entrambe le cose, e la seconda come limite della prima.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"

ANCHOR = "### Cosa questo NON stabilisce\n"

BLOCCO = '''### Quanto ripattern c'\u00e8, e quanto poco quel numero dica

Il rilievo nomina una quantit\u00e0 che prima non esisteva: **quanto** cambia la mappa di assegnazione
sotto deformazione. \u00c8 calcolabile senza generare un solo mock, ed \u00e8 stata calcolata.

La deformazione sposta la griglia rispetto al reticolo del box periodico di **0.0076 voxel** in NGC
e **0.3822** in SGC \u2014 un fattore cinquanta. La frazione di voxel in-survey la cui **cella sorgente
cambia** fra B1 e B5 vale **12.76%** in NGC e **92.66%** in SGC, su 306 166 e 168 596 voxel comuni.

**Ma quei due numeri non sono robusti, e lo diciamo perch\u00e9 l'abbiamo verificato.** Traslando in
blocco *entrambe* le griglie di una frazione di cella del box \u2014 una scelta arbitraria, che dipende
da dove `derive_box` colloca l'origine dell'embedding e che lascia **invariato** lo spostamento
relativo fra i due punti \u2014 la frazione spazia fra 0 e 15% in NGC e fra **0 e 100%** in SGC, con
mediana 0% e 11%. Su un solo passo del reticolo copre l'intero intervallo possibile.

Il contrasto apparente fra i due emisferi \u00e8 quindi in gran parte un **accidente della fase**, e non
si presta a spiegare perch\u00e9 l'effetto misurato compaia in SGC e non in NGC. Sopravvive alla verifica
solo lo **spostamento relativo**, che della fase non dipende: 0.0076 contro 0.3822 voxel.

La quantit\u00e0 era stata dichiarata **descrittiva e senza soglia prima di calcolarla** (item 3.2d, §5),
e resta tale: il verdetto del §4.6 \u00e8 quello del run, non questo. La riportiamo con il suo intervallo
perch\u00e9 il rilievo chiedeva di quantificarla \u2014 e quantificarla mostra che non \u00e8 la leva che sembrava.

'''

EDITS = [
    ("1. sottosezione sulla scala geometrica del ripattern",
     ANCHOR,
     BLOCCO + ANCHOR,
     "### Quanto ripattern c'\u00e8, e quanto poco quel numero dica"),
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


def piatto(t):
    """Spazi collassati. Un controllo che cerca una frase la quale ATTRAVERSA un
    fine riga non la trova: regola gia' registrata, e violata di nuovo qui."""
    return " ".join(norm(t).split())


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
    print("  prerequisito: il \u00a74.6 esiste ed \u00e8 [SCRITTA]: %s"
          % ("## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]**" in n))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    if "## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]**" not in n:
        fail("il \u00a74.6 non c'e' ancora: lancia prima paper2_risposta_46_patch.py. "
             "Una sottosezione senza la sua sezione non ha dove stare.")
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
    print("  %d -> %d byte" % (len(txt.encode("utf-8")), len(out.encode("utf-8"))))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".pre46b"
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
    f = piatto(n)
    ok = True
    print("")
    print("=== VERIFY ===")
    checks = [
        ("la sottosezione esiste",
         "### Quanto ripattern c'\u00e8" in n),
        ("sta DENTRO il \u00a74.6",
         "## \u00a74.6" in n
         and n.index("## \u00a74.6") < n.index("### Quanto ripattern c'\u00e8")),
        ("precede «Cosa questo NON stabilisce»",
         n.index("### Quanto ripattern c'\u00e8")
         < n.index("### Cosa questo NON stabilisce")),
        ("i due spostamenti relativi ci sono",
         "0.0076 voxel" in n and "0.3822" in n),
        ("le due frazioni ci sono", "12.76%" in n and "92.66%" in n),
        ("l'intervallo dello scan \u00e8 riportato",
         "0 e 15%" in n and "0 e 100%" in n),
        ("dice che il contrasto \u00e8 un accidente della fase",
         "accidente della fase" in f and "non si presta a spiegare" in f),
        ("dice che lo spostamento relativo SOPRAVVIVE",
         "Sopravvive alla verifica solo lo" in f),
        ("richiama che la quantit\u00e0 era dichiarata descrittiva PRIMA",
         "prima di calcolarla" in n),
        ("il verdetto del \u00a74.6 non cambia",
         "il verdetto del \u00a74.6 \u00e8 quello del run" in n),
        ("il resto del \u00a74.6 \u00e8 intatto",
         "\u0394_ripattern" in n or "+6.96" in n),
        ("la tabella finale non \u00e8 stata toccata",
         "| \u00a74.6 | **[SCRITTA]** | chiusa da una misura" in n),
    ]
    for name, cond in checks:
        print("  [%s] %s" % ("ok" if cond else "NO", name))
        ok &= bool(cond)
    print("  esito: %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def cmd_selftest(args):
    import tempfile
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    corpo = ("# Risposta\n\n"
             "## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]**\n\n"
             "\u0394_ripattern +6.96 e il resto della sezione.\n\n"
             + ANCHOR + "\ntesto finale\n\n"
             "## Sezioni ancora aperte\n\n"
             "| \u00a74.6 | **[SCRITTA]** | chiusa da una misura, emendamento 44 |\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "r_%s.md" % lab)
            with open(p, "wb") as fh:
                fh.write(corpo.replace("\n", eol).encode("utf-8"))
            txt, det, _, _ = read_target(p)
            chk("1%s fine riga rilevato" % lab, det == eol, repr(det))
            ok, done, bad = plan(txt)
            chk("2%s ancora unica" % lab, len(ok) == 1 and not bad,
                "ok=%d bad=%s" % (len(ok), bad))
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
            ok2, _, bad2 = plan(read_target(p)[0])
            chk("5%s idempotenza" % lab, not ok2 and not bad2,
                "ok=%s bad=%s" % (ok2, bad2))

        # senza il §4.6 la patch DEVE rifiutare
        p2 = os.path.join(td, "senza46.md")
        with open(p2, "wb") as fh:
            fh.write(("# Risposta\n\n" + ANCHOR + "\ntesto\n").encode("utf-8"))

        class B:
            target = p2
            apply = False
            backup = False
            allow_eol_normalise = False
        chk("6  senza il \u00a74.6 la patch rifiuta", _exits(lambda: cmd_patch(B())))

    # i numeri del blocco vengono dai registri, non dalla memoria
    for v in ("0.0076", "0.3822", "12.76%", "92.66%", "306\u2009166", "168 596"):
        pass
    chk("7  il blocco cita i due spostamenti e le due frazioni",
        all(v in BLOCCO for v in ("0.0076", "0.3822", "12.76%", "92.66%")))
    chk("7b il blocco cita l'intervallo dello scan, non solo il valore",
        "0 e 15%" in BLOCCO and "0 e 100%" in BLOCCO
        and "mediana 0% e 11%" in BLOCCO)
    fb = piatto(BLOCCO)
    chk("7c il blocco NON attribuisce la differenza fra emisferi al ripattern",
        "non si presta a spiegare" in fb and "accidente della fase" in fb,
        "confronto su testo con spazi collassati")

    print("=== SELFTEST paper2_risposta_46b_patch ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def _exits(fn):
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(
        description="Aggiunge al \u00a74.6 la scala geometrica del ripattern")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", default=DEFAULT_TARGET)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect", parents=[common]).set_defaults(func=cmd_inspect)
    sub.add_parser("verify", parents=[common]).set_defaults(func=cmd_verify)
    sub.add_parser("selftest", parents=[common]).set_defaults(func=cmd_selftest)
    pa = sub.add_parser("patch", parents=[common])
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

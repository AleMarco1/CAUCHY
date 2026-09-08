#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_36_patch.py - l'item 3.6 passa da [~] a [x].

Il lato mock ai livelli 2 e 3 mancava su quattro punti del blocco A -- A0, A0m,
A1m, A3m -- ed erano l'ultimo pezzo. Sono stati girati, il budget ha girato ai
quattro livelli, e il pavimento poggia su SEI punti ovunque.

La voce non si limita a spuntare: riporta il cancello di riproduzione, i due
pavimenti nuovi, e il fatto che la COPERTURA del non attribuito crolla sopra
k=1 -- che e' un vincolo sul §A.2 del secondo report e non era nel disegno.

Due modifiche: la voce 3.6, e il rimando in Fase 7 punto 5 dove il crollo della
copertura va ripreso in scrittura. Si muovono insieme: una voce chiusa che
produce un fatto nuovo senza un posto dove riprenderlo e' un fatto perso.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "checklist_paper2.md"
M = "\u2726\u2726\u2726\u2727"

I36_V = (
    "- [~] **\u2726\u2727 3.6 \u2014 Erosione per punto. LATO MOCK DA COMPLETARE**, con predizione dichiarata.\n"
    "      **\u2726\u2726\u2726\u2727 Aggiornamento rev. 3.18:** i livelli 2 e 3 **esistono al fiduciale** dal record 26")

I36_N = (
    "- [x] **\u2726\u2727 3.6 \u2014 Erosione per punto. COMPLETATA**, 6 set 2026, emendamento 49.\n"
    "      **\u2726\u2726\u2726\u2727 Esito (rev. 3.18).** Mancava il lato mock a *k*=2,3 su quattro punti del blocco A\n"
    "      \u2014 A0, A0m, A1m, A3m \u2014 ed erano l'ultimo pezzo. Girati con 200 realizzazioni per emisfero:\n"
    "      il pavimento poggia ora su **sei punti a tutti e quattro i livelli**, e il budget non\n"
    "      \u00abdescrive e non classifica\u00bb per mancanza di punti.\n"
    "\n"
    "      **Il cancello di riproduzione \u00e8 passato:** a *k*=0 e *k*=1 il pavimento \u00e8 **identico** al\n"
    "      depositato \u2014 51.13 e 32.96 in NGC, 34.61 e 27.51 in SGC. Quei livelli non hanno guadagnato\n"
    "      punti e non dovevano muoversi. Verificare i livelli che **non** devono cambiare \u00e8 ci\u00f2 che\n"
    "      rende credibili i due nuovi: 44.76 e 20.59 in NGC, 12.48 e 6.05 in SGC.\n"
    "\n"
    "      **E un fatto che il disegno non prevedeva: la COPERTURA del non attribuito crolla.** Il\n"
    "      \u00a7A.2 del secondo report identifica il residuo non attribuito con la struttura a singola\n"
    "      realizzazione del lato dati, e cita l'80\u201386% di copertura del pavimento come prova. A\n"
    "      *k*=0,1 c'\u00e8: 86%, 80%, 83%, 52%. A *k*=2,3 diventa **85%, 44%, 26% e 10%**. O\n"
    "      l'identificazione vale solo dove il pavimento \u00e8 grande \u2014 e allora A.2 \u00e8 un'osservazione a\n"
    "      *k*=0,1, non una spiegazione \u2014 oppure il pavimento perde potere con l'erosione e il\n"
    "      residuo contiene qualcosa che il blocco A a quei livelli non vede. **Otto numeri non le\n"
    "      separano.** Si riprende in Fase 7, punto 5.\n"
    "\n"
    "      *(Resta vero che a k=2,3 il budget non emette esito E1\u2013E4: le soglie depositate sono\n"
    "      tarate sul deficit a k=0,1, quindi non c'\u00e8 un verdetto a cui applicare un pavimento. Sei\n"
    "      punti invece di due fanno del pavimento una misura migliore, non un verdetto.)*\n"
    "\n"
    "      *(Storia, rev. 3.18 prima del completamento:)* i livelli 2 e 3 **esistono al fiduciale** dal record 26")

F7_V = (
    "   **\u2726\u2726\u2726\u2727 Da sciogliere qui (item 3.10):** \u0394*D*_max \u00e8 definito come B5 \u2212 B1, e a *k* = 0 in")

F7_N = (
    "   **\u2726\u2726\u2726\u2727 Da riprendere qui (item 3.6, emendamento 49):** la copertura del non attribuito da\n"
    "   parte del pavimento del blocco A vale 86%, 80%, 83% e 52% a *k*=0,1 e **85%, 44%, 26% e 10%**\n"
    "   a *k*=2,3. Il \u00a7A.2 del secondo report costruisce su quella copertura l'identificazione fra\n"
    "   residuo non attribuito e struttura a singola realizzazione del lato dati. **L'identificazione\n"
    "   non si estende ai livelli alti**, e le due letture possibili \u2014 vale solo dove il pavimento \u00e8\n"
    "   grande, oppure il pavimento perde potere con l'erosione \u2014 non sono separate da questi otto\n"
    "   numeri. Va detto nel paper con entrambe le letture, non con una sola.\n"
    "\n"
    "   **\u2726\u2726\u2726\u2727 Da sciogliere qui (item 3.10):** \u0394*D*_max \u00e8 definito come B5 \u2212 B1, e a *k* = 0 in")

EDITS = [
    ("1. item 3.6 a [x]", I36_V, I36_N, "3.6 \u2014 Erosione per punto. COMPLETATA"),
    ("2. Fase 7: dove riprendere il crollo della copertura", F7_V, F7_N,
     "Da riprendere qui (item 3.6, emendamento 49)"),
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
    """Spazi collassati, prefissi `>` tolti E minuscole. Il maiuscolo di enfasi
    ha gia' fatto fallire controlli sani tre volte in questa sessione."""
    righe = [l.lstrip().lstrip(">").strip() for l in norm(t).split("\n")]
    return " ".join(" ".join(righe).split()).lower()


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
        fail("applicazione PARZIALE gia' presente (%s): non proseguo."
             % ", ".join(done))
    n = norm(txt)
    for name, old, new, marker in EDITS:
        n = n.replace(old, new, 1)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  righe     : %d" % len(n.splitlines()))
    print("  rev. 3.18 gia' applicata: %s" % ("### rev. 3.18" in n))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    if "### rev. 3.18" not in n:
        fail("la rev. 3.18 non c'e' ancora: lancia prima "
             "paper2_checklist_318.py. Queste voci usano il suo marcatore, e "
             "un marcatore senza il suo changelog non si sa cosa significhi.")
    if n_crlf and n_lf and not args.allow_eol_normalise:
        fail("fine riga MISTI (CRLF=%d, LF=%d): --allow-eol-normalise."
             % (n_crlf, n_lf))
    new_n, done = apply_all(txt)
    print("=== PATCH %s ===" % args.target)
    print("  sha256 prima : %s" % sha256_file(args.target))
    if new_n is None:
        print("  [OK] niente da fare (%s)." % ", ".join(done))
        return 0
    out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
    print("  %d -> %d righe, 2 modifiche"
          % (len(n.splitlines()), len(new_n.splitlines())))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".pre36"
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
        ("3.6 e' [x] e COMPLETATA",
         "- [x] **\u2726\u2727 3.6" in n and "LATO MOCK DA COMPLETARE" not in n),
        ("cita l'emendamento 49", "emendamento 49" in f),
        ("i quattro punti girati sono nominati",
         "a0, a0m, a1m, a3m" in f),
        ("il pavimento e' su sei punti a tutti i livelli",
         "sei punti a tutti e quattro i livelli" in f),
        ("il cancello di riproduzione e' riportato",
         "cancello di riproduzione \u00e8 passato" in f
         and "51.13 e 32.96" in n and "34.61 e 27.51" in n),
        ("e spiega PERCHE' verificare cio' che non deve cambiare",
         "non dovevano muoversi" in f),
        ("i due pavimenti nuovi ci sono", "44.76 e 20.59" in n and "12.48 e 6.05" in n),
        ("il crollo della copertura e' riportato con gli otto numeri",
         "85%, 44%, 26% e 10%" in n and "86%, 80%, 83%, 52%" in n),
        ("le DUE letture restano aperte", "otto numeri non le" in f),
        ("resta vero che k=2,3 non classifica",
         "non emette esito e1\u2013e4" in f),
        ("la storia precedente non e' cancellata",
         "storia, rev. 3.18 prima del completamento" in f),
        ("il punto di ripresa e' in Fase 7",
         "Da riprendere qui (item 3.6" in n),
        ("e non ha scalzato quello del 3.10",
         "Da sciogliere qui (item 3.10)" in n
         and n.index("Da riprendere qui (item 3.6") < n.index("Da sciogliere qui (item 3.10)")),
        ("il marcatore della 3.18 e' sulle voci nuove (>=3)", n.count(M) >= 3),
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

    corpo = ("# Checklist\n### rev. 3.18 \u2014 5 settembre\n\n## Fase 3\n\n"
             + I36_V + " \u2014 reseed FID-only.\n\n"
             "## Fase 7 \u2014 Scrittura\n\n### Struttura\n\n"
             "5. Risposta AP del deficit.\n"
             + F7_V + "\n   NGC B1 sta +153.2.\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "c_%s.md" % lab)
            with open(p, "wb") as fh:
                fh.write(corpo.replace("\n", eol).encode("utf-8"))
            txt, det, _, _ = read_target(p)
            chk("1%s fine riga rilevato" % lab, det == eol, repr(det))
            ok, done, bad = plan(txt)
            chk("2%s le due ancore sono uniche" % lab,
                len(ok) == 2 and not bad, "ok=%d bad=%s" % (len(ok), bad))
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

        p2 = os.path.join(td, "senza318.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace("### rev. 3.18 \u2014 5 settembre",
                                   "### rev. 3.17").encode("utf-8"))

        class B:
            target = p2
            apply = False
            backup = False
            allow_eol_normalise = False
        chk("6  senza la rev. 3.18 la patch rifiuta", _exits(lambda: cmd_patch(B())))

        p3 = os.path.join(td, "parziale.md")
        with open(p3, "wb") as fh:
            fh.write(corpo.replace(I36_V, I36_N).encode("utf-8"))
        chk("7  applicazione parziale: si ferma",
            _exits(lambda: apply_all(read_target(p3)[0])))

    chk("8  3.6 diventa [x], non resta [~]", I36_N.startswith("- [x]"))
    chk("8b la storia precedente e' conservata, non cancellata",
        "Storia, rev. 3.18 prima del completamento" in I36_N
        and "esistono al fiduciale" in I36_N)
    chk("9  il rimando di Fase 7 nomina l'item e l'emendamento",
        "item 3.6, emendamento 49" in F7_N)
    chk("9b e chiede ENTRAMBE le letture, non una",
        "con entrambe le letture, non con una sola" in F7_N)

    print("=== SELFTEST paper2_checklist_36_patch ===")
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
    p = argparse.ArgumentParser(description="Item 3.6 a [x], e il rimando in Fase 7")
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

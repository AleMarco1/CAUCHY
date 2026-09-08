#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_item34_patch.py - i quattro item della Fase 3 che il changelog
della rev. 3.17 contraddice, e il rimando in Fase 7 per il 3.10.

  1. 3.7 da [ ] a [x]: il trattamento (B) e' stato ESEGUITO, record 38, e la
     rev. 3.17 punto 4 lo racconta. La casella non era stata mossa.
  2. 3.8 da [ ] a [x]: la linea B in spazio reale idem, record 37, rev. 3.17
     punto 2.
  3. 3.6 resta [~] -- non e' completo su tutti i punti -- ma il testo dice
     ancora «il lato mock ha k = 0 e 1», e i livelli 2 e 3 esistono al
     fiduciale dal record 26.
  4. 3.10 da [ ] a [~]: RIMANDATO con una data, non lasciato aperto senza. E
     il punto dove riprenderlo entra nella struttura della Fase 7.

Aggiornare i changelog e non le caselle e' come registrare un run e non
depositarne il risultato: il documento dice due cose diverse a due lettori
diversi. Le quattro modifiche si muovono insieme.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "checklist_paper2.md"
M = "\u2726\u2726\u2726\u2727"          # marcatore della rev. 3.18

I36_V = "- [~] **\u2726\u2727 3.6 \u2014 Erosione per punto. LATO MOCK DA COMPLETARE**, con predizione dichiarata."
I36_N = ("- [~] **\u2726\u2727 3.6 \u2014 Erosione per punto. LATO MOCK DA COMPLETARE**, con predizione dichiarata.\n"
         "      **\u2726\u2726\u2726\u2727 Aggiornamento rev. 3.18:** i livelli 2 e 3 **esistono al fiduciale** dal record 26\n"
         "      \u2014 reseed FID-only, 1.49 h + 1.48 h, 200 realizzazioni per emisfero \u2014 e il budget gira a\n"
         "      **quattro livelli** dal record 41. Manca il lato mock ai livelli 2 e 3 sugli **altri** punti,\n"
         "      quindi il pavimento a *k*=2,3 poggia su **due** punti invece che sei e a quei livelli il\n"
         "      budget **descrive e non classifica**. La tilde resta per questo.")

I37_V = ("- [ ] **\u2726\u2727\u2727 3.7 \u2014 Trattamento (B), osservabili fisse. DA ESEGUIRE**, perimetro e cancelli fissati\n"
         "      dal record 16 prima che il primo punto giri.")
I37_N = ("- [x] **\u2726\u2727\u2727 3.7 \u2014 Trattamento (B), osservabili fisse. ESEGUITO**, 3\u20134 set 2026, record 38.\n"
         "      **\u2726\u2726\u2726\u2727 Esito (rev. 3.18):** tutti e quattro i cancelli superati \u2014 D5a muto, 400 celle\n"
         "      fiduciali bit-identiche, D5b esatto sui quattro valori del record 21, `n_sel` costante ai sei\n"
         "      punti in 400 realizzazioni su 400, D5c massimo 8 contro soglia 28. Il fattore fra i due lati\n"
         "      si muove di **\u00b110%**: il terzo meccanismo candidato \u00e8 **escluso**. E le SEM sono pi\u00f9 piccole\n"
         "      che sotto (A): misura migliore, predizione che fallisce lo stesso.\n"
         "      Perimetro e cancelli erano fissati dal record 16 prima che il primo punto girasse.")

I38_V = "- [ ] **\u2726\u2727\u2727 3.8 \u2014 Linea B in spazio reale: falsificazione del meccanismo. DA ESEGUIRE.**"
I38_N = ("- [x] **\u2726\u2727\u2727 3.8 \u2014 Linea B in spazio reale: falsificazione del meccanismo. ESEGUITO**, 3 set\n"
         "      2026, record 37.\n"
         "      **\u2726\u2726\u2726\u2727 Esito (rev. 3.18):** il rapporto fra i due lati si muove di **\u00b113%** togliendo\n"
         "      l'RSD del tutto: il meccanismo scritto nel record 16 \u00e8 **falsificato**, e il clipping risulta\n"
         "      **interamente RSD** \u2014 zero clippati su 2400 in spazio reale. Il primo tentativo fu un run\n"
         "      **NULLO** (record 35), e da li' viene la regola sui flag verificati da numeri diversi.")

I310_V = "- [ ] **\u2726\u2727\u2726 3.10 \u2014 B1 \u00e8 anomalo a *k* = 0 in NGC. DA DECIDERE COME RIPORTARLO.**"
I310_N = ("- [~] **\u2726\u2727\u2726 3.10 \u2014 B1 \u00e8 anomalo a *k* = 0 in NGC. RIMANDATO, con una data.**\n"
          "      **\u2726\u2726\u2726\u2727 rev. 3.18:** \u00e8 una decisione di **scrittura**, non un run, e dipende da come il\n"
          "      \u00a71 della risposta presenta \u0394*D*_max \u2014 sezione appena riscritta. Deciderla a caldo\n"
          "      significa deciderla male. **Si scioglie in Fase 7, punto 5, prima della sottomissione della\n"
          "      revisione** e non prima della risposta al referee: la risposta non ne dipende.")

F7_V = ("5. Risposta AP del deficit: decomposizione a cinque contributi, ranghi empirici.")
F7_N = ("5. Risposta AP del deficit: decomposizione a cinque contributi, ranghi empirici.\n"
        "   **\u2726\u2726\u2726\u2727 Da sciogliere qui (item 3.10):** \u0394*D*_max \u00e8 definito come B5 \u2212 B1, e a *k* = 0 in\n"
        "   NGC B1 sta **+153.2 \u00b1 11.7** contro il fiduciale \u2014 13\u03c3 \u2014 mentre B2, B4, B5 e B6 stanno entro\n"
        "   \u00b140. Il numero che classifica E2 a quel livello \u00e8 quindi **dominato dal punto pi\u00f9 fuori\n"
        "   linea**, non da una risposta liscia alla deformazione. A *k* = 1 il quadro \u00e8 diverso e a\n"
        "   *k* = 2 \u00e8 monotono. **Decidere come riportarlo prima di sottomettere la revisione.**")

EDITS = [
    ("1. item 3.6, testo aggiornato", I36_V, I36_N, "Aggiornamento rev. 3.18"),
    ("2. item 3.7 a [x]", I37_V, I37_N, "3.7 \u2014 Trattamento (B), osservabili fisse. ESEGUITO"),
    ("3. item 3.8 a [x]", I38_V, I38_N, "3.8 \u2014 Linea B in spazio reale: falsificazione del meccanismo. ESEGUITO"),
    ("4. item 3.10 a [~], rimandato con una data", I310_V, I310_N,
     "3.10 \u2014 B1 \u00e8 anomalo a *k* = 0 in NGC. RIMANDATO"),
    ("5. Fase 7 punto 5: dove riprendere il 3.10", F7_V, F7_N,
     "Da sciogliere qui (item 3.10)"),
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
    righe = [l.lstrip().lstrip(">").strip() for l in norm(t).split("\n")]
    return " ".join(" ".join(righe).split())


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
    print("  %d -> %d righe, 5 modifiche"
          % (len(n.splitlines()), len(new_n.splitlines())))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".pre34"
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
        ("3.7 e' [x] ed ESEGUITO",
         "- [x] **\u2726\u2727\u2727 3.7" in n and "DA ESEGUIRE**, perimetro" not in n),
        ("3.7 riporta l'esito e il record",
         "record 38" in f and "\u00b110%" in f),
        ("3.8 e' [x] ed ESEGUITO",
         "- [x] **\u2726\u2727\u2727 3.8" in n),
        ("3.8 riporta l'esito e il record",
         "record 37" in f and "\u00b113%" in f and "interamente RSD" in f),
        ("3.6 resta [~] e dice cosa c'e' ora",
         "- [~] **\u2726\u2727 3.6" in n and "esistono al fiduciale" in f
         and "descrive e non classifica" in f),
        ("3.10 e' [~] e RIMANDATO con una data",
         "- [~] **\u2726\u2727\u2726 3.10" in n and "RIMANDATO, con una data" in n
         and "prima della sottomissione della revisione" in f),
        ("e dice che la risposta al referee NON ne dipende",
         "la risposta non ne dipende" in f),
        ("il punto di ripresa e' in Fase 7", "Da sciogliere qui (item 3.10)" in n),
        ("e sta nel punto 5 della struttura",
         n.index("Da sciogliere qui (item 3.10)") > n.index("## Fase 7 \u2014 Scrittura")),
        ("i numeri di B1 sono nel punto di ripresa",
         "+153.2 \u00b1 11.7" in n.split("## Fase 7")[-1]),
        ("nessun item della Fase 3 resta DA ESEGUIRE",
         "3.7 \u2014 Trattamento (B), osservabili fisse. DA ESEGUIRE" not in n
         and "3.8 \u2014 Linea B in spazio reale: falsificazione del meccanismo. DA ESEGUIRE" not in n),
        # cinque: le cinque voci toccate. Nel file vero ce ne sono di piu',
        # perche' il changelog della 3.18 ne porta altri: il minimo e' cinque.
        ("il marcatore della 3.18 e' su tutte e cinque le voci nuove",
         n.count(M) >= 5),
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

    corpo = ("# Checklist\n### rev. 3.18 \u2014 5 settembre\n\n"
             "## Fase 3\n\n"
             + I36_V + "\n      testo del 3.6\n"
             + I37_V + "\n      testo del 3.7\n"
             + I38_V + "\n      testo del 3.8\n"
             + I310_V + "\n      testo del 3.10\n\n"
             "## Fase 7 \u2014 Scrittura\n\n### Struttura\n\n"
             "4. Il canale anisotropo.\n"
             + F7_V + "\n"
             "6. Risposta ai parametri cosmologici.\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "c_%s.md" % lab)
            with open(p, "wb") as fh:
                fh.write(corpo.replace("\n", eol).encode("utf-8"))
            txt, det, _, _ = read_target(p)
            chk("1%s fine riga rilevato" % lab, det == eol, repr(det))
            ok, done, bad = plan(txt)
            chk("2%s le cinque ancore sono uniche" % lab,
                len(ok) == 5 and not bad, "ok=%d bad=%s" % (len(ok), bad))
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
            fh.write(corpo.replace(I37_V, I37_N).encode("utf-8"))
        chk("7  applicazione parziale: si ferma",
            _exits(lambda: apply_all(read_target(p3)[0])))

    chk("8  3.6 resta [~], non diventa [x]", I36_N.startswith("- [~]"))
    chk("8b 3.10 diventa [~], non [x]: e' rimandato, non chiuso",
        I310_N.startswith("- [~]") and "RIMANDATO" in I310_N)
    chk("8c 3.7 e 3.8 diventano [x] e citano il record",
        I37_N.startswith("- [x]") and "record 38" in I37_N
        and I38_N.startswith("- [x]") and "record 37" in I38_N)
    chk("8d il rimando di Fase 7 nomina l'item e la scadenza",
        "item 3.10" in F7_N and "prima di sottomettere la revisione" in F7_N)

    print("=== SELFTEST paper2_checklist_item34_patch ===")
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
    p = argparse.ArgumentParser(description="I quattro item della Fase 3, e il rimando in Fase 7")
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

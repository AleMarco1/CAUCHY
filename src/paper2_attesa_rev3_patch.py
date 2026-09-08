#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_attesa_rev3_patch.py - porta paper2_attesa_ordine_grandezza.md alla rev. 3.

COSA AGGIUNGE, E PERCHE'
------------------------
La rev. 2 riporta i contrasti in D con la sola SEM della media mock: 5-16 SEM
dall'attesa. E' vero, ed e' incompleto. La risposta 1 al referee stabilisce che
«da qui in avanti nessun sigma si scrive senza dire a quale domanda risponde»:

  SEM della media mock   ->  la media dell'ensemble risponde come il campo
                             osservato?      5.0 - 16.4 sigma: NO.
  sd mock-a-mock         ->  il campo osservato e' un'estrazione strana della
                             distribuzione dei contrasti?
                             0.33 - 1.16 sigma: NO.

Sono due affermazioni entrambe vere e che dicono cose diverse. Riportare solo la
prima farebbe leggere «il campo osservato e' anomalo», che la seconda smentisce
-- ed e' l'errore che il referee ha contestato al §2. La rev. 3 riporta entrambe.

Tre modifiche, atomiche: intestazione, §3(c), e il punto 1 del §6 che era una
cosa DA FARE e ora e' fatta.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "paper2_attesa_ordine_grandezza.md"


EDITS = [

    ("1. intestazione: rev. 3",
     "### **rev. 2, 5 settembre 2026 \u2014 corregge due errori della rev. 1 "
     "e riporta la misura**",
     "### **rev. 3, 5 settembre 2026 \u2014 riporta i DUE denominatori della "
     "risposta 1**\n"
     "### *(rev. 2: corregge due errori della rev. 1 e riporta la misura; "
     "rev. 1: 34 al posto di 84, e il segno dato per predetto)*",
     "rev. 3, 5 settembre 2026"),

    ("2. \u00a73(c): entrambi i denominatori",
     "**(c) E in *D* nulla si cancella.** L'attesa dice \u22120.6 e \u221216.8; "
     "la misura d\u00e0 **+84 \u2026 +222** sul\n"
     "dispari e **\u2212139 \u2026 \u2212242** sul pari, cio\u00e8 5\u201316 SEM "
     "dall'attesa. \u00c8 la scoperta centrale del Paper 2 \u2014\n"
     "i due lati rispondono in modo diverso \u2014 **ora con un numero a priori "
     "contro cui misurarla**, che \u00e8\n"
     "esattamente ci\u00f2 che il referee chiedeva.",
     "**(c) E in *D* nulla si cancella \u2014 ma la frase va detta con DUE "
     "denominatori.** L'attesa dice\n"
     "\u22120.6 sul dispari e \u221216.8 sul pari; la misura d\u00e0 **+84 \u2026 +222** e "
     "**\u2212139 \u2026 \u2212242**. Quanto sia\n"
     "lontano dipende da quale domanda si fa, e la risposta 1 impone di dire "
     "sempre quale:\n"
     "\n"
     "| | in *D* | SEM della media | **sd mock-a-mock** |\n"
     "|---|---:|---:|---:|\n"
     "| DISPARI NGC *k*=0 | +111.7 | 7.0\u03c3 | **0.49\u03c3** |\n"
     "| DISPARI NGC *k*=1 | +83.9 | 5.6\u03c3 | **0.40\u03c3** |\n"
     "| DISPARI SGC *k*=0 | +221.8 | 16.4\u03c3 | **1.16\u03c3** |\n"
     "| DISPARI SGC *k*=1 | +206.4 | 16.0\u03c3 | **1.13\u03c3** |\n"
     "| PARI NGC *k*=0 | \u2212205.4 | 6.0\u03c3 | **0.43\u03c3** |\n"
     "| PARI NGC *k*=1 | \u2212170.1 | 5.0\u03c3 | **0.35\u03c3** |\n"
     "| PARI SGC *k*=0 | \u2212138.8 | 4.6\u03c3 | **0.33\u03c3** |\n"
     "| PARI SGC *k*=1 | \u2212242.1 | 8.7\u03c3 | **0.62\u03c3** |\n"
     "\n"
     "**Con la SEM: la media dell'ensemble NON risponde come il campo osservato**, "
     "a 4.6\u201316.4\u03c3. \u00c8 la\n"
     "scoperta centrale del Paper 2, ora con un numero a priori contro cui "
     "misurarla \u2014 esattamente ci\u00f2\n"
     "che il referee chiedeva al punto 8.\n"
     "\n"
     "**Con la dispersione mock-a-mock: il campo osservato NON \u00e8 "
     "un'estrazione strana**, a 0.33\u20131.16\u03c3.\n"
     "Il suo contrasto \u00e8 un valore del tutto ordinario per una singola "
     "realizzazione dell'ensemble.\n"
     "\n"
     "Le due cose non si contraddicono e vanno scritte insieme. La discrepanza \u00e8 "
     "**di livello medio**:\n"
     "sta fra la media dei 200 mock e il campo osservato, non fra il campo "
     "osservato e la popolazione\n"
     "da cui potrebbe provenire. \u00c8 la stessa distinzione che regge il rango "
     "1/2001 del deficit \u2014 dove\n"
     "invece il campo osservato **\u00e8** un'estrazione estrema \u2014 e tacerla qui "
     "farebbe leggere «anomalo»\n"
     "dove il dato dice «ordinario».",
     "**Con la dispersione mock-a-mock:"),

    ("3. \u00a76 punto 1: fatto, e cosa resta",
     "1. **Correggere `paper2_contrasti.py`.** La colonna \u00abattesa\u00bb per il "
     "dispari **in *D*** usa l'attesa\n"
     "   del lato mock (57.3) invece di att_dati \u2212 att_mock (\u22120.6). Con la "
     "prima il rapporto misura/attesa\n"
     "   dice 1.95; con la seconda la misura \u00e8 a sette SEM da zero. La riga da "
     "cambiare passa\n"
     "   `res[\"att_odd\"]` al confronto in *D*: va sostituita con "
     "`res[\"att_odd_data\"] - res[\"att_odd\"]`,\n"
     "   che il record gi\u00e0 calcola. Il termine pari \u00e8 gi\u00e0 confrontato "
     "correttamente.",
     "1. **`paper2_contrasti.py` \u00e8 stato corretto** (rev. 5). Tre difetti, tutti "
     "di refertazione e\n"
     "   nessuno di calcolo: l'attesa del dispari **in *D*** usava quella del "
     "lato mock (57.3) invece di\n"
     "   att_dati \u2212 att_mock (\u22120.6); il rapporto misura/attesa veniva stampato "
     "anche con l'attesa\n"
     "   indistinguibile da zero, producendo numeri come \u2212759 accanto a \u00ab16.4 "
     "SEM\u00bb; e mancava la sd\n"
     "   mock-a-mock. Ora l'attesa in *D* \u00e8 derivata, il rapporto si stampa solo "
     "quando \u00e8 informativo, e i\n"
     "   due denominatori escono affiancati con la domanda a cui rispondono. Due "
     "controlli nuovi fissano\n"
     "   che l'attesa del dispari in *D* \u00e8 il **solo travaso** e che "
     "sd = SEM\u00b7\u221an.",
     "`paper2_contrasti.py` \u00e8 stato corretto"),
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
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
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
    print("  %d -> %d byte, %d modifiche"
          % (len(txt.encode("utf-8")), len(out.encode("utf-8")), len(EDITS)))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".rev2"
    if args.backup and not os.path.exists(bak):
        with open(bak, "wb") as fh:
            fh.write(txt.encode("utf-8"))
        print("  copia rev. 2 : %s" % bak)
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
        ("l'intestazione dice rev. 3", "rev. 3, 5 settembre 2026" in n),
        ("la storia delle revisioni resta leggibile",
         "rev. 2:" in n and "rev. 1:" in n),
        ("la tabella dei due denominatori c'e'",
         "sd mock-a-mock" in n and "| DISPARI SGC *k*=0 | +221.8 |" in n),
        ("entrambe le letture sono scritte",
         "NON risponde come il campo osservato" in n
         and "NON \u00e8 un'estrazione strana" in n),
        ("il confronto col rango 1/2001 c'e'", "1/2001" in n),
        ("il §6 registra la correzione dello strumento",
         "\u00e8 stato corretto" in n and "solo travaso" in n),
        ("i tre difetti dello strumento sono nominati",
         "\u2212759" in n),
        ("la smentita del termine pari resta",
         "smentita in tutti e quattro i casi" in n),
        ("la debolezza della calibrazione SGC resta",
         "crescerebbe" in n and "3.8\u00d7 a 7\u00d7" in n),
        ("il ritiro dell'osservazione della rev. 1 resta",
         "si ritira" in n),
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

    corpo = ("# L'attesa a priori\n\n"
             "### richiesta dal referee, \u00abCosa manca\u00bb, punto 8\n"
             + EDITS[0][1] + "\n\n## 3. Cosa dicono\n\n"
             "**(b)** ... **La predizione del termine pari \u00e8 smentita in tutti e "
             "quattro i casi**, e si registra\ncome smentita.\n\n"
             + EDITS[1][1] + "\n\n## 4. Debolezze\n\n"
             "crescerebbe, da 3.8\u00d7 a 7\u00d7. E l'osservazione della rev. 1 "
             "si ritira.\n\n"
             "## 6. Da fare\n\n" + EDITS[2][1] + "\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "a_%s.md" % lab)
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

        p2 = os.path.join(td, "parziale.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace(EDITS[0][1], EDITS[0][2]).encode("utf-8"))
        chk("6  applicazione parziale: si ferma",
            _exits(lambda: apply_all(read_target(p2)[0])))

    # i due denominatori differiscono di sqrt(200): la relazione che il
    # documento afferma, verificata invece che scritta
    # L'invariante non e' il valore della sd -- che dipende da quante cifre
    # della SEM si guardano -- ma il RAPPORTO fra i due sigma, che vale sqrt(n)
    # qualunque sia l'arrotondamento.
    import math
    for lab, s_sem, s_sd in (("DISPARI NGC k0", 7.0, 0.49),
                             ("DISPARI SGC k0", 16.4, 1.16),
                             ("PARI NGC k0", 6.0, 0.43),
                             ("PARI SGC k1", 8.7, 0.62)):
        r = s_sem / s_sd
        chk("7  %s: sigma_SEM / sigma_sd = %.2f, atteso sqrt(200) = %.2f"
            % (lab, r, math.sqrt(200)),
            abs(r - math.sqrt(200)) < 0.5,
            "scarto %.3f, compatibile con l'arrotondamento a una cifra"
            % abs(r - math.sqrt(200)))

    print("=== SELFTEST paper2_attesa_rev3_patch ===")
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
        description="Porta l'attesa a priori alla rev. 3 (due denominatori)")
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

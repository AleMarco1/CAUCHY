#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_b3_patch.py - il rilievo B.3 del secondo report: il controllo c'e' gia'.

Il referee osserva che il blocco A e' solo lato dati mentre il non attribuito e'
su D, e propone come decisivo il controllo «blocco A con i mock». La premessa
era vera nella richiesta di review, dove il blocco A aveva DUE punti. L'
emendamento 40 lo ha portato a SEI e con il lato mock: il registro del budget
porta `n_mock` = 200 e una `sem` per ogni punto del blocco A.

Il pavimento e' quindi gia' su D. Il controllo e' stato eseguito come effetto
collaterale di un emendamento fatto per un'altra ragione, e non ce ne eravamo
accorti finche' il rilievo non l'ha fatto cercare.

E il suo esito CONFERMA A.2 a k=0,1 -- copertura 86, 80, 83 e 52% -- mentre
l'emendamento 49 lo LIMITA sopra: 85, 44, 26 e 10%.

Una modifica sola: la sezione, prima di «Sezioni ancora aperte».
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"
ANCORA = "---\n\n## Sezioni ancora aperte\n"
SEZIONE = "---\n\n## Secondo report, B.3 — **[SCRITTA]** — *il controllo c'è già, ed è nei dati*\n\n> *«Il blocco A è solo lato dati, mentre il non attribuito è su* D*: due domini diversi presentati\n> come rapporto. Il controllo che decide: blocco A con i mock, due o tre ampiezze × 200\n> realizzazioni.»*\n\n**La premessa era vera quando l'abbiamo scritta, e non lo è più.** Nella richiesta di review il blocco\nA aveva **due** punti e serviva da test di chiusura sul solo lato dati. L'emendamento 40 lo ha portato\na **sei**, e con il lato mock: il registro del budget porta per ogni punto del blocco A un `dD` con la\nsua `sem` e **`n_mock` = 200**, in entrambi gli emisferi.\n\nIl pavimento è quindi **già su *D***, non sul lato dati. Il controllo che il report propone come\ndecisivo è stato eseguito, come effetto collaterale di un emendamento fatto per un'altra ragione, e\nnon ce ne eravamo accorti finché il rilievo non ce l'ha fatto cercare.\n\n### E il suo esito conferma A.2\n\nIl report scrive: *«se il pavimento su* D *coincide con quello sul lato dati, la struttura è tutta del\nlato dati e A.2 è dimostrato. Se è più grande, c'è un contributo mock che non avete.»*\n\nIl pavimento su *D* copre **86%, 80%, 83% e 52%** del non attribuito a *k*=0,1. **Non c'è un\ncontributo mock aggiuntivo**: la struttura è del lato dati, e A.2 è dimostrato a quei livelli. Con\nessa vale la conseguenza di A.4, che abbiamo già accettato: il residuo non attribuito **non è un\nsistematico** ed esce da σ_sys.\n\n### Ma non si estende ai livelli alti\n\nIl blocco A a *k*=2,3 mancava su quattro punti. Sono stati girati — emendamento 49 — e ora il\npavimento poggia su sei punti a **tutti e quattro** i livelli, con il cancello di riproduzione passato\na *k*=0,1.\n\nLa copertura a *k*=2,3 vale **85%, 44%, 26% e 10%**.\n\n**L'identificazione dimostrata a *k*=0,1 non vale a *k*=2,3.** O vale solo dove il pavimento è grande\n— e allora A.2 è un'osservazione ai livelli primari e non una spiegazione generale — oppure il\npavimento perde potere con l'erosione, e il residuo contiene qualcosa che il blocco A a quei livelli\nnon vede. **Otto numeri non separano le due letture**, e le riportiamo entrambe.\n\n### Cosa questo cambia nel disegno\n\nNulla da girare. Cambia che il rapporto fra pavimento e non attribuito **non era** fra due domini\ndiversi, come il rilievo temeva e come la nostra descrizione lasciava credere: era su *D* da quando\nil blocco A ha sei punti. La descrizione era in ritardo sui dati, ed è quella che correggiamo.\n\n"

EDITS = [
    ("1. B.3: il controllo c'e' gia'", ANCORA, SEZIONE + ANCORA,
     "## Secondo report, B.3 \u2014 **[SCRITTA]**"),
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
    n = norm(txt)
    for name, old, new, marker in EDITS:
        prima = len(n)
        n = n.replace(old, new, 1)
        if len(n) == prima:
            fail("la sostituzione %r non ha cambiato nulla." % name)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  righe     : %d   sezioni: %d" % (len(n.splitlines()), n.count("\n## ")))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    for prereq, chi in (("## Secondo report, punto A", "paper2_sottrazioni_patch.py"),):
        if prereq not in n:
            fail("manca %r: lancia prima %s. Questa sezione ci si appoggia."
                 % (prereq, chi))
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
    print("  %d -> %d righe" % (len(n.splitlines()), len(new_n.splitlines())))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".preb3"
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
        ("la sezione esiste", "## Secondo report, B.3" in n),
        ("e precede «Sezioni ancora aperte»",
         n.index("## Secondo report, B.3") < n.index("## Sezioni ancora aperte")),
        ("dice che la premessa era vera e non lo e' piu'",
         "era vera quando l'abbiamo scritta, e non lo \u00e8 pi\u00f9" in f),
        ("cita n_mock = 200 e la sem per punto",
         "`n_mock` = 200" in n and "con la sua `sem`" in f),
        ("dice che il pavimento e' GIA' su D",
         "gi\u00e0 su *d***, non sul lato dati" in f),
        ("ammette di non essersene accorti prima",
         "non ce ne eravamo accorti" in f),
        ("riporta la regola di decisione del report",
         "coincide con quello sul lato dati" in f),
        ("l'esito CONFERMA A.2 a k=0,1",
         "86%, 80%, 83% e 52%" in n and "a.2 \u00e8 dimostrato a quei livelli" in f),
        ("e non c'e' contributo mock aggiuntivo",
         "non c'\u00e8 un contributo mock aggiuntivo" in f),
        ("con la conseguenza di A.4 gia' accettata", "esce da \u03c3_sys" in n),
        ("ma NON si estende a k=2,3",
         "85%, 44%, 26% e 10%" in n and "non vale a *k*=2,3" in f),
        ("e le due letture restano aperte",
         "non separano le due letture" in f),
        ("dice che non c'e' nulla da girare", "nulla da girare" in f),
        ("e che a essere in ritardo era la DESCRIZIONE",
         "la descrizione era in ritardo sui dati" in f),
        ("le sezioni precedenti sono intatte",
         "## Secondo report, punto A" in n
         and "## Secondo report, rilievi minori" in n),
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

    corpo = ("# Risposta\n\n## Secondo report, punto A \u2014 **[SCRITTA]**\n\nt\n\n"
             "## Secondo report, rilievi minori D.2\u2013D.6 \u2014 **[SCRITTA]**\n\nt\n\n"
             + ANCORA)

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

        p2 = os.path.join(td, "senzaA.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace("## Secondo report, punto A \u2014 **[SCRITTA]**",
                                   "## Altro").encode("utf-8"))

        class B:
            target = p2
            apply = False
            backup = False
            allow_eol_normalise = False
        chk("6  senza la sezione del punto A la patch rifiuta",
            _exits(lambda: cmd_patch(B())))

    fs = piatto(SEZIONE)
    chk("7  la sezione NON rivendica un test nuovo",
        "nulla da girare" in fs and "gi\u00e0 su" in fs)
    chk("7b e ammette che ce l'ha fatto vedere il rilievo",
        "non ce ne eravamo accorti" in fs)
    chk("7c l'esito e' riportato in ENTRAMBE le direzioni",
        "\u00e8 dimostrato a quei livelli" in fs and "non vale a *k*=2,3" in fs)
    chk("7d e la conseguenza di A.4 non viene rinnegata",
        "non \u00e8 un sistematico" in fs)

    print("=== SELFTEST paper2_b3_patch ===")
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
    p = argparse.ArgumentParser(description="B.3: il controllo esiste gia'")
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

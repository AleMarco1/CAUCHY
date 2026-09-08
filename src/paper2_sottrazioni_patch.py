#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_sottrazioni_patch.py - il punto A del secondo report, accettato, e le
sottrazioni che ne seguono.

Il referee osserva che la discrepanza riportata come risultato e' compatibile
con il rumore di una singola realizzazione, e che il numero che lo dimostra e'
NOSTRO -- la dispersione delle 200 pendenze, riportata alla risposta 2 senza
trarne la conseguenza. L'aritmetica regge: i quattro rapporti da 2.10 a 5.56
sono la stessa affermazione, 0.77-1.05 sigma.

COSA SI RITIRA, E PERCHE' DICHIARATAMENTE
------------------------------------------
La regola a quattro esiti E1-E4 sta nella pre-registrazione §5.3. Il registro e'
append-only: toglierla dal manoscritto senza dirlo la renderebbe invisibile,
mentre dirlo costa un paragrafo e mostra la disciplina. Si ritira DICHIARANDOLO,
con la ragione e con l'audit dell'emendamento 48 che la conferma dall'interno.

Con essa escono il fattore 2.1-5.6 come risultato, i tre meccanismi esclusi
(che diventano una nota) e il budget nella forma attuale.

E LA SEZIONE PORTA DUE COSE CHE IL REPORT NON HA
-------------------------------------------------
Il §3.7 REGGE: lo spostamento implicato sulla media delle pendenze vale meno
dell'1%, e il punto 3 di A.5 e' infondato. E la copertura del pavimento CROLLA
sopra k=1 -- 85%, 44%, 26%, 10% -- quindi l'identificazione del §A.2 non si
estende ai livelli alti. Nessuno dei due era stato chiesto.

Una modifica sola: la sezione, prima di «Sezioni ancora aperte».
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"
ANCORA = "---\n\n## Sezioni ancora aperte\n"
SEZIONE = "---\n\n## Secondo report, punto A — **[SCRITTA]** — *accettato, e la revisione è una sottrazione*\n\n> *«Con quel numero in mano, quella che chiamate la scoperta centrale del Paper 2 è una fluttuazione a\n> un sigma, e l'avete già scritto voi a riga 110 senza trarne la conseguenza.»*\n\n**Ha ragione, e il numero era nostro.** La tabella dei due denominatori dice 0.33–1.16σ; il passo che\nnon abbiamo fatto è la conseguenza: se il campo osservato è un'estrazione ordinaria della\ndistribuzione mock, la discrepanza **non richiede un meccanismo**. Abbiamo speso tre run per\nescluderne tre.\n\nL'aritmetica di A.1 la confermiamo: (1 − 1/*R*)/(sd/media) dà **0.97, 0.94, 0.77 e 1.05σ**. I quattro\nrapporti da 2.10 a 5.56 sono la stessa affermazione quattro volte, e il 5.56 è **meno** estremo del\n2.10 perché il suo denominatore è più grande.\n\n### La regola dei denominatori, adottata\n\n> La **SEM** è il denominatore giusto quando l'oggetto della domanda è una proprietà dell'**ensemble\n> di mock**. La **dispersione per realizzazione** lo è quando l'affermazione riguarda il **campo\n> osservato**, che ha *N* = 1.\n\nLa adottiamo come **primo** passo di ogni misura, non come chiarimento successivo, ed è la\nraccomandazione della nota finale del report. Ne segue che\n\n**Δ*D*_max = −98.3 ± 11.2 (media mock) ± ~100 (realizzazione del lato dati)**\n\nè **compatibile con zero**. Il sistematico vero è il solo termine (c), **7.7 generatori**; il residuo\nnon attribuito esce da σ_sys e si riporta come **pavimento statistico di realizzazione**, che è ciò\nche è.\n\nE ne segue il **tetto**: l'incertezza di realizzazione è irriducibile perché l'universo osservato è\nuno, vale ~100 generatori, cioè l'1.4% del deficit NGC e il 2.8% del SGC. Δ*D*_max = 75–114 **è già a\nquel tetto**. La Componente A ha esaurito la sua precisione.\n\n### Cosa si ritira, dichiaratamente\n\nIl registro è append-only e la pre-registrazione §5.3 contiene la regola: togliere senza dirlo la\nrenderebbe invisibile, e dirlo costa un paragrafo.\n\n**La regola a quattro esiti E1–E4 è RITIRATA.** Decideva Δ*D*_max contro 53 con la SEM della media\nmock, cioè con il denominatore che la regola di A.3 esclude per un'affermazione sul campo osservato.\nL'audit dell'emendamento 48 lo conferma **dall'interno**: la soglia E1/E2 non è attraversata da\nnulla, e la stessa predizione P1 «fallisce» in NGC e «passa» in SGC a 0.22σ e 0.12σ dalla soglia —\ndue verdetti opposti dallo stesso non-risultato. Al suo posto resta la domanda 1 del §F, che risponde\nmeglio e senza soglie.\n\n**Il fattore 2.1–5.6 esce dai risultati** e resta come una frase con il suo σ: *il campo osservato\nrisponde all'AP circa un sigma sotto la media dell'ensemble*.\n\n**I tre meccanismi esclusi diventano una nota.** Maschera-intersezione, spazio reale e trattamento\n(B) sono misure fatte e restano nel registro; ma escludono meccanismi di un effetto che non ne\nrichiede, e il loro posto è una nota a piè di pagina, non una sezione.\n\n**Il budget si riscrive** con (c) come unico sistematico e il non attribuito riportato fuori, come\npavimento di realizzazione.\n\n**La «firma asimmetrica fra emisferi»** è già stata declassata a osservazione a 1.6σ (rilievo B.2).\n\n### Dove il report chiede un conto e il conto lo contraddice\n\nIl punto 3 di A.5 sospetta che la media delle pendenze, stimata sui primi 200 dell'ipercubo, sia\nspostata. **Non lo è.** Il prefisso è atipico in modo uniforme e modesto — tutti i parametri a\n*z* fra −0.9 e −1.5 — e lo spostamento implicato sulla media delle pendenze, via il parametro che\npesa di più (*n*_s), vale **+30.0 e −17.0 generatori, cioè meno dell'1%**, contro un'incertezza per\nrealizzazione del 54–78%. Il §3.7 regge, e ora con un numero.\n\n### E il conto che il report sperava non funziona\n\nIl punto 1 di A.5 propone la chiusura positiva: se i mock con meno anelli rispondono meno, il basso\nconteggio di DESI **predice** la sua bassa risposta. Lo abbiamo fatto — la pendenza è la regressione\ndi *N*_H1 su *F* sui sei punti della linea B, definizione verificata perché riproduce esattamente le\nquattro dispersioni depositate.\n\nρ(pendenza, *N*_H1) vale **−0.060, −0.060, −0.131 e −0.222**: il **segno è quello predetto** in tutti\ne quattro, ma è nullo in NGC (0.85σ) e raggiunge 3.2σ solo in SGC *k*=1.\n\n**E l'estrapolazione è vietata**, per la ragione che il report stesso indica in fondo ad A.5: il\nconteggio DESI sta a **20–25σ** dalla distribuzione mock. Portandovi la regressione, la pendenza\npredetta **cambia segno** in SGC — +1884 e +4736 contro medie di −2119 e −1869. Non è una previsione:\nè la dimostrazione che l'estrapolazione non ha senso, e sarebbe stata la quarta occorrenza dello\nstesso errore.\n\nIl punto 2 dà una sola correlazione sotto *p* = 0.05 su 28 confronti, ρ(pendenza, *n*_s) = −0.15 in\nNGC e nulla in SGC. Con 1.4 attese per caso, e con *k*=0 e *k*=1 non indipendenti, è **una**\nosservazione debole. Non regge la saldatura col Paper 1 che si sperava.\n\n### Un vincolo su A.2 che nessuno aveva chiesto\n\nIl §A.2 identifica il residuo non attribuito con la struttura a singola realizzazione del lato dati,\ne cita come prova che il pavimento del blocco A ne copre l'**80–86%**. Abbiamo completato il blocco a\n*k*=2,3 — quattro punti che mancavano — e il pavimento poggia ora su **sei punti a tutti e quattro i\nlivelli**, con il cancello di riproduzione passato a *k*=0,1.\n\nLa copertura: **86%, 80%, 83% e 52%** a *k*=0,1; **85%, 44%, 26% e 10%** a *k*=2,3.\n\n**L'identificazione non si estende ai livelli alti.** O vale solo dove il pavimento è grande — e\nallora A.2 è un'osservazione a *k*=0,1 e non una spiegazione — oppure il pavimento perde potere con\nl'erosione e il residuo contiene qualcosa che il blocco A a quei livelli non vede. **Otto numeri non\nseparano le due letture**, e le riportiamo entrambe.\n\n### Cosa resta\n\nLe due domande del §F, che condividiamo:\n\n1. **Quanto sposta il fiduciale il risultato pubblicato?** Rango **1/201 in ogni punto**, deficit\n   20.04–20.61% a *k*=0 e 25.27–25.66% a *k*=1, escursione ≤0.57 pp. La limitazione (ix) di M26 è\n   chiusa qui.\n2. **Il campo osservato risponde all'AP diversamente da un campo ΛCDM?** **No, a 0.77–1.05σ**, e la\n   domanda non è migliorabile perché il lato dati ha *N* = 1.\n\nPiù la regola dei denominatori, che è il risultato metodologico più utile della misura che l'ha\nprodotta.\n\n"

EDITS = [
    ("1. il punto A accettato e le sottrazioni", ANCORA, SEZIONE + ANCORA,
     "## Secondo report, punto A \u2014 **[SCRITTA]**"),
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
    for prereq, chi in (("## Risposta 5 \u2014 Il terzo canale", "paper2_risposta_5_patch.py"),
                        ("Con quale denominatore", "paper2_risposta_finale_patch.py"),
                        ("Con quanta forza (rilievo B.2)", "paper2_risposta_r2_patch.py")):
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
    bak = args.target + ".presottr"
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
        ("la sezione esiste", "## Secondo report, punto A" in n),
        ("e precede «Sezioni ancora aperte»",
         n.index("## Secondo report, punto A") < n.index("## Sezioni ancora aperte")),
        ("il punto A e' ACCETTATO, e il numero riconosciuto come nostro",
         "ha ragione, e il numero era nostro" in f),
        ("l'aritmetica di A.1 e' rifatta", "0.97, 0.94, 0.77 e 1.05" in n),
        # sul testo piatto: e' un inizio di frase, quindi maiuscola.
        ("la regola dei denominatori e' adottata",
         "la adottiamo come **primo** passo" in f),
        ("Delta D_max e' riscritto con i due errori",
         "\u00b1 11.2 (media mock) \u00b1 ~100" in n and "compatibile con zero" in f),
        ("il non attribuito esce da sigma_sys",
         "esce da \u03c3_sys" in n and "pavimento statistico di realizzazione" in f),
        ("il tetto della Componente A e' scritto",
         "\u00e8 gi\u00e0 a\nquel tetto" in n or "gi\u00e0 a quel tetto" in f),
        ("E1-E4 e' RITIRATA, e dichiaratamente",
         "regola a quattro esiti E1\u2013E4 \u00e8 RITIRATA" in n
         and "togliere senza dirlo la" in f),
        ("con l'audit del 48 come conferma interna",
         "emendamento 48" in f and "dall'interno" in f),
        ("e i due verdetti opposti di P1 sono citati",
         "0.22\u03c3 e 0.12\u03c3" in n),
        ("il fattore 2.1-5.6 esce dai risultati",
         "esce dai risultati" in f),
        ("i tre meccanismi diventano una nota",
         "diventano una nota" in f),
        ("il budget si riscrive", "il budget si riscrive" in f),
        ("il \u00a73.7 REGGE, con il numero",
         "meno dell'1%" in f and "il \u00a73.7 regge" in f),
        ("A.5 punto 1: rho riportato e estrapolazione vietata",
         "\u22120.060, \u22120.060, \u2212" in n and "cambia segno" in f),
        ("A.5 punto 2 e' riportato con le 28 prove",
         "28 confronti" in f),
        ("il vincolo su A.2 dal record 49 c'e'",
         "85%, 44%, 26% e 10%" in n and "non si estende ai livelli alti" in f),
        ("e le due letture restano aperte",
         "non\nseparano le due letture" in n or "non separano le due letture" in f),
        ("le due domande del \u00a7F sono condivise",
         "1/201 in ogni punto" in n and "0.77\u20131.05\u03c3" in n),
        ("le sezioni precedenti sono intatte",
         "## Risposta 5 \u2014 Il terzo canale" in n
         and "## Attesa a priori" in n
         and "## \u00a74.6 \u2014 Il ripattern del tiling" in n),
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

    corpo = ("# Risposta\n\n## Risposta 5 \u2014 Il terzo canale, misurato\n\nt\n\n"
             "## Attesa a priori\n\nt\n\n"
             "## \u00a74.6 \u2014 Il ripattern del tiling\n\nt\n\n"
             "## Risposta 3\n\nCon quale denominatore \u00abescludono zero\u00bb. t\n\n"
             "## \u00a73.8\n\nCon quanta forza (rilievo B.2). t\n\n" + ANCORA)

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

        for prereq in ("## Risposta 5 \u2014 Il terzo canale, misurato",
                       "Con quale denominatore", "Con quanta forza (rilievo B.2)"):
            p2 = os.path.join(td, "senza.md")
            with open(p2, "wb") as fh:
                fh.write(corpo.replace(prereq, "ALTRO").encode("utf-8"))

            class B:
                target = p2
                apply = False
                backup = False
                allow_eol_normalise = False
            chk("6  senza %r la patch rifiuta" % prereq[:24],
                _exits(lambda: cmd_patch(B())))

    fs = piatto(SEZIONE)
    chk("7  la sezione ACCETTA invece di difendersi",
        "ha ragione" in fs and "abbiamo speso tre run" in fs)
    chk("7b il ritiro di E1-E4 e' dichiarato, non silenzioso",
        "ritirata" in fs and "renderebbe invisibile" in fs)
    chk("7c e le quattro sottrazioni sono tutte nominate",
        all(x in fs for x in ("esce dai risultati", "diventano una nota",
                              "il budget si riscrive", "1.6\u03c3")))
    chk("7d la sezione porta anche cio' che il report NON ha chiesto",
        "il \u00a73.7 regge" in fs and "non si estende ai livelli alti" in fs)
    chk("7e e non rivendica una chiusura positiva che non c'e'",
        "l'estrapolazione \u00e8 vietata" in fs and "cambia segno" in fs)

    print("=== SELFTEST paper2_sottrazioni_patch ===")
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
    p = argparse.ArgumentParser(description="Il punto A accettato e le sottrazioni")
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

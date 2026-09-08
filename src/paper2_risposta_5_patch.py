#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_risposta_5_patch.py - scrive la risposta 5 nella risposta al referee.

Due modifiche, atomiche: la sezione, e la riga della tabella finale da
[BLOCCATA] a [SCRITTA]. Sono lo stesso fatto in due posti.

LA SEZIONE RIPORTA UNA SMENTITA
-------------------------------
La firma dichiarata nell'item 3.2e -- sopra soglia a C1 e C4, sotto a C2 e C3 --
e' FALSIFICATA nel verso opposto, in due emisferi indipendenti. Si scrive come
smentita: non riscritta, non indebolita, non reinterpretata in un successo.

E riporta anche il difetto dell'analisi che l'ha preceduta, perche' senza quello
la sezione conterrebbe il verdetto sbagliato: il primo confronto metteva un
|Delta N| GREZZO contro un pavimento costruito su residui gia' corretti per il
termine (e), e il verdetto cambiava segno a seconda della correzione.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"

ANCHOR_SEZIONI = "---\n\n## Sezioni ancora aperte\n"

SEZIONE = '''---

## Risposta 5 \u2014 Il terzo canale, misurato **[SCRITTA]** \u2014 *e la firma dichiarata \u00e8 smentita*

> *«Non cercate un* F *efficace: \u00e8 la mossa che vi ha bloccato. Il disegno corretto non interpola
> affatto. Per ogni angolo* C*: applicate la deformazione vera e misurate* D(C)*; applicate il suo
> surrogato affine minimax come punto di griglia separato e misurate* D(C_aff)*; la differenza* \u00c8 *il
> terzo canale, misurato direttamente.»*

**Il disegno ha funzionato.** Il test depositato confrontava *D*_obs con un *D*_pred da **modello**, e
`CORNER_F` era vuoto perch\u00e9 un angolo \u00e8 una **traiettoria** in *F*(*z*), non un valore \u2014 per C1
spazza da 0.9611 a 0.9856. Questo confronta **due run**. Sparisce il modello, sparisce
l'estrapolazione, e i quattro angoli veri erano gi\u00e0 su disco: il costo \u00e8 stato quattro punti di
griglia nuovi sul solo lato dati.

**E la misura smentisce la predizione.**

### Come

Il surrogato \u00e8 il miglior membro della famiglia del Lemma 3 \u2014 *f*(*r*) = *A r*^*p* \u2014 contro la
deformazione vera dell'angolo. Il fitter avvolge il minimax gi\u00e0 esistente invece di riscriverlo, e
passa tre cancelli: a *p* = 1 riproduce il residuo a un parametro depositato; sull'angolo nullo d\u00e0
*p* = 1 e residuo 0; il fit riduce e *p* resta dentro il bracket della linea B.

**Riproduce anche i residui documentati**: 0.0822, 0.0473, 0.0062 e 0.0051 voxel contro 0.082, 0.047,
0.006 e 0.005 della checklist \u2014 quattro cifre su quattro angoli indipendenti. E il residuo a un
parametro di C1, 8.8751, riproduce la costante che ancora B1 e B5. Quei numeri avevano provenienza
documentale e ora hanno provenienza di codice.

Nella griglia un surrogato \u00e8 **strutturalmente un punto di linea B**, con *F*_AP = *p* letto dal
registro del fit e mai scritto nel codice. Costruito con `deform` e non con `make_dc_tab_ap`, che
differisce di un ULP. Con la patch e senza surrogati, B1 in NGC d\u00e0 28194 / 23791, identici ai
congelati: il percorso esistente \u00e8 intatto.

### Un difetto dell'analisi, preso prima di scrivere

Il primo confronto metteva un |\u0394*N*| **grezzo** contro `prop2_floor`. Ma quel pavimento \u00e8 il massimo
di |*b*_residual| sul blocco A, cio\u00e8 un residuo **gi\u00e0 corretto** per il termine (e). Due quantit\u00e0
diverse.

E non era un dettaglio: la maschera differisce fra un angolo e il suo surrogato fino a **1686 voxel**,
che a 0.1009 generatori per voxel valgono **170 generatori** \u2014 quasi il doppio del segnale grezzo. Il
verdetto cambiava segno a seconda che si correggesse o no.

Correggere con la pendenza media **non bastava**: il §4.4 misura l'elasticit\u00e0 locale al bordo a 1.71
contro la globale 1.08, quindi la sottrazione lascia ~0.59 dell'ampiezza corretta, circa 100
generatori su NGC C1. Pi\u00f9 grande di tutto ci\u00f2 che si cerca.

**Il rimedio esisteva gi\u00e0**, costruito per il §3.2: intersezione delle maschere sugli **otto** punti,
poi maschera fissa. `n_valid_voxels` diventa costante per costruzione \u2014 305 533 in NGC, 168 643 in
SGC \u2014 e il termine (e) **non esiste** invece di essere sottratto.

### Il risultato

| angolo | canale non modellato | \\|\u0394\\| *k*=0 | pav. | \\|\u0394\\| *k*=1 | pav. |
|---|---:|---:|---:|---:|---:|
| NGC C1 | 0.0822 vox | 37 | 51.1 | 22 | 33.0 |
| NGC C4 | 0.0473 | 22 | 51.1 | **5** | 33.0 |
| NGC C2 | 0.0062 | 9 | 51.1 | **74** | 33.0 |
| NGC C3 | 0.0051 | 48 | 51.1 | **77** | 33.0 |
| SGC C1 | 0.0822 | **81** | 34.6 | 0 | 27.5 |
| SGC C4 | 0.0473 | 4 | 34.6 | **13** | 27.5 |
| SGC C2 | 0.0062 | **56** | 34.6 | **72** | 27.5 |
| SGC C3 | 0.0051 | **68** | 34.6 | **71** | 27.5 |

**La firma dichiarata era: sopra soglia a C1 e C4, sotto a C2 e C3.** L'ordinamento \u00e8 **rovesciato**.

C2 e C3 \u2014 i due canali **pi\u00f9 piccoli**, 0.0062 e 0.0051 voxel \u2014 stanno sopra soglia in tre casi su
quattro. C4, il **secondo pi\u00f9 grande** con 0.0473, sta sotto in **tutti e quattro**: 22, 5, 4 e 13
generatori. Non \u00e8 segnale non visto: \u00e8 l'ordinamento opposto, riprodotto in due emisferi
indipendenti.

**La predizione dell'item 3.2e §3 \u00e8 falsificata, e resta nel registro come falsificata** \u2014
emendamento 46. Non riscritta, non indebolita, non reinterpretata.

### Cosa questo non toglie, e cosa non aggiunge

Il fitter **riproduce** 0.082 e 0.047. Quei numeri sono giusti: semplicemente **non predicono** dove
*D*(*C*) − *D*(*C*_aff) \u00e8 grande. Riprodurre una quantit\u00e0 e quella quantit\u00e0 avere potere predittivo
sono due affermazioni diverse, e solo la prima era stabilita.

I \u0394 grandi stanno dove `du` \u2014 lo spostamento di griglia contro il fiduciale \u2014 \u00e8 **piccolo**: 0.14 e
0.18 a C2 e C3 contro 0.77 e 0.53 a C1 e C4. Sarebbe coerente con il §4.4, dove il canale che conta \u00e8
la maschera al bordo. **Ma questa ipotesi \u00e8 nata guardando questi numeri**, e la riportiamo come *a
posteriori*: metterla alla prova richiede punti scelti per separare `du` dal residuo, e la griglia
attuale non li ha.

**Tre riserve.** Il pavimento \u00e8 calcolato sulla maschera **piena** mentre questi \u0394 stanno
sull'intersezione, pi\u00f9 piccola dello 0.8% in NGC e del 2% in SGC \u2014 lo stesso genere di confronto fra
domini diversi che il termine (e) ci ha appena insegnato a evitare, piccolo ma da dire. Il lato dati
\u00e8 deterministico ma \u00e8 **una** realizzazione, e senza mock non ha un secondo denominatore. E otto
numeri su due livelli sono pochi per una legge: la coerenza fra emisferi li rende pi\u00f9 di un caso, non
la misura di un meccanismo.

**Se valga la pena aggiungere i mock, ora si pu\u00f2 rispondere**: il disegno dichiarato non testerebbe la
firma dichiarata, perch\u00e9 quella firma \u00e8 falsificata. Un test con i mock andrebbe ridisegnato attorno a
quello che la misura ha trovato, non attorno a quello che ci si aspettava.

'''

EDITS = [
    ("1. la sezione risposta 5",
     ANCHOR_SEZIONI,
     SEZIONE + ANCHOR_SEZIONI,
     "## Risposta 5 \u2014 Il terzo canale, misurato **[SCRITTA]**"),

    ("2. tabella finale, riga risposta 5",
     "| risposta 5 | **[BLOCCATA]** | emendamento e disegno del surrogato affine |",
     "| risposta 5 | **[SCRITTA]** | chiusa da una misura: il terzo canale c'\u00e8, e la firma "
     "dichiarata \u00e8 SMENTITA nel verso opposto. Emendamento 46 |",
     "| risposta 5 | **[SCRITTA]** | chiusa da una misura"),
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
    """Spazi collassati: un controllo che cerca una frase attraverso un fine
    riga non la trova. Regola gia' registrata, e gia' violata una volta."""
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
    if len(ok) != len(EDITS):
        fail("applicazione PARZIALE gia' presente (%s). Sezione e riga di "
             "tabella sono lo stesso fatto: non proseguo." % ", ".join(done))
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
    print("  nessuna sezione [BLOCCATA] residua dopo la patch: %s"
          % ("[BLOCCATA]" not in n.replace(
              "| risposta 5 | **[BLOCCATA]**", "")))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
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
    print("  %d -> %d byte, 2 modifiche"
          % (len(txt.encode("utf-8")), len(out.encode("utf-8"))))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".pre5"
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
        ("la sezione esiste ed e' [SCRITTA]",
         "## Risposta 5 \u2014 Il terzo canale, misurato **[SCRITTA]**" in n),
        ("precede «Sezioni ancora aperte»",
         n.index("## Risposta 5") < n.index("## Sezioni ancora aperte")),
        ("dice che il disegno del referee ha funzionato",
         "Il disegno ha funzionato" in f),
        ("la SMENTITA e' dichiarata come tale",
         "resta nel registro come falsificata" in f
         and "Non riscritta, non indebolita" in f),
        ("l'ordinamento rovesciato e' spiegato con C4",
         "sta sotto in **tutti e quattro**" in f),
        ("i tre cancelli del fitter ci sono", "tre cancelli" in f),
        ("la riproduzione dei residui documentati e' riportata",
         "0.0822, 0.0473, 0.0062 e 0.0051" in f),
        ("la distinzione riprodurre / predire e' scritta",
         "non predicono" in f and "potere predittivo" in f),
        ("il difetto del termine (e) e' riportato con quanto pesava",
         "1686 voxel" in f and "170 generatori" in f),
        ("e che correggerlo non bastava", "non bastava" in f and "1.71" in f),
        ("la maschera fissa e i due conteggi ci sono",
         "305 533" in f and "168 643" in f),
        ("l'ipotesi su du e' etichettata a posteriori",
         "nata guardando questi numeri" in f and "a\n> posteriori" in n
         or "posteriori" in f),
        ("le tre riserve ci sono", "Tre riserve" in f),
        ("la tabella finale non ha piu' [BLOCCATA] sulla risposta 5",
         "| risposta 5 | **[BLOCCATA]**" not in n),
        ("il §4.6 e il §3.9 sono intatti",
         "## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]**" in n
         and "## \u00a73.9 \u2014 Componente D **[SCRITTA]**" in n),
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

    corpo = ("# Risposta\n\n## \u00a73.9 \u2014 Componente D **[SCRITTA]**\n\ntesto\n\n"
             "## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]**\n\ntesto\n\n"
             + ANCHOR_SEZIONI + "\n| rilievo | stato | cosa aspetta |\n|---|---|---|\n"
             + EDITS[1][1] + "\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "r_%s.md" % lab)
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

        p2 = os.path.join(td, "parziale.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace(EDITS[1][1], EDITS[1][2]).encode("utf-8"))
        chk("6  applicazione parziale: si ferma",
            _exits(lambda: apply_all(read_target(p2)[0])))

    fb = piatto(SEZIONE)
    # I valori sopra soglia sono in GRASSETTO: "| **5** |" e non " 5 ". Il
    # confronto va fatto per token, dopo aver tolto gli asterischi.
    import re as _re
    tok = set(_re.findall(r"\d+", SEZIONE.replace("*", "")))
    mancanti = [v for v in (37, 22, 9, 48, 74, 77, 81, 4, 56, 68, 13, 72, 71, 0, 5)
                if str(v) not in tok]
    chk("7  i sedici Delta della tabella ci sono tutti", not mancanti,
        "mancano %s" % mancanti if mancanti else "confronto per token")
    chk("7b i quattro pavimenti ci sono",
        all(v in SEZIONE for v in ("51.1", "33.0", "34.6", "27.5")))
    chk("7c la sezione NON reinterpreta la smentita in un successo",
        "falsificata" in fb and "successo" not in fb.lower())
    chk("7d la sezione dichiara l'ipotesi du come a posteriori",
        "a posteriori" in fb and "nata guardando questi numeri" in fb)

    print("=== SELFTEST paper2_risposta_5_patch ===")
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
    p = argparse.ArgumentParser(description="Scrive la risposta 5")
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

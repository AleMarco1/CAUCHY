#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_risposta_46_patch.py - scrive il §4.6 nella risposta al referee.

Tre modifiche, atomiche, perche' sono LO STESSO FATTO in tre posti:

  1. la sezione §4.6, nuova, inserita prima di «Sezioni ancora aperte»;
  2. Risposta 8 punto 4 - «i mock necessari non sono su disco» -> ora ci sono,
     e il rilievo e' chiuso da una misura;
  3. la riga §4.6 della tabella finale, da [DA CERCARE] a [SCRITTA].

Applicandone due su tre il documento si contraddirebbe davanti al referee.

La sezione riporta il risultato COME E' USCITO: il rilievo era valido, la voce
3.2b non e' ritirata ma limitata, il verdetto e' sotto soglia, e le due cose che
non sono andate come previste - l'appaiamento fallito e la soglia fortunata -
stanno nel testo invece che nel registro soltanto.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"

ANCHOR_SEZIONI = "---\n\n## Sezioni ancora aperte\n"

SEZIONE = '''---

## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]** \u2014 *il referee ha ragione, e ora \u00e8 misurato*

> *\u00abRepliche costanti, escursione 0,2%\u00bb limita le statistiche di molteplicit\u00e0, non il ripattern:
> sotto deformazione cambia quali celle del box finiscono dove, anche a molteplicit\u00e0 invariata, e il
> 59% dei voxel in-survey sta su celle usate pi\u00f9 di una volta.*

**Il rilievo \u00e8 fondato, e la nostra chiusura per argomento non lo copriva.** La voce 3.2b dimostra
che il gauge a cubo costante fissa il **numero** di repliche \u2014 15 in NGC, 10 in SGC su tutti e undici
i punti \u2014 e la frazione di volume indipendente, con escursione 0.2% contro 13.1% del cubo variabile.
Non dimostra nulla sulla **mappa di assegnazione**. Sono due quantit\u00e0 diverse e 3.2b ne vincola una
sola.

La voce **non si ritira**: resta vera per ci\u00f2 che afferma. Cessa di essere la chiusura del §4.6, che
non era.

**E il 59% \u00e8 un nostro numero, letto correttamente.** Da `results/revision/rev1_r11_tiling.json`:
frazione di volume indipendente 0.69594, voxel in-survey su celle riusate **0.58757**, molteplicit\u00e0
media 1.43690, massima 5. Il 30% di volume ripetuto e il 59% di voxel toccati non si contraddicono:
le celle riusate sono riusate **poco** \u2014 media 1.44 \u2014 ma sono **tante**. Una statistica di
molteplicit\u00e0 quasi invariata \u00e8 quindi compatibile con una riassegnazione estesa, ed \u00e8 esattamente la
ragione per cui il rilievo regge.

**Il run \u00e8 stato fatto.** Item 3.2d, disegno e soglia dichiarati prima (`paper2_item32d_ripattern.md`),
esito nell'emendamento 44.

### Come

La permutazione segnata degli assi \u2014 una simmetria **esatta** del box periodico: il campo resta lo
stesso campo, cambia solo l'orientazione con cui ogni replica viene posata \u2014 \u00e8 entrata **dentro**
`carve_cutsky`, non in una seconda copia. Una permutazione **per replica**, e **le stesse a ogni
punto**: con permutazioni diverse fra B1 e B5 il campo verrebbe rimescolato fra i due punti e
\u0394*D* misurerebbe quel rimescolamento invece della deformazione.

Due cancelli, e il secondo \u00e8 quello che il record 35 impone.

**G-nullo:** due esecuzioni dello smoke, prima e dopo la patch, sul percorso di produzione. Identiche
riga per riga \u2014 *n*_sel, *k*=0, *k*=1, i \u0394*N* a B1 e B5, fino a `D4b=scarti [1, 1]`. La patch ha
cambiato 44 690 byte in 46 918 e non un numero.

**G-azione:** tre realizzazioni al fiduciale, confrontate con i congelati. Tutte e tre **diverse**, di
139\u2013417 generatori. *Un flag che cambia una misura si verifica con un run che produce numeri diversi,
non ispezionando il percorso di codice.*

G-azione **non** sta nello smoke, deliberatamente: D4b verifica che *N*_H1 sia identico ai congelati
mock per mock, quindi con le repliche randomizzate fallirebbe **per costruzione**. Un cancello che
fallisce quando la cosa funziona \u00e8 peggio di nessun cancello.

### Il risultato

200 realizzazioni per emisfero, B1 e B5, *rot_seed* 20260905, ~2 h ciascuno.

| | \u0394*D* standard | \u0394*D* randomizzato | **\u0394_ripattern** | *t* |
|---|---:|---:|---:|---:|
| NGC *k*=0 | \u2212218.00 \u00b1 11.62 | \u2212211.03 \u00b1 11.64 | **+6.96 \u00b1 16.40** | +0.42 |
| NGC *k*=1 | \u2212172.30 \u00b1 11.25 | \u2212181.69 \u00b1 11.55 | **\u22129.38 \u00b1 15.72** | \u22120.60 |
| SGC *k*=0 | \u2212135.98 \u00b1 9.17 | \u2212169.81 \u00b1 9.86 | **\u221233.84 \u00b1 13.50** | \u22122.51 |
| SGC *k*=1 | \u2212111.13 \u00b1 8.71 | \u2212139.76 \u00b1 9.45 | **\u221228.63 \u00b1 12.92** | \u22122.22 |

**Tutti e quattro sotto la soglia di 53 dichiarata prima del run.** Il ripattern del tiling non guida
la risposta AP, e il termine (d) del budget resta **zero per misura** invece che per argomento.

### Due cose che non sono andate come previste

**L'appaiamento fra i bracci \u00e8 fallito.** Il disegno assumeva che i semi condivisi tenessero appaiati
i due bracci, dando una SEM molto pi\u00f9 piccola sulla differenza. Non \u00e8 cos\u00ec: la correlazione fra
bracci \u00e8 0.0054, 0.0490, \u22120.0049 e \u22120.0109 \u2014 zero \u2014 e la SEM appaiata coincide con quella non
appaiata. Randomizzare le repliche produce di fatto una **realizzazione indipendente** della stessa
cosmologia: la coerenza che tiene appaiati due *punti* dello stesso mock non sopravvive fra due
*bracci*. Il test ha quindi 13\u201316 generatori di SEM invece dei 2\u20134 previsti, e molta meno potenza.

**E la soglia \u00e8 stata fortunata.** 53 fu scelta prima del run come la pi\u00f9 stretta fra due candidate,
53 contro 75, sul principio che una soglia fissata in anticipo debba essere la pi\u00f9 difficile da
superare. Il 3σ naturale di questa quantit\u00e0 risulta 39\u201349: 53 \u00e8 quindi leggermente pi\u00f9 **larga** di
3σ, non pi\u00f9 stretta. Scelta al buio, \u00e8 caduta vicino. Lo riportiamo come fortuna.

### E SGC non \u00e8 zero

NGC \u00e8 compatibile con zero e **cambia segno** fra i due livelli (+6.96, \u22129.38). SGC sta a
**2.2\u20132.5σ con lo stesso segno** a entrambi i livelli.

Il verdetto dichiarato \u00e8 \u00abil ripattern non guida la risposta\u00bb, ed \u00e8 quello che scriviamo. Ma
\u00abnon guida\u00bb non \u00e8 \u00abassente\u00bb, e riportare SGC come zero sarebbe la sovra-affermazione che questo
stesso report contesta altrove. \u00c8 anche, di nuovo, la **firma asimmetrica fra emisferi** che il
programma incontra sotto trattamento (B), in spazio reale, e nei contrasti pari e dispari.

### Cosa questo NON stabilisce

**Due punti**, i pi\u00f9 deformati, non l'intera griglia: che valga altrove \u00e8 un'estrapolazione.
La **risposta AP**, non il deficit \u2014 quello \u00e8 il pilot del 22 agosto, con il suo limite separato.
E nulla sui **modi pi\u00f9 grandi della scatola periodica**, che sono **assenti** e non duplicati, e che
nessun riarrangiamento delle repliche pu\u00f2 restituire: M26 §7(vii) lo dice in stampa, e il Paper 2
eredita la limitazione invece di introdurla.

'''

EDITS = [

    ("1. la sezione \u00a74.6",
     ANCHOR_SEZIONI,
     SEZIONE + ANCHOR_SEZIONI,
     "## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]**"),

    ("2. Risposta 8, punto 4",
     "4. **Il tiling con repliche randomizzate.** I mock necessari non sono su disco.",
     "4. **Il tiling con repliche randomizzate.** Fatto: 200 realizzazioni per emisfero a B1 e B5,\n"
     "   \u0394_ripattern fra \u22129 e \u221234 generatori contro una soglia di 53. Il termine (d) resta zero\n"
     "   **per misura**. Resta fuori la carenza dei modi pi\u00f9 grandi della scatola, che nessun\n"
     "   riarrangiamento delle repliche pu\u00f2 restituire. Vedi §4.6.",
     "\u0394_ripattern fra \u22129 e \u221234 generatori"),

    ("3. tabella finale, riga \u00a74.6",
     "| \u00a74.6 | **[DA CERCARE]** | i mock a repliche randomizzate ESISTONO: M26 \u00a75.6, "
     "permutazioni segnate degli assi. La mia ricerca cercava `replic|permut|randomi` nei "
     "NOMI dei file e non li ha trovati: stanno sotto un altro nome |",
     "| \u00a74.6 | **[SCRITTA]** | chiusa da una misura: \u0394_ripattern sotto soglia, emendamento 44. "
     "*(La macchina non era in M26 \u00a75.6 \u2014 quella \u00e8 la sezione sulla significativit\u00e0 \u2014 ma in "
     "\u00a77(vii) e nel pilot `rev1_r11_pilot.py`.)* |",
     "| \u00a74.6 | **[SCRITTA]** | chiusa da una misura"),
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
        fail("applicazione PARZIALE gia' presente (%s). I tre passaggi sono lo "
             "stesso fatto in tre posti: non proseguo." % ", ".join(done))
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
    print("  \u00a73.9 gia' chiuso: %s" % ("Componente D **[SCRITTA]**" in n))
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
    print("  %d -> %d byte, 3 modifiche"
          % (len(txt.encode("utf-8")), len(out.encode("utf-8"))))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".pre46"
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
        ("la sezione \u00a74.6 esiste ed \u00e8 [SCRITTA]",
         "## \u00a74.6 \u2014 Il ripattern del tiling **[SCRITTA]**" in n),
        ("dice che il rilievo \u00e8 fondato", "Il rilievo \u00e8 fondato" in n),
        ("la voce 3.2b NON \u00e8 ritirata", "non si ritira" in n),
        ("il 59% \u00e8 riconosciuto come nostro numero", "0.58757" in n),
        ("i quattro \u0394_ripattern ci sono",
         all(v in n for v in ("+6.96", "\u22129.38", "\u221233.84", "\u221228.63"))),
        ("i due cancelli sono descritti",
         "G-nullo" in n and "G-azione" in n),
        ("il motivo per cui G-azione non sta nello smoke \u00e8 scritto",
         "per costruzione" in n),
        ("l'appaiamento fallito \u00e8 riportato",
         "appaiamento fra i bracci \u00e8 fallito" in n),
        ("la soglia fortunata \u00e8 dichiarata come fortuna",
         "come fortuna" in n),
        ("SGC non \u00e8 riportato come zero",
         "SGC non \u00e8 zero" in n and "non \u00e8 \u00abassente\u00bb" in n),
        ("Risposta 8 punto 4 aggiornato",
         "I mock necessari non sono su disco" not in n),
        ("la tabella finale non ha pi\u00f9 [DA CERCARE] sul \u00a74.6",
         "| \u00a74.6 | **[DA CERCARE]**" not in n),
        ("la citazione sbagliata a M26 \u00a75.6 \u00e8 corretta",
         "quella \u00e8 la sezione sulla significativit\u00e0" in n),
        ("i modi oltre la scatola restano esclusi",
         "assenti** e non duplicati" in n),
        ("le sezioni preesistenti sono intatte",
         "## Sezioni ancora aperte" in n and "## \u00a74.5" in n and "## \u00a73.9" in n),
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

    corpo = ("# Risposta al referee\n\n## \u00a73.9 \u2014 Componente D **[SCRITTA]**\n\ntesto\n\n"
             "## Risposta 8 \u2014 Cosa manca **[SCRITTA]**\n\n"
             "3. **Altro.**\n"
             + EDITS[1][1] + "\n"
             "5. **La Componente D.**\n\n"
             "## \u00a74.5 \u2014 Il termine (c) **[SCRITTA]**\n\ntesto che non va toccato\n\n"
             + ANCHOR_SEZIONI + "\n| rilievo | stato | cosa aspetta |\n|---|---|---|\n"
             + EDITS[2][1] + "\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "r_%s.md" % lab)
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
            n2 = norm(read_target(p)[0])
            chk("4%s la sezione PRECEDE «Sezioni ancora aperte»" % lab,
                n2.index("## \u00a74.6") < n2.index("## Sezioni ancora aperte"))
            chk("5%s il \u00a74.5 preesistente \u00e8 intatto" % lab,
                "testo che non va toccato" in n2)
            chk("6%s fine riga preservati" % lab,
                (read_target(p)[0].count("\r\n") == 0) if eol == "\n"
                else (read_target(p)[0].count("\n")
                      == read_target(p)[0].count("\r\n")))
            ok2, done2, bad2 = plan(read_target(p)[0])
            chk("7%s idempotenza" % lab, not ok2 and not bad2,
                "ok=%s bad=%s" % (ok2, bad2))

        p2 = os.path.join(td, "parziale.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace(EDITS[2][1], EDITS[2][2]).encode("utf-8"))
        chk("8  applicazione parziale: si ferma",
            _exits(lambda: apply_all(read_target(p2)[0])))

        p3 = os.path.join(td, "rotto.md")
        with open(p3, "wb") as fh:
            fh.write(corpo.replace(EDITS[1][1], "4. **Altro testo.**").encode("utf-8"))
        _, _, bad3 = plan(read_target(p3)[0])
        chk("9  ancora mancante: segnalata", len(bad3) == 1, str(bad3))

    print("=== SELFTEST paper2_risposta_46_patch ===")
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
    p = argparse.ArgumentParser(description="Scrive il \u00a74.6 nella risposta al referee")
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

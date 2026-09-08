#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_risposta_39_patch.py - chiude il §3.9 della risposta al referee e applica
i tre ritocchi della consegna §3.3.

Modifiche
---------
  1. §3.9  - riscritto da [BLOCCATA in parte] a [SCRITTA]: la verifica di
             tracciabilita' e' stata fatta, la Componente D resta nel paper, con
             la riserva scritta. Sostituzione di SEZIONE: dal titolo fino al
             titolo successivo, calcolata a runtime invece che ancorata a un
             blocco lungo.
  2. Risposta 8, punto 5 - non piu' "il suo input non e' tracciato".
  3. Tabella finale, riga §3.9.
  4. §4.2 - il pavimento a k=2,3 (39.43 e 12.10 su DUE punti), col suo limite.
  5. Titolo "Risposta 6 e §4.3" accorciato a "Risposta 6".
  6. OPZIONALE - "[IN ATTESA DI RUN]" del trattamento (B) nella tabella. Nella
     copia di progetto risulta gia' [SCRITTA]: se l'ancora manca non e' un
     errore, viene riportato.

I punti 1, 2 e 3 sono lo STESSO fatto in tre posti: o si muovono insieme o il
documento si contraddice. Il patcher li applica atomicamente.

Fine riga
---------
Il file si legge in binario e si rileva il terminatore dominante. Le modifiche
sono scritte con \\n e convertite prima dell'inserimento. Se il file ha fine riga
MISTI la normalizzazione toccherebbe anche righe non modificate: in quel caso
serve --allow-eol-normalise, e il fatto viene detto.

Sottocomandi
------------
  inspect    ancore, unicita', profilo dei fine riga. Non scrive.
  patch      applica. Scrive solo con --apply.
  verify     ricontrolla dopo la patch. Non scrive.
  selftest   costruisce un markdown sintetico e prova che le modifiche mordono.

Uscita ASCII pura: console Windows cp1252 senza UnicodeEncodeError.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"

H_39 = "## \u00a73.9 \u2014 Componente D **[BLOCCATA in parte]**"
H_39_NEW = "## \u00a73.9 \u2014 Componente D **[SCRITTA]**"
H_NEXT = "## \u00a71 \u2014 I due lati di *D*, separati"


# ---------------------------------------------------------------------------
# Il nuovo §3.9
# ---------------------------------------------------------------------------

SEC_39 = """## \u00a73.9 \u2014 Componente D **[SCRITTA]**

**La sovra-affermazione si ritira.** \u00abChiude la questione per chiunque\u00bb non \u00e8 sostenibile e non lo
scriveremo pi\u00f9. La riformulazione, nel perimetro del test:

> Entro la suite nwLH campionata, con questa pipeline e questa statistica, la risposta di *N*_H1 ai
> parametri cosmologici implica un vincolo 1\u03c3 su *w*\u2080 di **\u00b13.13** (NGC) e **\u00b15.71** (SGC), contro i
> \u00b10.06 del BAO DESI: **52\u00d7 e 95\u00d7 peggio**. \u00c8 un tetto di sensibilit\u00e0 **misurato** per questa
> statistica, non una chiusura della questione per chi usi un'altra filtrazione o un altro ensemble.

**Il secondo pezzo si \u00e8 sbloccato: la verifica di tracciabilit\u00e0 \u00e8 stata fatta.** Il rilievo era
fondato, e pi\u00f9 specifico di quanto sembrasse.

**Cosa c'era.** `phase0_data_manifest.json` porta un checksum per ciascuno dei 2000 campi di densit\u00e0
nwLH, e per il file dei parametri **solo un percorso** \u2014 nessun digest, in nessuno dei tre blocchi di
suite. E quel percorso **non risolve**: il file sta una directory pi\u00f9 in basso. Il default di
`--params` nello script ne nominava un terzo, anch'esso inesistente. Infine `config_hash`, che
sembrava poter ancorare gli ingressi, \u00e8 lo sha256 di `{nh1_path, params_path, n}`: hasha la
**descrizione** della configurazione, non i byte. La met\u00e0 dell'input che porta *N*_H1 era congelata;
quella che porta i regressori \u2014 l'unica cosa che la Componente D aggiunge \u2014 no.

**Cosa \u00e8 stato fatto**, in tre cancelli e in un ordine obbligato (emendamento 43).

**D-T1, i digest.** File dei parametri `bf0519c6\u20268d9e3e`, 156\u202f070 byte, 2001 righe, non modificato
dal 27 aprile \u2014 quattro mesi prima del run. Pi\u00f9 i due registri `per_mock`. `config_hash` resta com'\u00e8:
ridefinirlo darebbe a un campo due significati nel tempo. I digest dei byte sono campi **nuovi**.

**D-T3, le etichette.** Prima di riprodurre, il cancello sull'assunzione. L'intestazione del file
entra come **terza fonte**, l'unica delle tre indipendente da `PARAM_RANGES`: posizione e valori
dipendono entrambi da quella tabella, quindi se fosse sbagliata sbaglierebbero insieme a lei. Pi\u00f9 una
soglia assoluta sul punteggio di identificazione, **0.10, dichiarata prima del run** e dal disegno.
Osservata **0.010495**, su *M*_\u03bd, il cui estremo nominale \u00e8 0.00 mentre la suite campiona da 0.0102 \u2014
il bordo mancante, non rumore. Margine **9.5\u00d7**, quotato come misurato e non come i due ordini di
grandezza che la stima di disegno suggeriva.

**D-T2, la riproduzione.** Dichiarato prima del run: le quattordici correlazioni parziali devono
ridare i valori depositati **a precisione piena**, entrambi gli emisferi, nessuna tolleranza; un solo
*r* che si muove e la Componente D esce dal paper. Hanno ridato \u2014 identiche a diciassette cifre, a
nove giorni dal run originale \u2014 insieme a *R*\u00b2, attenuazione, deficit e `config_hash`, col cancello
2.1 che tiene a 35\u202f436.6860 / 312.9892 in NGC e 18\u202f712.9675 / 197.7874 in SGC.

**Tre cose che non erano nel piano e che riportiamo perch\u00e9 sono vere.**

La riproduzione ha ridato anche la **smentita**: P1 \u2014 |*r*(*w*\u2080)| < 0.05 \u2014 fallisce di nuovo in NGC a
+0.0549 e tiene in SGC a +0.0474, esattamente come registrato. Una predizione falsificata che si
riproduce identica \u00e8 evidenza migliore di una confermata.

I record della riproduzione li ha scritti lo script **patchato**, quelli canonici quello non
patchato: la riproduzione attraversa quindi anche le cinque modifiche e le dimostra **inerti sui
numeri**.

E l'ordine era obbligato. **D-T3 prima di D-T2**: una riproduzione fatta con la stessa tabella di
etichette hard-coded avrebbe riprodotto fedelmente anche un'etichetta sbagliata, perch\u00e9 non convalida
un'assunzione che entrambe le esecuzioni condividono.

**Cosa non rivendichiamo.** Non di aver difeso da una permutazione di colonne: `infer_names` lo
faceva gi\u00e0, confrontando gli **estremi** delle colonne e non le posizioni, e su questa suite gli
intervalli si separano. Il nuovo \u00e8 la terza fonte, la soglia con arresto, e la diagnostica
depositata nel record invece che stampata.

**E la riserva, che \u00e8 parte del risultato.** Il tracciamento \u00e8 **a posteriori per riproduzione**, non
congelamento contemporaneo. Il test non dimostra che il file di oggi sia bit-identico a quello di
agosto; dimostra che **produce esattamente le quantit\u00e0 riportate**. Per ogni numero che entra nel
paper le due cose coincidono, e la differenza la scriviamo invece di lasciarla implicita.

Il percorso sbagliato a riga 8043 del manifest resta dov'\u00e8: \u00e8 un artefatto congelato, e la
correzione si **registra** invece di riscriverlo.

---

"""


# ---------------------------------------------------------------------------
# Le modifiche puntuali
# ---------------------------------------------------------------------------

EDITS = [
    ("2. Risposta 8, punto 5",
     "5. **La Componente D.** Vedi la sezione dedicata: il suo input non \u00e8 tracciato.",
     "5. **La Componente D.** L'input \u00e8 ora tracciato, ma **a posteriori per riproduzione** e non\n"
     "   per congelamento contemporaneo: non \u00e8 dimostrato che il file dei parametri di oggi sia\n"
     "   bit-identico a quello letto dal run. Vedi \u00a73.9.",
     True),

    ("3. tabella finale, riga \u00a73.9",
     "| \u00a73.9 | **[BLOCCATA in parte]** | verifica di tracciabilit\u00e0 dell'input |",
     "| \u00a73.9 | **[SCRITTA]** | chiusa: input tracciato a posteriori per riproduzione, "
     "emendamento 43 |",
     True),

    ("4. \u00a74.2, il pavimento a k=2,3",
     "**Due cose che questo NON fa, e le diciamo.**",
     "**A *k*=2 e *k*=3 il pavimento poggia su DUE punti**, non sei: i quattro punti nuovi del\n"
     "blocco A sono stati girati alle erosioni 0 e 1 soltanto, perch\u00e9 servono il pavimento e il\n"
     "pavimento si calcola ai livelli del budget. Vale **39.43** e **12.10** in NGC, ed \u00e8 quotato\n"
     "come \u00abmassimo sui due punti depositati\u00bb. A quei livelli il budget **descrive e non\n"
     "classifica**: le soglie sono calibrate sul deficit a *k*=0,1, quindi l\u00ec pavimento e\n"
     "sistematico non hanno un termine di paragone.\n\n"
     "**Due cose che questo NON fa, e le diciamo.**",
     True),

    ("5. titolo Risposta 6",
     "## Risposta 6 e \u00a74.3 \u2014 La bit-identit\u00e0",
     "## Risposta 6 \u2014 La bit-identit\u00e0",
     True),

    ("6. trattamento (B) nella tabella (OPZIONALE)",
     "| \u00a71, trattamento (B) | **[IN ATTESA DI RUN]** |",
     "| \u00a71, trattamento (B) | **[SCRITTA]** |",
     False),
]


# ---------------------------------------------------------------------------
# Utilita'
# ---------------------------------------------------------------------------

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
    eol = "\r\n" if n_crlf >= n_lf else "\n"
    return txt, eol, n_crlf, n_lf


def norm(txt):
    return txt.replace("\r\n", "\n")


def replace_section(txt, header, next_header, block):
    """Sostituisce dalla riga del titolo fino al titolo successivo.

    Calcolata a runtime invece che ancorata a un blocco lungo: un'ancora di
    quaranta righe si spezza al primo carattere che non ho trascritto bene.
    """
    if txt.count(header) != 1:
        return None, "titolo %r: %d occorrenze" % (header[:40], txt.count(header))
    start = txt.index(header)
    if txt.count(next_header) != 1:
        return None, "titolo successivo %r: %d occorrenze" % (next_header[:40],
                                                              txt.count(next_header))
    end = txt.index(next_header)
    if end <= start:
        return None, "il titolo successivo precede il §3.9"
    return txt[:start] + block + txt[end:], None


def plan(txt):
    """(applicabili, gia_applicate, problemi) senza scrivere niente."""
    n = norm(txt)
    ok, done, bad = [], [], []
    if n.count(H_39_NEW) and not n.count(H_39):
        done.append("1. \u00a73.9")
    elif n.count(H_39) == 1 and n.count(H_NEXT) == 1:
        ok.append("1. \u00a73.9")
    else:
        bad.append("1. \u00a73.9: titolo %d occorrenze, successivo %d"
                   % (n.count(H_39), n.count(H_NEXT)))
    for name, old, new, required in EDITS:
        if n.count(new):
            done.append(name)
        elif n.count(old) == 1:
            ok.append(name)
        elif required:
            bad.append("%s: %d occorrenze dell'ancora" % (name, n.count(old)))
        else:
            done.append(name + "  [ancora assente, non richiesta]")
    return ok, done, bad


def apply_all(txt):
    """Tutte o nessuna."""
    ok, done, bad = plan(txt)
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    if not ok:
        return None, done
    n = norm(txt)
    if "1. \u00a73.9" in ok:
        n2, err = replace_section(n, H_39, H_NEXT, SEC_39)
        if err:
            fail(err)
        n = n2
    for name, old, new, required in EDITS:
        if name in ok:
            n = n.replace(old, new, 1)
    return n, done


# ---------------------------------------------------------------------------
# Sottocomandi
# ---------------------------------------------------------------------------

def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    print("=== %s ===" % args.target)
    print("  byte            : %d" % len(txt.encode("utf-8")))
    print("  sha256          : %s" % sha256_file(args.target))
    print("  fine riga       : CRLF=%d  LF=%d  ->  dominante %r%s"
          % (n_crlf, n_lf, eol, "   MISTI" if (n_crlf and n_lf) else ""))
    ok, done, bad = plan(txt)
    print("  da applicare    : %s" % (", ".join(ok) if ok else "nessuna"))
    print("  gia' applicate  : %s" % (", ".join(done) if done else "nessuna"))
    print("  problemi        : %s" % (", ".join(bad) if bad else "nessuno"))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    if n_crlf and n_lf and not args.allow_eol_normalise:
        fail("il file ha fine riga MISTI (CRLF=%d, LF=%d). Scrivere normalizzerebbe "
             "anche righe non modificate. Rilancia con --allow-eol-normalise se va bene."
             % (n_crlf, n_lf))
    new_n, done = apply_all(txt)
    print("=== PATCH %s ===" % args.target)
    if done:
        print("  gia' applicate: %s" % ", ".join(done))
    if new_n is None:
        print("  [OK] niente da fare.")
        return 0
    out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
    print("  %d -> %d byte" % (len(txt.encode("utf-8")), len(out.encode("utf-8"))))
    print("  sezioni toccate: \u00a73.9, Risposta 8, tabella finale, \u00a74.2, titolo Risposta 6")
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".prepatch39"
    if args.backup and not os.path.exists(bak):
        with open(bak, "wb") as fh:
            fh.write(txt.encode("utf-8"))
        print("  copia    : %s" % bak)
    tmp = args.target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(out.encode("utf-8"))
    os.replace(tmp, args.target)
    print("  [OK] scritto")
    return cmd_verify(args)


def cmd_verify(args):
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    ok_all = True
    print("")
    print("=== VERIFY ===")
    checks = [
        ("\u00a73.9 e' [SCRITTA]", n.count(H_39_NEW) == 1 and n.count(H_39) == 0),
        ("\u00a73.9 dice 'a posteriori per riproduzione'",
         "a posteriori per riproduzione" in n),
        ("\u00a73.9 non rivendica cio' che infer_names gia' faceva",
         "Cosa non rivendichiamo" in n),
        ("la riserva bit-identita' e' scritta", "bit-identico a quello di" in n),
        ("Risposta 8 punto 5 aggiornato",
         "il suo input non \u00e8 tracciato" not in n),
        ("tabella finale aggiornata",
         "| \u00a73.9 | **[BLOCCATA in parte]** |" not in n),
        ("\u00a74.2 cita il pavimento a k=2,3", "**39.43** e **12.10**" in n),
        ("titolo Risposta 6 accorciato",
         "## Risposta 6 e \u00a74.3" not in n and "## Risposta 6 \u2014 La bit-identit\u00e0" in n),
        ("nessuna sezione [BLOCCATA in parte] residua",
         "[BLOCCATA in parte]" not in n),
        ("il §1 successivo e' intatto", n.count(H_NEXT) == 1),
    ]
    for name, cond in checks:
        print("  [%s] %s" % ("ok" if cond else "NO", name))
        ok_all &= bool(cond)
    print("  esito: %s" % ("CLEAN" if ok_all else "SPORCO"))
    return 0 if ok_all else 3


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

SYNTH = """# Paper 2 \u2014 Risposta al referee report

---

## Risposta 8 \u2014 Cosa manca **[SCRITTA]**

4. **Il tiling.** I mock non sono su disco.
5. **La Componente D.** Vedi la sezione dedicata: il suo input non \u00e8 tracciato.
6. **Quali 200 mock**, come sopra.

---

## \u00a73.9 \u2014 Componente D **[BLOCCATA in parte]**

Testo vecchio che deve sparire del tutto.

**Quindi qui non decidiamo.**

---

---

## \u00a71 \u2014 I due lati di *D*, separati **[SCRITTA]**

Questa sezione non va toccata.

---

## \u00a74.2 \u2014 Provenienza delle soglie E3 **[SCRITTA]**

Contro il 25\u201378% del pavimento depositato.

**Due cose che questo NON fa, e le diciamo.** Non riduce il sistematico.

---

## Risposta 6 e \u00a74.3 \u2014 La bit-identit\u00e0 **[SCRITTA]**

Testo.

---

## Sezioni ancora aperte

| rilievo | stato | cosa aspetta |
|---|---|---|
| \u00a73.9 | **[BLOCCATA in parte]** | verifica di tracciabilit\u00e0 dell'input |
| \u00a74.6 | **[DA CERCARE]** | i mock esistono |
| \u00a71, trattamento (B) | **[IN ATTESA DI RUN]** | il run |
"""


def cmd_selftest(args):
    import tempfile
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    with tempfile.TemporaryDirectory() as td:
        for label, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "r_%s.md" % label)
            with open(p, "wb") as fh:
                fh.write(SYNTH.replace("\n", eol).encode("utf-8"))

            txt, det_eol, n_crlf, n_lf = read_target(p)
            chk("1%s fine riga rilevato" % label, det_eol == eol, repr(det_eol))

            ok, done, bad = plan(txt)
            chk("2%s tutte le sei modifiche sono applicabili" % label,
                len(ok) == 6 and not bad, "ok=%d bad=%s" % (len(ok), bad))

            new_n, _ = apply_all(txt)
            out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
            with open(p, "wb") as fh:
                fh.write(out.encode("utf-8"))

            t2 = read_target(p)[0]
            n2 = norm(t2)
            chk("3%s il testo vecchio del \u00a73.9 e' sparito" % label,
                "Testo vecchio che deve sparire" not in n2
                and "Quindi qui non decidiamo" not in n2)
            chk("4%s il \u00a71 successivo e' intatto" % label,
                "Questa sezione non va toccata" in n2 and n2.count(H_NEXT) == 1)
            chk("5%s il nuovo \u00a73.9 e' dentro" % label,
                H_39_NEW in n2 and "a posteriori per riproduzione" in n2)
            chk("6%s Risposta 8 punto 5 aggiornato" % label,
                "il suo input non \u00e8 tracciato" not in n2
                and "bit-identico" in n2)
            chk("7%s \u00a74.2: il paragrafo nuovo PRECEDE 'Due cose'" % label,
                n2.index("**39.43** e **12.10**")
                < n2.index("**Due cose che questo NON fa"))
            chk("8%s titolo Risposta 6 accorciato" % label,
                "## Risposta 6 \u2014 La bit-identit\u00e0" in n2
                and "## Risposta 6 e \u00a74.3" not in n2)
            chk("9%s trattamento (B) opzionale applicato" % label,
                "| \u00a71, trattamento (B) | **[SCRITTA]** |" in n2)
            chk("10%s fine riga preservati (nessun misto introdotto)" % label,
                (t2.count("\r\n") == 0) if eol == "\n"
                else (t2.count("\n") == t2.count("\r\n")))

            ok2, done2, bad2 = plan(t2)
            chk("11%s idempotenza: nulla resta da applicare" % label,
                not ok2 and not bad2, "ok=%s bad=%s" % (ok2, bad2))

        # ancora opzionale assente: non deve essere un errore
        p3 = os.path.join(td, "r_noopt.md")
        with open(p3, "wb") as fh:
            fh.write(SYNTH.replace(
                "| \u00a71, trattamento (B) | **[IN ATTESA DI RUN]** | il run |",
                "| \u00a71, trattamento (B) | **[SCRITTA]** | eseguito |").encode("utf-8"))
        ok3, done3, bad3 = plan(read_target(p3)[0])
        chk("12 ancora opzionale assente: nessun errore, riportata come fatta",
            not bad3 and any("OPZIONALE" in d for d in done3), str(done3))

        # ancora obbligatoria assente: DEVE fermare tutto
        p4 = os.path.join(td, "r_bad.md")
        with open(p4, "wb") as fh:
            fh.write(SYNTH.replace(
                "| \u00a73.9 | **[BLOCCATA in parte]** | verifica di tracciabilit\u00e0 dell'input |",
                "| \u00a73.9 | qualcosa d'altro |").encode("utf-8"))
        ok4, done4, bad4 = plan(read_target(p4)[0])
        chk("13 ancora obbligatoria assente: segnalata, e apply_all si ferma",
            bool(bad4) and _refuses(lambda: apply_all(read_target(p4)[0])), str(bad4))

    print("=== SELFTEST paper2_risposta_39_patch ===")
    n = 0
    for name, ok, detail in checks:
        if not ok:
            n += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), n))
    return 0 if not n else 1


def _refuses(fn):
    try:
        fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(description="Chiude il \u00a73.9 della risposta al referee")
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

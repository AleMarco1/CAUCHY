#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_315.py — porta checklist_paper2.md dalla rev. 3.14 alla 3.15.

Cinque modifiche, ciascuna ancorata a una stringa che deve comparire ESATTAMENTE
una volta nel file. Se un'ancora manca o e' ambigua lo script si ferma senza
scrivere: una checklist rattoppata a mano nel punto sbagliato e' peggio di una
non aggiornata.

  A  titolo: rev. 3.14 -> rev. 3.15
  B  blocco di changelog della 3.14, in coda a quello della 3.13
  C  voce 3.8: meccanismo e predizione 2 SOSTITUITI (unica sostituzione, non\n     aggiunta: il testo era falso)\n  D  voce 1.4b: nota di rettifica

Marcatore della revisione: ✦✧✦ (verificato assente nella 3.14).\nI blocchi di changelog storici NON si riscrivono: il punto 4 della 3.12 resta\nfalso e la 3.14 lo dichiara.

Sottocomandi
------------
  selftest   controlli, senza scrivere
  apply      applica (dry-run se manca --write)

Il file e' LF puro e UTF-8: si legge e si riscrive con newline='' per non
convertire nulla.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

MARK = "\u2726\u2727\u2726"          # ✦✧✦
DEFAULT_PATH = "checklist_paper2.md"

OLD_TITLE = ("### rev. 3.14 — 1 settembre 2026 — emendamento 18: il gauge fissa il lato e non "
             "l'origine; predizione 2 ritirata")
NEW_TITLE = ("### rev. 3.15 — 1 settembre 2026 — record 19-22; un valore superseded "
             "rientrato in un cancello; il difetto di fusione; k = 2,3 misurati")

ANCHOR_CHANGELOG = ("> 8. **Errore preso prima di qualunque run.** Né (B) né la linea B in spazio "
                    "reale sono girate:\n>    nessuna misura poggia sulla premessa falsa.")

CHANGELOG = """

> **Cosa cambia nella rev. 3.15.** Voci marcate **✦✧✦**. Seconda parte della sessione del 1
> settembre: chiusura del run a *k* = 2,3, tre record nuovi, un difetto di fusione, tre patch.
>
> 1. **Registro a ventidue record.** 19 ritiro di due sovra-affermazioni, 20 il sistematico entra
>    negli intervalli, 21 rettifica dei valori di D5b, 22 la loro vera provenienza.
>    `DOCUMENTED_AMENDMENTS = 22`, CLEAN.
> 1b. **Un valore dichiarato SUPERSEDED è rientrato come riferimento di un cancello.** Il 18 693.595
>    scritto in D5b è la metà SGC del `frozen_reference.mock_baseline` di M26, che la voce **2.1-E**
>    aveva dichiarato superato il **27 agosto** — «scarto ∓0.10 σ con segno opposto nei due
>    emisferi, firma della collisione di percorsi», e «fuori dal verdetto, citato per memoria».
>    Quattro giorni dopo è tornato dentro. E la firma si è ripresentata **nell'errore stesso**: NGC
>    portava il valore giusto, solo SGC quello contaminato.
> 2. **Difetto di fusione, trovato e corretto.** Dopo il run a *k* = 2,3 il registro ha **tre**
>    record per (regione, indice): 11 punti a *k* = 0,1, il solo B6 dall'emendamento 15, e 12 punti
>    a *k* = 2,3. `budget` e `analisi` fondevano sostituendo il dizionario del punto invece di
>    unirlo, e il record nuovo è l'**ultimo** per tutti e 400 gli indici: **zero celle su 2400**
>    conservavano `N_H1_k0`. Non mentivano in silenzio, cadevano con `KeyError`. `due_lati` era già
>    stato corretto il 31 agosto.
> 3. **Il termine (c) ha ritrovato la sua definizione.** Il cancello di riproduzione di `termc` ha
>    fallito con rapporto **√2** su tutti e quattro i valori: σ_carving = sd(Δ*N*)/√2, perché la
>    differenza appaiata è fra **due** estrazioni indipendenti. Riprodotti 7.69, 7.73, 6.78, 6.29
>    alla terza cifra, e σ_carve vale 108.7, 109.3, 95.9, 88.9 — i «109 e 89» del documento sono
>    quattro numeri, non due.
> 4. **`--levels`, e una decisione dichiarata.** A *k* = 2 e 3 i numeri si stampano ma **non si
>    emette né l'esito E1–E4 né la §5.4**: le soglie 53, 390 e 206 sono l'1.1% di un deficit
>    misurato a *k* = 0,1, e usarle altrove estenderebbe la regola in silenzio. Reversibile: serve
>    una regola registrata con le sue soglie, prima del run.
> 5. **`F_PHYS = 0.027` non è il range fisico.** È il lato piccolo di un intervallo asimmetrico. Le
>    decisioni passano a `F_PHYS_MAX_DEV = 0.0389`, e si riportano **entrambi** i rapporti, perché
>    la loro distanza — il 44% — è essa stessa il punto.
> 6. **Il codice non emette più nulla che il registro abbia ritirato.** L'estrapolazione «247 volte»
>    era ancora stampata sei ore dopo il record 19.
> 7. **A *k* = 2 il modello REGGE.** χ² = 6.9 su 3 dof, residui tutti sotto 0.8 SEM, e il **verdetto
>    di simmetria viene emesso: risposta DISPARI**, con il termine pari compatibile con zero
>    (−0.17σ). È la risposta AP più pulita che questo lavoro abbia prodotto, ed è a un livello che
>    il protocollo non contemplava."""

ANCHOR_14 = "      radiale — regge, perché il round-trip è una proprietà delle sole tabelle."

ITEM_14B = """
      **✦✧✦ Rettifica, record 21 e 22: i valori di D5b erano etichettati male, due su quattro erano
      sbagliati, e uno era un valore già dichiarato superato.** Stavano nel record 16 come
      `mock_mean_N_H1` accoppiato a `desi_N_H1`. Quel paio non esiste: il lato dati scrive
      `int(round(...))`, quindi *N*_H1^DESI è **intero**, e 31 889.930 non lo è. Tutti e quattro
      sono ⟨*N*_H1⟩_mock **al fiduciale**, ai due livelli di erosione. Letti dal registro:
      **35 423.575 / 31 889.925** (NGC), **18 694.420 / 16 477.950** (SGC).
      **✦✧✦ Da dove veniva davvero il 18 693.595, ed è la parte grave.** È la metà SGC del
      `frozen_reference.mock_baseline` di M26, 35 467.15 / 18 693.595, che la **voce 2.1-E** di
      questa stessa checklist aveva dichiarato **superseded il 27 agosto**, con la motivazione
      «scarto ∓0.10 σ **con segno opposto nei due emisferi**, firma della collisione di percorsi», e
      messo «fuori dal verdetto, citato per memoria». Quattro giorni dopo è tornato dentro come
      riferimento di un cancello bloccante. Non è una trascrizione distratta: è il **rientro di un
      valore che il programma aveva già identificato come contaminato**, dal difetto di collisione
      di percorso del Paper 1 §2.5 — lo stesso che il referee cita al §3.7.
      **La firma si è ripresentata nell'errore.** Il baseline superato vale 35 467.15 in NGC, e in
      D5b NGC c'era 35 423.575, cioè il valore **giusto**. Solo SGC portava quello contaminato: è
      esattamente il pattern a segno opposto fra emisferi che la 2.1-E aveva usato per scoprire il
      difetto la prima volta.
      **Due regole, e la seconda è quella che serve.** Il record 21 aveva adottato «un valore che
      entra in un cancello si legge dal registro, mai si trascrive». **Non sarebbe bastata**: il
      difetto non era la copia ma lo **stato** di ciò che veniva copiato. Il record 22 aggiunge: *un
      valore dichiarato **superseded**, **ritirato** o **contaminato** da qualunque record, cancello
      o voce di checklist non rientra per nessuna via, nemmeno come riferimento di un cancello
      nuovo; e prima che un valore diventi riferimento lo si cerca nel **registro degli emendamenti
      e nella checklist**, non solo in `results/`.* Questa è meccanica e la può applicare uno
      script, non la diligenza.
      *(Il flag `--baseline-verified` chiedeva di verificare i **valori**; l'invenzione erano i
      **nomi**, e la contaminazione era nello **stato**. Un cancello con i campi sbagliati non si
      convalida controllando i suoi numeri.)*"""

ANCHOR_D5B = ("""      **Cancello D5b — riproduzione ESATTA del baseline appaiato *n* = 200:** 35 423.575 / 31 889.930
      (NGC), 18 693.595 / 16 477.565 (SGC).""")

ITEM_D5B = ("""      **✦✧✦ Cancello D5b — riproduzione ESATTA della media mock al fiduciale, ai due livelli**
      (valori corretti dal record 21; i precedenti erano etichettati male e due erano sbagliati):
      **35 423.575** (*k* = 0) e **31 889.925** (*k* = 1) in NGC, **18 694.420** e **16 477.950** in
      SGC, letti da `results/paper2/due_lati.jsonl`, `two_sides[FID].mock_mean`. Tolleranza zero.
      I conteggi DESI al fiduciale — 28 256 / 23 790 e 15 122 / 12 011, **interi** — non fanno parte
      di D5b e si citano solo perché l'errore di etichetta non si ripeta.""")

ANCHOR_FASE3 = ("      senza regola pre-registrata**: questa voce riempie una lacuna dichiarata, "
                "non contraddice il\n      deposito.")

ITEMS_39_310 = """
- [x] **✦✧✦ 3.9 — Erosione *k* = 2 e 3 misurata. CHIUSA**, 1 set 2026, 200 realizzazioni per
      emisfero, 12 punti, 11.69 h + 11.55 h. `--erosions 2 3` sul runner mock, `--levels` su
      `paper2_fase3_analisi.py`.
      **Nessun esito E1–E4 e nessuna §5.4 a questi livelli**, per decisione dichiarata: le soglie
      depositate sono tarate sul deficit a *k* = 0,1. I numeri si riportano, il verdetto no.
      **✦✧✦ E a *k* = 2 il modello di forma REGGE.** χ² = **6.9** su 3 dof contro un limite di
      11.34, residui tutti sotto 0.8 SEM, punti perfettamente monotoni (+74.3, +22.7, 0, −36.9,
      −60.3, −113.7). Il **verdetto di simmetria è emesso: risposta DISPARI**, *a* = −2328.5
      (−17.2σ) con il termine pari **compatibile con zero** (−0.17σ). A *k* = 0, 1 e 3 il fit
      fallisce; a *k* = 2 no. È coerente con il §1(a) del referee: il rifiuto è un artefatto della
      struttura del lato dati assente dalla covarianza mock, e a un livello di erosione
      quell'artefatto non c'è.
      Δ*D*_max: −134.6 ± 9.7 (*k* = 2) e −102.9 ± 8.4 (*k* = 3) in NGC.
      **Il budget a questi livelli è BLOCCATO:** `TERM_C` ha solo le chiavi 0 e 1, perché il reseed
      del carving è stato girato prima che *k* = 2,3 esistessero. O si rigira con `--erosions 2 3`,
      o si dichiara che a quei livelli il budget non è disponibile.
- [ ] **✦✧✦ 3.10 — B1 è anomalo a *k* = 0 in NGC. DA DECIDERE COME RIPORTARLO.**
      Contro il fiduciale: B1 **+153.2 ± 11.7**, cioè 13σ, mentre B2 +5.3, B4 +7.6, B5 +39.2 e
      B6 −5.8 stanno tutti entro ±40. E Δ*D*_max è definito come B5 − B1, quindi **il numero che
      classifica E2 a *k* = 0 è dominato dal punto più fuori linea**, non da una risposta liscia
      alla deformazione. I residui del fit lo confermano: B1 +2.4 e B2 −2.4 SEM, adiacenti e di
      segno opposto. A *k* = 1 il quadro è diverso — +73.6, +53.4, +67.8, −24.7, −71.3 scende da B1
      a B6 — e a *k* = 2 è monotono.
      Che l'escursione sui cinque punti di linea B valga **153.2** contro un Δ*D*_max di 114.0 dice
      la stessa cosa: gli estremi non sono B1 e B5. Non è nel referee report e va deciso prima di
      scriverne."""

EDITS = [
    ("A  titolo 3.14 -> 3.15", OLD_TITLE, NEW_TITLE),
    ("B  blocco changelog 3.15", ANCHOR_CHANGELOG, ANCHOR_CHANGELOG + CHANGELOG),
    ("C  voce 1.4b: rettifica di D5b (record 21)", ANCHOR_14, ANCHOR_14 + ITEM_14B),
    ("D  voce 3.7: valori di D5b SOSTITUITI", ANCHOR_D5B, ITEM_D5B),
    ("E  voci 3.9 e 3.10 in coda alla Fase 3", ANCHOR_FASE3, ANCHOR_FASE3 + ITEMS_39_310),
]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    ok = os.path.isfile(path)
    chk("1  checklist presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)

    chk("2  file LF puro (nessun CRLF)", "\r" not in s)
    chk("3  parte dalla rev. 3.14", s.count(OLD_TITLE) == 1,
        "occorrenze=%d" % s.count(OLD_TITLE))
    chk("4  marcatore %s libero nella 3.14" % MARK, s.count(MARK) == 0,
        "occorrenze=%d" % s.count(MARK))
    chk("5  prerequisito: le voci 3.7/3.8 e la rettifica del gauge ci sono",
        ("3.7 — Trattamento" in s) and ("3.8 — Linea B" in s)
        and ("Rettifica, emendamento 18" in s))
    chk("6  idempotenza: la 3.15 non e' gia' applicata",
        (NEW_TITLE not in s) and ("record 21 e 22" not in s)
        and ("3.9 — Erosione" not in s))

    for i, (name, old, new) in enumerate(EDITS, start=7):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    out = apply_all(s)
    # 18 693.595 resta alla voce 2.1-E, dove e' storia legittima: li' e' il
    # valore superseded, citato per memoria. Va tolto dalla VOCE 3.7, non dal file.
    _v37 = out.split("3.7 — Trattamento")[1].split("3.8 — Linea B")[0]
    chk("11 i valori sbagliati sono RIMOSSI dalla voce 3.7 (non dal file: la 2.1-E resta)",
        ("18 693.595" not in _v37) and ("16 477.565" not in _v37)
        and ("18 693.595" in out))
    chk("12 e i valori corretti ci sono, con la loro fonte",
        ("31 889.925" in out) and ("18 694.420" in out) and ("16 477.950" in out)
        and ("two_sides[FID].mock_mean" in out))
    chk("12b entrambe le regole sono dichiarate, e la seconda e' quella che serve",
        ("mai si trascrive" in out) and ("Non sarebbe bastata" in out)
        and ("non rientra per nessuna via" in out))
    chk("12b2 la provenienza vera e' registrata, con data e voce",
        ("2.1-E" in out) and ("27 agosto" in out)
        and ("collisione di percorso" in out or "collisione di percorsi" in out))
    chk("12b3 la firma NGC-giusto / SGC-contaminato e' spiegata",
        ("35 467.15" in out) and ("segno opposto fra emisferi" in out))
    chk("12c il difetto di fusione e' registrato coi suoi numeri",
        ("zero celle su 2400" in out) and ("KeyError" in out))
    chk("12d il risultato di k=2 c'e', col verdetto emesso",
        ("verdetto di simmetria è emesso" in out) and ("6.9" in out)
        and ("compatibile con zero" in out))
    chk("12e l'anomalia di B1 e' registrata come DA DECIDERE",
        ("B1 è anomalo" in out) and ("DA DECIDERE" in out) and ("+153.2" in out))
    chk("13 riapplicazione bloccata (idempotenza sul risultato)",
        out.count(OLD_TITLE) == 0 and out.count(NEW_TITLE) == 1)
    chk("14 crescita del file plausibile (+60..+140 righe)",
        60 <= out.count("\n") - s.count("\n") <= 140,
        "delta=%d righe" % (out.count("\n") - s.count("\n")))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_checklist_315 ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def apply_all(s):
    for name, old, new in EDITS:
        if s.count(old) != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, s.count(old)))
        s = s.replace(old, new)
    return s


def cmd_apply(args):
    nfail = selftest(args.path)
    print("")
    if nfail:
        fail("selftest fallito (%d controlli): nessuna scrittura." % nfail)
    s = read(args.path)
    out = apply_all(s)

    diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                     fromfile="rev.3.14", tofile="rev.3.15", n=1))
    print("=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff))
    print("")
    print("righe: %d -> %d (+%d)" % (s.count("\n"), out.count("\n"),
                                     out.count("\n") - s.count("\n")))
    if not args.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    tmp = args.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, args.path)
    print("[OK] %s portato alla rev. 3.15" % args.path)
    back = read(args.path)
    print("verifica: rev.3.15 presente=%s  CRLF introdotti=%s"
          % (NEW_TITLE in back, "\r" in back))
    return 0


def main():
    p = argparse.ArgumentParser(description="checklist_paper2.md: rev. 3.14 -> 3.15")
    p.add_argument("--path", default=DEFAULT_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(func=lambda a: 1 if selftest(a.path) else 0)
    ap = sub.add_parser("apply")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(func=cmd_apply)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

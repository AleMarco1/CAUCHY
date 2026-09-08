#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_316.py — porta checklist_paper2.md dalla rev. 3.15 alla 3.16.

Cinque modifiche, ciascuna ancorata a una stringa che deve comparire ESATTAMENTE
una volta nel file. Se un'ancora manca o e' ambigua lo script si ferma senza
scrivere: una checklist rattoppata a mano nel punto sbagliato e' peggio di una
non aggiornata.

  A  titolo: rev. 3.15 -> rev. 3.16
  B  blocco di changelog della 3.14, in coda a quello della 3.13
  C  voce 3.8: meccanismo e predizione 2 SOSTITUITI (unica sostituzione, non\n     aggiunta: il testo era falso)\n  D  voce 1.4b: nota di rettifica

Marcatore della revisione: ✧✦✧ (verificato assente nella 3.15).\nI blocchi di changelog storici NON si riscrivono: il punto 4 della 3.12 resta\nfalso e la 3.14 lo dichiara.

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

MARK = "\u2727\u2726\u2727"          # ✧✦✧
DEFAULT_PATH = "checklist_paper2.md"

OLD_TITLE = ("### rev. 3.15 — 1 settembre 2026 — record 19-22; un valore superseded "
             "rientrato in un cancello; il difetto di fusione; k = 2,3 misurati")
NEW_TITLE = ("### rev. 3.16 — 2 settembre 2026 — record 23-31; §3.2 chiuso PARTIAL; "
             "§6 misurato a tre ampiezze; il turnover trovato")

ANCHOR_CHANGELOG = (">    (−0.17σ). È la risposta AP più pulita che questo lavoro abbia prodotto, "
                    "ed è a un livello che\n>    il protocollo non contemplava.")

CHANGELOG = """

> **Cosa cambia nella rev. 3.16.** Voci marcate **✧✦✧**. Giornata del 2 settembre: nove record,
> due test chiusi da run, cinque patch.
>
> 1. **Registro a trentuno record.** 23 D5c misura invece di fermare; 24 e 25 il test della
>    maschera-intersezione e il suo verdetto; 26 il termine (c) e i livelli mancanti; 27, 28, 29,
>    30, 31 il blocco A a tre ampiezze. `DOCUMENTED_AMENDMENTS = 31`.
> 2. **§3.2 CHIUSO: PARTIAL.** ρ mediana **0.496** contro R depositata e **0.474** contro il
>    pavimento, verdetto identico su entrambi i denominatori. Il canale voxel di bordo **dimezza**
>    il residuo del blocco A, non lo azzera. Per la regola del record 24 **il budget non si
>    riderivà**: il sistematico resta 41.9–60.3 e E2 resta a ~1σ. Cancello D6 tenuto: 304 823 e
>    167 269 voxel identici ai dodici punti.
> 3. **§6 MISURATO a tre ampiezze**, sei punti di linea A. Il dispari in SGC è **reale e isolato**
>    dal confondente del campionamento asimmetrico, e ha una **forma**: sale da zero, ha un massimo
>    a |α−1| ≈ 0.02–0.03, e ricade. Entrambe le regole dichiarate danno **TURNOVER**, mediane 0.680
>    e 0.395.
> 4. **Una predizione dichiarata è stata falsificata.** La potenza estrapolata del record 30
>    prediceva |pari| = 32.4 / 75.4 / 15.1 alla terza ampiezza; misurato **18.5 / 23.5 / 3.5**,
>    sovrastima di 1.8–4.3 volte. Non riparata, nessun esponente rifittato.
> 5. **Due letture del rapporto di Fase 3 sono ritirate.** L'«offset costante» del blocco A in NGC
>    (record 29): non è né costante né crescente. E l'estrapolazione «247 volte» era ancora
>    **stampata dal codice** sei ore dopo il record 19: tolta.
> 6. **D5c ha sparato al FIDUCIALE** e la misura ha smontato la premessa del record 17: il clipping
>    non dipende dalla deformazione, vale 0–3 su ~218 000 a ogni punto, ed è **dentro i valori
>    congelati** (D4b li riproduce esatti col clipping presente). 45 clippati su 45 finiscono **in
>    maschera**, il che confuta un mio argomento. Soglia zero irraggiungibile → `D5C_MODE =
>    "measure"` per i due run lunghi, deroga dichiarata col suo costo.
> 7. **Il difetto di fusione trovato ieri è corretto** in `budget` e `analisi`; `due_lati` lo era
>    già. E `--levels` è applicato: a *k* = 2,3 **nessun esito E1–E4 e nessuna §5.4**, per decisione
>    dichiarata.
> 8. **`F_PHYS = 0.027` non è il range fisico** ed è affiancato da `F_PHYS_MAX_DEV = 0.0389`. Le
>    decisioni passano alla deviazione massima e si riportano **entrambi** i rapporti, perché la
>    loro distanza — il 44% — è essa stessa il risultato.
> 9. **Tre errori miei, tutti registrati e tutti presi prima di un run:** i valori di D5b erano un
>    baseline dichiarato **superseded** il 27 agosto (record 22); gli α degli specchi erano stati
>    **invertiti da *c*** invece che letti da `LINE_A` (record 28); e la regola del record 27 non
>    dichiarava l'aggregazione (record 29)."""

ANCHOR_FASE3 = ("      la stessa cosa: gli estremi non sono B1 e B5. Non è nel referee report e va "
                "deciso prima di\n      scriverne.")

ITEMS_311_312 = """
- [x] **✧✦✧ 3.11 — Maschera-intersezione, §3.2 del referee. CHIUSA: PARTIAL**, 2 set 2026, record
      24 (disegno) e 25 (verdetto). Due passate, lato dati, dodici punti per emisfero.
      **L'ipotesi, sua e adottata come la scrive lui.** Il cancello 2.2a misura 216 voxel = 34
      generatori, cioè un'elasticità locale di **1.71** contro la globale **1.08** del 2.7: i voxel
      che commutano al bordo sono più ricchi di anelli di ~1.6. Il termine (e) sottrae con una
      pendenza **media**, quindi il residuo di quella sottrazione vale ~0.588 volte l'ampiezza del
      canale.
      **Il disegno.** Maschera-intersezione — i voxel in maschera a **tutti** i dodici punti —
      applicata identica ovunque, così `n_valid_voxels` è **costante per costruzione** e il termine
      (e) **non esiste** invece di essere sottratto.
      **Cancello D6, tolleranza zero: TENUTO.** 304 823 voxel identici ai dodici punti NGC,
      167 269 in SGC.
      **Dichiarato prima del run:** l'intersezione è più piccola di ogni maschera, quindi *N*_H1
      scende ovunque e il fiduciale **non** riproduce 28 256 / 15 122 — infatti dà 27 978 e 14 659.
      Il cancello di riproduzione abituale non si applica; D6 ne prende il posto.
      **✧✦✧ VERDETTO: PARTIAL.** ρ mediana **0.4962** contro R depositata, **0.4741** contro il
      pavimento (f); i due denominatori concordano, quindi nessuna scelta è stata fatta. Il canale
      **dimezza** il residuo del blocco A e non lo azzera: l'ipotesi del referee è confermata **a
      metà**. Per la regola del record 24 **il budget NON si riderivà** — un parziale non si
      arrotonda al verdetto favorevole.
      **Un limite della regola, registrato nel record 25.** Il record 24 non attaccava
      un'incertezza a ρ, e R è la rms di **due** residui per caso: il *verdetto* è robusto — per
      IDENTIFIED servirebbe un fattore due — ma il **valore** 0.4962 non regge tre cifre. Nella
      risposta si scrive «circa la metà».
      **Conseguenza sul record 20.** Un PARTIAL non decide se residuo non attribuito e rifiuto del
      χ² siano lo stesso oggetto: si chiude **la via**, non la domanda.
- [x] **✧✦✧ 3.12 — Blocco A a TRE ampiezze, §6 del referee. MISURATO**, 2 set 2026, record 27–31.
      Sei punti di linea A, quattro nuovi, otto run deterministici.
      **Il confondente che rendeva illeggibili i due punti originali.** A1 e A3 stanno a |α−1| =
      0.0275 e **0.0406**, distanze **diverse** da 1: con due punti asimmetrici pari e dispari
      **non si separano**. Una risposta puramente pari e quadratica darebbe A3/A1 = 2.18, cioè un
      **37%** di dispari apparente. NGC *k*=0 misura 2.78: **compatibile**, quindi il suo «offset
      costante» non era stabilito. SGC no, e per una ragione che non usa modelli: **una funzione
      pari non può cambiare segno**, e SGC *k*=0 dà −30 e +30.
      **I punti.** A1m 1.0275 e A3m 0.9594 (specchi esatti, record 27–28); poi A0 0.981373 e A0m
      1.018627 alla terza ampiezza **0.018627**, la continuazione **geometrica** verso il basso, così
      le tre ampiezze sono equispaziate in log a rapporto 1.4764. A3m è **sotto** il range fisico
      [0.9725, 1.0406]: sul blocco A il segnale è zero **per teorema** a qualunque α, quindi il test
      nullo resta valido. Dichiarato, non nascosto.
      **Il vincolo che ha reso decidibile la forma:** residuo(α = 1) = **zero esatto**, perché α = 1
      *è* il fiduciale. Il residuo scende fra 0.0275 e 0.0406, quindi ha un **massimo** in
      (0, 0.0406). Due ampiezze danno un rapporto, tre danno una forma.
      **✧✦✧ VERDETTO: TURNOVER su entrambe le regole**, dichiarate separate nel record 30. Pari
      mediana **0.6797**, dispari **0.3953**, entrambe sotto la soglia di 0.75. Nessun cambio di
      segno, quindi il ramo `SIGN_CHANGE` non è servito.
      **✧✦✧ E una predizione dichiarata è FALSIFICATA.** La potenza estrapolata dalle due ampiezze
      note prediceva |pari| = **32.4 / 75.4 / 15.1** alla terza; misurato **18.5 / 23.5 / 3.5**,
      sovrastima di **1.8, 3.2, 4.3**. Il record 30 diceva che quella estrapolazione «deve fallire
      da qualche parte»: fallisce **alla prima ampiezza sotto**, non nel limite. Non riparata.
      **Cosa è stabilito:** il dispari in SGC è **reale**, isolato dal confondente, e ha una forma
      con un massimo a |α−1| ≈ 0.02–0.03 — due o tre voxel di spostamento al bordo su un cubo di
      128. **Coerente con** un effetto di registrazione della griglia, e **non** con l'offset
      costante né con un artefatto monotono. **Cosa non lo è:** la causa. Tre ampiezze danno forma e
      scala, non un meccanismo.
      **Un numero da non citare:** SGC *k*=0 pari, ρ = 0.0625, formato da −0.5 e −8.0 su una parte
      piccola ovunque che cambia direzione due volte. È rumore di discretizzazione su interi. Resta
      **dentro** la mediana perché il record 30 aveva dichiarato la soglia sulla mediana e non sui
      casi singoli: escluderlo adesso sarebbe scegliere dopo aver visto.
      **Il pavimento (f) è ancora da definire**, e i sei numeri decomposti qui **non sono** residui
      di pavimento: sono escursioni **grezze**. Il pavimento depositato è la rms **dopo** la
      sottrazione del canale voxel, e le due quantità non si somigliano — a A1, NGC *k*=1, il grezzo
      è +1/+35 e il depositato −10.0/−10.3. I residui sottratti ai quattro punti nuovi **non sono
      ancora stati calcolati**."""

EDITS = [
    ("A  titolo 3.15 -> 3.16", OLD_TITLE, NEW_TITLE),
    ("B  blocco changelog 3.16", ANCHOR_CHANGELOG, ANCHOR_CHANGELOG + CHANGELOG),
    ("C  voci 3.11 e 3.12 in coda alla Fase 3", ANCHOR_FASE3, ANCHOR_FASE3 + ITEMS_311_312),
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
    chk("3  parte dalla rev. 3.15", s.count(OLD_TITLE) == 1,
        "occorrenze=%d" % s.count(OLD_TITLE))
    chk("4  marcatore %s libero nella 3.15" % MARK, s.count(MARK) == 0,
        "occorrenze=%d" % s.count(MARK))
    chk("5  prerequisito: le voci 3.9 e 3.10 della 3.15 ci sono",
        ("3.9 — Erosione" in s) and ("3.10 — B1 è anomalo" in s))
    chk("6  idempotenza: la 3.16 non e' gia' applicata",
        (NEW_TITLE not in s) and ("3.11 — Maschera" not in s)
        and ("3.12 — Blocco A" not in s))

    for i, (name, old, new) in enumerate(EDITS, start=7):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    out = apply_all(s)
    chk("11 il §3.2 e' chiuso con verdetto e cancello, non solo nominato",
        ("VERDETTO: PARTIAL" in out) and ("304 823" in out) and ("D6" in out))
    chk("12 il §6 riporta TURNOVER su entrambe le regole, con le mediane",
        ("TURNOVER su entrambe" in out) and ("0.6797" in out) and ("0.3953" in out))
    chk("12b la predizione falsificata e' registrata come tale",
        ("32.4 / 75.4 / 15.1" in out) and ("18.5 / 23.5 / 3.5" in out)
        and ("Non riparata" in out))
    chk("12c il numero non citabile e' segnalato e NON tolto",
        ("0.0625" in out) and ("Resta\n      **dentro** la mediana" in out))
    chk("12d cio' che NON e' stabilito e' detto: la causa",
        ("Cosa non lo è:** la causa" in out) and ("Coerente con" in out))
    chk("12e il pavimento e' dichiarato ANCORA da definire, con la distinzione",
        ("non sono** residui" in out) and ("escursioni **grezze**" in out))
    chk("13 riapplicazione bloccata (idempotenza sul risultato)",
        out.count(OLD_TITLE) == 0 and out.count(NEW_TITLE) == 1)
    chk("14 crescita del file plausibile (+80..+180 righe)",
        80 <= out.count("\n") - s.count("\n") <= 180,
        "delta=%d righe" % (out.count("\n") - s.count("\n")))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_checklist_316 ===")
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
                                     fromfile="rev.3.15", tofile="rev.3.16", n=1))
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
    print("[OK] %s portato alla rev. 3.16" % args.path)
    back = read(args.path)
    print("verifica: rev.3.16 presente=%s  CRLF introdotti=%s"
          % (NEW_TITLE in back, "\r" in back))
    return 0


def main():
    p = argparse.ArgumentParser(description="checklist_paper2.md: rev. 3.15 -> 3.16")
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

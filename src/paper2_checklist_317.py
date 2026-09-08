#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_317.py — porta checklist_paper2.md dalla rev. 3.16 alla 3.17.

Cinque modifiche, ciascuna ancorata a una stringa che deve comparire ESATTAMENTE
una volta nel file. Se un'ancora manca o e' ambigua lo script si ferma senza
scrivere: una checklist rattoppata a mano nel punto sbagliato e' peggio di una
non aggiornata.

  A  titolo: rev. 3.16 -> rev. 3.17
  B  blocco di changelog della 3.14, in coda a quello della 3.13
  C  voce 3.8: meccanismo e predizione 2 SOSTITUITI (unica sostituzione, non\n     aggiunta: il testo era falso)\n  D  voce 1.4b: nota di rettifica

Marcatore della revisione: ✦✦✦✦ (verificato assente nella 3.16).\nI blocchi di changelog storici NON si riscrivono: il punto 4 della 3.12 resta\nfalso e la 3.14 lo dichiara.

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

MARK = "\u2726\u2726\u2726\u2726"          # ✦✦✦✦
DEFAULT_PATH = "checklist_paper2.md"

OLD_TITLE = ("### rev. 3.16 — 2 settembre 2026 — record 23-31; §3.2 chiuso PARTIAL; "
             "§6 misurato a tre ampiezze; il turnover trovato")
NEW_TITLE = ("### rev. 3.17 — 4 settembre 2026 — record 32-38; TRE meccanismi esclusi e "
             "il fattore 2-6 sopravvive; D5c chiuso")

ANCHOR_CHANGELOG = (">    **invertiti da *c*** invece che letti da `LINE_A` (record 28); e la "
                    "regola del record 27 non\n>    dichiarava l'aggregazione (record 29).")

CHANGELOG = """

> **Cosa cambia nella rev. 3.17.** Voci marcate **✦✦✦✦**. Giornate del 3 e 4 settembre: sette
> record, tre run lunghi, e il risultato più importante del programma dopo il deficit stesso.
>
> 1. **Registro a trentotto record.** 32 e 33 la regola del pavimento e la sua rettifica; 34 la
>    deroga D5c da lista a condizione; 35 il run in spazio reale NULLO; 36 la soglia di D5c; 37 il
>    meccanismo RSD falsificato; 38 il trattamento (B). `DOCUMENTED_AMENDMENTS = 38`.
> 2. **✦✦✦✦ TRE MECCANISMI ESCLUSI, E IL FATTORE SOPRAVVIVE A TUTTI E TRE.** Il lato mock risponde
>    all'AP **2–6 volte** più del lato dati. Non è il canale voxel di bordo (record 25: lo
>    **dimezza**, non lo azzera). Non è l'RSD (record 37: togliendolo del tutto, **±13%**). Non è la
>    rigenerazione del trattamento (record 38: congelando le osservabili, **±10%**). Una discrepanza
>    robusta, riproducibile e **non spiegata** fra la risposta dell'ensemble e quella del campo
>    osservato: si riporta come **risultato**, con i tre meccanismi che non è.
> 3. **✦✦✦✦ E la firma si ripete.** Sotto trattamento (B) il rapporto **scende in NGC e sale in
>    SGC**; in spazio reale identico, 0.920/0.942 contro 1.120/1.131. Due manipolazioni diverse, la
>    stessa asimmetria fra emisferi. Un meccanismo che si limitasse a scalare la risposta non
>    potrebbe produrlo: è il **vincolo più forte** che abbiamo sulla causa.
> 4. **Il trattamento (B) ha superato tutti e quattro i cancelli.** D5a muto e 400 celle fiduciali
>    bit-identiche; D5b **esatto** su tutti e quattro i valori del record 21; `n_sel` costante ai sei
>    punti in 400 realizzazioni su 400; D5c massimo 8 contro soglia 28. E le SEM sono **più piccole**
>    che sotto (A): misura migliore, predizione che fallisce lo stesso.
> 5. **Dodici ore perse, e la regola che ne è uscita.** Il primo run in spazio reale è stato
>    **NULLO**: 2400 celle su 2400 identiche al run principale, perché il flag `--real-space` era
>    cablato ai due capi e **collegato da niente** — `M.REAL_SPACE` non veniva mai assegnato.
>    Ventuno controlli verificavano che il flag esistesse; nessuno che qualcuno lo **accendesse**.
>    **Regola adottata:** un flag che cambia una misura si verifica con un run che **produce numeri
>    diversi**, non ispezionando il percorso di codice.
> 6. **D5c è chiuso.** Soglia **28**, derivata dall'**effetto** e non dai quantili: è il numero di
>    voxel il cui impilamento raggiunge **metà** della SEM più piccola. La deroga aperta il 1
>    settembre è finita.
> 7. **Il pavimento (f) è il massimo dei moduli**, non una rms — perché il massimo è ≥ della rms di
>    qualunque sottoinsieme, quindi la regola **può solo alzarlo**. La prima forma proposta non
>    aveva quella proprietà e la rettifica è nel record 33.
> 8. **Due errori miei, entrambi presi prima che contassero.** Il pavimento a sei punti non era
>    calcolabile dopo i run lato dati, perché `gather` costruisce il blocco A dal **lato mock**
>    (record 34). E il clipping non è geometria di bordo ma è **interamente RSD** — zero clippati su
>    2400 in spazio reale — dopo che avevo concluso il contrario generalizzando dalla **dimensione**
>    dell'eccesso alla sua **causa** (record 37)."""

ANCHOR_312 = "      ancora stati calcolati**."

ITEMS_313_315 = """
- [x] **✦✦✦✦ 3.13 — Il pavimento (f) è il MASSIMO dei moduli. REGOLA DICHIARATA**, 2 set 2026,
      record 32 e 33.
      **La regola.** (f) = **max |residuo sottratto|** sui punti del blocco A, per emisfero e
      livello, in gauge `regauged`.
      **La proprietà che la rende adottabile dopo aver visto i grezzi**, ed è **dimostrata**: per
      qualunque insieme finito rms = √(media(*x*²)) ≤ √(max(*x*²)) = max|*x*|, quindi il massimo è ≥
      della rms di **qualunque** sottoinsieme — coppia depositata inclusa — per **ogni** valore che i
      residui prenderanno. Non può abbassare il pavimento, quindi non può fabbricare un sistematico
      favorevole.
      **✦✦✦✦ Rettifica, record 33.** La prima forma — «massimo fra le rms per ampiezza» —
      sosteneva la stessa proprietà e **non ce l'aveva**: `BLOCK_A = ("A1", "A3")` e quei due punti
      stanno a |α−1| = 0.0275 e 0.0406, ampiezze **diverse**, quindi il depositato non è la rms a
      un'ampiezza. Con residui −10.0, −10.3, 0, 0 le rms per ampiezza darebbero 7.07 e 7.28 contro
      un depositato di 10.15: **avrebbe abbassato**.
      **Stato attuale: il pavimento è il massimo su DUE punti**, cioè il cambio di regola senza i
      punti nuovi: **10.27, 18.07, 26.35, 33.54** contro i depositati 10.1, 17.7, 20.2, 32.5. Sale
      ovunque, come garantito. **SGC *k*=1 sale del 30%**, perché i suoi residui sono +26.3 e −10.9:
      la rms li media, il massimo prende il grande.
      **Il cancello è passato:** la rms sulla coppia {A1, A3} riproduce 10.12, 17.73, 20.16 e 32.47.
      **Diventa il pavimento a sei punti solo dopo il run mock del blocco A**, perché `gather`
      costruisce quelle righe dal **lato mock** e i quattro punti nuovi sono stati girati solo sul
      lato dati. Fino ad allora si cita come «massimo sui due punti depositati», non «sui sei».
- [x] **✦✦✦✦ 3.14 — Linea B in spazio reale, §3.8. MISURATO al secondo tentativo**, 3 set 2026,
      record 35 e 37.
      **Il primo run è stato NULLO**, dodici ore: 2400 celle su 2400 identiche al run principale.
      `REAL_SPACE` era una variabile di modulo in `phase8` e `--real-space` un flag del runner che
      finiva nel record e nella chiave; **la riga che le collegava non è mai stata scritta**.
      Ventuno controlli verificavano che il flag esistesse, entrasse nella chiave, entrasse nel
      record, azzerasse `v_los` dentro `phase8`, e che ogni nome fosse legato. **Nessuno verificava
      che qualcuno lo accendesse.** E lo smoke non poteva prenderlo: gira apposta **senza** il flag,
      e da lì inerzia e scollegamento sono indistinguibili.
      **✦✦✦✦ Regola adottata:** un flag che cambia una misura si verifica con un run che **produce
      numeri diversi**, non ispezionando il codice. Il rilancio ha richiesto uno smoke **con** il
      flag che **fallisse se i numeri coincidevano**.
      **Il risultato, al secondo tentativo:** Δ_mock in spazio reale vale **−200.60, −162.29,
      −152.37, −125.63** contro −218.0, −172.3, −136.0, −111.1: rapporti **0.920, 0.942, 1.120,
      1.131**. Togliere **completamente** l'RSD cambia la risposta del **±13%**.
      **✦✦✦✦ Il meccanismo dei record 16 e 18 è FALSIFICATO.** Prevedeva che senza RSD la risposta
      mock in gran parte sparisse. Non sparisce. Non riparato, nessuna riformulazione.
      **E un mio errore corretto:** `n_clipped` è **zero ovunque** in spazio reale, contro 0–9 in
      spazio di redshift. Il clipping è **interamente RSD**. Avevo concluso che fosse geometria di
      bordo perché la maggior parte degli eccessi era sotto 0.5 Mpc/h: velocità piccole danno
      spostamenti piccoli, e avevo generalizzato dalla **dimensione** dell'eccesso alla sua **causa**.
- [x] **✦✦✦✦ 3.15 — Trattamento (B), osservabili fisse. MISURATO**, 4 set 2026, record 38.
      200 realizzazioni per emisfero, sei punti, 5.77 h + 5.71 h.
      **Tutti e quattro i cancelli passati.** **D5a** muto, e il segno esterno è che **400 celle su
      2400 sono identiche** al run principale: sono esattamente le fiduciali, dove (B) riproduce (A)
      bit a bit per costruzione. **D5b esatto**: 35 423.575, 31 889.925, 18 694.420, 16 477.950,
      alla terza cifra su tutti e quattro. **`n_sel` costante** ai sei punti in 400 realizzazioni su
      400 — sotto (A) varia. **D5c** massimo 8 contro soglia 28.
      **✦✦✦✦ La predizione 1 del record 16 è FALSIFICATA.** Prevedeva che sotto (B) il rapporto
      scendesse verso 1. Va da **2.096, 2.328, 2.230, 5.555** sotto (A) a **1.905, 2.166, 2.286,
      6.117** sotto (B): giù del 7–9% in NGC, **su** del 3% e del 10% in SGC.
      **E non è questione di precisione:** le SEM sotto (B) sono **9.62, 9.10, 7.67, 6.67**, più
      piccole che sotto (A), perché congelare la selezione toglie una sorgente di rumore. Misura
      migliore, predizione che fallisce lo stesso.
      **Conseguenza sul §1 della risposta:** che (A) e il lato dati subiscano perturbazioni diverse
      resta vero **come fatto sul codice**, ma **(B) È il trattamento del lato dati** e risponde
      comunque il doppio. La differenza di trattamento **non è ciò che produce il fattore**.
- [x] **✦✦✦✦ 3.16 — D5c chiuso. SOGLIA 28**, 4 set 2026, record 36.
      **Derivata dall'effetto, non dai quantili.** Il cancello 2.2a dà 0.1574 generatori per voxel;
      la SEM più piccola vale 8.7; il numero di voxel il cui effetto raggiunge **metà** di quella
      SEM è 0.5 × 8.7 / 0.1574 = **27.6 → 28**.
      **Perché metà**, con due argomenti indipendenti che stringono da lati opposti. In quadratura
      un termine aggiunge +3.1% a un quarto, +5.4% a un terzo, **+11.8% a metà**, +41.4% alla
      parità: metà è dove «trascurabile» smette di essere difendibile. E la coda è **pesante** —
      sotto Poisson(0.703) un 9 ha probabilità 6 × 10⁻⁸ e uno è stato osservato — quindi una soglia
      a un quarto, 13.8, starebbe solo 1.5× sopra il massimo e sparerebbe sulla crescita ordinaria.
      Metà dà 3.1×. L'unità è scartata dall'altro lato: a 55 voxel il clipping contribuirebbe quanto
      l'errore campionario e dovrebbe entrare nel **budget**, non in un cancello.
      **✦✦✦✦ La copertura è PARZIALE, e va dichiarato.** Il campo `d5c_n_clipped` esiste solo nei
      record scritti **dopo** la patch del 1 settembre. Applicata all'indietro dà: 2400 misure e
      massimo **0** in spazio reale; 2400 e massimo **8** sotto (B); ma solo **69** misure nel
      registro principale, perché i 1200 record del run a dodici punti e i 400 a *k*=2,3 sono
      **precedenti allo strumento**.
      **Quindi la misura depositata di Fase 3 non è coperta da D5c**, e la frase corretta è «la
      soglia copre i run dal 1 settembre; la misura depositata precede lo strumento, e il suo
      clipping è limitato dalla stessa taratura a **≤ 1.42 generatori**, il 16% della SEM più
      piccola». Non «D5c è stato applicato a tutto».
      *(Il clipping c'era anche allora: il record 23 lo dimostra, perché D4b riproduce i valori
      congelati **con il clipping presente**.)*"""

EDITS = [
    ("A  titolo 3.16 -> 3.17", OLD_TITLE, NEW_TITLE),
    ("B  blocco changelog 3.17", ANCHOR_CHANGELOG, ANCHOR_CHANGELOG + CHANGELOG),
    ("C  voci 3.13, 3.14, 3.15, 3.16 in coda alla Fase 3", ANCHOR_312,
     ANCHOR_312 + ITEMS_313_315),
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
    chk("3  parte dalla rev. 3.16", s.count(OLD_TITLE) == 1,
        "occorrenze=%d" % s.count(OLD_TITLE))
    chk("4  marcatore %s libero nella 3.16" % MARK, s.count(MARK) == 0,
        "occorrenze=%d" % s.count(MARK))
    chk("5  prerequisito: le voci 3.11 e 3.12 della 3.16 ci sono",
        ("3.11 — Maschera" in s) and ("3.12 — Blocco A" in s))
    chk("6  idempotenza: la 3.17 non e' gia' applicata",
        (NEW_TITLE not in s) and ("3.13 — Il pavimento" not in s)
        and ("3.15 — Trattamento (B)" not in s))

    for i, (name, old, new) in enumerate(EDITS, start=7):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    out = apply_all(s)
    chk("11 i tre meccanismi esclusi sono elencati insieme, coi numeri",
        ("dimezza" in out) and ("±13%" in out) and ("±10%" in out))
    chk("12 la firma opposta fra emisferi e' registrata come vincolo",
        ("scende in NGC e sale in\n>    SGC" in out) and ("1.120/1.131" in out))
    chk("12b il run nullo e la regola che ne esce sono registrati",
        ("2400 celle su 2400" in out) and ("produce numeri\n>    diversi" in out))
    chk("12c la soglia 28 ha la sua derivazione, non solo il valore",
        ("27.6 → 28" in out) and ("+11.8% a metà" in out) and ("3.1×" in out))
    chk("12d la copertura PARZIALE di D5c e' dichiarata, non taciuta",
        ("solo **69**" in out) and ("precede lo strumento" in out)
        and ("≤ 1.42 generatori" in out))
    chk("12e il pavimento e' su DUE punti, e si dice fino a quando",
        ("massimo su DUE punti" in out) and ("run mock del blocco A" in out))
    chk("12f i quattro cancelli di (B) sono riportati come passati",
        ("400 celle su\n      2400 sono identiche" in out) and ("D5b esatto" in out))
    chk("13 riapplicazione bloccata (idempotenza sul risultato)",
        out.count(OLD_TITLE) == 0 and out.count(NEW_TITLE) == 1)
    chk("14 crescita del file plausibile (+90..+200 righe)",
        90 <= out.count("\n") - s.count("\n") <= 200,
        "delta=%d righe" % (out.count("\n") - s.count("\n")))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_checklist_317 ===")
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
                                     fromfile="rev.3.16", tofile="rev.3.17", n=1))
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
    print("[OK] %s portato alla rev. 3.17" % args.path)
    back = read(args.path)
    print("verifica: rev.3.17 presente=%s  CRLF introdotti=%s"
          % (NEW_TITLE in back, "\r" in back))
    return 0


def main():
    p = argparse.ArgumentParser(description="checklist_paper2.md: rev. 3.16 -> 3.17")
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

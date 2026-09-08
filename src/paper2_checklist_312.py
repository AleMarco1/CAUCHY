#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_312.py — porta checklist_paper2.md dalla rev. 3.11 alla 3.12.

Quattro modifiche, ciascuna ancorata a una stringa che deve comparire ESATTAMENTE
una volta nel file. Se un'ancora manca o e' ambigua lo script si ferma senza
scrivere: una checklist rattoppata a mano nel punto sbagliato e' peggio di una
non aggiornata.

  A  titolo: rev. 3.11 -> rev. 3.12
  B  blocco di changelog della 3.12, in coda a quello della 3.11
  C  voce 1.4b: emendamento 16, i due trattamenti nominati
  D  voci 3.7 e 3.8: trattamento (B) e linea B in spazio reale

Marcatore della revisione: ✦✧✧ (verificato assente nella 3.11).

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

MARK = "\u2726\u2727\u2727"          # ✦✧✧
DEFAULT_PATH = "checklist_paper2.md"

OLD_TITLE = ("### rev. 3.11 — 31 agosto 2026 — B6 misurato, cancello 5.3 costruito, "
             "Fase 3 chiusa salvo il 3.3")
NEW_TITLE = ("### rev. 3.12 — 31 agosto 2026 — emendamento 16: i due trattamenti nominati, "
             "trattamento (B) dichiarato")

ANCHOR_CHANGELOG = ("> 7. Due esclusioni strutturali registrate: `paper1_rev_n10_phases.py` è "
                    "**NGC-only** nel corpo del\n>    codice, e il JSON del residuo arrotonda "
                    "`sd_draw` a 157.0.")

CHANGELOG = """

> **Cosa cambia nella rev. 3.12.** Voci marcate **✦✧✧**. Sessione del 31 agosto, seconda metà,
> dopo il referee report.
>
> 1. **Emendamento 16 appeso** (riga 16, item `1.4/treatment_B`, `type: protocol`). Registro a
>    sedici record, `DOCUMENTED_AMENDMENTS = 16`, `paper2_freeze_verify.py` CLEAN.
> 2. **I due trattamenti sono nominati.** Quel che la Fase 3 ha misurato è *D* sotto **trattamento
>    (A)**, con la mappatura scatola→cielo rifatta al fiduciale di ogni punto. Il §5.1 della
>    pre-registrazione non lo distingueva, ed è l'ambiguità che ha permesso di leggere il rapporto
>    Δ_mock/Δ_dati come un fatto invece che come un artefatto di trattamento. Rettifica
>    **obbligatoria anche se (B) non venisse mai eseguito**.
> 3. **Regola di quotazione dichiarata prima del run.** L'esito E1–E4 resta valutato su (A), che dà
>    l'escursione più grande, e il budget prende quel numero; (B) si riporta accanto. Motivo: la
>    direzione dell'effetto di (B) è **nota in anticipo**, quindi promuoverlo a primario ora
>    sarebbe sostituire l'analisi pre-registrata con una più favorevole di cui si conosce il verso.
>    L'obiezione contraria — la pratica standard costruisce il mock una volta e fa entrare il
>    fiduciale solo in analisi, cioè fa (B) — è **registrata nel record**, non solo la scelta.
> 4. **Meccanismo letto nel codice, non ipotizzato.** Nel gauge a cubo costante il tiling non è un
>    canale di variazione (offset e maschera identici punto per punto); senza RSD il giro
>    *r* → *z* → *r*′ è l'**identità** a 1.9 × 10⁻¹⁶, quindi sotto (A) le posizioni non si muovono e
>    cambia solo la **selezione**; con RSD lo spostamento comovente si riscala con *H*(*z*) della
>    tabella iniettata. Il trattamento (A) distorce **lo spostamento RSD**, il lato dati distorce
>    **tutta la coordinata radiale**.
> 5. **Due voci nuove in Fase 3**, 3.7 e 3.8, entrambe con predizione e soglia dichiarate prima
>    dell'esecuzione."""

ANCHOR_14 = ("Vanno riportate entrambe, separatamente: confonderle è l'errore più facile di questo "
             "paper.")

ITEM_14B = """
- [x] **✦✧✧ 1.4b — Emendamento 16: i due trattamenti nominati. STATUTO CHIUSO**, 31 ago 2026,
      record 16 di `src/paper2_v1_amendments.jsonl`, item `1.4/treatment_B`,
      `src/paper2_append_amend16.py` (18 controlli di selftest), documento `paper2_item16.md`.
      **La distinzione che la voce sopra non faceva.** *(A)* **mock rigenerati:** la mappatura
      scatola→cielo è rifatta al fiduciale di ogni punto da `carve_cutsky()`. È quel che la Fase 3
      ha misurato, in tutti i suoi punti. *(B)* **osservabili fisse:** (r̂, *z*_obs) congelate al
      fiduciale, per ogni punto si ricalcola solo *r*′ = *D*_C^(*g*)(*z*_obs). È il trattamento che
      il lato dati subisce **per costruzione**, perché per i dati (RA, DEC, *z*) non dipendono dalla
      cosmologia d'analisi. Il §5.1 depositato dice che l'AP agisce su entrambi i lati senza dire
      **come** il lato mock viene portato al punto: non sono la stessa perturbazione.
      **Rettifica obbligatoria e indipendente dal test.** Il manoscritto deve dire «*D* sotto
      trattamento (A)» anche se (B) non venisse mai eseguito. Non cambia un numero: cambia cosa quei
      numeri dicono.
      **Regola di quotazione, dichiarata prima del run.** L'esito E1–E4 **resta valutato su (A)**,
      che dà l'escursione più grande, e il budget dei sistematici prende quel numero. (B) si riporta
      accanto come isolamento del canale AP proprio. Il motivo è che la direzione dell'effetto di
      (B) è **nota in anticipo** — Δ_mock^(B) ≤ Δ_mock^(A), quindi Δ*D* si riduce e l'esito si
      muove da E2 verso E1, cioè verso il risultato favorevole — e promuoverlo a primario adesso
      sarebbe sostituire l'analisi pre-registrata con una più favorevole di cui si conosce il verso.
      **L'obiezione contraria è registrata nel record, non solo la scelta:** la pratica standard
      nelle analisi AP costruisce il catalogo mock **una volta**, con la cosmologia vera della
      simulazione, e fa entrare il fiduciale solo nel passo d'analisi, cioè fa (B); sotto quella
      lettura (A) non è una variante conservativa ma una procedura che cambia l'universo simulato
      invece della scelta d'analisi. La regola quota comunque il numero più grande, quindi resta
      conservativa anche se l'obiezione è fondata.
      **Statuto di (B): NON pre-registrato.** Non compare nel protocollo depositato in alcuna forma.
      Etichetta obbligatoria nel manoscritto e in ogni figura o tabella: **«post-review, dichiarato
      prima dell'esecuzione»**. Vietate «pre-registrato», «pianificato», «previsto dal protocollo»."""

ANCHOR_36 = ("      2 e 3 sui mock non sono stati calcolati: raddoppiavano le venti ore per due "
             "diagnostici di\n      bordo che il lato dati ha già su tutti i punti. Da riportare "
             "come scelta, non come omissione.")

ITEMS_37_38 = """
- [ ] **✦✧✧ 3.7 — Trattamento (B), osservabili fisse. DA ESEGUIRE**, perimetro e cancelli fissati
      dal record 16 prima che il primo punto giri.
      **Perimetro:** sei punti di linea B (B1, B2, fiduciale, B4, B5, B6), *N* = 200 appaiate sugli
      **stessi indici 0–199** della Fase 3, due emisferi, *k* = 1 primario e *k* = 0 in parallelo,
      gauge a cubo costante. Costo dell'ordine di **10 ore**: il percorso con cache salta il
      carving.
      **Cache:** costruita al punto fiduciale **dopo il Pass 2** di `carve_cutsky()`; contiene `rhat`
      e `z_obs` in float64 con **ordine di riga preservato**, chiave (emisfero, realizzazione, seme
      HOD), hash di configurazione. A valle si applica **esattamente** la catena del lato dati:
      nessun ricampionamento n(*z*), nessun ri-seed, nessuna ricostruzione della selezione, nessuna
      riapplicazione dei tagli in *z*. La selezione è congelata al fiduciale, ed è questo che rende
      (B) il gemello del lato dati.
      **Implementazione:** modalità `--fixed-observables` di `paper2_runner_fase3_mock.py`, campo
      `mode` nel record e hash di configurazione distinto. **Non** uno script nuovo: una sola
      implementazione per quantità, che è la classe di difetto del 445 contro 313.
      **Cancello D5a — bit-identità al fiduciale, tolleranza ZERO.** L'emendamento 14 non si applica:
      là il confronto era fra `comoving_distance` nativa e tabella iniettata, qui è **interno alla
      stessa tabella** (`phase8:682-683`, stessa `np.interp`, stessi bit in ingresso). Porre il
      cancello alla scala di tie-breaking (2.5 × 10⁻⁵ generatori) accetterebbe una cache sbagliata:
      sarebbe un cancello che non può fallire.
      **Cancello D5b — riproduzione ESATTA del baseline appaiato *n* = 200:** 35 423.575 / 31 889.930
      (NGC), 18 693.595 / 16 477.565 (SGC).
      **✦✧✧ PREDIZIONE DICHIARATA prima del run:** se il fattore 2.10–5.56 fra Δ_mock e Δ_dati è
      interamente di costruzione, sotto (B) il rapporto scende verso 1 e Δ*D* verso zero.
      **Falsificata se il rapporto resta > 2 in almeno tre punti su sei**, nel qual caso il lato mock
      risponde all'AP più del campo osservato per una ragione che non è il rimappaggio RSD. Non si
      ripara dopo.
      **Statuto:** (B) non entra in Δ*D*_max, non riapre l'esito E2, non tocca il fit di simmetria
      né il test di completezza sugli angoli.
- [ ] **✦✧✧ 3.8 — Linea B in spazio reale: falsificazione del meccanismo. DA ESEGUIRE.**
      Non è una diagnostica generica: è il test che decide se il meccanismo scritto nel record 16 è
      quello vero.
      **Perché ha una predizione chiusa.** Nel gauge a cubo costante `BOX_MIN`, `BOX_SIZE`, `CELL`,
      `NGRID`, `SIGMA_PX` e la maschera sono congelati sulla griglia, quindi gli offset di tiling
      (`phase8:652-657`) e l'array di maschera (`phase8:690`) sono **identici punto per punto**: il
      tiling non è un canale di variazione. Le posizioni nella scatola sono fisse, quindi
      `dC = norm(P)` e `rhat` non cambiano. **Senza RSD** si ha `z_obs = z_cosmo` e
      `dC_rsd = interp(interp(dC, _DC_TAB, _Z_TAB), _Z_TAB, _DC_TAB)`: il round-trip di una mappa
      monotona lineare a tratti **sugli stessi nodi**, cioè l'identità in aritmetica esatta e
      **1.9 × 10⁻¹⁶** in floating point (misurato dal selftest 14 di `paper2_append_amend16.py`),
      pari a ~10⁻¹³ Mpc/h contro una cella di 15.6. Le posizioni **non si muovono, per qualunque
      tabella iniettata**: cambia solo **chi** è selezionato — pre-filtro radiale (674) su soglie che
      si spostano, `zsel` (684) su `z_obs` ricalcolato, ricampionamento n(*z*) (702-715) dove
      `rng.random(len(z_cand))` riallinea lo stream appena il conteggio dei candidati cambia.
      **✦✧✧ PREDIZIONE DICHIARATA prima del run:** sotto (A) **senza RSD**, Δ_mock è un **puro
      effetto di riselezione**, dell'ordine del termine (c) di ri-randomizzazione del carving,
      cioè da −3.2 ± 10.9 a +15.0 ± 9.6 generatori. **Falsificata se |Δ_mock| > 53 generatori**, la
      soglia di rilevabilità depositata: in quel caso «il meccanismo è il rimappaggio RSD» è
      sbagliato e si apre un canale di riselezione di ampiezza non trascurabile.
      **Il canale è già dichiarato scoperto.** Il §8 della pre-registrazione elenca «the number of
      galaxies changing selection state per grid point» fra le cose **non coperte e da misurare
      senza regola pre-registrata**: questa voce riempie una lacuna dichiarata, non contraddice il
      deposito."""

EDITS = [
    ("A  titolo 3.11 -> 3.12", OLD_TITLE, NEW_TITLE),
    ("B  blocco changelog 3.12", ANCHOR_CHANGELOG, ANCHOR_CHANGELOG + CHANGELOG),
    ("C  voce 1.4b", ANCHOR_14, ANCHOR_14 + ITEM_14B),
    ("D  voci 3.7 e 3.8", ANCHOR_36, ANCHOR_36 + ITEMS_37_38),
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
    chk("3  parte dalla rev. 3.11", s.count(OLD_TITLE) == 1,
        "occorrenze=%d" % s.count(OLD_TITLE))
    chk("4  marcatore %s libero nella 3.11" % MARK, s.count(MARK) == 0,
        "occorrenze=%d" % s.count(MARK))
    chk("5  nessuna voce 3.7 / 3.8 gia' presente",
        ("**3.7 —" not in s) and ("**3.8 —" not in s)
        and ("3.7 — Trattamento" not in s))
    chk("6  idempotenza: la 3.12 non e' gia' applicata",
        (NEW_TITLE not in s) and ("1.4b" not in s))

    for i, (name, old, new) in enumerate(EDITS, start=7):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    out = apply_all(s)
    chk("11 il risultato contiene entrambe le predizioni con soglia",
        ("resta > 2 in almeno tre punti su sei" in out)
        and ("|Δ_mock| > 53 generatori" in out))
    chk("12 il risultato dichiara (A) primario e registra l'obiezione",
        ("resta valutato su (A)" in out) and ("pratica standard" in out))
    chk("13 il risultato dichiara (B) non pre-registrato",
        "NON pre-registrato" in out)
    chk("14 riapplicazione bloccata (idempotenza sul risultato)",
        out.count(OLD_TITLE) == 0 and out.count(NEW_TITLE) == 1)
    chk("15 crescita del file plausibile (+40..+120 righe)",
        40 <= out.count("\n") - s.count("\n") <= 120,
        "delta=%d righe" % (out.count("\n") - s.count("\n")))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_checklist_312 ===")
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
                                     fromfile="rev.3.11", tofile="rev.3.12", n=1))
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
    print("[OK] %s portato alla rev. 3.12" % args.path)
    back = read(args.path)
    print("verifica: rev.3.12 presente=%s  CRLF introdotti=%s"
          % (NEW_TITLE in back, "\r" in back))
    return 0


def main():
    p = argparse.ArgumentParser(description="checklist_paper2.md: rev. 3.11 -> 3.12")
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_314.py — porta checklist_paper2.md dalla rev. 3.13 alla 3.14.

Quattro modifiche, ciascuna ancorata a una stringa che deve comparire ESATTAMENTE
una volta nel file. Se un'ancora manca o e' ambigua lo script si ferma senza
scrivere: una checklist rattoppata a mano nel punto sbagliato e' peggio di una
non aggiornata.

  A  titolo: rev. 3.13 -> rev. 3.14
  B  blocco di changelog della 3.14, in coda a quello della 3.13
  C  voce 3.8: meccanismo e predizione 2 SOSTITUITI (unica sostituzione, non\n     aggiunta: il testo era falso)\n  D  voce 1.4b: nota di rettifica

Marcatore della revisione: ✦✦✧ (verificato assente nella 3.13).\nI blocchi di changelog storici NON si riscrivono: il punto 4 della 3.12 resta\nfalso e la 3.14 lo dichiara.

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

MARK = "\u2726\u2726\u2727"          # ✦✦✧
DEFAULT_PATH = "checklist_paper2.md"

OLD_TITLE = ("### rev. 3.13 — 31 agosto 2026 — emendamento 17: cancello D5c e denominatore "
             "della predizione 1")
NEW_TITLE = ("### rev. 3.14 — 1 settembre 2026 — emendamento 18: il gauge fissa il lato e non "
             "l'origine; predizione 2 ritirata")

ANCHOR_CHANGELOG = ("> 5. **La catena a valle è già una sola.** `one_mock` chiama già `M.cic_3d`, "
                    "`P1.compute_delta`,\n>    `M.build_field`, `M.compute_tda_features` e "
                    "`F3.erosion_levels` — quest'ultima importata **dal\n>    runner dati**. Non "
                    "c'è nessuna copia da riunificare: l'unico passo specifico del lato mock è\n"
                    ">    `carve_cutsky`, che è esattamente ciò che (B) sostituisce.")

CHANGELOG = """

> **Cosa cambia nella rev. 3.14.** Voci marcate **✦✦✧**. Rettifica di un errore mio, trovato
> leggendo il referee report contro la voce 1.4a di questa stessa checklist.
>
> 1. **Emendamento 18 appeso** (riga 18, item `1.4b/rettifica_gauge`). Registro a diciotto record,
>    `DOCUMENTED_AMENDMENTS = 18`, verificatore CLEAN.
> 2. **Il gauge a cubo costante fissa il LATO, non l'ORIGINE.** `BOX_SIZE`, `CELL` e `SIGMA_PX`
>    sono costanti sulla griglia; `BOX_MIN` **no**. `build_geometries` lo deriva punto per punto
>    (riga 195) da random che si deformano con la tabella iniettata, e la maschera è **riderivata**
>    a riga 207. Gli offset di tiling dipendono da `BOX_MIN` (`phase8:653`), quindi cambiano le
>    repliche, cambia `inb` (666), cambia `P`, cambia `dC = norm(P)`.
> 3. **Il punto 4 del changelog della rev. 3.12 è quindi falso** e resta come storia, non
>    riscritto. Il testo della voce 3.8, che su quella premessa era costruito, è **sostituito**.
> 4. **Due controlli lo smentivano in un passo, ed entrambi erano a portata di mano.** La voce
>    1.4a di questa checklist lo dice esplicitamente; e il termine (e) del budget esiste **solo
>    se** `n_valid_voxels` varia punto per punto — se la maschera fosse congelata, (e) sarebbe
>    identicamente zero. Il §3.2 del referee propone la maschera-intersezione **proprio per**
>    rendere costante `n_valid_voxels`, il che sarebbe vuoto se già lo fosse.
> 5. **La predizione 2 è RITIRATA, non falsificata.** La sua premessa era falsa, quindi non era
>    testabile come scritta. Riportarla come smentita sarebbe la stessa classe di errore che il
>    §4.1 del referee contesta sulla seconda predizione di B6.
> 6. **Nessun cancello cade.** D5a, D5b, D5c e il denominatore restano in vigore; la rettifica di
>    denominazione (A)/(B) e la regola di quotazione pure. Regge anche il risultato centrale del
>    record 16 — sotto (A) la distorsione AP non è applicata alla coordinata radiale — perché il
>    round-trip è una proprietà delle **sole tabelle**.
> 7. **La lista di canali del referee è adottata come sta:** maschera (dai random, che si
>    deformano), registrazione del tiling, residuo RSD; più lo spostamento di griglia, che
>    `PF.grid_shift` già misura.
> 8. **Errore preso prima di qualunque run.** Né (B) né la linea B in spazio reale sono girate:
>    nessuna misura poggia sulla premessa falsa."""

ANCHOR_38 = "      **Perché ha una predizione chiusa.** Nel gauge a cubo costante `BOX_MIN`, `BOX_SIZE`, `CELL`,\n      `NGRID`, `SIGMA_PX` e la maschera sono congelati sulla griglia, quindi gli offset di tiling\n      (`phase8:652-657`) e l'array di maschera (`phase8:690`) sono **identici punto per punto**: il\n      tiling non è un canale di variazione. Le posizioni nella scatola sono fisse, quindi\n      `dC = norm(P)` e `rhat` non cambiano. **Senza RSD** si ha `z_obs = z_cosmo` e\n      `dC_rsd = interp(interp(dC, _DC_TAB, _Z_TAB), _Z_TAB, _DC_TAB)`: il round-trip di una mappa\n      monotona lineare a tratti **sugli stessi nodi**, cioè l'identità in aritmetica esatta e\n      **1.9 × 10⁻¹⁶** in floating point (misurato dal selftest 14 di `paper2_append_amend16.py`),\n      pari a ~10⁻¹³ Mpc/h contro una cella di 15.6. Le posizioni **non si muovono, per qualunque\n      tabella iniettata**: cambia solo **chi** è selezionato — pre-filtro radiale (674) su soglie che\n      si spostano, `zsel` (684) su `z_obs` ricalcolato, ricampionamento n(*z*) (702-715) dove\n      `rng.random(len(z_cand))` riallinea lo stream appena il conteggio dei candidati cambia.\n      **✦✧✧ PREDIZIONE DICHIARATA prima del run:** sotto (A) **senza RSD**, Δ_mock è un **puro\n      effetto di riselezione**, dell'ordine del termine (c) di ri-randomizzazione del carving,\n      cioè da −3.2 ± 10.9 a +15.0 ± 9.6 generatori. **Falsificata se |Δ_mock| > 53 generatori**, la\n      soglia di rilevabilità depositata: in quel caso «il meccanismo è il rimappaggio RSD» è\n      sbagliato e si apre un canale di riselezione di ampiezza non trascurabile."

ITEM_38 = """      **✦✦✧ Perché ha una predizione chiusa — RISCRITTA dopo l'emendamento 18.** *(Il testo
      precedente affermava che maschera e tiling fossero congelati sulla griglia. È falso: vedi il
      punto 2 del changelog di questa revisione. Quel che segue lo sostituisce.)*
      Il gauge fissa `BOX_SIZE`, `CELL` e `SIGMA_PX`, **non** `BOX_MIN`: la maschera è riderivata
      punto per punto (`build_geometries:207`) e gli offset di tiling dipendono dall'origine del
      cubo (`phase8:653`). In spazio reale restano quindi attivi il **canale voxel**, la
      **registrazione del tiling** e lo **spostamento di griglia**.
      Quel che resta vero, ed è una proprietà delle **sole tabelle**: senza RSD si ha
      `z_obs = z_cosmo` e `dC_rsd = interp(interp(dC, _DC_TAB, _Z_TAB), _Z_TAB, _DC_TAB)`, il
      round-trip di una mappa monotona lineare a tratti **sugli stessi nodi**, cioè l'identità in
      aritmetica esatta e **1.9 × 10⁻¹⁶** in floating point. La mappa *z* → *r*′ **non** sposta di
      per sé una galassia rispetto alla sua distanza in spazio reale: la distorsione AP propria,
      sotto (A), non è applicata alla coordinata radiale. È il risultato per cui il record 16
      esiste, e regge.
      **✦✦✧ PREDIZIONE DICHIARATA prima del run, riformulata a RAPPORTO** (emendamento 18; quella
      a soglia assoluta del record 16 è **ritirata**, non falsificata, perché la premessa era
      falsa). Sotto (A) in spazio reale, il residuo **dopo la sottrazione del termine (e)** è
      dell'ordine dei canali di registrazione residui — tiling e spostamento di griglia — e **non**
      dell'ordine della risposta in spazio di redshift. **Falsificata se il residuo in spazio reale
      dopo (e) raggiunge almeno METÀ di quello in spazio di redshift dopo (e), in almeno metà dei
      punti misurati, in entrambi gli emisferi.**
      **Perché a rapporto e non in generatori.** In spazio reale la maschera si muove ancora con
      `box_min`, quindi il canale voxel è presente ed è da solo più grande della soglia di
      rilevabilità: valutare il Δ_mock grezzo non testerebbe nulla. E la scala assoluta del residuo
      è **essa stessa** la quantità non spiegata della Fase 3, quindi non può fare da riferimento a
      sé stessa."""

ANCHOR_14B = ("prima dell'esecuzione»**. Vietate «pre-registrato», «pianificato», «previsto dal "
              "protocollo».")

ITEM_14B_ADD = """
      **✦✦✧ Rettifica, emendamento 18.** La frase del campo `evidence` del record 16 su maschera e
      tiling congelati è **falsa**, e con essa cade la predizione 2, **ritirata e non falsificata**.
      Restano in vigore la rettifica di denominazione, la regola di quotazione, e i cancelli D5a e
      D5b. Il risultato centrale — sotto (A) la distorsione AP non è applicata alla coordinata
      radiale — regge, perché il round-trip è una proprietà delle sole tabelle."""

EDITS = [
    ("A  titolo 3.13 -> 3.14", OLD_TITLE, NEW_TITLE),
    ("B  blocco changelog 3.14", ANCHOR_CHANGELOG, ANCHOR_CHANGELOG + CHANGELOG),
    ("C  voce 3.8: paragrafo del meccanismo e predizione 2, SOSTITUITI", ANCHOR_38, ITEM_38),
    ("D  voce 1.4b: nota di rettifica", ANCHOR_14B, ANCHOR_14B + ITEM_14B_ADD),
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
    chk("3  parte dalla rev. 3.13", s.count(OLD_TITLE) == 1,
        "occorrenze=%d" % s.count(OLD_TITLE))
    chk("4  marcatore %s libero nella 3.13" % MARK, s.count(MARK) == 0,
        "occorrenze=%d" % s.count(MARK))
    chk("5  prerequisito: D5c e le voci 3.7/3.8 esistono gia' (rev. 3.13)",
        ("Cancello D5c" in s) and ("3.7 — Trattamento" in s) and ("3.8 — Linea B" in s))
    chk("6  idempotenza: la 3.14 non e' gia' applicata",
        (NEW_TITLE not in s) and ("emendamento 18" not in s))

    for i, (name, old, new) in enumerate(EDITS, start=7):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    out = apply_all(s)
    chk("10 l'affermazione falsa e' RIMOSSA dalla voce 3.8",
        ("sono congelati sulla griglia, quindi gli offset di tiling" not in out)
        and ("Le posizioni **non si muovono, per qualunque" not in out))
    chk("11 la storia resta: il punto 4 della 3.12 non e' riscritto",
        out.count("> 4. **Meccanismo letto nel codice, non ipotizzato.**") == 1
        and ("Il punto 4 del changelog della rev. 3.12 è quindi falso" in out))
    chk("12 predizione 2 ritirata e riformulata a rapporto",
        ("è **ritirata**, non falsificata" in out)
        and ("almeno METÀ di quello in spazio di redshift" in out)
        and ("Falsificata se |Δ_mock| > 53 generatori" not in out))
    chk("12b i cancelli restano dichiarati in vigore",
        ("Cancello D5c" in out) and ("D5a" in out) and ("D5b" in out)
        and ("Nessun cancello cade" in out))
    chk("12c quel che sopravvive e' detto, non solo quel che cade",
        ("proprietà delle **sole tabelle**" in out)
        and ("È il risultato per cui il record 16" in out))
    chk("13 riapplicazione bloccata (idempotenza sul risultato)",
        out.count(OLD_TITLE) == 0 and out.count(NEW_TITLE) == 1)
    chk("14 crescita del file plausibile (+20..+80 righe)",
        20 <= out.count("\n") - s.count("\n") <= 80,
        "delta=%d righe" % (out.count("\n") - s.count("\n")))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_checklist_314 ===")
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
                                     fromfile="rev.3.13", tofile="rev.3.14", n=1))
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
    print("[OK] %s portato alla rev. 3.14" % args.path)
    back = read(args.path)
    print("verifica: rev.3.14 presente=%s  CRLF introdotti=%s"
          % (NEW_TITLE in back, "\r" in back))
    return 0


def main():
    p = argparse.ArgumentParser(description="checklist_paper2.md: rev. 3.13 -> 3.14")
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

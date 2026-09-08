#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_checklist_313.py — porta checklist_paper2.md dalla rev. 3.12 alla 3.13.

Tre modifiche, ciascuna ancorata a una stringa che deve comparire ESATTAMENTE
una volta nel file. Se un'ancora manca o e' ambigua lo script si ferma senza
scrivere: una checklist rattoppata a mano nel punto sbagliato e' peggio di una
non aggiornata.

  A  titolo: rev. 3.12 -> rev. 3.13
  B  blocco di changelog della 3.13, in coda a quello della 3.12
  C  voce 3.7: D5c, denominatore della predizione 1, capture=

Marcatore della revisione: ✧✦✦ (verificato assente nella 3.12).

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

MARK = "\u2727\u2726\u2726"          # ✧✦✦
DEFAULT_PATH = "checklist_paper2.md"

OLD_TITLE = ("### rev. 3.12 — 31 agosto 2026 — emendamento 16: i due trattamenti nominati, "
             "trattamento (B) dichiarato")
NEW_TITLE = ("### rev. 3.13 — 31 agosto 2026 — emendamento 17: cancello D5c e denominatore "
             "della predizione 1")

ANCHOR_CHANGELOG = ("> 5. **Due voci nuove in Fase 3**, 3.7 e 3.8, entrambe con predizione e "
                    "soglia dichiarate prima\n>    dell'esecuzione.")

CHANGELOG = """

> **Cosa cambia nella rev. 3.13.** Voci marcate **✧✦✦**. Stessa sessione, dopo la lettura dei due
> runner di Fase 3 contro `phase8_cutsky_mocks.py`.
>
> 1. **Emendamento 17 appeso** (riga 17, item `3.7/D5c`). Registro a diciassette record.
> 2. **Cancello D5c: zero clippati sul lato mock, arresto duro.** Il lato dati non conta i
>    fuori-cubo, li **vieta** (`paper2_runner_fase3.py:277-282` e `296-301`, `clipped_per_face` più
>    `sys.exit`, emendamento 13 punto (c)). Il lato mock quella barriera non l'ha mai avuta:
>    `phase8:688` clippa in silenzio e **impila sul voxel di bordo**, e `one_mock` non chiama mai
>    `clipped_per_face` su `pos_sel`. Sotto (B) le galassie si spostano radialmente e verso
>    *F* > 1 escono dal cubo congelato: senza D5c l'impilamento verrebbe contato come segnale.
> 3. **Il denominatore della predizione 1 è fissato.** D5c può rendere punti non misurabili, e
>    «tre su sei» non sarebbe più definito. Regola dichiarata prima di sapere quali punti cadono:
>    si valuta sui punti **effettivamente misurati**, falsificata se il rapporto resta sopra 2 in
>    **almeno metà** di essi, con **minimo quattro**; sotto quattro è **non valutabile**, che non è
>    un superamento.
> 4. **`capture=` NON è un emendamento.** Con `capture=None` il comportamento è invariato bit a
>    bit: è strumentazione, e sta qui in checklist, verificata dalla macchina D4a esistente. Se
>    ogni modifica al codice diventasse un emendamento il registro sarebbe un changelog.
> 5. **La catena a valle è già una sola.** `one_mock` chiama già `M.cic_3d`, `P1.compute_delta`,
>    `M.build_field`, `M.compute_tda_features` e `F3.erosion_levels` — quest'ultima importata **dal
>    runner dati**. Non c'è nessuna copia da riunificare: l'unico passo specifico del lato mock è
>    `carve_cutsky`, che è esattamente ciò che (B) sostituisce."""

ANCHOR_14 = ("      **Statuto:** (B) non entra in Δ*D*_max, non riapre l'esito E2, non tocca il fit "
             "di simmetria\n      né il test di completezza sugli angoli.")

ITEM_14B = """
      **✧✦✦ Cancello D5c — zero clippati lato mock, arresto duro** (emendamento 17). `D5a` al
      fiduciale **non** verifica la catena a valle: a *F* = 1 la tabella è identica, quindi niente
      si muove e il confronto passa qualunque cosa il codice faccia dopo il rimappaggio. È a valle
      che (B) può divergere dal lato dati. `PF.clipped_per_face(pos_sel, BOX_MIN, BOX_SIZE)` deve
      dare `n_clipped == 0` a ogni punto, **in entrambi i trattamenti**; un conteggio non nullo
      ferma il punto, non lo avverte. Un punto che non si misura si riporta **con i conteggi per
      faccia**: è un dato, non un buco. Il cancello può solo **rifiutare** punti, mai accettarne, ed
      è questa proprietà che lo rende ammissibile dopo il deposito.
      **✧✦✦ Denominatore della predizione 1, dichiarato prima di sapere quali punti cadono.** Si
      valuta sui punti **effettivamente misurati**: falsificata se il rapporto resta sopra 2 in
      **almeno metà** di essi, con un **minimo di quattro** punti misurati; sotto quattro la
      predizione è **non valutabile**, e non valutabile non è un superamento. *(Scartate: valutare
      sempre sui sei nominali, che farebbe contare un punto non misurato come non-falsificante,
      cioè premierebbe il fallimento del cancello; e una frazione senza minimo, che con due punti
      superstiti non significa nulla.)*
      **✧✦✦ Costruzione della cache: `capture=`, e perché la via facile non funziona.** Ricavare
      (r̂, *z*_obs) invertendo `pos_sel` costa qualche ulp sul giro di ritorno, quindi al fiduciale
      `rhat · interp(z_obs, …)` **non** sarebbe bit-identico a `pos_sel` e D5a fallirebbe per un
      motivo che non è un difetto della cache. Cachare `pos_sel` stesso e restituirlo tale e quale
      renderebbe invece D5a un cancello che non può fallire. I valori vanno presi **dentro**
      `carve_cutsky`, dove esistono già in float64: parametro opzionale `capture=None`; se è un
      dizionario riceve `rhat[sel]` e `z_obs[sel]` dopo il Pass 2. **Non è un emendamento**: con
      `capture=None` il comportamento è invariato bit a bit e nessuna quantità misurata può
      cambiare. **Verifica obbligatoria prima di usarlo:** rilancio del percorso FID con
      `--frozen-delta-dir`, `D4a_identical` vero su tutte e 200 le realizzazioni. La macchina
      esiste già in `one_mock`; non si verifica a occhio, perché `phase8` è un nodo condiviso da
      ~30 script.
      **✧✦✦ La catena a valle è già una sola.** `one_mock` chiama `M.cic_3d`, `P1.compute_delta`,
      `M.build_field`, `M.compute_tda_features` e `F3.erosion_levels`, quest'ultima importata **dal
      runner dati**. L'unico passo specifico del lato mock è `carve_cutsky`. Il vincolo «una sola
      implementazione per quantità» del record 16 è quindi **descrittivo del codice esistente**, non
      una modifica da fare."""

EDITS = [
    ("A  titolo 3.12 -> 3.13", OLD_TITLE, NEW_TITLE),
    ("B  blocco changelog 3.13", ANCHOR_CHANGELOG, ANCHOR_CHANGELOG + CHANGELOG),
    ("C  D5c, denominatore e capture= dentro la voce 3.7", ANCHOR_14, ANCHOR_14 + ITEM_14B),
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
    chk("3  parte dalla rev. 3.12", s.count(OLD_TITLE) == 1,
        "occorrenze=%d" % s.count(OLD_TITLE))
    chk("4  marcatore %s libero nella 3.12" % MARK, s.count(MARK) == 0,
        "occorrenze=%d" % s.count(MARK))
    chk("5  prerequisito: le voci 3.7 e 3.8 esistono gia' (rev. 3.12)",
        ("3.7 — Trattamento" in s) and ("3.8 — Linea B" in s) and ("1.4b —" in s))
    chk("6  idempotenza: la 3.13 non e' gia' applicata",
        (NEW_TITLE not in s) and ("D5c" not in s))

    for i, (name, old, new) in enumerate(EDITS, start=7):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    out = apply_all(s)
    chk("10 D5c: zero, arresto duro, entrambi i trattamenti",
        ("n_clipped == 0" in out) and ("in entrambi i trattamenti" in out)
        and ("solo **rifiutare**" in out))
    chk("11 denominatore: meta', minimo quattro, non valutabile",
        ("almeno metà" in out) and ("minimo di quattro" in out)
        and ("non valutabile non è un superamento" in out))
    chk("12 capture= dichiarato non emendamento, con verifica D4a",
        ("Non è un emendamento" in out) and ("D4a_identical" in out))
    chk("13 riapplicazione bloccata (idempotenza sul risultato)",
        out.count(OLD_TITLE) == 0 and out.count(NEW_TITLE) == 1)
    chk("14 crescita del file plausibile (+25..+90 righe)",
        25 <= out.count("\n") - s.count("\n") <= 90,
        "delta=%d righe" % (out.count("\n") - s.count("\n")))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_checklist_313 ===")
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
                                     fromfile="rev.3.12", tofile="rev.3.13", n=1))
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
    print("[OK] %s portato alla rev. 3.13" % args.path)
    back = read(args.path)
    print("verifica: rev.3.13 presente=%s  CRLF introdotti=%s"
          % (NEW_TITLE in back, "\r" in back))
    return 0


def main():
    p = argparse.ArgumentParser(description="checklist_paper2.md: rev. 3.12 -> 3.13")
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

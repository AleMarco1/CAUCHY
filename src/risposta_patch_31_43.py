#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
risposta_patch_31_43.py — aggiunge a risposta_referee.md le due sezioni
redazionali che mancavano: §3.1 come sezione propria, e §4.3 separato dalla
risposta 6.

PERCHE' DUE SEZIONI E NON UN RIMANDO
  §3.1 ha tre parti. Le prime due - il sistematico fuori dagli intervalli, E2
  come affermazione a un sigma - confluiscono nella risposta 1 e la' restano.
  La TERZA - il rapporto sistematico/segnale costante a ~0.5, e la lettura
  moltiplicativa che il referee ne trae - non e' nella risposta 1 e non ha
  ancora una sezione. Un rimando non basta: manca il contenuto.

  §4.3 e la risposta 6 rispondono alla stessa domanda da due lati. Tenerli
  insieme funzionava finche' erano una bozza; separati, il §4.3 puo' dire quel
  che il referee chiede - che la bit-identita' e' risolvibile alla sorgente - e
  la risposta 6 quel che ne segue per i cancelli.

UN SEGNAPOSTO, DICHIARATO
  Il §4.3 del report cita un numero di celle divergenti fra percorso nativo e
  tabella iniettata. Quel numero NON e' verificabile da qui, quindi la sezione
  lo lascia come [DA VERIFICARE SUL REPORT] invece di riportarlo a memoria.
  Un numero non ricontrollabile non va in un documento che torna al referee.

Uso:
    python src\\risposta_patch_31_43.py selftest
    python src\\risposta_patch_31_43.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import math
import os
import sys

DEFAULT_PATH = "risposta_referee.md"

ANCHOR_31 = ("La seconda è favorevole alla conclusione del programma e non era in nessuna barra "
             "d'errore.")

ITEM_31 = """

---

## §3.1 — Il rapporto sistematico/segnale, e la lettura moltiplicativa **[SCRITTA]**

Le prime due parti del rilievo — il sistematico fuori dagli intervalli, E2 come affermazione a un
sigma — sono nella **risposta 1**, con la tabella completa. Qui la terza, che merita una sezione
propria perché è l'unico punto del report su cui **non siamo d'accordo**.

**L'osservazione è reale.** Il rapporto fra il sistematico su (b) e |Δ*D*_max| vale **0.426, 0.529,
0.589, 0.560**: quasi costante nei quattro casi. Il referee ne trae che l'errore sia
**moltiplicativo** e non un disturbo additivo, e che sommarlo in quadratura sia quindi il
trattamento sbagliato.

**Non lo adottiamo, e la ragione è che i quattro numeri non sono indipendenti.** Il residuo non
attribuito è la rms dei residui degli **stessi undici punti** di cui Δ*D*_max è l'escursione. Sono
due misure di quanto *D* si muove, calcolate sullo stesso insieme di dati: sono correlate per
costruzione, e un rapporto stabile è **atteso** senza che nessun meccanismo moltiplicativo sia in
gioco. Quattro numeri correlati non stabiliscono un modello.

**Quel che invece è stabilito, e lo adottiamo:** i residui valgono **4–5 volte la SEM**. Non sono
rumore campionario. Quella parte del rilievo regge e la riportiamo.

**Come lo trattiamo.** Il rapporto costante entra come **osservazione**, non come modello: lo stesso
trattamento che il documento riserva già all'antisimmetria del blocco A in SGC, dove avevamo scritto
«è un'osservazione, non un risultato». Il budget continua a sommare in quadratura, e non lo
cambiamo su quattro numeri correlati.

**E c'è una conseguenza che il referee non poteva prevedere.** Al suo §6 sostiene che il budget
conta una volta come disturbo ciò che il paragrafo «quello che non regge» conta un'altra volta come
fallimento di modello — «due fatti, un fatto solo». Nella forma in cui lo scrive **cade**, perché
non c'è nessun fallimento di modello: il fit sul solo lato mock è adeguato ovunque (§1(a)). Ma
l'intuizione sopravvive in forma diversa: residuo non attribuito e rifiuto del χ² sono plausibilmente
manifestazioni dello **stesso** oggetto — la struttura a singola realizzazione del lato dati, assente
dalla covarianza costruita sul lato mock. Non è un errore moltiplicativo, ed è coerente con la
risposta 1, dove quella struttura è misurata.

**Quella domanda resta aperta.** Il test della maschera-intersezione (§3.2) doveva deciderla e ha
dato PARTIAL: il residuo non è né tutto il canale voxel né indipendente da esso, quindi per quella
via non si decide. Si riesamina quando arrivano la linea B in spazio reale e il trattamento (B)."""

# L'ancora nel file e' spezzata su TRE righe: ricopiarla "logicamente" non
# funziona, va presa come sta.
ANCHOR_43 = ("""**La distinzione da riportare** è fra un confronto **fra implementazioni** — dove la bit-identità è
irraggiungibile per costruzione e va sostituita da determinismo più stabilità della filtrazione — e un
confronto **dentro la stessa implementazione**, dove la bit-identità è il cancello giusto e si esige.""")

ITEM_43 = """

---

## §4.3 — La bit-identità è risolvibile alla sorgente **[SCRITTA]**

Il referee propone di risolvere il problema **alla sorgente**: usare al fiduciale il percorso
nativo invece della tabella iniettata, così che le due strade coincidano per costruzione. La
proposta è giusta come diagnosi e non praticabile come rimedio, e le due cose vanno separate.

**Come diagnosi ha ragione.** La divergenza non è una proprietà della geometria: è una proprietà
delle **due implementazioni** di *D*_C. `set_geometry(dc_tab=...)` sostituisce `comoving_distance`
con un'interpolazione lineare, e al fiduciale le due forme coincidono **matematicamente** ma non bit
a bit. Il confronto misura quindi la differenza fra due implementazioni, non fra due cosmologie.

**Ed è un fatto empirico, non strutturale, e va dichiarato come tale.** Il report riporta un numero
di celle divergenti fra i due percorsi — **[DA VERIFICARE SUL REPORT: conteggio e frazione dei voxel
in maschera]** — e quel numero descrive **queste due implementazioni su questa griglia**, non un
limite di principio. Con una tabella più fitta, o con un'aritmetica diversa, sarebbe un altro
numero. Scriverlo come se fosse una costante del problema è l'errore da evitare.

**Come rimedio non è praticabile, per una ragione che il referee non poteva vedere.** Il percorso
nativo al fiduciale non è disponibile a costo zero: `set_geometry` è il punto in cui l'intera
geometria viene iniettata, e usarne due forme diverse a due punti della stessa griglia
introdurrebbe una **seconda implementazione della stessa quantità** — la classe di difetto che in
questo programma ha già prodotto una dispersione sbagliata di 445 contro 313. Il rimedio costerebbe
più del male.

**Dove invece la bit-identità si esige, ed è il caso che conta.** Per il trattamento a osservabili
fisse il confronto è **interno alla stessa tabella**: sia il carving sia la ricostruzione dalla
cache eseguono la stessa `np.interp` sugli stessi bit in ingresso, quindi l'uscita è identica bit a
bit. Lì il cancello è posto a **tolleranza zero**, e la ragione è che lì **può fallire davvero** —
se `rhat` o `z_obs` fossero presi nel punto sbagliato, troncati o riordinati. Porlo alla scala di
tie-breaking accetterebbe una cache sbagliata: sarebbe un cancello che non può fallire.

**La regola che ne esce**, e che riportiamo come tale: un confronto **fra implementazioni** non
ammette la bit-identità e va sostituito da determinismo più stabilità della filtrazione; un
confronto **dentro la stessa implementazione** la ammette, e allora si esige a tolleranza zero.
Le due cose portavano lo stesso nome e non sono la stessa richiesta."""

EDITS = [
    ("A  §3.1 come sezione propria", ANCHOR_31, ANCHOR_31 + ITEM_31),
    ("B  §4.3 separato dalla risposta 6", ANCHOR_43, ANCHOR_43 + ITEM_43),
]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    for name, old, new in EDITS:
        n = s.count(old)
        if n != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, n))
        s = s.replace(old, new, 1)
    return s


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # 1: l'argomento del §3.1 e' aritmetico e va verificato
    R = {"NGC_k1": (41.9, 98.3), "NGC_k0": (60.3, 114.0),
         "SGC_k1": (53.7, 91.1), "SGC_k0": (42.0, 75.0)}
    rap = [s / d for s, d in R.values()]
    att = [0.426, 0.529, 0.589, 0.560]
    chk("1  i quattro rapporti sono quelli, e sono quasi costanti",
        all(abs(a - b) < 5e-4 for a, b in zip(sorted(rap), sorted(att)))
        and (max(rap) - min(rap)) < 0.17,
        "da %.3f a %.3f" % (min(rap), max(rap)))
    chk("2  e i residui valgono 4-5 volte la SEM: l'altra meta' del rilievo",
        all(3.5 < s / sem < 6.5 for s, sem in
            ((41.2, 11.2), (59.8, 11.6), (53.3, 8.7), (41.5, 9.2))),
        "%.1f - %.1f" % (41.2 / 11.2, 53.3 / 8.7))

    ok = os.path.isfile(path)
    chk("3  risposta_referee.md presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("4  prerequisito: risposta 1 e risposta 6 gia' scritte",
        ("## Risposta 1" in s) and ("Risposta 6" in s))
    chk("5  idempotenza: le due sezioni non ci sono ancora",
        ("## §3.1 —" not in s) and ("## §4.3 —" not in s))
    for i, (name, old, new) in enumerate(EDITS, start=6):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("8  il §3.1 dice dove NON siamo d'accordo, non solo cosa accettiamo",
            ("non siamo d'accordo" in out) and ("Non lo adottiamo" in out))
        chk("9  e dice cosa del rilievo REGGE, con il numero",
            ("4–5 volte la SEM" in out) and ("Quella parte del rilievo regge" in out))
        chk("10 il §6 e' rivisto, non liquidato: cade la forma, resta l'intuizione",
            ("cade" in out) and ("l'intuizione sopravvive" in out))
        chk("11 il §4.3 separa DIAGNOSI e RIMEDIO",
            ("Come diagnosi ha ragione" in out)
            and ("Come rimedio non è praticabile" in out))
        # Le frasi nel .md vanno a capo: si cercano frammenti che NON attraversano
        # un fine riga. E' lo stesso inciampo dell'ancora del §4.3.
        chk("12 e dichiara il numero come EMPIRICO, non strutturale",
            ("fatto empirico" in out) and ("non strutturale" in out)
            and ("limite di principio" in out))
        chk("13 IL SEGNAPOSTO C'E' ed e' visibile, non un numero a memoria",
            "[DA VERIFICARE SUL REPORT" in out,
            "il conteggio del report non e' verificabile da qui")
        chk("14 la risposta 6 non e' duplicata: resta dov'era",
            out.count("## Risposta 6") == 1)
        chk("15 crescita plausibile (+50..+110 righe)",
            50 <= out.count("\n") - s.count("\n") <= 110,
            "delta=%d" % (out.count("\n") - s.count("\n")))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST risposta_patch_31_43 ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def cmd_apply(a):
    if selftest(a.path):
        print("")
        fail("selftest fallito: nessuna scrittura.")
    s = read(a.path)
    out = apply_all(s)
    diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                     fromfile="prima", tofile="dopo", n=1))
    print("\n=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff[:30]))
    print("... (%d righe di diff in tutto)" % len(diff))
    print("righe: %d -> %d" % (s.count("\n"), out.count("\n")))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    print("""
DA FARE A MANO, ed e' l'unica cosa: cercare
    [DA VERIFICARE SUL REPORT
nel §4.3 e sostituirlo con il conteggio delle celle divergenti che il referee
riporta. Non l'ho scritto io perche' non posso rileggere il report da qui, e un
numero non ricontrollabile non va in un documento che torna al referee.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="§3.1 e §4.3 nella risposta al referee")
    p.add_argument("--path", default=DEFAULT_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(func=lambda a: 1 if selftest(a.path) else 0)
    ap = sub.add_parser("apply")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(func=cmd_apply)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

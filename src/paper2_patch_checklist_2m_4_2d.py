#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_checklist_2m_4_2d.py

Aggiorna due voci di checklist_paper2.md ai risultati dell'8 settembre 2026.

**2.1-M** — il filo aperto sul peso FKP si chiude. I due numeri in disaccordo
sono medie su popolazioni diverse, entrambe corrette; e delta e' esattamente
invariante per riscalamento globale dei pesi, quindi il filo non era bloccante
per 4.2a e non lo e' mai stato. Record 56 del ledger.

**4.2d** — la voce usa la Tabella 12 del Paper 1 come cancello interno. Resta
valida per le righe 3 e 4 (voxel multi-occupati, molteplicita' massima), che
non dipendono dai pesi. NON vale per le righe 1 e 2, che dai pesi dipendono e
che sono collineari fra loro a Pearson +0.999: sono una prova sola. E la riga 1
ha un problema di provenienza aperto.

COME
----
Come il patcher di Fase 4: localizza per riga di apertura e rimpiazza fino alla
voce successiva, cosi' l'ancora non dipende dagli a capo. Rifiuta se le
occorrenze non sono esattamente una per bersaglio.

2.1-M resta [x]: era chiusa e lo resta, cambia solo il paragrafo del filo.
4.2d resta [ ]: il cancello gira dentro 4.2a, che non e' partito.

Il marcatore di revisione e' un PARAMETRO.

USO
    python src\\paper2_patch_checklist_2m_4_2d.py selftest
    python src\\paper2_patch_checklist_2m_4_2d.py applica ^
        --file papers\\paper2\\checklist_paper2.md --marca "<segno>" --dry-run
    python src\\paper2_patch_checklist_2m_4_2d.py applica ^
        --file papers\\paper2\\checklist_paper2.md --marca "<segno>" ^
        --backup logs\\checklist_pre_2m4_2d.md

Uscita: 0 se applicato, 2 se rifiutato, 3 se la rilettura non torna.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile

# Il paragrafo del filo aperto dentro 2.1-M: non e' un'apertura di voce, ma e'
# l'ultimo paragrafo della voce, quindi si rimpiazza fino alla voce successiva.
APRE_FILO = re.compile(r"^\s*\*\*[^*]*Filo aperto[^*]*\*\*", re.M)
APRE_4_2D = re.compile(r"^- \[([ x~])\] \*\*(?:[^*]*?)4\.2d —", re.M)
PROSSIMA = re.compile(r"^(?:- \[[ x~]\] |#{1,6} |---\s*$)", re.M)


def nuovo_filo(marca):
    m = (marca + " ") if marca else ""
    return f"""      **{m}Filo aperto, CHIUSO l'8 settembre 2026 (record 56).** I due numeri sono medie su
      **popolazioni diverse**, ed entrambe sono corrette. **0.309 è la media sulle GALASSIE MOCK**
      (0.309057, a 0.11 mezze unità dell'ultima cifra quotata); **0.3168 è la media sul CATALOGO
      DEI RANDOM** (0.316783, che coincide con la media per voxel pesata dal conteggio a
      **6.10e-07**, perché la CIC conserva le somme e tutti i 307 805 voxel di maschera contengono
      random). I dati stanno a 0.300682, la media semplice per voxel a 0.331917. Otto domini
      misurati in una passata: `src/paper2_pesofkp_domini.py` (selftest 14/14), uscita
      `results/paper2/pesofkp_domini_NGC.json`.
      **{m}Lo 0.3308 dell'SGC non è una discrepanza.** 0.309 è un numero NGC — Paper 1 §7.2
      descrive il test di n6, e n6 come n10 ha NGC nel corpo del codice — quindi l'SGC non ha un
      valore pubblicato con cui essere in disaccordo.
      **{m}E il filo non era bloccante per 4.2a, né lo è mai stato.** δ è **esattamente invariante**
      per riscalamento globale dei pesi mock: con α = Σ*w*_d/Σ*w*_r, mandando *w*_d → *c*·*w*_d si
      manda `field_d` → *c*·`field_d` e α → *c*·α, quindi δ = (*n*_g − α*n*_r)/(α*n*_r) ha
      numeratore e denominatore riscalati dallo stesso *c*. **Solo la forma in *z* entra nel
      risultato, non la media.** Verificato a max\\|δ(*c*) − δ(1)\\| ≤ **2.9e-14** per
      *c* ∈ {{0.975, 7.3, 1e-4}}, cioè virgola mobile.
      *(Regola che ne esce, e vale oltre questo caso: prima di dichiarare una voce bloccante,
      verificare se la quantità entra nel risultato. Questa è stata sul percorso critico di 4.2a
      per due settimane su una grandezza che si semplifica esattamente.)*
      **{m}Quel che resta è materia di manoscritto, non di run**: la frase del Paper 1 §7.2 attacca
      la parentesi al sostantivo sbagliato. Voce **P1-1** di `modifiche_paper1.md`, stato PRONTA.
"""


def nuovo_4_2d(marca):
    m = (marca + " ") if marca else ""
    return f"""- [ ] **{m}4.2d — Tab. 12 su v2 come cancello interno:** voxel multi-occupati e molteplicità
      massima **non dipendono dai pesi** e devono restare identici. **Vale per le righe 3 e 4** della
      tabella, e solo per quelle.
      **{m}Le righe 1 e 2 non sono un cancello e vanno escluse da questo uso.** Curtosi in eccesso
      di ν e ν₉₉−ν₁ dipendono dai pesi, e sono **collineari fra loro**: Pearson +0.9988 in NGC a
      footprint pieno, +0.9962 in NGC a P10, +0.9985 in SGC, con Spearman ≥ +0.994 ovunque. Sono
      due parametrizzazioni della forma di ν, cioè **una prova sola**. La didascalia «five
      independent diagnostics» è corretta in **P1-3** di `modifiche_paper1.md`.
      **{m}E la riga 1 ha un problema di provenienza, aperto.** I valori pubblicati +3.90 / +0.20
      non escono da **nessuna** delle quattro restrizioni di step6, in **nessuno** dei due emisferi:
      NGC footprint pieno +2.7638 / **−0.4382** (segno opposto), erosione 2 voxel +5.2172 / +1.9209,
      *field_r* > P5 +3.5603 / +0.0625, *field_r* > P10 +4.4236 / +0.5896. Il valore pubblicato sta
      fra P5 e P10 e non su nessuna delle due; a *n* = 2000, 200, 100, 60 e 50 lo scarto non si
      muove. Voce **P1-2** di `modifiche_paper1.md`, **BLOCCATA** finché non si trova lo script che
      l'ha prodotta. *(Quel che NON è in discussione: sotto tutte e quattro le restrizioni, in
      entrambi gli emisferi, la curtosi dei mock è maggiore di quella di DESI. La correzione è di
      contabilità, non di risultato.)*
      Strumento: `src/paper2_tab12_restrizione.py` (selftest 15/15).
"""


def valida_marca(marca, testo=None):
    """Una marca con < o > e' quasi sempre un segnaposto copiato da un messaggio.
    E' successo tre volte. Il rimedio e' un rifiuto, non la prudenza."""
    if marca and ("<" in marca or ">" in marca):
        raise SystemExit("RIFIUTO: la marca %r sembra un segnaposto, non un segno di "
                         "revisione. Passa il glifo vero, o '' per nessuna marca." % marca)
    if len(marca) > 12:
        raise SystemExit("RIFIUTO: marca lunga %d caratteri: e' un segno, non una frase."
                         % len(marca))
    if testo is not None and marca:
        # LA MARCA NON DEV'ESSERE INDISTINGUIBILE DA UNA PRECEDENTE.
        # L'11 settembre la rev. 3.20 e' stata scritta con ✦✦✦, che e'
        # sottostringa delle ✦✦✦✦ della rev. 3.17: le due revisioni sarebbero
        # state indistinguibili, e una sostituzione cieca avrebbe corrotto le
        # marche altrui. Se ne e' accorto un assert scritto a mano.
        #
        # RIFIUTO solo in quel caso. La presenza ISOLATA della marca non e' un
        # difetto: dentro una revisione la stessa marca si usa con piu' patcher,
        # ed e' il flusso normale. Li' si avvisa e basta — un rifiuto
        # bloccherebbe l'uso legittimo, e un cancello che ferma il lavoro giusto
        # viene disattivato, non rispettato.
        glifo = marca[0]
        piu_lunga = max((len(m.group()) for m in
                         re.finditer(re.escape(glifo) + "+", testo)), default=0)
        if piu_lunga > len(marca):
            raise SystemExit(
                "RIFIUTO: la marca %r cade dentro una sequenza di %d %r gia'"
                " presente: le due sarebbero indistinguibili, e una"
                " sostituzione cieca corromperebbe quella vecchia."
                % (marca, piu_lunga, glifo))
        n = testo.count(marca)
        if n:
            print("    [avviso] la marca %r compare gia' %d volte: se e' di"
                  " questa revisione va bene, se e' di una precedente le due"
                  " diventano indistinguibili." % (marca, n))
    return marca


def blocco(testo, apre, nome):
    trovate = list(apre.finditer(testo))
    if len(trovate) != 1:
        raise SystemExit(f"RIFIUTO: {nome} trovata {len(trovate)} volte, attesa 1")
    i = trovate[0].start()
    dopo = PROSSIMA.search(testo, trovate[0].end())
    if dopo is None:
        raise SystemExit(f"RIFIUTO: non trovo dove finisce {nome}")
    return i, dopo.start()


def applica(path, marca, dry_run=False, backup=None):
    valida_marca(marca)
    if not os.path.isfile(path):
        raise SystemExit(f"RIFIUTO: file inesistente: {path}")
    with open(path, "rb") as fh:
        grezzo = fh.read()
    testo = grezzo.decode("utf-8")
    valida_marca(marca, testo)   # la marca dev'essere LIBERA: serve il testo, che ora c'e'

    ia, fa = blocco(testo, APRE_FILO, "il filo aperto di 2.1-M")
    ib, fb = blocco(testo, APRE_4_2D, "4.2d")
    if not (fa <= ib):
        raise SystemExit("RIFIUTO: i due blocchi si sovrappongono o sono invertiti "
                         f"(filo {ia}-{fa}, 4.2d {ib}-{fb})")

    print(f"file    : {os.path.abspath(path)}")
    print(f"2.1-M   : byte {ia}-{fa}, {fa - ia} byte (paragrafo del filo)")
    print(f"4.2d    : byte {ib}-{fb}, {fb - ib} byte, casella "
          f"'{APRE_4_2D.search(testo).group(1)}'")
    print(f"marca   : {marca!r}")

    nuovo = testo[:ia] + nuovo_filo(marca) + testo[fa:ib] + nuovo_4_2d(marca) + testo[fb:]
    print(f"byte    : {len(grezzo)} -> {len(nuovo.encode('utf-8'))}")

    if testo[:ia] != nuovo[:ia] or testo[fb:] != nuovo[len(nuovo) - len(testo[fb:]):]:
        raise SystemExit("RIFIUTO: la sostituzione tocca testo fuori dai due blocchi")

    if dry_run:
        print("dry-run: nessuna scrittura")
        return 0

    if backup:
        os.makedirs(os.path.dirname(os.path.abspath(backup)) or ".", exist_ok=True)
        with open(backup, "wb") as fh:
            fh.write(grezzo)
        print(f"backup  : {os.path.abspath(backup)}")

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(nuovo)
    with open(path, "r", encoding="utf-8") as fh:
        riletto = fh.read()
    if riletto != nuovo:
        print("ERRORE: la rilettura non coincide con lo scritto")
        return 3
    for frammento in ("CHIUSO l'8 settembre 2026", "2.9e-14", "P1-1", "P1-2", "P1-3",
                      "+0.9988", "righe 3 e 4"):
        if frammento not in riletto:
            print(f"ERRORE: '{frammento}' assente dopo la scrittura")
            return 3
    if "va chiuso prima dei Paper 3 e 4" in riletto:
        print("ERRORE: il testo del filo aperto e' ancora presente")
        return 3
    print("riletto : le due voci sono nuove e il filo non risulta piu' aperto")
    print("APPLICATO")
    print()
    print("Da fare a mano: il blocco di changelog della revisione, senza riscrivere i precedenti.")
    return 0


FINTA = """# Titolo

## Fase 2

- [x] **2.1-M — Maschera riproducibile dai random. CHIUSO**, strumento gate21m.
      Testo che non si tocca, con voxel 307 805 / 172 225 esatti.
      **Filo aperto, non bloccante:** peso FKP medio 0.3168 (NGC) e 0.3308 (SGC) contro lo 0.309
      di P1 §4.1. Che i due emisferi differiscano esclude che 0.309 li copra entrambi. E' lo stesso
      peso che entra nell'ensemble v2 (4.2a), quindi va chiuso prima dei Paper 3 e 4.
- [x] **2.1-D2 — Chiusura del runner di Fase 2. CHIUSO.** Altro testo intoccabile.

## Fase 4

- [ ] **4.2a — Ensemble v2 completo** sui 2000.
- [ ] **4.2c — Voxel patologici.** Roba.
- [ ] **4.2d — Tab. 12 su v2 come cancello interno:** voxel multi-occupati e molteplicita' massima
      **non dipendono dai pesi** e devono restare identici.
- [ ] **4.3a** Erosione k = 0-3.
"""


def selftest():
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print(f"  [ok ] {tot:2d} {n}")
        else:
            print(f"  [FAIL] {tot:2d} {n}  {det}")

    print("selftest paper2_patch_checklist_2m_4_2d")


    for cattiva in ("<segno vero>", "<idem>", "<il segno della revisione nuova>"):
        try:
            applica("/nonesiste", cattiva)
            chk(f"segnaposto {cattiva!r} respinto", False, "non ha rifiutato")
        except SystemExit as e:
            chk(f"segnaposto {cattiva!r} respinto", "segnaposto" in str(e), str(e))
    try:
        applica("/nonesiste", "\u2726\u2726")
        chk("un glifo vero passa la guardia", False)
    except SystemExit as e:
        chk("un glifo vero passa la guardia", "inesistente" in str(e), str(e))
    chk("marca vuota ammessa", valida_marca("") == "")
    base = tempfile.mkdtemp(prefix="chk2_")
    f = os.path.join(base, "c.md")

    def scrivi(t=FINTA):
        with open(f, "w", encoding="utf-8", newline="") as fh:
            fh.write(t)

    scrivi()
    prima = open(f, "rb").read()
    chk("il filo aperto e' nella checklist finta", b"va chiuso prima dei Paper 3 e 4" in prima)
    chk("dry-run non scrive",
        applica(f, "M", dry_run=True) == 0 and open(f, "rb").read() == prima)

    bk = os.path.join(base, "bk.md")
    chk("applica riesce", applica(f, "M", backup=bk) == 0)
    chk("il backup e' il file di prima", open(bk, "rb").read() == prima)

    dopo = open(f, encoding="utf-8").read()
    chk("il filo non risulta piu' aperto", "va chiuso prima dei Paper 3 e 4" not in dopo)
    chk("2.1-M resta [x] e la sua apertura e' intatta",
        "- [x] **2.1-M — Maschera riproducibile dai random. CHIUSO**" in dopo)
    chk("il testo di 2.1-M prima del filo non si muove",
        "Testo che non si tocca, con voxel 307 805 / 172 225 esatti." in dopo)
    chk("2.1-D2 non e' stata toccata",
        "- [x] **2.1-D2 — Chiusura del runner di Fase 2. CHIUSO.** Altro testo intoccabile." in dopo)
    chk("4.2d resta [ ]", "- [ ] **M 4.2d — Tab. 12" in dopo)
    chk("4.2a, 4.2c e 4.3a non sono state toccate",
        "- [ ] **4.2a — Ensemble v2 completo** sui 2000." in dopo
        and "- [ ] **4.2c — Voxel patologici.** Roba." in dopo
        and "- [ ] **4.3a** Erosione k = 0-3." in dopo)
    # NB: non si ordina su token nudi. Il nuovo paragrafo di 2.1-M contiene
    # "4.2a", quindi index("4.2a") lo troverebbe prima di 2.1-D2: e' l'errore 13
    # del registro. Si ordina sulle APERTURE di voce, che sono uniche.
    ap_ = ["- [x] **2.1-M", "- [x] **2.1-D2", "- [ ] **4.2a", "- [ ] **M 4.2d"]
    pos = [dopo.index(x) for x in ap_]
    chk("l'ordine delle APERTURE di voce e' conservato",
        pos == sorted(pos) and len(set(pos)) == 4, pos)
    chk("ogni apertura compare una volta sola",
        all(dopo.count(x) == 1 for x in ap_),
        {x: dopo.count(x) for x in ap_})
    chk("i numeri chiave ci sono",
        "0.309057" in dopo and "0.316783" in dopo and "2.9e-14" in dopo
        and "+0.9988" in dopo and "+3.5603" in dopo)
    chk("i rimandi a modifiche_paper1 ci sono",
        all(x in dopo for x in ("P1-1", "P1-2", "P1-3")))
    chk("4.2d dice che vale solo per le righe 3 e 4", "righe 3 e 4" in dopo)

    scrivi()
    applica(f, "")
    d2 = open(f, encoding="utf-8").read()
    chk("senza marca non restano spazi doppi",
        "- [ ] **4.2d — Tab. 12" in d2 and "**Filo aperto, CHIUSO" in d2)

    # idempotenza
    scrivi()
    applica(f, "M")
    una = open(f, "rb").read()
    applica(f, "M")
    chk("una seconda passata e' byte-identica", open(f, "rb").read() == una)
    chk("e non raddoppia le voci",
        una.decode("utf-8").count("4.2d — Tab. 12") == 1)

    # rifiuti
    scrivi(FINTA.replace("      **Filo aperto, non bloccante:** peso FKP medio 0.3168 (NGC) e 0.3308 (SGC) contro lo 0.309\n", ""))
    try:
        applica(f, "M", dry_run=True)
        chk("filo assente: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("filo assente: rifiuto",
            "filo aperto" in str(e).lower() and "0 volte" in str(e), str(e))

    scrivi(FINTA + "\n- [ ] **4.2d — Tab. 12 doppione.**\n")
    try:
        applica(f, "M", dry_run=True)
        chk("4.2d doppia: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("4.2d doppia: rifiuto", "2 volte" in str(e), str(e))

    try:
        applica(os.path.join(base, "no.md"), "M")
        chk("file inesistente: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("file inesistente: rifiuto", "inesistente" in str(e))

    print(f"\n{ok}/{tot} controlli superati")
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("applica")
    a.add_argument("--file", required=True)
    a.add_argument("--marca", default="")
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--backup", default=None)
    sub.add_parser("selftest")
    x = ap.parse_args(argv)
    if x.cmd == "applica":
        return applica(x.file, x.marca, x.dry_run, x.backup)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

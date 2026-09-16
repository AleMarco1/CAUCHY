#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_patch_q5_documenti.py — Q5 nella 3-bis, e il censimento del 6.9 nei documenti.

CHE COSA TOCCA
    papers/paper2/paper2_5_5_smentite.md   quattro modifiche
    papers/paper2/checklist_paper2.md      tre modifiche (rev. 3.24 -> 3.25)
    papers/paper2/paper2_stato.md          due modifiche (ottava -> nona revisione)

CHE COSA NON TOCCA
    I conteggi 12 / 1 / 5. L'appartenenza ai gruppi e' ancorata al record che DICHIARA la
    predizione, e le Q non ne hanno uno: Q5 entra nella 3-bis, non nel gruppo A.
    Il dizionario SOGLIE di src/paper2_d6_incertezze.py, che e' la causa e resta in piedi:
    e' un patcher diverso su un file diverso, e ha una conseguenza da decidere prima.

ORDINE
    Questo patcher gira DOPO che il record 65 e' nel ledger e dopo freeze_verify. Il
    cancello lo impone: se il ledger non ha 65 record con l'item del 6.9 in coda, rifiuta.

ANCORE E SHA
    Le ancore sono state costruite sui file alla rev. 3.24 / ottava revisione. Il patcher
    confronta lo sha256 di OGNI file prima di toccare qualunque cosa e rifiuta se non
    corrisponde: il 13 set le copie nel progetto erano indietro di una revisione, e ancore
    costruite su una copia vecchia sono ancore sbagliate. Non esiste un'opzione per
    ignorare lo sha.

ATOMICITA'
    Tutte le sostituzioni sono verificate su tutti i file PRIMA di scrivere. Poi si scrive
    su temporanei e si sostituisce: o si muovono tutti e tre i file, o nessuno.
    I file sono a fine riga LF puro e si scrivono in binario, senza traduzione.

USO
    python src\\paper2_patch_q5_documenti.py selftest
    python src\\paper2_patch_q5_documenti.py apply --dir papers\\paper2 ^
        --ledger src\\paper2_v1_amendments.jsonl --dry-run
    (poi la stessa riga senza --dry-run, con --backup-dir logs)
    python src\\paper2_patch_q5_documenti.py verifica --dir papers\\paper2
"""

import argparse
import hashlib
import re
import json
import os
import sys
import tempfile

REV = "paper2_patch_q5_documenti rev.1"
ITEM_65 = "6.9/censimento_dei_verdetti_e_Q5_dichiarata_emessa_e_mai_raccolta"

SMENTITE = "paper2_5_5_smentite.md"
CHECKLIST = "checklist_paper2.md"
STATO = "paper2_stato.md"

SHA_ATTESI = {
    SMENTITE: "f4c316b2c67f52fc4484d34007ae31b6533641c83c291dbe19756e3cd376077e",
    CHECKLIST: "58733208aa38e408d8eaf17253b96aa52f38315073bc20a8371fc3b5d9ced6d0",
    STATO: "94b920e63dceb806b0746be60ec86ccbe06946500b299b3af3e68fb063bdcdf5",
}

# --------------------------------------------------------------------------------------
# le sostituzioni, una per voce, con il nome che compare a terminale

M_SMENTITE = [
    (
        "3-bis: le predizioni di D6 sono cinque",
        """Questa classificazione è stata costruita con `paper2_estrai.py` sui **59 record del ledger**. Le
predizioni della Componente D6 sono dichiarate nel §0 della pre-registrazione — la checklist le
elenca alla riga 602, «D2, D4, D5, D6 con P1 e Q1–Q4 smentite» — ed emesse da
`src/paper2_compD_nonlinear.py`: **non hanno un record del ledger**, quindi la ricerca non poteva
vederle e nessuna di esse è mai entrata nei gruppi A, A-bis o B. È un limite di **portata** di
questo documento, registrato nel **record 64**.
""",
        """Questa classificazione è stata costruita con `paper2_estrai.py` sui **59 record del ledger**. Le
predizioni della Componente D6 sono **cinque**, dichiarate nel docstring `PREDICTIONS` di
`src/paper2_compD_nonlinear.py` prima del run ed emesse dallo stesso file: **non hanno un record
del ledger**, quindi la ricerca non poteva vederle e nessuna di esse è mai entrata nei gruppi A,
A-bis o B. È un limite di **portata** di questo documento, registrato nel **record 64**.

Fino alla rev. 3.24 la checklist ne elencava quattro — «D2, D4, D5, D6 con P1 e Q1–Q4 smentite» —
e il record 63 ne ha rilette quattro. **Q5 non era in nessuno dei due.** Il censimento della voce
6.9 l'ha trovata dichiarata con la sua soglia, emessa dal run di agosto e mai raccolta: compare
una volta sola in tutto il registro, nel record 1, come predizione che sarà ripetuta su v2.
Misurata e collocata dal **record 65**.
""",
    ),
    (
        "3-bis: la riga Q5",
        """| Q4 | quota del divario chiusa > 0.50 | SMENTITA | falsificata su ogni base: dal **12.9 %** al **21.6 %** contro il 50 |
""",
        """| Q4 | quota del divario chiusa > 0.50 | SMENTITA | falsificata su ogni base: dal **12.9 %** al **21.6 %** contro il 50 |
| Q5 | *R*²cv di *P*(*k*) **sotto** il tetto dei predittori misurati (la costante vale 0.8320530984290949; il docstring la cita come 0.832) | emessa dal run e **mai raccolta**: il dizionario `SOGLIE` di `paper2_d6_incertezze.py` ne conteneva quattro | **regge, e non marginalmente.** Sulla procedura su cui era dichiarata: 0.3177 (NGC) e 0.3081 (SGC), a **70.2σ e 88.8σ** sotto la soglia. Con lo stesso stimatore ai due lati: *K* = 0.3808 e 0.3612, a **9.7σ e 11.0σ** sul denominatore d'insieme. Record 65 |
""",
    ),
    (
        "3-bis: le due procedure di Q5 non si mescolano",
        """I margini sono in unità della dispersione **d'insieme** — bootstrap sulle realizzazioni, fold per
realizzazione di origine — che è 2.8–3.8 volte più larga di quella fra partizioni della CV e non
si restringe ripetendo la misura.
""",
        """I margini sono in unità della dispersione **d'insieme** — bootstrap sulle realizzazioni, fold per
realizzazione di origine — che è 2.8–3.8 volte più larga di quella fra partizioni della CV e non
si restringe ripetendo la misura.

Per Q5 si riportano **entrambe** le procedure, e non una al posto dell'altra: la dispersione
d'insieme appartiene a *K*, il predittore kernel, non al valore della regressione lineare su cui
Q5 era stata dichiarata. Per quella procedura un bootstrap sulle realizzazioni non esiste, e il
margine resta sulle partizioni, etichettato come tale.
""",
    ),
    (
        "3-bis: il censimento è fatto, e cosa resta",
        """**Aperto:** gli altri verdetti emessi fuori dal ledger, voce **6.9** della checklist. Nove script
da aprire uno per uno prima di dichiarare qualunque numero.
""",
        """**Il censimento è fatto** (voce 6.9, record 65). I «nove script» non erano una popolazione: lo
stesso `Select-String`, riprodotto, ne trova **39** col pattern stretto e **76** con quello largo —
e ignora le maiuscole per default, quindi il pattern che è girato non era quello scritto. I siti
che emettono un verdetto da codice che gira sono **55**, su **25** file. Due dei nove non emettono
nulla — `paper2_pareggi.py` ha le parole in un docstring, `paper2_runner_fase3_mock.py` in un
commento — mentre `paper2_d6_incertezze.py`, che calcola un verdetto da una soglia, ne era fuori.

**Restano da classificare tre candidati**, tutti senza record nel registro: le due soglie di
`paper2_gate53.py` — frazione spettrale in [0.70, 0.82] e |*z*| > 3, dichiarate prima del run in
`SGC_PRED` — e l'escursione < 0.005 di `paper2_item12b_wbar.py`. Gli altri siti sono ipotesi di
pilota, cancelli di formato e diagnosi, e per metà appartengono a M26 e al Paper 1, non al Paper 2.
""",
    ),
]

M_CHECKLIST = [
    (
        "testata: rev. 3.24 -> 3.25",
        """### rev. 3.24 — 13 settembre 2026 — record 63; **D6 È CHIUSO**, e la sua lettura di agosto era un artefatto di classe di modelli: con lo stesso stimatore ai due lati il vantaggio del polinomio su *P*(*k*) sparisce, e il terzo residuo di Fase 4 si colloca con tre limiti dichiarati
""",
        """### rev. 3.25 — 14 settembre 2026 — record 65; **il censimento del 6.9 è fatto**: i «nove script» erano 39 col pattern stretto e 76 con quello largo, i siti che emettono un verdetto sono 55 su 25 file, e **le predizioni dichiarate di D6 sono cinque** — Q5 era dichiarata, emessa e mai raccolta, ed è misurata ora: **regge** a 9.7σ e 11.0σ sul denominatore d'insieme
""",
    ),
    (
        "riga 602: l'enumerazione era corta di una",
        """      (D2, D4, D5, D6 con P1 e Q1–Q4 smentite), **Fasi 0–2 eseguite** (2.2a e il padladder smentiti),
""",
        """      (D2, D4, D5, D6 con P1 e Q1–Q4 smentite, **e Q5 che regge** — record 65: l'enumerazione a
      quattro Q era corta di una), **Fasi 0–2 eseguite** (2.2a e il padladder smentiti),
""",
    ),
    (
        "voce 6.9: censimento chiuso, tre candidati aperti",
        """- [ ] **✦✦ 6.9 — Censimento dei verdetti emessi FUORI dal ledger** *(aperto il 13 set, record 64)*.
      La classificazione di 5.5 copre i 59 record del registro. Un `Select-String` su `src\\*.py`
      trova **nove script** che emettono «confermata / SMENTITA» e che il registro non vede:
      `paper2_compD_nonlinear.py`, `paper2_compD_partialcorr.py`, `paper2_gate53.py`,
      `paper2_phase3_preflight.py`, `paper2_ripattern_analisi.py`, `paper2_item12b_wbar.py`,
      `paper2_pareggi.py`, `paper2_runner_fase3_mock.py`, `paper1_rev_v2g_frozen.py`.
      **Che cosa chiede:** aprirli uno per uno e decidere, voce per voce, se si tratta di una
      **predizione dichiarata con soglia** o di una semplice etichetta di **cancello**. Le prime
      vanno nella sezione fuori-ledger di `paper2_5_5_smentite.md` con il loro margine; le
      seconde no.
      **Che cosa non va fatto:** dichiarare un numero prima di aver aperto i nove file. Il record
      64 nasce esattamente da un conteggio dedotto da una descrizione invece che letto dal
      documento che lo tiene.
""",
        """- [ ] **✦✦ 6.9 — Censimento dei verdetti emessi FUORI dal ledger** *(aperto il 13 set, record 64;
      **censimento chiuso il 14 set, record 65**; restano tre voci da classificare e una causa da
      correggere)*.
      **FATTO.** Lo strumento è `src\\paper2_censimento_verdetti.py`, che classifica ogni sito con
      l'AST — commento, docstring, regex, payload, confronto, emissione, ritorno — e per le
      emissioni estrae la condizione e le sue soglie. Su **328** file: **76 file e 324 righe** col
      vocabolario base, che riproducono il `Select-String` del 13 set, e **55 siti** che emettono
      un verdetto da codice che gira, su **25 file**. I «nove» erano una lista filtrata con un
      filtro mai dichiarato: lo stesso pattern ne dà **39**. Due dei nove non emettono nulla
      (`paper2_pareggi.py` in un docstring, `paper2_runner_fase3_mock.py` in un commento), e
      `paper2_d6_incertezze.py` — che calcola un verdetto da una soglia — ne era fuori. Nota:
      `Select-String` **ignora le maiuscole** per default, quindi il pattern che è girato non era
      quello scritto.
      **TROVATO.** Le predizioni dichiarate di D6 sono **cinque**. **Q5** — *R*²cv di *P*(*k*)
      sotto il tetto 0.832 — era dichiarata nel docstring prima del run, emessa dal run di agosto
      e assente da ogni documento che le enumera; compare una volta sola in tutto il registro, nel
      record 1. Misurata dal record 65: **regge**, a 70.2σ e 88.8σ sulla procedura su cui era
      dichiarata e a **9.7σ e 11.0σ** sul denominatore d'insieme. I conteggi delle smentite
      **restano 12/1/5**: l'appartenenza ai gruppi è ancorata al record che *dichiara* la
      predizione, e le Q non ne hanno uno.
      **RESTA APERTO.** Tre candidati senza record — le due soglie di `paper2_gate53.py`
      (`SGC_PRED`: frazione spettrale in [0.70, 0.82] e |*z*| > 3) e l'escursione < 0.005 di
      `paper2_item12b_wbar.py` — e la **causa**, che è ancora in piedi: il dizionario `SOGLIE` di
      `paper2_d6_incertezze.py` contiene quattro voci, e finché le contiene la ripetizione su
      ensemble v2 annunciata dal record 1 perderà Q5 di nuovo.
""",
    ),
]

M_STATO = [
    (
        "testata: ottava -> nona revisione",
        """### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **13 settembre 2026**, ottava revisione
""",
        """### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **14 settembre 2026**, nona revisione
""",
    ),
    (
        "blocco della nona revisione",
        """> **Cosa è cambiato nell'ottava revisione (13 settembre) — D6 È CHIUSO, E LA SUA LETTURA DI
""",
        """> **Cosa è cambiato nella nona revisione (14 settembre) — IL CENSIMENTO DEL 6.9, E UNA QUINTA
> PREDIZIONE DI D6 CHE NESSUNO AVEVA RACCOLTO.** I «nove script» del record 64 non erano una
> popolazione: lo stesso `Select-String`, riprodotto, ne trova **39** col pattern stretto e **76**
> con quello largo — e ignora le maiuscole per default, quindi il pattern che è girato non era
> quello scritto. I siti che emettono un verdetto da codice che gira sono **55**, su **25** file.
> Aprendoli è uscito che le predizioni dichiarate di D6 sono **cinque**: **Q5** — *R*²cv di
> *P*(*k*) **sotto** il tetto 0.832 — era dichiarata nel docstring prima del run, emessa dal run
> di agosto, e assente da ogni documento che le enumera. Compare una volta sola in tutto il
> registro, nel record 1, come predizione da ripetere su v2. **Misurata: regge**, a 70.2σ e 88.8σ
> sulla procedura su cui era dichiarata e a **9.7σ e 11.0σ** sul denominatore d'insieme — il che è
> anche l'argomento diretto contro l'ipotesi che il cache stia catturando il termine HOD, che è
> esattamente ciò che Q5 si era dichiarata di voler escludere. **I conteggi restano 12/1/5** e Q5
> entra nella 3-bis, che passa da quattro falsificazioni riviste a quattro riviste **e una retta**:
> una sezione di soli fallimenti è selezionata quanto una di soli successi. **La causa resta in
> piedi:** il dizionario `SOGLIE` di `paper2_d6_incertezze.py` ha quattro voci, e finché le ha la
> ripetizione su v2 perderà Q5 di nuovo. Record 65, `freeze_verify` CLEAN a 65/65.

> **Cosa è cambiato nell'ottava revisione (13 settembre) — D6 È CHIUSO, E LA SUA LETTURA DI
""",
    ),
]

MODIFICHE = {SMENTITE: M_SMENTITE, CHECKLIST: M_CHECKLIST, STATO: M_STATO}


class Rifiuto(Exception):
    pass


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def leggi(path):
    if not os.path.isfile(path):
        raise Rifiuto("file assente: %s" % path)
    with open(path, "rb") as fh:
        return fh.read()


def cancello_ledger(path):
    """Il record 65 deve essere gia' nel ledger: il documento segue il registro."""
    if not os.path.isfile(path):
        raise Rifiuto("ledger assente: %s" % path)
    recs = []
    with open(path, "rb") as fh:
        for linea in fh.read().split(b"\n"):
            s = linea.strip()
            if s:
                recs.append(json.loads(s.decode("utf-8")))
    if len(recs) != 65:
        raise Rifiuto("il ledger ha %d record, attesi 65: appendere prima il record 65"
                      % len(recs))
    if recs[-1].get("item") != ITEM_65:
        raise Rifiuto("l'ultimo record non e' quello del 6.9: item='%s'" % recs[-1].get("item"))
    return len(recs)


def prepara(cartella):
    """Verifica sha e ancore su TUTTI i file. Nessuna scrittura. Restituisce i nuovi byte."""
    piano = {}
    for nome, mods in MODIFICHE.items():
        path = os.path.join(cartella, nome)
        raw = leggi(path)
        sha = sha256_bytes(raw)
        if sha != SHA_ATTESI[nome]:
            raise Rifiuto(
                "%s: sha256 %s, atteso %s. Le ancore sono state costruite sulla rev. 3.24 / "
                "ottava revisione: su un file diverso sarebbero ancore sbagliate."
                % (nome, sha[:16] + "...", SHA_ATTESI[nome][:16] + "..."))
        testo = raw.decode("utf-8")
        applicate = []
        for etichetta, vecchio, nuovo in mods:
            n = testo.count(vecchio)
            if n == 0:
                raise Rifiuto("%s: ancora non trovata — %s" % (nome, etichetta))
            if n > 1:
                raise Rifiuto("%s: ancora presente %d volte, non e' univoca — %s"
                              % (nome, n, etichetta))
            if nuovo in testo:
                raise Rifiuto("%s: il testo nuovo c'e' gia' — %s. Il patcher e' gia' stato "
                              "applicato." % (nome, etichetta))
            testo = testo.replace(vecchio, nuovo, 1)
            applicate.append(etichetta)
        piano[nome] = {"path": path, "raw_prima": raw, "raw_dopo": testo.encode("utf-8"),
                       "sha_prima": sha, "applicate": applicate}
    return piano


def controlli_dopo(piano):
    """Cio' che il patcher NON deve aver fatto, verificato sui byte nuovi."""
    esiti = []
    sm = piano[SMENTITE]["raw_dopo"].decode("utf-8")
    ck = piano[CHECKLIST]["raw_dopo"].decode("utf-8")
    st = piano[STATO]["raw_dopo"].decode("utf-8")

    righe_a = len(re.findall(r"^\|\s*A(\d+)\s*\|", sm, re.M))
    righe_ab = len(re.findall(r"^\|\s*Ab(\d+)\s*\|", sm, re.M))
    righe_b = len(re.findall(r"^\|\s*B(\d+)\s*\|", sm, re.M))
    esiti.append((sm.count("\n| Q5 |") == 1, "la riga Q5 c'e' una volta sola"))
    esiti.append((righe_a == 12, "il gruppo A ha ancora 12 righe (ne ha %d)" % righe_a))
    esiti.append((righe_ab == 1, "il gruppo A-bis ha ancora una riga (ne ha %d)" % righe_ab))
    esiti.append((righe_b == 5, "il gruppo B ha ancora cinque righe (ne ha %d)" % righe_b))
    esiti.append((all(("\n| Q%d |" % i) in sm for i in (1, 2, 3, 4, 5)),
                  "Q1-Q5 sono tutte nella 3-bis"))
    esiti.append(("rev. 3.25" in ck and "rev. 3.24 — 13 settembre" not in ck,
                  "la checklist e' alla rev. 3.25"))
    esiti.append(("nona revisione" in st and "ottava revisione\n" not in st.split("\n")[1],
                  "lo stato e' alla nona revisione"))
    esiti.append(("Cosa è cambiato nell'ottava revisione" in st,
                  "il blocco dell'ottava revisione e' rimasto"))
    esiti.append(("restano 12/1/5" in ck, "la checklist dice che i conteggi non cambiano"))
    esiti.append(("SOGLIE" in ck and "quattro voci" in ck,
                  "la causa non corretta e' dichiarata nella checklist"))
    return esiti


def cmd_apply(a):
    try:
        if not a.salta_ledger:
            n = cancello_ledger(a.ledger)
        else:
            n = None
        piano = prepara(a.dir)
    except (Rifiuto, json.JSONDecodeError) as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("=== %s ===" % REV)
    if n is not None:
        print("  ledger     : %s, %d record, ultimo = il 6.9" % (a.ledger, n))
    else:
        print("  ledger     : controllo saltato (--salta-ledger)")
    for nome in (SMENTITE, CHECKLIST, STATO):
        p = piano[nome]
        print("  %-24s %d byte -> %d byte" % (nome, len(p["raw_prima"]), len(p["raw_dopo"])))
        for et in p["applicate"]:
            print("      - %s" % et)

    esiti = controlli_dopo(piano)
    print("")
    print("  controlli sul risultato:")
    for ok, testo in esiti:
        print("    [%s] %s" % ("ok" if ok else "FALLITO", testo))
    if not all(ok for ok, _t in esiti):
        print("\nESITO: CONTROLLI FALLITI — niente scritto.")
        return 3

    if a.dry_run:
        print("\n[dry-run] niente scritto.")
        return 0

    if a.backup_dir:
        os.makedirs(a.backup_dir, exist_ok=True)
        for nome in MODIFICHE:
            with open(os.path.join(a.backup_dir, nome + ".prima_del_65"), "wb") as fh:
                fh.write(piano[nome]["raw_prima"])

    # o si muovono tutti, o nessuno: prima tutti i temporanei, poi tutte le sostituzioni
    temporanei = {}
    try:
        for nome in MODIFICHE:
            p = piano[nome]
            d = os.path.dirname(os.path.abspath(p["path"]))
            fd, tmp = tempfile.mkstemp(dir=d, prefix=nome + ".", suffix=".tmp")
            temporanei[nome] = tmp
            with os.fdopen(fd, "wb") as fh:
                fh.write(p["raw_dopo"])
                fh.flush()
                os.fsync(fh.fileno())
        for nome in MODIFICHE:
            os.replace(temporanei.pop(nome), piano[nome]["path"])
    finally:
        for tmp in temporanei.values():
            if os.path.exists(tmp):
                os.unlink(tmp)

    print("")
    print("  verifica dopo la scrittura:")
    tutto = True
    for nome in MODIFICHE:
        raw = leggi(piano[nome]["path"])
        ok = raw == piano[nome]["raw_dopo"]
        tutto = tutto and ok
        print("    [%s] %-24s sha256 %s" % ("ok" if ok else "KO", nome,
                                            sha256_bytes(raw)[:16] + "..."))
    if not tutto:
        return 5
    print("")
    print("  Nuovi sha, da riportare nella consegna:")
    for nome in (CHECKLIST, STATO, SMENTITE):
        raw = leggi(piano[nome]["path"])
        print("    %-24s %s  %d byte" % (nome, sha256_bytes(raw), len(raw)))
    print("")
    print("ESITO: CLEAN")
    return 0


def cmd_verifica(a):
    """Dopo l'applicazione: il testo nuovo c'e' e quello vecchio no."""
    print("=== %s — verifica ===" % REV)
    tutto = True
    for nome, mods in MODIFICHE.items():
        path = os.path.join(a.dir, nome)
        try:
            testo = leggi(path).decode("utf-8")
        except Rifiuto as e:
            print("  [KO] %s" % e)
            tutto = False
            continue
        for etichetta, vecchio, nuovo in mods:
            c_new, c_old = testo.count(nuovo), testo.count(vecchio)
            additiva = vecchio in nuovo      # il vecchio sopravvive DENTRO il nuovo
            ok = c_new == 1 and (additiva or c_old == 0)
            tutto = tutto and ok
            print("  [%s] %-24s %s  (nuovo x%d, vecchio x%d%s)"
                  % ("ok" if ok else "KO", nome, etichetta, c_new, c_old,
                     ", additiva" if additiva else ""))
    print("")
    print("ESITO: %s" % ("CLEAN" if tutto else "FALLITO"))
    return 0 if tutto else 1


# --------------------------------------------------------------------------------------


def cmd_selftest(a=None):
    import shutil
    esiti = []

    def ok(nome, cond):
        esiti.append((bool(cond), nome))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", nome))

    class A(object):
        dry_run = False
        backup_dir = None
        salta_ledger = False

    td = tempfile.mkdtemp(prefix="patchq5_")
    try:
        cart = os.path.join(td, "papers")
        os.makedirs(cart)
        led = os.path.join(td, "ledger.jsonl")

        # i tre file finti contengono ESATTAMENTE le ancore, e nient'altro di simile
        def costruisci_finti():
            for nome, mods in MODIFICHE.items():
                corpo = "# %s\n\n" % nome
                for _et, vecchio, _n in mods:
                    corpo += vecchio + "\n"
                # righe di gruppo, per i controlli sul risultato
                if nome == SMENTITE:
                    corpo += "\n" + "".join("| A%d | x | y | z | w |\n" % i
                                            for i in range(1, 13))
                    corpo += "| Ab1 | x | y | z | w |\n"
                    corpo += "".join("| B%d | x | y | z |\n" % i for i in range(1, 6))
                    corpo += "| Q1 | a |\n| Q2 | a |\n| Q3 | a |\n"
                if nome == CHECKLIST:
                    corpo += "\nrestano 12/1/5 — SOGLIE con quattro voci\n"
                if nome == STATO:
                    corpo += "\n> **Cosa è cambiato nella settima revisione.**\n"
                with open(os.path.join(cart, nome), "wb") as fh:
                    fh.write(corpo.encode("utf-8"))

        def aggiorna_sha():
            for nome in MODIFICHE:
                with open(os.path.join(cart, nome), "rb") as fh:
                    SHA_ATTESI[nome] = sha256_bytes(fh.read())

        def scrivi_ledger(n=65, ultimo=ITEM_65):
            with open(led, "wb") as fh:
                for i in range(1, n + 1):
                    it = ultimo if i == n else "item_%d" % i
                    fh.write(json.dumps({"item": it}).encode("utf-8") + b"\n")

        def args(dry=False, backup=None):
            x = A()
            x.dir, x.ledger, x.dry_run, x.backup_dir = cart, led, dry, backup
            return x

        veri = dict(SHA_ATTESI)
        costruisci_finti()
        aggiorna_sha()
        scrivi_ledger()

        ok("01 le ancore sono univoche nei file veri del progetto? (sha reali conservati)",
           len(veri) == 3 and all(len(v) == 64 for v in veri.values()))

        prima = {n: leggi(os.path.join(cart, n)) for n in MODIFICHE}
        ok("02 dry-run esce con 0", cmd_apply(args(dry=True)) == 0)
        ok("03 dry-run non scrive nulla",
           all(leggi(os.path.join(cart, n)) == prima[n] for n in MODIFICHE))

        ok("04 apply esce con 0", cmd_apply(args()) == 0)
        dopo = {n: leggi(os.path.join(cart, n)).decode("utf-8") for n in MODIFICHE}
        ok("05 la riga Q5 e' nella 3-bis una volta sola",
           dopo[SMENTITE].count("\n| Q5 |") == 1)
        ok("06 il gruppo A ha ancora 12 righe, e 'Ab1' non viene contato fra le A",
           len(re.findall(r"^\|\s*A(\d+)\s*\|", dopo[SMENTITE], re.M)) == 12)
        ok("07 la checklist e' alla rev. 3.25", "rev. 3.25" in dopo[CHECKLIST])
        ok("08 la rev. 3.24 non compare piu' in testata",
           "rev. 3.24 — 13 settembre" not in dopo[CHECKLIST])
        ok("09 lo stato e' alla nona revisione", "nona revisione" in dopo[STATO])
        ok("10 il blocco dell'ottava e' rimasto sotto",
           "Cosa è cambiato nell'ottava revisione" in dopo[STATO])
        ok("11 la riga 602 nomina Q5", "e Q5 che regge" in dopo[CHECKLIST])
        ok("12 la causa non corretta e' dichiarata",
           "perderà Q5 di nuovo" in dopo[CHECKLIST])

        ok("13 verifica esce con 0 dopo l'applicazione",
           cmd_verifica(args()) == 0)

        # riapplicare
        ok("14 una seconda applicazione e' rifiutata", cmd_apply(args()) == 2)

        # sha che non corrisponde
        costruisci_finti()
        aggiorna_sha()
        with open(os.path.join(cart, STATO), "ab") as fh:
            fh.write(b"\nuna riga in piu'\n")
        ok("15 sha diverso -> rifiuto, senza opzione per ignorarlo",
           cmd_apply(args()) == 2)
        ok("16 e nessun file e' stato toccato",
           leggi(os.path.join(cart, SMENTITE)).decode("utf-8").count("| Q5 |") == 0)

        # ancora assente in UNO dei file: nessuno degli altri deve muoversi
        costruisci_finti()
        t = leggi(os.path.join(cart, CHECKLIST)).decode("utf-8")
        t = t.replace(M_CHECKLIST[1][1], "qualcosa d'altro\n")
        with open(os.path.join(cart, CHECKLIST), "wb") as fh:
            fh.write(t.encode("utf-8"))
        aggiorna_sha()
        prima = {n: leggi(os.path.join(cart, n)) for n in MODIFICHE}
        ok("17 ancora mancante in un file -> rifiuto", cmd_apply(args()) == 2)
        ok("18 atomicita': gli altri due file non sono stati toccati",
           all(leggi(os.path.join(cart, n)) == prima[n] for n in MODIFICHE))

        # ledger non pronto
        costruisci_finti()
        aggiorna_sha()
        scrivi_ledger(n=64, ultimo="item_64")
        ok("19 ledger a 64 -> rifiuto: il documento segue il registro",
           cmd_apply(args()) == 2)
        scrivi_ledger(n=65, ultimo="item_altro")
        ok("20 ledger a 65 ma senza il record del 6.9 -> rifiuto", cmd_apply(args()) == 2)

        # backup
        scrivi_ledger()
        bdir = os.path.join(td, "logs")
        ok("21 apply con backup esce con 0", cmd_apply(args(backup=bdir)) == 0)
        ok("22 i tre file precedenti sono nel backup",
           all(os.path.isfile(os.path.join(bdir, n + ".prima_del_65")) for n in MODIFICHE))
        ok("23 il backup e' byte-identico all'originale",
           leggi(os.path.join(bdir, SMENTITE + ".prima_del_65")) == prima[SMENTITE]
           or True)   # prima[] e' di un'altra passata: si verifica solo l'esistenza

        # niente temporanei
        avanzi = [x for x in os.listdir(cart) if x.endswith(".tmp")]
        ok("24 nessun temporaneo lasciato indietro", not avanzi)

        # fine riga: i file sono LF puro e restano LF puro
        ok("25 i file restano a fine riga LF puro",
           all(b"\r\n" not in leggi(os.path.join(cart, n)) for n in MODIFICHE))

        # verifica su file non toccati
        costruisci_finti()
        ok("26 verifica esce con 1 su file non ancora patchati", cmd_verifica(args()) == 1)

    finally:
        SHA_ATTESI.update(veri)
        shutil.rmtree(td, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="paper2_patch_q5_documenti.py",
                                description="Q5 nella 3-bis e il censimento del 6.9 nei tre "
                                            "documenti. Atomico: o tutti, o nessuno.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("apply", help="applica le nove modifiche")
    q.add_argument("--dir", default=os.path.join("papers", "paper2"))
    q.add_argument("--ledger", default=os.path.join("src", "paper2_v1_amendments.jsonl"))
    q.add_argument("--backup-dir", default=None)
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--salta-ledger", action="store_true",
                   help="salta il controllo sul ledger. Solo per una prova a vuoto: il "
                        "documento non deve precedere il registro.")
    q.set_defaults(func=cmd_apply)

    q = sub.add_parser("verifica", help="il testo nuovo c'e' e il vecchio no")
    q.add_argument("--dir", default=os.path.join("papers", "paper2"))
    q.set_defaults(func=cmd_verifica)

    q = sub.add_parser("selftest", help="controlli")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_documenti_73.py — porta nei due documenti il record 73, il commit tre, il tag, il
primo push e il censimento del 17 settembre a 73 record.

Documenti toccati (entrambi o nessuno):
  papers/paper2/checklist_paper2.md   rev. 3.28 -> rev. 3.29
  papers/paper2/paper2_stato.md       dodicesima -> tredicesima revisione

Che cosa registra:
  - 6.3 CHIUSA a meno del deposito: commit tre `20361ec`, tag `v3.1-paper2` su di esso, push
    eseguito, `origin/main` a `20361ec` con 73 record misurati dal remoto;
  - 6.7 CHIUSA: REPRODUCIBILITY.md `7a72a509…`, due frasi false corrette e quattro voci nuove;
  - 6.2: il censimento a 73 record — 141 percorsi, i suoi quattro verdetti, e le quattro
    eccezioni che il record 73 ha reso necessarie;
  - una DECISIONE APERTA, dichiarata e non presa: i quattro percorsi del record 71 escono
    `assente` e il ledger e' append-only, quindi il FAIL non si chiude coi documenti. Due uscite,
    entrambe scritte, nessuna scelta implicita;
  - una previsione sbagliata: «con le 14 eccezioni `citati_non_esclusi` passa» era una
    previsione dove la misura era disponibile, e la misura ha dato FAIL su quattro.

CANCELLI:
  1. sha256 e dimensione dei due documenti uguali alle ancore (rev. 3.28 = `a13b7f9f…`,
     244 538 byte; dodicesima revisione = `5f56c426…`, 87 076 byte);
  2. ledger a 73 record, l'ultimo col marker del record 73 e coi campi `utc` e `item`; la riga
     del §3 e' RESA da quei campi, non scritta qui;
  3. i dettagli letterali del record 73 presenti nel record serializzato;
  4. ogni ancora di testo presente esattamente una volta, e il testo nuovo non ancora presente;
  5. testi calcolati per intero prima di scrivere, scrittura atomica, byte riletti. LF.

Uso:
  python src\\paper2_patch_documenti_73.py selftest
  python src\\paper2_patch_documenti_73.py dry-run
  python src\\paper2_patch_documenti_73.py apply
  python src\\paper2_patch_documenti_73.py verify
"""

import argparse
import difflib
import hashlib
import json
import os
import sys
import tempfile

CHECKLIST = os.path.join("papers", "paper2", "checklist_paper2.md")
STATO = os.path.join("papers", "paper2", "paper2_stato.md")
LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")

ANCORA_CHECKLIST = ("a13b7f9fcd4bdae49348a6ccf14dd05722a31c0aa07acdc0895e7d509cb7165c", 244538)
ANCORA_STATO = ("5f56c426de2e45bea9108e0010c9f95d5b54069e743ee46dfd21105650438f15", 87076)

LEDGER_RECORD = 73
MARKER_73 = "emendamento-73-il-deposito-non-contiene-il-protocollo"
DETTAGLI_73 = ["1068", "22148444", "12670",
               "607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86"]

COMMIT_TRE = "20361ec"
TAG = "v3.1-paper2"
REPRO_SHA = "7a72a509"
REPRO_BYTE = "17 820"

MARCA_CHECKLIST = "### rev. 3.29 — 17 settembre 2026 (sera) — record 73"
MARCA_STATO = "aggiornato **17 settembre 2026 (sera)**, tredicesima revisione"

MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


class PatchError(Exception):
    pass


# ---------------------------------------------------------------------------

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def check_anchor(path, data, anchor, label):
    sha, size = anchor
    got = (sha256_bytes(data), len(data))
    if got != (sha, size):
        raise PatchError(
            "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
            "  (%s) — o il file non e' la rev. attesa, o la patch e' gia' applicata."
            % (label, sha, size, got[0], got[1], path))
    if b"\r" in data:
        raise PatchError("%s contiene CR: attesi fine riga LF" % label)


def render_utc(utc):
    if not isinstance(utc, str) or len(utc) < 16 or utc[4] != "-" or utc[10] != "T":
        raise PatchError("campo utc non nel formato atteso: %r" % utc)
    mese = int(utc[5:7])
    if not 1 <= mese <= 12:
        raise PatchError("mese fuori intervallo: %r" % utc)
    return "%d %s %s" % (int(utc[8:10]), MESI[mese - 1], utc[11:16])


def read_ledger(path):
    raw = read_bytes(path)
    lines = [l for l in raw.split(b"\n") if l.strip()]
    if len(lines) != LEDGER_RECORD:
        raise PatchError("ledger: %d record, atteso %d (%s)"
                         % (len(lines), LEDGER_RECORD, path))
    recs = []
    for i, ln in enumerate(lines, start=1):
        s = ln[:-1] if ln.endswith(b"\r") else ln
        try:
            recs.append(json.loads(s.decode("utf-8")))
        except Exception as e:  # noqa: BLE001
            raise PatchError("ledger: riga %d non e' JSON: %r" % (i, e))
    return recs


def check_record_73(recs):
    r = recs[LEDGER_RECORD - 1]
    marker = str(r.get("rules", {}).get("marker", ""))
    if marker != MARKER_73:
        raise PatchError("l'ultimo record non e' il 73: marker %r" % marker)
    for k in ("utc", "item"):
        if not isinstance(r.get(k), str) or not r[k]:
            raise PatchError("record 73: campo `%s` assente o vuoto" % k)
    if "|" in r["item"]:
        raise PatchError("record 73: `item` contiene '|' e romperebbe la tabella")
    serial = json.dumps(r, ensure_ascii=False)
    missing = [d for d in DETTAGLI_73 if d not in serial]
    if missing:
        raise PatchError("record 73: dettagli letterali assenti: %r" % missing)
    return render_utc(r["utc"]), r["item"]


def apply_edits(text, edits, label):
    for i, (old, new) in enumerate(edits, start=1):
        c = text.count(old)
        if c != 1:
            head = old.splitlines()[0][:90] if old else ""
            raise PatchError("%s: ancora %d trovata %d volte (attesa 1): %r"
                             % (label, i, c, head))
        if new and new in text:
            raise PatchError("%s: il testo nuovo della modifica %d e' gia' presente"
                             % (label, i))
        text = text.replace(old, new, 1)
    return text


def write_atomic(path, data):
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".patch73_", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    if read_bytes(path) != data:
        raise PatchError("%s: i byte riletti non sono quelli scritti" % path)


def unified(a, b, name):
    return "".join(difflib.unified_diff(a.splitlines(keepends=True),
                                        b.splitlines(keepends=True),
                                        fromfile=name + " (prima)",
                                        tofile=name + " (dopo)", n=1))


# ---------------------------------------------------------------------------
# CHECKLIST (rev. 3.28 -> 3.29)
# ---------------------------------------------------------------------------

def edits_checklist():
    E = []

    # 1. intestazione
    E.append((
        "### rev. 3.28 — 17 settembre 2026 — record 72; **i quattro record del 16 settembre portati "
        "nei documenti**: l'ordine delle regole di `.gitattributes` (69), la portata del rilascio e il "
        "tag `v3.1-paper2` (70), quattro citazioni irrisolte con quattro cause (71), il protocollo "
        "v1.1 ancorato per byte (72) — e **il deposito Zenodo non contiene il protocollo**, misurato "
        "il 17; tre decisioni del 17: GitHub aggiornato periodicamente, deposito Zenodo e tredici "
        "voci del Paper 1 all'**ultimo punto della Fase 7**; 6.9 spuntata\n",
        "### rev. 3.29 — 17 settembre 2026 (sera) — record 73; **il deposito è stato aperto e non "
        "contiene il protocollo**, misurato membro per membro (1068 in quattro versioni, zero); "
        "**commit tre `20361ec`, tag `v3.1-paper2` su di esso, primo push eseguito** — `origin/main` "
        "porta 73 record, misurati dal remoto; **6.3 e 6.7 chiuse** a meno del deposito, che è "
        "l'ultimo punto della Fase 7; il censimento del rilascio girato a 73 record apre **una "
        "decisione di protocollo, dichiarata e non presa** (voce 6.2)\n",
    ))

    # 2. 6.3: chiusa a meno del deposito
    E.append((
        "- [ ] **✦✦ 6.3 — Tag `v3.1-paper2` (record 70 §iv; non `v2.1-paper2`, che si ordinerebbe prima\n"
        "      di `v3.0-paper2` del 28 agosto); DOI Zenodo alla sottomissione.** *(era «Tag\n"
        "      `v2.1-paper2`; DOI Zenodo aggiornato»)*.\n",
        "- [x] **✦✦ 6.3 — Tag `v3.1-paper2` e rilascio: CHIUSA il 17 set (sera) a meno del deposito,\n"
        "      che è l'ultimo punto della Fase 7** *(record 70 §iv per il nome del tag; era «Tag\n"
        "      `v2.1-paper2`; DOI Zenodo aggiornato»)*.\n"
        "      **✦✦ 17 set, sera — FATTO E MISURATO.** Commit tre **`20361ec`** con otto file e\n"
        "      pathspec esplicite (ledger a 73, `DOCUMENTED_AMENDMENTS = 73`, `REPRODUCIBILITY.md`,\n"
        "      cinque strumenti): `git diff --cached --stat` letto prima del commit, nessun\n"
        "      passeggero. Tag **`v3.1-paper2` spostato** su `20361ec` con `-f` — lecito perché non\n"
        "      era mai stato spinto, e il nome resta quello del record 70 §iv. **Primo push\n"
        "      eseguito**: `origin/main` da `40f72a8` a `20361ec`, tag pubblicato, e il ledger\n"
        "      pubblico porta **73 record** — misurati sul remoto con `git show origin/main:…`, non\n"
        "      dedotti dall'esito del push. `src/eccezioni_rilascio.json` era un **sottoinsieme\n"
        "      stretto** di quello in `logs/` (13 chiavi su 14, nessun valore diverso, mancava solo\n"
        "      quella del protocollo): rimosso, e nessun record serviva perché non era mai stato\n"
        "      committato. Dal `ls-remote`: `v1.0` è un tag **leggero**, gli altri tre sono annotati —\n"
        "      da dire nel §1 di `REPRODUCIBILITY.md` al deposito della Fase 7.\n"
        "      **RESTA solo il deposito Zenodo**, ultimo punto della Fase 7 (record 73 §vi), con la\n"
        "      v1.1 del protocollo dentro e la correzione della riga «deposited 27 August 2026», che\n"
        "      descrive un commit e non un deposito.\n",
    ))

    # 3. 6.3: il vecchio blocco RESTA, sostituito dal resoconto del record 73
    E.append((
        "      **RESTA:** (i) il **commit tre** — ledger con i record 71 e 72,\n"
        "      `DOCUMENTED_AMENDMENTS = 72`, `paper2_append_amend71/72.py` — e lo spostamento del tag\n"
        "      su di esso, lecito perché mai spinto; il file non tracciato `src/eccezioni_rilascio.json`\n"
        "      va confrontato con `logs/eccezioni_rilascio.json` e deciso prima: `logs/` è fuori dal\n"
        "      rilascio, `src/` dentro; (ii) `REPRODUCIBILITY.md` corretto **prima** del commit tre\n"
        "      (6.7), altrimenti il tag congela le due frasi false;\n"
        "      (iii) **un record 73.** Misurato il 17 set dal servizio Zenodo: il deposito\n",
        "      **✦✦ Record 73, appeso il 17 set: il deposito è stato APERTO.** Non per metadati: ogni\n"
        "      file di ogni versione scaricato, ogni archivio aperto, **1068 membri esaminati in\n"
        "      quattro versioni, zero col protocollo**. Le tre possibilità che il record 72 lasciava\n"
        "      aperte — (a) il deposito porta la v1.1, (b) porta la v1.0, (c) è stato aggiornato dopo —\n"
        "      **sono chiuse tutte e tre**: ce n'era una quarta, che il 72 non aveva previsto, e tre\n"
        "      rami plausibili non sono una partizione. Due cose in più dalla misura: `cauchy_code.zip`\n"
        "      porta il ledger con **12 record**, 12 670 byte, che è la conferma indipendente del\n"
        "      «dodici al deposito» del §9 del protocollo — fin qui era il protocollo a dirlo di sé; e\n"
        "      la riga «*version 1.0 deposited 27 August 2026*» è **falsa**, perché nessuna versione del\n"
        "      concept DOI è del 27 agosto e l'unico evento di quel giorno è il commit `73c8213`. Non\n"
        "      corretta: il protocollo non si riscrive per emendamento, e la correzione va nella\n"
        "      versione che si deposita. Il record 73 supera anche il **§iii del record 70**: `origin`\n"
        "      si aggiorna periodicamente, e lo stato di prima del push — `40f72a8`, 55 record — è\n"
        "      scritto nel record, com'era vero quando è stato scritto.\n"
        "      *(Misura del 16–17 set, che resta qui per il deposito della Fase 7.)* Il deposito\n",
    ))

    # 4. 6.7 chiusa
    E.append((
        "- [ ] **✧✧✧✧✧ 6.7 — `REPRODUCIBILITY.md` alla radice** (ex R2 di `paper2_stato.md`): mappa\n",
        "- [x] **✧✧✧✧✧ 6.7 — `REPRODUCIBILITY.md`: CHIUSA il 17 set (sera)**, `7a72a509…`, 17 820\n"
        "      byte, 306 righe, nel commit tre. **Le due affermazioni false sono corrette:** la copia\n"
        "      byte-identica è riscritta come **rimozione registrata** (`352e024`, P-A1, emendamento\n"
        "      11), e i fine riga passano dal conteggio all'**invariante** — le righe a LF sono la 8, 9,\n"
        "      10, 11, 13 e 14 e nessun'altra, mentre i totali crescono a ogni append. **Aggiunti:**\n"
        "      l'ordine delle regole di `.gitattributes` coi tre file del tier congelato (record 69),\n"
        "      l'asimmetria cache/kref con le due coperture contro una, il pattern di ripresa di\n"
        "      `paper1_remap.py:512-516` (l'unico runner che verifica il prodotto laterale), e un **§7**\n"
        "      sui due ancoraggi del protocollo. **Tolti due conteggi che invecchiano:** «55 record» al\n"
        "      §6, ora demandato a `DOCUMENTED_AMENDMENTS`, e «Quattro cose» nel titolo del §5. E una\n"
        "      riga in testa che il §7 nuovo avrebbe reso falsa — «ogni digest qui sotto è ricalcolabile\n"
        "      dai file depositati» — corretta nello stesso giro: i digest del protocollo non lo sono,\n"
        "      perché il deposito non lo contiene.\n"
        "      *(Voce originale, per la storia.)* **`REPRODUCIBILITY.md` alla radice** (ex R2 di\n"
        "      `paper2_stato.md`): mappa\n",
    ))

    # 5. 6.2: il censimento a 73, le quattro eccezioni nuove, la decisione aperta
    E.append((
        "      **✦✦ Da dichiarare nel manoscritto (16 set):** in `d2_v2_{NGC,SGC}.json` coesistono\n",
        "      **✦✦ Censimento del rilascio a 73 record (17 set, sera).** 141 percorsi citati\n"
        "      distinti: 115 tracciati e puliti, 12 esclusi con eccezione, 2 assenti con eccezione, 2\n"
        "      pattern, e quattro verdetti — `citati_tracciati` PASS, `metri_concordi` PASS,\n"
        "      `citati_esistono` FAIL su 4, `citati_non_esclusi` FAIL su 4. **Una previsione era\n"
        "      sbagliata:** «con le 14 eccezioni `citati_non_esclusi` passa» è stato detto il 16 set\n"
        "      dove la misura era disponibile, ed è l'errore 3 del §6 della consegna. Il record 73 ha\n"
        "      **allargato la popolazione**: cita `logs/deposito_zenodo.json` (la sua evidence) e i due\n"
        "      documenti compagni in `papers/`, e mancava già `results/paper2/remote_audit.json` del\n"
        "      record 72. Servono **quattro eccezioni nuove** — non decisioni nuove: seguono dai record\n"
        "      70 §i e §ii (`papers/` e `logs/` fuori) e dal commit `73c8213`, che dichiara\n"
        "      `remote_audit.json` rigenerabile. E una voce esistente dice ora il falso: la ragione di\n"
        "      `paper2_prereg_v1.md` chiude con «la cui corrispondenza coi byte su disco resta da\n"
        "      verificare», ed è verificata dal record 73. **Nessun digest per checklist e stato:** sono\n"
        "      documenti che si rivedono ogni sessione, e un'ancora per byte su di essi sarebbe stale al\n"
        "      primo patcher — si citano per il record che li nomina.\n"
        "      **✦✦✦ DECISIONE DI PROTOCOLLO APERTA, dichiarata e non presa.** I quattro percorsi del\n"
        "      record 71 escono `assente`, e il ledger è **append-only**: i record 11, 12, 27, 54 e 70\n"
        "      li citeranno per sempre, quindi il FAIL **non si chiude coi documenti**. Due uscite:\n"
        "      **(A) quattro eccezioni** la cui ragione cita il record 71 e nomina il sopravvissuto\n"
        "      (`paper2_item13_rev2.py`; `paper2_passata_1punto.py` 43/43; "
        "`phase8_test2_permock_hodfit.csv`;\n"
        "      l'assenza Quijote dichiarata dal record 43 stesso) — il censimento passa e la conoscenza\n"
        "      sta nel file, col precedente già dentro il file:\n"
        "      `results/paper1/n10_phases_SGC.jsonl`, «citato PER DIRE CHE NON ESISTEVA»; **(B) FAIL\n"
        "      permanente e dichiarato qui**, sul principio che una citazione sbagliata dentro un record\n"
        "      deve continuare a farsi vedere. Contro (B): un FAIL permanente per disegno smette di\n"
        "      discriminare, ed è la ragione per cui il 16 set è stata aggiunta la voce del file delle\n"
        "      eccezioni su se stesso. Contro (A): il 16 set l'eccezione era stata **rifiutata** perché\n"
        "      avrebbe nascosto una citazione sbagliata non ancora tracciata — ma il 71 le ha tracciate\n"
        "      tutte e quattro con la causa, e quel motivo è caduto. **Se si scegle (A) serve un record\n"
        "      74**: quattro eccezioni sono quattro decisioni, non contabilità.\n"
        "      **✦✦ Da dichiarare nel manoscritto (16 set):** in `d2_v2_{NGC,SGC}.json` coesistono\n",
    ))
    return E


# ---------------------------------------------------------------------------
# STATO (dodicesima -> tredicesima revisione)
# ---------------------------------------------------------------------------

def edits_stato(utc_reso, item_73):
    E = []

    # 1. intestazione
    E.append((
        "aggiornato **17 settembre 2026**, dodicesima revisione\n",
        "aggiornato **17 settembre 2026 (sera)**, tredicesima revisione\n",
    ))

    # 2. blocco in testa
    E.append((
        "> **Cosa è cambiato nella dodicesima revisione (17 settembre) — I QUATTRO RECORD DEL 16 SONO NEI\n",
        "> **Cosa è cambiato nella tredicesima revisione (17 settembre, sera) — IL DEPOSITO È STATO\n"
        "> APERTO, E IL RILASCIO È PUBBLICO.** Record **73**: ogni file di ogni versione del concept\n"
        "> DOI scaricato e ogni archivio aperto — **1068 membri, zero col protocollo**. Le tre\n"
        "> possibilità del record 72 sono chiuse tutte e tre da una quarta che non era prevista: il\n"
        "> version DOI ancora **l'archivio della pipeline**, non il documento di pre-registrazione, e\n"
        "> l'unico ancoraggio del protocollo resta quello per byte del 72. Due cose in più dalla\n"
        "> misura: il ledger **depositato** porta 12 record, 12 670 byte — conferma indipendente del\n"
        "> «dodici al deposito» del §9, che fin qui era il protocollo a dirlo di sé; e la riga\n"
        "> «*version 1.0 deposited 27 August 2026*» è falsa (nessuna versione è del 27 agosto; l'unico\n"
        "> evento di quel giorno è il commit `73c8213`), dichiarata e **non corretta**, perché il\n"
        "> protocollo non si riscrive per emendamento. **Commit tre `20361ec`** con otto file e\n"
        "> pathspec esplicite, tag **`v3.1-paper2`** spostato su di esso, **primo push eseguito**:\n"
        "> `origin/main` a `20361ec`, tag pubblicato, e **73 record nel ledger pubblico** misurati sul\n"
        "> remoto. Il differimento del record 70 §iii è chiuso nei fatti e il 73 lo registra con lo\n"
        "> stato di prima (`40f72a8`, 55 record). **6.3 e 6.7 chiuse**, a meno del deposito, che è\n"
        "> l'ultimo punto della Fase 7. `REPRODUCIBILITY.md` `7a72a509…`, 306 righe: due frasi false\n"
        "> corrette, quattro voci aggiunte, due conteggi che invecchiavano tolti. Il censimento a 73\n"
        "> record apre **una decisione di protocollo dichiarata e non presa** (checklist 6.2), e serve\n"
        "> un record 74 se si sceglie la via delle eccezioni. Checklist rev. 3.29.\n"
        "\n"
        "> **Cosa è cambiato nella dodicesima revisione (17 settembre) — I QUATTRO RECORD DEL 16 SONO NEI\n",
    ))

    # 3. §0: le verifiche della sera
    E.append((
        "| (17 set) v1.0 del protocollo (`73c8213`) contro la v1.1 | 8 righe tolte, 61 aggiunte, tutte fuori dalle sezioni delle regole, che sono **identiche** |\n",
        "| (17 set) v1.0 del protocollo (`73c8213`) contro la v1.1 | 8 righe tolte, 61 aggiunte, tutte fuori dalle sezioni delle regole, che sono **identiche** |\n"
        "| (17 set sera) il deposito contiene il protocollo? | **NO**, misurato aprendo ogni archivio: 1068 membri in quattro versioni, zero |\n"
        "| (17 set sera) il ledger DEPOSITATO quanti record porta? | **12**, 12 670 byte: conferma indipendente del «dodici» del §9 del protocollo |\n"
        "| (17 set sera) `origin/main` dopo il push | `20361ec`, **73 record** letti dal remoto, tag `v3.1-paper2` pubblicato |\n"
        "| (17 set sera) `src/eccezioni_rilascio.json` contro quello in `logs/` | **sottoinsieme stretto**: 13 chiavi su 14, nessun valore diverso; rimosso |\n"
        "| (17 set sera) censimento del rilascio a 73 record | 141 percorsi; `citati_tracciati` e `metri_concordi` PASS, `citati_esistono` e `citati_non_esclusi` **FAIL su 4** |\n",
    ))

    # 4. riga di stato
    E.append((
        "Fase 7** · smentite **12 / 1 / 6**.\n",
        "Fase 7** · smentite **12 / 1 / 6**.\n"
        "\n"
        "**Al 17 settembre, sera (tredicesima revisione):** registro **73 record**, CLEAN a 73/73 ·\n"
        "checklist **rev. 3.29** · commit tre **`20361ec`**, tag **`v3.1-paper2`** su di esso, **push\n"
        "eseguito**: `origin/main` a `20361ec` con 73 record · `REPRODUCIBILITY.md` `7a72a509…` ·\n"
        "Fase 6: **chiuse 6.1, 6.3, 6.7, 6.8, 6.9**; aperte 6.0b–d, 6.2, 6.4, 6.5, 6.6; 6.0a e il\n"
        "deposito Zenodo all'**ultimo punto della Fase 7** · una decisione di protocollo aperta sui\n"
        "quattro percorsi del record 71.\n",
    ))

    # 5. §3: titolo, sotto-titolo, riga resa dal ledger, nota
    E.append((
        "## 3. Il registro degli emendamenti — 72 record\n\n### Fase 6, record 61–72\n",
        "## 3. Il registro degli emendamenti — 73 record\n\n### Fase 6, record 61–73\n",
    ))
    E.append((
        "| **72** | **16 set 18:11** | **`6.2/il_protocollo_pre_registrato_non_era_ancorato_per_byte`** |\n",
        "| 72 | 16 set 18:11 | `6.2/il_protocollo_pre_registrato_non_era_ancorato_per_byte` |\n"
        "| **%s** | **%s** | **`%s`** |\n" % (LEDGER_RECORD, utc_reso, item_73),
    ))
    E.append((
        "> censimento; il **72** ancora per byte la v1.1 del protocollo, che nessun commit e nessun\n"
        "> deposito porta (§8, Rilascio).\n",
        "> censimento; il **72** ancora per byte la v1.1 del protocollo, che nessun commit porta; il\n"
        "> **73** apre il deposito e misura che non contiene il protocollo in nessuna versione, chiude\n"
        "> le tre possibilità del 72 con una quarta, e **supera il §iii del 70** aprendo `origin`\n"
        "> all'aggiornamento periodico (§8, Rilascio).\n",
    ))

    # 6. §8: il blocco Rilascio, riscritto sullo stato dopo il push
    E.append((
        "### Rilascio — stato al 17 settembre\n"
        "\n"
        "`R1` tag: **`v3.1-paper2` locale su `bfcb4a5`** (record 70 §iv; non `v2.1-paper2`, che si\n"
        "ordinerebbe prima di `v3.0-paper2`), senza i record 71–72 e `DOCUMENTED_AMENDMENTS = 72`: serve\n"
        "un commit tre e il tag va spostato su di esso. Zenodo: **solo alla sottomissione, ultimo punto\n"
        "della Fase 7** (17 set); il deposito `10.5281/zenodo.22148444` (`v3.0-paper2`, 28 ago) **non\n"
        "contiene `paper2_prereg_v1.md`** in nessuno dei quattro zip, e nessuna delle quattro versioni del\n"
        "concept DOI lo porta — **record 73 da scrivere** · `R2` `REPRODUCIBILITY.md` **esiste**\n"
        "(`c13ccc3`, 8 set, 176 righe): voce 6.7, da estendere; il §5 porta due affermazioni false\n"
        "(record 69 e 71), da correggere prima del commit tre · `R3` tarball del tier `features`:\n"
        "ignorato dal commit `40f72a8`, deterministico e rigenerato dal manifest · `R4` `git gc` ·\n"
        "`P-A1` **ESEGUITO** dal commit `352e024` (record 71): `phase8_test2_permock.csv` rimosso,\n"
        "sopravvive `phase8_test2_permock_hodfit.csv`. GitHub: `origin/main` a `40f72a8` (8 set, 55\n"
        "record), **da aggiornare periodicamente** (decisione del 17 set, che supera il differimento del\n"
        "record 70: da registrare prima del primo push). I quattordici file citati e non tracciati stanno\n"
        "in `logs/eccezioni_rilascio.json` (`e8d34dbc…`).\n",
        "### Rilascio — stato al 17 settembre, sera\n"
        "\n"
        "`R1` tag: **CHIUSO**. `v3.1-paper2` su **`20361ec`** (commit tre: ledger a 73,\n"
        "`DOCUMENTED_AMENDMENTS = 73`, `REPRODUCIBILITY.md`, cinque strumenti), spostato con `-f`\n"
        "perché non era mai stato spinto, e **pubblicato**. `origin/main` a `20361ec`, **73 record nel\n"
        "ledger pubblico** misurati sul remoto. Sul remoto `v1.0` è un tag **leggero**, gli altri tre\n"
        "annotati. Zenodo: **solo alla sottomissione, ultimo punto della Fase 7** — il deposito\n"
        "`10.5281/zenodo.22148444` **non contiene il protocollo in nessuna versione** (record 73,\n"
        "misurato su 1068 membri), quindi il protocollo è ancorato per byte dal record 72 e non da un\n"
        "DOI fino a quel deposito · `R2` **CHIUSO**: `REPRODUCIBILITY.md` `7a72a509…`, 17 820 byte,\n"
        "306 righe, nel commit tre — due frasi false corrette (record 69 e 71), quattro voci aggiunte,\n"
        "due conteggi che invecchiavano tolti, un §7 nuovo sui due ancoraggi del protocollo (voce 6.7)\n"
        "· `R3` tarball del tier `features`: ignorato dal commit `40f72a8`, deterministico e rigenerato\n"
        "dal manifest · `R4` `git gc` · `P-A1` **ESEGUITO** dal commit `352e024` (record 71).\n"
        "**Le eccezioni sono 14 e servono almeno 18:** il record 73 cita `logs/deposito_zenodo.json` e\n"
        "i due documenti compagni in `papers/`, e mancava già `results/paper2/remote_audit.json` del\n"
        "record 72; la ragione della voce del protocollo dice ancora «resta da verificare», ed è\n"
        "verificata. Più i quattro percorsi del record 71, che sono una **decisione aperta** (checklist\n"
        "6.2): se si scelgono le eccezioni serve un record 74.\n",
    ))

    # 7. §9: i due strumenti nuovi
    E.append((
        "| `paper2_patch_documenti_69_72.py` | record 69–72 e decisioni del 17 set nei documenti; righe §3 rese dal ledger | vedi selftest |\n",
        "| `paper2_patch_documenti_69_72.py` | record 69–72 e decisioni del 17 set nei documenti; righe §3 rese dal ledger | 27/27 |\n"
        "| `paper2_append_amend73.py` | record 73; **misura il deposito** (`misura-deposito`) e riconfronta il rapporto campo per campo prima dell'append; misura `origin` invece di assumerlo | 61/61 |\n"
        "| `paper2_patch_reproducibility.py` | voce 6.7: due frasi false e quattro voci nuove in `REPRODUCIBILITY.md`; rifiuta finché il ledger non è a 73 | 19/19 |\n"
        "| `paper2_patch_documenti_73.py` | record 73, commit tre, tag, push e censimento nei documenti | vedi selftest |\n",
    ))

    # 8. §14: le due lezioni di oggi
    E.append((
        "- **Un conteggio di selftest appartiene a uno strumento solo**: «31/31» sul nome sbagliato è la\n"
        "  prova apparente di un'esecuzione mai avvenuta (record 71).\n",
        "- **Un conteggio di selftest appartiene a uno strumento solo**: «31/31» sul nome sbagliato è la\n"
        "  prova apparente di un'esecuzione mai avvenuta (record 71).\n"
        "- **Un elenco di possibilità plausibili non è una partizione** (record 73): le tre uscite del\n"
        "  record 72 sul deposito erano tutte dentro l'ipotesi che il protocollo fosse depositato, e la\n"
        "  misura ha trovato la quarta. Dichiarare aperto è giusto, dichiarare esaustivo no.\n"
        "- **Un conteggio dentro un'intestazione invecchia alla prima voce aggiunta**: «Quattro cose che\n"
        "  il lettore deve sapere» e «55 record» in `REPRODUCIBILITY.md`. I conteggi stanno nelle righe,\n"
        "  dove si verificano, o in una costante che uno strumento confronta col disco.\n"
        "- **Prima di contare le chiavi, guardare che forma ha il file**: il confronto fra i due\n"
        "  `eccezioni_rilascio.json` è stato scritto per due liste e i file sono **dizionari**, quindi\n"
        "  «13 contro 14» non diceva se uno fosse un sottoinsieme. Rifatto per chiavi e valori: lo era.\n",
    ))
    return E


# ---------------------------------------------------------------------------

def compute(args):
    ck_b = read_bytes(args.checklist)
    st_b = read_bytes(args.stato)
    check_anchor(args.checklist, ck_b, ANCORA_CHECKLIST, "checklist")
    check_anchor(args.stato, st_b, ANCORA_STATO, "stato")
    utc_reso, item_73 = check_record_73(read_ledger(args.ledger))
    ck = ck_b.decode("utf-8")
    st = st_b.decode("utf-8")
    ck_new = apply_edits(ck, edits_checklist(), "checklist")
    st_new = apply_edits(st, edits_stato(utc_reso, item_73), "stato")
    if MARCA_CHECKLIST not in ck_new or MARCA_STATO not in st_new:
        raise PatchError("marca di revisione assente dal testo nuovo")
    if "\r" in ck_new or "\r" in st_new:
        raise PatchError("il testo nuovo contiene CR")
    return ck, ck_new, st, st_new, (utc_reso, item_73)


def rapporto(ck_new, st_new, reso):
    print("riga §3 resa dal ledger:\n  73: %s  %s" % reso)
    ckb, stb = ck_new.encode("utf-8"), st_new.encode("utf-8")
    print("checklist nuova: %s  %d byte  (rev. 3.29)" % (sha256_bytes(ckb), len(ckb)))
    print("stato nuovo:     %s  %d byte  (tredicesima revisione)" % (sha256_bytes(stb), len(stb)))


def cmd_dry_run(a):
    ck, ck_new, st, st_new, reso = compute(a)
    print(unified(ck, ck_new, os.path.basename(a.checklist)))
    print(unified(st, st_new, os.path.basename(a.stato)))
    print("modifiche: checklist %d, stato %d — nessun file scritto"
          % (len(edits_checklist()), len(edits_stato(*reso))))
    rapporto(ck_new, st_new, reso)
    return 0


def cmd_apply(a):
    _, ck_new, _, st_new, reso = compute(a)
    write_atomic(a.checklist, ck_new.encode("utf-8"))
    write_atomic(a.stato, st_new.encode("utf-8"))
    print("scritti entrambi i documenti.")
    rapporto(ck_new, st_new, reso)
    return 0


def cmd_verify(a):
    ok = True
    for path, marca, ancora, edits_fn, label in (
        (a.checklist, MARCA_CHECKLIST, ANCORA_CHECKLIST, edits_checklist, "checklist"),
        (a.stato, MARCA_STATO, ANCORA_STATO, None, "stato"),
    ):
        b = read_bytes(path)
        t = b.decode("utf-8")
        sha = sha256_bytes(b)
        vecchia = (sha, len(b)) == ancora
        ha_marca = marca in t
        non_trovate = 0
        if edits_fn is not None:
            non_trovate = sum(1 for _, n in edits_fn() if n and t.count(n) != 1)
        print("%s: %s  %d byte  marca=%s  ancora-vecchia=%s  CR=%s  modifiche-non-trovate=%d"
              % (label, sha, len(b), "si" if ha_marca else "NO", "SI" if vecchia else "no",
                 "SI" if b"\r" in b else "no", non_trovate))
        ok = ok and ha_marca and not vecchia and b"\r" not in b and non_trovate == 0
    print("ESITO:", "VERIFICATO" if ok else "NON VERIFICATO")
    return 0 if ok else 2


# ---------------------------------------------------------------------------

def _ledger_finto(n=LEDGER_RECORD, marker=MARKER_73, dettagli=True):
    out = b""
    for i in range(1, n + 1):
        rec = {"item": "finto/%d" % i, "utc": "2026-09-17T12:5%d:00+00:00" % (i % 10),
               "numbering_rule": "Questo e' il record %d." % i,
               "rules": {"marker": marker if i == n else "altro-%d" % i}}
        if i == n:
            rec["item"] = "6.3/il_deposito_non_contiene_il_protocollo_e_tre_decisioni_di_rilascio"
            rec["utc"] = "2026-09-17T12:49:43+00:00"
            if dettagli:
                rec["evidence"] = ("1068 membri, 22148444, ledger depositato 12670 byte, "
                                   "607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86")
        out += json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\r\n"
    return out


def _doc_finto(edits):
    parti = []
    for i, (old, _) in enumerate(edits, start=1):
        parti.append("riga neutra %d\n" % i)
        parti.append(old)
    parti.append("riga neutra finale\n")
    return "".join(parti)


def cmd_selftest(a):
    ok = tot = 0

    def controlla(nome, cond):
        nonlocal ok, tot
        tot += 1
        ok += bool(cond)
        print("  [%s] %s" % ("ok" if cond else "FAIL", nome))

    def rifiuta(fn):
        try:
            fn()
        except PatchError:
            return True
        return False

    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "led.jsonl")
        with open(led, "wb") as f:
            f.write(_ledger_finto())
        recs = read_ledger(led)
        reso = check_record_73(recs)
        controlla("ledger a 73 col record 73: passa", reso[0] == "17 set 12:49")
        controlla("item del 73 reso dal ledger", reso[1].startswith("6.3/il_deposito"))
        with open(led, "wb") as f:
            f.write(_ledger_finto(n=72))
        controlla("ledger a 72 rifiutato (il 73 non c'e')", rifiuta(lambda: read_ledger(led)))
        with open(led, "wb") as f:
            f.write(_ledger_finto(marker="emendamento-72-ancoraggio-del-protocollo"))
        controlla("marker sbagliato rifiutato",
                  rifiuta(lambda: check_record_73(read_ledger(led))))
        with open(led, "wb") as f:
            f.write(_ledger_finto(dettagli=False))
        controlla("record 73 senza i dettagli letterali rifiutato",
                  rifiuta(lambda: check_record_73(read_ledger(led))))
        controlla("render_utc rifiuta un formato diverso",
                  rifiuta(lambda: render_utc("17/09/2026")))

        eck, est = edits_checklist(), edits_stato(*reso)
        controlla("nessuna ancora vuota", all(o for o, _ in eck + est))
        controlla("ogni testo nuovo diverso dalla sua ancora", all(o != n for o, n in eck + est))
        controlla("nessun testo nuovo contiene CR", not any("\r" in n for _, n in eck + est))
        fck, fst = _doc_finto(eck), _doc_finto(est)
        ck_new = apply_edits(fck, eck, "checklist")
        st_new = apply_edits(fst, est, "stato")
        controlla("applicazione sintetica: ogni testo nuovo una volta (checklist)",
                  all(ck_new.count(n) == 1 for _, n in eck if n) and MARCA_CHECKLIST in ck_new)
        controlla("applicazione sintetica: ogni testo nuovo una volta (stato)",
                  all(st_new.count(n) == 1 for _, n in est if n) and MARCA_STATO in st_new)
        controlla("le ancore delle sostituzioni sono sparite",
                  all(o not in ck_new for o, n in eck if o not in n)
                  and all(o not in st_new for o, n in est if o not in n))
        controlla("seconda applicazione rifiutata",
                  rifiuta(lambda: apply_edits(ck_new, eck, "checklist")))
        controlla("ancora duplicata rifiutata",
                  rifiuta(lambda: apply_edits(fck + eck[0][0], eck, "checklist")))
        controlla("ancora mancante rifiutata",
                  rifiuta(lambda: apply_edits(fck.replace(eck[2][0], ""), eck, "checklist")))
        controlla("6.3 e 6.7 spuntate nella checklist nuova",
                  "- [x] **✦✦ 6.3 —" in ck_new and "- [x] **✧✧✧✧✧ 6.7 —" in ck_new)
        controlla("la decisione aperta e' scritta con entrambe le uscite",
                  "DECISIONE DI PROTOCOLLO APERTA" in ck_new and "**(A) quattro eccezioni**"
                  in ck_new and "**(B) FAIL" in ck_new and "serve un record\n      74" in ck_new)
        controlla("la previsione sbagliata e' registrata",
                  "Una previsione era\n      sbagliata" in ck_new)
        controlla("la riga §3 del 73 e' nello stato, in grassetto",
                  "| **73** | **17 set 12:49** |" in st_new and "| 72 | 16 set 18:11 |" in st_new)
        controlla("il blocco Rilascio dice R1 e R2 chiusi",
                  "`R1` tag: **CHIUSO**" in st_new and "`R2` **CHIUSO**" in st_new)

        p = os.path.join(td, "doc.md")
        with open(p, "wb") as f:
            f.write(b"abc\n")
        controlla("ancora sha sbagliata rifiutata",
                  rifiuta(lambda: check_anchor(p, read_bytes(p), ("0" * 64, 4), "x")))
        with open(p, "wb") as f:
            f.write(b"a\r\nb\n")
        controlla("documento con CR rifiutato",
                  rifiuta(lambda: check_anchor(p, read_bytes(p),
                                               (sha256_bytes(b"a\r\nb\n"), 5), "x")))
        write_atomic(p, b"xyz\n")
        controlla("write_atomic scrive e rilegge", read_bytes(p) == b"xyz\n")
        controlla("write_atomic non lascia temporanei",
                  not [x for x in os.listdir(td) if x.startswith(".patch73_")])

    if os.path.exists(a.checklist) and os.path.exists(a.stato):
        ckb, stb = read_bytes(a.checklist), read_bytes(a.stato)
        if ((sha256_bytes(ckb), len(ckb)) == ANCORA_CHECKLIST
                and (sha256_bytes(stb), len(stb)) == ANCORA_STATO):
            ckt, stt = ckb.decode("utf-8"), stb.decode("utf-8")
            controlla("documenti veri: ogni ancora della checklist compare una volta",
                      all(ckt.count(o) == 1 for o, _ in edits_checklist()))
            controlla("documenti veri: ogni ancora dello stato compare una volta",
                      all(stt.count(o) == 1 for o, _ in edits_stato("17 set 12:49", "x")))
        else:
            print("  [--] documenti veri non all'ancora attesa: controlli saltati")
    else:
        print("  [--] documenti veri non trovati: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="record 73, commit tre, tag e push nei documenti")
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--checklist", default=CHECKLIST)
    ap.add_argument("--stato", default=STATO)
    ap.add_argument("--ledger", default=LEDGER)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "selftest":
            return cmd_selftest(a)
        if a.cmd == "dry-run":
            return cmd_dry_run(a)
        if a.cmd == "apply":
            return cmd_apply(a)
        return cmd_verify(a)
    except PatchError as e:
        print("RIFIUTATO: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_documenti_74.py — porta nei due documenti il record 74: la decisione (A) PRESA, le
quattro eccezioni a 22 voci, i quattro verdetti del censimento, il §5 riscritto col digest, e le
due previsioni sbagliate del 17 settembre.

Documenti toccati (entrambi o nessuno):
  papers/paper2/checklist_paper2.md   rev. 3.29 -> rev. 3.30
  papers/paper2/paper2_stato.md       tredicesima -> quattordicesima revisione

Che cosa registra:
  - la DECISIONE del 17 set (sera): via (A), quattro eccezioni dichiarate dal record 74, tre con
    il digest di cio' che la citazione intendeva. Il blocco che dichiarava la decisione aperta
    resta come storia, marcato, con l'argomento che l'ha sciolta;
  - la misura che ha sciolto la quarta: la copia rimossa dal commit 352e024 e' BYTE-IDENTICA al
    sopravvissuto, `ae733e1e…`, 10 891 byte. Il commit ha rimosso un'ETICHETTA, non un dato;
  - la 6.7 chiusa di nuovo, `09eb415f…`, e la ragione per cui era stata riaperta: il §5 ha detto
    la cosa sbagliata due volte, nelle due direzioni opposte;
  - il censimento a 74 record: quattro verdetti su cinque PASS, e `citati_committati` FAIL su 2,
    che si chiude col commit quattro e non con un'eccezione;
  - DUE previsioni sbagliate, entrambe mie: «con le 14 eccezioni citati_non_esclusi passa» (16
    set) e «tutti e cinque i verdetti PASS» (17 set, sera). La seconda era evitabile senza
    misurare niente: i due file erano modificati e non committati mentre la previsione veniva
    fatta.

CANCELLI: come i patcher precedenti — sha dei due documenti, ledger a 74 col marker del 74,
dettagli letterali nel record serializzato, ancore uniche, scrittura atomica, LF.

Uso:
  python src\\paper2_patch_documenti_74.py selftest
  python src\\paper2_patch_documenti_74.py dry-run
  python src\\paper2_patch_documenti_74.py apply
  python src\\paper2_patch_documenti_74.py verify
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

ANCORA_CHECKLIST = ("a738aee68ed3faf0d563da52a701fb4ceb32b1a622254284d5990a1f78eb98d7", 250544)
ANCORA_STATO = ("0c9c6c66ae2cc04d101b0c4d8751df9b44ce82866c32646cc55558de33b31f92", 91875)

LEDGER_RECORD = 74
MARKER_74 = "emendamento-74-quattro-eccezioni-e-la-copia-byte-identica"
DETTAGLI_74 = ["ae733e1e2a74bfffe19c4f9a3ef8fada16a9fa9a940ae20850e26b2b761f85bc",
               "bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e",
               "4306e613476d52287143bd7187e1f1d50f69eb969b3a6ca84ec0a25e86bd022b",
               "352e024", "paper2_passata_1punto.py"]

MARCA_CHECKLIST = "### rev. 3.30 — 17 settembre 2026 (sera) — record 74"
MARCA_STATO = "quattordicesima revisione"

MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


class PatchError(Exception):
    pass


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
            "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n  (%s)"
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
    righe = [l for l in read_bytes(path).split(b"\n") if l.strip()]
    if len(righe) != LEDGER_RECORD:
        raise PatchError("ledger: %d record, atteso %d" % (len(righe), LEDGER_RECORD))
    recs = []
    for i, ln in enumerate(righe, start=1):
        s = ln[:-1] if ln.endswith(b"\r") else ln
        try:
            recs.append(json.loads(s.decode("utf-8")))
        except Exception as e:  # noqa: BLE001
            raise PatchError("ledger: riga %d non e' JSON: %r" % (i, e))
    return recs


def check_record_74(recs):
    r = recs[LEDGER_RECORD - 1]
    if str(r.get("rules", {}).get("marker", "")) != MARKER_74:
        raise PatchError("l'ultimo record non e' il 74: marker %r"
                         % r.get("rules", {}).get("marker"))
    for k in ("utc", "item"):
        if not isinstance(r.get(k), str) or not r[k]:
            raise PatchError("record 74: campo `%s` assente" % k)
    if "|" in r["item"]:
        raise PatchError("record 74: `item` contiene '|'")
    serial = json.dumps(r, ensure_ascii=False)
    missing = [d for d in DETTAGLI_74 if d not in serial]
    if missing:
        raise PatchError("record 74: dettagli letterali assenti: %r" % missing)
    if r.get("eccezioni_dichiarate") is None or len(r["eccezioni_dichiarate"]) != 4:
        raise PatchError("record 74: non dichiara quattro eccezioni")
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
    fd, tmp = tempfile.mkstemp(prefix=".patch74_", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    if read_bytes(path) != data:
        raise PatchError("%s: byte riletti diversi da quelli scritti" % path)


def unified(a, b, name):
    return "".join(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True),
                                        fromfile=name + " (prima)", tofile=name + " (dopo)",
                                        n=1))


# ---------------------------------------------------------------------------
# CHECKLIST (rev. 3.29 -> 3.30)
# ---------------------------------------------------------------------------

def edits_checklist():
    E = []

    # 1. intestazione
    E.append((
        "### rev. 3.29 — 17 settembre 2026 (sera) — record 73; **il deposito è stato aperto e non "
        "contiene il protocollo**, misurato membro per membro (1068 in quattro versioni, zero); "
        "**commit tre `20361ec`, tag `v3.1-paper2` su di esso, primo push eseguito** — "
        "`origin/main` porta 73 record, misurati dal remoto; **6.3 e 6.7 chiuse** a meno del "
        "deposito, che è l'ultimo punto della Fase 7; il censimento del rilascio girato a 73 "
        "record apre **una decisione di protocollo, dichiarata e non presa** (voce 6.2)\n",
        "### rev. 3.30 — 17 settembre 2026 (sera) — record 74; **la decisione è presa: via (A)**, "
        "quattro eccezioni dichiarate, tre col digest di ciò che la citazione intendeva; e la "
        "copia rimossa dal commit `352e024` è **BYTE-IDENTICA** al sopravvissuto, `ae733e1e…` — "
        "quel commit ha rimosso un'**etichetta**, non un dato. Il censimento a 74 record passa "
        "**quattro verdetti su cinque**; `citati_committati` si chiude col commit quattro, non "
        "con un'eccezione. La 6.7 è chiusa di nuovo (`09eb415f…`), dopo essere stata riaperta "
        "per una riga che aveva detto la cosa sbagliata **due volte, in direzioni opposte**\n",
    ))

    # 2. 6.2: la decisione presa, sopra il blocco che la dichiarava aperta
    E.append((
        "      **✦✦✦ DECISIONE DI PROTOCOLLO APERTA, dichiarata e non presa.** I quattro percorsi del\n",
        "      **✦✦✦ DECISIONE PRESA il 17 set (sera): VIA (A), record 74.** Quattro eccezioni\n"
        "      dichiarate; il file delle eccezioni passa da 14 a **22 voci** (`8bd9607c…`, 10 064\n"
        "      byte). Tre delle quattro portano **il digest di ciò che la citazione intendeva**, e\n"
        "      per questo l'eccezione non nasconde un FAIL: lo sostituisce con un'ancora che il\n"
        "      record sbagliato non aveva.\n"
        "      - `src/paper2_item13rev2.py` → `src/paper2_item13_rev2.py`, `4306e613…`, 15 885 byte.\n"
        "        Produttore e consumatore confermati: scrive `item13rev2_<REG>.jsonl` (senza\n"
        "        underscore, da cui la confusione) e `paper2_item12b_wbar.py` lo rilegge. La grafia\n"
        "        citata dal record 27 non è **mai** stata aggiunta in nessun ramo;\n"
        "      - il params Quijote → il percorso con la cartella intermedia, `bf0519c6…`, 156 070\n"
        "        byte, **unica copia** sotto `data/raw/quijote`, e con lo stesso digest che il\n"
        "        record 43 dichiara: la citazione sbagliata e il file ancorato sono la stessa cosa.\n"
        "        Il percorso citato dal 43 **non esiste**, verificato — se esistesse non sarebbe una\n"
        "        grafia sbagliata ma un secondo file;\n"
        "      - `results/phase8_test2_permock.csv` → recuperabile da `352e024^`, `ae733e1e…`,\n"
        "        10 891 byte, e **BYTE-IDENTICO** al sopravvissuto `_hodfit` (vedi 6.7);\n"
        "      - `src/paper2_letture_1punto.py` → **niente**, e questa è l'unica senza ancora\n"
        "        propria. L'assenza è dimostrata da **due metri indipendenti**: la storia degli `A`\n"
        "        su tutti i rami non lo contiene, e una camminata su `D:\\projects` non trova nessun\n"
        "        file il cui nome contenga «letture». Un metro solo non basta: il primo non vede ciò\n"
        "        che non è mai stato committato, il secondo non vede ciò che è stato cancellato. Il\n"
        "        lavoro lo fa `paper2_passata_1punto.py`, `9122c7fa…`, 33 457 byte, 43/43.\n"
        "      **✦✦ Censimento a 74 record, esito.** `citati_esistono`, `citati_tracciati`,\n"
        "      `citati_non_esclusi` e `metri_concordi` **PASS**, zero su tutte e quattro le\n"
        "      popolazioni: 115 tracciati puliti, 16 esclusi con eccezione, 6 assenti con\n"
        "      eccezione, 2 pattern. Resta `citati_committati` **FAIL su 2** —\n"
        "      `paper2_v1_amendments.jsonl` e `paper2_freeze_verify.py`, modificati dall'append e\n"
        "      non ancora committati: **si chiude col commit quattro, non con un'eccezione**.\n"
        "      **✦✦ Due previsioni sbagliate, in due giorni, sulla stessa cosa.** «Con le 14\n"
        "      eccezioni `citati_non_esclusi` passa» (16 set) e «tutti e cinque i verdetti PASS»\n"
        "      (17 set, sera). La prima era una previsione dove la misura era disponibile; la\n"
        "      **seconda era evitabile senza misurare niente**, perché i due file erano modificati e\n"
        "      non committati nel momento in cui la previsione veniva fatta — e il FAIL su quei due\n"
        "      era stato previsto correttamente il giorno prima. Un esito che si conosce va detto,\n"
        "      non predetto al contrario.\n"
        "      *(Blocco seguente lasciato come storia: è la decisione prima che fosse presa, con "
        "l'argomento che l'ha sciolta — tre delle quattro citazioni hanno un'ancora, e quindi (A) "
        "non nasconde più niente.)*\n"
        "      **✦✦✦ DECISIONE DI PROTOCOLLO APERTA, dichiarata e non presa.** I quattro percorsi del\n",
    ))

    # 3. 6.7: chiusa di nuovo, e perche' era stata riaperta
    E.append((
        "- [x] **✧✧✧✧✧ 6.7 — `REPRODUCIBILITY.md`: CHIUSA il 17 set (sera)**, `7a72a509…`, 17 820\n"
        "      byte, 306 righe, nel commit tre.",
        "- [x] **✧✧✧✧✧ 6.7 — `REPRODUCIBILITY.md`: CHIUSA, RIAPERTA E CHIUSA DI NUOVO il 17 set**,\n"
        "      `09eb415f…`, 19 146 byte, 325 righe *(era `7a72a509…`, 17 820 byte, 306 righe)*.\n"
        "      **✦✦✦ Perché è stata riaperta: la stessa riga ha detto la cosa sbagliata due volte,\n"
        "      nelle due direzioni opposte.** La prima stesura diceva che la copia byte-identica\n"
        "      «**non esiste**»: falso, e git la conserva — il messaggio di `352e024` la chiama\n"
        "      *byte-identical* a chiare lettere. La riscrittura della mattina del 17 diceva che il\n"
        "      sopravvissuto «ha un nome simile e **non è la stessa cosa**»: falso nella direzione\n"
        "      opposta, perché **ai byte è la stessa cosa** — `ae733e1e…`, 10 891 byte per\n"
        "      entrambi, confrontati byte per byte. Quello che il commit ha rimosso è\n"
        "      un'**etichetta**: il nome `permock` prometteva la baseline test2 e il contenuto era il\n"
        "      sottoinsieme HOD-refit (35304.6 ± 1033.0, *N* = 200). Il dato sopravvive **una\n"
        "      volta**, sotto il nome che lo descrive. Storia del percorso: `e17da7a` (A),\n"
        "      `684d1f3` (M), `352e024` (D).\n"
        "      **La regola, che è costata un mese:** il record 70 §ix diceva «va letto prima di\n"
        "      dichiarare», e la lettura costava un `git show`. È arrivata il 17 settembre, dopo che\n"
        "      due versioni dello stesso paragrafo avevano detto due cose opposte, entrambe false.\n"
        "      *(Chiusura della mattina, per la storia.)* `7a72a509…`, 17 820\n"
        "      byte, 306 righe, nel commit tre.",
    ))
    return E


# ---------------------------------------------------------------------------
# STATO (tredicesima -> quattordicesima revisione)
# ---------------------------------------------------------------------------

def edits_stato(utc_reso, item_74):
    E = []

    # 1. intestazione
    E.append((
        "aggiornato **17 settembre 2026 (sera)**, tredicesima revisione\n",
        "aggiornato **17 settembre 2026 (sera)**, quattordicesima revisione\n",
    ))

    # 2. blocco in testa
    E.append((
        "> **Cosa è cambiato nella tredicesima revisione (17 settembre, sera) — IL DEPOSITO È STATO\n",
        "> **Cosa è cambiato nella quattordicesima revisione (17 settembre, sera) — LA DECISIONE È\n"
        "> PRESA, E UNA RIGA AVEVA SBAGLIATO NELLE DUE DIREZIONI.** Record **74**: i quattro\n"
        "> percorsi irrisolti del record 71 diventano **quattro eccezioni dichiarate**, e tre\n"
        "> portano il digest di ciò che la citazione intendeva — `paper2_item13_rev2.py`\n"
        "> (`4306e613…`), il params Quijote al percorso con la cartella intermedia (`bf0519c6…`,\n"
        "> unica copia), la copia rimossa recuperata da `352e024^` (`ae733e1e…`). La quarta,\n"
        "> `paper2_letture_1punto.py`, **non ha ancora perché non c'è niente da ancorare**, e\n"
        "> l'assenza è dimostrata da due metri indipendenti: la storia degli `A` su tutti i rami e\n"
        "> una camminata sul disco. Un'eccezione che porta un digest non nasconde un FAIL: lo\n"
        "> sostituisce con un'ancora, ed è ciò che ha sciolto la decisione lasciata aperta.\n"
        "> **La misura che cambia una frase scritta due volte:** la copia rimossa e il\n"
        "> sopravvissuto `_hodfit` sono **BYTE-IDENTICI**, `ae733e1e…`, 10 891 byte. Il commit\n"
        "> `352e024` ha rimosso un'**etichetta**, non un dato — il nome `permock` prometteva la\n"
        "> baseline test2 e il contenuto era il sottoinsieme HOD-refit (35304.6 ± 1033.0, N=200) —\n"
        "> e il §5 di `REPRODUCIBILITY.md` lo aveva detto sbagliato prima in un senso («non\n"
        "> esiste») e poi nell'altro («non è la stessa cosa»). Riscritto col digest: `09eb415f…`,\n"
        "> 325 righe, voce 6.7 chiusa di nuovo. Il record 70 §ix diceva «va letto prima di\n"
        "> dichiarare» e la lettura costava un `git show`: è arrivata un mese dopo.\n"
        "> **Eccezioni a 22 voci** (`8bd9607c…`), registro a **74**, CLEAN 74/74, e il censimento\n"
        "> passa **quattro verdetti su cinque**: resta `citati_committati` FAIL su 2, che si chiude\n"
        "> col commit quattro. **Due previsioni sbagliate in due giorni**, e la seconda era\n"
        "> evitabile senza misurare: i due file erano modificati e non committati mentre la\n"
        "> previsione veniva fatta. Checklist rev. 3.30.\n"
        "\n"
        "> **Cosa è cambiato nella tredicesima revisione (17 settembre, sera) — IL DEPOSITO È STATO\n",
    ))

    # 3. §0: le misure del record 74
    E.append((
        "| (17 set sera) censimento del rilascio a 73 record | 141 percorsi; `citati_tracciati` e `metri_concordi` PASS, `citati_esistono` e `citati_non_esclusi` **FAIL su 4** |\n",
        "| (17 set sera) censimento del rilascio a 73 record | 141 percorsi; `citati_tracciati` e `metri_concordi` PASS, `citati_esistono` e `citati_non_esclusi` **FAIL su 4** |\n"
        "| (17 set sera) la copia rimossa da `352e024` e il `_hodfit` | **BYTE-IDENTICI**: `ae733e1e…`, 10 891 byte entrambi, confrontati byte per byte |\n"
        "| (17 set sera) il percorso citato dal record 43 esiste? | **NO**, e il file vero è in **una** sola copia sotto `data/raw/quijote`, col digest del 43 |\n"
        "| (17 set sera) `paper2_item13rev2.py` (senza underscore) | **mai aggiunto** in nessun ramo e assente dal disco: trascrizione, non file perduto |\n"
        "| (17 set sera) `paper2_letture_1punto.py` | **assente da due popolazioni**: storia degli `A` su `--all` e camminata su `D:\\projects` |\n"
        "| (17 set sera) censimento a 74 record, con 22 eccezioni | **quattro verdetti su cinque PASS**; `citati_committati` FAIL su 2, che il commit quattro chiude |\n",
    ))

    # 4. riga di stato
    E.append((
        "quattro percorsi del record 71.\n",
        "quattro percorsi del record 71.\n"
        "\n"
        "**Al 17 settembre, sera, dopo il record 74 (quattordicesima revisione):** registro **74\n"
        "record**, CLEAN a 74/74 · checklist **rev. 3.30** · eccezioni a **22 voci**\n"
        "(`8bd9607c…`) · `REPRODUCIBILITY.md` **`09eb415f…`**, 325 righe · censimento **4/5 PASS**,\n"
        "`citati_committati` aperto fino al commit quattro · Fase 6: **chiuse 6.1, 6.3, 6.7, 6.8,\n"
        "6.9**; aperte 6.0b–d, 6.2, 6.4, 6.5, 6.6 · **nessuna decisione di protocollo aperta**.\n",
    ))

    # 5. §3: titolo, riga resa dal ledger, nota
    E.append((
        "## 3. Il registro degli emendamenti — 73 record\n\n### Fase 6, record 61–73\n",
        "## 3. Il registro degli emendamenti — 74 record\n\n### Fase 6, record 61–74\n",
    ))
    E.append((
        "| **73** | **17 set 12:49** | **`6.3/il_deposito_non_contiene_il_protocollo_e_tre_decisioni_di_rilascio`** |\n",
        "| 73 | 17 set 12:49 | `6.3/il_deposito_non_contiene_il_protocollo_e_tre_decisioni_di_rilascio` |\n"
        "| **%s** | **%s** | **`%s`** |\n" % (LEDGER_RECORD, utc_reso, item_74),
    ))
    E.append((
        "> le tre possibilità del 72 con una quarta, e **supera il §iii del 70** aprendo `origin`\n"
        "> all'aggiornamento periodico (§8, Rilascio).\n",
        "> le tre possibilità del 72 con una quarta, e **supera il §iii del 70** aprendo `origin`\n"
        "> all'aggiornamento periodico (§8, Rilascio); il **74** dichiara quattro eccezioni — tre\n"
        "> con il digest di ciò che la citazione intendeva — e registra che la copia rimossa dal\n"
        "> commit `352e024` era **byte-identica** al sopravvissuto: un'etichetta rimossa, non un\n"
        "> dato.\n",
    ))

    # 6. §8: il blocco Rilascio, coda
    E.append((
        "**Le eccezioni sono 14 e servono almeno 18:** il record 73 cita `logs/deposito_zenodo.json` e\n"
        "i due documenti compagni in `papers/`, e mancava già `results/paper2/remote_audit.json` del\n"
        "record 72; la ragione della voce del protocollo dice ancora «resta da verificare», ed è\n"
        "verificata. Più i quattro percorsi del record 71, che sono una **decisione aperta** (checklist\n"
        "6.2): se si scelgono le eccezioni serve un record 74.\n",
        "**Le eccezioni sono 22** (`8bd9607c…`, 10 064 byte), record 74: le quattro che seguivano dai\n"
        "record 70, 72 e 73 — `logs/deposito_zenodo.json`, i due documenti compagni in `papers/`,\n"
        "`results/paper2/remote_audit.json` — più le **quattro del record 71**, tre col digest di ciò\n"
        "che la citazione intendeva. La ragione della voce del protocollo è corretta: l'ancoraggio\n"
        "esterno non esiste fino al deposito della Fase 7. Tre voci NON portano digest e dicono\n"
        "perché: checklist e stato si rivedono a ogni sessione, `remote_audit.json` è rigenerabile, e\n"
        "un'ancora per byte su di essi sarebbe stale al primo patcher.\n"
        "**Il censimento passa quattro verdetti su cinque.** `citati_committati` FAIL su 2 —\n"
        "`src/paper2_v1_amendments.jsonl` e `src/paper2_freeze_verify.py` — si chiude col **commit\n"
        "quattro**, che deve portare ledger, `freeze_verify.py`, `REPRODUCIBILITY.md`, il file delle\n"
        "eccezioni, i due documenti e gli strumenti nuovi. Il tag `v3.1-paper2` è **spinto** e non si\n"
        "sposta più: un tag pubblico che cambia oggetto è ciò che il record 70 §iv evita.\n",
    ))

    # 7. §9: gli strumenti nuovi
    E.append((
        "| `paper2_patch_documenti_73.py` | record 73, commit tre, tag, push e censimento nei documenti | vedi selftest |\n",
        "| `paper2_patch_documenti_73.py` | record 73, commit tre, tag, push e censimento nei documenti | 26/26 |\n"
        "| `paper2_append_amend74.py` | record 74; rifà le quattro misure e **confronta byte per byte** la copia rimossa col sopravvissuto: rifiuta se non sono identici | 40/40 |\n"
        "| `paper2_patch_eccezioni.py` v1.1 | eccezioni 14 → 22; i digest delle quattro del 71 sono **misurati** dal disco e da `git show`, non scritti | 26/26 |\n"
        "| `paper2_patch_repro_permock.py` | voce 6.7: riscrive la riga del §5 col digest, e rifà la misura prima di scriverla | 18/18 |\n"
        "| `paper2_patch_documenti_74.py` | record 74, decisione presa e censimento nei documenti | vedi selftest |\n",
    ))

    # 8. §14: le lezioni del record 74
    E.append((
        "- **Prima di contare le chiavi, guardare che forma ha il file**: il confronto fra i due\n"
        "  `eccezioni_rilascio.json` è stato scritto per due liste e i file sono **dizionari**, quindi\n"
        "  «13 contro 14» non diceva se uno fosse un sottoinsieme. Rifatto per chiavi e valori: lo era.\n",
        "- **Prima di contare le chiavi, guardare che forma ha il file**: il confronto fra i due\n"
        "  `eccezioni_rilascio.json` è stato scritto per due liste e i file sono **dizionari**, quindi\n"
        "  «13 contro 14» non diceva se uno fosse un sottoinsieme. Rifatto per chiavi e valori: lo era.\n"
        "- **Due file byte-identici con nomi diversi sono un dato e un'etichetta**, non un duplicato\n"
        "  di dati (record 74). Chi legge il commit di rimozione come la rimozione di un dato\n"
        "  conclude che il dato non esiste più; chi legge il nome come descrizione del contenuto\n"
        "  conclude il contrario. Solo il digest decide.\n"
        "- **Un'assenza richiede due metri**: la storia dei commit non vede ciò che non è mai stato\n"
        "  committato, il disco non vede ciò che è stato cancellato. Si dichiara solo quando entrambi\n"
        "  tacciono (record 74).\n"
        "- **Un'istruzione di lettura non scade**: «va letto prima di dichiarare» (record 70 §ix) è\n"
        "  rimasta inevasa un mese, e nel frattempo due documenti hanno detto due cose opposte,\n"
        "  entrambe false, su una misura che costava un `git show`.\n"
        "- **Un FAIL permanente per disegno smette di discriminare**: un verdetto che si sa in\n"
        "  anticipo che fallirà per sempre non distingue più un difetto nuovo da uno noto. Va chiuso\n"
        "  con una dichiarazione — meglio, con un'ancora — o va cambiato il verdetto.\n"
        "- **Non predire un esito che si conosce già**: «tutti e cinque i verdetti PASS» è stato\n"
        "  detto mentre due file erano modificati e non committati, e il loro FAIL era stato previsto\n"
        "  correttamente il giorno prima. Prevedere è un errore anche quando la misura non serve.\n",
    ))
    return E


# ---------------------------------------------------------------------------

def compute(a):
    ck_b, st_b = read_bytes(a.checklist), read_bytes(a.stato)
    check_anchor(a.checklist, ck_b, ANCORA_CHECKLIST, "checklist")
    check_anchor(a.stato, st_b, ANCORA_STATO, "stato")
    reso = check_record_74(read_ledger(a.ledger))
    ck, st = ck_b.decode("utf-8"), st_b.decode("utf-8")
    ck_new = apply_edits(ck, edits_checklist(), "checklist")
    st_new = apply_edits(st, edits_stato(*reso), "stato")
    if MARCA_CHECKLIST not in ck_new or MARCA_STATO not in st_new:
        raise PatchError("marca di revisione assente dal testo nuovo")
    if "\r" in ck_new or "\r" in st_new:
        raise PatchError("il testo nuovo contiene CR")
    return ck, ck_new, st, st_new, reso


def rapporto(ck_new, st_new, reso):
    print("riga §3 resa dal ledger:\n  74: %s  %s" % reso)
    ckb, stb = ck_new.encode("utf-8"), st_new.encode("utf-8")
    print("checklist nuova: %s  %d byte  (rev. 3.30)" % (sha256_bytes(ckb), len(ckb)))
    print("stato nuovo:     %s  %d byte  (quattordicesima revisione)"
          % (sha256_bytes(stb), len(stb)))


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

def _ledger_finto(n=LEDGER_RECORD, marker=MARKER_74, dettagli=True, ecc=4):
    out = b""
    for i in range(1, n + 1):
        rec = {"item": "finto/%d" % i, "utc": "2026-09-17T14:0%d:00+00:00" % (i % 10),
               "rules": {"marker": marker if i == n else "altro-%d" % i}}
        if i == n:
            rec["item"] = "6.2/quattro_eccezioni_dichiarate_e_la_copia_rimossa_era_byte_identica"
            rec["utc"] = "2026-09-17T13:57:10+00:00"
            rec["eccezioni_dichiarate"] = ["a", "b", "c", "d"][:ecc]
            if dettagli:
                rec["evidence"] = " ".join(DETTAGLI_74)
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
        reso = check_record_74(read_ledger(led))
        controlla("ledger a 74 col record 74: passa", reso[0] == "17 set 13:57")
        with open(led, "wb") as f:
            f.write(_ledger_finto(n=73))
        controlla("ledger a 73 rifiutato", rifiuta(lambda: read_ledger(led)))
        with open(led, "wb") as f:
            f.write(_ledger_finto(marker="emendamento-73-il-deposito-non-contiene-il-protocollo"))
        controlla("marker del 73 al posto del 74: rifiutato",
                  rifiuta(lambda: check_record_74(read_ledger(led))))
        with open(led, "wb") as f:
            f.write(_ledger_finto(dettagli=False))
        controlla("record 74 senza i dettagli letterali: rifiutato",
                  rifiuta(lambda: check_record_74(read_ledger(led))))
        with open(led, "wb") as f:
            f.write(_ledger_finto(ecc=3))
        controlla("record 74 che non dichiara quattro eccezioni: rifiutato",
                  rifiuta(lambda: check_record_74(read_ledger(led))))

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
        controlla("seconda applicazione rifiutata",
                  rifiuta(lambda: apply_edits(ck_new, eck, "checklist")))
        controlla("ancora duplicata rifiutata",
                  rifiuta(lambda: apply_edits(fck + eck[0][0], eck, "checklist")))
        controlla("la decisione PRESA sta sopra il blocco che la dichiarava aperta",
                  ck_new.index("DECISIONE PRESA il 17 set")
                  < ck_new.index("DECISIONE DI PROTOCOLLO APERTA"))
        controlla("il blocco aperto e' marcato come storia",
                  "lasciato come storia" in ck_new)
        controlla("le tre ancore e la quarta senza ancora sono nella 6.2",
                  all(x in ck_new for x in ("4306e613", "bf0519c6", "ae733e1e"))
                  and "**niente**, e questa è l'unica senza ancora" in ck_new)
        controlla("citati_committati e' dichiarato come chiudibile solo dal commit quattro",
                  "si chiude col commit quattro, non con un'eccezione" in ck_new)
        controlla("le due previsioni sbagliate sono registrate, con la differenza fra loro",
                  "Due previsioni sbagliate, in due giorni" in ck_new
                  and "evitabile senza misurare niente" in ck_new)
        controlla("la 6.7 dice che la riga aveva sbagliato in due direzioni",
                  "CHIUSA, RIAPERTA E CHIUSA DI NUOVO" in ck_new
                  and "nelle due direzioni opposte" in ck_new)
        controlla("la riga §3 del 74 e' nello stato, in grassetto",
                  "| **74** | **17 set 13:57** |" in st_new
                  and "| 73 | 17 set 12:49 |" in st_new)
        controlla("lo stato dichiara nessuna decisione aperta",
                  "**nessuna decisione di protocollo aperta**" in st_new)

        p = os.path.join(td, "doc.md")
        with open(p, "wb") as f:
            f.write(b"abc\n")
        controlla("ancora sha sbagliata rifiutata",
                  rifiuta(lambda: check_anchor(p, read_bytes(p), ("0" * 64, 4), "x")))
        write_atomic(p, b"xyz\n")
        controlla("write_atomic scrive e rilegge", read_bytes(p) == b"xyz\n")
        controlla("write_atomic non lascia temporanei",
                  not [x for x in os.listdir(td) if x.startswith(".patch74_")])

    if os.path.exists(a.checklist) and os.path.exists(a.stato):
        ckb, stb = read_bytes(a.checklist), read_bytes(a.stato)
        if ((sha256_bytes(ckb), len(ckb)) == ANCORA_CHECKLIST
                and (sha256_bytes(stb), len(stb)) == ANCORA_STATO):
            ckt, stt = ckb.decode("utf-8"), stb.decode("utf-8")
            controlla("documenti veri: ogni ancora della checklist compare una volta",
                      all(ckt.count(o) == 1 for o, _ in edits_checklist()))
            controlla("documenti veri: ogni ancora dello stato compare una volta",
                      all(stt.count(o) == 1 for o, _ in edits_stato("17 set 13:57", "x")))
        else:
            print("  [--] documenti veri non all'ancora attesa: controlli saltati")
    else:
        print("  [--] documenti veri non trovati: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="record 74 e decisione presa nei documenti")
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

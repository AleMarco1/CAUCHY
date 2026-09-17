#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_append_amend73.py — record 73: il version DOI non identifica NESSUNA versione del
protocollo, e tre decisioni di rilascio del 17 settembre 2026.

Appende UN record a src\paper2_v1_amendments.jsonl. Modello `amend68`-`amend72`: temporaneo
piu' os.replace, e IL CANCELLO PRINCIPALE E' IL PREFISSO.

CHE COSA DICHIARA. Il record 72 ancora la v1.1 del protocollo per byte e lascia aperte TRE
possibilita' sul deposito: (a) il deposito porta la v1.1, (b) porta la v1.0, (c) e' stato
aggiornato dopo. Misurato il 17 settembre: nessuna delle tre. Il deposito
10.5281/zenodo.22148444 (`v3.0-paper2`) contiene sei file — README.md, MANIFEST.sha256 e
quattro zip — e **nessuno dei quattro zip contiene il protocollo**, in nessuna versione; e
nessuna delle quattro versioni del concept DOI lo contiene. E' una QUARTA possibilita', che il
72 non aveva previsto: il DOI ancora l'archivio della pipeline, non il documento di
pre-registrazione.

E tre decisioni prese il 17 settembre:
  - GitHub (`origin`) si aggiorna PERIODICAMENTE. Supera il §iii del record 70, che differiva
    la pubblicazione alla sottomissione;
  - il deposito Zenodo si aggiorna SOLO alla sottomissione, ultimo punto della Fase 7, con la
    v1.1 del protocollo dentro;
  - le tredici voci del Paper 1 si applicano all'ULTIMO PUNTO della Fase 7, prima della
    sottomissione.

CANCELLI PROPRI DI QUESTO RECORD:
  - il ledger deve essere a 72 record, coi suoi byte e il suo profilo di fine riga;
  - il record 70 deve contenere il testo del differimento che questo record supera, e il
    record 72 le tre possibilita' che questo record chiude: un record non supera cio' che non
    c'e';
  - il protocollo su disco deve portare ancora i byte che il record 72 ancora, e il campo
    `prereg_sha256` del 72 deve concordare col disco;
  - il percorso del protocollo NON deve essere tracciato, e git deve conservare la v1.0:
    invariato dal 72, riverificato qui;
  - LA MISURA DEL DEPOSITO deve venire da un file di misura prodotto da `misura-deposito` e
    combaciare, file per file e digest per digest, con cio' che questo record dichiara. Se il
    deposito e' cambiato, il cancello rifiuta: il record va riscritto, non appeso.

NON FA: non deposita, non spinge, non tocca il protocollo, non riscrive nessun record. La
correzione della frase «version 1.0 deposited 27 August 2026» dentro il protocollo NON e'
fatta: e' dichiarata e rinviata al deposito della Fase 7.

Sequenza:  selftest  ->  misura-deposito  ->  applica --dry-run  ->  applica
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
REFERENCE_PATH_DEFAULT = "src/paper2_v1_reference.json"
REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA256 = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

LEDGER_DEFAULT = "src/paper2_v1_amendments.jsonl"
LEDGER_SHA256_ATTESO = "5a48598fe609740fa5d656d68de30c3ab39c10f51ddb4f223dbf790fac459dfc"
LEDGER_BYTE_ATTESI = 602170
ATTESI_DEFAULT = 72
NUMERO_RECORD = 73

EOL_CRLF_ATTESI = 66
EOL_LF_ATTESI = 6
EOL_RIGHE_LF_ATTESE = [8, 9, 10, 11, 13, 14]

PREREG = "papers/paper2/paper2_prereg_v1.md"
V11_SHA256 = "607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86"
V11_BYTE = 25319
V10_SHA256 = "05cd32b20388fffd5372711880d4c11ef6dda32ff2ff7767e898d667e2a6c115"
V10_BYTE = 21430
COMMIT_IMPORTO = "73c8213"
COMMIT_UNTRACK = "900335e"
COMMIT_ATTESI = 2

VERSION_DOI = "10.5281/zenodo.22148444"
CONCEPT_DOI = "10.5281/zenodo.21128856"
DEPOSITO_RECORD_ID = "22148444"
DEPOSITO_DEFAULT = "logs/deposito_zenodo.json"
API_VERSIONI = "https://zenodo.org/api/records/%s/versions?size=25" % DEPOSITO_RECORD_ID
API_CONTENUTO = "https://zenodo.org/api/records/%s/files/%s/content"

# Le sette righe che il 17 settembre 2026 il deposito porta, misurate scaricando ogni file e
# aprendo ogni zip. `voci` e' il numero di membri dello zip (0 per i file non-zip).
DEPOSITO_ATTESO = {
    "21128857": {
        "doi": "10.5281/zenodo.21128857", "version": "v1.0",
        "publication_date": "2026-07-02", "created": "2026-07-02T08:50:36",
        "files": [
            {"key": "AleMarco1/CAUCHY-v1.0.zip", "size": 3685492, "voci": 181,
             "sha256": "12a823887501d220d32f4758aa4f09c774916a6b45c77f364388d266d0950e7e"},
        ],
    },
    "21158278": {
        "doi": "10.5281/zenodo.21158278", "version": "v2.0-paper-c",
        "publication_date": "2026-07-03", "created": "2026-07-03T09:38:28",
        "files": [
            {"key": "AleMarco1/CAUCHY-v2.0-paper-c.zip", "size": 3756484, "voci": 212,
             "sha256": "f7710f8923842a64ce9b15a715d3a2cf4310f384e171a78b237d8764defda819"},
        ],
    },
    "21213351": {
        "doi": "10.5281/zenodo.21213351", "version": "v2.1-phase9b",
        "publication_date": "2026-07-06", "created": "2026-07-06T05:07:23",
        "files": [
            {"key": "AleMarco1/CAUCHY-v2.1-phase9b.zip", "size": 3840650, "voci": 237,
             "sha256": "85f3e1c1044c9cacfe8d90643c4c09647853e9b0ebff593dacdb3c3430c2bbb9"},
        ],
    },
    "22148444": {
        "doi": VERSION_DOI, "version": "v3.0-paper2",
        "publication_date": "2026-08-28", "created": "2026-08-28T18:07:52",
        "files": [
            {"key": "MANIFEST.sha256", "size": 429, "voci": 0,
             "sha256": "c975dd5c3a634a932f1f5af638d2e19bdb3bb705a162f01101472850581f9b91"},
            {"key": "README.md", "size": 7078, "voci": 0,
             "sha256": "bea7ea6120202b10b40dc5a46d50b0e8a587fc3b94ddfd5188e82030ec80cd37"},
            {"key": "cauchy_paper2_products.zip", "size": 365854, "voci": 28,
             "sha256": "e8d8e34660841c861751800dd45fe47249b7b58ea8971e5c699efafae14ab2e2"},
            {"key": "cauchy_code.zip", "size": 945010, "voci": 172,
             "sha256": "37319a68b7100b9376fa1f52631512de870cae069380117ec17a578e495db39b"},
            {"key": "cauchy_records_v1.zip", "size": 4886558, "voci": 224,
             "sha256": "7cb66fc083c0430a91b92228165378eb5a6c69a02dbf64c89799c19254ee4f0b"},
            {"key": "cauchy_manifests_v1.zip", "size": 1819849, "voci": 14,
             "sha256": "b5fb812d7ec812b13e75b5299deafb57441d33f99b2e7d99640e5bfc7e96b2e1"},
        ],
    },
}
VOCI_ESAMINATE = sum(f["voci"] for v in DEPOSITO_ATTESO.values() for f in v["files"])  # 1068
# Quello che si cerca dentro ogni zip. Per NOME, ma la popolazione e' tutta: ogni membro di
# ogni archivio, non un sottoinsieme scelto.
AGHI = ("prereg", "protocol", "papers/", "papers\\")

# Il ledger depositato dentro cauchy_code.zip: dodici record, cioe' il conteggio che il §9 del
# protocollo dichiara al deposito. E' la conferma indipendente di quel dodici.
LEDGER_DEPOSITATO = {"membro": "src/paper2_v1_amendments.jsonl", "byte": 12670, "record": 12}

# Testi che questo record supera: devono esistere nei record che dice di superare.
ANCORA_70 = "la pubblicazione avviene in concomitanza con essa"
ANCORA_70_CHIAVE = "iii_decisione_pubblicazione_differita"
ANCORA_72_CHIAVE = "iii_la_verifica_del_deposito_resta_aperta"
ANCORA_72_TESTI = ("(a)", "(b)", "(c)", "DICHIARATA come aperta")

ORIGIN_REF = "origin/main"


class Rifiuto(Exception):
    """Un cancello non e' passato. Nessun byte e' stato scritto."""


# ===========================================================================
# utilita' (identiche a amend68-amend72)
# ===========================================================================

def ora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def sha256_bytes(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


def profilo_eol(dati: bytes) -> dict:
    ris = {"n_byte": len(dati), "n_righe": 0, "crlf": 0, "lf": 0,
           "righe_lf": [], "coda_terminata": True, "ereditato": None}
    if not dati:
        return ris
    ris["coda_terminata"] = dati.endswith(b"\n")
    parti = dati.split(b"\n")
    corpi = parti[:-1]
    coda = None if dati.endswith(b"\n") else parti[-1]
    for i, corpo in enumerate(corpi, start=1):
        if corpo.endswith(b"\r"):
            ris["crlf"] += 1
        else:
            ris["lf"] += 1
            ris["righe_lf"].append(i)
    ris["n_righe"] = len(corpi) + (0 if coda is None else 1)
    if corpi:
        ris["ereditato"] = "crlf" if corpi[0].endswith(b"\r") else "lf"
    return ris


def righe_json(dati: bytes) -> list:
    fuori = []
    for grezza in dati.split(b"\n"):
        linea = grezza[:-1] if grezza.endswith(b"\r") else grezza
        if not linea.strip():
            continue
        fuori.append(json.loads(linea.decode("utf-8")))
    return fuori


# ===========================================================================
# misura del deposito — il comando che produce l'artefatto
# ===========================================================================

def _scarica(url: str, scarica=None) -> bytes:
    if scarica is not None:
        return scarica(url)
    try:
        with urllib.request.urlopen(url, timeout=180) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001
        raise Rifiuto("non ho potuto leggere %s: %r" % (url, e))


def misura_deposito(scarica=None) -> dict:
    """Scarica OGNI file di OGNI versione del concept DOI, apre ogni zip, e cerca il
    protocollo fra tutti i membri. Nessun campo e' assunto: cio' che non si misura non entra
    nel rapporto."""
    grezzo = _scarica(API_VERSIONI, scarica)
    try:
        hits = json.loads(grezzo.decode("utf-8"))["hits"]["hits"]
    except Exception as e:  # noqa: BLE001
        raise Rifiuto("la risposta dell'elenco versioni non e' quella attesa: %r" % e)

    versioni = {}
    voci = 0
    trovato = []
    for h in hits:
        rid = str(h["id"])
        meta = h.get("metadata", {})
        files = []
        for f in h.get("files", []):
            key = f["key"]
            dati = _scarica(API_CONTENUTO % (rid, key), scarica)
            if len(dati) != f["size"]:
                raise Rifiuto("%s/%s: scaricati %d byte, dichiarati %d"
                              % (rid, key, len(dati), f["size"]))
            membri = []
            if key.lower().endswith(".zip"):
                try:
                    with zipfile.ZipFile(io.BytesIO(dati)) as z:
                        membri = z.namelist()
                except zipfile.BadZipFile as e:
                    raise Rifiuto("%s/%s non e' uno zip leggibile: %r" % (rid, key, e))
            colpi = sorted(m for m in membri if any(a in m.lower() for a in AGHI))
            if colpi:
                trovato.append({"record_id": rid, "file": key, "membri": colpi})
            voci += len(membri)
            files.append({"key": key, "size": len(dati), "sha256": sha256_bytes(dati),
                          "voci": len(membri), "colpi": colpi})
        versioni[rid] = {
            "doi": h.get("doi"), "version": meta.get("version"),
            "publication_date": meta.get("publication_date"),
            "created": str(h.get("created", ""))[:19],
            "files": files,
        }
    return {
        "strumento": "paper2_append_amend73.py misura-deposito",
        "utc": ora_utc(),
        "concept_doi": CONCEPT_DOI,
        "version_doi": VERSION_DOI,
        "aghi": list(AGHI),
        "versioni": versioni,
        "voci_esaminate": voci,
        "protocollo_trovato": trovato,
    }


def cancello_deposito(rapporto: dict) -> list:
    """Confronta il rapporto con cio' che il record dichiara. Tutto, non un campione."""
    esiti = []
    if not isinstance(rapporto, dict) or "versioni" not in rapporto:
        raise Rifiuto("il file di misura non ha la forma attesa: manca `versioni`")
    v = rapporto["versioni"]
    if set(v) != set(DEPOSITO_ATTESO):
        raise Rifiuto("versioni nel deposito: %s, attese %s. Se ne e' stata aggiunta una, il "
                      "record va riscritto." % (sorted(v), sorted(DEPOSITO_ATTESO)))
    for rid, atteso in sorted(DEPOSITO_ATTESO.items()):
        got = v[rid]
        for campo in ("doi", "version", "publication_date"):
            if str(got.get(campo)) != atteso[campo]:
                raise Rifiuto("versione %s, campo %s: %r, atteso %r"
                              % (rid, campo, got.get(campo), atteso[campo]))
        if not str(got.get("created", "")).startswith(atteso["created"]):
            raise Rifiuto("versione %s, created: %r, atteso %r"
                          % (rid, got.get("created"), atteso["created"]))
        gf = {f["key"]: f for f in got.get("files", [])}
        af = {f["key"]: f for f in atteso["files"]}
        if set(gf) != set(af):
            raise Rifiuto("versione %s: file %s, attesi %s" % (rid, sorted(gf), sorted(af)))
        for key in sorted(af):
            for campo in ("size", "sha256", "voci"):
                if gf[key][campo] != af[key][campo]:
                    raise Rifiuto("versione %s, file %s, %s: %r, atteso %r"
                                  % (rid, key, campo, gf[key][campo], af[key][campo]))
            if gf[key].get("colpi"):
                raise Rifiuto("versione %s, file %s: il protocollo C'E': %r. Il record 73 "
                              "direbbe il falso." % (rid, key, gf[key]["colpi"]))
        esiti.append("versione %s (%s, %s): %d file, digest conformi, nessun membro col "
                     "protocollo" % (rid, atteso["version"], atteso["publication_date"],
                                     len(af)))
    if rapporto.get("voci_esaminate") != VOCI_ESAMINATE:
        raise Rifiuto("voci esaminate: %r, attese %d"
                      % (rapporto.get("voci_esaminate"), VOCI_ESAMINATE))
    if rapporto.get("protocollo_trovato"):
        raise Rifiuto("il rapporto trova il protocollo nel deposito: %r"
                      % rapporto["protocollo_trovato"])
    if sorted(rapporto.get("aghi") or []) != sorted(AGHI):
        raise Rifiuto("il rapporto e' stato prodotto con altri termini di ricerca: %r"
                      % (rapporto.get("aghi"),))
    esiti.append("%d membri esaminati in tutto, zero col protocollo" % VOCI_ESAMINATE)
    return esiti


# ===========================================================================
# il record
# ===========================================================================

def costruisci_record(citanti: int, totale: int, origin: dict) -> dict:
    return {
        "document": "paper2_prereg_v1.md v1.1 — version DOI " + VERSION_DOI,
        "type": "protocol",
        "utc": ora_utc(),
        "item": "6.3/il_deposito_non_contiene_il_protocollo_e_tre_decisioni_di_rilascio",
        "key": "the_version_doi_identifies_no_version_of_the_protocol_and_the_release_opens_periodically",
        "amends_records": [70, 72],
        "json_path": PREREG + "; REPRODUCIBILITY.md §1, §2 e §5; "
                     "papers/paper2/checklist_paper2.md voci 6.0a, 6.2, 6.3, 6.7; "
                     "papers/paper2/paper2_stato.md §8",
        "old_value":
            "Il record 72 ancora la v1.1 per byte e lascia aperte tre possibilita' sul "
            "deposito: (a) il deposito porta la v1.1, e il DOI ancora " + V11_SHA256[:16]
            + "…; (b) porta la v1.0, e allora i record citano una v1.1 che il DOI non "
            "identifica; (c) e' stato aggiornato dopo, e va datato. Il record 70 §iii decide "
            "che «i record 56-69 e i risultati di Fase 4, 5 e 6 restano LOCALI fino alla "
            "sottomissione, e la pubblicazione avviene in concomitanza con essa». E la voce "
            "6.0a della checklist colloca le tredici voci del Paper 1 «qui», in Fase 6.",
        "reason":
            "Un version DOI ancora i byte che il deposito CONTIENE. Le tre possibilita' del "
            "record 72 presupponevano tutte che il protocollo fosse dentro, in una versione o "
            "nell'altra: nessuna prevedeva che non ci fosse affatto. E' l'errore di forma che "
            "il record 71 descrive — dedurre la causa dalla forma — applicato a un'assenza: "
            "tre rami plausibili non sono una partizione, e l'unico modo di sapere quale vale "
            "e' aprire il deposito. Aperto il 17 settembre 2026, file per file e membro per "
            "membro, non e' nessuno dei tre.",
        "new_value": {
            "i_la_misura": {
                "che_cosa_e_stato_aperto": "Le quattro versioni del concept DOI " + CONCEPT_DOI
                                           + ": 21128857 (v1.0, 2 lug), 21158278 "
                                           "(v2.0-paper-c, 3 lug), 21213351 (v2.1-phase9b, 6 "
                                           "lug), 22148444 (v3.0-paper2, 28 ago). Ogni file "
                                           "scaricato, ogni zip aperto, ogni membro "
                                           "esaminato: %d in tutto." % VOCI_ESAMINATE,
                "che_cosa_contiene_il_deposito_del_28_agosto":
                    "Sei file: MANIFEST.sha256 (429 byte), README.md (7078), "
                    "cauchy_paper2_products.zip (365854, 28 membri), cauchy_code.zip (945010, "
                    "172), cauchy_records_v1.zip (4886558, 224), cauchy_manifests_v1.zip "
                    "(1819849, 14). I quattro digest dichiarati dal MANIFEST.sha256 "
                    "coincidono coi digest dei file scaricati.",
                "il_protocollo": "ASSENTE. Nessun membro, in nessuno zip, in nessuna delle "
                                 "quattro versioni, ha nel percorso `prereg`, `protocol` o "
                                 "`papers/`. Il deposito non contiene il documento di "
                                 "pre-registrazione ne' in v1.0 ne' in v1.1, e "
                                 "`cauchy_code.zip` non contiene `papers/` perche' "
                                 "quell'albero era uscito dal versionamento col commit "
                                 + COMMIT_UNTRACK + ", sedici minuti prima del deposito.",
                "il_ledger_depositato": "cauchy_code.zip porta "
                                        + LEDGER_DEPOSITATO["membro"] + " con "
                                        + str(LEDGER_DEPOSITATO["record"]) + " record, "
                                        + str(LEDGER_DEPOSITATO["byte"]) + " byte: e' la "
                                        "conferma indipendente del «dodici al deposito» che "
                                        "il §9 del protocollo dichiara e che "
                                        "paper2_freeze_verify.py usa come soglia inferiore.",
                "quanti_record_citano_il_prereg": citanti,
                "su_quanti_record": totale,
            },
            "ii_la_quarta_possibilita":
                "Il version DOI " + VERSION_DOI + " identifica l'ARCHIVIO DELLA PIPELINE al "
                "momento della pre-registrazione, non il documento di pre-registrazione. La "
                "stringa che " + str(citanti) + " record su " + str(totale) + " portano nel "
                "campo `document` resta un identificatore valido del DEPOSITO, e non e' — e "
                "non era — un ancoraggio del protocollo: quell'ancoraggio e' il record 72, "
                "per byte. Le possibilita' (a), (b) e (c) del 72 sono chiuse tutte e tre per "
                "misura, e sostituite da questa.",
            "iii_che_cosa_dice_il_protocollo_di_se":
                "La v1.1 dichiara in testa «Version 1.1 — 28 August 2026 (version 1.0 "
                "deposited 27 August 2026)». Nessuna versione del concept DOI e' del 27 "
                "agosto: le date sono 2, 3 e 6 luglio e 28 agosto. L'unico evento del 27 "
                "agosto su quel percorso e' il commit " + COMMIT_IMPORTO + ". La parola "
                "«deposited» in quella riga descrive quindi un commit, non un deposito. La "
                "frase NON e' corretta qui: il protocollo non si riscrive per emendamento, e "
                "la correzione va fatta nella versione che si deposita alla sottomissione, "
                "dove sara' vera.",
            "iv_le_due_versioni_del_protocollo_a_confronto":
                "v1.0: " + V10_SHA256 + ", " + str(V10_BYTE) + " byte, recuperabile da git a "
                + COMMIT_UNTRACK + "^. v1.1: " + V11_SHA256 + ", " + str(V11_BYTE) + " byte, "
                "solo su disco, ancorata dal record 72. Fra le due: 8 righe tolte e 61 "
                "aggiunte, e le aggiunte cadono nel preambolo, nel §2.1 (Reference set), nel "
                "§9 (Amendment record) e in tre righe del §0. **Le sezioni che portano le "
                "regole dell'analisi sono identiche riga per riga.** E' la ragione per cui "
                "depositare la v1.1 alla sottomissione non altera niente di cio' che era "
                "pre-registrato: e' misurato, non assunto, e va rimisurato se qualcuno tocca "
                "il documento.",
            "v_decisione_github_periodico":
                "`origin` (https://github.com/AleMarco1/CAUCHY.git) si aggiorna PERIODICAMENTE "
                "con commit e tag, non piu' solo alla sottomissione: questo SUPERA il §iii del "
                "record 70. Stato misurato al momento di questo record: " + ORIGIN_REF + " a "
                + str(origin.get("commit")) + ", con " + str(origin.get("record")) + " record "
                "nel ledger pubblico, contro " + str(totale) + " in locale. La ragione del "
                "differimento — che i referee vedessero i risultati insieme al manoscritto — "
                "resta soddisfatta: cio' che decide la lettura e' la sottomissione del "
                "manoscritto, non la visibilita' del codice, e un repository che avanza a "
                "salti di settimane e' piu' difficile da verificare di uno che avanza per "
                "commit. Il §iii del 70 resta valido per il DEPOSITO, non per il repository.",
            "vi_decisione_zenodo_alla_sottomissione":
                "Il deposito Zenodo si aggiorna SOLO alla sottomissione del Paper 2, come "
                "ULTIMO punto della Fase 7, e la nuova versione contiene la v1.1 del "
                "protocollo — che e' cio' che chiude la catena aperta dal record 72 e da "
                "questo. Fino a quel momento il protocollo e' ancorato per byte e non per DOI, "
                "e i due ancoraggi vanno citati per quello che sono.",
            "vii_decisione_paper1_alla_sottomissione":
                "Le tredici voci di modifiche_paper1.md si applicano all'ULTIMO punto della "
                "Fase 7, prima della sottomissione, non in Fase 6: il manoscritto e' in "
                "revisione e le Fasi 6 e 7 possono produrne altre. La voce 6.0a della "
                "checklist e la voce Z-P1 di paper2_stato.md sono state aggiornate il 17 "
                "settembre.",
            "viii_what_is_NOT_done":
                "Nessun deposito e' stato fatto o aggiornato. Nessun push e' stato fatto da "
                "questo record: la decisione del §v lo consente, non lo esegue. Il protocollo "
                "non e' stato toccato, e la frase «deposited 27 August 2026» resta come sta. "
                "Nessun record e' stato riscritto: i record 70 e 72 restano leggibili come "
                "erano, e questo li supera dichiarandolo. Il §5 di REPRODUCIBILITY.md porta "
                "ancora, al momento di questo record, due affermazioni false gia' dichiarate "
                "dai record 69 e 71 — i fine riga del ledger e la copia byte-identica — e la "
                "loro correzione e' la voce 6.7.",
        },
        "evidence":
            "Misure del 17 settembre 2026, dal servizio Zenodo. `GET " + API_VERSIONI + "`: "
            "quattro versioni, 21128857 (v1.0, publication_date 2026-07-02), 21158278 "
            "(v2.0-paper-c, 2026-07-03), 21213351 (v2.1-phase9b, 2026-07-06), 22148444 "
            "(v3.0-paper2, 2026-08-28, created 2026-08-28T18:07:52Z). Ogni file di ogni "
            "versione scaricato per intero e verificato per dimensione e sha256; ogni zip "
            "aperto e i suoi membri elencati: " + str(VOCI_ESAMINATE) + " in tutto, dei quali "
            "ZERO contengono `prereg`, `protocol` o `papers/` nel percorso. I quattro digest "
            "del MANIFEST.sha256 del deposito coincidono con quelli dei file scaricati. "
            "cauchy_code.zip::" + LEDGER_DEPOSITATO["membro"] + " porta "
            + str(LEDGER_DEPOSITATO["record"]) + " record. Il rapporto completo sta in "
            + DEPOSITO_DEFAULT + " ed e' stato riconfrontato, campo per campo, dai cancelli di "
            "questo script immediatamente prima dell'append; gli stessi cancelli hanno "
            "riverificato dal disco e da git i byte della v1.1, i byte della v1.0 conservata "
            "da git, il fatto che il percorso non sia tracciato, e che i record 70 e 72 "
            "contengano i testi che questo record supera.",
        "counts_before": {"DOCUMENTED_AMENDMENTS": ATTESI_DEFAULT,
                          "ledger_su_disco": ATTESI_DEFAULT},
        "counts_after": {"DOCUMENTED_AMENDMENTS": NUMERO_RECORD,
                         "ledger_su_disco": NUMERO_RECORD},
        "counts_note": "Regola del record 67: un campo di conteggi porta il numero che i "
                       "documenti avranno DOPO i patcher. DOCUMENTED_AMENDMENTS va portato a "
                       + str(NUMERO_RECORD) + " da paper2_patch_documented_amendments.py.",
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": REFERENCE_FILE_SHA256,
        "reference_self_sha256": REFERENCE_SELF_SHA256,
        "prereg_sha256": V11_SHA256,
        "prereg_byte": V11_BYTE,
        "deposito": {
            "version_doi": VERSION_DOI,
            "concept_doi": CONCEPT_DOI,
            "versioni": sorted(DEPOSITO_ATTESO),
            "voci_esaminate": VOCI_ESAMINATE,
            "protocollo_presente": False,
            "file_del_28_agosto": {f["key"]: {"byte": f["size"], "sha256": f["sha256"]}
                                   for f in DEPOSITO_ATTESO[DEPOSITO_RECORD_ID]["files"]},
            "ledger_depositato": dict(LEDGER_DEPOSITATO),
        },
        "origin": dict(origin),
        "numbering_rule": "Il numero di un emendamento e' la sua POSIZIONE 1-based in questo "
                          "file. Questo e' il record %d." % NUMERO_RECORD,
        "rules": {
            "marker": "emendamento-73-il-deposito-non-contiene-il-protocollo",
            "companion_documents": "REPRODUCIBILITY.md §1, §2 e §5; checklist_paper2.md voci "
                                   "6.0a, 6.3 e 6.7; paper2_stato.md §8",
            "un_DOI_ancora_cio_che_il_deposito_contiene":
                "Un version DOI non ancora un documento perche' quel documento lo cita: "
                "ancora i byte che stanno dentro il deposito. Prima di dire che un DOI ancora "
                "qualcosa, si apre il deposito e si guarda.",
            "tre_possibilita_plausibili_non_sono_una_partizione":
                "Un elenco di rami costruito da quello che si sa non copre quello che non si "
                "sa. Dichiararlo aperto e' giusto; dichiararlo esaustivo no. Il record 72 fece "
                "la prima cosa, e questo aggiunge il quarto ramo che la misura ha trovato.",
            "due_ancoraggi_diversi_si_citano_diversamente":
                "Il protocollo ha un ancoraggio per byte (record 72) e nessun ancoraggio per "
                "DOI fino al deposito della Fase 7. Citare il DOI come se ancorasse il "
                "documento e' l'errore che questo record chiude.",
            "aprire_il_repository_e_una_decisione_di_rilascio_separata_dal_deposito":
                "Rendere leggibile il codice e depositare un archivio citabile sono due "
                "decisioni: la prima si puo' fare periodicamente, la seconda ha senso quando "
                "lo stato e' quello che il manoscritto cita.",
            "depositare_dopo_non_cambia_il_pre_registrato_se_le_regole_sono_identiche":
                "Una versione posteriore di un protocollo si puo' depositare senza indebolire "
                "la pre-registrazione, a condizione che le sezioni delle regole siano le "
                "stesse. E' una condizione da MISURARE riga per riga, non da affermare.",
        },
    }


# ===========================================================================
# cancelli
# ===========================================================================

def _git(radice: Path, *arg, esegui=None, byte=False):
    if esegui is not None:
        return esegui(list(arg))
    try:
        r = subprocess.run(["git"] + list(arg), cwd=str(radice), capture_output=True)
    except FileNotFoundError:
        raise Rifiuto("git non trovato nel PATH")
    if r.returncode != 0:
        raise Rifiuto("git %s uscito %d" % (" ".join(arg), r.returncode))
    return r.stdout if byte else r.stdout.decode("utf-8", "replace")


def cancelli_protocollo(radice: Path, esegui=None,
                        v11_sha: str = V11_SHA256, v11_byte: int = V11_BYTE,
                        v10_sha: str = V10_SHA256, v10_byte: int = V10_BYTE) -> list:
    """Invariati dal record 72 e riverificati: se uno di questi e' cambiato, il 72 non
    descrive piu' il disco e il 73 non puo' appoggiarsi a lui."""
    esiti = []

    p = radice / PREREG
    if not p.is_file():
        raise Rifiuto("il protocollo non e' sul disco: %s" % PREREG)
    dati = p.read_bytes()
    sha = sha256_bytes(dati)
    if sha != v11_sha or len(dati) != v11_byte:
        raise Rifiuto(
            "il protocollo non porta i byte che il record 72 ancora:\n  disco:      %s  %d "
            "byte\n  ancorato:   %s  %d byte\n  Se il documento e' stato modificato, il 72 va "
            "emendato prima del 73." % (sha, len(dati), v11_sha, v11_byte))
    esiti.append("v1.1 sul disco, invariata dal 72: %s  %d byte" % (sha, len(dati)))

    tracciati = set(r.strip().replace("\\", "/")
                    for r in _git(radice, "ls-files", esegui=esegui).splitlines() if r.strip())
    if PREREG in tracciati:
        raise Rifiuto("%s e' tracciato: la decisione del record 70 §i e' cambiata e va "
                      "emendata, non scavalcata" % PREREG)
    esiti.append("%s non tracciato, come il record 70 §i decide" % PREREG)

    righe = [r for r in _git(radice, "log", "--all", "--oneline", "--", PREREG,
                             esegui=esegui).splitlines() if r.strip()]
    if len(righe) != COMMIT_ATTESI:
        raise Rifiuto("commit sul percorso: %d, attesi %d\n%s"
                      % (len(righe), COMMIT_ATTESI, "\n".join(righe)[:400]))
    esiti.append("commit sul percorso: %d, come al 72" % len(righe))

    dati10 = _git(radice, "show", COMMIT_UNTRACK + "^:" + PREREG, esegui=esegui, byte=True)
    if isinstance(dati10, str):
        dati10 = dati10.encode("utf-8")
    sha10 = sha256_bytes(dati10)
    if sha10 != v10_sha or len(dati10) != v10_byte:
        raise Rifiuto("lo stato conservato da git non e' la v1.0 dichiarata:\n  git:        %s  "
                      "%d byte\n  dichiarato: %s  %d byte" % (sha10, len(dati10), v10_sha,
                                                              v10_byte))
    if sha10 == sha:
        raise Rifiuto("git conserva gli stessi byte del disco: il record direbbe il falso")
    esiti.append("git conserva la v1.0: %s  %d byte" % (sha10, len(dati10)))
    return esiti


def misura_origin(radice: Path, esegui=None, richiesto: bool = True) -> dict:
    """Misura, non assume: il record porta cio' che esce da qui. Se `origin/main` non esiste
    il record lo dichiara assente, invece di scrivere un numero."""
    try:
        commit = _git(radice, "rev-parse", "--short", ORIGIN_REF, esegui=esegui).strip()
        grezzo = _git(radice, "show", ORIGIN_REF + ":" + LEDGER_DEFAULT, esegui=esegui,
                      byte=True)
        if isinstance(grezzo, str):
            grezzo = grezzo.encode("utf-8")
        n = len(righe_json(grezzo))
    except Rifiuto:
        if richiesto:
            raise Rifiuto("non ho potuto misurare %s. Con --senza-origin il record dichiara "
                          "la misura non disponibile, invece di ometterla." % ORIGIN_REF)
        return {"ref": ORIGIN_REF, "commit": None, "record": None,
                "nota": "misura non disponibile al momento del record"}
    return {"ref": ORIGIN_REF, "commit": commit, "record": n}


def cancelli_record_superati(record: list) -> list:
    """Un record non supera cio' che non c'e': i testi superati devono esistere."""
    esiti = []
    if len(record) < 72:
        raise Rifiuto("il ledger non arriva al record 72")

    r70 = record[69]
    nv70 = r70.get("new_value")
    if not isinstance(nv70, dict) or ANCORA_70_CHIAVE not in nv70:
        raise Rifiuto("il record 70 non porta la chiave %r: il §v del 73 supererebbe un testo "
                      "che non esiste" % ANCORA_70_CHIAVE)
    if ANCORA_70 not in str(nv70[ANCORA_70_CHIAVE]):
        raise Rifiuto("il record 70 §iii non contiene il testo del differimento che il 73 "
                      "supera: %r" % ANCORA_70)
    esiti.append("record 70 §iii presente, col testo del differimento")

    r72 = record[71]
    nv72 = r72.get("new_value")
    if not isinstance(nv72, dict) or ANCORA_72_CHIAVE not in nv72:
        raise Rifiuto("il record 72 non porta la chiave %r" % ANCORA_72_CHIAVE)
    testo72 = str(nv72[ANCORA_72_CHIAVE])
    mancanti = [t for t in ANCORA_72_TESTI if t not in testo72]
    if mancanti:
        raise Rifiuto("il record 72 non dichiara le tre possibilita' come atteso: mancano %r"
                      % mancanti)
    if r72.get("prereg_sha256") != V11_SHA256 or r72.get("prereg_byte") != V11_BYTE:
        raise Rifiuto("il record 72 ancora byte diversi da quelli che il 73 riporta: %r / %r"
                      % (r72.get("prereg_sha256"), r72.get("prereg_byte")))
    esiti.append("record 72 presente, con le tre possibilita' e l'ancoraggio per byte")
    return esiti


def conta_citazioni(record: list) -> int:
    return sum(1 for r in record if "paper2_prereg_v1.md" in str(r.get("document", "")))


def cancelli_ledger(dati: bytes, attesi: int, controlla_sha: bool = True) -> tuple:
    prof = profilo_eol(dati)
    if controlla_sha:
        sha = sha256_bytes(dati)
        if sha != LEDGER_SHA256_ATTESO:
            raise Rifiuto("sha del ledger: %s, atteso %s" % (sha, LEDGER_SHA256_ATTESO))
        if len(dati) != LEDGER_BYTE_ATTESI:
            raise Rifiuto("byte del ledger: %d, attesi %d" % (len(dati), LEDGER_BYTE_ATTESI))
    record = righe_json(dati)
    if len(record) != attesi:
        raise Rifiuto("record sul disco: %d, attesi %d" % (len(record), attesi))
    if not prof["coda_terminata"]:
        raise Rifiuto("l'ultima riga del ledger non e' terminata: append non sicuro")
    if controlla_sha:
        if prof["crlf"] != EOL_CRLF_ATTESI or prof["lf"] != EOL_LF_ATTESI:
            raise Rifiuto("profilo dei fini riga: %d CRLF e %d LF, attesi %d e %d"
                          % (prof["crlf"], prof["lf"], EOL_CRLF_ATTESI, EOL_LF_ATTESI))
        if prof["righe_lf"] != EOL_RIGHE_LF_ATTESE:
            raise Rifiuto("le righe a LF sono %r, attese %r"
                          % (prof["righe_lf"], EOL_RIGHE_LF_ATTESE))
    nr = str(record[-1].get("numbering_rule", ""))
    if not nr.rstrip().endswith("record %d." % attesi):
        raise Rifiuto("l'ultimo record non si dichiara il %d" % attesi)
    return prof, record


def cancello_reference(p: Path) -> None:
    if not p.is_file():
        raise Rifiuto("reference assente: %s" % p)
    if sha256_bytes(p.read_bytes()) != REFERENCE_FILE_SHA256:
        raise Rifiuto("sha del reference non e' quello atteso")


# ===========================================================================
# append
# ===========================================================================

def serializza(record: dict, terminatore: bytes) -> bytes:
    linea = json.dumps(record, ensure_ascii=False, sort_keys=True)
    if "\n" in linea or "\r" in linea:
        raise Rifiuto("il record serializzato contiene un fine riga")
    return linea.encode("utf-8") + terminatore


def carica_deposito(p: Path) -> dict:
    if not p.is_file():
        raise Rifiuto("il file di misura del deposito non c'e': %s\n  Eseguire prima:\n    "
                      "python src\\paper2_append_amend73.py misura-deposito --out %s" % (p, p))
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise Rifiuto("il file di misura non e' JSON leggibile: %r" % e)


def applica(radice: Path, ledger: Path, reference: Path, deposito: Path,
            dry_run: bool, attesi: int, controlla_sha: bool = True,
            esegui_git=None, controlla_reference: bool = True,
            origin_richiesto: bool = True, **digest) -> tuple:
    vecchio = ledger.read_bytes()
    prof, record = cancelli_ledger(vecchio, attesi, controlla_sha)
    if controlla_reference:
        cancello_reference(reference)
    esiti = cancelli_record_superati(record)
    esiti += cancelli_protocollo(radice, esegui=esegui_git, **digest)
    esiti += cancello_deposito(carica_deposito(deposito))
    origin = misura_origin(radice, esegui=esegui_git, richiesto=origin_richiesto)
    esiti.append("%s: %s, %s record nel ledger pubblico contro %d in locale"
                 % (ORIGIN_REF, origin.get("commit"), origin.get("record"), len(record)))

    citanti = conta_citazioni(record)
    nuovo_record = costruisci_record(citanti, len(record), origin)
    terminatore = b"\r\n" if prof["ereditato"] == "crlf" else b"\n"
    linea = serializza(nuovo_record, terminatore)
    nuovo = vecchio + linea

    rapporto = {
        "sha_prima": sha256_bytes(vecchio), "byte_prima": len(vecchio),
        "sha_dopo": sha256_bytes(nuovo), "byte_dopo": len(nuovo),
        "byte_del_record": len(linea),
        "terminatore": "crlf" if terminatore == b"\r\n" else "lf",
        "cancelli": esiti + ["record che citano il prereg: %d su %d" % (citanti, len(record))],
    }
    if dry_run:
        rapporto["scritto"] = False
        return rapporto, nuovo_record

    fd, tmp = tempfile.mkstemp(dir=str(ledger.parent), prefix=".amend73_", suffix=".jsonl")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(nuovo)
        os.replace(tmp, str(ledger))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    riletto = ledger.read_bytes()
    if riletto[:len(vecchio)] != vecchio:
        raise Rifiuto("IL PREFISSO E' CAMBIATO: append-only violato. Ripristinare dal backup.")
    if riletto != nuovo:
        raise Rifiuto("i byte riletti non sono quelli scritti")
    rec = righe_json(riletto)
    if len(rec) != attesi + 1:
        raise Rifiuto("dopo l'append i record sono %d, attesi %d" % (len(rec), attesi + 1))
    if rec[-1] != nuovo_record:
        raise Rifiuto("il record riletto non e' quello inteso")
    if controlla_sha and profilo_eol(riletto)["righe_lf"] != EOL_RIGHE_LF_ATTESE:
        raise Rifiuto("le righe a LF sono cambiate")
    rapporto["scritto"] = True
    rapporto["record_dopo"] = len(rec)
    return rapporto, nuovo_record


# ===========================================================================
# selftest
# ===========================================================================

def _ledger_finto(n: int, righe_lf=(2, 3), cita=None, con70=True, con72=True) -> bytes:
    cita = n if cita is None else cita
    fuori = b""
    for i in range(1, n + 1):
        rec = {"item": "finto/%d" % i, "numbering_rule": "This is record %d." % i}
        if i <= cita:
            rec["document"] = "paper2_prereg_v1.md v1.1 — version DOI " + VERSION_DOI
        if i == 70 and con70:
            rec["new_value"] = {ANCORA_70_CHIAVE: "… e " + ANCORA_70 + ", cosi' che i referee …"}
        elif i == 70:
            rec["new_value"] = {"altro": "niente differimento qui"}
        if i == 72 and con72:
            rec["new_value"] = {ANCORA_72_CHIAVE: "restano tre possibilita': (a) …, (b) …, "
                                                  "(c) …. DICHIARATA come aperta."}
            rec["prereg_sha256"] = V11_SHA256
            rec["prereg_byte"] = V11_BYTE
        elif i == 72:
            rec["new_value"] = {"altro": "nessuna possibilita' dichiarata"}
        if i == n:
            rec["numbering_rule"] = "Questo e' il record %d." % n
        fuori += json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8") \
            + (b"\n" if i in righe_lf else b"\r\n")
    return fuori


def _rapporto_finto(**muta) -> dict:
    versioni = {}
    for rid, a in DEPOSITO_ATTESO.items():
        versioni[rid] = {
            "doi": a["doi"], "version": a["version"],
            "publication_date": a["publication_date"], "created": a["created"] + ".000000+00:00",
            "files": [{"key": f["key"], "size": f["size"], "sha256": f["sha256"],
                       "voci": f["voci"], "colpi": []} for f in a["files"]],
        }
    rapporto = {"strumento": "finto", "utc": ora_utc(), "concept_doi": CONCEPT_DOI,
                "version_doi": VERSION_DOI, "aghi": list(AGHI), "versioni": versioni,
                "voci_esaminate": VOCI_ESAMINATE, "protocollo_trovato": []}
    rapporto.update(muta)
    return rapporto


def _git_stub(commit=COMMIT_ATTESI, tracciato=False, v10=b"v1.0 finta",
              origin="40f72a8", origin_ledger=None, senza_origin=False):
    def esegui(arg):
        if arg[0] == "ls-files":
            return (PREREG + "\n") if tracciato else "\n"
        if arg[0] == "log":
            return "".join("abc%04d un commit\n" % i for i in range(commit))
        if arg[0] == "rev-parse":
            if senza_origin:
                raise Rifiuto("git rev-parse uscito 128")
            return origin + "\n"
        if arg[0] == "show":
            if arg[1].startswith(ORIGIN_REF):
                if senza_origin:
                    raise Rifiuto("git show uscito 128")
                return origin_ledger if origin_ledger is not None else _ledger_finto(55)
            return v10
        raise AssertionError("comando git non previsto: %r" % arg)
    return esegui


def _albero(base: Path, v11=b"v1.1 finta, piu' lunga") -> str:
    (base / "papers" / "paper2").mkdir(parents=True, exist_ok=True)
    (base / "src").mkdir(parents=True, exist_ok=True)
    (base / "logs").mkdir(parents=True, exist_ok=True)
    (base / PREREG).write_bytes(v11)
    return sha256_bytes(v11)


def selftest() -> int:
    ok, ko = 0, 0

    def controlla(nome, cond):
        nonlocal ok, ko
        if cond:
            ok += 1
        else:
            ko += 1
            print("  FAIL  %s" % nome)

    def rifiuta(nome, fn):
        nonlocal ok, ko
        try:
            fn()
        except Rifiuto:
            ok += 1
            return
        except Exception as e:  # noqa: BLE001
            ko += 1
            print("  FAIL  %s (eccezione sbagliata: %r)" % (nome, e))
            return
        ko += 1
        print("  FAIL  %s (non ha rifiutato)" % nome)

    # --- il record ---------------------------------------------------------- #
    origin = {"ref": ORIGIN_REF, "commit": "40f72a8", "record": 55}
    rec = costruisci_record(60, 72, origin)
    controlla("record: numbering_rule al 73", rec["numbering_rule"].endswith("record 73."))
    controlla("record: item della 6.3", rec["item"].startswith("6.3/"))
    controlla("record: emenda il 70 e il 72", rec["amends_records"] == [70, 72])
    controlla("record: marker",
              rec["rules"]["marker"] == "emendamento-73-il-deposito-non-contiene-il-protocollo")
    controlla("record: conteggi 72 -> 73",
              rec["counts_before"]["DOCUMENTED_AMENDMENTS"] == 72
              and rec["counts_after"]["DOCUMENTED_AMENDMENTS"] == 73)
    controlla("record: dichiara il protocollo ASSENTE dal deposito",
              rec["deposito"]["protocollo_presente"] is False
              and "ASSENTE" in rec["new_value"]["i_la_misura"]["il_protocollo"])
    controlla("record: porta le quattro versioni e le voci esaminate",
              rec["deposito"]["versioni"] == sorted(DEPOSITO_ATTESO)
              and rec["deposito"]["voci_esaminate"] == 1068)
    controlla("record: chiude le tre possibilita' del 72",
              "(a), (b) e (c) del 72 sono chiuse" in rec["new_value"]["ii_la_quarta_possibilita"])
    controlla("record: porta i digest dei sei file del deposito",
              len(rec["deposito"]["file_del_28_agosto"]) == 6)
    controlla("record: conferma il dodici del §9 dal ledger depositato",
              rec["deposito"]["ledger_depositato"]["record"] == 12)
    controlla("record: la frase «deposited 27 August» e' dichiarata falsa e NON corretta",
              "descrive quindi un commit" in
              rec["new_value"]["iii_che_cosa_dice_il_protocollo_di_se"]
              and "resta come sta" in rec["new_value"]["viii_what_is_NOT_done"])
    controlla("record: il confronto v1.0/v1.1 dice che le regole sono identiche",
              "identiche riga per riga" in
              rec["new_value"]["iv_le_due_versioni_del_protocollo_a_confronto"])
    controlla("record: la decisione su GitHub supera il 70 §iii",
              "SUPERA il §iii del record 70" in rec["new_value"]["v_decisione_github_periodico"])
    controlla("record: porta la misura di origin, non un numero fisso",
              rec["origin"]["commit"] == "40f72a8" and rec["origin"]["record"] == 55
              and "40f72a8" in rec["new_value"]["v_decisione_github_periodico"])
    controlla("record: Zenodo e Paper 1 all'ultimo punto della Fase 7",
              "ULTIMO punto della Fase 7" in rec["new_value"]["vi_decisione_zenodo_alla_sottomissione"]
              and "ULTIMO punto della Fase 7" in rec["new_value"]["vii_decisione_paper1_alla_sottomissione"])
    controlla("record: porta ancora l'ancoraggio per byte del protocollo",
              rec["prereg_sha256"] == V11_SHA256 and rec["prereg_byte"] == V11_BYTE)
    rec2 = costruisci_record(60, 72, {"ref": ORIGIN_REF, "commit": None, "record": None,
                                      "nota": "misura non disponibile al momento del record"})
    controlla("record: senza origin dichiara la misura non disponibile",
              rec2["origin"]["commit"] is None and "nota" in rec2["origin"])
    linea = serializza(rec, b"\r\n")
    controlla("serializza: una riga sola", linea.count(b"\n") == 1)
    controlla("serializza: chiavi ordinate",
              list(json.loads(linea[:-2].decode("utf-8"))) == sorted(rec))

    # --- cancello sul deposito ---------------------------------------------- #
    controlla("deposito: il rapporto conforme passa",
              len(cancello_deposito(_rapporto_finto())) == 5)
    controlla("deposito: 1068 voci attese", VOCI_ESAMINATE == 1068)
    r = _rapporto_finto()
    r["versioni"]["22148444"]["files"][3]["sha256"] = "0" * 64
    rifiuta("deposito: un digest cambiato rifiutato", lambda: cancello_deposito(r))
    r = _rapporto_finto()
    r["versioni"]["22148444"]["files"][3]["colpi"] = ["papers/paper2/paper2_prereg_v1.md"]
    rifiuta("deposito: il protocollo TROVATO rifiutato", lambda: cancello_deposito(r))
    r = _rapporto_finto()
    del r["versioni"]["21128857"]
    rifiuta("deposito: una versione in meno rifiutata", lambda: cancello_deposito(r))
    r = _rapporto_finto()
    r["versioni"]["99999"] = r["versioni"]["22148444"]
    rifiuta("deposito: una versione in piu' rifiutata", lambda: cancello_deposito(r))
    r = _rapporto_finto(voci_esaminate=1067)
    rifiuta("deposito: conteggio dei membri diverso rifiutato",
            lambda: cancello_deposito(r))
    r = _rapporto_finto(aghi=["prereg"])
    rifiuta("deposito: rapporto prodotto con altri termini rifiutato",
            lambda: cancello_deposito(r))
    r = _rapporto_finto(protocollo_trovato=[{"record_id": "22148444"}])
    rifiuta("deposito: verdetto di presenza rifiutato", lambda: cancello_deposito(r))
    r = _rapporto_finto()
    r["versioni"]["22148444"]["publication_date"] = "2026-09-01"
    rifiuta("deposito: data di pubblicazione diversa rifiutata",
            lambda: cancello_deposito(r))
    r = _rapporto_finto()
    r["versioni"]["22148444"]["files"] = r["versioni"]["22148444"]["files"][:5]
    rifiuta("deposito: un file in meno rifiutato", lambda: cancello_deposito(r))
    rifiuta("deposito: rapporto senza `versioni` rifiutato",
            lambda: cancello_deposito({"utc": "x"}))

    # --- misura-deposito, con la rete simulata ------------------------------ #
    def _finto_zip(nomi):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for n in nomi:
                z.writestr(n, "x")
        return buf.getvalue()

    zip_pulito = _finto_zip(["src/a.py", "results/b.jsonl"])
    zip_col_prereg = _finto_zip(["papers/paper2/paper2_prereg_v1.md"])

    def _rete(zipdati):
        def scarica(url):
            if url == API_VERSIONI:
                return json.dumps({"hits": {"hits": [{
                    "id": 22148444, "doi": VERSION_DOI, "created": "2026-08-28T18:07:52+00:00",
                    "metadata": {"version": "v3.0-paper2", "publication_date": "2026-08-28"},
                    "files": [{"key": "x.zip", "size": len(zipdati)}]}]}}).encode("utf-8")
            return zipdati
        return scarica

    m = misura_deposito(scarica=_rete(zip_pulito))
    controlla("misura: conta i membri e non trova niente",
              m["voci_esaminate"] == 2 and m["protocollo_trovato"] == []
              and m["versioni"]["22148444"]["files"][0]["sha256"] == sha256_bytes(zip_pulito))
    m = misura_deposito(scarica=_rete(zip_col_prereg))
    controlla("misura: se il protocollo c'e', lo riporta",
              [c["membri"] for c in m["protocollo_trovato"]]
              == [["papers/paper2/paper2_prereg_v1.md"]])
    controlla("misura: e allora il cancello rifiuta quel rapporto",
              _refiuta_silenzioso(lambda: cancello_deposito(m)))

    def _rete_corta(url):
        if url == API_VERSIONI:
            return json.dumps({"hits": {"hits": [{
                "id": 1, "doi": "x", "created": "2026-01-01T00:00:00+00:00",
                "metadata": {"version": "v", "publication_date": "2026-01-01"},
                "files": [{"key": "x.zip", "size": 999}]}]}}).encode("utf-8")
        return b"corto"
    rifiuta("misura: dimensione dichiarata diversa da quella scaricata",
            lambda: misura_deposito(scarica=_rete_corta))
    rifiuta("misura: risposta non nel formato atteso",
            lambda: misura_deposito(scarica=lambda u: b"{}"))

    # --- cancelli sui record superati --------------------------------------- #
    controlla("superati: ledger conforme passa",
              len(cancelli_record_superati(righe_json(_ledger_finto(72)))) == 2)
    rifiuta("superati: record 70 senza il differimento rifiutato",
            lambda: cancelli_record_superati(righe_json(_ledger_finto(72, con70=False))))
    rifiuta("superati: record 72 senza le tre possibilita' rifiutato",
            lambda: cancelli_record_superati(righe_json(_ledger_finto(72, con72=False))))
    rifiuta("superati: ledger troppo corto rifiutato",
            lambda: cancelli_record_superati(righe_json(_ledger_finto(71))))

    controlla("conta_citazioni: conta il campo document",
              conta_citazioni(righe_json(_ledger_finto(10, cita=7))) == 7)

    # --- cancelli su disco e git -------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha11 = _albero(base)
        d = dict(v11_sha=sha11, v11_byte=len(b"v1.1 finta, piu' lunga"),
                 v10_sha=sha256_bytes(b"v1.0 finta"), v10_byte=len(b"v1.0 finta"))
        controlla("protocollo: quattro righe di esito",
                  len(cancelli_protocollo(base, esegui=_git_stub(), **d)) == 4)
        rifiuta("protocollo tracciato rifiutato",
                lambda: cancelli_protocollo(base, esegui=_git_stub(tracciato=True), **d))
        rifiuta("numero di commit diverso rifiutato",
                lambda: cancelli_protocollo(base, esegui=_git_stub(commit=3), **d))
        rifiuta("digest del disco che non combacia col 72",
                lambda: cancelli_protocollo(base, esegui=_git_stub(),
                                            **dict(d, v11_sha="0" * 64)))
        o = misura_origin(base, esegui=_git_stub())
        controlla("origin: misurato dal ledger pubblico",
                  o["commit"] == "40f72a8" and o["record"] == 55)
        rifiuta("origin assente e richiesto: rifiutato",
                lambda: misura_origin(base, esegui=_git_stub(senza_origin=True)))
        o = misura_origin(base, esegui=_git_stub(senza_origin=True), richiesto=False)
        controlla("origin assente e non richiesto: dichiarato non disponibile",
                  o["commit"] is None and "nota" in o)

    # --- pipeline ------------------------------------------------------------ #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha11 = _albero(base)
        d = dict(v11_sha=sha11, v11_byte=len(b"v1.1 finta, piu' lunga"),
                 v10_sha=sha256_bytes(b"v1.0 finta"), v10_byte=len(b"v1.0 finta"))
        led = base / "src" / "amend.jsonl"
        led.write_bytes(_ledger_finto(72, cita=60))
        dep = base / "logs" / "dep.json"
        dep.write_text(json.dumps(_rapporto_finto()), encoding="utf-8")
        vecchio = led.read_bytes()
        r, nr = applica(base, led, None, dep, True, 72, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False, **d)
        controlla("dry-run: non scrive", led.read_bytes() == vecchio)
        controlla("dry-run: terminatore ereditato CRLF", r["terminatore"] == "crlf")
        controlla("dry-run: citanti presi dal ledger",
                  nr["new_value"]["i_la_misura"]["quanti_record_citano_il_prereg"] == 60)
        controlla("dry-run: origin nel rapporto dei cancelli",
                  any("40f72a8" in x for x in r["cancelli"]))
        rifiuta("conteggio dei record sbagliato", lambda: applica(
            base, led, None, dep, True, 71, controlla_sha=False,
            esegui_git=_git_stub(), controlla_reference=False, **d))
        rifiuta("file di misura assente rifiutato", lambda: applica(
            base, led, None, base / "logs" / "manca.json", True, 72, controlla_sha=False,
            esegui_git=_git_stub(), controlla_reference=False, **d))
        r, nr = applica(base, led, None, dep, False, 72, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False, **d)
        nuovo = led.read_bytes()
        controlla("apply: scritto", r["scritto"] is True)
        controlla("apply: prefisso invariato", nuovo[:len(vecchio)] == vecchio)
        controlla("apply: 73 record", len(righe_json(nuovo)) == 73)
        controlla("apply: righe a LF invariate",
                  profilo_eol(nuovo)["righe_lf"] == profilo_eol(vecchio)["righe_lf"])
        controlla("apply: record riletto identico", righe_json(nuovo)[-1] == nr)
        controlla("apply: nessun temporaneo residuo",
                  not list((base / "src").glob(".amend73_*")))
        rifiuta("apply due volte rifiutato", lambda: applica(
            base, led, None, dep, False, 72, controlla_sha=False,
            esegui_git=_git_stub(), controlla_reference=False, **d))

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


def _refiuta_silenzioso(fn) -> bool:
    try:
        fn()
    except Rifiuto:
        return True
    return False


# ===========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="record 73: il deposito non contiene il protocollo, e tre decisioni")
    ap.add_argument("comando", choices=["selftest", "misura-deposito", "applica"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--radice", default=".")
    ap.add_argument("--ledger", default=LEDGER_DEFAULT)
    ap.add_argument("--reference", default=REFERENCE_PATH_DEFAULT)
    ap.add_argument("--deposito", default=DEPOSITO_DEFAULT,
                    help="file di misura del deposito, prodotto da misura-deposito")
    ap.add_argument("--out", default=DEPOSITO_DEFAULT,
                    help="dove scrivere la misura (misura-deposito)")
    ap.add_argument("--attesi", type=int, default=ATTESI_DEFAULT)
    ap.add_argument("--senza-origin", action="store_true",
                    help="se origin/main non e' raggiungibile: il record lo dichiara")
    args = ap.parse_args(argv)

    if args.comando == "selftest":
        return selftest()

    radice = Path(args.radice)

    if args.comando == "misura-deposito":
        try:
            rapporto = misura_deposito()
        except Rifiuto as e:
            print("RIFIUTO: %s" % e)
            return 2
        out = radice / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rapporto, ensure_ascii=False, indent=1), encoding="utf-8")
        print("=== misura del deposito %s ===" % VERSION_DOI)
        for rid, v in sorted(rapporto["versioni"].items()):
            print("  %s  %s  %s  %d file"
                  % (rid, v["version"], v["publication_date"], len(v["files"])))
            for f in v["files"]:
                print("     %-30s %10d byte  %s…  %4d membri%s"
                      % (f["key"], f["size"], f["sha256"][:16], f["voci"],
                         ("  COLPI: %r" % f["colpi"]) if f["colpi"] else ""))
        print("  membri esaminati: %d" % rapporto["voci_esaminate"])
        print("  protocollo nel deposito: %s"
              % ("TROVATO — il record 73 va riscritto" if rapporto["protocollo_trovato"]
                 else "ASSENTE"))
        print("\nscritto: %s" % out)
        try:
            cancello_deposito(rapporto)
        except Rifiuto as e:
            print("\nATTENZIONE: la misura NON combacia con cio' che il record 73 dichiara.")
            print("  %s" % e)
            print("Il deposito e' cambiato dal 17 settembre: il record va riscritto, non "
                  "appeso.")
            return 2
        print("La misura combacia con cio' che il record 73 dichiara. Ora: applica --dry-run")
        return 0

    try:
        r, rec = applica(radice, radice / args.ledger, radice / args.reference,
                         radice / args.deposito, args.dry_run, args.attesi,
                         origin_richiesto=not args.senza_origin)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e)
        print("Nessun byte e' stato scritto.")
        return 2

    print("=== paper2_append_amend73 — record %d ===" % NUMERO_RECORD)
    for riga in r["cancelli"]:
        print("  [ok] %s" % riga)
    print("  prima: %s  %d byte" % (r["sha_prima"], r["byte_prima"]))
    print("  dopo:  %s  %d byte  (+%d, terminatore %s)"
          % (r["sha_dopo"], r["byte_dopo"], r["byte_del_record"], r["terminatore"]))
    if r["scritto"]:
        print("  record sul disco: %d" % r["record_dopo"])
        print("\nAppeso. Ora:")
        print("  python src\\paper2_patch_documented_amendments.py apply "
              "--file src\\paper2_freeze_verify.py --da %d --a %d"
              % (ATTESI_DEFAULT, NUMERO_RECORD))
        print("  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
        print("  python src\\paper2_patch_reproducibility.py dry-run   (voce 6.7)")
        print("\nPoi il commit tre, con pathspec esplicite, e il tag spostato.")
    else:
        print("\nDRY-RUN: nessun byte scritto. Il record che verrebbe appeso:")
        print(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

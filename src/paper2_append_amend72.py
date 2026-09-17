#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_append_amend72.py — record 72: il documento di pre-registrazione non e'
ancorato da nessun digest, e da qui lo e'.

Appende UN record a src\paper2_v1_amendments.jsonl. Modello `amend68`-`amend71`:
temporaneo piu' os.replace, e IL CANCELLO PRINCIPALE E' IL PREFISSO.

CHE COSA DICHIARA. Tutti i record del ledger portano
`document: paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444`.
E' una citazione per nome, versione e DOI: nessun record ne porta il digest. I
due sha che ogni record contiene — reference_file_sha256 e
reference_self_sha256 — sono del REFERENCE, non del protocollo.

E la v1.1 non e' mai stata committata. Due soli commit toccano quel percorso, e
in entrambi i byte sono quelli della v1.0. La v1.1 esiste in una copia su un
disco, senza storia in git e senza digest in nessun record. Questo record e'
il suo ancoraggio.

CANCELLI PROPRI DI QUESTO RECORD:
  - il protocollo su disco deve portare i byte dichiarati qui;
  - il percorso NON deve essere tracciato (papers/ e' fuori per decisione del
    record 70, e questo record non la cambia);
  - esattamente DUE commit devono toccare quel percorso in tutta la storia;
  - lo stato conservato da git al commit di untrack deve essere la v1.0 coi
    suoi byte, non la v1.1: e' cio' che rende la v1.1 non recuperabile da git.

NON FA: non deposita, non ri-deposita, non sposta niente dentro il
versionamento, non duplica la copia. La verifica del deposito Zenodo resta
aperta e dichiarata.

Sequenza:  selftest  ->  applica --dry-run  ->  applica
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
REFERENCE_PATH_DEFAULT = "src/paper2_v1_reference.json"
REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA256 = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

LEDGER_DEFAULT = "src/paper2_v1_amendments.jsonl"
LEDGER_SHA256_ATTESO = "7bfaf3d364ab5475482a3a2d21d764dc63d1df080a404ead4ee75c3e41b67e0d"
LEDGER_BYTE_ATTESI = 594444
ATTESI_DEFAULT = 71
NUMERO_RECORD = 72

EOL_CRLF_ATTESI = 65
EOL_LF_ATTESI = 6
EOL_RIGHE_LF_ATTESE = [8, 9, 10, 11, 13, 14]

PREREG = "papers/paper2/paper2_prereg_v1.md"
V11_SHA256 = "607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86"
V11_BYTE = 25319
V11_MTIME = "2026-08-28 20:13:04"
V10_SHA256 = "05cd32b20388fffd5372711880d4c11ef6dda32ff2ff7767e898d667e2a6c115"
V10_BYTE = 21430
COMMIT_IMPORTO = "73c8213"
COMMIT_UNTRACK = "900335e"
UNTRACK_UTC = "2026-08-28 18:23:40 +0200"
TAG_DEPOSITO = "v3.0-paper2"
COMMIT_TAG = "5c54807"
TAG_UTC = "2026-08-28 18:32:52 +0200"
VERSION_DOI = "10.5281/zenodo.22148444"
CONCEPT_DOI = "10.5281/zenodo.21128856"
COMMIT_ATTESI = 2


class Rifiuto(Exception):
    """Un cancello non e' passato. Nessun byte e' stato scritto."""


# ===========================================================================
# utilita' (identiche a amend68-amend71)
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
# il record
# ===========================================================================

def costruisci_record(n_record_che_lo_citano: int) -> dict:
    return {
        "document": "paper2_prereg_v1.md v1.1 — version DOI " + VERSION_DOI,
        "type": "protocol",
        "utc": ora_utc(),
        "item": "6.2/il_protocollo_pre_registrato_non_era_ancorato_per_byte",
        "key": "the_preregistration_protocol_had_no_digest_in_any_record_and_gets_one_here",
        "amends_records": [],
        "json_path": PREREG + "; src/paper2_v1_amendments.jsonl (campo document di ogni "
                     "record); results/paper2/remote_audit.json",
        "old_value":
            "Ogni record del ledger porta, nel campo `document`, la stringa "
            "«paper2_prereg_v1.md v1.1 — version DOI " + VERSION_DOI + "»: una citazione per "
            "nome, versione e DOI. I due digest che ogni record contiene, reference_file_sha256 "
            "e reference_self_sha256, sono del REFERENCE (src/paper2_v1_reference.json) e non "
            "del protocollo. Nessun record, in " + str(ATTESI_DEFAULT) + ", porta il digest del "
            "documento di pre-registrazione.",
        "reason":
            "Il protocollo e' il documento contro cui ogni misura di questo programma si "
            "dichiara, e finora era l'unico artefatto centrale senza ancoraggio per byte. Non e' "
            "una dimenticanza isolata: e' la conseguenza di due decisioni giuste prese in ordine "
            "sfortunato. `papers/` e' uscito dal versionamento col commit " + COMMIT_UNTRACK
            + " del " + UNTRACK_UTC + " — «manuscript sources and internal handoffs are not part "
            "of the code release» — e la v1.1 del protocollo e' stata scritta DOPO, alle "
            + V11_MTIME + ". Un file uscito dal versionamento smette di avere una storia nello "
            "stesso istante, e cio' che si scrive dopo non ce l'ha mai avuta. Il digest va "
            "quindi dove i digest di questo programma stanno: in un record.",
        "new_value": {
            "i_la_misura": {
                "sul_disco": "v1.1: " + PREREG + ", sha256 " + V11_SHA256 + ", " + str(V11_BYTE)
                             + " byte, mtime " + V11_MTIME + ". Il documento dichiara di se' "
                             "«Version 1.1 — 28 August 2026 (version 1.0 deposited 27 August "
                             "2026)».",
                "in_git": "Due soli commit toccano quel percorso in tutta la storia, su tutti i "
                          "rami: " + COMMIT_IMPORTO + " (importazione dei 49 file da "
                          "D:/projects/cauchy_3.0, 27 agosto) e " + COMMIT_UNTRACK + " "
                          "(untrack di papers/, " + UNTRACK_UTC + "). In entrambi i byte sono "
                          "quelli della v1.0: sha256 " + V10_SHA256 + ", " + str(V10_BYTE)
                          + " byte. La v1.1 NON e' recuperabile da git.",
                "nell_altro_albero": "La copia in D:/projects/cauchy_3.0 e' byte-identica alla "
                                     "v1.0 (" + V10_SHA256[:16] + "…). Quell'albero NON e' un "
                                     "repository — results/paper2/remote_audit.json registra "
                                     "`\"git\": null` per quella radice — quindi non aggiunge "
                                     "nessuna storia.",
                "la_cronologia": "Il tag del deposito, " + TAG_DEPOSITO + " = commit "
                                 + COMMIT_TAG + ", e' del " + TAG_UTC + ": un'ora e quaranta "
                                 "PRIMA dell'mtime della v1.1. Il tag non puo' contenere la "
                                 "v1.1, e non la conterrebbe comunque perche' papers/ era gia' "
                                 "fuori dal versionamento da nove minuti.",
                "quanti_record_lo_citano": n_record_che_lo_citano,
            },
            "ii_ancoraggio": "Questo record ancora la v1.1 per byte: sha256 " + V11_SHA256
                             + ", " + str(V11_BYTE) + " byte, alla data del 16 settembre 2026. "
                             "Da qui in avanti il campo `document` di ogni record ha un digest a "
                             "cui rimandare, e una copia che si degradasse o si perdesse sarebbe "
                             "rilevabile invece che silenziosa.",
            "iii_la_verifica_del_deposito_resta_aperta":
                "L'ancoraggio esterno del protocollo e' il version DOI " + VERSION_DOI + ", che "
                "identifica cio' che e' stato DEPOSITATO, non cio' che sta sul disco. Le due "
                "cose vanno confrontate leggendo la pagina del deposito — data di pubblicazione "
                "e dimensione del file — e finche' non e' fatto restano tre possibilita': (a) il "
                "deposito porta la v1.1 e allora il DOI ancora " + V11_SHA256[:16] + "… e la "
                "catena e' chiusa; (b) il deposito porta la v1.0, e allora i record citano una "
                "v1.1 che il DOI non identifica, e va depositata o dichiarata come revisione "
                "post-deposito; (c) il deposito e' stato aggiornato dopo, e va datato. "
                "DICHIARATA come aperta, non assunta in nessuna delle tre direzioni. Il concept "
                "DOI " + CONCEPT_DOI + " risolve sempre all'ultima versione e quindi non "
                "discrimina.",
            "iv_cosa_NON_cambia":
                "La decisione del record 70 resta: `papers/` sta FUORI dal versionamento e dal "
                "rilascio, perche' contiene i sorgenti dei paper e la corrispondenza con editore "
                "e referee. Ancorare per byte NON e' versionare, ed e' esattamente il meccanismo "
                "che il record 70 usa per gli altri otto documenti esclusi. Il protocollo e' il "
                "nono, ed e' quello che mancava.",
            "v_what_is_NOT_done":
                "Non e' stato depositato ne' ri-depositato niente. Nessuna copia e' stata "
                "duplicata, spostata o messa sotto versionamento. La v1.0 resta recuperabile da "
                "git al commit " + COMMIT_UNTRACK + "^, e questo record non la tocca. Il §5 di "
                "REPRODUCIBILITY.md dichiara come ancorare il LEDGER — «lo si calcoli sui record "
                "e non sui byte» — e non dice niente sul protocollo: la regola per il protocollo "
                "e' questo record, e va riportata in quel documento (voce 6.7).",
        },
        "evidence":
            "Misure del 16 settembre 2026. `Get-FileHash` su " + PREREG + ": " + V11_SHA256
            + ", " + str(V11_BYTE) + " byte. `git log --all --oneline --name-only -- "
            "\"*paper2_prereg_v1.md\"`: due commit, " + COMMIT_UNTRACK + " e " + COMMIT_IMPORTO
            + ". `git show " + COMMIT_UNTRACK + "^:" + PREREG + "` ricalcolato: " + V10_SHA256
            + ", " + str(V10_BYTE) + " byte, cioe' la v1.0. `Get-FileHash` sulla copia in "
            "D:/projects/cauchy_3.0: lo stesso digest della v1.0. `git log -1 " + TAG_DEPOSITO
            + "`: " + COMMIT_TAG + ", " + TAG_UTC + ". Ricerca dei due digest fra i record 13-22, "
            "che nominano il prereg accanto a uno sha: nessuno dei due compare, e gli sha di quei "
            "record sono del reference. I cancelli di questo script hanno riverificato dal disco "
            "e da git, immediatamente prima dell'append, i byte della v1.1, i byte della v1.0 "
            "conservata da git, il numero di commit sul percorso e il fatto che il percorso non "
            "sia tracciato.",
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
        "numbering_rule": "Il numero di un emendamento e' la sua POSIZIONE 1-based in questo "
                          "file. Questo e' il record %d." % NUMERO_RECORD,
        "rules": {
            "marker": "emendamento-72-ancoraggio-del-protocollo",
            "companion_documents": "REPRODUCIBILITY.md §1 e §5; checklist_paper2.md voce 6.2; "
                                   "paper2_stato.md",
            "il_documento_che_ogni_record_cita_va_ancorato_come_ogni_altra_cosa":
                "Un campo `document` ripetuto in ogni record non e' un ancoraggio: e' un nome. "
                "Il digest va accanto, almeno una volta, in un record.",
            "uscire_dal_versionamento_interrompe_la_storia_nell_istante":
                "Un file togliato da git conserva la sua storia fino a quel commit e nessuna "
                "dopo. Cio' che si scrive dopo l'untrack non e' mai stato versionato, e la "
                "differenza non si vede guardando il file.",
            "il_DOI_ancora_il_deposito_non_il_disco":
                "Un version DOI identifica i byte depositati. Coincidono con quelli su disco solo "
                "se nessuno ha toccato il file dopo il deposito, e questo va verificato, non "
                "assunto.",
            "ancorare_non_e_versionare":
                "Un documento puo' restare fuori dal versionamento e avere comunque un digest in "
                "un record. Le due decisioni sono indipendenti, e confonderle porta a scegliere "
                "fra pubblicare e poter verificare.",
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
    """I digest sono parametri solo perche' il selftest non puo' fabbricare un
    file con un dato sha256: in esercizio restano le costanti del record."""
    esiti = []

    p = radice / PREREG
    if not p.is_file():
        raise Rifiuto("il protocollo non e' sul disco: %s" % PREREG)
    dati = p.read_bytes()
    sha = sha256_bytes(dati)
    if sha != v11_sha or len(dati) != v11_byte:
        raise Rifiuto(
            "il protocollo non porta i byte dichiarati:\n  disco:      %s  %d byte\n"
            "  dichiarato: %s  %d byte\n  Se il documento e' stato modificato, rimisurare "
            "prima di ancorarlo." % (sha, len(dati), v11_sha, v11_byte))
    esiti.append("v1.1 sul disco: %s  %d byte" % (sha, len(dati)))

    tracciati = set(r.strip().replace("\\", "/")
                    for r in _git(radice, "ls-files", esegui=esegui).splitlines() if r.strip())
    if PREREG in tracciati:
        raise Rifiuto("%s e' tracciato: il record 72 direbbe il falso, e la decisione del "
                      "record 70 sarebbe stata cambiata" % PREREG)
    esiti.append("%s non tracciato, come il record 70 decide" % PREREG)

    righe = [r for r in _git(radice, "log", "--all", "--oneline", "--", PREREG,
                             esegui=esegui).splitlines() if r.strip()]
    if len(righe) != COMMIT_ATTESI:
        raise Rifiuto("commit sul percorso: %d, attesi %d\n%s"
                      % (len(righe), COMMIT_ATTESI, "\n".join(righe)[:400]))
    esiti.append("commit sul percorso: %d, gli ultimi due della sua storia" % len(righe))

    dati10 = _git(radice, "show", COMMIT_UNTRACK + "^:" + PREREG, esegui=esegui, byte=True)
    if isinstance(dati10, str):
        dati10 = dati10.encode("utf-8")
    sha10 = sha256_bytes(dati10)
    if sha10 != v10_sha or len(dati10) != v10_byte:
        raise Rifiuto(
            "lo stato conservato da git non e' la v1.0 dichiarata:\n  git:        %s  %d byte\n"
            "  dichiarato: %s  %d byte" % (sha10, len(dati10), v10_sha, v10_byte))
    if sha10 == sha:
        raise Rifiuto("git conserva gli stessi byte del disco: la v1.1 sarebbe recuperabile e "
                      "il record direbbe il falso")
    esiti.append("git conserva la v1.0: %s  %d byte, diversa dal disco" % (sha10, len(dati10)))

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


def applica(radice: Path, ledger: Path, reference: Path,
            dry_run: bool, attesi: int, controlla_sha: bool = True,
            esegui_git=None, controlla_reference: bool = True, **digest) -> tuple:
    vecchio = ledger.read_bytes()
    prof, record = cancelli_ledger(vecchio, attesi, controlla_sha)
    if controlla_reference:
        cancello_reference(reference)
    esiti = cancelli_protocollo(radice, esegui=esegui_git, **digest)

    nuovo_record = costruisci_record(conta_citazioni(record))
    terminatore = b"\r\n" if prof["ereditato"] == "crlf" else b"\n"
    linea = serializza(nuovo_record, terminatore)
    nuovo = vecchio + linea

    rapporto = {
        "sha_prima": sha256_bytes(vecchio), "byte_prima": len(vecchio),
        "sha_dopo": sha256_bytes(nuovo), "byte_dopo": len(nuovo),
        "byte_del_record": len(linea),
        "terminatore": "crlf" if terminatore == b"\r\n" else "lf",
        "cancelli": esiti + ["record che citano il prereg: %d su %d"
                             % (conta_citazioni(record), len(record))],
    }
    if dry_run:
        rapporto["scritto"] = False
        return rapporto, nuovo_record

    fd, tmp = tempfile.mkstemp(dir=str(ledger.parent), prefix=".amend72_", suffix=".jsonl")
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

def _ledger_finto(n: int, righe_lf=(2, 3), cita=None) -> bytes:
    cita = n if cita is None else cita
    fuori = b""
    for i in range(1, n + 1):
        rec = {"item": "finto/%d" % i, "numbering_rule": "This is record %d." % i}
        if i <= cita:
            rec["document"] = "paper2_prereg_v1.md v1.1 — version DOI " + VERSION_DOI
        if i == n:
            rec["numbering_rule"] = "Questo e' il record %d." % n
        fuori += json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8") \
            + (b"\n" if i in righe_lf else b"\r\n")
    return fuori


def _git_stub(commit=COMMIT_ATTESI, tracciato=False, v10=b"v1.0 finta"):
    def esegui(arg):
        if arg[0] == "ls-files":
            return (PREREG + "\n") if tracciato else "\n"
        if arg[0] == "log":
            return "".join("abc%04d un commit\n" % i for i in range(commit))
        if arg[0] == "show":
            return v10
        raise AssertionError("comando git non previsto: %r" % arg)
    return esegui


def _albero(base: Path, v11=b"v1.1 finta, piu' lunga") -> str:
    (base / "papers" / "paper2").mkdir(parents=True, exist_ok=True)
    (base / "src").mkdir(parents=True, exist_ok=True)
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
        except Exception as e:
            ko += 1
            print("  FAIL  %s (eccezione sbagliata: %r)" % (nome, e))
            return
        ko += 1
        print("  FAIL  %s (non ha rifiutato)" % nome)

    rec = costruisci_record(71)
    controlla("record: numbering_rule al 72", rec["numbering_rule"].endswith("record 72."))
    controlla("record: item della 6.2", rec["item"].startswith("6.2/"))
    controlla("record: non emenda nessuno", rec["amends_records"] == [])
    controlla("record: marker",
              rec["rules"]["marker"] == "emendamento-72-ancoraggio-del-protocollo")
    controlla("record: conteggi 71 -> 72",
              rec["counts_before"]["DOCUMENTED_AMENDMENTS"] == 71
              and rec["counts_after"]["DOCUMENTED_AMENDMENTS"] == 72)
    controlla("record: porta il digest del prereg in un campo proprio",
              rec["prereg_sha256"] == V11_SHA256 and rec["prereg_byte"] == V11_BYTE)
    controlla("record: il digest sta anche nel testo dell'ancoraggio",
              V11_SHA256 in rec["new_value"]["ii_ancoraggio"])
    controlla("record: distingue v1.1 e v1.0",
              V11_SHA256 in rec["new_value"]["i_la_misura"]["sul_disco"]
              and V10_SHA256 in rec["new_value"]["i_la_misura"]["in_git"])
    controlla("record: dichiara le tre possibilita' del deposito",
              all(x in rec["new_value"]["iii_la_verifica_del_deposito_resta_aperta"]
                  for x in ("(a)", "(b)", "(c)", "DICHIARATA come aperta")))
    controlla("record: non cambia la decisione del 70",
              "resta: `papers/` sta FUORI" in rec["new_value"]["iv_cosa_NON_cambia"])
    controlla("record: ancorare non e' versionare",
              "ancorare_non_e_versionare" in rec["rules"])
    controlla("record: porta il conteggio dei citanti",
              rec["new_value"]["i_la_misura"]["quanti_record_lo_citano"] == 71)
    linea = serializza(rec, b"\r\n")
    controlla("serializza: una riga sola", linea.count(b"\n") == 1)
    controlla("serializza: chiavi ordinate",
              list(json.loads(linea[:-2].decode("utf-8"))) == sorted(rec))

    controlla("conta_citazioni: conta il campo document",
              conta_citazioni(righe_json(_ledger_finto(10, cita=7))) == 7)

    # --- cancelli --------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha11 = _albero(base)
        d = dict(v11_sha=sha11, v11_byte=len(b"v1.1 finta, piu' lunga"),
                 v10_sha=sha256_bytes(b"v1.0 finta"), v10_byte=len(b"v1.0 finta"))
        esiti = cancelli_protocollo(base, esegui=_git_stub(), **d)
        controlla("cancelli: quattro righe di esito", len(esiti) == 4)
        rifiuta("prereg tracciato rifiutato",
                lambda: cancelli_protocollo(base, esegui=_git_stub(tracciato=True), **d))
        rifiuta("numero di commit diverso rifiutato",
                lambda: cancelli_protocollo(base, esegui=_git_stub(commit=3), **d))
        rifiuta("git che conserva gli stessi byte del disco",
                lambda: cancelli_protocollo(
                    base, esegui=_git_stub(v10=b"v1.1 finta, piu' lunga"),
                    **dict(d, v10_sha=sha11, v10_byte=d["v11_byte"])))
        rifiuta("digest del disco che non combacia",
                lambda: cancelli_protocollo(base, esegui=_git_stub(),
                                            **dict(d, v11_sha="0" * 64)))
        (base / PREREG).unlink()
        rifiuta("prereg assente dal disco",
                lambda: cancelli_protocollo(base, esegui=_git_stub(), **d))

    # --- pipeline --------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha11 = _albero(base)
        d = dict(v11_sha=sha11, v11_byte=len(b"v1.1 finta, piu' lunga"),
                 v10_sha=sha256_bytes(b"v1.0 finta"), v10_byte=len(b"v1.0 finta"))
        led = base / "src" / "amend.jsonl"
        led.write_bytes(_ledger_finto(71, cita=71))
        vecchio = led.read_bytes()
        r, nr = applica(base, led, None, True, 71, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False, **d)
        controlla("dry-run: non scrive", led.read_bytes() == vecchio)
        controlla("dry-run: terminatore ereditato CRLF", r["terminatore"] == "crlf")
        controlla("dry-run: il conteggio dei citanti viene dal ledger",
                  nr["new_value"]["i_la_misura"]["quanti_record_lo_citano"] == 71)
        controlla("dry-run: lo dichiara fra i cancelli",
                  any("record che citano il prereg: 71 su 71" in x for x in r["cancelli"]))
        rifiuta("conteggio dei record sbagliato", lambda: applica(
            base, led, None, True, 70, controlla_sha=False,
            esegui_git=_git_stub(), controlla_reference=False, **d))
        r, nr = applica(base, led, None, False, 71, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False, **d)
        nuovo = led.read_bytes()
        controlla("apply: scritto", r["scritto"] is True)
        controlla("apply: prefisso invariato", nuovo[:len(vecchio)] == vecchio)
        controlla("apply: 72 record", len(righe_json(nuovo)) == 72)
        controlla("apply: righe a LF invariate",
                  profilo_eol(nuovo)["righe_lf"] == profilo_eol(vecchio)["righe_lf"])
        controlla("apply: record riletto identico", righe_json(nuovo)[-1] == nr)
        controlla("apply: nessun temporaneo residuo",
                  not list((base / "src").glob(".amend72_*")))
        rifiuta("apply due volte rifiutato", lambda: applica(
            base, led, None, False, 71, controlla_sha=False,
            esegui_git=_git_stub(), controlla_reference=False, **d))

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


# ===========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="record 72: ancoraggio del protocollo")
    ap.add_argument("comando", choices=["selftest", "applica"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--radice", default=".")
    ap.add_argument("--ledger", default=LEDGER_DEFAULT)
    ap.add_argument("--reference", default=REFERENCE_PATH_DEFAULT)
    ap.add_argument("--attesi", type=int, default=ATTESI_DEFAULT)
    args = ap.parse_args(argv)

    if args.comando == "selftest":
        return selftest()

    radice = Path(args.radice)
    try:
        r, rec = applica(radice, radice / args.ledger, radice / args.reference,
                         args.dry_run, args.attesi)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e)
        print("Nessun byte e' stato scritto.")
        return 2

    print("=== paper2_append_amend72 — record %d ===" % NUMERO_RECORD)
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
        print("\nResta aperta la verifica del deposito: pagina del version DOI %s,"
              % VERSION_DOI)
        print("data di pubblicazione e dimensione del file del protocollo.")
    else:
        print("\nDRY-RUN: nessun byte scritto. Il record che verrebbe appeso:")
        print(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

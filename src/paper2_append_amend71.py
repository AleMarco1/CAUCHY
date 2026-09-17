#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_append_amend71.py — record 71: quattro citazioni irrisolte, quattro esiti.

Appende UN record a src\paper2_v1_amendments.jsonl. Modello `amend68`-`amend70`:
temporaneo piu' os.replace, e IL CANCELLO PRINCIPALE E' IL PREFISSO.

CHE COSA DICHIARA. Il censimento del rilascio dava quattro percorsi «citati e
non su disco», con lo stesso esito per tutti e quattro. Aperti uno per uno,
hanno quattro cause diverse: un errore di trascrizione, un nome che non e' mai
corrisposto a niente, una rimozione per causa, e un'assenza che il record che
la cita registra come proprio contenuto. Lo stesso esito di misura non e' una
diagnosi: il censimento misura, e chi legge apre.

EMENDA IL RECORD 70, che nel campo ix_what_is_NOT_done chiama «assente»
src/paper2_item13rev2.py — che e' citato con un nome sbagliato — «sparito»
src/paper2_letture_1punto.py — che non e' mai esistito — e «grafia sbagliata»
il percorso Quijote del record 43, che e' invece il percorso scritto in un
manifest e che il 43 cita per dichiararlo assente. Il 70 non si riscrive.

CANCELLI PROPRI DI QUESTO RECORD. Un record non si scrive prima che cio' che
dichiara sia vero:
  - src/paper2_item13_rev2.py deve esistere e essere tracciato, e
    src/paper2_item13rev2.py NON deve esistere;
  - src/paper2_letture_1punto.py non deve esistere ne' comparire in nessun
    commit di nessun ramo;
  - results/phase8_test2_permock.csv non deve esistere, e
    results/phase8_test2_permock_hodfit.csv deve esistere coi byte dichiarati;
  - il record 70 deve essere davvero il 70 e deve contenere le due frasi che
    questo record emenda: un emendamento senza bersaglio e' un errore.

Sequenza:  selftest  ->  applica --dry-run  ->  applica
Poi:       paper2_patch_documented_amendments.py apply --file
           src\paper2_freeze_verify.py --da 70 --a 71, e freeze_verify.
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
LEDGER_SHA256_ATTESO = "290da8016e3d5b82cea3543ad12a8529c338c8d974bd48d849a854278c733691"
LEDGER_BYTE_ATTESI = 583374
ATTESI_DEFAULT = 70
NUMERO_RECORD = 71

EOL_CRLF_ATTESI = 64
EOL_LF_ATTESI = 6
EOL_RIGHE_LF_ATTESE = [8, 9, 10, 11, 13, 14]

STRUMENTO_VERO = "src/paper2_item13_rev2.py"
STRUMENTO_CITATO = "src/paper2_item13rev2.py"
MAI_ESISTITO = "src/paper2_letture_1punto.py"
CSV_RIMOSSO = "results/phase8_test2_permock.csv"
CSV_SOPRAVVISSUTO = "results/phase8_test2_permock_hodfit.csv"
CSV_SHA16 = "ae733e1e2a74bfff"
CSV_BYTE = 10891
COMMIT_RIMOZIONE = "352e024"

# Le due frasi del record 70 che questo record emenda.
BERSAGLI_NEL_70 = ["paper2_item13rev2.py", "paper2_letture_1punto.py"]


class Rifiuto(Exception):
    """Un cancello non e' passato. Nessun byte e' stato scritto."""


# ===========================================================================
# utilita' (identiche a amend68-amend70)
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

def costruisci_record() -> dict:
    return {
        "document": "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444",
        "type": "protocol",
        "utc": ora_utc(),
        "item": "6.2/quattro_citazioni_irrisolte_aperte_una_per_una",
        "key": "four_unresolved_path_citations_four_different_causes",
        "amends_records": [70],
        "json_path": STRUMENTO_VERO + "; " + CSV_SOPRAVVISSUTO + "; "
                     "src/paper2_passata_1punto.py; src/paper2_boxcox_v2.py; "
                     "src/record54_contenuto.md; "
                     "results/paper2/ensemble_v1_manifest_records.jsonl",
        "old_value":
            "Il record 70, campo ix_what_is_NOT_done, elenca QUATTRO percorsi «citati e non su "
            "disco» come lavoro del 6.2, e ne caratterizza tre: "
            + STRUMENTO_CITATO + " «assente», " + MAI_ESISTITO + " «assente», e il percorso "
            "Quijote del record 43 come «la grafia del percorso, che in un punto omette la "
            "cartella intermedia e quindi non risolve». Il censimento del rilascio dava per "
            "tutti e quattro lo stesso esito, `assente`.",
        "reason":
            "Lo stesso esito di misura non e' una diagnosi. Aperti uno per uno, i quattro "
            "percorsi hanno quattro cause diverse, e tre delle caratterizzazioni del record 70 "
            "sono sbagliate: una perche' lo strumento esiste sotto un nome di un carattere "
            "diverso, una perche' il nome non e' mai corrisposto a niente — e quindi «sparito» "
            "attribuisce una perdita che non c'e' stata — e una perche' l'assenza e' il "
            "CONTENUTO della citazione, non un suo difetto. Un percorso citato che non risolve "
            "rende non tracciabile il numero che ci poggia, ed e' per questo che la voce 6.2 "
            "esiste; ma la riparazione dipende dalla causa, e la causa si legge, non si deduce "
            "dalla forma del nome.",
        "new_value": {
            "i_item13rev2_e_un_errore_di_trascrizione": {
                "citato_dal_record": 27,
                "cosa_dice_il_27": "«Points are defined in " + STRUMENTO_CITATO + ", LINE_A, "
                                   "which point_plan reads», e il json_path lo mette accanto a "
                                   "«prereg §4 (measurement grid, line A)» e al referee report §6.",
                "cosa_c_e_davvero": "Lo strumento e' " + STRUMENTO_VERO + " — con l'underscore — "
                                    "tracciato e presente. PRODUCE "
                                    "results/paper2/item13rev2_<REG>.jsonl, che invece si scrive "
                                    "SENZA underscore: il record ha copiato il nome dell'uscita "
                                    "al posto del nome dello strumento.",
                "la_catena_e_intera": "src/paper2_item12b_wbar.py porta "
                                      "DEFAULT_GRID = 'results/paper2/item13rev2_%s.jsonl' alla "
                                      "riga 91, e ogni record di results/paper2/item12b_{NGC,SGC}"
                                      ".jsonl porta grid_source: 'item13rev2_<REG>.jsonl'. I punti "
                                      "della griglia pre-registrata sono prodotti, letti e "
                                      "registrati: e' la citazione che sbaglia un carattere.",
                "esito": "Citazione da correggere nei documenti compagni. Nessun file da "
                         "ricostruire, nessuna misura in dubbio.",
            },
            "ii_letture_1punto_non_e_mai_esistito": {
                "citato_dal_record": 54,
                "misura": "`git log --all --diff-filter=DR` su quel percorso non trova nessuna "
                          "cancellazione ne' rinomina, e `git grep` a HEAD non lo trova in nessun "
                          "file. La stringa vive in quattro posti e nessuno e' codice: "
                          "src/paper2_append_amend54.py, src/record54_contenuto.md (la bozza del "
                          "record), il ledger, e il record 70 che la ripete.",
                "il_conteggio_appartiene_a_un_altro_strumento":
                    "La bozza scrive «via " + MAI_ESISTITO + " (selftest 31/31)». Il 31/31 e' di "
                    "src/paper2_boxcox_v2.py, come src/paper2_append_amend57.py documenta alla "
                    "lettera per la voce 4.2b-5 col 9 settembre 2026. "
                    "src/paper2_passata_1punto.py non ha mai avuto 31 controlli: la sua versione "
                    "al commit 0dc0225 ne conta gia' 43, come quella di oggi.",
                "chi_fa_il_lavoro": "src/paper2_passata_1punto.py PRODUCE i registri "
                                    "onepoint_v1_{NGC,SGC}.jsonl, ha un sottocomando `desi` per la "
                                    "riga DESI nel suo file, e GENERA il sommario da se' "
                                    "(percorso_sommario affianca il file al registro, perche' un "
                                    "record senza idx dentro il registro sarebbe "
                                    "indistinguibile). Non c'era un quarto substrato da leggere "
                                    "altrove: leggere il sommario e i registri per estrarne "
                                    "quattro decisioni e' una lettura, non uno strumento.",
                "che_cosa_regge_la_provenienza_del_54":
                    "La passata, non un lettore: cancello di paper2_cancello_nu.py superato il 7 "
                    "settembre 2026 con max|d| = 0.000e+00 sui cubi congelati, due ancore di "
                    "riproduzione DISGIUNTE su NGC (50 record di delta da n1_spectra_NGC.jsonl, "
                    "1800 di nu da n1b_spectra_NGC.jsonl, tolleranza relativa 1e-5 dichiarata "
                    "prima di qualunque misura), e delta_sha256 riscontrato contro "
                    "cachedelta_manifest_<REG>.jsonl a ogni record.",
                "cio_che_git_non_puo_dire": "Che un file omonimo sia vissuto in locale fra due "
                                            "commit e sia stato rinominato o assorbito prima di "
                                            "essere committato. git vede solo cio' che e' stato "
                                            "committato, quindi un'assenza dalla storia non e' una "
                                            "prova di non-esistenza. DICHIARATO come ipotesi non "
                                            "verificabile, non escluso.",
                "esito": "Citazione da rimuovere dai documenti compagni e da sostituire con "
                         "src/paper2_passata_1punto.py. Il 31/31 non va attribuito a nessuno "
                         "strumento del record 54.",
            },
            "iii_il_csv_e_stato_rimosso_per_causa": {
                "citato_dai_record": [11, 12],
                "misura": "Commit " + COMMIT_RIMOZIONE + ": «Remove mislabelled per-mock CSV: "
                          "byte-identical to phase8_test2_permock_hodfit.csv, contains the "
                          "HOD-refit subset (35304.6 +/- 1033.0, N=200), not the test2 "
                          "baseline». La rimozione e' motivata e registrata in git.",
                "il_sopravvissuto": CSV_SOPRAVVISSUTO + ", " + CSV_SHA16 + ", " + str(CSV_BYTE)
                                    + " byte, dentro il tier congelato `records`.",
                "conseguenza_su_P_A1": "P-A1 del §8 di paper2_stato.md — «rimuovere "
                                       "phase8_test2_permock.csv e ricostruire il manifest "
                                       "records» — risulta ESEGUITO, e il tier records e' "
                                       "marcato `(emendato)` da freeze_verify. Il documento lo "
                                       "da' ancora aperto e bloccante per R2: e' la divergenza "
                                       "documento-contro-disco, non un lavoro da fare.",
                "esito": "I record 11 e 12 vanno indirizzati al sopravvissuto nei documenti "
                         "compagni. Nessun file da ricostruire.",
            },
            "iv_il_percorso_quijote_e_un_assenza_dichiarata": {
                "citato_dal_record": 43,
                "cosa_dice_il_43": "Nel campo evidence: «The manifest path "
                                   "data/raw/quijote/3D_cubes/latin_hypercube_nwLH_params.txt was "
                                   "confirmed absent at the time of writing, WHICH IS THE DEFECT "
                                   "THIS RECORD REGISTERS».",
                "lettura": "Il percorso senza la cartella intermedia e' quello scritto IN UN "
                           "MANIFEST, e il record esiste per dichiarare che non risolveva. "
                           "L'assenza e' il contenuto della citazione, come per "
                           "results/paper1/n10_phases_SGC.jsonl nel record 66. Il percorso che "
                           "risolve, data/raw/quijote/3D_cubes/latin_hypercube_nwLH/"
                           "latin_hypercube_nwLH_params.txt, e' citato dai record 4, 43 e 62 ed "
                           "e' ancorato dal 43 per digest.",
                "esito": "Eccezione dichiarata nel censimento, non riparazione. Il record 70 lo "
                         "chiamava «grafia sbagliata»: e' emendato qui.",
            },
            "v_che_cosa_cambia_nel_record_70":
                "Il campo ix_what_is_NOT_done del record 70 resta agli atti e non si riscrive. "
                "Di esso: «" + STRUMENTO_CITATO + " (record 27, definisce i punti della griglia "
                "di misura pre-registrata)» va letto come citazione con un nome sbagliato, non "
                "come file assente; «" + MAI_ESISTITO + " (record 54)» va letto come nome mai "
                "corrisposto a un file, non come file sparito; «la grafia del percorso Quijote "
                "dentro il record 43» va letta come assenza dichiarata dal 43 stesso. Il conteggio "
                "di quattro percorsi irrisolti resta corretto come misura del censimento: quello "
                "che cambia e' la diagnosi di tre di essi.",
            "vi_what_is_NOT_done":
                "Nessun file e' stato creato, rinominato o ricostruito. Nessun record precedente "
                "e' stato riscritto. I documenti compagni non sono ancora aggiornati: checklist e "
                "paper2_stato.md non portano i record 69, 70 e 71, e la voce 6.3 della checklist "
                "porta ancora il nome di tag superato. Il censimento del rilascio continuera' a "
                "dare `assente` sui quattro percorsi — e' l'esito giusto per un percorso che non "
                "risolve — e i due che restano senza eccezione, " + STRUMENTO_CITATO + " e "
                + MAI_ESISTITO + ", la avranno quando i documenti porteranno la correzione: "
                "un'eccezione su una citazione sbagliata la nasconderebbe invece di correggerla.",
        },
        "evidence":
            "Misure del 16 set 2026. `git log --all --oneline --name-status --diff-filter=DR` sui "
            "tre percorsi: una sola cancellazione, " + CSV_RIMOSSO + " al commit "
            + COMMIT_RIMOZIONE + ". `git grep -n` a HEAD: `item13rev2` compare nei record di "
            "results/paper2/item12b_{NGC,SGC}.jsonl come grid_source e in "
            "src/paper2_item12b_wbar.py righe 91 e 454; `letture_1punto` in nessun file di codice. "
            "`git ls-files src` porta " + STRUMENTO_VERO + " e non " + STRUMENTO_CITATO + ". "
            "`git log --all -S '31/31' --name-only`: la stringa compare in "
            "src/paper2_append_amend57.py, src/paper2_append_amend54.py, "
            "src/record54_contenuto.md e nel ledger. Selftest eseguiti: "
            "src/paper2_passata_1punto.py 43/43 oggi e 43/43 alla sua versione in 0dc0225, "
            "src/paper2_boxcox_v2.py 31/31, src/paper2_cancello_nu.py 26/26. "
            "REPRODUCIBILITY.md §5 dichiara " + CSV_SOPRAVVISSUTO + " nel tier records con "
            + CSV_SHA16 + " e " + str(CSV_BYTE) + " byte. I cancelli di questo script hanno "
            "riverificato dal disco, immediatamente prima dell'append, l'esistenza dello "
            "strumento vero, l'assenza dei due percorsi non risolti e i byte del sopravvissuto.",
        "counts_before": {"DOCUMENTED_AMENDMENTS": 70, "ledger_su_disco": 70},
        "counts_after": {"DOCUMENTED_AMENDMENTS": 71, "ledger_su_disco": 71},
        "counts_note": "Regola del record 67: un campo di conteggi porta il numero che i "
                       "documenti avranno DOPO i patcher. DOCUMENTED_AMENDMENTS va portato a 71 "
                       "da paper2_patch_documented_amendments.py.",
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": REFERENCE_FILE_SHA256,
        "reference_self_sha256": REFERENCE_SELF_SHA256,
        "numbering_rule": "Il numero di un emendamento e' la sua POSIZIONE 1-based in questo "
                          "file. Questo e' il record %d." % NUMERO_RECORD,
        "rules": {
            "marker": "emendamento-71-quattro-citazioni-irrisolte",
            "companion_documents": "checklist_paper2.md voci 6.2 e 6.3; paper2_stato.md §8 (P-A1); "
                                   "REPRODUCIBILITY.md §5",
            "scope_of_the_amendment": "Emenda la caratterizzazione di tre dei quattro percorsi nel "
                                      "campo ix_what_is_NOT_done del record 70. Non tocca il record "
                                      "27, il 43, il 54, l'11 e il 12: le loro citazioni restano "
                                      "agli atti come sono, e la correzione va nei documenti.",
            "lo_stesso_esito_non_e_una_diagnosi":
                "Un censimento misura: quattro percorsi non risolti escono tutti `assente`, ed e' "
                "corretto. La causa si legge aprendo, e puo' essere diversa per ognuno.",
            "un_nome_si_verifica_sul_disco":
                "Un carattere di differenza fra il nome dello strumento e il nome della sua uscita "
                "basta a rendere non tracciabile una misura tracciabile. Quando un record nomina "
                "un file, il nome va copiato da `ls-files`, non dalla memoria.",
            "un_conteggio_di_selftest_appartiene_a_uno_strumento_solo":
                "«selftest 31/31» e' un'ancora: identifica una versione di uno strumento. "
                "Attaccarlo al nome sbagliato crea una prova apparente di un'esecuzione che non "
                "c'e' stata.",
            "git_non_prova_la_non_esistenza":
                "git vede solo cio' che e' stato committato. Un file nato e ribattezzato fra due "
                "commit e' invisibile alla storia, quindi «non compare in nessun commit» e' una "
                "misura, non una dimostrazione. La differenza si dichiara.",
        },
    }


# ===========================================================================
# cancelli
# ===========================================================================

def _git(radice: Path, *arg, esegui=None) -> str:
    if esegui is not None:
        return esegui(list(arg))
    try:
        r = subprocess.run(["git"] + list(arg), cwd=str(radice), capture_output=True)
    except FileNotFoundError:
        raise Rifiuto("git non trovato nel PATH")
    if r.returncode != 0:
        raise Rifiuto("git %s uscito %d" % (" ".join(arg), r.returncode))
    return r.stdout.decode("utf-8", "replace")


def cancelli_citazioni(radice: Path, record70: dict, esegui=None,
                       csv_sha16: str = CSV_SHA16, csv_byte: int = CSV_BYTE) -> list:
    """csv_sha16 e csv_byte sono parametri solo perche' il selftest non puo'
    fabbricare un file con un dato prefisso di sha256: in esercizio restano le
    costanti dichiarate nel record."""
    esiti = []

    if not (radice / STRUMENTO_VERO).is_file():
        raise Rifiuto("lo strumento vero non e' sul disco: %s" % STRUMENTO_VERO)
    tracciati = set(r.strip().replace("\\", "/")
                    for r in _git(radice, "ls-files", esegui=esegui).splitlines() if r.strip())
    if STRUMENTO_VERO not in tracciati:
        raise Rifiuto("%s non e' tracciato" % STRUMENTO_VERO)
    if (radice / STRUMENTO_CITATO).exists() or STRUMENTO_CITATO in tracciati:
        raise Rifiuto("%s esiste: il record 71 direbbe il falso" % STRUMENTO_CITATO)
    esiti.append("%s tracciato, %s assente" % (STRUMENTO_VERO, STRUMENTO_CITATO))

    if (radice / MAI_ESISTITO).exists() or MAI_ESISTITO in tracciati:
        raise Rifiuto("%s esiste: il record 71 direbbe il falso" % MAI_ESISTITO)
    storia = _git(radice, "log", "--all", "--oneline", "--", MAI_ESISTITO, esegui=esegui).strip()
    if storia:
        raise Rifiuto("%s compare nella storia:\n%s" % (MAI_ESISTITO, storia[:300]))
    esiti.append("%s assente dal disco e da tutta la storia" % MAI_ESISTITO)

    if (radice / CSV_RIMOSSO).exists():
        raise Rifiuto("%s esiste ancora: la rimozione non e' avvenuta" % CSV_RIMOSSO)
    p = radice / CSV_SOPRAVVISSUTO
    if not p.is_file():
        raise Rifiuto("il sopravvissuto non e' sul disco: %s" % CSV_SOPRAVVISSUTO)
    dati = p.read_bytes()
    sha = sha256_bytes(dati)
    if not sha.startswith(csv_sha16) or len(dati) != csv_byte:
        raise Rifiuto(
            "il sopravvissuto non porta i byte dichiarati: %s %d byte, attesi %s… %d byte"
            % (sha, len(dati), csv_sha16, csv_byte))
    esiti.append("%s %s… %d byte" % (CSV_SOPRAVVISSUTO, sha[:16], len(dati)))

    nr = str(record70.get("numbering_rule", ""))
    if not nr.rstrip().endswith("record %d." % ATTESI_DEFAULT):
        raise Rifiuto("l'ultimo record non si dichiara il %d" % ATTESI_DEFAULT)
    testo = json.dumps(record70, ensure_ascii=False)
    for bersaglio in BERSAGLI_NEL_70:
        if bersaglio not in testo:
            raise Rifiuto("il record 70 non contiene %r: emendamento senza bersaglio" % bersaglio)
    esiti.append("record 70: entrambi i bersagli dell'emendamento sono nel suo testo")

    return esiti


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
    return prof, record[-1]


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


def applica(radice: Path, ledger: Path, reference: Path, record: dict,
            dry_run: bool, attesi: int, controlla_sha: bool = True,
            esegui_git=None, controlla_reference: bool = True,
            csv_sha16: str = CSV_SHA16) -> dict:
    vecchio = ledger.read_bytes()
    prof, record70 = cancelli_ledger(vecchio, attesi, controlla_sha)
    if controlla_reference:
        cancello_reference(reference)
    esiti = cancelli_citazioni(radice, record70, esegui=esegui_git, csv_sha16=csv_sha16)

    terminatore = b"\r\n" if prof["ereditato"] == "crlf" else b"\n"
    linea = serializza(record, terminatore)
    nuovo = vecchio + linea

    rapporto = {
        "sha_prima": sha256_bytes(vecchio), "byte_prima": len(vecchio),
        "sha_dopo": sha256_bytes(nuovo), "byte_dopo": len(nuovo),
        "byte_del_record": len(linea),
        "terminatore": "crlf" if terminatore == b"\r\n" else "lf",
        "cancelli": esiti,
    }
    if dry_run:
        rapporto["scritto"] = False
        return rapporto

    fd, tmp = tempfile.mkstemp(dir=str(ledger.parent), prefix=".amend71_", suffix=".jsonl")
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
    if rec[-1] != record:
        raise Rifiuto("il record riletto non e' quello inteso")
    if controlla_sha and profilo_eol(riletto)["righe_lf"] != EOL_RIGHE_LF_ATTESE:
        raise Rifiuto("le righe a LF sono cambiate")
    rapporto["scritto"] = True
    rapporto["record_dopo"] = len(rec)
    return rapporto


# ===========================================================================
# selftest
# ===========================================================================

def _record70_finto(bersagli=True) -> dict:
    testo = ("Restano QUATTRO percorsi citati e non su disco: "
             + (STRUMENTO_CITATO + " (record 27), " + MAI_ESISTITO + " (record 54), "
                if bersagli else "niente, ")
             + "e la grafia del percorso Quijote dentro il record 43.")
    return {"item": "6.3/portata", "numbering_rule": "Questo e' il record 70.",
            "new_value": {"ix_what_is_NOT_done": testo}}


def _ledger_finto(n: int, righe_lf=(2, 3), record70=None) -> bytes:
    fuori = b""
    for i in range(1, n + 1):
        if i == n and record70 is not None:
            rec = record70
        else:
            rec = {"item": "finto/%d" % i, "numbering_rule": "This is record %d." % i}
        linea = json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8")
        fuori += linea + (b"\n" if i in righe_lf else b"\r\n")
    return fuori


def _git_stub(storia="", tracciato=True):
    def esegui(arg):
        if arg[0] == "ls-files":
            return (STRUMENTO_VERO + "\n") if tracciato else "\n"
        if arg[0] == "log":
            return storia
        raise AssertionError("comando git non previsto: %r" % arg)
    return esegui


def _albero(base: Path, csv_byte=CSV_BYTE, csv_dati=None,
            crea_citato=False, crea_mai_esistito=False, csv_rimosso=False) -> str:
    (base / "src").mkdir(parents=True, exist_ok=True)
    (base / "results").mkdir(parents=True, exist_ok=True)
    (base / STRUMENTO_VERO).write_bytes(b"# strumento vero\n")
    if crea_citato:
        (base / STRUMENTO_CITATO).write_bytes(b"# sbagliato\n")
    if crea_mai_esistito:
        (base / MAI_ESISTITO).write_bytes(b"# non deve esistere\n")
    if csv_rimosso:
        (base / CSV_RIMOSSO).write_bytes(b"x")
    dati = csv_dati if csv_dati is not None else b"\0" * csv_byte
    (base / CSV_SOPRAVVISSUTO).write_bytes(dati)
    return sha256_bytes(dati)[:16]


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

    rec = costruisci_record()
    controlla("record: numbering_rule al 71", rec["numbering_rule"].endswith("record 71."))
    controlla("record: item della 6.2", rec["item"].startswith("6.2/"))
    controlla("record: emenda il 70", rec["amends_records"] == [70])
    controlla("record: marker",
              rec["rules"]["marker"] == "emendamento-71-quattro-citazioni-irrisolte")
    controlla("record: conteggi 70 -> 71",
              rec["counts_before"]["DOCUMENTED_AMENDMENTS"] == 70
              and rec["counts_after"]["DOCUMENTED_AMENDMENTS"] == 71)
    controlla("record: quattro esiti piu' due chiusure", len(rec["new_value"]) == 6)
    controlla("record: i quattro percorsi sono nominati",
              all(p in json.dumps(rec, ensure_ascii=False) for p in
                  (STRUMENTO_CITATO, MAI_ESISTITO, CSV_RIMOSSO, "latin_hypercube_nwLH_params")))
    controlla("record: nomina lo strumento vero",
              STRUMENTO_VERO in rec["new_value"]["i_item13rev2_e_un_errore_di_trascrizione"]
              ["cosa_c_e_davvero"])
    controlla("record: attribuisce il 31/31 al boxcox",
              "paper2_boxcox_v2.py" in rec["new_value"]["ii_letture_1punto_non_e_mai_esistito"]
              ["il_conteggio_appartiene_a_un_altro_strumento"])
    controlla("record: dichiara il limite di git",
              "non e' una prova di non-esistenza"
              in rec["new_value"]["ii_letture_1punto_non_e_mai_esistito"]["cio_che_git_non_puo_dire"])
    controlla("record: P-A1 dichiarato eseguito",
              "ESEGUITO" in rec["new_value"]["iii_il_csv_e_stato_rimosso_per_causa"]
              ["conseguenza_su_P_A1"])
    controlla("record: il 43 registra la propria assenza",
              "THE DEFECT THIS RECORD REGISTERS"
              in rec["new_value"]["iv_il_percorso_quijote_e_un_assenza_dichiarata"]["cosa_dice_il_43"])
    controlla("record: non chiede eccezioni per le due citazioni sbagliate",
              "la nasconderebbe invece di correggerla" in rec["new_value"]["vi_what_is_NOT_done"])
    controlla("record: lo scope non tocca i record citati",
              "Non tocca il record 27" in rec["rules"]["scope_of_the_amendment"])
    linea = serializza(rec, b"\r\n")
    controlla("serializza: una riga sola", linea.count(b"\n") == 1)
    controlla("serializza: chiavi ordinate",
              list(json.loads(linea[:-2].decode("utf-8"))) == sorted(rec))

    # --- cancelli --------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha16 = _albero(base)
        r70 = _record70_finto()
        esiti = cancelli_citazioni(base, r70, esegui=_git_stub(), csv_sha16=sha16)
        controlla("cancelli: quattro righe di esito", len(esiti) == 4)
        rifiuta("strumento vero non tracciato",
                lambda: cancelli_citazioni(base, r70, esegui=_git_stub(tracciato=False),
                                           csv_sha16=sha16))
        rifiuta("record 70 senza i bersagli",
                lambda: cancelli_citazioni(base, _record70_finto(bersagli=False),
                                           esegui=_git_stub(), csv_sha16=sha16))
        rifiuta("record 70 che non si dichiara il 70",
                lambda: cancelli_citazioni(
                    base, dict(r70, numbering_rule="Questo e' il record 69."),
                    esegui=_git_stub(), csv_sha16=sha16))
        rifiuta("storia non vuota per il mai esistito",
                lambda: cancelli_citazioni(base, r70, csv_sha16=sha16,
                                           esegui=_git_stub(storia="abc1234 un commit\n")))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha16 = _albero(base, crea_citato=True)
        rifiuta("il nome sbagliato esiste sul disco",
                lambda: cancelli_citazioni(base, _record70_finto(), esegui=_git_stub(),
                                           csv_sha16=sha16))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha16 = _albero(base, crea_mai_esistito=True)
        rifiuta("il mai esistito esiste sul disco",
                lambda: cancelli_citazioni(base, _record70_finto(), esegui=_git_stub(),
                                           csv_sha16=sha16))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha16 = _albero(base, csv_rimosso=True)
        rifiuta("il csv rimosso c'e' ancora",
                lambda: cancelli_citazioni(base, _record70_finto(), esegui=_git_stub(),
                                           csv_sha16=sha16))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha16 = _albero(base, csv_byte=CSV_BYTE - 1)
        rifiuta("il sopravvissuto ha i byte sbagliati",
                lambda: cancelli_citazioni(base, _record70_finto(), esegui=_git_stub(),
                                           csv_sha16=sha16))
        rifiuta("il sopravvissuto ha lo sha sbagliato",
                lambda: cancelli_citazioni(base, _record70_finto(), esegui=_git_stub(),
                                           csv_sha16="0" * 16, csv_byte=CSV_BYTE - 1))

    # --- pipeline --------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sha16 = _albero(base)
        led = base / "src" / "amend.jsonl"
        led.write_bytes(_ledger_finto(70, record70=_record70_finto()))
        vecchio = led.read_bytes()
        r = applica(base, led, None, rec, True, 70, controlla_sha=False,
                    esegui_git=_git_stub(), controlla_reference=False, csv_sha16=sha16)
        controlla("dry-run: non scrive", led.read_bytes() == vecchio)
        controlla("dry-run: terminatore ereditato CRLF", r["terminatore"] == "crlf")
        rifiuta("conteggio dei record sbagliato", lambda: applica(
            base, led, None, rec, True, 69, controlla_sha=False,
            esegui_git=_git_stub(), controlla_reference=False, csv_sha16=sha16))
        r = applica(base, led, None, rec, False, 70, controlla_sha=False,
                    esegui_git=_git_stub(), controlla_reference=False, csv_sha16=sha16)
        nuovo = led.read_bytes()
        controlla("apply: scritto", r["scritto"] is True)
        controlla("apply: prefisso invariato", nuovo[:len(vecchio)] == vecchio)
        controlla("apply: 71 record", len(righe_json(nuovo)) == 71)
        controlla("apply: righe a LF invariate",
                  profilo_eol(nuovo)["righe_lf"] == profilo_eol(vecchio)["righe_lf"])
        controlla("apply: record riletto identico", righe_json(nuovo)[-1] == rec)
        controlla("apply: nessun temporaneo residuo",
                  not list((base / "src").glob(".amend71_*")))
        rifiuta("apply due volte rifiutato", lambda: applica(
            base, led, None, rec, False, 70, controlla_sha=False,
            esegui_git=_git_stub(), controlla_reference=False, csv_sha16=sha16))

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


# ===========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="record 71: quattro citazioni irrisolte")
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
        rec = costruisci_record()
        r = applica(radice, radice / args.ledger, radice / args.reference,
                    rec, args.dry_run, args.attesi)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e)
        print("Nessun byte e' stato scritto.")
        return 2

    print("=== paper2_append_amend71 — record %d ===" % NUMERO_RECORD)
    for riga in r["cancelli"]:
        print("  [ok] %s" % riga)
    print("  prima: %s  %d byte" % (r["sha_prima"], r["byte_prima"]))
    print("  dopo:  %s  %d byte  (+%d, terminatore %s)"
          % (r["sha_dopo"], r["byte_dopo"], r["byte_del_record"], r["terminatore"]))
    if r["scritto"]:
        print("  record sul disco: %d" % r["record_dopo"])
        print("\nAppeso. Ora:")
        print("  python src\\paper2_patch_documented_amendments.py apply "
              "--file src\\paper2_freeze_verify.py --da 70 --a 71")
        print("  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    else:
        print("\nDRY-RUN: nessun byte scritto. Il record che verrebbe appeso:")
        print(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

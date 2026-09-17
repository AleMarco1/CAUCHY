#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_append_amend74.py — record 74: le quattro citazioni irrisolte del record 71 diventano
quattro ECCEZIONI dichiarate, tre con il digest di cio' che la citazione intendeva; e la copia
rimossa dal commit 352e024 e' BYTE-IDENTICA al sopravvissuto, misurato.

Appende UN record a src\paper2_v1_amendments.jsonl. Modello `amend68`-`amend73`: temporaneo piu'
os.replace, e IL CANCELLO PRINCIPALE E' IL PREFISSO.

CHE COSA DECIDE. Il record 71 ha dato quattro cause a quattro citazioni che non risolvono. Il 16
settembre l'eccezione era stata RIFIUTATA, perche' avrebbe nascosto una citazione sbagliata non
ancora tracciata. Quel motivo e' caduto: il 71 le ha tracciate tutte e quattro, e il 17 settembre
tre delle quattro hanno un artefatto con un digest. Quindi l'eccezione non nasconde un FAIL: lo
sostituisce con un'ancora. La quarta dichiara un'assenza dimostrata da due metri indipendenti.

  | citato dal ledger                        | che cosa e'                          | ancora     |
  | data/.../3D_cubes/latin_..._params.txt   | grafia senza la cartella intermedia  | bf0519c6…  |
  | results/phase8_test2_permock.csv         | rimosso per causa da 352e024         | ae733e1e…  |
  | src/paper2_item13rev2.py                 | errore di trascrizione               | 4306e613…  |
  | src/paper2_letture_1punto.py             | mai esistito                         | nessuna    |

CHE COSA CORREGGE. Il record 70 §ix diceva «REPRODUCIBILITY.md §5 tratta un file di nome simile
ma non identico … va letto prima di dichiarare». L'istruzione era giusta e non e' stata seguita
fino al 17 settembre. Letto: i due file hanno lo STESSO sha256 e la stessa dimensione. Il §5
diceva che la copia byte-identica «non esiste», e la sua riscrittura del 17 diceva che il
sopravvissuto «non e' la stessa cosa»: sbagliate entrambe, nelle due direzioni opposte. Il
commit 352e024 non ha rimosso un dato, ha rimosso un'ETICHETTA SBAGLIATA su un duplicato.

CANCELLI PROPRI DI QUESTO RECORD:
  - il params Quijote sul disco al percorso con la cartella intermedia, col digest del record 43,
    e il percorso citato dal 43 NON sul disco: e' quello che rende la citazione irrisolvibile;
  - `src/paper2_item13_rev2.py` sul disco col suo digest, e la grafia senza underscore assente
    dal disco E dalla storia degli `A` su tutti i rami;
  - la copia rimossa recuperabile da `352e024^` col suo digest, il sopravvissuto sul disco, e
    I DUE CONFRONTATI BYTE PER BYTE: se non sono identici il record direbbe il falso;
  - `paper2_letture_1punto.py` assente da DUE popolazioni indipendenti — la storia degli `A` su
    tutti i rami e una camminata sul disco sotto la radice.

NON FA: non scrive il file delle eccezioni (lo fa `paper2_patch_eccezioni.py --con-record71`,
che rifiuta finche' questo record non esiste), non tocca `REPRODUCIBILITY.md` (voce 6.7, patcher
suo), non riscrive nessun record.

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
LEDGER_SHA256_ATTESO = "5f2f30f9eb7da9f377b7cecd5874fae180b29e6875645be39ad83892c6e67917"
LEDGER_BYTE_ATTESI = 613480
ATTESI_DEFAULT = 73
NUMERO_RECORD = 74

EOL_CRLF_ATTESI = 67
EOL_LF_ATTESI = 6
EOL_RIGHE_LF_ATTESE = [8, 9, 10, 11, 13, 14]

MARKER_73 = "emendamento-73-il-deposito-non-contiene-il-protocollo"

# --- i quattro percorsi, come il ledger li cita ---------------------------- #
CIT_PARAMS = "data/raw/quijote/3D_cubes/latin_hypercube_nwLH_params.txt"
CIT_PERMOCK = "results/phase8_test2_permock.csv"
CIT_ITEM13 = "src/paper2_item13rev2.py"
CIT_LETTURE = "src/paper2_letture_1punto.py"
QUATTRO = (CIT_PARAMS, CIT_PERMOCK, CIT_ITEM13, CIT_LETTURE)

# --- e cio' che la misura del 17 settembre ha trovato ---------------------- #
VERO_PARAMS = "data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt"
PARAMS_SHA = "bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e"
PARAMS_BYTE = 156070

VERO_ITEM13 = "src/paper2_item13_rev2.py"
ITEM13_SHA = "4306e613476d52287143bd7187e1f1d50f69eb969b3a6ca84ec0a25e86bd022b"
ITEM13_BYTE = 15885
ITEM13_CONSUMATORE = "src/paper2_item12b_wbar.py"

COMMIT_RIMOZIONE = "352e024"
VERO_PERMOCK = "results/phase8_test2_permock_hodfit.csv"
PERMOCK_SHA = "ae733e1e2a74bfffe19c4f9a3ef8fada16a9fa9a940ae20850e26b2b761f85bc"
PERMOCK_BYTE = 10891
PERMOCK_STORIA = "e17da7a (A), 684d1f3 (M), 352e024 (D)"
PERMOCK_CONTENUTO = "sottoinsieme HOD-refit, 35304.6 +/- 1033.0, N=200, non la baseline test2"

VERO_PASSATA = "src/paper2_passata_1punto.py"

RECORD_43 = 43
RECORD_71 = 71


class Rifiuto(Exception):
    """Un cancello non e' passato. Nessun byte e' stato scritto."""


# ===========================================================================
# utilita' (identiche a amend68-amend73)
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


# ===========================================================================
# cancelli
# ===========================================================================

def storia_aggiunti(radice: Path, esegui=None) -> set:
    """Tutti i percorsi mai AGGIUNTI su qualunque ramo. E' la popolazione esaustiva: una
    ricerca sul disco non dice niente su cio' che e' stato cancellato, e una sul ramo corrente
    non dice niente sugli altri."""
    fuori = _git(radice, "log", "--all", "--pretty=format:", "--diff-filter=A", "--name-only",
                 esegui=esegui)
    return set(r.strip().replace("\\", "/") for r in fuori.splitlines() if r.strip())


def cammina_disco(radice: Path, aghi) -> list:
    trovati = []
    for base, _dirs, files in os.walk(str(radice)):
        for nome in files:
            basso = nome.lower()
            if any(a in basso for a in aghi):
                p = Path(base) / nome
                try:
                    rel = p.relative_to(radice).as_posix()
                except ValueError:
                    rel = str(p)
                trovati.append(rel)
    return sorted(trovati)


def misura_disco(radice: Path, rel: str, sha: str, byte: int, etichetta: str) -> str:
    p = radice / rel
    if not p.is_file():
        raise Rifiuto("%s non e' sul disco: %s" % (etichetta, rel))
    dati = p.read_bytes()
    got = sha256_bytes(dati)
    if got != sha or len(dati) != byte:
        raise Rifiuto("%s non porta i byte dichiarati:\n  disco:      %s  %d byte\n"
                      "  dichiarato: %s  %d byte" % (etichetta, got, len(dati), sha, byte))
    return "%s: %s  %d byte" % (rel, got, len(dati))


def cancelli_quattro(radice: Path, esegui=None,
                     params=(PARAMS_SHA, PARAMS_BYTE),
                     item13=(ITEM13_SHA, ITEM13_BYTE),
                     permock=(PERMOCK_SHA, PERMOCK_BYTE)) -> tuple:
    """I digest sono parametri solo perche' il selftest non puo' fabbricare file con un dato
    sha256: in esercizio restano le costanti del record."""
    esiti = []
    aggiunti = storia_aggiunti(radice, esegui=esegui)

    # (1) il params Quijote: uno solo, al percorso con la cartella intermedia
    esiti.append("params Quijote, " + misura_disco(radice, VERO_PARAMS, params[0], params[1],
                                                   "il params Quijote"))
    if (radice / CIT_PARAMS).exists():
        raise Rifiuto("il percorso citato dal record 43 ESISTE (%s): allora non e' una grafia "
                      "sbagliata ma un secondo file, e l'eccezione direbbe il falso" % CIT_PARAMS)
    esiti.append("il percorso citato dal record %d non esiste: la grafia e' l'errore" % RECORD_43)

    # (2) item13_rev2: esiste col nome giusto, e la grafia sbagliata non e' mai stata aggiunta
    esiti.append("strumento item13, " + misura_disco(radice, VERO_ITEM13, item13[0], item13[1],
                                                     "paper2_item13_rev2.py"))
    if CIT_ITEM13 in aggiunti or (radice / CIT_ITEM13).exists():
        raise Rifiuto("%s esiste o e' stato aggiunto in un commit: non e' un errore di "
                      "trascrizione" % CIT_ITEM13)
    esiti.append("%s mai aggiunto in nessun ramo e assente dal disco" % CIT_ITEM13)

    # (3) la copia rimossa, e LA BYTE-IDENTITA'
    dati_rim = _git(radice, "show", COMMIT_RIMOZIONE + "^:" + CIT_PERMOCK, esegui=esegui,
                    byte=True)
    if isinstance(dati_rim, str):
        dati_rim = dati_rim.encode("utf-8")
    sha_rim = sha256_bytes(dati_rim)
    if sha_rim != permock[0] or len(dati_rim) != permock[1]:
        raise Rifiuto("la copia rimossa non porta i byte dichiarati:\n  git:        %s  %d byte\n"
                      "  dichiarato: %s  %d byte" % (sha_rim, len(dati_rim), permock[0],
                                                     permock[1]))
    p_sop = radice / VERO_PERMOCK
    if not p_sop.is_file():
        raise Rifiuto("il sopravvissuto non e' sul disco: %s" % VERO_PERMOCK)
    dati_sop = p_sop.read_bytes()
    if dati_sop != dati_rim:
        raise Rifiuto(
            "i due file NON sono byte-identici:\n  rimosso:      %s  %d byte\n"
            "  sopravvissuto: %s  %d byte\n  Il record 74 dichiara la byte-identita': se non "
            "c'e', va riscritto, non appeso."
            % (sha_rim, len(dati_rim), sha256_bytes(dati_sop), len(dati_sop)))
    esiti.append("copia rimossa da %s^ e sopravvissuto: BYTE-IDENTICI, %s  %d byte"
                 % (COMMIT_RIMOZIONE, sha_rim, len(dati_rim)))

    # (4) letture_1punto: assente da due popolazioni indipendenti
    if CIT_LETTURE in aggiunti:
        raise Rifiuto("%s E' stato aggiunto in un commit: non e' vero che non e' mai esistito"
                      % CIT_LETTURE)
    sul_disco = cammina_disco(radice, ("letture",))
    if sul_disco:
        raise Rifiuto("qualcosa che si chiama «letture» e' sul disco: %r" % sul_disco[:5])
    uno_punto = [p for p in cammina_disco(radice, ("1punto",)) if p.endswith(".py")]
    esiti.append("%s assente dalla storia degli `A` su tutti i rami E dal disco; gli unici "
                 "`1punto` sul disco: %s" % (CIT_LETTURE, ", ".join(uno_punto) or "nessuno"))
    passata = None
    if (radice / VERO_PASSATA).is_file():
        d = (radice / VERO_PASSATA).read_bytes()
        passata = {"percorso": VERO_PASSATA, "sha256": sha256_bytes(d), "byte": len(d)}
        esiti.append("sopravvissuto del 54: %s  %s  %d byte"
                     % (VERO_PASSATA, passata["sha256"], passata["byte"]))

    misure = {
        "params": {"citato": CIT_PARAMS, "vero": VERO_PARAMS, "sha256": params[0],
                   "byte": params[1]},
        "permock": {"citato": CIT_PERMOCK, "vero": VERO_PERMOCK, "sha256": sha_rim,
                    "byte": len(dati_rim), "byte_identici": True},
        "item13": {"citato": CIT_ITEM13, "vero": VERO_ITEM13, "sha256": item13[0],
                   "byte": item13[1]},
        "letture": {"citato": CIT_LETTURE, "vero": None, "uno_punto_sul_disco": uno_punto,
                    "passata": passata},
    }
    return esiti, misure


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
    if str(record[-1].get("rules", {}).get("marker", "")) != MARKER_73:
        raise Rifiuto("l'ultimo record non e' il 73: marker %r"
                      % record[-1].get("rules", {}).get("marker"))
    r71 = record[RECORD_71 - 1]
    citati = json.dumps(r71, ensure_ascii=False)
    mancanti = [p.rsplit("/", 1)[-1] for p in QUATTRO if p.rsplit("/", 1)[-1] not in citati]
    if mancanti:
        raise Rifiuto("il record 71 non nomina %r: il 74 decide su cio' che il 71 ha tracciato"
                      % mancanti)
    return prof, record


def cancello_reference(p: Path) -> None:
    if not p.is_file():
        raise Rifiuto("reference assente: %s" % p)
    if sha256_bytes(p.read_bytes()) != REFERENCE_FILE_SHA256:
        raise Rifiuto("sha del reference non e' quello atteso")


# ===========================================================================
# il record
# ===========================================================================

def costruisci_record(misure: dict) -> dict:
    return {
        "document": "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444",
        "type": "protocol",
        "utc": ora_utc(),
        "item": "6.2/quattro_eccezioni_dichiarate_e_la_copia_rimossa_era_byte_identica",
        "key": "the_four_unresolved_citations_become_declared_exceptions_three_with_a_digest",
        "amends_records": [],
        "json_path": "logs/eccezioni_rilascio.json; REPRODUCIBILITY.md §5; "
                     "papers/paper2/checklist_paper2.md voce 6.2; papers/paper2/paper2_stato.md",
        "old_value":
            "Il record 71 ha dato quattro cause a quattro citazioni che non risolvono, e le ha "
            "lasciate senza eccezione: il censimento del rilascio le segnala come `assente` e "
            "`citati_esistono` esce FAIL. La voce 6.2 della checklist, il 16 settembre, "
            "dichiarava che «un'eccezione su una citazione sbagliata la nasconderebbe invece di "
            "correggerla». E il record 70 §ix diceva: «REPRODUCIBILITY.md §5 tratta un file di "
            "nome simile ma non identico, phase8_test2_permock_hodfit.csv: va letto prima di "
            "dichiarare».",
        "reason":
            "Il motivo per cui l'eccezione era stata rifiutata e' caduto. Il 16 settembre "
            "avrebbe nascosto citazioni non ancora tracciate; il record 71 le ha tracciate "
            "tutte e quattro con la loro causa, e la misura del 17 ha trovato, per TRE delle "
            "quattro, l'artefatto che la citazione intendeva, col suo digest. Un'eccezione che "
            "porta il digest di cio' che si cercava non nasconde un FAIL: lo sostituisce con "
            "un'ancora. La quarta dichiara un'assenza dimostrata da due popolazioni "
            "indipendenti. E un FAIL permanente per disegno smette di discriminare: e' la "
            "ragione per cui il 16 settembre e' stata dichiarata come eccezione anche la voce "
            "del file delle eccezioni su se stesso.",
        "new_value": {
            "i_eccezione_params_quijote": {
                "citato_da": "record 43, 71",
                "citato_come": misure["params"]["citato"],
                "che_cosa_e": "Grafia che omette la cartella intermedia latin_hypercube_nwLH/ e "
                              "quindi non risolve. Il percorso citato NON esiste sul disco, "
                              "verificato; il file vero esiste in UNA sola copia sotto "
                              "data/raw/quijote, cercata per nome su tutto l'albero.",
                "il_file_vero": misure["params"]["vero"],
                "sha256": misure["params"]["sha256"],
                "byte": misure["params"]["byte"],
                "nota": "E' lo stesso digest che il record 43 dichiara: la citazione sbagliata "
                        "e il file ancorato sono la stessa cosa, e l'unica differenza e' la "
                        "grafia. Dato esterno Quijote, non nostro da redistribuire.",
            },
            "ii_eccezione_permock_e_la_byte_identita": {
                "citato_da": "record 11, 12, 70, 71",
                "citato_come": misure["permock"]["citato"],
                "che_cosa_e": "Rimosso PER CAUSA dal commit " + COMMIT_RIMOZIONE + ". Storia "
                              "completa del percorso: " + PERMOCK_STORIA + ". Recuperabile da "
                              + COMMIT_RIMOZIONE + "^, e recuperato per questa misura.",
                "il_file_vero": misure["permock"]["vero"],
                "sha256": misure["permock"]["sha256"],
                "byte": misure["permock"]["byte"],
                "byte_identici": True,
                "che_cosa_e_stato_rimosso":
                    "NON un dato: un'ETICHETTA. I due file hanno lo stesso sha256 e la stessa "
                    "dimensione — confrontati byte per byte dai cancelli di questo script — e il "
                    "messaggio del commit lo dice: «byte-identical to "
                    "phase8_test2_permock_hodfit.csv, contains the HOD-refit subset ("
                    + PERMOCK_CONTENUTO + ")». Il nome `permock` prometteva la baseline test2 e "
                    "il contenuto era il refit HOD. Il dato sopravvive UNA volta, sotto il nome "
                    "che lo descrive.",
                "correzione_di_due_documenti":
                    "Il §5 di REPRODUCIBILITY.md diceva che la copia byte-identica «non "
                    "esiste»: falso, e git la dichiara nel proprio messaggio di commit. La sua "
                    "riscrittura del 17 settembre diceva che il sopravvissuto «ha un nome simile "
                    "e non e' la stessa cosa»: falso nella direzione opposta, perche' ai byte e' "
                    "la stessa cosa. Sbagliate entrambe; la riga va riscritta col digest. E' "
                    "voce 6.7, riaperta per questa riga. L'istruzione del record 70 §ix — «va "
                    "letto prima di dichiarare» — era giusta e non e' stata seguita per un mese.",
            },
            "iii_eccezione_item13rev2": {
                "citato_da": "record 27, 70, 71",
                "citato_come": misure["item13"]["citato"],
                "che_cosa_e": "Errore di trascrizione: manca l'underscore. La grafia citata non "
                              "e' mai stata aggiunta in nessun commit di nessun ramo (storia "
                              "degli `A` su --all) e non e' sul disco.",
                "il_file_vero": misure["item13"]["vero"],
                "sha256": misure["item13"]["sha256"],
                "byte": misure["item13"]["byte"],
                "nota": "Produttore e consumatore confermati: lo strumento scrive "
                        "`item13rev2_<REG>.jsonl` — senza underscore, da cui la confusione — e "
                        + ITEM13_CONSUMATORE + " lo rilegge. I due registri prodotti, "
                        "results/paper2/item13rev2_{NGC,SGC}.jsonl, esistono e sono nel "
                        "rilascio.",
            },
            "iv_eccezione_letture_1punto": {
                "citato_da": "record 54, 70, 71",
                "citato_come": misure["letture"]["citato"],
                "che_cosa_e": "NON E' MAI ESISTITO, e questa e' l'unica delle quattro senza "
                              "un'ancora, perche' non c'e' niente da ancorare.",
                "due_metri_indipendenti":
                    "(1) la storia degli `A` su tutti i rami non lo contiene; (2) una camminata "
                    "sul disco sotto la radice del progetto non trova nessun file il cui nome "
                    "contenga «letture». Un metro solo non basta a dimostrare un'assenza: il "
                    "primo non vede cio' che non e' mai stato committato, il secondo non vede "
                    "cio' che e' stato cancellato.",
                "uno_punto_sul_disco": misure["letture"]["uno_punto_sul_disco"],
                "il_lavoro_lo_fa": misure["letture"]["passata"],
                "il_selftest_31_31": "appartiene a src/paper2_boxcox_v2.py. Attaccato al nome "
                                     "sbagliato creava la prova apparente di un'esecuzione mai "
                                     "avvenuta; la riga e' stata tolta da paper2_stato.md §9 il "
                                     "17 settembre con nota di rimozione.",
            },
            "v_che_cosa_NON_cambia":
                "I record 11, 12, 27, 43, 54, 70 e 71 restano leggibili come sono: il ledger e' "
                "append-only e le citazioni sbagliate NON si riscrivono. Le eccezioni non "
                "correggono i record: dichiarano, una volta e con un digest, che cosa la "
                "citazione intendeva. Il censimento passera' `citati_esistono` non perche' i "
                "percorsi siano comparsi, ma perche' la loro assenza e' spiegata e ancorata.",
            "vi_what_is_NOT_done":
                "Nessun file e' stato creato, spostato o rinominato; nessuna copia rimossa e' "
                "stata ripristinata. logs/eccezioni_rilascio.json NON e' stato scritto da questo "
                "script: lo scrive paper2_patch_eccezioni.py --con-record71, che rifiuta finche' "
                "questo record non esiste. REPRODUCIBILITY.md §5 NON e' stato corretto qui: e' "
                "la voce 6.7, riaperta per una riga.",
        },
        "evidence":
            "Misure del 17 settembre 2026, tutte rifatte dai cancelli di questo script "
            "immediatamente prima dell'append. `git log --all --pretty=format: --diff-filter=A "
            "--name-only` come popolazione esaustiva dei percorsi mai aggiunti: contiene "
            + VERO_ITEM13 + " e non " + CIT_ITEM13 + ", contiene " + CIT_PERMOCK + " e "
            + VERO_PERMOCK + ", non contiene " + CIT_LETTURE + ". `Get-FileHash` su "
            + VERO_PARAMS + ": " + PARAMS_SHA + ", " + str(PARAMS_BYTE) + " byte, unica copia "
            "sotto data/raw/quijote. `git show " + COMMIT_RIMOZIONE + "^:" + CIT_PERMOCK
            + "` ricalcolato: " + PERMOCK_SHA + ", " + str(PERMOCK_BYTE) + " byte, e il "
            "confronto byte per byte col sopravvissuto su disco da' IDENTICI. `git log --all "
            "--name-status` sul percorso rimosso: " + PERMOCK_STORIA + ". `Get-FileHash` su "
            + VERO_ITEM13 + ": " + ITEM13_SHA + ", " + str(ITEM13_BYTE) + " byte; "
            "`Select-String item13rev2_` trova la scrittura nello strumento e la rilettura in "
            + ITEM13_CONSUMATORE + ". Camminata sul disco per «letture»: nessun risultato. "
            "NOTA DI METODO: una ricerca per comportamento («0-199», «sottoinsieme») su src\\ ha "
            "restituito 51 file, cioe' una popolazione che non discrimina: il metro era "
            "sbagliato prima dei dati, ed e' la storia degli `A` che ha deciso.",
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
        "eccezioni_dichiarate": list(QUATTRO),
        "numbering_rule": "Il numero di un emendamento e' la sua POSIZIONE 1-based in questo "
                          "file. Questo e' il record %d." % NUMERO_RECORD,
        "rules": {
            "marker": "emendamento-74-quattro-eccezioni-e-la-copia-byte-identica",
            "companion_documents": "logs/eccezioni_rilascio.json; REPRODUCIBILITY.md §5; "
                                   "checklist_paper2.md voci 6.2 e 6.7; paper2_stato.md §8",
            "un_eccezione_che_porta_un_digest_non_nasconde_un_FAIL":
                "Dichiarare un percorso irrisolvibile e' nascondere qualcosa solo se non si sa "
                "che cosa intendeva. Quando si sa, e si scrive col digest, l'eccezione e' "
                "l'ancora che il record sbagliato non aveva.",
            "un_FAIL_permanente_per_disegno_smette_di_discriminare":
                "Un verdetto che si sa in anticipo che fallira' per sempre non distingue piu' "
                "un difetto nuovo da uno noto. Va chiuso con una dichiarazione, o il verdetto "
                "va cambiato.",
            "un_assenza_richiede_due_metri":
                "La storia dei commit non vede cio' che non e' mai stato committato; il disco "
                "non vede cio' che e' stato cancellato. Un'assenza si dichiara solo quando "
                "entrambi tacciono.",
            "un_nome_puo_essere_l_errore_invece_del_contenuto":
                "Due file byte-identici con nomi diversi non sono un duplicato di dati: sono un "
                "dato e un'etichetta, e quella sbagliata si rimuove. Chi legge il commit di "
                "rimozione come la rimozione di un dato conclude che il dato non esiste piu'.",
            "leggere_prima_di_dichiarare":
                "Il record 70 §ix diceva di leggere i due file prima di dichiarare, e la lettura "
                "e' arrivata un mese dopo. Nel frattempo due documenti hanno detto due cose "
                "opposte, entrambe false. Un'istruzione di lettura non scade.",
        },
    }


# ===========================================================================
# append
# ===========================================================================

def serializza(record: dict, terminatore: bytes) -> bytes:
    linea = json.dumps(record, ensure_ascii=False, sort_keys=True)
    if "\n" in linea or "\r" in linea:
        raise Rifiuto("il record serializzato contiene un fine riga")
    return linea.encode("utf-8") + terminatore


def applica(radice: Path, ledger: Path, reference: Path, dry_run: bool, attesi: int,
            controlla_sha: bool = True, esegui_git=None, controlla_reference: bool = True,
            **digest) -> tuple:
    vecchio = ledger.read_bytes()
    prof, record = cancelli_ledger(vecchio, attesi, controlla_sha)
    if controlla_reference:
        cancello_reference(reference)
    esiti, misure = cancelli_quattro(radice, esegui=esegui_git, **digest)

    nuovo_record = costruisci_record(misure)
    terminatore = b"\r\n" if prof["ereditato"] == "crlf" else b"\n"
    linea = serializza(nuovo_record, terminatore)
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
        return rapporto, nuovo_record

    fd, tmp = tempfile.mkstemp(dir=str(ledger.parent), prefix=".amend74_", suffix=".jsonl")
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

def _ledger_finto(n=ATTESI_DEFAULT, marker=MARKER_73, con71=True) -> bytes:
    fuori = b""
    for i in range(1, n + 1):
        rec = {"item": "finto/%d" % i, "numbering_rule": "This is record %d." % i,
               "rules": {"marker": "altro-%d" % i}}
        if i == RECORD_71 and con71:
            rec["new_value"] = {"quattro": ("latin_hypercube_nwLH_params.txt, "
                                            "phase8_test2_permock.csv, paper2_item13rev2.py, "
                                            "paper2_letture_1punto.py")}
        if i == n:
            rec["numbering_rule"] = "Questo e' il record %d." % n
            rec["rules"] = {"marker": marker}
        fuori += json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8") \
            + (b"\n" if i in (2, 3) else b"\r\n")
    return fuori


def _albero(base: Path, identici=True, params=b"params finto", item13=b"item13 finto",
            permock=b"permock finto", con_letture=False, con_params_citato=False) -> dict:
    for rel in (VERO_PARAMS, VERO_ITEM13, VERO_PERMOCK, VERO_PASSATA):
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
    (base / VERO_PARAMS).write_bytes(params)
    (base / VERO_ITEM13).write_bytes(item13)
    (base / VERO_PERMOCK).write_bytes(permock if identici else permock + b" diverso")
    (base / VERO_PASSATA).write_bytes(b"passata finta")
    if con_letture:
        (base / CIT_LETTURE).write_bytes(b"non dovrebbe esistere")
    if con_params_citato:
        (base / CIT_PARAMS).parent.mkdir(parents=True, exist_ok=True)
        (base / CIT_PARAMS).write_bytes(b"un secondo file")
    return dict(params=(sha256_bytes(params), len(params)),
                item13=(sha256_bytes(item13), len(item13)),
                permock=(sha256_bytes(permock), len(permock)))


def _git_stub(aggiunti=None, permock=b"permock finto"):
    righe = aggiunti if aggiunti is not None else [VERO_ITEM13, VERO_PERMOCK, VERO_PARAMS]

    def esegui(arg):
        if arg[0] == "log":
            return "".join(r + "\n" for r in righe)
        if arg[0] == "show":
            return permock
        raise AssertionError("comando git non previsto: %r" % arg)
    return esegui


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

    # --- cancelli sui quattro ---------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        d = _albero(base)
        esiti, misure = cancelli_quattro(base, esegui=_git_stub(), **d)
        controlla("cancelli: sette righe di esito", len(esiti) == 7)
        (base / VERO_PASSATA).unlink()
        controlla("cancelli: senza il sopravvissuto del 54 sono sei, e il record lo dichiara "
                  "assente",
                  len(cancelli_quattro(base, esegui=_git_stub(), **d)[0]) == 6
                  and cancelli_quattro(base, esegui=_git_stub(),
                                       **d)[1]["letture"]["passata"] is None)
        (base / VERO_PASSATA).write_bytes(b"passata finta")
        controlla("cancelli: byte-identita' dichiarata",
                  misure["permock"]["byte_identici"] is True)
        controlla("cancelli: il sopravvissuto del 54 e' misurato",
                  misure["letture"]["passata"]["percorso"] == VERO_PASSATA)
        controlla("cancelli: gli `1punto` trovati sono elencati",
                  misure["letture"]["uno_punto_sul_disco"] == [VERO_PASSATA])
        rifiuta("digest del params che non combacia",
                lambda: cancelli_quattro(base, esegui=_git_stub(),
                                         **dict(d, params=("0" * 64, 1))))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        d = _albero(base, identici=False)
        rifiuta("i due permock NON identici: rifiutato",
                lambda: cancelli_quattro(base, esegui=_git_stub(), **d))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        d = _albero(base, con_letture=True)
        rifiuta("letture_1punto trovato sul disco: rifiutato",
                lambda: cancelli_quattro(base, esegui=_git_stub(), **d))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        d = _albero(base)
        rifiuta("letture_1punto nella storia degli `A`: rifiutato",
                lambda: cancelli_quattro(
                    base, esegui=_git_stub(aggiunti=[VERO_ITEM13, CIT_LETTURE]), **d))
        rifiuta("la grafia sbagliata di item13 nella storia: rifiutata",
                lambda: cancelli_quattro(
                    base, esegui=_git_stub(aggiunti=[VERO_ITEM13, CIT_ITEM13]), **d))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        d = _albero(base, con_params_citato=True)
        rifiuta("il percorso citato dal 43 che ESISTE: rifiutato",
                lambda: cancelli_quattro(base, esegui=_git_stub(), **d))

    # --- il record ---------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        d = _albero(base)
        _, misure = cancelli_quattro(base, esegui=_git_stub(), **d)
        rec = costruisci_record(misure)
        controlla("record: numbering_rule al 74", rec["numbering_rule"].endswith("record 74."))
        controlla("record: item della 6.2", rec["item"].startswith("6.2/"))
        controlla("record: marker",
                  rec["rules"]["marker"] ==
                  "emendamento-74-quattro-eccezioni-e-la-copia-byte-identica")
        controlla("record: conteggi 73 -> 74",
                  rec["counts_before"]["DOCUMENTED_AMENDMENTS"] == 73
                  and rec["counts_after"]["DOCUMENTED_AMENDMENTS"] == 74)
        controlla("record: dichiara le quattro eccezioni",
                  rec["eccezioni_dichiarate"] == list(QUATTRO))
        controlla("record: tre portano un digest, la quarta no",
                  all("sha256" in rec["new_value"][k] for k in
                      ("i_eccezione_params_quijote", "ii_eccezione_permock_e_la_byte_identita",
                       "iii_eccezione_item13rev2"))
                  and "sha256" not in rec["new_value"]["iv_eccezione_letture_1punto"])
        controlla("record: la byte-identita' e' nel record",
                  rec["new_value"]["ii_eccezione_permock_e_la_byte_identita"]["byte_identici"]
                  is True)
        controlla("record: dichiara sbagliate ENTRAMBE le versioni del §5",
                  "falso nella direzione opposta" in
                  rec["new_value"]["ii_eccezione_permock_e_la_byte_identita"]
                  ["correzione_di_due_documenti"])
        controlla("record: i due metri dell'assenza",
                  "due_metri_indipendenti" in rec["new_value"]["iv_eccezione_letture_1punto"])
        controlla("record: non emenda nessun record e lo dice",
                  rec["amends_records"] == []
                  and "append-only" in rec["new_value"]["v_che_cosa_NON_cambia"])
        controlla("record: dichiara che non scrive il file delle eccezioni",
                  "NON e' stato scritto da questo script" in
                  rec["new_value"]["vi_what_is_NOT_done"])
        controlla("record: la nota di metodo sul metro sbagliato c'e'",
                  "NOTA DI METODO" in rec["evidence"])
        controlla("record: la regola di lettura del 70 §ix",
                  "leggere_prima_di_dichiarare" in rec["rules"])
        linea = serializza(rec, b"\r\n")
        controlla("serializza: una riga sola", linea.count(b"\n") == 1)
        controlla("serializza: chiavi ordinate",
                  list(json.loads(linea[:-2].decode("utf-8"))) == sorted(rec))

    # --- ledger ------------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        led = base / "led.jsonl"
        led.write_bytes(_ledger_finto())
        prof, record = cancelli_ledger(led.read_bytes(), 73, controlla_sha=False)
        controlla("ledger finto: 73 record col marker del 73", len(record) == 73)
        led.write_bytes(_ledger_finto(marker="altro"))
        rifiuta("ultimo record che non e' il 73: rifiutato",
                lambda: cancelli_ledger(led.read_bytes(), 73, controlla_sha=False))
        led.write_bytes(_ledger_finto(con71=False))
        rifiuta("record 71 che non nomina i quattro: rifiutato",
                lambda: cancelli_ledger(led.read_bytes(), 73, controlla_sha=False))
        led.write_bytes(_ledger_finto(n=72))
        rifiuta("ledger a 72: rifiutato",
                lambda: cancelli_ledger(led.read_bytes(), 73, controlla_sha=False))

    # --- pipeline ----------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        d = _albero(base)
        led = base / "src" / "amend.jsonl"
        led.parent.mkdir(parents=True, exist_ok=True)
        led.write_bytes(_ledger_finto())
        vecchio = led.read_bytes()
        r, nr = applica(base, led, None, True, 73, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False, **d)
        controlla("dry-run: non scrive", led.read_bytes() == vecchio)
        controlla("dry-run: terminatore ereditato CRLF", r["terminatore"] == "crlf")
        rifiuta("conteggio dei record sbagliato", lambda: applica(
            base, led, None, True, 72, controlla_sha=False, esegui_git=_git_stub(),
            controlla_reference=False, **d))
        r, nr = applica(base, led, None, False, 73, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False, **d)
        nuovo = led.read_bytes()
        controlla("apply: scritto", r["scritto"] is True)
        controlla("apply: prefisso invariato", nuovo[:len(vecchio)] == vecchio)
        controlla("apply: 74 record", len(righe_json(nuovo)) == 74)
        controlla("apply: righe a LF invariate",
                  profilo_eol(nuovo)["righe_lf"] == profilo_eol(vecchio)["righe_lf"])
        controlla("apply: record riletto identico", righe_json(nuovo)[-1] == nr)
        controlla("apply: nessun temporaneo residuo",
                  not list((base / "src").glob(".amend74_*")))
        rifiuta("apply due volte rifiutato", lambda: applica(
            base, led, None, False, 73, controlla_sha=False, esegui_git=_git_stub(),
            controlla_reference=False, **d))

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


# ===========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="record 74: quattro eccezioni dichiarate, tre con un digest")
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

    print("=== paper2_append_amend74 — record %d ===" % NUMERO_RECORD)
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
        print("  python src\\paper2_patch_eccezioni.py --con-record71 dry-run")
        print("  python src\\paper2_patch_repro_permock.py dry-run   (voce 6.7, una riga)")
    else:
        print("\nDRY-RUN: nessun byte scritto. Il record che verrebbe appeso:")
        print(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

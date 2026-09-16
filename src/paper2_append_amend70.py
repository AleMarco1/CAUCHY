#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_append_amend70.py — record 70: la portata del rilascio.

Appende UN record a src\paper2_v1_amendments.jsonl. Modello `amend68`/`amend69`:
temporaneo piu' os.replace, e IL CANCELLO PRINCIPALE E' IL PREFISSO — i primi
len(vecchio) byte del nuovo file identici byte per byte al vecchio.

CHE COSA DICHIARA. Che cosa il rilascio contiene, che cosa non contiene e
perche', e QUANDO diventa leggibile. Sei decisioni, gli otto digest dei file
citati dal ledger che restano fuori, e il nome del tag.

CANCELLI PROPRI DI QUESTO RECORD, oltre a quelli del ledger:
  - gli otto digest dichiarati devono combaciare col disco, ricalcolati adesso:
    un record che ancora dei byte non si scrive su una misura di ieri;
  - gli otto percorsi devono essere DAVVERO esclusi — ne' tracciati ne' offerti
    da git: se uno fosse visibile, la decisione non e' in forza e il record
    direbbe il falso;
  - `results/paper2/phase7_pk_nwlh_kref.npz` deve essere visibile o tracciato,
    perche' il record dichiara che e' stato riammesso;
  - `origin/main` deve portare 55 record, perche' il record dichiara che i
    56-69 sono ancora locali.

Sequenza:  selftest  ->  applica --dry-run  ->  applica
Poi:       paper2_patch_documented_amendments.py apply --file
           src\paper2_freeze_verify.py --da 69 --a 70, e freeze_verify.
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
# Ancore.
# ---------------------------------------------------------------------------
REFERENCE_PATH_DEFAULT = "src/paper2_v1_reference.json"
REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA256 = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

LEDGER_DEFAULT = "src/paper2_v1_amendments.jsonl"
LEDGER_SHA256_ATTESO = "01ff2e754e37761a05594b9d222c79836f7c0aa8cc508e27844220e4f8d2756e"
LEDGER_BYTE_ATTESI = 573436
ATTESI_DEFAULT = 69
NUMERO_RECORD = 70

EOL_CRLF_ATTESI = 63
EOL_LF_ATTESI = 6
EOL_RIGHE_LF_ATTESE = [8, 9, 10, 11, 13, 14]

RECORD_SU_ORIGIN = 55

# Gli otto citati dal ledger che restano fuori dal rilascio. Sorgente unica:
# il record li dichiara da qui, e il cancello li verifica da qui.
DIGEST_ATTESI = {
    "papers/paper2/paper2_5_5_smentite.md": (
        "82b2878d001509f837609ebfef588c334353de1e11bec175ffb53bc3d1efb44c", 15129,
        "record 60, 63, 64, 65, 66, 67 — porta i conteggi delle smentite 12 / 1 / 6"),
    "papers/paper2/paper2_budget_5_1.md": (
        "0b7f8d5418875130fd38502e07e627a0105fa659585fdf67dc5b47aca565c6ae", 8993,
        "record 60"),
    "papers/paper2/paper2_residui_fase4.md": (
        "05161983e71b529f9a9ae6031f4a6a3b31b5aee0e4022264ec99e1aba14d960a", 6398,
        "record 60, 62, 63"),
    "papers/paper2/paper2_5_4_practice.md": (
        "39ea969e8d3e5ffedf574a03fd596b09ebf0c87f981bde6fdad727e066f10d4f", 6594,
        "record 60"),
    "papers/paper2/modifiche_paper1.md": (
        "c6350fd4423edc4f2529e37f694d0c4a7e867bf00e5a8552a495297de17a9922", 74973,
        "record 60"),
    "logs/censimento_v14.jsonl": (
        "b1d8192deacc589cbad0464bdf723f215d4df2d9d0633dfcb83b6ad5be2fbedd", 315025,
        "record 68 — evidence del censimento dei registri, linea di base corrente"),
    "logs/prov_pk.jsonl": (
        "98dc66c1f19afb83861d93dff07ca686656557ac73d17e4b0aa03f6fad64eca4", 9939,
        "record 62 — provenienza di pk_matrix"),
    "logs/ladder_sigma.jsonl": (
        "549a2ca9f148caab56fe0d4691f61c3d4bff2758015ae723b2f466aaac0f7b13", 3623,
        "record 51"),
}

KREF = "results/paper2/phase7_pk_nwlh_kref.npz"
TAG = "v3.1-paper2"


class Rifiuto(Exception):
    """Un cancello non e' passato. Nessun byte e' stato scritto."""


# ===========================================================================
# utilita' (identiche a amend68/amend69)
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
    fuori_dal_rilascio = dict(
        (p, {"sha256": sha, "byte": n, "citato_da": chi})
        for p, (sha, n, chi) in DIGEST_ATTESI.items()
    )
    return {
        "document": "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444",
        "type": "protocol",
        "utc": ora_utc(),
        "item": "6.3/portata_del_rilascio_ancoraggio_dei_non_redistribuiti_e_differimento",
        "key": "release_scope_digests_for_what_stays_out_and_publication_deferred_to_submission",
        "amends_records": [],
        "json_path": ".gitignore; logs/eccezioni_rilascio.json; "
                     "src/paper2_censimento_rilascio.py; "
                     "results/paper2/phase7_pk_nwlh_kref.npz",
        "old_value":
            "La voce 6.3 chiedeva «tag `v2.1-paper2`; DOI Zenodo aggiornato». Non diceva che "
            "cosa il rilascio dovesse contenere, e la popolazione era delimitata di fatto da "
            "`.gitignore`: due righe secche, `papers/` e `logs/`, che escludevano cinque "
            "documenti e tre registri che i record del ledger citano. Il nome del tag era "
            "inoltre incompatibile con quelli esistenti.",
        "reason":
            "Un rilascio il cui ledger cita file che il rilascio non contiene non e' "
            "verificabile dall'esterno, e non lo diventa lasciando che sia una regola di "
            "`.gitignore` a decidere per omissione. La popolazione del rilascio si deriva dai "
            "record, come quella del censimento dei registri: ogni percorso citato dev'essere "
            "dentro, oppure fuori con un motivo scritto e, se non ha altro ancoraggio, un "
            "digest. Cinque documenti e tre registri restano fuori per scelta e sono ancorati "
            "qui per byte: chi li riceve puo' verificare di avere quelli citati.",
        "new_value": {
            "i_decisione_papers_fuori":
                "`papers/` resta FUORI dal versionamento e dal rilascio: contiene i sorgenti "
                "dei paper scritti e in scrittura e la corrispondenza con editore e referee. "
                "Non e' una questione di formato ma di primato: quei testi escono col paper, "
                "non col codice. I cinque `.md` citati dai record sono ancorati per digest in "
                "`fuori_dal_rilascio`.",
            "ii_decisione_logs_fuori":
                "`logs/` resta fuori: e' sentiero di lavoro, e i risultati che contano devono "
                "stare in `results/`. Dei tre registri citati, `logs/censimento_v14.jsonl` e' "
                "il caso in cui la regola e la verificabilita' tirano in direzioni diverse — e' "
                "l'evidence del record 68 e la linea di base del censimento dei registri, non "
                "un log. Se la voce 6.1 dovra' reggere a un lettore esterno, la via e' "
                "spostarlo in `results/` con un record che dichiari il cambio di percorso, non "
                "redistribuirlo da `logs/`. Per ora resta fuori, ancorato per byte.",
            "iii_decisione_pubblicazione_differita":
                "`origin` (https://github.com/AleMarco1/CAUCHY.git) e' PUBBLICO, verificato il "
                "16 set 2026 con una `ls-remote` anonima, e porta " + str(RECORD_SU_ORIGIN) +
                " record: si e' fermato l'8 settembre. I record 56-69 e i risultati di Fase 4, "
                "5 e 6 restano LOCALI fino alla sottomissione, e la pubblicazione avviene in "
                "concomitanza con essa, cosi' che i referee vedano i risultati insieme al "
                "manoscritto. Il commit e il tag si fanno adesso in locale: un tag e' un "
                "oggetto locale finche' non lo si spinge. Il deposito Zenodo non passa da "
                "GitHub — `paper2_deposit.py` costruisce gli zip da una lista di file — quindi "
                "il DOI si puo' ottenere con accesso limitato prima dell'apertura del repo. "
                "La portata del rilascio comprende QUANDO diventa leggibile, non solo che cosa "
                "contiene.",
            "iv_decisione_nome_del_tag":
                "Il tag e' `" + TAG + "`, non il `v2.1-paper2` della voce 6.3. I tag esistenti "
                "sono v3.0-paper2 (il deposito del 28 agosto), v2.1-phase9b, v2.0-paper-c, "
                "v1.0: un `v2.1-paper2` creato oggi si ordinerebbe PRIMA del deposito e "
                "collide nella serie con un v2.1 gia' usato per altro. Il nome della voce era "
                "ereditato, non scelto.",
            "v_decisione_popolazione_di_src":
                "Entra tutto `src/`, non i soli strumenti citati da un record. La regola "
                "alternativa — «entra solo cio' che un record cita» — sarebbe una seconda "
                "delimitazione di popolazione, non dichiarata da nessuna parte, e si "
                "romperebbe il giorno che un record cita uno degli esclusi. Entrano anche gli "
                "snapshot dell'ambiente env_cauchy_2026-09-11.txt e .yml: vanno dichiarati "
                "insieme a results/revision/env_versions.txt, che e' nel tier congelato ma "
                "appartiene al ciclo di revisione del Paper 1 — due snapshot di due momenti, e "
                "il lettore deve sapere quale vale per cosa.",
            "vi_decisione_riammissione_del_kref":
                "`" + KREF + "`, 1684 byte, era escluso da `*.npz`, regola scritta per i cubi "
                "di campo (il tier fields pesa 18,4 GB). E' l'asse k delle 110 colonne di "
                "pk_matrix, records 61 e 62, cioe' un artefatto di PROVENIENZA: senza di esso "
                "chi verifica dall'esterno non ha l'asse k. Riammesso per nome. Delimitare per "
                "estensione e' l'errore che il record 68 dichiara, e qui stava dentro "
                "`.gitignore`.",
            "vii_fuori_dal_rilascio": fuori_dal_rilascio,
            "viii_strumento":
                "src/paper2_censimento_rilascio.py v1.1: cammina tutti i record, raccoglie ogni "
                "percorso citato e chiede a git in che stato e'. Quattro verdetti — i citati "
                "esistono, sono tracciati, non sono esclusi senza eccezione, non sono "
                "modificati e non committati — piu' `metri_concordi`, che confronta due misure "
                "indipendenti dell'esclusione (`git status --untracked-files=all` contro "
                "`check-ignore`) perche' una delle due, da sola, aveva dato un PASS silenzioso "
                "su un metro rotto. Le eccezioni stanno in logs/eccezioni_rilascio.json, dodici "
                "voci, e un motivo piu' corto di dieci caratteri viene rifiutato.",
            "ix_what_is_NOT_done":
                "Nessun documento e' stato spostato, nessun record riscritto, nessun byte di "
                "risultato toccato. Restano QUATTRO percorsi citati e non su disco, che sono "
                "lavoro del 6.2 e non dichiarabili come eccezioni: src/paper2_item13rev2.py "
                "(record 27, definisce i punti della griglia di misura pre-registrata), "
                "src/paper2_letture_1punto.py (record 54), results/phase8_test2_permock.csv "
                "(record 11 e 12; rimosso da P-A1, e REPRODUCIBILITY.md §5 tratta un file di "
                "nome simile ma non identico, phase8_test2_permock_hodfit.csv: va letto prima "
                "di dichiarare), e la grafia del percorso Quijote dentro il record 43, che in "
                "un punto omette la cartella intermedia e quindi non risolve. Inoltre il file "
                "delle eccezioni sta esso stesso in `logs/` e sara' quindi segnalato dal "
                "censimento: il suo contenuto autorevole e' questo record, non quel file.",
        },
        "evidence":
            "Censimento del 16 set 2026, src/paper2_censimento_rilascio.py v1.1 su 69 record: "
            "122 percorsi citati distinti, 79 tracciati e puliti, 22 da aggiungere, 10 esclusi "
            "con eccezione, 4 assenti, 2 assenti con eccezione, 1 pattern. Verdetti: "
            "citati_non_esclusi PASS, metri_concordi PASS; citati_tracciati, citati_committati "
            "e citati_esistono FAIL, ognuno con la sua lista. Gli otto digest di "
            "`fuori_dal_rilascio` sono stati ricalcolati dal disco dai cancelli di questo "
            "script immediatamente prima dell'append. `origin/main` a " + str(RECORD_SU_ORIGIN) +
            " record, verificato con `git show origin/main:src/paper2_v1_amendments.jsonl`. "
            "Regole in forza dal commit 3e43e38: .gitignore sha256 "
            "f5a8b24108cddde43a28c2c0566b4a470f8d0c58d3b3e0d831cb8917f21f35d2, 2742 byte, con "
            "`papers/` e `logs/` righe secche e la riammissione del kref in coda.",
        "counts_before": {"DOCUMENTED_AMENDMENTS": 69, "ledger_su_disco": 69},
        "counts_after": {"DOCUMENTED_AMENDMENTS": 70, "ledger_su_disco": 70},
        "counts_note": "Regola del record 67: un campo di conteggi porta il numero che i "
                       "documenti avranno DOPO i patcher. DOCUMENTED_AMENDMENTS va portato a 70 "
                       "da paper2_patch_documented_amendments.py.",
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": REFERENCE_FILE_SHA256,
        "reference_self_sha256": REFERENCE_SELF_SHA256,
        "numbering_rule": "Il numero di un emendamento e' la sua POSIZIONE 1-based in questo "
                          "file. Questo e' il record %d." % NUMERO_RECORD,
        "rules": {
            "marker": "emendamento-70-portata-del-rilascio",
            "companion_documents": "checklist_paper2.md voce 6.3 (il nome del tag va corretto "
                                   "da v2.1-paper2 a " + TAG + "); paper2_stato.md; "
                                   "REPRODUCIBILITY.md §1",
            "la_popolazione_del_rilascio_si_deriva_dai_record":
                "Non «src e results» per abitudine: ogni percorso che un record nomina dev'essere "
                "dentro, o fuori con un motivo scritto. Lo verifica uno strumento, non la memoria.",
            "cio_che_resta_fuori_va_ancorato":
                "Un'esclusione e' dichiarabile solo se qualcosa ancora i byte. Il dato Quijote ha "
                "il digest nel record 43; questi otto non avevano niente, e ce l'hanno da qui.",
            "un_gitignore_non_e_una_decisione":
                "Una riga secca che esclude una cartella decide la portata di un rilascio per "
                "omissione. La decisione va scritta dove si legge, non dedotta da una regola.",
            "il_quando_e_parte_della_portata":
                "Un repository pubblico rende leggibile al `push`, non al tag. Differire la "
                "pubblicazione e' una scelta di protocollo e si dichiara.",
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


def cancelli_portata(radice: Path, esegui=None) -> list:
    esiti = []

    # 1. i digest, ricalcolati adesso
    for percorso, (sha_atteso, byte_attesi, _) in sorted(DIGEST_ATTESI.items()):
        p = radice / percorso
        if not p.is_file():
            raise Rifiuto("dichiarato fuori dal rilascio ma assente dal disco: %s" % percorso)
        dati = p.read_bytes()
        sha = sha256_bytes(dati)
        if sha != sha_atteso or len(dati) != byte_attesi:
            raise Rifiuto(
                "il digest dichiarato non e' quello sul disco: %s\n"
                "  disco:      %s  %d byte\n  dichiarato: %s  %d byte\n"
                "  Il file e' cambiato dopo la misura: rimisurare e aggiornare DIGEST_ATTESI."
                % (percorso, sha, len(dati), sha_atteso, byte_attesi))
        esiti.append("digest: %s  %s  %d byte" % (percorso, sha[:16], len(dati)))

    # 2. gli otto devono essere davvero esclusi, e il kref davvero dentro
    tracciati = set(
        r.strip().replace("\\", "/")
        for r in _git(radice, "ls-files", esegui=esegui).splitlines() if r.strip())
    visibili = set()
    for riga in _git(radice, "-c", "core.quotepath=false", "status", "--porcelain",
                     "--untracked-files=all", esegui=esegui).splitlines():
        if riga.startswith("?? "):
            visibili.add(riga[3:].strip('"').replace("\\", "/"))
    for percorso in sorted(DIGEST_ATTESI):
        if percorso in tracciati or percorso in visibili:
            raise Rifiuto(
                "il record dichiara %s fuori dal rilascio, ma git lo offre o lo traccia: "
                "la decisione non e' in forza" % percorso)
    esiti.append("esclusi: %d percorsi ne' tracciati ne' offerti da git" % len(DIGEST_ATTESI))
    if KREF not in tracciati and KREF not in visibili:
        raise Rifiuto("il record dichiara %s riammesso, ma git non lo vede" % KREF)
    esiti.append("riammesso: %s visibile a git" % KREF)

    # 3. origin/main deve essere fermo dove il record dice
    dati = _git(radice, "show", "origin/main:" + LEDGER_DEFAULT, esegui=esegui, byte=True)
    if isinstance(dati, str):
        dati = dati.encode("utf-8")
    n = len(righe_json(dati))
    if n != RECORD_SU_ORIGIN:
        raise Rifiuto("origin/main porta %d record, il record dichiara %d" % (n, RECORD_SU_ORIGIN))
    esiti.append("origin/main: %d record, i 56-%d restano locali" % (n, ATTESI_DEFAULT + 1))

    return esiti


def cancelli_ledger(dati: bytes, attesi: int, controlla_sha: bool = True) -> dict:
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
    return prof


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
            esegui_git=None, controlla_reference: bool = True) -> dict:
    vecchio = ledger.read_bytes()
    prof = cancelli_ledger(vecchio, attesi, controlla_sha)
    if controlla_reference:
        cancello_reference(reference)
    esiti = cancelli_portata(radice, esegui=esegui_git)

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

    fd, tmp = tempfile.mkstemp(dir=str(ledger.parent), prefix=".amend70_", suffix=".jsonl")
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

def _ledger_finto(n: int, righe_lf=(2, 3)) -> bytes:
    fuori = b""
    for i in range(1, n + 1):
        rec = {"item": "finto/%d" % i, "numbering_rule": "This is record %d." % i}
        linea = json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8")
        fuori += linea + (b"\n" if i in righe_lf else b"\r\n")
    return fuori


def _git_stub(origin=RECORD_SU_ORIGIN, esclusi=True, kref=True):
    def esegui(arg):
        if arg[0] == "ls-files":
            return (KREF + "\n") if kref else "\n"
        if "status" in arg:
            righe = []
            if not esclusi:
                righe.append("?? " + sorted(DIGEST_ATTESI)[0])
            return "\n".join(righe) + ("\n" if righe else "")
        if arg[0] == "show":
            return _ledger_finto(origin)
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
        except Exception as e:
            ko += 1
            print("  FAIL  %s (eccezione sbagliata: %r)" % (nome, e))
            return
        ko += 1
        print("  FAIL  %s (non ha rifiutato)" % nome)

    rec = costruisci_record()
    controlla("record: numbering_rule al 70", rec["numbering_rule"].endswith("record 70."))
    controlla("record: item della 6.3", rec["item"].startswith("6.3/"))
    controlla("record: marker", rec["rules"]["marker"] == "emendamento-70-portata-del-rilascio")
    controlla("record: conteggi 69 -> 70",
              rec["counts_before"]["DOCUMENTED_AMENDMENTS"] == 69
              and rec["counts_after"]["DOCUMENTED_AMENDMENTS"] == 70)
    controlla("record: sei decisioni",
              sum(1 for k in rec["new_value"] if k.split("_")[0] in
                  ("i", "ii", "iii", "iv", "v", "vi")) == 6)
    controlla("record: otto file fuori dal rilascio",
              len(rec["new_value"]["vii_fuori_dal_rilascio"]) == 8)
    controlla("record: ogni voce porta sha e byte",
              all(set(v) == {"sha256", "byte", "citato_da"}
                  for v in rec["new_value"]["vii_fuori_dal_rilascio"].values()))
    controlla("record: i digest vengono da DIGEST_ATTESI",
              all(rec["new_value"]["vii_fuori_dal_rilascio"][p]["sha256"] == DIGEST_ATTESI[p][0]
                  for p in DIGEST_ATTESI))
    controlla("record: il tag e' v3.1-paper2",
              TAG in rec["new_value"]["iv_decisione_nome_del_tag"]
              and TAG in rec["rules"]["companion_documents"])
    controlla("record: dichiara il differimento",
              "LOCALI fino alla sottomissione"
              in rec["new_value"]["iii_decisione_pubblicazione_differita"])
    controlla("record: dichiara i quattro irrisolti",
              all(x in rec["new_value"]["ix_what_is_NOT_done"] for x in
                  ("paper2_item13rev2.py", "paper2_letture_1punto.py",
                   "phase8_test2_permock.csv", "record 43")))
    controlla("record: il file delle eccezioni non e' la fonte autorevole",
              "contenuto autorevole e' questo record"
              in rec["new_value"]["ix_what_is_NOT_done"])
    linea = serializza(rec, b"\r\n")
    controlla("serializza: una riga sola", linea.count(b"\n") == 1)
    controlla("serializza: chiavi ordinate",
              list(json.loads(linea[:-2].decode("utf-8"))) == sorted(rec))

    # --- cancelli di portata su un albero finto --------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for percorso, (sha, n, _) in DIGEST_ATTESI.items():
            p = base / percorso
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\0" * n)          # byte giusti in numero, sha sbagliato
        rifiuta("digest che non combacia rifiutato",
                lambda: cancelli_portata(base, esegui=_git_stub()))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        veri = {}
        for percorso, (sha, n, chi) in DIGEST_ATTESI.items():
            p = base / percorso
            p.parent.mkdir(parents=True, exist_ok=True)
            dati = os.urandom(n)
            p.write_bytes(dati)
            veri[percorso] = (sha256_bytes(dati), n, chi)
        atteso_originale = dict(DIGEST_ATTESI)
        DIGEST_ATTESI.clear()
        DIGEST_ATTESI.update(veri)
        try:
            esiti = cancelli_portata(base, esegui=_git_stub())
            controlla("cancelli: otto digest piu' tre righe", len(esiti) == 11)
            controlla("cancelli: origin dichiarato",
                      any("origin/main" in x for x in esiti))
            rifiuta("un escluso che git offre e' un rifiuto",
                    lambda: cancelli_portata(base, esegui=_git_stub(esclusi=False)))
            rifiuta("origin/main con un conteggio diverso e' un rifiuto",
                    lambda: cancelli_portata(base, esegui=_git_stub(origin=60)))
            rifiuta("kref invisibile e' un rifiuto",
                    lambda: cancelli_portata(base, esegui=_git_stub(kref=False)))
            (base / sorted(DIGEST_ATTESI)[0]).unlink()
            rifiuta("un dichiarato assente dal disco e' un rifiuto",
                    lambda: cancelli_portata(base, esegui=_git_stub()))
        finally:
            DIGEST_ATTESI.clear()
            DIGEST_ATTESI.update(atteso_originale)

    # --- pipeline ---------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "src").mkdir()
        led = base / "src" / "amend.jsonl"
        led.write_bytes(_ledger_finto(69))
        vecchio = led.read_bytes()
        veri = {}
        for percorso, (sha, n, chi) in DIGEST_ATTESI.items():
            p = base / percorso
            p.parent.mkdir(parents=True, exist_ok=True)
            dati = os.urandom(n)
            p.write_bytes(dati)
            veri[percorso] = (sha256_bytes(dati), n, chi)
        atteso_originale = dict(DIGEST_ATTESI)
        DIGEST_ATTESI.clear()
        DIGEST_ATTESI.update(veri)
        try:
            rec2 = costruisci_record()
            r = applica(base, led, None, rec2, True, 69, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False)
            controlla("dry-run: non scrive", led.read_bytes() == vecchio)
            controlla("dry-run: terminatore ereditato CRLF", r["terminatore"] == "crlf")
            rifiuta("conteggio dei record sbagliato", lambda: applica(
                base, led, None, rec2, True, 68, controlla_sha=False,
                esegui_git=_git_stub(), controlla_reference=False))
            r = applica(base, led, None, rec2, False, 69, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False)
            nuovo = led.read_bytes()
            controlla("apply: scritto", r["scritto"] is True)
            controlla("apply: prefisso invariato", nuovo[:len(vecchio)] == vecchio)
            controlla("apply: 70 record", len(righe_json(nuovo)) == 70)
            controlla("apply: righe a LF invariate",
                      profilo_eol(nuovo)["righe_lf"] == profilo_eol(vecchio)["righe_lf"])
            controlla("apply: record riletto identico", righe_json(nuovo)[-1] == rec2)
            controlla("apply: nessun temporaneo residuo",
                      not list((base / "src").glob(".amend70_*")))
            rifiuta("apply due volte rifiutato", lambda: applica(
                base, led, None, rec2, False, 69, controlla_sha=False,
                esegui_git=_git_stub(), controlla_reference=False))
        finally:
            DIGEST_ATTESI.clear()
            DIGEST_ATTESI.update(atteso_originale)

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


# ===========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="record 70: la portata del rilascio")
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

    print("=== paper2_append_amend70 — record %d ===" % NUMERO_RECORD)
    for riga in r["cancelli"]:
        print("  [ok] %s" % riga)
    print("  prima: %s  %d byte" % (r["sha_prima"], r["byte_prima"]))
    print("  dopo:  %s  %d byte  (+%d, terminatore %s)"
          % (r["sha_dopo"], r["byte_dopo"], r["byte_del_record"], r["terminatore"]))
    if r["scritto"]:
        print("  record sul disco: %d" % r["record_dopo"])
        print("\nAppeso. Ora:")
        print("  python src\\paper2_patch_documented_amendments.py apply "
              "--file src\\paper2_freeze_verify.py --da 69 --a 70")
        print("  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    else:
        print("\nDRY-RUN: nessun byte scritto. Il record che verrebbe appeso:")
        print(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

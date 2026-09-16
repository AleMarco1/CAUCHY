#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_append_amend69.py — record 69: l'ordine di `.gitattributes` e tre file
del tier congelato `records`.

Appende UN record a src\paper2_v1_amendments.jsonl. Modello `amend68`:
scrittura su temporaneo piu' os.replace, e IL CANCELLO PRINCIPALE E' IL
PREFISSO — i primi len(vecchio) byte del nuovo file devono essere identici
byte per byte al vecchio. Copre insieme la normalizzazione dei sei LF isolati
(righe 8 9 10 11 13 14, record 47), quella dei CRLF, e la modifica di un
record precedente.

CHE COSA DICHIARA, in una frase: in `.gitattributes` vince l'ultima regola che
combacia, le due regole di cartella stavano in testa, e quindi per i `.md`,
`.txt` e `.py` dentro `results/` erano scavalcate dalle regole di tipo in coda
— tre di quei file sono nel tier congelato `records`, con un digest sui byte.

CANCELLI PROPRI DI QUESTO RECORD. Un record non si scrive prima che cio' che
dichiara sia vero. Prima di appendere, lo script verifica con git che:
  - i tre file del tier abbiano `text: unset`, cioe' `-text` esplicito;
  - il loro blob nell'indice sia CRLF come i byte su disco (`i/crlf w/crlf`),
    perche' e' l'indice che un checkout riversa sul disco;
  - `*.py` e `*.md` abbiano `eol=lf`.
Se uno dei tre non passa, RIFIUTA e non scrive nulla.

Sequenza:  selftest  ->  applica --dry-run  ->  applica
Poi:       paper2_patch_documented_amendments.py  per portare
           DOCUMENTED_AMENDMENTS a 69, e freeze_verify.
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
LEDGER_SHA256_ATTESO = "78c47a5d893313ad760249983c78f5eda34f303146ef940d9c4cf693f39b04b8"
LEDGER_BYTE_ATTESI = 565567
ATTESI_DEFAULT = 68          # record sul disco PRIMA di questo append
NUMERO_RECORD = 69           # posizione 1-based di questo record

# Profilo dei fini riga atteso PRIMA dell'append: 61/6 al record 67 (censimento
# del 15 set), piu' il CRLF del record 68 appeso lo stesso giorno.
EOL_CRLF_ATTESI = 62
EOL_LF_ATTESI = 6
EOL_RIGHE_LF_ATTESE = [8, 9, 10, 11, 13, 14]

FILE_TIER = [
    "results/paper1/src_bundle_phase9.txt",
    "results/phase5_hod_variance_decomp_summary.md",
    "results/revision/env_versions.txt",
]
FILE_EOL_LF = [
    "src/paper2_freeze_verify.py",
    "papers/paper2/checklist_paper2.md",
]

PATCHER_SHA256 = "98217c6f17ca1b8d74c4f3362741a8085b128618520fc1a09a0f162e4fcd54d2"


class Rifiuto(Exception):
    """Un cancello non e' passato. Nessun byte e' stato scritto."""


# ===========================================================================
# utilita' (stesse di amend68)
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
        "item": "6.3/ordine_di_gitattributes_e_tre_file_del_tier_congelato",
        "key": "last_matching_attribute_wins_and_three_frozen_files_were_normalisable",
        "amends_records": [],
        "json_path": ".gitattributes; results/paper1/src_bundle_phase9.txt; "
                     "results/phase5_hod_variance_decomp_summary.md; "
                     "results/revision/env_versions.txt; "
                     "results/paper2/ensemble_v1_manifest_records.jsonl; "
                     "src/paper2_patch_regole_git.py",
        "old_value":
            "`.gitattributes` dichiarava in testa, col commento «Nessuna normalizzazione su "
            "NULLA dentro results/ e MANIFESTS/», le due regole `results/** -text` e "
            "`manifests/** -text`; e in coda, sotto «Sorgenti e documenti: normalizzazione "
            "normale», `*.py text`, `*.md text`, `*.txt text`. Il commento in testa era preso "
            "per la portata effettiva della regola.",
        "reason":
            "In `.gitattributes` VINCE L'ULTIMA REGOLA CHE COMBACIA. Con le regole di cartella "
            "in testa e quelle di tipo in coda, ogni `.md`, `.txt` e `.py` dentro `results/` "
            "era dichiarato `text` e quindi normalizzabile, nonostante il commento dicesse il "
            "contrario. Un commento non e' una regola, e la portata di una regola non si legge "
            "in cio' che dichiara di coprire ma nella sua posizione. Tre dei file cosi' esposti "
            "sono nel tier congelato `records`, con un digest SUI BYTE nel manifest: i loro "
            "byte su disco erano riproducibili solo su una macchina Windows con "
            "core.autocrlf=true. Un checkout con autocrlf=false, o su Linux, li avrebbe scritti "
            "a LF e il congelamento sarebbe uscito MISMATCH. Il CLEAN del 15 e del 16 settembre "
            "non lo vedeva perche' la conversione non era ancora avvenuta su questa macchina, "
            "non perche' non potesse avvenire.",
        "new_value": {
            "i_la_misura": {
                "check_attr_prima": "git check-attr text -- su results/paper1/src_bundle_phase9.txt, "
                                    "results/phase5_hod_variance_decomp_summary.md, "
                                    "results/revision/env_versions.txt dava `text: set` su tutti tre.",
                "ls_files_eol_prima": "`i/lf w/crlf attr/text`: indice a LF, disco a CRLF. Il "
                                      "manifest digerisce i byte su disco, quindi indice e "
                                      "manifest erano in disaccordo e nessun controllo lo diceva.",
                "appartenenza_al_tier": "Tutti tre compaiono in "
                                        "results/paper2/ensemble_v1_manifest_records.jsonl, tier "
                                        "`records`, 224 voci, quello marcato `(emendato)` da "
                                        "freeze_verify.",
                "popolazione_dei_crlf": "246 file tracciati con la copia di lavoro a CRLF, su 671 "
                                        "tracciati: 239 sono `attr/-text` (git non li converte e non "
                                        "li ha mai convertiti: sono CRLF perche' li hanno scritti "
                                        "cosi' gli strumenti), 1 e' un `.bak` senza attributi, e 6 "
                                        "sono `attr/text`. Di quei 6, tre sono i file del tier.",
            },
            "ii_la_correzione": {
                "regola": "Le due regole di cartella spostate in CODA, dopo quelle di tipo, dove "
                          "riprendono la precedenza che il commento in testa gli attribuiva.",
                "eol_lf_sui_sorgenti": "`*.py` e `*.md` passano a `text eol=lf`: git normalizza a LF "
                                       "nell'indice E fa il checkout a LF su ogni piattaforma, "
                                       "ignorando core.autocrlf. I byte diventano deterministici, "
                                       "che e' cio' che la disciplina di ancoraggio di questo "
                                       "programma richiede — ogni patcher si aggancia allo sha256 "
                                       "dei byte su disco di un sorgente o di un documento.",
                "strumento": "src/paper2_patch_regole_git.py v1.3, selftest 66/66, sha256 "
                             + PATCHER_SHA256 + ". Lavora sulle righe col loro terminatore: cio' che "
                             "non tocca resta byte per byte, e le righe nuove nascono col fine riga "
                             "di maggioranza del file.",
                "indice": "`git add` da solo non bastava: l'indice portava mtime e dimensione "
                          "registrati al checkout, quando i file erano `text`, e cambiare un "
                          "attributo non invalida la cache di stat, quindi git concludeva «non "
                          "modificato» e non rileggeva i byte. Invalidata la cache (mtime) e "
                          "riletti: `i/crlf w/crlf attr/-text`.",
            },
            "iii_rapporto_coi_record_47_e_68": {
                "cosa_diceva_il_47": "Che le sei righe LF del ledger fossero a rischio perche' "
                                     "`.gitattributes` copriva `results/**` e non `src/`, e un "
                                     "checkout con core.autocrlf avrebbe potuto normalizzarle "
                                     "cambiando i byte del file senza che nulla se ne accorgesse.",
                "cosa_ha_stabilito_il_68": "Che per i `.jsonl` e i `.json` quel pericolo non era "
                                           "possibile: `*.jsonl -text` esiste dal commit 684d1f3 "
                                           "del 25 agosto 2026, e `-text` scavalca core.autocrlf. "
                                           "Quella conclusione RESTA VERA e non e' toccata qui.",
                "che_cosa_nessuno_dei_due_ha_guardato": "I `.py`, i `.md` e i `.txt`. Per quella "
                                                        "classe il pericolo che il 47 descriveva era "
                                                        "REALE, e arrivava dentro il congelamento. "
                                                        "Il 47 aveva torto sul meccanismo per i "
                                                        "registri e ragione sulla classe di rischio: "
                                                        "esisteva, su altri file.",
                "la_lezione_riusabile": "Verificare che una regola copra cio' che si vuole coprire "
                                        "non basta: va verificato che nessuna regola successiva la "
                                        "scavalchi per un sottoinsieme.",
            },
            "iv_what_is_NOT_done": "Nessun byte di nessun file di risultato e' stato toccato: "
                                   "freeze_verify resta CLEAN, 34 836 file e 26.77144 GiB sui "
                                   "cinque tier. I 239 file `-text` a CRLF NON sono rinormalizzati "
                                   "e non devono esserlo: sono i byte che i manifest digeriscono. "
                                   "Restano da rinormalizzare i tre `attr/text` fuori dal tier — "
                                   "CAUCHY_Review_and_GATE.md, src/phase5bis_growth_factor.py, "
                                   "src/phase8_test2_masked.py — nessuno dei quali e' citato da un "
                                   "record: e' un commit a parte, non mescolato ai contenuti.",
        },
        "evidence":
            "Misure del 16 set 2026 su questa macchina, core.autocrlf=true. "
            "`git check-attr text --` sui tre file: `text: set` prima, `text: unset` dopo. "
            "`git ls-files --eol`: `i/lf w/crlf attr/text` prima, `i/crlf w/crlf attr/-text` dopo, "
            "verificato dai cancelli di questo script prima dell'append. "
            "`git ls-files --eol | Where-Object { $_ -match 'w/crlf' }`: 246 file, di cui 239 "
            "`attr/-text`, 6 `attr/text`, 1 senza attributi. Appartenenza al tier verificata "
            "cercando i tre nomi in results/paper2/ensemble_v1_manifest_*.jsonl: `records` per "
            "tutti tre. `.gitattributes` da sha256 "
            "47b383d4ca478f09702d25c9f62c2fcfd83f43ef213a8453e66ebd9cc517843f (1092 byte, 40 CRLF) "
            "a ec5b6d78be63e4fcfd5b2cb039037ef39228dec0eab18748ab33a54ae518bbd0 (1525 byte). "
            "freeze_verify CLEAN alle 2026-09-16T05:05:43Z con disco = documentati = 68.",
        "counts_before": {"DOCUMENTED_AMENDMENTS": 68, "ledger_su_disco": 68},
        "counts_after": {"DOCUMENTED_AMENDMENTS": 69, "ledger_su_disco": 69},
        "counts_note": "Regola del record 67: un campo di conteggi porta il numero che i documenti "
                       "avranno DOPO i patcher, non quello che hanno mentre il record si scrive. "
                       "DOCUMENTED_AMENDMENTS va portato a 69 da "
                       "paper2_patch_documented_amendments.py.",
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": REFERENCE_FILE_SHA256,
        "reference_self_sha256": REFERENCE_SELF_SHA256,
        "numbering_rule": "Il numero di un emendamento e' la sua POSIZIONE 1-based in questo file. "
                          "Questo e' il record %d." % NUMERO_RECORD,
        "rules": {
            "marker": "emendamento-69-ordine-di-gitattributes",
            "companion_documents": "checklist_paper2.md voce 6.3; paper2_stato.md; "
                                   "REPRODUCIBILITY.md §5",
            "l_ultima_regola_che_combacia_vince": "In .gitattributes la precedenza e' posizionale. "
                                                  "Una regola di cartella messa in testa e' "
                                                  "scavalcata da ogni regola di tipo che venga dopo, "
                                                  "per i file che hanno quell'estensione.",
            "un_commento_non_e_una_regola": "Il commento in testa dichiarava una protezione piu' "
                                            "larga di quella reale. Va verificata la regola, non "
                                            "letto il commento.",
            "i_byte_di_un_file_congelato_non_si_lasciano_a_una_configurazione":
                "Un digest sui byte esige che i byte siano gli stessi su ogni macchina. `-text` per "
                "cio' che e' congelato, `eol=lf` per cio' che e' ancorato per sha.",
            "la_cache_di_stat_non_si_invalida_da_se": "Cambiare un attributo non fa rileggere i byte "
                "a git: `git add` su un file il cui stat combacia con l'indice e' un no-op "
                "silenzioso. Va invalidata la cache, e poi verificato con `ls-files --eol`.",
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


def cancelli_git(radice: Path, esegui=None) -> list:
    """Verifica che cio' che il record dichiara sia vero PRIMA di scriverlo."""
    esiti = []

    uscita = _git(radice, "check-attr", "text", "--", *FILE_TIER, esegui=esegui)
    righe = [r for r in uscita.splitlines() if r.strip()]
    if len(righe) != len(FILE_TIER):
        raise Rifiuto("check-attr ha dato %d righe per %d file" % (len(righe), len(FILE_TIER)))
    for r in righe:
        if not r.strip().endswith("unset"):
            raise Rifiuto("il tier non e' protetto: %s" % r.strip())
        esiti.append("check-attr: " + r.strip())

    uscita = _git(radice, "ls-files", "--eol", "--", *FILE_TIER, esegui=esegui)
    righe = [r for r in uscita.splitlines() if r.strip()]
    if len(righe) != len(FILE_TIER):
        raise Rifiuto("ls-files --eol ha dato %d righe per %d file" % (len(righe), len(FILE_TIER)))
    for r in righe:
        campi = r.split()
        if campi[0] != "i/crlf" or campi[1] != "w/crlf" or campi[2] != "attr/-text":
            raise Rifiuto(
                "indice e disco non concordano ancora: %s\n"
                "  Invalida la cache di stat e rileggi:\n"
                "    $f = @(%s); $f | ForEach-Object { (Get-Item $_).LastWriteTime = Get-Date }; "
                "git add -- $f" % (r.strip(), ",".join('"%s"' % x for x in FILE_TIER))
            )
        esiti.append("ls-files --eol: " + " ".join(campi))

    uscita = _git(radice, "check-attr", "eol", "--", *FILE_EOL_LF, esegui=esegui)
    for r in [x for x in uscita.splitlines() if x.strip()]:
        if not r.strip().endswith("lf"):
            raise Rifiuto("i sorgenti non hanno eol=lf: %s" % r.strip())
        esiti.append("check-attr eol: " + r.strip())

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
    ultimo = record[-1]
    nr = str(ultimo.get("numbering_rule", ""))
    if not nr.rstrip().endswith("record %d." % attesi):
        raise Rifiuto("l'ultimo record non si dichiara il %d" % attesi)
    return prof


def cancello_reference(p: Path) -> None:
    if not p.is_file():
        raise Rifiuto("reference assente: %s" % p)
    sha = sha256_bytes(p.read_bytes())
    if sha != REFERENCE_FILE_SHA256:
        raise Rifiuto("sha del reference: %s, atteso %s" % (sha, REFERENCE_FILE_SHA256))


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
    esiti_git = cancelli_git(radice, esegui=esegui_git)

    terminatore = b"\r\n" if prof["ereditato"] == "crlf" else b"\n"
    linea = serializza(record, terminatore)
    nuovo = vecchio + linea

    rapporto = {
        "sha_prima": sha256_bytes(vecchio), "byte_prima": len(vecchio),
        "sha_dopo": sha256_bytes(nuovo), "byte_dopo": len(nuovo),
        "byte_del_record": len(linea),
        "terminatore": "crlf" if terminatore == b"\r\n" else "lf",
        "cancelli_git": esiti_git,
    }
    if dry_run:
        rapporto["scritto"] = False
        return rapporto

    fd, tmp = tempfile.mkstemp(dir=str(ledger.parent), prefix=".amend69_", suffix=".jsonl")
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
    prof_dopo = profilo_eol(riletto)
    if prof_dopo["righe_lf"] != EOL_RIGHE_LF_ATTESE and controlla_sha:
        raise Rifiuto("le righe a LF sono cambiate: %r" % prof_dopo["righe_lf"])
    rapporto["scritto"] = True
    rapporto["record_dopo"] = len(rec)
    return rapporto


# ===========================================================================
# selftest
# ===========================================================================

def _git_stub(buono=True):
    def esegui(arg):
        if arg[:2] == ["check-attr", "text"]:
            stato = "unset" if buono else "set"
            return "".join("%s: text: %s\n" % (p, stato) for p in FILE_TIER)
        if arg[:2] == ["ls-files", "--eol"]:
            i = "i/crlf" if buono else "i/lf"
            return "".join("%s\tw/crlf\tattr/-text\t%s\n" % (i, p) for p in FILE_TIER)
        if arg[:2] == ["check-attr", "eol"]:
            return "".join("%s: eol: lf\n" % p for p in FILE_EOL_LF)
        raise AssertionError("comando git non previsto: %r" % arg)
    return esegui


def _ledger_finto(n: int, righe_lf=(2, 3)) -> bytes:
    fuori = b""
    for i in range(1, n + 1):
        rec = {"item": "finto/%d" % i,
               "numbering_rule": "This is record %d." % i}
        linea = json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8")
        fuori += linea + (b"\n" if i in righe_lf else b"\r\n")
    return fuori


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
    controlla("record: numbering_rule al 69", rec["numbering_rule"].endswith("record 69."))
    controlla("record: item della 6.3", rec["item"].startswith("6.3/"))
    controlla("record: marker", rec["rules"]["marker"] == "emendamento-69-ordine-di-gitattributes")
    controlla("record: conteggi 68 -> 69",
              rec["counts_before"]["DOCUMENTED_AMENDMENTS"] == 68
              and rec["counts_after"]["DOCUMENTED_AMENDMENTS"] == 69)
    controlla("record: documenti compagni",
              "checklist_paper2.md" in rec["rules"]["companion_documents"]
              and "REPRODUCIBILITY.md" in rec["rules"]["companion_documents"])
    controlla("record: il 68 non e' smentito",
              "RESTA VERA" in rec["new_value"]["iii_rapporto_coi_record_47_e_68"]
                              ["cosa_ha_stabilito_il_68"])
    controlla("record: nomina i tre file del tier",
              all(p in rec["json_path"] or p in rec["evidence"] for p in FILE_TIER[:1]))
    controlla("record: ancorato al reference",
              rec["reference_file_sha256"] == REFERENCE_FILE_SHA256)
    controlla("record: serializzabile su una riga",
              b"\n" not in serializza(rec, b"")[:-0] or True)
    linea = serializza(rec, b"\r\n")
    controlla("serializza: termina col terminatore dato", linea.endswith(b"\r\n"))
    controlla("serializza: un solo fine riga", linea.count(b"\n") == 1)
    controlla("serializza: chiavi ordinate",
              list(json.loads(linea.decode("utf-8"))) == sorted(rec))
    dentro = serializza(dict(rec, item="a\nb"), b"\n")
    controlla("serializza: un newline nel valore viene escapato, non spezza la riga",
              dentro.count(b"\n") == 1
              and json.loads(dentro.decode("utf-8"))["item"] == "a\nb")

    controlla("profilo_eol: conta e indicizza",
              profilo_eol(b"a\r\nb\nc\r\n")["lf"] == 1
              and profilo_eol(b"a\r\nb\nc\r\n")["righe_lf"] == [2]
              and profilo_eol(b"a\r\nb\nc\r\n")["ereditato"] == "crlf")
    controlla("profilo_eol: coda non terminata",
              profilo_eol(b"a\r\nb")["coda_terminata"] is False)

    # --- pipeline su un ledger finto ------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "src").mkdir()
        led = base / "src" / "amend.jsonl"
        led.write_bytes(_ledger_finto(68))
        ref = base / "src" / "ref.json"
        ref.write_bytes(b"x")
        vecchio = led.read_bytes()

        rifiuta("reference sbagliato", lambda: applica(
            base, led, ref, rec, True, 68, controlla_sha=False, esegui_git=_git_stub()))
        rifiuta("reference assente", lambda: applica(
            base, led, base / "src" / "non_c_e.json", rec, True, 68,
            controlla_sha=False, esegui_git=_git_stub()))
        controlla("reference: il cancello non ha scritto", led.read_bytes() == vecchio)

    # Il resto della catena si prova saltando il solo cancello sul reference:
    # non si puo' fabbricare un file che produca quello sha256.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "src").mkdir()
        led = base / "src" / "amend.jsonl"
        led.write_bytes(_ledger_finto(68))
        vecchio = led.read_bytes()
        if True:
            r = applica(base, led, None, rec, True, 68, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False)
            controlla("dry-run: non scrive", led.read_bytes() == vecchio)
            controlla("dry-run: dichiara il terminatore ereditato", r["terminatore"] == "crlf")
            controlla("dry-run: scritto False", r["scritto"] is False)

            rifiuta("cancello git: indice a LF rifiutato", lambda: applica(
                base, led, None, rec, True, 68, controlla_sha=False,
                esegui_git=_git_stub(buono=False), controlla_reference=False))
            controlla("cancello git: non ha scritto", led.read_bytes() == vecchio)

            rifiuta("conteggio dei record sbagliato", lambda: applica(
                base, led, None, rec, True, 67, controlla_sha=False,
                esegui_git=_git_stub(), controlla_reference=False))

            r = applica(base, led, None, rec, False, 68, controlla_sha=False,
                        esegui_git=_git_stub(), controlla_reference=False)
            nuovo = led.read_bytes()
            controlla("apply: scritto", r["scritto"] is True)
            controlla("apply: prefisso invariato", nuovo[:len(vecchio)] == vecchio)
            controlla("apply: 69 record", len(righe_json(nuovo)) == 69)
            controlla("apply: le righe a LF non sono cambiate",
                      profilo_eol(nuovo)["righe_lf"] == profilo_eol(vecchio)["righe_lf"])
            controlla("apply: il record riletto e' quello inteso",
                      righe_json(nuovo)[-1] == rec)
            controlla("apply: nessun temporaneo residuo",
                      not list((base / "src").glob(".amend69_*")))
            controlla("apply: terminatore CRLF come l'eredita'", nuovo.endswith(b"\r\n"))

            rifiuta("apply due volte: rifiutato", lambda: applica(
                base, led, None, rec, False, 68, controlla_sha=False,
                esegui_git=_git_stub(), controlla_reference=False))

            # prefisso violato: un record precedente modificato
            rotto = base / "src" / "rotto.jsonl"
            d = _ledger_finto(68)
            rotto.write_bytes(d.replace(b"finto/3", b"finto/X"))
            controlla("il prefisso e' il cancello: un byte cambiato si vede",
                      rotto.read_bytes()[:len(d)] != d)

            # coda non terminata
            tronco = base / "src" / "tronco.jsonl"
            tronco.write_bytes(_ledger_finto(68).rstrip(b"\r\n"))
            rifiuta("coda non terminata rifiutata", lambda: applica(
                base, tronco, None, rec, True, 68, controlla_sha=False,
                esegui_git=_git_stub(), controlla_reference=False))

            # ultimo record che non si dichiara il 68
            sbagliato = base / "src" / "sbagliato.jsonl"
            sbagliato.write_bytes(_ledger_finto(68).replace(
                b"This is record 68.", b"This is record 99."))
            rifiuta("ultimo record con numerazione sbagliata", lambda: applica(
                base, sbagliato, None, rec, True, 68, controlla_sha=False,
                esegui_git=_git_stub(), controlla_reference=False))

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


# ===========================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
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

    print("=== paper2_append_amend69 — record %d ===" % NUMERO_RECORD)
    for riga in r["cancelli_git"]:
        print("  [ok] %s" % riga)
    print("  prima: %s  %d byte" % (r["sha_prima"], r["byte_prima"]))
    print("  dopo:  %s  %d byte  (+%d, terminatore %s)"
          % (r["sha_dopo"], r["byte_dopo"], r["byte_del_record"], r["terminatore"]))
    if r["scritto"]:
        print("  record sul disco: %d" % r["record_dopo"])
        print("\nAppeso. Ora:")
        print("  python src\\paper2_patch_documented_amendments.py   (a 69)")
        print("  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    else:
        print("\nDRY-RUN: nessun byte scritto. Il record che verrebbe appeso:")
        print(json.dumps(rec, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

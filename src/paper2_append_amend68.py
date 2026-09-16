#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend68.py — record 68: chiusura della voce 6.1.

Appende UN record a src\\paper2_v1_amendments.jsonl. Modello `amend67`, non
`amend64`: scrittura su temporaneo piu' os.replace, e cancelli sul terminatore
che tengono conto di quello EREDITATO invece di assumere CRLF.

IL CANCELLO PRINCIPALE E' IL PREFISSO.
La scrittura passa da un temporaneo, quindi il file viene RISCRITTO per intero.
L'append-only si dimostra allora in un modo solo: i primi len(vecchio) byte del
nuovo file devono essere identici, byte per byte, al vecchio. Quel controllo
copre insieme tre cose che `amend64` controllava male o non controllava:
  - nessun LF isolato preesistente e' stato normalizzato a CRLF
  - nessun CRLF preesistente e' stato normalizzato a LF
  - nessun record precedente e' stato toccato
E' lo stesso criterio che `paper2_censimento_registri.py` usa per
`append_storico` contro la linea di base.

Il ledger porta sei LF isolati alle righe 8, 9, 10, 11, 13, 14 su eredita' CRLF
(record 47). NON si normalizzano: il record 47 dichiara che restano, e il
controllo del prefisso lo impone.

Sequenza:  selftest  ->  applica --dry-run  ->  applica
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Ancore. Il record deve agganciarsi al reference, che freeze_verify ha
# validato CLEAN il 15 settembre 2026 alle 07:13:43Z.
# Se `file_sha256` calcolato dal disco coincide con la costante, il reference
# e' byte-identico a quello validato, e quindi anche il self-digest che
# dichiara al suo interno e' quello. Lo script RIFIUTA se non coincide.
# ---------------------------------------------------------------------------
REFERENCE_PATH_DEFAULT = "src/paper2_v1_reference.json"
REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA256 = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

LEDGER_DEFAULT = "src/paper2_v1_amendments.jsonl"
ATTESI_DEFAULT = 67          # record sul disco PRIMA di questo append
NUMERO_RECORD = 68           # posizione 1-based di questo record

# Profilo dei fini riga atteso PRIMA dell'append (record 47, riverificato dal
# censimento del 15 set: 61 CRLF, 6 LF, righe 8 9 10 11 13 14).
EOL_CRLF_ATTESI = 61
EOL_LF_ATTESI = 6
EOL_RIGHE_LF_ATTESE = [8, 9, 10, 11, 13, 14]


# ===========================================================================
# utilita'
# ===========================================================================

def ora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def sha256_bytes(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


def profilo_eol(dati: bytes) -> dict:
    """Profilo dei fini riga. Il terminatore EREDITATO e' quello della prima
    riga terminata: e' cio' che `amend64` non guardava."""
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

def costruisci_record(utc: str, ref_file_sha: str, ref_self_sha: str) -> dict:
    return {
        "document": "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444",

        "item": "6.1/censimento_dei_registri_tre_proprieta_misurate_e_resumable_ridefinita",
        "type": "protocol",
        "utc": utc,

        "key": "six_one_register_census_three_measured_properties_and_resumable_"
               "redefined_as_a_runner_declaration",

        "numbering_rule": "Il numero di un emendamento e' la sua POSIZIONE "
                          "1-based in questo file. Questo e' il record %d." % NUMERO_RECORD,

        "amends_records": [47],

        "counts_before": {"ledger_su_disco": 67, "DOCUMENTED_AMENDMENTS": 67},
        "counts_after": {"ledger_su_disco": 68, "DOCUMENTED_AMENDMENTS": 68},
        "counts_note": "Regola del record 67: un campo di conteggi porta il numero "
                       "che i documenti avranno DOPO i patcher, non quello che hanno "
                       "mentre il record si scrive. DOCUMENTED_AMENDMENTS va portato "
                       "a 68 da paper2_patch_documented_amendments.py.",

        "json_path": "src/paper2_v1_amendments.jsonl; src/paper2_censimento_registri.py; "
                     "src/paper2_chiavi_registri.py; logs/censimento_v14.jsonl; "
                     "src/paper2_freeze_verify.py",

        "reference_file": REFERENCE_PATH_DEFAULT,
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,

        "old_value": "La voce 6.1 chiedeva che i JSONL di Fase 3, 4 e 4D fossero "
                     "append-only, atomici, crash-safe e resumable. Nessuno dei "
                     "quattro aggettivi era definito, la popolazione non era "
                     "delimitata, e non era dichiarato dove ciascuna proprieta' si "
                     "verifichi. In particolare `resumable` era trattata come una "
                     "proprieta' del registro.",

        "reason": "Le quattro proprieta' non si verificano nello stesso posto, e la "
                  "voce non lo diceva. Append-only strutturale, residuo di atomicita' "
                  "e residuo di crash-safety si MISURANO sul registro. Append-only "
                  "storico si misura solo contro uno stato precedente, quindi non e' "
                  "dimostrabile all'indietro. E `resumable` non e' una proprieta' del "
                  "registro affatto: e' una proprieta' del RUNNER, che il registro "
                  "puo' corroborare ma non produrre. Due strumenti l'hanno misurata "
                  "col metro sbagliato prima che la cosa fosse chiara, e sono "
                  "registrati qui perche' l'errore e' istruttivo: cercarla per NOME "
                  "di campo dava 33 FAIL su 48 con firma uniforme; cercarla per "
                  "UNICITA' restituiva `base.b1_fwhm`, `P_small_abs`, `_var_delta_piena` "
                  "e `seconds`, cioe' risultati e timestamp. Un float continuo su 2000 "
                  "record e' unico per costruzione: unicita' non e' identificazione. "
                  "Una proprieta' che fallisce sul 69% della popolazione con firma "
                  "uniforme non descrive la popolazione, descrive il metro.",

        "new_value": {
            "decisione_A_censimento_non_conformita":
                "6.1 e' un censimento con eccezioni dichiarate, non un requisito di "
                "conformita'. I registri sono append-only e in parte dentro il "
                "congelamento: riscriverli e' escluso. L'unica uscita ammessa per un "
                "registro che non soddisfa una proprieta' e' DICHIARARLA.",

            "decisione_B_popolazione":
                "Dentro i cachedelta_manifest_* (provenienza su cui poggia il 4.2b) e "
                "i gate*.jsonl (un cancello non append-only corromperebbe un verdetto "
                "come un registro di misura), con le proprieta' non applicabili "
                "marcate esplicitamente: NA e' un esito stampato, mai un pass "
                "silenzioso. CORRETTA il 15 settembre: i cinque tier del congelamento "
                "ensemble_v1_manifest_* erano rimasti fuori per svista, ed e' cio' che "
                "freeze_verify legge per dichiarare CLEAN. Lasciare il congelamento "
                "fuori da un censimento dei registri non si regge. Popolazione in "
                "scopo: 53 file, 67 915 righe.",

            "decisione_C_append_only_non_e_dimostrabile_all_indietro":
                "In una passata sola si misura la precondizione strutturale (una riga "
                "per record, nessun wrapper d'array, coda terminata). La proprieta' "
                "storica richiede un prima. Lo strumento STABILISCE la linea di base "
                "— lunghezza e digest per file — e da li' in avanti verifica che i "
                "primi n byte siano invariati. Verificato il 15 set su 121 file su "
                "121, zero prefissi modificati, zero file accorciati.",

            "misura":
                "121 file .jsonl, 78 067 righe; in scopo 53 file, 67 915 righe. "
                "append_strutturale, append_storico (contro linea di base), "
                "atomico_residuo e crashsafe_residuo: PASS ovunque, con un solo FAIL.",

            "unico_FAIL":
                "src/paper2_v1_amendments.jsonl su crashsafe_residuo: 61 CRLF e 6 LF "
                "su eredita' CRLF. GIA' DICHIARATO DAL RECORD 47 e non una eccezione "
                "nuova. Verificato invariato attraverso ventun emendamenti: il "
                "profilo era 40/6 su 46 record il 6 settembre, e' 61/6 su 67 oggi, "
                "con gli stessi indici 8 9 10 11 13 14. E' la verifica sperimentale "
                "del 'nothing is rewritten' che il 47 dichiarava.",

            "resumable_ridefinita":
                "Dichiarazione del runner, verificata sul registro. 53 righe, ognuna "
                "col file e le righe di origine. Sei modi: ripresa_dal_registro (16), "
                "na_una_passata (23), na_scansione (8), nessuna_ripresa_id (4), "
                "nessuna_ripresa_senza_id (2), da_leggere (0). La chiave di Fase 3 e' "
                "una tupla a dieci componenti letta a paper2_runner_fase3_mock.py "
                "righe 691-738, TOLLERANTE all'assenza perche' il runner la legge con "
                ".get(): un controllo di presenza darebbe FAIL su un registro corretto.",

            "il_grado_di_rischio_piu_alto":
                "ensemble_v2_{NGC,SGC}.jsonl: nessuna ripresa E nessun identificatore. "
                "paper2_runner_4_2a.py rifiuta il nome smoke sbagliato e --da fuori "
                "intervallo, ma non un --out gia' popolato; e --da e' un selettore di "
                "popolazione, non una ripresa (il selftest di paper2_fasi_v2.py righe "
                "572-577 lo dichiara per il caso gemello). Una seconda corsa "
                "appenderebbe 2000 record che nessun lettore per unione saprebbe "
                "distinguere dai primi. DICHIARATO, non riparato: la Fase 4 e' chiusa "
                "e quel runner non ripartira'.",

            "la_ripresa_migliore_del_programma":
                "paper1_remap.py righe 512-516 riprende SOLO se esistono sia la riga "
                "nel registro sia il file delle curve su disco. E' l'unico runner che "
                "verifica il prodotto laterale e non solo il registro: senza, "
                "un'unita' il cui .npy fosse sparito verrebbe saltata dalla riga che "
                "la dichiara fatta. Va in REPRODUCIBILITY.md come pattern.",

            "duplicati_attesi_non_sono_difetti":
                "per_mock_NGC_erosion_restrict.jsonl ha 600 record su 200 chiavi (tre "
                "passate) e SGC 400 su 200 (due). Dichiarati come duplicati ATTESI: "
                "una quarta passata inattesa esce FAIL. Ogni passata porta un "
                "sottoinsieme diverso di cells.*, quindi la lettura scientifica va "
                "fatta per UNIONE mentre la mappa di ripresa del runner e' LAST-WINS "
                "(done e' un dizionario per key). Due regole di lettura opposte sullo "
                "stesso file: voce per il 6.2.",

            "residuo_dichiarato":
                "67 file .jsonl sotto results/ restano non classificati: registri di "
                "Paper 1, smoke e item, fuori da Fase 3-4-4D. NON sono dichiarati "
                "fuori scopo perche' non sono stati aperti, e inventare uno scopo e' "
                "l'errore che questa voce esiste per non fare. L'uscita dello "
                "strumento resta 1 finche' non sono decisi: lavoro del 6.2.",

            "limiti_dichiarati": [
                "L'AST dice quali siti POSSONO fare una cosa, non quali l'hanno "
                "fatta. L'esecuzione si verifica sui registri.",
                "L'ispezione degli scrittori conta le chiamate open() con un modo "
                "letterale: chi appende attraverso un helper importato da un altro "
                "modulo non si vede. Una versione precedente leggeva sempre args[1] "
                "e mancava ogni Path.open(mode), dove il modo e' args[0].",
                "Il rilevatore di percorso chiede un separatore: un manifest di soli "
                "nomi di file non sarebbe riconosciuto come tale.",
                "L'euristica di classe legge `seed` come indice, quindi gate25.jsonl "
                "esce misurato `run` contro il dichiarato `gate`. Lasciato: il "
                "controllo che conta, gate_senza_verdetto, non scatta.",
            ],

            "tre_voci_aperte_per_il_6_2": [
                "gate53.jsonl porta tre record per due regioni. Il NGC delle "
                "12:48:02Z del 31 ago e' SUPERATO da quello delle 12:50:06Z, che "
                "sostituisce sd_draw_assumed con sd_draw_published e aggiunge "
                "sd_deconvolved_exact, sd_draw_exact, z_deconvolved_exact. "
                "spectral_fraction e' identica nei due, quindi il 76.3% non e' "
                "toccato; ma ogni numero che dipenda dalla sd delle estrazioni cambia "
                "secondo quale si legge, e il superamento NON e' marcato. La "
                "convenzione esiste (supersedes.utc, amend_reason, amended_utc nei "
                "compD) e qui non e' stata applicata.",
                "per_mock_*_erosion_restrict va letto per unione mentre la mappa di "
                "ripresa e' last-wins; va dichiarato quale record e' la fonte di quale "
                "numero.",
                "Il cancello '.bak atteso: 0' del §7 della consegna e' INCOMPATIBILE "
                "con paper2_patch_documented_amendments.py righe 86-87, che fa copy2 "
                "prima di ogni patch e lascia la copia in src/. Fallira' dopo ogni "
                "emendamento. Il rimedio va nel patcher — spostamento in logs/ a "
                "patch riuscita — non in un cancello che conta: il suo selftest gia' "
                "verifica 'nessun backup su rifiuto', quindi la disciplina c'e' per "
                "l'errore e manca per il successo.",
            ],

            "what_is_NOT_done":
                "Nessun registro e' stato riscritto, nessuna riga normalizzata, "
                "nessuna ripresa aggiunta a un runner. I sei LF del ledger restano. "
                "Le due mancanze di ripresa restano. Cambia che sono note e "
                "dichiarate, con il file e le righe in cui si guardano.",
        },

        "rules": {
            "una_proprieta_che_fallisce_ovunque_descrive_il_metro":
                "33 FAIL su 48 con due sole diciture e zero difetti sulle altre tre "
                "proprieta' non e' una popolazione difettosa: e' una misura sbagliata. "
                "Prima di dichiarare 33 eccezioni, rifare il metro.",
            "unicita_non_e_identificazione":
                "Su 2000 record un float continuo e' unico per costruzione, e un "
                "timestamp al secondo pure. Una chiave di ripresa deve esistere PRIMA "
                "del calcolo: e' cio' su cui il runner decide se saltare.",
            "la_chiave_di_ripresa_e_del_runner":
                "Il registro puo' corroborare una dichiarazione, non produrla. Ogni "
                "riga della tabella porta il sorgente e le righe da cui e' letta.",
            "NA_e_un_esito_stampato":
                "Una proprieta' non applicabile si stampa NA. Un pass silenzioso su "
                "una proprieta' che non si applica e' indistinguibile da un pass vero.",
            "non_si_dichiara_cio_che_non_si_e_letto":
                "Il modo `da_leggere` esiste per questo, non e' un pass e fa uscire "
                "non-zero. Oggi e' vuoto perche' gli undici per_mock_* sono stati "
                "letti, non perche' siano stati assunti.",
            "il_prefisso_e_l_unica_prova_dell_append_only":
                "Un file riscritto per intero si dimostra append-only in un modo solo: "
                "i primi n byte invariati. Copre insieme la normalizzazione dei LF, "
                "quella dei CRLF e la modifica di un record precedente.",
            "companion_documents":
                "checklist_paper2.md; paper2_stato.md; logs/censimento_v14.jsonl",
            "marker": "emendamento-68-censimento-dei-registri-voce-6-1",
        },

        "evidence":
            "logs/censimento_v14.jsonl, prodotto da src/paper2_censimento_registri.py "
            "v1.4 (selftest 150/150) il 15 set 2026. 121 file, 78 067 righe; in scopo "
            "53 file, 67 915 righe; append_strutturale, append_storico, "
            "atomico_residuo, crashsafe_residuo PASS su tutti tranne "
            "src/paper2_v1_amendments.jsonl su crashsafe (61 CRLF, 6 LF, righe 8 9 10 "
            "11 13 14, eredita' CRLF). Linea di base: 121 coperti, 0 falliti, 0 "
            "prefissi modificati. Ripresa per modo: 16 ripresa_dal_registro, 23 "
            "na_una_passata, 8 na_scansione, 4 nessuna_ripresa_id, 2 "
            "nessuna_ripresa_senza_id, 0 da_leggere. Cancello di riproduzione PASS a "
            "121 file. freeze_verify CLEAN alle 07:13:43Z con disco=documentati=67, "
            "34 836 file e 26.77144 GiB sui cinque tier, albero pulito. La rettifica "
            "al record 47 poggia su `git log --follow -- .gitattributes`: la regola "
            "`*.jsonl -text` entra col commit 684d1f3 del 25 ago 2026, dodici giorni "
            "prima del record 47, e `git check-attr text -- "
            "src/paper2_v1_amendments.jsonl` restituisce `text: unset`, cioe' -text "
            "esplicito, che scavalca core.autocrlf=true attivo su questa macchina.",

        "rettifica_del_record_47": {
            "cosa_diceva":
                "Il record 47 dichiara le sei righe LF inerti perche' '.gitattributes "
                "covers results/**, not src/, so a checkout with core.autocrlf could "
                "normalise those six lines and change the file's bytes with nothing "
                "noticing'.",
            "cosa_e_falso":
                "`.gitattributes` porta `*.jsonl -text` senza restrizione di cartella, "
                "dal commit 684d1f3 del 25 agosto 2026 — dodici giorni PRIMA del "
                "record 47. Il file e' dichiarato non-testo ai fini dei fini riga e "
                "-text scavalca core.autocrlf. Lo scenario di pericolo descritto NON "
                "era possibile quando e' stato scritto.",
            "la_conclusione_regge":
                "Le sei righe sono inerti, e piu' protette di quanto il 47 credesse. "
                "Cambia il meccanismo, non l'esito. Un record che spiega un'inerzia "
                "con una ragione sbagliata induce in errore chi lo leggera'.",
            "corollario_con_piu_mordente":
                "`*.json -text` protegge anche src/paper2_v1_reference.json, il cui "
                "file_sha256 e' un digest SUI BYTE di un file in src/ — precisamente "
                "la cosa che il 47 dichiara ostaggio di git. La regola 'hash the "
                "records, not the bytes' resta giusta in generale; questa istanza e' "
                "difesa da una riga di .gitattributes, e chi la legge deve sapere da "
                "cosa dipende.",
            "cosa_NON_si_fa":
                "Il record 47 non si riscrive. Questo lo emenda, come il 64 emenda il "
                "63.",
        },
    }


# ---------------------------------------------------------------------------
# I comandi che seguono l'append. CORRETTI il 15 set: la versione precedente
# stampava `paper2_patch_documented_amendments.py --da 67 --a 68` senza il
# sottocomando `apply` ne' `--file`, e il patcher rifiutava. L'errore veniva da
# una riga di `amend67` letta a meta' — un frammento preso per un comando.
# Chi riusa questo script come modello NON deve riportarselo dietro, quindi i
# comandi stanno qui e il selftest ne verifica la forma.
# ---------------------------------------------------------------------------

def comandi_seguenti(attesi: int) -> list:
    fv = "src\\paper2_freeze_verify.py"
    return [
        "python src\\paper2_patch_documented_amendments.py apply --file %s "
        "--da %d --a %d --dry-run" % (fv, attesi, NUMERO_RECORD),
        "python src\\paper2_patch_documented_amendments.py apply --file %s "
        "--da %d --a %d" % (fv, attesi, NUMERO_RECORD),
        "python src\\paper2_patch_documented_amendments.py verify --file %s "
        "--da %d --a %d" % (fv, attesi, NUMERO_RECORD),
        "python %s verify --jobs 4 --out logs\\fv.jsonl" % fv,
        "   atteso: CLEAN, disco = documentati = %d" % NUMERO_RECORD,
        "python src\\paper2_censimento_registri.py censimento --roots results src "
        "--baseline logs\\censimento_v14.jsonl --attesi-file 121",
        "   atteso: append_storico PASS sul ledger, crashsafe ancora FAIL a %d/%d"
        % (EOL_CRLF_ATTESI + 1, EOL_LF_ATTESI),
    ]


# ===========================================================================
# cancelli
# ===========================================================================

class Rifiuto(SystemExit):
    pass


def verifica_reference(percorso: Path) -> tuple:
    if not percorso.exists():
        raise Rifiuto("RIFIUTO: reference assente -> %s" % percorso)
    dati = percorso.read_bytes()
    sha = sha256_bytes(dati)
    if sha != REFERENCE_FILE_SHA256:
        raise Rifiuto(
            "RIFIUTO: il reference non e' quello validato da freeze_verify.\n"
            "  atteso    %s\n  calcolato %s\n"
            "  Rifare freeze_verify prima di appendere." % (REFERENCE_FILE_SHA256, sha))
    return sha, REFERENCE_SELF_SHA256


def verifica_prima(dati: bytes, attesi: int) -> dict:
    prof = profilo_eol(dati)

    if prof["n_righe"] != attesi:
        raise Rifiuto("RIFIUTO: il ledger ha %d record, attesi %d.\n"
                      "  Un secondo appendiscritto potrebbe aver gia' scritto."
                      % (prof["n_righe"], attesi))
    if not prof["coda_terminata"]:
        raise Rifiuto("RIFIUTO: il ledger non termina con un fine riga: la coda e' "
                      "parziale e appendere la incollerebbe al record nuovo.")
    if prof["ereditato"] != "crlf":
        raise Rifiuto("RIFIUTO: terminatore ereditato '%s', atteso 'crlf'."
                      % prof["ereditato"])
    if prof["crlf"] != EOL_CRLF_ATTESI or prof["lf"] != EOL_LF_ATTESI:
        raise Rifiuto("RIFIUTO: profilo dei fini riga %d CRLF / %d LF, attesi %d / %d."
                      % (prof["crlf"], prof["lf"], EOL_CRLF_ATTESI, EOL_LF_ATTESI))
    if prof["righe_lf"] != EOL_RIGHE_LF_ATTESE:
        raise Rifiuto("RIFIUTO: i LF isolati sono alle righe %s, attese %s (record 47)."
                      % (prof["righe_lf"], EOL_RIGHE_LF_ATTESE))

    try:
        record = righe_json(dati)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise Rifiuto("RIFIUTO: il ledger non e' JSONL integro: %s" % e)
    if len(record) != attesi:
        raise Rifiuto("RIFIUTO: %d record parsati su %d righe." % (len(record), attesi))

    return prof


def verifica_dopo(vecchio: bytes, nuovo: bytes, prof_prima: dict, record_nuovo: dict) -> None:
    # 1. IL PREFISSO. E' il cancello che copre tutto il resto.
    if len(nuovo) <= len(vecchio):
        raise Rifiuto("RIFIUTO: il file non e' cresciuto (%d -> %d byte)."
                      % (len(vecchio), len(nuovo)))
    if nuovo[:len(vecchio)] != vecchio:
        raise Rifiuto("RIFIUTO: il prefisso e' cambiato. Qualcosa ha riscritto un "
                      "record precedente o normalizzato un fine riga.")

    prof = profilo_eol(nuovo)

    # 2. i sei LF isolati sono ancora li', e sono ancora sei
    if prof["righe_lf"] != EOL_RIGHE_LF_ATTESE:
        raise Rifiuto("RIFIUTO: i LF isolati ora sono alle righe %s, attese %s."
                      % (prof["righe_lf"], EOL_RIGHE_LF_ATTESE))
    if prof["lf"] != prof_prima["lf"]:
        raise Rifiuto("RIFIUTO: i LF isolati sono passati da %d a %d."
                      % (prof_prima["lf"], prof["lf"]))

    # 3. esattamente un CRLF in piu': il record nuovo, e nessuna conversione
    if prof["crlf"] != prof_prima["crlf"] + 1:
        raise Rifiuto("RIFIUTO: i CRLF sono passati da %d a %d, atteso +1."
                      % (prof_prima["crlf"], prof["crlf"]))

    if prof["n_righe"] != prof_prima["n_righe"] + 1:
        raise Rifiuto("RIFIUTO: righe %d -> %d, atteso +1."
                      % (prof_prima["n_righe"], prof["n_righe"]))
    if not prof["coda_terminata"]:
        raise Rifiuto("RIFIUTO: il file non termina con un fine riga.")

    # 4. il record appeso e' il nostro, e il ledger e' ancora integro
    record = righe_json(nuovo)
    if len(record) != prof["n_righe"]:
        raise Rifiuto("RIFIUTO: %d record su %d righe." % (len(record), prof["n_righe"]))
    if record[-1] != record_nuovo:
        raise Rifiuto("RIFIUTO: l'ultimo record non e' quello costruito.")
    if len(record) != NUMERO_RECORD:
        raise Rifiuto("RIFIUTO: il ledger ha %d record, atteso %d."
                      % (len(record), NUMERO_RECORD))


# ===========================================================================
# scrittura: temporaneo piu' os.replace, nella stessa cartella
# ===========================================================================

def scrivi_atomico(ledger: Path, nuovo: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(ledger.parent), prefix=".amend68_", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(nuovo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(ledger))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def comando_applica(args) -> int:
    ledger = Path(args.ledger)
    if not ledger.exists():
        raise Rifiuto("RIFIUTO: ledger assente -> %s" % ledger)

    ref_file_sha, ref_self_sha = verifica_reference(Path(args.reference))
    vecchio = ledger.read_bytes()
    prof_prima = verifica_prima(vecchio, args.attesi)

    utc = ora_utc()
    record = costruisci_record(utc, ref_file_sha, ref_self_sha)
    linea = json.dumps(record, ensure_ascii=False, sort_keys=True)
    if "\n" in linea or "\r" in linea:
        raise Rifiuto("RIFIUTO: il record serializzato contiene un fine riga.")
    nuovo = vecchio + linea.encode("utf-8") + b"\r\n"

    print("=" * 74)
    print("RECORD %d — chiusura della voce 6.1" % NUMERO_RECORD)
    print("=" * 74)
    print("ledger        : %s" % ledger)
    print("record prima  : %d   (%d CRLF, %d LF alle righe %s)"
          % (prof_prima["n_righe"], prof_prima["crlf"], prof_prima["lf"],
             prof_prima["righe_lf"]))
    print("reference     : %s  self %s" % (ref_file_sha[:16], ref_self_sha[:16]))
    print("utc           : %s" % utc)
    print("byte          : %d -> %d  (+%d)"
          % (len(vecchio), len(nuovo), len(nuovo) - len(vecchio)))
    print("sha256 dopo   : %s" % sha256_bytes(nuovo))
    print()

    if args.dry_run:
        # Si eseguono comunque TUTTI i cancelli del dopo, in memoria.
        verifica_dopo(vecchio, nuovo, prof_prima, record)
        print("DRY-RUN: nulla e' stato scritto. Tutti i cancelli del dopo superati.")
        print()
        print("Per applicare, rilancia senza --dry-run.")
        return 0

    if args.backup:
        backup = Path(args.backup)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(ledger), str(backup))
        print("backup        : %s" % backup)

    scrivi_atomico(ledger, nuovo)

    riletto = ledger.read_bytes()
    verifica_dopo(vecchio, riletto, prof_prima, record)
    if riletto != nuovo:
        raise Rifiuto("RIFIUTO: il file riletto non coincide con quello scritto.")

    prof = profilo_eol(riletto)
    print("APPESO. record %d, %d CRLF, %d LF alle righe %s, prefisso invariato."
          % (prof["n_righe"], prof["crlf"], prof["lf"], prof["righe_lf"]))
    print()
    print("Ora, in quest'ordine:")
    for riga in comandi_seguenti(args.attesi):
        print("  %s" % riga)
    print()
    print("Poi lo spostamento dei .bak in logs\\, che questo record dichiara "
          "incompatibile col cancello '.bak atteso: 0'.")
    return 0


# ===========================================================================
# selftest
# ===========================================================================

class Contatore:
    def __init__(self):
        self.ok = 0
        self.ko = []

    def verifica(self, nome, cond):
        if cond:
            self.ok += 1
        else:
            self.ko.append(nome)

    def uguale(self, nome, ott, att):
        self.verifica("%s (ottenuto %r, atteso %r)" % (nome, ott, att), ott == att)

    def rifiuta(self, nome, fn):
        try:
            fn()
            self.ko.append("%s (nessun rifiuto)" % nome)
        except SystemExit:
            self.ok += 1


def _ledger_finto(n_record=67, righe_lf=EOL_RIGHE_LF_ATTESE):
    """Ledger di prova con lo stesso profilo di quello vero: CRLF ereditato,
    sei LF isolati agli stessi indici."""
    pezzi = []
    for i in range(1, n_record + 1):
        linea = json.dumps({"item": "prova/%d" % i, "utc": "2026-08-%02dT00:00:00+00:00"
                            % (1 + i % 28)}, ensure_ascii=False, sort_keys=True)
        fine = b"\n" if i in righe_lf else b"\r\n"
        pezzi.append(linea.encode("utf-8") + fine)
    return b"".join(pezzi)


def comando_selftest(args) -> int:
    c = Contatore()

    # ---- 1. profilo dei fini riga ----------------------------------------
    d = _ledger_finto()
    p = profilo_eol(d)
    c.uguale("finto: righe", p["n_righe"], 67)
    c.uguale("finto: crlf", p["crlf"], 61)
    c.uguale("finto: lf", p["lf"], 6)
    c.uguale("finto: righe lf", p["righe_lf"], EOL_RIGHE_LF_ATTESE)
    c.uguale("finto: ereditato", p["ereditato"], "crlf")
    c.uguale("finto: coda terminata", p["coda_terminata"], True)

    # ---- 2. i cancelli del prima -----------------------------------------
    c.verifica("prima: ledger conforme passa", verifica_prima(d, 67) is not None)
    c.rifiuta("prima: conteggio sbagliato", lambda: verifica_prima(d, 66))
    c.rifiuta("prima: coda non terminata", lambda: verifica_prima(d[:-2], 67))
    c.rifiuta("prima: LF in posizione diversa",
              lambda: verifica_prima(_ledger_finto(righe_lf=[8, 9, 10, 11, 13, 20]), 67))
    c.rifiuta("prima: un LF in meno",
              lambda: verifica_prima(_ledger_finto(righe_lf=[8, 9, 10, 11, 13]), 67))
    c.rifiuta("prima: eredita' LF",
              lambda: verifica_prima(_ledger_finto(righe_lf=list(range(1, 68))), 67))

    # ---- 3. append corretto: tutti i cancelli del dopo passano -----------
    rec = costruisci_record("2026-09-15T12:00:00+00:00", REFERENCE_FILE_SHA256,
                            REFERENCE_SELF_SHA256)
    linea = json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8")
    prof = profilo_eol(d)
    buono = d + linea + b"\r\n"
    verifica_dopo(d, buono, prof, rec)
    c.verifica("dopo: append corretto passa", True)

    # ---- 4. DIFETTO: append con LF invece del CRLF ereditato -------------
    # E' la forma di cio' che ha prodotto i sei LF del record 47.
    c.rifiuta("dopo: append con LF isolato rifiutato",
              lambda: verifica_dopo(d, d + linea + b"\n", prof, rec))

    # ---- 5. DIFETTO: normalizzazione dei sei LF a CRLF -------------------
    # E' il caso che `amend64` non vedeva. Il prefisso lo prende.
    normalizzato = _ledger_finto(righe_lf=[]) + linea + b"\r\n"
    c.rifiuta("dopo: normalizzazione dei LF rifiutata",
              lambda: verifica_dopo(d, normalizzato, prof, rec))

    # ---- 6. DIFETTO: normalizzazione dei CRLF a LF -----------------------
    tutto_lf = _ledger_finto(righe_lf=list(range(1, 68))) + linea + b"\n"
    c.rifiuta("dopo: normalizzazione dei CRLF rifiutata",
              lambda: verifica_dopo(d, tutto_lf, prof, rec))

    # ---- 7. DIFETTO: un record precedente riscritto ----------------------
    alterato = bytearray(d)
    i = alterato.index(b'"prova/40"')
    alterato[i + 8:i + 10] = b"41"
    c.rifiuta("dopo: record precedente riscritto rifiutato",
              lambda: verifica_dopo(d, bytes(alterato) + linea + b"\r\n", prof, rec))

    # ---- 8. DIFETTO: file accorciato -------------------------------------
    c.rifiuta("dopo: file accorciato rifiutato",
              lambda: verifica_dopo(d, d[:100], prof, rec))

    # ---- 9. DIFETTO: due record appesi invece di uno ---------------------
    c.rifiuta("dopo: due record rifiutati",
              lambda: verifica_dopo(d, d + linea + b"\r\n" + linea + b"\r\n", prof, rec))

    # ---- 10. DIFETTO: record diverso da quello costruito ----------------
    altro = json.dumps({"item": "altro"}, ensure_ascii=False).encode("utf-8")
    c.rifiuta("dopo: record estraneo rifiutato",
              lambda: verifica_dopo(d, d + altro + b"\r\n", prof, rec))

    # ---- 11. il record e' JSON su UNA riga -------------------------------
    testo = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    c.verifica("record: nessun a-capo nel serializzato",
               "\n" not in testo and "\r" not in testo)
    c.verifica("record: rileggibile", json.loads(testo) == rec)
    c.verifica("record: non vuoto", len(testo) > 2000)

    # ---- 12. campi obbligatori -------------------------------------------
    for campo in ("item", "type", "utc", "key", "numbering_rule", "reason",
                  "new_value", "rules", "evidence", "json_path",
                  "reference_file", "reference_file_sha256", "reference_self_sha256",
                  "counts_before", "counts_after", "amends_records",
                  "rettifica_del_record_47"):
        c.verifica("record: campo %s presente" % campo, campo in rec)

    # ---- 13. la regola dei conteggi del record 67 ------------------------
    c.uguale("counts_before: ledger", rec["counts_before"]["ledger_su_disco"], 67)
    c.uguale("counts_after: ledger", rec["counts_after"]["ledger_su_disco"], 68)
    c.uguale("counts_after: DOCUMENTED_AMENDMENTS",
             rec["counts_after"]["DOCUMENTED_AMENDMENTS"], 68)
    c.verifica("counts: il campo porta il numero DOPO i patcher",
               "DOPO i patcher" in rec["counts_note"])

    # ---- 14. il record emenda il 47 --------------------------------------
    c.uguale("amends_records", rec["amends_records"], [47])
    c.verifica("rettifica: nomina il commit", "684d1f3" in rec["evidence"])
    c.verifica("rettifica: dichiara cosa NON si fa",
               "non si riscrive" in rec["rettifica_del_record_47"]["cosa_NON_si_fa"])

    # ---- 15. numerazione per posizione -----------------------------------
    c.verifica("numbering_rule: dichiara la posizione",
               "POSIZIONE" in rec["numbering_rule"] and "68" in rec["numbering_rule"])

    # ---- 16. i numeri della misura sono quelli del censimento -----------
    ev = rec["evidence"]
    for numero in ("121", "78 067", "53", "67 915", "150/150", "34 836"):
        c.verifica("evidence: porta %s" % numero, numero in ev)

    # ---- 17. il reference: rifiuto se non e' quello validato -------------
    with tempfile.TemporaryDirectory() as tmp:
        falso = Path(tmp) / "ref.json"
        falso.write_text('{"nope": 1}', encoding="utf-8")
        c.rifiuta("reference: digest diverso rifiutato",
                  lambda: verifica_reference(falso))
        c.rifiuta("reference: assente rifiutato",
                  lambda: verifica_reference(Path(tmp) / "manca.json"))

    # ---- 18. il dry-run non scrive ---------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        led = Path(tmp) / "ledger.jsonl"
        led.write_bytes(d)
        prima = led.read_bytes()
        ref = Path(tmp) / "ref.json"
        ref.write_bytes(b"x")          # digest sbagliato: deve rifiutare prima

        class A:
            ledger = str(led); reference = str(ref); attesi = 67
            backup = None; dry_run = True
        c.rifiuta("dry-run: rifiuta col reference sbagliato",
                  lambda: comando_applica(A()))
        c.verifica("dry-run: non ha scritto", led.read_bytes() == prima)

    # ---- 19. scrittura atomica: il temporaneo sparisce ------------------
    with tempfile.TemporaryDirectory() as tmp:
        led = Path(tmp) / "ledger.jsonl"
        led.write_bytes(d)
        scrivi_atomico(led, d + linea + b"\r\n")
        c.verifica("atomico: contenuto scritto", led.read_bytes() == d + linea + b"\r\n")
        residui = [x for x in Path(tmp).iterdir() if x.name.startswith(".amend68_")]
        c.uguale("atomico: nessun temporaneo residuo", residui, [])

    # ---- 20. il temporaneo nasce nella stessa cartella -------------------
    # os.replace e' atomico solo sullo stesso filesystem.
    with tempfile.TemporaryDirectory() as tmp:
        led = Path(tmp) / "sub" / "ledger.jsonl"
        led.parent.mkdir()
        led.write_bytes(d)
        scrivi_atomico(led, d + linea + b"\r\n")
        c.verifica("atomico: sottocartella", led.exists())

    # ---- 21. i comandi stampati sono comandi interi ----------------------
    # DIFETTO RIPRODOTTO: la versione precedente stampava il patcher senza il
    # sottocomando `apply` e senza --file, e il patcher rifiutava.
    righe = comandi_seguenti(67)
    patcher = [r for r in righe if "paper2_patch_documented_amendments.py" in r]
    c.uguale("comandi: tre invocazioni del patcher", len(patcher), 3)
    for r in patcher:
        c.verifica("comandi: porta un sottocomando",
                   " apply " in r or " verify " in r)
        c.verifica("comandi: porta --file", "--file" in r)
        c.verifica("comandi: porta --da e --a", "--da" in r and "--a " in r)
    c.verifica("comandi: un dry-run prima dell'apply",
               patcher[0].endswith("--dry-run") and not patcher[1].endswith("--dry-run"))
    c.verifica("comandi: nessun segnaposto",
               not any(ch in " ".join(righe) for ch in "<>"))
    c.verifica("comandi: freeze_verify in coda",
               any("paper2_freeze_verify.py verify" in r for r in righe))
    c.verifica("comandi: il censimento cita la linea di base",
               any("--baseline" in r for r in righe))

    totale = c.ok + len(c.ko)
    print("selftest: %d/%d" % (c.ok, totale))
    if c.ko:
        print("FALLITI:")
        for nome in c.ko:
            print("  %s" % nome)
        return 1
    return 0


# ===========================================================================

def principale(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="paper2_append_amend68.py",
        description="Appende il record 68 — chiusura della voce 6.1.")
    sub = ap.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("applica", help="appende il record (usa prima --dry-run)")
    p.add_argument("--ledger", default=LEDGER_DEFAULT)
    p.add_argument("--reference", default=REFERENCE_PATH_DEFAULT)
    p.add_argument("--attesi", type=int, default=ATTESI_DEFAULT,
                   help="record sul disco PRIMA dell'append (default %d)" % ATTESI_DEFAULT)
    p.add_argument("--backup", default=None,
                   help="copia del ledger prima dell'append, es. logs\\amend68_pre.jsonl")
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.set_defaults(funzione=comando_applica)

    p = sub.add_parser("selftest", help="riproduce ogni difetto prima di dichiararlo preso")
    p.set_defaults(funzione=comando_selftest)

    args = ap.parse_args(argv)
    return args.funzione(args)


if __name__ == "__main__":
    sys.exit(principale())

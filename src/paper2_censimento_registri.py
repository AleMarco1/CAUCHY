#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_censimento_registri.py — voce 6.1 della Fase 6 del Paper 2.

Censisce i registri JSONL di Fase 3, 4 e 4D contro quattro proprieta'
dichiarate: append-only, atomico, crash-safe, resumable.

LE QUATTRO PROPRIETA' NON SI VERIFICANO NELLO STESSO POSTO.
Questo strumento lo dichiara invece di nasconderlo.

  append-only  strutturale : MISURATO sul registro (una riga per record,
                             nessun wrapper d'array, coda terminata)
  append-only  storico     : MISURATO solo contro una linea di base
                             precedente (sottocomando `censimento --baseline`).
                             Senza baseline l'esito e' NON_VERIFICABILE, mai
                             un pass.
  atomico                  : nel registro si vede solo il RESIDUO (nessuna
                             riga troncata, nessun byte NUL, nessuna riga non
                             parsabile). La proprieta' vera sta nel percorso
                             di scrittura -> sottocomando `scrittori`,
                             dichiarato come ISPEZIONE, non come misura.
  crash-safe               : idem, piu' il terminatore di riga coerente con
                             quello EREDITATO dal file (non con un CRLF
                             assoluto: e' il difetto di `amend64`).
  resumable                : MISURATO sul registro (esiste una chiave di
                             ripresa, i suoi valori sono stringhe). NA per i
                             registri di cancello, che non riprendono.

Sottocomandi
  censimento   misura ogni registro trovato; cancello di riproduzione su
               conteggi (--attesi-file / --attese-righe)
  scrittori    ispezione AST dei percorsi di scrittura in src\\
  selftest     riproduce ogni difetto su fixture prima di dichiararlo rilevato

Ambiente: Windows/PowerShell, D:\\projects\\cauchy, comandi dalla radice.
Nessuna dipendenza fuori dalla libreria standard.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA = "paper2_censimento_registri_v1"
VERSIONE = "1.6"

# ---------------------------------------------------------------------------
# Dove lo strumento puo' scrivere.
# Record 53 e l'incidente n1_desi_nu_SGC.npy: uno strumento del Paper 2 non
# scrive fuori da results/paper2. logs/ e' ammesso perche' e' dove vive fv.jsonl.
# ---------------------------------------------------------------------------
USCITE_AMMESSE = ("results/paper2", "logs")

# ---------------------------------------------------------------------------
# CLASSIFICAZIONE DICHIARATA.
# Il nome del file e' una DICHIARAZIONE, non una misura. Ogni riga qui sotto
# viene incrociata con la classe misurata dal contenuto; una discordanza fa
# fallire il censimento. Un file che non cade in nessuna riga e' riportato
# come `non_classificato` e fa fallire il censimento: la popolazione si
# estende a mano, con un motivo, non per inerzia.
#
# (glob sul nome base, classe dichiarata, in_scopo_6_1, motivo)
# ---------------------------------------------------------------------------
CLASSI_DICHIARATE = (
    # --- Fase 3, lato mock e lato dati -------------------------------------
    ("fase3_mock.jsonl", "run", True, "Fase 3 lato mock, k0..k3, due emisferi, 38 record smoke"),
    ("fase3.jsonl", "run", True, "Fase 3 lato dati, ladder per punto e regione"),
    ("fase3_mock_ripattern.jsonl", "run", True, "Fase 3, repliche randomizzate"),
    ("fase3_mock_off_*.jsonl", "run", True, "Fase 3 sezione C, offset"),
    ("fase3_surrogato_fisso.jsonl", "run", True, "Fase 3, maschera fissa"),
    ("surrogato_aff.jsonl", "run", True, "Fase 3, fit del surrogato"),
    ("ripattern_geom.jsonl", "run", True, "Fase 3, diagnostica geometrica"),
    ("preflight_*.jsonl", "run", True, "Fase 3, pre-flight geometrico 3.0a"),
    ("fase2.jsonl", "run", True, "Fase 2, ancora operativa dei due record d2"),
    # --- Fase 4, ensemble v2 ------------------------------------------------
    ("per_mock_*_R5.jsonl", "run", True, "ensemble canonico 2000 mock, base.N_H1"),
    ("per_mock_*.jsonl", "run", True, "registri d'ensemble per realizzazione"),
    ("onepoint_v1_*.jsonl", "run", True, "statistiche a un punto v1"),
    ("ensemble_v2_*.jsonl", "run", True, "ensemble v2, runner 4.2a"),
    ("fasi_mock_pr_v1_*.jsonl", "run", True, "randomizzazione di fase v1"),
    ("n10_phases_*.jsonl", "run", True, "fasi n=10, ingressi di gate53"),
    ("coppie_fase5_*.jsonl", "run", True, "coppie di Fase 5, ingresso di gate53 SGC"),
    ("q5_margine.jsonl", "run", True, "margine di Q5, record 65"),
    # --- Fase 4D, Componente D ---------------------------------------------
    ("compD_*.jsonl", "run", True, "Componente D, risposta ai parametri cosmologici"),
    # --- registri di cancello ----------------------------------------------
    ("gate*.jsonl", "gate", True, "registro di cancello: un verdetto, nessuna ripresa"),
    # --- manifest ----------------------------------------------------------
    ("cachedelta_manifest_*.jsonl", "manifest", True,
     "manifest della cache delta: provenienza su cui poggia il 4.2b, dentro per decisione B"),
    ("ensemble_v1_manifest_*.jsonl", "manifest", True,
     "i cinque tier del congelamento: sono cio' che freeze_verify legge per "
     "dichiarare CLEAN. Erano fuori per una svista della decisione B, corretta "
     "il 15 set: lasciare fuori il congelamento da un censimento dei registri "
     "non si regge."),
    # --- fuori dallo scopo di 6.1, ma classificati e non ignorati -----------
    ("paper2_v1_amendments.jsonl", "ledger", False,
     "registro degli emendamenti: append-only per sua natura, ma non e' un run"),
    ("fv.jsonl", "log", False, "registro di freeze_verify, non e' un run di misura"),
    ("censimento_registri.jsonl", "log", False, "uscita di questo strumento"),
    ("censimento_verdetti.jsonl", "log", False, "uscita del censimento dei verdetti, voce 6.9"),
    # --- i 67 lasciati non classificati dal 15 set: voce 6.2-vi (g), 18 set --
    # Nome ESATTO, mai un glob: un file nuovo resta non classificato e fa
    # fallire il censimento, come deve. Fuori scopo 6.1 perche' CHIUSI: le
    # proprieta' di 6.1 riguardano registri che un runner appende, e nessun
    # runner li riprende (fasi 3-5 chiuse, record 59-60; revisione del Paper 1
    # chiusa). L'append storico resta verificato per tutti dalla baseline.
    # La citazione nel motivo e' cio' che serve alla 6.2; e' un'istantanea.
    ("m2_fiducial_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("m2b_hodscatter_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("n10b_control_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("n1_spectra_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 50, 52, 54, 71"),
    ("n1b_spectra_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 50, 52, 54, 71, 75; modifiche_paper1.md"),
    ("n1c_bands_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("n2_persistence_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: checklist"),
    ("n6_fkp_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 56"),
    ("n7_nfw_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; registro del test NFW del Paper 1 §7.1 e della riga 5 del budget; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("n8_masks_128.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 60; budget, modifiche_paper1.md"),
    ("n8b_masks_128_B.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; citato: record 60; checklist, budget, modifiche_paper1.md"),
    ("n9_res256_NGC.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("per_target_NGC_mirror_lfl.jsonl", "run", False,
     "Paper 1, registro di revisione; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("cancello_nu_NGC.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 54"),
    ("d3_check.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("d6_incertezze.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 63, 64, 65"),
    ("d6bis.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 63, 64, 65"),
    ("dmed_NGC.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 6"),
    ("dmed_SGC.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 6, 7"),
    ("due_lati.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 19, 20, 21, 22; checklist"),
    ("fase3_analisi.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 15; checklist, budget, modifiche_paper1.md"),
    ("fase3_budget.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 40, 46, 49; checklist, budget"),
    ("fase3_intersezione.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 25"),
    ("fase3_intersezione_verdetto.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("fase3_maskpass1.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 25"),
    ("fase3_mock_carve777.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 26"),
    ("fase3_mock_carve777_b6.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 39"),
    ("fase3_mock_fid_ripetizione.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: checklist"),
    ("fase3_mock_fixedobs.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 38"),
    ("fase3_mock_realspace.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 35, 37"),
    ("fase3_mock_realspace_NULLO.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 35, 36"),
    ("fase3_mock_smoke.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("fase3_surrogato.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("fase3_surrogato_pass1.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("fasi_desi_pr_NGC.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("fasi_desi_pr_SGC.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("fasi_mock_pr_v2_NGC.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("fasi_mock_pr_v2_SGC.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("gazione_32d.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 44"),
    ("item12a_cosmo.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 15, 19; checklist"),
    ("item12a_geom_NGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 13; checklist"),
    ("item12b_NGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 2, 71"),
    ("item12b_SGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 2, 3, 7, 71"),
    ("item13a.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("item13rev2_NGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 74"),
    ("item13rev2_SGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: record 74"),
    ("item15a_NGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("item15a_SGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("item15a_g13_NGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: checklist"),
    ("item15a_g13_SGC.jsonl", "run", False,
     "Paper 2, item del referee; chiuso, fuori scopo 6.1; citato: checklist"),
    ("smoke_1punto_NGC.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_1punto_NGC_sommario.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_offset0.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_post32d.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; citato: record 44"),
    ("smoke_pre32d.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; citato: record 44"),
    ("smoke_v2_NGC.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_NGC_ancore.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_NGC_ancore_sommario.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_NGC_appaiato.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_NGC_appaiato_sommario.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_NGC_sommario.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_SGC.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_SGC_ancora.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_SGC_ancora_sommario.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("smoke_v2_SGC_sommario.jsonl", "run", False,
     "smoke: prova di funzionamento; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("survey_ancora_SGC.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; non citato al 18 set"),
    ("tabres_probe.jsonl", "run", False,
     "Paper 2, registro di run di fase chiusa; chiuso, fuori scopo 6.1; citato: record 14, 51"),
    # --- registri di figura, Fase 7 (1.6, 25 set 2026, Z-censimento-fig) -----
    # Nome ESATTO, come i 67: una figura nuova resta non classificata finche' non
    # e' dichiarata. Uno script di figura appende un record per run (numeri
    # disegnati, sha degli ingressi e del PDF); non e' un run di misura.
    ("fig_F1.jsonl", "log", False,
     "registro di figura F1, src/paper2_fig_F1.py; non in scopo 6.1: un record per run, "
     "i numeri vengono da registri gia' censiti, verify cerca il record per sha del PDF"),
    ("fig_F7.jsonl", "log", False,
     "registro di figura F7, src/paper2_fig_F7.py; non in scopo 6.1: un record per run, "
     "i numeri vengono da registri gia' censiti, verify cerca il record per sha del PDF"),
)

# ---------------------------------------------------------------------------
# Applicabilita' delle quattro proprieta' per classe.
# NA e' un esito stampato, non un pass silenzioso.
# ---------------------------------------------------------------------------
APPLICABILITA = {
    "run": {"append_strutturale": True, "atomico_residuo": True,
            "crashsafe_residuo": True, "resumable": True},
    "gate": {"append_strutturale": True, "atomico_residuo": True,
             "crashsafe_residuo": True, "resumable": False},
    "manifest": {"append_strutturale": True, "atomico_residuo": True,
                 "crashsafe_residuo": True, "resumable": True},
    "ledger": {"append_strutturale": True, "atomico_residuo": True,
               "crashsafe_residuo": True, "resumable": False},
    "log": {"append_strutturale": True, "atomico_residuo": True,
            "crashsafe_residuo": True, "resumable": False},
}

# ---------------------------------------------------------------------------
# Chiavi di ripresa. Nomi dichiarati, piu' i nomi che contengono "key"/"chiave".
# `config_hash` e' elencato a parte: paper2_stato.md §14 dichiara che NON e'
# un ancoraggio degli ingressi, quindi un registro la cui sola chiave sia
# quella e' segnalato, non promosso.
# ---------------------------------------------------------------------------
CHIAVI_RIPRESA = ("key", "resume_key", "run_key", "cache_key", "chiave",
                  "chiave_ripresa", "record_key", "id")
CHIAVI_NON_SUFFICIENTI = ("config_hash",)

# Nomi di campo che segnalano un verdetto (per la classe misurata).
CAMPI_VERDETTO = ("verdetto", "esito", "verdict", "status", "stato", "gate", "cancello",
                  "pass", "passed")
# Profondita' e larghezza della ricerca del verdetto dentro un record (1.5).
PROFONDITA_VERDETTO = 3
MAX_ELEMENTI_VERDETTO = 50
VALORI_VERDETTO = ("PASS", "FAIL", "CLEAN", "DISCREPANCY", "OK", "KO",
                   "CONFERMATA", "SMENTITA", "NON_DECIDIBILE", "PASSATO", "FALLITO")

# Nomi di campo che segnalano un indice di realizzazione o di punto.
CAMPI_INDICE = ("idx", "index", "indice", "i_mock", "imock", "mock", "mock_idx",
                "realizzazione", "realization", "punto", "point", "seed", "n", "k")

ESTENSIONI_PERCORSO = (".npy", ".npz", ".jsonl", ".json", ".csv", ".fits",
                       ".txt", ".h5", ".hdf5", ".pkl", ".md", ".py")


# ===========================================================================
# utilita'
# ===========================================================================

def ora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


def rel_posix(percorso: Path, radice: Path) -> str:
    """Percorso relativo in forma POSIX: indipendente dalla piattaforma."""
    try:
        rel = percorso.resolve().relative_to(radice.resolve())
    except ValueError:
        rel = percorso
    return str(PurePosixPath(*rel.parts))


def e_esadecimale_64(valore) -> bool:
    if not isinstance(valore, str) or len(valore) != 64:
        return False
    return all(c in "0123456789abcdefABCDEF" for c in valore)


def sembra_percorso(valore) -> bool:
    if not isinstance(valore, str) or len(valore) < 3:
        return False
    if "/" not in valore and "\\" not in valore:
        return False
    minuscolo = valore.lower()
    return any(minuscolo.endswith(e) for e in ESTENSIONI_PERCORSO)


def verifica_uscita(percorso: Path) -> None:
    """Rifiuta di scrivere fuori dalle cartelle ammesse. Record 53."""
    normalizzato = str(percorso).replace("\\", "/")
    for ammessa in USCITE_AMMESSE:
        if ("/" + ammessa + "/") in ("/" + normalizzato) or normalizzato.startswith(ammessa + "/"):
            return
    raise SystemExit(
        "RIFIUTO: uscita fuori dalle cartelle ammesse %s -> %s\n"
        "  Record 53: uno strumento del Paper 2 non scrive dove il freeze guarda."
        % (list(USCITE_AMMESSE), percorso)
    )


# ---------------------------------------------------------------------------
# RIPRESA DICHIARATA — voce 6.1, sostituisce CHIAVI_RIPRESA.
#
# La chiave di ripresa NON si deduce dal registro: e' una proprieta' del
# runner. Il censimento del 15 settembre lo ha dimostrato per assurdo —
# cercandola per nome dava 33 FAIL su 48 con firma uniforme, e cercandola per
# unicita' dava `base.b1_fwhm` e `seconds`, cioe' risultati e timestamp.
# Qui ogni riga e' LETTA nel sorgente del runner, col punto esatto, e il
# registro serve solo a verificarla.
#
# modo:
#   ripresa_dal_registro     il runner rilegge il registro e salta le unita'
#                            gia' fatte. VERIFICABILE: la chiave dichiarata
#                            deve dare `duplicati_attesi` duplicati.
#   nessuna_ripresa_id       nessuna ripresa, ma un identificatore dell'unita'
#                            di lavoro esiste nel registro. VERIFICABILE: e'
#                            unico. Una seconda corsa sarebbe deduplicabile.
#   nessuna_ripresa_senza_id nessuna ripresa e nessun identificatore. Una
#                            seconda corsa produce record indistinguibili.
#                            E' il grado di rischio piu' alto.
#   na_una_passata           lo strumento non itera su una popolazione che si
#                            possa riprendere: una corsa, pochi record.
#   na_scansione             scansione o riscrittura di campo, non un run.
#   da_leggere               runner non ancora letto. NON e' un pass: conta
#                            come lacuna e fa uscire non-zero.
#
# `record_al_15set` e' il conteggio al momento della dichiarazione. Se cambia,
# lo strumento segnala DA_RIVEDERE: la dichiarazione e' piu' vecchia del
# registro. Regola del record 67 applicata alle dichiarazioni.
# ---------------------------------------------------------------------------
RIPRESA_DICHIARATA = {
    # --- ripresa vera, chiave riletta dal registro -------------------------
    "fase3_mock.jsonl": {
        "modo": "ripresa_dal_registro",
        "runner": "src/paper2_runner_fase3_mock.py:691-738",
        "chiave": ["region", "index", "carve_reseed", "points:chiavi", "erosions",
                   "real_space", "fixed_observables", "replica_randomise",
                   "rot_seed", "origin_offset"],
        "booleani": ["real_space", "fixed_observables", "replica_randomise"],
        "esclusi_se": "smoke",
        "duplicati_attesi": 0,
        "record_al_15set": 2038,
        "motivo": "tupla a dieci componenti; ogni componente ha il motivo scritto "
                  "nel sorgente. I record smoke sono esclusi da `done` alla riga 696.",
    },
    "fase3_mock_off_hi.jsonl": {
        "modo": "ripresa_dal_registro",
        "runner": "src/paper2_runner_fase3_mock.py:691-738",
        "chiave": ["region", "index", "carve_reseed", "points:chiavi", "erosions",
                   "real_space", "fixed_observables", "replica_randomise",
                   "rot_seed", "origin_offset"],
        "booleani": ["real_space", "fixed_observables", "replica_randomise"],
        "esclusi_se": "smoke",
        "duplicati_attesi": 0,
        "record_al_15set": 400,
        "motivo": "stesso runner; origin_offset costante e dentro la chiave (sezione C).",
    },
    "fase3_mock_off_lo.jsonl": {
        "modo": "ripresa_dal_registro",
        "runner": "src/paper2_runner_fase3_mock.py:691-738",
        "chiave": ["region", "index", "carve_reseed", "points:chiavi", "erosions",
                   "real_space", "fixed_observables", "replica_randomise",
                   "rot_seed", "origin_offset"],
        "booleani": ["real_space", "fixed_observables", "replica_randomise"],
        "esclusi_se": "smoke",
        "duplicati_attesi": 0,
        "record_al_15set": 400,
        "motivo": "stesso runner; origin_offset costante e dentro la chiave (sezione C).",
    },
    "fase3_mock_ripattern.jsonl": {
        "modo": "ripresa_dal_registro",
        "runner": "src/paper2_runner_fase3_mock.py:691-738",
        "chiave": ["region", "index", "carve_reseed", "points:chiavi", "erosions",
                   "real_space", "fixed_observables", "replica_randomise",
                   "rot_seed", "origin_offset"],
        "booleani": ["real_space", "fixed_observables", "replica_randomise"],
        "esclusi_se": "smoke",
        "duplicati_attesi": 0,
        "record_al_15set": 400,
        "motivo": "stesso runner; replica_randomise e rot_seed dentro la chiave.",
    },
    "n10_phases_*.jsonl": {
        "modo": "ripresa_dal_registro",
        "runner": "src/paper1_rev_n10_phases.py:220-244",
        "chiave": ["tipo", "idx"],
        "duplicati_attesi": 0,
        "record_al_15set": 150,
        "motivo": "50 desi_pr piu' 100 mock_pr; gli indici mock partono da 200, "
                  "quindi disgiunti dai 0-49 di DESI e `idx` sarebbe unico da solo.",
    },

    # --- nessuna ripresa, identificatore presente -------------------------
    "onepoint_v1_NGC.jsonl": {
        "modo": "nessuna_ripresa_id",
        "runner": "src/paper2_passata_1punto.py:769-780",
        "chiave": ["idx"],
        "record_al_15set": 2000,
        "motivo": "nessun done, nessuna guardia su --out; `idx` unico su 2000 "
                  "record, quindi una seconda corsa sarebbe deduplicabile.",
    },
    "onepoint_v1_SGC.jsonl": {
        "modo": "nessuna_ripresa_id",
        "runner": "src/paper2_passata_1punto.py:769-780",
        "chiave": ["idx"],
        "record_al_15set": 2000,
        "motivo": "come NGC.",
    },
    "fasi_mock_pr_v1_NGC.jsonl": {
        "modo": "nessuna_ripresa_id",
        "runner": "src/paper2_fasi_v2.py:640-649",
        "chiave": ["idx"],
        "record_al_15set": 100,
        "motivo": "--da e' un selettore di popolazione per appaiare i due rami "
                  "(selftest righe 572-577), NON una ripresa.",
    },
    "fasi_mock_pr_v1_SGC.jsonl": {
        "modo": "nessuna_ripresa_id",
        "runner": "src/paper2_fasi_v2.py:640-649",
        "chiave": ["idx"],
        "record_al_15set": 100,
        "motivo": "come NGC.",
    },

    # --- nessuna ripresa e nessun identificatore --------------------------
    "ensemble_v2_NGC.jsonl": {
        "modo": "nessuna_ripresa_senza_id",
        "runner": "src/paper2_runner_4_2a.py:589-602, 775",
        "record_al_15set": 2000,
        "motivo": "nessun done; i rifiuti coprono il nome smoke e --da/--n, non "
                  "un --out gia' popolato. Nessuna tupla identificante nel record: "
                  "una seconda corsa appende 2000 record indistinguibili.",
    },
    "ensemble_v2_SGC.jsonl": {
        "modo": "nessuna_ripresa_senza_id",
        "runner": "src/paper2_runner_4_2a.py:589-602, 775",
        "record_al_15set": 2000,
        "motivo": "come NGC.",
    },

    # --- non applicabile: una passata, pochi record -----------------------
    "compD_NGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_compD_partialcorr.py",
                        "record_al_15set": 4, "motivo": "una corsa; config_hash unica chiave, irrilevante senza ripresa."},
    "compD_SGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_compD_partialcorr.py",
                        "record_al_15set": 4, "motivo": "come NGC."},
    "compD_NGC_dt2.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_compD_partialcorr.py",
                            "record_al_15set": 1, "motivo": "un record."},
    "compD_SGC_dt2.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_compD_partialcorr.py",
                            "record_al_15set": 1, "motivo": "un record."},
    "compD_nonlinear_NGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_compD_nonlinear.py",
                                  "record_al_15set": 2, "motivo": "due record; e' il registro dove Q5 era dichiarata."},
    "fase2.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_runner_fase2.py",
                    "record_al_15set": 14, "motivo": "una passata; porta i due record d2 dell'ancora operativa."},
    "fase3.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_runner_fase3_mock.py (lato dati)",
                    "record_al_15set": 44, "motivo": "ladder lato dati per punto e regione, una passata breve."},
    "fase3_surrogato_fisso.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_surrogato_fit.py",
                                    "record_al_15set": 16, "motivo": "una passata su maschera fissa."},
    "preflight_NGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_phase3_preflight.py",
                            "record_al_15set": 10, "motivo": "pre-flight geometrico, dieci punti, una corsa."},
    "preflight_SGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_phase3_preflight.py",
                            "record_al_15set": 10, "motivo": "come NGC."},
    "q5_margine.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_q5.py",
                         "record_al_15set": 2, "motivo": "due regioni, una corsa; record 65."},
    "ripattern_geom.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_ripattern_geom.py",
                             "record_al_15set": 11, "motivo": "diagnostica geometrica, una corsa."},
    "surrogato_aff.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_surrogato_fit.py",
                            "record_al_15set": 4, "motivo": "fit del surrogato, una corsa."},
    "ensemble_v2_NGC_sommario.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_runner_4_2a.py:796",
                                       "record_al_15set": 1, "motivo": "sommario, un record per corsa."},
    "ensemble_v2_SGC_sommario.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_runner_4_2a.py:796",
                                       "record_al_15set": 1, "motivo": "sommario, un record per corsa."},
    "onepoint_v1_NGC_sommario.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_passata_1punto.py",
                                       "record_al_15set": 1, "motivo": "sommario, un record per corsa."},
    "onepoint_v1_SGC_sommario.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_passata_1punto.py",
                                       "record_al_15set": 1, "motivo": "sommario, un record per corsa."},
    "onepoint_v1_DESI_NGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_passata_1punto.py (sub desi)",
                                   "record_al_15set": 1, "motivo": "la riga DESI, un record."},
    "onepoint_v1_DESI_SGC.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_passata_1punto.py (sub desi)",
                                   "record_al_15set": 1, "motivo": "la riga DESI, un record."},
    # registri di figura (1.6): nessun `record_al_15set`, perche' ogni rilancio
    # appende per disegno e un conteggio dichiarato darebbe DA_RIVEDERE a ogni run.
    "fig_F1.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_fig_F1.py (cmd_run)",
                     "motivo": "una corsa per figura, un record per corsa; si rilancia, non si riprende."},
    "fig_F7.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_fig_F7.py (cmd_run)",
                     "motivo": "una corsa per figura, un record per corsa; si rilancia, non si riprende."},

    # --- non applicabile: scansione o riscrittura -------------------------
    "cachedelta_manifest_NGC.jsonl": {"modo": "na_scansione", "runner": "src/paper2_deposit.py",
                                      "record_al_15set": 2000,
                                      "motivo": "scansione della cache delta: si rifa', non si riprende."},
    "cachedelta_manifest_SGC.jsonl": {"modo": "na_scansione", "runner": "src/paper2_deposit.py",
                                      "record_al_15set": 2000, "motivo": "come NGC."},
    "ensemble_v1_manifest_diagrams.jsonl": {"modo": "na_scansione", "runner": "src/paper2_freeze_v1.py",
                                            "record_al_15set": 16221, "motivo": "tier del congelamento: scansione dell'albero."},
    "ensemble_v1_manifest_features.jsonl": {"modo": "na_scansione", "runner": "src/paper2_freeze_v1.py",
                                            "record_al_15set": 12189, "motivo": "tier del congelamento."},
    "ensemble_v1_manifest_fields.jsonl": {"modo": "na_scansione", "runner": "src/paper2_freeze_v1.py",
                                          "record_al_15set": 2202, "motivo": "tier del congelamento."},
    "ensemble_v1_manifest_records.jsonl": {"modo": "na_scansione", "runner": "src/paper2_freeze_v1.py",
                                           "record_al_15set": 224,
                                           "motivo": "tier del congelamento; 224 rel su 218 sha256 — otto file "
                                                     "in due gruppi condividono un digest, sono manifest di ripresa "
                                                     "a 2000 voci tutte 'done'. L'aggregate resta ben definito "
                                                     "perche' include rel, che e' unico. Unico tier emendato."},
    "ensemble_v1_manifest_superseded.jsonl": {"modo": "na_scansione", "runner": "src/paper2_freeze_v1.py",
                                              "record_al_15set": 4000, "motivo": "tier del congelamento."},
    "coppie_fase5_SGC.jsonl": {"modo": "na_scansione", "runner": "src/paper2_fase5_a_coppie.py:194-200",
                               "record_al_15set": 151,
                               "motivo": "riscrittura del solo campo `tipo` su temporaneo piu' os.replace: "
                                         "una trasformazione, non un run."},

    # --- cancelli: una corsa, un verdetto ---------------------------------
    "gate21.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_gate21.py",
                     "record_al_15set": 5, "motivo": "cancello 2.1-M, una corsa per verdetto."},
    "gate25.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_gate25.py",
                     "record_al_15set": 2, "motivo": "cancello 2.5, una corsa per regione."},
    "gate53.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_gate53.py",
                     "record_al_15set": 3,
                     "motivo": "tre record per due regioni: NGC 12:48 e 12:50 del 31 ago, "
                               "il secondo con sd_draw_published al posto di sd_draw_assumed; "
                               "SGC 14 set. Il superamento del primo NON e' marcato nel record "
                               "(manca la convenzione supersedes.utc dei compD): voce per il 6.2."},
    "gate53_margini.jsonl": {"modo": "na_una_passata", "runner": "src/paper2_gate53_margini.py",
                             "record_al_15set": 1, "motivo": "un record, SGC."},

    # --- per_mock: ripresa che verifica anche il prodotto laterale ---------
    # paper1_remap.py:512-516 riprende SOLO se esistono sia la riga sia il file
    # delle curve. E' l'unico runner del progetto che controlla l'artefatto e
    # non solo il registro. `done` e' un dizionario per `key`, quindi la mappa
    # di ripresa e' LAST-WINS; la lettura scientifica di erosion_restrict deve
    # invece fare l'UNIONE, perche' le passate portano sottoinsiemi diversi di
    # cells.* — due regole opposte sullo stesso file, da dichiarare nel 6.2.
    "per_mock_NGC_R5.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                              "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 2000,
                              "motivo": "ensemble canonico; key = fp.stem, ripresa con controllo del file curve."},
    "per_mock_SGC_R5.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                              "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 2000,
                              "motivo": "ensemble canonico, emisfero sud."},
    "per_mock_NGC_R10.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                               "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 2000,
                               "motivo": "ladder di lisciamento R10."},
    "per_mock_NGC_R12.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                               "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 2000,
                               "motivo": "ladder di lisciamento R12."},
    "per_mock_NGC_R15.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                               "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 2000,
                               "motivo": "ladder di lisciamento R15."},
    "per_mock_NGC_R17.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                               "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 2000,
                               "motivo": "ladder di lisciamento R17."},
    "per_mock_NGC_R20.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                               "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 2000,
                               "motivo": "ladder di lisciamento R20."},
    "per_mock_NGC_R30.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                               "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 2000,
                               "motivo": "ladder di lisciamento R30."},
    "per_mock_NGC_R5_nullmm.jsonl": {"modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
                                     "chiave": ["key"], "duplicati_attesi": 0, "record_al_15set": 200,
                                     "motivo": "ramo nullo mock-mock, 200 coppie."},
    "per_mock_NGC_erosion_restrict.jsonl": {
        "modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
        "chiave": ["key"], "duplicati_attesi": 400, "record_al_15set": 600,
        "motivo": "TRE passate su 200 unita': 400 duplicati ATTESI, non un difetto. "
                  "Ogni passata porta un sottoinsieme diverso di cells.*, quindi la "
                  "lettura scientifica va fatta per unione."},
    "per_mock_SGC_erosion_restrict.jsonl": {
        "modo": "ripresa_dal_registro", "runner": "src/paper1_remap.py:512-516",
        "chiave": ["key"], "duplicati_attesi": 200, "record_al_15set": 400,
        "motivo": "DUE passate su 200 unita': 200 duplicati attesi. Come NGC, "
                  "lettura per unione."},
}


# I 48 registri in scopo osservati il 15 settembre 2026. Il selftest verifica
# che ognuno risolva a una dichiarazione di ripresa: se ne compare uno nuovo il
# censimento lo segnala come non_dichiarato, e se ne sparisce una dichiarazione
# il selftest fallisce prima che il censimento giri.
REGISTRI_IN_SCOPO_15SET = (
    "n10_phases_NGC.jsonl",
    "per_mock_NGC_erosion_restrict.jsonl", "per_mock_SGC_erosion_restrict.jsonl",
    "per_mock_NGC_R5.jsonl", "per_mock_SGC_R5.jsonl", "per_mock_NGC_R5_nullmm.jsonl",
    "per_mock_NGC_R10.jsonl", "per_mock_NGC_R12.jsonl", "per_mock_NGC_R15.jsonl",
    "per_mock_NGC_R17.jsonl", "per_mock_NGC_R20.jsonl", "per_mock_NGC_R30.jsonl",
    "cachedelta_manifest_NGC.jsonl", "cachedelta_manifest_SGC.jsonl",
    "ensemble_v1_manifest_diagrams.jsonl", "ensemble_v1_manifest_features.jsonl",
    "ensemble_v1_manifest_fields.jsonl", "ensemble_v1_manifest_records.jsonl",
    "ensemble_v1_manifest_superseded.jsonl",
    "compD_NGC.jsonl", "compD_SGC.jsonl", "compD_NGC_dt2.jsonl",
    "compD_SGC_dt2.jsonl", "compD_nonlinear_NGC.jsonl",
    "coppie_fase5_SGC.jsonl",
    "ensemble_v2_NGC.jsonl", "ensemble_v2_SGC.jsonl",
    "ensemble_v2_NGC_sommario.jsonl", "ensemble_v2_SGC_sommario.jsonl",
    "fase2.jsonl", "fase3.jsonl", "fase3_mock.jsonl",
    "fase3_mock_off_hi.jsonl", "fase3_mock_off_lo.jsonl",
    "fase3_mock_ripattern.jsonl", "fase3_surrogato_fisso.jsonl",
    "fasi_mock_pr_v1_NGC.jsonl", "fasi_mock_pr_v1_SGC.jsonl",
    "gate21.jsonl", "gate25.jsonl", "gate53.jsonl", "gate53_margini.jsonl",
    "onepoint_v1_DESI_NGC.jsonl", "onepoint_v1_DESI_SGC.jsonl",
    "onepoint_v1_NGC.jsonl", "onepoint_v1_SGC.jsonl",
    "onepoint_v1_NGC_sommario.jsonl", "onepoint_v1_SGC_sommario.jsonl",
    "preflight_NGC.jsonl", "preflight_SGC.jsonl",
    "q5_margine.jsonl", "ripattern_geom.jsonl", "surrogato_aff.jsonl",
)


def _canonico_ripresa(valore):
    if isinstance(valore, str):
        return "s:" + valore
    return "j:" + json.dumps(valore, sort_keys=True, ensure_ascii=False)


def _valore_chiave(rec, campo, booleani):
    """Valuta una componente della chiave dichiarata.

    `nome:chiavi` = le chiavi ordinate di un campo dizionario (e' la forma
    `tuple(sorted(r.get("points", {})))` del runner di Fase 3).
    Un campo assente vale None: e' cio' che fa `.get()` nel runner, e la
    chiave e' quindi TOLLERANTE all'assenza per costruzione.
    """
    if campo.endswith(":chiavi"):
        base = campo[: -len(":chiavi")]
        v = rec.get(base)
        return "k:" + (",".join(sorted(v)) if isinstance(v, dict) else "__assente__")
    v = rec.get(campo)
    if campo in booleani:
        v = bool(v)
    return _canonico_ripresa(v)


def _dichiarazione_ripresa(nome_base):
    if nome_base in RIPRESA_DICHIARATA:
        return RIPRESA_DICHIARATA[nome_base]
    for glob, d in RIPRESA_DICHIARATA.items():
        if "*" in glob and fnmatch.fnmatch(nome_base, glob):
            return d
    return None


def valuta_ripresa(nome_base, record_letti):
    """La proprieta' `resumable`, valutata contro la DICHIARAZIONE del runner."""
    d = _dichiarazione_ripresa(nome_base)
    if d is None:
        return {"applicabile": False, "metodo": "non_dichiarato", "esito": "NON_DICHIARATO",
                "difetti": [], "nota": "nessuna dichiarazione: fuori scopo o da aggiungere"}

    modo = d["modo"]
    base = {"applicabile": modo in ("ripresa_dal_registro", "nessuna_ripresa_id"),
            "metodo": "dichiarato_dal_runner_verificato_sul_registro",
            "modo": modo, "runner": d.get("runner"), "motivo": d.get("motivo"),
            "difetti": []}

    n = len(record_letti)
    atteso = d.get("record_al_15set")
    if atteso is not None and atteso != n:
        base["record_cambiati"] = {"alla_dichiarazione": atteso, "ora": n}
        base["difetti"].append("DA_RIVEDERE:record %d -> %d" % (atteso, n))

    if modo == "da_leggere":
        base["esito"] = "DA_LEGGERE"
        base["difetti"].append("runner_non_letto")
        return base

    if modo in ("na_una_passata", "na_scansione"):
        base["esito"] = "NA" if not base["difetti"] else "FAIL"
        return base

    if modo == "nessuna_ripresa_senza_id":
        # Niente da verificare sul registro: e' proprio l'assenza di un
        # identificatore il contenuto della dichiarazione. L'esito e'
        # DICHIARATO, non NA e non PASS: il rischio esiste ed e' registrato.
        base["esito"] = "DICHIARATO" if not base["difetti"] else "FAIL"
        return base

    # --- i due modi verificabili -------------------------------------------
    chiave = d["chiave"]
    booleani = d.get("booleani", [])
    esclusi = d.get("esclusi_se")
    considerati = [r for r in record_letti if not (esclusi and r.get(esclusi))]
    visti = {}
    for r in considerati:
        tupla = tuple(_valore_chiave(r, c, booleani) for c in chiave)
        visti[tupla] = visti.get(tupla, 0) + 1
    duplicati = sum(v - 1 for v in visti.values() if v > 1)

    base["chiave"] = chiave
    base["record_considerati"] = len(considerati)
    base["record_esclusi"] = n - len(considerati)
    base["duplicati"] = duplicati

    attesi = d.get("duplicati_attesi", 0)
    base["duplicati_attesi"] = attesi
    if duplicati != attesi:
        base["difetti"].append("duplicati %d, attesi %d" % (duplicati, attesi))

    base["esito"] = "PASS" if not base["difetti"] else "FAIL"
    return base


# ===========================================================================
# misura di un registro
# ===========================================================================

def misura_bytes(dati: bytes) -> dict:
    """Misura strutturale su byte grezzi. Nessuna decodifica implicita."""
    ris = {
        "n_byte": len(dati),
        "sha256": sha256_bytes(dati),
        "byte_nul": dati.count(b"\x00"),
        "vuoto": len(dati) == 0,
    }

    if not dati:
        ris.update({
            "n_righe": 0, "coda_terminata": True, "coda_parziale_byte": 0,
            "terminatore_ereditato": None, "terminatori_crlf": 0,
            "terminatori_lf": 0, "deviazioni_terminatore": 0,
            "wrapper_array": False,
        })
        return ris

    # Il primo carattere non-spazio dice se il file e' un array JSON intero
    # invece che una riga per record: sarebbe la negazione strutturale
    # dell'append-only.
    primo = dati.lstrip()[:1]
    ris["wrapper_array"] = primo == b"["

    parti = dati.split(b"\n")
    corpi = parti[:-1]                       # ciascuno aveva un terminatore
    coda = None if dati.endswith(b"\n") else parti[-1]

    ris["coda_terminata"] = dati.endswith(b"\n")
    ris["coda_parziale_byte"] = 0 if coda is None else len(coda)

    n_crlf = sum(1 for c in corpi if c.endswith(b"\r"))
    ris["terminatori_crlf"] = n_crlf
    ris["terminatori_lf"] = len(corpi) - n_crlf

    if corpi:
        ereditato = "crlf" if corpi[0].endswith(b"\r") else "lf"
    else:
        ereditato = None
    ris["terminatore_ereditato"] = ereditato

    # Deviazioni contro il terminatore EREDITATO, non contro un assoluto.
    # E' il difetto di paper2_append_amend64.py, corretto da amend65 in poi.
    if ereditato == "crlf":
        ris["deviazioni_terminatore"] = len(corpi) - n_crlf
    elif ereditato == "lf":
        ris["deviazioni_terminatore"] = n_crlf
    else:
        ris["deviazioni_terminatore"] = 0

    # Righe = corpi terminati + eventuale coda parziale (contata, non ignorata)
    ris["n_righe"] = len(corpi) + (0 if coda is None else 1)
    return ris


def _porta_verdetto(oggetto, profondita: int = 0) -> bool:
    """Un verdetto a qualunque livello, fino a PROFONDITA_VERDETTO.

    DIFETTO CORRETTO il 18 set 2026 (voce 6.2-vi, versione 1.5): il segnale
    guardava solo le chiavi di primo livello e non conosceva `pass`.
    gate53.jsonl porta `pass` booleano, gate53_margini.jsonl porta `esito`
    dentro `margine_*`: il censimento del 15 set li dava entrambi «gate senza
    verdetto», frazione 0.0. Il nome del campo si confronta per UGUAGLIANZA,
    mai per sottostringa: `mask_pass` e `F_ap_passed` non sono verdetti, e
    `bypass_signal` nemmeno.
    """
    if profondita > PROFONDITA_VERDETTO:
        return False
    if isinstance(oggetto, dict):
        for nome, valore in oggetto.items():
            if str(nome).lower() in CAMPI_VERDETTO:
                return True
            if isinstance(valore, str) and valore.upper() in VALORI_VERDETTO:
                return True
            if isinstance(valore, (dict, list)) and _porta_verdetto(valore, profondita + 1):
                return True
    elif isinstance(oggetto, list):
        for valore in oggetto[:MAX_ELEMENTI_VERDETTO]:
            if isinstance(valore, (dict, list)) and _porta_verdetto(valore, profondita + 1):
                return True
    return False


def misura_record(dati: bytes, max_forme: int = 12) -> dict:
    """Decodifica e parsing riga per riga. Ogni fallimento porta il numero di riga."""
    ris = {
        "righe_json_valide": 0,
        "righe_non_parsabili": [],
        "righe_non_utf8": [],
        "righe_non_oggetto": [],
        "forme_schema": [],
        "n_forme_schema": 0,
        "chiavi_ripresa_trovate": [],
        "chiavi_ripresa_non_stringa": [],
        "chiavi_ripresa_duplicate": {},
        "solo_config_hash": False,
        "segnale_verdetto": 0,
        "segnale_indice": 0,
        "segnale_manifest": 0,
        "n_record": 0,
    }

    parti = dati.split(b"\n")
    corpi = parti[:-1]
    coda = None if dati.endswith(b"\n") else parti[-1]
    grezze = list(corpi) + ([coda] if coda is not None else [])

    forme: dict[frozenset, int] = {}
    valori_chiave: dict[str, dict[str, int]] = {}
    oggetti: list = []

    for i, grezza in enumerate(grezze, start=1):
        linea = grezza[:-1] if grezza.endswith(b"\r") else grezza
        if not linea.strip():
            continue
        try:
            testo = linea.decode("utf-8")
        except UnicodeDecodeError:
            ris["righe_non_utf8"].append(i)
            continue
        try:
            record = json.loads(testo)
        except (json.JSONDecodeError, ValueError):
            ris["righe_non_parsabili"].append(i)
            continue
        ris["righe_json_valide"] += 1
        if not isinstance(record, dict):
            ris["righe_non_oggetto"].append(i)
            continue
        ris["n_record"] += 1
        oggetti.append(record)

        chiavi = frozenset(record.keys())
        forme[chiavi] = forme.get(chiavi, 0) + 1

        # segnali di classe, misurati sul contenuto
        ha_digest = any(e_esadecimale_64(v) for v in record.values())
        ha_percorso = any(sembra_percorso(v) for v in record.values())
        if ha_digest and ha_percorso:
            ris["segnale_manifest"] += 1
        if _porta_verdetto(record):
            ris["segnale_verdetto"] += 1
        for nome in record.keys():
            if nome.lower() in CAMPI_INDICE:
                ris["segnale_indice"] += 1
                break

        # chiavi di ripresa
        for nome, valore in record.items():
            minuscolo = nome.lower()
            candidata = (
                minuscolo in CHIAVI_RIPRESA
                or "key" in minuscolo
                or "chiave" in minuscolo
                or minuscolo in CHIAVI_NON_SUFFICIENTI
            )
            if not candidata:
                continue
            if nome not in valori_chiave:
                valori_chiave[nome] = {}
            if not isinstance(valore, str):
                if [nome, i] not in ris["chiavi_ripresa_non_stringa"]:
                    ris["chiavi_ripresa_non_stringa"].append([nome, i])
                chiave_testo = json.dumps(valore, sort_keys=True)
            else:
                chiave_testo = valore
            valori_chiave[nome][chiave_testo] = valori_chiave[nome].get(chiave_testo, 0) + 1

    ordinate = sorted(forme.items(), key=lambda kv: (-kv[1], sorted(kv[0])))
    ris["n_forme_schema"] = len(ordinate)
    ris["forme_schema"] = [
        {"campi": sorted(chiavi), "n": n} for chiavi, n in ordinate[:max_forme]
    ]

    ris["chiavi_ripresa_trovate"] = sorted(valori_chiave.keys())
    for nome, conteggi in sorted(valori_chiave.items()):
        duplicati = sum(n - 1 for n in conteggi.values() if n > 1)
        if duplicati:
            ris["chiavi_ripresa_duplicate"][nome] = duplicati

    utili = [c for c in ris["chiavi_ripresa_trovate"] if c.lower() not in CHIAVI_NON_SUFFICIENTI]
    ris["solo_config_hash"] = bool(ris["chiavi_ripresa_trovate"]) and not utili
    ris["_oggetti"] = oggetti
    return ris


# Un manifest vero ha pochi campi: percorso, digest, byte, orario. Un registro
# di run che porta la provenienza per record (delta_sha256 + delta_file) ne ha
# decine, e chiamarlo manifest e' l'errore che produceva cinque discordanze su
# dieci. La soglia e' sulla forma piu' frequente, non sulla media.
MAX_CAMPI_MANIFEST = 8


def classe_misurata(misura: dict) -> str:
    """Classe dedotta dal CONTENUTO. Incrociata con quella dichiarata.

    `gate` NON e' una classe misurata: «porta un verdetto» e' un SEGNALE, e un
    sommario ne porta uno per definizione. Il segnale resta, ed e' usato per un
    controllo mirato — un file dichiarato gate che non contiene verdetti — che
    e' il difetto vero.
    """
    n = misura["n_record"]
    if n == 0:
        return "indeterminato"
    forme = misura.get("forme_schema") or []
    campi_forma_frequente = len(forme[0]["campi"]) if forme else 0
    if (misura["segnale_manifest"] / n >= 0.90
            and 0 < campi_forma_frequente <= MAX_CAMPI_MANIFEST):
        return "manifest"
    if misura["segnale_indice"] / n >= 0.50:
        return "run"
    return "indeterminato"


def classe_dichiarata(nome_base: str):
    for glob, classe, in_scopo, motivo in CLASSI_DICHIARATE:
        if fnmatch.fnmatch(nome_base, glob):
            return classe, in_scopo, motivo
    return None, None, None


def valuta_proprieta(classe: str, strutturale: dict, record: dict) -> dict:
    """Le quattro proprieta', ciascuna con il suo esito e il suo metodo."""
    applicabile = APPLICABILITA.get(classe, APPLICABILITA["run"])
    esiti = {}

    # --- append-only, parte strutturale ------------------------------------
    difetti = []
    if strutturale["wrapper_array"]:
        difetti.append("wrapper_array")
    if record["righe_non_oggetto"]:
        difetti.append("righe_non_oggetto")
    esiti["append_strutturale"] = {
        "applicabile": applicabile["append_strutturale"],
        "metodo": "misurato_sul_registro",
        "esito": "PASS" if not difetti else "FAIL",
        "difetti": difetti,
    }

    # --- append-only, parte storica ----------------------------------------
    esiti["append_storico"] = {
        "applicabile": True,
        "metodo": "misurato_contro_baseline",
        "esito": "NON_VERIFICABILE",
        "difetti": [],
        "nota": "richiede una linea di base precedente; questa passata la stabilisce",
    }

    # --- atomico, residuo ---------------------------------------------------
    difetti = []
    if not strutturale["coda_terminata"]:
        difetti.append("coda_non_terminata:%d_byte" % strutturale["coda_parziale_byte"])
    if record["righe_non_parsabili"]:
        difetti.append("righe_non_parsabili:%s" % record["righe_non_parsabili"][:10])
    esiti["atomico_residuo"] = {
        "applicabile": applicabile["atomico_residuo"],
        "metodo": "residuo_misurato_sul_registro",
        "esito": "PASS" if not difetti else "FAIL",
        "difetti": difetti,
        "limite": "il residuo assente non prova la scrittura atomica: vedi sottocomando scrittori",
    }

    # --- crash-safe, residuo ------------------------------------------------
    difetti = []
    if strutturale["byte_nul"]:
        difetti.append("byte_nul:%d" % strutturale["byte_nul"])
    if record["righe_non_utf8"]:
        difetti.append("righe_non_utf8:%s" % record["righe_non_utf8"][:10])
    if strutturale["deviazioni_terminatore"]:
        difetti.append("deviazioni_terminatore:%d_su_%s"
                       % (strutturale["deviazioni_terminatore"],
                          strutturale["terminatore_ereditato"]))
    esiti["crashsafe_residuo"] = {
        "applicabile": applicabile["crashsafe_residuo"],
        "metodo": "residuo_misurato_sul_registro",
        "esito": "PASS" if not difetti else "FAIL",
        "difetti": difetti,
        "limite": "terminatore confrontato con quello EREDITATO dal file, non con un assoluto",
    }

    # --- resumable ----------------------------------------------------------
    if not applicabile["resumable"]:
        esiti["resumable"] = {
            "applicabile": False,
            "metodo": "non_applicabile",
            "esito": "NA",
            "difetti": [],
            "nota": "un registro di questa classe non riprende",
        }
    else:
        difetti = []
        if not record["chiavi_ripresa_trovate"]:
            difetti.append("nessuna_chiave_di_ripresa")
        if record["chiavi_ripresa_non_stringa"]:
            difetti.append("chiave_non_stringa:%s" % record["chiavi_ripresa_non_stringa"][:5])
        if record["solo_config_hash"]:
            difetti.append("solo_config_hash")
        esiti["resumable"] = {
            "applicabile": True,
            "metodo": "misurato_sul_registro",
            "esito": "PASS" if not difetti else "FAIL",
            "difetti": difetti,
            "duplicati_chiave": record["chiavi_ripresa_duplicate"],
            "nota": "i duplicati sono informativi: la convenzione e' lettura per UNIONE",
        }

    return esiti


def censisci_file(percorso: Path, radice: Path) -> dict:
    dati = percorso.read_bytes()
    strutturale = misura_bytes(dati)
    record = misura_record(dati)
    nome_base = percorso.name

    dichiarata, in_scopo, motivo = classe_dichiarata(nome_base)
    misurata = classe_misurata(record)

    # Un file DICHIARATO gate non si confronta con la classe misurata: `gate`
    # non e' una classe misurata (vedi classe_misurata), e il confronto dava
    # DISCORDANZA per costruzione a ogni cancello che porta un indice —
    # gate25.jsonl, lasciato cosi' dal record 68: un FAIL permanente per
    # disegno. Per un gate il controllo e' la presenza del verdetto, e dalla
    # 1.5 pesa sull'uscita (18 set 2026, voce 6.2-vi).
    gate_senza_verdetto = (
        dichiarata == "gate" and record["n_record"] > 0
        and record["segnale_verdetto"] / record["n_record"] < 0.50
    )
    if dichiarata is None:
        stato_classe = "NON_CLASSIFICATO"
        classe = misurata
    elif dichiarata == "gate":
        stato_classe = "GATE_SENZA_VERDETTO" if gate_senza_verdetto else "GATE_CON_VERDETTO"
        classe = dichiarata
    elif misurata == "indeterminato":
        stato_classe = "DICHIARATA_SOLA"
        classe = dichiarata
    elif misurata == dichiarata:
        stato_classe = "CONCORDE"
        classe = dichiarata
    else:
        stato_classe = "DISCORDANZA"
        classe = dichiarata

    esiti = valuta_proprieta(classe, strutturale, record)
    esiti["resumable"] = valuta_ripresa(nome_base, record.pop("_oggetti", []))

    # (gate_senza_verdetto e' calcolato sopra, prima dello stato di classe.)

    falliti = [k for k, v in esiti.items() if v["esito"] == "FAIL"]

    return {
        "schema": SCHEMA,
        "tipo": "registro",
        "percorso": rel_posix(percorso, radice),
        "nome": nome_base,
        "classe_dichiarata": dichiarata,
        "classe_misurata": misurata,
        "stato_classe": stato_classe,
        "in_scopo_6_1": bool(in_scopo),
        "motivo_classe": motivo,
        "strutturale": strutturale,
        "record": record,
        "proprieta": esiti,
        "proprieta_fallite": falliti,
        "gate_senza_verdetto": gate_senza_verdetto,
        "frazione_record_con_verdetto": (
            record["segnale_verdetto"] / record["n_record"] if record["n_record"] else 0.0),
    }


# ===========================================================================
# baseline: la sola forma in cui append-only e' dimostrabile
# ===========================================================================

def carica_baseline(percorso: Path) -> dict:
    """Legge una passata precedente e ne estrae lunghezza e digest per file."""
    base = {}
    with percorso.open("rb") as fh:
        for grezza in fh:
            linea = grezza.rstrip(b"\r\n")
            if not linea.strip():
                continue
            try:
                record = json.loads(linea.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                continue
            if record.get("tipo") != "registro":
                continue
            base[record["percorso"]] = {
                "n_byte": record["strutturale"]["n_byte"],
                "sha256": record["strutturale"]["sha256"],
            }
    return base


def verifica_prefisso(percorso: Path, n_byte_prec: int, sha_prec: str) -> dict:
    """Append-only => il prefisso e' conservato. E' l'unica prova possibile."""
    dimensione = percorso.stat().st_size
    if dimensione < n_byte_prec:
        return {"esito": "FAIL", "difetto": "file_accorciato",
                "n_byte_prec": n_byte_prec, "n_byte_ora": dimensione}
    with percorso.open("rb") as fh:
        prefisso = fh.read(n_byte_prec)
    sha_ora = sha256_bytes(prefisso)
    if sha_ora != sha_prec:
        return {"esito": "FAIL", "difetto": "prefisso_modificato",
                "sha_prec": sha_prec, "sha_ora": sha_ora,
                "n_byte_prec": n_byte_prec, "n_byte_ora": dimensione}
    return {"esito": "PASS", "difetto": None,
            "n_byte_prec": n_byte_prec, "n_byte_ora": dimensione,
            "byte_appesi": dimensione - n_byte_prec}


# ===========================================================================
# sottocomando: censimento
# ===========================================================================

def trova_registri(radici: list[Path]) -> list[Path]:
    trovati = []
    for radice in radici:
        if not radice.exists():
            raise SystemExit("RIFIUTO: radice inesistente -> %s" % radice)
        for percorso in sorted(radice.rglob("*.jsonl")):
            if percorso.is_file():
                trovati.append(percorso)
    return trovati


def comando_censimento(args) -> int:
    base_repo = Path(args.base).resolve()
    radici = [Path(r) if Path(r).is_absolute() else base_repo / r for r in args.roots]
    percorsi = trova_registri(radici)

    baseline = {}
    if args.baseline:
        percorso_baseline = Path(args.baseline)
        if not percorso_baseline.exists():
            raise SystemExit("RIFIUTO: baseline inesistente -> %s" % percorso_baseline)
        baseline = carica_baseline(percorso_baseline)
        if not baseline:
            raise SystemExit("RIFIUTO: la baseline non contiene record di tipo 'registro'")

    record_uscita = []
    n_righe_totali = 0
    non_classificati = []
    discordanze = []
    gate_muti = []
    falliti = []
    baseline_falliti = []
    baseline_coperti = 0

    for percorso in percorsi:
        record = censisci_file(percorso, base_repo)
        n_righe_totali += record["strutturale"]["n_righe"]

        if record["stato_classe"] == "NON_CLASSIFICATO":
            non_classificati.append(record["percorso"])
        if record["stato_classe"] == "DISCORDANZA":
            discordanze.append(record["percorso"])
        if record["stato_classe"] == "GATE_SENZA_VERDETTO":
            gate_muti.append(record["percorso"])

        chiave = record["percorso"]
        if chiave in baseline:
            esito = verifica_prefisso(percorso, baseline[chiave]["n_byte"],
                                      baseline[chiave]["sha256"])
            record["proprieta"]["append_storico"] = {
                "applicabile": True,
                "metodo": "misurato_contro_baseline",
                "esito": esito["esito"],
                "difetti": [] if esito["difetto"] is None else [esito["difetto"]],
                "dettaglio": esito,
            }
            baseline_coperti += 1
            if esito["esito"] == "FAIL":
                baseline_falliti.append(chiave)

        record["proprieta_fallite"] = [
            k for k, v in record["proprieta"].items() if v["esito"] == "FAIL"
        ]
        if record["in_scopo_6_1"] and record["proprieta_fallite"]:
            falliti.append((record["percorso"], record["proprieta_fallite"]))

        record["utc"] = ora_utc()
        record_uscita.append(record)

    in_scopo = [r for r in record_uscita if r["in_scopo_6_1"]]

    sommario = {
        "schema": SCHEMA,
        "tipo": "sommario",
        "versione_strumento": VERSIONE,
        "utc": ora_utc(),
        "radici": [rel_posix(r, base_repo) for r in radici],
        "n_file": len(record_uscita),
        "n_righe": n_righe_totali,
        "n_file_in_scopo": len(in_scopo),
        "n_righe_in_scopo": sum(r["strutturale"]["n_righe"] for r in in_scopo),
        "non_classificati": non_classificati,
        "discordanze_classe": discordanze,
        "gate_senza_verdetto": gate_muti,
        "in_scopo_con_difetti": [p for p, _ in falliti],
        "baseline": {
            "usata": bool(baseline),
            "file_coperti": baseline_coperti,
            "file_non_coperti": len(record_uscita) - baseline_coperti,
            "falliti": baseline_falliti,
        },
        "cancello_riproduzione": {
            "attesi_file": args.attesi_file,
            "attese_righe": args.attese_righe,
            "esito": None,
        },
    }

    # --- cancello di riproduzione ------------------------------------------
    problemi_cancello = []
    if args.attesi_file is not None and args.attesi_file != len(record_uscita):
        problemi_cancello.append("file attesi %d, trovati %d"
                                 % (args.attesi_file, len(record_uscita)))
    if args.attese_righe is not None and args.attese_righe != n_righe_totali:
        problemi_cancello.append("righe attese %d, trovate %d"
                                 % (args.attese_righe, n_righe_totali))
    sommario["cancello_riproduzione"]["esito"] = "PASS" if not problemi_cancello else "FAIL"
    sommario["cancello_riproduzione"]["problemi"] = problemi_cancello

    # --- scrittura ----------------------------------------------------------
    if args.out:
        uscita = Path(args.out)
        verifica_uscita(uscita)
        uscita.parent.mkdir(parents=True, exist_ok=True)
        with uscita.open("w", encoding="utf-8", newline="\n") as fh:
            for record in record_uscita:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.write(json.dumps(sommario, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    # --- stampa -------------------------------------------------------------
    print("=" * 78)
    print("CENSIMENTO DEI REGISTRI — voce 6.1")
    print("=" * 78)
    print("file .jsonl trovati : %d" % len(record_uscita))
    print("righe totali        : %d" % n_righe_totali)
    print("in scopo 6.1        : %d file, %d righe"
          % (sommario["n_file_in_scopo"], sommario["n_righe_in_scopo"]))
    print()

    larghezza = max([len(r["percorso"]) for r in record_uscita] + [20])
    intestazione = ("%-*s  %-9s  %-6s  %-6s  %-6s  %-6s  %-6s"
                    % (larghezza, "registro", "classe", "app.s", "stor.", "atom.",
                       "crash", "resum"))
    print(intestazione)
    print("-" * len(intestazione))
    breve = {"PASS": "PASS", "FAIL": "FAIL", "NA": "NA", "NON_VERIFICABILE": "n.v.",
             "DICHIARATO": "dich.", "DA_LEGGERE": "LEGG", "NON_DICHIARATO": "-"}
    for record in record_uscita:
        p = record["proprieta"]
        print("%-*s  %-9s  %-6s  %-6s  %-6s  %-6s  %-6s" % (
            larghezza, record["percorso"],
            record["classe_dichiarata"] or "?",
            breve.get(p["append_strutturale"]["esito"], "?"),
            breve.get(p["append_storico"]["esito"], "?"),
            breve.get(p["atomico_residuo"]["esito"], "?"),
            breve.get(p["crashsafe_residuo"]["esito"], "?"),
            breve.get(p["resumable"]["esito"], "?"),
        ))
    print()

    if non_classificati:
        print("NON CLASSIFICATI (%d) — estendere CLASSI_DICHIARATE con un motivo:"
              % len(non_classificati))
        for p in non_classificati:
            print("  %s" % p)
        print()
    if gate_muti:
        print("GATE SENZA VERDETTO (%d):" % len(gate_muti))
        for p in gate_muti:
            print("  %s" % p)
        print()
    if discordanze:
        print("DISCORDANZA fra classe dichiarata e classe misurata (%d):" % len(discordanze))
        for p in discordanze:
            record = next(r for r in record_uscita if r["percorso"] == p)
            print("  %s  dichiarata=%s  misurata=%s"
                  % (p, record["classe_dichiarata"], record["classe_misurata"]))
        print()
    if falliti:
        print("IN SCOPO CON DIFETTI (%d) — ciascuno va dichiarato, non riparato:" % len(falliti))
        for p, props in falliti:
            record = next(r for r in record_uscita if r["percorso"] == p)
            print("  %s" % p)
            for nome in props:
                print("      %-20s %s" % (nome, record["proprieta"][nome]["difetti"]))
        print()

    if baseline:
        print("BASELINE: %d file coperti, %d senza copertura, %d falliti"
              % (baseline_coperti, sommario["baseline"]["file_non_coperti"],
                 len(baseline_falliti)))
        for p in baseline_falliti:
            print("  FAIL  %s" % p)
    else:
        print("BASELINE: nessuna. `append_storico` resta NON_VERIFICABILE per ogni file.")
        print("          Questa passata la STABILISCE: la prossima passi --baseline su questa uscita.")
    print()

    modi = {}
    for record in record_uscita:
        m = record["proprieta"]["resumable"].get("modo", "non_dichiarato")
        modi[m] = modi.get(m, 0) + 1
    print("ripresa, per modo dichiarato:")
    for m in sorted(modi):
        print("  %-28s %d" % (m, modi[m]))
    print()

    print("cancello di riproduzione: %s" % sommario["cancello_riproduzione"]["esito"])
    for problema in problemi_cancello:
        print("  %s" % problema)

    codice = 0
    if modi.get("da_leggere"):
        codice = 1
    if non_classificati or discordanze or gate_muti or problemi_cancello or baseline_falliti:
        codice = 1
    if falliti:
        codice = max(codice, 2)
    print()
    print("uscita: %d  (0 pulito, 1 popolazione/classe/cancello, 2 difetti da dichiarare)" % codice)
    return codice


# ===========================================================================
# sottocomando: scrittori (ISPEZIONE, non misura)
# ===========================================================================

def ispeziona_sorgente(percorso: Path) -> dict:
    testo = percorso.read_text(encoding="utf-8", errors="replace")
    try:
        albero = ast.parse(testo, filename=str(percorso))
    except SyntaxError as errore:
        return {"errore_sintassi": str(errore)}

    registri = set()
    aperture_append = []
    usa_flush = False
    usa_fsync = False
    usa_replace = False
    usa_tempfile = False

    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            if nodo.value.lower().endswith(".jsonl"):
                registri.add(nodo.value.replace("\\", "/"))
        if isinstance(nodo, ast.Call):
            nome = ""
            if isinstance(nodo.func, ast.Name):
                nome = nodo.func.id
            elif isinstance(nodo.func, ast.Attribute):
                nome = nodo.func.attr
            if nome == "open":
                # DIFETTO CORRETTO (riprodotto nel selftest): in `open(path, mode)`
                # il modo e' il SECONDO argomento; in `Path.open(mode)` e'
                # il PRIMO. Leggere sempre args[1] manca ogni scrittore che
                # usa un oggetto Path — cioe' gli strumenti piu' recenti.
                builtin = isinstance(nodo.func, ast.Name)
                posizione = 1 if builtin else 0
                modo = None
                if len(nodo.args) > posizione and isinstance(nodo.args[posizione], ast.Constant):
                    modo = nodo.args[posizione].value
                for kw in nodo.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        modo = kw.value.value
                if isinstance(modo, str) and "a" in modo:
                    aperture_append.append({"riga": nodo.lineno, "modo": modo,
                                            "forma": "builtin" if builtin else "metodo"})
            if nome == "flush":
                usa_flush = True
            if nome == "fsync":
                usa_fsync = True
            if nome == "replace":
                usa_replace = True
            if nome in ("NamedTemporaryFile", "mkstemp", "TemporaryDirectory"):
                usa_tempfile = True

    return {
        "registri_citati": sorted(registri),
        "aperture_append": aperture_append,
        "usa_flush": usa_flush,
        "usa_fsync": usa_fsync,
        "usa_os_replace": usa_replace,
        "usa_tempfile": usa_tempfile,
    }


def comando_scrittori(args) -> int:
    base_repo = Path(args.base).resolve()
    radice = Path(args.src) if Path(args.src).is_absolute() else base_repo / args.src
    if not radice.exists():
        raise SystemExit("RIFIUTO: cartella sorgente inesistente -> %s" % radice)

    record_uscita = []
    for percorso in sorted(radice.rglob("*.py")):
        if not percorso.is_file():
            continue
        ispezione = ispeziona_sorgente(percorso)
        if ispezione.get("errore_sintassi"):
            record_uscita.append({
                "schema": SCHEMA, "tipo": "scrittore",
                "percorso": rel_posix(percorso, base_repo),
                "metodo": "ispezione_ast",
                "errore_sintassi": ispezione["errore_sintassi"],
            })
            continue
        if not ispezione["aperture_append"] and not ispezione["registri_citati"]:
            continue
        record_uscita.append({
            "schema": SCHEMA,
            "tipo": "scrittore",
            "percorso": rel_posix(percorso, base_repo),
            "metodo": "ispezione_ast",
            "limite": "l'AST dice cosa il codice PUO' fare, non cosa e' stato eseguito",
            **ispezione,
        })

    scriventi = [r for r in record_uscita if r.get("aperture_append")]
    senza_fsync = [r["percorso"] for r in scriventi if not r.get("usa_fsync")]

    print("=" * 78)
    print("SCRITTORI — ispezione AST, non misura")
    print("=" * 78)
    print("sorgenti che citano un .jsonl : %d" % len(record_uscita))
    print("sorgenti che aprono in append : %d" % len(scriventi))
    print()
    larghezza = max([len(r["percorso"]) for r in record_uscita] + [20]) if record_uscita else 20
    print("%-*s  %-7s  %-7s  %-7s  %-7s" % (larghezza, "sorgente", "append", "flush", "fsync", "replace"))
    print("-" * (larghezza + 36))
    for record in scriventi:
        print("%-*s  %-7d  %-7s  %-7s  %-7s" % (
            larghezza, record["percorso"], len(record["aperture_append"]),
            "si" if record["usa_flush"] else "NO",
            "si" if record["usa_fsync"] else "NO",
            "si" if record["usa_os_replace"] else "no",
        ))
    print()
    if senza_fsync:
        print("APRONO IN APPEND SENZA fsync (%d) — crash-safe non ispezionabile come presente:"
              % len(senza_fsync))
        for p in senza_fsync:
            print("  %s" % p)
    print()
    print("LIMITE DICHIARATO: questo elenco e' ispezione del codice. L'esecuzione")
    print("si verifica sui registri, non sul codice (lezione 5 della consegna 14 set).")

    if args.out:
        uscita = Path(args.out)
        verifica_uscita(uscita)
        uscita.parent.mkdir(parents=True, exist_ok=True)
        with uscita.open("w", encoding="utf-8", newline="\n") as fh:
            for record in record_uscita:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    return 0


# ===========================================================================
# selftest — ogni difetto riprodotto su fixture PRIMA di dichiararlo rilevato
# ===========================================================================

class Contatore:
    def __init__(self):
        self.ok = 0
        self.ko = []

    def verifica(self, nome, condizione):
        if condizione:
            self.ok += 1
        else:
            self.ko.append(nome)

    def uguale(self, nome, ottenuto, atteso):
        self.verifica("%s (ottenuto %r, atteso %r)" % (nome, ottenuto, atteso),
                      ottenuto == atteso)


def comando_selftest(args) -> int:
    c = Contatore()

    # ---- 1. misura_bytes su file pulito CRLF ------------------------------
    pulito = b'{"key":"a","idx":0}\r\n{"key":"b","idx":1}\r\n'
    m = misura_bytes(pulito)
    c.uguale("crlf: n_righe", m["n_righe"], 2)
    c.uguale("crlf: terminatore ereditato", m["terminatore_ereditato"], "crlf")
    c.uguale("crlf: deviazioni", m["deviazioni_terminatore"], 0)
    c.uguale("crlf: coda terminata", m["coda_terminata"], True)
    c.uguale("crlf: byte nul", m["byte_nul"], 0)
    c.uguale("crlf: wrapper array", m["wrapper_array"], False)

    # ---- 2. file pulito LF -------------------------------------------------
    pulito_lf = b'{"key":"a","idx":0}\n{"key":"b","idx":1}\n'
    m = misura_bytes(pulito_lf)
    c.uguale("lf: terminatore ereditato", m["terminatore_ereditato"], "lf")
    c.uguale("lf: deviazioni", m["deviazioni_terminatore"], 0)

    # ---- 3. DIFETTO: terminatori misti, ereditato CRLF --------------------
    # E' la forma del difetto di amend64: un controllo assoluto non lo vede.
    misto = b'{"key":"a"}\r\n{"key":"b"}\n{"key":"c"}\r\n'
    m = misura_bytes(misto)
    c.uguale("misto crlf: ereditato", m["terminatore_ereditato"], "crlf")
    c.uguale("misto crlf: deviazioni", m["deviazioni_terminatore"], 1)

    # ---- 4. DIFETTO: terminatori misti, ereditato LF ----------------------
    # Lo stesso file con l'eredita' rovesciata deve dare la stessa deviazione.
    misto_lf = b'{"key":"a"}\n{"key":"b"}\r\n{"key":"c"}\n'
    m = misura_bytes(misto_lf)
    c.uguale("misto lf: ereditato", m["terminatore_ereditato"], "lf")
    c.uguale("misto lf: deviazioni", m["deviazioni_terminatore"], 1)

    # ---- 5. DIFETTO: coda non terminata (residuo di scrittura non atomica) -
    troncato = b'{"key":"a"}\r\n{"key":"b"'
    m = misura_bytes(troncato)
    c.uguale("troncato: coda terminata", m["coda_terminata"], False)
    c.uguale("troncato: byte di coda", m["coda_parziale_byte"], 10)
    c.uguale("troncato: n_righe include la coda", m["n_righe"], 2)
    r = misura_record(troncato)
    c.uguale("troncato: riga non parsabile", r["righe_non_parsabili"], [2])
    c.uguale("troncato: record validi", r["n_record"], 1)

    # ---- 6. DIFETTO: byte NUL ---------------------------------------------
    con_nul = b'{"key":"a"}\r\n\x00\x00{"key":"b"}\r\n'
    m = misura_bytes(con_nul)
    c.uguale("nul: conteggio", m["byte_nul"], 2)

    # ---- 7. DIFETTO: wrapper d'array (negazione strutturale dell'append) --
    array = b'[\n{"key":"a"},\n{"key":"b"}\n]\n'
    m = misura_bytes(array)
    c.uguale("array: wrapper rilevato", m["wrapper_array"], True)

    # ---- 8. file vuoto -----------------------------------------------------
    m = misura_bytes(b"")
    c.uguale("vuoto: n_righe", m["n_righe"], 0)
    c.uguale("vuoto: flag", m["vuoto"], True)
    c.uguale("vuoto: nessun terminatore", m["terminatore_ereditato"], None)

    # ---- 9. righe vuote non contano come record ---------------------------
    con_vuote = b'{"key":"a"}\n\n{"key":"b"}\n'
    r = misura_record(con_vuote)
    c.uguale("righe vuote: record", r["n_record"], 2)
    c.uguale("righe vuote: non parsabili", r["righe_non_parsabili"], [])

    # ---- 10. DIFETTO: chiave di ripresa non stringa ------------------------
    non_stringa = b'{"key":1,"idx":0}\n{"key":2,"idx":1}\n'
    r = misura_record(non_stringa)
    c.verifica("chiave non stringa rilevata", len(r["chiavi_ripresa_non_stringa"]) == 2)
    c.uguale("chiave non stringa: nome", r["chiavi_ripresa_non_stringa"][0][0], "key")

    # ---- 11. duplicati di chiave: informativi, non difetto ----------------
    duplicati = b'{"key":"a","idx":0}\n{"key":"a","idx":0}\n{"key":"b","idx":1}\n'
    r = misura_record(duplicati)
    c.uguale("duplicati: conteggio", r["chiavi_ripresa_duplicate"].get("key"), 1)
    esiti = valuta_proprieta("run", misura_bytes(duplicati), r)
    c.uguale("duplicati NON fanno fallire resumable", esiti["resumable"]["esito"], "PASS")

    # ---- 12. DIFETTO: nessuna chiave di ripresa ---------------------------
    senza_chiave = b'{"valore":1.0,"idx":0}\n{"valore":2.0,"idx":1}\n'
    r = misura_record(senza_chiave)
    esiti = valuta_proprieta("run", misura_bytes(senza_chiave), r)
    c.uguale("senza chiave: resumable FAIL", esiti["resumable"]["esito"], "FAIL")
    c.verifica("senza chiave: difetto nominato",
               "nessuna_chiave_di_ripresa" in esiti["resumable"]["difetti"])

    # ---- 13. DIFETTO: la sola chiave e' config_hash -----------------------
    solo_ch = b'{"config_hash":"aa","idx":0}\n{"config_hash":"bb","idx":1}\n'
    r = misura_record(solo_ch)
    c.uguale("solo config_hash rilevato", r["solo_config_hash"], True)
    esiti = valuta_proprieta("run", misura_bytes(solo_ch), r)
    c.uguale("solo config_hash: resumable FAIL", esiti["resumable"]["esito"], "FAIL")

    # ---- 14. resumable NA per la classe gate ------------------------------
    esiti = valuta_proprieta("gate", misura_bytes(senza_chiave), misura_record(senza_chiave))
    c.uguale("gate: resumable NA", esiti["resumable"]["esito"], "NA")
    c.uguale("gate: NA non e' PASS", esiti["resumable"]["applicabile"], False)

    # ---- 15. append_storico senza baseline non e' mai PASS ----------------
    esiti = valuta_proprieta("run", misura_bytes(pulito), misura_record(pulito))
    c.uguale("storico senza baseline", esiti["append_storico"]["esito"], "NON_VERIFICABILE")
    c.verifica("storico senza baseline non e' PASS",
               esiti["append_storico"]["esito"] != "PASS")

    # ---- 16. tre forme di schema in un registro solo ----------------------
    # E' la forma reale del registro d'ensemble: ancora_catena / ancora_n6_wfkp
    # / diagnostica_n6_wfkp. Deve essere censita, non segnalata come difetto.
    tre_forme = (b'{"key":"a","idx":0,"ancora_catena":1}\n'
                 b'{"key":"b","idx":1,"ancora_n6_wfkp":2}\n'
                 b'{"key":"c","idx":2,"diagnostica_n6_wfkp":3}\n')
    r = misura_record(tre_forme)
    c.uguale("tre forme censite", r["n_forme_schema"], 3)
    esiti = valuta_proprieta("run", misura_bytes(tre_forme), r)
    c.uguale("tre forme non sono un difetto", esiti["append_strutturale"]["esito"], "PASS")

    # ---- 17. copertura parziale di un campo (forma di d5c_n_clipped) ------
    parziale = (b'{"key":"a","idx":0}\n'
                b'{"key":"b","idx":1,"d5c_n_clipped":0}\n')
    r = misura_record(parziale)
    c.uguale("copertura parziale: due forme", r["n_forme_schema"], 2)

    # ---- 18. classe misurata dal contenuto --------------------------------
    manifest = (b'{"path":"results/paper2/a.npy","sha256":"' + b"a" * 64 + b'"}\n'
                b'{"path":"results/paper2/b.npy","sha256":"' + b"b" * 64 + b'"}\n')
    c.uguale("classe manifest", classe_misurata(misura_record(manifest)), "manifest")
    # `gate` non e' piu' una classe misurata: portare un verdetto e' un segnale,
    # e un sommario ne porta uno. Il segnale resta contato.
    gate = b'{"gate":"2.5","verdetto":"PASS"}\n{"gate":"2.5","verdetto":"FAIL"}\n'
    mg = misura_record(gate)
    c.uguale("verdetto non e' una classe", classe_misurata(mg), "indeterminato")
    c.uguale("segnale verdetto contato", mg["segnale_verdetto"], 2)

    # DIFETTO RIPRODOTTO: un registro di run con provenienza per record veniva
    # chiamato manifest. Ottantina di campi piu' percorso e digest.
    campi = ", ".join('"q%d": %f' % (i, i * 1.5) for i in range(30))
    ricco = (b'{"delta_file":"cache/d0.npy","delta_sha256":"' + b"a" * 64 + b'","idx":0,'
             + campi.encode() + b'}\n'
             b'{"delta_file":"cache/d1.npy","delta_sha256":"' + b"b" * 64 + b'","idx":1,'
             + campi.encode() + b'}\n')
    mr = misura_record(ricco)
    c.uguale("provenienza per record NON e' un manifest", classe_misurata(mr), "run")
    c.verifica("il segnale manifest c'e' comunque", mr["segnale_manifest"] == 2)

    # un manifest vero: pochi campi
    magro = (b'{"rel":"results/paper2/a.npy","sha256":"' + b"a" * 64 + b'","bytes":10,"mtime_utc":"x"}\n'
             b'{"rel":"results/paper2/b.npy","sha256":"' + b"b" * 64 + b'","bytes":20,"mtime_utc":"y"}\n')
    c.uguale("manifest magro resta manifest", classe_misurata(misura_record(magro)), "manifest")
    # LIMITE DICHIARATO: il rilevatore di percorso chiede un separatore. Un
    # manifest di soli nomi di file non sarebbe riconosciuto — non capita sui
    # cinque tier, i cui `rel` sono relativi alla radice, ma va saputo.
    nudo = (b'{"rel":"a.npy","sha256":"' + b"a" * 64 + b'"}\n'
            b'{"rel":"b.npy","sha256":"' + b"b" * 64 + b'"}\n')
    c.uguale("limite: manifest di soli nomi non riconosciuto",
             classe_misurata(misura_record(nudo)), "indeterminato")
    run = b'{"idx":0,"N_H1":35436.0}\n{"idx":1,"N_H1":35440.0}\n'
    c.uguale("classe run", classe_misurata(misura_record(run)), "run")

    # ---- 19. classificazione dichiarata ------------------------------------
    cl, scopo, _ = classe_dichiarata("gate53.jsonl")
    c.uguale("dichiarata: gate53", cl, "gate")
    c.uguale("dichiarata: gate53 in scopo", scopo, True)
    cl, scopo, _ = classe_dichiarata("cachedelta_manifest_NGC.jsonl")
    c.uguale("dichiarata: cachedelta", cl, "manifest")
    c.uguale("dichiarata: cachedelta in scopo (decisione B)", scopo, True)
    cl, scopo, _ = classe_dichiarata("paper2_v1_amendments.jsonl")
    c.uguale("dichiarata: ledger", cl, "ledger")
    c.uguale("dichiarata: ledger fuori scopo", scopo, False)
    cl, _, _ = classe_dichiarata("qualcosa_di_nuovo.jsonl")
    c.uguale("dichiarata: sconosciuto -> None", cl, None)

    # ---- 20. il nome NON decide da solo: la discordanza si vede -----------
    with tempfile.TemporaryDirectory() as tmp:
        radice = Path(tmp)
        # un file chiamato gate*.jsonl il cui contenuto e' un registro di run
        (radice / "gate99.jsonl").write_bytes(b'{"idx":0,"N_H1":1.0}\n{"idx":1,"N_H1":2.0}\n')
        record = censisci_file(radice / "gate99.jsonl", radice)
        # 1.5 (18 set): un gate dichiarato si giudica dal verdetto. La proprieta'
        # che questo controllo protegge resta — un file chiamato gate che e' un
        # run NON passa — e cambia il nome dello stato, che pesa sull'uscita.
        c.uguale("discordanza rilevata", record["stato_classe"], "GATE_SENZA_VERDETTO")
        c.uguale("discordanza: dichiarata", record["classe_dichiarata"], "gate")
        c.uguale("discordanza: misurata", record["classe_misurata"], "run")

    # ---- 21. baseline: prefisso conservato -> PASS ------------------------
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "r.jsonl"
        primo = b'{"key":"a","idx":0}\n'
        f.write_bytes(primo)
        n0, s0 = len(primo), sha256_bytes(primo)
        with f.open("ab") as fh:
            fh.write(b'{"key":"b","idx":1}\n')
        esito = verifica_prefisso(f, n0, s0)
        c.uguale("baseline: append PASS", esito["esito"], "PASS")
        c.uguale("baseline: byte appesi", esito["byte_appesi"], 20)

    # ---- 22. DIFETTO baseline: prefisso modificato -> FAIL ----------------
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "r.jsonl"
        primo = b'{"key":"a","idx":0}\n'
        f.write_bytes(primo)
        n0, s0 = len(primo), sha256_bytes(primo)
        f.write_bytes(b'{"key":"z","idx":9}\n{"key":"b","idx":1}\n')
        esito = verifica_prefisso(f, n0, s0)
        c.uguale("baseline: riscrittura FAIL", esito["esito"], "FAIL")
        c.uguale("baseline: difetto nominato", esito["difetto"], "prefisso_modificato")

    # ---- 23. DIFETTO baseline: file accorciato -> FAIL --------------------
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "r.jsonl"
        primo = b'{"key":"a","idx":0}\n{"key":"b","idx":1}\n'
        f.write_bytes(primo)
        n0, s0 = len(primo), sha256_bytes(primo)
        f.write_bytes(b'{"key":"a","idx":0}\n')
        esito = verifica_prefisso(f, n0, s0)
        c.uguale("baseline: troncamento FAIL", esito["esito"], "FAIL")
        c.uguale("baseline: difetto nominato", esito["difetto"], "file_accorciato")

    # ---- 24. rifiuto di scrivere fuori dalle cartelle ammesse -------------
    try:
        verifica_uscita(Path("results/paper1/x.jsonl"))
        c.verifica("rifiuto uscita results/paper1", False)
    except SystemExit:
        c.verifica("rifiuto uscita results/paper1", True)
    try:
        verifica_uscita(Path("results/paper2/x.jsonl"))
        c.verifica("accetta results/paper2", True)
    except SystemExit:
        c.verifica("accetta results/paper2", False)
    try:
        verifica_uscita(Path("logs/x.jsonl"))
        c.verifica("accetta logs", True)
    except SystemExit:
        c.verifica("accetta logs", False)

    # ---- 25. ispezione AST: append con e senza fsync ----------------------
    with tempfile.TemporaryDirectory() as tmp:
        buono = Path(tmp) / "buono.py"
        buono.write_text(
            'import os, json\n'
            'P = "results/paper2/x.jsonl"\n'
            'def scrivi(r):\n'
            '    with open(P, "a", encoding="utf-8") as fh:\n'
            '        fh.write(json.dumps(r) + "\\n")\n'
            '        fh.flush()\n'
            '        os.fsync(fh.fileno())\n',
            encoding="utf-8")
        i = ispeziona_sorgente(buono)
        c.uguale("ast: registro citato", i["registri_citati"], ["results/paper2/x.jsonl"])
        c.uguale("ast: aperture append", len(i["aperture_append"]), 1)
        c.uguale("ast: flush", i["usa_flush"], True)
        c.uguale("ast: fsync", i["usa_fsync"], True)

        cattivo = Path(tmp) / "cattivo.py"
        cattivo.write_text(
            'import json\n'
            'def scrivi(r):\n'
            '    with open("results/paper2/y.jsonl", "a") as fh:\n'
            '        fh.write(json.dumps(r) + "\\n")\n',
            encoding="utf-8")
        i = ispeziona_sorgente(cattivo)
        c.uguale("ast: fsync assente rilevato", i["usa_fsync"], False)
        c.uguale("ast: append comunque rilevato", len(i["aperture_append"]), 1)

        # DIFETTO RIPRODOTTO: Path.open(mode) ha il modo in args[0], non
        # in args[1]. La versione 1.0 lo mancava e dichiarava 67 scrittori
        # quando ne mancavano almeno una dozzina.
        pathopen = Path(tmp) / "pathopen.py"
        pathopen.write_text(
            'import json\n'
            'from pathlib import Path\n'
            'def append_jsonl(path, rec):\n'
            '    p = Path(path)\n'
            '    with p.open("a", encoding="utf-8") as fh:\n'
            '        fh.write(json.dumps(rec) + "\\n")\n',
            encoding="utf-8")
        i = ispeziona_sorgente(pathopen)
        c.uguale("ast: Path.open in append rilevato", len(i["aperture_append"]), 1)
        c.uguale("ast: forma metodo", i["aperture_append"][0]["forma"], "metodo")
        c.uguale("ast: modo letto da args[0]", i["aperture_append"][0]["modo"], "a")

        pathlettore = Path(tmp) / "pathlettore.py"
        pathlettore.write_text(
            'from pathlib import Path\n'
            'Path("x.jsonl").open("r", encoding="utf-8")\n',
            encoding="utf-8")
        i = ispeziona_sorgente(pathlettore)
        c.uguale("ast: Path.open in lettura non e' append", len(i["aperture_append"]), 0)

        # il builtin resta letto da args[1]
        misto = Path(tmp) / "misto.py"
        misto.write_text('open("a.jsonl", "a")\n', encoding="utf-8")
        i = ispeziona_sorgente(misto)
        c.uguale("ast: builtin ancora letto da args[1]", len(i["aperture_append"]), 1)
        c.uguale("ast: forma builtin", i["aperture_append"][0]["forma"], "builtin")

        # scrittura in sola lettura: non e' uno scrittore
        lettore = Path(tmp) / "lettore.py"
        lettore.write_text('open("results/paper2/z.jsonl", "r")\n', encoding="utf-8")
        i = ispeziona_sorgente(lettore)
        c.uguale("ast: modo r non e' append", len(i["aperture_append"]), 0)

    # ---- 26. cancello di riproduzione: conteggi ---------------------------
    with tempfile.TemporaryDirectory() as tmp:
        radice = Path(tmp)
        (radice / "results" / "paper2").mkdir(parents=True)
        (radice / "results" / "paper2" / "fase3.jsonl").write_bytes(
            b'{"idx":0,"key":"a","N_H1":1.0}\n{"idx":1,"key":"b","N_H1":2.0}\n')
        (radice / "results" / "paper2" / "gate53.jsonl").write_bytes(
            b'{"gate":"5.3","verdetto":"PASS"}\n')
        percorsi = trova_registri([radice / "results"])
        c.uguale("cancello: file trovati", len(percorsi), 2)
        righe = sum(misura_bytes(p.read_bytes())["n_righe"] for p in percorsi)
        c.uguale("cancello: righe totali", righe, 3)

    # ---- 27. un file pulito passa tutte le proprieta' applicabili ---------
    esiti = valuta_proprieta("run", misura_bytes(pulito), misura_record(pulito))
    c.uguale("pulito: strutturale", esiti["append_strutturale"]["esito"], "PASS")
    c.uguale("pulito: atomico", esiti["atomico_residuo"]["esito"], "PASS")
    c.uguale("pulito: crashsafe", esiti["crashsafe_residuo"]["esito"], "PASS")
    c.uguale("pulito: resumable", esiti["resumable"]["esito"], "PASS")

    # ---- 28. ogni proprieta' dichiara il proprio metodo -------------------
    for nome, esito in esiti.items():
        c.verifica("metodo dichiarato per %s" % nome, "metodo" in esito and esito["metodo"])

    # ---- 29. ripresa dichiarata: chiave del runner di Fase 3 --------------
    # Il registro reale ha componenti ASSENTI (carve_reseed, origin_offset,
    # real_space...): il runner le legge con .get(), quindi la chiave e'
    # tollerante all'assenza. Un controllo di presenza darebbe FAIL su un
    # registro corretto — e' il difetto che ha prodotto i 33 del 15 set.
    righe = []
    for reg in ("NGC", "SGC"):
        for i in range(10):
            righe.append({"region": reg, "index": i,
                          "points": {"B1": 1.0, "B5": 2.0, "FID": 3.0},
                          "erosions": [1, 2]})
    for i in range(5):                      # record smoke, esclusi da `done`
        righe.append({"region": "NGC", "index": i, "smoke": True,
                      "points": {"B1": 1.0, "B5": 2.0, "FID": 3.0},
                      "erosions": [1, 2]})
    e = valuta_ripresa("fase3_mock.jsonl", righe)
    c.uguale("ripresa: modo", e["modo"], "ripresa_dal_registro")
    c.uguale("ripresa: smoke esclusi", e["record_esclusi"], 5)
    c.uguale("ripresa: considerati", e["record_considerati"], 20)
    c.uguale("ripresa: zero duplicati nonostante i campi assenti", e["duplicati"], 0)
    c.verifica("ripresa: DA_RIVEDERE se il conteggio cambia",
               any("DA_RIVEDERE" in d for d in e["difetti"]))

    # ---- 30. DIFETTO: due offset diversi senza origin_offset nella chiave -
    # E' l'incidente --origin-offset. Con la componente dichiarata i due
    # gruppi si separano; togliendola collidono.
    righe = []
    for off in (4.0, -2.1):
        for i in range(10):
            righe.append({"region": "NGC", "index": i, "origin_offset": off,
                          "points": {"B1": 1.0}, "erosions": [1]})
    e = valuta_ripresa("fase3_mock_off_hi.jsonl", righe)
    c.uguale("origin_offset nella chiave: nessun duplicato", e["duplicati"], 0)
    senza = [k for k in RIPRESA_DICHIARATA["fase3_mock_off_hi.jsonl"]["chiave"]
             if k != "origin_offset"]
    visti = {}
    for r in righe:
        tup = tuple(_valore_chiave(r, k, ["real_space", "fixed_observables",
                                          "replica_randomise"]) for k in senza)
        visti[tup] = visti.get(tup, 0) + 1
    c.uguale("senza origin_offset: dieci collisioni",
             sum(v - 1 for v in visti.values() if v > 1), 10)

    # ---- 31. nessuna_ripresa_id: l'identificatore deve essere unico -------
    righe = [{"idx": i, "N_H1": float(i)} for i in range(2000)]
    e = valuta_ripresa("onepoint_v1_NGC.jsonl", righe)
    c.uguale("nessuna_ripresa_id: esito", e["esito"], "PASS")
    c.uguale("nessuna_ripresa_id: applicabile", e["applicabile"], True)
    c.uguale("nessuna_ripresa_id: duplicati", e["duplicati"], 0)
    e = valuta_ripresa("onepoint_v1_NGC.jsonl", righe + [{"idx": 0, "N_H1": 0.0}])
    c.uguale("nessuna_ripresa_id: doppione rilevato", e["esito"], "FAIL")

    # ---- 32. nessuna_ripresa_senza_id: nessun controllo, ma dichiarato ----
    e = valuta_ripresa("ensemble_v2_NGC.jsonl", [{"_n_gal": i} for i in range(2000)])
    c.uguale("senza_id: modo", e["modo"], "nessuna_ripresa_senza_id")
    c.uguale("senza_id: non applicabile", e["applicabile"], False)
    c.uguale("senza_id: esito DICHIARATO, non NA", e["esito"], "DICHIARATO")
    c.verifica("senza_id: nessuna chiave dichiarata", "chiave" not in e)

    # ---- 33. na_una_passata e na_scansione -------------------------------
    e = valuta_ripresa("compD_NGC.jsonl", [{"a": i} for i in range(4)])
    c.uguale("na_una_passata: esito", e["esito"], "NA")
    e = valuta_ripresa("cachedelta_manifest_NGC.jsonl", [{"rel": str(i)} for i in range(2000)])
    c.uguale("na_scansione: esito", e["esito"], "NA")

    # ---- 34. DA_RIVEDERE quando il registro cresce oltre la dichiarazione -
    e = valuta_ripresa("compD_NGC.jsonl", [{"a": i} for i in range(9)])
    c.uguale("na con conteggio cambiato: FAIL", e["esito"], "FAIL")
    c.uguale("na: conteggio riportato", e["record_cambiati"]["ora"], 9)

    # ---- 35. da_leggere non e' un pass ------------------------------------
    # Oggi nessun registro e' in questo stato: il ramo si prova iniettando una
    # voce temporanea, perche' un ramo non coperto e' un ramo non verificato.
    RIPRESA_DICHIARATA["__prova_da_leggere__.jsonl"] = {
        "modo": "da_leggere", "runner": "src/un_runner_mai_letto.py",
        "motivo": "voce di prova del selftest"}
    try:
        e = valuta_ripresa("__prova_da_leggere__.jsonl", [{"key": str(i)} for i in range(5)])
        c.uguale("da_leggere: esito", e["esito"], "DA_LEGGERE")
        c.verifica("da_leggere: non e' PASS", e["esito"] != "PASS")
        c.verifica("da_leggere: nomina il runner", "un_runner_mai_letto" in e["runner"])
        c.verifica("da_leggere: difetto registrato", "runner_non_letto" in e["difetti"])
    finally:
        del RIPRESA_DICHIARATA["__prova_da_leggere__.jsonl"]
    c.verifica("nessun registro reale resta da_leggere",
               not any(d["modo"] == "da_leggere" for d in RIPRESA_DICHIARATA.values()))

    # ---- 36. registro senza dichiarazione ---------------------------------
    e = valuta_ripresa("qualcosa_di_nuovo.jsonl", [{"a": 1}])
    c.uguale("non dichiarato", e["esito"], "NON_DICHIARATO")

    # ---- 37. n10_phases: chiave a due componenti --------------------------
    righe = [{"tipo": "desi_pr", "idx": i} for i in range(50)]
    righe += [{"tipo": "mock_pr", "idx": 200 + i} for i in range(100)]
    e = valuta_ripresa("n10_phases_NGC.jsonl", righe)
    c.uguale("n10_phases: esito", e["esito"], "PASS")
    c.uguale("n10_phases: considerati", e["record_considerati"], 150)

    # ---- 38. per_mock: duplicati ATTESI non sono un difetto ---------------
    # Tre passate su 200 unita' danno 400 duplicati. Dichiararli attesi e'
    # la differenza fra un registro letto per unione e un registro rotto.
    righe = []
    for passata in range(3):
        for i in range(200):
            righe.append({"key": "mock_%04d" % i, "cells.R%d" % (5 + passata): float(i)})
    e = valuta_ripresa("per_mock_NGC_erosion_restrict.jsonl", righe)
    c.uguale("per_mock erosion NGC: esito", e["esito"], "PASS")
    c.uguale("per_mock erosion NGC: duplicati", e["duplicati"], 400)
    c.uguale("per_mock erosion NGC: attesi", e["duplicati_attesi"], 400)

    e = valuta_ripresa("per_mock_SGC_erosion_restrict.jsonl", righe[:400])
    c.uguale("per_mock erosion SGC: duplicati", e["duplicati"], 200)
    c.uguale("per_mock erosion SGC: esito", e["esito"], "PASS")

    # una quarta passata inattesa deve emergere
    e = valuta_ripresa("per_mock_NGC_erosion_restrict.jsonl",
                       righe + [{"key": "mock_%04d" % i} for i in range(200)])
    c.uguale("per_mock: passata in piu' rilevata", e["esito"], "FAIL")

    # ---- 39. per_mock canonico: nessun duplicato --------------------------
    e = valuta_ripresa("per_mock_NGC_R5.jsonl",
                       [{"key": "m%04d" % i} for i in range(2000)])
    c.uguale("per_mock R5: esito", e["esito"], "PASS")
    c.uguale("per_mock R5: duplicati", e["duplicati"], 0)
    c.verifica("per_mock R5: il glob non scavalca il nome esatto",
               "erosion" not in (e.get("motivo") or ""))

    # ---- 40. i cancelli sono dichiarati, non piu' `non_dichiarato` --------
    for nome, n in (("gate21.jsonl", 5), ("gate25.jsonl", 2),
                    ("gate53.jsonl", 3), ("gate53_margini.jsonl", 1)):
        e = valuta_ripresa(nome, [{"a": i} for i in range(n)])
        c.uguale("cancello %s: NA" % nome, e["esito"], "NA")

    # ---- 41. i 48 in scopo hanno tutti una dichiarazione -----------------
    c.uguale("l'elenco in scopo ha 53 voci", len(REGISTRI_IN_SCOPO_15SET), 53)
    senza = [n for n in REGISTRI_IN_SCOPO_15SET if _dichiarazione_ripresa(n) is None]
    c.uguale("ogni registro in scopo ha una dichiarazione di ripresa", senza, [])
    senza_classe = [n for n in REGISTRI_IN_SCOPO_15SET if classe_dichiarata(n)[0] is None]
    c.uguale("ogni registro in scopo ha una classe dichiarata", senza_classe, [])
    fuori = [n for n in REGISTRI_IN_SCOPO_15SET if not classe_dichiarata(n)[1]]
    c.uguale("nessun registro dell'elenco e' fuori scopo", fuori, [])

    # ---- 42. i cinque tier del congelamento sono in scopo ----------------
    for tier in ("diagrams", "features", "fields", "records", "superseded"):
        nome = "ensemble_v1_manifest_%s.jsonl" % tier
        cl, scopo, _ = classe_dichiarata(nome)
        c.uguale("tier %s: classe" % tier, cl, "manifest")
        c.uguale("tier %s: in scopo" % tier, scopo, True)
        c.uguale("tier %s: ripresa" % tier,
                 _dichiarazione_ripresa(nome)["modo"], "na_scansione")
    c.verifica("il tier records porta la nota sui digest ripetuti",
               "218" in _dichiarazione_ripresa("ensemble_v1_manifest_records.jsonl")["motivo"])

    # ---- 43. verdetto: annidato e `pass` (1.5, voce 6.2-vi) ---------------
    # DIFETTO RIPRODOTTO: queste forme davano segnale 0 fino alla 1.4.
    g53 = b'{"pass":false,"fails":["x"],"region":"NGC"}\n{"pass":true,"fails":[],"region":"NGC"}\n'
    c.uguale("gate53: pass booleano e' un verdetto", misura_record(g53)["segnale_verdetto"], 2)
    marg = b'{"region":"NGC","margine_1_z":{"soglia":3,"esito":"confermata"}}\n'
    c.uguale("margini: esito annidato e' un verdetto", misura_record(marg)["segnale_verdetto"], 1)
    falsi = b'{"mask_pass":"derive","F_ap_passed":1.03,"bypass_signal":3,"x":{"passenger":1}}\n'
    c.uguale("nome per uguaglianza: nessun falso positivo", misura_record(falsi)["segnale_verdetto"], 0)
    profondo = b'{"a":{"b":{"c":{"d":{"e":{"esito":"PASS"}}}}}}\n'
    c.uguale("oltre la profondita' dichiarata non si cerca", misura_record(profondo)["segnale_verdetto"], 0)

    # ---- 44. un gate si giudica dal verdetto, non dalla classe -------------
    with tempfile.TemporaryDirectory() as td:
        radice = Path(td)
        (radice / "results" / "paper2").mkdir(parents=True)
        g25 = radice / "results" / "paper2" / "gate25.jsonl"
        g25.write_bytes(b'{"gate":"2.5","pass":true,"seed":1,"idx":0}\n'
                        b'{"gate":"2.5","pass":true,"seed":2,"idx":1}\n')
        r25 = censisci_file(g25, radice)
        c.uguale("gate25: indice e verdetto -> GATE_CON_VERDETTO", r25["stato_classe"], "GATE_CON_VERDETTO")
        c.uguale("gate25: nessuna discordanza per costruzione", r25["gate_senza_verdetto"], False)
        muto = radice / "results" / "paper2" / "gate99.jsonl"
        muto.write_bytes(b'{"idx":0,"valore":1.0}\n{"idx":1,"valore":2.0}\n')
        c.uguale("gate senza verdetto -> GATE_SENZA_VERDETTO",
                 censisci_file(muto, radice)["stato_classe"], "GATE_SENZA_VERDETTO")

    # ---- 45. i 67 del 15 set, per nome esatto, fuori scopo -----------------
    sessantasette = [g for g, _, _, m in CLASSI_DICHIARATE if "fuori scopo 6.1;" in m]
    c.uguale("i 67 sono dichiarati", len(sessantasette), 67)
    c.uguale("nessuno dei 67 e' un glob", [g for g in sessantasette if any(x in g for x in "*?[")], [])
    c.uguale("nessuno dei 67 e' in scopo", [g for g in sessantasette if classe_dichiarata(g)[1]], [])
    c.uguale("ognuno risolve alla propria riga", [g for g in sessantasette
             if "fuori scopo 6.1;" not in (classe_dichiarata(g)[2] or "")], [])
    c.uguale("un nome nuovo resta non classificato", classe_dichiarata("qualcosa_di_nuovo.jsonl")[0], None)

    # ---- 46. registri di figura (1.6, 25 set): nome esatto, log, fuori scopo --
    for nome in ("fig_F1.jsonl", "fig_F7.jsonl"):
        cl, scopo, _ = classe_dichiarata(nome)
        c.uguale("%s: classe log" % nome, cl, "log")
        c.uguale("%s: fuori scopo" % nome, scopo, False)
        d = _dichiarazione_ripresa(nome)
        c.uguale("%s: ripresa" % nome, d["modo"], "na_una_passata")
        c.verifica("%s: nessun conteggio dichiarato" % nome, "record_al_15set" not in d)
        e = valuta_ripresa(nome, [{"schema": "x"} for _ in range(7)])
        c.uguale("%s: un rilancio non rende vecchia la dichiarazione" % nome, e["esito"], "NA")
    c.uguale("una figura nuova resta non classificata", classe_dichiarata("fig_F2.jsonl")[0], None)
    c.uguale("una figura nuova non ha ripresa dichiarata", _dichiarazione_ripresa("fig_F2.jsonl"), None)

    totale = c.ok + len(c.ko)
    print("selftest: %d/%d" % (c.ok, totale))
    if c.ko:
        print("FALLITI:")
        for nome in c.ko:
            print("  %s" % nome)
        return 1
    return 0


# ===========================================================================
# riga di comando
# ===========================================================================

def principale(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="paper2_censimento_registri.py",
        description="Censimento dei registri JSONL — voce 6.1 della Fase 6.")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("censimento", help="misura ogni registro trovato")
    p.add_argument("--base", default=".", help="radice del repository (default: .)")
    p.add_argument("--roots", nargs="+", default=["results"],
                   help="cartelle in cui cercare i .jsonl (default: results)")
    p.add_argument("--out", default=None, help="registro di uscita (.jsonl)")
    p.add_argument("--baseline", default=None,
                   help="uscita di una passata precedente, per verificare append-only")
    p.add_argument("--attesi-file", type=int, default=None, dest="attesi_file")
    p.add_argument("--attese-righe", type=int, default=None, dest="attese_righe")
    p.set_defaults(funzione=comando_censimento)

    p = sub.add_parser("scrittori", help="ispezione AST dei percorsi di scrittura")
    p.add_argument("--base", default=".", help="radice del repository (default: .)")
    p.add_argument("--src", default="src", help="cartella dei sorgenti (default: src)")
    p.add_argument("--out", default=None, help="registro di uscita (.jsonl)")
    p.set_defaults(funzione=comando_scrittori)

    p = sub.add_parser("selftest", help="riproduce ogni difetto prima di dichiararlo rilevato")
    p.set_defaults(funzione=comando_selftest)

    args = parser.parse_args(argv)
    return args.funzione(args)


if __name__ == "__main__":
    sys.exit(principale())

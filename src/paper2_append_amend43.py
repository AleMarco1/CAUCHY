#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend43.py - Emendamento 43: la Componente D e' TRACCIATA, a
posteriori per riproduzione, e resta nel paper.

Chiude il rilievo del referee sul §3.9. Clona il meccanismo dell'appender 42:
numerazione posizionale, tre digest, utc con offset +00:00, chiavi ordinate,
ensure_ascii DERIVATO dal file, schema dall'intersezione delle ultime tre righe,
lettore robusto ai fine riga misti.

I fatti che il record afferma sono verificati MECCANICAMENTE dal selftest, che
ricalcola i digest, rilegge i registri e riesegue il confronto D-T2.

Sottocomandi
------------
  inspect    schema, righe, digest, stato degli ingressi. Non scrive.
  dump N     stampa la riga N. Non scrive.
  gates      stato dei tre cancelli D-T1/D-T2/D-T3. Non scrive.
  selftest   tutti i controlli. Non scrive.
  append     costruisce e mostra il record; scrive solo con --apply.
  verify     ricontrolla il registro dopo l'append.

Cancelli d'append (bloccanti)
-----------------------------
  G1   sha256 del reference invariato e uguale a quello citato nella riga 42;
  G2   il registro ha esattamente 42 righe prima dell'append;
  G2b  la riga 42 si ri-serializza byte per byte identica a se stessa;
  G3   idempotenza: marker assente e item non gia' usato;
  G3b  prerequisito: il record 42 e' presente ED e' sulla riga 42;
  G4   schema: tutte le chiavi comuni alle righe 40-42;
  G6   --item obbligatorio;
  M1   sha256 degli ingressi = quelli dichiarati;
  M2   i record dt2 portano digest, names_source e infer_score_max dichiarati;
  M3   le quattordici correlazioni parziali sono identiche a precisione piena;
  M4   il punteggio massimo di infer_names sta sotto la soglia dichiarata;
  M5   il percorso del manifest a riga 8043 NON risolve: il difetto che il
       record registra e' ancora vero al momento in cui lo si scrive.

Uscita ASCII pura: console Windows cp1252 senza UnicodeEncodeError.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

# ---------------------------------------------------------------------------
# Costanti dichiarate
# ---------------------------------------------------------------------------

AMEND_POSITION = 43
EXPECTED_LINES_BEFORE = 42

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")

PARAMS_PATH = os.path.join("data", "raw", "quijote", "3D_cubes",
                           "latin_hypercube_nwLH", "latin_hypercube_nwLH_params.txt")
PARAMS_SHA = "bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e"
PARAMS_BYTES = 156070
PARAMS_ROWS = 2001
PARAMS_HEADER = ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "M_nu", "w0"]

NH1 = {
    "NGC": (os.path.join("results", "paper1", "per_mock_NGC_R5.jsonl"),
            "67eead4517b206fe00ea83756b5f33bd6a38e8c37b283fc81cb7a5764852b412", 1607497),
    "SGC": (os.path.join("results", "paper1", "per_mock_SGC_R5.jsonl"),
            "4463bde0aa918be054d60f0a1ee9cf34feacd7e3b7ff9d04e3c40ac3115f2055", 1596343),
}

COMPD = {"NGC": os.path.join("results", "paper2", "compD_NGC.jsonl"),
         "SGC": os.path.join("results", "paper2", "compD_SGC.jsonl")}
COMPD_DT2 = {k: v.replace(".jsonl", "_dt2.jsonl") for k, v in COMPD.items()}

INFER_SCORE_THRESHOLD = 0.10
INFER_SCORE_OBSERVED = 0.010495
NAMES_SOURCE = "header+position+values"

# Le quattordici correlazioni parziali NON si trascrivono: si leggono dal
# registro canonico al momento di costruire il record. Un primo tentativo le
# copio' dall'output di `compare`, che stampa con %+.16f - sedici DECIMALI, non
# diciassette cifre significative - e l'ultima cifra si perse. Stessa forma del
# record 22: un valore preso da un output invece che letto dal registro.
#
# L'ancoraggio indipendente e' la checklist D2, che le quota a quattro decimali:
# quello e' un documento separato, e su di esso si puo' legare senza trascrivere
# una precisione che la stampa non porta.
R_PARTIAL_4DP = {
    "NGC": {"Omega_m": 0.1855, "Omega_b": -0.1387, "h": 0.2373, "n_s": 0.3976,
            "sigma_8": 0.1897, "M_nu": -0.0673, "w0": 0.0549},
    "SGC": {"Omega_m": 0.1667, "Omega_b": -0.1319, "h": 0.2201, "n_s": 0.4163,
            "sigma_8": 0.2484, "M_nu": -0.0203, "w0": 0.0474},
}

MANIFEST_PATH = os.path.join("results", "phase0_data_manifest.json")
MANIFEST_BAD_PATH = os.path.join("data", "raw", "quijote", "3D_cubes",
                                 "latin_hypercube_nwLH_params.txt")

MARKER = "emendamento-43-componente-d-tracciata-per-riproduzione"
MARKER_42 = "emendamento-42-vitalita-posizionale-nel-registro-compD"
COMPANION_DOCUMENT = "risposta_referee.md §3.9; checklist_paper2.md items D2-D5"


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "component_d_is_traceable_a_posteriori_by_reproduction_and_stays_in_the_paper"

JSON_PATH = ("src/paper2_compD_partialcorr.py; results/paper2/compD_{NGC,SGC}.jsonl; "
             "results/paper2/compD_{NGC,SGC}_dt2.jsonl; results/phase0_data_manifest.json "
             "line 8043; risposta_referee.md §3.9")

OLD_VALUE = (
    "The referee observes that the input of Component D is not tracked, and that nothing derived "
    "from it may be reported until it is. The observation was correct and more specific than it "
    "looked. results/phase0_data_manifest.json carries a checksum for each of the 2000 nwLH density "
    "fields, and for the parameter file only a PATH - no digest anywhere in the manifest, in any of "
    "its three suite blocks. The path it carries, "
    "D:\\projects\\cauchy\\data\\raw\\quijote\\3D_cubes\\latin_hypercube_nwLH_params.txt, "
    "resolves to NO FILE: the file is one directory deeper, inside latin_hypercube_nwLH/. The "
    "default of --params at paper2_compD_partialcorr.py:484 named a third path, also nonexistent. "
    "And config_hash, which looked like it might pin the inputs, is sha256 of {nh1_path, "
    "params_path, n}: it hashes the DESCRIPTION of the configuration, not the bytes. So the half of "
    "the input that carries N_H1 was frozen and the half that carries the regressors - the only "
    "thing Component D adds - was not."
)

NEW_VALUE = {
    "what_was_found_on_disk": {
        "the_file_is_there": ("data/raw/quijote/3D_cubes/latin_hypercube_nwLH/"
                              "latin_hypercube_nwLH_params.txt, 156070 bytes, 2001 lines "
                              "(header included), last modified 27 Apr 2026 - four months before "
                              "the run of 26 Aug and unmodified since. sha256 "
                              "bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e."),
        "and_the_records_named_it": ("All four records in each hemisphere deposit params_path "
                                     "pointing at that file. The runs were launched with --params "
                                     "explicit, which is why the wrong default never bit."),
        "the_manifest_path_is_wrong": ("phase0_data_manifest.json line 8043 points at a path that "
                                       "does not exist. A manifest whose pointer does not resolve "
                                       "tracks nothing, even when the file is two directories "
                                       "away."),
    },
    "D_T1_digests_now_registered": {
        "params_sha256": PARAMS_SHA,
        "nh1_NGC_sha256": NH1["NGC"][1],
        "nh1_SGC_sha256": NH1["SGC"][1],
        "config_hash_is_left_alone": ("32af0533ef8c6da2 in NGC and 8e548c4d5ff892a0 in SGC keep the "
                                      "meaning they have on the deposited records. Redefining it to "
                                      "cover bytes would give one field two meanings across time and "
                                      "would break the comparison with what is already on disk. The "
                                      "byte digests are NEW fields, params_sha256 and nh1_sha256, so "
                                      "config_hash keeps both its meaning and its value."),
    },
    "D_T3_the_label_gates": {
        "what_it_does_not_claim": ("infer_names ALREADY defended against a column permutation: it "
                                   "compares the endpoints of each column with the nominal ranges, "
                                   "not the position, and on this suite the ranges separate - the "
                                   "closest pair, Omega_m against M_nu, scores 0.60 against ~0. "
                                   "That defence existed and is not claimed as new."),
        "what_is_new": ("(a) The file HEADER as a third source, the only one of the three "
                        "independent of PARAM_RANGES: position and values both depend on that "
                        "table, so if the table were wrong they would be wrong together and "
                        "nothing would notice. (b) An ABSOLUTE threshold with a stop: the "
                        "assignment used to be complete whatever the score, and the last column "
                        "never chose at all because only one name was left. (c) The outcome "
                        "deposited in the record instead of printed to the terminal."),
        "the_threshold_was_declared_before_the_run": ("0.10, declared before the run, from the "
                                                      "design and not from the "
                                                      "output: with 2000 samples a Latin hypercube "
                                                      "leaves edge gaps of order 1/2000 of the "
                                                      "span, so the true score sits below 1e-2, "
                                                      "while the nearest competitor sits at 0.60. "
                                                      "One order of magnitude above the first, six "
                                                      "times below the second."),
        "and_it_held_with_a_measured_margin": ("Observed maximum 0.010495, on M_nu, because "
                                               "PARAM_RANGES declares M_nu in (0.00, 1.00) while "
                                               "the suite samples from 0.0102 - the missing lower "
                                               "edge, not noise. Every other column scores 0.0005. "
                                               "The margin is therefore 9.5x, not the two orders of "
                                               "magnitude the design estimate suggested, and it is "
                                               "quoted as measured."),
        "names_source": ("header+position+values in both hemispheres: all three sources agree with "
                         "the labels in use."),
    },
    "D_T2_the_reproduction": {
        "what_was_required": ("Declared before the run: the fourteen partial correlations must "
                              "reproduce to FULL PRECISION in both hemispheres, no tolerance. One "
                              "r moving and Component D leaves the paper."),
        "what_happened": ("All fourteen identical to sixteen decimals, nine days after the original "
                          "run. r2_multi, r2_ceiling, attenuation, deficit_gen, n and config_hash "
                          "also identical. Gate 2.1 held on the way: 35436.6860 / 312.9892 in NGC "
                          "and 18712.9675 / 197.7874 in SGC against the frozen values."),
        "it_reproduced_the_falsification_too": ("P1 - |r(w0)| < 0.05 - fails again in NGC at "
                                                "+0.0549 and holds in SGC at +0.0474, exactly as "
                                                "record D3 registered. A falsified prediction that "
                                                "reproduces identically is better evidence than a "
                                                "confirmed one."),
        "and_it_crossed_the_patch": ("The dt2 records were written by the PATCHED script, the "
                                     "canonical ones by the unpatched script. The reproduction "
                                     "therefore also demonstrates that the five edits are INERT on "
                                     "the numbers. This was not designed; it is reported because it "
                                     "is true."),
        "the_order_was_forced": ("D-T3 before D-T2. A reproduction run with the same hard-coded "
                                 "label table would have reproduced a wrong label faithfully: it "
                                 "does not validate an assumption both executions share."),
    },
    "the_verdict": {
        "component_d_stays": ("The input is traceable. It is named by every deposited record, "
                              "present on disk, now digested, and it reproduces the reported "
                              "quantities exactly."),
        "and_the_distinction_that_goes_to_the_referee": ("The tracking is A POSTERIORI BY "
                                                         "REPRODUCTION, not contemporaneous "
                                                         "freezing. The test does not prove the "
                                                         "file of today is bit-identical to the "
                                                         "file of August; it proves the file of "
                                                         "today produces exactly the quantities "
                                                         "reported. For every number that enters "
                                                         "the paper the two coincide. The "
                                                         "difference is stated in one line rather "
                                                         "than left implicit."),
    },
    "a_defect_in_the_checking_tool_itself": {
        "what": ("paper2_compD_gates.py compare guarded the digest check with `if "
                 "B.get('params_sha256') and B[...] != EXPECTED`. With the field ABSENT the guard "
                 "is false and the check passes: absence and correctness gave the same verdict."),
        "why_it_is_registered": ("It did not bite - the fields were present and were verified by "
                                 "hand - but a gate that cannot distinguish a missing value from a "
                                 "right one is not a gate. Same class as record 41."),
        "the_correction": "The guard is removed: a missing digest fails.",
    },
    "what_this_does_not_do": ("It does not reopen Phase 3, does not touch any frozen value, and "
                              "writes nothing to the canonical compD registers - the reproduction "
                              "was written to compD_{NGC,SGC}_dt2.jsonl precisely so that a "
                              "verification would not mutate the thing being verified. It does not "
                              "correct phase0_data_manifest.json, which is a frozen artefact: the "
                              "wrong path at line 8043 is registered here, not rewritten there."),
}

RULES = {
    "amends_records": [],
    "a_manifest_pointer_that_does_not_resolve_tracks_nothing": ("Recording a path is not tracking. "
                                                                "A manifest entry must carry a "
                                                                "digest, and its path must resolve."),
    "a_reproduction_does_not_validate_a_shared_assumption": ("Run the gate on the assumption FIRST. "
                                                             "Two executions sharing a hard-coded "
                                                             "table reproduce its errors faithfully."),
    "a_verification_does_not_write_into_what_it_verifies": ("The reproduction went to a separate "
                                                            "file. The canonical register is "
                                                            "untouched and the question of which "
                                                            "record is canonical does not reopen."),
    "absent_and_correct_must_not_give_the_same_verdict": ("A check written as `if x and x != "
                                                          "expected` passes when x is missing. "
                                                          "Compare directly."),
    "companion_document": COMPANION_DOCUMENT,
    "marker": MARKER,
    "tracking_by_reproduction_is_declared_as_such": ("It is weaker than contemporaneous freezing "
                                                     "and stronger than nothing, and the difference "
                                                     "is written down rather than blurred."),
    "what_this_does_not_do": ("No frozen value modified, nothing written to the canonical compD "
                              "registers, phase0_data_manifest.json not rewritten."),
}

REASON = (
    "The referee's §3.9 objection is closed, and Component D stays in the paper. WHAT WAS FOUND. "
    "The manifest digests the 2000 nwLH density fields and gives the parameter file a path and no "
    "digest; that path, at phase0_data_manifest.json line 8043, resolves to NO FILE, the file "
    "being one directory deeper. The --params default named a third, also nonexistent, path. And "
    "config_hash hashes {nh1_path, params_path, n}, that is the DESCRIPTION of the configuration "
    "and not the bytes. So the half of the input carrying N_H1 was frozen and the half carrying the "
    "regressors was not. THREE GATES, IN A FORCED ORDER. D-T1 registers the digests: parameter file "
    "bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e, 156070 bytes, 2001 lines, "
    "unmodified since 27 April; and the two per_mock registers. config_hash is left alone and the "
    "byte digests are new fields, so one field does not acquire two meanings. D-T3 adds what was "
    "missing on the LABELS - and not what was already there: infer_names already defended against a "
    "column permutation, and that is not claimed as new. What is new is the file header as a third "
    "source independent of PARAM_RANGES, an absolute threshold with a stop, and the outcome "
    "deposited rather than printed. The threshold, 0.10, was declared from the design before the "
    "run; it held at 0.010495, driven by M_nu whose nominal lower edge is 0.00 while the suite "
    "samples from 0.0102 - a margin of 9.5x and not the two orders the estimate suggested, quoted "
    "as measured. D-T2 then reproduced: fourteen partial correlations identical to sixteen decimals "
    "in both hemispheres, nine days on, together with r2_multi, attenuation, deficit_gen and "
    "config_hash, and with gate 2.1 holding at 35436.6860 / 312.9892 and 18712.9675 / 197.7874. It "
    "reproduced the FALSIFICATION as well: P1 fails again in NGC at +0.0549. The order was forced - "
    "D-T3 before D-T2 - because a reproduction run with the same hard-coded table would have "
    "reproduced a wrong label faithfully. AND AN UNPLANNED RESULT: the dt2 records were written by "
    "the patched script and the canonical ones by the unpatched script, so the reproduction also "
    "shows the five edits are inert on the numbers. THE DISTINCTION THAT GOES TO THE REFEREE: this "
    "is tracking A POSTERIORI BY REPRODUCTION, not contemporaneous freezing. It does not prove the "
    "file of today is bit-identical to the file of August; it proves it produces exactly the "
    "quantities reported, which for every number in the paper is the same thing. That is written in "
    "one line rather than left implicit. A DEFECT IN THE CHECKING TOOL was caught and is registered: "
    "the compare guarded its digest check with `if B.get(...) and ...`, so an ABSENT digest passed. "
    "It did not bite, the fields being present and checked by hand, but a gate that cannot tell a "
    "missing value from a right one is not a gate."
)

EVIDENCE_TEMPLATE = (
    "Runs of 5 Sep 2026. D-T1: sha256 of "
    "data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt = "
    "bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e, 156070 bytes, 2001 lines, "
    "header '#Omega_m Omega_b h n_s sigma_8 M_nu w0'; results/paper1/per_mock_NGC_R5.jsonl = "
    "67eead4517b206fe00ea83756b5f33bd6a38e8c37b283fc81cb7a5764852b412 (1607497 bytes); "
    "per_mock_SGC_R5.jsonl = 4463bde0aa918be054d60f0a1ee9cf34feacd7e3b7ff9d04e3c40ac3115f2055 "
    "(1596343 bytes). D-T3 selftest: 12 checks, 0 failures, including the two that matter - with "
    "PARAM_RANGES swapped the old code mislabels SILENTLY and the gate stops; a column that does "
    "not fill its interval stops on the threshold. Both runs printed names_source "
    "'header+position+values' and infer_score_max 0.010495, and both dt2 records deposit it. "
    "D-T2, the fourteen partial correlations read from the canonical registers at repr "
    "precision and NOT transcribed from a formatted print: %s - each identical between the "
    "canonical record and "
    "the dt2 record. R^2 0.2606 (NGC) and 0.2773 (SGC) against the ceiling 0.6980; implied 1-sigma "
    "on w0 +-3.13 and +-5.71. The manifest path "
    "data/raw/quijote/3D_cubes/latin_hypercube_nwLH_params.txt was confirmed absent at the time of "
    "writing, which is the defect this record registers."
)


def make_evidence():
    """I numeri esatti si leggono dal registro canonico, non si trascrivono."""
    G = analyse_gates()
    parts = []
    for region in ("NGC", "SGC"):
        ex = G["D-T2"][region].get("r_exact")
        if not ex:
            return EVIDENCE_TEMPLATE % ("(registri assenti: numeri non derivabili)")
        parts.append("%s %s" % (region, ", ".join(
            "%s %r" % (k, ex[k]) for k in sorted(ex))))
    return EVIDENCE_TEMPLATE % "; ".join(parts)

# ---------------------------------------------------------------------------
# Utilita'
# ---------------------------------------------------------------------------

def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_jsonl(raw):
    """Spezza su LF e toglie un CR finale: robusto ai fine riga MISTI.
    Assumere un terminatore uniforme incolla due record quando non lo e'."""
    parts = raw.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    lines, terms = [], []
    for pt in parts:
        if pt.endswith(b"\r"):
            lines.append(pt[:-1])
            terms.append(b"\r\n")
        else:
            lines.append(pt)
            terms.append(b"\n")
    keep = [(l, t) for l, t in zip(lines, terms) if l.strip()]
    return [l for l, _ in keep], [t for _, t in keep]


def eol_profile(terms):
    """(n_crlf, n_lf, posizioni 1-based delle righe che deviano dalla maggioranza)."""
    n_crlf = sum(1 for t in terms if t == b"\r\n")
    n_lf = len(terms) - n_crlf
    major = b"\r\n" if n_crlf >= n_lf else b"\n"
    odd = [i for i, t in enumerate(terms, start=1) if t != major]
    return n_crlf, n_lf, odd


def read_jsonl(path):
    """Ritorna (recs, newline, pure_ascii, sorted_keys, raw, righe, terminatori).
    `newline` e' il terminatore dell'ULTIMA riga: e' dopo quella che si appende."""
    with open(path, "rb") as f:
        raw = f.read()
    lines, terms = split_jsonl(raw)
    newline = terms[-1] if terms else b"\r\n"
    pure_ascii = all(b < 128 for b in raw)
    recs = []
    for i, ln in enumerate(lines, start=1):
        try:
            recs.append(json.loads(ln.decode("utf-8")))
        except Exception as exc:
            fail("%s riga %d non e' JSON valido: %s" % (path, i, exc))
    sorted_keys = all(list(r.keys()) == sorted(r.keys()) for r in recs)
    return recs, newline, pure_ascii, sorted_keys, raw, lines, terms


def read_ledger(path):
    return read_jsonl(path)


def utc_now():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def common_keys(recs, n=3):
    tail = recs[-n:] if len(recs) >= n else recs
    s = set(tail[0].keys())
    for r in tail[1:]:
        s &= set(r.keys())
    return sorted(s)




def analyse_gates():
    """Ricalcola lo stato dei tre cancelli dai file. Non scrive nulla."""
    out = {"D-T1": {}, "D-T2": {}, "D-T3": {}}

    out["D-T1"]["params"] = {
        "path": PARAMS_PATH, "exists": os.path.isfile(PARAMS_PATH),
        "sha256": sha256_file(PARAMS_PATH) if os.path.isfile(PARAMS_PATH) else None,
        "expected": PARAMS_SHA,
        "bytes": os.path.getsize(PARAMS_PATH) if os.path.isfile(PARAMS_PATH) else None,
    }
    for region, (path, sha, size) in sorted(NH1.items()):
        out["D-T1"]["nh1_" + region] = {
            "path": path, "exists": os.path.isfile(path),
            "sha256": sha256_file(path) if os.path.isfile(path) else None,
            "expected": sha,
            "bytes": os.path.getsize(path) if os.path.isfile(path) else None,
        }
    out["D-T1"]["manifest_path_resolves"] = os.path.isfile(MANIFEST_BAD_PATH)

    for region in ("NGC", "SGC"):
        a, b = COMPD[region], COMPD_DT2[region]
        info = {"canonical": a, "repro": b,
                "both_present": os.path.isfile(a) and os.path.isfile(b)}
        if info["both_present"]:
            A = read_jsonl(a)[0][-1]
            B = read_jsonl(b)[0][-1]
            ra = {r["param"]: r.get("r_partial") for r in A.get("rows", [])}
            rb = {r["param"]: r.get("r_partial") for r in B.get("rows", [])}
            info["params"] = sorted(ra)
            info["identical"] = (ra == rb)
            info["matches_checklist_4dp"] = all(
                round(v, 4) == R_PARTIAL_4DP[region].get(k)
                for k, v in ra.items()) and set(ra) == set(R_PARTIAL_4DP[region])
            info["r_exact"] = ra
            info["fields_equal"] = all(A.get(k) == B.get(k) for k in
                                       ("r2_multi", "r2_ceiling", "attenuation",
                                        "deficit_gen", "n", "config_hash"))
            info["repro_params_sha256"] = B.get("params_sha256")
            info["repro_nh1_sha256"] = B.get("nh1_sha256")
            info["names_source"] = B.get("names_source")
            info["infer_score_max"] = B.get("infer_score_max")
        out["D-T2"][region] = info
        out["D-T3"][region] = {
            "names_source": out["D-T2"][region].get("names_source"),
            "infer_score_max": out["D-T2"][region].get("infer_score_max"),
            "threshold": INFER_SCORE_THRESHOLD,
        }
    return out

def _renumber(rule, position):
    """La numbering_rule della riga precedente termina con 'This is record 41.':
    ereditarla verbatim scriverebbe il numero sbagliato. Si riscrive l'ultimo
    intero della stringa con la posizione effettiva."""
    if not isinstance(rule, str):
        return rule
    import re as _re
    hits = list(_re.finditer(r"\b\d+\b", rule))
    if not hits:
        return rule
    last = hits[-1]
    return rule[:last.start()] + str(position) + rule[last.end():]


def build_record(recs, ref_path, file_sha, self_sha, item, overrides):
    prev = recs[-1]
    known = {
        "type": "protocol",
        "utc": utc_now(),
        "item": item,
        "document": prev.get("document"),
        "reference_file": prev.get("reference_file", ref_path.replace("\\", "/")),
        "reference_file_sha256": file_sha,
        "reference_self_sha256": self_sha,
        "numbering_rule": _renumber(prev.get("numbering_rule"), len(recs) + 1),
        "reason": REASON,
        "evidence": make_evidence(),
        "key": KEY,
        "json_path": JSON_PATH,
        "old_value": OLD_VALUE,
        "new_value": NEW_VALUE,
        "rules": RULES,
    }

    required = common_keys(recs, 3)
    rec = {}
    unfilled = []
    for k in required:
        if k in overrides:
            rec[k] = overrides[k]
        elif k in known and known[k] is not None:
            rec[k] = known[k]
        else:
            rec[k] = "__DA_DICHIARARE__"
            unfilled.append(k)

    rec["rules"] = RULES
    rec = {k: rec[k] for k in sorted(rec.keys())}
    extras = sorted(set(rec.keys()) - set(required))
    return rec, unfilled, extras, required



# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest(ledger, reference, item, overrides, verbose=True):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    ok_ledger = os.path.isfile(ledger)
    chk("1  registro presente", ok_ledger, ledger)
    if not ok_ledger:
        return _report(checks, verbose)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(ledger)

    chk("2  righe = %d" % EXPECTED_LINES_BEFORE, len(recs) == EXPECTED_LINES_BEFORE,
        "trovate %d" % len(recs))
    round_trip = json.dumps(recs[-1], ensure_ascii=pure_ascii,
                            sort_keys=True).encode("utf-8")
    chk("2b la riga %d si ri-serializza byte per byte identica" % len(recs),
        round_trip == lines[-1],
        "%d byte contro %d" % (len(round_trip), len(lines[-1])))

    ok_ref = os.path.isfile(reference)
    file_sha = sha256_file(reference) if ok_ref else ""
    chk("3  sha256 del reference invariato", file_sha == REFERENCE_FILE_SHA256,
        file_sha[:16] if file_sha else "assente")
    cited = recs[-1].get("reference_file_sha256") if recs else None
    chk("4  digest = quello citato nella riga %d" % len(recs), cited == file_sha,
        (cited or "assente")[:16])

    self_sha = ""
    if ok_ref:
        try:
            self_sha = json.load(open(reference, "r", encoding="utf-8")).get("_self_sha256", "")
        except Exception as exc:
            chk("4b _self_sha256 leggibile", False, str(exc))
    chk("5  _self_sha256 presente, atteso, e uguale a quello della riga %d" % len(recs),
        bool(self_sha) and self_sha == REFERENCE_SELF_SHA
        and self_sha == recs[-1].get("reference_self_sha256"), self_sha[:16])

    blob = raw.decode("utf-8", "replace")
    dup_item = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 43 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 42 e' presente ED e' sulla riga %d" % EXPECTED_LINES_BEFORE,
        (MARKER_42 in blob)
        and (MARKER_42 in json.dumps(recs[EXPECTED_LINES_BEFORE - 1], ensure_ascii=False)))

    n_crlf, n_lf, odd = eol_profile(terms)
    chk("7  convenzioni: ascii_puro=%s chiavi_ordinate=%s; fine riga CRLF=%d LF=%d"
        % (pure_ascii, sorted_keys, n_crlf, n_lf), True,
        ("righe fuori maggioranza: %s - preesistente" % odd) if odd else "uniformi")
    chk("7b l'ultima riga segue la maggioranza",
        terms[-1] == (b"\r\n" if n_crlf >= n_lf else b"\n"), "ultima=%r" % terms[-1])

    G = analyse_gates()

    bad = []
    p = G["D-T1"]["params"]
    if not p["exists"] or p["sha256"] != PARAMS_SHA:
        bad.append("params sha=%s" % (p["sha256"] or "assente"))
    if p["exists"] and p["bytes"] != PARAMS_BYTES:
        bad.append("params byte=%s" % p["bytes"])
    for region, (path, sha, size) in sorted(NH1.items()):
        g = G["D-T1"]["nh1_" + region]
        if not g["exists"] or g["sha256"] != sha:
            bad.append("nh1 %s sha" % region)
        if g["exists"] and g["bytes"] != size:
            bad.append("nh1 %s byte=%s" % (region, g["bytes"]))
    chk("M1 D-T1: i digest degli ingressi sono quelli dichiarati", not bad,
        ",".join(bad) if bad else "tre file, digest e dimensione")

    chk("M5 il percorso del manifest NON risolve: il difetto registrato e' vero",
        not G["D-T1"]["manifest_path_resolves"], MANIFEST_BAD_PATH)

    bad2, bad3, bad4 = [], [], []
    for region in ("NGC", "SGC"):
        d = G["D-T2"][region]
        if not d.get("both_present"):
            bad3.append("%s: manca un registro" % region)
            continue
        if not d.get("identical"):
            bad3.append("%s: r_partial diversi" % region)
        if not d.get("matches_checklist_4dp"):
            bad3.append("%s: r_partial != checklist D2 a 4 decimali" % region)
        if not d.get("fields_equal"):
            bad3.append("%s: r2/attenuation/config_hash diversi" % region)
        if d.get("repro_params_sha256") != PARAMS_SHA:
            bad2.append("%s: params_sha256 depositato = %r" % (region, d.get("repro_params_sha256")))
        if d.get("repro_nh1_sha256") != NH1[region][1]:
            bad2.append("%s: nh1_sha256 depositato" % region)
        if d.get("names_source") != NAMES_SOURCE:
            bad4.append("%s: names_source=%r" % (region, d.get("names_source")))
        sc = d.get("infer_score_max")
        if sc is None or sc > INFER_SCORE_THRESHOLD:
            bad4.append("%s: punteggio %r oltre soglia %r" % (region, sc, INFER_SCORE_THRESHOLD))
        if sc != INFER_SCORE_OBSERVED:
            bad4.append("%s: punteggio %r != osservato dichiarato %r"
                        % (region, sc, INFER_SCORE_OBSERVED))
    chk("M2 i record dt2 depositano i digest degli ingressi (assente FALLISCE)", not bad2,
        ",".join(bad2) if bad2 else "quattro digest")
    chk("M3 D-T2: le quattordici correlazioni parziali sono identiche e sono "
        "quelle citate nel record", not bad3,
        ",".join(bad3) if bad3 else "due emisferi, sette parametri")
    chk("M4 D-T3: names_source e punteggio sotto la soglia dichiarata", not bad4,
        ",".join(bad4) if bad4 else "soglia %.3g, osservato %.6g"
        % (INFER_SCORE_THRESHOLD, INFER_SCORE_OBSERVED))

    rec = None
    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha, self_sha,
                                                       item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 40-42 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 old_value nomina il percorso che non risolve e il config_hash",
            ("resolves to NO FILE" in rec["old_value"])
            and ("not the bytes" in rec["old_value"]))
        chk("11 il record NON rivendica cio' che infer_names gia' faceva",
            ("ALREADY defended" in rec["new_value"]["D_T3_the_label_gates"]
                ["what_it_does_not_claim"])
            and ("not claimed as new" in rec["new_value"]["D_T3_the_label_gates"]
                 ["what_it_does_not_claim"]))
        chk("12 la soglia e' dichiarata prima e il margine e' quotato come MISURATO",
            ("before the run" in json.dumps(rec["new_value"]["D_T3_the_label_gates"]))
            and ("9.5x" in rec["new_value"]["D_T3_the_label_gates"]
                 ["and_it_held_with_a_measured_margin"]))
        ex = G["D-T2"]["NGC"].get("r_exact") or {}
        chk("12b i numeri esatti nel record sono DERIVATI dal registro, non trascritti",
            bool(ex) and all(repr(v) in rec["evidence"] for v in ex.values())
            and "NOT transcribed" in rec["evidence"],
            "sette valori NGC" if ex else "registro assente")
        chk("13 la riproduzione porta anche la SMENTITA",
            "+0.0549" in rec["new_value"]["D_T2_the_reproduction"]
            ["it_reproduced_the_falsification_too"])
        chk("13a l'ordine forzato D-T3 -> D-T2 e' dichiarato con la sua ragione",
            "share" in rec["new_value"]["D_T2_the_reproduction"]["the_order_was_forced"])
        chk("13b la distinzione per il referee e' esplicita",
            ("A POSTERIORI BY REPRODUCTION" in rec["new_value"]["the_verdict"]
                ["and_the_distinction_that_goes_to_the_referee"])
            and ("bit-identical" in rec["new_value"]["the_verdict"]
                 ["and_the_distinction_that_goes_to_the_referee"]))
        chk("13c il difetto dello strumento di verifica e' registrato",
            "absence and correctness" in rec["new_value"]
            ["a_defect_in_the_checking_tool_itself"]["what"])
        chk("13d config_hash NON e' ridefinito",
            "two meanings" in rec["new_value"]["D_T1_digests_now_registered"]
            ["config_hash_is_left_alone"])
        chk("13e nulla scritto nei registri canonici",
            "writes nothing to the canonical compD registers"
            in rec["new_value"]["what_this_does_not_do"])
        chk("13f lingua del record: inglese come le righe 40-42",
            ("perche'" not in txt) and ("cancelli" not in txt) and ("emisferi" not in txt))
        chk("13g document ereditato dalla riga %d" % len(recs),
            rec["document"] == recs[-1].get("document"), str(rec["document"])[:48])
        chk("13h numbering_rule cita il record %d" % (len(recs) + 1),
            (str(len(recs) + 1) in str(rec.get("numbering_rule")))
            and ("record %d." % len(recs) not in str(rec.get("numbering_rule"))),
            str(rec.get("numbering_rule"))[-40:])
    else:
        for n in ("8  schema", "9  serializzazione", "10 old_value", "11 rivendicazioni",
                  "12 soglia", "13 riproduzione"):
            chk(n, False, "manca --item")

    return _report(checks, verbose)

def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend42 rev.1 ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        if verbose:
            print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                                   ("   <- " + detail) if detail else ""))
    if verbose:
        print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def parse_overrides(items):
    ov = {}
    for it in (items or []):
        if "=" not in it:
            fail("--set richiede chiave=valore, ricevuto %r" % it)
        k, v = it.split("=", 1)
        ov[k] = None if v == "null" else v
    return ov




def cmd_gates(args):
    G = analyse_gates()
    print("=== D-T1  digest degli ingressi ===")
    p = G["D-T1"]["params"]
    print("  parametri : %s" % ("OK" if p["sha256"] == PARAMS_SHA else "DIVERSO/ASSENTE"))
    print("      %s" % (p["sha256"] or "assente"))
    print("      %d byte" % p["bytes"] if p["bytes"] else "      assente")
    for region in ("NGC", "SGC"):
        g = G["D-T1"]["nh1_" + region]
        print("  N_H1 %s  : %s   %s" % (region,
              "OK" if g["sha256"] == NH1[region][1] else "DIVERSO/ASSENTE",
              (g["sha256"] or "assente")[:32] + "..."))
    print("  percorso del manifest (riga 8043) risolve: %s   <- deve essere False"
          % G["D-T1"]["manifest_path_resolves"])
    print("")
    print("=== D-T3  etichette ===")
    for region in ("NGC", "SGC"):
        d = G["D-T3"][region]
        print("  %s  names_source=%r  punteggio max=%r  soglia=%r"
              % (region, d["names_source"], d["infer_score_max"], d["threshold"]))
    print("")
    print("=== D-T2  riproduzione ===")
    for region in ("NGC", "SGC"):
        d = G["D-T2"][region]
        if not d.get("both_present"):
            print("  %s  manca un registro" % region)
            continue
        print("  %s  r_partial identiche: %s   uguali alla checklist D2 (4 dec): %s   "
              "altri campi: %s" % (region, d["identical"], d["matches_checklist_4dp"],
                                   d["fields_equal"]))
    return 0


def cmd_inspect(args):
    if not os.path.isfile(args.ledger):
        fail("registro assente: %s" % args.ledger)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    print("registro        : %s" % args.ledger)
    print("righe           : %d" % len(recs))
    print("ascii puro      : %s   chiavi ordinate: %s" % (pure_ascii, sorted_keys))
    n_crlf, n_lf, odd = eol_profile(terms)
    print("fine riga       : CRLF=%d  LF=%d%s"
          % (n_crlf, n_lf, ("   fuori maggioranza: %s" % odd) if odd else "   uniformi"))
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("round-trip r.%-2d : %s" % (len(recs), "IDENTICO" if rt == lines[-1] else "DIVERSO"))
    if os.path.isfile(args.reference):
        fs = sha256_file(args.reference)
        print("reference file  : %s   %s"
              % (fs[:32] + "...", "OK" if fs == REFERENCE_FILE_SHA256 else "DIVERSO"))
    ck = common_keys(recs, 3)
    print("chiavi comuni 40-42 (%d): %s" % (len(ck), ck))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d  item: %r   utc: %r" % (i, r.get("item"), r.get("utc")))
    print("")
    return cmd_gates(args)


def cmd_dump(args):
    recs, _, _, _, _, _, _ = read_ledger(args.ledger)
    n = args.n
    if not (1 <= n <= len(recs)):
        fail("riga %d fuori intervallo 1..%d" % (n, len(recs)))
    print(json.dumps(recs[n - 1], ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def cmd_selftest(args):
    return 1 if selftest(args.ledger, args.reference, args.item,
                         parse_overrides(args.set)) else 0


def cmd_append(args):
    if not args.item:
        fail("--item obbligatorio: la numerazione dell'item non la deduco dal registro.")
    ov = parse_overrides(args.set)
    nfail = selftest(args.ledger, args.reference, args.item, ov)
    print("")
    if nfail:
        fail("selftest fallito (%d controlli): nessuna scrittura." % nfail)

    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    file_sha = sha256_file(args.reference)
    self_sha = json.load(open(args.reference, "r", encoding="utf-8")).get("_self_sha256", "")
    rec, unfilled, extras, required = build_record(recs, args.reference, file_sha, self_sha,
                                                   args.item, ov)
    if unfilled:
        fail("chiavi che non so riempire: %s. Usa --set chiave=valore (o =null)."
             % ", ".join(unfilled))
    if extras and not args.allow_extra_keys:
        fail("il record 43 aggiunge le chiavi %s rispetto alle comuni 40-42. "
             "Approvale con --allow-extra-keys." % ", ".join(extras))

    line = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
    print("=== RECORD %d - riga %d, %d caratteri ===" % (AMEND_POSITION, len(recs) + 1, len(line)))
    pretty = json.dumps(rec, ensure_ascii=True, indent=2, sort_keys=True)
    print(pretty if len(pretty) <= 6000 else pretty[:6000] + "\n... (troncato in stampa)")
    print("")
    if not args.apply:
        print("[DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0

    out = raw
    if out and not out.endswith(newline):
        out = out.rstrip(b"\r\n") + newline
    out = out + line.encode("utf-8") + newline
    tmp = args.ledger + ".tmp"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, args.ledger)
    print("[OK] record %d appeso a %s" % (AMEND_POSITION, args.ledger))
    return cmd_verify(args)


def cmd_verify(args):
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    fs = sha256_file(args.reference) if os.path.isfile(args.reference) else ""
    ok = True
    print("")
    print("=== VERIFY ===")
    print("  righe su disco            : %d (atteso %d)" % (len(recs), AMEND_POSITION))
    ok &= len(recs) == AMEND_POSITION
    print("  digest reference invariato: %s" % (fs == REFERENCE_FILE_SHA256))
    ok &= fs == REFERENCE_FILE_SHA256
    last = json.dumps(recs[-1], ensure_ascii=False) if recs else ""
    print("  marker nella riga %-2d      : %s" % (AMEND_POSITION, MARKER in last))
    ok &= MARKER in last
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("  round-trip della riga %-2d  : %s" % (AMEND_POSITION, rt == lines[-1]))
    ok &= rt == lines[-1]
    print("  item della riga %-2d        : %r" % (AMEND_POSITION, recs[-1].get("item")))
    G = analyse_gates()
    print("  registri canonici intatti : %s"
          % all(len(read_jsonl(COMPD[r])[0]) == 4 for r in ("NGC", "SGC")))
    print("  ingressi invariati        : %s"
          % (G["D-T1"]["params"]["sha256"] == PARAMS_SHA))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 43 - Componente D tracciata per riproduzione")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    p.add_argument("--reference", default=DEFAULT_REFERENCE)
    p.add_argument("--item", default=None, help="numerazione item, es. 3.9/componente_D")
    p.add_argument("--set", action="append", metavar="CHIAVE=VALORE")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("gates").set_defaults(func=cmd_gates)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    d = sub.add_parser("dump")
    d.add_argument("n", type=int)
    d.set_defaults(func=cmd_dump)

    ap = sub.add_parser("append")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-extra-keys", action="store_true")
    ap.set_defaults(func=cmd_append)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

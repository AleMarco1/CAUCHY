#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend36.py  (rev. 1) — Emendamento 36: la soglia di D5c e' 28, derivata
dall'effetto e non dai quantili. La deroga finisce.

Rev. 2 allinea lo script allo schema REALE del registro, letto con `inspect`:
  - la numerazione e' POSIZIONALE (nessun campo id): il record 16 e' la riga 16;
  - tre campi di digest distinti: reference_file, reference_file_sha256,
    reference_self_sha256;
  - timestamp in campo `utc`, formato ISO con offset +00:00 (non 'Z');
  - chiavi scritte in ordine alfabetico (sort_keys=True);
  - file CRLF, non-ASCII (ensure_ascii=False);
  - le chiavi extra sono la NORMA: 13 ha falsified_prediction e withdrawn,
    14 ha falsified_predictions, 15 ha rules. Il cancello di schema e' quindi
    sull'INTERSEZIONE delle ultime tre righe, non sul soprainsieme del 15.

Sottocomandi
------------
  inspect    schema, conteggio righe, digest. Non scrive.
  dump N     stampa la riga N per intero (ASCII-safe). Non scrive.
  selftest   controlli. Non scrive.
  append     costruisce e mostra il record; scrive solo con --apply.
  verify     ricontrolla il registro dopo l'append.

Cancelli d'append (bloccanti)
-----------------------------
  G1  sha256 di paper2_v1_reference.json == REFERENCE_FILE_SHA256, e uguale a
      quello citato nella riga 15;
  G2  il registro ha esattamente 15 righe prima dell'append;
  G3  idempotenza: marker assente e nessuna riga con lo stesso `item`;
  G4  schema: il record 16 contiene tutte le chiavi comuni alle righe 13-15;
  G5  --baseline-verified obbligatorio (cancello D5b);
  G6  --item obbligatorio: la numerazione dell'item non la deduco.

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

AMEND_POSITION = 36                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 35

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")

BASELINE = {
    "NGC": {"mock_mean_N_H1": 35423.575, "desi_N_H1": 31889.930},
    "SGC": {"mock_mean_N_H1": 18693.595, "desi_N_H1": 16477.565},
}

LINE_B = [0.971070, 0.985396, 1.0, 1.014889, 1.030071, 1.045531810025433]

RATIO_FALSIFY_ABOVE = 2.0
RATIO_FALSIFY_NPOINTS = 3
REALSPACE_FALSIFY_GEN = 53
D5A_TOLERANCE = 0

MARKER = "emendamento-36-soglia-d5c"
MARKER_35 = "emendamento-35-run-spazio-reale-nullo"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "d5c_threshold_declared_from_the_effect_not_from_the_quantiles"

JSON_PATH = ("amendments record 17 (gate_D5c.requirement, tolerance); "
             "amendments record 23 (the_derogation.when_it_ends); "
             "amendments record 34 (the_derogation_is_rebound_to_a_condition)")

OLD_VALUE = (
    "Record 17 sets D5c at n_clipped == 0, tolerance zero, hard stop. Record 23 suspends it to "
    "MEASURE mode because zero is unattainable, and states: 'the threshold is declared on that "
    "distribution, and applied retroactively to the same runs. Until then no result from either run "
    "is quoted.' Record 34 rebinds the derogation to a CONDITION: D5c measures for ALL runs until "
    "the threshold is declared. The warning printed by the runner still reads 'NON per un run che "
    "produce risultati', which was the wording under record 23's regime of two named runs."
)

NEW_VALUE = {
    "the_distribution_exists_now": {
        "where_it_came_from": ("The 2400 n_clipped measurements of the null real-space run, 200 "
                               "realisations x 6 points x 2 hemispheres. They are VALID despite the "
                               "run being null: n_clipped does not depend on RSD (record 35)."),
        "the_numbers": {"mean": 0.703, "median": 0, "q90": 2, "q99": 4, "q999": 7, "max": 9,
                        "fraction_zero": 0.568,
                        "NGC": {"mean": 1.006, "q99": 5, "max": 9},
                        "SGC": {"mean": 0.401, "q99": 3, "max": 5}},
        "and_it_is_flat_across_the_grid": ("Per-point means in NGC: B1 1.15, B2 1.02, B4 0.95, B5 "
                                           "0.96, B6 0.96, FID 1.00. The fiducial is in the middle, "
                                           "not at the bottom. The clipping does not depend on the "
                                           "deformation, confirming record 23 on 2400 measurements "
                                           "instead of 30."),
    },
    "why_the_threshold_is_not_taken_from_the_quantiles": {
        "the_effect_of_the_worst_case_observed": (
            "By the calibration of gate 2.2a one mask voxel is worth 34/216 = 0.1574 generators. "
            "The maximum observed, 9 clipped positions, is therefore worth at most 1.42 generators, "
            "which is 16.3 per cent of the smallest SEM (8.7). Even the worst of 2400 measurements "
            "has an effect an order of magnitude below the sampling uncertainty."),
        "so_a_quantile_threshold_would_protect_nothing": ("A threshold of 9 or 10, taken from the "
                                                          "observed tail, would fire on noise and "
                                                          "guard against something not measurable. "
                                                          "The threshold must come from the EFFECT "
                                                          "the gate exists to prevent, as record 26 "
                                                          "took its 21.2 per cent from a sampling "
                                                          "error rather than from taste."),
    },
    "the_threshold": {
        "rule": "D5c fires when n_clipped >= 28 at any point, per realisation.",
        "derivation": ("28 is the number of voxels whose effect reaches HALF the smallest SEM: "
                       "0.5 x 8.7 / 0.1574 = 27.6, rounded up. Below it the stacking is not "
                       "distinguishable from sampling noise; above it, it is."),
        "what_is_derived_and_what_is_chosen": ("DERIVED: the conversion from voxels to generators "
                                               "(0.1574 per voxel, gate 2.2a) and the comparison "
                                               "with the SEM. CHOSEN: the factor one half. The "
                                               "choice is stated as a choice and motivated below."),
    },
    "why_one_half_and_not_a_quarter_or_unity": {
        "first_argument_quadrature": (
            "A term x beside a dominant term s adds, in quadrature: +3.1 per cent at x = s/4, +5.4 "
            "per cent at s/3, +11.8 per cent at s/2, +41.4 per cent at parity. A contribution below "
            "about a third is conventionally negligible in quadrature, adding under 6 per cent. "
            "HALF is where 'negligible' stops being defensible: the gate fires exactly when the "
            "clipping would inflate the total uncertainty by about 12 per cent, and not before."),
        "second_argument_the_tail_is_heavy": (
            "Under Poisson with the observed mean 0.703, P(X >= 9) = 6.2e-08, so 1.5e-04 events "
            "expected in 2400 trials. One was observed. The distribution is therefore strongly "
            "OVER-DISPERSED and its tail is heavier than Poisson. Roughly 4000 further measurements "
            "are coming - treatment (B) and the block-A mock run - so the observed maximum will "
            "probably grow. A threshold at a quarter of the SEM sits at 13.8, only 1.5x the current "
            "maximum: it would likely fire on ordinary tail growth. Half sits at 27.6, a margin of "
            "3.1x."),
        "and_why_not_unity": ("At the full SEM the threshold is 55.3, a margin of 6.1x - but by then "
                              "the clipping would already contribute as much as the sampling error, "
                              "and would have to enter the budget as a term rather than be caught by "
                              "a gate. A gate that fires only after the quantity has become a budget "
                              "line is not a gate."),
        "the_two_arguments_are_independent_and_agree": ("One is about when the term stops being "
                                                        "negligible in quadrature; the other about "
                                                        "not firing on the tail of a heavy "
                                                        "distribution. They bracket the factor from "
                                                        "opposite sides and both point at one "
                                                        "half."),
    },
    "how_it_is_applied": {
        "retroactively_first": ("The threshold is applied to the records ALREADY written, as record "
                                "23 requires: n_clipped is in every record, in both modes, so this "
                                "is an analysis step and not a re-run. Expected exceedances: zero, "
                                "since the maximum observed is 9 against a threshold of 28."),
        "and_prospectively_after_the_current_runs": ("D5C_MODE returns to 'block' with D5C_SOGLIA = "
                                                     "28 AFTER the runs now in flight finish. The "
                                                     "runner is not edited while a run is using "
                                                     "it: the module is loaded in memory, so the "
                                                     "running process would not change, but a "
                                                     "resume would read a different file from the "
                                                     "one it started with."),
        "the_derogation_ends_here": ("Record 34 bound it to 'until the threshold is declared on the "
                                     "observed distribution'. It is declared. The condition is "
                                     "satisfied and the derogation ends when the code is changed."),
    },
    "a_stale_warning_that_contradicts_record_34": {
        "what_it_says": ("The runner prints: 'ATTENZIONE: D5c e' in modalita' measure, NON in "
                         "block. Va bene per un giro diagnostico; NON per un run che produce "
                         "risultati.'"),
        "why_it_is_wrong_now": ("That wording is from record 23's regime, where the derogation "
                                "covered two NAMED runs. Record 34 rebound it to a condition "
                                "covering ALL runs until the threshold is declared. The message "
                                "therefore alarms about something that is regular, and a warning "
                                "that cries wolf stops being read."),
        "correction": ("The message is rewritten to state the condition and to cite record 34. It "
                       "is corrected in the same patch that restores 'block', not before, because "
                       "the runner is in use."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not change the budget, and does not stop or "
                              "alter the runs in flight."),
}

REASON = (
    "The D5c threshold is declared, on the distribution record 23 required and from the effect "
    "rather than from the quantiles. "
    "THE DISTRIBUTION EXISTS. The null real-space run produced 2400 valid n_clipped measurements - "
    "valid because n_clipped does not depend on RSD - with mean 0.703, median 0, q99 4, max 9, and "
    "56.8 per cent at zero. Per-point means in NGC are 1.15, 1.02, 0.95, 0.96, 0.96 and 1.00, with "
    "the fiducial in the middle: the clipping does not depend on the deformation, now on 2400 "
    "measurements instead of 30. "
    "WHY NOT FROM THE QUANTILES. One mask voxel is worth 0.1574 generators by gate 2.2a, so the "
    "worst case observed - 9 clipped positions - is worth 1.42 generators, 16.3 per cent of the "
    "smallest SEM. A threshold taken from the observed tail would guard against something an order "
    "of magnitude below the sampling uncertainty and would fire on noise. "
    "THE THRESHOLD IS 28: the number of voxels whose effect reaches half the smallest SEM, "
    "0.5 x 8.7 / 0.1574 = 27.6. What is DERIVED is the voxel-to-generator conversion and the "
    "comparison with the SEM; what is CHOSEN is the factor one half. "
    "WHY ONE HALF, WITH TWO INDEPENDENT ARGUMENTS. In quadrature a term adds +3.1 per cent at a "
    "quarter, +5.4 at a third, +11.8 at a half and +41.4 at parity: below about a third a term is "
    "conventionally negligible, and HALF is where that stops being defensible - the gate fires "
    "exactly when the clipping would inflate the total uncertainty by about 12 per cent. And the "
    "tail is heavy: under Poisson with mean 0.703 a value of 9 has probability 6.2e-08, so 1.5e-04 "
    "expected in 2400 trials, and one was seen. With about 4000 further measurements coming the "
    "maximum will probably grow, so a threshold at a quarter - 13.8, only 1.5x the current maximum "
    "- would likely fire on ordinary tail growth, while half sits at 3.1x. Unity is rejected from "
    "the other side: at 55.3 voxels the clipping would already contribute as much as the sampling "
    "error and would have to enter the budget as a term, and a gate that fires only after that is "
    "not a gate. The two arguments bracket the factor from opposite sides and agree. "
    "APPLICATION. Retroactively first, to the records already written, since n_clipped is in every "
    "record: expected exceedances zero. Prospectively AFTER the runs in flight finish, because the "
    "runner is not edited while a run is using it. "
    "AND A STALE WARNING IS CORRECTED. The runner prints that MEASURE mode is 'NON per un run che "
    "produce risultati', wording from record 23's two-named-runs regime. Record 34 rebound the "
    "derogation to a condition covering all runs, so the message alarms about something regular, "
    "and a warning that cries wolf stops being read."
)

EVIDENCE = (
    "results/paper2/fase3_mock_realspace_NULLO.jsonl, field d5c_n_clipped: 2400 measurements, mean "
    "0.703, median 0, q90 2, q99 4, q99.9 7, max 9, 56.8 per cent zero. NGC mean 1.006, q99 5, max "
    "9; SGC mean 0.401, q99 3, max 5. Per point in NGC: B1 1.15, B2 1.02, B4 0.95, B5 0.96, B6 "
    "0.96, FID 1.00. "
    "Gate 2.2a: 216 mask voxels are worth 34 generators, hence 0.1574 generators per voxel. "
    "SEM of DDmax: 11.2, 11.6, 8.7, 9.2; the smallest is 8.7 (SGC k=1). "
    "9 x 0.1574 = 1.42 generators = 16.3 per cent of 8.7. "
    "0.5 x 8.7 / 0.1574 = 27.6, rounded to 28. Margins over the observed maximum: 1.5x at a "
    "quarter (13.8), 3.1x at a half (27.6), 6.1x at unity (55.3). "
    "Quadrature: sqrt(1 + f^2) for f = 0.25, 1/3, 0.5, 1.0 gives 1.0308, 1.0541, 1.1180, 1.4142. "
    "Poisson(0.703): P(X >= 9) = 6.15e-08, expected count in 2400 trials 1.48e-04, observed 1."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.7",
    "amends_records": [17, 23, 34],
    "the_threshold_is_28": ("n_clipped >= 28 at any point, per realisation. Blocking, once "
                            "D5C_MODE returns to 'block'."),
    "derived_from_the_effect_not_the_distribution": ("The distribution says the current clipping is "
                                                     "negligible; it does not say where the gate "
                                                     "should sit. That comes from the effect, via "
                                                     "gate 2.2a and the SEM."),
    "the_chosen_factor_is_declared_and_motivated": ("One half, with two independent arguments: "
                                                    "quadrature, where a term stops being "
                                                    "negligible; and tail margin, where a threshold "
                                                    "stops being safe from ordinary growth. They "
                                                    "bracket it from opposite sides."),
    "applied_retroactively_first": ("To the records already written, as record 23 requires. It is "
                                    "an analysis step, not a re-run."),
    "the_runner_is_not_edited_while_in_use": ("D5C_MODE returns to 'block' after the runs in flight "
                                              "finish. A resume would otherwise read a different "
                                              "file from the one the run started with."),
    "the_derogation_ends_when_the_code_changes": ("Record 34 bound it to 'until the threshold is "
                                                  "declared'. It is declared; the condition is "
                                                  "satisfied."),
    "the_warning_message_is_corrected_not_removed": ("It contradicts record 34 and alarms about "
                                                     "something regular. It is rewritten to state "
                                                     "the condition, in the same patch that "
                                                     "restores 'block'."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not stop or alter the runs in flight."),
}


# ---------------------------------------------------------------------------
# Utilita'
# ---------------------------------------------------------------------------

def fail(msg: str):
    print("[FATAL] " + msg)
    sys.exit(2)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ledger(path: str):
    with open(path, "rb") as f:
        raw = f.read()
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    lines = [ln.rstrip(b"\r") for ln in raw.split(b"\n") if ln.strip()]
    pure_ascii = all(b < 128 for b in raw)
    recs = []
    for i, ln in enumerate(lines, start=1):
        try:
            recs.append(json.loads(ln.decode("utf-8")))
        except Exception as exc:
            fail("riga %d non e' JSON valido: %s" % (i, exc))
    sorted_keys = all(list(r.keys()) == sorted(r.keys()) for r in recs)
    return recs, newline, pure_ascii, sorted_keys, raw


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def common_keys(recs, n=3):
    tail = recs[-n:] if len(recs) >= n else recs
    s = set(tail[0].keys())
    for r in tail[1:]:
        s &= set(r.keys())
    return sorted(s)


# ---------------------------------------------------------------------------
# Costruzione del record
# ---------------------------------------------------------------------------

def _renumber(rule, position):
    """La numbering_rule della riga 15 termina con 'This is record 15.': ereditarla
    verbatim scriverebbe il numero sbagliato nel record 16. Si riscrive l'ultimo
    intero della stringa con la posizione effettiva, e si fallisce se non ce n'e'
    esattamente uno da riscrivere."""
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
        "evidence": EVIDENCE,
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
        elif k in ("key", "json_path", "old_value", "new_value"):
            # emendamento di protocollo: nulli se lo sono nella riga 15
            if prev.get(k) is None:
                rec[k] = None
            else:
                rec[k] = "__DA_DICHIARARE__"
                unfilled.append(k)
        else:
            rec[k] = "__DA_DICHIARARE__"
            unfilled.append(k)

    # chiavi di contenuto, nell'idioma del registro (13: falsified_prediction,
    # 14: falsified_predictions, 15: rules)
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
    recs, newline, pure_ascii, sorted_keys, raw = read_ledger(ledger)

    chk("2  righe = %d" % EXPECTED_LINES_BEFORE, len(recs) == EXPECTED_LINES_BEFORE,
        "trovate %d" % len(recs))

    ok_ref = os.path.isfile(reference)
    file_sha = sha256_file(reference) if ok_ref else ""
    chk("3  sha256 del reference invariato", file_sha == REFERENCE_FILE_SHA256,
        file_sha[:16] if file_sha else "assente")

    cited = recs[-1].get("reference_file_sha256") if recs else None
    chk("4  digest = quello citato nella riga 15", cited == file_sha,
        (cited or "assente")[:16])

    self_sha = ""
    if ok_ref:
        try:
            self_sha = json.load(open(reference, "r", encoding="utf-8")).get("_self_sha256", "")
        except Exception as exc:
            chk("4b _self_sha256 leggibile", False, str(exc))
    chk("5  _self_sha256 presente nel reference", bool(self_sha), self_sha[:16])

    blob = raw.decode("utf-8", "replace")
    dup_item = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 36 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 35 e' gia' nel registro", MARKER_35 in blob)

    chk("7  convenzioni del file: CRLF=%s, ascii_puro=%s, chiavi_ordinate=%s"
        % (newline == b"\r\n", pure_ascii, sorted_keys), True)

    rec = None
    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha, self_sha,
                                                       item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 13-15 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 old_value cita la condizione del 23 e il messaggio del runner",
            ("applied retroactively" in rec["old_value"])
            and ("produce risultati" in rec["old_value"]))
        chk("11 la soglia e' 28 e la derivazione e' scritta",
            ("n_clipped >= 28" in rec["rules"]["the_threshold_is_28"])
            and ("0.5 x 8.7 / 0.1574" in rec["new_value"]["the_threshold"]["derivation"]))
        chk("12 derivato e scelto sono DISTINTI, non confusi",
            ("DERIVED:" in rec["new_value"]["the_threshold"]
                ["what_is_derived_and_what_is_chosen"])
            and ("CHOSEN: the factor one half" in rec["new_value"]["the_threshold"]
                 ["what_is_derived_and_what_is_chosen"]))
        chk("13 la scelta del fattore ha DUE argomenti indipendenti",
            ("first_argument_quadrature" in rec["new_value"]
                ["why_one_half_and_not_a_quarter_or_unity"])
            and ("second_argument_the_tail_is_heavy" in rec["new_value"]
                 ["why_one_half_and_not_a_quarter_or_unity"])
            and ("bracket the factor from opposite sides" in rec["new_value"]
                 ["why_one_half_and_not_a_quarter_or_unity"]
                 ["the_two_arguments_are_independent_and_agree"]))
        chk("13f il record 35 e' sulla riga 35 e si emendano 17, 23, 34",
            (MARKER_35 in json.dumps(recs[34], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [17, 23, 34])
        chk("13g anche l'UNITA' e' scartata, dall'altro lato",
            ("not a gate" in rec["new_value"]["why_one_half_and_not_a_quarter_or_unity"]
                ["and_why_not_unity"]))
        chk("13h il runner NON si tocca mentre gira, ed e' motivato",
            ("not edited while a run is using it" in rec["new_value"]["how_it_is_applied"]
                ["and_prospectively_after_the_current_runs"])
            and ("different file from the one" in rec["rules"]
                 ["the_runner_is_not_edited_while_in_use"]))
        chk("13b lingua del record: inglese come le righe 13-15",
            ("perche'" not in txt) and ("cancelli" not in txt)
            and ("emisferi" not in txt))
        chk("13c document ereditato dalla riga 15 (documento emendato, non il .md)",
            rec["document"] == recs[-1].get("document"), str(rec["document"])[:48])
        chk("13e numbering_rule cita il record %d, non il 15" % (len(recs) + 1),
            (str(len(recs) + 1) in str(rec.get("numbering_rule")))
            and ("record 15" not in str(rec.get("numbering_rule"))),
            str(rec.get("numbering_rule"))[-40:])
        chk("13d reference_self_sha256 = quello della riga 15",
            rec["reference_self_sha256"] == recs[-1].get("reference_self_sha256"),
            (rec["reference_self_sha256"] or "")[:16])
    else:
        for n in ("8  schema", "9  serializzazione", "10 soglie", "11 tolleranza",
                  "12 baseline", "13 quotazione"):
            chk(n, False, "manca --item")

    try:
        import math
        bad = []
        gv = 34.0 / 216.0
        smin = 8.7
        # 1. la soglia e' DAVVERO meta' SEM in voxel
        if abs(0.5 * smin / gv - 27.6) > 0.1:
            bad.append("derivazione")
        if rec["new_value"]["the_threshold"]["rule"].count("28") != 1:
            bad.append("soglia non 28")
        # 2. il massimo osservato vale davvero il 16% della SEM
        if abs(100 * 9 * gv / smin - 16.3) > 0.2:
            bad.append("effetto del massimo")
        # 3. i quattro incrementi in quadratura
        for f, att in ((0.25, 3.1), (1 / 3, 5.4), (0.5, 11.8), (1.0, 41.4)):
            if abs(100 * (math.sqrt(1 + f * f) - 1) - att) > 0.1:
                bad.append("quadratura %.2f" % f)
        # 4. i tre margini sul massimo osservato
        for f, att in ((0.25, 1.5), (0.5, 3.1), (1.0, 6.1)):
            if abs((f * smin / gv) / 9 - att) > 0.1:
                bad.append("margine %.2f" % f)
        # 5. e la coda e' davvero piu' pesante di Poisson: e' il secondo argomento
        lam = 0.703
        p = 1 - sum(math.exp(-lam) * lam ** k / math.factorial(k) for k in range(9))
        if not (p * 2400 < 0.01):
            bad.append("la coda non e' pesante: il secondo argomento cade")
        chk("14 aritmetica: soglia 27.6->28, effetto 16.3%%, quadratura e "
            "margini, coda %.1e attesi contro 1 osservato" % (p * 2400),
            not bad, ",".join(bad) if bad else "sedici controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend36 rev.1 ===")
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


# ---------------------------------------------------------------------------
# Sottocomandi
# ---------------------------------------------------------------------------

def parse_overrides(items):
    ov = {}
    for it in (items or []):
        if "=" not in it:
            fail("--set richiede chiave=valore, ricevuto %r" % it)
        k, v = it.split("=", 1)
        ov[k] = None if v == "null" else v
    return ov


def cmd_inspect(args):
    if not os.path.isfile(args.ledger):
        fail("registro assente: %s" % args.ledger)
    recs, newline, pure_ascii, sorted_keys, raw = read_ledger(args.ledger)
    print("registro        : %s" % args.ledger)
    print("righe           : %d" % len(recs))
    print("newline         : %s" % ("CRLF" if newline == b"\r\n" else "LF"))
    print("ascii puro      : %s" % pure_ascii)
    print("chiavi ordinate : %s" % sorted_keys)
    if os.path.isfile(args.reference):
        fs = sha256_file(args.reference)
        print("reference file  : %s" % fs)
        print("atteso          : %s   %s"
              % (REFERENCE_FILE_SHA256, "OK" if fs == REFERENCE_FILE_SHA256 else "DIVERSO"))
    print("chiavi comuni 13-15 (%d): %s" % (len(common_keys(recs, 3)), common_keys(recs, 3)))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d extra: %s" % (i, sorted(set(r.keys()) - set(common_keys(recs, 3)))))
        print("           item: %r   type: %r   utc: %r"
              % (r.get("item"), r.get("type"), r.get("utc")))
    return 0


def cmd_dump(args):
    recs, _, _, _, _ = read_ledger(args.ledger)
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

    recs, newline, pure_ascii, sorted_keys, raw = read_ledger(args.ledger)
    file_sha = sha256_file(args.reference)
    self_sha = json.load(open(args.reference, "r", encoding="utf-8")).get("_self_sha256", "")
    rec, unfilled, extras, required = build_record(recs, args.reference, file_sha, self_sha,
                                                   args.item, ov)
    if unfilled:
        fail("chiavi che non so riempire: %s. Usa --set chiave=valore (o =null)."
             % ", ".join(unfilled))
    if extras and not args.allow_extra_keys:
        fail("il record 36 aggiunge le chiavi %s rispetto alle comuni 13-15. "
             "Approvale con --allow-extra-keys (nel registro le chiavi di contenuto "
             "variano gia' riga per riga: 13 falsified_prediction+withdrawn, "
             "14 falsified_predictions, 15 rules)." % ", ".join(extras))

    line = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
    print("=== RECORD %d — riga %d, %d caratteri ===" % (AMEND_POSITION, len(recs) + 1, len(line)))
    pretty = json.dumps(rec, ensure_ascii=True, indent=2, sort_keys=True)
    print(pretty if len(pretty) <= 6000 else pretty[:6000] + "\n... (troncato in stampa)")
    print("")

    if not args.apply:
        print("[DRY-RUN] nulla scritto. Rilancia con --apply --baseline-verified --allow-extra-keys.")
        return 0
    if not args.baseline_verified:
        fail("--baseline-verified obbligatorio: conferma di aver controllato 35423.575 / "
             "31889.930 (NGC) e 18693.595 / 16477.565 (SGC) contro il registro di Fase 3. "
             "In un file append-only un numero sbagliato non si corregge, si emenda.")

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
    recs, newline, pure_ascii, sorted_keys, raw = read_ledger(args.ledger)
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
    print("  item della riga %-2d        : %r" % (AMEND_POSITION, recs[-1].get("item") if recs else None))
    print("  newline / ascii / ordine  : %s / %s / %s"
          % ("CRLF" if newline == b"\r\n" else "LF", pure_ascii, sorted_keys))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(description="Emendamento 16 - statuto del test a osservabili fisse")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    p.add_argument("--reference", default=DEFAULT_REFERENCE)
    p.add_argument("--item", default=None, help="numerazione item, es. 1.6")
    p.add_argument("--set", action="append", metavar="CHIAVE=VALORE")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    d = sub.add_parser("dump")
    d.add_argument("n", type=int)
    d.set_defaults(func=cmd_dump)

    ap = sub.add_parser("append")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-extra-keys", action="store_true")
    ap.add_argument("--baseline-verified", action="store_true")
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

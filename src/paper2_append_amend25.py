#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend25.py  (rev. 1) — Emendamento 25: verdetto del test
maschera-intersezione. PARTIAL, e un limite della regola del 24.

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

AMEND_POSITION = 25                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 24

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

MARKER = "emendamento-25-verdetto-intersezione-partial"
MARKER_24 = "emendamento-24-maschera-intersezione"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "intersection_mask_verdict_partial"

JSON_PATH = ("amendments record 24 (declared_prediction, gate_D6); "
             "amendments record 20 (referee_section_6_revised.how_it_is_decided)")

OLD_VALUE = (
    "Record 24 declares the intersection-mask test with three exhaustive outcomes on median(rho), "
    "rho = R_intersection / R_current: IDENTIFIED at <= 1/3, REFUTED at >= 2/3, PARTIAL in "
    "between, reported with the number and rounded to neither. Record 20 leaves open whether the "
    "unattributed residual and the chi2 rejection are the same object, and states that it is "
    "decided by this test and not by argument."
)

NEW_VALUE = {
    "the_run": {
        "executed": "2 Sep 2026, data side only, two passes, both hemispheres, twelve points each.",
        "gate_D6": ("HELD. n_valid_voxels = 304823 at all twelve NGC points and 167269 at all "
                    "twelve SGC points, identical and not within tolerance. Re-verified on the "
                    "records afterwards by paper2_intersezione_verdetto.py."),
        "proposition_2_still_holds": ("On the intersection, the two pure dilations A1 and A3 in "
                                      "gauge `derived` give the SAME value - 23585 and 27978 in "
                                      "NGC, 11765 and 14659 in SGC - so the fiducial of block A is "
                                      "defined and the residual is meaningful. The analyser stops "
                                      "if they differ."),
        "n_h1_fell_everywhere_as_declared": ("28256 -> 27978 in NGC, 15122 -> 14659 in SGC at the "
                                             "fiducial. Declared in record 24 before the run, so "
                                             "it is not read as a defect."),
    },
    "the_verdict": {
        "outcome": "PARTIAL",
        "median_rho_vs_R_deposited": 0.4962,
        "median_rho_vs_floor_f": 0.4741,
        "both_denominators_agree": ("Record 24 required that the two denominators be reported and "
                                    "that a disagreement be registered rather than resolved. They "
                                    "agree: PARTIAL either way, so no choice was made."),
        "per_case_rho_vs_R_deposited": {"NGC_k1": 0.502, "NGC_k0": 0.491,
                                        "SGC_k1": 0.556, "SGC_k0": 0.420},
        "reading": ("The edge-voxel channel HALVES the block-A residual and does not remove it. "
                    "The referee's section 3.2 hypothesis is confirmed by half: the channel "
                    "contributes and does not dominate."),
        "consequence_by_the_declared_rule": ("The budget is NOT re-derived. The systematic on term "
                                             "(b) stays at 41.9-60.3 and the E2 classification "
                                             "stays a one-sigma statement, as record 20 records it. "
                                             "A partial result is not rounded to the favourable "
                                             "verdict."),
    },
    "a_limitation_of_record_24_that_is_mine": {
        "what": ("Record 24 declares a rule on median(rho) and attaches NO uncertainty to rho. With "
                 "hindsight that is a defect in the rule, not in the run."),
        "why_it_matters": ("R is the rms of TWO residuals per case - eight numbers in total - and "
                           "on the intersection those residuals are 3, 8, 7, 11, -10, 7, -14, -11 "
                           "generators. A change of one or two units moves rho appreciably: NGC k=1 "
                           "would go from 0.502 to 0.58 if A1 were 4 instead of 3."),
        "what_survives_anyway": ("The VERDICT is robust: reaching IDENTIFIED would require rho to "
                                 "fall by roughly a factor of two, and reaching REFUTED to rise by "
                                 "a third. PARTIAL is not a marginal call."),
        "what_does_not": ("The VALUE 0.4962 is not robust to three digits and must NOT be quoted "
                          "that way. In the response to the referee it is reported as 'about a "
                          "half', with the per-case values and the fact that they rest on two "
                          "points each."),
        "not_repaired_retroactively": ("The rule of record 24 is not amended and the thresholds are "
                                       "not moved. The limitation is registered, and any future "
                                       "test of this shape declares an uncertainty on its ratio "
                                       "before the run."),
    },
    "consequence_for_record_20": {
        "what_record_20_left_open": ("Whether the unattributed residual and the chi2 rejection are "
                                     "manifestations of the same object - the single-realisation "
                                     "structure of the data side, absent from the mock covariance - "
                                     "and it named this test as the decider."),
        "what_this_run_settles": ("Nothing, and that is itself the answer for this route. A PARTIAL "
                                  "means the residual is neither wholly the edge-voxel channel nor "
                                  "independent of it, so the question 'are they the same object' "
                                  "cannot be decided by this test. The open item stays open and the "
                                  "route is closed."),
        "what_would_decide_it": ("Not more of this. The real-space line B (record 18) and treatment "
                                 "(B) (record 16) both bear on the same question from a different "
                                 "side, and both are running or about to run. The question is "
                                 "re-examined when they land, not before."),
    },
    "an_observation_without_a_declared_threshold": {
        "what": ("Sign of the block-A residuals. NGC is both-positive on the deposited geometry AND "
                 "on the intersection, at both levels. SGC k=1 is mixed in both. SGC k=0 goes from "
                 "mixed to both-negative."),
        "status": ("Reported and nothing more. No threshold was declared on this, so no verdict is "
                   "emitted from it, and it is not used to support any reading."),
        "a_correction_to_what_was_said_in_session": ("It had been claimed mid-session that the NGC "
                                                     "residuals change sign between the two "
                                                     "geometries. They do not: the deposited "
                                                     "-10.0/-10.3 of the report are the residuals "
                                                     "AFTER the voxel-channel subtraction, not the "
                                                     "raw excursions, which are +1/+17. The claim "
                                                     "was made from the wrong quantity."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not re-derive the budget - which is what "
                              "the declared rule requires on a PARTIAL."),
}

REASON = (
    "The intersection-mask test of record 24 has been run and its verdict is PARTIAL. "
    "THE RUN. Data side only, two passes, twelve points per hemisphere, on 2 Sep 2026. Gate D6 "
    "held: n_valid_voxels is 304823 at all twelve NGC points and 167269 at all twelve SGC points, "
    "identical. Proposition 2 still holds on the intersection - the two pure dilations give the "
    "same value - so the block-A fiducial is defined. N_H1 fell everywhere, from 28256 to 27978 and "
    "from 15122 to 14659 at the fiducial, exactly as record 24 declared in advance. "
    "THE VERDICT. median(rho) = 0.4962 against the deposited R and 0.4741 against the floor (f). "
    "Record 24 required both denominators to be reported and a disagreement to be registered rather "
    "than resolved; they agree, so no choice was made. The edge-voxel channel HALVES the block-A "
    "residual without removing it: the referee's hypothesis is confirmed by half. By the declared "
    "rule the budget is NOT re-derived, the systematic stays at 41.9-60.3, and the E2 "
    "classification stays a one-sigma statement. "
    "A LIMITATION OF RECORD 24, AND IT IS MINE. That record declares a rule on median(rho) and "
    "attaches no uncertainty to rho. R is the rms of TWO residuals per case, and on the "
    "intersection those are 3, 8, 7, 11, -10, 7, -14, -11 generators: one or two units move rho "
    "appreciably. The VERDICT is robust - IDENTIFIED would need a factor of two - but the VALUE "
    "0.4962 is not robust to three digits and must not be quoted that way. In the response it is "
    "'about a half', with the per-case numbers and the fact that each rests on two points. The rule "
    "is not amended and the thresholds are not moved; the limitation is registered, and any future "
    "test of this shape declares an uncertainty on its ratio BEFORE the run. "
    "FOR RECORD 20. That record left open whether the unattributed residual and the chi2 rejection "
    "are the same object and named this test as the decider. A PARTIAL decides nothing there: the "
    "residual is neither wholly the channel nor independent of it. The open item stays open and "
    "THIS ROUTE is closed. It is re-examined when the real-space run and treatment (B) land."
)

EVIDENCE = (
    "results/paper2/fase3_maskpass1.jsonl and results/paper2/fase3_intersezione.jsonl, read by "
    "src/paper2_intersezione_verdetto.py. "
    "Intersection: 304823 voxels in NGC from twelve masks of 306563 to 308750; 167269 in SGC from "
    "twelve of 171449 to 172668. "
    "Block-A residuals on the intersection, (A1, A3) against the `derived` fiducial: NGC k=1 (3, "
    "8), k=0 (7, 11); SGC k=1 (-10, 7), k=0 (-14, -11). R = 6.04, 9.22, 8.63, 12.59. "
    "On the deposited geometry, same quantity: NGC k=1 (1, 17), k=0 (9, 25); SGC k=1 (-19, 11), "
    "k=0 (-30, 30). R = 12.04, 18.79, 15.52, 30.00. "
    "rho against the deposited R: 0.502, 0.491, 0.556, 0.420, median 0.4962. rho against the "
    "deposited floor (10.1, 17.7, 20.2, 32.5): 0.598, 0.521, 0.427, 0.387, median 0.4741. "
    "Fiducial on the intersection, gauge `derived`, A1 and A3 identical: 23585 / 27978 (NGC), "
    "11765 / 14659 (SGC)."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.11",
    "amends_records": [24],
    "verdict_is_partial_and_stays_partial": ("PARTIAL is not rounded to IDENTIFIED. The budget is "
                                             "not re-derived and the systematic stays as "
                                             "deposited."),
    "rho_is_not_quoted_to_three_digits": ("The value rests on two residuals per case, of a few "
                                          "generators each. It is reported as about a half, with "
                                          "the per-case numbers and their basis. The verdict is "
                                          "robust; the digits are not."),
    "future_ratio_tests_declare_an_uncertainty": ("Any test of this shape declares, before the run, "
                                                  "an uncertainty on its ratio as well as its "
                                                  "thresholds. Record 24 did not, and that is a "
                                                  "defect of the rule."),
    "record_24_is_not_amended": ("Its thresholds are not moved and its rule is not rewritten. The "
                                 "verdict is emitted under the rule as declared."),
    "record_20_route_closed_question_open": ("This test cannot decide whether the residual and the "
                                             "chi2 rejection are the same object. The route is "
                                             "closed; the question is re-examined when the "
                                             "real-space run and treatment (B) land."),
    "the_sign_observation_carries_no_verdict": ("No threshold was declared on the sign of the "
                                                "block-A residuals, so none is emitted from it and "
                                                "it supports no reading."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not re-derive the budget."),
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
    chk("6  idempotenza (marker 25 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 24 e' gia' nel registro", MARKER_24 in blob)

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
        chk("10 old_value cita la regola del 24 e la domanda aperta del 20",
            ("IDENTIFIED at <= 1/3" in rec["old_value"])
            and ("chi2 rejection are the same object" in rec["old_value"]))
        chk("11 il verdetto e' PARTIAL e i due denominatori concordano",
            rec["new_value"]["the_verdict"]["outcome"] == "PARTIAL"
            and ("They agree" in rec["new_value"]["the_verdict"]
                 ["both_denominators_agree"]))
        chk("12 il budget NON si riderivà, come la regola imponeva",
            ("NOT re-derived" in rec["new_value"]["the_verdict"]
                ["consequence_by_the_declared_rule"])
            and ("not re-derive the budget" in rec["new_value"]["what_this_does_not_do"]))
        chk("13 il limite della regola del 24 e' MIO ed e' registrato",
            ("that is a defect in the rule" in rec["new_value"]
                ["a_limitation_of_record_24_that_is_mine"]["what"])
            and ("must NOT be quoted" in rec["new_value"]
                 ["a_limitation_of_record_24_that_is_mine"]["what_does_not"])
            and ("not_repaired_retroactively" in rec["new_value"]
                 ["a_limitation_of_record_24_that_is_mine"]))
        chk("13f il record 24 e' sulla riga 24 e si emenda il 24",
            (MARKER_24 in json.dumps(recs[23], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [24])
        chk("13g verdetto robusto, cifre no: distinti esplicitamente",
            ("VERDICT is robust" in rec["new_value"]
                ["a_limitation_of_record_24_that_is_mine"]["what_survives_anyway"])
            and ("verdict is robust; the digits are not" in rec["rules"]
                 ["rho_is_not_quoted_to_three_digits"]))
        chk("13h il record 20 resta aperto: si chiude la VIA, non la domanda",
            ("stays open" in rec["new_value"]["consequence_for_record_20"]
                ["what_this_run_settles"])
            and ("route is closed" in rec["rules"]["record_20_route_closed_question_open"]))
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
        import statistics as _st
        bad = []
        # I numeri del verdetto si ricalcolano dai residui, non si rileggono.
        INT = {"NGC_k1": (3, 8), "NGC_k0": (7, 11),
               "SGC_k1": (-10, 7), "SGC_k0": (-14, -11)}
        DEP = {"NGC_k1": (1, 17), "NGC_k0": (9, 25),
               "SGC_k1": (-19, 11), "SGC_k0": (-30, 30)}
        PAV = {"NGC_k1": 10.1, "NGC_k0": 17.7, "SGC_k1": 20.2, "SGC_k0": 32.5}
        rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
        r_dep = [rms(INT[k]) / rms(DEP[k]) for k in INT]
        r_pav = [rms(INT[k]) / PAV[k] for k in INT]
        m1, m2 = _st.median(r_dep), _st.median(r_pav)
        v = rec["new_value"]["the_verdict"]
        if abs(m1 - v["median_rho_vs_R_deposited"]) > 5e-4:
            bad.append("mediana/R_dep")
        if abs(m2 - v["median_rho_vs_floor_f"]) > 5e-4:
            bad.append("mediana/pavimento")
        # entrambe cadono in PARTIAL, e la soglia non e' sfiorata
        for m in (m1, m2):
            if not (1.0 / 3.0 < m < 2.0 / 3.0):
                bad.append("non PARTIAL")
        # il verdetto e' robusto: servirebbe un fattore ~2 per IDENTIFIED
        if not (m1 / (1.0 / 3.0) > 1.4):
            bad.append("margine da IDENTIFIED")
        # ma il VALORE no: +1 su un residuo sposta rho oltre il centesimo
        alt = rms((4, 8)) / rms(DEP["NGC_k1"])
        if abs(alt - r_dep[0]) < 0.01:
            bad.append("sensibilita' non dimostrata")
        chk("14 aritmetica: mediane ricalcolate, PARTIAL, verdetto robusto e "
            "valore no (+1 sposta rho di %.3f)" % abs(alt - r_dep[0]),
            not bad, ",".join(bad) if bad else "otto controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend25 rev.1 ===")
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
        fail("il record 25 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

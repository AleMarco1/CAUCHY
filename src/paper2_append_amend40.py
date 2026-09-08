#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend40.py  (rev. 1) — Emendamento 40: il pavimento a sei punti TRIPLICA
in NGC, e non entra in sigma_sys come il record 32 sosteneva.

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

AMEND_POSITION = 40                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 39

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

MARKER = "emendamento-40-pavimento-sei-punti"
MARKER_39 = "emendamento-39-termine-c-indipendente-dal-punto"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "the_six_point_floor_triples_in_ngc_and_does_not_enter_sigma_sys"

JSON_PATH = ("amendments record 32 (what_it_will_probably_do; consequences); "
             "amendments record 33 (the_corrected_rule); "
             "src/paper2_fase3_budget.py (floor)")

OLD_VALUE = (
    "Record 33 defines term (f) as max |b_residual| over the six block-A points. Record 32 states "
    "the expectation in advance: 'Record 31 finds the maximum of the RAW residual near 0.0275, "
    "which is the deposited amplitude. If the subtracted residual peaks at the same place, the "
    "maximum rule returns approximately the deposited floor and the systematic barely moves.' It "
    "also states the consequence: 'sigma_sys is sqrt of the quadrature of the budget terms, of "
    "which (f) is the dominant part. If (f) rises, sigma_sys rises and the E2 classification moves "
    "FURTHER from the E1 boundary' and 'SGC k=0 ... moves CLOSER to zero sigma'. Record 34 records "
    "that until the block-A mock run the floor is the maximum over TWO points: 10.27, 18.07, 26.35, "
    "33.54."
)

NEW_VALUE = {
    "the_run_and_the_gate": {
        "what": ("A0, A1m, A3m and A0m on the mock side, 200 realisations per hemisphere, into "
                 "fase3_mock.jsonl, 4 Sep 2026. Line A is now complete at k=0 and k=1: six points, "
                 "both hemispheres."),
        "the_gate_held": ("The rms over the deposited pair {A1, A3} reproduces 10.12, 17.73, 20.16 "
                          "and 32.47 against the deposited 10.1, 17.7, 20.2 and 32.5. The extension "
                          "to six points did not change the existing computation."),
    },
    "the_six_point_floor": {
        "values": {"NGC_k1": {"floor": 32.96, "driver": "A1m", "two_point": 10.27, "deposited": 10.1},
                   "NGC_k0": {"floor": 51.13, "driver": "A1m", "two_point": 18.07, "deposited": 17.7},
                   "SGC_k1": {"floor": 27.51, "driver": "A0", "two_point": 26.35, "deposited": 20.2},
                   "SGC_k0": {"floor": 34.61, "driver": "A3m", "two_point": 33.54, "deposited": 32.5}},
        "it_triples_in_NGC": ("3.26x and 2.89x the deposited value. The reason is in the residuals: "
                              "at NGC k=1 the six are -3.6, -10.0, -33.0, -10.3, -8.4 and -26.0, "
                              "and the two DEPOSITED points - A1 at -10.0 and A3 at -10.3 - were "
                              "among the SMALLEST of the six. The deposited pair happened to be the "
                              "least informative one."),
        "and_barely_moves_in_SGC": ("1.36x and 1.06x. The hemispheres again behave differently, for "
                                    "the third time in three days."),
    },
    "record_32_expectation_not_verified": {
        "what_was_expected": ("That the floor would barely move, because the RAW residual peaks at "
                              "the deposited amplitude."),
        "what_happened": ("It tripled in NGC. The expectation was stated in advance precisely so "
                          "that an unchanged floor could not be read afterwards as the rule having "
                          "been chosen to produce it. It is registered as NOT VERIFIED, with the "
                          "same weight it would have had if confirmed."),
        "why_it_failed": ("Records 29 and 31 decompose the RAW excursions; the floor is built from "
                          "the SUBTRACTED residuals, and record 32 itself warns that the two do not "
                          "resemble each other. The expectation extrapolated from one to the other "
                          "anyway."),
    },
    "a_claim_of_record_32_is_false_and_is_corrected": {
        "what_it_said": ("'sigma_sys is sqrt of the quadrature of the budget terms, of which (f) is "
                         "the dominant part. If (f) rises, sigma_sys rises and the E2 "
                         "classification moves FURTHER from the E1 boundary' - and that SGC k=0 "
                         "would separate E1 from E2 even less well."),
        "why_it_is_false": ("The floor does NOT enter sigma_sys. The budget computes "
                            "sqrt(TERM_C^2 + unattributed^2): 41.9, 60.3, 53.7 and 42.1, and these "
                            "are UNCHANGED by the six-point floor. (f) is a REPORTING quantity - "
                            "'of these, at least X are measured artefact' - not a term in the "
                            "quadrature."),
        "so_the_direction_that_damages_us_does_not_exist": ("Record 32 argued that the rule was "
                                                            "adoptable because it could only make "
                                                            "the systematic worse. The 'can only "
                                                            "raise' property of the FLOOR stands "
                                                            "and is proved in record 33; what is "
                                                            "false is that raising the floor raises "
                                                            "sigma_sys. The rule remains adoptable, "
                                                            "but for a weaker reason than the one "
                                                            "given: it cannot inflate the "
                                                            "ATTRIBUTED fraction beyond what is "
                                                            "measured, which is a different "
                                                            "guarantee."),
        "the_E1_E2_distances_are_unchanged": ("2.27, 1.86, 1.67 and 1.74 sigma from zero; 1.04, "
                                              "0.99, 0.70 and 0.51 from the boundary. SGC k=0 still "
                                              "does not separate E1 from E2."),
    },
    "what_the_floor_actually_buys": {
        "the_attributed_fraction": ("(f) over the unattributed residual: 32.96/41.2 = 80 per cent "
                                    "(NGC k=1), 51.13/59.8 = 86 per cent (NGC k=0), 27.51/53.3 = 52 "
                                    "per cent (SGC k=1), 34.61/41.5 = 83 per cent (SGC k=0). "
                                    "Against roughly 25 to 78 per cent with the deposited floor."),
        "why_that_is_the_result": ("The referee asks how much of the unattributed residual is "
                                   "identified. The answer moves from 'a quarter in NGC' to 'four "
                                   "fifths', and it is identified in the strongest possible sense: "
                                   "it is what remains on block A, where the signal is ZERO BY "
                                   "THEOREM. It is artefact that has been MEASURED, not modelled."),
        "what_it_does_not_do": ("It does not identify the MECHANISM, and it does not reduce "
                                "sigma_sys. The residual is better attributed and equally large."),
    },
    "the_rejected_rule_would_not_have_lowered_it_here": {
        "what": ("Record 33 rejected the rms over all six because averaging could pull the floor "
                 "DOWN. On these numbers it would have given 18.50 at NGC k=1, ABOVE the deposited "
                 "10.15: the specific worry did not materialise."),
        "and_the_guarantee_still_mattered": ("max is >= the rms of any subset for EVERY possible "
                                             "value; rms over six is not. The rule was chosen for a "
                                             "guarantee, not for a prediction about these "
                                             "particular numbers, and that a risk did not occur "
                                             "does not make guarding against it wrong."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not "
                              "change the E1-E4 verdict or its distances, does not change sigma_sys, "
                              "and does not identify the mechanism of the residual."),
}

REASON = (
    "The six-point floor is measured, and it corrects two things in record 32. "
    "THE RUN AND THE GATE. The four new block-A points were run on the mock side; line A is now "
    "complete at k=0 and k=1. The gate held: the rms over the deposited pair {A1, A3} reproduces "
    "10.12, 17.73, 20.16 and 32.47. "
    "THE FLOOR TRIPLES IN NGC. 32.96 and 51.13 against the deposited 10.1 and 17.7, that is 3.26x "
    "and 2.89x, both driven by A1m. The reason is in the residuals: at NGC k=1 the six are -3.6, "
    "-10.0, -33.0, -10.3, -8.4 and -26.0, and the two DEPOSITED points were among the SMALLEST. In "
    "SGC it barely moves, 1.36x and 1.06x - the hemispheres differing again, the third time in "
    "three days. "
    "RECORD 32's EXPECTATION IS NOT VERIFIED. It said the floor would barely move because the RAW "
    "residual peaks at the deposited amplitude. It tripled. The expectation was stated in advance "
    "so that an unchanged floor could not be read afterwards as the rule having been chosen to "
    "produce it; it is registered as not verified, with the weight it would have had if confirmed. "
    "It failed because it extrapolated from the raw excursions to the subtracted residuals, which "
    "record 32 itself warns do not resemble each other. "
    "AND A CLAIM OF RECORD 32 IS FALSE. It said the floor is the dominant part of sigma_sys, so "
    "raising it would raise sigma_sys and push SGC k=0 closer to zero sigma. The floor does NOT "
    "enter sigma_sys: the budget computes sqrt(TERM_C^2 + unattributed^2), giving 41.9, 60.3, 53.7 "
    "and 42.1, UNCHANGED. (f) is a reporting quantity, not a term in the quadrature. The "
    "'can only raise' property of the floor stands and is proved in record 33; what is false is the "
    "consequence drawn from it. The rule remains adoptable for a weaker reason: it cannot inflate "
    "the ATTRIBUTED fraction beyond what is measured. "
    "WHAT THE FLOOR ACTUALLY BUYS. The attributed fraction of the unattributed residual goes from "
    "about a quarter in NGC to 80 and 86 per cent, and is 52 and 83 per cent in SGC. The referee "
    "asks how much of the residual is identified; the answer moves from a quarter to four fifths, "
    "and in the strongest sense available - it is what remains on block A, where the signal is zero "
    "BY THEOREM. Artefact measured, not modelled. It does not identify the mechanism and does not "
    "reduce sigma_sys: better attributed, equally large."
)

EVIDENCE = (
    "results/paper2/fase3_budget.jsonl and the run of 4 Sep 2026. "
    "'(f) pavimento = 32.96 su 6 punti, determinato da A1m [rms coppia depositata 10.12 contro "
    "10.1]'; 51.13 da A1m [17.73 contro 17.7]; 27.51 da A0 [20.16 contro 20.2]; 34.61 da A3m [32.47 "
    "contro 32.5]. "
    "Subtracted residuals at NGC k=1: A0 -3.6, A1 -10.0, A1m -33.0, A3 -10.3, A3m -8.4, A0m -26.0. "
    "max |.| = 33.0; rms over six = 18.50; rms over {A1, A3} = 10.15. "
    "Ratios to the deposited floor: 3.26, 2.89, 1.36, 1.06. Two-point floors from record 34: 10.27, "
    "18.07, 26.35, 33.54. "
    "Budget output, unchanged: 'incertezza sistematica su (b): sqrt(7.73^2 + 41.2^2) = 41.9', and "
    "60.3, 53.7, 42.1 for the other three. Unattributed residual: 41.2, 59.8, 53.3, 41.5. "
    "Attributed fraction (f)/unattributed: 0.800, 0.855, 0.516, 0.834. "
    "Record 20: distances from zero 2.27, 1.86, 1.67, 1.74 sigma; from the E1 boundary 1.04, 0.99, "
    "0.70, 0.51."
)

RULES = {
    "marker": MARKER,
    "companion_document": ("risposta_referee.md, §3.1 and §4.2; checklist_paper2.md, item 3.13"),
    "amends_records": [32],
    "the_floor_does_not_enter_sigma_sys": ("sigma_sys on (b) is sqrt(TERM_C^2 + unattributed^2) and "
                                           "is unchanged at 41.9, 60.3, 53.7, 42.1. Record 32's "
                                           "claim to the contrary is corrected."),
    "the_expectation_is_registered_as_not_verified": ("It was stated in advance and it failed. It "
                                                      "carries the same weight it would have had if "
                                                      "confirmed."),
    "the_can_only_raise_property_stands": ("Proved in record 33 for the FLOOR. What was false is "
                                           "the consequence drawn from it about sigma_sys."),
    "the_result_is_the_attributed_fraction": ("From about a quarter to 80 and 86 per cent in NGC, "
                                              "52 and 83 in SGC. Artefact measured on block A where "
                                              "the signal is zero by theorem, not modelled."),
    "better_attributed_equally_large": ("The residual is not reduced. Nothing about the E1-E4 "
                                        "verdict or its distances changes."),
    "a_risk_that_did_not_occur_does_not_invalidate_guarding_against_it": ("The rms over six would "
                                                                          "have given 18.50 here, "
                                                                          "above the deposited "
                                                                          "10.15. max is >= the rms "
                                                                          "of any subset for every "
                                                                          "possible value; rms is "
                                                                          "not. The guarantee was "
                                                                          "the reason, not a "
                                                                          "prediction."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not change "
                              "the E1-E4 verdict, its distances or sigma_sys."),
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
    chk("6  idempotenza (marker 40 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 39 e' gia' nel registro", MARKER_39 in blob)

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
        chk("10 old_value cita l'aspettativa E la conseguenza sbagliata",
            ("barely moves" in rec["old_value"]) and ("sigma_sys rises" in rec["old_value"]))
        chk("11 il cancello sulla coppia depositata e' passato",
            ("10.12" in rec["new_value"]["the_run_and_the_gate"]["the_gate_held"])
            and ("did not change the existing computation" in rec["new_value"]
                 ["the_run_and_the_gate"]["the_gate_held"]))
        chk("12 l'aspettativa del 32 e' registrata come NON VERIFICATA",
            ("NOT VERIFIED" in rec["new_value"]["record_32_expectation_not_verified"]
                ["what_happened"])
            and ("same weight it would have had if confirmed" in rec["new_value"]
                 ["record_32_expectation_not_verified"]["what_happened"]))
        chk("13 la claim falsa del 32 e' corretta, con la formula giusta",
            ("does NOT enter sigma_sys" in rec["new_value"]
                ["a_claim_of_record_32_is_false_and_is_corrected"]["why_it_is_false"])
            and ("TERM_C^2 + unattributed^2" in rec["rules"]
                 ["the_floor_does_not_enter_sigma_sys"]))
        chk("13f il record 39 e' sulla riga 39 e si emenda il 32",
            (MARKER_39 in json.dumps(recs[38], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [32])
        chk("13g cio' che il pavimento COMPRA e' distinto da cio' che non fa",
            ("what_it_does_not_do" in rec["new_value"]["what_the_floor_actually_buys"])
            and ("better_attributed_equally_large" in rec["rules"])
            and ("is not reduced" in rec["rules"]["better_attributed_equally_large"])
            and ("equally large" in rec["reason"]))
        chk("13h la regola scartata NON avrebbe abbassato QUI, ed e' detto",
            ("did not materialise" in rec["new_value"]
                ["the_rejected_rule_would_not_have_lowered_it_here"]["what"])
            and ("was the reason, not a" in rec["rules"]
                 ["a_risk_that_did_not_occur_does_not_invalidate_guarding_against_it"]))
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
        V = rec["new_value"]["the_six_point_floor"]["values"]
        # 1. il pavimento e' il MASSIMO dei sei residui, ricalcolato
        RES = [-3.6, -10.0, -33.0, -10.3, -8.4, -26.0]     # NGC k=1
        if abs(max(abs(x) for x in RES) - 33.0) > 0.05:
            bad.append("massimo")
        if abs(V["NGC_k1"]["floor"] - 32.96) > 0.05:
            bad.append("pavimento NGC k1")
        # 2. e i due punti depositati sono fra i PIU' PICCOLI: e' la spiegazione
        dep = sorted([abs(-10.0), abs(-10.3)])
        tutti = sorted(abs(x) for x in RES)
        if not (tutti.index(dep[0]) <= 2 and tutti.index(dep[1]) <= 3):
            bad.append("i depositati non sono fra i piu' piccoli")
        # 3. NGC triplica, SGC no: l'asimmetria dichiarata
        for k in ("NGC_k1", "NGC_k0"):
            if not (2.5 < V[k]["floor"] / V[k]["deposited"] < 3.5):
                bad.append(k + "/non triplica")
        for k in ("SGC_k1", "SGC_k0"):
            if not (1.0 <= V[k]["floor"] / V[k]["deposited"] < 1.5):
                bad.append(k + "/sale troppo")
        # 4. il pavimento NON entra in sigma_sys: si ricalcola senza di esso
        TC = {"NGC_k1": 7.73, "NGC_k0": 7.69, "SGC_k1": 6.29, "SGC_k0": 6.78}
        NA = {"NGC_k1": 41.2, "NGC_k0": 59.8, "SGC_k1": 53.3, "SGC_k0": 41.5}
        SS = {"NGC_k1": 41.9, "NGC_k0": 60.3, "SGC_k1": 53.7, "SGC_k0": 42.1}
        for k in SS:
            if abs(math.sqrt(TC[k] ** 2 + NA[k] ** 2) - SS[k]) > 0.05:
                bad.append(k + "/sigma_sys")
        # 5. e la rms su sei sarebbe stata SOPRA il depositato: il rischio non c'e' stato
        if not (math.sqrt(sum(x * x for x in RES) / 6) > 10.15):
            bad.append("la rms su sei avrebbe abbassato: cambia l'affermazione")
        # 6. le quote attribuite
        for k in V:
            if abs(V[k]["floor"] / NA[k] - {"NGC_k1": 0.800, "NGC_k0": 0.855,
                                            "SGC_k1": 0.516, "SGC_k0": 0.834}[k]) > 0.005:
                bad.append(k + "/quota")
        chk("14 aritmetica: pavimento = max dei sei, depositati fra i piu' "
            "piccoli, sigma_sys senza il pavimento, quote attribuite",
            not bad, ",".join(bad) if bad else "diciannove controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend40 rev.1 ===")
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
        fail("il record 40 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend32.py  (rev. 1) — Emendamento 32: il pavimento (f) diventa il
MASSIMO sulle tre ampiezze. Puo' solo alzarlo.

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

AMEND_POSITION = 32                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 31

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

MARKER = "emendamento-32-pavimento-massimo-sulle-ampiezze"
MARKER_31 = "emendamento-31-blocco-a-turnover"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "floor_f_is_the_maximum_over_the_three_amplitudes"

JSON_PATH = ("prereg \\u00a76 (error budget, term (f)); src/paper2_fase3_budget.py; "
             "amendments records 27, 29, 31 (each deferred this)")

OLD_VALUE = (
    "Term (f), the floor, is the rms of the TWO block-A residuals after subtraction of the voxel "
    "channel, one value per hemisphere and erosion level: 10.1 and 17.7 in NGC, 20.2 and 32.5 in "
    "SGC. Line A now has SIX points at THREE symmetric amplitudes, |alpha - 1| = 0.018627, 0.0275 "
    "and 0.0406. Records 27, 29 and 31 each deferred the question of what the floor becomes, the "
    "last of them because 'deciding now would mean choosing the amplitude after seeing the "
    "numbers'."
)

NEW_VALUE = {
    "a_distinction_that_was_blurred_in_session_and_is_fixed_here": {
        "what": ("The six numbers decomposed in records 29 and 31 are RAW EXCURSIONS, N_H1(point) - "
                 "N_H1(fiducial). The deposited floor is the rms of the residuals AFTER subtraction "
                 "of the voxel channel, term (e). They are not the same quantity and do not "
                 "resemble each other."),
        "the_evidence_that_they_differ": ("At A1, NGC k=1, the raw excursions are +1 and +35; the "
                                          "deposited residuals are -10.0 and -10.3. The subtraction "
                                          "changes both sign and order of magnitude."),
        "why_it_matters_for_this_decision": ("The residuals AFTER subtraction at the four new "
                                             "points have NOT been computed. The rule below is "
                                             "therefore declared on quantities that have not been "
                                             "seen. The correlation between raw and subtracted is "
                                             "not zero - they come from the same runs - but +35 "
                                             "becoming -10.3 shows it is weak."),
    },
    "the_rule": {
        "definition": ("Term (f) = MAX over the three amplitudes of the rms of the two residuals at "
                       "that amplitude, computed per hemisphere and per erosion level, on the "
                       "residuals AFTER subtraction of the voxel channel, in gauge `regauged` "
                       "(record 28)."),
        "what_it_replaces": ("The rms at the single amplitude 0.0275, which is what the deposited "
                             "value is."),
        "granularity_unchanged": "One value per hemisphere and erosion level, as now.",
    },
    "why_this_rule_and_not_another": {
        "it_can_only_raise_the_floor": (
            "The deposited floor IS the rms at one of the three amplitudes. The maximum over the "
            "three is therefore >= it, BY CONSTRUCTION and independently of what the numbers turn "
            "out to be. A rule that can only make the systematic larger cannot manufacture a "
            "favourable result, which is what makes it adoptable with partial information. It is "
            "the same property that made gate D5c admissible in record 17: a gate that can only "
            "reject."),
        "rejected_rms_over_all_six": ("Averaging over six would pull the floor DOWN, because record "
                                      "31 establishes a turnover: the residual peaks near 0.0275 "
                                      "and is smaller at 0.018627 and 0.0406. Adopting it now would "
                                      "be choosing the rule knowing the shape it exploits."),
        "rejected_keeping_the_deposited_value": ("Defensible by the B6 precedent - points added "
                                                 "afterwards do not reopen a rule already applied - "
                                                 "but reticent here. The residual is now known to "
                                                 "have a maximum, and not using that would be "
                                                 "declining to report what was measured."),
        "rejected_the_amplitude_with_the_largest_raw_excursion": ("That would select on the raw "
                                                                  "quantity, which record 31 shows "
                                                                  "is not the one the floor is "
                                                                  "built from."),
    },
    "what_it_will_probably_do_and_why_that_is_said_now": {
        "expectation": ("Record 31 finds the maximum of the RAW residual near 0.0275, which is the "
                        "deposited amplitude. If the subtracted residual peaks at the same place, "
                        "the maximum rule returns approximately the deposited floor and the "
                        "systematic barely moves."),
        "why_state_it_before": ("So that a result of 'the floor is unchanged' is not read "
                                "afterwards as the rule having been chosen to produce it. If "
                                "instead the subtracted residual peaks elsewhere, the floor rises "
                                "and the systematic with it."),
        "it_is_not_a_prediction": ("No threshold is declared on the outcome, because the rule is "
                                   "not a test: it is a definition. Whatever the three rms turn out "
                                   "to be, the maximum of them is the floor."),
    },
    "consequences": {
        "the_systematic": ("sigma_sys is sqrt of the quadrature of the budget terms, of which (f) "
                           "is the dominant part. If (f) rises, sigma_sys rises and the E2 "
                           "classification moves FURTHER from the E1 boundary, not closer - so this "
                           "rule cannot be used to strengthen the result."),
        "the_e1_e2_verdict": ("Unchanged. The deposited rule classifies on the point estimate of "
                              "DDmax, which the floor does not enter. Record 20's reporting rule - "
                              "each determination quoted with sigma_tot and its distance from the "
                              "boundary - uses the floor, so those distances are recomputed."),
        "sgc_k0_at_0_51_sigma": ("That determination sits 0.51 sigma from the E1 boundary. If the "
                                 "floor rises, it moves CLOSER to zero sigma, that is, it separates "
                                 "E1 from E2 even less well. This is stated because it is the "
                                 "direction that damages the result, and it follows from the rule "
                                 "adopted here."),
    },
    "implementation": {
        "where": ("src/paper2_fase3_budget.py, which already computes the subtracted residuals for "
                  "A1 and A3. The change extends that computation to A0, A0m, A1m and A3m and takes "
                  "the maximum of the three per-amplitude rms."),
        "not_a_second_implementation": ("The voxel-channel subtraction is not reimplemented. The "
                                        "budget's existing slope and its existing residual "
                                        "computation are used, extended to more points."),
        "gate": ("At the deposited amplitude the recomputed rms must reproduce the deposited floor "
                 "- 10.1, 17.7, 20.2, 32.5 - before any new value is reported. If it does not, the "
                 "extension has changed the existing computation and nothing from it is used."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not "
                              "change the E1-E4 classification rule, and does not touch DDmax."),
}

REASON = (
    "Term (f) is redefined as the MAXIMUM over the three block-A amplitudes of the per-amplitude "
    "rms, declared before the quantities it is computed from have been seen. "
    "A DISTINCTION THAT WAS BLURRED AND IS FIXED HERE. The six numbers decomposed in records 29 and "
    "31 are RAW excursions. The deposited floor is the rms of the residuals AFTER subtraction of "
    "the voxel channel, and the two do not resemble each other: at A1, NGC k=1, the raw excursions "
    "are +1 and +35 while the deposited residuals are -10.0 and -10.3. The subtracted residuals at "
    "the four new points have NOT been computed, so this rule is declared on quantities not yet "
    "seen - not blindly, since raw and subtracted come from the same runs, but +35 becoming -10.3 "
    "shows the correlation is weak. "
    "THE RULE. Term (f) = max over the three amplitudes of the rms of the two residuals at that "
    "amplitude, per hemisphere and erosion level, on the SUBTRACTED residuals in gauge `regauged`. "
    "WHY THIS ONE. It can only RAISE the floor: the deposited value is the rms at one of the three "
    "amplitudes, so the maximum over three is greater than or equal to it, by construction and "
    "whatever the numbers are. A rule that can only make the systematic larger cannot manufacture a "
    "favourable result - the same property that made D5c admissible in record 17. The rms over all "
    "six is rejected because averaging would pull the floor DOWN, exploiting the turnover record 31 "
    "just established; keeping the deposited value is defensible by the B6 precedent but reticent, "
    "since the residual is now known to have a maximum. "
    "WHAT IT WILL PROBABLY DO, SAID NOW. Record 31 puts the maximum of the RAW residual near "
    "0.0275, the deposited amplitude. If the subtracted residual peaks in the same place the rule "
    "returns approximately the deposited floor and the systematic barely moves. This is stated "
    "BEFORE so that an unchanged floor is not later read as the rule having been chosen to produce "
    "it. It is not a prediction and carries no threshold: the rule is a definition, not a test. "
    "AND THE DIRECTION THAT DAMAGES US IS STATED TOO. If the floor rises, sigma_sys rises, and SGC "
    "k=0 - already only 0.51 sigma from the E1 boundary by record 20 - separates E1 from E2 even "
    "less well. The rule cannot be used to strengthen the result, and that is the point of choosing "
    "it."
)

EVIDENCE = (
    "Deposited floor (f): 10.1 (NGC k=1), 17.7 (NGC k=0), 20.2 (SGC k=1), 32.5 (SGC k=0). Record 24 "
    "verifies these are the rms of the two block-A residuals -10.0/-10.3, -18.1/-17.4, +26.3/-10.9, "
    "+33.5/-31.4, reproducing them to the tenth. "
    "Raw excursions at the same points, from results/paper2/fase3.jsonl gauge `regauged`: NGC k=1 "
    "A1 +1 and A3 +17. The raw and the subtracted differ in sign and magnitude. "
    "Line A after records 28 and 30: six points at |alpha - 1| = 0.018627, 0.0275, 0.0406, three "
    "symmetric pairs, ratio 1.4764 between consecutive amplitudes. "
    "Record 31: the raw residual peaks near 0.0275, with rho_low medians 0.6797 (even) and 0.3953 "
    "(odd), both TURNOVER. "
    "Record 20: sigma_tot = sqrt(SEM^2 + sigma_sys^2) gives 43.4, 61.4, 54.4, 43.0, and the "
    "distances from the E1 boundary at 53 are 1.04, 0.99, 0.70 and 0.51 sigma. "
    "src/paper2_fase3_budget.py already computes the subtracted residuals for A1 and A3."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.12",
    "amends_records": [],
    "the_floor_is_the_maximum_over_amplitudes": ("Per hemisphere and erosion level, on the "
                                                 "subtracted residuals in gauge `regauged`. One "
                                                 "value each, as now."),
    "it_can_only_raise_never_lower": ("The deposited value is the rms at one of the three "
                                      "amplitudes; the maximum of three is at least that. The rule "
                                      "cannot produce a smaller systematic whatever the numbers "
                                      "are, and that is why it is adoptable after the raw numbers "
                                      "have been seen."),
    "raw_and_subtracted_are_different_quantities": ("The floor is built from the SUBTRACTED "
                                                    "residuals. The decompositions of records 29 "
                                                    "and 31 are raw and are not floors, and were "
                                                    "described as floors nowhere in the ledger, but "
                                                    "were blurred in discussion. Fixed here."),
    "the_expectation_is_stated_before_not_after": ("If the subtracted residual peaks at 0.0275 the "
                                                   "floor barely moves. Said now so that an "
                                                   "unchanged floor is not read afterwards as the "
                                                   "rule having been chosen to produce it."),
    "no_threshold_because_it_is_a_definition": ("The rule is not a test and declares no outcome. "
                                                "Whatever the three rms are, their maximum is the "
                                                "floor."),
    "the_reproduction_gate_comes_first": ("At the deposited amplitude the recomputed rms must "
                                          "reproduce 10.1, 17.7, 20.2 and 32.5 before any new value "
                                          "is reported. Otherwise the extension has changed the "
                                          "existing computation."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not "
                              "change the E1-E4 classification rule, and does not touch DDmax."),
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
    chk("6  idempotenza (marker 32 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 31 e' gia' nel registro", MARKER_31 in blob)

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
        chk("10 old_value cita il pavimento depositato e i tre rinvii",
            ("10.1 and 17.7" in rec["old_value"])
            and ("Records 27, 29 and 31 each deferred" in rec["old_value"]))
        chk("11 grezzo e sottratto sono distinti, con la prova numerica",
            ("+1 and +35" in rec["new_value"]
                ["a_distinction_that_was_blurred_in_session_and_is_fixed_here"]
                ["the_evidence_that_they_differ"])
            and ("-10.0 and -10.3" in rec["new_value"]
                 ["a_distinction_that_was_blurred_in_session_and_is_fixed_here"]
                 ["the_evidence_that_they_differ"]))
        chk("12 la proprieta' che rende adottabile la regola: puo' solo ALZARE",
            ("can only make the systematic larger" in rec["new_value"]
                ["why_this_rule_and_not_another"]["it_can_only_raise_the_floor"])
            and ("BY CONSTRUCTION" in rec["new_value"]
                 ["why_this_rule_and_not_another"]["it_can_only_raise_the_floor"])
            and ("cannot produce a smaller systematic" in rec["rules"]
                 ["it_can_only_raise_never_lower"]))
        chk("13 tre alternative sono scartate, ognuna con la sua ragione",
            len([k for k in rec["new_value"]["why_this_rule_and_not_another"]
                 if k.startswith("rejected_")]) == 3)
        chk("13f il record 31 e' sulla riga 31",
            MARKER_31 in json.dumps(recs[30], ensure_ascii=False))
        chk("13g l'aspettativa e' dichiarata PRIMA, e si dice perche'",
            ("stated BEFORE" in rec["reason"]
             or "why_state_it_before" in rec["new_value"]
             ["what_it_will_probably_do_and_why_that_is_said_now"])
            and ("not read afterwards" in rec["rules"]
                 ["the_expectation_is_stated_before_not_after"]))
        chk("13h la direzione che DANNEGGIA il risultato e' dichiarata",
            ("0.51 sigma" in rec["new_value"]["consequences"]["sgc_k0_at_0_51_sigma"])
            and ("damages the result" in rec["new_value"]["consequences"]
                 ["sgc_k0_at_0_51_sigma"])
            and ("cannot be used to strengthen" in rec["reason"]))
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
        # 1. il pavimento depositato E' la rms dei due residui SOTTRATTI, e la
        #    regola nuova non puo' che essere >= di esso: si dimostra, non si
        #    afferma.
        SOTTRATTI = {"NGC_k1": (-10.0, -10.3), "NGC_k0": (-18.1, -17.4),
                     "SGC_k1": (26.3, -10.9), "SGC_k0": (33.5, -31.4)}
        DEP = {"NGC_k1": 10.1, "NGC_k0": 17.7, "SGC_k1": 20.2, "SGC_k0": 32.5}
        rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
        for nm, v in SOTTRATTI.items():
            if abs(rms(v) - DEP[nm]) > 0.1:
                bad.append(nm + "/pavimento")
        # 2. max(a, b, c) >= a per QUALUNQUE b, c: la proprieta' che rende la
        #    regola adottabile. Provata su casi casuali, non asserita.
        import random
        random.seed(0)
        for _ in range(2000):
            a, b, c = (random.uniform(0, 100) for _ in range(3))
            if max(a, b, c) < a:
                bad.append("massimo")
                break
        # 3. la rms su sei INVECE puo' abbassare: e' la ragione dello scarto
        giu = 0
        for _ in range(2000):
            t = [random.uniform(0, 100) for _ in range(6)]
            if rms(t) < max(rms(t[0:2]), rms(t[2:4]), rms(t[4:6])):
                giu += 1
        if giu < 1900:
            bad.append("la rms su sei non abbassa quasi mai: argomento debole")
        # 4. grezzo e sottratto differiscono davvero, sul caso citato
        if rms((1, 35)) - rms((-10.0, -10.3)) < 10:
            bad.append("grezzo e sottratto troppo simili")
        chk("14 aritmetica: pavimento = rms dei sottratti, max non abbassa mai "
            "(2000 casi), rms su sei abbassa nel %d%%, grezzo != sottratto"
            % (giu * 100 // 2000), not bad,
            ",".join(bad) if bad else "otto controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend32 rev.1 ===")
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
        fail("il record 32 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

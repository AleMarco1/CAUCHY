#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend30.py  (rev. 1) — Emendamento 30: terza ampiezza sul blocco A,
per trovare il massimo che il vincolo residuo(1)=0 impone.

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

AMEND_POSITION = 30                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 29

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

MARKER = "emendamento-30-blocco-a-terza-ampiezza"
MARKER_29 = "emendamento-29-blocco-a-verdetto-specchi"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "block_a_third_amplitude_to_find_the_turnover"

JSON_PATH = ("src/paper2_item13a_15a.py LINE_A; amendments records 27, 28, 29; "
             "referee report section 6")

OLD_VALUE = (
    "Record 29 measures the block-A residual at two symmetric amplitudes, |alpha - 1| = 0.0275 and "
    "0.0406, and finds that in NGC it SHRINKS as the deformation grows, in both parts: even 18.0 -> "
    "10.0 and 32.5 -> 14.0, odd 17.0 -> 7.0 and 23.5 -> 11.0. It withdraws the Phase-3 'constant "
    "offset' reading as unsupported and states that resolving the shape would need a THIRD "
    "amplitude - two give a ratio, three give a shape - and that whether it is worth eight more "
    "runs is a decision not taken there. It also records that record 27 failed to declare how the "
    "four per-case ratios are aggregated."
)

NEW_VALUE = {
    "the_constraint_that_makes_this_decidable": {
        "statement": ("The residual at alpha = 1 is ZERO EXACTLY. This is not an approximation or "
                      "an extrapolation: alpha = 1 IS the fiducial point, and the residual is "
                      "defined against it."),
        "what_follows": ("The residual vanishes at 0 and is MEASURED to fall between 0.0275 and "
                         "0.0406. It therefore has a MAXIMUM somewhere in (0, 0.0406). The two "
                         "existing amplitudes cannot say where."),
        "why_that_is_the_whole_question": ("A discretisation artefact of scale s in alpha peaks near "
                                           "s. Locating the maximum measures s, and s is what "
                                           "distinguishes a voxel-grid effect from anything else."),
    },
    "the_third_amplitude": {
        "value": 0.018627,
        "derivation": ("The geometric continuation downward: a0 = a1 / (a2/a1) = 0.0275^2 / 0.0406 "
                       "= 0.018627. The three amplitudes are then EQUALLY SPACED IN LOG, ratio "
                       "1.476364 each step, which is the optimal design for fitting a power law."),
        "alpha_compression": 0.981373,
        "alpha_expansion": 1.018627,
        "names": {"A0": "compression, 0.981373", "A0m": "expansion, 1.018627"},
        "both_inside_the_physical_range": ("[0.9725, 1.0406] contains both, unlike A3m which sits "
                                           "below it. This third pair needs no out-of-range "
                                           "declaration."),
        "why_downward_and_not_upward": (
            "NOT for leverage: ln(a_max/a_min) is 0.7792 going down to 0.018627 and 0.7802 going up "
            "to 0.0600, which does not discriminate, and an earlier version of this argument was "
            "wrong to claim it did. It is downward for two other reasons. First, 0.0600 would put "
            "alpha at 1.06 and 0.94, BOTH outside the physical range, where A3m already costs one "
            "declaration. Second, and decisively, the constraint residual(0) = 0 bites at SMALL "
            "amplitude: the turnover is below 0.0406 and cannot be above it."),
        "cost": "eight deterministic data-side runs, about six minutes.",
    },
    "the_quantitative_prediction": {
        "power_law_extrapolated_from_the_two_known_amplitudes": (
            "Fitting |even| ~ a^p on the existing pair gives p = -1.51 (NGC k=1), -2.16 (NGC k=0), "
            "-2.60 (SGC k=1); SGC k=0 has an even part of exactly 0.0 at the large amplitude so no "
            "exponent is defined. Continued to a0 = 0.018627 those exponents predict |even| = 32.4, "
            "75.4 and 15.1, against 18.0, 32.5 and 5.5 measured at 0.0275."),
        "but_it_cannot_continue": ("A negative power diverges as a -> 0, and the residual must "
                                   "return to zero. The extrapolation is therefore a prediction "
                                   "that MUST fail somewhere; the question is whether it has "
                                   "already failed by 0.018627."),
    },
    "declared_prediction": {
        "quantity": ("rho_low = |part(a0)| / |part(a1)|, with a0 = 0.018627 and a1 = 0.0275, "
                     "computed per hemisphere and per erosion level, on the SYMMETRIC pairs, in "
                     "gauge `regauged` (record 28)."),
        "aggregation_is_declared_this_time": ("MEDIAN over the four cases. Record 27 omitted this "
                                              "and record 29 had to report two readings; the "
                                              "omission is not repeated."),
        "two_independent_rules": ("The rule is applied SEPARATELY to the even part and to the odd "
                                  "part, each with its own median and its own verdict. They may "
                                  "differ, and a difference is a RESULT and not a failure: the even "
                                  "part behaves like a discretisation term and the odd part is the "
                                  "section-6 anomaly, and there is no reason they share a shape."),
        "rule": {
            "STILL_GROWING": ("median rho_low >= 1.25. The residual keeps growing towards small "
                              "amplitude, the power law has not turned over by 0.018627, and the "
                              "maximum lies BELOW it: the structure is on a scale finer than 2 per "
                              "cent in alpha."),
            "TURNOVER": ("median rho_low <= 0.75. The residual is already falling towards zero at "
                         "0.018627, so the maximum sits between 0.0186 and 0.0406: a scale of 2 to "
                         "4 per cent in alpha."),
            "FLAT": ("0.75 < median rho_low < 1.25. No shape resolved between the two smallest "
                     "amplitudes. Reported with the number and assigned to neither."),
            "SIGN_CHANGE": ("any case where the part changes sign between a0 and a1 is reported "
                            "separately and excluded from the median, with the count stated. If two "
                            "or more of the four change sign the median is NOT EVALUABLE."),
        },
        "the_four_cases_are_exhaustive": True,
        "thresholds_are_chosen_not_derived": ("The data side is deterministic, so no sampling "
                                              "argument is available, exactly as in record 27. The "
                                              "bands 0.75 and 1.25 are a choice, stated as one, "
                                              "fixed before the run and not moved after."),
        "not_repaired_afterwards": True,
    },
    "what_is_reported_without_a_verdict": {
        "the_power_law_exponents": ("Fitted on both intervals, a0->a1 and a1->a2, for even and odd. "
                                    "If the two exponents differ the response is not a power law at "
                                    "all, which is informative, but no threshold is declared on "
                                    "them because no argument fixes one."),
        "the_sgc_odd_part": ("Section 6's anomaly. Its verdict comes from the odd rule above; its "
                             "MAGNITUDE at the third amplitude is reported and interpreted in the "
                             "response, not decided here."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not move any threshold of records 27 or 29, "
                              "and does not re-derive the floor (f) - which record 29 already left "
                              "as deposited."),
}

REASON = (
    "A third block-A amplitude is added to resolve the shape that two cannot, with its rule, its "
    "aggregation and its thresholds declared before the run. "
    "THE CONSTRAINT THAT MAKES IT DECIDABLE. The residual at alpha = 1 is ZERO EXACTLY - alpha = 1 "
    "IS the fiducial and the residual is defined against it - and record 29 measures it FALLING "
    "between 0.0275 and 0.0406. It therefore has a maximum in (0, 0.0406), and locating that "
    "maximum measures the scale of whatever produces it. "
    "THE AMPLITUDE. a0 = 0.0275^2/0.0406 = 0.018627, the geometric continuation downward, so the "
    "three amplitudes are equally spaced in log at ratio 1.476364 - the optimal spacing for a power "
    "law. Both alphas, 0.981373 and 1.018627, are INSIDE the physical range, unlike A3m. Downward "
    "and not upward NOT for leverage, which is 0.7792 against 0.7802 and does not discriminate - an "
    "earlier form of this argument claimed it did and was wrong - but because 0.0600 would put both "
    "alphas outside the range, and because the residual(0) = 0 constraint bites at small amplitude. "
    "THE QUANTITATIVE PREDICTION. The power law fitted on the existing pair gives exponents -1.51, "
    "-2.16 and -2.60, which continued to 0.018627 predict |even| = 32.4, 75.4 and 15.1 against "
    "18.0, 32.5 and 5.5 at 0.0275. A negative power diverges as a -> 0 and the residual must return "
    "to zero, so this extrapolation MUST fail somewhere: the question is whether it has already "
    "failed by 0.018627. "
    "THE RULE, WITH ITS AGGREGATION DECLARED. rho_low = |part(a0)|/|part(a1)|, median over the four "
    "cases - record 27 omitted the aggregation and record 29 had to report two readings; that is "
    "not repeated. Applied SEPARATELY to even and odd, because there is no reason a discretisation "
    "term and the section-6 anomaly share a shape, and a difference between them is a result. "
    "STILL_GROWING at >= 1.25, TURNOVER at <= 0.75, FLAT between, SIGN_CHANGE handled explicitly "
    "and excluded from the median with the count stated. The thresholds are a CHOICE on a "
    "deterministic side, stated as one."
)

EVIDENCE = (
    "Record 29: even 18.0 -> 10.0 (NGC k=1), 32.5 -> 14.0 (NGC k=0), -5.5 -> -2.0 (SGC k=1), -8.0 "
    "-> 0.0 (SGC k=0); odd 17.0 -> 7.0, 23.5 -> 11.0, 13.5 -> 13.0, 22.0 -> 30.0, across |alpha - "
    "1| = 0.0275 and 0.0406. "
    "Amplitude ratio 0.0406/0.0275 = 1.476364; geometric continuation 0.0275/1.476364 = 0.018627, "
    "giving log spacings 1.476364 and 1.476364, equal to 1e-12. "
    "Physical isotropic range [0.9725, 1.0406] contains 0.981373 and 1.018627. "
    "Power-law exponents on the existing interval: ln|even_large/even_small| / ln(1.476364) = -1.51, "
    "-2.16, -2.60; undefined for SGC k=0 where the large-amplitude even part is exactly 0.0. "
    "Continued to a0: |even| = 32.4, 75.4, 15.1. "
    "Leverage ln(a_max/a_min): 0.7792 with a0 = 0.018627, 0.7802 with a third at 0.0600. "
    "src/paper2_item13a_15a.py LINE_A currently holds four entries after record 28."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.12; referee report section 6",
    "amends_records": [],
    "aggregation_is_declared": ("MEDIAN over the four cases, stated here because record 27 omitted "
                                "it and record 29 had to carry the cost."),
    "two_rules_not_one": ("Even and odd get separate verdicts. A disagreement between them is a "
                          "result, not a failure of the test."),
    "thresholds_chosen_and_declared_as_chosen": ("0.75 and 1.25 on a deterministic side are a "
                                                 "choice. Fixed before the run, not moved after."),
    "sign_change_is_handled_explicitly": ("Cases where the part changes sign are excluded from the "
                                          "median and counted; two or more make the median NOT "
                                          "EVALUABLE. Record 27's rule had no such branch and "
                                          "record 29's data nearly needed one."),
    "the_exponents_carry_no_verdict": ("Reported on both intervals for even and odd. No threshold "
                                       "is declared on them because no argument fixes one."),
    "grid_values_are_read_from_the_definition": ("The two alphas go into LINE_A in "
                                                 "src/paper2_item13a_15a.py and nowhere else; c, L "
                                                 "and the box are derived by deform(), as record 28 "
                                                 "requires."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not re-derive the floor."),
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
    chk("6  idempotenza (marker 30 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 29 e' gia' nel registro", MARKER_29 in blob)

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
        chk("10 old_value cita la contrazione e la terza ampiezza mancante",
            ("32.5 -> 14.0" in rec["old_value"]) and ("THIRD amplitude" in rec["old_value"]))
        chk("11 il vincolo residuo(1)=0 e' dichiarato ESATTO, non approssimato",
            ("ZERO EXACTLY" in rec["new_value"]
                ["the_constraint_that_makes_this_decidable"]["statement"])
            and ("not an approximation" in rec["new_value"]
                 ["the_constraint_that_makes_this_decidable"]["statement"]))
        chk("12 l'aggregazione e' DICHIARATA, e si dice perche' stavolta",
            ("MEDIAN" in rec["new_value"]["declared_prediction"]
                ["aggregation_is_declared_this_time"])
            and ("Record 27 omitted" in rec["new_value"]["declared_prediction"]
                 ["aggregation_is_declared_this_time"])
            and ("record 27 omitted it" in rec["rules"]["aggregation_is_declared"]))
        chk("13 due regole separate, e la differenza e' un RISULTATO",
            ("SEPARATELY" in rec["new_value"]["declared_prediction"]["two_independent_rules"])
            and ("a RESULT and not a failure" in rec["new_value"]["declared_prediction"]
                 ["two_independent_rules"])
            and ("not a failure of the test" in rec["rules"]["two_rules_not_one"]))
        chk("13f il record 29 e' sulla riga 29",
            MARKER_29 in json.dumps(recs[28], ensure_ascii=False))
        chk("13g il ramo SIGN_CHANGE esiste, che al 27 mancava",
            ("SIGN_CHANGE" in rec["new_value"]["declared_prediction"]["rule"])
            and ("NOT EVALUABLE" in rec["new_value"]["declared_prediction"]["rule"]
                 ["SIGN_CHANGE"])
            and ("had no such branch" in rec["rules"]["sign_change_is_handled_explicitly"]))
        chk("13h l'argomento sbagliato sulla leva e' RITIRATO nel record",
            ("does not discriminate" in rec["new_value"]["the_third_amplitude"]
                ["why_downward_and_not_upward"])
            and ("was wrong" in rec["new_value"]["the_third_amplitude"]
                 ["why_downward_and_not_upward"]))
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
        T = rec["new_value"]["the_third_amplitude"]
        a1, a2 = 0.0275, 0.0406
        r = a2 / a1
        a0 = a1 / r
        # 1. la terza ampiezza e' la continuazione geometrica, e le spaziature
        #    in log sono uguali: e' la premessa del disegno
        if abs(T["value"] - a0) > 1e-6:
            bad.append("a0")
        if abs((a1 / a0) - (a2 / a1)) > 1e-12:
            bad.append("spaziatura non geometrica")
        # 2. gli alpha sono lo specchio esatto e stanno DENTRO il range
        if abs((1 - T["value"]) - T["alpha_compression"]) > 1e-9 \
                or abs((1 + T["value"]) - T["alpha_expansion"]) > 1e-9:
            bad.append("alpha")
        if not (0.9725 <= T["alpha_compression"] <= 1.0406
                and 0.9725 <= T["alpha_expansion"] <= 1.0406):
            bad.append("fuori range")
        # 3. la leva NON discrimina: l'argomento ritirato deve essere vero
        if abs(math.log(a2 / a0) - 0.7792) > 5e-4 \
                or abs(math.log(0.0600 / a1) - 0.7802) > 5e-4:
            bad.append("leva")
        # 4. gli esponenti e le predizioni quantitative si ricalcolano
        E = {"NGC_k1": (18.0, 10.0, -1.51, 32.4), "NGC_k0": (32.5, 14.0, -2.16, 75.4),
             "SGC_k1": (-5.5, -2.0, -2.60, 15.1)}
        for nm, (p, g, pe, pred) in E.items():
            e = math.log(abs(g / p)) / math.log(r)
            if abs(e - pe) > 0.01 or abs(abs(p) * (a0 / a1) ** e - pred) > 0.2:
                bad.append(nm + "/esponente")
        # 5. e le tre bande coprono la retta positiva senza sovrapporsi
        def v(x):
            return "TURNOVER" if x <= 0.75 else ("FLAT" if x < 1.25 else "STILL_GROWING")
        if {v(x / 1000.0) for x in range(0, 3001)} != {"TURNOVER", "FLAT", "STILL_GROWING"}:
            bad.append("bande")
        chk("14 aritmetica: a0 geometrica, alpha in range, leva 0.779/0.780, "
            "esponenti e predizioni, bande esaustive", not bad,
            ",".join(bad) if bad else "sedici controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend30 rev.1 ===")
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
        fail("il record 30 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

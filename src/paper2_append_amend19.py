#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend19.py  (rev. 1) — Emendamento 19: ritiro di due
sovra-affermazioni, l'estrapolazione 61-247 e la seconda predizione di B6.

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

AMEND_POSITION = 19                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 18

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

MARKER = "emendamento-19-due-sovra-affermazioni-ritirate"
MARKER_18 = "emendamento-18-rettifica-gauge-origine"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "two_overclaims_withdrawn"

JSON_PATH = ("prereg \u00a75.4 (required F_AP); prereg \u00a75.2 (physical range of F_AP); "
             "amendments record 15 (rules.declared_prediction on B6)")

OLD_VALUE = (
    "(a) Prereg \u00a75.4 states: |F_req - 1| > 0.027 -> AP cannot explain the deficit, whatever the "
    "amplitude of the response. Executed, this produced the claim reported as the STRONGEST, "
    "MODEL-INDEPENDENT result: 'the F that would zero the deficit by extrapolating the measured "
    "slope requires dF = +6.67, +3.75, +1.92, +1.66 against a physical range |F-1| <= 0.027: from "
    "61 to 247 times outside'. "
    "(b) Record 15 declared, before the B6 run: 'if it is an artefact growing with the deformation, "
    "|residual(B6)| > |residual(B5)|; if it is noise specific to the sampled points, it stays "
    "around 45 generators. The two cases are distinguishable, and neither is to be adjusted "
    "afterwards.' The result was reported as BOTH BRANCHES REFUTED."
)

NEW_VALUE = {
    "withdrawn_a_extrapolation": {
        "status": "WITHDRAWN as a reported result; the prereg \u00a75.4 rule itself is unaffected",
        "what_is_wrong": {
            "rejected_model_family": ("The extrapolated form is the quadratic family that the same "
                                      "document declares REJECTED by the data three paragraphs "
                                      "later (chi2 between 74.6 and 149.7 against limits 9.21 and "
                                      "11.34). A verdict on the shape cannot be suspended because "
                                      "the family fails to describe the data and simultaneously a "
                                      "coefficient of that family be inverted two orders of "
                                      "magnitude out of range."),
            "own_precedent": ("M26 \u00a75.5 already retracted w0 = -294 on the ground that inverting a "
                              "slope to extrapolate is numerically meaningless, and Paper 1 \u00a74.3 "
                              "establishes as one of its four methodological results that "
                              "regression attribution fails when the anomalous point falls outside "
                              "the calibration range of the regressors. This is the same class of "
                              "error, committed a third time."),
            "nonlinearity": ("If b is significant at 7-17 sigma then within |F-1| <= 0.03 the "
                             "response is not linear, and at dF = 6.67 the quadratic term dominates "
                             "the linear one by a factor of order 5e4. The claim 'does not depend "
                             "on a factor of two' is false: it depends on a factor of "
                             "fifty thousand."),
            "denominator": ("0.027 is not the physical range: it is the SMALL side of an asymmetric "
                            "interval. The measured envelope is [0.973869, 1.040504] in the "
                            "pipeline convention and [0.961073, 1.026832] in the standard one, so "
                            "the maximum deviation is 0.0405 and 0.0389 respectively. Using 0.0389 "
                            "the ratio becomes 42-171, a 40 per cent change from the choice of "
                            "endpoint alone."),
        },
        "replacement_in_range_claim": {
            "text": ("Over the whole sampled range, INCLUDING B6, D moves by at most 172.5 "
                     "generators, that is 2.0 to 4.8 per cent of the deficit; the deficit stays "
                     "within its quoted band and the empirical rank remains 1/201 at every grid "
                     "point, in both hemispheres, at both erosion levels."),
            "per_case": {"NGC_k0": {"excursion": 159.1, "percent_of_deficit": 2.22},
                         "NGC_k1": {"excursion": 144.9, "percent_of_deficit": 2.02},
                         "SGC_k0": {"excursion": 172.5, "percent_of_deficit": 4.80},
                         "SGC_k1": {"excursion": 166.9, "percent_of_deficit": 4.65}},
            "why_these_numbers_and_not_the_referee_s": (
                "The referee proposes the same substitution but writes '<= 114 generators, that is "
                "1.4-2.5 per cent of the deficit'. Those figures are the B1-B5 excursion, computed "
                "from a document that did not contain B6. With B6 the excursion is larger and the "
                "SGC fraction is roughly double what he states. The substitution is adopted; his "
                "numbers are not."),
            "property": ("in-range, not falsifiable by extrapolation, and it does not rest on the "
                         "rejected quadratic family"),
        },
    },
    "withdrawn_b_b6_second_branch": {
        "status": "the SECOND branch is WITHDRAWN as falsified; the FIRST branch stays falsified",
        "branch_1_stays_falsified": {
            "statement": "|residual(B6)| > |residual(B5)|",
            "verdict": "FALSIFIED, and informative",
            "evidence": ("|res(B6)| < |res(B5)| in all four cases: 10.4 vs 13.4, 61.6 vs 81.4, 3.7 "
                         "vs 51.5, 25.2 vs 40.3. B6 has the longest arm, 1.14 voxels of "
                         "displacement against 0.76, and the smallest residuals."),
        },
        "branch_2_withdrawn": {
            "statement": "the residual stays around 45 generators",
            "previous_verdict": "reported as FALSIFIED",
            "corrected_verdict": ("NOT FALSIFIED, and not confirmed either: the observation is "
                                  "COMPATIBLE with the declared value and the test had no power to "
                                  "reject it."),
            "arithmetic": ("rms of the four B6 residuals = 33.7 (B5 gives 52.6). The sampling error "
                           "of an rms from n values is about rms/sqrt(2n) = 11.9 for n = 4, so 45 "
                           "lies 0.94 sigma away. The four cases are moreover NOT independent: k=0 "
                           "and k=1 are the same field at two erosion levels, so the effective n is "
                           "below 4 and the uncertainty is LARGER, not smaller."),
            "why_it_matters": ("The second branch being compatible means the residual behaves as "
                               "noise of the sampled points rather than as an artefact growing with "
                               "the deformation. That is a favourable result that was recorded as "
                               "an unfavourable one."),
        },
    },
    "the_pattern": {
        "statement": ("The two withdrawals are the same error in opposite directions. (a) "
                      "overstates a result in OUR FAVOUR; (b) overstates a falsification AGAINST "
                      "US. Both come from reporting a verdict that the evidence does not carry. "
                      "They are registered in one record so that the pattern is visible rather "
                      "than split across two."),
        "rule_adopted": ("A verdict is emitted only where the declared decision rule applies and "
                         "the test has the power to separate the cases. Where it does not, the "
                         "outcome is reported as NOT EVALUABLE, which is neither a pass nor a "
                         "failure."),
    },
}

REASON = (
    "Two overclaims withdrawn, both raised by the referee report and both verified against the "
    "frozen records before this record was written. "
    "FIRST, the extrapolation of \u00a75.4. The claim that the F which would zero the deficit lies 61 to "
    "247 times outside the physical range is withdrawn as a REPORTED RESULT. It inverts a "
    "coefficient of the quadratic family that the same analysis declares rejected by the data; it "
    "repeats an error already retracted twice in this programme, in M26 \u00a75.5 and as one of the four "
    "methodological results of Paper 1 \u00a74.3; its denominator 0.027 is the small side of an "
    "asymmetric interval whose true maximum deviation is 0.0389 in the standard convention, so the "
    "ratio moves by 40 per cent on the choice of endpoint alone; and the assertion that the "
    "conclusion does not depend on a factor of two is false, since at dF = 6.67 the quadratic term "
    "exceeds the linear one by about 5e4. It is replaced by an in-range statement that rests on no "
    "model: over the whole sampled range including B6, D moves by at most 172.5 generators, 2.0 to "
    "4.8 per cent of the deficit, and the empirical rank stays 1/201 at every point. "
    "SECOND, the B6 prediction of record 15. Its FIRST branch stays falsified and is not touched. "
    "Its SECOND branch, 'the residual stays around 45', was reported as falsified and is WITHDRAWN "
    "from that verdict: the observed rms is 33.7 with a sampling error of about 11.9 on four "
    "non-independent values, so 45 is 0.94 sigma away and the test never had the power to reject "
    "it. The corrected verdict is COMPATIBLE, which means the residual behaves as noise of the "
    "sampled points. "
    "THE TWO ARE THE SAME ERROR IN OPPOSITE DIRECTIONS: the first overstates a result in our "
    "favour, the second a falsification against us. They are registered together so that the "
    "pattern is visible."
)

EVIDENCE = (
    "results/paper2/due_lati.jsonl, latest record per region: D per point at k=0 and k=1 gives "
    "|D(B6) - D(B1)| = 159.1, 144.9, 172.5, 166.9, against deficits of 7180.7 (NGC) and 3591.0 "
    "(SGC), hence 2.22, 2.02, 4.80 and 4.65 per cent. The same records give rank 1/201 and "
    "n_mock_below_desi = 0 at every point and every level. "
    "results/paper2/item12a_cosmo.jsonl, 24 records over twelve corners in (Om, w0): the pointwise "
    "F envelope is [0.973869, 1.040504] in the pipeline convention and [0.961073, 1.026832] in the "
    "standard one, exact reciprocals; the maximum deviation is therefore 0.0405 and 0.0389, not "
    "0.027, which is the +0.0268 endpoint rounded. The corners are a CHOSEN GRID, not a posterior, "
    "and alpha_iso_weighting is 'uniform_z' in all 24 records with alpha_iso_nz_weighted null "
    "throughout. "
    "On B6: residuals -10.4, +61.6, +3.7, -25.2 give rms 33.7; the B5 residuals +13.4, +81.4, "
    "+51.5, +40.3 give 52.6. rms/sqrt(2n) = 11.9 at n = 4, so |45 - 33.7| = 11.3 is 0.94 sigma. "
    "Branch 1 is falsified in all four cases: |res(B6)| < |res(B5)| pointwise. "
    "On the rejected family: the GLS fit with the full covariance of the mean gives chi2 = 74.6, "
    "107.1, 143.0, 149.7 on 3 dof against a limit of 11.34."
)

RULES = {
    "marker": MARKER,
    "companion_document": "piano_risposta_referee_fasi0-3.md, items 0.1 and 0.5",
    "amends_records": [15],
    "prereg_rule_not_changed": ("Prereg \u00a75.4 is NOT amended. The rule 'if |F_req - 1| > 0.027 then AP "
                               "cannot explain the deficit' remains as deposited; what is withdrawn "
                               "is the REPORTING of the extrapolated factor as a result. The rule "
                               "was written for a case the data did not produce, since the response "
                               "family it presupposes is rejected."),
    "first_branch_stays_falsified": ("Record 15's first branch remains falsified and is not "
                                     "repaired. Only the second branch's VERDICT is corrected, and "
                                     "the correction moves it from 'falsified' to 'compatible', "
                                     "not to 'confirmed'."),
    "withdrawn_is_not_falsified": ("A prediction that the test had no power to reject must not be "
                                   "reported as falsified. This is the rule the referee applies to "
                                   "us in section 4.1 and it is adopted."),
    "not_evaluable_is_a_valid_outcome": ("Where a declared rule does not apply, or the test cannot "
                                         "separate the cases, the outcome is NOT EVALUABLE, which "
                                         "is neither a pass nor a failure."),
    "the_replacement_is_stronger": ("The in-range statement cannot be attacked by the objection the "
                                    "extrapolation invites. It rests on measured excursions and on "
                                    "the empirical rank, neither of which requires a response "
                                    "model."),
    "referee_numbers_not_adopted": ("The referee proposes the same substitution with '<= 114 "
                                    "generators, 1.4-2.5 per cent'. Those are the B1-B5 figures "
                                    "from a document without B6; with B6 the correct figures are "
                                    "<= 172.5 generators and 2.0-4.8 per cent."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not change any threshold, and does not "
                              "amend prereg \u00a75.4."),
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
    chk("6  idempotenza (marker 19 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 18 e' gia' nel registro", MARKER_18 in blob)

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
        chk("10 entrambe le affermazioni ritirate sono citate in old_value",
            ("61 to 247 times outside" in rec["old_value"])
            and ("stays around 45 generators" in rec["old_value"])
            and ("BOTH BRANCHES REFUTED" in rec["old_value"]))
        chk("11 il PRIMO ramo di B6 resta falsificato e non e' riparato",
            rec["new_value"]["withdrawn_b_b6_second_branch"]
               ["branch_1_stays_falsified"]["verdict"].startswith("FALSIFIED")
            and "remains falsified and is not" in rec["rules"]["first_branch_stays_falsified"])
        chk("12 la prereg 5.4 NON e' emendata: si ritira il REPORT, non la regola",
            ("is NOT amended" in rec["rules"]["prereg_rule_not_changed"])
            and ("the prereg" in rec["new_value"]["withdrawn_a_extrapolation"]["status"])
            and ("does not amend prereg" in rec["rules"]["what_this_does_not_do"]))
        chk("13 la sostituzione in-range usa i numeri CON B6, non quelli del referee",
            rec["new_value"]["withdrawn_a_extrapolation"]
               ["replacement_in_range_claim"]["per_case"]["SGC_k0"]["excursion"] == 172.5
            and "1.4-2.5 per cent" in rec["rules"]["referee_numbers_not_adopted"])
        chk("13f il record 18 e' sulla riga 18 e il 15 e' citato come emendato",
            (MARKER_18 in json.dumps(recs[17], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [15])
        chk("13g i quattro difetti dell'estrapolazione sono tutti nel record",
            set(rec["new_value"]["withdrawn_a_extrapolation"]["what_is_wrong"])
            == {"rejected_model_family", "own_precedent", "nonlinearity", "denominator"})
        chk("13h lo schema dei due errori opposti e' dichiarato",
            ("in OUR FAVOUR" in rec["new_value"]["the_pattern"]["statement"])
            and ("AGAINST" in rec["new_value"]["the_pattern"]["statement"])
            and ("NOT EVALUABLE" in rec["new_value"]["the_pattern"]["rule_adopted"]))
        chk("13b lingua del record: inglese come le righe 13-15",
            ("perche'" not in txt) and ("cancelli" not in txt) and ("emisferi" not in txt))
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
        # I numeri del record devono reggere l'aritmetica, non solo essere scritti.
        import math
        res6 = [-10.4, 61.6, 3.7, -25.2]
        res5 = [13.4, 81.4, 51.5, 40.3]
        rms6 = math.sqrt(sum(x * x for x in res6) / 4)
        rms5 = math.sqrt(sum(x * x for x in res5) / 4)
        se = rms6 / math.sqrt(8)
        sigma = abs(45.0 - rms6) / se
        ok1 = abs(rms6 - 33.7) < 0.1 and abs(rms5 - 52.6) < 0.1 and sigma < 1.0
        ok2 = all(abs(a) < abs(b) for a, b in zip(res6, res5))   # ramo 1 falsificato
        defi = {"NGC": 7180.7, "SGC": 3591.0}
        pc = rec["new_value"]["withdrawn_a_extrapolation"]["replacement_in_range_claim"]["per_case"]
        ok3 = all(abs(100.0 * v["excursion"] / defi[k.split("_")[0]]
                      - v["percent_of_deficit"]) < 0.02 for k, v in pc.items())
        chk("14 aritmetica: rms 33.7/52.6, 45 a %.2f sigma, ramo 1 falsificato, "
            "percentuali coerenti" % sigma, ok1 and ok2 and ok3,
            "rms6=%.1f rms5=%.1f se=%.1f" % (rms6, rms5, se))
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend19 rev.1 ===")
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
        fail("il record 19 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

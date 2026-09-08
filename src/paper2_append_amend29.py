#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend29.py  (rev. 1) — Emendamento 29: il dispari in SGC e' reale,
ma in NGC il residuo si CONTRAE con l'ampiezza.

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

AMEND_POSITION = 29                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 28

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

MARKER = "emendamento-29-blocco-a-verdetto-specchi"
MARKER_28 = "emendamento-28-rettifica-alpha-specchi"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "block_a_odd_survives_but_the_residual_shrinks_with_amplitude"

JSON_PATH = ("amendments record 27 (declared_prediction: rule, and the missing aggregation); "
             "referee report section 6")

OLD_VALUE = (
    "Record 27 declares the block-A even/odd test with four exhaustive outcomes on the ratio "
    "odd(large amplitude)/odd(small amplitude): STEP in [0.900, 1.100], LINEAR at >= 1.329, "
    "UNRESOLVED in between, NEITHER below 0.900 or negative. It defines the quantity 'per "
    "hemisphere and per erosion level' - four numbers - and then states the rule on 'the ratio', "
    "singular. It also declares that the even part is reported without a threshold, and that a "
    "purely quadratic discretisation artefact would give an even ratio of 2.18."
)

NEW_VALUE = {
    "the_run": {
        "executed": ("2 Sep 2026, data side, eight deterministic runs. A1m at alpha = 1.0275 and "
                     "A3m at alpha = 0.9594, both gauges, both hemispheres."),
        "wiring_check_passed": ("In gauge `derived` both new points give the fiducial exactly - "
                                "23790 / 28256 in NGC, 12011 / 15122 in SGC - so alpha_iso reaches "
                                "deform() and the points are well formed. As record 28 says, this "
                                "is algebra and not a test of the physics."),
        "the_decomposition_is_on_regauged": ("As declared in record 28. On `derived` a pure "
                                             "dilation is the identity and there is nothing to "
                                             "decompose."),
    },
    "an_incompleteness_in_record_27_that_is_mine": {
        "what": ("Record 27 defines the ratio 'per hemisphere and per erosion level', which is four "
                 "numbers, and then states the four outcomes on 'the ratio', singular. It never "
                 "says how the four are aggregated. Record 24 said 'median' explicitly; record 27 "
                 "does not."),
        "how_it_is_handled": ("The rule is declared INCOMPLETE rather than completed now. Choosing "
                              "an aggregation after seeing the numbers is choosing the reading. "
                              "BOTH are reported: the four per-case verdicts, and the median, which "
                              "is the aggregation record 24 used."),
        "they_agree_on_what_matters": ("Per case: two NEITHER, one STEP, one LINEAR. Median 0.7155: "
                                       "NEITHER. The two readings disagree on the detail and agree "
                                       "that NEITHER declared form describes the data."),
        "not_repaired_retroactively": ("Record 27's thresholds are not moved and its rule is not "
                                       "rewritten. Any future test declares its aggregation with "
                                       "its thresholds."),
    },
    "the_measured_decomposition": {
        "pairs": ("small amplitude |alpha-1| = 0.0275: A1 (compression) and A1m (expansion). Large "
                  "amplitude 0.0406: A3m (compression) and A3 (expansion). Both pairs symmetric "
                  "about 1 by construction."),
        "NGC_k1": {"small": {"comp": 1, "exp": 35, "even": 18.0, "odd": 17.0},
                   "large": {"comp": 3, "exp": 17, "even": 10.0, "odd": 7.0},
                   "odd_ratio": 0.412, "verdict": "NEITHER"},
        "NGC_k0": {"small": {"comp": 9, "exp": 56, "even": 32.5, "odd": 23.5},
                   "large": {"comp": 3, "exp": 25, "even": 14.0, "odd": 11.0},
                   "odd_ratio": 0.468, "verdict": "NEITHER"},
        "SGC_k1": {"small": {"comp": -19, "exp": 8, "even": -5.5, "odd": 13.5},
                   "large": {"comp": -15, "exp": 11, "even": -2.0, "odd": 13.0},
                   "odd_ratio": 0.963, "verdict": "STEP"},
        "SGC_k0": {"small": {"comp": -30, "exp": 14, "even": -8.0, "odd": 22.0},
                   "large": {"comp": -30, "exp": 30, "even": 0.0, "odd": 30.0},
                   "odd_ratio": 1.364, "verdict": "LINEAR"},
        "median_odd_ratio": 0.7155,
    },
    "the_referee_section_6_stands": {
        "what_he_said": ("That SGC gives an odd response where the theorem says zero disturbs him "
                         "more than anything else in the document, and that 'two points per "
                         "hemisphere: it is an observation, not a result' is too indulgent."),
        "he_is_right_and_now_it_is_isolated": (
            "The odd part in SGC survives on SYMMETRIC pairs, so it is not the artefact of "
            "asymmetric sampling that record 27 showed could fake 37 per cent of it. At k=0, large "
            "amplitude, the even part is EXACTLY ZERO and the odd part is +30: a clean odd response "
            "where Proposition 2 says the signal is zero."),
        "and_it_does_not_shrink_there": ("SGC odd goes 13.5 -> 13.0 at k=1 and 22.0 -> 30.0 at k=0. "
                                         "It holds or grows, unlike everything else measured here."),
        "what_it_is_not_yet": ("Identified. Four symmetric residuals per hemisphere do not name a "
                               "mechanism; they establish that the odd part is real and not a "
                               "sampling artefact. The referee asked for that and it is delivered; "
                               "the cause is not."),
    },
    "the_finding_nobody_predicted": {
        "what": ("In NGC the residual SHRINKS as the deformation grows, in BOTH parts. Even: 18.0 "
                 "-> 10.0 at k=1 and 32.5 -> 14.0 at k=0, ratios 0.556 and 0.431. Odd: 17.0 -> 7.0 "
                 "and 23.5 -> 11.0, ratios 0.412 and 0.468. The raw excursions say it plainly: NGC "
                 "k=0 gives +9 and +56 at |alpha-1| = 0.0275, and +3 and +25 at 0.0406."),
        "why_it_matters": ("A discretisation artefact should GROW with the deformation, and a "
                           "quadratic one by 2.18 over these amplitudes. It falls by about a half. "
                           "Neither our hypothesis nor the referee's predicted this: the Phase-3 "
                           "report called the NGC behaviour a 'constant offset', and it is neither "
                           "constant nor growing."),
        "no_threshold_was_declared_on_the_even_part": ("Record 27 says the even part is reported "
                                                       "without a threshold because no argument "
                                                       "fixed one. It is therefore REPORTED and "
                                                       "carries no verdict. It is not used to "
                                                       "support any reading, including this one."),
        "what_would_be_needed": ("A third amplitude. Two amplitudes give a ratio; three give a "
                                 "shape. Whether that is worth eight more deterministic runs is a "
                                 "decision, not a conclusion, and it is not taken here."),
    },
    "consequences": {
        "the_floor_f": ("Term (f) is currently the rms of TWO block-A residuals. There are now "
                        "four, and they do not behave as the two suggested. Whether the floor "
                        "becomes the rms of four, or of the symmetric pairs, or something else, is "
                        "a change to the budget and is NOT decided here - record 27 already said "
                        "so. The budget stands as deposited."),
        "the_e2_classification": ("Unchanged. Line A does not enter DDmax and the E1-E4 verdict is "
                                  "not reopened, as record 15 established for B6."),
        "for_the_response_to_the_referee": ("Section 6 is answered on its own terms: the odd "
                                            "response in SGC is real and isolated from the sampling "
                                            "confounder. The NGC 'constant offset' reading is "
                                            "withdrawn as unsupported, and the shrinkage is reported "
                                            "as an open observation."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not move any threshold of record 27, and "
                              "does not re-derive the floor."),
}

REASON = (
    "The block-A mirror points have been measured and the section-6 question is answered in part. "
    "AN INCOMPLETENESS IN RECORD 27, AND IT IS MINE. That record defines the odd ratio 'per "
    "hemisphere and per erosion level' - four numbers - and then states its four outcomes on 'the "
    "ratio', singular, without saying how the four are aggregated. Record 24 said median; record 27 "
    "does not. The rule is declared INCOMPLETE rather than completed after the fact, and BOTH "
    "readings are reported: per case two NEITHER, one STEP, one LINEAR; on the median, 0.7155, "
    "NEITHER. They disagree on the detail and agree that neither declared form describes the data. "
    "THE REFEREE'S SECTION 6 STANDS, AND IS NOW ISOLATED. The odd part in SGC survives on SYMMETRIC "
    "pairs, so it is not the asymmetric-sampling artefact that record 27 showed could fake 37 per "
    "cent of it. At SGC k=0, large amplitude, the even part is EXACTLY ZERO and the odd part is "
    "+30: a clean odd response where Proposition 2 says zero. And it does not shrink - 13.5 to 13.0 "
    "at k=1, 22.0 to 30.0 at k=0. What is delivered is that the odd part is REAL; the mechanism is "
    "not identified, and four residuals per hemisphere cannot name one. "
    "AND SOMETHING NOBODY PREDICTED. In NGC the residual SHRINKS as the deformation grows, in both "
    "parts: even 18.0 to 10.0 and 32.5 to 14.0, odd 17.0 to 7.0 and 23.5 to 11.0. A discretisation "
    "artefact should grow, and a quadratic one by 2.18 over these amplitudes; it falls by about a "
    "half. The Phase-3 report called the NGC behaviour a 'constant offset': it is neither constant "
    "nor growing, and that reading is withdrawn as unsupported. No threshold was declared on the "
    "even part, so this carries no verdict and supports no reading. Resolving it would need a THIRD "
    "amplitude - two give a ratio, three give a shape - and whether that is worth eight more "
    "deterministic runs is a decision, not taken here."
)

EVIDENCE = (
    "results/paper2/fase3.jsonl, gauge `regauged`, against the fiducials 23790 / 28256 (NGC) and "
    "12011 / 15122 (SGC). "
    "NGC k=1: A1 +1, A1m +35, A3m +3, A3 +17. NGC k=0: A1 +9, A1m +56, A3m +3, A3 +25. "
    "SGC k=1: A1 -19, A1m +8, A3m -15, A3 +11. SGC k=0: A1 -30, A1m +14, A3m -30, A3 +30. "
    "Symmetric pairs: small |alpha-1| = 0.0275 is (A1, A1m); large 0.0406 is (A3m, A3). "
    "even = (expansion + compression)/2, odd = (expansion - compression)/2. "
    "Odd: NGC k=1 17.0 -> 7.0 (ratio 0.412); NGC k=0 23.5 -> 11.0 (0.468); SGC k=1 13.5 -> 13.0 "
    "(0.963); SGC k=0 22.0 -> 30.0 (1.364). Median 0.7155. "
    "Even: NGC k=1 18.0 -> 10.0 (0.556); NGC k=0 32.5 -> 14.0 (0.431); SGC k=1 -5.5 -> -2.0 "
    "(0.364); SGC k=0 -8.0 -> 0.0. A quadratic discretisation would give 2.18. "
    "Gauge `derived` at both new points reproduces the fiducial exactly, which record 28 declares "
    "to be algebra rather than a gate."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.12; referee report section 6",
    "amends_records": [27],
    "the_rule_is_incomplete_and_stays_so": ("Record 27 did not declare an aggregation over the four "
                                            "cases. It is not completed after the fact: both "
                                            "readings are reported and the thresholds are not "
                                            "moved."),
    "future_rules_declare_their_aggregation": ("A rule defined per case must say how the cases "
                                               "combine, before the run. Record 24 did; record 27 "
                                               "did not."),
    "the_even_part_carries_no_verdict": ("No threshold was declared on it. The shrinkage is "
                                         "reported as an observation and supports no reading, "
                                         "including the ones this record finds interesting."),
    "the_constant_offset_reading_is_withdrawn": ("The Phase-3 report calls the NGC block-A "
                                                 "behaviour a constant offset. On symmetric pairs "
                                                 "it is neither constant nor growing. The reading "
                                                 "is withdrawn as unsupported, not replaced."),
    "sgc_odd_is_real_but_not_identified": ("Symmetric pairs remove the sampling confounder, so the "
                                           "odd response is established. Its mechanism is not, and "
                                           "four residuals cannot establish one."),
    "the_floor_is_not_re_derived": ("Term (f) stands as deposited. Whether it becomes the rms of "
                                    "four residuals is a budget change and needs its own record."),
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
    chk("6  idempotenza (marker 29 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 28 e' gia' nel registro", MARKER_28 in blob)

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
        chk("10 old_value cita la regola del 27 e la sua lacuna",
            ("on 'the ratio', singular" in rec["old_value"])
            and ("2.18" in rec["old_value"]))
        chk("11 l'incompletezza e' DICHIARATA, non colmata dopo",
            ("declared INCOMPLETE rather than completed now" in rec["new_value"]
                ["an_incompleteness_in_record_27_that_is_mine"]["how_it_is_handled"])
            and ("not completed after the fact" in rec["rules"]
                 ["the_rule_is_incomplete_and_stays_so"]))
        chk("12 entrambe le letture sono riportate, e concordano sul punto",
            (rec["new_value"]["the_measured_decomposition"]["median_odd_ratio"] == 0.7155)
            and ("NEITHER declared form" in rec["new_value"]
                 ["an_incompleteness_in_record_27_that_is_mine"]
                 ["they_agree_on_what_matters"]))
        chk("13 il §6 del referee e' confermato, e si dice cosa NON e' stabilito",
            ("He is right" in rec["new_value"]["the_referee_section_6_stands"]
                ["he_is_right_and_now_it_is_isolated"]
             or "he_is_right_and_now_it_is_isolated" in rec["new_value"]
             ["the_referee_section_6_stands"])
            and ("the mechanism is not identified" in rec["reason"]
                 or "not identified" in rec["new_value"]["the_referee_section_6_stands"]
                 ["what_it_is_not_yet"]))
        chk("13f il record 28 e' sulla riga 28 e si emenda il 27",
            (MARKER_28 in json.dumps(recs[27], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [27])
        chk("13g la contrazione e' riportata SENZA verdetto, come il 27 imponeva",
            ("No threshold was declared" in rec["rules"]["the_even_part_carries_no_verdict"])
            and ("supports no reading" in rec["rules"]["the_even_part_carries_no_verdict"])
            and ("carries no verdict" in rec["new_value"]["the_finding_nobody_predicted"]
                 ["no_threshold_was_declared_on_the_even_part"]))
        chk("13h la lettura 'offset costante' e' RITIRATA, non sostituita",
            ("withdrawn as unsupported, not replaced" in rec["rules"]
                ["the_constant_offset_reading_is_withdrawn"]))
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
        import statistics as _st
        bad = []
        FID = {"NGC_k1": 23790, "NGC_k0": 28256, "SGC_k1": 12011, "SGC_k0": 15122}
        RAW = {"NGC_k1": (23791, 23825, 23793, 23807),
               "NGC_k0": (28265, 28312, 28259, 28281),
               "SGC_k1": (11992, 12019, 11996, 12022),
               "SGC_k0": (15092, 15136, 15092, 15152)}   # A1, A1m, A3m, A3
        D = rec["new_value"]["the_measured_decomposition"]
        rap = []
        for nm, (a1, a1m, a3m, a3) in RAW.items():
            f = FID[nm]
            c1, e1, c3, e3 = a1 - f, a1m - f, a3m - f, a3 - f
            eP, oP = (e1 + c1) / 2.0, (e1 - c1) / 2.0
            eG, oG = (e3 + c3) / 2.0, (e3 - c3) / 2.0
            r = oG / oP
            rap.append(r)
            d = D[nm]
            for k, v in (("comp", c1), ("exp", e1), ("even", eP), ("odd", oP)):
                if abs(d["small"][k] - v) > 1e-9:
                    bad.append(nm + "/small/" + k)
            for k, v in (("comp", c3), ("exp", e3), ("even", eG), ("odd", oG)):
                if abs(d["large"][k] - v) > 1e-9:
                    bad.append(nm + "/large/" + k)
            if abs(d["odd_ratio"] - r) > 5e-4:
                bad.append(nm + "/ratio")
        if abs(_st.median(rap) - D["median_odd_ratio"]) > 5e-4:
            bad.append("mediana")
        # le coppie DEVONO essere simmetriche: e' la premessa del test
        if abs(abs(1.0275 - 1) - abs(0.9725 - 1)) > 1e-12 \
                or abs(abs(0.9594 - 1) - abs(1.0406 - 1)) > 1e-12:
            bad.append("coppie non simmetriche")
        # e in NGC il residuo deve DAVVERO contrarsi, altrimenti la tesi cade
        for nm in ("NGC_k1", "NGC_k0"):
            if not (abs(D[nm]["large"]["even"]) < abs(D[nm]["small"]["even"])
                    and abs(D[nm]["large"]["odd"]) < abs(D[nm]["small"]["odd"])):
                bad.append(nm + "/non si contrae")
        chk("14 aritmetica: pari e dispari ricalcolati dai grezzi, mediana, "
            "simmetria, contrazione NGC", not bad,
            ",".join(bad) if bad else "trentacinque controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend29 rev.1 ===")
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
        fail("il record 29 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

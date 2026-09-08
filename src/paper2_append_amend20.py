#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend20.py  (rev. 1) — Emendamento 20: il sistematico entra
negli intervalli; due denominatori per due domande diverse.

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

AMEND_POSITION = 20                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 19

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

MARKER = "emendamento-20-sistematico-nell-intervallo-due-denominatori"
MARKER_19 = "emendamento-19-due-sovra-affermazioni-ritirate"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "systematic_inside_the_interval_and_the_two_denominators"

JSON_PATH = ("prereg \u00a75.2 (thresholds); prereg \u00a75.3 (the four outcomes); "
             "prereg \u00a76 (error budget)")

OLD_VALUE = (
    "The Phase-3 result is reported as: 'Four independent measures, all E2, with confidence "
    "intervals excluding zero.' Those intervals are percentile bootstrap over 4000 resamplings of "
    "the REALISATIONS and therefore contain only the mock-side sampling noise, quantified by the "
    "SEM (11.2, 11.6, 8.7, 9.2). They do NOT contain the systematic uncertainty on term (b), "
    "declared separately as 41.9, 60.3, 53.7 and 42.0 generators and dominated by the unattributed "
    "residual. The E1/E2 classification is stated without reference to the distance from the "
    "boundary."
)

NEW_VALUE = {
    "accepted_the_systematic_enters_the_interval": {
        "combination": "sigma_tot = sqrt(SEM^2 + sigma_sys^2), added in quadrature",
        "per_case": {
            "NGC_k1": {"DDmax": -98.3, "sem": 11.2, "sys": 41.9, "sigma_tot": 43.4,
                       "sigma_from_zero": 2.27, "sigma_from_E1_boundary": 1.04},
            "NGC_k0": {"DDmax": -114.0, "sem": 11.6, "sys": 60.3, "sigma_tot": 61.4,
                       "sigma_from_zero": 1.86, "sigma_from_E1_boundary": 0.99},
            "SGC_k1": {"DDmax": -91.1, "sem": 8.7, "sys": 53.7, "sigma_tot": 54.4,
                       "sigma_from_zero": 1.67, "sigma_from_E1_boundary": 0.70},
            "SGC_k0": {"DDmax": -75.0, "sem": 9.2, "sys": 42.0, "sigma_tot": 43.0,
                       "sigma_from_zero": 1.74, "sigma_from_E1_boundary": 0.51},
        },
        "consequence": ("No determination exceeds 2.3 sigma from zero once the systematic is "
                        "included, and none is more than about 1 sigma from the E1/E2 boundary. "
                        "E2 is a ONE-SIGMA STATEMENT and must be written as such."),
        "sgc_k0_declared": ("SGC k=0 sits 0.51 sigma from the boundary: that determination DOES NOT "
                            "SEPARATE E1 from E2. Presenting the four as a compact block of E2 "
                            "hides that one of them is a coin flip. It is declared here."),
    },
    "verdict_unchanged_reporting_changed": {
        "rule_is_deterministic": ("The deposited rule classifies on the POINT ESTIMATE: DDmax >= 53 "
                                  "gives E2. 75.0 >= 53, so SGC k=0 is E2 and the rule was applied "
                                  "correctly. Nothing about the verdict is reopened."),
        "what_changes": ("The REPORTING. Each determination is quoted with sigma_tot and with its "
                         "distance from the boundary, and the four are not presented as a compact "
                         "block."),
    },
    "two_denominators_two_questions": {
        "why": ("The deposited SEM answers one question and there is a second question, physically "
                "more interesting, that no reported error answers. Both are now reported, each "
                "labelled with the question it answers. Neither replaces the other."),
        "question_A": {
            "text": "Does D move when the fiducial changes?",
            "denominator": "SEM of the paired mean, the deposited one",
            "result_in_sigma": {"NGC_k1": 8.8, "NGC_k0": 9.8, "SGC_k1": 10.5, "SGC_k0": 8.2},
            "status": "the deposited denominator is correct FOR THIS QUESTION",
        },
        "question_B": {
            "text": ("Does the OBSERVED field respond to AP anomalously, compared with how a single "
                     "mock realisation responds?"),
            "denominator": ("dispersion of the 200 per-realisation slopes times the line-B "
                            "baseline dF = 0.059001: 111.9, 108.7, 89.7, 86.5 generators"),
            "result_in_sigma": {"NGC_k1": 0.90, "NGC_k0": 1.02, "SGC_k1": 1.05, "SGC_k0": 0.84},
            "reading": ("The observed excursion is entirely typical of a single realisation. The "
                        "observed field does NOT respond anomalously to a change of fiducial. This "
                        "is favourable to the programme's conclusion and it is in no reported "
                        "error bar."),
            "status": ("this is the crack the referee identifies in his answer 2, and it is "
                       "measured rather than argued"),
        },
        "not_to_be_conflated": ("Quoting 8-10 sigma without saying which question it answers "
                                "overstates; quoting 0.9 sigma without saying the same understates. "
                                "Both go in, both labelled."),
    },
    "multiplicative_reading_not_adopted": {
        "observation": ("The ratio sigma_sys / |DDmax| is 0.426, 0.529, 0.589, 0.560 in the four "
                        "cases: nearly constant."),
        "referee_inference": ("that a constant fraction indicates a MULTIPLICATIVE model error "
                              "rather than an additive nuisance, and that adding it in quadrature "
                              "is the wrong treatment"),
        "why_not_adopted": ("The four numbers are NOT independent. The unattributed residual is the "
                            "rms of the residuals of the SAME eleven points whose excursion is "
                            "DDmax. Two measures of how much D moves, computed on one dataset, are "
                            "correlated by construction, and a stable ratio is expected without any "
                            "multiplicative mechanism. Four correlated numbers cannot establish a "
                            "model."),
        "what_IS_established": ("The residuals are 4 to 5 times the SEM. They are therefore NOT "
                                "sampling noise. That part of the referee's point stands and is "
                                "adopted."),
        "registered_as": ("an OBSERVATION, not a model - the same treatment the document already "
                          "gives to the block-A antisymmetry in SGC, where 'two points per "
                          "hemisphere: it is an observation, not a result' was written."),
    },
    "referee_section_6_revised": {
        "his_claim": ("that the six-term budget counts once as a nuisance what the 'what does not "
                      "hold' section counts again as a model failure: 'two facts, one fact'."),
        "why_his_version_fails": ("There is no model failure. The quadratic family fitted to the "
                                  "MOCK SIDE ALONE, with its own covariance, gives chi2 = 5.61, "
                                  "0.72, 2.36, 0.90 on 3 dof against a limit of 11.34: adequate in "
                                  "all four cases. The chi2 rejection of 74.6-149.7 was an artefact "
                                  "of covariance construction, exactly as he predicted in his "
                                  "section 1(a)."),
        "why_it_may_hold_anyway": ("Both the unattributed residual AND the chi2 rejection are "
                                   "plausibly manifestations of the SAME object: the single-"
                                   "realisation structure of the data side, which has no "
                                   "representation in a covariance built from the mock side. That "
                                   "is a different object from a multiplicative model error, and it "
                                   "is consistent with question B above."),
        "how_it_is_decided": ("Not by argument. The intersection-mask test of his section 3.2 "
                              "removes the voxel channel by construction; if the block-A residuals "
                              "collapse, the object is identified and the budget shrinks. That test "
                              "is declared and not yet run."),
    },
}

REASON = (
    "The systematic uncertainty is brought inside the quoted intervals, the E1-E4 classification is "
    "declared as a one-sigma statement, a second denominator is registered alongside the deposited "
    "one, and the referee's multiplicative inference is recorded as an observation rather than "
    "adopted as a model. "
    "ACCEPTED WITHOUT RESERVE: the bootstrap intervals are over realisations and do not contain the "
    "41.9-60.3 generators of systematic. Combined in quadrature, sigma_tot = 43.4, 61.4, 54.4, "
    "43.0; no determination is further than 2.27 sigma from zero, and none is more than 1.04 sigma "
    "from the E1/E2 boundary. SGC k=0 sits at 0.51 sigma and DOES NOT SEPARATE E1 from E2. "
    "THE VERDICT IS NOT REOPENED: the deposited rule classifies on the point estimate and 75.0 >= "
    "53, so E2 stands and was correctly applied. What changes is the reporting. "
    "TWO DENOMINATORS, TWO QUESTIONS. The deposited SEM answers 'does D move', and on it the "
    "excursion is 8.2 to 10.5 sigma. A second question - 'does the observed field respond "
    "anomalously' - requires the dispersion of the per-realisation slopes, which gives 111.9, "
    "108.7, 89.7 and 86.5 generators and puts the excursion at 0.84 to 1.05 sigma. The observed "
    "response is entirely typical of a single realisation. Both are reported, each labelled with "
    "its question; neither replaces the other. "
    "THE MULTIPLICATIVE READING IS NOT ADOPTED. The constant ratio is real, but the four numbers "
    "are correlated by construction, since the unattributed residual and DDmax are computed from "
    "the same eleven points. What is established is that the residuals are 4-5 times the SEM and "
    "therefore not sampling noise; what is not established is that they are multiplicative."
)

EVIDENCE = (
    "Arithmetic reproduced from the frozen values: sqrt(11.2^2 + 41.9^2) = 43.4, "
    "sqrt(11.6^2 + 60.3^2) = 61.4, sqrt(8.7^2 + 53.7^2) = 54.4, sqrt(9.2^2 + 42.0^2) = 43.0; "
    "|DDmax|/sigma_tot = 2.27, 1.86, 1.67, 1.74; (|DDmax| - 53)/sigma_tot = 1.04, 0.99, 0.70, 0.51; "
    "sigma_sys/|DDmax| = 0.426, 0.529, 0.589, 0.560. Every figure of the referee's section 3.1 "
    "table is reproduced. "
    "results/paper2/due_lati.jsonl, per_realisation: the 200 per-realisation slopes have sd = "
    "1895.9, 1842.2, 1519.5, 1465.8 with sd/|mean| = 0.543, 0.610, 0.717, 0.784. Multiplied by the "
    "line-B baseline dF = 1.030071 - 0.971070 = 0.059001 these give 111.9, 108.7, 89.7 and 86.5 "
    "generators, against |DDmax| of 114.0, 98.3, 75.0 and 91.1, hence 1.02, 0.90, 0.84 and 1.05 "
    "sigma. "
    "results/paper2/due_lati.jsonl, mock_only_fit: chi2 = 5.606, 0.719, 2.361, 0.904 on 3 dof "
    "against a limit of 11.34, adequate = true in all four cases, against the 74.6-149.7 of the "
    "joint fit. The rejection of the quadratic family was an artefact of covariance construction."
)

RULES = {
    "marker": MARKER,
    "companion_document": "piano_risposta_referee_fasi0-3.md, item 0.4",
    "amends_records": [],
    "verdict_unchanged": ("The E1-E4 verdict is not reopened. The deposited rule classifies on the "
                          "point estimate and was correctly applied; this record changes how the "
                          "classification is REPORTED, not what it is."),
    "reporting_rule": ("Every determination is quoted with sigma_tot and with its distance from the "
                       "E1/E2 boundary. The four are not presented as a compact block. SGC k=0 is "
                       "declared as not separating E1 from E2."),
    "two_denominators_rule": ("Any statement about DDmax declares WHICH question it answers. 'D "
                              "moves' uses the deposited SEM; 'the observed field responds "
                              "anomalously' uses the per-realisation dispersion. A sigma quoted "
                              "without its question is not to be written."),
    "observation_not_model": ("The constant systematic-to-signal ratio is registered as an "
                              "observation. It is not used to change how the budget combines its "
                              "terms, because four numbers correlated by construction cannot "
                              "establish a multiplicative mechanism."),
    "open_and_how_it_closes": ("Whether the unattributed residual and the chi2 rejection are the "
                               "same object is OPEN. It is decided by the intersection-mask test, "
                               "not by argument."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not "
                              "change the E1-E4 verdict, does not change any threshold, and does "
                              "not alter how the six budget terms are combined."),
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
    chk("6  idempotenza (marker 20 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 19 e' gia' nel registro", MARKER_19 in blob)

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
        chk("10 old_value dice che gli IC non contengono il sistematico",
            ("do NOT contain the systematic" in rec["old_value"])
            and ("41.9, 60.3, 53.7 and 42.0" in rec["old_value"]))
        chk("11 SGC k=0 a 0.51 sigma e' dichiarato come NON separante",
            rec["new_value"]["accepted_the_systematic_enters_the_interval"]
               ["per_case"]["SGC_k0"]["sigma_from_E1_boundary"] == 0.51
            and "DOES NOT SEPARATE" in rec["new_value"]
               ["accepted_the_systematic_enters_the_interval"]["sgc_k0_declared"])
        chk("12 l'esito NON e' riaperto: cambia il report, non il verdetto",
            ("not reopened" in rec["rules"]["verdict_unchanged"])
            and ("correctly" in rec["new_value"]["verdict_unchanged_reporting_changed"]
                 ["rule_is_deterministic"]))
        chk("13 i due denominatori sono etichettati con la LORO domanda",
            ("Does D move" in rec["new_value"]["two_denominators_two_questions"]
                ["question_A"]["text"])
            and ("anomalously" in rec["new_value"]["two_denominators_two_questions"]
                 ["question_B"]["text"])
            and ("not to be written" in rec["rules"]["two_denominators_rule"]))
        chk("13f il record 19 e' sulla riga 19",
            MARKER_19 in json.dumps(recs[18], ensure_ascii=False))
        chk("13g la lettura moltiplicativa e' OSSERVAZIONE, non modello",
            ("correlated by construction" in rec["new_value"]
                ["multiplicative_reading_not_adopted"]["why_not_adopted"])
            and ("OBSERVATION, not a model" in rec["new_value"]
                 ["multiplicative_reading_not_adopted"]["registered_as"])
            and ("4 to 5 times the SEM" in rec["new_value"]
                 ["multiplicative_reading_not_adopted"]["what_IS_established"]))
        chk("13h il §6 del referee e' rivisto, non ignorato ne' accettato",
            ("no model failure" in rec["new_value"]["referee_section_6_revised"]
                ["why_his_version_fails"])
            and ("why_it_may_hold_anyway" in rec["new_value"]["referee_section_6_revised"])
            and ("intersection-mask" in rec["new_value"]["referee_section_6_revised"]
                 ["how_it_is_decided"]))
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
        # Ogni numero del record va ricalcolato, non solo riletto.
        import math
        pc = rec["new_value"]["accepted_the_systematic_enters_the_interval"]["per_case"]
        bad = []
        for nm, v in pc.items():
            tot = math.sqrt(v["sem"] ** 2 + v["sys"] ** 2)
            z0 = abs(v["DDmax"]) / tot
            d53 = (abs(v["DDmax"]) - 53.0) / tot
            if (abs(tot - v["sigma_tot"]) > 0.06 or abs(z0 - v["sigma_from_zero"]) > 0.01
                    or abs(d53 - v["sigma_from_E1_boundary"]) > 0.01):
                bad.append(nm)
        # e il secondo denominatore
        dF = 1.030071 - 0.971070
        sds = {"NGC_k0": 1895.9, "NGC_k1": 1842.2, "SGC_k0": 1519.5, "SGC_k1": 1465.8}
        qb = rec["new_value"]["two_denominators_two_questions"]["question_B"]["result_in_sigma"]
        for nm, sd in sds.items():
            if abs(abs(pc[nm]["DDmax"]) / (sd * dF) - qb[nm]) > 0.01:
                bad.append(nm + "/B")
        chk("14 aritmetica: sigma_tot, distanze e secondo denominatore ricalcolati",
            not bad, ",".join(bad) if bad else "quattro casi x tre quantita' + 4 rapporti")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend20 rev.1 ===")
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
        fail("il record 20 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

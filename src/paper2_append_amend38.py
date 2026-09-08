#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend38.py  (rev. 1) — Emendamento 38: il trattamento (B) falsifica la
predizione 1. Terzo meccanismo escluso, il fattore sopravvive.

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

AMEND_POSITION = 38                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 37

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

MARKER = "emendamento-38-trattamento-b-predizione-1-falsificata"
MARKER_37 = "emendamento-37-meccanismo-rsd-falsificato"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "treatment_B_falsifies_prediction_1_the_factor_survives"

JSON_PATH = ("amendments record 16 (prediction_1; gates D5a, D5b); "
             "amendments record 17 (denominator rule)")

OLD_VALUE = (
    "Record 16 declares treatment (B) - observables frozen at the fiducial, only r' = rhat * "
    "D_C(z_obs) recomputed - with gates D5a (bit-identity at the fiducial, tolerance zero), D5b "
    "(reproduction of the frozen fiducial baseline: 35423.575 / 31889.925 in NGC, 18694.420 / "
    "16477.950 in SGC, per record 21) and D5c. Prediction 1: if the measured factor 2.10-5.56 "
    "between the mock-side and data-side responses is entirely an artefact of treatment (A), then "
    "under (B) the ratio falls towards 1."
)

NEW_VALUE = {
    "the_run": {
        "executed": ("3-4 Sep 2026, 5.77 h + 5.71 h, 400 records, 200 realisations per hemisphere, "
                     "six line-B points, erosions 0 and 1, into "
                     "results/paper2/fase3_mock_fixedobs.jsonl."),
        "it_is_valid": ("1996 of 2400 comparable cells differ from fase3_mock.jsonl. The 404 that "
                        "do NOT differ are the 400 fiducial cells plus four coincidences: at the "
                        "fiducial (B) reproduces (A) BIT-IDENTICALLY by construction, which is D5a "
                        "seen from the outside."),
    },
    "all_four_gates_passed": {
        "D5a": ("Silent throughout. The reconstruction from the cache is bit-identical to the "
                "carving at the fiducial, tolerance zero."),
        "D5b": ("Means at the fiducial over 200 realisations: 35423.575, 31889.925, 18694.420, "
                "16477.950. EXACT against record 21, to the third decimal, in all four cases."),
        "n_sel_constant": ("Constant across all six points in all 400 realisations. In (B) the "
                           "selection is frozen at the fiducial, so this is the simplest external "
                           "sign that the mode does what it says. Under (A) it varies: 218292, "
                           "218151, 218132 at the first three points of the smoke."),
        "D5c": ("Applied retroactively at threshold 28 (record 36): maximum 8 over 2400 "
                "measurements, nothing excluded, results quotable."),
    },
    "prediction_1_is_falsified": {
        "the_measurement": {"NGC_k0": {"B": -198.10, "sem": 9.62, "A": -218.0, "data": -104.0,
                                       "ratio_B": 1.905, "ratio_A": 2.096},
                            "NGC_k1": {"B": -160.31, "sem": 9.10, "A": -172.3, "data": -74.0,
                                       "ratio_B": 2.166, "ratio_A": 2.328},
                            "SGC_k0": {"B": -139.46, "sem": 7.67, "A": -136.0, "data": -61.0,
                                       "ratio_B": 2.286, "ratio_A": 2.230},
                            "SGC_k1": {"B": -122.34, "sem": 6.67, "A": -111.1, "data": -20.0,
                                       "ratio_B": 6.117, "ratio_A": 5.555}},
        "what_it_says": ("The ratio does NOT fall towards 1. It goes from 2.096, 2.328, 2.230 and "
                         "5.555 under (A) to 1.905, 2.166, 2.286 and 6.117 under (B): down by 7 to "
                         "9 per cent in NGC, UP by 3 and 10 per cent in SGC. The factor survives "
                         "the change of treatment almost intact."),
        "and_it_is_not_a_matter_of_precision": ("The SEMs under (B) are 9.62, 9.10, 7.67 and 6.67, "
                                                "SMALLER than under (A) because the selection is "
                                                "frozen and one noise source is removed. The "
                                                "measurement is more precise, not less, and the "
                                                "prediction still fails."),
    },
    "the_third_pillar_to_fall_and_what_the_three_say_together": {
        "the_three": ("Record 25: the edge-voxel channel HALVES the residual and does not zero it, "
                      "PARTIAL. Record 37: removing the RSD entirely changes Delta_mock by about 13 "
                      "per cent. This record: freezing the observables changes it by about 10 per "
                      "cent."),
        "what_they_say_together": ("The mock side responds to the AP 2 to 6 times more than the "
                                   "data side, and NONE of the three candidate mechanisms accounts "
                                   "for it. The observation is now measured under three different "
                                   "treatments and survives all three."),
        "this_is_a_result_not_a_failure": ("A robust, unexplained, reproducible discrepancy between "
                                           "the response of a mock ensemble and that of the "
                                           "observed field is a finding. It is reported as one, "
                                           "with the three mechanisms it is NOT."),
    },
    "the_signature_repeats": {
        "what": ("Under (B) the ratio falls in NGC and RISES in SGC. Under real space (record 37) "
                 "the same: NGC 0.920 and 0.942, SGC 1.120 and 1.131. Two different treatments, the "
                 "same asymmetry between hemispheres."),
        "why_it_matters": ("A mechanism that merely scaled the response could not produce opposite "
                           "signs, and now it has appeared twice under different manipulations. "
                           "This is the strongest constraint the programme has on whatever the "
                           "cause is, and it is recorded as a constraint and not as a hypothesis."),
    },
    "what_this_does_to_the_response_document": {
        "section_1_again": ("The §1 section states that (A) and the data side undergo DIFFERENT "
                            "perturbations, so there is no reason for them to cancel. That remains "
                            "true as a fact about the code. But (B) IS the data-side treatment, and "
                            "it responds twice as much anyway: the difference in treatment is "
                            "therefore NOT what produces the factor. The section must say so."),
        "what_still_stands_there": ("The two columns, the ratios, the rank 1/201, the refutation of "
                                    "both of the referee's hypotheses, and the direct slope "
                                    "comparison at +0.96 sd."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not alter the measured ratios, which are "
                              "measurements and not interpretations."),
}

REASON = (
    "Treatment (B) has been executed and prediction 1 of record 16 is falsified. "
    "THE GATES. All four pass. D5a is silent: the reconstruction from the cache is bit-identical to "
    "the carving at the fiducial, and the external sign is that 400 of the 2400 cells - exactly the "
    "fiducial ones - are unchanged against the main register while 1996 differ. D5b is EXACT: the "
    "fiducial means are 35423.575, 31889.925, 18694.420 and 16477.950, matching record 21 to the "
    "third decimal in all four cases. n_sel is constant across all six points in all 400 "
    "realisations, which is what (B) means. D5c at threshold 28 excludes nothing, maximum 8. "
    "THE MEASUREMENT. Delta_mock(B5-B1) under (B) is -198.10, -160.31, -139.46 and -122.34, and the "
    "ratio to the data side goes from 2.096, 2.328, 2.230 and 5.555 under (A) to 1.905, 2.166, "
    "2.286 and 6.117 under (B): DOWN by 7 to 9 per cent in NGC, UP by 3 and 10 per cent in SGC. "
    "Record 16 predicted it would fall towards 1 if the factor were an artefact of treatment. It "
    "does not. And it is not a question of precision: the SEMs under (B) are SMALLER, because "
    "freezing the selection removes a noise source. "
    "THE THIRD PILLAR. Record 25 showed the edge-voxel channel halves the residual without zeroing "
    "it. Record 37 showed that removing the RSD entirely changes Delta_mock by 13 per cent. This "
    "record shows that freezing the observables changes it by 10 per cent. The mock side responds 2 "
    "to 6 times more than the data side, under three different treatments, and none of the three "
    "candidate mechanisms accounts for it. That is a finding and is reported as one, together with "
    "the three things it is not. "
    "AND THE SIGNATURE REPEATS. Under (B) the ratio falls in NGC and RISES in SGC; under real space "
    "the same asymmetry appeared, 0.920 and 0.942 against 1.120 and 1.131. Two different "
    "manipulations, the same opposite sign between hemispheres. A mechanism that merely scaled the "
    "response could not do that. It is recorded as a constraint on the cause, not as a hypothesis "
    "about it."
)

EVIDENCE = (
    "results/paper2/fase3_mock_fixedobs.jsonl, 400 records, 200 per hemisphere, six line-B points, "
    "erosions 0 and 1, fixed_observables true, run in 5.77 h and 5.71 h. "
    "Cell comparison against fase3_mock.jsonl on N_H1_k0: 1996 of 2400 differ; the 404 identical "
    "comprise the 400 fiducial cells. "
    "Fiducial means over 200 realisations: 35423.575 (NGC k=0), 31889.925 (NGC k=1), 18694.420 (SGC "
    "k=0), 16477.950 (SGC k=1), against record 21's values, exact. "
    "n_sel constant across the six points in 400 of 400 realisations. Under (A), from the smoke: "
    "218292 at FID, 218151 at B1, 218132 at B5. "
    "d5c_n_clipped over 2400 measurements: maximum 8, none at or above the threshold of 28 declared "
    "in record 36. "
    "Paired Delta_mock(B5-B1) under (B): -198.10 +/- 9.62, -160.31 +/- 9.10, -139.46 +/- 7.67, "
    "-122.34 +/- 6.67. Under (A): -218.0, -172.3, -136.0, -111.1. Data side: -104.0, -74.0, -61.0, "
    "-20.0. Ratios under (B): 1.905, 2.166, 2.286, 6.117; under (A): 2.096, 2.328, 2.230, 5.555. "
    "Record 37, real space: ratios to redshift space 0.920, 0.942 (NGC) and 1.120, 1.131 (SGC)."
)

RULES = {
    "marker": MARKER,
    "companion_document": "risposta_referee.md, §1; checklist_paper2.md, item 3.7",
    "amends_records": [16],
    "prediction_1_is_falsified_and_stays_so": ("The ratio does not fall towards 1 under (B). Not "
                                               "weakened, not reformulated, not repaired."),
    "three_mechanisms_are_now_excluded": ("Edge-voxel channel (record 25, PARTIAL), RSD (record 37), "
                                          "treatment regeneration (this record). The factor "
                                          "survives all three."),
    "the_unexplained_discrepancy_is_a_result": ("A robust, reproducible, unexplained difference "
                                                "between the AP response of the mock ensemble and "
                                                "that of the observed field is reported as a "
                                                "finding, with the mechanisms it is not."),
    "the_opposite_hemisphere_signature_is_a_constraint": ("It has now appeared under two different "
                                                          "manipulations. Any proposed cause must "
                                                          "produce deviations of opposite sign "
                                                          "between hemispheres."),
    "quoted_only_after_d5c": ("The threshold of record 36 was applied retroactively before any "
                              "number here was read, as records 23 and 34 require."),
    "the_treatment_difference_is_not_the_cause": ("(B) IS the data-side treatment and responds twice "
                                                  "as much anyway. That (A) and the data side "
                                                  "undergo different perturbations remains true "
                                                  "about the code and is no longer an explanation "
                                                  "of the factor."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not alter the measured ratios."),
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
    chk("6  idempotenza (marker 38 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 37 e' gia' nel registro", MARKER_37 in blob)

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
        chk("10 old_value cita la predizione 1 e i tre cancelli",
            ("falls towards 1" in rec["old_value"])
            and ("35423.575" in rec["old_value"]))
        chk("11 tutti e quattro i cancelli sono riportati come passati",
            len(rec["new_value"]["all_four_gates_passed"]) == 4
            and ("EXACT" in rec["new_value"]["all_four_gates_passed"]["D5b"]))
        chk("12 D5c applicato PRIMA di leggere i numeri, come i record 23 e 34",
            ("threshold 28" in rec["new_value"]["all_four_gates_passed"]["D5c"])
            and ("before any number here was read" in rec["rules"]["quoted_only_after_d5c"]))
        chk("13 i tre meccanismi esclusi sono elencati insieme",
            ("Record 25" in rec["new_value"]
                ["the_third_pillar_to_fall_and_what_the_three_say_together"]["the_three"])
            and ("Record 37" in rec["new_value"]
                 ["the_third_pillar_to_fall_and_what_the_three_say_together"]["the_three"])
            and ("three candidate mechanisms" in rec["new_value"]
                 ["the_third_pillar_to_fall_and_what_the_three_say_together"]
                 ["what_they_say_together"]))
        chk("13f il record 37 e' sulla riga 37 e si emenda il 16",
            (MARKER_37 in json.dumps(recs[36], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [16])
        chk("13g la firma opposta fra emisferi si RIPETE, ed e' un vincolo",
            ("appeared twice" in rec["new_value"]["the_signature_repeats"]["why_it_matters"])
            and ("opposite sign" in rec["rules"]
                 ["the_opposite_hemisphere_signature_is_a_constraint"]))
        chk("13h la SEM migliora e la predizione fallisce lo stesso",
            ("SMALLER than under (A)" in rec["new_value"]["prediction_1_is_falsified"]
                ["and_it_is_not_a_matter_of_precision"]))
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
        bad = []
        M = rec["new_value"]["prediction_1_is_falsified"]["the_measurement"]
        # 1. i rapporti si ricalcolano dai numeri grezzi
        for nm, d in M.items():
            if abs(d["B"] / d["data"] - d["ratio_B"]) > 5e-3:
                bad.append(nm + "/rapporto B")
            if abs(d["A"] / d["data"] - d["ratio_A"]) > 5e-3:
                bad.append(nm + "/rapporto A")
        # 2. NESSUNO scende verso 1: e' la falsificazione
        if any(d["ratio_B"] < 1.5 for d in M.values()):
            bad.append("un rapporto e' sceso verso 1: non sarebbe falsificato")
        # 3. la firma opposta: NGC scende, SGC sale
        ngc = [d for k, d in M.items() if k.startswith("NGC")]
        sgc = [d for k, d in M.items() if k.startswith("SGC")]
        if not (all(d["ratio_B"] < d["ratio_A"] for d in ngc)
                and all(d["ratio_B"] > d["ratio_A"] for d in sgc)):
            bad.append("la firma opposta non c'e': cade un'affermazione")
        # 4. e la SEM sotto (B) e' MIGLIORE, non peggiore
        SEM_A = {"NGC_k0": 11.6, "NGC_k1": 11.2, "SGC_k0": 9.2, "SGC_k1": 8.7}
        if not all(M[k]["sem"] < SEM_A[k] for k in M):
            bad.append("la SEM non migliora: cade l'argomento sulla precisione")
        # 5. lo scostamento massimo dei rapporti e' il ~10% dichiarato
        worst = max(abs(d["ratio_B"] / d["ratio_A"] - 1) for d in M.values())
        if not (0.08 < worst < 0.12):
            bad.append("scostamento massimo %.3f" % worst)
        chk("14 aritmetica: rapporti ricalcolati, nessuno verso 1, firma "
            "opposta, SEM migliore, scostamento max %.1f%%" % (100 * worst),
            not bad, ",".join(bad) if bad else "diciotto controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend38 rev.1 ===")
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
        fail("il record 38 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

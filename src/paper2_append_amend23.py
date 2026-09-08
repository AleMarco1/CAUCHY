#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend23.py  (rev. 1) — Emendamento 23: D5c misura invece di
fermare, perche' la soglia zero non e' raggiungibile.

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

AMEND_POSITION = 23                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 22

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

MARKER = "emendamento-23-d5c-misura-non-ferma"
MARKER_22 = "emendamento-22-valore-superseded-rientrato"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "d5c_measures_not_blocks_because_zero_is_unattainable"

JSON_PATH = "amendments record 17 (new_value.gate_D5c: tolerance, blocking, requirement)"

OLD_VALUE = (
    "Record 17 declares gate D5c: 'PF.clipped_per_face(pos_sel, BOX_MIN, BOX_SIZE) must report "
    "n_clipped == 0 at every grid point, in BOTH treatments; a non-zero count is a HARD STOP for "
    "that point, not a warning', with tolerance 0 and blocking true. Its rationale states: 'Under "
    "treatment (B) the galaxies are displaced radially and along line B towards F > 1 they move "
    "outward, so some WILL leave the frozen cube: without D5c the silent stacking would be counted "
    "as signal.'"
)

NEW_VALUE = {
    "what_was_measured": {
        "the_gate_fired_at_the_fiducial": ("On the first smoke after D5c was installed, it stopped "
                                           "at the FIDUCIAL point: 2 positions out of ~218000 "
                                           "outside the cube on face +y, excess 2.046 Mpc/h. At "
                                           "F = 1, inside the frozen Phase-3 measurement."),
        "it_does_not_depend_on_the_deformation": (
            "Smoke on FID, B1, B5 over 3 realisations, both hemispheres, then a read-only probe "
            "over 5 realisations and all six line-B points. Counts per point, NGC: FID 5, B1 7, "
            "B2 3, B4 4, B5 8, B6 2. SGC: FID 2, B1 5, B2 3, B4 3, B5 2, B6 1. The fiducial is "
            "neither the minimum nor the maximum in either hemisphere. Mean per point-realisation "
            "0.97 (NGC) and 0.53 (SGC); over 5 realisations the expected count per point is 4.8 "
            "and 2.7, and the observed spread 2-8 and 1-5 is within Poisson. The premise of record "
            "17 - that the clipping is produced by the deformation - is FALSE."),
        "it_is_already_inside_the_frozen_values": (
            "In the same smoke, gate D4b reproduces the frozen per-mock counts EXACTLY - 35318 = "
            "35318, 18627 = 18627 - with the clipping present. The frozen Phase-3 values were "
            "therefore computed with this clipping in them. It is not a new defect: it is a "
            "property of the mock side that had never been looked at."),
        "and_they_land_INSIDE_the_mask": (
            "45 clipped positions out of 45 land on a voxel that is IN the mask: 29 of 29 in NGC, "
            "16 of 16 in SGC. Measured with the same np.clip expression as phase8:688 and the same "
            "mask array the run uses."),
    },
    "my_reasoning_was_wrong_and_why": {
        "what_was_argued": ("That the clipped positions land in the padding, where the randoms do "
                            "not reach, so the mask threshold is not crossed there and they never "
                            "enter the filtration - making the effect on N_H1 exactly zero rather "
                            "than merely small."),
        "what_the_measurement_says": ("45 out of 45 are in the mask. The argument is refuted."),
        "why_it_failed": ("The excesses give it away: most are BELOW 0.5 Mpc/h, some as small as "
                          "0.005. These are not galaxies flung into the padding by a large RSD "
                          "displacement; they are galaxies sitting ON THE SURVEY EDGE, protruding "
                          "by a fraction of a cell. Their destination voxel after the clip is their "
                          "own edge voxel, which is in the mask because that is where the randoms "
                          "are. Only a few cases show excesses of 2-3 Mpc/h, and those are the ones "
                          "the RSD hypothesis fits. The rest is edge geometry."),
        "lesson": ("The mechanism was argued from the largest observed excess and generalised to "
                   "all of them. The distribution of excesses, which was in the same output, would "
                   "have shown it at once."),
    },
    "the_effect_is_small_but_not_zero": {
        "magnitude": ("1-2 galaxies displaced by less than one cell, against a mean occupancy of "
                      "~0.7 galaxies per voxel, can push zero or one voxel over the mask "
                      "threshold. By the calibration of gate 2.2a - 216 mask voxels are worth 34 "
                      "generators - one voxel is worth 0.157 generators, against a SEM of 11.2."),
        "status": ("Small, but not null, and never declared. It is reported as a known term of the "
                   "mock side, not swept."),
    },
    "why_zero_is_not_an_attainable_threshold": (
        "D5c as written requires n_clipped == 0. That is unreachable: the count is non-zero at the "
        "fiducial, where there is no deformation at all, and it is inside the frozen values. A "
        "gate whose threshold cannot be met is not a gate: it is a stop."),
    "the_derogation": {
        "what": ("For the §3.8 real-space run and for the treatment (B) run, D5c operates in "
                 "MEASURE mode: it computes n_clipped at every point and writes it into the "
                 "record, and does not stop the run. D5C_MODE = 'measure' is a module constant in "
                 "paper2_runner_fase3_mock.py, and the code prints a warning at every run and every "
                 "smoke."),
        "why_the_threshold_is_not_fixed_now": (
            "Five realisations with counts between 0 and 3 do not give a distribution. Choosing a "
            "threshold from them would be picking a number because it is convenient, which is "
            "exactly what record 20 refuses to do elsewhere. The runs themselves produce 200 x 6 x "
            "2 measurements: the threshold is declared on that distribution, and applied "
            "retroactively to the same runs."),
        "what_this_costs": ("A gate is suspended for the duration of two runs. That is the cost and "
                            "it is stated plainly."),
        "what_protects_the_result": [
            "the count is written into EVERY record, in both modes, so the datum does not depend "
            "on the mode",
            "no result from either run is quoted until the threshold is declared on the observed "
            "distribution and applied to those same records",
            "the derogation lives as a constant in the source, not as a command-line flag, so "
            "restoring it is a deliberate edit that leaves a trace",
            "the code prints the mode at every execution instead of relying on memory",
        ],
        "when_it_ends": ("When the threshold is declared. At that point D5C_MODE returns to "
                         "'block' and a record states the threshold, its derivation from the "
                         "observed distribution, and which points if any it excludes."),
    },
    "what_is_not_changed": {
        "d5a_and_d5b": "Untouched. Bit-identity at the fiducial and the frozen baseline both stand.",
        "denominator_rule": ("Record 17's denominator rule for prediction 1 is untouched. If D5c "
                             "later excludes points, that rule already covers the case."),
        "the_data_side": ("Record 13 point (c) still forbids any clipped object on the data side, "
                          "with a hard stop. Nothing there is relaxed: the data side achieves zero "
                          "and the mock side does not, and that asymmetry is itself the finding."),
    },
}

REASON = (
    "Gate D5c is suspended from blocking to measuring for the two long runs, because its threshold "
    "of zero is unattainable and the premise it was built on is false. Both statements are "
    "measured, not argued. "
    "THE PREMISE. Record 17 declares that under deformation galaxies move radially and leave the "
    "cube, so D5c catches the resulting silent stacking. Measured over 5 realisations and all six "
    "line-B points, the counts per point are 5, 7, 3, 4, 8, 2 in NGC and 2, 5, 3, 3, 2, 1 in SGC: "
    "the fiducial is neither the minimum nor the maximum, and the spread is within Poisson for a "
    "mean of about one per point-realisation. The clipping does not depend on the deformation. "
    "THE THRESHOLD. The count is non-zero AT THE FIDUCIAL, where there is no deformation, and gate "
    "D4b reproduces the frozen per-mock values exactly with the clipping present - so it is inside "
    "the frozen Phase-3 measurement already. A threshold of zero cannot be met. "
    "AN ARGUMENT OF MINE WAS REFUTED IN THE PROCESS, and it is recorded because the failure is "
    "instructive. I argued that the clipped positions land in the padding, outside the mask, making "
    "the effect on N_H1 exactly zero. The measurement says 45 of 45 land INSIDE the mask. The "
    "reason is in the excesses: most are below 0.5 Mpc/h, some 0.005 - these are edge galaxies "
    "protruding by a fraction of a cell, whose destination voxel is their own edge voxel, which is "
    "in the mask. Only a few show 2-3 Mpc/h, and only those fit the RSD hypothesis. The mechanism "
    "had been generalised from the largest excess to all of them. "
    "THE EFFECT IS THEREFORE NOT ZERO: by the calibration of gate 2.2a, one mask voxel is worth "
    "0.157 generators against a SEM of 11.2. Small, never declared, and now reported. "
    "THE DEROGATION AND ITS COST. D5c measures and does not stop for the §3.8 and treatment (B) "
    "runs. A gate is suspended for two runs; that is the cost. The threshold is not fixed now "
    "because five realisations with counts of 0 to 3 give no distribution, and choosing from them "
    "would be picking a convenient number. The runs produce 200 x 6 x 2 measurements and the "
    "threshold is declared on those, then applied retroactively to the same records. Until then no "
    "result from either run is quoted."
)

EVIDENCE = (
    "Smoke of paper2_runner_fase3_mock.py on FID, B1, B5, 3 realisations. NGC: FID 2, 1, 0; B1 2, "
    "0, 3; B5 1, 1, 2. SGC: FID 0, 0, 0; B1 2, 0, 2; B5 1, 0, 0. In the same smoke D4b reports "
    "'esatto' against the frozen R5_er0/R5_er1 values, per mock: 35318 vs 35318 and 18627 vs 18627. "
    "paper2_d5c_sonda.py, read-only, 5 realisations, six line-B points, with a reproduction gate on "
    "n_sel at FID for realisation 0 against results/paper2/fase3_mock.jsonl (218292 in NGC, 82693 "
    "in SGC, both matching). Totals: NGC 29 clipped, 29 in mask; SGC 16 clipped, 16 in mask. Per "
    "point NGC: FID 5, B1 7, B2 3, B4 4, B5 8, B6 2. Per point SGC: FID 2, B1 5, B2 3, B4 3, B5 2, "
    "B6 1. Excesses range from 0.005 to 3.207 Mpc/h, with the majority below 0.5. Faces: mostly +y "
    "in NGC, -z and -x in SGC. "
    "The in-mask test uses the same expression as phase8:688, "
    "np.clip(((pos - BOX_MIN)/CELL).astype(int), 0, NGRID-1), against the same mask array the run "
    "uses. "
    "Gate 2.2a calibration, checklist item 2.2a: 216 mask voxels changing are worth 34 generators, "
    "hence 0.157 generators per voxel. SEM of DD_max: 11.2 (NGC k=1)."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, items 3.7 and 3.9",
    "amends_records": [17],
    "gate_suspended_not_withdrawn": ("D5c is not withdrawn. It measures instead of blocking, for "
                                     "two runs, until its threshold can be declared on an observed "
                                     "distribution rather than guessed."),
    "the_datum_does_not_depend_on_the_mode": ("n_clipped is written into every record in both "
                                              "modes. Whatever is decided about the gate, the "
                                              "measurement exists."),
    "no_result_quoted_before_the_threshold": ("No number from the §3.8 or treatment (B) runs is "
                                              "quoted until the threshold is declared and applied "
                                              "to those same records."),
    "threshold_from_data_not_from_convenience": ("Five realisations give no distribution. The "
                                                 "threshold is derived from the 200 x 6 x 2 "
                                                 "measurements the runs themselves produce."),
    "derogation_is_visible_in_the_source": ("D5C_MODE is a module constant, not a command-line "
                                            "flag, and the code prints the mode at every run and "
                                            "every smoke. Restoring 'block' is a deliberate edit "
                                            "that leaves a trace in the file."),
    "data_side_not_relaxed": ("Record 13 point (c) still forbids any clipped object on the data "
                              "side with a hard stop. The data side reaches zero and the mock side "
                              "does not: that asymmetry is a finding, not a reason to relax the "
                              "data side."),
    "a_refuted_argument_is_recorded": ("The claim that clipped positions land outside the mask was "
                                       "mine, and it was wrong: 45 of 45 are inside. It is recorded "
                                       "because the way it failed - generalising a mechanism from "
                                       "the largest observed excess to all of them - is the "
                                       "instructive part."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "D5a, D5b or the denominator rule, and does not change the E1-E4 "
                              "verdict."),
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
    chk("6  idempotenza (marker 23 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 22 e' gia' nel registro", MARKER_22 in blob)

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
        chk("10 old_value cita D5c come dichiarato, premessa inclusa",
            ("n_clipped == 0" in rec["old_value"])
            and ("some WILL leave the frozen cube" in rec["old_value"]))
        chk("11 il cancello e' SOSPESO, non ritirato, e per due run",
            ("not withdrawn" in rec["rules"]["gate_suspended_not_withdrawn"])
            and ("measure" in rec["new_value"]["the_derogation"]["what"]))
        chk("12 il costo della deroga e' dichiarato, non attenuato",
            ("the cost" in rec["new_value"]["the_derogation"]["what_this_costs"])
            and len(rec["new_value"]["the_derogation"]["what_protects_the_result"]) == 4)
        chk("13 la soglia NON si fissa adesso, e la ragione e' dichiarata",
            ("do not give a distribution" in rec["new_value"]["the_derogation"]
                ["why_the_threshold_is_not_fixed_now"])
            and ("convenient" in rec["new_value"]["the_derogation"]
                 ["why_the_threshold_is_not_fixed_now"]))
        chk("13f il record 22 e' sulla riga 22 e si emenda il 17",
            (MARKER_22 in json.dumps(recs[21], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [17])
        chk("13g l'argomento MIO confutato e' registrato, con il perche'",
            ("45 out of 45" in rec["new_value"]["my_reasoning_was_wrong_and_why"]
                ["what_the_measurement_says"])
            and ("largest observed excess" in rec["new_value"]
                 ["my_reasoning_was_wrong_and_why"]["lesson"]))
        chk("13h il lato dati NON e' rilassato, e l'asimmetria e' un risultato",
            ("hard stop" in rec["rules"]["data_side_not_relaxed"])
            and ("asymmetry is a finding" in rec["rules"]["data_side_not_relaxed"]))
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
        NGC = {"FID": 5, "B1": 7, "B2": 3, "B4": 4, "B5": 8, "B6": 2}
        SGC = {"FID": 2, "B1": 5, "B2": 3, "B4": 3, "B5": 2, "B6": 1}
        if sum(NGC.values()) != 29 or sum(SGC.values()) != 16:
            bad.append("totali")
        if sum(NGC.values()) + sum(SGC.values()) != 45:
            bad.append("45")
        # il fiduciale non e' ne' minimo ne' massimo: la premessa del 17 cade
        for nm, d in (("NGC", NGC), ("SGC", SGC)):
            if d["FID"] == min(d.values()) or d["FID"] == max(d.values()):
                bad.append(nm + "/FID estremo")
        # e lo spread e' compatibile con Poisson su 5 realizzazioni
        for nm, d in (("NGC", NGC), ("SGC", SGC)):
            mu = sum(d.values()) / 6.0
            if not all(abs(v - mu) <= 3.0 * math.sqrt(mu) for v in d.values()):
                bad.append(nm + "/Poisson")
        # e un voxel vale 34/216 generatori
        if abs(34.0 / 216.0 - 0.157) > 5e-4:
            bad.append("0.157")
        chk("14 aritmetica: totali 29+16=45, FID non estremo, spread Poisson, "
            "0.157 gen/voxel", not bad, ",".join(bad) if bad else
            "sei controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend23 rev.1 ===")
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
        fail("il record 23 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

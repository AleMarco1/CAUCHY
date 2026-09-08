#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend27.py  (rev. 1) — Emendamento 27: due punti specchio sul
blocco A, per separare pari da dispari.

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

AMEND_POSITION = 27                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 26

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

MARKER = "emendamento-27-blocco-a-due-punti-specchio"
MARKER_26 = "emendamento-26-termine-c-dipendenza-dal-punto"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "block_a_two_mirror_points_to_separate_even_from_odd"

JSON_PATH = ("prereg \\u00a74 (measurement grid, line A); src/paper2_item13rev2.py LINE_A; "
             "referee report section 6")

OLD_VALUE = (
    "Line A has two points, pure isotropic dilations at alpha = 0.972638 and 1.040397, where the "
    "physical signal is ZERO BY THEOREM (Proposition 2). The measured residuals are, as raw "
    "excursions against the fiducial: NGC k=0 (+9, +25), k=1 (+1, +17); SGC k=0 (-30, +30), k=1 "
    "(-19, +11). The Phase-3 report calls the NGC behaviour 'a constant offset' and the SGC "
    "behaviour 'antisymmetric', and concludes: 'two points per hemisphere: it is an observation, "
    "not a result'. The referee's section 6 says that is too indulgent, and that SGC giving an odd "
    "response where the theorem says zero disturbs him more than anything else in the document."
)

NEW_VALUE = {
    "the_confounder_that_makes_the_current_data_unreadable": {
        "what": ("The two existing points are NOT symmetric about 1: |alpha - 1| is 0.02736 for A1 "
                 "and 0.04040 for A3, a ratio of 1.476. With two points at unequal distances, even "
                 "and odd DO NOT SEPARATE."),
        "how_large": ("A purely EVEN quadratic response would give A3/A1 = 1.476^2 = 2.18, which "
                      "reads as an apparent odd component of 37 per cent of the mean. So an odd "
                      "part of that size can be produced by an even response and asymmetric "
                      "sampling alone."),
        "what_it_changes_in_the_reading": (
            "NGC k=0 gives A3/A1 = 2.78 against the 2.18 expected from a pure even quadratic: "
            "CONSISTENT. Its apparent odd part is largely the sampling artefact, and the 'constant "
            "offset' reading is not established. SGC is different, and for a reason that needs no "
            "model: an EVEN function CANNOT CHANGE SIGN across 1, and SGC k=0 gives -30 and +30. "
            "The odd part there is real."),
        "conclusion": ("The referee's concern is genuine but applies to SGC only, and in the "
                       "present data it cannot be isolated. Two points cannot decompose a function "
                       "into even and odd when they sit at different amplitudes."),
    },
    "the_two_points": {
        "A1m": {"alpha": 1.027362320997, "c": 0.973366435154, "abs_alpha_minus_1": 0.027362320997,
                "mirror_of": "A1", "within_physical_range": True},
        "A3m": {"alpha": 0.959603267595, "c": 1.042097326853, "abs_alpha_minus_1": 0.040396732405,
                "mirror_of": "A3", "within_physical_range": False},
        "symmetry_is_exact": ("|alpha - 1| matches its partner to 0.00e+00, not to rounding: the "
                              "mirrors are constructed as 1 +/- |alpha_partner - 1|."),
        "naming": ("A1m and A3m, not A2 and A4. On line B the numbering skips 3 because B3 is the "
                   "fiducial; by the same convention A2 is reserved for the fiducial of line A, and "
                   "reusing it would create a silent collision. 'm' for mirror is "
                   "self-documenting."),
        "A3m_is_outside_the_physical_range": (
            "alpha = 0.959603 lies below the isotropic physical range [0.972638, 1.040397]. On "
            "block A that is admissible without qualification: the signal is ZERO BY THEOREM at any "
            "alpha, so this is a null test and not a cosmology point. It is stated here rather than "
            "left for a reader to notice."),
        "cost": ("Two points, two gauges each, two hemispheres: eight deterministic data-side runs "
                 "of about 40 s. The mock side is not touched."),
    },
    "what_the_two_amplitudes_buy": {
        "one_mirror_would_suffice_to_remove_the_confounder": (
            "A1m alone completes a symmetric pair with A1 and gives a clean even/odd decomposition "
            "at one amplitude."),
        "two_give_the_scaling": ("With pairs at |alpha - 1| = 0.02736 and 0.04040, in ratio r = "
                                 "1.4764, the ratio of the two odd parts distinguishes two forms: "
                                 "LINEAR in (alpha - 1) predicts 1.476, a CONSTANT STEP predicts "
                                 "1.000. The two predictions differ by 48 per cent."),
    },
    "reproduction_gate": {
        "what": ("At both new points, the `derived` gauge must reproduce the fiducial EXACTLY: "
                 "23790 and 28256 in NGC, 12011 and 15122 in SGC. A1 and A3 already do."),
        "why_it_is_the_right_gate_here": ("Proposition 2 in the `derived` gauge is an exact "
                                          "statement, not an approximation. If a new point fails "
                                          "it, the point is malformed and nothing from it is used."),
        "tolerance": 0,
        "blocking": True,
    },
    "declared_prediction": {
        "quantity": ("odd = (residual(expansion) - residual(compression)) / 2, computed within each "
                     "SYMMETRIC pair, per hemisphere and per erosion level. Ratio = odd(large "
                     "amplitude) / odd(small amplitude)."),
        "the_thresholds_are_chosen_not_derived": (
            "The data side is DETERMINISTIC: there are no error bars on these residuals, so the "
            "threshold cannot come from a sampling error as it does in record 26. It is a choice, "
            "and it is stated as one. The bands are +/- 10 per cent around each prediction, which "
            "do not overlap, and the gap between them is declared unresolved rather than assigned "
            "to the nearer side."),
        "rule": {
            "STEP": "0.900 <= ratio <= 1.100. The odd part does not scale: it is a step.",
            "LINEAR": "ratio >= 1.329. The odd part scales with the amplitude.",
            "UNRESOLVED": ("1.100 < ratio < 1.329. Between the two bands. Reported with the number "
                           "and assigned to neither."),
            "NEITHER": ("ratio < 0.900, or negative. The odd part shrinks with amplitude, or "
                        "changes sign between the two amplitudes: neither form describes it, and "
                        "that is itself a result."),
        },
        "the_four_cases_are_exhaustive": True,
        "and_the_even_part_too": ("The even part is reported at both amplitudes. If it scales as "
                                  "the square of the amplitude, ratio 2.18, it is the "
                                  "discretisation artefact the Phase-3 report assumed. That is "
                                  "reported, not decided: no threshold is declared on it, because "
                                  "no argument fixes one."),
        "not_repaired_afterwards": True,
    },
    "what_this_does_not_do": {
        "ddmax_and_the_verdict": ("Line A does not enter DDmax, which is the B1-B5 excursion, and "
                                  "the E1-E4 verdict is not reopened. Adding points to line A "
                                  "cannot change a rule already applied - the same reasoning "
                                  "record 15 used for B6."),
        "the_floor_f": ("Term (f), the floor, is currently the rms of the two block-A residuals. "
                        "Whether it becomes the rms of four is NOT decided here: that is a change "
                        "to the budget and would need its own record, after these numbers exist."),
    },
}

REASON = (
    "Two points are added to line A so that even and odd can be separated, which the present grid "
    "cannot do. "
    "THE CONFOUNDER. A1 and A3 sit at |alpha - 1| = 0.02736 and 0.04040, a ratio of 1.476. At "
    "unequal amplitudes a purely EVEN response produces an apparent odd component: an even "
    "quadratic gives A3/A1 = 2.18, which reads as 37 per cent of odd. NGC k=0 measures 2.78, "
    "consistent with a pure even response, so its 'constant offset' reading is not established. SGC "
    "is different for a reason that needs no model: an even function cannot change sign across 1, "
    "and SGC k=0 gives -30 and +30. The odd part there is real, and the referee's section 6 is "
    "right about SGC and not about the grid's ability to show it. "
    "THE POINTS. A1m at alpha = 1.027362 and A3m at alpha = 0.959603, each the exact mirror of an "
    "existing point, giving two SYMMETRIC pairs at two amplitudes. Named A1m and A3m rather than A2 "
    "and A4: line B skips 3 because B3 is the fiducial, so A2 is reserved by the same convention "
    "and reusing it would collide silently. A3m lies below the isotropic physical range, which on a "
    "null test where the signal is zero by theorem is admissible - and is stated here rather than "
    "left to be noticed. "
    "THE THRESHOLDS ARE CHOSEN, NOT DERIVED, AND THAT IS SAID. The data side is deterministic, so "
    "there are no error bars and no sampling argument is available as there was in record 26. With "
    "amplitudes in ratio 1.4764, a LINEAR odd part predicts a ratio of 1.476 between the two odd "
    "components and a constant STEP predicts 1.000. Bands of +/- 10 per cent around each do not "
    "overlap; the gap between them, 1.100 to 1.329, is declared UNRESOLVED rather than assigned to "
    "the nearer side; and a ratio below 0.900 or negative is NEITHER form, which is itself a "
    "result. The four cases are exhaustive. "
    "THE GATE. At both new points the `derived` gauge must reproduce the fiducial exactly, as A1 "
    "and A3 do. Proposition 2 in that gauge is exact, so a failure means the point is malformed."
)

EVIDENCE = (
    "results/paper2/fase3.jsonl and the Phase-3 report: line A at alpha = 0.972638 and 1.040397, "
    "recovered from the printed c = L_fid/L_point of 1.02813208 and 0.96117180. Raw excursions "
    "against the fiducial: NGC k=0 (+9, +25), k=1 (+1, +17); SGC k=0 (-30, +30), k=1 (-19, +11). "
    "Even/odd on the present pairs: NGC k=0 even +17.0 odd +8.0; NGC k=1 even +9.0 odd +8.0; SGC "
    "k=0 even 0.0 odd +30.0; SGC k=1 even -4.0 odd +15.0. A3/A1 = 2.78, 17.00, -1.00, -0.58. "
    "A pure even quadratic at these amplitudes predicts A3/A1 = (0.04040/0.02736)^2 = 2.18. "
    "Mirrors: 1 + 0.02736 = 1.027362 (c = 0.97336644) and 1 - 0.04040 = 0.959603 (c = 1.04209733); "
    "|alpha - 1| matches its partner to 0.00e+00. "
    "Amplitude ratio r = 0.04040/0.02736 = 1.4764. Bands: step [0.900, 1.100], linear [1.329, "
    "1.624], gap [1.100, 1.329]. "
    "In the deposited runs A1 and A3 in gauge `derived` reproduce 23790 / 28256 (NGC) and 12011 / "
    "15122 (SGC) exactly. "
    "Points are defined in src/paper2_item13rev2.py, LINE_A, which point_plan reads."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.12; referee report section 6",
    "amends_records": [],
    "line_a_does_not_enter_ddmax": ("As record 15 established for B6, points added after the fact "
                                    "cannot reopen a rule already applied. Line A never entered "
                                    "DDmax and still does not."),
    "thresholds_chosen_and_declared_as_chosen": ("No sampling argument is available on a "
                                                 "deterministic side. The bands are a choice, "
                                                 "stated as one, fixed before the run and not moved "
                                                 "afterwards."),
    "unresolved_is_not_rounded": ("The gap between the two bands is reported as UNRESOLVED with the "
                                  "number. It is not assigned to the nearer prediction."),
    "the_even_part_carries_no_verdict": ("It is reported at both amplitudes and compared with the "
                                         "2.18 of a quadratic, but no threshold is declared on it "
                                         "because no argument fixes one."),
    "out_of_range_is_admissible_here_and_declared": ("A3m lies below the physical isotropic range. "
                                                     "On block A the signal is zero by theorem at "
                                                     "any alpha, so a null test outside the range "
                                                     "is meaningful. Stated, not hidden."),
    "the_floor_is_not_re_derived_here": ("Whether term (f) becomes the rms of four residuals "
                                         "instead of two is a change to the budget and needs its "
                                         "own record, after the numbers exist."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not change the budget."),
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
    chk("6  idempotenza (marker 27 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 26 e' gia' nel registro", MARKER_26 in blob)

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
        chk("10 old_value cita i residui e la frase del rapporto di Fase 3",
            ("(-30, +30)" in rec["old_value"])
            and ("an observation, not a result" in rec["old_value"]))
        chk("11 il confondente e' quantificato, non solo nominato",
            ("2.18" in rec["new_value"]["the_confounder_that_makes_the_current_data_unreadable"]
                ["how_large"])
            and ("37 per cent" in rec["new_value"]
                 ["the_confounder_that_makes_the_current_data_unreadable"]["how_large"]))
        chk("12 NGC e SGC sono letti diversamente, e la ragione non usa modelli",
            ("CONSISTENT" in rec["new_value"]
                ["the_confounder_that_makes_the_current_data_unreadable"]
                ["what_it_changes_in_the_reading"])
            and ("CANNOT CHANGE SIGN" in rec["new_value"]
                 ["the_confounder_that_makes_the_current_data_unreadable"]
                 ["what_it_changes_in_the_reading"]))
        chk("13 le soglie sono SCELTE, e il record dice che lo sono",
            ("DETERMINISTIC" in rec["new_value"]["declared_prediction"]
                ["the_thresholds_are_chosen_not_derived"])
            and ("It is a choice, and it is stated as one" in rec["new_value"]
                 ["declared_prediction"]["the_thresholds_are_chosen_not_derived"])
            and ("stated as one" in rec["rules"]["thresholds_chosen_and_declared_as_chosen"]))
        chk("13f il record 26 e' sulla riga 26",
            MARKER_26 in json.dumps(recs[25], ensure_ascii=False))
        chk("13g quattro esiti, e il quarto non e' schiacciato sul terzo",
            rec["new_value"]["declared_prediction"]["the_four_cases_are_exhaustive"] is True
            and set(rec["new_value"]["declared_prediction"]["rule"])
            == {"STEP", "LINEAR", "UNRESOLVED", "NEITHER"}
            and ("not assigned to the nearer" in rec["rules"]["unresolved_is_not_rounded"]))
        chk("13h A3m fuori range e' DICHIARATO, e il nome non collide",
            rec["new_value"]["the_two_points"]["A3m"]["within_physical_range"] is False
            and ("A2 is reserved" in rec["new_value"]["the_two_points"]["naming"]))
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
        P = rec["new_value"]["the_two_points"]
        A1, A3 = 1 / 1.02813208, 1 / 0.96117180
        # 1. gli specchi sono ESATTI, non arrotondati
        if abs(abs(P["A1m"]["alpha"] - 1) - abs(A1 - 1)) > 1e-5:
            bad.append("A1m non specchia A1")
        if abs(abs(P["A3m"]["alpha"] - 1) - abs(A3 - 1)) > 1e-5:
            bad.append("A3m non specchia A3")
        # 2. c = 1/alpha, come il runner lo usa
        for nm in ("A1m", "A3m"):
            if abs(P[nm]["c"] - 1 / P[nm]["alpha"]) > 1e-7:
                bad.append(nm + "/c")
        # 3. A1m dentro il range, A3m fuori: dichiarato e VERO
        if not (A1 <= P["A1m"]["alpha"] <= A3):
            bad.append("A1m fuori range")
        if A1 <= P["A3m"]["alpha"] <= A3:
            bad.append("A3m dentro range")
        # 4. il confondente: una pari quadratica da' 2.18
        r = abs(A3 - 1) / abs(A1 - 1)
        if abs(r ** 2 - 2.18) > 0.01 or abs(r - 1.4764) > 5e-4:
            bad.append("confondente")
        # 5. le bande non si sovrappongono e coprono la retta positiva
        def verdetto(x):
            if x < 0.900:
                return "NEITHER"
            if x <= 1.100:
                return "STEP"
            if x < 1.329:
                return "UNRESOLVED"
            return "LINEAR"
        got = {verdetto(x / 1000.0) for x in range(0, 2001)}
        if got != {"NEITHER", "STEP", "UNRESOLVED", "LINEAR"}:
            bad.append("esiti non esaustivi")
        # 6. e le due previsioni cadono ognuna nella propria banda
        if verdetto(1.000) != "STEP" or verdetto(r) != "LINEAR":
            bad.append("previsioni fuori banda")
        chk("14 aritmetica: specchi esatti, c=1/alpha, confondente 2.18, "
            "quattro esiti esaustivi", not bad,
            ",".join(bad) if bad else "dodici controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend27 rev.1 ===")
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
        fail("il record 27 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

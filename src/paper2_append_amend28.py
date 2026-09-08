#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend28.py  (rev. 1) — Emendamento 28: rettifica degli alpha del
27, e il suo cancello e' un controllo di cablaggio.

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

AMEND_POSITION = 28                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 27

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

MARKER = "emendamento-28-rettifica-alpha-specchi"
MARKER_27 = "emendamento-27-blocco-a-due-punti-specchio"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "record_27_alphas_were_inverted_from_c_instead_of_read_from_line_a"

JSON_PATH = "amendments record 27 (new_value.the_two_points); src/paper2_item13a_15a.py LINE_A"

OLD_VALUE = (
    "Record 27 gives the two new block-A points as A1m at alpha = 1.027362320997 with c = "
    "0.973366435154, and A3m at alpha = 0.959603267595 with c = 1.042097326853, and states that "
    "'|alpha - 1| matches its partner to 0.00e+00, not to rounding'. Its evidence says the existing "
    "alphas were 'recovered from the printed c = L_fid/L_point of 1.02813208 and 0.96117180'."
)

NEW_VALUE = {
    "what_is_wrong": {
        "the_alphas_were_not_recovered_but_invented": (
            "LINE_A is defined in src/paper2_item13a_15a.py line 77 as [('A1', 0.9725), ('A3', "
            "1.0406)]. Those ARE the alphas. Record 27 did not read them: it inverted the c printed "
            "by the runner, on the assumption c = 1/alpha."),
        "c_is_not_one_over_alpha": (
            "c is the re-gauge factor, and for a pure dilation with padding it is "
            "c = (E + 2p)/(alpha E + 2p), not 1/alpha. The padding is what breaks the inversion. "
            "Solving that relation for E from A1 gives L_fid = 1997.55 against the frozen "
            "1997.3629, which is the same quantity to the accuracy of the padding convention: the "
            "mechanism is confirmed, the inversion is not."),
        "the_size_of_the_error": ("A1m was written 1.027362320997 instead of 1.0275, an error of "
                                  "1.38e-04; A3m 0.959603267595 instead of 0.9594, 2.03e-04."),
        "and_the_exactness_claim_was_false": (
            "Record 27 claims the mirrors match to 0.00e+00. With ITS OWN values they do not: "
            "|1.027362 - 1| - |0.972638 - 1| is not zero against the true partner 0.9725. With the "
            "corrected values the claim is true, to 1.11e-16 and 0.00e+00 exactly, because the "
            "mirrors are then constructed from the real LINE_A entries."),
    },
    "the_corrected_points": {
        "A1m": {"alpha_iso": 1.0275, "mirror_of": "A1", "abs_alpha_minus_1": 0.0275,
                "within_physical_range": True},
        "A3m": {"alpha_iso": 0.9594, "mirror_of": "A3", "abs_alpha_minus_1": 0.0406,
                "within_physical_range": False},
        "c_is_not_recorded_here_and_that_is_deliberate": (
            "Record 27 hard-coded c for both points. It should not have: c is DERIVED by "
            "I13.deform() from alpha_iso, exactly as it is for every other point on the grid. "
            "Writing it into a record creates a second place where it lives, which is the defect "
            "class that produced the 445 vs 313 dispersion. LINE_A carries (name, alpha_iso) and "
            "nothing else."),
    },
    "what_survives_unchanged": {
        "every_conclusion": ("The amplitude ratio is r = 0.0406/0.0275 = 1.476364 against the "
                             "1.4764 declared; the even-quadratic confounder is r^2 = 2.1796 "
                             "against 2.18; A1m is inside the physical range and A3m is outside, as "
                             "declared. No threshold moves and no verdict changes."),
        "the_four_outcomes": ("STEP, LINEAR, UNRESOLVED, NEITHER, with bands [0.900, 1.100] and "
                              "[1.329, 1.624], stand as declared in record 27. 1.476364 falls in "
                              "the LINEAR band exactly as 1.4764 did."),
        "the_reading_of_the_present_data": ("NGC k=0 at A3/A1 = 2.78 remains consistent with a pure "
                                            "even quadratic at 2.18; SGC still changes sign, which "
                                            "an even function cannot do. Unchanged."),
    },
    "the_gate_of_record_27_is_worthless_and_that_is_separate": {
        "what_record_27_declared": ("That at both new points the `derived` gauge must reproduce the "
                                    "fiducial exactly, calling it a blocking gate at tolerance "
                                    "zero."),
        "why_it_cannot_fail": (
            "src/paper2_item13_rev2.py, lines 283-287, states it: under the constant-cube gauge a "
            "pure isotropic dilation is the IDENTITY by construction - imposing L = L_fid on "
            "f = A r gives A E + 2p = E + 2p, hence A = 1 exactly. 'A1 and A3 become the fiducial "
            "point. It is not a loss, it is Proposition 2 made manifest by the gauge.' A gate that "
            "algebra guarantees is not a gate."),
        "what_it_means_for_the_measurement": (
            "The block-A residuals that record 27 sets out to decompose do NOT live in the "
            "`derived` gauge, where they are zero by construction. They live in `regauged`, where "
            "the cube is not forced to the fiducial. The even/odd decomposition is declared HERE to "
            "be computed on the `regauged` gauge; on `derived` it would measure zero and mean "
            "nothing."),
        "a_real_gate_in_its_place": ("At both new points, in gauge `derived`, N_H1 must equal the "
                                     "fiducial - 23790 / 28256 in NGC, 12011 / 15122 in SGC. It "
                                     "cannot fail on the geometry, but it CAN fail if the point is "
                                     "malformed, if alpha_iso does not reach deform(), or if the "
                                     "new entry is read in the wrong column. It is kept for that, "
                                     "and it is described as what it is: a wiring check, not a test "
                                     "of the physics."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not move any threshold of record 27, and "
                              "does not change its four outcomes."),
}

REASON = (
    "Record 27 gives the wrong alphas for the two new block-A points, and describes its gate as "
    "something it is not. Both are corrected before any code is written, so no point has been "
    "generated from the wrong values. "
    "THE ALPHAS. LINE_A is defined in src/paper2_item13a_15a.py as [('A1', 0.9725), ('A3', "
    "1.0406)]. Record 27 did not read that line: it inverted the c printed by the runner, assuming "
    "c = 1/alpha. But c is the re-gauge factor and for a pure dilation with padding it is "
    "(E + 2p)/(alpha E + 2p); the padding is what breaks the inversion. The mirrors are therefore "
    "1.0275 and 0.9594, not 1.027362320997 and 0.959603267595 - errors of 1.38e-04 and 2.03e-04. "
    "Record 27's claim that the mirrors match their partners to 0.00e+00 is false with its own "
    "values and TRUE with the corrected ones, which is how the error was found. "
    "AND c IS NOT RECORDED AT ALL. Record 27 hard-coded it for both points; it should not have, "
    "because deform() derives c from alpha_iso for every point on the grid. A second place where a "
    "derived quantity lives is the defect class that produced 445 against 313. LINE_A carries the "
    "name and alpha_iso, and nothing else. "
    "EVERY CONCLUSION OF RECORD 27 SURVIVES. r = 1.476364 against 1.4764 declared, the even "
    "confounder 2.1796 against 2.18, A1m inside the physical range and A3m outside. The four "
    "outcomes and their bands stand; 1.476364 falls in LINEAR exactly as 1.4764 did. "
    "SEPARATELY, THE GATE OF RECORD 27 IS WORTHLESS AS DESCRIBED. paper2_item13_rev2.py states that "
    "under the constant-cube gauge a pure dilation is the identity by construction: A E + 2p = "
    "E + 2p gives A = 1 exactly, and 'A1 and A3 become the fiducial point'. A gate that algebra "
    "guarantees cannot fail. It is kept as a WIRING CHECK - it still catches a malformed point or "
    "an alpha_iso that never reaches deform() - and it is described as that. The consequence "
    "matters more: the block-A residuals live in the `regauged` gauge, not in `derived` where they "
    "are zero by construction, so the even/odd decomposition is declared here to be computed on "
    "`regauged`."
)

EVIDENCE = (
    "src/paper2_item13a_15a.py line 77: LINE_A = [('A1', 0.9725), ('A3', 1.0406)]. Line 327 builds "
    "the plan as dict(kind='ap', alpha_iso=al, F_ap=1.0) from those entries, and "
    "src/paper2_runner_fase3.py line 214 reads I13.LINE_A. "
    "Mirrors from the true entries: 1 + 0.0275 = 1.0275 and 1 - 0.0406 = 0.9594; |alpha - 1| "
    "matches its partner to 1.11e-16 and 0.00e+00. Against record 27's values the differences are "
    "1.38e-04 and 2.03e-04. "
    "Amplitude ratio 0.0406/0.0275 = 1.476364; square 2.1796. Physical isotropic range [0.9725, "
    "1.0406]: 1.0275 inside, 0.9594 below. "
    "Solving c = (E + 2p)/(alpha E + 2p) for E with alpha = 0.9725, c = 1.02813208 and 2p = 10 "
    "gives L_fid = E + 2p = 1997.55, against the frozen 1997.3629: the same quantity to the "
    "accuracy of the padding convention, which confirms that c is not 1/alpha. "
    "src/paper2_item13_rev2.py lines 283-287: 'la linea A collassa sul fiduciale. Per una "
    "dilatazione pura f = A r, imporre L = L_fid da' A*E + 2p = E + 2p, cioe' A = 1 ESATTO: A1 e A3 "
    "diventano il punto fiduciale. Non e' una perdita, e' la Proposizione 2 resa manifesta dal "
    "gauge.' "
    "results/paper2/fase3.jsonl: A1 and A3 in gauge `derived` give 23790 / 28256 (NGC) and 12011 / "
    "15122 (SGC), the fiducial exactly; in gauge `regauged` they give the non-zero residuals that "
    "record 27 decomposes."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.12",
    "amends_records": [27],
    "grid_values_are_read_from_the_definition": ("A grid point's alpha_iso is read from LINE_A in "
                                                 "src/paper2_item13a_15a.py, never reconstructed "
                                                 "from a printed diagnostic. c, L and the box are "
                                                 "DERIVED and are not written into records."),
    "the_decomposition_is_on_regauged": ("The even/odd decomposition of the block-A residuals is "
                                         "computed on the `regauged` gauge. On `derived` a pure "
                                         "dilation is the identity by construction and the "
                                         "decomposition would measure zero."),
    "the_derived_gauge_check_is_a_wiring_check": ("It cannot fail on the geometry, because algebra "
                                                  "guarantees it. It is kept because it still "
                                                  "catches a malformed point or an alpha_iso that "
                                                  "never reaches deform(), and it is called what it "
                                                  "is."),
    "no_threshold_of_record_27_moves": ("The four outcomes, their bands and the amplitude ratio all "
                                        "stand. Only two numbers change, and they change before "
                                        "any point is generated."),
    "caught_before_any_run": ("No point has been generated from the wrong alphas and no measurement "
                              "rests on them."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not change the outcomes of record 27."),
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
    chk("6  idempotenza (marker 28 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 27 e' gia' nel registro", MARKER_27 in blob)

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
        chk("10 old_value cita i valori sbagliati e la frase falsa",
            ("1.027362320997" in rec["old_value"])
            and ("matches its partner to 0.00e+00" in rec["old_value"]))
        chk("11 la causa e' nominata: c non e' 1/alpha, e c'e' il padding",
            ("not 1/alpha" in rec["new_value"]["what_is_wrong"]["c_is_not_one_over_alpha"])
            and ("padding" in rec["new_value"]["what_is_wrong"]["c_is_not_one_over_alpha"]))
        chk("12 c NON e' scritto nel record, ed e' dichiarato perche'",
            ("445" in rec["new_value"]["the_corrected_points"]
                ["c_is_not_recorded_here_and_that_is_deliberate"])
            and "c" not in rec["new_value"]["the_corrected_points"]["A1m"]
            and "c" not in rec["new_value"]["the_corrected_points"]["A3m"])
        chk("13 nessuna conclusione del 27 cambia, ed e' elencato",
            ("No threshold moves" in rec["new_value"]["what_survives_unchanged"]["every_conclusion"])
            and ("stand as declared in record 27" in rec["new_value"]
                 ["what_survives_unchanged"]["the_four_outcomes"]))
        chk("13f il record 27 e' sulla riga 27 e si emenda il 27",
            (MARKER_27 in json.dumps(recs[26], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [27])
        chk("13g il cancello del 27 e' declassato a controllo di cablaggio",
            ("not a gate" in rec["new_value"]
                ["the_gate_of_record_27_is_worthless_and_that_is_separate"]["why_it_cannot_fail"])
            and ("wiring check" in rec["new_value"]
                 ["the_gate_of_record_27_is_worthless_and_that_is_separate"]
                 ["a_real_gate_in_its_place"])
            and ("called what it is" in rec["rules"]
                 ["the_derived_gauge_check_is_a_wiring_check"]))
        chk("13h la decomposizione e' dichiarata su REGAUGED, non su derived",
            ("`regauged`" in rec["rules"]["the_decomposition_is_on_regauged"])
            and ("identity by construction" in rec["rules"]
                 ["the_decomposition_is_on_regauged"]))
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
        A1, A3 = 0.9725, 1.0406           # LINE_A, letti dalla definizione
        P = rec["new_value"]["the_corrected_points"]
        # 1. gli specchi corretti sono esatti sui valori VERI
        if abs(abs(P["A1m"]["alpha_iso"] - 1) - abs(A1 - 1)) > 1e-12:
            bad.append("A1m")
        if abs(abs(P["A3m"]["alpha_iso"] - 1) - abs(A3 - 1)) > 1e-12:
            bad.append("A3m")
        # 2. e quelli del record 27 NON lo erano: l'errore e' reale
        if abs(abs(1.027362320997 - 1) - abs(A1 - 1)) < 1e-6:
            bad.append("errore del 27 non dimostrato")
        # 3. dentro / fuori range
        if not (A1 <= P["A1m"]["alpha_iso"] <= A3):
            bad.append("A1m fuori")
        if A1 <= P["A3m"]["alpha_iso"] <= A3:
            bad.append("A3m dentro")
        # 4. le conclusioni del 27 reggono coi numeri veri
        r = abs(A3 - 1) / abs(A1 - 1)
        if abs(r - 1.4764) > 5e-4 or abs(r ** 2 - 2.18) > 0.01:
            bad.append("conclusioni")
        if not (1.329 <= r <= 1.624):
            bad.append("r fuori dalla banda LINEAR")
        # 5. c non compare fra le chiavi dei punti
        if any("c" == k for p in P.values() if isinstance(p, dict) for k in p):
            bad.append("c scritto nel record")
        chk("14 aritmetica: specchi esatti a 1e-12, errore del 27 reale, "
            "conclusioni invariate, c assente", not bad,
            ",".join(bad) if bad else "nove controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend28 rev.1 ===")
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
        fail("il record 28 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

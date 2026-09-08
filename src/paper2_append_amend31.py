#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend31.py  (rev. 1) — Emendamento 31: TURNOVER su entrambe le regole,
e la predizione a potenza e' falsificata.

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

AMEND_POSITION = 31                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 30

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

MARKER = "emendamento-31-blocco-a-turnover"
MARKER_30 = "emendamento-30-blocco-a-terza-ampiezza"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "block_a_turnover_found_and_the_power_law_prediction_falsified"

JSON_PATH = ("amendments record 30 (declared_prediction; the_quantitative_prediction); "
             "referee report section 6")

OLD_VALUE = (
    "Record 30 adds a third block-A amplitude at |alpha - 1| = 0.018627 and declares: rho_low = "
    "|part(a0)|/|part(a1)|, median over four cases, applied SEPARATELY to even and odd, with "
    "TURNOVER at <= 0.75, STILL_GROWING at >= 1.25, FLAT between, and SIGN_CHANGE excluded from the "
    "median and counted. It also declares a quantitative prediction: the power law fitted on the "
    "two existing amplitudes, with exponents -1.51, -2.16 and -2.60, continued to a0 predicts "
    "|even| = 32.4, 75.4 and 15.1; and it states that this extrapolation MUST fail somewhere, the "
    "question being whether it has already failed by 0.018627."
)

NEW_VALUE = {
    "the_verdict": {
        "even": {"rho_per_case": {"NGC_k1": 1.0278, "NGC_k0": 0.7231,
                                  "SGC_k1": 0.636, "SGC_k0": 0.0625},
                 "median": 0.6797, "outcome": "TURNOVER"},
        "odd": {"rho_per_case": {"NGC_k1": 0.3235, "NGC_k0": 0.4043,
                                 "SGC_k1": 0.4074, "SGC_k0": 0.3864},
                "median": 0.3953, "outcome": "TURNOVER"},
        "no_sign_changes": ("No case changes sign between a0 and a1, so the SIGN_CHANGE branch of "
                            "record 30 is not used and both medians are over all four cases."),
        "the_two_independent_rules_agree": ("Record 30 declared them separately and stated that a "
                                            "disagreement would be a result. They agree: TURNOVER "
                                            "and TURNOVER."),
    },
    "the_quantitative_prediction_is_falsified": {
        "predicted": {"NGC_k1": 32.4, "NGC_k0": 75.4, "SGC_k1": 15.1},
        "measured": {"NGC_k1": 18.5, "NGC_k0": 23.5, "SGC_k1": 3.5},
        "overestimate_factors": [1.8, 3.2, 4.3],
        "reading": ("Record 30 declared that the negative power law MUST fail somewhere, because it "
                    "diverges as a -> 0 while the residual is zero at a = 0. It has failed already "
                    "at the first amplitude below, and by factors of 1.8 to 4.3. The extrapolation "
                    "was not merely wrong in the limit: it is wrong immediately."),
        "this_is_a_falsification_and_is_recorded_as_one": ("The prediction was declared before the "
                                                           "run with its numbers. It is not "
                                                           "repaired and no exponent is refitted to "
                                                           "make it agree."),
    },
    "the_shape": {
        "what_the_three_amplitudes_show": (
            "The residual rises from zero, peaks, and falls. Odd, NGC k=1: 5.5 -> 17.0 -> 7.0 "
            "across 0.0186, 0.0275, 0.0406, a clean maximum at the middle amplitude. Odd is "
            "consistent across all four cases: 5.5/9.5/5.5/8.5 at a0 against 17.0/23.5/13.5/22.0 at "
            "a1. Even is flatter and in NGC k=1 is almost unchanged between a0 and a1, 18.5 against "
            "18.0, before falling to 10.0."),
        "the_characteristic_scale": ("The maximum sits near |alpha - 1| = 0.02 to 0.03. On a "
                                     "128-voxel cube that is a displacement of about 2 to 3 voxels "
                                     "at the boundary."),
        "what_it_is_consistent_with": ("A grid-registration effect on that scale. It is NOT "
                                       "consistent with the 'constant offset' the Phase-3 report "
                                       "assumed, which record 29 already withdrew, nor with a "
                                       "monotone discretisation artefact, which would grow with the "
                                       "deformation."),
        "what_is_not_established": ("That the mechanism IS grid registration. Three amplitudes give "
                                    "a shape and a scale; they do not identify a cause. The "
                                    "consistency is stated as consistency."),
    },
    "one_number_that_must_not_be_quoted": {
        "which": "SGC k=0, even part, rho_low = 0.0625.",
        "why": ("The even part there is -0.5 at a0, -8.0 at a1 and exactly 0.0 at a2: it changes "
                "direction twice and is small everywhere. A ratio of 0.062 formed from -0.5 and "
                "-8.0 is not a measurement of shape, it is discretisation noise on integers."),
        "does_it_affect_the_verdict": ("No. The median is 0.6797 and would be 0.6797 without it as "
                                       "the second of three; the other three cases carry it. But "
                                       "the number itself is not quoted, and the even verdict rests "
                                       "on 0.723, 0.636 and 1.028."),
        "declared_now_and_not_used": ("No threshold was declared on individual cases, only on the "
                                      "median, so excluding it after the fact is not available and "
                                      "is not done. It is included in the median as the rule "
                                      "requires and flagged as unquotable."),
    },
    "for_the_referee_section_6": {
        "what_is_now_established": ("The odd response in SGC is real - symmetric pairs remove the "
                                    "sampling confounder, record 29 - and it has a SHAPE: it rises "
                                    "from zero, peaks near 2 to 3 per cent in alpha, and falls. It "
                                    "is not a constant offset and not a monotone artefact."),
        "what_is_still_not": ("Its cause. The referee asked that 'an observation, not a result' be "
                              "replaced by something stronger; it now is - a measured shape with a "
                              "scale - but the mechanism is not named."),
        "the_honest_summary_for_the_response": ("Six points on line A, three symmetric amplitudes, "
                                                "in a regime where Proposition 2 says the signal is "
                                                "exactly zero. The residual is non-zero, peaks at a "
                                                "scale of a few voxels of boundary displacement, "
                                                "and falls on either side. That is what is known."),
    },
    "consequences": {
        "the_floor_f": ("Term (f) is the rms of the block-A residuals, currently two of them. There "
                        "are now SIX, at three amplitudes, and they are not a constant: the floor "
                        "depends on which amplitude is used. This is a change to the budget and is "
                        "NOT decided here - records 27 and 29 both deferred it and it stays "
                        "deferred, because deciding it now would mean choosing the amplitude after "
                        "seeing the numbers."),
        "ddmax_and_the_verdict": ("Unchanged. Line A does not enter DDmax and E1-E4 is not "
                                  "reopened."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not move any threshold of record 30, and "
                              "does not re-derive the floor."),
}

REASON = (
    "The third block-A amplitude has been measured. Both declared rules give TURNOVER, and the "
    "declared quantitative prediction is falsified. "
    "THE VERDICT. rho_low = |part(a0)|/|part(a1)|: even 1.0278, 0.7231, 0.6364, 0.0625 with median "
    "0.6797; odd 0.3235, 0.4043, 0.4074, 0.3864 with median 0.3953. Both fall in TURNOVER, at <= 0.75. "
    "No case changes sign, so the SIGN_CHANGE branch is unused and both medians run over all four. "
    "Record 30 declared the two rules separately and said a disagreement would be a result: they "
    "agree. "
    "THE QUANTITATIVE PREDICTION IS FALSIFIED. The power law continued from the two known "
    "amplitudes predicted |even| = 32.4, 75.4 and 15.1 at a0; the measurement gives 18.5, 23.5 and "
    "3.5, overestimates by factors of 1.8, 3.2 and 4.3. Record 30 declared that this extrapolation "
    "MUST fail somewhere; it fails at the FIRST amplitude below, not in the limit. It is not "
    "repaired and no exponent is refitted. "
    "THE SHAPE. The residual rises from zero, peaks, and falls. The odd part is consistent across "
    "all four cases - 5.5, 9.5, 5.5, 8.5 at a0 against 17.0, 23.5, 13.5, 22.0 at a1 - with a clean "
    "maximum at the middle amplitude. The maximum sits near |alpha - 1| = 0.02 to 0.03, which on a "
    "128-voxel cube is a boundary displacement of two to three voxels. That is CONSISTENT WITH a "
    "grid-registration effect and inconsistent both with the 'constant offset' record 29 withdrew "
    "and with a monotone discretisation artefact. It does not identify the mechanism: three "
    "amplitudes give a shape and a scale, not a cause. "
    "ONE NUMBER MUST NOT BE QUOTED. SGC k=0, even, rho_low = 0.062, formed from -0.5 and -8.0 on a "
    "part that is small everywhere and changes direction twice. That is discretisation noise on "
    "integers, not a shape. It does not move the median and the even verdict rests on the other "
    "three; but it is flagged, and it is NOT excluded after the fact, because record 30 declared a "
    "threshold on the median and not on individual cases."
)

EVIDENCE = (
    "results/paper2/fase3.jsonl, gauge `regauged`, six line-A points against the fiducials 23790 / "
    "28256 (NGC) and 12011 / 15122 (SGC). "
    "A0 (alpha 0.981373, compression) and A0m (alpha 1.018627, expansion): NGC k=1 23803 and 23814; "
    "NGC k=0 28270 and 28289; SGC k=1 12002 and 12013; SGC k=0 15113 and 15130. In gauge `derived` "
    "both reproduce the fiducial exactly, which record 28 declares to be algebra. "
    "Even and odd at the three amplitudes 0.018627 / 0.0275 / 0.0406: "
    "NGC k=1 even 18.5 / 18.0 / 10.0, odd 5.5 / 17.0 / 7.0; "
    "NGC k=0 even 23.5 / 32.5 / 14.0, odd 9.5 / 23.5 / 11.0; "
    "SGC k=1 even -3.5 / -5.5 / -2.0, odd 5.5 / 13.5 / 13.0; "
    "SGC k=0 even -0.5 / -8.0 / 0.0, odd 8.5 / 22.0 / 30.0. "
    "rho_low even: 1.0278, 0.7231, 0.6364, 0.0625, median 0.6797. Odd: 0.3235, 0.4043, 0.4074, 0.3864, "
    "median 0.3953. Record 30's bands: TURNOVER <= 0.75, FLAT to 1.25, STILL_GROWING above. "
    "Record 30's power-law predictions at a0: 32.4, 75.4, 15.1 against 18.5, 23.5, 3.5 measured."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.12; referee report section 6",
    "amends_records": [],
    "a_declared_prediction_was_falsified_and_stays_so": ("The power-law extrapolation of record 30 "
                                                         "predicted 32.4, 75.4 and 15.1 and the "
                                                         "measurement gives 18.5, 23.5 and 3.5. "
                                                         "Falsified, not repaired, and no exponent "
                                                         "is refitted."),
    "the_unquotable_number_is_flagged_not_removed": ("SGC k=0 even, rho 0.0625, stays in the median "
                                                     "because record 30 declared the threshold on "
                                                     "the median. It is flagged as not quotable and "
                                                     "supports no statement."),
    "shape_and_scale_are_established_the_cause_is_not": ("Three amplitudes give a maximum near 2 to "
                                                         "3 per cent in alpha. Consistency with "
                                                         "grid registration is stated as "
                                                         "consistency, not as identification."),
    "the_floor_stays_deferred": ("There are now six block-A residuals at three amplitudes and the "
                                 "floor depends on which is used. Deciding now would mean choosing "
                                 "the amplitude after seeing the numbers. Deferred, as in records "
                                 "27 and 29."),
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
    chk("6  idempotenza (marker 31 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 30 e' gia' nel registro", MARKER_30 in blob)

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
        chk("10 old_value cita la regola e la predizione quantitativa del 30",
            ("TURNOVER at <= 0.75" in rec["old_value"])
            and ("32.4, 75.4 and 15.1" in rec["old_value"]))
        chk("11 le due regole indipendenti concordano, ed e' dichiarato",
            rec["new_value"]["the_verdict"]["even"]["outcome"] == "TURNOVER"
            and rec["new_value"]["the_verdict"]["odd"]["outcome"] == "TURNOVER"
            and ("They agree" in rec["new_value"]["the_verdict"]
                 ["the_two_independent_rules_agree"]))
        chk("12 la predizione quantitativa e' FALSIFICATA e non riparata",
            (rec["new_value"]["the_quantitative_prediction_is_falsified"]
             ["overestimate_factors"] == [1.8, 3.2, 4.3])
            and ("no exponent is refitted" in rec["rules"]
                 ["a_declared_prediction_was_falsified_and_stays_so"]))
        chk("13 il numero non citabile e' segnalato ma NON tolto dalla mediana",
            ("0.0625" in rec["new_value"]["one_number_that_must_not_be_quoted"]["which"])
            and ("is not done" in rec["new_value"]["one_number_that_must_not_be_quoted"]
                 ["declared_now_and_not_used"])
            and ("stays in the median" in rec["rules"]
                 ["the_unquotable_number_is_flagged_not_removed"]))
        chk("13f il record 30 e' sulla riga 30",
            MARKER_30 in json.dumps(recs[29], ensure_ascii=False))
        chk("13g forma e scala stabilite, causa NO, e distinte",
            ("does not identify the mechanism" in rec["reason"]
             or "not identify a cause" in rec["new_value"]["the_shape"]
             ["what_is_not_established"])
            and ("not as identification" in rec["rules"]
                 ["shape_and_scale_are_established_the_cause_is_not"]))
        chk("13h il pavimento resta rinviato, e si dice perche'",
            ("choosing the amplitude after seeing the numbers" in rec["new_value"]
                ["consequences"]["the_floor_f"])
            and ("Deferred" in rec["rules"]["the_floor_stays_deferred"]))
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
        # (comp, esp) alle tre ampiezze: a0, a1, a2
        RAW = {"NGC_k1": ((23803, 23814), (23791, 23825), (23793, 23807)),
               "NGC_k0": ((28270, 28289), (28265, 28312), (28259, 28281)),
               "SGC_k1": ((12002, 12013), (11992, 12019), (11996, 12022)),
               "SGC_k0": ((15113, 15130), (15092, 15136), (15092, 15152))}
        V = rec["new_value"]["the_verdict"]
        rl_e, rl_o = [], []
        for nm, tri in RAW.items():
            f = FID[nm]
            pe, po = [], []
            for c, e in tri:
                pe.append(((e - f) + (c - f)) / 2.0)
                po.append(((e - f) - (c - f)) / 2.0)
            re_, ro_ = abs(pe[0]) / abs(pe[1]), abs(po[0]) / abs(po[1])
            rl_e.append(re_)
            rl_o.append(ro_)
            if abs(V["even"]["rho_per_case"][nm] - re_) > 5e-4:
                bad.append(nm + "/pari")
            if abs(V["odd"]["rho_per_case"][nm] - ro_) > 5e-4:
                bad.append(nm + "/dispari")
            # nessun cambio di segno: e' quel che il record afferma
            if pe[0] * pe[1] < 0 or po[0] * po[1] < 0:
                bad.append(nm + "/segno")
        if abs(_st.median(rl_e) - V["even"]["median"]) > 5e-4:
            bad.append("mediana pari")
        if abs(_st.median(rl_o) - V["odd"]["median"]) > 5e-4:
            bad.append("mediana dispari")
        # entrambe devono cadere in TURNOVER, cioe' <= 0.75
        if not (_st.median(rl_e) <= 0.75 and _st.median(rl_o) <= 0.75):
            bad.append("non TURNOVER")
        # e la predizione a potenza deve essere davvero smentita
        Q = rec["new_value"]["the_quantitative_prediction_is_falsified"]
        for nm in ("NGC_k1", "NGC_k0", "SGC_k1"):
            f = round(Q["predicted"][nm] / Q["measured"][nm], 1)
            if f not in Q["overestimate_factors"]:
                bad.append(nm + "/fattore")
        chk("14 aritmetica: pari e dispari dai grezzi, mediane, nessun cambio "
            "di segno, TURNOVER, predizione smentita", not bad,
            ",".join(bad) if bad else "ventitre controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend31 rev.1 ===")
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
        fail("il record 31 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

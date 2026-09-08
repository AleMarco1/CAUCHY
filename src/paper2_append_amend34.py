#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend34.py  (rev. 1) — Emendamento 34: la deroga D5c diventa una
CONDIZIONE, e il pavimento a sei punti richiede un run mock.

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

AMEND_POSITION = 34                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 33

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

MARKER = "emendamento-34-deroga-a-condizione-e-blocco-a-mock"
MARKER_33 = "emendamento-33-rettifica-regola-pavimento"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "d5c_derogation_bound_to_a_condition_and_the_block_a_mock_run"

JSON_PATH = ("amendments record 23 (the_derogation.what); "
             "amendments records 32 and 33 (the six block-A points)")

OLD_VALUE = (
    "Record 23 grants the D5c derogation to two NAMED runs: 'For the §3.8 real-space run and for "
    "the treatment (B) run, D5c operates in MEASURE mode.' Records 32 and 33 define term (f) over "
    "'the SIX block-A points', with record 33 setting it to max |b_residual| over them, on the "
    "assumption that those residuals would be available once the four new points had been run."
)

NEW_VALUE = {
    "the_planning_error_is_mine": {
        "what_was_assumed": ("That running A0, A1m, A3m and A0m on the DATA side would make the six "
                             "block-A residuals available to the budget."),
        "why_it_is_false": ("paper2_fase3_budget.py gather() builds the block-A rows from the MOCK "
                            "side: its own comment says the block-A Delta D 'is in no register: it "
                            "is computed from the mock side, paired mean minus the DESI "
                            "difference'. The mock side has only the original twelve points, which "
                            "include A1 and A3 and not the four new ones."),
        "the_consequence": ("The floor now computed is the MAXIMUM OVER TWO POINTS - the rule "
                            "change alone, without the new points. It is 10.27, 18.07, 26.35 and "
                            "33.54 against the deposited 10.1, 17.7, 20.2 and 32.5, and it is NOT "
                            "the six-point floor of records 32 and 33."),
        "how_it_will_read_until_the_run": ("Any quotation of the floor before the mock run must say "
                                           "'maximum over the two deposited points', not 'over the "
                                           "six'. Records 32 and 33 are not amended in their rule; "
                                           "what is corrected is the assumption that the rule was "
                                           "already computable."),
        "it_cost_no_measurement": ("The gate of record 33 passed - the rms over {A1, A3} reproduces "
                                   "10.12, 17.73, 20.16 and 32.47 - so the existing computation is "
                                   "intact. The error cost a wrong expectation, not a wrong "
                                   "number."),
    },
    "what_the_two_point_floor_already_shows": {
        "it_rose_everywhere_as_guaranteed": ("10.1 -> 10.27, 17.7 -> 18.07, 20.2 -> 26.35, 32.5 -> "
                                             "33.54. max >= rms holds in every case, as record 33 "
                                             "proves it must."),
        "sgc_k1_moves_by_30_per_cent": ("Its two residuals are +26.3 and -10.9: the rms averages "
                                        "them to 20.2, the maximum takes the larger. This is the "
                                        "case where the rule bites, and it bites in the declared "
                                        "direction - the systematic gets worse, not better."),
        "what_changes_in_the_reported_text": ("The sentence 'of these, at least X are MEASURED "
                                              "artefact' takes the new floor: 26.3 instead of 20.2 "
                                              "in SGC k=1. The quoted sigma_sys on term (b) is "
                                              "built from the unattributed residual and does not "
                                              "move."),
    },
    "the_derogation_is_rebound_to_a_condition": {
        "what_record_23_did": ("Granted MEASURE mode to two runs BY NAME. A third run now needs it, "
                              "and D5C_MODE is a module constant so it would apply anyway - which "
                              "is precisely why the perimeter must be restated rather than "
                              "silently exceeded."),
        "the_new_binding": ("D5c operates in MEASURE mode for ALL runs until the threshold is "
                            "declared on the observed distribution. It is a CONDITION, not a list, "
                            "so a further run does not need a further record."),
        "why_a_condition_is_safer_than_a_list": ("A list is exceeded silently the first time "
                                                 "someone runs something not on it. A condition "
                                                 "cannot be exceeded: it ends when the threshold is "
                                                 "declared, and until then it covers everything by "
                                                 "construction."),
        "the_four_protections_are_unchanged": [
            "n_clipped is written into EVERY record, in both modes",
            "no result from any run under the derogation is quoted until the threshold is declared "
            "on the observed distribution and applied to those same records",
            "D5C_MODE is a constant in the source, not a command-line flag",
            "the code prints the mode at every run and every smoke",
        ],
        "and_the_end_condition_is_restated": ("When the threshold is declared, D5C_MODE returns to "
                                              "'block' and a record states the threshold, its "
                                              "derivation from the observed distribution, and which "
                                              "points if any it excludes."),
    },
    "the_run": {
        "what": ("A0, A1m, A3m and A0m on the MOCK side, N = 200, both hemispheres, into "
                 "results/paper2/fase3_mock.jsonl."),
        "why_the_main_register_and_not_a_separate_one": ("gather() reads the block-A rows from "
                                                         "fase3_mock.jsonl. These are grid points, "
                                                         "added by amendment as B6 was, not a "
                                                         "diagnostic - and the resumption key "
                                                         "includes the point set, so the existing "
                                                         "records are untouched, exactly as the "
                                                         "B6-only records of amendment 15."),
        "cost": "four points x 200 realisations x two hemispheres, of order eight hours.",
        "when": ("After the §3.8 run finishes. It is a mock run and does not share the machine with "
                 "another."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not change the floor rule of record 33, and "
                              "does not relax D5c on the data side, where record 13 point (c) still "
                              "forbids any clipped object with a hard stop."),
}

REASON = (
    "The D5c derogation is rebound from a list of named runs to a condition, and a planning error of "
    "mine is registered. "
    "THE ERROR. Records 32 and 33 define term (f) over the SIX block-A points, on the assumption "
    "that running A0, A1m, A3m and A0m on the DATA side would make those residuals available. It "
    "does not: gather() in paper2_fase3_budget.py builds the block-A rows from the MOCK side - its "
    "own comment says the block-A Delta D 'is computed from the mock side, paired mean minus the "
    "DESI difference' - and the mock side has only the original twelve points. The floor now "
    "computed is therefore the MAXIMUM OVER TWO POINTS, the rule change without the new points: "
    "10.27, 18.07, 26.35 and 33.54 against the deposited 10.1, 17.7, 20.2 and 32.5. Until the mock "
    "run, any quotation of the floor says 'over the two deposited points', not 'over the six'. The "
    "rule of record 33 is not amended; what is corrected is the assumption that it was already "
    "computable. The gate of record 33 passed - the rms over {A1, A3} gives 10.12, 17.73, 20.16 and "
    "32.47 - so the error cost a wrong expectation, not a wrong number. "
    "WHAT THE TWO-POINT FLOOR ALREADY SHOWS. It rose in every case, as max >= rms guarantees. SGC "
    "k=1 rises by 30 per cent, from 20.2 to 26.35, because its residuals are +26.3 and -10.9 and "
    "the maximum takes the larger where the rms averages them. That is the case where the rule "
    "bites, and it bites in the declared direction: the systematic gets worse. "
    "THE DEROGATION. Record 23 granted MEASURE mode to two runs BY NAME. This is a third, and "
    "D5C_MODE is a module constant so it would apply anyway - which is exactly why the perimeter is "
    "restated rather than silently exceeded. It is now bound to a CONDITION: D5c measures for ALL "
    "runs until the threshold is declared on the observed distribution. A list is exceeded silently "
    "the first time someone runs something not on it; a condition cannot be, and it ends when the "
    "threshold is declared. The four protections of record 23 are unchanged and restated."
)

EVIDENCE = (
    "src/paper2_fase3_budget.py gather(), comment before the block-A section: 'Il blocco A non e' in "
    "per_point del 3.4 ... Il suo Delta D non e' in nessun registro: si calcola dal lato mock, con "
    "la stessa definizione del 3.4 - media appaiata meno differenza DESI, esatta.' "
    "Run of 2 Sep 2026 after the floor patch: '(f) pavimento = 10.27 su 2 punti, determinato da A3 "
    "[rms coppia depositata 10.12 contro 10.1]'; 18.07 su 2 punti da A1 [17.73 contro 17.7]; 26.35 "
    "su 2 punti da A1 [20.16 contro 20.2]; 33.54 su 2 punti da A1 [32.47 contro 32.5]. The gate of "
    "record 33 passed in all four cases. "
    "Block-A residuals printed in the same run: NGC k=1 A1 -10.0 and A3 -10.3; SGC k=1 A1 +26.3 and "
    "A3 -10.9. "
    "results/paper2/fase3_mock.jsonl contains the twelve original points; A0, A1m, A3m and A0m were "
    "run only through src/paper2_runner_fase3.py, the data-side runner. "
    "Record 23: 'For the §3.8 real-space run and for the treatment (B) run, D5c operates in MEASURE "
    "mode', with D5C_MODE a module constant in paper2_runner_fase3_mock.py."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, items 3.12 and 3.13",
    "amends_records": [23, 32, 33],
    "the_derogation_is_a_condition_not_a_list": ("D5c measures for ALL runs until the threshold is "
                                                 "declared on the observed distribution. No further "
                                                 "record is needed for a further run, and the "
                                                 "perimeter cannot be exceeded silently."),
    "the_floor_is_over_two_points_until_the_mock_run": ("Any quotation of term (f) before the "
                                                        "block-A mock run says 'maximum over the "
                                                        "two deposited points'. The six-point floor "
                                                        "of records 32 and 33 does not exist yet."),
    "the_rule_of_record_33_is_not_amended": ("max |b_residual| over the available block-A points "
                                             "stands. What was wrong was the assumption that six "
                                             "were available."),
    "block_a_mock_goes_to_the_main_register": ("fase3_mock.jsonl, because gather() reads it and "
                                               "these are grid points added by amendment, not a "
                                               "diagnostic. The resumption key includes the point "
                                               "set, so existing records are untouched."),
    "the_data_side_is_not_relaxed": ("Record 13 point (c) still forbids any clipped object on the "
                                     "data side with a hard stop. The derogation is mock-side "
                                     "only."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not change the floor rule."),
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
    chk("6  idempotenza (marker 34 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 33 e' gia' nel registro", MARKER_33 in blob)

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
        chk("10 old_value cita la deroga a DUE run nominati e i sei punti",
            ("§3.8 real-space run and for the treatment (B) run" in rec["old_value"])
            and ("SIX block-A points" in rec["old_value"]))
        chk("11 l'errore di pianificazione e' MIO ed e' nominato",
            ("the_planning_error_is_mine" in rec["new_value"])
            and ("of mine is registered" in rec["reason"])
            and ("from the MOCK side" in rec["new_value"]["the_planning_error_is_mine"]
                 ["why_it_is_false"]))
        chk("12 e' dichiarato che il pavimento e' su DUE punti, non sei",
            ("MAXIMUM OVER TWO POINTS" in rec["new_value"]
                ["the_planning_error_is_mine"]["the_consequence"])
            and ("over the two deposited points" in rec["rules"]
                 ["the_floor_is_over_two_points_until_the_mock_run"]))
        chk("13 la deroga e' una CONDIZIONE, e si dice perche' non una lista",
            ("CONDITION, not a list" in rec["new_value"]
                ["the_derogation_is_rebound_to_a_condition"]["the_new_binding"])
            and ("exceeded silently" in rec["new_value"]
                 ["the_derogation_is_rebound_to_a_condition"]
                 ["why_a_condition_is_safer_than_a_list"]))
        chk("13f il record 33 e' sulla riga 33 e si emendano 23, 32, 33",
            (MARKER_33 in json.dumps(recs[32], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [23, 32, 33])
        chk("13g le quattro protezioni del 23 sono ripetute, non solo citate",
            len(rec["new_value"]["the_derogation_is_rebound_to_a_condition"]
                ["the_four_protections_are_unchanged"]) == 4)
        chk("13h il lato dati NON e' rilassato, e la fine della deroga e' data",
            ("mock-side only" in rec["rules"]["the_data_side_is_not_relaxed"])
            and ("returns to" in rec["new_value"]
                 ["the_derogation_is_rebound_to_a_condition"]
                 ["and_the_end_condition_is_restated"]))
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
        rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
        # 1. il pavimento a due punti e' davvero il MASSIMO dei due, e supera
        #    la rms: e' quel che il run ha stampato e va ricalcolato.
        RES = {"NGC_k1": (-10.0, -10.3), "SGC_k1": (26.3, -10.9)}
        ATT = {"NGC_k1": 10.27, "SGC_k1": 26.35}
        for nm, v in RES.items():
            mx = max(abs(x) for x in v)
            if abs(mx - ATT[nm]) > 0.35:
                bad.append(nm + "/massimo")
            if mx < rms(v):
                bad.append(nm + "/max<rms")
        # 2. SGC k=1 sale del ~30%: e' il caso in cui la regola morde
        if not (1.25 < 26.35 / 20.2 < 1.35):
            bad.append("SGC k1 non sale del 30%")
        # 3. e negli altri il movimento e' piccolo: la regola non stravolge
        for dep, new in ((10.1, 10.27), (17.7, 18.07), (32.5, 33.54)):
            if not (1.0 <= new / dep < 1.06):
                bad.append("movimento anomalo %.1f->%.2f" % (dep, new))
        # 4. il cancello del record 33 e' passato in tutti e quattro
        GATE = ((10.12, 10.1), (17.73, 17.7), (20.16, 20.2), (32.47, 32.5))
        for got, exp in GATE:
            if abs(got - exp) > 0.1:
                bad.append("cancello %.2f vs %.1f" % (got, exp))
        chk("14 aritmetica: pavimento = max dei due, SGC k1 +30%%, gli altri "
            "<6%%, cancello passato quattro volte", not bad,
            ",".join(bad) if bad else "tredici controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend34 rev.1 ===")
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
        fail("il record 34 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend35.py  (rev. 1) — Emendamento 35: il run in spazio reale e' NULLO,
il flag non era collegato. Dodici ore, zero misure.

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

AMEND_POSITION = 35                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 34

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

MARKER = "emendamento-35-run-spazio-reale-nullo"
MARKER_34 = "emendamento-34-deroga-a-condizione-e-blocco-a-mock"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "the_real_space_run_was_null_the_flag_was_never_connected"

JSON_PATH = ("src/phase8_cutsky_mocks.py REAL_SPACE; "
             "src/paper2_runner_fase3_mock.py --real-space; "
             "results/paper2/fase3_mock_realspace.jsonl")

OLD_VALUE = (
    "The §3.8 real-space run of records 16 and 18 was executed on 1-2 Sep 2026, about twelve hours, "
    "400 records at results/paper2/fase3_mock_realspace.jsonl, each carrying real_space: true. The "
    "run was declared to measure Delta_mock with v_los set to zero, against the restated prediction "
    "of record 18."
)

NEW_VALUE = {
    "the_run_produced_nothing": {
        "the_finding": ("All 2400 comparable cells of fase3_mock_realspace.jsonl are IDENTICAL to "
                        "fase3_mock.jsonl. Not close: identical, integer for integer. "
                        "Delta_mock(B5-B1) reproduces -218.00, -172.30, -135.98 and -111.13 against "
                        "the redshift-space -218.0, -172.3, -136.0 and -111.1, ratio 1.000 in every "
                        "case."),
        "what_it_means": ("The --real-space flag had NO EFFECT. Twelve hours of machine time "
                          "reproduced a run that already existed."),
    },
    "the_defect": {
        "where": ("The §3.8 patch put REAL_SPACE as a MODULE variable in phase8_cutsky_mocks.py, "
                  "with 'if REAL_SPACE: v_los = np.zeros_like(v_los)' inside carve_cutsky, and "
                  "added --real-space to the runner, which writes it into the record and into the "
                  "resumption key. The line that CONNECTS the two - M.REAL_SPACE = True - was never "
                  "written. The flag is read, recorded and keyed on; phase8 stays at False."),
        "why_no_check_caught_it": ("The twenty-one checks of that patch verified that the flag "
                                   "existed, that it entered the key, that it entered the record, "
                                   "that v_los was zeroed INSIDE phase8, and that every name was "
                                   "bound. None verified that anything ever SETS the flag. It is "
                                   "the same shape of defect as _scrivi_intersezione, defined and "
                                   "never called, which was caught only because it happened to be "
                                   "looked for."),
        "why_the_smoke_could_not_catch_it": ("The smoke runs deliberately WITHOUT --real-space, to "
                                             "verify the flag is inert. It was inert in both "
                                             "directions, and the smoke cannot tell those apart."),
        "the_class_of_defect": ("A switch that is plumbed at both ends and connected in the middle "
                                "by nothing. Static checks see both ends and the wire that is "
                                "missing has no name to be absent."),
    },
    "the_register_asserts_something_false": {
        "what": ("The 400 records carry real_space: true, written by cmd_run from the argparse "
                 "namespace. They state they are real-space measurements and they are not."),
        "why_deleting_the_file_is_not_enough": ("The resumption key includes real_space, so a "
                                                "corrected relaunch would SKIP every realisation, "
                                                "believing them done. The register must be removed "
                                                "or renamed, not merely ignored."),
        "action": ("results/paper2/fase3_mock_realspace.jsonl is renamed to "
                   "fase3_mock_realspace_NULLO.jsonl and is not read by any analysis. It is kept, "
                   "not deleted: it is the evidence that the run was null, and it holds valid D5c "
                   "measurements."),
    },
    "what_survives_from_the_run": {
        "the_d5c_distribution": ("n_clipped does not depend on RSD, so the 2400 measurements are "
                                 "VALID. This is exactly the distribution record 23 required before "
                                 "the D5c threshold could be declared: mean 0.703, median 0, q90 = "
                                 "2, q99 = 4, q99.9 = 7, max 9, with 56.8 per cent of points at "
                                 "zero. Per hemisphere: NGC mean 1.006, q99 5, max 9; SGC mean "
                                 "0.401, q99 3, max 5."),
        "and_it_confirms_what_the_smoke_said": ("The count does not grow with the deformation: "
                                                "per-point means in NGC are 1.15, 1.02, 0.95, 0.96, "
                                                "0.96 and 1.00 at B1, B2, B4, B5, B6 and FID. The "
                                                "fiducial is in the middle of the range, not at the "
                                                "bottom."),
        "the_threshold_is_not_declared_here": ("Having the distribution does not make this the right "
                                               "record to declare the threshold in. That is a "
                                               "separate decision with its own reasoning, and "
                                               "bundling it with the report of a failed run would "
                                               "hide it."),
    },
    "what_this_costs": {
        "twelve_hours": "and the §3.8 answer, which is still not measured.",
        "the_response_document": ("Section §3.8 stays [IN ATTESA DI RUN]. Nothing written about it "
                                  "is withdrawn, because nothing was written: the section was never "
                                  "filled."),
        "no_result_was_contaminated": ("The null run wrote to a SEPARATE register, as records 16 and "
                                       "23 required. fase3_mock.jsonl was not touched, and no "
                                       "analysis read the null file. The separate-register "
                                       "discipline contained the damage to the time."),
    },
    "what_is_required_before_the_relaunch": {
        "the_missing_line": "M.REAL_SPACE = bool(getattr(a, 'real_space', False)) in the runner.",
        "a_check_on_the_CONNECTION_not_the_flag": ("The patch must verify that something SETS "
                                                   "REAL_SPACE, not that the flag exists. A static "
                                                   "check that the module attribute is assigned "
                                                   "somewhere."),
        "a_smoke_WITH_the_flag": ("The decisive check: run the smoke WITH --real-space and compare "
                                  "against the main run. It must FAIL IF THE NUMBERS MATCH. Every "
                                  "check so far was built to confirm inertness; this one is built "
                                  "to confirm effect."),
        "rule_adopted": ("A flag that changes a measurement is verified by a run that PRODUCES "
                         "DIFFERENT NUMBERS, not by inspection of the code path. Inertness and "
                         "disconnection are indistinguishable from the outside, and only a "
                         "difference tells them apart."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not declare the D5c threshold."),
}

REASON = (
    "The §3.8 real-space run produced nothing and is registered as null before anything is read from "
    "it. "
    "THE FINDING. All 2400 comparable cells of fase3_mock_realspace.jsonl are IDENTICAL, integer for "
    "integer, to fase3_mock.jsonl. Delta_mock(B5-B1) gives -218.00, -172.30, -135.98 and -111.13 "
    "against the redshift-space -218.0, -172.3, -136.0 and -111.1: ratio 1.000 in all four cases. "
    "The flag had no effect and twelve hours reproduced an existing run. "
    "THE DEFECT. REAL_SPACE is a module variable in phase8 and --real-space is a runner flag that "
    "enters the record and the resumption key. The line that connects them - M.REAL_SPACE = True - "
    "was never written. Twenty-one checks verified that the flag existed, entered the key, entered "
    "the record, zeroed v_los inside phase8, and that every name was bound; none verified that "
    "anything SETS it. It is the same shape as _scrivi_intersezione, defined and never called, which "
    "was caught only because it happened to be looked for. And the smoke could not catch it: the "
    "smoke runs WITHOUT the flag, to confirm inertness, and inertness and disconnection look the "
    "same from there. "
    "THE REGISTER ASSERTS SOMETHING FALSE. The 400 records carry real_space: true. Deleting the file "
    "is not enough, because the resumption key includes real_space and a corrected relaunch would "
    "skip every realisation. The file is RENAMED to fase3_mock_realspace_NULLO.jsonl and kept: it is "
    "the evidence, and it holds valid measurements. "
    "WHAT SURVIVES. n_clipped does not depend on RSD, so the 2400 D5c measurements are valid - and "
    "they are exactly the distribution record 23 required: mean 0.703, median 0, q99 = 4, max 9, 56.8 "
    "per cent at zero. The threshold is NOT declared here: bundling it with the report of a failed "
    "run would hide it. "
    "WHAT IT COST. Twelve hours and the §3.8 answer. No result was contaminated: the null run wrote "
    "to a separate register as records 16 and 23 required, fase3_mock.jsonl was untouched, and no "
    "analysis read the null file. "
    "THE RULE ADOPTED. A flag that changes a measurement is verified by a run that PRODUCES "
    "DIFFERENT NUMBERS, not by inspection of the code path. The relaunch requires a smoke WITH the "
    "flag that FAILS IF THE NUMBERS MATCH."
)

EVIDENCE = (
    "results/paper2/fase3_mock_realspace.jsonl: 400 records, 200 per hemisphere, six line-B points, "
    "erosions 0 and 1, every record carrying real_space: true. "
    "Cell-by-cell comparison with results/paper2/fase3_mock.jsonl on N_H1_k0: 2400 comparable cells, "
    "2400 identical, 0 different. Examples, NGC FID: 35318, 34971, 35526, 35708, 35418 in both files "
    "at indices 0 to 4. "
    "Paired Delta_mock(B5-B1) from the null file: -218.00 +/- 11.62 (NGC k=0), -172.30 +/- 11.25 "
    "(NGC k=1), -135.98 +/- 9.17 (SGC k=0), -111.13 +/- 8.71 (SGC k=1), against the redshift-space "
    "values -218.0, -172.3, -136.0, -111.1. "
    "src/phase8_cutsky_mocks.py: REAL_SPACE = False at module level, used in carve_cutsky. "
    "src/paper2_runner_fase3_mock.py: --real-space defined, written to rec['real_space'] and "
    "included in the resumption tuple. No assignment to M.REAL_SPACE anywhere. "
    "D5c counts from the same file, 2400 measurements: mean 0.703, median 0, q90 2, q99 4, q99.9 7, "
    "max 9, 56.8 per cent zero. Per point in NGC: B1 1.15, B2 1.02, B4 0.95, B5 0.96, B6 0.96, FID "
    "1.00."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.8; risposta_referee.md, §3.8",
    "amends_records": [],
    "the_null_register_is_renamed_not_deleted": ("fase3_mock_realspace_NULLO.jsonl. The resumption "
                                                 "key contains real_space, so leaving it in place "
                                                 "would make a corrected relaunch skip everything. "
                                                 "It is kept as evidence and for its valid D5c "
                                                 "counts."),
    "a_flag_is_verified_by_a_difference": ("A flag that changes a measurement is verified by a run "
                                           "that produces DIFFERENT numbers. Inertness and "
                                           "disconnection are indistinguishable by inspection, and "
                                           "every check written for that patch tested for "
                                           "inertness."),
    "the_smoke_must_run_WITH_the_flag": ("And must fail if the numbers match the main run. The "
                                         "existing smoke runs without it by design and cannot "
                                         "detect this."),
    "static_checks_cannot_see_a_missing_wire": ("Both ends existed and were verified. The connection "
                                                "has no name, so its absence has nothing to be "
                                                "checked against. Only behaviour shows it."),
    "the_separate_register_contained_the_damage": ("Records 16 and 23 required a separate register "
                                                   "for this run. Because of that the cost is twelve "
                                                   "hours and no contamination."),
    "the_d5c_threshold_is_not_declared_here": ("Having the distribution does not make a failed-run "
                                               "report the right place to declare a threshold. It "
                                               "gets its own record."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not declare the D5c threshold."),
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
    chk("6  idempotenza (marker 35 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 34 e' gia' nel registro", MARKER_34 in blob)

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
        chk("10 old_value descrive il run come dichiarato, con le sue 12 ore",
            ("twelve hours" in rec["old_value"])
            and ("real_space: true" in rec["old_value"]))
        chk("11 la prova e' cella per cella, non un'impressione",
            ("2400" in rec["new_value"]["the_run_produced_nothing"]["the_finding"])
            and ("integer for integer" in rec["new_value"]
                 ["the_run_produced_nothing"]["the_finding"]))
        chk("12 il difetto e' localizzato: la riga che collega non esiste",
            ("M.REAL_SPACE = True - was never written" in rec["new_value"]
                ["the_defect"]["where"])
            and ("no name to be absent" in rec["new_value"]["the_defect"]
                 ["the_class_of_defect"]))
        chk("13 perche' NESSUN controllo l'ha preso, e' spiegato senza scuse",
            ("SETS the flag" in rec["new_value"]["the_defect"]["why_no_check_caught_it"])
            and ("never called" in rec["new_value"]["the_defect"]
                 ["why_no_check_caught_it"])
            and ("inert in both" in rec["new_value"]["the_defect"]
                 ["why_the_smoke_could_not_catch_it"]))
        chk("13f il record 34 e' sulla riga 34",
            MARKER_34 in json.dumps(recs[33], ensure_ascii=False))
        chk("13g il registro va RINOMINATO, e si dice perche' non basta cancellare",
            ("would SKIP every realisation" in rec["new_value"]
                ["the_register_asserts_something_false"]["why_deleting_the_file_is_not_enough"])
            and ("NULLO" in rec["new_value"]["the_register_asserts_something_false"]["action"]))
        chk("13h la regola nuova: un flag si verifica con una DIFFERENZA",
            ("PRODUCES DIFFERENT NUMBERS" in rec["new_value"]
                ["what_is_required_before_the_relaunch"]["rule_adopted"])
            and ("FAIL IF THE NUMBERS MATCH" in rec["new_value"]
                 ["what_is_required_before_the_relaunch"]["a_smoke_WITH_the_flag"]))
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
        # 1. il run nullo: i quattro Delta coincidono col run principale entro
        #    l'arrotondamento con cui i secondi sono riportati. Se NON
        #    coincidessero, il run non sarebbe nullo e il record sbaglierebbe.
        NULLO = (-218.00, -172.30, -135.98, -111.13)
        REDSHIFT = (-218.0, -172.3, -136.0, -111.1)
        for a_, b_ in zip(NULLO, REDSHIFT):
            if abs(a_ - b_) > 0.05:
                bad.append("Delta %.2f vs %.1f" % (a_, b_))
        # 2. e i rapporti sono 1.000, non "circa 1"
        for a_, b_ in zip(NULLO, REDSHIFT):
            if abs(a_ / b_ - 1.0) > 5e-4:
                bad.append("rapporto %.4f" % (a_ / b_))
        # 3. la distribuzione D5c dichiarata e' coerente con se stessa
        D = {"media": 0.703, "q90": 2, "q99": 4, "q999": 7, "max": 9,
             "zero_frac": 0.568, "NGC_media": 1.006, "SGC_media": 0.401}
        if not (D["q90"] <= D["q99"] <= D["q999"] <= D["max"]):
            bad.append("quantili non monotoni")
        if abs((D["NGC_media"] + D["SGC_media"]) / 2 - D["media"]) > 0.01:
            bad.append("media globale != media dei due emisferi")
        if not (0 < D["zero_frac"] < 1) or D["media"] <= 0:
            bad.append("distribuzione incoerente")
        # 4. e il clipping NON cresce con la deformazione: FID non e' il minimo
        PER_PT = {"B1": 1.15, "B2": 1.02, "B4": 0.95, "B5": 0.96,
                  "B6": 0.96, "FID": 1.00}
        if PER_PT["FID"] == min(PER_PT.values()) or PER_PT["FID"] == max(PER_PT.values()):
            bad.append("FID estremo: il clipping dipenderebbe dalla deformazione")
        if max(PER_PT.values()) / min(PER_PT.values()) > 1.5:
            bad.append("spread per punto troppo grande per dirlo piatto")
        chk("14 aritmetica: i quattro Delta coincidono (rapporto 1.000), "
            "quantili monotoni, medie coerenti, FID non estremo", not bad,
            ",".join(bad) if bad else "quattordici controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend35 rev.1 ===")
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
        fail("il record 35 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

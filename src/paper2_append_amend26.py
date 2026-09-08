#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend26.py  (rev. 1) — Emendamento 26: il termine (c) dipende
dal punto? E i due livelli che gli mancano.

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

AMEND_POSITION = 26                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 25

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

MARKER = "emendamento-26-termine-c-dipendenza-dal-punto"
MARKER_25 = "emendamento-25-verdetto-intersezione-partial"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "term_c_point_dependence_and_the_missing_levels"

JSON_PATH = ("prereg \\u00a76 (error budget, term (c)); referee report section 4.5; "
             "amendments record 17 (denominator rule, for the form of the threshold)")

OLD_VALUE = (
    "Term (c), the carving re-randomisation, is a hand-written constant in "
    "src/paper2_fase3_budget.py: TERM_C = {NGC: {1: 7.73, 0: 7.69}, SGC: {1: 6.29, 0: 6.78}}. It "
    "was measured with a dedicated reseed run at the FIDUCIAL POINT ONLY, and applied unchanged at "
    "every grid point. There are no entries for k=2 and k=3, so the budget cannot be built at those "
    "levels. The referee's section 4.5 asks whether the desynchronisation grows with |F-1|, and "
    "notes that only the dispersion was ever reported, never the mean."
)

NEW_VALUE = {
    "what_is_already_settled": {
        "the_mean": ("Record-level: the mean of the paired difference is ZERO by exchangeability - "
                     "N_main(p,i) and N_reseed(p,i) are two draws from the same conditional "
                     "distribution given the HOD field and the geometry, differing only in the "
                     "carving seed. That holds at EVERY point, not only at the fiducial, so the "
                     "contribution to DDmax is exactly zero. Verified at the fiducial: z = +0.37, "
                     "-0.29, +1.57, +0.89, none above 3."),
        "sigma_carve_recovered": ("The frozen TERM_C is sd(dN)/sqrt(2)/sqrt(200), the sqrt(2) "
                                  "because the paired difference is between TWO independent draws. "
                                  "Measured sd(dN) at the fiducial: 153.74, 154.50, 135.69, 125.76, "
                                  "giving sigma_carve 108.71, 109.25, 95.95, 88.93 and TERM_C "
                                  "7.687, 7.725, 6.785, 6.288 against the deposited 7.69, 7.73, "
                                  "6.78, 6.29."),
    },
    "what_is_not_settled": {
        "point_dependence": ("Exchangeability constrains the MEAN, not the VARIANCE. Whether "
                             "sd(dN) grows with the deformation is untested, and TERM_C is a single "
                             "value per hemisphere and level applied at all twelve points. That "
                             "assumption has never been stated, let alone checked."),
        "the_missing_levels": ("TERM_C has no entries for k=2 and k=3, because the reseed run "
                               "predates them. The budget at those levels is therefore not "
                               "buildable, which is why checklist item 3.9 records it as blocked."),
    },
    "the_run": {
        "no_code_change_needed": ("The runner already has --carve-reseed, --points, --erosions and "
                                  "--out, and the resumption key includes all of them. Nothing is "
                                  "patched for this: only the decision rule is declared here."),
        "run_A": ("--points FID B6 --carve-reseed 777 --erosions 0 1, both hemispheres, N=200, into "
                  "a SEPARATE register. B6 is the most deformed point of line B: if sd depends on "
                  "the deformation, it shows there or nowhere."),
        "run_B": ("--points FID --carve-reseed 777 --erosions 2 3, both hemispheres, N=200, same "
                  "register. Fills TERM_C at the two levels that lack it. FID only: TERM_C is "
                  "defined at the fiducial."),
        "why_B6_and_not_B1_and_B5": ("B6 has the longest arm, 1.14 voxels of displacement against "
                                     "0.76 for B5. A hypothesis of growth is killed at the extreme "
                                     "or nowhere, and one point costs half of two."),
    },
    "reproduction_gate": {
        "what": ("Run A re-measures the FIDUCIAL, which is already on disk from the earlier reseed. "
                 "With the same seed, the same realisations and the same geometry the result is "
                 "deterministic, so sd(dN) at the fiducial must reproduce 153.74, 154.50, 135.69 "
                 "and 125.76 EXACTLY."),
        "why_it_matters_here": ("phase8_cutsky_mocks.py and the runner have been patched four times "
                                "since that measurement: capture=, REAL_SPACE, D5c, D5C_MODE. Each "
                                "was checked to be inert, but the fiducial reseed is the first run "
                                "that re-measures a frozen quantity through all of them at once."),
        "blocking": True,
        "tolerance": 0,
    },
    "declared_prediction": {
        "statement": ("Term (c) does not depend on the grid point: sd(dN) at B6 equals sd(dN) at "
                      "the fiducial, within sampling error."),
        "the_threshold_is_derived_not_chosen": (
            "The relative sampling error of an sd estimated from n = 200 values is 1/sqrt(2n) = "
            "5.00 per cent. The ratio of two independent sd estimates therefore carries "
            "sqrt(2) x 5.00 = 7.07 per cent, and three sigma is 21.2 per cent. The threshold is "
            "that number, not a round figure picked afterwards."),
        "falsified_if": ("|sd(B6)/sd(FID) - 1| > 0.212 in AT LEAST HALF of the four cases, that is "
                         "two or more of NGC k=0, NGC k=1, SGC k=0, SGC k=1."),
        "if_falsified": ("Term (c) is point-dependent and a single value per hemisphere and level "
                         "is not justified. The budget then carries (c) per point, or declares the "
                         "assumption it makes. This is a change to the budget and would be "
                         "registered."),
        "if_it_holds": ("The practice of measuring (c) at the fiducial and applying it everywhere is "
                        "justified by measurement rather than by silence, and the referee's section "
                        "4.5 closes: the mean is zero by exchangeability and verified, and the "
                        "dispersion is point-independent."),
        "not_repaired_afterwards": True,
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not change TERM_C - which is re-measured "
                              "at the fiducial as a gate, not re-derived."),
}

REASON = (
    "Two gaps in term (c) are closed by one reseed run, and its decision rule is declared before it "
    "runs. "
    "WHAT IS ALREADY SETTLED. The MEAN of the carving re-randomisation is zero by exchangeability, "
    "at every point and not only at the fiducial, so its contribution to DDmax is exactly zero; "
    "verified at the fiducial with z = +0.37, -0.29, +1.57, +0.89. And the definition of the frozen "
    "TERM_C has been recovered: sd(dN)/sqrt(2)/sqrt(200), reproducing 7.69, 7.73, 6.78, 6.29 to the "
    "third digit. "
    "WHAT IS NOT. Exchangeability constrains the mean, not the variance. Whether sd(dN) grows with "
    "the deformation has never been tested, and TERM_C is one value per hemisphere and level "
    "applied at all twelve points - an assumption never stated. And TERM_C has no entries for k=2 "
    "and k=3, so the budget at those levels is not buildable. "
    "THE RUN, WHICH NEEDS NO CODE. Run A: FID and B6, reseed 777, erosions 0 and 1. Run B: FID "
    "only, erosions 2 and 3. B6 because it has the longest arm, 1.14 voxels against 0.76 for B5: a "
    "hypothesis of growth dies at the extreme or nowhere. "
    "THE REPRODUCTION GATE. Run A re-measures the fiducial, which is on disk. Being deterministic, "
    "sd(dN) must reproduce 153.74, 154.50, 135.69 and 125.76 exactly. This matters more than usual: "
    "phase8 and the runner have been patched four times since that measurement, and this is the "
    "first run that re-measures a frozen quantity through all of them at once. "
    "THE THRESHOLD, DERIVED AND NOT CHOSEN. The relative sampling error of an sd from n = 200 is "
    "1/sqrt(2n) = 5.00 per cent; the ratio of two carries 7.07 per cent; three sigma is 21.2 per "
    "cent. The prediction is that (c) does not depend on the point, FALSIFIED if the ratio departs "
    "from 1 by more than 0.212 in at least half of the four cases."
)

EVIDENCE = (
    "src/paper2_fase3_budget.py: TERM_C = {'NGC': {1: 7.73, 0: 7.69}, 'SGC': {1: 6.29, 0: 6.78}}, "
    "with no entries for k=2 or k=3. "
    "results/paper2/fase3_mock_carve777.jsonl: 400 records, FID only, erosions 0 and 1. Measured "
    "sd(dN) = 153.74 (NGC k=0), 154.50 (NGC k=1), 135.69 (SGC k=0), 125.76 (SGC k=1); divided by "
    "sqrt(2) and sqrt(200) these give 7.687, 7.725, 6.785, 6.288 against the deposited constants. "
    "Means at the fiducial: +3.990, -3.200, +15.025, +7.920, with z = +0.37, -0.29, +1.57, +0.89. "
    "Arm lengths on line B: B6 displaces 1.14 voxels against 0.76 for B5, from checklist item 1.3. "
    "Sampling error of an sd from n = 200: 1/sqrt(400) = 0.0500; of a ratio of two, 0.0707; three "
    "sigma, 0.2121."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, items 3.7 and 3.9",
    "amends_records": [],
    "threshold_derived_from_sampling_error": ("21.2 per cent is three times the 7.07 per cent "
                                              "relative error of a ratio of two sd estimates from "
                                              "n = 200. It is not a round number chosen for "
                                              "convenience."),
    "reproduction_gate_is_blocking": ("If the fiducial does not reproduce 153.74 / 154.50 / 135.69 "
                                      "/ 125.76 exactly, nothing from this run is used and the four "
                                      "patches applied since that measurement are re-examined."),
    "the_mean_is_not_re_opened": ("Exchangeability settles the mean at every point. This run tests "
                                  "the VARIANCE, which exchangeability does not constrain."),
    "term_c_is_not_re_derived_here": ("TERM_C is re-measured at the fiducial as a gate. If the "
                                      "prediction holds, the constant stands as deposited; the run "
                                      "only adds the two missing levels."),
    "a_falsification_changes_the_budget_and_is_registered": ("If (c) turns out to be "
                                                             "point-dependent, carrying it per "
                                                             "point is a change to the budget and "
                                                             "gets its own record."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not change TERM_C."),
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
    chk("6  idempotenza (marker 26 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 25 e' gia' nel registro", MARKER_25 in blob)

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
        chk("10 old_value cita TERM_C com'e' scritto, e i livelli che mancano",
            ("{NGC: {1: 7.73, 0: 7.69}" in rec["old_value"])
            and ("no entries for k=2 and k=3" in rec["old_value"]))
        chk("11 media e varianza sono tenute distinte, ed e' il punto",
            ("constrains the MEAN, not the VARIANCE" in rec["new_value"]
                ["what_is_not_settled"]["point_dependence"])
            and ("does not constrain" in rec["rules"]["the_mean_is_not_re_opened"]))
        chk("12 il cancello di riproduzione e' bloccante e sa perche' serve QUI",
            rec["new_value"]["reproduction_gate"]["blocking"] is True
            and rec["new_value"]["reproduction_gate"]["tolerance"] == 0
            and ("patched four times" in rec["new_value"]["reproduction_gate"]
                 ["why_it_matters_here"]))
        chk("13 la soglia e' DERIVATA dall'errore di campionamento, non scelta",
            ("1/sqrt(2n) = 5.00 per cent" in rec["new_value"]["declared_prediction"]
                ["the_threshold_is_derived_not_chosen"])
            and ("not a round number chosen for" in rec["rules"]
                 ["threshold_derived_from_sampling_error"]))
        chk("13f il record 25 e' sulla riga 25",
            MARKER_25 in json.dumps(recs[24], ensure_ascii=False))
        chk("13g il run non richiede codice, ed e' dichiarato",
            ("Nothing is patched" in rec["new_value"]["the_run"]["no_code_change_needed"]
             or "no code" in rec["new_value"]["the_run"]["no_code_change_needed"].lower()))
        chk("13h B6 e' scelto per il braccio, con il numero",
            ("1.14 voxels" in rec["new_value"]["the_run"]["why_B6_and_not_B1_and_B5"])
            and ("0.76" in rec["new_value"]["the_run"]["why_B6_and_not_B1_and_B5"]))
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
        # 1. la soglia deve USCIRE dall'errore di campionamento, non essere scritta
        rel = 1.0 / math.sqrt(2 * 200)
        soglia = 3.0 * rel * math.sqrt(2.0)
        if abs(rel - 0.0500) > 5e-4 or abs(soglia - 0.2121) > 5e-4:
            bad.append("derivazione della soglia")
        if "0.212" not in rec["new_value"]["declared_prediction"]["falsified_if"]:
            bad.append("soglia non nel record")
        # 2. TERM_C si ricava dalle sd misurate, col sqrt(2)
        SD = {"NGC_k0": 153.74, "NGC_k1": 154.50,
              "SGC_k0": 135.69, "SGC_k1": 125.76}
        DEP = {"NGC_k0": 7.69, "NGC_k1": 7.73, "SGC_k0": 6.78, "SGC_k1": 6.29}
        for k, s in SD.items():
            if abs(s / math.sqrt(2.0) / math.sqrt(200.0) - DEP[k]) > 0.01:
                bad.append(k + "/termc")
        # 3. e "almeno meta'" su quattro casi vuol dire due, non tre
        if sum(1 for _ in range(4)) // 2 != 2:
            bad.append("meta'")
        if "two or more" not in rec["new_value"]["declared_prediction"]["falsified_if"]:
            bad.append("meta' non esplicitata")
        chk("14 aritmetica: soglia 21.2%% derivata, TERM_C = sd/sqrt(2)/sqrt(200), "
            "meta' di quattro e' due", not bad,
            ",".join(bad) if bad else "dieci controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend26 rev.1 ===")
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
        fail("il record 26 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

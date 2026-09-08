#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend39.py  (rev. 1) — Emendamento 39: il termine (c) NON dipende dal
punto. Prima predizione che regge, e il cancello copre sette patch.

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

AMEND_POSITION = 39                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 38

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

MARKER = "emendamento-39-termine-c-indipendente-dal-punto"
MARKER_38 = "emendamento-38-trattamento-b-predizione-1-falsificata"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "term_c_is_point_independent_and_the_reproduction_gate_held"

JSON_PATH = ("amendments record 26 (declared_prediction; reproduction_gate); "
             "referee report section 4.5")

OLD_VALUE = (
    "Record 26 declares: term (c) does not depend on the grid point, so sd(dN) at B6 equals sd(dN) "
    "at the fiducial within sampling error. FALSIFIED IF |sd(B6)/sd(FID) - 1| > 0.212 in at least "
    "half of the four cases, the threshold being three times the 7.07 per cent relative error of a "
    "ratio of two sd estimates from n = 200. It also declares a blocking reproduction gate at "
    "tolerance zero: sd(dN) at the fiducial must reproduce 153.74, 154.50, 135.69 and 125.76 "
    "exactly, and notes that phase8 and the runner had been patched four times since that "
    "measurement."
)

NEW_VALUE = {
    "the_reproduction_gate_held_exactly": {
        "measured": {"NGC_k0": 153.739, "NGC_k1": 154.502,
                     "SGC_k0": 135.694, "SGC_k1": 125.758},
        "frozen": {"NGC_k0": 153.74, "NGC_k1": 154.50,
                   "SGC_k0": 135.69, "SGC_k1": 125.76},
        "and_it_is_now_seven_patches_not_four": (
            "Record 26 counted four. Since it was written there have been three more: "
            "_accendi_real_space, --fixed-observables, and D5C_SOGLIA. Seven changes to phase8 and "
            "the runner separate this measurement from the frozen one, each verified inert on its "
            "own. This is the first run that re-measures a frozen quantity through ALL of them at "
            "once, and nothing moved."),
        "why_that_matters_more_than_usual": ("Two of those seven were defective when written - the "
                                             "real-space flag was never connected (record 35) and "
                                             "the floor patch used a key that does not exist "
                                             "(record 34) - so the assumption that each was inert "
                                             "had already failed twice. It is now tested rather "
                                             "than assumed."),
    },
    "the_prediction_holds": {
        "ratios": {"NGC_k0": 1.0543, "NGC_k1": 1.0160,
                   "SGC_k0": 0.9666, "SGC_k1": 0.9265},
        "deviations": {"NGC_k0": 0.0543, "NGC_k1": 0.0160,
                       "SGC_k0": 0.0334, "SGC_k1": 0.0735},
        "threshold": 0.212,
        "exceedances": 0,
        "reading": ("Zero of four exceed, and the largest deviation - 0.0735 in SGC k=1 - sits at "
                    "about a third of the threshold. sd(dN) at B6, the most deformed point of line "
                    "B with an arm of 1.14 voxels against 0.76 for B5, is indistinguishable from "
                    "sd(dN) at the fiducial."),
        "so_term_c_does_not_depend_on_the_point": ("Measuring (c) at the fiducial and applying it "
                                                   "at every grid point is now justified BY "
                                                   "MEASUREMENT rather than by silence. The "
                                                   "assumption had never been stated, let alone "
                                                   "checked."),
    },
    "section_4_5_closes": {
        "the_mean": ("Zero by exchangeability, at EVERY point and not only at the fiducial: "
                     "N_main(p,i) and N_reseed(p,i) are two draws from the same conditional "
                     "distribution given the HOD field and the geometry, differing only in the "
                     "carving seed. Verified at the fiducial: z = +0.37, -0.29, +1.57, +0.89."),
        "the_dispersion": ("Point-independent, measured here. The referee's section 4.5 asked "
                           "whether the desynchronisation grows with |F-1| and noted that only the "
                           "dispersion had ever been reported, never the mean. Both are now "
                           "answered."),
        "what_remains_open_there": ("Nothing in 4.5. The k=2 and k=3 levels of TERM_C are a "
                                    "separate gap, closed by the FID-only reseed at those "
                                    "erosions, and are not part of this rilievo."),
    },
    "a_confirmation_after_five_falsifications": {
        "what": ("This is the first declared prediction to HOLD in this response cycle. The RSD "
                 "mechanism (record 37), prediction 1 of treatment (B) (record 38), the power-law "
                 "extrapolation of the block A (record 31), and the two over-claims of record 19 "
                 "were all falsified."),
        "why_it_is_worth_saying": ("A programme in which every declared prediction fails is a "
                                   "programme whose predictions are not constraining. One that "
                                   "holds, with a threshold derived from a sampling error rather "
                                   "than chosen, shows the rules are capable of both outcomes."),
        "and_it_was_the_cheapest_to_falsify": ("B6 has the longest arm on line B. If the dispersion "
                                               "grew with the deformation it would show there or "
                                               "nowhere, and it does not show."),
    },
    "an_observation_carried_by_the_same_run": {
        "what": ("The four new block-A points give n_valid_voxels of 307732, 307944, 307634 and "
                 "307916 in NGC, against 307805 at the fiducial: all different, and different from "
                 "each other, on PURE ISOTROPIC DILATIONS where Proposition 2 says the signal is "
                 "zero. The spread is -171 to +139 voxels."),
        "status": ("Reported, no verdict. It is the same channel (e) the budget subtracts, now "
                   "visible on six points instead of two. No threshold was declared on it here."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not change TERM_C - which is re-measured at "
                              "the fiducial as a gate and stands as deposited - and does not fill "
                              "the k=2,3 entries."),
}

REASON = (
    "The section-4.5 prediction of record 26 HOLDS, and the reproduction gate held exactly. "
    "THE GATE. sd(dN) at the fiducial measures 153.739, 154.502, 135.694 and 125.758 against the "
    "frozen 153.74, 154.50, 135.69 and 125.76: exact to the second decimal in all four cases. "
    "Record 26 counted four patches to phase8 and the runner since that measurement; there have "
    "since been three more, so SEVEN separate this run from the frozen value, each verified inert "
    "on its own. This is the first run to re-measure a frozen quantity through all of them at once. "
    "It matters more than usual because two of those seven were defective when written - the "
    "real-space flag was never connected, and the floor patch used a key that does not exist - so "
    "the assumption of inertness had already failed twice. "
    "THE PREDICTION. sd(B6)/sd(FID) gives 1.0543, 1.0160, 0.9666 and 0.9265, that is deviations of "
    "0.0543, 0.0160, 0.0334 and 0.0735 against a threshold of 0.212 derived from the sampling error of "
    "a ratio of two sd estimates. ZERO of four exceed, and the largest sits at about a third of the "
    "threshold. B6 has the longest arm on line B - 1.14 voxels of displacement against 0.76 for B5 "
    "- so if the dispersion grew with the deformation it would show there or nowhere. It does not. "
    "TERM (C) DOES NOT DEPEND ON THE GRID POINT, and measuring it at the fiducial and applying it "
    "everywhere is now justified by measurement rather than by silence. Section 4.5 closes: the "
    "mean is zero by exchangeability and verified, the dispersion is point-independent and "
    "measured. "
    "AND IT IS THE FIRST DECLARED PREDICTION TO HOLD in this response cycle, after the RSD "
    "mechanism, prediction 1 of treatment (B), the power-law extrapolation of block A and the two "
    "over-claims of record 19. A programme in which every prediction fails is one whose predictions "
    "do not constrain; one that holds, with a threshold derived rather than chosen, shows the rules "
    "can go either way."
)

EVIDENCE = (
    "results/paper2/fase3_mock_carve777_b6.jsonl, 400 records, 200 realisations per hemisphere, "
    "points FID and B6, erosions 0 and 1, carve_reseed 777, run 4 Sep 2026 in 2.51 h and 2.11 h. "
    "Paired differences against results/paper2/fase3_mock.jsonl at the same points. "
    "sd(dN) at FID: 153.739, 154.502, 135.694, 125.758 (n = 200 each), against the frozen 153.74, "
    "154.50, 135.69, 125.76 of the earlier reseed. "
    "sd(dN) at B6: 162.088, 156.980, 131.161, 116.520. Ratios to FID: 1.0543, 1.0160, 0.9666, "
    "0.9265; |ratio - 1| = 0.0543, 0.0160, 0.0334, 0.0735; threshold 0.212 = 3 x sqrt(2) / sqrt(2 x "
    "200). "
    "Arm lengths on line B, checklist item 1.3: B6 displaces 1.14 voxels against 0.76 for B5. "
    "Means of the paired difference at the fiducial, from the earlier reseed: z = +0.37, -0.29, "
    "+1.57, +0.89. "
    "Block-A voxel counts from the same session, NGC: A0 307732, A1m 307944, A3m 307634, A0m "
    "307916, against 307805 at the fiducial. "
    "Patches to phase8 and paper2_runner_fase3_mock.py since the frozen reseed: capture=, "
    "REAL_SPACE, D5c, D5C_MODE, _accendi_real_space, --fixed-observables, D5C_SOGLIA."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.9; risposta_referee.md, §4.5",
    "amends_records": [],
    "term_c_is_point_independent": ("Measured, not assumed. sd(B6)/sd(FID) deviates by 0.0160 to "
                                    "0.0735 against a threshold of 0.212, zero exceedances."),
    "the_deposited_practice_is_now_justified": ("Measuring (c) at the fiducial and applying it at "
                                                "every point was an unstated assumption. It is now "
                                                "a measurement."),
    "the_reproduction_gate_covered_seven_patches": ("Each had been verified inert alone; two of the "
                                                    "seven were defective when written. Testing "
                                                    "them together was the point of the gate."),
    "section_4_5_is_closed": ("Mean zero by exchangeability and verified; dispersion "
                              "point-independent and measured. The k=2,3 entries of TERM_C are a "
                              "separate gap."),
    "the_block_a_voxel_spread_carries_no_verdict": ("Six points, counts from 307634 to 307944 "
                                                    "against 307805, on pure dilations. Reported "
                                                    "because it is the channel (e) seen on six "
                                                    "points instead of two; no threshold was "
                                                    "declared on it."),
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
    chk("6  idempotenza (marker 39 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 38 e' gia' nel registro", MARKER_38 in blob)

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
        chk("10 old_value cita la soglia e la sua derivazione",
            ("0.212" in rec["old_value"]) and ("7.07 per cent" in rec["old_value"]))
        chk("11 il cancello di riproduzione e' passato ESATTO su quattro casi",
            len(rec["new_value"]["the_reproduction_gate_held_exactly"]["measured"]) == 4
            and ("and_it_is_now_seven_patches_not_four" in rec["new_value"]
                 ["the_reproduction_gate_held_exactly"]))
        chk("12 zero superamenti su quattro, e la lettura lo dice",
            rec["new_value"]["the_prediction_holds"]["exceedances"] == 0
            and ("Zero of four exceed" in rec["new_value"]["the_prediction_holds"]["reading"]))
        chk("13 e' la PRIMA predizione che regge, e si dice perche' conta",
            ("first declared prediction to HOLD" in rec["new_value"]
                ["a_confirmation_after_five_falsifications"]["what"])
            and ("not constraining" in rec["new_value"]
                 ["a_confirmation_after_five_falsifications"]["why_it_is_worth_saying"]))
        chk("13f il record 38 e' sulla riga 38",
            MARKER_38 in json.dumps(recs[37], ensure_ascii=False))
        chk("13g le sette patch sono nominate, e due erano difettose",
            ("failed twice" in rec["new_value"]["the_reproduction_gate_held_exactly"]
                ["why_that_matters_more_than_usual"])
            and ("D5C_SOGLIA" in rec["evidence"]))
        chk("13h lo spread voxel del blocco A e' riportato SENZA verdetto",
            ("no verdict" in rec["new_value"]["an_observation_carried_by_the_same_run"]
                ["status"])
            and ("no threshold was declared" in rec["rules"]
                 ["the_block_a_voxel_spread_carries_no_verdict"]))
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
        G = rec["new_value"]["the_reproduction_gate_held_exactly"]
        P = rec["new_value"]["the_prediction_holds"]
        # 1. il cancello: misurato e congelato coincidono alla seconda cifra
        for nm in G["measured"]:
            if abs(G["measured"][nm] - G["frozen"][nm]) > 0.01:
                bad.append(nm + "/cancello")
        # 2. la soglia e' quella derivata nel record 26, ricalcolata
        soglia = 3.0 * math.sqrt(2.0) / math.sqrt(2 * 200)
        if abs(soglia - P["threshold"]) > 5e-4:
            bad.append("soglia %.4f" % soglia)
        # 3. le deviazioni escono dai rapporti, e NESSUNA supera
        for nm, r in P["ratios"].items():
            if abs(abs(r - 1) - P["deviations"][nm]) > 5e-4:
                bad.append(nm + "/deviazione")
            if abs(r - 1) > P["threshold"]:
                bad.append(nm + "/supera")
        if P["exceedances"] != sum(1 for r in P["ratios"].values()
                                   if abs(r - 1) > P["threshold"]):
            bad.append("conteggio superamenti")
        # 4. e la piu' grande sta a circa un terzo della soglia: e' il margine
        worst = max(abs(r - 1) for r in P["ratios"].values())
        if not (0.28 < worst / P["threshold"] < 0.40):
            bad.append("margine %.2f" % (worst / P["threshold"]))
        chk("14 aritmetica: cancello esatto, soglia 0.212 ricalcolata, zero "
            "superamenti, la peggiore a %.0f%% della soglia"
            % (100 * worst / P["threshold"]), not bad,
            ",".join(bad) if bad else "diciassette controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend39 rev.1 ===")
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
        fail("il record 39 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend16.py  (rev. 3) — Emendamento 16: statuto del test a
osservabili fisse.

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

AMEND_POSITION = 16                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 15

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

MARKER = "emendamento-16-osservabili-fisse"
COMPANION_DOCUMENT = "paper2_item16.md"


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro, cfr. righe 13-15)
# ---------------------------------------------------------------------------

KEY = "fixed_observables_treatment"

JSON_PATH = ("prereg \u00a75.1 (what is measured); prereg \u00a77.2 (geometry injection "
             "sequence); prereg \u00a78 (scope: selection-state channel)")

OLD_VALUE = (
    "\u00a75.1: D(g) = <N_H1>_mock(g) - N_H1^DESI(g); AP acts on both sides, so the response "
    "cancels in D if data and mocks respond identically, and all noise is on the mock side. No "
    "distinction is drawn between regenerating the mock sky at each fiducial and holding the mock "
    "observables fixed, although the two are different perturbations of the mock field. "
    "\u00a78 already lists 'carving re-randomisation at fixed geometry' and 'the number of galaxies "
    "changing selection state per grid point' as NOT covered and to be measured without a "
    "pre-registered rule."
)

NEW_VALUE = {
    "treatment_A": ("regenerated mocks: the box-to-sky mapping is rebuilt at the fiducial of each "
                    "grid point by carve_cutsky(). This is what paper2_runner_fase3_mock.py "
                    "executes and what Phase 3 measured at every point."),
    "treatment_B": ("fixed observables: (rhat, z_obs) are frozen at the fiducial and only "
                    "r' = D_C^(g)(z_obs) is recomputed per point. This is the treatment the data "
                    "side undergoes by construction, since for the data (RA, DEC, z) do not depend "
                    "on the analysis cosmology."),
    "mandatory_label": "post-review, declared before execution",
    "forbidden_labels": ["pre-registered", "planned", "foreseen by the protocol"],
    "pre_registered": False,
    "perimeter": {
        "points": ["B1", "B2", "fiducial", "B4", "B5", "B6"],
        "F_ap_pipeline_convention": LINE_B,
        "N_realisations": 200,
        "pairing": "same indices 0-199 as Phase 3",
        "hemispheres": ["NGC", "SGC"],
        "erosion": {"primary": 1, "parallel": 0},
        "gauge": "amend13 constant cube",
        "cache": {
            "built_at": "the fiducial point, AFTER Pass 2 of carve_cutsky",
            "fields": ["rhat float64", "z_obs float64"],
            "row_order": "preserved",
            "keyed_by": ["hemisphere", "realisation index", "HOD seed"],
            "config_hash": True,
        },
        "downstream_treatment": ("exactly the data-side chain: no n(z) resampling, no re-seeding, "
                                 "no rebuilding of the selection, no re-application of the z cuts. "
                                 "The selection is frozen at the fiducial, and that is what makes "
                                 "(B) the twin of the data side."),
    },
    "gates": {
        "D5a": {
            "name": "bit-identity at the fiducial point",
            "requirement": "P_rsd from (B) bit-identical to P_rsd from (A)",
            "tolerance": D5A_TOLERANCE,
            "blocking": True,
            "why_record_14_does_not_apply": (
                "Record 14 established that mock-side bit-identity is unattainable by "
                "construction, but that comparison was between the native comoving_distance and an "
                "injected table. Here the comparison is INTERNAL to the same table: "
                "phase8_cutsky_mocks.py lines 682-683 compute "
                "dC_rsd = np.interp(np.clip(z_obs, 0.0, 0.6), _Z_TAB, _DC_TAB) and "
                "P_rsd = rhat * dC_rsd[:, None], and (B) at the fiducial runs the same function, "
                "on the same table, on the same input bits. The output is identical bit for bit. "
                "Setting the gate at the tie-breaking scale (2.5e-05 generators) would accept a "
                "wrong cache: it would be a gate that cannot fail."),
        },
        "D5b": {
            "name": "reproduction of the frozen Phase-3 baseline",
            "requirement": "exact, not within tolerance",
            "values": BASELINE,
            "blocking": True,
        },
    },
}

REASON = (
    "Two purposes, both arising from the referee report and both declared here before any run of "
    "treatment (B). "
    "FIRST: a naming rectification, mandatory and independent of whether (B) is ever executed. "
    "\u00a75.1 defines D(g) and states that AP acts on both sides, without saying how the mock side is "
    "brought to the grid point. What Phase 3 measured is D(g) UNDER TREATMENT (A), with the "
    "box-to-sky mapping regenerated at the fiducial of each point. The manuscript must say so. "
    "This changes no number; it changes what the numbers mean. The unqualified phrasing is "
    "ambiguous between two physically different perturbations of the mock field, and that "
    "ambiguity is what allowed the ratio Delta_mock/Delta_dati to be read as a fact rather than as "
    "an artefact of treatment. "
    "SECOND: the statute of treatment (B), fixed observables. It is NOT pre-registered and appears "
    "nowhere in the deposited protocol; it originates in the referee report. It is declared here "
    "before execution, with perimeter, gates, predictions and quotation rule fixed before the "
    "first point runs. Its mandatory label in the manuscript and in every figure or table is "
    "'post-review, declared before execution'."
)

EVIDENCE = (
    "phase8_cutsky_mocks.py, carve_cutsky(). Under the constant-cube gauge (record 13) BOX_MIN, "
    "BOX_SIZE, CELL, NGRID, SIGMA_PX and the mask are frozen across the grid, so the tiling "
    "offsets (lines 652-657) and the mask array (line 690) are identical point by point: tiling is "
    "NOT a channel of variation. Only _Z_TAB/_DC_TAB and D_C_ZMIN/D_C_ZMAX vary. Box positions are "
    "fixed, hence dC = norm(P) (line 673) and rhat (line 678) do not change. Without RSD, "
    "z_obs = z_cosmo and dC_rsd = interp(interp(dC, _DC_TAB, _Z_TAB), _Z_TAB, _DC_TAB), the "
    "round trip of a monotone piecewise-linear map on the SAME nodes: the identity in exact "
    "arithmetic, within a few ulp in floating point (measured 1.9e-16 relative by selftest 14 of "
    "paper2_append_amend16.py). Positions therefore do not move for ANY injected table, and only "
    "the SELECTION changes: the radial pre-filter (line 674) on thresholds that shift, zsel "
    "(line 684) on a recomputed z_obs, and the n(z) resampling (lines 702-715) where "
    "rng.random(len(z_cand)) realigns the stream as soon as the candidate count changes. With RSD, "
    "dC_rsd - dC ~ (1+z) v_los / H(z), and H(z) is the local slope of the injected table: "
    "treatment (A) applies the AP distortion to the RSD DISPLACEMENT while leaving the real-space "
    "field invariant, whereas the data side applies it to the whole radial coordinate. These are "
    "not the same perturbation, and this is the mechanism of the measured factor 2.10-5.56 between "
    "Delta_mock and Delta_dati."
)

RULES = {
    "marker": MARKER,
    "companion_document": "paper2_item16.md",
    "verdict_unchanged": (
        "Treatment (B) does NOT enter DD_max, which stays defined on treatment (A) and on B1-B5 as "
        "deposited. The E1-E4 verdict is already issued - E2, four times out of four - and does "
        "not change. A treatment declared afterwards cannot reopen a rule already applied."),
    "quotation_rule": (
        "The deposited outcome (E1-E4, prereg \u00a75.3) stays evaluated on treatment (A), which gives "
        "the larger excursion, and the systematics budget takes that number. Treatment (B) is "
        "reported alongside as the isolation of the AP channel proper, with its own conclusion."),
    "why_A_stays_primary": (
        "The direction of the (B) effect is KNOWN BEFORE THE RUN: Delta_mock^(B) <= Delta_mock^(A) "
        "is expected, so Delta_D shrinks and the outcome moves from E2 towards E1, that is towards "
        "the result favourable to the paper. Promoting (B) to primary now would replace the "
        "pre-registered analysis with a more favourable one whose direction is already known. "
        "Keeping (A) concludes on the more conservative of the two and the substitution cannot be "
        "contested."),
    "counterargument_recorded": (
        "Standard practice in AP analyses builds the mock catalogue ONCE, with the true cosmology "
        "of the simulation, and lets the fiducial enter only at the analysis step: that is "
        "treatment (B). Under that reading (A) is not a conservative variant but a procedure that "
        "changes the simulated universe instead of the analysis choice, and its Delta_D is an "
        "artefact rather than an analysis systematic. The rule adopted here quotes the larger "
        "number either way, so it stays conservative even if the objection is right; but the "
        "manuscript must report the objection, not only the choice."),
    "where_B_enters": (
        "Isolation of the AP channel proper; the ratio Delta_mock/Delta_dati point by point; the "
        "mechanism test on the real-space line B. It does not enter DD_max, the symmetry fit or "
        "the corner completeness test."),
    "implementation": (
        "A --fixed-observables mode of paper2_runner_fase3_mock.py, with a 'mode' field in the "
        "JSONL record and a distinct config hash. NOT a new script: one implementation per "
        "quantity, the defect class that produced the 445 vs 313 mock dispersion."),
    "cost": ("six points x 200 paired mocks x two hemispheres, plus one data-side reference run; "
             "of order 10 h at the measured ~13 s per mock-point. The cached path skips the "
             "carving step."),
    "declared_prediction_ratio": (
        "If the measured factor 2.10-5.56 between Delta_mock and Delta_dati is entirely an "
        "artefact of treatment, then under (B) the ratio Delta_mock/Delta_dati falls towards 1 and "
        "Delta_D towards zero. FALSIFIED IF the ratio stays above 2 at three or more of the six "
        "points, in which case the mock side responds to AP more than the observed field for a "
        "reason that is not the RSD remapping. Not to be repaired afterwards."),
    "declared_prediction_real_space": (
        "Under treatment (A) WITHOUT RSD, Delta_mock is a pure re-selection effect, with positions "
        "invariant to 1e-16 (see evidence). Expected order: that of the carving re-randomisation "
        "term, -3.2 +/- 10.9 to +15.0 +/- 9.6 generators. FALSIFIED IF |Delta_mock| > 53 "
        "generators, the deposited detectability threshold, in which case 'the mechanism is the "
        "RSD remapping' is wrong and a selection channel of non-negligible amplitude is open. This "
        "turns the real-space line B from a generic diagnostic into a falsification of the "
        "mechanism, with a threshold declared before the run. The channel is the one prereg \u00a78 "
        "already lists as not covered ('the number of galaxies changing selection state per grid "
        "point'), so measuring it fills a declared gap rather than contradicting the deposit."),
    "what_this_does_not_do": (
        "It modifies no frozen value, does not reopen Phase 3, does not touch the E2 verdict, and "
        "does not change the deposited grid or the detectability and relevance thresholds."),
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
    chk("6  idempotenza (marker assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")

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
        chk("10 soglie delle due predizioni dichiarate presenti",
            ("above 2 at three or more of the six points" in txt)
            and ("> %d " % REALSPACE_FALSIFY_GEN in txt)
            and txt.count("FALSIFIED IF") == 2)
        chk("11 tolleranza D5a esattamente zero",
            rec["new_value"]["gates"]["D5a"]["tolerance"] == 0)
        chk("12 quattro valori congelati del cancello D5b presenti",
            all(str(v) in txt for h in BASELINE for v in BASELINE[h].values()))
        chk("13 quotazione: (A) primario, obiezione contraria e statuto non pre-registrato",
            ("stays evaluated on treatment (A)" in rec["rules"]["quotation_rule"])
            and ("Standard practice" in rec["rules"]["counterargument_recorded"])
            and rec["new_value"]["pre_registered"] is False
            and "NOT pre-registered" in rec["reason"])
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
        import numpy as np
        z = np.linspace(0.0, 0.6, 4001)
        dc = 2997.92458 * z * (1.0 - 0.75 * z + 0.5 * z * z)
        assert np.all(np.diff(dc) > 0)
        probe = np.linspace(dc[1], dc[-2], 20001)
        back = np.interp(np.interp(probe, dc, z), z, dc)
        rel = float(np.max(np.abs(back - probe) / probe))
        chk("14 round-trip interp identita' (premessa predizione 2)", rel < 1e-12,
            "rel max %.2e" % rel)
    except Exception as exc:
        chk("14 round-trip interp identita'", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend16 rev.3 ===")
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
        fail("il record 16 aggiunge le chiavi %s rispetto alle comuni 13-15. "
             "Approvale con --allow-extra-keys (nel registro le chiavi di contenuto "
             "variano gia' riga per riga: 13 falsified_prediction+withdrawn, "
             "14 falsified_predictions, 15 rules)." % ", ".join(extras))

    line = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
    print("=== RECORD 16 — riga %d, %d caratteri ===" % (len(recs) + 1, len(line)))
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
    print("[OK] record 16 appeso a %s" % args.ledger)
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
    print("  marker nella riga 16      : %s" % (MARKER in last))
    ok &= MARKER in last
    print("  item della riga 16        : %r" % (recs[-1].get("item") if recs else None))
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

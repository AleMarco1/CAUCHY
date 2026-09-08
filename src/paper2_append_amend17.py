#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend17.py  (rev. 1) — Emendamento 17: cancello D5c sul
clipping lato mock, e denominatore della predizione 1.

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

AMEND_POSITION = 17                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 16

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

MARKER = "emendamento-17-cancello-clipping-mock"
MARKER_16 = "emendamento-16-osservabili-fisse"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "mock_side_clipping_gate"

JSON_PATH = ("prereg \u00a77.2 (mandatory procedure); prereg \u00a75.3 (the four outcomes); "
             "amendments record 13 point (c) (zero-clipping gate, data side only); "
             "amendments record 16 (declared prediction 1, denominator)")

OLD_VALUE = (
    "Record 13 point (c) forbids ANY galaxy or random falling outside the cube, and "
    "paper2_runner_fase3.py enforces it on the data side with a hard stop: "
    "PF.clipped_per_face(pos_r, ...) at line 278 and PF.clipped_per_face(pos_d, ...) at line 298, "
    "each followed by sys.exit if n_clipped is non-zero. The MOCK side has no such barrier: "
    "phase8_cutsky_mocks.py line 688 computes "
    "ijk = np.clip(((P_rsd - BOX_MIN)/CELL).astype(int), 0, NGRID-1) and line 690 evaluates "
    "inmask = mask[ijk], so mock galaxies outside the cube are not discarded but STACKED on the "
    "boundary voxel and tested against the mask there, and paper2_runner_fase3_mock.py never calls "
    "clipped_per_face on pos_sel. Record 16 declares prediction 1 with the threshold 'ratio above 2 "
    "at three or more of the six points', a denominator that assumes all six points are measured."
)

NEW_VALUE = {
    "gate_D5c": {
        "name": "zero clipping on the mock side, after the remapping",
        "requirement": ("PF.clipped_per_face(pos_sel, BOX_MIN, BOX_SIZE) must report n_clipped == 0 "
                        "at every grid point, in BOTH treatments; a non-zero count is a HARD STOP "
                        "for that point, not a warning"),
        "tolerance": 0,
        "blocking": True,
        "scope": "treatments (A) and (B), both hemispheres, all grid points",
        "rationale": ("Record 16 requires treatment (B) to apply 'exactly the data-side chain'. The "
                      "data-side chain refuses to measure a point with any clipped object. "
                      "Extending the same refusal to the mock side is therefore a SPECIFICATION of "
                      "record 16 and an extension of record 13 point (c) to the side it never "
                      "covered, not a new convention."),
        "why_a_late_gate_is_safe_here": ("The gate can only REJECT points, never accept more of "
                                         "them, so it cannot manufacture a favourable result. This "
                                         "is the property that makes it admissible after the "
                                         "deposit; a gate that could admit points would not be."),
        "reporting": ("A point that fails D5c is reported WITH its per-face clipped counts. A point "
                      "that is not measured is a datum, not a hole."),
    },
    "denominator_rule": {
        "why_needed": ("D5c can make points unmeasurable. Prediction 1 of record 16 is stated as "
                       "'above 2 at three or more of the six points', which is undefined if fewer "
                       "than six points exist. Deciding the denominator after the run - on the "
                       "surviving points or on the six nominal ones - is exactly the decision that "
                       "gate-first exists to prevent. It is therefore fixed here, before it is "
                       "known which points fall."),
        "rule": ("Prediction 1 is evaluated on the points ACTUALLY MEASURED. It is falsified if the "
                 "ratio stays above 2 at AT LEAST HALF of them, with a MINIMUM OF FOUR measured "
                 "points. Below four measured points the prediction is NOT EVALUABLE and is "
                 "reported as such."),
        "min_measured_points": 4,
        "falsify_fraction": 0.5,
        "not_evaluable_is_not_a_pass": True,
        "rejected_alternatives": {
            "six_nominal_always": ("evaluating on the six nominal points would let an unmeasured "
                                   "point count as non-falsifying, that is, it would reward the "
                                   "failure of the gate"),
            "fraction_without_minimum": ("a fraction with no floor is meaningless with two "
                                         "surviving points"),
        },
    },
}

REASON = (
    "Two declarations, both made before the first run of treatment (B) and both occasioned by "
    "reading paper2_runner_fase3.py and paper2_runner_fase3_mock.py against phase8_cutsky_mocks.py. "
    "FIRST: gate D5c. The data side refuses to measure a point at which any object falls outside "
    "the cube (record 13 point (c), enforced by a hard stop at lines 278 and 298 of the data "
    "runner). The mock side has never had that barrier, and phase8 line 688 stacks out-of-cube "
    "galaxies on the boundary voxel instead of discarding them. Under treatment (B) the galaxies "
    "are displaced radially and along line B towards F > 1 they move outward, so some WILL leave "
    "the frozen cube: without D5c the silent stacking would be counted as signal. D5c is the same "
    "refusal, applied to the side that lacked it. "
    "SECOND: the denominator of declared prediction 1. D5c can make points unmeasurable, and "
    "prediction 1 of record 16 counts 'three or more of the six points'. A gate that can change the "
    "denominator of an already declared prediction must be registered in the same ledger as that "
    "prediction, with the new denominator fixed BEFORE it is known which points fall. "
    "What is NOT registered here, and why: the optional capture= parameter of carve_cutsky, which "
    "lets the fiducial cache take rhat and z_obs in float64 where they are already computed, is "
    "INSTRUMENTATION. With capture=None the behaviour is unchanged bit for bit and no measured "
    "quantity can be altered by it. It is specified in checklist item 3.7 and verified by the "
    "existing D4a machinery (re-run of the FID path with --frozen-delta-dir, D4a_identical true on "
    "all 200 realisations), not by an amendment. If every code change became an amendment the "
    "ledger would stop being the record of analytical decisions and become a changelog."
)

EVIDENCE = (
    "paper2_runner_fase3.py lines 277-282: cl_r = PF.clipped_per_face(pos_r, box_min, box_size) "
    "followed by sys.exit if cl_r['n_clipped'], with the comment naming record 13 point (c). Lines "
    "296-301: the same for the data galaxies, cl_d, same hard stop. "
    "paper2_runner_fase3_mock.py one_mock(): no call to clipped_per_face anywhere; pos_sel goes "
    "straight into M.cic_3d at line 270. "
    "phase8_cutsky_mocks.py lines 688-690: ijk is np.clip-ed to [0, NGRID-1] and inmask = mask[ijk], "
    "so out-of-cube mock galaxies are mapped onto the boundary voxel and tested against the mask "
    "there; they can enter the selection. Already recorded in checklist item 3.0 as affecting 3.2 "
    "and not 3.1. "
    "On the shared downstream chain: one_mock already calls M.cic_3d, P1.compute_delta, "
    "M.build_field, M.compute_tda_features and F3.erosion_levels, the last of these imported from "
    "the DATA runner. There is no duplicated implementation downstream of the carving to unify; the "
    "'one implementation per quantity' clause of record 16 is descriptive of the existing code, not "
    "a change to it. The only mock-specific step is carve_cutsky itself, which is precisely what "
    "treatment (B) replaces with the cached remapping."
)

RULES = {
    "marker": MARKER,
    "companion_document": "paper2_item16.md (item 3.7 of the checklist, rev. 1.13)",
    "amends_record": 16,
    "verdict_unchanged": ("D5c does not enter DD_max and does not reopen the E1-E4 verdict, which "
                          "stays defined on treatment (A) over B1-B5 as deposited."),
    "gate_can_only_reject": ("D5c can only remove points from the measured set. It has no branch "
                             "that admits a point which would otherwise be excluded. This is the "
                             "property that makes a gate admissible after the deposit."),
    "applies_to_both_treatments": ("D5c is applied to (A) as well as (B). The clipped counts of (A) "
                                   "are informative in their own right: if a Phase-3 point had "
                                   "silently stacked galaxies, that is a fact about the frozen "
                                   "measurement and is to be reported, not corrected retroactively."),
    "capture_is_not_an_amendment": ("The optional capture= parameter of carve_cutsky is "
                                    "instrumentation, not a decision: with capture=None the "
                                    "behaviour is bit-identical and no measured quantity can "
                                    "change. It is specified in checklist 3.7 and verified by the "
                                    "existing D4a machinery, not registered here."),
    "why_the_cache_cannot_be_derived": ("Reconstructing (rhat, z_obs) by inverting pos_sel costs a "
                                        "few ulp on the round trip, so at the fiducial "
                                        "rhat * interp(z_obs, ...) would NOT be bit-identical to "
                                        "pos_sel and gate D5a would fail for a reason that is not a "
                                        "defect of the cache. Caching pos_sel itself and returning "
                                        "it verbatim at the fiducial would instead make D5a a gate "
                                        "that cannot fail, which record 16 forbids. The values must "
                                        "be taken inside carve_cutsky, where they exist in "
                                        "float64."),
    "declared_denominator": ("Prediction 1 of record 16 is evaluated on the points actually "
                             "measured: falsified if the ratio stays above 2 at at least half of "
                             "them, with a minimum of four measured points; below four it is NOT "
                             "EVALUABLE, which is not a pass."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E2 verdict, does not change the deposited grid, and does not "
                              "alter the thresholds of prediction 1 or 2 - only the denominator of "
                              "prediction 1, which record 16 left undefined for the case of "
                              "unmeasurable points."),
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
    chk("6  idempotenza (marker 17 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 16 e' gia' nel registro",
        MARKER_16 in blob)

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
        chk("10 regola del denominatore completa (meta', minimo 4, non-valutabile)",
            rec["new_value"]["denominator_rule"]["min_measured_points"] == MIN_MEASURED_POINTS
            and rec["new_value"]["denominator_rule"]["falsify_fraction"] == FALSIFY_FRACTION
            and rec["new_value"]["denominator_rule"]["not_evaluable_is_not_a_pass"] is True
            and len(rec["new_value"]["denominator_rule"]["rejected_alternatives"]) == 2)
        chk("11 tolleranza D5c esattamente zero e bloccante",
            rec["new_value"]["gate_D5c"]["tolerance"] == 0
            and rec["new_value"]["gate_D5c"]["blocking"] is True)
        chk("12 il cancello puo' solo rifiutare, ed e' scritto nel record",
            ("only REJECT" in txt) and ("only remove points" in txt))
        chk("13 capture= dichiarato NON emendamento, con la ragione",
            ("capture_is_not_an_amendment" in rec["rules"])
            and ("instrumentation" in rec["rules"]["capture_is_not_an_amendment"])
            and ("changelog" in rec["reason"]))
        chk("13f il record 16 e' sulla riga 16 e viene citato",
            (MARKER_16 in json.dumps(recs[15], ensure_ascii=False))
            and rec["rules"]["amends_record"] == 16)
        chk("13g D5c dichiarato su ENTRAMBI i trattamenti",
            "(A) and (B)" in rec["new_value"]["gate_D5c"]["scope"]
            or "applies_to_both_treatments" in rec["rules"])
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
        # Il denominatore dichiarato deve dare un esito definito per ogni numero
        # di punti superstiti da 0 a 6: se esiste un caso non coperto, la regola
        # e' incompleta e va riscritta ORA, non a run finito.
        def verdict(n_measured, n_above):
            if n_measured < MIN_MEASURED_POINTS:
                return "non-valutabile"
            return "falsificata" if n_above >= FALSIFY_FRACTION * n_measured else "sostenuta"
        outcomes = set()
        for n in range(0, 7):
            for a in range(0, n + 1):
                outcomes.add(verdict(n, a))
        chk("14 la regola del denominatore copre tutti i casi 0..6 punti",
            outcomes == {"non-valutabile", "falsificata", "sostenuta"},
            "esiti=%s" % sorted(outcomes))
    except Exception as exc:
        chk("14 regola del denominatore", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend17 rev.1 ===")
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
        fail("il record 17 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend18.py  (rev. 1) — Emendamento 18: rettifica - il gauge a cubo
costante fissa il lato e non l'origine; ritiro della predizione 2.

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

AMEND_POSITION = 18                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 17

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

MARKER = "emendamento-18-rettifica-gauge-origine"
MARKER_16 = "emendamento-16-osservabili-fisse"
MARKER_17 = "emendamento-17-cancello-clipping-mock"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "constant_cube_gauge_fixes_the_side_not_the_origin"

JSON_PATH = ("amendments record 16 (evidence field; declared prediction 2); "
             "amendments record 17 (evidence field); "
             "checklist item 1.4a (gauge fixes the side, not the origin)")

OLD_VALUE = (
    "Records 16 and 17 both state, in their evidence field, that under the constant-cube gauge "
    "'BOX_MIN, BOX_SIZE, CELL, NGRID, SIGMA_PX and the mask are frozen across the grid, so the "
    "tiling offsets (lines 652-657) and the mask array (line 690) are identical point by point: "
    "tiling is NOT a channel of variation. Only _Z_TAB/_DC_TAB and D_C_ZMIN/D_C_ZMAX vary. Box "
    "positions are fixed, hence dC = norm(P) and rhat do not change.' Record 16 builds declared "
    "prediction 2 on that premise: 'under treatment (A) WITHOUT RSD, Delta_mock is a pure "
    "re-selection effect, with positions invariant to 1e-16; expected order that of the carving "
    "re-randomisation term, -3.2 +/- 10.9 to +15.0 +/- 9.6 generators; FALSIFIED IF |Delta_mock| > "
    "53 generators.'"
)

NEW_VALUE = {
    "correction": {
        "what_is_false": ("The constant-cube gauge fixes the SIDE, not the ORIGIN. BOX_SIZE, CELL "
                          "and SIGMA_PX are constant across the grid; BOX_MIN is NOT. "
                          "paper2_runner_fase3_mock.py build_geometries() derives box_min per point "
                          "at line 195 from _box(GEO, pos_r, pad), and the randoms move with the "
                          "injected table; the mask is REDERIVED per point at line 207 from the "
                          "field_r built at that geometry. The tiling offsets depend on BOX_MIN: "
                          "phase8_cutsky_mocks.py line 653, lo, hi = BOX_MIN[axis], BOX_MIN[axis] + "
                          "BOX_SIZE, so which replicas are used changes, the inb selection at line "
                          "666 changes, P changes, and dC = norm(P) changes. Neither the mask nor "
                          "the tiling registration nor the galaxy distances are invariant across "
                          "the grid."),
        "already_stated_in_the_checklist": ("Item 1.4a says it explicitly: 'cubo costante fissa il "
                                            "lato, non l'origine. La chiusura di questa voce vale "
                                            "per sigma_px e non copre box_min.' The false claim was "
                                            "written despite that entry, not in ignorance of it."),
        "internal_check_that_was_not_run": ("Budget term (e), the voxel-count channel, exists ONLY "
                                            "because n_valid_voxels varies point to point. Had the "
                                            "mask been frozen, (e) would be identically zero. The "
                                            "referee's own section 3.2 proposes the intersection "
                                            "mask precisely in order TO MAKE n_valid_voxels "
                                            "constant by construction, which is vacuous if it "
                                            "already is. Either check refutes the claim in one "
                                            "step."),
        "channels_adopted": ("The referee's Hypothesis 1 lists the correct channels and is adopted "
                             "as it stands: the mask (through the randoms, which do deform), the "
                             "tiling registration, and the RSD residual. To these the grid "
                             "displacement is added, which is already measured by PF.grid_shift."),
    },
    "what_survives_and_why": {
        "round_trip_identity": ("interp(interp(dC, _DC_TAB, _Z_TAB), _Z_TAB, _DC_TAB) = dC to a few "
                                "ulp (1.9e-16 measured) is a statement about the TABLES ALONE and "
                                "is unaffected. Without RSD the z -> r' map does not itself displace "
                                "a galaxy relative to its real-space distance."),
        "core_finding_of_record_16": ("Treatment (A) does NOT apply the AP distortion to the "
                                      "underlying radial coordinate, whereas the data side does. "
                                      "This is unchanged, and it is the finding record 16 exists "
                                      "for."),
        "gate_D5a": ("Justified by 'same np.interp, same table, same input bits at the fiducial'. "
                     "Does not depend on box_min. Intact."),
        "gate_D5b": "Intact.",
        "gate_D5c_and_denominator": ("Intact. D5c is STRENGTHENED: if box_min moves across the "
                                     "grid, out-of-cube displacement is a live risk rather than a "
                                     "marginal one."),
        "naming_rectification_and_quotation_rule": ("Intact. 'Treatment (A) regenerates the "
                                                    "box-to-sky mapping at each fiducial' is MORE "
                                                    "true under this correction, not less."),
        "no_gate_was_created_by_mistake": ("No gate rests on the false premise. What rests on it is "
                                           "one sentence of evidence, repeated in two records, and "
                                           "declared prediction 2."),
    },
    "withdrawn": {
        "target": "record 16, declared_prediction_real_space (prediction 2)",
        "status": "WITHDRAWN, not falsified and not repaired",
        "reason": ("Its premise - that under (A) without RSD only the selection changes - is false. "
                   "A prediction whose premise is false was never testable as stated: withdrawing "
                   "it is not the same as declaring it falsified, and it must not be reported as "
                   "either satisfied or falsified."),
        "threshold_was_not_discriminating": ("The 53-generator threshold discriminated nothing, "
                                             "because the voxel channel alone is larger than 53 and "
                                             "would have triggered the threshold irrespective of "
                                             "the RSD mechanism."),
        "precedent": "record 13 uses the same key for a withdrawn item",
    },
    "prediction_2_restated": {
        "status": "declared, not yet decided; replaces the withdrawn prediction 2 of record 16",
        "statement": ("Under treatment (A) in REAL SPACE (no RSD), the residual AFTER subtraction "
                      "of budget term (e), the voxel-count channel, is of the order of the "
                      "remaining registration channels - tiling registration and grid displacement "
                      "- and NOT of the order of the redshift-space response."),
        "why_the_subtraction_is_required": ("In real space the mask still moves with box_min, so "
                                            "the voxel channel is present and is larger than the "
                                            "detectability threshold on its own. Evaluating the raw "
                                            "Delta_mock would test nothing. Term (e) is subtracted "
                                            "here exactly as everywhere else in Phase 3, with the "
                                            "slope measured on D."),
        "falsification": ("The mechanism claim 'the redshift-space response of treatment (A) is "
                          "dominated by the rescaling of the RSD displacement' is FALSIFIED IF the "
                          "real-space residual after (e) reaches at least HALF of the "
                          "redshift-space residual after (e), in at least half of the measured "
                          "points, in both hemispheres. Stated as a ratio because the absolute "
                          "scale of the residual is itself the unexplained quantity of Phase 3 and "
                          "cannot serve as a reference."),
        "not_repaired_afterwards": True,
    },
}

REASON = (
    "A rectification of two evidence statements and the withdrawal of one declared prediction, made "
    "BEFORE any run of treatment (B) and before any real-space run. No measurement is contaminated: "
    "nothing has been measured under either. "
    "THE ERROR: records 16 and 17 assert that the constant-cube gauge freezes BOX_MIN and the mask "
    "across the grid, and that tiling is not a channel of variation. The gauge fixes the SIDE, not "
    "the ORIGIN. box_min is derived per point from randoms that deform with the injected table, the "
    "mask is rederived per point, and the tiling offsets are computed from BOX_MIN. Checklist item "
    "1.4a states this explicitly, and budget term (e) exists only because the voxel count varies: "
    "the claim was refutable in one step by either route and was written anyway. "
    "WHAT THIS IS NOT: no gate rests on the false premise. D5a is justified by the identity of the "
    "np.interp call at the fiducial, D5b by the frozen baseline, D5c by the data-side chain; the "
    "naming rectification and the quotation rule of record 16 are untouched, and the central "
    "finding - that treatment (A) does not apply the AP distortion to the radial coordinate while "
    "the data side does - survives, because the round-trip identity is a property of the tables "
    "alone. "
    "WHY IT IS REGISTERED RATHER THAN ERASED: erasing records 16 and 17 would require rewriting an "
    "append-only file, and the claim is in any case already carried by checklist revisions 3.12 and "
    "3.13, whose historical changelog blocks are not rewritten. The choice is therefore between a "
    "ledger that explains the correction and a checklist that silently contradicts it. A "
    "self-correction taken before any run is evidence that the discipline works; two records "
    "disappearing the day after they were written, one of them carrying a declared prediction, is "
    "not explicable if it ever surfaces. "
    "PREDICTION 2 IS WITHDRAWN, NOT FALSIFIED. Its premise is false, so it was never testable as "
    "stated. It is replaced here by a restated prediction with a ratio-based threshold, declared "
    "before the run."
)

EVIDENCE = (
    "paper2_runner_fase3_mock.py build_geometries(): line 195, box_min, box_size = _box(GEO, pos_r, "
    "pad), computed per point inside the loop over the point plan; line 207, "
    "mask = field_r > 0.01 * field_r.mean(), rederived per point; line 214, n_valid_voxels stored "
    "per geometry and printed per point at line 216; the fiducial-only check at lines 218-220 "
    "confirms that only FID is asserted against a frozen voxel count. "
    "phase8_cutsky_mocks.py carve_cutsky(): line 653, lo, hi = BOX_MIN[axis], BOX_MIN[axis] + "
    "BOX_SIZE inside offsets(), so the replica range depends on the cube origin; line 664-665, "
    "shift = [kx,ky,kz] * BOXSIZE_MOCK and P = pos_gal + shift; line 666-667, inb tested against "
    "BOX_MIN and BOX_MIN + BOX_SIZE; line 673, dC = np.linalg.norm(P, axis=1). A change in BOX_MIN "
    "therefore propagates to which replicas contribute, which galaxies pass inb, P, dC and rhat. "
    "Checklist item 1.4a: the constant-cube closure covers sigma_px and does NOT cover box_min, "
    "which is question (b) of item 0.14 and remains open. "
    "Budget term (e), the voxel-count channel, is non-zero by measurement, which is possible only "
    "if n_valid_voxels varies across the grid. Referee report section 3.2 proposes the intersection "
    "mask in order to make n_valid_voxels constant by construction. "
    "The referee's Hypothesis 1 in section 1 lists the correct channels - the mask through the "
    "randoms, the tiling registration, the RSD residual - and is adopted."
)

RULES = {
    "marker": MARKER,
    "companion_document": "paper2_item16.md (items 1.4b, 3.7 and 3.8 of the checklist, rev. 3.14)",
    "amends_records": [16, 17],
    "no_gate_withdrawn": ("D5a, D5b, D5c and the denominator rule of record 17 are unaffected and "
                          "remain in force. This record withdraws one prediction and corrects two "
                          "evidence statements."),
    "verdict_unchanged": ("Does not enter DD_max, does not reopen the E1-E4 verdict, does not touch "
                          "any frozen value."),
    "withdrawn_is_not_falsified": ("A prediction withdrawn for a false premise must not be reported "
                                   "as falsified. Reporting it as falsified would be the same class "
                                   "of error the referee identifies in section 4.1 for the second "
                                   "B6 prediction: claiming a falsification the evidence does not "
                                   "support."),
    "error_found_before_any_run": ("Found BEFORE any run: neither treatment (B) nor the "
                                   "real-space line B has been executed. "
                                   "The correction is therefore complete: no measurement "
                                   "rests on the false premise, and nothing is repaired "
                                   "retroactively."),
    "how_it_was_found": ("Reading the referee report against checklist item 1.4a. The referee's "
                         "mechanism analysis was right and the record's was wrong."),
    "declared_prediction_restated": ("See new_value.prediction_2_restated: falsified if the "
                                     "real-space residual after term (e) reaches at least half of "
                                     "the redshift-space residual after term (e), in at least half "
                                     "of the measured points, in both hemispheres."),
    "what_this_does_not_do": ("It modifies no frozen value, creates no gate, removes no gate, and "
                              "changes no threshold of record 17."),
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
    chk("6  idempotenza (marker 18 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: i record 16 e 17 sono gia' nel registro",
        (MARKER_16 in blob) and (MARKER_17 in blob))

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
        chk("10 l'affermazione falsa e' citata per intero in old_value",
            ("frozen across the grid" in rec["old_value"])
            and ("tiling is NOT a channel of variation" in rec["old_value"])
            and ("pure re-selection effect" in rec["old_value"]))
        chk("11 ritiro: WITHDRAWN e non falsificata, con la ragione",
            rec["new_value"]["withdrawn"]["status"].startswith("WITHDRAWN")
            and ("not the same as declaring it falsified"
                 in rec["new_value"]["withdrawn"]["reason"])
            and ("must not be reported as falsified"
                 in rec["rules"]["withdrawn_is_not_falsified"]))
        chk("12 nessun cancello ritirato: D5a, D5b, D5c e denominatore restano",
            all(k in rec["rules"]["no_gate_withdrawn"] for k in ("D5a", "D5b", "D5c"))
            and all(k in rec["new_value"]["what_survives_and_why"]
                    for k in ("gate_D5a", "gate_D5b", "gate_D5c_and_denominator")))
        chk("13 predizione 2 riformulata come RAPPORTO, non come soglia assoluta",
            ("at least HALF of the" in rec["new_value"]["prediction_2_restated"]["falsification"])
            and (str(REALSPACE_FALSIFY_GEN)
                 not in rec["new_value"]["prediction_2_restated"]["falsification"])
            and rec["new_value"]["prediction_2_restated"]["not_repaired_afterwards"] is True)
        chk("13f i record 16 e 17 sono alle righe 16 e 17 e sono citati entrambi",
            (MARKER_16 in json.dumps(recs[15], ensure_ascii=False))
            and (MARKER_17 in json.dumps(recs[16], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [16, 17])
        chk("13g le due prove indipendenti dell'errore sono nel record",
            ("term (e)" in txt) and ("intersection mask" in txt) and ("1.4a" in txt))
        chk("13h errore trovato PRIMA di qualunque run, ed e' dichiarato",
            "before" in rec["rules"]["error_found_before_any_run"].lower()
            and "BEFORE any run" in rec["reason"])
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
        # Il ritiro deve essere completo: quel che sopravvive e quel che cade non
        # possono sovrapporsi, e insieme devono coprire cio' che il record 16
        # poggiava sulla premessa falsa.
        surv = set(rec["new_value"]["what_survives_and_why"]) if rec else set()
        fell = {rec["new_value"]["withdrawn"]["target"]} if rec else set()
        chk("14 ritiro coerente: nulla e' insieme salvo e ritirato",
            bool(surv) and not (surv & fell)
            and "prediction 2" in rec["new_value"]["withdrawn"]["target"])
    except Exception as exc:
        chk("14 coerenza del ritiro", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend18 rev.1 ===")
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
        fail("il record 18 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

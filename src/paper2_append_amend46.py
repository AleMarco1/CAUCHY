#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend46.py - Emendamento 46: il terzo canale e' misurato, e la
firma dichiarata e' SMENTITA nel verso opposto. Item 3.2e, risposta 5.

PREREQUISITO: il record 45 (diagnostica geometrica) deve essere sulla riga 45.
I numeri degli emendamenti non sono prenotati - sono la POSIZIONE nel file - e
questo record e' il 46 solo se il 45 c'e'. Il cancello G6b lo impone.

I fatti si RILEGGONO dai registri: gli otto Delta dalla passata a maschera
fissa, i pavimenti da fase3_budget.jsonl, i quattro esponenti e i residui dal
registro del fit. Nessun numero trascritto.

Cancelli
--------
  G1..G4, G6   come nei record 43-45;
  M1  la passata a maschera fissa ha 16 record, otto per emisfero, con
      n_valid_voxels COSTANTE dentro l'emisfero: e' cio' che rende il termine
      (e) inesistente per costruzione;
  M2  gli otto |Delta| ricalcolati coincidono con quelli citati;
  M3  il verdetto contro il pavimento coincide con quello citato;
  M4  C4 e' SOTTO soglia in tutti e quattro i casi -- il pezzo piu' pulito
      della smentita;
  M5  il registro del fit ha i quattro esponenti e i quattro residui.

Uscita ASCII pura.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

AMEND_POSITION = 46
EXPECTED_LINES_BEFORE = 45

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")
FISSO = os.path.join("results", "paper2", "fase3_surrogato_fisso.jsonl")
BUDGET = os.path.join("results", "paper2", "fase3_budget.jsonl")
FIT = os.path.join("results", "paper2", "surrogato_aff.jsonl")

ANGOLI = ("C1", "C4", "C2", "C3")
VOXEL_ATTESI = {"NGC": 305533, "SGC": 168643}

# Residui non modellati dal fit, in voxel. La firma li ordinava.
RES_VOX = {"C1": 0.0822, "C4": 0.0473, "C2": 0.0062, "C3": 0.0051}

# Gli otto |Delta| citati nel testo. Il selftest li RICALCOLA.
DELTA = {
    ("NGC", "k0"): {"C1": 37, "C4": 22, "C2": 9, "C3": 48},
    ("NGC", "k1"): {"C1": 22, "C4": 5, "C2": 74, "C3": 77},
    ("SGC", "k0"): {"C1": 81, "C4": 4, "C2": 56, "C3": 68},
    ("SGC", "k1"): {"C1": 0, "C4": 13, "C2": 72, "C3": 71},
}
PAVIMENTI = {("NGC", "k0"): 51.1, ("NGC", "k1"): 33.0,
             ("SGC", "k0"): 34.6, ("SGC", "k1"): 27.5}

MARKER = "emendamento-46-terzo-canale-misurato-firma-smentita"
MARKER_45 = "emendamento-45-scala-geometrica-del-ripattern-e-suo-limite"
COMPANION_DOCUMENT = "paper2_item32e_surrogato.md; risposta_referee.md risposta 5"


KEY = "the_third_channel_is_measured_and_the_declared_signature_is_falsified_in_the_opposite_direction"

JSON_PATH = ("src/paper2_surrogato_fit.py; src/paper2_runner_fase3.py (point_plan, "
             "load_corners_aff); results/paper2/surrogato_aff.jsonl; "
             "results/paper2/fase3_surrogato_fisso.jsonl")

OLD_VALUE = (
    "Response 5 was BLOCKED. The deposited completeness test compared D_obs with a D_pred from a "
    "MODEL, and CORNER_F was empty because a corner is a TRAJECTORY in F(z), not a value - for C1 it "
    "sweeps 0.9611 to 0.9856. The referee's design removes the model entirely: run the corner with "
    "its true deformation, run its affine minimax surrogate as a SEPARATE grid point, and the "
    "difference D(C) - D(C_aff) IS the third channel, measured directly. Item 3.2e declared the "
    "signature before the run: above the block-A floor at C1 and C4, where the unmodelled channel is "
    "0.0822 and 0.0473 voxel, and below at C2 and C3, where it is 0.0062 and 0.0051."
)

NEW_VALUE = {
    "what_was_built": {
        "the_fitter": ("A two-parameter minimax against the corner's true D_C, wrapping deform_ap "
                       "and minimax_alpha - no second implementation of the minimax. Three gates: "
                       "at p = 1 the residual equals the deposited one-parameter minimax; the null "
                       "corner gives p = 1 and residual 0; the fit reduces and p stays inside the "
                       "line-B bracket. It REPRODUCES the documented residuals: 0.0822, 0.0473, "
                       "0.0062 and 0.0051 voxel, against 0.082, 0.047, 0.006 and 0.005 in checklist "
                       "1.3 - four figures on four independent corners. Those numbers had "
                       "documentary provenance and now have code provenance."),
        "the_grid": ("A surrogate is STRUCTURALLY a line-B point: dict(kind='ap', alpha_iso=1.0, "
                     "F_ap=p). No new kind, one extra list, block 'Caff'. The exponents are READ "
                     "from the fit register, never written into the code. And built with deform, "
                     "NOT make_dc_tab_ap: the two differ by one ULP and a gate at delta == 0 exact "
                     "does not tolerate it."),
        "the_non_regression_gate": ("With the patch applied and no --surrogato, B1 in NGC gives "
                                    "28194 / 23791, identical to the frozen values. The patch is "
                                    "inert on the existing path."),
    },
    "a_defect_in_the_ANALYSIS_caught_before_it_was_written": {
        "what": ("The first comparison put a RAW |Delta N| against prop2_floor. But prop2_floor is "
                 "the maximum |b_residual| over block A, that is a residual ALREADY corrected for "
                 "term (e), the mask-count correction. Two different quantities."),
        "how_much_it_mattered": ("The mask differs between a corner and its surrogate by up to 1686 "
                                 "voxels, which at slope_data_side = 0.1009 generators per voxel is "
                                 "170 generators - nearly twice the raw signal. The verdict flipped "
                                 "sign depending on whether the correction was applied."),
        "and_correcting_it_was_not_enough": ("Section 4.4 measures the LOCAL boundary elasticity at "
                                             "1.71 against the global 1.08, so subtracting with a "
                                             "mean slope leaves ~0.59 of the corrected amplitude - "
                                             "about 100 generators on NGC C1, larger than everything "
                                             "being looked for."),
        "the_fix": ("--mask-intersect-out over the EIGHT points, then --mask-fixed. n_valid_voxels "
                    "becomes constant by construction and term (e) DOES NOT EXIST rather than being "
                    "subtracted. 305533 voxels in NGC, 168643 in SGC. The machinery already existed, "
                    "built for §3.2."),
    },
    "the_result": {
        "NGC_k0": "C1 37, C4 22, C2 9, C3 48, against a floor of 51.1: all below.",
        "NGC_k1": "C1 22, C4 5, C2 74, C3 77, against 33.0: C2 and C3 above.",
        "SGC_k0": "C1 81, C4 4, C2 56, C3 68, against 34.6: C1, C2, C3 above.",
        "SGC_k1": "C1 0, C4 13, C2 72, C3 71, against 27.5: C2 and C3 above.",
    },
    "THE_DECLARED_SIGNATURE_IS_FALSIFIED": {
        "what_was_declared": ("Above threshold at C1 and C4, below at C2 and C3. Declared in item "
                              "3.2e §3 before any run."),
        "what_happened": ("The ORDERING IS REVERSED. C2 and C3 - the two smallest unmodelled "
                          "channels, 0.0062 and 0.0051 voxel - are above threshold in three of four "
                          "cases. C4, the second LARGEST at 0.0473, is below in all four: 22, 5, 4, "
                          "13 generators. It is not signal-not-seen; it is the opposite ordering, "
                          "reproduced in two independent hemispheres."),
        "it_is_registered_as_falsified": ("Not rewritten, not weakened, not reinterpreted into a "
                                          "success. The prediction was declared, tested and failed, "
                                          "and it stays in the record as failed."),
        "and_the_confirmation_of_record_earlier_stands": ("The fitter DOES reproduce 0.082 and "
                                                          "0.047, so those numbers are right. They "
                                                          "simply do not PREDICT where D(C) - "
                                                          "D(C_aff) is large. Reproducing a quantity "
                                                          "and that quantity having predictive power "
                                                          "are different claims, and only the first "
                                                          "was established."),
    },
    "an_a_posteriori_hypothesis_declared_as_such": ("The large Deltas sit where du - the grid shift "
                                                    "against the fiducial - is SMALL: 0.14 and 0.18 "
                                                    "at C2 and C3 against 0.77 and 0.53 at C1 and "
                                                    "C4. It would be consistent with §4.4, where the "
                                                    "channel that matters is the boundary mask with "
                                                    "local elasticity 1.71. This hypothesis was born "
                                                    "LOOKING AT these numbers and is recorded as a "
                                                    "posteriori, not as an explanation. Testing it "
                                                    "needs points chosen to separate du from the "
                                                    "residual, which the current grid does not."),
    "three_reserves": {
        "the_floor_is_computed_on_the_FULL_mask": ("These Deltas are on the intersection, smaller by "
                                                   "0.8% in NGC and 2% in SGC. It is the same class "
                                                   "of mismatch as the (e) term just corrected - two "
                                                   "quantities on different domains - and it is "
                                                   "small but stated. Rigour would recompute "
                                                   "prop2_floor on the fixed mask."),
        "the_data_side_has_no_second_denominator": ("It is deterministic but it is ONE realisation. "
                                                    "Response 1 requires that no sigma be written "
                                                    "without saying which question it answers; here "
                                                    "the second denominator is unavailable without "
                                                    "mocks."),
        "eight_numbers_over_two_levels": ("Few for a law. The coherence between hemispheres makes it "
                                          "more than chance, but it is not a measurement of a "
                                          "mechanism."),
    },
    "what_this_does_not_do": ("It does not touch Phase 3's frozen values, does not reopen the "
                              "budget, and adds no mock: the four surrogates are data-side only. "
                              "Whether the mocks are worth adding is now answerable - and the answer "
                              "is that the declared design would not test the declared signature, "
                              "because that signature is falsified."),
}

RULES = {
    "amends_records": [],
    "a_declared_prediction_that_fails_stays_failed": ("Not rewritten, not weakened, not "
                                                      "reinterpreted. Item 3.2e §3 declared it and "
                                                      "the measurement falsified it."),
    "reproducing_a_number_is_not_the_same_as_that_number_predicting": ("The fitter reproduces 0.082 "
                                                                       "and 0.047 to four figures. "
                                                                       "They still do not order the "
                                                                       "measured effect."),
    "companion_document": COMPANION_DOCUMENT,
    "compare_quantities_defined_on_the_same_domain": ("A raw |Delta N| against a floor built from "
                                                      "(e)-corrected residuals is not a comparison. "
                                                      "The mask-fixed pass removes the term instead "
                                                      "of subtracting it."),
    "marker": MARKER,
    "an_a_posteriori_hypothesis_is_labelled_a_posteriori": ("The du anti-correlation was born looking "
                                                            "at the numbers and is recorded as such."),
    "what_this_does_not_do": ("No frozen value touched, no mock added, budget not reopened."),
}

REASON = (
    "Response 5 is closed, and it closes with a FALSIFICATION. The referee's design removed the model "
    "that had blocked the section: run the corner with its true deformation, run its affine minimax "
    "surrogate as a separate grid point, and the difference IS the third channel. Item 3.2e declared "
    "the signature before any run - above the block-A floor at C1 and C4, where the unmodelled "
    "channel is 0.0822 and 0.0473 voxel, below at C2 and C3 where it is 0.0062 and 0.0051. WHAT WAS "
    "BUILT: a two-parameter minimax fitter wrapping the existing minimax, with three gates, which "
    "REPRODUCES the documented residuals to four figures on four independent corners; a grid patch "
    "where a surrogate is structurally a line-B point and the exponents are READ from the fit "
    "register; and a non-regression gate showing B1 unchanged at 28194 / 23791. A DEFECT IN THE "
    "ANALYSIS was caught before it was written down: the first comparison put a RAW |Delta N| against "
    "prop2_floor, which is built from residuals ALREADY corrected for term (e). The masks differ by "
    "up to 1686 voxels, worth 170 generators at 0.1009 per voxel, and the verdict flipped sign "
    "depending on the correction. Correcting with a mean slope was not enough either, because §4.4 "
    "measures the local boundary elasticity at 1.71 against the global 1.08. The fix was the §3.2 "
    "machinery: intersection over the eight points, then a fixed mask, so term (e) does not exist "
    "rather than being subtracted. THE RESULT. With n_valid_voxels constant - 305533 in NGC, 168643 "
    "in SGC - the ordering is REVERSED. C2 and C3, the two smallest channels, are above threshold in "
    "three of four cases; C4, the second largest, is below in all four at 22, 5, 4 and 13 generators. "
    "Not signal-not-seen: the opposite ordering, reproduced in two independent hemispheres. It is "
    "registered as falsified. The earlier confirmation stands as far as it went - the fitter does "
    "reproduce 0.082 and 0.047 - but reproducing a quantity and that quantity having predictive power "
    "are different claims, and only the first was established. An a posteriori hypothesis is recorded "
    "AS a posteriori: the large Deltas sit where du is small, which would fit §4.4's boundary-mask "
    "channel, but it was born looking at these numbers and testing it needs points that separate du "
    "from the residual."
)

EVIDENCE = (
    "Runs of 5 Sep 2026. Fit: p = 1.0289029, 0.9945301, 1.0070012, 0.9806182 for C1..C4, residuals "
    "8.8751 -> 1.2831, 1.6447 -> 0.0966, 2.0999 -> 0.0790, 5.6225 -> 0.7380 h^-1 Mpc, i.e. 0.0822, "
    "0.0062, 0.0051 and 0.0473 voxel at dx = 15.604397786848558; the one-parameter residual of C1, "
    "8.8751, reproduces RESID_MAX_HMPC = 8.875, the constant anchoring B1 and B5. Grid patch: "
    "paper2_runner_fase3.py 30191 -> 33753 bytes, sha256 bb3932058a7ac06d... -> b8d6a0fd8fbc2f44..., "
    "four edits, one definition of point_plan. Non-regression: B1 NGC 28194 / 23791 against the "
    "frozen 28194 / 23791. Pass 1, eight points: intersection 305533 voxels in NGC and 168643 in SGC. "
    "Pass 2, mask fixed, |Delta| at k=0 and k=1: NGC C1 37 and 22, C4 22 and 5, C2 9 and 74, C3 48 "
    "and 77; SGC C1 81 and 0, C4 4 and 13, C2 56 and 72, C3 68 and 71. Floors from "
    "fase3_budget.jsonl prop2_floor: 51.13221154660196 and 32.96 in NGC, 34.61 and 27.51 in SGC. "
    "Grid shifts du: 0.7725, 0.5268, 0.1423, 0.1782 at C1, C4, C2, C3 in NGC. Before the fixed mask "
    "the same comparison gave the opposite verdict at several corners, which is the defect this "
    "record registers."
)

# ---------------------------------------------------------------------------
# Utilita'
# ---------------------------------------------------------------------------

def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_jsonl(raw):
    """Spezza su LF e toglie un CR finale: robusto ai fine riga MISTI.
    Assumere un terminatore uniforme incolla due record quando non lo e'."""
    parts = raw.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    lines, terms = [], []
    for pt in parts:
        if pt.endswith(b"\r"):
            lines.append(pt[:-1])
            terms.append(b"\r\n")
        else:
            lines.append(pt)
            terms.append(b"\n")
    keep = [(l, t) for l, t in zip(lines, terms) if l.strip()]
    return [l for l, _ in keep], [t for _, t in keep]


def eol_profile(terms):
    """(n_crlf, n_lf, posizioni 1-based delle righe che deviano dalla maggioranza)."""
    n_crlf = sum(1 for t in terms if t == b"\r\n")
    n_lf = len(terms) - n_crlf
    major = b"\r\n" if n_crlf >= n_lf else b"\n"
    odd = [i for i, t in enumerate(terms, start=1) if t != major]
    return n_crlf, n_lf, odd


def read_jsonl(path):
    """Ritorna (recs, newline, pure_ascii, sorted_keys, raw, righe, terminatori).
    `newline` e' il terminatore dell'ULTIMA riga: e' dopo quella che si appende."""
    with open(path, "rb") as f:
        raw = f.read()
    lines, terms = split_jsonl(raw)
    newline = terms[-1] if terms else b"\r\n"
    pure_ascii = all(b < 128 for b in raw)
    recs = []
    for i, ln in enumerate(lines, start=1):
        try:
            recs.append(json.loads(ln.decode("utf-8")))
        except Exception as exc:
            fail("%s riga %d non e' JSON valido: %s" % (path, i, exc))
    sorted_keys = all(list(r.keys()) == sorted(r.keys()) for r in recs)
    return recs, newline, pure_ascii, sorted_keys, raw, lines, terms


def read_ledger(path):
    return read_jsonl(path)


def utc_now():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def common_keys(recs, n=3):
    tail = recs[-n:] if len(recs) >= n else recs
    s = set(tail[0].keys())
    for r in tail[1:]:
        s &= set(r.keys())
    return sorted(s)




def _renumber(rule, position):
    """La numbering_rule della riga precedente termina con 'This is record 41.':
    ereditarla verbatim scriverebbe il numero sbagliato. Si riscrive l'ultimo
    intero della stringa con la posizione effettiva."""
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
        else:
            rec[k] = "__DA_DICHIARARE__"
            unfilled.append(k)

    rec["rules"] = RULES
    rec = {k: rec[k] for k in sorted(rec.keys())}
    extras = sorted(set(rec.keys()) - set(required))
    return rec, unfilled, extras, required









def analyse_gates():
    """Ricalcola gli otto Delta e i verdetti dai registri. Nessun numero trascritto."""
    out = {"errore": None, "voxel": {}, "delta": {}, "pav": {}, "fit": {}}
    for p in (FISSO, BUDGET, FIT):
        if not os.path.isfile(p):
            out["errore"] = "registro assente: %s" % p
            return out
    D = {}
    for r in read_jsonl(FISSO)[0]:
        if r.get("region") and r.get("point"):
            D[(r["region"], r["point"])] = r
    for g in ("NGC", "SGC"):
        vx = sorted({D[(g, p)]["n_valid_voxels"] for p in D if p[0] == g}
                    ) if False else sorted(
            {v["n_valid_voxels"] for (gg, _), v in D.items() if gg == g})
        out["voxel"][g] = vx
        for lev, campo in (("k0", "N_H1_k0"), ("k1", "N_H1")):
            out["delta"][(g, lev)] = {}
            for c in ANGOLI:
                a, b = D.get((g, c)), D.get((g, c + "aff"))
                if a is None or b is None:
                    out["delta"][(g, lev)][c] = None
                else:
                    out["delta"][(g, lev)][c] = abs(int(a[campo]) - int(b[campo]))
    U = {}
    for r in read_jsonl(BUDGET)[0]:
        if r.get("region"):
            U[r["region"]] = r
    for g in ("NGC", "SGC"):
        for lev in ("k0", "k1"):
            try:
                out["pav"][(g, lev)] = float(U[g]["levels"][lev]["prop2_floor"])
            except Exception:
                out["pav"][(g, lev)] = None
    for r in read_jsonl(FIT)[0]:
        if r.get("schema") == "paper2_surrogato_v1":
            out["fit"][r["point_aff"]] = (float(r["p"]), float(r["res_2p_hMpc"]))
    return out


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest(ledger, reference, item, overrides, verbose=True):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    if not os.path.isfile(ledger):
        chk("1  registro presente", False, ledger)
        return _report(checks, verbose)
    chk("1  registro presente", True, ledger)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(ledger)

    chk("2  righe = %d" % EXPECTED_LINES_BEFORE, len(recs) == EXPECTED_LINES_BEFORE,
        "trovate %d -- se sono 44, appendi prima il record 45" % len(recs))
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    chk("2b la riga %d si ri-serializza byte per byte identica" % len(recs),
        rt == lines[-1])

    ok_ref = os.path.isfile(reference)
    file_sha = sha256_file(reference) if ok_ref else ""
    chk("3  sha256 del reference invariato", file_sha == REFERENCE_FILE_SHA256,
        file_sha[:16] if file_sha else "assente")
    chk("4  digest = quello citato nella riga %d" % len(recs),
        recs[-1].get("reference_file_sha256") == file_sha)
    self_sha = ""
    if ok_ref:
        self_sha = json.load(open(reference, "r", encoding="utf-8")).get("_self_sha256", "")
    chk("5  _self_sha256 presente, atteso, e uguale a quello della riga %d" % len(recs),
        bool(self_sha) and self_sha == REFERENCE_SELF_SHA
        and self_sha == recs[-1].get("reference_self_sha256"))

    blob = raw.decode("utf-8", "replace")
    dup = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 46 assente, item non gia' usato)",
        (MARKER not in blob) and not dup)
    chk("6b PREREQUISITO: il record 45 e' presente ED e' sulla riga %d"
        % EXPECTED_LINES_BEFORE,
        (MARKER_45 in blob)
        and len(recs) >= EXPECTED_LINES_BEFORE
        and (MARKER_45 in json.dumps(recs[EXPECTED_LINES_BEFORE - 1],
                                     ensure_ascii=False)),
        "i numeri non sono prenotati: senza il 45 questo record e' il 45, non il 46")

    n_crlf, n_lf, odd = eol_profile(terms)
    chk("7  convenzioni: ascii_puro=%s ordinate=%s; CRLF=%d LF=%d"
        % (pure_ascii, sorted_keys, n_crlf, n_lf), True,
        ("fuori maggioranza: %s - preesistente" % odd) if odd else "uniformi")

    G = analyse_gates()
    if G["errore"]:
        chk("M1 registri della misura presenti", False, G["errore"])
        return _report(checks, verbose)

    bad = []
    for g in ("NGC", "SGC"):
        vx = G["voxel"][g]
        if vx != [VOXEL_ATTESI[g]]:
            bad.append("%s: n_valid_voxels %s, atteso il solo %d"
                       % (g, vx, VOXEL_ATTESI[g]))
    chk("M1 maschera FISSA: n_valid_voxels costante dentro l'emisfero",
        not bad, ",".join(bad) if bad
        else "NGC %d, SGC %d" % (VOXEL_ATTESI["NGC"], VOXEL_ATTESI["SGC"]))

    bad2 = []
    for k, att in sorted(DELTA.items(), key=lambda x: str(x[0])):
        got = G["delta"].get(k, {})
        for c in ANGOLI:
            if got.get(c) != att[c]:
                bad2.append("%s/%s/%s: %r contro %r citato" % (k[0], k[1], c,
                                                               got.get(c), att[c]))
    chk("M2 gli otto |Delta| RICALCOLATI coincidono con quelli citati",
        not bad2, ",".join(bad2) if bad2 else "sedici valori")

    bad3 = []
    for k, att in sorted(PAVIMENTI.items(), key=lambda x: str(x[0])):
        p = G["pav"].get(k)
        if p is None or abs(p - att) > 0.06:
            bad3.append("%s/%s: pavimento %r contro %r citato" % (k[0], k[1], p, att))
    chk("M3 i pavimenti letti dal budget coincidono con quelli citati",
        not bad3, ",".join(bad3) if bad3 else "quattro pavimenti")

    sopra_c4 = [k for k in DELTA
                if G["delta"][k]["C4"] > (G["pav"][k] or float("inf"))]
    chk("M4 C4 e' SOTTO soglia in tutti e quattro i casi",
        not sopra_c4, "sopra in %s" % sopra_c4 if sopra_c4
        else "22, 5, 4, 13 contro pavimenti 51.1, 33.0, 34.6, 27.5")

    inversi = []
    for k in DELTA:
        d, p = G["delta"][k], G["pav"][k]
        piccoli_sopra = sum(1 for c in ("C2", "C3") if d[c] > p)
        grandi_sopra = sum(1 for c in ("C1", "C4") if d[c] > p)
        if piccoli_sopra > grandi_sopra:
            inversi.append("%s/%s" % k)
    chk("M4b l'ordinamento e' INVERSO in almeno tre casi su quattro",
        len(inversi) >= 3, "inverso in %s" % inversi)

    chk("M5 il registro del fit ha i quattro esponenti e i residui",
        sorted(G["fit"]) == ["C1aff", "C2aff", "C3aff", "C4aff"],
        str(sorted(G["fit"])))

    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha,
                                                       self_sha, item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 43-45 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 la SMENTITA e' dichiarata come smentita",
            "THE_DECLARED_SIGNATURE_IS_FALSIFIED" in rec["new_value"]
            and "stays in the record as failed" in rec["new_value"]
            ["THE_DECLARED_SIGNATURE_IS_FALSIFIED"]["it_is_registered_as_falsified"])
        chk("11 la distinzione riprodurre / predire e' scritta",
            "having predictive power" in rec["new_value"]
            ["THE_DECLARED_SIGNATURE_IS_FALSIFIED"]
            ["and_the_confirmation_of_record_earlier_stands"])
        chk("12 il difetto dell'analisi e' registrato con quanto pesava",
            "1686" in json.dumps(rec["new_value"]
                                 ["a_defect_in_the_ANALYSIS_caught_before_it_was_written"]))
        chk("12b e che correggerlo non bastava",
            "and_correcting_it_was_not_enough" in rec["new_value"]
            ["a_defect_in_the_ANALYSIS_caught_before_it_was_written"])
        chk("13 l'ipotesi su du e' etichettata a posteriori",
            "recorded as a posteriori" in rec["new_value"]
            ["an_a_posteriori_hypothesis_declared_as_such"])
        chk("13a le tre riserve ci sono", len(rec["new_value"]["three_reserves"]) == 3)
        chk("13b la riserva sul dominio del pavimento e' esplicita",
            "different domains" in rec["new_value"]["three_reserves"]
            ["the_floor_is_computed_on_the_FULL_mask"])
        chk("13c lingua del record: inglese",
            ("perche'" not in txt) and ("emisferi" not in txt))
        chk("13d document ereditato dalla riga %d" % len(recs),
            rec["document"] == recs[-1].get("document"))
        chk("13e numbering_rule cita il record %d" % (len(recs) + 1),
            (str(len(recs) + 1) in str(rec.get("numbering_rule")))
            and ("record %d." % len(recs) not in str(rec.get("numbering_rule"))))
    else:
        for n in ("8 schema", "9 serializzazione", "10 smentita"):
            chk(n, False, "manca --item")

    return _report(checks, verbose)

def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend42 rev.1 ===")
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


def parse_overrides(items):
    ov = {}
    for it in (items or []):
        if "=" not in it:
            fail("--set richiede chiave=valore, ricevuto %r" % it)
        k, v = it.split("=", 1)
        ov[k] = None if v == "null" else v
    return ov










def cmd_gates(args):
    G = analyse_gates()
    if G["errore"]:
        fail(G["errore"])
    print("=== MASCHERA FISSA ===")
    for g in ("NGC", "SGC"):
        print("  %s  n_valid_voxels distinti: %s" % (g, G["voxel"][g]))
    print("")
    print("=== |Delta| CONTRO IL PAVIMENTO, ricalcolato ===")
    print("  %-4s %-3s %8s %8s %8s %8s %8s"
          % ("reg", "ang", "res vox", "|d| k0", "pav k0", "|d| k1", "pav k1"))
    for g in ("NGC", "SGC"):
        for c in ANGOLI:
            d0, d1 = G["delta"][(g, "k0")][c], G["delta"][(g, "k1")][c]
            p0, p1 = G["pav"][(g, "k0")], G["pav"][(g, "k1")]
            print("  %-4s %-3s %8.4f %8d %8.1f %8d %8.1f   %s"
                  % (g, c, RES_VOX[c], d0, p0, d1, p1,
                     ("SOPRA0 " if d0 > p0 else "sotto0 ")
                     + ("SOPRA1" if d1 > p1 else "sotto1")))
    print("")
    print("  La firma dichiarata era: SOPRA a C1 e C4, SOTTO a C2 e C3.")
    print("  C4, secondo canale piu' grande, e' sotto in tutti e quattro i casi.")
    print("  C2 e C3, i due piu' piccoli, sono sopra in tre su quattro.")
    print("  ORDINAMENTO INVERSO, in due emisferi indipendenti.")
    return 0


def cmd_inspect(args):
    if not os.path.isfile(args.ledger):
        fail("registro assente: %s" % args.ledger)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    print("registro        : %s   righe: %d" % (args.ledger, len(recs)))
    if len(recs) != EXPECTED_LINES_BEFORE:
        print("  ATTENZIONE: attese %d righe. Se sono %d, il record 45 non e'"
              % (EXPECTED_LINES_BEFORE, len(recs)))
        print("  ancora appeso: i numeri non sono prenotati, sono la POSIZIONE.")
    n_crlf, n_lf, odd = eol_profile(terms)
    print("fine riga       : CRLF=%d  LF=%d%s"
          % (n_crlf, n_lf, ("   fuori maggioranza: %s" % odd) if odd else "   uniformi"))
    ck = common_keys(recs, 3)
    print("chiavi comuni (%d): %s" % (len(ck), ck))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d  item: %r" % (i, r.get("item")))
    print("")
    return cmd_gates(args)


def cmd_dump(args):
    recs = read_ledger(args.ledger)[0]
    if not (1 <= args.n <= len(recs)):
        fail("riga %d fuori intervallo 1..%d" % (args.n, len(recs)))
    print(json.dumps(recs[args.n - 1], ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def cmd_selftest(args):
    return 1 if selftest(args.ledger, args.reference, args.item,
                         parse_overrides(args.set)) else 0


def cmd_append(args):
    if not args.item:
        fail("--item obbligatorio.")
    ov = parse_overrides(args.set)
    nfail = selftest(args.ledger, args.reference, args.item, ov)
    print("")
    if nfail:
        fail("selftest fallito (%d controlli): nessuna scrittura." % nfail)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    file_sha = sha256_file(args.reference)
    self_sha = json.load(open(args.reference, "r", encoding="utf-8")).get("_self_sha256", "")
    rec, unfilled, extras, required = build_record(recs, args.reference, file_sha,
                                                   self_sha, args.item, ov)
    if unfilled:
        fail("chiavi che non so riempire: %s" % ", ".join(unfilled))
    if extras and not args.allow_extra_keys:
        fail("il record 46 aggiunge le chiavi %s: --allow-extra-keys."
             % ", ".join(extras))
    line = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
    print("=== RECORD %d - riga %d, %d caratteri ===" % (AMEND_POSITION, len(recs) + 1, len(line)))
    pretty = json.dumps(rec, ensure_ascii=True, indent=2, sort_keys=True)
    print(pretty if len(pretty) <= 6000 else pretty[:6000] + "\n... (troncato in stampa)")
    print("")
    if not args.apply:
        print("[DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
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
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    fs = sha256_file(args.reference) if os.path.isfile(args.reference) else ""
    ok = True
    print("")
    print("=== VERIFY ===")
    print("  righe su disco            : %d (atteso %d)" % (len(recs), AMEND_POSITION))
    ok &= len(recs) == AMEND_POSITION
    print("  digest reference invariato: %s" % (fs == REFERENCE_FILE_SHA256))
    ok &= fs == REFERENCE_FILE_SHA256
    last = json.dumps(recs[-1], ensure_ascii=False)
    print("  marker nella riga %-2d      : %s" % (AMEND_POSITION, MARKER in last))
    ok &= MARKER in last
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("  round-trip della riga %-2d  : %s" % (AMEND_POSITION, rt == lines[-1]))
    ok &= rt == lines[-1]
    print("  item della riga %-2d        : %r" % (AMEND_POSITION, recs[-1].get("item")))
    print("  record 45 ancora sulla 45 : %s"
          % (MARKER_45 in json.dumps(recs[44], ensure_ascii=False)))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 46 - terzo canale misurato, firma smentita")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    p.add_argument("--reference", default=DEFAULT_REFERENCE)
    p.add_argument("--item", default=None)
    p.add_argument("--set", action="append", metavar="CHIAVE=VALORE")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("gates").set_defaults(func=cmd_gates)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    d = sub.add_parser("dump")
    d.add_argument("n", type=int)
    d.set_defaults(func=cmd_dump)
    ap = sub.add_parser("append")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-extra-keys", action="store_true")
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

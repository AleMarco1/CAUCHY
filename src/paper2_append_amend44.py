#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend44.py - Emendamento 44: il ripattern del tiling non guida la
risposta AP. Item 3.2d, §4.6 del referee.

Clona il meccanismo degli appender 42 e 43: numerazione posizionale, tre digest,
utc con offset +00:00, chiavi ordinate, ensure_ascii DERIVATO dal file, schema
dall'intersezione delle ultime tre righe, lettore robusto ai fine riga misti.

I fatti che il record afferma sono verificati MECCANICAMENTE: i quattro
Delta_ripattern si RICALCOLANO dai due registri e si confrontano con quelli
citati nel testo. Nessun numero trascritto.

Cancelli d'append (bloccanti)
-----------------------------
  G1..G4, G6  come nel 43;
  M1  i due registri hanno la forma attesa: 200 realizzazioni per emisfero, gli
      stessi indici, replica_randomise e rot_seed depositati;
  M2  i quattro Delta_ripattern RICALCOLATI coincidono con quelli citati;
  M3  tutti e quattro stanno SOTTO la soglia dichiarata di 53;
  M4  la correlazione fra i bracci e' ~0: l'appaiamento NON ha funzionato, ed e'
      un fatto che il record registra, non che nasconde;
  M5  D5c: nessun punto raggiunge la soglia di 28 clippati.

Uscita ASCII pura.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import statistics as st
import sys

AMEND_POSITION = 44
EXPECTED_LINES_BEFORE = 43

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")
STD = os.path.join("results", "paper2", "fase3_mock.jsonl")
RAND = os.path.join("results", "paper2", "fase3_mock_ripattern.jsonl")

SOGLIA = 53.0
ROT_SEED = 20260905
N_ATTESO = 200
D5C_SOGLIA = 28
CORR_MAX = 0.15          # oltre questa, l'appaiamento avrebbe funzionato

# I quattro risultati, come li cita il testo. Il selftest li RICALCOLA.
RISULTATI = {
    ("NGC", "N_H1_k0"): (6.96, 16.40),
    ("NGC", "N_H1_k1"): (-9.38, 15.72),
    ("SGC", "N_H1_k0"): (-33.84, 13.50),
    ("SGC", "N_H1_k1"): (-28.63, 12.92),
}

MARKER = "emendamento-44-ripattern-del-tiling-sotto-soglia"
MARKER_43 = "emendamento-43-componente-d-tracciata-per-riproduzione"
COMPANION_DOCUMENT = "paper2_item32d_ripattern.md; risposta_referee.md §4.6; checklist item 3.2d"


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "the_tiling_repattern_does_not_drive_the_ap_response_and_term_d_stays_zero_by_measurement"

JSON_PATH = ("src/phase8_cutsky_mocks.py (carve_cutsky); "
             "src/paper2_runner_fase3_mock.py; "
             "results/paper2/fase3_mock_ripattern.jsonl; "
             "results/paper2/gazione_32d.jsonl; checklist items 3.2b, 3.2d")

OLD_VALUE = (
    "Checklist item 3.2b closed the tiling question by ARGUMENT: in the constant-cube gauge the "
    "number of replicas is constant - 15 in NGC and 10 in SGC across all eleven grid points - and "
    "the independent-volume fraction moves by 0.2% against 13.1% in the variable-cube gauge, so "
    "budget term (d) was set to zero. The referee's §4.6 objection: that argument bounds MULTIPLICITY "
    "STATISTICS, not the REPATTERN. Under deformation it is WHICH box cell lands on which survey "
    "voxel that changes, at constant multiplicity, and 59% of in-survey voxels sit on cells used "
    "more than once. The two are different quantities and 3.2b constrains only one of them."
)

NEW_VALUE = {
    "the_objection_was_valid": {
        "what_3_2b_proves": ("The gauge fixes the NUMBER of replicas and the independent fraction. "
                             "That much stands and is not withdrawn."),
        "what_it_does_not_prove": ("Anything about the ASSIGNMENT MAP. A near-invariant multiplicity "
                                   "statistic is compatible with an extensive reassignment, because "
                                   "the reused cells are reused LITTLE - mean multiplicity 1.437 - "
                                   "but there are MANY of them."),
        "our_own_numbers_which_the_referee_read_correctly": ("From "
                                                             "results/revision/rev1_r11_tiling.json: "
                                                             "independent volume fraction 0.69594, "
                                                             "voxels on reused cells 0.58757, mean "
                                                             "multiplicity 1.43690, max 5. The 59% "
                                                             "he quotes is 0.58757 rounded."),
        "so_it_is_not_closable_by_argument": ("It wanted the run he asked for: two points of line B "
                                              "with replica-randomised mocks."),
    },
    "what_was_built": {
        "one_implementation_not_two": ("The signed axis permutation went INTO "
                                       "phase8_cutsky_mocks.carve_cutsky, not into a second copy. "
                                       "The pilot of 22 Aug (rev1_r11_pilot.py) kept its own copy of "
                                       "carve_cutsky and stays where it is as the artefact of the "
                                       "M26 run."),
        "a_parameter_not_a_module_flag": ("randomise_replicas is on the SIGNATURE. REAL_SPACE is a "
                                          "global and record 35 came from exactly there: the flag "
                                          "existed and nobody switched it on, with twenty-one checks "
                                          "verifying it existed and none that anyone lit it. A "
                                          "parameter with a default cannot stay unassigned in "
                                          "silence."),
        "the_off_branch_is_a_no_op_BY_CONSTRUCTION": ("The pilot still executes pos_gal @ I.T and "
                                                      "np.mod(..., BOXSIZE_MOCK) when off. The "
                                                      "identity product is exact but mod is not a "
                                                      "structural identity - on a coordinate exactly "
                                                      "equal to BOXSIZE_MOCK, or negative, it would "
                                                      "differ. In production the off branch returns "
                                                      "the input arrays untouched."),
        "the_permutations_are_THE_SAME_at_every_point": ("rot_state is snapshotted per realisation "
                                                         "and restored before each point, exactly as "
                                                         "rng is. With DIFFERENT permutations at B1 "
                                                         "and B5 the whole field would be reshuffled "
                                                         "between the two points and Delta D would "
                                                         "measure THAT reshuffle instead of the "
                                                         "deformation. This is the line the test "
                                                         "turns on."),
        "explicit_refusals": ("randomise_replicas=True without rot_rng raises; "
                              "--replica-randomise with --fixed-observables exits, because under (B) "
                              "the carving happens once at the fiducial; and the runner checks the "
                              "SIGNATURE of carve_cutsky, so it cannot run against an unpatched "
                              "phase8 after a checkout."),
    },
    "the_gates": {
        "G_null": ("Two smoke runs, one BEFORE the patch and one after, on the production path with "
                   "capture= and REAL_SPACE live: n_sel, k0, k1 and the B1/B5 deltas identical line "
                   "by line, down to 'D4b=scarti [1, 1]'. The patch changed 44690 -> 46918 bytes and "
                   "not one number."),
        "G_action": ("Three realisations at FID through the production path, compared with the frozen "
                     "values: 35018/31493 against 35318/31756, 35111/31538 against 34972/31419, "
                     "35943/32402 against 35526/32160. All three DIFFER, by 139 to 417 generators, "
                     "consistent with the paired sd of 201 the pilot measured. Record 35's rule: a "
                     "flag that changes a measurement is verified by a run that PRODUCES DIFFERENT "
                     "NUMBERS."),
        "why_G_action_is_not_in_the_smoke": ("D4b checks that N_H1 is identical to the frozen values "
                                             "mock by mock. With randomised replicas it MUST differ, "
                                             "so the smoke would fail by construction. A gate that "
                                             "fails when the thing works is worse than no gate, so "
                                             "the flag was deliberately NOT added to the smoke."),
    },
    "the_run": ("200 realisations per hemisphere, points B1 and B5, --skip-fid, rot_seed 20260905, "
                "about 2.0 h each. 400 records, indices 0-199 complete, no duplicates. D5c: at most "
                "8 clipped positions against a threshold of 28."),
    "the_result": {
        "NGC_k0": "+6.96 +- 16.40   (t +0.42)",
        "NGC_k1": "-9.38 +- 15.72   (t -0.60)",
        "SGC_k0": "-33.84 +- 13.50  (t -2.51)",
        "SGC_k1": "-28.63 +- 12.92  (t -2.22)",
        "verdict": ("All four BELOW the threshold of 53 declared in paper2_item32d_ripattern.md "
                    "before the run. The tiling repattern does not drive the AP response, and budget "
                    "term (d) stays ZERO BY MEASUREMENT instead of by argument."),
    },
    "what_did_NOT_hold_and_is_registered": {
        "the_pairing_assumption_failed": ("The design assumed the two arms would be paired through "
                                          "the shared seeds, giving a much smaller SEM on the "
                                          "difference. They are not: the correlation between arms is "
                                          "0.0054, 0.0490, -0.0049 and -0.0109 - zero - and the "
                                          "paired SEM equals the unpaired one. Randomising the "
                                          "replicas produces what is effectively an independent "
                                          "realisation of the same cosmology: the coherence that "
                                          "keeps two POINTS of one mock paired does not survive "
                                          "between two ARMS."),
        "what_it_cost": ("SEM of 13-16 generators instead of the 2-4 the design anticipated. The test "
                         "has far less power than planned, and the threshold was only met because it "
                         "was set conservatively."),
        "and_the_threshold_was_lucky": ("53 was chosen before the run as the stricter of two "
                                        "candidates - 53 against 75 - on the principle that a "
                                        "threshold fixed in advance should be the harder one to pass. "
                                        "The natural 3*SEM of this quantity turns out to be 39-49, so "
                                        "53 is slightly LOOSER than 3 sigma, not stricter. Chosen "
                                        "blind, it landed close. This is luck and is recorded as "
                                        "luck."),
    },
    "SGC_is_not_zero": {
        "what": ("NGC is compatible with zero and CHANGES SIGN between the two erosion levels (+6.96, "
                 "-9.38). SGC sits at 2.2-2.5 sigma with the SAME SIGN at both levels (-33.84, "
                 "-28.63)."),
        "how_it_is_reported": ("The declared verdict is 'the repattern does not drive the response', "
                               "and that is what gets written. But 'does not drive' is not 'absent', "
                               "and reporting SGC as zero would be the over-claim the referee "
                               "objected to elsewhere in this same report."),
        "and_it_is_the_recurring_signature": ("A hemispheric asymmetry, again: the programme meets it "
                                              "under treatment (B), in real space, and in the "
                                              "even/odd contrasts. Here it is weaker than those but "
                                              "it points the same way."),
    },
    "what_this_does_not_establish": ("Two points, the most deformed ones, not the whole grid - that it "
                                     "holds elsewhere is an extrapolation. The AP RESPONSE, not the "
                                     "deficit itself: that is the pilot of 22 Aug, with its own "
                                     "separate limit. And nothing about modes larger than the "
                                     "periodic box, which are ABSENT rather than duplicated and which "
                                     "no rearrangement of replicas can restore - M26 §7(vii) says so "
                                     "in print, and Paper 2 inherits the limitation rather than "
                                     "introducing it."),
}

RULES = {
    "amends_records": [],
    "a_gate_that_fails_when_the_thing_works_is_worse_than_no_gate": ("G-action was kept OUT of the "
                                                                     "smoke because D4b would fail by "
                                                                     "construction with randomised "
                                                                     "replicas."),
    "a_multiplicity_statistic_does_not_bound_an_assignment_map": ("Constant replica counts and a "
                                                                  "near-invariant independent "
                                                                  "fraction say nothing about WHICH "
                                                                  "cell lands where. Item 3.2b is not "
                                                                  "withdrawn; it is bounded."),
    "an_assumption_of_the_DESIGN_that_fails_is_registered": ("The pairing between arms was assumed and "
                                                             "does not hold. It is written down with "
                                                             "what it cost, not quietly absorbed."),
    "companion_document": COMPANION_DOCUMENT,
    "marker": MARKER,
    "the_permutations_must_be_the_same_at_every_point": ("Otherwise Delta D measures the reshuffle "
                                                         "between points instead of the deformation."),
    "what_this_does_not_do": ("It does not reopen Phase 3, changes no frozen value, and writes nothing "
                              "to fase3_mock.jsonl: the randomised arm went to a separate register."),
}

REASON = (
    "The referee's §4.6 objection was VALID and the tiling question is now closed BY MEASUREMENT. "
    "Item 3.2b argued that the constant-cube gauge fixes the replica count - 15 NGC, 10 SGC on all "
    "eleven points - and the independent fraction to 0.2%, so budget term (d) was zero. That bounds "
    "MULTIPLICITY, not the REPATTERN: under deformation it is which box cell lands on which voxel "
    "that changes, and 58.757% of in-survey voxels sit on reused cells - our own number, from "
    "rev1_r11_tiling.json, which the referee read and quoted correctly as 59%. A near-invariant "
    "multiplicity is compatible with extensive reassignment precisely because the reused cells are "
    "reused LITTLE, mean 1.437, but are MANY. So 3.2b is not withdrawn; it is bounded, and the "
    "question wanted the run. WHAT WAS BUILT. The signed axis permutation went into carve_cutsky "
    "itself, not a second copy; as a PARAMETER, not a module flag, because record 35 came from a "
    "global that existed and was never switched on; with the off branch a no-op BY CONSTRUCTION "
    "rather than by verification; and with the permutations restored to THE SAME state at every "
    "point - the line the whole test turns on, because different permutations at B1 and B5 would make "
    "Delta D measure the reshuffle instead of the deformation. TWO GATES. G-null: two smoke runs, "
    "before and after the patch, identical line by line on the production path. G-action: three "
    "realisations at FID differing from the frozen values by 139 to 417 generators. G-action was kept "
    "OUT of the smoke on purpose, because D4b requires identity with the frozen values and would fail "
    "by construction. THE RESULT. 200 realisations per hemisphere at B1 and B5: Delta_ripattern = "
    "+6.96 +- 16.40 and -9.38 +- 15.72 in NGC, -33.84 +- 13.50 and -28.63 +- 12.92 in SGC. All four "
    "below the threshold of 53 declared before the run. Term (d) stays zero, by measurement. AND TWO "
    "THINGS THAT DID NOT GO AS DESIGNED. The pairing between arms FAILED: correlation 0.005, 0.049, "
    "-0.005, -0.011, and the paired SEM equals the unpaired one. Randomising the replicas gives what "
    "is effectively an independent realisation, so the test has 13-16 generators of SEM instead of "
    "the 2-4 anticipated. And the threshold was lucky: 53 was picked as the stricter of two "
    "candidates, but the natural 3*SEM of this quantity is 39-49, so 53 is slightly looser than 3 "
    "sigma. Recorded as luck. FINALLY, SGC IS NOT ZERO. NGC is compatible with zero and changes sign "
    "between levels; SGC sits at 2.2-2.5 sigma with the same sign at both. 'Does not drive' is not "
    "'absent', and reporting SGC as zero would be the over-claim this same referee objected to "
    "elsewhere."
)

EVIDENCE = (
    "Runs of 5 Sep 2026. Patch of phase8_cutsky_mocks.py: 44690 -> 46918 bytes, sha256 "
    "427681df4fc38a81982990306d51d838f4029804b44dc18cbca5758d86321a8a -> "
    "bc61dc8a839643f5a370fee2bcabcdcc86b18557a7dd18d29fda176bfdc9b575, five edits, one definition of "
    "carve_cutsky, no copy introduced, REAL_SPACE untouched. Patch of paper2_runner_fase3_mock.py: "
    "40744 -> 45518 bytes, sha256 066ae6cc4b6d4635a2d18906f271938512e3a6fe2f9f386b778d0d50772cd007 -> "
    "a44d7155ae65199130bcedb8f69447e5eef1e13d3935ef74d190e51f6692fdb2, eleven edits, both resume keys "
    "moved together. G-null: smoke_pre32d.jsonl and smoke_post32d.jsonl identical outside utc and "
    "seconds. G-action: gazione_32d.jsonl, three realisations at FID, 35018/31493, 35111/31538, "
    "35943/32402 against frozen 35318/31756, 34972/31419, 35526/32160. The run: "
    "fase3_mock_ripattern.jsonl, 400 records, 200 per hemisphere, indices 0-199, replica_randomise "
    "true, rot_seed 20260905, 2.05 h and 2.00 h. Randomised arm means: NGC B1 35490.960 B5 35279.925 "
    "at k=0 and 31951.930 / 31770.245 at k=1; SGC 18777.325 / 18607.510 and 16554.760 / 16415.000. "
    "Standard arm Delta D: -218.00 +- 11.62, -172.30 +- 11.25, -135.98 +- 9.17, -111.13 +- 8.71. "
    "Correlations between arms: 0.0054, 0.0490, -0.0049, -0.0109. D5c: max 7 clipped in NGC and 8 in "
    "SGC, threshold 28. The tiling geometry quoted above is from rev1_r11_tiling.json and was read "
    "with encoding utf-8-sig: that file carries a BOM, unlike the other registers."
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





def _merge(records, want_rand):
    out = {}
    for r in records:
        if r.get("smoke"):
            continue
        if bool(r.get("replica_randomise", False)) != want_rand:
            continue
        k = (r.get("region"), r.get("index"))
        pts = r.get("points")
        if not isinstance(pts, dict):
            continue
        slot = out.setdefault(k, {})
        for name, d in pts.items():
            if isinstance(d, dict):
                slot.setdefault(name, {}).update(d)
    return out


def analyse_gates(std_path=STD, rand_path=RAND):
    """Ricalcola i quattro Delta_ripattern dai registri. Nessun numero trascritto."""
    out = {"per_regione": {}, "forma": {}, "d5c_max": 0}
    if not (os.path.isfile(std_path) and os.path.isfile(rand_path)):
        out["errore"] = "registri assenti"
        return out
    # read_jsonl del nucleo clonato torna la settupla del registro, non la
    # lista: [0] e' i record. Un errore che il primo `gates` ha trovato subito.
    std = _merge(read_jsonl(std_path)[0], False)
    rrecs_all = read_jsonl(rand_path)[0]
    rnd = _merge(rrecs_all, True)
    rrecs = [r for r in rrecs_all if not r.get("smoke")]

    for reg in ("NGC", "SGC"):
        idx_r = sorted(i for (g, i) in rnd if g == reg)
        out["forma"][reg] = {
            "n": len(idx_r),
            "indici_completi": idx_r == list(range(N_ATTESO)),
            "punti": sorted({p for (g, i), v in rnd.items() if g == reg for p in v}),
            "rot_seed": sorted({r.get("rot_seed") for r in rrecs
                                if r.get("region") == reg}),
        }
        for field in ("N_H1_k0", "N_H1_k1"):
            a, b = {}, {}
            for src_, dst in ((std, a), (rnd, b)):
                for (g, i), pts in src_.items():
                    if g != reg:
                        continue
                    if all(p in pts and field in pts[p] for p in ("B1", "B5")):
                        dst[i] = float(pts["B5"][field]) - float(pts["B1"][field])
            common = sorted(set(a) & set(b))
            if len(common) < 2:
                continue
            da = [a[i] for i in common]
            db = [b[i] for i in common]
            dd = [b[i] - a[i] for i in common]
            m = st.mean(dd)
            sem = st.stdev(dd) / math.sqrt(len(dd))
            out["per_regione"][(reg, field)] = {
                "n": len(common), "delta": m, "sem": sem,
                "t": m / sem if sem else float("nan"),
                "corr": st.correlation(da, db) if len(da) > 2 else float("nan"),
                "std_mean": st.mean(da), "rand_mean": st.mean(db),
                "sotto_soglia": abs(m) < SOGLIA,
            }
    for r in rrecs:
        for pt in (r.get("points") or {}).values():
            if isinstance(pt, dict) and "d5c_n_clipped" in pt:
                out["d5c_max"] = max(out["d5c_max"], int(pt["d5c_n_clipped"]))
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
        "trovate %d" % len(recs))
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    chk("2b la riga %d si ri-serializza byte per byte identica" % len(recs),
        rt == lines[-1], "%d byte contro %d" % (len(rt), len(lines[-1])))

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
        and self_sha == recs[-1].get("reference_self_sha256"), self_sha[:16])

    blob = raw.decode("utf-8", "replace")
    dup = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 44 assente, item non gia' usato)",
        (MARKER not in blob) and not dup)
    chk("6b prerequisito: il record 43 e' presente ED e' sulla riga %d" % EXPECTED_LINES_BEFORE,
        (MARKER_43 in blob)
        and (MARKER_43 in json.dumps(recs[EXPECTED_LINES_BEFORE - 1], ensure_ascii=False)))

    n_crlf, n_lf, odd = eol_profile(terms)
    chk("7  convenzioni: ascii_puro=%s ordinate=%s; CRLF=%d LF=%d"
        % (pure_ascii, sorted_keys, n_crlf, n_lf), True,
        ("fuori maggioranza: %s - preesistente" % odd) if odd else "uniformi")
    chk("7b l'ultima riga segue la maggioranza",
        terms[-1] == (b"\r\n" if n_crlf >= n_lf else b"\n"))

    G = analyse_gates()
    if "errore" in G:
        chk("M1 registri presenti", False, G["errore"])
        return _report(checks, verbose)

    bad = []
    for reg in ("NGC", "SGC"):
        f = G["forma"][reg]
        if f["n"] != N_ATTESO or not f["indici_completi"]:
            bad.append("%s: %d realizzazioni, indici completi=%s"
                       % (reg, f["n"], f["indici_completi"]))
        if f["punti"] != ["B1", "B5"]:
            bad.append("%s: punti %s" % (reg, f["punti"]))
        if f["rot_seed"] != [ROT_SEED]:
            bad.append("%s: rot_seed %s" % (reg, f["rot_seed"]))
    chk("M1 forma dei registri: 200 realizzazioni, B1/B5, rot_seed dichiarato",
        not bad, ",".join(bad) if bad else "due emisferi")

    bad2, bad3, bad4 = [], [], []
    for key, (d_att, s_att) in sorted(RISULTATI.items()):
        r = G["per_regione"].get(key)
        if r is None:
            bad2.append("%s/%s assente" % key)
            continue
        if round(r["delta"], 2) != d_att or round(r["sem"], 2) != s_att:
            bad2.append("%s/%s: %.2f+-%.2f contro %.2f+-%.2f"
                        % (key[0], key[1], r["delta"], r["sem"], d_att, s_att))
        if not r["sotto_soglia"]:
            bad3.append("%s/%s: |%.2f| >= %.0f" % (key[0], key[1], r["delta"], SOGLIA))
        if abs(r["corr"]) > CORR_MAX:
            bad4.append("%s/%s: corr %.4f" % (key[0], key[1], r["corr"]))
    chk("M2 i quattro Delta_ripattern RICALCOLATI coincidono con quelli citati",
        not bad2, ",".join(bad2) if bad2 else "quattro valori e quattro SEM")
    chk("M3 tutti e quattro SOTTO la soglia dichiarata di %.0f" % SOGLIA,
        not bad3, ",".join(bad3) if bad3 else "verdetto confermato")
    chk("M4 la correlazione fra i bracci e' ~0: l'appaiamento NON ha funzionato",
        not bad4, ",".join(bad4) if bad4
        else "max |corr| = %.4f" % max(abs(G["per_regione"][k]["corr"])
                                       for k in RISULTATI))
    chk("M5 D5c: nessun punto raggiunge la soglia di %d clippati" % D5C_SOGLIA,
        G["d5c_max"] < D5C_SOGLIA, "massimo %d" % G["d5c_max"])

    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha,
                                                       self_sha, item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 41-43 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        # `in` su un dizionario confronta CHIAVI intere, non sottostringhe: la
        # chiave e' the_objection_was_valid. Difetto trovato dal selftest.
        chk("10 il record dice che il rilievo era VALIDO e che 3.2b non e' ritirata",
            "the_objection_was_valid" in rec["new_value"]
            and "not withdrawn" in rec["new_value"]["the_objection_was_valid"]
            ["what_3_2b_proves"])
        chk("11 il fallimento dell'appaiamento e' registrato con il suo costo",
            "the_pairing_assumption_failed" in rec["new_value"]
            ["what_did_NOT_hold_and_is_registered"]
            and "13-16" in rec["new_value"]["what_did_NOT_hold_and_is_registered"]
            ["what_it_cost"])
        chk("12 la soglia fortunata e' dichiarata come fortuna",
            "recorded as luck" in rec["new_value"]
            ["what_did_NOT_hold_and_is_registered"]["and_the_threshold_was_lucky"])
        chk("13 SGC non e' riportato come zero",
            "not 'absent'" in rec["new_value"]["SGC_is_not_zero"]["how_it_is_reported"])
        chk("13a il motivo per cui G-azione non sta nello smoke e' scritto",
            "by construction" in rec["new_value"]["the_gates"]
            ["why_G_action_is_not_in_the_smoke"])
        chk("13b il 59%% del referee e' riconosciuto come NOSTRO numero",
            "58.757%" in rec["reason"])
        chk("13c i modi oltre la scatola restano esclusi",
            "ABSENT rather than duplicated" in rec["new_value"]
            ["what_this_does_not_establish"])
        chk("13d lingua del record: inglese",
            ("perche'" not in txt) and ("emisferi" not in txt)
            and ("cancelli" not in txt))
        chk("13e document ereditato dalla riga %d" % len(recs),
            rec["document"] == recs[-1].get("document"))
        chk("13f numbering_rule cita il record %d" % (len(recs) + 1),
            (str(len(recs) + 1) in str(rec.get("numbering_rule")))
            and ("record %d." % len(recs) not in str(rec.get("numbering_rule"))))
    else:
        for n in ("8 schema", "9 serializzazione", "10 rilievo valido"):
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
    if "errore" in G:
        fail(G["errore"])
    print("=== FORMA DEI REGISTRI ===")
    for reg in ("NGC", "SGC"):
        f = G["forma"][reg]
        print("  %s  n=%d  indici completi=%s  punti=%s  rot_seed=%s"
              % (reg, f["n"], f["indici_completi"], f["punti"], f["rot_seed"]))
    print("  D5c massimo: %d   (soglia %d)" % (G["d5c_max"], D5C_SOGLIA))
    print("")
    print("=== Delta_ripattern, RICALCOLATO   soglia %.0f ===" % SOGLIA)
    print("  %-5s %-9s %10s %8s %7s %9s %9s %8s"
          % ("reg", "livello", "Delta", "SEM", "t", "std", "rand", "corr"))
    for key in sorted(RISULTATI):
        r = G["per_regione"].get(key)
        if r is None:
            print("  %-5s %-9s  ASSENTE" % key)
            continue
        print("  %-5s %-9s %+10.2f %8.2f %+7.2f %9.2f %9.2f %8.4f   %s"
              % (key[0], key[1], r["delta"], r["sem"], r["t"],
                 r["std_mean"], r["rand_mean"], r["corr"],
                 "sotto" if r["sotto_soglia"] else "SOPRA"))
    print("")
    print("  L'appaiamento NON ha funzionato: correlazione ~0 fra i bracci, quindi")
    print("  la SEM appaiata coincide con quella non appaiata. E' un'assunzione")
    print("  del disegno che non ha retto, e il record la registra.")
    return 0


def cmd_inspect(args):
    if not os.path.isfile(args.ledger):
        fail("registro assente: %s" % args.ledger)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    print("registro        : %s" % args.ledger)
    print("righe           : %d" % len(recs))
    print("ascii puro      : %s   chiavi ordinate: %s" % (pure_ascii, sorted_keys))
    n_crlf, n_lf, odd = eol_profile(terms)
    print("fine riga       : CRLF=%d  LF=%d%s"
          % (n_crlf, n_lf, ("   fuori maggioranza: %s" % odd) if odd else "   uniformi"))
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("round-trip r.%-2d : %s" % (len(recs), "IDENTICO" if rt == lines[-1] else "DIVERSO"))
    ck = common_keys(recs, 3)
    print("chiavi comuni 41-43 (%d): %s" % (len(ck), ck))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d  item: %r   utc: %r" % (i, r.get("item"), r.get("utc")))
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
        fail("il record 44 aggiunge le chiavi %s: approvale con --allow-extra-keys."
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
    G = analyse_gates()
    print("  registri di misura intatti: %s"
          % all(G["forma"][r]["n"] == N_ATTESO for r in ("NGC", "SGC")))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 44 - ripattern del tiling sotto soglia")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    p.add_argument("--reference", default=DEFAULT_REFERENCE)
    p.add_argument("--item", default=None, help="numerazione item, es. 3.2d")
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend54.py — appende il record 54: quattro decisioni prese sui valori v1
misurati, prima che l'ensemble v2 giri.

I cancelli sull'append si importano da paper2_append_amend50.

Uso:
    python paper2_append_amend54.py selftest
    python paper2_append_amend54.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 53 --dry-run
"""

import argparse
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

ITEM = "4.2b/decisioni_su_valori_v1_misurati"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"
CRLF = chr(13).encode() + chr(10).encode()

# Valori v1 misurati il 7 settembre 2026. Ogni soglia sotto e' DERIVATA da questi,
# non scelta: il selftest ricalcola ciascuna.
V1 = {
    "NGC": {"n_pat_media": 4048.21, "n_pat_sd": 84.66, "n_pat_sem": 1.893,
            "n_pat_min": 3314, "n_pat_max": 4274, "R_P10": 3.6462},
    "SGC": {"n_pat_media": 2811.56, "n_pat_sd": 71.45, "n_pat_sem": 1.598,
            "n_pat_min": 2195, "n_pat_max": 3004, "R_P10": 8.0657},
}
FRAZIONE_SUCCESSO = 1.0 / 3.0     # gia' dichiarata per 4.3b nel record 51
FRAZIONE_FALLIMENTO = 2.0 / 3.0   # idem


def soglie_4_2c(region):
    v = V1[region]["n_pat_media"]
    return round(v * FRAZIONE_SUCCESSO, 2), round(v * FRAZIONE_FALLIMENTO, 2)


def soglia_4_2b_1(region):
    return round(2.0 * V1[region]["R_P10"], 4)


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    sN, fN = soglie_4_2c("NGC")
    sS, fS = soglie_4_2c("SGC")
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "four_decisions_taken_on_measured_v1_values_before_the_v2_ensemble_is_run",
        "json_path": ("results/paper2/onepoint_v1_{NGC,SGC}.jsonl; "
                      "results/paper2/onepoint_v1_{NGC,SGC}_sommario.jsonl; "
                      "results/paper2/onepoint_v1_DESI_{NGC,SGC}.jsonl; "
                      "results/paper2/cancello_nu_NGC.jsonl; "
                      "src/paper2_passata_1punto.py; src/paper2_cancello_nu.py; "
                      "src/paper2_letture_1punto.py; records 50 and 51"),
        "old_value": (
            "Record 50 left rule 4.2b-3 with its form declared and its threshold explicitly "
            "UNWRITTEN, because nu.p1 existed in no register. It set the 4.2b-1 threshold at "
            "7.358 (NGC) and 16.203 (SGC), twice the P10 variance ratio measured on n=200. Rule "
            "4.2c carried the prediction '~4000 pathological voxels per mock -> ~0', a threshold "
            "crossing with no denominator and no zone of indecision, of the same shape as the four "
            "predictions withdrawn in record 50. And the one-point pass had never been run, so the "
            "v1 side of four of the six rules was known only through the n=200 aggregates of "
            "paper1_step6_{NGC,SGC}.json."
        ),
        "new_value": {
            "i_the_pass_and_the_gates_it_passed": {
                "what_was_run": "src/paper2_passata_1punto.py over all 2000 mock delta fields in "
                    "both hemispheres, streaming one realisation at a time, plus a DESI row per "
                    "hemisphere. 0.12 s per mock, 4.1 minutes per hemisphere. It computes nothing "
                    "of its own: setup_region, compute_delta, build_nu, build_restrictions and "
                    "moments are imported from paper1_remap and paper1_step6_onepoint_betti, and a "
                    "runtime check verifies that the import is the real one.",
                "the_uniqueness_gate_on_nu": "Two objects named nu existed: build_nu(delta) "
                    "reconstructed at runtime, and the frozen cubes results/phase8_test2_fields/"
                    "test2_NNNN.npz from which n1b_spectra took its moments. N_H1 cannot tell them "
                    "apart - supralevel filtration is invariant under monotone remapping - so "
                    "reproducing 28256 and 35436.686 says nothing about which one has the right "
                    "moments, and the moments are exactly what 4.2b needs. Gate declared before "
                    "measuring, on indices 200/500/1000/1805/1999: UNICA if the relative "
                    "discrepancy on sigma and kurtosis stays at or below 1e-5 on every index, "
                    "CONFLITTO above 1e-3, undecided in between. Result: build_nu(delta) "
                    "reproduces the frozen cubes BIT FOR BIT, max|d| = 0.000e+00 on all five, and "
                    "the moments agree with n1b_spectra to 3.789e-07. build_nu is the single "
                    "implementation.",
                "reproduction_anchors": "NGC carries 1850 anchors, verified inline while the pass "
                    "ran, not on a sample: 50 delta records from n1_spectra_NGC.jsonl at indices "
                    "0-49 and 1800 nu records from n1b_spectra_NGC.jsonl at indices 200-1999. The "
                    "two index sets are DISJOINT, so no realisation validates both paths at once "
                    "and both registers had to be reproduced. Worst relative discrepancy over all "
                    "1850: 2.562e-06, against the 1e-5 declared before the run.",
                "SGC_has_no_anchor_and_this_is_recorded": "No frozen nu cube exists for SGC: the "
                    "tier `fields` holds 2000 test2_ plus 200 cutsky_ plus 2 revision entries, and "
                    "2000 is one hemisphere. SGC inherits validity from the code path verified in "
                    "NGC, not from an anchor of its own. Its summary reports 0 anchors and a worst "
                    "discrepancy of 0.000e+00: that zero means no comparison was made, not perfect "
                    "agreement.",
                "the_DESI_rows_are_anchored_on_seven_keys_per_field": "paper1_step6_{NGC,SGC}.json "
                    "already held DESI's mean, variance, skewness, excess kurtosis, median, p99 and "
                    "maximum per restriction. 28 values reproduced per hemisphere, worst "
                    "discrepancy 0.000e+00. p01 is the ONLY quantity in the whole pass that no "
                    "frozen register contains.",
                "twelve_frozen_constants_reproduced": "src/paper2_letture_1punto.py refuses to "
                    "report any v1 value until the idx 0-199 subset reproduces the frozen n=200 "
                    "constants. All twelve pass in both hemispheres, within the quantisation of "
                    "the quoted digit. Tightest margin 1.00: SGC kurtosis sd, 4.9827e-05 against "
                    "the 5e-05 that four decimals admit.",
                "input_anchoring": "Every record carries delta_sha256, cross-checked against "
                    "cachedelta_manifest_{NGC,SGC}.jsonl, 2000 entries per hemisphere, zero "
                    "mismatches. The thirteenth contract field of record 53 is in use."
            },
            "ii_measured_v1_values_n_2000": {
                "NGC": {
                    "mask_voxels": 307805, "sigma_px": 0.320422,
                    "pathological_threshold": 125.47415161132812,
                    "var_delta": {"desi": 2.916642, "mock_mean": 2844.93429,
                                  "mock_sd": 509.83181, "z": -5.574, "rank": "0/2000"},
                    "kurt_nu": {"desi": -0.438215, "mock_mean": 2.817516,
                                "mock_sd": 0.458057, "z": -7.108, "rank": "3/2000"},
                    "r_f": {"desi": 3.224635, "mock_mean": 5.648966,
                            "mock_sd": 0.250815, "z": -9.666, "rank": "0/2000"},
                    "max_delta": {"desi": 125.47415, "mock_mean": 3938.70910,
                                  "mock_sd": 2130.46930, "z": -1.790, "rank": "0/2000"},
                    "n_pathological": {"desi": 0, "mock_mean": 4048.21, "mock_sd": 84.66,
                                       "mock_sem": 1.893, "min": 3314, "max": 4274},
                    "nu_desi": {"p1": -5.137403, "p99": 3.524586, "sigma": 2.686192},
                    "R_full": 975.4143, "R_P10": 3.6462},
                "SGC": {
                    "mask_voxels": 172225, "sigma_px": 0.336055,
                    "pathological_threshold": 161.6696,
                    "var_delta": {"desi": 4.815533, "mock_mean": 9886.22733,
                                  "mock_sd": 1587.69743, "z": -6.224, "rank": "0/2000"},
                    "kurt_nu": {"desi": -1.135173, "mock_mean": 1.132737,
                                "mock_sd": 0.278277, "z": -8.150, "rank": "1/2000"},
                    "r_f": {"desi": 2.999872, "mock_mean": 4.790012,
                            "mock_sd": 0.151191, "z": -11.840, "rank": "0/2000"},
                    "max_delta": {"desi": 161.66965, "mock_mean": 6968.60580,
                                  "mock_sd": 2972.96715, "z": -2.290, "rank": "0/2000"},
                    "n_pathological": {"desi": 0, "mock_mean": 2811.56, "mock_sd": 71.45,
                                       "mock_sem": 1.598, "min": 2195, "max": 3004},
                    "nu_desi": {"p1": -4.712914, "p99": 4.049958, "sigma": 2.921082},
                    "R_full": 2052.9870, "R_P10": 8.0657},
                "note_on_DESI_n_pathological": "Zero by construction: the threshold IS DESI's own "
                    "maximum of delta inside the mask."
            },
            "iii_decision_A_rule_4_2b_3_withdrawn_as_a_falsification": {
                "decision": "4.2b-2 remains the falsification rule, unchanged: |z| < 3 success, "
                    "> 5 failure. 4.2b-3 is withdrawn as a falsification. r_f is retained as a "
                    "REPORTED DIAGNOSTIC with its v1 values above and NO threshold.",
                "the_fact": "Excess kurtosis of nu and r_f are collinear on the v1 ensemble in "
                    "BOTH hemispheres, on different masks and different geometries: Pearson "
                    "+0.9988 and Spearman +0.9976 in NGC, +0.9985 and +0.9978 in SGC. Residuals "
                    "about the kurtosis-r_f line in NGC have sd 0.0122 over a range running from "
                    "3.6 to 6.0. sigma(nu) is the third face of the same quantity at |r| >= 0.988. "
                    "This is not an accident of the v1 ensemble that reweighting could dissolve: "
                    "both are shape functionals of the same field. Declaring them as two "
                    "independent falsifications counts one piece of evidence twice.",
                "the_other_pairs_remain_distinguishable": "var delta and max delta share 77% in "
                    "NGC (Pearson +0.8789) and 69% in SGC (+0.8323). n_pathological is the least "
                    "tied to the others, its largest r^2 with any of them being 0.43. The five "
                    "rules span three directions, not five.",
                "the_criterion_and_what_it_is_not": "Two reasons, both known BEFORE the pass ran. "
                    "First: 4.2b-2's threshold was already declared in record 50, while 4.2b-3's "
                    "was explicitly unwritten; writing it now would mean fixing a threshold after "
                    "seeing the value it must judge. Second: kurtosis has 1800 anchors in "
                    "n1b_spectra, p1 has none and is the only quantity of the pass that no frozen "
                    "register contains. THE CRITERION WAS NOT THE z. At the moment of this choice "
                    "it was known that r_f gives the stronger signal - z = -9.666 and -11.840 "
                    "against -7.108 and -8.150, rank 0/2000 in both hemispheres against 3/2000 and "
                    "1/2000. Selecting the more favourable statistic after seeing both would be "
                    "post hoc selection, and this clause exists to exclude it."
            },
            "iv_decision_B_the_4_2b_1_threshold_is_recalibrated_to_n_2000": {
                "decision": f"Success requires R^v2(full footprint) + 3 sigma below "
                            f"{soglia_4_2b_1('NGC')} (NGC) and {soglia_4_2b_1('SGC')} (SGC). "
                            "The form of the rule is unchanged: twice the v1 variance ratio "
                            "measured on the field_r > P10 restriction.",
                "superseded": {"NGC": 7.3581, "SGC": 16.2032,
                               "basis": "R at P10 measured on n=200: 3.6791 (NGC), 8.1016 (SGC)"},
                "new_basis": {"NGC": V1["NGC"]["R_P10"], "SGC": V1["SGC"]["R_P10"],
                              "n": 2000},
                "why": "v2 will be measured on 2000 realisations, not 200, and the checklist rule "
                    "that thresholds calibrated at one n do not apply at another is already on the "
                    "record. The revision moves in the STRICTER direction - 7.2924 < 7.3581 and "
                    "16.1314 < 16.2032 - so success becomes harder, not easier. A change that "
                    "tightens does not have to defend itself against the suspicion of convenience.",
                "the_n_200_values_are_superseded_not_deleted": True
            },
            "v_decision_C_the_4_2c_threshold_is_declared": {
                "decision": "On the ensemble mean of n_pathological over the 2000 realisations, "
                            "as P_mock is for 4.3b.",
                "NGC": {"v1_mean": V1["NGC"]["n_pat_media"], "success_below": sN,
                        "failure_above": fN},
                "SGC": {"v1_mean": V1["SGC"]["n_pat_media"], "success_below": sS,
                        "failure_above": fS},
                "the_thresholds_are_derived_not_chosen": "They are one third and two thirds of the "
                    "frozen v1 mean. Both fractions were already declared for 4.3b in record 51, "
                    "so no new fraction is introduced here, and the numbers are evaluations of a "
                    "rule rather than free parameters.",
                "invalidation_condition": "If the per-realisation dispersion on v2 exceeds one "
                    "third of the v2 mean, the rule stops deciding. On v1 that ratio is 2.09% "
                    "(NGC) and 2.54% (SGC), so the condition is nowhere near triggering. Declared "
                    "before any v2 measurement, as required.",
                "data_side_mock_side_decomposition": "The pathological threshold is DESI's maximum "
                    "of delta inside the mask - 125.47415161132812 in NGC, 161.6696 in SGC - and "
                    "is data-side and FIXED under reweighting; the count comes entirely from the "
                    "mock field. Fraction invariant under reweighting: ZERO. This is the only one "
                    "of the five rules of which that can be said, and it is why 4.2c is also the "
                    "only one carrying information not already contained in the others. The "
                    "principle applied is the one that forced the Box-Cox withdrawal, where 84.3% "
                    "of the excursion was data-side.",
                "why_not_a_rule_in_sigma": "The SEM is 1.893 on a mean of 4048.21. Any real effect "
                    "is worth thousands of sigma, so a threshold in sigma would not separate "
                    "success from failure.",
                "what_this_replaces": "The prediction '~4000 -> ~0', which was a threshold crossing "
                    "with no denominator and no zone of indecision - the shape of the four "
                    "predictions withdrawn in record 50, and the only one of that shape that had "
                    "survived. It could not be rewritten earlier because n_pathological existed in "
                    "no register."
            },
            "vi_decision_D_the_max_delta_median_of_the_handover_is_at_n_100": {
                "what_was_written": "The 7 Sep 2026 handover, section 6, under a block headed "
                    "'One-point statistics, full footprint, v1, n=200', reports for the per-mock "
                    "maximum of delta: median 3474.58, minimum 2417.18, maximum 32244.41.",
                "what_the_pass_measures_at_n_200": {"median": 3530.1012, "min": 2375.2747,
                                                    "max": 32244.4102},
                "what_the_pass_measures_at_n_100": {"median": 3474.5798, "min": 2417.1763,
                                                    "max": 32244.4102},
                "resolution": "Those three statistics are at n=100, not n=200. The median 3474.58 "
                    "holds only for n between 86 and 102; the minimum 2417.18 holds for n <= 192, "
                    "index 193 introducing 2375.27; the only round number in the intersection is "
                    "100. The identical maximum to the last digit had already established that the "
                    "sample was the same and the restriction the same, which is what excluded the "
                    "two other candidate explanations.",
                "neither_value_is_wrong": "The defect is that a line computed at n=100 sits under a "
                    "heading that declares n=200.",
                "this_amends_no_ledger_record_and_moves_no_threshold": True
            }
        },
        "reason": (
            "The one-point pass was run to close the 4.2b-3 threshold, which record 50 had left "
            "unwritten because nu.p1 existed nowhere. It closed it, and in doing so made three "
            "further things measurable that had been assumed rather than checked. That the five "
            "rules are five independent falsifications: they are not, two of them being the same "
            "shape functional at Pearson +0.9988 and +0.9985. That a threshold calibrated on 200 "
            "realisations can judge a measurement on 2000: the checklist already said otherwise, "
            "and the correct basis differs by 0.9%. That '~4000 -> ~0' was a declared rule: it was "
            "a prediction of the withdrawn shape, and only now does it have a denominator. All "
            "four decisions are taken before v2 runs, on v1 values obtained through gates declared "
            "before the measurement."
        ),
        "evidence": (
            "Runs of 7 Sep 2026. src/paper2_cancello_nu.py (selftest 26/26): verdict UNICA, "
            "max|d| = 0.000e+00 on indices 200/500/1000/1805/1999, worst moment discrepancy "
            "3.789e-07. src/paper2_passata_1punto.py (selftest 43/43): NGC 2000 records with 1850 "
            "anchors and worst discrepancy 2.562e-06 against a declared 1e-5; SGC 2000 records "
            "with 0 anchors; DESI rows with 28 step6 anchors each and worst discrepancy 0.000e+00. "
            "src/paper2_letture_1punto.py (selftest 31/31): twelve frozen n=200 constants "
            "reproduced in both hemispheres within the quantisation of the quoted digit, tightest "
            "margin 1.00. src/paper2_contratto_4_2a.py (selftest 19/19) on the smoke output: all "
            "nine one-point contract names accepted, the four N_H1_k* correctly reported absent "
            "since the pass computes no persistent homology. Cost 0.12 s per mock, 4.1 minutes per "
            "hemisphere."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-54-decisioni-su-valori-v1",
            "amends_records": [50],
            "companion_document": ("src/paper2_passata_1punto.py; src/paper2_cancello_nu.py; "
                                   "src/paper2_letture_1punto.py; "
                                   "paper2_item4_2b_dichiarazione.md; checklist_paper2.md"),
            "two_collinear_rules_are_one_test": "Collinearity is not merely redundant computation: "
                "it changes the count of opportunities for refutation. Before declaring a set of "
                "rules as independent falsifications, the correlation between the quantities they "
                "are written on must be measured on the ensemble that will be reweighted.",
            "a_flag_on_a_record_is_not_a_label_on_the_number_it_contains": "During this session "
                "35318 was taken to be a smoke value because the first record of fase3_mock.jsonl "
                "carrying it has smoke: true. It is the opposite: 35318 is the production value, "
                "registered as frozen in records 14, 23, 35, 51 and 52 and held as "
                "FROZEN_NH1_MOCK0 in src/paper2_tabres_probe.py, while 35538 appears in a smoke "
                "record. A smoke test REPRODUCES production values - that is its purpose - so the "
                "presence of a number inside a smoke record says nothing about its provenance. "
                "Establishing it requires looking at every record that carries it.",
            "on_a_quoted_constant_the_tolerance_is_half_a_unit_of_the_last_digit": "A relative "
                "tolerance of 1e-4 rejects 0.274250 against a quoted 0.2743, which is correct: the "
                "quantisation of four decimals is worth 1.8e-4 in relative terms. The admissible "
                "discrepancy against a quoted constant is set by its quotation precision, not by a "
                "figure chosen elsewhere.",
            "a_block_heading_does_not_necessarily_cover_every_line_under_it": "The n=100 case "
                "under a heading declaring n=200.",
            "a_record_that_is_not_a_measurement_does_not_belong_in_the_register_of_measurements": (
                "The pass initially wrote its summary, which has no idx, into the per-realisation "
                "register. paper2_contratto_4_2a rejected the file for having no index key common "
                "to all records. It is the same shape as the defect of the 38 smoke tests inside "
                "fase3_mock.jsonl. Summaries now live in a file of their own."),
            "what_this_does_not_do": "It runs no v2 pass, changes no threshold of record 51, does "
                "not touch rules 4.2b-2 and 4.2b-4 beyond recording their v1 values, and asserts "
                "nothing about the outcome of the reweighting."
        }
    }


def cmd_append(args):
    try:
        raw, recs, eol, crlf, lf = leggi_ledger(args.ledger)
    except Rifiuto as e:
        print(f"RIFIUTO: {e}")
        return 2

    n = len(recs)
    if n != args.attesi:
        print(f"RIFIUTO: il ledger ha {n} record, attesi {args.attesi}")
        return 2
    if any(r.get("item") == ITEM for r in recs):
        print(f"RIFIUTO: esiste gia' un record con item '{ITEM}'")
        return 2
    if not os.path.isfile(args.reference):
        print(f"RIFIUTO: reference inesistente: {args.reference}")
        return 2

    ref_file_sha = sha256_file(args.reference)
    with open(args.reference, "r", encoding="utf-8") as fh:
        ref_self_sha = json.load(fh).get("_self_sha256")
    ultimo = recs[-1]
    if ultimo.get("reference_file_sha256") and ultimo["reference_file_sha256"] != ref_file_sha:
        print(f"RIFIUTO: sha256 del reference cambiato: ultimo record "
              f"{ultimo['reference_file_sha256'][:12]}… ricalcolato {ref_file_sha[:12]}…")
        return 2
    if ultimo.get("reference_self_sha256") and ultimo["reference_self_sha256"] != ref_self_sha:
        print("RIFIUTO: self-digest del reference cambiato")
        return 2

    rec = costruisci_record(n, ref_file_sha, ref_self_sha)
    linea = json.dumps(rec, ensure_ascii=False).encode("utf-8")

    print(f"ledger    : {os.path.abspath(args.ledger)}")
    print(f"record    : {n} -> {n + 1}")
    print(f"fine riga : {'CRLF' if eol == CRLF else 'LF'} (maggioranza: CRLF {crlf}, LF soli {lf})")
    print(f"ancore    : file {ref_file_sha[:12]}…  self {str(ref_self_sha)[:12]}…  concordi")
    print(f"item      : {rec['item']}")
    print(f"byte      : {len(linea)}")
    print(f"soglie    : 4.2b-1 {soglia_4_2b_1('NGC')} / {soglia_4_2b_1('SGC')}   "
          f"4.2c {soglie_4_2c('NGC')[0]} / {soglie_4_2c('SGC')[0]}")

    if args.dry_run:
        print("dry-run: nessuna scrittura")
        return 0

    if args.backup:
        os.makedirs(os.path.dirname(os.path.abspath(args.backup)) or ".", exist_ok=True)
        with open(args.backup, "wb") as fh:
            fh.write(raw)
        print(f"backup    : {os.path.abspath(args.backup)}")

    with open(args.ledger, "ab") as fh:
        fh.write(linea + eol)

    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(args.ledger)
    atteso_lf = lf + (1 if eol == b"\n" else 0)
    if len(recs2) != n + 1 or recs2[-1].get("item") != ITEM:
        print("ERRORE: rilettura incoerente")
        return 3
    if f"record {n + 1}." not in recs2[-1]["numbering_rule"]:
        print("ERRORE: numbering_rule incoerente con la posizione")
        return 3
    if lf2 != atteso_lf:
        print(f"ERRORE: righe a LF isolato da {lf} a {lf2}, atteso {atteso_lf}")
        return 3
    if not raw2.startswith(raw):
        print("ERRORE: i record precedenti non sono byte-identici")
        return 3
    print(f"riletto   : {len(recs2)} record, LF isolati {lf2} (attesi {atteso_lf})")
    print("APPESO")
    print()
    print("PASSO OBBLIGATORIO NELLO STESSO COMMIT:")
    print("  python src\\paper2_patch_documented_amendments.py apply "
          f"--file src\\paper2_freeze_verify.py --da {n} --a {n + 1} "
          f"--ledger src\\paper2_v1_amendments.jsonl")
    print("  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="amend54_")
    led = os.path.join(base, "ledger.jsonl")
    ref = os.path.join(base, "reference.json")
    with open(ref, "w", encoding="utf-8", newline="") as fh:
        json.dump({"_self_sha256": "s" * 64}, fh)
    ref_sha = sha256_file(ref)

    def scrivi_ledger(n):
        with open(led, "wb") as fh:
            for i in range(n):
                r = {"item": f"x{i}", "type": "protocol"}
                if i == n - 1:
                    r["reference_file_sha256"] = ref_sha
                    r["reference_self_sha256"] = "s" * 64
                fh.write(json.dumps(r).encode("utf-8") + CRLF)

    class A:
        pass

    def a(attesi=53, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    scrivi_ledger(53)
    raw_prima = open(led, "rb").read()
    ok("1 ledger sintetico a 53 record", len(leggi_ledger(led)[1]) == 53)
    ok("2 dry-run non scrive", cmd_append(a(dry=True)) == 0 and open(led, "rb").read() == raw_prima)
    ok("3 conteggio sbagliato: rifiuto", cmd_append(a(attesi=52)) == 2)
    ok("4 append: esito 0", cmd_append(a()) == 0)

    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("5 il conteggio cambia: 53 -> 54", len(recs2) == 54)
    ok("6 numbering_rule dice 54", "record 54." in recs2[-1]["numbering_rule"])
    ok("7 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 54)
    ok("8 i 53 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("9 secondo append rifiutato per item duplicato", cmd_append(a(attesi=54)) == 2)

    rec = recs2[-1]
    nv = rec["new_value"]
    A_ = nv["iii_decision_A_rule_4_2b_3_withdrawn_as_a_falsification"]
    B_ = nv["iv_decision_B_the_4_2b_1_threshold_is_recalibrated_to_n_2000"]
    C_ = nv["v_decision_C_the_4_2c_threshold_is_declared"]
    D_ = nv["vi_decision_D_the_max_delta_median_of_the_handover_is_at_n_100"]
    v1 = nv["ii_measured_v1_values_n_2000"]

    # --- ogni soglia e' ricalcolata, non riletta ---
    ok("10 4.2b-1 NGC e' due volte R a P10 su n=2000",
       abs(round(2 * v1["NGC"]["R_P10"], 4) - 7.2924) < 1e-9)
    ok("11 4.2b-1 SGC e' due volte R a P10 su n=2000",
       abs(round(2 * v1["SGC"]["R_P10"], 4) - 16.1314) < 1e-9)
    ok("12 la nuova soglia e' piu' severa della vecchia in entrambi",
       7.2924 < B_["superseded"]["NGC"] and 16.1314 < B_["superseded"]["SGC"])
    ok("13 4.2c NGC: successo = media v1 / 3, fallimento = 2/3",
       abs(C_["NGC"]["success_below"] - round(C_["NGC"]["v1_mean"] / 3, 2)) < 1e-9
       and abs(C_["NGC"]["failure_above"] - round(2 * C_["NGC"]["v1_mean"] / 3, 2)) < 1e-9)
    ok("14 4.2c SGC: successo = media v1 / 3, fallimento = 2/3",
       abs(C_["SGC"]["success_below"] - round(C_["SGC"]["v1_mean"] / 3, 2)) < 1e-9
       and abs(C_["SGC"]["failure_above"] - round(2 * C_["SGC"]["v1_mean"] / 3, 2)) < 1e-9)
    ok("15 successo sta sotto fallimento in entrambi gli emisferi",
       C_["NGC"]["success_below"] < C_["NGC"]["failure_above"]
       and C_["SGC"]["success_below"] < C_["SGC"]["failure_above"])
    ok("16 la condizione di invalidazione di 4.2c non e' al limite su v1",
       v1["NGC"]["n_pathological"]["mock_sd"] / v1["NGC"]["n_pathological"]["mock_mean"] < 1 / 3
       and v1["SGC"]["n_pathological"]["mock_sd"] / v1["SGC"]["n_pathological"]["mock_mean"] < 1 / 3)

    # --- coerenza interna dei valori v1 ---
    ok("17 r_f di DESI torna dai suoi p1, p99 e sigma nei due emisferi",
       all(abs((v1[r]["nu_desi"]["p99"] - v1[r]["nu_desi"]["p1"])
               / v1[r]["nu_desi"]["sigma"] - v1[r]["r_f"]["desi"]) < 5e-6
           for r in ("NGC", "SGC")))
    ok("18 z di r_f torna da media e sd dei mock",
       all(abs((v1[r]["r_f"]["desi"] - v1[r]["r_f"]["mock_mean"])
               / v1[r]["r_f"]["mock_sd"] - v1[r]["r_f"]["z"]) < 5e-4
           for r in ("NGC", "SGC")))
    ok("19 z della curtosi torna da media e sd dei mock",
       all(abs((v1[r]["kurt_nu"]["desi"] - v1[r]["kurt_nu"]["mock_mean"])
               / v1[r]["kurt_nu"]["mock_sd"] - v1[r]["kurt_nu"]["z"]) < 5e-4
           for r in ("NGC", "SGC")))
    ok("20 R a footprint pieno torna da media mock e var DESI",
       all(abs(v1[r]["var_delta"]["mock_mean"] / v1[r]["var_delta"]["desi"]
               - v1[r]["R_full"]) < 0.05 for r in ("NGC", "SGC")))
    ok("21 la soglia dei patologici e' il massimo di delta di DESI",
       all(abs(v1[r]["pathological_threshold"] - v1[r]["max_delta"]["desi"]) < 5e-5
           for r in ("NGC", "SGC")))
    ok("22 i voxel di maschera sono quelli congelati",
       v1["NGC"]["mask_voxels"] == 307805 and v1["SGC"]["mask_voxels"] == 172225)

    # --- la clausola che protegge la decisione A ---
    ok("23 il record dichiara che il criterio NON e' stato il z",
       "THE CRITERION WAS NOT THE z" in A_["the_criterion_and_what_it_is_not"])
    ok("24 il record riporta il z maggiore di r_f, che ha scartato",
       "-9.666" in A_["the_criterion_and_what_it_is_not"]
       and "-11.840" in A_["the_criterion_and_what_it_is_not"])
    ok("25 la collinearita' e' registrata per entrambi gli emisferi",
       "+0.9988" in A_["the_fact"] and "+0.9985" in A_["the_fact"])
    ok("26 r_f resta come diagnostica senza soglia",
       "NO threshold" in A_["decision"])

    # --- decisione D e regole ---
    ok("27 D: n=100 riproduce le tre statistiche della consegna",
       abs(D_["what_the_pass_measures_at_n_100"]["median"] - 3474.5798) < 5e-5
       and abs(D_["what_the_pass_measures_at_n_100"]["min"] - 2417.1763) < 5e-5)
    ok("28 D: il massimo e' identico fra n=100 e n=200, che e' cio' che identifica il campione",
       D_["what_the_pass_measures_at_n_100"]["max"]
       == D_["what_the_pass_measures_at_n_200"]["max"])
    ok("29 D non emenda nessun record e non muove soglie",
       D_["this_amends_no_ledger_record_and_moves_no_threshold"] is True)
    ok("30 emenda il record 50, dove le due soglie toccate erano scritte",
       rec["rules"]["amends_records"] == [50])
    ok("31 il record dichiara di non far girare v2",
       "runs no v2 pass" in rec["rules"]["what_this_does_not_do"])
    ok("32 i cancelli importati sono quelli del 50",
       sys.modules["paper2_append_amend50"].sha256_file is sha256_file)

    passati = sum(1 for _, c in controlli if c)
    print()
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print(f"selftest: {passati}/{len(controlli)}")
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_a = sub.add_parser("append")
    p_a.add_argument("--ledger", required=True)
    p_a.add_argument("--reference", required=True)
    p_a.add_argument("--attesi", type=int, default=53)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

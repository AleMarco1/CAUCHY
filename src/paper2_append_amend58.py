#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend58.py — appende il record 58: l'ensemble v2 esiste, cinque
regole su sei hanno un esito, e tutte e cinque FALLISCONO. La soglia di 4.3b e'
ricalibrata a n=2000 e DICHIARATA qui, prima che P^v2 venga calcolata.

I cancelli sull'append si importano da paper2_append_amend50.

Uso:
    python paper2_append_amend58.py selftest
    python paper2_append_amend58.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 57 --dry-run
"""

import argparse
import datetime as dt
import json
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

ITEM = "4.2a-4.2b-4.2c/ensemble_v2_misurato_cinque_regole_falliscono"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"
CRLF = chr(13).encode() + chr(10).encode()

# Esiti misurati l'11 settembre 2026, src/paper2_verdetto_v2.py (selftest 67/67),
# su results/paper2/verdetto_v2_{NGC,SGC}.json.
R = {
    "NGC": {
        "b1_R": 979.8053799004235, "b1_sigma": 4.149978169960069,
        "b1_meno3": 967.3554453905433, "b1_succ": 7.2924,
        "b2_z": -7.113535772203109, "b2_rango": 3,
        "b2_mock": 2.804624141062464, "b2_sd": 0.4558687843801427,
        "b2_desi": -0.43821476405642734,
        "b4_rango": 0, "b4_mediana_su_desi": 28.469009034820797,
        "c_media": 4021.077, "c_sd": 83.29916834352767,
        "c_succ": 1349.40, "c_fall": 2698.81, "c_disp": 0.020715636219731097,
        "P_corr": 3.8160788230778366, "P_curv": 1.1912210274362844,
        "P_sem": 0.00555886271332237,
        "soglia_vecchia": 1.2648, "P_v1_n200": 3.7943,
        "sep_sigma": 228.82851042727515, "guadagno_P": 5.005054953585065,
        "npat_d": -27.092, "npat_sem": 0.41126188270745934,
        "npat_sem_nonapp": 2.6533247673740545,
        "kurt_d": -0.012871997980808332, "kurt_sem": 5.848282727438681e-05,
        "kurt_sem_nonapp": 0.01445025658795716,
        "voxel_fra_soglie": 0, "diverge": 23, "n_record": 2000,
    },
    "SGC": {
        "b1_R": 2085.226525216027, "b1_sigma": 7.444587799414521,
        "b1_meno3": 2062.892761817783, "b1_succ": 16.1314,
        "b2_z": -8.16432399809673, "b2_rango": 1,
        "b2_mock": 1.124908878835639, "b2_sd": 0.2768241571660709,
        "b2_desi": -1.1351732307682145,
        "b4_rango": 0, "b4_mediana_su_desi": 40.31848589292756,
        "c_media": 2795.108, "c_sd": 70.76500674125273,
        "c_succ": 937.19, "c_fall": 1874.37, "c_disp": 0.025317449895049755,
        "P_corr": 3.9716387996783453, "P_curv": 3.5881993622738086,
        "P_sem": 0.007117671607931772,
        "soglia_vecchia": 1.3223, "P_v1_n200": 3.9668,
        "sep_sigma": 185.9989716886461, "guadagno_P": 4.7267080573383184,
        "npat_d": -16.447, "npat_sem": 0.3190720905994439,
        "npat_sem_nonapp": 2.2482687810303905,
        "kurt_d": -0.0077848662539670805, "kurt_sem": 3.877105816536517e-05,
        "kurt_sem_nonapp": 0.008776607021569299,
        "voxel_fra_soglie": 10, "diverge": 11, "n_record": 2000,
    },
}
SD_NPAT = {"NGC": 84.66, "SGC": 71.45}
BIAS_MAX_IN_SEM = 0.5


def soglie_4_3b(P_corr):
    return P_corr / 3.0, 2.0 * P_corr / 3.0


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    sN, fN = soglie_4_3b(R["NGC"]["P_corr"])
    sS, fS = soglie_4_3b(R["SGC"]["P_corr"])
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "ensemble_v2_exists_and_five_of_six_rules_fail_in_both_hemispheres",
        "json_path": ("results/paper2/ensemble_v2_{NGC,SGC}.jsonl; "
                      "results/paper2/verdetto_v2_{NGC,SGC}.json; "
                      "results/paper2/incrocio_cache_{NGC,SGC}.json; "
                      "src/paper2_runner_4_2a.py; src/paper2_verdetto_v2.py; "
                      "records 50, 54, 57"),
        "old_value": (
            "Record 50 rewrote the six falsification rules of 4.2b/4.2c after the original "
            "predictions were found unfalsifiable on v2, and record 54 recalibrated two "
            "thresholds from n=200 to n=2000. Record 57 measured 4.2b-5 and found it failing in "
            "both hemispheres. The remaining five rules had thresholds and no ensemble: item "
            "4.2a, the FKP-weighted ensemble they are evaluated on, did not exist. For 4.3b the "
            "threshold still sat at n=200 and rested on a JOIN across two registers produced by "
            "different chains (record 50 section vii): per_mock_*_erosion_restrict for k=0,2,3 "
            "and fase3_mock for k=1."
        ),
        "new_value": {
            "i_the_ensemble_exists_and_is_traceable_file_by_file": {
                "what_was_built": "src/paper2_runner_4_2a.py (selftest 62/62). 2000 "
                    "realisations per hemisphere at the fiducial geometry, EIGHT TDA calls each: "
                    "a unit-weight branch and an FKP branch, both at erosion k = 0,1,2,3, plus "
                    "the one-point diagnostics on BOTH branches. About 80 s per mock with the "
                    "two hemispheres in parallel, some 45 hours each.",
                "why_eight_and_not_five": "Two reasons, the second unforeseen. First, the v1 "
                    "ladder over 2000 realisations did not exist: fase3_mock has 200 indices and "
                    "two levels, per_mock_*_R5 only k=0. Second, record 50 section vii states "
                    "that assembling P per realisation required a JOIN across two registers from "
                    "different chains, to be validated before use. The unit branch produces "
                    "k=0..3 for all 2000 in a single register: the join is no longer needed.",
                "why_the_one_point_on_both_branches": "v1 from the cache and v2 from the R3 "
                    "chain would differ by 1.5e-3 to 2.9e-3 on delta from the geometry path "
                    "alone (D4a). Computed in the same pass, from the same realisation, on the "
                    "same path, that term cancels. The declared v1 values of record 54 are "
                    "unchanged; this is a SECOND v1, paired.",
                "traceability": "src/paper2_incrocio_cache.py (selftest 21/21): for each of the "
                    "4000 records the sha256 of the cached delta file was recomputed from disk "
                    "and compared with the digest deposited in the record. 4000 of 4000 match, "
                    "no missing file, no orphan file in the cache. 33.6 GB per hemisphere. This "
                    "check did not exist: paper2_manifest_cache.py verifies MANIFEST against "
                    "DISK; this verifies REGISTER against DISK, and it is the register that "
                    "carries the results."
            },
            "ii_five_rules_of_six_and_all_five_fail": {
                "4.2b-1_variance_of_delta": {
                    "NGC": {"R": R["NGC"]["b1_R"], "sigma": R["NGC"]["b1_sigma"],
                            "R_minus_3sigma": R["NGC"]["b1_meno3"],
                            "success_below": R["NGC"]["b1_succ"],
                            "failure_above": 100.0, "esito": "FAILURE"},
                    "SGC": {"R": R["SGC"]["b1_R"], "sigma": R["SGC"]["b1_sigma"],
                            "R_minus_3sigma": R["SGC"]["b1_meno3"],
                            "success_below": R["SGC"]["b1_succ"],
                            "failure_above": 100.0, "esito": "FAILURE"},
                    "not_marginal": "The rule asked for R below 7.29 and 16.13. It comes out at "
                        "980 and 2085, ten and twenty times the failure threshold of 100."},
                "4.2b-2_kurtosis_of_nu": {
                    "NGC": {"z": R["NGC"]["b2_z"], "rank": R["NGC"]["b2_rango"],
                            "mock": R["NGC"]["b2_mock"], "sd": R["NGC"]["b2_sd"],
                            "desi": R["NGC"]["b2_desi"], "esito": "FAILURE"},
                    "SGC": {"z": R["SGC"]["b2_z"], "rank": R["SGC"]["b2_rango"],
                            "mock": R["SGC"]["b2_mock"], "sd": R["SGC"]["b2_sd"],
                            "desi": R["SGC"]["b2_desi"], "esito": "FAILURE"},
                    "both_clauses_fail": "|z| exceeds 5 AND the rank sits at 3 and 1 out of "
                        "2000, far outside the central 95 per cent. Record 50 required both "
                        "for success; neither holds."},
                "4.2b-4_maximum_of_delta": {
                    "NGC": {"rank": 0, "median_over_desi": R["NGC"]["b4_mediana_su_desi"],
                            "esito": "FAILURE"},
                    "SGC": {"rank": 0, "median_over_desi": R["SGC"]["b4_mediana_su_desi"],
                            "esito": "FAILURE"},
                    "and_it_moves_the_WRONG_way": "The quantity record 50 requires to be "
                        "reported always - median(max delta)^v2 / 125 - was 27.80 on v1. On v2 "
                        "it is 28.47 in NGC and 40.32 in SGC. Reweighting widens the gap instead "
                        "of closing it."},
                "4.2c_pathological_voxels": {
                    "NGC": {"mean": R["NGC"]["c_media"], "sd": R["NGC"]["c_sd"],
                            "success_below": R["NGC"]["c_succ"],
                            "failure_above": R["NGC"]["c_fall"],
                            "dispersion_over_mean": R["NGC"]["c_disp"],
                            "invalidated": False, "esito": "FAILURE"},
                    "SGC": {"mean": R["SGC"]["c_media"], "sd": R["SGC"]["c_sd"],
                            "success_below": R["SGC"]["c_succ"],
                            "failure_above": R["SGC"]["c_fall"],
                            "dispersion_over_mean": R["SGC"]["c_disp"],
                            "invalidated": False, "esito": "FAILURE"},
                    "not_invalidated": "The declared invalidation condition - per-realisation "
                        "dispersion above one third of the mean - is nowhere near met: 2.1 and "
                        "2.5 per cent."},
                "4.2b-5_box_cox": "FAILURE in both hemispheres, record 57.",
                "4.2b-3": "withdrawn as a falsification by record 54; r_f reported without a "
                    "threshold: 5.6458 +- 0.2502 (NGC), 4.7882 +- 0.1507 (SGC).",
                "what_this_settles": "FKP reweighting of the mock voxelisation is not the "
                    "explanation of the anomaly. The hypothesis is falsified on twenty "
                    "independent fronts - five rules, two hemispheres, two paired branches - and "
                    "not one of them is marginal."
            },
            "iii_the_pairing_earned_the_twenty_three_extra_hours": {
                "kurtosis_NGC": {"delta": R["NGC"]["kurt_d"],
                                 "sem_paired": R["NGC"]["kurt_sem"],
                                 "sem_unpaired": R["NGC"]["kurt_sem_nonapp"],
                                 "gain": R["NGC"]["kurt_sem_nonapp"] / R["NGC"]["kurt_sem"]},
                "n_pat_NGC": {"delta": R["NGC"]["npat_d"],
                              "sem_paired": R["NGC"]["npat_sem"],
                              "sem_unpaired": R["NGC"]["npat_sem_nonapp"],
                              "gain": R["NGC"]["npat_sem_nonapp"] / R["NGC"]["npat_sem"]},
                "what_it_means": "Without the paired unit branch the kurtosis shift of -0.0129 "
                    "would have read 0.9 sigma instead of 220. The eight TDA calls per "
                    "realisation cost 23 hours and bought this."
            },
            "iv_4_3b_the_threshold_is_recalibrated_and_DECLARED_HERE": {
                "NGC": {"P_v1_corrected_pp": R["NGC"]["P_corr"],
                        "sem_pp": R["NGC"]["P_sem"],
                        "success_below_pp": sN, "failure_above_pp": fN,
                        "previous_threshold_at_n200": R["NGC"]["soglia_vecchia"],
                        "shift_percent": 100 * (sN / R["NGC"]["soglia_vecchia"] - 1),
                        "zone_separation_sigma": R["NGC"]["sep_sigma"]},
                "SGC": {"P_v1_corrected_pp": R["SGC"]["P_corr"],
                        "sem_pp": R["SGC"]["P_sem"],
                        "success_below_pp": sS, "failure_above_pp": fS,
                        "previous_threshold_at_n200": R["SGC"]["soglia_vecchia"],
                        "shift_percent": 100 * (sS / R["SGC"]["soglia_vecchia"] - 1),
                        "zone_separation_sigma": R["SGC"]["sep_sigma"]},
                "why_recalibrate_when_the_shift_is_half_a_per_cent": "Not for the sample size. "
                    "The n=200 value rested on a JOIN across two registers produced by DIFFERENT "
                    "CHAINS - paper1_remap for k=0,2,3 and R3 for k=1 - and that distinction "
                    "cost four run stoppages on 9 September. The new value comes from ONE "
                    "register, ONE chain, no join. It is not better sampled; it is better "
                    "founded. The fractions themselves, one third and two thirds, are unchanged.",
                "the_order_is_enforced_by_the_tool": "paper2_verdetto_v2.py refuses to compute "
                    "P^v2 unless the threshold is passed in from outside AND matches the one "
                    "derived from P^v1 to 1e-6. The first pass returned SOSPESA for both "
                    "hemispheres and printed the derived thresholds without touching P^v2. This "
                    "record declares them; only then can the second pass run.",
                "the_curvature_term_is_NOT_small_on_real_data": {
                    "NGC": {"P_curvature_pp": R["NGC"]["P_curv"],
                            "percent_of_uncorrected_P":
                                100 * R["NGC"]["P_curv"]
                                / (R["NGC"]["P_corr"] + R["NGC"]["P_curv"])},
                    "SGC": {"P_curvature_pp": R["SGC"]["P_curv"],
                            "percent_of_uncorrected_P":
                                100 * R["SGC"]["P_curv"]
                                / (R["SGC"]["P_corr"] + R["SGC"]["P_curv"])},
                    "what_record_50_says": "«It is small - under 1% of P on a synthetic fixture "
                        "- but it is reported, not assumed.»",
                    "what_it_actually_is": "23.8 per cent of the uncorrected P in NGC and 47.5 "
                        "per cent in SGC. On a synthetic fixture it may well be under 1 per "
                        "cent; on the real ladder it is not, by a factor of fifty. The "
                        "definition is unchanged and the subtraction was always prescribed - but "
                        "the characterisation 'small' is withdrawn, because a reader who "
                        "believed it might use the uncorrected P thinking the difference "
                        "negligible. The uncorrected P is 5.0073 pp in NGC, which is the +5.00 "
                        "pp record 50 quotes."
                }
            },
            "v_what_the_gates_caught_and_what_they_cost": {
                "four_stoppages_in_one_day": "The two runs stopped four times on 9 September, "
                    "every time on a gate of mine that was wrongly built, and every time the "
                    "remedy was a criterion already derived elsewhere - half the SEM, record 36. "
                    "In order: the ULP tripwire on the pathological threshold fired on a "
                    "difference of paths; the per_mock anchor compared a DIFFERENT CHAIN with a "
                    "same-chain tolerance; the voxels-between-thresholds gate tested the "
                    "PRESENCE of an effect rather than its SIZE and stopped SGC on ONE voxel; "
                    "and the n6 anchor repeated the second mistake two hours after it was fixed "
                    "ten lines above.",
                "the_question_that_was_not_asked": "For every register used as a gate: WAS THIS "
                    "WRITTEN BY THE CODE I AM RUNNING? fase3_mock yes. per_mock and n6 no - "
                    "they come from paper1_remap and from a chain that does not set the distance "
                    "table before setup_region. Those are cross-chain DIAGNOSTICS and their "
                    "tolerance cannot be that of a reproduction.",
                "what_the_diagnostics_then_measured": {
                    "cross_chain_divergence_NGC": {"n": R["NGC"]["diverge"], "of": 2000,
                                                   "bias_in_sem": 0.152},
                    "cross_chain_divergence_SGC": {"n": R["SGC"]["diverge"], "of": 2000,
                                                   "bias_in_sem": 0.175},
                    "note": "The first quantification of how often the 4001-node distance table "
                        "moves N_H1: about 1 per cent of realisations, with a bias on the "
                        "ensemble mean of 0.15-0.18 SEM against a declared limit of half. D4a "
                        "recorded that N_H1 is 'identical at all resolutions'; this measures how "
                        "often that 'identical' has an exception."},
                "voxels_between_the_two_thresholds": {
                    "NGC": R["NGC"]["voxel_fra_soglie"], "SGC": R["SGC"]["voxel_fra_soglie"],
                    "bias_in_sem_SGC": 0.0031,
                    "note": "Ten voxels across 2000 realisations in SGC, none in NGC: three "
                        "thousandths of a SEM. The binary gate would have stopped the run ten "
                        "times for this."},
                "and_a_gate_that_caught_a_real_thing": "The chain anchor against fase3_mock, "
                    "tolerance ZERO, passed on all 200 indices in both hemispheres: the "
                    "two-branch loop written here IS R3.one_mock. And nu computed through "
                    "build_field and through build_nu agreed BIT FOR BIT on all 4000 "
                    "realisations and both branches."
            }
        },
        "reason": (
            "Item 4.2a is complete: the FKP-weighted ensemble exists, 2000 realisations per "
            "hemisphere, traceable file by file. Five of the six declared rules now have an "
            "outcome and all five fail, in both hemispheres, none of them marginally. FKP "
            "reweighting of the mock voxelisation is not the explanation of the anomaly. The "
            "sixth, 4.3b, has its threshold recalibrated here - not for the sample size, which "
            "moves it by half a per cent, but because the n=200 value rested on a join across "
            "two chains - and declared before P^v2 is computed, with the order enforced by a "
            "refusal in the tool rather than by care."
        ),
        "evidence": (
            "Runs of 9-11 Sep 2026, src/paper2_runner_4_2a.py (selftest 62/62), 2000 records per "
            "hemisphere, summaries PULITA. Verdict of 11 Sep, src/paper2_verdetto_v2.py "
            "(selftest 67/67): fourteen gates passed in both hemispheres before any rule was "
            "applied. Cross-check register-against-disk, src/paper2_incrocio_cache.py (selftest "
            "21/21): 4000 of 4000 digests match, no orphan, 33.6 GB per hemisphere in 20 s. "
            "Chain anchor against fase3_mock: worst discrepancy ZERO on 200 indices per "
            "hemisphere. nu by two constructions: 0 differing cells on 4000 realisations."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-58-ensemble-v2-cinque-regole",
            "amends_records": [50, 54],
            "companion_document": ("src/paper2_verdetto_v2.py; paper2_stato.md; "
                                   "checklist items 4.2a, 4.2b, 4.2c, 4.3b"),
            "a_gate_compares_what_the_running_code_produced": "Four stoppages in one day on this "
                "distinction. A register written by another chain is a DIAGNOSTIC, and its "
                "tolerance cannot be that of a reproduction. The question is not what the number "
                "is but where it came from.",
            "when_a_criterion_has_been_derived_for_one_quantity_ask_first_whether_it_applies_to_the_next":
                "Half the SEM, derived by record 36 for D5c, served four times on 11 September "
                "alone: D5c, the cross-chain divergence, the voxels between thresholds, and the "
                "bias on the pathological count. Each time the first attempt invented a new "
                "threshold instead.",
            "a_fix_applied_to_the_writer_must_be_applied_to_the_reader": "The per_mock anchor "
                "was renamed when it was demoted to a diagnostic, and the verdict still looked "
                "for the old name: it would have declared missing a field present on all 2000 "
                "records. Same for the voxel gate, left binary in the reader after being made "
                "dimensional in the writer. Record 52 in a new form, twice.",
            "what_this_does_not_do": "It asserts nothing about 4.3b, whose outcome is computed "
                "only after this record exists. It does not touch the v1 ensemble, the declared "
                "v1 values of record 54, or any Paper 1 result."
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
        print("RIFIUTO: sha256 del reference cambiato")
        return 2
    if ultimo.get("reference_self_sha256") and ultimo["reference_self_sha256"] != ref_self_sha:
        print("RIFIUTO: self-digest del reference cambiato")
        return 2

    rec = costruisci_record(n, ref_file_sha, ref_self_sha)
    linea = json.dumps(rec, ensure_ascii=False).encode("utf-8")
    sN, fN = soglie_4_3b(R["NGC"]["P_corr"])
    sS, fS = soglie_4_3b(R["SGC"]["P_corr"])
    print(f"ledger    : {os.path.abspath(args.ledger)}")
    print(f"record    : {n} -> {n + 1}")
    print(f"fine riga : {'CRLF' if eol == CRLF else 'LF'} (maggioranza: CRLF {crlf}, LF soli {lf})")
    print(f"ancore    : file {ref_file_sha[:12]}…  self {str(ref_self_sha)[:12]}…  concordi")
    print(f"item      : {rec['item']}")
    print(f"byte      : {len(linea)}")
    print("esiti     : 4.2b-1, 4.2b-2, 4.2b-4, 4.2c FALLIMENTO in entrambi")
    print(f"soglia 4.3b NGC: successo < {sN:.12f}   fallimento > {fN:.12f}")
    print(f"soglia 4.3b SGC: successo < {sS:.12f}   fallimento > {fS:.12f}")

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
        print(f"ERRORE: righe a LF isolato da {lf} a {lf2}")
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
    print()
    print("E SOLO ORA il secondo giro del verdetto:")
    print(f"  python src\\paper2_verdetto_v2.py verdetto --region NGC --soglia-4-3b {sN!r}")
    print(f"  python src\\paper2_verdetto_v2.py verdetto --region SGC --soglia-4-3b {sS!r}")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="amend58_")
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

    def a(attesi=57, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    scrivi_ledger(57)
    raw_prima = open(led, "rb").read()
    ok("1 ledger sintetico a 57 record", len(leggi_ledger(led)[1]) == 57)
    ok("2 dry-run non scrive", cmd_append(a(dry=True)) == 0 and open(led, "rb").read() == raw_prima)
    ok("3 conteggio sbagliato: rifiuto", cmd_append(a(attesi=56)) == 2)
    ok("4 append: esito 0", cmd_append(a()) == 0)
    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("5 il conteggio cambia: 57 -> 58", len(recs2) == 58)
    ok("6 numbering_rule dice 58", "record 58." in recs2[-1]["numbering_rule"])
    ok("7 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 58)
    ok("8 i 57 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("9 secondo append rifiutato per item duplicato", cmd_append(a(attesi=58)) == 2)

    rec = recs2[-1]
    nv = rec["new_value"]
    II = nv["ii_five_rules_of_six_and_all_five_fail"]
    IV = nv["iv_4_3b_the_threshold_is_recalibrated_and_DECLARED_HERE"]

    # --- gli esiti si RICALCOLANO dalle soglie ------------------------------
    for reg in ("NGC", "SGC"):
        d = R[reg]
        ok(f"10+ {reg}: 4.2b-1 fallisce perche' R-3sigma supera 100",
           d["b1_meno3"] > 100.0
           and II["4.2b-1_variance_of_delta"][reg]["esito"] == "FAILURE")
        ok(f"12+ {reg}: e R+3sigma non e' sotto la soglia di successo",
           d["b1_R"] + 3 * d["b1_sigma"] > d["b1_succ"])
        ok(f"14+ {reg}: 4.2b-2 fallisce per |z| oltre 5",
           abs(d["b2_z"]) > 5.0
           and II["4.2b-2_kurtosis_of_nu"][reg]["esito"] == "FAILURE")
        ok(f"16+ {reg}: e anche il rango e' fuori dal 95% centrale",
           d["b2_rango"] < 50)
        ok(f"18+ {reg}: 4.2b-4 fallisce per rango <= 20", d["b4_rango"] <= 20)
        ok(f"20+ {reg}: 4.2c fallisce perche' la media supera la soglia",
           d["c_media"] > d["c_fall"])
        ok(f"22+ {reg}: e NON e' invalidata, la dispersione e' lontana da 1/3",
           d["c_disp"] < 1.0 / 3.0 / 10)

    # --- il dato piu' insidioso: la mediana peggiora ------------------------
    ok("26 la mediana su DESI PEGGIORA in entrambi: era 27.80",
       R["NGC"]["b4_mediana_su_desi"] > 27.8 and R["SGC"]["b4_mediana_su_desi"] > 27.8)

    # --- 4.3b: le soglie si riderivano da P^v1 ------------------------------
    for reg, chiave in (("NGC", "NGC"), ("SGC", "SGC")):
        s_, f_ = soglie_4_3b(R[reg]["P_corr"])
        ok(f"27+ {reg}: la soglia di successo e' un terzo di P^v1 corretta",
           abs(IV[chiave]["success_below_pp"] - s_) < 1e-12
           and abs(s_ - R[reg]["P_corr"] / 3) < 1e-12)
        ok(f"29+ {reg}: e il fallimento e' il doppio del successo",
           abs(IV[chiave]["failure_above_pp"] - 2 * s_) < 1e-12)
        ok(f"31+ {reg}: la ricalibrazione sposta la soglia di meno dell'1%",
           abs(IV[chiave]["shift_percent"]) < 1.0)
        ok(f"33+ {reg}: le zone distano molto piu' di 3 sigma",
           R[reg]["sep_sigma"] > 3.0)

    # --- la curvatura NON e' piccola ----------------------------------------
    C = IV["the_curvature_term_is_NOT_small_on_real_data"]
    for reg in ("NGC", "SGC"):
        atteso = 100 * R[reg]["P_curv"] / (R[reg]["P_corr"] + R[reg]["P_curv"])
        ok(f"35+ {reg}: la curvatura e' la percentuale dichiarata della P non corretta",
           abs(C[reg]["percent_of_uncorrected_P"] - atteso) < 1e-9)
        ok(f"37+ {reg}: e supera di molto l'1% che il record 50 le attribuisce",
           atteso > 20.0)
    ok("39 la P non corretta di NGC e' il +5.00 pp del record 50",
       abs((R["NGC"]["P_corr"] + R["NGC"]["P_curv"]) - 5.0073) < 0.001)

    # --- l'appaiamento -------------------------------------------------------
    III = nv["iii_the_pairing_earned_the_twenty_three_extra_hours"]
    ok("40 il guadagno sulla curtosi supera 200",
       III["kurtosis_NGC"]["gain"] > 200)
    ok("41 e senza appaiamento la variazione sarebbe sotto 1 sigma",
       abs(R["NGC"]["kurt_d"]) / R["NGC"]["kurt_sem_nonapp"] < 1.0)

    # --- i bias diagnostici stanno sotto meta' SEM ---------------------------
    for reg in ("NGC", "SGC"):
        sem = SD_NPAT[reg] / np.sqrt(2000)
        b = R[reg]["voxel_fra_soglie"] / 2000
        ok(f"42+ {reg}: i voxel fra le due soglie stanno sotto meta' SEM",
           b <= BIAS_MAX_IN_SEM * sem)

    ok("44 emenda i record 50 e 54", rec["rules"]["amends_records"] == [50, 54])
    ok("45 il record non afferma nulla su 4.3b",
       "asserts nothing about 4.3b" in rec["rules"]["what_this_does_not_do"])
    ok("46 e dichiara che l'ordine e' imposto da un rifiuto, non dalla cura",
       "enforced by a refusal" in rec["reason"])
    ok("47 i cancelli importati sono quelli del 50",
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
    p_a.add_argument("--attesi", type=int, default=57)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend60.py — appende il record 60: la Fase 5 e' chiusa.

Che cosa registra: i denominatori del budget dichiarati termine per termine (5.1), le quattro
correzioni al Paper 1 nate dalla Fase 4 e da 5.1 (P1-10, P1-11, P1-12, P1-13), la decisione su
5.6 (nessuna nota su M26, la nota va sul Paper 1), la ricognizione su M26 pubblicato senza
erratum, la riclassificazione delle smentite (12 in A, 1 in A-bis, 5 in B) e la collocazione dei
tre residui di Fase 4, con il terzo RINVIATO alla Fase 6 con il suo motivo.

I cancelli sull'append si importano da paper2_append_amend50, come per il record 59.

Uso:
    python paper2_append_amend60.py selftest
    python paper2_append_amend60.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 59 --dry-run
"""

import argparse
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

ITEM = "5.1-5.6/fase_5_chiusa_denominatori_dichiarati_e_quattro_correzioni_al_paper_1"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"
CRLF = chr(13).encode() + chr(10).encode()

# Basi dei bersagli del cancello, n = 2000. Da qui ogni percentuale di questo record.
BASI = {"NGC": {"N_mock": 35436.686, "N_desi": 28256.0},
        "SGC": {"N_mock": 18712.9675, "N_desi": 15122.0}}

# Termini del budget che questo record quota, con la loro forma dichiarata.
TERMINI = {
    "fkp_reweighting_NGC": {"valore": 89.15, "sem": 1.25, "regione": "NGC", "forma": "misura"},
    "fkp_reweighting_SGC": {"valore": 56.49, "sem": 0.83, "regione": "SGC", "forma": "misura"},
    "nfw_satellites_NGC": {"valore": 56.5, "sem": 23.5, "regione": "NGC", "forma": "limite"},
    "snapshot_lightcone_NGC": {"valore": 53.0 * 0.25, "sem": 112.0 * 0.25, "regione": "NGC",
                               "forma": "limite"},
    "box_tiling_mean_NGC": {"valore": 12.8, "sem": 20.1, "regione": "NGC", "forma": "limite"},
    "unit_weight_rebuild_NGC": {"valore": 309.0, "sem": None, "regione": "NGC",
                                "forma": "variante deterministica"},
}
# Le smentite riclassificate: conteggi dei tre gruppi.
SMENTITE = {"A": 12, "A_bis": 1, "B": 5, "record_letti": 59, "con_predizione_e_riscontro": 26}


def deficit(regione):
    b = BASI[regione]
    return b["N_mock"] - b["N_desi"]


def pct_deficit(valore, regione):
    return 100.0 * valore / deficit(regione)


def limite_3sigma(valore, sem):
    """La forma dichiarata in 5.1 R3 per un risultato compatibile con zero: |D| + 3 sigma."""
    return abs(valore) + 3.0 * sem


def quota(nome):
    """(valore quotato, % del deficit) nella forma dichiarata per quel termine."""
    t = TERMINI[nome]
    v = limite_3sigma(t["valore"], t["sem"]) if t["forma"] == "limite" else t["valore"]
    return v, pct_deficit(v, t["regione"])


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    q = {k: quota(k) for k in TERMINI}
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "phase_5_closed_every_denominator_declared_and_four_corrections_to_paper_1",
        "json_path": ("papers/paper2/paper2_budget_5_1.md; papers/paper2/paper2_5_4_practice.md; "
                      "papers/paper2/paper2_5_5_smentite.md; papers/paper2/paper2_residui_fase4.md; "
                      "papers/paper2/modifiche_paper1.md; prereg §6 (error budget); "
                      "records 50, 54, 57, 58, 59"),
        "old_value": (
            "Checklist item 5.1 asked for 'conservative denominators everywhere' without saying "
            "what the denominator of each term is; 5.2 asked for two rows of Table 8; 5.4 sent "
            "six practices to section 6.2 of M26; 5.5 listed two falsified predictions; 5.6 left "
            "open whether 4.3b required a correction note. Phase 4 closed with three residues "
            "unplaced: the degraded boundary, n_s and sigma_8 on the response function, and the "
            "unexplained cosmological variance."
        ),
        "new_value": {
            "i_the_word_conservative_is_withdrawn_from_the_budget": {
                "why": "For a limit a wider sigma is prudent; for a measurement quadrature in "
                       "place of the paired SEM understates the effect and is not prudent at "
                       "all. The word says opposite things in the two cases, so each term now "
                       "declares three things instead: the statistical denominator, the base of "
                       "the percentage, and the form.",
                "R1_denominators": "Paired SEM for a shift of the ensemble mean (the data side "
                    "is deterministic, prereg §5.1); per-realisation dispersion for a statement "
                    "about DESI against one mock (N=1); none for a deterministic data-side "
                    "variant, for a band of choices and for a rank.",
                "R2_percentage_base": "Always explicit: per cent of D or per cent of N_H1, "
                    "never a bare per cent. D = 7180.686 (NGC) and 3590.9675 (SGC) from the "
                    "gate targets at n=2000.",
                "R3_form": "A measurement is written D +/- sigma. A result with |D|/sigma < 3 is "
                    "written as a limit |D| + 3 sigma, with the measurement beside it and never "
                    "the central value alone. A known function is subtracted. A band of choices "
                    "is an interval and is NOT summed in quadrature with anything.",
                "R3_bis_declared_exception": "A term measured over a sample of GEOMETRIES and "
                    "transferred to a new geometry carries the dispersion across the geometries "
                    "tried, not the SEM and not |D| + 3 sigma: the SEM would say how well the "
                    "mean of the shapes tried is known, not how well that mean predicts the "
                    "next one. It applies today to the mask-residual term only.",
                "R5_two_columns": "Column A shifts the mean or the data side; column B touches "
                    "the per-realisation dispersion and therefore only the significance. The "
                    "tiling variance factor 1.44 is column B and must not be quoted beside the "
                    "column A terms."
            },
            "ii_the_terms_quoted_in_the_declared_form": {
                "fkp_reweighting": {
                    "NGC_generators": q["fkp_reweighting_NGC"][0],
                    "NGC_pct_of_D": q["fkp_reweighting_NGC"][1],
                    "SGC_generators": q["fkp_reweighting_SGC"][0],
                    "SGC_pct_of_D": q["fkp_reweighting_SGC"][1],
                    "form": "measurement, reported and NOT subtracted: Phase 4 showed v2 does "
                            "not fix the pathology it was meant to fix, so the reference "
                            "ensemble stays v1 - the one in M26, in Paper 1 and in the freeze."},
                "nfw_satellites_NGC": {
                    "measurement": "-56.5 +/- 23.5 over 40 pairs (Paper 1 section 7.1), 2.4 sigma",
                    "limit_generators": q["nfw_satellites_NGC"][0],
                    "pct_of_D": q["nfw_satellites_NGC"][1],
                    "form": "limit with the measurement beside it"},
                "snapshot_lightcone_NGC": {
                    "measurement": "-53 +/- 112 per unit z (M26 section 7 vi), dz ~ 0.25",
                    "limit_generators": q["snapshot_lightcone_NGC"][0],
                    "pct_of_D": q["snapshot_lightcone_NGC"][1],
                    "form": "limit: consistent with zero, so the central value is not the "
                            "expected effect. Paper 1 Table 8 quoted ~13 generators (0.2 per "
                            "cent), which is the central value of a null and understates the "
                            "term by a factor seven."},
                "box_tiling_mean_NGC": {
                    "measurement": "-12.8 +/- 20.1 over 100 mocks (results/revision/"
                                   "rev1_r11_pilot.json; M26 section 5.6)",
                    "limit_generators": q["box_tiling_mean_NGC"][0],
                    "pct_of_D": q["box_tiling_mean_NGC"][1],
                    "form": "limit. The sigma was already in the checklist at rev. 3.18; the "
                            "0.037 per cent of prereg (d) is per cent of the ensemble MEAN, "
                            "which against the deficit is 0.178 per cent."},
                "unit_weight_rebuild_NGC": {
                    "shift_of_N_desi": TERMINI["unit_weight_rebuild_NGC"]["valore"],
                    "pct_of_N_H1": 100.0 * 309.0 / BASI["NGC"]["N_desi"],
                    "pct_of_D": q["unit_weight_rebuild_NGC"][1],
                    "form": "deterministic data-side variant, no denominator. This is the term "
                            "whose base was wrong in both manuscripts: quoted as ~1 per cent, "
                            "which is per cent of N, in a column where every other row is per "
                            "cent of D, where it is 4.3 per cent."},
                "mask_residual": {
                    "measurement": "-14.3 per cent +/- 11.9 per cent of the contrast, "
                                   "recomputed from results/paper1/n8_masks_128.jsonl and "
                                   "n8b_masks_128_B.jsonl",
                    "form": "band of dispersion under R3-bis, that is +/- 2.4 percentage points "
                            "on the fiducial 20.3. The mean compression is declared as a "
                            "DIRECTION and not subtracted: at 1.2 sigma a subtraction is what "
                            "R3 forbids, it would move a central value that sits in the "
                            "abstract, in the freeze and in M26, and it would use as settled "
                            "the very transfer the text calls uncertain."}
            },
            "iii_four_corrections_to_paper_1_all_of_attribution_or_of_base": {
                "P1_10": "Section 8.1, Table 9 caption, section 10 (vii): the k=1 maximum was "
                    "attributed to the FKP-contaminated denominator voxels. Record 59 shows the "
                    "prominence does not fall under weighting, and section 7.2 already says "
                    "those voxels carry essentially no cycles. The maximum is geometric. Every "
                    "measurement stands; the cause does not.",
                "P1_11": "Section 7.2 and Table 12 caption: the ~4000 extreme-delta voxels and "
                    "the isolated delta spikes were attributed to the unit-weight voxelisation. "
                    "Weighting the mocks removes 27 of 4048 (0.7 per cent) and moves the median "
                    "max delta the WRONG way, from 27.80 to 28.47 times DESI, with the rank "
                    "staying 0/2000.",
                "P1_12": "Section 8.2: the differential mask test runs over four smoothing "
                    "scales and 240 configurations, but only 58 qualify under w_bar >= 0.99 and "
                    "all 58 sit at sigma_px = 0.3204, where the true contrast is 23.9 per cent "
                    "and not the 36.9 of all 240. Three numbers and one label are corrected; the "
                    "collapse of the shape dependence - the result of the test - stands.",
                "P1_13": "Table 8, four rows: the AP row is filled in form (B), the "
                    "falsification without the unpublished Phase 3 amplitudes; tiling moves "
                    "from unquantified to bounded; snapshot from a central value to a limit; and "
                    "the unit-weight rebuild acquires both bases, which makes it the first row "
                    "of that table above 2 per cent - so 'sub-dominant' is no longer the right "
                    "word for it.",
                "what_none_of_them_touches": "The deficit, its rank and the persistence "
                    "decomposition. The 20.3 per cent, the rank 1/2001 and the split are those "
                    "of the manuscript. What changes is the width of one propagated systematic "
                    "(P1-12), which stays inside the declared band."
            },
            "iv_5_6_the_note_is_needed_and_it_goes_on_paper_1_not_on_M26": {
                "criterion": "A note is needed if a Phase 4 outcome makes a manuscript statement "
                    "false: a number outside its uncertainty, a sign, a causal attribution. What "
                    "Phase 4 adds without contradicting goes in Paper 2.",
                "M26": "No note. M26 does not report D(k) level by level and does not attribute "
                    "the k=1 maximum; its section 4.1 attributes the delta spikes to near-zero "
                    "coverage, not to the weights, which is the reading Phase 4 confirms. The "
                    "Table 1 row -78.0 +/- 8.0 against the full ensemble -89.15 +/- 1.25 sits "
                    "1.4 sigma away and is 1.24 per cent of the deficit, inside the declared 1-2 "
                    "per cent.",
                "single_and_never_piecemeal": "The note is P1-10 of modifiche_paper1.md, applied "
                    "with the others after Phase 6."
            },
            "v_M26_is_published_four_findings_and_no_erratum": {
                "decision": "No erratum. Not because nothing in M26 is false - three of the four "
                    "findings below are - but because none of them changes a conclusion: the "
                    "deficit, the rank, the exclusion of w0CDM and the significance all stand. "
                    "The point reopens only if a finding touches a conclusion.",
                "findings": {
                    "the_309": "Section 5.3 and Table 1 bound the systematic at '1-2 per cent of "
                        "the deficit'. The unit-weight rebuild of DESI moves N by +309, which is "
                        "1.09 per cent of N and 4.30 per cent of D. The two percentages agree to "
                        "the second figure on different bases, and the sentence merged them.",
                    "the_snapshot": "Section 2 quotes ~13 generators, 0.2 per cent of the "
                        "deficit, which is the central value of -53 +/- 112 per unit z. Section 7 "
                        "(vi) does say 'consistent with zero'; section 2 quotes only the 0.2.",
                    "a_wrong_cross_reference": "Section 2 says the snapshot mismatch is "
                        "quantified in 'Section 5.4'; section 5.4 does not discuss it, the "
                        "measurement is in section 7 (vi).",
                    "the_box_cox": "Section 4.1 calls the change between 20.3 and 17.6 per cent "
                        "'a 14 per cent change'; it is 13.3 (13.4 on the unrounded values). "
                        "Marginal on its own."
                },
                "what_paper_1_does_instead": "P1-13 corrects the +309 base and the snapshot row "
                    "in Table 8, so a reader of the series finds the right numbers."
            },
            "vi_the_falsified_predictions_are_not_two": {
                "counts": SMENTITE,
                "group_A": "Twelve declared predictions with an outcome, eleven fallen on the "
                    "data and one standing (term (c) does not depend on the point, record 39 - "
                    "kept in the section because a section of failures only is as selected as a "
                    "section of successes only). Two were not in the checklist list at all: the "
                    "clipping predicted to follow the ANISOTROPIC residual, falsified without "
                    "running anything from records already on disk, and the two distinct "
                    "predictions of record 16, which fell in different records.",
                "group_A_bis": "One: the intersection-mask rule of record 24, whose outcome is "
                    "PARTIAL at 0.4962 and 0.4741 against a 2/3 threshold. Below the threshold, "
                    "so not falsified; not enough for a confirmation either. It has a group of "
                    "its own because the data authorise neither verdict and the rule was "
                    "declared in advance with its threshold - the outcome that does not resolve "
                    "is the easiest one to make disappear into either full group.",
                "group_B": "Five thresholds or characterisations badly posed, where the "
                    "conclusion does not change: the P1 of D3 withdrawn AS A FALSIFICATION "
                    "(0.22 sigma from its threshold, standard error 0.0224, and record 43 had "
                    "celebrated reproducing a threshold crossing without power - raised by the "
                    "referee, not by us); the four of six rules withdrawn by record 50 before "
                    "any measurement; the 'five independent falsifications' that are four; the "
                    "admissibility tolerance of record 13; and the 'constant offset' reading.",
                "the_33_excluded_records_were_checked_one_by_one": "Eleven hold the DECLARING "
                    "half of predictions whose outcome is already in group A (15 -> 19, 16 -> 37 "
                    "and 38, 30 -> 31, 51 -> 59); the rest declare design, definitions or "
                    "rectifications with no falsification clause. Record 32 says it itself: 'no "
                    "threshold is declared on the outcome, because the rule is not a test: it is "
                    "a definition'. No falsification was missed."
            },
            "vii_the_practices_change_destination_and_the_second_one_changes_argument": {
                "destination": "Section 6.2 of M26 is published and closed with three practices, "
                    "so the six of item 5.4 become a SECTION OF PAPER 2 citing and extending it. "
                    "On this point M26 says nothing false: it says less.",
                "practice_2_rewritten": "The original argument was that weighting the mocks "
                    "removes the delta spikes. Phase 4 falsified exactly that - it is the "
                    "outcome behind P1-11 - so the practice now rests on like-for-like pairing "
                    "and on the measured 1-2 per cent, and it must SAY that the expected effect "
                    "is absent. A practice sold as 'it removes the spikes' would be false, and "
                    "whoever followed it for that reason would find the opposite.",
                "practice_6_the_number_exists": "The first draft of this closure said the count "
                    "of positions falling outside the embedding cube did not exist and needed a "
                    "run. Wrong: d5c_n_clipped appears 18195 times in the Phase 3 registers. The "
                    "fiducial has it - mean 1.00 per realisation in NGC and 0.345 in SGC, "
                    "maximum 13 over all records, one or two galaxies out of some 5e5. "
                    "clipped_rand is 0 in all fourteen Phase 2 records, and the real-space run "
                    "has 200 zeros of 200 in both hemispheres: the randoms never leave, only the "
                    "galaxies do, and it is the RSD that pushes them out.",
                "practice_7_is_new": "Every run flag must enter the COMPUTATION and not only the "
                    "record: --real-space entered the record and the resume key but not the "
                    "calculation, and 2400 cells came out integer-identical to the "
                    "redshift-space run (ledger line 35). It is a pipeline defect, not a "
                    "falsified prediction, so it belongs with the practices."
            },
            "viii_the_three_residues_of_phase_4": {
                "residue_1_degraded_boundary": "Placed. In Paper 1 it IS P1-7, applied. In Paper "
                    "2 it goes in the discussion as a CANDIDATE for the geometric mechanism of "
                    "P1-10, never as the explanation: no measurement links the 52 fixed-value "
                    "void voxels to the D(k) excursion, and three gate formulations on this "
                    "object fell in a row (item 4.2d). Its sign also closes the caveat left open "
                    "under 5.6: a degraded boundary DILUTES the deficit, so it reinforces M26's "
                    "'not a boundary-skin artefact' rather than undermining it.",
                "residue_2_n_s_and_sigma_8": "Placed in the positive core, the response function "
                    "(figure F7), not among the systematics. n_s leads at 7.4 and 8.4 sigma "
                    "above the declared 0.25 and the ordering n_s, h, Omega_m, Omega_b is the "
                    "shape signature Prop. 1 predicts. Three limits are to be written beside it: "
                    "the two hemispheres are NOT independent (same suite of 2000 simulations, so "
                    "their agreement is expected by construction and is not a confirmation); "
                    "sigma_8 is NOT zero (18.97 and 24.84 per cent - the amplitude invariance is "
                    "a theorem about the functional, not an observation about the data); and a "
                    "partial correlation orders sensitivities, it does not constrain n_s.",
                "residue_3_unexplained_variance_DEFERRED": {
                    "what": "The 62.7 per cent (NGC) and 60.3 per cent (SGC) of cosmological "
                        "variance the seven parameters do not explain (D5), which should connect "
                        "to the 1710-generator beyond-two-point residual of Paper 1.",
                    "why_it_is_not_placed": "D6 is open, with its reserve already declared: the "
                        "model sequence does NOT converge (the 48.3 per cent is an upper bound, "
                        "not a measurement) and the provenance of pk_matrix is not established, "
                        "so tests B and C are not interpretable. Without D6 the two opposite "
                        "readings cannot be separated: if P(k) closes the gap then N_H1 IS a "
                        "two-point statistic and the seven parameters failed only because the "
                        "parameters -> P(k) map is not linear; if it does not, the unexplained "
                        "part is beyond two-point.",
                    "where_it_goes": "DEFERRED TO PHASE 6 as a checklist item, the same way "
                        "Phase 2 deferred what it could not close. It does not enter the 5.1 "
                        "budget as a term - it is neither a shift of the mean (column A) nor a "
                        "factor on the dispersion (column B), but unattributed variance, a third "
                        "thing - and it does not enter the discussion as a result.",
                    "the_ceiling_not_to_get_wrong_twice": "For predictors measured on the same "
                        "realisation the ceiling is not 0.698 but 0.832."
                }
            },
            "ix_what_this_record_does_not_do": {
                "it_does_not_confirm_the_anomaly": "Phase 5 declared denominators and corrected "
                    "bases and attributions. Not one of its outcomes is evidence for the "
                    "physical claim, and nothing here should be read as such.",
                "it_does_not_apply_the_paper_1_corrections": "P1-10 to P1-13 are written in "
                    "modifiche_paper1.md and applied to the manuscript after Phase 6, together "
                    "with P1-9, which rewrites a figure in the same paragraph as P1-11 and a row "
                    "of the same table as P1-13.",
                "open_after_this_record": "D6 and residue 3; the note 1 of the budget (the AP "
                    "percentages need <N>_mock at k=1 read from the unitary branch, not "
                    "reconstructed from the rounded 25.46 per cent); the source files of three "
                    "budget values; n_clip_inmask, which the D5c probe computes and the ledger "
                    "does not store; and item 4.2d, which still needs redefining."
            }
        },
        "reason": (
            "Phase 5 replaces 'conservative denominators everywhere' with a declaration per term, "
            "and the declaration found what the word had hidden: two published percentages on the "
            "wrong base (the +309 and the snapshot row), one systematic whose contrast belonged to "
            "another subset (the 36.9 against the 23.9 of the qualifying regime), and two causal "
            "attributions that Phase 4 had already falsified. Four corrections to Paper 1 follow, "
            "none of which touches the deficit, its rank or the persistence decomposition. The "
            "falsified predictions turn out to be twelve and not two, with one outcome that "
            "resolves nothing and keeps a group of its own. Two of the three Phase 4 residues are "
            "placed; the third is deferred to Phase 6 with its reason, because D6 does not "
            "converge and its input provenance is not established."
        ),
        "evidence": (
            "Budget and forms: papers/paper2/paper2_budget_5_1.md, rules R1, R2, R3, R3-bis, R5. "
            "Mask residual recomputed independently of the published report from "
            "results/paper1/n8_masks_128.jsonl and n8b_masks_128_B.jsonl, reproducing "
            "n8b_report_128.json to the sixth decimal: 240 configurations, 58 in the regime, "
            "differential -0.034216, standard deviation 0.028497 - and the 2.8 is the dispersion "
            "across the 58 geometries (bd99.std(ddof=1) in paper1_rev_n8b_differential.py), not a "
            "SEM. Provenance of that code verified: git status clean, and the only change after "
            "the 26 July run is 88f6bad of 28 August, which paraphrases referee quotations in a "
            "docstring and does not touch the logic. Clipping counts: paper2_estrai.py clipped "
            "over the Phase 3 registers, 8299 records carrying a count. Predictions: "
            "paper2_estrai.py predizioni --completo and esclusi over all 59 ledger records. "
            "Paper 1 corrections: papers/paper2/modifiche_paper1.md, entries P1-10 to P1-13, each "
            "applied by its own patcher with a verify on the re-read file."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-60-fase-5-chiusa",
            "amends_records": [50, 54, 58, 59],
            "companion_document": ("papers/paper2/paper2_budget_5_1.md; "
                                   "papers/paper2/paper2_5_4_practice.md; "
                                   "papers/paper2/paper2_5_5_smentite.md; "
                                   "papers/paper2/paper2_residui_fase4.md; "
                                   "papers/paper2/modifiche_paper1.md; paper2_stato.md; "
                                   "checklist items 5.1-5.6"),
            "a_declared_denominator_is_not_a_conservative_one":
                "Every term of the budget now carries its statistical denominator, the base of "
                "its percentage and its form. Where the form is a limit the quoted figure is "
                "|D| + 3 sigma; where it is a measurement the paired SEM is quoted and the "
                "quadrature figure, when the paired one is unavailable, is labelled as the wrong "
                "denominator.",
            "what_this_does_not_do":
                "It does not close D6 or place residue 3, which go to Phase 6. It does not apply "
                "the Paper 1 corrections to the manuscript. It does not confirm the anomaly."
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
    # il record 59 deve esserci: e' l'esito di 4.3b su cui poggiano P1-10 e la decisione di 5.6
    if not any("prominenza_su_v2" in str(r.get("item", "")) for r in recs):
        print("RIFIUTO: il record 59 non e' nel ledger. P1-10 e la decisione di 5.6 "
              "poggiano sull'esito di 4.3b, che deve essere registrato prima.")
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
    print(f"ledger    : {os.path.abspath(args.ledger)}")
    print(f"record    : {n} -> {n + 1}")
    print(f"fine riga : {'CRLF' if eol == CRLF else 'LF'} (maggioranza: CRLF {crlf}, LF soli {lf})")
    print(f"ancore    : file {ref_file_sha[:12]}…  self {str(ref_self_sha)[:12]}…  concordi")
    print(f"item      : {rec['item']}")
    print(f"byte      : {len(linea)}")
    print("budget    : misura ripesatura FKP NGC %8.2f gen  %5.2f %% di D"
          % quota("fkp_reweighting_NGC"))
    for nome, etich in (("nfw_satellites_NGC", "limite NFW NGC       "),
                        ("snapshot_lightcone_NGC", "limite snapshot NGC  "),
                        ("box_tiling_mean_NGC", "limite tiling NGC    "),
                        ("unit_weight_rebuild_NGC", "variante +309 unitari")):
        v, p = quota(nome)
        print("            %s %8.2f gen  %5.2f %% di D" % (etich, v, p))
    print("smentite  : %d in A, %d in A-bis, %d in B (su %d record, %d con predizione e riscontro)"
          % (SMENTITE["A"], SMENTITE["A_bis"], SMENTITE["B"],
             SMENTITE["record_letti"], SMENTITE["con_predizione_e_riscontro"]))
    print("residui   : 1 e 2 collocati, 3 RINVIATO alla Fase 6 (D6 non converge)")

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
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="amend60_")
    led = os.path.join(base, "ledger.jsonl")
    ref = os.path.join(base, "reference.json")
    with open(ref, "w", encoding="utf-8", newline="") as fh:
        json.dump({"_self_sha256": "s" * 64}, fh)
    ref_sha = sha256_file(ref)

    def scrivi_ledger(n, con59=True):
        with open(led, "wb") as fh:
            for i in range(n):
                r = {"item": f"x{i}", "type": "protocol"}
                if con59 and i == n - 1:
                    r["item"] = "4.3b/prominenza_su_v2_sei_regole_su_sei_falliscono"
                if i == n - 1:
                    r["reference_file_sha256"] = ref_sha
                    r["reference_self_sha256"] = "s" * 64
                fh.write(json.dumps(r).encode("utf-8") + CRLF)

    class A:
        pass

    def a(attesi=59, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    # --- il cancello sul record 59 -------------------------------------------
    scrivi_ledger(59, con59=False)
    ok("1 senza il record 59 l'append e' RIFIUTATO", cmd_append(a(dry=True)) == 2)
    scrivi_ledger(59, con59=True)
    raw_prima = open(led, "rb").read()
    ok("2 col record 59 presente, il dry-run passa", cmd_append(a(dry=True)) == 0)
    ok("3 e non scrive", open(led, "rb").read() == raw_prima)
    ok("4 conteggio sbagliato: rifiuto", cmd_append(a(attesi=58)) == 2)
    ok("5 reference inesistente: rifiuto", cmd_append(
        type("B", (), {"ledger": led, "reference": ref + ".no", "attesi": 59,
                       "dry_run": True, "backup": None})()) == 2)
    ok("6 append: esito 0", cmd_append(a()) == 0)
    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("7 il conteggio cambia: 59 -> 60", len(recs2) == 60)
    ok("8 numbering_rule dice 60", "record 60." in recs2[-1]["numbering_rule"])
    ok("9 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 60)
    ok("10 i 59 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("11 secondo append rifiutato per item duplicato", cmd_append(a(attesi=60)) == 2)

    rec = recs2[-1]
    nv = rec["new_value"]

    # --- le basi e le forme si RICALCOLANO ------------------------------------
    ok("12 D di NGC e' 7180.686", abs(deficit("NGC") - 7180.686) < 1e-9)
    ok("13 D di SGC e' 3590.9675", abs(deficit("SGC") - 3590.9675) < 1e-9)
    II = nv["ii_the_terms_quoted_in_the_declared_form"]
    ok("14 la ripesatura e' quotata come MISURA, non come limite",
       abs(II["fkp_reweighting"]["NGC_generators"] - 89.15) < 1e-9)
    ok("15 e vale l'1.24 % di D", abs(II["fkp_reweighting"]["NGC_pct_of_D"] - 1.2415) < 5e-3)
    ok("16 il NFW e' quotato come LIMITE |D|+3sigma = 127",
       abs(II["nfw_satellites_NGC"]["limit_generators"] - 127.0) < 1e-9)
    ok("17 lo snapshot come limite su dz=0.25: 97.25",
       abs(II["snapshot_lightcone_NGC"]["limit_generators"] - 97.25) < 1e-9)
    ok("18 il tiling come limite: 73.1",
       abs(II["box_tiling_mean_NGC"]["limit_generators"] - 73.1) < 1e-9)
    ok("19 il +309 porta ENTRAMBE le basi, e quella su D e' la maggiore",
       abs(II["unit_weight_rebuild_NGC"]["pct_of_N_H1"] - 1.0936) < 1e-3
       and abs(II["unit_weight_rebuild_NGC"]["pct_of_D"] - 4.3031) < 1e-3
       and II["unit_weight_rebuild_NGC"]["pct_of_D"] > II["unit_weight_rebuild_NGC"]["pct_of_N_H1"])
    ok("20 il +309 e' l'unico termine sopra il 2 % di D",
       sum(1 for k in TERMINI if quota(k)[1] > 2.0) == 1)
    ok("21 un limite e' sempre >= della sua misura",
       all(quota(k)[0] >= abs(TERMINI[k]["valore"]) for k in TERMINI if TERMINI[k]["forma"] == "limite"))

    # --- cio' che il record dichiara ------------------------------------------
    ok("22 'conservativo' e' ritirato con la sua ragione",
       "opposite things" in nv["i_the_word_conservative_is_withdrawn_from_the_budget"]["why"])
    ok("23 R3-bis e' dichiarata come eccezione, e per la sola riga 9",
       "mask-residual term only" in
       nv["i_the_word_conservative_is_withdrawn_from_the_budget"]["R3_bis_declared_exception"])
    ok("24 la compressione della maschera NON viene sottratta",
       "not subtracted" in II["mask_residual"]["form"])
    III = nv["iii_four_corrections_to_paper_1_all_of_attribution_or_of_base"]
    ok("25 sono quattro voci del Paper 1", all(k in III for k in ("P1_10", "P1_11", "P1_12", "P1_13")))
    ok("26 e nessuna tocca il deficit, il rango o la scomposizione",
       "rank" in III["what_none_of_them_touches"])
    ok("27 5.6: nessuna nota su M26", nv["iv_5_6_the_note_is_needed_and_it_goes_on_paper_1_not_on_M26"]["M26"].startswith("No note"))
    V = nv["v_M26_is_published_four_findings_and_no_erratum"]
    ok("28 M26: nessun erratum, e il motivo NON e' che nulla e' falso",
       V["decision"].startswith("No erratum") and "three of the four" in V["decision"])
    ok("29 e le quattro voci sono nominate", len(V["findings"]) == 4)
    VI = nv["vi_the_falsified_predictions_are_not_two"]
    ok("30 i conteggi delle smentite sono quelli dichiarati",
       VI["counts"]["A"] == 12 and VI["counts"]["A_bis"] == 1 and VI["counts"]["B"] == 5)
    ok("31 i 33 esclusi sono stati controllati uno per uno",
       "DECLARING" in VI["the_33_excluded_records_were_checked_one_by_one"]
       and "No falsification was missed" in VI["the_33_excluded_records_were_checked_one_by_one"])
    VII = nv["vii_the_practices_change_destination_and_the_second_one_changes_argument"]
    ok("32 la practice 2 dichiara assente l'effetto atteso",
       "expected effect is absent" in VII["practice_2_rewritten"])
    ok("33 la practice 6 corregge una conclusione sbagliata di questa stessa chiusura",
       "Wrong:" in VII["practice_6_the_number_exists"])
    VIII = nv["viii_the_three_residues_of_phase_4"]
    ok("34 il residuo 1 e' un CANDIDATO, non la spiegazione",
       "never as the explanation" in VIII["residue_1_degraded_boundary"])
    ok("35 il residuo 2 dichiara che sigma_8 NON e' zero",
       "sigma_8 is NOT zero" in VIII["residue_2_n_s_and_sigma_8"])
    R3 = VIII["residue_3_unexplained_variance_DEFERRED"]
    ok("36 il residuo 3 e' RINVIATO alla Fase 6, con il motivo",
       "DEFERRED TO PHASE 6" in R3["where_it_goes"] and "does NOT converge" in R3["why_it_is_not_placed"])
    ok("37 e non entra nel budget ne' nella discussione",
       "neither a shift of the mean" in R3["where_it_goes"])
    ok("38 il tetto giusto e' 0.832, non 0.698", "0.832" in R3["the_ceiling_not_to_get_wrong_twice"])
    IX = nv["ix_what_this_record_does_not_do"]
    ok("39 il record dichiara che l'anomalia NON e' confermata",
       "not one of its outcomes is evidence" in IX["it_does_not_confirm_the_anomaly"].lower()
       or "Not one of its outcomes is evidence" in IX["it_does_not_confirm_the_anomaly"])
    ok("40 e che le correzioni al Paper 1 non sono applicate",
       "after Phase 6" in IX["it_does_not_apply_the_paper_1_corrections"])
    ok("41 elenca cio' che resta aperto, D6 compreso", "D6" in IX["open_after_this_record"])
    ok("42 emenda 50, 54, 58 e 59", rec["rules"]["amends_records"] == [50, 54, 58, 59])
    ok("43 i cancelli importati sono quelli del 50",
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
    p_a.add_argument("--attesi", type=int, default=59)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

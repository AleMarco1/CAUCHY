#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend57.py — appende il record 57: 4.2b-5 misurata, in entrambi
gli emisferi, ed e' FALLIMENTO.

I cancelli sull'append si importano da paper2_append_amend50.

Uso:
    python paper2_append_amend57.py selftest
    python paper2_append_amend57.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 56 --dry-run
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

ITEM = "4.2b-5/box_cox_misurata_due_emisferi"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"
CRLF = chr(13).encode() + chr(10).encode()

FRAZ_SUCCESSO, FRAZ_FALLIMENTO = 0.25, 0.75
SIGMA_MAX_INVALIDA = 15.0
DEFICIT = {"NGC": 7181.5, "SGC": 3590.97}

# Misure del 9 settembre 2026, src/paper2_boxcox_v2.py (selftest 31/31).
S = {
    "NGC": {"v1": -183.32, "sem_v1": 11.124102898936275,
            "v2": -190.02, "sem_v2": 11.488076871438562,
            "d_appaiata": -6.70, "sem_d_appaiata": 6.14,
            "eps025_v1": 129.00, "eps05_v1": 124.52,
            "eps025_v2": 125.62, "eps05_v2": 122.10},
    "SGC": {"v1": -109.32, "sem_v1": 9.412516200490163,
            "v2": -109.62, "sem_v2": 9.236833541725813,
            "d_appaiata": -0.30, "sem_d_appaiata": 5.13,
            "eps025_v1": 144.00, "eps05_v1": 136.52,
            "eps025_v2": 142.94, "eps05_v2": 140.02},
}


def soglie(s_v1):
    a = abs(float(s_v1))
    return round(a * FRAZ_SUCCESSO, 2), round(a * FRAZ_FALLIMENTO, 2)


def esito(s_v2, sem_v2, succ, fall):
    if sem_v2 > SIGMA_MAX_INVALIDA:
        return "NON DECIDE (invalidata)"
    a = abs(float(s_v2))
    if a < succ:
        return "SUCCESSO"
    if a > fall:
        return "FALLIMENTO"
    return "NON DECIDE"


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    sN, fN = soglie(S["NGC"]["v1"])
    sS, fS = soglie(S["SGC"]["v1"])
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "rule_4_2b_5_is_measured_in_both_hemispheres_and_it_fails",
        "json_path": ("results/paper2/boxcox_{v1,v2}_{NGC,SGC}.json; "
                      "src/paper2_boxcox_v2.py; src/rev1_r14_monotone.py; "
                      "results/paper2/ensemble_v2_{NGC,SGC}.jsonl; record 50"),
        "old_value": (
            "Record 50 replaced the withdrawn Box-Cox prediction with s = <N_H1(eps=1) - "
            "N_H1(eps=0)> paired over the same 50 mocks, quoting v1 NGC only: s = -183.32 +- "
            "11.124102898936275, threshold 45.8 for success and 137.5 for failure, the rule not "
            "deciding if sigma(s^v2) exceeds 15. For SGC no s^v1 existed in any register, so the "
            "rule covered one hemisphere. And record 50 section viii lists the Box-Cox pass inside "
            "the output specification of 4.2a, which the 4.2a runner does not produce: the item "
            "was declared and had no producer."
        ),
        "new_value": {
            "i_the_pass_exists_and_reuses_the_v1_implementation": {
                "what_was_written": "src/paper2_boxcox_v2.py (selftest 31/31). It computes "
                    "nothing of its own: transform, field_from_delta and beta1_pers1 are imported "
                    "from rev1_r14_monotone, which produced the v1 numbers. beta1_pers1 calls "
                    "compute_tda_features(..., masked=True)[4], the same as the 4.2a runner, so "
                    "the numbers are comparable by construction.",
                "the_50_mocks_are_inherited_not_chosen": "rev1_r14_monotone.py:527 takes "
                    "sorted(glob('*.npy'))[:n_mocks], i.e. delta_0000..delta_0049. Record 50 says "
                    "'on the SAME 50 mocks as v1', so the pass inherits them; the selection is "
                    "deterministic even as the v2 cache grows.",
                "an_import_that_had_to_be_isolated": "rev1_r14_monotone parses its arguments AT "
                    "MODULE LEVEL: importing it makes its parser read the caller's command line, "
                    "fail to find --mode and kill the process. That file is not modified - it "
                    "belongs to Paper 1 and its results are deposited - so sys.argv is substituted "
                    "for the duration of the import alone and restored immediately. The three "
                    "functions used do not touch ARGS.",
                "gate_A_the_two_constructions_of_nu_coincide": "At eps=0, transform(delta,0) is "
                    "log(1 + clip(delta, -1+1e-3)), LITERALLY the first line of P1.build_nu. So "
                    "field_from_delta(delta, mask, 0) must equal P1.build_nu(delta, mask, "
                    "sigma_px) BIT FOR BIT. Verified on all four passes, both hemispheres, both "
                    "versions: identical.",
                "gate_B_eps_zero_against_a_number_already_deposited": "On the v2 branch, N_H1 at "
                    "eps=0 must reproduce the fkp.N_H1_k0 already written in "
                    "ensemble_v2_<REG>.jsonl for those 50 realisations. Same field, same TDA. "
                    "50 of 50 in both hemispheres, no exception. This is stronger than the v1 "
                    "provenance gate, which checks a property of the field: here a number already "
                    "on disk is compared."
            },
            "ii_s_v1_reproduced_exactly_in_NGC_and_measured_for_the_first_time_in_SGC": {
                "NGC": {"s": S["NGC"]["v1"], "sem_paired": S["NGC"]["sem_v1"],
                        "sem_unpaired": 48.25391345026128,
                        "pairing_gain": 4.337780213708332,
                        "discrepancy_against_record_50": 0.0,
                        "and_not_only_s": "The whole table is reproduced to the quoted digit: "
                            "<N_H1> at eps=0 is 35445.64, the eps=0.25 shift +129.00 +- 4.19, the "
                            "eps=0.5 shift +124.52 +- 7.08, and the unpaired SEM 48.25. Seven "
                            "numbers, all of them."},
                "SGC": {"s": S["SGC"]["v1"], "sem_paired": S["SGC"]["sem_v1"],
                        "sem_unpaired": 32.97219607920761,
                        "pairing_gain": 3.50301613053166,
                        "existed_nowhere_before": True},
                "why_NGC_first_and_alone": "The SGC branch has no published counterpart. "
                    "Reproducing NGC exactly is what covers it: the same code, the same path, one "
                    "side verified. The tool refuses to compute SGC if the NGC recomputation "
                    "misses record 50 by more than 3 generators. It missed it by ZERO. The same "
                    "structure covered the construction of n1_desi_nu_SGC.npy hours earlier, where "
                    "the NGC cache was reproduced bit for bit."
            },
            "iii_the_SGC_thresholds_are_derived_and_were_declared_BEFORE_v2": {
                "NGC": {"success_below": sN, "failure_above": fN,
                        "note": "45.83 and 137.49 are the record-50 values re-derived from "
                                "|s^v1|: 25% and 75%. Already declared, nothing new."},
                "SGC": {"success_below": sS, "failure_above": fS,
                        "note": "NEW. Derived from |s^v1| = 109.32 with the same two fractions. "
                                "No new fraction is introduced."},
                "the_order_was_enforced_by_the_tool_not_by_care": "The v2 branch REFUSES to run "
                    "without --soglia, and the v1 branch refuses to accept one: it derives the "
                    "threshold, it does not receive it. So the SGC number was written down and "
                    "passed back in before v2 ran. The file timestamps witness it: "
                    "boxcox_v1_SGC.json at 10:23:20Z, boxcox_v2_SGC.json at 12:15:46Z.",
                "and_this_is_not_the_ideal_sequence": "For NGC the threshold sat in record 50, "
                    "written before anything. For SGC it is derived and declared in the same "
                    "record that carries the outcome, because s^v1 SGC did not exist. That is "
                    "stated here rather than smoothed over; what makes it defensible is the "
                    "refusal built into the tool, not the intention of the person running it."
            },
            "iv_the_outcome_is_FAILURE_in_both_hemispheres": {
                "NGC": {"s_v2": S["NGC"]["v2"], "sem": S["NGC"]["sem_v2"],
                        "against_failure_threshold": fN,
                        "sigma_from_zero": round(S["NGC"]["v2"] / S["NGC"]["sem_v2"], 1),
                        "esito": esito(S["NGC"]["v2"], S["NGC"]["sem_v2"], sN, fN)},
                "SGC": {"s_v2": S["SGC"]["v2"], "sem": S["SGC"]["sem_v2"],
                        "against_failure_threshold": fS,
                        "sigma_from_zero": round(S["SGC"]["v2"] / S["SGC"]["sem_v2"], 1),
                        "esito": esito(S["SGC"]["v2"], S["SGC"]["sem_v2"], sS, fS)},
                "the_rule_decides_it_is_not_invalidated": "The invalidation condition declared in "
                    "record 50 - sigma(s^v2) above 15 generators - is not met: 11.49 in NGC and "
                    "9.24 in SGC. The rule decides, and it decides failure.",
                "what_this_means": "The part of the Box-Cox excursion that v2 could act on does "
                    "not move under reweighting. The original prediction was withdrawn because "
                    "84.3% of the excursion is data-side; what this adds is that the remaining "
                    "mock-side fraction is insensitive too.",
                "what_this_does_NOT_mean": "It is not a confirmation of the anomaly. 4.2b-5 asked "
                    "whether reweighting closes that channel: it does not. The other five rules "
                    "ask different questions and their outcomes depend on the 2000."
            },
            "v_the_shift_is_measured_with_the_PAIRED_denominator": {
                "NGC": {"delta_s": S["NGC"]["d_appaiata"],
                        "sem_paired": S["NGC"]["sem_d_appaiata"],
                        "sigma": round(S["NGC"]["d_appaiata"] / S["NGC"]["sem_d_appaiata"], 2),
                        "sem_in_quadrature": 15.99},
                "SGC": {"delta_s": S["SGC"]["d_appaiata"],
                        "sem_paired": S["SGC"]["sem_d_appaiata"],
                        "sigma": round(S["SGC"]["d_appaiata"] / S["SGC"]["sem_d_appaiata"], 2),
                        "sem_in_quadrature": 13.19},
                "the_pairing_is_2_6x_tighter_and_it_is_the_correct_one": "s^v1 and s^v2 are "
                    "computed on the SAME 50 realisations, so their difference is paired and the "
                    "quadrature sum is not the denominator - record 51: 'sigma appaiata, non in "
                    "quadratura; la non appaiata non e' conservativa, e' sbagliata'. With the "
                    "correct and TIGHTER error the shift is still 1.09 sigma in NGC and 0.06 in "
                    "SGC. The absence of an effect survives the more severe measurement, not only "
                    "the comfortable one.",
                "in_fractions_of_the_deficit": {
                    "NGC": [round(100 * S["NGC"]["v1"] / DEFICIT["NGC"], 2),
                            round(100 * S["NGC"]["v2"] / DEFICIT["NGC"], 2)],
                    "SGC": [round(100 * S["SGC"]["v1"] / DEFICIT["SGC"], 2),
                            round(100 * S["SGC"]["v2"] / DEFICIT["SGC"], 2)]}
            },
            "vi_the_non_monotonicity_in_eps_is_confirmed_independently_and_survives": {
                "record_50_reported_it_as_a_result_on_NGC_v1": "+129.00 +- 4.19 at eps=0.25, "
                    "+124.52 +- 7.08 at eps=0.5, then -183.32 +- 11.12 at eps=1: an excursion of "
                    "312 generators with a sign change, invisible if only the two endpoints are "
                    "read.",
                "SGC_v1": [S["SGC"]["eps025_v1"], S["SGC"]["eps05_v1"], S["SGC"]["v1"]],
                "NGC_v2": [S["NGC"]["eps025_v2"], S["NGC"]["eps05_v2"], S["NGC"]["v2"]],
                "SGC_v2": [S["SGC"]["eps025_v2"], S["SGC"]["eps05_v2"], S["SGC"]["v2"]],
                "two_independent_confirmations": "SGC is a statistically independent sample - the "
                    "two hemispheres correlate at r = 0.016 on paired realisations - and shows the "
                    "same shape with the sign change at the same point. And the shape SURVIVES the "
                    "reweighting, with the same values to two digits. It is a property of the "
                    "transform and of the field, not of the treatment nor of one hemisphere."
            }
        },
        "reason": (
            "Rule 4.2b-5 was declared in record 50 with a threshold for one hemisphere and no "
            "producer, while section viii of the same record lists the Box-Cox pass inside the "
            "output specification of 4.2a. Writing the pass closed both gaps and produced the "
            "first outcome of Phase 4. The rule fails in both hemispheres, and it fails by the "
            "widest possible margin: reweighting moves s by 1.09 sigma in NGC and 0.06 in SGC "
            "against a failure threshold set at three quarters of |s^v1|. The measurement is not "
            "marginal and the rule is not invalidated."
        ),
        "evidence": (
            "Runs of 9 Sep 2026, src/paper2_boxcox_v2.py (selftest 31/31), four passes: "
            "boxcox_v1_NGC.json 09:48:22Z, boxcox_v1_SGC.json 10:23:20Z, boxcox_v2_NGC.json "
            "11:36:10Z, boxcox_v2_SGC.json 12:15:46Z. Gate A (eps=0 identical to build_nu bit for "
            "bit) passed on all four. Gate B (eps=0 against the deposited fkp.N_H1_k0) passed 50 "
            "of 50 in both hemispheres. Gate C (NGC v1 against record 50) discrepancy 0.00 "
            "generators against a limit of 3. About 35 s per mock for the v1 branches and 46 for "
            "the v2 branches, the difference being contention with the two 4.2a runs."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-57-box-cox-misurata",
            "amends_records": [50],
            "companion_document": ("src/paper2_boxcox_v2.py; checklist item 4.2b-5; "
                                   "paper2_stato.md"),
            "a_threshold_that_must_be_derived_after_the_fact_is_declared_by_a_refusal": "The SGC "
                "threshold could not sit in record 50 because s^v1 SGC did not exist. What makes "
                "the late declaration defensible is that the tool REFUSES the v2 branch without "
                "the threshold and refuses to accept one on the v1 branch. The order is enforced "
                "by the code, and the file timestamps record it.",
            "a_side_without_a_counterpart_is_covered_by_reproducing_the_side_that_has_one": "SGC "
                "has no published Box-Cox value. Reproducing NGC to zero discrepancy is what makes "
                "the SGC branch trustworthy, and the tool stops if it does not. Second use of this "
                "structure in one day, after the DESI nu cache.",
            "a_module_that_parses_arguments_at_import_time_is_isolated_not_edited": "rev1_r14_"
                "monotone kills any process that imports it. sys.argv is substituted for the "
                "import alone. The file belongs to Paper 1 and its results are deposited.",
            "what_this_does_not_do": "It changes no other threshold, does not touch the 4.2a "
                "ensemble, and asserts nothing about the remaining five rules, whose outcomes "
                "depend on the 2000 realisations still running."
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
    print(f"esito     : NGC {esito(S['NGC']['v2'], S['NGC']['sem_v2'], *soglie(S['NGC']['v1']))}"
          f"   SGC {esito(S['SGC']['v2'], S['SGC']['sem_v2'], *soglie(S['SGC']['v1']))}")

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

    base = tempfile.mkdtemp(prefix="amend57_")
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

    def a(attesi=56, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    scrivi_ledger(56)
    raw_prima = open(led, "rb").read()
    ok("1 ledger sintetico a 56 record", len(leggi_ledger(led)[1]) == 56)
    ok("2 dry-run non scrive", cmd_append(a(dry=True)) == 0 and open(led, "rb").read() == raw_prima)
    ok("3 conteggio sbagliato: rifiuto", cmd_append(a(attesi=55)) == 2)
    ok("4 append: esito 0", cmd_append(a()) == 0)

    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("5 il conteggio cambia: 56 -> 57", len(recs2) == 57)
    ok("6 numbering_rule dice 57", "record 57." in recs2[-1]["numbering_rule"])
    ok("7 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 57)
    ok("8 i 56 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("9 secondo append rifiutato per item duplicato", cmd_append(a(attesi=57)) == 2)

    rec = recs2[-1]
    nv = rec["new_value"]
    II = nv["ii_s_v1_reproduced_exactly_in_NGC_and_measured_for_the_first_time_in_SGC"]
    III = nv["iii_the_SGC_thresholds_are_derived_and_were_declared_BEFORE_v2"]
    IV = nv["iv_the_outcome_is_FAILURE_in_both_hemispheres"]
    V = nv["v_the_shift_is_measured_with_the_PAIRED_denominator"]
    VI = nv["vi_the_non_monotonicity_in_eps_is_confirmed_independently_and_survives"]

    # --- le soglie si RIDERIVANO, non si rileggono --------------------------
    ok("10 NGC: 45.83 e' un quarto di |s^v1|",
       abs(III["NGC"]["success_below"] - round(abs(S["NGC"]["v1"]) * 0.25, 2)) < 1e-9)
    ok("11 NGC: 137.49 sono tre quarti, e stanno nel record 50",
       abs(III["NGC"]["failure_above"] - round(abs(S["NGC"]["v1"]) * 0.75, 2)) < 1e-9)
    ok("12 SGC: le soglie si riderivano dallo stesso modo",
       abs(III["SGC"]["success_below"] - round(abs(S["SGC"]["v1"]) * 0.25, 2)) < 1e-9
       and abs(III["SGC"]["failure_above"] - round(abs(S["SGC"]["v1"]) * 0.75, 2)) < 1e-9)
    ok("13 il rapporto fra fallimento e successo e' tre, in entrambi",
       all(abs(III[r]["failure_above"] / III[r]["success_below"] - 3.0) < 1e-9
           for r in ("NGC", "SGC")))

    # --- l'esito si RICALCOLA dalle soglie ---------------------------------
    for r in ("NGC", "SGC"):
        su, fa = soglie(S[r]["v1"])
        ok("14+ %s: l'esito nel record e' quello che le soglie impongono" % r,
           IV[r]["esito"] == esito(S[r]["v2"], S[r]["sem_v2"], su, fa) == "FALLIMENTO")
        ok("16+ %s: |s^v2| supera la soglia di fallimento" % r,
           abs(S[r]["v2"]) > fa)
        ok("18+ %s: sigma(s^v2) sta sotto il limite di invalidazione" % r,
           S[r]["sem_v2"] < SIGMA_MAX_INVALIDA)

    # --- la variazione appaiata, e che sia PIU' STRETTA della quadratura ----
    for r in ("NGC", "SGC"):
        quad = np.sqrt(S[r]["sem_v1"] ** 2 + S[r]["sem_v2"] ** 2)
        ok("20+ %s: la SEM appaiata e' piu' stretta della quadratura" % r,
           S[r]["sem_d_appaiata"] < quad)
        ok("22+ %s: e il rapporto e' circa 2.6" % r,
           abs(quad / S[r]["sem_d_appaiata"] - 2.6) < 0.1)
        ok("24+ %s: la variazione dichiarata e' s^v2 - s^v1" % r,
           abs(S[r]["d_appaiata"] - (S[r]["v2"] - S[r]["v1"])) < 0.01)
        ok("26+ %s: e resta sotto 1.5 sigma con il denominatore stretto" % r,
           abs(S[r]["d_appaiata"] / S[r]["sem_d_appaiata"]) < 1.5)

    # --- la non-monotonia -----------------------------------------------------
    for nome in ("SGC_v1", "NGC_v2", "SGC_v2"):
        tre = VI[nome]
        ok("28+ %s: sale, quasi ferma, poi cambia segno" % nome,
           tre[0] > 0 and tre[1] > 0 and tre[2] < 0 and abs(tre[1] - tre[0]) < 0.2 * tre[0])

    ok("31 il record dichiara che NON e' una conferma dell'anomalia",
       "not a confirmation" in IV["what_this_does_NOT_mean"])
    ok("32 e che l'ordine e' imposto dallo strumento, non dall'intenzione",
       "refusal built into the tool" in III["and_this_is_not_the_ideal_sequence"])
    ok("33 lo scarto di NGC contro il record 50 e' zero",
       II["NGC"]["discrepancy_against_record_50"] == 0.0)
    ok("34 SGC non esisteva prima", II["SGC"]["existed_nowhere_before"] is True)
    ok("35 emenda il record 50", rec["rules"]["amends_records"] == [50])
    ok("36 il record non afferma nulla sulle altre cinque regole",
       "asserts nothing about the remaining five" in rec["rules"]["what_this_does_not_do"])
    ok("37 i cancelli importati sono quelli del 50",
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
    p_a.add_argument("--attesi", type=int, default=56)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

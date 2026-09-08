#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend51.py — appende il record 51: la soglia numerica di 4.3b.

Il record 50 dichiarava la forma della regola e diceva esplicitamente che il numero si
sarebbe scritto solo dopo aver misurato sigma(P). E' misurata, e questo record la scrive.

I cancelli sull'append (conteggio, a capo finale, ancore al reference, item non duplicato,
terminazione di riga di maggioranza, rilettura) sono quelli di paper2_append_amend50, da cui
si importano: sono l'unica implementazione di quella logica.

Uso:
    python paper2_append_amend51.py selftest
    python paper2_append_amend51.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 50 --dry-run
"""

import argparse
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

def b_crlf():
    return chr(13).encode() + chr(10).encode()


ITEM = "4.3b/soglia_numerica"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "the_k1_peak_is_24_percent_data_side_in_NGC_and_47_percent_in_SGC_so_the_threshold_is_written_on_the_mock_side_part_only",
        "json_path": ("results/paper2/fase3_mock.jsonl (points.FID.N_H1_k0..k2, region NGC and SGC, "
                      "smoke records excluded); results/paper2/fase3.jsonl (ladder.0..2.N_H1, "
                      "point FID); logs/ladder_sigma.jsonl; src/paper2_ladder_sigma.py; "
                      "src/paper2_prominenza_v1.py; paper2_item4_2b_dichiarazione.md"),
        "old_value": (
            "Record 50 declared the FORM of the 4.3b rule and left the number unwritten: "
            "'sigma(P^v1) is not in any register... the NUMERIC threshold is written only after "
            "sigma(P^v1) is measured'. The v1 prominence was known only from the rounded deficits "
            "of erosion_ladder_canonical: +5.00 pp (NGC) and +7.55 pp (SGC), with no uncertainty "
            "and no separation of what the mock side contributes."
        ),
        "new_value": {
            "the_quantity_is_the_MOCK_SIDE_prominence": {
                "definition": "P = D(k=1) - 1/2 [D(k=0) + D(k=2)] splits exactly into two terms. "
                              "P_mock = D(N1, d1) - D((N0+N2)/2, d1) is the part produced by the "
                              "mock counts at k=1 departing from the linear interpolation of their "
                              "neighbours, at FIXED data side. The remainder is what P would be if "
                              "the mock ladder were linear, and it is driven by the DESI ladder's "
                              "own departure from linearity.",
                "why_it_matters": "Ensemble v2 changes the mock voxelisation only. The remainder is "
                                  "invariant under reweighting by construction, so a threshold on "
                                  "the total P would again be partly non-falsifiable - the same "
                                  "defect record 50 removed from the Box-Cox prediction, found a "
                                  "second time in a different place.",
                "the_split_is_verified_behaviourally": "P_mock depends on d1 and NOT on d0 or d2: "
                                  "the selftest of paper2_prominenza_v1 asserts it to 1e-9 while "
                                  "the total P moves. With a data side constant across levels the "
                                  "remainder collapses to the algebraic convexity of D = 1 - "
                                  "N_DESI/N and is under 1% of P; with the real, level-dependent "
                                  "data side it is a quarter to a half."
            },
            "the_measurement_v1_n_equals_200": {
                "NGC": {
                    "deficits_pp": [20.233912020455296, 25.399636405541877, 20.591452401568382],
                    "N_H1_DESI": [28256, 23790, 20066],
                    "P_pp": 4.9869541945300355,
                    "P_mock_pp": 3.7943150577959854,
                    "P_mock_per_realisation_pp": 3.7910299743654106,
                    "P_remainder_pp": 1.19263913673405,
                    "data_side_share": 0.239,
                    "sem_paired_P_pp": 0.015395223582361098,
                    "sem_jackknife_P_pp": 0.014981576816953588,
                    "sem_paired_P_mock_pp": 0.016539699645061558,
                    "sem_unpaired_pp": 0.07182433965814909,
                    "pairing_gain": 4.665365155231718,
                    "mock_k1_minus_linear_generators": 1543.4775000000009,
                    "DESI_k1_minus_linear_generators": -371.0,
                    "r_k0_k1": 0.9545978381885118,
                    "r_k1_k2": 0.9642758740105308
                },
                "SGC": {
                    "deficits_pp": [19.10955247608644, 27.108651258196563, 19.99557344400785],
                    "N_H1_DESI": [15122, 12011, 10049],
                    "P_pp": 7.5560882981494215,
                    "P_mock_pp": 3.9668154384590704,
                    "P_mock_per_realisation_pp": 3.962339233813496,
                    "P_remainder_pp": 3.589272859690351,
                    "data_side_share": 0.475,
                    "sem_paired_P_pp": 0.020870102039003337,
                    "sem_jackknife_P_pp": 0.020632307187279562,
                    "sem_paired_P_mock_pp": 0.022126166389742175,
                    "sem_unpaired_pp": 0.08337979093160433,
                    "pairing_gain": 3.9951788820092506,
                    "mock_k1_minus_linear_generators": 850.4625000000015,
                    "DESI_k1_minus_linear_generators": -574.5,
                    "r_k0_k1": 0.9317282407928351,
                    "r_k1_k2": 0.928079244700712
                },
                "n_is_200_not_2000": "The ladder at k=1 exists per realisation only in the block-A "
                                     "phase-3 register, which carries 200 realisations per "
                                     "hemisphere. Every number here is an n=200 number and must not "
                                     "be compared with an n=2000 one."
            },
            "the_thresholds_now_written": {
                "NGC": {"success_below_pp": 1.264771685931995,
                        "failure_above_pp": 2.52954337186399,
                        "zone_separation_sigma": 76.46884242602508},
                "SGC": {"success_below_pp": 1.3222718128196902,
                        "failure_above_pp": 2.6445436256393804,
                        "zone_separation_sigma": 59.76054728724735},
                "the_rule": "Success, i.e. the Paper 1 Sec.8.1 attribution holds and the k=1 peak is "
                            "a weighting artefact: P_mock^v2 below one third of P_mock^v1 AND "
                            "compatible with zero within 3 sigma. Failure, i.e. the maximum at k=1 "
                            "is geometric: P_mock^v2 above two thirds of P_mock^v1. Between them, "
                            "partial, reported with its fraction and sigma.",
                "the_validity_condition_is_met": "Record 50 required the two zones to be at least 3 "
                            "sigma apart. They are 76.5 and 59.8 sigma apart, so the rule decides. "
                            "If sigma on v2 is larger than a third of P_mock^v1, i.e. above 1.26 pp "
                            "(NGC) or 1.32 pp (SGC), the rule stops deciding and that is declared "
                            "before the result is read.",
                "paired_and_jackknife_agree": "2.7% (NGC) and 1.1% (SGC): the per-realisation and "
                            "ensemble definitions of P are the same quantity. The unpaired sigma is "
                            "4.0 to 4.7 times larger and is the wrong denominator, not a "
                            "conservative one."
            },
            "a_result_not_predicted_the_asymmetry_is_on_the_DATA_side": {
                "what_was_measured": "The total prominence differs by 51.5% between hemispheres "
                                     "(+4.987 pp NGC against +7.556 pp SGC). Its mock-side part "
                                     "differs by 4.5% (+3.7943 +- 0.0165 against +3.9668 +- 0.0221). "
                                     "The hemispheric asymmetry of the k=1 peak is therefore carried "
                                     "almost entirely by the data side.",
                "and_the_data_side_has_the_same_sign_in_both": "DESI at k=1 sits below its own linear "
                                     "interpolation in both hemispheres, by 371.0 generators in NGC "
                                     "and 574.5 in SGC, while the mocks sit above theirs by 1543.5 "
                                     "and 850.5. Both displacements raise the deficit at k=1: the "
                                     "peak is jointly produced, not a mock property.",
                "two_cautions_that_are_part_of_the_result": "4.5% is 6.24 sigma: the two mock-side "
                                     "terms are close in relative terms and distinguishable in "
                                     "absolute ones, and the smaller one is not the smaller "
                                     "hemisphere. And the two hemispheres share the same suite of "
                                     "simulations, so agreement between them is expected by "
                                     "construction and is not a confirmation - the same caution "
                                     "already standing for the partial correlations."
            },
            "the_gates_that_validated_the_measurement": {
                "reproduction": "NGC realisation index 0 reproduces 35318 exactly at k=0, the value "
                                "the frozen provenance gate of rev1_r14_monotone_testB and "
                                "tabres_probe.jsonl both check. This is what validates that the "
                                "phase-3 FID point is the fiducial geometry.",
                "ladder_against_Table_9": "20.234 / 25.400 / 20.591 pp in NGC and 19.110 / 27.109 / "
                                "19.996 in SGC, against 20.2 / 25.4 / 20.6 and 19.1 / 27.1 / 20.0 "
                                "published in P1 Table 9.",
                "union_not_last_wins": "k=0 and k=1 come from the earlier runs and k=2 from the run "
                                "of record 49; a last-wins reader loses two of the three levels."
            },
            "an_error_recorded_because_it_was_made_and_caught": {
                "what_happened": "The k=0 target was first declared as 20.26 pp (NGC) and 19.19 pp "
                                 "(SGC). Those are the n=2000 deficits. On the n=200 block-A subset "
                                 "the values are 20.234 and 19.108. SGC was REFUSED by the gate, "
                                 "scarto 0.0804 pp against a tolerance of 0.05.",
                "the_dangerous_half": "NGC PASSED, because its subset offset is 0.0296 pp and the "
                                      "tolerance was 0.05. It passed against the wrong target, which "
                                      "is worse than failing. What actually validated NGC is the "
                                      "per-realisation reproduction gate, not the mean.",
                "and_no_n200_mean_exists_for_NGC": "The reference deposits SGC_n200 (mock_mean "
                                      "18694.0, with the standing note not to average it with "
                                      "SGC_n2000) but no NGC counterpart. For NGC the reproduction "
                                      "gate stands in place of a mean gate.",
                "the_class_of_error": "A tolerance calibrated at one sample size applied unchanged at "
                                      "another. Already on the register from the |Delta delta| <= "
                                      "1e-3 case and from gate 2.2a."
            },
            "smoke_records_live_in_the_production_register": {
                "what_they_are": "38 records of results/paper2/fase3_mock.jsonl carry a `smoke` key. "
                                 "They hold FID and B1/B5 values at k=0 and k=1 that differ from the "
                                 "production ones: reading NGC without excluding them produces 6 "
                                 "conflicts, the first being 35318 against 35538 at index 0.",
                "how_it_is_handled": "They are excluded by a negative filter, not deleted. The "
                                     "register is append-only.",
                "why_the_first_detector_missed_them": "The discriminant check compared the DISTINCT "
                                     "VALUES of a field, and `smoke` has one. Absence must count as "
                                     "a value; the check now does, and refuses before the union "
                                     "rather than after.",
                "SGC_is_unaffected": "Its numbers are identical with and without the exclusion, "
                                     "which is why the flaw was invisible on that hemisphere."
            }
        },
        "reason": (
            "Record 50 wrote the rule of 4.3b without its number and named the condition for writing "
            "it: measure sigma(P) on v1. Measuring it did two things. It produced the number, and it "
            "showed that a quarter of the peak in NGC and nearly half in SGC lives on the data side, "
            "which the treatment under test cannot move. The threshold is therefore written on the "
            "mock-side part, and the total prominence is reported but not used as a decision variable."
        ),
        "evidence": (
            "Runs of 7 Sep 2026, src/paper2_ladder_sigma.py (selftest 18/18) with P and its sigmas "
            "imported from src/paper2_prominenza_v1.py (selftest 20/20); outputs deposited in "
            "logs/ladder_sigma.jsonl. Source: results/paper2/fase3_mock.jsonl, 2038 rows, filtered "
            "by region and with the smoke records excluded, 1000 rows per hemisphere, read by UNION "
            "on the `index` field, 200 realisations complete at k=0,1,2 in both hemispheres. Data "
            "side from results/paper2/fase3.jsonl, 44 records, one selected by region and point=FID: "
            "N_H1 DESI 28256 / 23790 / 20066 (NGC) and 15122 / 12011 / 10049 (SGC). Reproduction "
            "gate: NGC index 0 gives 35318, the frozen value. Target gate: D(k=0) recomputed "
            "20.2339 pp (NGC) and 19.1096 pp (SGC), the latter against the n=200 value 19.108 "
            "derived from the reference SGC_n200 block (15122 against mock_mean 18694.0), at a "
            "tolerance of 0.01 pp. Paired against jackknife sigma agree to 2.7% and 1.1%; the "
            "unpaired sigma is 4.7 and 4.0 times larger. Level correlations 0.955 / 0.964 (NGC) and "
            "0.932 / 0.928 (SGC)."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-51-soglia-numerica-4-3b-lato-mock",
            "amends_records": [50],
            "companion_document": "paper2_item4_2b_dichiarazione.md sezione 3; checklist_paper2.md 4.3b",
            "a_threshold_is_written_only_on_the_part_the_treatment_can_move": "Found twice now, in "
                "two unrelated places: the Box-Cox excursion (84.3% data side, record 50) and the "
                "erosion peak (24% and 47% data side, here). The generalisation belongs in the "
                "protocol: before declaring any v1 -> v2 prediction, split the quantity and check "
                "how much of it the reweighting can reach.",
            "what_this_does_not_do": "It does not measure v2, does not change ensemble v1, and does "
                "not reopen P1 Table 9, whose published deficits it reproduces. The attribution of "
                "the k=1 maximum remains open: this record only makes it decidable."
        }
    }


def cmd_append(args):
    # Stessa orchestrazione del 50, con l'item e il record di questo emendamento.
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
    print(f"fine riga : {'CRLF' if eol == b_crlf() else 'LF'} "
          f"(maggioranza: CRLF {crlf}, LF soli {lf})")
    print(f"ancore    : file {ref_file_sha[:12]}…  self {str(ref_self_sha)[:12]}…  concordi")
    print(f"item      : {rec['item']}")
    print(f"byte      : {len(linea)}")

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
          f"--file src\\paper2_freeze_verify.py --da {n} --a {n + 1}")
    print("  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="amend51_")
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
                fh.write(json.dumps(r).encode("utf-8") + b"\r\n")

    class A:
        pass

    def a(attesi=50, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    scrivi_ledger(50)
    raw_prima = open(led, "rb").read()
    ok("1 ledger sintetico a 50 record", len(leggi_ledger(led)[1]) == 50)
    ok("2 dry-run non scrive", cmd_append(a(dry=True)) == 0 and open(led, "rb").read() == raw_prima)
    ok("3 conteggio sbagliato: rifiuto", cmd_append(a(attesi=49)) == 2)
    ok("4 append: esito 0", cmd_append(a()) == 0)

    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("5 il conteggio cambia: 50 -> 51", len(recs2) == 51)
    ok("6 numbering_rule dice 51", "record 51." in recs2[-1]["numbering_rule"])
    ok("7 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 51)
    ok("8 i 50 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("9 secondo append rifiutato per item duplicato", cmd_append(a(attesi=51)) == 2)

    rec = recs2[-1]
    ok("10 le due soglie sono nel record",
       "the_thresholds_now_written" in rec["new_value"]
       and rec["new_value"]["the_thresholds_now_written"]["NGC"]["success_below_pp"] > 0)
    ok("11 la separazione delle zone e' oltre 3 sigma in entrambi",
       min(rec["new_value"]["the_thresholds_now_written"][r]["zone_separation_sigma"]
           for r in ("NGC", "SGC")) > 3.0)
    ok("12 la soglia di successo e' un terzo di P lato mock",
       abs(rec["new_value"]["the_thresholds_now_written"]["NGC"]["success_below_pp"]
           - rec["new_value"]["the_measurement_v1_n_equals_200"]["NGC"]["P_mock_pp"] / 3.0) < 1e-9
       and abs(rec["new_value"]["the_thresholds_now_written"]["SGC"]["success_below_pp"]
               - rec["new_value"]["the_measurement_v1_n_equals_200"]["SGC"]["P_mock_pp"] / 3.0) < 1e-9)
    ok("13 P = lato mock + resto, in entrambi gli emisferi",
       all(abs(v["P_pp"] - v["P_mock_pp"] - v["P_remainder_pp"]) < 1e-9
           for v in (rec["new_value"]["the_measurement_v1_n_equals_200"]["NGC"],
                     rec["new_value"]["the_measurement_v1_n_equals_200"]["SGC"])))
    ok("14 la quota lato dati dichiarata torna col rapporto",
       all(abs(v["data_side_share"] - v["P_remainder_pp"] / v["P_pp"]) < 0.001
           for v in (rec["new_value"]["the_measurement_v1_n_equals_200"]["NGC"],
                     rec["new_value"]["the_measurement_v1_n_equals_200"]["SGC"])))
    ok("15 i cancelli importati sono quelli del 50",
       "paper2_append_amend50" in sys.modules
       and sys.modules["paper2_append_amend50"].sha256_file is sha256_file)

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
    p_a.add_argument("--attesi", type=int, default=50)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

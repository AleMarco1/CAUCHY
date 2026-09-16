#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend59.py — appende il record 59: 4.3b ha un esito e FALLISCE.
Sei regole su sei, in entrambi gli emisferi. La Fase 4 e' decisa.

I cancelli sull'append si importano da paper2_append_amend50.

Uso:
    python paper2_append_amend59.py selftest
    python paper2_append_amend59.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 58 --dry-run
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

ITEM = "4.3b/prominenza_su_v2_sei_regole_su_sei_falliscono"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"
CRLF = chr(13).encode() + chr(10).encode()

# Da results/paper2/verdetto_v2_{NGC,SGC}_finale.json, 11 settembre 2026.
P = {
    "NGC": {"v1": 3.8160788230778366, "sem1": 0.00555886271332237,
            "v2": 3.8445170129516706, "sem2": 0.005670157409902198,
            "succ": 1.272026274359279, "fall": 2.544052548718558,
            "sigma_da_zero": 678.026505267335, "sep": 228.82851042727515,
            "curv": 1.1912210274362844, "guadagno": 5.005054953585065},
    "SGC": {"v1": 3.9716387996783453, "sem1": 0.007117671607931772,
            "v2": 3.9877532370277495, "sem2": 0.007194723028697145,
            "succ": 1.3238795998927817, "fall": 2.6477591997855634,
            "sigma_da_zero": 554.2608410528169, "sep": 185.9989716886461,
            "curv": 3.5881993622738086, "guadagno": 4.7267080573383184},
}
REGOLE = ("4.2b-1", "4.2b-2", "4.2b-4", "4.2b-5", "4.2c", "4.3b")


def delta_quadratura(reg):
    d = P[reg]["v2"] - P[reg]["v1"]
    s = float(np.sqrt(P[reg]["sem1"] ** 2 + P[reg]["sem2"] ** 2))
    return d, s, d / s


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    dN, sN, zN = delta_quadratura("NGC")
    dS, sS, zS = delta_quadratura("SGC")
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "rule_4_3b_has_an_outcome_and_all_six_rules_fail",
        "json_path": ("results/paper2/verdetto_v2_{NGC,SGC}_finale.json; "
                      "src/paper2_verdetto_v2.py; src/paper2_prominenza_v1.py; "
                      "records 50, 54, 57, 58"),
        "old_value": (
            "Record 58 declared the recalibrated 4.3b thresholds - 1.272026274359279 pp (NGC) "
            "and 1.3238795998927817 pp (SGC) - and asserted nothing about the outcome, because "
            "paper2_verdetto_v2.py refuses to compute P^v2 until the threshold is passed in from "
            "outside and matches the one derived from P^v1. At that point five of the six rules "
            "had an outcome and 4.3b was SOSPESA."
        ),
        "new_value": {
            "i_the_threshold_was_declared_first_and_the_tool_enforced_it": {
                "sequence": "Record 58 (ledger) declared the thresholds; the second pass of the "
                    "verdict was then run with --soglia-4-3b and the tool re-derived the "
                    "threshold from P^v1 and compared it to the one supplied, to 1e-6, BEFORE "
                    "computing P^v2. Had they differed the run would have been refused as "
                    "'either from another pass, or chosen by hand'.",
                "why_it_matters_here_more_than_elsewhere": "Between the computation of P^v1 and "
                    "that of P^v2 lies the only window in which a threshold could be written "
                    "with the result already on disk. It was closed by a refusal in the code, "
                    "not by the care of the person running it."
            },
            "ii_4_3b_fails_in_both_hemispheres": {
                "NGC": {"P_v1_pp": P["NGC"]["v1"], "P_v2_pp": P["NGC"]["v2"],
                        "sem_v2_pp": P["NGC"]["sem2"],
                        "success_below_pp": P["NGC"]["succ"],
                        "failure_above_pp": P["NGC"]["fall"],
                        "sigma_from_zero": P["NGC"]["sigma_da_zero"],
                        "zone_separation_sigma": P["NGC"]["sep"],
                        "esito": "FAILURE"},
                "SGC": {"P_v1_pp": P["SGC"]["v1"], "P_v2_pp": P["SGC"]["v2"],
                        "sem_v2_pp": P["SGC"]["sem2"],
                        "success_below_pp": P["SGC"]["succ"],
                        "failure_above_pp": P["SGC"]["fall"],
                        "sigma_from_zero": P["SGC"]["sigma_da_zero"],
                        "zone_separation_sigma": P["SGC"]["sep"],
                        "esito": "FAILURE"},
                "both_success_clauses_fail": "Record 50 required P^v2 below one third of P^v1 "
                    "AND compatible with zero within 3 sigma. P^v2 is 3.84 and 3.99 pp against "
                    "thresholds of 1.27 and 1.32, and sits 678 and 554 sigma from zero.",
                "the_rule_decides_the_zones_are_separated": "The declared invalidation - the two "
                    "zones closer than 3 sigma - is not met: they are 229 and 186 sigma apart."
            },
            "iii_the_prominence_does_not_move_and_if_anything_grows": {
                "NGC": {"delta_pp": dN, "sem_in_quadrature": sN, "sigma": zN},
                "SGC": {"delta_pp": dS, "sem_in_quadrature": sS, "sigma": zS},
                "the_denominator_quoted_here_is_the_WRONG_one": "P^v1 and P^v2 are computed on "
                    "the SAME 2000 realisations, so their difference is PAIRED and the "
                    "quadrature sum is not its error - record 51: 'the unpaired sigma is not "
                    "conservative, it is wrong'. paper2_prominenza_v1 returns a SEM for each P, "
                    "not for the difference, so the paired figure is not available and the "
                    "quadrature one is quoted. The paired SEM would be TIGHTER and the "
                    "significance LARGER: the number below understates the effect, and the "
                    "effect is in the direction that disfavours reweighting.",
                "what_it_says": "Reweighting moves the erosion-peak prominence by +0.7 per cent "
                    "in NGC and +0.4 per cent in SGC. It does not shrink it toward zero; it "
                    "nudges it up."
            },
            "iv_six_rules_of_six": {
                "outcomes": {r: {"NGC": "FAILURE", "SGC": "FAILURE"} for r in REGOLE},
                "4.2b-3": "withdrawn as a falsification by record 54, reported without a "
                    "threshold.",
                "none_marginal_none_invalidated": "Twenty-four independent outcomes - six rules, "
                    "two hemispheres, two paired branches - and not one falls in the "
                    "does-not-decide zone, not one meets its declared invalidation condition.",
                "and_three_of_the_six_move_the_WRONG_way": "The median of max delta over the "
                    "DESI value goes from 27.80 to 28.47 (NGC) and 40.32 (SGC); the variance "
                    "ratio rises by 12.7 and 154.9; the prominence rises by 0.03 and 0.02 pp. "
                    "Reweighting does not merely fail to close the gap - on these three it "
                    "widens it.",
                "what_is_settled": "FKP reweighting of the mock voxelisation is not the "
                    "explanation of the anomaly. That was the hypothesis Phase 4 existed to "
                    "test, and it is falsified with a margin that leaves no alternative reading."
            },
            "v_what_this_does_not_settle": {
                "the_anomaly_is_not_confirmed_by_this": "Phase 4 asked whether ONE candidate "
                    "systematic explains the deficit. It does not. That removes a candidate; it "
                    "does not establish the physical claim, and nothing in this record should be "
                    "read as doing so.",
                "items_of_phase_4_still_open": "4.2d - Table 12 on v2 as an internal gate - and "
                    "the repetition of D2 on v2. And 4.2d needs redefining before it is run: "
                    "rows 3-4 of Table 12 have been shown to count TIED VALUES in the smoothed "
                    "field, not galaxies sharing a cell (see the Paper 1 revision notes), so "
                    "applying them to v2 as a gate on the voxelisation would test something "
                    "other than what the item intended.",
                "and_the_reweighting_question_is_not_the_same_as_the_weighting_question":
                    "This record says the FKP weighting of the MOCK voxelisation does not "
                    "explain the deficit. It says nothing about whether the weighting scheme "
                    "itself, applied to data and mocks alike, is the right one."
            }
        },
        "reason": (
            "4.3b was the last of the six rules without an outcome, and its threshold had to be "
            "declared before P^v2 could be computed. Record 58 declared it; this record carries "
            "the outcome. P^v2 is 3.84 pp in NGC and 3.99 in SGC against failure thresholds of "
            "2.54 and 2.65, and 678 and 554 sigma from zero against a success clause that "
            "required compatibility with zero. Six rules of six now fail, in both hemispheres, "
            "none marginally. Phase 4 is decided: FKP reweighting of the mock voxelisation is "
            "not the explanation of the anomaly."
        ),
        "evidence": (
            "Second pass of src/paper2_verdetto_v2.py (selftest 67/67) on 11 Sep 2026 at "
            "06:41Z, with --soglia-4-3b set to the values declared in record 58; the tool "
            "re-derived each threshold from P^v1 and matched it to 1e-6 before computing P^v2. "
            "Fourteen gates passed in both hemispheres beforehand. P is imported from "
            "paper2_prominenza_v1, which carries the curvature subtraction that belongs to the "
            "definition; the data side comes from desi_ladder_{NGC,SGC}.json, whose k=0 value "
            "reproduces the frozen 28256 and 15122 exactly."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-59-4-3b-fase-4-decisa",
            "amends_records": [50, 54, 58],
            "companion_document": ("results/paper2/verdetto_v2_{NGC,SGC}_finale.json; "
                                   "paper2_stato.md; checklist items 4.2b, 4.2c, 4.3b"),
            "a_paired_difference_quoted_with_an_unpaired_error_understates_it":
                "The quadrature figure is given here because the paired one is not computed by "
                "the canonical implementation. It is labelled as the wrong denominator rather "
                "than passed off as conservative, and the direction of the bias is stated.",
            "what_this_does_not_do": "It does not close Phase 4: items 4.2d and D2 on v2 remain, "
                "and 4.2d needs redefining first. It does not confirm the anomaly - it removes "
                "one candidate explanation. It touches no Paper 1 result and no v1 value."
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
    # il record 58 deve esserci: e' lui a dichiarare le soglie che questo usa
    if not any("ensemble_v2_misurato" in str(r.get("item", "")) for r in recs):
        print("RIFIUTO: il record 58 non e' nel ledger. Le soglie di 4.3b devono "
              "essere DICHIARATE prima che l'esito venga registrato.")
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
    print("4.3b      : NGC P^v2 %.4f pp contro soglia %.4f -> FALLIMENTO"
          % (P["NGC"]["v2"], P["NGC"]["fall"]))
    print("            SGC P^v2 %.4f pp contro soglia %.4f -> FALLIMENTO"
          % (P["SGC"]["v2"], P["SGC"]["fall"]))
    print("            sei regole su sei, entrambi gli emisferi")

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

    base = tempfile.mkdtemp(prefix="amend59_")
    led = os.path.join(base, "ledger.jsonl")
    ref = os.path.join(base, "reference.json")
    with open(ref, "w", encoding="utf-8", newline="") as fh:
        json.dump({"_self_sha256": "s" * 64}, fh)
    ref_sha = sha256_file(ref)

    def scrivi_ledger(n, con58=True):
        with open(led, "wb") as fh:
            for i in range(n):
                r = {"item": f"x{i}", "type": "protocol"}
                if con58 and i == n - 1:
                    r["item"] = "4.2a-4.2b-4.2c/ensemble_v2_misurato_cinque_regole_falliscono"
                if i == n - 1:
                    r["reference_file_sha256"] = ref_sha
                    r["reference_self_sha256"] = "s" * 64
                fh.write(json.dumps(r).encode("utf-8") + CRLF)

    class A:
        pass

    def a(attesi=58, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    # --- il cancello sul record 58 ------------------------------------------
    scrivi_ledger(58, con58=False)
    ok("1 senza il record 58 l'append e' RIFIUTATO", cmd_append(a(dry=True)) == 2)
    scrivi_ledger(58, con58=True)
    raw_prima = open(led, "rb").read()
    ok("2 col record 58 presente, il dry-run passa", cmd_append(a(dry=True)) == 0)
    ok("3 e non scrive", open(led, "rb").read() == raw_prima)
    ok("4 conteggio sbagliato: rifiuto", cmd_append(a(attesi=57)) == 2)
    ok("5 append: esito 0", cmd_append(a()) == 0)
    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("6 il conteggio cambia: 58 -> 59", len(recs2) == 59)
    ok("7 numbering_rule dice 59", "record 59." in recs2[-1]["numbering_rule"])
    ok("8 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 59)
    ok("9 i 58 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("10 secondo append rifiutato per item duplicato", cmd_append(a(attesi=59)) == 2)

    rec = recs2[-1]
    nv = rec["new_value"]
    II = nv["ii_4_3b_fails_in_both_hemispheres"]
    III = nv["iii_the_prominence_does_not_move_and_if_anything_grows"]

    # --- l'esito si RICALCOLA dalle soglie ----------------------------------
    for reg in ("NGC", "SGC"):
        d = P[reg]
        ok(f"11+ {reg}: P^v2 supera la soglia di fallimento", d["v2"] > d["fall"])
        ok(f"13+ {reg}: e NON e' sotto quella di successo", not d["v2"] < d["succ"])
        ok(f"15+ {reg}: quindi FALLIMENTO", II[reg]["esito"] == "FAILURE")
        ok(f"17+ {reg}: non e' compatibile con zero entro 3 sigma",
           abs(d["v2"]) > 3 * d["sem2"])
        ok(f"19+ {reg}: e le zone distano molto piu' di 3 sigma", d["sep"] > 3.0)
        ok(f"21+ {reg}: la soglia usata e' un terzo di P^v1",
           abs(d["succ"] - d["v1"] / 3) < 1e-9)
        ok(f"23+ {reg}: e il fallimento il doppio del successo",
           abs(d["fall"] - 2 * d["succ"]) < 1e-9)

    # --- la prominenza CRESCE, non cala -------------------------------------
    for reg in ("NGC", "SGC"):
        dd, ss, zz = delta_quadratura(reg)
        ok(f"25+ {reg}: P^v2 e' MAGGIORE di P^v1, non minore", dd > 0)
        ok(f"27+ {reg}: la differenza in quadratura e' quella dichiarata",
           abs(III[reg]["delta_pp"] - dd) < 1e-12
           and abs(III[reg]["sem_in_quadrature"] - ss) < 1e-12)
        ok(f"29+ {reg}: e il denominatore e' dichiarato SBAGLIATO, non conservativo",
           "it is wrong" in III["the_denominator_quoted_here_is_the_WRONG_one"])

    # --- sei regole -----------------------------------------------------------
    IV = nv["iv_six_rules_of_six"]
    ok("31 sono sei regole, e 4.2b-3 non e' fra loro",
       len(IV["outcomes"]) == 6 and "4.2b-3" not in IV["outcomes"])
    ok("32 tutte e sei falliscono in entrambi gli emisferi",
       all(v["NGC"] == "FAILURE" and v["SGC"] == "FAILURE"
           for v in IV["outcomes"].values()))
    ok("33 e 4.3b e' fra le sei", "4.3b" in IV["outcomes"])

    # --- cio' che il record NON afferma ---------------------------------------
    V = nv["v_what_this_does_not_settle"]
    ok("34 il record dichiara che l'anomalia NON e' confermata",
       "does not establish the physical claim" in V["the_anomaly_is_not_confirmed_by_this"])
    ok("35 e che la Fase 4 non e' chiusa: restano 4.2d e D2",
       "4.2d" in V["items_of_phase_4_still_open"]
       and "D2" in V["items_of_phase_4_still_open"])
    ok("36 e che 4.2d va ridefinita prima di girare",
       "needs redefining" in V["items_of_phase_4_still_open"])
    ok("37 emenda 50, 54 e 58", rec["rules"]["amends_records"] == [50, 54, 58])
    ok("38 i cancelli importati sono quelli del 50",
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
    p_a.add_argument("--attesi", type=int, default=58)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

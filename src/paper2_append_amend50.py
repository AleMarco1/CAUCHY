#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend50.py — appende il record 50 al ledger degli emendamenti.

Il record 50 ritira quattro predizioni di 4.2b e deposita le sei regole di decisione
di 4.2b/4.3b, dichiarate PRIMA che l'ensemble v2 giri.

Cancelli meccanici, tutti bloccanti:
  1. il ledger deve avere esattamente --attesi record (default 49) e zero righe malformate;
  2. l'ultima riga deve terminare con un a capo, altrimenti l'append incollerebbe due record;
  3. i due digest del reference scritti nel record devono coincidere con quelli RICALCOLATI
     dal file su disco e con quelli portati dall'ultimo record;
  4. nessun record esistente puo' avere lo stesso `item`;
  5. la terminazione di riga usata e' quella MAGGIORITARIA del file (CRLF), mai imposta;
  6. dopo la scrittura il file viene riletto: deve avere --attesi + 1 record, tutti validi,
     e il nuovo deve stare in ultima posizione con numbering_rule coerente.

Uso:
    python paper2_append_amend50.py selftest
    python paper2_append_amend50.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 49 --dry-run
    python paper2_append_amend50.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 49 --backup logs\\amend.pre50.jsonl
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile

ITEM = "4.2b/4.3b/regole_di_decisione"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"


class Rifiuto(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blocco in iter(lambda: fh.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def leggi_ledger(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    if not raw.endswith(b"\n"):
        raise Rifiuto("l'ultima riga del ledger non termina con un a capo: "
                      "un append incollerebbe due record")
    testo = raw.decode("utf-8")
    righe = [r for r in testo.split("\n") if r.strip()]
    recs, malformate = [], []
    for i, r in enumerate(righe, 1):
        try:
            recs.append(json.loads(r))
        except Exception:
            malformate.append(i)
    if malformate:
        raise Rifiuto(f"righe malformate: {malformate}")
    crlf = raw.count(b"\r\n")
    lf_soli = raw.count(b"\n") - crlf
    eol = b"\r\n" if crlf >= lf_soli else b"\n"
    return raw, recs, eol, crlf, lf_soli


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    """Il numero e' la POSIZIONE: si deriva dal conteggio, non si scrive a mano."""
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "four_predictions_of_4_2b_are_withdrawn_because_they_were_written_on_a_different_quantity_from_the_one_measured",
        "json_path": ("src/paper2_v1_reference.json (box_cox_family.paper2_use, "
                      "small_scale_diagnostics.paper2_use); canovaccio_paper2.md Componente B punto 2; "
                      "checklist_paper2.md 4.2b, 4.3b; paper2_item4_2b_dichiarazione.md"),
        "old_value": (
            "4.2b carried five predictions and 4.3b one, all of them threshold crossings without a "
            "declared uncertainty. Four of the five named a starting number that does not belong to "
            "the quantity the run would measure: (i) excess kurtosis of nu 'from +3.90 towards +0.20 "
            "on the FULL footprint', (ii) maximum delta 'from 32244 towards ~125', (iii) the Box-Cox "
            "deficit excursion '20.3% -> 17.6% must compress', (iv) variance of delta 'from 1085 "
            "towards 1'. 4.3b predicted that the k=1 peak 'must flatten', with no statistic and no "
            "threshold."
        ),
        "new_value": {
            "i_kurtosis_wrong_restriction": {
                "what_was_wrong": "+3.90 and +0.20 are P10 numbers, from rev_n4n5_report.json "
                                  "momenti.P10.agg.kurt (mock_mean 3.902956198001257, mock_sd "
                                  "0.5983209563067237, desi 0.20448735601308332, z -6.181412840388943). "
                                  "The prediction placed them on the FULL footprint, where the v1 pair "
                                  "is different and DESI is NEGATIVE: NGC desi -0.43821476405642734 "
                                  "against mock 2.76384938163661 +- 0.47179461207878376 (z -6.786987523202857); "
                                  "SGC desi -1.1351732307682145 against 1.102669866717493 +- "
                                  "0.2742501734015092 (z -8.159860282784392). The declared target does "
                                  "not exist at the declared restriction.",
                "replaced_by": "z of DESI against the PER-REALISATION dispersion of the v2 mocks on the "
                               "full footprint, plus the empirical rank. Success |z| < 3 AND rank inside "
                               "the central 95% of 2000; failure |z| > 5; between 3 and 5 the rule DOES "
                               "NOT DECIDE and that is declared, not read for its sign."
            },
            "ii_max_delta_an_ensemble_extremum": {
                "what_was_wrong": "32244 is mock_max_delta.max in "
                                  "results/revision/rev1_r14_monotone_deltastats.json - the MAXIMUM over "
                                  "the ensemble of the per-mock maxima (32244.41015625). The median is "
                                  "3474.579833984375 and the minimum 2417.17626953125. Comparing it with "
                                  "the DESI maximum of 125, which is the maximum of ONE field, asks for a "
                                  "260x reduction where the like-for-like statement asks for 28x.",
                "replaced_by": "empirical rank of max(delta)_DESI among the 2000 per-mock maxima of v2. "
                               "Success: rank inside the central 95%. Failure: rank <= 20 or >= 1981. "
                               "Reported always: median(max delta)^v2 / 125, which is 27.80 on v1.",
                "and_the_field_name": "small_scale_diagnostics.max_delta_mock reads like a typical value "
                                      "and is an extremum. The name is not changed - the reference is "
                                      "frozen - it is annotated here."
            },
            "iii_box_cox_84_percent_of_it_is_the_data_side": {
                "what_was_wrong": "The deficit excursion is -2.714 pp (0.2028356661073125 at eps=0 to "
                                  "0.17569235376458497 at eps=1, results/revision/rev1_r14_monotone_testB.json). "
                                  "Decomposed: -2.288 pp if only the data side moved, -0.414 pp if only "
                                  "the mock side moved, interaction -0.012 pp. The DATA side carries 84.3% "
                                  "of it, and ensemble v2 changes the mock voxelisation only. The "
                                  "prediction as written was not falsifiable on v2.",
                "replaced_by": "s = <N_H1(eps=1) - N_H1(eps=0)> paired over the same 50 mocks, which is "
                               "the part of the quantity v2 can act on. v1 NGC: s = -183.32 +- "
                               "11.124102898936275 (-16.5 sigma); the pairing cancels 95% of the variance "
                               "(11.12 against 48.25 unpaired, r = 0.958). Threshold 45.8 generators "
                               "(25% of |s^v1|), which sits 4.1 sigma from zero and 12.4 sigma from the "
                               "v1 value; failure above 137.5 (75%). If sigma(s^v2) > 15 the rule does "
                               "not decide, and that is declared before the result is read.",
                "and_the_mock_side_is_NOT_MONOTONIC_in_eps": "+129.00 +- 4.194067724969716 at eps=0.25 "
                                  "(30.8 sigma), +124.52 +- 7.077543676290236 at eps=0.5, then -183.32 "
                                  "+- 11.124102898936275 at eps=1. An excursion of 312 generators WITH A "
                                  "SIGN CHANGE, invisible if only the two endpoints are read. The data "
                                  "side is monotonic: 28256, 28606, 28754, 29067. This is reported as a "
                                  "result, not predicted."
            },
            "iv_variance_ratio_has_two_implementations": {
                "what_was_wrong": "'towards 1' is a direction, not a threshold; and 1085 is one of two "
                                  "numbers for the same nominal quantity. "
                                  "results/paper1/paper1_step6_NGC.json footprint pieno gives "
                                  "1000.6039264234059; results/paper1/paper1_fkp_asymmetry_NGC.json "
                                  "onepoint_by_cut.0.0.var_ratio gives 1084.8087651141557. Same "
                                  "hemisphere, 8% apart. No published number is at risk: P1 Sec.7.2 "
                                  "states 'a factor 10^3' and both round to it.",
                "replaced_by": "R = <Var(delta)>_mock / Var(delta)_DESI on the full footprint, with "
                               "sigma(R) = SEM(Var_mock)/Var_DESI because the data side is deterministic. "
                               "v1: NGC 1000.60 +- 15.74 (2918.4033877918614 +- 649.2561203456237 over "
                               "2.9166419506502494, n=200); SGC 2068.32 +- 18.22 (9960.076648189868 +- "
                               "1240.7348398428771 over 4.815533379463941). THRESHOLD DERIVED, NOT "
                               "CHOSEN: the P10 cut is the cleaning P1 Sec.7.2 declares removes almost "
                               "all of the excess, and on v1 it brings R to 3.6790744990465085 (NGC) and "
                               "8.101621625795236 (SGC). Success: R^v2 + 3 sigma < twice those values, "
                               "i.e. < 7.358 and < 16.203. Failure: R^v2 - 3 sigma > 100.",
                "canonical_implementation": "step6, because it covers both hemispheres and carries sd and "
                                            "rank. The fkp_asymmetry value is to be reconciled or retired: "
                                            "one implementation per quantity."
            },
            "v_the_denominators_are_assigned_before_the_measurement": {
                "per_realisation": "4.2b-1 to 4.2b-4 compare the observed field, which has N=1, with "
                                   "single realisations. The rank needs no denominator at all, which is "
                                   "why it is the primary form.",
                "SEM": "4.2b-5 and 4.3b are ensemble-against-ensemble and use the PAIRED SEM."
            },
            "vi_4_3b_the_statistic_is_named": {
                "quantity": "P = D(k=1) - 1/2 [D(k=0) + D(k=2)], the PROMINENCE of the peak, not "
                            "D(1) - D(0): the prominence isolates the peak from the monotone decline with "
                            "k and is insensitive to a drift common to the levels. v1: +5.00 pp (NGC), "
                            "+7.55 pp (SGC), from erosion_ladder_canonical.",
                "a_curvature_term_belongs_to_the_DEFINITION": "D = 1 - N_DESI/N is convex in N, so a "
                            "perfectly linear ramp in N_H1 already produces a non-zero prominence. The "
                            "term is isolated by replacing N(k=1) with the mean of the two neighbours "
                            "and is subtracted. It is small - under 1% of P on a synthetic fixture - but "
                            "it is reported, not assumed.",
                "threshold_NOT_YET_WRITTEN": "sigma(P^v1) is not in any register. Success P^v2 < P^v1/3 "
                            "AND compatible with zero within 3 sigma; failure P^v2 > 2 P^v1/3; the two "
                            "zones must be at least 3 sigma apart or the rule does not decide. The "
                            "NUMERIC threshold is written only after sigma(P^v1) is measured."
            },
            "vii_the_per_mock_ladder_does_not_exist_in_one_register": {
                "what_the_scan_found": "results/paper1/per_mock_NGC_erosion_restrict.jsonl and its SGC "
                            "counterpart carry cells R5_er0, R5_er2, R5_er3 - there is NO er1. The k=1 "
                            "level per realisation exists only in results/paper2/fase3_mock.jsonl as "
                            "points.FID.N_H1_k1. Assembling P per realisation therefore requires a JOIN "
                            "across two registers produced by different runs.",
                "the_join_must_be_validated_before_use": "for the realisations in common, "
                            "points.FID.N_H1_k0 of fase3_mock.jsonl must equal base.N_H1 of "
                            "per_mock_NGC_R5.jsonl. If it does not, the two registers are different "
                            "treatments and P cannot be assembled from them.",
                "and_fase3_mock_is_read_by_UNION": "never last-wins, per record 49."
            },
            "viii_output_specification_for_4_2a": {
                "per_mock_both_hemispheres_all_2000": [
                    "sigma_in_mask and kurt_in_mask of delta and of nu (four fields)",
                    "max_delta",
                    "p1 and p99 of nu, plus the field sigma: nu99-nu1 in sigma units is derived from the three",
                    "count of pathological voxels (delta above the DESI maximum), for 4.2c",
                    "N_H1 at erosion k = 0, 1, 2, 3 IN ONE REGISTER, for 4.3a-b",
                    "the Box-Cox pass at eps in {0, 0.25, 0.5, 1.0} on the SAME 50 mocks as v1"
                ],
                "and_the_v1_counterparts_must_be_recomputed_where_missing": "all of SGC - no per-mock "
                            "one-point file exists for that hemisphere - plus max_delta and p1 in both. "
                            "Recomputing diagnostics from the frozen delta fields DOES NOT MODIFY v1: the "
                            "ensemble is immutable, its fields are not unreadable.",
                "why_this_is_blocking": "without it the v1 <-> v2 comparison is not like-for-like and none "
                            "of the six rules can be applied."
            }
        },
        "reason": (
            "Amendment 48 established that no threshold is crossed without the uncertainty of the "
            "quantity tested, declared when the rule is declared. Applying that to 4.2b before v2 runs "
            "showed something worse than a missing uncertainty: four of the six predictions named a "
            "starting number belonging to a different restriction, a different statistic, or a side of "
            "the comparison that the treatment cannot move. They are withdrawn here, before any "
            "measurement, and replaced by rules whose thresholds are derived from measured quantities."
        ),
        "evidence": (
            "Readings of 7 Sep 2026 from the frozen registers, by paper2_lettura_4_2b.py (selftest 15/15) "
            "and paper2_prominenza_v1.py (selftest 16/16). Box-Cox, results/revision/rev1_r14_monotone_testB.json: "
            "eps 0/0.25/0.5/1.0; DESI 28256, 28606, 28754, 29067 (shifts +350, +498, +811); mock means "
            "35445.64, 35574.64, 35570.16, 35262.32; paired mock shifts 0, +129.00+-4.194067724969716, "
            "+124.52+-7.077543676290236, -183.32+-11.124102898936275; deficit fractions 0.2028356661073125, "
            "0.19588785719265184, 0.191625789706878, 0.17569235376458497; spearman_vs_log at eps=1 "
            "0.996493001711132; n_mocks 50, provenance_gate pass on delta_0000..0004 against frozen_n 2000. "
            "The paired mean and SEM were recomputed from mock_beta1_max_per_eps and reproduce the stored "
            "summary. One-point, results/paper1/paper1_step6_{NGC,SGC}.json, restriction 'footprint pieno', "
            "n=200: var(delta) DESI 2.9166419506502494 / 4.815533379463941, mock mean 2918.4033877918614 / "
            "9960.076648189868, mock sd 649.2561203456237 / 1240.7348398428771, rank 0/200 both; "
            "var_ratio_delta 1000.6039264234059 / 2068.3226266616825; at field_r > P10, 3.6790744990465085 / "
            "8.101621625795236. nu kurtosis full footprint: DESI -0.43821476405642734 / -1.1351732307682145, "
            "mock 2.76384938163661+-0.47179461207878376 / 1.102669866717493+-0.2742501734015092, z "
            "-6.786987523202857 / -8.159860282784392, rank 0/200 both. P10 pair from "
            "results/paper1/rev_n4n5_report.json momenti.P10.agg.kurt: 3.902956198001257 +- "
            "0.5983209563067237 against 0.20448735601308332, z -6.181412840388943. Maximum delta, "
            "results/revision/rev1_r14_monotone_deltastats.json: median 3474.579833984375, min "
            "2417.17626953125, max 32244.41015625. Second implementation of the variance ratio, "
            "results/paper1/paper1_fkp_asymmetry_NGC.json onepoint_by_cut: 1084.8087651141557 at cut 0.0, "
            "359.93941192251486 at 1.0, 25.69156634091723 at 5.0, 3.569744963215932 at 10.0. Per-mock "
            "availability: sigma_in_mask and kurt_in_mask exist per realisation in "
            "results/paper1/n1_spectra_NGC.jsonl (delta) and n1b_spectra_NGC.jsonl (nu), NGC only, and the "
            "two files start at idx 0 and idx 200 respectively, so the realisations they cover must be "
            "checked before any rank is computed. Erosion ladder: per_mock_{NGC,SGC}_erosion_restrict.jsonl "
            "carry er0, er2, er3 and no er1; k=1 per realisation is only in "
            "results/paper2/fase3_mock.jsonl points.FID.N_H1_k1."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-50-regole-di-decisione-4-2b-4-3b",
            "amends_records": [48],
            "companion_document": "paper2_item4_2b_dichiarazione.md; checklist_paper2.md 4.2a, 4.2b, 4.3b; canovaccio_paper2.md Componente B",
            "a_withdrawn_prediction_is_not_a_repaired_one": "The four are removed with their reason and "
                "replaced before the measurement. None is reinterpreted after seeing a result, because no "
                "result exists yet: ensemble v2 has not run.",
            "the_thresholds_that_are_derived_are_marked_as_such": "4.2b-1 comes from the P10 cut measured "
                "on v1; 4.2b-5 comes from the measured paired sigma. The remaining two numeric thresholds "
                "- nu99-nu1 and the prominence of 4.3b - are deliberately NOT written, because the "
                "quantities they need do not exist in any register yet.",
            "what_this_does_not_do": "It does not touch ensemble v1, does not edit "
                "src/paper2_v1_reference.json, and reopens no deposited verdict. The two paper2_use "
                "strings in the reference are superseded by this record, not rewritten."
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
    atteso_file = ultimo.get("reference_file_sha256")
    atteso_self = ultimo.get("reference_self_sha256")
    if atteso_file and atteso_file != ref_file_sha:
        print(f"RIFIUTO: sha256 del reference cambiato: ultimo record {atteso_file[:12]}… "
              f"ricalcolato {ref_file_sha[:12]}…")
        return 2
    if atteso_self and atteso_self != ref_self_sha:
        print(f"RIFIUTO: self-digest del reference cambiato: ultimo record {str(atteso_self)[:12]}… "
              f"letto {str(ref_self_sha)[:12]}…")
        return 2

    rec = costruisci_record(n, ref_file_sha, ref_self_sha)
    linea = json.dumps(rec, ensure_ascii=False).encode("utf-8")

    print(f"ledger    : {os.path.abspath(args.ledger)}")
    print(f"record    : {n} -> {n + 1}")
    print(f"fine riga : {'CRLF' if eol == chr(13).encode() + chr(10).encode() else 'LF'} "
          f"(maggioranza: CRLF {crlf}, LF soli {lf})")
    print(f"ancore    : file {ref_file_sha[:12]}…  self {str(ref_self_sha)[:12]}…  concordi con il record {n}")
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
    if len(recs2) != n + 1:
        print(f"ERRORE: dopo l'append il ledger ha {len(recs2)} record")
        return 3
    if recs2[-1].get("item") != ITEM:
        print("ERRORE: il nuovo record non e' in ultima posizione")
        return 3
    if f"record {n + 1}." not in recs2[-1]["numbering_rule"]:
        print("ERRORE: numbering_rule incoerente con la posizione")
        return 3
    atteso_lf = lf + (1 if eol == b"\n" else 0)
    if lf2 != atteso_lf:
        print(f"ERRORE: righe a LF isolato da {lf} a {lf2}, atteso {atteso_lf}")
        return 3
    print(f"riletto   : {len(recs2)} record, ultimo item '{recs2[-1]['item']}', LF isolati {lf2} (attesi {atteso_lf})")
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

    base = tempfile.mkdtemp(prefix="amend50_")
    led = os.path.join(base, "ledger.jsonl")
    ref = os.path.join(base, "reference.json")

    with open(ref, "w", encoding="utf-8", newline="") as fh:
        json.dump({"_self_sha256": "s" * 64, "x": 1}, fh)
    ref_sha = sha256_file(ref)

    def scrivi_ledger(n, eol=b"\r\n", ultimo_ancorato=True):
        with open(led, "wb") as fh:
            for i in range(n):
                r = {"item": f"x{i}", "type": "protocol", "utc": "2026-01-01T00:00:00+00:00"}
                if i == n - 1 and ultimo_ancorato:
                    r["reference_file_sha256"] = ref_sha
                    r["reference_self_sha256"] = "s" * 64
                fh.write(json.dumps(r).encode("utf-8") + eol)

    class A:
        pass

    def args_append(attesi=49, dry=False, backup=None):
        a = A(); a.ledger = led; a.reference = ref; a.attesi = attesi
        a.dry_run = dry; a.backup = backup
        return a

    scrivi_ledger(49)
    prima = len(leggi_ledger(led)[1])
    ok("1 ledger sintetico a 49 record", prima == 49)
    ok("2 fine riga riconosciuta come CRLF", leggi_ledger(led)[2] == b"\r\n")

    ok("3 dry-run non scrive", cmd_append(args_append(dry=True)) == 0
       and len(leggi_ledger(led)[1]) == 49)

    ok("4 conteggio sbagliato: rifiuto", cmd_append(args_append(attesi=48)) == 2)

    bak = os.path.join(base, "bak.jsonl")
    raw_prima = open(led, "rb").read()
    ok("5 append: esito 0", cmd_append(args_append(backup=bak)) == 0)
    raw_dopo, recs_dopo, eol_dopo, crlf_dopo, lf_dopo = leggi_ledger(led)
    ok("6 il conteggio cambia davvero: 49 -> 50", prima == 49 and len(recs_dopo) == 50)
    ok("7 il nuovo record e' in ultima posizione", recs_dopo[-1]["item"] == ITEM)
    ok("8 numbering_rule dice 50", "record 50." in recs_dopo[-1]["numbering_rule"])
    ok("9 nessuna riga a LF introdotta", lf_dopo == 0 and crlf_dopo == 50)
    ok("10 il backup e' identico al prima", open(bak, "rb").read() == raw_prima)
    ok("11 le ancore sono quelle ricalcolate",
       recs_dopo[-1]["reference_file_sha256"] == ref_sha
       and recs_dopo[-1]["reference_self_sha256"] == "s" * 64)
    ok("12 i 49 record precedenti sono byte-identici", raw_dopo.startswith(raw_prima))

    ok("13 secondo append rifiutato per item duplicato",
       cmd_append(args_append(attesi=50)) == 2 and len(leggi_ledger(led)[1]) == 50)

    # reference cambiato -> rifiuto
    scrivi_ledger(49)
    with open(ref, "w", encoding="utf-8", newline="") as fh:
        json.dump({"_self_sha256": "s" * 64, "x": 2}, fh)
    ok("14 reference modificato: rifiuto sull'ancora", cmd_append(args_append()) == 2)

    # ultima riga senza a capo -> rifiuto
    with open(ref, "w", encoding="utf-8", newline="") as fh:
        json.dump({"_self_sha256": "s" * 64, "x": 1}, fh)
    scrivi_ledger(49)
    with open(led, "rb+") as fh:
        contenuto = fh.read().rstrip(b"\r\n")
        fh.seek(0); fh.truncate(); fh.write(contenuto)
    ok("15 ultima riga senza a capo: rifiuto", cmd_append(args_append()) == 2)

    # ledger a maggioranza LF -> l'append segue la maggioranza, non impone CRLF
    scrivi_ledger(49, eol=b"\n")
    ok("16 su ledger a LF l'append usa LF", leggi_ledger(led)[2] == b"\n"
       and cmd_append(args_append()) == 0
       and leggi_ledger(led)[3] == 0)

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
    p_a.add_argument("--attesi", type=int, default=49)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)

    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

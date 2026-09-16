#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend56.py — appende il record 56: 0.309 e 0.3168 sono medie su
domini diversi, e nessuno dei due entra in delta.

I cancelli sull'append si importano da paper2_append_amend50.

Uso:
    python paper2_append_amend56.py selftest
    python paper2_append_amend56.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 55 --dry-run
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

ITEM = "2.1-M/peso_fkp_domini_e_invarianza"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"
CRLF = chr(13).encode() + chr(10).encode()

QUOTATO_P1 = 0.309       # Paper 1 §7.2, tre decimali
GATE_21M = 0.3168        # cancello 2.1-M NGC, quattro decimali

# Misura del 8 settembre 2026, src/paper2_pesofkp_domini.py (selftest 14/14),
# results/paper2/pesofkp_domini_NGC.json. Ogni distanza sotto e' RICALCOLATA
# dal selftest, non riletta.
DOMINI = {
    "1_random_punti_media": 0.3167832832364633,
    "2_random_punti_mediana": 0.2943734299280938,
    "3_tabella_media_sui_bin": 0.3031051013313669,
    "4_tabella_interpolata_sui_random": 0.3099889615543192,
    "5_dati_punti_media": 0.30068181982748504,
    "6_voxel_in_maschera_media_semplice": 0.33191699959647386,
    "7_voxel_in_maschera_pesata_dal_conteggio": 0.3167826730785924,
    "8_galassie_mock_media_su_60_realizzazioni": 0.3090565805620197,
}


def ammesso(decimali):
    return 0.5 * 10.0 ** (-decimali)


def mezze_unita(valore, quotato, decimali):
    return abs(float(valore) - float(quotato)) / ammesso(decimali)


def delta_fkp(field_d, field_r, sum_wr):
    """delta = (n_g - alpha n_r)/(alpha n_r), con alpha = sum(w_d)/sum(w_r).
    Una implementazione sola, usata dal selftest per provare l'invarianza."""
    alpha = field_d.sum() / sum_wr
    return (field_d - alpha * field_r) / (alpha * field_r)


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "the_two_quoted_fkp_mean_weights_are_averages_over_different_domains_and_neither_enters_delta",
        "json_path": ("results/paper2/pesofkp_domini_NGC.json; "
                      "src/paper2_pesofkp_domini.py; src/paper1_rev_n6_fkp.py; "
                      "results/paper1/n6_fkp_NGC.jsonl; "
                      "results/paper1/n6_wfkp_table.npz; "
                      "checklist item 2.1-M; Paper 1 (MN-26-2388-P) §7.2"),
        "old_value": (
            "Checklist item 2.1-M carried an open thread: the mean in-mask FKP weight measured "
            "0.3168 (NGC) and 0.3308 (SGC) against the 0.309 quoted in Paper 1 §7.2, and the item "
            "recorded that the two hemispheres differing excludes 0.309 covering both. It added "
            "that this is the same weight that enters the v2 ensemble of 4.2a, and therefore had "
            "to be closed before Papers 3 and 4. The discrepancy was treated as a disagreement to "
            "be resolved, and as a possible obstacle to 4.2a."
        ),
        "new_value": {
            "i_neither_value_is_wrong_they_are_different_domains": {
                "method": "Eight averages, all of them legitimately callable 'the mean FKP "
                    "weight', measured in one pass over the NGC random catalogue (13,248,857 "
                    "points in z in [0.10, 0.40]), the data catalogue (217,614 points) and the "
                    "307,805 mask voxels. Tolerance declared before measuring: half a unit of the "
                    "last quoted digit, i.e. 0.0005 for 0.309 and 0.00005 for 0.3168.",
                "0.309_is_the_mean_over_MOCK_GALAXIES": {
                    "domain": "8_galassie_mock_media_su_60_realizzazioni",
                    "value": DOMINI["8_galassie_mock_media_su_60_realizzazioni"],
                    "half_units_from_0.309": mezze_unita(
                        DOMINI["8_galassie_mock_media_su_60_realizzazioni"], QUOTATO_P1, 3),
                    "source": "wfkp_mean per realisation in results/paper1/n6_fkp_NGC.jsonl, "
                              "i.e. the interpolated weight averaged over the mock galaxies that "
                              "receive it"},
                "0.3168_is_the_mean_over_the_RANDOM_CATALOGUE": {
                    "domains": ["1_random_punti_media",
                                "7_voxel_in_maschera_pesata_dal_conteggio"],
                    "values": [DOMINI["1_random_punti_media"],
                               DOMINI["7_voxel_in_maschera_pesata_dal_conteggio"]],
                    "half_units_from_0.3168": [
                        mezze_unita(DOMINI["1_random_punti_media"], GATE_21M, 4),
                        mezze_unita(DOMINI["7_voxel_in_maschera_pesata_dal_conteggio"],
                                    GATE_21M, 4)],
                    "the_two_agree_to": 6.10e-07,
                    "why_they_agree": "CIC conserves sums, and ALL 307,805 mask voxels contain "
                        "randoms, so the point average and the count-weighted voxel average are "
                        "the same number. Neither was guaranteed in advance; the agreement is a "
                        "check that passed."},
                "the_other_six": {k: DOMINI[k] for k in sorted(DOMINI)
                                  if k not in ("1_random_punti_media",
                                               "7_voxel_in_maschera_pesata_dal_conteggio",
                                               "8_galassie_mock_media_su_60_realizzazioni")},
                "the_simple_voxel_average_is_neither": "0.331917, far from both. The distinction "
                    "between the simple average of per-voxel ratios and the count-weighted one was "
                    "the hypothesis under test and it was needed to state the question precisely, "
                    "but the answer was not there."
            },
            "ii_what_is_actually_wrong_is_the_attribution_not_the_number": {
                "the_sentence": "Paper 1 §7.2 reads: we extract the radial FKP weight w_FKP(z) "
                    "from the random catalogue (mean in-mask weight 0.309), and voxelize the mock "
                    "galaxies with it.",
                "the_reading_it_invites": "That 0.309 is a property of the weight as extracted "
                    "from the random catalogue. Under that reading the correct figure is 0.3168, "
                    "and the quoted one is low by 2.52%.",
                "the_reading_under_which_it_is_true": "That 'in-mask weight' means the weight "
                    "carried by the objects being voxelized, i.e. the mock galaxies. Under that "
                    "reading 0.309 is right to 0.11 half-units.",
                "therefore": "The sentence is AMBIGUOUS, not false. The parenthetical is attached "
                    "to the wrong noun: it follows 'from the random catalogue' while describing "
                    "the mock galaxies. This distinction matters for how it is handled with the "
                    "journal - a clarification is not an erratum - and the record states it rather "
                    "than choosing.",
                "the_manuscript_is_submitted": "MN-26-2388-P. Like the beyond-two-point residual "
                    "of 5.3 and the corrected M26 Table-1 row, this touches a manuscript already "
                    "with the journal, and the channel is a decision, not a computation."
            },
            "iii_the_thread_did_not_block_4_2a_and_never_had": {
                "the_claim": "delta is EXACTLY invariant under a global rescaling of the mock "
                    "weights.",
                "the_argument": "With alpha = sum(w_d)/sum(w_r), sending w_d -> c*w_d sends "
                    "field_d -> c*field_d and alpha -> c*alpha, so delta = (n_g - alpha n_r) / "
                    "(alpha n_r) has numerator and denominator scaled by the same c. Only the "
                    "SHAPE of the weight in z enters the result; its mean does not.",
                "verified_numerically": "max|delta(c) - delta(1)| <= 3e-14 for c in "
                    "{0.9754, 7.3, 1e-4}, i.e. floating point. The selftest of this appender "
                    "recomputes it.",
                "consequence": "The 2.1-M thread was DOCUMENTARY, not physical. It does not gate "
                    "4.2a and never did, and the checklist statement that it must be closed before "
                    "Papers 3 and 4 is correct for the manuscript and wrong for the run.",
                "what_would_have_mattered_instead": "A difference in the SHAPE of w_FKP(z) between "
                    "what the pipeline applies and what the paper describes. That is a different "
                    "question and it is not raised by these measurements."
            },
            "iv_a_by_product_that_is_a_checkable_statement": {
                "measured": "Mock galaxies carry mean weight 0.309057, the data 0.300682: the "
                    "mocks are higher by 2.79%.",
                "what_it_means": "By the invariance above it does not move delta. But since "
                    "w_FKP is a monotone function of n(z), it is a statement about how closely the "
                    "mock radial selection reproduces the data one, and it has not been written "
                    "anywhere.",
                "not_pursued_here": True
            }
        },
        "reason": (
            "Item 2.1-M recorded a 2.5% disagreement between two quoted mean FKP weights and "
            "flagged it as gating the v2 ensemble. Measuring eight named averages in one pass "
            "showed that both numbers are correct and describe different populations: 0.309 the "
            "mock galaxies, 0.3168 the random catalogue. This is the third time in this series "
            "that a numerical disagreement dissolved into a difference of domain rather than an "
            "error - after the 313 against 445 dispersion and the max-delta median measured at "
            "n=100 under a heading declaring n=200. And the invariance of delta under a global "
            "rescaling of the weights removes the thread from the critical path of 4.2a "
            "altogether, which no document had established either way."
        ),
        "evidence": (
            "Run of 8 Sep 2026, src/paper2_pesofkp_domini.py (selftest 14/14), output "
            "results/paper2/pesofkp_domini_NGC.json. NGC only, and stated as such: 0.309 is an "
            "NGC figure - Paper 1 §7.2 describes the n6 test, and n6 like n10 has NGC in the body "
            "of the code - so the SGC value of 0.3308 has no published counterpart to disagree "
            "with. Domain 8 sits 0.113 half-units from 0.309; domains 1 and 7 sit 0.334 and 0.347 "
            "half-units from 0.3168 and agree with each other to 6.10e-07. The remaining five "
            "domains reproduce neither."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-56-peso-fkp-domini",
            "amends_records": [],
            "amends_no_prior_record": "No earlier record states either figure. What this closes is "
                "a checklist item, 2.1-M, and what it corrects is a sentence in a submitted "
                "manuscript.",
            "companion_document": ("src/paper2_pesofkp_domini.py; checklist item 2.1-M; "
                                   "paper2_stato.md voce Z-FKP"),
            "a_quoted_mean_needs_its_population_named": "'Mean in-mask weight' names a family, not "
                "a quantity: the average can be taken over random points, data points, table bins, "
                "mask voxels unweighted, or mask voxels weighted by count. Two of those differ by "
                "2.5% here and by a factor 2 in a constructed case. A quoted average without its "
                "population is not reproducible, and the third disagreement of this series to "
                "dissolve this way.",
            "before_declaring_a_thread_blocking_check_whether_the_quantity_enters_the_result": "The "
                "2.1-M thread was recorded as gating 4.2a for two weeks. One line of algebra, "
                "confirmed numerically in seconds, shows the mean weight cancels out of delta "
                "exactly. The cost of not checking was a false dependency in the plan.",
            "what_this_does_not_do": "It changes no threshold, runs no pass, does not touch the "
                "SGC value of 0.3308 (which has no published counterpart), and does not decide how "
                "the Paper 1 §7.2 sentence is handled with the journal."
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
    print(f"domini    : 0.309 -> galassie mock ({DOMINI['8_galassie_mock_media_su_60_realizzazioni']:.6f}); "
          f"0.3168 -> random ({DOMINI['1_random_punti_media']:.6f})")

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

    base = tempfile.mkdtemp(prefix="amend56_")
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

    def a(attesi=55, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    scrivi_ledger(55)
    raw_prima = open(led, "rb").read()
    ok("1 ledger sintetico a 55 record", len(leggi_ledger(led)[1]) == 55)
    ok("2 dry-run non scrive", cmd_append(a(dry=True)) == 0 and open(led, "rb").read() == raw_prima)
    ok("3 conteggio sbagliato: rifiuto", cmd_append(a(attesi=54)) == 2)
    ok("4 append: esito 0", cmd_append(a()) == 0)

    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("5 il conteggio cambia: 55 -> 56", len(recs2) == 56)
    ok("6 numbering_rule dice 56", "record 56." in recs2[-1]["numbering_rule"])
    ok("7 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 56)
    ok("8 i 55 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("9 secondo append rifiutato per item duplicato", cmd_append(a(attesi=56)) == 2)

    rec = recs2[-1]
    I = rec["new_value"]["i_neither_value_is_wrong_they_are_different_domains"]
    II = rec["new_value"]["ii_what_is_actually_wrong_is_the_attribution_not_the_number"]
    III = rec["new_value"]["iii_the_thread_did_not_block_4_2a_and_never_had"]
    IV = rec["new_value"]["iv_a_by_product_that_is_a_checkable_statement"]

    # --- le distanze sono RICALCOLATE dai valori, non rilette ---------------
    v8 = I["0.309_is_the_mean_over_MOCK_GALAXIES"]["value"]
    ok("10 il dominio 8 riproduce 0.309 entro mezza unita'",
       mezze_unita(v8, QUOTATO_P1, 3) <= 1.0)
    ok("11 la distanza dichiarata del dominio 8 e' quella vera",
       abs(I["0.309_is_the_mean_over_MOCK_GALAXIES"]["half_units_from_0.309"]
           - mezze_unita(v8, QUOTATO_P1, 3)) < 1e-9)
    v1, v7 = I["0.3168_is_the_mean_over_the_RANDOM_CATALOGUE"]["values"]
    ok("12 i domini 1 e 7 riproducono 0.3168 entro mezza unita'",
       mezze_unita(v1, GATE_21M, 4) <= 1.0 and mezze_unita(v7, GATE_21M, 4) <= 1.0)
    ok("13 l'accordo dichiarato fra 1 e 7 e' quello vero",
       abs(abs(v1 - v7) - I["0.3168_is_the_mean_over_the_RANDOM_CATALOGUE"]["the_two_agree_to"])
       < 1e-9)
    ok("14 il dominio 8 NON riproduce 0.3168 e viceversa",
       mezze_unita(v8, GATE_21M, 4) > 1.0 and mezze_unita(v1, QUOTATO_P1, 3) > 1.0)
    ok("15 nessuno degli altri sei riproduce alcuno dei due",
       all(mezze_unita(v, QUOTATO_P1, 3) > 1.0 and mezze_unita(v, GATE_21M, 4) > 1.0
           for v in I["the_other_six"].values()))
    ok("16 gli otto domini sono tutti nel record",
       len(I["the_other_six"]) == 5
       and len(I["0.3168_is_the_mean_over_the_RANDOM_CATALOGUE"]["values"]) == 2)

    # --- l'invarianza di delta, verificata e non asserita -------------------
    rng = np.random.default_rng(0)
    n_r = rng.random(2000) * 10 + 0.1
    n_g = rng.random(2000) * 3
    base_delta = delta_fkp(n_g, n_r, n_r.sum())
    peggio = max(float(np.abs(delta_fkp(c * n_g, n_r, n_r.sum()) - base_delta).max())
                 for c in (QUOTATO_P1 / GATE_21M, 7.3, 1e-4))
    ok("17 delta e' invariante per riscalamento globale dei pesi", peggio <= 1e-13)
    ok("18 il record dichiara la soglia che l'invarianza rispetta",
       "3e-14" in III["verified_numerically"] and peggio <= 3e-14)
    ok("19 il record dice che il filo NON blocca 4.2a",
       "does not gate 4.2a" in III["consequence"])

    # --- il sottoprodotto, ricalcolato --------------------------------------
    v5 = DOMINI["5_dati_punti_media"]
    ok("20 il +2.79% mock/dati e' quello vero",
       abs((v8 / v5 - 1) - 0.0279) < 5e-5 and "2.79%" in IV["measured"])

    # --- la distinzione ambiguo/falso, che e' il punto della sezione II -----
    ok("21 la sezione II dice AMBIGUOUS, non false", "AMBIGUOUS, not false" in II["therefore"])
    ok("22 e riporta il 2.52% della lettura sbagliata",
       "2.52%" in II["the_reading_it_invites"]
       and abs(GATE_21M / QUOTATO_P1 - 1 - 0.0252) < 5e-5)
    ok("23 il record non emenda nessun record precedente",
       rec["rules"]["amends_records"] == [])
    ok("24 il record dichiara di non toccare soglie ne' di far girare passate",
       "changes no threshold" in rec["rules"]["what_this_does_not_do"])
    ok("25 SGC e' escluso e la ragione e' scritta",
       "no published counterpart" in rec["evidence"])
    ok("26 i cancelli importati sono quelli del 50",
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
    p_a.add_argument("--attesi", type=int, default=55)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

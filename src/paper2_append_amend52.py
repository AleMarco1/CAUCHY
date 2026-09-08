#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend52.py — appende il record 52: l'inventario misurato di v1 e la regola
sui nomi dei campi.

Il record 50 punto viii elencava in prosa cosa v2 deve emettere. Questo record sostituisce
l'elenco con un inventario MISURATO di cosa v1 ha davvero, e registra il difetto trovato
verificandolo: il nome di un campo non identifica la grandezza.

I cancelli sull'append si importano da paper2_append_amend50.

Uso:
    python paper2_append_amend52.py selftest
    python paper2_append_amend52.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 51 --dry-run
"""

import argparse
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

ITEM = "4.2a/inventario_v1_e_nomi"
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"
CRLF = chr(13).encode() + chr(10).encode()


def costruisci_record(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM,
        "key": "a_field_name_is_not_an_identifier_of_the_quantity_and_the_v1_per_realisation_inventory_is_thinner_than_assumed",
        "json_path": ("src/paper2_contratto_4_2a.py; results/paper1/n1_spectra_NGC.jsonl; "
                      "results/paper1/n1b_spectra_NGC.jsonl; results/paper2/fase3_mock.jsonl; "
                      "record 50 point viii"),
        "old_value": (
            "Record 50 point viii listed, in prose, the per-mock fields ensemble v2 must emit, and "
            "stated that the v1 counterparts must be recomputed 'where missing' without saying where "
            "that is. The evidence block of record 50 asserted that sigma_in_mask and kurt_in_mask "
            "exist per realisation in n1_spectra_NGC.jsonl and n1b_spectra_NGC.jsonl without "
            "recording how many realisations each covers."
        ),
        "new_value": {
            "i_the_inventory_measured_not_assumed": {
                "delta_moments": "results/paper1/n1_spectra_NGC.jsonl, sigma_in_mask and "
                                 "kurt_in_mask, 50 realisations, idx from 0. FIFTY, not the full "
                                 "ensemble.",
                "nu_moments": "results/paper1/n1b_spectra_NGC.jsonl, same two names, 1800 "
                              "realisations, idx from 200.",
                "erosion_ladder": "results/paper2/fase3_mock.jsonl, points.FID.N_H1_k0..k3, 200 "
                                  "realisations per hemisphere after excluding the smoke records.",
                "absent_everywhere": "max delta, nu_p1, nu_p99 and the pathological-voxel count do "
                                     "not exist per realisation in either hemisphere.",
                "SGC": "no per-realisation one-point register exists at all. Every one-point number "
                       "for that hemisphere is an aggregate of paper1_step6_SGC.json.",
                "consequence_for_4_2b_1": "The secondary statistic of 4.2b-1 is the empirical rank "
                       "of Var(delta)_DESI among the mocks. On v2 it will have 2000; on v1 it would "
                       "have 50. The primary quantity R and its P10-derived threshold are "
                       "unaffected - they come from the n=200 aggregates of step6 - but the v1 "
                       "against v2 comparison of the RANK is not at equal n, and that is declared "
                       "rather than glossed."
            },
            "ii_the_defect_a_field_name_is_not_an_identifier": {
                "what_happened": "The first version of the contract checker credited "
                                 "n1b_spectra_NGC.jsonl with satisfying the DELTA fields, reporting "
                                 "'sigma_in_mask delta 1800/1800'. That file holds NU moments. The "
                                 "two registers use the same flat names for different quantities: "
                                 "sigma_in_mask is 56.953956604003906 at idx 0 in n1_spectra and "
                                 "2.101883888244629 at idx 200 in n1b_spectra; kurt_in_mask is "
                                 "1048.5986328125 against 2.710988998413086.",
                "why_it_is_worse_than_not_checking": "A verifier that credits a nu measurement to a "
                                 "delta field reports a satisfied contract that is not satisfied. "
                                 "The failure is silent and in the direction of proceeding.",
                "how_it_is_fixed": "Ambiguous flat names satisfy no field unless the side is "
                                 "DECLARED for that file (--lato-piatto). Without the declaration "
                                 "the checker names them and refuses. The v1 registers are not "
                                 "renamed: they are append-only outputs and the ambiguity is "
                                 "resolved at reading time.",
                "and_for_v2_the_names_carry_a_prefix": "delta.sigma_in_mask and nu.sigma_in_mask, so "
                                 "the ambiguity cannot recur. The flat spellings remain accepted "
                                 "only for re-reading v1."
            },
            "iii_the_third_instance_of_the_same_class": {
                "the_three": [
                    "small_scale_diagnostics.max_delta_mock: reads as a typical value, is the "
                    "maximum of the ensemble of per-mock maxima (record 50, point ii).",
                    "config_hash: the name promises an anchoring of the inputs that the field does "
                    "not provide (already on the register).",
                    "sigma_in_mask: the same name for two different quantities in two registers."
                ],
                "the_rule": "A field name is not an identifier of the quantity. Until a register "
                            "uses unambiguous names, the quantity is identified by the PAIR (file, "
                            "name), and any tool that reads across registers must be told which is "
                            "which rather than inferring it.",
                "where_it_bites_next": "Any cross-register join, and any contract check on v2 output."
            },
            "iv_the_contract_is_now_machine_checkable": {
                "what_exists": "src/paper2_contratto_4_2a.py holds the twelve fields of the 4.2a "
                               "output contract, the rule each one serves, and the frozen v1 values "
                               "that whoever produces them must reproduce: NGC idx 0 "
                               "sigma_in_mask 56.953956604003906, kurt_in_mask 1048.5986328125, "
                               "N_H1_k0 35318; NGC idx 200 nu sigma_in_mask 2.101883888244629, "
                               "kurt_in_mask 2.710988998413086.",
                "it_verifies_and_does_not_compute": "By construction it recomputes none of the "
                               "quantities: a checker that computed them would become a second "
                               "implementation of what the pipeline defines.",
                "nu99_minus_nu1_is_not_a_field": "It is derived from nu_p99, nu_p1 and "
                               "nu_sigma_in_mask. Depositing it as its own field would create the "
                               "second implementation the variance-ratio case already showed "
                               "(1084.81 against 1000.60).",
                "how_it_is_used": "On a v2 smoke run of a few realisations BEFORE committing the "
                               "~16 hours of TDA, and on the full output afterwards. Float32 "
                               "registers require --tolleranza-relativa 1e-5; at 1e-6 a correct "
                               "value fails, which the selftest demonstrates on a boundary case."
            }
        },
        "reason": (
            "Turning the prose specification of record 50 into a machine-checked contract did two "
            "things that prose could not. It measured the v1 inventory, which is thinner than the "
            "record assumed - fifty realisations for the delta moments, none at all for four of the "
            "twelve fields, and nothing per realisation for SGC. And it exposed a defect in the "
            "checker itself: it credited a nu register with satisfying the delta fields, because it "
            "treated a field name as an identifier of a quantity. Both are recorded here, the second "
            "as a rule."
        ),
        "evidence": (
            "Runs of 7 Sep 2026, src/paper2_contratto_4_2a.py (selftest 19/19). "
            "n1_spectra_NGC.jsonl: 50 rows, index 'idx', delta moments 50/50 with --lato-piatto "
            "delta, ten of twelve contract fields absent. n1b_spectra_NGC.jsonl: 1800 rows, index "
            "'idx' starting at 200, nu moments 1800/1800 with --lato-piatto nu and correctly NOT "
            "credited to delta, ten of twelve fields absent. fase3_mock.jsonl filtered by region "
            "and without the smoke records: 1000 rows, 200 realisations, points.FID.N_H1_k0..k3 at "
            "200/200 and the eight one-point fields absent. Before the fix the same call on "
            "n1b_spectra reported 'sigma_in_mask delta 1800/1800'; after it, the flat names resolve "
            "only on the declared side, and with no declaration the checker names the ambiguous "
            "keys and satisfies nothing."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-52-inventario-v1-e-nomi-dei-campi",
            "amends_records": [50],
            "companion_document": "paper2_item4_2b_dichiarazione.md sezione 1; src/paper2_contratto_4_2a.py",
            "a_specification_in_prose_is_not_a_specification": "Record 50 point viii was correct and "
                "unverifiable. What made it usable was running it against the registers and getting "
                "back a list of what is missing, with the rule each absence disables.",
            "what_this_does_not_do": "It does not produce any of the missing fields, does not touch "
                "ensemble v1, and does not change any threshold declared in records 50 and 51. The "
                "only quantitative consequence is the declared inequality of n for the rank "
                "statistic of 4.2b-1."
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

    base = tempfile.mkdtemp(prefix="amend52_")
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

    def a(attesi=51, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    scrivi_ledger(51)
    raw_prima = open(led, "rb").read()
    ok("1 ledger sintetico a 51 record", len(leggi_ledger(led)[1]) == 51)
    ok("2 dry-run non scrive", cmd_append(a(dry=True)) == 0 and open(led, "rb").read() == raw_prima)
    ok("3 conteggio sbagliato: rifiuto", cmd_append(a(attesi=50)) == 2)
    ok("4 append: esito 0", cmd_append(a()) == 0)

    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("5 il conteggio cambia: 51 -> 52", len(recs2) == 52)
    ok("6 numbering_rule dice 52", "record 52." in recs2[-1]["numbering_rule"])
    ok("7 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 52)
    ok("8 i 51 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("9 secondo append rifiutato per item duplicato", cmd_append(a(attesi=52)) == 2)

    rec = recs2[-1]
    inv = rec["new_value"]["i_the_inventory_measured_not_assumed"]
    ok("10 l'inventario dichiara i tre conteggi",
       "50 realisations" in inv["delta_moments"]
       and "1800 realisations" in inv["nu_moments"]
       and "200 realisations" in inv["erosion_ladder"])
    ok("11 i due valori che dimostrano l'ambiguita' sono nel record",
       "56.953956604003906" in rec["new_value"]["ii_the_defect_a_field_name_is_not_an_identifier"]["what_happened"]
       and "2.101883888244629" in rec["new_value"]["ii_the_defect_a_field_name_is_not_an_identifier"]["what_happened"])
    ok("12 la terza istanza elenca tre casi",
       len(rec["new_value"]["iii_the_third_instance_of_the_same_class"]["the_three"]) == 3)
    ok("13 il record non tocca le soglie di 50 e 51",
       "does not change any threshold" in rec["rules"]["what_this_does_not_do"])
    ok("14 i cancelli importati sono quelli del 50",
       sys.modules["paper2_append_amend50"].sha256_file is sha256_file)
    ok("15 il record e' ancorato al reference",
       rec["reference_file_sha256"] == ref_sha and rec["reference_self_sha256"] == "s" * 64)

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
    p_a.add_argument("--attesi", type=int, default=51)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

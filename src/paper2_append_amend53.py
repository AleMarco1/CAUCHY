#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend53.py — appende il record 53: la cache dei delta e' manifestata, e il
record 52 va corretto su un punto.

I cancelli sull'append si importano da paper2_append_amend50.

Uso:
    python paper2_append_amend53.py selftest
    python paper2_append_amend53.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --attesi 52 --dry-run
"""

import argparse
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

ITEM = "4.2a/cache_delta_manifestata"
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
        "key": "the_fields_tier_does_not_freeze_the_mock_delta_cache_which_is_now_manifested_instead",
        "json_path": ("results/paper2/cachedelta_manifest_{NGC,SGC}.jsonl; "
                      "results/paper2/cachedelta_header_{NGC,SGC}.json; "
                      "src/paper2_manifest_cache.py; results/paper2/ensemble_v1_manifest_fields.jsonl; "
                      "src/paper2_contratto_4_2a.py; record 52"),
        "old_value": (
            "The freeze was assumed to cover the inputs of the v1 baseline. It does not: the tier "
            "named `fields` holds 2202 files of results/phase8_test2_fields/test2_NNNN.npz, and its "
            "manifest contains neither the string paper1_mock_deltas nor the string SGC. The 4000 "
            "mock delta fields on which Paper 1 and the v1 baseline of four of the six rules rest "
            "were manifested nowhere. Record 52 also stated that no per-realisation one-point "
            "register exists for SGC - true - in a context that suggested the DATA were missing."
        ),
        "new_value": {
            "i_what_the_fields_tier_actually_holds": {
                "measured": "results/phase8_test2_fields/test2_NNNN.npz, 2202 files, 18,472,477,342 "
                            "bytes. Also 128^3 float32, which is why the count and the mean size "
                            "looked like a delta cache from the outside.",
                "the_fourth_instance": "A tier called `fields` that does not contain the fields the "
                            "analysis runs on. Fourth case today of a name promising what the "
                            "content does not give, after max_delta_mock (an ensemble extremum), "
                            "config_hash (not an anchoring of the inputs) and sigma_in_mask (two "
                            "quantities, one name). The rule of record 52 stands and is extended "
                            "from field names to TIER names."
            },
            "ii_the_delta_cache_is_now_manifested_not_frozen": {
                "what_was_produced": "A register in the same shape as the freeze manifests - rel, "
                            "bytes, mtime_utc, sha256, scanned_at - deliberately NOT a tier. "
                            "src/paper2_manifest_cache.py refuses to write on any name beginning "
                            "with ensemble_v1_manifest_ or ensemble_v1_freeze_, because such a file "
                            "would be discovered by paper2_freeze_verify as a tier that does not "
                            "exist.",
                "NGC": {"root": "data/processed/paper1_mock_deltas/NGC", "n_files": 2000,
                        "total_bytes": 16777472000, "aggregate_prefix": "631b0703fe3b",
                        "verify": "OK 2000, MISMATCH 0, MISSING 0, EXTRA 0"},
                "SGC": {"root": "data/processed/paper1_mock_deltas/SGC", "n_files": 2000,
                        "total_bytes": 16777472000, "aggregate_prefix": "92cb5e8dd26c",
                        "verify": "OK 2000, MISMATCH 0, MISSING 0, EXTRA 0"},
                "and_every_file_has_the_size_it_must": "16,777,472,000 / 2000 = 8,388,736 bytes "
                            "exactly, in BOTH hemispheres: 128^3 float32 plus the 128-byte npy "
                            "header, with no file deviating. Across 33.55 GB written in different "
                            "sessions, no truncated or half-written field exists. This is the first "
                            "thing the manifest establishes and it was not known before.",
                "the_aggregate_carries_its_recipe": "The header declares aggregate_recipe and "
                            "is_freeze_tier: false. It is NOT asserted to equal the aggregate rule "
                            "of paper2_freeze_verify, which is a different implementation and is not "
                            "guessed at - the same discipline that the variance-ratio case imposed.",
                "why_manifested_and_not_frozen": "The cache is regenerable from the catalogues in "
                            "about two hours per hemisphere, so freezing 33.55 GB is arguable. But "
                            "the regeneration is NOT known to be bit-identical - the register "
                            "already carries the falsified prediction that raising the resolution "
                            "would restore bit identity, with the finding that the convergence of a "
                            "quantity does not make its rounding converge. A manifest settles the "
                            "question under either reading: if the cache is an intermediate, it says "
                            "which intermediate; if it is primary, it identifies it.",
                "after_adding_the_two_files_the_freeze_is_still_CLEAN": "Five tiers, 34836 files, "
                            "unchanged. The two new registers live in results/paper2 and are not "
                            "discovered as tiers."
            },
            "iii_correction_to_record_52": {
                "what_record_52_left_implied": "That producing the SGC one-point numbers required "
                            "regenerating a cache, at roughly two hours per hemisphere.",
                "what_is_true": "Both delta caches exist and are complete: 2000 fields per "
                            "hemisphere. What is missing is a PASS that was never run, not the data. "
                            "The same holds for the n=50 of the NGC delta moments: the 2000 fields "
                            "were there and the pass was made on fifty.",
                "the_revised_cost": "Measured on a synthetic 128^3 float32 field: log plus "
                            "smoothing at sigma_px 0.320 with a one-voxel kernel, 50 ms; in-mask "
                            "extraction, 1 ms; variance, kurtosis, p1, p99 and maximum, 30 ms; "
                            "total 81 ms per field, so 2.7 minutes per 2000 single-threaded, plus "
                            "12.4 ms per field for the sha256. The pass is bound by disk, not by "
                            "arithmetic: about ten minutes per hemisphere against the ~14 hours of "
                            "TDA that none of these quantities requires. The figure is an order of "
                            "magnitude measured off the production code path, not a prediction "
                            "about it.",
                "the_operational_consequence": "The one-point diagnostics must be COMPUTED INSIDE "
                            "the 4.2a cache pass, where each v2 field is already in memory. Run "
                            "afterwards as a separate pass they would re-read 16.8 GB per hemisphere "
                            "for nothing. The v1 pass has no such option and pays the read once."
            },
            "iv_the_contract_gains_a_thirteenth_field": {
                "field": "delta_sha256, per record: the digest of the delta field the record was "
                         "computed from.",
                "why": "With the cache outside the freeze, this is what makes a number traceable to "
                       "an identified input. If a field changes between the v1 pass and the v2 pass, "
                       "the comparison notices instead of attributing the difference to the "
                       "reweighting.",
                "and_it_is_a_cross_check_not_an_isolated_digest": "It is verified against "
                       "cachedelta_manifest_{NGC,SGC}.jsonl, so an unmanifested field cannot enter "
                       "the baseline unnoticed.",
                "cost": "12.4 ms per field, 0.8 minutes over all 4000."
            }
        },
        "reason": (
            "Asking how long the missing quantities would take produced two answers that neither "
            "the checklist nor record 52 contained. The runs are minutes, not hours, because none of "
            "the four needs persistent homology and both delta caches already exist. And the inputs "
            "of the v1 baseline are not covered by the freeze at all, because the tier named `fields` "
            "holds something else. The first changes a plan; the second changes what the numbers of "
            "the baseline can be traced to, and is why the cache is manifested here."
        ),
        "evidence": (
            "Runs of 7 Sep 2026, src/paper2_manifest_cache.py (selftest 20/20). "
            "Select-String on results/paper2/ensemble_v1_manifest_fields.jsonl returns 0 for both "
            "'paper1_mock_deltas' and 'SGC'; its first body entries are "
            "results/phase8_test2_fields/test2_0000.npz and test2_0001.npz, 8,388,872 bytes each. "
            "Get-ChildItem on data/processed/paper1_mock_deltas gives NGC 2000 and SGC 2000 fields. "
            "Scan: NGC 2000 files, 16,777,472,000 bytes, aggregate 631b0703fe3b...; SGC 2000 files, "
            "16,777,472,000 bytes, aggregate 92cb5e8dd26c... - full values in "
            "results/paper2/cachedelta_header_{NGC,SGC}.json. Verify on both: OK 2000, MISMATCH 0, "
            "MISSING 0, EXTRA 0. paper2_freeze_verify after the two new registers: CLEAN, five "
            "tiers, 34836 files, amendments disco 52 documentati 52."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": f"The number of an amendment is its 1-based POSITION in this file. This is record {numero}.",
        "rules": {
            "marker": "emendamento-53-cache-delta-manifestata",
            "amends_records": [52],
            "companion_document": "src/paper2_manifest_cache.py; src/paper2_contratto_4_2a.py; consegna di fine sessione",
            "a_name_is_not_a_guarantee_of_content_at_any_level": "Four cases today: a constant "
                "(max_delta_mock), a field (config_hash), a column shared by two registers "
                "(sigma_in_mask) and now a TIER (fields). The check is the same in all four: read "
                "what is inside before relying on what it is called.",
            "manifesting_is_not_freezing_and_the_difference_is_declared": "The cache carries a "
                "digest per file and an aggregate with a stated recipe, and it is not a tier. "
                "Promoting it later requires no rework, because the shape is already the one "
                "paper2_freeze_verify reads.",
            "what_this_does_not_do": "It does not freeze the cache, does not change any threshold of "
                "records 50 and 51, and does not run any pass. It records what the inputs are and "
                "what the pass will cost."
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
          f"--file src\\paper2_freeze_verify.py --da {n} --a {n + 1} "
          f"--ledger src\\paper2_v1_amendments.jsonl")
    print("  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="amend53_")
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

    def a(attesi=52, dry=False, backup=None):
        x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
        x.dry_run = dry; x.backup = backup
        return x

    scrivi_ledger(52)
    raw_prima = open(led, "rb").read()
    ok("1 ledger sintetico a 52 record", len(leggi_ledger(led)[1]) == 52)
    ok("2 dry-run non scrive", cmd_append(a(dry=True)) == 0 and open(led, "rb").read() == raw_prima)
    ok("3 conteggio sbagliato: rifiuto", cmd_append(a(attesi=51)) == 2)
    ok("4 append: esito 0", cmd_append(a()) == 0)

    raw2, recs2, eol2, crlf2, lf2 = leggi_ledger(led)
    ok("5 il conteggio cambia: 52 -> 53", len(recs2) == 53)
    ok("6 numbering_rule dice 53", "record 53." in recs2[-1]["numbering_rule"])
    ok("7 nessun LF isolato introdotto", lf2 == 0 and crlf2 == 53)
    ok("8 i 52 record precedenti sono byte-identici", raw2.startswith(raw_prima))
    ok("9 secondo append rifiutato per item duplicato", cmd_append(a(attesi=53)) == 2)

    rec = recs2[-1]
    cache = rec["new_value"]["ii_the_delta_cache_is_now_manifested_not_frozen"]
    ok("10 i due emisferi hanno 2000 campi ciascuno",
       cache["NGC"]["n_files"] == 2000 and cache["SGC"]["n_files"] == 2000)
    ok("11 la dimensione per campo torna: 128^3 float32 + intestazione npy",
       cache["NGC"]["total_bytes"] // cache["NGC"]["n_files"] == 128 ** 3 * 4 + 128
       and cache["SGC"]["total_bytes"] // cache["SGC"]["n_files"] == 128 ** 3 * 4 + 128)
    ok("12 i due aggregati sono diversi",
       cache["NGC"]["aggregate_prefix"] != cache["SGC"]["aggregate_prefix"])
    ok("13 il record dichiara di non congelare la cache",
       "does not freeze the cache" in rec["rules"]["what_this_does_not_do"])
    ok("14 corregge il 52 e lo dichiara", rec["rules"]["amends_records"] == [52])
    ok("15 i cancelli importati sono quelli del 50",
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
    p_a.add_argument("--attesi", type=int, default=52)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

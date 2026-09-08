#!/usr/bin/env python3
"""
CAUCHY / Paper 2 — append del record 14 del file degli emendamenti.

COSA REGISTRA
  Il lato mock NON riproduce l'ensemble v1 bit a bit, e non e' un difetto: e'
  una conseguenza necessaria dell'iniezione della tabella D_C, che il protocollo
  depositato impone al §7. Il record fissa il meccanismo, la decisione di NON
  toccare la tabella, la riformulazione del cancello D4a, e tre predizioni
  smentite in sequenza durante la diagnosi.

  Come il 13, `type` e' "protocol": emenda cio' che il §7 puo' affermare, non un
  valore del reference set.

CANCELLI, prima di scrivere
  1. reference vivo con _self_sha256 = 865aa2ef... e byte = 332939bc...
  2. il file degli emendamenti ha esattamente 13 righe non vuote
  3. nessun record con item "3.2/D4" gia' presente

Uso:
    python src\\paper2_append_amend14.py selftest
    python src\\paper2_append_amend14.py --dry-run
    python src\\paper2_append_amend14.py --apply
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REF_REL = "src/paper2_v1_reference.json"
AM_REL = "src/paper2_v1_amendments.jsonl"

EXPECT_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"
EXPECT_FILE_SHA = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
EXPECT_LINES_BEFORE = 13
EXPECT_LINES_AFTER = 14
ITEM = "3.2/D4"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def self_digest(ref_path: Path) -> str:
    o = json.loads(ref_path.read_text(encoding="utf-8"))
    payload = {k: v for k, v in o.items() if k != "_self_sha256"}
    return sha256_bytes(json.dumps(payload, indent=2, sort_keys=True,
                                   ensure_ascii=False).encode())


def build_record(utc: str) -> dict:
    return {
        "type": "protocol",
        "item": ITEM,
        "utc": utc,
        "document": ("paper2_prereg_v1.md v1.1 — version DOI "
                     "10.5281/zenodo.22148444"),
        "json_path": "prereg §7 (mandatory procedure); prereg §8 (not covered)",
        "key": "mock_side_reproducibility / dc_table_resolution / gate_D4a",

        "old_value": (
            "§7 prescribes the injection sequence, including "
            "set_geometry(z_tab=, dc_tab=), without stating what the injection "
            "does to the mock side. Gate D4a, as first drafted for Phase 3, "
            "required the re-computed mock delta field to be BIT-IDENTICAL to "
            "the frozen v1 arrays in data/processed/paper1_mock_deltas/."),

        "new_value": {
            "a_mechanism": (
                "set_geometry(dc_tab=...) replaces comoving_distance with a "
                "linear interpolation on the injected table. This perturbs the "
                "comoving positions of BOTH catalogues, hence field_r, which is "
                "the DENOMINATOR of delta: the difference is therefore spread "
                "over the whole mask, not confined to where the numerator "
                "changes. Verified: with the native comoving_distance the mock "
                "delta is bit-identical to v1 and the derived cube side is "
                "exactly the frozen 1997.3629167166155; with any injected "
                "table it is not."),
            "b_table_unchanged": (
                "The D_C table STAYS at 4001 nodes. Measured over four "
                "resolutions (4001, 10001, 40001, 100001): the cube side "
                "converges as N^-2, from 2.857e-9 to 4.682e-12 relative, but "
                "the delta field does NOT converge — differing cells go 243010 "
                "-> 196946 -> 184609 -> 183752 and saturate, because field_r "
                "itself flips in the last bit of float32. N_H1 is IDENTICAL at "
                "every resolution: 28256 on the data side and 35318 on mock 0. "
                "Raising the resolution would therefore change no observable, "
                "while touching a constant cited in item 0.5, in gate 2.1-D2 "
                "and in this deposited document. It is not done."),
            "c_gate_D4a_reformulated": {
                "D4a-det": (
                    "DETERMINISM: the same mock computed twice through the same "
                    "path must give a bit-identical delta. A failure here is a "
                    "genuine defect (uncontrolled state), and it is the check "
                    "the bit-identity formulation did not contain. PASSED."),
                "D4a-stab": (
                    "STABILITY against v1, on the quantity that enters the "
                    "filtration and in units derived from it: "
                    "max|dnu| < (nu_max - nu_min)/N_THRESH, i.e. below one "
                    "filtration level spacing. The comparison is on nu and not "
                    "on delta, because nu is what is filtered and it is "
                    "computed after smoothing at sigma_px, which attenuates a "
                    "cell-scale perturbation. Measured on three realisations: "
                    "0.0054, 0.0057, 0.0018 level spacings. PASSED."),
                "why_not_delta": (
                    "A relative criterion on delta is meaningless: delta "
                    "crosses zero, and the cell of largest relative difference "
                    "has delta = -2.19e-6, i.e. noise over noise. An absolute "
                    "criterion on delta requires an invented number.")
            },
            "d_fiducial_mocks_recomputed": (
                "The 200 fiducial mocks are RECOMPUTED in the Phase-3 path and "
                "not reused from the frozen cache. Since field_r changes under "
                "injection, reusing the frozen fiducial while computing the "
                "deformed points anew would be two paths for the same quantity "
                "— the defect class that produced the 445/313 discrepancy in "
                "Paper 1. Cost: about two hours out of twenty."),
            "e_observable_unaffected": (
                "N_H1 at the fiducial reproduces the frozen per-mock values "
                "exactly on 2 of 3 smoke realisations and differs by 1 "
                "generator out of ~35000 on the third. That is the tie-breaking "
                "scale the reference already declares: tied_groups = 4272, "
                "tie_breaking_shift_generators = 3. Gate D4b therefore admits "
                "up to 3 generators, while printing whether the match was "
                "exact.")
        },

        "reason": (
            "The mock side is the side that carries the measurement of dD/dfid, "
            "and a gate that demands something unattainable would either be "
            "silently relaxed later or would block a correct pipeline. The "
            "mechanism is now identified, measured across four table "
            "resolutions, and shown not to touch any observable. What the §7 "
            "procedure can claim about mock-side reproducibility is therefore "
            "stated here explicitly, before the twenty-hour run rather than "
            "after it."),

        "evidence": (
            "results/paper2/tabres_probe.jsonl, five processes (native plus "
            "four resolutions), each injecting once from the native "
            "comoving_distance. Native: L = 1997.3629167166155 at rel 0, mask "
            "identical, delta bit-identical, N_H1 28256 / 35318. Injected: mask "
            "identical and N_H1 unchanged at every resolution, delta never "
            "bit-identical. Absolute max|d_delta| at 4001 nodes: 2.93e-3, "
            "2.20e-3, 1.46e-3 on mocks 0-2; median difference 3 ULP of float32 "
            "with 17555 cells beyond 16 ULP, i.e. a real perturbation with "
            "tails, not pure rounding."),

        "falsified_predictions": [
            {"claim": "The derived cube was the cause of the mock-side mismatch.",
             "outcome": ("Wrong. The cube was a symptom. With the native "
                         "comoving_distance, derive_box returns exactly the "
                         "frozen 1997.3629167166155 and the delta is "
                         "bit-identical; the two values recorded in item 0.5 "
                         "are one quantity computed two ways, not two "
                         "versions.")},
            {"claim": ("Raising the table resolution would restore "
                       "bit-identity, since linear interpolation error scales "
                       "as N^-2."),
             "outcome": ("Wrong. The cube side does converge as N^-2 over three "
                         "orders, but the differing-cell count saturates at "
                         "~184000 and the delta difference does not converge: "
                         "field_r flips in float32 under an arbitrarily small "
                         "perturbation. Convergence of a quantity does not make "
                         "its bit pattern converge.")},
            {"claim": "|delta - v1| <= 1e-3 in absolute value.",
             "outcome": ("Wrong: 2.93e-3, 2.20e-3, 1.46e-3. The threshold was "
                         "calibrated on the 4.88e-4 measured at 100001 nodes "
                         "and applied to the production path at 4001 nodes, "
                         "where the perturbation is 3-6 times larger. Same "
                         "error class as gate 2.2a, whose threshold was set "
                         "with a fixed mask and applied after 2.1-M made the "
                         "mask mobile. Replaced by a criterion derived from the "
                         "filtration, not chosen.")}
        ],

        "numbering_rule": (
            "The number of an amendment is its 1-based POSITION in this file. "
            "This is record 14."),

        "reference_file": REF_REL,
        "reference_file_sha256": EXPECT_FILE_SHA,
        "reference_self_sha256": EXPECT_SELF_SHA,
    }


def gates(base: Path, *, strict: bool = True) -> list:
    fails = []
    ref, am = base / REF_REL, base / AM_REL
    if not ref.is_file():
        return [f"reference assente: {ref}"]
    o = json.loads(ref.read_text(encoding="utf-8"))
    recorded, recomputed = o.get("_self_sha256"), self_digest(ref)
    if recorded != recomputed:
        fails.append(f"cancello del self-digest rotto: {recorded} != {recomputed}")
    if strict and recomputed != EXPECT_SELF_SHA:
        fails.append(f"self-digest inatteso: {recomputed}")
    if strict and sha256_bytes(ref.read_bytes()) != EXPECT_FILE_SHA:
        fails.append("sha256 dei byte del reference inatteso")
    if not am.is_file():
        return fails + [f"file degli emendamenti assente: {am}"]
    lines = [l for l in am.read_text(encoding="utf-8").splitlines() if l.strip()]
    if strict and len(lines) != EXPECT_LINES_BEFORE:
        fails.append(f"righe non vuote = {len(lines)}, attese {EXPECT_LINES_BEFORE}")
    for i, l in enumerate(lines, 1):
        try:
            r = json.loads(l)
        except Exception as exc:
            fails.append(f"riga {i} malformata: {str(exc)[:60]}")
            continue
        if isinstance(r, dict) and r.get("item") == ITEM:
            fails.append(f"un record con item {ITEM} esiste gia' alla riga {i}")
    return fails


def append_atomic(am: Path, line: str) -> None:
    data = (line + "\n").encode("utf-8")
    with open(am, "ab") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    try:
        dfd = os.open(str(am.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except (OSError, AttributeError):
        pass


def cmd_run(a) -> int:
    base = Path(a.base).resolve()
    fails = gates(base)
    print(f"base: {base}")
    print(f"cancelli: {'OK' if not fails else 'FALLITI'}")
    for f in fails:
        print(f"  [FATAL] {f}")
    if fails:
        return 2
    rec = build_record(datetime.now(timezone.utc)
                       .strftime("%Y-%m-%dT%H:%M:%S+00:00"))
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    print(f"\nrecord {EXPECT_LINES_AFTER}: {len(line)} byte, "
          f"sha256 {sha256_bytes(line.encode())[:16]}…")
    if not a.apply:
        print("\n--- riga che verrebbe appesa ---")
        print(line)
        print("\n(dry-run: nulla e' stato scritto. Rilanciare con --apply)")
        return 0
    am = base / AM_REL
    append_atomic(am, line)
    lines = [l for l in am.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = len(lines) == EXPECT_LINES_AFTER and json.loads(lines[-1])["item"] == ITEM
    print(f"\nappeso. righe ora: {len(lines)} (attese {EXPECT_LINES_AFTER}) "
          f"-> {'OK' if ok else 'CONTROLLARE A MANO'}")
    print("\nOra:  python src\\paper2_freeze_verify.py verify --jobs 4 "
          "--out logs\\fv.jsonl   -> CLEAN con disco=14")
    return 0 if ok else 1


def cmd_selftest(a) -> int:
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    tmp = Path(tempfile.mkdtemp(prefix="amend14_"))
    try:
        (tmp / "src").mkdir()
        ref, am = tmp / REF_REL, tmp / AM_REL
        payload = {"schema": "test", "x": 1}
        o = dict(payload)
        o["_self_sha256"] = sha256_bytes(json.dumps(
            payload, indent=2, sort_keys=True, ensure_ascii=False).encode())
        ref.write_text(json.dumps(o, indent=2), encoding="utf-8")
        am.write_text("".join('{"a":1}\n' for _ in range(13)), encoding="utf-8")

        expect("1. albero sano -> nessun fallimento", not gates(tmp, strict=False))
        am.write_text("".join('{"a":1}\n' for _ in range(12)), encoding="utf-8")
        expect("2. tredici righe attese, dodici trovate -> ferma",
               any("righe non vuote" in x for x in gates(tmp, strict=True)))
        am.write_text("".join('{"a":1}\n' for _ in range(13)), encoding="utf-8")
        append_atomic(am, json.dumps({"item": ITEM}))
        expect("3. record gia' presente -> doppione, ferma",
               any("esiste gia'" in x for x in gates(tmp, strict=False)))

        rec = build_record("2026-01-01T00:00:00+00:00")
        line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        rt = json.loads(line)
        expect("4. JSON valido, due ancore, type protocol",
               rt["reference_file_sha256"] == EXPECT_FILE_SHA
               and rt["reference_self_sha256"] == EXPECT_SELF_SHA
               and rt["type"] == "protocol")
        expect("5. registra TRE predizioni smentite",
               len(rt["falsified_predictions"]) == 3
               and all("outcome" in f for f in rt["falsified_predictions"]))
        expect("6. dichiara che la tabella NON si tocca",
               "STAYS at 4001" in rt["new_value"]["b_table_unchanged"])
        expect("7. e che i fiduciali si ricalcolano",
               "RECOMPUTED" in rt["new_value"]["d_fiducial_mocks_recomputed"])
        expect("8. nessun a capo dentro la riga", "\n" not in line)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=".")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    a = p.parse_args()
    return cmd_selftest(a) if a.cmd == "selftest" else cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())

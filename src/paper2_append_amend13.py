#!/usr/bin/env python3
"""
CAUCHY / Paper 2 — append del record 13 del file degli emendamenti.

COSA REGISTRA
  Il primo emendamento che non tocca il reference set ma il PROTOCOLLO depositato
  (paper2_prereg_v1.md v1.1, version DOI 10.5281/zenodo.22148444), §4 e §7.
  Fissa le tre convenzioni che il §4 lascia libere: quale box e' il fiduciale,
  come si costruisce il cubo a ogni punto, e cosa si fa delle posizioni fuori dal
  cubo di embedding. `type` e' "protocol", non "amendment", ma l'ancora al
  reference e' pretesa lo stesso da paper2_freeze_verify.py.

PERCHE' UNO SCRIPT E NON UNA RIGA A MANO
  Il file e' append-only e un record scritto male non si toglie. I tre cancelli
  qui sotto costano millisecondi e rendono impossibile appendere su un albero che
  non e' quello per cui il record e' stato scritto.

CANCELLI, prima di scrivere
  1. il reference vivo ha _self_sha256 = 865aa2ef... e sha256 dei byte = 332939bc...
  2. il file degli emendamenti ha esattamente 12 righe non vuote
  3. nessun record con item "0.14" e' gia' presente (idempotenza)
Fallimento rumoroso su ognuno: nessuna scrittura parziale, nessun warning.

Uso:
    python src\\paper2_append_amend13.py selftest
    python src\\paper2_append_amend13.py --dry-run
    python src\\paper2_append_amend13.py --apply
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
EXPECT_LINES_BEFORE = 12          # = PREREG_AMENDMENTS_AT_DEPOSIT
EXPECT_LINES_AFTER = 13           # = DOCUMENTED_AMENDMENTS
ITEM = "0.14"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def self_digest(ref_path: Path) -> str:
    """Digest del CONTENUTO riserializzato in forma canonica, escluso il campo
    stesso. E' il cancello che i manifest registrano in `reference_sha256`, ed e'
    una grandezza diversa dallo sha256 dei byte del file."""
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
        "json_path": "prereg §4 (measurement grid); prereg §7 (mandatory procedure)",
        "key": "constant_cube_gauge / box_min / clipped_positions",

        "old_value": (
            "§4: nine points, constant-cube gauge, L, dx and sigma_px identical to "
            "fiducial at every point; alpha_iso selected by Chebyshev minimax on the "
            "ANISOTROPIC residual. box_min not specified. §7: seven-step injection "
            "sequence, with no count of positions falling outside the embedding cube."
        ),

        "new_value": {
            "a_operational_anchor": {
                "source": "results/paper2/fase2.jsonl, the two gate d2 records",
                "NGC": {"box_size": 1997.3629110094512,
                        "cell": 15.604397742261337,
                        "sigma_px": 0.32042249039652254,
                        "R_SMOOTH": 4.999999985713251,
                        "n_valid_voxels": 307805, "N_H1": 28256,
                        "N_rand": 13248857},
                "SGC": {"box_size": 1904.450156441475,
                        "cell": 14.878516847199023,
                        "sigma_px": 0.33605500065144590,
                        "R_SMOOTH": 4.999999988778017,
                        "n_valid_voxels": 172225, "N_H1": 15122,
                        "N_rand": 5432939},
                "documentary_reference": (
                    "phase6_voxelize_diagnostics (NGC) and phase9_sgc_likeforlike "
                    "(SGC) remain the documentary reference. The former was written "
                    "by an R=14.8 run, so its sigma_px (0.9484505715737068 = "
                    "14.8/15.6044) is NOT the fiducial one; box, cell, alpha, counts "
                    "and the mask are R-independent and remain comparable.")
            },
            "b_cube_construction": (
                "For every measurement point the box is DERIVED, with MULTIPLICATIVE "
                "padding pad = 5c where c = L_fid / L_point. Then L = L_fid exactly, "
                "so dx and sigma_px are identical to fiducial by construction rather "
                "than by forcing; Proposition 2 holds in exact form instead of the "
                "approximate 2' form; and box_min follows the deformed cloud, so the "
                "grid-galaxy offset is the ANISOTROPIC part alone (0.28-0.57 voxel), "
                "which is the quantity being measured. The origin is re-derived, not "
                "forced. Block A keeps pad = 5*alpha_iso (gate 2.2b)."),
            "c_clipped_positions": (
                "Zero required, not bounded by a tolerance. Counted per face, "
                "separately for randoms and galaxies, on both the derived and the "
                "fiducial box; [FATAL] on any nonzero value. Verified by "
                "paper2_phase3_preflight.py before any field is built."),
            "d_grid_unchanged": (
                "By Lemma 3, F_AP = f/(r f') is invariant under f -> c f, so the five "
                "line-B exponents and the four corner labels are exactly those "
                "deposited. Only the residual column moves, by 0.8-1.6%: line B goes "
                "from +-0.2844/+-0.5687 to 0.2833-0.2856/0.5641-0.5734 voxel (NGC). "
                "The sampling is therefore equispaced in voxel to within 1.6%, not "
                "exactly, and must be described that way.")
        },

        "reason": (
            "Section 4 fixes L, dx and sigma_px but leaves box_min free, and selects "
            "alpha_iso by minimax on the ANISOTROPIC residual, which leaves "
            "alpha_box != 1. Forcing L with alpha_box != 1 does not absorb the "
            "residual isotropic dilation, it TRUNCATES the random cloud: cic_3d "
            "(phase8:495-508) does not discard out-of-cube positions, it stacks them "
            "on the cube faces. Stacked mass shifts field_r.mean(), hence the mask "
            "threshold, hence n_valid_voxels, hence N_H1 through the measured slope "
            "0.1009 (NGC) / 0.0945 (SGC). The artefact would be correlated with the "
            "signal, because it grows with the residual. Multiplicative padding "
            "removes it by construction rather than bounding it, and rests on gate "
            "2.2b (confirmed, delta = 0 exact in both hemispheres) rather than on "
            "2.2a (falsified)."),

        "evidence": (
            "results/paper2/item12a_geom_NGC.jsonl, 18 points. At a box forced to the "
            "fiducial the deformed cloud exits by up to 3.22 voxel at C1 "
            "(dL = +101.456 h^-1Mpc), 0.735 at C3 (+30.269) and 0.248 at B1 "
            "(+16.215). Calibration of the cost from gate 2.2a: a grid-galaxy offset "
            "of 0.031 voxel moved 216 mask voxels and 34 generators."),

        "falsified_prediction": (
            "Declared before this measurement and recorded as wrong. Clipping was "
            "predicted at B1/B5/C1/C4 and absent at B2/B4/C2/C3, anchored to the "
            "anisotropic residual. It is wrong at B5, C3 and C4. Clipping tracks the "
            "SIGN of dL, i.e. the residual ISOTROPIC part left in the box by the "
            "minimax gauge, not the anisotropic residual. Falsified by records "
            "already on disk, before any run. Not repaired."),

        "withdrawn": (
            "The admissibility threshold proposed on 29 Aug 2026 (|dV| <= 100 voxel "
            "NGC, 135 SGC, derived from the constant-cube floor divided by slope (e)) "
            "is WITHDRAWN. It mitigated a gauge defect; the corrected gauge removes "
            "the defect. Correcting an artefact within a tolerance is worse than not "
            "producing it."),

        "numbering_rule": (
            "The number of an amendment is its 1-based POSITION in this file: no "
            "field declares it, and prereg §9 refers to records 11 and 12 by "
            "position. This is record 13."),

        "reference_file": REF_REL,
        "reference_file_sha256": EXPECT_FILE_SHA,
        "reference_self_sha256": EXPECT_SELF_SHA,
    }


def gates(base: Path, *, strict: bool = True) -> list[str]:
    """Restituisce la lista dei cancelli falliti. Vuota = si puo' scrivere."""
    fails = []
    ref = base / REF_REL
    am = base / AM_REL

    if not ref.is_file():
        return [f"reference assente: {ref}"]
    file_sha = sha256_bytes(ref.read_bytes())
    o = json.loads(ref.read_text(encoding="utf-8"))
    recorded = o.get("_self_sha256")
    recomputed = self_digest(ref)

    if recorded != recomputed:
        fails.append(f"cancello del self-digest rotto: registrato={recorded} "
                     f"ricalcolato={recomputed}")
    if strict and recomputed != EXPECT_SELF_SHA:
        fails.append(f"self-digest inatteso: {recomputed} != {EXPECT_SELF_SHA}")
    if strict and file_sha != EXPECT_FILE_SHA:
        fails.append(f"sha256 dei byte inatteso: {file_sha} != {EXPECT_FILE_SHA}")

    if not am.is_file():
        fails.append(f"file degli emendamenti assente: {am}")
        return fails
    lines = [l for l in am.read_text(encoding="utf-8").splitlines() if l.strip()]
    if strict and len(lines) != EXPECT_LINES_BEFORE:
        fails.append(f"righe non vuote = {len(lines)}, attese "
                     f"{EXPECT_LINES_BEFORE}: l'albero non e' quello per cui "
                     f"questo record e' stato scritto")
    for i, l in enumerate(lines, 1):
        try:
            r = json.loads(l)
        except Exception as exc:
            fails.append(f"riga {i} malformata: {str(exc)[:60]}")
            continue
        if isinstance(r, dict) and r.get("item") == ITEM:
            fails.append(f"un record con item {ITEM} esiste gia' alla riga {i}: "
                         f"l'append sarebbe un doppione")
    return fails


def append_atomic(am: Path, line: str) -> None:
    """Append con fsync sul file e sulla directory: o c'e' tutta la riga, o non
    c'e' niente. Newline esplicito, nessun BOM, UTF-8."""
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
        pass          # su Windows fsync sulla directory non e' disponibile


def cmd_run(a) -> int:
    base = Path(a.base).resolve()
    am = base / AM_REL
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

    append_atomic(am, line)
    lines = [l for l in am.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = len(lines) == EXPECT_LINES_AFTER and json.loads(lines[-1])["item"] == ITEM
    print(f"\nappeso. righe ora: {len(lines)} (attese {EXPECT_LINES_AFTER}) "
          f"-> {'OK' if ok else 'CONTROLLARE A MANO'}")
    print("\nOra:  python src\\paper2_freeze_verify.py verify --jobs 4 "
          "--out logs\\fv.jsonl   -> deve dare CLEAN")
    return 0 if ok else 1


def cmd_selftest(a) -> int:
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    tmp = Path(tempfile.mkdtemp(prefix="amend13_"))
    try:
        (tmp / "src").mkdir()
        ref = tmp / REF_REL
        am = tmp / AM_REL

        payload = {"schema": "test", "x": 1}
        o = dict(payload)
        o["_self_sha256"] = sha256_bytes(json.dumps(
            payload, indent=2, sort_keys=True, ensure_ascii=False).encode())
        ref.write_text(json.dumps(o, indent=2), encoding="utf-8")
        am.write_text("".join('{"a":1}\n' for _ in range(12)), encoding="utf-8")

        f = gates(tmp, strict=False)
        expect("1. albero sano, cancelli non stringenti -> nessun fallimento",
               not f, f"({f})")

        f = gates(tmp, strict=True)
        expect("2. digest attesi assenti -> il cancello stringente ferma",
               any("self-digest inatteso" in x for x in f))

        o2 = dict(o); o2["x"] = 2
        ref.write_text(json.dumps(o2, indent=2), encoding="utf-8")
        expect("3. contenuto alterato -> cancello del self-digest rotto",
               any("self-digest rotto" in x for x in gates(tmp, strict=False)))
        ref.write_text(json.dumps(o, indent=2), encoding="utf-8")

        am.write_text("".join('{"a":1}\n' for _ in range(11)), encoding="utf-8")
        f = gates(tmp, strict=True)
        expect("4. conteggio righe sbagliato -> ferma",
               any("righe non vuote" in x for x in f))
        am.write_text("".join('{"a":1}\n' for _ in range(12)), encoding="utf-8")

        append_atomic(am, json.dumps({"item": ITEM, "type": "protocol"}))
        f = gates(tmp, strict=False)
        expect("5. record gia' presente -> l'append e' un doppione, ferma",
               any("esiste gia'" in x for x in f))

        n = len([l for l in am.read_text(encoding="utf-8").splitlines() if l.strip()])
        expect("6. append atomico: una riga in piu', non due", n == 13, f"(n={n})")

        rec = build_record("2026-01-01T00:00:00+00:00")
        line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        rt = json.loads(line)
        expect("7. il record e' JSON valido e porta le due ancore",
               rt["reference_file_sha256"] == EXPECT_FILE_SHA
               and rt["reference_self_sha256"] == EXPECT_SELF_SHA)
        expect("8. type = protocol, come pretende il verificatore",
               rt["type"] == "protocol")
        expect("9. il record dichiara la predizione smentita e la soglia ritirata",
               "falsified_prediction" in rt and "withdrawn" in rt)
        expect("10. nessun a capo dentro la riga",
               "\n" not in line)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=".", help="radice del repository")
    p.add_argument("--apply", action="store_true",
                   help="scrive davvero; senza, e' un dry-run")
    p.add_argument("--dry-run", action="store_true", help="esplicito, e' il default")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    a = p.parse_args()
    if a.cmd == "selftest":
        return cmd_selftest(a)
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())

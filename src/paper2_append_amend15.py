#!/usr/bin/env python3
"""
CAUCHY / Paper 2 — append del record 15: un sesto punto sulla linea B.

COSA REGISTRA
  L'aggiunta di un punto di misura oltre l'estremo campionato, con DUE scopi
  dichiarati e le regole con cui va letto. Emenda il §4 (griglia a nove punti) e
  il §5.2 (copertura della linea B a |F-1| = 0.0301) del protocollo depositato.

PERCHE' E' UN EMENDAMENTO E NON UN'AGGIUNTA
  Arriva DOPO aver visto i risultati della Fase 3. La griglia e la copertura
  sono depositate. Un punto in piu' scelto guardando i residui e' esattamente il
  tipo di estensione che va dichiarata prima di girare, con la sua regola, o non
  vale niente.

I DUE SCOPI
  1. La linea B non bracketa C1. Il F(z) di C1 arriva a 1.040504, oltre B5 a
     1.030071: per C1 il test di completezza del §5.6 e' ESTRAPOLAZIONE e non
     interpolazione. Il §5.4 afferma che la linea B bracketa il range fisico con
     l'11% di margine: vero per il F EFFICACE, falso per il F(z) puntuale. Non
     era previsto nel disegno della griglia.
  2. Dare leva a due cose che cinque punti non reggono: la forma della risposta
     (fit quadratico rifiutato, chi2 da 29 a 136 su 2 dof) e un residuo di ~45
     generatori rms che nessuna quantita' misurata descrive — spostamento di
     griglia, molteplicita' di tiling, w_bar, occupazione, selezione, tutti
     bocciati dal jackknife o con segno che si inverte fra emisferi.

IL VALORE DI F NON SI DIGITA: SI DERIVA
  Il punto continua il campionamento equispaziato in residuo minimax che ha
  prodotto B1-B5, alla terza unita'. Questo script lo calcola con la STESSA
  funzione `deform` che ha generato la linea B, e prima di farlo verifica che
  quella funzione riproduca il residuo depositato di B4. Un valore scritto a
  mano sarebbe un quarto numero da fidarsi.

REGOLE, dichiarate qui prima di qualunque run
  - B6 NON entra in DD_max, che resta definito su B1-B5 come depositato. Il
    verdetto E1-E4 e' gia' emesso (E2, quattro volte su quattro) e non cambia:
    un punto aggiunto dopo non puo' riaprire una regola gia' applicata.
  - B6 entra nel fit di simmetria (sei punti, tre parametri, 3 dof, limite
    chi2 = 11.34 al 99%), nel test di completezza per C1, e nella diagnostica
    del residuo.
  - PREDIZIONE DICHIARATA sul residuo non attribuito: se e' un artefatto che
    cresce con la deformazione, |residuo(B6)| > |residuo(B5)|; se e' rumore
    specifico dei punti campionati, resta ~45 generatori. I due casi si
    distinguono, e nessuno dei due si aggiusta a posteriori.
  - Costo: un run lato dati (~37 s) e 200 mock su un punto (~1 h per emisfero).

CANCELLI, prima di scrivere
  1. reference vivo con _self_sha256 = 865aa2ef... e byte = 332939bc...
  2. il file degli emendamenti ha esattamente 14 righe non vuote
  3. nessun record con item "1.3/B6" gia' presente
  4. la macchina riproduce il residuo depositato di B4 (0.2844 voxel NGC)
  5. il F calcolato supera il F_max di C1 (1.040504) con margine

Uso:
    python src\\paper2_append_amend15.py selftest
    python src\\paper2_append_amend15.py --dry-run
    python src\\paper2_append_amend15.py --apply
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

import numpy as np

REF_REL = "src/paper2_v1_reference.json"
AM_REL = "src/paper2_v1_amendments.jsonl"
EXPECT_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"
EXPECT_FILE_SHA = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
EXPECT_LINES_BEFORE = 14
EXPECT_LINES_AFTER = 15
ITEM = "1.3/B6"

CELL_NGC = 15.604397742261337
F_B4 = 1.014889                 # unita' del campionamento equispaziato
RES_B4_DEPOSITED = 0.2844       # voxel NGC, §4 della pre-registrazione
RES_TOL = 0.002                 # le cifre depositate sono quattro
C1_F_MAX = 1.040504             # item12a_cosmo, F_AP_par_over_perp_max
UNITS = 3                       # B6 alla terza unita': B2/B4 = 1, B1/B5 = 2
ZMIN, ZMAX = 0.10, 0.40


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def self_digest(ref: Path) -> str:
    o = json.loads(ref.read_text(encoding="utf-8"))
    payload = {k: v for k, v in o.items() if k != "_self_sha256"}
    return sha256_bytes(json.dumps(payload, indent=2, sort_keys=True,
                                   ensure_ascii=False).encode())


def residual_voxel(I13, z_tab, dc_fid, F, cell=CELL_NGC):
    """Residuo minimax in voxel, con la STESSA `deform` che ha fatto la linea B."""
    dc = I13.deform(z_tab, dc_fid, dict(kind="ap", alpha_iso=1.0, F_ap=F))
    m = (z_tab >= ZMIN) & (z_tab <= ZMAX)
    r, f = dc_fid[m], dc[m]
    al = I13.minimax_alpha(r, f)
    return float(np.max(np.abs(f - al * r)) / cell)


def solve_F(I13, z_tab, dc_fid, target, lo=1.0, hi=1.20, cell=CELL_NGC):
    """Bisezione su F > 1 per un residuo assegnato. Monotona in questo intervallo.

    `cell` va passata: senza, il bersaglio e la funzione starebbero in unita'
    diverse e la bisezione andrebbe a sbattere contro `hi` senza accorgersene.
    In produzione le due coincidono e il difetto resterebbe latente.
    """
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if residual_voxel(I13, z_tab, dc_fid, mid, cell=cell) < target:
            lo = mid
        else:
            hi = mid
    F = 0.5 * (lo + hi)
    if hi - lo > 1e-12 or F >= 0.999 * 1.20:
        raise SystemExit(f"[FATAL] la bisezione non ha convergito: F = {F!r}. "
                         f"Bersaglio {target!r} fuori dall'intervallo [1.0, 1.20]?")
    return F


def derive(srcdir="src"):
    if srcdir and srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    import phase8_cutsky_mocks as M
    import paper2_item13a_15a as I13
    z = np.asarray(M._Z_TAB, float).copy()
    dc = np.asarray(M._DC_TAB, float).copy()
    u = residual_voxel(I13, z, dc, F_B4)
    if abs(u - RES_B4_DEPOSITED) > RES_TOL:
        sys.exit(f"[FATAL] la macchina non riproduce il residuo depositato di B4: "
                 f"{u:.6f} contro {RES_B4_DEPOSITED} (tolleranza {RES_TOL}). "
                 f"Non calcolo un valore nuovo con un codice che non torna sul vecchio.")
    F = solve_F(I13, z, dc, UNITS * u)
    got = residual_voxel(I13, z, dc, F)
    if F <= C1_F_MAX:
        sys.exit(f"[FATAL] F calcolato {F:.6f} non supera il F_max di C1 "
                 f"({C1_F_MAX}): il punto non servirebbe al primo scopo.")
    return {"F_ap": F, "residual_voxel": got, "unit_voxel": u,
            "unit_check_B4": {"computed": u, "deposited": RES_B4_DEPOSITED},
            "units": UNITS, "margin_over_C1_Fmax": F - C1_F_MAX}


def build_record(utc: str, b6: dict) -> dict:
    return {
        "type": "protocol",
        "item": ITEM,
        "utc": utc,
        "document": ("paper2_prereg_v1.md v1.1 — version DOI "
                     "10.5281/zenodo.22148444"),
        "json_path": "prereg §4 (measurement grid); prereg §5.2 (line-B coverage)",
        "key": "line_B_sixth_point",
        "old_value": (
            "§4: nine measurement points. §5.2: line B covers |F-1| = 0.0301, "
            "bracketing the physical range |F-1| <= 0.027 with an 11% margin. "
            "§5.6 predicts D at each corner by interpolating in effective F "
            "along line B."),
        "new_value": {
            "point": "B6",
            "F_ap_pipeline_convention": b6["F_ap"],
            "abs_F_minus_1": abs(b6["F_ap"] - 1.0),
            "minimax_residual_voxel_NGC": b6["residual_voxel"],
            "sampling_rule": (
                "Continues the equispaced-in-minimax-residual sampling that "
                "produced B1-B5, at the third unit (B2/B4 = 1, B1/B5 = 2). The "
                "value is DERIVED by paper2_append_amend15.py with the same "
                "`deform` that generated line B, after checking that it "
                "reproduces the deposited residual of B4; it is not typed in."),
            "unit_check": b6["unit_check_B4"],
            "margin_over_C1_Fmax": b6["margin_over_C1_Fmax"],
        },
        "reason": (
            "Two purposes, both discovered after the Phase-3 results and both "
            "declared here before any run. FIRST: line B does not bracket C1. "
            "The pointwise F(z) of C1 reaches 1.040504, beyond B5 at 1.030071, "
            "so for C1 the §5.6 completeness test is EXTRAPOLATION and not "
            "interpolation. The §5.4 claim that line B brackets the physical "
            "range with an 11% margin holds for the EFFECTIVE F and fails for "
            "the pointwise F(z); the grid design did not anticipate it. SECOND: "
            "five points do not constrain what the data show. The quadratic "
            "response model is rejected (chi2 = 69.8, 29.3, 110.5, 135.9 on 2 "
            "dof, GLS with the full covariance of the mean), and a residual of "
            "~45 generators rms between points survives the subtraction of the "
            "voxel channel and is described by nothing measured: grid "
            "displacement, tiling multiplicity, w_bar, occupancy and selection "
            "are all either killed by a leave-one-out jackknife or change sign "
            "between hemispheres."),
        "rules": {
            "DD_max_unchanged": (
                "B6 does NOT enter DD_max, which stays defined on B1-B5 as "
                "deposited. The E1-E4 verdict is already issued — E2, four times "
                "out of four — and does not change. A point added afterwards "
                "cannot reopen a rule already applied."),
            "where_B6_enters": (
                "Symmetry fit (six points, three parameters, 3 dof, chi2 limit "
                "11.34 at 99%); completeness test for C1, which becomes "
                "interpolation; residual diagnostic."),
            "declared_prediction": (
                "On the unattributed residual: if it is an artefact growing with "
                "the deformation, |residual(B6)| > |residual(B5)|; if it is noise "
                "specific to the sampled points, it stays around 45 generators. "
                "The two cases are distinguishable, and neither is to be adjusted "
                "afterwards."),
            "cost": "one data-side run (~37 s) and 200 mocks on one point "
                    "(~1 h per hemisphere).",
        },
        "evidence": (
            "results/paper2/item12a_cosmo.jsonl: C1 (Om=0.25, w0=-1.2) has "
            "F_AP_par_over_perp between 1.014656 and 1.040504, an excursion of "
            "0.025848 — 43.8% of the whole line-B width — and it exits line B "
            "from above. results/paper2/fase3_analisi.jsonl: chi2 of the "
            "quadratic fit and per-point residuals. Jackknife on the residual "
            "diagnostic: d_multmax loses 77% of its slope in NGC k=1 when B4 is "
            "removed (r from +0.382 to +0.019) and 91% at k=0 when B5 is "
            "removed; du swings between r = -0.019 and +0.346 depending on which "
            "point is dropped; d_wbar1 changes sign between hemispheres "
            "(+8.9e8 NGC, -5.4e8 SGC)."),
        "numbering_rule": ("The number of an amendment is its 1-based POSITION "
                           "in this file. This is record 15."),
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
    if o.get("_self_sha256") != self_digest(ref):
        fails.append("cancello del self-digest rotto")
    if strict and self_digest(ref) != EXPECT_SELF_SHA:
        fails.append("self-digest inatteso")
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
    with open(am, "ab") as fh:
        fh.write((line + "\n").encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())


def cmd_run(a) -> int:
    base = Path(a.base).resolve()
    fails = gates(base)
    print(f"base: {base}\ncancelli sul file: {'OK' if not fails else 'FALLITI'}")
    for f in fails:
        print(f"  [FATAL] {f}")
    if fails:
        return 2
    b6 = derive(a.src)
    print(f"\n  unita' del campionamento (residuo di B4): {b6['unit_voxel']:.6f} voxel"
          f"   depositato {RES_B4_DEPOSITED}  -> riprodotto")
    print(f"  B6 alla {UNITS}a unita': F = {b6['F_ap']:.6f}  "
          f"|F-1| = {abs(b6['F_ap']-1):.6f}  residuo {b6['residual_voxel']:.6f} voxel")
    print(f"  supera il F_max di C1 ({C1_F_MAX}) di {b6['margin_over_C1_Fmax']:.6f}")

    rec = build_record(datetime.now(timezone.utc)
                       .strftime("%Y-%m-%dT%H:%M:%S+00:00"), b6)
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
    n = len([l for l in am.read_text(encoding="utf-8").splitlines() if l.strip()])
    ok = n == EXPECT_LINES_AFTER
    print(f"\nappeso. righe ora: {n} (attese {EXPECT_LINES_AFTER}) "
          f"-> {'OK' if ok else 'CONTROLLARE A MANO'}")
    print("\nOra: portare DOCUMENTED_AMENDMENTS a 15 in paper2_freeze_verify.py, "
          "poi verify -> CLEAN con disco=15")
    return 0 if ok else 1


def cmd_selftest(a) -> int:
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    tmp = Path(tempfile.mkdtemp(prefix="amend15_"))
    try:
        (tmp / "src").mkdir()
        ref, am = tmp / REF_REL, tmp / AM_REL
        payload = {"schema": "test", "x": 1}
        o = dict(payload)
        o["_self_sha256"] = sha256_bytes(json.dumps(
            payload, indent=2, sort_keys=True, ensure_ascii=False).encode())
        ref.write_text(json.dumps(o, indent=2), encoding="utf-8")
        am.write_text("".join('{"a":1}\n' for _ in range(14)), encoding="utf-8")
        expect("1. albero sano -> nessun fallimento", not gates(tmp, strict=False))
        am.write_text("".join('{"a":1}\n' for _ in range(13)), encoding="utf-8")
        expect("2. quattordici righe attese, tredici trovate -> ferma",
               any("righe non vuote" in x for x in gates(tmp, strict=True)))
        am.write_text("".join('{"a":1}\n' for _ in range(14)), encoding="utf-8")
        append_atomic(am, json.dumps({"item": ITEM}))
        expect("3. record gia' presente -> doppione, ferma",
               any("esiste gia'" in x for x in gates(tmp, strict=False)))

        # --- la bisezione, su una funzione sintetica monotona ----------------
        class Fake:
            @staticmethod
            def deform(z, dc, spec):
                return dc * (1.0 + 19.0 * (spec["F_ap"] - 1.0) / 1000.0)

            @staticmethod
            def minimax_alpha(r, f):
                return 1.0
        z = np.linspace(0.0, 0.6, 4001)
        dc = 1000.0 * z
        r1 = residual_voxel(Fake, z, dc, 1.014889, cell=1.0)
        F3 = solve_F(Fake, z, dc, 3 * r1, cell=1.0)
        r3 = residual_voxel(Fake, z, dc, F3, cell=1.0)
        expect("4. la bisezione centra tre unita' di residuo",
               abs(r3 / r1 - 3.0) < 1e-6, f"(rapporto {r3/r1:.8f})")
        expect("5. e il residuo cresce con |F-1|, come la bisezione assume",
               residual_voxel(Fake, z, dc, 1.05, cell=1.0)
               > residual_voxel(Fake, z, dc, 1.02, cell=1.0))
        # Il difetto che il test 4 ha scoperto: cella diversa fra bersaglio e
        # funzione manda la bisezione contro l'estremo, in silenzio. Ora urla.
        try:
            solve_F(Fake, z, dc, 3 * r1)          # cella di default: mismatch
            caught = False
        except SystemExit:
            caught = True
        expect("5b. e un bersaglio in unita' sbagliate NON passa in silenzio",
               caught)

        b6 = {"F_ap": 1.0444, "residual_voxel": 0.8532, "unit_voxel": 0.2844,
              "unit_check_B4": {"computed": 0.2844, "deposited": 0.2844},
              "units": 3, "margin_over_C1_Fmax": 1.0444 - C1_F_MAX}
        rt = json.loads(json.dumps(build_record("2026-01-01T00:00:00+00:00", b6),
                                   ensure_ascii=False, sort_keys=True))
        expect("6. il record dichiara che DD_max NON cambia",
               "does NOT enter DD_max" in rt["rules"]["DD_max_unchanged"])
        expect("7. e porta una predizione falsificabile sul residuo",
               "residual(B6)" in rt["rules"]["declared_prediction"])
        expect("8. due ancore e type protocol",
               rt["reference_file_sha256"] == EXPECT_FILE_SHA
               and rt["reference_self_sha256"] == EXPECT_SELF_SHA
               and rt["type"] == "protocol")
        expect("9. il valore di F e' accompagnato dalla verifica su B4",
               rt["new_value"]["unit_check"]["deposited"] == RES_B4_DEPOSITED)
        expect("10. nessun a capo dentro la riga",
               "\n" not in json.dumps(rt, ensure_ascii=False, sort_keys=True))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=".")
    p.add_argument("--src", default="src")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    a = p.parse_args()
    return cmd_selftest(a) if a.cmd == "selftest" else cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())

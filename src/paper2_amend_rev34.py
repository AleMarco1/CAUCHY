#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 - Tre emendamenti al reference, sessione del 27 ago 2026.

Il reference resta BYTE-IDENTICO (item 0.12): gli emendamenti vivono nel file
sorella append-only src/paper2_v1_amendments.jsonl. Lo script verifica lo sha256
del reference PRIMA di scrivere e rifiuta se non combacia, cosi' il campo
reference_sha256 di ogni record non e' una copia a memoria ma una misura.

CONTENUTO
  A1  la regola di costruzione della maschera, ASSENTE dal reference. E' il nodo
      condiviso da ~30 script e non aveva la propria regola nel set congelato.
  A2  disambiguazione: `mask_criterion` nel reference NON e' il criterio della
      maschera, e' il limite pratico w_bar/sigma_px di P1 §8.2. Collisione di
      nomi gia' emendata una volta (item 1.2b, practical_rule).
  A3  popolazione dei random non nulli e percentile equivalente per emisfero;
      il "P10" dichiarato in M26/P1 non riproduce la congelata.

Uso:
    python src\\paper2_amend_rev34.py            # anteprima, non scrive
    python src\\paper2_amend_rev34.py --apply
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REF = "src/paper2_v1_reference.json"
REF_SHA = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
AMEND = "src/paper2_v1_amendments.jsonl"
UTC = "2026-08-27T00:00:00Z"

RECORDS = [
    {
        "item": "0.5.3 / 2.1-M",
        "type": "amendment",
        "json_path": "mask_construction_rule",
        "key": "mask_construction_rule",
        "old_value": None,
        "new_value": {
            "rule": "mask = field_r > 0.01 * field_r.mean()",
            "mean_over": "full 128^3 cube, not the non-zero voxels",
            "producer": "phase6_bgs_voxelize.py:182-183",
            "threshold_NGC": 0.020012933760881424,
            "threshold_SGC": 0.008570596575737,
            "n_valid_voxels_NGC": 307805,
            "n_valid_voxels_SGC": 172225,
            "loaded_not_derived": ("in the fiducial path the mask is np.load'ed from "
                                   "phase6_fields/bgs_{ngc,sgc}_mask_128.npy "
                                   "(paper1_remap.py:211-214 NGC, 239-247 SGC); "
                                   "reconstruction from randoms is the fallback branch"),
            "shared_node": ("~30 scripts read this file: all paper1_rev_*, six phase6, "
                            "phase8_cutsky_mocks:85, eight phase9, some via rglob with no "
                            "fixed path. Never regenerate in place."),
        },
        "reason": ("La regola di costruzione della maschera non era registrata da nessuna "
                   "parte nel reference, pur essendo l'ingresso condiviso da M26, Paper 1 e "
                   "tutte le sue revisioni. Aggiunta, non corretta: old_value e' null."),
        "evidence": ("results/paper2/gate21.jsonl (cancello 2.1-M, 27 ago 2026): "
                     "np.array_equal(mask_ricalcolata, mask_congelata) VERO in entrambi gli "
                     "emisferi; soglia riprodotta a rel 2.2e-08 (NGC) e 7.0e-08 (SGC); "
                     "voxel 307805 e 172225 esatti. Strumento src/paper2_gate21m.py."),
        "reference_file": REF,
        "reference_sha256": REF_SHA,
        "utc": UTC,
    },
    {
        "item": "0.5.3 / 2.1-M",
        "type": "amendment",
        "json_path": "mask_criterion._scope",
        "key": "_scope",
        "old_value": None,
        "new_value": ("mask_criterion describes the PRACTICAL ADMISSIBILITY limit of P1 §8.2 "
                      "(w_bar threshold 0.99, sigma_px vs d_med), NOT the survey-mask "
                      "construction rule. The construction rule is in mask_construction_rule."),
        "reason": ("Collisione di nomi della stessa famiglia che ha reso necessario "
                   "paper2_stato.md. Chi legge 'mask_criterion' assume la regola della "
                   "maschera e trova invece il limite pratico. La chiave e' gia' stata "
                   "emendata una volta (item 1.2b, practical_rule): l'ambito va fissato "
                   "prima che un terzo emendamento la tocchi."),
        "evidence": "src/paper2_v1_reference.json, chiave mask_criterion; P1 §8.2.",
        "reference_file": REF,
        "reference_sha256": REF_SHA,
        "utc": UTC,
    },
    {
        "item": "0.5.3 / 0.2 (R2.6)",
        "type": "amendment",
        "json_path": "mask_construction_rule.percentile_equivalent",
        "key": "percentile_equivalent",
        "old_value": None,
        "new_value": {
            "population": "voxels with field_r > 0",
            "population_NGC": 320342,
            "population_SGC": 178293,
            "percentile_NGC": 3.914,
            "percentile_SGC": 3.403,
            "note": ("the 1%-of-mean rule is not a fixed percentile: it induces a different "
                     "percentile in each hemisphere, so 'P10' is not a mislabelling of the "
                     "same rule but a different rule altogether"),
            "p10_reproduces_frozen": False,
        },
        "reason": ("M26/P1 e la richiesta R2.6 del referee descrivono il taglio come 'P10 "
                   "della densita' dei random'. Il P10 non riproduce la congelata: 288307 "
                   "voxel contro 307805, Jaccard 0.9367. La soglia congelata (0.0200129) e' "
                   "piu' permissiva perfino del P5 (0.0433395). Materia della risposta ai "
                   "referee del Paper 1, item 0.2."),
        "evidence": ("results/paper1/rev_n4n5_report.json: p10_riproduce_congelata=false; "
                     "P5/P10/P15 danno 304324/288307/272290 voxel. "
                     "results/paper2/gate21.jsonl campo nonzero_population (cancello 2.1-M). "
                     "Nota di stabilita' per R2.6: fra P5 e P10 lo z dello SKEW inverte segno "
                     "(-4.58 -> +7.69); media, sd e curtosi mantengono il segno su P5-P15. "
                     "La maschera realmente usata sta a P3.914, cioe' dal lato P5."),
        "reference_file": REF,
        "reference_sha256": REF_SHA,
        "utc": UTC,
    },
]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Emendamenti rev. 3.4 al reference v1")
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    root = Path(args.project_root).resolve()

    ref = root / REF
    if not ref.exists():
        sys.exit("[FATAL] reference assente: %s" % ref)
    got = sha256_file(ref)
    print("reference sha256 = %s" % got)
    if got != REF_SHA:
        sys.exit("[FATAL] il reference NON e' quello congelato (atteso %s).\n"
                 "        Non scrivo emendamenti che citerebbero un hash falso." % REF_SHA)
    print("  combacia col congelato: il reference e' intatto.\n")

    path = root / AMEND
    existing = 0
    if path.exists():
        with open(path, "r", encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip():
                    existing += 1
                    r = json.loads(ln)          # verifica che il file sia integro
    print("emendamenti gia' presenti: %d" % existing)

    for i, r in enumerate(RECORDS, 1):
        print("\n--- A%d  item %s  ->  %s" % (i, r["item"], r["json_path"]))
        print("    %s" % r["reason"][:150])

    if not args.apply:
        print("\n[anteprima] nessuna scrittura. Rilanciare con --apply.")
        return 0

    lines = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in RECORDS)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(lines)
        fh.flush()
        os.fsync(fh.fileno())

    after = sha256_file(ref)
    if after != REF_SHA:
        sys.exit("[FATAL] il reference e' cambiato durante la scrittura. Indagare subito.")
    n = sum(1 for ln in open(path, encoding="utf-8") if ln.strip())
    print("\n[scritti] %d record appesi; totale %d. Reference invariato (%s)."
          % (len(RECORDS), n, after[:16] + "..."))
    return 0


if __name__ == "__main__":
    sys.exit(main())

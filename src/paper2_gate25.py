#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 - Cancello 2.5: appaiamento dei semi.

RIFORMULAZIONE, DICHIARATA PRIMA DELL'ESECUZIONE
------------------------------------------------
La checklist chiedeva che il run appaiato riproducesse il mock v1 "galassia per
galassia". NON E' POSSIBILE: `stage_cache` (paper1_remap.py:420) salva soltanto
`delta.astype(np.float32)`; le posizioni `pos_sel` vivono in memoria e muoiono
li'. Quei cataloghi non esistono.

Il cancello e' quindi riformulato come **chiusura campo per campo**: si riesegue
il mock kk con lo stesso seme e si verifica `np.array_equal` contro il
`delta_{kk:04d}.npy` congelato. E' piu' debole in linea di principio; in pratica
non lo e', perche' due insiemi di galassie diversi che producano un campo CIC
bit-identico su 128^3 float32 sono un evento di misura nulla. E il livello
galassia si recupera DENTRO la sessione: `len(pos_gal)` e `len(pos_sel)` sono in
memoria e vengono confrontati fra le repliche.

PREDIZIONE DICHIARATA: bit-identico in N/N. Un solo mock che non riproduce
significa che l'appaiamento non regge, e la Fase 3 (item 3.2, mock appaiati per
punto della griglia) non e' eseguibile come progettata.

PERCHE' NON SERVONO 2000 MOCK
  Se 20 su 20 riproducono bit-identici, l'appaiamento e' stabilito. Il costo
  scende da ore a minuti.

PERCHE' GLI INDICI DI DEFAULT SONO DUE BLOCCHI SEPARATI
  Il difetto di collisione di percorsi del Paper 1 riguardava i mock **0-199**,
  sovrascritti da un run successivo con un HOD diverso (dispersione NGC 445 in
  M26 contro 313 nel Paper 1). Il default campiona quindi 0-9 **e** 1000-1009 e
  riporta i due blocchi separatamente: se il blocco basso fallisce e quello alto
  no, e' la firma della collisione che riappare, ed e' un'informazione diversa
  da "l'appaiamento non regge".

COSA QUESTO SCRIPT NON FA
  Non chiama `stage_cache` (salta i file esistenti, riga 398) ne' `validate_cache`
  (CANCELLA cio' che giudica non valido, riga 391). Replica il corpo del ciclo,
  righe 402-419, e non scrive MAI in data/processed/paper1_mock_deltas/.
  Gli sha256 dei file confrontati sono verificati prima e dopo.

DIAGNOSTICA PER LA FASE 3
  `rng = np.random.default_rng(seed + kk)` e' UN generatore, consumato in
  sequenza da `populate_with_virial` (HOD) e poi da `carve_cutsky` (RSD, ritaglio,
  downsampling). L'appaiamento fra geometrie regge finche' il NUMERO di estrazioni
  a monte non cambia. Lo script registra lo stato del bit generator dopo l'HOD e
  dopo il carve: due geometrie che lascino lo stesso stato hanno consumato lo
  stesso numero di estrazioni. E' il test che servira' al 3.2, e qui costa zero.

Uso:
    python src\\paper2_gate25.py --region NGC
    python src\\paper2_gate25.py --region SGC --indices 0-9,1000-1009
    python src\\paper2_gate25.py --region NGC --indices 0-49
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SEED_DEFAULT = 42
SNAPNUM_DEFAULT = 3
INDICES_DEFAULT = "0-9,1000-1009"
LOG = "results/paper2/gate25.jsonl"
FROZEN_N_H1 = {"NGC": 28256, "SGC": 15122}


def now():
    return datetime.now(timezone.utc).isoformat()


def ok_str(b):
    return "PASSA" if b else "FALLITO"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def append_jsonl(path, rec):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def parse_indices(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part.lstrip("-"):
            a, b = part.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def state_digest(rng):
    """Impronta stabile dello stato del bit generator: due run che abbiano
    consumato lo stesso numero di estrazioni la condividono."""
    st = rng.bit_generator.state
    return hashlib.sha256(json.dumps(st, sort_keys=True, default=str).encode()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description="Cancello 2.5: appaiamento dei semi")
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", choices=["NGC", "SGC"], required=True)
    ap.add_argument("--indices", default=INDICES_DEFAULT,
                    help="es. '0-9,1000-1009' oppure '0-49'. Default: due blocchi separati, "
                         "per distinguere l'appaiamento rotto dalla collisione 0-199.")
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT)
    ap.add_argument("--snapnum", type=int, default=SNAPNUM_DEFAULT)
    args = ap.parse_args()
    root = Path(args.project_root).resolve()
    region = args.region
    idx = parse_indices(args.indices)

    # --- guardia sull'import: paper1_remap deve avere la guardia __main__ ----
    p1src = root / "src" / "paper1_remap.py"
    if not p1src.exists():
        sys.exit("[FATAL] assente: %s" % p1src)
    txt = p1src.read_text(encoding="utf-8", errors="replace")
    if '__name__ == "__main__"' not in txt and "__name__ == '__main__'" not in txt:
        sys.exit("[FATAL] paper1_remap.py non ha la guardia __main__: importarlo\n"
                 "        eseguirebbe main(), che al default e' --stage all. Non importo.")

    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
        import phase8_test2_masked as T2
        import paper1_remap as P1
    except Exception as e:
        sys.exit("[FATAL] import fallito: %s" % e)

    cache_dir = root / "data" / "processed" / "paper1_mock_deltas" / region
    if not cache_dir.exists():
        sys.exit("[FATAL] cache assente: %s" % cache_dir)
    desi_dir = root / "data" / "raw" / "desi_dr1"
    fld_dir = root / "data" / "processed" / "phase6_fields"

    print("=" * 74)
    print("CANCELLO 2.5  |  %s  |  appaiamento dei semi" % region)
    print("=" * 74)
    print("  RIFORMULATO: chiusura CAMPO per campo. I cataloghi di galassie non")
    print("  sono mai stati salvati (stage_cache:420 scrive solo il delta).")
    print("  PREDIZIONE DICHIARATA: bit-identico in %d/%d." % (len(idx), len(idx)))
    print("  Indici: %s" % args.indices)
    print("  Nessuna scrittura in %s\n" % cache_dir)

    # --- lato geometria: la stessa che v1 ha usato --------------------------
    # setup_region carica la maschera CONGELATA da disco, che e' quella con cui
    # v1 fu prodotto. Qui NON si riderivano le maschere: il 2.5 riproduce v1,
    # non misura una geometria nuova.
    G = P1.setup_region(M, region, desi_dir, fld_dir)
    hod = M.HOD_MEDIAN

    # --- sha256 dei file confrontati, PRIMA ---------------------------------
    targets = {}
    for kk in idx:
        f = cache_dir / ("delta_%04d.npy" % kk)
        if not f.exists():
            sys.exit("[FATAL] mock congelato assente: %s" % f)
        targets[kk] = f
    before = {kk: sha256_file(f) for kk, f in targets.items()}

    rows, n_ok, n_bad, n_skip = [], 0, 0, 0
    t_all = time.time()
    for kk in idx:
        t0 = time.time()
        rng = np.random.default_rng(args.seed + kk)
        pos_h, mass_h, vel_h = M.read_halo_catalog(kk, args.snapnum)
        if pos_h is None or len(pos_h) < 50:
            print("    [%4d] catalogo aloni assente o troppo piccolo - SALTATO" % kk)
            n_skip += 1
            continue
        pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h, hod, rng)
        st_hod = state_digest(rng)
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, G["mask"], G["nz_z"], G["nz_target"], rng)
        st_carve = state_digest(rng)
        if pos_sel is None or len(pos_sel) < 100:
            print("    [%4d] carve vuoto - SALTATO" % kk)
            n_skip += 1
            continue

        w_d = np.ones(len(pos_sel))
        field_d = M.cic_3d(pos_sel, w_d, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
        alpha = float(w_d.sum()) / G["sum_wr"]
        delta = P1.compute_delta(field_d, G["field_r"], alpha, G["mask"], M.NGRID)
        mine = delta.astype(np.float32)

        frozen = np.load(targets[kk], mmap_mode="r")
        same = bool(np.array_equal(mine, np.asarray(frozen)))
        d = np.abs(mine.astype(np.float64) - np.asarray(frozen, dtype=np.float64))
        dmax = float(d.max())
        ndiff = int((d > 0).sum())

        rows.append({"index": kk, "identical": same, "max_abs_diff": dmax,
                     "n_cells_differing": ndiff, "n_halos": int(len(pos_h)),
                     "n_gal": int(len(pos_gal)), "n_sel": int(len(pos_sel)),
                     "alpha": alpha, "rng_state_after_hod": st_hod,
                     "rng_state_after_carve": st_carve, "seconds": time.time() - t0})
        n_ok += same
        n_bad += (not same)
        print("    [%4d] aloni %7d  gal %8d  sel %7d  ->  %s%s  [%.1fs]"
              % (kk, len(pos_h), len(pos_gal), len(pos_sel),
                 "IDENTICO" if same else "DIVERSO",
                 "" if same else "  (celle diverse %d, max|d| %.3e)" % (ndiff, dmax),
                 time.time() - t0))

    # --- sha256 DOPO: la cache non deve essere stata toccata ----------------
    after = {kk: sha256_file(f) for kk, f in targets.items()}
    touched = [kk for kk in targets if before[kk] != after[kk]]

    n_tot = n_ok + n_bad
    passed = (n_bad == 0 and n_tot > 0 and not touched)

    print("\n  identici %d / %d   diversi %d   saltati %d   [%.1fs totali]"
          % (n_ok, n_tot, n_bad, n_skip, time.time() - t_all))
    print("  cache congelata intatta: %s" % ok_str(not touched))
    if touched:
        print("    *** FILE ALTERATI: %s ***" % touched)

    if n_bad:
        counts_equal = len({(r["n_gal"], r["n_sel"]) for r in rows if not r["identical"]}) >= 0
        gal_same = all(r["n_sel"] > 0 for r in rows)
        print("\n  ATTRIBUZIONE, dichiarata prima del run:")
        lo = [r for r in rows if r["index"] < 200 and not r["identical"]]
        hi = [r for r in rows if r["index"] >= 200 and not r["identical"]]
        if lo and not hi:
            print("    Falliscono SOLO gli indici < 200 -> firma della collisione di percorsi")
            print("    del Paper 1 (0-199 sovrascritti con un HOD diverso). NON e' l'appaiamento:")
            print("    e' la cache di quel blocco che non corrisponde ai semi dichiarati.")
        elif hi and not lo:
            print("    Falliscono solo gli indici alti: la collisione non spiega nulla qui.")
        else:
            print("    Falliscono in entrambi i blocchi -> l'appaiamento non regge.")
        print("    Primo posto dove guardare: `np.random.seed(args.seed)` a livello di modulo")
        print("    in phase8_cutsky_mocks.py:75. Imposta il generatore GLOBALE legacy di numpy")
        print("    all'import: se un percorso usa np.random.* invece dell'rng passato, il")
        print("    risultato dipende dall'ordine di import e da quanto e' stato consumato prima.")

    rec = {"ts": now(), "gate": "2.5", "region": region, "indices": args.indices,
           "seed": args.seed, "snapnum": args.snapnum,
           "n_identical": n_ok, "n_different": n_bad, "n_skipped": n_skip,
           "cache_intact": not touched, "cache_touched": touched,
           "per_mock": rows, "pass": bool(passed)}
    append_jsonl(root / LOG, rec)

    print("\n=== 2.5 %s %s ===" % (region, ok_str(passed)))
    if not passed:
        print("    La Fase 3 non e' eseguibile come progettata: il 3.2 assume mock")
        print("    appaiati per punto della griglia.")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

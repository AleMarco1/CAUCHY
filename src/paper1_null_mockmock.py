#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, Script 2
src/paper1_null_mockmock.py

NULL TEST MOCK->MOCK  (raffinamento post-registrazione del protocollo v2 §6)

MOTIVAZIONE
-----------
Il null test originale rimappa ogni mock sulla scala di quantili MEDIA dei 2000
mock. Ma il test primario rimappa i mock sulla scala GREZZA di DESI, che e' una
singola realizzazione. Mediare 2000 scale produce un bersaglio molto piu' LISCIO
di qualunque realizzazione singola: le due trasformazioni non sono dello stesso
tipo, quindi il null non controlla esattamente cio' che dovrebbe.

Sintomi osservati nel run NGC/R5:
  * sigma_null passata da 12.3 (pilota, scala media su 20) a 47.8 (scala media
    su 2000): piu' mock si mediano, piu' la scala e' liscia, piu' la
    trasformazione nulla e' violenta;
  * la scala nulla aumenta la dispersione dei mock del +9.6%, quella di DESI
    solo del +1.3%.

QUESTO SCRIPT
-------------
Null like-for-like: il mock i viene rimappato sulla scala di quantili GREZZA del
mock j, con j = (i + shift) mod N e shift = N//2 per default (deterministico,
nessun seme, j != i sempre). Bersaglio a singola realizzazione, esattamente come
DESI nel test primario.

Costa UNA sola valutazione TDA per mock: la baseline viene RIUSATA dal file
per_mock_<region>_<tag>.jsonl prodotto da paper1_remap.py, senza ricalcolarla.

DIAGNOSTICA DELLE SCALE (gratuita, nessuna TDA)
----------------------------------------------
Per ogni mock misura la distanza L2 normalizzata della sua scala di quantili da:
  (a) la scala del mock j        -> ampiezza della trasformazione nulla NUOVA
  (b) la scala media dei mock    -> ampiezza della trasformazione nulla VECCHIA
  (c) la scala di DESI           -> ampiezza della trasformazione PRIMARIA
Se (a) ~ (c) mentre (b) << (c), il null mock->mock e' il controllo corretto e
quello a scala media sottostimava il rumore.

USO
---
  # controllo su 200 mock (~30 min) - sufficiente
  python src\\paper1_null_mockmock.py --project_root D:\\projects\\cauchy --region NGC --k 200

  # su tutti i 2000 (~4.6 h)
  python src\\paper1_null_mockmock.py --project_root D:\\projects\\cauchy --region NGC --k 2000

  # solo la diagnostica delle scale, senza TDA (pochi minuti)
  python src\\paper1_null_mockmock.py ... --stage ladders

Riprendibile: se si interrompe, rilanciare lo stesso comando.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    ap.add_argument("--k", type=int, default=200)
    ap.add_argument("--tag", default="R5",
                    help="tag del run primario da cui riusare le baseline")
    ap.add_argument("--shift", type=int, default=0,
                    help="j = (i + shift) mod N; 0 = automatico (N//2)")
    ap.add_argument("--sigma_scale", type=float, default=1.0)
    ap.add_argument("--stage", choices=["all", "ladders"], default="all")
    ap.add_argument("--no_diagrams", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
        import paper1_remap as P1          # riuso: campo costruito in modo identico
    except Exception as e:
        sys.exit(f"[FATAL] import fallito: {e}")

    desi_dir = root / "data" / "raw" / "desi_dr1"
    fld_dir = root / "data" / "processed" / "phase6_fields"
    cache_dir = root / "data" / "processed" / "paper1_mock_deltas" / args.region
    out_dir = root / "results" / "paper1"
    out_dir.mkdir(parents=True, exist_ok=True)
    curve_dir = out_dir / f"curves_{args.region}_{args.tag}_nullmm"
    curve_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"CAUCHY Paper 1 - NULL mock->mock  |  {args.region}  K={args.k}  tag={args.tag}")
    print("=" * 70)
    P1.cleanup_tmp(cache_dir, out_dir, curve_dir)

    G = P1.setup_region(M, args.region, desi_dir, fld_dir)
    mask = G["mask"]
    sigma_px = M.SIGMA_PX * args.sigma_scale
    if args.sigma_scale != 1.0:
        print(f"  sigma_px riscalato: {M.SIGMA_PX:.4f} -> {sigma_px:.4f}")

    # ---- cache e accoppiamento deterministico -----------------------------
    ok, bad = P1.validate_cache(cache_dir, M.NGRID)
    files = sorted(cache_dir.glob("delta_*.npy"))[:args.k]
    N = len(files)
    if N < 10:
        sys.exit(f"[FATAL] solo {N} campi in cache.")
    shift = args.shift if args.shift else N // 2
    if shift % N == 0:
        sys.exit("[FATAL] shift multiplo di N: darebbe j == i.")
    print(f"  campi: {N}   accoppiamento: j = (i + {shift}) mod {N}")

    # ---- riferimento DESI --------------------------------------------------
    alpha = G["sum_wd"] / G["sum_wr"]
    desi_delta = P1.compute_delta(G["field_d"], G["field_r"], alpha, mask, M.NGRID)
    desi_r, _ = P1.tda_full(P1.build_nu(desi_delta, mask, sigma_px), mask,
                            M.N_THRESH, False)
    ref = P1.FROZEN[args.region]["desi_N_H1"]
    print(f"  N_H1(DESI) = {desi_r['N_H1']:.0f}  (congelato {ref:.0f}, "
          f"scarto {100*abs(desi_r['N_H1']-ref)/ref:.3f}%)")
    Q_desi = np.sort(desi_delta[mask])

    # ---- scala media dei mock (quella del null vecchio) --------------------
    lad_p = out_dir / f"null_ladder_{args.region}_n{len(sorted(cache_dir.glob('delta_*.npy')))}.npy"
    Q_mean = np.load(lad_p) if lad_p.exists() else None
    if Q_mean is None:
        print(f"  [avviso] scala media non trovata ({lad_p.name}): "
              f"diagnostica (b) non disponibile")

    # ---- baseline riusate dal run primario ---------------------------------
    jsonl_main = out_dir / f"per_mock_{args.region}_{args.tag}.jsonl"
    main_rows = P1.read_jsonl(jsonl_main)
    if not main_rows:
        sys.exit(f"[FATAL] {jsonl_main.name} assente: eseguire prima paper1_remap.py")
    print(f"  baseline riusate dal run primario: {len(main_rows)}")

    # ---- ciclo -------------------------------------------------------------
    jsonl = out_dir / f"per_mock_{args.region}_{args.tag}_nullmm.jsonl"
    done = P1.read_jsonl(jsonl)
    todo = [(i, fp) for i, fp in enumerate(files)
            if not (fp.stem in done and
                    (args.stage == "ladders" or
                     (done[fp.stem].get("curves") and
                      (curve_dir / done[fp.stem]["curves"]).exists())))]
    print(f"  gia' completi: {N-len(todo)}   da fare: {len(todo)}")

    t0 = time.time()
    for c, (i, fp) in enumerate(todo):
        try:
            j = (i + shift) % N
            fp_j = files[j]
            x_i = np.load(fp).astype(np.float64)
            lad_j = np.sort(np.load(fp_j).astype(np.float64)[mask])   # scala GREZZA di j
            lad_i = np.sort(x_i[mask])

            # --- diagnostica delle scale (nessuna TDA) ---
            rms = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
            row = {"key": fp.stem, "i": i, "j": j, "j_key": fp_j.stem,
                   "tag": args.tag, "sigma_px": sigma_px, "ts": P1._now(),
                   "d_to_mock_j": rms(lad_i, lad_j),
                   "d_to_desi": rms(lad_i, Q_desi)}
            if Q_mean is not None and Q_mean.size == lad_i.size:
                row["d_to_mean"] = rms(lad_i, Q_mean)

            if args.stage == "all":
                p_j = (np.arange(lad_j.size, dtype=np.float64) + 0.5) / lad_j.size
                nu = P1.build_nu(P1.remap_delta(x_i, mask, lad_j, p_j), mask, sigma_px)
                s, arr = P1.tda_full(nu, mask, M.N_THRESH, not args.no_diagrams)
                row["nullmm"] = s
                base = main_rows.get(fp.stem, {}).get("base")
                if base:
                    row["base"] = base
                    row["delta_N_H1"] = s["N_H1"] - base["N_H1"]
                cf = f"nullmm_{fp.stem.split('_')[-1]}.npz"
                P1.atomic_save_npz(curve_dir / cf, arr)
                row["curves"] = cf
            P1.append_jsonl(jsonl, row)
        except KeyboardInterrupt:
            print("\n  [interrotto] risultati salvati; rilancia per riprendere.")
            raise
        except Exception as e:
            print(f"  [{fp.stem}] ERRORE: {type(e).__name__}: {e} - salto")
            continue
        if (c + 1) % 5 == 0 or c == 0:
            el = time.time() - t0
            msg = f"  [{c+1}/{len(todo)}]"
            if "delta_N_H1" in row:
                msg += f" i={i}->j={j}  dN_H1={row['delta_N_H1']:+.0f}"
            msg += f"  ({el/(c+1):.1f}s/mock, ETA {el/(c+1)*(len(todo)-c-1)/60:.0f} min)"
            print(msg)

    # ---- report -------------------------------------------------------------
    rec = P1.read_jsonl(jsonl)
    rows = list(rec.values())
    print("\n" + "=" * 70)
    print("REPORT")
    print("=" * 70)

    d_j = np.array([r["d_to_mock_j"] for r in rows])
    d_d = np.array([r["d_to_desi"] for r in rows])
    has_mean = all("d_to_mean" in r for r in rows)
    print("  Distanza RMS fra scale di quantili (delta grezzo):")
    print(f"    mock_i -> mock_j (null NUOVO)  : {d_j.mean():.4f} +/- {d_j.std(ddof=1):.4f}")
    if has_mean:
        d_m = np.array([r["d_to_mean"] for r in rows])
        print(f"    mock_i -> media  (null VECCHIO): {d_m.mean():.4f} +/- {d_m.std(ddof=1):.4f}")
    print(f"    mock_i -> DESI   (PRIMARIO)    : {d_d.mean():.4f} +/- {d_d.std(ddof=1):.4f}")
    if has_mean:
        print(f"    rapporto (i->j)/(i->DESI) = {d_j.mean()/d_d.mean():.3f}   "
              f"(i->media)/(i->DESI) = {d_m.mean()/d_d.mean():.3f}")
        print("    -> il null e' un controllo equo quanto piu' il suo rapporto e' vicino a 1")

    out = {"schema_version": "1.0", "script": "paper1_null_mockmock.py",
           "protocol": "v2 §6 - raffinamento POST-REGISTRAZIONE (§12)",
           "timestamp": P1._now(), "region": args.region, "tag": args.tag,
           "sigma_px": sigma_px, "n_mocks": len(rows), "shift": shift,
           "pairing": f"j = (i + {shift}) mod {N}",
           "ladder_distance_rms": {
               "mock_to_mock": float(d_j.mean()), "mock_to_desi": float(d_d.mean()),
               **({"mock_to_mean": float(d_m.mean()),
                   "ratio_mm_over_desi": float(d_j.mean()/d_d.mean()),
                   "ratio_mean_over_desi": float(d_m.mean()/d_d.mean())} if has_mean else {})},
           "desi": desi_r}

    with_tda = [r for r in rows if "delta_N_H1" in r]
    if with_tda:
        d = np.array([r["delta_N_H1"] for r in with_tda])
        base = np.array([r["base"]["N_H1"] for r in with_tda])
        nmm = np.array([r["nullmm"]["N_H1"] for r in with_tda])
        D = base.mean() - desi_r["N_H1"]
        f_mm = -d.mean() / D
        sigma_mm = float(d.std(ddof=1))
        eta_mm = 3 * sigma_mm / abs(D)
        sem = sigma_mm / np.sqrt(len(d))
        print(f"\n  Null mock->mock (N={len(d)}):")
        print(f"    base   = {base.mean():.1f} +/- {base.std(ddof=1):.1f}")
        print(f"    nullmm = {nmm.mean():.1f} +/- {nmm.std(ddof=1):.1f}")
        print(f"    spostamento medio = {d.mean():+.1f} +/- {sem:.1f} loop  "
              f"({abs(d.mean())/sem:.1f} sigma)")
        print(f"    f_null_mm = {f_mm:+.5f}     sigma_null_mm = {sigma_mm:.1f} loop")
        print(f"    eta_mm = 3*sigma/D = {eta_mm:.5f}")
        print(f"\n  CONFRONTO col null a scala media (run primario):")
        print(f"    sigma_null  vecchio = 47.8   nuovo = {sigma_mm:.1f}   "
              f"({sigma_mm/47.8:.2f}x)")
        print(f"    l'effetto primario e' 102 loop: rapporto effetto/rumore = "
              f"{102/sigma_mm:.1f} per mock, {102/sem:.0f} sulla media")
        out.update({"mock_baseline_mean": float(base.mean()),
                    "mock_nullmm_mean": float(nmm.mean()),
                    "mock_nullmm_std": float(nmm.std(ddof=1)),
                    "D": float(D), "f_null_mm": float(f_mm),
                    "sigma_null_mm": sigma_mm, "eta_mm": float(eta_mm),
                    "mean_shift_loops": float(d.mean()), "sem_loops": float(sem)})

    out["notes"] = ("Null like-for-like: bersaglio a singola realizzazione (scala grezza "
                    "di un altro mock), stesso tipo del bersaglio DESI del test primario. "
                    "Sostituisce come controllo di riferimento il null a scala media, che "
                    "usa un bersaglio piu' liscio e non e' quindi confrontabile col "
                    "primario. Raffinamento non pre-registrato: nato da un'osservazione "
                    "fatta in fase di analisi (salto di sigma_null fra pilota e produzione). "
                    "Da dichiarare come post-registrazione ai sensi del protocollo v2 §12.")
    P1.atomic_write_text(out_dir / f"paper1_nullmm_{args.region}_{args.tag}.json",
                         json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n[scritto] paper1_nullmm_{args.region}_{args.tag}.json")
    print("\n[fine]")


if __name__ == "__main__":
    main()

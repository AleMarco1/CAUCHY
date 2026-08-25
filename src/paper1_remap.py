#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, Script 1 (v3 - crash-safe + curve di Betti salvate)
src/paper1_remap.py

Esperimento primario del Paper 1 (protocollo v2, §4-§8): quanta parte del
deficit di generatori H1 e' spiegabile dalla sola struttura a un punto?

NOVITA' v2 - RESILIENZA A INTERRUZIONI (blackout, kill, crash)
--------------------------------------------------------------
  * Risultati su file JSONL APPEND-ONLY (una riga per mock, flush+fsync):
    un'interruzione puo' troncare al massimo l'ultima riga, che viene
    scartata in lettura. Nessun rischio di perdere il run.
  * Tutte le scritture di file interi sono ATOMICHE (tmp + os.replace).
  * Cache dei campi delta validata all'avvio (dimensione attesa); i file
    troncati da un'interruzione vengono eliminati e rigenerati.
  * Scala di quantili nulla CONGELATA su disco: non va ricalcolata a ogni
    ripresa e garantisce che un run ripreso usi lo stesso bersaglio.
  * Ripresa automatica: rilanciare lo stesso comando riprende da dove si era
    fermato. Nessun flag da ricordare.

METODO (protocollo v2 §4)
-------------------------
La rimappatura rank-order agisce sul delta GREZZO, PRIMA di log e smoothing:
la persistenza di supralivello dipende solo dall'ORDINAMENTO delle celle,
quindi un remap post-smoothing lascerebbe N_H1 esattamente invariato
(lemma §3bis). L'unico canale one-point e' l'interazione con lo smoothing.

STATISTICA PRIMARIA
-------------------
  N_H1 = numero totale di generatori H1 = feats[4] ("beta1_max" nel codice
         CAUCHY). Secondaria: b1_peak = feats[1], picco della curva di Betti.

USO
---
  # pilota
  python src\\paper1_remap.py --project_root D:\\projects\\cauchy --region NGC --k 20

  # produzione (riprendibile: se si interrompe, RILANCIA LO STESSO COMANDO)
  python src\\paper1_remap.py --project_root D:\\projects\\cauchy --region NGC --k 2000

  # solo una fase
  python src\\paper1_remap.py ... --stage cache
  python src\\paper1_remap.py ... --stage experiment

  # shard paralleli sulla cache (piu' finestre, stessa cartella)
  python src\\paper1_remap.py ... --stage cache --i0 0    --i1 500
  python src\\paper1_remap.py ... --stage cache --i0 500  --i1 1000

  # scansione dello smoothing (§9.2) su un sottoinsieme, riusa la stessa cache
  python src\\paper1_remap.py ... --stage experiment --k 200 --sigma_scale 2.0 --tag R10

  # verifica integrale della cache (lenta: apre ogni file)
  python src\\paper1_remap.py ... --stage verify
"""

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

FROZEN = {
    "NGC": {"desi_N_H1": 28256.0, "mock_baseline": 35467.15, "D": 7211.15},
    "SGC": {"desi_N_H1": 15122.0, "mock_baseline": 18693.595, "D": 3571.595},
}
SELFCHECK_TOL = 0.005


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# I/O ATOMICO E DUREVOLE
# ---------------------------------------------------------------------------
def atomic_write_text(path: Path, text: str):
    """Scrittura atomica: se salta la corrente, il file originale resta intatto."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)          # atomica su NTFS e POSIX


def atomic_save_npy(path: Path, arr: np.ndarray):
    """np.save atomico: nessun .npy troncato in cache."""
    tmp = path.with_suffix(".npy.tmp")
    with open(tmp, "wb") as f:
        np.save(f, arr)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_save_npz(path: Path, arrays: dict):
    """np.savez atomico per curve di Betti e diagrammi di persistenza."""
    tmp = path.with_suffix(".npz.tmp")
    with open(tmp, "wb") as f:
        np.savez_compressed(f, **arrays)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def append_jsonl(path: Path, obj: dict):
    """Append durevole di una riga JSON (flush + fsync a ogni riga)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path: Path):
    """Legge un JSONL scartando in silenzio una eventuale ultima riga troncata."""
    out = {}
    if not path.exists():
        return out
    n_bad = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                n_bad += 1
                continue
            out[o["key"]] = o
    if n_bad:
        print(f"  [ripresa] {n_bad} riga/e incompleta/e scartata/e in {path.name} "
              f"(normale dopo un'interruzione)")
    return out


def cleanup_tmp(*dirs):
    """Rimuove i .tmp lasciati da un'interruzione."""
    n = 0
    for d in dirs:
        if d and d.exists():
            for p in list(d.glob("*.tmp")) + list(d.glob("*.npy.tmp")):
                try:
                    p.unlink()
                    n += 1
                except OSError:
                    pass
    if n:
        print(f"  [ripresa] rimossi {n} file temporanei incompleti")


# ---------------------------------------------------------------------------
# Pipeline: delta grezzo <-> nu
# ---------------------------------------------------------------------------
def compute_delta(field_d, field_r, alpha, mask, ngrid):
    delta = np.zeros((ngrid, ngrid, ngrid), dtype=np.float64)
    denom = alpha * field_r
    valid = denom > 0
    delta[valid] = (field_d[valid] - denom[valid]) / denom[valid]
    delta[~mask] = 0.0
    return delta


def build_nu(delta, mask, sigma_px):
    nu = np.zeros_like(delta, dtype=np.float64)
    nu[mask] = np.log(1.0 + np.clip(delta[mask], -1.0 + 1e-3, None))
    nu = gaussian_filter(nu, sigma=sigma_px)
    nu[~mask] = 0.0
    nu[mask] -= nu[mask].mean()
    return nu.astype(np.float32)


# ---------------------------------------------------------------------------
# Remapping
# ---------------------------------------------------------------------------
def quantile_ladder(target_values):
    Q = np.sort(np.asarray(target_values, dtype=np.float64))
    p = (np.arange(Q.size, dtype=np.float64) + 0.5) / Q.size
    return Q, p


def rank_remap(values, Q, p):
    v = np.asarray(values, dtype=np.float64)
    M = v.size
    order = np.argsort(v, kind="stable")
    ranks = np.empty(M, dtype=np.float64)
    ranks[order] = np.arange(M, dtype=np.float64)
    return np.interp((ranks + 0.5) / M, p, Q)


def remap_delta(delta, mask, Q, p):
    out = np.asarray(delta, dtype=np.float64).copy()
    out[mask] = rank_remap(out[mask], Q, p)
    return out


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------
def setup_region(M, region, desi_dir, fld_dir):
    if region == "NGC":
        field_r, sum_wr = M.load_desi_random_field()
        field_d, sum_wd = M.load_desi_data_field()
        mask_path = fld_dir / "bgs_ngc_mask_128.npy"
        if not mask_path.exists():
            sys.exit(f"[FATAL] maschera NGC mancante: {mask_path}")
        mask = np.load(mask_path).astype(bool)
        n_data = None
        print(f"  NGC: box={M.BOX_SIZE:.1f}  cell={M.CELL:.3f}  sigma_px={M.SIGMA_PX:.4f}")
    else:
        import phase9_sgc_likeforlike as S
        ran = desi_dir / "BGS_BRIGHT-21.5_SGC_0_clustering.ran.fits"
        dat = desi_dir / "BGS_BRIGHT-21.5_SGC_clustering.dat.fits"
        nz = desi_dir / "BGS_BRIGHT-21.5_SGC_nz.txt"
        for pth in (ran, dat, nz):
            if not pth.exists():
                sys.exit(f"[FATAL] file SGC mancante: {pth}")
        pos_r, w_r = S.sgc_positions(ran, wkeys=("WEIGHT_FKP",), M=M)
        box_min = pos_r.min(axis=0) - 5.0
        box_size = float(((pos_r.max(axis=0) + 5.0) - box_min).max())
        cell = box_size / M.NGRID
        M.BOX_MIN, M.BOX_SIZE, M.CELL = box_min, box_size, cell
        M.SIGMA_PX = M.R_SMOOTH / cell
        M.RAN_FITS, M.NZ_FILE = ran, nz
        field_r = M.cic_3d(pos_r, w_r, M.NGRID, box_min, box_size)
        sum_wr = float(w_r.sum())
        pos_d, w_d = S.sgc_positions(dat, wkeys=("WEIGHT", "WEIGHT_FKP"), M=M)
        field_d = M.cic_3d(pos_d, w_d, M.NGRID, box_min, box_size)
        sum_wd = float(w_d.sum())
        n_data = int(len(pos_d))
        M.N_TARGET_BGS = n_data
        mask_path = fld_dir / "bgs_sgc_mask_128.npy"
        mask = None
        if mask_path.exists():
            m0 = np.load(mask_path).astype(bool)
            ijk = np.clip(((pos_d - box_min[None, :]) / cell).astype(int), 0, M.NGRID - 1)
            inside = m0[ijk[:, 0], ijk[:, 1], ijk[:, 2]].mean()
            if inside > 0.90:
                mask = m0
                print(f"  maschera SGC congelata OK ({100*inside:.1f}% dei dati dentro)")
        if mask is None:
            ref = field_r[field_r > 0].mean()
            mask = field_r > 0.01 * ref
            print(f"  maschera SGC ricostruita dai random: fill {100*mask.mean():.2f}%")
        print(f"  SGC: box={box_size:.1f}  cell={cell:.3f}  sigma_px={M.SIGMA_PX:.4f}  "
              f"N_dati={n_data}")

    nz_z, nz_target = M.load_bgs_nz()
    return dict(field_r=field_r, sum_wr=sum_wr, field_d=field_d, sum_wd=sum_wd,
                mask=mask, nz_z=nz_z, nz_target=nz_target, n_data=n_data)


def tda(M, nu, mask):
    feats = M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)
    return dict(N_H1=float(feats[4]), b1_peak=float(feats[1]),
                peak_nu=float(feats[0]), mean_pers1=float(feats[5]))


# ---------------------------------------------------------------------------
# REPLICA ESATTA di phase8_cutsky_mocks.compute_tda_features che, in piu',
# RESTITUISCE la curva di Betti e il diagramma H1 (che l'originale scarta).
# L'identita' numerica con l'originale e' verificata a ogni selfcheck.
# ---------------------------------------------------------------------------
def compute_tda_full(delta_field, mask, n_thresh=100, masked=True):
    import gudhi
    field = delta_field.astype(np.float64)
    field_in = field[mask]
    thresholds = np.linspace(float(np.percentile(field_in, 1)),
                             float(np.percentile(field_in, 99)), n_thresh)
    SENT = 1.0e6
    if masked:
        field_work = field.copy()
        field_work[~mask] = -SENT
        field_neg = -field_work
        cutoff = SENT / 2.0
    else:
        field_neg = -field
        cutoff = np.inf

    cc = gudhi.CubicalComplex(dimensions=list(field_neg.shape),
                              top_dimensional_cells=field_neg.flatten())
    cc.compute_persistence()
    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    def proc(diag):
        if len(diag) == 0:
            return np.array([]), np.array([]), np.array([])
        d = np.array(diag)
        keep = np.isfinite(d[:, 1]) & (d[:, 0] < cutoff) & (d[:, 1] < cutoff)
        df = d[keep]
        b, dth = -df[:, 0], -df[:, 1]
        return b, dth, b - dth

    b0, d0, _ = proc(diag_0)
    b1, d1, p1 = proc(diag_1)

    b1_curve = np.zeros(n_thresh)
    b0_curve = np.zeros(n_thresh)
    for k, nu in enumerate(thresholds):
        if len(b0):
            b0_curve[k] = np.sum((b0 >= nu) & (d0 < nu))
        if len(b1):
            b1_curve[k] = np.sum((b1 >= nu) & (d1 < nu))

    feats = np.zeros(8, dtype=np.float64)
    if b1_curve.max() > 0:
        pk = np.argmax(b1_curve)
        feats[0] = thresholds[pk]
        feats[1] = b1_curve[pk]
        half = b1_curve.max() / 2.0
        above = np.where(b1_curve >= half)[0]
        feats[2] = (thresholds[above[-1]] - thresholds[above[0]]) if len(above) > 1 else 0.0
        feats[3] = np.trapezoid(b1_curve, thresholds)
    if len(p1) > 0:
        feats[4] = len(p1)
        feats[5] = float(np.mean(p1))
        feats[6] = float(np.sum(p1 >= np.percentile(p1, 90)))
    mean_val = float(field[mask].mean())
    feats[7] = b0_curve[np.argmin(np.abs(thresholds - mean_val))]
    return feats, thresholds, b0_curve, b1_curve, b1, d1


def tda_full(nu, mask, n_thresh, save_diag=True):
    """Ritorna (sommario, blocco-arrays-da-salvare)."""
    feats, th, b0c, b1c, h1b, h1d = compute_tda_full(nu, mask, n_thresh, masked=True)
    summary = dict(N_H1=float(feats[4]), b1_peak=float(feats[1]),
                   peak_nu=float(feats[0]), mean_pers1=float(feats[5]),
                   b1_fwhm=float(feats[2]), b1_integral=float(feats[3]),
                   n_pers_top10=float(feats[6]), b0_at_mean=float(feats[7]))
    arrays = {"thresholds": th.astype(np.float32),
              "b0_curve": b0c.astype(np.float32),
              "b1_curve": b1c.astype(np.float32)}
    if save_diag:
        arrays["h1_birth"] = h1b.astype(np.float32)
        arrays["h1_death"] = h1d.astype(np.float32)
    return summary, arrays


# ---------------------------------------------------------------------------
# CACHE: validazione, riparazione, generazione
# ---------------------------------------------------------------------------
def expected_npy_size(ngrid):
    """128^3 float32 + header .npy (128 byte con allineamento standard)."""
    return ngrid ** 3 * 4 + 128


def validate_cache(cache_dir: Path, ngrid: int, deep: bool = False):
    """Elimina i .npy troncati/corrotti. deep=True apre davvero ogni file."""
    if not cache_dir.exists():
        return 0, 0
    exp = expected_npy_size(ngrid)
    ok = bad = 0
    for p in sorted(cache_dir.glob("delta_*.npy")):
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        good = (sz == exp)
        if good and deep:
            try:
                a = np.load(p, mmap_mode="r")
                good = (a.shape == (ngrid, ngrid, ngrid))
            except Exception:
                good = False
        if good:
            ok += 1
        else:
            print(f"  [riparazione] {p.name} corrotto ({sz} byte invece di {exp}) - elimino")
            try:
                p.unlink()
            except OSError:
                pass
            bad += 1
    return ok, bad


def stage_cache(M, G, cache_dir, k, i0, i1, snapnum, seed):
    import phase8_test2_masked as T2
    print("\n" + "=" * 70)
    print(f"STAGE cache  (mock {i0}..{min(i1, k)-1})")
    print("=" * 70)
    cache_dir.mkdir(parents=True, exist_ok=True)
    ok, bad = validate_cache(cache_dir, M.NGRID)
    print(f"  cache esistente: {ok} validi, {bad} rigenerati")
    hod = M.HOD_MEDIAN
    done = skipped = failed = 0
    t0 = time.time()
    for kk in range(i0, min(i1, k)):
        out = cache_dir / f"delta_{kk:04d}.npy"
        if out.exists():
            skipped += 1
            continue
        try:
            rng = np.random.default_rng(seed + kk)
            pos_h, mass_h, vel_h = M.read_halo_catalog(kk, snapnum)
            if pos_h is None or len(pos_h) < 50:
                failed += 1
                continue
            pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h, hod, rng)
            if len(pos_gal) < 100:
                failed += 1
                continue
            pos_sel = M.carve_cutsky(pos_gal, vel_gal, G["mask"],
                                     G["nz_z"], G["nz_target"], rng)
            if pos_sel is None or len(pos_sel) < 100:
                failed += 1
                continue
            w_d = np.ones(len(pos_sel))
            field_d = M.cic_3d(pos_sel, w_d, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
            alpha = float(w_d.sum()) / G["sum_wr"]
            delta = compute_delta(field_d, G["field_r"], alpha, G["mask"], M.NGRID)
            atomic_save_npy(out, delta.astype(np.float32))
            done += 1
        except KeyboardInterrupt:
            print("\n  [interrotto] la cache e' consistente; rilancia per riprendere.")
            raise
        except Exception as e:
            print(f"  [{kk}] ERRORE: {type(e).__name__}: {e} - salto")
            failed += 1
            continue
        if done % 10 == 0 or done == 1:
            el = time.time() - t0
            left = min(i1, k) - kk - 1
            print(f"  [{kk}] nuovi={done}  ({el/done:.1f}s/mock, "
                  f"ETA {el/done*left/60:.1f} min)")
    print(f"  nuovi={done}  gia'_presenti={skipped}  falliti={failed}")


# ---------------------------------------------------------------------------
# SCALA DI QUANTILI NULLA: calcolata una volta, congelata su disco
# ---------------------------------------------------------------------------
def get_null_ladder(cache_dir: Path, out_dir: Path, mask, k, region, force=False):
    # La scala nulla e' costruita su TUTTA la cache disponibile, NON troncata da
    # --k: cosi' resta identica fra il run primario (k=2000) e le scansioni di
    # smoothing (k=200), rendendo i risultati confrontabili fra tag diversi.
    # Il numero di mock e' nel nome del file: una cache diversa produce un file
    # diverso invece di sovrascrivere silenziosamente quello vecchio.
    files = sorted(cache_dir.glob("delta_*.npy"))
    if not files:
        sys.exit("[FATAL] cache vuota: eseguire prima --stage cache")
    lad_p = out_dir / f"null_ladder_{region}_n{len(files)}.npy"
    meta_p = out_dir / f"null_ladder_{region}_n{len(files)}.json"

    if lad_p.exists() and meta_p.exists() and not force:
        meta = json.loads(meta_p.read_text())
        Q = np.load(lad_p)
        if meta.get("n_mocks") == len(files) and Q.size == int(mask.sum()):
            print(f"  scala nulla congelata riusata ({meta['n_mocks']} mock)")
            return Q, (np.arange(Q.size, dtype=np.float64) + 0.5) / Q.size, meta
        print("  scala nulla su disco incoerente - ricalcolo")

    print(f"  costruzione scala nulla da {len(files)} mock ...")
    acc = None
    t0 = time.time()
    for i, fp in enumerate(files):
        v = np.sort(np.load(fp).astype(np.float64)[mask])
        acc = v if acc is None else acc + v
        if (i + 1) % 200 == 0:
            print(f"    {i+1}/{len(files)}  ({time.time()-t0:.0f}s)")
    Q = acc / len(files)
    atomic_save_npy(lad_p, Q)
    meta = {"n_mocks": len(files), "n_voxels": int(Q.size), "created": _now(),
            "files_first": files[0].name, "files_last": files[-1].name}
    atomic_write_text(meta_p, json.dumps(meta, indent=2))
    print(f"  scala nulla congelata in {lad_p.name}")
    return Q, (np.arange(Q.size, dtype=np.float64) + 0.5) / Q.size, meta


# ---------------------------------------------------------------------------
def stage_experiment(M, G, cache_dir, out_dir, k, sigma_px, desi_delta, tag, region,
                     save_diag=True):
    print("\n" + "=" * 70)
    print(f"STAGE experiment  (sigma_px={sigma_px:.4f}, tag={tag})")
    print("=" * 70)
    mask = G["mask"]
    out_dir.mkdir(parents=True, exist_ok=True)
    curve_dir = out_dir / f"curves_{region}_{tag}"
    curve_dir.mkdir(parents=True, exist_ok=True)
    cleanup_tmp(curve_dir)
    jsonl = out_dir / f"per_mock_{region}_{tag}.jsonl"

    ok, bad = validate_cache(cache_dir, M.NGRID)
    if bad:
        print(f"  ATTENZIONE: {bad} campi corrotti eliminati - rilanciare --stage cache")
    files = sorted(cache_dir.glob("delta_*.npy"))[:k]
    print(f"  campi in cache: {len(files)}")

    done = read_jsonl(jsonl)
    # si riprende solo se ESISTONO sia la riga sia il file delle curve
    todo = [fp for fp in files
            if not (fp.stem in done and done[fp.stem].get("curves")
                    and (curve_dir / done[fp.stem]["curves"]).exists())]
    print(f"  gia' completi: {len(files)-len(todo)}   da fare: {len(todo)}")

    Q_desi, p_desi = quantile_ladder(desi_delta[mask])
    Q_null, p_null, lad_meta = get_null_ladder(cache_dir, out_dir, mask, k, region)

    t0 = time.time()
    for j, fp in enumerate(todo):
        try:
            idx = fp.stem.split("_")[-1]
            delta = np.load(fp).astype(np.float64)
            row = {"key": fp.stem, "tag": tag, "sigma_px": sigma_px, "ts": _now()}
            blocks = {}
            for name, dd in (("base", delta),
                             ("remap", remap_delta(delta, mask, Q_desi, p_desi)),
                             ("null", remap_delta(delta, mask, Q_null, p_null))):
                s, arr = tda_full(build_nu(dd, mask, sigma_px), mask, M.N_THRESH, save_diag)
                row[name] = s
                for kk, vv in arr.items():
                    blocks[f"{name}__{kk}"] = vv
            cf = f"curves_{idx}.npz"
            atomic_save_npz(curve_dir / cf, blocks)   # PRIMA le curve ...
            row["curves"] = cf
            append_jsonl(jsonl, row)                  # ... POI la riga di indice
        except KeyboardInterrupt:
            print("\n  [interrotto] risultati salvati fino a qui; rilancia per riprendere.")
            raise
        except Exception as e:
            print(f"  [{fp.stem}] ERRORE: {type(e).__name__}: {e} - salto")
            continue
        if (j + 1) % 5 == 0 or j == 0:
            el = time.time() - t0
            print(f"  [{j+1}/{len(todo)}] base={row['base']['N_H1']:.0f} "
                  f"remap={row['remap']['N_H1']:.0f} null={row['null']['N_H1']:.0f}  "
                  f"({el/(j+1):.0f}s/mock, ETA {el/(j+1)*(len(todo)-j-1)/3600:.1f} h)")

    # mirror (§7): DESI rimappato sulla PDF media dei mock
    print("  mirror: DESI -> PDF media mock ...")
    mir_s, mir_arr = tda_full(build_nu(remap_delta(desi_delta, mask, Q_null, p_null),
                                       mask, sigma_px), mask, M.N_THRESH, save_diag)
    atomic_save_npz(out_dir / f"curves_DESI_mirror_{region}_{tag}.npz", mir_arr)
    print(f"    N_H1(DESI remappato) = {mir_s['N_H1']:.0f}")
    return read_jsonl(jsonl), mir_s, lad_meta


# ---------------------------------------------------------------------------
def stage_report(rec, mirror, region, tag, desi_r, out_dir, sigma_px, meta, lad_meta):
    print("\n" + "=" * 70)
    print("STAGE report")
    print("=" * 70)
    rows = [v for v in rec.values() if v.get("tag") == tag]
    if len(rows) < 3:
        sys.exit("[FATAL] troppi pochi mock per il report.")
    base = np.array([r["base"]["N_H1"] for r in rows])
    remap = np.array([r["remap"]["N_H1"] for r in rows])
    null = np.array([r["null"]["N_H1"] for r in rows])
    pk_b = np.array([r["base"]["b1_peak"] for r in rows])
    pk_r = np.array([r["remap"]["b1_peak"] for r in rows])

    desi = desi_r["N_H1"]
    n = len(rows)
    D = base.mean() - desi
    f_1p = (base.mean() - remap.mean()) / D
    f_null = (base.mean() - null.mean()) / D
    sigma_null = float((null - base).std(ddof=1))
    # errore su f_1p: dispersione appaiata (remap - base), non le due std separate
    d_pair = base - remap
    sem_f = float(d_pair.std(ddof=1) / np.sqrt(n) / abs(D))
    eta = 3.0 * sigma_null / abs(D)
    g_1p = (mirror["N_H1"] - desi) / D
    thr = max(0.2, eta)
    if f_1p >= 1 - thr and g_1p >= 1 - thr:
        verdict = "ONE_POINT"
    elif f_1p <= thr and g_1p <= thr:
        verdict = "PHASE_CONNECTIVITY"
    else:
        verdict = "MIXED"

    # deficit "corretto per one-point": mock con PDF di DESI vs DESI
    D_corr_fwd = remap.mean() - desi
    D_corr_mir = base.mean() - mirror["N_H1"]

    print(f"  N mock            : {n}")
    print(f"  N_H1 DESI         : {desi:.0f}")
    print(f"  N_H1 mock baseline: {base.mean():.1f} +/- {base.std(ddof=1):.1f}")
    print(f"  N_H1 mock remap   : {remap.mean():.1f} +/- {remap.std(ddof=1):.1f}")
    print(f"  N_H1 mock null    : {null.mean():.1f} +/- {null.std(ddof=1):.1f}")
    print(f"  D (deficit)       : {D:.1f}")
    print(f"  f_1p              : {f_1p:+.4f} +/- {sem_f:.4f}")
    print(f"  g_1p (speculare)  : {g_1p:+.4f}")
    print(f"  f_null            : {f_null:+.5f}   sigma_null = {sigma_null:.1f} loop")
    print(f"  eta = 3 sigma/D   : {eta:.4f}    soglia = {thr:.4f}")
    print(f"  deficit corretto  : avanti {D_corr_fwd:.0f}  speculare {D_corr_mir:.0f} "
          f"(grezzo {D:.0f})")
    print(f"  b1_peak DESI/mock : {desi_r['b1_peak']:.0f} / {pk_b.mean():.0f}  "
          f"(deficit {100*(1-desi_r['b1_peak']/pk_b.mean()):.1f}%)")
    print(f"\n  >>> VERDETTO (§8): {verdict}")

    out = {
        "schema_version": "3.0", "script": "paper1_remap.py (v3)",
        "paper": "Paper 1 - one-point vs H1 topology",
        "protocol": "prereg v2 §4-§8", "timestamp": _now(),
        "region": region, "tag": tag, "sigma_px": sigma_px, "n_mocks": n,
        "statistic_primary": "N_H1 = numero di generatori H1 (feats[4])",
        "desi": desi_r, "mirror": mirror,
        "mock_baseline_mean": float(base.mean()), "mock_baseline_std": float(base.std(ddof=1)),
        "mock_remap_mean": float(remap.mean()), "mock_remap_std": float(remap.std(ddof=1)),
        "mock_null_mean": float(null.mean()), "mock_null_std": float(null.std(ddof=1)),
        "D": float(D), "D_corrected_forward": float(D_corr_fwd),
        "D_corrected_mirror": float(D_corr_mir),
        "f_1p": float(f_1p), "f_1p_sem": sem_f, "g_1p": float(g_1p),
        "f_null": float(f_null), "sigma_null": sigma_null, "eta": float(eta),
        "threshold_used": float(thr), "verdict": verdict,
        "secondary_b1_peak": {"desi": desi_r["b1_peak"],
                              "base_mean": float(pk_b.mean()),
                              "remap_mean": float(pk_r.mean()),
                              "deficit_frac": float(1 - desi_r["b1_peak"] / pk_b.mean())},
        "null_ladder": lad_meta, "frozen_reference": FROZEN[region], "meta": meta,
        "notes": ("Rimappatura sul delta GREZZO (pre-log, pre-smoothing): la "
                  "persistenza di supralivello e' invariante per trasformazioni "
                  "monotone, quindi un remap post-smoothing darebbe f_1p=0 per "
                  "costruzione. Vedi protocollo v2 §3bis. Valori NEGATIVI di f_1p/g_1p "
                  "indicano che il canale one-point agisce in direzione OPPOSTA al "
                  "deficit: correggendo per la struttura a un punto il deficit si allarga."),
    }
    atomic_write_text(out_dir / f"paper1_remap_{region}_{tag}.json",
                      json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n[scritto] {out_dir / f'paper1_remap_{region}_{tag}.json'}")
    return out


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--i0", type=int, default=0)
    ap.add_argument("--i1", type=int, default=10**9)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--stage", choices=["selfcheck", "cache", "experiment",
                                        "report", "verify", "all"], default="all")
    ap.add_argument("--sigma_scale", type=float, default=1.0)
    ap.add_argument("--tag", default="R5")
    ap.add_argument("--no_diagrams", action="store_true",
                    help="non salvare i diagrammi H1 (solo curve): ~5x meno disco")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
    except Exception as e:
        sys.exit(f"[FATAL] import di phase8_cutsky_mocks fallito: {e}")

    desi_dir = root / "data" / "raw" / "desi_dr1"
    fld_dir = root / "data" / "processed" / "phase6_fields"
    cache_dir = root / "data" / "processed" / "paper1_mock_deltas" / args.region
    out_dir = root / "results" / "paper1"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"CAUCHY Paper 1 - remapping v3  |  {args.region}  K={args.k}  tag={args.tag}")
    print("=" * 70)
    cleanup_tmp(cache_dir, out_dir)

    if args.stage == "verify":
        ok, bad = validate_cache(cache_dir, 128, deep=True)
        print(f"  verifica integrale: {ok} validi, {bad} eliminati")
        return

    G = setup_region(M, args.region, desi_dir, fld_dir)
    sigma_px = M.SIGMA_PX * args.sigma_scale
    if args.sigma_scale != 1.0:
        print(f"  sigma_px riscalato: {M.SIGMA_PX:.4f} -> {sigma_px:.4f}")

    meta = {"box_size": float(M.BOX_SIZE), "cell": float(M.CELL),
            "sigma_px_canonical": float(M.SIGMA_PX), "sigma_px_used": float(sigma_px),
            "n_thresh": int(M.N_THRESH), "ngrid": int(M.NGRID),
            "mask_fill_pct": float(100 * G["mask"].mean()),
            "snapnum": args.snapnum, "seed": args.seed}

    desi_delta = desi_r = None
    if args.stage in ("selfcheck", "all", "experiment", "report"):
        print("\n" + "=" * 70)
        print("STAGE selfcheck")
        print("=" * 70)
        alpha = G["sum_wd"] / G["sum_wr"]
        desi_delta = compute_delta(G["field_d"], G["field_r"], alpha, G["mask"], M.NGRID)
        nu_mine = build_nu(desi_delta, G["mask"], sigma_px)
        nu_mod = M.build_field(G["field_d"], G["field_r"], alpha, G["mask"])
        if args.sigma_scale == 1.0:
            dmax = float(np.abs(nu_mine.astype(np.float64) - nu_mod.astype(np.float64)).max())
            print(f"  build_field identica al modulo : {np.array_equal(nu_mine, nu_mod)}  "
                  f"(max|diff|={dmax:.3e})")
            if dmax > 1e-6:
                sys.exit("[FATAL] ricostruzione di build_field NON coincidente.")
        t0 = time.time()
        desi_r, desi_arr = tda_full(nu_mine, G["mask"], M.N_THRESH, not args.no_diagrams)
        # verifica che la replica sia IDENTICA all'originale del modulo
        feats_mod = M.compute_tda_features(nu_mine, G["mask"], M.N_THRESH, masked=True)
        feats_mine = np.array([desi_r["peak_nu"], desi_r["b1_peak"], desi_r["b1_fwhm"],
                               desi_r["b1_integral"], desi_r["N_H1"], desi_r["mean_pers1"],
                               desi_r["n_pers_top10"], desi_r["b0_at_mean"]])
        dmax_f = float(np.abs(feats_mine - np.asarray(feats_mod, dtype=float)).max())
        print(f"  compute_tda_full identica al modulo (8 feature): "
              f"{np.allclose(feats_mine, feats_mod, rtol=0, atol=0)}  (max|diff|={dmax_f:.3e})")
        if dmax_f > 1e-9:
            sys.exit("[FATAL] la replica di compute_tda_features NON coincide col modulo.")
        atomic_save_npz(out_dir / f"curves_DESI_{args.region}_{args.tag}.npz", desi_arr)
        ref = FROZEN[args.region]["desi_N_H1"]
        rel = abs(desi_r["N_H1"] - ref) / ref
        print(f"  N_H1(DESI {args.region}) = {desi_r['N_H1']:.0f}   congelato = {ref:.0f}   "
              f"scarto = {100*rel:.3f}%   [{time.time()-t0:.1f}s]")
        if args.sigma_scale == 1.0 and rel > SELFCHECK_TOL:
            print("  *** ATTENZIONE: scarto oltre tolleranza ***")
        else:
            print("  -> test di chiusura SUPERATO")

    if args.stage in ("cache", "all"):
        stage_cache(M, G, cache_dir, args.k, args.i0, args.i1, args.snapnum, args.seed)

    if args.stage in ("experiment", "all", "report"):
        rec, mirror, lad_meta = stage_experiment(M, G, cache_dir, out_dir, args.k,
                                                 sigma_px, desi_delta, args.tag,
                                                 args.region, not args.no_diagrams)
        stage_report(rec, mirror, args.region, args.tag, desi_r, out_dir,
                     sigma_px, meta, lad_meta)

    print("\n[fine]")


if __name__ == "__main__":
    main()

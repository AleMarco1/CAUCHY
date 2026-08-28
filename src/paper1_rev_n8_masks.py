#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n8_masks.py

N8 - TRASFERIBILITA' DEL CRITERIO w_bar >= 0.99

Referee 1 §6 osserva che il collasso e' dimostrato su due footprint che sono
entrambi cunei sottili della stessa survey, con profondita' mediana quasi
identica (3.0 e 2.8 voxel): chiamarlo survey-independent e trasferibile e'
prematuro. Suggerisce come computazionalmente banale e dirimente un test su
maschere sintetiche - campi gaussiani con profondita' controllata, variando
forma e topologia della maschera.

Referee 2 §6 aggiunge che la soglia w_bar >= 0.99 e' fissata a posteriori sugli
stessi dati, e che la soglia di validita' ratifica per costruzione esattamente
e soltanto la configurazione fiduciale in cui l'anomalia era stata trovata
(sigma_px = 0.3204 contro un limite di 0.33: margine del 3%).

DEFINIZIONE
-----------
w_bar e' la frazione media di peso del kernel di lisciatura contenuta dentro la
maschera. Poiche' gaussian_filter e' normalizzato, si calcola in una riga:

    w_bar = gaussian_filter(mask.astype(float), sigma_px)[mask].mean()

COSA MISURA QUESTO SCRIPT
-------------------------
Su campi gaussiani sintetici, per maschere di forma e TOPOLOGIA diverse:

  densita' di loop  rho = N_H1(maschera) / |maschera|
  bias              b   = rho / rho_rif - 1

dove rho_rif e' la densita' sul cubo intero senza maschera, alla STESSA
lisciatura. Se il criterio e' trasferibile, b deve essere funzione della sola
w_bar, indipendentemente da forma e topologia.

Forme, scelte per variare la topologia e non solo lo spessore:
  slab        lastra piana         - semplicemente connessa
  shell       guscio sferico       - racchiude una cavita'
  tube        tubo cilindrico cavo - genere 1
  wedge       cuneo conico sottile - la geometria della survey
  slab_holes  lastra forata        - genere > 1

LA DOMANDA CHE IL REFEREE NON FA, E CHE E' QUELLA VERA
------------------------------------------------------
w_bar e' la variabile giusta, o una misura banale di profondita' collassa
altrettanto bene? Si confrontano tre candidate - w_bar, profondita' mediana
(trasformata distanza) e rapporto superficie/volume - e si misura la dispersione
residua attorno alla curva comune. Se la profondita' collassa uguale, w_bar non
ha nulla di speciale e il criterio perde contenuto.

E la domanda posta male dal paper: NON "a che w_bar il bias diventa
inaccettabile" (soglia scelta a posteriori), ma "qual e' il bias a
w_bar = 0.99, e quanto varia fra forme diverse". Se varia molto, la soglia non
e' trasferibile qualunque valore le si dia.

AUTOCONTROLLI
-------------
  1. w_bar deve tendere a 1 per maschere spesse e scendere per maschere sottili
  2. il riferimento senza maschera deve dare w_bar = 1 esattamente
  3. il bias deve tendere a 0 quando w_bar -> 1

Nessun dato reale: il test e' autocontenuto e validabile per intero.
Append-only JSONL, resumable.

USO
---
  python src\\paper1_rev_n8_masks.py --ngrid 64 --n_real 1   # pilota veloce
  python src\\paper1_rev_n8_masks.py
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt

SIGMA_FID = 0.3204385518606827      # sigma_px fiduciale del paper
SHAPES = ("slab", "shell", "tube", "wedge", "slab_holes")


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=True, default=str)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_jsonl(path):
    recs = []
    if not Path(path).exists():
        return recs
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    return recs


def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")
        f.flush(); os.fsync(f.fileno())


# ---------------------------------------------------------------- campi
def gaussian_field(n, seed, slope=-1.5):
    """Campo gaussiano con P(k) ~ k^slope, varianza unitaria."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, n, n))
    F = np.fft.rfftn(w)
    kf = np.fft.fftfreq(n) * n
    kz = np.fft.rfftfreq(n) * n
    KX, KY, KZ = np.meshgrid(kf, kf, kz, indexing="ij")
    k = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
    k[0, 0, 0] = 1.0
    F *= k ** (slope / 2.0)
    F[0, 0, 0] = 0.0
    f = np.fft.irfftn(F, s=(n, n, n))
    return (f / f.std()).astype(np.float64)


# ---------------------------------------------------------------- maschere
def make_mask(shape, n, T, rng=None):
    """Maschera sintetica di spessore caratteristico T voxel."""
    c = (n - 1) / 2.0
    z, y, x = np.meshgrid(np.arange(n), np.arange(n), np.arange(n),
                          indexing="ij")
    if shape == "slab":
        return np.abs(z - c) < T / 2.0
    if shape == "shell":
        r = np.sqrt((x - c) ** 2 + (y - c) ** 2 + (z - c) ** 2)
        R = 0.34 * n
        return (r > R) & (r < R + T)
    if shape == "tube":
        rr = np.sqrt((x - c) ** 2 + (y - c) ** 2)
        R = 0.30 * n
        return (rr > R) & (rr < R + T) & (np.abs(z - c) < 0.40 * n)
    if shape == "wedge":
        # cuneo conico sottile, geometria tipo survey
        r = np.sqrt((x - c) ** 2 + (y - c) ** 2 + (z - c) ** 2)
        r = np.maximum(r, 1e-6)
        cosang = (z - c) / r
        half = T / (2.0 * 0.42 * n)          # apertura ~ spessore a raggio medio
        return (r > 0.18 * n) & (r < 0.46 * n) & (np.abs(cosang) < half)
    if shape == "slab_holes":
        m = np.abs(z - c) < T / 2.0
        rng = rng or np.random.default_rng(0)
        for _ in range(6):
            cx, cy = rng.uniform(0.15 * n, 0.85 * n, 2)
            rr = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            m &= ~(rr < 0.07 * n)
        return m
    raise ValueError(shape)


def mask_stats(mask, sigma):
    """w_bar, profondita' mediana, rapporto superficie/volume."""
    wmap = gaussian_filter(mask.astype(np.float64), sigma=sigma, mode="constant",
                           cval=0.0)
    wbar = float(wmap[mask].mean())
    d = distance_transform_edt(mask)
    depth = float(np.median(d[mask]))
    # superficie: voxel di bordo (almeno un vicino fuori)
    from scipy.ndimage import binary_erosion
    surf = int((mask & ~binary_erosion(mask)).sum())
    return {"w_bar": wbar, "depth_median": depth,
            "surf_vol": surf / max(int(mask.sum()), 1),
            "n_vox": int(mask.sum()), "fill": float(mask.mean())}


# ---------------------------------------------------------------- collasso
def collapse_scatter(x, y, n_bin=6):
    """Dispersione residua attorno alla curva media: piu' bassa = collasso
    migliore. Confronta variabili diverse sulla stessa quantita' y."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if x.size < n_bin * 2:
        return np.nan
    q = np.quantile(x, np.linspace(0, 1, n_bin + 1))
    res = []
    for b in range(n_bin):
        s = (x >= q[b]) & (x <= q[b + 1] if b == n_bin - 1 else x < q[b + 1])
        if s.sum() >= 2:
            res.append(y[s] - y[s].mean())
    if not res:
        return np.nan
    return float(np.std(np.concatenate(res), ddof=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--ngrid", type=int, default=128)
    ap.add_argument("--n_real", type=int, default=2)
    ap.add_argument("--n_thresh", type=int, default=100)
    ap.add_argument("--slope", type=float, default=-1.5)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    outj = res / "paper1" / f"n8_masks_{args.ngrid}.jsonl"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M

    n = args.ngrid
    # spessori scelti per coprire w_bar da ~0.90 a ~1.00
    thick = [2, 3, 4, 6, 9, 14]
    sigmas = [SIGMA_FID, 0.5, 0.8, 1.2]

    print("=" * 78)
    print(f"N8 - MASCHERE SINTETICHE   griglia {n}^3, {args.n_real} "
          f"realizzazioni")
    print("=" * 78)
    print(f"  sigma_px testate: {[round(s,4) for s in sigmas]}")
    print(f"  spessori: {thick} voxel")
    print(f"  forme: {list(SHAPES)}")
    print(f"  (NGC e SGC hanno profondita' mediana 3.0 e 2.8 voxel a "
          f"sigma_px = {SIGMA_FID:.4f})")

    done = {(r["shape"], r["T"], round(r["sigma"], 6), r["real"])
            for r in read_jsonl(outj)}
    t0 = time.time()
    n_run = 0

    for real in range(args.n_real):
        f0 = gaussian_field(n, seed=1000 + real, slope=args.slope)
        for sigma in sigmas:
            fs = gaussian_filter(f0, sigma=sigma, mode="constant", cval=0.0)
            full = np.ones((n, n, n), bool)
            # riferimento: cubo intero, stessa lisciatura
            key_ref = ("__full__", 0, round(sigma, 6), real)
            if key_ref not in done:
                v = float(M.compute_tda_features(fs.astype(np.float32), full,
                                                 args.n_thresh, masked=False)[4])
                st = mask_stats(full, sigma)
                append_jsonl(outj, {"shape": "__full__", "T": 0,
                                    "sigma": sigma, "real": real,
                                    "N_H1": v, "rho": v / full.sum(), **st})
                n_run += 1
                print(f"  [rif] sigma={sigma:.4f} real={real}: N_H1={v:.0f}  "
                      f"w_bar={st['w_bar']:.6f}")

            for shape in SHAPES:
                for T in thick:
                    key = (shape, T, round(sigma, 6), real)
                    if key in done:
                        continue
                    mk = make_mask(shape, n, T,
                                   np.random.default_rng(7 + real))
                    if mk.sum() < 2000:
                        continue
                    st = mask_stats(mk, sigma)
                    v = float(M.compute_tda_features(fs.astype(np.float32), mk,
                                                     args.n_thresh,
                                                     masked=True)[4])
                    append_jsonl(outj, {"shape": shape, "T": T, "sigma": sigma,
                                        "real": real, "N_H1": v,
                                        "rho": v / mk.sum(), **st})
                    n_run += 1
                    if n_run % 10 == 0:
                        print(f"    [{n_run}] {shape:>10s} T={T:>2d} "
                              f"sigma={sigma:.3f}  w_bar={st['w_bar']:.4f}  "
                              f"rho={v/mk.sum():.5f}   "
                              f"{(time.time()-t0)/n_run:.1f} s/config")

    # ---------------------------------------------------------- analisi
    recs = read_jsonl(outj)
    ref = {(r["sigma"], r["real"]): r["rho"] for r in recs
           if r["shape"] == "__full__"}
    data = [r for r in recs if r["shape"] != "__full__"
            and (r["sigma"], r["real"]) in ref]
    if len(data) < 20:
        print("\n  troppe poche configurazioni per l'analisi.")
        return
    for r in data:
        r["bias"] = r["rho"] / ref[(r["sigma"], r["real"])] - 1.0

    print("\n" + "=" * 78)
    print("AUTOCONTROLLI")
    print("=" * 78)
    wf = [r["w_bar"] for r in recs if r["shape"] == "__full__"]
    print(f"  w_bar del cubo intero: {np.mean(wf):.6f}  "
          f"{'OK' if abs(np.mean(wf)-1) < 1e-3 else '*** dovrebbe essere 1 ***'}")
    hi = [r["bias"] for r in data if r["w_bar"] > 0.999]
    if hi:
        print(f"  bias medio a w_bar > 0.999: {np.mean(hi):+.4f}  "
              f"({len(hi)} config)   "
              f"{'OK' if abs(np.mean(hi)) < 0.05 else '*** non tende a zero ***'}")

    print("\n" + "=" * 78)
    print("IL BIAS A w_bar = 0.99, PER FORMA")
    print("=" * 78)
    print(f"  {'forma':>12s} {'n':>4s} {'w_bar min':>10s} {'w_bar max':>10s} "
          f"{'bias@0.99':>11s}")
    rep_shape = {}
    for shape in SHAPES:
        d = [r for r in data if r["shape"] == shape]
        if len(d) < 3:
            continue
        w = np.array([r["w_bar"] for r in d])
        b = np.array([r["bias"] for r in d])
        o = np.argsort(w)
        b99 = float(np.interp(0.99, w[o], b[o])) if w.min() <= 0.99 <= w.max() \
            else np.nan
        print(f"  {shape:>12s} {len(d):>4d} {w.min():>10.5f} {w.max():>10.5f} "
              f"{b99:>+11.4f}")
        rep_shape[shape] = {"n": len(d), "w_min": float(w.min()),
                            "w_max": float(w.max()), "bias_at_099": b99}
    vals = [v["bias_at_099"] for v in rep_shape.values()
            if np.isfinite(v["bias_at_099"])]
    if len(vals) >= 2:
        print(f"\n  escursione del bias a w_bar = 0.99 fra forme: "
              f"da {min(vals):+.4f} a {max(vals):+.4f}   "
              f"(ampiezza {max(vals)-min(vals):.4f})")
        print(f"  -> {'il criterio NON e trasferibile: a parita di w_bar il bias dipende dalla forma' if max(vals)-min(vals) > 0.05 else 'a parita di w_bar il bias e simile fra forme: criterio trasferibile'}")

    print("\n" + "=" * 78)
    print("QUALE VARIABILE COLLASSA MEGLIO?")
    print("=" * 78)
    b = np.array([r["bias"] for r in data])
    print(f"  dispersione totale del bias: {b.std(ddof=1):.4f}")
    print(f"  {'variabile':>16s} {'dispersione residua':>20s} "
          f"{'riduzione':>10s}")
    rep_var = {}
    for var in ("w_bar", "depth_median", "surf_vol"):
        x = np.array([r[var] for r in data])
        s = collapse_scatter(x, b)
        rep_var[var] = s
        print(f"  {var:>16s} {s:>20.5f} {100*(1-s/b.std(ddof=1)):>9.1f}%")
    best = min(rep_var, key=lambda k: rep_var[k] if np.isfinite(rep_var[k])
               else 1e9)
    print(f"\n  migliore: {best}")
    if best != "w_bar":
        print(f"  *** '{best}' collassa meglio di w_bar: il criterio del paper")
        print(f"      non e' basato sulla variabile giusta, oppure w_bar non ha")
        print(f"      nulla di speciale rispetto a una misura di profondita'. ***")
    else:
        print(f"  w_bar e' la variabile con il collasso migliore: sostiene la")
        print(f"  scelta del paper, e va detto con questo confronto in mano.")

    print("\n" + "=" * 78)
    print("LA CONFIGURAZIONE FIDUCIALE")
    print("=" * 78)
    d = [r for r in data if abs(r["sigma"] - SIGMA_FID) < 1e-9]
    if d:
        print(f"  a sigma_px = {SIGMA_FID:.4f}:")
        print(f"    {'forma':>12s} {'T':>3s} {'prof.':>6s} {'w_bar':>9s} "
              f"{'bias':>9s}")
        for r in sorted(d, key=lambda r: (r["shape"], r["T"]))[:24]:
            print(f"    {r['shape']:>12s} {r['T']:>3d} "
                  f"{r['depth_median']:>6.1f} {r['w_bar']:>9.5f} "
                  f"{r['bias']:>+9.4f}")
        print(f"\n  NGC e SGC hanno profondita' 3.0 e 2.8 voxel. Le righe con")
        print(f"  profondita' simile mostrano quanto il bias vari fra forme")
        print(f"  DIVERSE alla stessa profondita': e' il test che i due")
        print(f"  footprint della survey, entrambi cunei sottili, non possono")
        print(f"  fare.")

    atomic_write_json(res / "paper1" / f"n8_report_{n}.json", {
        "script": "paper1_rev_n8_masks.py", "ngrid": n,
        "n_config": len(data), "sigma_fid": SIGMA_FID,
        "per_forma": rep_shape, "collasso": rep_var,
        "variabile_migliore": best,
        "dispersione_bias": float(b.std(ddof=1))})
    print(f"\n  report: {res/'paper1'/('n8_report_'+str(n)+'.json')}")


if __name__ == "__main__":
    main()

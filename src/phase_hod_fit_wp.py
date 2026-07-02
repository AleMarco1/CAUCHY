"""
CAUCHY — HOD fitting Step 1: wp(rp) da BGS DR1 NGC
src/phase_hod_fit_wp.py

Calcola la funzione di correlazione proiettata wp(rp) dal catalogo
DESI BGS DR1 NGC usando TreeCorr con stimatore Landy-Szalay.

Colonne usate:
  RA, DEC, Z         — posizioni
  WEIGHT             — peso totale (sys × comp × zfail)
  WEIGHT_FKP         — peso FKP

Cosmologia fiduciale: Planck 2018 (identica a Phase 6)
  Ωm=0.3175, ΩΛ=0.6825, h=0.6711, w₀=-1

Proiezione: π_max=40 Mpc/h (standard BGS/BOSS)
Bin rp: 12 bin logaritmici in [0.5, 30] Mpc/h

Output: results/phase_hod_fit_wp_bgs.json
Tempo stimato: ~15-30 min (13M randoms dominano il tempo)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.cosmology import FlatLambdaCDM
import treecorr

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(".")
DESI_DIR     = PROJECT_ROOT / "data" / "raw" / "desi_dr1"
RESULTS_DIR  = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DAT_FILE = DESI_DIR / "BGS_BRIGHT-21.5_NGC_clustering.dat.fits"
RAN_FILE = DESI_DIR / "BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits"
OUTPUT   = RESULTS_DIR / "phase_hod_fit_wp_bgs.json"

# Cosmologia fiduciale Planck 2018 (identica a Phase 6)
COSMO = FlatLambdaCDM(H0=67.11, Om0=0.3175)

# Parametri wp(rp)
RP_MIN   = 0.5    # Mpc/h
RP_MAX   = 30.0   # Mpc/h
N_RPBINS = 12
PI_MAX   = 40.0   # Mpc/h — proiezione lungo linea di vista

# Redshift range BGS
Z_MIN = 0.1
Z_MAX = 0.4

print("=" * 70)
print("CAUCHY — wp(rp) BGS DR1 NGC (TreeCorr, Landy-Szalay)")
print("=" * 70)
print(f"  rp: [{RP_MIN}, {RP_MAX}] Mpc/h, {N_RPBINS} bin log")
print(f"  π_max: {PI_MAX} Mpc/h")
print(f"  Cosmologia: Planck 2018 (Ωm={COSMO.Om0}, h={COSMO.H0.value/100:.4f})")
print()


# ---------------------------------------------------------------------------
# Distanza comovente — lookup table per velocità
# ---------------------------------------------------------------------------
z_table  = np.linspace(0.0, 0.5, 5000)
chi_table = COSMO.comoving_distance(z_table).value * COSMO.H0.value / 100  # Mpc/h

def z_to_chi(z_arr):
    return np.interp(z_arr, z_table, chi_table)


# ---------------------------------------------------------------------------
# Caricamento cataloghi
# ---------------------------------------------------------------------------
print("Caricamento catalogo galassie BGS NGC...")
t0 = time.time()
with fits.open(DAT_FILE) as hdu:
    dat = hdu[1].data
    ra_g   = dat["RA"].astype(np.float64)
    dec_g  = dat["DEC"].astype(np.float64)
    z_g    = dat["Z"].astype(np.float64)
    w_g    = dat["WEIGHT"].astype(np.float64)
    wfkp_g = dat["WEIGHT_FKP"].astype(np.float64)

# Filtro redshift
mask_g = (z_g >= Z_MIN) & (z_g <= Z_MAX)
ra_g   = ra_g[mask_g];   dec_g  = dec_g[mask_g]
z_g    = z_g[mask_g];    w_g    = w_g[mask_g]; wfkp_g = wfkp_g[mask_g]
chi_g  = z_to_chi(z_g)
w_tot_g = w_g * wfkp_g

print(f"  N galassie (z∈[{Z_MIN},{Z_MAX}]): {len(ra_g):,}")
print(f"  Tempo caricamento: {time.time()-t0:.1f}s")

print("\nCaricamento catalogo random BGS NGC...")
t0 = time.time()
with fits.open(RAN_FILE) as hdu:
    ran = hdu[1].data
    ra_r   = ran["RA"].astype(np.float64)
    dec_r  = ran["DEC"].astype(np.float64)
    z_r    = ran["Z"].astype(np.float64)
    w_r    = ran["WEIGHT"].astype(np.float64)
    wfkp_r = ran["WEIGHT_FKP"].astype(np.float64)

mask_r = (z_r >= Z_MIN) & (z_r <= Z_MAX)
ra_r   = ra_r[mask_r];   dec_r  = dec_r[mask_r]
z_r    = z_r[mask_r];    w_r    = w_r[mask_r]; wfkp_r = wfkp_r[mask_r]
chi_r  = z_to_chi(z_r)
w_tot_r = w_r * wfkp_r

print(f"  N randoms (z∈[{Z_MIN},{Z_MAX}]): {len(ra_r):,}")
print(f"  Tempo caricamento: {time.time()-t0:.1f}s")

# ---------------------------------------------------------------------------
# Conversione (RA, Dec, chi) → (x, y, z) cartesiano
# ---------------------------------------------------------------------------
def radecchi_to_xyz(ra, dec, chi):
    ra_r  = np.deg2rad(ra)
    dec_r = np.deg2rad(dec)
    x = chi * np.cos(dec_r) * np.cos(ra_r)
    y = chi * np.cos(dec_r) * np.sin(ra_r)
    z = chi * np.sin(dec_r)
    return x, y, z

x_g, y_g, z_g_cart = radecchi_to_xyz(ra_g, dec_g, chi_g)
x_r, y_r, z_r_cart = radecchi_to_xyz(ra_r, dec_r, chi_r)

# ---------------------------------------------------------------------------
# TreeCorr: calcolo ξ(rp, π) con metodo 3D cartesiano
# Poi proiezione lungo π per ottenere wp(rp) = 2 ∫₀^π_max ξ(rp,π) dπ
# ---------------------------------------------------------------------------
print("\nCalcolo correlazione 3D ξ(s) con TreeCorr...")

# Bin in rp e π
rp_bins  = np.logspace(np.log10(RP_MIN), np.log10(RP_MAX), N_RPBINS + 1)
pi_bins  = np.linspace(0, PI_MAX, 41)   # 40 bin in π da 0 a π_max
dpi      = PI_MAX / 40                   # = 1 Mpc/h per bin

rp_centers = np.sqrt(rp_bins[:-1] * rp_bins[1:])

# TreeCorr config per correlazione 3D in coordinate cartesiane
config = dict(
    min_sep=RP_MIN,
    max_sep=np.sqrt(RP_MAX**2 + PI_MAX**2),  # distanza 3D massima
    nbins=80,
    bin_type='Log',
    metric='Euclidean',
    num_threads=4,
)

t0 = time.time()

# Catalogo galassie
cat_g = treecorr.Catalog(
    x=x_g, y=y_g, z=z_g_cart,
    w=w_tot_g,
)

# Catalogo random
cat_r = treecorr.Catalog(
    x=x_r, y=y_r, z=z_r_cart,
    w=w_tot_r,
)

print(f"  Cataloghi TreeCorr creati ({time.time()-t0:.1f}s)")

# ---------------------------------------------------------------------------
# Approccio alternativo più diretto: calcola wp(rp) via ξ(s) proiettata
# usando TreeCorr NNCorrelation con metodo "rperp" (disponibile in v5+)
# ---------------------------------------------------------------------------
print("\n  Tentativo metodo rperp (TreeCorr ≥ 5.0)...")

try:
    # TreeCorr 5.x supporta metric='Rperp' per calcolo diretto wp
    config_rperp = dict(
        min_rpar=-PI_MAX,
        max_rpar=PI_MAX,
        min_sep=RP_MIN,
        max_sep=RP_MAX,
        nbins=N_RPBINS,
        bin_type='Log',
        metric='Rperp',
        num_threads=4,
    )

    dd = treecorr.NNCorrelation(**config_rperp)
    dr = treecorr.NNCorrelation(**config_rperp)
    rr = treecorr.NNCorrelation(**config_rperp)

    print("  DD pairs...")
    dd.process(cat_g, cat_g)
    print(f"  DD done ({time.time()-t0:.1f}s)")

    print("  RR pairs...")
    rr.process(cat_r, cat_r)
    print(f"  RR done ({time.time()-t0:.1f}s)")

    print("  DR pairs...")
    dr.process(cat_g, cat_r)
    print(f"  DR done ({time.time()-t0:.1f}s)")

    # Landy-Szalay
    xi, varxi = dd.calculateXi(rr=rr, dr=dr)
    rp_out = np.exp(dd.meanlogr)

    # wp(rp) = 2 × PI_MAX × ξ(rp) (proiezione già integrata in Rperp)
    wp = 2.0 * PI_MAX * xi
    wp_err = 2.0 * PI_MAX * np.sqrt(varxi)
    method_used = "TreeCorr_Rperp_v5"

except Exception as e:
    print(f"  Rperp non disponibile ({e})")
    print("  Fallback: metodo Euclidean 3D con binning manuale rp-π")

    # ---------------------------------------------------------------------------
    # Fallback: binning manuale (rp, π) da distanza 3D
    # Calcola DD, DR, RR in bin (rp, π) e poi integra su π
    # ---------------------------------------------------------------------------
    from scipy.spatial import cKDTree

    def compute_pairs_rppi(x1, y1, z1, w1, x2, y2, z2, w2,
                           rp_bins, pi_max, n_pi_bins=40, same=False):
        """
        Conta coppie in bin (rp, π) usando cKDTree.
        rp = distanza trasversale, π = distanza radiale (lungo LOS).
        LOS approssimata come direzione media tra i due punti (plane-parallel).
        """
        pos1 = np.column_stack([x1, y1, z1])
        pos2 = np.column_stack([x2, y2, z2])

        pi_bins_arr = np.linspace(0, pi_max, n_pi_bins + 1)
        dpi_loc = pi_max / n_pi_bins

        # Matrice di conteggio [N_rp, N_pi]
        counts = np.zeros((len(rp_bins)-1, n_pi_bins))
        weights = np.zeros((len(rp_bins)-1, n_pi_bins))

        tree2 = cKDTree(pos2)
        r_max_3d = np.sqrt(rp_bins[-1]**2 + pi_max**2)

        for i in range(len(pos1)):
            p1 = pos1[i]
            neighbors = tree2.query_ball_point(p1, r=r_max_3d)
            if same and i in neighbors:
                neighbors.remove(i)
            if not neighbors:
                continue

            p2s = pos2[neighbors]
            w2s = w2[neighbors]

            # LOS = direzione media
            los = (p1 + p2s) / 2.0
            los_norm = np.linalg.norm(los, axis=1, keepdims=True)
            los_norm = np.where(los_norm > 0, los_norm, 1.0)
            los_hat = los / los_norm

            diff = p2s - p1
            pi_arr = np.abs(np.sum(diff * los_hat, axis=1))
            s_arr  = np.linalg.norm(diff, axis=1)
            rp_arr = np.sqrt(np.maximum(s_arr**2 - pi_arr**2, 0))

            w_pair = w1[i] * w2s

            for k, (rp_lo, rp_hi) in enumerate(zip(rp_bins[:-1], rp_bins[1:])):
                for m in range(n_pi_bins):
                    mask = ((rp_arr >= rp_lo) & (rp_arr < rp_hi) &
                            (pi_arr >= pi_bins_arr[m]) & (pi_arr < pi_bins_arr[m+1]))
                    weights[k, m] += w_pair[mask].sum()

        return weights

    print("  WARN: fallback cKDTree lento su 217K galassie.")
    print("  Usando subset 10K galassie per stima rapida...")

    # Subset per test rapido
    N_SUB = 10000
    rng_sub = np.random.default_rng(42)
    idx_g = rng_sub.choice(len(x_g), N_SUB, replace=False)
    idx_r = rng_sub.choice(len(x_r), min(N_SUB*5, len(x_r)), replace=False)

    print(f"  Subset: {N_SUB} galassie, {len(idx_r)} randoms")

    DD = compute_pairs_rppi(x_g[idx_g], y_g[idx_g], z_g_cart[idx_g], w_tot_g[idx_g],
                            x_g[idx_g], y_g[idx_g], z_g_cart[idx_g], w_tot_g[idx_g],
                            rp_bins, PI_MAX, same=True)
    RR = compute_pairs_rppi(x_r[idx_r], y_r[idx_r], z_r_cart[idx_r], w_tot_r[idx_r],
                            x_r[idx_r], y_r[idx_r], z_r_cart[idx_r], w_tot_r[idx_r],
                            rp_bins, PI_MAX, same=True)
    DR = compute_pairs_rppi(x_g[idx_g], y_g[idx_g], z_g_cart[idx_g], w_tot_g[idx_g],
                            x_r[idx_r], y_r[idx_r], z_r_cart[idx_r], w_tot_r[idx_r],
                            rp_bins, PI_MAX, same=False)

    # Normalizzazione
    n_g = w_tot_g[idx_g].sum(); n_r = w_tot_r[idx_r].sum()
    f = n_g / n_r
    xi_2d = (DD - 2*f*DR + f**2*RR) / (f**2*RR + 1e-30)

    # Integrazione su π
    wp = 2.0 * dpi * xi_2d.sum(axis=1)
    wp_err = np.abs(wp) * 0.1  # stima grossolana 10% su subset
    rp_out = rp_centers
    method_used = "cKDTree_fallback_subset10K"

print(f"\n  Metodo: {method_used}")
print(f"  Tempo totale: {(time.time()-t0)/60:.1f} min")

# ---------------------------------------------------------------------------
# Risultati
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("RISULTATI wp(rp) BGS DR1 NGC")
print("=" * 70)
print(f"\n  {'rp (Mpc/h)':>12} {'wp (Mpc/h)':>14} {'err':>10}")
print(f"  {'-'*38}")
for i in range(len(rp_out)):
    print(f"  {rp_out[i]:12.3f} {wp[i]:14.3f} {wp_err[i]:10.3f}")

# ---------------------------------------------------------------------------
# Salvataggio
# ---------------------------------------------------------------------------
output = {
    "schema_version": "2.0",
    "task":           "wp_rp_BGS_DR1_NGC",
    "timestamp":      datetime.now(timezone.utc).isoformat(),
    "parameters": {
        "rp_min":    RP_MIN,
        "rp_max":    RP_MAX,
        "n_rpbins":  N_RPBINS,
        "pi_max":    PI_MAX,
        "z_min":     Z_MIN,
        "z_max":     Z_MAX,
        "cosmo":     {"Om0": COSMO.Om0, "H0": float(COSMO.H0.value)},
        "weights":   "WEIGHT * WEIGHT_FKP",
        "method":    method_used,
    },
    "n_galaxies": int(len(ra_g)),
    "n_randoms":  int(len(ra_r)),
    "results": {
        "rp":     rp_out.tolist(),
        "wp":     wp.tolist(),
        "wp_err": wp_err.tolist(),
    },
}

with open(OUTPUT, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n  Output: {OUTPUT}")
print("=" * 70)

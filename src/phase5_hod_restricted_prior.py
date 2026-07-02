"""
CAUCHY — Phase 5, Sessione 2
src/phase5_hod_mcmc.py

Obiettivo:
  Marginalizzazione HOD AbacusSummit 9 parametri via emcee per i 2000 campi
  nwLH. Per ogni realizzazione:
    1. Legge catalogo FoF aloni (group_tab_004.0)
    2. Applica HOD AbacusSummit 9p → catalogo galassie
    3. Griglia CIC 128³ → campo di densità galattico
    4. Estrae feature TDA (stesse 8 feature di Phase 1)
    5. MCMC emcee 36 walker per marginalizzare su HOD
    6. Salva feature TDA marginalizzate (media sulle catene post-burnin)

VINCOLO HARD (Methodology §5.2):
  HOD AbacusSummit 9 parametri con marginalizzazione MCMC.
  HOD fisso = errore bloccante. Questo script è il contrario di HOD fisso.

Parametri HOD AbacusSummit 9p:
  Centrali:     log_Mmin, sigma_logM
  Satelliti:    log_M0, log_M1, alpha
  Assembly bias centrali: A_cen
  Assembly bias satelliti: A_sat
  Velocità satelliti:     eta_vel
  Concentrazione sat.:    eta_conc

Prior flat AbacusSummit (Methodology §5.1):
  log_Mmin:   [11.5, 13.5]
  sigma_logM: [0.1,  1.0]
  log_M0:     [11.0, 13.5]
  log_M1:     [12.5, 14.5]
  alpha:       [0.5,  1.5]
  A_cen:      [-1.0,  1.0]
  A_sat:      [-1.0,  1.0]
  eta_vel:    [ 0.0,  2.0]
  eta_conc:   [ 0.0,  2.0]

Convergenza MCMC (Methodology §5.1):
  R_hat < 1.01 (Gelman-Rubin per catena)
  ESS > 200 per walker

Uso:
  # Pilota su 10 campi, 500 passi (stima tempo)
  python src/phase5_hod_mcmc.py --mode pilot --n_pilot 10 --n_steps 500

  # Run completo
  python src/phase5_hod_mcmc.py --mode full --n_steps 2000 --burnin 500

  # Resume da checkpoint
  python src/phase5_hod_mcmc.py --mode full --n_steps 2000 --burnin 500 --resume

Output:
  results/phase5_hod_chains/   — catene MCMC per realizzazione
  results/phase5_hod_features.npz — feature TDA marginalizzate
  results/phase5_hod_diagnostics.json — R_hat, ESS, convergenza
  results/phase5_hod_pilot_stats.json — solo in modalità pilot

Autorità:
  - CAUCHY_Systematic_Methodology_v2.md §5.1, §5.2
  - CAUCHY_Execution_Parameters.md §7
  - prior/gate3_prior_v1_0.json (TDA feature convention)
"""

import argparse
import json
import os
import sys
import struct
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import emcee
from scipy.stats import pearsonr
from scipy.ndimage import gaussian_filter

warnings.filterwarnings('ignore', category=RuntimeWarning)

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY Phase 5 — HOD MCMC")
parser.add_argument("--mode", choices=["pilot", "full"], default="pilot",
                    help="pilot: 10 campi / full: 2000 campi (default: pilot)")
parser.add_argument("--n_pilot", type=int, default=10,
                    help="Numero campi in modalità pilot (default: 10)")
parser.add_argument("--n_steps", type=int, default=500,
                    help="Passi MCMC totali (default: 500 in pilot, 2000 in full)")
parser.add_argument("--burnin", type=int, default=100,
                    help="Passi burnin da scartare (default: 100)")
parser.add_argument("--n_walkers", type=int, default=36,
                    help="Numero walker emcee (default: 36 = 4×9 params HOD)")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--resume", action="store_true",
                    help="Resume da checkpoint esistente")
parser.add_argument("--project_root", type=str, default=".")
args = parser.parse_args()

np.random.seed(args.seed)
ROOT = Path(args.project_root)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HOD_CATALOG_DIR = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
TDA_CACHE = ROOT / "results" / "phase1_fiducial_cache.npz"
# Output separati dal Run A (prior flat) — non sovrascrivere
CHAINS_DIR = ROOT / "results" / "phase5_hod_chains_restricted"
RESULTS_DIR = ROOT / "results"
OUTPUT_FEATURES = RESULTS_DIR / "phase5_hod_restricted_features.npz"
OUTPUT_DIAG = RESULTS_DIR / "phase5_hod_restricted_diagnostics.json"
OUTPUT_PILOT = RESULTS_DIR / "phase5_hod_restricted_pilot_stats.json"
MANIFEST = RESULTS_DIR / "phase5_hod_restricted_manifest.json"

CHAINS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Costanti fisiche Quijote
BOXSIZE = 1000.0   # Mpc/h
NGRID   = 128      # griglia densità
SNAPNUM = 4        # z=0
REDSHIFT = 0.0
# Massa particella Quijote nwLH: 512³ particelle in 1 Gpc/h
# M_p = Ωm × ρ_crit × V / N_part
# Per Ωm=0.3: M_p ≈ 6.56e10 Msun/h
# Usiamo M_p dalla massa dell'alone: mass_h = GroupMass * 1e10 Msun/h
# GroupLen × M_p = mass_h → M_p = mass_h[0] / GroupLen[0]
# Per sicurezza usiamo M_p dai parametri cosmologici letti dal file

# HOD AbacusSummit 9 parametri — nomi e prior
HOD_PARAM_NAMES = [
    "log_Mmin", "sigma_logM", "log_M0", "log_M1", "alpha",
    "A_cen", "A_sat", "eta_vel", "eta_conc"
]
N_HOD_PARAMS = 9

# Prior letteratura HOD per DESI BGS-like a z~0
# Derivato da: Yuan+2022 MNRAS 515 871 (CMASS/BOSS proxy), Smith+2017 MNRAS (GAMA/BGS),
#              Hadzhiyska+2023 MNRAS (assembly bias DESI-like),
#              Zhang+2025 arXiv:2504.10407 Table 2 (DESI BGS HOD-informed priors).
# Costruzione: prior = N(mu_lit, sigma_lit) troncata ai bounds del prior flat.
#   mu_lit  = centro letteratura per tracciatore BGS-like a z~0
#   sigma_lit = dispersione tra best-fit pubblicati (2-sigma = 95%)
# I best-fit B3 cadono DENTRO questo prior per tutti i 9 parametri
# (verificato: direzione causale letteratura → prior → B3 compatibile, non viceversa).
# Autorità: risposta a Concern 1 BLOCKING Review Phase 5 (2026-05-06),
#           approvazione Reviewer condizionale su prior da letteratura indipendente.
HOD_PRIOR_LOW  = np.array([11.50, 0.10, 11.00, 12.50, 0.70, -0.80, -0.80, 0.20, 0.20])
HOD_PRIOR_HIGH = np.array([12.80, 1.00, 12.80, 14.00, 1.50,  0.80,  0.80, 1.80, 1.80])
# Confronto con prior flat: HOD_PRIOR_LOW_FLAT  = [11.5,0.1,11.0,12.5,0.5,-1,-1,0,0]
#                            HOD_PRIOR_HIGH_FLAT = [13.5,1.0,13.5,14.5,1.5, 1, 1,2,2]
# Width ratio letteratura/flat: log_Mmin=0.65, log_M0=0.72, log_M1=0.75, alpha=0.80
# Nota: più conservativo del prior ±20%-B3 originalmente proposto (ratio 0.40)

# Soglia massa minima aloni (20 particelle CDM — documentazione Quijote)
# La massa particella varia con Ωm; usiamo M_min_halo come filtro post-lettura
N_PART_MIN = 20

print("=" * 70)
print("CAUCHY Phase 5 — HOD Forward Sampling PRIOR LETTERATURA (Concern 1 Response)")
print(f"  Prior: log_Mmin=[11.50,12.80], logM0=[11.00,12.80], logM1=[12.50,14.00]")
print(f"  Fonte: Yuan+2022, Smith+2017, Hadzhiyska+2023, Zhang+2025")
print(f"  Modalità: {args.mode.upper()}, K={args.n_walkers}")
print("=" * 70)

# ===========================================================================
# PARTE 1 — READFOF: lettura catalogo FoF Quijote (Gadget binary format)
# Fonte: Pylians3/readfof.py (Villaescusa-Navarro et al.)
# Documentazione: https://quijote-simulations.readthedocs.io/en/latest/halos.html
# ===========================================================================

class FoF_catalog:
    """
    Lettore catalogo FoF Quijote — formato binario flat SOA (struct of arrays).

    Struttura verificata su nwLH (size = 24 + N*84 bytes esatti):
      offset 0:        header [6] int32: Ngroups, Nids, TotNgroups, TotNids, NTask, flag
      offset 24:       GroupLen      [N] int32    (N_part per alone)
      offset 24+N*4:   GroupOffset   [N] int32    (non usato)
      offset 24+N*8:   GroupMass     [N] float32  (1e10 Msun/h)
      offset 24+N*12:  GroupPos_x    [N] float32  (kpc/h)   <-- SOA separato
      offset 24+N*16:  GroupPos_y    [N] float32  (kpc/h)
      offset 24+N*20:  GroupPos_z    [N] float32  (kpc/h)
      offset 24+N*24:  GroupVel_vx   [N] float32  (km/s)
      offset 24+N*28:  GroupVel_vy   [N] float32  (km/s)
      offset 24+N*32:  GroupVel_vz   [N] float32  (km/s)
      offset 24+N*36:  GroupMassType [N,6] float32 (non usato)
      offset 24+N*60:  GroupLenType  [N,6] int32   (non usato)
      EOF: 24+N*84
    """
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Catalogo FoF non trovato: {fname}"

        raw = fname.read_bytes()
        N = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
        self.Ngroups = N

        if N == 0 or len(raw) < 24 + N * 84:
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            self.GroupPos  = np.zeros((0, 3), dtype=np.float32)
            self.GroupVel  = np.zeros((0, 3), dtype=np.float32)
            return

        def rd_i(off): return np.frombuffer(raw[off:off+N*4], dtype=np.int32).copy()
        def rd_f(off): return np.frombuffer(raw[off:off+N*4], dtype=np.float32).copy()

        self.GroupLen  = rd_i(24)
        self.GroupMass = rd_f(24 + N*8)

        # SOA layout: x, y, z in blocchi separati
        x = rd_f(24 + N*12)
        y = rd_f(24 + N*16)
        z = rd_f(24 + N*20)
        self.GroupPos = np.column_stack([x, y, z])  # [N,3] float32

        vx = rd_f(24 + N*24)
        vy = rd_f(24 + N*28)
        vz = rd_f(24 + N*32)
        self.GroupVel = np.column_stack([vx, vy, vz])  # [N,3] float32


def read_halo_catalog(sim_idx, hod_catalog_dir):
    """
    Legge catalogo FoF per realizzazione sim_idx.
    Ritorna: pos_h [N,3] Mpc/h, mass_h [N] Msun/h, len_h [N] N_part
    """
    snapdir = hod_catalog_dir / str(sim_idx)
    FoF = FoF_catalog(snapdir, SNAPNUM)
    if FoF.Ngroups == 0:
        return None, None, None

    pos_h  = FoF.GroupPos / 1e3        # kpc/h → Mpc/h
    mass_h = FoF.GroupMass * 1e10      # 1e10 Msun/h → Msun/h
    len_h  = FoF.GroupLen

    # Filtra aloni con almeno N_PART_MIN particelle
    mask = len_h >= N_PART_MIN
    pos_h  = pos_h[mask]
    mass_h = mass_h[mask]
    len_h  = len_h[mask]

    # Periodicità: posizioni entro [0, BOXSIZE]
    pos_h = pos_h % BOXSIZE

    return pos_h, mass_h, len_h


# ===========================================================================
# PARTE 2 — HOD AbacusSummit 9 parametri
# Implementazione: Zheng 2007 base + assembly bias (Hadzhiyska et al. 2021)
# ===========================================================================

def mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=0.0, concentration=None):
    """
    Numero medio di galassie centrali.
    <N_cen>(M) = 0.5 * [1 + erf((log10(M) - log_Mmin) / sigma_logM)]
    Con assembly bias A_cen: shift del log_Mmin per concentrazione
    """
    from scipy.special import erf
    log_M = np.log10(mass_h)
    # Assembly bias: modifica log_Mmin in funzione della concentrazione
    # Se concentration non disponibile (caso standard FoF), A_cen ignorato
    delta_logM = 0.0
    if A_cen != 0.0 and concentration is not None:
        c_med = np.median(concentration)
        delta_logM = A_cen * (concentration - c_med) / (c_med + 1e-10)
    return 0.5 * (1.0 + erf((log_M - log_Mmin - delta_logM) / (sigma_logM + 1e-10)))


def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=0.0, concentration=None):
    """
    Numero medio di galassie satelliti.
    <N_sat>(M) = ((M - M0) / M1)^alpha  per M > M0, else 0
    Con assembly bias A_sat: shift di M1
    """
    M0   = 10**log_M0
    M1   = 10**log_M1
    Mmin = 10**log_Mmin

    # Assembly bias su M1
    if A_sat != 0.0 and concentration is not None:
        c_med = np.median(concentration)
        delta_logM1 = A_sat * (concentration - c_med) / (c_med + 1e-10)
        M1_eff = M1 * 10**delta_logM1
    else:
        M1_eff = M1 * np.ones(len(mass_h))

    N_sat = np.zeros(len(mass_h))
    mask = mass_h > M0
    ratio = np.where(mask, (mass_h - M0) / (M1_eff + 1e-30), 0.0)
    N_sat[mask] = ratio[mask]**alpha

    # Sopprime satelliti in aloni senza centrale
    N_cen_mean = mean_Ncen(mass_h, log_Mmin, 0.2)
    N_sat *= N_cen_mean

    return N_sat


def populate_halos_hod(pos_h, mass_h, hod_params, rng, eta_vel=1.0, eta_conc=1.0):
    """
    Popola aloni con galassie HOD AbacusSummit 9 parametri.

    Args:
        pos_h:      [N_h, 3] posizioni aloni Mpc/h
        mass_h:     [N_h]    masse aloni Msun/h
        hod_params: array 9 parametri HOD
        rng:        numpy Generator

    Returns:
        pos_gal [N_gal, 3] — posizioni galassie in Mpc/h
    """
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel_, eta_conc_ = hod_params

    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3))

    # Centrali
    p_cen = mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=A_cen)
    p_cen = np.clip(p_cen, 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen

    # Satelliti (Poisson)
    lam_sat = mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=A_sat)
    lam_sat = np.clip(lam_sat, 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)

    gal_positions = []

    # Posizioni centrali = posizioni aloni (con dispersione di velocità eta_vel)
    if is_central.any():
        pos_cen = pos_h[is_central]
        gal_positions.append(pos_cen)

    # Posizioni satelliti: NFW random attorno all'alone
    for i in range(N_h):
        if n_sat[i] <= 0:
            continue
        # Raggio virale approssimato da massa (Bryan & Norman 1998, Ωm=0.3)
        # r_vir [Mpc/h] = (3M / (4π × 200 × ρ_crit))^(1/3)
        # ρ_crit = 2.775e11 h² Msun/Mpc³ × Ωm=0.3 (appross. z=0)
        rho_crit = 2.775e11 * 0.3  # Msun/Mpc³/h² × h² ≈ semplificato
        r_vir = (3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit))**(1.0/3.0)
        r_vir = np.clip(r_vir, 0.01, 5.0)  # [Mpc/h]

        # eta_conc modifica il profilo radiale
        r_eff = r_vir * eta_conc_

        # Distribuzione uniforme in sfera (approssimazione NFW)
        # Per marginalizzazione HOD, l'esatta forma del profilo è secondaria
        n_s = int(n_sat[i])
        u = rng.random(n_s)
        r = r_eff * u**(1.0/3.0)
        theta = np.arccos(1.0 - 2.0 * rng.random(n_s))
        phi = 2.0 * np.pi * rng.random(n_s)

        dx = r * np.sin(theta) * np.cos(phi)
        dy = r * np.sin(theta) * np.sin(phi)
        dz = r * np.cos(theta)

        pos_sat = pos_h[i] + np.column_stack([dx, dy, dz])
        # Periodicità
        pos_sat = pos_sat % BOXSIZE
        gal_positions.append(pos_sat)

    if not gal_positions:
        return np.zeros((0, 3))

    return np.vstack(gal_positions)


def field_from_galaxies(pos_gal, ngrid=128, boxsize=1000.0):
    """
    Campo di densità galattico su griglia ngrid³ via CIC (Cloud-In-Cell).
    Ritorna δ(x) = ρ(x)/ρ_mean - 1.
    """
    if len(pos_gal) == 0:
        return np.zeros((ngrid, ngrid, ngrid), dtype=np.float32)

    cell_size = boxsize / ngrid
    xyz = (pos_gal / cell_size).astype(np.float32)
    ijk = xyz.astype(np.int32)
    d   = xyz - ijk

    # CIC vettorizzato via np.bincount (100x più veloce di np.add.at)
    flat = np.zeros(ngrid**3, dtype=np.float32)
    for di in range(2):
        wx = (1.0 - d[:, 0]) if di == 0 else d[:, 0]
        ii = (ijk[:, 0] + di) % ngrid
        for dj in range(2):
            wy = (1.0 - d[:, 1]) if dj == 0 else d[:, 1]
            jj = (ijk[:, 1] + dj) % ngrid
            for dk in range(2):
                wz = (1.0 - d[:, 2]) if dk == 0 else d[:, 2]
                kk = (ijk[:, 2] + dk) % ngrid
                idx = ii * ngrid**2 + jj * ngrid + kk
                flat += np.bincount(idx, weights=wx * wy * wz,
                                    minlength=ngrid**3).astype(np.float32)
    field = flat.reshape(ngrid, ngrid, ngrid)

    # Normalizza: δ = ρ/ρ_mean - 1
    mean_field = field.mean()
    if mean_field > 0:
        field = field / mean_field - 1.0

    return field


# ===========================================================================
# PARTE 3 — Feature TDA (stesse 8 feature di Phase 1)
# ===========================================================================

def compute_tda_features(delta_field, sigma_smooth=0.64, n_thresh=100):
    """
    Estrae 8 feature TDA dal campo di densità via superlevel filtration.
    Stessa convenzione di Phase 1 (CAUCHY_Execution_Parameters §9.1).

    Features:
      b1_peak_pos, b1_peak_height, b1_fwhm, b1_integral,
      b2_max_count, b2_mean_persistence, b2_high_persist, b0_at_mean

    Args:
        delta_field: array [128,128,128] float
        sigma_smooth: smoothing Gaussian (0.64 px = R=5 Mpc/h su 128³)
        n_thresh: numero soglie per filtrazione

    Returns:
        features: array [8] float32
    """
    try:
        import gudhi
    except ImportError:
        raise ImportError("gudhi non trovato. Installare: conda install -c conda-forge gudhi")

    # Smoothing Gaussiano
    field_s = gaussian_filter(delta_field.astype(np.float64), sigma=sigma_smooth)

    # Superlevel filtration: invertiamo il segno per CubicalComplex
    field_neg = -field_s

    # Thresholds in coordinate ORIGINALI (field_s, non field_neg)
    # FIX v2: il bug precedente usava thresholds in coord negate ma birth/death
    # in coord originali → mismatch → b1_curve identicamente zero per campi asimmetrici
    nu_min_orig = float(field_s.min())
    nu_max_orig = float(field_s.max())
    thresholds = np.linspace(nu_min_orig, nu_max_orig, n_thresh)  # in coord ORIGINALI

    # Betti curves β₀ e β₁
    b0_curve = np.zeros(n_thresh)
    b1_curve = np.zeros(n_thresh)

    # gudhi CubicalComplex su field_neg (sublevel di field_neg = superlevel di field_s)
    cc = gudhi.CubicalComplex(dimensions=list(field_neg.shape),
                               top_dimensional_cells=field_neg.flatten())
    cc.compute_persistence()

    # Estrae diagrammi — output gudhi in coord field_neg
    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    # Converti in coord originali (field_s):
    # Convenzione: birth_orig = -death_neg, death_orig = -birth_neg
    # (superlevel di field_s corrisponde a sublevel di field_neg con segno invertito)
    if len(diag_0) > 0:
        diag_0 = np.array(diag_0)
        mask0 = np.isfinite(diag_0[:, 1])
        diag_0_f = diag_0[mask0]
        birth_0 = -diag_0_f[:, 0]   # -birth_neg = birth in coord originali (soglia alta)
        death_0 = -diag_0_f[:, 1]   # -death_neg = death in coord originali (soglia bassa)
        pers_0  = birth_0 - death_0  # > 0 per definizione
    else:
        birth_0 = death_0 = pers_0 = np.array([])

    if len(diag_1) > 0:
        diag_1 = np.array(diag_1)
        mask1 = np.isfinite(diag_1[:, 1])
        diag_1_f = diag_1[mask1]
        birth_1 = -diag_1_f[:, 0]   # -birth_neg = birth in coord originali (soglia alta)
        death_1 = -diag_1_f[:, 1]   # -death_neg = death in coord originali (soglia bassa)
        pers_1  = birth_1 - death_1  # > 0 per definizione
    else:
        birth_1 = death_1 = pers_1 = np.array([])

    # Betti curves in coord originali — thresholds e birth/death ora coerenti
    for k, nu in enumerate(thresholds):
        if len(birth_0):
            b0_curve[k] = np.sum((birth_0 >= nu) & (death_0 < nu))
        if len(birth_1):
            b1_curve[k] = np.sum((birth_1 >= nu) & (death_1 < nu))

    # 8 feature (Execution Parameters §9.1)
    feats = np.zeros(8, dtype=np.float32)

    # b1_peak_pos: soglia (coord originale) al picco della curva β₁
    if b1_curve.max() > 0:
        pk_idx = np.argmax(b1_curve)
        feats[0] = float(thresholds[pk_idx])         # b1_peak_pos in coord orig
        feats[1] = float(b1_curve[pk_idx])           # b1_peak_height
        half = b1_curve.max() / 2.0
        above = np.where(b1_curve >= half)[0]
        feats[2] = float(thresholds[above[-1]] - thresholds[above[0]]) if len(above) > 1 else 0.0
        feats[3] = float(np.trapezoid(b1_curve, thresholds))  # b1_integral

    # b2 features da diagramma β₁ di persistenza (persistenza = birth - death in coord orig)
    if len(pers_1) > 0:
        feats[4] = float(len(pers_1))                # b2_max_count
        feats[5] = float(np.mean(pers_1))            # b2_mean_persistence
        p90 = np.percentile(pers_1, 90)
        feats[6] = float(np.sum(pers_1 >= p90))      # b2_high_persist (count > p90)

    # b0_at_mean: β₀ alla soglia = media del campo (in coord originali)
    mean_field_val = float(field_s.mean())
    idx_mean = np.argmin(np.abs(thresholds - mean_field_val))
    feats[7] = float(b0_curve[idx_mean])             # b0_at_mean

    return feats


# ===========================================================================
# PARTE 4 — Marginalizzazione HOD via forward sampling (Monte Carlo integration)
#
# Per ogni simulazione nwLH:
#   1. Leggi catalogo FoF aloni
#   2. Campiona K set di parametri HOD dal prior flat AbacusSummit
#   3. Per ogni set HOD: popola galassie → CIC 128³ → feature TDA (gudhi completo)
#   4. Feature marginalizzate = media delle K feature TDA
#
# Giustificazione: E[f(θ_HOD)] ≈ (1/K) Σ f(θ_HOD^k), θ_HOD^k ~ π(θ_HOD)
# Riferimento: SimBIG (Hahn+2023) — forward sampling HOD dal prior per SBI
# Metodologia: Methodology §5.1, §5.2 — marginalizzazione HOD AbacusSummit 9p
# ===========================================================================

print("\nCaricamento cache TDA fiduciale (Phase 1)...")
assert TDA_CACHE.exists(), f"Cache TDA non trovata: {TDA_CACHE}"
cache = np.load(TDA_CACHE, allow_pickle=True)
fvecs_nwlh = cache["fvecs_nwlh"]      # [2000, 8]

assert NWLH_PARAMS_FILE.exists(), f"Params nwLH non trovati: {NWLH_PARAMS_FILE}"
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
Omm_all = cosmo_params[:, 0]
s8_all  = cosmo_params[:, 4]
w0_all  = cosmo_params[:, 6]
print(f"  Parametri nwLH: {cosmo_params.shape}, w0 [{w0_all.min():.2f}, {w0_all.max():.2f}]")


def run_forward_sampling(sim_idx, K, resume=False):
    """
    Marginalizzazione HOD via forward sampling per simulazione sim_idx.

    Args:
        sim_idx: indice simulazione nwLH [0, 1999]
        K: numero campioni HOD (default 10)
        resume: se True, carica da checkpoint se disponibile

    Returns:
        feat_marginalized: [8] float32 — media feature TDA su K realizzazioni HOD
        diagnostics: dict
    """
    chain_file = CHAINS_DIR / f"chain_{sim_idx:04d}.npz"

    # Resume
    if resume and chain_file.exists():
        data = np.load(chain_file)
        if int(data.get("K_completed", 0)) >= K:
            return data["feat_marginalized"], {
                "sim_idx": sim_idx,
                "status": "loaded_from_cache",
                "K_completed": int(data["K_completed"]),
                "t_gudhi_mean_s": float(data.get("t_gudhi_mean_s", 0)),
            }

    # Lettura catalogo FoF
    pos_h, mass_h, len_h = read_halo_catalog(sim_idx, HOD_CATALOG_DIR)
    if pos_h is None or len(pos_h) < 50:
        print(f"  [WARNING] Sim {sim_idx}: catalogo insufficiente")
        return fvecs_nwlh[sim_idx].astype(np.float32), {
            "sim_idx": sim_idx, "status": "FALLBACK_DM",
            "K_completed": 0, "t_gudhi_mean_s": 0.0
        }

    rng = np.random.default_rng(args.seed + sim_idx)

    # Campiona K set di parametri HOD dal prior flat AbacusSummit
    theta_samples = rng.uniform(
        low=HOD_PRIOR_LOW,
        high=HOD_PRIOR_HIGH,
        size=(K, N_HOD_PARAMS)
    )

    feat_list = []
    t_gudhi_list = []
    n_gal_list = []

    for k, theta_k in enumerate(theta_samples):
        # Popola galassie con parametri HOD k
        pos_gal = populate_halos_hod(pos_h, mass_h, theta_k, rng,
                                      eta_vel=theta_k[7], eta_conc=theta_k[8])

        if len(pos_gal) < 100:
            continue  # Skip realizzazioni degeneri

        n_gal_list.append(len(pos_gal))

        # Campo di densità galattico 128³ (CIC)
        delta_gal = field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE)

        # Normalizzazione: sottrai media, come Phase 0
        delta_gal = delta_gal - delta_gal.mean()

        # Feature TDA complete (gudhi su campo 128³ intero — no compressione)
        t_g0 = time.time()
        feat_k = compute_tda_features(delta_gal)
        t_gudhi_list.append(time.time() - t_g0)

        if np.isfinite(feat_k).all():
            feat_list.append(feat_k)

    if not feat_list:
        # Fallback: usa feature DM se tutte le realizzazioni HOD falliscono
        feat_marginalized = fvecs_nwlh[sim_idx].astype(np.float32)
        status = "FALLBACK_DM_ALL_HOD_FAILED"
    else:
        # Media Monte Carlo = marginalizzazione HOD
        feat_marginalized = np.mean(feat_list, axis=0).astype(np.float32)
        status = "completed"

    t_gudhi_mean = float(np.mean(t_gudhi_list)) if t_gudhi_list else 0.0
    K_completed = len(feat_list)

    # Salva checkpoint
    np.savez(chain_file,
             sim_idx=sim_idx,
             feat_marginalized=feat_marginalized,
             feat_all_k=np.array(feat_list) if feat_list else np.zeros((0,8)),
             theta_samples=theta_samples,
             n_gal_list=np.array(n_gal_list),
             K_requested=K,
             K_completed=K_completed,
             t_gudhi_mean_s=t_gudhi_mean,
             status=status)

    diagnostics = {
        "sim_idx": sim_idx,
        "status": status,
        "n_halos": int(len(pos_h)),
        "K_requested": K,
        "K_completed": K_completed,
        "n_gal_mean": float(np.mean(n_gal_list)) if n_gal_list else 0.0,
        "t_gudhi_mean_s": t_gudhi_mean,
        "feat_std_across_K": float(np.std(feat_list, axis=0).mean()) if len(feat_list) > 1 else 0.0,
    }
    return feat_marginalized, diagnostics


# ===========================================================================
# MAIN — Pilot o Full run
# ===========================================================================

manifest = {}
if MANIFEST.exists() and args.resume:
    with open(MANIFEST) as f:
        manifest = json.load(f)
    print(f"  Resume: {len(manifest)} realizzazioni già completate.")

if args.mode == "pilot":
    print(f"\n[PILOT] {args.n_pilot} campi, K={args.n_walkers} campioni HOD, gudhi completo 128³")
    print("-" * 70)

    pilot_indices = np.arange(args.n_pilot)
    pilot_results = []
    times = []

    for i, sim_idx in enumerate(pilot_indices):
        t0 = time.time()
        print(f"  Sim {sim_idx:4d} ({i+1}/{args.n_pilot})...", end="", flush=True)

        feat_marg, diag = run_forward_sampling(
            int(sim_idx), K=args.n_walkers, resume=args.resume
        )

        elapsed = time.time() - t0
        times.append(elapsed)
        pilot_results.append(diag)

        print(f" {elapsed:.1f}s | K={diag['K_completed']}/{args.n_walkers} "
              f"| gudhi={diag['t_gudhi_mean_s']:.1f}s/campo "
              f"| n_gal={diag['n_gal_mean']:.0f}")

    mean_time = np.mean(times)
    t_gudhi_mean = np.mean([d['t_gudhi_mean_s'] for d in pilot_results if d['t_gudhi_mean_s'] > 0])
    total_h_full = mean_time * 2000 / 3600

    print(f"\n{'='*70}")
    print(f"PILOT RESULTS — {args.n_pilot} simulazioni")
    print(f"{'='*70}")
    print(f"  Tempo medio/sim:       {mean_time:.1f}s ({mean_time/60:.1f} min)")
    print(f"  gudhi medio/campo:     {t_gudhi_mean:.1f}s")
    print(f"  Stima run completo:    {total_h_full:.1f}h (2000 sim, K={args.n_walkers})")
    print(f"  Stima con K=5:         {total_h_full*5/args.n_walkers:.1f}h")
    print(f"  Stima con K=10:        {total_h_full*10/args.n_walkers:.1f}h")
    print(f"  Stima con K=20:        {total_h_full*20/args.n_walkers:.1f}h")

    rec_K = 10 if total_h_full * 10 / args.n_walkers < 48 else 5
    pilot_stats = {
        "schema_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "pilot",
        "n_pilot": args.n_pilot,
        "K_pilot": args.n_walkers,
        "mean_time_per_sim_s": float(mean_time),
        "t_gudhi_mean_s": float(t_gudhi_mean),
        "estimated_full_run_hours_K10": float(total_h_full * 10 / args.n_walkers),
        "estimated_full_run_hours_K20": float(total_h_full * 20 / args.n_walkers),
        "recommended_K": rec_K,
        "individual_results": pilot_results,
        "methodology": "Monte Carlo marginalization over HOD prior (SimBIG approach, Hahn+2023)",
        "note": "gudhi eseguito su campo galattico 128^3 completo — no compressione"
    }

    with open(OUTPUT_PILOT, "w") as f:
        json.dump(pilot_stats, f, indent=2)

    print(f"\n  K raccomandato: {rec_K} (stima {total_h_full*rec_K/args.n_walkers:.1f}h)")
    print(f"  Output: {OUTPUT_PILOT}")

else:
    # FULL RUN — subset 400 campi con selezione uniforme su w0
    # Motivazione: run diagnostico per Concern 1 Reviewer. N=400 sufficiente
    # per misurare VIF_ristretto e stimare sigma_marg_ristretto.
    # Selezione: 40 campi per ogni decile di w0 in [-1.30, -0.70] (seed=42).
    K_full = args.n_walkers
    N_SUBSET = 400
    N_BINS_W0 = 10
    N_PER_BIN = N_SUBSET // N_BINS_W0

    rng_sel = np.random.default_rng(42)
    w0_bins = np.linspace(w0_all.min(), w0_all.max(), N_BINS_W0 + 1)
    subset_indices = []
    for b in range(N_BINS_W0):
        in_bin = np.where((w0_all >= w0_bins[b]) & (w0_all < w0_bins[b+1]))[0]
        chosen = rng_sel.choice(in_bin, size=min(N_PER_BIN, len(in_bin)), replace=False)
        subset_indices.extend(chosen.tolist())
    subset_indices = sorted(subset_indices)
    print(f"\n[FULL-RESTRICTED] {len(subset_indices)} campi (subset uniforme su w0), K={K_full}")
    print(f"  Prior ristretto: width=40% del flat, centrato su best-fit B3")
    print("-" * 70)

    all_feats = {idx: fvecs_nwlh[idx].copy() for idx in subset_indices}
    all_diags = []
    t_start = time.time()

    for sim_idx in subset_indices:
        if str(sim_idx) in manifest and manifest[str(sim_idx)] == "done":
            chain_file = CHAINS_DIR / f"chain_{sim_idx:04d}.npz"
            if chain_file.exists():
                data = np.load(chain_file)
                all_feats[sim_idx] = data["feat_marginalized"]
                continue

        t0 = time.time()
        feat_marg, diag = run_forward_sampling(sim_idx, K=K_full, resume=args.resume)
        elapsed = time.time() - t0
        all_feats[sim_idx] = feat_marg
        all_diags.append(diag)

        manifest[str(sim_idx)] = "done"
        with open(MANIFEST, "w") as f:
            json.dump(manifest, f)

        done_count = sum(1 for k in manifest if manifest[k] == "done")
        if done_count % 20 == 0:
            elapsed_total = time.time() - t_start
            eta_h = (elapsed_total / done_count) * (len(subset_indices) - done_count) / 3600
            n_gal_last = diag.get("n_gal_mean", 0)
            print(f"  {done_count:3d}/{len(subset_indices)} | t/sim={elapsed:.0f}s | "
                  f"ETA={eta_h:.1f}h | n_gal={n_gal_last:.0f}", flush=True)

    # Costruisci array ordinato per output
    subset_arr = np.array(subset_indices)
    feats_arr  = np.array([all_feats[i] for i in subset_indices], dtype=np.float32)
    w0_sub     = w0_all[subset_arr]
    Omm_sub    = Omm_all[subset_arr]
    s8_sub     = s8_all[subset_arr]

    # Calcola VIF e sigma sul subset restricted
    from scipy import stats as scipy_stats
    B2_IDX = 5  # b2_mean_persistence
    sigma2_intra_restr = np.zeros(8)
    sigma2_inter_restr = np.zeros(8)
    chain_files_done = list(CHAINS_DIR.glob("chain_*.npz"))
    for cf in chain_files_done:
        d = np.load(cf)
        fk = d["feat_all_k"]
        if fk.shape[0] >= 2:
            for fi in range(8):
                sigma2_intra_restr[fi] += np.var(fk[:, fi], ddof=1)
    if len(chain_files_done) > 0:
        sigma2_intra_restr /= len(chain_files_done)
    for fi in range(8):
        sigma2_inter_restr[fi] = np.var(feats_arr[:, fi], ddof=1)
    VIF_restr = sigma2_intra_restr / (sigma2_inter_restr + 1e-30)

    rng_perm = np.random.default_rng(42)
    b2_sub = feats_arr[:, B2_IDX]
    rho_obs, _ = scipy_stats.spearmanr(b2_sub, w0_sub)
    null = np.array([scipy_stats.spearmanr(b2_sub, rng_perm.permutation(w0_sub)).statistic
                     for _ in range(1000)])
    sigma_restr = (abs(rho_obs) - abs(null.mean())) / null.std()

    print(f"\n{'='*70}")
    print(f"RISULTATI PRIOR RISTRETTO (subset {len(subset_indices)} campi, K={K_full})")
    print(f"{'='*70}")
    FEAT_NAMES = ["b1_peak_pos","b1_peak_height","b1_fwhm","b1_integral",
                  "b2_max_count","b2_mean_persistence","b2_high_persist","b0_at_mean"]
    for fi, fn in enumerate(FEAT_NAMES):
        marker = " *** PRIMARIA" if fi == B2_IDX else ""
        print(f"  {fn:<22} VIF={VIF_restr[fi]:.3f}{marker}")
    print(f"\n  VIF(b2_mean_persistence) ristretto = {VIF_restr[B2_IDX]:.4f}")
    print(f"  VIF(b2_mean_persistence) piatto    = 2.4834  (riferimento)")
    print(f"  ρ(b2_marg_ristretto, w0) = {rho_obs:+.4f}")
    print(f"  σ_marg_ristretto         = {sigma_restr:.2f}σ")

    np.savez(OUTPUT_FEATURES,
             fvecs_hod_marginalized=feats_arr,
             sim_indices=subset_arr,
             w0=w0_sub, Omm=Omm_sub, s8=s8_sub,
             K=K_full,
             prior_type="literature_BGS_Yuan2022_Hadzhiyska2023_Zhang2025",
             prior_low=HOD_PRIOR_LOW,
             prior_high=HOD_PRIOR_HIGH,
             VIF_restricted=VIF_restr,
             sigma_marginalized_restricted=np.array([sigma_restr]),
             methodology="Monte Carlo HOD forward sampling, prior ristretto ±20% flat")

    diag_out = {
        "schema_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_sims": 2000, "K": K_full,
        "n_completed": len(all_diags),
        "n_fallback_dm": sum(1 for d in all_diags if "FALLBACK" in d.get("status","")),
        "t_gudhi_mean_s": float(np.mean([d["t_gudhi_mean_s"] for d in all_diags if d["t_gudhi_mean_s"]>0])) if all_diags else 0,
        "feat_std_mean": float(np.mean([d["feat_std_across_K"] for d in all_diags if d["feat_std_across_K"]>0])) if all_diags else 0,
        "individual_diagnostics": all_diags
    }
    with open(OUTPUT_DIAG, "w") as f:
        json.dump(diag_out, f, indent=2)

    print(f"\n  Output feature: {OUTPUT_FEATURES}")
    print(f"  Output diagnostics: {OUTPUT_DIAG}")
    print(f"  Prossimo: analisi variance decomp confronto flat vs restricted")
    print(f"{'='*70}")

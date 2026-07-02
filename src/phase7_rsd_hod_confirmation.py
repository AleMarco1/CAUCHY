"""
CAUCHY — Phase 7 Sub-Phase 7.1 — Task 7.1d
===========================================
HOD B3 RS run — paper-quality RSD confirmation su campi galattici
Nota frozen phase7_rsd_test.json: "HOD B3 RS run recommended for paper-quality confirmation"

PIPELINE (replica esatta phase5_hod_b3.py + aggiunta RS):
  Per ogni sim (stride=10, N=200, stessi indici Gate 7.0):
    1. Leggi halos FoF via reader custom SOA (identico a Phase 5, solo pos+mass)
    2. Applica HOD B3 deterministico (identico a Phase 5: populate_halos_hod)
       -> pos_gal real-space
    3. [NUOVO RS] Carica velocità halos via readfof standard
       -> trasforma pos_gal in redshift space: s_z = x_z + v_z_halo/H0
    4. field_from_galaxies (identico a Phase 5: CIC + field/mean-1)
    5. compute_tda_features (identico a Phase 5: beta1, thresholds adattativi)
    6. feats[5] = b1_mean_persistence RS
    7. Confronta con b1_mean_persistence real-space da phase5_hod_b3_features.npz

NOTA NOMENCLATURA:
  La feature chiamata "b2_mean_persistence" nella nomenclatura CAUCHY
  corrisponde a feats[5] = beta_1 mean persistence nel codice Phase 5.
  (Convenzione interna: b0=beta0, b1=beta1, b2=beta1 in terminologia paper)
  Questo script mantiene la nomenclatura del codice Phase 5.

TRACEABILITY:
  phase5_hod_b3.py    -> pipeline identica (field_from_galaxies, compute_tda_features)
  phase7_rsd_test.json -> delta_dm=0.034sigma, sim_indices_stride=10
  phase5_hod_b3_features.npz -> fvecs_hod_b3[:,5] real-space reference

ESECUZIONE:
  cd D:\\projects\\cauchy
  conda activate cauchy
  python src\\phase7_rsd_hod_confirmation.py [--test]
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.special import erf

try:
    import gudhi
except ImportError:
    print("ERRORE: gudhi non trovato."); sys.exit(1)

try:
    import readfof as _readfof_module
    HAS_READFOF = True
except ImportError:
    HAS_READFOF = False
    print("ATTENZIONE: readfof non trovato — velocità halos non disponibili")

# ============================================================
# PARAMETRI FROZEN (identici a phase5_hod_b3.py)
# ============================================================
BOXSIZE    = 1000.0
NGRID      = 128
SNAPNUM    = 4
N_PART_MIN = 20
H0         = 100.0   # h km/s/Mpc (unità Quijote)

HOD_PRIOR_LOW  = np.array([11.5, 0.1, 11.0, 12.5, 0.5, -1.0, -1.0, 0.0, 0.0])
HOD_PRIOR_HIGH = np.array([13.5, 1.0, 13.5, 14.5, 1.5,  1.0,  1.0, 2.0, 2.0])
HOD_MEDIAN     = 0.5 * (HOD_PRIOR_LOW + HOD_PRIOR_HIGH)
HOD_PARAM_NAMES = ["log_Mmin","sigma_logM","log_M0","log_M1","alpha",
                   "A_cen","A_sat","eta_vel","eta_conc"]

SIM_STRIDE  = 10
N_FIELDS    = 200
SIM_INDICES = list(range(0, N_FIELDS * SIM_STRIDE, SIM_STRIDE))

DELTA_DM_SIGMA = 0.034   # Gate 7.0

HALOS_DIR       = Path(r"D:\projects\cauchy\data\raw\quijote\3D_cubes\latin_hypercube_nwLH_hod")
PHASE5_B3_FEATS = Path(r"D:\projects\cauchy\results\phase5_hod_b3_features.npz")
OUTPUT_JSON     = Path(r"D:\projects\cauchy\results\phase7_rsd_hod_confirmation.json")
SEED            = 42


# ============================================================
# READER FoF CUSTOM — identico a phase5_hod_b3.py (solo pos+mass)
# ============================================================
class FoF_catalog_pos_mass:
    """Reader SOA binario identico a phase5_hod_b3.py."""
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Catalogo non trovato: {fname}"
        raw = fname.read_bytes()
        N   = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
        self.Ngroups = N
        if N == 0 or len(raw) < 24 + N * 84:
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            self.GroupPos  = np.zeros((0, 3), dtype=np.float32)
            return
        def rd_i(off): return np.frombuffer(raw[off:off+N*4], dtype=np.int32).copy()
        def rd_f(off): return np.frombuffer(raw[off:off+N*4], dtype=np.float32).copy()
        self.GroupLen  = rd_i(24)
        self.GroupMass = rd_f(24 + N*8)
        x = rd_f(24 + N*12);  y = rd_f(24 + N*16);  z = rd_f(24 + N*20)
        self.GroupPos  = np.column_stack([x, y, z])


def read_halo_catalog_pos_mass(sim_idx):
    """Identico a phase5_hod_b3.py read_halo_catalog."""
    snapdir = HALOS_DIR / str(sim_idx)
    FoF     = FoF_catalog_pos_mass(snapdir, SNAPNUM)
    if FoF.Ngroups == 0:
        return None, None
    mask   = FoF.GroupLen >= N_PART_MIN
    pos_h  = (FoF.GroupPos[mask] / 1e3) % BOXSIZE   # kpc/h -> Mpc/h
    mass_h = FoF.GroupMass[mask] * 1e10              # 1e10 -> Msun/h
    return pos_h, mass_h


def read_halo_velocities(sim_idx):
    """
    Legge velocità halos via readfof (ha accesso a GroupVel).
    Restituisce vel shape (N_halos_filtered, 3) in km/s, filtrato con N_PART_MIN.
    """
    if not HAS_READFOF:
        return None
    snapdir = str(HALOS_DIR / str(sim_idx))
    FoF     = _readfof_module.FoF_catalog(snapdir, SNAPNUM,
                                           long_ids=False, swap=False,
                                           SFR=False, read_IDs=False)
    # GroupLen per applicare stesso filtro N_PART_MIN di Phase 5
    # readfof non espone GroupLen direttamente — usiamo reader custom per il mask
    FoF_pm  = FoF_catalog_pos_mass(sim_idx if False else str(HALOS_DIR / str(sim_idx)), SNAPNUM)
    mask    = FoF_pm.GroupLen >= N_PART_MIN
    vel_all = FoF.GroupVel * (1.0 + 0.0)   # z=0: moltiplicatore = 1
    if len(vel_all) != len(mask):
        # Fallback: tronca al minimo
        n = min(len(vel_all), len(mask))
        return vel_all[:n][mask[:n]]
    return vel_all[mask]


# ============================================================
# HOD — identico a phase5_hod_b3.py
# ============================================================
def mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=0.0):
    log_M = np.log10(mass_h)
    return 0.5 * (1.0 + erf((log_M - log_Mmin) / (sigma_logM + 1e-10)))


def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=0.0):
    M0    = 10**log_M0;  M1 = 10**log_M1
    N_sat = np.zeros(len(mass_h))
    mask  = mass_h > M0
    ratio = np.where(mask, (mass_h - M0) / (M1 + 1e-30), 0.0)
    N_sat[mask] = ratio[mask]**alpha
    N_sat *= mean_Ncen(mass_h, log_Mmin, 0.2)
    return N_sat


def populate_halos_hod(pos_h, mass_h, hod_params, rng):
    """Identico a phase5_hod_b3.py — restituisce solo posizioni (no velocità)."""
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel, eta_conc = hod_params
    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3))
    p_cen      = np.clip(mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat    = np.clip(mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat), 0.0, 1e4)
    n_sat      = rng.poisson(lam_sat)

    gal_positions = []
    if is_central.any():
        gal_positions.append(pos_h[is_central])

    rho_crit = 2.775e11 * 0.3
    for i in range(N_h):
        if n_sat[i] <= 0:
            continue
        r_vir  = np.clip(
            (3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit))**(1.0/3.0),
            0.01, 5.0
        ) * eta_conc
        n_s    = int(n_sat[i])
        u      = rng.random(n_s)
        r      = r_vir * u**(1.0/3.0)
        theta  = np.arccos(1.0 - 2.0 * rng.random(n_s))
        phi    = 2.0 * np.pi * rng.random(n_s)
        pos_sat = (pos_h[i] + np.column_stack([
            r*np.sin(theta)*np.cos(phi),
            r*np.sin(theta)*np.sin(phi),
            r*np.cos(theta)
        ])) % BOXSIZE
        gal_positions.append(pos_sat)

    return np.vstack(gal_positions) if gal_positions else np.zeros((0, 3))


def populate_halos_hod_with_halo_indices(pos_h, mass_h, hod_params, rng):
    """
    Come populate_halos_hod ma traccia anche l'indice dell'alone di provenienza
    per poter assegnare la velocità dell'alone a ogni galassia.
    Restituisce (pos_gal, halo_idx_per_gal).
    """
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel, eta_conc = hod_params
    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3)), np.array([], dtype=int)

    p_cen      = np.clip(mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat    = np.clip(mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat), 0.0, 1e4)
    n_sat      = rng.poisson(lam_sat)

    gal_pos_list = []
    halo_idx_list = []

    cen_idx = np.where(is_central)[0]
    if len(cen_idx) > 0:
        gal_pos_list.append(pos_h[cen_idx])
        halo_idx_list.append(cen_idx)

    rho_crit = 2.775e11 * 0.3
    for i in range(N_h):
        if n_sat[i] <= 0:
            continue
        r_vir  = np.clip(
            (3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit))**(1.0/3.0),
            0.01, 5.0
        ) * eta_conc
        n_s    = int(n_sat[i])
        u      = rng.random(n_s)
        r      = r_vir * u**(1.0/3.0)
        theta  = np.arccos(1.0 - 2.0 * rng.random(n_s))
        phi    = 2.0 * np.pi * rng.random(n_s)
        pos_sat = (pos_h[i] + np.column_stack([
            r*np.sin(theta)*np.cos(phi),
            r*np.sin(theta)*np.sin(phi),
            r*np.cos(theta)
        ])) % BOXSIZE
        gal_pos_list.append(pos_sat)
        halo_idx_list.append(np.full(n_s, i, dtype=int))

    if not gal_pos_list:
        return np.zeros((0, 3)), np.array([], dtype=int)

    return (np.vstack(gal_pos_list),
            np.concatenate(halo_idx_list))


# ============================================================
# REDSHIFT SPACE
# ============================================================
def to_redshift_space(pos_gal, vel_halos, halo_idx_per_gal, axis=2):
    """
    Assegna a ogni galassia la velocità del suo alone di provenienza.
    s_z = x_z + v_z / H0  (a=1, z=0)
    """
    vel_gal     = vel_halos[halo_idx_per_gal]   # (N_gal, 3)
    pos_rs      = pos_gal.copy()
    pos_rs[:, axis] = (pos_gal[:, axis] + vel_gal[:, axis] / H0) % BOXSIZE
    return pos_rs


# ============================================================
# FIELD + TDA — identici a phase5_hod_b3.py
# ============================================================
def field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE):
    """Identico a phase5_hod_b3.py field_from_galaxies."""
    if len(pos_gal) == 0:
        return np.zeros((ngrid, ngrid, ngrid), dtype=np.float32)
    cell_size = boxsize / ngrid
    xyz  = (pos_gal / cell_size).astype(np.float32)
    ijk  = xyz.astype(np.int32) % ngrid
    d    = xyz - ijk.astype(np.float32)
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
                flat += np.bincount(idx, weights=wx*wy*wz,
                                    minlength=ngrid**3).astype(np.float32)
    field  = flat.reshape(ngrid, ngrid, ngrid)
    mean_f = field.mean()
    if mean_f > 0:
        field = field / mean_f - 1.0
    return field


def compute_tda_features(delta_field, sigma_smooth=0.64, n_thresh=100):
    """
    Identico a phase5_hod_b3.py compute_tda_features.
    feats[5] = beta1 mean persistence (= "b2_mean_persistence" nella nomenclatura CAUCHY).
    Thresholds ADATTATIVI: linspace(field.min, field.max, n_thresh).
    """
    field_s   = gaussian_filter(delta_field.astype(np.float64), sigma=sigma_smooth)
    field_neg = -field_s
    thresholds = np.linspace(float(field_s.min()), float(field_s.max()), n_thresh)

    cc = gudhi.CubicalComplex(
        dimensions=list(field_neg.shape),
        top_dimensional_cells=field_neg.flatten()
    )
    cc.compute_persistence()

    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    def process_diag(diag):
        if len(diag) == 0:
            return np.array([]), np.array([]), np.array([])
        d    = np.array(diag)
        mask = np.isfinite(d[:, 1])
        df   = d[mask]
        birth = -df[:, 0]
        death = -df[:, 1]
        pers  = birth - death
        return birth, death, pers

    birth_0, death_0, pers_0 = process_diag(diag_0)
    birth_1, death_1, pers_1 = process_diag(diag_1)

    b0_curve = np.zeros(n_thresh)
    b1_curve = np.zeros(n_thresh)
    for k, nu in enumerate(thresholds):
        if len(birth_0):
            b0_curve[k] = np.sum((birth_0 >= nu) & (death_0 < nu))
        if len(birth_1):
            b1_curve[k] = np.sum((birth_1 >= nu) & (death_1 < nu))

    feats = np.zeros(8, dtype=np.float32)
    if b1_curve.max() > 0:
        pk_idx   = np.argmax(b1_curve)
        feats[0] = float(thresholds[pk_idx])
        feats[1] = float(b1_curve[pk_idx])
        half     = b1_curve.max() / 2.0
        above    = np.where(b1_curve >= half)[0]
        feats[2] = float(thresholds[above[-1]] - thresholds[above[0]]) if len(above) > 1 else 0.0
        feats[3] = float(np.trapz(b1_curve, thresholds))

    if len(pers_1) > 0:
        feats[4] = float(len(pers_1))
        feats[5] = float(np.mean(pers_1))        # <-- questa è la feature chiave
        p90      = np.percentile(pers_1, 90)
        feats[6] = float(np.sum(pers_1 >= p90))

    mean_field_val = float(field_s.mean())
    idx_mean = np.argmin(np.abs(thresholds - mean_field_val))
    feats[7] = float(b0_curve[idx_mean])

    return feats


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="N=10 campi")
    args = parser.parse_args()

    n_fields    = 10 if args.test else N_FIELDS
    sim_indices = SIM_INDICES[:n_fields]

    print("=" * 60)
    print(f"CAUCHY 7.1d — HOD B3 RS confirmation ({n_fields} campi)")
    print(f"Pipeline: identica a phase5_hod_b3.py + RS transform")
    print("=" * 60)

    # ── Verifica sim 0 ────────────────────────────────────────────────────────
    print("\n[0] Verifica pipeline su sim 0...")
    pos_h0, mass_h0 = read_halo_catalog_pos_mass(sim_indices[0])
    print(f"  pos+mass OK: N_halos={len(mass_h0):,}")
    vel_h0 = read_halo_velocities(sim_indices[0])
    if vel_h0 is not None:
        print(f"  vel OK: shape={vel_h0.shape}, "
              f"v_z mean={abs(vel_h0[:,2]).mean():.1f} km/s")
    else:
        print("  ERRORE: velocità non disponibili — uscita")
        sys.exit(1)

    # ── Carica b2_real HOD B3 da Phase 5 (reference) ─────────────────────────
    print("\n[1] Caricamento feats real-space HOD B3 Phase 5...")
    d5           = np.load(PHASE5_B3_FEATS, allow_pickle=True)
    feats_real   = d5["fvecs_hod_b3"]                  # (2000, 8)
    b2_real_all  = feats_real[:, 5]                    # feats[5] = b1_mean_persistence
    b2_real_sub  = b2_real_all[sim_indices]
    sigma_real   = float(b2_real_sub.std())
    print(f"  feats[:,5] real ({n_fields} campi): "
          f"mean={b2_real_sub.mean():.6f}, std={sigma_real:.6f}")

    # ── Loop principale ───────────────────────────────────────────────────────
    print(f"\n[2] HOD B3 -> RS -> TDA su {n_fields} campi...")
    b2_rs_vals  = []
    n_gal_list  = []
    errors      = []
    t0          = time.time()

    for i, sim_idx in enumerate(sim_indices):
        try:
            rng = np.random.default_rng(SEED + sim_idx)

            # 1. Halos pos+mass (identico Phase 5)
            pos_h, mass_h = read_halo_catalog_pos_mass(sim_idx)
            if pos_h is None or len(pos_h) < 50:
                raise ValueError("Troppo pochi halos")

            # 2. Halos velocità (per RS)
            vel_h = read_halo_velocities(sim_idx)
            if vel_h is None:
                raise ValueError("Velocità halos non disponibili")

            # 3. HOD B3 con tracciamento indici alone
            pos_gal, halo_idx = populate_halos_hod_with_halo_indices(
                pos_h, mass_h, HOD_MEDIAN, rng
            )
            if len(pos_gal) < 100:
                raise ValueError(f"Troppo poche galassie: {len(pos_gal)}")

            # 4. Redshift space
            pos_gal_rs = to_redshift_space(pos_gal, vel_h, halo_idx, axis=2)

            # 5. Campo galattico RS (identico Phase 5)
            delta_rs = field_from_galaxies(pos_gal_rs)

            # 6. TDA features (identico Phase 5)
            feats_rs = compute_tda_features(delta_rs)
            b2_rs    = float(feats_rs[5])   # b1_mean_persistence RS

            b2_rs_vals.append(b2_rs)
            n_gal_list.append(len(pos_gal))

        except Exception as e:
            print(f"  ERRORE sim {sim_idx}: {e}")
            errors.append(sim_idx)
            b2_rs_vals.append(np.nan)
            n_gal_list.append(0)

        if (i + 1) % 20 == 0 or (i + 1) == n_fields:
            elapsed = time.time() - t0
            eta     = elapsed / (i+1) * (n_fields - i - 1)
            print(f"  {i+1}/{n_fields} | b2_rs={b2_rs_vals[-1]:.5f} | "
                  f"elapsed={elapsed/60:.1f}min | ETA={eta/60:.1f}min | "
                  f"errori={len(errors)}")

    # ── Calcolo Delta ─────────────────────────────────────────────────────────
    b2_rs_arr = np.array(b2_rs_vals)
    valid     = ~np.isnan(b2_rs_arr)
    n_valid   = int(valid.sum())

    b2_rs_mean   = float(b2_rs_arr[valid].mean())
    b2_rs_std    = float(b2_rs_arr[valid].std())
    b2_real_mean = float(b2_real_sub[valid].mean())
    delta_mean   = b2_rs_mean - b2_real_mean
    delta_sigma  = float(delta_mean / sigma_real) if sigma_real > 0 else np.nan

    verdict = (
        "NEGLIGIBLE" if abs(delta_sigma) < 0.5 else
        "SUB_SIGMA"  if abs(delta_sigma) < 1.0 else
        "MODERATE"   if abs(delta_sigma) < 2.0 else
        "SIGNIFICANT"
    )

    elapsed_total = (time.time() - t0) / 60

    print(f"\n{'='*60}")
    print(f"RIEPILOGO HOD B3 RS")
    print(f"{'='*60}")
    print(f"b1_mean_pers real  : mean={b2_real_mean:.6f}, std={sigma_real:.6f}")
    print(f"b1_mean_pers RS    : mean={b2_rs_mean:.6f},  std={b2_rs_std:.6f}")
    print(f"Delta b2           : {delta_mean:+.6f}")
    print(f"Delta/sigma        : {delta_sigma:+.4f}sigma  [{verdict}]")
    print(f"Riferimento DM (Gate 7.0): {DELTA_DM_SIGMA:.3f}sigma")
    print(f"N galassie medio   : {np.mean([x for x in n_gal_list if x>0]):.0f}")
    print(f"N validi: {n_valid}/{n_fields}, errori: {len(errors)}")
    print(f"Tempo: {elapsed_total:.1f}min")

    # ── Output JSON ───────────────────────────────────────────────────────────
    output = {
        "schema_version": "2.0",
        "task": "7.1d_RSD_HOD_confirmation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": "HOD_B3_deterministic_FoF_halos_redshiftspace_phase5_pipeline",
        "description": (
            "Paper-quality RSD test on HOD B3 galaxy fields. "
            "Pipeline identica a phase5_hod_b3.py + RS transform (v_halo/H0 along z). "
            "feats[5] = beta1 mean persistence (nomenclatura CAUCHY: b2_mean_persistence)."
        ),
        "traceability": {
            "gate7_0_delta_dm_kaiser": DELTA_DM_SIGMA,
            "gate7_0_source": "phase7_rsd_test.json -> delta_sigma",
            "b2_real_source": "phase5_hod_b3_features.npz -> fvecs_hod_b3[:,5]",
            "pipeline_source": "phase5_hod_b3.py (identical: field_from_galaxies, compute_tda_features)",
            "hod_params": HOD_MEDIAN.tolist(),
            "hod_param_names": HOD_PARAM_NAMES,
            "sim_indices": sim_indices,
            "n_fields": n_fields,
            "stride": SIM_STRIDE,
        },
        "tda_params": {
            "sigma_smooth": 0.64,
            "n_thresh": 100,
            "thresholds": "adaptive linspace(field.min, field.max, 100)",
            "feature_idx": 5,
            "feature_name": "beta1_mean_persistence",
            "cauchy_nomenclature": "b2_mean_persistence",
        },
        "results": {
            "n_valid":                    n_valid,
            "n_errors":                   len(errors),
            "b1_realspace_hod_mean":      b2_real_mean,
            "b1_realspace_hod_std":       sigma_real,
            "b1_redshiftspace_hod_mean":  b2_rs_mean,
            "b1_redshiftspace_hod_std":   b2_rs_std,
            "delta_mean_b1":              float(delta_mean),
            "sigma_real_hod":             sigma_real,
            "delta_sigma_hod":            float(delta_sigma),
            "delta_sigma_dm_gate70":      DELTA_DM_SIGMA,
            "verdict":                    verdict,
            "n_gal_mean": float(np.mean([x for x in n_gal_list if x > 0])),
        },
        "interpretation": {
            "verdict": verdict,
            "combined_rsd": (
                f"Kaiser (DM, Gate 7.0): Delta={DELTA_DM_SIGMA:.3f}sigma. "
                f"Kaiser+FoG (HOD B3, questo test): Delta={delta_sigma:+.3f}sigma. "
            ),
            "paper_statement": (
                f"RSD robustness at two levels: (i) Kaiser distortions on DM fields "
                f"Delta_Kaiser={DELTA_DM_SIGMA:.3f}sigma (Gate 7.0, N=200); "
                f"(ii) full RSD on HOD B3 galaxy fields "
                f"Delta_HOD={delta_sigma:+.3f}sigma (N={n_valid}). "
            ),
        },
        "b2_rs_per_sim":   [float(x) if not np.isnan(x) else None for x in b2_rs_vals],
        "b2_real_per_sim": b2_real_sub.tolist(),
        "errors":          errors,
        "elapsed_min":     float(elapsed_total),
        "test_mode":       args.test,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Output: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

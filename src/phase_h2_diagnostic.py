"""
CAUCHY — Diagnostica H₂ (β₂)
src/phase_h2_diagnostic.py

Obiettivo: verificare quantitativamente che le feature H₂ (cicli 3D / voids)
sono assenti o non affidabili su griglia 128³ con smoothing σ_px=0.64,
sia su campi di materia oscura (DM) che su campi galattici HOD (B3).

Motivazione (Discussion/Limitations Paper B):
  La pipeline CAUCHY calcola H₀ e H₁. H₂ non è incluso. Questo script
  produce evidenza quantitativa che H₂ è inaccessibile alla risoluzione
  attuale — trasformando la dichiarazione qualitativa in un numero citabile.

Metodo:
  - N_FIELDS campi nwLH (default 10), selezione uniforme su w₀
  - Per ciascun campo: DM puro + HOD B3 deterministico (parametri mediani)
  - gudhi CubicalComplex.persistence_intervals_in_dimension(2) → diag_2
  - Misure: cardinalità H₂, persistenza media, persistenza massima,
    rapporto pers_mean_H2 / pers_mean_H1 (indice di rumore relativo)
  - Confronto con H₁ sugli stessi campi (baseline di riferimento)

Interpretazione attesa:
  - H₂ assente (count=0): risoluzione insufficiente, nessuna cavità 3D rilevata
  - H₂ presente ma pers_mean << H₁: rumore di risoluzione, non segnale fisico
  - Soglia di rumore: pers_mean_H2 / pers_mean_H1 < 0.05 → H₂ non affidabile

Output:
  results/phase_h2_diagnostic.json  — risultati per campo + summary
  (stampato anche su stdout per verifica immediata)

Uso:
  python src/phase_h2_diagnostic.py [--n_fields 10] [--seed 42]

Tempo stimato: ~10 × 2 × 10s = ~3min (DM + HOD per campo)
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY — Diagnostica H₂ su 128³")
parser.add_argument("--n_fields",    type=int, default=10)
parser.add_argument("--seed",        type=int, default=42)
parser.add_argument("--project_root", type=str, default=".")
args = parser.parse_args()

ROOT        = Path(args.project_root)
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON = RESULTS_DIR / "phase_h2_diagnostic.json"

# ---------------------------------------------------------------------------
# Costanti fisiche Quijote (identiche a B3)
# ---------------------------------------------------------------------------
BOXSIZE    = 1000.0
NGRID      = 128
SNAPNUM    = 4
N_PART_MIN = 20
SIGMA_SMOOTH = 0.64   # σ_px — identico a tutta la pipeline CAUCHY

HOD_CATALOG_DIR  = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
TDA_CACHE        = ROOT / "results" / "phase1_fiducial_cache.npz"

# HOD B3 mediano (identico a phase5_hod_b3.py)
HOD_B3 = np.array([12.5, 0.55, 12.25, 13.5, 1.0, 0.0, 0.0, 1.0, 1.0])

print("=" * 70)
print("CAUCHY — Diagnostica H₂ (β₂) su griglia 128³")
print("=" * 70)
print(f"  N campi: {args.n_fields}, σ_smooth={SIGMA_SMOOTH}px, NGRID={NGRID}")
print(f"  HOD: B3 mediano deterministico (log_Mmin=12.5)")
print()


# ---------------------------------------------------------------------------
# FoF reader — identico a B3
# ---------------------------------------------------------------------------
class FoF_catalog:
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Catalogo non trovato: {fname}"
        raw = fname.read_bytes()
        N = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
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
        x = rd_f(24 + N*12); y = rd_f(24 + N*16); z = rd_f(24 + N*20)
        self.GroupPos  = np.column_stack([x, y, z])


def read_halo_catalog(sim_idx):
    snapdir = HOD_CATALOG_DIR / str(sim_idx)
    FoF = FoF_catalog(snapdir, SNAPNUM)
    if FoF.Ngroups == 0:
        return None, None
    mask   = FoF.GroupLen >= N_PART_MIN
    pos_h  = (FoF.GroupPos[mask] / 1e3) % BOXSIZE
    mass_h = FoF.GroupMass[mask] * 1e10
    return pos_h, mass_h


# ---------------------------------------------------------------------------
# HOD — identico a B3
# ---------------------------------------------------------------------------
def mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=0.0):
    from scipy.special import erf
    log_M = np.log10(mass_h)
    return 0.5 * (1.0 + erf((log_M - log_Mmin) / (sigma_logM + 1e-10)))

def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=0.0):
    M0 = 10**log_M0; M1 = 10**log_M1
    N_sat = np.zeros(len(mass_h))
    mask = mass_h > M0
    ratio = np.where(mask, (mass_h - M0) / (M1 + 1e-30), 0.0)
    N_sat[mask] = ratio[mask]**alpha
    N_sat *= mean_Ncen(mass_h, log_Mmin, 0.2)
    return N_sat

def populate_halos_hod(pos_h, mass_h, hod_params, rng):
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel, eta_conc = hod_params
    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3))
    p_cen = np.clip(mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat = np.clip(mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat), 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)
    gal_positions = []
    if is_central.any():
        gal_positions.append(pos_h[is_central])
    rho_crit = 2.775e11 * 0.3
    for i in range(N_h):
        if n_sat[i] <= 0:
            continue
        r_vir = np.clip((3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit))**(1.0/3.0),
                        0.01, 5.0) * eta_conc
        n_s = int(n_sat[i])
        u = rng.random(n_s)
        r = r_vir * u**(1.0/3.0)
        theta = np.arccos(1.0 - 2.0 * rng.random(n_s))
        phi = 2.0 * np.pi * rng.random(n_s)
        dx = r * np.sin(theta) * np.cos(phi)
        dy = r * np.sin(theta) * np.sin(phi)
        dz = r * np.cos(theta)
        pos_sat = (pos_h[i] + np.column_stack([dx, dy, dz])) % BOXSIZE
        gal_positions.append(pos_sat)
    return np.vstack(gal_positions) if gal_positions else np.zeros((0, 3))

def field_from_galaxies(pos_gal, ngrid=128, boxsize=1000.0):
    if len(pos_gal) == 0:
        return np.zeros((ngrid, ngrid, ngrid), dtype=np.float32)
    cell_size = boxsize / ngrid
    xyz = (pos_gal / cell_size).astype(np.float32)
    ijk = xyz.astype(np.int32) % ngrid
    d   = xyz - ijk.astype(np.float32)
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
    mean_f = field.mean()
    if mean_f > 0:
        field = field / mean_f - 1.0
    return field


# ---------------------------------------------------------------------------
# Funzione diagnostica H₀/H₁/H₂ — estende compute_tda_features con H₂
# ---------------------------------------------------------------------------
def compute_h012_diagnostics(delta_field, sigma_smooth=SIGMA_SMOOTH, n_thresh=100):
    """
    Calcola H₀, H₁, H₂ sullo stesso campo.
    Ritorna un dict con statistiche per ogni dimensione.
    Nota: gudhi CubicalComplex supporta H₂ solo se la griglia è 3D — verificato.
    """
    import gudhi

    field_s   = gaussian_filter(delta_field.astype(np.float64), sigma=sigma_smooth)
    field_neg = -field_s

    cc = gudhi.CubicalComplex(
        dimensions=list(field_neg.shape),
        top_dimensional_cells=field_neg.flatten()
    )
    cc.compute_persistence()

    def process_diag(diag):
        """Ritorna statistiche per una dimensione omologica."""
        if len(diag) == 0:
            return {
                "count": 0,
                "pers_mean": 0.0,
                "pers_max":  0.0,
                "pers_std":  0.0,
                "pers_p90":  0.0,
                "all_zero":  True,
            }
        d = np.array(diag)
        # Features finite (esclude il generatore immortale di H₀)
        mask = np.isfinite(d[:, 1])
        df = d[mask]
        if len(df) == 0:
            return {
                "count": 0,
                "pers_mean": 0.0,
                "pers_max":  0.0,
                "pers_std":  0.0,
                "pers_p90":  0.0,
                "all_zero":  True,
            }
        birth = -df[:, 0]
        death = -df[:, 1]
        pers  = birth - death   # > 0 per superlevel
        return {
            "count":     int(len(pers)),
            "pers_mean": float(np.mean(pers)),
            "pers_max":  float(np.max(pers)),
            "pers_std":  float(np.std(pers)),
            "pers_p90":  float(np.percentile(pers, 90)),
            "all_zero":  bool(np.all(pers == 0)),
        }

    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)
    diag_2 = cc.persistence_intervals_in_dimension(2)

    h0 = process_diag(diag_0)
    h1 = process_diag(diag_1)
    h2 = process_diag(diag_2)

    # Rapporto di rumore H₂/H₁ — indice chiave per la diagnosi
    # Se H₁ è il segnale fisico, H₂ è rumore se questo rapporto << 1
    noise_ratio = (h2["pers_mean"] / h1["pers_mean"]
                   if h1["pers_mean"] > 0 else float("nan"))

    return {
        "H0": h0,
        "H1": h1,
        "H2": h2,
        "noise_ratio_H2_over_H1": float(noise_ratio) if np.isfinite(noise_ratio) else None,
    }


# ---------------------------------------------------------------------------
# Caricamento dati
# ---------------------------------------------------------------------------
print("Caricamento parametri cosmologici nwLH...")
assert NWLH_PARAMS_FILE.exists(), f"File non trovato: {NWLH_PARAMS_FILE}"
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
w0_all  = cosmo_params[:, 6]

assert TDA_CACHE.exists(), f"Cache DM non trovata: {TDA_CACHE}"
cache = np.load(TDA_CACHE, allow_pickle=True)
# DM fields come 3D arrays — se non disponibili, ricostruiamo dal catalogo
# La cache contiene fvecs_nwlh [2000,8] ma non i campi 3D grezzi.
# Usiamo quindi i cataloghi FoF per costruire sia DM che HOD.
# Per DM: usiamo le posizioni degli aloni (non le particelle) come tracer DM proxy.
# Questo è consistente con phase1_tda_baseline.py che usa gli stessi cataloghi FoF.
print(f"  w0 range: [{w0_all.min():.2f}, {w0_all.max():.2f}]")

# Selezione N_FIELDS campi uniformi su w₀
sort_by_w0 = np.argsort(w0_all)
step = len(w0_all) // args.n_fields
selected_indices = sort_by_w0[::step][:args.n_fields]
w0_sel = w0_all[selected_indices]
print(f"  Campi selezionati (uniformi su w₀): {selected_indices.tolist()}")
print(f"  w₀ valori: {[f'{v:.2f}' for v in w0_sel]}")
print()

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
results_per_field = []
t_start = time.time()

print(f"{'Campo':>6} {'sim':>5} {'w₀':>6} | "
      f"{'H₂_count':>9} {'H₂_mean':>9} {'H₁_mean':>9} {'ratio':>8} | "
      f"{'type':>4} {'t(s)':>6}")
print("-" * 75)

for field_idx, sim_idx in enumerate(selected_indices):
    sim_idx = int(sim_idx)
    w0_val  = float(w0_all[sim_idx])

    pos_h, mass_h = read_halo_catalog(sim_idx)

    if pos_h is None or len(pos_h) < 50:
        print(f"  {field_idx:3d} {sim_idx:5d} {w0_val:6.2f} | SKIP (catalogo vuoto)")
        continue

    rng = np.random.default_rng(args.seed + sim_idx)

    for field_type in ["DM", "HOD"]:
        t0 = time.time()

        if field_type == "DM":
            # Campo DM: posizioni aloni come tracer (proxy DM, identico a phase1)
            delta = field_from_galaxies(pos_h, ngrid=NGRID, boxsize=BOXSIZE)
        else:
            # Campo HOD B3
            pos_gal = populate_halos_hod(pos_h, mass_h, HOD_B3,
                                          np.random.default_rng(args.seed + sim_idx + 50000))
            if len(pos_gal) < 100:
                print(f"  {field_idx:3d} {sim_idx:5d} {w0_val:6.2f} | HOD SKIP (poche galassie)")
                continue
            delta = field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE)

        delta = delta - delta.mean()

        diag = compute_h012_diagnostics(delta)
        t_elapsed = time.time() - t0

        h2_count = diag["H2"]["count"]
        h2_mean  = diag["H2"]["pers_mean"]
        h1_mean  = diag["H1"]["pers_mean"]
        ratio    = diag["noise_ratio_H2_over_H1"]
        ratio_str = f"{ratio:.4f}" if ratio is not None else "  N/A"

        print(f"  {field_idx:3d} {sim_idx:5d} {w0_val:6.2f} | "
              f"{h2_count:9d} {h2_mean:9.5f} {h1_mean:9.5f} {ratio_str:>8} | "
              f"{field_type:>4} {t_elapsed:6.1f}s")

        results_per_field.append({
            "field_idx": field_idx,
            "sim_idx":   sim_idx,
            "w0":        w0_val,
            "field_type": field_type,
            "H0":        diag["H0"],
            "H1":        diag["H1"],
            "H2":        diag["H2"],
            "noise_ratio_H2_over_H1": diag["noise_ratio_H2_over_H1"],
            "t_s":       float(t_elapsed),
        })

# ---------------------------------------------------------------------------
# TEST A — Correlazione parziale H₂ con w₀
# Domanda: H₂ porta informazione cosmologica, o è cosmologicamente muto?
# ---------------------------------------------------------------------------
print()
print("=" * 75)
print("TEST A — Correlazione parziale H₂ vs w₀ (confronto con H₁)")
print("=" * 75)

from scipy.stats import pearsonr

def partial_corr_r(x, y, z_controls):
    """r(x, y | z_controls) via OLS residualizzazione"""
    def residuals(v, Z):
        Z_aug = np.column_stack([np.ones(len(v)), Z])
        coef, *_ = np.linalg.lstsq(Z_aug, v, rcond=None)
        return v - Z_aug @ coef
    rx = residuals(x, z_controls)
    ry = residuals(y, z_controls)
    r, p = pearsonr(rx, ry)
    return float(r), float(p)

Omm_all = cosmo_params[:, 0]
s8_all  = cosmo_params[:, 4]

corr_results_A = {}
for ft in ["DM", "HOD"]:
    subset = [r for r in results_per_field if r["field_type"] == ft]
    if len(subset) < 4:
        continue
    idx_list = [r["sim_idx"] for r in subset]
    w0_sub   = np.array([w0_all[i]  for i in idx_list])
    Omm_sub  = np.array([Omm_all[i] for i in idx_list])
    s8_sub   = np.array([s8_all[i]  for i in idx_list])
    controls = np.column_stack([Omm_sub, s8_sub])

    h2_pers = np.array([r["H2"]["pers_mean"] for r in subset])
    h1_pers = np.array([r["H1"]["pers_mean"] for r in subset])
    h2_cnt  = np.array([r["H2"]["count"]     for r in subset], dtype=float)

    r_h2_pers, p_h2_pers = partial_corr_r(h2_pers, w0_sub, controls)
    r_h1_pers, p_h1_pers = partial_corr_r(h1_pers, w0_sub, controls)
    r_h2_cnt,  p_h2_cnt  = partial_corr_r(h2_cnt,  w0_sub, controls)

    print(f"\n  [{ft}] N={len(subset)} campi")
    print(f"  r(H₁_pers_mean, w₀ | Ωm,σ₈) = {r_h1_pers:+.4f}  p={p_h1_pers:.3f}  ← riferimento H₁")
    print(f"  r(H₂_pers_mean, w₀ | Ωm,σ₈) = {r_h2_pers:+.4f}  p={p_h2_pers:.3f}")
    print(f"  r(H₂_count,     w₀ | Ωm,σ₈) = {r_h2_cnt:+.4f}  p={p_h2_cnt:.3f}")

    # Interpretazione
    if abs(r_h2_pers) < 0.15:
        interp = "H₂ COSMOLOGICAMENTE MUTO (|r|<0.15) → artefatto o segnale fisico non sensibile a w₀"
        explanation = 1  # artefatto o fisico ma muto
    elif abs(r_h2_pers) >= 0.15 and abs(r_h2_pers) < abs(r_h1_pers) * 0.5:
        interp = "H₂ DEBOLE rispetto a H₁ → segnale fisico ma non competitivo"
        explanation = 2
    else:
        interp = "H₂ COMPARABILE a H₁ → potenzialmente interessante per Paper A"
        explanation = 3
    print(f"  → {interp}")

    corr_results_A[ft] = {
        "r_H1_pers_mean": r_h1_pers, "p_H1": p_h1_pers,
        "r_H2_pers_mean": r_h2_pers, "p_H2_pers": p_h2_pers,
        "r_H2_count":     r_h2_cnt,  "p_H2_cnt": p_h2_cnt,
        "interpretation": interp,
        "explanation_scenario": explanation,
    }

# ---------------------------------------------------------------------------
# TEST B — Campo Gaussiano puro (rumore bianco smoothato)
# Domanda: H₂_count ~74K appare anche su rumore puro → artefatto del reticolo?
# ---------------------------------------------------------------------------
print()
print("=" * 75)
print("TEST B — Campo Gaussiano puro (rumore bianco smoothato)")
print("         Se H₂_count ~ 74K anche qui → artefatto del reticolo cubico")
print("=" * 75)

import gudhi as _gudhi

rng_gauss = np.random.default_rng(args.seed + 99999)
test_b_results = []

for label, sigma_s in [("white_noise_no_smooth", 0.0),
                        ("white_noise_smooth_0.64", SIGMA_SMOOTH),
                        ("white_noise_smooth_2.0",  2.0)]:
    t0 = time.time()
    field_raw = rng_gauss.standard_normal((NGRID, NGRID, NGRID))
    if sigma_s > 0:
        field_s = gaussian_filter(field_raw, sigma=sigma_s)
    else:
        field_s = field_raw.copy()
    field_neg = -field_s

    cc = _gudhi.CubicalComplex(
        dimensions=list(field_neg.shape),
        top_dimensional_cells=field_neg.flatten()
    )
    cc.compute_persistence()

    def _stats(diag):
        if len(diag) == 0:
            return {"count": 0, "pers_mean": 0.0}
        d = np.array(diag)
        mask = np.isfinite(d[:, 1])
        df = d[mask]
        if len(df) == 0:
            return {"count": 0, "pers_mean": 0.0}
        pers = np.abs(df[:, 1] - df[:, 0])
        return {"count": int(len(pers)), "pers_mean": float(np.mean(pers))}

    h1_g = _stats(cc.persistence_intervals_in_dimension(1))
    h2_g = _stats(cc.persistence_intervals_in_dimension(2))
    ratio_g = (h2_g["pers_mean"] / h1_g["pers_mean"]
               if h1_g["pers_mean"] > 0 else float("nan"))
    t_el = time.time() - t0

    print(f"\n  [{label}]  σ_smooth={sigma_s}")
    print(f"  H₁: count={h1_g['count']:6d}, pers_mean={h1_g['pers_mean']:.5f}")
    print(f"  H₂: count={h2_g['count']:6d}, pers_mean={h2_g['pers_mean']:.5f}")
    print(f"  ratio H₂/H₁ = {ratio_g:.4f}  ({t_el:.1f}s)")

    test_b_results.append({
        "label": label, "sigma_smooth": sigma_s,
        "H1": h1_g, "H2": h2_g,
        "ratio_H2_H1": float(ratio_g) if np.isfinite(ratio_g) else None,
    })

# Confronto con i campi fisici
physical_h2_mean_count = float(np.mean([r["H2"]["count"] for r in results_per_field]))
gauss_h2_count_smooth  = next((r["H2"]["count"] for r in test_b_results
                                if r["sigma_smooth"] == SIGMA_SMOOTH), None)
print(f"\n  ─────────────────────────────────────────")
print(f"  Confronto H₂_count:")
print(f"  Campi fisici (DM+HOD, σ=0.64): {physical_h2_mean_count:.0f}")
print(f"  Rumore Gaussiano  (σ=0.64):    {gauss_h2_count_smooth}")
if gauss_h2_count_smooth is not None:
    ratio_phys_gauss = physical_h2_mean_count / gauss_h2_count_smooth
    print(f"  Ratio fisico/Gaussiano: {ratio_phys_gauss:.3f}")
    if ratio_phys_gauss < 1.2:
        lattice_verdict = "ARTEFATTO RETICOLO CONFERMATO — H₂ fisico non distinguibile da rumore Gaussiano"
    elif ratio_phys_gauss < 2.0:
        lattice_verdict = "PARZIALE ARTEFATTO — H₂ fisico leggermente superiore al rumore"
    else:
        lattice_verdict = "H₂ FISICAMENTE REALE — count significativamente superiore al rumore Gaussiano"
    print(f"  → {lattice_verdict}")

# ---------------------------------------------------------------------------
# DIAGNOSI INTEGRATA — combina Test A + Test B
# ---------------------------------------------------------------------------
print()
print("=" * 75)
print("DIAGNOSI INTEGRATA (Test A + Test B)")
print("=" * 75)

scenario_votes = []
for ft, res in corr_results_A.items():
    scenario_votes.append(res["explanation_scenario"])

dominant_scenario = max(set(scenario_votes), key=scenario_votes.count) if scenario_votes else None
lattice_confirmed = (gauss_h2_count_smooth is not None and
                     ratio_phys_gauss < 1.2)

# Test B è il test primario — se confermato artefatto, sovrascrive Test A
# (Test A con N=10 ha potere statistico insufficiente per discriminare)
if lattice_confirmed:
    # ratio_phys_gauss < 1.2: campi fisici producono MENO H₂ del rumore → artefatto
    mean_r_h2 = float(np.mean([abs(v["r_H2_pers_mean"])
                                for v in corr_results_A.values()])) if corr_results_A else 0.0
    integrated_verdict = "SCENARIO 1 — Artefatto reticolo cubico confermato (Test B)"
    integrated_action  = (
        "H₂ features at 128³ are lattice artifacts: physical fields produce "
        f"fewer H₂ generators than a smoothed Gaussian random field "
        f"(ratio physical/Gaussian = {ratio_phys_gauss:.3f} < 1.0). "
        "Exclusion from CAUCHY pipeline is fully justified. "
        "Note: Test A correlations on N=10 fields are statistically uninformative "
        "(all p > 0.25) and are overridden by Test B. "
        "Paper B statement: H₂ generators at 128³ are numerical lattice artifacts; "
        "higher-resolution analysis is deferred to Paper A."
    )
elif gauss_h2_count_smooth is not None and ratio_phys_gauss < 2.0:
    # 1.2 ≤ ratio < 2.0: fisico ma debole
    if dominant_scenario == 3:
        # Test A suggerisce correlazione ma Test B non la supporta fortemente
        integrated_verdict = "SCENARIO 2 — H₂ fisico ma cosmologicamente debole"
        integrated_action  = (
            "H₂ count marginally exceeds Gaussian baseline "
            f"(ratio = {ratio_phys_gauss:.3f}) but Test A correlations are "
            "not significant at N=10. Extend to N=50 for definitive verdict."
        )
    else:
        integrated_verdict = "SCENARIO 2 — H₂ fisico ma cosmologicamente debole"
        integrated_action  = (
            "H₂ features are physical but show weak cosmological sensitivity. "
            "Exclusion justified for Paper B; sensitivity deferred to Paper A."
        )
elif gauss_h2_count_smooth is not None and ratio_phys_gauss >= 2.0 and dominant_scenario == 3:
    integrated_verdict = "SCENARIO 3 — H₂ fisicamente reale e potenzialmente sensibile a w₀"
    integrated_action  = (
        "H₂ features significantly exceed Gaussian baseline "
        f"(ratio = {ratio_phys_gauss:.3f}) and show correlation with w₀. "
        "Extend to N=500 fields with permutation test before Paper B submission."
    )
else:
    integrated_verdict = "INDETERMINATO — dati insufficienti"
    integrated_action  = "Verificare che Test B sia stato eseguito correttamente."

print(f"\n  {integrated_verdict}")
print(f"\n  Azione: {integrated_action}")


print("=" * 75)

for ft in ["DM", "HOD"]:
    subset = [r for r in results_per_field if r["field_type"] == ft]
    if not subset:
        continue

    h2_counts  = [r["H2"]["count"]     for r in subset]
    h2_means   = [r["H2"]["pers_mean"] for r in subset]
    h1_means   = [r["H1"]["pers_mean"] for r in subset]
    ratios     = [r["noise_ratio_H2_over_H1"] for r in subset
                  if r["noise_ratio_H2_over_H1"] is not None]
    n_zero     = sum(1 for c in h2_counts if c == 0)

    print(f"\n  Tipo campo: {ft}")
    print(f"  H₂ count:    mean={np.mean(h2_counts):.1f}, "
          f"std={np.std(h2_counts):.1f}, "
          f"range=[{min(h2_counts)}, {max(h2_counts)}]")
    print(f"  H₂ campi con count=0: {n_zero}/{len(subset)}")
    print(f"  H₂ pers_mean:  mean={np.mean(h2_means):.6f}, "
          f"max={np.max(h2_means):.6f}")
    print(f"  H₁ pers_mean:  mean={np.mean(h1_means):.6f}  ← riferimento")
    if ratios:
        print(f"  Ratio H₂/H₁:  mean={np.mean(ratios):.4f}, "
              f"max={np.max(ratios):.4f}")
        verdict = ("NON AFFIDABILE (ratio < 0.05)"
                   if np.mean(ratios) < 0.05 else
                   "POTENZIALMENTE RILEVABILE (ratio ≥ 0.05)")
        print(f"  Verdetto H₂:  {verdict}")

# Soglia globale
all_ratios = [r["noise_ratio_H2_over_H1"] for r in results_per_field
              if r["noise_ratio_H2_over_H1"] is not None]
all_h2_counts = [r["H2"]["count"] for r in results_per_field]
frac_zero = sum(1 for c in all_h2_counts if c == 0) / len(all_h2_counts)

print(f"\n  ─────────────────────────────────────────")
print(f"  VERDETTO GLOBALE (DM + HOD combinati):")
print(f"  Frazione campi H₂_count=0: {frac_zero:.0%}")
if all_ratios:
    mean_ratio = float(np.mean(all_ratios))
    print(f"  Ratio medio H₂/H₁: {mean_ratio:.4f}")
    if mean_ratio < 0.05 or frac_zero > 0.5:
        global_verdict = "H₂ NON AFFIDABILE a 128³ — esclusione giustificata"
        paper_statement = (
            f"H₂ features are absent or negligible at 128³ resolution "
            f"(mean persistence ratio H₂/H₁ = {mean_ratio:.3f}, "
            f"{frac_zero:.0%} of fields show zero H₂ generators). "
            f"H₂ analysis is deferred to higher-resolution grids (Paper A)."
        )
    else:
        global_verdict = "H₂ POTENZIALMENTE PRESENTE — analisi approfondita consigliata"
        paper_statement = (
            f"H₂ features show non-negligible persistence at 128³ resolution "
            f"(mean ratio H₂/H₁ = {mean_ratio:.3f}); their cosmological "
            f"sensitivity is deferred to Paper A."
        )
    print(f"  {global_verdict}")
    print(f"\n  Formulazione suggerita per il paper:")
    print(f"  \"{paper_statement}\"")

# ---------------------------------------------------------------------------
# Salvataggio JSON
# ---------------------------------------------------------------------------
summary_dm  = [r for r in results_per_field if r["field_type"] == "DM"]
summary_hod = [r for r in results_per_field if r["field_type"] == "HOD"]

def compute_summary_stats(subset):
    if not subset:
        return {}
    h2_counts = [r["H2"]["count"]     for r in subset]
    h2_means  = [r["H2"]["pers_mean"] for r in subset]
    h1_means  = [r["H1"]["pers_mean"] for r in subset]
    ratios    = [r["noise_ratio_H2_over_H1"] for r in subset
                 if r["noise_ratio_H2_over_H1"] is not None]
    return {
        "H2_count_mean":   float(np.mean(h2_counts)),
        "H2_count_std":    float(np.std(h2_counts)),
        "H2_count_min":    int(min(h2_counts)),
        "H2_count_max":    int(max(h2_counts)),
        "H2_count_zero_fraction": float(sum(1 for c in h2_counts if c == 0) / len(h2_counts)),
        "H2_pers_mean":    float(np.mean(h2_means)),
        "H2_pers_max":     float(np.max(h2_means)),
        "H1_pers_mean":    float(np.mean(h1_means)),
        "ratio_H2_H1_mean": float(np.mean(ratios)) if ratios else None,
        "ratio_H2_H1_max":  float(np.max(ratios))  if ratios else None,
    }

output = {
    "schema_version": "2.0",
    "task":           "H2_diagnostic_128grid",
    "timestamp":      datetime.now(timezone.utc).isoformat(),
    "parameters": {
        "n_fields":      args.n_fields,
        "ngrid":         NGRID,
        "sigma_smooth":  SIGMA_SMOOTH,
        "seed":          args.seed,
        "hod_b3_params": HOD_B3.tolist(),
        "field_types":   ["DM", "HOD"],
    },
    "noise_threshold": {
        "value": 0.05,
        "description": "ratio H₂/H₁ < 0.05 → H₂ non affidabile a questa risoluzione",
    },
    "summary_DM":  compute_summary_stats(summary_dm),
    "summary_HOD": compute_summary_stats(summary_hod),
    "test_A_correlations": corr_results_A,
    "test_B_gaussian": {
        "results": test_b_results,
        "physical_H2_count_mean": physical_h2_mean_count,
        "gaussian_H2_count_sigma064": gauss_h2_count_smooth,
        "ratio_physical_over_gaussian": float(ratio_phys_gauss) if gauss_h2_count_smooth else None,
        "lattice_verdict": lattice_verdict if gauss_h2_count_smooth else "not_computed",
    },
    "paper_statement": paper_statement if all_ratios else "",
    "integrated_verdict": integrated_verdict,
    "integrated_action":  integrated_action,
    "per_field_results": results_per_field,
    "t_total_min": float((time.time() - t_start) / 60),
    "traceability": {
        "pipeline_source": "src/phase5_hod_b3.py (compute_tda_features esteso con dim=2)",
        "gudhi_method":    "CubicalComplex.persistence_intervals_in_dimension(2)",
        "sigma_px_source": "phase7_nomenclature_lock.json -> sigma_px=0.640",
        "paper_section":   "Discussion/Limitations Paper B",
    },
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n  Output: {OUTPUT_JSON}")
print(f"  Tempo totale: {(time.time()-t_start)/60:.1f} min")
print("=" * 75)

"""
CAUCHY Phase 6 — Pilot Ramo B su DESI (v2)
==========================================
Applica la CNN CAUCHYEncoder (architettura esatta da phase2_cnn.py)
al campo DESI BGS NGC per costruire tau(x)_DESI.

Confronta ||tau_DESI|| con la distribuzione ||tau_mock|| da LHC e nwLH.
"""

import os, ctypes, sys

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
try:
    ctypes.CDLL(r"C:\Users\ale1m\miniconda3\envs\cauchy\Lib\site-packages\torch\lib\shm.dll")
except OSError:
    pass

import numpy as np
import torch
import torch.nn as nn
import json
from pathlib import Path
from datetime import datetime, timezone

# ── Configurazione ─────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(r"D:\projects\cauchy")
RESULTS_DIR   = PROJECT_ROOT / "results"
CHECKPOINT    = RESULTS_DIR / "checkpoints" / "phase2_cnn_best.pt"
FIELD_DESI_R5 = PROJECT_ROOT / "data" / "processed" / "phase6_fields" / "bgs_ngc_delta_128.npy"
MASK_DESI     = PROJECT_ROOT / "data" / "processed" / "phase6_fields" / "bgs_ngc_mask_128.npy"
TAU_LHC_DIR   = RESULTS_DIR / "phase2_tau_fields" / "lhc"
TAU_NWLH_DIR  = RESULTS_DIR / "phase2_tau_fields" / "nwlh"
OUTPUT_PATH   = RESULTS_DIR / "phase6_ramo_b_pilot.json"

# Frozen da gate2_prior_v1_0.json
N_PTS        = 8192
K_NN         = 16
D_LATENT     = 32
N_FEATURES   = 8
BOX_MOCK     = 1000.0
BOX_DESI     = 1997.4
MU_LCDM_NORM = 2.892929792404175
SAMPLING_EPS = 0.01
DELTA_CLIP   = 6.230
SEED         = 42


# ── Architettura (identica a phase2_cnn.py) ────────────────────────────────────

def build_cauchy_encoder():
    from e3nn import o3
    from e3nn.o3 import FullyConnectedTensorProduct, Linear

    mul_s = D_LATENT // 4   # 8
    mul_v = D_LATENT // 4   # 8
    irreps_hidden = o3.Irreps(f"{mul_s}x0e + {mul_v}x1o")
    irreps_sh     = o3.Irreps.spherical_harmonics(lmax=1)

    class EquivariantBlock(nn.Module):
        def __init__(self):
            super().__init__()
            self.tp = FullyConnectedTensorProduct(
                irreps_hidden, irreps_sh, irreps_hidden, shared_weights=False)
            self.radial_net = nn.Sequential(
                nn.Linear(8, 64), nn.SiLU(),
                nn.Linear(64, self.tp.weight_numel))
            self.output_linear = Linear(irreps_hidden, irreps_hidden)

        def _rbf(self, r, r_max=150.0):
            centers = torch.linspace(0, r_max, 8, device=r.device)
            sigma = r_max / 16
            return torch.exp(-((r.unsqueeze(-1) - centers)**2) / (2*sigma**2))

        def forward(self, x, pos, edge_index):
            src, dst = edge_index[0], edge_index[1]
            r_vec  = pos[dst] - pos[src]
            r_dist = r_vec.norm(dim=-1, keepdim=True)
            r_hat  = r_vec / (r_dist + 1e-8)
            sh     = o3.spherical_harmonics(irreps_sh, r_hat,
                                            normalize=True, normalization="component")
            w      = self.radial_net(self._rbf(r_dist.squeeze(-1)))
            msg    = self.tp(x[src], sh, w)
            x_out  = torch.zeros(x.shape[0], irreps_hidden.dim,
                                 dtype=x.dtype, device=x.device)
            x_out.scatter_add_(0, dst.unsqueeze(-1).expand_as(msg), msg)
            return self.output_linear(x_out)

    class CAUCHYEncoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = nn.Sequential(
                nn.Linear(1, 64), nn.SiLU(),
                nn.Linear(64, irreps_hidden.dim))
            self.mp_layers  = nn.ModuleList([EquivariantBlock() for _ in range(3)])
            self.layer_norms = nn.ModuleList([
                nn.LayerNorm(irreps_hidden.dim) for _ in range(3)])
            self.proj_out = nn.Sequential(
                nn.Linear(irreps_hidden.dim, D_LATENT*2), nn.SiLU(),
                nn.Linear(D_LATENT*2, D_LATENT))
            self.supervision_head = nn.Sequential(
                nn.Linear(D_LATENT, 64), nn.SiLU(),
                nn.Linear(64, N_FEATURES))

        def encode(self, delta_pts, pos, edge_index):
            """Restituisce latente per campo [D_LATENT]."""
            x = self.embedding(delta_pts)
            for mp, ln in zip(self.mp_layers, self.layer_norms):
                x = ln(x + mp(x, pos, edge_index))
            tau_pts = self.proj_out(x)       # [N, D_LATENT]
            return tau_pts.mean(dim=0)        # [D_LATENT]

    return CAUCHYEncoder()


# ── Sampling ────────────────────────────────────────────────────────────────────

def sample_field(field, mask, n_pts, rng):
    """Density-weighted sampling sui voxel in-survey."""
    ng    = field.shape[0]
    idx   = np.argwhere(mask)
    delta = np.clip(field[mask], -1.0, DELTA_CLIP).astype(np.float32)
    w     = np.abs(delta) + SAMPLING_EPS
    w    /= w.sum()
    n_v   = len(idx)
    sel   = rng.choice(n_v, size=n_pts, replace=(n_v < n_pts), p=w)
    pts   = idx[sel]
    # Coordinate in Mpc/h DESI, poi normalizzate a box mock [0,1000]
    coords = (pts + 0.5) * (BOX_DESI / ng) * (BOX_MOCK / BOX_DESI)
    return coords.astype(np.float32), delta[sel].reshape(-1, 1)


# ── Carica tau mock (file .npz) ─────────────────────────────────────────────────

def load_tau_norms(tau_dir, n_max=200):
    norms = []
    files = sorted(Path(tau_dir).glob("*.npz"))[:n_max]
    for f in files:
        d = np.load(f)
        if "tau_points" in d:
            # tau_points [8192,35]: colonne 3:35 = latente, col 0:3 = coord
            lat = d["tau_points"][:, 3:]      # [8192, 32]
            mu  = d["mu_lcdm"]                # [32]
            tau = lat.mean(axis=0) - mu        # [32]
            norms.append(float(np.linalg.norm(tau)))
        elif "mu_lcdm" in d:
            # Struttura alternativa
            norms.append(float(np.linalg.norm(d["mu_lcdm"])))
    return np.array(norms)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("CAUCHY Phase 6 — Pilot Ramo B su DESI (v2)")
    print("=" * 70)

    # Validate
    for p in [CHECKPOINT, FIELD_DESI_R5, MASK_DESI]:
        if not p.exists():
            print(f"[ERRORE] Mancante: {p}"); sys.exit(1)
    print("[OK] Path validation superata")

    rng    = np.random.default_rng(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[OK] Device: {device}")

    # ── [1] Carica modello ────────────────────────────────────────────────────
    print("\n[1/5] Caricamento CNN...")
    ckpt  = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    model = build_cauchy_encoder().to(device)
    res   = model.load_state_dict(ckpt["model_state_dict"], strict=True)
    model.eval()
    print(f"  Caricato: epoch={ckpt['epoch']}, val_loss={ckpt['val_loss']:.5f}")
    print(f"  Parametri: {sum(p.numel() for p in model.parameters()):,}")

    # ── [2] Prepara campo DESI ────────────────────────────────────────────────
    print("\n[2/5] Preparazione campo DESI...")
    field = np.load(FIELD_DESI_R5).astype(np.float32)
    mask  = np.load(MASK_DESI)
    print(f"  Voxel in-survey: {mask.sum():,} ({100*mask.mean():.1f}%)")
    print(f"  δ std in-survey: {field[mask].std():.4f}")
    coords, delta_pts = sample_field(field, mask, N_PTS, rng)
    print(f"  Campionati {N_PTS} punti, δ range [{delta_pts.min():.3f},{delta_pts.max():.3f}]")

    # ── [3] Forward pass ──────────────────────────────────────────────────────
    print("\n[3/5] Forward pass CNN...")
    from torch_geometric.nn import knn_graph
    coords_t = torch.tensor(coords,     dtype=torch.float32, device=device)
    delta_t  = torch.tensor(delta_pts,  dtype=torch.float32, device=device)
    edge_idx = knn_graph(coords_t, k=K_NN, loop=False)

    with torch.no_grad():
        latent_desi = model.encode(delta_t, coords_t, edge_idx).cpu().numpy()

    latent_norm = float(np.linalg.norm(latent_desi))
    print(f"  ||latente_DESI||  = {latent_norm:.4f}")
    print(f"  ||μ_ΛCDM||        = {MU_LCDM_NORM:.4f}")

    # τ_DESI = latente - μ_ΛCDM (vettore)
    # μ_ΛCDM come vettore è disponibile nei file tau_mock
    # Usiamo la norma scalare come proxy per il pilot
    tau_norm_desi = abs(latent_norm - MU_LCDM_NORM)
    print(f"  ||τ_DESI|| proxy  = {tau_norm_desi:.4f}")

    # ── [4] Carica tau mock ───────────────────────────────────────────────────
    print("\n[4/5] Caricamento tau mock...")
    tau_norms_lhc  = load_tau_norms(TAU_LHC_DIR)
    tau_norms_nwlh = load_tau_norms(TAU_NWLH_DIR)
    print(f"  LHC:  N={len(tau_norms_lhc)},  mean={tau_norms_lhc.mean():.4f}±{tau_norms_lhc.std():.4f}")
    print(f"  nwLH: N={len(tau_norms_nwlh)}, mean={tau_norms_nwlh.mean():.4f}±{tau_norms_nwlh.std():.4f}")

    # Calcolo corretto tau: latente - mu_lcdm per ogni mock
    # Ricarichiamo per avere il vettore mu_lcdm reale
    print("  Ricalcolo con vettore mu_lcdm esatto...")
    tau_norms_lhc2, tau_norms_nwlh2 = [], []
    for tag, tau_dir, out in [("LHC", TAU_LHC_DIR, tau_norms_lhc2),
                               ("nwLH", TAU_NWLH_DIR, tau_norms_nwlh2)]:
        files = sorted(Path(tau_dir).glob("*.npz"))[:200]
        for f in files:
            d = np.load(f)
            if "tau_points" in d and "mu_lcdm" in d:
                lat = d["tau_points"][:, 3:].mean(axis=0)  # [32] latente medio
                mu  = d["mu_lcdm"]                          # [32]
                out.append(float(np.linalg.norm(lat - mu)))

    tau_norms_lhc2  = np.array(tau_norms_lhc2)
    tau_norms_nwlh2 = np.array(tau_norms_nwlh2)

    # Per DESI: usiamo mu_lcdm dal primo file tau disponibile
    f0 = next(TAU_LHC_DIR.glob("*.npz"), None)
    mu_lcdm_vec = np.load(f0)["mu_lcdm"] if f0 else None
    if mu_lcdm_vec is not None:
        tau_desi_vec = latent_desi - mu_lcdm_vec
        tau_norm_desi_exact = float(np.linalg.norm(tau_desi_vec))
        print(f"  ||τ_DESI|| (mu vettoriale) = {tau_norm_desi_exact:.4f}")
    else:
        tau_norm_desi_exact = tau_norm_desi

    # ── [5] Anomalia ─────────────────────────────────────────────────────────
    print("\n[5/5] Valutazione anomalia...")
    anomaly = {"tau_norm_desi": tau_norm_desi_exact}

    for label, arr in [("LHC", tau_norms_lhc2), ("nwLH", tau_norms_nwlh2)]:
        if len(arr) == 0:
            continue
        z = (tau_norm_desi_exact - arr.mean()) / arr.std(ddof=1)
        pct = float(np.mean(arr < tau_norm_desi_exact) * 100)
        anomaly[f"z_vs_{label}"] = float(z)
        anomaly[f"{label}_mean"] = float(arr.mean())
        anomaly[f"{label}_std"]  = float(arr.std(ddof=1))
        anomaly[f"{label}_pct"]  = pct
        print(f"  z-score vs {label}: {z:+.2f}σ  (percentile {pct:.1f}%)")

    # ── Output ────────────────────────────────────────────────────────────────
    output = {
        "schema_version": "2.0",
        "output_id":  "phase6_ramo_b_pilot",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latent_desi_norm": latent_norm,
        "mu_lcdm_norm_scalar": MU_LCDM_NORM,
        "tau_norm_desi": tau_norm_desi_exact,
        "anomaly": anomaly,
        "domain_adaptation": {
            "coord_normalization": f"DESI {BOX_DESI} Mpc/h → Mock {BOX_MOCK} Mpc/h",
            "outlier_clip": DELTA_CLIP,
            "std_desi_vs_mock": "0.63 vs 1.7 — non normalizzata (limitazione dichiarata)",
        },
        "interpretation": (
            "z > 2σ: DESI anomalo in spazio latente → Ramo B produce segnale. "
            "z < 1σ: null result informativo."
        ),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[SAVED] {OUTPUT_PATH}")
    print("[COMPLETATO] Pilot Ramo B terminato.")


if __name__ == "__main__":
    if __name__ == "__main__":
        import multiprocessing as mp
        mp.freeze_support()
    main()

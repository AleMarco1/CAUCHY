#!/usr/bin/env python3
"""
CAUCHY — Phase 3 GNN Diagnostica
==================================
Carica il checkpoint phase3_gnn_best.pt e diagnostica perché j* ha varianza zero.
Non riesegue il training — usa i grafi già costruiti in memoria tramite resume mode.

Uso:
  python src/phase3_gnn_diagnose.py --repo-root D:/projects/cauchy
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("diagnose")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--n-fields", type=int, default=20, help="Campi da processare per la diagnostica rapida")
    return p.parse_args()


def main():
    args = parse_args()
    repo_root = args.repo_root.resolve()

    import torch
    import torch.nn as nn
    from torch_geometric.nn import GCNConv, global_mean_pool, global_max_pool

    ckpt_path = repo_root / "results" / "checkpoints" / "phase3_gnn_best.pt"
    log.info(f"Caricamento checkpoint: {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    log.info(f"  best_epoch={ckpt['best_epoch']}, val_loss={ckpt['best_val_loss']:.6f}")

    # ── Ricostruisce il modello IDENTICO allo script originale ───────────────
    class CauchyGNN_Original(nn.Module):
        def __init__(self):
            super().__init__()
            self.input_proj = nn.Linear(9, 64)
            self.convs = nn.ModuleList([GCNConv(64, 64), GCNConv(64, 64), GCNConv(64, 32)])
            self.norms = nn.ModuleList([nn.LayerNorm(64), nn.LayerNorm(64)])
            self.j_star_proj = nn.Sequential(nn.Linear(64, 32), nn.ReLU())  # <-- ReLU su j*
            self.output = nn.Linear(32, 2)

        def forward(self, x, edge_index, batch):
            import torch.nn.functional as F
            x = F.relu(self.input_proj(x))
            for i, conv in enumerate(self.convs[:-1]):
                x = conv(x, edge_index)
                x = self.norms[i](x)
                x = F.relu(x)
            x = F.relu(self.convs[-1](x, edge_index))
            x_mean = global_mean_pool(x, batch)
            x_max = global_max_pool(x, batch)
            x_pool = torch.cat([x_mean, x_max], dim=1)
            j_star = self.j_star_proj(x_pool)
            out = self.output(j_star)
            return out, j_star

    model = CauchyGNN_Original()
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    # ── Diagnostica 1: pesi del layer j_star_proj ───────────────────────────
    log.info("\n=== Diagnostica 1: pesi j_star_proj ===")
    W = model.j_star_proj[0].weight.detach().numpy()   # [32, 64]
    b = model.j_star_proj[0].bias.detach().numpy()     # [32]
    log.info(f"  W: shape={W.shape}, mean={W.mean():.4f}, std={W.std():.4f}")
    log.info(f"  b: mean={b.mean():.4f}, std={b.std():.4f}, min={b.min():.4f}")

    # ── Diagnostica 2: pre-ReLU activation su input fittizio ────────────────
    log.info("\n=== Diagnostica 2: pre-ReLU activation su input sintetico ===")
    x_fake = torch.randn(100, 9)
    edge_index_fake = torch.zeros((2, 0), dtype=torch.long)
    batch_fake = torch.zeros(100, dtype=torch.long)

    with torch.no_grad():
        h = torch.relu(model.input_proj(x_fake))
        for i, conv in enumerate(model.convs[:-1]):
            h = conv(h, edge_index_fake)
            h = model.norms[i](h)
            h = torch.relu(h)
        h = torch.relu(model.convs[-1](h, edge_index_fake))

        x_mean = global_mean_pool(h, batch_fake)
        x_max = global_max_pool(h, batch_fake)
        x_pool = torch.cat([x_mean, x_max], dim=1)

        # Pre-ReLU
        pre_relu = model.j_star_proj[0](x_pool)
        log.info(f"  pre-ReLU: mean={pre_relu.mean():.4f}, std={pre_relu.std():.4f}, "
                 f"min={pre_relu.min():.4f}, max={pre_relu.max():.4f}")
        n_negative = (pre_relu < 0).sum().item()
        log.info(f"  Neuroni negativi pre-ReLU: {n_negative}/32 ({n_negative/32*100:.1f}%)")

        # Post-ReLU (j*)
        j_star_fake = torch.relu(pre_relu)
        log.info(f"  j* (post-ReLU): mean={j_star_fake.mean():.4f}, std={j_star_fake.std():.4f}")
        n_zero = (j_star_fake == 0).sum().item()
        log.info(f"  Neuroni zero in j*: {n_zero}/32 ({n_zero/32*100:.1f}%) ← dying ReLU")

    # ── Diagnostica 3: j* reale su N campi tau ──────────────────────────────
    log.info(f"\n=== Diagnostica 3: j* su {args.n_fields} campi reali ===")
    from torch_geometric.data import Data
    from torch_geometric.loader import DataLoader
    import gudhi
    from scipy.spatial import KDTree

    gate2_prior_path = repo_root / "gate2_prior_v1_0.json"
    if not gate2_prior_path.exists():
        gate2_prior_path = repo_root / "prior" / "gate2_prior_v1_0.json"
    with open(gate2_prior_path) as f:
        gate2_prior = json.load(f)

    tau_lhc_dir = repo_root / gate2_prior["frozen_tau_construction"]["tau_lhc_dir"]
    files = sorted(tau_lhc_dir.glob("tau_field_*.npz"))[:args.n_fields]
    persistence_threshold = 0.35589513778686577

    data_list = []
    for npz_path in files:
        data = np.load(npz_path)
        tau_pts = data["tau_points"]
        pos_pts = tau_pts[:, :3]
        latent = tau_pts[:, 3:]
        tau_norm = np.linalg.norm(latent, axis=1)

        if "tau_grid" in data:
            tau_grid = data["tau_grid"].astype(np.float64)
            cc = gudhi.CubicalComplex(dimensions=list(tau_grid.shape), top_dimensional_cells=-tau_grid.ravel())
            cc.compute_persistence()
            pairs = cc.persistence()
        else:
            continue

        node_features = []
        for dim_target in [1, 2]:
            for dim_, (b_val, d_val) in pairs:
                if dim_ != dim_target or np.isinf(d_val): continue
                persistence = abs(b_val - d_val)
                if persistence <= persistence_threshold: continue
                birth_real = -b_val
                region_mask = tau_norm >= max(0.0, birth_real * 0.9)
                if region_mask.sum() == 0: region_mask = tau_norm >= np.percentile(tau_norm, 80)
                region_pos = pos_pts[region_mask]
                region_tau = tau_norm[region_mask]
                weights = region_tau / (region_tau.sum() + 1e-12)
                centroid = (region_pos * weights[:, None]).sum(axis=0) / 1000.0
                feat = np.array([birth_real, -d_val, persistence,
                                 1.0 if dim_target == 1 else 0.0,
                                 1.0 if dim_target == 2 else 0.0,
                                 float(region_tau.mean()),
                                 float(centroid[0]), float(centroid[1]), float(centroid[2])],
                                dtype=np.float32)
                node_features.append(feat)

        if not node_features: continue
        x = np.stack(node_features, axis=0)
        bd = x[:, :2]
        k = min(5, len(x) - 1)
        if k <= 0:
            ei = np.zeros((2, 0), dtype=np.int64)
        else:
            tree = KDTree(bd)
            _, nbrs = tree.query(bd, k=k + 1)
            nbrs = nbrs[:, 1:]
            src = np.repeat(np.arange(len(x)), k)
            dst = nbrs.ravel()
            ei = np.stack([np.concatenate([src, dst]), np.concatenate([dst, src])], axis=0)

        data_list.append(Data(
            x=torch.tensor(x, dtype=torch.float32),
            edge_index=torch.tensor(ei, dtype=torch.long),
            y=torch.zeros(1, 2),
        ))

    if not data_list:
        log.error("Nessun grafo costruito. Verificare il path tau_lhc_dir.")
        sys.exit(1)

    log.info(f"  Grafi costruiti: {len(data_list)}")
    loader = DataLoader(data_list, batch_size=4, shuffle=False)
    all_j = []
    with torch.no_grad():
        for batch in loader:
            _, j = model(batch.x, batch.edge_index, batch.batch)
            all_j.append(j.numpy())
    J = np.concatenate(all_j, axis=0)   # [N, 32]

    log.info(f"  j* shape: {J.shape}")
    log.info(f"  j* mean per campo: {J.mean(axis=1)[:5].round(4)}")
    vars_per_dim = J.var(axis=0)
    n_dead = (vars_per_dim < 1e-8).sum()
    log.info(f"  Varianza per dim — mean={vars_per_dim.mean():.6f}, min={vars_per_dim.min():.8f}")
    log.info(f"  Dimensioni con var < 1e-8 (morte): {n_dead}/32")

    if n_dead == 32:
        log.error("  CONFERMATO: tutte le 32 dimensioni di j* hanno varianza zero.")
        log.error("  Causa: ReLU finale in j_star_proj azzera l'intero output.")
        log.error("  Fix: rimuovere ReLU da j_star_proj nell'architettura GNN.")
    elif n_dead > 0:
        log.warning(f"  {n_dead}/32 dimensioni morte — correlazioni parzialmente recuperabili.")
    else:
        log.info("  j* ha varianza non-zero su tutte le dimensioni. Problema altrove.")

    log.info("\n=== CONCLUSIONE DIAGNOSTICA ===")
    log.info("  Fix da applicare a build_gnn_model in phase3_gnn.py:")
    log.info("    j_star_proj = nn.Linear(2*latent_dim, latent_dim)  # senza ReLU")
    log.info("  Poi rieseguire con --resume-from-checkpoint non funziona (architettura diversa).")
    log.info("  Necessario: rifare training con architettura corretta.")


if __name__ == "__main__":
    main()

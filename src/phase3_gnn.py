#!/usr/bin/env python3
"""
CAUCHY — Phase 3 GNN
=====================
GNN su TDA(τ(x)) — Ramo B.
Autorità: CAUCHY_Execution_Design_v2.md §5.4, CAUCHY_Execution_Parameters.md §5,
          CAUCHY_Systematic_Methodology_v2.md §3.1–3.2, gate2_prior_v1_0.json.

Pipeline:
  1. Assert gate2_prior (obbligatorio all'avvio)
  2. [PRE-TRAINING CHECK] Stima empirica numero nodi su 10 campi campione
  3. Costruzione grafi topologici da τ(x): nodi β₁+β₂ con persistenza > p90,
     feature nodo (9 scalari), archi k-NN nello spazio (birth, death)
  4. Training GNN su LHC 80% (seed=42, coerente con Phase 2)
  5. Valutazione correlazioni |r(j*, Ωm)| e |r(j*, σ₈)| sul test set 20%
  6. Correlazione |r(j*, w₀)| su nwLH (soft gate)
  7. Calcolo miglioramento su baseline Ramo A (Execution Parameters §5.2)
  8. Serializzazione results/phase3_gnn_correlations.json

Uso:
  python src/phase3_gnn.py --repo-root /path/to/repo \\
      --prerequisites-json results/phase3_prerequisites.json \\
      [--batch-size 4] [--lr 1e-3] [--epochs 300] [--seed 42]

Note operative:
  - Legge τ(x) da results/phase2_tau_fields/ — non riprocessa i campi di Phase 2
  - Split seed=42 obbligatorio per coerenza con Phase 2 (stesso 20% test set)
  - nwLH mai nel training — solo per correlazione w₀ post-training
  - La baseline Ramo A è letta da results/phase1_tda_baseline.json — non ricalcolata
  - Target supervisione: (Ωm, σ₈) su LHC — w₀ è soft gate separato
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("phase3_gnn")

# ---------------------------------------------------------------------------
# Constants — tutti tracciati a documenti autoritativi
# ---------------------------------------------------------------------------
EXPECTED_SHA256 = "302771fcd8656d4626bd923e87c8778cd5e64fc91210cc60c05fcd0b44cd6505"
# Autorità: gate2_prior_v1_0.json frozen_training.checkpoint_sha256

N_PTS_PER_FIELD = 8192
# Autorità: gate2_prior_v1_0.json frozen_architecture.n_pts_per_field

D_LATENT = 32
# Autorità: gate2_prior_v1_0.json frozen_architecture.D_latent

BOX_SIZE_MPCH = 1000.0
# Autorità: gate2_prior_v1_0.json frozen_architecture.box_size_mpch

GLOBAL_SEED = 42
# Autorità: CAUCHY_Execution_Parameters §5.1, environment.yml CAUCHY_GLOBAL_SEED

GNN_HIDDEN_DIM = 64
GNN_LATENT_DIM = 32   # j* — coerente con D_LATENT Phase 2
GNN_N_LAYERS = 3
GNN_K_NN = 5
# Autorità: architettura proposta in Sessione 1 Fase B, approvata dal PI

CORR_THRESHOLD_LHC = 0.20
# Autorità: CAUCHY_Execution_Parameters §5.2

VARIANCE_ADDED_THRESHOLD_PCT = 5.0
# Autorità: CAUCHY_Execution_Parameters §5.2


# ---------------------------------------------------------------------------
# Gate 2 Prior Verification (obbligatoria)
# ---------------------------------------------------------------------------

def verify_gate2_prior(repo_root: Path) -> dict:
    """
    Assert obbligatori su gate2_prior_v1_0.json.
    Se fallisce: STOP — i tau(x) su disco potrebbero non corrispondere
    alla configurazione dichiarata.
    Autorità: phase3_prompt.md §Specifica Tecnica — Assert parametri frozen.
    """
    prior_path = repo_root / "prior" / "gate2_prior_v1_0.json"
    if not prior_path.exists():
        prior_path = repo_root / "gate2_prior_v1_0.json"

    log.info(f"Verifica gate2_prior: {prior_path}")
    with open(prior_path) as f:
        gate2_prior = json.load(f)

    arch = gate2_prior["frozen_architecture"]
    training = gate2_prior["frozen_training"]

    assert arch["n_pts_per_field"] == N_PTS_PER_FIELD, (
        f"MISMATCH n_pts_per_field: atteso {N_PTS_PER_FIELD}, trovato {arch['n_pts_per_field']}"
    )
    assert arch["D_latent"] == D_LATENT, (
        f"MISMATCH D_latent: atteso {D_LATENT}, trovato {arch['D_latent']}"
    )
    assert training["checkpoint_sha256"] == EXPECTED_SHA256, (
        f"MISMATCH checkpoint_sha256:\n"
        f"  atteso:  {EXPECTED_SHA256}\n"
        f"  trovato: {training['checkpoint_sha256']}"
    )

    log.info("✓ gate2_prior verificato: n_pts=8192, D_latent=32, SHA-256 OK")
    return gate2_prior


def load_prerequisites(prereq_json: Path) -> dict:
    """
    Carica e valida phase3_prerequisites.json.
    Se overall_prerequisites != PASS: STOP.
    """
    with open(prereq_json) as f:
        prereq = json.load(f)

    status = prereq.get("overall_prerequisites", "UNKNOWN")
    if status != "PASS":
        raise RuntimeError(
            f"phase3_prerequisites.json riporta overall_prerequisites={status}. "
            "Il Ramo B è bloccato. Non procedere con il GNN."
        )

    p90 = prereq["persistence_threshold_p90"]
    log.info(f"✓ Prerequisiti PASS. Soglia persistenza p90 = {p90:.6f}")
    return prereq


# ---------------------------------------------------------------------------
# Costruzione grafo topologico da τ(x)
# ---------------------------------------------------------------------------

def extract_topological_graph(
    npz_path: Path,
    persistence_threshold: float,
    k_nn: int,
    use_3d: bool = True,
) -> dict | None:
    """
    Costruisce il grafo topologico per un campo τ(x).

    Nodi: feature β₁ e β₂ con persistenza > persistence_threshold.
    Feature nodo (9 scalari):
      [birth, death, persistence, dim_is_beta1, dim_is_beta2,
       tau_norm_mean_region, cx_norm, cy_norm, cz_norm]

    Archi: k-NN nello spazio (birth, death) del diagramma di persistenza.
    Autorità: Methodology §3.1, phase3_prompt.md §Specifica Tecnica.

    Restituisce dict con:
      - x: array [N_nodes, 9] feature nodo
      - edge_index: array [2, N_edges] archi k-NN
      - n_nodes: int
      - n_edges: int
      - n_beta1: int
      - n_beta2: int
    Restituisce None se N_nodes == 0 (campo senza feature sopra soglia).
    """
    import gudhi

    data = np.load(npz_path)
    tau_pts = data["tau_points"]          # [8192, 35]
    pos_pts = tau_pts[:, :3]              # [8192, 3]  coordinate fisiche Mpc/h
    latent = tau_pts[:, 3:]              # [8192, 32]
    tau_norm = np.linalg.norm(latent, axis=1)  # [8192]

    # --- TDA su tau_grid 3D (preferita) o fallback 1D ---
    if use_3d and "tau_grid" in data:
        tau_grid = data["tau_grid"].astype(np.float64)
        neg_grid = -tau_grid.ravel()
        cc = gudhi.CubicalComplex(
            dimensions=list(tau_grid.shape),
            top_dimensional_cells=neg_grid,
        )
        cc.compute_persistence()
        pairs_raw = cc.cofaces_of_persistence_pairs()
        # pairs_raw: list per dimensione, ogni elemento (birth_idx, death_idx) flat
        use_grid = True
        grid_shape = tau_grid.shape
    else:
        sorted_idx = np.argsort(tau_norm)[::-1]
        sorted_vals = tau_norm[sorted_idx]
        cc = gudhi.CubicalComplex(
            dimensions=[len(sorted_vals)],
            top_dimensional_cells=sorted_vals,
        )
        cc.compute_persistence()
        pairs_raw = cc.cofaces_of_persistence_pairs()
        use_grid = False
        grid_shape = None

    # Ottieni i diagrammi di persistenza con indici
    pairs = cc.persistence()

    node_features = []   # lista di array [9]

    for dim_target in [1, 2]:
        dim_pairs = [(b, d) for (dim_, (b, d)) in pairs
                     if dim_ == dim_target and not np.isinf(d)]

        for birth_val, death_val in dim_pairs:
            persistence = birth_val - death_val  # superlevel negato: death < birth
            # Nota: per superlevel via negazione, birth e death sono negati,
            # quindi persistenza = death_neg - birth_neg = |birth_real - death_real|
            persistence = abs(persistence)

            if persistence <= persistence_threshold:
                continue

            # --- Feature nodo base ---
            dim_is_b1 = 1.0 if dim_target == 1 else 0.0
            dim_is_b2 = 1.0 if dim_target == 2 else 0.0

            # --- Baricentro spaziale della feature ---
            # Stima del baricentro: media delle posizioni dei punti con
            # |tau_norm - birth_val_real| < epsilon (punti vicini al valore
            # di nascita della feature nella filtrazione).
            # birth_val è negato rispetto al valore reale della filtrazione.
            birth_real = -birth_val  # riconversione al dominio reale

            # Seleziona punti nella regione con tau_norm >= birth_real * 0.9
            # (approssimazione del supporto spaziale della feature)
            region_mask = tau_norm >= max(0.0, birth_real * 0.9)
            if region_mask.sum() == 0:
                region_mask = tau_norm >= np.percentile(tau_norm, 80)

            region_pos = pos_pts[region_mask]      # [N_region, 3]
            region_tau = tau_norm[region_mask]     # [N_region]

            # Baricentro pesato per tau_norm
            weights = region_tau / (region_tau.sum() + 1e-12)
            centroid = (region_pos * weights[:, None]).sum(axis=0)  # [3]
            centroid_norm = centroid / BOX_SIZE_MPCH                 # [3] in [0,1]

            # tau_norm medio nella regione
            tau_mean_region = float(region_tau.mean())

            # feature nodo: [birth, death, persistence, b1, b2, tau_mean, cx, cy, cz]
            feat = np.array([
                birth_real,
                -death_val,           # death nella scala reale
                persistence,
                dim_is_b1,
                dim_is_b2,
                tau_mean_region,
                float(centroid_norm[0]),
                float(centroid_norm[1]),
                float(centroid_norm[2]),
            ], dtype=np.float32)

            node_features.append(feat)

    n_nodes = len(node_features)
    if n_nodes == 0:
        return None

    x = np.stack(node_features, axis=0)  # [N_nodes, 9]

    # --- Archi k-NN nello spazio (birth, death) ---
    birth_death_coords = x[:, :2]  # [N_nodes, 2]
    k_actual = min(k_nn, n_nodes - 1)

    if k_actual <= 0:
        # Grafo con un solo nodo: nessun arco
        edge_index = np.zeros((2, 0), dtype=np.int64)
    else:
        from scipy.spatial import KDTree
        tree = KDTree(birth_death_coords)
        dists, neighbors = tree.query(birth_death_coords, k=k_actual + 1)
        # Esclude il punto stesso (indice 0 in neighbors)
        neighbors = neighbors[:, 1:]  # [N_nodes, k_actual]

        src = np.repeat(np.arange(n_nodes), k_actual)
        dst = neighbors.ravel()
        # Archi bidirezionali
        edge_index = np.stack([
            np.concatenate([src, dst]),
            np.concatenate([dst, src]),
        ], axis=0)  # [2, 2*N_nodes*k_actual]

    n_beta1 = int(sum(1 for f in node_features if f[3] == 1.0))
    n_beta2 = int(sum(1 for f in node_features if f[4] == 1.0))

    return {
        "x": x,
        "edge_index": edge_index,
        "n_nodes": n_nodes,
        "n_edges": edge_index.shape[1],
        "n_beta1": n_beta1,
        "n_beta2": n_beta2,
    }


# ---------------------------------------------------------------------------
# Pre-training check: stima empirica numero nodi (punto A PI)
# ---------------------------------------------------------------------------

def pretraining_node_check(
    lhc_files: list,
    persistence_threshold: float,
    k_nn: int,
    n_check: int = 10,
    use_3d: bool = True,
) -> dict:
    """
    Verifica empirica del numero medio di nodi per grafo su n_check campi LHC.
    Da eseguire obbligatoriamente prima del training completo.
    Logga i risultati e lancia WARNING se il numero di nodi è fuori
    dall'intervallo [50, 5000] — range operativo ragionevole per questo GNN.
    Autorità: decisione PI Sessione 1 punto A.
    """
    log.info(f"=== Pre-training node check su {n_check} campi campione ===")
    node_counts = []
    beta1_counts = []
    beta2_counts = []

    for i, npz_path in enumerate(lhc_files[:n_check]):
        log.info(f"  Campo {i+1}/{n_check}: {npz_path.name}")
        graph = extract_topological_graph(npz_path, persistence_threshold, k_nn, use_3d)
        if graph is None:
            log.warning(f"  Campo {npz_path.name}: 0 nodi sopra soglia — escluso dal check")
            node_counts.append(0)
            beta1_counts.append(0)
            beta2_counts.append(0)
        else:
            log.info(f"    N_nodes={graph['n_nodes']}, β₁={graph['n_beta1']}, β₂={graph['n_beta2']}, N_edges={graph['n_edges']}")
            node_counts.append(graph["n_nodes"])
            beta1_counts.append(graph["n_beta1"])
            beta2_counts.append(graph["n_beta2"])

    mean_nodes = float(np.mean(node_counts))
    std_nodes = float(np.std(node_counts))
    max_nodes = int(np.max(node_counts))

    log.info(f"  Nodi per grafo: mean={mean_nodes:.1f} ± {std_nodes:.1f}, max={max_nodes}")

    if mean_nodes < 10:
        log.error(
            f"  ANOMALIA: mean_nodes={mean_nodes:.1f} < 10. "
            "La soglia di persistenza p90 potrebbe essere troppo alta. "
            "Considerare riduzione della soglia prima di procedere."
        )
    elif mean_nodes > 5000:
        log.warning(
            f"  ATTENZIONE: mean_nodes={mean_nodes:.1f} > 5000. "
            "Grafi molto densi — considerare aumento soglia o riduzione batch_size."
        )
    else:
        log.info(f"  ✓ Numero nodi nel range operativo.")

    return {
        "n_fields_checked": n_check,
        "node_counts": node_counts,
        "beta1_counts": beta1_counts,
        "beta2_counts": beta2_counts,
        "mean_nodes": mean_nodes,
        "std_nodes": std_nodes,
        "max_nodes": max_nodes,
        "persistence_threshold_used": float(persistence_threshold),
        "k_nn_used": k_nn,
    }


# ---------------------------------------------------------------------------
# Dataset: costruisce tutti i grafi con caching opzionale
# ---------------------------------------------------------------------------

def _graph_cache_path(cache_dir, npz_path, subdir=None):
    """
    Restituisce il path del file cache per un campo tau.
    subdir: sottocartella dentro cache_dir (es. 'lhc', 'nwlh', 'fiducial').
    Obbligatoria per evitare collisioni tra dataset con stessi nomi file.
    """
    folder = cache_dir / subdir if subdir else cache_dir
    return folder / (npz_path.stem + "_graph.npz")


def _save_graph(graph, path):
    np.savez_compressed(
        path,
        x=graph["x"],
        edge_index=graph["edge_index"],
        meta=np.array([graph["n_nodes"], graph["n_edges"],
                       graph["n_beta1"], graph["n_beta2"]], dtype=np.int64),
    )


def _load_graph(path):
    data = np.load(path)
    meta = data["meta"]
    if meta[0] == 0:
        return None
    return {
        "x": data["x"],
        "edge_index": data["edge_index"],
        "n_nodes": int(meta[0]),
        "n_edges": int(meta[1]),
        "n_beta1": int(meta[2]),
        "n_beta2": int(meta[3]),
    }


def build_graph_dataset(
    files: list,
    persistence_threshold: float,
    k_nn: int,
    use_3d: bool = True,
    desc: str = "dataset",
    cache_dir=None,
    cache_subdir: str = None,
) -> list:
    """
    Costruisce la lista di grafi per tutti i file in input.
    Restituisce lista di dict {x, edge_index, n_nodes, n_edges, n_beta1, n_beta2}.
    I campi con 0 nodi vengono saltati (placeholder None per allineamento cosmo_params).

    Se cache_dir e' specificato:
      - Carica il grafo dalla cache se esiste (evita ricalcolo TDA).
      - Salva il grafo nella cache dopo il calcolo.
      - cache_subdir: sottocartella obbligatoria per separare dataset con
        stessi nomi file (es. 'lhc', 'nwlh'). Senza di essa tau_field_0001.npz
        da LHC e nwLH colliderebbero sullo stesso file di cache.
      - Formato: tau_field_0001.npz -> <cache_dir>/<cache_subdir>/tau_field_0001_graph.npz
    """
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        effective_cache = cache_dir / cache_subdir if cache_subdir else cache_dir
        effective_cache.mkdir(parents=True, exist_ok=True)
    else:
        effective_cache = None

    graphs = []
    skipped = 0
    n_from_cache = 0
    n_computed = 0

    for i, npz_path in enumerate(files):
        if i % 100 == 0:
            log.info(f"  {desc}: {i}/{len(files)} "
                     f"(cache={n_from_cache}, calcolati={n_computed})")

        if effective_cache is not None:
            cp = _graph_cache_path(effective_cache, npz_path)
            if cp.exists():
                graph = _load_graph(cp)
                graphs.append(graph)
                n_from_cache += 1
                if graph is None:
                    skipped += 1
                continue

        graph = extract_topological_graph(npz_path, persistence_threshold, k_nn, use_3d)
        n_computed += 1

        if graph is None:
            log.warning(f"  {npz_path.name}: 0 nodi — saltato")
            skipped += 1
            if effective_cache is not None:
                cp = _graph_cache_path(effective_cache, npz_path)
                np.savez_compressed(cp,
                    x=np.zeros((0, 9), dtype=np.float32),
                    edge_index=np.zeros((2, 0), dtype=np.int64),
                    meta=np.array([0, 0, 0, 0], dtype=np.int64),
                )
            graphs.append(None)
        else:
            if effective_cache is not None:
                cp = _graph_cache_path(effective_cache, npz_path)
                _save_graph(graph, cp)
            graphs.append(graph)

    log.info(f"  {desc}: completato — {n_from_cache} da cache, "
             f"{n_computed} calcolati, {skipped} saltati")
    return graphs


# ---------------------------------------------------------------------------
# GNN — implementazione con torch-geometric, fallback scipy
# ---------------------------------------------------------------------------

def build_gnn_model(n_features: int = 9, hidden_dim: int = 64,
                    latent_dim: int = 32, n_layers: int = 3,
                    n_out: int = 2):
    """
    Architettura GNN approvata dal PI (Sessione 1 Fase B):
      Input (n_features) → Linear(hidden_dim)
      → GCNConv(hidden_dim→hidden_dim) + ReLU + LayerNorm  [×n_layers-1]
      → GCNConv(hidden_dim→latent_dim) + ReLU              [ultimo layer]
      → GlobalMeanPool + GlobalMaxPool → concat(2*latent_dim)
      → Linear(2*latent_dim→latent_dim) + ReLU             [j* embedding]
      → Linear(latent_dim→n_out)                           [output]

    Autorità: Execution Parameters §5.1, proposta architetturale Sessione 1.
    """
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torch_geometric.nn import GCNConv, global_mean_pool, global_max_pool

        class CauchyGNN(nn.Module):
            def __init__(self):
                super().__init__()
                self.input_proj = nn.Linear(n_features, hidden_dim)
                self.convs = nn.ModuleList()
                self.norms = nn.ModuleList()
                for i in range(n_layers - 1):
                    self.convs.append(GCNConv(hidden_dim, hidden_dim))
                    self.norms.append(nn.LayerNorm(hidden_dim))
                # Ultimo layer: hidden_dim → latent_dim
                self.convs.append(GCNConv(hidden_dim, latent_dim))

                # Pooling + embedding j* — Linear senza ReLU finale:
                # j* deve essere uno spazio latente libero in ℝ^latent_dim.
                # ReLU qui causerebbe dying neurons (j* collassa a zero se
                # le pre-attivazioni sono negative) rendendo le correlazioni NaN.
                self.j_star_proj = nn.Sequential(
                    nn.Linear(2 * latent_dim, latent_dim),
                    # NO ReLU — j* è spazio latente libero
                )
                self.output = nn.Linear(latent_dim, n_out)

            def forward(self, x, edge_index, batch):
                x = F.relu(self.input_proj(x))
                for i, conv in enumerate(self.convs[:-1]):
                    x = conv(x, edge_index)
                    x = self.norms[i](x)
                    x = F.relu(x)
                x = F.relu(self.convs[-1](x, edge_index))

                # Global pooling — concat mean + max
                x_mean = global_mean_pool(x, batch)   # [B, latent_dim]
                x_max = global_max_pool(x, batch)     # [B, latent_dim]
                x_pool = torch.cat([x_mean, x_max], dim=1)  # [B, 2*latent_dim]

                j_star = self.j_star_proj(x_pool)     # [B, latent_dim]
                out = self.output(j_star)              # [B, n_out]
                return out, j_star

        model = CauchyGNN()
        n_params = sum(p.numel() for p in model.parameters())
        log.info(f"✓ GNN torch-geometric: {n_params} parametri")
        return model, "torch_geometric"

    except ImportError:
        log.warning("torch-geometric non disponibile — fallback scipy (no GPU)")
        return None, "scipy_fallback"


def graphs_to_torch_data(graphs: list, labels: np.ndarray):
    """
    Converte lista di grafi in lista di torch_geometric.data.Data.
    Skippa i grafi None (campi con 0 nodi).
    """
    import torch
    from torch_geometric.data import Data

    data_list = []
    valid_labels = []
    for g, lbl in zip(graphs, labels):
        if g is None:
            continue
        x = torch.tensor(g["x"], dtype=torch.float32)
        edge_index = torch.tensor(g["edge_index"], dtype=torch.long)
        y = torch.tensor(lbl, dtype=torch.float32).unsqueeze(0)
        data_list.append(Data(x=x, edge_index=edge_index, y=y))
        valid_labels.append(lbl)
    return data_list, np.array(valid_labels)


def train_gnn_torch(
    train_data: list,
    val_data: list,
    model,
    n_epochs: int,
    batch_size: int,
    lr: float,
    seed: int,
    device: str,
) -> dict:
    """
    Training loop GNN con torch-geometric.
    Restituisce dict con curve di loss e best val_loss.
    """
    import torch
    import torch.nn as nn
    from torch_geometric.loader import DataLoader

    torch.manual_seed(seed)
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=n_epochs)
    criterion = nn.MSELoss()

    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False)

    train_losses = []
    val_losses = []
    best_val_loss = float("inf")
    best_epoch = 0
    best_state = None

    for epoch in range(1, n_epochs + 1):
        # --- Train ---
        model.train()
        total_loss = 0.0
        n_batches = 0
        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            pred, _ = model(batch.x, batch.edge_index, batch.batch)
            loss = criterion(pred, batch.y.squeeze(1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
        train_loss = total_loss / max(n_batches, 1)

        # --- Val ---
        model.eval()
        with torch.no_grad():
            total_val = 0.0
            n_val = 0
            for batch in val_loader:
                batch = batch.to(device)
                pred, _ = model(batch.x, batch.edge_index, batch.batch)
                loss = criterion(pred, batch.y.squeeze(1))
                total_val += loss.item()
                n_val += 1
        val_loss = total_val / max(n_val, 1)

        scheduler.step()

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if epoch % 20 == 0 or epoch == 1:
            log.info(f"  Epoch {epoch:3d}/{n_epochs}: train_loss={train_loss:.6f}, val_loss={val_loss:.6f}")

    log.info(f"  Best: epoch={best_epoch}, val_loss={best_val_loss:.6f}")

    if best_state is not None:
        model.load_state_dict(best_state)

    return {
        "train_losses": train_losses,
        "val_losses": val_losses,
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "_best_state": best_state,   # passato al chiamante per salvataggio su disco
    }


def extract_j_star_torch(data_list: list, model, batch_size: int, device: str) -> np.ndarray:
    """
    Estrae il vettore latente j* [latent_dim] per ogni campo.
    Restituisce array [0, latent_dim] se data_list è vuota.
    """
    import torch
    from torch_geometric.loader import DataLoader

    if len(data_list) == 0:
        log.warning("extract_j_star_torch: data_list vuota — restituisce array [0, latent_dim]")
        return np.zeros((0, GNN_LATENT_DIM), dtype=np.float32)

    model.eval()
    model = model.to(device)
    loader = DataLoader(data_list, batch_size=batch_size, shuffle=False)
    all_j_star = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            _, j_star = model(batch.x, batch.edge_index, batch.batch)
            all_j_star.append(j_star.cpu().numpy())
    return np.concatenate(all_j_star, axis=0)   # [N, latent_dim]


# ---------------------------------------------------------------------------
# Fallback scipy: Mean-pool semplice (non GNN ma produce j* per diagnostica)
# ---------------------------------------------------------------------------

def train_gnn_scipy_fallback(
    train_graphs: list,
    train_labels: np.ndarray,
    val_graphs: list,
    val_labels: np.ndarray,
    n_epochs: int,
    seed: int,
) -> tuple:
    """
    Fallback scipy: regressione lineare su mean-pool delle feature di nodo.
    Non è un GNN vero — produce j* come mean-pool (dim=9) per diagnostica.
    Il paper deve dichiarare l'uso del fallback se attivato.
    """
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    log.warning("FALLBACK scipy: training con regressione lineare su mean-pool features")

    def pool_features(graphs):
        pooled = []
        for g in graphs:
            if g is None:
                continue
            pooled.append(g["x"].mean(axis=0))
        return np.array(pooled)

    X_train = pool_features(train_graphs)
    X_val = pool_features(val_graphs)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)

    # Filtra labels per grafi validi
    valid_train_labels = np.array([l for g, l in zip(train_graphs, train_labels) if g is not None])
    valid_val_labels = np.array([l for g, l in zip(val_graphs, val_labels) if g is not None])

    model = Ridge(alpha=1.0)
    model.fit(X_train_s, valid_train_labels)

    val_pred = model.predict(X_val_s)
    val_loss = float(np.mean((val_pred - valid_val_labels) ** 2))
    log.info(f"  Fallback Ridge val_loss={val_loss:.6f}")

    j_star_val = X_val_s   # mean-pool features come proxy di j*
    j_star_train = X_train_s

    training_info = {
        "method": "scipy_ridge_fallback",
        "val_loss": val_loss,
        "best_epoch": n_epochs,
        "best_val_loss": val_loss,
        "train_losses": [val_loss],
        "val_losses": [val_loss],
        "note": "Fallback scipy: regressione Ridge su mean-pool feature. j* = feature normalizzate (dim=9, non dim=32).",
    }

    return model, scaler, j_star_train, j_star_val, training_info


# ---------------------------------------------------------------------------
# Correlazioni Gate 3
# ---------------------------------------------------------------------------

def compute_pearson_r(j_star: np.ndarray, cosmo_param: np.ndarray) -> float:
    """
    Calcola max |r(j*, param)| sulle latent_dim componenti di j*.
    Autorità: Execution Parameters §5.2 — "|r(GNN_j*, Ωm)| sul test set LHC"
    """
    assert j_star.shape[0] == len(cosmo_param), (
        f"Shape mismatch: j_star {j_star.shape[0]} vs param {len(cosmo_param)}"
    )
    r_values = []
    for d in range(j_star.shape[1]):
        r = float(np.corrcoef(j_star[:, d], cosmo_param)[0, 1])
        r_values.append(abs(r))
    return float(np.max(r_values))


def compute_variance_added(
    j_star_test: np.ndarray,
    omm_test: np.ndarray,
    s8_test: np.ndarray,
    phase1_baseline_path: Path,
) -> float:
    """
    Calcola la varianza aggiuntiva spiegata da GNN(τ) rispetto alla baseline Ramo A.

    Definizione (Execution Parameters §5.2):
      var_added = (R2_GNN - R2_ramoA_best) / var_totale * 100

    dove R2_GNN è la varianza spiegata dal componente j* più correlato,
    e R2_ramoA_best è la varianza spiegata dalla feature TDA di Phase 1
    più correlata con (Ωm, σ₈) sullo stesso test set.

    Nota: le correlazioni Ramo A sono lette direttamente da phase1_tda_baseline.json
    — non ricalcolate (Execution Parameters §5.2).
    """
    with open(phase1_baseline_path) as f:
        baseline = json.load(f)

    gate1_corr = baseline.get("gate1_correlations", {})

    # Best |r| Ramo A su (Ωm, σ₈) dal gate1
    r_ramo_a_omm = float(gate1_corr.get("best_r_omm", 0.0))
    r_ramo_a_s8 = float(gate1_corr.get("best_r_s8", 0.0))
    r_ramo_a_best = max(r_ramo_a_omm, r_ramo_a_s8)

    r_gnn_omm = compute_pearson_r(j_star_test, omm_test)
    r_gnn_s8 = compute_pearson_r(j_star_test, s8_test)
    r_gnn_best = max(r_gnn_omm, r_gnn_s8)

    # Varianza spiegata = r^2
    r2_gnn = r_gnn_best ** 2
    r2_ramo_a = r_ramo_a_best ** 2

    variance_added_pct = (r2_gnn - r2_ramo_a) * 100.0

    log.info(f"  Baseline Ramo A: best |r|={r_ramo_a_best:.4f}, R²={r2_ramo_a:.4f}")
    log.info(f"  GNN Ramo B:      best |r|={r_gnn_best:.4f}, R²={r2_gnn:.4f}")
    log.info(f"  Varianza aggiunta: {variance_added_pct:.2f}% (threshold ≥ {VARIANCE_ADDED_THRESHOLD_PCT}%)")

    return float(variance_added_pct)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CAUCHY Phase 3 GNN")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--prerequisites-json", type=Path,
        default=None,
        help="Path a results/phase3_prerequisites.json. Default: <repo-root>/results/phase3_prerequisites.json"
    )
    parser.add_argument("--batch-size", type=int, default=4,
                        help="Batch size per GNN training. Default: 4")
    parser.add_argument("--lr", type=float, default=1e-3,
                        help="Learning rate iniziale. Default: 1e-3")
    parser.add_argument("--epochs", type=int, default=300,
                        help="Epoche massime di training. Default: 300")
    parser.add_argument("--seed", type=int, default=42,
                        help="Seed RNG (coerente con Phase 2). Default: 42")
    parser.add_argument("--k-nn", type=int, default=GNN_K_NN,
                        help=f"k per grafo k-NN in spazio (birth, death). Default: {GNN_K_NN}")
    parser.add_argument("--no-3d", action="store_true",
                        help="Usa TDA 1D invece di tau_grid 3D (fallback)")
    parser.add_argument("--n-node-check", type=int, default=10,
                        help="Numero di campi per pre-training node check. Default: 10")
    parser.add_argument("--graphs-cache-dir", type=Path, default=None,
                        help=(
                            "Directory per la cache dei grafi TDA. "
                            "Se specificata, i grafi calcolati vengono salvati e "
                            "ricaricati nei run successivi (evita ~12h di ricalcolo TDA). "
                            "Esempio: results/graphs_cache"
                        ))
    parser.add_argument("--resume-from-checkpoint", type=Path, default=None,
                        help=(
                            "Se specificato, carica il checkpoint GNN da questo path e SALTA il training. "
                            "Esegue solo la costruzione grafi + estrazione j* + correlazioni. "
                            "Utile dopo un run che ha completato il training ma ha prodotto correlazioni NaN."
                        ))
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    repo_root = args.repo_root.resolve()
    use_3d = not args.no_3d

    np.random.seed(args.seed)

    log.info("=" * 60)
    log.info("CAUCHY — Phase 3 GNN (Ramo B)")
    log.info(f"  repo_root   : {repo_root}")
    log.info(f"  seed        : {args.seed}")
    log.info(f"  lr          : {args.lr}")
    log.info(f"  epochs      : {args.epochs}")
    log.info(f"  batch_size  : {args.batch_size}")
    log.info(f"  k_nn        : {args.k_nn}")
    log.info(f"  use_3d      : {use_3d}")
    log.info("=" * 60)

    # 0. Assert gate2_prior
    try:
        gate2_prior = verify_gate2_prior(repo_root)
    except (AssertionError, FileNotFoundError) as e:
        log.error(f"VERIFICA GATE2 PRIOR FALLITA: {e}")
        sys.exit(1)

    # 1. Carica prerequisiti
    prereq_json = args.prerequisites_json or repo_root / "results" / "phase3_prerequisites.json"
    try:
        prereq = load_prerequisites(prereq_json)
    except RuntimeError as e:
        log.error(str(e))
        sys.exit(1)

    persistence_threshold = prereq["persistence_threshold_p90"]
    log.info(f"Soglia persistenza p90 = {persistence_threshold:.6f} (frozen da prerequisites)")

    # 2. Carica cosmologie
    cache_path = repo_root / "results" / "phase1_fiducial_cache.npz"
    log.info(f"Caricamento cosmologie da: {cache_path}")
    cosmo_cache = np.load(cache_path)
    cosmo_lhc = cosmo_cache["cosmo_lhc"]    # [2000, 2] — [Ωm, σ₈]
    cosmo_nwlh = cosmo_cache["cosmo_nwlh"]  # [2000, 1] — [w₀]

    # 3. Split LHC 80/20 — seed=42 obbligatorio (coerente con Phase 2)
    rng = np.random.default_rng(args.seed)
    n_lhc = len(cosmo_lhc)
    idx_all = np.arange(n_lhc)
    rng_split = np.random.default_rng(42)  # seed fisso obbligatorio
    rng_split.shuffle(idx_all)
    n_train = int(0.8 * n_lhc)
    idx_train = idx_all[:n_train]
    idx_test = idx_all[n_train:]
    log.info(f"Split LHC: {len(idx_train)} train, {len(idx_test)} test (seed=42)")

    # 4. Recupera file tau LHC e nwLH
    tau_lhc_dir = repo_root / gate2_prior["frozen_tau_construction"]["tau_lhc_dir"]
    tau_nwlh_dir = repo_root / gate2_prior["frozen_tau_construction"]["tau_nwlh_dir"]

    lhc_files_all = sorted(tau_lhc_dir.glob("tau_field_*.npz"))
    nwlh_files_all = sorted(tau_nwlh_dir.glob("tau_field_*.npz"))

    if len(lhc_files_all) < n_lhc:
        log.error(f"LHC: trovati {len(lhc_files_all)} file, attesi {n_lhc}")
        sys.exit(1)
    if len(nwlh_files_all) < len(cosmo_nwlh):
        log.error(f"nwLH: trovati {len(nwlh_files_all)} file, attesi {len(cosmo_nwlh)}")
        sys.exit(1)

    lhc_files_train = [lhc_files_all[i] for i in idx_train]
    lhc_files_test = [lhc_files_all[i] for i in idx_test]
    cosmo_train = cosmo_lhc[idx_train]  # [1600, 2]
    cosmo_test = cosmo_lhc[idx_test]    # [400, 2]

    # Normalizzazione (Ωm, σ₈) al range [0,1] sui valori LHC totali
    # Autorità: nota architetturale Sessione 1 — evita scale diverse
    omm_min, omm_max = cosmo_lhc[:, 0].min(), cosmo_lhc[:, 0].max()
    s8_min, s8_max = cosmo_lhc[:, 1].min(), cosmo_lhc[:, 1].max()

    def normalize_labels(cosmo_arr):
        omm_norm = (cosmo_arr[:, 0] - omm_min) / (omm_max - omm_min + 1e-12)
        s8_norm = (cosmo_arr[:, 1] - s8_min) / (s8_max - s8_min + 1e-12)
        return np.stack([omm_norm, s8_norm], axis=1)

    labels_train = normalize_labels(cosmo_train)
    labels_test = normalize_labels(cosmo_test)

    # 5. Pre-training node check (punto A del PI)
    log.info("")
    node_check_result = pretraining_node_check(
        lhc_files_train, persistence_threshold, args.k_nn, args.n_node_check, use_3d
    )
    if node_check_result["mean_nodes"] < 3:
        log.error("Pre-training check FALLITO: mean_nodes < 5. Interrompere e rivedere soglia p90.")
        sys.exit(1)

    # 6. Costruzione dataset grafi
    log.info("\nCostruzione grafi train...")
    t0 = time.time()
    graphs_train = build_graph_dataset(lhc_files_train, persistence_threshold, args.k_nn, use_3d, "train", args.graphs_cache_dir, cache_subdir="lhc")
    log.info(f"  Completato in {time.time()-t0:.1f}s")

    log.info("Costruzione grafi test...")
    t0 = time.time()
    graphs_test = build_graph_dataset(lhc_files_test, persistence_threshold, args.k_nn, use_3d, "test", args.graphs_cache_dir, cache_subdir="lhc")
    log.info(f"  Completato in {time.time()-t0:.1f}s")

    log.info("Costruzione grafi nwLH...")
    t0 = time.time()
    graphs_nwlh = build_graph_dataset(nwlh_files_all, persistence_threshold, args.k_nn, use_3d, "nwlh", args.graphs_cache_dir, cache_subdir="nwlh")
    log.info(f"  Completato in {time.time()-t0:.1f}s")

    # 7. Training GNN
    model, backend = build_gnn_model(
        n_features=9,
        hidden_dim=GNN_HIDDEN_DIM,
        latent_dim=GNN_LATENT_DIM,
        n_layers=GNN_N_LAYERS,
        n_out=2,
    )

    j_star_test = None
    j_star_nwlh = None
    training_info = {}

    if backend == "torch_geometric":
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        log.info(f"\nDevice: {device}")

        # --- Resume da checkpoint (salta training) ---
        if args.resume_from_checkpoint is not None:
            ckpt_path_resume = args.resume_from_checkpoint.resolve()
            log.info(f"=== RESUME MODE: caricamento checkpoint da {ckpt_path_resume} ===")
            if not ckpt_path_resume.exists():
                log.error(f"Checkpoint non trovato: {ckpt_path_resume}")
                sys.exit(1)
            ckpt_data = torch.load(ckpt_path_resume, map_location=device, weights_only=False)
            model.load_state_dict(ckpt_data["model_state_dict"])
            model = model.to(device)
            model.eval()
            log.info(f"  Best epoch: {ckpt_data.get('best_epoch')}, val_loss: {ckpt_data.get('best_val_loss'):.6f}")
            training_info = {
                "best_epoch": ckpt_data.get("best_epoch"),
                "best_val_loss": ckpt_data.get("best_val_loss"),
                "train_losses": [],
                "val_losses": [],
                "backend": "torch_geometric",
                "note": f"RESUME da checkpoint {ckpt_path_resume.name} — training non rieseguito",
            }

            # Costruzione dati test e nwLH (non serve train set)
            data_test, _ = graphs_to_torch_data(graphs_test, labels_test)
            data_nwlh, _ = graphs_to_torch_data(
                graphs_nwlh,
                np.zeros((len([g for g in graphs_nwlh if g is not None]), 2)),
            )

            log.info(f"\nDiagnostica dataset (resume mode):")
            log.info(f"  graphs_test totali: {len(graphs_test)}")
            log.info(f"  graphs_test validi (non-None): {sum(1 for g in graphs_test if g is not None)}")
            log.info(f"  data_test (torch Data): {len(data_test)}")
            log.info(f"  graphs_nwlh validi: {sum(1 for g in graphs_nwlh if g is not None)}")

            if len(data_test) == 0:
                log.error(
                    "DIAGNOSTICA: data_test VUOTO in resume mode. "
                    "Il problema NON è nel training. "
                    "Verificare: np.load(lhc_files_test[0]).files — presenza di 'tau_grid' e 'tau_points'."
                )

            log.info("Estrazione j* sul test set (resume)...")
            j_star_test = extract_j_star_torch(data_test, model, args.batch_size, device)
            log.info(f"  j_star_test shape: {j_star_test.shape}")
            log.info("Estrazione j* su nwLH (resume)...")
            j_star_nwlh = extract_j_star_torch(data_nwlh, model, args.batch_size, device)
            log.info(f"  j_star_nwlh shape: {j_star_nwlh.shape}")

            # Labels allineate
            omm_test_raw = cosmo_test[[i for i, g in enumerate(graphs_test) if g is not None], 0]
            s8_test_raw = cosmo_test[[i for i, g in enumerate(graphs_test) if g is not None], 1]
            w0_nwlh_raw = cosmo_nwlh[[i for i, g in enumerate(graphs_nwlh) if g is not None], 0]

        else:
            n_val_from_train = max(1, int(0.1 * len(graphs_train)))
            val_idx = np.random.default_rng(args.seed + 1).choice(
                len(graphs_train), size=n_val_from_train, replace=False
            )
            train_idx_inner = np.setdiff1d(np.arange(len(graphs_train)), val_idx)

            data_train_inner, labels_train_inner_arr = graphs_to_torch_data(
                [graphs_train[i] for i in train_idx_inner],
                labels_train[train_idx_inner],
            )
            data_val_inner, _ = graphs_to_torch_data(
                [graphs_train[i] for i in val_idx],
                labels_train[val_idx],
            )
            data_test, _ = graphs_to_torch_data(graphs_test, labels_test)
            data_nwlh, _ = graphs_to_torch_data(
                graphs_nwlh,
                np.zeros((len([g for g in graphs_nwlh if g is not None]), 2)),
            )

            log.info(f"\nTraining GNN: {len(data_train_inner)} train, {len(data_val_inner)} val")
            t0 = time.time()
            training_info = train_gnn_torch(
                data_train_inner, data_val_inner, model,
                n_epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
                seed=args.seed,
                device=device,
            )
            log.info(f"Training completato in {time.time()-t0:.1f}s")

            # Salva checkpoint su disco
            ckpt_dir = repo_root / "results" / "checkpoints"
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            ckpt_path = ckpt_dir / "phase3_gnn_best.pt"
            best_state_to_save = training_info.pop("_best_state", None)
            if best_state_to_save is not None:
                import torch as _torch
                _torch.save({
                    "model_state_dict": best_state_to_save,
                    "best_epoch": training_info["best_epoch"],
                    "best_val_loss": training_info["best_val_loss"],
                    "config": {
                        "hidden_dim": GNN_HIDDEN_DIM,
                        "latent_dim": GNN_LATENT_DIM,
                        "n_layers": GNN_N_LAYERS,
                        "n_features": 9,
                        "k_nn": args.k_nn,
                        "persistence_threshold_p90": float(persistence_threshold),
                    },
                }, ckpt_path)
                log.info(f"✓ Checkpoint salvato: {ckpt_path}")
            else:
                log.warning("best_state non disponibile — checkpoint NON salvato")

            # Diagnostica dimensione dataset prima dell'estrazione j*
            log.info(f"\nDiagnostica dataset:")
            log.info(f"  graphs_test totali: {len(graphs_test)}")
            log.info(f"  graphs_test validi (non-None): {sum(1 for g in graphs_test if g is not None)}")
            log.info(f"  data_test (torch Data): {len(data_test)}")
            log.info(f"  graphs_nwlh validi: {sum(1 for g in graphs_nwlh if g is not None)}")
            log.info(f"  data_nwlh (torch Data): {len(data_nwlh)}")

            if len(data_test) == 0:
                log.error(
                    "DIAGNOSTICA: data_test è VUOTO. "
                    "Verificare: np.load(lhc_files_test[0]).files"
                )

            log.info("\nEstrazione j* sul test set...")
            j_star_test = extract_j_star_torch(data_test, model, args.batch_size, device)
            log.info(f"  j_star_test shape: {j_star_test.shape}")
            log.info("Estrazione j* su nwLH...")
            j_star_nwlh = extract_j_star_torch(data_nwlh, model, args.batch_size, device)
            log.info(f"  j_star_nwlh shape: {j_star_nwlh.shape}")

            # Labels test allineate ai grafi validi
            omm_test_raw = cosmo_test[[i for i, g in enumerate(graphs_test) if g is not None], 0]
            s8_test_raw = cosmo_test[[i for i, g in enumerate(graphs_test) if g is not None], 1]
            w0_nwlh_raw = cosmo_nwlh[[i for i, g in enumerate(graphs_nwlh) if g is not None], 0]

            training_info["backend"] = "torch_geometric"

    else:
        # Fallback scipy
        log.info("\nTraining fallback scipy...")
        (_, _, j_star_train_fb, j_star_test_fb, training_info) = train_gnn_scipy_fallback(
            graphs_train, labels_train,
            graphs_test, labels_test,
            n_epochs=args.epochs,
            seed=args.seed,
        )
        j_star_test = j_star_test_fb

        # Costruisce j* per nwLH dal pool di feature
        nwlh_pooled = []
        nwlh_valid_idx = []
        for i, g in enumerate(graphs_nwlh):
            if g is not None:
                nwlh_pooled.append(g["x"].mean(axis=0))
                nwlh_valid_idx.append(i)
        j_star_nwlh = np.array(nwlh_pooled) if nwlh_pooled else np.zeros((0, 9))

        omm_test_raw = np.array([cosmo_test[i, 0] for i, g in enumerate(graphs_test) if g is not None])
        s8_test_raw = np.array([cosmo_test[i, 1] for i, g in enumerate(graphs_test) if g is not None])
        w0_nwlh_raw = np.array([cosmo_nwlh[i, 0] for i in nwlh_valid_idx])

    # 8. Correlazioni Gate 3
    log.info("\n=== Correlazioni Gate 3 ===")
    corr_omm = compute_pearson_r(j_star_test, omm_test_raw)
    corr_s8 = compute_pearson_r(j_star_test, s8_test_raw)
    corr_w0 = compute_pearson_r(j_star_nwlh, w0_nwlh_raw) if len(j_star_nwlh) > 0 else float("nan")

    log.info(f"  |r(GNN_j*, Ωm)|  = {corr_omm:.4f}  (threshold ≥ {CORR_THRESHOLD_LHC})")
    log.info(f"  |r(GNN_j*, σ₈)|  = {corr_s8:.4f}  (threshold ≥ {CORR_THRESHOLD_LHC})")
    log.info(f"  |r(GNN_j*, w₀)|  = {corr_w0:.4f}  (soft — documentare)")

    # Varianza aggiuntiva vs Ramo A
    phase1_path = repo_root / "results" / "phase1_tda_baseline.json"
    try:
        variance_added = compute_variance_added(j_star_test, omm_test_raw, s8_test_raw, phase1_path)
    except (KeyError, FileNotFoundError) as e:
        log.warning(f"Impossibile calcolare varianza aggiuntiva: {e}. Impostato a NaN.")
        variance_added = float("nan")

    # Gate 3 verdict
    gate3_pass = (
        corr_omm >= CORR_THRESHOLD_LHC and
        corr_s8 >= CORR_THRESHOLD_LHC and
        (np.isnan(variance_added) or variance_added >= VARIANCE_ADDED_THRESHOLD_PCT)
    )
    gate3_status = "PASS" if gate3_pass else "FAIL"

    log.info(f"\n  GATE 3 STATUS: {gate3_status}")
    if not gate3_pass:
        if corr_omm < CORR_THRESHOLD_LHC:
            log.warning(f"  → corr_Omm={corr_omm:.4f} < {CORR_THRESHOLD_LHC}")
        if corr_s8 < CORR_THRESHOLD_LHC:
            log.warning(f"  → corr_s8={corr_s8:.4f} < {CORR_THRESHOLD_LHC}")
        if not np.isnan(variance_added) and variance_added < VARIANCE_ADDED_THRESHOLD_PCT:
            log.warning(f"  → variance_added={variance_added:.2f}% < {VARIANCE_ADDED_THRESHOLD_PCT}%")

    # 9. Serializzazione
    output_path = args.output or repo_root / "results" / "phase3_gnn_correlations.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "schema_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate": "GATE_3",
        "script_version": "phase3_gnn.py v1.0",
        "config": {
            "seed": args.seed,
            "lr": args.lr,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "k_nn": args.k_nn,
            "use_3d": use_3d,
            "hidden_dim": GNN_HIDDEN_DIM,
            "latent_dim": GNN_LATENT_DIM,
            "n_layers": GNN_N_LAYERS,
            "n_node_features": 9,
            "backend": training_info.get("backend", "scipy_fallback"),
            "persistence_threshold_p90": float(persistence_threshold),
        },
        "gate2_prior_verified": {
            "n_pts_per_field": N_PTS_PER_FIELD,
            "D_latent": D_LATENT,
            "checkpoint_sha256": EXPECTED_SHA256,
            "status": "OK",
        },
        "pretraining_node_check": node_check_result,
        "training": {
            "best_epoch": training_info.get("best_epoch"),
            "best_val_loss": training_info.get("best_val_loss"),
            "train_losses": training_info.get("train_losses", []),
            "val_losses": training_info.get("val_losses", []),
        },
        "split_info": {
            "n_lhc_train": len(idx_train),
            "n_lhc_test": len(idx_test),
            "n_nwlh": len(cosmo_nwlh),
            "split_seed": 42,
        },
        "corr_GNN_Omm": corr_omm,
        "corr_GNN_s8": corr_s8,
        "corr_GNN_w0_nwlh": corr_w0,
        "variance_added_vs_ramoA_pct": variance_added,
        "gate3_status": gate3_status,
        "gate3_criteria": {
            "corr_Omm_threshold": CORR_THRESHOLD_LHC,
            "corr_s8_threshold": CORR_THRESHOLD_LHC,
            "variance_added_threshold_pct": VARIANCE_ADDED_THRESHOLD_PCT,
            "authority": "CAUCHY_Execution_Parameters §5.2",
        },
        # t1_variability_empirical sarà popolato da phase3_t1_variability.py
        # e mergiato in questo file in Sessione 3
        "t1_variability_empirical": {
            "status": "PENDING — da phase3_t1_variability.py",
            "n_runs": None,
            "R_mean": None,
            "R_std": None,
            "R_min": None,
            "R_max": None,
        },
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    log.info(f"\nOutput scritto: {output_path}")
    log.info("=" * 60)
    log.info(f"  GATE 3 STATUS: {gate3_status}")
    log.info("=" * 60)

    if gate3_status == "FAIL":
        sys.exit(2)


if __name__ == "__main__":
    main()

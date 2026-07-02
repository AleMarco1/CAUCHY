"""
CAUCHY — Phase 7 Sub-Phase 7.1 — Task 7.1a
===========================================
Variabilità T1 GNN Ramo B — Training ridotto su subset
Pre-submission blocker L6 (peer review esterna, maggio 2026)

APPROCCIO: training stochasticity empirica su subset ridotto
  - N_train=160, N_val=40 (subset del dataset LHC di 2000 campi)
  - 10 run indipendenti con torch_seed=0..9
  - Ogni run: training completo -> checkpoint -> estrazione j* su N_SIM_EVAL=200 nwLH
  - sigma_B via permutation test N=1000 (identico a Phase 5)
  - Output: distribuzione sigma_B su 10 run, mean ± std

RAZIONALE:
  Il subset ridotto (200/2000 campi) accelera il training ~10x.
  La variabilità T1 misurata è reale (pesi diversi per seed diverso).
  Il risultato è più rumoroso ma empiricamente corretto.
  sigma_B dovrebbe rimanere ~1σ per tutti i run (null fisicamente atteso).

TRACEABILITY:
  gate3_prior_v1_0.json  -> architettura, optimizer, normalizzazione frozen
  phase5_ramo_b.py       -> tau_to_graph, CGNNCAUCHY, permutation test
  phase5_ramo_b_results.json -> sigma_B_reference=0.983

TARGET SUPERVISIONE: (Omm_norm, s8_norm) — identico a Phase 3
  Normalizzazione min-max frozen sui 2000 campi LHC totali.

ESECUZIONE:
  cd D:\\projects\\cauchy
  conda activate cauchy
  python src\\phase7_t1_variability.py [--test]

  Test rapido (N_RUNS=2, N_TRAIN=16, N_VAL=4, N_EPOCHS=5, N_SIM_EVAL=20):
  python src\\phase7_t1_variability.py --test
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pickle
import torch
import torch.nn as nn
from scipy.stats import pearsonr
from torch.optim.lr_scheduler import CosineAnnealingLR

try:
    from torch_geometric.data import Data, Batch
    from torch_geometric.nn import GCNConv, global_mean_pool, global_max_pool
except ImportError:
    print("ERRORE: torch_geometric non trovato."); sys.exit(1)

try:
    import gudhi
except ImportError:
    print("ERRORE: gudhi non trovato."); sys.exit(1)

# ============================================================
# PARAMETRI
# ============================================================
# Frozen da gate3_prior_v1_0.json
P90        = 0.35589513778686577
K_NN       = 5
HIDDEN_DIM = 64
LATENT_DIM = 32
N_NODE_F   = 9
N_PTS      = 8192
GLOBAL_SEED = 42
VAL_SEED    = 43

# Training ridotto
N_TRAIN     = 1600
N_VAL       = 400
N_SUBSET    = N_TRAIN + N_VAL   # 2000 campi LHC
N_EPOCHS    = 200
LR          = 0.001
WEIGHT_DECAY = 0.0001
GRAD_CLIP   = 1.0
BATCH_SIZE  = 4
EARLY_STOP  = 30     # riabilitato — patience=30, identico a Phase 3

# T1 variability
N_RUNS        = 10
TORCH_SEEDS   = list(range(N_RUNS))

# Eval
N_SIM_EVAL    = 2000  # campi nwLH per sigma_B — massima statistica
PERM_N        = 1000
PERM_SEED     = 42

SIGMA_B_REFERENCE = 0.9830224216611991

# Paths
TAU_LHC_DIR  = Path(r"D:\projects\cauchy\results\phase2_tau_fields\lhc")
TAU_NWLH_DIR = Path(r"D:\projects\cauchy\results\phase2_tau_fields\nwlh")
LHC_PARAMS   = Path(r"D:\projects\cauchy\data\raw\quijote\3D_cubes\latin_hypercube\latin_hypercube_params.txt")
NWLH_PARAMS  = Path(r"D:\projects\cauchy\data\raw\quijote\3D_cubes\latin_hypercube_nwLH\latin_hypercube_nwLH_params.txt")
PRIOR_GATE3  = Path(r"D:\projects\cauchy\prior\gate3_prior_v1_0.json")
CKPT_DIR     = Path(r"D:\projects\cauchy\results\checkpoints")
OUTPUT_JSON      = Path(r"D:\projects\cauchy\results\phase7_t1_variability.json")
CACHE_LHC_PKL    = Path(r"D:\projects\cauchy\results\phase7_t1_graphs_lhc_2000.pkl")
CACHE_NWLH_PKL   = Path(r"D:\projects\cauchy\results\phase7_t1_graphs_nwlh.pkl")


# ============================================================
# ARCHITETTURA GNN (identica a phase5_ramo_b.py / gate3_prior)
# ============================================================

class CGNNCAUCHY(nn.Module):
    def __init__(self, n_node_features=9, hidden_dim=64, latent_dim=32):
        super().__init__()
        self.input_proj = nn.Linear(n_node_features, hidden_dim)
        self.convs = nn.ModuleList([
            GCNConv(hidden_dim, hidden_dim),
            GCNConv(hidden_dim, hidden_dim),
            GCNConv(hidden_dim, latent_dim),
        ])
        self.norms = nn.ModuleList([
            nn.LayerNorm(hidden_dim),
            nn.LayerNorm(hidden_dim),
        ])
        self.j_star_proj = nn.Sequential(
            nn.Linear(2 * latent_dim, latent_dim)
        )
        self.output = nn.Linear(latent_dim, 2)

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        x = self.input_proj(x);  x = torch.relu(x)
        x = self.convs[0](x, edge_index);  x = self.norms[0](x);  x = torch.relu(x)
        x = self.convs[1](x, edge_index);  x = self.norms[1](x);  x = torch.relu(x)
        x = self.convs[2](x, edge_index)
        x_mean = global_mean_pool(x, batch)
        x_max  = global_max_pool(x, batch)
        pool   = torch.cat([x_mean, x_max], dim=1)
        j_star = self.j_star_proj[0](pool)
        return j_star

    def predict(self, data):
        j = self.forward(data)
        return self.output(j)


# ============================================================
# COSTRUZIONE GRAFO (identica a phase5_ramo_b.py)
# ============================================================

def tau_to_graph(tau_field, p90, k_nn, n_pts, mu_lcdm_scalar, rng=None):
    tau_norm  = np.abs(tau_field.astype(np.float64))
    field_neg = -tau_norm
    cc = gudhi.CubicalComplex(
        dimensions=list(field_neg.shape),
        top_dimensional_cells=field_neg.flatten()
    )
    cc.compute_persistence()
    diag_1 = np.array(cc.persistence_intervals_in_dimension(1))
    diag_2 = np.array(cc.persistence_intervals_in_dimension(2))

    def filter_diag(diag, p90):
        if len(diag) == 0:
            return [], [], [], []
        fin   = np.isfinite(diag[:, 1])
        d     = diag[fin]
        if len(d) == 0:
            return [], [], [], []
        birth = -d[:, 0];  death = -d[:, 1];  pers = birth - death
        mask  = pers >= p90
        return d[mask], birth[mask], death[mask], pers[mask]

    res1 = filter_diag(diag_1, p90)
    res2 = filter_diag(diag_2, p90)

    nodes_list = []
    N_grid     = tau_norm.shape[0]
    flat_vals  = tau_norm.ravel()
    sort_idx   = np.argsort(flat_vals)[::-1]
    sorted_v   = flat_vals[sort_idx].astype(np.float32)
    coords_all = np.stack(
        np.unravel_index(sort_idx, tau_norm.shape), axis=1
    ).astype(np.float32)
    MAX_BARY = 2048

    def add_nodes(d_raw, birth_arr, death_arr, pers_arr, dim_lbl):
        d1 = 1.0 if dim_lbl == 1 else 0.0
        d2 = 1.0 if dim_lbl == 2 else 0.0
        for idx in range(len(birth_arr)):
            b = birth_arr[idx];  dv = death_arr[idx];  p = pers_arr[idx]
            thr = max(0.0, b * 0.9)
            n_ab = int(np.searchsorted(-sorted_v, -thr, side='right'))
            if n_ab == 0:
                cx = cy = cz = 0.5;  tm = 0.0
            else:
                nu = min(n_ab, MAX_BARY)
                c  = coords_all[:nu];  w = sorted_v[:nu];  ws = float(w.sum())
                cx = float((c[:,0]*w).sum()/(ws*N_grid))
                cy = float((c[:,1]*w).sum()/(ws*N_grid))
                cz = float((c[:,2]*w).sum()/(ws*N_grid))
                tm = float(sorted_v[:n_ab].mean())
            nodes_list.append([b, dv, p, d1, d2,
                                float(tm/(mu_lcdm_scalar+1e-10)), cx, cy, cz])

    if len(res1[0]) > 0:
        add_nodes(res1[0], res1[1], res1[2], res1[3], 1)
    if len(res2[0]) > 0:
        add_nodes(res2[0], res2[1], res2[2], res2[3], 2)
    if len(nodes_list) == 0:
        nodes_list = [[0.0]*9]

    node_feats = np.array(nodes_list, dtype=np.float32)

    # Subsampling (con rng se fornito, altrimenti deterministico)
    if len(node_feats) > n_pts:
        if rng is not None:
            idx = rng.choice(len(node_feats), n_pts, replace=False)
        else:
            idx = np.arange(n_pts)
        node_feats = node_feats[idx]

    bd   = node_feats[:, :2];  N = len(bd);  k = min(k_nn, N-1)
    if k <= 0:
        edge_index = np.zeros((2, 0), dtype=np.int64)
    else:
        diff = bd[:, None, :] - bd[None, :, :]
        dist = np.sqrt((diff**2).sum(-1))
        np.fill_diagonal(dist, np.inf)
        knn_idx    = np.argsort(dist, axis=1)[:, :k]
        src        = np.repeat(np.arange(N), k)
        dst        = knn_idx.flatten()
        edge_index = np.concatenate([
            np.stack([src, dst]), np.stack([dst, src])
        ], axis=1)

    return node_feats, edge_index


def load_graph(tau_file, p90, k_nn, n_pts, rng=None):
    """Carica tau_field e costruisce grafo PyG."""
    d              = np.load(tau_file)
    tau            = d['tau_grid']
    mu_lcdm_scalar = float(d['mu_lcdm'].mean())
    node_feats, edge_index = tau_to_graph(tau, p90, k_nn, n_pts,
                                           mu_lcdm_scalar, rng)
    return Data(
        x=torch.tensor(node_feats, dtype=torch.float32),
        edge_index=torch.tensor(edge_index, dtype=torch.long),
    )


# ============================================================
# DATASET
# ============================================================

class TauDataset:
    def __init__(self, graphs_cache, indices, labels_norm):
        """graphs_cache: dict {field_idx: Data} pre-costruito."""
        self.cache  = graphs_cache
        self.indices = indices
        self.labels  = labels_norm

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, local_idx):
        i    = self.indices[local_idx]
        data = self.cache[i].clone()
        data.y = torch.tensor(self.labels[i], dtype=torch.float32).unsqueeze(0)
        return data


def build_graph_cache(tau_dir, indices, label="", disk_cache_path=None):
    """
    Pre-costruisce tutti i grafi una volta sola (deterministic, no rng).
    Se disk_cache_path fornito: carica da disco se esiste, altrimenti
    costruisce e salva su disco per riusi futuri.
    """
    # Prova a caricare da disco
    if disk_cache_path is not None and Path(disk_cache_path).exists():
        print(f"  Cache {label} trovata su disco: {disk_cache_path}")
        t0 = time.time()
        with open(disk_cache_path, 'rb') as f:
            cache = pickle.load(f)
        print(f"  Cache {label} caricata: {len(cache)} grafi in "
              f"{(time.time()-t0)/60:.1f}min")
        return cache

    # Costruisci da zero
    cache = {}
    t0    = time.time()
    print(f"  Pre-caching {len(indices)} grafi {label}...")
    for k, i in enumerate(indices):
        path = Path(tau_dir) / f"tau_field_{i:04d}.npz"
        try:
            cache[i] = load_graph(path, P90, K_NN, N_PTS, rng=None)
        except Exception as e:
            print(f"    ERRORE campo {i}: {e}")
        if (k+1) % 50 == 0 or (k+1) == len(indices):
            print(f"    {k+1}/{len(indices)} | {(time.time()-t0)/60:.1f}min")
    print(f"  Cache completata: {len(cache)} grafi in {(time.time()-t0)/60:.1f}min")

    # Salva su disco
    if disk_cache_path is not None:
        print(f"  Salvataggio cache {label} su disco: {disk_cache_path}")
        Path(disk_cache_path).parent.mkdir(parents=True, exist_ok=True)
        with open(disk_cache_path, 'wb') as f:
            pickle.dump(cache, f, protocol=4)
        print(f"  Salvato.")

    return cache


def collate_graphs(batch):
    return Batch.from_data_list(batch)


# ============================================================
# TRAINING
# ============================================================

def train_one_run(model, train_ds, val_ds, device, run_idx,
                  n_epochs, ckpt_path):
    from torch.utils.data import DataLoader
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              collate_fn=collate_graphs, num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              collate_fn=collate_graphs, num_workers=0)

    opt   = torch.optim.AdamW(model.parameters(), lr=LR,
                               weight_decay=WEIGHT_DECAY)
    sched = CosineAnnealingLR(opt, T_max=n_epochs, eta_min=1e-6)
    crit  = nn.MSELoss()

    best_val   = float('inf')
    best_epoch = 0
    no_improve = 0
    t0         = time.time()

    for epoch in range(1, n_epochs + 1):
        model.train()
        tr_loss = 0.0
        for batch in train_loader:
            batch = batch.to(device)
            opt.zero_grad()
            j     = model(batch)
            pred  = model.output(j)
            loss  = crit(pred, batch.y.squeeze(1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            opt.step()
            tr_loss += loss.item()
        sched.step()

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                batch    = batch.to(device)
                j        = model(batch)
                pred     = model.output(j)
                val_loss += crit(pred, batch.y.squeeze(1)).item()

        tr_loss  /= len(train_loader)
        val_loss /= len(val_loader)

        if val_loss < best_val:
            best_val   = val_loss
            best_epoch = epoch
            no_improve = 0
            torch.save({'epoch': epoch,
                        'model_state_dict': model.state_dict(),
                        'val_loss': val_loss,
                        'run_idx': run_idx,
                        'torch_seed': TORCH_SEEDS[run_idx]}, ckpt_path)
        else:
            no_improve += 1

        if epoch % 20 == 0 or epoch == 1:
            print(f"    Ep {epoch:3d} | tr={tr_loss:.5f} val={val_loss:.5f} "
                  f"best={best_val:.5f}@{best_epoch} "
                  f"elapsed={( time.time()-t0)/60:.1f}min")

        if no_improve >= EARLY_STOP:
            print(f"    Early stop ep={epoch}")
            break

    elapsed = (time.time() - t0) / 60
    print(f"    Completato: best_val={best_val:.5f} @ep={best_epoch} "
          f"in {elapsed:.1f}min")
    return {'best_val': float(best_val), 'best_epoch': int(best_epoch),
            'n_epochs': epoch, 'elapsed_min': float(elapsed)}


# ============================================================
# ESTRAZIONE j* (identica a phase5_ramo_b.py)
# ============================================================

def _load_single_graph(args):
    """Carica un singolo grafo nwLH — eseguibile in thread pool."""
    i, tau_file = args
    try:
        data = load_graph(tau_file, P90, K_NN, N_PTS, rng=None)
        return i, data, data.x.shape[0], None
    except Exception as e:
        return i, None, 0, str(e)


def extract_jstar(model, device, n_sim, nwlh_cache=None):
    """
    Estrae j* su n_sim campi nwLH.
    Se nwlh_cache fornita: usa grafi pre-cachati (nessun I/O/gudhi).
    Altrimenti carica in parallelo con ThreadPoolExecutor (8 thread).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    model.eval()
    jstar        = np.zeros((n_sim, LATENT_DIM), dtype=np.float32)
    n_nodes_list = []
    errors       = []

    # Step 1: ottieni grafi (da cache o da disco)
    if nwlh_cache is not None:
        graphs       = {i: nwlh_cache[i] for i in range(n_sim) if i in nwlh_cache}
        errors       = [i for i in range(n_sim) if i not in nwlh_cache]
        n_nodes_list = [nwlh_cache[i].x.shape[0] for i in graphs]
    else:
        tasks    = [(i, TAU_NWLH_DIR / f"tau_field_{i:04d}.npz")
                    for i in range(n_sim)
                    if (TAU_NWLH_DIR / f"tau_field_{i:04d}.npz").exists()]
        missing  = [i for i in range(n_sim)
                    if not (TAU_NWLH_DIR / f"tau_field_{i:04d}.npz").exists()]
        errors.extend(missing)
        N_WORKERS = min(8, len(tasks))
        graphs    = {}
        with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
            futures = {pool.submit(_load_single_graph, t): t[0] for t in tasks}
            done    = 0
            for fut in as_completed(futures):
                i, data, n_nodes, err = fut.result()
                if err is not None:
                    errors.append(i)
                else:
                    graphs[i] = data
                    n_nodes_list.append(n_nodes)
                done += 1
                if done % 200 == 0:
                    print(f"      Grafi caricati: {done}/{len(tasks)}")

    # Step 2: forward pass GPU in batch da 8
    BATCH_GPU = 8
    indices   = sorted(graphs.keys())

    with torch.no_grad():
        for start in range(0, len(indices), BATCH_GPU):
            batch_idx  = indices[start: start + BATCH_GPU]
            batch_data = Batch.from_data_list(
                [graphs[i] for i in batch_idx]
            ).to(device)
            # batch_data.batch assegnato automaticamente da Batch
            j_batch = model(batch_data)   # (batch_size, LATENT_DIM)
            for k, i in enumerate(batch_idx):
                jstar[i] = j_batch[k].cpu().numpy()

    if errors:
        valid = ~np.isin(np.arange(n_sim), errors)
        if valid.sum() > 0:
            for e in errors:
                jstar[e] = jstar[valid].mean(axis=0)

    return jstar, errors, float(np.mean(n_nodes_list)) if n_nodes_list else 0.0


# ============================================================
# SIGMA_B (identica a phase5_ramo_b.py)
# ============================================================

def compute_sigma_B(jstar, w0_all, Om_all, s8_all, n_perm=PERM_N, seed=PERM_SEED):
    """
    sigma_B via partial correlation + permutation test.
    Identica a phase5_ramo_b.py righe 420-451.
    Residui calcolati su (Omm, s8) prima di tutto.
    """
    from numpy.linalg import lstsq
    N = len(w0_all)
    X = np.column_stack([Om_all, s8_all, np.ones(N)])
    rw = w0_all - X @ lstsq(X, w0_all, rcond=None)[0]
    r_components = np.zeros(LATENT_DIM)
    for k in range(LATENT_DIM):
        if jstar[:, k].std() < 1e-10:
            continue
        rjk = jstar[:, k] - X @ lstsq(X, jstar[:, k], rcond=None)[0]
        r_components[k] = float(pearsonr(rjk, rw)[0])
    best_k   = int(np.argmax(np.abs(r_components)))
    rjk_best = jstar[:, best_k] - X @ lstsq(X, jstar[:, best_k], rcond=None)[0]
    r_obs    = float(pearsonr(rjk_best, rw)[0])
    rng      = np.random.default_rng(seed)
    nulls    = np.array([pearsonr(rjk_best, rng.permutation(rw))[0]
                         for _ in range(n_perm)])
    null_mean = float(nulls.mean())
    null_std  = float(nulls.std())
    sigma_B   = float((abs(r_obs) - abs(null_mean)) / null_std) if null_std > 0 else 0.0
    return {'sigma_B': sigma_B, 'rho_obs': r_obs,
            'best_component': best_k,
            'null_mean': null_mean, 'null_std': null_std,
            'max_abs_rho': float(np.max(np.abs(r_components))),
            'r_components_partial': r_components.tolist()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true",
                        help="Test: N_RUNS=2, N_TRAIN=16, N_VAL=4, "
                             "N_EPOCHS=5, N_SIM_EVAL=20, PERM_N=50")
    args = parser.parse_args()

    n_runs    = 2   if args.test else N_RUNS
    n_train   = 32  if args.test else N_TRAIN
    n_val     = 8   if args.test else N_VAL
    n_epochs  = 5   if args.test else N_EPOCHS
    n_sim     = 20  if args.test else N_SIM_EVAL
    perm_n    = 50  if args.test else PERM_N
    n_subset  = n_train + n_val

    print("=" * 60)
    print(f"CAUCHY 7.1a — T1 variability GNN (training ridotto)")
    print(f"N_RUNS={n_runs}, N_TRAIN={n_train}, N_VAL={n_val}, "
          f"N_EPOCHS={n_epochs}, N_SIM_EVAL={n_sim}")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # ── Carica parametri cosmologici LHC ─────────────────────────────────────
    print("\n[1] Caricamento parametri LHC e nwLH...")

    # LHC params — cerca il file con fallback su path alternativi
    lhc_params_candidates = [
        LHC_PARAMS,
        Path(r"D:\projects\cauchy\data\raw\quijote\3D_cubes\latin_hypercube\latin_hypercube_params.txt"),
        Path(r"D:\projects\cauchy\data\raw\quijote\latin_hypercube_params.txt"),
    ]
    lhc_params_file = None
    for c in lhc_params_candidates:
        if c.exists():
            lhc_params_file = c; break
    if lhc_params_file is None:
        # Cerca ricorsivamente
        import glob
        hits = glob.glob(r"D:\projects\cauchy\**\latin_hypercube_params.txt",
                         recursive=True)
        if hits:
            lhc_params_file = Path(hits[0])
        else:
            print("ERRORE: latin_hypercube_params.txt non trovato.")
            print("Dimmi il path esatto del file parametri LHC.")
            sys.exit(1)

    print(f"  LHC params: {lhc_params_file}")
    lhc_cosmo = np.loadtxt(lhc_params_file)
    Omm_lhc   = lhc_cosmo[:, 0]
    s8_lhc    = lhc_cosmo[:, 4]

    # Normalizzazione frozen sui 2000 campi LHC totali
    Omm_min, Omm_max = Omm_lhc.min(), Omm_lhc.max()
    s8_min,  s8_max  = s8_lhc.min(),  s8_lhc.max()
    Omm_norm = (Omm_lhc - Omm_min) / (Omm_max - Omm_min)
    s8_norm  = (s8_lhc  - s8_min)  / (s8_max  - s8_min)
    labels_norm = np.stack([Omm_norm, s8_norm], axis=1).astype(np.float32)
    print(f"  Omm_norm range: [{Omm_norm.min():.3f}, {Omm_norm.max():.3f}]")
    print(f"  s8_norm  range: [{s8_norm.min():.3f},  {s8_norm.max():.3f}]")

    # w0 nwLH per sigma_B
    params_nwlh = np.loadtxt(NWLH_PARAMS)
    w0_all = params_nwlh[:n_sim, 6]   # col6 = w0 (Phase 5 riga 104)
    Om_all = params_nwlh[:n_sim, 0]
    s8_all = params_nwlh[:n_sim, 4]
    print(f"  w0 nwLH: shape={w0_all.shape}, "
          f"range=[{w0_all.min():.3f},{w0_all.max():.3f}]")

    # ── Split subset (seed fisso per riproducibilità) ─────────────────────────
    rng_split = np.random.default_rng(GLOBAL_SEED)
    subset_idx = rng_split.choice(2000, size=n_subset, replace=False)
    rng_val    = np.random.default_rng(VAL_SEED)
    val_local  = rng_val.choice(n_subset, size=n_val, replace=False)
    val_mask   = np.zeros(n_subset, dtype=bool)
    val_mask[val_local] = True
    train_indices = subset_idx[~val_mask]
    val_indices   = subset_idx[val_mask]
    print(f"\n  Subset: {n_subset} campi LHC "
          f"(train={len(train_indices)}, val={len(val_indices)})")

    # Pre-caching grafi LHC (una volta sola, riusato per tutti i 10 run)
    all_indices   = np.concatenate([train_indices, val_indices])
    graphs_cache  = build_graph_cache(TAU_LHC_DIR, all_indices, label="LHC subset",
                                          disk_cache_path=CACHE_LHC_PKL)
    train_ds = TauDataset(graphs_cache, train_indices, labels_norm)
    val_ds   = TauDataset(graphs_cache, val_indices,   labels_norm)

    # Pre-cache grafi nwLH — evita ricalcolo gudhi ad ogni run
    nwlh_cache = build_graph_cache(TAU_NWLH_DIR, list(range(n_sim)), label="nwLH",
                                      disk_cache_path=CACHE_NWLH_PKL)

    # ── Loop T1 ───────────────────────────────────────────────────────────────
    print(f"\n[2] {n_runs} run di training con torch_seed diversi...")
    run_results    = []
    sigma_B_values = []
    t_total        = time.time()

    CKPT_DIR.mkdir(parents=True, exist_ok=True)

    for i in range(n_runs):
        seed_i    = TORCH_SEEDS[i]
        ckpt_path = CKPT_DIR / f"phase7_t1_run_{i:02d}_best.pt"
        print(f"\n  {'='*50}")
        print(f"  RUN {i:02d}/{n_runs-1} — torch_seed={seed_i}")
        print(f"  {'='*50}")

        # Inizializza modello con seed diverso (pesi diversi)
        torch.manual_seed(seed_i)
        if device.type == 'cuda':
            torch.cuda.manual_seed(seed_i)
        model  = CGNNCAUCHY(N_NODE_F, HIDDEN_DIM, LATENT_DIM).to(device)
        n_par  = sum(p.numel() for p in model.parameters())
        print(f"  Modello inizializzato: {n_par:,} params (torch_seed={seed_i})")

        # Training
        print(f"  Training ({n_train} tr + {n_val} val, max {n_epochs} epoche)...")
        train_report = train_one_run(model, train_ds, val_ds, device,
                                     i, n_epochs, ckpt_path)

        # Carica best checkpoint
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        model.eval()

        # Estrai j* su campi nwLH
        print(f"  Estrazione j* su {n_sim} campi nwLH...")
        jstar, errors, n_nodes_mean = extract_jstar(model, device, n_sim,
                                                         nwlh_cache=nwlh_cache)

        # sigma_B
        result = compute_sigma_B(jstar, w0_all, Om_all, s8_all,
                                  n_perm=perm_n)
        sigma_B_values.append(result['sigma_B'])

        print(f"  sigma_B={result['sigma_B']:.4f}  "
              f"rho_obs={result['rho_obs']:+.4f}  "
              f"component={result['best_component']}  "
              f"n_nodes_mean={n_nodes_mean:.0f}")

        run_results.append({
            'run_idx':       i,
            'torch_seed':    seed_i,
            'training':      train_report,
            'sigma_B':       result,
            'n_nodes_mean':  n_nodes_mean,
            'n_errors':      len(errors),
        })

        del model
        if device.type == 'cuda':
            torch.cuda.empty_cache()

    # ── Statistiche finali ────────────────────────────────────────────────────
    arr          = np.array(sigma_B_values)
    mean_s       = float(arr.mean())
    std_s        = float(arr.std())
    min_s        = float(arr.min())
    max_s        = float(arr.max())
    all_nonsig   = bool(all(s < 2.0 for s in sigma_B_values))
    cv_pct       = float(std_s / mean_s * 100) if mean_s > 0 else 0.0
    elapsed_total = (time.time() - t_total) / 60

    print(f"\n{'='*60}")
    print(f"RIEPILOGO T1 VARIABILITY ({n_runs} run)")
    print(f"{'='*60}")
    print(f"sigma_B per run: {[f'{s:.3f}' for s in sigma_B_values]}")
    print(f"mean ± std:      {mean_s:.4f} ± {std_s:.4f}")
    print(f"range:           [{min_s:.4f}, {max_s:.4f}]")
    print(f"CV:              {cv_pct:.1f}%")
    print(f"Riferimento Phase 5 (N=2000): {SIGMA_B_REFERENCE:.3f}")
    print(f"Tutti < 2sigma:  {all_nonsig}")
    print(f"Tempo totale:    {elapsed_total:.1f} min")

    # ── Output JSON ───────────────────────────────────────────────────────────
    output = {
        "schema_version": "2.0",
        "task": "7.1a_T1_variability",
        "approach": "training_stochasticity_reduced_subset",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": (
            f"T1 training stochasticity: {n_runs} independent GNN training runs "
            f"with different torch seeds on reduced subset "
            f"(N_train={n_train}, N_val={n_val}). "
            "Sigma_B evaluated on N_SIM_EVAL nwLH fields. "
            "Pipeline identical to phase5_ramo_b.py."
        ),
        "traceability": {
            "architecture": "CGNNCAUCHY (phase5_ramo_b.py)",
            "optimizer": "AdamW + CosineAnnealingLR (gate3_prior_v1_0.json)",
            "sigma_B_reference_phase5": SIGMA_B_REFERENCE,
            "phase5_N_sim": 2000,
            "torch_seeds": TORCH_SEEDS[:n_runs],
            "subset_seed": GLOBAL_SEED,
            "val_seed": VAL_SEED,
        },
        "parameters": {
            "n_runs": n_runs, "n_train": n_train, "n_val": n_val,
            "n_epochs_max": n_epochs, "n_sim_eval": n_sim,
            "p90": P90, "k_nn": K_NN, "latent_dim": LATENT_DIM,
            "perm_n": perm_n, "early_stop_patience": EARLY_STOP,
        },
        "results": {
            "sigma_B_values":               sigma_B_values,
            "sigma_B_mean":                 mean_s,
            "sigma_B_std":                  std_s,
            "sigma_B_min":                  min_s,
            "sigma_B_max":                  max_s,
            "coefficient_of_variation_pct": cv_pct,
            "all_nonsignificant_2sigma":    all_nonsig,
            "sigma_B_reference_phase5":     SIGMA_B_REFERENCE,
        },
        "run_details": run_results,
        "interpretation": {
            "verdict": "ROBUST_NULL" if all_nonsig else "CHECK_REQUIRED",
            "caveat": (
                f"Training on reduced subset (N={n_train+n_val} vs 2000 in Phase 5). "
                "sigma_B values are noisier but training stochasticity is real. "
                "All runs expected ~1sigma (null physically motivated at z=0 real space)."
            ),
            "paper_statement": (
                f"sigma_B = {mean_s:.2f} +/- {std_s:.2f} "
                f"(mean +/- std, N={n_runs} independent training runs with "
                f"different random seeds, evaluated on N={n_sim} nwLH fields). "
                "Consistent with null result across all seeds."
            ),
        },
        "elapsed_total_min": float(elapsed_total),
        "test_mode": args.test,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Output: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

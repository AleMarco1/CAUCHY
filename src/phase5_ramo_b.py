"""
CAUCHY — Phase 5, Ramo B
src/phase5_ramo_b.py

Estrae j* ∈ R^32 dal checkpoint GNN (epoch 171) per i 2000 campi nwLH
e calcola la correlazione parziale r(j*, w0 | Omm, s8).

Il GNN opera su τ(x) = CNN(δ) − μ_ΛCDM (campo di tensione Phase 2),
non sul campo δ_DM direttamente.

Parametri frozen (gate3_prior_v1_0.json):
  checkpoint:  results/checkpoints/phase3_gnn_best.pt
  p90:         0.35589513778686577
  k_nn:        5
  hidden_dim:  64
  latent_dim:  32
  n_layers:    3
  n_node_feat: 9 (birth, death, persistence, dim_beta1, dim_beta2,
                   tau_norm_mean_region, cx_norm, cy_norm, cz_norm)
  pooling:     GlobalMeanPool + GlobalMaxPool concatenati
  split_seed:  42

Input:
  results/phase2_tau_fields/nwlh/{i}/tau_grid.npy      (campo tau 128^3)
  results/checkpoints/phase3_gnn_best.pt               (checkpoint)
  latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt (parametri cosmologici)
  prior/gate3_prior_v1_0.json                          (parametri frozen)

Output:
  results/phase5_jstar_nwlh.npz   — j* [2000, 32] + w0, Omm, s8
  results/phase5_ramo_b_results.json

Uso:
  python src/phase5_ramo_b.py [--n_perm 1000] [--seed 42] [--project_root .]
  python src/phase5_ramo_b.py --mode extract_only   # solo j*, no permutation test
  python src/phase5_ramo_b.py --mode corr_only      # solo correlazione (j* gia estratto)
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr

parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--n_perm", type=int, default=1000)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--mode", choices=["full", "extract_only", "corr_only"],
                    default="full")
parser.add_argument("--batch_size", type=int, default=16,
                    help="Batch size per inferenza GNN (default 16)")
args = parser.parse_args()

ROOT         = Path(args.project_root)
TAU_DIR      = ROOT / "results" / "phase2_tau_fields" / "nwlh"
CHECKPOINT   = ROOT / "results" / "checkpoints" / "phase3_gnn_best.pt"
PARAMS_FILE  = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / \
               "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
PRIOR_GATE3  = ROOT / "prior" / "gate3_prior_v1_0.json"
JSTAR_FILE   = ROOT / "results" / "phase5_jstar_nwlh.npz"
OUTPUT_FILE  = ROOT / "results" / "phase5_ramo_b_results.json"

np.random.seed(args.seed)
rng = np.random.default_rng(args.seed)

print("=" * 70)
print("CAUCHY Phase 5 — Ramo B: j* extraction + partial correlation")
print("=" * 70)

# ---------------------------------------------------------------------------
# Verifica prerequisiti
# ---------------------------------------------------------------------------
assert CHECKPOINT.exists(),  f"Checkpoint non trovato: {CHECKPOINT}"
assert PARAMS_FILE.exists(), f"Parametri nwLH non trovati: {PARAMS_FILE}"
assert PRIOR_GATE3.exists(), f"Prior Gate 3 non trovato: {PRIOR_GATE3}"

with open(PRIOR_GATE3) as f:
    prior3 = json.load(f)

P90        = prior3["frozen_graph_construction"]["persistence_threshold_p90"]
K_NN       = prior3["frozen_gnn_architecture"]["k_nn_persistence_space"]
HIDDEN_DIM = prior3["frozen_gnn_architecture"]["hidden_dim"]
LATENT_DIM = prior3["frozen_gnn_architecture"]["latent_dim"]
N_LAYERS   = prior3["frozen_gnn_architecture"]["n_layers"]
N_NODE_F   = prior3["frozen_gnn_architecture"]["n_node_features"]
BEST_EPOCH = prior3["frozen_gnn_training"]["best_epoch"]
MU_LCDM    = prior3["frozen_tau_source"]["mu_lcdm_norm"]
N_PTS      = prior3["frozen_tau_source"]["n_pts_per_field"]
BOXSIZE    = prior3["frozen_graph_construction"]["box_size_mpch"]

print(f"\nParametri frozen Gate 3:")
print(f"  p90 = {P90:.6f}")
print(f"  k_nn = {K_NN}, hidden_dim = {HIDDEN_DIM}, latent_dim = {LATENT_DIM}")
print(f"  best_epoch = {BEST_EPOCH}")
print(f"  mu_LCDM = {MU_LCDM:.6f}")
print(f"  n_pts_per_field = {N_PTS}")

# Carica parametri cosmologici
cosmo   = np.loadtxt(PARAMS_FILE, comments='#')
w0_all  = cosmo[:, 6]
Omm_all = cosmo[:, 0]
s8_all  = cosmo[:, 4]
N_SIM   = 2000
print(f"\nParametri nwLH: {cosmo.shape}, w0 [{w0_all.min():.2f}, {w0_all.max():.2f}]")

# ---------------------------------------------------------------------------
# FASE 1: Estrazione j* dal checkpoint GNN
# ---------------------------------------------------------------------------
if args.mode in ["full", "extract_only"]:
    print(f"\n{'='*70}")
    print("FASE 1 — Estrazione j* (GNN inference su 2000 campi nwLH)")
    print(f"{'='*70}")

    # Import lazy: torch caricato solo quando serve, con env gia configurato
    import os
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    # Aggiungi DLL torch al PATH (fix shm.dll su Windows con torch nightly)
    import sys
    torch_lib = None
    for p in sys.path:
        candidate = os.path.join(p, "torch", "lib")
        if os.path.isdir(candidate):
            torch_lib = candidate
            break
    if torch_lib and torch_lib not in os.environ.get("PATH", ""):
        os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")

    try:
        import torch
        import torch.nn as nn
        from torch_geometric.data import Data, Batch
        from torch_geometric.nn import GCNConv, global_mean_pool, global_max_pool
        import gudhi
    except ImportError as e:
        print(f"Dipendenza mancante: {e}")
        print("Installare: pip install torch torch_geometric gudhi")
        raise

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    # Definizione architettura GNN (identica a Phase 3)
    class CGNNCAUCHY(nn.Module):
        """
        Architettura verificata dal checkpoint phase3_gnn_best.pt:
          input_proj: Linear(9->64)
          convs.0: GCNConv(64->64), norms.0: LayerNorm(64)
          convs.1: GCNConv(64->64), norms.1: LayerNorm(64)
          convs.2: GCNConv(64->32)  [NO norm.2 nel checkpoint]
          pooling: GlobalMeanPool + GlobalMaxPool -> [B, 64]
          j_star_proj.0: Linear(64->32)  [NO ReLU — dying neurons fix]
          output: Linear(32->2)  [non usato per j*]
        j* = j_star_proj.0(pool) in R^32
        """
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
                # norms.2 NON presente nel checkpoint
            ])
            # j_star_proj: Linear(2*latent_dim -> latent_dim), NO ReLU
            self.j_star_proj = nn.Sequential(
                nn.Linear(2 * latent_dim, latent_dim)
            )
            # output: Linear(latent_dim -> 2) — usato per training, non per j*
            self.output = nn.Linear(latent_dim, 2)

        def forward(self, data):
            x, edge_index, batch = data.x, data.edge_index, data.batch
            x = self.input_proj(x)
            x = torch.relu(x)
            # Conv 0: con norm e relu
            x = self.convs[0](x, edge_index)
            x = self.norms[0](x)
            x = torch.relu(x)
            # Conv 1: con norm e relu
            x = self.convs[1](x, edge_index)
            x = self.norms[1](x)
            x = torch.relu(x)
            # Conv 2: senza norm (non nel checkpoint), senza relu finale
            x = self.convs[2](x, edge_index)
            # Pooling: GlobalMeanPool + GlobalMaxPool concatenati -> [B, 64]
            x_mean = global_mean_pool(x, batch)
            x_max  = global_max_pool(x, batch)
            pool = torch.cat([x_mean, x_max], dim=1)  # [B, 2*latent_dim=64]
            # j* = proiezione lineare senza ReLU (fix dying neurons Phase 3)
            j_star = self.j_star_proj[0](pool)  # [B, 32]
            return j_star

    # Carica checkpoint
    model = CGNNCAUCHY(N_NODE_F, HIDDEN_DIM, LATENT_DIM).to(device)
    ckpt  = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    # Il checkpoint potrebbe contenere solo state_dict o un dict con 'model_state_dict'
    if isinstance(ckpt, dict) and 'model_state_dict' in ckpt:
        model.load_state_dict(ckpt['model_state_dict'])
        epoch_loaded = ckpt.get('epoch', BEST_EPOCH)
    else:
        model.load_state_dict(ckpt)
        epoch_loaded = BEST_EPOCH
    model.eval()
    print(f"  Checkpoint caricato (epoch {epoch_loaded})")

    # Costruzione grafo da campo τ (identica a Phase 3)
    def tau_to_graph(tau_field, p90, k_nn, n_pts, boxsize, mu_lcdm):
        """
        Costruisce il grafo PyG da un campo τ 128³.
        Identica alla funzione usata in Phase 3 per garantire coerenza.
        """
        import gudhi

        # 1. τ_norm = |τ(x)| grezzo — il prior gate3 frozen dice esplicitamente:
        #    "tda_field: tau_grid — norma |tau(x)| su griglia 128^3" (senza divisione).
        #    p90=0.3559 è calibrato su questo campo grezzo (range ~[0,23]).
        tau_norm = np.abs(tau_field.astype(np.float64))

        # 2. Filtrazione superlevel su tau_norm
        field_neg = -tau_norm
        cc = gudhi.CubicalComplex(
            dimensions=list(field_neg.shape),
            top_dimensional_cells=field_neg.flatten()
        )
        cc.compute_persistence()

        # 3. Filtra con soglia p90
        diag_1 = np.array(cc.persistence_intervals_in_dimension(1))
        diag_2 = np.array(cc.persistence_intervals_in_dimension(2))

        def filter_diag(diag, p90):
            if len(diag) == 0:
                return np.zeros((0, 2))
            fin = np.isfinite(diag[:, 1])
            d = diag[fin]
            # Convenzione gudhi per filtrazione su -tau_norm (superlevel):
            # col0 = valore di filtrazione alla nascita = -tau_alto (più negativo)
            # col1 = valore di filtrazione alla morte  = -tau_basso (meno negativo)
            # Quindi: birth_real = -col0, death_real = -col1, pers = birth-death > 0
            birth = -d[:, 0]
            death = -d[:, 1]
            pers  = birth - death
            mask  = pers >= p90
            return d[mask], birth[mask], death[mask], pers[mask]

        res1 = filter_diag(diag_1, p90)
        res2 = filter_diag(diag_2, p90)

        nodes_list = []
        N_grid = tau_norm.shape[0]

        # Precomputa struttura ordinata per campo — evita argwhere per ogni nodo
        # Ordina valori in ordine decrescente: celle sopra soglia = prefisso
        flat_vals  = tau_norm.ravel()
        sort_idx   = np.argsort(flat_vals)[::-1]
        sorted_v   = flat_vals[sort_idx].astype(np.float32)
        coords_all = np.stack(np.unravel_index(sort_idx, tau_norm.shape), axis=1).astype(np.float32)

        # Max celle per il calcolo del baricentro: campiona le top-N per valore
        # (già ordinate desc in sorted_v/coords_all). 2048 è più che sufficiente
        # per stimare un baricentro pesato — evita dot-product su ~1M celle.
        MAX_BARY_CELLS = 2048

        def add_nodes(diag_raw, birth_arr, death_arr, pers_arr, dim_label):
            dim1_flag = 1.0 if dim_label == 1 else 0.0
            dim2_flag = 1.0 if dim_label == 2 else 0.0
            for idx in range(len(birth_arr)):
                b = birth_arr[idx]
                d_val = death_arr[idx]
                p = pers_arr[idx]
                threshold = max(0.0, b * 0.9)
                # Celle >= threshold = prefisso di sorted_v (ordinato desc)
                n_above = int(np.searchsorted(-sorted_v, -threshold, side='right'))
                if n_above == 0:
                    cx = cy = cz = 0.5
                    tau_mean = 0.0
                else:
                    # Campiona al massimo MAX_BARY_CELLS celle (le più alte per valore)
                    n_use = min(n_above, MAX_BARY_CELLS)
                    c  = coords_all[:n_use]
                    w  = sorted_v[:n_use]
                    ws = float(w.sum())
                    cx = float((c[:, 0] * w).sum() / (ws * N_grid))
                    cy = float((c[:, 1] * w).sum() / (ws * N_grid))
                    cz = float((c[:, 2] * w).sum() / (ws * N_grid))
                    tau_mean = float(sorted_v[:n_above].mean())
                nodes_list.append([
                    b, d_val, p,
                    dim1_flag, dim2_flag,
                    float(tau_mean / (mu_lcdm + 1e-10)),
                    cx, cy, cz
                ])

        if len(res1) == 4:
            add_nodes(res1[0], res1[1], res1[2], res1[3], dim_label=1)
        if len(res2) == 4:
            add_nodes(res2[0], res2[1], res2[2], res2[3], dim_label=2)

        if len(nodes_list) == 0:
            # Campo degenere: crea un nodo dummy
            nodes_list = [[0.0] * 9]

        node_feats = np.array(nodes_list, dtype=np.float32)

        # Subsample a n_pts se necessario
        if len(node_feats) > n_pts:
            idx = np.random.choice(len(node_feats), n_pts, replace=False)
            node_feats = node_feats[idx]

        # k-NN graph in spazio (birth, death)
        bd = node_feats[:, :2]  # [N, 2]
        N  = len(bd)
        k  = min(k_nn, N - 1)
        if k <= 0:
            edge_index = np.zeros((2, 0), dtype=np.int64)
        else:
            # Distanza euclidea in spazio birth-death
            diff = bd[:, None, :] - bd[None, :, :]  # [N, N, 2]
            dist = np.sqrt((diff**2).sum(-1))         # [N, N]
            np.fill_diagonal(dist, np.inf)
            knn_idx = np.argsort(dist, axis=1)[:, :k]  # [N, k]
            src = np.repeat(np.arange(N), k)
            dst = knn_idx.flatten()
            # Bidirezionale
            edge_index = np.concatenate([
                np.stack([src, dst]),
                np.stack([dst, src])
            ], axis=1)

        return node_feats, edge_index

    # Inference su tutti i 2000 campi nwLH
    jstar_all = np.zeros((N_SIM, LATENT_DIM), dtype=np.float32)
    n_nodes_list = []
    t0 = time.time()

    with torch.no_grad():
        for i in range(N_SIM):
            # Carica campo τ
            # Formato: tau_field_XXXX.npz (da Phase 2)
            tau_file = TAU_DIR / f"tau_field_{i:04d}.npz"
            if not tau_file.exists():
                print(f"  [WARN] Campo τ non trovato per sim {i}: {tau_file}")
                continue

            tau_data = np.load(tau_file)
            tau = tau_data['tau_grid']  # [128,128,128] float32

            # Costruisci grafo
            # mu_lcdm e' salvato per campo (array [32]), usiamo la media come scalare
            mu_lcdm_field = float(tau_data['mu_lcdm'].mean())
            node_feats, edge_index = tau_to_graph(
                tau, P90, K_NN, N_PTS, BOXSIZE, mu_lcdm_field
            )
            n_nodes_list.append(len(node_feats))

            # PyG Data
            data = Data(
                x=torch.tensor(node_feats, dtype=torch.float32),
                edge_index=torch.tensor(edge_index, dtype=torch.long)
            ).to(device)

            # Inference
            j_star = model(data)  # [1, 32]
            jstar_all[i] = j_star.cpu().numpy().flatten()

            if (i + 1) % 10 == 0 or i == 0:
                elapsed = time.time() - t0
                t_per = elapsed / (i + 1)
                eta_h = t_per * (N_SIM - i - 1) / 3600
                print(f"  {i+1:4d}/{N_SIM} | t/campo={t_per:.1f}s | "
                      f"ETA={eta_h:.1f}h | nodes_mean={np.mean(n_nodes_list):.0f}", flush=True)

    elapsed_total = time.time() - t0
    n_nonzero = (np.abs(jstar_all).sum(axis=1) > 0).sum()
    print(f"\n  Completato in {elapsed_total/60:.1f} min")
    print(f"  Campi processati: {n_nonzero}/{N_SIM}")
    print(f"  j* shape: {jstar_all.shape}")
    print(f"  j* mean norm: {np.linalg.norm(jstar_all, axis=1).mean():.4f}")

    # Salva j*
    np.savez(JSTAR_FILE,
             jstar=jstar_all,
             w0=w0_all, Omm=Omm_all, s8=s8_all,
             checkpoint_epoch=BEST_EPOCH,
             p90=P90, k_nn=K_NN,
             n_nodes_mean=float(np.mean(n_nodes_list)) if n_nodes_list else 0.0)
    print(f"  Salvato: {JSTAR_FILE}")

# ---------------------------------------------------------------------------
# FASE 2: Correlazione parziale r(j*, w0 | Omm, s8)
# ---------------------------------------------------------------------------
if args.mode in ["full", "corr_only"]:
    print(f"\n{'='*70}")
    print("FASE 2 — Correlazione parziale r(j*, w0 | Omm, s8)")
    print(f"{'='*70}")

    assert JSTAR_FILE.exists(), f"j* non trovato: {JSTAR_FILE}. Eseguire prima --mode extract_only"
    data_j = np.load(JSTAR_FILE)
    jstar  = data_j['jstar']       # [2000, 32]
    w0_j   = data_j['w0']
    Omm_j  = data_j['Omm']
    s8_j   = data_j['s8']

    # Escludi sim con j*=0 (campo τ mancante)
    valid = np.abs(jstar).sum(axis=1) > 0
    N_valid = valid.sum()
    print(f"  Sim valide (j* non nullo): {N_valid}/{N_SIM}")

    jstar_v = jstar[valid]
    w0_v    = w0_j[valid]
    Omm_v   = Omm_j[valid]
    s8_v    = s8_j[valid]

    X = np.column_stack([np.ones(N_valid), Omm_v, s8_v])
    rw = w0_v - X @ np.linalg.lstsq(X, w0_v, rcond=None)[0]

    # Correlazione parziale per ciascuna delle 32 componenti j*
    print(f"\n  Correlazione parziale r(j*_k, w0 | Omm, s8) per k=1..32:")
    r_components = np.zeros(LATENT_DIM)
    for k in range(LATENT_DIM):
        jk = jstar_v[:, k]
        if jk.std() < 1e-10:
            continue
        rjk = jk - X @ np.linalg.lstsq(X, jk, rcond=None)[0]
        r_components[k] = float(pearsonr(rjk, rw)[0])

    max_r_idx = np.argmax(np.abs(r_components))
    max_r_val = float(r_components[max_r_idx])
    print(f"  max|r(j*_k, w0)| = {abs(max_r_val):.4f} (componente k={max_r_idx})")
    print(f"  Top 5 componenti per |r|:")
    top5 = np.argsort(np.abs(r_components))[::-1][:5]
    for k in top5:
        print(f"    k={k:2d}: r={r_components[k]:+.4f}")

    # Permutation test su componente più informativa
    best_k = max_r_idx
    jk_best = jstar_v[:, best_k]
    rjk_best = jk_best - X @ np.linalg.lstsq(X, jk_best, rcond=None)[0]
    r_obs_k = float(pearsonr(rjk_best, rw)[0])
    nulls_k = np.array([pearsonr(rjk_best, rng.permutation(rw))[0]
                        for _ in range(args.n_perm)])
    sigma_best_k = (abs(r_obs_k) - abs(nulls_k.mean())) / nulls_k.std()

    print(f"\n  Permutation test N={args.n_perm} su j*_{best_k}:")
    print(f"    r_obs = {r_obs_k:.4f}  sigma = {sigma_best_k:.2f}σ")

    # Combinazione ottimale delle 32 componenti j*
    good_k = [k for k in range(LATENT_DIM) if jstar_v[:, k].std() > 1e-10]
    RF_j = np.column_stack([
        jstar_v[:, k] - X @ np.linalg.lstsq(X, jstar_v[:, k], rcond=None)[0]
        for k in good_k
    ])
    beta_j = np.linalg.lstsq(RF_j, rw, rcond=None)[0]
    comb_j = RF_j @ beta_j
    r_comb_j = float(pearsonr(comb_j, rw)[0])
    nulls_cj = np.array([pearsonr(comb_j, rng.permutation(rw))[0]
                         for _ in range(args.n_perm)])
    sigma_comb_j = (abs(r_comb_j) - abs(nulls_cj.mean())) / nulls_cj.std()

    print(f"\n  Combinazione ottimale 32 componenti j*:")
    print(f"    r_comb = {r_comb_j:.4f}  sigma = {sigma_comb_j:.2f}σ")

    # Confronto Ramo A (TDA) vs Ramo B (j*)
    print(f"\n{'='*70}")
    print("CONFRONTO Ramo A (TDA) vs Ramo B (j*)")
    print(f"{'='*70}")

    val_file = ROOT / "results" / "phase5_validation_checks.json"
    if val_file.exists():
        with open(val_file) as f:
            val = json.load(f)
        sigma_A_b2   = val["feature_sigmas"]["b2_mean_persistence"]["sigma"]
        sigma_A_comb = val["sigma_reference_ols"]
        sigma_A_safe = val["tests"]["T2_ngal_contamination"]["sigma_tda_controlling_ngal"]

        print(f"  Ramo A TDA (b2_mean_persistence):  {sigma_A_b2:.2f}σ")
        print(f"  Ramo A TDA (6 feature combinate):  {sigma_A_comb:.2f}σ")
        print(f"  Ramo A TDA (conservativo):         {sigma_A_safe:.2f}σ")
        print(f"  Ramo B j* (componente migliore):   {sigma_best_k:.2f}σ")
        print(f"  Ramo B j* (32 componenti comb.):   {sigma_comb_j:.2f}σ")

        # Confronto sullo stesso campione (tutti i 2000 validi)
        better_ramo = "A" if sigma_A_b2 > sigma_best_k else "B"
        print(f"\n  Ramo dominante (feature singola): Ramo {better_ramo}")

        # Combinazione A+B (se informazione indipendente)
        b3_file = ROOT / "results" / "phase5_hod_b3_features.npz"
        if b3_file.exists():
            b3_data   = np.load(b3_file, allow_pickle=True)
            fvecs_b3  = b3_data['fvecs_hod_b3']
            b2_b3     = fvecs_b3[valid, 5]  # b2_mean_persistence sui validi
            rb2       = b2_b3 - X @ np.linalg.lstsq(X, b2_b3, rcond=None)[0]
            r_ab      = float(pearsonr(rb2, rjk_best)[0])
            print(f"\n  r(Ramo_A_b2, Ramo_B_j*) = {r_ab:.4f}")
            if abs(r_ab) < 0.3:
                print(f"  -> Rami A e B portano informazione INDIPENDENTE")
                print(f"  -> La combinazione A+B sara > max(A, B)")
            else:
                print(f"  -> Correlazione moderata A-B: informazione parzialmente sovrapposta")

            # Combinazione A+B
            RF_ab = np.column_stack([rb2.reshape(-1, 1), comb_j.reshape(-1, 1)])
            beta_ab = np.linalg.lstsq(RF_ab, rw, rcond=None)[0]
            comb_ab = RF_ab @ beta_ab
            nulls_ab = np.array([pearsonr(comb_ab, rng.permutation(rw))[0]
                                  for _ in range(args.n_perm)])
            sigma_ab = (abs(pearsonr(comb_ab,rw)[0]) - abs(nulls_ab.mean())) / nulls_ab.std()
            print(f"\n  Combinazione A+B: sigma = {sigma_ab:.2f}σ")
    else:
        sigma_A_b2 = sigma_A_comb = sigma_A_safe = None
        print("  Phase 5 validation checks non trovati.")

    # Salva risultati
    results = {
        "schema_version": "2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_sim_valid": int(N_valid),
        "checkpoint_epoch": BEST_EPOCH,
        "p90_frozen": P90,
        "k_nn_frozen": K_NN,
        "n_perm": args.n_perm,
        "j_star_dim": LATENT_DIM,
        "r_components": r_components.tolist(),
        "best_component_k": int(best_k),
        "r_best_component": float(r_obs_k),
        "sigma_best_component": float(sigma_best_k),
        "sigma_combination_32": float(sigma_comb_j),
        "sigma_ramo_a_b2": float(sigma_A_b2) if sigma_A_b2 else None,
        "sigma_ramo_a_combination": float(sigma_A_comb) if sigma_A_comb else None,
        "sigma_ramo_a_conservative": float(sigma_A_safe) if sigma_A_safe else None,
        "sigma_combination_ab": float(sigma_ab) if 'sigma_ab' in dir() else None,
        "r_correlation_a_b": float(r_ab) if 'r_ab' in dir() else None,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*70}")
    print("RIEPILOGO RAMO B")
    print(f"{'='*70}")
    print(f"  j* componente migliore: sigma = {sigma_best_k:.2f}σ (k={best_k})")
    print(f"  j* combinazione 32:     sigma = {sigma_comb_j:.2f}σ")
    if sigma_A_b2:
        print(f"  TDA b2_mean_persistence: sigma = {sigma_A_b2:.2f}σ")
        print(f"  Combinazione A+B:        sigma = {sigma_ab:.2f}σ" if 'sigma_ab' in dir() else "")
    print(f"\n  Output: {JSTAR_FILE}")
    print(f"  Risultati: {OUTPUT_FILE}")
    print(f"{'='*70}")

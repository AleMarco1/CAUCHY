#!/usr/bin/env python3
"""
CAUCHY Phase 4 — Opening Script
=================================
Chiude gli impegni obbligatori R3-1, R3-2, R3-3 prima dell'avvio del
Symbolic Regression (Phase 4 SR).

Struttura dati verificata:
  results/graphs_cache/lhc/tau_field_NNNN_graph.npz  — 2000 grafi LHC cachati
  results/graphs_cache/nwlh/tau_field_NNNN_graph.npz — 2000 grafi nwLH cachati
      keys: x [N_nodes,9], edge_index [2,E], meta [4]

Outputs:
  results/phase4_opening_stats.json  — R3-1 + R3-2
  results/phase4_mmd_w0.json         — R3-3

Uso:
  python src/phase4_opening.py \
      --repo-root . \
      --data-root . \
      [--mmd-permutations 1000] \
      [--device cuda]
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("phase4_opening")


# ─────────────────────────────────────────────
# 1.  CLI
# ─────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="CAUCHY Phase 4 Opening")
    p.add_argument("--repo-root", type=str, default=".")
    p.add_argument("--data-root", type=str, default=".")
    p.add_argument("--mmd-permutations", type=int, default=1000)
    p.add_argument("--device", type=str, default="cuda", choices=["cuda", "cpu"])
    return p.parse_args()


# ─────────────────────────────────────────────
# 2.  ASSERT GATE3 PRIOR
# ─────────────────────────────────────────────

def verify_gate3_prior(repo_root: Path) -> dict:
    for candidate in [
        repo_root / "prior" / "gate3_prior_v1_0.json",
        repo_root / "gate3_prior_v1_0.json",
    ]:
        if candidate.exists():
            prior_path = candidate
            break
    else:
        raise FileNotFoundError("gate3_prior_v1_0.json non trovato")

    with open(prior_path) as f:
        prior = json.load(f)

    assert prior["frozen_gnn_training"]["best_epoch"] == 171
    assert prior["frozen_gnn_training"]["split_seed"] == 42
    assert prior["frozen_graph_construction"]["persistence_threshold_p90"] == \
        0.35589513778686577

    log.info("  [ASSERT OK] gate3_prior: epoch=171, seed=42, p90=0.35589...")
    return prior


# ─────────────────────────────────────────────
# 3.  CARICAMENTO GNN — importa da phase3_gnn.py
#     Unica fonte di verita' per l'architettura.
# ─────────────────────────────────────────────

def load_gnn(checkpoint_path: Path, repo_root: Path, device):
    """
    Importa build_gnn_model direttamente da src/phase3_gnn.py
    e carica il checkpoint frozen. Nessuna ridefinizione dell'architettura.
    """
    import importlib.util
    import torch

    gnn_script = repo_root / "src" / "phase3_gnn.py"
    if not gnn_script.exists():
        raise FileNotFoundError(f"phase3_gnn.py non trovato: {gnn_script}")

    spec   = importlib.util.spec_from_file_location("phase3_gnn", gnn_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    model, backend = module.build_gnn_model(
        n_features=9, hidden_dim=64, latent_dim=32, n_layers=3, n_out=2
    )
    log.info(f"  backend: {backend}")

    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
        model.load_state_dict(ckpt["model_state_dict"])
        log.info(f"  best_epoch={ckpt.get('best_epoch')}, "
                 f"val_loss={ckpt.get('best_val_loss', float('nan')):.6f}")
    elif isinstance(ckpt, dict) and "state_dict" in ckpt:
        model.load_state_dict(ckpt["state_dict"])
    else:
        model.load_state_dict(ckpt)

    model.to(device)
    model.eval()
    n = sum(p.numel() for p in model.parameters())
    assert n == 13442, f"Parametri inattesi: {n} (atteso 13442)"
    log.info(f"  GNN caricato da phase3_gnn.build_gnn_model: {n} parametri OK")
    return model

# ─────────────────────────────────────────────
# 4.  CARICAMENTO GRAFI DALLA CACHE
#     LHC:  graphs_cache/lhc/tau_field_NNNN_graph.npz
#     nwLH: graphs_cache/nwlh/tau_field_NNNN_graph.npz
#     Keys: x [N,9], edge_index [2,E], meta [4]
# ─────────────────────────────────────────────

def load_cached_graph(subdir: Path, idx: int):
    """Carica il grafo idx dalla subdir della cache come torch_geometric Data."""
    import torch
    from torch_geometric.data import Data

    path = subdir / f"tau_field_{idx:04d}_graph.npz"
    if not path.exists():
        raise FileNotFoundError(f"Grafo non in cache: {path}")
    npz = np.load(path)
    return Data(
        x=torch.tensor(npz["x"], dtype=torch.float32),
        edge_index=torch.tensor(npz["edge_index"], dtype=torch.long),
    )


def extract_j_star(model, indices, cache_subdir: Path, device, batch_size=32, label=""):
    """Estrae j* [len(indices), 32] dai grafi cachati in cache_subdir."""
    import torch
    from torch_geometric.data import Batch

    j_stars = []
    n = len(indices)
    with torch.no_grad():
        for start in range(0, n, batch_size):
            end    = min(start + batch_size, n)
            graphs = [load_cached_graph(cache_subdir, int(i)) for i in indices[start:end]]
            batch  = Batch.from_data_list(graphs).to(device)
            _, j   = model(batch.x, batch.edge_index, batch.batch)
            j_stars.append(j.cpu().numpy())
            if start % (batch_size * 10) == 0:
                log.info(f"    [{end}/{n}] {label} estratti...")
    return np.concatenate(j_stars, axis=0)


# ─────────────────────────────────────────────
# 6.  SPLIT LHC (riproduce Phase 3 esattamente)
# ─────────────────────────────────────────────

def get_lhc_split(n_total=2000, n_train=1600, seed=42):
    rng = np.random.default_rng(seed)
    idx = np.arange(n_total)
    rng.shuffle(idx)
    return np.sort(idx[:n_train]), np.sort(idx[n_train:])


# ─────────────────────────────────────────────
# 7.  R3-1 + R3-2
# ─────────────────────────────────────────────

def compute_r31_r32(model, cache_lhc, fiducial_cache, device):
    from scipy.stats import pearsonr
    from sklearn.linear_model import LinearRegression, Ridge

    log.info("Caricamento phase1_fiducial_cache.npz...")
    cache     = np.load(fiducial_cache)
    cosmo_lhc = cache["cosmo_lhc"]   # [2000,2]
    fvecs_lhc = cache["fvecs_lhc"]   # [2000,8]

    train_idx, test_idx = get_lhc_split()
    assert len(test_idx) == 400

    Omm_tr = cosmo_lhc[train_idx, 0];  s8_tr = cosmo_lhc[train_idx, 1]
    Omm_te = cosmo_lhc[test_idx,  0];  s8_te = cosmo_lhc[test_idx,  1]

    # Ramo B: j* dalla cache LHC
    log.info("Estrazione j* train LHC (1600)...")
    j_tr = extract_j_star(model, train_idx, cache_lhc, device, label="LHC train")
    log.info("Estrazione j* test LHC (400)...")
    j_te = extract_j_star(model, test_idx,  cache_lhc, device, label="LHC test")

    reg_O = LinearRegression().fit(j_tr, Omm_tr)
    reg_s = LinearRegression().fit(j_tr, s8_tr)
    r31_O, p31_O = pearsonr(reg_O.predict(j_te), Omm_te)
    r31_s, p31_s = pearsonr(reg_s.predict(j_te), s8_te)
    log.info(f"  R3-1  r(ŷ_Ωm) = {r31_O:.4f}  r(ŷ_σ₈) = {r31_s:.4f}")

    # Ramo A: Ridge su 8 feature TDA
    log.info("Ridge Ramo A (8 feature TDA)...")
    fvec_tr = fvecs_lhc[train_idx];  fvec_te = fvecs_lhc[test_idx]
    rA_O = Ridge(alpha=1.0).fit(fvec_tr, Omm_tr)
    rA_s = Ridge(alpha=1.0).fit(fvec_tr, s8_tr)
    r32_O, p32_O = pearsonr(rA_O.predict(fvec_te), Omm_te)
    r32_s, p32_s = pearsonr(rA_s.predict(fvec_te), s8_te)
    log.info(f"  R3-2  r(Ridge_Ωm) = {r32_O:.4f}  r(Ridge_σ₈) = {r32_s:.4f}")

    r2_B = (r31_O**2 + r31_s**2) / 2
    r2_A = (r32_O**2 + r32_s**2) / 2
    var_added = (r2_B - r2_A) / r2_A * 100 if r2_A > 0 else float("inf")
    log.info(f"  R² Ramo B={r2_B:.4f}  Ramo A={r2_A:.4f}  +{var_added:.1f}%")

    return {
        "R3_1_corrected_correlations": {
            "r_yhat_Omm_vs_Omm_true": float(r31_O), "p_yhat_Omm": float(p31_O),
            "r_yhat_s8_vs_s8_true":   float(r31_s), "p_yhat_s8":  float(p31_s),
            "r2_Omm": float(r31_O**2), "r2_s8": float(r31_s**2),
            "method": "r(Linear(j*), y_true) — Linear fit su 1600 LHC train seed=42",
        },
        "R3_2_variance_added_equivalent": {
            "r_ramoA_Ridge_Omm": float(r32_O), "p_ramoA_Ridge_Omm": float(p32_O),
            "r_ramoA_Ridge_s8":  float(r32_s), "p_ramoA_Ridge_s8":  float(p32_s),
            "r2_ramoA_Omm": float(r32_O**2), "r2_ramoA_s8": float(r32_s**2),
            "r2_ramoB_mean": float(r2_B), "r2_ramoA_mean": float(r2_A),
            "variance_added_equivalent_pct": float(var_added),
            "method": "stesso test set 400 LHC seed=42, r(yhat,ytrue), Ridge alpha=1.0",
        },
    }


# ─────────────────────────────────────────────
# 8.  R3-3  (MMD distribuzionale j* vs w₀)
# ─────────────────────────────────────────────

def rbf_mmd2(X, Y, bw):
    """MMD² U-statistic con kernel RBF(bw)."""
    def K(A, B):
        d2 = (np.sum(A**2, 1, keepdims=True)
              + np.sum(B**2, 1, keepdims=True).T
              - 2 * A @ B.T)
        return np.exp(-d2 / (2 * bw**2))
    Kxx = K(X, X); np.fill_diagonal(Kxx, 0)
    Kyy = K(Y, Y); np.fill_diagonal(Kyy, 0)
    n, m = len(X), len(Y)
    return float(Kxx.sum()/(n*(n-1)) + Kyy.sum()/(m*(m-1)) - 2*K(X,Y).mean())


def compute_r33_mmd(model, nwlh_cache_dir, fiducial_cache,
                    device, n_permutations=1000, w0_threshold=-1.0):
    from scipy.stats import pearsonr

    log.info("Caricamento cosmologie nwLH...")
    w0_all = np.load(fiducial_cache)["cosmo_nwlh"][:, 0]  # [2000]

    log.info("Caricamento grafi nwLH dalla cache (graphs_cache/nwlh/)...")
    J = extract_j_star(model, np.arange(2000), nwlh_cache_dir, device, label="nwLH")
    w0_valid = w0_all[:len(J)]

    mask_low  = w0_valid < w0_threshold
    mask_high = w0_valid >= w0_threshold
    X, Y = J[mask_low], J[mask_high]
    log.info(f"  w₀ < {w0_threshold}: {len(X)}  |  w₀ >= {w0_threshold}: {len(Y)}")

    # Bandwidth: median heuristic
    XY  = np.concatenate([X, Y])
    rng = np.random.default_rng(42)
    s   = XY[rng.choice(len(XY), min(500, len(XY)), replace=False)]
    d2  = np.sum(s**2, 1, keepdims=True) + np.sum(s**2, 1) - 2 * s @ s.T
    bw  = float(np.sqrt(np.median(d2[d2 > 0]) / 2))
    log.info(f"  Bandwidth: {bw:.4f}")

    mmd_obs = rbf_mmd2(X, Y, bw)
    log.info(f"  MMD² osservato: {mmd_obs:.6f}")

    # Permutation test
    log.info(f"  Permutation test ({n_permutations} iterazioni)...")
    rng2  = np.random.default_rng(42)
    XYa   = np.concatenate([X, Y])
    nx    = len(X)
    count = 0
    t0    = time.time()
    for i in range(n_permutations):
        p = rng2.permutation(len(XYa))
        if rbf_mmd2(XYa[p[:nx]], XYa[p[nx:]], bw) >= mmd_obs:
            count += 1
        if (i + 1) % 200 == 0:
            log.info(f"    {i+1}/{n_permutations} ({time.time()-t0:.0f}s)...")
    pvalue = (count + 1) / (n_permutations + 1)
    log.info(f"  p-value = {pvalue:.4f}")

    verdict = "SIGNIFICATIVO" if pvalue < 0.05 else "NON_SIGNIFICATIVO"
    interp  = (
        f"MMD²={mmd_obs:.6f} {'>' if verdict=='SIGNIFICATIVO' else 'non >'} 0 "
        f"(p={pvalue:.4f}). " + (
        "j* porta segnale distribuzionale su w₀ — Ramo B motivato per Phase 6."
        if verdict == "SIGNIFICATIVO" else
        "j* non mostra separazione distribuzionale su w₀. "
        "Il PI decide se Phase 6 è giustificata.")
    )
    log.info(f"  Verdetto: {verdict}")

    # Analisi |r(j*_k, w₀)| per k=0..31
    abs_r = [float(abs(pearsonr(J[:, k], w0_valid)[0])) for k in range(32)]
    top10 = list(map(int, np.argsort(abs_r)[::-1][:10]))
    log.info("  Top-5 componenti j* per |r| con w₀:")
    for rank in range(5):
        k = top10[rank]
        log.info(f"    j*[{k:2d}]  |r| = {abs_r[k]:.4f}")

    return {
        "n_fields_w0_low":  int(len(X)),
        "n_fields_w0_high": int(len(Y)),
        "n_fields_valid":   int(len(J)),
        "w0_threshold":     w0_threshold,
        "mmd_stat":         mmd_obs,
        "mmd_pvalue":       float(pvalue),
        "n_permutations":   n_permutations,
        "kernel":           "RBF",
        "kernel_bandwidth": float(bw),
        "verdict":          verdict,
        "interpretation":   interp,
        "feature_correlations_w0": {
            "abs_r_per_component":    abs_r,
            "top10_component_indices": top10,
            "top10_abs_r":            [abs_r[i] for i in top10],
        },
    }


# ─────────────────────────────────────────────
# 9.  MAIN
# ─────────────────────────────────────────────

def main():
    import torch
    args      = parse_args()
    repo_root = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()

    log.info("=" * 60)
    log.info("CAUCHY Phase 4 — Opening Script")
    log.info(f"  repo_root : {repo_root}")
    log.info(f"  data_root : {data_root}")
    log.info(f"  device    : {args.device}")
    log.info(f"  MMD perms : {args.mmd_permutations}")
    log.info("=" * 60)

    # 1. Prior
    log.info("[STEP 1] Verifica gate3_prior...")
    prior = verify_gate3_prior(repo_root)
    p90   = prior["frozen_graph_construction"]["persistence_threshold_p90"]

    # 2. Path
    ckpt_path      = data_root / "results" / "checkpoints" / "phase3_gnn_best.pt"
    cache_lhc      = data_root / "results" / "graphs_cache" / "lhc"
    cache_nwlh     = data_root / "results" / "graphs_cache" / "nwlh"
    fid_cache      = data_root / "results" / "phase1_fiducial_cache.npz"
    results_dir    = data_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    for path, label in [
        (ckpt_path,   "checkpoint GNN"),
        (cache_lhc,   "graphs_cache/lhc"),
        (cache_nwlh,  "graphs_cache/nwlh"),
        (fid_cache,   "phase1_fiducial_cache.npz"),
    ]:
        if not path.exists():
            log.error(f"Non trovato: {label} — {path}")
            sys.exit(1)
        log.info(f"  [OK] {label}")

    n_lhc  = len(list(cache_lhc.glob("tau_field_*_graph.npz")))
    n_nwlh = len(list(cache_nwlh.glob("tau_field_*_graph.npz")))
    log.info(f"  Grafi in cache: LHC={n_lhc} nwLH={n_nwlh} (attesi 2000 ciascuno)")

    # 3. Device
    if args.device == "cuda" and not torch.cuda.is_available():
        log.warning("CUDA non disponibile — uso CPU")
        device = torch.device("cpu")
    else:
        device = torch.device(args.device)

    # 4. GNN
    log.info("[STEP 2] Caricamento GNN frozen...")
    model = load_gnn(ckpt_path, repo_root, device)

    # 5. R3-1 + R3-2
    log.info("[STEP 3] R3-1 + R3-2...")
    t0 = time.time()
    r31_r32 = compute_r31_r32(model, cache_lhc, fid_cache, device)
    log.info(f"  Completati in {time.time()-t0:.1f}s")

    out_stats = results_dir / "phase4_opening_stats.json"
    with open(out_stats, "w") as f:
        json.dump({
            "schema_version": "2.0",
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "gate":           "GATE_4_apertura",
            "script":         "src/phase4_opening.py",
            "gate3_prior_verified": {
                "best_epoch":  prior["frozen_gnn_training"]["best_epoch"],
                "split_seed":  prior["frozen_gnn_training"]["split_seed"],
                "p90_threshold": p90,
            },
            **r31_r32,
        }, f, indent=2)
    log.info(f"  [SALVATO] {out_stats}")

    # 6. R3-3
    log.info("[STEP 4] R3-3: MMD nwLH (dalla cache graphs_cache/nwlh/)...")
    t0 = time.time()
    mmd = compute_r33_mmd(
        model, cache_nwlh, fid_cache,
        device, n_permutations=args.mmd_permutations,
    )
    log.info(f"  Completato in {time.time()-t0:.1f}s")

    out_mmd = results_dir / "phase4_mmd_w0.json"
    with open(out_mmd, "w") as f:
        json.dump({
            "schema_version": "2.0",
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "gate":           "GATE_4_apertura",
            "script":         "src/phase4_opening.py",
            "gate3_prior_verified": {
                "best_epoch": prior["frozen_gnn_training"]["best_epoch"],
                "split_seed": prior["frozen_gnn_training"]["split_seed"],
            },
            **mmd,
        }, f, indent=2)
    log.info(f"  [SALVATO] {out_mmd}")

    # 7. Sommario
    r31 = r31_r32["R3_1_corrected_correlations"]
    r32 = r31_r32["R3_2_variance_added_equivalent"]
    log.info("=" * 60)
    log.info("SOMMARIO PHASE 4 OPENING")
    log.info(f"  R3-1  r(ŷ_Ωm) = {r31['r_yhat_Omm_vs_Omm_true']:.4f}")
    log.info(f"  R3-1  r(ŷ_σ₈) = {r31['r_yhat_s8_vs_s8_true']:.4f}")
    log.info(f"  R3-2  r(Ridge_Ωm) = {r32['r_ramoA_Ridge_Omm']:.4f}")
    log.info(f"  R3-2  r(Ridge_σ₈) = {r32['r_ramoA_Ridge_s8']:.4f}")
    log.info(f"  R3-2  varianza aggiuntiva = {r32['variance_added_equivalent_pct']:.1f}%")
    log.info(f"  R3-3  MMD² = {mmd['mmd_stat']:.6f}  p = {mmd['mmd_pvalue']:.4f}")
    log.info(f"  R3-3  verdetto = {mmd['verdict']}")
    log.info("=" * 60)
    log.info("Riporta phase4_opening_stats.json e phase4_mmd_w0.json nella sessione 2.")


if __name__ == "__main__":
    main()

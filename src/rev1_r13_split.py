"""
CAUCHY — MN-26-2100-P revision, referee point R1.3 (addendum)
src/rev1_r13_split.py

Freezes the three-way split of the deficit in normalised persistence. It reads
results/revision/rev1_r13_beta1curve.npz and recomputes nothing: no filtration
is run, so this takes seconds. Its only job is to put the numbers quoted in
Section 5.2 into a frozen record of their own, with the bin boundaries declared
explicitly rather than chosen after looking at the answer.

Boundaries, both fixed by the histogram rather than by the result:
  * the lower edge is the first bin of the persistence histogram, i.e. the
    near-diagonal population that a superlevel filtration of a noisy field
    always produces;
  * the upper edge is the top of the occupied range as defined in the main run
    (mock mean above `occ_frac` of the peak bin), beyond which the mock
    histogram is too sparse for a per-bin comparison.

  python src\\rev1_r13_split.py

Output: results/revision/rev1_r13_persistence_split.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

OUT_DIR = Path.cwd() / "results" / "revision"
NPZ = OUT_DIR / "rev1_r13_beta1curve.npz"
SRC_JSON = OUT_DIR / "rev1_r13_beta1curve.json"

if not NPZ.exists() or not SRC_JSON.exists():
    raise SystemExit(f"[ERRORE] servono {NPZ.name} e {SRC_JSON.name} in {OUT_DIR}")

z = np.load(NPZ)
main = json.loads(SRC_JSON.read_text(encoding="utf-8"))
rec = main["decompositions"]["pers_sigma_normalised"]

centres = np.array(rec["bin_centres"])
edges = z["edges_pn"]
D = z["desi_pers_n"].astype(float)
M = z["mock_pers_n"].astype(float).mean(axis=0)

lo_edge = float(edges[1])                      # top of the first bin
hi_edge = float(rec["occupied_range"][1])      # top of the occupied range

near = centres <= lo_edge
bulk = (centres > lo_edge) & (centres <= hi_edge)
tail = centres > hi_edge

out = {
    "source": {"npz": NPZ.name, "json": SRC_JSON.name,
               "n_mocks": main["n_mocks"]},
    "boundaries_p_over_sigma": {"near_diagonal_upper": lo_edge,
                                "bulk_upper": hi_edge},
    "near_diagonal": {"desi": float(D[near].sum()), "mock": float(M[near].sum()),
                      "desi_minus_mock": float(D[near].sum() - M[near].sum())},
    "bulk": {"desi": float(D[bulk].sum()), "mock": float(M[bulk].sum()),
             "mock_minus_desi": float(M[bulk].sum() - D[bulk].sum())},
    "persistent_tail": {"desi": float(D[tail].sum()), "mock": float(M[tail].sum()),
                        "desi_minus_mock": float(D[tail].sum() - M[tail].sum())},
    "total_deficit_from_split": float(M.sum() - D.sum()),
    "total_deficit_main_run": main["total_deficit"],
}
out["split_closes"] = bool(
    abs(out["total_deficit_from_split"] - out["total_deficit_main_run"]) < 1.0)

print("=" * 68)
print("R1.3 — split in persistenza normalizzata")
print("=" * 68)
print(f"  confini p/sigma: near-diagonal <= {lo_edge:.4f}, bulk <= {hi_edge:.4f}")
print(f"  near-diagonal   DESI {out['near_diagonal']['desi']:9.0f}  "
      f"mock {out['near_diagonal']['mock']:9.1f}  "
      f"ECCESSO {out['near_diagonal']['desi_minus_mock']:+9.1f}")
print(f"  bulk            DESI {out['bulk']['desi']:9.0f}  "
      f"mock {out['bulk']['mock']:9.1f}  "
      f"DEFICIT {out['bulk']['mock_minus_desi']:+9.1f}")
print(f"  coda persistente DESI {out['persistent_tail']['desi']:8.0f}  "
      f"mock {out['persistent_tail']['mock']:9.1f}  "
      f"ECCESSO {out['persistent_tail']['desi_minus_mock']:+9.1f}")
print(f"  somma = {out['total_deficit_from_split']:.1f} "
      f"(deficit totale {out['total_deficit_main_run']:.1f}) -> "
      f"{'CHIUDE' if out['split_closes'] else 'NON CHIUDE'}")

out["timestamp"] = datetime.now(timezone.utc).isoformat()
out["script"] = "src/rev1_r13_split.py"
p = OUT_DIR / "rev1_r13_persistence_split.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\n[OUT] {p}")

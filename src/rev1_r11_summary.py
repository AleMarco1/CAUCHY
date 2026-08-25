"""
CAUCHY — MN-26-2100-P revision, referee point R1.1 (summary)
src/rev1_r11_summary.py

Combines the two frozen R1.1 records and fixes a labelling error in the pilot
output. `rev1_r11_pilot.json` carries a field
`geometric_expectation_if_var_scales_as_inverse_volume = 1.199`; that number is
the expected inflation of the REALISATION TERM, not of the total ensemble
scatter, and the pilot measures the total. The realisation term is only 13.4%
of the variance (Section 5.5), so the same assumption predicts an inflation of
the TOTAL scatter of about 1.03, not 1.20. Comparing the measured ratio against
1.199 would understate the agreement; this script recomputes the comparison on
the right quantity and freezes it.

It reads nothing but the two JSONs and runs in a second.

  python src\\rev1_r11_summary.py

Output: results/revision/rev1_r11_summary.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path

OUT_DIR = Path.cwd() / "results" / "revision"
T = json.loads((OUT_DIR / "rev1_r11_tiling.json").read_text(encoding="utf-8"))
P = json.loads((OUT_DIR / "rev1_r11_pilot.json").read_text(encoding="utf-8"))

if not P.get("null_gate_passed"):
    raise SystemExit("[STOP] il null gate del pilota non e' passato.")

sd_full = T["ensemble"]["std"]
deficit = T["ensemble"]["deficit"]
sd_corr = T["tiling_correction"]["sigma_total_corrected"]
expected_total_ratio = sd_corr / sd_full

meas = P["sigma_ratio"]
lo, hi = P["sigma_ratio_ci95"]

# Translate the measured ratio onto the full 2000-mock ensemble.
sd_hi = sd_full * hi
z_hi = -deficit / sd_hi
need3 = T["width_required"]["3sigma"]["sigma_total_growth_factor"]

out = {
    "sources": ["rev1_r11_tiling.json", "rev1_r11_pilot.json"],
    "null_gate_passed": True,
    "n_pilot_mocks": P["n_mocks_used"],
    "measured_sigma_ratio": meas,
    "measured_sigma_ratio_ci95": [lo, hi],
    "mean_shift_generators": P["mean_shift"],
    "expected_total_sigma_ratio_from_geometry": expected_total_ratio,
    "note_on_pilot_json_field": (
        "geometric_expectation_if_var_scales_as_inverse_volume=1.199 in "
        "rev1_r11_pilot.json refers to the realisation term alone; the "
        "corresponding expectation for the total scatter is the value of "
        "expected_total_sigma_ratio_from_geometry here."),
    "expectation_inside_measured_ci": bool(lo <= expected_total_ratio <= hi),
    "unity_inside_measured_ci": bool(lo <= 1.0 <= hi),
    "ensemble_sigma": sd_full,
    "ensemble_sigma_at_ci_upper": sd_hi,
    "z_at_ci_upper": z_hi,
    "sigma_growth_required_for_3sigma": need3,
    "margin_between_ci_upper_and_3sigma_requirement": need3 / hi,
}

print("=" * 70)
print("R1.1 — SINTESI")
print("=" * 70)
print(f"  null gate del pilota: passato")
print(f"  pilota N = {out['n_pilot_mocks']}")
print(f"  rapporto misurato sigma_rand/sigma_std = {meas:.3f} "
      f"[95% {lo:.3f}, {hi:.3f}]")
print(f"  atteso dalla geometria SUL TOTALE = {expected_total_ratio:.3f} "
      f"(dentro l'intervallo: {out['expectation_inside_measured_ci']})")
print(f"  unita' dentro l'intervallo: {out['unity_inside_measured_ci']}")
print(f"  spostamento della media: {out['mean_shift_generators']:+.1f} generatori")
print(f"  al limite superiore dell'intervallo: sigma {sd_full:.1f} -> "
      f"{sd_hi:.1f}, z {-deficit/sd_full:.2f} -> {z_hi:.2f}")
print(f"  servirebbe x{need3:.2f} per 3 sigma: il limite superiore misurato "
      f"e' {out['margin_between_ci_upper_and_3sigma_requirement']:.1f} volte "
      f"piu' basso")

out["timestamp"] = datetime.now(timezone.utc).isoformat()
out["script"] = "src/rev1_r11_summary.py"
p = OUT_DIR / "rev1_r11_summary.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\n[OUT] {p}")

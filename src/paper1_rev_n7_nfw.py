#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n7_nfw.py

N7 - PROFILO RADIALE DEI SATELLITI: UNIFORME CONTRO NFW

Referee 2 §5. L'editore chiede che il canale sia verificato oppure
quantitativamente limitato. Qui si fa entrambe le cose.

IL PROBLEMA
-----------
In phase8_test2_masked.populate_with_virial i satelliti sono collocati con

    u = rng.random(ns)
    r = r_vir * u ** (1.0 / 3.0)

che dà densità COSTANTE dentro il raggio viriale. Gli aloni reali seguono NFW,
molto più concentrato. E' un errore noto e per costruzione nella struttura
spaziale a piccola scala - cioè dove N2 colloca gran parte del deficit e dove
puntano i cinque diagnostici dello shot noise (curtosi mock +3.90 contro DESI
+0.20, molteplicità dei pareggi 52 contro 3, ecc.).

PARTE A - IL BOUND ANALITICO
----------------------------
r_vir è tipicamente ~1 Mpc/h, la lisciatura 5 Mpc/h, la cella 15.6 Mpc/h. La
ridistribuzione radiale avviene MOLTO sotto la scala di lisciatura, quindi entra
solo attraverso la varianza del profilo: al secondo ordine equivale a uno
spostamento della lisciatura efficace

    R_eff^2 = R^2 + <r^2>/3

con <r^2>_unif = (3/5) r_vir^2 e <r^2>_NFW molto minore. Convertendo con
l'indice locale della scansione di lisciatura (N_H1 ~ R^alpha, misurato fra R5
e R10) si ottiene un limite superiore su |Delta N_H1|.

Il bound è pesato sui satelliti, non sugli aloni: gli aloni massicci hanno più
satelliti E raggi viriali maggiori, quindi dominano.

PARTE B - IL TEST APPAIATO
--------------------------
Simmetria che rende il confronto esatto: il campionamento NFW consuma LO STESSO
numero di estrazioni casuali di quello uniforme - una `u` per satellite - quindi
il flusso del generatore resta allineato e l'unica differenza è la mappa
radiale. Stesso catalogo di aloni, stesso HOD, stesso carving, stessa
voxelizzazione. La differenza per mock è pulita e la varianza fra mock si
cancella nel confronto appaiato.

CANCELLO
--------
Grazie all'allineamento del generatore, la variante UNIFORME deve riprodurre
ESATTAMENTE il valore in per_mock_NGC_R5.jsonl per lo stesso indice. Se non lo
fa, sto chiamando la pipeline in modo diverso dal run congelato e mi fermo:
qualunque differenza misurata dopo sarebbe priva di significato.

USO
---
  python src\\paper1_rev_n7_nfw.py --k 3     # cancello + tempi
  python src\\paper1_rev_n7_nfw.py --k 40
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

NH1 = "base.N_H1"
MIN_IDX = 200
R_SMOOTH = 5.0
DEFICIT = 7181.5          # 35436.7 - 28256, per esprimere il bound in frazione


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=True, default=str)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_jsonl(path):
    recs = []
    if not Path(path).exists():
        return recs
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    return recs


def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")
        f.flush(); os.fsync(f.fileno())


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


# ---------------------------------------------------------------- NFW
def concentration(mass, z=0.3):
    """Duffy et al. 2008, aloni rilassati, definizione 200c."""
    return 5.71 * (np.maximum(mass, 1e9) / 2e12) ** (-0.084) * (1.0 + z) ** (-0.47)


def _mu(c):
    return np.log(1.0 + c) - c / (1.0 + c)


def nfw_radius(u, c, n_grid=512):
    """Inverte M(<r)/M(r_vir) = u per NFW. Restituisce x = r/r_vir in [0,1].
    Consuma ESATTAMENTE gli stessi `u` del caso uniforme: nessuna estrazione
    aggiuntiva, quindi il flusso del generatore resta allineato."""
    x = np.linspace(0.0, 1.0, n_grid)
    m = _mu(c * x) / _mu(c)
    m[0] = 0.0
    return np.interp(u, m, x)


def nfw_r2_mean(c, n_grid=4096):
    """<r^2>/r_vir^2 per NFW troncato a r_vir, pesato sulla massa."""
    x = np.linspace(1e-6, 1.0, n_grid)
    w = x / (1.0 + c * x) ** 2          # dM/dx ~ x/(1+cx)^2
    return float(np.trapezoid(w * x ** 2, x) / np.trapezoid(w, x))


# ---------------------------------------------------------------- popolamento
def populate(pos_h, mass_h, vel_h, hod, rng, M, T2, profile="uniform"):
    """Copia fedele di T2.populate_with_virial, con la sola mappa radiale
    parametrizzata. Stesso ordine e numero di estrazioni casuali."""
    (log_Mmin, sigma_logM, log_M0, log_M1, alpha,
     A_cen, A_sat, eta_vel, eta_conc) = hod
    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3)), np.zeros((0, 3))

    p_cen = np.clip(M.mean_Ncen(mass_h, log_Mmin, sigma_logM), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat = np.clip(M.mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin),
                      0.0, 1e4)
    n_sat = rng.poisson(lam_sat)

    pos_list, vel_list = [], []
    if is_central.any():
        pos_list.append(pos_h[is_central])
        vel_list.append(vel_h[is_central])

    rho_crit = 2.775e11 * M.OMM
    for i in range(N_h):
        ns = int(n_sat[i])
        if ns <= 0:
            continue
        r_vir = np.clip((3.0 * mass_h[i] /
                         (4.0 * np.pi * 200.0 * rho_crit)) ** (1.0 / 3.0),
                        0.01, 5.0) * eta_conc
        u = rng.random(ns)                       # <- estrazioni identiche
        if profile == "uniform":
            r = r_vir * u ** (1.0 / 3.0)
        else:
            r = r_vir * nfw_radius(u, concentration(mass_h[i]))
        theta = np.arccos(1.0 - 2.0 * rng.random(ns))
        phi = 2.0 * np.pi * rng.random(ns)
        dxyz = np.column_stack([r * np.sin(theta) * np.cos(phi),
                                r * np.sin(theta) * np.sin(phi),
                                r * np.cos(theta)])
        pos_list.append((pos_h[i] + dxyz) % M.BOXSIZE_MOCK)
        s1d = T2.sigma1d_virial(mass_h[i], r_vir) * eta_vel
        vel_list.append(vel_h[i][None, :] + rng.normal(0.0, s1d, size=(ns, 3)))

    if not pos_list:
        return np.zeros((0, 3)), np.zeros((0, 3))
    return np.vstack(pos_list), np.vstack(vel_list)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=40)
    ap.add_argument("--min_idx", type=int, default=MIN_IDX)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    outj = res / "paper1" / "n7_nfw_NGC.jsonl"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    import phase8_test2_masked as T2

    mask = np.load(M.DESI_MASK_FILE).astype(bool) \
        if Path(str(M.DESI_MASK_FILE)).exists() else \
        np.load(root / "data" / "processed" / "phase6_fields" /
                "bgs_ngc_mask_128.npy").astype(bool)

    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            kk = int(str(fl.get("key", j)).split("_")[-1])
        except (TypeError, ValueError):
            kk = j
        nh1[kk] = float(fl.get(NH1, np.nan))

    print("=" * 78)
    print("N7 - PROFILO DEI SATELLITI: UNIFORME CONTRO NFW")
    print("=" * 78)

    # ============================================================ A
    print("\n[A] BOUND ANALITICO")
    hod = M.HOD_MEDIAN
    eta_conc = hod[8]
    rho_crit = 2.775e11 * M.OMM

    # distribuzione di r_vir pesata sui SATELLITI, da alcuni cataloghi
    rv, wsat = [], []
    for i in range(args.min_idx, args.min_idx + 3):
        try:
            pos_h, mass_h, vel_h = M.read_halo_catalog(i, args.snapnum)
        except Exception as e:
            print(f"  [!] catalogo {i} non leggibile: {e}")
            continue
        if pos_h is None or len(pos_h) < 50:
            continue
        r = np.clip((3.0 * mass_h /
                     (4.0 * np.pi * 200.0 * rho_crit)) ** (1.0 / 3.0),
                    0.01, 5.0) * eta_conc
        lam = np.clip(M.mean_Nsat(mass_h, hod[2], hod[3], hod[4], hod[0]),
                      0.0, 1e4)
        rv.append(r); wsat.append(lam)
    if not rv:
        print("  [FATAL] nessun catalogo di aloni leggibile")
        return
    rv = np.concatenate(rv); wsat = np.concatenate(wsat)
    ok = wsat > 0
    rv, wsat = rv[ok], wsat[ok]
    w = wsat / wsat.sum()

    r2_unif = float(np.sum(w * 0.6 * rv ** 2))
    cs = concentration(np.full(rv.size, 1e13))  # placeholder, sostituito sotto
    # <r^2> NFW pesato: dipende dalla concentrazione, quindi dalla massa
    mass_from_r = (4.0 / 3.0) * np.pi * 200.0 * rho_crit * (rv / eta_conc) ** 3
    cs = concentration(mass_from_r)
    f_nfw = np.array([nfw_r2_mean(c) for c in np.clip(cs, 1.0, 20.0)])
    r2_nfw = float(np.sum(w * f_nfw * rv ** 2))

    print(f"  raggio viriale pesato sui satelliti: mediana "
          f"{np.median(np.repeat(rv, np.maximum(wsat.astype(int), 1))[:100000]):.3f}"
          f"  media pesata {np.sum(w*rv):.3f} Mpc/h")
    print(f"  concentrazione NFW (Duffy+08): mediana {np.median(cs):.2f}")
    print(f"  <r^2> uniforme = {r2_unif:.4f} (Mpc/h)^2")
    print(f"  <r^2> NFW      = {r2_nfw:.4f} (Mpc/h)^2")

    dR2 = (r2_unif - r2_nfw) / 3.0
    R_eff_u = np.sqrt(R_SMOOTH ** 2 + r2_unif / 3.0)
    R_eff_n = np.sqrt(R_SMOOTH ** 2 + r2_nfw / 3.0)
    dR_rel = (R_eff_u - R_eff_n) / R_SMOOTH
    print(f"\n  lisciatura efficace: uniforme {R_eff_u:.5f}, NFW {R_eff_n:.5f}"
          f"   (R = {R_SMOOTH})")
    print(f"  spostamento relativo: {100*dR_rel:.4f}%")

    # indice locale della scansione di lisciatura
    mirror = res / "paper1" / "paper1_mirror_lfl_NGC.json"
    alpha = None
    if mirror.exists():
        J = json.load(open(mirror, encoding="utf-8"))
        try:
            n5 = J["results"]["R5"]["mock_baseline_mean"]
            n10 = J["results"]["R10"]["mock_baseline_mean"]
            alpha = float(np.log(n10 / n5) / np.log(10.0 / 5.0))
            print(f"  indice della scansione: N_H1 ~ R^{alpha:.3f}  "
                  f"(da R5={n5:.0f}, R10={n10:.0f})")
        except Exception:
            pass
    if alpha is None:
        alpha = -1.24
        print(f"  indice non ricavabile dal file: uso alpha = {alpha}")

    dN = abs(alpha) * dR_rel * 35436.7
    print(f"\n  |Delta N_H1| stimato = {dN:.0f} generatori")
    print(f"  in frazione del deficit ({DEFICIT:.0f}): {100*dN/DEFICIT:.2f}%")
    print(f"\n  CAUTELA: l'indice è misurato fra R5 e R10, un intervallo ampio")
    print(f"  su cui la relazione non è una potenza pura. Il bound va inteso")
    print(f"  come ordine di grandezza, ed è per questo che serve la parte B.")

    boundA = {"r2_unif": r2_unif, "r2_nfw": r2_nfw,
              "R_eff_unif": float(R_eff_u), "R_eff_nfw": float(R_eff_n),
              "dR_rel": float(dR_rel), "alpha": alpha,
              "dN_stimato": float(dN),
              "frazione_deficit": float(dN / DEFICIT)}

    # ============================================================ B
    print("\n[B] TEST APPAIATO")
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    done = {r["idx"] for r in read_jsonl(outj)}
    t0 = time.time()
    n_run = 0

    for i in range(args.min_idx, args.min_idx + args.k):
        if i in done:
            continue
        try:
            pos_h, mass_h, vel_h = M.read_halo_catalog(i, args.snapnum)
        except Exception as e:
            print(f"  [!] catalogo {i}: {e}")
            continue
        if pos_h is None or len(pos_h) < 50:
            continue

        vals = {}
        for prof in ("uniform", "nfw"):
            rng = np.random.default_rng(args.seed + i)
            pg, vg = populate(pos_h, mass_h, vel_h, hod, rng, M, T2, prof)
            if len(pg) < 100:
                break
            ps = M.carve_cutsky(pg, vg, mask, nz_z, nz_target, rng)
            if ps is None or len(ps) < 100:
                break
            nu = M.voxelize_mock(ps, field_r, sum_wr, mask)
            if nu is None:
                break
            vals[prof] = float(M.compute_tda_features(
                nu, mask, M.N_THRESH, masked=True)[4])
            vals[prof + "_ngal"] = int(len(ps))
        if "uniform" not in vals or "nfw" not in vals:
            print(f"  [!] mock {i} scartato")
            continue

        exp = nh1.get(i, np.nan)
        ok_gate = np.isfinite(exp) and abs(vals["uniform"] - exp) < 0.5
        if n_run == 0:
            print(f"\n  CANCELLO sul primo mock (idx {i}):")
            print(f"    uniforme ricalcolato = {vals['uniform']:.0f}")
            print(f"    JSONL congelato      = {exp:.0f}")
            print(f"    {'OK: la pipeline è riprodotta esattamente' if ok_gate else '*** DISCORDE ***'}")
            if not ok_gate:
                print(f"    Sto chiamando la pipeline in modo diverso dal run")
                print(f"    congelato. Qualunque differenza misurata dopo")
                print(f"    sarebbe priva di significato. Mi fermo.")
                return

        append_jsonl(outj, {"idx": i, "uniform": vals["uniform"],
                            "nfw": vals["nfw"],
                            "delta": vals["nfw"] - vals["uniform"],
                            "ngal_unif": vals["uniform_ngal"],
                            "ngal_nfw": vals["nfw_ngal"],
                            "gate_ok": bool(ok_gate),
                            "jsonl": float(exp) if np.isfinite(exp) else None})
        n_run += 1
        el = time.time() - t0
        print(f"    idx {i}: unif={vals['uniform']:.0f}  nfw={vals['nfw']:.0f}"
              f"  delta={vals['nfw']-vals['uniform']:+.0f}"
              f"   {el/n_run:.0f} s/coppia")

    # ============================================================ analisi
    recs = read_jsonl(outj)
    if len(recs) < 3:
        print("\n  troppe poche coppie per l'analisi.")
        return
    d = np.array([r["delta"] for r in recs], float)
    u = np.array([r["uniform"] for r in recs], float)
    gates = [r.get("gate_ok") for r in recs if r.get("jsonl") is not None]

    print("\n" + "=" * 78)
    print("RISULTATO")
    print("=" * 78)
    print(f"  coppie: {len(recs)}   cancello superato su "
          f"{sum(1 for g in gates if g)}/{len(gates)}")
    print(f"  uniforme : {u.mean():.1f} +/- {u.std(ddof=1):.1f}")
    print(f"  differenza NFW - uniforme, appaiata:")
    sem = d.std(ddof=1) / np.sqrt(d.size)
    print(f"    media {d.mean():+.1f} +/- {sem:.1f}   "
          f"({d.mean()/sem if sem else 0:+.1f} sigma)")
    print(f"    sd delle differenze {d.std(ddof=1):.1f}  "
          f"(contro sd fra mock {u.std(ddof=1):.1f}: l'appaiamento cancella "
          f"{100*(1-d.std(ddof=1)/u.std(ddof=1)):.0f}% della varianza)")
    print(f"    range [{d.min():+.0f}, {d.max():+.0f}]")
    print(f"\n  in frazione del deficit: {100*d.mean()/DEFICIT:+.2f}%  "
          f"(+/- {100*sem/DEFICIT:.2f}%)")
    print(f"  bound analitico della parte A: {100*dN/DEFICIT:.2f}%")

    print("\n  LETTURA:")
    if abs(d.mean()) < 2 * sem:
        print("    La differenza è compatibile con zero: il profilo radiale dei")
        print("    satelliti NON contribuisce al deficit. Il canale è chiuso,")
        print("    come l'editore chiede in via principale.")
    elif abs(d.mean()) / DEFICIT < 0.05:
        print("    Differenza significativa ma piccola: il profilo sposta")
        print(f"    {100*abs(d.mean())/DEFICIT:.1f}% del deficit. Da quotare come")
        print("    contributo delimitato, non come spiegazione.")
    else:
        print("    Il profilo sposta una frazione SOSTANZIALE del deficit.")
        print("    Va rifatto l'ensemble con satelliti NFW prima di qualunque")
        print("    affermazione sul residuo oltre-due-punti, che va")
        print("    ricalcolato al netto di questo canale.")
    print(f"\n    Nota: questo test misura il profilo RADIALE a HOD fisso. Non")
    print(f"    copre una ri-calibrazione dell'HOD su un profilo NFW, che")
    print(f"    potrebbe compensare in parte. Da dichiarare come limite.")

    atomic_write_json(res / "paper1" / "n7_report_NGC.json", {
        "script": "paper1_rev_n7_nfw.py", "bound_analitico": boundA,
        "n_coppie": len(recs),
        "delta_media": float(d.mean()), "delta_sem": float(sem),
        "delta_sd": float(d.std(ddof=1)),
        "uniform_mean": float(u.mean()), "uniform_sd": float(u.std(ddof=1)),
        "frazione_deficit": float(d.mean() / DEFICIT),
        "cancello_superato": bool(all(gates)) if gates else None})
    print(f"\n  report: {res/'paper1'/'n7_report_NGC.json'}")


if __name__ == "__main__":
    main()

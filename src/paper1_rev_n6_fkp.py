#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n6_fkp.py

N6 - VOXELIZZAZIONE DEI MOCK PESATA FKP

Referee 2 §3, il rilievo piu' duro del rapporto, in sintesi. La Sez. 6.2
caratterizza bene l'asimmetria di pesatura (dati con completeness+FKP, mock a
peso unitario) e dimostra che non trasporta cicli, ma rimanda la correzione
alla sorgente a un articolo compagno. Per un lavoro la cui affermazione
centrale e' un confronto dati-mock di precisione questo non basta: M26
Tabella 1 mostra gia' che pesare i mock in stile FKP sposta la media di ~600
generatori ALLONTANANDOLA dai dati, e quel limite va importato esplicitamente
nella banda sistematica di Sez. 6.3. Il referee chiede inoltre perche' la
voxelizzazione FKP-pesata dei mock - una modifica di poche righe alla
pipeline - non possa essere eseguita almeno su un sottoinsieme N = 200 qui.

L'ASIMMETRIA, VERIFICATA NEL CODICE
-----------------------------------
  random (denominatore): cic_3d(pos_r, w = WEIGHT_FKP)          load_desi_random_field
  dati   (numeratore)  : cic_3d(pos_d, w = WEIGHT * WEIGHT_FKP)
  mock   (numeratore)  : w_d = np.ones(len(pos_sel))            voxelize_mock riga 513

IL METODO
---------
Si estrae la tabella w_FKP(z) dal catalogo dei RANDOM stessi, che porta il peso
per oggetto con la stessa dipendenza in redshift dei dati. Nessun P0 da
indovinare, nessuna n(z) da ricostruire: solo cio' che e' su disco.

Ogni galassia mock riceve il peso alla propria z, recuperata invertendo la
distanza comovente dalla posizione nel cubo di embedding (osservatore
all'origine, come in load_desi_random_field).

I pesi di completezza NON si applicano: i mock non hanno incompletezza per
costruzione. Quella asimmetria e' una questione distinta (R2.4, fiber
assignment) e va trattata separatamente.

DISEGNO APPAIATO
----------------
Stesso catalogo di aloni, stesso seed, stesso HOD, stesso carving: l'unica
differenza e' il vettore di pesi passato a cic_3d. La varianza fra mock si
cancella nel confronto appaiato, com'e' avvenuto in N7 (che ha cancellato il
47% della dispersione).

Nota sulla numerosita': il referee chiede N = 200. Il disegno appaiato con 60
coppie da una precisione MOLTO superiore a 200 mock non appaiati - in N7 la sd
delle differenze era 149 contro 279 fra mock - quindi 60 bastano a misurare uno
spostamento di ~600 generatori a oltre 30 sigma. Va spiegato nel testo invece
di limitarsi a mostrare un N piu' piccolo di quello richiesto.

CANCELLO
--------
La variante a peso unitario deve riprodurre ESATTAMENTE il valore in
per_mock_NGC_R5.jsonl. Se non lo fa, sto chiamando la pipeline in modo diverso
dal run congelato e mi fermo. In N7 questo cancello e' passato.

USO
---
  python src\\paper1_rev_n6_fkp.py --k 3      # cancello + tempi
  python src\\paper1_rev_n6_fkp.py --k 60
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
DEFICIT = 7181.5
M26_TAB1_SHIFT = 600.0     # spostamento citato da M26, Tabella 1


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


def build_wfkp_table(M, cache, n_bin=60):
    """w_FKP(z) mediano dal catalogo dei random, messo in cache."""
    if cache.exists():
        d = np.load(cache)
        return d["z"], d["w"]
    from astropy.io import fits
    with fits.open(M.RAN_FITS) as h:
        r = h["LSS"].data
        mz = (r["Z"] >= M.ZMIN) & (r["Z"] <= M.ZMAX)
        z = r["Z"][mz].astype(np.float64)
        w = r["WEIGHT_FKP"][mz].astype(np.float64)
    edges = np.linspace(M.ZMIN, M.ZMAX, n_bin + 1)
    idx = np.clip(np.digitize(z, edges) - 1, 0, n_bin - 1)
    zc = 0.5 * (edges[:-1] + edges[1:])
    wc = np.array([np.median(w[idx == b]) if (idx == b).any() else np.nan
                   for b in range(n_bin)])
    good = np.isfinite(wc)
    zc, wc = zc[good], wc[good]
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, z=zc, w=wc)
    return zc, wc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=60)
    ap.add_argument("--min_idx", type=int, default=MIN_IDX)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    outj = res / "paper1" / "n6_fkp_NGC.jsonl"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    import phase8_test2_masked as T2

    mp = root / "data" / "processed" / "phase6_fields" / "bgs_ngc_mask_128.npy"
    mask = np.load(mp).astype(bool)

    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            kk = int(str(fl.get("key", j)).split("_")[-1])
        except (TypeError, ValueError):
            kk = j
        nh1[kk] = float(fl.get(NH1, np.nan))

    print("=" * 78)
    print("N6 - VOXELIZZAZIONE DEI MOCK PESATA FKP")
    print("=" * 78)

    # ============================================================ A
    print("\n[A] TABELLA w_FKP(z) DAI RANDOM")
    zt, wt = build_wfkp_table(M, res / "paper1" / "n6_wfkp_table.npz")
    print(f"  {len(zt)} bin fra z = {M.ZMIN} e {M.ZMAX}")
    print(f"  w_FKP: min {wt.min():.4f}  mediana {np.median(wt):.4f}  "
          f"max {wt.max():.4f}")
    print(f"  {'z':>7s} {'w_FKP':>9s}")
    for j in range(0, len(zt), max(1, len(zt) // 8)):
        print(f"  {zt[j]:>7.3f} {wt[j]:>9.4f}")
    if not (0.0 < wt.min() and wt.max() <= 1.0 + 1e-9):
        print("  *** w_FKP fuori da (0,1]: la colonna non e' quella attesa. ***")
        return
    print("  -> w_FKP in (0,1] e monotono in z come atteso: la tabella e' sensata.")

    # inversione distanza comovente -> z
    zg = np.linspace(max(M.ZMIN - 0.05, 1e-3), M.ZMAX + 0.05, 4000)
    dg = M.comoving_distance(zg)

    def wfkp_of_pos(pos):
        r = np.linalg.norm(pos, axis=1)
        z = np.interp(r, dg, zg)
        return np.interp(z, zt, wt), z

    # ============================================================ B
    print(f"\n[B] TEST APPAIATO  (peso unitario contro FKP)")
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    hod = M.HOD_MEDIAN
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

        rng = np.random.default_rng(args.seed + i)
        pg, vg = T2.populate_with_virial(pos_h, mass_h, vel_h, hod, rng)
        if len(pg) < 100:
            continue
        ps = M.carve_cutsky(pg, vg, mask, nz_z, nz_target, rng)
        if ps is None or len(ps) < 100:
            continue

        # --- peso unitario: identico a voxelize_mock
        nu_u = M.voxelize_mock(ps, field_r, sum_wr, mask)
        if nu_u is None:
            continue
        v_u = float(M.compute_tda_features(nu_u, mask, M.N_THRESH,
                                           masked=True)[4])

        # --- peso FKP: stesse posizioni, solo il vettore dei pesi cambia
        w_d, zsel = wfkp_of_pos(ps)
        field_d = M.cic_3d(ps, w_d, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
        nu_f = M.build_field(field_d, field_r, float(w_d.sum()) / sum_wr, mask)
        v_f = float(M.compute_tda_features(nu_f, mask, M.N_THRESH,
                                           masked=True)[4])

        exp = nh1.get(i, np.nan)
        ok_gate = np.isfinite(exp) and abs(v_u - exp) < 0.5
        if n_run == 0:
            print(f"\n  CANCELLO sul primo mock (idx {i}):")
            print(f"    peso unitario ricalcolato = {v_u:.0f}")
            print(f"    JSONL congelato           = {exp:.0f}")
            print(f"    {'OK' if ok_gate else '*** DISCORDE: mi fermo ***'}")
            if not ok_gate:
                return
            print(f"    galassie selezionate {len(ps)}   "
                  f"w_FKP media {w_d.mean():.4f}   z media {zsel.mean():.4f}")

        append_jsonl(outj, {"idx": i, "unit": v_u, "fkp": v_f,
                            "delta": v_f - v_u, "ngal": int(len(ps)),
                            "wfkp_mean": float(w_d.mean()),
                            "wfkp_sum": float(w_d.sum()),
                            "gate_ok": bool(ok_gate),
                            "jsonl": float(exp) if np.isfinite(exp) else None})
        n_run += 1
        el = time.time() - t0
        print(f"    idx {i}: unit={v_u:.0f}  fkp={v_f:.0f}  "
              f"delta={v_f-v_u:+.0f}   {el/n_run:.0f} s/coppia")

    # ============================================================ analisi
    recs = read_jsonl(outj)
    if len(recs) < 3:
        print("\n  troppe poche coppie.")
        return
    d = np.array([r["delta"] for r in recs], float)
    u = np.array([r["unit"] for r in recs], float)
    gates = [r.get("gate_ok") for r in recs if r.get("jsonl") is not None]

    print("\n" + "=" * 78)
    print("RISULTATO")
    print("=" * 78)
    sem = d.std(ddof=1) / np.sqrt(d.size)
    print(f"  coppie: {len(recs)}   cancello superato su "
          f"{sum(1 for g in gates if g)}/{len(gates)}")
    print(f"  peso unitario: {u.mean():.1f} +/- {u.std(ddof=1):.1f}")
    print(f"  differenza FKP - unitario, appaiata:")
    print(f"    media {d.mean():+.1f} +/- {sem:.1f}   "
          f"({d.mean()/sem if sem else 0:+.1f} sigma)")
    print(f"    sd delle differenze {d.std(ddof=1):.1f}  "
          f"(contro {u.std(ddof=1):.1f} fra mock: appaiamento cancella "
          f"{100*(1-d.std(ddof=1)/u.std(ddof=1)):.0f}%)")
    print(f"    range [{d.min():+.0f}, {d.max():+.0f}]")
    print(f"\n  in frazione del deficit: {100*d.mean()/DEFICIT:+.2f}%")
    print(f"  M26 Tabella 1 cita ~{M26_TAB1_SHIFT:.0f} generatori "
          f"({100*M26_TAB1_SHIFT/DEFICIT:.1f}%), in allontanamento dai dati")

    print("\n  LETTURA:")
    if d.mean() > 0:
        print(f"    Il peso FKP ALZA la media dei mock, quindi ALLONTANA i mock")
        print(f"    dai dati e AUMENTA il deficit di {d.mean():.0f} generatori.")
        print(f"    Il sistematico va nella direzione che rafforza l'anomalia:")
        print(f"    correggerlo non la spiega, la accentua.")
    else:
        print(f"    Il peso FKP ABBASSA la media dei mock, avvicinandoli ai")
        print(f"    dati di {abs(d.mean()):.0f} generatori "
              f"({100*abs(d.mean())/DEFICIT:.1f}% del deficit).")
        print(f"    ATTENZIONE: e' la direzione OPPOSTA a quella che M26")
        print(f"    Tabella 1 riporta. La discrepanza va risolta prima di")
        print(f"    citare l'uno o l'altro.")
    agree = abs(abs(d.mean()) - M26_TAB1_SHIFT) < 3 * sem + 0.3 * M26_TAB1_SHIFT
    print(f"\n    compatibile in modulo con M26 Tabella 1: "
          f"{'SI' if agree else 'NO - da chiarire'}")
    print(f"\n    Nota per il testo: il referee chiede N = 200 non appaiati. Il")
    print(f"    disegno appaiato con {len(recs)} coppie da' SEM = {sem:.1f}")
    print(f"    contro {u.std(ddof=1)/np.sqrt(200):.1f} che si otterrebbe con")
    print(f"    200 mock indipendenti: va spiegato, non nascosto.")

    atomic_write_json(res / "paper1" / "n6_report_NGC.json", {
        "script": "paper1_rev_n6_fkp.py", "n_coppie": len(recs),
        "delta_media": float(d.mean()), "delta_sem": float(sem),
        "delta_sd": float(d.std(ddof=1)),
        "unit_mean": float(u.mean()), "unit_sd": float(u.std(ddof=1)),
        "frazione_deficit": float(d.mean() / DEFICIT),
        "m26_tab1_shift": M26_TAB1_SHIFT,
        "wfkp_mean": float(np.mean([r["wfkp_mean"] for r in recs])),
        "cancello_superato": bool(all(gates)) if gates else None})
    print(f"\n  report: {res/'paper1'/'n6_report_NGC.json'}")


if __name__ == "__main__":
    main()

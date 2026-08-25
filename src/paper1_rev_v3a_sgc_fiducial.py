#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v3a_sgc_fiducial.py

A - CHIUSURA DEL RAMO SGC
B - INVENTARIO PER LA MISURA DELLA DISPERSIONE FRA REALIZZAZIONI (punto 7.2)

--------------------------------------------------------------------------
A. PERCHE' L'SGC E' PROBABILMENTE PULITO
--------------------------------------------------------------------------
phase9_sgc_likeforlike.py non legge mai phase8_test2_fields/: ricalcola tutto
dai cataloghi di aloni via M.read_halo_catalog(kk, snapnum). Il meccanismo che
ha contaminato l'NGC - cubi del pilota rimasti in cache e riletti da una
ricomputazione - non si applica.

E i numeri tornano:
    M26 (tex riga 675):   18694 +/- 178   (N=200)
    Paper 1:              18712.97 +/- 197.79   (N=2000)
Media diversa dello 0.10%. Rapporto delle sigma 1.11, ~2 sigma combinando gli
errori campionari - e nella direzione attesa: la distribuzione SGC ha curtosi
+27 e sigma robusta 171.98 contro sigma grezza 197.79. Un campione di 200
manca quasi sempre la coda.

TEST DECISIVO (A3): estrarre molti sottocampioni di 200 dai nostri 2000 e
vedere dove cade 178 nella distribuzione delle sigma. Se e' un percentile
ordinario, l'SGC e' spiegato e chiuso.

TRE PUNTI DA VERIFICARE COMUNQUE
  A1  convenzione sul rank: lo script stampa n_below/n_ok ma calcola la p come
      (n_below+1)/(n_ok+1). Da li' "rank 1/2000" e "below all 200 mocks",
      mentre Paper 1 usa 1/2001. Con E2 che chiede disciplina sui rank le due
      convenzioni vanno armonizzate.
  A2  ramo di fallback sulla maschera: se <90% dei dati SGC cade dentro la
      maschera congelata, lo script ne ricostruisce una con soglia all'1%, ma
      imposta comunque M.DESI_MASK_FILE = mask_sgc_path (la congelata). Se
      quel ramo e' scattato, M26 ha usato una maschera diversa da quella che
      il file di riferimento indica. Verificabile confrontando mask_fill_pct
      nel JSON col riempimento reale del file congelato.
  A4  taglio in redshift: sgc_positions() ha zmin=0.1, zmax=0.4 come default e
      non riceve mai M.ZMIN/M.ZMAX, mentre la stampa dichiara
      "z in [M.ZMIN, M.ZMAX]". Se non coincidono, i dati SGC sono tagliati
      diversamente dai dati NGC dentro un confronto like-for-like.

--------------------------------------------------------------------------
B. COSA MANCA PER IL PUNTO 7.2
--------------------------------------------------------------------------
M26 ha misurato solo il termine HOD/downsampling (110 generatori) fissando SIA
la cosmologia SIA la realizzazione (indice nwLH 1805) e variando 50 semi.
La dispersione fra REALIZZAZIONI DELLE CONDIZIONI INIZIALI a cosmologia fissa
non e' mai stata misurata. Serve per chiudere:

    sigma^2(nwLH) = sigma^2(cosmologia) + sigma^2(realizzazione) + sigma^2(HOD)

con il terzo termine noto e il secondo misurabile sul set FIDUCIALE di Quijote
(molte realizzazioni indipendenti alla stessa cosmologia).

Questa sezione inventaria cosa c'e' su disco e da dove read_halo_catalog pesca,
prima di lanciare qualunque run.

Solo lettura. Scrive un report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_v3a_sgc_fiducial.py
"""

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

import numpy as np

M26_SGC = {"mean": 18694.0, "std": 178.0, "n": 200, "desi": 15122.0,
           "z": -20.0, "frac_deficit": 0.191, "sigma_px": 0.336}
NH1 = "base.N_H1"


def read_jsonl(path):
    recs = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    return recs


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


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


def robust(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    med = float(np.median(v))
    mad = float(1.4826 * np.median(np.abs(v - med)))
    return med, (mad if mad > 0 else float(v.std(ddof=1)))


def grep_globals(path, names):
    """Estrae assegnazioni di costanti a livello di modulo."""
    out = {}
    if not path.exists():
        return out
    for L in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.+?)\s*(?:#.*)?$", L)
        if m and m.group(1) in names:
            out[m.group(1)] = m.group(2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--n_boot", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20260725)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    src = root / "src"
    rng = np.random.default_rng(args.seed)
    rep = {"script": "paper1_rev_v3a_sgc_fiducial.py", "m26_sgc": M26_SGC}

    # ============================================================ A0
    print("=" * 78)
    print("A0 - IL JSON DEL RUN SGC DI M26")
    print("=" * 78)
    sj = res / "phase9_sgc_likeforlike.json"
    J = None
    if not sj.exists():
        print(f"  [!] {sj} non trovato")
    else:
        J = json.load(open(sj, encoding="utf-8"))
        for k, v in sorted(flatten(J).items()):
            if isinstance(v, float):
                print(f"    {k:<40s} = {v:.6g}")
            elif not isinstance(v, (list, dict)):
                print(f"    {k:<40s} = {v}")
        rep["phase9_sgc_json"] = J
        print(f"\n  k_mocks effettivi: {J.get('k_mocks')}  "
              f"(il paper dichiara N=200)")
        if J.get("k_mocks") != 200:
            print(f"  *** i mock scartati silenziosamente riducono N: "
                  f"il paper va corretto ***")

    # ============================================================ A2
    print("\n" + "=" * 78)
    print("A2 - QUALE MASCHERA HA USATO DAVVERO IL RUN SGC")
    print("=" * 78)
    mp = root / "data" / "processed" / "phase6_fields" / "bgs_sgc_mask_128.npy"
    if not mp.exists():
        print(f"  [!] {mp} non trovata")
    else:
        m0 = np.load(mp).astype(bool)
        fill_frozen = 100.0 * float(m0.mean())
        print(f"  maschera congelata: {mp}")
        print(f"    riempimento reale        : {fill_frozen:.4f}%")
        if J and "sgc_geometry" in J:
            fill_used = float(J["sgc_geometry"].get("mask_fill_pct", np.nan))
            print(f"    riempimento registrato   : {fill_used:.4f}%")
            same = abs(fill_used - fill_frozen) < 0.01
            print(f"    coincidono: {'SI -> usata la congelata' if same else 'NO -> *** e scattato il ramo di RICOSTRUZIONE ***'}")
            if not same:
                print(f"    conseguenza: M26 ha usato una maschera diversa da")
                print(f"    quella che DESI_MASK_FILE indica. Va dichiarato.")
            rep["maschera_sgc"] = {"fill_congelata": fill_frozen,
                                   "fill_registrato": fill_used,
                                   "usata_congelata": bool(same)}

    # ============================================================ A4
    print("\n" + "=" * 78)
    print("A4 - TAGLIO IN REDSHIFT: SGC e NGC usano lo stesso intervallo?")
    print("=" * 78)
    g = grep_globals(src / "phase8_cutsky_mocks.py",
                     {"ZMIN", "ZMAX", "NGRID", "R_SMOOTH", "CELL", "SIGMA_PX",
                      "N_THRESH", "N_TARGET_BGS", "HOD_MEDIAN"})
    for k, v in sorted(g.items()):
        print(f"    phase8_cutsky_mocks.{k:<16s} = {v}")
    zmin = g.get("ZMIN"); zmax = g.get("ZMAX")
    print(f"\n  sgc_positions() usa i default zmin=0.1, zmax=0.4")
    if zmin is not None and zmax is not None:
        try:
            ok = abs(float(zmin) - 0.1) < 1e-9 and abs(float(zmax) - 0.4) < 1e-9
            print(f"  modulo NGC: ZMIN={zmin}, ZMAX={zmax}")
            print(f"  -> {'COINCIDONO: nessun problema' if ok else '*** DIVERSI: i dati SGC sono tagliati diversamente dagli NGC dentro un confronto like-for-like ***'}")
            rep["taglio_z"] = {"ngc": [zmin, zmax], "sgc_default": [0.1, 0.4],
                              "coincidono": bool(ok)}
        except ValueError:
            print(f"  ZMIN/ZMAX non numerici nel sorgente: verifica a mano")

    # ============================================================ A3
    print("\n" + "=" * 78)
    print("A3 - TEST DECISIVO: sigma=178 a N=200 e' compatibile coi nostri 2000?")
    print("=" * 78)
    p = res / "paper1" / "per_mock_SGC_R5.jsonl"
    if not p.exists():
        print(f"  [!] {p} non trovato")
    else:
        v = np.array([float(flatten(r).get(NH1, np.nan)) for r in read_jsonl(p)])
        v = v[np.isfinite(v)]
        med, mad = robust(v)
        print(f"  nostro ensemble SGC: n={v.size}  media={v.mean():.2f}  "
              f"sigma={v.std(ddof=1):.2f}")
        print(f"    sigma robusta (MAD) = {mad:.2f}   mediana = {med:.1f}")

        sub = rng.choice(v.size, size=(args.n_boot, M26_SGC["n"]), replace=True)
        sds = v[sub].std(axis=1, ddof=1)
        mns = v[sub].mean(axis=1)
        pct_sd = 100.0 * float((sds < M26_SGC["std"]).mean())
        pct_mn = 100.0 * float((mns < M26_SGC["mean"]).mean())
        print(f"\n  {args.n_boot} sottocampioni di {M26_SGC['n']} dai nostri 2000:")
        print(f"    sigma: mediana {np.median(sds):.1f}   "
              f"IC90 [{np.percentile(sds,5):.1f}, {np.percentile(sds,95):.1f}]")
        print(f"    M26 riporta {M26_SGC['std']:.0f} -> percentile {pct_sd:.1f}")
        print(f"    media: mediana {np.median(mns):.1f}   "
              f"IC90 [{np.percentile(mns,5):.1f}, {np.percentile(mns,95):.1f}]")
        print(f"    M26 riporta {M26_SGC['mean']:.0f} -> percentile {pct_mn:.1f}")
        verdetto = ("COMPATIBILE: l'SGC e' spiegato dalla sola dimensione del "
                    "campione" if 2.0 < pct_sd < 98.0 else
                    "NON compatibile: serve una spiegazione ulteriore")
        print(f"\n  VERDETTO: {verdetto}")
        rep["bootstrap_sgc"] = {
            "n_boot": args.n_boot, "sigma_percentile_m26": pct_sd,
            "media_percentile_m26": pct_mn,
            "sigma_mediana_sub": float(np.median(sds)),
            "sigma_ic90": [float(np.percentile(sds, 5)),
                           float(np.percentile(sds, 95))],
            "verdetto": verdetto}

    # ============================================================ B
    print("\n" + "=" * 78)
    print("B - INVENTARIO PER IL PUNTO 7.2 (dispersione fra realizzazioni)")
    print("=" * 78)

    print("\n  B1 - da dove pesca read_halo_catalog")
    f8 = src / "phase8_cutsky_mocks.py"
    if f8.exists():
        lines = f8.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, L in enumerate(lines):
            if "def read_halo_catalog" in L:
                for j in range(i, min(i + 30, len(lines))):
                    print(f"    {j+1:>5d}| {lines[j][:140]}")
                break
        else:
            print("    definizione non trovata in phase8_cutsky_mocks.py")
        pat = re.compile(
            r"""["']([^"']*(?:fiducial|latin|nwlh|hypercube|halo|snapdir)"""
            r"""[^"']*)["']""", re.I)
        hits = sorted({m.group(1) for m in pat.finditer("\n".join(lines))})
        if hits:
            print("\n    stringhe di percorso rilevanti nel modulo:")
            for h in hits[:20]:
                print(f"      {h}")

    print("\n  B2 - asset su disco")
    cands = [root / "data" / "processed" / "phase0_fields" / "fiducial",
             root / "data" / "processed" / "phase0_fields" / "lhc",
             root / "data" / "processed" / "phase0_fields" / "nwlh",
             root / "data" / "raw" / "quijote"]
    rep["asset"] = {}
    for d in cands:
        if not d.exists():
            print(f"    [assente] {d}")
            continue
        files = sorted([q for q in d.iterdir() if q.is_file()])
        tot = sum(q.stat().st_size for q in files)
        print(f"    [presente] {d}")
        print(f"        {len(files)} file, {tot/1024**3:.2f} GB")
        if files:
            print(f"        esempi: {[q.name for q in files[:3]]}")
        rep["asset"][str(d)] = {"n_file": len(files),
                                "gb": round(tot / 1024 ** 3, 3)}

    print("\n  B3 - directory di cataloghi di aloni (ricerca ampia)")
    seen = 0
    for d in root.rglob("*"):
        if not d.is_dir():
            continue
        n = d.name.lower()
        if any(t in n for t in ("fiducial", "halo", "snapdir")) and seen < 12:
            try:
                cnt = sum(1 for _ in d.iterdir())
            except Exception:
                continue
            print(f"    {d}   ({cnt} elementi)")
            seen += 1

    print("\n  LETTURA:")
    print("    per il 7.2 servono M realizzazioni indipendenti ALLA STESSA")
    print("    cosmologia. Il set fiduciale di Quijote e' fatto per questo.")
    print("    Se i cataloghi fiduciali ci sono, il passo successivo e' un")
    print("    pilota da 3 mock per validare il percorso, poi la produzione.")
    print("    Se NON ci sono, il 7.2 richiede prima uno scaricamento e va")
    print("    pianificato di conseguenza.")

    outp = res / "paper1" / "rev_v3a_sgc_fiducial_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()

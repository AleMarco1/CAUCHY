#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n1_spectral.py

N1 - PIANO (P_small, N_H1) SUI 2000 MOCK, CON DESI LOCALIZZATO

L'ESPERIMENTO CHIAVE. Punto E3 dell'editore, Referee 3 §1(c).

LA DOMANDA
----------
Il paper dimostra che il deficit non e' one-point (il rank remapping non lo
sposta). Ne conclude che sia "informazione di fase". Referee 3 osserva che fra
"non one-point" e "fase" c'e' tutta la funzione a due punti: un campo gaussiano
con meno potenza a piccola scala ha meno loop con fasi perfettamente casuali.
E M26 ha misurato che DESI ha meno potenza a piccola scala dei mock (frazione
sopra meta-Nyquist 0.570 contro 0.680).

  DESI giace sulla relazione P_small-N_H1 dei mock  -> il deficit e' predetto
    dal suo spettro, il contenuto "topologico" e' nullo, il paper si
    re-intitola sull'origine spettrale.
  DESI cade fuori dalla relazione                   -> e' la prova che manca,
    piu' forte di tutto il resto, e "beyond-two-point" diventa dimostrato.

TRE SCELTE DI DISEGNO, DICHIARATE
---------------------------------
1. CAMPO. Lo spettro si calcola sul campo nu che entra EFFETTIVAMENTE nella
   TDA (data/processed/paper1_mock_deltas/<REG>/delta_XXXX.npy: post log,
   lisciatura, sottrazione della media, maschera). La domanda e' se la funzione
   a due punti DELLO STESSO CAMPO su cui si calcola la topologia predica N_H1.
   Usare il delta grezzo sarebbe un test diverso e piu' debole.

2. STATISTICA. Si riproduce la frazione sopra meta-Nyquist quotata da M26, per
   confrontabilita'. Ma se ne calcolano anche altre (sopra un quarto di
   Nyquist, potenza assoluta a piccola scala, pendenza efficace, sigma del
   campo): se la conclusione dipende da quale definizione si sceglie, e' una
   cosa da sapere, non da nascondere.

3. NESSUNA DECONVOLUZIONE DELLA FINESTRA. Il campo e' mascherato e la finestra
   contamina lo spettro. Non si deconvolve: si applica lo stesso trattamento a
   DESI e ai mock, e si dichiara che il confronto e' relativo.

IL CAVEAT CHE PUO' DECIDERE TUTTO
---------------------------------
Se la frazione di DESI (0.570) e' fuori dall'intervallo coperto dai mock
(~0.680), predire N_H1 alla sua posizione significa EXTRAPOLARE la relazione
oltre i dati che la calibrano. Lo script misura il rank di DESI nella
distribuzione spettrale e lo dichiara: se e' saturo, la conclusione dipende da
un'assunzione di linearita' e va scritta come tale.

AUTOCONTROLLO OBBLIGATORIO
--------------------------
Il campo DESI viene ricostruito con build_field e la sua TDA DEVE restituire
28256. Se non lo fa, lo script si ferma: significa che sto calcolando lo
spettro di un campo diverso da quello del paper.

INGEGNERIA
----------
Append-only JSONL, resumable: rilanciare riprende da dove si era fermato.
Il campo nu di DESI viene messo in cache al primo giro.

USO
---
  python src\\paper1_rev_n1_spectral.py --k 50        # pilota
  python src\\paper1_rev_n1_spectral.py               # tutti i 2000
  python src\\paper1_rev_n1_spectral.py --analyze_only
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

DESI_NH1 = {"NGC": 28256.0, "SGC": 15122.0}
M26_FHALF = {"desi": 0.570, "mock": 0.680}
NH1 = "base.N_H1"


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
        f.flush()
        os.fsync(f.fileno())


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


# ---------------------------------------------------------------- spettro
_KCACHE = {}


def kgrid(ngrid, cell):
    key = (ngrid, round(cell, 9))
    if key in _KCACHE:
        return _KCACHE[key]
    kf = 2.0 * np.pi * np.fft.fftfreq(ngrid, d=cell)
    kz = 2.0 * np.pi * np.fft.rfftfreq(ngrid, d=cell)
    KX, KY, KZ = np.meshgrid(kf, kf, kz, indexing="ij")
    kmag = np.sqrt(KX ** 2 + KY ** 2 + KZ ** 2)
    # peso per la simmetria hermitiana della rfft
    w = np.full(kmag.shape, 2.0)
    w[..., 0] = 1.0
    if ngrid % 2 == 0:
        w[..., -1] = 1.0
    _KCACHE[key] = (kmag, w)
    return kmag, w


def spectral_summary(nu, cell, mask=None):
    """Sommari spettrali del campo nu. Periodogramma grezzo, nessuna
    deconvoluzione della finestra: trattamento identico a DESI e ai mock."""
    ngrid = nu.shape[0]
    kmag, w = kgrid(ngrid, cell)
    F = np.fft.rfftn(nu.astype(np.float64))
    P = (F.real ** 2 + F.imag ** 2) * w
    k_nyq = np.pi / cell

    pos = kmag > 0
    tot = float(P[pos].sum())
    out = {"k_nyq": float(k_nyq), "P_tot": tot}
    for frac, nome in ((0.5, "f_half"), (0.25, "f_quarter"), (0.75, "f_three_q")):
        sel = pos & (kmag > frac * k_nyq)
        out[nome] = float(P[sel].sum()) / tot if tot > 0 else np.nan
        if nome == "f_half":
            out["P_small_abs"] = float(P[sel].sum())

    # pendenza efficace fra due bande logaritmiche
    b1 = pos & (kmag > 0.10 * k_nyq) & (kmag <= 0.20 * k_nyq)
    b2 = pos & (kmag > 0.40 * k_nyq) & (kmag <= 0.80 * k_nyq)
    if b1.any() and b2.any():
        p1 = P[b1].mean(); p2 = P[b2].mean()
        k1 = kmag[b1].mean(); k2 = kmag[b2].mean()
        out["slope_eff"] = (float(np.log(p2 / p1) / np.log(k2 / k1))
                            if p1 > 0 and p2 > 0 else np.nan)
    else:
        out["slope_eff"] = np.nan

    if mask is not None:
        v = nu[mask]
        out["sigma_in_mask"] = float(v.std())
        out["kurt_in_mask"] = float(((v - v.mean()) ** 4).mean() / v.std() ** 4 - 3.0)
    return out


# ---------------------------------------------------------------- analisi
def corr_ci(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    n = int(m.sum())
    if n < 8:
        return None
    r = float(np.corrcoef(x[m], y[m])[0, 1])
    r = min(max(r, -0.999999), 0.999999)
    zf = 0.5 * np.log((1 + r) / (1 - r))
    se = 1.0 / np.sqrt(n - 3)
    return {"r": r, "n": n, "sigma": float(abs(zf) / se),
            "ic95": [float(np.tanh(zf - 1.96 * se)),
                     float(np.tanh(zf + 1.96 * se))]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", default="NGC")
    ap.add_argument("--k", type=int, default=0, help="0 = tutti i mock trovati")
    ap.add_argument("--analyze_only", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    reg = args.region
    res = root / "results"
    cache = root / "data" / "processed" / "paper1_mock_deltas" / reg
    outj = res / "paper1" / f"n1_spectra_{reg}.jsonl"
    desi_cache = res / "paper1" / f"n1_desi_nu_{reg}.npy"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M

    mask_file = (root / "data" / "processed" / "phase6_fields" /
                 f"bgs_{reg.lower()}_mask_128.npy")
    mask = np.load(mask_file).astype(bool)
    cell = M.CELL if reg == "NGC" else None
    print("=" * 78)
    print(f"N1 - {reg}")
    print("=" * 78)
    print(f"  maschera: {mask_file}  ({100*mask.mean():.2f}% pieno)")

    # ---------------------------------------------------------- DESI
    print("\n[1] CAMPO nu DI DESI + AUTOCONTROLLO")
    desi_spec = None
    if reg != "NGC":
        print("  ATTENZIONE: la geometria SGC va iniettata come in "
              "phase9_sgc_likeforlike.py; questa versione copre NGC.")
        print("  Per SGC serve una passata dedicata. Interrompo.")
        return
    if desi_cache.exists():
        nu_desi = np.load(desi_cache)
        print(f"  caricato da cache: {desi_cache}")
    else:
        print("  ricostruzione da FITS (qualche minuto)...")
        field_r, sum_wr = M.load_desi_random_field()
        field_d, sum_wd = M.load_desi_data_field()
        nu_desi = M.build_field(field_d, field_r, sum_wd / sum_wr, mask)
        desi_cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(desi_cache, nu_desi)
        print(f"  salvato in cache: {desi_cache}")

    f = M.compute_tda_features(nu_desi, mask, M.N_THRESH, masked=True)
    nh1_check = float(f[4])
    print(f"  N_H1 ricalcolato = {nh1_check:.0f}   atteso = {DESI_NH1[reg]:.0f}")
    if abs(nh1_check - DESI_NH1[reg]) > 0.5:
        print("\n  *** AUTOCONTROLLO FALLITO ***")
        print("  Il campo ricostruito non riproduce il valore congelato: sto")
        print("  calcolando lo spettro di un campo diverso da quello del paper.")
        print("  Mi fermo. Verificare build_field, la maschera e i FITS.")
        return
    print("  autocontrollo superato.")
    desi_spec = spectral_summary(nu_desi, M.CELL, mask)
    print(f"\n  DESI: f_half = {desi_spec['f_half']:.5f}   "
          f"f_quarter = {desi_spec['f_quarter']:.5f}")
    print(f"        sigma dentro maschera = {desi_spec['sigma_in_mask']:.5f}   "
          f"pendenza eff. = {desi_spec['slope_eff']:+.3f}")
    print(f"  M26 quota f_half DESI ~ {M26_FHALF['desi']}, mock ~ "
          f"{M26_FHALF['mock']}")

    # ---------------------------------------------------------- mock
    if not args.analyze_only:
        print("\n[2] SPETTRI DEI MOCK (append-only, resumable)")
        done = {r["idx"] for r in read_jsonl(outj)}
        files = sorted(cache.glob("delta_*.npy"))
        if args.k > 0:
            files = files[:args.k]
        todo = [(int(p.stem.split("_")[1]), p) for p in files]
        todo = [(i, p) for i, p in todo if i not in done]
        print(f"  {len(files)} campi in cache, {len(done)} gia' fatti, "
              f"{len(todo)} da fare")
        t0 = time.time()
        for n, (i, p) in enumerate(todo, 1):
            nu = np.load(p)
            s = spectral_summary(nu, M.CELL, mask)
            s["idx"] = i
            append_jsonl(outj, s)
            if n % 50 == 0 or n == 1:
                el = time.time() - t0
                eta = el / n * (len(todo) - n) / 60.0
                print(f"    [{n}/{len(todo)}] idx={i}  f_half={s['f_half']:.5f}  "
                      f"ETA {eta:.1f} min")
        if todo:
            print(f"  completato in {(time.time()-t0)/60:.1f} min")

    # ---------------------------------------------------------- analisi
    print("\n[3] ANALISI")
    recs = read_jsonl(outj)
    if len(recs) < 30:
        print(f"  solo {len(recs)} spettri: troppo pochi per l'analisi.")
        return
    spec = {r["idx"]: r for r in recs}

    pm = read_jsonl(res / "paper1" / f"per_mock_{reg}_R5.jsonl")
    nh1 = {}
    for j, r in enumerate(pm):
        fl = flatten(r)
        key = fl.get("key", j)
        try:
            key = int(key)
        except (TypeError, ValueError):
            key = j
        nh1[key] = float(fl.get(NH1, np.nan))

    idx = sorted(set(spec) & set(nh1))
    print(f"  mock con spettro e N_H1: {len(idx)}")
    y = np.array([nh1[i] for i in idx])
    rep = {"script": "paper1_rev_n1_spectral.py", "regione": reg,
           "n_mock": len(idx), "desi": desi_spec,
           "desi_nh1": DESI_NH1[reg], "m26_fhalf_citato": M26_FHALF}

    VARS = ["f_half", "f_quarter", "f_three_q", "slope_eff",
            "sigma_in_mask", "P_small_abs"]
    print(f"\n  correlazioni con N_H1:")
    print(f"    {'variabile':>14s} {'r':>9s} {'IC95%':>20s} {'sigma':>7s}")
    rep["correlazioni"] = {}
    for v in VARS:
        x = np.array([spec[i].get(v, np.nan) for i in idx], float)
        c = corr_ci(x, y)
        if c:
            print(f"    {v:>14s} {c['r']:>+9.4f} "
                  f"[{c['ic95'][0]:>+7.4f},{c['ic95'][1]:>+7.4f}] "
                  f"{c['sigma']:>7.1f}")
            rep["correlazioni"][v] = c

    # ------- il piano (f_half, N_H1) e la posizione di DESI
    print("\n" + "=" * 78)
    print("IL RISULTATO: DOVE CADE DESI")
    print("=" * 78)
    rep["piano"] = {}
    for v in ("f_half", "f_quarter", "sigma_in_mask"):
        x = np.array([spec[i].get(v, np.nan) for i in idx], float)
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 30 or v not in desi_spec:
            continue
        xx, yy = x[m], y[m]
        xd = float(desi_spec[v])

        # rank di DESI nella distribuzione spettrale dei mock
        below = int((xx < xd).sum())
        fuori = xd < xx.min() or xd > xx.max()
        A = np.column_stack([np.ones(xx.size), xx])
        beta, *_ = np.linalg.lstsq(A, yy, rcond=None)
        pred_all = A @ beta
        sr = float(np.std(yy - pred_all, ddof=2))
        pred_desi = float(beta[0] + beta[1] * xd)
        obs = DESI_NH1[reg]
        resid = obs - pred_desi
        deficit = float(yy.mean()) - obs
        spiegato = (float(yy.mean()) - pred_desi) / deficit if deficit else np.nan

        print(f"\n  --- {v}")
        print(f"    mock : {xx.mean():.5f} +/- {xx.std(ddof=1):.5f}  "
              f"range [{xx.min():.5f}, {xx.max():.5f}]")
        print(f"    DESI : {xd:.5f}   rank {below+1}/{xx.size+1}"
              f"   {'*** FUORI dall intervallo dei mock ***' if fuori else ''}")
        print(f"    relazione N_H1 = {beta[0]:.1f} + {beta[1]:.1f} x {v}"
              f"   (dispersione attorno alla relazione {sr:.1f})")
        print(f"    N_H1 predetto alla posizione di DESI : {pred_desi:.0f}")
        print(f"    N_H1 osservato                       : {obs:.0f}")
        print(f"    residuo                              : {resid:+.0f}"
              f"   = {resid/sr:+.2f} volte la dispersione")
        print(f"    frazione del deficit spiegata dallo spettro: "
              f"{100*spiegato:.1f}%")
        if fuori:
            print(f"    ATTENZIONE: la predizione e' un'EXTRAPOLAZIONE oltre")
            print(f"    l'intervallo che calibra la relazione. La conclusione")
            print(f"    dipende da un'assunzione di linearita' e va scritta")
            print(f"    come tale.")
        rep["piano"][v] = {
            "mock_mean": float(xx.mean()), "mock_std": float(xx.std(ddof=1)),
            "mock_min": float(xx.min()), "mock_max": float(xx.max()),
            "desi": xd, "rank_desi": f"{below+1}/{xx.size+1}",
            "desi_fuori_range": bool(fuori),
            "intercetta": float(beta[0]), "pendenza": float(beta[1]),
            "dispersione_relazione": sr,
            "nh1_predetto": pred_desi, "nh1_osservato": obs,
            "residuo": float(resid), "residuo_in_sigma": float(resid / sr),
            "frazione_deficit_spiegata": float(spiegato)}

    # ------- lettura
    print("\n" + "=" * 78)
    print("LETTURA")
    print("=" * 78)
    p = rep["piano"].get("f_half")
    if p:
        fr = p["frazione_deficit_spiegata"]
        rs = abs(p["residuo_in_sigma"])
        print(f"  frazione del deficit spiegata da f_half: {100*fr:.1f}%")
        print(f"  residuo di DESI dalla relazione: {rs:.1f} dispersioni")
        if fr > 1.15:
            print("\n  -> LO SPETTRO SOVRAPREDICE IL DEFICIT. Alla sua potenza a")
            print("     piccola scala, DESI dovrebbe avere ANCORA MENO loop di")
            print("     quanti ne ha. Il deficit e' interamente riconducibile al")
            print("     due-punti e in eccesso: 'oltre il due-punti' cade, e va")
            print("     indagato perche' la topologia sia meno depressa dello")
            print("     spettro (candidati: non linearita' della relazione fuori")
            print("     range, oppure fasi non casuali che PRESERVANO loop).")
        elif fr < 0.0:
            print("\n  -> SEGNO SBAGLIATO. La relazione dei mock predice piu'")
            print("     loop della media alla posizione spettrale di DESI: lo")
            print("     spettro non spiega nulla del deficit e la relazione va")
            print("     esaminata prima di trarne conclusioni.")
        elif fr > 0.8 and rs < 3:
            print("\n  -> DESI GIACE SULLA RELAZIONE. Il deficit e' predetto dal")
            print("     suo spettro a piccola scala. La tesi 'oltre il due-punti'")
            print("     cade: titolo, abstract e Sez. 7 vanno riscritti")
            print("     sull'origine spettrale. Risultato forte e pubblicabile,")
            print("     ma diverso da quello attuale.")
        elif fr < 0.5 and rs > 3:
            print("\n  -> DESI CADE FUORI DALLA RELAZIONE. E' la prova che")
            print("     Referee 3 chiede, e piu' forte di tutto il resto:")
            print("     lo spettro a piccola scala spiega solo una parte del")
            print("     deficit e il resto e' contenuto non-due-punti.")
        else:
            print("\n  -> ESITO INTERMEDIO. Lo spettro spiega una frazione")
            print("     sostanziale ma non tutto. Il paper deve quotare quella")
            print("     frazione come risultato principale e riformulare la tesi")
            print("     in termini quantitativi invece che dicotomici.")
        if p["desi_fuori_range"]:
            print("\n  In ogni caso: DESI e' fuori dall'intervallo spettrale dei")
            print("  mock, quindi la relazione va extrapolata. Questo va")
            print("  dichiarato, e rende N10 (fasi randomizzate a spettro")
            print("  fissato) piu' necessario, non meno.")

    atomic_write_json(res / "paper1" / f"n1_report_{reg}.json", rep)
    print(f"\n  report: {res / 'paper1' / ('n1_report_' + reg + '.json')}")


if __name__ == "__main__":
    main()

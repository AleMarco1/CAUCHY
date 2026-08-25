#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1 (revisione) + Paper 5 (canovaccio, punto M1)
src/paper1_rev_m1_cosmo_response.py

M1 - RISPOSTA DI N_H1 AI PARAMETRI COSMOLOGICI, A n = 2000

PERCHE'
-------
Le correlazioni usate finora erano su n = 200, e non per un limite dei dati ma
perche' phase8_test2_permock.csv era stato sovrascritto da un run successivo a
200 mock. I parametri di TUTTI i 2000 stanno in latin_hypercube_nwLH_params.txt
(lo legge load_nwlh_params() in phase8_test2_masked.py), e i valori corretti di
N_H1 per tutti i 2000 stanno in results/paper1/per_mock_NGC_R5.jsonl.

A n = 2000 l'errore su r scende da 0.071 a 0.022: una correlazione di 0.05
diventa misurabile.

DUE USI
-------
1. Revisione Paper 1: rimpiazza le correlazioni a n=200 con cui stiamo per
   correggere cauchy_mnras.tex riga 735 (M26 riporta Om +0.45, s8 +0.29,
   w0 -0.03, calcolate sull'array contaminato). Meglio correggere col numero
   definitivo che con quello provvisorio. L'R^2 del modello completo da' anche
   la frazione di varianza attribuibile ai parametri, che serve a rifare la
   decomposizione senza residui.
2. Paper 5 (canovaccio, regola di decisione di §4): se |r(N_H1, w0)| > 0.10 con
   IC95% che esclude lo zero, il test CPL ha una leva; altrimenti va riformulato.

UNA CORRELAZIONE NULLA NON BASTA
--------------------------------
Tre controlli oltre alla regressione lineare:

A. VALIDAZIONE DELLA MAPPATURA DELLE COLONNE. I commenti in load_nwlh_params()
   si contraddicono: il docstring dice 6 colonne (Om, Ob, h, ns, s8, w0), il
   commento nel codice dice 7 con Mnu in posizione 5 e usa tab[:,0], tab[:,4],
   tab[:,6]. Qui la mappatura si deduce dalle firme degli intervalli e poi si
   VERIFICA contro w0/Om/s8 dell'npz sugli indici 0-199, che sappiamo corretti
   perche' riproducono esattamente le correlazioni di M26. Se non coincidono,
   lo script si ferma.

B. MEDIE BINNATE IN w0. Con n=2000 e 10 bin, l'errore sulla media per bin e'
   313/sqrt(200) ~ 22 generatori: una risposta di 60 sarebbe evidente. Piu'
   convincente di qualunque coefficiente.

C. TERMINE QUADRATICO. Una correlazione lineare nulla puo' nascondere una
   risposta simmetrica in |w0+1|, plausibile per una statistica che dipende
   dalla forma dello spettro e non dall'ampiezza. Va escluso, non assunto.

Solo lettura. Scrive un report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_m1_cosmo_response.py
  python src\\paper1_rev_m1_cosmo_response.py --params_file <percorso>
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np

NH1 = "base.N_H1"
DESI = {"NGC": 28256.0, "SGC": 15122.0}
PATOL = {"NGC": [139, 598, 1430, 1666], "SGC": [598, 1022, 1430, 1666]}
M26_QUOTED = {"Om": 0.45, "s8": 0.29, "w0": -0.03}

# firme di intervallo per dedurre la mappatura delle colonne
SIGN = {
    "Om": (0.05, 0.55), "Ob": (0.02, 0.09), "h":  (0.45, 0.95),
    "ns": (0.75, 1.30), "s8": (0.55, 1.05), "Mnu": (-0.01, 1.2),
    "w0": (-1.45, -0.55),
}
ORDER = ("Om", "Ob", "h", "ns", "s8", "Mnu", "w0")


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


def ols(X, y, names):
    """OLS con errori standard, t e R^2. X senza colonna di intercetta."""
    A = np.column_stack([np.ones(X.shape[0]), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    n, p = A.shape
    dof = n - p
    s2 = float(resid @ resid) / dof
    XtXi = np.linalg.pinv(A.T @ A)
    se = np.sqrt(np.maximum(np.diag(XtXi) * s2, 0.0))
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(resid @ resid) / ss_tot
    r2adj = 1.0 - (1.0 - r2) * (n - 1) / dof
    out = {"r2": r2, "r2_adj": r2adj, "n": n, "sigma_resid": float(np.sqrt(s2)),
           "intercetta": {"coef": float(beta[0]), "se": float(se[0])},
           "coef": {}}
    for k, nm in enumerate(names, start=1):
        out["coef"][nm] = {"coef": float(beta[k]), "se": float(se[k]),
                           "t": float(beta[k] / se[k]) if se[k] > 0 else 0.0}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--params_file", default=None)
    ap.add_argument("--n_bins", type=int, default=10)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    rep = {"script": "paper1_rev_m1_cosmo_response.py", "m26_citato": M26_QUOTED}

    # ============================================================ 1. params
    print("=" * 78)
    print("1 - TABELLA DEI PARAMETRI nwLH")
    print("=" * 78)
    cands = []
    if args.params_file:
        cands.append(Path(args.params_file))
    q = root / "data" / "raw" / "quijote"
    cands += [q / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt",
              q / "latin_hypercube_nwLH_params.txt",
              q / "3D_cubes" / "latin_hypercube_nwLH_hod" / "latin_hypercube_nwLH_params.txt"]
    path = next((p for p in cands if p.exists()), None)
    if path is None:
        hits = sorted(root.rglob("*nwLH*params*.txt"))
        if hits:
            path = hits[0]
            print(f"  trovato per ricerca: {path}")
    if path is None:
        print("  [FATAL] tabella dei parametri non trovata.")
        print("  Passala con --params_file. Percorsi provati:")
        for c in cands:
            print(f"    {c}")
        return
    tab = np.loadtxt(path)
    if tab.ndim == 1:
        tab = tab.reshape(1, -1)
    print(f"  {path}")
    print(f"  shape = {tab.shape}")
    print(f"\n  {'col':>4s} {'min':>12s} {'max':>12s} {'mediana':>12s} "
          f"{'distinti':>9s}  ipotesi")
    guess = {}
    for j in range(tab.shape[1]):
        c = tab[:, j]
        lo, hi = float(c.min()), float(c.max())
        names = [k for k, (a, b) in SIGN.items() if a <= lo and hi <= b]
        # se e' costante, non e' un parametro variato
        if len(np.unique(np.round(c, 10))) == 1:
            names = [f"costante={lo:.4g}"]
        guess[j] = names
        print(f"  {j:>4d} {lo:>12.5g} {hi:>12.5g} {np.median(c):>12.5g} "
              f"{len(np.unique(np.round(c,10))):>9d}  {names}")

    # mappatura per posizione, filtrata dalle firme
    mapping = {}
    used = set()
    for name in ORDER:
        for j in range(tab.shape[1]):
            if j in used:
                continue
            if name in guess.get(j, []):
                mapping[name] = j
                used.add(j)
                break
    print(f"\n  mappatura dedotta: "
          f"{ {k: mapping[k] for k in sorted(mapping, key=lambda x: mapping[x])} }")
    rep["params_file"] = str(path)
    rep["mappatura"] = mapping
    rep["params_shape"] = list(tab.shape)

    # ============================================================ 2. validazione
    print("\n" + "=" * 78)
    print("2 - VALIDAZIONE: la mappatura combacia con l'npz sugli indici 0-199?")
    print("=" * 78)
    npzp = res / "phase9_likeforlike_arrays.npz"
    ok_map = None
    if not npzp.exists():
        print(f"  [!] {npzp} assente: validazione NON eseguibile")
        print(f"  *** la mappatura resta un'IPOTESI dedotta dagli intervalli.")
        print(f"      Le firme di Om/Ob/h/ns/s8/Mnu si sovrappongono, quindi")
        print(f"      l'assegnazione dipende dall'ordine assunto delle colonne.")
        print(f"      Verifica a mano prima di citare qualunque numero. ***")
        rep["validazione_mappatura"] = {"ok": None,
                                        "nota": "npz assente, mappatura non validata"}
    else:
        z = np.load(npzp, allow_pickle=True)
        checks = {}
        for k in ("w0", "Om", "s8"):
            if k not in z.files or k not in mapping:
                continue
            a = np.asarray(z[k], float).ravel()[:200]
            b = tab[:200, mapping[k]]
            m = np.isfinite(a) & np.isfinite(b)
            if m.sum() < 50:
                continue
            md = float(np.max(np.abs(a[m] - b[m])))
            checks[k] = md
            print(f"    {k:>3s}: max|npz - params| su {int(m.sum())} indici = "
                  f"{md:.3e}   {'OK' if md < 1e-6 else '*** DISCORDANTI ***'}")
        ok_map = bool(checks) and all(v < 1e-6 for v in checks.values())
        rep["validazione_mappatura"] = {"max_diff": checks, "ok": ok_map}
        if not ok_map:
            print("\n  *** la mappatura NON e' validata: mi fermo qui. ***")
            print("  Le correlazioni calcolate su colonne sbagliate sarebbero")
            print("  peggio che nessuna correlazione. Verifica l'ordine delle")
            print("  colonne nel file dei parametri e ripassa --params_file.")
            atomic_write_json(res / "paper1" / "rev_m1_cosmo_report.json", rep)
            return
        print("\n  mappatura validata: l'npz sugli indici noti coincide.")

    # ============================================================ 3. dati
    print("\n" + "=" * 78)
    print("3 - VALORI CORRETTI DI N_H1")
    print("=" * 78)
    ours = {}
    for reg in ("NGC", "SGC"):
        p = res / "paper1" / f"per_mock_{reg}_R5.jsonl"
        if not p.exists():
            continue
        v = np.array([float(flatten(r).get(NH1, np.nan))
                      for r in read_jsonl(p)])
        ours[reg] = v
        print(f"  {reg}: n={v.size}  media={np.nanmean(v):.2f}  "
              f"sd={np.nanstd(v, ddof=1):.2f}")
    if not ours:
        print("  [FATAL] nessun JSONL trovato")
        return
    nrow = min(tab.shape[0], min(v.size for v in ours.values()))
    print(f"  righe utilizzabili (min fra params e JSONL): {nrow}")

    par = {k: tab[:nrow, j] for k, j in mapping.items()
           if not str(k).startswith("costante")}
    varied = [k for k in par if len(np.unique(np.round(par[k], 10))) > 1]
    print(f"  parametri effettivamente variati: {varied}")

    print("\n  matrice di correlazione del disegno (deve essere ~identita'"
          " in un Latin hypercube):")
    print("        " + "".join(f"{k:>8s}" for k in varied))
    D = np.column_stack([par[k] for k in varied])
    C = np.corrcoef(D.T)
    for i, k in enumerate(varied):
        print(f"  {k:>6s}" + "".join(f"{C[i, j]:>8.3f}" for j in range(len(varied))))
    rep["corr_disegno"] = {"parametri": varied, "matrice": C.tolist()}

    # ============================================================ 4. correlazioni
    print("\n" + "=" * 78)
    print("4 - CORRELAZIONI UNIVARIATE, n = 2000")
    print("=" * 78)
    rep["correlazioni"] = {}
    for reg, v in ours.items():
        y = v[:nrow]
        keep = np.ones(nrow, bool)
        keep[[i for i in PATOL[reg] if i < nrow]] = False
        print(f"\n  --- {reg}")
        print(f"      {'par':>5s} {'r (tutti)':>12s} {'IC95%':>22s} "
              f"{'sigma':>7s} | {'r (no patol.)':>14s}")
        rep["correlazioni"][reg] = {}
        for k in varied:
            c = corr_ci(par[k], y)
            c2 = corr_ci(par[k][keep], y[keep])
            if c is None:
                continue
            print(f"      {k:>5s} {c['r']:>+12.4f} "
                  f"[{c['ic95'][0]:>+8.4f},{c['ic95'][1]:>+8.4f}] "
                  f"{c['sigma']:>7.1f} | {c2['r']:>+14.4f}")
            rep["correlazioni"][reg][k] = {"tutti": c, "senza_patologici": c2}
        if reg == "NGC":
            print(f"\n      M26 riga 735 riporta (su n=200 contaminato): "
                  f"Om {M26_QUOTED['Om']:+.2f}, s8 {M26_QUOTED['s8']:+.2f}, "
                  f"w0 {M26_QUOTED['w0']:+.2f}")

    # ============================================================ 5. OLS
    print("\n" + "=" * 78)
    print("5 - REGRESSIONE MULTIVARIATA")
    print("=" * 78)
    rep["ols"] = {}
    for reg, v in ours.items():
        y = v[:nrow]
        m = np.isfinite(y) & np.all(np.isfinite(D), axis=1)
        o = ols(D[m], y[m], varied)
        print(f"\n  --- {reg}   n={o['n']}   R^2={o['r2']:.5f}   "
              f"R^2 agg.={o['r2_adj']:.5f}   sd residua={o['sigma_resid']:.1f}")
        print(f"      {'par':>5s} {'coef':>14s} {'se':>12s} {'t':>8s} "
              f"{'escursione':>12s}")
        for k in varied:
            c = o["coef"][k]
            rng = float(par[k].max() - par[k].min())
            print(f"      {k:>5s} {c['coef']:>+14.2f} {c['se']:>12.2f} "
                  f"{c['t']:>+8.2f} {c['coef']*rng:>+12.1f}")
            o["coef"][k]["escursione_su_range"] = c["coef"] * rng
        print(f"\n      i parametri cosmologici spiegano il "
              f"{100*o['r2']:.2f}% della varianza di N_H1")
        rep["ols"][reg] = o

    # ============================================================ 6. w0 binnato
    print("\n" + "=" * 78)
    print("6 - MEDIE BINNATE IN w0  (test di risposta indipendente dal modello)")
    print("=" * 78)
    rep["bin_w0"] = {}
    if "w0" not in par:
        print("  w0 non presente nella tabella: sezione saltata")
    else:
        w = par["w0"]
        edges = np.quantile(w, np.linspace(0, 1, args.n_bins + 1))
        for reg, v in ours.items():
            y = v[:nrow]
            print(f"\n  --- {reg}   (sd per bin attesa ~ "
                  f"{np.nanstd(y, ddof=1)/np.sqrt(nrow/args.n_bins):.0f} generatori)")
            print(f"      {'bin':>4s} {'w0 medio':>10s} {'n':>5s} "
                  f"{'N_H1 medio':>12s} {'SEM':>8s}")
            rows = []
            for b in range(args.n_bins):
                sel = (w >= edges[b]) & (w <= edges[b + 1] if b == args.n_bins - 1
                                         else w < edges[b + 1])
                sel &= np.isfinite(y)
                if sel.sum() < 5:
                    continue
                yy = y[sel]
                sem = float(yy.std(ddof=1) / np.sqrt(yy.size))
                print(f"      {b:>4d} {w[sel].mean():>10.4f} {int(sel.sum()):>5d} "
                      f"{yy.mean():>12.1f} {sem:>8.1f}")
                rows.append({"bin": b, "w0": float(w[sel].mean()),
                             "n": int(sel.sum()), "media": float(yy.mean()),
                             "sem": sem})
            if len(rows) > 2:
                mm = np.array([r["media"] for r in rows])
                ss = np.array([r["sem"] for r in rows])
                spread = float(mm.max() - mm.min())
                print(f"      escursione fra bin: {spread:.1f} generatori  "
                      f"(SEM tipica {np.median(ss):.1f})")
                print(f"      -> {'RISPOSTA VISIBILE' if spread > 4*np.median(ss) else 'nessuna risposta oltre il rumore'}")
            rep["bin_w0"][reg] = rows

    # ============================================================ 7. quadratico
    print("\n" + "=" * 78)
    print("7 - RISPOSTA SIMMETRICA IN |w0 + 1|?")
    print("=" * 78)
    rep["quadratico"] = {}
    if "w0" in par:
        w = par["w0"]
        for reg, v in ours.items():
            y = v[:nrow]
            m = np.isfinite(y)
            X2 = np.column_stack([w[m], (w[m] + 1.0) ** 2])
            o = ols(X2, y[m], ["w0", "(w0+1)^2"])
            cq = o["coef"]["(w0+1)^2"]
            rng2 = float(((w + 1.0) ** 2).max())
            print(f"  {reg}: coef quadratico {cq['coef']:+.1f} +/- {cq['se']:.1f}"
                  f"   t={cq['t']:+.2f}")
            print(f"        escursione implicata su (w0+1)^2 max = "
                  f"{cq['coef']*rng2:+.1f} generatori")
            print(f"        R^2 del modello w0 + quadratico: {o['r2']:.5f}")
            rep["quadratico"][reg] = o
        print(f"\n  Un t quadratico non significativo esclude una risposta")
        print(f"  simmetrica attorno a w0 = -1, che una correlazione lineare")
        print(f"  nulla da sola non escluderebbe.")

    # ============================================================ 8. Paper 5
    print("\n" + "=" * 78)
    print("8 - CONSEGUENZA PER PAPER 5 (regola di decisione di canovaccio §4)")
    print("=" * 78)
    if "w0" in par and "NGC" in ours:
        c = rep["correlazioni"]["NGC"].get("w0", {}).get("tutti")
        o = rep["ols"]["NGC"]["coef"].get("w0", {})
        y = ours["NGC"][:nrow]
        sd = float(np.nanstd(y, ddof=1))
        if c and o:
            b, sb = o["coef"], o["se"]
            b_hi = abs(b) + 1.96 * sb
            dw = float(par["w0"].max() - par["w0"].min())
            print(f"  r(N_H1, w0) = {c['r']:+.4f}   IC95% "
                  f"[{c['ic95'][0]:+.4f}, {c['ic95'][1]:+.4f}]   n={c['n']}")
            print(f"  pendenza    = {b:+.1f} +/- {sb:.1f} generatori per unita' di w0")
            print(f"  limite sup. 95% |pendenza| = {b_hi:.1f}")
            print(f"  escursione sull'intervallo campionato (dw0={dw:.2f}): "
                  f"{b*dw:+.1f}  (limite sup. {b_hi*dw:.1f})")
            print(f"  dispersione a singola realizzazione: {sd:.1f}")
            print(f"  segnale/rumore sull'intero intervallo: "
                  f"{abs(b*dw)/sd:.3f} sigma  (limite sup. {b_hi*dw/sd:.3f})")
            if b_hi > 0:
                print(f"  vincolo 1 sigma su w0 da una misura con errore {sd:.0f}: "
                      f"+/- {sd/b_hi:.2f} (nel caso piu' favorevole al 95%)")
                print(f"  da confrontare con ~+/-0.06 di BAO DESI")
            crit = abs(c["r"]) > 0.10 and (c["ic95"][0] * c["ic95"][1] > 0)
            print(f"\n  REGOLA DI DECISIONE (canovaccio §4):")
            print(f"    |r| > 0.10 con IC95% che esclude lo zero: "
                  f"{'SODDISFATTA -> Paper 5 come test CPL ha una leva' if crit else 'NON soddisfatta -> Paper 5 va RIFORMULATO'}")
            print(f"    Resta comunque da verificare M3 (realizzazioni per punto")
            print(f"    di griglia in AbacusSummit) prima di qualunque impegno.")
            rep["paper5"] = {
                "r_w0": c, "pendenza": b, "se_pendenza": sb,
                "limite_sup_95": b_hi, "dw0": dw, "sd_singola": sd,
                "snr_su_intervallo": abs(b * dw) / sd,
                "vincolo_1sigma_w0": sd / b_hi if b_hi > 0 else None,
                "criterio_soddisfatto": bool(crit)}

    outp = res / "paper1" / "rev_m1_cosmo_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()

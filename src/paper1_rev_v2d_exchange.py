#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2d_exchange.py

V2d - QUALE CATENA HA IL PROBLEMA SUL BLOCCO 0-199, E QUANTA LEVA HA LA
      COSMOLOGIA SUL DEFICIT

Stato accertato finora
----------------------
  sigma_px costante; key == posizione; 1800/2000 valori identici a M26.
  L'intera differenza 313 vs 445 vive negli indici 0-199: adottando i valori
  di M26 su quel blocco la nostra sigma diventa 444.814, esattamente la loro.
  Dentro il blocco: M26 ha 13 mock patologici che noi non abbiamo, piu' un
  offset sistematico di -96 loop (nostro - M26) sul mock tipico.
  Patologici 598/1022/1430/1666 hanno cosmologia NaN -> difettosi.
  Patologico 139 e' cosmologia di frontiera (Om 0.05 pct) -> legittimo.
  Correlazioni N_H1 x cosmologia: Om +0.150, s8 +0.137, w0 +0.011.

  NOTA: il test "blocchi temporalmente disgiunti" del v2c era mal costruito
  (vero per costruzione in ogni run sequenziale) e non ha valore diagnostico.

QUATTRO DOMANDE
---------------
D1  AUDIT DEI NaN. Quanti mock hanno cosmologia indefinita in totale? Se sono
    esattamente i quattro patologici, il criterio di esclusione per integrita'
    dei metadati e' esaustivo. Se sono piu' di quattro, la regola va applicata
    anche a mock il cui N_H1 sembra normale - ed e' giusto cosi', perche' il
    criterio deve essere cieco alla statistica primaria.

D2  SCAMBIABILITA'. I 2000 mock nwLH non hanno ordine privilegiato. In una
    catena corretta il blocco 0-199 non differisce dai restanti 1800. Si
    confronta blocco vs resto DENTRO ciascuna catena separatamente
    (Mann-Whitney sui ranghi + KS + posizione e scala robuste):
      - se il blocco e' anomalo SOLO in M26  -> il difetto e' di M26
      - se e' anomalo SOLO da noi            -> il difetto e' nostro
      - se lo e' in entrambe                 -> il blocco e' speciale davvero
    Controllo di sicurezza: la scambiabilita' va testata anche sulla
    COSMOLOGIA. Se il file dell'hypercube e' ordinato, il blocco e' speciale
    per costruzione e una differenza di N_H1 e' legittima, non un bug.

D3  ANATOMIA DEI 13. Valori, mean_pers1 e cosmologia dei mock che collassano
    in M26 e non da noi. Un tasso di guasto del 6.5% confinato nei primi 200
    e nullo dopo e' la firma di un bug corretto a run in corso.
    L'offset di -96: e' significativo, o e' rumore letto male?

D4  LEVA COSMOLOGICA SUL DEFICIT. Regressione di N_H1 su (w0, Om, s8) e
    massima escursione predetta attraverso l'INTERO hypercube, confrontata
    col deficit osservato. Con Om in [0.10, 0.50] e s8 in [0.60, 1.00] la
    prior e' molto piu' larga di qualunque prior credibile: se l'escursione
    resta una frazione del deficit, e' un argomento diretto contro
    l'interpretazione cosmologica.

Solo lettura. Scrive un unico report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_v2d_exchange.py
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np

DESI = {"NGC": 28256.0, "SGC": 15122.0}
NH1 = "base.N_H1"
BLOCK = 200
ROBUST_Z = 5.0
COSMO_KEYS = ("w0", "Om", "s8")


# ---------------------------------------------------------------- io
def read_jsonl(path):
    recs, bad = [], 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                bad += 1
    return recs, bad


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
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ---------------------------------------------------------------- test a due campioni
def mannwhitney(a, b):
    """U di Mann-Whitney con approssimazione normale e correzione per pari.
    Restituisce (z, p a due code, probabilita' di superiorita')."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    n1, n2 = a.size, b.size
    allv = np.concatenate([a, b])
    order = np.argsort(allv, kind="stable")
    ranks = np.empty(allv.size, float)
    sv = allv[order]
    i = 0
    while i < sv.size:
        j = i
        while j + 1 < sv.size and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    R1 = ranks[:n1].sum()
    U1 = R1 - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    _, cnt = np.unique(allv, return_counts=True)
    N = allv.size
    tie = float(((cnt ** 3 - cnt).sum()) / (N * (N - 1)))
    sd = np.sqrt(n1 * n2 / 12.0 * ((N + 1) - tie))
    z = (U1 - mu) / sd if sd > 0 else 0.0
    p = 2.0 * (1.0 - _ndtr(abs(z)))
    return float(z), float(p), float(U1 / (n1 * n2))


def _ndtr(x):
    import math
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def ks_two(a, b):
    """Statistica KS a due campioni e p asintotica."""
    a = np.sort(np.asarray(a, float)); b = np.sort(np.asarray(b, float))
    allv = np.concatenate([a, b])
    ca = np.searchsorted(a, allv, side="right") / a.size
    cb = np.searchsorted(b, allv, side="right") / b.size
    d = float(np.max(np.abs(ca - cb)))
    ne = a.size * b.size / (a.size + b.size)
    lam = (np.sqrt(ne) + 0.12 + 0.11 / np.sqrt(ne)) * d
    p = 2.0 * sum((-1) ** (k - 1) * np.exp(-2.0 * k * k * lam * lam)
                  for k in range(1, 101))
    return d, float(min(max(p, 0.0), 1.0))


def robust(v):
    v = np.asarray(v, float)
    med = float(np.median(v))
    mad = float(1.4826 * np.median(np.abs(v - med)))
    return med, (mad if mad > 0 else float(v.std(ddof=1)))


def compare_block(name, v, mask=None, label_a="0-199", label_b="200-fine"):
    v = np.asarray(v, float)
    idx = np.arange(v.size)
    good = np.isfinite(v) if mask is None else (np.isfinite(v) & mask)
    a = v[good & (idx < BLOCK)]
    b = v[good & (idx >= BLOCK)]
    if a.size < 5 or b.size < 5:
        print(f"\n    {name}: campione insufficiente "
              f"(n={a.size}/{b.size}) - saltato")
        return {"saltato": True, "n_blocco": int(a.size), "n_resto": int(b.size)}
    ma, sa = robust(a); mb, sb = robust(b)
    z, p, ps = mannwhitney(a, b)
    d, pk = ks_two(a, b)
    print(f"\n    {name}")
    print(f"      {label_a:<10s} n={a.size:<5d} mediana={ma:>10.1f} "
          f"sigma_MAD={sa:>7.1f}  sigma={a.std(ddof=1):>7.1f}")
    print(f"      {label_b:<10s} n={b.size:<5d} mediana={mb:>10.1f} "
          f"sigma_MAD={sb:>7.1f}  sigma={b.std(ddof=1):>7.1f}")
    print(f"      differenza di mediana: {ma - mb:+.1f}   "
          f"rapporto sigma_MAD: {sa / sb:.3f}")
    print(f"      Mann-Whitney z={z:+.2f}  p={p:.3g}   "
          f"KS D={d:.4f}  p={pk:.3g}")
    verdict = ("BLOCCO ANOMALO" if (p < 0.01 or pk < 0.01) else "compatibile")
    print(f"      -> {verdict}")
    return {"n_blocco": int(a.size), "n_resto": int(b.size),
            "mediana_blocco": ma, "mediana_resto": mb,
            "sigma_mad_blocco": sa, "sigma_mad_resto": sb,
            "sigma_blocco": float(a.std(ddof=1)),
            "sigma_resto": float(b.std(ddof=1)),
            "mw_z": z, "mw_p": p, "ks_d": d, "ks_p": pk,
            "verdetto": verdict}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--m26_npz", default="results\\phase9_likeforlike_arrays.npz")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    our_dir = root / "results" / "paper1"
    rep = {"script": "paper1_rev_v2d_exchange.py"}

    parts = [q for q in args.m26_npz.replace("\\", "/").split("/") if q]
    npz_path = (Path(args.m26_npz) if Path(args.m26_npz).is_absolute()
                else root.joinpath(*parts))
    if not npz_path.exists():
        print(f"[!] {npz_path} non trovato")
        return
    z = np.load(npz_path, allow_pickle=True)
    m26 = np.asarray(z["beta1_max"], float)
    pers = np.asarray(z["pers1_mean"], float) if "pers1_mean" in z.files else None
    cos = {k: np.asarray(z[k], float).ravel() for k in COSMO_KEYS
           if k in z.files}

    ours = {}
    for reg in ("NGC", "SGC"):
        p = our_dir / f"per_mock_{reg}_R5.jsonl"
        if not p.exists():
            continue
        recs, _ = read_jsonl(p)
        flat = [flatten(r) for r in recs]
        ours[reg] = np.array([float(f.get(NH1, np.nan)) for f in flat])

    # ============================================================ D1
    print("=" * 78)
    print("D1 - AUDIT DEI NaN NEI METADATI COSMOLOGICI")
    print("=" * 78)
    bad_any = np.zeros(m26.size, bool)
    for k, a in cos.items():
        nz = ~np.isfinite(a)
        bad_any |= nz
        print(f"  {k:>4s}: {int(nz.sum())} valori non finiti"
              + (f" -> indici {np.where(nz)[0].tolist()}" if nz.sum() <= 25 else ""))
    idx_bad = np.where(bad_any)[0]
    print(f"\n  mock con almeno un parametro indefinito: {idx_bad.size}")
    print(f"    indici: {idx_bad.tolist() if idx_bad.size <= 40 else '(troppi)'}")
    print(f"  di questi, nel blocco 0-199: {int((idx_bad < BLOCK).sum())}")

    print(f"\n  N_H1 dei mock a cosmologia indefinita:")
    print(f"    {'idx':>6s} {'nostro NGC':>11s} {'nostro SGC':>11s} "
          f"{'M26':>10s} {'z_rob NGC':>10s}")
    if "NGC" in ours:
        mn, sn = robust(ours["NGC"])
    for i in idx_bad[:40]:
        vn = ours["NGC"][i] if "NGC" in ours else np.nan
        vs = ours["SGC"][i] if "SGC" in ours else np.nan
        rz = (vn - mn) / sn if "NGC" in ours else np.nan
        print(f"    {i:>6d} {vn:>11.0f} {vs:>11.0f} {m26[i]:>10.0f} "
              f"{rz:>+10.1f}")
    print(f"\n  LETTURA: se tutti i mock a cosmologia indefinita hanno anche")
    print(f"    N_H1 anomalo, il criterio di integrita' e' esaustivo e coincide")
    print(f"    con la coda. Se qualcuno ha N_H1 normale, va escluso comunque:")
    print(f"    il criterio deve essere cieco alla statistica primaria.")
    rep["nan_audit"] = {
        "per_parametro": {k: int((~np.isfinite(a)).sum()) for k, a in cos.items()},
        "indici_difettosi": idx_bad.tolist(),
        "n_nel_blocco": int((idx_bad < BLOCK).sum())}

    # ============================================================ D2
    print("\n" + "=" * 78)
    print("D2 - SCAMBIABILITA': il blocco 0-199 e' anomalo, e in quale catena?")
    print("=" * 78)
    print("  I 2000 mock nwLH non hanno ordine privilegiato. In una catena")
    print("  corretta blocco e resto sono statisticamente indistinguibili.")

    ok = np.isfinite(m26)
    for k, a in cos.items():
        ok &= np.isfinite(a)
    print(f"\n  (esclusi {int((~ok).sum())} mock a metadati difettosi da tutti"
          f" i confronti seguenti)")

    rep["scambiabilita"] = {}
    print("\n  --- COSMOLOGIA (controllo di sicurezza: l'hypercube e' ordinato?)")
    for k, a in cos.items():
        rep["scambiabilita"][f"cosmo_{k}"] = compare_block(k, a)
    print("\n    Se questi risultano ANOMALI, il blocco e' speciale per")
    print("    costruzione e una differenza di N_H1 e' legittima.")

    print("\n  --- N_H1")
    if "NGC" in ours:
        rep["scambiabilita"]["nostro_NGC"] = compare_block(
            "nostra catena NGC", ours["NGC"], mask=ok)
    if "SGC" in ours:
        rep["scambiabilita"]["nostro_SGC"] = compare_block(
            "nostra catena SGC", ours["SGC"], mask=ok)
    rep["scambiabilita"]["m26"] = compare_block("catena M26 (NGC)", m26, mask=ok)
    if pers is not None:
        rep["scambiabilita"]["m26_pers1"] = compare_block(
            "M26 mean_pers1 (secondaria)", pers, mask=ok)

    print("\n  VERDETTO:")
    an_our = rep["scambiabilita"].get("nostro_NGC", {}).get("verdetto", "")
    an_m26 = rep["scambiabilita"]["m26"]["verdetto"]
    an_cos = any(rep["scambiabilita"][f"cosmo_{k}"]["verdetto"] == "BLOCCO ANOMALO"
                 for k in cos)
    if an_cos:
        print("    la COSMOLOGIA del blocco e' anomala -> blocco speciale per")
        print("    costruzione; una differenza di N_H1 e' attesa, non un bug.")
    elif an_m26 == "BLOCCO ANOMALO" and an_our != "BLOCCO ANOMALO":
        print("    anomalo SOLO in M26 -> il difetto e' nella catena di M26.")
        print("    sigma = 445 e' gonfiata da valutazioni fallite nel primo")
        print("    batch; la nostra 313 (robusta 265) e' quella corretta.")
        print("    Da correggere anche nella revisione di M26, ancora in review.")
    elif an_our == "BLOCCO ANOMALO" and an_m26 != "BLOCCO ANOMALO":
        print("    anomalo SOLO da noi -> il difetto e' NOSTRO: rigenerare")
        print("    i primi 200 record e ricongelare i numeri.")
    elif an_our == an_m26 == "BLOCCO ANOMALO":
        print("    anomalo in entrambe -> il blocco e' davvero diverso;")
        print("    cercare la causa nei mock, non nel codice.")
    else:
        print("    nessuna delle due catene mostra un blocco anomalo:")
        print("    la differenza e' concentrata in pochi mock, non nel blocco")
        print("    come popolazione. Vedi D3.")

    # ============================================================ D3
    print("\n" + "=" * 78)
    print("D3 - ANATOMIA DEI MOCK CHE COLLASSANO SOLO IN M26")
    print("=" * 78)
    if "NGC" in ours:
        v = ours["NGC"]
        mm, sm = robust(m26)
        pm = set(np.where((m26 - mm) / sm < -ROBUST_Z)[0].tolist())
        mn, sn = robust(v)
        pn = set(np.where((v - mn) / sn < -ROBUST_Z)[0].tolist())
        solo_m26 = sorted(pm - pn)
        print(f"  patologici solo in M26: {len(solo_m26)} -> {solo_m26}")
        hdr = f"  {'idx':>5s} {'nostro':>9s} {'M26':>9s} {'diff':>8s}"
        if pers is not None:
            hdr += f" {'pers1':>8s} {'z_pers':>7s}"
        for k in cos:
            hdr += f" {k:>8s}"
        print(hdr)
        mp, sp = robust(pers[np.isfinite(pers)]) if pers is not None else (0, 1)
        for i in solo_m26:
            line = (f"  {i:>5d} {v[i]:>9.0f} {m26[i]:>9.0f} "
                    f"{v[i] - m26[i]:>+8.0f}")
            if pers is not None:
                line += f" {pers[i]:>8.4f} {(pers[i]-mp)/sp:>+7.1f}"
            for k, a in cos.items():
                line += f" {a[i]:>8.4f}"
            print(line)

        # offset sistematico: significativo?
        keep = np.ones(m26.size, bool)
        keep[list(pm | pn)] = False
        keep &= ok
        blk = keep.copy(); blk[BLOCK:] = False
        rest = keep.copy(); rest[:BLOCK] = False
        d_blk = (v - m26)[blk]
        d_rest = (v - m26)[rest]
        print(f"\n  OFFSET SISTEMATICO (esclusi tutti i patologici di entrambe)")
        print(f"    blocco 0-199 : n={d_blk.size}  media={d_blk.mean():+.2f}  "
              f"sd={d_blk.std(ddof=1):.2f}  "
              f"sem={d_blk.std(ddof=1)/np.sqrt(max(d_blk.size,1)):.2f}")
        print(f"    resto        : n={d_rest.size}  media={d_rest.mean():+.2f}  "
              f"max|diff|={np.abs(d_rest).max() if d_rest.size else 0:.2f}")
        if d_blk.size > 2:
            t = d_blk.mean() / (d_blk.std(ddof=1) / np.sqrt(d_blk.size))
            print(f"    t dell'offset sul blocco: {t:+.1f}")
            print(f"    -> {'offset REALE' if abs(t) > 4 else 'compatibile con zero'}")
            print(f"    frazione di mock del blocco con diff esattamente 0: "
                  f"{100.0 * np.mean(d_blk == 0):.1f}%")
        rep["offset_blocco"] = {
            "n": int(d_blk.size), "media": float(d_blk.mean()),
            "sd": float(d_blk.std(ddof=1)) if d_blk.size > 1 else None,
            "t": float(t) if d_blk.size > 2 else None,
            "solo_m26": solo_m26}

    # ============================================================ D4
    print("\n" + "=" * 78)
    print("D4 - QUANTA LEVA HA LA COSMOLOGIA SUL DEFICIT?")
    print("=" * 78)
    if "NGC" in ours and len(cos) == 3:
        v = ours["NGC"]
        m = ok.copy()
        m[list(pn)] = False          # via i nostri patologici
        X = np.column_stack([cos[k][m] for k in COSMO_KEYS])
        y = v[m]
        A = np.column_stack([np.ones(X.shape[0]), X])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ beta
        r2 = 1.0 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        print(f"  regressione lineare N_H1 ~ 1 + w0 + Om + s8   (n={y.size})")
        print(f"    intercetta {beta[0]:+.1f}")
        for k, b in zip(COSMO_KEYS, beta[1:]):
            rng = cos[k][m].max() - cos[k][m].min()
            print(f"    {k:>4s}: coeff {b:+10.1f}   intervallo campionato "
                  f"[{cos[k][m].min():.4f}, {cos[k][m].max():.4f}]"
                  f"   escursione {b * rng:+.0f} loop")
        print(f"    R^2 = {r2:.4f}   ->  la cosmologia spiega il "
              f"{100*r2:.1f}% della varianza di N_H1")
        span = float(pred.max() - pred.min())
        deficit = float(y.mean() - DESI["NGC"])
        print(f"\n    escursione TOTALE predetta sull'intero hypercube: "
              f"{span:.0f} loop")
        print(f"    deficit osservato di DESI                     : "
              f"{deficit:.0f} loop")
        print(f"    rapporto deficit / escursione cosmologica     : "
              f"{deficit / span:.1f}x")
        print(f"\n    minimo predetto dalla regressione: {pred.min():.0f}")
        print(f"    DESI                              : {DESI['NGC']:.0f}")
        print(f"    DESI resta sotto il minimo predetto di "
              f"{pred.min() - DESI['NGC']:.0f} loop")
        print(f"\n  LETTURA: l'ensemble copre Om in [{cos['Om'][m].min():.2f}, "
              f"{cos['Om'][m].max():.2f}] e s8 in [{cos['s8'][m].min():.2f}, "
              f"{cos['s8'][m].max():.2f}],")
        print(f"    una prior molto piu' larga di qualunque prior credibile.")
        print(f"    Se il rapporto sopra e' >> 1, nessuna cosmologia entro")
        print(f"    quell'intervallo produce il deficit: e' un argomento")
        print(f"    diretto contro l'interpretazione cosmologica.")
        rep["leva_cosmologica"] = {
            "coefficienti": dict(zip(COSMO_KEYS, beta[1:].tolist())),
            "intercetta": float(beta[0]), "r2": float(r2),
            "escursione_predetta": span, "deficit": deficit,
            "rapporto": deficit / span,
            "minimo_predetto": float(pred.min()),
            "margine_desi_sotto_minimo": float(pred.min() - DESI["NGC"])}

    outp = our_dir / "rev_v2d_exchange_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()

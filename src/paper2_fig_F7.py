#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_fig_F7.py -- Figura F7 del Paper 2: la funzione di risposta di N_H1.

Per ogni parametro theta disegna lo spostamento della media dei mock sull'intervallo che l'analisi
campiona, in unita' della dispersione per realizzazione della calotta a k = 0. Normalizzazione
decisa il 25 set (checklist 3.39, Z-F7) e fissata qui come costanti, non come argomenti:

  - sette parametri nwLH: excursion_gen di compD (pendenza grezza x span), diviso per la dispersione
    della calotta, 312.989 (NGC) e 197.787 (SGC): FROZEN di paper2_compD_partialcorr.py, budget
    riga B0. Errore 1 sigma dall'intervallo di Fisher della r grezza, con fisher_ci IMPORTATA da
    compD (una sola implementazione per grandezza);
  - F_AP: lato mock da B1 a B5 a k = 0, dove la dispersione e' definita (fase3_analisi.jsonl,
    levels.k0.DD_max_B5_B1: mock_mean_diff e sem). Accanto, lo spostamento di D (estimate): F_AP
    muove anche i dati, i parametri nwLH no. Il livello primario del §4.4, k = 1, resta nel testo;
  - alpha_iso: zero per teorema (Prop. 2), verificato sui dodici record 'derived' di fase3.jsonl
    (N_H1 a k = 0 e 1 uguale al fiduciale, 12/12);
  - regola R3 del budget: sotto 3 sigma si disegna il limite |Delta| + 3 sigma, con la misura
    accanto. L'insieme che la regola produce deve coincidere con quello deciso, {w0, M_nu}, in
    entrambe le calotte: se no, arresto.

Cancelli prima di disegnare:
  C1  compD: i due registri trovati per nome sotto results/, con lo sha ancorato dalla consegna del
      25 set; quattro record per calotta con righe identiche (lettura per unione); n = 2000.
  C2  modulo compD con lo sha ancorato (9321d7ec...); fisher_ci e FROZEN vengono da li'; FROZEN sd
      coincide con la normalizzazione decisa.
  C3  pendenze senza costanti di calotta: per ogni parametro (pendenza/r)_NGC / (pendenza/r)_SGC deve
      valere dispersione_NGC / dispersione_SGC (stessi 2000 theta nelle due calotte, stesso span).
      Una costante di NGC nella pendenza di SGC darebbe 1 invece di 1.582.
  C4  firma di Z-sigma-SGC: w0_sigma1_implied di compD = SIGMA_TOT / |pendenza| con SIGMA_TOT = 313.0
      in entrambe le calotte. Il valore non si usa: la semi-ampiezza si ricalcola con la dispersione
      della calotta e deve arrotondare a 3.1 / 3.6, i numeri del manoscritto (§6.2 e §9).
  C5  span / sd(theta) entro 2e-3 da sqrt(12): il disegno e' un ipercubo latino uniforme.
  C6  fase3_analisi: lettura per unione sulle nove passate; stesso (regione, livello) con valori
      diversi -> errore; i valori riproducono il §4.4 e il §4.5 (tolleranza mezza unita' della
      terza cifra); estimate = mock_mean_diff - desi_offset; n = 200.
  C7  alpha_iso: FID = 28256 / 23790 (NGC) e 15122 / 12011 (SGC); ogni punto del blocco A in gauge
      'derived' riproduce il FID a k = 0 e k = 1; sei punti per calotta.
  C8  regola R3: l'insieme dei limitati e' {w0, M_nu} in ogni calotta.

Scrive, e non tocca altro:
  papers/paper2/MNRAS/figures/F7_response_function.pdf   (metadati senza data: deterministico)
  results/paper2/fig_F7.jsonl                            (append-only, un record per run)

Sottocomandi: selftest | run | verify. Dalla radice del repository.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

J = os.path.join
FASE3 = J("results", "paper2", "fase3.jsonl")
ANALISI = J("results", "paper2", "fase3_analisi.jsonl")
REG = J("results", "paper2", "fig_F7.jsonl")
PDF = J("papers", "paper2", "MNRAS", "figures", "F7_response_function.pdf")
MOD_COMPD = "paper2_compD_partialcorr"

CAPS = ("NGC", "SGC")
COMPD_NAME = {"NGC": "compD_NGC.jsonl", "SGC": "compD_SGC.jsonl"}
COMPD_SHA = {"NGC": "23f86735022b5c345229f689ba0f24931470d0d16ef50b18210d242b703de1dd",
             "SGC": "ee7648f34826a04c468de02a6fd1d73de9295ee284a19e4345be174dc25c90b6"}
MOD_SHA = "9321d7ec04845fbd40aff0f6356cae8d67599a936bb5569f4613f2b6061d873b"

DISPERSION = {"NGC": 312.989, "SGC": 197.787}     # decisione del 25 set; = FROZEN[...]["sd"] di compD
LEVEL = "k0"                                      # il livello della dispersione
N_SIGMA = 3.0                                     # regola R3 del budget
DECLARED_BOUNDED = frozenset({"w0", "M_nu"})      # decisione del 25 set
PARAMS = ("n_s", "h", "sigma_8", "Omega_m", "Omega_b", "M_nu", "w0")   # ordine della figura
N_COMPD, N_AP = 2000, 200
TOL_RATIO = 1e-5          # FROZEN porta la dispersione a tre decimali: scarto atteso ~1e-6
TOL_SQRT12 = 2e-3
TOL_AP = 5e-4             # mezza unita' della terza cifra quotata
MANUSCRIPT_HALFWIDTH = {"NGC": 3.1, "SGC": 3.6}
# (estimate, mock_mean_diff, desi_offset) di DD_max_B5_B1, come nel §4.4 e nel §4.5
EXPECT_AP = {("NGC", "k0"): (-113.995, -217.995, -104), ("SGC", "k0"): (-74.980, -135.980, -61),
             ("NGC", "k1"): (-98.300, -172.300, -74), ("SGC", "k1"): (-91.130, -111.130, -20)}
EXPECT_FID = {"NGC": (28256, 23790), "SGC": (15122, 12011)}
BLOCK_A = ("A0", "A0m", "A1", "A1m", "A3", "A3m")


class F7Error(Exception):
    pass


# ----------------------------------------------------------------------------- lettura

def _load_lines(text, where):
    out = []
    for i, riga in enumerate(text.splitlines(), 1):
        if riga.strip():
            try:
                out.append(json.loads(riga))
            except ValueError as e:
                raise F7Error("%s riga %d: JSON non valido (%s)" % (where, i, e))
    return out


def read_compd(text, region):
    """Righe per parametro. Il registro porta quattro passate (due run, due riscritture per
    l'etichetta v1, item 0.9): le righe devono essere identiche in tutte, altrimenti non si sceglie."""
    recs = _load_lines(text, COMPD_NAME[region])
    if not recs:
        raise F7Error("%s vuoto" % COMPD_NAME[region])
    base = json.dumps(recs[0]["rows"], sort_keys=True)
    for j, r in enumerate(recs, 1):
        if r.get("region") != region:
            raise F7Error("%s record %d: regione %r" % (COMPD_NAME[region], j, r.get("region")))
        if r.get("n") != N_COMPD:
            raise F7Error("%s record %d: n = %r, attesi %d" % (COMPD_NAME[region], j, r.get("n"), N_COMPD))
        if json.dumps(r["rows"], sort_keys=True) != base:
            raise F7Error("%s record %d: righe diverse dal record 1 (lettura per unione impossibile)"
                          % (COMPD_NAME[region], j))
    if not any(r.get("ensemble") == "v1" for r in recs):
        raise F7Error("%s: nessun record etichettato ensemble v1" % COMPD_NAME[region])
    s1 = {r.get("w0_sigma1_implied") for r in recs}
    dg = {r.get("deficit_gen") for r in recs}
    if len(s1) != 1 or len(dg) != 1:
        raise F7Error("%s: w0_sigma1_implied o deficit_gen non univoci" % COMPD_NAME[region])
    rows = {r["param"]: r for r in recs[0]["rows"]}
    missing = [p for p in PARAMS if p not in rows]
    if missing:
        raise F7Error("%s: parametri assenti %s" % (COMPD_NAME[region], missing))
    return {"rows": rows, "w0_sigma1_implied": s1.pop(), "deficit_gen": dg.pop(), "n_records": len(recs)}


def read_analisi(text):
    """DD_max_B5_B1 per (regione, livello), per unione sulle passate: stesso punto, stesso valore."""
    out = {}
    for i, r in enumerate(_load_lines(text, "fase3_analisi.jsonl"), 1):
        for lv, d in r["levels"].items():
            key = (r["region"], lv)
            v = d["DD_max_B5_B1"]
            if key in out and json.dumps(out[key], sort_keys=True) != json.dumps(v, sort_keys=True):
                raise F7Error("fase3_analisi.jsonl record %d: %s con DD_max_B5_B1 diverso da una passata "
                              "precedente" % (i, key))
            out[key] = v
    return out


def ladder_nh1(rec, k):
    """N_H1 al livello k: 'N_H1_k0' per k = 0 se c'e', altrimenti ladder[k].N_H1 (lista o dizionario).
    Se mancano entrambi, arresto con le chiavi del record: lo schema si legge, non si indovina."""
    lad = rec.get("ladder")
    e = None
    if isinstance(lad, dict):
        e = lad.get(str(k), lad.get(k))
    elif isinstance(lad, list) and len(lad) > k:
        e = lad[k]
    via_ladder = e.get("N_H1") if isinstance(e, dict) else None
    if k == 0 and rec.get("N_H1_k0") is not None:
        if via_ladder is not None and via_ladder != rec["N_H1_k0"]:
            raise F7Error("fase3.jsonl %s/%s: N_H1_k0 %r contro ladder.0.N_H1 %r"
                          % (rec.get("region"), rec.get("point"), rec["N_H1_k0"], via_ladder))
        return rec["N_H1_k0"]
    if via_ladder is None:
        raise F7Error("fase3.jsonl %s/%s gauge %s: N_H1 a k = %d non trovato. Chiavi del record: %s; "
                      "tipo di 'ladder': %s" % (rec.get("region"), rec.get("point"), rec.get("gauge"), k,
                                                sorted(rec.keys()), type(lad).__name__))
    return via_ladder


def read_iso(text):
    """(k0, k1) per (regione, gauge, punto), per unione, dei soli record 'fid' e 'derived'."""
    out, seen = {}, set()
    for i, r in enumerate(_load_lines(text, "fase3.jsonl"), 1):
        g = r.get("gauge")
        seen.add((g, r.get("point")))
        if g not in ("fid", "derived"):
            continue
        key = (r.get("region"), g, r.get("point"))
        val = (ladder_nh1(r, 0), ladder_nh1(r, 1))
        if key in out and out[key] != val:
            raise F7Error("fase3.jsonl riga %d: %s compare con valori diversi (%r contro %r)" % (i, key, out[key], val))
        out[key] = val
    return out, seen


# ----------------------------------------------------------------------------- calcolo e cancelli

def gate_cross_cap(rows):
    """C3 e C5. Restituisce k = span/sd(theta) per parametro."""
    target = DISPERSION["NGC"] / DISPERSION["SGC"]
    ks = {}
    for p in PARAMS:
        rn, rs = rows["NGC"][p], rows["SGC"][p]
        if rn["span"] != rs["span"]:
            raise F7Error("C3 %s: span diverso fra le calotte (%r, %r): i theta non sono gli stessi"
                          % (p, rn["span"], rs["span"]))
        q = (rn["slope_gen_per_unit"] / rn["r_raw"]) / (rs["slope_gen_per_unit"] / rs["r_raw"])
        if abs(q / target - 1.0) > TOL_RATIO:
            raise F7Error("C3 %s: (pendenza/r) NGC/SGC = %.6f contro %.6f atteso dalle dispersioni: "
                          "la pendenza porta una costante di calotta" % (p, q, target))
        k = {c: rows[c][p]["excursion_gen"] / (rows[c][p]["r_raw"] * DISPERSION[c]) for c in CAPS}
        if abs(k["NGC"] / k["SGC"] - 1.0) > TOL_RATIO:
            raise F7Error("C3 %s: span/sd(theta) diverso fra le calotte (%r)" % (p, k))
        if abs(k["NGC"] / math.sqrt(12.0) - 1.0) > TOL_SQRT12:
            raise F7Error("C5 %s: span/sd(theta) = %.5f, lontano da sqrt(12)" % (p, k["NGC"]))
        ks[p] = k["NGC"]
    return ks


def gate_zsigma(compd, sigma_tot):
    """C4: la firma del difetto noto, e la semi-ampiezza ricalcolata."""
    out = {}
    for c in CAPS:
        slope = compd[c]["rows"]["w0"]["slope_gen_per_unit"]
        stored = compd[c]["w0_sigma1_implied"]
        if abs(stored - sigma_tot / abs(slope)) > 1e-9 * abs(stored):
            raise F7Error("C4 %s: w0_sigma1_implied = %r non e' SIGMA_TOT/|pendenza| = %r. Lo strumento e' "
                          "cambiato: rileggere Z-sigma-SGC prima di disegnare" % (c, stored, sigma_tot / abs(slope)))
        hw = DISPERSION[c] / abs(slope)
        if round(hw, 1) != MANUSCRIPT_HALFWIDTH[c]:
            raise F7Error("C4 %s: semi-ampiezza %.4f non arrotonda a %.1f del manoscritto" % (c, hw, MANUSCRIPT_HALFWIDTH[c]))
        out[c] = {"w0_sigma1_implied_stored": stored, "sigma_tot_tool": sigma_tot,
                  "halfwidth_cap_dispersion": hw, "slope_gen_per_unit": slope}
    return out


def nwlh_rows(compd, fisher_ci):
    """Barre dei sette parametri: valore, errore asimmetrico, classe secondo R3."""
    res = {}
    for c in CAPS:
        res[c] = {}
        for p in PARAMS:
            r = compd[c]["rows"][p]
            k = r["excursion_gen"] / (r["r_raw"] * DISPERSION[c])
            lo, hi = fisher_ci(r["r_raw"], N_COMPD, z=1.0)
            v = r["excursion_gen"] / DISPERSION[c]
            s_lo, s_hi = (r["r_raw"] - lo) * k, (hi - r["r_raw"]) * k
            sigma = 0.5 * (s_lo + s_hi)
            nsig = abs(v) / sigma
            bounded = nsig < N_SIGMA
            res[c][p] = {"value": v, "sigma": sigma, "sigma_lo": s_lo, "sigma_hi": s_hi, "n_sigma": nsig,
                         "class": "bounded" if bounded else "measured",
                         "limit": (abs(v) + N_SIGMA * sigma) if bounded else None,
                         "r_raw": r["r_raw"], "excursion_gen": r["excursion_gen"], "span": r["span"],
                         "span_over_sd": k}
    return res


def gate_bounded(nw):
    """C8."""
    for c in CAPS:
        got = frozenset(p for p in PARAMS if nw[c][p]["class"] == "bounded")
        if got != DECLARED_BOUNDED:
            raise F7Error("C8 %s: la regola R3 limita %s, la decisione del 25 set dice %s"
                          % (c, sorted(got), sorted(DECLARED_BOUNDED)))


def gate_analisi(an):
    """C6."""
    for key, (est, mock, desi) in EXPECT_AP.items():
        if key not in an:
            raise F7Error("C6: fase3_analisi.jsonl senza %s" % (key,))
        d = an[key]
        if d.get("n") != N_AP:
            raise F7Error("C6 %s: n = %r" % (key, d.get("n")))
        for nome, got, want in (("estimate", d["estimate"], est), ("mock_mean_diff", d["mock_mean_diff"], mock),
                                ("desi_offset", d["desi_offset"], desi)):
            if abs(got - want) > TOL_AP:
                raise F7Error("C6 %s: %s = %r contro %r del manoscritto" % (key, nome, got, want))
        if abs(d["estimate"] - (d["mock_mean_diff"] - d["desi_offset"])) > 1e-6:
            raise F7Error("C6 %s: estimate diverso da mock - dati" % (key,))


def fap_rows(an):
    out = {}
    for c in CAPS:
        d = an[(c, LEVEL)]
        s = DISPERSION[c]
        out[c] = {"value_mock": d["mock_mean_diff"] / s, "sigma": d["sem"] / s,
                  "n_sigma": abs(d["mock_mean_diff"]) / d["sem"], "value_D": d["estimate"] / s,
                  "value_data": d["desi_offset"] / s, "mock_mean_diff": d["mock_mean_diff"],
                  "estimate": d["estimate"], "desi_offset": d["desi_offset"], "sem": d["sem"], "n": d["n"],
                  "interval": "B1->B5", "level": LEVEL}
    return out


def gate_iso(iso, seen):
    """C7."""
    out = {}
    for c in CAPS:
        fid = [v for (rg, g, p), v in iso.items() if rg == c and g == "fid"]
        if len(fid) != 1:
            raise F7Error("C7 %s: %d record fiduciali (gauge 'fid') invece di 1. Coppie (gauge, punto) viste: %s"
                          % (c, len(fid), sorted(seen, key=str)))
        if fid[0] != EXPECT_FID[c]:
            raise F7Error("C7 %s: fiduciale %r contro %r" % (c, fid[0], EXPECT_FID[c]))
        der = {p: v for (rg, g, p), v in iso.items() if rg == c and g == "derived"}
        if set(der) != set(BLOCK_A):
            raise F7Error("C7 %s: punti 'derived' %s, attesi %s" % (c, sorted(der), list(BLOCK_A)))
        bad = {p: v for p, v in der.items() if v != fid[0]}
        if bad:
            raise F7Error("C7 %s: la Prop. 2 non si riproduce in %s (fiduciale %r)" % (c, bad, fid[0]))
        out[c] = {"fid_k0_k1": list(fid[0]), "derived_equal": len(der)}
    return out


# ----------------------------------------------------------------------------- figura

LABELS = {"n_s": r"$n_s$", "h": r"$h$", "sigma_8": r"$\sigma_8$", "Omega_m": r"$\Omega_m$",
          "Omega_b": r"$\Omega_b$", "M_nu": r"$M_\nu$", "w0": r"$w_0$",
          "alpha_iso": r"$\alpha_{\rm iso}$", "F_AP": r"$F_{\rm AP}$"}
COLOR = {"NGC": "0.0", "SGC": "0.62"}
OFFSET = {"NGC": +0.19, "SGC": -0.19}
YPOS = dict(zip(PARAMS, range(8, 1, -1)))
YPOS.update({"alpha_iso": 0.5, "F_AP": -0.5})


def draw(nw, fap, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    h = 0.34
    fig, ax = plt.subplots(figsize=(3.4, 3.3))
    ax.axvline(0.0, color="0.55", lw=0.5, zorder=0)
    ax.axhline(1.25, color="0.75", lw=0.5, ls=(0, (2, 2)), zorder=0)
    for c in CAPS:
        col = COLOR[c]
        for p in PARAMS:
            q = nw[c][p]
            y = YPOS[p] + OFFSET[c]
            if q["class"] == "measured":
                ax.barh(y, q["value"], height=h, color=col, lw=0, zorder=2)
                ax.errorbar(q["value"], y, xerr=[[q["sigma_lo"]], [q["sigma_hi"]]], fmt="none",
                            ecolor="k", elinewidth=0.6, capsize=1.4, capthick=0.6, zorder=3)
            else:
                L = q["limit"]
                ax.plot([-L, L], [y, y], color=col if c == "SGC" else "k", lw=0.8, zorder=2)
                for x in (-L, L):
                    ax.plot([x, x], [y - 0.12, y + 0.12], color=col if c == "SGC" else "k", lw=0.8, zorder=2)
                ax.plot(q["value"], y, marker="o", ms=3.0, mfc=col, mec="k", mew=0.5, zorder=3)
        y = YPOS["alpha_iso"] + OFFSET[c]
        ax.plot(0.0, y, marker="*", ms=6.5, mfc=col, mec="k", mew=0.4, zorder=3)
        q = fap[c]
        y = YPOS["F_AP"] + OFFSET[c]
        ax.barh(y, q["value_mock"], height=h, color=col, lw=0, zorder=2)
        ax.errorbar(q["value_mock"], y, xerr=q["sigma"], fmt="none", ecolor="k", elinewidth=0.6,
                    capsize=1.4, capthick=0.6, zorder=3)
        ax.plot(q["value_D"], y, marker="D", ms=3.4, mfc="white", mec="k", mew=0.7, zorder=4)
    # etichette dirette sulla prima riga: identita' non affidata al solo grigio
    for c in CAPS:
        q = nw[c]["n_s"]
        ax.text(q["value"] + q["sigma_hi"] + 0.04, YPOS["n_s"] + OFFSET[c], c, fontsize=5.5, va="center")
    rows = list(PARAMS) + ["alpha_iso", "F_AP"]
    ax.set_yticks([YPOS[r] for r in rows])
    ax.set_yticklabels([LABELS[r] for r in rows], fontsize=7.5)
    ax.set_ylim(-1.05, 8.55)
    ax.set_xlim(-0.95, 1.75)
    ax.set_xticks([-0.5, 0.0, 0.5, 1.0, 1.5])
    ax.tick_params(axis="x", labelsize=7)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(r"$\Delta\langle N_{H_1}\rangle\,/\,\sigma$ over the sampled interval", fontsize=7.5)
    ax.text(-0.92, 8.5, "nwLH suite", fontsize=6, ha="left", va="top", style="italic")
    ax.text(-0.92, 1.15, "fiducial geometry", fontsize=6, ha="left", va="top", style="italic")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    handles = [Patch(facecolor=COLOR["NGC"], label="NGC"), Patch(facecolor=COLOR["SGC"], label="SGC"),
               Line2D([], [], marker="D", ls="none", ms=3.4, mfc="white", mec="k", mew=0.7, label=r"deficit $D$"),
               Line2D([], [], color="k", lw=0.8, marker="|", ms=4, label=r"bound $|\Delta|+3\sigma$"),
               Line2D([], [], marker="*", ls="none", ms=6.5, mfc="0.5", mec="k", mew=0.4, label="zero by theorem")]
    ax.legend(handles=handles, loc="lower right", fontsize=5.5, frameon=False, handlelength=1.4,
              borderaxespad=0.2, labelspacing=0.35)
    fig.tight_layout()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, metadata={"CreationDate": None, "ModDate": None, "Creator": "paper2_fig_F7.py",
                                "Producer": None})
    plt.close(fig)


# ----------------------------------------------------------------------------- disco

def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def find_compd(root="results"):
    """C1: i due registri per nome sotto results/. Piu' copie sono ammesse solo se tutte portano lo
    sha ancorato; una copia diversa ferma il run."""
    found = {c: [] for c in CAPS}
    for d, _, files in os.walk(root):
        for c in CAPS:
            if COMPD_NAME[c] in files:
                found[c].append(J(d, COMPD_NAME[c]))
    out = {}
    for c in CAPS:
        if not found[c]:
            raise F7Error("C1: %s non trovato sotto %s" % (COMPD_NAME[c], root))
        shas = {p: sha_file(p) for p in sorted(found[c])}
        wrong = {p: s[:12] for p, s in shas.items() if s != COMPD_SHA[c]}
        if wrong:
            raise F7Error("C1: %s con sha diverso da quello ancorato (%s...): %s" % (COMPD_NAME[c], COMPD_SHA[c][:12], wrong))
        out[c] = sorted(found[c])
    return out


def attach(srcdir="src"):
    if srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    path = J(srcdir, MOD_COMPD + ".py")
    if not os.path.exists(path):
        raise F7Error("C2: %s assente" % path)
    if sha_file(path) != MOD_SHA:
        raise F7Error("C2: %s ha sha %s..., ancorato %s...: il modulo e' cambiato" % (path, sha_file(path)[:12], MOD_SHA[:12]))
    try:
        M = __import__(MOD_COMPD)
    except Exception as e:
        raise F7Error("C2: import di %s fallito: %s" % (MOD_COMPD, e))
    if M.fisher_ci.__module__ != MOD_COMPD:
        raise F7Error("C2: fisher_ci non viene da %s" % MOD_COMPD)
    for c in CAPS:
        if M.FROZEN[c]["sd"] != DISPERSION[c]:
            raise F7Error("C2 %s: FROZEN sd %r contro la normalizzazione decisa %r" % (c, M.FROZEN[c]["sd"], DISPERSION[c]))
    return M, path


def compute(M, compd, an, iso, seen):
    ks = gate_cross_cap({c: compd[c]["rows"] for c in CAPS})
    zs = gate_zsigma(compd, M.SIGMA_TOT)
    nw = nwlh_rows(compd, M.fisher_ci)
    gate_bounded(nw)
    gate_analisi(an)
    fap = fap_rows(an)
    isog = gate_iso(iso, seen)
    deficit = {c: compd[c]["deficit_gen"] / DISPERSION[c] for c in CAPS}
    maxbar = max(abs(nw[c][p]["value"]) for c in CAPS for p in PARAMS)
    return {"span_over_sd": ks, "zsigma": zs, "nwlh": nw, "fap": fap, "alpha_iso": isog,
            "deficit_in_dispersions": deficit, "max_abs_nwlh": maxbar,
            "max_abs_fap_mock": max(abs(fap[c]["value_mock"]) for c in CAPS)}


def cmd_run():
    if not (os.path.isdir("src") and os.path.isdir("results") and os.path.isdir("papers")):
        raise F7Error("lanciare dalla radice del repository")
    M, modpath = attach()
    paths = find_compd()
    compd = {c: read_compd(open(paths[c][0], encoding="utf-8").read(), c) for c in CAPS}
    an = read_analisi(open(ANALISI, encoding="utf-8").read())
    iso, seen = read_iso(open(FASE3, encoding="utf-8").read())
    res = compute(M, compd, an, iso, seen)
    draw(res["nwlh"], res["fap"], PDF)
    inputs = {ANALISI: sha_file(ANALISI), FASE3: sha_file(FASE3), modpath: sha_file(modpath),
              J("src", "paper2_fig_F7.py"): sha_file(J("src", "paper2_fig_F7.py"))}
    for c in CAPS:
        for p in paths[c]:
            inputs[p] = sha_file(p)
    rec = {"schema": "paper2_fig_F7_v1", "utc": datetime.now(timezone.utc).isoformat(),
           "inputs": inputs,
           "choices": {"dispersion": DISPERSION, "level": LEVEL, "fap_interval": "B1->B5",
                       "rule": "R3: |Delta|/sigma < %g -> limit |Delta| + %g sigma" % (N_SIGMA, N_SIGMA),
                       "declared_bounded": sorted(DECLARED_BOUNDED),
                       "nwlh_sigma": "Fisher 1 sigma on the raw correlation, n = %d" % N_COMPD},
           "result": res, "gates": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"],
           "pdf": {PDF: sha_file(PDF)}}
    with open(REG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    print("cancelli: 8/8 PASS  (compD: %s)" % ", ".join("%s %d record" % (c, compd[c]["n_records"]) for c in CAPS))
    for p in PARAMS:
        a, b = res["nwlh"]["NGC"][p], res["nwlh"]["SGC"][p]
        print("%-8s %+.3f +- %.3f (%4.1f sig)  /  %+.3f +- %.3f (%4.1f sig)  %s" % (
            p, a["value"], a["sigma"], a["n_sigma"], b["value"], b["sigma"], b["n_sigma"],
            "" if a["class"] == "measured" else "limiti %.2f / %.2f" % (a["limit"], b["limit"])))
    f = res["fap"]
    print("F_AP     mock %+.3f +- %.3f / %+.3f +- %.3f ; D %+.3f / %+.3f  (k = 0, B1->B5)" % (
        f["NGC"]["value_mock"], f["NGC"]["sigma"], f["SGC"]["value_mock"], f["SGC"]["sigma"],
        f["NGC"]["value_D"], f["SGC"]["value_D"]))
    print("alpha_iso: zero per teorema; derived = FID %d/%d e %d/%d" % (
        res["alpha_iso"]["NGC"]["derived_equal"], len(BLOCK_A), res["alpha_iso"]["SGC"]["derived_equal"], len(BLOCK_A)))
    print("semi-ampiezza w0: %.3f / %.3f (registro compD: %.3f / %.3f, SIGMA_TOT)" % (
        res["zsigma"]["NGC"]["halfwidth_cap_dispersion"], res["zsigma"]["SGC"]["halfwidth_cap_dispersion"],
        res["zsigma"]["NGC"]["w0_sigma1_implied_stored"], res["zsigma"]["SGC"]["w0_sigma1_implied_stored"]))
    print("deficit in dispersioni: %.2f / %.2f" % (res["deficit_in_dispersions"]["NGC"], res["deficit_in_dispersions"]["SGC"]))
    print("figura: %s  sha %s" % (PDF, rec["pdf"][PDF][:12]))
    print("ESITO: SCRITTA")


def cmd_verify():
    if not os.path.exists(REG) or not os.path.exists(PDF):
        raise F7Error("registro o figura assenti: lanciare 'run'")
    h = sha_file(PDF)
    recs = [json.loads(l) for l in open(REG, encoding="utf-8") if l.strip()]
    match = [r for r in recs if r.get("pdf", {}).get(PDF) == h]
    if not match:
        raise F7Error("la figura su disco (%s) non corrisponde a nessun record del registro" % h[:12])
    last = match[-1]
    stale = [p for p, s in last["inputs"].items() if not os.path.exists(p) or sha_file(p) != s]
    print("record che descrivono la figura: %d; ingressi cambiati dal run: %s" % (len(match), stale or "nessuno"))
    print("ESITO: %s" % ("PASS" if not stale else "FAIL"))
    return 0 if not stale else 1


# ----------------------------------------------------------------------------- selftest

def _fisher(r, n, z=1.959963985):     # copia per il selftest: nel run si usa quella di compD (C2)
    a = math.atanh(r)
    s = 1.0 / math.sqrt(n - 3)
    return math.tanh(a - z * s), math.tanh(a + z * s)


def _rows_fixture(contaminate=False):
    """Due calotte con gli stessi theta: pendenza = r sd(N)/sd(theta), span/sd = 3.4615."""
    k = 3.4615
    r_by = {"n_s": (0.376, 0.394), "h": (0.21, 0.19), "sigma_8": (0.18, 0.23), "Omega_m": (0.15, 0.14),
            "Omega_b": (-0.13, -0.12), "M_nu": (-0.048, -0.008), "w0": (0.055, 0.048)}
    span = {p: (0.5997 if p == "w0" else 0.3998) for p in PARAMS}
    rows = {}
    for i, c in enumerate(CAPS):
        rows[c] = {}
        sd_n = DISPERSION[c] if not (contaminate and c == "SGC") else 313.0
        for p in PARAMS:
            r = r_by[p][i]
            slope = r * sd_n / (span[p] / k)
            rows[c][p] = {"param": p, "r_raw": r, "slope_gen_per_unit": slope, "span": span[p],
                          "excursion_gen": slope * span[p]}
    return rows


def _t_cross_cap():
    ks = gate_cross_cap(_rows_fixture())
    ok = all(abs(v - 3.4615) < 1e-9 for v in ks.values())
    try:
        gate_cross_cap(_rows_fixture(contaminate=True))
    except F7Error:
        return ok
    return False


def _t_zsigma():
    rows = _rows_fixture()
    compd = {c: {"rows": rows[c], "w0_sigma1_implied": 313.0 / abs(rows[c]["w0"]["slope_gen_per_unit"])} for c in CAPS}
    # la fixture ha pendenze diverse da quelle vere: si prova solo la firma, con la semi-ampiezza forzata
    saved = dict(MANUSCRIPT_HALFWIDTH)
    try:
        for c in CAPS:
            MANUSCRIPT_HALFWIDTH[c] = round(DISPERSION[c] / abs(rows[c]["w0"]["slope_gen_per_unit"]), 1)
        gate_zsigma(compd, 313.0)
        compd["SGC"]["w0_sigma1_implied"] = DISPERSION["SGC"] / abs(rows["SGC"]["w0"]["slope_gen_per_unit"])
        try:
            gate_zsigma(compd, 313.0)
        except F7Error:
            return True
        return False
    finally:
        MANUSCRIPT_HALFWIDTH.update(saved)


def _t_bounded():
    rows = _rows_fixture()
    compd = {c: {"rows": rows[c]} for c in CAPS}
    nw = nwlh_rows(compd, _fisher)
    ok = all(nw[c][p]["class"] == ("bounded" if p in ("w0", "M_nu") else "measured") for c in CAPS for p in PARAMS)
    lim = nw["NGC"]["w0"]
    ok = ok and abs(lim["limit"] - (abs(lim["value"]) + 3 * lim["sigma"])) < 1e-12
    gate_bounded(nw)
    nw["SGC"]["h"]["class"] = "bounded"
    try:
        gate_bounded(nw)
    except F7Error:
        return ok
    return False


def _analisi_line(region, lv_vals, extra=None):
    lv = {}
    for k, (est, mock, desi) in lv_vals.items():
        lv[k] = {"DD_max_B5_B1": {"estimate": est, "mock_mean_diff": mock, "desi_offset": desi, "n": 200, "sem": 10.0}}
    r = {"region": region, "levels": lv}
    if extra:
        r.update(extra)
    return json.dumps(r)


def _analisi_text(mod=None):
    L = []
    for c in CAPS:
        vals = {lv: EXPECT_AP[(c, lv)] for lv in ("k0", "k1")}
        L.append(_analisi_line(c, vals))
        L.append(_analisi_line(c, vals))           # seconda passata identica
    if mod:
        L.append(mod)
    return "\n".join(L) + "\n"


def _t_analisi():
    an = read_analisi(_analisi_text())
    gate_analisi(an)
    ok = abs(fap_rows(an)["NGC"]["value_mock"] - (-217.995 / 312.989)) < 1e-12
    bad = _analisi_line("NGC", {"k0": (-113.995, -217.995, -104), "k1": (-98.3, -172.4, -74.1)})
    try:
        read_analisi(_analisi_text(bad))
    except F7Error:
        pass
    else:
        return False
    an2 = read_analisi(_analisi_text())
    an2[("SGC", "k0")] = dict(an2[("SGC", "k0")], estimate=-75.1, mock_mean_diff=-136.1)
    try:
        gate_analisi(an2)
    except F7Error:
        return ok
    return False


def _fase3_text(ladder_kind="list", break_point=None, drop_k1=False):
    L = []
    for c in CAPS:
        k0, k1 = EXPECT_FID[c]
        for g, p in [("fid", "FID")] + [("derived", q) for q in BLOCK_A] + [("regauged", "B1")]:
            a, b = (k0, k1) if not (g == "derived" and p == break_point) else (k0 + 1, k1)
            if g == "regauged":
                a, b = k0 - 50, k1 - 40
            lad = [{"N_H1": a}, {"N_H1": b}, {"N_H1": 1}, {"N_H1": 1}]
            if drop_k1:
                lad = lad[:1]
            if ladder_kind == "dict":
                lad = {str(i): e for i, e in enumerate(lad)}
            L.append(json.dumps({"region": c, "gauge": g, "point": p, "N_H1_k0": a, "ladder": lad}))
    return "\n".join(L) + "\n"


def _t_iso():
    for kind in ("list", "dict"):
        iso, seen = read_iso(_fase3_text(kind))
        g = gate_iso(iso, seen)
        if g["NGC"]["derived_equal"] != 6:
            return False
    iso, seen = read_iso(_fase3_text(break_point="A1m"))
    try:
        gate_iso(iso, seen)
    except F7Error:
        pass
    else:
        return False
    try:
        read_iso(_fase3_text(drop_k1=True))
    except F7Error as e:
        return "Chiavi del record" in str(e)
    return False


def _t_find():
    import tempfile
    d = tempfile.mkdtemp(prefix="st_f7_")
    try:
        find_compd(d)
    except F7Error:
        pass
    else:
        return False
    os.makedirs(J(d, "a"))
    for c in CAPS:
        open(J(d, "a", COMPD_NAME[c]), "w").write("x")
    try:
        find_compd(d)
    except F7Error as e:
        return "sha diverso" in str(e)
    return False


def _t_read_compd():
    rows = _rows_fixture()["NGC"]
    rec = {"region": "NGC", "n": 2000, "rows": [rows[p] for p in PARAMS], "w0_sigma1_implied": 3.0,
           "deficit_gen": 7180.686}
    t = json.dumps(rec) + "\n" + json.dumps(dict(rec, ensemble="v1")) + "\n"
    ok = read_compd(t, "NGC")["n_records"] == 2
    rec2 = dict(rec, ensemble="v1")
    rec2["rows"] = [dict(rows[p], r_raw=rows[p]["r_raw"] + (0.01 if p == "h" else 0)) for p in PARAMS]
    try:
        read_compd(t + json.dumps(rec2) + "\n", "NGC")
    except F7Error:
        return ok
    return False


def _t_pdf_deterministico():
    try:
        import matplotlib  # noqa: F401
    except Exception:
        return True
    import tempfile
    rows = _rows_fixture()
    nw = nwlh_rows({c: {"rows": rows[c]} for c in CAPS}, _fisher)
    an = read_analisi(_analisi_text())
    fap = fap_rows(an)
    d = tempfile.mkdtemp(prefix="st_f7_")
    a, b = J(d, "a.pdf"), J(d, "b.pdf")
    draw(nw, fap, a)
    draw(nw, fap, b)
    return open(a, "rb").read() == open(b, "rb").read()


TESTS = [
    ("C3: pendenze pulite passano; costante di NGC in SGC -> errore", _t_cross_cap),
    ("C4: firma SIGMA_TOT/|pendenza| riconosciuta; strumento corretto -> errore", _t_zsigma),
    ("R3 e C8: limiti |Delta|+3sigma; insieme diverso dal dichiarato -> errore", _t_bounded),
    ("C6: unione sulle passate, doppione diverso -> errore; valore fuori dal manoscritto -> errore", _t_analisi),
    ("C7: ladder lista o dizionario; derived diverso dal FID -> errore; campo assente -> chiavi stampate", _t_iso),
    ("C1: registro assente o con sha diverso -> errore", _t_find),
    ("compD: passate identiche lette per unione; righe diverse -> errore", _t_read_compd),
    ("PDF deterministico: due salvataggi, byte identici", _t_pdf_deterministico),
]


def selftest():
    ok = 0
    for nome, fn in TESTS:
        try:
            esito = bool(fn())
        except Exception as e:
            esito = False
            nome += " [%s: %s]" % (type(e).__name__, e)
        ok += esito
        if not esito:
            print("  FAIL  " + nome)
    print("selftest: %d/%d %s" % (ok, len(TESTS), "PASS" if ok == len(TESTS) else "FAIL"))
    return ok == len(TESTS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("comando", choices=["selftest", "run", "verify"])
    a = ap.parse_args()
    try:
        if a.comando == "selftest":
            return 0 if selftest() else 1
        if a.comando == "run":
            if not selftest():
                raise F7Error("selftest non superato")
            cmd_run()
            return 0
        return cmd_verify()
    except F7Error as e:
        print("ERRORE: %s" % e)
        print("ESITO: FALLITO")
        return 2


if __name__ == "__main__":
    sys.exit(main())

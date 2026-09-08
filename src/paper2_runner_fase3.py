#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 - Runner di Fase 3: cancello D3 e item 3.1 (lato dati).

PERCHE' UN RUNNER NUOVO, E PERCHE' NON RISCRIVE NIENTE
------------------------------------------------------
paper2_runner_fase2.py ha prodotto i quattordici record congelati di Fase 2:
modificarlo significherebbe che quei numeri non sono piu' riproducibili dal file
che li ha fatti. Ma nulla qui e' riscritto. Si IMPORTANO:
    da paper2_runner_fase2   unpack_positions, unpack_box, unpack_mask,
                             count_clipped, data_side_fields, append_jsonl
    da paper2_phase3_preflight  Cache, clipped_per_face, grid_shift, dominant_axis
    da paper2_item13a_15a       deform, LINE_A, LINE_B, CORNERS
Una sola implementazione per ogni quantita': due percorsi per lo stesso numero
sono la classe di difetto che produsse la discrepanza 445/313 nel Paper 1.

IL CANCELLO D3, PRIMA DI QUALUNQUE NUMERO NUOVO
------------------------------------------------
Questo runner, a geometria fiduciale e attraverso il PROPRIO percorso, deve
ridare 28256 / 15122 con differenza ZERO. E' il 2.1-D2 rifatto per il codice
nuovo. Senza, il confronto fra fiduciale e punti deformati misurerebbe la
differenza fra due implementazioni piu' la geometria.

IL GAUGE (emendamento 13, record 13 del file degli emendamenti)
----------------------------------------------------------------
    dc_pt = deform(z_tab, dc_fid, spec)     # NON make_dc_tab_ap: differisce di
                                            # un ULP (2.22e-16), e un cancello a
                                            # delta == 0 ESATTO non lo tollera
    set_geometry(z_tab, dc_tab=dc_pt)                      # passo 1
    derive_box(pos_r, pad=5.0)                    -> L_punto
    c = L_fid / L_punto                                    # passo 2
    set_geometry(z_tab, dc_tab=dc_pt * c)                  # passo 3
    derive_box(pos_r, pad=5.0*c)                  -> L = L_fid ESATTO
    R_SMOOTH = sigma_target * cell         # PRIMA di set_geometry(box)
    set_geometry(box_min=, box_size=)
    count_clipped(pos_r), count_clipped(pos_d)    -> [FATAL] se non zero
    mask = build_mask(field_r, "v1_fullcube")     # RIDERIVATA, mai np.load
    build_field(...) -> compute_tda_features(..., masked=True)

Il blocco A gira in DUE gauge: derivato con pad = 5*alpha (cancello 2.2b, la
Prop. 2 vale in forma esatta e la predizione e' delta == 0) e ri-gaugiato
(L = L_fid, resta il residuo della Prop. 2' misurato in 3.0a).

PREDIZIONI DICHIARATE PRIMA DELL'ESECUZIONE
--------------------------------------------
  D3    fiduciale, nessuna deformazione -> N_H1 == 28256 / 15122, delta == 0
        ESATTO; n_valid_voxels == 307805 / 172225; sigma_px a rel 0.00e+00;
        zero clippati; frazioni ritenute dell'erosione == 0.846/0.681/0.487
        (NGC) contro il reference `erosion_ladder_canonical`.
  A     blocco A, gauge derivato -> delta N_H1 == 0 ESATTO (Prop. 2, pad = 5*alpha)
  A'    blocco A, ri-gaugiato    -> |delta N_H1| compatibile con lo spostamento
        di 0.0090/0.0124 voxel misurato in 3.0a. NON e' zero e non si pretende
        che lo sia: e' l'artefatto del padding additivo, Prop. 2'.
  B, C  nessuna predizione di segno: e' la misura. Le soglie sono quelle
        dell'item 1.4 (rilevabilita' 53, rilevanza 390 NGC / 206 SGC).

REGOLA DI SIMMETRIA DELLA LINEA B, dichiarata qui prima del run
---------------------------------------------------------------
La linea B fu progettata su punti simmetrici in residuo minimax. Il pre-flight
ha misurato che nello SPOSTAMENTO REALE non lo sono: |du| vale 0.7494 (B1) e
0.7561 (B5) in NGC, 0.7565 e 0.7635 in SGC, cioe' B5 supera B1 dello 0.9%, con
lo stesso segno nei due emisferi. Un'asimmetria osservata sarebbe quindi
ambigua se non si dichiarasse PRIMA quanto ne e' dovuto alla costruzione.

  1. si stima la pendenza locale s_u = dN_H1/d|du| regredendo i QUATTRO punti di
     linea B su |du| misurato dal pre-flight;
  2. l'asimmetria ATTESA PER COSTRUZIONE e' A_pred = s_u * (|du|_B5 - |du|_B1);
  3. l'asimmetria osservata A_obs = N_H1(B5) - N_H1(B1) e' dichiarata FISICA
     solo se |A_obs - A_pred| > 53 generatori, cioe' la soglia di rilevabilita'
     3*sigma_Delta/sqrt(N) gia' pre-registrata.

Sotto quella soglia si riporta "compatibile con l'asimmetria strumentale", e non
"nessuna asimmetria": sono affermazioni diverse.

Uso:
    python src\\paper2_runner_fase3.py selftest
    python src\\paper2_runner_fase3.py d3  --region NGC
    python src\\paper2_runner_fase3.py run --region NGC
    python src\\paper2_runner_fase3.py run --region SGC --points B1 B5
    python src\\paper2_runner_fase3.py symmetry --region NGC
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

GAUGE_VERSION = "amend13"      # record 13: origine riderivata, pad = 5c
PAD_FID = 5.0
NGRID = 128
TOL_SIGMA_REL = 1e-12
TOL_L_REL = 1e-12
EROSIONS = (0, 1, 2, 3)
DETECT_THRESHOLD = 53          # 3*sigma_Delta/sqrt(N), item 1.4
LOG_DEFAULT = "results/paper2/fase3.jsonl"

# Ancora OPERATIVA: i due record `d2` di results/paper2/fase2.jsonl.
# Emendamento 13, punto (a). NON i congelati di phase6/phase9, che differiscono
# di 2.86e-9 relativo e, in NGC, portano un sigma_px scritto da un run a R=14.8.
ANCHOR = {
    "NGC": {"N_H1": 28256, "box_size": 1997.3629110094512,
            "cell": 15.604397742261337, "sigma_px": 0.32042249039652254,
            "n_valid_voxels": 307805, "N_rand": 13248857, "N_data": 217614},
    "SGC": {"N_H1": 15122, "box_size": 1904.450156441475,
            "cell": 14.878516847199023, "sigma_px": 0.33605500065144590,
            "n_valid_voxels": 172225, "N_rand": 5432939, "N_data": 82429},
}

# reference `erosion_ladder_canonical` (P1 §8.1, Tab. 9-10). Secondo cancello,
# indipendente da quello su N_H1: verifica il PERCORSO dell'erosione, non la TDA.
EROSION_FROZEN = {
    "NGC": {"retained": {1: 0.846, 2: 0.681, 3: 0.487},
            "wbar": {0: 0.998, 1: 0.99999}},
    "SGC": {"retained": {}, "wbar": {}},
}
EROSION_TOL = 0.002            # le frazioni del reference sono a 3 cifre

# Spostamenti misurati dal pre-flight 3.0a (results/paper2/preflight_*.jsonl).
# Servono alla regola di simmetria; il runner li RILEGGE dal registro e questi
# valgono solo da riferimento per il selftest e per un avviso di disallineamento.
PREFLIGHT_SHIFT_REF = {
    "NGC": {"B1": 0.7494, "B2": 0.3755, "B4": 0.3772, "B5": 0.7561},
    "SGC": {"B1": 0.7565, "B2": 0.3791, "B4": 0.3809, "B5": 0.7635},
}


def now():
    return datetime.now(timezone.utc).isoformat()


def config_hash(d):
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, default=float).encode()).hexdigest()[:16]


# --------------------------------------------------------------------------
# Aritmetica pura: testabile senza i moduli del progetto
# --------------------------------------------------------------------------

def erosion_levels(mask, levels=EROSIONS):
    """Erosione euclidea, come paper1_mask_erosion.py:78 — `edt(mask) > k`.
    A k = 1 coincide con l'erosione a sei vicini; diverge per k >= 2, quindi i
    livelli >= 2 NON sono confrontabili con una erosione a facce."""
    from scipy.ndimage import distance_transform_edt
    dist = distance_transform_edt(mask)
    out = {}
    for k in levels:
        out[k] = mask if k == 0 else (dist > k)
    return out, dist


def wbar(mask_full, m, sigma_px):
    """Frazione del peso del kernel proveniente da DENTRO la maschera piena.
    Identico a paper1_mask_erosion.py: gaussian_filter sulla maschera float."""
    from scipy.ndimage import gaussian_filter
    return float(gaussian_filter(mask_full.astype(np.float64),
                                 sigma=sigma_px)[m].mean())


def symmetry_verdict(shifts, counts, threshold=DETECT_THRESHOLD):
    """Regola dichiarata: un'asimmetria B1/B5 e' fisica solo se eccede di
    `threshold` quella predetta dalla pendenza locale.

    shifts, counts: dict {punto: valore} sui quattro punti di linea B.
    """
    pts = [p for p in ("B1", "B2", "B4", "B5") if p in shifts and p in counts]
    if len(pts) < 3:
        return {"ok": False, "reason": f"servono almeno 3 punti di linea B, ho {pts}"}
    u = np.array([shifts[p] for p in pts], float)
    n = np.array([counts[p] for p in pts], float)
    s_u = float(np.polyfit(u, n, 1)[0])
    if not ("B1" in counts and "B5" in counts):
        return {"ok": False, "reason": "servono B1 e B5"}
    du = float(shifts["B5"] - shifts["B1"])
    a_pred = s_u * du
    a_obs = float(counts["B5"] - counts["B1"])
    excess = a_obs - a_pred
    return {"ok": True, "points": pts, "slope_per_voxel": s_u,
            "du_B5_minus_B1": du, "A_pred": a_pred, "A_obs": a_obs,
            "excess": excess, "threshold": threshold,
            "physical": bool(abs(excess) > threshold),
            "verdict": ("asimmetria FISICA" if abs(excess) > threshold
                        else "compatibile con l'asimmetria strumentale")}


# --------------------------------------------------------------------------
# Aggancio
# --------------------------------------------------------------------------

def attach(srcdir="src"):
    if srcdir and srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    import phase8_cutsky_mocks as M
    import paper2_data_geometry as G
    import phase9_sgc_likeforlike as S
    import paper2_runner_fase2 as F2
    import paper2_phase3_preflight as PF
    import paper2_item13a_15a as I13
    z = np.asarray(M._Z_TAB, float).copy()
    dc = np.asarray(M._DC_TAB, float).copy()
    return M, G, S, F2, PF, I13, z, dc


def load_corners_aff(path):
    """I quattro surrogati affini, LETTI dal registro del fit (item 3.2e).

    Non si scrivono nel codice: due copie dello stesso numero divergono, e un
    numero senza provenienza e' il rilievo del §3.9. Il registro lo deposita
    paper2_surrogato_fit.py dopo i suoi tre cancelli.

    Ritorna [(nome, p), ...] in ordine di angolo. Se il file manca o e'
    malformato SOLLEVA: un piano di run che salta punti in silenzio e' peggio
    di un piano che non parte.
    """
    # Import LOCALI: il bersaglio non e' detto che abbia `os` o `json` in
    # testa -- e infatti `os` non c'era. Un caricatore che dipende dagli
    # import di chi lo ospita e' un caricatore che fallisce a run avviato.
    import json
    import os
    if not path or not os.path.isfile(path):
        raise SystemExit(
            "[FATAL] surrogati richiesti ma il registro non c'e': %r. Lancia "
            "prima src/paper2_surrogato_fit.py fit --out <registro>." % path)
    per_punto = {}
    with open(path, "rb") as fh:
        raw = fh.read()
    for i, ln in enumerate(raw.replace(b"\r\n", b"\n").split(b"\n"), start=1):
        if not ln.strip():
            continue
        try:
            r = json.loads(ln.decode("utf-8"))
        except Exception as exc:
            raise SystemExit("[FATAL] %s riga %d non e' JSON: %s" % (path, i, exc))
        if r.get("schema") != "paper2_surrogato_v1":
            continue
        for k in ("point_aff", "p"):
            if k not in r:
                raise SystemExit(
                    "[FATAL] %s riga %d: campo %r assente. Il registro non ha "
                    "la forma attesa e non indovino." % (path, i, k))
        nome, p = str(r["point_aff"]), float(r["p"])
        if nome in per_punto and per_punto[nome] != p:
            raise SystemExit(
                "[FATAL] %s: %s compare con due esponenti diversi, %r e %r. "
                "Non scelgo io quale." % (path, nome, per_punto[nome], p))
        per_punto[nome] = p
    if not per_punto:
        raise SystemExit("[FATAL] %s non contiene record paper2_surrogato_v1."
                         % path)
    return [(n, per_punto[n]) for n in sorted(per_punto)]


def point_plan(I13, points=None, aff_path=None):
    plan = [("FID", dict(kind="fid"), "fid")]
    plan += [(n, dict(kind="ap", alpha_iso=al, F_ap=1.0), "A") for n, al in I13.LINE_A]
    plan += [(n, dict(kind="ap", alpha_iso=1.0, F_ap=F), "B") for n, F in I13.LINE_B]
    plan += [(n, dict(kind="cosmo", omm=o, w0=w), "C") for n, o, w in I13.CORNERS]
    # Item 3.2e: i surrogati affini. Strutturalmente punti di linea B --
    # dict(kind="ap", alpha_iso=1.0, F_ap=p) -- perche' la famiglia e' la
    # stessa; il blocco "Caff" li distingue nel registro. La scala non la
    # portano: il ri-gauge sotto impone L = L_fid.
    if aff_path:
        plan += [(n, dict(kind="ap", alpha_iso=1.0, F_ap=p), "Caff")
                 for n, p in load_corners_aff(aff_path)]
    if points:
        noti = {p[0] for p in plan}
        ignoti = [q for q in points if q not in noti]
        if ignoti:
            # Un punto chiesto e non presente veniva SALTATO in silenzio:
            # il run girava su meno punti di quelli richiesti senza dirlo.
            raise SystemExit(
                "[FATAL] punti richiesti e non nel piano: %s. Se sono "
                "surrogati serve --surrogato con il registro del fit."
                % ignoti)
        plan = [p for p in plan if p[0] in points]
    return plan


def one_point(M, G, S, F2, PF, I13, region, root, cache_r, cache_d,
              z_tab, dc_fid, name, spec, block, L_fid, box_min_fid, pos_fid,
              gauge, sigma_target):
    """Un punto, un gauge. Nessun ramo silenzioso: ogni scelta e' esplicita."""
    t0 = time.time()
    rec = {"schema": "paper2_fase3_v1", "region": region, "point": name,
           "block": block, "gauge": gauge, "gauge_version": GAUGE_VERSION,
           "utc": now()}
    rec.update({k: v for k, v in spec.items() if k != "kind"})

    dc_pt = I13.deform(z_tab, dc_fid, spec)

    if gauge == "regauged":
        M.set_geometry(z_tab=z_tab, dc_tab=dc_pt, verbose=False)
        pos_r, _ = cache_r.positions()
        _, L_nat = F2.unpack_box(G.derive_box(pos_r, pad=PAD_FID))
        c = L_fid / L_nat
        M.set_geometry(z_tab=z_tab, dc_tab=dc_pt * c, verbose=False)
        pad = PAD_FID * c
        rec.update(c=c, L_natural=L_nat, dL_vs_fid=L_nat - L_fid)
    elif gauge == "derived":
        # Blocco A soltanto: pad = 5*alpha, la Prop. 2 vale in forma esatta.
        M.set_geometry(z_tab=z_tab, dc_tab=dc_pt, verbose=False)
        pad = PAD_FID * float(spec.get("alpha_iso", 1.0))
        rec.update(c=1.0, pad_mode="scaled")
    elif gauge == "fid":
        M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
        pad = PAD_FID
    else:
        sys.exit(f"[FATAL] gauge '{gauge}' sconosciuto.")

    pos_r, w_r = cache_r.positions()
    box_min, box_size = F2.unpack_box(G.derive_box(pos_r, pad=pad))
    cell = box_size / M.NGRID
    rec.update(pad=pad, box_size=box_size, cell=cell,
               box_min=[float(v) for v in box_min])
    if gauge == "regauged":
        rel = abs(box_size - L_fid) / L_fid
        rec["L_rel_err_vs_fid"] = rel
        if rel > TOL_L_REL:
            sys.exit(f"[FATAL] ri-gauge fallito su {name}: L = {box_size!r}, "
                     f"atteso {L_fid!r} (rel {rel:.2e}).")

    # R_SMOOTH PRIMA di set_geometry: SIGMA_PX = R_SMOOTH/CELL e' ricalcolato
    # sempre (phase8:319-321) e asserito a 1e-15. La convenzione e' "sigma_px
    # bloccato", non "R bloccato".
    M.R_SMOOTH = sigma_target * cell
    M.set_geometry(box_min=box_min, box_size=box_size, verbose=False)
    sigma = float(M.SIGMA_PX)
    e = abs(sigma - sigma_target) / sigma_target
    rec.update(R_SMOOTH=float(M.R_SMOOTH), sigma_px=sigma, sigma_locked_rel=e)
    if e > TOL_SIGMA_REL:
        sys.exit(f"[FATAL] blocco di sigma_px fallito su {name}: "
                 f"{sigma!r} contro {sigma_target!r} (rel {e:.2e}).")

    # Clippati: cancello a ZERO, emendamento 13 punto (c).
    cl_r = PF.clipped_per_face(pos_r, box_min, box_size)
    rec["clipped_rand"] = cl_r
    if cl_r["n_clipped"]:
        sys.exit(f"[FATAL] {cl_r['n_clipped']} random fuori dal cubo su {name}. "
                 "cic_3d li impilerebbe sulle facce: il punto non si misura.")

    field_r = M.cic_3d(pos_r, w_r, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    # §3.2 / record 24. In passata 2 la maschera si CARICA. La regola esplicita
    # 0.01*field_r.mean() qui non si applica: l'intersezione non e' la maschera
    # di questo punto, e' quella comune a tutti. Il controllo che resta e' D6.
    _mfix = getattr(one_point, "_mask_fixed", None)
    sum_wr = float(w_r.sum())

    # Maschera RIDERIVATA, mai np.load (cancello 2.1-M).
    mask, thr_reported = F2.unpack_mask(G.build_mask(field_r, "v1_fullcube"))
    thr = 0.01 * float(field_r.mean())
    if not np.array_equal(mask, field_r > thr):
        sys.exit("[FATAL] build_mask('v1_fullcube') non coincide con la regola "
                 "esplicita 0.01*field_r.mean(). Il 2.1-M vale per la seconda.")
    rec.update(mask_threshold=thr, mask_threshold_reported=thr_reported)
    # Passata 1: si accumula l'AND. La maschera del punto e' quella derivata,
    # quindi la passata 1 e' identica al comportamento di sempre a parte
    # l'accumulo, che non tocca nulla.
    _acc = getattr(one_point, "_mask_acc", None)
    if _acc is not None:
        one_point._mask_acc = mask.copy() if _acc is True else (_acc & mask)
        rec["mask_pass"] = "derive"
    # Passata 2: si sostituisce, e da qui in poi `mask` E' l'intersezione.
    if _mfix is not None:
        if _mfix.shape != mask.shape:
            sys.exit(f"[FATAL] maschera fissa di forma {_mfix.shape} contro "
                     f"{mask.shape} attesa: non e' l'intersezione di questa "
                     f"geometria.")
        if not np.all(mask[_mfix]):
            sys.exit("[FATAL] la maschera fissa NON e' contenuta in quella di "
                     "questo punto: non e' un'intersezione dei dodici punti.")
        mask = _mfix
        rec["mask_pass"] = "fixed"
    rec.update(n_valid_voxels=int(mask.sum()))
    # CANCELLO D6, tolleranza zero (record 24). In passata 2 il conteggio e'
    # costante PER COSTRUZIONE: se varia, la modalita' non fa quel che dice.
    if _mfix is not None:
        _n = int(mask.sum())
        _first = getattr(one_point, "_d6_n", None)
        if _first is None:
            one_point._d6_n = _n
        elif _n != _first:
            sys.exit(f"[FATAL] D6: n_valid_voxels = {_n} contro {_first} del "
                     f"primo punto. Con maschera fissa e' costante per "
                     f"costruzione. Tolleranza zero, record 24.")

    if cache_d is not None:
        pos_d, _ = cache_d.positions()
        cl_d = PF.clipped_per_face(pos_d, box_min, box_size)
        rec["clipped_data"] = cl_d
        if cl_d["n_clipped"]:
            sys.exit(f"[FATAL] {cl_d['n_clipped']} galassie fuori dal cubo su {name}.")
        rec["grid_shift_vs_fid"] = PF.grid_shift(
            pos_d, box_min, cell, pos_fid, box_min_fid, L_fid / M.NGRID)
        del pos_d
    rec["dominant"] = PF.dominant_axis(pos_r)
    del pos_r

    field_d, sum_wd = F2.data_side_fields(M, S, region, root)
    alpha_fkp = sum_wd / sum_wr
    rec.update(sum_wr=sum_wr, sum_wd=sum_wd, alpha_fkp=alpha_fkp)

    # --- campo, TDA, scala di erosione in modo RESTRICT ----------------------
    # nu si costruisce con la maschera PIENA (lo smoothing usa tutta
    # l'informazione), la filtrazione si restringe alla erosa: cosi' si
    # escludono dalla topologia i voxel contaminati dal bordo senza degradare il
    # campo altrove. E' il modo primario di paper1_mask_erosion.py.
    nu = M.build_field(field_d, field_r, alpha_fkp, mask)
    masks, dist = erosion_levels(mask, EROSIONS)
    lad = {}
    for k in EROSIONS:
        m = masks[k]
        feats = M.compute_tda_features(nu, m, M.N_THRESH, masked=True)
        lad[str(k)] = {"N_H1": int(round(float(feats[4]))),
                       "b1_peak": float(feats[1]),
                       "n_voxels": int(m.sum()),
                       "retained": float(m.sum() / mask.sum()),
                       "wbar": wbar(mask, m, sigma)}
    rec["ladder"] = lad
    rec["N_H1"] = lad["1"]["N_H1"]          # livello PRIMARIO: k = 1 (item 1.2b)
    rec["N_H1_k0"] = lad["0"]["N_H1"]       # riportato in parallelo per v1
    rec["d_med_voxel"] = float(np.median(dist[mask]))
    rec["occupancy_gal_per_voxel"] = ANCHOR[region]["N_data"] / int(mask.sum())
    rec["seconds"] = time.time() - t0
    rec["config_hash"] = config_hash(
        {"gauge": gauge, "gauge_version": GAUGE_VERSION, "point": name,
         "region": region, "spec": spec, "erosions": list(EROSIONS),
         "sigma_target": sigma_target, "pad_fid": PAD_FID})
    return rec


# --------------------------------------------------------------------------
# Comandi
# --------------------------------------------------------------------------

def _setup(a):
    M, G, S, F2, PF, I13, z_tab, dc_fid = attach(a.src)
    root = Path(a.project_root).resolve()
    reg = a.region
    M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
    cache_r = PF.Cache(G, M, reg, "ran")
    cache_d = PF.Cache(G, M, reg, "dat")
    if cache_r.n != ANCHOR[reg]["N_rand"]:
        sys.exit(f"[FATAL] N_rand = {cache_r.n}, atteso {ANCHOR[reg]['N_rand']}.")
    if not a.no_cache_gate:
        g = PF.cache_gate(G, cache_r)
        if not g["ok"]:
            sys.exit("[FATAL] la cache non e' bit-identica a G.positions().")
    pos_fid, _ = cache_d.positions()
    pos_r_fid, _ = cache_r.positions()
    box_min_fid, L_fid = F2.unpack_box(G.derive_box(pos_r_fid, pad=PAD_FID))
    del pos_r_fid
    anc = ANCHOR[reg]
    if abs(L_fid - anc["box_size"]) / anc["box_size"] > TOL_L_REL:
        sys.exit(f"[FATAL] L fiduciale {L_fid!r} != ancora {anc['box_size']!r}.")
    return (M, G, S, F2, PF, I13, z_tab, dc_fid, root, reg,
            cache_r, cache_d, pos_fid, box_min_fid, L_fid)


def cmd_d3(a):
    ctx = _setup(a)
    (M, G, S, F2, PF, I13, z_tab, dc_fid, root, reg,
     cache_r, cache_d, pos_fid, box_min_fid, L_fid) = ctx
    anc = ANCHOR[reg]
    print("=" * 72)
    print(f"D3 — chiusura del runner di Fase 3 a geometria fiduciale, {reg}")
    print("=" * 72)
    print("  PREDIZIONE: N_H1 == %d, delta == 0 ESATTO; voxel == %d; sigma rel 0"
          % (anc["N_H1"], anc["n_valid_voxels"]))
    rec = one_point(M, G, S, F2, PF, I13, reg, root, cache_r, cache_d,
                    z_tab, dc_fid, "FID", dict(kind="fid"), "fid",
                    L_fid, box_min_fid, pos_fid, "fid", anc["sigma_px"])
    rec["gate"] = "d3"
    fails = []
    if rec["N_H1_k0"] != anc["N_H1"]:
        fails.append(f"N_H1(k=0) = {rec['N_H1_k0']}, atteso {anc['N_H1']}")
    if rec["n_valid_voxels"] != anc["n_valid_voxels"]:
        fails.append(f"voxel = {rec['n_valid_voxels']}, attesi {anc['n_valid_voxels']}")
    if rec["sigma_locked_rel"] != 0.0:
        fails.append(f"sigma_px rel = {rec['sigma_locked_rel']:.2e}, atteso 0")
    for k, exp in EROSION_FROZEN[reg]["retained"].items():
        got = rec["ladder"][str(k)]["retained"]
        if abs(got - exp) > EROSION_TOL:
            fails.append(f"ritenuta k={k}: {got:.4f}, attesa {exp}")
    for k, exp in EROSION_FROZEN[reg]["wbar"].items():
        got = rec["ladder"][str(k)]["wbar"]
        if abs(got - exp) > 5e-4:
            fails.append(f"wbar k={k}: {got:.5f}, atteso {exp}")
    rec["pass"] = not fails
    rec["fails"] = fails
    print(f"\n  N_H1(k=0) = {rec['N_H1_k0']}   N_H1(k=1) = {rec['N_H1']}")
    print(f"  voxel = {rec['n_valid_voxels']}   d_med = {rec['d_med_voxel']:.3f} voxel")
    for k in EROSIONS:
        L = rec["ladder"][str(k)]
        print(f"    k={k}: N_H1={L['N_H1']:8d}  voxel={L['n_voxels']:8d}  "
              f"ritenuta={L['retained']:.4f}  wbar={L['wbar']:.5f}")
    if a.out:
        F2.append_jsonl(a.out, rec)
    print(f"\n  {'D3 SUPERATO' if not fails else 'FALLITO: ' + '; '.join(fails)}")
    return 0 if not fails else 1


def _setup_maschera(a):
    """§3.2, record 24. Prepara la passata 1 o la 2 e stampa cosa aspettarsi."""
    if getattr(a, "mask_intersect_out", None) and getattr(a, "mask_fixed", None):
        sys.exit("[FATAL] --mask-intersect-out e --mask-fixed sono le due "
                 "passate dello stesso test e non si usano insieme.")
    one_point._mask_acc = True if getattr(a, "mask_intersect_out", None) else None
    one_point._mask_fixed = None
    one_point._d6_n = None
    if getattr(a, "mask_fixed", None):
        one_point._mask_fixed = np.load(a.mask_fixed)
        print("=" * 74)
        print("  §3.2 PASSATA 2 — maschera FISSA da %s" % a.mask_fixed)
        print("  voxel dell'intersezione: %d" % int(one_point._mask_fixed.sum()))
        print("  DICHIARATO PRIMA DEL RUN (record 24): l'intersezione e' piu'")
        print("  piccola di ogni singola maschera, quindi N_H1 SCENDE a ogni")
        print("  punto e il fiduciale NON riprodurra' 28256 / 15122. Non e' un")
        print("  difetto. Il cancello di riproduzione non si applica: c'e' D6.")
        print("  E' un DIAGNOSTICO del residuo, non una ri-misura di D.")
        print("=" * 74)
    elif getattr(a, "mask_intersect_out", None):
        print("=" * 74)
        print("  §3.2 PASSATA 1 — accumulo dell'AND, uscita in %s"
              % a.mask_intersect_out)
        print("  Nessun risultato si riporta da questa passata.")
        print("=" * 74)


def _scrivi_intersezione(a):
    acc = getattr(one_point, "_mask_acc", None)
    if getattr(a, "mask_intersect_out", None) and acc is not None and acc is not True:
        np.save(a.mask_intersect_out, acc)
        print("\n  [§3.2] intersezione scritta in %s: %d voxel"
              % (a.mask_intersect_out, int(acc.sum())))


def cmd_run(a):
    _setup_maschera(a)
    ctx = _setup(a)
    (M, G, S, F2, PF, I13, z_tab, dc_fid, root, reg,
     cache_r, cache_d, pos_fid, box_min_fid, L_fid) = ctx
    anc = ANCHOR[reg]
    done = set()
    if a.out and Path(a.out).exists():
        for ln in Path(a.out).read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    r = json.loads(ln)
                    done.add((r.get("point"), r.get("gauge"), r.get("config_hash")))
                except Exception:
                    pass
    print("=" * 72)
    print(f"3.1 — lato dati, {reg}, gauge {GAUGE_VERSION}")
    print("=" * 72)
    rows = []
    try:
        for name, spec, block in point_plan(
                I13, a.points, getattr(a, "surrogato", None)):
            if name == "FID":
                continue
            gauges = ["regauged"] + (["derived"] if block == "A" else [])
            for gauge in gauges:
                rec = one_point(M, G, S, F2, PF, I13, reg, root, cache_r, cache_d,
                                z_tab, dc_fid, name, spec, block, L_fid,
                                box_min_fid, pos_fid, gauge, anc["sigma_px"])
                key = (name, gauge, rec["config_hash"])
                if key in done:
                    print(f"  {name:<4} [{gauge}] gia' fatto, salto")
                    continue
                rec["delta_vs_fid"] = rec["N_H1"] - anc["N_H1"]
                rows.append(rec)
                if a.out:
                    F2.append_jsonl(a.out, rec)
                sh = rec.get("grid_shift_vs_fid", {}).get("max", float("nan"))
                print(f"  {name:<4} [{block}/{gauge:<9}] L={rec['box_size']:12.6f}  "
                      f"voxel={rec['n_valid_voxels']:7d}  "
                      f"N_H1(k1)={rec['N_H1']:7d}  k0={rec['N_H1_k0']:7d}  "
                      f"du={sh:.4f}  [{rec['seconds']:.0f}s]")
    finally:
        M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
        print("\n[restore] geometria fiduciale ripristinata.")
        _scrivi_intersezione(a)
    return 0


def cmd_symmetry(a):
    """Applica la regola dichiarata ai record gia' su disco. Nessun run."""
    path = Path(a.out or LOG_DEFAULT)
    if not path.exists():
        sys.exit(f"[FATAL] registro assente: {path}")
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]
    rows = [r for r in rows if r.get("region") == a.region
            and r.get("gauge") == "regauged" and r.get("block") == "B"]
    counts = {r["point"]: r["N_H1"] for r in rows}
    shifts = {r["point"]: r["grid_shift_vs_fid"]["max"] for r in rows
              if "grid_shift_vs_fid" in r}
    ref = PREFLIGHT_SHIFT_REF[a.region]
    for p, v in shifts.items():
        if p in ref and abs(v - ref[p]) > 0.005:
            print(f"  [avviso] spostamento {p} = {v:.4f}, il pre-flight diede "
                  f"{ref[p]:.4f}: i due registri non concordano.")
    v = symmetry_verdict(shifts, counts)
    print(json.dumps(v, indent=2, ensure_ascii=False))
    return 0


def cmd_selftest(a):
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    m = np.zeros((32, 32, 32), bool)
    m[8:24, 8:24, 8:24] = True
    masks, dist = erosion_levels(m, (0, 1, 2, 3))
    expect("1. erosione k=0 e' la maschera piena",
           np.array_equal(masks[0], m))
    expect("2. le erosioni sono annidate e strettamente decrescenti",
           all(masks[k + 1].sum() < masks[k].sum() for k in (0, 1, 2))
           and all((masks[k + 1] & ~masks[k]).sum() == 0 for k in (0, 1, 2)))
    expect("3. a k=1 l'erosione euclidea toglie esattamente lo strato di faccia",
           int(masks[1].sum()) == 14 ** 3, f"({int(masks[1].sum())} contro {14**3})")
    # I voxel con profondita' >= d sono (18-2d)^3: 4096 a d=1, 2744 a d=2,
    # 1728 a d=3. La mediana su 4096 cade quindi a 2, non al semilato — il
    # footprint e' tutto bordo molto prima di quanto suggerisca la geometria.
    # (Reale: NGC 3.000 voxel, SGC 2.828 = 2*sqrt(2).)
    expect("4. d_med su un cubo 16^3 vale 2 voxel, non il semilato",
           abs(float(np.median(dist[m])) - 2.0) < 1e-9,
           f"({float(np.median(dist[m])):.3f})")

    w0 = wbar(m, masks[0], 0.32)
    w1 = wbar(m, masks[1], 0.32)
    expect("5. wbar cresce con l'erosione e resta in (0,1]",
           0 < w0 < w1 <= 1.0, f"(k0 {w0:.5f}, k1 {w1:.5f})")

    # regola di simmetria: costruisco un caso in cui l'asimmetria e' TUTTA
    # strumentale, e uno in cui eccede la soglia.
    sh = {"B1": 0.7494, "B2": 0.3755, "B4": 0.3772, "B5": 0.7561}
    s_u = 300.0
    base = {p: 28000 + s_u * sh[p] for p in sh}
    v = symmetry_verdict(sh, base)
    expect("6. asimmetria puramente strumentale -> non fisica",
           v["ok"] and not v["physical"] and abs(v["excess"]) < 1e-6,
           f"(eccesso {v['excess']:.3e})")
    expect("7. e la pendenza stimata e' quella iniettata",
           abs(v["slope_per_voxel"] - s_u) < 1e-6)

    hard = dict(base); hard["B5"] += 200.0
    v2 = symmetry_verdict(sh, hard)
    expect("8. asimmetria di 200 generatori -> fisica (soglia 53)",
           v2["physical"] and 150 < v2["excess"] < 210,
           f"(eccesso {v2['excess']:.1f})")

    soft = dict(base); soft["B5"] += 40.0
    v3 = symmetry_verdict(sh, soft)
    expect("9. asimmetria di 40 generatori -> sotto soglia, NON 'nessuna'",
           not v3["physical"] and "strumentale" in v3["verdict"])

    v4 = symmetry_verdict({"B1": 1.0}, {"B1": 1})
    expect("10. con meno di tre punti la regola si rifiuta di decidere",
           not v4["ok"])

    h1 = config_hash({"a": 1, "b": [2, 3]})
    h2 = config_hash({"b": [2, 3], "a": 1})
    expect("11. l'hash di configurazione non dipende dall'ordine delle chiavi",
           h1 == h2)
    expect("12. ma cambia se cambia il gauge",
           config_hash({"g": "amend13"}) != config_hash({"g": "forced"}))

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", default="src")
    p.add_argument("--project_root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for nm in ("d3", "run", "symmetry"):
        q = sub.add_parser(nm)
        q.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
        q.add_argument("--out", default=LOG_DEFAULT)
        q.add_argument("--no-cache-gate", action="store_true")
        if nm == "run":
            q.add_argument("--points", nargs="*", default=None)
            q.add_argument("--surrogato", default=None, metavar="FILE",
                           help="item 3.2e: registro del fit dei "
                                "surrogati affini. Aggiunge C1aff..C4aff "
                                "al piano, con F_ap letto da li'. Usare "
                                "un --out SEPARATO: sono punti di griglia "
                                "nuovi, non una continuazione")
            q.add_argument("--mask-intersect-out", default=None, metavar="FILE",
                           help="§3.2 passata 1: accumula l'AND delle maschere "
                                "dei punti e lo scrive in FILE.")
            q.add_argument("--mask-fixed", default=None, metavar="FILE",
                           help="§3.2 passata 2: CARICA la maschera invece di "
                                "derivarla. n_valid_voxels diventa costante per "
                                "costruzione e il termine (e) non esiste. "
                                "Usare un --out SEPARATO: e' un diagnostico, "
                                "non una ri-misura.")
    a = p.parse_args()
    return {"selftest": cmd_selftest, "d3": cmd_d3,
            "run": cmd_run, "symmetry": cmd_symmetry}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

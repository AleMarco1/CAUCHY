#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 - Runner di Fase 2: cancelli 2.1-D2, 2.2a, 2.2b, 2.3.

PERCHE' UN RUNNER NUOVO
-----------------------
paper1_remap.py non puo' eseguire questi cancelli: il parser non ha leve di
geometria, e sigma_px viene fissato subito dopo setup_region, cioe' nel punto
esatto in cui andrebbe iniettato il box. Ma se il baseline lo produce un codice e
il punto dilatato un altro, il |dN_H1| <= 5 del 2.2a misura la differenza fra i
due codici piu' la geometria. Da qui il 2.1-D2: questo runner, a geometria
fiduciale, deve ridare 28256 / 15122 con differenza ZERO prima che il 2.2 sia
interpretabile.

PREDIZIONI DICHIARATE PRIMA DELL'ESECUZIONE (checklist rev. 3.4, Fase 2)
------------------------------------------------------------------------
  2.1-D2  fiduciale, nessuna deformazione   -> N_H1 == 28256 / 15122, delta == 0
  2.2b    alpha=1.05, pad = 5.0*alpha       -> delta N_H1 == 0 ESATTAMENTE
  2.2a    alpha=1.05, pad = 5.0 additivo    -> |delta N_H1| <= 5 generatori
  2.3     stessa dilatazione, R_SMOOTH = 5  -> delta N_H1 > 0
          (meno smoothing: sigma_px scende da 0.320422 a 0.305164, peso centrale
           del kernel 95.54% -> 97.26%, campo shot-noise dominato)

Il 2.2b passera' comunque e passando NON dira' nulla sul problema della Fase 3:
con pos -> alpha*pos, box_min -> alpha*box_min, cell -> alpha*cell, il rapporto
(pos - box_min)/cell e' invariante bit a bit, gli indici non si muovono e una
maschera in spazio di indici resta corretta per caso. Va scritto nel verbale,
altrimenti l'esito viene letto come una rassicurazione che non e'.

SEQUENZA (checklist 3.0 rev. 3.4)
---------------------------------
  R_SMOOTH  assegnato PRIMA di set_geometry: SIGMA_PX = R_SMOOTH/CELL e'
            ricalcolato sempre (phase8:319-321) e asserito a 1e-15 (riga 325),
            quindi sigma_px non e' sovrascrivibile e si pilota da R_SMOOTH.
  set_geometry(z_tab, dc_tab)   comoving_distance e' fra le globali riassegnate
  positions(region, "ran")      kind="ran": ogni altro token restituisce i DATI
  derive_box(pos_r, pad)        pad = 5.0 (additivo) oppure 5.0*alpha (scalato)
  set_geometry(box_min, box_size)
  mask = build_mask(field_r, "v1_fullcube")   RIDERIVATA, mai np.load (2.1-M)
  build_field(field_d, field_r, alpha_fkp, mask)     usa la globale SIGMA_PX
  compute_tda_features(nu, mask, N_THRESH, masked=True)   NON e' il default

Lato dati: NGC via M.load_desi_data_field(), SGC via S.sgc_positions() + cic_3d,
come fa setup_region. Cosi' il token "dat" di positions() non serve e la trappola
0.8 non puo' mordere.

Uso:
    python src\\paper2_runner_fase2.py d2   --region NGC
    python src\\paper2_runner_fase2.py g22b --region NGC
    python src\\paper2_runner_fase2.py g22a --region NGC
    python src\\paper2_runner_fase2.py g23  --region NGC
Un cancello e una regione per invocazione: la geometria e' stato globale e viene
ripristinata in finally, ma il processo deve morire subito dopo comunque.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

FROZEN = {
    "NGC": {"N_H1": 28256, "box_size": 1997.3629167166155,
            "cell": 15.604397786848558, "sigma_px": 0.32042249039652254,
            "n_valid_voxels": 307805, "N_rand": 13248857, "N_data": 217614,
            "mask_threshold": 0.020012933760881424,
            "mask_file": "bgs_ngc_mask_128.npy"},
    "SGC": {"N_H1": 15122, "box_size": 1904.4501607158168,
            "cell": 14.878516880592318, "sigma_px": 0.3360550006514459,
            "n_valid_voxels": 172225, "N_rand": 5432939, "N_data": 82429,
            "mask_threshold": 0.008570596575737,
            "mask_file": "bgs_sgc_mask_128.npy"},
}

GATES = {
    #  nome      alpha   pad_mode     sigma_mode   predizione
    "d2":   dict(alpha=1.00, pad="additive", sigma="frozen",
                 pred="N_H1 == congelato, delta == 0 ESATTO"),
    "g22b": dict(alpha=1.05, pad="scaled",   sigma="frozen",
                 pred="delta N_H1 == 0 ESATTAMENTE"),
    "g22a": dict(alpha=1.05, pad="additive", sigma="frozen",
                 pred="|delta N_H1| <= 5 generatori"),
    "g23":  dict(alpha=1.05, pad="additive", sigma="canonical",
                 pred="delta N_H1 > 0"),
    "padladder": dict(alpha=1.00, pad="additive", sigma="frozen",
                 pred="dispersione <= 0.25 sigma dell'ensemble su tutta la scala"),
    "maskladder": dict(alpha=1.00, pad="additive", sigma="frozen",
                 pred="pendenza dN_H1/dV compatibile entro 2 sigma con quella del padladder"),
}

# Pendenze misurate dal padladder (27 ago 2026), regressione N_H1 su n_valid_voxels,
# con il PROPRIO errore standard: res_sd / sqrt(Sxx). La pendenza di riferimento e'
# nota solo al 10-11%, quindi un confronto "entro il 20%" sarebbe piu' largo
# dell'incertezza della cosa con cui si confronta e non deciderebbe nulla.
PADLADDER_SLOPE = {"NGC": (0.0897, 0.0100), "SGC": (0.1137, 0.0113)}
SLOPE_NSIGMA = 2.0
# Serve un'escursione di ~2% della maschera per portare l'errore della pendenza
# al 6%: da 0.007-0.014 (~1%) non basta. Scala log-spaziata su un fattore 5.
SCALES_DEFAULT = [0.005, 0.0065, 0.008, 0.010, 0.0125, 0.016, 0.020, 0.025]

# Pavimento di ricampionamento: sigma dell'ensemble v1, per la soglia del padladder.
SIGMA_ENSEMBLE = {"NGC": 312.9891651683112, "SGC": 197.7873817207103}
LADDER_FRAC = 0.25
PADS_DEFAULT = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0]

PAD_FID = 5.0
TOL_GEOM_REL = 1e-6
TOL_SIGMA_REL = 1e-12
LOG = "results/paper2/fase2.jsonl"


def now():
    return datetime.now(timezone.utc).isoformat()


def ok_str(b):
    return "PASSA" if b else "FALLITO"


def append_jsonl(path, rec):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True, default=float) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def unpack_positions(out, region):
    """positions() puo' restituire pos, (pos, w) o un dict. I pesi FKP sono
    obbligatori: field_r pesato e' cio' che definisce la maschera, e sostituirli
    con degli uni cambierebbe la soglia in silenzio."""
    pos = w = None
    if isinstance(out, np.ndarray):
        pos = out
    elif isinstance(out, dict):
        for k in ("pos", "positions", "xyz"):
            if k in out:
                pos = np.asarray(out[k])
                break
        for k in ("w", "weights", "wfkp", "weight"):
            if k in out:
                w = np.asarray(out[k], dtype=np.float64)
                break
    elif isinstance(out, (tuple, list)):
        if len(out) >= 1:
            pos = np.asarray(out[0])
        if len(out) >= 2 and out[1] is not None:
            w = np.asarray(out[1], dtype=np.float64)
    if pos is None or pos.ndim != 2 or pos.shape[1] != 3:
        sys.exit("[FATAL] positions(%r,'ran') ha restituito un oggetto che non so "
                 "interpretare come (N,3). Tipo: %r" % (region, type(out)))
    if w is None:
        sys.exit("[FATAL] positions(%r,'ran') non restituisce i pesi FKP.\n"
                 "        Non li sostituisco con degli uni: cambierebbero la soglia\n"
                 "        della maschera in silenzio. Serve il corpo di positions()."
                 % region)
    return pos, w


def unpack_box(out):
    """derive_box() puo' restituire (box_min, box_size), un dict o un oggetto."""
    if isinstance(out, dict):
        for a in ("box_min", "bmin"):
            if a in out:
                bmin = np.asarray(out[a], dtype=np.float64)
                break
        else:
            bmin = None
        for a in ("box_size", "bsize", "L"):
            if a in out:
                bsize = float(out[a])
                break
        else:
            bsize = None
    elif isinstance(out, (tuple, list)) and len(out) >= 2:
        bmin, bsize = np.asarray(out[0], dtype=np.float64), float(out[1])
    else:
        bmin = getattr(out, "box_min", None)
        bsize = getattr(out, "box_size", None)
        bmin = None if bmin is None else np.asarray(bmin, dtype=np.float64)
        bsize = None if bsize is None else float(bsize)
    if bmin is None or bsize is None or bmin.shape != (3,):
        sys.exit("[FATAL] derive_box() ha restituito %r, non (box_min, box_size)." % type(out))
    return bmin, bsize


def unpack_mask(out):
    """build_mask() restituisce una tupla, non l'array: cerco l'unico elemento
    3-D booleano e, se c'e', mi tengo anche la soglia per il confronto."""
    cand, extra = None, []
    items = out if isinstance(out, (tuple, list)) else (
        list(out.values()) if isinstance(out, dict) else [out])
    for x in items:
        a = np.asarray(x) if not np.isscalar(x) else None
        if a is not None and a.ndim == 3:
            if cand is not None:
                sys.exit("[FATAL] build_mask() ha restituito due array 3-D: non so quale.")
            cand = a
        else:
            extra.append(x)
    if cand is None:
        sys.exit("[FATAL] build_mask() non contiene nessun array 3-D. Ha restituito %r." % (out,))
    thr = None
    for x in extra:
        try:
            v = float(x)
        except (TypeError, ValueError):
            continue
        if np.isfinite(v):
            thr = v
            break
    return cand.astype(bool), thr


def data_side_fields(M, S, region, root):
    """Lato dati DOPO che il box e' impostato. Evita il token 'dat' di positions()."""
    if region == "NGC":
        return M.load_desi_data_field()          # (field_d, sum_wd)
    desi_dir = root / "data" / "raw" / "desi_dr1"
    dat = desi_dir / "BGS_BRIGHT-21.5_SGC_clustering.dat.fits"
    if not dat.exists():
        sys.exit("[FATAL] dati SGC assenti: %s" % dat)
    pos_d, w_d = S.sgc_positions(dat, wkeys=("WEIGHT", "WEIGHT_FKP"), M=M)
    field_d = M.cic_3d(pos_d, w_d, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    return field_d, float(w_d.sum())


def count_clipped(pos, box_min, box_size):
    """cic_3d ritaglia in silenzio (phase8:495-508): le posizioni fuori dal cubo
    non vengono scartate, vengono impilate sulle facce."""
    lo = pos < box_min[None, :]
    hi = pos >= (box_min + box_size)[None, :]
    return int(np.any(lo | hi, axis=1).sum())


def run(M, G, S, region, root, alpha, pad_mode, sigma_mode, mask_mode, z_fid, dc_fid,
        pad_override=None, cache=None, mask_scale=None):
    f = FROZEN[region]
    rec = {"region": region, "alpha_iso": alpha, "pad_mode": pad_mode,
           "sigma_mode": sigma_mode, "mask_mode": mask_mode}

    # --- deformazione: dilatazione isotropa pura su D_C ----------------------
    dc_new = dc_fid if alpha == 1.0 else alpha * dc_fid
    M.set_geometry(z_tab=z_fid, dc_tab=dc_new, verbose=True)

    # --- random nella nuova mappatura ---------------------------------------
    t0 = time.time()
    # La cache dei random e' lecita SOLO a mappatura invariata: se la dc_tab
    # cambia, le posizioni cambiano e riusarle sarebbe un errore silenzioso.
    if cache is not None and alpha == 1.0 and "pos_r" in cache:
        pos_r, w_r = cache["pos_r"], cache["w_r"]
    else:
        pos_r, w_r = unpack_positions(G.positions(region, "ran"), region)
        if cache is not None and alpha == 1.0:
            cache["pos_r"], cache["w_r"] = pos_r, w_r
    n_rand = int(len(pos_r))
    rec["N_rand"] = n_rand
    rec["N_rand_ok"] = (n_rand == f["N_rand"])
    if not rec["N_rand_ok"]:
        sys.exit("[FATAL] N_rand = %d, atteso %d: positions() non ha dato i random."
                 % (n_rand, f["N_rand"]))

    if pad_override is not None:
        pad = float(pad_override)
    else:
        pad = PAD_FID * alpha if pad_mode == "scaled" else PAD_FID
    box_min, box_size = unpack_box(G.derive_box(pos_r, pad=pad))
    cell = box_size / M.NGRID
    rec.update(pad=pad, box_size=box_size, cell=cell)

    # --- R_SMOOTH PRIMA di set_geometry, altrimenti resta inerte -------------
    if sigma_mode == "frozen":
        M.R_SMOOTH = f["sigma_px"] * cell        # sigma_px costante in unita' di griglia
    else:
        M.R_SMOOTH = 5.0                          # canonico: sigma_px insegue la cella
    M.set_geometry(box_min=box_min, box_size=box_size, verbose=True)

    sigma = float(M.SIGMA_PX)
    rec.update(R_SMOOTH=float(M.R_SMOOTH), sigma_px=sigma)
    if sigma_mode == "frozen":
        e = abs(sigma - f["sigma_px"]) / f["sigma_px"]
        rec["sigma_locked_rel"] = e
        if e > TOL_SIGMA_REL:
            sys.exit("[FATAL] override di sigma_px fallito: %.17g contro %.17g (rel %.2e)"
                     % (sigma, f["sigma_px"], e))

    # --- campi, maschera riderivata -----------------------------------------
    rec["clipped_rand"] = count_clipped(pos_r, box_min, box_size)
    field_r = M.cic_3d(pos_r, w_r, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    sum_wr = float(w_r.sum())

    # La maschera riderivata si calcola SEMPRE, anche quando non la si usa:
    # serve come diagnostica del canale di bordo.
    mask_re, thr_reported = unpack_mask(G.build_mask(field_r, "v1_fullcube"))
    thr_explicit = 0.01 * float(field_r.mean())
    mask_explicit = field_r > thr_explicit
    rec["mask_rule_agrees"] = bool(np.array_equal(mask_re, mask_explicit))
    if thr_reported is not None:
        rec["mask_threshold_reported"] = thr_reported
        rec["mask_threshold_rel"] = abs(thr_reported - thr_explicit) / abs(thr_explicit)
    if not rec["mask_rule_agrees"]:
        sys.exit("[FATAL] build_mask('v1_fullcube') non coincide con la regola esplicita "
                 "0.01*field_r.mean(). Il 2.1-M vale per la seconda.")
    rec.update(mask_threshold=thr_explicit, n_valid_rederived=int(mask_re.sum()))

    if mask_scale is not None:
        # Scala di soglia a CUBO COSTANTE: separa "N_H1 segue i voxel" da
        # "N_H1 segue la cella", che nel padladder si muovono insieme e sono
        # collineari. A mask_scale = 0.01 deve ridare esattamente build_mask.
        thr_k = float(mask_scale) * float(field_r.mean())
        mask = field_r > thr_k
        rec["mask_scale"] = float(mask_scale)
        rec["mask_threshold"] = thr_k
        if abs(float(mask_scale) - 0.01) < 1e-15 and not np.array_equal(mask, mask_re):
            sys.exit("[FATAL] a mask_scale=0.01 la maschera non coincide con build_mask.")
    elif mask_mode == "frozen":
        # DIAGNOSTICA, non il percorso di produzione: si usa deliberatamente un
        # array in spazio di indici costruito su un'ALTRA geometria. E' la
        # situazione che il 3.0 vieta; qui serve a isolare il canale di bordo.
        mp = root / "data" / "processed" / "phase6_fields" / f["mask_file"]
        if not mp.exists():
            sys.exit("[FATAL] maschera congelata assente: %s" % mp)
        mask = np.load(mp).astype(bool)
        if int(mask.sum()) != f["n_valid_voxels"]:
            sys.exit("[FATAL] la maschera congelata ha %d voxel, attesi %d."
                     % (int(mask.sum()), f["n_valid_voxels"]))
    else:
        mask = mask_re

    rec["n_valid_voxels"] = int(mask.sum())
    rec["mask_voxels_flipped"] = int(np.logical_xor(mask_re, mask).sum())
    rec["mask_gained"] = int((mask_re & ~mask).sum())
    rec["mask_lost"] = int((mask & ~mask_re).sum())

    field_d, sum_wd = data_side_fields(M, S, region, root)
    alpha_fkp = sum_wd / sum_wr
    rec.update(sum_wr=sum_wr, sum_wd=sum_wd, alpha_fkp=alpha_fkp)

    # --- campo e TDA ---------------------------------------------------------
    nu = M.build_field(field_d, field_r, alpha_fkp, mask)
    feats = M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)
    rec["N_H1"] = int(round(float(feats[4])))
    rec["b1_peak"] = float(feats[1])
    rec["seconds"] = time.time() - t0
    return rec          # R_SMOOTH e geometria si ripristinano nel finally di main()


def maskladder(M, G, S, region, root, scales, z_fid, dc_fid):
    """Scala di soglia della maschera a CUBO COSTANTE.

    Box e cella restano al fiduciale (pad = 5.0, alpha = 1); varia solo il
    moltiplicatore della soglia, quindi n_valid_voxels si muove a RISOLUZIONE
    INVARIATA. Nel padladder cella e voxel si muovono insieme e sono collineari:
    una regressione su un solo regressore non puo' decidere quale sia la causa.
    Qui la cella e' bloccata, quindi la pendenza misurata e' quella dei voxel.

    PREDIZIONE DICHIARATA PRIMA DEL RUN: la pendenza dN_H1/dV coincide con quella
    del padladder (0.0897 NGC, 0.1137 SGC) entro il 20%.
      - se coincide -> N_H1 segue il CONTEGGIO DEI VOXEL. La correzione del 3.3
        si scrive su n_valid_voxels, e va SOTTRATTA, non sommata in quadratura.
      - se la pendenza qui e' molto minore -> il regressore vero era la CELLA, e
        la correzione va riscritta prima della pre-registrazione.
    """
    f = FROZEN[region]
    sig_ens = SIGMA_ENSEMBLE[region]
    ref_slope, ref_se = PADLADDER_SLOPE[region]
    cache = {}
    rows = []
    print("  PREDIZIONE DICHIARATA: pendenza dN_H1/dV compatibile entro %.0f sigma con "
          "%.4f +/- %.4f (padladder %s)" % (SLOPE_NSIGMA, ref_slope, ref_se, region))
    print("  cubo COSTANTE: pad=5.0, alpha=1. Varia solo la soglia.")
    print("  moltiplicatori: %s\n" % ", ".join("%.4f" % k for k in scales))
    for k in scales:
        r = run(M, G, S, region, root, 1.0, "additive", "frozen", "rederived",
                z_fid, dc_fid, pad_override=PAD_FID, cache=cache, mask_scale=k)
        r["mask_scale"] = k
        rows.append(r)
        print("    k=%.4f  soglia=%.9g  cella=%.9f  voxel=%d  N_H1=%d  [%.1fs]"
              % (k, r["mask_threshold"], r["cell"], r["n_valid_voxels"],
                 r["N_H1"], r["seconds"]))
    N = np.array([r["N_H1"] for r in rows], dtype=float)
    V = np.array([r["n_valid_voxels"] for r in rows], dtype=float)
    C = np.array([r["cell"] for r in rows], dtype=float)
    cell_span = float(C.max() - C.min())
    v_span = float(V.max() - V.min())
    if v_span < 0.0005 * V.mean():
        sys.exit("[FATAL] la scala di soglia muove solo %d voxel su %d (%.4f%%): la\n"
                 "        regressione sarebbe singolare e la pendenza priva di senso.\n"
                 "        Allargare --scales finche' i voxel si muovono di almeno lo 0.5%%,\n"
                 "        cioe' un'escursione paragonabile a quella del padladder."
                 % (int(v_span), int(V.mean()), 100 * v_span / V.mean()))
    if cell_span != 0.0:
        sys.exit("[FATAL] la cella si e' mossa di %.3e: il cubo NON e' costante e la\n"
                 "        scala non separa i due regressori. Indagare prima di leggere."
                 % cell_span)
    a = np.polyfit(V, N, 1)
    slope = float(a[0])
    res = N - np.polyval(a, V)
    Sxx = float(((V - V.mean()) ** 2).sum())
    res_sd = float(res.std(ddof=1))
    se = res_sd / np.sqrt(Sxx) if Sxx > 0 else float("inf")
    rel = abs(slope - ref_slope) / ref_slope
    nsig = abs(slope - ref_slope) / np.sqrt(se ** 2 + ref_se ** 2)
    passed = nsig <= SLOPE_NSIGMA

    print("\n  cella: escursione %.3e (deve essere 0 per costruzione)" % cell_span)
    print("  voxel: %d -> %d   (%+.3f%%)" % (V[0], V[-1], 100 * (V[-1] / V[0] - 1)))
    print("  N_H1 : %d -> %d   (%+.3f%%)" % (N[0], N[-1], 100 * (N[-1] / N[0] - 1)))
    print("\n  pendenza dN_H1/dV = %.4f +/- %.4f  (%.1f%%)   r = %.4f"
          % (slope, se, 100 * se / abs(slope) if slope else float("nan"),
             float(np.corrcoef(V, N)[0, 1])))
    print("  padladder          = %.4f +/- %.4f" % (ref_slope, ref_se))
    print("  differenza %.4f = %.2f sigma combinati   limite %.0f   -> %s"
          % (slope - ref_slope, nsig, SLOPE_NSIGMA, ok_str(passed)))
    print("  (scarto relativo %.1f%%, riportato per confronto col criterio vecchio)" % (100 * rel))
    print("  proporzionalita' pura darebbe N/V = %.4f   (elasticita' %.3f)"
          % (N[0] / V[0], slope / (N[0] / V[0])))
    print("  residui attorno alla retta: sd %.1f generatori = %.3f sigma"
          % (res_sd, res_sd / sig_ens))
    if se > 0.10 * abs(ref_slope):
        print("\n  [!] la pendenza e' misurata peggio del 10%%: la leva e' insufficiente.")
        print("      Allargare --scales prima di leggere l'esito come conclusivo.")
    if passed:
        print("\n  -> N_H1 segue il CONTEGGIO DEI VOXEL. La deriva del padladder e'")
        print("     correggibile su n_valid_voxels; in quadratura entra solo il residuo.")
    else:
        print("\n  -> le due pendenze NON coincidono: nel padladder il regressore")
        print("     dominante non era il conteggio dei voxel. La correzione del 3.3")
        print("     va riscritta PRIMA della pre-registrazione.")
    return rows, dict(slope=slope, slope_se=se, ref_slope=ref_slope, ref_se=ref_se,
                      rel=rel, nsigma=nsig, nsigma_limit=SLOPE_NSIGMA,
                      res_sd=res_sd, cell_span=cell_span, v_span=v_span,
                      n_points=len(rows))


def padladder(M, G, S, region, root, pads, z_fid, dc_fid):
    """Scala di padding a cosmologia FIDUCIALE.

    Stesso catalogo, stessa cosmologia, sigma_px bloccato, maschera riderivata:
    varia solo dove cade la griglia. Nessun contenuto fisico cambia, quindi ogni
    scarto e' artefatto puro. La dispersione su questa scala E' il pavimento di
    ricampionamento del metodo, e non e' mai stato misurato.

    PREDIZIONE DICHIARATA PRIMA DEL RUN: dispersione <= 0.25 sigma dell'ensemble
    (78 generatori NGC, 49 SGC). Motivazione: il residuo a maschera ferma
    misurato dal g22a vale 0.07 sigma a 0.031 voxel di disallineamento, e la
    risposta dovrebbe saturare invece di crescere linearmente. Se sfora, la
    Componente A va ripensata PRIMA della pre-registrazione, non dopo.
    """
    f = FROZEN[region]
    sig_ens = SIGMA_ENSEMBLE[region]
    limit = LADDER_FRAC * sig_ens
    cache = {}
    rows = []
    print("  PREDIZIONE DICHIARATA: dispersione (max-min) <= %.1f generatori "
          "= %.2f sigma dell'ensemble (%.1f)" % (limit, LADDER_FRAC, sig_ens))
    print("  pad: %s\n" % ", ".join("%.2f" % p for p in pads))
    for pad in pads:
        r = run(M, G, S, region, root, 1.0, "additive", "frozen", "rederived",
                z_fid, dc_fid, pad_override=pad, cache=cache)
        r["pad"] = pad
        # spostamento della griglia rispetto al punto di riferimento pad=5.0
        r["grid_shift_voxel"] = abs(r["box_size"] / rows[0]["box_size"] - 1.0) * M.NGRID if rows else 0.0
        rows.append(r)
        print("    pad=%5.2f  box=%.6f  cella=%.9f  voxel=%d  shift=%.4f vox  N_H1=%d  [%.1fs]"
              % (pad, r["box_size"], r["cell"], r["n_valid_voxels"],
                 r["grid_shift_voxel"], r["N_H1"], r["seconds"]))
    n = np.array([r["N_H1"] for r in rows], dtype=float)
    spread = float(n.max() - n.min())
    sd = float(n.std(ddof=1))
    passed = spread <= limit
    print("\n  N_H1: min %d  max %d  escursione %d  sd %.2f" % (n.min(), n.max(), spread, sd))
    print("  escursione = %.4f sigma dell'ensemble   limite %.2f   -> %s"
          % (spread / sig_ens, LADDER_FRAC, ok_str(passed)))
    print("  escursione = %.4f%% di N_H1 fiduciale" % (100 * spread / f["N_H1"]))
    print("\n  PAVIMENTO DI RICAMPIONAMENTO da sommare in quadratura nel 3.3: %.1f generatori"
          % sd)
    if not passed:
        print("\n    La Componente A va ripensata PRIMA della pre-registrazione: a questa")
        print("    scala l'incertezza irriducibile non e' trascurabile contro il segnale AP.")
    return rows, dict(spread=spread, sd=sd, sigma_ensemble=sig_ens,
                      limit=limit, n_points=len(rows))


def main():
    ap = argparse.ArgumentParser(description="Runner di Fase 2 (2.1-D2, 2.2a/b, 2.3, padladder)")
    ap.add_argument("gate", choices=sorted(GATES))
    ap.add_argument("--region", choices=["NGC", "SGC"], required=True)
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--scales", default=None,
                    help="solo per 'maskladder': moltiplicatori della soglia, "
                         "separati da virgola. Default 0.007..0.014.")
    ap.add_argument("--pads", default=None,
                    help="solo per 'padladder': lista di pad separati da virgola. "
                         "Default 5.0..9.0 a passo 0.5.")
    ap.add_argument("--mask", choices=["rederived", "frozen"], default="rederived",
                    help="'rederived' e' il percorso di produzione (3.0). 'frozen' e' una "
                         "DIAGNOSTICA: usa l'array congelato sotto un'altra geometria, cioe' "
                         "cio' che il 3.0 vieta, per isolare il canale di bordo.")
    ap.add_argument("--baseline", type=int, default=None,
                    help="N_H1 fiduciale di questo runner (da 'd2'). "
                         "Obbligatorio per g22a/g22b/g23.")
    args = ap.parse_args()
    root = Path(args.project_root).resolve()
    region, gname = args.region, args.gate
    g = GATES[gname]
    f = FROZEN[region]

    if gname not in ("d2", "padladder", "maskladder") and args.baseline is None:
        sys.exit("[FATAL] --baseline mancante. Il delta va misurato contro il fiduciale\n"
                 "        DI QUESTO runner, non contro il congelato: chiudere prima 'd2'.")

    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
        import paper2_data_geometry as G
    except Exception as e:
        sys.exit("[FATAL] import fallito: %s" % e)
    S = None
    if region == "SGC":
        import phase9_sgc_likeforlike as S

    print("=" * 70)
    print("FASE 2  |  cancello %s  |  %s" % (gname, region))
    print("  alpha=%.4f  pad=%s  sigma=%s  mask=%s"
          % (g["alpha"], g["pad"], g["sigma"], args.mask))
    if args.mask == "frozen":
        print("  *** MODALITA' DIAGNOSTICA: maschera congelata sotto geometria diversa. ***")
        print("  Attribuzione dichiarata PRIMA del run, cancello g22a:")
        print("    delta <= 5 in ENTRAMBI  -> il canale e' la maschera. Provato.")
        print("                               Il 3.3 acquista un quinto contributo.")
        print("    delta ~ invariato       -> il canale e' il ricampionamento CIC.")
        print("                               La maschera e' innocente, il 3.3 va ripensato.")
        print("    esiti discordanti fra emisferi -> nessuna delle due; si guarda")
        print("                               il rendimento per voxel di bordo, 0.157 vs 0.043.")
    print("  PREDIZIONE DICHIARATA: %s" % g["pred"])
    print("=" * 70)

    # istantanea fiduciale: BOX_MIN va catturato ORA, non riletto nel finally,
    # dove sarebbe gia' quello dilatato.
    z_fid = np.asarray(M._Z_TAB, dtype=np.float64).copy()
    dc_fid = np.asarray(M._DC_TAB, dtype=np.float64).copy()
    box_min_fid = np.asarray(M.BOX_MIN, dtype=np.float64).copy()
    box_size_fid = float(M.BOX_SIZE)
    r_smooth_fid = float(M.R_SMOOTH)

    ladder = None
    try:
        if gname == "maskladder":
            scales = ([float(x) for x in args.scales.split(",")]
                      if args.scales else SCALES_DEFAULT)
            rows, ladder = maskladder(M, G, S, region, root, scales, z_fid, dc_fid)
            rec = dict(rows[0])
            rec["ladder"] = ladder
            rec["per_scale"] = [{"mask_scale": r["mask_scale"], "N_H1": r["N_H1"],
                                 "n_valid_voxels": r["n_valid_voxels"],
                                 "mask_threshold": r["mask_threshold"],
                                 "cell": r["cell"]} for r in rows]
        elif gname == "padladder":
            pads = ([float(x) for x in args.pads.split(",")] if args.pads else PADS_DEFAULT)
            rows, ladder = padladder(M, G, S, region, root, pads, z_fid, dc_fid)
            rec = dict(rows[0])
            rec["ladder"] = ladder
            rec["per_pad"] = [{"pad": r["pad"], "N_H1": r["N_H1"],
                               "box_size": r["box_size"], "cell": r["cell"],
                               "n_valid_voxels": r["n_valid_voxels"],
                               "grid_shift_voxel": r["grid_shift_voxel"]} for r in rows]
        else:
            rec = run(M, G, S, region, root, g["alpha"], g["pad"], g["sigma"],
                      args.mask, z_fid, dc_fid)
    finally:
        M.R_SMOOTH = r_smooth_fid
        M.set_geometry(z_tab=z_fid, dc_tab=dc_fid, verbose=False)
        M.set_geometry(box_min=box_min_fid, box_size=box_size_fid, verbose=False)
        # L'invariante e' "il runner lascia il modulo come l'ha trovato", NON
        # "torna al congelato della regione": all'import le globali di
        # phase8_cutsky_mocks sono quelle NGC, quindi in un run SGC lo stato
        # iniziale non e' il fiduciale SGC. E' la trappola annotata nel 3.0.
        bad = (abs(M.BOX_SIZE - box_size_fid) > 0.0
               or not np.array_equal(np.asarray(M.BOX_MIN), box_min_fid)
               or M.R_SMOOTH != r_smooth_fid)
        print("[restore] stato del modulo ripristinato all'import%s."
              % ("  *** RESIDUO: %r ***" % {"box": M.BOX_SIZE, "R": M.R_SMOOTH}
                 if bad else ""))

    if gname == "maskladder":
        passed = ladder["nsigma"] <= ladder["nsigma_limit"]
        rec.update(ts=now(), gate=gname, prediction=g["pred"], **{"pass": bool(passed)})
        append_jsonl(root / LOG, rec)
        print("\n=== maskladder %s %s ===" % (region, ok_str(passed)))
        sys.exit(0 if passed else 1)

    if gname == "padladder":
        passed = ladder["spread"] <= ladder["limit"]
        rec.update(ts=now(), gate=gname, prediction=g["pred"], **{"pass": bool(passed)})
        append_jsonl(root / LOG, rec)
        print("\n=== padladder %s %s ===" % (region, ok_str(passed)))
        sys.exit(0 if passed else 1)

    print("\n  box   = %.10f   cella = %.12f" % (rec["box_size"], rec["cell"]))
    print("  R_SMOOTH = %.12f   sigma_px = %.17g" % (rec["R_SMOOTH"], rec["sigma_px"]))
    print("  maschera [%s]: soglia %.18g   voxel usati %d   riderivati %d"
          % (rec["mask_mode"], rec["mask_threshold"], rec["n_valid_voxels"],
             rec["n_valid_rederived"]))
    if rec["mask_voxels_flipped"]:
        print("     differenza usata/riderivata: %d voxel (%+d riderivati in piu', %+d in meno)"
              % (rec["mask_voxels_flipped"], rec["mask_gained"], rec["mask_lost"]))
    print("  random fuori dal cubo (clippati da cic_3d): %d" % rec["clipped_rand"])
    print("  N_H1 = %d      [%.1fs]" % (rec["N_H1"], rec["seconds"]))

    if gname == "d2":
        delta = rec["N_H1"] - f["N_H1"]
        passed = (delta == 0)
        print("\n[2.1-D2] N_H1 = %d   congelato = %d   delta = %+d   -> %s"
              % (rec["N_H1"], f["N_H1"], delta, ok_str(passed)))
        for k, ref in (("n_valid_voxels", f["n_valid_voxels"]),
                       ("N_rand", f["N_rand"])):
            good = rec[k] == ref
            passed &= good
            print("     %-16s %d   atteso %d   %s" % (k, rec[k], ref, ok_str(good)))
        for k, ref in (("box_size", f["box_size"]), ("cell", f["cell"]),
                       ("sigma_px", f["sigma_px"]), ("mask_threshold", f["mask_threshold"])):
            e = abs(rec[k] - ref) / abs(ref)
            good = e <= TOL_GEOM_REL
            passed &= good
            print("     %-16s %.17g   rel %.2e   %s" % (k, rec[k], e, ok_str(good)))
        if not passed:
            print("\n    Il 2.2 NON va lanciato: senza chiusura del runner il delta misura\n"
                  "    la differenza fra due codici piu' la geometria.")
    else:
        delta = rec["N_H1"] - args.baseline
        rec["baseline"] = args.baseline
        rec["delta"] = delta
        if gname == "g22b":
            passed = (delta == 0)
        elif gname == "g22a":
            passed = (abs(delta) <= 5)
        else:
            passed = (delta > 0)
        print("\n[%s] N_H1 = %d   baseline = %d   delta = %+d   -> %s"
              % (gname, rec["N_H1"], args.baseline, delta, ok_str(passed)))
        print("     predizione: %s" % g["pred"])
        if gname == "g22b" and passed:
            print("     NOTA per il verbale: sotto pad scalato il rapporto (pos-box_min)/cell e'")
            print("     invariante bit a bit, quindi questo esito NON dice nulla sul problema")
            print("     della maschera in spazio di indici della Fase 3.")

    rec.update(ts=now(), gate=gname, prediction=g["pred"], **{"pass": bool(passed)})
    if args.mask == "frozen":
        rec["diagnostic"] = True          # non e' un esito di cancello
    append_jsonl(root / LOG, rec)
    tag = "%s %s [mask=%s]" % (gname, region, args.mask)
    if args.mask == "frozen":
        print("\n    Questo NON e' un esito di cancello: e' una diagnostica di attribuzione.")
        print("    Il verdetto del %s resta quello a maschera riderivata." % gname)
    print("\n=== %s %s ===" % (tag, ok_str(passed)))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

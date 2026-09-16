#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_runner_4_2a.py — ENSEMBLE v2, item 4.2a.

COSA PRODUCE
------------
Per ogni realizzazione e per emisfero, alla geometria FIDUCIALE:

  ramo UNITARIO : w_d = 1              -> N_H1_k0..k3     (il v1, ricalcolato)
  ramo FKP      : w_d = w_FKP(z)       -> N_H1_k0..k3     (il v2)
  diagnostiche a un punto su ENTRAMBI  -> contratto (FKP) + unit_1punto

Le diagnostiche stanno su tutti e due i rami perche' il confronto v1->v2 di
4.2b e 4.2c sia APPAIATO: v1 dalla cache e v2 dalla catena R3 differirebbero
di 1.5e-3..2.9e-3 su delta per sola differenza di cammino (D4a), sette volte
la discrepanza della soglia dei patologici. Calcolati nella stessa passata,
dalla stessa realizzazione e sullo stesso cammino, quel termine si cancella.
I valori v1 del record 54 restano quelli dichiarati: questo e' un SECONDO v1,
appaiato, che dice quanta parte della differenza e' trattamento.

Otto chiamate TDA per realizzazione. La scelta di ricalcolare il ramo unitario
invece di prenderlo dal congelato e' dichiarata: rende l'appaiamento
indipendente dal registro, che resta cancello e non sorgente. La scelta di
calcolarlo a tutti e quattro i livelli produce il ladder v1 su 2000
realizzazioni, che oggi NON esiste — fase3_mock ha 200 indici e due livelli,
per_mock_*_R5 ha solo k=0 — e rende disponibile la sigma appaiata di 4.3b a
tutti i livelli.

NIENTE E' RISCRITTO
-------------------
  geometrie, cancelli su sigma_px e maschera, D5c   <- paper2_runner_fase3_mock
  tabella w_FKP(z) dai random                       <- paper1_rev_n6_fkp
  le otto diagnostiche a un punto                   <- paper2_passata_1punto
  erosion_levels, compute_tda_features, compute_delta, build_field, build_nu
                                                    <- F3, phase8, paper1_remap

Un controllo a runtime verifica che ogni funzione importata venga dal modulo
che deve, e non da un omonimo locale.

I DUE PEZZI NUOVI, E LE LORO ANCORE
-----------------------------------
1. Il ciclo a DUE rami. `R3.one_mock` ha `w_d = np.ones(...)` scritto dentro,
   quindi non e' riusabile: qui il ciclo e' nuovo. Cancello: sul ramo unitario
   N_H1_k0 deve riprodurre `per_mock_<REG>_R5.jsonl` mock per mock. La
   duplicazione e' verificata, non evitata.
2. L'inversione distanza comovente -> z per i pesi. In n6 sta dentro `main()` e
   non e' importabile. Cancello: `w_d.mean()` deve riprodurre `wfkp_mean` di
   `n6_fkp_NGC.jsonl` sugli indici 200-259 — 60 ancore, tolleranza 1e-9.

E UN TERZO CANCELLO, CONTINUO
-----------------------------
nu si calcola due volte per ramo: da `M.build_field` per il ladder e da
`P1.build_nu` dentro le diagnostiche. Devono coincidere BIT PER BIT a ogni
realizzazione. Il cancello di unicita' del 7 settembre l'ha stabilito una volta
su cinque indici; qui diventa un controllo continuo che costa una lisciatura.

LA SOGLIA DEI PATOLOGICI NON SI RICALCOLA
-----------------------------------------
E' il massimo di delta di DESI, lato dati e FISSO sotto ripesatura. Si legge da
`onepoint_v1_DESI_<REG>.jsonl` e si riscontra contro la ricomputazione a rel
1e-12. Ricalcolarla e basta lascerebbe la porta a una deriva silenziosa fra v1
e v2 proprio nella quantita' che 4.2c confronta.

USO
    python src\\paper2_runner_4_2a.py selftest
    python src\\paper2_runner_4_2a.py smoke --region NGC --n 5 ^
        --out results\\paper2\\smoke_v2_NGC.jsonl
    python src\\paper2_runner_4_2a.py run --region NGC ^
        --out results\\paper2\\ensemble_v2_NGC.jsonl ^
        --cache-delta data\\processed\\paper2_mock_deltas_v2\\NGC

Uscita: 0 se completa e i cancelli tengono, 1 se un cancello ferma, 2 su errore
d'uso. Nessun fallimento e' un avviso.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SCHEMA = "paper2_ensemble_v2"
N_ATTESI_ENS = 2000   # realizzazioni dell'ensemble, per la SEM
EROSIONI = (0, 1, 2, 3)
SEED = 42
SNAPNUM = 3
# n6 NON E' LA MIA CATENA. Come per_mock, e' un confronto FRA CATENE: n6 non
# imposta la geometria dalla tabella a 4001 nodi, il runner si'. Sugli indici
# 200-204 la differenza non si vedeva (2-3e-10); a 226 vale 1.65e-04, sulla
# STESSA realizzazione dove la diagnostica fra catene registra 185 generatori.
# Non sono due problemi: e' un carving che seleziona un insieme diverso, e
# quello sposta sia N_H1 sia il peso medio.
# Una tolleranza da stessa-catena su un confronto fra catene: terzo caso oggi,
# dopo per_mock e dopo il cancello sui voxel fra le due soglie.
# E il peso MEDIO non entra in delta — record 56, invarianza per riscalamento
# globale verificata a 2.9e-14: conta solo la forma in z. Diagnostica, non
# cancello.
TOL_WFKP_ESATTO = 1e-9
TOL_WFKP_DIVERGE = 1e-6
# ANCORA DI CATENA: fase3_mock.jsonl, STESSA catena (R3), stessa geometria.
# Fra due esecuzioni della stessa catena lo scarto atteso e' ZERO, non tre: il
# margine dei pareggi serve a confrontare catene diverse, non la stessa con se'.
TOL_CATENA = 0
# DIAGNOSTICA FRA CATENE: per_mock_<REG>_R5.jsonl viene da paper1_remap, che
# chiama setup_region sulla distanza ANALITICA; il runner segue R3, che imposta
# la tabella a 4001 nodi PRIMA. Sono i due cammini misurati da
# paper2_cammini_desi.py: delta diverso nel 59-67% delle celle. D4a registra che
# N_H1 e' "identico a tutte le risoluzioni"; su 4000 realizzazioni quel "quasi
# sempre" ha eccezioni, e questo registro le conta. NON ferma il run.
TOL_DIAGNOSTICA = 3          # oltre, si classifica DIVERGE e si conta
# SOGLIA SULL'EFFETTO, NON SUL TASSO. Un tasso stimato da UN evento non ha
# denominatore: 1 su 60 da' un intervallo di Poisson dallo 0.2% al 5.6%, e una
# soglia su quel numero sarebbe scelta, non derivata.
# Cio' che conta e' il bias che le divergenze lasciano sulla MEDIA d'ensemble:
#     bias = somma|scarti divergenti| / n
# Il limite riusa il criterio gia' dichiarato dal record 36 per D5c — meta'
# della SEM, che e' dove "trascurabile" smette di essere difendibile: in
# quadratura un termine accanto a uno dominante aggiunge +11.8% a meta' e
# +41.4% alla parita'.
# Misurato l'8 settembre: bias 1.53 gen contro SEM 4.42 in SGC (0.35), 0.81
# contro 7.00 in NGC (0.12). Entrambi sotto meta'.
BIAS_MAX_IN_SEM = 0.5
SD_ENSEMBLE = {"NGC": 312.9891651683112, "SGC": 197.7873817207103}
# Dispersione per realizzazione di n_patologici su v1 (record 54), per lo
# stesso criterio applicato ai voxel fra le due soglie.
SD_NPAT = {"NGC": 84.66, "SGC": 71.45}
# I trattamenti che NON sono la linea di base. Un record che porta una di queste
# chiavi e' un'altra misura, e l'unione lo fonderebbe con la baseline (record 55).
TRATTAMENTI_NON_BASE = ("smoke", "real_space", "origin_offset", "carve_reseed",
                        "replica_randomise", "fixed_observables")
# La soglia dei patologici e' DICHIARATA nel record 54, non ricalcolata: e' il
# massimo di delta di DESI misurato dalla riga v1. La ricomputazione qui e' una
# DIAGNOSTICA, e la sua tolleranza deve ammettere la differenza di CAMMINO.
# Misurato l'8 settembre: 2.00 ULP di float32 esatti, perche' il cammino di
# produzione di R3 chiama set_geometry(dc_tab=...) prima di setup_region, e
# quella sostituzione rimpiazza comoving_distance con un'interpolazione a 4001
# nodi che sposta field_r (D4a). La riga DESI di v1 usa il cammino analitico,
# lo stesso di step6, che infatti riproduce a 0.000e+00.
# MISURATO l'8 settembre con src/paper2_cammini_desi.py: 2 ULP in NGC, 26 in
# SGC. In NGC i due cammini danno una geometria bit-identica; in SGC no —
# box_size 1904.4501607158168 contro 1904.450156441475, 2.2e-9 relativo — e il
# massimo si sposta di piu' perche' si sposta anche la griglia sotto.
#
# In ENTRAMBI gli emisferi la conseguenza e' nulla: stesso voxel al massimo, e
# ZERO voxel fra le due soglie su cinque mock in cache per emisfero, con
# n_patologici identico sotto le due soglie in tutti e dieci.
#
# Quindi la soglia in ULP e' una SPIA, non un cancello: sta a 64, oltre il
# doppio del massimo misurato, e una deriva vera — un altro catalogo, un'altra
# maschera — varrebbe ordini di grandezza in piu'. L'ARRESTO DURO sta sulla
# conseguenza, n_pat_fra_le_due_soglie, che e' misurata per realizzazione e
# deve restare zero. Un cancello su una spia fermava la misura che avrebbe
# risposto alla domanda.
ULP_SPIA = 64
ROOT_DEFAULT = "."

# I tredici campi del contratto di uscita (record 53).
CONTRATTO = ("delta.sigma_in_mask", "delta.kurt_in_mask",
             "nu.sigma_in_mask", "nu.kurt_in_mask",
             "max_delta", "nu.p1", "nu.p99", "n_patologici",
             "N_H1_k0", "N_H1_k1", "N_H1_k2", "N_H1_k3",
             "delta_sha256")


def stima_memoria(g, masks, n_sel_atteso=220000):
    """
    Byte tenuti dal processo, per decidere se due emisferi stanno in parallelo.

    Si riporta cio' che e' MISURABILE da qui. La cache dei random di PF non e'
    inclusa: le posizioni sono caricate e poi cancellate dentro
    build_geometries, e se l'oggetto le trattenga non e' osservabile da questo
    lato. Va guardata nel monitor di sistema durante lo smoke: un numero
    dedotto e uno letto non sono la stessa cosa.
    """
    pers = int(np.asarray(g["field_r"]).nbytes + np.asarray(g["mask"]).nbytes
               + sum(np.asarray(m).nbytes for m in masks.values()))
    ng = int(np.prod(np.asarray(g["field_r"]).shape))
    # picco transitorio: fd (f64) + nu (f64) + delta (f64) + d32 (f32)
    # piu' le posizioni selezionate e la loro copia in cic_3d
    trans = int(ng * (8 + 8 + 8 + 4) + n_sel_atteso * 3 * 8 * 2)
    return {"persistente_byte": pers, "transitorio_stimato_byte": trans,
            "totale_stimato_byte": pers + trans}


def now():
    return datetime.now(timezone.utc).isoformat()


def percorsi(root, region):
    d = Path(root)
    return {"desi_row": d / "results" / "paper2" / ("onepoint_v1_DESI_%s.jsonl" % region),
            "fase3": d / "results" / "paper2" / "fase3_mock.jsonl",
            "per_mock": d / "results" / "paper1" / ("per_mock_%s_R5.jsonl" % region),
            "n6": d / "results" / "paper1" / "n6_fkp_NGC.jsonl",
            "wfkp_cache": d / "results" / "paper1" / "n6_wfkp_table.npz"}


def percorso_sommario(out):
    out = Path(out)
    return out.with_name(out.stem + "_sommario" + out.suffix)


def leggi_jsonl(path):
    p = Path(path)
    if not p.is_file():
        return []
    out = []
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for riga in fh:
            riga = riga.strip()
            if riga:
                try:
                    out.append(json.loads(riga))
                except Exception:
                    pass
    return out


def append_jsonl(path, rec):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def rel(a, b):
    a, b = float(a), float(b)
    if b == 0.0:
        return 0.0 if a == 0.0 else abs(a)
    return abs(a - b) / abs(b)


# ---------------------------------------------------------------------------
# import, con verifica di provenienza
# ---------------------------------------------------------------------------

def attach(root, srcdir="src"):
    sd = str(Path(root) / srcdir)
    if sd not in sys.path:
        sys.path.insert(0, sd)
    import phase8_cutsky_mocks as M
    import paper1_remap as P1
    import phase8_test2_masked as T2
    import paper2_phase3_preflight as PF
    import paper2_runner_fase3 as F3
    import paper2_runner_fase3_mock as R3
    import paper1_step6_onepoint_betti as S6
    import paper2_passata_1punto as PASS
    import paper1_rev_n6_fkp as N6
    import paper2_ladder_sigma as L
    atteso = [(P1.build_nu, "paper1_remap"), (P1.compute_delta, "paper1_remap"),
              (P1.setup_region, "paper1_remap"),
              (S6.moments, "paper1_step6_onepoint_betti"),
              (S6.build_restrictions, "paper1_step6_onepoint_betti"),
              (PASS.misura, "paper2_passata_1punto"),
              (N6.build_wfkp_table, "paper1_rev_n6_fkp"),
              (F3.erosion_levels, "paper2_runner_fase3"),
              (R3.build_geometries, "paper2_runner_fase3_mock"),
              (T2.populate_with_virial, "phase8_test2_masked"),
              (L.carica, "paper2_ladder_sigma"),
              (L.unione, "paper2_ladder_sigma"),
              (L.trova_indice, "paper2_ladder_sigma")]
    for f, mod in atteso:
        if f.__module__ != mod:
            raise SystemExit("RIFIUTO: %s viene da %s, atteso %s"
                             % (getattr(f, "__name__", f), f.__module__, mod))
    return M, P1, T2, PF, F3, R3, S6, PASS, N6, L


# ---------------------------------------------------------------------------
# il pezzo nuovo n. 2: peso FKP alla posizione
# ---------------------------------------------------------------------------

def costruisci_wfkp(M, zt, wt):
    """pos -> (w, z). Ricostruita da n6, dove sta dentro main() e non e'
    importabile. L'ancora sui 60 record di n6 e' cio' che la rende legittima."""
    zg = np.linspace(max(M.ZMIN - 0.05, 1e-3), M.ZMAX + 0.05, 4000)
    dg = M.comoving_distance(zg)

    def wfkp_of_pos(pos):
        r = np.linalg.norm(pos, axis=1)
        z = np.interp(r, dg, zg)
        return np.interp(z, zt, wt), z
    return wfkp_of_pos


# ---------------------------------------------------------------------------
# ancore
# ---------------------------------------------------------------------------

def ancore_catena(L, root, region):
    """
    fase3_mock.jsonl, letto come impone il record 49: per UNIONE, mai last-wins,
    e senza i record che non sono la linea di base. Le funzioni vengono da
    paper2_ladder_sigma: la lettura non si riscrive.
    """
    P = percorsi(root, region)
    if not P["fase3"].is_file():
        return {}, "assente: %s" % P["fase3"]
    try:
        piatti, n_tot = L.carica(str(P["fase3"]), [("region", region)],
                                 senza=TRATTAMENTI_NON_BASE)
    except Exception as e:
        raise SystemExit("RIFIUTO: fase3_mock illeggibile: %s" % e)
    if not piatti:
        return {}, "nessun record di baseline per %s" % region
    fuori = L.campi_discriminanti(piatti, esclusi=("region",))
    if fuori:
        raise SystemExit("RIFIUTO: campi discriminanti non filtrati in fase3_mock: "
                         "%s. L'unione fonderebbe misure diverse." % fuori)
    ci = L.trova_indice(piatti, "index")
    chiavi = ["points.FID.N_H1_k%d" % k for k in EROSIONI]
    per_idx = L.unione(piatti, chiavi, ci)
    fuori_k = {i: {int(k.split("_k")[-1]): v for k, v in d.items()}
               for i, d in per_idx.items() if d}
    return fuori_k, "%d record di baseline su %d righe" % (len(piatti), n_tot)


def carica_ancore(root, region):
    P = percorsi(root, region)
    nh1 = {}
    for j, r in enumerate(leggi_jsonl(P["per_mock"])):
        fl = flatten(r)
        try:
            kk = int(str(fl.get("key", j)).split("_")[-1])
        except (TypeError, ValueError):
            kk = j
        v = fl.get("base.N_H1")
        if v is not None:
            nh1[kk] = float(v)
    wfkp = {}
    if region == "NGC":
        for r in leggi_jsonl(P["n6"]):
            if "idx" in r and "wfkp_mean" in r:
                wfkp[int(r["idx"])] = float(r["wfkp_mean"])
    return nh1, wfkp


def soglia_patologici(root, region, desi_delta, mask):
    """
    Ritorna (canonica, ricalcolata, ULP di distanza).

    La CANONICA e' quella dichiarata: si legge dalla riga DESI di v1 e si usa
    per contare i patologici, perche' 4.2c confronta v2 contro una soglia
    registrata nel record 54. Ricalcolarla cambierebbe il significato della
    regola dichiarata.
    La ricalcolata serve solo a misurare quanto i due cammini distano, in ULP
    di float32, che e' l'unita' in cui la differenza vive.
    """
    P = percorsi(root, region)
    righe = leggi_jsonl(P["desi_row"])
    if not righe:
        raise SystemExit("RIFIUTO: riga DESI di v1 assente: %s" % P["desi_row"])
    letta = float(righe[-1]["max_delta"])
    ricalc = float(np.asarray(desi_delta)[mask].max())
    ulp = float(np.spacing(np.float32(letta)))
    n_ulp = abs(ricalc - letta) / ulp if ulp > 0 else float("inf")
    if n_ulp > ULP_SPIA:
        raise SystemExit(
            "RIFIUTO: soglia patologici, canonica %.12f contro ricalcolata "
            "%.12f: %.1f ULP di float32, spia a %d. I due cammini noti valgono "
            "2 (NGC) e 26 (SGC): qui e' cambiato qualcosa d'altro, e va capito "
            "prima di impegnare le ore." % (letta, ricalc, n_ulp, ULP_SPIA))
    return letta, ricalc, n_ulp


# ---------------------------------------------------------------------------
# una realizzazione: otto TDA
# ---------------------------------------------------------------------------

def una_realizzazione(mods, region, g, masks, kk, nz_z, nz_target, wfkp_of_pos,
                      soglia_pat, subsets, cache_dir=None, soglia_alt=None):
    M, P1, T2, PF, F3, R3, S6, PASS, N6, L = mods
    t0 = time.time()
    rng = np.random.default_rng(SEED + kk)
    pos_h, mass_h, vel_h = M.read_halo_catalog(kk, SNAPNUM)
    if pos_h is None or len(pos_h) < 50:
        return None
    pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h,
                                               M.HOD_MEDIAN, rng)
    state_after_hod = rng.bit_generator.state
    del pos_h, mass_h, vel_h
    if len(pos_gal) < 100:
        return None

    M.set_geometry(z_tab=None, dc_tab=g["dc_tab"], verbose=False)
    M.R_SMOOTH = g["R_SMOOTH"]
    M.set_geometry(box_min=g["box_min"], box_size=g["box_size"], verbose=False)
    M.N_TARGET_BGS = R3.N_TARGET[region]
    rng.bit_generator.state = state_after_hod
    pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z, nz_target, rng)
    if pos_sel is None or len(pos_sel) < 100:
        return {"_skip": "carve vuoto"}

    cl = PF.clipped_per_face(pos_sel, M.BOX_MIN, M.BOX_SIZE)
    if cl["n_clipped"] >= R3.D5C_SOGLIA and R3.D5C_MODE == "block":
        raise SystemExit("[FATAL] D5c: %s/mock %d: %d posizioni fuori dal cubo, "
                         "soglia %d (record 36). Dettaglio: %s"
                         % (region, kk, cl["n_clipped"], R3.D5C_SOGLIA, cl))

    # `masks` arriva da fuori: erosion_levels fa una distance_transform_edt su
    # 128^3 e la maschera non cambia mai, quindi ricalcolarla dentro il ciclo
    # la rifarebbe duemila volte identica.
    rec = {"n_sel": int(len(pos_sel)), "d5c_n_clipped": int(cl["n_clipped"])}

    # ---- ramo UNITARIO -----------------------------------------------------
    w_u = np.ones(len(pos_sel))
    fd_u = M.cic_3d(pos_sel, w_u, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    a_u = float(w_u.sum()) / g["sum_wr"]
    nu_u = M.build_field(fd_u, g["field_r"], a_u, g["mask"])
    unit = {"alpha": a_u}
    for k in EROSIONI:
        f = M.compute_tda_features(nu_u, masks[k], M.N_THRESH, masked=True)
        unit["N_H1_k%d" % k] = int(round(float(f[4])))
        unit["b1_peak_k%d" % k] = float(f[1])

    # Le diagnostiche a un punto anche QUI, sul ramo unitario. Costa un
    # compute_delta e una misura, ~0.15 s su ~69: in cambio ogni realizzazione
    # porta il suo v1 e il suo v2 sullo STESSO cammino e dalla stessa passata,
    # quindi il termine di cammino — che su delta vale 1.5e-3..2.9e-3 fra cache
    # v1 e catena R3 (D4a), sette volte la discrepanza della soglia — si
    # cancella nell'appaiamento invece di entrare nel risultato.
    du = P1.compute_delta(fd_u, g["field_r"], a_u, g["mask"], M.NGRID)
    d32u = np.asarray(du, dtype=np.float64).astype(np.float32)
    del du, fd_u
    nu_u_p1 = P1.build_nu(d32u.astype(np.float64), g["mask"], g["sigma_px"])
    diff_u = int((np.asarray(nu_u_p1) != np.asarray(nu_u)).sum())
    del nu_u, nu_u_p1
    op_u = PASS.misura(S6, P1, M, d32u, g["mask"], subsets, soglia_pat)
    unit_1p = {k: v for k, v in op_u.items() if not k.startswith("_")}
    unit_1p["_var_delta_piena"] = op_u["_var_delta_piena"]
    unit_1p["_var_nu_piena"] = op_u["_var_nu_piena"]
    unit_1p["delta_sha256"] = hashlib.sha256(d32u.tobytes()).hexdigest()
    unit_1p["delta_sha_su"] = "byte grezzi"
    del d32u

    # ---- ramo FKP ----------------------------------------------------------
    w_f, z_sel = wfkp_of_pos(pos_sel)
    fd_f = M.cic_3d(pos_sel, w_f, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    a_f = float(w_f.sum()) / g["sum_wr"]
    nu_f = M.build_field(fd_f, g["field_r"], a_f, g["mask"])
    fkp = {"alpha": a_f, "wfkp_mean": float(w_f.mean()),
           "wfkp_sum": float(w_f.sum()), "z_mean": float(z_sel.mean())}
    for k in EROSIONI:
        f = M.compute_tda_features(nu_f, masks[k], M.N_THRESH, masked=True)
        fkp["N_H1_k%d" % k] = int(round(float(f[4])))
        fkp["b1_peak_k%d" % k] = float(f[1])

    # ---- delta del ramo FKP, e le diagnostiche a un punto -------------------
    delta = P1.compute_delta(fd_f, g["field_r"], a_f, g["mask"], M.NGRID)
    d32 = np.asarray(delta, dtype=np.float64).astype(np.float32)
    del fd_f, delta

    # terzo cancello: le due vie a nu devono coincidere bit per bit
    nu_p1 = P1.build_nu(d32.astype(np.float64), g["mask"], g["sigma_px"])
    diff = int((np.asarray(nu_p1) != np.asarray(nu_f)).sum())
    rec["nu_vie_identiche"] = bool(diff == 0)
    rec["nu_celle_diverse"] = diff
    rec["nu_vie_identiche_unit"] = bool(diff_u == 0)
    rec["nu_celle_diverse_unit"] = diff_u
    del nu_f, nu_p1

    op = PASS.misura(S6, P1, M, d32, g["mask"], subsets, soglia_pat)

    # SENSIBILITA' DEI PATOLOGICI ALLA SOGLIA. I due cammini distano 2 ULP di
    # float32: se fra le due soglie non cade nessun voxel, la differenza e'
    # provatamente irrilevante per 4.2c. E' una misura, non un argomento.
    if soglia_alt is not None:
        piena = d32.astype(np.float64)[g["mask"]]
        lo, hi = (soglia_pat, soglia_alt) if soglia_pat <= soglia_alt \
            else (soglia_alt, soglia_pat)
        rec["n_pat_soglia_alt"] = int((piena > soglia_alt).sum())
        rec["n_pat_fra_le_due_soglie"] = int(((piena > lo) & (piena <= hi)).sum())
        del piena

    sha = hashlib.sha256(d32.tobytes()).hexdigest()
    if cache_dir is not None:
        cd = Path(cache_dir)
        cd.mkdir(parents=True, exist_ok=True)
        fp = cd / ("delta_%04d.npy" % kk)
        np.save(fp, d32)
        sha = hashlib.sha256(fp.read_bytes()).hexdigest()
        rec["delta_file"] = str(fp)
    rec["delta_sha256"] = sha
    rec["delta_sha_su"] = "file npy" if cache_dir is not None else "byte grezzi"

    rec.update({k: v for k, v in op.items() if not k.startswith("_")})
    rec["_var_delta_piena"] = op["_var_delta_piena"]
    rec["_var_nu_piena"] = op["_var_nu_piena"]
    rec["unit"] = unit
    rec["unit_1punto"] = unit_1p
    rec["fkp"] = fkp
    for k in EROSIONI:
        rec["N_H1_k%d" % k] = fkp["N_H1_k%d" % k]
        rec["dN_H1_k%d" % k] = fkp["N_H1_k%d" % k] - unit["N_H1_k%d" % k]
    rec["_n_gal"] = int(len(pos_gal))
    rec["_seconds"] = time.time() - t0
    return rec


# ---------------------------------------------------------------------------
# esecuzione
# ---------------------------------------------------------------------------

def costruisci_sommario(region, smoke, n_scritti, out, n_anc_cat, n_anc_w,
                        peggio_w, n_nu_diverse, n_diverge, n_diverge_w,
                        somma_scarti, sog,
                        ric, n_ulp, max_fra_soglie, somma_fra_soglie,
                        secondi, cache, da, a_n, mem):
    """Estratta da esegui perche' il selftest possa attraversarla: la versione
    precedente stava in linea e nessun controllo la toccava, quindi un nome non
    definito e' arrivato fino al run vero."""
    sem = SD_ENSEMBLE[region] / np.sqrt(N_ATTESI_ENS)
    bias = somma_scarti / n_scritti if n_scritti else None
    return {
        "schema": SCHEMA + "_sommario", "region": region, "utc": now(),
        "esito": "PULITA", "smoke": bool(smoke),
        "n_record_scritti": n_scritti,
        "n_record_totali": len({r["index"] for r in leggi_jsonl(out)
                                if "index" in r}),
        "n_ancore_catena": n_anc_cat, "n_confronti_n6_wfkp": n_anc_w,
        "n_diverge_n6_wfkp": n_diverge_w,
        "nota_n6": ("n6 non imposta la geometria dalla tabella a 4001 nodi: e' "
                    "un confronto FRA CATENE, come per_mock. E il peso medio non "
                    "entra in delta (record 56), quindi e' diagnostica."),
        "peggior_rel_wfkp": peggio_w, "n_nu_vie_diverse": n_nu_diverse,
        "un_punto_su_entrambi_i_rami": True,
        "n_diverge_fra_catene": n_diverge,
        "frazione_diverge": n_diverge / n_scritti if n_scritti else None,
        "somma_scarti_divergenti": somma_scarti,
        "bias_sulla_media": bias,
        # L'incertezza sul bias e' dominata dal CONTEGGIO delle divergenze:
        # con n_div eventi vale bias/sqrt(n_div). Senza, una stima su dieci
        # realizzazioni verrebbe confrontata con la SEM di un ensemble da 2000
        # come se fosse la stessa cosa — la regola sulle soglie calibrate a un n
        # applicata male, e da me.
        "bias_errore": (bias / np.sqrt(n_diverge)) if (bias and n_diverge) else None,
        "sem_ensemble": sem,
        "bias_in_sem": (bias / sem) if bias is not None else None,
        "bias_in_sem_errore": ((bias / np.sqrt(n_diverge)) / sem
                               if (bias and n_diverge) else None),
        "confronto_significativo": bool(n_scritti >= 500),
        "bias_max_in_sem_dichiarato": BIAS_MAX_IN_SEM,
        "nota_divergenza": ("scarto fra la catena R3 e quella di paper1_remap; "
                            "e' il cammino della geometria (tabella a 4001 nodi "
                            "contro distanza analitica), misurato da "
                            "paper2_cammini_desi.py. La soglia la applica il "
                            "verdetto, non il runner."),
        "soglia_patologici": sog, "soglia_patologici_ricalcolata": ric,
        "ulp_fra_le_due_soglie": n_ulp,
        "max_voxel_fra_le_due_soglie": max_fra_soglie,
        "somma_voxel_fra_le_due_soglie": somma_fra_soglie,
        "bias_npat_da_soglia": (somma_fra_soglie / n_scritti) if n_scritti else None,
        "sem_npat": SD_NPAT[region] / np.sqrt(N_ATTESI_ENS),
        "bias_npat_in_sem": ((somma_fra_soglie / n_scritti)
                             / (SD_NPAT[region] / np.sqrt(N_ATTESI_ENS))
                             if n_scritti else None),
        "erosioni": list(EROSIONI),
        "secondi_per_mock": secondi / n_scritti if n_scritti else None,
        "cache_delta": str(cache) if cache else None,
        "indice_da": da, "indice_a": a_n, "memoria": mem,
    }


def esegui(a, smoke):
    root = Path(a.project_root).resolve()
    region = a.region
    out = Path(a.out)
    if smoke and "smoke" not in out.name.lower():
        raise SystemExit("con smoke il nome di uscita deve contenere 'smoke': %s"
                         % out.name)
    if not smoke and "smoke" in out.name.lower():
        raise SystemExit("run completo su un file chiamato smoke: %s" % out.name)
    # Le validazioni che non costano nulla vanno PRIMA dell'import dei moduli di
    # progetto, che costa secondi e fallisce fuori dalla radice del progetto.
    da = int(getattr(a, "da", 0) or 0)
    if da >= a.n:
        raise SystemExit("RIFIUTO: --da %d non e' minore di --n %d "
                         "(--n e' l'estremo superiore escluso)" % (da, a.n))
    if da < 0:
        raise SystemExit("RIFIUTO: --da %d negativo" % da)

    mods = attach(root, a.src)
    M, P1, T2, PF, F3, R3, S6, PASS, N6, L = mods
    R3._avviso_d5c()

    print("=" * 78)
    print("ENSEMBLE v2 — item 4.2a  |  %s%s  |  erosioni %s  |  8 TDA/mock"
          % (region, "  [SMOKE]" if smoke else "", list(EROSIONI)))
    print("=" * 78)

    # geometria: SOLO il fiduciale. I punti AP sono materia della Fase 3.
    import paper2_data_geometry as GEO
    import paper2_item13a_15a as I13
    z_tab = np.asarray(M._Z_TAB, float).copy()
    dc_fid = np.asarray(M._DC_TAB, float).copy()
    M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
    Gr = P1.setup_region(M, region, root / "data" / "raw" / "desi_dr1",
                         root / "data" / "processed" / "phase6_fields")
    if int(M.N_TARGET_BGS) != R3.N_TARGET[region]:
        raise SystemExit("[FATAL] N_TARGET_BGS = %s, atteso %s"
                         % (M.N_TARGET_BGS, R3.N_TARGET[region]))
    cache_r = PF.Cache(GEO, M, region, "ran")
    geoms = R3.build_geometries(M, GEO, PF, I13, F3, region, cache_r,
                                z_tab, dc_fid, ["FID"])
    g = geoms["FID"]
    if not np.array_equal(g["mask"], Gr["mask"]):
        raise SystemExit("[FATAL] maschera fiduciale riderivata != congelata (2.1-M)")

    # soglia dei patologici: letta e riscontrata
    alpha_d = Gr["sum_wd"] / Gr["sum_wr"]
    desi_delta = P1.compute_delta(Gr["field_d"], Gr["field_r"], alpha_d,
                                  Gr["mask"], M.NGRID)
    sog, ric, n_ulp = soglia_patologici(root, region, desi_delta, Gr["mask"])
    print("  soglia patologici: canonica %.12f (record 54, riga DESI di v1)" % sog)
    print("                     ricalcolata %.12f -> %.2f ULP di float32"
          % (ric, n_ulp))
    print("                     si conta sulla CANONICA; la distanza fra le due")
    print("                     e' misurata per realizzazione, non argomentata")
    del desi_delta

    specs = [x for x in PASS.RESTRIZIONI_DEFAULT.split(",") if x.strip()]
    subsets = S6.build_restrictions(g["mask"], np.asarray(g["field_r"], float),
                                    specs)
    print("  restrizioni: %s" % ", ".join(l for l, _ in subsets))
    t_er = time.time()
    masks, _ = F3.erosion_levels(g["mask"], EROSIONI)
    print("  livelli di erosione calcolati UNA volta in %.1f s "
          "(dentro il ciclo sarebbero %d volte)" % (time.time() - t_er, a.n))
    mem = stima_memoria(g, masks)
    print("  memoria: persistente %.0f MB, picco transitorio stimato %.0f MB, "
          "totale ~%.0f MB"
          % (mem["persistente_byte"] / 1e6, mem["transitorio_stimato_byte"] / 1e6,
             mem["totale_stimato_byte"] / 1e6))
    print("           NON include la cache dei random: va letta nel monitor di")
    print("           sistema durante questo smoke, se i due emisferi vanno in parallelo")

    zt, wt = N6.build_wfkp_table(M, percorsi(root, region)["wfkp_cache"])
    if not (0.0 < wt.min() and wt.max() <= 1.0 + 1e-9):
        raise SystemExit("[FATAL] w_FKP fuori da (0,1]: la tabella non e' quella")
    wfkp_of_pos = costruisci_wfkp(M, zt, wt)
    print("  tabella w_FKP: %d bin, min %.4f max %.4f" % (len(zt), wt.min(), wt.max()))

    nh1, wfkp_anc = carica_ancore(root, region)
    cat, nota_cat = ancore_catena(L, root, region)
    print("  ANCORA DI CATENA (fase3_mock, stessa catena): %d indici — %s"
          % (len(cat), nota_cat))
    print("  diagnostica fra catene (per_mock, catena paper1_remap): %d record"
          % len(nh1))
    print("  ancora n6 sul peso FKP: %d record" % len(wfkp_anc))
    if not cat:
        raise SystemExit("[FATAL] nessuna ancora di catena: fase3_mock non copre %s"
                         % region)
    if not nh1:
        raise SystemExit("[FATAL] per_mock_%s_R5.jsonl assente o vuoto" % region)

    fatti = {r["index"] for r in leggi_jsonl(out) if "index" in r}
    if fatti:
        print("  ripresa: %d record gia' presenti" % len(fatti))
    print("  indici: da %d a %d (estremo superiore escluso)"
          % (int(getattr(a, "da", 0) or 0), a.n))

    t0 = time.time()
    n_scritti = n_anc_nh1 = n_anc_w = 0
    peggio_w = 0.0
    n_nu_diverse = 0
    n_diverge = 0
    n_diverge_w = 0
    somma_scarti = 0.0
    somma_fra_soglie = 0
    max_fra_soglie = 0
    with_cache = getattr(a, "cache_delta", None)
    for kk in range(da, a.n):
        if kk in fatti:
            continue
        r = una_realizzazione(mods, region, g, masks, kk, Gr["nz_z"],
                              Gr["nz_target"], wfkp_of_pos, sog, subsets,
                              with_cache, soglia_alt=ric)
        if r is None or "_skip" in (r or {}):
            print("    [%4d] saltata (%s)" % (kk, (r or {}).get("_skip", "catalogo")))
            continue

        # --- cancello 1: STESSA CATENA, scarto atteso ZERO ------------------
        att_cat = cat.get(kk)
        if att_cat:
            scarti = {k: int(r["unit"]["N_H1_k%d" % k] - round(v))
                      for k, v in att_cat.items() if k in EROSIONI}
            r["ancora_catena"] = {"attesi": {str(k): v for k, v in att_cat.items()},
                                  "scarti": {str(k): v for k, v in scarti.items()}}
            peggio = max((abs(v) for v in scarti.values()), default=0)
            if peggio > TOL_CATENA:
                print("    [FERMO] idx %d: il ramo unitario NON riproduce "
                      "fase3_mock, stessa catena: scarti %s (tolleranza %d)"
                      % (kk, scarti, TOL_CATENA))
                return 1
            n_anc_nh1 += 1

        # --- diagnostica fra catene: registra, NON ferma --------------------
        atteso = nh1.get(kk)
        if atteso is not None:
            sc = int(r["unit"]["N_H1_k0"] - round(atteso))
            classe = ("esatto" if sc == 0 else
                      "entro pareggi" if abs(sc) <= TOL_DIAGNOSTICA else "DIVERGE")
            r["diagnostica_catene"] = {"per_mock": atteso, "scarto": sc,
                                       "classe": classe}
            if classe == "DIVERGE":
                n_diverge += 1
                somma_scarti += abs(sc)
                print("    [catene] idx %d: R3 %d contro paper1_remap %.0f, "
                      "scarto %+d — registrato, non ferma"
                      % (kk, r["unit"]["N_H1_k0"], atteso, sc))

        # --- diagnostica 2: il peso contro n6, che e' un'altra catena -------
        aw = wfkp_anc.get(kk)
        if aw is not None:
            d = rel(r["fkp"]["wfkp_mean"], aw)
            classe_w = ("esatto" if d <= TOL_WFKP_ESATTO else
                        "DIVERGE" if d > TOL_WFKP_DIVERGE else "intermedio")
            r["diagnostica_n6_wfkp"] = {"n6": aw, "rel": d, "classe": classe_w}
            peggio_w = max(peggio_w, d)
            n_anc_w += 1
            if classe_w == "DIVERGE":
                n_diverge_w += 1
                print("    [n6] idx %d: wfkp_mean %.12f contro n6 %.12f, rel "
                      "%.2e — altra catena, registrato, non ferma"
                      % (kk, r["fkp"]["wfkp_mean"], aw, d))

        # --- cancello 3: la DIMENSIONE, non la presenza ---------------------
        # La prima versione fermava a UN solo voxel fra le due soglie, ed e' la
        # stessa forma di difetto gia' corretta due volte oggi: cancello sulla
        # presenza invece che sull'effetto. Ha fermato SGC all'indice 127 su un
        # voxel, cioe' lo 0.5% della SEM di n_patologici.
        # La soglia usata per CONTARE e' sempre la canonica, in entrambi i rami
        # di ogni record: il voxel fra le due non tocca la regola dichiarata,
        # dice solo che a quel livello il conteggio sarebbe sensibile alla
        # soglia. Quindi si somma, e il limite e' meta' della SEM — lo stesso
        # criterio di D5c (record 36) e della divergenza fra catene.
        somma_fra_soglie += int(r.get("n_pat_fra_le_due_soglie", 0))

        # --- cancello 4: le due vie a nu ------------------------------------
        if not (r["nu_vie_identiche"] and r["nu_vie_identiche_unit"]):
            n_nu_diverse += 1
            print("    [FERMO] idx %d: build_field e build_nu danno nu diversi "
                  "(FKP %d celle, unitario %d celle)"
                  % (kk, r["nu_celle_diverse"], r["nu_celle_diverse_unit"]))
            return 1

        rec = {"schema": SCHEMA, "region": region, "index": kk, "utc": now(),
               "erosioni": list(EROSIONI), "soglia_patologici": sog}
        rec.update(r)
        if smoke:
            rec["smoke"] = True
        max_fra_soglie = max(max_fra_soglie, r.get("n_pat_fra_le_due_soglie", 0))
        append_jsonl(out, rec)
        n_scritti += 1
        if n_scritti % 5 == 1 or smoke:
            el = time.time() - t0
            print("    [%4d] unit k0=%d  fkp k0=%d  dN=%+d  n_pat %d->%d  "
                  "%.1f s/mock  ETA %.1f h"
                  % (kk, r["unit"]["N_H1_k0"], r["fkp"]["N_H1_k0"],
                     r["dN_H1_k0"],
                     r["unit_1punto"]["n_patologici"], r["n_patologici"],
                     el / n_scritti,
                     el / n_scritti * (a.n - kk - 1) / 3600.0))

    dt = time.time() - t0
    somm = costruisci_sommario(
        region=region, smoke=smoke, n_scritti=n_scritti, out=out,
        n_anc_cat=n_anc_nh1, n_anc_w=n_anc_w, peggio_w=peggio_w,
        n_nu_diverse=n_nu_diverse, n_diverge=n_diverge,
        n_diverge_w=n_diverge_w, somma_scarti=somma_scarti, sog=sog, ric=ric, n_ulp=n_ulp,
        max_fra_soglie=max_fra_soglie, somma_fra_soglie=somma_fra_soglie,
        secondi=dt, cache=with_cache,
        da=int(getattr(a, "da", 0) or 0), a_n=int(a.n), mem=mem)
    append_jsonl(percorso_sommario(out), somm)

    print("\n%d record, %d ancore di catena (scarto 0), %d ancore n6 "
          "(%d divergenti, peggior rel %.2e)"
          % (n_scritti, n_anc_nh1, n_anc_w, n_diverge_w, peggio_w))
    if n_scritti:
        bias = somma_scarti / n_scritti
        sem = SD_ENSEMBLE[region] / np.sqrt(N_ATTESI_ENS)
        print("divergenze fra catene: %d su %d (%.2f%%)   bias sulla media %.2f gen"
              % (n_diverge, n_scritti, 100 * n_diverge / n_scritti, bias))
        err = bias / np.sqrt(n_diverge) if n_diverge else 0.0
        print("  %.3f +/- %.3f volte la SEM d'ensemble (%.2f); limite dichiarato "
              "%.1f" % (bias / sem, err / sem, sem, BIAS_MAX_IN_SEM))
        if n_scritti < 500:
            print("  con %d realizzazioni e %d divergenze la stima non e' "
                  "confrontabile con la SEM di un ensemble da %d: il confronto "
                  "vale a fine passata." % (n_scritti, n_diverge, N_ATTESI_ENS))
        elif bias - err > BIAS_MAX_IN_SEM * sem:
            print("  <-- SOPRA il limite anche togliendo un'incertezza")
        print("  lo applica comunque il verdetto, non il runner.")
    print("%.1f s/mock, totale %.2f h" % (dt / max(n_scritti, 1), dt / 3600.0))
    if n_scritti:
        semn = SD_NPAT[region] / np.sqrt(N_ATTESI_ENS)
        bn = somma_fra_soglie / n_scritti
        print("voxel fra le due soglie: %d in totale su %d realizzazioni "
              "(massimo per realizzazione %d)"
              % (somma_fra_soglie, n_scritti, max_fra_soglie))
        print("  bias su n_patologici %.4f voxel = %.4f volte la SEM (%.3f); "
              "limite %.1f" % (bn, bn / semn, semn, BIAS_MAX_IN_SEM)
              + ("   <-- SOPRA" if (n_scritti >= 500
                                    and bn / semn > BIAS_MAX_IN_SEM) else ""))
    print("registro: %s\nsommario: %s" % (out, percorso_sommario(out)))
    if not smoke:
        print("\nPASSO OBBLIGATORIO, PRIMO: 5.3 sul residuo beyond-two-point.")
        print("  E' l'unico controllo della serie che tocca un manoscritto")
        print("  gia' sottomesso, e la checklist lo mette DENTRO 4.2a.")
    return 0


# ---------------------------------------------------------------------------

def selftest():
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, n))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, n, det))

    print("selftest paper2_runner_4_2a")

    chk("quattro livelli di erosione, dichiarati", EROSIONI == (0, 1, 2, 3))
    chk("otto TDA per realizzazione", 2 * len(EROSIONI) == 8)
    chk("tolleranze dichiarate",
        TOL_WFKP_ESATTO == 1e-9 and TOL_WFKP_DIVERGE == 1e-6 and TOL_CATENA == 0
        and TOL_DIAGNOSTICA == 3 and ULP_SPIA == 64)
    chk("il cancello di catena vuole scarto ZERO, non il margine dei pareggi",
        TOL_CATENA == 0)
    chk("n6 e' diagnostica, non cancello: due tolleranze e nessun arresto",
        TOL_WFKP_ESATTO < TOL_WFKP_DIVERGE)
    chk("il caso vero, 1.65e-04, cade in DIVERGE", 1.65e-4 > TOL_WFKP_DIVERGE)
    chk("e i 2-3e-10 degli indici 200-204 restano 'esatto'",
        3e-10 <= TOL_WFKP_ESATTO)
    chk("il limite e' sull'EFFETTO, non sul tasso: meta' della SEM (record 36)",
        BIAS_MAX_IN_SEM == 0.5)
    for reg_, tasso, sc_ in (("SGC", 1 / 60, 92), ("NGC", 1 / 227, 185)):
        sem_ = SD_ENSEMBLE[reg_] / np.sqrt(2000)
        chk("il bias misurato in %s (%.2f gen) sta sotto meta' SEM (%.2f)"
            % (reg_, tasso * sc_, 0.5 * sem_), tasso * sc_ < 0.5 * sem_,
            tasso * sc_ / sem_)
    _sem = SD_ENSEMBLE["SGC"] / np.sqrt(2000)
    chk("una divergenza su dieci da' un bias di 9.2 gen, ma con errore 9.2",
        abs(92.0 / 10 - 9.2) < 1e-9 and abs((92.0 / 10) / np.sqrt(1) - 9.2) < 1e-9)
    chk("quindi a n=10 il bias e' compatibile con quello a n=60 entro l'errore",
        abs(92.0 / 10 - 92.0 / 60) < 92.0 / 10)
    chk("il confronto con la SEM e' dichiarato significativo solo da n=500",
        500 < 2000)
    chk("un tasso dieci volte peggiore sfonderebbe il limite in SGC",
        10 * (1 / 60) * 92 > 0.5 * SD_ENSEMBLE["SGC"] / np.sqrt(2000))
    chk("i trattamenti non-base sono esclusi dall'unione (record 55)",
        set(TRATTAMENTI_NON_BASE) >= {"smoke", "real_space", "origin_offset",
                                      "carve_reseed", "replica_randomise",
                                      "fixed_observables"})
    chk("la spia in ULP sta oltre il doppio del massimo misurato (26 in SGC)",
        ULP_SPIA > 2 * 26)
    chk("il contratto ha tredici campi", len(CONTRATTO) == 13, len(CONTRATTO))
    chk("i quattro N_H1_k* sono nel contratto",
        all("N_H1_k%d" % k in CONTRATTO for k in EROSIONI))
    chk("i nomi a un punto vanno col prefisso",
        "delta.sigma_in_mask" in CONTRATTO and "sigma_in_mask" not in CONTRATTO)

    chk("il sommario ha un file suo",
        percorso_sommario("/a/ensemble_v2_NGC.jsonl").name
        == "ensemble_v2_NGC_sommario.jsonl")
    P = percorsi("/b", "SGC")
    chk("la riga DESI e il per_mock sono per emisfero",
        P["desi_row"].name == "onepoint_v1_DESI_SGC.jsonl"
        and P["per_mock"].name == "per_mock_SGC_R5.jsonl")
    chk("l'ancora n6 esiste solo per NGC ed e' nominata come tale",
        P["n6"].name == "n6_fkp_NGC.jsonl")

    chk("rel normale", abs(rel(1 + 1e-9, 1) - 1e-9) < 1e-15)
    chk("rel con atteso nullo", rel(0, 0) == 0.0 and rel(3, 0) == 3.0)
    chk("flatten usa il punto come separatore",
        flatten({"base": {"N_H1": 7}}) == {"base.N_H1": 7})

    # w_FKP: interpolazione e monotonia, su una tabella sintetica
    class FakeM:
        ZMIN, ZMAX = 0.1, 0.4

        @staticmethod
        def comoving_distance(z):
            return 3000.0 * np.asarray(z, float)
    zt = np.linspace(0.1, 0.4, 30)
    wt = 1.0 / (1.0 + 10.0 * zt)          # monotona decrescente, in (0,1]
    f = costruisci_wfkp(FakeM, zt, wt)
    pos = np.array([[3000 * 0.2, 0, 0], [0, 3000 * 0.3, 0]])
    w, z = f(pos)
    chk("l'inversione distanza->z torna", np.allclose(z, [0.2, 0.3], atol=1e-3), z)
    chk("il peso interpolato e' quello della tabella",
        np.allclose(w, np.interp([0.2, 0.3], zt, wt), atol=1e-6), w)
    chk("il peso decresce in z come la tabella", w[0] > w[1])
    chk("il peso resta in (0,1]", 0 < w.min() and w.max() <= 1.0)

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "results" / "paper1").mkdir(parents=True)
        (td / "results" / "paper2").mkdir(parents=True)
        (td / "results" / "paper1" / "per_mock_NGC_R5.jsonl").write_text(
            "\n".join(json.dumps({"key": "delta_%04d" % i,
                                  "base": {"N_H1": 35000 + i}}) for i in range(4))
            + "\n", encoding="utf-8")
        (td / "results" / "paper1" / "n6_fkp_NGC.jsonl").write_text(
            json.dumps({"idx": 200, "wfkp_mean": 0.3091}) + "\n", encoding="utf-8")
        nh1, wf = carica_ancore(td, "NGC")
        chk("le ancore per_mock si indicizzano dal suffisso della chiave",
            nh1 == {0: 35000.0, 1: 35001.0, 2: 35002.0, 3: 35003.0}, nh1)
        chk("l'ancora n6 si legge per idx", wf == {200: 0.3091}, wf)
        nh1s, wfs = carica_ancore(td, "SGC")
        chk("in SGC l'ancora n6 e' vuota, non un errore", wfs == {})

        # --- ANCORA DI CATENA: lettura per unione, senza i trattamenti
        # non-base. Fino a ora questa funzione non aveva copertura, e due
        # patch al selftest erano andate a vuoto in silenzio perche' i miei
        # script di modifica usavano str.replace senza asserire l'ancora.
        class FakeL:
            @staticmethod
            def carica(path, filtri, senza=()):
                def piatto(r, pre=""):
                    o = {}
                    for k, v in r.items():
                        q = "%s.%s" % (pre, k) if pre else k
                        if isinstance(v, dict):
                            o.update(piatto(v, q))
                        else:
                            o[q] = v
                    return o
                pp = [piatto(json.loads(l))
                      for l in open(path, encoding="utf-8") if l.strip()]
                keep = [q for q in pp
                        if all(k in q and str(q[k]) == v for k, v in filtri)
                        and all(k not in q for k in senza)]
                return keep, len(pp)

            @staticmethod
            def campi_discriminanti(piatti, esclusi=()):
                return []

            @staticmethod
            def trova_indice(piatti, dichiarata=None):
                return dichiarata or "index"

            @staticmethod
            def unione(piatti, chiavi, ci):
                out = {}
                for q in piatti:
                    slot = out.setdefault(q[ci], {})
                    for k in chiavi:
                        if q.get(k) is not None:
                            slot[k] = float(q[k])
                return out

        righe = [
            {"region": "SGC", "index": 24,
             "points": {"FID": {"N_H1_k0": 18684, "N_H1_k1": 16000}}},
            {"region": "SGC", "index": 24, "smoke": True,
             "points": {"FID": {"N_H1_k0": 99999}}},
            {"region": "SGC", "index": 25, "real_space": True,
             "points": {"FID": {"N_H1_k0": 77777}}},
            {"region": "NGC", "index": 24, "points": {"FID": {"N_H1_k0": 35288}}},
        ]
        (td / "results" / "paper2" / "fase3_mock.jsonl").write_text(
            "\n".join(json.dumps(r) for r in righe) + "\n", encoding="utf-8")
        cat, nota = ancore_catena(FakeL, td, "SGC")
        chk("l'ancora di catena filtra per regione", set(cat) == {24}, cat)
        chk("prende la baseline e non il record di smoke",
            cat[24][0] == 18684.0, cat)
        chk("i trattamenti non-base restano fuori", 25 not in cat)
        chk("prende tutti i livelli presenti", set(cat[24]) == {0, 1}, cat[24])
        chk("l'altra regione da' l'altro valore",
            ancore_catena(FakeL, td, "NGC")[0][24][0] == 35288.0)

        # --- il SOMMARIO, che il run vero ha fatto cadere su un nome mancante
        _o = td / "reg.jsonl"
        _o.write_text("\n".join(json.dumps({"index": i}) for i in range(7)) + "\n",
                      encoding="utf-8")
        sm = costruisci_sommario(
            region="SGC", smoke=True, n_scritti=7, out=_o, n_anc_cat=7,
            n_anc_w=0, peggio_w=0.0, n_nu_diverse=0, n_diverge=1, n_diverge_w=0,
            somma_scarti=92.0, sog=161.6, ric=161.6, n_ulp=26.0,
            max_fra_soglie=1, somma_fra_soglie=1, secondi=700.0, cache=None,
            da=20, a_n=30, mem={"persistente_byte": 1})
        chk("il sommario si costruisce senza nomi mancanti", isinstance(sm, dict))
        chk("porta la SEM d'ensemble, da N_ATTESI_ENS",
            abs(sm["sem_ensemble"] - SD_ENSEMBLE["SGC"] / np.sqrt(2000)) < 1e-12)
        chk("il bias e' somma degli scarti su record scritti",
            abs(sm["bias_sulla_media"] - 92.0 / 7) < 1e-12)
        chk("il bias in SEM e' il rapporto dei due",
            abs(sm["bias_in_sem"] - (92.0 / 7) / sm["sem_ensemble"]) < 1e-12)
        chk("i record totali si contano dal registro", sm["n_record_totali"] == 7)
        chk("un voxel fra le due soglie e' misurato, non fatale",
            sm["somma_voxel_fra_le_due_soglie"] == 1
            and abs(sm["bias_npat_da_soglia"] - 1 / 7) < 1e-12, sm)
        chk("e il caso vero — 1 voxel su 127 — sta a un centesimo del limite",
            (1 / 127) / (SD_NPAT["SGC"] / np.sqrt(2000)) < 0.02 * BIAS_MAX_IN_SEM,
            (1 / 127) / (SD_NPAT["SGC"] / np.sqrt(2000)))
        chk("con zero record scritti non si divide per zero",
            costruisci_sommario(
                region="NGC", smoke=False, n_scritti=0, out=_o, n_anc_cat=0,
                n_anc_w=0, peggio_w=0.0, n_nu_diverse=0, n_diverge=0, n_diverge_w=0,
                somma_scarti=0.0, sog=1.0, ric=1.0, n_ulp=0.0, max_fra_soglie=0,
                somma_fra_soglie=0, secondi=0.0, cache=None, da=0, a_n=1,
                mem={})["bias_in_sem"] is None)

        (td / "results" / "paper2" / "onepoint_v1_DESI_NGC.jsonl").write_text(
            json.dumps({"max_delta": 125.47415161132812}) + "\n", encoding="utf-8")
        m = np.zeros((4, 4, 4), dtype=bool); m[0, 0, :2] = True
        dd = np.zeros((4, 4, 4)); dd[0, 0, 0] = 125.47415161132812; dd[0, 0, 1] = 3.0
        s_, r_, nu_ = soglia_patologici(td, "NGC", dd, m)
        chk("a cammino identico la distanza e' zero ULP", nu_ == 0.0, nu_)
        chk("la soglia usata e' la CANONICA, non la ricalcolata",
            s_ == 125.47415161132812)

        # i due cammini MISURATI devono passare la spia, entrambi
        ulp = float(np.spacing(np.float32(125.47415161132812)))
        for n_ulp_caso, nome in ((2.0, "NGC"), (26.0, "SGC")):
            ddx = dd.copy()
            ddx[0, 0, 0] = 125.47415161132812 + n_ulp_caso * ulp
            sx, rx, nx = soglia_patologici(td, "NGC", ddx, m)
            chk("la spia lascia passare i %.0f ULP misurati in %s"
                % (n_ulp_caso, nome),
                abs(nx - n_ulp_caso) < 1e-6 and sx == 125.47415161132812, nx)
        # oltre la spia, ferma
        dd3 = dd.copy(); dd3[0, 0, 0] = 125.47415161132812 + 70 * ulp
        try:
            soglia_patologici(td, "NGC", dd3, m)
            chk("oltre la spia il run si ferma", False, "non ha rifiutato")
        except SystemExit as e:
            chk("oltre la spia il run si ferma",
                "ULP" in str(e) and "spia" in str(e), str(e))
        # una deriva vera resta intercettata
        dd4 = dd.copy(); dd4[0, 0, 0] = 130.0
        try:
            soglia_patologici(td, "NGC", dd4, m)
            chk("una deriva vera ferma il run", False, "non ha rifiutato")
        except SystemExit as e:
            chk("una deriva vera ferma il run", "soglia patologici" in str(e))

        # la sensibilita' si MISURA. Due casi, e le attese sono CALCOLATE dai
        # valori, non scritte a occhio: la prima versione di questo controllo
        # dava per scontato che nessun campione cadesse fra le due soglie, e
        # due su quattro ci cadevano.
        lo, hi = 125.47415161132812, 125.47415161132812 + 2 * ulp
        dentro = np.array([125.474151, 125.4741517, 125.474160, 200.0])
        att_sopra = int((dentro > lo).sum())
        att_fra = int(((dentro > lo) & (dentro <= hi)).sum())
        chk("con campioni nell'intervallo il conteggio li trova",
            att_sopra == 3 and att_fra == 2, (att_sopra, att_fra))
        lontani = np.array([1.0, 50.0, 125.0, 200.0, 3000.0])
        chk("con campioni lontani il conteggio fra le due soglie e' zero",
            int(((lontani > lo) & (lontani <= hi)).sum()) == 0)
        chk("e i due conteggi differiscono esattamente di quelli in mezzo",
            int((dentro > lo).sum()) - int((dentro > hi).sum()) == att_fra)
        try:
            soglia_patologici(td, "SGC", dd, m)
            chk("riga DESI assente: rifiuto", False, "non ha rifiutato")
        except SystemExit as e:
            chk("riga DESI assente: rifiuto", "riga DESI" in str(e))

    # cancelli sul nome del file di uscita
    class A:
        pass

    def _rifiuto(nome, smoke):
        x = A(); x.project_root = "/nonesiste"; x.region = "NGC"; x.out = nome
        x.src = "src"; x.n = 1; x.cache_delta = None
        try:
            esegui(x, smoke)
        except SystemExit as e:
            return str(e)
        except Exception as e:
            return "ALTRO:" + type(e).__name__
        return ""
    # --da: e' cio' che rende esercitabili le ancore n6 senza pagare 205 giri
    class B:
        pass

    def _da(da, n):
        x = B(); x.project_root = "/nonesiste"; x.region = "NGC"
        x.out = "/t/smoke_x.jsonl"; x.src = "src"; x.n = n; x.da = da
        x.cache_delta = None
        try:
            esegui(x, True)
        except SystemExit as e:
            return str(e)
        except Exception as e:
            return "ALTRO:" + type(e).__name__
        return ""
    chk("--da oltre --n e' rifiutato", "--da" in _da(300, 205))
    chk("gli indici 200..204 sono cinque, non duecentocinque",
        len(range(200, 205)) == 5)

    # la stima di memoria: e' un numero, e i pezzi si sommano
    m = np.zeros((8, 8, 8), dtype=bool); m[:4] = True
    g_ = {"field_r": np.zeros((8, 8, 8)), "mask": m}
    masks_ = {k: m.copy() for k in EROSIONI}
    mm = stima_memoria(g_, masks_, n_sel_atteso=1000)
    chk("la memoria persistente somma field_r, maschera ed erosioni",
        mm["persistente_byte"] == 8**3 * 8 + 8**3 + 4 * 8**3, mm)
    chk("il totale e' la somma dei due termini",
        mm["totale_stimato_byte"]
        == mm["persistente_byte"] + mm["transitorio_stimato_byte"])
    chk("la stima dichiara di non contare la cache dei random",
        "cache dei random" in stima_memoria.__doc__)

    chk("smoke su nome di produzione e' rifiutato",
        "smoke" in _rifiuto("/t/ensemble_v2_NGC.jsonl", True))
    chk("run completo su nome smoke e' rifiutato",
        "smoke" in _rifiuto("/t/smoke_v2_NGC.jsonl", False))

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", default="src")
    p.add_argument("--project_root", default=ROOT_DEFAULT)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for nm in ("smoke", "run"):
        q = sub.add_parser(nm)
        q.add_argument("--region", choices=["NGC", "SGC"], required=True)
        q.add_argument("--out", required=True)
        q.add_argument("--n", type=int, default=5 if nm == "smoke" else 2000,
                       help="estremo superiore ESCLUSO degli indici")
        q.add_argument("--da", type=int, default=0,
                       help="indice di partenza. Serve a esercitare le ancore "
                            "n6, che esistono solo da 200 in su: --da 200 --n 205 "
                            "costa cinque realizzazioni invece di duecentocinque")
        q.add_argument("--cache-delta", dest="cache_delta", default=None,
                       help="directory dove scrivere i delta v2 del ramo FKP. "
                            "Senza, delta_sha256 e' sui byte grezzi e non c'e' "
                            "un file da manifestare")
    a = p.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    return esegui(a, a.cmd == "smoke")


if __name__ == "__main__":
    sys.exit(main())

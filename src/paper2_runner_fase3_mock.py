#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY / Paper 2 - Fase 3, lato mock appaiato: cancello D4 e item 3.2.

COSA MISURA
  Per ogni realizzazione e ogni punto della griglia AP, N_H1 del mock nella
  geometria di quel punto. Il deficit D = <N_H1(mock)> - N_H1(DESI) si valuta
  punto per punto, ed e' dD/dfiducia la quantita' del 3.4: l'AP agisce su
  ENTRAMBI i lati, quindi una risposta comune si cancella in D. Il lato dati da
  solo (item 3.1) non dice nulla su questo.

TRE COSE CHE IL CODICE ESISTENTE IMPONE, E CHE NON SONO OVVIE
--------------------------------------------------------------
1. L'HOD e' `T2.populate_with_virial` di phase8_test2_masked, NON
   `M.populate_halos_hod_with_vel`. Le due coesistono; i mock congelati di v1
   vengono dalla prima, ed e' quella che il cancello 2.5 ha riprodotto bit a
   bit. Usare l'altra darebbe mock plausibili e sbagliati, senza errore.

2. `rng` e' SEQUENZIALE e condiviso: carve_cutsky consuma lo stato lasciato
   dall'HOD. Riusando l'HOD su dieci punti — cosa legittima, perche' il 2.5 ha
   misurato che `rng_state_after_hod` non dipende dalla regione — ogni carving
   deve RIPARTIRE DALLO STESSO STATO. Senza il ripristino, i punti
   differirebbero anche per estrazioni diverse, cioe' proprio il termine (c)
   del 3.3 che si vuole isolare. Qui lo stato si fotografa dopo l'HOD e si
   ripristina prima di ogni carving.

3. `N_TARGET_BGS` e' una globale MUTATA da altri moduli: vale 217614 nel modulo
   (phase8:134) ma paper1_remap.py:238 la riassegna a n_data e
   phase9_sgc_likeforlike.py:142 a 82429. Il carving campiona verso quel
   bersaglio, quindi va asserita a ogni cambio di emisfero. Nessun errore se
   sbagliata: solo mock con la densita' sbagliata.

IL CANCELLO D4, PRIMA DI QUALUNQUE PUNTO DEFORMATO
---------------------------------------------------
  D4a  RIFORMULATO il 29 ago, dopo misura. La formulazione precedente chiedeva
       che il delta fosse BIT-IDENTICO ai congelati di v1. E' irraggiungibile
       per costruzione, e non per un difetto: set_geometry(dc_tab=...) sostituisce
       comoving_distance con un'interpolazione lineare, che sposta le posizioni
       e quindi anche field_r, cioe' il DENOMINATORE di delta. Misurato su
       quattro risoluzioni della tabella (4001, 10001, 40001, 100001 nodi):
         - il lato del cubo converge come N^-2, da 2.86e-9 a 4.68e-12 relativo;
         - il delta NON converge: le celle diverse vanno da 243010 a 183752 e
           saturano, perche' field_r si ribalta nell'ultimo bit di float32;
         - N_H1 e' IDENTICO a tutte le risoluzioni, 28256 sul lato dati e 35318
           sul mock 0. Lo scarto assoluto su delta vale 4.88e-4 su un campo che
           va da -1 a +150, e sopra passa uno smoothing con sigma_px = 0.32.
       Il cancello si spacca quindi in due, e nessuno dei due e' piu' debole:
         D4a-det   DETERMINISMO: lo stesso mock calcolato due volte nello stesso
                   percorso deve dare un delta bit-identico. Se fallisce, c'e'
                   uno stato non controllato, ed e' un difetto vero.
         D4a-stab  STABILITA' contro v1: |delta - v1| <= TOL_DELTA_ABS in valore
                   ASSOLUTO. Il rapporto relativo NON si usa: delta passa per
                   zero e il rapporto esplode su celle irrilevanti (la cella di
                   max_rel ha delta = -2.19e-6, cioe' rumore diviso rumore).
  D4b  generatori: e' il cancello che conta, perche' e' l'osservabile.
       N_H1 al fiduciale deve riprodurre i valori congelati di
       results/paper1/per_mock_{region}_erosion_restrict.jsonl, celle
       R5_er0 e R5_er1, MOCK PER MOCK. Un confronto di medie passerebbe anche
       con due sottoinsiemi diversi che si compensano.
  D4c  sanita', non predizione: ai punti deformati il delta N_H1 contro il
       proprio fiduciale appaiato deve stare nell'ordine di grandezza del lato
       dati (decine). Centinaia significherebbero che il carving risponde alla
       geometria in un modo che il lato dati non mostra.

POPOLAZIONE DI RIFERIMENTO
  Il baseline appaiato e' il sottoinsieme n = 200: media 35423.575 (NGC) e
  18693.595 (SGC). NON l'ensemble n = 2000 (35436.686 / 18712.9675), che e'
  quello del cancello 2.1-E. Il reference lo dice in chiaro per SGC:
  "do not average with SGC_n2000".

Uso:
    python src\\paper2_runner_fase3_mock.py selftest
    python src\\paper2_runner_fase3_mock.py smoke --region NGC
    python src\\paper2_runner_fase3_mock.py run --region NGC --n 200
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

GAUGE_VERSION = "amend13"
PAD_FID = 5.0
# k=1 primario, k=0 per l'aggancio a v1. I livelli 2 e 3 sono DIAGNOSTICI e
# costano due chiamate TDA in piu' per punto-mock (~14 s), cioe' ~21 ore sui
# dodici punti e due emisferi: si chiedono esplicitamente con --erosions.
# Servono a separare BORDO da VOLUME, che e' l'unico asse rimasto ortogonale
# agli scalari geometrici gia' provati e tutti falliti.
EROSIONS_MOCK = (0, 1)

# --- D5c, modalita' -----------------------------------------------------------
# "block"   : arresto duro a n_clipped > 0. E' la forma dell'emendamento 17 ed e'
#             quella che vale per i run che producono risultati.
# "measure" : misura e registra senza fermare. DIAGNOSTICA, 1 set 2026, aperta
#             perche' D5c ha sparato al punto FIDUCIALE (2 posizioni, faccia +y,
#             eccesso 2.046 Mpc/h) e serve sapere se n_clipped cresce con |F-1|
#             o e' una costante del fiduciale. In "measure" il conteggio finisce
#             comunque nel record: il dato non dipende dalla modalita'.
#
# QUESTA E' UNA DEROGA TEMPORANEA a un cancello che ha gia' sparato. Va
# riportata a "block" prima di qualunque run che produca risultati, e il codice
# lo stampa a ogni esecuzione invece di affidarsi alla memoria.
D5C_MODE = "block"

# SOGLIA DI D5c, record 36. Derivata dall'EFFETTO, non dai quantili.
#
# Il cancello 2.2a misura 216 voxel di maschera = 34 generatori, cioe' 0.1574
# generatori per voxel. La SEM piu' piccola di DDmax vale 8.7 (SGC k=1). Il
# numero di voxel il cui effetto raggiunge META' di quella SEM e'
#     0.5 * 8.7 / 0.1574 = 27.6  ->  28
#
# Perche' META' e non un quarto o la SEM intera. In quadratura un termine
# accanto a uno dominante aggiunge +3.1% a un quarto, +5.4% a un terzo, +11.8%
# a meta', +41.4% alla parita': meta' e' dove "trascurabile" smette di essere
# difendibile. E dall'altro lato: il massimo osservato su 4800 misure e' 9, e
# la distribuzione e' fortemente sovra-dispersa (sotto Poisson(0.703) un 9 ha
# probabilita' 6e-08), quindi una soglia a un quarto - 13.8, solo 1.5x il
# massimo - sparerebbe sulla crescita ordinaria della coda. Meta' da' 3.1x.
# L'unita' e' scartata dal lato opposto: a 55 voxel il clipping contribuirebbe
# quanto l'errore campionario e dovrebbe entrare nel budget come termine.
#
# NON e' un quantile: la distribuzione dice che il clipping attuale e'
# trascurabile, non dove mettere il cancello.
D5C_SOGLIA = 28
# PREDIZIONE SMENTITA, 29 ago, registrata e non riparata.
#   "|delta - v1| <= 1e-3 in assoluto" -> osservato 2.93e-3, 2.20e-3, 1.46e-3.
# La soglia era calibrata sul 4.88e-4 misurato a 100001 nodi, mentre il percorso
# di produzione gira a 4001, dove la perturbazione e' 3-6 volte piu' grande:
# soglia presa in una configurazione e applicata in un'altra, stessa classe di
# errore del cancello 2.2a. E comunque 1e-3 era un numero inventato.
#
# Il criterio corretto e' DERIVABILE e non si sceglie: la filtrazione ha
# N_THRESH livelli sull'escursione di nu, quindi il passo vale
#   spacing = (nu_max - nu_min) / N_THRESH
# e una perturbazione sotto il passo non puo' spostare un generatore attraverso
# un livello, salvo sui pareggi — che e' esattamente cio' che D4b misura in
# modo diretto. Il confronto si fa su NU, non su delta, perche' e' nu che entra
# nella filtrazione, e dopo lo smoothing con sigma_px.
D4A_MAX_LEVELS = 1.0           # max|dnu| deve stare sotto UN passo di livello
SEED = 42
SNAPNUM = 3
LOG_DEFAULT = "results/paper2/fase3_mock.jsonl"

N_TARGET = {"NGC": 217614, "SGC": 82429}
SIGMA_FID = {"NGC": 0.32042249039652254, "SGC": 0.33605500065144590}
L_FID = {"NGC": 1997.3629110094512, "SGC": 1904.450156441475}
VOX_FID = {"NGC": 307805, "SGC": 172225}

# Baseline appaiato n = 200 (results/paper1/per_mock_*_erosion_restrict.jsonl,
# celle FUSE per chiave: 600 righe per 200 mock in NGC, last-wins perderebbe
# meta' delle celle).
BASELINE_N200 = {"NGC": {"0": 35423.575, "1": 31889.930},
                 "SGC": {"0": 18693.595, "1": 16477.565}}


def now():
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path, rec):
    import os
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def load_frozen_mock_cells(root, region):
    """Celle FUSE per chiave. Il registro e' append-only e ci sono passate con
    insiemi di celle diversi: `read_jsonl` last-wins ne perderebbe una parte."""
    import collections
    p = Path(root) / "results" / "paper1" / f"per_mock_{region}_erosion_restrict.jsonl"
    merged = collections.defaultdict(dict)
    if not p.exists():
        return merged
    for l in p.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            merged[r["key"]].update(r.get("cells", {}))
    return merged


# --------------------------------------------------------------------------

def attach(srcdir="src"):
    if srcdir and srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    import phase8_cutsky_mocks as M
    import paper1_remap as P1
    import phase8_test2_masked as T2
    import paper2_data_geometry as GEO
    import paper2_phase3_preflight as PF
    import paper2_item13a_15a as I13
    import paper2_runner_fase3 as F3
    z = np.asarray(M._Z_TAB, float).copy()
    dc = np.asarray(M._DC_TAB, float).copy()
    return M, P1, T2, GEO, PF, I13, F3, z, dc


def build_geometries(M, GEO, PF, I13, F3, region, cache_r, z_tab, dc_fid,
                     points=None, verbose=True, origin_offset=None):
    """Geometria, campo dei random e maschera per ogni punto, UNA volta.

    Precalcolare qui costa ~200 MB e toglie il ricalcolo da dentro il ciclo
    sulle realizzazioni, dove verrebbe rifatto duecento volte identico.
    """
    out = {}
    plan = F3.point_plan(I13, points)
    for name, spec, block in plan:
        dc_pt = I13.deform(z_tab, dc_fid, spec)
        if name == "FID":
            c, dc_use, pad = 1.0, dc_pt, PAD_FID
        else:
            M.set_geometry(z_tab=z_tab, dc_tab=dc_pt, verbose=False)
            pos_r, _ = cache_r.positions()
            _, L_nat = _box(GEO, pos_r, PAD_FID)
            c = L_FID[region] / L_nat
            dc_use, pad = dc_pt * c, PAD_FID * c
            del pos_r
        M.set_geometry(z_tab=z_tab, dc_tab=dc_use, verbose=False)
        pos_r, w_r = cache_r.positions()
        box_min, box_size = _box(GEO, pos_r, pad)
        # §C del secondo report: l'origine dell'embedding e' una SCELTA,
        # e traslarla cambia la FASE della griglia rispetto al reticolo
        # del box periodico -- quindi quanto ripattern c'e' -- lasciando
        # invariato lo spostamento RELATIVO fra i punti. box_size NON si
        # tocca: cell, R_SMOOTH e il cancello su sigma_px restano dove
        # sono, o l'offset misurerebbe due cose insieme.
        # Il ramo spento e' un no-op PER COSTRUZIONE: se e' None non si
        # esegue nulla, non si somma zero.
        if origin_offset is not None:
            box_min = box_min + float(origin_offset)
        cell = box_size / M.NGRID
        M.R_SMOOTH = SIGMA_FID[region] * cell
        M.set_geometry(box_min=box_min, box_size=box_size, verbose=False)
        e = abs(float(M.SIGMA_PX) - SIGMA_FID[region]) / SIGMA_FID[region]
        if e > 1e-12:
            sys.exit(f"[FATAL] sigma_px non bloccato su {name}: rel {e:.2e}")
        cl = PF.clipped_per_face(pos_r, box_min, box_size)
        if cl["n_clipped"]:
            sys.exit(f"[FATAL] {cl['n_clipped']} random fuori dal cubo su {name}.")
        field_r = M.cic_3d(pos_r, w_r, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
        sum_wr = float(w_r.sum())
        mask = field_r > 0.01 * float(field_r.mean())
        del pos_r
        out[name] = {"spec": spec, "block": block, "c": c, "pad": pad,
                     "dc_tab": dc_use, "box_min": box_min, "box_size": box_size,
                     "cell": cell, "sigma_px": float(M.SIGMA_PX),
                     "R_SMOOTH": float(M.R_SMOOTH), "field_r": field_r,
                     "sum_wr": sum_wr, "mask": mask,
                     "n_valid_voxels": int(mask.sum())}
        if verbose:
            print(f"  [geom] {name:<4} L={box_size:12.6f} voxel={int(mask.sum()):7d} "
                  f"c={c:.8f}")
    if "FID" in out and out["FID"]["n_valid_voxels"] != VOX_FID[region]:
        sys.exit(f"[FATAL] maschera fiduciale riderivata: "
                 f"{out['FID']['n_valid_voxels']} voxel, attesi {VOX_FID[region]}.")
    return out


def _box(GEO, pos_r, pad):
    o = GEO.derive_box(pos_r, pad=pad)
    bmin, L = (o[0], float(o[1])) if isinstance(o, tuple) else (o, None)
    return np.asarray(bmin, float), L


def one_mock(M, P1, T2, F3, region, geoms, kk, nz_z, nz_target, order,
             frozen_delta_dir=None, carve_reseed=None,
             erosions=EROSIONS_MOCK, fixed_observables=False,
             replica_randomise=False, rot_seed=None):
    """Una realizzazione su tutti i punti richiesti, con semi appaiati.

    L'HOD si calcola UNA volta (non dipende da regione ne' geometria: misurato
    dal cancello 2.5, `rng_state_after_hod` identico fra NGC e SGC). Lo stato
    dell'rng si fotografa subito dopo e si RIPRISTINA prima di ogni carving.
    """
    t0 = time.time()
    rng = np.random.default_rng(SEED + kk)
    pos_h, mass_h, vel_h = M.read_halo_catalog(kk, SNAPNUM)
    if pos_h is None or len(pos_h) < 50:
        return None
    pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h,
                                               M.HOD_MEDIAN, rng)
    state_after_hod = rng.bit_generator.state
    # --- item 3.2d / referee 4.6: repliche randomizzate ----------------
    # Generatore SEPARATO. Non deve consumare un solo valore da `rng`,
    # altrimenti l'appaiamento dei semi con i run gia' depositati salta.
    if replica_randomise and rot_seed is None:
        sys.exit('[FATAL] replica_randomise senza rot_seed: il run non sarebbe riproducibile dal suo seme.')
    rot_rng = (np.random.default_rng(int(rot_seed) + kk)
               if replica_randomise else None)
    rot_state = rot_rng.bit_generator.state if rot_rng is not None else None
    # -------------------------------------------------------------------
    if carve_reseed is not None:
        # TERMINE (c) del 3.3: ri-randomizzazione del carving a GEOMETRIA FERMA.
        # L'HOD resta identico — stesse galassie, stessi aloni, stesso seme — e
        # cambia solo lo stato da cui parte il carving. La differenza appaiata
        # contro il run principale isola quindi la sola ri-selezione, senza
        # nessuna componente geometrica: e' la definizione del termine (c).
        state_after_hod = np.random.default_rng(
            carve_reseed + kk).bit_generator.state
    del pos_h, mass_h, vel_h

    # --- TRATTAMENTO (B): la cache al fiduciale, e il cancello D5a -----------
    # (rhat, z_obs) si prendono UNA VOLTA al fiduciale, dopo il Pass 2. Per ogni
    # punto si ricalcola poi solo r' = rhat * D_C^(g)(z_obs): la selezione resta
    # quella del fiduciale, che e' cio' che rende (B) il gemello del lato dati.
    _fixed = None
    if fixed_observables:
        gF = geoms["FID"]
        M.set_geometry(z_tab=None, dc_tab=gF["dc_tab"], verbose=False)
        M.R_SMOOTH = gF["R_SMOOTH"]
        M.set_geometry(box_min=gF["box_min"], box_size=gF["box_size"], verbose=False)
        M.N_TARGET_BGS = N_TARGET[region]
        rng.bit_generator.state = state_after_hod
        _cap = {}
        _pos_fid = M.carve_cutsky(pos_gal, vel_gal, gF["mask"], nz_z, nz_target,
                                  rng, capture=_cap)
        if _pos_fid is None or len(_pos_fid) < 100:
            return None
        # CANCELLO D5a, tolleranza ZERO (record 16). Attenzione a cosa verifica:
        # il confronto e' NELLO STESSO PROCESSO, fra l'uscita del percorso
        # normale e la ricostruzione dalla cache. E' un cancello sulla
        # COSTRUZIONE DELLA CACHE, non sul run. Fallisce se rhat o z_obs sono
        # presi nel punto sbagliato del Pass 2, troncati, o riordinati.
        _dc = np.interp(np.clip(_cap["z_obs"], 0.0, 0.6), M._Z_TAB, M._DC_TAB)
        _ric = _cap["rhat"] * _dc[:, None]
        if _ric.shape != _pos_fid.shape or not np.array_equal(_ric, _pos_fid):
            _n = (int((_ric != _pos_fid).sum())
                  if _ric.shape == _pos_fid.shape else -1)
            sys.exit(f"[FATAL] D5a: {region}/mock {kk}: la ricostruzione dalla "
                     f"cache NON e' bit-identica al carving al fiduciale "
                     f"(elementi diversi: {_n}, forme {_ric.shape} contro "
                     f"{_pos_fid.shape}). Tolleranza zero, record 16.")
        _fixed = _cap

    res = {}
    for name in order:
        g = geoms[name]
        M.set_geometry(z_tab=None, dc_tab=g["dc_tab"], verbose=False)
        M.R_SMOOTH = g["R_SMOOTH"]
        M.set_geometry(box_min=g["box_min"], box_size=g["box_size"], verbose=False)
        M.N_TARGET_BGS = N_TARGET[region]          # globale mutata altrove
        rng.bit_generator.state = state_after_hod  # APPAIAMENTO: stesso stato
        if rot_rng is not None:
            # LE STESSE permutazioni a OGNI punto. Con permutazioni diverse
            # fra B1 e B5 il campo verrebbe rimescolato fra i due punti e
            # Delta D misurerebbe QUEL rimescolamento invece della
            # deformazione. Cosi' la randomizzazione e' una rietichettatura
            # COMUNE ai punti: toglie la coerenza fra repliche, che e' cio'
            # che il ripattern muoverebbe, e lascia appaiato il resto.
            rot_rng.bit_generator.state = rot_state
        if _fixed is None:
            pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z,
                                     nz_target, rng,
                                     randomise_replicas=replica_randomise,
                                     rot_rng=rot_rng)
        else:
            # (B): si rimappa e basta. Nessun ricampionamento n(z), nessun
            # ri-seed, nessuna ricostruzione della selezione o dei tagli in z.
            # n_sel sara' identico a ogni punto: e' atteso, ed e' il controllo
            # piu' semplice che la modalita' stia facendo quel che dice.
            _dcp = np.interp(np.clip(_fixed["z_obs"], 0.0, 0.6),
                             M._Z_TAB, M._DC_TAB)
            pos_sel = _fixed["rhat"] * _dcp[:, None]
        # CANCELLO D5c (emendamento 17): zero clippati sul lato mock, arresto
        # duro, in ENTRAMBI i trattamenti. Il lato dati vieta gia' i fuori-cubo
        # (paper2_runner_fase3.py:277-282 e 296-301, emendamento 13 punto (c));
        # il lato mock non lo ha mai fatto, e phase8:688 li IMPILA sul voxel di
        # bordo invece di scartarli. Sotto deformazione le galassie si spostano
        # radialmente e qualcuna esce: senza questo, l'impilamento verrebbe
        # contato come segnale. Un punto che fallisce non si misura, e si
        # riporta CON i conteggi per faccia: e' un dato, non un buco.
        # PF non e' fra i parametri di one_mock: si importa qui. attach() ha gia'
        # messo src sul sys.path e il modulo e' gia' in sys.modules, quindi
        # questo e' una lettura di dizionario, non un caricamento.
        import paper2_phase3_preflight as PF
        _cl = None
        if pos_sel is not None and len(pos_sel) >= 100:
            _cl = PF.clipped_per_face(pos_sel, M.BOX_MIN, M.BOX_SIZE)
            if _cl["n_clipped"] >= D5C_SOGLIA and D5C_MODE == "block":
                sys.exit(f"[FATAL] D5c: {region}/{name}/mock {kk}: "
                         f"{_cl['n_clipped']} posizioni fuori dal cubo, soglia "
                         f"{D5C_SOGLIA} (record 36). A questo conteggio "
                         f"l'impilamento vale ~{_cl['n_clipped'] * 0.1574:.1f} "
                         f"generatori, cioe' meta' della SEM piu' piccola: "
                         f"non e' piu' distinguibile dal rumore campionario. "
                         f"Dettaglio: {_cl}.")
            if _cl["n_clipped"] and D5C_MODE == "measure":
                print(f"    [D5c misura] {name}/mock {kk}: "
                      f"n_clipped = {_cl['n_clipped']}")
        if pos_sel is None or len(pos_sel) < 100:
            res[name] = {"skipped": "carve vuoto"}
            continue
        w_d = np.ones(len(pos_sel))
        field_d = M.cic_3d(pos_sel, w_d, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
        alpha = float(w_d.sum()) / g["sum_wr"]
        delta = P1.compute_delta(field_d, g["field_r"], alpha, g["mask"], M.NGRID)
        mine = delta.astype(np.float32)

        row = {"n_sel": int(len(pos_sel)), "alpha": alpha}
        # D5c: il conteggio si registra SEMPRE, in entrambe le modalita'. Che il
        # cancello fermi o no, il dato non deve dipendere da quella scelta.
        if _cl is not None:
            row["d5c_n_clipped"] = int(_cl["n_clipped"])
            row["d5c_per_face"] = {k: v for k, v in _cl.items() if k != "n_clipped"}
        if name == "FID" and frozen_delta_dir is not None:
            f = Path(frozen_delta_dir) / ("delta_%04d.npy" % kk)
            if f.exists():
                fz = np.asarray(np.load(f, mmap_mode="r"))
                row["D4a_identical"] = bool(np.array_equal(mine, fz))
                d = np.abs(mine.astype(np.float64) - fz.astype(np.float64))
                nz = fz != 0
                row["D4a_max_abs_diff"] = float(d.max())
                row["D4a_max_rel_diff"] = float(
                    (d[nz] / np.abs(fz[nz].astype(np.float64))).max()) if nz.any() else 0.0
                row["D4a_n_cells_differing"] = int((d > 0).sum())
                # Un ULP di float32 vale 2^-23 = 1.19e-7 relativo: se lo scarto
                # sta li', le due versioni sono lo stesso numero arrotondato in
                # modo diverso, non due risultati.
                row["D4a_within_1ulp_f32"] = bool(row["D4a_max_rel_diff"] < 2.4e-7)
                # D4a-stab: sulla quantita' che entra nella filtrazione, e in
                # unita' del passo di livello. Nessun numero scelto a mano.
                nu_mine = P1.build_nu(mine.astype(np.float64), g["mask"],
                                      g["sigma_px"])
                nu_fz = P1.build_nu(fz.astype(np.float64), g["mask"],
                                    g["sigma_px"])
                inm = g["mask"]
                dnu = float(np.abs(nu_mine[inm] - nu_fz[inm]).max())
                span = float(nu_fz[inm].max() - nu_fz[inm].min())
                spacing = span / M.N_THRESH
                row["D4a_max_dnu"] = dnu
                row["D4a_nu_span"] = span
                row["D4a_level_spacing"] = spacing
                row["D4a_dnu_in_levels"] = dnu / spacing if spacing else float("inf")
                row["D4a_stab_ok"] = bool(row["D4a_dnu_in_levels"] < D4A_MAX_LEVELS)
                del fz, d, nz, nu_mine, nu_fz

        nu = M.build_field(field_d, g["field_r"], alpha, g["mask"])
        masks, _ = F3.erosion_levels(g["mask"], erosions)
        for k in erosions:
            feats = M.compute_tda_features(nu, masks[k], M.N_THRESH, masked=True)
            row[f"N_H1_k{k}"] = int(round(float(feats[4])))
            row[f"b1_peak_k{k}"] = float(feats[1])
        res[name] = row
        del field_d, nu, delta, mine, pos_sel
    res["_erosions"] = tuple(erosions)
    res["_seconds"] = time.time() - t0
    res["_state_after_hod"] = str(state_after_hod["state"]["state"])[:16]
    res["_n_gal"] = int(len(pos_gal))
    return res


# --------------------------------------------------------------------------

def _prepare(a, points):
    M, P1, T2, GEO, PF, I13, F3, z_tab, dc_fid = attach(a.src)
    root = Path(a.project_root).resolve()
    reg = a.region
    desi_dir = root / "data" / "raw" / "desi_dr1"
    fld_dir = root / "data" / "processed" / "phase6_fields"
    M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
    Gr = P1.setup_region(M, reg, desi_dir, fld_dir)
    if int(M.N_TARGET_BGS) != N_TARGET[reg]:
        sys.exit(f"[FATAL] N_TARGET_BGS = {M.N_TARGET_BGS}, atteso {N_TARGET[reg]}.")
    cache_r = PF.Cache(GEO, M, reg, "ran")
    if not a.no_cache_gate:
        if not PF.cache_gate(GEO, cache_r)["ok"]:
            sys.exit("[FATAL] cache non bit-identica a positions().")
    _off = getattr(a, "origin_offset", None)
    if _off is not None and not bool(getattr(a, "skip_fid", False)):
        sys.exit("[FATAL] --origin-offset richiede --skip-fid. Con "
                 "l'origine spostata la maschera fiduciale riderivata "
                 "non coincide piu' con la congelata, e il 2.1-M "
                 "scatterebbe: giustamente. Non lo si spegne, si toglie "
                 "il fiduciale dal piano. Applicare l'offset a tutti i "
                 "punti TRANNE FID metterebbe FID e i punti B su "
                 "griglie diverse, e Delta D misurerebbe quella "
                 "differenza.")
    geoms = build_geometries(M, GEO, PF, I13, F3, reg, cache_r, z_tab, dc_fid,
                             points, origin_offset=_off)
    # La maschera fiduciale RIDERIVATA deve coincidere con la congelata: e' il
    # 2.1-M, ed e' la precondizione perche' D4a possa restare bit-identico.
    if "FID" in geoms and not np.array_equal(geoms["FID"]["mask"], Gr["mask"]):
        sys.exit("[FATAL] maschera fiduciale riderivata != congelata (2.1-M).")
    cache_dir = root / "data" / "processed" / "paper1_mock_deltas" / reg
    return (M, P1, T2, F3, root, reg, geoms, Gr, cache_dir,
            load_frozen_mock_cells(root, reg))


def cmd_smoke(a):
    _avviso_d5c()
    pts = a.points or ["FID", "B1", "B5"]
    (M, P1, T2, F3, root, reg, geoms, Gr, cache_dir, frozen) = _prepare(a, pts)
    _accendi_real_space(M, a)
    idx = list(range(a.n))
    print("=" * 74)
    print(f"D4 — smoke test, {reg}, {len(idx)} realizzazioni, punti {pts}")
    print("=" * 74)
    print("  D4a-det   lo stesso mock due volte -> delta bit-identico")
    print(f"  D4a-stab  max|dnu| < {D4A_MAX_LEVELS:g} passi di livello della "
          "filtrazione (criterio derivato, non scelto)")
    print("  D4b  N_H1 identico ai congelati R5_er0 / R5_er1, MOCK PER MOCK")
    print("  D4c  sanita': delta ai punti deformati dell'ordine delle decine\n")
    fails, rows = [], []

    # D4a-det, una volta: se il percorso non e' deterministico, tutto il resto
    # non e' interpretabile. Costa un mock ripetuto.
    r_a = one_mock(M, P1, T2, F3, reg, geoms, idx[0], Gr["nz_z"], Gr["nz_target"],
                   ["FID"], frozen_delta_dir=None)
    r_b = one_mock(M, P1, T2, F3, reg, geoms, idx[0], Gr["nz_z"], Gr["nz_target"],
                   ["FID"], frozen_delta_dir=None)
    det = (r_a is not None and r_b is not None
           and r_a["FID"]["N_H1_k0"] == r_b["FID"]["N_H1_k0"]
           and r_a["FID"]["N_H1_k1"] == r_b["FID"]["N_H1_k1"]
           and r_a["FID"]["n_sel"] == r_b["FID"]["n_sel"])
    print(f"  D4a-det: due esecuzioni identiche -> {'ok' if det else 'NO'}")
    if not det:
        fails.append("D4a-det: il percorso non e' deterministico")

    for kk in idx:
        r = one_mock(M, P1, T2, F3, reg, geoms, kk, Gr["nz_z"], Gr["nz_target"],
                     pts, frozen_delta_dir=cache_dir)
        if r is None:
            print(f"  [{kk:4d}] catalogo assente, salto")
            continue
        key = "delta_%04d" % kk
        fid = r["FID"]
        exp = frozen.get(key, {})
        e0 = exp.get("R5_er0", {}).get("N_H1")
        e1 = exp.get("R5_er1", {}).get("N_H1")
        ok_a = fid.get("D4a_stab_ok")          # D4a-stab, non piu' bit-identita'
        # Tolleranza sui pareggi: il reference dichiara tied_groups = 4272 e
        # tie_breaking_shift_generators = 3. Uno scarto di 1-3 generatori su
        # ~35000 non e' un percorso diverso, e' l'ordinamento di valori uguali.
        db = [abs(int(e0) - fid["N_H1_k0"]) if e0 is not None else 999,
              abs(int(e1) - fid["N_H1_k1"]) if e1 is not None else 999]
        ok_b = max(db) <= 3
        exact_b = max(db) == 0
        if not ok_a:
            fails.append(
                f"D4a-stab su {key}: max|dnu| = "
                f"{fid.get('D4a_max_dnu', float('nan')):.3e} = "
                f"{fid.get('D4a_dnu_in_levels', float('nan')):.3f} passi di livello "
                f"(passo {fid.get('D4a_level_spacing', float('nan')):.3e}), "
                f"limite {D4A_MAX_LEVELS:g}")
        if not ok_b:
            fails.append(f"D4b su {key}: k0 {fid['N_H1_k0']} vs {e0}, "
                         f"k1 {fid['N_H1_k1']} vs {e1} (scarti {db}, "
                         f"tolleranza pareggi 3)")
        print(f"  [{kk:4d}] n_sel={fid['n_sel']:7d}  k0={fid['N_H1_k0']:7d} "
              f"(atteso {e0})  k1={fid['N_H1_k1']:7d} (atteso {e1})  "
              f"D4b={'esatto' if exact_b else f'scarti {db}'}  "
              f"D4a-stab={'ok' if ok_a else 'NO'} "
              f"(dnu={fid.get('D4a_dnu_in_levels', float('nan')):.4f} livelli)"
              f"  [{r['_seconds']:.0f}s]")
        for p in pts:
            if p == "FID" or "N_H1_k1" not in r.get(p, {}):
                continue
            d0 = r[p]["N_H1_k0"] - fid["N_H1_k0"]
            d1 = r[p]["N_H1_k1"] - fid["N_H1_k1"]
            # La soglia e' sigma_Delta = 250.5, la dispersione PER
            # REALIZZAZIONE gia' pre-registrata, non un numero tondo. Il
            # carving appaiato non elimina il rumore: cambiando la maschera
            # cambia la selezione (~150 galassie su 218k fra un punto e
            # l'altro), quindi il Delta per singolo mock scatta di ~sigma_Delta
            # per costruzione. Solo la MEDIA su N=200 scende a 250.5/sqrt(200)
            # = 17.7, sotto la soglia di rilevabilita' di 53.
            flag = ("" if max(abs(d0), abs(d1)) < 3 * 250.5
                    else "   <-- oltre 3 sigma_Delta su UN mock")
            print(f"         {p}: dN k0={d0:+6d}  k1={d1:+6d}  "
                  f"n_sel={r[p]['n_sel']:7d}{flag}")
        rec = {"schema": "paper2_fase3_mock_v1", "region": reg, "index": kk,
               "gauge_version": GAUGE_VERSION, "utc": now(), "smoke": True,
               "points": {p: r[p] for p in pts if p in r},
               "seconds": r["_seconds"], "n_gal": r["_n_gal"]}
        rows.append(rec)
        if a.out:
            append_jsonl(a.out, rec)
    print(f"\n  {'D4 SUPERATO' if not fails else 'FALLITO:'}")
    for f in fails:
        print(f"    {f}")
    if rows:
        tot = sum(x["seconds"] for x in rows) / len(rows)
        n_pts = len(pts) - 1
        print(f"\n  {tot:.1f} s per realizzazione su {len(pts)} punti "
              f"-> stima 10 punti x 200 mock x 2 emisferi: "
              f"{tot/len(pts)*10*200*2/3600:.1f} h")
    return 1 if fails else 0


def _avviso_d5c():
    """Lo stato di D5c si stampa SEMPRE, non solo quando e' anomalo.

    Il messaggio precedente diceva "NON per un run che produce risultati": era
    la formulazione del record 23, quando la deroga copriva due run NOMINATI. Il
    record 34 l'ha rilegata a una condizione che copriva tutti i run, e il 36
    l'ha chiusa dichiarando la soglia. Quel testo ha continuato ad allarmare su
    una cosa regolare per due record, e un avviso che grida al lupo smette di
    essere letto."""
    if D5C_MODE == "block":
        print(f"  [D5c] modalita' 'block', soglia {D5C_SOGLIA} "
              f"(record 36: meta' della SEM piu' piccola, "
              f"{D5C_SOGLIA * 0.1574:.1f} generatori).")
        return
    print("=" * 74)
    print(f"  ATTENZIONE: D5c e' in modalita' '{D5C_MODE}', NON in 'block'.")
    print("  Il cancello MISURA e non ferma. La deroga dei record 23 e 34 e'")
    print("  CHIUSA dal record 36, che ha dichiarato la soglia: questa")
    print("  modalita' non e' piu' coperta da nessun record.")
    print(f"  Rimettere D5C_MODE = 'block' in cima a questo file.")
    print("=" * 74)


def _accendi_real_space(M, a):
    """LA RIGA CHE MANCAVA (record 35).

    REAL_SPACE e' una variabile di MODULO in phase8: il flag di argparse non la
    tocca da solo. Senza questa funzione il run gira in spazio di redshift
    scrivendo real_space: true nel record, che e' esattamente quel che e'
    successo il 1-2 settembre: dodici ore, 2400 celle su 2400 identiche al run
    principale.

    Si stampa sempre, anche quando e' False: uno stato che non si vede e' uno
    stato che si dimentica."""
    rs = bool(getattr(a, "real_space", False))
    M.REAL_SPACE = rs
    print(f"  [phase8] REAL_SPACE = {M.REAL_SPACE}"
          + ("   <-- v_los AZZERATO, spazio reale" if rs else ""))
    if rs and not getattr(M, "REAL_SPACE", False):
        sys.exit("[FATAL] REAL_SPACE non e' stato accettato dal modulo: il "
                 "flag esiste ma non arriva a carve_cutsky.")
    return rs


ROT_SEED_DEFAULT = 20260905


def _verifica_ripattern(M, a):
    """Item 3.2d. Due cose che devono valere PRIMA di consumare ore di macchina.

    (1) --replica-randomise e --fixed-observables sono incompatibili: sotto
        (B) il carving avviene UNA volta al fiduciale e i punti sono
        rimappati, quindi randomizzare toccherebbe solo quel carving. E'
        una domanda diversa, e mescolarle darebbe un numero che non
        risponde a nessuna delle due.
    (2) il flag deve ARRIVARE a carve_cutsky. Qui il rischio non e' un
        globale mai assegnato -- e' un parametro, non un globale -- ma
        girare contro un phase8 NON patchato, dopo un checkout per dire.
        Si controlla la FIRMA, non l'esistenza del flag.

    Si stampa sempre, anche quando e' False: uno stato che non si vede e'
    uno stato che si dimentica.
    """
    rr = bool(getattr(a, "replica_randomise", False))
    print(f"  [phase8] randomise_replicas = {rr}")
    if not rr:
        return False
    if bool(getattr(a, "fixed_observables", False)):
        sys.exit("[FATAL] --replica-randomise e --fixed-observables sono "
                 "incompatibili: sotto il trattamento (B) il carving e' "
                 "uno solo, al fiduciale. Sono due misure diverse e "
                 "vogliono due --out diversi.")
    import inspect as _inspect
    if "randomise_replicas" not in _inspect.signature(
            M.carve_cutsky).parameters:
        sys.exit("[FATAL] phase8 non e' patchato: carve_cutsky non "
                 "accetta randomise_replicas, quindi il flag non "
                 "arriverebbe da nessuna parte. Lancia prima "
                 "src/paper2_ripattern_patch.py patch --apply.")
    print(f"  [phase8] rot_seed = {int(a.rot_seed)}   <-- repliche "
          f"randomizzate, LE STESSE a ogni punto")
    return True


def cmd_run(a):
    _avviso_d5c()
    pts = a.points
    (M, P1, T2, F3, root, reg, geoms, Gr, cache_dir, frozen) = _prepare(a, pts)
    _accendi_real_space(M, a)
    _verifica_ripattern(M, a)
    order = [p for p in geoms if p != "FID"] if a.skip_fid else list(geoms)
    done = set()
    if a.out and Path(a.out).exists():
        for l in Path(a.out).read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                if not r.get("smoke"):
                    # La chiave e' (regione, indice, seme del carving, INSIEME
                    # DEI PUNTI). Il seme perche' il termine (c) e' una misura
                    # diversa sulla stessa realizzazione. L'insieme dei punti
                    # perche' un record a undici punti non deve far saltare un
                    # run su un punto solo aggiunto dopo (B6, emendamento 15):
                    # senza, appendere B6 nello stesso registro salterebbe tutto.
                    # real_space entra nella chiave: senza, un run in spazio
                    # reale salterebbe le realizzazioni gia' fatte in spazio di
                    # redshift, che sono una MISURA DIVERSA. Con --out separato
                    # non succede, ma la chiave non deve dipendere da quella
                    # disciplina esterna.
                    done.add((r.get("region"), r.get("index"),
                              r.get("carve_reseed"),
                              tuple(sorted(r.get("points", {}))),
                              tuple(r.get("erosions", EROSIONS_MOCK)),
                              bool(r.get("real_space", False)),
                              bool(r.get("fixed_observables", False)),
                              bool(r.get("replica_randomise", False)),
                              r.get("rot_seed"),
                              # §C: l'offset dell'origine e' una GEOMETRIA
                              # diversa, quindi una misura diversa. Senza
                              # questa componente due offset condividono la
                              # chiave e la ripresa non li separa.
                              (float(r["origin_offset"])
                               if r.get("origin_offset") is not None
                               else None)))
    ero = tuple(a.erosions) if a.erosions else EROSIONS_MOCK
    print("=" * 74)
    print(f"3.2 — lato mock appaiato, {reg}, punti {order}, erosioni {list(ero)}")
    print("=" * 74)
    t0 = time.time()
    n_done = 0
    for kk in range(a.n):
        if (reg, kk, a.carve_reseed, tuple(sorted(order)),
                tuple(ero), bool(getattr(a, "real_space", False)),
                bool(getattr(a, "fixed_observables", False)),
                bool(getattr(a, "replica_randomise", False)),
                (int(a.rot_seed)
                 if getattr(a, "replica_randomise", False) else None),
                (float(a.origin_offset)
                 if getattr(a, "origin_offset", None) is not None
                 else None)) in done:
            continue
        r = one_mock(M, P1, T2, F3, reg, geoms, kk, Gr["nz_z"], Gr["nz_target"],
                     order, frozen_delta_dir=cache_dir if not a.skip_fid else None,
                     carve_reseed=a.carve_reseed, erosions=ero,
                     fixed_observables=bool(getattr(a, "fixed_observables", False)),
                     replica_randomise=bool(
                         getattr(a, "replica_randomise", False)),
                     rot_seed=(int(a.rot_seed)
                               if getattr(a, "replica_randomise", False)
                               else None))
        if r is None:
            continue
        rec = {"schema": "paper2_fase3_mock_v1", "region": reg, "index": kk,
               "gauge_version": GAUGE_VERSION, "utc": now(),
               "points": {p: r[p] for p in order if p in r},
               "seconds": r["_seconds"], "n_gal": r["_n_gal"],
               "erosions": list(ero)}
        if a.carve_reseed is not None:
            rec["carve_reseed"] = int(a.carve_reseed)
        if getattr(a, "real_space", False):
            rec["real_space"] = True
        if getattr(a, "fixed_observables", False):
            rec["fixed_observables"] = True
        # Item 3.2d: un run la cui provenienza non sta nel record e'
        # esattamente il rilievo §3.9, e l'abbiamo appena chiuso.
        if getattr(a, "replica_randomise", False):
            rec["replica_randomise"] = True
            rec["rot_seed"] = int(a.rot_seed)
        # Il record deve dire a quale geometria appartiene. Senza, due
        # offset diversi finiscono nello stesso registro indistinguibili,
        # ed e' esattamente quello che e' successo.
        if getattr(a, "origin_offset", None) is not None:
            rec["origin_offset"] = float(a.origin_offset)
        if a.out:
            append_jsonl(a.out, rec)
        n_done += 1
        if n_done % 5 == 1:
            el = time.time() - t0
            left = (a.n - kk - 1) * el / n_done
            print(f"  [{kk:4d}] {r['_seconds']:.0f}s  "
                  f"ETA {left/3600:.1f} h")
    print(f"\n[fine] {n_done} realizzazioni in {(time.time()-t0)/3600:.2f} h")
    return 0


def cmd_selftest(a):
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    # il ripristino dello stato e' cio' che rende appaiati i punti
    rng = np.random.default_rng(7)
    rng.random(10)
    st = rng.bit_generator.state
    a1 = rng.random(5)
    rng.bit_generator.state = st
    a2 = rng.random(5)
    expect("1. ripristinando lo stato l'estrazione si ripete identica",
           np.array_equal(a1, a2))
    b = rng.random(5)
    expect("2. senza ripristino no: e' il confondente che si sta togliendo",
           not np.array_equal(a1, b))

    rng2 = np.random.default_rng(7)
    rng2.random(10)
    expect("3. e lo stato dipende solo dal seme e dai consumi precedenti",
           rng2.bit_generator.state["state"] == st["state"])

    # fusione delle celle contro last-wins
    import collections
    merged = collections.defaultdict(dict)
    for cells in ({"R5_er0": 1}, {"R5_er2": 2}, {"R5_er1": 3}):
        merged["k"].update(cells)
    expect("4. la fusione tiene tutte le celle, last-wins ne perderebbe due",
           set(merged["k"]) == {"R5_er0", "R5_er1", "R5_er2"})

    expect("5. il baseline appaiato e' n=200, non n=2000",
           abs(BASELINE_N200["SGC"]["0"] - 18693.595) < 1e-6
           and abs(BASELINE_N200["NGC"]["0"] - 35423.575) < 1e-6)
    expect("6. e non coincide con l'ensemble del cancello 2.1-E",
           abs(BASELINE_N200["NGC"]["0"] - 35436.686) > 10
           and abs(BASELINE_N200["SGC"]["0"] - 18712.9675) > 10)

    expect("7. N_TARGET per emisfero, e sono diversi",
           N_TARGET["NGC"] == 217614 and N_TARGET["SGC"] == 82429)
    expect("8. sul lato mock si calcolano solo k=0 e k=1",
           tuple(EROSIONS_MOCK) == (0, 1))

    # --- termine (c): il ri-seme cambia il carving e non l'HOD ---------------
    r0 = np.random.default_rng(SEED + 5)
    r0.random(1000)                      # simula il consumo dell'HOD
    st_hod = r0.bit_generator.state
    st_new = np.random.default_rng(777 + 5).bit_generator.state
    expect("9. il ri-seme del carving da' uno stato DIVERSO da quello post-HOD",
           st_new["state"] != st_hod["state"])
    a1 = np.random.default_rng(777 + 5).random(5)
    a2 = np.random.default_rng(777 + 5).random(5)
    expect("10. ma resta riproducibile: stesso seme, stesse estrazioni",
           np.array_equal(a1, a2))
    b1 = np.random.default_rng(777 + 5).random(5)
    b2 = np.random.default_rng(777 + 6).random(5)
    expect("11. e realizzazioni diverse hanno carving diversi",
           not np.array_equal(b1, b2))
    expect("12. la chiave di ripartenza include il seme del carving",
           ("NGC", 3, None, ("FID",)) != ("NGC", 3, 777, ("FID",)))
    expect("13. e l'insieme dei punti: undici non fa saltare uno",
           ("NGC", 3, None, tuple(sorted(["FID", "B1", "B6"])))
           != ("NGC", 3, None, ("B6",)))
    expect("14. e i livelli di erosione: k=0,1 non fa saltare k=2,3",
           ("NGC", 3, None, ("FID",), (0, 1))
           != ("NGC", 3, None, ("FID",), (2, 3)))
    expect("15. il default resta k=0,1: i livelli diagnostici si chiedono",
           tuple(EROSIONS_MOCK) == (0, 1))

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", default="src")
    p.add_argument("--project_root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for nm in ("smoke", "run"):
        q = sub.add_parser(nm)
        q.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
        q.add_argument("--n", type=int, default=3 if nm == "smoke" else 200)
        q.add_argument("--points", nargs="*", default=None)
        q.add_argument("--out", default=LOG_DEFAULT)
        q.add_argument("--no-cache-gate", action="store_true")
        if nm == "run":
            q.add_argument("--skip-fid", action="store_true",
                           help="riusa i 200 fiduciali congelati, se D4 e' passato")
            q.add_argument("--erosions", type=int, nargs="*", default=None,
                           help="livelli di erosione; default 0 1. I livelli 2 "
                                "e 3 sono diagnostici e costano ~21 h in piu'")
            q.add_argument("--carve-reseed", type=int, default=None,
                           help="termine (c) del 3.3: cambia SOLO il seme del "
                                "carving, HOD identico, geometria ferma")
            q.add_argument("--real-space", action="store_true",
                           help="§3.8: azzera v_los, cioe' niente RSD. Usare un "
                                "--out SEPARATO: e' una misura diversa, non una "
                                "continuazione di quella in spazio di redshift")
            q.add_argument("--replica-randomise", action="store_true",
                           help="item 3.2d / referee 4.6: una permutazione "
                                "segnata degli assi per replica, LE STESSE "
                                "a ogni punto. Usare un --out SEPARATO: e' "
                                "una misura diversa. Incompatibile con "
                                "--fixed-observables")
            q.add_argument("--origin-offset", type=float, default=None,
                           metavar="H_MPC",
                           help="§C del secondo report: trasla l'origine "
                                "dell'embedding di questa quantita'. Cambia "
                                "la FASE della griglia rispetto al reticolo "
                                "del box, non lo spostamento RELATIVO fra i "
                                "punti. Richiede --skip-fid e un --out "
                                "SEPARATO: e' un'altra geometria")
            q.add_argument("--rot-seed", type=int, default=ROT_SEED_DEFAULT,
                           help="seme del generatore delle permutazioni. "
                                "Entra nel record e nella chiave di "
                                "ripresa: due semi diversi sono due misure")
            q.add_argument("--fixed-observables", action="store_true",
                           help="trattamento (B), record 16: (rhat, z_obs) "
                                "congelate al fiduciale, per ogni punto si "
                                "ricalcola solo r'. Usare un --out SEPARATO")
        if nm == "smoke":
            # Lo smoke deve poter girare CON il flag: e' l'unico modo di
            # distinguere "inerte" da "scollegato" (record 35). Senza questo,
            # lo smoke conferma solo che senza flag non cambia nulla, che era
            # vero anche quando il flag non era collegato.
            q.add_argument("--real-space", action="store_true",
                           help="smoke in spazio reale: DEVE dare numeri "
                                "diversi dallo smoke normale, altrimenti il "
                                "flag e' ancora scollegato")
        # NON `else`: si legherebbe a `if nm == "smoke"`. Ogni sottocomando
        # riceve i default di cio' che NON dichiara, e nient'altro.
        if nm != "run":
            q.set_defaults(carve_reseed=None, fixed_observables=False)
        if nm not in ("run", "smoke"):
            q.set_defaults(real_space=False)
    a = p.parse_args()
    return {"selftest": cmd_selftest, "smoke": cmd_smoke, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

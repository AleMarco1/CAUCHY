#!/usr/bin/env python3
"""
paper2_data_geometry.py  --  Paper 2, item G3: il lato dati sotto una fiduciale
diversa.

PERCHE' UN MODULO NUOVO E NON UNA MODIFICA A phase6_bgs_voxelize.py

phase6_bgs_voxelize.py ha prodotto la geometria e la maschera di v1. Modificarlo
significherebbe toccare il produttore di un ensemble dichiarato immutabile. Qui
la sua logica viene RIPRODOTTA, e la riproduzione e' validata contro il record
congelato results/phase6_voxelize_diagnostics.json: se box_size, cell_size,
box_min, alpha e n_valid_voxels coincidono al fiduciale, la replica e' fedele.

IL PUNTO CHE QUESTO MODULO ESISTE PER RISOLVERE

Nella pipeline convivono DUE definizioni di maschera:

    phase6_bgs_voxelize.py:181    0.01 * field_r.mean()            <- tutto il cubo
    phase9_sgc_likeforlike.py:135 0.01 * field_r[field_r > 0].mean()  <- solo non nulli

Le due medie stanno nel rapporto della frazione di riempimento, quindi la
seconda e' 6.8x piu' restrittiva per la NGC e 12.2x per la SGC. v1 e' stato
costruito con la PRIMA.

Finora non ha morso: phase9 usa la maschera congelata quando la geometria e'
compatibile, e il ramo di ricostruzione non e' mai scattato. Nella Fase 3
scattera' a OGNI punto, perche' ogni cambio di fiduciale rende incompatibile la
maschera congelata. M26 sec.5.4 misura proprio questo sistematico: soglie
dall'1% al 20% spostano il deficit dal 20% al 29%. Un fattore 6.8 cade dentro
quell'intervallo, cioe' varrebbe ~12 volte il segnale AP anisotropo atteso
(<= 0.73 voxel), e con la stessa dipendenza dalla fiducia.

Qui la regola e' un parametro esplicito, senza default implicito: il chiamante
deve dire quale sta usando, e "v1_fullcube" e' la sola che riproduca v1.

ORDINE OBBLIGATO PER LA FASE 3

    1. M.set_geometry(dc_tab=...)          la mappatura radiale, PRIMA di tutto
    2. positions(region, kind="ran")       converte con la mappatura nuova
    3. derive_box(pos_r)                   il cubo dai random RICONVERTITI
    4. M.set_geometry(box_min=, box_size=) ora il cubo
    5. field_r = M.cic_3d(...)             CIC sulla griglia nuova
    6. build_mask(field_r, "v1_fullcube")  la maschera dalla griglia nuova

Invertire 1 e 3 significa riconvertire con la fiduciale e inscatolare con
l'altra: il difetto non produce alcun errore visibile.

Uso, da D:\\projects\\cauchy :

    python src\\paper2_data_geometry.py --validate           # fedelta' al fiduciale
    python src\\paper2_data_geometry.py --validate --region SGC
    python src\\paper2_data_geometry.py --compare-mask-rules # quanto pesa la regola
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M  # noqa: E402

PAD_MPC_H = 5.0          # phase6_bgs_voxelize.py:166-167, additivo per lato

# Le due regole, entrambe nominate. Nessun default implicito: il chiamante
# sceglie, e la scelta finisce nel record.
MASK_RULES = {
    # Verificata contro data_side in entrambi gli emisferi: la soglia e' l'1%
    # della densita' random pesata media sul CUBO PIENO, cioe'
    # 0.01 * sum(w_r)/NGRID**3 -> 0.0200129 (NGC, sum w_r = 4 197 016) e
    # 0.0085706 (SGC, 1 797 384).
    "v1_fullcube": lambda fr: 0.01 * fr.mean(),
    "nonzero_mean": lambda fr: 0.01 * fr[fr > 0].mean(),
}

# Limite pratico sulla lisciatura, PER REGIONE. Non e' una costante globale, e
# trattarla come tale e' l'errore che ha prodotto un falso allarme sul fiduciale
# SGC.
#
# d_med = mediana della distanza EUCLIDEA dal bordo della maschera, in unita' di
# griglia (scipy.ndimage.distance_transform_edt, come paper1_mask_erosion.py:78;
# la riga 19 dello stesso file dichiara "il footprint NGC ha profondita' mediana
# di soli 3 voxel"). Misurato: NGC 3.000 voxel ESATTI -> 3/9 = 0.33333, che
# riproduce il congelato `practical_limit_NGC` = 0.333 a +3e-4. SGC 2.828 =
# 2*sqrt(2) esatto -> 0.31422.
#
# ATTENZIONE, e va detto nel manoscritto: in SGC sigma_px fiduciale = 0.33606 e'
# -6.9% OLTRE il limite, e lo e' in tutti e 11 i punti della griglia AP. Non e'
# quindi un criterio di esclusione utilizzabile al sud, perche' escluderebbe un
# risultato pubblicato: e' un CAVEAT. Il criterio primario resta w_bar >= 0.99
# (SGC: 0.99642), e il rimedio operativo e' l'erosione, che il Paper 1 ha
# eseguito e che il deficit SGC ha superato.
#
# Il sud e' piu' difficile perche' due effetti si sommano: footprint piu' sottile
# (2.828 contro 3.000 voxel, +6.1%) e cella piu' piccola (14.879 contro 15.604,
# quindi sigma_px = R/dx piu' grande, +4.9%).
#
# Da valutare SEMPRE sulla maschera a k = 0: applicarlo alla maschera erosa e' un
# errore di categoria, perche' l'erosione assottiglia il footprint mentre rimuove
# proprio i voxel che il limite voleva segnalare.
D_MED_VOXEL = {"NGC": 3.0000000, "SGC": 2.8284271}
PRACTICAL_LIMIT = {r: d / 9.0 for r, d in D_MED_VOXEL.items()}


def positions(region: str, kind: str, zmin=None, zmax=None):
    """Posizioni comoventi e pesi, convertite con la mappatura CORRENTE.

    Usa M.comoving_distance, che set_geometry() ridirige sulla tabella iniettata:
    chiamando questa funzione dopo set_geometry() si ottengono automaticamente le
    posizioni nella fiduciale nuova. Non fa CIC, perche' il cubo non e' ancora
    noto — e' esattamente il passo che i loader di phase8 non permettono di
    separare.
    """
    # 0.8 — nessun ramo 'else' silenzioso. Senza questa guardia, kind="random"
    # o un refuso come "dta" caricherebbero i DATI con i pesi dei dati, senza
    # errore: la stessa classe di difetto della collisione di path che produsse
    # la discrepanza 445/313 nel Paper 1.
    if kind not in ("ran", "dat"):
        raise ValueError(f"positions: kind='{kind}' non valido; usare 'ran' o 'dat'")
    if region not in ("NGC", "SGC"):
        raise ValueError(f"positions: region='{region}' non valida; usare 'NGC' o 'SGC'")

    from astropy.io import fits
    zmin = M.ZMIN if zmin is None else zmin
    zmax = M.ZMAX if zmax is None else zmax
    base = M.DESI_DIR / f"BGS_BRIGHT-21.5_{region}"
    path = Path(f"{base}_0_clustering.ran.fits") if kind == "ran" \
        else Path(f"{base}_clustering.dat.fits")   # kind gia' validato sopra
    if not path.exists():
        raise FileNotFoundError(path)
    with fits.open(path) as h:
        t = h["LSS"].data
        mz = (t["Z"] >= zmin) & (t["Z"] <= zmax)
        ra = t["RA"][mz].astype(np.float64)
        dec = t["DEC"][mz].astype(np.float64)
        z = t["Z"][mz].astype(np.float64)
        # pesi identici a phase6 e a phase8: WEIGHT_FKP per i random,
        # WEIGHT * WEIGHT_FKP per i dati
        w = t["WEIGHT_FKP"][mz].astype(np.float64)
        if kind == "dat":                       # esplicito, non 'diverso da ran'
            w = w * t["WEIGHT"][mz].astype(np.float64)
    dC = np.atleast_1d(M.comoving_distance(z)).astype(np.float64)
    rar, decr = np.radians(ra), np.radians(dec)
    pos = np.column_stack([dC * np.cos(decr) * np.cos(rar),
                           dC * np.cos(decr) * np.sin(rar),
                           dC * np.sin(decr)])
    return pos, w


def derive_box(pos_r: np.ndarray, pad: float = PAD_MPC_H):
    """Cubo di embedding: regola di phase6_bgs_voxelize.py:166-168.

    Il padding e' ADDITIVO e non viene riscalato: e' la ragione per cui la
    Proposizione 2 vale a 1.4e-2 voxel invece che esattamente.

    Il residuo NON e' un errore generico. Posto E = estensione dei random, la
    mappa fra coordinate di griglia e' l'affinita'

        u(alpha) = a(alpha) * u(1) + b(alpha),
        a(alpha) = alpha*(E + 2p) / (alpha*E + 2p),

    identica sui tre assi e con PUNTO FISSO u* = N/2, cioe' il centro del cubo.
    E' quindi una dilatazione isotropa residua, e lo spostamento massimo e'

        max|du| = (N/2)*|a-1| = N*p*|1-alpha| / (alpha*E + 2p)

    cioe' 1.25e-2 voxel (NGC) e 1.31e-2 (SGC) all'angolo alpha = 1.0406, il
    peggiore della griglia AP.

    La stima 2p(1-alpha)/L = 2.5e-2 che circolava e' il DIAMETRO dell'escursione:
    conservativa di un fattore 2 ESATTO, perche' ignora che il punto fisso sta al
    centro. Verificata sui dati veri: per A1 (alpha=0.9725) la forma chiusa
    predice L = 1942.710437 contro 1942.7104 osservato; per A3 (alpha=1.0406)
    2078.049851 contro 2078.0498.

    Essendo una dilatazione, il residuo e' ISOTROPO: non puo' imitare una firma
    F_AP, e contamina solo la linea alpha_iso pura, che e' gia' un test ad attesa
    nulla.

    Per il cancello 2.2b si passa pad = PAD_MPC_H * alpha_iso e l'invarianza
    torna esatta.
    """
    box_min = pos_r.min(axis=0) - pad
    box_max = pos_r.max(axis=0) + pad
    box_size = float((box_max - box_min).max())
    return box_min, box_size


def build_mask(field_r: np.ndarray, rule: str):
    if rule not in MASK_RULES:
        raise ValueError(f"regola maschera '{rule}' sconosciuta; "
                         f"scegliere fra {sorted(MASK_RULES)}")
    thr = float(MASK_RULES[rule](field_r))
    mask = field_r > thr
    return mask, thr


def data_side(region: str, mask_rule: str = "v1_fullcube", pad: float = PAD_MPC_H,
              verbose: bool = True) -> dict:
    """Geometria, campi e maschera del lato dati, nella fiduciale CORRENTE.

    Chiama set_geometry() con il cubo derivato, cosi' che lato dati e lato mock
    restino sulla stessa griglia per costruzione.
    """
    pos_r, w_r = positions(region, "ran")
    box_min, box_size = derive_box(pos_r, pad)
    M.set_geometry(box_min=box_min, box_size=box_size, verbose=False)

    field_r = M.cic_3d(pos_r, w_r, M.NGRID, box_min, box_size)
    sum_wr = float(w_r.sum())
    pos_d, w_d = positions(region, "dat")
    field_d = M.cic_3d(pos_d, w_d, M.NGRID, box_min, box_size)
    sum_wd = float(w_d.sum())
    mask, thr = build_mask(field_r, mask_rule)

    out = {
        "region": region,
        "mask_rule": mask_rule,
        "pad_mpc_h": pad,
        "box_size_mpc_h": box_size,
        "cell_size_mpc_h": box_size / M.NGRID,
        "sigma_px": M.R_SMOOTH / (box_size / M.NGRID),
        "box_min": box_min.tolist(),
        "alpha": sum_wd / sum_wr,
        "N_data": int(len(pos_d)),
        "N_rand": int(len(pos_r)),
        "mask_threshold": thr,
        "n_valid_voxels": int(mask.sum()),
        "survey_fill_fraction": float(mask.mean()),
        "D_C_ZMIN": M.D_C_ZMIN, "D_C_ZMAX": M.D_C_ZMAX,
    }
    if verbose:
        print(f"  {region}: box={box_size:.4f} cell={out['cell_size_mpc_h']:.6f} "
              f"sigma_px={out['sigma_px']:.6f} alpha={out['alpha']:.6f} "
              f"voxel={out['n_valid_voxels']} fill={100*out['survey_fill_fraction']:.2f}%")
    return {**out, "_fields": (field_d, field_r, mask, sum_wd, sum_wr)}


# Le geometrie congelate non stanno tutte nello stesso posto.
# phase6_bgs_voxelize.py riscrive l'INTERO file di diagnostica a ogni run, quindi
# un'esecuzione con --region NGC cancella il blocco SGC scritto in precedenza:
# results/phase6_voxelize_diagnostics.json contiene solo l'ultima regione girata.
# La geometria SGC sopravvive pero' in results/phase9_sgc_likeforlike.json, che e'
# anzi la fonte migliore: e' quella che ha prodotto i numeri SGC pubblicati.
FROZEN_SOURCES = [
    {
        "path": "results/phase6_voxelize_diagnostics.json",
        "extract": lambda d, r: d.get("regions", {}).get(r),
        "keys": {"box_size_mpc_h": "box_size_mpc_h", "cell_size_mpc_h": "cell_size_mpc_h",
                 "alpha": "alpha", "N_data": "N_data", "N_rand": "N_rand",
                 "n_valid_voxels": "n_valid_voxels", "sigma_px": "sigma_smooth_px",
                 "R_smooth": "R_smooth_mpc_h", "box_min": "box_min"},
        "label": "phase6_voxelize_diagnostics",
    },
    {
        "path": "results/phase9_sgc_likeforlike.json",
        "extract": lambda d, r: ({**d["sgc_geometry"],
                                  "N_data": d.get("sgc_data_galaxies"),
                                  "n_valid_voxels": round(
                                      d["sgc_geometry"]["mask_fill_pct"] / 100.0 * 128 ** 3)}
                                 if r == "SGC" and "sgc_geometry" in d else None),
        "keys": {"box_size_mpc_h": "box_size_mpc_h", "cell_size_mpc_h": "cell_mpc_h",
                 "N_data": "N_data", "n_valid_voxels": "n_valid_voxels",
                 "sigma_px": "sigma_px", "box_min": "box_min"},
        "label": "phase9_sgc_likeforlike",
    },
]


def find_frozen(region: str, root: Path):
    """Prima fonte congelata che contenga la regione. Restituisce (dict, label)."""
    tried = []
    for src in FROZEN_SOURCES:
        fp = root / src["path"]
        if not fp.exists():
            tried.append(f"{src['path']} (assente)")
            continue
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            tried.append(f"{src['path']} (illeggibile)")
            continue
        blk = src["extract"](doc, region)
        if blk is None:
            avail = sorted(doc.get("regions", {})) if "regions" in doc else []
            tried.append(f"{src['path']} (regioni presenti: {avail or 'nessuna'})")
            continue
        return {k: blk.get(v) for k, v in src["keys"].items() if blk.get(v) is not None}, \
               src["label"], tried
    return None, None, tried


def validate(region: str, root: Path) -> int:
    frozen, label, tried = find_frozen(region, root)
    if frozen is None:
        sys.stderr.write(f"\nNessuna geometria congelata per {region}. Fonti provate:\n")
        for t in tried:
            sys.stderr.write(f"  - {t}\n")
        sys.stderr.write(
            "\nPer la NGC serve results/phase6_voxelize_diagnostics.json con il blocco\n"
            "NGC; per la SGC va bene anche results/phase9_sgc_likeforlike.json.\n"
            "Rigenerare il primo con:\n"
            "    python src/phase6_bgs_voxelize.py --region both\n"
            "ATTENZIONE: quel run RISCRIVE i campi in data/processed/phase6_fields/,\n"
            "che sono ingressi di v1. Verificare prima con paper2_freeze_v1.py verify.\n")
        return 2

    M.set_geometry(omm=0.3175, verbose=False)          # fiduciale esatta
    got = data_side(region, mask_rule="v1_fullcube", verbose=False)

    print(f"\n=== fedelta' al record congelato — {region} ===")
    print(f"    fonte: {label}")
    # sigma_px = R_smooth / cell e' una DEFINIZIONE: confrontarla col valore
    # congelato ha senso solo se il record e' stato scritto con lo stesso R. Se
    # l'R del record differisce, il confronto va fatto contro R_record/cell, e
    # la discrepanza va segnalata come difetto del RECORD, non della replica.
    R_rec = frozen.get("R_smooth")
    if R_rec is not None and abs(R_rec - M.R_SMOOTH) > 1e-9:
        print(f"\n  !! il record e' stato scritto con R_smooth = {R_rec} Mpc/h,")
        print(f"     la pipeline usa R = {M.R_SMOOTH}. sigma_px viene quindi confrontato")
        print(f"     contro {R_rec}/cell, non contro {M.R_SMOOTH}/cell.")
        print(f"     Tutto il resto del record e' indipendente da R (il box, la cella,")
        print(f"     alpha, i conteggi e LA MASCHERA, che si calcola prima dello")
        print(f"     smoothing), quindi resta confrontabile.\n")
        frozen["sigma_px"] = R_rec / frozen["cell_size_mpc_h"]
        got = {**got, "sigma_px": R_rec / got["cell_size_mpc_h"]}
    # NB: se il record congelato ha scritto sigma_px con la stessa definizione
    # (R/cell), il controllo qui sotto e' IMPLICATO da quello sulla cella a 1e-9
    # e non porta informazione indipendente. Non e' un difetto — sigma_px e' una
    # definizione, non una misura — ma va saputo: il 10/10 di G3 non ha mai
    # testato sigma_px in modo autonomo.
    checks = [("box_size_mpc_h", 1e-9), ("cell_size_mpc_h", 1e-9), ("sigma_px", 1e-6),
              ("alpha", 1e-9), ("N_data", 0), ("N_rand", 0), ("n_valid_voxels", 0)]
    fails = 0
    for name, tol in checks:
        if name not in frozen:
            print(f"  [ -- ] {name:<18} non presente in {label}")
            continue
        a, b = got[name], frozen[name]
        d = abs(a - b)
        ok = (d == 0) if tol == 0 else (d / max(abs(b), 1e-30) < tol)
        fails += (not ok)
        print(f"  [{'OK ' if ok else 'FAIL'}] {name:<18} {a!r:<24} atteso {b!r}"
              + ("" if ok else f"   scarto {d:.3e}"))
    if "box_min" in frozen:
        for i, (a, b) in enumerate(zip(got["box_min"], frozen["box_min"])):
            ok = abs(a - b) < 1e-9
            fails += (not ok)
            print(f"  [{'OK ' if ok else 'FAIL'}] box_min[{i}]        {a!r:<24} atteso {b!r}")
    print("\n  " + ("REPLICA FEDELE: la logica di phase6 e' riprodotta."
                    if not fails else f"{fails} scostamenti — NON usare per la Fase 3."))
    return 1 if fails else 0


def compare_mask_rules(region: str) -> None:
    """Quanto pesa la scelta della regola, sul footprint vero."""
    M.set_geometry(omm=0.3175, verbose=False)
    pos_r, w_r = positions(region, "ran")
    box_min, box_size = derive_box(pos_r)
    M.set_geometry(box_min=box_min, box_size=box_size, verbose=False)
    field_r = M.cic_3d(pos_r, w_r, M.NGRID, box_min, box_size)
    print(f"\n=== peso della regola di maschera — {region} ===")
    ref = None
    for rule in ("v1_fullcube", "nonzero_mean"):
        mask, thr = build_mask(field_r, rule)
        n = int(mask.sum())
        if ref is None:
            ref = n
        print(f"  {rule:<14} soglia={thr:.6e}  voxel={n:>7}  fill={100*mask.mean():5.2f}%"
              f"  rispetto a v1: {100*(n-ref)/ref:+6.2f}%")
    print("\n  M26 sec.5.4: alzando la soglia dall'1% al 5% e al 20% della densita'")
    print("  random media, il deficit frazionario passa dal 20% al 29%. Una")
    print("  differenza di maschera di questa entita' NON e' un dettaglio: nella")
    print("  Fase 3 varrebbe piu' del segnale AP che si vuole misurare.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Lato dati sotto fiduciale arbitraria (G3).")
    ap.add_argument("--region", default="NGC", choices=["NGC", "SGC"])
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--compare-mask-rules", action="store_true")
    ap.add_argument("--root", default=".", help="radice del progetto")
    args = ap.parse_args()
    if not hasattr(M, "set_geometry"):
        sys.stderr.write("set_geometry() assente: inserire prima il blocco G2.\n")
        return 2
    rc = 0
    if args.validate:
        rc |= validate(args.region, Path(args.root).resolve())
    if args.compare_mask_rules:
        compare_mask_rules(args.region)
    if not (args.validate or args.compare_mask_rules):
        ap.print_help()
    return rc


if __name__ == "__main__":
    sys.exit(main())

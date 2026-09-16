#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_pareggi_profondi.py — quanti pareggi sono invarianti PER COSTRUZIONE.

L'ARGOMENTO, PRIMA DELLA MISURA
-------------------------------
1. I pesi FKP sono STRETTAMENTE POSITIVI (la tabella di n6 sta in (0,1],
   minimo 0.2516). Quindi un voxel con field_d = 0 senza pesi ha field_d = 0
   anche con i pesi: **l'insieme dei voxel vuoti e' identico fra v1 e v2**, non
   approssimativamente ma esattamente. La CIC distribuisce su otto celle con
   pesi non negativi, e sommare contributi positivi non puo' dare zero se ce
   n'e' uno.
2. Dove non c'e' nessuna galassia, delta = -1 ESATTO. Il clip lo porta a
   -1+1e-3 e log(1e-3) e' lo stesso float ovunque.
3. Il raggio del kernel e' UN voxel: int(4 * 0.3204 + 0.5) = 1, dalla
   kernel_weights di rev1_r14_monotone con truncate=4 di scipy. Quindi nu in
   un voxel dipende SOLO dal suo blocco 3x3x3.
4. Percio' un voxel il cui intero blocco 3x3x3 e' vuoto ha nu esattamente
   uguale a ogni altro nella stessa condizione — chiamiamoli PROFONDI — e la
   sottrazione della media in maschera, che e' una costante, li sposta tutti
   insieme senza rompere il pareggio.

**I pareggi fra voxel profondi sono quindi ESATTAMENTE invarianti sotto
ripesatura. Solo gli altri possono muoversi.**

Questo strumento misura quanti sono, e il numero dice quanto margine ha la
regola 4.2e: se i profondi sono il 95% dei voxel in pareggio, una variazione
oltre il 5% falsificherebbe l'argomento sopra, non la ripesatura.

PERCHE' SERVE PRIMA DI SCRIVERE LA SOGLIA
-----------------------------------------
La soglia di 4.2e va DERIVATA da questa frazione, non scelta. Misurarla prima
di dichiararla e' l'ordine che il record 58 ha imposto a 4.3b.

USO
    python src\\paper2_pareggi_profondi.py selftest
    python src\\paper2_pareggi_profondi.py misura --region NGC
    python src\\paper2_pareggi_profondi.py misura --region SGC
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

CLIP_DELTA = -1.0
N_VOXEL = {"NGC": 307805, "SGC": 172225}
ROOT_DEFAULT = "."
MASCHERA = {"NGC": "bgs_ngc_mask_128.npy", "SGC": "bgs_sgc_mask_128.npy"}
SIGMA_PX_ATTESA = {"NGC": 0.32042249039652254, "SGC": 0.33605500065144590}
TRUNCATE = 4.0            # il default di scipy.ndimage.gaussian_filter


def raggio_kernel(sigma_px, truncate=TRUNCATE):
    """Lo stesso di rev1_r14_monotone.kernel_weights."""
    return int(truncate * sigma_px + 0.5)


def fissi(delta, mask, raggio):
    """
    Voxel il cui intero blocco (2r+1)^3 contiene SOLO valori di delta fissati
    dalla costruzione, cioe' indipendenti dai pesi:
       - dentro maschera e vuoto: delta = -1 ESATTO, perche' n_d = 0;
       - fuori maschera: delta = 0, azzerato da compute_delta.
    Entrambi non dipendono dai pesi, che sono strettamente positivi.

    LA PRIMA VERSIONE CONTAVA SOLO I VUOTI IN MASCHERA, e squalificava ogni
    voxel a ridosso del bordo — che e' esattamente dove i pareggi stanno
    (field_r mediano 0.079 contro 16.59). Trovava 4 voxel su 9364. L'argomento
    era giusto, la definizione no.
    """
    from scipy.ndimage import binary_erosion
    d = np.asarray(delta)
    m = np.asarray(mask, bool)
    fisso = ((d <= CLIP_DELTA + 1e-12) & m) | (~m)
    if raggio < 1:
        return fisso
    st = np.ones((2 * raggio + 1,) * 3, dtype=bool)
    return binary_erosion(fisso, structure=st, border_value=1)


def gruppi_pareggio(v):
    """(maschera dei voxel in pareggio, valori ripetuti, conteggi)."""
    u, cnt = np.unique(v, return_counts=True)
    rip = u[cnt > 1]
    return np.isin(v, rip), u, cnt


def misura(root, region, out_path=None):
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M          # noqa: E402
    import paper1_remap as P1                # noqa: E402

    d = Path(root)
    mask = np.load(d / "data" / "processed" / "phase6_fields"
                   / MASCHERA[region]).astype(bool)
    if int(mask.sum()) != N_VOXEL[region]:
        raise SystemExit("RIFIUTO: %d voxel, attesi %d"
                         % (int(mask.sum()), N_VOXEL[region]))

    print("=" * 78)
    print("PAREGGI PROFONDI  |  %s" % region)
    print("=" * 78)

    G = P1.setup_region(M, region, d / "data" / "raw" / "desi_dr1",
                        d / "data" / "processed" / "phase6_fields")
    sigma_px = float(M.SIGMA_PX)
    if abs(sigma_px - SIGMA_PX_ATTESA[region]) / SIGMA_PX_ATTESA[region] > 1e-9:
        raise SystemExit("RIFIUTO: sigma_px %.9f, atteso %.9f"
                         % (sigma_px, SIGMA_PX_ATTESA[region]))
    r = raggio_kernel(sigma_px)
    print("  sigma_px %.9f  ->  raggio del kernel %d voxel (truncate %.0f)"
          % (sigma_px, r, TRUNCATE))
    if r != 1:
        print("  [!] raggio diverso da 1: il blocco e' %dx%dx%d e l'argomento"
              % (2 * r + 1,) * 3)
        print("      sull'invarianza vale su quello, non sul 3x3x3")

    alpha = G["sum_wd"] / G["sum_wr"]
    delta = np.asarray(P1.compute_delta(G["field_d"], G["field_r"], alpha,
                                        mask, M.NGRID), dtype=np.float64)
    cache = (d / "results" / "paper1" / ("n1_desi_nu_%s.npy" % region))
    if not cache.is_file():
        cache = d / "results" / "paper2" / ("n1_desi_nu_%s.npy" % region)
    nu = np.load(cache)

    # --- i vuoti, e i profondi ---------------------------------------------
    vuoti_in_maschera = (delta <= CLIP_DELTA + 1e-12) & mask
    prof = fissi(delta, mask, r) & mask
    nv, npf = int(vuoti_in_maschera.sum()), int(prof.sum())
    # il confronto con la definizione stretta, per far vedere la differenza
    from scipy.ndimage import binary_erosion as _be
    st = np.ones((2 * r + 1,) * 3, dtype=bool)
    stretta = int((_be((delta <= CLIP_DELTA + 1e-12), structure=st,
                       border_value=0) & mask).sum()) if r >= 1 else nv
    print("\n  voxel vuoti (delta = -1) in maschera  : %7d  (%.3f%%)"
          % (nv, 100 * nv / N_VOXEL[region]))
    print("  a valore FISSO (vuoti dentro, zeri fuori): %7d  (%.1f%% dei vuoti)"
          % (npf, 100 * npf / nv if nv else 0))
    print("  con la definizione stretta (solo vuoti)  : %7d  <- la prima, sbagliata"
          % stretta)

    # --- i pareggi ----------------------------------------------------------
    vi = nu[mask]
    pari_in, u, cnt = gruppi_pareggio(vi)
    pari = np.zeros_like(mask)
    pari[mask] = pari_in
    npari = int(pari.sum())
    pari_prof = int((pari & prof).sum())
    pari_vuoti = int((pari & vuoti_in_maschera).sum())
    print("\n  voxel in pareggio                     : %7d  (%.3f%%)"
          % (npari, 100 * npari / N_VOXEL[region]))
    print("  di questi, vuoti                      : %7d  (%.1f%%)"
          % (pari_vuoti, 100 * pari_vuoti / npari if npari else 0))
    print("  di questi, PROFONDI e quindi INVARIANTI: %6d  (%.1f%%)"
          % (pari_prof, 100 * pari_prof / npari if npari else 0))
    mobili = npari - pari_prof
    print("  restano MOBILI                        : %7d  (%.1f%%)"
          % (mobili, 100 * mobili / npari if npari else 0))

    # --- il gruppo massimo --------------------------------------------------
    top = int(np.argmax(cnt))
    val = float(u[top])
    sel_flat = vi == val
    sel = np.zeros_like(mask)
    sel[mask] = sel_flat
    top_prof = int((sel & prof).sum())
    print("\n  gruppo massimo: %d voxel a nu = %.12g" % (cnt[top], val))
    print("    a valore fisso: %d su %d (%.0f%%)"
          % (top_prof, int(sel.sum()), 100 * top_prof / int(sel.sum())))

    # --- la soglia che ne discende -----------------------------------------
    f_inv = pari_prof / npari if npari else 0.0
    f_mob = 1.0 - f_inv
    print("\n  --- la soglia di 4.2e, DERIVATA da questi numeri ---")
    print("  Una frazione %.1f%% dei pareggi e' invariante PER COSTRUZIONE."
          % (100 * f_inv))
    print("  Al massimo il %.1f%% puo' muoversi ripesando, e solo se OGNI voxel"
          % (100 * f_mob))
    print("  mobile cambiasse gruppo: e' il limite superiore, non l'attesa.")
    print("  Quindi: successo se la variazione relativa del conteggio dei")
    print("  pareggi resta sotto %.3f, fallimento se supera %.3f."
          % (f_mob / 2, f_mob))
    print("  Oltre %.3f l'argomento sui pesi positivi sarebbe FALSO, e la"
          % f_mob)
    print("  cosa da rivedere non sarebbe la ripesatura ma il ragionamento.")

    rec = {"schema": "paper2_pareggi_profondi_v1", "region": region,
           "utc": datetime.now(timezone.utc).isoformat(),
           "sigma_px": sigma_px, "raggio_kernel": r,
           "n_voxel_maschera": N_VOXEL[region],
           "n_vuoti": nv, "n_fissi": npf, "n_fissi_definizione_stretta": stretta,
           "n_pareggio": npari, "n_pareggio_vuoti": pari_vuoti,
           "n_pareggio_fissi": pari_prof, "n_pareggio_mobili": mobili,
           "frazione_invariante": f_inv, "frazione_mobile": f_mob,
           "gruppo_massimo": {"molteplicita": int(cnt[top]), "valore_nu": val,
                              "fissi": top_prof},
           "soglia_4_2e_derivata": {"successo_sotto": f_mob / 2,
                                    "fallimento_sopra": f_mob,
                                    "nota": "limite superiore da un argomento, "
                                            "non da un campione"}}
    dest = (Path(out_path) if out_path
            else d / "results" / "paper2" / ("pareggi_profondi_%s.json" % region))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rec, indent=2, ensure_ascii=True), encoding="utf-8")
    print("\n  scritto: %s" % dest)
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

    print("selftest paper2_pareggi_profondi")

    # il raggio: quello di rev1_r14_monotone
    chk("sigma_px di NGC da' raggio 1",
        raggio_kernel(SIGMA_PX_ATTESA["NGC"]) == 1)
    chk("e quello di SGC pure", raggio_kernel(SIGMA_PX_ATTESA["SGC"]) == 1)
    chk("la formula e' int(4*sigma + 0.5), non ceil",
        raggio_kernel(0.3204) == 1 and raggio_kernel(0.1) == 0
        and raggio_kernel(0.4) == 2)
    chk("con sigma 1.0 il raggio sarebbe 4", raggio_kernel(1.0) == 4)

    # la definizione: FUORI MASCHERA conta come fisso, ed e' la correzione
    m = np.zeros((7, 7, 7), dtype=bool); m[2:5, 2:5, 2:5] = True
    d = np.zeros((7, 7, 7))            # fuori maschera delta = 0
    d[m] = -1.0                        # dentro, tutto vuoto
    f = fissi(d, m, 1)
    chk("un cubo di vuoti circondato da ESTERNO e' tutto fisso",
        int((f & m).sum()) == int(m.sum()) == 27, int((f & m).sum()))
    # la definizione vecchia ne trovava uno solo: e' il difetto, riprodotto
    from scipy.ndimage import binary_erosion
    st = np.ones((3, 3, 3), dtype=bool)
    vecchia = binary_erosion(d <= -1 + 1e-12, structure=st, border_value=0) & m
    chk("la definizione stretta ne trovava UNO: il centro",
        int(vecchia.sum()) == 1, int(vecchia.sum()))
    chk("quindi la correzione cambia 1 in 27 su questo caso",
        int((f & m).sum()) == 27 * int(vecchia.sum()))
    # un voxel pieno dentro rompe l'invarianza dei suoi vicini
    d2 = d.copy(); d2[3, 3, 3] = 5.0
    f2 = fissi(d2, m, 1)
    chk("un solo voxel pieno squalifica il suo intorno",
        int((f2 & m).sum()) < int((f & m).sum()), int((f2 & m).sum()))
    chk("e squalifica esattamente i voxel che lo hanno come vicino",
        int((f & m).sum()) - int((f2 & m).sum()) == 27)
    chk("con raggio 0 fisso = vuoto o fuori maschera",
        int(fissi(d, m, 0).sum()) == int(((d <= -1 + 1e-12) & m).sum()) + int((~m).sum()))

    # i pareggi
    x = np.array([1.0, 1.0, 2.0, 3.0, 3.0, 3.0, 4.0])
    m, u, c = gruppi_pareggio(x)
    chk("la maschera prende i due 1.0 e i tre 3.0, non il 2 e il 4",
        list(m) == [True, True, False, True, True, True, False], list(m))
    chk("il gruppo massimo ha tre elementi", int(c.max()) == 3)
    chk("senza ripetizioni nessuno e' in pareggio",
        int(gruppi_pareggio(np.array([1.0, 2.0, 3.0]))[0].sum()) == 0)

    # la soglia derivata
    for f_inv, s_att, f_att in ((0.95, 0.025, 0.05), (0.80, 0.10, 0.20),
                                (1.00, 0.0, 0.0)):
        f_mob = 1 - f_inv
        chk("con il %.0f%% invariante la soglia e' %.3f / %.3f"
            % (100 * f_inv, s_att, f_att),
            abs(f_mob / 2 - s_att) < 1e-12 and abs(f_mob - f_att) < 1e-12)
    # La proprieta' che conta non e' un'aritmetica ma la DIPENDENZA: la soglia
    # deve muoversi con la frazione misurata. Un confronto esatto in virgola
    # mobile — (1-0.9)/2 == 0.05 — sarebbe pure falso, e lo era.
    sog = lambda f: (1 - f) / 2
    chk("la soglia dipende dalla frazione misurata, e non e' una costante",
        sog(0.95) != sog(0.80) and sog(0.95) < sog(0.80))
    chk("con tutto invariante la soglia e' zero: nulla puo' muoversi",
        abs(sog(1.0)) < 1e-15)
    chk("ed e' monotona: piu' invariante, piu' stretta",
        all(sog(a) > sog(b) for a, b in zip([0.5, 0.7, 0.9], [0.7, 0.9, 0.99])))

    # l'argomento sui pesi positivi, sulla logica
    w = np.array([0.2516, 0.3797, 0.309])
    chk("i pesi FKP sono strettamente positivi", bool((w > 0).all()))
    conteggi = np.array([0.0, 0.0, 3.0])
    pesati = conteggi * 0.3
    chk("pesare non puo' rendere non vuoto un voxel vuoto",
        list((conteggi == 0)) == list((pesati == 0)))
    chk("ne' vuoto uno non vuoto", (conteggi[2] > 0) == (pesati[2] > 0))

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("misura")
    m.add_argument("--root", default=ROOT_DEFAULT)
    m.add_argument("--region", choices=["NGC", "SGC"], required=True)
    m.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "misura":
        return misura(a.root, a.region, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

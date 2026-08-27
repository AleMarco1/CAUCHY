#!/usr/bin/env python3
"""
paper2_g2_equivalence.py  --  Paper 2, item G2: set_geometry() e' equivalente?

Da eseguire DOPO aver inserito set_geometry() e make_dc_tab_ap() in
src/phase8_cutsky_mocks.py (subito dopo z_of_dc, riga 154).

Il criterio non e' "sembra funzionare": e' che al fiduciale la funzione sia un
NO-OP BIT-ESATTO. Se lo e', ogni numero di M26 e del Paper 1 resta riproducibile
per costruzione, e la rifattorizzazione non ha bisogno di essere ri-validata
sull'intera pipeline.

Test:
  T1  no-op esatto al fiduciale: nove costanti + la tabella _DC_TAB invariate
      allo zero assoluto, non "entro tolleranza"
  T2  geometria SGC: CELL e SIGMA_PX derivati devono riprodurre i valori
      pubblicati (M26 sec.5.4: sigma_px = 0.336; Paper 1: 0.3361)
  T3  alpha_iso puro: la mappatura scala esattamente, il rapporto e' alpha
  T4  F_AP puro: il pivot resta fermo, la curvatura cambia
  T5  monotonia imposta (cancello 2.4 della checklist)
  T6  omm e dc_tab mutuamente esclusivi
  T7  stato ripristinato al fiduciale alla fine

Uso, da D:\\projects\\cauchy :

    python src\\paper2_g2_equivalence.py
    python src\\paper2_g2_equivalence.py --sgc-box <valore reale del box SGC>

Exit 0 se tutto passa, 1 altrimenti.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M  # noqa: E402

# Costanti congelate di v1, lato NGC. Sono i valori che il modulo DEVE avere
# all'import e a cui DEVE tornare dopo un set_geometry(omm=0.3175).
FROZEN = {
    "OMM": 0.3175,
    "OML": 0.6825,
    "BOX_SIZE": 1997.3629167166155,
    "CELL": 15.604397786848558,
    "SIGMA_PX": 0.32042249039652254,
    "D_C_ZMIN": 292.535950750378,
    "D_C_ZMAX": 1080.7298534541035,
}
BOX_MIN_FROZEN = [-1085.5836039835003, -1059.3513403117618, -194.44091723978792]

fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def snapshot() -> dict:
    return {"scalars": {k: getattr(M, k) for k in FROZEN},
            "BOX_MIN": np.array(M.BOX_MIN, dtype=float).copy(),
            "DC_TAB": np.array(M._DC_TAB, dtype=float).copy(),
            "Z_TAB": np.array(M._Z_TAB, dtype=float).copy()}


def restore_fiducial() -> None:
    M.set_geometry(omm=0.3175, box_size=FROZEN["BOX_SIZE"],
                   box_min=BOX_MIN_FROZEN, verbose=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sgc-box", type=float, default=None,
                    help="lato del cubo SGC; se dato, T2 verifica sigma_px = 0.3361")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    if not hasattr(M, "set_geometry"):
        sys.stderr.write("set_geometry() non trovata in phase8_cutsky_mocks.py.\n"
                         "Inserirla dopo z_of_dc (riga 154) e rieseguire.\n")
        return 2

    print("\n=== stato all'import ===")
    for k, v in FROZEN.items():
        got = getattr(M, k)
        check(f"{k} all'import", got == v, f"{got!r}" + ("" if got == v else f" != {v!r}"))

    print("\n=== T1: set_geometry(omm=0.3175) e' un no-op BIT-ESATTO ===")
    before = snapshot()
    M.set_geometry(omm=0.3175, verbose=False)
    after = snapshot()
    for k in FROZEN:
        d = abs(after["scalars"][k] - before["scalars"][k])
        check(f"T1 {k}", d == 0.0, f"scarto {d:.3e}")
    dt = float(np.max(np.abs(after["DC_TAB"] - before["DC_TAB"])))
    check("T1 _DC_TAB", dt == 0.0, f"max|delta| = {dt:.3e}")
    dz = float(np.max(np.abs(after["Z_TAB"] - before["Z_TAB"])))
    check("T1 _Z_TAB", dz == 0.0, f"max|delta| = {dz:.3e}")
    db = float(np.max(np.abs(after["BOX_MIN"] - before["BOX_MIN"])))
    check("T1 BOX_MIN", db == 0.0, f"max|delta| = {db:.3e}")

    print("\n=== T2: geometria SGC (box diverso, cosmologia invariata) ===")
    sgc_box = args.sgc_box if args.sgc_box else 1904.5
    M.set_geometry(box_size=sgc_box, verbose=False)
    check("T2 CELL derivata", abs(M.CELL - sgc_box / M.NGRID) < 1e-12,
          f"{M.CELL:.6f}")
    check("T2 SIGMA_PX derivata", abs(M.SIGMA_PX - M.R_SMOOTH / M.CELL) < 1e-15,
          f"{M.SIGMA_PX:.6f}")
    if args.sgc_box:
        check("T2 sigma_px SGC = 0.3361", abs(M.SIGMA_PX - 0.3361) < 5e-4,
              f"{M.SIGMA_PX:.6f} contro 0.3361 pubblicato")
    else:
        print(f"       (box SGC approssimato a {sgc_box}: sigma_px = {M.SIGMA_PX:.6f}, "
              f"pubblicato 0.3361. Usare --sgc-box per il valore reale.)")
    check("T2 D_C invariati", M.D_C_ZMIN == FROZEN["D_C_ZMIN"]
          and M.D_C_ZMAX == FROZEN["D_C_ZMAX"],
          "la cosmologia non e' cambiata, quindi la finestra radiale non deve muoversi")
    restore_fiducial()

    print("\n=== T3: alpha_iso puro (la direzione che NON deve muovere N_H1) ===")
    # Il riferimento e' la tabella, NON la costante congelata D_C_ZMAX: quella
    # viene da comoving_distance() diretta, la tabella da interpolazione, e le
    # due differiscono di 3.4e-09 in relativo. Confrontarle sarebbe misurare la
    # discretizzazione della tabella invece della correttezza di alpha_iso.
    # Il rapporto va inoltre verificato su TUTTA la tabella, non in un punto.
    z0, dc0 = M.make_dc_tab_ap(alpha_iso=1.0, F_ap=1.0)
    pos = dc0 > 0
    for a in (0.97, 1.00, 1.04):
        z, dc = M.make_dc_tab_ap(alpha_iso=a, F_ap=1.0)
        ratio = dc[pos] / dc0[pos]
        worst = float(np.max(np.abs(ratio - a)))
        check(f"T3 alpha={a:.2f}", worst < 1e-12,
              f"max|dc/dc0 - alpha| = {worst:.3e} su {int(pos.sum())} punti")

    print("\n=== T4: F_AP puro (la direzione con contenuto fisico) ===")
    pivot_fid = float(np.interp(0.25, M._Z_TAB, M._DC_TAB))
    for F in (0.97, 1.00, 1.03):
        z, dc = M.make_dc_tab_ap(alpha_iso=1.0, F_ap=F)
        p = float(np.interp(0.25, z, dc))
        lo, hi = float(np.interp(0.1, z, dc)), float(np.interp(0.4, z, dc))
        check(f"T4 F_ap={F:.2f} pivot fermo", abs(p - pivot_fid) < 1e-6,
              f"D_C: [{lo:.3f}, {p:.3f}, {hi:.3f}]")
        check(f"T4 F_ap={F:.2f} monotona", bool(np.all(np.diff(dc) > 0)))

    print("\n=== T5: monotonia imposta (cancello 2.4) E atomicita' sul fallimento ===")
    pre = snapshot()
    bad = np.array(M._DC_TAB, dtype=float).copy()
    bad[2000] = bad[1999] - 1.0
    try:
        M.set_geometry(dc_tab=bad, verbose=False)
        check("T5 tabella non monotona respinta", False, "accettata!")
    except ValueError as e:
        check("T5 tabella non monotona respinta", True, str(e)[:64])
    # Il rifiuto non basta: il modulo deve essere ESATTAMENTE come prima. Se
    # set_geometry assegnasse la tabella prima di controllarla, il chiamante
    # vedrebbe un ValueError e crederebbe che nulla sia cambiato, mentre ogni
    # run successivo userebbe la mappatura scartata.
    post = snapshot()
    for k in FROZEN:
        check(f"T5 atomicita' {k}", post["scalars"][k] == pre["scalars"][k])
    check("T5 atomicita' _DC_TAB",
          bool(np.array_equal(post["DC_TAB"], pre["DC_TAB"])))
    check("T5 atomicita' comoving_distance",
          M.comoving_distance is M._COMOVING_DISTANCE_ANALYTIC,
          "deve essere tornata alla forma analitica")

    print("\n=== T6: omm e dc_tab sono mutuamente esclusivi ===")
    try:
        M.set_geometry(omm=0.3, dc_tab=M._DC_TAB, verbose=False)
        check("T6 respinti insieme", False, "accettati!")
    except ValueError:
        check("T6 respinti insieme", True)

    print("\n=== T8: dc_tab iniettata -> comoving_distance segue la tabella ===")
    # Senza questo, load_desi_random_field()/load_desi_data_field() convertono le
    # posizioni DESI con la cosmologia VECCHIA mentre carve_cutsky() usa gia' la
    # tabella nuova: mock e dati su mappature diverse, nessun errore visibile.
    zt, dct = M.make_dc_tab_ap(alpha_iso=1.04, F_ap=1.02)
    st = M.set_geometry(dc_tab=dct, z_tab=zt, verbose=False)
    check("T8 modo dichiarato", st.get("comoving_distance") == "table-interpolated",
          str(st.get("comoving_distance")))
    for zz in (0.1, 0.25, 0.4):
        a = float(np.atleast_1d(M.comoving_distance([zz]))[0])
        b = float(np.interp(zz, M._Z_TAB, M._DC_TAB))
        check(f"T8 comoving_distance(z={zz})", abs(a - b) < 1e-9,
              f"{a:.4f} contro tabella {b:.4f}")
    check("T8 D_C_ZMIN coerente",
          abs(M.D_C_ZMIN - float(np.interp(0.1, M._Z_TAB, M._DC_TAB))) < 1e-9)
    check("T8 D_C_ZMAX coerente",
          abs(M.D_C_ZMAX - float(np.interp(0.4, M._Z_TAB, M._DC_TAB))) < 1e-9)

    print("\n=== T9: ritorno al fiduciale ripristina la forma analitica ===")
    st = M.set_geometry(omm=0.3175, verbose=False)
    check("T9 modo dichiarato", st.get("comoving_distance") == "analytic",
          str(st.get("comoving_distance")))
    check("T9 valore analitico esatto",
          float(np.atleast_1d(M.comoving_distance([0.1]))[0]) == FROZEN["D_C_ZMIN"],
          f"{float(np.atleast_1d(M.comoving_distance([0.1]))[0]):.12f}")

    print("\n=== T7: stato ripristinato al fiduciale ===")
    restore_fiducial()
    for k, v in FROZEN.items():
        got = getattr(M, k)
        check(f"T7 {k}", got == v, f"{got!r}")

    print("\n" + "=" * 74)
    if fails:
        print(f"{len(fails)} TEST FALLITI:")
        for f in fails:
            print("  - " + f)
        print("\nNON procedere alla Fase 3 finche' T1 non passa a scarto esatto:")
        print("un no-op approssimato rompe la riproducibilita' di ogni numero pubblicato.")
    else:
        print("TUTTI I TEST PASSANO.")
        print("set_geometry() e' un no-op bit-esatto al fiduciale: i numeri di M26 e")
        print("del Paper 1 restano riproducibili per costruzione.")
        print("\nTest piu' profondo, quando serve: far chiamare set_geometry() a")
        print("phase9_sgc_likeforlike.py al posto delle otto assegnazioni a mano, e")
        print("verificare che riproduca 15122 e 18713.0 +/- 197.8. Sono numeri")
        print("PUBBLICATI, non un test costruito per l'occasione.")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            {"failures": fails, "frozen": FROZEN,
             "final_state": {k: getattr(M, k) for k in FROZEN}},
            indent=2), encoding="utf-8")
        print(f"\nscritto in {args.json}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_surrogato_fit.py - il surrogato affine minimax dei quattro angoli.
Item 3.2e, risposta 5 del referee.

COSA CALCOLA
------------
Per ogni angolo C, l'esponente p che minimizza

    max | dc_C(z) - A(p) * dc_fid(z)^p |     su z in [ZMIN, ZMAX]

con A(p) fissato dal minimax interno. E' il miglior membro della famiglia del
Lemma 3 -- f(r) = A r^p -- contro la deformazione VERA dell'angolo. La
differenza che resta e' il terzo canale, quello che la famiglia a due parametri
non rappresenta.

PURA NUMERICA
-------------
Niente cache, niente catalogo, niente box. Due ragioni:

  * il fit e' INVARIANTE DI SCALA: moltiplicare dc per una costante non sposta
    il p ottimo, perche' A la assorbe. Quindi il ri-gauge non entra nel fit;
  * il runner ri-gaugia da solo -- paper2_runner_fase3.py:30-33 fa deform,
    derive_box, c = L_fid/L_punto, set_geometry(dc*c) -- quindi il surrogato
    deve portare SOLO la forma. Il cancello sul cubo costante e' del run, non
    di questo strumento, e qui non si simula.

NESSUNA IMPLEMENTAZIONE NUOVA DEL MINIMAX. Si importa `minimax_alpha` da
paper2_item12a_geom e si usa quella. Una seconda copia darebbe due surrogati
leggermente diversi con lo stesso nome.

I CANCELLI, dichiarati prima dei numeri
---------------------------------------
  G1  A p = 1 il residuo deve coincidere ESATTAMENTE con il minimax a un
      parametro dell'angolo. Se non lo fa, il fitter non sta risolvendo il
      problema che crede di risolvere.
  G2  Sull'angolo NULLO (Om, w0) = fiduciale il fit deve dare p = 1 e residuo 0.
  G3  Il fit deve RIDURRE il residuo (res_2p < res_1p) e p deve cadere dentro
      il bracket usato per la linea B, (0.90, 1.12). Fuori da li' il surrogato
      non e' un punto di griglia comparabile agli altri.
      (Il terzo cancello del disegno -- cubo costante -- e' del run: il runner
      lo impone per costruzione. Segnalato come spostato, non come tolto.)

Sottocomandi
------------
  fit        i quattro angoli. Stampa; scrive solo con --out.
  selftest   angoli sintetici a p noto. Non tocca niente.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

# Bracket della linea B, da paper2_item13_rev2.solve_line.
P_LO, P_HI = 0.90, 1.12

CORNERS = [("C1", 0.2500, -1.2), ("C2", 0.2500, -0.8),
           ("C3", 0.3500, -1.2), ("C4", 0.3500, -0.8)]


def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def attach(srcdir):
    """Importa il modulo di geometria. Nessuna reimplementazione."""
    srcdir = os.path.abspath(srcdir)
    if srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    try:
        import paper2_item12a_geom as G
    except Exception as exc:
        fail("non riesco a importare paper2_item12a_geom da %s: %s" % (srcdir, exc))
    for name in ("minimax_alpha", "dc_from_scratch", "ZMIN", "ZMAX",
                 "OMM_FID", "W0_FID"):
        if not hasattr(G, name):
            fail("paper2_item12a_geom non espone %r: la firma e' cambiata, "
                 "non indovino." % name)
    return G


def brent(f, a, b, tol=1e-14, itmax=200):
    """Bisezione robusta su un intervallo con cambio di segno."""
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return None
    for _ in range(itmax):
        m = 0.5 * (a + b)
        fm = f(m)
        if fa * fm <= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
        if abs(b - a) < tol:
            break
    return 0.5 * (a + b)


def fit_corner(G, z, dc_fid, dc_corner, p_lo=P_LO, p_hi=P_HI, n_grid=241):
    """(p, residuo_2p, alpha_di_p, residuo_1p, curva del residuo).

    Ricerca in due passi: griglia grossa per localizzare il minimo -- il
    residuo minimax e' unimodale in p ma non liscio, quindi una derivata non
    e' affidabile -- poi sezione aurea dentro la terna che lo racchiude.
    """
    m = (z >= G.ZMIN) & (z <= G.ZMAX)
    r = dc_fid[m]
    target = dc_corner[m]

    def res_at(p):
        x = dc_fid ** p
        a, res = G.minimax_alpha(x[m], target)
        return float(res), float(a)

    ps = np.linspace(p_lo, p_hi, n_grid)
    curve = [res_at(float(p))[0] for p in ps]
    j = int(np.argmin(curve))
    if j == 0 or j == len(ps) - 1:
        lo, hi = float(ps[max(0, j - 1)]), float(ps[min(len(ps) - 1, j + 1)])
    else:
        lo, hi = float(ps[j - 1]), float(ps[j + 1])

    # sezione aurea: nessuna derivata, nessuna assunzione di regolarita'
    gr = 0.5 * (np.sqrt(5.0) - 1.0)
    c1, c2 = hi - gr * (hi - lo), lo + gr * (hi - lo)
    f1, f2 = res_at(c1)[0], res_at(c2)[0]
    for _ in range(200):
        if f1 < f2:
            hi, c2, f2 = c2, c1, f1
            c1 = hi - gr * (hi - lo)
            f1 = res_at(c1)[0]
        else:
            lo, c1, f1 = c1, c2, f2
            c2 = lo + gr * (hi - lo)
            f2 = res_at(c2)[0]
        if abs(hi - lo) < 1e-13:
            break
    p = 0.5 * (lo + hi)
    res2, alpha = res_at(p)
    res1, alpha1 = res_at(1.0)
    return p, res2, alpha, res1, (ps.tolist(), curve)


# ---------------------------------------------------------------------------
# I cancelli
# ---------------------------------------------------------------------------

def gates(G, z, dc_fid, rows, verbose=True):
    bad = []

    # G1: a p = 1 il residuo E' il minimax a un parametro, per definizione.
    m = (z >= G.ZMIN) & (z <= G.ZMAX)
    for row in rows:
        dc_c = row["_dc"]
        _, res_direct = G.minimax_alpha(dc_fid[m], dc_c[m])
        if abs(res_direct - row["res_1p_hMpc"]) > 1e-12 * max(1.0, res_direct):
            bad.append("G1 %s: %.12g contro %.12g"
                       % (row["point"], row["res_1p_hMpc"], res_direct))

    # G2: l'angolo nullo deve dare p = 1 e residuo 0.
    p0, res0, _, res0_1p, _ = fit_corner(G, z, dc_fid, dc_fid.copy())
    if abs(p0 - 1.0) > 1e-6 or res0 > 1e-9 or res0_1p > 1e-9:
        bad.append("G2 angolo nullo: p=%.10f res2p=%.3e res1p=%.3e"
                   % (p0, res0, res0_1p))

    # G3: il fit riduce, e p sta nel bracket della linea B.
    for row in rows:
        if not (row["res_2p_hMpc"] < row["res_1p_hMpc"]):
            bad.append("G3 %s: il fit NON riduce (%.4f -> %.4f)"
                       % (row["point"], row["res_1p_hMpc"], row["res_2p_hMpc"]))
        if not (P_LO < row["p"] < P_HI):
            bad.append("G3 %s: p = %.6f fuori dal bracket (%.2f, %.2f)"
                       % (row["point"], row["p"], P_LO, P_HI))

    if verbose:
        print("")
        print("=== CANCELLI ===")
        print("  [%s] G1 a p=1 il residuo e' il minimax a un parametro"
              % ("ok" if not any(b.startswith("G1") for b in bad) else "NO"))
        print("  [%s] G2 angolo nullo: p=1 e residuo 0   (p=%.10f, res=%.2e)"
              % ("ok" if not any(b.startswith("G2") for b in bad) else "NO",
                 p0, res0))
        print("  [%s] G3 il fit riduce, e p sta in (%.2f, %.2f)"
              % ("ok" if not any(b.startswith("G3") for b in bad) else "NO",
                 P_LO, P_HI))
        print("  [--] cubo costante: cancello del RUN, non di questo strumento.")
        print("       paper2_runner_fase3 ri-gaugia con c = L_fid/L_punto, quindi")
        print("       il surrogato porta solo la FORMA e la scala la impone lui.")
        for b in bad:
            print("     %s" % b)
    return bad


# ---------------------------------------------------------------------------
# Sottocomandi
# ---------------------------------------------------------------------------

def cmd_fit(args):
    G = attach(args.src)
    z = np.linspace(0.0, G.ZMAX + 0.05, args.nz)
    dc_fid = np.asarray(G.dc_from_scratch(z, G.OMM_FID, G.W0_FID), float)
    m = (z >= G.ZMIN) & (z <= G.ZMAX)

    print("=" * 78)
    print("Item 3.2e - surrogato affine minimax dei quattro angoli")
    print("=" * 78)
    print("  fiduciale (Om, w0) = (%.4f, %+.1f)   z in [%.2f, %.2f], %d nodi"
          % (G.OMM_FID, G.W0_FID, G.ZMIN, G.ZMAX, args.nz))
    print("  il fit e' INVARIANTE DI SCALA: il ri-gauge non lo sposta.")
    print("")

    rows = []
    for name, omm, w0 in CORNERS:
        dc_c = np.asarray(G.dc_from_scratch(z, omm, w0), float)
        p, res2, alpha, res1, curve = fit_corner(G, z, dc_fid, dc_c,
                                                 args.p_lo, args.p_hi)
        rows.append({
            "schema": "paper2_surrogato_v1",
            "point": name, "point_aff": name + "aff",
            "omm": omm, "w0": w0,
            "p": p,
            "F_pipeline_par_over_perp": p,
            "F_standard_perp_over_par": 1.0 / p,
            "alpha_iso_minimax_at_p": alpha,
            "res_1p_hMpc": res1,
            "res_2p_hMpc": res2,
            "riduzione": (res1 / res2) if res2 > 0 else float("inf"),
            "_dc": dc_c,
        })

    hdr = "  %-4s %7s %5s | %10s | %11s %11s %8s" % (
        "ang", "Om", "w0", "p", "res 1p", "res 2p", "fattore")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for r in rows:
        line = ("  %-4s %7.4f %5.1f | %10.7f | %9.4f   %9.4f   %7.1fx"
                % (r["point"], r["omm"], r["w0"], r["p"],
                   r["res_1p_hMpc"], r["res_2p_hMpc"], r["riduzione"]))
        if args.dx:
            line += "   | %7.4f -> %7.4f vox" % (r["res_1p_hMpc"] / args.dx,
                                                 r["res_2p_hMpc"] / args.dx)
        print(line)
    if not args.dx:
        print("")
        print("  (--dx per la colonna in voxel. Non metto un default: una cella")
        print("   sbagliata darebbe numeri plausibili e falsi.)")

    print("")
    print("  ORDINAMENTO, che e' la firma dichiarata nell'item 3.2e:")
    for k, lab in (("res_1p_hMpc", "a un parametro"), ("res_2p_hMpc", "a due")):
        order = " > ".join(r["point"] for r in sorted(rows, key=lambda x: -x[k]))
        print("    %-16s %s" % (lab + ":", order))

    bad = gates(G, z, dc_fid, rows, verbose=True)
    print("")
    print("  esito cancelli: %s" % ("CLEAN" if not bad else "SPORCO"))

    if args.out:
        if bad:
            fail("cancelli falliti: non scrivo.")
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".",
                    exist_ok=True)
        with open(args.out, "a", encoding="utf-8") as fh:
            for r in rows:
                rec = {k: v for k, v in r.items() if not k.startswith("_")}
                rec["z_nodes"] = int(args.nz)
                rec["p_bracket"] = [args.p_lo, args.p_hi]
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print("  scritto in %s" % args.out)
    return 0 if not bad else 3


# ---------------------------------------------------------------------------
# Selftest: angoli SINTETICI a p noto
# ---------------------------------------------------------------------------

class _FakeG:
    ZMIN, ZMAX = 0.1, 0.4
    OMM_FID, W0_FID = 0.3175, -1.0

    @staticmethod
    def minimax_alpha(r_fid, r_new):
        g = r_new / r_fid
        lo, hi = float(g.min()), float(g.max())
        if hi - lo < 1e-15:
            return 0.5 * (lo + hi), 0.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            d = r_fid * (mid - g)
            if float(d.max()) - float((-d).max()) > 0.0:
                hi = mid
            else:
                lo = mid
        a = 0.5 * (lo + hi)
        return a, float(np.max(np.abs(r_new - a * r_fid)))


def cmd_selftest(args):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    G = _FakeG()
    z = np.linspace(0.0, G.ZMAX + 0.05, 20001)
    dc_fid = 2997.92458 * (z + 0.35 * z ** 2)          # monotona, non lineare
    m = (z >= G.ZMIN) & (z <= G.ZMAX)

    # 1. un angolo DENTRO la famiglia: p si deve recuperare, residuo ~0
    for p_true in (0.9600, 1.0000, 1.0500):
        dc_c = 3.7 * dc_fid ** p_true
        p, res2, a, res1, _ = fit_corner(G, z, dc_fid, dc_c)
        chk("1  angolo dentro la famiglia, p=%.4f: recuperato %.6f, residuo %.2e"
            % (p_true, p, res2),
            abs(p - p_true) < 1e-5 and res2 < 1e-6 * max(1.0, res1))

    # 2. un angolo FUORI dalla famiglia: il fit riduce ma non azzera
    dc_c = dc_fid * (1.0 + 0.004 * np.sin(9.0 * z))
    p, res2, a, res1, _ = fit_corner(G, z, dc_fid, dc_c)
    chk("2  angolo fuori dalla famiglia: il fit riduce senza azzerare",
        0.0 < res2 < res1, "%.4f -> %.4f  (p=%.6f)" % (res1, res2, p))

    # 3. INVARIANZA DI SCALA: e' la ragione per cui il ri-gauge non entra
    p_s, res_s, _, _, _ = fit_corner(G, z, dc_fid, 137.0 * dc_c)
    chk("3  il fit e' invariante di scala: p identico, residuo scalato",
        abs(p_s - p) < 1e-9 and abs(res_s - 137.0 * res2) < 1e-6 * res_s,
        "p %.9f contro %.9f" % (p_s, p))

    # 4. G1: a p=1 il residuo E' il minimax a un parametro
    _, res_direct = G.minimax_alpha(dc_fid[m], dc_c[m])
    chk("4  G1: a p=1 il residuo coincide col minimax a un parametro",
        abs(res1 - res_direct) < 1e-12 * max(1.0, res_direct),
        "%.12g contro %.12g" % (res1, res_direct))

    # 5. G2: angolo nullo
    p0, res0, _, res0_1, _ = fit_corner(G, z, dc_fid, dc_fid.copy())
    chk("5  G2: angolo nullo -> p=1 e residuo 0",
        abs(p0 - 1.0) < 1e-6 and res0 < 1e-9, "p=%.10f res=%.2e" % (p0, res0))

    # 6. il minimo non e' al bordo del bracket su un caso realistico
    ps, curve = fit_corner(G, z, dc_fid, dc_c)[4]
    j = int(np.argmin(curve))
    chk("6  il minimo cade DENTRO il bracket, non al bordo",
        0 < j < len(ps) - 1, "indice %d su %d" % (j, len(ps)))

    # 7. i cancelli respingono, e SOLO per la ragione giusta: le righe di prova
    #    hanno res_1p corretto, cosi' G1 passa e resta acceso solo G3.
    base = {"point": "X", "p": p, "res_1p_hMpc": res1, "_dc": dc_c}
    bad = gates(G, z, dc_fid, [dict(base, res_2p_hMpc=res1 * 2.0)], verbose=False)
    chk("7  G3 respinge un fit che NON riduce, e G1 resta verde",
        any("NON riduce" in b for b in bad)
        and not any(b.startswith("G1") for b in bad), str(bad))
    bad2 = gates(G, z, dc_fid,
                 [dict(base, p=1.30, res_2p_hMpc=res2)], verbose=False)
    chk("7b G3 respinge un p fuori dal bracket, e G1 resta verde",
        any("fuori dal bracket" in b for b in bad2)
        and not any(b.startswith("G1") for b in bad2), str(bad2))
    bad3 = gates(G, z, dc_fid,
                 [dict(base, res_2p_hMpc=res2)], verbose=False)
    chk("7c su una riga sana i tre cancelli passano", not bad3, str(bad3))

    # 8. nessuna reimplementazione nel percorso di fit. Si guarda l'AST, non
    #    si contano stringhe: un conteggio testuale conterebbe se stesso.
    import ast as _ast
    tree = _ast.parse(open(__file__, encoding="utf-8").read())
    target = "minimax" + "_alpha"
    dentro_fake, fuori = [], []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, _ast.FunctionDef) and sub.name == target:
                    dentro_fake.append(node.name)
    for node in tree.body:
        if isinstance(node, _ast.FunctionDef) and node.name == target:
            fuori.append(node.name)
    usa_modulo = any(
        isinstance(n, _ast.Attribute) and n.attr == target
        for n in _ast.walk(tree))
    chk("8  il minimax del percorso di fit viene dal modulo importato",
        usa_modulo and not fuori and dentro_fake == ["_FakeG"],
        "a livello di modulo: %s; dentro classi: %s" % (fuori, dentro_fake))

    print("=== SELFTEST paper2_surrogato_fit ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def main():
    # Le opzioni stanno sul SOTTOCOMANDO, non sul parser di primo livello:
    # argparse vuole le opzioni del padre PRIMA del sottocomando, e definirle in
    # entrambi i posti fa vincere il default del figlio su un valore passato al
    # padre. Un'opzione che viene silenziosamente azzerata e' peggio di
    # un'opzione che non c'e'.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--src", default="src")
    common.add_argument("--nz", type=int, default=90001)
    common.add_argument("--p-lo", type=float, default=P_LO)
    common.add_argument("--p-hi", type=float, default=P_HI)
    common.add_argument("--dx", type=float, default=None,
                        help="cella in h^-1 Mpc, per la colonna in voxel")
    common.add_argument("--out", default=None)

    p = argparse.ArgumentParser(
        description="Surrogato affine minimax dei quattro angoli (item 3.2e)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fit", parents=[common]).set_defaults(func=cmd_fit)
    sub.add_parser("selftest", parents=[common]).set_defaults(func=cmd_selftest)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

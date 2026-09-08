#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_cancello_nu.py

CANCELLO DI UNICITA' DI NU. Da eseguire PRIMA della passata a un punto su v1.

Nel programma esistono due oggetti che si chiamano nu:
  (1) P1.build_nu(delta, mask, M.SIGMA_PX), ricostruito a runtime dalla cache
      dei delta -- la via di paper1_step6_onepoint_betti.py;
  (2) i cubi congelati results/phase8_test2_fields/test2_XXXX.npz, chiave
      'delta', che contengono nu -- la via da cui n1b_spectra_NGC.jsonl ha
      ricavato sigma_in_mask e kurt_in_mask.

N_H1 non distingue le due: la filtrazione di supralivello e' invariante per
rimappatura monotona, quindi "la catena riproduce 28256 cifra per cifra" non
dice nulla su quale delle due abbia i momenti giusti. I momenti sono
esattamente le quantita' che l'invarianza NON protegge, e sono quelle che
servono a 4.2b.

TRE CONFRONTI, perche' separano tre diagnosi:
  A  momenti del cubo congelato   <-> n1b_spectra   : la maschera di n1b
  B  build_nu(delta)              <-> cubo congelato: le due nu, campo su campo
  C  build_nu(delta)              <-> n1b_spectra   : il composto, e il verdetto

SOGLIE, DICHIARATE IL 7 SETTEMBRE 2026 PRIMA DI QUALUNQUE MISURA
  UNICA        scarto relativo <= 1e-5 su sigma e curtosi, su TUTTI gli indici
  CONFLITTO    scarto relativo >  1e-3 su almeno un indice
  NON_DECIDE   in mezzo. La passata non parte lo stesso.
Indici di controllo: 200, 500, 1000, 1805, 1999. I primi quattro sono quelli
gia' usati come controllo da paper1_rev_v2h_monotone.py; il quinto chiude
l'intervallo. Nessuno e' scelto dopo aver visto un numero.

SOLO NGC. Cubi nu congelati per SGC non esistono (il tier 'fields' ha 2000
test2_ + 200 cutsky_ + 2 revision): SGC eredita la validita' dal cammino, non
da un'ancora propria, e questo va scritto nel record.

Non calcola nulla di suo: importa build_nu da paper1_remap e moments da
paper1_step6_onepoint_betti, e un controllo verifica che l'import sia quello
vero. Nessuna scrittura fuori da --out.

USO
    python src\\paper2_cancello_nu.py selftest
    python src\\paper2_cancello_nu.py run --out results\\paper2\\cancello_nu_NGC.jsonl

Uscita: 0 se UNICA, 1 se NON_DECIDE o CONFLITTO, 2 su errore d'uso o dato
mancante. Un dato mancante e' un errore, non un avviso.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# --- dichiarate prima della misura, non modificabili a run in corso ---------
TOL_UNICA = 1e-5
TOL_CONFLITTO = 1e-3
INDICI_CONTROLLO = (200, 500, 1000, 1805, 1999)
REGIONE = "NGC"
SCHEMA = "paper2_cancello_nu_v1"

ROOT_DEFAULT = r"D:\projects\cauchy"


# ---------------------------------------------------------------------------
# primitive
# ---------------------------------------------------------------------------

def rel_diff(a, b):
    """|a-b| / |b|, con b=0 gestito: allora e' |a| se a!=0, altrimenti 0."""
    a = float(a)
    b = float(b)
    if not np.isfinite(a) or not np.isfinite(b):
        return float("inf")
    if b == 0.0:
        return 0.0 if a == 0.0 else abs(a)
    return abs(a - b) / abs(b)


def verdetto(rel_max):
    if not np.isfinite(rel_max):
        return "CONFLITTO"
    if rel_max <= TOL_UNICA:
        return "UNICA"
    if rel_max > TOL_CONFLITTO:
        return "CONFLITTO"
    return "NON_DECIDE"


def peggiore(verdetti):
    """Il verdetto aggregato e' il peggiore, non la media."""
    ordine = {"UNICA": 0, "NON_DECIDE": 1, "CONFLITTO": 2}
    return max(verdetti, key=lambda v: ordine[v])


def leggi_n1b(path, indici):
    """Estrae i record richiesti. Un indice assente e' un errore."""
    voluti = set(int(i) for i in indici)
    trovati = {}
    with Path(path).open("r", encoding="utf-8") as fh:
        for riga in fh:
            riga = riga.strip()
            if not riga:
                continue
            rec = json.loads(riga)
            i = int(rec["idx"])
            if i in voluti:
                trovati[i] = rec
    mancanti = sorted(voluti - set(trovati))
    if mancanti:
        raise KeyError("indici assenti da %s: %s" % (path, mancanti))
    return trovati


def percorsi(root):
    """Tutti i percorsi in un posto solo, cosi' il selftest puo' vederli."""
    root = Path(root)
    return {
        "n1b": root / "results" / "paper1" / ("n1b_spectra_%s.jsonl" % REGIONE),
        "delta": root / "data" / "processed" / "paper1_mock_deltas" / REGIONE,
        "nu": root / "results" / "phase8_test2_fields",
        "desi_raw": root / "data" / "raw" / "desi_dr1",
        "phase6": root / "data" / "processed" / "phase6_fields",
    }


def nome_delta(idx):
    return "delta_%04d.npy" % int(idx)


def nome_nu(idx):
    return "test2_%04d.npz" % int(idx)


def carica_moduli(root):
    """Import dei moduli di progetto. Solo qui, mai nel selftest."""
    sys.path.insert(0, str(Path(root) / "src"))
    import phase8_cutsky_mocks as M          # noqa: E402
    import paper1_remap as P1                # noqa: E402
    import paper1_step6_onepoint_betti as S6  # noqa: E402
    # l'import e' quello vero, non un omonimo locale
    if P1.build_nu.__module__ != "paper1_remap":
        raise RuntimeError("build_nu non viene da paper1_remap: %s"
                           % P1.build_nu.__module__)
    if S6.moments.__module__ != "paper1_step6_onepoint_betti":
        raise RuntimeError("moments non viene da step6: %s"
                           % S6.moments.__module__)
    return M, P1, S6


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def run(root, out_path, indici=INDICI_CONTROLLO):
    root = Path(root).resolve()
    M, P1, S6 = carica_moduli(root)

    P = percorsi(root)
    reg_n1b, dir_delta, dir_nu = P["n1b"], P["delta"], P["nu"]
    for p in (reg_n1b, dir_delta, dir_nu):
        if not p.exists():
            raise FileNotFoundError(str(p))

    print("=" * 78)
    print("CANCELLO DI UNICITA' DI NU  |  %s  |  indici %s"
          % (REGIONE, list(indici)))
    print("soglie dichiarate: UNICA <= %.0e   CONFLITTO > %.0e"
          % (TOL_UNICA, TOL_CONFLITTO))
    print("=" * 78)

    n1b = leggi_n1b(reg_n1b, indici)

    G = P1.setup_region(M, REGIONE, P["desi_raw"], P["phase6"])
    mask = G["mask"]
    n_vox = int(mask.sum())
    print("  maschera: %d voxel   sigma_px = %.6f" % (n_vox, float(M.SIGMA_PX)))

    righe = []
    verdetti = []
    for idx in indici:
        fp_d = dir_delta / nome_delta(idx)
        fp_n = dir_nu / nome_nu(idx)
        if not fp_d.is_file():
            raise FileNotFoundError(str(fp_d))
        if not fp_n.is_file():
            raise FileNotFoundError(str(fp_n))

        delta = np.load(fp_d).astype(np.float64)
        nu_calc = P1.build_nu(delta, mask, M.SIGMA_PX)
        with np.load(fp_n) as Z:
            if "delta" not in Z.files:
                raise KeyError("%s non ha la chiave 'delta' (che contiene nu): %s"
                               % (fp_n.name, Z.files))
            nu_frz = np.asarray(Z["delta"])

        if nu_calc.shape != nu_frz.shape:
            raise ValueError("forme diverse: %s contro %s"
                             % (nu_calc.shape, nu_frz.shape))

        vc = nu_calc[mask].astype(np.float64)
        vf = nu_frz[mask].astype(np.float64)
        d = vc - vf
        max_abs = float(np.abs(d).max())
        n_diff = int((d != 0.0).sum())
        scala = float(vf.std())
        rel_campo = max_abs / scala if scala > 0 else float("inf")

        mc = S6.moments(vc)
        mf = S6.moments(vf)
        rec = n1b[idx]

        # A: cubo congelato contro registro
        A_s = rel_diff(mf["std"], rec["sigma_in_mask"])
        A_k = rel_diff(mf["kurt_excess"], rec["kurt_in_mask"])
        # C: build_nu contro registro -- il verdetto
        C_s = rel_diff(mc["std"], rec["sigma_in_mask"])
        C_k = rel_diff(mc["kurt_excess"], rec["kurt_in_mask"])

        v = verdetto(max(C_s, C_k))
        verdetti.append(v)

        riga = {
            "schema": SCHEMA, "utc": datetime.now(timezone.utc).isoformat(),
            "region": REGIONE, "idx": int(idx), "verdetto": v,
            "n_voxel_maschera": n_vox, "sigma_px": float(M.SIGMA_PX),
            "A_congelato_vs_n1b": {"rel_sigma": A_s, "rel_kurt": A_k},
            "B_buildnu_vs_congelato": {"max_abs": max_abs,
                                       "n_celle_diverse": n_diff,
                                       "frac_celle_diverse": n_diff / n_vox,
                                       "rel_su_sigma": rel_campo},
            "C_buildnu_vs_n1b": {"rel_sigma": C_s, "rel_kurt": C_k},
            "misure": {"buildnu": {"sigma": mc["std"], "kurt": mc["kurt_excess"],
                                   "p01": mc["p01"], "p99": mc["p99"]},
                       "congelato": {"sigma": mf["std"], "kurt": mf["kurt_excess"],
                                     "p01": mf["p01"], "p99": mf["p99"]},
                       "n1b": {"sigma": float(rec["sigma_in_mask"]),
                               "kurt": float(rec["kurt_in_mask"])}},
            "nota_sgc": ("cubi nu congelati per SGC inesistenti: SGC eredita "
                         "la validita' dal cammino, non da un'ancora propria"),
        }
        righe.append(riga)

        print("  idx %4d  %-10s | A s=%.2e k=%.2e | B max|d|=%.3e celle=%.4f%% "
              "| C s=%.2e k=%.2e"
              % (idx, v, A_s, A_k, max_abs, 100.0 * n_diff / n_vox, C_s, C_k))

    finale = peggiore(verdetti)
    sommario = {
        "schema": SCHEMA + "_sommario",
        "utc": datetime.now(timezone.utc).isoformat(),
        "region": REGIONE, "indici": list(indici),
        "tol_unica": TOL_UNICA, "tol_conflitto": TOL_CONFLITTO,
        "verdetto": finale,
        "rel_max_C": max(max(r["C_buildnu_vs_n1b"]["rel_sigma"],
                             r["C_buildnu_vs_n1b"]["rel_kurt"]) for r in righe),
        "rel_max_A": max(max(r["A_congelato_vs_n1b"]["rel_sigma"],
                             r["A_congelato_vs_n1b"]["rel_kurt"]) for r in righe),
        "max_abs_B": max(r["B_buildnu_vs_congelato"]["max_abs"] for r in righe),
    }
    righe.append(sommario)

    if out_path:
        op = Path(out_path)
        op.parent.mkdir(parents=True, exist_ok=True)
        with op.open("a", encoding="utf-8") as fh:   # append-only
            for r in righe:
                fh.write(json.dumps(r, ensure_ascii=True) + "\n")
        print("\n%d record appesi a %s" % (len(righe), op))

    print("\nVERDETTO: %s   (rel max C = %.3e, A = %.3e, max|d| B = %.3e)"
          % (finale, sommario["rel_max_C"], sommario["rel_max_A"],
             sommario["max_abs_B"]))
    if finale == "UNICA":
        print("build_nu e' canonica. La passata a un punto puo' essere scritta.")
        return 0
    print("La passata NON parte. Il conflitto va registrato e risolto prima.")
    return 1


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def _momenti_riferimento(v):
    """Formula di n1b_spectral:172-175, riscritta QUI e solo per il confronto."""
    v = np.asarray(v, dtype=np.float64)
    sd = float(v.std())
    k = float(((v - v.mean()) ** 4).mean() / sd ** 4 - 3.0) if sd > 0 else np.nan
    return sd, k


def selftest(root=ROOT_DEFAULT):
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, n))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, n, det))

    print("selftest paper2_cancello_nu")

    # soglie e indici: sono la dichiarazione, non un parametro
    chk("tolleranze dichiarate", TOL_UNICA == 1e-5 and TOL_CONFLITTO == 1e-3,
        (TOL_UNICA, TOL_CONFLITTO))
    chk("indici di controllo dichiarati",
        INDICI_CONTROLLO == (200, 500, 1000, 1805, 1999), INDICI_CONTROLLO)
    chk("gli indici stanno tutti in 200..1999 (fuori dal blocco pilota)",
        all(200 <= i <= 1999 for i in INDICI_CONTROLLO))

    # rel_diff
    chk("rel_diff normale", abs(rel_diff(1.0 + 1e-6, 1.0) - 1e-6) < 1e-12)
    chk("rel_diff con b=0 e a=0", rel_diff(0.0, 0.0) == 0.0)
    chk("rel_diff con b=0 e a!=0", rel_diff(3.0, 0.0) == 3.0)
    chk("rel_diff con nan e' infinito", rel_diff(float("nan"), 1.0) == float("inf"))

    # verdetto
    chk("sotto soglia -> UNICA", verdetto(9e-6) == "UNICA")
    chk("sopra soglia -> CONFLITTO", verdetto(2e-3) == "CONFLITTO")
    chk("in mezzo -> NON_DECIDE", verdetto(1e-4) == "NON_DECIDE")
    chk("esattamente 1e-5 -> UNICA", verdetto(1e-5) == "UNICA")
    chk("esattamente 1e-3 -> NON_DECIDE", verdetto(1e-3) == "NON_DECIDE")
    chk("nan -> CONFLITTO", verdetto(float("nan")) == "CONFLITTO")

    # aggregazione: il peggiore, non la maggioranza
    chk("un solo CONFLITTO domina quattro UNICA",
        peggiore(["UNICA"] * 4 + ["CONFLITTO"]) == "CONFLITTO")
    chk("un NON_DECIDE domina gli UNICA",
        peggiore(["UNICA", "NON_DECIDE", "UNICA"]) == "NON_DECIDE")

    # lettura del registro
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "n1b.jsonl"
        f.write_text("\n".join(
            json.dumps({"idx": i, "sigma_in_mask": 2.0 + i * 1e-4,
                        "kurt_in_mask": 2.7}) for i in (200, 500, 1000)) + "\n",
            encoding="utf-8")
        got = leggi_n1b(f, [200, 1000])
        chk("leggi_n1b trova gli indici richiesti",
            set(got) == {200, 1000} and got[200]["sigma_in_mask"] == 2.02, got)
        try:
            leggi_n1b(f, [200, 1805])
            chk("indice assente solleva", False, "non ha sollevato")
        except KeyError as e:
            chk("indice assente solleva", "1805" in str(e), str(e))

    # percorsi: il difetto che il selftest non vedeva
    P = percorsi("/base")
    chk("percorsi restituisce solo Path",
        all(isinstance(v, Path) for v in P.values()), P)
    chk("il registro n1b ha il nome giusto",
        P["n1b"].name == "n1b_spectra_NGC.jsonl", P["n1b"].name)
    chk("la cache dei delta e' per emisfero",
        P["delta"].name == "NGC" and P["delta"].parent.name == "paper1_mock_deltas",
        str(P["delta"]))
    chk("i cubi nu stanno in phase8_test2_fields",
        P["nu"].name == "phase8_test2_fields", P["nu"].name)
    chk("nome_delta e nome_nu sono a quattro cifre",
        nome_delta(200) == "delta_0200.npy" and nome_nu(1805) == "test2_1805.npz",
        (nome_delta(200), nome_nu(1805)))
    chk("i percorsi si compongono senza rompersi",
        str(P["delta"] / nome_delta(1999)).endswith("delta_1999.npy"),
        str(P["delta"] / nome_delta(1999)))

    # la formula dei momenti che uso e' quella di n1b
    rng = np.random.default_rng(0)
    v = rng.normal(size=50000) * 2.3 + 1.1
    sd_ref, k_ref = _momenti_riferimento(v)
    try:
        sys.path.insert(0, str(Path(root) / "src"))
        import paper1_step6_onepoint_betti as S6
        m = S6.moments(v)
        chk("moments di step6 == sigma di n1b",
            abs(m["std"] - sd_ref) <= 1e-12 * abs(sd_ref), (m["std"], sd_ref))
        chk("moments di step6 == curtosi di n1b",
            abs(m["kurt_excess"] - k_ref) <= 1e-12 * abs(k_ref),
            (m["kurt_excess"], k_ref))
        chk("moments espone p01, che il driver di step6 scarta",
            "p01" in m and np.isfinite(m["p01"]), sorted(m))
    except ImportError as e:
        chk("step6 importabile per il confronto di formula", False, str(e))
        chk("(saltato)", False, "step6 non importabile")
        chk("(saltato)", False, "step6 non importabile")

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="esegue il cancello")
    r.add_argument("--root", default=ROOT_DEFAULT)
    r.add_argument("--out", default=None)
    st = sub.add_parser("selftest", help="controlli interni")
    st.add_argument("--root", default=ROOT_DEFAULT)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return run(a.root, a.out)
    if a.cmd == "selftest":
        return selftest(a.root)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

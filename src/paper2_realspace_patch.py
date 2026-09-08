#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_realspace_patch.py — §3.8: la linea B in spazio reale, con il cancello D5c.

COSA MISURA
  Il record 18 riformula la predizione 2 a RAPPORTO: sotto trattamento (A) in
  SPAZIO REALE, il residuo DOPO la sottrazione del termine (e) e' dell'ordine
  dei canali di registrazione residui — tiling e spostamento di griglia — e NON
  dell'ordine della risposta in spazio di redshift. FALSIFICATA se il residuo in
  spazio reale dopo (e) raggiunge almeno META' di quello in spazio di redshift
  dopo (e), in almeno meta' dei punti misurati, in ENTRAMBI gli emisferi.

COME
  Azzerando v_los prima della riga 681 di phase8_cutsky_mocks.py. NON saltando
  il calcolo: v_los viene posto a zero e l'espressione resta la stessa, cosi' il
  percorso di codice e' identico e l'unica differenza e' il VALORE. Con v_los=0
  si ha z_obs = z_cosmo esattamente (somma di 0.0), quindi dC_rsd e' il
  round-trip delle tabelle, che il record 18 ha misurato essere l'identita' a
  1.9e-16.

CINQUE MODIFICHE
  A  phase8: flag di modulo REAL_SPACE, default False. Con False il
     comportamento e' invariato bit a bit per i ~30 script che lo importano.
  B  phase8: v_los azzerato se REAL_SPACE, espressione invariata.
  C  runner: --real-space, che accende il flag e finisce nel record.
  D  runner: la chiave di ripartenza include real_space, altrimenti un run in
     spazio reale salterebbe tutte le realizzazioni gia' fatte in spazio di
     redshift, o peggio le confonderebbe.
  E  runner: CANCELLO D5c, PF.clipped_per_face su pos_sel, zero, arresto duro
     (record 17). Vale per ENTRAMBI i trattamenti, quindi entra qui e serve
     anche al trattamento (B).

USO PREVISTO
  python src\\paper2_runner_fase3_mock.py run --region NGC --n 200 \\
      --points FID B1 B2 B4 B5 B6 --real-space \\
      --out results\\paper2\\fase3_mock_realspace.jsonl
  e lo stesso per SGC. Registro SEPARATO: il trattamento (B) avra' il suo, e
  nessuno dei due tocca fase3_mock.jsonl.

Uso di questo patcher:
    python src\\paper2_realspace_patch.py selftest
    python src\\paper2_realspace_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

FILES = {"phase8": os.path.join("src", "phase8_cutsky_mocks.py"),
         "runner": os.path.join("src", "paper2_runner_fase3_mock.py")}

A_OLD = '''C_KMS     = 299792.458          # km/s'''

A_NEW = '''C_KMS     = 299792.458          # km/s

# --- §3.8, 1 set 2026 -------------------------------------------------------
# Linea B in spazio reale. Con REAL_SPACE = True, carve_cutsky azzera v_los
# prima di costruire z_obs. Il default False lascia il comportamento invariato
# BIT A BIT per ogni script che importa questo modulo: l'unica differenza e' il
# VALORE di v_los, non il percorso di codice.
# Con v_los = 0 si ha z_obs = z_cosmo esattamente, perche' si somma 0.0; quindi
# dC_rsd e' il round-trip delle tabelle, misurato identita' a 1.9e-16
# (emendamento 18). Restano attivi il canale voxel, la registrazione del tiling
# e lo spostamento di griglia: la predizione del record 18 e' a RAPPORTO, non a
# soglia assoluta, proprio per questo.
REAL_SPACE = False'''

B_OLD = '''                v_los = np.sum(V * rhat, axis=1)                 # km/s
                z_obs = z_cosmo + (1.0 + z_cosmo) * v_los / C_KMS'''

B_NEW = '''                v_los = np.sum(V * rhat, axis=1)                 # km/s
                if REAL_SPACE:
                    # §3.8: si AZZERA v_los, non si salta il calcolo. Cosi'
                    # l'espressione sotto e' la stessa e la differenza fra i due
                    # trattamenti e' un valore, non un ramo.
                    v_los = np.zeros_like(v_los)
                z_obs = z_cosmo + (1.0 + z_cosmo) * v_los / C_KMS'''

C_OLD = '''            q.add_argument("--carve-reseed", type=int, default=None,
                           help="termine (c) del 3.3: cambia SOLO il seme del "
                                "carving, HOD identico, geometria ferma")
        else:
            q.set_defaults(carve_reseed=None)'''

C_NEW = '''            q.add_argument("--carve-reseed", type=int, default=None,
                           help="termine (c) del 3.3: cambia SOLO il seme del "
                                "carving, HOD identico, geometria ferma")
            q.add_argument("--real-space", action="store_true",
                           help="§3.8: azzera v_los, cioe' niente RSD. Usare un "
                                "--out SEPARATO: e' una misura diversa, non una "
                                "continuazione di quella in spazio di redshift")
        else:
            q.set_defaults(carve_reseed=None, real_space=False)'''

D_OLD = '''                    done.add((r.get("region"), r.get("index"),
                              r.get("carve_reseed"),
                              tuple(sorted(r.get("points", {}))),
                              tuple(r.get("erosions", EROSIONS_MOCK))))'''

D_NEW = '''                    # real_space entra nella chiave: senza, un run in spazio
                    # reale salterebbe le realizzazioni gia' fatte in spazio di
                    # redshift, che sono una MISURA DIVERSA. Con --out separato
                    # non succede, ma la chiave non deve dipendere da quella
                    # disciplina esterna.
                    done.add((r.get("region"), r.get("index"),
                              r.get("carve_reseed"),
                              tuple(sorted(r.get("points", {}))),
                              tuple(r.get("erosions", EROSIONS_MOCK)),
                              bool(r.get("real_space", False))))'''

E_OLD = '''        if (reg, kk, a.carve_reseed, tuple(sorted(order)),
                tuple(ero)) in done:'''

E_NEW = '''        if (reg, kk, a.carve_reseed, tuple(sorted(order)),
                tuple(ero), bool(getattr(a, "real_space", False))) in done:'''

F_OLD = '''        pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z, nz_target, rng)
        if pos_sel is None or len(pos_sel) < 100:'''

F_NEW = '''        pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z, nz_target, rng)
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
        if pos_sel is not None and len(pos_sel) >= 100:
            _cl = PF.clipped_per_face(pos_sel, M.BOX_MIN, M.BOX_SIZE)
            if _cl["n_clipped"]:
                sys.exit(f"[FATAL] D5c: {region}/{name}/mock {kk}: "
                         f"{_cl['n_clipped']} posizioni fuori dal cubo. "
                         f"Dettaglio: {_cl}. Il punto non si misura "
                         f"(emendamento 17).")
        if pos_sel is None or len(pos_sel) < 100:'''

G_OLD = '''        if a.carve_reseed is not None:
            rec["carve_reseed"] = int(a.carve_reseed)'''

G_NEW = '''        if a.carve_reseed is not None:
            rec["carve_reseed"] = int(a.carve_reseed)
        if getattr(a, "real_space", False):
            rec["real_space"] = True'''

EDITS = {
    "phase8": [("A  flag REAL_SPACE di modulo", A_OLD, A_NEW),
               ("B  v_los azzerato, espressione invariata", B_OLD, B_NEW)],
    "runner": [("C  --real-space", C_OLD, C_NEW),
               ("D  real_space nella chiave di ripartenza", D_OLD, D_NEW),
               ("E  e nel confronto della chiave", E_OLD, E_NEW),
               ("F  CANCELLO D5c su pos_sel", F_OLD, F_NEW),
               ("G  real_space nel record", G_OLD, G_NEW)],
}


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_one(s, label):
    for name, old, new in EDITS[label]:
        if s.count(old) != 1:
            fail("ancora non unica in %s per '%s' (occorrenze=%d)"
                 % (label, name, s.count(old)))
        s = s.replace(old, new, 1)
    return s


def _nomi_liberi(src, funcname):
    """Nomi usati in una funzione e legati da nessuna parte: parametri, locali,
    import interni, target di for/with/except, comprehension, globali del modulo
    e builtins. Quel che resta e' un NameError che aspetta di succedere.

    `ast.parse` non lo vede: la sintassi e' valida, il nome no."""
    import ast
    import builtins
    tree = ast.parse(src)
    glob = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    glob |= {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            glob |= {(al.asname or al.name.split(".")[0]) for al in n.names}
        elif isinstance(n, ast.Assign):
            glob |= {t.id for t in ast.walk(n) if isinstance(t, ast.Name)}
    fn = next((f for f in ast.walk(tree)
               if isinstance(f, ast.FunctionDef) and f.name == funcname), None)
    if fn is None:
        return {"<funzione %s non trovata>" % funcname}
    bound = set(glob) | set(dir(builtins))
    a = fn.args
    for arg in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
        bound.add(arg.arg)
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            bound.add(extra.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound |= {(al.asname or al.name.split(".")[0]) for al in node.names}
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
            for arg in list(node.args.args) + list(node.args.kwonlyargs):
                bound.add(arg.arg)
        elif isinstance(node, (ast.comprehension,)):
            bound |= {t.id for t in ast.walk(node.target) if isinstance(t, ast.Name)}
    usati = {node.id for node in ast.walk(fn)
             if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    return usati - bound


def _parses(src):
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        print("      [sintassi] %s" % exc)
        return False


def selftest(paths):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # 1-2: l'argomento fisico, verificato numericamente e non asserito
    z = 0.2345678901234
    z_obs_rs = z + (1.0 + z) * 0.0 / 299792.458
    chk("1  con v_los = 0, z_obs == z_cosmo ESATTAMENTE", z_obs_rs == z,
        "diff %r" % (z_obs_rs - z))
    try:
        import numpy as np
        zt = np.linspace(0.0, 0.6, 4001)
        dct = 2997.92458 * zt * (1.0 - 0.75 * zt + 0.5 * zt * zt)
        probe = np.linspace(dct[1], dct[-2], 20001)
        back = np.interp(np.interp(probe, dct, zt), zt, dct)
        rel = float(np.max(np.abs(back - probe) / probe))
        chk("2  e il round-trip delle tabelle e' l'identita'", rel < 1e-12,
            "rel max %.2e" % rel)
    except Exception as exc:
        chk("2  round-trip", False, str(exc))

    n = 3
    for label, path in paths.items():
        ok = os.path.isfile(path)
        chk("%-2d %s presente" % (n, label), ok, path)
        n += 1
        if not ok:
            continue
        s = read(path)
        already = ("REAL_SPACE" in s) or ("--real-space" in s) or ("D5c" in s)
        chk("%-2d %s: idempotenza" % (n, label), not already)
        n += 1
        for name, old, new in EDITS[label]:
            c = s.count(old)
            chk("%-2d %s: ancora %s" % (n, label, name), c == 1, "occorrenze=%d" % c)
            n += 1

    if all(c[1] for c in checks):
        out8 = apply_one(read(paths["phase8"]), "phase8")
        outr = apply_one(read(paths["runner"]), "runner")
        chk("%-2d entrambi restano Python valido" % n,
            _parses(out8) and _parses(outr)); n += 1
        chk("%-2d il default e' False: nessuno dei ~30 script cambia" % n,
            "REAL_SPACE = False" in out8); n += 1
        chk("%-2d v_los e' AZZERATO, non saltato: l'espressione e' la stessa" % n,
            out8.count("z_obs = z_cosmo + (1.0 + z_cosmo) * v_los / C_KMS") == 1
            and "np.zeros_like(v_los)" in out8); n += 1
        chk("%-2d D5c: soglia zero e arresto duro, non un avviso" % n,
            ('if _cl["n_clipped"]:' in outr) and ("sys.exit" in outr)
            and ("per faccia" in outr)); n += 1
        chk("%-2d D5c: PF importato DENTRO one_mock, non assunto in scope" % n,
            "PF.clipped_per_face" in outr
            and "import paper2_phase3_preflight as PF" in outr); n += 1
        # Il controllo che serviva davvero: ast.parse dice che il file e'
        # sintatticamente valido, non che i nomi esistano. La prima stesura
        # usava PF, reg e name senza che PF e reg fossero in scope dentro
        # one_mock: sarebbe esploso con NameError al primo punto.
        libere = _nomi_liberi(outr, "one_mock")
        chk("%-2d SCOPE: ogni nome usato in one_mock e' legato" % n,
            not libere, "liberi: %s" % ", ".join(sorted(libere)) if libere else ""); n += 1
        chk("%-2d real_space e' nella chiave E nel record" % n,
            outr.count('bool(r.get("real_space", False))') == 1
            and 'rec["real_space"] = True' in outr); n += 1
        chk("%-2d chiave scritta e chiave letta hanno la stessa arita' (6)" % n,
            outr.count('bool(getattr(a, "real_space", False))) in done') == 1); n += 1
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_realspace_patch ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def cmd_apply(a):
    paths = {k: getattr(a, k) for k in FILES}
    if selftest(paths):
        print("")
        fail("selftest fallito: nessuna scrittura, su nessuno dei due file.")
    print("")
    for label, path in paths.items():
        s = read(path)
        out = apply_one(s, label)
        diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                         fromfile=label + " prima",
                                         tofile=label + " dopo", n=2))
        print("=== %s: %s (%d righe di diff) ===" % (label, path, len(diff)))
        sys.stdout.write("".join(diff))
        print("")
        if a.write:
            bak = path + ".pre_realspace"
            if not os.path.exists(bak):
                with open(bak, "w", encoding="utf-8", newline="") as f:
                    f.write(s)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(out)
            os.replace(tmp, path)
            print("[OK] %s aggiornato (backup in %s)" % (path, bak))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    print(r"""
PRIMA di lanciare, nell'ordine:
  python src\\paper2_runner_fase3_mock.py selftest
  python src\\paper2_fase3_analisi.py selftest
  python src\\paper2_runner_fase3_mock.py smoke --region NGC

Lo smoke e' il controllo che conta: gira SENZA --real-space e deve dare gli
stessi numeri di prima. Se cambiano, il flag non e' inerte e non si prosegue.

POI il §3.8, sulla sola linea B, registro SEPARATO:
  python src\\paper2_runner_fase3_mock.py run --region NGC --n 200 \\
      --points FID B1 B2 B4 B5 B6 --real-space \\
      --out results\\paper2\\fase3_mock_realspace.jsonl
  python src\\paper2_runner_fase3_mock.py run --region SGC --n 200 \\
      --points FID B1 B2 B4 B5 B6 --real-space \\
      --out results\\paper2\\fase3_mock_realspace.jsonl

Sei punti invece di dodici: ~6 h per emisfero. Il registro NON e'
fase3_mock.jsonl, cosi' il trattamento (B) potra' avere il suo e nessuno dei
due sovrascrive niente.

Se D5c ferma un punto, NON e' un difetto del run: e' il cancello che fa quel
che deve. Riporta il messaggio con i conteggi per faccia.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="§3.8 linea B in spazio reale, con D5c")
    for k, v in FILES.items():
        p.add_argument("--" + k, default=v)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(
        func=lambda a: 1 if selftest({k: getattr(a, k) for k in FILES}) else 0)
    ap = sub.add_parser("apply")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(func=cmd_apply)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

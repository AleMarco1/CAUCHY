#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_fixedobs_patch.py — trattamento (B), osservabili fisse. Record 16, 17, 21, 23.

COSA MISURA
  Il §1 del referee: se il fattore 2.10-5.56 fra Delta_mock e Delta_dati e'
  interamente un artefatto del trattamento (A), allora sotto (B) il rapporto
  scende verso 1 e Delta_D verso zero. Predizione dichiarata nel record 16,
  denominatore nel record 17.

COME
  (rhat, z_obs) si congelano al FIDUCIALE, dopo il Pass 2 di carve_cutsky, e per
  ogni punto si ricalcola solo r' = rhat * D_C^(g)(z_obs). La SELEZIONE resta
  quella del fiduciale: niente ricampionamento n(z), niente ri-seed, niente
  ricostruzione dei tagli. E' questo che rende (B) il gemello del lato dati,
  dove (RA, DEC, z) non dipendono dalla cosmologia d'analisi.

SEI MODIFICHE
  A  phase8: carve_cutsky prende `capture=None`. Con None non cambia NULLA.
  B  phase8: accumula rhat accanto a P_rsd e z_obs, SOLO se capture e' chiesto.
  C  phase8: a fine Pass 2 riempie capture con rhat e z_obs della selezione.
  D  runner: one_mock prende `fixed_observables=False`; se vero costruisce la
     cache al fiduciale, esegue D5a, e nel ciclo rimappa invece di carvare.
  E  runner: --fixed-observables, nella chiave di ripartenza e nel record.
  F  runner: cmd_run passa il flag a one_mock. NON cmd_smoke: lo smoke resta
     nel trattamento (A), cosi' continua a fare da controllo di non-regressione.

D5a, E COSA VERIFICA DAVVERO
  Al fiduciale, `rhat * interp(z_obs, _Z_TAB, _DC_TAB)` deve essere BIT-IDENTICO
  al `pos_sel` che carve_cutsky ha appena restituito. Va detto con precisione:
  il confronto avviene NELLO STESSO PROCESSO, fra l'uscita del percorso normale
  e la ricostruzione dalla cache. Non e' un cancello sul run, e' un cancello
  sulla COSTRUZIONE DELLA CACHE. E' comunque il controllo giusto - se rhat o
  z_obs fossero presi nel punto sbagliato del Pass 2, o troncati, o riordinati,
  fallirebbe - ma la sua natura non va lasciata implicita.

  La bit-identita' e' raggiungibile perche' le due strade fanno la STESSA
  moltiplicazione elementwise sugli STESSI bit: np.interp e' elementwise, quindi
  calcolarla sull'array intero e poi sottoinsiemarlo, o calcolarla direttamente
  sul sottoinsieme, da' gli stessi valori. Non e' il caso del record 14, dove il
  confronto era fra comoving_distance nativa e tabella iniettata.

D5b
  Al fiduciale, la media su 200 deve riprodurre 35423.575 / 31889.925 (NGC) e
  18694.420 / 16477.950 (SGC), valori del record 21. Non e' verificabile dentro
  one_mock, che vede una realizzazione per volta: si verifica in analisi, sul
  registro finito. Il patcher lo scrive nell'intestazione del run e nel record,
  cosi' il confronto non dipende da chi se lo ricorda.

D5c
  Resta in modalita' 'measure' (record 23): misura e registra, non ferma.

USO PREVISTO
  python src\\paper2_runner_fase3_mock.py run --region NGC --n 200 \\
      --points FID B1 B2 B4 B5 B6 --fixed-observables \\
      --out results\\paper2\\fase3_mock_fixedobs.jsonl
  e lo stesso per SGC. Registro SEPARATO da fase3_mock.jsonl e da
  fase3_mock_realspace.jsonl.

  DA APPLICARE A RUN FERMO: tocca il runner e phase8.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

FILES = {"phase8": os.path.join("src", "phase8_cutsky_mocks.py"),
         "runner": os.path.join("src", "paper2_runner_fase3_mock.py")}

A_OLD = '''def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng):'''

A_NEW = '''def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng, capture=None):'''

B_OLD = '''    cand_P, cand_z = [], []'''

B_NEW = '''    cand_P, cand_z = [], []
    # §1 / trattamento (B), 1 set 2026. Con capture=None questa lista resta
    # vuota e non viene mai toccata: il percorso di default e' invariato bit a
    # bit e non paga memoria. Serve solo a chi costruisce la cache a osservabili
    # fisse, che ha bisogno di rhat oltre che di P_rsd e z_obs.
    cand_r = []'''

C_OLD = '''                cand_P.append(P_rsd[inmask])
                cand_z.append(z_obs_s[inmask])'''

C_NEW = '''                cand_P.append(P_rsd[inmask])
                cand_z.append(z_obs_s[inmask])
                if capture is not None:
                    cand_r.append(rhat[zsel][inmask])'''

D_OLD = '''    keep = rng.random(len(z_cand)) < p
    return P_cand[keep]'''

D_NEW = '''    keep = rng.random(len(z_cand)) < p
    if capture is not None:
        # DOPO il Pass 2, cioe' sulla selezione finale, e nello STESSO ordine di
        # riga di quel che si restituisce: `keep` e' applicato agli stessi array.
        capture["rhat"] = np.vstack(cand_r)[keep]
        capture["z_obs"] = z_cand[keep]
    return P_cand[keep]'''

E_OLD = '''def one_mock(M, P1, T2, F3, region, geoms, kk, nz_z, nz_target, order,
             frozen_delta_dir=None, carve_reseed=None,
             erosions=EROSIONS_MOCK):'''

E_NEW = '''def one_mock(M, P1, T2, F3, region, geoms, kk, nz_z, nz_target, order,
             frozen_delta_dir=None, carve_reseed=None,
             erosions=EROSIONS_MOCK, fixed_observables=False):'''

F_OLD = '''    res = {}
    for name in order:
        g = geoms[name]'''

F_NEW = '''    # --- TRATTAMENTO (B): la cache al fiduciale, e il cancello D5a -----------
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
        g = geoms[name]'''

G_OLD = '''        rng.bit_generator.state = state_after_hod  # APPAIAMENTO: stesso stato
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z, nz_target, rng)'''

G_NEW = '''        rng.bit_generator.state = state_after_hod  # APPAIAMENTO: stesso stato
        if _fixed is None:
            pos_sel = M.carve_cutsky(pos_gal, vel_gal, g["mask"], nz_z,
                                     nz_target, rng)
        else:
            # (B): si rimappa e basta. Nessun ricampionamento n(z), nessun
            # ri-seed, nessuna ricostruzione della selezione o dei tagli in z.
            # n_sel sara' identico a ogni punto: e' atteso, ed e' il controllo
            # piu' semplice che la modalita' stia facendo quel che dice.
            _dcp = np.interp(np.clip(_fixed["z_obs"], 0.0, 0.6),
                             M._Z_TAB, M._DC_TAB)
            pos_sel = _fixed["rhat"] * _dcp[:, None]'''

H_OLD = '''                    done.add((r.get("region"), r.get("index"),
                              r.get("carve_reseed"),
                              tuple(sorted(r.get("points", {}))),
                              tuple(r.get("erosions", EROSIONS_MOCK)),
                              bool(r.get("real_space", False))))'''

H_NEW = '''                    done.add((r.get("region"), r.get("index"),
                              r.get("carve_reseed"),
                              tuple(sorted(r.get("points", {}))),
                              tuple(r.get("erosions", EROSIONS_MOCK)),
                              bool(r.get("real_space", False)),
                              bool(r.get("fixed_observables", False))))'''

I_OLD = '''        if (reg, kk, a.carve_reseed, tuple(sorted(order)),
                tuple(ero), bool(getattr(a, "real_space", False))) in done:'''

I_NEW = '''        if (reg, kk, a.carve_reseed, tuple(sorted(order)),
                tuple(ero), bool(getattr(a, "real_space", False)),
                bool(getattr(a, "fixed_observables", False))) in done:'''

J_OLD = '''        if getattr(a, "real_space", False):
            rec["real_space"] = True'''

J_NEW = '''        if getattr(a, "real_space", False):
            rec["real_space"] = True
        if getattr(a, "fixed_observables", False):
            rec["fixed_observables"] = True'''

# L'ancora K e' cambiata: la patch realspace_fix ha inserito il blocco
# `if nm == "smoke":` esattamente dove qui ci si aspettava `else:`. Si ancora al
# nuovo contesto.
K_OLD = '''            q.add_argument("--real-space", action="store_true",
                           help="§3.8: azzera v_los, cioe' niente RSD. Usare un "
                                "--out SEPARATO: e' una misura diversa, non una "
                                "continuazione di quella in spazio di redshift")
        if nm == "smoke":'''

K_NEW = '''            q.add_argument("--real-space", action="store_true",
                           help="§3.8: azzera v_los, cioe' niente RSD. Usare un "
                                "--out SEPARATO: e' una misura diversa, non una "
                                "continuazione di quella in spazio di redshift")
            q.add_argument("--fixed-observables", action="store_true",
                           help="trattamento (B), record 16: (rhat, z_obs) "
                                "congelate al fiduciale, per ogni punto si "
                                "ricalcola solo r'. Usare un --out SEPARATO")
        if nm == "smoke":'''

# E si corregge un difetto lasciato da realspace_fix: quell'`else` si lega a
# `if nm == "smoke"`, non a `if nm == "run"`, quindi per `run` esegue
# set_defaults DOPO gli add_argument. Nei fatti e' innocuo - store_true
# funziona lo stesso e il run in spazio reale lo ha dimostrato - ma un ramo che
# si lega al blocco sbagliato e' una trappola che aspetta la prossima patch.
M_OLD = '''        else:
            q.set_defaults(carve_reseed=None, real_space=False)'''

M_NEW = '''        # NON `else`: si legherebbe a `if nm == "smoke"`. Ogni sottocomando
        # riceve i default di cio' che NON dichiara, e nient'altro.
        if nm != "run":
            q.set_defaults(carve_reseed=None, fixed_observables=False)
        if nm not in ("run", "smoke"):
            q.set_defaults(real_space=False)'''

L_OLD = '''        r = one_mock(M, P1, T2, F3, reg, geoms, kk, Gr["nz_z"], Gr["nz_target"],
                     order, frozen_delta_dir=cache_dir if not a.skip_fid else None,
                     carve_reseed=a.carve_reseed, erosions=ero)'''

L_NEW = '''        r = one_mock(M, P1, T2, F3, reg, geoms, kk, Gr["nz_z"], Gr["nz_target"],
                     order, frozen_delta_dir=cache_dir if not a.skip_fid else None,
                     carve_reseed=a.carve_reseed, erosions=ero,
                     fixed_observables=bool(getattr(a, "fixed_observables", False)))'''

EDITS = {
    "phase8": [("A  carve_cutsky prende capture=None", A_OLD, A_NEW),
               ("B  lista cand_r, vuota se capture e' None", B_OLD, B_NEW),
               ("C  accumula rhat solo se capture e' chiesto", C_OLD, C_NEW),
               ("D  riempie capture dopo il Pass 2", D_OLD, D_NEW)],
    "runner": [("E  one_mock prende fixed_observables", E_OLD, E_NEW),
               ("F  cache al fiduciale e cancello D5a", F_OLD, F_NEW),
               ("G  nel ciclo: rimappa invece di carvare", G_OLD, G_NEW),
               ("H  fixed_observables nella chiave", H_OLD, H_NEW),
               ("I  e nel confronto della chiave", I_OLD, I_NEW),
               ("J  e nel record", J_OLD, J_NEW),
               ("K  --fixed-observables", K_OLD, K_NEW),
               ("M  l'else non penzola piu' dal blocco smoke", M_OLD, M_NEW),
               ("L  cmd_run passa il flag a one_mock", L_OLD, L_NEW)],
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
    """Nomi usati in una funzione e legati da nessuna parte. `ast.parse` non li
    vede: la sintassi e' valida, il nome no. E' il controllo che ha intercettato
    PF e reg nella patch del §3.8."""
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
        elif isinstance(node, ast.comprehension):
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

    # 1-2: l'argomento della bit-identita', verificato e non asserito
    try:
        import numpy as np
        rng = np.random.default_rng(0)
        zt = np.linspace(0.0, 0.6, 4001)
        dct = 2997.92458 * zt * (1.0 - 0.75 * zt + 0.5 * zt * zt)
        z = rng.uniform(0.05, 0.45, 5000)
        rh = rng.normal(size=(5000, 3))
        rh /= np.linalg.norm(rh, axis=1)[:, None]
        # come phase8: interp sull'array INTERO, poi sottoinsieme
        dc_full = np.interp(np.clip(z, 0.0, 0.6), zt, dct)
        P_full = rh * dc_full[:, None]
        sel = rng.random(5000) < 0.3
        P_sub = P_full[sel]
        # come la cache: interp direttamente sul SOTTOINSIEME
        dc_sub = np.interp(np.clip(z[sel], 0.0, 0.6), zt, dct)
        P_ric = rh[sel] * dc_sub[:, None]
        chk("1  interp e' elementwise: sottoinsiemare prima o dopo e' identico",
            np.array_equal(P_ric, P_sub), "diversi: %d" % int((P_ric != P_sub).sum()))
        chk("2  quindi D5a a tolleranza ZERO e' raggiungibile, non ottimistico",
            np.array_equal(P_ric, P_sub))
    except Exception as exc:
        chk("1  bit-identita'", False, str(exc))

    n = 3
    for label, path in paths.items():
        ok = os.path.isfile(path)
        chk("%-2d %s presente" % (n, label), ok, path)
        n += 1
        if not ok:
            continue
        s = read(path)
        already = ("capture" in s) or ("--fixed-observables" in s) or ("D5a" in s)
        chk("%-2d %s: idempotenza" % (n, label), not already)
        n += 1
        for name, old, new in EDITS[label]:
            c = s.count(old)
            chk("%-2d %s: ancora %s" % (n, label, name), c == 1,
                "occorrenze=%d" % c)
            n += 1

    if all(c[1] for c in checks):
        out8 = apply_one(read(paths["phase8"]), "phase8")
        outr = apply_one(read(paths["runner"]), "runner")
        chk("%-2d entrambi restano Python valido" % n,
            _parses(out8) and _parses(outr)); n += 1
        chk("%-2d SCOPE: one_mock, ogni nome legato" % n,
            not _nomi_liberi(outr, "one_mock"),
            ", ".join(sorted(_nomi_liberi(outr, "one_mock")))); n += 1
        chk("%-2d SCOPE: carve_cutsky, ogni nome legato" % n,
            not _nomi_liberi(out8, "carve_cutsky"),
            ", ".join(sorted(_nomi_liberi(out8, "carve_cutsky")))); n += 1
        chk("%-2d capture=None non tocca nulla: cand_r resta vuota" % n,
            "if capture is not None:\n                    cand_r.append" in out8
            and out8.count("cand_r.append") == 1); n += 1
        chk("%-2d rhat si prende DOPO zsel e inmask, come P_rsd e z_obs" % n,
            "cand_r.append(rhat[zsel][inmask])" in out8); n += 1
        chk("%-2d e capture si riempie DOPO il Pass 2, con lo stesso keep" % n,
            'capture["rhat"] = np.vstack(cand_r)[keep]' in out8
            and 'capture["z_obs"] = z_cand[keep]' in out8); n += 1
        chk("%-2d D5a: tolleranza zero, array_equal, arresto duro" % n,
            "np.array_equal(_ric, _pos_fid)" in outr
            and "Tolleranza zero, record 16" in outr
            and "sys.exit" in outr.split("CANCELLO D5a")[1][:1200]); n += 1
        chk("%-2d e la sua natura e' dichiarata, non lasciata implicita" % n,
            "COSTRUZIONE DELLA CACHE" in outr
            and "NELLO STESSO PROCESSO" in outr); n += 1
        chk("%-2d in (B) il carving NON si richiama nel ciclo" % n,
            "if _fixed is None:" in outr
            and outr.count("M.carve_cutsky(pos_gal, vel_gal, g[\"mask\"]") == 1); n += 1
        chk("%-2d fixed_observables e' nella chiave, nel record e nel flag" % n,
            outr.count('bool(r.get("fixed_observables", False))') == 1
            and 'rec["fixed_observables"] = True' in outr
            and "--fixed-observables" in outr); n += 1
        chk("%-2d e ogni sottocomando ha i default di cio' che NON dichiara" % n,
            'if nm != "run":' in outr
            and 'if nm not in ("run", "smoke"):' in outr
            and outr.count("        else:\n            q.set_defaults") == 0); n += 1
        chk("%-2d chiave scritta e chiave letta hanno la stessa arita' (7)" % n,
            outr.count('bool(getattr(a, "fixed_observables", False))) in done') == 1); n += 1
        chk("%-2d cmd_run passa il flag: senza, la modalita' non arriva mai" % n,
            outr.count("fixed_observables=bool(getattr(a,") == 1
            and "one_mock" in outr.split("fixed_observables=bool(getattr(a,")[0][-400:]
            and "pts, frozen_delta_dir=cache_dir)" in outr); n += 1
        chk("%-2d D5c resta in 'measure' (record 23): non lo si tocca qui" % n,
            'D5C_MODE = "measure"' in outr); n += 1
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_fixedobs_patch ===")
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
            bak = path + ".pre_fixedobs"
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
DA APPLICARE A RUN FERMO: tocca il runner e phase8, e il §3.8 li sta usando.

PRIMA di lanciare, nell'ordine:
  python src\paper2_runner_fase3_mock.py selftest
  python src\paper2_runner_fase3_mock.py smoke --region NGC

Lo smoke gira SENZA --fixed-observables e deve dare gli stessi numeri di
prima: capture=None non deve cambiare niente. Se D4b smette di dire "esatto",
il parametro non e' inerte e non si prosegue.

POI il trattamento (B), sola linea B, registro SEPARATO:
  python src\paper2_runner_fase3_mock.py run --region NGC --n 200 ^
      --points FID B1 B2 B4 B5 B6 --fixed-observables ^
      --out results\paper2\fase3_mock_fixedobs.jsonl
  python src\paper2_runner_fase3_mock.py run --region SGC --n 200 ^
      --points FID B1 B2 B4 B5 B6 --fixed-observables ^
      --out results\paper2\fase3_mock_fixedobs.jsonl

DUE CONTROLLI A OCCHIO, sulle prime righe di output:
  - D5a non deve dire niente. Se compare, il run si e' fermato.
  - n_sel deve essere IDENTICO a tutti e sei i punti, per ogni realizzazione:
    in (B) la selezione e' congelata al fiduciale. Se varia, la modalita' non
    sta facendo quel che dice e va fermata.

D5b si verifica DOPO, in analisi: la media su 200 al fiduciale deve dare
35423.575 / 31889.925 (NGC) e 18694.420 / 16477.950 (SGC), record 21.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="trattamento (B), osservabili fisse")
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

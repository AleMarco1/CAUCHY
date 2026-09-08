#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_passata_1punto.py

PASSATA A UN PUNTO SU v1. Produce, per ogni mock e per emisfero, i campi a un
punto del contratto di uscita di 4.2a che oggi non esistono in nessun registro.

PERCHE' NON E' step6 CON --n_onepoint 2000
------------------------------------------
paper1_step6_onepoint_betti.py precarica mock_d e mock_n interi: a n=200 sono
6.7 GB, a n=2000 sarebbero 67. Qui si scorre a flusso, una realizzazione per
volta, e si depositano record PER REALIZZAZIONE invece di aggregati per
restrizione. Il calcolo e' lo stesso: setup_region, compute_delta, build_nu,
build_restrictions e moments sono IMPORTATI, non riscritti.

CANCELLO GIA' SUPERATO
----------------------
paper2_cancello_nu.py, 7 settembre 2026, indici 200/500/1000/1805/1999:
build_nu(delta) riproduce i cubi congelati test2_XXXX.npz bit per bit
(max|d| = 0.000e+00) e i momenti coincidono con n1b_spectra a 3.8e-07.
Verdetto UNICA: build_nu e' l'unica implementazione di nu.

ANCORE DI RIPRODUZIONE, SOLO NGC
--------------------------------
  delta : n1_spectra_NGC.jsonl,  idx 0-49    ->  50 record
  nu    : n1b_spectra_NGC.jsonl, idx 200-1999 -> 1800 record
Gli insiemi sono DISGIUNTI: nessuna realizzazione valida i due cammini
insieme, quindi si riproducono entrambi. Tolleranza relativa 1e-5, dichiarata
il 7 settembre prima di qualunque misura (i registri sono float32; a 1e-6 un
valore corretto fallisce).

SGC non ha ancore: nessun cubo nu congelato esiste per quell'emisfero. SGC
eredita la validita' dal cammino, non da un'ancora propria, e per questo NON
parte finche' NGC non e' completa e pulita (--ancora-ngc).

ANCORAGGIO AGLI INGRESSI
------------------------
Ogni record porta delta_sha256, calcolato sui byte del file letti una volta
sola, e riscontrato contro cachedelta_manifest_<REG>.jsonl. Uno scarto ferma
la passata: significa che il campo in ingresso non e' quello manifestato.

PROVE DI FUMO IN UN REGISTRO SEPARATO
-------------------------------------
Con --n < 2000 i record portano "smoke": true e il nome del file di uscita
DEVE contenere "smoke", altrimenti la passata si rifiuta di partire. Le 38
prove dentro fase3_mock.jsonl hanno prodotto sei conflitti coi valori di
produzione: qui non e' una raccomandazione, e' un cancello.

USO
    python src\\paper2_passata_1punto.py selftest
    python src\\paper2_passata_1punto.py run --region NGC --n 5 ^
        --out results\\paper2\\smoke_1punto_NGC.jsonl
    python src\\paper2_passata_1punto.py run --region NGC ^
        --out results\\paper2\\onepoint_v1_NGC.jsonl
    python src\\paper2_passata_1punto.py run --region SGC ^
        --ancora-ngc results\\paper2\\onepoint_v1_NGC.jsonl ^
        --out results\\paper2\\onepoint_v1_SGC.jsonl

Uscita: 0 se completa e tutte le riproduzioni tornano, 1 se una riproduzione
fallisce o l'ancoraggio non torna, 2 su errore d'uso. Nessun fallimento e'
un avviso.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# --- dichiarati prima della misura ----------------------------------------
TOL_RIPRODUZIONE = 1e-5
SCHEMA = "paper2_onepoint_v1"
RESTRIZIONI_DEFAULT = "none,fieldr10"   # le due che le regole dichiarate usano
N_PREGATE = 5                            # indici di pre-cancello per ancora
ROOT_DEFAULT = r"D:\projects\cauchy"


# ---------------------------------------------------------------------------
# percorsi e nomi, in un posto solo
# ---------------------------------------------------------------------------

def percorsi(root, region):
    root = Path(root)
    return {
        "delta": root / "data" / "processed" / "paper1_mock_deltas" / region,
        "manifest": root / "results" / "paper2" / ("cachedelta_manifest_%s.jsonl" % region),
        "n1": root / "results" / "paper1" / ("n1_spectra_%s.jsonl" % region),
        "n1b": root / "results" / "paper1" / ("n1b_spectra_%s.jsonl" % region),
        "desi_raw": root / "data" / "raw" / "desi_dr1",
        "phase6": root / "data" / "processed" / "phase6_fields",
    }


def percorso_sommario(out):
    """Il sommario NON sta nel registro: un record senza idx lo rende
    eterogeneo e il verificatore del contratto lo rifiuta, giustamente."""
    out = Path(out)
    return out.with_name(out.stem + "_sommario" + out.suffix)


def nome_delta(idx):
    return "delta_%04d.npy" % int(idx)


def rel_diff(a, b):
    a, b = float(a), float(b)
    if not (np.isfinite(a) and np.isfinite(b)):
        return float("inf")
    if b == 0.0:
        return 0.0 if a == 0.0 else abs(a)
    return abs(a - b) / abs(b)


# ---------------------------------------------------------------------------
# registri
# ---------------------------------------------------------------------------

def leggi_registro(path, chiave="idx"):
    """idx -> record. Registro assente: dizionario vuoto, non errore."""
    out = {}
    p = Path(path)
    if not p.is_file():
        return out
    with p.open("r", encoding="utf-8") as fh:
        for riga in fh:
            riga = riga.strip()
            if not riga:
                continue
            r = json.loads(riga)
            if isinstance(r, dict) and chiave in r:
                out[int(r[chiave])] = r
    return out


def leggi_manifest(path):
    """Manifest della cache: nome del file -> sha256."""
    out = {}
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    with p.open("r", encoding="utf-8") as fh:
        for riga in fh:
            riga = riga.strip()
            if not riga:
                continue
            r = json.loads(riga)
            if not isinstance(r, dict):
                continue
            nome = None
            for k in ("rel", "path", "file", "nome"):
                if k in r:
                    nome = str(r[k]).replace("\\", "/").split("/")[-1]
                    break
            sha = None
            for k in ("sha256", "sha", "hash", "sha256_hex"):
                if k in r and isinstance(r[k], str):
                    sha = r[k].lower()
                    break
            if nome and sha:
                out[nome] = sha
    return out


def sommario_pulito(path, attesi=None):
    """
    Vero se l'ultimo sommario di quel registro e' di passata pulita E, quando
    attesi e' dato, se i record totali sono esattamente quelli. Una ripresa a
    zero record nuovi resta valida solo se il registro e' completo.
    'path' e' il registro; il sommario si legge dal file affiancato.
    """
    p = percorso_sommario(path)
    if not p.is_file():
        return False
    righe = [r for r in p.read_text(encoding="utf-8").splitlines() if r.strip()]
    if not righe:
        return False
    try:
        ult = json.loads(righe[-1])
    except Exception:
        return False
    if (ult.get("schema") != SCHEMA + "_sommario"
            or ult.get("esito") != "PULITA"
            or ult.get("smoke", False)):
        return False
    if attesi is not None and int(ult.get("n_record_totali", -1)) != int(attesi):
        return False
    return True


def idx_gia_fatti(path):
    return set(leggi_registro(path))


# ---------------------------------------------------------------------------
# misura di una realizzazione
# ---------------------------------------------------------------------------

def carica_delta(fp):
    """Legge i byte UNA volta: da li' sia lo sha sia l'array."""
    b = Path(fp).read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    a = np.load(io.BytesIO(b))
    return a, sha


def verifica_ancoraggio(nome, sha, manifest):
    """Ritorna None se il file e' quello manifestato, altrimenti il motivo."""
    atteso = manifest.get(nome)
    if atteso is None:
        return "%s non e' nel manifest della cache" % nome
    if atteso != sha:
        return ("%s: sha %s contro manifest %s"
                % (nome, sha[:12], atteso[:12]))
    return None


def misura(S6, P1, M, delta32, mask, subsets, soglia_pat):
    """Otto campi del contratto piu' le restrizioni extra. delta32 e' float32."""
    delta = delta32.astype(np.float64)
    nu = P1.build_nu(delta, mask, M.SIGMA_PX)

    piena = delta[mask]
    md = S6.moments(piena)
    mn = S6.moments(nu[mask].astype(np.float64))

    rec = {
        "delta": {"sigma_in_mask": md["std"], "kurt_in_mask": md["kurt_excess"]},
        "nu": {"sigma_in_mask": mn["std"], "kurt_in_mask": mn["kurt_excess"],
               "p1": mn["p01"], "p99": mn["p99"]},
        "max_delta": md["max"],
        "n_patologici": int((piena > soglia_pat).sum()),
    }
    extra = {}
    for label, sel in subsets:
        if label == "footprint pieno":
            continue
        xd = delta[sel]
        xn = nu[sel].astype(np.float64)
        a, b = S6.moments(xd), S6.moments(xn)
        extra[label] = {
            "n_voxel": int(sel.sum()),
            "delta": {"sigma_in_mask": a["std"], "kurt_in_mask": a["kurt_excess"],
                      "var": a["var"], "max": a["max"]},
            "nu": {"sigma_in_mask": b["std"], "kurt_in_mask": b["kurt_excess"],
                   "var": b["var"], "p1": b["p01"], "p99": b["p99"]},
        }
    rec["restrizioni"] = extra
    rec["_var_delta_piena"] = md["var"]
    rec["_var_nu_piena"] = mn["var"]
    return rec


def controlla_ancore(idx, rec, n1, n1b):
    """Confronta col registro congelato dove esiste. Ritorna lista di scarti."""
    esiti = []
    if idx in n1:
        r = n1[idx]
        esiti.append(("n1/delta.sigma", rel_diff(rec["delta"]["sigma_in_mask"],
                                                 r["sigma_in_mask"])))
        esiti.append(("n1/delta.kurt", rel_diff(rec["delta"]["kurt_in_mask"],
                                                r["kurt_in_mask"])))
    if idx in n1b:
        r = n1b[idx]
        esiti.append(("n1b/nu.sigma", rel_diff(rec["nu"]["sigma_in_mask"],
                                               r["sigma_in_mask"])))
        esiti.append(("n1b/nu.kurt", rel_diff(rec["nu"]["kurt_in_mask"],
                                              r["kurt_in_mask"])))
    return esiti


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def ancore_step6(root, region):
    """
    Valori di DESI gia' congelati in paper1_step6_<REG>.json, per restrizione
    e per campo. step6 espone sette chiavi (mean, var, skew, kurt_excess,
    median, p99, max) e NON espone p01: e' l'unica quantita' nuova della riga.
    """
    p = (Path(root) / "results" / "paper1" / ("paper1_step6_%s.json" % region))
    if not p.is_file():
        return {}, str(p)
    rep = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for label, r in (rep.get("onepoint", {}).get("restrictions", {}) or {}).items():
        for campo in ("delta", "nu"):
            for k, v in (r.get(campo, {}) or {}).items():
                if isinstance(v, dict) and "desi" in v and v["desi"] is not None:
                    out[(label, campo, k)] = float(v["desi"])
    return out, str(p)


def riga_desi(root, region, out_path):
    """
    Statistiche a un punto di DESI, nel suo file. NON entra nel registro per
    realizzazione: un record senza idx lo renderebbe eterogeneo, ed e' il
    difetto che il verificatore del contratto ha respinto.
    """
    root = Path(root).resolve()
    M, P1, S6 = carica_moduli(root)
    P = percorsi(root, region)
    out = Path(out_path)

    print("=" * 78)
    print("RIGA A UN PUNTO DI DESI  |  %s" % region)
    print("=" * 78)

    G = P1.setup_region(M, region, P["desi_raw"], P["phase6"])
    mask = G["mask"]
    alpha = G["sum_wd"] / G["sum_wr"]
    delta = np.asarray(P1.compute_delta(G["field_d"], G["field_r"], alpha,
                                        mask, M.NGRID), dtype=np.float64)
    nu = P1.build_nu(delta, mask, M.SIGMA_PX)
    subsets = S6.build_restrictions(mask, np.asarray(G["field_r"], float),
                                    [x for x in RESTRIZIONI_DEFAULT.split(",") if x])

    ancore, dove = ancore_step6(root, region)
    print("  ancore da %s: %d valori" % (dove, len(ancore)))
    if not ancore:
        print("  [FERMO] senza le ancore di step6 la riga di DESI non e' verificabile")
        return 1

    mis, peggio, n_conf = {}, 0.0, 0
    for label, sel in subsets:
        md = S6.moments(delta[sel])
        mn = S6.moments(nu[sel].astype(np.float64))
        mis[label] = {"n_voxel": int(sel.sum()), "delta": md, "nu": mn}
        for campo, m in (("delta", md), ("nu", mn)):
            for k, v in m.items():
                a = ancore.get((label, campo, k))
                if a is None:
                    continue
                r = rel_diff(v, a)
                n_conf += 1
                peggio = max(peggio, r)
                if r > TOL_RIPRODUZIONE:
                    print("    [FERMO] %s %s.%s: %r contro %r, scarto %.3e"
                          % (label, campo, k, v, a, r))
                    return 1
    print("  %d valori riscontrati con step6, peggior scarto %.3e" % (n_conf, peggio))

    piena = dict(mis["footprint pieno"])
    rec = {
        "schema": SCHEMA + "_desi", "region": region, "soggetto": "DESI",
        "utc": datetime.now(timezone.utc).isoformat(),
        "delta": {"sigma_in_mask": piena["delta"]["std"],
                  "kurt_in_mask": piena["delta"]["kurt_excess"]},
        "nu": {"sigma_in_mask": piena["nu"]["std"],
               "kurt_in_mask": piena["nu"]["kurt_excess"],
               "p1": piena["nu"]["p01"], "p99": piena["nu"]["p99"]},
        "max_delta": piena["delta"]["max"],
        "n_patologici": 0,
        "nota_n_patologici": ("nullo per costruzione: la soglia E' il massimo "
                              "di delta di DESI"),
        "n_voxel_maschera": int(mask.sum()),
        "sigma_px": float(M.SIGMA_PX),
        "n_ancore_step6": n_conf,
        "peggior_scarto_step6": peggio,
        "momenti": mis,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=True) + "\n")

    rf = ((piena["nu"]["p99"] - piena["nu"]["p01"]) / piena["nu"]["std"])
    print("  nu di DESI: p1 %.6f  p99 %.6f  sigma %.6f" %
          (piena["nu"]["p01"], piena["nu"]["p99"], piena["nu"]["std"]))
    print("  r_f = (p99-p1)/sigma = %.6f   <- p1 e' l'unico valore non ancorato" % rf)
    print("  scritto: %s" % out)
    return 0


def carica_moduli(root):
    sys.path.insert(0, str(Path(root) / "src"))
    import phase8_cutsky_mocks as M            # noqa: E402
    import paper1_remap as P1                  # noqa: E402
    import paper1_step6_onepoint_betti as S6   # noqa: E402
    for f, mod in ((P1.build_nu, "paper1_remap"),
                   (P1.compute_delta, "paper1_remap"),
                   (P1.setup_region, "paper1_remap"),
                   (S6.moments, "paper1_step6_onepoint_betti"),
                   (S6.build_restrictions, "paper1_step6_onepoint_betti")):
        if f.__module__ != mod:
            raise RuntimeError("%s non viene da %s ma da %s"
                               % (f.__name__, mod, f.__module__))
    return M, P1, S6


def run(root, region, out_path, n=0, restrizioni=RESTRIZIONI_DEFAULT,
        ancora_ngc=None):
    root = Path(root).resolve()
    out = Path(out_path)
    smoke = bool(n)

    # cancello sul nome: una prova di fumo non entra in un registro di produzione
    if smoke and "smoke" not in out.name.lower():
        raise SystemExit("con --n il nome di uscita deve contenere 'smoke': %s"
                         % out.name)
    if not smoke and "smoke" in out.name.lower():
        raise SystemExit("passata completa su un file chiamato smoke: %s" % out.name)

    # ordine dichiarato: SGC solo dopo una NGC completa e pulita
    if region == "SGC" and not smoke:
        if not ancora_ngc:
            raise SystemExit("SGC richiede --ancora-ngc: nessuna ancora esiste "
                             "per questo emisfero")
        attesi = len(list((Path(root) / "data" / "processed"
                           / "paper1_mock_deltas" / "NGC").glob("delta_*.npy")))
        if not sommario_pulito(ancora_ngc, attesi):
            raise SystemExit(
                "l'ancora NGC non e' una passata completa e pulita "
                "(attesi %d record): %s" % (attesi, ancora_ngc))

    M, P1, S6 = carica_moduli(root)
    P = percorsi(root, region)

    print("=" * 78)
    print("PASSATA A UN PUNTO SU v1  |  %s%s" % (region, "  [SMOKE]" if smoke else ""))
    print("tolleranza di riproduzione: %.0e" % TOL_RIPRODUZIONE)
    print("=" * 78)

    manifest = leggi_manifest(P["manifest"])
    n1 = leggi_registro(P["n1"])
    n1b = leggi_registro(P["n1b"])
    print("  ancore: n1 %d record, n1b %d record, manifest %d voci"
          % (len(n1), len(n1b), len(manifest)))
    if region == "NGC" and not (n1 and n1b):
        raise SystemExit("ancore NGC assenti: la passata non parte senza")

    G = P1.setup_region(M, region, P["desi_raw"], P["phase6"])
    mask = G["mask"]
    alpha = G["sum_wd"] / G["sum_wr"]
    desi_delta = P1.compute_delta(G["field_d"], G["field_r"], alpha, mask, M.NGRID)
    soglia_pat = float(np.asarray(desi_delta)[mask].max())
    print("  maschera %d voxel   sigma_px %.6f   soglia patologici (max delta DESI) %.4f"
          % (int(mask.sum()), float(M.SIGMA_PX), soglia_pat))

    specs = [x for x in restrizioni.split(",") if x.strip()]
    subsets = S6.build_restrictions(mask, np.asarray(G["field_r"], float), specs)
    print("  restrizioni: %s" % ", ".join(lab for lab, _ in subsets))

    files = sorted(P["delta"].glob("delta_*.npy"))
    if not files:
        raise FileNotFoundError(str(P["delta"] / "delta_*.npy"))
    if n:
        files = files[:n]
    fatti = idx_gia_fatti(out) if out.is_file() else set()
    if fatti:
        print("  ripresa: %d record gia' presenti" % len(fatti))

    # pre-cancello: le prime N_PREGATE realizzazioni con ancora, prima di tutto
    pre = ([i for i in sorted(n1)][:N_PREGATE] +
           [i for i in sorted(n1b)][:N_PREGATE])
    if pre and not smoke:
        print("  pre-cancello su %d indici con ancora ..." % len(pre))
        for idx in pre:
            fp = P["delta"] / nome_delta(idx)
            if not fp.is_file():
                raise FileNotFoundError(str(fp))
            a, sha = carica_delta(fp)
            motivo = verifica_ancoraggio(fp.name, sha, manifest)
            if motivo:
                print("    [FERMO] ingresso non manifestato: %s" % motivo)
                return 1
            rec = misura(S6, P1, M, a, mask, subsets, soglia_pat)
            for nome, r in controlla_ancore(idx, rec, n1, n1b):
                if r > TOL_RIPRODUZIONE:
                    print("    [FERMO] idx %d %s scarto %.3e > %.0e"
                          % (idx, nome, r, TOL_RIPRODUZIONE))
                    return 1
        print("  pre-cancello superato")

    t0 = time.time()
    n_scritti = n_ancorati = 0
    peggior_scarto = 0.0
    with out.open("a", encoding="utf-8") as fh:
        for k, fp in enumerate(files):
            idx = int(fp.stem.split("_")[-1])
            if idx in fatti:
                continue
            a, sha = carica_delta(fp)

            motivo = verifica_ancoraggio(fp.name, sha, manifest)
            if motivo:
                print("    [FERMO] ingresso non manifestato: %s" % motivo)
                return 1

            rec = misura(S6, P1, M, a, mask, subsets, soglia_pat)
            scarti = controlla_ancore(idx, rec, n1, n1b)
            for nome, r in scarti:
                peggior_scarto = max(peggior_scarto, r)
                if r > TOL_RIPRODUZIONE:
                    print("    [FERMO] idx %d %s scarto %.3e > %.0e"
                          % (idx, nome, r, TOL_RIPRODUZIONE))
                    return 1
            if scarti:
                n_ancorati += 1

            rec.update({"schema": SCHEMA, "region": region, "idx": idx,
                        "delta_sha256": sha,
                        "soglia_patologici": soglia_pat,
                        "n_ancore": len(scarti),
                        "utc": datetime.now(timezone.utc).isoformat()})
            if smoke:
                rec["smoke"] = True
            fh.write(json.dumps(rec, ensure_ascii=True) + "\n")
            n_scritti += 1

            if n_scritti % 50 == 0:
                dt = time.time() - t0
                print("    %d/%d  %.2f s/mock  stimate %.1f min"
                      % (n_scritti, len(files), dt / n_scritti,
                         dt / n_scritti * (len(files) - n_scritti) / 60.0))

    dt = time.time() - t0
    sommario = {
        "schema": SCHEMA + "_sommario", "region": region,
        "utc": datetime.now(timezone.utc).isoformat(),
        "esito": "PULITA", "smoke": smoke,
        "n_record_scritti": n_scritti,
        "n_record_totali": len(idx_gia_fatti(out)),
        "n_con_ancora": n_ancorati,
        "peggior_scarto_relativo": peggior_scarto,
        "tol_riproduzione": TOL_RIPRODUZIONE,
        "soglia_patologici": soglia_pat,
        "restrizioni": [lab for lab, _ in subsets],
        "secondi_per_mock": dt / n_scritti if n_scritti else None,
        "nota_sgc": ("SGC non ha cubi nu congelati: nessuna ancora propria, "
                     "validita' ereditata dal cammino verificato in NGC"),
    }
    ps = percorso_sommario(out)
    with ps.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(sommario, ensure_ascii=True) + "\n")

    print("\n%d record scritti, %d con ancora, peggior scarto %.3e"
          % (n_scritti, n_ancorati, peggior_scarto))
    print("%.2f s/mock, totale %.1f min" % (dt / max(n_scritti, 1), dt / 60.0))
    print("registro: %s" % out)
    print("sommario: %s" % ps)
    return 0


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def selftest(root=ROOT_DEFAULT):
    import tempfile
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, n))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, n, det))

    print("selftest paper2_passata_1punto")

    chk("tolleranza dichiarata", TOL_RIPRODUZIONE == 1e-5, TOL_RIPRODUZIONE)
    chk("restrizioni di default sono quelle delle regole",
        RESTRIZIONI_DEFAULT == "none,fieldr10", RESTRIZIONI_DEFAULT)

    P = percorsi("/b", "SGC")
    chk("percorsi sono Path", all(isinstance(v, Path) for v in P.values()))
    chk("il manifest e' per emisfero",
        P["manifest"].name == "cachedelta_manifest_SGC.jsonl", P["manifest"].name)
    chk("nome_delta a quattro cifre", nome_delta(7) == "delta_0007.npy")
    chk("i percorsi si compongono",
        str(P["delta"] / nome_delta(1999)).endswith("delta_1999.npy"))

    chk("rel_diff normale", abs(rel_diff(1 + 1e-6, 1) - 1e-6) < 1e-12)
    chk("rel_diff con b=0", rel_diff(0, 0) == 0.0 and rel_diff(2, 0) == 2.0)
    chk("rel_diff con nan", rel_diff(float("nan"), 1) == float("inf"))

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        f = td / "r.jsonl"
        f.write_text("\n".join(json.dumps({"idx": i, "sigma_in_mask": 1.0 + i,
                                           "kurt_in_mask": 2.0})
                               for i in (0, 1, 2)) + "\n", encoding="utf-8")
        r = leggi_registro(f)
        chk("leggi_registro indicizza per idx", set(r) == {0, 1, 2}, sorted(r))
        chk("registro assente non e' errore", leggi_registro(td / "no.jsonl") == {})
        chk("idx_gia_fatti per la ripresa", idx_gia_fatti(f) == {0, 1, 2})

        m = td / "man.jsonl"
        m.write_text(json.dumps({"rel": "NGC/delta_0000.npy", "sha256": "AB12"}) + "\n"
                     + json.dumps({"path": "x\\NGC\\delta_0001.npy", "sha": "cd34"}) + "\n",
                     encoding="utf-8")
        mm = leggi_manifest(m)
        chk("manifest: nome del file e sha, minuscolo",
            mm == {"delta_0000.npy": "ab12", "delta_0001.npy": "cd34"}, mm)
        try:
            leggi_manifest(td / "assente.jsonl")
            chk("manifest assente solleva", False, "non ha sollevato")
        except FileNotFoundError:
            chk("manifest assente solleva", True)

        arr = np.arange(64, dtype=np.float32).reshape(4, 4, 4)
        fp = td / "delta_0000.npy"
        np.save(fp, arr)
        a, sha = carica_delta(fp)
        chk("carica_delta legge i byte una volta e ne da' array e sha",
            np.array_equal(a, arr) and sha == hashlib.sha256(
                fp.read_bytes()).hexdigest(), sha[:12])

    # ancore: confronto con i registri congelati
    rec = {"delta": {"sigma_in_mask": 10.0, "kurt_in_mask": 3.0},
           "nu": {"sigma_in_mask": 2.0, "kurt_in_mask": 0.5, "p1": -1.0, "p99": 1.0}}
    n1 = {5: {"sigma_in_mask": 10.0, "kurt_in_mask": 3.0}}
    n1b = {5: {"sigma_in_mask": 2.0 * (1 + 1e-3), "kurt_in_mask": 0.5}}
    e = dict(controlla_ancore(5, rec, n1, n1b))
    chk("ancora delta riconosciuta", e["n1/delta.sigma"] == 0.0, e)
    chk("ancora nu misura lo scarto (denominatore = registro congelato)",
        abs(e["n1b/nu.sigma"] - 1e-3 / (1 + 1e-3)) < 1e-12, e)
    chk("un idx senza ancora non produce confronti",
        controlla_ancore(99, rec, n1, n1b) == [], "non vuoto")
    chk("i due insiemi di ancore sono distinti nel nome",
        set(k.split("/")[0] for k in e) == {"n1", "n1b"}, sorted(e))

    # contratto: i nomi vanno col prefisso
    chiavi = set()

    def _flat(d, p=""):
        for k, v in d.items():
            q = "%s.%s" % (p, k) if p else k
            if isinstance(v, dict):
                _flat(v, q)
            else:
                chiavi.add(q)
    _flat({"delta": rec["delta"], "nu": rec["nu"], "max_delta": 0,
           "n_patologici": 0, "delta_sha256": ""})
    attese = {"delta.sigma_in_mask", "delta.kurt_in_mask", "nu.sigma_in_mask",
              "nu.kurt_in_mask", "nu.p1", "nu.p99", "max_delta",
              "n_patologici", "delta_sha256"}
    chk("il contratto ha i nove nomi, col prefisso", attese <= chiavi,
        sorted(attese - chiavi))
    chk("sigma_in_mask piatto non esiste nel record",
        "sigma_in_mask" not in chiavi)

    # cancello sul nome del file di uscita
    chk("smoke su nome di produzione e' rifiutato",
        "smoke" in _rifiuto("NGC", "/t/onepoint_v1_NGC.jsonl", 5, None))
    chk("passata completa su nome smoke e' rifiutata",
        "smoke" in _rifiuto("NGC", "/t/smoke_1punto_NGC.jsonl", 0, None))
    chk("SGC senza ancora e' rifiutata",
        "ancora" in _rifiuto("SGC", "/t/onepoint_v1_SGC.jsonl", 0, None))

    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "onepoint_v1_NGC.jsonl"
        f.write_text(json.dumps({"schema": SCHEMA, "idx": 0}) + "\n",
                     encoding="utf-8")
        percorso_sommario(f).write_text(json.dumps(
            {"schema": SCHEMA + "_sommario", "esito": "PULITA",
             "smoke": False}) + "\n", encoding="utf-8")
        chk("un sommario PULITA vale come ancora", sommario_pulito(f))
        g = Path(td) / "smoke.jsonl"
        g.write_text(json.dumps({"schema": SCHEMA, "idx": 0}) + "\n",
                     encoding="utf-8")
        percorso_sommario(g).write_text(json.dumps(
            {"schema": SCHEMA + "_sommario", "esito": "PULITA",
             "smoke": True}) + "\n", encoding="utf-8")
        chk("un sommario di smoke NON vale come ancora", not sommario_pulito(g))
        chk("un file senza sommario non vale come ancora",
            not sommario_pulito(Path(td) / "vuoto.jsonl"))

    # ancoraggio: la funzione unica usata dal pre-cancello e dal ciclo
    man = {"delta_0000.npy": "abc"}
    chk("ancoraggio: file giusto passa",
        verifica_ancoraggio("delta_0000.npy", "abc", man) is None)
    chk("ancoraggio: sha diverso e' respinto con il motivo giusto",
        "manifest" in (verifica_ancoraggio("delta_0000.npy", "zzz", man) or ""))
    chk("ancoraggio: file fuori manifest e' respinto",
        "non e' nel manifest" in (verifica_ancoraggio("delta_9999.npy", "abc", man) or ""))

    # il sommario sta fuori dal registro, e il registro resta omogeneo
    chk("il sommario ha un file suo",
        percorso_sommario("/a/onepoint_v1_NGC.jsonl").name
        == "onepoint_v1_NGC_sommario.jsonl",
        percorso_sommario("/a/onepoint_v1_NGC.jsonl").name)
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "onepoint_v1_NGC.jsonl"
        f.write_text("\n".join(json.dumps({"schema": SCHEMA, "idx": i})
                                for i in range(3)) + "\n", encoding="utf-8")
        chiavi_comuni = set.intersection(*[
            set(json.loads(l)) for l in f.read_text().splitlines() if l.strip()])
        chk("ogni record del registro porta idx", "idx" in chiavi_comuni,
            sorted(chiavi_comuni))
        percorso_sommario(f).write_text(json.dumps(
            {"schema": SCHEMA + "_sommario", "esito": "PULITA", "smoke": False,
             "n_record_scritti": 0, "n_record_totali": 3}) + "\n",
            encoding="utf-8")
        chk("ancora completa vale", sommario_pulito(f, 3))
        chk("ancora incompleta NON vale", not sommario_pulito(f, 2000))
        chk("senza attesi resta il controllo debole", sommario_pulito(f))
        chk("registro senza sommario affiancato non e' ancora",
            not sommario_pulito(Path(td) / "altro.jsonl"))

    # ancore di DESI da step6
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "results" / "paper1").mkdir(parents=True)
        (td / "results" / "paper1" / "paper1_step6_NGC.json").write_text(json.dumps(
            {"onepoint": {"restrictions": {
                "footprint pieno": {
                    "delta": {"var": {"desi": 2.9166, "mock_mean": 2918.4},
                              "max": {"desi": 125.4742}},
                    "nu": {"kurt_excess": {"desi": -0.4382},
                           "p99": {"desi": 5.0, "z": None}}}}}}),
            encoding="utf-8")
        A, dove = ancore_step6(td, "NGC")
        chk("ancore_step6 legge i valori di DESI per restrizione e campo",
            A.get(("footprint pieno", "delta", "var")) == 2.9166
            and A.get(("footprint pieno", "nu", "kurt_excess")) == -0.4382, A)
        chk("ancore_step6 prende solo il lato DESI, non mock_mean",
            all(isinstance(v, float) for v in A.values()) and len(A) == 4, A)
        chk("p01 NON e' fra le ancore: e' la quantita' nuova",
            ("footprint pieno", "nu", "p01") not in A, sorted(A))
        chk("step6 assente: nessuna ancora, e il percorso viene detto",
            ancore_step6(td, "SGC")[0] == {}
            and "paper1_step6_SGC.json" in ancore_step6(td, "SGC")[1])

    # formula dei momenti, contro n1b
    rng = np.random.default_rng(1)
    v = rng.normal(size=20000) * 1.7
    sd = float(v.std())
    k = float(((v - v.mean()) ** 4).mean() / sd ** 4 - 3.0)
    try:
        sys.path.insert(0, str(Path(root) / "src"))
        import paper1_step6_onepoint_betti as S6
        m = S6.moments(v)
        chk("moments == sigma di n1b", abs(m["std"] - sd) <= 1e-12 * abs(sd))
        chk("moments == curtosi di n1b", abs(m["kurt_excess"] - k) <= 1e-12 * abs(k))
        chk("nu.p1 viene da moments['p01']", "p01" in m)
    except ImportError as e:
        chk("step6 importabile", False, str(e))
        chk("(saltato)", False, "step6 non importabile")
        chk("(saltato)", False, "step6 non importabile")

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def _rifiuto(region, nome, n, ancora):
    """Ritorna il messaggio di rifiuto di run, o '' se non ha rifiutato."""
    try:
        run("/nonesiste", region, nome, n=n, ancora_ngc=ancora)
    except SystemExit as ex:
        return str(ex)
    except Exception as ex:
        return "ALTRO:" + type(ex).__name__
    return ""


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--root", default=ROOT_DEFAULT)
    r.add_argument("--region", choices=["NGC", "SGC"], required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--n", type=int, default=0, help="prova di fumo su n mock")
    r.add_argument("--restrizioni", default=RESTRIZIONI_DEFAULT)
    r.add_argument("--ancora-ngc", dest="ancora_ngc", default=None)
    d = sub.add_parser("desi", help="riga a un punto di DESI, nel suo file")
    d.add_argument("--root", default=ROOT_DEFAULT)
    d.add_argument("--region", choices=["NGC", "SGC"], required=True)
    d.add_argument("--out", required=True)
    s = sub.add_parser("selftest")
    s.add_argument("--root", default=ROOT_DEFAULT)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return run(a.root, a.region, a.out, a.n, a.restrizioni, a.ancora_ngc)
    if a.cmd == "desi":
        return riga_desi(a.root, a.region, a.out)
    if a.cmd == "selftest":
        return selftest(a.root)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

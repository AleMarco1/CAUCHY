#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_prov_pk.py — audit di PROVENIENZA, in sola lettura, del cache P(k) nwLH.

Punto 6.8 della checklist, passo 1: stabilire la provenienza di `pk_matrix`
(`results/phase7_pk_nwlh_cache.npz`).

CHE COSA FA, E CHE COSA NON FA
------------------------------
Non calcola R^2, non esegue i test B e C di D6, non interpreta il 48.3 %.
Fa una cosa sola: dichiarare che cosa il file contiene, quando e come e' stato
scritto, e se l'allineamento **riga -> realizzazione nwLH** sia VERIFICABILE
DAL FILE oppure sia un'assunzione posizionale.

Il modo di fallire della Fase 6 e' dichiarare tracciabile un numero perche'
*esiste* un file che lo contiene. Un digest congelato dimostra INTEGRITA'
(il file non e' cambiato), non PROVENIENZA (chi lo ha scritto, con quale
codice, con quale ordine di righe). Questo strumento separa le due cose e si
rifiuta di emettere un verdetto sulla seconda: la restituisce come stato
- `esplicito`  : il file porta identificatori di realizzazione
- `posizionale`: l'ordine e' un'assunzione, e serve un test esterno

SOLA LETTURA
------------
Il cache viene aperto solo in lettura (`allow_pickle=False`). sha256 e mtime
sono misurati prima e dopo l'ispezione e confrontati: se cambiano, il comando
fallisce. L'unica scrittura e' una riga JSONL appesa a `--out`.

USO
---
    python src\\paper2_prov_pk.py selftest
    python src\\paper2_prov_pk.py ispeziona --npz results\\phase7_pk_nwlh_cache.npz --params data\\raw\\quijote\\3D_cubes\\latin_hypercube_nwLH\\latin_hypercube_nwLH_params.txt --out logs\\prov_pk.jsonl

Opzionale: `--sha-atteso <hex>` confronta il digest col valore congelato
(item 0.13). Il confronto e' riportato come integrita', mai come provenienza.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

VERSIONE = "1.1"
SPREAD_SOGLIA_S = 60.0  # oltre questo, i membri dello zip non sono di una sola passata


# ---------------------------------------------------------------- utilita' pure

def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def spread_secondi(date_times) -> float:
    """Distanza in secondi fra il membro piu' vecchio e il piu' recente di uno zip."""
    if not date_times:
        return 0.0
    ts = []
    for dt in date_times:
        y, mo, d, hh, mm, ss = dt
        ts.append(_dt.datetime(y, mo, d, hh, mm, ss).timestamp())
    return max(ts) - min(ts)


def is_permutazione(a: np.ndarray) -> bool:
    """True se `a` e' 1-D e i suoi valori sono esattamente 0..n-1 oppure 1..n."""
    if a.ndim != 1 or a.size < 2:
        return False
    if a.dtype.kind in "iu":
        v = a.astype(np.int64, copy=False)
    elif a.dtype.kind == "f":
        if not np.all(np.isfinite(a)) or not np.all(a == np.floor(a)):
            return False
        v = a.astype(np.int64)
    else:
        return False
    s = np.sort(v)
    n = v.size
    return bool(np.array_equal(s, np.arange(n)) or np.array_equal(s, np.arange(1, n + 1)))


def is_asse_monotono(a: np.ndarray) -> bool:
    """True se `a` e' 1-D, float, finito e strettamente crescente (candidato griglia k)."""
    if a.ndim != 1 or a.size < 3 or a.dtype.kind != "f":
        return False
    if not np.all(np.isfinite(a)):
        return False
    return bool(np.all(np.diff(a) > 0))


def _testa(a: np.ndarray, n: int = 6) -> list:
    """Primi n valori del piatto, in forma JSON-serializzabile."""
    flat = a.reshape(-1)[:n]
    out = []
    for x in flat:
        if isinstance(x, (bytes, np.bytes_)):
            out.append(x.decode("utf-8", "replace"))
        elif isinstance(x, (str, np.str_)):
            out.append(str(x))
        else:
            try:
                out.append(float(x))
            except Exception:
                out.append(repr(x))
    return out


# ------------------------------------------------------------------ ispezione

def inventario_zip(path: Path) -> dict:
    with zipfile.ZipFile(path, "r") as z:
        infos = z.infolist()
        membri = [
            {
                "nome": i.filename,
                "byte_compressi": i.compress_size,
                "byte": i.file_size,
                "compressione": int(i.compress_type),
                "data_ora": "%04d-%02d-%02dT%02d:%02d:%02d" % i.date_time,
                "create_system": int(i.create_system),
                "create_version": int(i.create_version),
                "crc32": "%08x" % (i.CRC & 0xFFFFFFFF),
            }
            for i in infos
        ]
        sp = spread_secondi([i.date_time for i in infos])
        epoca = all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in infos) and bool(infos)
    return {
        "n_membri": len(membri),
        "membri": membri,
        "spread_membri_s": sp,
        "una_sola_passata": bool(sp <= SPREAD_SOGLIA_S),
        "timestamp_all_epoca_zip": epoca,
        "nota_timestamp": (
            "tutti i membri sono all'epoca zip (1980-01-01): e' cio' che scrive np.savez "
            "dalle versioni recenti di numpy. Assenza di informazione, non difetto"
            if epoca
            else "i membri portano un timestamp reale: utile, e confrontabile col mtime del file"
        ),
    }


def descrivi_array(nome: str, a: np.ndarray) -> dict:
    d = {
        "nome": nome,
        "shape": list(a.shape),
        "dtype": str(a.dtype),
        "ndim": int(a.ndim),
        "size": int(a.size),
        "c_contiguous": bool(a.flags["C_CONTIGUOUS"]),
        "testa": _testa(a),
    }
    if a.dtype.kind in "fiu" and a.size:
        fin = np.isfinite(a) if a.dtype.kind == "f" else np.ones(a.shape, bool)
        d["n_non_finiti"] = int(a.size - int(fin.sum()))
        if int(fin.sum()):
            d["min"] = float(np.asarray(a)[fin].min())
            d["max"] = float(np.asarray(a)[fin].max())
    if a.dtype.kind in "US":
        d["esempi"] = _testa(a, 3)
    if a.ndim == 1 and a.size <= 64 and a.dtype.kind == "f":
        d["valori_interi"] = [float(x) for x in a]
    d["candidato_asse"] = is_asse_monotono(a)
    d["candidato_id"] = is_permutazione(a)
    d["candidato_etichette"] = bool(a.dtype.kind in "US" and a.ndim == 1 and a.size > 1)
    return d


def leggi_params(path: Path) -> dict:
    righe_commento = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for riga in fh:
            s = riga.strip()
            if not s:
                continue
            if s.startswith("#"):
                righe_commento.append(s)
            else:
                break
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tab = np.loadtxt(path, comments="#", ndmin=2)
    if tab.size == 0:
        raise SystemExit("FALLIMENTO: nessuna riga di dati in %s" % path)
    out = {
        "path": str(path),
        "sha256": sha256_file(path),
        "n_righe": int(tab.shape[0]),
        "n_colonne": int(tab.shape[1]),
        "righe_commento": righe_commento[:5],
        "min_per_colonna": [float(x) for x in tab.min(axis=0)],
        "max_per_colonna": [float(x) for x in tab.max(axis=0)],
        "prima_riga": [float(x) for x in tab[0]],
    }
    return out


def ispeziona(npz_path: Path, params_path: Path | None, sha_atteso: str | None = None) -> dict:
    if not npz_path.is_file():
        raise SystemExit("FALLIMENTO: cache non trovato: %s" % npz_path)

    st0 = npz_path.stat()
    sha0 = sha256_file(npz_path)

    rec = {
        "strumento": "paper2_prov_pk",
        "versione": VERSIONE,
        "quando": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "file": {
            "path": str(npz_path),
            "byte": int(st0.st_size),
            "mtime": _dt.datetime.fromtimestamp(st0.st_mtime).isoformat(timespec="seconds"),
            "sha256": sha0,
        },
        "integrita": {
            "sha_atteso": sha_atteso,
            "corrisponde": (None if sha_atteso is None else bool(sha_atteso.lower() == sha0)),
            "nota": "l'integrita' NON e' la provenienza",
        },
    }

    rec["zip"] = inventario_zip(npz_path)

    arrays = []
    try:
        with np.load(npz_path, allow_pickle=False) as f:
            chiavi = list(f.files)
            for k in chiavi:
                arrays.append(descrivi_array(k, np.asarray(f[k])))
    except ValueError as e:
        raise SystemExit(
            "FALLIMENTO: il cache richiede allow_pickle (contiene oggetti Python). "
            "Un cache di provenienza non stabilita non va aperto con pickle. Dettaglio: %s" % e
        )
    rec["chiavi"] = chiavi
    rec["arrays"] = arrays

    matrici = [a for a in arrays if a["ndim"] == 2]
    assi = [a for a in arrays if a["candidato_asse"]]
    ids = [a for a in arrays if a["candidato_id"]]
    etich = [a for a in arrays if a["candidato_etichette"]]

    if params_path is not None:
        rec["params"] = leggi_params(params_path)
        n_real = rec["params"]["n_righe"]
    else:
        rec["params"] = None
        n_real = None

    incroci = []
    for m in matrici:
        d0, d1 = m["shape"]
        incroci.append(
            {
                "matrice": m["nome"],
                "dim0": d0,
                "dim1": d1,
                "dim0_uguale_n_realizzazioni": (None if n_real is None else bool(d0 == n_real)),
                "dim1_uguale_a_un_asse": [a["nome"] for a in assi if a["size"] == d1],
                "dim0_uguale_a_un_id": [a["nome"] for a in ids if a["size"] == d0],
                "dim0_uguale_a_etichette": [a["nome"] for a in etich if a["size"] == d0],
            }
        )
    rec["incroci"] = incroci

    esplicito = any(
        (c["dim0_uguale_a_un_id"] or c["dim0_uguale_a_etichette"]) for c in incroci
    )
    rec["allineamento"] = {
        "stato": "esplicito" if esplicito else "posizionale",
        "motivo": (
            "il file porta identificatori di riga della stessa lunghezza della matrice"
            if esplicito
            else "nessun identificatore di riga nel file: l'ordine riga -> realizzazione e' un'assunzione"
        ),
        "verificabile_dal_file": bool(esplicito),
    }

    st1 = npz_path.stat()
    sha1 = sha256_file(npz_path)
    if sha1 != sha0 or int(st1.st_mtime) != int(st0.st_mtime):
        raise SystemExit("FALLIMENTO: il cache e' cambiato durante l'ispezione (sola lettura violata)")
    rec["sola_lettura_confermata"] = True

    rec["verdetto"] = {
        "integrita": (
            "non dichiarata" if sha_atteso is None
            else ("CONFERMATA" if rec["integrita"]["corrisponde"] else "DISCORDANTE")
        ),
        "codice_scrivente": "NON stabilito da questo strumento (serve la ricerca nel repo e in git)",
        "semantica": "NON stabilita da questo strumento (quantita', unita', spazio reale/redshift, snapshot)",
        "allineamento_righe": rec["allineamento"]["stato"],
        "provenienza_stabilita": False,
    }
    return rec


def appendi_jsonl(out_path: Path, rec: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    riga = json.dumps(rec, ensure_ascii=False, sort_keys=False)
    with open(out_path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(riga + "\n")
        fh.flush()
        os.fsync(fh.fileno())



# ------------------------------------------------------ prove di allineamento

SEED_DEFAULT = 20260912
NPERM_DEFAULT = 1000


def r2_ols(X: np.ndarray, y: np.ndarray):
    """R^2 di una OLS con intercetta. Nessun fallback silenzioso."""
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ beta
    yc = y - y.mean()
    ss_tot = float(yc @ yc)
    if ss_tot == 0.0:
        raise SystemExit("FALLIMENTO: il sommario ha varianza nulla")
    return 1.0 - float(res @ res) / ss_tot, beta


def trova_riempimenti(M: np.ndarray) -> dict:
    """Righe esattamente duplicate e loro rapporto con la media delle righe uniche.

    In float32 su piu' decine di colonne due realizzazioni distinte non
    coincidono bit a bit: un gruppo di duplicati e' un riempimento, non un dato.
    """
    uni, inv, cnt = np.unique(M, axis=0, return_inverse=True, return_counts=True)
    inv = np.ravel(inv)
    dup = np.zeros(M.shape[0], dtype=bool)
    gruppi = []
    for g in np.where(cnt > 1)[0]:
        righe = np.where(inv == g)[0]
        dup[righe] = True
        gruppi.append(
            {
                "n_righe": int(cnt[g]),
                "prime_righe": [int(x) for x in righe[:20]],
                "troncato": bool(cnt[g] > 20),
            }
        )
    out = {
        "n_righe_duplicate": int(dup.sum()),
        "n_gruppi": len(gruppi),
        "gruppi": gruppi,
        "n_righe_uniche": int((~dup).sum()),
    }
    if gruppi and int((~dup).sum()) > 1:
        mu = M[~dup].astype(np.float64).mean(axis=0)
        peggiore = None
        for g in np.where(cnt > 1)[0]:
            riga = M[np.where(inv == g)[0][0]].astype(np.float64)
            den = np.where(np.abs(mu) > 0, np.abs(mu), 1.0)
            rel = float(np.max(np.abs(riga - mu) / den))
            peggiore = rel if peggiore is None else min(peggiore, rel)
        out["rel_vs_media_uniche"] = peggiore
        out["firma_mean_pk"] = bool(peggiore is not None and peggiore < 1e-5)
    else:
        out["rel_vs_media_uniche"] = None
        out["firma_mean_pk"] = False
    return out


def allinea(npz_path: Path, params_path: Path, chiave: str = "pk_matrix",
            nperm: int = NPERM_DEFAULT, seed: int = SEED_DEFAULT) -> dict:
    if not npz_path.is_file():
        raise SystemExit("FALLIMENTO: cache non trovato: %s" % npz_path)
    sha0 = sha256_file(npz_path)

    with np.load(npz_path, allow_pickle=False) as f:
        if chiave not in f.files:
            raise SystemExit("FALLIMENTO: chiave '%s' assente. Presenti: %s" % (chiave, list(f.files)))
        M = np.asarray(f[chiave])
    if M.ndim != 2:
        raise SystemExit("FALLIMENTO: '%s' non e' una matrice (shape %s)" % (chiave, M.shape))

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        X_all = np.loadtxt(params_path, comments="#", ndmin=2)
    if X_all.shape[0] != M.shape[0]:
        raise SystemExit(
            "FALLIMENTO: %d righe nel cache contro %d realizzazioni: il join non e' nemmeno di forma giusta"
            % (M.shape[0], X_all.shape[0])
        )
    if not np.all(np.isfinite(M)):
        raise SystemExit("FALLIMENTO: valori non finiti nella matrice: il test non e' definito")

    rec = {
        "strumento": "paper2_prov_pk/allinea",
        "versione": VERSIONE,
        "quando": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "file": {"path": str(npz_path), "sha256": sha0, "chiave": chiave,
                 "shape": [int(x) for x in M.shape], "dtype": str(M.dtype)},
        "params": {"path": str(params_path), "shape": [int(x) for x in X_all.shape]},
        "regola_dichiarata": (
            "il join e' sostenuto solo se l'R^2 osservato sta fuori dall'intero supporto "
            "del nullo per permutazione (nperm permutazioni delle righe del disegno). "
            "Stabilisce l'ordine, non il codice ne' la semantica."
        ),
        "nperm": int(nperm),
        "seed": int(seed),
    }

    rec["riempimenti"] = trova_riempimenti(M)
    dup = np.zeros(M.shape[0], dtype=bool)
    if rec["riempimenti"]["n_gruppi"]:
        uni, inv, cnt = np.unique(M, axis=0, return_inverse=True, return_counts=True)
        inv = np.ravel(inv)
        for g in np.where(cnt > 1)[0]:
            dup[np.where(inv == g)[0]] = True
    keep = ~dup
    rec["righe_usate"] = int(keep.sum())
    if int(keep.sum()) < 50:
        raise SystemExit("FALLIMENTO: meno di 50 righe utilizzabili dopo l'esclusione dei duplicati")

    Mk = M[keep].astype(np.float64)
    Xk = X_all[keep]
    Xs = (Xk - Xk.mean(axis=0)) / Xk.std(axis=0, ddof=0)

    sommari = {
        "bin_0": Mk[:, 0],
        "media_colonne": Mk.mean(axis=1),
        "inclinazione_primo_meno_ultimo": Mk[:, 0] - Mk[:, -1],
    }

    rng = np.random.default_rng(seed)
    perm_idx = [rng.permutation(len(Xs)) for _ in range(int(nperm))]

    esiti = {}
    for nome, y in sommari.items():
        ys = (y - y.mean()) / y.std(ddof=0)
        r2, beta = r2_ols(Xs, ys)
        nulli = np.empty(int(nperm))
        for j, p_ in enumerate(perm_idx):
            nulli[j], _ = r2_ols(Xs[p_], ys)
        esiti[nome] = {
            "r2_osservato": float(r2),
            "nullo_max": float(nulli.max()),
            "nullo_medio": float(nulli.mean()),
            "nullo_p999": float(np.quantile(nulli, 0.999)),
            "fuori_dal_supporto": bool(r2 > nulli.max()),
            "beta_standardizzati": {
                n: float(b) for n, b in zip(
                    ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "M_nu", "w0"][: Xs.shape[1]],
                    beta[1:],
                )
            },
        }
    rec["esiti"] = esiti
    rec["verdetto"] = {
        "allineamento_sostenuto": bool(all(e["fuori_dal_supporto"] for e in esiti.values())),
        "stabilisce": "solo l'ordine riga -> realizzazione",
        "non_stabilisce": "identita' del codice scrivente, semantica della quantita', griglia k",
    }

    if sha256_file(npz_path) != sha0:
        raise SystemExit("FALLIMENTO: il cache e' cambiato durante il test (sola lettura violata)")
    rec["sola_lettura_confermata"] = True
    return rec


# ------------------------------------------------------------------- selftest

def _fab_npz(dirp: Path, nome: str, con_id: bool, n: int = 40, nk: int = 12,
             nan: bool = False, oggetti: bool = False, etichette: bool = False) -> Path:
    rng = np.random.default_rng(7)
    pk = rng.lognormal(size=(n, nk))
    if nan:
        pk[3, 4] = np.nan
    kg = np.logspace(-2, 0, nk)
    d = {"pk_matrix": pk, "k": kg}
    if con_id:
        d["real_id"] = np.arange(n, dtype=np.int64)
    if etichette:
        d["sorgenti"] = np.array(["nwLH_%04d" % i for i in range(n)])
    if oggetti:
        d["meta"] = np.array([{"a": 1}], dtype=object)
        p = dirp / nome
        np.savez(p, **d)
        return p
    p = dirp / nome
    np.savez(p, **d)
    return p


def _fab_params(dirp: Path, nome: str, n: int = 40) -> Path:
    rng = np.random.default_rng(11)
    tab = rng.uniform(0.1, 0.9, size=(n, 7))
    p = dirp / nome
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("# Omega_m Omega_b h n_s sigma_8 M_nu w\n")
        for r in tab:
            fh.write(" ".join("%.8f" % x for x in r) + "\n")
    return p



def _fab_cache_da_params(dirp: Path, nome: str, X: np.ndarray, nk: int = 30,
                         rumore: float = 0.05, n_riempimenti: int = 0,
                         permuta: bool = False, seed: int = 5) -> Path:
    """Cache sintetico in cui log P dipende davvero dai parametri (segnale forte)."""
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    kk = np.linspace(0.0, 1.0, nk)[None, :]
    amp = X[:, 4][:, None]          # sigma_8 -> ampiezza
    tilt = (X[:, 3][:, None] - 1.0)  # n_s -> inclinazione
    M = 4.0 + 2.0 * amp - 3.0 * kk + 2.0 * tilt * kk + rumore * rng.normal(size=(n, nk))
    M = M.astype(np.float32)
    if permuta:
        M = M[rng.permutation(n)]
    if n_riempimenti:
        righe = rng.choice(n, size=n_riempimenti, replace=False)
        mask = np.ones(n, bool)
        mask[righe] = False
        media = M[mask].astype(np.float64).mean(axis=0).astype(np.float32)
        M[righe] = media
    pp = dirp / nome
    np.savez(pp, pk_matrix=M)
    return pp


def selftest() -> int:
    ok = 0
    tot = 0

    def check(cond, nome):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok]   %s" % nome)
        else:
            print("  [FAIL] %s" % nome)

    print("selftest paper2_prov_pk v%s" % VERSIONE)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # --- funzioni pure
        f = d / "x.bin"
        f.write_bytes(b"cauchy")
        check(sha256_file(f) == hashlib.sha256(b"cauchy").hexdigest(), "sha256_file == hashlib")
        check(spread_secondi([(2026, 9, 12, 10, 0, 0), (2026, 9, 12, 10, 0, 30)]) == 30.0,
              "spread_secondi su due membri")
        check(spread_secondi([]) == 0.0, "spread_secondi su zip vuoto")
        check(is_permutazione(np.arange(5)), "is_permutazione su 0..n-1")
        check(is_permutazione(np.arange(1, 6)), "is_permutazione su 1..n")
        check(not is_permutazione(np.array([0, 0, 1, 2, 3])), "DIFETTO: duplicati non sono un id")
        check(not is_permutazione(np.array([0.5, 1.5])), "non interi non sono un id")
        check(is_asse_monotono(np.logspace(-2, 0, 10)), "is_asse_monotono su griglia k")
        check(not is_asse_monotono(np.array([1.0, 0.5, 2.0])), "DIFETTO: asse non monotono respinto")

        # --- ispezione con id espliciti
        npz_id = _fab_npz(d, "con_id.npz", con_id=True)
        par = _fab_params(d, "params.txt", n=40)
        r = ispeziona(npz_id, par)
        nomi = {a["nome"] for a in r["arrays"]}
        check(nomi == {"pk_matrix", "k", "real_id"}, "tutte le chiavi riportate")
        pkd = [a for a in r["arrays"] if a["nome"] == "pk_matrix"][0]
        check(pkd["shape"] == [40, 12], "shape della matrice corretta")
        check(pkd["dtype"] == "float64", "dtype riportato")
        check(pkd["n_non_finiti"] == 0, "nessun non finito su dati puliti")
        check(any(a["candidato_asse"] for a in r["arrays"] if a["nome"] == "k"),
              "griglia k riconosciuta come asse")
        check(r["allineamento"]["stato"] == "esplicito", "allineamento esplicito con real_id")
        check(r["incroci"][0]["dim0_uguale_n_realizzazioni"] is True,
              "incrocio righe cache <-> righe params")
        check(r["verdetto"]["provenienza_stabilita"] is False,
              "provenienza NON dichiarata stabilita nemmeno col caso migliore")
        check(r["sola_lettura_confermata"] is True, "sha256 e mtime invariati dopo l'ispezione")
        check(r["zip"]["una_sola_passata"] is True, "membri dello zip in una sola passata")
        check(r["zip"]["timestamp_all_epoca_zip"] is True,
              "epoca zip riconosciuta come assenza di informazione, non come difetto")

        # --- etichette testuali
        npz_lab = _fab_npz(d, "etich.npz", con_id=False, etichette=True)
        r_lab = ispeziona(npz_lab, par)
        check(r_lab["allineamento"]["stato"] == "esplicito", "etichette testuali bastano")

        # --- DIFETTO: nessun id -> posizionale
        npz_no = _fab_npz(d, "senza_id.npz", con_id=False)
        r2 = ispeziona(npz_no, par)
        check(r2["allineamento"]["stato"] == "posizionale",
              "DIFETTO: senza id l'allineamento e' posizionale, non silenziosamente accettato")
        check(r2["allineamento"]["verificabile_dal_file"] is False,
              "posizionale dichiarato non verificabile dal file")

        # --- DIFETTO: conteggio righe discordante
        par_corto = _fab_params(d, "params_corto.txt", n=37)
        r3 = ispeziona(npz_no, par_corto)
        check(r3["incroci"][0]["dim0_uguale_n_realizzazioni"] is False,
              "DIFETTO: 40 righe contro 37 realizzazioni segnalato")

        # --- DIFETTO: non finiti
        npz_nan = _fab_npz(d, "nan.npz", con_id=True, nan=True)
        r4 = ispeziona(npz_nan, par)
        pk4 = [a for a in r4["arrays"] if a["nome"] == "pk_matrix"][0]
        check(pk4["n_non_finiti"] == 1, "DIFETTO: un NaN contato")

        # --- DIFETTO: file mancante -> fallimento esplicito
        try:
            ispeziona(d / "non_esiste.npz", par)
            check(False, "cache mancante deve fallire")
        except SystemExit:
            check(True, "DIFETTO: cache mancante fallisce in modo esplicito")

        # --- DIFETTO: npz con oggetti -> rifiuto di pickle
        npz_obj = _fab_npz(d, "oggetti.npz", con_id=True, oggetti=True)
        try:
            ispeziona(npz_obj, par)
            check(False, "npz con oggetti deve fallire")
        except SystemExit:
            check(True, "DIFETTO: npz con pickle rifiutato, non caricato")

        # --- log append-only
        out = d / "logs" / "prov.jsonl"
        appendi_jsonl(out, r)
        prima = out.read_text(encoding="utf-8")
        appendi_jsonl(out, r2)
        dopo = out.read_text(encoding="utf-8")
        check(dopo.startswith(prima), "log append-only: la prima riga non e' toccata")
        check(len(dopo.strip().splitlines()) == 2, "due righe dopo due ispezioni")
        rec0 = json.loads(dopo.strip().splitlines()[0])
        check({"strumento", "file", "zip", "arrays", "allineamento", "verdetto"} <= set(rec0),
              "il record JSONL porta tutte le sezioni")
        check(sha256_file(npz_id) == r["file"]["sha256"], "il cache non e' stato modificato dal log")

        # --- integrita' dichiarata
        r5 = ispeziona(npz_id, par, sha_atteso=r["file"]["sha256"])
        check(r5["verdetto"]["integrita"] == "CONFERMATA", "sha atteso corrispondente")
        r6 = ispeziona(npz_id, par, sha_atteso="00" * 32)
        check(r6["verdetto"]["integrita"] == "DISCORDANTE", "DIFETTO: sha atteso sbagliato segnalato")

        # --- params senza tabella valida
        cattivo = d / "vuoto.txt"
        cattivo.write_text("# solo commenti\n", encoding="utf-8")
        try:
            leggi_params(cattivo)
            check(False, "params vuoto deve fallire")
        except SystemExit:
            check(True, "DIFETTO: params senza righe dati fallisce")

        # --- allinea: segnale vero, ordine corretto
        par_g = _fab_params(d, "params_grande.txt", n=200)
        Xp = np.loadtxt(par_g, comments="#", ndmin=2)
        c_ok = _fab_cache_da_params(d, "all_ok.npz", Xp, n_riempimenti=0)
        ra = allinea(c_ok, par_g, nperm=200, seed=1)
        check(ra["esiti"]["media_colonne"]["fuori_dal_supporto"] is True,
              "allinea: ordine corretto -> R^2 fuori dal supporto del nullo")
        check(ra["verdetto"]["allineamento_sostenuto"] is True, "allinea: verdetto sostenuto")
        check(ra["riempimenti"]["n_righe_duplicate"] == 0, "allinea: nessun duplicato su dati puliti")
        check(ra["sola_lettura_confermata"] is True, "allinea: sola lettura confermata")
        check(ra["nperm"] == 200 and ra["seed"] == 1, "allinea: nperm e seed registrati")
        b = ra["esiti"]["media_colonne"]["beta_standardizzati"]
        check(abs(b["sigma_8"]) > 5 * abs(b["Omega_b"]),
              "allinea: sigma_8 domina l'ampiezza, come iniettato")

        # --- DIFETTO: righe permutate -> il test non sostiene il join
        c_perm = _fab_cache_da_params(d, "all_perm.npz", Xp, permuta=True)
        rp = allinea(c_perm, par_g, nperm=200, seed=1)
        check(rp["verdetto"]["allineamento_sostenuto"] is False,
              "DIFETTO: cache permutato -> allineamento NON sostenuto")
        check(rp["esiti"]["media_colonne"]["r2_osservato"] < rp["esiti"]["media_colonne"]["nullo_max"],
              "DIFETTO: R^2 del permutato cade dentro il nullo")

        # --- DIFETTO: righe di riempimento
        c_fill = _fab_cache_da_params(d, "all_fill.npz", Xp, n_riempimenti=7)
        rf = allinea(c_fill, par_g, nperm=100, seed=1)
        check(rf["riempimenti"]["n_righe_duplicate"] == 7, "DIFETTO: sette righe duplicate contate")
        check(rf["riempimenti"]["n_gruppi"] == 1, "DIFETTO: un solo gruppo di duplicati")
        check(rf["riempimenti"]["firma_mean_pk"] is True,
              "DIFETTO: il duplicato coincide con la media delle uniche (firma mean_pk)")
        check(rf["righe_usate"] == Xp.shape[0] - 7, "allinea: righe di riempimento escluse dal test")

        # --- determinismo
        r1 = allinea(c_ok, par_g, nperm=100, seed=77)
        r2_ = allinea(c_ok, par_g, nperm=100, seed=77)
        check(r1["esiti"]["bin_0"]["nullo_max"] == r2_["esiti"]["bin_0"]["nullo_max"],
              "allinea: stesso seed, stesso nullo")

        # --- DIFETTO: conteggio righe incompatibile
        try:
            allinea(c_ok, par_corto, nperm=10)
            check(False, "join di forma sbagliata deve fallire")
        except SystemExit:
            check(True, "DIFETTO: 200 righe contro 37 realizzazioni fallisce prima del test")

        # --- DIFETTO: chiave assente
        try:
            allinea(c_ok, par_g, chiave="non_esiste", nperm=10)
            check(False, "chiave assente deve fallire")
        except SystemExit:
            check(True, "DIFETTO: chiave assente fallisce in modo esplicito")

        # --- r2_ols su relazione esatta
        Xe = np.random.default_rng(0).normal(size=(200, 3))
        ye = Xe @ np.array([1.0, -2.0, 0.5]) + 3.0
        r2e, _ = r2_ols(Xe, ye)
        check(abs(r2e - 1.0) < 1e-12, "r2_ols: relazione esatta -> R^2 = 1")
        try:
            r2_ols(Xe, np.ones(200))
            check(False, "varianza nulla deve fallire")
        except SystemExit:
            check(True, "DIFETTO: sommario a varianza nulla fallisce")

    print("\nselftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


# ----------------------------------------------------------------------- main

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Audit di provenienza, in sola lettura, del cache P(k) nwLH")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("selftest", help="controlli su dati sintetici, difetti inclusi")

    i = sub.add_parser("ispeziona", help="apre il cache in sola lettura e scrive un record JSONL")
    i.add_argument("--npz", required=True)
    i.add_argument("--params", default=None)
    i.add_argument("--out", default=None)
    i.add_argument("--sha-atteso", default=None)

    al_ = sub.add_parser("allinea", help="duplicati e test di allineamento con nullo per permutazione")
    al_.add_argument("--npz", required=True)
    al_.add_argument("--params", required=True)
    al_.add_argument("--chiave", default="pk_matrix")
    al_.add_argument("--nperm", type=int, default=NPERM_DEFAULT)
    al_.add_argument("--seed", type=int, default=SEED_DEFAULT)
    al_.add_argument("--out", default=None)

    a = p.parse_args(argv)

    if a.cmd == "selftest":
        return selftest()

    if a.cmd == "allinea":
        rec = allinea(Path(a.npz), Path(a.params), a.chiave, a.nperm, a.seed)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        if a.out:
            appendi_jsonl(Path(a.out), rec)
            print("\n[log] riga appesa a %s" % a.out, file=sys.stderr)
        print(
            "\n== ALLINEAMENTO ==\nrighe duplicate: %d (firma mean_pk: %s)\nrighe usate: %d\nsostenuto: %s\nstabilisce: solo l'ordine\n"
            % (rec["riempimenti"]["n_righe_duplicate"], rec["riempimenti"]["firma_mean_pk"],
               rec["righe_usate"], "SI" if rec["verdetto"]["allineamento_sostenuto"] else "NO"),
            file=sys.stderr,
        )
        return 0

    rec = ispeziona(Path(a.npz), Path(a.params) if a.params else None, a.sha_atteso)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    if a.out:
        appendi_jsonl(Path(a.out), rec)
        print("\n[log] riga appesa a %s" % a.out, file=sys.stderr)

    al = rec["allineamento"]["stato"]
    print(
        "\n== VERDETTO ==\nintegrita': %s\ncodice scrivente: %s\nsemantica: %s\nallineamento righe: %s\nprovenienza stabilita: NO\n"
        % (rec["verdetto"]["integrita"], rec["verdetto"]["codice_scrivente"],
           rec["verdetto"]["semantica"], al),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

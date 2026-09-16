#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_prov_pk_riproduci.py — chiusura dei punti 2, 3 e 4 della provenienza del cache P(k).

Punto 6.8, passo 1, seconda parte. Il primo strumento (`paper2_prov_pk.py`) ha
chiuso l'integrita' e ha sostenuto l'allineamento con un nullo per permutazione.
Restano due cose che nessuna statistica sul contenuto puo' dare:

  - **codice scrivente**: `git log --follow` su `src/phase7_r53_robustness.py`
    porta un solo commit, 2 lug 2026, un mese DOPO l'mtime del cache
    (5 giu 2026). Il versionamento non puo' datare chi ha scritto il file.
  - **semantica**: e' leggibile nel codice (log10 del monopolo di P(k) del campo
    DM a z=0, box 1000, 110 bin), ma leggerla non dimostra che sia stata eseguita.

Entrambe si chiudono con una sola prova: **riprodurre righe del cache dal codice
di HEAD**. Se tre righe a indici dichiarati tornano, tornano insieme il codice,
la semantica e l'ordine.

Sottocomandi
  selftest      controlli su dati sintetici, difetti inclusi. Non richiede Pylians
  riempimento   il buco del test sui duplicati: un riempimento `mean_pk` SINGOLO
                non ha un gemello e non e' un duplicato. Qui ogni riga viene
                confrontata con la media delle altre 1999. Non richiede Pylians
  riproduci     ricalcola le righe agli indici dichiarati con lo stesso percorso
                di codice e le confronta bit a bit. Richiede Pylians3, e se manca
                FALLISCE: il ramo scipy di ripiego produce un bin, non 110

REGOLA, DICHIARATA PRIMA DI ESEGUIRE
------------------------------------
Indici dichiarati: **0, 1000, 1999**. Esito:
  - **coincidenza bit a bit** su tutte tre  -> punti 2, 3 e 4 chiusi insieme;
  - **rel <= 1e-6** ma non bit a bit        -> chiusi, con nota sulla versione
                                               di libreria (float32 eps ~1.2e-7);
  - **qualunque scarto maggiore**           -> la provenienza NON e' ricostruibile,
                                               e vale la seconda uscita di P1-2:
                                               dichiararlo e TOGLIERE i test B e C,
                                               non tenerli con un caveat.
Il cache non viene mai riscritto. La griglia k, che il cache non contiene, viene
salvata in un file sorella nuovo e solo se non esiste: `--out-kref`.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

VERSIONE = "1.0"
INDICI_DICHIARATI = (0, 1000, 1999)
TOL_AMMESSA = 1e-6
SOGLIA_RIEMPIMENTO = 1e-5
BOX_SIZE = 1000.0
MAS_CODICE = "CIC"          # quello che passa HEAD, non quello che il nome del file suggerisce
NOME_CAMPO = "df_m_128_PCS_z=0.npy"


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def appendi_jsonl(out_path: Path, rec: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def carica_matrice(npz_path: Path, chiave: str = "pk_matrix") -> tuple[np.ndarray, str]:
    if not npz_path.is_file():
        raise SystemExit("FALLIMENTO: cache non trovato: %s" % npz_path)
    sha = sha256_file(npz_path)
    with np.load(npz_path, allow_pickle=False) as f:
        if chiave not in f.files:
            raise SystemExit("FALLIMENTO: chiave '%s' assente. Presenti: %s" % (chiave, list(f.files)))
        M = np.asarray(f[chiave])
    if M.ndim != 2:
        raise SystemExit("FALLIMENTO: '%s' non e' una matrice" % chiave)
    return M, sha


# ------------------------------------------------- riempimento singolo (senza Pylians)

def rel_vs_media_altre(M: np.ndarray) -> np.ndarray:
    """Per ogni riga: scarto relativo massimo dalla media delle ALTRE righe.

    Un riempimento `mean_pk` unico vale esattamente la media delle riuscite,
    cioe' la media delle altre righe: il suo scarto e' ~0. Una realizzazione
    vera sta a distanza O(0.1-1). Il test sui duplicati non lo vede, perche'
    un riempimento solo non ha gemelli.
    """
    X = M.astype(np.float64)
    n = X.shape[0]
    if n < 3:
        raise SystemExit("FALLIMENTO: servono almeno tre righe")
    S = X.sum(axis=0)
    mu = (S[None, :] - X) / (n - 1)
    den = np.where(np.abs(mu) > 0, np.abs(mu), 1.0)
    return np.max(np.abs(X - mu) / den, axis=1)


def comando_riempimento(npz_path: Path, chiave: str, soglia: float) -> dict:
    M, sha = carica_matrice(npz_path, chiave)
    rel = rel_vs_media_altre(M)
    ordine = np.argsort(rel)
    sospette = [int(i) for i in np.where(rel < soglia)[0]]
    return {
        "strumento": "paper2_prov_pk_riproduci/riempimento",
        "versione": VERSIONE,
        "quando": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "file": {"path": str(npz_path), "sha256": sha, "shape": [int(x) for x in M.shape]},
        "soglia": float(soglia),
        "rel_minima": float(rel[ordine[0]]),
        "riga_piu_vicina_alla_media": int(ordine[0]),
        "prime_cinque": [{"riga": int(i), "rel": float(rel[i])} for i in ordine[:5]],
        "mediana_rel": float(np.median(rel)),
        "righe_sospette": sospette,
        "verdetto": {
            "riempimento_singolo": bool(len(sospette) > 0),
            "nota": (
                "nessuna riga coincide con la media delle altre: il ramo mean_pk non e' scattato"
                if not sospette
                else "una o piu' righe valgono la media delle altre: sono riempimenti, non dati"
            ),
        },
    }


# ------------------------------------------------------------ riproduzione (Pylians)

def _importa_pylians():
    try:
        import Pk_library as PKL  # noqa
    except ImportError as e:
        raise SystemExit(
            "FALLIMENTO: Pylians3 non importabile (%s). Nessun ripiego: il ramo scipy "
            "del codice scrivente produce un bin, non 110, e non riprodurrebbe nulla." % e
        )
    return PKL


def calcola_riga(campo_path: Path, box: float, mas: str) -> tuple[np.ndarray, np.ndarray]:
    """Ripercorre il corpo di `_compute_pk_matrix` per una singola realizzazione.

    Ritorna (k3D, riga_float32) con riga = log10(clip(Pk[:,0], 1e-10)).
    """
    PKL = _importa_pylians()
    if not campo_path.is_file():
        raise SystemExit("FALLIMENTO: campo non trovato: %s" % campo_path)
    field = np.load(campo_path).astype(np.float32)
    if not field.flags["C_CONTIGUOUS"]:
        field = np.ascontiguousarray(field)
    pk_obj = PKL.Pk(field, box, axis=0, MAS=mas, threads=1, verbose=False)
    k = np.asarray(pk_obj.k3D)
    pk = np.asarray(pk_obj.Pk[:, 0])
    riga = np.log10(np.clip(pk, 1e-10, None)).astype(np.float32)
    return k, riga


def confronta_riga(attesa: np.ndarray, ottenuta: np.ndarray) -> dict:
    if attesa.shape != ottenuta.shape:
        raise SystemExit(
            "FALLIMENTO: lunghezze diverse, %s contro %s: non e' la stessa quantita'"
            % (attesa.shape, ottenuta.shape)
        )
    a = attesa.astype(np.float64)
    b = ottenuta.astype(np.float64)
    den = np.where(np.abs(a) > 0, np.abs(a), 1.0)
    rel = np.abs(a - b) / den
    return {
        "bit_a_bit": bool(np.array_equal(attesa.view(np.uint8), ottenuta.view(np.uint8))),
        "rel_max": float(rel.max()),
        "rel_mediana": float(np.median(rel)),
        "bin_peggiore": int(np.argmax(rel)),
    }


def scrivi_kref(out_path: Path, k: np.ndarray, sorgente: str) -> dict:
    """Salva la griglia k in un file NUOVO. Rifiuta di sovrascrivere."""
    if out_path.exists():
        raise SystemExit(
            "FALLIMENTO: %s esiste gia'. Un file di riferimento non si riscrive: "
            "confrontalo, oppure scegli un altro nome." % out_path
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out_path, k3D=np.asarray(k, dtype=np.float64),
             sorgente=np.array([sorgente]))
    return {"path": str(out_path), "sha256": sha256_file(out_path), "n_k": int(len(k))}


def comando_riproduci(npz_path: Path, nwlh_dir: Path, indici, chiave: str,
                      box: float, mas: str, out_kref: Path | None) -> dict:
    M, sha = carica_matrice(npz_path, chiave)
    n_k_cache = int(M.shape[1])

    rec = {
        "strumento": "paper2_prov_pk_riproduci/riproduci",
        "versione": VERSIONE,
        "quando": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "file": {"path": str(npz_path), "sha256": sha, "shape": [int(x) for x in M.shape]},
        "percorso_codice": {
            "sorgente": "src/phase7_r53_robustness.py::_compute_pk_matrix (HEAD)",
            "campo": NOME_CAMPO,
            "box": float(box),
            "mas_passato": mas,
            "trasformazione": "log10(clip(Pk[:,0], 1e-10)) -> float32",
            "threads": 1,
        },
        "regola_dichiarata": {
            "indici": [int(i) for i in indici],
            "chiusura": "bit a bit, oppure rel <= %g con nota" % TOL_AMMESSA,
            "altrimenti": "provenienza non ricostruibile: togliere i test B e C",
        },
        "righe": [],
    }

    k_prima = None
    for i in indici:
        i = int(i)
        if not (0 <= i < M.shape[0]):
            raise SystemExit("FALLIMENTO: indice %d fuori dalle %d righe" % (i, M.shape[0]))
        campo = nwlh_dir / str(i) / NOME_CAMPO
        k, riga = calcola_riga(campo, box, mas)
        if len(k) != n_k_cache:
            raise SystemExit(
                "FALLIMENTO: %d bin ricalcolati contro %d nel cache: non e' lo stesso "
                "percorso di codice o non e' la stessa griglia" % (len(k), n_k_cache)
            )
        if k_prima is None:
            k_prima = k
        elif not np.allclose(k, k_prima, rtol=0, atol=0):
            raise SystemExit("FALLIMENTO: la griglia k non e' identica fra realizzazioni")
        esito = confronta_riga(M[i], riga)
        esito["riga"] = i
        esito["campo"] = str(campo)
        rec["righe"].append(esito)

    bit = all(r["bit_a_bit"] for r in rec["righe"])
    entro = all(r["rel_max"] <= TOL_AMMESSA for r in rec["righe"])
    rec["k"] = {
        "n_k": int(len(k_prima)),
        "k_min": float(k_prima.min()),
        "k_max": float(k_prima.max()),
        "primi_tre": [float(x) for x in k_prima[:3]],
    }
    if out_kref is not None and (bit or entro):
        rec["kref"] = scrivi_kref(out_kref, k_prima,
                                  "PKL.Pk(%s, %.1f, axis=0, MAS=%s).k3D, realizzazione %d"
                                  % (NOME_CAMPO, box, mas, int(indici[0])))
    rec["verdetto"] = {
        "bit_a_bit": bool(bit),
        "entro_tolleranza": bool(entro),
        "esito": ("CHIUSI 2, 3 e 4 (bit a bit)" if bit
                  else ("CHIUSI 2, 3 e 4, con nota di versione" if entro
                        else "NON RICOSTRUIBILE: togliere i test B e C")),
    }
    if sha256_file(npz_path) != sha:
        raise SystemExit("FALLIMENTO: il cache e' cambiato durante la riproduzione")
    rec["cache_intatto"] = True
    return rec


# ------------------------------------------------------------------- selftest

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

    print("selftest paper2_prov_pk_riproduci v%s" % VERSIONE)
    rng = np.random.default_rng(3)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)

        # --- confronta_riga
        a = rng.normal(size=110).astype(np.float32)
        check(confronta_riga(a, a.copy())["bit_a_bit"] is True, "confronta_riga: copia identica, bit a bit")
        check(confronta_riga(a, a.copy())["rel_max"] == 0.0, "confronta_riga: rel 0 su copia")
        b = a.copy()
        b[7] = np.float32(np.nextafter(np.float32(b[7]), np.float32(np.inf)))
        c = confronta_riga(a, b)
        check(c["bit_a_bit"] is False, "confronta_riga: un ulp non e' bit a bit")
        check(c["rel_max"] <= TOL_AMMESSA, "confronta_riga: un ulp sta entro 1e-6")
        check(c["bin_peggiore"] == 7, "confronta_riga: individua il bin peggiore")
        b2 = a.copy()
        b2[3] = a[3] * np.float32(1.001)
        check(confronta_riga(a, b2)["rel_max"] > TOL_AMMESSA, "DIFETTO: scarto 1e-3 oltre tolleranza")
        try:
            confronta_riga(a, a[:50])
            check(False, "lunghezze diverse devono fallire")
        except SystemExit:
            check(True, "DIFETTO: lunghezze diverse falliscono in modo esplicito")

        # --- rel_vs_media_altre, dati puliti
        M = (4.0 + rng.normal(scale=0.5, size=(300, 110))).astype(np.float32)
        rel = rel_vs_media_altre(M)
        check(rel.min() > SOGLIA_RIEMPIMENTO * 100, "riempimento: dati puliti, nessuna riga vicina alla media")

        # --- DIFETTO: un riempimento SINGOLO, che i duplicati non vedono
        Mf = M.copy()
        altre = np.delete(np.arange(300), 42)
        Mf[42] = Mf[altre].astype(np.float64).mean(axis=0).astype(np.float32)
        uni = np.unique(Mf, axis=0)
        check(uni.shape[0] == 300, "DIFETTO: il riempimento singolo NON e' un duplicato")
        relf = rel_vs_media_altre(Mf)
        check(int(np.argmin(relf)) == 42, "DIFETTO: il riempimento singolo e' la riga piu' vicina alla media")
        check(relf[42] < SOGLIA_RIEMPIMENTO, "DIFETTO: riempimento singolo sotto la soglia")

        np.savez(d / "pulito.npz", pk_matrix=M)
        np.savez(d / "riempito.npz", pk_matrix=Mf)
        r_ok = comando_riempimento(d / "pulito.npz", "pk_matrix", SOGLIA_RIEMPIMENTO)
        check(r_ok["verdetto"]["riempimento_singolo"] is False, "riempimento: verdetto negativo su dati puliti")
        r_no = comando_riempimento(d / "riempito.npz", "pk_matrix", SOGLIA_RIEMPIMENTO)
        check(r_no["righe_sospette"] == [42], "riempimento: riga 42 segnalata")
        check(len(r_no["prime_cinque"]) == 5, "riempimento: cinque righe piu' vicine riportate")

        # --- chiave assente e file mancante
        try:
            comando_riempimento(d / "pulito.npz", "non_esiste", SOGLIA_RIEMPIMENTO)
            check(False, "chiave assente deve fallire")
        except SystemExit:
            check(True, "DIFETTO: chiave assente fallisce")
        try:
            comando_riempimento(d / "assente.npz", "pk_matrix", SOGLIA_RIEMPIMENTO)
            check(False, "file assente deve fallire")
        except SystemExit:
            check(True, "DIFETTO: file assente fallisce")

        # --- scrivi_kref: crea una volta, poi rifiuta
        kk = np.logspace(-2.2, 0.3, 110)
        info = scrivi_kref(d / "kref.npz", kk, "prova")
        check(info["n_k"] == 110 and Path(info["path"]).is_file(), "kref: file creato con 110 bin")
        with np.load(d / "kref.npz", allow_pickle=False) as f:
            check(np.allclose(f["k3D"], kk) and f["sorgente"][0] == "prova", "kref: contenuto e sorgente")
        try:
            scrivi_kref(d / "kref.npz", kk, "prova")
            check(False, "kref esistente deve essere rifiutato")
        except SystemExit:
            check(True, "DIFETTO: kref non viene sovrascritto")

        # --- log append-only
        out = d / "logs" / "rip.jsonl"
        appendi_jsonl(out, r_ok)
        prima = out.read_text(encoding="utf-8")
        appendi_jsonl(out, r_no)
        dopo = out.read_text(encoding="utf-8")
        check(dopo.startswith(prima) and len(dopo.strip().splitlines()) == 2,
              "log append-only con due righe")
        check(json.loads(dopo.strip().splitlines()[1])["righe_sospette"] == [42],
              "il record JSONL rilegge il verdetto")

    print("\nselftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


# ----------------------------------------------------------------------- main

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chiusura dei punti 2, 3 e 4 della provenienza del cache P(k)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("selftest")

    r = sub.add_parser("riempimento", help="cerca un riempimento mean_pk singolo (senza Pylians)")
    r.add_argument("--npz", required=True)
    r.add_argument("--chiave", default="pk_matrix")
    r.add_argument("--soglia", type=float, default=SOGLIA_RIEMPIMENTO)
    r.add_argument("--out", default=None)

    q = sub.add_parser("riproduci", help="ricalcola le righe dichiarate e confronta bit a bit")
    q.add_argument("--npz", required=True)
    q.add_argument("--nwlh-dir", required=True)
    q.add_argument("--indici", default=",".join(str(i) for i in INDICI_DICHIARATI))
    q.add_argument("--chiave", default="pk_matrix")
    q.add_argument("--box", type=float, default=BOX_SIZE)
    q.add_argument("--mas", default=MAS_CODICE)
    q.add_argument("--out-kref", default=None)
    q.add_argument("--out", default=None)

    a = p.parse_args(argv)

    if a.cmd == "selftest":
        return selftest()

    if a.cmd == "riempimento":
        rec = comando_riempimento(Path(a.npz), a.chiave, a.soglia)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        if a.out:
            appendi_jsonl(Path(a.out), rec)
        print("\n== RIEMPIMENTO ==\nrel minima: %.3e (riga %d)\nmediana: %.3e\nsospette: %s\n"
              % (rec["rel_minima"], rec["riga_piu_vicina_alla_media"], rec["mediana_rel"],
                 rec["righe_sospette"] or "nessuna"), file=sys.stderr)
        return 0

    indici = [int(x) for x in str(a.indici).split(",") if x.strip() != ""]
    if len(indici) < 3:
        raise SystemExit("FALLIMENTO: la regola dichiara almeno tre indici")
    rec = comando_riproduci(Path(a.npz), Path(a.nwlh_dir), indici, a.chiave, a.box, a.mas,
                            Path(a.out_kref) if a.out_kref else None)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    if a.out:
        appendi_jsonl(Path(a.out), rec)
    print("\n== RIPRODUZIONE ==\n%s\n" % rec["verdetto"]["esito"], file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

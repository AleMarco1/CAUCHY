#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_incrocio_cache.py — i digest del registro contro i file su disco.

IL CONTROLLO CHE OGGI NESSUNO FA
--------------------------------
Il runner di 4.2a scrive, per ogni realizzazione, il campo delta del ramo FKP in
data/processed/paper2_mock_deltas_v2/<REG>/delta_NNNN.npy e deposita nel record
il suo `delta_sha256`, calcolato sui BYTE DEL FILE (il campo `delta_sha_su` lo
dichiara). Nessuno ha mai verificato che i due coincidano.

E' il difetto che il record 53 ha chiuso per la cache di v1 — gli ingressi
dell'ensemble non erano manifestati — in una forma piu' insidiosa: qui il
digest c'e', sta nel registro, e proprio per questo nessuno pensa a
controllarlo. Un file riscritto, troncato o sostituito dopo il run passerebbe
inosservato, e l'ensemble v2 poggia su quei 4000 file.

paper2_manifest_cache.py verifica MANIFEST contro DISCO. Questo verifica
REGISTRO contro DISCO, che e' l'anello mancante: e' il registro a portare i
risultati, e se il suo digest non descrive il file che c'e' adesso, la
tracciabilita' e' apparente.

I TRE CANCELLI
--------------
  1. ogni record con `delta_file` deve avere il suo file, e il sha256 del file
     deve coincidere con quello depositato;
  2. ogni file nella cache deve avere un record che lo rivendica — un file
     orfano significa che qualcosa ha scritto li' dentro fuori dal runner;
  3. i record scritti SENZA --cache-delta portano un digest sui byte grezzi e
     nessun file: si contano e si dichiarano, non si ignorano.

USO
    python src\\paper2_incrocio_cache.py selftest
    python src\\paper2_incrocio_cache.py incrocia --region NGC
    python src\\paper2_incrocio_cache.py incrocia --region SGC --n 50

Uscita: 0 se i tre cancelli passano, 1 se no, 2 su errore d'uso.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BLOCCO = 1 << 22          # 4 MiB per lettura
ROOT_DEFAULT = "."


def sha256_file(path, blocco=BLOCCO):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(blocco), b""):
            h.update(b)
    return h.hexdigest()


def percorsi(root, region):
    d = Path(root)
    return {"registro": d / "results" / "paper2" / ("ensemble_v2_%s.jsonl" % region),
            "cache": d / "processed_placeholder",
            "cache_default": d / "data" / "processed" / "paper2_mock_deltas_v2" / region,
            "out": d / "results" / "paper2" / ("incrocio_cache_%s.json" % region)}


def leggi_registro(path):
    """(record utili, n_smoke, n_senza_file). Un record senza indice non e' una
    realizzazione: e' il sommario, e non entra."""
    utili, smoke, senza = [], 0, 0
    with Path(path).open("r", encoding="utf-8") as fh:
        for riga in fh:
            riga = riga.strip()
            if not riga:
                continue
            r = json.loads(riga)
            if "index" not in r:
                continue
            if r.get("smoke"):
                smoke += 1
                continue
            if not r.get("delta_file"):
                senza += 1
                continue
            utili.append({"index": int(r["index"]), "file": r["delta_file"],
                          "sha": r.get("delta_sha256"),
                          "su": r.get("delta_sha_su")})
    return utili, smoke, senza


def incrocia(root, region, n=None, cache_dir=None, out_path=None):
    root = Path(root).resolve()
    P = percorsi(root, region)
    if not P["registro"].is_file():
        raise SystemExit("RIFIUTO: registro inesistente: %s" % P["registro"])
    cache = Path(cache_dir) if cache_dir else P["cache_default"]

    print("=" * 78)
    print("REGISTRO CONTRO DISCO  |  %s" % region)
    print("=" * 78)
    utili, n_smoke, n_senza = leggi_registro(P["registro"])
    print("  registro: %s" % P["registro"])
    print("  %d record con file, %d di smoke scartati, %d senza file"
          % (len(utili), n_smoke, n_senza))
    if n_senza:
        print("    (i %d senza file portano il digest sui byte grezzi: scritti "
              "senza --cache-delta, non verificabili contro il disco)" % n_senza)
    if not utili:
        raise SystemExit("RIFIUTO: nessun record con delta_file da verificare")

    # L'elenco COMPLETO degli indici rivendicati dal registro si tiene prima
    # di troncare: --n limita l'hashing (cancello 1), non la rivendicazione
    # (cancello 2). Calcolare gli orfani sui soli record verificati faceva
    # apparire orfani i record non ancora esaminati.
    nel_registro = {r["index"] for r in utili}
    if n:
        utili = utili[:n]
        print("  verifica limitata ai primi %d dei %d record"
              % (len(utili), len(nel_registro)))

    # --- cancello 1: registro -> disco -------------------------------------
    ok, mism, mancanti, senza_sha = 0, [], [], []
    byte = 0
    t0 = time.time()
    for j, r in enumerate(utili, 1):
        fp = Path(r["file"])
        if not fp.is_absolute():
            fp = root / fp
        if not fp.is_file():
            mancanti.append(r["index"])
            continue
        if not r["sha"]:
            senza_sha.append(r["index"])
            continue
        h = sha256_file(fp)
        byte += fp.stat().st_size
        if h == r["sha"]:
            ok += 1
        else:
            mism.append({"index": r["index"], "file": str(fp),
                         "registro": r["sha"], "disco": h})
        if j % 200 == 0:
            el = time.time() - t0
            print("    %d/%d  %.1f MB/s  ETA %.1f min"
                  % (j, len(utili), byte / el / 1e6,
                     el / j * (len(utili) - j) / 60))
    dt = time.time() - t0
    print("\n  --- cancello 1: i digest del registro descrivono i file su disco ---")
    print("    coincidono %d,  DISCORDI %d,  file mancanti %d,  senza digest %d"
          % (ok, len(mism), len(mancanti), len(senza_sha)))
    print("    %.2f GB verificati in %.1f min (%.0f MB/s)"
          % (byte / 1e9, dt / 60, byte / dt / 1e6 if dt else 0))
    for m in mism[:5]:
        print("      idx %d: registro %s… disco %s…"
              % (m["index"], m["registro"][:12], m["disco"][:12]))

    # --- cancello 2: disco -> registro -------------------------------------
    sul_disco = {int(p.stem.split("_")[-1]) for p in cache.glob("delta_*.npy")} \
        if cache.is_dir() else set()
    orfani = sorted(sul_disco - nel_registro)
    print("\n  --- cancello 2: ogni file ha un record che lo rivendica ---")
    print("    %d file nella cache, %d rivendicati, %d ORFANI"
          % (len(sul_disco), len(sul_disco & nel_registro), len(orfani)))
    if orfani:
        print("    primi orfani: %s" % orfani[:10])
        print("    un file orfano significa che qualcosa ha scritto nella cache")
        print("    fuori dal runner, e non e' tracciato da nessun record.")

    esito = (not mism) and (not mancanti) and (not senza_sha) and (not orfani)
    # se la verifica e' parziale, l'assenza di orfani non e' dimostrata
    parziale = bool(n) and len(utili) < len(nel_registro)
    print("\n  ESITO: %s%s" % ("PULITO" if esito else "DISCREPANZA",
                               "  (PARZIALE: %d record su %d hashati; il "
                               "cancello 2 vale, il cancello 1 no)"
                               % (len(utili), len(nel_registro))
                               if parziale else ""))

    rec = {"schema": "paper2_incrocio_cache_v1", "region": region,
           "utc": datetime.now(timezone.utc).isoformat(),
           "registro": str(P["registro"]), "cache": str(cache),
           "n_record_con_file": len(utili), "n_smoke_scartati": n_smoke,
           "n_senza_file": n_senza, "n_coincidono": ok,
           "n_discordi": len(mism), "discordi": mism[:50],
           "file_mancanti": mancanti[:50], "senza_digest": senza_sha[:50],
           "n_file_su_disco": len(sul_disco), "orfani": orfani[:50],
           "byte_verificati": byte, "secondi": dt,
           "verifica_parziale": parziale, "esito": "PULITO" if esito else "DISCREPANZA"}
    dest = Path(out_path) if out_path else P["out"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rec, indent=2, ensure_ascii=True), encoding="utf-8")
    print("  scritto: %s" % dest)
    return 0 if esito else 1


# ---------------------------------------------------------------------------

def selftest():
    ok = tot = 0

    def chk(nm, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, nm))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, nm, det))

    print("selftest paper2_incrocio_cache")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cache = td / "data" / "processed" / "paper2_mock_deltas_v2" / "NGC"
        cache.mkdir(parents=True)
        res = td / "results" / "paper2"
        res.mkdir(parents=True)

        # sha256 su file: contro hashlib diretto
        f0 = cache / "delta_0000.npy"
        f0.write_bytes(b"contenuto zero")
        chk("sha256_file coincide con hashlib sui byte",
            sha256_file(f0) == hashlib.sha256(b"contenuto zero").hexdigest())
        chk("e la lettura a blocchi non cambia il digest",
            sha256_file(f0, blocco=3) == sha256_file(f0, blocco=1 << 20))

        for i in (1, 2):
            (cache / ("delta_%04d.npy" % i)).write_bytes(b"contenuto %d" % i)

        def record(i, sha=None, file=True, smoke=False):
            r = {"index": i, "schema": "x"}
            if smoke:
                r["smoke"] = True
            if file:
                fp = cache / ("delta_%04d.npy" % i)
                r["delta_file"] = str(fp)
                r["delta_sha256"] = sha or sha256_file(fp)
                r["delta_sha_su"] = "file npy"
            else:
                r["delta_sha256"] = "0" * 64
                r["delta_sha_su"] = "byte grezzi"
            return r

        reg = res / "ensemble_v2_NGC.jsonl"

        def scrivi(righe):
            reg.write_text("\n".join(json.dumps(r) for r in righe) + "\n",
                           encoding="utf-8")

        # caso pulito
        scrivi([record(0), record(1), record(2), {"schema": "sommario"}])
        u, sm, sz = leggi_registro(reg)
        chk("il sommario non entra: non ha indice", len(u) == 3 and sm == 0)
        chk("incrocio pulito: esito 0", incrocia(td, "NGC") == 0)
        r = json.loads((res / "incrocio_cache_NGC.json").read_text(encoding="utf-8"))
        chk("tre digest coincidono, nessun discorde",
            r["n_coincidono"] == 3 and r["n_discordi"] == 0)
        chk("nessun orfano", r["orfani"] == [] and r["n_file_su_disco"] == 3)
        chk("e l'esito registrato e' PULITO", r["esito"] == "PULITO")

        # un file cambiato dopo il run: e' il caso che lo strumento esiste per prendere
        (cache / "delta_0001.npy").write_bytes(b"contenuto MANOMESSO")
        chk("un file riscritto dopo il run viene preso", incrocia(td, "NGC") == 1)
        r = json.loads((res / "incrocio_cache_NGC.json").read_text(encoding="utf-8"))
        chk("ed e' nominato per indice",
            r["n_discordi"] == 1 and r["discordi"][0]["index"] == 1, r["discordi"])
        chk("con entrambi i digest, per poterli confrontare",
            r["discordi"][0]["registro"] != r["discordi"][0]["disco"])
        (cache / "delta_0001.npy").write_bytes(b"contenuto 1")
        chk("rimesso a posto, torna pulito", incrocia(td, "NGC") == 0)

        # file mancante
        (cache / "delta_0002.npy").unlink()
        chk("un file sparito ferma", incrocia(td, "NGC") == 1)
        r = json.loads((res / "incrocio_cache_NGC.json").read_text(encoding="utf-8"))
        chk("ed e' elencato fra i mancanti", r["file_mancanti"] == [2])
        (cache / "delta_0002.npy").write_bytes(b"contenuto 2")

        # orfano: un file senza record
        (cache / "delta_0009.npy").write_bytes(b"intruso")
        chk("un file orfano ferma", incrocia(td, "NGC") == 1)
        r = json.loads((res / "incrocio_cache_NGC.json").read_text(encoding="utf-8"))
        chk("ed e' nominato", r["orfani"] == [9])
        (cache / "delta_0009.npy").unlink()

        # smoke e record senza file
        scrivi([record(0), record(1), record(2), record(5, file=False),
                dict(record(1), smoke=True, index=7)])
        chk("i record di smoke sono scartati, non verificati",
            leggi_registro(reg)[1] == 1)
        chk("quelli senza file si contano a parte", leggi_registro(reg)[2] == 1)
        scrivi([record(0), record(1), record(2)])

        # verifica parziale: il cancello 2 non e' concludente
        (cache / "delta_0009.npy").write_bytes(b"intruso")
        incrocia(td, "NGC", n=1)
        r = json.loads((res / "incrocio_cache_NGC.json").read_text(encoding="utf-8"))
        chk("con --n la verifica si dichiara PARZIALE", r["verifica_parziale"] is True)
        chk("l'orfano viene visto, e SOLO quello", r["orfani"] == [9], r["orfani"])
        chk("i record non ancora hashati NON sono orfani",
            1 not in r["orfani"] and 2 not in r["orfani"])
        chk("e il cancello 1 ha guardato un record solo", r["n_coincidono"] == 1)

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("incrocia")
    c.add_argument("--root", default=ROOT_DEFAULT)
    c.add_argument("--region", choices=["NGC", "SGC"], required=True)
    c.add_argument("--n", type=int, default=None,
                   help="verifica solo i primi n record. Rende il cancello 2 "
                        "non concludente, e lo strumento lo dichiara")
    c.add_argument("--cache", default=None)
    c.add_argument("--out", default=None)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "incrocia":
        return incrocia(a.root, a.region, a.n, a.cache, a.out)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

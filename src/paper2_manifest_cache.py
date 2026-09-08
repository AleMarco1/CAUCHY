#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_manifest_cache.py — manifesta la cache dei campi delta, che il freeze non copre.

Il tier `fields` congela results/phase8_test2_fields/, non i delta dei mock. I 4000 campi di
data/processed/paper1_mock_deltas non sono manifestati da nessuna parte, e su di essi poggia
la linea di base di v1 per quattro delle sei regole di 4.2b/4.3b.

Questo strumento produce un registro nella STESSA FORMA dei manifest del freeze
(rel, bytes, mtime_utc, sha256, scanned_at) senza creare un tier: la struttura congelata non
si tocca. Se un giorno la si vorra' promuovere a tier, la forma e' gia' quella.

RIFIUTA di scrivere su nomi riservati (ensemble_v1_manifest_*, ensemble_v1_freeze_*): un file
con quel nome verrebbe scoperto da paper2_freeze_verify come un tier che non esiste.

L'aggregato e' calcolato con una ricetta DICHIARATA nell'intestazione. Non si afferma che
coincida con quella di paper2_freeze_verify: quella e' un'altra implementazione e non la si
indovina.

Uso:
    python paper2_manifest_cache.py selftest
    python paper2_manifest_cache.py scansiona --dir data\\processed\\paper1_mock_deltas\\NGC ^
        --base . --etichetta NGC --jobs 4 ^
        --out results\\paper2\\cachedelta_manifest_NGC.jsonl ^
        --header results\\paper2\\cachedelta_header_NGC.json
    python paper2_manifest_cache.py verifica --manifest results\\paper2\\cachedelta_manifest_NGC.jsonl ^
        --base . --jobs 4
"""

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile

ESTENSIONI = (".npy", ".npz")
RISERVATI = ("ensemble_v1_manifest_", "ensemble_v1_freeze_")
RICETTA = ("sha256 over the concatenation, in ascending order of `rel`, of "
           "f'{rel}\\t{sha256}\\t{bytes}\\n' encoded utf-8")


class Rifiuto(Exception):
    pass


def sha256_file(path, blocco=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for pezzo in iter(lambda: fh.read(blocco), b""):
            h.update(pezzo)
    return h.hexdigest()


def controlla_nome(path):
    nome = os.path.basename(path)
    for r in RISERVATI:
        if nome.startswith(r):
            raise Rifiuto(f"nome riservato: '{nome}' verrebbe scoperto da paper2_freeze_verify "
                          f"come un tier. Scegli un altro nome.")


def elenca(dirpath, estensioni=ESTENSIONI):
    trovati = []
    for radice, dirs, files in os.walk(dirpath):
        dirs.sort()
        for fn in sorted(files):
            if fn.lower().endswith(tuple(estensioni)):
                trovati.append(os.path.join(radice, fn))
    return trovati


def rel_norm(path, base):
    return os.path.relpath(path, base).replace("\\", "/")


def voce(path, base, scanned_at):
    st = os.stat(path)
    return {
        "bytes": st.st_size,
        "mtime_utc": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc)
                       .replace(microsecond=0).isoformat(),
        "rel": rel_norm(path, base),
        "scanned_at": scanned_at,
        "sha256": sha256_file(path),
    }


def aggregato(voci):
    h = hashlib.sha256()
    for v in sorted(voci, key=lambda x: x["rel"]):
        h.update(f"{v['rel']}\t{v['sha256']}\t{v['bytes']}\n".encode("utf-8"))
    return h.hexdigest()


def scrivi_jsonl(path, voci):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        for v in sorted(voci, key=lambda x: x["rel"]):
            fh.write(json.dumps(v, sort_keys=True) + "\n")


def leggi_jsonl(path):
    voci = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, riga in enumerate(fh, 1):
            riga = riga.strip()
            if not riga:
                continue
            try:
                voci.append(json.loads(riga))
            except Exception:
                raise Rifiuto(f"{os.path.basename(path)} riga {i}: JSON malformato")
    return voci


def cmd_scansiona(args):
    try:
        controlla_nome(args.out)
        if args.header:
            controlla_nome(args.header)
        if not os.path.isdir(args.dir):
            raise Rifiuto(f"cartella inesistente: {args.dir}")
        base = os.path.abspath(args.base)
        percorsi = elenca(args.dir)
        if not percorsi:
            raise Rifiuto(f"nessun file {ESTENSIONI} sotto {args.dir}")
        scanned_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        if args.jobs > 1:
            with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
                voci = list(ex.map(lambda p: voce(p, base, scanned_at), percorsi))
        else:
            voci = [voce(p, base, scanned_at) for p in percorsi]
    except Rifiuto as e:
        print(f"RIFIUTO: {e}")
        return 2

    agg = aggregato(voci)
    tot = sum(v["bytes"] for v in voci)
    scrivi_jsonl(args.out, voci)

    intestazione = {
        "aggregate_recipe": RICETTA,
        "aggregate_sha256": agg,
        "body": rel_norm(os.path.abspath(args.out), base),
        "etichetta": args.etichetta,
        "is_freeze_tier": False,
        "n_files": len(voci),
        "note": ("Manifest of an input cache that the freeze does not cover. Same shape as the "
                 "freeze manifests, deliberately NOT a tier. The aggregate uses the recipe "
                 "declared here and is not asserted to equal the one of paper2_freeze_verify."),
        "root": rel_norm(os.path.abspath(args.dir), base),
        "scanned_at": scanned_at,
        "total_bytes": tot,
    }
    if args.header:
        os.makedirs(os.path.dirname(os.path.abspath(args.header)) or ".", exist_ok=True)
        with open(args.header, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(intestazione, indent=1, sort_keys=True) + "\n")

    print(f"radice    : {intestazione['root']}")
    print(f"file      : {len(voci)}")
    print(f"byte      : {tot:,}")
    print(f"aggregato : {agg[:12]}…")
    print(f"corpo     : {os.path.abspath(args.out)}")
    if args.header:
        print(f"intestaz. : {os.path.abspath(args.header)}")
    return 0


def cmd_verifica(args):
    try:
        voci = leggi_jsonl(args.manifest)
        if not voci:
            raise Rifiuto("manifest vuoto")
        base = os.path.abspath(args.base)
    except Rifiuto as e:
        print(f"RIFIUTO: {e}")
        return 2

    def controlla(v):
        p = os.path.join(base, v["rel"])
        if not os.path.isfile(p):
            return ("MISSING", v["rel"], None)
        if os.path.getsize(p) != v["bytes"]:
            return ("MISMATCH", v["rel"], "bytes")
        if sha256_file(p) != v["sha256"]:
            return ("MISMATCH", v["rel"], "sha256")
        return ("OK", v["rel"], None)

    if args.jobs > 1:
        with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
            esiti = list(ex.map(controlla, voci))
    else:
        esiti = [controlla(v) for v in voci]

    conta = {"OK": 0, "MISMATCH": 0, "MISSING": 0}
    for stato, rel, perche in esiti:
        conta[stato] += 1
        if stato != "OK":
            print(f"  {stato:9s} {rel}" + (f"  ({perche})" if perche else ""))

    radice = os.path.join(base, os.path.dirname(voci[0]["rel"]))
    extra = []
    if os.path.isdir(radice):
        attesi = {v["rel"] for v in voci}
        for p in elenca(radice):
            r = rel_norm(p, base)
            if r not in attesi:
                extra.append(r)
    for r in extra[:20]:
        print(f"  EXTRA     {r}")

    agg = aggregato(voci)
    print(f"manifest  : {len(voci)} voci  aggregato {agg[:12]}…")
    print(f"esiti     : OK {conta['OK']}  MISMATCH {conta['MISMATCH']}  "
          f"MISSING {conta['MISSING']}  EXTRA {len(extra)}")
    pulito = conta["MISMATCH"] == 0 and conta["MISSING"] == 0 and not extra
    print("CACHE INTEGRA" if pulito else "CACHE NON INTEGRA")
    return 0 if pulito else 2


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="manifcache_")
    cache = os.path.join(base, "data", "cache", "NGC")
    os.makedirs(cache)
    for i in range(5):
        with open(os.path.join(cache, f"delta_{i:04d}.npy"), "wb") as fh:
            fh.write(bytes([i]) * (1000 + i))
    with open(os.path.join(cache, "note.txt"), "w") as fh:
        fh.write("non e' un campo")

    out = os.path.join(base, "results", "cachedelta_manifest_NGC.jsonl")
    hdr = os.path.join(base, "results", "cachedelta_header_NGC.json")

    class A:
        pass

    def a_scan(**kw):
        x = A(); x.dir = cache; x.base = base; x.etichetta = "NGC"; x.jobs = 1
        x.out = out; x.header = hdr
        for k, v in kw.items():
            setattr(x, k, v)
        return x

    def a_ver(**kw):
        x = A(); x.manifest = out; x.base = base; x.jobs = 1
        for k, v in kw.items():
            setattr(x, k, v)
        return x

    ok("1 scansione: esito 0", cmd_scansiona(a_scan()) == 0)
    voci = leggi_jsonl(out)
    ok("2 cinque campi, il .txt escluso", len(voci) == 5)
    ok("3 chiavi nella forma dei manifest del freeze",
       set(voci[0]) == {"bytes", "mtime_utc", "rel", "scanned_at", "sha256"})
    ok("4 rel con separatori a barra e relativo a base",
       all(v["rel"].startswith("data/cache/NGC/") for v in voci))
    ok("5 corpo ordinato per rel", [v["rel"] for v in voci] == sorted(v["rel"] for v in voci))
    with open(out, "rb") as fh:
        raw = fh.read()
    ok("6 nessun CRLF nel corpo", b"\r\n" not in raw)
    intest = json.load(open(hdr, encoding="utf-8"))
    ok("7 intestazione: conteggio e byte coerenti col corpo",
       intest["n_files"] == 5 and intest["total_bytes"] == sum(v["bytes"] for v in voci))
    ok("8 intestazione dichiara di non essere un tier", intest["is_freeze_tier"] is False)
    ok("9 la ricetta dell'aggregato e' dichiarata", "sha256 over the concatenation" in intest["aggregate_recipe"])

    ok("10 verifica su cache intatta: integra", cmd_verifica(a_ver()) == 0)

    # un byte cambiato
    p0 = os.path.join(cache, "delta_0000.npy")
    dati = open(p0, "rb").read()
    with open(p0, "wb") as fh:
        fh.write(b"\xff" + dati[1:])
    ok("11 byte cambiato a parita' di dimensione: MISMATCH", cmd_verifica(a_ver()) == 2)
    with open(p0, "wb") as fh:
        fh.write(dati)
    ok("12 ripristinato: torna integra", cmd_verifica(a_ver()) == 0)

    # file mancante
    p4 = os.path.join(cache, "delta_0004.npy")
    d4 = open(p4, "rb").read()
    os.remove(p4)
    ok("13 file rimosso: MISSING", cmd_verifica(a_ver()) == 2)
    with open(p4, "wb") as fh:
        fh.write(d4)

    # file in piu'
    p5 = os.path.join(cache, "delta_0005.npy")
    with open(p5, "wb") as fh:
        fh.write(b"x" * 10)
    ok("14 file non manifestato: EXTRA", cmd_verifica(a_ver()) == 2)
    os.remove(p5)
    ok("15 rimosso l'extra: torna integra", cmd_verifica(a_ver()) == 0)

    # l'aggregato risponde al contenuto
    agg1 = aggregato(leggi_jsonl(out))
    with open(p0, "wb") as fh:
        fh.write(b"\xff" + dati[1:])
    cmd_scansiona(a_scan())
    agg2 = aggregato(leggi_jsonl(out))
    ok("16 l'aggregato cambia se cambia un campo", agg1 != agg2)
    with open(p0, "wb") as fh:
        fh.write(dati)
    cmd_scansiona(a_scan())
    ok("17 e torna identico al ripristino", aggregato(leggi_jsonl(out)) == agg1)

    # nomi riservati
    ok("18 nome di tier riservato: rifiuto",
       cmd_scansiona(a_scan(out=os.path.join(base, "results",
                                             "ensemble_v1_manifest_cache.jsonl"))) == 2)
    ok("19 intestazione con nome riservato: rifiuto",
       cmd_scansiona(a_scan(header=os.path.join(base, "results",
                                                "ensemble_v1_freeze_cache.json"))) == 2)

    # jobs > 1 deve dare lo stesso risultato
    out2 = os.path.join(base, "results", "parallelo.jsonl")
    cmd_scansiona(a_scan(out=out2, header=None, jobs=4))
    ok("20 con --jobs 4 il corpo e' identico",
       [dict(v, scanned_at=None) for v in leggi_jsonl(out2)]
       == [dict(v, scanned_at=None) for v in leggi_jsonl(out)])

    passati = sum(1 for _, c in controlli if c)
    print()
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print(f"selftest: {passati}/{len(controlli)}")
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_s = sub.add_parser("scansiona")
    p_s.add_argument("--dir", required=True)
    p_s.add_argument("--base", default=".")
    p_s.add_argument("--etichetta", default="")
    p_s.add_argument("--out", required=True)
    p_s.add_argument("--header", default=None)
    p_s.add_argument("--jobs", type=int, default=1)
    p_s.set_defaults(func=cmd_scansiona)

    p_v = sub.add_parser("verifica")
    p_v.add_argument("--manifest", required=True)
    p_v.add_argument("--base", default=".")
    p_v.add_argument("--jobs", type=int, default=1)
    p_v.set_defaults(func=cmd_verifica)

    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

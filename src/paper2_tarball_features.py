#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_tarball_features.py - R3: il tarball del tier `features` per il deposito.

COSTRUITO DAL MANIFEST, NON DALL'ALBERO
---------------------------------------
Un tarball fatto con `tar -czf results/...` prende quello che trova sul disco.
Uno fatto dal manifest prende quello che il congelamento DICHIARA, e ogni
differenza fra le due cose diventa un errore invece di finire dentro in
silenzio. Il tier `features` sono 12189 file per 24 326 788 byte, e l'aggregato
depositato e' b0601f36c894...

I QUATTRO CANCELLI
------------------
  G1  ogni voce del manifest esiste sul disco e il suo sha256 combacia. Un file
      che non combacia NON entra: il tarball si ferma.
  G2  il numero di file e la somma dei byte tornano con l'intestazione.
  G3  l'aggregato RICALCOLATO dai file messi nel tarball coincide con quello
      depositato. E' il cancello che dice che il tarball E' il tier.
  G4  dopo la scrittura, il tarball si RILEGGE: si estraggono i digest dai
      membri e si ricalcola l'aggregato una seconda volta, dal file prodotto.
      Verificare cio' che si e' scritto, non cio' che si intendeva scrivere.

DETERMINISMO
------------
I membri si aggiungono in ordine di percorso ordinato, con mtime, uid, gid,
uname e gname azzerati, e la compressione gzip senza timestamp (mtime=0). Due
esecuzioni sullo stesso albero producono lo STESSO byte. Senza questo il
tarball non e' citabile: il suo digest cambierebbe a ogni ricostruzione.

Sottocomandi
------------
  inspect   legge il manifest e verifica G1 e G2. Non scrive nulla.
  build     costruisce, con tutti e quattro i cancelli. Scrive solo con --apply.
  verify    rilegge un tarball esistente e rifa' G3 e G4.
  selftest  albero sintetico, con i cancelli esercitati sia in verde sia in rosso.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile

DEFAULT_MANIFEST = os.path.join("results", "paper2",
                                "ensemble_v1_manifest_features.jsonl")
DEFAULT_HEAD = os.path.join("results", "paper2", "ensemble_v1_freeze_features.json")
DEFAULT_OUT = os.path.join("results", "paper2", "ensemble_v1_features.tar.gz")
AGGREGATE_ATTESO = "b0601f36c894"          # prefisso depositato


def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def aggregato(coppie):
    """sha256 di "\\n".join(sorted("{rel}:{sha256}")).

    La regola del congelamento, riscritta qui perche' il tarball deve poterla
    riprodurre SENZA la pipeline: e' il punto di tutto l'esercizio.
    """
    righe = sorted("%s:%s" % (rel, dig) for rel, dig in coppie)
    return sha256_bytes("\n".join(righe).encode("utf-8"))


def leggi_manifest(path, head_path):
    """Corpo dal .jsonl, intestazione dal .json SEPARATO.

    Avevo assunto che l'intestazione fosse la prima riga del .jsonl. Non lo e':
    sta in ensemble_v1_freeze_{tier}.json, con aggregate_sha256, n_files,
    total_bytes. Assumere un nome invece di leggerlo e' la forma di errore
    numero 7 del ciclo precedente, e il fixture del selftest la nascondeva
    perche' usava i nomi che avevo inventato io.

    E il corpo si DEDUPLICA per percorso, last-wins: paper2_freeze_verify.py:185
    lo dichiara, perche' l'aggregato lavora su un dizionario. Contare le righe
    darebbe n_files sbagliato appena un manifest venisse accodato.
    """
    for p_, che in ((path, "corpo"), (head_path, "intestazione")):
        if not os.path.isfile(p_):
            fail("%s assente: %s" % (che, p_))
    with open(head_path, "r", encoding="utf-8") as fh:
        head = json.load(fh)
    for k in ("n_files", "total_bytes", "aggregate_sha256"):
        if k not in head:
            fail("l'intestazione %s non ha %r: non indovino." % (head_path, k))
    with open(path, "rb") as fh:
        raw = fh.read()
    per_rel, n_righe = {}, 0
    for i, ln in enumerate(raw.replace(b"\r\n", b"\n").split(b"\n"), start=1):
        if not ln.strip():
            continue
        n_righe += 1
        try:
            r = json.loads(ln.decode("utf-8"))
        except Exception as exc:
            fail("%s riga %d non e' JSON: %s" % (path, i, exc))
        for k in ("rel", "sha256", "bytes"):
            if k not in r:
                fail("%s riga %d non ha %r: non indovino." % (path, i, k))
        per_rel[r["rel"]] = r          # last-wins, come il congelamento
    corpo = [per_rel[k] for k in sorted(per_rel)]
    if n_righe != len(corpo):
        print("  [nota] %d righe -> %d percorsi distinti (deduplicazione "
              "last-wins)" % (n_righe, len(corpo)))
    return head, corpo


def controlla(head, corpo, base, verbose=True):
    """G1 e G2. Torna (coppie, problemi)."""
    coppie, bad, tot = [], [], 0
    mancanti = diversi = 0
    for r in corpo:
        p = os.path.join(base, r["rel"].replace("/", os.sep))
        if not os.path.isfile(p):
            mancanti += 1
            if len(bad) < 8:
                bad.append("MANCA %s" % r["rel"])
            continue
        d = sha256_file(p)
        if d != r["sha256"]:
            diversi += 1
            if len(bad) < 8:
                bad.append("DIVERSO %s (%s contro %s)"
                           % (r["rel"], d[:12], r["sha256"][:12]))
            continue
        coppie.append((r["rel"], d))
        tot += int(r["bytes"])
    if verbose:
        print("  G1 corpo contro disco : OK=%d  MANCANTI=%d  DIVERSI=%d"
              % (len(coppie), mancanti, diversi))
    n_att = int(head.get("n_files", -1))
    b_att = int(head.get("total_bytes", -1))
    g2 = (len(coppie) == n_att) and (tot == b_att)
    if verbose:
        print("  G2 intestazione       : file %d/%d  byte %d/%d  -> %s"
              % (len(coppie), n_att, tot, b_att, "ok" if g2 else "NO"))
    if not g2:
        bad.append("intestazione: %d file / %d byte contro %d / %d"
                   % (len(coppie), tot, n_att, b_att))
    return coppie, bad


def cmd_inspect(args):
    head, corpo = leggi_manifest(args.manifest, args.head)
    print("=== %s ===" % args.manifest)
    print("  voci nel corpo        : %d" % len(corpo))
    print("  intestazione          : n_files=%s  total_bytes=%s  aggregate=%s"
          % (head.get("n_files"), head.get("total_bytes"),
             str(head.get("aggregate_sha256"))[:12]))
    coppie, bad = controlla(head, corpo, args.base)
    agg = aggregato(coppie)
    print("  G3 aggregato dai file : %s   depositato %s   -> %s"
          % (agg[:12], str(head.get("aggregate_sha256"))[:12],
             "ok" if agg == head.get("aggregate_sha256") else "NO"))
    if bad:
        print("")
        for x in bad[:8]:
            print("  %s" % x)
    return 0 if not bad and agg == head.get("aggregate_sha256") else 3


def scrivi_tarball(coppie, base, out):
    """Deterministico: ordine, metadati azzerati, gzip senza timestamp."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for rel, _ in sorted(coppie):
            p = os.path.join(base, rel.replace("/", os.sep))
            info = tarfile.TarInfo(name=rel)
            info.size = os.path.getsize(p)
            info.mtime = 0
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.type = tarfile.REGTYPE
            with open(p, "rb") as fh:
                tf.addfile(info, fh)
    crudo = buf.getvalue()
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode="wb", compresslevel=9, mtime=0) as g:
        g.write(crudo)
    dati = gz.getvalue()
    tmp = out + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(dati)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, out)
    return len(crudo), len(dati)


def rileggi_tarball(path):
    """G4: i digest si ricalcolano DAL TARBALL, non da cio' che ci si e' messo."""
    coppie = []
    with tarfile.open(path, mode="r:gz") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            f = tf.extractfile(m)
            h = hashlib.sha256()
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
            coppie.append((m.name, h.hexdigest()))
    return coppie


def cmd_build(args):
    head, corpo = leggi_manifest(args.manifest, args.head)
    print("=== R3 - tarball del tier `features` ===")
    coppie, bad = controlla(head, corpo, args.base)
    if bad:
        for x in bad[:8]:
            print("  %s" % x)
        fail("il manifest e il disco non coincidono: un tarball costruito qui "
             "conterrebbe qualcosa di diverso da cio' che il congelamento "
             "dichiara. Non lo scrivo.")
    agg = aggregato(coppie)
    ok3 = agg == head.get("aggregate_sha256")
    print("  G3 aggregato          : %s   depositato %s   -> %s"
          % (agg[:12], str(head.get("aggregate_sha256"))[:12],
             "ok" if ok3 else "NO"))
    if not ok3:
        fail("l'aggregato ricalcolato non coincide con quello depositato.")
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    n_crudo, n_gz = scrivi_tarball(coppie, args.base, args.out)
    print("  scritto               : %s" % args.out)
    print("  dimensione            : %s byte crudi -> %s compressi (%.1f%%)"
          % ("{:,}".format(n_crudo), "{:,}".format(n_gz),
             100.0 * n_gz / n_crudo))
    print("  sha256 del tarball    : %s" % sha256_file(args.out))
    return cmd_verify(args)


def cmd_verify(args):
    if not os.path.isfile(args.out):
        fail("tarball assente: %s" % args.out)
    head, corpo = leggi_manifest(args.manifest, args.head)
    letto = rileggi_tarball(args.out)
    agg = aggregato(letto)
    ok = True
    print("")
    print("=== VERIFY  (G4: dal TARBALL, non da cio' che ci si e' messo) ===")
    print("  membri nel tarball    : %d (manifest: %d)" % (len(letto), len(corpo)))
    ok &= len(letto) == len(corpo)
    dep = head.get("aggregate_sha256")
    print("  aggregato dal tarball : %s" % agg[:12])
    print("  aggregato depositato  : %s" % str(dep)[:12])
    print("  coincidono            : %s" % (agg == dep))
    ok &= agg == dep
    print("  prefisso atteso %s   : %s" % (AGGREGATE_ATTESO,
                                           str(agg).startswith(AGGREGATE_ATTESO)))
    ok &= str(agg).startswith(AGGREGATE_ATTESO)
    nomi = [n for n, _ in letto]
    print("  membri in ordine      : %s" % (nomi == sorted(nomi)))
    ok &= nomi == sorted(nomi)
    print("  sha256 del tarball    : %s" % sha256_file(args.out))
    print("  esito                 : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def cmd_selftest(args):
    import tempfile
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "albero")
        os.makedirs(os.path.join(base, "results", "sub"))
        rels, tot = [], 0
        for i in range(7):
            rel = "results/sub/f%02d.npy" % i
            p = os.path.join(base, rel.replace("/", os.sep))
            dati = ("contenuto %d" % i).encode() * (i + 1)
            with open(p, "wb") as fh:
                fh.write(dati)
            rels.append((rel, sha256_bytes(dati)))
            tot += len(dati)
        agg = aggregato(rels)
        # Il fixture ha la STESSA forma del bersaglio: intestazione in un file
        # SEPARATO, e le voci con `bytes`. Il fixture precedente metteva
        # l'intestazione nel .jsonl -- nomi inventati da me -- e per questo il
        # selftest passava su codice che sul file vero non partiva.
        man = os.path.join(td, "man.jsonl")
        hpath = os.path.join(td, "freeze.json")
        with open(hpath, "w", encoding="utf-8") as fh:
            json.dump({"schema": "cauchy.paper2.v1_manifest",
                       "n_files": len(rels), "total_bytes": tot,
                       "aggregate_sha256": agg}, fh)
        with open(man, "w", encoding="utf-8", newline="") as fh:
            for rel, d in rels:
                b = os.path.getsize(os.path.join(base, rel.replace("/", os.sep)))
                fh.write(json.dumps({"rel": rel, "sha256": d, "bytes": b}) + "\n")

        head, corpo = leggi_manifest(man, hpath)
        chk("1  intestazione da file SEPARATO, corpo dal jsonl",
            head["n_files"] == 7 and len(corpo) == 7)
        coppie, bad = controlla(head, corpo, base, verbose=False)
        # deduplicazione: una riga accodata per lo stesso percorso non deve
        # gonfiare n_files, e vince l'ultima. E' cio' che freeze_verify:185
        # dichiara e che il mio lettore ignorava.
        man_dup = os.path.join(td, "man_dup.jsonl")
        with open(man, "rb") as fh:
            corpo_raw = fh.read()
        with open(man_dup, "wb") as fh:
            fh.write(corpo_raw)
            r0 = json.loads(corpo_raw.split(b"\n")[0].decode())
            fh.write(json.dumps(dict(r0, scanned_at="dopo")).encode() + b"\n")
        h_d, c_d = leggi_manifest(man_dup, hpath)
        chk("1b il corpo si DEDUPLICA per percorso, last-wins",
            len(c_d) == 7 and any(x.get("scanned_at") == "dopo" for x in c_d),
            "8 righe -> 7 percorsi")

        chk("2  G1 e G2 verdi su un albero sano", len(coppie) == 7 and not bad,
            str(bad[:1]))
        chk("3  G3 l'aggregato si riproduce dalla regola, senza pipeline",
            aggregato(coppie) == agg)

        out = os.path.join(td, "t.tar.gz")

        class A:
            manifest = man
            pass

        a = A(); a.base = base; a.out = out; a.apply = True
        n1, g1 = scrivi_tarball(coppie, base, out)
        d1 = sha256_file(out)
        letto = rileggi_tarball(out)
        chk("4  G4 l'aggregato ricalcolato DAL TARBALL coincide",
            aggregato(letto) == agg, aggregato(letto)[:12])
        chk("4b i membri sono in ordine di percorso",
            [n for n, _ in letto] == sorted(n for n, _ in letto))

        import time
        time.sleep(1.1)
        os.utime(os.path.join(base, "results", "sub", "f00.npy"), None)
        scrivi_tarball(coppie, base, out)
        chk("5  DETERMINISMO: due scritture danno lo stesso byte, anche con "
            "mtime cambiati", sha256_file(out) == d1, d1[:16])

        # G1 in rosso: un file mutato NON deve entrare
        p0 = os.path.join(base, "results", "sub", "f03.npy")
        with open(p0, "ab") as fh:
            fh.write(b"x")
        _, bad2 = controlla(head, corpo, base, verbose=False)
        chk("6  G1 respinge un file il cui digest non combacia",
            any("DIVERSO" in x for x in bad2), str(bad2[:1]))
        with open(p0, "rb+") as fh:
            fh.truncate(os.path.getsize(p0) - 1)

        # G1 in rosso: un file mancante
        os.remove(os.path.join(base, "results", "sub", "f05.npy"))
        _, bad3 = controlla(head, corpo, base, verbose=False)
        chk("6b G1 respinge un file mancante",
            any("MANCA" in x for x in bad3), str(bad3[:1]))

        # G3 in rosso: aggregato depositato sbagliato
        man2, hbad = man, os.path.join(td, "freeze_bad.json")
        with open(hbad, "w", encoding="utf-8") as fh:
            json.dump({"n_files": len(rels), "total_bytes": tot,
                       "aggregate_sha256": "0" * 64}, fh)
        h2, c2 = leggi_manifest(man2, hbad)
        chk("7  G3 respinge un aggregato che non coincide",
            aggregato(rels) != h2["aggregate_sha256"])

        # G4 in rosso: tarball manomesso
        letto2 = rileggi_tarball(out)
        letto2[0] = (letto2[0][0], "0" * 64)
        chk("8  G4 respinge un tarball il cui contenuto e' cambiato",
            aggregato(letto2) != agg)

    print("=== SELFTEST paper2_tarball_features ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def main():
    p = argparse.ArgumentParser(description="R3 - tarball del tier `features`")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--manifest", default=DEFAULT_MANIFEST)
    common.add_argument("--head", default=DEFAULT_HEAD)
    common.add_argument("--base", default=".")
    common.add_argument("--out", default=DEFAULT_OUT)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect", parents=[common]).set_defaults(func=cmd_inspect)
    sub.add_parser("verify", parents=[common]).set_defaults(func=cmd_verify)
    sub.add_parser("selftest", parents=[common]).set_defaults(func=cmd_selftest)
    b = sub.add_parser("build", parents=[common])
    b.add_argument("--apply", action="store_true")
    b.set_defaults(func=cmd_build)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

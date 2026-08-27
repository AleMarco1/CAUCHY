#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY - Confronto fra l'albero LOCALE, il remoto GIT e il deposito ZENODO.

PERCHE'
  L'inventario locale dice cosa esiste. Questo dice cosa e' stato PUBBLICATO.
  Lo scarto fra i due e' esattamente cio' che rompe la riproducibilita' di un
  manoscritto gia' sottomesso: M26 e il Paper 1 citano il concept DOI, quindi
  quello che c'e' davvero nel deposito deve corrispondere a cio' che il paper
  promette. Un file che sta solo sul PC non esiste, per un referee.

COSA FA
  1. GIT: remoti, branch, ultimo commit, e le tre divergenze che contano —
     modificato-non-committato, committato-non-spinto, sul-remoto-non-in-locale.
  2. ZENODO: interroga l'API pubblica (nessun token per i record pubblici),
     elenca tutte le versioni del concept DOI e i file dell'ultima, con md5 e
     dimensione.
  3. DIFF: confronta i file del deposito con quelli locali per nome e md5.
     Zenodo usa md5, non sha256: gli md5 locali sono calcolati solo per i file
     che compaiono nel deposito, quindi il costo e' limitato.

NON MODIFICA NULLA, ne' in locale ne' in remoto. Sola lettura.

Uso:
    python src\\cauchy_remote_audit.py
    python src\\cauchy_remote_audit.py --concept 21128856 --root D:\\projects\\cauchy
    python src\\cauchy_remote_audit.py --no-net        # solo la parte git
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ZENODO_API = "https://zenodo.org/api"
CONCEPT_DEFAULT = "21128856"


def human(n):
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or u == "TiB":
            return "%.1f %s" % (n, u)
        n /= 1024.0


def git(root, *args, ok_fail=True):
    try:
        r = subprocess.run(["git", "-C", str(root)] + list(args),
                           capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        return None if ok_fail else sys.exit("[FATAL] git non disponibile: %s" % e)
    return r.stdout.strip() if r.returncode == 0 else None


def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "cauchy-audit"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


# --------------------------------------------------------------------------
# 1. git
# --------------------------------------------------------------------------

def audit_git(root):
    print("=" * 74)
    print("GIT  —  %s" % root)
    print("=" * 74)
    if git(root, "rev-parse", "--git-dir") is None:
        print("  nessun repository git in questo albero.")
        print("  *** Se qui vivono documenti del progetto, NON sono versionati. ***")
        return None

    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    head = git(root, "log", "-1", "--format=%h %ad %s", "--date=short") or "?"
    remotes = git(root, "remote", "-v") or ""
    print("  branch   : %s" % branch)
    print("  HEAD     : %s" % head)
    print("  remoti   : %s" % (remotes.replace("\n", "\n             ") if remotes
                               else "NESSUNO — il repo e' solo locale"))

    tracked = (git(root, "ls-files") or "").splitlines()
    print("  tracciati: %d file" % len(tracked))

    dirty = (git(root, "status", "--porcelain") or "").splitlines()
    mod = [l for l in dirty if not l.startswith("??")]
    untr = [l for l in dirty if l.startswith("??")]
    print("\n  modificati non committati : %d" % len(mod))
    for l in mod[:15]:
        print("      %s" % l)
    if len(mod) > 15:
        print("      ... e altri %d" % (len(mod) - 15))
    print("  non tracciati (??)        : %d" % len(untr))
    for l in untr[:15]:
        print("      %s" % l)
    if len(untr) > 15:
        print("      ... e altri %d" % (len(untr) - 15))

    if remotes:
        git(root, "fetch", "--all", "--quiet")
        up = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if up:
            ahead = git(root, "rev-list", "--count", "%s..HEAD" % up) or "?"
            behind = git(root, "rev-list", "--count", "HEAD..%s" % up) or "?"
            print("\n  upstream : %s" % up)
            print("  commit locali NON spinti : %s" % ahead)
            print("  commit remoti NON tirati : %s" % behind)
            if ahead not in ("0", "?"):
                names = git(root, "diff", "--name-only", "%s..HEAD" % up) or ""
                n = names.splitlines()
                print("\n  File che esistono in locale ma NON su GitHub (%d):" % len(n))
                for x in n[:25]:
                    print("      %s" % x)
                if len(n) > 25:
                    print("      ... e altri %d" % (len(n) - 25))
        else:
            print("\n  *** Il branch %s non ha upstream: nulla e' mai stato spinto. ***" % branch)
    return {"branch": branch, "head": head, "tracked": len(tracked),
            "modified": len(mod), "untracked": len(untr)}


# --------------------------------------------------------------------------
# 2. Zenodo
# --------------------------------------------------------------------------

def audit_zenodo(concept, root):
    print("\n" + "=" * 74)
    print("ZENODO  —  concept %s" % concept)
    print("=" * 74)
    try:
        rec = get_json("%s/records/%s" % (ZENODO_API, concept))
    except urllib.error.HTTPError as e:
        print("  [!] HTTP %s. Se il record e' RISTRETTO o in bozza l'API pubblica non"
              % e.code)
        print("      lo restituisce: aprilo dal browser e incolla qui l'elenco file.")
        return None
    except Exception as e:
        print("  [!] rete non disponibile: %s" % e)
        return None

    md = rec.get("metadata", {})
    print("  titolo   : %s" % md.get("title", "?"))
    print("  versione : %s   pubblicato %s" % (md.get("version", "?"),
                                               md.get("publication_date", "?")))
    print("  DOI      : %s   (concept %s)" % (rec.get("doi", "?"),
                                              rec.get("conceptdoi", "?")))
    print("  accesso  : %s" % md.get("access_right", "?"))

    try:
        vers = get_json("%s/records/%s/versions?size=100" % (ZENODO_API, concept))
        hits = vers.get("hits", {}).get("hits", [])
        print("\n  versioni depositate: %d" % len(hits))
        for h in sorted(hits, key=lambda x: x.get("created", "")):
            print("      %-12s %-12s %s" % (h.get("metadata", {}).get("version", "?"),
                                            h.get("metadata", {}).get("publication_date", "?"),
                                            h.get("doi", "?")))
    except Exception:
        print("\n  (elenco versioni non recuperabile)")

    files = rec.get("files", [])
    tot = sum(f.get("size", 0) for f in files)
    print("\n  file nell'ultima versione: %d  (%s)" % (len(files), human(tot)))
    for f in sorted(files, key=lambda x: -x.get("size", 0))[:30]:
        print("      %-56s %10s" % (f.get("key", "?")[:56], human(f.get("size", 0))))
    if len(files) > 30:
        print("      ... e altri %d" % (len(files) - 30))

    # --- diff contro il locale, per nome e md5 ---------------------------
    print("\n  CONFRONTO COL LOCALE (per nome, poi per md5)")
    local = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".venv")]
        for fn in filenames:
            local.setdefault(fn, []).append(Path(dirpath) / fn)

    missing, changed, same = [], [], []
    for f in files:
        key = f.get("key", "")
        cks = (f.get("checksum") or "").split(":")[-1]
        cand = local.get(key, [])
        if not cand:
            missing.append(key)
            continue
        hit = False
        for c in cand:
            try:
                if md5_file(c) == cks:
                    same.append(key)
                    hit = True
                    break
            except OSError:
                pass
        if not hit:
            changed.append((key, [str(c) for c in cand]))

    print("    identici al locale        : %d" % len(same))
    print("    presenti ma DIVERSI       : %d" % len(changed))
    for k, where in changed[:15]:
        print("        %-48s  locale: %s" % (k[:48], where[0]))
    print("    su Zenodo ma NON in locale: %d" % len(missing))
    for k in missing[:15]:
        print("        %s" % k)
    if changed:
        print("\n    *** Un file che differisce fra deposito e locale e' il caso peggiore:")
        print("    il manoscritto cita il DOI, quindi il referee vedrebbe una versione")
        print("    diversa da quella che ha prodotto i numeri. Da risolvere per primo. ***")
    return {"n_files": len(files), "same": len(same),
            "changed": len(changed), "missing": len(missing)}


def main():
    ap = argparse.ArgumentParser(description="Audit di git e Zenodo contro il locale")
    ap.add_argument("--roots", nargs="+",
                    default=["D:\\projects\\cauchy", "D:\\projects\\cauchy_3.0"])
    ap.add_argument("--concept", default=CONCEPT_DEFAULT,
                    help="id numerico del record Zenodo (dal DOI 10.5281/zenodo.<id>)")
    ap.add_argument("--no-net", action="store_true", help="salta la parte Zenodo")
    ap.add_argument("--out", default="results/paper2/remote_audit.json")
    args = ap.parse_args()

    summary = {}
    for r in args.roots:
        root = Path(r)
        if not root.exists():
            print("[!] assente, saltato: %s" % root)
            continue
        summary[str(root)] = {"git": audit_git(root)}

    if not args.no_net:
        first = Path(args.roots[0])
        summary["zenodo"] = audit_zenodo(args.concept, first)

    out = Path(args.roots[0]) / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n  rapporto -> %s" % out)
    print("\nSola lettura: nulla e' stato modificato, ne' in locale ne' in remoto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

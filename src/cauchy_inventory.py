#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CAUCHY - Censimento dei due alberi di progetto, in vista del riordino
dell'archivio (git + Zenodo, un solo concept DOI).

Non sposta e non cancella NULLA. Legge, classifica, e scrive un rapporto.

COSA CLASSIFICA
  - per paper (M26 / Paper 1 / Paper 2 / condiviso / ignoto), da regole sui nomi
    che sono DICHIARATE nella tabella RULES e stampate nel rapporto, cosi' si
    vede subito cosa la regola ha sbagliato;
  - per destinazione proposta: git, zenodo, rigenerabile, escluso;
  - per stato git: tracciato, ignorato, non tracciato.

PERCHE' SERVE
  Il codice e' condiviso fra i paper (phase8_cutsky_mocks e' usato da tutti e
  tre), quindi l'archivio NON va spezzato per paper: si spezza per dimensione
  (git = testo piccolo e diffabile, Zenodo = binari congelati) e la struttura
  per paper la danno gli indici papers/<nome>/README.md. Questo script produce
  i dati per scrivere quegli indici.

Uso:
    python src\\cauchy_inventory.py
    python src\\cauchy_inventory.py --roots D:\\projects\\cauchy D:\\projects\\cauchy_3.0
    python src\\cauchy_inventory.py --out results\\paper2\\inventory.json --hash-small
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# regole di classificazione, dichiarate
# --------------------------------------------------------------------------

RULES = [
    # (etichetta, tipo, pattern)   il primo che combacia vince
    ("Paper 2", "prefisso", ("paper2_",)),
    ("Paper 2", "nome", ("checklist_paper2", "canovaccio_paper2", "canovaccio_paper3",
                         "canovaccio_paper4", "canovaccio_4_paper_followup")),
    ("Paper 1", "prefisso", ("paper1_",)),
    ("Paper 1", "nome", ("canovaccio_paper1",)),
    ("M26", "prefisso", ("phase6_", "phase7_", "phase9_", "m26_")),
    ("condiviso", "prefisso", ("phase8_",)),
]

# estensioni che vanno in git (testo, piccolo, diffabile)
GIT_EXT = {".py", ".md", ".txt", ".json", ".jsonl", ".csv", ".cff", ".yml", ".yaml",
           ".toml", ".cfg", ".ini", ".sh", ".ps1", ".gitattributes", ".gitignore", ".ipynb"}
# il manoscritto e il suo apparato: git, sotto papers/<nome>/
PAPER_EXT = {".tex", ".bib", ".bst", ".cls", ".sty", ".bbl", ".pdf", ".png", ".jpg",
             ".eps", ".svg", ".eml", ".docx"}
# binari congelati prodotti da NOI: candidati Zenodo
ZENODO_EXT = {".npy", ".npz", ".h5", ".hdf5", ".pkl"}
# rigenerabili: non si archiviano, si documenta la ricetta
REGEN_HINTS = ("cache", "tmp", "__pycache__", "mock_deltas", "diagrams", ".ipynb_checkpoints")
# DATO DI TERZI: pubblico, si cita col proprio DOI e NON si rideposita.
# E' il grosso dello spazio (DESI DR1, BOSS DR12, cataloghi Quijote .0) e
# mandarlo a Zenodo sarebbe una ri-pubblicazione di dato altrui.
EXTERNAL_HINTS = ("data" + os.sep + "raw", "quijote", "boss_dr12", "desi_dr1")
EXTERNAL_EXT = {".fits", ".gz", ".0"}
# copie di sicurezza: non si archiviano
BACKUP_HINTS = (".bak", "_backup", "~")
# mai
EXCLUDE_HINTS = (".git" + os.sep, "node_modules", ".venv", "venv" + os.sep, ".mypy_cache")

BIG = 50 * 1024 * 1024          # oltre questo, git non e' il posto giusto
SMALL_HASH = 5 * 1024 * 1024    # sotto questo, si puo' hashare senza costo


# secondo livello: i file di RISULTATO sono nominati per contenuto, non per paper
# (per_mock_NGC_R5.jsonl), ma il percorso lo dice. Si applica dopo le regole sul nome.
PATH_RULES = [
    ("Paper 2", ("results" + os.sep + "paper2", "papers" + os.sep + "paper2")),
    ("Paper 1", ("results" + os.sep + "paper1", "papers" + os.sep + "paper1")),
    ("M26", ("results" + os.sep + "phase6", "results" + os.sep + "phase9",
             "papers" + os.sep + "m26")),
]


def classify_paper(name, rel=""):
    low = name.lower()
    for label, kind, pats in RULES:
        for p in pats:
            if (kind == "prefisso" and low.startswith(p)) or (kind == "nome" and p in low):
                return label, "%s:%s" % (kind, p)
    rl = rel.lower().replace("/", os.sep)
    for label, pats in PATH_RULES:
        for p in pats:
            if p in rl:
                return label, "percorso:%s" % p
    return "ignoto", "-"


def classify_dest(rel, size, ext, name=""):
    r = rel.lower()
    if any(h in r for h in EXCLUDE_HINTS):
        return "escluso"
    if ext.startswith(".bak") or any(h in (name.lower() + r) for h in BACKUP_HINTS):
        return "backup"
    if ext in EXTERNAL_EXT or any(h in r for h in EXTERNAL_HINTS):
        return "esterno"
    if any(h in r for h in REGEN_HINTS):
        return "rigenerabile"
    if ext in GIT_EXT or ext in PAPER_EXT:
        return "git-troppo-grande" if size > BIG else "git"
    if ext in ZENODO_EXT:
        return "zenodo-grande" if size > 100 * 1024 * 1024 else "zenodo"
    return "da-decidere"


def git_status(root):
    """Restituisce (tracciati, ignorati) come insiemi di path relativi, o (None, None)."""
    def run(args):
        try:
            out = subprocess.run(["git", "-C", str(root)] + args,
                                 capture_output=True, text=True, timeout=120)
            return out.stdout.splitlines() if out.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    tracked = run(["ls-files"])
    if tracked is None:
        return None, None
    ignored = run(["ls-files", "--others", "--ignored", "--exclude-standard"]) or []
    norm = lambda xs: {x.replace("/", os.sep) for x in xs}
    return norm(tracked), norm(ignored)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def walk(root, do_hash):
    tracked, ignored = git_status(root)
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", ".venv", "node_modules",
                                    ".mypy_cache", ".ipynb_checkpoints")]
        for fn in filenames:
            fp = Path(dirpath) / fn
            try:
                st = fp.stat()
            except OSError:
                continue
            rel = str(fp.relative_to(root))
            ext = fp.suffix.lower()
            paper, why = classify_paper(fn, rel)
            dest = classify_dest(rel, st.st_size, ext, fn)
            row = {"root": str(root), "rel": rel, "name": fn, "ext": ext,
                   "bytes": st.st_size,
                   "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                   "paper": paper, "rule": why, "dest": dest,
                   "git": ("tracciato" if tracked is not None and rel in tracked else
                           "ignorato" if ignored is not None and rel in ignored else
                           "non-tracciato" if tracked is not None else "senza-git")}
            if do_hash and st.st_size <= SMALL_HASH and dest in ("git", "zenodo"):
                try:
                    row["sha256"] = sha256_file(fp)
                except OSError:
                    pass
            rows.append(row)
    return rows


def human(n):
    for u in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or u == "TiB":
            return "%.1f %s" % (n, u)
        n /= 1024.0


def table(rows, key, title, extra=None):
    cnt, siz = Counter(), Counter()
    for r in rows:
        cnt[r[key]] += 1
        siz[r[key]] += r["bytes"]
    print("\n%s" % title)
    print("  %-18s %8s %12s" % ("", "file", "spazio"))
    for k, _ in cnt.most_common():
        print("  %-18s %8d %12s" % (k, cnt[k], human(siz[k])))
    if extra:
        extra(cnt, siz)


def main():
    ap = argparse.ArgumentParser(description="Censimento degli alberi CAUCHY")
    ap.add_argument("--roots", nargs="+",
                    default=["D:\\projects\\cauchy", "D:\\projects\\cauchy_3.0"])
    ap.add_argument("--out", default="results/paper2/inventory.json")
    ap.add_argument("--hash-small", action="store_true",
                    help="sha256 dei file <= 5 MiB destinati a git o Zenodo")
    ap.add_argument("--top", type=int, default=20, help="quanti file grandi elencare")
    args = ap.parse_args()

    rows = []
    print("=" * 74)
    print("CAUCHY - censimento, %s" % datetime.now(timezone.utc).isoformat())
    print("=" * 74)
    for r in args.roots:
        root = Path(r)
        if not root.exists():
            print("  [!] assente, saltato: %s" % root)
            continue
        t, _ = git_status(root)
        got = walk(root, args.hash_small)
        rows += got
        print("  %-34s %6d file  %10s  git: %s"
              % (str(root), len(got), human(sum(x["bytes"] for x in got)),
                 "si (%d tracciati)" % len(t) if t is not None else "NO"))

    if not rows:
        sys.exit("[FATAL] nessun file trovato: controllare --roots.")

    table(rows, "paper", "PER PAPER")
    table(rows, "dest", "PER DESTINAZIONE PROPOSTA")
    table(rows, "git", "PER STATO GIT")
    table(rows, "ext", "PER ESTENSIONE")

    for r in rows:
        parts = r["rel"].replace("/", os.sep).split(os.sep)
        r["area"] = os.sep.join(parts[:2]) if len(parts) > 2 else (parts[0] if len(parts) > 1 else "(radice)")
    table(rows, "area", "PER AREA (primi due livelli di percorso)")

    # incroci che rivelano i problemi veri
    print("\nDA GUARDARE PER PRIMI")
    orph = [r for r in rows if r["paper"] == "ignoto" and r["dest"] in ("git", "zenodo")]
    print("  %-52s %6d" % ("file classificabili ma senza paper ('ignoto')", len(orph)))
    untr = [r for r in rows if r["git"] == "non-tracciato" and r["dest"] == "git"]
    print("  %-52s %6d" % ("destinati a git ma NON tracciati", len(untr)))
    bigg = [r for r in rows if r["dest"] == "git-troppo-grande"]
    print("  %-52s %6d" % ("testo oltre 50 MiB (git non e' il posto)", len(bigg)))
    dec = [r for r in rows if r["dest"] == "da-decidere"]
    print("  %-52s %6d" % ("estensione non prevista dalle regole", len(dec)))

    if untr:
        print("\n  Destinati a git ma non tracciati, i primi %d:" % min(args.top, len(untr)))
        for r in sorted(untr, key=lambda x: -x["bytes"])[:args.top]:
            print("    %-9s %-58s %10s" % (r["paper"], r["rel"][:58], human(r["bytes"])))

    if dec:
        print("\n  Estensioni non previste: %s"
              % ", ".join("%s(%d)" % (e, c) for e, c in
                          Counter(r["ext"] or "(nessuna)" for r in dec).most_common(12)))

    print("\n  Che cosa si archivia davvero:")
    for d in ("git", "zenodo", "zenodo-grande"):
        sel = [r for r in rows if r["dest"] == d]
        print("    %-14s %6d file  %10s" % (d, len(sel), human(sum(x["bytes"] for x in sel))))
    ext_ = [r for r in rows if r["dest"] == "esterno"]
    print("    %-14s %6d file  %10s   (dato di terzi: si cita, non si rideposita)"
          % ("esterno", len(ext_), human(sum(x["bytes"] for x in ext_))))

    print("\n  I %d file piu' grandi:" % args.top)
    for r in sorted(rows, key=lambda x: -x["bytes"])[:args.top]:
        print("    %-11s %-9s %-48s %10s"
              % (r["dest"], r["paper"], r["rel"][:48], human(r["bytes"])))

    # duplicati fra i due alberi, per nome
    byname = defaultdict(list)
    for r in rows:
        byname[r["name"]].append(r)
    dup = {k: v for k, v in byname.items()
           if len({x["root"] for x in v}) > 1}
    print("\n  Nomi presenti in ENTRAMBI gli alberi: %d" % len(dup))
    for k in sorted(dup)[:args.top]:
        sizes = " | ".join("%s: %s" % (Path(x["root"]).name, human(x["bytes"])) for x in dup[k])
        print("    %-44s %s" % (k[:44], sizes))
    if len(dup) > args.top:
        print("    ... e altri %d" % (len(dup) - args.top))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated": datetime.now(timezone.utc).isoformat(),
               "roots": args.roots, "rules": [list(x) for x in RULES],
               "path_rules": [list(x) for x in PATH_RULES],
               "n_files": len(rows), "files": rows}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n  rapporto completo -> %s  (%s)" % (out, human(out.stat().st_size)))
    print("\nNessun file e' stato spostato o cancellato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

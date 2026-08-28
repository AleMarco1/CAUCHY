#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_deposit.py — costruzione del deposito Zenodo (checklist Paper 2, voce 0.6).

Struttura prodotta in deposit/
------------------------------
  README.md                          sciolto
  MANIFEST.sha256                    sciolto, formato coreutils: `sha256sum -c` lo legge
  cauchy_code.zip                    sorgenti tracciati da git
  cauchy_manifests_v1.zip            i sei freeze (intestazioni + corpi) + reference + emendamenti
  cauchy_records_v1.zip              tier records: 224 file, 20.7 MB
  cauchy_paper2_products.zip         tier paper2_products: 28 file, 0.8 MB

I quattro tier binari (features, fields, diagrams, superseded — 28.7 GB) NON sono
caricati. I loro manifest sì: chi ha i dati può ricalcolare i sei aggregate con la regola
di tre righe documentata nel README, senza alcuno strumento di questo repository.

Tre cancelli, in ordine
-----------------------
  1. INTEGRITA'    tutti i tier devono verificare CLEAN prima che si scriva un byte.
  2. RISERVATEZZA  nessun file che assomigli a materiale di revisione entra in una zip.
                   Un archivio con DOI non si ritratta: nel repository c'e' gia' stato un
                   incidente con 85 file, fra cui referti di revisione.
  3. ALBERO PULITO il codice depositato deve corrispondere a un commit identificabile.

Le zip sono RIPRODUCIBILI: nomi ordinati, timestamp fisso, permessi fissi. Ricostruirle
dalla stessa sorgente dà lo stesso sha256, quindi il MANIFEST.sha256 è una verifica e non
una fotografia.

  python src\\paper2_deposit.py selftest
  python src\\paper2_deposit.py check
  python src\\paper2_deposit.py build --out deposit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

CHUNK = 1 << 20
FIXED_DATE = (1980, 1, 1, 0, 0, 0)      # timestamp fisso: zip riproducibili
FIXED_MODE = 0o644 << 16

# Il deposito è permanente. Questi schemi fermano la build, non la filtrano in silenzio:
# un file escluso senza che nessuno lo veda è lo stesso difetto di un file incluso senza
# che nessuno lo veda.
CONFIDENTIAL = [
    r"referee", r"reviewer", r"peer[_\- ]?review", r"review",
    r"revisione[_\- ]scientifica", r"rapporto[_\- ]referee",
    r"MN-?26-?\d{4}-?P.*\.(pdf|docx?)$", r"_R[12]_Proof", r"response[_\- ]letter",
    r"lettera[_\- ]di[_\- ]risposta",
]
CONF_RE = [re.compile(p, re.I) for p in CONFIDENTIAL]

# Il nome non basta: un referto integrale puo' stare in un file chiamato notes.md.
# `CAUCHY_Review_and_GATE.md` sfuggiva a \breview\b perche' '_' e' un carattere di
# parola, e comunque il rischio e' nel CONTENUTO. Questi termini si cercano dentro i
# file di testo; sono deliberatamente ampi, perche' un falso positivo costa un'occhiata
# e un falso negativo costa un DOI che non si ritratta.
# Due livelli, perche' un cancello che scatta su un quarto dei file insegna a ignorarlo.
#
# BLOCCANTI: frasi che in pratica compaiono solo DENTRO un rapporto di revisione o una
# lettera editoriale. Una sola occorrenza ferma la build.
CONTENT_BLOCK = [
    r"comments? to the author", r"confidential comments?",
    r"confidential to the editor", r"decision letter", r"editor.s decision",
    r"referee report", r"reviewer report", r"reviewer.s comments",
    r"referee.s comments", r"recommendation to the editor",
    r"rapporto del referee", r"commenti riservati",
]
# DA GUARDARE: menzioni. Uno script che spiega a quale rilievo risponde ne contiene una
# o due ed e' legittimo; un file che ne contiene molte probabilmente RIPORTA il rapporto.
# Si segnalano sempre, bloccano solo oltre soglia o con --strict.
CONTENT_WARN = [r"referee", r"reviewer", r"peer[_\- ]?review", r"confidential"]
BLOCK_RE = [re.compile(t, re.I) for t in CONTENT_BLOCK]
WARN_RE = [re.compile(t, re.I) for t in CONTENT_WARN]
WARN_LINE_THRESHOLD = 6

# Gli strumenti che CERCANO questi termini li contengono per forza: la lista bloccante
# vive in questo file, e paper2_scrub_quotes.py spiega nella docstring perche' le
# citazioni vanno parafrasate. Uno scanner che incrimina se stesso produce rumore e
# nasconde il segnale. L'esenzione e' per NOME e per contenuto-di-schemi soltanto: se
# uno di questi file contenesse una vera citazione, la scansione delle citazioni lunghe
# di paper2_scrub_quotes.py la vedrebbe comunque.
SELF_EXEMPT = {"src/paper2_deposit.py", "src/paper2_scrub_quotes.py"}
SCANNABLE_EXT = {".md", ".txt", ".tex", ".py", ".json", ".jsonl", ".csv", ".yml",
                 ".yaml", ".bib", ".cff", ".rst", ".html", ".ps1", ".sh"}
SCAN_MAX_BYTES = 8 << 20

TIERS_V1 = ("records", "features", "fields", "diagrams", "superseded")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


def flagged(rel: str) -> list[str]:
    return [p.pattern for p in CONF_RE if p.search(rel)]


def flagged_content(path: Path) -> dict:
    """Ritorna {'block': [...], 'warn': [...], 'warn_lines': n}."""
    empty = {"block": [], "warn": [], "warn_lines": 0}
    if path.suffix.lower() not in SCANNABLE_EXT:
        return empty
    try:
        if path.stat().st_size > SCAN_MAX_BYTES:
            return empty
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return empty
    block, warn, warn_lines = {}, {}, set()
    for i, line in enumerate(text.splitlines(), 1):
        for rx in BLOCK_RE:
            if rx.search(line) and rx.pattern not in block:
                block[rx.pattern] = {"term": rx.pattern, "line": i,
                                     "context": line.strip()[:120]}
        for rx in WARN_RE:
            if rx.search(line):
                warn_lines.add(i)
                warn.setdefault(rx.pattern, {"term": rx.pattern, "line": i,
                                             "context": line.strip()[:120]})
    return {"block": list(block.values()), "warn": list(warn.values()),
            "warn_lines": len(warn_lines)}


def git_out(base: Path, *args) -> list[str]:
    r = subprocess.run(["git", *args], cwd=str(base), capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"[FATAL] git {' '.join(args)}: {r.stderr[:300]}")
    return [l for l in r.stdout.splitlines() if l.strip()]


# ------------------------------------------------------------------ raccolta dei file

DEFAULT_CODE_ROOTS = ["src"]
DEFAULT_CODE_EXTRAS = [".gitattributes", ".gitignore", "LICENSE", "LICENSE.md",
                       "CITATION.cff", "requirements.txt", "environment.yml"]


def collect_code(base: Path, roots=None, extras=None) -> list[str]:
    """Solo file TRACCIATI da git, sotto le radici indicate: cio' che git non conosce non
    finisce nel deposito per sbaglio, e cio' che non serve a riprodurre non ci entra."""
    roots = [r.rstrip("/") for r in (roots or DEFAULT_CODE_ROOTS)]
    extras = set(extras or DEFAULT_CODE_EXTRAS)
    out = []
    for rel in git_out(base, "ls-files"):
        r = rel.replace("\\", "/")
        if not (base / r).is_file():
            continue
        if r in extras or any(r == x or r.startswith(x + "/") for x in roots):
            out.append(r)
    return sorted(out)


def collect_from_manifest(base: Path, body: Path) -> list[str]:
    rels = {}
    with open(body, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            rels[o["rel"]] = o["sha256"]          # last-wins, come il lettore del freeze
    return sorted(rels)


# ------------------------------------------------------------------------- cancelli

def gate_integrity(base: Path, quiet=False):
    """Cancello 1. Importa il verificatore invece di riprodurne la logica."""
    sys.path.insert(0, str(base / "src"))
    try:
        import paper2_freeze_verify as V
    except Exception as exc:
        return False, [f"impossibile importare paper2_freeze_verify: {exc}"]
    problems = []
    for mdir, tiers in ((base / "results" / "paper2", list(TIERS_V1)),
                        (base / "manifests", None)):
        if not mdir.is_dir():
            problems.append(f"{mdir} assente")
            continue
        rep = V.verify(base=base, manifest_dir=mdir, only_tiers=tiers, jobs=4)
        if rep.get("status") != "CLEAN":
            bad = [c["check"] for c in rep.get("checks", []) if not c["ok"]]
            problems.append(f"{mdir.name}: {rep.get('status')} — {bad}")
        elif not quiet:
            print(f"    {mdir}: CLEAN ({', '.join(rep['tiers'])})")
    return not problems, problems


def load_ack(path: Path) -> dict:
    """
    Riconoscimenti espliciti. I file dentro un tier congelato non si possono modificare
    senza rompere l'aggregate: l'unica via onesta e' dichiarare, per percorso e con una
    motivazione, che sono stati esaminati. Il riconoscimento e' un file versionato, non
    un flag da riga di comando: resta agli atti e finisce nel log del deposito.
    Formato: una riga per file, `percorso<TAB>motivazione`. '#' commenta.
    """
    ack = {}
    if not path or not Path(path).is_file():
        return ack
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\t+| {2,}", line, maxsplit=1)
        if len(parts) != 2 or not parts[1].strip():
            raise SystemExit(f"[FATAL] riga senza motivazione in {path}: {line[:80]}")
        ack[parts[0].strip().replace("\\", "/")] = parts[1].strip()
    return ack


def gate_confidential(items, base: Path = None, strict: bool = False,
                      ack: dict = None) -> tuple[list, list, list]:
    """Cancello 2. Ritorna (bloccanti, da_guardare, riconosciuti)."""
    ack = ack or {}
    blocking, watch, acked = [], [], []
    for z, r in items:
        if r in SELF_EXEMPT:
            continue
        by_name = flagged(r)
        c = flagged_content(base / r) if base else {"block": [], "warn": [], "warn_lines": 0}
        dense = c["warn_lines"] >= WARN_LINE_THRESHOLD
        rec = {"zip": z, "path": r, "patterns": by_name, "block": c["block"],
               "warn": c["warn"], "warn_lines": c["warn_lines"]}
        flagged_any = by_name or c["block"] or dense or (strict and c["warn"])
        if flagged_any and r in ack:
            rec["ack"] = ack[r]
            acked.append(rec)
        elif flagged_any:
            blocking.append(rec)
        elif c["warn"]:
            watch.append(rec)
    return blocking, watch, acked


def gate_clean_tree(base: Path):
    dirty = git_out(base, "status", "--porcelain")
    head = git_out(base, "rev-parse", "HEAD")[0]
    return (not dirty), dirty, head


# ---------------------------------------------------------------------------- build

def write_zip(base: Path, dest: Path, rels, arc_prefix: str = "") -> tuple[str, int]:
    """Zip deterministica: nomi ordinati, timestamp e permessi fissi."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in sorted(rels):
            src = base / rel
            info = zipfile.ZipInfo(arc_prefix + rel, date_time=FIXED_DATE)
            info.external_attr = FIXED_MODE
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(src, "rb") as fh, z.open(info, "w") as out:
                shutil.copyfileobj(fh, out, CHUNK)
    os.replace(tmp, dest)
    return sha256_file(dest)


def build(base: Path, out: Path, allow_dirty: bool, code_roots=None, code_extras=None,
          strict: bool = False, ack_file=None, quiet=False) -> dict:
    rep = {"utc": utcnow(), "base": str(base), "out": str(out)}

    print("=== CANCELLO 1: integrità ===")
    ok, problems = gate_integrity(base, quiet)
    rep["integrity"] = {"ok": ok, "problems": problems}
    if not ok:
        for p in problems:
            print(f"    FAIL {p}")
        raise SystemExit("[FATAL] i tier non verificano CLEAN. Nessun file scritto.")

    print("\n=== CANCELLO 3: albero pulito ===")
    clean, dirty, head = gate_clean_tree(base)
    rep["git"] = {"clean": clean, "head": head, "dirty": dirty}
    print(f"    HEAD {head[:8]}   percorsi non committati: {len(dirty)}")
    if not clean and not allow_dirty:
        for d in dirty[:10]:
            print(f"      {d}")
        raise SystemExit("[FATAL] albero sporco: il codice depositato non sarebbe "
                         "identificabile da un commit. Nessun file scritto.")

    # --- composizione
    mdir_v1 = base / "results" / "paper2"
    mdir_p2 = base / "manifests"
    # Il pacchetto di codice contiene cio' che RIPRODUCE i risultati, non il diario di
    # lavoro: canovacci, checklist, consegne e prior del framework abbandonato non
    # servono a nessuno che voglia rifare i conti, e sono superficie di rischio gratuita.
    code = collect_code(base, roots=code_roots, extras=code_extras)
    manifests = sorted(
        [str(p.relative_to(base)).replace("\\", "/")
         for t in TIERS_V1
         for p in (mdir_v1 / f"ensemble_v1_freeze_{t}.json",
                   mdir_v1 / f"ensemble_v1_manifest_{t}.jsonl") if p.is_file()]
        + [str(p.relative_to(base)).replace("\\", "/")
           for p in mdir_p2.glob("ensemble_v1_*") if p.is_file()]
        + ["src/paper2_v1_reference.json", "src/paper2_v1_amendments.jsonl"])
    records = collect_from_manifest(base, mdir_v1 / "ensemble_v1_manifest_records.jsonl")
    products = collect_from_manifest(base, mdir_p2 / "ensemble_v1_manifest_paper2_products.jsonl")

    plan = {"cauchy_code.zip": code,
            "cauchy_manifests_v1.zip": manifests,
            "cauchy_records_v1.zip": records,
            "cauchy_paper2_products.zip": products}

    print("\n=== CANCELLO 2: riservatezza ===")
    items = [(z, r) for z, rs in plan.items() for r in rs]
    ack = load_ack(ack_file)
    blocking, watch, acked = gate_confidential(items, base, strict, ack)
    rep["confidential"] = {"blocking": blocking, "watch": watch, "acknowledged": acked}
    if acked:
        print(f"    riconosciuti ({len(acked)}): esaminati e dichiarati in {ack_file}")
        for h in acked[:6]:
            print(f"      {h['path']}  — {h['ack'][:70]}")
        if len(acked) > 6:
            print(f"      ... e altri {len(acked)-6}")
    n = len(items)
    if watch:
        print(f"    da guardare ({len(watch)} su {n}): menzioni isolate, non bloccanti")
        for h in watch[:10]:
            w = h["warn"][0]
            print(f"      {h['path']}  ({h['warn_lines']} righe)  riga {w['line']}: "
                  f"{w['context'][:80]}")
        if len(watch) > 10:
            print(f"      ... e altri {len(watch)-10}")
    if blocking:
        print(f"\n    BLOCCANTI ({len(blocking)}):")
        for h in blocking[:40]:
            why = (h["patterns"] or [c["term"] for c in h["block"]]
                   or [f"{h['warn_lines']} righe con menzioni"])
            print(f"      {h['path']}   -> {why}")
            for c in (h["block"] or h["warn"])[:2]:
                print(f"          riga {c['line']}: {c['context']}")
        raise SystemExit(
            f"[FATAL] {len(blocking)} file assomigliano a materiale di revisione.\n"
            "  Un archivio con DOI non si ritratta. Toglierli dal pacchetto, oppure\n"
            "  verificarli e restringere le radici del codice. Nessun file scritto.")
    print(f"    nessun bloccante su {n} file")

    # --- scrittura
    print(f"\n=== COSTRUZIONE === {out}")
    out.mkdir(parents=True, exist_ok=True)
    rep["zips"] = {}
    for name, rels in plan.items():
        missing = [r for r in rels if not (base / r).is_file()]
        if missing:
            raise SystemExit(f"[FATAL] {name}: {len(missing)} file assenti, es. {missing[:3]}")
        sha, size = write_zip(base, out / name, rels)
        rep["zips"][name] = {"files": len(rels), "bytes": size, "sha256": sha}
        print(f"    {name:<32} {len(rels):>6} file  {size:>12,} B  {sha[:16]}…")

    return rep


def write_manifest_sha256(out: Path, extra: list[Path] = ()) -> Path:
    """Formato coreutils: due spazi fra digest e nome, verificabile con `sha256sum -c`."""
    names = sorted([p for p in out.iterdir()
                    if p.is_file() and p.name != "MANIFEST.sha256"] + list(extra),
                   key=lambda p: p.name)
    lines = []
    for p in names:
        sha, _ = sha256_file(p)
        lines.append(f"{sha}  {p.name}")
    dest = out / "MANIFEST.sha256"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return dest


# -------------------------------------------------------------------------- comandi

def cmd_check(args) -> int:
    base = Path(args.base).resolve()
    print("=== CANCELLO 1: integrità ===")
    ok, problems = gate_integrity(base)
    for p in problems:
        print(f"    FAIL {p}")
    clean, dirty, head = gate_clean_tree(base)
    print(f"\n=== CANCELLO 3: albero pulito ===\n    HEAD {head[:8]}   "
          f"non committati: {len(dirty)}")
    for d in dirty[:10]:
        print(f"      {d}")
    code = collect_code(base, roots=args.code_roots, extras=None)
    mv1 = base / "results" / "paper2"
    mp2 = base / "manifests"
    recs = collect_from_manifest(base, mv1 / "ensemble_v1_manifest_records.jsonl")
    prods = collect_from_manifest(base, mp2 / "ensemble_v1_manifest_paper2_products.jsonl")
    allitems = ([("code", r) for r in code] + [("records", r) for r in recs]
                + [("products", r) for r in prods])
    ack = load_ack(args.ack_file)
    blocking, watch, acked = gate_confidential(allitems, base, args.strict, ack)
    print(f"\n=== CANCELLO 2: riservatezza ===\n    {len(blocking)} bloccanti, "
          f"{len(acked)} riconosciuti, {len(watch)} da guardare, su {len(allitems)} file")
    for h in blocking[:40]:
        why = (h["patterns"] or [c["term"] for c in h["block"]]
               or [f"{h['warn_lines']} righe con menzioni"])
        print(f"      BLOCCA {h['path']}  -> {why}")
        for c in (h["block"] or h["warn"])[:2]:
            print(f"          riga {c['line']}: {c['context']}")
    for h in watch[:15]:
        w = h["warn"][0]
        print(f"      guarda {h['path']}  ({h['warn_lines']} righe)  "
              f"riga {w['line']}: {w['context'][:70]}")
    print(f"\ncomposizione prevista: code={len(code)}  records={len(recs)}  "
          f"products={len(prods)}")
    good = ok and clean and not blocking
    print(f"\npronto per build: {'SI' if good else 'NO'}")
    return 0 if good else 1


def cmd_build(args) -> int:
    base = Path(args.base).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = base / out
    rep = build(base, out, args.allow_dirty, code_roots=args.code_roots,
                strict=args.strict, ack_file=args.ack_file)
    man = write_manifest_sha256(out)
    print(f"\n    MANIFEST.sha256 su {len(man.read_text().splitlines())} file")
    log = base / "logs" / "deposit.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rep, ensure_ascii=False, default=str) + "\n")
    print(f"\nManca il README.md: scriverlo in {out} e RIGENERARE il MANIFEST con\n"
          f"  python src\\paper2_deposit.py manifest --out {args.out}")
    return 0


def cmd_manifest(args) -> int:
    base = Path(args.base).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = base / out
    man = write_manifest_sha256(out)
    print(man.read_text())
    return 0


# ------------------------------------------------------------------------- selftest

def cmd_selftest(args) -> int:
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")
        ok = ok and bool(cond)

    tmp = Path(tempfile.mkdtemp(prefix="dep_"))
    try:
        base = tmp / "repo"
        (base / "src").mkdir(parents=True)
        for i in range(3):
            (base / "src" / f"m{i}.py").write_text(f"# {i}\n")
        z = base / "a.zip"

        rels = [f"src/m{i}.py" for i in range(3)]
        s1, n1 = write_zip(base, z, rels)
        import time
        time.sleep(1.1)
        s2, n2 = write_zip(base, z, rels)
        expect("1. zip riproducibile: stesso sha a distanza di tempo", s1 == s2,
               f"({s1[:12]}…)")

        s3, _ = write_zip(base, z, list(reversed(rels)))
        expect("2. ordine dei nomi irrilevante", s3 == s1)

        (base / "src" / "m1.py").write_text("# cambiato\n")
        s4, _ = write_zip(base, z, rels)
        expect("3. un byte diverso cambia lo sha", s4 != s1)

        # riservatezza
        cases = {
            "docs/Referee_Report_1.pdf": True,
            "docs/MN-26-2100-P_R1_Proof_hi.pdf": True,
            "src/response_letter.md": True,
            "papers/Abedi2025_Revisione_Scientifica.md": True,
            "src/paper2_gate21.py": False,
            "results/paper2/compD_NGC.jsonl": False,
            "src/paper1_remap.py": False,
        }
        wrong = {p: bool(flagged(p)) for p, exp in cases.items() if bool(flagged(p)) != exp}
        expect("4. schemi sui NOMI: nessun falso positivo né negativo",
               not wrong, f"({wrong})" if wrong else "")

        # 4b. il caso che il filtro sui nomi mancava: contenuto riservato, nome innocuo
        (base / "CAUCHY_Review_and_GATE.md").write_text(
            "# Note\nIl Referee 2 osserva che la stima e' instabile.\n", encoding="utf-8")
        (base / "innocuo.md").write_text(
            "# Note\nnessun contenuto sensibile qui.\n", encoding="utf-8")
        (base / "rapporto.md").write_text(
            "# Note\nReviewer's comments to the Author:\n1. La stima e' instabile.\n",
            encoding="utf-8")
        (base / "menzione.md").write_text(
            "# Nota\nQuesto script risponde al rilievo del Referee 3.\n", encoding="utf-8")
        (base / "denso.md").write_text(
            "# Trascrizione\n" + "".join(f"Referee {i}: osservazione {i}.\n"
                                         for i in range(9)), encoding="utf-8")
        b1, w1, _ = gate_confidential([("z", "rapporto.md")], base)
        b2, w2, _ = gate_confidential([("z", "menzione.md")], base)
        b3, w3, _ = gate_confidential([("z", "denso.md")], base)
        b4, w4, _ = gate_confidential([("z", "innocuo.md")], base)
        b5, w5, _ = gate_confidential([("z", "src/m0.py")], base)
        expect("4b. frase da rapporto di revisione -> BLOCCA", len(b1) == 1,
               f"({b1[0]['block'][0]['term'] if b1 and b1[0]['block'] else ''})")
        expect("4c. menzione isolata in una docstring -> da guardare, NON blocca",
               not b2 and len(w2) == 1, f"({w2[0]['warn_lines'] if w2 else 0} righe)")
        expect("4d. molte menzioni (trascrizione) -> BLOCCA per densita'",
               len(b3) == 1 and b3[0]["warn_lines"] >= WARN_LINE_THRESHOLD,
               f"({b3[0]['warn_lines'] if b3 else 0} righe)")
        expect("4e. testo pulito e codice del progetto -> nessun allarme",
               not b4 and not w4 and not b5 and not w5)
        bs, ws, _ = gate_confidential([("z", "menzione.md")], base, strict=True)
        expect("4f. --strict promuove la menzione isolata a bloccante",
               len(bs) == 1 and not ws)

        # 4g. riconoscimento esplicito: sposta da bloccante a riconosciuto, non silenzia
        ackf = base / "ack.tsv"
        ackf.write_text("denso.md\tciclo di review interno, non revisione esterna\n",
                        encoding="utf-8")
        a = load_ack(ackf)
        bb, ww, aa = gate_confidential([("z", "denso.md")], base, ack=a)
        expect("4g. file riconosciuto -> non blocca, ma resta registrato",
               not bb and len(aa) == 1 and aa[0]["ack"].startswith("ciclo"))
        ackf.write_text("denso.md\n", encoding="utf-8")
        try:
            load_ack(ackf); caught = False
        except SystemExit:
            caught = True
        expect("4h. riconoscimento senza motivazione -> rifiutato", caught)

        # 4i. gli scanner non incriminano se stessi, ma nulla d'altro e' esente
        (base / "src").mkdir(exist_ok=True)
        for name in ("paper2_deposit.py", "paper2_scrub_quotes.py", "altro.py"):
            (base / "src" / name).write_text(
                "# referee reviewer peer review\n" * 9, encoding="utf-8")
        bx, wx, _ = gate_confidential(
            [("z", f"src/{n}") for n in ("paper2_deposit.py",
                                         "paper2_scrub_quotes.py", "altro.py")], base)
        expect("4i. i due scanner sono esenti, un terzo file no",
               [h["path"] for h in bx] == ["src/altro.py"],
               f"({[h['path'] for h in bx]})")

        # MANIFEST.sha256 leggibile da sha256sum -c
        out = tmp / "dep"
        out.mkdir()
        (out / "x.zip").write_bytes(b"abc")
        (out / "y.zip").write_bytes(b"def")
        man = write_manifest_sha256(out)
        txt = man.read_text()
        good = all(re.fullmatch(r"[0-9a-f]{64}  \S+", l) for l in txt.splitlines())
        expect("5. MANIFEST.sha256 in formato coreutils", good)
        expect("5b. il MANIFEST non elenca se stesso", "MANIFEST.sha256" not in txt)
        expect("5c. digest corretto",
               hashlib.sha256(b"abc").hexdigest() in txt
               and hashlib.sha256(b"def").hexdigest() in txt)

        # last-wins sul corpo
        body = tmp / "b.jsonl"
        body.write_text('{"rel":"a","sha256":"0"}\n{"rel":"b","sha256":"1"}\n'
                        '{"rel":"a","sha256":"2"}\n', encoding="utf-8")
        expect("6. corpo accodato: percorsi distinti, non righe",
               collect_from_manifest(tmp, body) == ["a", "b"])

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("selftest"); p.set_defaults(func=cmd_selftest)
    for name, fn in (("check", cmd_check), ("build", cmd_build),
                     ("manifest", cmd_manifest)):
        p = sub.add_parser(name)
        p.add_argument("--base", default=".")
        p.add_argument("--code-roots", nargs="+", default=None, dest="code_roots",
                       help=f"radici del pacchetto di codice; default {DEFAULT_CODE_ROOTS}")
        p.add_argument("--ack-file", default="deposit_acknowledged.tsv",
                       dest="ack_file",
                       help="file versionato: percorso<TAB>motivazione, per i file "
                            "esaminati che non si possono modificare (tier congelati)")
        p.add_argument("--strict", action="store_true",
                       help="tratta come bloccante anche una singola menzione")
        if name != "check":
            p.add_argument("--out", default="deposit")
        if name == "build":
            p.add_argument("--allow-dirty", action="store_true")
        p.set_defaults(func=fn)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

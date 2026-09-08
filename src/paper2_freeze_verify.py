#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_freeze_verify.py — rev. 2 — verifica del congelamento ensemble v1.

Schema reale del freeze (scoperto il 28 ago 2026)
-------------------------------------------------
Ogni tier ha DUE file in results/paper2:
  ensemble_v1_freeze_{tier}.json    intestazione: schema "cauchy.paper2.v1_manifest",
                                    aggregate_sha256, n_files, total_bytes, base, roots,
                                    include_ext, exclude_pat, reference_sha256, git
  ensemble_v1_manifest_{tier}.jsonl corpo: una voce per file
La rev. 1 leggeva solo i .json e concludeva che il corpo non esistesse. Sbagliato.

Quattro direzioni indipendenti
------------------------------
  A. intestazione vs corpo   n_files e total_bytes contro le righe effettive del JSONL
  B. corpo vs disco          sha256 ricalcolato per ogni voce
  C. disco vs corpo          le REGOLE del tier (roots + include_ext + exclude_pat) sono
                             rigiocate sul disco: ogni file che le soddisfa e non e' nel
                             corpo e' un EXTRA. E' la direzione che intercetta un manifest
                             troncato, e quella che un verify per riga non ha.
  D. aggregate               ricostruito con ~20 costruzioni candidate (due ordinamenti, con e
                             senza il campo bytes, piu' il digest del corpo stesso); se una
                             riproduce l'aggregate dichiarato, il digest diventa
                             ricalcolabile senza lo strumento originale.
Piu' tre trasversali: reference_sha256 dei manifest contro il reference vivo;
sovrapposizioni fra tier; file congelati che vivono dentro results/paper2, cioe' un tier
che contiene i propri manifest.

Sola lettura sui tier. L'unica scrittura e' il JSONL di esito, che lo script rifiuta di
mettere dentro results/.

  python src\\paper2_freeze_verify.py selftest
  python src\\paper2_freeze_verify.py inspect
  python src\\paper2_freeze_verify.py verify --tier records features --out logs\\fv.jsonl
  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl

Uscita: 0 CLEAN, 1 discrepanze, 2 errore d'uso o schema non riconosciuto.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "cauchy.paper2.v1_manifest"
TIERS = ("records", "features", "fields", "diagrams", "superseded")

# Valori dei documenti: servono a misurare la deriva documento <-> disco, non come verita'.
DOCUMENTED = {   # paper2_item01_closed.md, 25 ago 2026
    "records":    {"files": 225,   "aggregate_sha256": "e905d7fd085b23e9a7e534e2583a4940a40904d1a6cf3bdc3a0e9011ffe882ce"},
    "features":   {"files": 12189, "aggregate_sha256": "b0601f36c89430b3133b46e6107a0c13f50f55a8626fefcc808a6ec3d8d21fcc"},
    "fields":     {"files": 2202,  "aggregate_sha256": "bf176f95a3b9e31d0c78590a2d7eef1fdc6ecd2bbf5efc4388358ca5724a2c34"},
    "diagrams":   {"files": 16221, "aggregate_sha256": "3a746c95e009b89a3a66408880b3085abe41e5f1e5c9ac12ee05009ae08f4929"},
    "superseded": {"files": 4000,  "aggregate_sha256": "f2cf37627a44e4475a8a19b19d7631b0a094098e509220f1f5a0267bffb33764"},
}
DOCUMENTED_TOTAL_FILES = 34836          # consegna 27 ago, prereg §2.1
DOCUMENTED_TOTAL_GIB = 26.771
GIB = 1024 ** 3
DOCUMENTED_TOTAL_BYTES = DOCUMENTED_TOTAL_GIB * GIB
DOCUMENTED_TOTAL_TOL = 0.0005 * GIB

# Emendamenti: DUE conteggi, e non sono la stessa grandezza.
#  - PREREG_AMENDMENTS_AT_DEPOSIT e' quanti record esistevano al deposito della
#    pre-registrazione (v1.1, §9, version DOI 10.5281/zenodo.22148444). Quel
#    documento non si muove, quindi questa costante non si tocca mai: e' un
#    limite INFERIORE, perche' il file e' append-only e un record non puo'
#    sparire. La v1.0 diceva dieci; era il conteggio alla stesura e non al
#    deposito, ed e' rettificato dentro il §9 stesso.
#  - DOCUMENTED_AMENDMENTS e' quanti ne dichiara la documentazione corrente
#    (consegna e checklist). Va incrementata a ogni append, nello stesso commit
#    che appende: se cambia il file e non la costante, il verificatore lo dice.
# Il numero di un emendamento e' la sua POSIZIONE a base 1: nel record non
# esiste nessun campo che lo dichiari, e il §9 vi rimanda per posizione.
PREREG_AMENDMENTS_AT_DEPOSIT = 12
DOCUMENTED_AMENDMENTS = 55

# Due grandezze, non due versioni. Vedi il blocco reference in verify().
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"
REFERENCE_FILE_SHA = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"

HEX64 = frozenset("0123456789abcdef")
CHUNK = 1 << 20


# ----------------------------------------------------------------------------- utilita'

def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_sha256(s) -> bool:
    return isinstance(s, str) and len(s) == 64 and set(s.lower()) <= HEX64


def norm(p) -> str:
    s = str(p).replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s


def rel_to(path_posix: str, base_posix: str) -> str:
    """Relativo a base se ne e' dentro. Confronto case-insensitive: siamo su NTFS."""
    p, b = norm(path_posix), norm(base_posix).rstrip("/")
    if b and p.lower().startswith(b.lower() + "/"):
        return p[len(b) + 1:]
    return p.lstrip("/")


def sha256_file(path: Path, chunk: int = CHUNK):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fmt_bytes(n) -> str:
    return f"{n:,.0f} B = {n/1e9:.3f} GB = {n/GIB:.5f} GiB"


def atomic_append_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True, default=str) + "\n"
                      for r in records)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())


# ------------------------------------------------------------------- lettura dei manifest

PATH_KEYS = ("rel", "path", "relpath", "rel_path", "file", "filename", "name", "p")
SHA_KEYS = ("sha256", "sha", "hash", "digest", "checksum", "sha256sum")
SIZE_KEYS = ("size", "bytes", "size_bytes", "nbytes", "length")


def entry_from_obj(o):
    if isinstance(o, dict):
        sha = next((o[k] for k in SHA_KEYS if is_sha256(o.get(k))), None)
        p = next((o[k] for k in PATH_KEYS if isinstance(o.get(k), str)), None)
        if sha is None or p is None:
            if len(o) == 1:
                (k, v), = o.items()
                if is_sha256(v):
                    return {"path": norm(k), "raw": k, "sha256": v.lower(), "size": None}
            return None
        size = next((o[k] for k in SIZE_KEYS if isinstance(o.get(k), int)), None)
        return {"path": norm(p), "raw": p, "sha256": sha.lower(), "size": size}
    if isinstance(o, list) and len(o) >= 2:
        p = next((x for x in o if isinstance(x, str) and not is_sha256(x)), None)
        sha = next((x for x in o if is_sha256(x)), None)
        size = next((x for x in o if isinstance(x, int)), None)
        if p and sha:
            return {"path": norm(p), "raw": p, "sha256": sha.lower(), "size": size}
    return None


def load_body(path: Path):
    """
    Ritorna (entries, bad, n_superate). Il JSONL e' append-only e piu' righe possono
    riferirsi allo stesso percorso: paper2_freeze_v1.py:394 legge last-wins, e
    aggregate_digest lavora su un dizionario, quindi sull'insieme deduplicato. Contare le
    righe invece di deduplicare darebbe n_files sbagliato e aggregate irriproducibile
    appena un manifest venisse accodato.
    """
    entries, bad = [], []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception as exc:
                bad.append({"line": i, "error": str(exc)[:120]})
                continue
            e = entry_from_obj(o)
            if e is None:
                bad.append({"line": i, "error": "nessun (percorso, sha256) riconoscibile",
                            "keys": sorted(o.keys())[:12] if isinstance(o, dict) else None})
            else:
                e["_line"] = i
                entries.append(e)
    by_path = {}
    for e in entries:
        by_path[e["path"]] = e          # last-wins
    n_superseded = len(entries) - len(by_path)
    return list(by_path.values()), bad, n_superseded


def discover(manifest_dir: Path):
    heads, ignored = {}, []
    for f in sorted(manifest_dir.glob("*.json")):
        raw = f.read_bytes()
        try:
            o = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            ignored.append({"file": f.name, "why": f"JSON illeggibile: {exc}"[:100]})
            continue
        if not (isinstance(o, dict) and o.get("schema") == SCHEMA):
            ignored.append({"file": f.name, "why": "schema diverso da quello del freeze"})
            continue
        o["_header_file"] = str(f)
        o["_header_sha256"] = sha256_bytes(raw)
        heads[o.get("tier") or f.stem] = o

    # I corpi si accoppiano al tier DICHIARATO dalle intestazioni trovate, non a una
    # lista fissa di nomi: altrimenti un tier nuovo (paper2_products, v1_manifests)
    # risulterebbe senza corpo e la verifica lo direbbe assente invece di verificarlo.
    bodies = {}
    for tier in heads:
        exact = manifest_dir / f"ensemble_v1_manifest_{tier}.jsonl"
        if exact.is_file():
            bodies[tier] = [exact]
            continue
        hits = [f for f in sorted(manifest_dir.glob("*.jsonl"))
                if tier.lower() in f.name.lower()]
        if hits:
            bodies[tier] = hits
    return heads, bodies, ignored


# ------------------------------------------------------- rigiocare le regole di un tier

def walk_rules(base: Path, roots, include_ext, exclude_pat, exclude_on: str,
               exclude_dirs=None):
    """
    exclude_on='base': il pattern e' cercato nel percorso relativo a base;
    'root': nel percorso relativo alla radice del tier. La regola vera non e' documentata:
    si provano entrambe e si tiene quella che riproduce n_files.
    """
    exts = {e.lower() for e in include_ext}
    # paper2_freeze_v1.py esclude sempre la propria directory di output
    # (iter_files(..., exclude_dirs=[out]), docstring righe 185-188). Se l'intestazione lo
    # dichiara lo rigiochiamo; se non lo dichiara, il replay non puo' tornare.
    exd = []
    for d in (exclude_dirs or []):
        dp = Path(norm(d))
        exd.append((dp if dp.is_absolute() else base / dp).resolve())

    def in_excluded(fp: Path) -> bool:
        try:
            rp = fp.resolve()
        except OSError:
            return False
        return any(rp == d or d in rp.parents for d in exd)

    out = {}
    for r in roots:
        rp = Path(norm(r))
        if not rp.is_absolute():
            rp = base / rp
        if not rp.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                fp = Path(dirpath) / fn
                if fp.suffix.lower() not in exts:
                    continue
                if exd and in_excluded(fp):
                    continue
                rel_b = rel_to(fp.as_posix(), base.as_posix())
                rel_r = rel_to(fp.as_posix(), rp.as_posix())
                target = rel_b if exclude_on == "base" else rel_r
                if any(pat in target for pat in exclude_pat):
                    continue
                out[rel_b] = fp
    return out


# ---------------------------------------------------------------------------- aggregate

def aggregate_candidates(entries, body_path: Path | None = None):
    """
    La regola dell'aggregate non e' documentata. Si provano le costruzioni plausibili in
    due ordinamenti (per percorso e nell'ordine in cui il corpo e' stato scritto), con e
    senza il campo bytes, piu' il digest del corpo stesso.
    """
    orders = {"pathsorted": sorted(entries, key=lambda e: e["path"]),
              "fileorder": list(entries)}
    c = {}
    for tag, seq in orders.items():
        hx = [e["sha256"] for e in seq]
        c[f"concat_hex_{tag}"] = sha256_bytes("".join(hx).encode())
        c[f"concat_raw_{tag}"] = sha256_bytes(b"".join(bytes.fromhex(s) for s in hx))
        c[f"lines_sha_2sp_path_{tag}"] = sha256_bytes(
            "".join(f"{e['sha256']}  {e['path']}\n" for e in seq).encode())
        c[f"lines_sha_1sp_path_{tag}"] = sha256_bytes(
            "".join(f"{e['sha256']} {e['path']}\n" for e in seq).encode())
        c[f"lines_path_tab_sha_{tag}"] = sha256_bytes(
            "".join(f"{e['path']}\t{e['sha256']}\n" for e in seq).encode())
        c[f"lines_path_sha_pipe_{tag}"] = sha256_bytes(
            "".join(f"{e['path']}|{e['sha256']}\n" for e in seq).encode())
        if all(isinstance(e["size"], int) for e in seq):
            c[f"lines_path_sha_size_{tag}"] = sha256_bytes(
                "".join(f"{e['path']}|{e['sha256']}|{e['size']}\n" for e in seq).encode())
            c[f"json_rel_sha_bytes_{tag}"] = sha256_bytes("".join(
                json.dumps({"rel": e["path"], "sha256": e["sha256"], "bytes": e["size"]},
                           sort_keys=True, separators=(",", ":")) + "\n"
                for e in seq).encode())
        c[f"update_hex_{tag}"] = _incremental(hx)
    # Regola vera, da paper2_freeze_v1.py:235-238 (aggregate_digest):
    #   sha256 di "\n".join(sorted(f"{rel}:{sha256}")) — niente newline finale,
    #   ordinamento sulla stringa composta, indipendente dall'ordine di scansione.
    for tag, key in (("rel_norm", "path"), ("rel_grezzo", "raw")):
        vals = [f"{e.get(key, e['path'])}:{e['sha256']}" for e in entries]
        c[f"REGOLA_freeze_v1[{tag}]"] = sha256_bytes("\n".join(sorted(vals)).encode())
    hs = sorted(e["sha256"] for e in entries)
    c["concat_hex_shasorted"] = sha256_bytes("".join(hs).encode())
    c["concat_raw_shasorted"] = sha256_bytes(b"".join(bytes.fromhex(s) for s in hs))
    c["json_compact_map_pathsorted"] = sha256_bytes(
        json.dumps({e["path"]: e["sha256"] for e in orders["pathsorted"]},
                   sort_keys=True, separators=(",", ":")).encode())
    if body_path is not None and body_path.is_file():
        c["_sha256_del_corpo_jsonl"] = sha256_bytes(body_path.read_bytes())
    return c


def _incremental(hexes):
    h = hashlib.sha256()
    for s_ in hexes:
        h.update(s_.encode())
    return h.hexdigest()


def load_amendments(base: Path):
    """
    Item 0.12: gli emendamenti vivono in un file sorella append-only e chi legge li
    SOVRAPPONE al valore congelato. Qui si applica la stessa regola ai valori documentati
    dei tier: senza questa sovrapposizione un emendamento gia' registrato verrebbe
    riportato come deriva, che e' il contrario di cio' che il file serve a fare.
    """
    am = base / "src" / "paper2_v1_amendments.jsonl"
    recs = []
    if not am.is_file():
        return recs, {}
    for line in am.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            pass
    overlay = {}
    for r in recs:
        jp = str(r.get("json_path", ""))
        for t in TIERS:
            if jp == f"ensemble_v1_freeze_{t}" or jp.endswith(f"freeze_{t}"):
                nv = r.get("new_value") or {}
                if isinstance(nv, dict):
                    d = overlay.setdefault(t, {})
                    if "n_files" in nv:
                        d["files"] = nv["n_files"]
                    if "aggregate_sha256" in nv:
                        d["aggregate_sha256"] = nv["aggregate_sha256"]
                    d["_amended_by"] = r.get("date") or r.get("utc") or r.get("item")
    return recs, overlay


def apply_overlay(documented: dict, overlay: dict) -> dict:
    out = {t: dict(v) for t, v in documented.items()}
    for t, patch in overlay.items():
        out.setdefault(t, {}).update({k: v for k, v in patch.items()
                                      if not k.startswith("_")})
    return out


# ------------------------------------------------------------------------------- verify

def verify(base: Path, manifest_dir: Path, only_tiers=None, jobs: int = 1,
           documented=None):
    documented = DOCUMENTED if documented is None else documented
    amend_recs, overlay = load_amendments(base)
    documented = apply_overlay(documented, overlay)
    heads, bodies, ignored = discover(manifest_dir)
    if only_tiers:
        heads = {t: h for t, h in heads.items() if t in only_tiers}
    if not heads:
        return {"status": "SCHEMA_ERROR",
                "error": f"nessuna intestazione con schema {SCHEMA} in {manifest_dir}",
                "ignored": ignored}

    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    per_tier, tier_paths, agg_report, rules_report = {}, {}, {}, {}
    all_failures = []

    for tier, hdr in sorted(heads.items()):
        hbase = Path(norm(hdr.get("base") or base.as_posix()))
        roots = hdr.get("roots", [])
        inc = hdr.get("include_ext", [])
        exc = hdr.get("exclude_pat", [])
        n_dec = hdr.get("n_files")
        b_dec = hdr.get("total_bytes")
        agg_dec = hdr.get("aggregate_sha256")

        cands = bodies.get(tier, [])
        if not cands:
            add(f"tier[{tier}].corpo", False,
                f"nessun *.jsonl per il tier: l'elenco per file non e' leggibile")
            per_tier[tier] = {"files": 0, "OK": 0, "MISMATCH": 0, "MISSING": 0,
                              "UNREADABLE": 0, "bytes": 0, "body": None}
            continue
        body_file = cands[0]
        entries, bad, n_sup = load_body(body_file)
        add(f"tier[{tier}].corpo", bool(entries) and not bad,
            f"{body_file.name}: {len(entries)} voci"
            + (f", {n_sup} righe superate collassate (last-wins)" if n_sup else "")
            + (f", {len(bad)} righe non interpretate {bad[:2]}" if bad else ""))
        if len(cands) > 1:
            add(f"tier[{tier}].corpo_unico", False,
                f"piu' candidati: {[c.name for c in cands]}")

        for e in entries:
            e["rel"] = rel_to(e["path"], hbase.as_posix())
        tier_paths[tier] = {e["rel"] for e in entries}

        # A
        add(f"tier[{tier}].A_intestazione_vs_corpo_n", n_dec == len(entries),
            f"n_files={n_dec} percorsi distinti={len(entries)} "
            f"delta={len(entries)-(n_dec or 0):+d}"
            + (f" (su {len(entries)+n_sup} righe)" if n_sup else ""))
        if entries and all(isinstance(e["size"], int) for e in entries) and b_dec is not None:
            bb = sum(e["size"] for e in entries)
            add(f"tier[{tier}].A_intestazione_vs_corpo_byte", bb == b_dec,
                f"total_bytes={b_dec:,} somma_corpo={bb:,} delta={bb-b_dec:+,}")

        # B
        def check(e):
            fp = hbase / e["rel"]
            if not fp.is_file():
                return {"path": e["rel"], "tier": tier, "verdict": "MISSING", "size": 0}
            try:
                sha, size = sha256_file(fp)
            except OSError as exc:
                return {"path": e["rel"], "tier": tier, "verdict": "UNREADABLE",
                        "error": str(exc)[:120], "size": 0}
            v = "OK" if sha == e["sha256"] else "MISMATCH"
            rec = {"path": e["rel"], "tier": tier, "verdict": v, "size": size}
            if v == "MISMATCH":
                rec["expected"], rec["actual"] = e["sha256"], sha
            elif isinstance(e["size"], int) and e["size"] != size:
                rec["verdict"] = "MISMATCH"
                rec["size_expected"] = e["size"]
            return rec

        t0 = time.time()
        if jobs > 1:
            with ThreadPoolExecutor(max_workers=jobs) as ex:
                res = list(ex.map(check, entries))
        else:
            res = [check(e) for e in entries]
        el = time.time() - t0

        d = Counter(r["verdict"] for r in res)
        per_tier[tier] = {"files": len(res), "OK": d["OK"], "MISMATCH": d["MISMATCH"],
                          "MISSING": d["MISSING"], "UNREADABLE": d["UNREADABLE"],
                          "bytes": sum(r["size"] for r in res), "body": body_file.name,
                          "elapsed_s": round(el, 1)}
        add(f"tier[{tier}].B_corpo_vs_disco",
            d["MISMATCH"] == 0 and d["MISSING"] == 0 and d["UNREADABLE"] == 0,
            f"OK={d['OK']} MISMATCH={d['MISMATCH']} MISSING={d['MISSING']} "
            f"UNREADABLE={d['UNREADABLE']}")
        all_failures += [r for r in res if r["verdict"] != "OK"]

        # C
        exdirs = hdr.get("exclude_dirs") or []
        seen = {m: walk_rules(hbase, roots, inc, exc, m, exdirs)
                for m in ("base", "root")}
        if len(seen["base"]) == n_dec:
            best = "base"
        elif len(seen["root"]) == n_dec:
            best = "root"
        else:
            best = min(seen, key=lambda m: abs(len(seen[m]) - (n_dec or 0)))
        found = seen[best]
        extra = sorted(set(found) - tier_paths[tier])
        # paper2_freeze_v1.py esclude results/paper2 nel codice ma non lo dichiara in
        # exclude_pat: sono i prodotti del Paper 2, fuori da v1 per disegno. Vanno separati
        # dagli EXTRA veri, che sono file finiti nel territorio di un tier per sbaglio.
        ex_p2 = [p for p in extra if "results/paper2/" in p.lower()]
        ex_else = [p for p in extra if p not in set(ex_p2)]
        declared_p2 = bool(exdirs) or any("paper2" in str(p) for p in exc)
        rules_report[tier] = {"roots": roots, "include_ext": inc, "exclude_pat": exc,
                              "n_by_rule_base": len(seen["base"]),
                              "n_by_rule_root": len(seen["root"]),
                              "rule_used": best, "n_dec": n_dec,
                              "extra_n": len(extra), "extra": extra[:200],
                              "extra_paper2_n": len(ex_p2),
                              "extra_altrove": ex_else[:200]}
        add(f"tier[{tier}].C_regole_riproducono_n_files", len(found) == n_dec,
            f"regola '{best}' trova {len(found)} contro n_files={n_dec} "
            f"(base={len(seen['base'])} root={len(seen['root'])}"
            + (f", di cui {len(ex_p2)} prodotti Paper 2" if ex_p2 else "") + ")")
        add(f"tier[{tier}].C_file_fuori_manifest_altrove", not ex_else,
            f"{len(ex_else)} file dentro le regole del tier, fuori dal corpo e fuori da "
            f"results/paper2" + (f": {ex_else[:5]}" if ex_else else ""))
        if ex_p2:
            add(f"tier[{tier}].C_esclusione_outdir_dichiarata", declared_p2,
                f"{len(ex_p2)} file sotto results/paper2 esclusi dal corpo, ma "
                f"exclude_pat={exc} ed exclude_dirs={exdirs} non lo dichiarano: "
                f"paper2_freeze_v1.py esclude la propria --out via iter_files, e "
                f"l'intestazione (riga 341) non lo registra")

        # D
        c = aggregate_candidates(entries, body_file)
        match = [k for k, v in c.items() if agg_dec and v == agg_dec]
        doc = documented.get(tier, {})
        agg_report[tier] = {"in_header": agg_dec, "documented": doc.get("aggregate_sha256"),
                            "reproduced_by": match, "candidates": c}
        add(f"tier[{tier}].D_aggregate_ricalcolabile", bool(match),
            f"riprodotto da {match}" if match else
            f"nessuna delle {len(c)} costruzioni candidate riproduce l'aggregate")
        if doc.get("aggregate_sha256"):
            amd = tier in overlay
            add(f"tier[{tier}].aggregate_vs_documento", agg_dec == doc["aggregate_sha256"],
                f"header={str(agg_dec)[:12]}… documento={doc['aggregate_sha256'][:12]}…"
                + (" (emendato)" if amd else ""))
        if doc.get("files") is not None:
            add(f"tier[{tier}].n_files_vs_documento", n_dec == doc["files"],
                f"header={n_dec} documento={doc['files']} delta={(n_dec or 0)-doc['files']:+d}")

    # trasversali
    membership = defaultdict(list)
    for t, ps in tier_paths.items():
        for p in ps:
            membership[p].append(t)
    multi = {p: ts for p, ts in membership.items() if len(ts) > 1}
    add("unione: nessun percorso in due tier", not multi,
        f"{len(multi)} percorsi condivisi" + (f", es. {list(multi)[:3]}" if multi else ""))

    # L'invariante e' che un manifest non hashi se' stesso: se la directory dei manifest
    # cade dentro l'insieme congelato, ogni run cambia il proprio input e maschera la
    # deriva che il manifest esiste per rilevare (paper2_freeze_v1.py, docstring 185-188).
    # Il criterio e' la posizione della manifest dir, NON il nome results/paper2: per il
    # tier paper2_products quella cartella e' la radice, e i suoi file ci stanno di diritto.
    md_rel = rel_to(manifest_dir.resolve().as_posix(), base.resolve().as_posix())
    md_pref = md_rel.rstrip("/") + "/"
    self_ref = sorted(p for p in membership if p.lower().startswith(md_pref.lower()))
    add("nessun manifest congelato dentro il proprio tier", not self_ref,
        f"manifest dir '{md_rel}': {len(self_ref)} suoi file dentro un tier congelato"
        + (f": {self_ref[:6]}" if self_ref else ""))

    tot_files_body = sum(v["files"] for v in per_tier.values())
    tot_union = len(membership)
    tot_bytes = sum(v["bytes"] for v in per_tier.values())
    hdr_files = sum((h.get("n_files") or 0) for h in heads.values())
    hdr_bytes = sum((h.get("total_bytes") or 0) for h in heads.values())

    if set(heads) == set(TIERS):
        add("TOTALE file (unione) vs documento", tot_union == DOCUMENTED_TOTAL_FILES,
            f"unione={tot_union} corpo={tot_files_body} intestazioni={hdr_files} "
            f"documento={DOCUMENTED_TOTAL_FILES}")
        add("TOTALE byte vs documento",
            abs(tot_bytes - DOCUMENTED_TOTAL_BYTES) <= DOCUMENTED_TOTAL_TOL,
            f"disco={fmt_bytes(tot_bytes)} intestazioni={fmt_bytes(hdr_bytes)} "
            f"documento={DOCUMENTED_TOTAL_GIB} GiB")

    ref_info = {}
    ref = base / "src" / "paper2_v1_reference.json"
    if ref.is_file():
        # DUE grandezze distinte sullo stesso file, e confonderle costa ore:
        #  - sha256 dei BYTE del file (332939bc…), citato da consegna e prereg §2.1;
        #  - _self_sha256, il digest del CONTENUTO riserializzato in forma canonica
        #    (865aa2ef…), che e' cio' che load_reference verifica come cancello e cio'
        #    che i manifest registrano in reference_sha256.
        # Il confronto giusto e' fra manifest e _self_sha256. Il digest del file si
        # riporta a parte, senza confrontarlo con niente.
        file_sha, size = sha256_file(ref)
        obj = json.loads(ref.read_text(encoding="utf-8"))
        recorded = obj.pop("_self_sha256", None)
        blob = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
        self_sha = sha256_bytes(blob.encode())
        declared = {t: h.get("reference_sha256") for t, h in heads.items()}
        agree = {v for v in declared.values() if v}
        ref_info = {"file_sha256": file_sha, "self_sha256_recomputed": self_sha,
                    "self_sha256_recorded": recorded, "size": size,
                    "declared_by_manifests": declared}
        add("reference: cancello del self-digest", recorded == self_sha,
            f"registrato={str(recorded)[:12]}… ricalcolato={self_sha[:12]}… "
            f"(byte del file: {file_sha[:12]}…, altra grandezza)")
        add("reference: i manifest concordano fra loro", len(agree) <= 1,
            f"{sorted(x[:12] + '…' for x in agree)}")
        add("reference: manifest vs self-digest del reference vivo",
            bool(agree) and agree == {self_sha},
            f"manifest={[x[:12] + '…' for x in sorted(agree)]} "
            f"self-digest={self_sha[:12]}…")
    am = base / "src" / "paper2_v1_amendments.jsonl"
    if am.is_file():
        lines = [l for l in am.read_text(encoding="utf-8").splitlines() if l.strip()]
        badlines = []
        for i, l in enumerate(lines, 1):
            try:
                json.loads(l)
            except Exception as exc:
                badlines.append({"line": i, "error": str(exc)[:80]})
        # Deriva di schema, sanata leggendo entrambi i nomi: i record fino all'11
        # portano `reference_sha256`, il 12 lo spacca in `reference_file_sha256`
        # (i byte) e `reference_self_sha256` (il contenuto canonico), che e'
        # esattamente la distinzione che quel record esiste per registrare. Un
        # record senza nessuno dei tre non e' ancorato a niente.
        REF_KEYS = ("reference_sha256", "reference_file_sha256",
                    "reference_self_sha256")
        # Solo gli emendamenti veri e propri devono portare l'ancora: una
        # `declaration` non emenda nulla e un `input_hash` porta il digest del
        # file che congela, non quello del reference.
        ANCHORED_TYPES = ("amendment", "protocol")
        unanchored = []
        for i, l in enumerate(lines, 1):
            try:
                r = json.loads(l)
            except Exception:
                continue
            if isinstance(r, dict) and r.get("type") in ANCHORED_TYPES:
                if not any(k in r for k in REF_KEYS):
                    unanchored.append({"line": i, "item": r.get("item"),
                                       "type": r.get("type")})
        ref_info["amendments"] = {"disco": len(lines),
                                  "documentati": DOCUMENTED_AMENDMENTS,
                                  "prereg_al_deposito": PREREG_AMENDMENTS_AT_DEPOSIT,
                                  "malformate": badlines,
                                  "non_ancorati": unanchored,
                                  "tier_emendati": sorted(overlay)}
        add("emendamenti: JSONL integro", not badlines,
            f"disco={len(lines)} righe malformate={len(badlines)}")
        # Il file e' append-only: scendere sotto il conteggio al deposito
        # significa che un record e' stato tolto, che e' l'unica cosa che questo
        # file non deve poter subire.
        add("emendamenti: nessun record perso dal deposito",
            len(lines) >= PREREG_AMENDMENTS_AT_DEPOSIT,
            f"disco={len(lines)} >= prereg §9 al deposito="
            f"{PREREG_AMENDMENTS_AT_DEPOSIT}")
        # E il conteggio corrente deve coincidere con quello dichiarato: se
        # divergono, o il documento e' indietro o l'append e' avvenuto senza
        # aggiornarlo, e in entrambi i casi va saputo prima di citare un numero.
        add("emendamenti: disco == documentazione corrente",
            len(lines) == DOCUMENTED_AMENDMENTS,
            f"disco={len(lines)} documentati={DOCUMENTED_AMENDMENTS}")
        add("emendamenti: ogni record ancorato a un digest del reference",
            not unanchored,
            f"non ancorati={unanchored}" if unanchored
            else f"tutti i {len(lines)} record portano un digest del reference")

    dirty = {t: h.get("git", {}).get("dirty") for t, h in heads.items()}
    commits = {t: (h.get("git", {}).get("commit") or "")[:7] for t, h in heads.items()}
    add("freeze eseguito su albero pulito", not any(dirty.values()),
        f"dirty={dirty} commit={commits}")

    status = "CLEAN" if all(c["ok"] for c in checks) else "DISCREPANCY"
    return {
        "status": status, "utc": utcnow(), "base": str(base.resolve()),
        "manifest_dir": str(manifest_dir), "tiers": sorted(heads),
        "ignored_json": ignored,
        "headers": {t: {**{k: h[k] for k in
                           ("aggregate_sha256", "n_files", "total_bytes", "roots",
                            "include_ext", "exclude_pat", "exclude_dirs",
                            "reference_sha256",
                            "frozen_at_utc", "_header_sha256") if k in h},
                        "git_dirty": h.get("git", {}).get("dirty"),
                        "git_commit": h.get("git", {}).get("commit")}
                    for t, h in heads.items()},
        "per_tier": per_tier, "rules": rules_report, "aggregate": agg_report,
        "totals": {"files_body": tot_files_body, "files_union": tot_union,
                   "files_headers": hdr_files, "bytes_disk": tot_bytes,
                   "bytes_headers": hdr_bytes, "gib_disk": tot_bytes / GIB},
        "multi_tier": {k: v for k, v in list(multi.items())[:20]},
        "self_referential": self_ref[:80],
        "reference": ref_info,
        "failures_n": len(all_failures), "failures": all_failures[:300],
        "checks": checks,
    }


# ------------------------------------------------------------------------------ comandi

def cmd_inspect(args) -> int:
    base = Path(args.base)
    mdir = Path(args.manifest_dir)
    if not mdir.is_absolute():
        mdir = base / mdir
    heads, bodies, ignored = discover(mdir)
    print(f"manifest dir: {mdir}")
    print(f"intestazioni schema {SCHEMA}: {sorted(heads)}")
    print(f"json ignorati: {[i['file'] for i in ignored]}")
    for t in sorted(heads):
        h = heads[t]
        print(f"\n=== {t}")
        print(f"  n_files={h.get('n_files')}  total_bytes={h.get('total_bytes'):,}")
        print(f"  roots={h.get('roots')}")
        print(f"  include_ext={h.get('include_ext')}  exclude_pat={h.get('exclude_pat')}"
              f"  exclude_dirs={h.get('exclude_dirs')}")
        print(f"  aggregate={h.get('aggregate_sha256')}")
        print(f"  reference_sha256={h.get('reference_sha256')}")
        print(f"  frozen={h.get('frozen_at_utc')}  dirty={h.get('git', {}).get('dirty')}")
        for bf in bodies.get(t, []):
            entries, bad, n_sup = load_body(bf)
            print(f"  corpo {bf.name}: {len(entries)} voci, {n_sup} superate, "
                  f"{len(bad)} righe non interpretate")
            if entries:
                print(f"    esempio      : {entries[0]}")
                print(f"    size presente: {all(isinstance(e['size'], int) for e in entries)}")
            if bad:
                print(f"    illeggibili  : {bad[:3]}")
        if t not in bodies:
            print("  corpo: ASSENTE")
    return 0


def cmd_verify(args) -> int:
    base = Path(args.base)
    mdir = Path(args.manifest_dir)
    if not mdir.is_absolute():
        mdir = base / mdir
    out = Path(args.out) if args.out else None
    if out:
        try:
            rel = out.resolve().relative_to(base.resolve()).as_posix()
            if rel.startswith("results/") and not args.force_unsafe_out:
                print(f"RIFIUTO: --out {out} cade dentro results/. Usare logs\\.",
                      file=sys.stderr)
                return 2
        except ValueError:
            pass

    rep = verify(base=base, manifest_dir=mdir, only_tiers=args.tier, jobs=args.jobs)
    if rep["status"] == "SCHEMA_ERROR":
        print(json.dumps(rep, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    print(f"\n=== paper2_freeze_verify rev.2 — {rep['utc']} ===")
    print(f"base: {rep['base']}   tier: {rep['tiers']}")
    print(f"\n  {'tier':<12} {'corpo':>7} {'OK':>7} {'MISM':>6} {'MISS':>6} {'byte':>18} {'s':>7}")
    for t, d in rep["per_tier"].items():
        print(f"  {t:<12} {d['files']:>7} {d['OK']:>7} {d['MISMATCH']:>6} {d['MISSING']:>6} "
              f"{d['bytes']:>18,} {d.get('elapsed_s', 0):>7}")
    tt = rep["totals"]
    print(f"  {'SOMMA':<12} {tt['files_body']:>7} {'':>7} {'':>6} {'':>6} "
          f"{tt['bytes_disk']:>18,}")
    print(f"  unione={tt['files_union']}  intestazioni={tt['files_headers']} file / "
          f"{tt['bytes_headers']:,} B  |  disco {tt['gib_disk']:.5f} GiB")

    print("\ncontrolli:")
    for c in rep["checks"]:
        print(f"  [{'ok' if c['ok'] else 'FAIL'}] {c['check']}: {c['detail']}")

    for t, r in rep["rules"].items():
        if r.get("extra_altrove"):
            print(f"\nEXTRA in {t}, fuori da results/paper2 ({len(r['extra_altrove'])}):")
            for p in r["extra_altrove"][:25]:
                print(f"    {p}")
        if r.get("extra_paper2_n"):
            print(f"\nprodotti Paper 2 non in v1 ({t}): {r['extra_paper2_n']} file sotto "
                  f"results/paper2")
    if rep["failures_n"]:
        print(f"\nfallimenti ({rep['failures_n']}, primi 25):")
        for f in rep["failures"][:25]:
            print(f"    {f['verdict']:<10} [{f['tier']}] {f['path']}")
    print(f"\nreference: {json.dumps(rep['reference'], ensure_ascii=False)}")
    print(f"\nESITO: {rep['status']}")

    if out:
        atomic_append_jsonl(out, [rep])
        print(f"record appeso a {out}")
    return 0 if rep["status"] == "CLEAN" else 1


# ----------------------------------------------------------------------------- selftest

def _w(p: Path, b: bytes):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)


def _freeze(base: Path, mdir: Path, tier: str, roots, inc, exc, ref_sha):
    found = walk_rules(base, roots, inc, exc, "base")
    entries = []
    for rel in sorted(found):
        sha, size = sha256_file(found[rel])
        entries.append({"path": rel, "sha256": sha, "size": size})
    mdir.mkdir(parents=True, exist_ok=True)
    with open(mdir / f"ensemble_v1_manifest_{tier}.jsonl", "w", encoding="utf-8",
              newline="\n") as fh:
        for e in entries:
            fh.write(json.dumps({"rel": e["path"], "sha256": e["sha256"],
                                 "bytes": e["size"], "mtime_utc": utcnow(),
                                 "scanned_at": utcnow()}) + "\n")
    hdr = {"schema": SCHEMA, "schema_version": "1.0", "tier": tier, "ensemble": "v1",
           "base": base.as_posix(), "roots": [Path(r).as_posix() for r in roots],
           "include_ext": inc, "exclude_pat": exc, "n_files": len(entries),
           "total_bytes": sum(e["size"] for e in entries),
           "aggregate_sha256": aggregate_candidates(entries)["REGOLA_freeze_v1[rel_norm]"],
           "reference_sha256": ref_sha,
           "git": {"commit": "0" * 40, "dirty": False}, "frozen_at_utc": utcnow()}
    (mdir / f"ensemble_v1_freeze_{tier}.json").write_text(json.dumps(hdr, indent=1),
                                                          encoding="utf-8")
    return entries


def cmd_selftest(args) -> int:
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")
        ok = ok and bool(cond)

    tmp = Path(tempfile.mkdtemp(prefix="frz2_"))
    try:
        base = tmp / "cauchy"
        for i in range(6):
            _w(base / f"results/paper1/per_mock_{i}.jsonl", f'{{"i":{i}}}\n'.encode())
        for i in range(4):
            _w(base / f"results/fieldsroot/f{i}.npz", bytes([i]) * (200 + i))
        _w(base / "results/fieldsroot/phase8_skip.npz", b"x" * 10)
        def _mkref(payload):
            o = dict(payload)
            o["_self_sha256"] = sha256_bytes(json.dumps(
                payload, indent=2, sort_keys=True, ensure_ascii=False).encode())
            _w(base / "src/paper2_v1_reference.json",
               json.dumps(o, indent=2).encode())
            return o["_self_sha256"]
        ref_sha = _mkref({"r": 1})          # e' il SELF-digest, come nei manifest veri
        _w(base / "src/paper2_v1_amendments.jsonl",
           b'{"a":1}\n' * DOCUMENTED_AMENDMENTS)
        mdir = base / "results/paper2"

        _freeze(base, mdir, "records", [base / "results/paper1"], [".jsonl"], [], ref_sha)
        _freeze(base, mdir, "fields", [base / "results/fieldsroot"], [".npz"],
                ["phase8_"], ref_sha)

        def run():
            return verify(base=base, manifest_dir=mdir, jobs=1, documented={})

        r = run()
        expect("1. freeze sintetico -> CLEAN", r["status"] == "CLEAN",
               f"({[c['check'] for c in r['checks'] if not c['ok']]})")
        expect("1b. exclude_pat rispettato", r["per_tier"]["fields"]["files"] == 4)
        expect("1c. aggregate ricalcolabile",
               all(r["aggregate"][t]["reproduced_by"] for t in ("records", "fields")))

        p = base / "results/paper1/per_mock_2.jsonl"
        keep = p.read_bytes(); p.write_bytes(keep[:-1] + b" \n")
        expect("2. byte modificato -> MISMATCH",
               any(f["verdict"] == "MISMATCH" for f in run()["failures"]))
        p.write_bytes(keep)

        p = base / "results/fieldsroot/f1.npz"; keep = p.read_bytes(); p.unlink()
        expect("3. file assente -> MISSING",
               any(f["verdict"] == "MISSING" for f in run()["failures"]))
        _w(p, keep)

        _w(base / "results/paper1/per_mock_NUOVO.jsonl", b'{"z":1}\n')
        r = run()
        expect("4. file nuovo dentro le regole -> EXTRA, senza alcun MISMATCH",
               r["rules"]["records"]["extra_n"] == 1
               and not any(f["verdict"] == "MISMATCH" for f in r["failures"]))
        (base / "results/paper1/per_mock_NUOVO.jsonl").unlink()

        bf = mdir / "ensemble_v1_manifest_records.jsonl"
        lines = bf.read_text().splitlines(True)
        bf.write_text("".join(lines[:-1]))
        r = run()
        expect("5. corpo troncato -> intestazione, regole e aggregate lo intercettano",
               any(c["check"].endswith("A_intestazione_vs_corpo_n") and not c["ok"]
                   for c in r["checks"])
               and r["rules"]["records"]["extra_n"] == 1
               and not r["aggregate"]["records"]["reproduced_by"])
        bf.write_text("".join(lines))

        # 6. il reference cambiato deve rompere il confronto col self-digest, e il
        #    digest dei BYTE non deve mai essere confuso con quello del contenuto.
        import json as _j, hashlib as _h
        def _self(o):
            o = dict(o); o.pop("_self_sha256", None)
            return _h.sha256(_j.dumps(o, indent=2, sort_keys=True,
                                      ensure_ascii=False).encode()).hexdigest()
        _mkref({"r": 1})
        r6 = run()
        gate_ok = any(c["check"] == "reference: cancello del self-digest" and c["ok"]
                      for c in r6["checks"])
        expect("6. self-digest ricalcolato coincide col registrato", gate_ok)
        expect("6b. digest dei byte tenuto distinto dal self-digest",
               r6["reference"]["file_sha256"] != r6["reference"]["self_sha256_recomputed"])
        bad = {"r": 2, "_self_sha256": ref_sha}     # contenuto cambiato, digest vecchio
        _w(base / "src/paper2_v1_reference.json", _j.dumps(bad, indent=2).encode())
        expect("6c. contenuto alterato -> cancello del self-digest rotto",
               any(c["check"] == "reference: cancello del self-digest" and not c["ok"]
                   for c in run()["checks"]))
        _mkref({"r": 1})

        (mdir / "provenance_audit.json").write_text('{"A":1}')
        (mdir / "inventory.json").write_text(
            json.dumps({"files": [{"path": "x", "sha256": "0" * 64}]}))
        r = run()
        expect("7. json senza lo schema del freeze ignorati",
               set(r["tiers"]) == {"records", "fields"}
               and {"provenance_audit.json", "inventory.json"}
               <= {i["file"] for i in r["ignored_json"]})

        # 8. un tier la cui radice E' la manifest dir: si hasherebbe da solo
        _freeze(base, mdir, "features", [mdir], [".json", ".jsonl"], [], ref_sha)
        r = run()
        expect("8. tier che contiene i propri manifest -> autoreferenzialita' rilevata",
               bool(r["self_referential"])
               and any(c["check"].startswith("nessun manifest congelato") and not c["ok"]
                       for c in r["checks"]))
        for f in list(mdir.glob("*features*")):
            f.unlink()

        # 8b. un tier la cui RADICE sta sotto results/paper2 ma i cui manifest stanno
        #     altrove non e' autoreferenziale: e' il caso di paper2_products.
        prod = base / "results/paper2/prodotti"
        _w(prod / "risultato.jsonl", b'{"p":1}\n')
        alt = base / "manifests"
        _freeze(base, alt, "superseded", [prod], [".jsonl"], [], ref_sha)
        r8b = verify(base=base, manifest_dir=alt, jobs=1, documented={})
        expect("8b. radice sotto results/paper2, manifest altrove -> nessun allarme",
               not r8b["self_referential"] and r8b["status"] == "CLEAN",
               f"({[c['check'] for c in r8b['checks'] if not c['ok']]})")
        shutil.rmtree(alt); shutil.rmtree(prod)

        # 12. corpo accodato: last-wins, non conteggio di righe
        bf2 = mdir / "ensemble_v1_manifest_records.jsonl"
        orig_lines = bf2.read_text()
        first = json.loads(orig_lines.splitlines()[0])
        with open(bf2, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(first) + "\n")      # riga duplicata, identica
        r = verify(base=base, manifest_dir=mdir, jobs=1, documented={})
        expect("12. riga superata collassata: n_files e aggregate restano validi",
               r["per_tier"]["records"]["files"] == 6
               and r["aggregate"]["records"]["reproduced_by"]
               and all(c["ok"] for c in r["checks"]
                       if c["check"].startswith("tier[records].A_")),
               f"(voci={r['per_tier']['records']['files']})")
        bf2.write_text(orig_lines)

        # 11. exclude_dirs dichiarato nell'intestazione rende il replay esatto
        _w(base / "results/paper1/out_side/extra.jsonl", b'{"q":1}\n')
        r_no = verify(base=base, manifest_dir=mdir, jobs=1, documented={})
        hp = mdir / "ensemble_v1_freeze_records.json"
        h = json.loads(hp.read_text())
        h["exclude_dirs"] = ["results/paper1/out_side"]
        hp.write_text(json.dumps(h, indent=1))
        r_yes = verify(base=base, manifest_dir=mdir, jobs=1, documented={})
        expect("11. exclude_dirs dichiarato: il replay torna esatto",
               r_no["rules"]["records"]["n_by_rule_base"] == 7
               and r_yes["rules"]["records"]["n_by_rule_base"] == 6
               and not r_yes["rules"]["records"]["extra_altrove"],
               f"(senza={r_no['rules']['records']['n_by_rule_base']} "
               f"con={r_yes['rules']['records']['n_by_rule_base']})")
        shutil.rmtree(base / "results/paper1/out_side")
        h.pop("exclude_dirs"); hp.write_text(json.dumps(h, indent=1))

        # 10. un emendamento registrato non deve essere riportato come deriva
        hdrp = mdir / "ensemble_v1_freeze_records.json"
        h = json.loads(hdrp.read_text())
        doc_old = {"records": {"files": 999,
                               "aggregate_sha256": "1" * 64}}
        r = verify(base=base, manifest_dir=mdir, jobs=1, documented=doc_old)
        pre = [c["check"] for c in r["checks"] if not c["ok"]]
        _w(base / "src/paper2_v1_amendments.jsonl",
           (b'{"a":1}\n' * (DOCUMENTED_AMENDMENTS - 1)) + json.dumps(
               {"json_path": "ensemble_v1_freeze_records",
                "old_value": {"n_files": 999, "aggregate_sha256": "1" * 64},
                "new_value": {"n_files": h["n_files"],
                              "aggregate_sha256": h["aggregate_sha256"]},
                "reason": "test"}).encode() + b"\n")
        r2 = verify(base=base, manifest_dir=mdir, jobs=1, documented=doc_old)
        post = [c["check"] for c in r2["checks"] if not c["ok"]]
        expect("10. emendamento sovrapposto: la deriva registrata smette di apparire",
               any("records].n_files_vs_documento" in c for c in pre)
               and not any("records].n_files_vs_documento" in c for c in post)
               and not any("records].aggregate_vs_documento" in c for c in post),
               f"(prima={len(pre)} dopo={len(post)})")
        _w(base / "src/paper2_v1_amendments.jsonl",
           b'{"a":1}\n' * DOCUMENTED_AMENDMENTS)

        # 13. il conteggio degli emendamenti e' un'asserzione, non piu' una nota
        def _named(res, frag):
            return [c for c in res["checks"] if frag in c["check"]]
        r_ok = verify(base=base, manifest_dir=mdir, jobs=1, documented={})
        _w(base / "src/paper2_v1_amendments.jsonl",
           b'{"a":1}\n' * (DOCUMENTED_AMENDMENTS - 1))
        r_short = verify(base=base, manifest_dir=mdir, jobs=1, documented={})
        _w(base / "src/paper2_v1_amendments.jsonl",
           b'{"a":1}\n' * (DOCUMENTED_AMENDMENTS + 1))
        r_long = verify(base=base, manifest_dir=mdir, jobs=1, documented={})
        expect("13. conteggio emendamenti: giusto passa, corto e lungo falliscono",
               all(c["ok"] for c in _named(r_ok, "disco == documentazione"))
               and not any(c["ok"] for c in _named(r_short, "disco == documentazione"))
               and not any(c["ok"] for c in _named(r_long, "disco == documentazione")),
               f"(atteso {DOCUMENTED_AMENDMENTS})")

        # 14. append-only: sotto il conteggio al deposito e' un record perso
        _w(base / "src/paper2_v1_amendments.jsonl",
           b'{"a":1}\n' * (PREREG_AMENDMENTS_AT_DEPOSIT - 1))
        r_lost = verify(base=base, manifest_dir=mdir, jobs=1, documented={})
        expect("14. record perso dal deposito: segnalato a parte dal conteggio",
               not any(c["ok"] for c in _named(r_lost, "nessun record perso"))
               and any(c["ok"] for c in _named(r_short, "nessun record perso")),
               f"(deposito={PREREG_AMENDMENTS_AT_DEPOSIT})")

        # 15. un record senza digest del reference non passa inosservato
        _w(base / "src/paper2_v1_amendments.jsonl",
           (b'{"a":1}\n' * (DOCUMENTED_AMENDMENTS - 1))
           + json.dumps({"type": "amendment", "item": "senza-ancora"}).encode()
           + b"\n")
        r_ua = verify(base=base, manifest_dir=mdir, jobs=1, documented={})
        expect("15. record senza digest del reference: segnalato",
               not any(c["ok"] for c in _named(r_ua, "ogni record ancorato")))
        _w(base / "src/paper2_v1_amendments.jsonl",
           b'{"a":1}\n' * DOCUMENTED_AMENDMENTS)

        outp = base / "logs" / "o.jsonl"
        atomic_append_jsonl(outp, [{"a": 1}]); atomic_append_jsonl(outp, [{"a": 2}])
        expect("9. JSONL append-only",
               len([l for l in outp.read_text().splitlines() if l.strip()]) == 2)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("selftest"); p.set_defaults(func=cmd_selftest)
    for name, fn in (("inspect", cmd_inspect), ("verify", cmd_verify)):
        p = sub.add_parser(name)
        p.add_argument("--base", default=".")
        p.add_argument("--manifest-dir", default="results/paper2")
        if name == "verify":
            p.add_argument("--tier", nargs="+", default=None)
            p.add_argument("--jobs", type=int, default=1)
            p.add_argument("--out", default=None)
            p.add_argument("--force-unsafe-out", action="store_true")
        p.set_defaults(func=fn)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

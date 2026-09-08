#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_lettura_4_2b.py — lettore di provenienza per le due letture di §4 della consegna.

NON calcola nulla e NON scrive nulla nell'albero dei risultati: cerca, e riporta
DOVE stanno e COME sono fatti i numeri di 4.2b:

    varianza di delta, curtosi in eccesso di nu, nu99 - nu1, massimo di delta,
    scansione Box-Cox (epsilon).

Per ogni chiave trovata riporta il fatto che decide la lettura 2:
`varia` — se il valore cambia fra i record campionati (quantita' PER REALIZZAZIONE)
oppure e' unico (quantita' AGGREGATA, media o fiduciale).

Uso:
    python paper2_lettura_4_2b.py scan --root D:\\projects\\cauchy --out logs\\lettura_4_2b.jsonl
    python paper2_lettura_4_2b.py selftest
"""

import argparse
import json
import os
import re
import sys
import tempfile

PATTERNS = {
    "boxcox":    re.compile(r"box[_\-]?cox|t_eps|(?<![a-z])epsilon(?![a-z])|(?<![a-z])eps(?![a-z])", re.I),
    "kurtosi":   re.compile(r"kurt", re.I),
    "var_delta": re.compile(r"var[_\.]?delta|delta[_\.]?var|var[_\.]?ratio|variance[_\-]?ratio|var[_\.]?d(?![a-z])", re.I),
    "nu_range":  re.compile(r"nu[_\-]?99|nu[_\-]?1(?![0-9])|p99|percentil\w*[_\- ]?99", re.I),
    "delta_max": re.compile(r"max[_\-]?delta|delta[_\-]?max", re.I),
}

SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", "node_modules",
             ".venv", "venv", ".mypy_cache", ".pytest_cache"}
DATA_EXT = {".jsonl", ".json"}
CODE_EXT = {".py"}
MAX_BYTES_JSON = 64 * 1024 * 1024


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict,)):
                out.update(flatten(v, key))
            elif isinstance(v, list):
                out[key] = f"<list n={len(v)}>"
            else:
                out[key] = v
    return out


def match_key(key):
    for name, rx in PATTERNS.items():
        if rx.search(key):
            return name
    return None


def scan_data_file(path, max_records):
    """Restituisce {chiave: {'famiglia':.., 'valori':[..], 'n':int}} sui record campionati."""
    found = {}
    n_rec = 0
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".jsonl":
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    n_rec += 1
                    for k, v in flatten(rec).items():
                        fam = match_key(k)
                        if fam is None:
                            continue
                        slot = found.setdefault(k, {"famiglia": fam, "valori": []})
                        if len(slot["valori"]) < 8:
                            slot["valori"].append(v)
                    if n_rec >= max_records:
                        break
        else:
            if os.path.getsize(path) > MAX_BYTES_JSON:
                return {}, 0
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                rec = json.load(fh)
            n_rec = 1
            for k, v in flatten(rec).items():
                fam = match_key(k)
                if fam is None:
                    continue
                found.setdefault(k, {"famiglia": fam, "valori": [v]})
    except Exception:
        return {}, 0
    return found, n_rec


def scan_code_file(path, max_hits=12):
    hits = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                fam = match_key(line)
                if fam is None:
                    continue
                hits.append({"riga": i, "famiglia": fam, "testo": line.strip()[:200]})
                if len(hits) >= max_hits:
                    break
    except Exception:
        return []
    return hits


def scan(root, out_path, max_records):
    root = os.path.abspath(root)
    records = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if ext in DATA_EXT:
                found, n_rec = scan_data_file(full, max_records)
                for key, slot in found.items():
                    vals = slot["valori"]
                    varia = len({repr(v) for v in vals}) > 1
                    records.append({
                        "tipo": "dato", "file": rel, "chiave": key,
                        "famiglia": slot["famiglia"], "n_record_campionati": n_rec,
                        "varia": varia,
                        "lettura": "per realizzazione" if varia else "aggregata o unico record",
                        "primi_valori": vals[:4],
                    })
            elif ext in CODE_EXT:
                for h in scan_code_file(full):
                    records.append({
                        "tipo": "codice", "file": rel, "riga": h["riga"],
                        "famiglia": h["famiglia"], "testo": h["testo"],
                    })

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return records


def riassunto(records):
    per_fam = {}
    for r in records:
        per_fam.setdefault(r["famiglia"], {"dato": 0, "codice": 0, "per_realizzazione": 0})
        per_fam[r["famiglia"]][r["tipo"]] += 1
        if r["tipo"] == "dato" and r["varia"]:
            per_fam[r["famiglia"]]["per_realizzazione"] += 1
    return per_fam


def cmd_scan(args):
    records = scan(args.root, args.out, args.max_records)
    per_fam = riassunto(records)
    print(f"radice: {os.path.abspath(args.root)}")
    print(f"record emessi: {len(records)}")
    for fam in sorted(PATTERNS):
        d = per_fam.get(fam, {"dato": 0, "codice": 0, "per_realizzazione": 0})
        print(f"  {fam:10s}  chiavi-dato={d['dato']:4d}  di cui per-realizzazione={d['per_realizzazione']:4d}  righe-codice={d['codice']:4d}")
    if args.out:
        print(f"registro: {os.path.abspath(args.out)}")
    if not records:
        print("NESSUN RISCONTRO — la radice e' sbagliata oppure i nomi delle chiavi sono altri.")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="lettura42b_")
    os.makedirs(os.path.join(base, "results"))
    os.makedirs(os.path.join(base, "src"))
    os.makedirs(os.path.join(base, ".git"))

    p_jsonl = os.path.join(base, "results", "onepoint_NGC.jsonl")
    with open(p_jsonl, "w", encoding="utf-8", newline="") as fh:
        for i in range(4):
            fh.write(json.dumps({"mock_id": i,
                                 "base": {"excess_kurtosis_nu": 3.90 + 0.01 * i,
                                          "var_delta": 1000 + i,
                                          "n_h1": 35000 + i}}) + "\n")

    p_json = os.path.join(base, "results", "aggregato.json")
    with open(p_json, "w", encoding="utf-8", newline="") as fh:
        json.dump({"var_ratio_mock_desi": 1085.0, "delta_max": 32244}, fh)

    p_py = os.path.join(base, "src", "onepoint.py")
    with open(p_py, "w", encoding="utf-8", newline="") as fh:
        fh.write("from scipy.stats import kurtosis\n")
        fh.write("k = kurtosis(nu[mask], fisher=True, bias=False)\n")
        fh.write("t_eps = ((1.0 + delta) ** eps - 1.0) / eps\n")

    with open(os.path.join(base, ".git", "sporco.jsonl"), "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"kurt": 1}) + "\n")

    rec = scan(base, None, max_records=1000)
    dati = {(r["file"].replace("\\", "/"), r["chiave"]): r for r in rec if r["tipo"] == "dato"}
    codice = [r for r in rec if r["tipo"] == "codice"]

    k_kurt = ("results/onepoint_NGC.jsonl", "base.excess_kurtosis_nu")
    k_var = ("results/onepoint_NGC.jsonl", "base.var_delta")
    k_agg = ("results/aggregato.json", "var_ratio_mock_desi")
    k_dmax = ("results/aggregato.json", "delta_max")

    ok("1 curtosi trovata nel jsonl", k_kurt in dati)
    ok("2 curtosi classificata per realizzazione", dati.get(k_kurt, {}).get("varia") is True)
    ok("3 quattro record campionati", dati.get(k_kurt, {}).get("n_record_campionati") == 4)
    ok("4 var_delta trovata nel jsonl", k_var in dati)
    ok("5 rapporto aggregato trovato", k_agg in dati)
    ok("6 rapporto aggregato NON per realizzazione", dati.get(k_agg, {}).get("varia") is False)
    ok("7 massimo di delta trovato", k_dmax in dati)
    ok("8 famiglia corretta per il massimo", dati.get(k_dmax, {}).get("famiglia") == "delta_max")
    ok("9 chiave non pertinente ignorata", all(k[1] != "base.n_h1" for k in dati))
    ok("10 .git escluso", all(".git" not in r["file"] for r in rec))
    ok("11 riga di codice della curtosi", any(c["famiglia"] == "kurtosi" and c["riga"] == 2 for c in codice))
    ok("12 riga di codice del Box-Cox", any(c["famiglia"] == "boxcox" and c["riga"] == 3 for c in codice))

    # Controllo COMPORTAMENTALE: con un solo record campionato la classificazione
    # "per realizzazione" DEVE cambiare. Se restasse vera, il flag non e' calcolato.
    rec1 = scan(base, None, max_records=1)
    dati1 = {(r["file"].replace("\\", "/"), r["chiave"]): r for r in rec1 if r["tipo"] == "dato"}
    ok("13 con max-records=1 il flag varia diventa falso",
       dati1.get(k_kurt, {}).get("varia") is False and dati1.get(k_kurt, {}).get("n_record_campionati") == 1)

    # Controllo del registro su disco: una riga per record, newline=\"\" (Windows).
    out = os.path.join(base, "logs", "lettura.jsonl")
    scan(base, out, max_records=1000)
    with open(out, "rb") as fh:
        raw = fh.read()
    ok("14 registro senza CRLF", b"\r\n" not in raw)
    ok("15 registro con una riga per record", raw.decode("utf-8").count("\n") == len(rec))

    passati = sum(1 for _, c in controlli if c)
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print(f"selftest: {passati}/{len(controlli)}")
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="cerca chiavi e definizioni sotto --root")
    p_scan.add_argument("--root", required=True)
    p_scan.add_argument("--out", default=None)
    p_scan.add_argument("--max-records", type=int, default=200)
    p_scan.set_defaults(func=cmd_scan)

    p_st = sub.add_parser("selftest", help="esegue i 15 controlli")
    p_st.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
paper2_inventario_6_2vi.py  —  voce 6.2-vi: inventario di sola lettura di results/**/*.json(l)

Per ogni file: percorso, byte, sha256, righe (JSONL) e righe malformate, 'schema' e 'script'
dichiarati, chiavi del primo record, chiavi di verdetto trovate (token ESATTO, non
sottostringa), tracciato da git o no, citato dal ledger e dai documenti per percorso o solo
per nome. Non scrive niente fuori da logs/.

Uso:
  python src\\paper2_inventario_6_2vi.py selftest
  python src\\paper2_inventario_6_2vi.py run      ->  logs\\inventario_6_2vi.json
"""
import argparse, hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = Path("src/paper2_v1_amendments.jsonl")
DOCUMENTI = [Path(p) for p in (
    "papers/paper2/checklist_paper2.md", "papers/paper2/paper2_stato.md",
    "papers/paper2/paper2_budget_5_1.md", "papers/paper2/modifiche_paper1.md",
    "papers/paper2/paper2_prereg_v1.md", "papers/paper2/paper2_5_5_smentite.md",
    "REPRODUCIBILITY.md")]
TOKEN_VERDETTO = {"verdict", "verdetto", "verdetti", "esito", "esiti", "outcome", "passed",
                  "pass", "fail", "failed", "superato", "superata", "decision", "decisione"}
MAX_REC_SCAN = 50          # record JSONL scansionati per le chiavi di verdetto
MAX_VERDETTI = 20          # chiavi di verdetto riportate per file

def token(k: str):
    return {t for t in re.split(r"[^0-9a-zA-Zàèéìòù]+", str(k).lower()) if t}

def chiavi_verdetto(o, p="", out=None):
    out = [] if out is None else out
    if len(out) >= MAX_VERDETTI: return out
    if isinstance(o, dict):
        for k, v in o.items():
            q = f"{p}/{k}"
            if token(k) & TOKEN_VERDETTO:
                out.append((q, v if isinstance(v, (bool, int, float)) or v is None else str(v)[:80]))
            chiavi_verdetto(v, q, out)
    elif isinstance(o, list):
        for i, v in enumerate(o[:200]):
            chiavi_verdetto(v, f"{p}/{i}", out)
    return out

def leggi_file(p: Path):
    raw = p.read_bytes()
    d = {"byte": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    txt = raw.decode("utf-8", errors="replace")
    primo, ver = None, []
    if p.suffix == ".jsonl":
        righe = [l for l in txt.splitlines() if l.strip()]
        d["righe"], mal = len(righe), 0
        d["righe_distinte"] = len(set(righe))
        for i, l in enumerate(righe):
            try: r = json.loads(l)
            except Exception: mal += 1; continue
            if primo is None: primo = r
            if i < MAX_REC_SCAN: chiavi_verdetto(r, f"#{i+1}", ver)
        d["malformate"] = mal
    else:
        try:
            primo = json.loads(txt); chiavi_verdetto(primo, "", ver); d["malformate"] = 0
        except Exception:
            d["malformate"] = 1
    if isinstance(primo, dict):
        d["chiavi_primo"] = list(primo)[:25]
        for k in ("schema", "script", "region", "regione"):
            if k in primo and not isinstance(primo[k], (dict, list)): d[k] = primo[k]
    d["verdetti"] = ver[:MAX_VERDETTI]
    return d

def citazioni(rel: str, testi: dict):
    nome = rel.rsplit("/", 1)[-1]
    out = {}
    for fonte, t in testi.items():
        per_percorso = rel in t or rel.replace("/", "\\") in t or rel.replace("/", "\\\\") in t
        per_nome = (not per_percorso) and re.search(r"(?<![\w.-])" + re.escape(nome) + r"(?![\w.-])", t) is not None
        if per_percorso: out[fonte] = "percorso"
        elif per_nome: out[fonte] = "solo_nome"
    return out

def record_citanti(rel: str, righe_ledger):
    nome = rel.rsplit("/", 1)[-1]
    pat = re.compile(r"(?<![\w.-])" + re.escape(nome) + r"(?![\w.-])")
    return [i + 1 for i, l in enumerate(righe_ledger) if pat.search(l)]

def inventario(base: Path, tracciati: set):
    testi, righe_ledger = {}, []
    lp = base / LEDGER
    if lp.exists():
        t = lp.read_text(encoding="utf-8"); testi["ledger"] = t; righe_ledger = t.splitlines()
    for d in DOCUMENTI:
        if (base / d).exists(): testi[d.name] = (base / d).read_text(encoding="utf-8", errors="replace")
    files = sorted(p for p in (base / "results").rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl"))
    out = []
    for p in files:
        rel = p.relative_to(base).as_posix()
        e = {"path": rel, "tipo": p.suffix[1:], "git": rel in tracciati}
        e.update(leggi_file(p))
        e["citato_da"] = citazioni(rel, testi)
        e["record_ledger"] = record_citanti(rel, righe_ledger)
        out.append(e)
    return out, sorted(testi)

def git_tracciati(base: Path):
    r = subprocess.run(["git", "-C", str(base), "ls-files", "-z", "results"], capture_output=True)
    if r.returncode != 0:
        raise SystemExit("STOP: git ls-files fallito; l'inventario non indovina lo stato di git")
    return {x for x in r.stdout.decode("utf-8").split("\0") if x}

# ── selftest ───────────────────────────────────────────────────────────────
def selftest():
    ok = 0
    # 1: token esatto — il difetto di «sign» dentro «signal», riprodotto e poi escluso
    assert "sign" in "signal" and not (token("bypass_signal") & TOKEN_VERDETTO); ok += 1
    assert token("gate_passed") & TOKEN_VERDETTO and token("esito") & TOKEN_VERDETTO; ok += 1
    assert not (token("passenger") & TOKEN_VERDETTO) and not (token("failover_x") & TOKEN_VERDETTO); ok += 1
    with tempfile.TemporaryDirectory() as td:
        b = Path(td); (b / "results/paper2").mkdir(parents=True); (b / "src").mkdir()
        (b / "results/paper2/a.jsonl").write_bytes(b'{"schema":"s1","x":{"gate_passed":true}}\n{"x":1}\nnon json\n{"x":1}\n')
        (b / "results/paper2/rep.json").write_bytes(b'{"script":"p.py","signal":3,"verdetto":"FAIL"}')
        (b / "results/paper2/altro_a.jsonl").write_bytes(b'{"y":2}\n')
        (b / "src/paper2_v1_amendments.jsonl").write_text(
            '{"evidence":"results/paper2/rep.json"}\n{"evidence":"vedi a.jsonl e xa.jsonl"}\n', encoding="utf-8")
        inv, fonti = inventario(b, {"results/paper2/rep.json"})
        m = {e["path"]: e for e in inv}
        a, r, x = m["results/paper2/a.jsonl"], m["results/paper2/rep.json"], m["results/paper2/altro_a.jsonl"]
        # 4: righe, malformate, distinte
        assert (a["righe"], a["malformate"], a["righe_distinte"]) == (4, 1, 3); ok += 1
        # 5: verdetti a profondità, e «signal» non è un verdetto
        assert a["verdetti"] == [("#1/x/gate_passed", True)] and r["verdetti"] == [("/verdetto", "FAIL")]; ok += 1
        # 6: git
        assert r["git"] and not a["git"]; ok += 1
        # 7: citazione per percorso contro solo per nome, e record del ledger
        assert r["citato_da"] == {"ledger": "percorso"} and r["record_ledger"] == [1]; ok += 1
        assert a["citato_da"] == {"ledger": "solo_nome"} and a["record_ledger"] == [2]; ok += 1
        # 9: «altro_a.jsonl» non è citato da «a.jsonl», né «a.jsonl» da «xa.jsonl»
        assert x["citato_da"] == {} and x["record_ledger"] == []; ok += 1
    print(f"selftest: {ok}/9 OK")

def run():
    tr = git_tracciati(ROOT)
    inv, fonti = inventario(ROOT, tr)
    lp = ROOT / LEDGER
    out = {"schema": "paper2_inventario_6_2vi_v1", "fonti_lette": fonti,
           "ledger_sha256": hashlib.sha256(lp.read_bytes()).hexdigest() if lp.exists() else None,
           "n_file": len(inv), "file": inv}
    dest = ROOT / "logs" / "inventario_6_2vi.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n = lambda f: sum(1 for e in inv if f(e))
    print(f"file: {len(inv)}  (json {n(lambda e: e['tipo']=='json')}, jsonl {n(lambda e: e['tipo']=='jsonl')})")
    print(f"tracciati da git: {n(lambda e: e['git'])}   con righe malformate: {n(lambda e: e.get('malformate'))}")
    print(f"con chiavi di verdetto: {n(lambda e: e['verdetti'])}   citati dal ledger: {n(lambda e: e['record_ledger'])}"
          f"   non citati da nessuna fonte: {n(lambda e: not e['citato_da'])}")
    print(f"fonti lette: {', '.join(fonti)}")
    print(f"scritto: {dest.relative_to(ROOT)}  {dest.stat().st_size} byte  sha {hashlib.sha256(dest.read_bytes()).hexdigest()[:12]}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "run"])
    {"selftest": selftest, "run": run}[ap.parse_args().cmd]()

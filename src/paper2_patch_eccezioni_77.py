#!/usr/bin/env python3
"""
paper2_patch_eccezioni_77.py  -  eccezioni del rilascio 22 -> 23: papers/paper2/paper2_6_5_ritirati.md

Il censimento del rilascio dopo il record 77 (logs/censimento_rilascio_77.jsonl) ha dato
citati_non_esclusi FAIL su un solo percorso, come previsto: il documento della voce 6.5, citato
dal campo `document` del record 77 ed escluso da .gitignore:80 (papers/). Le eccezioni non sono la
fonte autorevole, lo sono i record: qui l'autorita' e' il record 70 §i (papers/ fuori dal
versionamento) e il record 77, che ancora il documento per byte in rules.documents_by_digest.
Nessun record nuovo.

Rifiuta se: il file delle eccezioni non e' all'ancora; la sua riserializzazione non ridà i byte
originali (allora il formato non e' quello che questo patcher sa scrivere); la voce esiste gia';
il record 77 non ancora il documento con quel digest; il documento su disco ha un altro sha; il
risultato non ha lo sha atteso; togliere la voce non ridà il file originale.

Uso:
  python src\\paper2_patch_eccezioni_77.py selftest
  python src\\paper2_patch_eccezioni_77.py dry-run
  python src\\paper2_patch_eccezioni_77.py apply
  python src\\paper2_patch_eccezioni_77.py verify
"""
import argparse, hashlib, json, os, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "logs" / "eccezioni_rilascio.json"
LEDGER = ROOT / "src" / "paper2_v1_amendments.jsonl"
DOC = ROOT / "papers" / "paper2" / "paper2_6_5_ritirati.md"
PRIMA = ("2783ab80088a77b799b960a10b47dc8be12eb2918167a05bffdd3b8b080c1321", 11492)
DOPO = ("464e628b1dad546105712f388190ae54f335e34c3a04a7688ce0b8fa7f7deda9", 12153)
DOC_SHA = ("517e72095feb376b359f3b67df754a33ff3a048a98716a09d4466d80873d1770", 4868)
CHIAVE = "papers/paper2/paper2_6_5_ritirati.md"
MOTIVO = ("FUORI dal versionamento, decisione del record 70 §i, come tutto papers/. Citato dal record 77 "
          "nel campo `document` e ancorato per byte dallo stesso record in rules.documents_by_digest: "
          "sha256 517e72095feb376b359f3b67df754a33ff3a048a98716a09d4466d80873d1770, 4868 byte al 23 set 2026. "
          "E' l'elenco della voce 6.5, chiusa dal record 77: le 17 affermazioni del canovaccio del 24 luglio "
          "(canovaccio_paper2_rev1.md, 1152bcc9...) col loro esito. Il documento e' CHIUSO e non va riscritto: "
          "l'ancora sta nel ledger, e una nota aggiunta dopo la renderebbe stale. Cio' che viene dopo la 6.5 "
          "sta nella checklist e nello stato.")

def sha(b): return hashlib.sha256(b).hexdigest()
def serializza(d): return (json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

def trasforma(raw: bytes) -> bytes:
    d = json.loads(raw.decode("utf-8"))
    if serializza(d) != raw: raise ValueError("la riserializzazione non ridà i byte originali: formato sconosciuto")
    if CHIAVE in d: raise ValueError(f"la voce {CHIAVE} esiste gia'")
    d[CHIAVE] = MOTIVO
    nuovo = serializza(d)
    d2 = json.loads(nuovo.decode("utf-8")); del d2[CHIAVE]
    if serializza(d2) != raw: raise ValueError("togliere la voce non ridà il file originale")
    return nuovo

def autorita() -> list:
    err = []
    righe = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    r77 = json.loads(righe[76]) if len(righe) >= 77 else {}
    if not r77.get("numbering_rule", "").endswith("record 77."): err.append("ledger: il record 77 non e' in posizione 77")
    elif r77.get("rules", {}).get("documents_by_digest", {}).get("paper2_6_5_ritirati.md") != DOC_SHA[0]:
        err.append("record 77: non ancora paper2_6_5_ritirati.md con 517e7209...")
    elif CHIAVE not in r77.get("document", ""): err.append("record 77: il campo document non cita il percorso")
    raw = DOC.read_bytes() if DOC.exists() else b""
    if (sha(raw), len(raw)) != DOC_SHA: err.append(f"documento su disco: {sha(raw)[:12]}..., {len(raw)} byte")
    return err

def dry_run(scrivi=False):
    raw = FILE.read_bytes(); s = sha(raw)
    if s == DOPO[0]: print("gia' all'ancora «dopo», non si tocca"); return
    if (s, len(raw)) != PRIMA: raise SystemExit(f"STOP: eccezioni {s[:12]}..., {len(raw)} byte, attese {PRIMA[0][:12]}..., {PRIMA[1]}")
    err = autorita()
    if err: print("STOP:"); [print("  -", e) for e in err]; raise SystemExit(1)
    try: nuovo = trasforma(raw)
    except ValueError as e: raise SystemExit(f"STOP: {e}")
    if sha(nuovo) != DOPO[0]: raise SystemExit(f"STOP: risultato {sha(nuovo)[:12]}..., atteso {DOPO[0][:12]}...")
    print(f"eccezioni: {s[:12]}... {len(raw)} B, 22 voci -> {sha(nuovo)[:12]}... {len(nuovo)} B, 23 voci; "
          f"autorita' del record 77 verificata; inversa OK")
    if not scrivi: print("[dry-run] niente scritto."); return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (FILE.parent / f"{FILE.name}.bak_{ts}").write_bytes(raw)
    tmp = FILE.with_name(FILE.name + ".tmp"); tmp.write_bytes(nuovo); os.replace(tmp, FILE)
    if sha(FILE.read_bytes()) != DOPO[0]: raise SystemExit("STOP: riletto non coincide")
    print(f"[apply] scritto e riletto; backup logs\\{FILE.name}.bak_{ts}")

def verify():
    s = sha(FILE.read_bytes()); d = json.loads(FILE.read_text(encoding="utf-8"))
    ok = s == DOPO[0] and len(d) == 23 and d.get(CHIAVE) == MOTIVO
    print(f"verify {'OK' if ok else 'ANOMALIA'}: {s[:12]}..., {len(d)} voci"); sys.exit(0 if ok else 1)

def selftest():
    ok = 0
    base = {"a/b.md": "x «y» — z e'", "c/d.py": "w"}
    raw = serializza(base)
    n = trasforma(raw); d = json.loads(n.decode("utf-8"))
    assert list(d) == sorted(d) and d[CHIAVE] == MOTIVO and len(d) == 3; ok += 1
    try: trasforma(n); raise AssertionError
    except ValueError: pass
    ok += 1
    try: trasforma(json.dumps(base, indent=4).encode()); raise AssertionError
    except ValueError: pass
    ok += 1
    assert DOC_SHA[0] in MOTIVO and str(DOC_SHA[1]) in MOTIVO and "record 77" in MOTIVO; ok += 1
    print(f"selftest: {ok}/4 OK")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    {"selftest": selftest, "dry-run": lambda: dry_run(False), "apply": lambda: dry_run(True), "verify": verify}[ap.parse_args().cmd]()

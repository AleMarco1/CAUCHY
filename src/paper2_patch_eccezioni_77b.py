#!/usr/bin/env python3
"""
paper2_patch_eccezioni_77b.py  -  eccezioni del rilascio 23 -> 25: i due canovacci citati dal record 77

Il censimento dopo la 23a eccezione (logs/censimento_rilascio_77b.jsonl) ha dato 152 percorsi,
«escluso» 2 e citati_non_esclusi FAIL. La previsione era 150 e un percorso solo: contava il solo
campo `document` del record 77, mentre lo strumento legge i percorsi in tutti i campi di testo.
Il record 77 cita per intero altri due documenti di papers/:
  papers/paper2/canovaccio_paper1.md  voce D, il gemello del controllo di fedelta' delle schede
  papers/paper2/canovaccio_paper2.md  rules.git_rechecked_at_append (A/D in 73c8213 e 900335e)
e li ancora entrambi per byte in rules.documents_by_digest. L'autorita' e' il record 77, sotto la
portata del record 70 §i. Nessun record nuovo.

RIFIUTA se: l'ultimo record di logs/censimento_rilascio_77b.jsonl non porta ESATTAMENTE questi due
come esclusi senza eccezione; il file delle eccezioni non e' all'ancora della 77; il record 77 non
cita il percorso per intero o non ancora il nome col digest; il file su disco ha un altro sha; la
riserializzazione non ridà i byte; il risultato non ha lo sha atteso; l'inversa non torna.

Uso:
  python src\\paper2_patch_eccezioni_77b.py selftest
  python src\\paper2_patch_eccezioni_77b.py dry-run
  python src\\paper2_patch_eccezioni_77b.py apply
  python src\\paper2_patch_eccezioni_77b.py verify
"""
import argparse, hashlib, json, os, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "logs" / "eccezioni_rilascio.json"
LEDGER = ROOT / "src" / "paper2_v1_amendments.jsonl"
CENSIMENTO = ROOT / "logs" / "censimento_rilascio_77b.jsonl"
PRIMA = ("464e628b1dad546105712f388190ae54f335e34c3a04a7688ce0b8fa7f7deda9", 12153)
DOPO = ("abe6c63d5fe7c58a7472ba2e1b16710088e558b330be26d2ae428c84315522f3", 13369)

VOCI = {
 "papers/paper2/canovaccio_paper1.md": {
  "sha": ("1512e1da391066103ec15fef79055e094e4abe5d92ca53e38032e89d840d8137", 10438),
  "motivo": ("FUORI dal versionamento, decisione del record 70 §i, come tutto papers/. Citato dal record 77, "
             "voce D, come gemello del controllo di fedelta' delle schede delle chat: il download di "
             "canovaccio_paper1_rev3.md dalla chat 002 e' identico a questo file byte per byte. Ancorato per byte "
             "dallo stesso record in rules.documents_by_digest: sha256 "
             "1512e1da391066103ec15fef79055e094e4abe5d92ca53e38032e89d840d8137, 10438 byte al 23 set 2026. "
             "E' il canovaccio del Paper 1, rev3 del 24 luglio 2026: documento storico, chiuso.")},
 "papers/paper2/canovaccio_paper2.md": {
  "sha": ("7cbc0877ebcd4b1b0ac0ed61262dd204667a241f09715b0441d7dff30fbfa1db", 20518),
  "motivo": ("FUORI dal versionamento dal commit 900335e del 28 ago 2026, come tutto papers/; in git solo "
             "nella versione aggiunta da 73c8213. Citato per intero dal record 77 (rules.git_rechecked_at_append) "
             "e, senza cartella, dal record 50, che il censimento non vede come percorso (limite dichiarato). "
             "Ancorato per byte dal record 77 in rules.documents_by_digest: sha256 "
             "7cbc0877ebcd4b1b0ac0ed61262dd204667a241f09715b0441d7dff30fbfa1db, 20518 byte al 23 set 2026, "
             "rev. 25 agosto (sera). E' il file a cui si risolve la citazione del record 50, e tiene il suo nome: "
             "il canovaccio del 24 luglio si chiama canovaccio_paper2_rev1.md.")},
}

def sha(b): return hashlib.sha256(b).hexdigest()
def serializza(d): return (json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

def trasforma(raw: bytes) -> bytes:
    d = json.loads(raw.decode("utf-8"))
    if serializza(d) != raw: raise ValueError("la riserializzazione non ridà i byte originali: formato sconosciuto")
    for k, v in VOCI.items():
        if k in d: raise ValueError(f"la voce {k} esiste gia'")
        d[k] = v["motivo"]
    nuovo = serializza(d)
    d2 = json.loads(nuovo.decode("utf-8"))
    for k in VOCI: del d2[k]
    if serializza(d2) != raw: raise ValueError("togliere le voci non ridà il file originale")
    return nuovo

def precondizioni() -> list:
    err = []
    cens = [json.loads(l) for l in CENSIMENTO.read_text(encoding="utf-8").splitlines() if l.strip()][-1]
    esclusi = sorted(cens.get("per_stato", {}).get("escluso", []))
    if esclusi != sorted(VOCI):
        err.append(f"censimento 77b: esclusi senza eccezione {esclusi}, attesi {sorted(VOCI)}")
    righe = [l for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(righe) < 77: return err + ["ledger: meno di 77 record"]
    testo77 = righe[76]; r77 = json.loads(testo77)
    dig = r77.get("rules", {}).get("documents_by_digest", {})
    for k, v in VOCI.items():
        nome = k.split("/")[-1]
        if k not in testo77: err.append(f"record 77: non cita {k} per intero")
        if dig.get(nome) != v["sha"][0]: err.append(f"record 77: {nome} non ancorato con {v['sha'][0][:12]}...")
        raw = (ROOT / k).read_bytes() if (ROOT / k).exists() else b""
        if (sha(raw), len(raw)) != v["sha"]: err.append(f"disco: {k} {sha(raw)[:12]}..., {len(raw)} byte")
    return err

def dry_run(scrivi=False):
    raw = FILE.read_bytes(); s = sha(raw)
    if s == DOPO[0]: print("gia' all'ancora «dopo», non si tocca"); return
    if (s, len(raw)) != PRIMA: raise SystemExit(f"STOP: eccezioni {s[:12]}..., {len(raw)} byte, attese {PRIMA[0][:12]}..., {PRIMA[1]}")
    err = precondizioni()
    if err: print("STOP:"); [print("  -", e) for e in err]; raise SystemExit(1)
    try: nuovo = trasforma(raw)
    except ValueError as e: raise SystemExit(f"STOP: {e}")
    if sha(nuovo) != DOPO[0]: raise SystemExit(f"STOP: risultato {sha(nuovo)[:12]}..., atteso {DOPO[0][:12]}...")
    print(f"eccezioni: {s[:12]}... {len(raw)} B, 23 voci -> {sha(nuovo)[:12]}... {len(nuovo)} B, 25 voci; "
          f"i due esclusi del censimento sono esattamente questi; autorita' del record 77 verificata; inversa OK")
    if not scrivi: print("[dry-run] niente scritto."); return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    (FILE.parent / f"{FILE.name}.bak_{ts}").write_bytes(raw)
    tmp = FILE.with_name(FILE.name + ".tmp"); tmp.write_bytes(nuovo); os.replace(tmp, FILE)
    if sha(FILE.read_bytes()) != DOPO[0]: raise SystemExit("STOP: riletto non coincide")
    print(f"[apply] scritto e riletto; backup logs\\{FILE.name}.bak_{ts}")

def verify():
    s = sha(FILE.read_bytes()); d = json.loads(FILE.read_text(encoding="utf-8"))
    ok = s == DOPO[0] and len(d) == 25 and all(d.get(k) == v["motivo"] for k, v in VOCI.items())
    print(f"verify {'OK' if ok else 'ANOMALIA'}: {s[:12]}..., {len(d)} voci"); sys.exit(0 if ok else 1)

def selftest():
    ok = 0
    base = {"a/b.md": "x «y» — z e'", "papers/paper2/paper2_6_5_ritirati.md": "w"}
    n = trasforma(serializza(base)); d = json.loads(n.decode("utf-8"))
    assert list(d) == sorted(d) and len(d) == 4 and all(d[k] == v["motivo"] for k, v in VOCI.items()); ok += 1
    try: trasforma(n); raise AssertionError
    except ValueError: pass
    ok += 1
    assert all(v["sha"][0] in v["motivo"] and str(v["sha"][1]) in v["motivo"] and "record 77" in v["motivo"] for v in VOCI.values()); ok += 1
    print(f"selftest: {ok}/3 OK")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    {"selftest": selftest, "dry-run": lambda: dry_run(False), "apply": lambda: dry_run(True), "verify": verify}[ap.parse_args().cmd]()

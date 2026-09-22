#!/usr/bin/env python3
"""
paper2_patch_stato_15.py  —  14ª → 15ª revisione di paper2_stato.md
Porta il file in linea con la checklist rev. 3.32 e il ledger a 75 record.

Nove patch, dichiarate con old/new prima di toccare il file:
  P1  rev. 3.30 → 3.31 nella riga-storia della 13ª rev.    (riga 33)
  P2  Snapshot (17 set sera): riscrive la riga censimento    (riga 272)
  P3  14ª rev → 15ª revisione, blocco corrente              (riga 308)
  P4  eccezioni `8bd9607c…` / 10 064 → `2783ab80…` / 11 492 riga 309
  P5  censimento 4/5 → PULITO 5/5                           (riga 309)
  P6  6.0b–d aperte → 6.0 chiusa (a in F7, b record 75)     (riga 311)
  P7  origin/main/record nel testo corrente                  (riga 308)
  P8  record 74–75 nella tabella del ledger                  (riga 371)
  P9  strumenti: dodici nuove righe dopo paper2_patch_documenti_74

Ancora:
  sha256 atteso : 122e0306c27f17ee0d5d6a2c6592deccdb3486049d1039fcd0d15d9f61f1b46b
  byte attesi   : 97846

Uso:
  python src\\paper2_patch_stato_15.py selftest
  python src\\paper2_patch_stato_15.py dry-run
  python src\\paper2_patch_stato_15.py apply
  python src\\paper2_patch_stato_15.py verify
"""

import hashlib, sys
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
TARGET = ROOT / "papers" / "paper2" / "paper2_stato.md"

SHA_ATTESO   = "122e0306c27f17ee0d5d6a2c6592deccdb3486049d1039fcd0d15d9f61f1b46b"
BYTE_ATTESI  = 97846

# ── patch: (old, new) ────────────────────────────────────────────────────
PATCHES = [

# P1 — rev. 3.30 → 3.31 nella riga-storia della 13ª rev.
(
"previsione veniva fatta. Checklist rev. 3.30.",
"previsione veniva fatta. Checklist rev. 3.31."
),

# P2 — riga snapshot censimento a 74 record: 4 verdetti → 5
(
"| (17 set sera) censimento a 74 record, con 22 eccezioni | **quattro verdetti su cinque PASS**; `citati_committati` FAIL su 2, che il commit quattro chiude |",
"| (17 set sera) censimento a 74 record, con 22 eccezioni | **quattro verdetti su cinque PASS**; `citati_committati` FAIL su 2, chiuso col commit `50a8707` |\n| (18 set) censimento a 75 record, con 22 eccezioni | **PULITO 5/5**, 141 percorsi, 117 tracciati / 16 esclusi con eccezione / 6 assenti con eccezione / 2 pattern |"
),

# P3+P4+P5+P6+P7 — intero blocco della quattordicesima revisione
(
"**Al 17 settembre, sera, dopo il record 74 (quattordicesima revisione):** registro **74\nrecord**, CLEAN a 74/74 · checklist **rev. 3.30** · eccezioni a **22 voci**\n(`8bd9607c…`) · `REPRODUCIBILITY.md` **`09eb415f…`**, 325 righe · censimento **4/5 PASS**,\n`citati_committati` aperto fino al commit quattro · Fase 6: **chiuse 6.1, 6.3, 6.7, 6.8,\n6.9**; aperte 6.0b–d, 6.2, 6.4, 6.5, 6.6 · **nessuna decisione di protocollo aperta**.",
"**Al 17 settembre, sera, dopo il record 74 (quattordicesima revisione):** registro **74\nrecord**, CLEAN a 74/74 · checklist **rev. 3.31** · eccezioni a **22 voci**\n(`2783ab80…`, 11 492 byte) · `REPRODUCIBILITY.md` **`09eb415f…`**, 325 righe · censimento\n**PULITO 5/5**, 141 percorsi, `citati_committati` chiuso col commit `50a8707` · Fase 6:\n**chiuse 6.1, 6.3, 6.7, 6.8, 6.9**; 6.0a in Fase 7; **6.0b CHIUSA** (record 75: provenienza\n+3.90/+0.20 su `rev_n4n5_report.json`, documentazione P1-2 corretta, testo manoscritto\ninvariato); aperte 6.2 (2/6: v e vi), 6.4, 6.5, 6.6 · **nessuna decisione di protocollo\naperta** · `origin/main` a **`50a8707`**, **75 record**.\n\n**Al 18 settembre (quindicesima revisione):** questa revisione."
),

# P6b — eccezioni riga di corpo (riga ~932): stale ma di «testo corrente»
(
"**Le eccezioni sono 22** (`8bd9607c…`, 10 064 byte), record 74:",
"**Le eccezioni sono 22** (`2783ab80…`, 11 492 byte), record 74–75:"
),

# P8 — tabella ledger: aggiunge righe 74 (testo) e 75
(
"| **74** | **17 set 13:57** | **`6.2/quattro_eccezioni_dichiarate_e_la_copia_rimossa_era_byte_identica`** |",
"| **74** | **17 set 13:57** | **`6.2/quattro_eccezioni_dichiarate_e_la_copia_rimossa_era_byte_identica`** |\n| **75** | **18 set 09:xx** | **`6.0b / P1-2_documentazione`** |"
),

# P8b — nota sotto la tabella: aggiunge il 75
(
"> **73** apre il deposito e misura che non contiene il protocollo in nessuna versione, chiude\n> le tre possibilità del 72 con una quarta, e **supera il §iii del 70** aprendo `origin`\n> all'aggiornamento periodico (§8, Rilascio); il **74** dichiara quattro eccezioni — tre\n> con il digest di ciò che la citazione intendeva — e registra che la copia rimossa dal\n> commit `352e024` era **byte-identica** al sopravvissuto: un'etichetta rimossa, non un\n> dato.",
"> **73** apre il deposito e misura che non contiene il protocollo in nessuna versione, chiude\n> le tre possibilità del 72 con una quarta, e **supera il §iii del 70** aprendo `origin`\n> all'aggiornamento periodico (§8, Rilascio); il **74** dichiara quattro eccezioni — tre\n> con il digest di ciò che la citazione intendeva — e registra che la copia rimossa dal\n> commit `352e024` era **byte-identica** al sopravvissuto: un'etichetta rimossa, non un\n> dato; il **75** chiude la 6.0b (provenienza di +3.90/+0.20 verificata su file,\n> documentazione interna di P1-2 corretta, testo del manoscritto invariato)."
),

# P9 — tabella strumenti: aggiunge le otto righe della sessione 17-18 set
(
"| `paper2_patch_documenti_74.py` | record 74, decisione presa e censimento nei documenti | vedi selftest |",
"| `paper2_patch_documenti_74.py` | record 74, decisione presa e censimento nei documenti | vedi selftest |\n| `paper2_patch_eccezioni_ragioni.py` | aggiunge i campi `reason` alle 22 eccezioni | — |\n| `paper2_patch_eccezioni_budget.py` | porta il budget nelle eccezioni e viceversa | 41/41 |\n| `paper2_patch_budget_riga4.py` | corregge 1.242 → 1.241 (derivato dalla fonte, non dalla cella) | 32/32 |\n| `paper2_cerca_valore.py` rev. 2 | cerca valori numerici per finestra nei registri | 32/32 |\n| `paper2_patch_budget_colonna.py` | sdoppia la colonna percentuale: limite 3σ + Δ*D*/*D* | 22/22 |\n| `paper2_patch_budget_segno.py` | corregge il segno della riga 11 (+309 su N → −309 su *D*) | 27/27 |\n| `paper2_patch_budget_nota1b.py` | aggiunge nota 1b: base a *k*=1 su ramo unitario | 21/21 |\n| `paper2_patch_checklist_331.py` | checklist rev. 3.30 → 3.31 | 15/15 |\n| `paper2_valida_unione_p1_2.py` | valida unione step6+n1b per P1-2 (G1/G2/G3) | 3/3 |\n| `paper2_append_amend75.py` | record 75: 6.0b e documentazione P1-2 | 3/3 |"
),

]

# ── utilità ───────────────────────────────────────────────────────────────
def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load():
    return TARGET.read_text(encoding="utf-8")

# ── selftest ──────────────────────────────────────────────────────────────
def selftest():
    # ogni old_str è non vuoto e diverso dal corrispondente new_str
    for i, (old, new) in enumerate(PATCHES):
        assert old, f"P{i+1}: old vuoto"
        assert old != new, f"P{i+1}: old == new"
    # le old_str sono tutte distinte fra loro (nessuna si applica due volte)
    olds = [old for old, _ in PATCHES]
    assert len(olds) == len(set(olds)), "old_str duplicati"
    print(f"selftest: {len(PATCHES)} patch, {len(PATCHES)}/{len(PATCHES)} OK")

# ── dry-run ───────────────────────────────────────────────────────────────
def dry_run():
    sha = sha256_file(TARGET)
    if sha != SHA_ATTESO:
        print(f"STOP: sha atteso {SHA_ATTESO[:12]}…  trovato {sha[:12]}…")
        sys.exit(1)
    testo = load()
    errori = []
    for i, (old, _) in enumerate(PATCHES):
        n = testo.count(old)
        if n != 1:
            errori.append(f"  P{i+1}: occorrenze di old_str = {n} (attesa 1)")
    if errori:
        print("STOP dry-run — cancelli non soddisfatti:")
        print("\n".join(errori))
        sys.exit(1)
    print(f"dry-run OK: sha {sha[:12]}…  {len(testo)} car  {len(PATCHES)} patch applicabili")

# ── apply ─────────────────────────────────────────────────────────────────
def apply():
    dry_run()
    testo = load()
    for i, (old, new) in enumerate(PATCHES):
        testo = testo.replace(old, new, 1)
    TARGET.write_text(testo, encoding="utf-8")
    sha_nuovo = sha256_file(TARGET)
    byte_nuovi = TARGET.stat().st_size
    print(f"[apply] scritto  sha {sha_nuovo[:12]}…  {byte_nuovi} byte")

# ── verify ────────────────────────────────────────────────────────────────
def verify():
    testo = load()
    sha = sha256_file(TARGET)
    byte = TARGET.stat().st_size
    print(f"verify: sha {sha[:12]}…  {byte} byte")
    # controlla che nessun old_str sia ancora presente
    errori = []
    for i, (old, _) in enumerate(PATCHES):
        if old in testo:
            errori.append(f"  P{i+1}: old_str ancora presente")
    # controlla che i new_str siano tutti presenti
    for i, (_, new) in enumerate(PATCHES):
        # il new può contenere il new di una patch precedente: verifica solo il primo rigo
        first_line = new.splitlines()[0]
        if first_line not in testo:
            errori.append(f"  P{i+1}: prima riga di new_str non trovata: {first_line[:60]!r}")
    if errori:
        print("ANOMALIE:")
        print("\n".join(errori))
    else:
        print(f"verify OK: tutte le {len(PATCHES)} patch applicate, nessun old_str residuo")

# ── main ──────────────────────────────────────────────────────────────────
CMDS = {"selftest": selftest, "dry-run": dry_run, "apply": apply, "verify": verify}

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=list(CMDS))
    args = ap.parse_args()
    CMDS[args.cmd]()

#!/usr/bin/env python3
"""
paper2_patch_stato_16.py  —  paper2_stato.md, 15ª -> 16ª revisione: record 76, i due censimenti, le date vere della sessione

Sostituzioni ad ancora unica; EOL misurato e preservato; l'inversa deve restituire l'originale
prima di scrivere; seconda applicazione rifiutata; righe di tabella contate prima di scriverle.
Precondizioni: ledger al record 76, checklist 3.32, budget con la riga 5, modifiche_paper1 aggiornato.
Uso:
  python src\\paper2_patch_stato_16.py selftest | dry-run | apply | verify
"""
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'papers/paper2/paper2_stato.md'
SHA_ATTESO = 'ad728f1e83a99a64753e7d27f04cc28499a34e7e7aa9cf175220ea7912aef1e5'
BYTE_ATTESI = 100774
PRECONDIZIONI = {'src/paper2_v1_amendments.jsonl': ['a2dba4f7adbdfa9967de2c380f183ec7dd51a323682161068d0fe21f52808780', None], 'papers/paper2/checklist_paper2.md': ['4b2b830acd82ec938ebe50b8ef18ef3ffdaf27204eb57d2b0d872627f10f7fbb', 261080], 'papers/paper2/paper2_budget_5_1.md': ['a5d60b1537e777d4c54ac1f55caf1a60b00d676d4785877ba9ac62985b45eea2', 27802], 'papers/paper2/modifiche_paper1.md': ['77849455d1d4f9fa46e61a3e3bb850daf1f763f140e22d486b5ecb8e03f141c1', 82006]}
COLONNE_TABELLE = [3]
EDITS = json.loads(r'''[
 [
  "S1 intestazione",
  "### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **17 settembre 2026 (sera)**, quattordicesima revisione",
  "### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **22 settembre 2026**, sedicesima revisione"
 ],
 [
  "S2 blocco corrente",
  "**Al 18 settembre (quindicesima revisione):** questa revisione.",
  "**Al 22 settembre (quindicesima revisione, scritta quel giorno come «18 settembre»):**\nallineamento alla checklist 3.31 e al record 75.\n\n**Al 22 settembre, sera (sedicesima revisione):** registro **76 record** (`a2dba4f7…`),\n`freeze_verify` **CLEAN 76/76** con `DOCUMENTED_AMENDMENTS = 76` (`3337e2ab…`) · checklist\n**rev. 3.32** (`4b2b830a…`, 261 080 byte) · budget **`a5d60b15…`**, 27 802 byte, con le note\n10/11 e F e la correzione della 5/6 · `modifiche_paper1.md` **`77849455…`**, 82 006 byte,\n**sedici voci** · censimento dei **registri** alla 1.5, uscita **0** — 121 file, 78 075 righe,\nbaseline 121 coperti e 0 falliti · censimento del **rilascio** **PULITO**, cinque verdetti su\ncinque, **149 percorsi**: 123 tracciati puliti, 16 esclusi con eccezione, 6 assenti con\neccezione, 4 pattern · Fase 6: la **6.0 non ha più nulla in Fase 6** (b chiusa dal record 75, a\nin Fase 7) e la **6.2 è CHIUSA** (iii in Fase 7 col suo P1-12); restano **6.4, 6.5, 6.6** ·\n`origin/main` a **`a5fdabd`**, dieci commit nella sessione."
 ],
 [
  "S3 titolo del registro",
  "## 3. Il registro degli emendamenti — 74 record",
  "## 3. Il registro degli emendamenti — 76 record"
 ],
 [
  "S4 intervallo di Fase 6",
  "### Fase 6, record 61–74",
  "### Fase 6, record 61–76"
 ],
 [
  "S5 record 75 e 76",
  "| **75** | **18 set 09:xx** | **`6.0b / P1-2_documentazione`** |",
  "| **75** | **22 set 12:40** | **`6.0b / P1-2_documentazione`** |\n| **76** | **22 set 17:23** | **`6.2-vi`** |"
 ],
 [
  "S6 nota sotto il registro",
  "> dato; il **75** chiude la 6.0b (provenienza di +3.90/+0.20 verificata su file,\n> documentazione interna di P1-2 corretta, testo del manoscritto invariato).",
  "> dato; il **75** chiude la 6.0b (provenienza di +3.90/+0.20 verificata su file,\n> documentazione interna di P1-2 corretta, testo del manoscritto invariato); il **76** chiude la\n> 6.2-vi: corregge il record 50 §vii — `R5_er1` esiste, e il cancello a tolleranza zero sulla\n> giunzione è **fallito** su 7 mock di 400, con effetto sulla media 2 500 e 20 volte sotto la\n> mezza SEM — marca il superamento del `gate53`, porta il censimento dei registri alla 1.5 con\n> i 67 dichiarati, ancora i domini dei record 64 e 69 al commit `3e43e38`, e dà un registro\n> alla riga 5 del budget."
 ],
 [
  "S7 strumenti della sessione",
  "| `paper2_append_amend75.py` | record 75: 6.0b e documentazione P1-2 | 3/3 |",
  "| `paper2_append_amend75.py` | record 75: 6.0b e documentazione P1-2 | 3/3 |\n| `paper2_patch_stato_15.py` | questo documento, 14ª → 15ª revisione | 7/7 |\n| `paper2_patch_budget_doppione.py` | §4 punto 4 del budget chiuso come doppione (6.2-iv) | 9/9 |\n| `paper2_patch_budget_nota10_11.py` | nota 10/11: righe 10 e 11 dalle loro fonti (6.2-v) | 9/9 |\n| `paper2_patch_budget_notaF.py` | nota F: la colonna «fonte» riletta riga per riga (6.2-vi a) | 9/9 |\n| `paper2_inventario_6_2vi.py` | inventario di sola lettura di `results/**/*.json(l)` | 9/9 |\n| `paper2_patch_censimento_15.py` | censimento dei registri 1.4 → 1.5, con i 67 dichiarati | 6/6 |\n| `paper2_append_amend76.py` | record 76: ricalcola ogni suo numero dai file prima dell'append | 7/7 |\n| `paper2_patch_budget_riga5.py` | nota 5/6: la riga 5 ha un registro | 6/6 |\n| `paper2_patch_modifiche_p1_18set.py` | `modifiche_paper1.md`: P1-2, P1-9, P1-14, P1-15, P1-16 | 6/6 |\n| `paper2_patch_checklist_332.py` | checklist rev. 3.31 → 3.32 | 6/6 |"
 ],
 [
  "S8 rilascio, censimento del 22",
  "### Rilascio — stato al 17 settembre, sera",
  "### Rilascio — censimento del 22 settembre, sui 76 record\n\n**PULITO, cinque verdetti su cinque.** 149 percorsi distinti: **123 tracciati puliti**, 16\nesclusi con eccezione — i sei documenti di `papers/`, cinque log di lavoro, `remote_audit.json`\ne i due dei dati grezzi — 6 assenti con eccezione, e **4 pattern**: `src/*.py` e\n`results/paper2/ensemble_v1_manifest_*.jsonl`, che il record 76 dichiara **domini di ricerca**\ne ancora al commit `3e43e38` (albero `src` `c0c7f75e…`, 279 file `.py`, e i cinque blob dei\nmanifest), più `results/phase*_manifest*.json` e `results/phase*_review*.json`. Niente da\naggiungere, niente modificato, `metri_concordi` PASS. Le eccezioni restano **22**. Registro:\n`censimento_rilascio.jsonl`, log di lavoro, `7aebae63…`.\n\n### Rilascio — stato al 17 settembre, sera"
 ],
 [
  "S9 le date della sessione",
  "## 9. Strumenti, tutti con selftest",
  "## 8-ter. Le date della sessione, misurate\n\nLa sessione si apre con un `freeze_verify` del **18 settembre, 07:44Z**, e tutto ciò che è\nstato scritto è del **22 settembre**, fra le 12:26 e le 17:33. Nei documenti ho scritto «18\nsettembre» dappertutto: è la data d'inizio, non quella della scrittura.\n\n| commit | ora (22 set) | cosa |\n|---|---|---|\n| `01543c6` | 12:26 | validazione dell'unione di P1-2 |\n| `50a8707` | 12:40 | **record 75** |\n| `b459cf5` | 12:47 | questo documento, 15ª revisione |\n| `4055215` | 13:08 | budget, doppione del §4 (6.2-iv) |\n| `c5c0379` | 14:22 | budget, nota 10/11 (6.2-v) |\n| `b41bf75` | 14:54 | budget, nota F (6.2-vi a) |\n| `411bc6f` | 15:17 | inventario della 6.2-vi |\n| `431d3a2` | 17:18 | censimento dei registri 1.5 |\n| `4409375` | 17:24 | **record 76**, `DOCUMENTED_AMENDMENTS` 74 → 76 |\n| `a5fdabd` | 17:33 | passaggio documentale: budget riga 5, `modifiche_paper1.md`, checklist 3.32 |\n\n**Dove «18 settembre» va letto «22 settembre»:** note 10/11, F e correzione della 5/6 del\nbudget; checklist rev. 3.32; changelog e voci nuove di `modifiche_paper1.md`; la 15ª revisione\ndi questo documento; il testo del record 76; i motivi dei 67 dentro\n`paper2_censimento_registri.py` («non citato al 18 set»). Nessun numero dipende da una data,\nquindi non si riscrive nulla per questo: la correzione entra nel prossimo record del ledger che\nsi scrive per altre ragioni. L'`utc` del record 75, `2026-09-18T00:00:00`, è sbagliato anche\nnel giorno — l'append è delle 12:40 del 22 — e la voce J del record 76 lo rimanda al commit,\nche ora ha una data misurata. Dal record 76 l'`utc` lo legge l'orologio.\n\n---\n\n## 9. Strumenti, tutti con selftest"
 ]
]''')

def leggi(raw: bytes):
    t = raw.decode("utf-8"); n_crlf, n_lf = t.count("\r\n"), t.count("\n")
    if n_crlf == n_lf and n_crlf > 0: eol = "\r\n"
    elif n_crlf == 0 and "\r" not in t: eol = "\n"
    else: raise SystemExit(f"STOP: fine riga miste (CRLF {n_crlf}, LF {n_lf}); nessuna modifica")
    return t.replace(eol, "\n"), eol

def applica(testo: str) -> str:
    for nome, old, new in EDITS:
        n = testo.count(old)
        if n != 1: raise SystemExit(f"STOP: ancora «{nome}» trovata {n} volte (attesa 1); nessuna modifica")
        testo = testo.replace(old, new, 1)
    return testo

def inverti(testo: str) -> str:
    for nome, old, new in reversed(EDITS):
        if testo.count(new) != 1: raise SystemExit(f"STOP: inversa, «{nome}» non unica")
        testo = testo.replace(new, old, 1)
    return testo

def controlla(testo: str) -> list:
    err = []
    for nome, old, new in EDITS:
        if testo.count(new) != 1: err.append(f"«{nome}»: testo nuovo presente {testo.count(new)} volte")
        if old not in new and old in testo: err.append(f"«{nome}»: testo vecchio ancora presente")
    return err

def selftest():
    ok = 0
    fx = "\n\n<riempitivo>\n\n".join(old for _, old, _ in EDITS) + "\n"
    out = applica(fx); assert not controlla(out), controlla(out); ok += 1
    assert inverti(out) == fx; ok += 1
    try: applica(out); raise AssertionError("seconda applicazione accettata")
    except SystemExit: ok += 1
    try: applica(fx.replace(EDITS[-1][1], "")); raise AssertionError("ancora mancante accettata")
    except SystemExit: ok += 1
    olds = [o for _, o, _ in EDITS]; assert len(olds) == len(set(olds)); ok += 1
    for _, _, new in EDITS:
        for riga in new.split("\n"):
            if riga.startswith("|"): assert riga.count("|") - 1 in COLONNE_TABELLE, riga
    ok += 1
    print(f"selftest: {ok}/6 OK  ({len(EDITS)} interventi)")

def precondizioni():
    for rel, (s, byte) in PRECONDIZIONI.items():
        p = ROOT / rel; raw = p.read_bytes() if p.exists() else b""
        if hashlib.sha256(raw).hexdigest() != s or (byte is not None and len(raw) != byte):
            raise SystemExit(f"STOP: precondizione non soddisfatta, {rel} non e' {s[:12]}… {byte} byte")

def prepara(p):
    raw = p.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA_ATTESO or len(raw) != BYTE_ATTESI:
        raise SystemExit(f"STOP: ancora attesa {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte, trovata "
                         f"{hashlib.sha256(raw).hexdigest()[:12]}… {len(raw)} byte; nessuna modifica")
    testo, eol = leggi(raw); nuovo = applica(testo)
    if inverti(nuovo) != testo: raise SystemExit("STOP: l'inversa non restituisce l'originale")
    return raw, nuovo.replace("\n", eol).encode("utf-8")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--file", type=Path, default=TARGET); a = ap.parse_args()
    if a.cmd == "selftest": selftest()
    elif a.cmd == "verify":
        raw = a.file.read_bytes(); t, eol = leggi(raw); err = controlla(t)
        print(f"verify {'OK' if not err else 'ANOMALIA'}: sha {hashlib.sha256(raw).hexdigest()}  {len(raw)} byte")
        for e in err: print("  -", e)
        sys.exit(1 if err else 0)
    else:
        if a.file == TARGET: precondizioni()
        raw, out = prepara(a.file)
        if a.cmd == "dry-run":
            print(f"dry-run OK: ancora {SHA_ATTESO[:12]}… {BYTE_ATTESI} byte; {len(EDITS)} interventi, inversa esatta")
            print(f"  dopo: {len(out)} byte (Δ {len(out)-len(raw):+d}), sha {hashlib.sha256(out).hexdigest()[:12]}…; nessuna modifica scritta")
        else:
            a.file.write_bytes(out); print(f"[apply] scritto: sha {hashlib.sha256(out).hexdigest()}  {len(out)} byte")

#!/usr/bin/env python3
"""
paper2_patch_checklist_332.py  —  checklist rev. 3.31 -> 3.32: 6.0b e 6.2 chiuse in Fase 6, residuo della 6.1 chiuso, osservazione alla 3.6

Sostituzioni ad ancora unica; EOL misurato e preservato; l'inversa deve restituire l'originale
prima di scrivere; seconda applicazione rifiutata; righe di tabella contate prima di scriverle.
Precondizioni: il budget alla nota 5/6 corretta (a5d60b15…) e il ledger al record 76 (a2dba4f7…).
Uso:
  python src\\paper2_patch_checklist_332.py selftest | dry-run | apply | verify
"""
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'papers/paper2/checklist_paper2.md'
SHA_ATTESO = '0d29ba06fcdb0d3c3f10c8f6c4cbda5ce7b0c5f110d3bab79f874d8533d26a93'
BYTE_ATTESI = 257682
PRECONDIZIONI = {'papers/paper2/paper2_budget_5_1.md': ['a5d60b1537e777d4c54ac1f55caf1a60b00d676d4785877ba9ac62985b45eea2', 27802], 'src/paper2_v1_amendments.jsonl': ['a2dba4f7adbdfa9967de2c380f183ec7dd51a323682161068d0fe21f52808780', None]}
COLONNE_TABELLE = []
EDITS = json.loads(r'''[
 [
  "C1 intestazione rev. 3.32",
  "### rev. 3.31 — 17 settembre 2026 (notte) — record 74; **la 6.2 è a due sotto-voci su sei**, non chiusa: fatte 6.2-i (righe 4, 5 e 6 del budget) e 6.2-ii (base a *k*=1), rimandata 6.2-iii alla Fase 7 col suo P1-12, **già soddisfatta** 6.2-iv dalla voce 5.1 di questa checklist, aperte 6.2-v e 6.2-vi. La **6.0 chiude su c) e d)** e resta aperta su a) e b). Il budget è a `47503c98…`, 19 108 byte, con sei note nuove — 4b, C, 5/6, S, 6b, 1b — e **due colonne di percentuali** al posto di una, perché la R3 vieta il solo valore centrale sotto 3σ. Un derivato era sbagliato: **1.242 calcolato su −89.15, la cella, invece che su −89.147, la fonte**; e il **+309 della riga 11 vale −309 su *D***, mentre la colonna senza segno li leggeva concordi",
  "### rev. 3.32 — 18 settembre 2026 — record 75 e 76; **la 6.0 non ha più nulla in Fase 6** (la b chiusa dal record 75, la a in Fase 7) e **la 6.2 è CHIUSA in Fase 6** (i, ii, iv, v, vi; la iii in Fase 7 col suo P1-12). Il record 76 corregge il record 50 §vii — `R5_er1` esiste, e il cancello a tolleranza zero sulla giunzione è **fallito** su 7 mock di 400, con un effetto sulla media 2 500 e 20 volte sotto la mezza SEM — e marca il superamento del `gate53`. Il censimento dei registri è alla 1.5 ed esce `0`. La riga 5 del budget ha un registro, `n7_nfw_NGC.jsonl`, che la ricerca per valore del 17 set non poteva trovare: cercava tre valori sullo stesso record, e un registro per realizzazione non porta l'aggregato. Budget a `a5d60b15…`, ledger a 76 record, `freeze_verify` CLEAN 76/76."
 ],
 [
  "C2 6.0 b chiusa",
  "      **b) P1-2 è BLOCCATA sulla provenienza, e va sbloccata o dichiarata.** I valori pubblicati",
  "      **b) CHIUSA il 18 set, record 75: la provenienza era nel record 50 dall'8 settembre, e ora\n      è verificata su file.** `results/paper1/rev_n4n5_report.json`, `momenti.P10.agg.kurt`: mock\n      3.9030, DESI 0.2045, *n* = 200, produttore `paper1_rev_n4n5.py`. Le due cifre sono mock e\n      DESI della **stessa cella** di un report NGC, non due emisferi; i sostitutivi di P1-2 sono\n      l'unione validata di step6 e `n1b`. *(Il testo che segue è quello del 17 set, che la\n      chiamava BLOCCATA: nove giorni indietro rispetto a `modifiche_paper1.md`.)* I valori pubblicati"
 ],
 [
  "C3 6.2 chiusa",
  "- [ ] **6.2** Ogni numero del manoscritto tracciabile a un singolo run verificato.\n      **✦✦ Stato al 17 set (sera): DUE sotto-voci su sei.**",
  "- [x] **6.2** Ogni numero del manoscritto tracciabile a un singolo run verificato.\n      **✦✦✦ CHIUSA in Fase 6 il 18 set, record 76: cinque sotto-voci su sei, la iii in Fase 7\n      col suo P1-12.** Ogni riga del budget ha il suo registro, o la dichiarazione misurata che\n      non ce l'ha (note 4b, 5/6, 10/11, F). **✦✦ Stato al 17 set (sera): DUE sotto-voci su sei.**"
 ],
 [
  "C4 6.2-i NFW",
  "        **snapshot** (M26 §7 vi): due valori che vivono in un manoscritto e in nessun registro;",
  "        **snapshot** (M26 §7 vi): due valori che vivono in un manoscritto e in nessun registro —\n        **falso per NFW**, che ha il suo registro, `results/paper1/n7_nfw_NGC.jsonl` (18 set,\n        record 76 e nota 5/6 del budget); lo snapshot resta senza;"
 ],
 [
  "C5 6.2-iv chiusa",
  "      - **6.2-iv — GIÀ SODDISFATTA dalla voce 5.1**: togliere",
  "      - **6.2-iv — CHIUSA il 18 set** (doppione tolto: il punto 4 del §4 del budget è chiuso) —\n        **era già soddisfatta dalla voce 5.1**: togliere"
 ],
 [
  "C6 6.2-v chiusa",
  "      - **6.2-v** righe 10 e 11: la 10 ha per fonte due *voci* (4.3a, P1-8), la 11 un",
  "      - **6.2-v — CHIUSA il 18 set** (nota 10/11 del budget): 17.3 % da `ensemble_v2_SGC.jsonl`\n        (ramo `unit.`) e `desi_ladder_SGC.json`, *n* = 2000; 31.2 ± 0.08 da\n        `copertura_v1_SGC.json`, P25, *n* = 200; il +309 ha fonte bibliografica, M26 §5.3 e\n        Table 1, e nessun run registrato, assente su due metri. Il testo del 17 set — righe 10 e\n        11: la 10 ha per fonte due *voci* (4.3a, P1-8), la 11 un"
 ],
 [
  "C7 6.2-vi chiusa",
  "      - **6.2-vi** dal censimento e dai record: `gate53.jsonl` (superamento non marcato),",
  "      - **6.2-vi — CHIUSA il 18 set** (record 76; nota F del budget; censimento dei registri 1.5,\n        uscita `0`). Colonna «fonte» riletta riga per riga; nel `gate53` il record 2 supera il 1;\n        `erosion_restrict` si legge **per unione**, e il record 50 §vii che negava `R5_er1` è\n        corretto; i 67 dichiarati per nome, fuori scopo 6.1 perché chiusi; i domini dei record 64\n        e 69 ancorati a `3e43e38`; i `phase*_manifest` dichiarati; sette verdetti riferiti a\n        parole senza il file, ora nominati — `cammini_desi_{NGC,SGC}.json`,\n        `fase3_intersezione_verdetto.jsonl`, `p10_definizione_{NGC,SGC}.json`, `pareggi_NGC.json`,\n        `pareggi_NGC_mock1999.json`. Il testo del 17 set — dal censimento e dai record:\n        `gate53.jsonl` (superamento non marcato),"
 ],
 [
  "C8 residuo della 6.1 chiuso",
  "      **Residuo dichiarato:** **67 file `.jsonl`** sotto `results/` restano non",
  "      **✦✦ Residuo CHIUSO il 18 set (voce 6.2-vi, record 76):** i 67 sono dichiarati per nome\n      esatto, fuori scopo 6.1 perché chiusi, e lo strumento alla 1.5 esce `0` — 121 file, 78 075\n      righe, baseline 121 coperti e 0 falliti. **Non erano «Paper 1, smoke, item»**: almeno\n      diciotto sono registri del Paper 2 di Fase 3 e 5. Il testo del 15 set:\n      **Residuo dichiarato:** **67 file `.jsonl`** sotto `results/` restano non"
 ],
 [
  "C9 3.6 prova di segno a sei punti",
  "      rende credibili i due nuovi: 44.76 e 20.59 in NGC, 12.48 e 6.05 in SGC.",
  "      rende credibili i due nuovi: 44.76 e 20.59 in NGC, 12.48 e 6.05 in SGC.\n\n      **✦✦ Osservazione del 18 set (voce 6.2-vi, nota F del budget): la prova di segno della 3.3,\n      rifatta a sei punti.** La 3.3 chiamava «misurato» il pavimento di NGC perché la pendenza di\n      controllo del blocco A concordava in segno con la globale (+0.0335 e +0.0349 a *k*=0, 1). A\n      sei punti `slope_blockA_sign_check` di NGC vale **−0.0434 e −0.0078**, contro +0.0545 e\n      +0.0492: segno opposto anche a nord, come a sud (−0.1955, −0.0925). Nella cornice del\n      record 40 il pavimento è ciò che resta sul blocco A, nullo per teorema, e resta misurato in\n      entrambi gli emisferi (decisione A del 18 set); l'osservazione dice che cosa può contenere —\n      un termine (e) che non si trasferisce al blocco A — non se è misurato. Il campo non porta un\n      errore, e a *k*=1 il valore di NGC è prossimo a zero."
 ],
 [
  "C10 3.11 il registro del verdetto",
  "      24 (disegno) e 25 (verdetto). Due passate, lato dati, dodici punti per emisfero.",
  "      24 (disegno) e 25 (verdetto; registro `results/paper2/fase3_intersezione_verdetto.jsonl`,\n      nominato il 18 set). Due passate, lato dati, dodici punti per emisfero."
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

#!/usr/bin/env python3
"""
paper2_patch_modifiche_p1_18set.py  —  modifiche_paper1.md: P1-2 e P1-9 verificate su file, P1-14/15/16 nuove, verdetti col loro file (record 75-76)

Sostituzioni ad ancora unica; EOL misurato e preservato; l'inversa deve restituire l'originale
prima di scrivere; seconda applicazione rifiutata; righe di tabella contate prima di scriverle.

Uso:
  python src\\paper2_patch_modifiche_p1_18set.py selftest | dry-run | apply | verify
"""
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'papers/paper2/modifiche_paper1.md'
SHA_ATTESO = 'c6350fd4423edc4f2529e37f694d0c4a7e867bf00e5a8552a495297de17a9922'
BYTE_ATTESI = 74973
PRECONDIZIONI = {}
COLONNE_TABELLE = [3, 2]
EDITS = json.loads(r'''[
 [
  "MP1a riga P1-2",
  "| **P1-2** | Tabella 12, riga 1: etichetta «in-mask» e provenienza dei valori — **due punti nel testo** | **PRONTA** |",
  "| **P1-2** | Tabella 12, riga 1: etichetta «in-mask» e provenienza dei valori — **due punti nel testo** | **PRONTA** — provenienza verificata su file, sostitutivi da un'unione validata (record 75) |"
 ],
 [
  "MP1b riga P1-9",
  "| **P1-9** | Δ*N*_H1 della ripesatura: da 60 a 2000 realizzazioni, in **tre punti** | **PRONTA** |",
  "| **P1-9** | Δ*N*_H1 della ripesatura: da 60 a 2000 realizzazioni, in **tre punti** | **PRONTA** — le 60 coppie su file (record 76) |"
 ],
 [
  "MP1c tre voci nuove",
  "| **P1-5** | §6 / residuo beyond-two-point su v2 | **MISURATA**: 6.83σ → 6.86σ in NGC, differenza +0.03 ± 0.17 |",
  "| **P1-14** | §7.1: «47 per cent of the variance» — il 47 è della **deviazione standard** | **PRONTA** — una parola |\n| **P1-15** | Tabella 12, riga 5: 0.680 non si riproduce dal registro della popolazione a 1800 (0.681) | **BLOCCATA** — manca la provenienza di 0.680 |\n| **P1-16** | curve di step6 a R12, R15, R17 su 1905 e 1907 realizzazioni, il paper dice 2000 | **BLOCCATA** — manca quali prodotti le leggono |\n| **P1-5** | §6 / residuo beyond-two-point su v2 | **MISURATA**: 6.83σ → 6.86σ in NGC, differenza +0.03 ± 0.17 |"
 ],
 [
  "MP2 P1-2 verificata su file",
  "## P1-3 — Tabella 12: le prime due righe non sono due diagnostici",
  "### Verificato su file (18 settembre 2026, record 75)\n\n`results/paper1/rev_n4n5_report.json` (`d0e8284b…`, 5 902 byte), campo `momenti.P10.agg.kurt`:\n`mock_mean` 3.902956198001257, `desi` 0.20448735601308332, `z` −6.181412840388943, `n_mock` 200;\nproduttore `src/paper1_rev_n4n5.py` (`029e32fe…`), dichiarato dal campo `script` del report. I due\nnumeri pubblicati sono **mock e DESI della stessa cella** di un report NGC — come dice la\ndidascalia «(NGC)» della tabella — e non due emisferi. La provenienza passa da citata al record\n50 a verificata su un file.\n\n## P1-3 — Tabella 12: le prime due righe non sono due diagnostici"
 ],
 [
  "MP3 P1-2 i 2000",
  "+2.82 per i mock è un contrasto più netto di +0.20 contro +3.90.\n\nSotto tutte e quattro le restrizioni e in entrambi gli emisferi la curtosi dei\nmock resta maggiore di quella di DESI.",
  "+2.82 per i mock è un contrasto più netto di +0.20 contro +3.90.\n\nSotto tutte e quattro le restrizioni e in entrambi gli emisferi la curtosi dei\nmock resta maggiore di quella di DESI.\n\n**Da dove vengono i 2000** (18 settembre 2026, record 75). I quattro numeri qui sopra sono\nl'**unione** di due registri disgiunti con lo stesso stimatore: step6 a footprint pieno sulle\nrealizzazioni 0–199 (+2.7638 ± 0.4718, rango 0/200) e `n1b_spectra_NGC.jsonl` sulle 200–1999\n(+2.8235 ± 0.4562, tre sotto DESI). L'unione dà 2.817516 ± 0.458057, *z* −7.1077, rango 3/2000,\nsotto la mezza unità dell'ultima cifra quotata; validata da `src/paper2_valida_unione_p1_2.py`\ncon tre cancelli — disgiunzione, riproduzione di `n1b` su cinque campi, stimatore identico. I\n«1800 record congelati» sono la parte di `n1b`; il valore di DESI viene da step6. Il testo che\nentra nel manoscritto, **+2.82 ± 0.46**, non cambia."
 ],
 [
  "MP4 P1-9 le 60 coppie",
  "(−1.2 % contro −1.6 %). Aggiungerlo è una scelta, come per P1-5.",
  "(−1.2 % contro −1.6 %). Aggiungerlo è una scelta, come per P1-5.\n\n**Il registro delle 60 coppie** (18 settembre 2026, record 76). `results/paper1/n6_fkp_NGC.jsonl`\n(`78fae4e1…`): 60 record, `idx` 200–259, tutti `gate_ok`; Δ medio **−77.967**, SEM appaiata\n**8.001**, cioè il −78.0 ± 8.0 del §7.2 e di M26 R1. Le due estremità della relazione di questa\nvoce — 60 coppie e 2000 realizzazioni — stanno ora su file."
 ],
 [
  "MP5 P1-7 il registro del verdetto",
  "**Misurata il 10 settembre 2026** con `src/paper2_pareggi.py` (selftest 19/19).",
  "**Misurata il 10 settembre 2026** con `src/paper2_pareggi.py` (selftest 19/19); il verdetto sta in\n`results/paper2/pareggi_NGC.json` e `results/paper2/pareggi_NGC_mock1999.json` (file nominati il 18\nsettembre, record 76)."
 ],
 [
  "MP6 P1-8 il registro dell'esclusione",
  "`src/paper2_p10_definizione.py` (selftest 16/16):",
  "`src/paper2_p10_definizione.py` (selftest 16/16; registri `results/paper2/p10_definizione_{NGC,SGC}.json`,\nnominati il 18 settembre):"
 ],
 [
  "MP7 P1-14, P1-15, P1-16",
  "## P1-5 — il residuo beyond-two-point su v2: MISURATA",
  "## P1-14 — §7.1: il 47 per cento è della deviazione standard, non della varianza\n\n**Stato: PRONTA.** Nata il 18 settembre 2026 dalla voce 6.2-vi del Paper 2 (record 76).\n\n**Da:** «The pairing cancels 47 per cent of the variance, and the result is Δ*N*_H1 = −56.5 ± 23.5\n(2.4σ)».\n**A:** «The pairing reduces the standard deviation by 47 per cent, and the result is Δ*N*_H1 =\n−56.5 ± 23.5 (2.4σ)». In alternativa, sulla varianza: «The pairing removes 72 per cent of the\nvariance».\n\n### il numero\n\n`results/paper1/n7_nfw_NGC.jsonl` (`efe9ee50…`), 40 coppie, `idx` 200–239, tutti `gate_ok`:\nσ(uniforme) 279.0, σ(Δ) 148.8, quindi 1 − σ_Δ/σ_uniforme = **46.7 %**. Sulla varianza\nl'appaiamento ne toglie il 71.5 % rispetto a un braccio e l'86.2 % rispetto alla differenza non\nappaiata. Il 47 del testo è il rapporto delle deviazioni standard: il numero è giusto, il\nsostantivo no. Lo stesso file riproduce la misura, −56.475 ± 23.531: fino al 17 settembre il\nbudget del Paper 2 la dava senza registro.\n\n## P1-15 — Tabella 12, riga 5: 0.680 non si riproduce dal registro della sua popolazione\n\n**Stato: BLOCCATA** — manca la provenienza di 0.680, e del valore di DESI 0.575.\n\nLa riga 5 pubblica «small-scale power fraction *f*₁/₂ | 0.680 ± 0.007 | 0.575». Il registro della\npopolazione spettrale che il Paper 1 dichiara per la stessa analisi — 1800 mock — è\n`results/paper1/n1b_spectra_NGC.jsonl`, campo `f_half`: **0.681238**, sd 0.007188, SEM 0.000169,\n*n* = 1800. La dispersione si riproduce, la media no: 0.681 contro 0.680, a **7.3 SEM**.\n\nLa spiegazione che regge per P1-2 — un'unione con altre 200 realizzazioni — qui non regge: per\ndare 0.680 su 2000, le 200 mancanti dovrebbero stare fra 14.5 e 34.2 SEM sotto `n1b`, secondo\nl'arrotondamento. L'affermazione della riga non cambia: 0.68 contro 0.575 resta a quasi quindici\ndeviazioni standard. È **contabilità, non risultato**.\n\n**Uscite ammesse:** trovare il produttore di 0.680 e verificare 0.575, oppure riscrivere 0.681\ndichiarando *n* = 1800. Ritoccare perché «si avvicina» è escluso, come per P1-2.\n\n## P1-16 — curve di step6 a R12, R15, R17: 1905 e 1907 realizzazioni, non 2000\n\n**Stato: BLOCCATA** — manca l'elenco dei prodotti del Paper 1 che leggono quelle curve.\n\n`results/paper1/paper1_step6_NGC.json` porta `n_mock_curves` = 2000 a R5, R10, R20 e R30, ma\n**1905 a R12, 1907 a R15 e a R17**. La causa è misurata: step6 ha cercato i file di\n`curves_NGC_<R>/` alle 18:37 del 24 luglio, mentre `paper1_remap.py` stava ancora scrivendo quelle\ntre scale — le finestre del `glob` stanno in ordine R12, R15, R17 fra le 18:37:11 e le 18:38:14,\nil JSON è delle 18:42:00, e dopo il `glob` sono arrivati 95, 93 e 93 file, di cui 85, 83 e 84 dopo\nil JSON. Oggi le cartelle ne hanno 2000 ciascuna. `n_mock_curves` è onesto: si conta prima di\ncaricare.\n\nIl Paper 1 dichiara 2000 mock ovunque e usa R12, R15 e R17 nella Fig. 5, nella Tab. 10 e nella\nscansione di segno del §8.2 (il verdetto a *R* = 15 discordante fra emisferi). **Manca sapere se\nquei prodotti leggono le curve di step6.** Un indizio, da verificare e non da assumere: la Fig. 5\ncopre i due emisferi a sette scale, e di SGC esiste solo `curves_SGC_R5/`, mentre\n`per_mock_*_erosion_restrict.jsonl` letto per unione porta quelle scale. Se un prodotto legge le\ncurve di step6, va rifatto sulle cartelle complete — senza sovrascrivere\n`paper1_step6_NGC.json`, che `main()` riscrive — oppure va dichiarato il *n* per scala. E il\n`except Exception: continue` del caricamento delle curve salta un file illeggibile mentre\n`n_mock_curves` continua a contarlo: da correggere se step6 si rilancia.\n\n## P1-5 — il residuo beyond-two-point su v2: MISURATA"
 ],
 [
  "MP8a punto 2 superato",
  "2. Rieseguire `src/paper2_tab12_restrizione.py leggi` su entrambi gli emisferi: se nel\n   frattempo step6 è stato rilanciato con altre restrizioni, l'esito può cambiare e P1-2\n   potrebbe sbloccarsi da sola.",
  "2. P1-2: la provenienza è verificata su file e i sostitutivi sono un'unione validata (record\n   75). Prima di applicare, rieseguire `src/paper2_valida_unione_p1_2.py run` e controllare che\n   esca VALIDATA. *(Fino al 18 settembre questo punto chiedeva di rieseguire\n   `paper2_tab12_restrizione.py` sperando che P1-2 si sbloccasse da sola: era sbloccata dall'8.)*"
 ],
 [
  "MP8b punto 5 nuovo",
  "4. Controllare che nessuna delle voci sia stata applicata due volte: ogni voce applicata va\n   marcata qui con la data, e questo documento è l'unico indice.",
  "4. Controllare che nessuna delle voci sia stata applicata due volte: ogni voce applicata va\n   marcata qui con la data, e questo documento è l'unico indice.\n5. P1-15 e P1-16 sono BLOCCATE, e ciascuna dice che cosa manca: non si applicano finché non è\n   trovato."
 ],
 [
  "MP9 cambiamenti",
  "| 8 set 2026 | apertura. P1-1, P1-3, P1-4 PRONTE; P1-2 BLOCCATA sulla provenienza; P1-5 in attesa di 4.2a |",
  "| 8 set 2026 | apertura. P1-1, P1-3, P1-4 PRONTE; P1-2 BLOCCATA sulla provenienza; P1-5 in attesa di 4.2a |\n| 18 set 2026 | Voce 6.2 del Paper 2, record 75 e 76. **P1-2**: la provenienza di +3.90 / +0.20 è verificata su `rev_n4n5_report.json`; i sostitutivi (2.8175 ± 0.4581, 3/2000) sono l'unione validata di step6 (0–199) e `n1b` (200–1999), il testo +2.82 ± 0.46 non cambia. **P1-9**: il registro delle 60 coppie è su file. Nascono **P1-14** (§7.1, il 47 per cento è della deviazione standard: PRONTA), **P1-15** (Tab. 12 riga 5, 0.680 contro 0.681: BLOCCATA) e **P1-16** (curve di step6 a R12–R17 su 1905–1907 realizzazioni: BLOCCATA). Nominati i registri dei verdetti di P1-7 e P1-8. Il punto 2 di «Da rifare» era superato dall'8 settembre |"
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_documenti_69_72.py — porta nei due documenti i record 69–72 del ledger, le tre
decisioni del 17 settembre 2026 e l'esito della verifica del deposito Zenodo.

Documenti toccati (entrambi o nessuno):
  papers/paper2/checklist_paper2.md   rev. 3.27 -> rev. 3.28
  papers/paper2/paper2_stato.md       undicesima -> dodicesima revisione

Cancelli, nell'ordine in cui il patcher li applica:
  1. sha256 e dimensione dei due documenti uguali alle ancore della consegna del 16 set
     (rev. 3.27 = db5d2308..., 237 389 byte; undicesima revisione = edc33a00..., 79 465 byte);
  2. ledger a 72 righe, tutte JSON, e i record 69–72 con i campi `utc` e `item`;
  3. dettagli letterali dei record 69–72 presenti nel record serializzato (`.gitattributes`,
     `v3.1-paper2`, i tre nomi del 71, i due digest del 72);
  4. ogni ancora di testo presente ESATTAMENTE una volta nel documento, e il testo nuovo non
     ancora presente (così una seconda esecuzione rifiuta due volte: allo sha e all'ancora);
  5. i due testi nuovi sono calcolati per intero PRIMA di scrivere alcunché; la scrittura è
     su file temporaneo + `os.replace`, e i byte scritti vengono riletti e confrontati.

Le righe della tabella §3 dello stato sono RESE dai campi `utc` e `item` del ledger, non
scritte a mano: per questo il patcher legge il ledger anche in dry-run.

Uso (dalla radice del repository, `D:\\projects\\cauchy`):
  python src\\paper2_patch_documenti_69_72.py selftest
  python src\\paper2_patch_documenti_69_72.py dry-run
  python src\\paper2_patch_documenti_69_72.py apply
  python src\\paper2_patch_documenti_69_72.py verify

I fine riga dei due documenti sono LF e restano LF: i file sono letti e scritti in binario.
"""

import argparse
import difflib
import hashlib
import json
import os
import sys
import tempfile

CHECKLIST = os.path.join("papers", "paper2", "checklist_paper2.md")
STATO = os.path.join("papers", "paper2", "paper2_stato.md")
LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")

ANCHOR_CHECKLIST = ("db5d2308d289ad8f01b9d9b886f833fa3664a750b3aa89c4a9b0460adb532276", 237389)
ANCHOR_STATO = ("edc33a0073b2ce36d7692faa1c4997e96bfe1b69c9c19a26040d48465e34e4bb", 79465)

LEDGER_RECORDS = 72
RECORDS_TO_RENDER = (69, 70, 71, 72)

# Dettagli letterali che il record serializzato DEVE contenere. Solo quelli certi: un controllo
# che fallisce su una congettura di grafia non e' un controllo, e' rumore.
LITERAL_DETAILS = {
    69: [".gitattributes"],
    70: ["v3.1-paper2"],
    71: ["paper2_passata_1punto.py", "paper2_item13_rev2.py", "352e024",
         "phase8_test2_permock_hodfit.csv"],
    72: ["607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86", "05cd32b2"],
}

MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]

# Marche che devono comparire nei documenti DOPO la patch (per `verify`).
MARKER_CHECKLIST = "### rev. 3.28 — 17 settembre 2026 — record 72"
MARKER_STATO = "aggiornato **17 settembre 2026**, dodicesima revisione"


class PatchError(Exception):
    pass


# --------------------------------------------------------------------------------------------
# utilita'
# --------------------------------------------------------------------------------------------

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def check_anchor(path, data, anchor, label):
    sha, size = anchor
    got = (sha256_bytes(data), len(data))
    if got != (sha, size):
        raise PatchError(
            f"{label}: ancora NON corrisponde.\n"
            f"  atteso  {sha}  {size} byte\n"
            f"  trovato {got[0]}  {got[1]} byte\n"
            f"  ({path}) — o il file non e' la rev. attesa, o la patch e' gia' applicata."
        )


def render_utc(utc):
    """'2026-09-16T14:41:03Z' -> '16 set 14:41' (come le righe gia' presenti nella tabella §3)."""
    if not isinstance(utc, str) or len(utc) < 16 or utc[4] != "-" or utc[7] != "-" or utc[10] != "T":
        raise PatchError(f"campo utc non nel formato atteso: {utc!r}")
    mese = int(utc[5:7])
    giorno = int(utc[8:10])
    if not 1 <= mese <= 12:
        raise PatchError(f"mese fuori intervallo nel campo utc: {utc!r}")
    return f"{giorno} {MESI[mese - 1]} {utc[11:16]}"


def read_ledger(path):
    """Legge il ledger in binario, tollera CRLF e LF per riga, esige 72 righe JSON."""
    raw = read_bytes(path)
    lines = raw.split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]
    if len(lines) != LEDGER_RECORDS:
        raise PatchError(f"ledger: attese {LEDGER_RECORDS} righe, trovate {len(lines)} ({path})")
    records = []
    for i, ln in enumerate(lines, start=1):
        s = ln[:-1] if ln.endswith(b"\r") else ln
        try:
            rec = json.loads(s.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            raise PatchError(f"ledger: riga {i} non e' JSON valido: {e}")
        if not isinstance(rec, dict):
            raise PatchError(f"ledger: riga {i} non e' un oggetto JSON")
        records.append(rec)
    return records


def check_ledger_records(records):
    """Controlla i campi e i dettagli letterali dei record 69–72; ritorna {n: (utc_reso, item)}."""
    out = {}
    for n in RECORDS_TO_RENDER:
        rec = records[n - 1]
        for k in ("utc", "item"):
            if k not in rec or not isinstance(rec[k], str) or not rec[k]:
                raise PatchError(f"record {n}: campo `{k}` assente o vuoto")
        serial = json.dumps(rec, ensure_ascii=False)
        missing = [d for d in LITERAL_DETAILS[n] if d not in serial]
        if missing:
            raise PatchError(f"record {n}: dettagli letterali assenti dal record serializzato: {missing}")
        if "|" in rec["item"]:
            raise PatchError(f"record {n}: `item` contiene '|' e romperebbe la tabella: {rec['item']!r}")
        out[n] = (render_utc(rec["utc"]), rec["item"])
    return out


def apply_edits(text, edits, label):
    """Ogni `old` deve comparire esattamente una volta, e il testo `new` non deve essere gia'
    presente (cosi' una seconda esecuzione e' rifiutata anche se una modifica e' un'aggiunta in
    coda all'ancora, che quindi sopravvive)."""
    for i, (old, new) in enumerate(edits, start=1):
        c = text.count(old)
        if c != 1:
            head = old.splitlines()[0][:90] if old else ""
            raise PatchError(f"{label}: ancora {i} trovata {c} volte (attesa 1): {head!r}")
        if new and new in text:
            raise PatchError(f"{label}: il testo nuovo della modifica {i} e' gia' presente — patch gia' applicata?")
        text = text.replace(old, new, 1)
    return text


def write_atomic(path, data):
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".patch_", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    back = read_bytes(path)
    if back != data:
        raise PatchError(f"{path}: i byte riletti differiscono da quelli scritti")


def unified(old_text, new_text, name):
    return "".join(difflib.unified_diff(
        old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
        fromfile=name + " (prima)", tofile=name + " (dopo)", n=1))


# --------------------------------------------------------------------------------------------
# le modifiche alla CHECKLIST (rev. 3.27 -> 3.28) — nessuna dipende dal ledger
# --------------------------------------------------------------------------------------------

def edits_checklist():
    E = []

    # 1. intestazione di revisione (riga 2, intera)
    E.append((
        "### rev. 3.27 — 15 settembre 2026 — record 68; **la 6.1 è un censimento con eccezioni "
        "dichiarate, non un requisito di conformità**: tre proprietà misurate su 121 file e 78 067 "
        "righe (53 file e 67 915 in scopo), l'append-only storico contro una linea di base, "
        "`resumable` ridefinita come **dichiarazione del runner** su 53 righe, un solo FAIL già "
        "dichiarato dal **record 47** — che questo record **emenda** — e 67 file non classificati "
        "consegnati al 6.2\n",
        "### rev. 3.28 — 17 settembre 2026 — record 72; **i quattro record del 16 settembre portati "
        "nei documenti**: l'ordine delle regole di `.gitattributes` (69), la portata del rilascio e il "
        "tag `v3.1-paper2` (70), quattro citazioni irrisolte con quattro cause (71), il protocollo "
        "v1.1 ancorato per byte (72) — e **il deposito Zenodo non contiene il protocollo**, misurato "
        "il 17; tre decisioni del 17: GitHub aggiornato periodicamente, deposito Zenodo e tredici "
        "voci del Paper 1 all'**ultimo punto della Fase 7**; 6.9 spuntata\n",
    ))

    # 2. base documentale: il protocollo NON e' depositato
    E.append((
        "`paper2_prereg_v1.md` v1.1 (depositata,\n"
        "> version DOI 10.5281/zenodo.22148444), `CONSEGNA_FASE3_20260828.md`.\n",
        "`paper2_prereg_v1.md` v1.1 (**non\n"
        "> depositata**: il deposito 10.5281/zenodo.22148444 — `v3.0-paper2`, 28 ago — non contiene il\n"
        "> protocollo in nessuna versione; la v1.1 è ancorata per byte dal record 72, `607708e8…`,\n"
        "> 25 319 byte; la v1.0 è pubblica nel commit `73c8213` — voce 6.3), `CONSEGNA_FASE3_20260828.md`.\n",
    ))

    # 3. 6.0a: quando si applicano le tredici voci
    E.append((
        "      **a) Le tredici voci del Paper 1 si applicano qui, e IN COPPIA.** Il manoscritto non è\n"
        "      editabile prima: le correzioni vanno nella versione rivista.",
        "      **a) Le tredici voci del Paper 1 si applicano IN COPPIA, all'ULTIMO PUNTO DELLA FASE 7 —\n"
        "      subito prima della sottomissione del Paper 2** *(decisione del 17 set; era «qui»: la voce\n"
        "      resta in 6.0 come indice e si spunta quando è fatta)*. Il manoscritto non è\n"
        "      editabile prima: le correzioni vanno nella versione rivista.",
    ))

    # 4. 6.2: lista di lavoro, record 71, quantita' da dichiarare
    E.append((
        "      valori con la colonna «fonte» già compilata: è il punto di partenza, non un doppione.\n"
        "- [ ] **6.3** Tag `v2.1-paper2`; DOI Zenodo aggiornato.\n",
        "      valori con la colonna «fonte» già compilata: è il punto di partenza, non un doppione.\n"
        "      **✦✦ Cominciata il 16 set — la lista di lavoro, dal §4 del budget:**\n"
        "      - **6.2-i** righe 4, 5, 6 del budget. La **4 è riletta**: la fonte è\n"
        "        `results/paper2/d2_v2_{NGC,SGC}.json`, campi `dN_medio` e `dN_sem`, non «il registro\n"
        "        di `paper2_d2_v2.py`» — era nominata col produttore. Restano **NFW** (Paper 1 §7.1) e\n"
        "        **snapshot** (M26 §7 vi): due valori che vivono in un manoscritto e in nessun registro;\n"
        "      - **6.2-ii** nota 1: ⟨*N*⟩_mock a *k*=1 dal ramo unitario, e le % della riga 1\n"
        "        ricalcolate su quella base (con le basi a *k*=0 verrebbero 1.369 / 2.537 %, **da non\n"
        "        usare**);\n"
        "      - **6.2-iii** riga 9 riletta dal ricalcolo P1-12, col §8.2 del Paper 1 corretto insieme;\n"
        "      - **6.2-iv** voce 5.1: togliere «denominatori conservativi ovunque», banda da 17–29 a\n"
        "        17.3–31.2 %;\n"
        "      - **6.2-v** righe 10 e 11: la 10 ha per fonte due *voci* (4.3a, P1-8), la 11 un\n"
        "        manoscritto (M26 §5.3) e porta il **+309** che il budget stesso dà come caso di base\n"
        "        sbagliata; il 6.0(d) non la include;\n"
        "      - **6.2-vi** dal censimento e dai record: `gate53.jsonl` (superamento non marcato),\n"
        "        `per_mock_*_erosion_restrict` (unione contro last-wins), i verdetti dentro i `.json`\n"
        "        di report, i 67 `.jsonl` non classificati, i `phase*_manifest.json` (assenti dal\n"
        "        ledger), `src/*.py` citato come pattern dal record 64.\n"
        "      Le fonti del budget sono una popolazione diversa da quella del censimento del rilascio\n"
        "      (`fase3_budget.jsonl` e `n8b_masks_128_B.jsonl` sono citati **senza cartella**, e il\n"
        "      rilevatore di percorsi chiede un separatore): serve un censimento suo, sulla colonna\n"
        "      «fonte», e non è un doppione.\n"
        "      **✦✦ Record 71 — quattro citazioni irrisolte, quattro cause, da portare ovunque siano\n"
        "      citate.** `item13rev2.py` è un errore di trascrizione: lo strumento è\n"
        "      `paper2_item13_rev2.py` e produce `item13rev2_<REG>.jsonl` senza underscore.\n"
        "      `paper2_letture_1punto.py` **non è mai esistito**, in nessun commit di nessun ramo: il\n"
        "      «31/31» accostatogli era di `paper2_boxcox_v2.py`, e il lavoro lo fa\n"
        "      `paper2_passata_1punto.py` (43/43). `phase8_test2_permock.csv` è **rimosso per causa**\n"
        "      dal commit `352e024`; sopravvive `phase8_test2_permock_hodfit.csv`. Il percorso Quijote\n"
        "      del record 43 è dichiarato assente dal 43 stesso. In questa checklist nessuna delle due\n"
        "      grafie sbagliate compariva: stavano in `paper2_stato.md` §9 (riga tolta il 17 set, con\n"
        "      nota) e in `modifiche_paper1.md` (due citazioni, righe 245 e 383 al 17 set: 6.0a).\n"
        "      Finché il censimento le segnala, **va bene così**: un'eccezione le nasconderebbe.\n"
        "      **✦✦ Da dichiarare nel manoscritto (16 set):** in `d2_v2_{NGC,SGC}.json` coesistono\n"
        "      `dN_su_N_medio` (media dei rapporti, 0.2513 %) e il rapporto delle medie (0.2516 %) —\n"
        "      quale delle due si cita va detto; e «1.242 % di *D*» viene da 1.2415, su un confine di\n"
        "      arrotondamento, senza convenzione dichiarata.\n"
        "- [ ] **✦✦ 6.3 — Tag `v3.1-paper2` (record 70 §iv; non `v2.1-paper2`, che si ordinerebbe prima\n"
        "      di `v3.0-paper2` del 28 agosto); DOI Zenodo alla sottomissione.** *(era «Tag\n"
        "      `v2.1-paper2`; DOI Zenodo aggiornato»)*.\n"
        "      **FATTO:** le regole di fine riga (record 69: in `.gitattributes` vince l'ultima regola\n"
        "      che combacia — regole di cartella in coda, `*.py` e `*.md` a `text eol=lf`, tre file\n"
        "      del tier `records` riletti nell'indice), i commit `3e43e38` e `bfcb4a5`, il tag annotato\n"
        "      `v3.1-paper2` su `bfcb4a5`, la portata del rilascio (record 70: `papers/` e `logs/`\n"
        "      fuori, tutto `src/` dentro, il kref riammesso), le 14 eccezioni del censimento\n"
        "      installate (`e8d34dbc…`, 5 159 byte).\n"
        "      **RESTA:** (i) il **commit tre** — ledger con i record 71 e 72,\n"
        "      `DOCUMENTED_AMENDMENTS = 72`, `paper2_append_amend71/72.py` — e lo spostamento del tag\n"
        "      su di esso, lecito perché mai spinto; il file non tracciato `src/eccezioni_rilascio.json`\n"
        "      va confrontato con `logs/eccezioni_rilascio.json` e deciso prima: `logs/` è fuori dal\n"
        "      rilascio, `src/` dentro; (ii) `REPRODUCIBILITY.md` corretto **prima** del commit tre\n"
        "      (6.7), altrimenti il tag congela le due frasi false;\n"
        "      (iii) **un record 73.** Misurato il 17 set dal servizio Zenodo: il deposito\n"
        "      `10.5281/zenodo.22148444` (`v3.0-paper2`, creato il 28 ago alle 18:07:52Z, sei file, sha\n"
        "      dei quattro zip conformi al `MANIFEST.sha256`) **non contiene `paper2_prereg_v1.md`** in\n"
        "      nessuno zip, e nessuna delle quattro versioni del concept DOI (2, 3, 6 lug, 28 ago) lo\n"
        "      porta. I 59 record che citano «v1.1 — version DOI 22148444» citano un contenitore senza\n"
        "      il file. La v1.0 è pubblica nel commit `73c8213` (27 ago 13:38, `05cd32b2…`, 21 430\n"
        "      byte); la v1.1 (`607708e8…`, 25 319 byte, scritta alle 20:13:04 del 28 ago, cinque minuti\n"
        "      dopo il deposito) esiste in una copia sola. Fra le due: 8 righe tolte e 61 aggiunte,\n"
        "      tutte nel preambolo, in §2.1, in §9 e tre in §0 — **le sezioni delle regole sono\n"
        "      identiche riga per riga**. Le tre possibilità del record 72 sono superate da questa\n"
        "      quarta; (iv) **deposito Zenodo alla sottomissione, ultimo punto della Fase 7**\n"
        "      (decisione del 17 set), con la v1.1 dentro; (v) **GitHub aggiornato periodicamente**\n"
        "      (17 set): supera il differimento del record 70 e va registrato prima del primo push.\n",
    ))

    # 5. 6.7: le due affermazioni false del §5 di REPRODUCIBILITY.md
    E.append((
        "      non nella radice di `results/` perché lì cadrebbe **dentro** le regole del tier `features` e\n"
        "      il freeze lo segnalerebbe come file extra — due FAIL, visti e rientrati col trasloco.\n",
        "      non nella radice di `results/` perché lì cadrebbe **dentro** le regole del tier `features` e\n"
        "      il freeze lo segnalerebbe come file extra — due FAIL, visti e rientrati col trasloco.\n"
        "      **✦✦ 16–17 set: il file ESISTE** (176 righe, commit `c13ccc3` dell'8 set): da estendere,\n"
        "      non da scrivere. **Il §5 porta due affermazioni false, da correggere PRIMA del commit\n"
        "      tre:** «49 CRLF e 6 LF» per il ledger, dove il conteggio cambia a ogni append (66 e 6 a\n"
        "      72 record) — va scritto l'invariante: sei record a LF, l'8, 9, 10, 11, 13 e 14 (record\n"
        "      47), tutti gli altri a CRLF; e «una copia byte-identica: non esiste», dove il commit\n"
        "      `352e024` dichiara esattamente quella copia rimossa (record 71) — va riscritta come\n"
        "      **rimozione registrata**, non come negazione. Da aggiungere anche l'asimmetria\n"
        "      cache/kref (record 61 contro record 5 e manifest `features`) e il pattern di\n"
        "      `paper1_remap`.\n",
    ))

    # 6. 6.9: casella spuntata, blocco storico marcato
    E.append((
        "- [ ] **✦✦ 6.9 — Censimento dei verdetti emessi FUORI dal ledger** *(aperto il 13 set, record 64;\n",
        "- [x] **✦✦ 6.9 — Censimento dei verdetti emessi FUORI dal ledger. CHIUSA nel ledger dai record\n"
        "      65–67; casella spuntata il 17 set** *(aperto il 13 set, record 64;\n",
    ))
    E.append((
        "      **RESTA APERTO.** Tre candidati senza record — le due soglie di `paper2_gate53.py`\n",
        "      **RESTAVA APERTO prima dei record 66–67** *(blocco lasciato come storia: la causa è\n"
        "      corretta sopra e il ledger dà la voce chiusa)*. Tre candidati senza record — le due\n"
        "      soglie di `paper2_gate53.py`\n",
    ))

    # 7. Fase 7: gli ultimi due punti, dichiarati in testa
    E.append((
        "### Struttura\n"
        "\n"
        "1. Introduzione: la domanda della funzione di risposta; le limitazioni (ix) e (ii).\n",
        "**✦✦ Ultimi due punti della Fase 7 (decisione del 17 set), subito prima della sottomissione:**\n"
        "(i) le tredici voci del Paper 1, in coppia (6.0a); (ii) il deposito Zenodo con la v1.1 del\n"
        "protocollo e il tag della sottomissione (6.3). GitHub, invece, si aggiorna periodicamente.\n"
        "\n"
        "### Struttura\n"
        "\n"
        "1. Introduzione: la domanda della funzione di risposta; le limitazioni (ix) e (ii).\n",
    ))
    return E


# --------------------------------------------------------------------------------------------
# le modifiche allo STATO (undicesima -> dodicesima revisione) — le righe §3 vengono dal ledger
# --------------------------------------------------------------------------------------------

def edits_stato(rendered):
    """`rendered` = {n: (utc_reso, item)} per n in 69..72, dal ledger."""
    E = []

    # 1. intestazione
    E.append((
        "aggiornato **15 settembre 2026**, undicesima revisione\n",
        "aggiornato **17 settembre 2026**, dodicesima revisione\n",
    ))

    # 2. blocco «cosa e' cambiato», in testa
    E.append((
        "> **Cosa è cambiato nell'undicesima revisione (15 settembre) — LA 6.1 È UN CENSIMENTO CON\n",
        "> **Cosa è cambiato nella dodicesima revisione (17 settembre) — I QUATTRO RECORD DEL 16 SONO NEI\n"
        "> DOCUMENTI, E IL DEPOSITO ZENODO NON CONTIENE IL PROTOCOLLO.** Record **69**: in\n"
        "> `.gitattributes` vince l'ultima regola che combacia; le regole di cartella stavano in testa,\n"
        "> quindi tre file del tier congelato `records` erano `text`, riproducibili solo su Windows con\n"
        "> `core.autocrlf=true` — regole di cartella in coda, `*.py` e `*.md` a `text eol=lf`, indice\n"
        "> riletto (la cache di stat non si invalida da sé). Record **70**: `papers/` e `logs/` fuori dal\n"
        "> rilascio, tutto `src/` dentro, il kref riammesso, tag `v3.1-paper2` e non `v2.1-paper2`.\n"
        "> Record **71**: quattro citazioni irrisolte del censimento, quattro cause diverse —\n"
        "> trascrizione (`paper2_item13_rev2.py`), un file mai esistito (`paper2_letture_1punto.py`, il\n"
        "> cui «31/31» era di `paper2_boxcox_v2.py`), una rimozione per causa (`352e024`), un'assenza\n"
        "> già dichiarata (record 43). Record **72**: il protocollo era citato come stringa da 59 record\n"
        "> e la v1.1 non è mai stata committata — `papers/` è uscito dal versionamento alle 18:23:40 del\n"
        "> 28 agosto e la v1.1 è delle 20:13:04 — quindi è ancorata per byte, `607708e8…`, 25 319.\n"
        "> **Misurato il 17 dal servizio Zenodo:** `10.5281/zenodo.22148444` (`v3.0-paper2`, creato il\n"
        "> 28 ago alle 18:07:52Z, sei file, sha dei quattro zip conformi al `MANIFEST.sha256`) **non\n"
        "> contiene `paper2_prereg_v1.md`** in nessuno zip, e nessuna delle quattro versioni del concept\n"
        "> DOI (2, 3, 6 luglio, 28 agosto) lo porta: il DOI non identifica nessuna versione del\n"
        "> protocollo, e il deposito precede la v1.1 di cinque minuti. La v1.0 è pubblica nel commit\n"
        "> `73c8213` (`05cd32b2…`, 21 430 byte); fra v1.0 e v1.1 8 righe tolte e 61 aggiunte, tutte nel\n"
        "> preambolo, in §2.1, in §9 e tre in §0 — **le sezioni delle regole sono identiche riga per\n"
        "> riga**. Serve un record 73. **Tre decisioni del 17:** GitHub aggiornato periodicamente\n"
        "> (supera il differimento del record 70, da registrare prima del primo push); Zenodo solo alla\n"
        "> sottomissione, ultimo punto della Fase 7; le tredici voci del Paper 1 idem, ultimo punto\n"
        "> della Fase 7. Le 14 eccezioni del censimento sono installate (`e8d34dbc…`). `freeze_verify`\n"
        "> CLEAN alle 06:02:52Z del 17, 72/72; tag `v3.1-paper2` su `bfcb4a5` senza i record 71–72:\n"
        "> commit tre e spostamento del tag ancora da fare. Checklist rev. 3.28.\n"
        "\n"
        "> **Cosa è cambiato nell'undicesima revisione (15 settembre) — LA 6.1 È UN CENSIMENTO CON\n",
    ))

    # 3. §0: tre verifiche del 17 set, in coda alla tabella
    E.append((
        "| il termine di curvatura di *P* contro «under 1%» del record 50 | **23.8 % (NGC), 47.5 % (SGC)**: la caratterizzazione è ritirata |\n",
        "| il termine di curvatura di *P* contro «under 1%» del record 50 | **23.8 % (NGC), 47.5 % (SGC)**: la caratterizzazione è ritirata |\n"
        "| (17 set) le sette ancore della consegna del 16 contro il disco | **CONFERMATE** tutte e sette; `freeze_verify` CLEAN 06:02:52Z, 72/72, albero pulito |\n"
        "| (17 set) il deposito `22148444` contiene `paper2_prereg_v1.md`? | **NO**, in nessuno dei quattro zip, e in nessuna delle quattro versioni del concept DOI |\n"
        "| (17 set) v1.0 del protocollo (`73c8213`) contro la v1.1 | 8 righe tolte, 61 aggiunte, tutte fuori dalle sezioni delle regole, che sono **identiche** |\n",
    ))

    # 4. «Stato in una riga»: paragrafo del 17
    E.append((
        "in B**, più le quattro Q di D6, fuori dall'universo del ledger e classificate a parte.\n",
        "in B**, più le quattro Q di D6, fuori dall'universo del ledger e classificate a parte.\n"
        "\n"
        "**Al 17 settembre (dodicesima revisione):** registro **72 record**, CLEAN a 72/72 · checklist\n"
        "**rev. 3.28** · tag **`v3.1-paper2`** locale su `bfcb4a5`, senza i record 71–72 · `origin/main`\n"
        "a `40f72a8` (8 set, 55 record) · deposito Zenodo `v3.0-paper2` del 28 ago **senza il\n"
        "protocollo** · Fase 6: **chiuse 6.1, 6.8, 6.9**; 6.3 fatta a meno del commit tre, del deposito e\n"
        "del record 73; 6.2 cominciata; 6.4, 6.5, 6.6, 6.7 aperte; 6.0a all'**ultimo punto della\n"
        "Fase 7** · smentite **12 / 1 / 6**.\n",
    ))

    # 5. §3: intestazione, sotto-intestazione, righe 69–72 rese dal ledger, nota
    E.append((
        "## 3. Il registro degli emendamenti — 68 record\n\n### Fase 6, record 61–68\n",
        "## 3. Il registro degli emendamenti — 72 record\n\n### Fase 6, record 61–72\n",
    ))
    rows = "| 68 | 15 set 12:10 | `6.1/censimento_dei_registri_tre_proprieta_misurate_e_resumable_ridefinita` |\n"
    for n in RECORDS_TO_RENDER:
        utc, item = rendered[n]
        if n == RECORDS_TO_RENDER[-1]:
            rows += f"| **{n}** | **{utc}** | **`{item}`** |\n"
        else:
            rows += f"| {n} | {utc} | `{item}` |\n"
    E.append((
        "| **68** | **15 set 12:10** | **`6.1/censimento_dei_registri_tre_proprieta_misurate_e_resumable_ridefinita`** |\n",
        rows,
    ))
    E.append((
        "> voce 6.1 della checklist; il suo contenuto sta lì e in `logs/censimento_v14.jsonl`.\n",
        "> voce 6.1 della checklist; il suo contenuto sta lì e in `logs/censimento_v14.jsonl`. Il **69**\n"
        "> corregge l'ordine delle regole di `.gitattributes`; il **70** dichiara la portata del rilascio\n"
        "> e il tag `v3.1-paper2`; il **71** dà quattro cause alle quattro citazioni irrisolte del\n"
        "> censimento; il **72** ancora per byte la v1.1 del protocollo, che nessun commit e nessun\n"
        "> deposito porta (§8, Rilascio).\n",
    ))

    # 6. §8: Z-P1 e il blocco Rilascio
    E.append((
        "| **applicazione RINVIATA a dopo la Fase 6** |",
        "| **applicazione all'ULTIMO PUNTO DELLA FASE 7, prima della sottomissione** *(17 set; era «dopo la Fase 6»)* |",
    ))
    E.append((
        "### Rilascio — stato non verificato da settimane\n"
        "\n"
        "`R1` tag retroattivi e Zenodo · `R2` `REPRODUCIBILITY.md`, bloccato da `P-A1` · `R3` tarball del tier\n"
        "`features` · `R4` `git gc` · `P-A1` rimuovere `phase8_test2_permock.csv` e ricostruire il manifest\n"
        "`records`.\n",
        "### Rilascio — stato al 17 settembre\n"
        "\n"
        "`R1` tag: **`v3.1-paper2` locale su `bfcb4a5`** (record 70 §iv; non `v2.1-paper2`, che si\n"
        "ordinerebbe prima di `v3.0-paper2`), senza i record 71–72 e `DOCUMENTED_AMENDMENTS = 72`: serve\n"
        "un commit tre e il tag va spostato su di esso. Zenodo: **solo alla sottomissione, ultimo punto\n"
        "della Fase 7** (17 set); il deposito `10.5281/zenodo.22148444` (`v3.0-paper2`, 28 ago) **non\n"
        "contiene `paper2_prereg_v1.md`** in nessuno dei quattro zip, e nessuna delle quattro versioni del\n"
        "concept DOI lo porta — **record 73 da scrivere** · `R2` `REPRODUCIBILITY.md` **esiste**\n"
        "(`c13ccc3`, 8 set, 176 righe): voce 6.7, da estendere; il §5 porta due affermazioni false\n"
        "(record 69 e 71), da correggere prima del commit tre · `R3` tarball del tier `features`:\n"
        "ignorato dal commit `40f72a8`, deterministico e rigenerato dal manifest · `R4` `git gc` ·\n"
        "`P-A1` **ESEGUITO** dal commit `352e024` (record 71): `phase8_test2_permock.csv` rimosso,\n"
        "sopravvive `phase8_test2_permock_hodfit.csv`. GitHub: `origin/main` a `40f72a8` (8 set, 55\n"
        "record), **da aggiornare periodicamente** (decisione del 17 set, che supera il differimento del\n"
        "record 70: da registrare prima del primo push). I quattordici file citati e non tracciati stanno\n"
        "in `logs/eccezioni_rilascio.json` (`e8d34dbc…`).\n",
    ))

    # 7. §9: la riga falsa tolta con nota, gli strumenti nuovi aggiunti
    E.append((
        "| `paper2_letture_1punto.py` | rifiuta di riportare finché il sottoinsieme 0–199 non riproduce | 31/31 |\n",
        "",
    ))
    E.append((
        "| `paper2_contrasti.py` · `paper2_pendenze.py` · `paper2_ripattern_*.py` · `paper2_surrogato_fit.py` | Fase 3 | — |\n"
        "\n"
        "**Il 54 ha una proprietà che gli altri appender non hanno**",
        "| `paper2_contrasti.py` · `paper2_pendenze.py` · `paper2_ripattern_*.py` · `paper2_surrogato_fit.py` | Fase 3 | — |\n"
        "| `paper2_censimento_rilascio.py` v1.1 | popolazione del rilascio derivata dai record; `metri_concordi` fra `git status` e `check-ignore` | 60/60 |\n"
        "| `paper2_patch_regole_git.py` v1.3 | ordine delle regole di `.gitattributes`, reversibile nei due versi (record 69) | 66/66 |\n"
        "| `paper2_patch_voce_6_1.py` | record 68 nei documenti; diciassette dettagli letterali verificati sul ledger | 71/71 |\n"
        "| `paper2_append_amend69…72.py` | i quattro record del 16 set; consumati, rieseguirli è rifiutato dallo sha del ledger | 35 · 31 · 36 · 33 |\n"
        "| `paper2_patch_documenti_69_72.py` | record 69–72 e decisioni del 17 set nei documenti; righe §3 rese dal ledger | vedi selftest |\n"
        "\n"
        "**Riga tolta il 17 set:** `paper2_letture_1punto.py` «31/31» — lo strumento **non è mai\n"
        "esistito** (record 71); il «31/31» è di `paper2_boxcox_v2.py`, il lavoro lo fa\n"
        "`paper2_passata_1punto.py` (43/43). Rimozione registrata, non silenziosa.\n"
        "\n"
        "**Il 54 ha una proprietà che gli altri appender non hanno**",
    ))

    # 8. §14: le nove lezioni del 16 set
    E.append((
        "- **Non riordinare le chiavi del registro dal record 56 in avanti**: dal 50 la convenzione è quella,\n"
        "  e alternare sarebbe peggio.\n",
        "- **Non riordinare le chiavi del registro dal record 56 in avanti**: dal 50 la convenzione è quella,\n"
        "  e alternare sarebbe peggio.\n"
        "- **Cercare per NOME invece che per contenuto** ha fallito cinque volte in un giorno (16 set):\n"
        "  `cancelli` al plurale, `controlla(` che dà zero in uno strumento con 43 controlli, undici termini\n"
        "  del budget filtrati per cinque parole. **Se una popolazione nota esce incompleta, il metro è\n"
        "  sbagliato prima dei dati.**\n"
        "- **Non dedurre la causa dalla forma**: quattro percorsi con lo stesso esito di misura avevano\n"
        "  quattro cause diverse (record 71).\n"
        "- **Non prevedere un numero invece di aspettare la misura**: «8 esclusi» erano 11. Lo strumento\n"
        "  esiste per questo.\n"
        "- **Un controllo che non può fallire sul difetto che cerca non è un controllo**: «CRLF conservato»\n"
        "  passava anche su `\\r\\r\\n`. Ora confronta byte per byte col caso LF.\n"
        "- **Un metro solo per una proprietà**: `check-ignore --stdin` in modalità testo su Windows riceveva\n"
        "  un CR per riga e non trovava nulla, e `citati_non_esclusi` era PASS perché il metro era rotto.\n"
        "  Si misura su `git status --untracked-files=all` e si confrontano i metri (`metri_concordi`).\n"
        "- **`git add --renormalize .` mette in scena OGNI modifica**, non solo i fine riga: pathspec\n"
        "  esplicite, sempre.\n"
        "- **La cache di stat non si invalida da sé**: dopo un cambio di attributo `git add` è un no-op\n"
        "  silenzioso; si invalida l'mtime e si verifica con `ls-files --eol`.\n"
        "- **Nei record si citano file, non pattern**: `src/*.py` (record 64) e\n"
        "  `ensemble_v1_manifest_*.jsonl` (record 69) non ancorano niente di verificabile.\n"
        "- **Un conteggio di selftest appartiene a uno strumento solo**: «31/31» sul nome sbagliato è la\n"
        "  prova apparente di un'esecuzione mai avvenuta (record 71).\n",
    ))
    return E


# --------------------------------------------------------------------------------------------
# calcolo dei due testi nuovi (nessuna scrittura)
# --------------------------------------------------------------------------------------------

def compute(args):
    ck_b = read_bytes(args.checklist)
    st_b = read_bytes(args.stato)
    check_anchor(args.checklist, ck_b, ANCHOR_CHECKLIST, "checklist")
    check_anchor(args.stato, st_b, ANCHOR_STATO, "stato")
    if b"\r" in ck_b or b"\r" in st_b:
        raise PatchError("uno dei due documenti contiene CR: attesi fine riga LF")
    records = read_ledger(args.ledger)
    rendered = check_ledger_records(records)
    ck = ck_b.decode("utf-8")
    st = st_b.decode("utf-8")
    ck_new = apply_edits(ck, edits_checklist(), "checklist")
    st_new = apply_edits(st, edits_stato(rendered), "stato")
    if MARKER_CHECKLIST not in ck_new or MARKER_STATO not in st_new:
        raise PatchError("marca di revisione assente dal testo nuovo: patch incoerente")
    return ck, ck_new, st, st_new, rendered


def report(ck_new, st_new, rendered):
    print("righe §3 rese dal ledger:")
    for n in RECORDS_TO_RENDER:
        print(f"  {n}: {rendered[n][0]}  {rendered[n][1]}")
    ckb = ck_new.encode("utf-8")
    stb = st_new.encode("utf-8")
    print(f"checklist nuova: {sha256_bytes(ckb)}  {len(ckb)} byte  (rev. 3.28)")
    print(f"stato nuovo:     {sha256_bytes(stb)}  {len(stb)} byte  (dodicesima revisione)")


def cmd_dry_run(args):
    ck, ck_new, st, st_new, rendered = compute(args)
    print(unified(ck, ck_new, os.path.basename(args.checklist)))
    print(unified(st, st_new, os.path.basename(args.stato)))
    print(f"modifiche: checklist {len(edits_checklist())}, stato {len(edits_stato(rendered))} — nessun file scritto")
    report(ck_new, st_new, rendered)
    return 0


def cmd_apply(args):
    ck, ck_new, st, st_new, rendered = compute(args)
    ckb = ck_new.encode("utf-8")
    stb = st_new.encode("utf-8")
    write_atomic(args.checklist, ckb)
    write_atomic(args.stato, stb)
    print("scritti entrambi i documenti.")
    report(ck_new, st_new, rendered)
    return 0


def cmd_verify(args):
    ok = True
    for path, marker, anchor, edits_fn, label in (
        (args.checklist, MARKER_CHECKLIST, ANCHOR_CHECKLIST, lambda: edits_checklist(), "checklist"),
        (args.stato, MARKER_STATO, ANCHOR_STATO, None, "stato"),
    ):
        b = read_bytes(path)
        txt = b.decode("utf-8")
        sha = sha256_bytes(b)
        stale = (sha, len(b)) == anchor
        has_marker = marker in txt
        has_cr = b"\r" in b
        not_applied = 0
        if edits_fn is not None:
            not_applied = sum(1 for _, new in edits_fn() if new and txt.count(new) != 1)
        print(f"{label}: {sha}  {len(b)} byte  marca={'si' if has_marker else 'NO'}  "
              f"ancora-vecchia={'SI' if stale else 'no'}  CR={'SI' if has_cr else 'no'}  "
              f"modifiche-non-trovate={not_applied}")
        ok = ok and has_marker and not stale and not has_cr and not_applied == 0
    print("ESITO:", "VERIFICATO" if ok else "NON VERIFICATO")
    return 0 if ok else 2


# --------------------------------------------------------------------------------------------
# selftest: riproduce i difetti che i cancelli devono fermare, su copie sintetiche
# --------------------------------------------------------------------------------------------

def _fake_ledger(n=LEDGER_RECORDS, drop=None, lf_rows=(8, 9, 10, 11, 13, 14)):
    """Ledger sintetico: 72 righe JSON, CRLF tranne sei righe a LF, dettagli letterali nei 69–72."""
    texts = {
        69: "regole di .gitattributes: vince l'ultima che combacia; src_bundle_phase9.txt riletto",
        70: "portata del rilascio: tag v3.1-paper2 e non v2.1-paper2; papers/ e logs/ fuori",
        71: "quattro cause: paper2_item13_rev2.py, paper2_passata_1punto.py (43/43), "
            "phase8_test2_permock_hodfit.csv sopravvive a 352e024, record 43",
        72: "prereg v1.1 607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86 25319; "
            "v1.0 05cd32b20388fffd5372711880d4c11ef6dda32ff2ff7767e898d667e2a6c115 21430",
    }
    items = {69: "6.3/regole_git", 70: "6.3/portata_del_rilascio", 71: "6.2/quattro_cause",
             72: "6.3/protocollo_ancorato"}
    out = b""
    for i in range(1, n + 1):
        rec = {"item": items.get(i, f"0.{i}"), "text": texts.get(i, f"record {i}"),
               "type": "amend", "utc": f"2026-09-16T1{i % 10}:0{i % 6}:00Z"}
        if drop == i:
            rec["text"] = "x"
        out += json.dumps(rec, ensure_ascii=False).encode("utf-8") + (b"\n" if i in lf_rows else b"\r\n")
    return out


def _fake_doc(edits):
    """Documento sintetico: ogni ancora esattamente una volta, nell'ordine, separate da testo neutro."""
    parts = []
    for i, (old, _) in enumerate(edits, start=1):
        parts.append(f"riga neutra {i}\n")
        parts.append(old)
    parts.append("riga neutra finale\n")
    return "".join(parts)


def cmd_selftest(_args):
    n_ok = 0
    n_tot = 0

    def ctrl(name, cond):
        nonlocal n_ok, n_tot
        n_tot += 1
        n_ok += bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name}")

    def raises(fn):
        try:
            fn()
        except PatchError:
            return True
        return False

    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "ledger.jsonl")
        with open(led, "wb") as f:
            f.write(_fake_ledger())
        recs = read_ledger(led)
        ctrl("ledger sintetico letto: 72 record", len(recs) == LEDGER_RECORDS)
        rendered = check_ledger_records(recs)
        ctrl("record 69–72 con dettagli letterali: passano", set(rendered) == set(RECORDS_TO_RENDER))
        ctrl("utc reso nel formato della tabella ('16 set 19:03')", rendered[69][0] == "16 set 19:03")
        ctrl("render_utc rifiuta un formato diverso", raises(lambda: render_utc("16/09/2026")))

        # difetti del ledger
        with open(led + ".71", "wb") as f:
            f.write(_fake_ledger(n=71))
        ctrl("ledger a 71 righe: rifiutato", raises(lambda: read_ledger(led + ".71")))
        with open(led + ".d", "wb") as f:
            f.write(_fake_ledger(drop=71))
        ctrl("record 71 senza i suoi dettagli letterali: rifiutato",
             raises(lambda: check_ledger_records(read_ledger(led + ".d"))))
        with open(led + ".j", "wb") as f:
            f.write(_fake_ledger()[:-10] + b"{non json\r\n")
        ctrl("riga non JSON: rifiutata", raises(lambda: read_ledger(led + ".j")))
        bad = [dict(r) for r in recs]
        bad[69]["item"] = "a|b"
        ctrl("item con '|' (romperebbe la tabella): rifiutato", raises(lambda: check_ledger_records(bad)))

        # le ancore, sui documenti veri se ci sono, altrimenti sui sintetici
        eck = edits_checklist()
        est = edits_stato(rendered)
        ctrl("nessuna ancora vuota", all(o for o, _ in eck + est))
        ctrl("ogni testo nuovo è diverso dalla sua ancora", all(o != n for o, n in eck + est))

        fck = _fake_doc(eck)
        fst = _fake_doc(est)
        ck_new = apply_edits(fck, eck, "checklist")
        st_new = apply_edits(fst, est, "stato")
        ctrl("applicazione su documento sintetico: ogni testo nuovo presente una volta (checklist)",
             all(ck_new.count(n) == 1 for _, n in eck if n) and MARKER_CHECKLIST in ck_new)
        ctrl("applicazione su documento sintetico: ogni testo nuovo presente una volta (stato)",
             all(st_new.count(n) == 1 for _, n in est if n) and MARKER_STATO in st_new)
        ctrl("le ancore delle sostituzioni (non aggiunte) sono sparite dal testo nuovo",
             all(o not in ck_new for o, n in eck if o not in n) and all(o not in st_new for o, n in est if o not in n))
        ctrl("seconda applicazione sullo stesso testo: rifiutata (idempotenza)",
             raises(lambda: apply_edits(ck_new, eck, "checklist")))
        ctrl("ancora duplicata: rifiutata", raises(lambda: apply_edits(fck + eck[0][0], eck, "checklist")))
        ctrl("ancora mancante: rifiutata", raises(lambda: apply_edits(fck.replace(eck[3][0], ""), eck, "checklist")))
        ctrl("il testo nuovo non contiene CR", "\r" not in ck_new and "\r" not in st_new)
        ctrl("le quattro righe §3 stanno nello stato nuovo, l'ultima in grassetto",
             "| 69 | 16 set 19:03 | `6.3/regole_git` |" in st_new and "| **72** | **16 set 12:00** |" in st_new)
        ctrl("la riga falsa di §9 è tolta e la nota di rimozione c'è",
             "| `paper2_letture_1punto.py` |" not in st_new and "**Riga tolta il 17 set:**" in st_new)
        ctrl("6.9 spuntata nella checklist nuova",
             "- [x] **✦✦ 6.9 —" in ck_new and "- [ ] **✦✦ 6.9 —" not in ck_new)
        ctrl("6.3 porta il tag v3.1-paper2 e non più v2.1 come titolo",
             "**✦✦ 6.3 — Tag `v3.1-paper2`" in ck_new and "- [ ] **6.3** Tag `v2.1-paper2`" not in ck_new)

        # ancore sha e scrittura atomica
        p = os.path.join(d, "doc.md")
        with open(p, "wb") as f:
            f.write(b"abc\n")
        ctrl("ancora sha sbagliata: rifiutata", raises(lambda: check_anchor(p, read_bytes(p), ("00" * 32, 4), "x")))
        ctrl("ancora sha giusta: passa", not raises(lambda: check_anchor(p, read_bytes(p), (sha256_bytes(b"abc\n"), 4), "x")))
        write_atomic(p, b"xyz\n")
        ctrl("write_atomic scrive e rilegge gli stessi byte", read_bytes(p) == b"xyz\n")
        ctrl("write_atomic non lascia file temporanei", not [x for x in os.listdir(d) if x.startswith(".patch_")])

        # sui documenti veri, se presenti nella posizione di default: ancore uniche
        ck_path, st_path = CHECKLIST, STATO
        if os.path.exists(ck_path) and os.path.exists(st_path):
            ckb, stb = read_bytes(ck_path), read_bytes(st_path)
            if (sha256_bytes(ckb), len(ckb)) == ANCHOR_CHECKLIST and (sha256_bytes(stb), len(stb)) == ANCHOR_STATO:
                ckt, stt = ckb.decode("utf-8"), stb.decode("utf-8")
                ctrl("documenti veri alla rev. attesa: ogni ancora della checklist compare una volta",
                     all(ckt.count(o) == 1 for o, _ in eck))
                ctrl("documenti veri alla rev. attesa: ogni ancora dello stato compare una volta",
                     all(stt.count(o) == 1 for o, _ in est))
            else:
                print("  [--] documenti veri non alla rev. attesa (gia' patchati?): controlli sulle ancore saltati")
        else:
            print("  [--] documenti veri non trovati nella posizione di default: controlli sulle ancore saltati")

    print(f"selftest: {n_ok}/{n_tot}")
    return 0 if n_ok == n_tot else 1


# --------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--checklist", default=CHECKLIST)
    ap.add_argument("--stato", default=STATO)
    ap.add_argument("--ledger", default=LEDGER)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "selftest":
            return cmd_selftest(args)
        if args.cmd == "dry-run":
            return cmd_dry_run(args)
        if args.cmd == "apply":
            return cmd_apply(args)
        return cmd_verify(args)
    except PatchError as e:
        print("RIFIUTATO:", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

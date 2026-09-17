#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_reproducibility.py — voce 6.7: `REPRODUCIBILITY.md` da estendere, non da scrivere.

DUE AFFERMAZIONI FALSE, dichiarate dai record 69 e 71, che questo patcher corregge:
  - §5, fine riga: «Il file committato porta 49 CRLF e 6 LF». Ne porta 66 e 6 a 72 record, e il
    conteggio cambia a ogni append: il numero non e' l'invariante. L'invariante e' l'INSIEME
    delle righe a LF — 8, 9, 10, 11, 13 e 14 — che non cambia mai, perche' il file e'
    append-only;
  - §5, `phase8_test2_permock_hodfit.csv`: «Documenti interni precedenti ne segnalavano una
    copia byte-identica: non esiste». Il commit 352e024 dichiara esattamente quella copia e la
    RIMUOVE (record 71, P-A1): va riscritta come rimozione registrata, non come negazione.

E cio' che la voce 6.7 chiede di aggiungere:
  - l'asimmetria di copertura fra la cache di P(k) (due coperture) e il suo asse k (una);
  - il pattern di ripresa di `paper1_remap.py`, l'unico runner che verifica il prodotto laterale;
  - il §7: il protocollo, il suo ancoraggio per byte (record 72) e cio' che il version DOI NON
    contiene (record 73, misurato);
  - i conteggi che invecchiano — «55 record» al §6, «Quattro cose» al §5 — sostituiti da
    formulazioni che restano vere dopo il prossimo append.

CANCELLI:
  1. sha256 e dimensione del documento uguali all'ancora (`f6b380e8…`, 8 138 byte, 176 righe);
  2. il ledger deve essere a 73 record e l'ultimo deve portare il marker del record 73: questo
     patcher cita il 73 e non puo' girare prima di lui;
  3. ogni ancora di testo presente ESATTAMENTE una volta, e il testo nuovo non ancora presente;
     fra le ancore c'e' la promessa in testa al documento, che il §7 nuovo renderebbe falsa;
  4. le due frasi false devono essere PRESENTI prima (se non ci sono, o il file e' un altro, o
     qualcuno le ha gia' toccate) e ASSENTI dopo;
  5. testo nuovo calcolato per intero prima di scrivere; scrittura su temporaneo piu'
     os.replace; byte riletti e confrontati. Fine riga LF, come il file su disco.

Uso (dalla radice del repository):
  python src\paper2_patch_reproducibility.py selftest
  python src\paper2_patch_reproducibility.py dry-run
  python src\paper2_patch_reproducibility.py apply
  python src\paper2_patch_reproducibility.py verify
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

DOC = "REPRODUCIBILITY.md"
LEDGER = "src/paper2_v1_amendments.jsonl"

ANCORA_SHA = "f6b380e893c178dd2992be3f3268067ae62205005a0e7f7452fcec8755c93907"
ANCORA_BYTE = 8138
ANCORA_RIGHE = 176

LEDGER_RECORD_ATTESI = 73
MARKER_73 = "emendamento-73-il-deposito-non-contiene-il-protocollo"

# Le due frasi false: devono esserci prima, e non esserci dopo.
FALSO_EOL = "Il file committato porta 49 CRLF e 6 LF, cioè"
FALSO_COPIA = "Documenti interni precedenti ne segnalavano una copia byte-identica: **non esiste**."

MARKER_DOC = "rev. 17 settembre 2026"


class PatchError(Exception):
    pass


# ---------------------------------------------------------------------------

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leggi(p: Path) -> bytes:
    return p.read_bytes()


def cancello_ancora(p: Path, dati: bytes) -> None:
    got = (sha256_bytes(dati), len(dati))
    if got != (ANCORA_SHA, ANCORA_BYTE):
        raise PatchError(
            "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
            "  O il file non e' quello del commit c13ccc3, o la patch e' gia' applicata."
            % (p, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
    if b"\r" in dati:
        raise PatchError("%s contiene CR: attesi fine riga LF" % p)
    n = dati.count(b"\n")
    if n != ANCORA_RIGHE:
        raise PatchError("%s: %d righe, attese %d" % (p, n, ANCORA_RIGHE))


def cancello_ledger(p: Path) -> str:
    """Il documento nuovo cita il record 73: deve esistere."""
    if not p.is_file():
        raise PatchError("ledger assente: %s" % p)
    righe = [l for l in p.read_bytes().split(b"\n") if l.strip()]
    if len(righe) != LEDGER_RECORD_ATTESI:
        raise PatchError(
            "ledger a %d record, atteso %d. Questo patcher cita il record 73: prima\n"
            "  python src\\paper2_append_amend73.py applica"
            % (len(righe), LEDGER_RECORD_ATTESI))
    ultimo = json.loads(righe[-1].rstrip(b"\r").decode("utf-8"))
    marker = str(ultimo.get("rules", {}).get("marker", ""))
    if marker != MARKER_73:
        raise PatchError("l'ultimo record non e' il 73 atteso: marker %r" % marker)
    if not str(ultimo.get("numbering_rule", "")).rstrip().endswith("record 73."):
        raise PatchError("l'ultimo record non si dichiara il 73")
    return marker


def applica_modifiche(testo: str, modifiche: list) -> str:
    for i, (vecchio, nuovo) in enumerate(modifiche, start=1):
        c = testo.count(vecchio)
        if c != 1:
            testa = vecchio.splitlines()[0][:90] if vecchio else ""
            raise PatchError("ancora %d trovata %d volte (attesa 1): %r" % (i, c, testa))
        if nuovo and nuovo in testo:
            raise PatchError("il testo nuovo della modifica %d e' gia' presente" % i)
        testo = testo.replace(vecchio, nuovo, 1)
    return testo


def scrivi_atomico(p: Path, dati: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".patch_repro_", suffix=".md")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dati)
        os.replace(tmp, str(p))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if leggi(p) != dati:
        raise PatchError("%s: i byte riletti non sono quelli scritti" % p)


# ---------------------------------------------------------------------------
# le modifiche
# ---------------------------------------------------------------------------

def modifiche() -> list:
    E = []

    # 0. la promessa in testa: il §7 porta digest che il deposito NON contiene, e la riga
    #    «ogni digest qui sotto e' ricalcolabile dai file depositati» diventerebbe falsa.
    E.append((
        "Non introduce numeri nuovi: ogni digest qui sotto è ricalcolabile dai file depositati, e la regola per\n"
        "farlo è nel §3.\n",
        "Non introduce numeri nuovi. I digest dei tier congelati sono **ricalcolabili dai file\n"
        "depositati**, e la regola per farlo è nel §3. I digest del **protocollo**, al §7, non lo sono — il\n"
        "deposito non contiene quel documento — e si verificano contro il record 72 e il file su disco.\n",
    ))

    # 1. intestazione: la data di revisione
    E.append((
        "### Manoscritto → tag → DOI → digest — voce **R2** — 7 settembre 2026\n",
        "### Manoscritto → tag → DOI → digest — voce **R2** — 7 settembre 2026,\n"
        "### rev. 17 settembre 2026 (record 69, 71, 72, 73)\n",
    ))

    # 2. §1: lo stato del Paper 2 e che cosa il version DOI identifica davvero
    E.append((
        "| **Paper 2** — a cosa risponde il conteggio | Fasi 0–3 chiuse | `v3.0-paper2` | "
        "`5c54807` | **version DOI 10.5281/zenodo.22148444** |\n",
        "| **Paper 2** — a cosa risponde il conteggio | Fasi 0–5 chiuse, Fase 6 in corso | "
        "`v3.0-paper2` | `5c54807` | **version DOI 10.5281/zenodo.22148444** — l'archivio della "
        "pipeline, **non** il protocollo: §7 |\n",
    ))

    # 3. §1: che cosa ancora il version DOI, e che cosa no
    E.append((
        "**Version DOI della pre-registrazione:** `10.5281/zenodo.22148444` — identifica lo stato dei file\n"
        "**pre-registrato**, e non si muove. È quello contro cui la Fase 3 è registrata.\n",
        "**Version DOI del deposito:** `10.5281/zenodo.22148444` — identifica i **sei file depositati**\n"
        "il 28 agosto 2026, e non si muove. È quello contro cui la Fase 3 è registrata.\n"
        "**Non contiene il documento di pre-registrazione**, in nessuna versione: misurato il 17\n"
        "settembre aprendo ogni archivio di ogni versione del concept DOI (record 73). Il protocollo è\n"
        "ancorato **per byte** dal record 72, e il §7 di questo documento dice come citare i due\n"
        "ancoraggi senza confonderli.\n",
    ))

    # 4. §1: gli stati dopo il tag, e il conteggio che non si scrive a mano
    E.append((
        "| `3858660` | registri di misura della Fase 3: griglia, mock, budget, ripattern, surrogati |\n",
        "| `3858660` | registri di misura della Fase 3: griglia, mock, budget, ripattern, surrogati |\n"
        "| `352e024` | **rimozione** di `results/phase8_test2_permock.csv` e ricostruzione del manifest "
        "`records` (P-A1; §5) |\n"
        "| `c13ccc3` | prima stesura di questo documento |\n"
        "| `3e43e38` | disciplina dei fine riga: regole di cartella in coda in `.gitattributes`, "
        "`eol=lf` sui sorgenti, tre file del tier `records` riportati a `-text` con l'indice riletto "
        "(record 69) |\n"
        "| `bfcb4a5` | contenuti di Fase 4–6: registri di misura, strumenti e verdetti; il record 70 "
        "dichiara la portata del rilascio |\n"
        "\n"
        "Il **tag del Paper 2 per le Fasi 4–6 è `v3.1-paper2`** (record 70 §iv; non `v2.1-paper2`, che\n"
        "si ordinerebbe prima del deposito del 28 agosto). `origin` si aggiorna **periodicamente** dal\n"
        "17 settembre 2026 (record 73 §v); il deposito Zenodo, invece, **solo alla sottomissione**\n"
        "(record 73 §vi), ed è lì che la v1.1 del protocollo entra nell'archivio citabile.\n",
    ))

    # 5. §5: il titolo col numero, che invecchia a ogni voce aggiunta
    E.append((
        "## 5. Quattro cose che il lettore deve sapere\n",
        "## 5. Quello che il lettore deve sapere\n"
        "\n"
        "*(Il titolo portava «Quattro cose». Un conteggio in un'intestazione invecchia alla prima voce\n"
        "aggiunta, come il «55 record» del §6: qui i conteggi stanno nelle righe, dove si verificano.)*\n",
    ))

    # 6. §5: la copia byte-identica — rimozione registrata, non negazione
    E.append((
        "Il tier `records` contiene `results/phase8_test2_permock_hodfit.csv`, `ae733e1e2a74bfff`, 10 891 byte.\n"
        "Documenti interni precedenti ne segnalavano una copia byte-identica: **non esiste**. Gli unici digest\n"
        "ripetuti dentro `records` sono **otto manifest JSON** — sei `phase*_manifest.json` con lo stesso\n"
        "digest e due `phase_r51_manifest` — e sono identici **per costruzione**, non per errore.\n",
        "Il tier `records` contiene `results/phase8_test2_permock_hodfit.csv`, `ae733e1e2a74bfff`, 10 891 byte.\n"
        "\n"
        "**Correzione del 17 settembre 2026 (record 71).** Questo paragrafo diceva che la copia\n"
        "byte-identica segnalata da documenti interni precedenti **non esiste**. La copia esisteva:\n"
        "`results/phase8_test2_permock.csv`, **rimossa per causa** dal commit `352e024`, che è la voce\n"
        "`P-A1` — la rimozione per cui il tier `records` è passato a 224 file e all'aggregato\n"
        "`5364cf2e…`, registrata dall'emendamento 11. Al momento in cui questo documento è stato\n"
        "scritto il file non c'era più, e **«non esiste adesso» è stato scritto come «non è mai\n"
        "esistito»**: una rimozione registrata letta come una negazione. Il sopravvissuto è il\n"
        "`_hodfit` qui sopra, che ha un nome simile e non è la stessa cosa.\n"
        "\n"
        "Gli unici digest ripetuti dentro `records` sono **otto manifest JSON** — sei\n"
        "`phase*_manifest.json` con lo stesso digest e due `phase_r51_manifest` — e sono identici\n"
        "**per costruzione**, non per errore.\n",
    ))

    # 7. §5: i fine riga — l'invariante al posto del conteggio
    E.append((
        "`.gitattributes` contiene `*.jsonl -text`, quindi git **non converte** quei fine riga in nessuna\n"
        "direzione, nonostante `core.autocrlf = true`. Il file committato porta 49 CRLF e 6 LF, cioè\n"
        "l'anomalia com'è.\n",
        "`.gitattributes` contiene `*.jsonl -text`, quindi git **non converte** quei fine riga in nessuna\n"
        "direzione, nonostante `core.autocrlf = true`. Quell'attributo esiste dal 25 agosto 2026, dodici\n"
        "giorni prima del record 47: il record 68 lo emenda su questo punto — cambia il meccanismo, non\n"
        "l'esito.\n"
        "\n"
        "**L'invariante sono le righe, non i conteggi** *(correzione del 17 settembre, record 69)*. Questo\n"
        "paragrafo dava «49 CRLF e 6 LF» per il file committato. I totali crescono a ogni append — a 72\n"
        "record sono 66 e 6, a 73 saranno 67 e 6 — quindi non sono un'ancora: la proprietà verificabile\n"
        "è che le righe a LF siano **esattamente la 8, 9, 10, 11, 13 e 14 e nessun'altra**, e che i\n"
        "primi byte del file non cambino mai. È ciò che `paper2_append_amend*.py` verifica prima e dopo\n"
        "ogni append, e ciò che il censimento dei registri misura.\n"
        "\n"
        "**E l'attributo di un file si legge, non si deduce dal commento in testa a `.gitattributes`.**\n"
        "In quel file **vince l'ultima regola che combacia**: le due regole di cartella stavano in testa\n"
        "e quelle di tipo in coda, quindi ogni `.md`, `.txt` e `.py` sotto `results/` era `text` — e tre\n"
        "file del tier congelato `records` (`src_bundle_phase9.txt`,\n"
        "`phase5_hod_variance_decomp_summary.md`, `env_versions.txt`) erano **normalizzabili**: i loro\n"
        "byte erano riproducibili solo su Windows con `core.autocrlf=true`, e un checkout altrove li\n"
        "avrebbe scritti a LF facendo uscire il congelamento MISMATCH. Il `CLEAN` non lo vedeva perché\n"
        "la conversione non era ancora avvenuta. Corretto dal commit `3e43e38` (record 69): regole di\n"
        "cartella in coda, `*.py` e `*.md` a `text eol=lf`, l'indice dei tre file riletto — la cache di\n"
        "stat di git non si invalida da sé, e `git add` su un file il cui stat combacia con l'indice è\n"
        "un no-op silenzioso. Si verifica con `git ls-files --eol`, non a occhio.\n",
    ))

    # 8. §5: le due voci nuove che la 6.7 chiede — kref e ripresa
    E.append((
        "**Se un giorno si aggiungerà un digest del registro, lo si calcoli sui RECORD e non sui byte.** È\n"
        "invariante ai fine riga, all'ordine delle chiavi — che dal record 50 non è più uniforme — e al BOM\n"
        "che `results/revision/rev1_r11_tiling.json` porta e gli altri registri no.\n",
        "**Se un giorno si aggiungerà un digest del registro, lo si calcoli sui RECORD e non sui byte.** È\n"
        "invariante ai fine riga, all'ordine delle chiavi — che dal record 50 non è più uniforme — e al BOM\n"
        "che `results/revision/rev1_r11_tiling.json` porta e gli altri registri no.\n"
        "\n"
        "### Due coperture per la cache di *P*(*k*), una sola per il suo asse *k*\n"
        "\n"
        "| | percorso | byte | sha256 | chi lo copre |\n"
        "|---|---|---:|---|---|\n"
        "| cache | `results/phase7_pk_nwlh_cache.npz` | 880 272 | `d148f63f…` | il corpo del manifest "
        "`features` **e** il record 5 |\n"
        "| asse *k* | `results/paper2/phase7_pk_nwlh_kref.npz` | 1 684 | `92679cbd…` | **solo** il record 61 |\n"
        "\n"
        "L'asse *k* delle 110 colonne di `pk_matrix` non esisteva in nessun file: il codice che scrive la\n"
        "cache ricava `k_ref` dalla prima realizzazione riuscita e **non lo salva**. Il kref è quell'asse,\n"
        "rigenerato dalla realizzazione 0 e congelato nel record 61. Sta in `results/paper2/` e non nella\n"
        "radice di `results/` per una ragione meccanica: lì cadrebbe **dentro** le regole del tier\n"
        "`features` e il congelamento lo segnalerebbe come file extra. Chi verifica dall'esterno ha\n"
        "bisogno di entrambi, e il kref ha una copertura sola: se si perde, l'asse va rigenerato con\n"
        "`src/paper2_prov_pk_riproduci.py riproduci --out-kref` e riconfrontato col digest del record 61.\n"
        "\n"
        "### Il pattern di ripresa che vale la pena copiare\n"
        "\n"
        "`paper1_remap.py`, righe 512-516, riprende una corsa interrotta solo se esistono **sia** la riga\n"
        "nel registro **sia** il file delle curve su disco. È l'unico runner del programma che verifica il\n"
        "**prodotto laterale** e non solo il proprio registro, ed è la forma corretta: una riga scritta\n"
        "prima di un file mancante fa saltare un lavoro che non è stato fatto. All'estremo opposto,\n"
        "dichiarato e non riparato, `ensemble_v2_{NGC,SGC}.jsonl` non ha né ripresa né identificatore —\n"
        "`--da` è un selettore di popolazione, non una ripresa — e una seconda corsa vi appenderebbe 2000\n"
        "record indistinguibili dai primi per chi legge per unione. Quel runner non riparte: la Fase 4 è\n"
        "chiusa. **I registri di misura si leggono per UNIONE, mai last-wins, e senza i record `smoke`.**\n",
    ))

    # 9. §6: il conteggio che invecchia, e il «documento depositato» che non è depositato
    E.append((
        "**55 record**, append-only, in un file separato dal reference set, che resta byte-identico per sempre.\n"
        "Il §9 del documento depositato ne dichiarava dodici al deposito, e il verificatore asserisce che il\n"
        "conteggio su disco non scenda mai sotto quella soglia.\n",
        "Append-only, in un file separato dal reference set, che resta byte-identico per sempre. **Il\n"
        "conteggio corrente non si scrive qui**: lo dichiara `DOCUMENTED_AMENDMENTS` in\n"
        "`src/paper2_freeze_verify.py`, e ogni esecuzione del verificatore confronta quella costante col\n"
        "numero di record sul disco e rifiuta se divergono. *(Questo paragrafo diceva «55 record»: era\n"
        "vero all'8 settembre e ha smesso di esserlo al primo append.)*\n"
        "\n"
        "Il **§9 del protocollo** ne dichiara dodici alla data del deposito, e il verificatore asserisce\n"
        "che il conteggio su disco non scenda mai sotto quella soglia. Il dodici ha una conferma\n"
        "indipendente: `cauchy_code.zip` del deposito porta `src/paper2_v1_amendments.jsonl` con **dodici\n"
        "record**, 12 670 byte (record 73).\n",
    ))

    # 10. il §7 nuovo, in coda
    E.append((
        "**Le predizioni falsificate restano falsificate**, con la ragione per cui la soglia era mal posta, e\n"
        "non sono mai riparate a posteriori. Fra i record 39–55: due predizioni dichiarate e smentite, un\n"
        "audit che ha **ritirato** una falsificazione precedente perché non decideva, e la registrazione di un\n"
        "difetto che è costato otto ore di macchina.\n",
        "**Le predizioni falsificate restano falsificate**, con la ragione per cui la soglia era mal posta, e\n"
        "non sono mai riparate a posteriori. Fra i record 39–55: due predizioni dichiarate e smentite, un\n"
        "audit che ha **ritirato** una falsificazione precedente perché non decideva, e la registrazione di un\n"
        "difetto che è costato otto ore di macchina.\n"
        "\n"
        "---\n"
        "\n"
        "## 7. Il protocollo: due ancoraggi, e cosa il DOI non contiene\n"
        "\n"
        "Ogni record del registro porta, nel campo `document`, la stringa «`paper2_prereg_v1.md` v1.1 —\n"
        "version DOI 10.5281/zenodo.22148444». È un **nome**, non un digest, e per 71 record non ce n'era\n"
        "nessun altro.\n"
        "\n"
        "| | valore | che cos'è |\n"
        "|---|---|---|\n"
        "| **v1.1, su disco** | `607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86`, 25 319 byte | "
        "il protocollo corrente, **ancorato per byte dal record 72** |\n"
        "| **v1.0, in git** | `05cd32b20388fffd5372711880d4c11ef6dda32ff2ff7767e898d667e2a6c115`, 21 430 byte | "
        "recuperabile con `git show 900335e^:papers/paper2/paper2_prereg_v1.md` |\n"
        "| **nel deposito** | — | **nessuna delle due**: il version DOI non contiene il protocollo |\n"
        "\n"
        "**Perché la v1.1 non è in git.** `papers/` è uscito dal versionamento col commit `900335e` del 28\n"
        "agosto alle 18:23:40 +0200 — i sorgenti dei manoscritti e la corrispondenza con editore e referee\n"
        "non fanno parte del rilascio del codice (record 70 §i) — e la v1.1 è stata scritta alle 20:13:04,\n"
        "dopo. Un file uscito dal versionamento smette di avere una storia nello stesso istante, e ciò che\n"
        "si scrive dopo non ce l'ha mai avuta. **Ancorare non è versionare**: le due decisioni sono\n"
        "indipendenti, e il record 72 fa la prima senza toccare la seconda.\n"
        "\n"
        "**Perché la v1.1 non è nel deposito, e nemmeno la v1.0** *(record 73, misurato il 17 settembre\n"
        "2026)*. Il concept DOI ha quattro versioni — v1.0 (2 luglio), v2.0-paper-c (3 luglio),\n"
        "v2.1-phase9b (6 luglio), v3.0-paper2 (28 agosto). Ogni file di ognuna è stato scaricato e ogni\n"
        "archivio aperto: **1068 membri in tutto, nessuno col protocollo**. Le prime tre versioni sono\n"
        "archivi del repository a quei tag, e il protocollo non esisteva ancora; la quarta contiene sei\n"
        "file — `README.md`, `MANIFEST.sha256` e quattro zip, i cui digest coincidono col manifest — e\n"
        "`cauchy_code.zip` non porta `papers/` perché quell'albero era già fuori dal versionamento da\n"
        "sedici minuti. **Il version DOI ancora l'archivio della pipeline, non il documento contro cui la\n"
        "pipeline si dichiara.**\n"
        "\n"
        "**Che cosa cambia fra v1.0 e v1.1, misurato riga per riga:** 8 righe tolte e 61 aggiunte, e le\n"
        "aggiunte cadono nel preambolo, nel §2.1 (*Reference set*), nel §9 (*Amendment record*) e in tre\n"
        "righe del §0. **Le sezioni che portano le regole dell'analisi sono identiche.** È la ragione per\n"
        "cui depositare la v1.1 alla sottomissione non indebolisce la pre-registrazione: non c'è una\n"
        "regola che sia stata cambiata dopo aver visto un risultato. È una condizione da **rimisurare** se\n"
        "qualcuno tocca il documento, non da riaffermare.\n"
        "\n"
        "**Una riga del protocollo che non è vera, e non è stata corretta qui.** La v1.1 dichiara in testa\n"
        "«*Version 1.1 — 28 August 2026 (version 1.0 deposited 27 August 2026)*». Nessuna versione del\n"
        "concept DOI è del 27 agosto: l'unico evento di quel giorno su quel percorso è il commit\n"
        "`73c8213`. La parola «deposited» descrive lì un commit, non un deposito. Il protocollo **non si\n"
        "riscrive per emendamento**: la correzione va nella versione che si deposita alla sottomissione,\n"
        "dove sarà vera (record 73 §iii).\n"
        "\n"
        "**Come citare i due ancoraggi.** Fino al deposito della Fase 7: il **DOI** per l'archivio della\n"
        "pipeline, il **digest del record 72** per il documento. Dopo il deposito, il version DOI nuovo\n"
        "coprirà entrambi, e questa sezione va riscritta con quel DOI al posto di questa distinzione.\n",
    ))
    return E


# ---------------------------------------------------------------------------

def calcola(doc: Path, ledger: Path, controlla_ledger: bool = True) -> tuple:
    dati = leggi(doc)
    cancello_ancora(doc, dati)
    if controlla_ledger:
        cancello_ledger(ledger)
    testo = dati.decode("utf-8")
    for frase, nome in ((FALSO_EOL, "il conteggio «49 CRLF e 6 LF»"),
                        (FALSO_COPIA, "la negazione della copia byte-identica")):
        if testo.count(frase) != 1:
            raise PatchError("non trovo %s esattamente una volta: il documento non e' quello "
                             "che questa patch corregge" % nome)
    nuovo = applica_modifiche(testo, modifiche())
    for frase, nome in ((FALSO_EOL, "il conteggio «49 CRLF e 6 LF»"),
                        (FALSO_COPIA, "la negazione della copia byte-identica")):
        if frase in nuovo:
            raise PatchError("%s sopravvive nel testo nuovo" % nome)
    if MARKER_DOC not in nuovo:
        raise PatchError("marca di revisione assente dal testo nuovo")
    if "\r" in nuovo:
        raise PatchError("il testo nuovo contiene CR")
    return testo, nuovo


def rapporto(nuovo: str) -> None:
    b = nuovo.encode("utf-8")
    print("REPRODUCIBILITY.md nuovo: %s  %d byte  %d righe"
          % (sha256_bytes(b), len(b), nuovo.count("\n")))


def cmd_dry_run(a) -> int:
    vecchio, nuovo = calcola(Path(a.doc), Path(a.ledger), not a.senza_ledger)
    print("".join(difflib.unified_diff(vecchio.splitlines(keepends=True),
                                       nuovo.splitlines(keepends=True),
                                       fromfile=DOC + " (prima)", tofile=DOC + " (dopo)", n=1)))
    print("modifiche: %d — nessun byte scritto" % len(modifiche()))
    rapporto(nuovo)
    return 0


def cmd_apply(a) -> int:
    _, nuovo = calcola(Path(a.doc), Path(a.ledger), not a.senza_ledger)
    scrivi_atomico(Path(a.doc), nuovo.encode("utf-8"))
    print("scritto %s" % a.doc)
    rapporto(nuovo)
    return 0


def cmd_verify(a) -> int:
    dati = leggi(Path(a.doc))
    testo = dati.decode("utf-8")
    sha = sha256_bytes(dati)
    vecchio = (sha, len(dati)) == (ANCORA_SHA, ANCORA_BYTE)
    marca = MARKER_DOC in testo
    falsi = [n for f, n in ((FALSO_EOL, "49 CRLF e 6 LF"),
                            (FALSO_COPIA, "copia byte-identica: non esiste")) if f in testo]
    mancanti = sum(1 for _, n in modifiche() if n and testo.count(n) != 1)
    print("%s: %s  %d byte  marca=%s  ancora-vecchia=%s  CR=%s  frasi-false=%s  "
          "modifiche-non-trovate=%d"
          % (DOC, sha, len(dati), "si" if marca else "NO", "SI" if vecchio else "no",
             "SI" if b"\r" in dati else "no", falsi if falsi else "nessuna", mancanti))
    ok = marca and not vecchio and not falsi and mancanti == 0 and b"\r" not in dati
    print("ESITO:", "VERIFICATO" if ok else "NON VERIFICATO")
    return 0 if ok else 2


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def _doc_finto(mods) -> str:
    parti = []
    for i, (vecchio, _) in enumerate(mods, start=1):
        parti.append("riga neutra %d\n" % i)
        parti.append(vecchio)
    parti.append("riga neutra finale\n")
    return "".join(parti)


def _ledger_finto(n=LEDGER_RECORD_ATTESI, marker=MARKER_73) -> bytes:
    fuori = b""
    for i in range(1, n + 1):
        rec = {"item": "finto/%d" % i,
               "numbering_rule": "Questo e' il record %d." % i,
               "rules": {"marker": marker if i == n else "altro-%d" % i}}
        fuori += json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\r\n"
    return fuori


def selftest(a) -> int:
    ok = tot = 0

    def controlla(nome, cond):
        nonlocal ok, tot
        tot += 1
        ok += bool(cond)
        print("  [%s] %s" % ("ok" if cond else "FAIL", nome))

    def rifiuta(fn):
        try:
            fn()
        except PatchError:
            return True
        return False

    mods = modifiche()
    controlla("nessuna ancora vuota", all(v for v, _ in mods))
    controlla("ogni testo nuovo diverso dalla sua ancora", all(v != n for v, n in mods))
    controlla("le due frasi false stanno in un'ancora e in nessun testo nuovo",
              any(FALSO_EOL in v for v, _ in mods) and any(FALSO_COPIA in v for v, _ in mods)
              and not any(FALSO_EOL in n or FALSO_COPIA in n for _, n in mods))
    controlla("nessun testo nuovo contiene CR", not any("\r" in n for _, n in mods))

    finto = _doc_finto(mods)
    nuovo = applica_modifiche(finto, mods)
    controlla("applicazione su documento sintetico: ogni testo nuovo una volta",
              all(nuovo.count(n) == 1 for _, n in mods if n))
    controlla("marca di revisione presente", MARKER_DOC in nuovo)
    controlla("le frasi false sono sparite", FALSO_EOL not in nuovo and FALSO_COPIA not in nuovo)
    controlla("seconda applicazione rifiutata", rifiuta(lambda: applica_modifiche(nuovo, mods)))
    controlla("ancora duplicata rifiutata",
              rifiuta(lambda: applica_modifiche(finto + mods[0][0], mods)))
    controlla("ancora mancante rifiutata",
              rifiuta(lambda: applica_modifiche(finto.replace(mods[2][0], ""), mods)))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        led = base / "led.jsonl"
        led.write_bytes(_ledger_finto())
        controlla("ledger a 73 col marker del 73: passa", cancello_ledger(led) == MARKER_73)
        led.write_bytes(_ledger_finto(n=72))
        controlla("ledger a 72 rifiutato (il 73 non c'e' ancora)",
                  rifiuta(lambda: cancello_ledger(led)))
        led.write_bytes(_ledger_finto(marker="emendamento-72-ancoraggio-del-protocollo"))
        controlla("ledger a 73 col marker sbagliato rifiutato",
                  rifiuta(lambda: cancello_ledger(led)))
        led.unlink()
        controlla("ledger assente rifiutato", rifiuta(lambda: cancello_ledger(led)))

        d = base / "doc.md"
        d.write_bytes(b"niente\n")
        controlla("ancora sha sbagliata rifiutata",
                  rifiuta(lambda: cancello_ancora(d, leggi(d))))
        scrivi_atomico(d, b"altro\n")
        controlla("scrivi_atomico scrive e rilegge", leggi(d) == b"altro\n")
        controlla("scrivi_atomico non lascia temporanei",
                  not [x for x in os.listdir(td) if x.startswith(".patch_repro_")])

    # sul documento vero, se e' quello atteso: ancore uniche
    vero = Path(a.doc)
    if vero.is_file():
        dati = leggi(vero)
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            t = dati.decode("utf-8")
            controlla("documento vero: ogni ancora compare una volta",
                      all(t.count(v) == 1 for v, _ in mods))
            controlla("documento vero: le due frasi false ci sono",
                      t.count(FALSO_EOL) == 1 and t.count(FALSO_COPIA) == 1)
        else:
            print("  [--] documento vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] documento vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="voce 6.7: correzione ed estensione di "
                                             "REPRODUCIBILITY.md")
    ap.add_argument("comando", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--doc", default=DOC)
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--senza-ledger", action="store_true",
                    help="salta il cancello sul record 73 (solo per prove)")
    a = ap.parse_args(argv)
    try:
        if a.comando == "selftest":
            return selftest(a)
        if a.comando == "dry-run":
            return cmd_dry_run(a)
        if a.comando == "apply":
            return cmd_apply(a)
        return cmd_verify(a)
    except PatchError as e:
        print("RIFIUTATO: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

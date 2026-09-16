#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""paper2_patch_voce_6_1.py — porta il record 68 nei due documenti compagni.

Il record 68 chiude la voce 6.1 nel ledger e nomina come documenti compagni
`checklist_paper2.md` e `paper2_stato.md`. Finche' i documenti non lo portano, il
ledger e la checklist dicono due cose diverse sullo stesso punto: e' la condizione
che il record 64 ha corretto per il 63.

Che cosa fa, e in quale ordine:

  1. CANCELLO SUGLI SHA. I tre file di ingresso (ledger, checklist, stato) devono
     avere lo sha256 e la lunghezza dichiarati in ANCORE. Se uno solo non combacia,
     il patcher rifiuta e non scrive nulla: le ancore di testo sono state ricavate
     da QUEI byte.
  2. CANCELLO SUL RECORD. Il ledger deve avere 68 righe; l'ultima deve essere il
     record 68 (numbering_rule), della voce 6.1 (item), che emenda il 47
     (amends_records) e nomina i due documenti (rules.companion_documents).
  3. ESTRAZIONE. Ogni numero che entra nei documenti e' letto dai campi del record,
     non scritto qui: popolazione, righe, modi di ripresa, profilo CRLF/LF, residuo.
     Se una sola estrazione fallisce, il patcher rifiuta.
  4. VERIFICHE LETTERALI. Ogni dettaglio citato nel testo inserito (un commit, un
     intervallo di righe, un nome di file) deve comparire nel record serializzato.
     La prosa di raccordo e' scritta qui; nessun fatto lo e'.
  5. ANCORE UNIVOCHE. Ogni ancora deve comparire esattamente una volta. Zero o due
     occorrenze sono un rifiuto, mai una sostituzione silenziosa.
  6. BACKUP IN logs/. La copia si SCRIVE in logs/, non si sposta dopo: uno
     spostamento e' una seconda operazione che puo' fallire a meta'. Nessun .bak
     nasce accanto al file (regola del record 68, terza voce per il 6.2).
  7. SCRITTURA ATOMICA. I due file si muovono insieme: tmp + os.replace, e se la
     seconda sostituzione fallisce la prima viene riportata indietro dal backup.
  8. VERIFICA A VALLE. Lo sha di cio' che e' finito su disco deve combaciare con lo
     sha di cio' che si intendeva scrivere, e con SHA_DOPO.

Sottocomandi: selftest | dryrun | apply | verify

    python src\paper2_patch_voce_6_1.py selftest
    python src\paper2_patch_voce_6_1.py dryrun
    python src\paper2_patch_voce_6_1.py apply
    python src\paper2_patch_voce_6_1.py verify

Il patcher NON tocca il ledger, NON tocca paper2_5_5_smentite.md, NON tocca
DOCUMENTED_AMENDMENTS (gia' a 68, patcher suo).
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VERSIONE = "1.0"

# --------------------------------------------------------------------------- #
# Ancore: sha256 e lunghezza dei tre ingressi, dalla consegna del 15 settembre.
# --------------------------------------------------------------------------- #

ANCORE = {
    "ledger": (
        "src/paper2_v1_amendments.jsonl",
        "78c47a5d893313ad760249983c78f5eda34f303146ef940d9c4cf693f39b04b8",
        565567,
    ),
    "checklist": (
        "papers/paper2/checklist_paper2.md",
        "c4632ca307a95215967fa633249836096872db6dc093226c432c542df35fcb8b",
        232204,
    ),
    "stato": (
        "papers/paper2/paper2_stato.md",
        "8f1a7d7fda402ec6b169c1ca9e30dec31c7be1a74ba24649f22f6ea24ae73cca",
        77021,
    ),
}

# sha256 attesi DOPO la patch. Se il cancello a monte passa, l'uscita e'
# deterministica: questi devono combaciare, e `verify` li controlla.
SHA_DOPO = {
    "checklist": "db5d2308d289ad8f01b9d9b886f833fa3664a750b3aa89c4a9b0460adb532276",
    "stato": "edc33a0073b2ce36d7692faa1c4997e96bfe1b69c9c19a26040d48465e34e4bb",
}

MARCA = "\u25c6\u25c6"  # doppio rombo: combinazione libera, verificata a runtime

RECORD_ATTESO = 68
VOCE = "6.1"

# --------------------------------------------------------------------------- #
# Ancore di testo. Ognuna deve comparire ESATTAMENTE una volta.
# --------------------------------------------------------------------------- #

A_CHK_VOCE = (
    "- [ ] **6.1** JSONL append-only, atomico, crash-safe, resumable, "
    "per ogni run di Fase 3, 4 e 4D."
)
A_CHK_REV_PREFISSO = "### rev. 3.26 \u2014 14 settembre 2026 \u2014 record 67;"

A_STATO_REV = "**14 settembre 2026**, decima revisione"
A_STATO_BLOCCO = "> **Cosa \u00e8 cambiato nella decima revisione (14 settembre)"
A_STATO_H3 = "## 3. Il registro degli emendamenti \u2014 60 record"
A_STATO_H4 = "### Fase 4 e Fase 5, record 56\u201360"

# Dettagli che il testo inserito cita e che devono esistere nel record.
VERIFICHE_LETTERALI = [
    "684d1f3",
    "25 agosto 2026",
    "691-738",
    "512-516",
    "8 9 10 11 13 14",
    "cachedelta_manifest_",
    "ensemble_v1_manifest_",
    "ensemble_v2_{NGC,SGC}.jsonl",
    "paper1_remap.py",
    "paper2_runner_fase3_mock.py",
    "gate53.jsonl",
    "per_mock_*_erosion_restrict",
    "REPRODUCIBILITY.md",
    "crashsafe_residuo",
    "append_strutturale",
    "core.autocrlf",
    "text: unset",
]

MESI = {
    1: "gen", 2: "feb", 3: "mar", 4: "apr", 5: "mag", 6: "giu",
    7: "lug", 8: "ago", 9: "set", 10: "ott", 11: "nov", 12: "dic",
}


class Rifiuto(Exception):
    """Un cancello non e' passato. Nessun file e' stato scritto."""


# --------------------------------------------------------------------------- #
# Utilita'
# --------------------------------------------------------------------------- #

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leggi_byte(p: Path) -> bytes:
    if not p.is_file():
        raise Rifiuto("file assente: %s" % p)
    return p.read_bytes()


def spazia(n: int) -> str:
    """78067 -> '78 067', come nei documenti."""
    return "{:,}".format(n).replace(",", "\u00a0").replace("\u00a0", " ")


def una_sola_volta(testo: str, ancora: str, nome: str) -> None:
    n = testo.count(ancora)
    if n != 1:
        raise Rifiuto("ancora %s trovata %d volte, attesa 1" % (nome, n))


# --------------------------------------------------------------------------- #
# Lettura del ledger
# --------------------------------------------------------------------------- #

def leggi_ledger(p: Path, attesi: int = RECORD_ATTESO) -> list:
    righe = leggi_byte(p).decode("utf-8").splitlines()
    righe = [r for r in righe if r.strip()]
    if len(righe) != attesi:
        raise Rifiuto("ledger a %d record, atteso %d" % (len(righe), attesi))
    out = []
    for i, r in enumerate(righe, 1):
        try:
            out.append(json.loads(r))
        except Exception as e:
            raise Rifiuto("record %d non parsabile: %s" % (i, e))
    return out


def cancello_record(rec: dict, n: int = RECORD_ATTESO) -> None:
    nr = str(rec.get("numbering_rule", ""))
    if not nr.rstrip().endswith("record %d." % n):
        raise Rifiuto("l'ultimo record non si dichiara il %d: %r" % (n, nr[-40:]))
    item = str(rec.get("item", ""))
    if not item.startswith(VOCE + "/"):
        raise Rifiuto("il record %d non e' della voce %s: item=%r" % (n, VOCE, item))
    if rec.get("amends_records") != [47]:
        raise Rifiuto("amends_records atteso [47], trovato %r" % (rec.get("amends_records"),))
    ca = (rec.get("counts_after") or {}).get("DOCUMENTED_AMENDMENTS")
    if ca != n:
        raise Rifiuto("counts_after.DOCUMENTED_AMENDMENTS atteso %d, trovato %r" % (n, ca))
    comp = str((rec.get("rules") or {}).get("companion_documents", ""))
    for doc in ("checklist_paper2.md", "paper2_stato.md"):
        if doc not in comp:
            raise Rifiuto("il record non nomina %s fra i documenti compagni" % doc)
    if not str((rec.get("rules") or {}).get("marker", "")).startswith("emendamento-%d-" % n):
        raise Rifiuto("rules.marker non e' quello dell'emendamento %d" % n)


# --------------------------------------------------------------------------- #
# Estrazione: ogni numero viene dal record
# --------------------------------------------------------------------------- #

def estrai(rec: dict) -> dict:
    nv = rec.get("new_value") or {}
    if not isinstance(nv, dict):
        raise Rifiuto("new_value non e' un oggetto")

    def campo(nome: str) -> str:
        v = nv.get(nome)
        if not isinstance(v, str) or not v.strip():
            raise Rifiuto("campo new_value.%s assente o vuoto" % nome)
        return v

    v = {}

    m = re.search(
        r"(\d+) file \.jsonl, ([\d\s]+?) righe; in scopo (\d+) file, ([\d\s]+?) righe",
        campo("misura"),
    )
    if not m:
        raise Rifiuto("new_value.misura: popolazione non estraibile")
    v["n_file"] = int(m.group(1))
    v["n_righe"] = int(re.sub(r"\s", "", m.group(2)))
    v["n_file_scopo"] = int(m.group(3))
    v["n_righe_scopo"] = int(re.sub(r"\s", "", m.group(4)))

    res = campo("resumable_ridefinita")
    m = re.search(r"(\d+) righe, ognuna col file", res)
    if not m:
        raise Rifiuto("new_value.resumable_ridefinita: numero di dichiarazioni non estraibile")
    v["n_dichiarazioni"] = int(m.group(1))
    modi = re.findall(r"([a-z_]+) \((\d+)\)", res)
    attesi = [
        "ripresa_dal_registro", "na_una_passata", "na_scansione",
        "nessuna_ripresa_id", "nessuna_ripresa_senza_id", "da_leggere",
    ]
    d = dict((k, int(x)) for k, x in modi)
    if sorted(d) != sorted(attesi):
        raise Rifiuto("modi di ripresa attesi %r, trovati %r" % (sorted(attesi), sorted(d)))
    if sum(d.values()) != v["n_dichiarazioni"]:
        raise Rifiuto(
            "i modi sommano %d, le dichiarazioni sono %d" % (sum(d.values()), v["n_dichiarazioni"])
        )
    v["modi"] = d
    m = re.search(r"righe (\d+-\d+)", res)
    if not m:
        raise Rifiuto("new_value.resumable_ridefinita: righe della chiave di Fase 3 non estraibili")
    v["righe_chiave"] = m.group(1)

    fail = campo("unico_FAIL")
    m = re.search(r"(\d+) CRLF e (\d+) LF", fail)
    if not m:
        raise Rifiuto("new_value.unico_FAIL: profilo CRLF/LF non estraibile")
    v["crlf"], v["lf"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"era (\d+)/(\d+) su (\d+) record", fail)
    if not m:
        raise Rifiuto("new_value.unico_FAIL: profilo iniziale non estraibile")
    v["prof_prima"] = "%s/%s" % (m.group(1), m.group(2))
    v["rec_prima"] = int(m.group(3))
    m = re.search(r"(\d+)/(\d+) su (\d+) oggi", fail)
    if not m:
        raise Rifiuto("new_value.unico_FAIL: profilo corrente non estraibile")
    v["prof_oggi"] = "%s/%s" % (m.group(1), m.group(2))
    v["rec_oggi"] = int(m.group(3))
    m = re.search(r"indici ([\d ]+?)\.", fail)
    if not m:
        raise Rifiuto("new_value.unico_FAIL: indici delle righe non estraibili")
    v["indici"] = m.group(1).strip()

    m = re.search(r"(\d+) file \.jsonl sotto results/", campo("residuo_dichiarato"))
    if not m:
        raise Rifiuto("new_value.residuo_dichiarato: non classificati non estraibili")
    v["n_non_classificati"] = int(m.group(1))

    m = re.search(r"appenderebbe (\d+) record", campo("il_grado_di_rischio_piu_alto"))
    if not m:
        raise Rifiuto("new_value.il_grado_di_rischio_piu_alto: numero di record non estraibile")
    v["n_seconda_corsa"] = int(m.group(1))

    m = re.search(r"righe (\d+-\d+)", campo("la_ripresa_migliore_del_programma"))
    if not m:
        raise Rifiuto("new_value.la_ripresa_migliore_del_programma: righe non estraibili")
    v["righe_remap"] = m.group(1)

    ret = rec.get("rettifica_del_record_47") or {}
    if not isinstance(ret, dict) or "cosa_e_falso" not in ret:
        raise Rifiuto("rettifica_del_record_47 assente o senza cosa_e_falso")
    m = re.search(r"commit ([0-9a-f]{7,40}) del (\d+ \w+ \d{4})", ret["cosa_e_falso"])
    if not m:
        raise Rifiuto("rettifica_del_record_47: commit e data non estraibili")
    v["commit"] = m.group(1)
    v["data_commit"] = m.group(2)

    v["utc"] = str(rec.get("utc", ""))
    if not re.match(r"^\d{4}-\d{2}-\d{2}T", v["utc"]):
        raise Rifiuto("utc del record non riconosciuto: %r" % v["utc"])
    v["marker"] = str((rec.get("rules") or {}).get("marker", ""))

    testo = json.dumps(rec, ensure_ascii=False)
    for lit in VERIFICHE_LETTERALI:
        if lit not in testo:
            raise Rifiuto("verifica letterale fallita: %r non e' nel record" % lit)

    return v


# --------------------------------------------------------------------------- #
# Resa dei testi
# --------------------------------------------------------------------------- #

def riga_rev_checklist(v: dict) -> str:
    return (
        "### rev. 3.27 \u2014 15 settembre 2026 \u2014 record 68; **la 6.1 \u00e8 un censimento con "
        "eccezioni dichiarate, non un requisito di conformit\u00e0**: tre propriet\u00e0 misurate su "
        "{n_file} file e {n_righe} righe ({n_file_scopo} file e {n_righe_scopo} in scopo), "
        "l'append-only storico contro una linea di base, `resumable` ridefinita come "
        "**dichiarazione del runner** su {n_dichiarazioni} righe, un solo FAIL gi\u00e0 dichiarato "
        "dal **record 47** \u2014 che questo record **emenda** \u2014 e {n_non_classificati} file non "
        "classificati consegnati al 6.2"
    ).format(
        n_file=v["n_file"],
        n_righe=spazia(v["n_righe"]),
        n_file_scopo=v["n_file_scopo"],
        n_righe_scopo=spazia(v["n_righe_scopo"]),
        n_dichiarazioni=v["n_dichiarazioni"],
        n_non_classificati=v["n_non_classificati"],
    )


def voce_checklist(v: dict) -> str:
    m = v["modi"]
    righe = [
        "- [x] **{marca} 6.1 \u2014 JSONL di Fase 3, 4 e 4D: CENSIMENTO ESEGUITO. CHIUSA il 15 set,"
        " record 68**".format(marca=MARCA),
        "      *(la voce chiedeva append-only, atomici, crash-safe e resumable: nessuno dei quattro",
        "      aggettivi era definito, la popolazione non era delimitata, e non era dichiarato dove",
        "      ciascuna propriet\u00e0 si verifichi)*.",
        "      **Decisione A \u2014 \u00e8 un censimento con eccezioni dichiarate, non un requisito di",
        "      conformit\u00e0.** I registri sono append-only e in parte dentro il congelamento:",
        "      riscriverli \u00e8 escluso, e l'unica uscita ammessa per un registro che non soddisfa una",
        "      propriet\u00e0 \u00e8 **dichiararla**. `NA` \u00e8 un esito stampato, mai un pass silenzioso.",
        "      **Popolazione:** {n_file} file `.jsonl` e {n_righe} righe, **in scopo {n_file_scopo} "
        "file e {n_righe_scopo} righe**.".format(
            n_file=v["n_file"], n_righe=spazia(v["n_righe"]),
            n_file_scopo=v["n_file_scopo"], n_righe_scopo=spazia(v["n_righe_scopo"]),
        ),
        "      Dentro i `cachedelta_manifest_*` (la provenienza su cui poggia il 4.2b) e i",
        "      `gate*.jsonl` (un cancello non append-only corromperebbe un verdetto come un registro",
        "      di misura). **Corretta il 15 settembre:** i cinque tier del congelamento",
        "      `ensemble_v1_manifest_*` erano rimasti fuori per svista \u2014 ed \u00e8 ci\u00f2 che",
        "      `freeze_verify` legge per dichiarare CLEAN.",
        "      **Le quattro propriet\u00e0 non si verificano nello stesso posto**, e la voce non lo",
        "      diceva. `append_strutturale`, `atomico_residuo` e `crashsafe_residuo` si **misurano**",
        "      sul registro: PASS ovunque, con un solo FAIL. L'append-only **storico** richiede un",
        "      prima e non \u00e8 dimostrabile all'indietro: lo strumento **stabilisce la linea di base**",
        "      \u2014 lunghezza e digest per file \u2014 e da l\u00ec verifica che i primi *n* byte siano invariati;",
        "      **{n_file} file su {n_file}**, zero prefissi modificati, zero file accorciati.".format(
            n_file=v["n_file"]),
        "      **`resumable` non \u00e8 una propriet\u00e0 del registro**: \u00e8 del **runner**, che il registro",
        "      pu\u00f2 corroborare ma non produrre. {n} dichiarazioni, ognuna col file e le righe di".format(
            n=v["n_dichiarazioni"]),
        "      origine \u2014 `ripresa_dal_registro` {a}, `na_una_passata` {b}, `na_scansione` {c},".format(
            a=m["ripresa_dal_registro"], b=m["na_una_passata"], c=m["na_scansione"]),
        "      `nessuna_ripresa_id` {d}, `nessuna_ripresa_senza_id` {e}, `da_leggere` {f}. La chiave".format(
            d=m["nessuna_ripresa_id"], e=m["nessuna_ripresa_senza_id"], f=m["da_leggere"]),
        "      di Fase 3 \u00e8 una **tupla a dieci componenti** (`paper2_runner_fase3_mock.py` righe",
        "      {righe}), **tollerante all'assenza** perch\u00e9 il runner la legge con `.get()`: un".format(
            righe=v["righe_chiave"]),
        "      controllo di presenza darebbe FAIL su un registro corretto.",
        "      **L'unico FAIL era gi\u00e0 dichiarato nove giorni prima, dal record 47**:",
        "      `src\\paper2_v1_amendments.jsonl` su `crashsafe_residuo`, {crlf} CRLF e {lf} LF su".format(
            crlf=v["crlf"], lf=v["lf"]),
        "      eredit\u00e0 CRLF, righe {indici}. Non \u00e8 un'eccezione nuova, ed \u00e8 la verifica".format(
            indici=v["indici"]),
        "      sperimentale del \u00abnothing is rewritten\u00bb che il 47 dichiarava: il profilo era",
        "      **{pa} su {ra} record** il 6 settembre ed \u00e8 **{po} su {ro}** oggi, **stessi indici**.".format(
            pa=v["prof_prima"], ra=v["rec_prima"], po=v["prof_oggi"], ro=v["rec_oggi"]),
        "      **Il record 47 \u00e8 emendato, e la posizione migliora.** La sua premessa \u2014",
        "      \u00ab`.gitattributes` copre `results/**`, non `src/`\u00bb \u2014 \u00e8 **falsa**: `*.jsonl -text`",
        "      entra col commit `{commit}` del **{data}**, dodici giorni PRIMA del 47, e".format(
            commit=v["commit"], data=v["data_commit"]),
        "      `git check-attr` d\u00e0 `text: unset`, cio\u00e8 `-text` esplicito, che scavalca",
        "      `core.autocrlf=true` attivo su questa macchina. Lo scenario di pericolo che il 47",
        "      descrive **non era possibile quando \u00e8 stato scritto**. Corollario: `*.json -text`",
        "      protegge anche `src\\paper2_v1_reference.json`, il cui `file_sha256` \u00e8 un digest **sui",
        "      byte di un file in `src\\`** \u2014 precisamente la cosa che il 47 dichiara ostaggio di git.",
        "      Cambia il meccanismo, non l'esito, e **il 47 non si riscrive**: questo lo emenda, come",
        "      il 64 emenda il 63.",
        "      **Il grado di rischio pi\u00f9 alto, dichiarato e non riparato:**",
        "      `ensemble_v2_{NGC,SGC}.jsonl`, nessuna ripresa **e** nessun identificatore. `--da` \u00e8",
        "      un selettore di popolazione, non una ripresa, e una seconda corsa appenderebbe {n}".format(
            n=v["n_seconda_corsa"]),
        "      record che nessun lettore per unione saprebbe distinguere dai primi. La Fase 4 \u00e8",
        "      chiusa e quel runner non riparte.",
        "      **La ripresa migliore del programma** \u00e8 `paper1_remap.py` righe {righe}: riprende solo".format(
            righe=v["righe_remap"]),
        "      se esistono **sia** la riga nel registro **sia** il file delle curve su disco \u2014 l'unico",
        "      runner che verifica il prodotto laterale. Va in `REPRODUCIBILITY.md` come pattern",
        "      (voce 6.7).",
        "      **Residuo dichiarato:** **{n} file `.jsonl`** sotto `results/` restano non".format(
            n=v["n_non_classificati"]),
        "      classificati \u2014 Paper 1, smoke, item \u2014 e l'uscita dello strumento resta `1` finch\u00e9 non",
        "      sono decisi. **Non** sono dichiarati fuori scopo, perch\u00e9 non sono stati aperti, e",
        "      inventare uno scopo \u00e8 l'errore che questa voce esiste per non fare: **lavoro del 6.2**,",
        "      con le due voci che il censimento ha aperto \u2014 `gate53.jsonl`, che porta tre record per",
        "      due regioni con un superamento **non marcato**, e `per_mock_*_erosion_restrict`, che va",
        "      letto per **unione** mentre la mappa di ripresa del runner \u00e8 **last-wins**.",
        "      **Che cosa NON \u00e8 stato fatto:** nessun registro riscritto, nessuna riga normalizzata,",
        "      nessuna ripresa aggiunta a un runner. I sei LF restano, le due mancanze di ripresa",
        "      restano. Cambia che sono note e dichiarate, con il file e le righe in cui si guardano.",
        "      *(Prova del censimento: `logs/censimento_v14.jsonl`, linea di base corrente.)*",
    ]
    return "\n".join(righe)


def blocco_stato(v: dict) -> str:
    righe = [
        "> **Cosa \u00e8 cambiato nell'undicesima revisione (15 settembre) \u2014 LA 6.1 \u00c8 UN CENSIMENTO CON",
        "> ECCEZIONI DICHIARATE, NON UN REQUISITO DI CONFORMIT\u00c0.** I quattro aggettivi della voce non",
        "> si verificano nello stesso posto: append-only strutturale, residuo di atomicit\u00e0 e residuo",
        "> di crash-safety si **misurano** sul registro; l'append-only **storico** richiede un prima,",
        "> quindi lo strumento **stabilisce la linea di base** \u2014 lunghezza e digest per file \u2014 e da l\u00ec",
        "> verifica che i primi *n* byte siano invariati, {n_file} file su {n_file}, zero prefissi".format(
            n_file=v["n_file"]),
        "> modificati; e **`resumable` non \u00e8 del registro, \u00e8 del runner**, che il registro corrobora",
        "> senza produrre \u2014 {n} dichiarazioni, ognuna col file e le righe di origine. **Popolazione:**".format(
            n=v["n_dichiarazioni"]),
        "> {n_file} file `.jsonl` e {n_righe} righe, **in scopo {n_file_scopo} file e {n_righe_scopo} "
        "righe**, con i".format(
            n_file=v["n_file"], n_righe=spazia(v["n_righe"]),
            n_file_scopo=v["n_file_scopo"], n_righe_scopo=spazia(v["n_righe_scopo"]),
        ),
        "> cinque tier del congelamento rientrati il 15 settembre: erano fuori per svista, ed \u00e8 ci\u00f2",
        "> che `freeze_verify` legge per dichiarare CLEAN. **L'unico FAIL era gi\u00e0 dichiarato dal",
        "> record 47** \u2014 {crlf} CRLF e {lf} LF nel ledger, stessi indici da {ra} a {ro} record: \u00e8 la".format(
            crlf=v["crlf"], lf=v["lf"], ra=v["rec_prima"], ro=v["rec_oggi"]),
        "> verifica sperimentale del \u00abnothing is rewritten\u00bb \u2014 e **il 47 \u00e8 emendato**: `*.jsonl -text`",
        "> esiste dal {data}, dodici giorni prima, quindi lo scenario di pericolo che il 47 descrive".format(
            data=v["data_commit"]),
        "> non era possibile. Cambia il meccanismo, non l'esito. **Residuo:** {n} file `.jsonl` non".format(
            n=v["n_non_classificati"]),
        "> classificati, uscita dello strumento `1`, **lavoro del 6.2**. Record 68.",
    ]
    return "\n".join(righe)


def tabella_stato(records: list, da: int = 61, a: int = RECORD_ATTESO) -> str:
    righe = [
        "### Fase 6, record %d\u2013%d" % (da, a),
        "",
        "| # | utc | item (reso dal ledger) |",
        "|---|---|---|",
    ]
    for n in range(da, a + 1):
        rec = records[n - 1]
        nr = str(rec.get("numbering_rule", ""))
        if not nr.rstrip().endswith("record %d." % n):
            raise Rifiuto("il record in posizione %d non si dichiara tale" % n)
        utc = str(rec.get("utc", ""))
        try:
            dt = datetime.fromisoformat(utc.replace("Z", "+00:00"))
        except Exception:
            raise Rifiuto("utc non leggibile nel record %d: %r" % (n, utc))
        quando = "%d %s %02d:%02d" % (dt.day, MESI[dt.month], dt.hour, dt.minute)
        item = str(rec.get("item", ""))
        if not item:
            raise Rifiuto("item assente nel record %d" % n)
        if n == a:
            righe.append("| **%d** | **%s** | **`%s`** |" % (n, quando, item))
        else:
            righe.append("| %d | %s | `%s` |" % (n, quando, item))
    righe += [
        "",
        "> Le righe sono rese dai campi `utc` e `item` del ledger, non riscritte. Il **68** chiude la",
        "> voce 6.1 della checklist; il suo contenuto sta l\u00ec e in `logs/censimento_v14.jsonl`.",
    ]
    return "\n".join(righe)


# --------------------------------------------------------------------------- #
# Costruzione dei due file nuovi
# --------------------------------------------------------------------------- #

def nuovo_checklist(testo: str, v: dict) -> str:
    if "\r" in testo:
        raise Rifiuto("checklist: trovati CR, il file era a soli LF")
    if MARCA in testo:
        raise Rifiuto("la marca %r \u00e8 gi\u00e0 in uso nella checklist" % MARCA)
    una_sola_volta(testo, A_CHK_VOCE, "6.1 della checklist")
    righe = testo.split("\n")
    idx = [i for i, r in enumerate(righe) if r.startswith("### rev. ")]
    if len(idx) != 1:
        raise Rifiuto("righe '### rev. ' trovate %d, attesa 1" % len(idx))
    if not righe[idx[0]].startswith(A_CHK_REV_PREFISSO):
        raise Rifiuto("la riga di revisione non \u00e8 la 3.26 attesa")
    righe[idx[0]] = riga_rev_checklist(v)
    testo = "\n".join(righe)
    return testo.replace(A_CHK_VOCE, voce_checklist(v), 1)


def nuovo_stato(testo: str, v: dict, records: list) -> str:
    if "\r" in testo:
        raise Rifiuto("stato: trovati CR, il file era a soli LF")
    for ancora, nome in (
        (A_STATO_REV, "revisione dello stato"),
        (A_STATO_BLOCCO, "blocco della decima revisione"),
        (A_STATO_H3, "intestazione del \u00a73"),
        (A_STATO_H4, "sottosezione record 56\u201360"),
    ):
        una_sola_volta(testo, ancora, nome)
    testo = testo.replace(
        A_STATO_REV, "**15 settembre 2026**, undicesima revisione", 1
    )
    testo = testo.replace(
        A_STATO_BLOCCO, blocco_stato(v) + "\n\n" + A_STATO_BLOCCO, 1
    )
    testo = testo.replace(
        A_STATO_H3, "## 3. Il registro degli emendamenti \u2014 %d record" % RECORD_ATTESO, 1
    )
    testo = testo.replace(
        A_STATO_H4, tabella_stato(records) + "\n\n" + A_STATO_H4, 1
    )
    return testo


# --------------------------------------------------------------------------- #
# Cancelli sugli sha e scrittura
# --------------------------------------------------------------------------- #

def cancello_sha(radice: Path, quali: dict, override: dict) -> dict:
    byte = {}
    for nome, (rel, sha_atteso, lung) in quali.items():
        p = radice / rel
        b = leggi_byte(p)
        sha = sha256(b)
        atteso = override.get(nome, sha_atteso)
        if sha != atteso or (override.get(nome) is None and len(b) != lung):
            raise Rifiuto(
                "cancello sha FALLITO su %s\n  su disco: %s  %d byte\n  atteso:   %s  %d byte"
                % (rel, sha, len(b), atteso, lung)
            )
        byte[nome] = b
    return byte


def scrivi_atomico(coppie: list, cartella_log: Path, marca_tempo: str) -> list:
    """coppie: [(Path, bytes)]. Backup scritto IN logs/, mai accanto al file."""
    cartella_log.mkdir(parents=True, exist_ok=True)
    backup = []
    for p, _ in coppie:
        b = cartella_log / ("%s.bak_%s" % (p.name, marca_tempo))
        if b.exists():
            raise Rifiuto("backup gi\u00e0 esistente: %s" % b)
        b.write_bytes(p.read_bytes())
        backup.append((p, b))
    tmp = []
    try:
        for p, dati in coppie:
            fd, nome = tempfile.mkstemp(dir=str(p.parent), prefix=".tmp_", suffix=p.suffix)
            with os.fdopen(fd, "wb") as fh:
                fh.write(dati)
            tmp.append((Path(nome), p, dati))
        fatti = []
        try:
            for t, p, dati in tmp:
                os.replace(str(t), str(p))
                fatti.append((p, dati))
        except Exception:
            for p, b in backup:
                if any(q == p for q, _ in fatti):
                    p.write_bytes(b.read_bytes())
            raise
    finally:
        for t, _, _ in tmp:
            if t.exists():
                t.unlink()
    return backup


# --------------------------------------------------------------------------- #
# Sottocomandi
# --------------------------------------------------------------------------- #

def prepara(radice: Path, override: dict) -> tuple:
    byte = cancello_sha(radice, ANCORE, override)
    records = leggi_ledger(radice / ANCORE["ledger"][0])
    rec = records[-1]
    cancello_record(rec)
    v = estrai(rec)
    chk = byte["checklist"].decode("utf-8")
    sta = byte["stato"].decode("utf-8")
    chk_nuovo = nuovo_checklist(chk, v)
    sta_nuovo = nuovo_stato(sta, v, records)
    if chk_nuovo == chk or sta_nuovo == sta:
        raise Rifiuto("una delle due patch non cambia nulla")
    return v, chk, sta, chk_nuovo.encode("utf-8"), sta_nuovo.encode("utf-8")


def cmd_dryrun(args) -> int:
    radice = Path(args.radice)
    override = {"ledger": args.sha_ledger, "checklist": args.sha_checklist, "stato": args.sha_stato}
    override = dict((k, x) for k, x in override.items() if x)
    v, chk, sta, chk_b, sta_b = prepara(radice, override)
    for nome, vecchio, nuovo in (
        ("checklist_paper2.md", chk, chk_b.decode("utf-8")),
        ("paper2_stato.md", sta, sta_b.decode("utf-8")),
    ):
        print("\n=== %s ===" % nome)
        d = difflib.unified_diff(
            vecchio.split("\n"), nuovo.split("\n"),
            fromfile="prima", tofile="dopo", lineterm="", n=1,
        )
        for riga in d:
            print(riga)
    print("\nsha256 che risulterebbero:")
    print("  checklist_paper2.md  %s  %d byte" % (sha256(chk_b), len(chk_b)))
    print("  paper2_stato.md      %s  %d byte" % (sha256(sta_b), len(sta_b)))
    print("\nDRYRUN: nessun file scritto.")
    return 0


def cmd_apply(args) -> int:
    radice = Path(args.radice)
    override = {"ledger": args.sha_ledger, "checklist": args.sha_checklist, "stato": args.sha_stato}
    override = dict((k, x) for k, x in override.items() if x)
    if override:
        print("ATTENZIONE: cancello sha scavalcato per %s" % ", ".join(sorted(override)))
    v, chk, sta, chk_b, sta_b = prepara(radice, override)
    p_chk = radice / ANCORE["checklist"][0]
    p_sta = radice / ANCORE["stato"][0]
    marca_tempo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = scrivi_atomico(
        [(p_chk, chk_b), (p_sta, sta_b)], radice / args.logs, marca_tempo
    )
    esito = 0
    for p, atteso in ((p_chk, chk_b), (p_sta, sta_b)):
        sha = sha256(p.read_bytes())
        if sha != sha256(atteso):
            print("FAIL: %s scritto ma lo sha non combacia" % p.name)
            esito = 1
        else:
            print("scritto  %s  %s  %d byte" % (p.name, sha, len(atteso)))
    for p, b in backup:
        print("backup   %s" % b)
    if not override:
        for nome, p in (("checklist", p_chk), ("stato", p_sta)):
            if SHA_DOPO[nome] != "DA_MISURARE" and sha256(p.read_bytes()) != SHA_DOPO[nome]:
                print("FAIL: %s non combacia con SHA_DOPO" % p.name)
                esito = 1
    print("APPLY: %s" % ("OK" if esito == 0 else "FALLITO"))
    return esito


def cmd_verify(args) -> int:
    radice = Path(args.radice)
    esito = 0
    for nome in ("checklist", "stato"):
        rel = ANCORE[nome][0]
        sha = sha256(leggi_byte(radice / rel))
        atteso = SHA_DOPO[nome]
        stato = "OK" if sha == atteso else ("? (SHA_DOPO non misurato)" if atteso == "DA_MISURARE" else "FAIL")
        if stato == "FAIL":
            esito = 1
        print("%-22s %s  %s" % (Path(rel).name, sha, stato))
    bak = list((radice / "src").glob("*.bak_*")) + list(
        (radice / "papers" / "paper2").glob("*.bak_*")
    )
    print("`.bak` in src/ e papers/paper2/: %d (atteso 0)" % len(bak))
    if bak:
        esito = 1
    print("VERIFY: %s" % ("OK" if esito == 0 else "FALLITO"))
    return esito


# --------------------------------------------------------------------------- #
# Selftest
# --------------------------------------------------------------------------- #

def _finto_record(n: int, item: str, utc: str) -> dict:
    return {
        "item": item,
        "utc": utc,
        "numbering_rule": "This is record %d." % n,
        "rules": {"marker": "emendamento-%d-finto" % n},
    }


def _record_68_finto() -> dict:
    return {
        "amends_records": [47],
        "counts_after": {"DOCUMENTED_AMENDMENTS": 68},
        "item": "6.1/censimento_finto",
        "utc": "2026-09-15T12:10:27+00:00",
        "numbering_rule": "Questo e' il record 68.",
        "rettifica_del_record_47": {
            "cosa_e_falso": "`*.jsonl -text` dal commit 684d1f3 del 25 agosto 2026 — dodici giorni prima. core.autocrlf, text: unset."
        },
        "rules": {
            "marker": "emendamento-68-censimento-dei-registri-voce-6-1",
            "companion_documents": "checklist_paper2.md; paper2_stato.md",
        },
        "new_value": {
            "misura": "121 file .jsonl, 78 067 righe; in scopo 53 file, 67 915 righe. append_strutturale e crashsafe_residuo PASS.",
            "resumable_ridefinita": "53 righe, ognuna col file e le righe di origine. ripresa_dal_registro (16), na_una_passata (23), na_scansione (8), nessuna_ripresa_id (4), nessuna_ripresa_senza_id (2), da_leggere (0). paper2_runner_fase3_mock.py righe 691-738.",
            "unico_FAIL": "61 CRLF e 6 LF; era 40/6 su 46 record, e' 61/6 su 67 oggi, con gli stessi indici 8 9 10 11 13 14.",
            "residuo_dichiarato": "67 file .jsonl sotto results/ restano non classificati.",
            "il_grado_di_rischio_piu_alto": "ensemble_v2_{NGC,SGC}.jsonl: una seconda corsa appenderebbe 2000 record. cachedelta_manifest_ e ensemble_v1_manifest_ e gate53.jsonl e per_mock_*_erosion_restrict.",
            "la_ripresa_migliore_del_programma": "paper1_remap.py righe 512-516. REPRODUCIBILITY.md.",
        },
    }


def _albero(base: Path, chk: str, sta: str, records: list) -> None:
    (base / "src").mkdir(parents=True, exist_ok=True)
    (base / "papers" / "paper2").mkdir(parents=True, exist_ok=True)
    (base / "logs").mkdir(parents=True, exist_ok=True)
    linee = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    (base / "src" / "paper2_v1_amendments.jsonl").write_bytes(linee.encode("utf-8"))
    (base / "papers" / "paper2" / "checklist_paper2.md").write_bytes(chk.encode("utf-8"))
    (base / "papers" / "paper2" / "paper2_stato.md").write_bytes(sta.encode("utf-8"))


def _shas(base: Path) -> dict:
    return dict(
        (nome, sha256((base / rel).read_bytes()))
        for nome, (rel, _, _) in ANCORE.items()
    )


CHK_FIXTURE = "\n".join([
    "# Paper 2 — Checklist",
    A_CHK_REV_PREFISSO + " coda della riga",
    "",
    "> Base documentale.",
    "",
    A_CHK_VOCE,
    "- [ ] **6.2** Ogni numero tracciabile.",
    "",
])

STA_FIXTURE = "\n".join([
    "# Paper 2 — stato consolidato",
    "### Indice unico — aggiornato " + A_STATO_REV,
    "",
    A_STATO_BLOCCO + " testo.",
    "> seconda riga.",
    "",
    A_STATO_H3,
    "",
    A_STATO_H4,
    "",
    "| # | contenuto |",
    "",
])


def cmd_selftest(args) -> int:
    ok, ko = 0, 0

    def controlla(nome, cond):
        nonlocal ok, ko
        if cond:
            ok += 1
        else:
            ko += 1
            print("  FAIL  %s" % nome)

    def rifiuta(nome, fn):
        nonlocal ok, ko
        try:
            fn()
        except Rifiuto:
            ok += 1
            return
        except Exception as e:
            ko += 1
            print("  FAIL  %s (eccezione sbagliata: %r)" % (nome, e))
            return
        ko += 1
        print("  FAIL  %s (non ha rifiutato)" % nome)

    # --- estrazione dal record finto -------------------------------------- #
    rec = _record_68_finto()
    v = estrai(rec)
    controlla("estrazione: n_file 121", v["n_file"] == 121)
    controlla("estrazione: n_righe 78067", v["n_righe"] == 78067)
    controlla("estrazione: in scopo 53 file", v["n_file_scopo"] == 53)
    controlla("estrazione: in scopo 67915 righe", v["n_righe_scopo"] == 67915)
    controlla("estrazione: 53 dichiarazioni", v["n_dichiarazioni"] == 53)
    controlla("estrazione: sei modi", len(v["modi"]) == 6)
    controlla("estrazione: somma dei modi", sum(v["modi"].values()) == 53)
    controlla("estrazione: CRLF 61", v["crlf"] == 61)
    controlla("estrazione: LF 6", v["lf"] == 6)
    controlla("estrazione: profilo prima 40/6", v["prof_prima"] == "40/6")
    controlla("estrazione: record prima 46", v["rec_prima"] == 46)
    controlla("estrazione: profilo oggi 61/6", v["prof_oggi"] == "61/6")
    controlla("estrazione: record oggi 67", v["rec_oggi"] == 67)
    controlla("estrazione: indici", v["indici"] == "8 9 10 11 13 14")
    controlla("estrazione: non classificati 67", v["n_non_classificati"] == 67)
    controlla("estrazione: commit", v["commit"] == "684d1f3")
    controlla("estrazione: data commit", v["data_commit"] == "25 agosto 2026")
    controlla("estrazione: righe chiave", v["righe_chiave"] == "691-738")
    controlla("estrazione: righe remap", v["righe_remap"] == "512-516")
    controlla("spazia()", spazia(78067) == "78 067" and spazia(915) == "915")

    # numeri nel testo, non a mano
    testo = voce_checklist(v)
    controlla("voce: porta 78 067", "78 067" in testo)
    controlla("voce: porta 67 915", "67 915" in testo)
    controlla("voce: porta la marca", MARCA in testo)
    controlla("voce: casella spuntata", testo.startswith("- [x] "))
    controlla("voce: nomina il record 68", "record 68" in testo)
    controlla("voce: nomina il 47", "record 47" in testo)
    controlla("voce: consegna il residuo al 6.2", "lavoro del 6.2" in testo)
    controlla("voce: continuazioni indentate",
              all(r.startswith("      ") for r in testo.split("\n")[1:]))
    controlla("voce: nessuna riga vuota", "" not in testo.split("\n"))
    controlla("voce: niente apostrofo-accento", " e' " not in testo and "proprieta'" not in testo)
    controlla("blocco stato: prefisso >",
              all(r.startswith(">") for r in blocco_stato(v).split("\n")))

    # record che non passano
    for nome, mod in (
        ("record: numbering_rule sbagliata", {"numbering_rule": "This is record 67."}),
        ("record: item non 6.1", {"item": "6.2/altro"}),
        ("record: amends sbagliato", {"amends_records": [46]}),
        ("record: counts_after sbagliato", {"counts_after": {"DOCUMENTED_AMENDMENTS": 67}}),
    ):
        r = dict(_record_68_finto())
        r.update(mod)
        rifiuta(nome, lambda r=r: cancello_record(r))

    r = _record_68_finto()
    r["rules"] = {"marker": "emendamento-68-x", "companion_documents": "solo_uno.md"}
    rifiuta("record: documenti compagni mancanti", lambda: cancello_record(r))

    r = _record_68_finto()
    del r["new_value"]["misura"]
    rifiuta("estrazione: misura assente", lambda: estrai(r))

    r = _record_68_finto()
    r["new_value"]["resumable_ridefinita"] = "53 righe, ognuna col file e le righe di origine. ripresa_dal_registro (16), na_una_passata (23)."
    rifiuta("estrazione: modi incompleti", lambda: estrai(r))

    r = _record_68_finto()
    r["new_value"]["resumable_ridefinita"] = r["new_value"]["resumable_ridefinita"].replace("(23)", "(24)")
    rifiuta("estrazione: modi che non sommano", lambda: estrai(r))

    r = _record_68_finto()
    r["new_value"]["la_ripresa_migliore_del_programma"] = "paper1_remap.py, nessun intervallo. REPRODUCIBILITY.md"
    rifiuta("verifica letterale: 512-516 assente", lambda: estrai(r))

    # --- pipeline su un albero finto -------------------------------------- #
    records = [_finto_record(i, "x/y_%d" % i, "2026-09-0%dT01:02:03+00:00" % (i % 9 + 1))
               for i in range(1, 61)]
    records += [
        _finto_record(61, "0.13/6.8-kref/input_hash", "2026-09-12T16:39:49+00:00"),
        _finto_record(62, "6.8/provenienza_pk_matrix", "2026-09-12T16:39:49+00:00"),
        _finto_record(63, "6.8/D6_chiuso", "2026-09-13T14:30:48+00:00"),
        _finto_record(64, "5.5/correzione_del_63", "2026-09-13T15:17:05+00:00"),
        _finto_record(65, "6.9/censimento_dei_verdetti", "2026-09-14T06:34:32+00:00"),
        _finto_record(66, "6.9/SGC_PRED_risolta", "2026-09-14T14:41:37+00:00"),
        _finto_record(67, "6.9/rettifica_dei_conteggi", "2026-09-14T19:27:47+00:00"),
        _record_68_finto(),
    ]

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _albero(base, CHK_FIXTURE, STA_FIXTURE, records)
        ov = _shas(base)

        class A:
            radice = str(base)
            logs = "logs"
            sha_ledger = ov["ledger"]
            sha_checklist = ov["checklist"]
            sha_stato = ov["stato"]

        controlla("fixture: scritta a byte, senza CR",
                  b"\r" not in (base / "papers/paper2/checklist_paper2.md").read_bytes())
        controlla("dryrun: esce 0", cmd_dryrun(A()) == 0)
        prima_chk = (base / "papers/paper2/checklist_paper2.md").read_bytes()
        controlla("dryrun: non scrive", sha256(prima_chk) == ov["checklist"])
        controlla("dryrun: nessun backup", not list((base / "logs").glob("*.bak_*")))

        controlla("apply: esce 0", cmd_apply(A()) == 0)
        chk_dopo = (base / "papers/paper2/checklist_paper2.md").read_text(encoding="utf-8")
        sta_dopo = (base / "papers/paper2/paper2_stato.md").read_text(encoding="utf-8")
        controlla("apply: 6.1 spuntata", "- [x] **%s 6.1" % MARCA in chk_dopo)
        controlla("apply: vecchia 6.1 sparita", A_CHK_VOCE not in chk_dopo)
        controlla("apply: rev 3.27", "### rev. 3.27" in chk_dopo)
        controlla("apply: rev 3.26 sparita", "rev. 3.26" not in chk_dopo)
        controlla("apply: stato undicesima", "undicesima revisione" in sta_dopo)
        controlla("apply: stato decima sparita", A_STATO_REV not in sta_dopo)
        controlla("apply: §3 a 68", "emendamenti — 68 record" in sta_dopo)
        controlla("apply: tabella Fase 6", "### Fase 6, record 61–68" in sta_dopo)
        controlla("apply: riga 68 in grassetto", "| **68** |" in sta_dopo)
        controlla("apply: data resa dal ledger", "| 61 | 12 set 16:39 |" in sta_dopo)
        controlla("apply: blocco decima conservato", A_STATO_BLOCCO in sta_dopo)
        controlla("apply: sottosezione 56–60 conservata", A_STATO_H4 in sta_dopo)
        controlla("apply: nessun CR introdotto",
                  b"\r" not in (base / "papers/paper2/paper2_stato.md").read_bytes())
        controlla("apply: ledger non toccato",
                  sha256((base / "src/paper2_v1_amendments.jsonl").read_bytes()) == ov["ledger"])
        bak = sorted((base / "logs").glob("*.bak_*"))
        controlla("apply: due backup in logs/", len(bak) == 2)
        controlla("apply: backup fedele",
                  any(sha256(b.read_bytes()) == ov["checklist"] for b in bak))
        controlla("apply: nessun .bak accanto ai file",
                  not list((base / "papers/paper2").glob("*.bak_*"))
                  and not list((base / "src").glob("*.bak_*")))
        controlla("apply: nessun tmp residuo", not list((base / "papers/paper2").glob(".tmp_*")))

        # seconda applicazione: il cancello sha deve rifiutare
        rifiuta("apply due volte: rifiutata", lambda: cmd_apply(A()))

    # ancore assenti o doppie
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _albero(base, CHK_FIXTURE.replace(A_CHK_VOCE, "- [ ] **6.1** altro testo"),
                STA_FIXTURE, records)
        ov = _shas(base)

        class B:
            radice = str(base)
            logs = "logs"
            sha_ledger = ov["ledger"]
            sha_checklist = ov["checklist"]
            sha_stato = ov["stato"]

        rifiuta("ancora 6.1 assente", lambda: cmd_apply(B()))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _albero(base, CHK_FIXTURE + "\n" + A_CHK_VOCE + "\n", STA_FIXTURE, records)
        ov = _shas(base)

        class C:
            radice = str(base)
            logs = "logs"
            sha_ledger = ov["ledger"]
            sha_checklist = ov["checklist"]
            sha_stato = ov["stato"]

        rifiuta("ancora 6.1 doppia", lambda: cmd_apply(C()))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _albero(base, CHK_FIXTURE.replace("# Paper 2", MARCA + " # Paper 2"), STA_FIXTURE, records)
        ov = _shas(base)

        class D:
            radice = str(base)
            logs = "logs"
            sha_ledger = ov["ledger"]
            sha_checklist = ov["checklist"]
            sha_stato = ov["stato"]

        rifiuta("marca gia' in uso", lambda: cmd_apply(D()))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _albero(base, CHK_FIXTURE, STA_FIXTURE, records)

        class E:
            radice = str(base)
            logs = "logs"
            sha_ledger = None
            sha_checklist = None
            sha_stato = None

        rifiuta("cancello sha: ancore della consegna su fixture", lambda: cmd_apply(E()))
        controlla("cancello sha: nessuna scrittura dopo il rifiuto",
                  not list((base / "logs").glob("*.bak_*")))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _albero(base, CHK_FIXTURE, STA_FIXTURE, records[:-1])
        ov = _shas(base)

        class F:
            radice = str(base)
            logs = "logs"
            sha_ledger = ov["ledger"]
            sha_checklist = ov["checklist"]
            sha_stato = ov["stato"]

        rifiuta("ledger a 67 record", lambda: cmd_apply(F()))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        r = list(records)
        r[-1] = dict(r[-1], item="6.2/altro")
        _albero(base, CHK_FIXTURE, STA_FIXTURE, r)
        ov = _shas(base)

        class G:
            radice = str(base)
            logs = "logs"
            sha_ledger = ov["ledger"]
            sha_checklist = ov["checklist"]
            sha_stato = ov["stato"]

        rifiuta("ultimo record non e' della 6.1", lambda: cmd_apply(G()))

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("comando", choices=["selftest", "dryrun", "apply", "verify"])
    ap.add_argument("--radice", default=".", help="radice del repo (default: .)")
    ap.add_argument("--logs", default="logs", help="cartella dei backup (default: logs)")
    ap.add_argument("--sha-ledger", default=None, help="scavalca il cancello sha (solo selftest)")
    ap.add_argument("--sha-checklist", default=None)
    ap.add_argument("--sha-stato", default=None)
    args = ap.parse_args(argv)
    fn = {
        "selftest": cmd_selftest,
        "dryrun": cmd_dryrun,
        "apply": cmd_apply,
        "verify": cmd_verify,
    }[args.comando]
    try:
        return fn(args)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e)
        print("Nessun file e' stato scritto.")
        return 2


if __name__ == "__main__":
    sys.exit(main())

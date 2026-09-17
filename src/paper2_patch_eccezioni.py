#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_eccezioni.py v1.1 — porta `logs\\eccezioni_rilascio.json` da 14 a 18 voci,
o a 22 con --con-record71 (record 74): le quattro ragioni del 71 portano il digest di cio' che
la citazione intendeva, MISURATO dal disco e da git, non scritto a mano, e corregge
la ragione del protocollo, che dopo il record 73 dice il falso.

PERCHE'. Il censimento del rilascio a 73 record da' `citati_non_esclusi` FAIL su quattro
percorsi. Nessuno dei quattro e' una decisione nuova:
  - `logs/deposito_zenodo.json`     evidence del record 73, e `logs/` e' fuori (record 70 §ii);
  - `papers/paper2/checklist_paper2.md` e `papers/paper2/paper2_stato.md`, citati dal record 73
    come documenti compagni, e `papers/` e' fuori (record 70 §i);
  - `results/paper2/remote_audit.json`, citato dal record 72 ed escluso PER NOME da
    `.gitignore` perche' rigenerabile, come dichiara il commit 73c8213.

E la voce di `papers/paper2/paper2_prereg_v1.md` chiude con «L'ancoraggio esterno e' il version
DOI …, la cui corrispondenza coi byte su disco resta da verificare». E' verificata: il deposito
non contiene il protocollo in nessuna versione (record 73, 1068 membri esaminati). Una frase
falsa dentro il file che dichiara le eccezioni e' la stessa classe del §5 di REPRODUCIBILITY.md.

DIGEST: MISURATI, non scritti a mano. Per `logs/deposito_zenodo.json` la voce porta sha256 e
byte letti dal disco. Per checklist, stato e `remote_audit.json` la voce NON porta digest, e
dice perche': i primi due si rivedono ogni sessione e il terzo e' rigenerabile, quindi un'ancora
per byte sarebbe stale al primo patcher — l'ancoraggio di quei tre e' il record che li nomina.

I QUATTRO PERCORSI DEL RECORD 71 (`citati_esistono` FAIL) NON sono qui per default: sono una
decisione di protocollo, e quattro eccezioni sono quattro decisioni. Con `--con-record71` si
aggiungono, ma solo se il ledger porta un record che le dichiara (marker
`emendamento-74-…`): se non c'e', lo strumento rifiuta e dice di scriverlo prima.

CANCELLI:
  1. sha256 e dimensione del file uguali all'ancora (`e8d34dbc…`, 5 159 byte), 14 voci;
  2. ledger a >= 73 record, col marker del record 73 al 73;
  3. le chiavi nuove non devono esistere gia'; la frase da correggere deve esistere esattamente
     una volta ed essere assente dopo;
  4. ogni ragione >= 10 caratteri, che e' il rifiuto che il censimento applica;
  5. i percorsi delle voci nuove devono esistere sul disco (una eccezione che dichiara un file
     inesistente sposterebbe il FAIL da un verdetto all'altro);
  6. scrittura atomica, byte riletti, JSON riletto e confrontato voce per voce. Fine riga LF,
     chiavi ordinate, `indent=2` come il file originale.

Uso:
  python src\\paper2_patch_eccezioni.py selftest
  python src\\paper2_patch_eccezioni.py dry-run
  python src\\paper2_patch_eccezioni.py apply
  python src\\paper2_patch_eccezioni.py verify
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile

FILE = os.path.join("logs", "eccezioni_rilascio.json")
LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")

ANCORA_SHA = "e8d34dbce3daa46b88ed767bf2c7320ae0b5f35eec8642b3eab3fb18c7f6aa0b"
ANCORA_BYTE = 5159
ANCORA_VOCI = 14

MARKER_73 = "emendamento-73-il-deposito-non-contiene-il-protocollo"
MARKER_74 = "emendamento-74-"

PREREG = "papers/paper2/paper2_prereg_v1.md"
FRASE_FALSA = ("L'ancoraggio esterno e' il version DOI 10.5281/zenodo.22148444, la cui "
               "corrispondenza coi byte su disco resta da verificare.")
FRASE_NUOVA = ("L'ancoraggio esterno NON esiste: misurato il 17 set 2026, il deposito "
               "10.5281/zenodo.22148444 non contiene questo documento in nessuna versione, e "
               "nemmeno le altre tre versioni del concept DOI lo contengono — 1068 membri "
               "esaminati, zero (record 73). Il version DOI ancora l'archivio della pipeline, "
               "non il protocollo. Fino al deposito della Fase 7 l'unico ancoraggio e' quello "
               "per byte del record 72.")

MISURATI = {"logs/deposito_zenodo.json"}

NUOVE = {
    "logs/deposito_zenodo.json":
        "FUORI dal rilascio: logs/ e' sentiero di lavoro (record 70 §ii). E' l'evidence del "
        "record 73 — la misura del deposito 10.5281/zenodo.22148444: ogni file di ogni versione "
        "del concept DOI scaricato, ogni archivio aperto, 1068 membri esaminati, zero col "
        "protocollo. Rifatta in qualunque momento con "
        "`python src/paper2_append_amend73.py misura-deposito`, che la riconfronta campo per "
        "campo con cio' che il record 73 dichiara e rifiuta se il deposito e' cambiato. "
        "Ancorato per byte: sha256 {sha}, {byte} byte al 17 set 2026.",
    "papers/paper2/checklist_paper2.md":
        "FUORI dal versionamento, decisione del record 70 §i, come tutto papers/. Citato dal "
        "record 73 fra i documenti compagni, insieme a paper2_stato.md e REPRODUCIBILITY.md. "
        "NESSUN DIGEST QUI, per scelta: la checklist si rivede a ogni sessione — rev. 3.29 al 17 "
        "set 2026 — e un'ancora per byte sarebbe stale al primo patcher. Cio' che la ancora e' "
        "il record che la nomina, piu' l'intestazione di revisione dentro il documento.",
    "papers/paper2/paper2_stato.md":
        "FUORI dal versionamento, decisione del record 70 §i, come tutto papers/. Citato dal "
        "record 73 fra i documenti compagni. NESSUN DIGEST QUI, per la stessa ragione della "
        "checklist: e' l'indice unico di cio' che e' aperto e chiuso e cambia a ogni revisione "
        "(tredicesima al 17 set 2026). Lo ancora il record che lo nomina.",
    "results/paper2/remote_audit.json":
        "Escluso PER NOME da .gitignore, non da una regola di cartella: e' RIGENERABILE, come "
        "dichiara il commit 73c8213 («ignora remote_audit.json, rigenerabile»). Citato dal "
        "record 72, che se ne serve per un fatto preciso: registra `\"git\": null` per la radice "
        "D:/projects/cauchy_3.0, cioe' che quell'albero non e' un repository e non aggiunge "
        "storia alla copia del protocollo che contiene. NESSUN DIGEST QUI: un file rigenerato "
        "cambia byte per costruzione, e ancorarlo darebbe un MISMATCH alla prima rigenerazione.",
}

RECORD71 = {
    "src/paper2_item13rev2.py":
        "ECCEZIONE DICHIARATA DAL RECORD 74. Errore di trascrizione dichiarato dal record 71: "
        "manca l'underscore. Lo strumento e' src/paper2_item13_rev2.py, {item13}, e produce "
        "results/paper2/item13rev2_<REG>.jsonl SENZA underscore — da cui la confusione; "
        "src/paper2_item12b_wbar.py lo rilegge. La grafia citata dal record 27 non e' mai stata "
        "aggiunta in nessun commit di nessun ramo, misurato sulla storia degli `A` su --all. Il "
        "ledger e' append-only e la citazione resta: la correzione e' il record 71, l'ancora "
        "e' questa.",
    "src/paper2_letture_1punto.py":
        "ECCEZIONE DICHIARATA DAL RECORD 74, e la sola delle quattro SENZA ancora, perche' non "
        "c'e' niente da ancorare: lo strumento non e' mai esistito. Due metri indipendenti, "
        "misurati il 17 set 2026 — la storia degli `A` su tutti i rami non lo contiene, e una "
        "camminata su D:/projects non trova nessun file il cui nome contenga «letture». Il "
        "lavoro che il record 54 gli attribuisce lo fa src/paper2_passata_1punto.py, {passata}, "
        "con selftest 43/43; il «31/31» accostatogli e' di src/paper2_boxcox_v2.py.",
    "results/phase8_test2_permock.csv":
        "ECCEZIONE DICHIARATA DAL RECORD 74. Rimosso PER CAUSA dal commit 352e024 (voce P-A1, "
        "emendamento 11), recuperabile da 352e024^: {permock}. E' BYTE-IDENTICO al "
        "sopravvissuto results/phase8_test2_permock_hodfit.csv — confrontati byte per byte il 17 "
        "set 2026 — quindi cio' che il commit ha rimosso e' un'ETICHETTA e non un dato: il nome "
        "`permock` prometteva la baseline test2 e il contenuto e' il sottoinsieme HOD-refit "
        "(35304.6 +/- 1033.0, N=200). Il dato sopravvive una volta, sotto il nome che lo "
        "descrive. Storia del percorso: e17da7a (A), 684d1f3 (M), 352e024 (D).",
    "data/raw/quijote/3D_cubes/latin_hypercube_nwLH_params.txt":
        "ECCEZIONE DICHIARATA DAL RECORD 74. Grafia che omette la cartella intermedia "
        "latin_hypercube_nwLH/ e quindi non risolve: il record 43 esiste per dichiarare "
        "quell'assenza. Il file vero e' "
        "data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt, "
        "{params}, unica copia sotto data/raw/quijote (cercata per nome su tutto l'albero il 17 "
        "set 2026), e porta lo stesso digest che il record 43 dichiara: la citazione sbagliata e "
        "il file ancorato sono la stessa cosa, e l'unica differenza e' la grafia. Dato esterno "
        "Quijote, non nostro da redistribuire.",
}

# I segnaposto delle quattro ragioni sopra: misurati dal disco o da git, non scritti a mano.
MISURE_71 = {
    "{item13}": ("disco", "src/paper2_item13_rev2.py"),
    "{passata}": ("disco", "src/paper2_passata_1punto.py"),
    "{params}": ("disco",
                 "data/raw/quijote/3D_cubes/latin_hypercube_nwLH/"
                 "latin_hypercube_nwLH_params.txt"),
    "{permock}": ("git", "352e024^:results/phase8_test2_permock.csv"),
}

MIN_RAGIONE = 10


class PatchError(Exception):
    pass


# ---------------------------------------------------------------------------

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def carica(path, controlla_ancora=True):
    dati = read_bytes(path)
    if controlla_ancora:
        got = (sha256_bytes(dati), len(dati))
        if got != (ANCORA_SHA, ANCORA_BYTE):
            raise PatchError(
                "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
                "  O il file non e' quello a 14 voci, o la patch e' gia' applicata."
                % (path, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
    try:
        voci = json.loads(dati.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise PatchError("%s non e' JSON leggibile: %r" % (path, e))
    if not isinstance(voci, dict):
        raise PatchError("%s non e' un oggetto JSON ma %s: il censimento legge un dizionario "
                         "percorso -> ragione" % (path, type(voci).__name__))
    if controlla_ancora and len(voci) != ANCORA_VOCI:
        raise PatchError("%s: %d voci, attese %d" % (path, len(voci), ANCORA_VOCI))
    return voci


def cancello_ledger(path, con_record71):
    if not os.path.exists(path):
        raise PatchError("ledger assente: %s" % path)
    righe = [l for l in read_bytes(path).split(b"\n") if l.strip()]
    if len(righe) < 73:
        raise PatchError("ledger a %d record: le voci nuove citano il record 73, che deve "
                         "esistere prima" % len(righe))
    r73 = json.loads(righe[72].rstrip(b"\r").decode("utf-8"))
    if str(r73.get("rules", {}).get("marker", "")) != MARKER_73:
        raise PatchError("il record 73 non porta il marker atteso: %r"
                         % r73.get("rules", {}).get("marker"))
    esiti = ["ledger a %d record, il 73 col suo marker" % len(righe)]
    if con_record71:
        marker = None
        for ln in righe[73:]:
            rec = json.loads(ln.rstrip(b"\r").decode("utf-8"))
            m = str(rec.get("rules", {}).get("marker", ""))
            if m.startswith(MARKER_74):
                marker = m
                break
        if marker is None:
            raise PatchError(
                "--con-record71 aggiunge QUATTRO ECCEZIONI, che sono quattro DECISIONI di\n"
                "  protocollo: il ledger deve portarle, con un record 74 (marker\n"
                "  `emendamento-74-…`). Scriverlo prima, o eseguire senza --con-record71 per\n"
                "  le quattro voci che seguono dai record 70, 72 e 73.")
        esiti.append("record 74 presente (%s): le quattro eccezioni del 71 sono dichiarate"
                     % marker)
    return esiti


def misura_git(radice, spec):
    import subprocess
    try:
        r = subprocess.run(["git", "show", spec], cwd=radice, capture_output=True)
    except FileNotFoundError:
        raise PatchError("git non trovato nel PATH")
    if r.returncode != 0:
        raise PatchError("git show %s uscito %d" % (spec, r.returncode))
    return sha256_bytes(r.stdout), len(r.stdout)


def risolvi_segnaposto(ragione, radice, richiedi_disco=True):
    """Sostituisce i {segnaposto} con «sha256 …, N byte» MISURATI. Se la misura non e'
    disponibile lo strumento rifiuta: una ragione con un digest inventato e' peggio di una
    senza."""
    for chiave, (dove, spec) in MISURE_71.items():
        if chiave not in ragione:
            continue
        if not richiedi_disco:
            sha, byte = "0" * 64, 0
        elif dove == "git":
            sha, byte = misura_git(radice, spec)
        else:
            sha, byte = misura(radice, spec)
        ragione = ragione.replace(chiave, "sha256 %s, %d byte" % (sha, byte))
    return ragione


def misura(radice, percorso):
    p = os.path.join(radice, percorso.replace("/", os.sep))
    if not os.path.isfile(p):
        raise PatchError("il percorso di una voce nuova non e' sul disco: %s\n  Un'eccezione "
                         "su un file inesistente spostera' il FAIL da citati_non_esclusi a "
                         "citati_esistono, non lo chiude." % percorso)
    dati = read_bytes(p)
    return sha256_bytes(dati), len(dati)


def costruisci(voci, radice, con_record71, richiedi_disco=True):
    fuori = dict(voci)
    esiti = []

    if PREREG not in fuori:
        raise PatchError("la voce del protocollo non c'e': %s" % PREREG)
    testo = fuori[PREREG]
    if testo.count(FRASE_FALSA) != 1:
        raise PatchError("la frase da correggere non compare esattamente una volta nella voce "
                         "del protocollo: il file non e' quello atteso")
    fuori[PREREG] = testo.replace(FRASE_FALSA, FRASE_NUOVA, 1)
    esiti.append("voce del protocollo: frase sul DOI corretta (record 73)")

    nuove = dict(NUOVE)
    if con_record71:
        nuove.update(RECORD71)
    for percorso in sorted(nuove):
        if percorso in fuori:
            raise PatchError("la voce %s esiste gia': patch gia' applicata?" % percorso)
        ragione = nuove[percorso]
        if "{sha}" in ragione:
            if not richiedi_disco:
                sha, byte = "0" * 64, 0
            else:
                sha, byte = misura(radice, percorso)
            ragione = ragione.format(sha=sha, byte=byte)
            esiti.append("%s: digest MISURATO dal disco (%s…, %d byte)"
                         % (percorso, sha[:16], byte))
        elif percorso in RECORD71:
            prima = ragione
            ragione = risolvi_segnaposto(ragione, radice, richiedi_disco)
            if percorso == "src/paper2_letture_1punto.py":
                esiti.append("%s: nessuna ancora, e i due metri dell'assenza sono nella "
                             "ragione" % percorso)
            else:
                if ragione == prima:
                    raise PatchError("la ragione di %s non porta nessun segnaposto da "
                                     "misurare: e' un'eccezione senza ancora" % percorso)
                esiti.append("%s: ancora MISURATA di cio' che la citazione intendeva"
                             % percorso)
        else:
            if richiedi_disco and percorso in MISURATI:
                raise PatchError("incoerenza interna: %s dovrebbe portare un digest" % percorso)
            if richiedi_disco:
                misura(radice, percorso)
            esiti.append("%s: nessun digest, e la ragione dice perche'" % percorso)
        if len(ragione) < MIN_RAGIONE:
            raise PatchError("ragione troppo corta per %s: il censimento la rifiuta" % percorso)
        fuori[percorso] = ragione

    for k, v in fuori.items():
        if not isinstance(v, str) or len(v) < MIN_RAGIONE:
            raise PatchError("ragione mancante o troppo corta per %s" % k)
    testo_tutto = json.dumps(fuori, ensure_ascii=False)
    if FRASE_FALSA in testo_tutto:
        raise PatchError("la frase falsa sopravvive nel file nuovo")
    restati = [k for k in MISURE_71 if k in testo_tutto]
    if restati:
        raise PatchError("segnaposto non sostituiti: %r" % restati)
    return fuori, esiti


def serializza(voci):
    return (json.dumps(voci, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_atomic(path, dati):
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".patch_ecc_", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dati)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    riletto = read_bytes(path)
    if riletto != dati:
        raise PatchError("%s: i byte riletti non sono quelli scritti" % path)
    return json.loads(riletto.decode("utf-8"))


# ---------------------------------------------------------------------------

def cmd_dry_run(a):
    voci = carica(a.file)
    esiti = cancello_ledger(a.ledger, a.con_record71)
    nuove, e2 = costruisci(voci, a.radice, a.con_record71)
    for x in esiti + e2:
        print("  [ok] %s" % x)
    dati = serializza(nuove)
    print("\nvoci: %d -> %d" % (len(voci), len(nuove)))
    for k in sorted(set(nuove) - set(voci)):
        print("  + %s" % k)
    print("\nfile nuovo: %s  %d byte" % (sha256_bytes(dati), len(dati)))
    print("nessun byte scritto.")
    return 0


def cmd_apply(a):
    voci = carica(a.file)
    esiti = cancello_ledger(a.ledger, a.con_record71)
    nuove, e2 = costruisci(voci, a.radice, a.con_record71)
    dati = serializza(nuove)
    riletto = write_atomic(a.file, dati)
    if riletto != nuove:
        raise PatchError("il JSON riletto non e' quello inteso")
    for x in esiti + e2:
        print("  [ok] %s" % x)
    print("\nscritto %s — %d voci" % (a.file, len(nuove)))
    print("file nuovo: %s  %d byte" % (sha256_bytes(dati), len(dati)))
    n = len([l for l in read_bytes(a.ledger).split(b"\n") if l.strip()])
    print("\nOra: python src\\paper2_censimento_rilascio.py censimento --attesi-record %d "
          "--eccezioni logs\\eccezioni_rilascio.json --out logs\\censimento_rilascio.jsonl" % n)
    return 0


def cmd_verify(a):
    voci = carica(a.file, controlla_ancora=False)
    dati = read_bytes(a.file)
    attese = set(NUOVE) | (set(RECORD71) if a.con_record71 else set())
    mancanti = sorted(attese - set(voci))
    falsa = FRASE_FALSA in dati.decode("utf-8")
    corte = sorted(k for k, v in voci.items() if not isinstance(v, str) or len(v) < MIN_RAGIONE)
    print("%s: %s  %d byte  voci=%d  mancanti=%s  frase-falsa=%s  ragioni-corte=%s"
          % (a.file, sha256_bytes(dati), len(dati), len(voci),
             mancanti if mancanti else "nessuna", "SI" if falsa else "no",
             corte if corte else "nessuna"))
    ok = not mancanti and not falsa and not corte
    print("ESITO:", "VERIFICATO" if ok else "NON VERIFICATO")
    return 0 if ok else 2


# ---------------------------------------------------------------------------

def _ledger_finto(n=73, con74=False):
    out = b""
    for i in range(1, n + 1):
        m = "altro-%d" % i
        if i == 73:
            m = MARKER_73
        if i == 74 and con74:
            m = MARKER_74 + "quattro-eccezioni-del-71"
        rec = {"item": "finto/%d" % i, "rules": {"marker": m}}
        out += json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\r\n"
    return out


def cmd_selftest(a):
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

    base = {PREREG: "prima parte. " + FRASE_FALSA, "altro/x.txt": "ragione lunga abbastanza"}

    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "led.jsonl")
        with open(led, "wb") as f:
            f.write(_ledger_finto())
        controlla("ledger a 73 col marker: passa", len(cancello_ledger(led, False)) == 1)
        controlla("--con-record71 senza record 74: rifiutato",
                  rifiuta(lambda: cancello_ledger(led, True)))
        with open(led, "wb") as f:
            f.write(_ledger_finto(n=74, con74=True))
        controlla("--con-record71 col record 74: passa", len(cancello_ledger(led, True)) == 2)
        with open(led, "wb") as f:
            f.write(_ledger_finto(n=72))
        controlla("ledger a 72: rifiutato", rifiuta(lambda: cancello_ledger(led, False)))

        # costruzione senza disco
        nuove, esiti = costruisci(base, td, False, richiedi_disco=False)
        controlla("quattro voci nuove aggiunte", len(nuove) == len(base) + 4)
        controlla("la frase falsa e' sparita e la nuova c'e'",
                  FRASE_FALSA not in nuove[PREREG] and "1068 membri" in nuove[PREREG])
        controlla("solo la voce del deposito porta un digest",
                  "sha256 0000" in nuove["logs/deposito_zenodo.json"]
                  and "NESSUN DIGEST QUI" in nuove["papers/paper2/checklist_paper2.md"]
                  and "NESSUN DIGEST QUI" in nuove["results/paper2/remote_audit.json"])
        controlla("ogni ragione supera la soglia del censimento",
                  all(len(v) >= MIN_RAGIONE for v in nuove.values()))
        controlla("con --con-record71 le voci sono otto",
                  len(costruisci(base, td, True, richiedi_disco=False)[0]) == len(base) + 8)
        controlla("le quattro del 71 nominano il sopravvissuto",
                  "paper2_item13_rev2.py" in RECORD71["src/paper2_item13rev2.py"]
                  and "paper2_passata_1punto.py" in RECORD71["src/paper2_letture_1punto.py"]
                  and "permock_hodfit.csv" in RECORD71["results/phase8_test2_permock.csv"])
        con71 = costruisci(base, td, True, richiedi_disco=False)[0]
        controlla("tre portano l'ancora di CIO' CHE LA CITAZIONE INTENDEVA; la quarta dichiara "
                  "di non averne e cita il digest del sopravvissuto",
                  sum(1 for k in RECORD71 if "sha256 " in con71[k]) == 4
                  and "SENZA ancora" in con71["src/paper2_letture_1punto.py"]
                  and "Due metri indipendenti" in con71["src/paper2_letture_1punto.py"]
                  and "paper2_passata_1punto.py, sha256" in
                  con71["src/paper2_letture_1punto.py"])
        controlla("nessun segnaposto sopravvive",
                  not any(k in json.dumps(con71, ensure_ascii=False) for k in MISURE_71))
        controlla("ogni ragione del 71 cita il record 74",
                  all("RECORD 74" in con71[k] for k in RECORD71))
        controlla("seconda costruzione rifiutata (voci gia' presenti)",
                  rifiuta(lambda: costruisci(nuove, td, False, richiedi_disco=False)))
        controlla("voce del protocollo senza la frase attesa: rifiutata",
                  rifiuta(lambda: costruisci({PREREG: "niente"}, td, False,
                                             richiedi_disco=False)))
        controlla("file senza la voce del protocollo: rifiutato",
                  rifiuta(lambda: costruisci({"x/y.txt": "ragione lunga"}, td, False,
                                             richiedi_disco=False)))

        # misura dal disco, e il rifiuto su un percorso assente
        os.makedirs(os.path.join(td, "logs"), exist_ok=True)
        os.makedirs(os.path.join(td, "papers", "paper2"), exist_ok=True)
        os.makedirs(os.path.join(td, "results", "paper2"), exist_ok=True)
        with open(os.path.join(td, "logs", "deposito_zenodo.json"), "wb") as f:
            f.write(b'{"x": 1}\n')
        controlla("percorso di una voce nuova assente dal disco: rifiutato",
                  rifiuta(lambda: costruisci(base, td, False)))
        for p in ("papers/paper2/checklist_paper2.md", "papers/paper2/paper2_stato.md",
                  "results/paper2/remote_audit.json"):
            with open(os.path.join(td, p.replace("/", os.sep)), "wb") as f:
                f.write(b"x")
        nuove2, _ = costruisci(base, td, False)
        controlla("digest del deposito misurato dal disco",
                  sha256_bytes(b'{"x": 1}\n')[:16] in nuove2["logs/deposito_zenodo.json"])

        # serializzazione e scrittura
        dati = serializza(nuove2)
        controlla("serializza: LF, chiavi ordinate, termina con newline",
                  b"\r" not in dati and dati.endswith(b"\n")
                  and list(json.loads(dati.decode("utf-8"))) == sorted(nuove2))
        p = os.path.join(td, "ecc.json")
        controlla("write_atomic scrive e rilegge il JSON",
                  write_atomic(p, dati) == nuove2)
        controlla("write_atomic non lascia temporanei",
                  not [x for x in os.listdir(td) if x.startswith(".patch_ecc_")])

        # ancora e forma
        with open(p, "wb") as f:
            f.write(b'{"a": "b"}')
        controlla("ancora sha sbagliata rifiutata", rifiuta(lambda: carica(p)))
        with open(p, "wb") as f:
            f.write(b'["a"]')
        controlla("file che non e' un dizionario rifiutato",
                  rifiuta(lambda: carica(p, controlla_ancora=False)))

    # sul file vero, se e' quello atteso
    if os.path.exists(a.file):
        dati = read_bytes(a.file)
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            voci = json.loads(dati.decode("utf-8"))
            controlla("file vero: 14 voci, dizionario", len(voci) == ANCORA_VOCI)
            controlla("file vero: la frase da correggere c'e' una volta",
                      dati.decode("utf-8").count(FRASE_FALSA) == 1)
            controlla("file vero: nessuna delle chiavi nuove esiste gia'",
                      not (set(NUOVE) | set(RECORD71)) & set(voci))
        else:
            print("  [--] file vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] file vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="eccezioni del rilascio: 14 -> 18 voci")
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--file", default=FILE)
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--radice", default=".")
    ap.add_argument("--con-record71", action="store_true",
                    help="aggiunge anche le quattro eccezioni del record 71 (richiede un "
                         "record 74 che le dichiari)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "selftest":
            return cmd_selftest(a)
        if a.cmd == "dry-run":
            return cmd_dry_run(a)
        if a.cmd == "apply":
            return cmd_apply(a)
        return cmd_verify(a)
    except PatchError as e:
        print("RIFIUTATO: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

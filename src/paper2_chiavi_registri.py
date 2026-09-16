#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_chiavi_registri.py — diagnostico per la voce 6.1 della Fase 6.

PERCHE' ESISTE.
Il censimento del 15 settembre ha dato 33 FAIL su 48 sulla proprieta'
`resumable`, tutti con due sole diciture e zero difetti sulle altre tre
proprieta'. Una proprieta' che fallisce sul 69% della popolazione con firma
uniforme non descrive la popolazione: descrive il metro. La causa e' che
`paper2_censimento_registri.py` cerca una CHIAVE PER NOME (`key`, `chiave`,
`config_hash`), cioe' deduce dal nome — la prima voce del §4 della consegna
del 14 settembre.

La chiave di ripresa di un registro di run non e' un campo che si chiama
`key`. E' la TUPLA di campi che identifica l'unita' di lavoro: indice della
realizzazione, regione, punto, ramo. Questo strumento la MISURA invece di
cercarne il nome.

COSA MISURA, e cosa no.
  MISURATO  quali sottoinsiemi minimi di campi hanno tupla distinta su tutti
            i record (chiave candidata), e con quanti duplicati
  MISURATO  quali campi variano e NON entrano in nessuna chiave candidata
            — e' la classe dell'incidente `--origin-offset`: un parametro che
            cambia una misura e non entra nella chiave produce record
            indistinguibili
  MISURATO  quali campi sono costanti su tutto il registro (configurazione
            dichiarata, non discriminante)
  NON MISURATO  se il runner USI quella tupla per riprendere. Quella e'
            ispezione del codice, e va chiesta al sorgente, non al registro.

I duplicati non sono un difetto: la convenzione di lettura e' per UNIONE, e
`fase3_mock.jsonl` porta 38 record `smoke` per costruzione. Vengono contati e
riportati, mai trasformati in un FAIL.

Ambiente: Windows/PowerShell, D:\\projects\\cauchy, comandi dalla radice.
Nessuna dipendenza fuori dalla libreria standard.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA = "paper2_chiavi_registri_v1"
VERSIONE = "1.0"

USCITE_AMMESSE = ("results/paper2", "logs")

# Profondita' di appiattimento dei record annidati. `base.N_H1` e
# `ladder.0.N_H1` sono campi a tutti gli effetti; oltre il secondo livello
# si smette e lo si dichiara.
PROFONDITA_MAX = 2

# Tetti dichiarati. Nessun ripiego silenzioso: quando un tetto morde, lo
# strumento lo STAMPA nel record.
MAX_CAMPI_CANDIDATI = 28
MAX_DIMENSIONE_CHIAVE = 3
MAX_RECORD_LETTI = 200000


def ora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel_posix(percorso: Path, radice: Path) -> str:
    try:
        rel = percorso.resolve().relative_to(radice.resolve())
    except ValueError:
        rel = percorso
    return str(PurePosixPath(*rel.parts))


def verifica_uscita(percorso: Path) -> None:
    normalizzato = str(percorso).replace("\\", "/")
    for ammessa in USCITE_AMMESSE:
        if ("/" + ammessa + "/") in ("/" + normalizzato) or normalizzato.startswith(ammessa + "/"):
            return
    raise SystemExit(
        "RIFIUTO: uscita fuori dalle cartelle ammesse %s -> %s\n"
        "  Record 53: uno strumento del Paper 2 non scrive dove il freeze guarda."
        % (list(USCITE_AMMESSE), percorso)
    )


# ===========================================================================
# lettura e appiattimento
# ===========================================================================

def appiattisci(record: dict, profondita: int = PROFONDITA_MAX) -> dict:
    """Appiattisce i dizionari annidati in campi puntati, fino a profondita'.

    I valori non scalari che restano dopo il tetto diventano una stringa JSON
    canonica: entrano nel confronto come valore unico, non vengono scartati.
    """
    piatto = {}

    def scendi(prefisso: str, valore, livello: int):
        if isinstance(valore, dict) and livello < profondita:
            for nome, sotto in valore.items():
                scendi("%s.%s" % (prefisso, nome) if prefisso else str(nome),
                       sotto, livello + 1)
            return
        if isinstance(valore, (dict, list)):
            piatto[prefisso] = "json:" + json.dumps(valore, sort_keys=True,
                                                    ensure_ascii=False)
            return
        piatto[prefisso] = valore

    scendi("", record, 0)
    return piatto


def leggi_record(percorso: Path) -> tuple[list[dict], dict]:
    """Legge un registro JSONL. Le righe non parsabili sono contate, non tolte
    dal conteggio in silenzio."""
    record = []
    diagnosi = {"righe_lette": 0, "righe_non_parsabili": 0, "righe_non_oggetto": 0,
                "tetto_record_raggiunto": False}
    with percorso.open("rb") as fh:
        for grezza in fh:
            linea = grezza.rstrip(b"\r\n")
            if not linea.strip():
                continue
            diagnosi["righe_lette"] += 1
            if len(record) >= MAX_RECORD_LETTI:
                diagnosi["tetto_record_raggiunto"] = True
                break
            try:
                oggetto = json.loads(linea.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                diagnosi["righe_non_parsabili"] += 1
                continue
            if not isinstance(oggetto, dict):
                diagnosi["righe_non_oggetto"] += 1
                continue
            record.append(appiattisci(oggetto))
    return record, diagnosi


def canonico(valore) -> str:
    if isinstance(valore, str):
        return "s:" + valore
    return "j:" + json.dumps(valore, sort_keys=True, ensure_ascii=False)


# ===========================================================================
# ricerca delle chiavi candidate
# ===========================================================================

def profila_campi(record: list[dict]) -> dict:
    n = len(record)
    presenza: dict[str, int] = {}
    valori: dict[str, set] = {}
    for r in record:
        for nome, valore in r.items():
            presenza[nome] = presenza.get(nome, 0) + 1
            valori.setdefault(nome, set()).add(canonico(valore))
    profilo = {}
    for nome, conta in presenza.items():
        profilo[nome] = {
            "presenza": conta,
            "presenza_frazione": conta / n if n else 0.0,
            "cardinalita": len(valori[nome]),
        }
    return profilo


def costruisci_colonne(record: list[dict], campi: list) -> dict:
    """Forma canonica precalcolata per campo. Una serializzazione per valore,
    non una per combinazione: senza questo la ricerca su 2000 record e 28
    campi costerebbe ~2e7 serializzazioni."""
    return {
        nome: [canonico(r[nome]) if nome in r else "\x00assente" for r in record]
        for nome in campi
    }


def duplicati_di(record: list[dict], campi: tuple, colonne: dict | None = None) -> int:
    """Quanti record in eccesso condividono la stessa tupla. 0 = chiave unica."""
    if colonne is None:
        colonne = costruisci_colonne(record, list(campi))
    visti: dict[tuple, int] = {}
    for tupla in zip(*(colonne[c] for c in campi)):
        visti[tupla] = visti.get(tupla, 0) + 1
    return sum(v - 1 for v in visti.values() if v > 1)


def cerca_chiavi(record: list[dict], profilo: dict) -> dict:
    """Sottoinsiemi minimi di campi con tupla distinta su tutti i record."""
    n = len(record)
    esito = {
        "n_record": n,
        "chiavi_uniche": [],
        "migliore_non_unica": None,
        "tetto_campi": False,
        "tetto_dimensione": MAX_DIMENSIONE_CHIAVE,
        "campi_esclusi_da_tetto": [],
    }
    if n == 0:
        return esito

    # Candidati: presenti quasi ovunque e non costanti. Un campo costante non
    # discrimina; un campo assente da meta' dei record non e' una chiave.
    candidati = [
        nome for nome, p in profilo.items()
        if p["presenza_frazione"] >= 0.99 and 1 < p["cardinalita"] <= n
    ]
    # Ordine dichiarato: cardinalita' decrescente, poi nome. Deterministico.
    candidati.sort(key=lambda nome: (-profilo[nome]["cardinalita"], nome))
    if len(candidati) > MAX_CAMPI_CANDIDATI:
        esito["tetto_campi"] = True
        esito["campi_esclusi_da_tetto"] = candidati[MAX_CAMPI_CANDIDATI:]
        candidati = candidati[:MAX_CAMPI_CANDIDATI]

    # A parita' di duplicati le combinazioni sono EQUIVALENTI: riportarne una
    # sola farebbe passare le altre per "campi fuori dalla chiave", cioe' un
    # falso allarme della classe --origin-offset. Si tengono tutte.
    minimo_duplicati = None
    migliori: list[list] = []
    colonne = costruisci_colonne(record, candidati)
    for dimensione in range(1, MAX_DIMENSIONE_CHIAVE + 1):
        trovate = []
        for combinazione in itertools.combinations(candidati, dimensione):
            duplicati = duplicati_di(record, combinazione, colonne)
            if duplicati == 0:
                trovate.append(list(combinazione))
            if minimo_duplicati is None or duplicati < minimo_duplicati:
                minimo_duplicati = duplicati
                migliori = [list(combinazione)]
            elif duplicati == minimo_duplicati:
                migliori.append(list(combinazione))
        if trovate:
            trovate.sort()
            esito["chiavi_uniche"] = trovate[:12]
            esito["n_chiavi_uniche"] = len(trovate)
            esito["dimensione_chiave"] = dimensione
            break

    if not esito["chiavi_uniche"] and migliori:
        migliori.sort(key=lambda campi: (len(campi), campi))
        esito["migliore_non_unica"] = {
            "campi": migliori[0],
            "duplicati": minimo_duplicati,
            "equivalenti": migliori[:12],
            "n_equivalenti": len(migliori),
        }
    return esito


def analizza(percorso: Path, radice: Path) -> dict:
    record, diagnosi = leggi_record(percorso)
    profilo = profila_campi(record)
    chiavi = cerca_chiavi(record, profilo)

    costanti = sorted(nome for nome, p in profilo.items() if p["cardinalita"] == 1)
    variabili = sorted(nome for nome, p in profilo.items() if p["cardinalita"] > 1)

    # Campi che VARIANO e non entrano in nessuna chiave candidata trovata.
    # E' la classe dell'incidente `--origin-offset`: un parametro che cambia
    # una misura e non entra nella chiave produce record indistinguibili.
    in_chiave = set()
    for chiave in chiavi["chiavi_uniche"]:
        in_chiave.update(chiave)
    if chiavi["migliore_non_unica"]:
        for chiave in chiavi["migliore_non_unica"]["equivalenti"]:
            in_chiave.update(chiave)
    fuori_chiave = sorted(c for c in variabili if c not in in_chiave)

    # Campi parzialmente presenti: la forma di `d5c_n_clipped`, copertura
    # parziale dopo una patch. Censiti, non segnalati come difetto.
    parziali = sorted(
        nome for nome, p in profilo.items()
        if 0.0 < p["presenza_frazione"] < 0.99
    )

    return {
        "schema": SCHEMA,
        "tipo": "registro",
        "percorso": rel_posix(percorso, radice),
        "nome": percorso.name,
        "utc": ora_utc(),
        "diagnosi_lettura": diagnosi,
        "n_record": len(record),
        "n_campi": len(profilo),
        "chiavi": chiavi,
        "campi_costanti": costanti,
        "campi_variabili": variabili,
        "campi_parziali": parziali,
        "campi_variabili_fuori_chiave": fuori_chiave,
        "profilo_campi": {
            nome: profilo[nome] for nome in sorted(profilo)
        },
        "limite": "questo strumento misura il registro; se il runner USI la "
                  "chiave per riprendere si verifica sul sorgente",
    }


# ===========================================================================
# comando principale
# ===========================================================================

def comando_chiavi(args) -> int:
    base_repo = Path(args.base).resolve()
    percorsi: list[Path] = []
    for voce in args.registri:
        p = Path(voce) if Path(voce).is_absolute() else base_repo / voce
        if p.is_dir():
            percorsi.extend(sorted(x for x in p.rglob("*.jsonl") if x.is_file()))
        elif p.is_file():
            percorsi.append(p)
        else:
            raise SystemExit("RIFIUTO: percorso inesistente -> %s" % p)
    if not percorsi:
        raise SystemExit("RIFIUTO: nessun registro da analizzare")

    record_uscita = [analizza(p, base_repo) for p in percorsi]

    print("=" * 78)
    print("CHIAVI DI RIPRESA — misurate, non cercate per nome")
    print("=" * 78)
    print("registri analizzati: %d" % len(record_uscita))
    print()

    larghezza = max(len(r["percorso"]) for r in record_uscita)
    print("%-*s  %8s  %6s  %s" % (larghezza, "registro", "record", "campi", "chiave minima"))
    print("-" * (larghezza + 40))
    senza_chiave = []
    for r in record_uscita:
        chiavi = r["chiavi"]
        if chiavi["chiavi_uniche"]:
            testo = "+".join(chiavi["chiavi_uniche"][0])
            if len(chiavi["chiavi_uniche"]) > 1:
                testo += "  (+%d alternative)" % (len(chiavi["chiavi_uniche"]) - 1)
        elif chiavi["migliore_non_unica"]:
            testo = "NESSUNA <=%d campi; migliore %s con %d duplicati" % (
                MAX_DIMENSIONE_CHIAVE,
                "+".join(chiavi["migliore_non_unica"]["campi"]),
                chiavi["migliore_non_unica"]["duplicati"])
            senza_chiave.append(r)
        else:
            testo = "nessun campo candidato"
            senza_chiave.append(r)
        print("%-*s  %8d  %6d  %s" % (larghezza, r["percorso"], r["n_record"],
                                      r["n_campi"], testo))
    print()

    if args.dettaglio:
        for r in record_uscita:
            print("-" * 78)
            print(r["percorso"])
            chiavi = r["chiavi"]
            if chiavi["chiavi_uniche"]:
                print("  chiavi uniche (dim %d):" % chiavi.get("dimensione_chiave", 0))
                for chiave in chiavi["chiavi_uniche"]:
                    print("      %s" % "+".join(chiave))
            elif chiavi["migliore_non_unica"]:
                print("  nessuna chiave unica entro %d campi" % MAX_DIMENSIONE_CHIAVE)
                print("      combinazioni equivalenti a duplicati minimi: %d"
                      % chiavi["migliore_non_unica"]["n_equivalenti"])
                print("      migliore: %s  duplicati %d" % (
                    "+".join(chiavi["migliore_non_unica"]["campi"]),
                    chiavi["migliore_non_unica"]["duplicati"]))
            if chiavi["tetto_campi"]:
                print("  TETTO CAMPI: esclusi %d campi a bassa cardinalita' -> %s"
                      % (len(chiavi["campi_esclusi_da_tetto"]),
                         chiavi["campi_esclusi_da_tetto"][:8]))
            if r["campi_variabili_fuori_chiave"]:
                print("  variabili FUORI dalla chiave (%d) — classe --origin-offset:"
                      % len(r["campi_variabili_fuori_chiave"]))
                for c in r["campi_variabili_fuori_chiave"][:20]:
                    print("      %-32s cardinalita' %d"
                          % (c, r["profilo_campi"][c]["cardinalita"]))
            if r["campi_parziali"]:
                print("  campi a copertura parziale (%d): %s"
                      % (len(r["campi_parziali"]), r["campi_parziali"][:10]))
            if r["campi_costanti"]:
                print("  costanti (%d): %s" % (len(r["campi_costanti"]),
                                               r["campi_costanti"][:10]))
            print()

    if senza_chiave:
        print("SENZA CHIAVE UNICA entro %d campi (%d):" % (MAX_DIMENSIONE_CHIAVE,
                                                           len(senza_chiave)))
        for r in senza_chiave:
            print("  %s" % r["percorso"])
        print()
        print("Non e' automaticamente un difetto: un registro letto per UNIONE puo'")
        print("portare la stessa unita' di lavoro piu' volte per costruzione (i 38")
        print("record `smoke` di fase3_mock). Va deciso registro per registro.")
        print()

    if args.out:
        uscita = Path(args.out)
        verifica_uscita(uscita)
        uscita.parent.mkdir(parents=True, exist_ok=True)
        with uscita.open("w", encoding="utf-8", newline="\n") as fh:
            for r in record_uscita:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    return 0


# ===========================================================================
# selftest
# ===========================================================================

class Contatore:
    def __init__(self):
        self.ok = 0
        self.ko = []

    def verifica(self, nome, condizione):
        if condizione:
            self.ok += 1
        else:
            self.ko.append(nome)

    def uguale(self, nome, ottenuto, atteso):
        self.verifica("%s (ottenuto %r, atteso %r)" % (nome, ottenuto, atteso),
                      ottenuto == atteso)


def comando_selftest(args) -> int:
    c = Contatore()

    # ---- 1. appiattimento -------------------------------------------------
    piatto = appiattisci({"idx": 0, "base": {"N_H1": 35436.0, "sd": 1.0},
                          "lista": [1, 2]})
    c.uguale("appiattito: idx", piatto.get("idx"), 0)
    c.uguale("appiattito: base.N_H1", piatto.get("base.N_H1"), 35436.0)
    c.verifica("appiattito: lista serializzata",
               isinstance(piatto.get("lista"), str) and piatto["lista"].startswith("json:"))
    c.verifica("appiattito: nessun dizionario residuo",
               not any(isinstance(v, dict) for v in piatto.values()))

    # ---- 2. profondita' massima rispettata --------------------------------
    piatto = appiattisci({"a": {"b": {"c": {"d": 1}}}})
    c.verifica("profondita': fermata a 2", "a.b" in piatto)
    c.verifica("profondita': livello 3 serializzato", str(piatto["a.b"]).startswith("json:"))

    # ---- 3. chiave a un campo --------------------------------------------
    record = [{"idx": i, "valore": float(i)} for i in range(50)]
    profilo = profila_campi(record)
    chiavi = cerca_chiavi(record, profilo)
    c.uguale("chiave singola trovata", chiavi["chiavi_uniche"][0], ["idx"])
    c.uguale("chiave singola: dimensione", chiavi["dimensione_chiave"], 1)

    # ---- 4. chiave a due campi (la forma reale: indice + regione) --------
    record = []
    for regione in ("NGC", "SGC"):
        for i in range(30):
            record.append({"idx": i, "region": regione, "N_H1": float(i)})
    profilo = profila_campi(record)
    chiavi = cerca_chiavi(record, profilo)
    c.uguale("chiave doppia: dimensione", chiavi["dimensione_chiave"], 2)
    c.verifica("chiave doppia: idx+region fra le trovate",
               ["idx", "region"] in chiavi["chiavi_uniche"])
    c.verifica("nessuna chiave a un campo sola", all(
        len(k) == 2 for k in chiavi["chiavi_uniche"]))

    # ---- 5. chiave a tre campi (indice + regione + k) --------------------
    record = []
    for regione in ("NGC", "SGC"):
        for k in range(4):
            for i in range(10):
                record.append({"idx": i, "region": regione, "k": k, "N_H1": float(i + k)})
    profilo = profila_campi(record)
    chiavi = cerca_chiavi(record, profilo)
    c.uguale("chiave tripla: dimensione", chiavi["dimensione_chiave"], 3)

    # ---- 6. DIFETTO: nessuna chiave unica, duplicati contati -------------
    record = [{"idx": i % 5, "valore": 1.0} for i in range(20)]
    profilo = profila_campi(record)
    chiavi = cerca_chiavi(record, profilo)
    c.uguale("senza chiave: nessuna unica", chiavi["chiavi_uniche"], [])
    c.verifica("senza chiave: migliore riportata", chiavi["migliore_non_unica"] is not None)
    c.uguale("senza chiave: duplicati contati",
             chiavi["migliore_non_unica"]["duplicati"], 15)

    # ---- 7. i duplicati per UNIONE non fanno fallire nulla ---------------
    # fase3_mock: stessa unita' di lavoro ripetuta dai record smoke.
    record = [{"idx": i, "region": "NGC", "N_H1": 1.0} for i in range(10)]
    record += [{"idx": 0, "region": "NGC", "N_H1": 1.0}]
    profilo = profila_campi(record)
    chiavi = cerca_chiavi(record, profilo)
    c.uguale("unione: nessuna chiave unica", chiavi["chiavi_uniche"], [])
    c.uguale("unione: un solo duplicato", chiavi["migliore_non_unica"]["duplicati"], 1)
    c.verifica("unione: lo strumento non emette un verdetto",
               "esito" not in chiavi and "verdetto" not in chiavi)

    # ---- 7-bis. DIFETTO RIPRODOTTO: combinazioni equivalenti a parita' di
    # duplicati. Riportarne una sola faceva uscire l'altra come "campo fuori
    # dalla chiave", cioe' un falso allarme della classe --origin-offset.
    record = []
    for reg in ("NGC", "SGC"):
        for i in range(20):
            # idx e N_H1 sono in corrispondenza biunivoca: idx+region e
            # N_H1+region sono equivalenti, e nessuno dei due e' "fuori".
            record.append({"idx": i, "region": reg, "N_H1": float(i), "extra": 0})
    record.append({"idx": 0, "region": "NGC", "N_H1": 0.0, "extra": 0})
    profilo = profila_campi(record)
    chiavi = cerca_chiavi(record, profilo)
    c.uguale("equivalenti: nessuna unica", chiavi["chiavi_uniche"], [])
    c.verifica("equivalenti: piu' di una combinazione riportata",
               chiavi["migliore_non_unica"]["n_equivalenti"] >= 2)
    unione = set()
    for chiave in chiavi["migliore_non_unica"]["equivalenti"]:
        unione.update(chiave)
    c.verifica("equivalenti: idx nell'unione", "idx" in unione)
    c.verifica("equivalenti: N_H1 nell'unione", "N_H1" in unione)

    # ---- 8. campo costante escluso dai candidati -------------------------
    record = [{"idx": i, "ensemble": "v2"} for i in range(20)]
    profilo = profila_campi(record)
    c.uguale("costante: cardinalita' 1", profilo["ensemble"]["cardinalita"], 1)
    chiavi = cerca_chiavi(record, profilo)
    c.verifica("costante: fuori dalle chiavi",
               all("ensemble" not in k for k in chiavi["chiavi_uniche"]))

    # ---- 9. DIFETTO classe --origin-offset: parametro fuori dalla chiave --
    with tempfile.TemporaryDirectory() as tmp:
        radice = Path(tmp)
        f = radice / "r.jsonl"
        righe = []
        for offset in (4.0, -2.1):
            for i in range(10):
                righe.append(json.dumps({"idx": i, "region": "NGC",
                                         "origin_offset": offset,
                                         "N_H1": float(i)}))
        f.write_bytes(("\n".join(righe) + "\n").encode("utf-8"))
        r = analizza(f, radice)
        # idx+region NON e' unica: l'offset raddoppia i record
        c.verifica("origin-offset: idx+region non basta",
                   ["idx", "region"] not in r["chiavi"]["chiavi_uniche"])
        c.verifica("origin-offset: il parametro entra nella chiave trovata",
                   any("origin_offset" in k for k in r["chiavi"]["chiavi_uniche"]))

    # ---- 10. campi a copertura parziale (forma di d5c_n_clipped) ---------
    with tempfile.TemporaryDirectory() as tmp:
        radice = Path(tmp)
        f = radice / "r.jsonl"
        righe = [json.dumps({"idx": i, "N_H1": 1.0}) for i in range(10)]
        righe += [json.dumps({"idx": i, "N_H1": 1.0, "d5c_n_clipped": 0})
                  for i in range(10, 20)]
        f.write_bytes(("\n".join(righe) + "\n").encode("utf-8"))
        r = analizza(f, radice)
        c.verifica("parziale: d5c rilevato", "d5c_n_clipped" in r["campi_parziali"])
        c.verifica("parziale: non e' un difetto", "difetto" not in r)
        c.uguale("parziale: record letti", r["n_record"], 20)

    # ---- 11. righe non parsabili contate, non tolte in silenzio ----------
    with tempfile.TemporaryDirectory() as tmp:
        radice = Path(tmp)
        f = radice / "r.jsonl"
        f.write_bytes(b'{"idx":0}\n{"idx":1\n{"idx":2}\n')
        r = analizza(f, radice)
        c.uguale("non parsabili: contate", r["diagnosi_lettura"]["righe_non_parsabili"], 1)
        c.uguale("non parsabili: righe lette", r["diagnosi_lettura"]["righe_lette"], 3)
        c.uguale("non parsabili: record validi", r["n_record"], 2)

    # ---- 12. record annidati: la chiave puo' stare in un campo puntato ---
    with tempfile.TemporaryDirectory() as tmp:
        radice = Path(tmp)
        f = radice / "r.jsonl"
        righe = [json.dumps({"meta": {"idx": i, "region": "NGC"},
                             "base": {"N_H1": float(i)}}) for i in range(20)]
        f.write_bytes(("\n".join(righe) + "\n").encode("utf-8"))
        r = analizza(f, radice)
        c.verifica("annidato: meta.idx candidato",
                   any("meta.idx" in k for k in r["chiavi"]["chiavi_uniche"]))

    # ---- 13. registro vuoto: nessuna eccezione ---------------------------
    with tempfile.TemporaryDirectory() as tmp:
        radice = Path(tmp)
        f = radice / "vuoto.jsonl"
        f.write_bytes(b"")
        r = analizza(f, radice)
        c.uguale("vuoto: n_record", r["n_record"], 0)
        c.uguale("vuoto: nessuna chiave", r["chiavi"]["chiavi_uniche"], [])

    # ---- 14. determinismo: due passate danno lo stesso esito -------------
    record = []
    for regione in ("NGC", "SGC"):
        for i in range(20):
            record.append({"idx": i, "region": regione, "v": float(i)})
    profilo = profila_campi(record)
    a = cerca_chiavi(record, profilo)
    b = cerca_chiavi(record, profilo)
    c.uguale("determinismo", a["chiavi_uniche"], b["chiavi_uniche"])

    # ---- 15. rifiuto di scrivere fuori dalle cartelle ammesse ------------
    try:
        verifica_uscita(Path("results/paper1/x.jsonl"))
        c.verifica("rifiuto results/paper1", False)
    except SystemExit:
        c.verifica("rifiuto results/paper1", True)
    try:
        verifica_uscita(Path("results/paper2/x.jsonl"))
        c.verifica("accetta results/paper2", True)
    except SystemExit:
        c.verifica("accetta results/paper2", False)

    # ---- 16. lo strumento non emette verdetti ----------------------------
    with tempfile.TemporaryDirectory() as tmp:
        radice = Path(tmp)
        f = radice / "r.jsonl"
        f.write_bytes(b'{"idx":0}\n{"idx":0}\n')
        r = analizza(f, radice)
        testo = json.dumps(r)
        for parola in ('"esito"', '"verdetto"', '"PASS"', '"FAIL"'):
            c.verifica("nessun verdetto emesso: %s" % parola, parola not in testo)

    totale = c.ok + len(c.ko)
    print("selftest: %d/%d" % (c.ok, totale))
    if c.ko:
        print("FALLITI:")
        for nome in c.ko:
            print("  %s" % nome)
        return 1
    return 0


def principale(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="paper2_chiavi_registri.py",
        description="Misura la chiave di ripresa reale dei registri — voce 6.1.")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("chiavi", help="misura le chiavi candidate")
    p.add_argument("registri", nargs="+",
                   help="file .jsonl o cartelle da analizzare")
    p.add_argument("--base", default=".", help="radice del repository (default: .)")
    p.add_argument("--dettaglio", action="store_true",
                   help="stampa campi fuori chiave, parziali e costanti")
    p.add_argument("--out", default=None, help="registro di uscita (.jsonl)")
    p.set_defaults(funzione=comando_chiavi)

    p = sub.add_parser("selftest", help="riproduce ogni caso su fixture")
    p.set_defaults(funzione=comando_selftest)

    args = parser.parse_args(argv)
    return args.funzione(args)


if __name__ == "__main__":
    sys.exit(principale())

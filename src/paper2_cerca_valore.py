#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_cerca_valore.py rev.2 — voce 6.2-i, righe 5 e 6: trovare il run di un valore che oggi ha
per fonte solo un manoscritto.

LA REV.1 NON DISCRIMINAVA, E LA MISURA LO DICEVA: 26 candidati per l'NFW, 77 per lo snapshot
contro 69 col solo valore centrale. Quando la coppia AUMENTA i candidati rispetto al singolo
valore, la coppia non e' un criterio. Tre difetti, tutti riprodotti nel selftest prima di essere
corretti:

  (1) LE CIFRE DENTRO LE STRINGHE ESADECIMALI erano lette come numeri: «...a112af94...» produce
      un 112, e i manifest sono pieni di sha256. Ora un numero e' tale solo se NON confina con
      una lettera, una cifra, un punto o un underscore.
  (2) LA CO-OCCORRENZA NEL FILE non discrimina un registro da 2000 record: in 1,6 MB ogni coppia
      di numeri si trova da qualche parte. Ora conta solo la co-occorrenza nello STESSO RECORD, e
      i JSON su una riga sola sono dichiarati non discriminanti invece di essere contati.
  (3) DUE VALORI NON BASTANO: si pretendono TUTTI E TRE i bersagli della riga sullo stesso
      record — valore centrale, incertezza e terza quantita' (numerosita' o passo).

E UNA DISTINZIONE NUOVA, STRUTTURALE E NON PER NOME. Un record che CITA un valore non e' il run
che l'ha prodotto: le copie del ledger portano i numeri del budget nella loro prosa. Un record con
i campi `document` e `item` e' una citazione di protocollo e viene classificato tale; il verdetto
si calcola solo sui record di misura. Nessuna cartella e nessun nome sono esclusi a mano.

DUE METRI, PERCHE' UN'ASSENZA NE RICHIEDE DUE (record 74): `cerca` cammina il disco, `--storia`
aggiunge i percorsi aggiunti in qualche ramo e non piu' su disco, letti da git.

IL VERDETTO NON E' «TROVATO»:
  UNICA          un solo registro di misura porta i tre valori sullo stesso record;
  NON_DISCRIMINA piu' di uno: la ricerca non decide, e li elenca;
  ASSENTE        nessuno, sui metri percorsi — e lo strumento dice quali NON ha percorso.

LIMITI DICHIARATI:
  - solo estensioni di testo (.json .jsonl .csv .tsv .txt .dat) sotto il cap di byte: un valore
    dentro un .npz non viene visto, e il conteggio degli scartati lo dice;
  - confronta numeri, non significati: un 53 che parla d'altro e' un candidato come gli altri;
  - un JSON scritto su una riga sola non ha record distinguibili: viene dichiarato tale e non
    entra nel verdetto, ma resta elencato;
  - un valore memorizzato con meno cifre di quelle scritte nel budget non rientra nella
    tolleranza e non viene trovato;
  - un CSV a colonne porta i valori su righe diverse per costruzione: se la fonte e' un CSV, il
    criterio «stesso record» la scarta. Dichiarato, non aggirato.

Uso:
  python src\paper2_cerca_valore.py selftest
  python src\paper2_cerca_valore.py bersagli
  python src\paper2_cerca_valore.py cerca --bersaglio nfw --storia --out logs\cerca_valore.jsonl
  python src\paper2_cerca_valore.py cerca --bersaglio snapshot --storia --out logs\cerca_valore.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BUDGET = "papers/paper2/paper2_budget_5_1.md"
ANCORA_BUDGET = "777403c7a66961debee2c51e50ed0b764a88a6d4689be1ffdba76d7d042a68df"
ANCORA_BYTE = 10822

RADICI = ("results", "logs")
ESTENSIONI = (".json", ".jsonl", ".csv", ".tsv", ".txt", ".dat")
CAP_BYTE = 64 * 1024 * 1024
CAP_RIGA = 4000          # oltre questa lunghezza, «stesso record» non vuol dire niente
CAMPI_CITAZIONE = ("document", "item")

RIGHE = {
    "nfw": {
        "riga": 5,
        "descrizione": "profilo dei satelliti NFW",
        "citata": "Paper 1 §7.1",
        "regex": r"\| 5 \| profilo dei satelliti NFW \| NGC \u2212(\d+(?:\.\d+)?) \u00b1 "
                 r"(\d+(?:\.\d+)?), (\d+) coppie \|",
        "nomi": ("centrale", "incertezza", "coppie"),
    },
    "snapshot": {
        "riga": 6,
        "descrizione": "snapshot contro lightcone",
        "citata": "M26 §7 (vi); Paper 1 Tab. 8",
        "regex": r"\| 6 \| snapshot contro lightcone \| \u2212(\d+(?:\.\d+)?) \u00b1 "
                 r"(\d+(?:\.\d+)?) per unità di \*z\*, \u0394\*z\* \u2248 (\d+(?:\.\d+)?) \|",
        "nomi": ("centrale", "incertezza", "passo_z"),
    },
}

NUMERO = re.compile(r"\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
# un numero non confina con una lettera, una cifra, un punto o un underscore: e' cosi' che le
# cifre dentro «a112af94» smettono di essere numeri (difetto 1 della rev.1)
CONFINE = re.compile(r"[0-9A-Za-z._]")


class RicercaError(Exception):
    pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def tolleranza(scritto: str) -> float:
    """Mezza unita' nell'ultima cifra scritta. Non si sceglie: si misura sulla grafia."""
    if "." in scritto:
        return 0.5 * 10 ** (-len(scritto.split(".", 1)[1]))
    return 0.5


def bersagli_dal_budget(testo: str) -> dict:
    fuori = {}
    for chiave, spec in RIGHE.items():
        m = re.search(spec["regex"], testo)
        if not m:
            raise RicercaError(
                "la riga %d del budget non si legge nella forma attesa: il documento e' cambiato "
                "e i bersagli andrebbero inventati. Fermarsi." % spec["riga"])
        valori = [{"nome": nome, "scritto": s, "valore": float(s), "tolleranza": tolleranza(s)}
                  for nome, s in zip(spec["nomi"], m.groups())]
        fuori[chiave] = {"riga": spec["riga"], "descrizione": spec["descrizione"],
                         "citata": spec["citata"], "valori": valori}
    return fuori


def numeri_della_riga(riga: str) -> list:
    """Tutti i numeri della riga. Un numero non confina con lettere, cifre, punti o underscore:
    cosi' le cifre dentro un digest esadecimale non sono numeri."""
    fuori = []
    for m in NUMERO.finditer(riga):
        i, j = m.start(), m.end()
        if i > 0 and CONFINE.match(riga[i - 1]):
            continue
        if j < len(riga) and CONFINE.match(riga[j]):
            if not (riga[j] == "." and (j + 1 >= len(riga) or not riga[j + 1].isdigit())):
                continue
        try:
            fuori.append((float(m.group(0)), i))
        except ValueError:  # pragma: no cover
            continue
    return fuori


def coincide(x: float, v: dict) -> bool:
    return abs(abs(x) - v["valore"]) <= v["tolleranza"]


def classe_record(riga: str) -> str:
    """Un record che CITA un valore non e' il run che l'ha prodotto. La distinzione e'
    strutturale: i campi `document` e `item` fanno di un record una citazione di protocollo."""
    s = riga.strip().rstrip(",")
    if not s.startswith("{"):
        return "registro"
    try:
        d = json.loads(s)
    except Exception:  # noqa: BLE001
        return "registro"
    if isinstance(d, dict) and all(c in d for c in CAMPI_CITAZIONE):
        return "citazione_ledger"
    return "registro"


def esamina_testo(testo: str, valori: list) -> dict:
    """Cerca i tre bersagli sullo STESSO record. Restituisce le classi, dalla piu' forte."""
    nomi = [v["nome"] for v in valori]
    per_nome = {n: 0 for n in nomi}
    tre, due, lunghe, citazioni = [], [], 0, 0
    for n, riga in enumerate(testo.splitlines(), 1):
        numeri = numeri_della_riga(riga)
        if not numeri:
            continue
        colpiti = set()
        for x, _ in numeri:
            for v in valori:
                if coincide(x, v):
                    colpiti.add(v["nome"])
        for c in colpiti:
            per_nome[c] += 1
        if len(colpiti) < 2:
            continue
        if len(riga) > CAP_RIGA:
            lunghe += 1
            continue
        if classe_record(riga) == "citazione_ledger":
            citazioni += 1
            continue
        voce = {"riga": n, "colpiti": sorted(colpiti), "contesto": riga.strip()[:220]}
        (tre if len(colpiti) == 3 else due).append(voce)
    return {"per_nome": per_nome, "tre": tre[:10], "due": due[:10],
            "n_tre": len(tre), "n_due": len(due),
            "righe_lunghe": lunghe, "citazioni_ledger": citazioni}


def file_candidati(radici, estensioni, cap) -> tuple:
    dentro, scartati = [], {"estensione": 0, "troppo_grandi": 0, "illeggibili": 0}
    for r in radici:
        base = Path(r)
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in estensioni:
                scartati["estensione"] += 1
                continue
            try:
                if p.stat().st_size > cap:
                    scartati["troppo_grandi"] += 1
                    continue
            except OSError:
                scartati["illeggibili"] += 1
                continue
            dentro.append(p)
    return sorted(dentro), scartati


def _git(args, radice="."):
    try:
        r = subprocess.run(["git"] + args, cwd=radice, capture_output=True)
    except OSError as e:  # pragma: no cover
        raise RicercaError("git non eseguibile: %r" % e)
    return r.stdout if r.returncode == 0 else None


def percorsi_mai_su_disco(estensioni, radici, radice=".") -> list:
    out = _git(["log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:"], radice)
    if out is None:
        raise RicercaError("git log non risponde: la storia non e' un metro disponibile qui")
    visti, fuori = set(), []
    for riga in out.decode("utf-8", "replace").splitlines():
        s = riga.strip()
        if not s or s in visti:
            continue
        visti.add(s)
        if not s.startswith(tuple(r.rstrip("/") + "/" for r in radici)):
            continue
        if Path(s).suffix.lower() not in estensioni:
            continue
        if (Path(radice) / s).is_file():
            continue
        fuori.append(s)
    return sorted(fuori)


def contenuto_da_git(percorso: str, radice=".") -> bytes | None:
    rev = _git(["rev-list", "--all", "-1", "--", percorso], radice)
    if not rev or not rev.strip():
        return None
    c = rev.decode().strip()
    for spec in ("%s:%s" % (c, percorso), "%s^:%s" % (c, percorso)):
        b = _git(["show", spec], radice)
        if b:
            return b
    return None


def leggi_budget(p: Path) -> str:
    if not p.is_file():
        raise RicercaError("budget assente: %s" % p)
    dati = p.read_bytes()
    got = (hashlib.sha256(dati).hexdigest(), len(dati))
    if got != (ANCORA_BUDGET, ANCORA_BYTE):
        raise RicercaError(
            "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
            "  I bersagli si leggono da questo documento: se e' cambiato, vanno riletti prima."
            % (p, ANCORA_BUDGET, ANCORA_BYTE, got[0], got[1]))
    return dati.decode("utf-8")


# ---------------------------------------------------------------------------

def cmd_bersagli(a) -> int:
    for chiave, b in bersagli_dal_budget(leggi_budget(Path(a.budget))).items():
        print("%-9s riga %d — %s (citata: %s)"
              % (chiave, b["riga"], b["descrizione"], b["citata"]))
        for v in b["valori"]:
            print("            %-11s scritto %-6s -> cerco |x| in [%.4f, %.4f]"
                  % (v["nome"], v["scritto"], v["valore"] - v["tolleranza"],
                     v["valore"] + v["tolleranza"]))
    print("\ncriterio: TUTTI E TRE sullo stesso record, su un registro di misura e non su una "
          "citazione di protocollo.")
    return 0


def cmd_cerca(a) -> int:
    t0 = time.time()
    bersagli = bersagli_dal_budget(leggi_budget(Path(a.budget)))
    if a.bersaglio not in bersagli:
        raise RicercaError("bersaglio %r sconosciuto: %s" % (a.bersaglio, sorted(bersagli)))
    b = bersagli[a.bersaglio]
    valori = b["valori"]
    print("=== paper2_cerca_valore rev.2 — riga %d, %s ===" % (b["riga"], b["descrizione"]))
    for v in valori:
        print("  %-11s %-6s  |x| in [%.4f, %.4f]"
              % (v["nome"], v["scritto"], v["valore"] - v["tolleranza"],
                 v["valore"] + v["tolleranza"]))
    print("  criterio: tutti e tre sullo stesso record, su un registro di misura")

    percorsi, scartati = file_candidati(a.radici, ESTENSIONI, a.cap)
    print("\ndisco: %d file letti sotto %s; scartati %d per estensione, %d oltre il cap, %d "
          "illeggibili" % (len(percorsi), "/".join(a.radici), scartati["estensione"],
                           scartati["troppo_grandi"], scartati["illeggibili"]))

    forti, deboli = [], {"due_valori": 0, "righe_lunghe": 0, "citazioni_ledger": 0,
                         "solo_un_valore": 0}
    esaminati = 0

    def conta(e, percorso, metro, byte, sha):
        if e["n_tre"]:
            forti.append({"percorso": percorso, "metro": metro, "byte": byte, "sha256": sha,
                          **e})
            return
        if e["n_due"]:
            deboli["due_valori"] += 1
        elif e["righe_lunghe"]:
            deboli["righe_lunghe"] += 1
        elif e["citazioni_ledger"]:
            deboli["citazioni_ledger"] += 1
        elif any(e["per_nome"].values()):
            deboli["solo_un_valore"] += 1

    for p in percorsi:
        try:
            testo = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            scartati["illeggibili"] += 1
            continue
        esaminati += 1
        conta(esamina_testo(testo, valori), p.as_posix(), "disco", p.stat().st_size,
              sha256_file(p))

    storici = []
    if a.storia:
        mai = percorsi_mai_su_disco(ESTENSIONI, a.radici)
        print("storia: %d percorsi aggiunti in qualche ramo e non piu' su disco" % len(mai))
        for s in mai:
            dati = contenuto_da_git(s)
            if dati is None:
                continue
            storici.append(s)
            conta(esamina_testo(dati.decode("utf-8", "replace"), valori), s, "git", len(dati),
                  hashlib.sha256(dati).hexdigest())
    else:
        print("storia: NON percorsa (senza --storia il secondo metro manca, e un'assenza non si "
              "puo' dichiarare)")

    print("\npotere discriminante:")
    print("  %d file con i TRE valori su un record di misura   <- il criterio" % len(forti))
    print("  %d con due valori soli, %d con un valore solo" % (deboli["due_valori"],
                                                               deboli["solo_un_valore"]))
    print("  %d scartati perche' il record e' una riga oltre %d caratteri (nessun record "
          "distinguibile)" % (deboli["righe_lunghe"], CAP_RIGA))
    print("  %d scartati perche' il record CITA il valore (campi %s): una citazione non e' un run"
          % (deboli["citazioni_ledger"], " e ".join(CAMPI_CITAZIONE)))

    esito = ("UNICA" if len(forti) == 1 else "NON_DISCRIMINA" if len(forti) > 1
             else "ASSENTE" if a.storia else "ASSENTE_SU_UN_METRO_SOLO")

    for c in forti:
        print("\n--- %s  (%s)  %s...  %d byte  — %d record coi tre valori"
              % (c["percorso"], c["metro"], c["sha256"][:16], c["byte"], c["n_tre"]))
        for r in c["tre"][:3]:
            print("    riga %d: %s" % (r["riga"], r["contesto"]))

    record = {"schema": "paper2_cerca_valore_v2",
              "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "bersaglio": a.bersaglio, "riga": b["riga"], "citata": b["citata"],
              "budget_sha256": ANCORA_BUDGET, "valori": valori, "radici": list(a.radici),
              "estensioni": list(ESTENSIONI), "cap_byte": a.cap, "cap_riga": CAP_RIGA,
              "file_esaminati": esaminati, "scartati": scartati, "deboli": deboli,
              "storia_percorsa": bool(a.storia), "percorsi_storici": len(storici),
              "candidati": forti, "esito": esito, "secondi": round(time.time() - t0, 2)}
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print("\nrecord appeso a %s" % a.out)
    print("ESITO: %s" % esito)
    return 0 if esito == "UNICA" else 3


# ---------------------------------------------------------------------------

def cmd_selftest(a) -> int:
    ok = tot = 0

    def controlla(nome, cond):
        nonlocal ok, tot
        tot += 1
        ok += bool(cond)
        print("  [%s] %s" % ("ok" if cond else "FAIL", nome))

    def rifiuta(fn):
        try:
            fn()
        except RicercaError:
            return True
        return False

    # --- tolleranza ---------------------------------------------------------
    controlla("tolleranza di «56.5» = 0.05", tolleranza("56.5") == 0.05)
    controlla("tolleranza di «53» = 0.5", tolleranza("53") == 0.5)
    controlla("tolleranza di «0.25» = 0.005", abs(tolleranza("0.25") - 0.005) < 1e-12)

    # --- DIFETTO 1: cifre dentro le stringhe esadecimali --------------------
    esa = '"sha256": "e676c7e1a112af94ae970187b4b45bea5d87946d53c6dd0b23ced3806e8767b9"'
    controlla("DIFETTO 1 corretto: nessun numero dentro un digest esadecimale",
              numeri_della_riga(esa) == [])
    controlla("un digest tutto cifre non produce i suoi pezzi",
              numeri_della_riga('"h": "112233445566"') == [(112233445566.0, 6)])
    controlla("156.5 non produce un 56.5",
              sorted(x for x, _ in numeri_della_riga("a 156.5 b 56.5 c")) == [56.5, 156.5])
    controlla("un numero dopo il due punti di JSON si legge",
              [x for x, _ in numeri_della_riga('{"dN_sem": 23.487}')] == [23.487])
    controlla("un numero negativo si legge (il segno non conta)",
              [x for x, _ in numeri_della_riga('{"dN": -56.512}')] == [56.512])
    controlla("un numero con esponente si legge",
              any(abs(x - 3.5e-5) < 1e-12 for x, _ in numeri_della_riga('"s": 3.5e-05,')))
    controlla("un numero a fine frase si legge",
              any(x == 0.25 for x, _ in numeri_della_riga("passo 0.25.")))
    controlla("un identificatore come delta_0112 non produce 112",
              numeri_della_riga('"key": "delta_0112"') == [])

    riga5 = ("| 5 | profilo dei satelliti NFW | NGC \u221256.5 \u00b1 23.5, 40 coppie | "
             "Paper 1 §7.1 | x |\n")
    riga6 = ("| 6 | snapshot contro lightcone | \u221253 \u00b1 112 per unità di *z*, "
             "\u0394*z* \u2248 0.25 | M26 §7 (vi); Paper 1 Tab. 8 | x |\n")
    b = bersagli_dal_budget(riga5 + riga6)
    controlla("riga 5 letta dal documento: 56.5 / 23.5 / 40",
              [x["valore"] for x in b["nfw"]["valori"]] == [56.5, 23.5, 40.0])
    controlla("riga 6 letta dal documento: 53 / 112 / 0.25",
              [x["valore"] for x in b["snapshot"]["valori"]] == [53.0, 112.0, 0.25])
    controlla("documento cambiato: bersagli NON inventati, si rifiuta",
              rifiuta(lambda: bersagli_dal_budget("| 5 | qualcosa d'altro |")))
    valori5 = b["nfw"]["valori"]

    # --- DIFETTO 3: due valori non bastano ----------------------------------
    e = esamina_testo('{"dN_medio": -56.512, "dN_sem": 23.487, "coppie": 40}', valori5)
    controlla("DIFETTO 3 corretto: tre valori su un record -> candidato forte",
              e["n_tre"] == 1 and e["n_due"] == 0)
    e = esamina_testo('{"dN_medio": -56.512, "dN_sem": 23.487}', valori5)
    controlla("due valori soli: NON e' un candidato forte",
              e["n_tre"] == 0 and e["n_due"] == 1)

    # --- DIFETTO 2: co-occorrenza nel file, non nel record -------------------
    e = esamina_testo("dN -56.5\naltro 40\nsem 23.5", valori5)
    controlla("DIFETTO 2 corretto: valori su righe diverse non fanno un candidato",
              e["n_tre"] == 0 and e["n_due"] == 0)
    lunga = '{"a": -56.5, "b": 23.5, "c": 40, "pad": "' + "x" * (CAP_RIGA + 10) + '"}'
    e = esamina_testo(lunga, valori5)
    controlla("riga unica oltre il cap: scartata e dichiarata, non contata",
              e["n_tre"] == 0 and e["righe_lunghe"] == 1)

    # --- la distinzione fra citazione e misura ------------------------------
    cit = ('{"document": "paper2_prereg_v1.md v1.1", "item": "5.1", "new_value": '
           '"NFW -56.5 +/- 23.5 su 40 coppie"}')
    controlla("un record con `document` e `item` e' una citazione, non un run",
              classe_record(cit) == "citazione_ledger")
    e = esamina_testo(cit, valori5)
    controlla("la citazione non entra fra i candidati e viene contata a parte",
              e["n_tre"] == 0 and e["citazioni_ledger"] == 1)
    controlla("un record di misura resta un registro",
              classe_record('{"dN_medio": -56.5, "dN_sem": 23.5, "coppie": 40}') == "registro")
    controlla("una riga non JSON resta un registro",
              classe_record("56.5 23.5 40") == "registro")
    controlla("un JSON malformato resta un registro (non si presume)",
              classe_record('{"document": "x", "item":') == "registro")

    # --- la camminata, in byte espliciti ------------------------------------
    # la rev.1 aveva qui un controllo che dipendeva dalla traduzione dei fine riga: su Linux
    # write_text("x\n") scrive 2 byte, su Windows 3. Un controllo che cambia con la piattaforma
    # non e' un controllo. Qui si scrive in byte.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        vecchia_cwd = os.getcwd()
        os.chdir(td)
        (base / "results" / "paper1").mkdir(parents=True)
        (base / "results" / "paper1" / "nfw.jsonl").write_bytes(
            b'{"dN_medio": -56.512, "dN_sem": 23.487, "coppie": 40}\n')
        (base / "results" / "paper1" / "rumore.json").write_bytes(b'{"x": -56.5, "y": 1}\n')
        (base / "results" / "paper1" / "cubo.npz").write_bytes(b"\x00" * 10)
        (base / "results" / "paper1" / "tre_byte.csv").write_bytes(b"x\r\n")
        percorsi, scartati = file_candidati(["results"], ESTENSIONI, CAP_BYTE)
        controlla("la camminata prende le estensioni di testo e scarta il resto",
                  len(percorsi) == 3 and scartati["estensione"] == 1)
        controlla("il cap e' inclusivo, misurato in byte espliciti: a cap=3 passa il file da 3",
                  [x.name for x in file_candidati(["results"], ESTENSIONI, 3)[0]]
                  == ["tre_byte.csv"])
        controlla("a cap=2 non passa nemmeno quello, e sono tutti contati",
                  file_candidati(["results"], ESTENSIONI, 2)[1]["troppo_grandi"] == 3)
        controlla("radice inesistente: nessun errore, zero file",
                  file_candidati(["non_c_e"], ESTENSIONI, CAP_BYTE)[0] == [])

        class A:
            budget = str(base / "b.md")
            bersaglio = "nfw"
            radici = ["results"]
            cap = CAP_BYTE
            storia = False
            out = None

        (base / "b.md").write_bytes((riga5 + riga6).encode("utf-8"))
        controlla("budget con lo sha sbagliato: rifiutato",
                  rifiuta(lambda: leggi_budget(Path(A.budget))))
        controlla("budget assente: rifiutato",
                  rifiuta(lambda: leggi_budget(base / "manca.md")))

        sha_vero, byte_vero = ANCORA_BUDGET, ANCORA_BYTE
        try:
            dati = (riga5 + riga6).encode("utf-8")
            globals()["ANCORA_BUDGET"] = hashlib.sha256(dati).hexdigest()
            globals()["ANCORA_BYTE"] = len(dati)
            controlla("ciclo completo, un candidato forte: esito UNICA", cmd_cerca(A()) == 0)
            (base / "results" / "paper1" / "gemello.json").write_bytes(
                b'{"a": -56.49, "b": 23.52, "c": 40}\n')
            controlla("due candidati forti: NON_DISCRIMINA (e non «trovato»)",
                      cmd_cerca(A()) == 3)
            for f in ("nfw.jsonl", "gemello.json"):
                (base / "results" / "paper1" / f).unlink()
            controlla("nessun candidato e storia non percorsa: un metro solo, non ASSENTE",
                      cmd_cerca(A()) == 3)
        finally:
            globals()["ANCORA_BUDGET"], globals()["ANCORA_BYTE"] = sha_vero, byte_vero
            os.chdir(vecchia_cwd)

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="cerca per valore il run di una riga del budget")
    ap.add_argument("cmd", choices=["selftest", "bersagli", "cerca"])
    ap.add_argument("--bersaglio", default="nfw", choices=sorted(RIGHE))
    ap.add_argument("--budget", default=BUDGET)
    ap.add_argument("--radici", nargs="+", default=list(RADICI))
    ap.add_argument("--cap", type=int, default=CAP_BYTE)
    ap.add_argument("--storia", action="store_true",
                    help="secondo metro: legge da git i percorsi mai piu' su disco")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "selftest":
            return cmd_selftest(a)
        if a.cmd == "bersagli":
            return cmd_bersagli(a)
        return cmd_cerca(a)
    except RicercaError as e:
        print("RIFIUTATO: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_eccezioni_budget.py — toglie il digest dalla ragione di
`papers/paper2/paper2_budget_5_1.md` in `logs\eccezioni_rilascio.json`, finche' la voce 6.2 e'
aperta.

PERCHE'. Il budget e' il documento in cui ogni numero del manoscritto va riletto dalla sua fonte,
e ogni sotto-voce della 6.2 ne riscrive una riga: un'ancora per byte scritta dentro una ragione in
prosa invecchia alla prima patch. E' il terzo caso della stessa specie in due giorni, dopo
«rev. 3.29» e «tredicesima», e la ragione scritta per checklist e stato vale identica qui.

COSA NON SI PERDE. La misura del 16 set 2026 sta nel campo `new_value.vii_fuori_dal_rilascio` del
record 70, e il ledger e' append-only: nessuno la riscrive. Il CANCELLO 3 lo verifica sul ledger
prima di togliere qualunque cosa — un'ancora non si rimuove sulla parola di chi scrive la patch.

DOVE TORNERA'. Nel record che chiude la voce 6.2, quando il documento smette di muoversi e
diventa la fonte dei numeri del Paper 2.

UN CASO OPPOSTO A QUELLO DI IERI. In `paper2_patch_eccezioni_ragioni.py` il testo nuovo CITAVA la
frase sbagliata per dichiararla tale, e un controllo per sottostringa nuda rifiutava proprio la
correzione. Qui no: cio' che deve sparire non e' un'affermazione ma una MISURA, e citarla la
reintrodurrebbe. La regola che distingue i due casi: una frase falsa si puo' citare, un digest
stale no. Quindi il controllo per sottostringa nuda e' giusto qui, e il selftest verifica che il
testo nuovo NON contenga ne' il digest ne' il conteggio dei byte.

NON aggiunge e non toglie voci: cambia UN valore e nient'altro, e lo verifica.

CANCELLI:
  1. sha256 e dimensione del file uguali all'ancora (`61a802c4...`, 10 716 byte), 22 voci;
  2. IL SERIALIZZATORE DEVE ROUND-TRIPPARE: rileggendo il file e riscrivendolo senza toccare
     niente si devono riottenere gli STESSI byte, altrimenti la patch cambierebbe righe che non
     intende toccare;
  3. IL RECORD 70 DEVE PORTARE L'ANCORA CHE STIAMO TOGLIENDO: digest e byte, per quel percorso.
     Se non la porta, la ragione nuova sarebbe falsa e la misura andrebbe persa: RIFIUTA;
  4. il testo vecchio presente ESATTAMENTE una volta nel valore della SUA chiave, e il testo
     nuovo non ancora presente;
  5. dopo la patch: digest e conteggio dei byte ASSENTI da tutto il file, chiavi identiche, le
     altre 21 ragioni non toccate byte per byte;
  6. scrittura atomica, byte riletti, JSON riletto e confrontato. LF, chiavi ordinate.

Nessun numero di record e' cablato nei messaggi: il conteggio del ledger si misura e si stampa.

Uso:
  python src\paper2_patch_eccezioni_budget.py selftest
  python src\paper2_patch_eccezioni_budget.py dry-run
  python src\paper2_patch_eccezioni_budget.py apply
  python src\paper2_patch_eccezioni_budget.py verify
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

FILE = "logs/eccezioni_rilascio.json"
LEDGER = "src/paper2_v1_amendments.jsonl"

ANCORA_SHA = "61a802c4f3ee2a867516350d357ac2bc9f6820af0ca7811b35ba3110f37c80c0"
ANCORA_BYTE = 10716
ANCORA_VOCI = 22

CHIAVE = "papers/paper2/paper2_budget_5_1.md"

# L'ancora che questa patch toglie dalla prosa, e che il record 70 deve portare.
DIGEST = "0b7f8d5418875130fd38502e07e627a0105fa659585fdf67dc5b47aca565c6ae"
BYTE_DOC = 8993
RECORD_PORTANTE = 70

VECCHIO = (
    "FUORI dal versionamento, stessa decisione del 16 set 2026. Citato dal record 60. "
    "Ancorato per byte: sha256 " + DIGEST + ", " + str(BYTE_DOC) + " byte al 16 set 2026."
)

MARCA = "NESSUN DIGEST QUI MENTRE LA VOCE 6.2 E' APERTA"

NUOVO = (
    "FUORI dal versionamento, stessa decisione del 16 set 2026. Citato dal record 60. "
    + MARCA + ": e' il documento in cui ogni numero del manoscritto va riletto dalla sua fonte, "
    "e ogni sotto-voce della 6.2 ne riscrive una riga, quindi un'ancora per byte sarebbe stale "
    "alla prima patch — lo stesso motivo per cui checklist e stato non ne portano, e i loro "
    "numeri di revisione sono invecchiati lo stesso giorno in cui erano stati scritti. Questa "
    "voce ne portava una, misurata il 16 set 2026: quella misura resta dov'e' stata presa, nel "
    "campo new_value.vii_fuori_dal_rilascio del record 70, e un ledger append-only non la "
    "riscrive — verificato sul ledger prima di togliere il digest da qui. Il digest torna in "
    "questa voce col record che chiude la 6.2, quando il documento smette di muoversi e diventa "
    "la fonte dei numeri del Paper 2; fino ad allora cio' che lo ancora e' il record che lo "
    "nomina, e a che punto stia lo dice la sua intestazione."
)

# Cio' che dopo la patch non deve piu' comparire in NESSUN punto del file. Sono MISURE, non
# affermazioni: non si citano, si rimuovono.
DA_SPARIRE = (DIGEST, str(BYTE_DOC))
MIN_RAGIONE = 10


class PatchError(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def serializza(voci: dict) -> bytes:
    return (json.dumps(voci, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def carica(p: Path, controlla_ancora: bool = True) -> tuple:
    if not p.is_file():
        raise PatchError("file assente: %s" % p)
    dati = p.read_bytes()
    if controlla_ancora:
        got = (sha256_bytes(dati), len(dati))
        if got != (ANCORA_SHA, ANCORA_BYTE):
            raise PatchError(
                "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
                "  O il file non e' quello a 22 voci del 17 set 2026, o la patch e' gia' "
                "applicata." % (p, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
    try:
        voci = json.loads(dati.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise PatchError("%s non e' JSON leggibile: %r" % (p, e))
    if not isinstance(voci, dict):
        raise PatchError("%s non e' un oggetto JSON ma %s" % (p, type(voci).__name__))
    if controlla_ancora and len(voci) != ANCORA_VOCI:
        raise PatchError("%s: %d voci, attese %d" % (p, len(voci), ANCORA_VOCI))
    return voci, dati


def cancello_round_trip(voci: dict, dati: bytes) -> str:
    """Riscrivere il file senza toccare niente deve dare gli stessi byte."""
    rifatto = serializza(voci)
    if rifatto != dati:
        raise PatchError(
            "il serializzatore NON round-trippa: rileggendo e riscrivendo il file senza "
            "modifiche i byte cambiano (%d -> %d, sha %s -> %s). Questa patch toccherebbe anche "
            "cio' che non intende: fermarsi e guardare come e' stato scritto il file."
            % (len(dati), len(rifatto), sha256_bytes(dati)[:16], sha256_bytes(rifatto)[:16]))
    return "il serializzatore round-trippa: byte identici senza modifiche"


def _cerca_ancora(nodo, chiave: str):
    """Cerca ricorsivamente un oggetto {sha256, byte} associato a `chiave`, dentro dizionari,
    liste e stringhe che contengono JSON. Restituisce il primo trovato, o None."""
    if isinstance(nodo, dict):
        v = nodo.get(chiave)
        if isinstance(v, dict) and "sha256" in v:
            return v
        for x in nodo.values():
            trovato = _cerca_ancora(x, chiave)
            if trovato is not None:
                return trovato
    elif isinstance(nodo, list):
        for x in nodo:
            trovato = _cerca_ancora(x, chiave)
            if trovato is not None:
                return trovato
    elif isinstance(nodo, str) and chiave in nodo and "sha256" in nodo:
        try:
            return _cerca_ancora(json.loads(nodo), chiave)
        except Exception:  # noqa: BLE001
            return None
    return None


def cancello_record_portante(p: Path) -> str:
    """L'ancora che togliamo dalla prosa deve esistere altrove, misurata e non riscrivibile.
    Se il record che dovrebbe portarla non la porta, rimuoverla da qui la perderebbe."""
    if not p.is_file():
        raise PatchError("ledger assente: %s — senza il ledger non si puo' verificare che la "
                         "misura sopravviva altrove, e il digest non si tocca" % p)
    righe = [l for l in p.read_bytes().split(b"\n") if l.strip()]
    n = len(righe)
    if n < RECORD_PORTANTE:
        raise PatchError("ledger a %d record: il %d, che deve portare l'ancora, non esiste"
                         % (n, RECORD_PORTANTE))
    grezza = righe[RECORD_PORTANTE - 1].rstrip(b"\r").decode("utf-8")
    try:
        record = json.loads(grezza)
    except Exception as e:  # noqa: BLE001
        raise PatchError("il record %d non e' JSON leggibile: %r" % (RECORD_PORTANTE, e))

    ancora = _cerca_ancora(record, CHIAVE)
    if ancora is not None:
        got_sha = str(ancora.get("sha256", ""))
        got_byte = ancora.get("byte")
        if got_sha != DIGEST or got_byte != BYTE_DOC:
            raise PatchError(
                "il record %d porta per %s un'ancora DIVERSA da quella che questa patch "
                "rimuove:\n  nel record  %s  %r byte\n  qui         %s  %d byte\n  Guardare "
                "quale delle due e' la misura buona prima di toccare niente."
                % (RECORD_PORTANTE, CHIAVE, got_sha, got_byte, DIGEST, BYTE_DOC))
        return ("ledger a %d record; il %d porta l'ancora di %s nella sua struttura: %s, %d byte"
                % (n, RECORD_PORTANTE, CHIAVE, DIGEST[:16] + "...", BYTE_DOC))

    # Ripiego: la struttura non e' quella attesa, ma la misura puo' esserci come testo.
    if CHIAVE in grezza and DIGEST in grezza and str(BYTE_DOC) in grezza:
        return ("ledger a %d record; nel %d l'ancora di %s si trova nel TESTO del record e non "
                "nella struttura attesa: la misura sopravvive, ma la forma del record non e' "
                "quella che questo strumento sa leggere" % (n, RECORD_PORTANTE, CHIAVE))
    raise PatchError(
        "il record %d NON porta l'ancora di %s (ne' nella struttura ne' nel testo). Togliere il "
        "digest dalla ragione lo perderebbe: fermarsi, e cercare dove quella misura e' scritta."
        % (RECORD_PORTANTE, CHIAVE))


def costruisci(voci: dict) -> tuple:
    fuori = dict(voci)
    esiti = []
    if CHIAVE not in fuori:
        raise PatchError("la voce %s non c'e'" % CHIAVE)
    valore = fuori[CHIAVE]
    if valore.count(VECCHIO) != 1:
        raise PatchError("nel valore di %s il testo da sostituire compare %d volte (attesa 1)"
                         % (CHIAVE, valore.count(VECCHIO)))
    if NUOVO in valore:
        raise PatchError("nel valore di %s il testo nuovo e' gia' presente" % CHIAVE)
    fuori[CHIAVE] = valore.replace(VECCHIO, NUOVO, 1)
    esiti.append("%s: ragione riscritta (%+d caratteri)"
                 % (CHIAVE, len(fuori[CHIAVE]) - len(valore)))

    if set(fuori) != set(voci):
        raise PatchError("le chiavi sono cambiate: questa patch non aggiunge ne' toglie voci")
    toccate = sorted(k for k in voci if fuori[k] != voci[k])
    if toccate != [CHIAVE]:
        raise PatchError("valori cambiati: %r, atteso solo %r" % (toccate, CHIAVE))
    esiti.append("%d voci su %d non toccate, byte per byte" % (len(voci) - 1, len(voci)))

    testo = json.dumps(fuori, ensure_ascii=False)
    restati = [f for f in DA_SPARIRE if f in testo]
    if restati:
        raise PatchError("dopo la patch sopravvivono, da qualche parte nel file: %r"
                         % [f[:20] + "..." if len(f) > 20 else f for f in restati])
    esiti.append("digest e conteggio dei byte: assenti da tutto il file")
    for k, v in fuori.items():
        if not isinstance(v, str) or len(v) < MIN_RAGIONE:
            raise PatchError("ragione mancante o troppo corta per %s" % k)
    return fuori, esiti


def scrivi(p: Path, dati: bytes, inteso: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".patch_budget_", suffix=".json")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dati)
        os.replace(tmp, str(p))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    riletto = p.read_bytes()
    if riletto != dati:
        raise PatchError("%s: byte riletti diversi da quelli scritti" % p)
    if json.loads(riletto.decode("utf-8")) != inteso:
        raise PatchError("%s: il JSON riletto non e' quello inteso" % p)


def diff_valore(voci: dict, nuove: dict) -> str:
    a = [x + ".\n" for x in voci[CHIAVE].split(". ")]
    b = [x + ".\n" for x in nuove[CHIAVE].split(". ")]
    return "--- %s\n%s" % (CHIAVE, "".join(
        difflib.unified_diff(a, b, n=0, lineterm="\n")))


# ---------------------------------------------------------------------------

def _prepara(a) -> tuple:
    p = Path(a.file)
    voci, dati = carica(p)
    esiti = [cancello_round_trip(voci, dati), cancello_record_portante(Path(a.ledger))]
    nuove, e2 = costruisci(voci)
    return p, voci, nuove, esiti + e2


def cmd_dry_run(a) -> int:
    _, voci, nuove, esiti = _prepara(a)
    for x in esiti:
        print("  [ok] %s" % x)
    print()
    print(diff_valore(voci, nuove))
    b = serializza(nuove)
    print("file nuovo: %s  %d byte  %d voci" % (sha256_bytes(b), len(b), len(nuove)))
    print("nessun byte scritto.")
    return 0


def cmd_apply(a) -> int:
    p, _, nuove, esiti = _prepara(a)
    b = serializza(nuove)
    scrivi(p, b, nuove)
    for x in esiti:
        print("  [ok] %s" % x)
    print("\nscritto %s — %d voci" % (a.file, len(nuove)))
    print("file nuovo: %s  %d byte" % (sha256_bytes(b), len(b)))
    return 0


def cmd_verify(a) -> int:
    p = Path(a.file)
    voci, dati = carica(p, controlla_ancora=False)
    testo = dati.decode("utf-8")
    vecchia = (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE)
    restati = [f[:20] for f in DA_SPARIRE if f in testo]
    fatta = NUOVO in voci.get(CHIAVE, "")
    print("%s: %s  %d byte  voci=%d  marca=%s  ancora-vecchia=%s  residui=%s  modifica=%s"
          % (a.file, sha256_bytes(dati), len(dati), len(voci),
             "si" if MARCA in testo else "NO", "SI" if vecchia else "no",
             restati if restati else "nessuno", "fatta" if fatta else "NON TROVATA"))
    ok = (MARCA in testo and not vecchia and not restati and fatta
          and len(voci) == ANCORA_VOCI)
    print("ESITO:", "VERIFICATO" if ok else "NON VERIFICATO")
    return 0 if ok else 2


# ---------------------------------------------------------------------------

def _record_finto(n=74, sha=DIGEST, byte=BYTE_DOC, con_voce=True) -> bytes:
    out = b""
    for i in range(1, n + 1):
        if i == RECORD_PORTANTE:
            fuori = {"papers/paper2/paper2_5_5_smentite.md":
                     {"byte": 15129, "citato_da": "record 60", "sha256": "82b2878d"}}
            if con_voce:
                fuori[CHIAVE] = {"byte": byte, "citato_da": "record 60", "sha256": sha}
            r = {"item": "70", "new_value": {"vii_fuori_dal_rilascio": fuori}}
        else:
            r = {"item": str(i)}
        out += json.dumps(r, ensure_ascii=False).encode("utf-8") + b"\r\n"
    return out


def _voci_finte() -> dict:
    return {"altro/x.txt": "una ragione lunga abbastanza per passare",
            CHIAVE: VECCHIO}


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
        except PatchError:
            return True
        return False

    # --- la forma dei testi -------------------------------------------------
    controlla("il testo vecchio contiene il digest e il conteggio dei byte",
              DIGEST in VECCHIO and str(BYTE_DOC) in VECCHIO)
    controlla("IL TESTO NUOVO NON CITA IL DIGEST: una misura non si cita, si rimuove",
              DIGEST not in NUOVO)
    controlla("il testo nuovo non cita nemmeno il conteggio dei byte",
              str(BYTE_DOC) not in NUOVO)
    controlla("nessun elemento di DA_SPARIRE sopravvive nel testo nuovo",
              not any(f in NUOVO for f in DA_SPARIRE))
    controlla("il testo nuovo porta la marca", MARCA in NUOVO)
    controlla("il testo nuovo nomina il record che conserva la misura",
              "record 70" in NUOVO and "vii_fuori_dal_rilascio" in NUOVO)
    controlla("il testo nuovo dichiara quando il digest tornera'", "chiude la 6.2" in NUOVO)
    controlla("vecchio e nuovo sono diversi", VECCHIO != NUOVO)
    controlla("le due parti invariate sono conservate",
              NUOVO.startswith("FUORI dal versionamento, stessa decisione del 16 set 2026.")
              and "Citato dal record 60." in NUOVO)

    # --- costruisci ---------------------------------------------------------
    finte = _voci_finte()
    nuove, esiti = costruisci(finte)
    controlla("costruisci: un valore cambiato e le chiavi intatte",
              set(nuove) == set(finte)
              and [k for k in finte if nuove[k] != finte[k]] == [CHIAVE])
    controlla("costruisci: la voce estranea non e' toccata",
              nuove["altro/x.txt"] == finte["altro/x.txt"])
    controlla("costruisci: tre righe di esito, tutte piene",
              len(esiti) == 3 and all(x.strip() for x in esiti))
    controlla("seconda costruzione rifiutata", rifiuta(lambda: costruisci(nuove)))
    controlla("chiave mancante rifiutata",
              rifiuta(lambda: costruisci({"altro/x.txt": finte["altro/x.txt"]})))
    doppio = dict(finte)
    doppio[CHIAVE] = VECCHIO + " " + VECCHIO
    controlla("testo da sostituire due volte: rifiutato", rifiuta(lambda: costruisci(doppio)))
    misto = dict(finte)
    misto[CHIAVE] = "senza il testo atteso"
    controlla("testo da sostituire assente: rifiutato", rifiuta(lambda: costruisci(misto)))
    altrove = dict(finte)
    altrove["altro/y.txt"] = "il digest compare anche qui: " + DIGEST
    controlla("digest presente in un'ALTRA voce: rifiutato (sopravviverebbe nel file)",
              rifiuta(lambda: costruisci(altrove)))
    corta = dict(finte)
    corta["altro/z.txt"] = "x"
    controlla("ragione troppo corta: rifiutata", rifiuta(lambda: costruisci(corta)))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        p = base / "e.json"
        d = serializza(finte)
        p.write_bytes(d)
        voci, dati = carica(p, controlla_ancora=False)
        controlla("round-trip su file scritto dal serializzatore: passa",
                  bool(cancello_round_trip(voci, dati)))
        p.write_bytes(json.dumps(finte, ensure_ascii=False, indent=4).encode("utf-8"))
        voci2, dati2 = carica(p, controlla_ancora=False)
        controlla("round-trip su file con altro indent: rifiutato",
                  rifiuta(lambda: cancello_round_trip(voci2, dati2)))

        # --- il cancello sul record portante -------------------------------
        led = base / "led.jsonl"
        led.write_bytes(_record_finto())
        controlla("record 70 con l'ancora giusta: passa", bool(cancello_record_portante(led)))
        controlla("il messaggio misura il conteggio del ledger, non lo cabla",
                  "74 record" in cancello_record_portante(led))
        led.write_bytes(_record_finto(n=200))
        controlla("ledger piu' lungo: passa comunque, e conta 200",
                  "200 record" in cancello_record_portante(led))
        led.write_bytes(_record_finto(n=69))
        controlla("ledger troppo corto: rifiutato", rifiuta(lambda: cancello_record_portante(led)))
        led.write_bytes(_record_finto(con_voce=False))
        controlla("record 70 SENZA l'ancora: rifiutato (la misura andrebbe persa)",
                  rifiuta(lambda: cancello_record_portante(led)))
        led.write_bytes(_record_finto(sha="a" * 64))
        controlla("record 70 con un digest DIVERSO: rifiutato",
                  rifiuta(lambda: cancello_record_portante(led)))
        led.write_bytes(_record_finto(byte=7920))
        controlla("record 70 con un conteggio byte diverso: rifiutato",
                  rifiuta(lambda: cancello_record_portante(led)))
        led.write_bytes(b'{"item": "70"}\r\n' * 70)
        controlla("record 70 che non nomina il percorso: rifiutato",
                  rifiuta(lambda: cancello_record_portante(led)))
        # struttura inattesa, misura presente come testo: passa e lo dichiara
        strana = b""
        for i in range(1, 71):
            if i == RECORD_PORTANTE:
                strana += json.dumps({"note": "fuori: %s sha256 %s, %d byte"
                                              % (CHIAVE, DIGEST, BYTE_DOC)}).encode() + b"\r\n"
            else:
                strana += b'{"item": "x"}\r\n'
        led.write_bytes(strana)
        esito = cancello_record_portante(led)
        controlla("ancora nel TESTO del record e non nella struttura: passa e lo dichiara",
                  "TESTO del record" in esito)
        led.write_bytes(b"non json\r\n" * 70)
        controlla("record 70 illeggibile: rifiutato",
                  rifiuta(lambda: cancello_record_portante(led)))
        controlla("ledger assente: rifiutato",
                  rifiuta(lambda: cancello_record_portante(base / "manca.jsonl")))

        # --- scrittura ------------------------------------------------------
        p.write_bytes(d)
        b = serializza(nuove)
        scrivi(p, b, nuove)
        controlla("scrivi: byte e JSON riletti coincidono",
                  p.read_bytes() == b and json.loads(p.read_text(encoding="utf-8")) == nuove)
        controlla("scrivi: nessun temporaneo residuo",
                  not [x for x in os.listdir(td) if x.startswith(".patch_budget_")])
        p.write_bytes(b'{"a": 1}')
        controlla("ancora sha sbagliata: rifiutata", rifiuta(lambda: carica(p)))
        p.write_bytes(b'["a"]')
        controlla("file che non e' un dizionario: rifiutato",
                  rifiuta(lambda: carica(p, controlla_ancora=False)))
        controlla("file assente: rifiutato",
                  rifiuta(lambda: carica(base / "manca.json", controlla_ancora=False)))

    # --- il file vero -------------------------------------------------------
    vero = Path(a.file)
    if vero.is_file():
        dati = vero.read_bytes()
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            voci = json.loads(dati.decode("utf-8"))
            testo = dati.decode("utf-8")
            controlla("file vero: 22 voci", len(voci) == ANCORA_VOCI)
            controlla("file vero: il serializzatore round-trippa", serializza(voci) == dati)
            controlla("file vero: il testo da sostituire e' nella sua voce, una volta",
                      voci.get(CHIAVE, "").count(VECCHIO) == 1)
            controlla("file vero: il digest compare una volta sola in tutto il file",
                      testo.count(DIGEST) == 1)
            controlla("file vero: il conteggio dei byte compare una volta sola",
                      testo.count(str(BYTE_DOC)) == 1)
        else:
            print("  [--] file vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] file vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="toglie il digest dalla ragione del budget, finche' la 6.2 e' aperta")
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--file", default=FILE)
    ap.add_argument("--ledger", default=LEDGER)
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

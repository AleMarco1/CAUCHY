#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_eccezioni_ragioni.py — tre ragioni di `logs\eccezioni_rilascio.json` che sono
invecchiate lo stesso giorno in cui sono state scritte.

  1. `papers/paper2/checklist_paper2.md` — la ragione dice «rev. 3.29 al 17 set 2026», e la
     checklist e' alla 3.30 dallo stesso giorno;
  2. `papers/paper2/paper2_stato.md` — dice «tredicesima al 17 set 2026», ed e' la
     quattordicesima;
  3. `logs/eccezioni_rilascio.json` — dice che la fonte autorevole e' «il record 70, che porta
     gli otto digest», ma le voci aggiunte dopo vengono dai record 72, 73 e 74.

Le prime due sono lo stesso errore per cui in quelle voci il digest NON c'e': una proprieta' che
cambia a ogni sessione non si scrive in un file che nessuno rivede. Il numero di revisione lo
porta l'intestazione del documento, dov'e' sempre esatto.

NON aggiunge e non toglie voci: cambia TRE valori e nient'altro, e lo verifica.

CANCELLI:
  1. sha256 e dimensione del file uguali all'ancora (`8bd9607c…`, 10 064 byte), 22 voci;
  2. IL SERIALIZZATORE DEVE ROUND-TRIPPARE: rileggendo il file e riscrivendolo senza toccare
     niente si devono riottenere gli STESSI byte. Se non succede, questa patch cambierebbe il
     file anche dove non intende, e rifiuta;
  3. ledger a >= 74 record col marker del 74 al 74: la terza ragione cita quel record;
  4. ogni testo vecchio presente ESATTAMENTE una volta nel valore della SUA chiave, e il testo
     nuovo non ancora presente;
  5. dopo la patch: i due numeri di revisione e la vecchia formula sulla fonte autorevole
     ASSENTI da tutto il file, le chiavi identiche, e i 19 valori non toccati byte per byte;
  6. scrittura atomica, byte riletti, JSON riletto e confrontato. LF, chiavi ordinate.

Uso:
  python src\paper2_patch_eccezioni_ragioni.py selftest
  python src\paper2_patch_eccezioni_ragioni.py dry-run
  python src\paper2_patch_eccezioni_ragioni.py apply
  python src\paper2_patch_eccezioni_ragioni.py verify
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

ANCORA_SHA = "8bd9607c2e3aa18d6e00205887da2304e64cc5bd62bbbf51eb165e4a3d72e49b"
ANCORA_BYTE = 10064
ANCORA_VOCI = 22

MARKER_74 = "emendamento-74-quattro-eccezioni-e-la-copia-byte-identica"

# (chiave, testo vecchio, testo nuovo). Il testo vecchio deve stare nel valore di QUELLA
# chiave, una volta sola: una sostituzione su tutto il file cadrebbe nella voce sbagliata.
MODIFICHE = [
    (
        "papers/paper2/checklist_paper2.md",
        "NESSUN DIGEST QUI, per scelta: la checklist si rivede a ogni sessione — rev. 3.29 al "
        "17 set 2026 — e un'ancora per byte sarebbe stale al primo patcher. Cio' che la ancora "
        "e' il record che la nomina, piu' l'intestazione di revisione dentro il documento.",
        "NESSUN DIGEST E NESSUN NUMERO DI REVISIONE QUI, per la stessa ragione: la checklist si "
        "rivede a ogni sessione, e sia un'ancora per byte sia un numero di revisione sarebbero "
        "stale al primo patcher. Questa voce ne portava uno — «rev. 3.29 al 17 set 2026» — e ha "
        "smesso di essere esatto lo stesso giorno, con la rev. 3.30. Cio' che la ancora e' il "
        "record che la nomina; a che punto stia lo dice l'intestazione dentro il documento, "
        "dov'e' sempre esatto.",
    ),
    (
        "papers/paper2/paper2_stato.md",
        "NESSUN DIGEST QUI, per la stessa ragione della checklist: e' l'indice unico di cio' "
        "che e' aperto e chiuso e cambia a ogni revisione (tredicesima al 17 set 2026). Lo "
        "ancora il record che lo nomina.",
        "NESSUN DIGEST E NESSUN NUMERO DI REVISIONE QUI, per la stessa ragione della checklist: "
        "e' l'indice unico di cio' che e' aperto e chiuso e cambia a ogni revisione. Questa "
        "voce ne portava uno — «tredicesima al 17 set 2026» — ed era gia' la quattordicesima "
        "quella sera. Lo ancora il record che lo nomina; a che punto stia lo dice la sua "
        "intestazione.",
    ),
    (
        "logs/eccezioni_rilascio.json",
        "NON e' la fonte autorevole: lo e' il record 70, che porta gli otto digest nel campo "
        "new_value.vii_fuori_dal_rilascio.",
        "NON e' la fonte autorevole: lo sono i RECORD. Il 70 dichiara la portata del rilascio "
        "nel campo new_value.vii_fuori_dal_rilascio, e le voci aggiunte dopo sono dichiarate "
        "dai record 72, 73 e 74, ciascuno con la propria ragione e i propri digest. Questa "
        "frase diceva «lo e' il record 70, che porta gli otto digest»: era vera quando il 70 "
        "era l'unico, e ha smesso di esserlo al primo record che ha aggiunto una voce.",
    ),
]

# Cio' che dopo la patch non deve piu' comparire in NESSUN punto del file, NELLA FORMA IN CUI
# STA nel file — non come frammento: i testi nuovi CITANO i tre difetti per dichiararli tali, e
# un controllo per sottostringa nuda rifiuterebbe proprio il testo che li corregge. E' lo stesso
# inciampo del patcher del §5 di REPRODUCIBILITY.md, la mattina dello stesso giorno.
DA_SPARIRE = ("si rivede a ogni sessione — rev. 3.29 al 17 set 2026 —",
              "cambia a ogni revisione (tredicesima al 17 set 2026)",
              "lo e' il record 70, che porta gli otto digest nel campo")
MARCA = "NESSUN DIGEST E NESSUN NUMERO DI REVISIONE QUI"
MIN_RAGIONE = 10


class PatchError(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def serializza(voci: dict) -> bytes:
    return (json.dumps(voci, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def carica(p: Path, controlla_ancora: bool = True) -> tuple:
    dati = p.read_bytes()
    if controlla_ancora:
        got = (sha256_bytes(dati), len(dati))
        if got != (ANCORA_SHA, ANCORA_BYTE):
            raise PatchError(
                "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
                "  O il file non e' quello a 22 voci, o la patch e' gia' applicata."
                % (p, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
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
    """Riscrivere il file senza toccare niente deve dare gli stessi byte. Se non e' cosi', il
    serializzatore non e' quello che ha scritto il file e la patch cambierebbe righe che non
    intende toccare."""
    rifatto = serializza(voci)
    if rifatto != dati:
        raise PatchError(
            "il serializzatore NON round-trippa: rileggendo e riscrivendo il file senza "
            "modifiche i byte cambiano (%d -> %d, sha %s -> %s). Questa patch toccherebbe anche "
            "cio' che non intende: fermarsi e guardare come e' stato scritto il file."
            % (len(dati), len(rifatto), sha256_bytes(dati)[:16], sha256_bytes(rifatto)[:16]))
    return "il serializzatore round-trippa: byte identici senza modifiche"


def cancello_ledger(p: Path) -> str:
    if not p.is_file():
        raise PatchError("ledger assente: %s" % p)
    righe = [l for l in p.read_bytes().split(b"\n") if l.strip()]
    if len(righe) < 74:
        raise PatchError("ledger a %d record: la terza ragione cita il record 74, che deve "
                         "esistere" % len(righe))
    r74 = json.loads(righe[73].rstrip(b"\r").decode("utf-8"))
    marker = str(r74.get("rules", {}).get("marker", ""))
    if marker != MARKER_74:
        raise PatchError("il record 74 non porta il marker atteso: %r" % marker)
    return "ledger a %d record, il 74 col suo marker" % len(righe)


def costruisci(voci: dict) -> tuple:
    fuori = dict(voci)
    esiti = []
    for chiave, vecchio, nuovo in MODIFICHE:
        if chiave not in fuori:
            raise PatchError("la voce %s non c'e'" % chiave)
        valore = fuori[chiave]
        if valore.count(vecchio) != 1:
            raise PatchError("nel valore di %s il testo da sostituire compare %d volte (attesa "
                             "1)" % (chiave, valore.count(vecchio)))
        if nuovo in valore:
            raise PatchError("nel valore di %s il testo nuovo e' gia' presente" % chiave)
        fuori[chiave] = valore.replace(vecchio, nuovo, 1)
        esiti.append("%s: ragione riscritta (%+d caratteri)"
                     % (chiave, len(fuori[chiave]) - len(valore)))

    if set(fuori) != set(voci):
        raise PatchError("le chiavi sono cambiate: questa patch non aggiunge ne' toglie voci")
    toccate = sorted(k for k in voci if fuori[k] != voci[k])
    attese = sorted(c for c, _, _ in MODIFICHE)
    if toccate != attese:
        raise PatchError("valori cambiati: %r, attesi %r" % (toccate, attese))
    esiti.append("%d voci su %d non toccate, byte per byte"
                 % (len(voci) - len(attese), len(voci)))

    testo = json.dumps(fuori, ensure_ascii=False)
    restati = [f for f in DA_SPARIRE if f in testo]
    if restati:
        raise PatchError("dopo la patch sopravvivono: %r" % restati)
    esiti.append("i due numeri di revisione e la vecchia formula sulla fonte: assenti da tutto "
                 "il file")
    for k, v in fuori.items():
        if not isinstance(v, str) or len(v) < MIN_RAGIONE:
            raise PatchError("ragione mancante o troppo corta per %s" % k)
    return fuori, esiti


def scrivi(p: Path, dati: bytes, inteso: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".patch_ragioni_", suffix=".json")
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


def diff_valori(voci: dict, nuove: dict) -> str:
    fuori = []
    for chiave, _, _ in MODIFICHE:
        a = voci[chiave].split(". ")
        b = nuove[chiave].split(". ")
        fuori.append("--- %s\n%s" % (chiave, "".join(
            difflib.unified_diff([x + ".\n" for x in a], [x + ".\n" for x in b], n=0,
                                 lineterm="\n"))))
    return "\n".join(fuori)


# ---------------------------------------------------------------------------

def cmd_dry_run(a) -> int:
    p = Path(a.file)
    voci, dati = carica(p)
    esiti = [cancello_round_trip(voci, dati), cancello_ledger(Path(a.ledger))]
    nuove, e2 = costruisci(voci)
    for x in esiti + e2:
        print("  [ok] %s" % x)
    print()
    print(diff_valori(voci, nuove))
    b = serializza(nuove)
    print("file nuovo: %s  %d byte  %d voci" % (sha256_bytes(b), len(b), len(nuove)))
    print("nessun byte scritto.")
    return 0


def cmd_apply(a) -> int:
    p = Path(a.file)
    voci, dati = carica(p)
    esiti = [cancello_round_trip(voci, dati), cancello_ledger(Path(a.ledger))]
    nuove, e2 = costruisci(voci)
    b = serializza(nuove)
    scrivi(p, b, nuove)
    for x in esiti + e2:
        print("  [ok] %s" % x)
    print("\nscritto %s — %d voci" % (a.file, len(nuove)))
    print("file nuovo: %s  %d byte" % (sha256_bytes(b), len(b)))
    return 0


def cmd_verify(a) -> int:
    p = Path(a.file)
    voci, dati = carica(p, controlla_ancora=False)
    testo = dati.decode("utf-8")
    vecchia = (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE)
    restati = [f for f in DA_SPARIRE if f in testo]
    non_fatte = [c for c, _, n in MODIFICHE if n not in voci.get(c, "")]
    print("%s: %s  %d byte  voci=%d  marca=%s  ancora-vecchia=%s  residui=%s  "
          "modifiche-non-trovate=%s"
          % (a.file, sha256_bytes(dati), len(dati), len(voci),
             "si" if MARCA in testo else "NO", "SI" if vecchia else "no",
             restati if restati else "nessuno", non_fatte if non_fatte else "nessuna"))
    ok = (MARCA in testo and not vecchia and not restati and not non_fatte
          and len(voci) == ANCORA_VOCI)
    print("ESITO:", "VERIFICATO" if ok else "NON VERIFICATO")
    return 0 if ok else 2


# ---------------------------------------------------------------------------

def _ledger_finto(n=74, marker=MARKER_74) -> bytes:
    out = b""
    for i in range(1, n + 1):
        out += json.dumps({"rules": {"marker": marker if i == 74 else "altro-%d" % i}}) \
            .encode("utf-8") + b"\r\n"
    return out


def _voci_finte() -> dict:
    v = {"altro/x.txt": "una ragione lunga abbastanza per passare"}
    for chiave, vecchio, _ in MODIFICHE:
        v[chiave] = "testa. " + vecchio + " coda."
    return v


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

    controlla("tre modifiche, tre chiavi distinte",
              len(MODIFICHE) == 3 and len({c for c, _, _ in MODIFICHE}) == 3)
    controlla("nessun testo nuovo contiene cio' che deve sparire",
              not any(f in n for _, _, n in MODIFICHE for f in DA_SPARIRE))
    controlla("ogni testo vecchio e' diverso dal nuovo", all(v != n for _, v, n in MODIFICHE))
    controlla("le due voci dei documenti portano la marca nuova",
              sum(1 for _, _, n in MODIFICHE if MARCA in n) == 2)
    controlla("i testi nuovi CITANO i tre difetti, per dichiararli tali",
              all(x in MODIFICHE[i][2] for i, x in ((0, "«rev. 3.29 al 17 set 2026»"),
                                                    (1, "«tredicesima al 17 set 2026»"),
                                                    (2, "«lo e' il record 70, che porta gli "
                                                        "otto digest»"))))
    controlla("i tre difetti stanno nei testi che vengono sostituiti",
              all(DA_SPARIRE[i] in MODIFICHE[i][1] for i in range(3)))

    finte = _voci_finte()
    nuove, esiti = costruisci(finte)
    controlla("costruisci: tre valori cambiati e le chiavi intatte",
              set(nuove) == set(finte)
              and sorted(k for k in finte if nuove[k] != finte[k])
              == sorted(c for c, _, _ in MODIFICHE))
    controlla("costruisci: la voce estranea non e' toccata",
              nuove["altro/x.txt"] == finte["altro/x.txt"])
    controlla("costruisci: cinque righe di esito", len(esiti) == 5)
    controlla("seconda costruzione rifiutata", rifiuta(lambda: costruisci(nuove)))
    controlla("chiave mancante rifiutata",
              rifiuta(lambda: costruisci({k: v for k, v in finte.items()
                                          if k != MODIFICHE[0][0]})))
    doppio = dict(finte)
    doppio[MODIFICHE[1][0]] = finte[MODIFICHE[1][0]] + " " + MODIFICHE[1][1]
    controlla("testo da sostituire due volte nella stessa voce: rifiutato",
              rifiuta(lambda: costruisci(doppio)))
    misto = dict(finte)
    misto[MODIFICHE[0][0]] = "senza il testo atteso"
    controlla("testo da sostituire assente: rifiutato", rifiuta(lambda: costruisci(misto)))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        # round-trip: file scritto dal serializzatore -> passa; file con altra forma -> rifiuta
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

        led = base / "led.jsonl"
        led.write_bytes(_ledger_finto())
        controlla("ledger a 74 col marker del 74: passa", bool(cancello_ledger(led)))
        led.write_bytes(_ledger_finto(n=73))
        controlla("ledger a 73: rifiutato", rifiuta(lambda: cancello_ledger(led)))
        led.write_bytes(_ledger_finto(marker="emendamento-73-il-deposito-non-contiene-il-protocollo"))
        controlla("marker sbagliato al 74: rifiutato", rifiuta(lambda: cancello_ledger(led)))

        p.write_bytes(d)
        b = serializza(nuove)
        scrivi(p, b, nuove)
        controlla("scrivi: byte e JSON riletti coincidono",
                  p.read_bytes() == b and json.loads(p.read_text(encoding="utf-8")) == nuove)
        controlla("scrivi: nessun temporaneo residuo",
                  not [x for x in os.listdir(td) if x.startswith(".patch_ragioni_")])
        p.write_bytes(b'{"a": 1}')
        controlla("ancora sha sbagliata: rifiutata", rifiuta(lambda: carica(p)))
        p.write_bytes(b'["a"]')
        controlla("file che non e' un dizionario: rifiutato",
                  rifiuta(lambda: carica(p, controlla_ancora=False)))

    vero = Path(a.file)
    if vero.is_file():
        dati = vero.read_bytes()
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            voci = json.loads(dati.decode("utf-8"))
            controlla("file vero: 22 voci", len(voci) == ANCORA_VOCI)
            controlla("file vero: il serializzatore round-trippa",
                      serializza(voci) == dati)
            controlla("file vero: ogni testo da sostituire e' nella sua voce, una volta",
                      all(voci.get(c, "").count(v) == 1 for c, v, _ in MODIFICHE))
            controlla("file vero: i tre difetti ci sono tutti",
                      all(f in dati.decode("utf-8") for f in DA_SPARIRE))
        else:
            print("  [--] file vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] file vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="tre ragioni invecchiate nel file delle eccezioni")
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

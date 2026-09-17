#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_repro_permock.py — voce 6.7, riaperta per una riga: la copia rimossa dal commit
352e024 e' BYTE-IDENTICA al sopravvissuto, e il §5 di `REPRODUCIBILITY.md` lo ha detto sbagliato
due volte, nelle due direzioni opposte.

  - prima stesura (c13ccc3):  «ne segnalavano una copia byte-identica: **non esiste**»
    -> falso: git la conserva, e il messaggio di 352e024 la chiama «byte-identical».
  - riscrittura del 17 set:    «il sopravvissuto ha un nome simile e **non e' la stessa cosa**»
    -> falso nella direzione opposta: ai byte E' la stessa cosa.

Cio' che il commit ha rimosso e' un'ETICHETTA, non un dato: il nome `permock` prometteva la
baseline test2 e il contenuto era il sottoinsieme HOD-refit (35304.6 +/- 1033.0, N=200). Il dato
sopravvive UNA volta, sotto il nome che lo descrive. Questa patch riscrive il paragrafo col
digest, e aggiunge la regola: leggere prima di dichiarare (record 70 §ix, record 74).

CANCELLI:
  1. sha256 e dimensione del documento uguali all'ancora (`7a72a509…`, 17 820 byte, 306 righe);
  2. il ledger deve essere a 74 record, l'ultimo col marker del record 74;
  3. LA MISURA, rifatta qui: `git show 352e024^:results/phase8_test2_permock.csv` contro
     `results/phase8_test2_permock_hodfit.csv` sul disco, byte per byte. Se non sono identici,
     la patch RIFIUTA: scriverebbe un'altra frase falsa;
  4. la frase sbagliata presente una volta prima, assente dopo; testo nuovo non gia' presente;
  5. scrittura atomica, byte riletti, LF.

Uso:
  python src\paper2_patch_repro_permock.py selftest
  python src\paper2_patch_repro_permock.py dry-run
  python src\paper2_patch_repro_permock.py apply
  python src\paper2_patch_repro_permock.py verify
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DOC = "REPRODUCIBILITY.md"
LEDGER = "src/paper2_v1_amendments.jsonl"

ANCORA_SHA = "7a72a509d2d0df937e776e5cf134b388cafbeefec202ecdfa5a520f29e7737ae"
ANCORA_BYTE = 17820
ANCORA_RIGHE = 306

MARKER_74 = "emendamento-74-quattro-eccezioni-e-la-copia-byte-identica"

COMMIT = "352e024"
RIMOSSO = "results/phase8_test2_permock.csv"
SOPRAVVISSUTO = "results/phase8_test2_permock_hodfit.csv"
SHA_ATTESO = "ae733e1e2a74bfffe19c4f9a3ef8fada16a9fa9a940ae20850e26b2b761f85bc"
BYTE_ATTESI = 10891

MARCA = "Correzione del 17 settembre 2026 (sera), record 74"

# Le due frasi false, nella forma in cui STANNO nel documento — non come frammento: il
# paragrafo nuovo le CITA per dichiararle false, e un controllo per sottostringa nuda
# rifiuterebbe il testo che le corregge.
FALSA_1 = "`_hodfit` qui sopra, che ha un nome simile e non è la stessa cosa."
FALSA_2 = "byte-identica segnalata da documenti interni precedenti **non esiste**"

VECCHIO = """**Correzione del 17 settembre 2026 (record 71).** Questo paragrafo diceva che la copia
byte-identica segnalata da documenti interni precedenti **non esiste**. La copia esisteva:
`results/phase8_test2_permock.csv`, **rimossa per causa** dal commit `352e024`, che è la voce
`P-A1` — la rimozione per cui il tier `records` è passato a 224 file e all'aggregato
`5364cf2e…`, registrata dall'emendamento 11. Al momento in cui questo documento è stato
scritto il file non c'era più, e **«non esiste adesso» è stato scritto come «non è mai
esistito»**: una rimozione registrata letta come una negazione. Il sopravvissuto è il
`_hodfit` qui sopra, che ha un nome simile e non è la stessa cosa.
"""

NUOVO_TEMPLATE = """**Correzione del 17 settembre 2026 (sera), record 74 — e correzione di una correzione.**
Questo paragrafo ha detto la cosa sbagliata due volte, nelle due direzioni opposte, e la misura
che le scioglie è una sola.

| | |
|---|---|
| copia rimossa, `{rimosso}` | recuperabile con `git show {commit}^:{rimosso}` — sha256 `{sha}`, {byte_fmt} byte |
| sopravvissuto, `{sopravvissuto}` | sul disco — sha256 `{sha}`, {byte_fmt} byte |
| confronto byte per byte | **IDENTICI** |

La prima stesura diceva che la copia byte-identica **non esiste**: falso, e git la conserva —
il messaggio di `{commit}` la chiama *byte-identical* a chiare lettere. La riscrittura di
quella mattina diceva che il sopravvissuto «ha un nome simile e non è la stessa cosa»: falso
nella direzione opposta, perché **ai byte è la stessa cosa**.

Quello che il commit ha rimosso è un'**etichetta**, non un dato. Il nome `permock` prometteva la
baseline test2; il contenuto era il **sottoinsieme HOD-refit** (35304.6 ± 1033.0, *N* = 200),
come dice il messaggio del commit. Il dato sopravvive **una volta**, sotto il nome che lo
descrive, ed è la voce `P-A1`: la rimozione per cui il tier `records` è passato a 224 file e
all'aggregato `5364cf2e…`, registrata dall'emendamento 11. Storia completa del percorso:
`e17da7a` (aggiunto), `684d1f3` (modificato), `{commit}` (rimosso).

**La regola, che è costata un mese.** Il record 70 §ix diceva: «REPRODUCIBILITY.md §5 tratta un
file di nome simile ma non identico … **va letto prima di dichiarare**». L'istruzione era giusta
e la lettura è arrivata il 17 settembre. Nel frattempo due versioni di questo paragrafo hanno
detto due cose opposte, entrambe false, e nessuna delle due costava più di un `git show`. Due
file byte-identici con nomi diversi non sono un duplicato di dati: sono un dato e un'etichetta.
"""


class PatchError(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cancello_ancora(p: Path, dati: bytes) -> None:
    got = (sha256_bytes(dati), len(dati))
    if got != (ANCORA_SHA, ANCORA_BYTE):
        raise PatchError("%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n"
                         "  trovato %s  %d byte" % (p, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
    if b"\r" in dati:
        raise PatchError("%s contiene CR: attesi fine riga LF" % p)
    if dati.count(b"\n") != ANCORA_RIGHE:
        raise PatchError("%s: %d righe, attese %d" % (p, dati.count(b"\n"), ANCORA_RIGHE))


def cancello_ledger(p: Path) -> str:
    if not p.is_file():
        raise PatchError("ledger assente: %s" % p)
    righe = [l for l in p.read_bytes().split(b"\n") if l.strip()]
    if len(righe) != 74:
        raise PatchError("ledger a %d record, atteso 74: questa patch cita il record 74.\n"
                         "  Prima: python src\\paper2_append_amend74.py applica" % len(righe))
    ultimo = json.loads(righe[-1].rstrip(b"\r").decode("utf-8"))
    marker = str(ultimo.get("rules", {}).get("marker", ""))
    if marker != MARKER_74:
        raise PatchError("l'ultimo record non e' il 74: marker %r" % marker)
    return marker


def misura(radice: Path, esegui=None) -> tuple:
    """La misura centrale, rifatta qui: se i due file non sono identici questa patch
    scriverebbe un'altra frase falsa, e quindi rifiuta."""
    if esegui is not None:
        dati_rim = esegui()
    else:
        try:
            r = subprocess.run(["git", "show", COMMIT + "^:" + RIMOSSO], cwd=str(radice),
                               capture_output=True)
        except FileNotFoundError:
            raise PatchError("git non trovato nel PATH")
        if r.returncode != 0:
            raise PatchError("git show %s^:%s uscito %d" % (COMMIT, RIMOSSO, r.returncode))
        dati_rim = r.stdout
    p = radice / SOPRAVVISSUTO
    if not p.is_file():
        raise PatchError("il sopravvissuto non e' sul disco: %s" % SOPRAVVISSUTO)
    dati_sop = p.read_bytes()
    sha = sha256_bytes(dati_rim)
    if dati_rim != dati_sop:
        raise PatchError(
            "i due file NON sono byte-identici:\n  rimosso:       %s  %d byte\n"
            "  sopravvissuto: %s  %d byte\n  Il paragrafo nuovo dichiara la byte-identita': se "
            "non c'e', va riscritto." % (sha, len(dati_rim), sha256_bytes(dati_sop),
                                         len(dati_sop)))
    if sha != SHA_ATTESO or len(dati_rim) != BYTE_ATTESI:
        raise PatchError("i byte non sono quelli dichiarati dal record 74:\n  misurato:   %s  %d\n"
                         "  dichiarato: %s  %d" % (sha, len(dati_rim), SHA_ATTESO, BYTE_ATTESI))
    return sha, len(dati_rim)


def testo_nuovo(sha: str, byte: int) -> str:
    return NUOVO_TEMPLATE.format(rimosso=RIMOSSO, sopravvissuto=SOPRAVVISSUTO, commit=COMMIT,
                                 sha=sha, byte_fmt="%s" % format(byte, ",d").replace(",", " "))


def calcola(doc: Path, ledger: Path, radice: Path, controlla_ledger=True, esegui=None) -> tuple:
    dati = doc.read_bytes()
    cancello_ancora(doc, dati)
    if controlla_ledger:
        cancello_ledger(ledger)
    sha, byte = misura(radice, esegui=esegui)
    testo = dati.decode("utf-8")
    if testo.count(VECCHIO) != 1:
        raise PatchError("il paragrafo da riscrivere non compare esattamente una volta: il "
                         "documento non e' quello che questa patch corregge")
    nuovo = testo_nuovo(sha, byte)
    if nuovo in testo:
        raise PatchError("il testo nuovo e' gia' presente: patch gia' applicata?")
    fuori = testo.replace(VECCHIO, nuovo, 1)
    sopravvissute = [f for f in (FALSA_1, FALSA_2) if f in fuori]
    if sopravvissute:
        raise PatchError("una delle due frasi false sopravvive nel testo nuovo: %r"
                         % [x[:40] for x in sopravvissute])
    if MARCA not in fuori:
        raise PatchError("marca di revisione assente dal testo nuovo")
    return testo, fuori, (sha, byte)


def scrivi(doc: Path, dati: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(doc.parent), prefix=".patch_permock_", suffix=".md")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dati)
        os.replace(tmp, str(doc))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if doc.read_bytes() != dati:
        raise PatchError("%s: i byte riletti non sono quelli scritti" % doc)


# ---------------------------------------------------------------------------

def cmd_dry_run(a) -> int:
    vecchio, nuovo, m = calcola(Path(a.doc), Path(a.ledger), Path(a.radice))
    print("".join(difflib.unified_diff(vecchio.splitlines(keepends=True),
                                       nuovo.splitlines(keepends=True),
                                       fromfile=DOC + " (prima)", tofile=DOC + " (dopo)", n=1)))
    print("  [ok] byte-identici, misurati adesso: %s  %d byte" % m)
    b = nuovo.encode("utf-8")
    print("file nuovo: %s  %d byte  %d righe" % (sha256_bytes(b), len(b), nuovo.count("\n")))
    print("nessun byte scritto.")
    return 0


def cmd_apply(a) -> int:
    _, nuovo, m = calcola(Path(a.doc), Path(a.ledger), Path(a.radice))
    b = nuovo.encode("utf-8")
    scrivi(Path(a.doc), b)
    print("  [ok] byte-identici, misurati adesso: %s  %d byte" % m)
    print("scritto %s" % a.doc)
    print("file nuovo: %s  %d byte  %d righe" % (sha256_bytes(b), len(b), nuovo.count("\n")))
    return 0


def cmd_verify(a) -> int:
    dati = Path(a.doc).read_bytes()
    t = dati.decode("utf-8")
    vecchia = (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE)
    false = [f[:40] for f in (FALSA_1, FALSA_2) if f in t]
    print("%s: %s  %d byte  marca=%s  ancora-vecchia=%s  frasi-false=%s  CR=%s"
          % (DOC, sha256_bytes(dati), len(dati), "si" if MARCA in t else "NO",
             "SI" if vecchia else "no", false if false else "nessuna",
             "SI" if b"\r" in dati else "no"))
    ok = MARCA in t and not vecchia and not false and b"\r" not in dati
    print("ESITO:", "VERIFICATO" if ok else "NON VERIFICATO")
    return 0 if ok else 2


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

    n = testo_nuovo(SHA_ATTESO, BYTE_ATTESI)
    controlla("il testo nuovo porta il digest e la dimensione", SHA_ATTESO in n and "10 891" in n)
    controlla("dichiara IDENTICI e nomina l'etichetta", "**IDENTICI**" in n
              and "un'**etichetta**" in n)
    controlla("dichiara sbagliate entrambe le versioni precedenti",
              "non esiste**: falso" in n and "nella direzione opposta" in n)
    controlla("cita la regola del record 70 §ix", "va leggere" not in n
              and "va letto prima di dichiarare" in n)
    controlla("porta la storia del percorso", "e17da7a" in n and "684d1f3" in n)
    controlla("nessuna delle due frasi false, nella forma in cui sta nel documento, e' nel "
              "testo nuovo", FALSA_1 not in n and FALSA_2 not in n)
    controlla("il testo nuovo le CITA entrambe, per dichiararle false",
              "«ha un nome simile e non è la stessa cosa»" in n and "non esiste**: falso" in n)
    controlla("le due frasi false stanno nel paragrafo che viene sostituito",
              FALSA_1 in VECCHIO and FALSA_2 in VECCHIO)

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "results").mkdir(parents=True, exist_ok=True)
        dati = b"x" * 10
        (base / SOPRAVVISSUTO).write_bytes(dati)
        controlla("digest diverso da quello del record 74: rifiutato",
                  rifiuta(lambda: misura(base, esegui=lambda: dati)))
        (base / SOPRAVVISSUTO).write_bytes(b"diverso")
        controlla("i due file non identici: rifiutato",
                  rifiuta(lambda: misura(base, esegui=lambda: dati)))
        (base / SOPRAVVISSUTO).unlink()
        controlla("sopravvissuto assente: rifiutato",
                  rifiuta(lambda: misura(base, esegui=lambda: dati)))

        led = base / "led.jsonl"
        righe = b""
        for i in range(1, 75):
            m = MARKER_74 if i == 74 else "altro-%d" % i
            righe += json.dumps({"rules": {"marker": m}}).encode("utf-8") + b"\r\n"
        led.write_bytes(righe)
        controlla("ledger a 74 col marker del 74: passa", cancello_ledger(led) == MARKER_74)
        led.write_bytes(righe[:righe.rindex(b"\r\n", 0, len(righe) - 2) + 2])
        controlla("ledger a 73: rifiutato", rifiuta(lambda: cancello_ledger(led)))

        doc = base / "d.md"
        doc.write_bytes(b"niente\n")
        controlla("ancora sha sbagliata: rifiutata",
                  rifiuta(lambda: cancello_ancora(doc, doc.read_bytes())))
        scrivi(doc, b"altro\n")
        controlla("scrivi atomico: byte riletti", doc.read_bytes() == b"altro\n")
        controlla("nessun temporaneo residuo",
                  not [x for x in os.listdir(td) if x.startswith(".patch_permock_")])

    vero = Path(a.doc)
    if vero.is_file():
        d = vero.read_bytes()
        if (sha256_bytes(d), len(d)) == (ANCORA_SHA, ANCORA_BYTE):
            t = d.decode("utf-8")
            controlla("documento vero: il paragrafo da riscrivere c'e' una volta",
                      t.count(VECCHIO) == 1)
            controlla("documento vero: il testo nuovo non c'e' ancora",
                      testo_nuovo(SHA_ATTESO, BYTE_ATTESI) not in t)
        else:
            print("  [--] documento vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] documento vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="voce 6.7: la copia rimossa era byte-identica")
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--doc", default=DOC)
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--radice", default=".")
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_budget_colonna.py — voce 6.2-i: dichiarare che cosa contiene la colonna «% di D», e
chiudere le righe 5 e 6 con l'esito della ricerca.

DUE COSE, TROVATE LEGGENDO LA CITAZIONE INVECE DI CERCARE IL FILE.

(1) LA COLONNA «% di D» NON PORTA LA STESSA QUANTITA' IN OGNI RIGA. Le righe 4 e 11 quotano il
    VALORE CENTRALE su D; le righe 5, 6 e 7 quotano il LIMITE |Δ|+3σ su D; la 9 quota punti
    percentuali di un'altra grandezza; la 10 una banda senza denominatore. Il Paper 1 (Tab. 8 e
    §7) quota SEMPRE il valore centrale, quindi la stessa intestazione copre due quantita' nei
    due documenti: su NFW il budget dice 1.769 % dove il Paper 1 dice 0.8 %, sullo snapshot
    1.354 % contro 0.2 % — fattori 2.25 e 7.34. Anche «% di N» ha due denominatori: N_DESI per la
    riga 11, <N>_mock per il rapporto della nota 4b.

(2) LE RIGHE 5 E 6 NON HANNO UN REGISTRO. `paper2_cerca_valore.py` rev.2, due metri, 17 set 2026:
    riga 5 ASSENTE; riga 6 un solo candidato, che letto e' un record per-mock della scala R12 e
    non un esperimento appaiato. Coerente col manoscritto: §7.1 descrive il test e non nomina
    alcun file.

NON serve una quattordicesima voce per il Paper 1: la relazione fra la riga 4 e il §7.2 e' gia'
P1-9 («da 60 a 2000 realizzazioni», stato PRONTA), che porta i tre punti da toccare e lo stesso
1.4σ. Questa patch la cita e non la duplica.

QUESTO STRUMENTO NON SI FIDA DELLE PERCENTUALI CHE SCRIVE: legge le tre basi (<N>_mock, N_DESI,
D) dalla §0 del documento e RICALCOLA ogni cifra della nota, compresi i due fattori. Se una non
coincide, rifiuta.

CANCELLI:
  1. sha256 e dimensione del documento uguali all'ancora (`777403c7...`, 10 822 byte);
  2. le tre basi lette dalla §0 coincidono con quelle attese;
  3. ogni percentuale e ogni fattore della nota RICALCOLATI dalle basi;
  4. ogni testo vecchio presente esattamente una volta; nessun testo nuovo gia' presente;
  5. dopo la patch: la forma vecchia del punto 3 assente, le due note presenti, le righe non
     toccate identiche;
  6. scrittura atomica, byte riletti.

Uso:
  python src\paper2_patch_budget_colonna.py selftest
  python src\paper2_patch_budget_colonna.py dry-run
  python src\paper2_patch_budget_colonna.py apply
  python src\paper2_patch_budget_colonna.py verify
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import re
import sys
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DOC = "papers/paper2/paper2_budget_5_1.md"
ANCORA_SHA = "777403c7a66961debee2c51e50ed0b764a88a6d4689be1ffdba76d7d042a68df"
ANCORA_BYTE = 10822

BASI = {"NGC": {"N_mock": Decimal("35436.686"), "N_DESI": Decimal("28256"),
                "D": Decimal("7180.686")},
        "SGC": {"N_mock": Decimal("18712.9675"), "N_DESI": Decimal("15122"),
                "D": Decimal("3590.9675")}}

# ogni cifra della nota C: (etichetta, numeratore, base, decimali, valore scritto)
CIFRE = [
    ("riga 4, centrale/D", "89.147", "D", "0.001", "1.241"),
    ("riga 5, centrale/D", "56.5", "D", "0.001", "0.787"),
    ("riga 5, limite/D", "127.0", "D", "0.001", "1.769"),
    ("riga 6, centrale/D", "13.25", "D", "0.001", "0.185"),
    ("riga 6, limite/D", "97.25", "D", "0.001", "1.354"),
    ("riga 7, centrale/D", "12.8", "D", "0.001", "0.178"),
    ("riga 7, limite/D", "73.1", "D", "0.001", "1.018"),
    ("riga 11, centrale/D", "309", "D", "0.001", "4.303"),
    ("riga 11, centrale/N_DESI", "309", "N_DESI", "0.001", "1.094"),
]
FATTORI = [("NFW, limite su centrale", "127.0", "56.5", "0.01", "2.25"),
           ("snapshot, limite su centrale", "97.25", "13.25", "0.01", "7.34")]

MARCA_C = "**Nota C — la colonna «% di *D*» non porta la stessa quantità in ogni riga.**"
MARCA_56 = "**Nota 5/6 — il run non è registrato, misurato su due metri"

V_CODA = "di un documento che si rivede invecchia alla prima patch.\n"

NOTA_C = """
**Nota C — la colonna «% di *D*» non porta la stessa quantità in ogni riga.** L'intestazione è
una sola e le quantità sono tre. Dichiarazione riga per riga, perché nessuna cella lo diceva:

| riga | che cosa contiene la cella | erosione | che cosa pubblica il Paper 1 |
|---|---|---|---|
| 1 | rimandata alla nota 1: la base va letta a *k*=1 | 1 | — |
| 2, 3 | nessuna percentuale | | — |
| 4 | **valore centrale / *D*** = 1.241 % | 0 | §7.2: −78.0 ± 8.0 su 60 coppie, **1.09 %** — la stessa misura a *n* diverso (voce **P1-9**, PRONTA) |
| 5 | **limite \\|Δ\\|+3σ / *D*** = 127/*D* = 1.769 %; il centrale è 0.787 % | — | §7.1 e Tab. 8: **0.79 / 0.8 %**, cioè il centrale |
| 6 | **limite / *D*** = 97.25/*D* = 1.354 %; il centrale scalato (13.25) è 0.185 % | — | Tab. 8: **0.2 %**, cioè il centrale |
| 7 | **limite / *D*** = 73.1/*D* = 1.018 %; il centrale è 0.178 % | — | — |
| 9 | punti percentuali del contrasto, non % di *D* | | — |
| 10 | banda, nessun denominatore | | — |
| 11 | **valore centrale / *D*** = 4.303 % | 0 | Tab. 8: **∼1 % di *N***, cioè 1.094 % su *N*_DESI |

**La regola, da qui in avanti: una riga che porta un limite quota il limite, una riga che porta
una misura quota il valore centrale, e la cella lo dice.** Il Paper 1 quota sempre il valore
centrale su *D*, in Tab. 8 come nel §7: la stessa intestazione copre quindi due quantità nei due
documenti, e sulle due righe che il Paper 1 pubblica i numeri differiscono di un fattore **2.25**
(NFW) e **7.34** (snapshot). Nessuna delle due è sbagliata; ciò che manca è la dichiarazione.
Prima che una di queste celle entri nel manoscritto va detto quale delle due quantità è.

**Anche «% di *N*» ha due denominatori**, e per una ragione: la riga 11 sposta *N*_DESI e si
divide per *N*_DESI (309 / 28 256 = 1.094 %), mentre il rapporto della nota 4b sposta la media dei
mock e si divide per ⟨*N*⟩_mock. Sono due grandezze diverse sotto la stessa etichetta, e ciascuna
va nominata per intero.
"""

NOTA_56 = """
**Nota 5/6 — il run non è registrato, misurato su due metri (17 settembre 2026).** Le due righe
hanno per fonte un manoscritto, e il manoscritto non nomina un file: il §7.1 del Paper 1 descrive
il test — inverse-CDF di un profilo NFW a concentrazione *c*(*M*), catalogo, HOD e seme fissi, 40
realizzazioni appaiate, appaiamento che cancella il 47 % della varianza — e la Tab. 8 attribuisce
lo snapshot a M26 §7 (vi). La ricerca per valore (`src/paper2_cerca_valore.py` rev.2: i tre valori
della riga sullo stesso record, su un registro di misura e non su una citazione di protocollo) ha
percorso i 399 file di testo sotto `results/` e `logs/` più i percorsi aggiunti in qualche ramo e
non più su disco. **Riga 5: nessun candidato, ASSENTE su entrambi i metri.** **Riga 6: un solo
candidato**, `results/paper1/per_mock_NGC_R12.jsonl` riga 168, che è un record per-mock della
scala di erosione R12 e non un esperimento appaiato snapshot/lightcone: coincidenza numerica in un
registro da 2000 record, non una fonte. Limiti dichiarati della ricerca: solo estensioni di testo
sotto il cap, quindi nessun `.npz`; e 20 file per la riga 5, 30 per la riga 6, scartati perché il
loro record è una riga sola oltre i 4000 caratteri, dove «stesso record» non discrimina. Il run è
avvenuto — il manoscritto lo descrive — ma il suo registro non è fra i file cercati: la citazione
resta quella giusta, e queste due righe non avranno un percorso accanto.
"""

V_PUNTO3 = ("3. **Righe 5 e 6**: individuare il file dei due valori che oggi hanno come fonte "
            "solo un\n   manoscritto (NFW, snapshot). La riga 4 è chiusa: nota 4b.\n")
N_PUNTO3 = ("3. **Righe 5 e 6 — chiuse con esito negativo**: il run non è registrato, misurato "
            "su due\n   metri il 17 settembre (nota 5/6). La riga 4 è chiusa: nota 4b.\n")

# il punto nuovo va DOPO il 4, non prima: una lista numerata 3, 5, 4 e' un difetto di per se'.
V_PUNTO4 = ("4. **Voce 5.1 della checklist** (rev. 3.21): togliere «denominatori conservativi "
            "ovunque» e\n   rimandare a questo documento. Aggiornare anche la banda, da "
            "«17–29 %» a 17.3–31.2 %.\n")
N_PUNTO5 = ("5. **Nota C**: decidere se portare tutta la colonna «% di *D*» al valore centrale, "
            "come fa\n   il Paper 1, o tenere i limiti dichiarando cella per cella. Finché la "
            "colonna è mista,\n   nessuna sua cifra entra nel manoscritto senza la nota "
            "accanto.\n")

MODIFICHE = [
    ("nota C e nota 5/6, in coda alle note della colonna A", V_CODA,
     V_CODA + NOTA_C + NOTA_56),
    ("§4 punto 3, riscritto", V_PUNTO3, N_PUNTO3),
    ("§4 punto 5, nuovo, dopo il punto 4", V_PUNTO4, V_PUNTO4 + N_PUNTO5),
]
DA_SPARIRE = ("3. **Righe 5 e 6**: individuare il file",)


class PatchError(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def carica(p: Path, controlla_ancora: bool = True) -> tuple:
    if not p.is_file():
        raise PatchError("documento assente: %s" % p)
    dati = p.read_bytes()
    if controlla_ancora:
        got = (sha256_bytes(dati), len(dati))
        if got != (ANCORA_SHA, ANCORA_BYTE):
            raise PatchError(
                "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
                "  O il documento non e' quello uscito dalla patch della riga 4, o questa patch "
                "e' gia' applicata." % (p, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
    return dati.decode("utf-8"), dati


def basi_dal_documento(testo: str) -> dict:
    """Le basi non si assumono: si leggono dove la §0 le dichiara."""
    fuori = {}
    for emi in ("NGC", "SGC"):
        m = re.search(r"^\| %s \| ([\d ]+\.\d+) \| ([\d ]+) \| \*\*([\d ]+\.\d+)\*\* \|$" % emi,
                      testo, re.M)
        if not m:
            raise PatchError("la §0 non dichiara la riga delle basi per %s nella forma attesa"
                             % emi)
        letto = {"N_mock": Decimal(m.group(1).replace(" ", "")),
                 "N_DESI": Decimal(m.group(2).replace(" ", "")),
                 "D": Decimal(m.group(3).replace(" ", ""))}
        if letto != BASI[emi]:
            raise PatchError("le basi %s lette dal documento %r non sono quelle attese %r"
                             % (emi, {k: str(v) for k, v in letto.items()},
                                {k: str(v) for k, v in BASI[emi].items()}))
        fuori[emi] = letto
    return fuori


def cancello_cifre(basi: dict) -> list:
    """Ricalcola ogni percentuale e ogni fattore scritti nella nota C."""
    esiti = []
    for etichetta, num, base, dec, scritto in CIFRE:
        calcolato = (Decimal(num) / basi["NGC"][base] * 100).quantize(
            Decimal(dec), rounding=ROUND_HALF_UP)
        if calcolato != Decimal(scritto):
            raise PatchError("%s: ricalcolato %s, nella nota %s. Guardare prima di scrivere."
                             % (etichetta, calcolato, scritto))
    esiti.append("%d percentuali della nota C ricalcolate dalle basi della §0" % len(CIFRE))
    for etichetta, a, b, dec, scritto in FATTORI:
        calcolato = (Decimal(a) / Decimal(b)).quantize(Decimal(dec), rounding=ROUND_HALF_UP)
        if calcolato != Decimal(scritto):
            raise PatchError("%s: ricalcolato %s, nella nota %s" % (etichetta, calcolato,
                                                                    scritto))
    esiti.append("i due fattori (%s) ricalcolati" % ", ".join(f[4] for f in FATTORI))
    return esiti


def costruisci(testo: str) -> tuple:
    fuori, esiti = testo, []
    for nome, vecchio, nuovo in MODIFICHE:
        if fuori.count(vecchio) != 1:
            raise PatchError("%s: il testo da sostituire compare %d volte (attesa 1)"
                             % (nome, fuori.count(vecchio)))
        if nuovo in fuori:
            raise PatchError("%s: il testo nuovo e' gia' presente" % nome)
        fuori = fuori.replace(vecchio, nuovo, 1)
        esiti.append("%s: applicata" % nome)
    for f in DA_SPARIRE:
        if f in fuori:
            raise PatchError("dopo la patch sopravvive la forma vecchia: %r" % f)
    for m in (MARCA_C, MARCA_56):
        if m not in fuori:
            raise PatchError("manca nel testo nuovo: %r" % m[:50])
    esiti.append("le due note presenti, la forma vecchia del punto 3 assente")
    if "P1-9" not in fuori:
        raise PatchError("la nota C non cita P1-9: senza quel rimando sembrerebbe che la "
                         "relazione col Paper 1 non sia gia' registrata")
    esiti.append("la nota C rimanda a P1-9 invece di duplicarla")
    vecchie, nuove = testo.split("\n"), fuori.split("\n")
    comuni = sum(l.size for l in
                 difflib.SequenceMatcher(None, vecchie, nuove).get_matching_blocks())
    esiti.append("%d righe su %d non toccate" % (comuni, len(vecchie)))
    return fuori, esiti


def scrivi(p: Path, dati: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".patch_colonna_", suffix=".md")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dati)
        os.replace(tmp, str(p))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if p.read_bytes() != dati:
        raise PatchError("%s: byte riletti diversi da quelli scritti" % p)


def _prepara(a) -> tuple:
    p = Path(a.doc)
    testo, _ = carica(p)
    basi = basi_dal_documento(testo)
    esiti = ["basi lette dalla §0: D = %s / %s, N_DESI = %s"
             % (basi["NGC"]["D"], basi["SGC"]["D"], basi["NGC"]["N_DESI"])]
    esiti += cancello_cifre(basi)
    nuovo, e2 = costruisci(testo)
    return p, testo, nuovo, esiti + e2


def cmd_dry_run(a) -> int:
    _, testo, nuovo, esiti = _prepara(a)
    for x in esiti:
        print("  [ok] %s" % x)
    print()
    print("".join(difflib.unified_diff(testo.splitlines(True), nuovo.splitlines(True),
                                       fromfile="prima", tofile="dopo", n=1)))
    b = nuovo.encode("utf-8")
    print("documento nuovo: %s  %d byte" % (sha256_bytes(b), len(b)))
    print("nessun byte scritto.")
    return 0


def cmd_apply(a) -> int:
    p, _, nuovo, esiti = _prepara(a)
    b = nuovo.encode("utf-8")
    scrivi(p, b)
    for x in esiti:
        print("  [ok] %s" % x)
    print("\nscritto %s" % a.doc)
    print("documento nuovo: %s  %d byte" % (sha256_bytes(b), len(b)))
    return 0


def cmd_verify(a) -> int:
    testo, dati = carica(Path(a.doc), controlla_ancora=False)
    vecchia = (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE)
    restati = [f[:40] for f in DA_SPARIRE if f in testo]
    ok = (MARCA_C in testo and MARCA_56 in testo and N_PUNTO3 in testo
          and not vecchia and not restati and "P1-9" in testo)
    print("%s: %s  %d byte  nota-C=%s  nota-5/6=%s  punto-3=%s  ancora-vecchia=%s  residui=%s"
          % (a.doc, sha256_bytes(dati), len(dati), "si" if MARCA_C in testo else "NO",
             "si" if MARCA_56 in testo else "NO", "nuovo" if N_PUNTO3 in testo else "NO",
             "SI" if vecchia else "no", restati if restati else "nessuno"))
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

    controlla("tre modifiche, tre ancore distinte",
              len(MODIFICHE) == 3 and len({v for _, v, _ in MODIFICHE}) == 3)
    controlla("il punto nuovo e' il 5 e va dopo il 4: nessuna lista 3, 5, 4",
              N_PUNTO5.startswith("5.") and MODIFICHE[2][2].index("5.")
              > MODIFICHE[2][2].index("4."))
    controlla("la nota C dichiara la regola generale",
              "una riga che porta un limite quota il limite" in NOTA_C)
    controlla("la nota C cita P1-9 e non la duplica",
              "P1-9" in NOTA_C and "da 60 a 2000" not in NOTA_C)
    controlla("la nota C dichiara i due denominatori di «% di N»",
              "*N*_DESI" in NOTA_C and "⟨*N*⟩_mock" in NOTA_C)
    controlla("la nota 5/6 dichiara entrambi i metri",
              "ASSENTE su entrambi i metri" in NOTA_56 and "non più su disco" in NOTA_56)
    controlla("la nota 5/6 dichiara i limiti della ricerca",
              ".npz" in NOTA_56 and "4000 caratteri" in NOTA_56)
    controlla("la nota 5/6 non chiama «fonte» il candidato della riga 6",
              "coincidenza numerica" in NOTA_56)
    controlla("il punto 3 nuovo non promette piu' di individuare un file",
              "individuare il file" not in N_PUNTO3)
    controlla("il punto 5 nuovo apre la decisione sulla colonna",
              "Nota C" in N_PUNTO5 and "decidere" in N_PUNTO5)

    basi = dict(BASI)
    controlla("le cifre della nota si ricalcolano dalle basi", bool(cancello_cifre(basi)))
    controlla("base falsata: cifre rifiutate",
              rifiuta(lambda: cancello_cifre(
                  {"NGC": {"N_mock": Decimal("1"), "N_DESI": Decimal("1"),
                           "D": Decimal("7000")}, "SGC": BASI["SGC"]})))
    controlla("una cifra sbagliata nella tabella: rifiutata",
              rifiuta(lambda: (CIFRE.append(("finta", "1", "D", "0.001", "9.999")),
                               cancello_cifre(basi))[1]) or CIFRE.pop() is not None)

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        p = base / "d.md"
        p.write_bytes(b"prima")
        scrivi(p, b"dopo")
        controlla("scrivi: byte riletti coincidono", p.read_bytes() == b"dopo")
        controlla("scrivi: nessun temporaneo residuo",
                  not [x for x in os.listdir(td) if x.startswith(".patch_colonna_")])
        p.write_bytes(b"x")
        controlla("ancora sbagliata: rifiutata", rifiuta(lambda: carica(p)))
        controlla("documento assente: rifiutato",
                  rifiuta(lambda: carica(base / "manca.md", controlla_ancora=False)))

    vero = Path(a.doc)
    if vero.is_file():
        dati = vero.read_bytes()
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            testo = dati.decode("utf-8")
            controlla("documento vero: ogni ancora c'e' una volta sola",
                      all(testo.count(v) == 1 for _, v, _ in MODIFICHE))
            controlla("documento vero: le basi della §0 si leggono e coincidono",
                      bool(basi_dal_documento(testo)))
            controlla("documento vero: la nota 4b c'e' (questa patch le va in coda)",
                      "Nota 4b" in testo)
            nuovo, esiti = costruisci(testo)
            controlla("documento vero: la patch si costruisce", len(esiti) == 6)
            controlla("documento vero: seconda costruzione rifiutata",
                      rifiuta(lambda: costruisci(nuovo)))
        else:
            print("  [--] documento vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] documento vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="dichiara la colonna «% di D» e chiude le righe 5-6")
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--doc", default=DOC)
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

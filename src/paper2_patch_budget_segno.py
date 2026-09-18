#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_budget_segno.py — voce 6.2, punto 5 del §4: la colonna «% di D» si sdoppia in
limite e misura col segno.

LA DECISIONE. La R3 del documento vieta l'opzione «tutto al valore centrale»: un risultato con
|Δ|/σ < 3 si scrive come limite |Δ|+3σ, con la misura accanto e MAI il solo valore centrale — e le
righe 5, 6 e 7 stanno a 2.4σ o meno. Ma il centrale serve, per tre cose che il limite non fa: e'
sommabile (i limiti no, e la R3 lo dice), e' confrontabile col Paper 1 riga per riga, ed e' la
quantita' che un lettore ricalcola da se'. Quindi due colonne, che e' la forma che la R3 chiede:
limite come primario, misura accanto.

E UN ERRORE DI SEGNO, TROVATO SCRIVENDO QUESTA PATCH. La colonna nuova porta il segno
dell'effetto su *D*, non quello della cella «valore». Sulle righe 4, 5, 6 e 7 i due coincidono.
Sulla riga 11 NO: +309 e' uno spostamento di N_DESI, e D = <N>_mock - N_DESI, quindi su D fa -309.
La colonna vecchia scriveva 4.303 senza segno accanto a un +309: due quantita' opposte nella
stessa riga, lette come concordi. Tutti e cinque i termini ACCORCIANO il deficit; nessuno lo
allunga. Era stato detto il contrario, ed era sbagliato.

E il limite della riga 6 non e' come gli altri due: la misura e' per unita' di z, e diventa
13.25 +/- 28 solo dopo aver fissato Dz ~ 0.25, che e' una scelta. Nota 6b.

QUESTO STRUMENTO NON SI FIDA DI CIO' CHE SCRIVE:
  - per ogni riga verifica che la cella attuale sia quella dichiarata, prima di sostituirla;
  - RICALCOLA ogni percentuale dalle basi lette dalla §0 del documento;
  - dopo la patch pretende che TUTTE le righe della tabella della §1 abbiano lo stesso numero di
    celle dell'intestazione: una tabella con una riga corta e' un difetto che si vede solo
    rendendola.

CANCELLI:
  1. sha256 e dimensione uguali all'ancora (`748cdfc9...`, 14 559 byte);
  2. ogni prefisso di riga individua UNA sola riga del documento;
  3. la cella attuale di ogni riga e' quella dichiarata;
  4. ogni percentuale ricalcolata dalle basi della §0;
  5. dopo: celle allineate su tutte le righe, note S e 6b presenti, ogni misura numerica col
     segno, il punto 5 non e' piu' una domanda;
  6. scrittura atomica, byte riletti.

Uso:
  python src\paper2_patch_budget_segno.py selftest
  python src\paper2_patch_budget_segno.py dry-run
  python src\paper2_patch_budget_segno.py apply
  python src\paper2_patch_budget_segno.py verify
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
ANCORA_SHA = "748cdfc943aef91689f66ee9e7bd45baed79c7a4d8d326b22a8cc22e251f68c1"
ANCORA_BYTE = 14559

BASI = {"NGC": {"N_mock": Decimal("35436.686"), "N_DESI": Decimal("28256"),
                "D": Decimal("7180.686")},
        "SGC": {"N_mock": Decimal("18712.9675"), "N_DESI": Decimal("15122"),
                "D": Decimal("3590.9675")}}

# (etichetta, numeratore, emisfero, base, valore scritto nella colonna delle misure)
CIFRE = [
    ("riga 4 NGC", "89.147", "NGC", "D", "1.241"),
    ("riga 4 SGC", "56.494", "SGC", "D", "1.573"),
    ("riga 5", "56.5", "NGC", "D", "0.787"),
    ("riga 6", "13.25", "NGC", "D", "0.185"),
    ("riga 7", "12.8", "NGC", "D", "0.178"),
    ("riga 11 su D", "309", "NGC", "D", "4.303"),
    ("riga 11 su N_DESI", "309", "NGC", "N_DESI", "1.094"),
]

INTESTAZIONE_V = ("| # | termine | valore | fonte | denominatore | forma | % di *D* |")
INTESTAZIONE_N = ("| # | termine | valore | fonte | denominatore | forma | limite, % di *D* | "
                  "misura Δ*D*/*D*, col segno |")
SEPARATORE_V = "|---|---|---|---|---|---|---:|"
SEPARATORE_N = "|---|---|---|---|---|---|---:|---:|"

# (prefisso unico della riga, cella attuale, cella limite, cella misura)
RIGHE = [
    ("| 1 | **AP**, Δ*D*_max", " vedi nota 1 ", " — ", " vedi nota 1 "),
    ("| 2 | sistematico su (1)", " — ", " — ", " — "),
    ("| 3 | (e) conteggio voxel", " — ", " — ", " — "),
    ("| 4 | **ripesatura FKP** dei mock", " **1.241** / 1.573 *derivato* (nota 4b) ", " — ",
     " **−1.241** / **−1.573** *derivato* (nota 4b) "),
    ("| 5 | profilo dei satelliti NFW", " 1.769 *derivato* ", " 1.769 *derivato* ",
     " **−0.787** *derivato* "),
    ("| 6 | snapshot contro lightcone", " 1.354 *derivato* ",
     " 1.354 *derivato* (nota 6b) ", " **−0.185** *derivato* "),
    ("| 7 | tiling sulla media", " 1.018 *derivato* ", " 1.018 *derivato* ",
     " **−0.178** *derivato* "),
    ("| 9 | residuo di maschera", " ±2.4 pp *derivato* ", " — ",
     " ±2.4 pp *derivato* (banda; verso: compressione) "),
    ("| 10 | banda del deficit", " — ", " — ", " — "),
    ("| 11 | DESI ricostruito a pesi unitari", " **4.303** *derivato* (1.094 % di *N*) ", " — ",
     " **−4.303** *derivato* (nota S; −1.094 % su *N*_DESI) "),
]

NOTA_C_11_V = "| 11 | **valore centrale / *D*** = 4.303 % | 0 |"
NOTA_C_11_N = ("| 11 | **valore centrale / *D*** = **−4.303 %** (nota S: +309 su *N*_DESI vale "
               "−309 su *D*) | 0 |")

MARCA_S = "**Nota S — il segno è quello di Δ*D*"
MARCA_6B = "**Nota 6b — il limite della riga 6 contiene una scelta.**"

V_CODA = ("resta quella giusta, e queste due righe non avranno un percorso accanto.\n")

NOTE_NUOVE = """
**Nota S — il segno è quello di Δ*D*, e su una riga ribalta la lettura.** La colonna delle misure
porta il segno dell'effetto sul **deficit**, non quello scritto nella cella «valore»: un termine
negativo accorcia *D*. Sulle righe 4, 5, 6 e 7 i due segni coincidono, perché quelle celle sono
già spostamenti del lato mock. Sulla **riga 11 no**: +309 è uno spostamento di *N*_DESI, e
*D* = ⟨*N*⟩_mock − *N*_DESI, quindi su *D* vale **−309**, cioè −4.303 %. La colonna precedente
scriveva 4.303 senza segno accanto a un +309: due quantità opposte nella stessa riga, lette come
concordi. **Tutti e cinque i termini accorciano il deficit, nessuno lo allunga** — ed è la ragione
per cui questa colonna esiste: senza segno la somma è priva di senso, e con il segno sbagliato è
peggio che priva di senso. La nota 4/11 resta valida e va letta con questa: i due lati non sono
simmetrici in ampiezza, ma hanno lo stesso verso su *D*.

**Nota 6b — il limite della riga 6 contiene una scelta.** I limiti delle righe 5 e 7 si calcolano
su quantità misurate: |Δ| + 3σ con Δ e σ come stanno nella loro fonte. Quello della riga 6 no: la
misura è −53 ± 112 **per unità di *z***, e diventa 13.25 ± 28 soltanto dopo aver fissato
Δ*z* ≈ 0.25, che è una scelta e non una misura. Il limite 97.25 la porta dentro, e con un Δ*z*
diverso cambia in proporzione. Tre limiti nella stessa colonna, uno dei quali dipende da un
parametro dichiarato: va letto con quel parametro accanto.
"""

V_PUNTO5 = ("5. **Nota C**: decidere se portare tutta la colonna «% di *D*» al valore centrale, "
            "come fa\n   il Paper 1, o tenere i limiti dichiarando cella per cella. Finché la "
            "colonna è mista,\n   nessuna sua cifra entra nel manoscritto senza la nota "
            "accanto.\n")
N_PUNTO5 = ("5. **Nota C — deciso il 17 settembre: due colonne.** Il limite resta il primario, "
            "perché la\n   R3 vieta il solo valore centrale sotto 3σ; accanto compare la misura "
            "Δ*D*/*D* col segno,\n   che è la quantità sommabile e quella che il Paper 1 "
            "pubblica. È la forma che la R3 chiede:\n   limite come primario, misura accanto "
            "(note S e 6b).\n")

DA_SPARIRE = (INTESTAZIONE_V + "\n", SEPARATORE_V + "\n", NOTA_C_11_V,
              "decidere se portare tutta la colonna")


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
                "  O il documento non e' quello uscito dalla patch della colonna, o questa patch "
                "e' gia' applicata." % (p, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
    return dati.decode("utf-8"), dati


def basi_dal_documento(testo: str) -> dict:
    fuori = {}
    for emi in ("NGC", "SGC"):
        m = re.search(r"^\| %s \| ([\d ]+\.\d+) \| ([\d ]+) \| \*\*([\d ]+\.\d+)\*\* \|$" % emi,
                      testo, re.M)
        if not m:
            raise PatchError("la §0 non dichiara le basi per %s nella forma attesa" % emi)
        letto = {"N_mock": Decimal(m.group(1).replace(" ", "")),
                 "N_DESI": Decimal(m.group(2).replace(" ", "")),
                 "D": Decimal(m.group(3).replace(" ", ""))}
        if letto != BASI[emi]:
            raise PatchError("basi %s lette %r, attese %r" % (emi, letto, BASI[emi]))
        fuori[emi] = letto
    return fuori


def cancello_cifre(basi: dict) -> list:
    for etichetta, num, emi, base, scritto in CIFRE:
        calcolato = (Decimal(num) / basi[emi][base] * 100).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP)
        if calcolato != Decimal(scritto):
            raise PatchError("%s: ricalcolato %s, scritto %s" % (etichetta, calcolato, scritto))
    return ["%d percentuali della colonna delle misure ricalcolate dalle basi della §0"
            % len(CIFRE)]


def _riga_unica(testo: str, prefisso: str) -> str:
    trovate = [l for l in testo.split("\n") if l.startswith(prefisso)]
    if len(trovate) != 1:
        raise PatchError("il prefisso %r individua %d righe (attesa 1): ancora inservibile"
                         % (prefisso, len(trovate)))
    return trovate[0]


def cancello_allineamento(testo: str, celle_attese: int) -> str:
    """Tutte le righe della tabella della §1 devono avere lo stesso numero di celle
    dell'intestazione. Una riga corta si vede solo rendendo il documento."""
    righe = testo.split("\n")
    try:
        i = righe.index(INTESTAZIONE_N)
    except ValueError:
        raise PatchError("l'intestazione nuova non c'e': allineamento non verificabile")
    guardate = 0
    for l in righe[i:]:
        if not l.startswith("|"):
            break
        n = len(l.split("|"))
        if n != celle_attese:
            raise PatchError("la tabella della §1 non e' allineata: %r ha %d celle invece di %d"
                             % (l[:60], n, celle_attese))
        guardate += 1
    if guardate != len(RIGHE) + 2:
        raise PatchError("nella tabella della §1 ho contato %d righe, attese %d"
                         % (guardate, len(RIGHE) + 2))
    return "tabella della §1 allineata: %d righe, %d celle ciascuna" % (guardate, celle_attese)


def costruisci(testo: str) -> tuple:
    fuori, esiti = testo, []

    fuori = fuori.replace(INTESTAZIONE_V + "\n", INTESTAZIONE_N + "\n", 1)
    fuori = fuori.replace(SEPARATORE_V + "\n", SEPARATORE_N + "\n", 1)
    esiti.append("intestazione e separatore: due colonne al posto di una")

    for prefisso, attuale, limite, misura in RIGHE:
        riga = _riga_unica(fuori, prefisso)
        celle = riga.split("|")
        if celle[-2] != attuale:
            raise PatchError("riga %r: la cella attuale e' %r, dichiarata %r. Il documento non "
                             "e' quello che questa patch descrive."
                             % (prefisso[:20], celle[-2], attuale))
        celle[-2] = limite
        celle.insert(-1, misura)
        fuori = fuori.replace(riga, "|".join(celle), 1)
    esiti.append("%d righe della tabella: limite a sinistra, misura col segno a destra"
                 % len(RIGHE))

    if fuori.count(NOTA_C_11_V) != 1:
        raise PatchError("la riga 11 della nota C non si trova nella forma attesa")
    fuori = fuori.replace(NOTA_C_11_V, NOTA_C_11_N, 1)
    esiti.append("nota C, riga 11: il segno dichiarato anche nella nota")

    if fuori.count(V_CODA) != 1:
        raise PatchError("la coda della nota 5/6 non si trova: %d volte" % fuori.count(V_CODA))
    fuori = fuori.replace(V_CODA, V_CODA + NOTE_NUOVE, 1)
    if fuori.count(V_PUNTO5) != 1:
        raise PatchError("il punto 5 del §4 non si trova nella forma attesa")
    fuori = fuori.replace(V_PUNTO5, N_PUNTO5, 1)
    esiti.append("note S e 6b aggiunte, punto 5 chiuso con la decisione")

    for f in DA_SPARIRE:
        if f in fuori:
            raise PatchError("dopo la patch sopravvive la forma vecchia: %r" % f[:50])
    for m in (MARCA_S, MARCA_6B):
        if m not in fuori:
            raise PatchError("manca nel testo nuovo: %r" % m[:40])
    esiti.append(cancello_allineamento(fuori, len(INTESTAZIONE_N.split("|"))))

    # il criterio e' «la cella dichiara un derivato», non «la cella contiene una cifra»: un
    # rimando come «vedi nota 1» porta una cifra e non e' un numero. Un \d nudo qui rifiutava la
    # riga 1, ed era un difetto del cancello, non del contenuto.
    senza_segno = [p for p, _, _, mis in RIGHE
                   if "*derivato*" in mis and "−" not in mis and "±" not in mis]
    if senza_segno:
        raise PatchError("celle che dichiarano un derivato e non portano il segno: %r"
                         % senza_segno)
    esiti.append("ogni cella con un derivato porta il segno (o il ± della banda)")

    vecchie, nuove = testo.split("\n"), fuori.split("\n")
    comuni = sum(l.size for l in
                 difflib.SequenceMatcher(None, vecchie, nuove).get_matching_blocks())
    esiti.append("%d righe su %d non toccate" % (comuni, len(vecchie)))
    return fuori, esiti


def scrivi(p: Path, dati: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".patch_segno_", suffix=".md")
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
    esiti = cancello_cifre(basi_dal_documento(testo))
    nuovo, e2 = costruisci(testo)
    return p, testo, nuovo, esiti + e2


def cmd_dry_run(a) -> int:
    _, testo, nuovo, esiti = _prepara(a)
    for x in esiti:
        print("  [ok] %s" % x)
    print()
    print("".join(difflib.unified_diff(testo.splitlines(True), nuovo.splitlines(True),
                                       fromfile="prima", tofile="dopo", n=0)))
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
    allineata = "no"
    try:
        allineata = cancello_allineamento(testo, len(INTESTAZIONE_N.split("|"))) and "si"
    except PatchError:
        pass
    ok = (MARCA_S in testo and MARCA_6B in testo and N_PUNTO5 in testo and allineata == "si"
          and not vecchia and not restati)
    print("%s: %s  %d byte  nota-S=%s  nota-6b=%s  punto-5=%s  tabella-allineata=%s  "
          "ancora-vecchia=%s  residui=%s"
          % (a.doc, sha256_bytes(dati), len(dati), "si" if MARCA_S in testo else "NO",
             "si" if MARCA_6B in testo else "NO", "deciso" if N_PUNTO5 in testo else "NO",
             allineata, "SI" if vecchia else "no", restati if restati else "nessuno"))
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

    controlla("dieci righe, dieci prefissi distinti",
              len(RIGHE) == 10 and len({r[0] for r in RIGHE}) == 10)
    controlla("l'intestazione nuova ha una colonna in piu' della vecchia",
              len(INTESTAZIONE_N.split("|")) == len(INTESTAZIONE_V.split("|")) + 1)
    controlla("il separatore nuovo ha una colonna in piu'",
              len(SEPARATORE_N.split("|")) == len(SEPARATORE_V.split("|")) + 1)
    controlla("intestazione e separatore concordano",
              len(INTESTAZIONE_N.split("|")) == len(SEPARATORE_N.split("|")))
    controlla("la riga 11 e' la sola che cambia segno rispetto alla cella «valore»",
              "−4.303" in RIGHE[-1][3] and "nota S" in RIGHE[-1][3])
    controlla("il limite resta solo dove c'e' un limite (righe 5, 6, 7)",
              [p for p, _, lim, _ in RIGHE if re.search(r"\d", lim)]
              == [RIGHE[4][0], RIGHE[5][0], RIGHE[6][0]])
    controlla("la nota 6b dichiara che il Δz e' una scelta",
              "una scelta e non una misura" in NOTE_NUOVE)
    controlla("la nota S dice che tutti i termini accorciano il deficit",
              "accorciano il deficit, nessuno lo allunga" in NOTE_NUOVE)
    controlla("la nota S non contraddice la nota 4/11, la cita",
              "La nota 4/11 resta valida" in NOTE_NUOVE)
    controlla("il punto 5 nuovo non e' piu' una domanda",
              "decidere se" not in N_PUNTO5 and "deciso" in N_PUNTO5)
    controlla("il punto 5 motiva col vincolo della R3", "R3" in N_PUNTO5)
    controlla("il cancello sul segno guarda i derivati, non le cifre: «vedi nota 1» passa",
              [p for p, _, _, m in RIGHE
               if "*derivato*" in m and "−" not in m and "±" not in m] == [])

    basi = dict(BASI)
    controlla("le percentuali si ricalcolano dalle basi", bool(cancello_cifre(basi)))
    controlla("base falsata: rifiutata",
              rifiuta(lambda: cancello_cifre(
                  {"NGC": {"D": Decimal("7000"), "N_DESI": Decimal("28256"),
                           "N_mock": Decimal("1")}, "SGC": BASI["SGC"]})))

    controlla("prefisso che individua due righe: rifiutato",
              rifiuta(lambda: _riga_unica("| 4 | x |\n| 4 | y |", "| 4 |")))
    controlla("prefisso che non individua nulla: rifiutato",
              rifiuta(lambda: _riga_unica("| 5 | x |", "| 4 |")))

    finto = (INTESTAZIONE_N + "\n" + SEPARATORE_N + "\n"
             + "\n".join("| %d | x | y | z | w | v | a | b |" % i for i in range(10)) + "\n\n")
    controlla("allineamento: tabella regolare accettata",
              bool(cancello_allineamento(finto, len(INTESTAZIONE_N.split("|")))))
    storta = finto.replace("| 3 | x | y | z | w | v | a | b |", "| 3 | x | y | z | w | v | a |")
    controlla("allineamento: una riga corta e' rifiutata",
              rifiuta(lambda: cancello_allineamento(storta,
                                                    len(INTESTAZIONE_N.split("|")))))
    corta = (INTESTAZIONE_N + "\n" + SEPARATORE_N + "\n"
             + "| 0 | x | y | z | w | v | a | b |\n\n")
    controlla("allineamento: conteggio delle righe sbagliato e' rifiutato",
              rifiuta(lambda: cancello_allineamento(corta, len(INTESTAZIONE_N.split("|")))))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        p = base / "d.md"
        p.write_bytes(b"prima")
        scrivi(p, b"dopo")
        controlla("scrivi: byte riletti coincidono", p.read_bytes() == b"dopo")
        controlla("scrivi: nessun temporaneo residuo",
                  not [x for x in os.listdir(td) if x.startswith(".patch_segno_")])
        p.write_bytes(b"x")
        controlla("ancora sbagliata: rifiutata", rifiuta(lambda: carica(p)))

    vero = Path(a.doc)
    if vero.is_file():
        dati = vero.read_bytes()
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            testo = dati.decode("utf-8")
            controlla("documento vero: ogni prefisso individua una riga sola",
                      all(_riga_unica(testo, r[0]) for r in RIGHE))
            controlla("documento vero: ogni cella attuale e' quella dichiarata",
                      all(_riga_unica(testo, r[0]).split("|")[-2] == r[1] for r in RIGHE))
            controlla("documento vero: intestazione e separatore vecchi presenti una volta",
                      testo.count(INTESTAZIONE_V + "\n") == 1
                      and testo.count(SEPARATORE_V + "\n") == 1)
            nuovo, esiti = costruisci(testo)
            controlla("documento vero: la patch si costruisce", len(esiti) == 7)
            controlla("documento vero: seconda costruzione rifiutata",
                      rifiuta(lambda: costruisci(nuovo)))
        else:
            print("  [--] documento vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] documento vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="sdoppia la colonna delle percentuali e dichiara il "
                                             "segno")
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

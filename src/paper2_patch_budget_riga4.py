#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_budget_riga4.py — voce 6.2-i: la riga 4 del budget 5.1, riletta dalla sua fonte.

Il budget dichiara di se': «prima che un numero entri nel manoscritto va riletto dalla sua fonte».
La riga 4 aveva per fonte il PRODUTTORE (`src/paper2_d2_v2.py`), non un file. Questa patch scrive
la fonte vera e corregge cio' che la rilettura ha trovato:

  (i)   il derivato NGC diceva 1.242 e vale 1.241. Il 1.242 viene da -89.15, il valore ARROTONDATO
        scritto nella cella; dalla fonte (-89.147) viene 1.24148 %. Un rapporto si calcola dalla
        fonte, non dalla cella. In SGC le due vie coincidono, ed e' il motivo per cui e' passato;
  (ii)  la misura e' a k=0 (campo `fkp.N_H1_k0`), come la base D della §0: riga e base sono
        omogenee, ma la colonna «% di D» non lo e', perche' la nota 1 sposta la riga 1 a k=1;
  (iii) nella fonte convivono la media dei rapporti e il rapporto delle medie: va dichiarato quale.

QUESTO STRUMENTO NON SI FIDA DEI NUMERI CHE SCRIVE:
  - rilegge i due file di fonte e rifiuta se `dN_medio`, `dN_sem`, `n`, `schema` o `region` non
    sono quelli dichiarati, o se lo sha del file e' cambiato;
  - legge le basi D e <N>_mock dalla §0 DEL DOCUMENTO, non da una costante;
  - RICALCOLA il derivato e rifiuta se non coincide con la cella nuova. Se un numero si puo'
    misurare, non si scrive.

UN CASO OPPOSTO A `paper2_patch_eccezioni_budget.py`, scritto lo stesso giorno. La' cio' che
doveva sparire era una MISURA (un digest), e citarla l'avrebbe reintrodotta: controllo per
sottostringa nuda. Qui cio' che deve sparire e' una CELLA SBAGLIATA, e la nota nuova cita «1.242»
per dichiararla tale: il controllo va fatto sulla FORMA ESATTA in cui la cella sta nel file. Le
due regole valgono insieme, e vanno distinte ogni volta.

CANCELLI:
  1. sha256 e dimensione del documento uguali all'ancora (`0b7f8d54...`, 8 993 byte);
  2. i due file di fonte esistono, con sha, schema, region, n, dN_medio, dN_sem dichiarati;
  3. le basi lette dalla §0 coincidono con quelle attese, e il derivato RICALCOLATO coincide con
     la cella nuova (NGC e SGC), e il rapporto delle medie con quello della nota;
  4. ogni testo vecchio presente ESATTAMENTE una volta; nessun testo nuovo gia' presente;
  5. dopo la patch: le tre forme vecchie assenti, «1.242» presente solo DENTRO la nota che la
     dichiara sbagliata, le righe non toccate identiche byte per byte;
  6. scrittura atomica, byte riletti e confrontati.

Uso:
  python src\paper2_patch_budget_riga4.py selftest
  python src\paper2_patch_budget_riga4.py dry-run
  python src\paper2_patch_budget_riga4.py apply
  python src\paper2_patch_budget_riga4.py verify
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DOC = "papers/paper2/paper2_budget_5_1.md"

ANCORA_SHA = "0b7f8d5418875130fd38502e07e627a0105fa659585fdf67dc5b47aca565c6ae"
ANCORA_BYTE = 8993

# --- la fonte, come dichiarata dalla misura del 17 set 2026 -----------------
FONTI = {
    "NGC": {
        "percorso": "results/paper2/d2_v2_NGC.json",
        "sha256": "a9661340609ce854b32bfe2bd93788f74e2c6dfb5b8b639dde622f55a3c03430",
        "byte": 7437,
        "dN_medio": -89.147,
        "dN_sem": 1.2474801797621673,
        "dN_su_N_medio": -0.0025129321327547294,
    },
    "SGC": {
        "percorso": "results/paper2/d2_v2_SGC.json",
        "sha256": "73d133029a0808e7f7675810767aba62a94b2d5579583ec69dcaf123ac924169",
        "byte": 7388,
        "dN_medio": -56.494,
        "dN_sem": 0.8311828405695275,
        "dN_su_N_medio": -0.0030155197221396193,
    },
}
SCHEMA = "paper2_d2_v2_v1"
N_ATTESO = 2000

# le basi che la §0 del documento deve dichiarare (verificate, non assunte)
BASI_D = {"NGC": Decimal("7180.686"), "SGC": Decimal("3590.9675")}
BASI_N = {"NGC": Decimal("35436.686"), "SGC": Decimal("18712.9675")}

# il derivato che la cella nuova porta: RICALCOLATO dal cancello 3
DERIVATO = {"NGC": "1.241", "SGC": "1.573"}
RAPPORTO_MEDIE_NGC = "0.2516"   # -89.147 / 35 436.686, a 4 decimali
MEDIA_RAPPORTI_NGC = "0.2513"   # campo dN_su_N_medio, a 4 decimali

# --- i tre pezzi di testo ---------------------------------------------------
V_FONTE = "| registro di `src/paper2_d2_v2.py`, *n* = 2000 |"
N_FONTE = ("| `results/paper2/d2_v2_{NGC,SGC}.json`, campi `dN_medio` e `dN_sem`, *n* = 2000 "
           "(nota 4b) |")

V_CELLA = "| 1.242 / 1.573 *derivato* |"
N_CELLA = "| **1.241** / 1.573 *derivato* (nota 4b) |"

V_CODA_NOTA = ("M26 «bounded at 1–2% of the deficit» vale per la prima e **non** per la seconda: "
               "è la voce aperta\ndell'erratum.\n")

NOTA_4B = """
**Nota 4b — la riga 4, riletta dalla sua fonte (voce 6.2-i, 17 settembre 2026).** La fonte non è
il registro dello strumento ma i due file `results/paper2/d2_v2_{NGC,SGC}.json`, schema
`paper2_d2_v2_v1`, scritti l'11 settembre: `dN_medio` = **−89.147** / **−56.494**, `dN_sem` =
**1.2475** / **0.8312**, `n` = 2000. Tre cose che la rilettura ha trovato.

**(i) Il derivato NGC diceva 1.242 e vale 1.241.** Il 1.242 si ottiene da −89.15, cioè dal valore
arrotondato scritto in questa tabella; dalla fonte, −89.147, viene 1.24148 % e quindi 1.241. Non è
una convenzione di arrotondamento da dichiarare: è un rapporto calcolato su un numero già
arrotondato. **Un rapporto si calcola dalla fonte, non dalla cella.** In SGC le due vie coincidono
(1.5732 contro 1.5731), ed è la ragione per cui l'errore è passato; le altre cinque celle
*derivato* — righe 1, 5, 6, 7 e 11 — si riproducono dalla fonte.

**(ii) La misura è a *k*=0.** Il campo confrontato è `fkp.N_H1_k0`, e la base *D* della §0 è
anch'essa a *k*=0: lo conferma la riga 1, 98.3 / 7 180.686 = 1.369 %, il valore che la nota 1 dà
come «a *k*=0». Riga e base sono dunque omogenee, ma la colonna «% di *D*» non lo è, perché la
nota 1 sposta la riga 1 su base *k*=1 e lascia le altre dove sono. Finché la colonna non si sposta
tutta, ogni cella dichiara il proprio livello.

**(iii) Due quantità diverse, entrambe nella fonte.** `dN_su_N_medio` = −0.0025129 è la **media
dei rapporti** (0.2513 % di *N*); il **rapporto delle medie**, −89.147 / 35 436.686, dà 0.2516 %.
Il manoscritto ne citerà una, e quale va dichiarato.

Gli sha dei due file stanno nel record che chiude la voce 6.2, non qui: un digest dentro la prosa
di un documento che si rivede invecchia alla prima patch.
"""

V_PUNTO3 = ("3. **Righe 4, 5, 6**: individuare il file dei tre valori che oggi hanno come fonte "
            "solo un\n   manoscritto (NFW, snapshot) o solo lo strumento (D2 su v2).\n")
N_PUNTO3 = ("3. **Righe 5 e 6**: individuare il file dei due valori che oggi hanno come fonte "
            "solo un\n   manoscritto (NFW, snapshot). La riga 4 è chiusa: nota 4b.\n")

MODIFICHE = [
    ("riga 4, colonna fonte", V_FONTE, N_FONTE),
    ("riga 4, cella del derivato", V_CELLA, N_CELLA),
    ("nota 4b, in coda alla nota 4/11", V_CODA_NOTA, V_CODA_NOTA + NOTA_4B),
    ("§4 punto 3", V_PUNTO3, N_PUNTO3),
]

# Forme ESATTE che devono sparire. Non frammenti: la nota nuova cita «1.242» per dichiararlo
# sbagliato, e un controllo su "1.242" nudo rifiuterebbe la correzione.
DA_SPARIRE = (V_FONTE, V_CELLA, "3. **Righe 4, 5, 6**")
MARCA = "**Nota 4b — la riga 4, riletta dalla sua fonte"


class PatchError(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pct(valore: Decimal, base: Decimal, decimali: str = "0.001") -> Decimal:
    return (abs(valore) / base * 100).quantize(Decimal(decimali), rounding=ROUND_HALF_UP)


def carica(p: Path, controlla_ancora: bool = True) -> tuple:
    if not p.is_file():
        raise PatchError("documento assente: %s" % p)
    dati = p.read_bytes()
    if controlla_ancora:
        got = (sha256_bytes(dati), len(dati))
        if got != (ANCORA_SHA, ANCORA_BYTE):
            raise PatchError(
                "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
                "  O il documento non e' quello ancorato dal record 70, o la patch e' gia' "
                "applicata. CONFRONTARE prima di insistere." % (p, ANCORA_SHA, ANCORA_BYTE,
                                                                got[0], got[1]))
    return dati.decode("utf-8"), dati


def cancello_fonti(radice: Path) -> list:
    """Rilegge i due file di fonte. Se un valore non e' quello dichiarato, il numero che questa
    patch scrive nel budget sarebbe inventato: rifiuta."""
    esiti = []
    for emi in ("NGC", "SGC"):
        f = FONTI[emi]
        p = radice / f["percorso"]
        if not p.is_file():
            raise PatchError("fonte assente: %s — la riga 4 non si puo' rileggere" % p)
        dati = p.read_bytes()
        sha, byte = sha256_bytes(dati), len(dati)
        if (sha, byte) != (f["sha256"], f["byte"]):
            raise PatchError(
                "%s: lo sha della fonte e' cambiato.\n  atteso  %s  %d byte\n  trovato %s  %d "
                "byte\n  I valori vanno rimisurati prima di scriverli nel budget."
                % (p, f["sha256"], f["byte"], sha, byte))
        try:
            d = json.loads(dati.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            raise PatchError("%s non e' JSON leggibile: %r" % (p, e))
        if d.get("schema") != SCHEMA:
            raise PatchError("%s: schema %r, atteso %r" % (p, d.get("schema"), SCHEMA))
        if d.get("region") != emi:
            raise PatchError("%s: region %r, attesa %r" % (p, d.get("region"), emi))
        if d.get("n") != N_ATTESO:
            raise PatchError("%s: n = %r, atteso %d" % (p, d.get("n"), N_ATTESO))
        for campo in ("dN_medio", "dN_sem", "dN_su_N_medio"):
            if campo not in d:
                raise PatchError("%s: manca il campo %s" % (p, campo))
            if round(float(d[campo]), 10) != round(float(f[campo]), 10):
                raise PatchError("%s: %s = %r, dichiarato %r" % (p, campo, d[campo], f[campo]))
        esiti.append("fonte %s: %s, %d byte — dN_medio %.3f, dN_sem %.4f, n = %d, schema %s"
                     % (emi, sha[:16] + "...", byte, d["dN_medio"], d["dN_sem"], d["n"], SCHEMA))
    return esiti


def basi_dal_documento(testo: str) -> dict:
    """Legge <N>_mock e D dalla §0. Le basi non si assumono: si leggono dove sono dichiarate."""
    fuori = {}
    for emi in ("NGC", "SGC"):
        m = re.search(r"^\| %s \| ([\d ]+\.\d+) \| ([\d ]+) \| \*\*([\d ]+\.\d+)\*\* \|$" % emi,
                      testo, re.M)
        if not m:
            raise PatchError("la §0 non dichiara la riga delle basi per %s nella forma attesa"
                             % emi)
        n_mock = Decimal(m.group(1).replace(" ", ""))
        d_base = Decimal(m.group(3).replace(" ", ""))
        if n_mock != BASI_N[emi] or d_base != BASI_D[emi]:
            raise PatchError("le basi %s lette dal documento (<N> = %s, D = %s) non sono quelle "
                             "attese (%s, %s)" % (emi, n_mock, d_base, BASI_N[emi], BASI_D[emi]))
        fuori[emi] = (n_mock, d_base)
    return fuori


def cancello_derivato(basi: dict) -> list:
    """Ricalcola il derivato e pretende che sia quello scritto nella cella nuova."""
    esiti = []
    for emi in ("NGC", "SGC"):
        _, d_base = basi[emi]
        calcolato = pct(Decimal(repr(FONTI[emi]["dN_medio"])), d_base)
        atteso = Decimal(DERIVATO[emi])
        if calcolato != atteso:
            raise PatchError("derivato %s: ricalcolato %s, nella cella nuova %s. La cella e' "
                             "sbagliata o la base non e' quella." % (emi, calcolato, atteso))
        esiti.append("derivato %s ricalcolato dalla fonte: %s %% di D (base %s)"
                     % (emi, calcolato, d_base))
    # la cella vecchia si riproduce dal valore ARROTONDATO: e' la diagnosi della nota (i)
    arrotondato = pct(Decimal("89.15"), basi["NGC"][1])
    if arrotondato != Decimal("1.242"):
        raise PatchError("la diagnosi della nota (i) non si riproduce: da -89.15 viene %s e non "
                         "1.242. Guardare prima di scrivere." % arrotondato)
    esiti.append("la cella vecchia (1.242) si riproduce da -89.15, il valore arrotondato: "
                 "diagnosi (i) confermata")
    # (iii) le due quantita
    media_rapporti = (abs(Decimal(repr(FONTI["NGC"]["dN_su_N_medio"]))) * 100) \
        .quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    rapporto_medie = pct(Decimal(repr(FONTI["NGC"]["dN_medio"])), basi["NGC"][0], "0.0001")
    if (str(media_rapporti), str(rapporto_medie)) != (MEDIA_RAPPORTI_NGC, RAPPORTO_MEDIE_NGC):
        raise PatchError("la nota (iii) non si riproduce: media dei rapporti %s, rapporto delle "
                         "medie %s; nella nota %s e %s" % (media_rapporti, rapporto_medie,
                                                           MEDIA_RAPPORTI_NGC,
                                                           RAPPORTO_MEDIE_NGC))
    esiti.append("nota (iii) confermata: media dei rapporti %s %%, rapporto delle medie %s %% — "
                 "due quantita' diverse" % (media_rapporti, rapporto_medie))
    return esiti


def _occorrenze(testo: str, frammento: str) -> list:
    fuori, i = [], testo.find(frammento)
    while i != -1:
        fuori.append(i)
        i = testo.find(frammento, i + 1)
    return fuori


def costruisci(testo: str) -> tuple:
    fuori = testo
    esiti = []
    for nome, vecchio, nuovo in MODIFICHE:
        if fuori.count(vecchio) != 1:
            raise PatchError("%s: il testo da sostituire compare %d volte (attesa 1). Non "
                             "insistere con un'ancora piu' corta: guardare il file."
                             % (nome, fuori.count(vecchio)))
        if nuovo != vecchio and nuovo in fuori:
            raise PatchError("%s: il testo nuovo e' gia' presente" % nome)
        fuori = fuori.replace(vecchio, nuovo, 1)
        esiti.append("%s: applicata" % nome)

    for f in DA_SPARIRE:
        if f in fuori:
            raise PatchError("dopo la patch sopravvive la forma vecchia: %r" % f[:60])
    esiti.append("le tre forme vecchie: assenti")

    if MARCA not in fuori:
        raise PatchError("la nota 4b non c'e' nel testo nuovo")
    # «1.242» resta, ma SOLO dentro la nota che lo dichiara sbagliato. La proprieta' e' la
    # POSIZIONE, non il numero di volte: la nota lo cita due volte, e riscriverla ne cambierebbe
    # il conteggio senza cambiare nulla di cio' che conta. Un conteggio al posto di una posizione
    # e' lo stesso errore dei numeri di revisione dentro le ragioni.
    i_nota = fuori.index(MARCA)
    prima = [i for i in _occorrenze(fuori, "1.242") if i < i_nota]
    if prima:
        raise PatchError("«1.242» compare %d volte PRIMA della nota 4b (offset %r): non e' la "
                         "citazione, e' una cella" % (len(prima), prima[:3]))
    dopo = [i for i in _occorrenze(fuori, "1.242") if i > i_nota]
    if not dopo:
        raise PatchError("la nota non cita «1.242»: senza la citazione non dichiara che cosa "
                         "stava scritto prima")
    esiti.append("«1.242» compare %d volte, tutte dentro la nota che lo dichiara sbagliato"
                 % len(dopo))

    # le righe non toccate devono essere identiche
    vecchie, nuove = testo.split("\n"), fuori.split("\n")
    comuni = sum(1 for l in difflib.SequenceMatcher(None, vecchie, nuove).get_matching_blocks()
                 for _ in range(l.size))
    esiti.append("%d righe su %d non toccate" % (comuni, len(vecchie)))
    return fuori, esiti


def scrivi(p: Path, dati: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".patch_riga4_", suffix=".md")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dati)
        os.replace(tmp, str(p))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if p.read_bytes() != dati:
        raise PatchError("%s: byte riletti diversi da quelli scritti" % p)


def diff(vecchio: str, nuovo: str) -> str:
    return "".join(difflib.unified_diff(vecchio.splitlines(True), nuovo.splitlines(True),
                                        fromfile="prima", tofile="dopo", n=1))


# ---------------------------------------------------------------------------

def _prepara(a) -> tuple:
    p = Path(a.doc)
    testo, _ = carica(p)
    esiti = cancello_fonti(Path(a.radice))
    basi = basi_dal_documento(testo)
    esiti += ["basi lette dalla §0 del documento: NGC D = %s, SGC D = %s"
              % (basi["NGC"][1], basi["SGC"][1])]
    esiti += cancello_derivato(basi)
    nuovo, e2 = costruisci(testo)
    return p, testo, nuovo, esiti + e2


def cmd_dry_run(a) -> int:
    _, testo, nuovo, esiti = _prepara(a)
    for x in esiti:
        print("  [ok] %s" % x)
    print()
    print(diff(testo, nuovo))
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
    p = Path(a.doc)
    testo, dati = carica(p, controlla_ancora=False)
    vecchia = (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE)
    restati = [f[:40] for f in DA_SPARIRE if f in testo]
    print("%s: %s  %d byte  nota-4b=%s  ancora-vecchia=%s  residui=%s  cella=%s  fonte=%s"
          % (a.doc, sha256_bytes(dati), len(dati), "si" if MARCA in testo else "NO",
             "SI" if vecchia else "no", restati if restati else "nessuno",
             "nuova" if N_CELLA in testo else "NO", "nuova" if N_FONTE in testo else "NO"))
    ok = (MARCA in testo and not vecchia and not restati
          and N_CELLA in testo and N_FONTE in testo and N_PUNTO3 in testo
          and MARCA in testo
          and not [i for i in _occorrenze(testo, "1.242") if i < testo.index(MARCA)])
    print("ESITO:", "VERIFICATO" if ok else "NON VERIFICATO")
    return 0 if ok else 2


# ---------------------------------------------------------------------------

def _fonte_finta(emi: str, **cambi) -> bytes:
    f = FONTI[emi]
    d = {"schema": SCHEMA, "region": emi, "n": N_ATTESO, "dN_medio": f["dN_medio"],
         "dN_sem": f["dN_sem"], "dN_su_N_medio": f["dN_su_N_medio"]}
    d.update(cambi)
    return json.dumps(d, ensure_ascii=False).encode("utf-8")


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
    controlla("quattro modifiche, quattro ancore distinte",
              len(MODIFICHE) == 4 and len({v for _, v, _ in MODIFICHE}) == 4)
    controlla("LA NOTA CITA «1.242»: una cella sbagliata si puo' citare",
              "1.242" in NOTA_4B)
    controlla("la nota lo cita piu' di una volta, e il cancello guarda la POSIZIONE non il "
              "conteggio", len(_occorrenze(NOTA_4B, "1.242")) > 1)
    controlla("un'occorrenza PRIMA della nota sarebbe rifiutata",
              _occorrenze("1.242 " + MARCA + " 1.242", "1.242")[0]
              < ("1.242 " + MARCA + " 1.242").index(MARCA))
    controlla("la cella vecchia, nella sua forma esatta, non e' nel testo nuovo",
              V_CELLA not in N_CELLA + NOTA_4B)
    controlla("la nota nomina la fonte, i campi e il livello di erosione",
              all(x in NOTA_4B for x in ("d2_v2_{NGC,SGC}.json", "dN_medio", "fkp.N_H1_k0")))
    controlla("la nota dichiara la regola generale",
              "Un rapporto si calcola dalla fonte, non dalla cella" in NOTA_4B)
    controlla("la nota non porta gli sha dei due file",
              FONTI["NGC"]["sha256"] not in NOTA_4B and FONTI["SGC"]["sha256"] not in NOTA_4B)
    controlla("il punto 3 nuovo non nomina piu' la riga 4 fra quelle da tracciare",
              "Righe 4, 5, 6" not in N_PUNTO3 and "Righe 5 e 6" in N_PUNTO3)

    # --- l'aritmetica -------------------------------------------------------
    basi = {"NGC": (BASI_N["NGC"], BASI_D["NGC"]), "SGC": (BASI_N["SGC"], BASI_D["SGC"])}
    controlla("il derivato si ricalcola e coincide con le celle nuove",
              bool(cancello_derivato(basi)))
    controlla("dalla fonte NGC viene 1.241",
              pct(Decimal("89.147"), BASI_D["NGC"]) == Decimal("1.241"))
    controlla("dal valore arrotondato viene 1.242, ed e' la diagnosi",
              pct(Decimal("89.15"), BASI_D["NGC"]) == Decimal("1.242"))
    controlla("in SGC le due vie coincidono: nessuna discrepanza da correggere",
              pct(Decimal("56.494"), BASI_D["SGC"]) == pct(Decimal("56.49"), BASI_D["SGC"])
              == Decimal("1.573"))
    controlla("base sbagliata: derivato rifiutato",
              rifiuta(lambda: cancello_derivato({"NGC": (BASI_N["NGC"], Decimal("7000")),
                                                 "SGC": basi["SGC"]})))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "results" / "paper2").mkdir(parents=True)

        # --- il cancello sulle fonti ---------------------------------------
        def scrivi_fonti(**cambi):
            for emi in ("NGC", "SGC"):
                (base / FONTI[emi]["percorso"]).write_bytes(_fonte_finta(emi, **cambi))

        scrivi_fonti()
        controlla("fonte con lo sha diverso da quello dichiarato: rifiutata",
                  rifiuta(lambda: cancello_fonti(base)))
        controlla("fonte assente: rifiutata",
                  rifiuta(lambda: cancello_fonti(base / "vuoto")))

        # per provare i controlli interni, allineiamo sha e byte al file finto
        salvati = {emi: (FONTI[emi]["sha256"], FONTI[emi]["byte"]) for emi in FONTI}
        try:
            def allinea():
                for emi in ("NGC", "SGC"):
                    d = (base / FONTI[emi]["percorso"]).read_bytes()
                    FONTI[emi]["sha256"], FONTI[emi]["byte"] = sha256_bytes(d), len(d)

            scrivi_fonti()
            allinea()
            controlla("fonti finte allineate: passano", bool(cancello_fonti(base)))
            for cambio, nome in ((dict(n=1999), "n diverso"),
                                 (dict(schema="altro"), "schema diverso"),
                                 (dict(dN_medio=-89.2), "dN_medio diverso"),
                                 (dict(dN_sem=1.5), "dN_sem diverso"),
                                 (dict(dN_su_N_medio=-0.003), "dN_su_N_medio diverso")):
                scrivi_fonti(**cambio)
                allinea()
                controlla("fonte con %s: rifiutata" % nome,
                          rifiuta(lambda: cancello_fonti(base)))
            for emi in ("NGC", "SGC"):
                (base / FONTI[emi]["percorso"]).write_bytes(b"non json")
            allinea()
            controlla("fonte illeggibile: rifiutata", rifiuta(lambda: cancello_fonti(base)))
        finally:
            for emi in FONTI:
                FONTI[emi]["sha256"], FONTI[emi]["byte"] = salvati[emi]

        # --- scrittura atomica ---------------------------------------------
        p = base / "d.md"
        p.write_bytes(b"prima")
        scrivi(p, "dopo".encode("utf-8"))
        controlla("scrivi: byte riletti coincidono", p.read_bytes() == b"dopo")
        controlla("scrivi: nessun temporaneo residuo",
                  not [x for x in os.listdir(td) if x.startswith(".patch_riga4_")])

    # --- il documento vero --------------------------------------------------
    vero = Path(a.doc)
    if vero.is_file():
        dati = vero.read_bytes()
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            testo = dati.decode("utf-8")
            controlla("documento vero: ogni ancora c'e' una volta sola",
                      all(testo.count(v) == 1 for _, v, _ in MODIFICHE))
            controlla("documento vero: nessun testo nuovo e' gia' presente",
                      not any(n in testo for _, v, n in MODIFICHE if n != v))
            controlla("documento vero: le basi della §0 si leggono e coincidono",
                      bool(basi_dal_documento(testo)))
            controlla("documento vero: «1.242» compare solo nella cella, una volta",
                      len(_occorrenze(testo, "1.242")) == 1)
            nuovo, esiti = costruisci(testo)
            controlla("documento vero: la patch si costruisce", len(esiti) == 7)
            controlla("documento vero: dopo la patch «1.242» sta solo DOPO la nota",
                      len(_occorrenze(nuovo, "1.242")) >= 1
                      and min(_occorrenze(nuovo, "1.242")) > nuovo.index(MARCA))
            controlla("documento vero: seconda costruzione rifiutata",
                      rifiuta(lambda: costruisci(nuovo)))
        else:
            print("  [--] documento vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] documento vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="voce 6.2-i: la riga 4 del budget, riletta")
    ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    ap.add_argument("--doc", default=DOC)
    ap.add_argument("--radice", default=".", help="radice del repo, per i file di fonte")
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

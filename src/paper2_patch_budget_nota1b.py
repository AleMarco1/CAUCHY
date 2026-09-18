#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_budget_nota1b.py — voce 6.2, punti 1 e 2 del §4: la base a k=1, misurata; e la
riga 9 rimandata dove sta il suo pezzo.

PUNTO 2, FATTO. La nota 1 chiedeva <N>_mock(k=1) «dal ramo unitario v1» e non lo aveva. Misurato:
il ramo `unit.N_H1_k1` di `results/paper2/ensemble_v2_{NGC,SGC}.jsonl` (2000 record) e
`results/paper2/desi_ladder_{NGC,SGC}.json` danno D(k=1) = 8123.568 (NGC) e 4483.586 (SGC), e la
riga 1 vale -1.210 % e -2.032 % invece di -1.369 e -2.537 letti sulla base a k=0.

Quattro riscontri, tutti misurati e nessuno assunto:
  (i)   il ramo unitario del v2 riproduce il v1 a k=0 (scarto 0.008 in NGC, 0.27 in SGC sulla
        media), quindi la base non mescola due ensemble oltre l'ultima cifra;
  (ii)  il 25.46 % citato dalla nota 1 si riproduce (25.455 %) e la sua cautela e' quantificata:
        ricostruire la base da quel numero arrotondato sbaglia di 2.2 generatori;
  (iii) la soglia «~350» si riproduce (351.0), e l'SGC che la nota 1 non dava vale 181.4: -98.3 e
        -91.1 stanno sotto entrambe, quindi E2 non cambia;
  (iv)  media(fkp.N_H1_k0) - media(unit.N_H1_k0) da' -89.147 e -56.494, cioe' esattamente i
        `dN_medio` della fonte: la riga 4 e' verificata una seconda volta, per via indipendente.

E UNA TRAPPOLA NEL REGISTRO, che e' il motivo per cui questa nota nomina i rami per intero: al
primo livello del record `N_H1_k0...k3` NON e' la linea base ma il ramo FKP — coincide con
`fkp.N_H1_k*` in tutte le cifre stampate, in entrambi gli emisferi. Chi legge `N_H1_k1` credendolo
il riferimento ottiene D(k=1) = 8026.209 e la riga 1 diventa -1.225 % invece di -1.210 %.

PUNTO 1, RIMANDATO DOVE STA IL SUO PEZZO. La verifica della riga 9 e' appaiata alla correzione
P1-12 del §8.2 del Paper 1, e le correzioni al Paper 1 si applicano in Fase 7 per decisione del
17 settembre: farla qui lascerebbe il budget avanti e il manoscritto indietro, che e' il difetto
che il punto 1 vuole evitare. Quello che si puo' chiudere ora e' il percorso: il documento cita
`n8b_masks_128_B.jsonl` senza cartella, e i due registri stanno in `results/paper1/`, 248 record
ciascuno.

QUESTO STRUMENTO RICALCOLA TUTTO CIO' CHE SCRIVE: le due basi a k=1, le due percentuali della
riga 1, la frazione del deficit, le due soglie, lo scarto fra i rami, la trappola del primo
livello e i due dN_medio. Le misure d'ingresso sono dichiarate una volta sola, in MISURE.

CANCELLI:
  1. sha256 e dimensione uguali all'ancora (`11acc046...`, 16 434 byte);
  2. le basi a k=0 lette dalla §0 coincidono con quelle attese;
  3. ogni numero della nota 1b ricalcolato dalle misure dichiarate;
  4. ogni testo vecchio presente una volta sola; la tabella della §1 resta allineata;
  5. dopo: la riga 1 non dice piu' «vedi nota 1», i punti 1 e 2 del §4 non sono piu' aperti;
  6. scrittura atomica, byte riletti.

Uso:
  python src\paper2_patch_budget_nota1b.py selftest
  python src\paper2_patch_budget_nota1b.py dry-run
  python src\paper2_patch_budget_nota1b.py apply
  python src\paper2_patch_budget_nota1b.py verify
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import re
import sys
import tempfile
from decimal import Decimal as Dec, ROUND_HALF_UP
from pathlib import Path

DOC = "papers/paper2/paper2_budget_5_1.md"
ANCORA_SHA = "11acc0462a1ca36c1d1dfbef47f42acb88ee8c5214b8dcacbc68bbf291514eec"
ANCORA_BYTE = 16434

# le misure d'ingresso, dichiarate una volta sola. Tutto il resto e' ricalcolato.
MISURE = {
    "NGC": {"unit_k0": "35436.678", "unit_k1": "31913.568", "fkp_k0": "35347.531",
            "fkp_k1": "31816.209", "desi_k1": "23790", "ap": "98.3",
            "dN_medio": "-89.147"},
    "SGC": {"unit_k0": "18713.236", "unit_k1": "16494.586", "fkp_k0": "18656.742",
            "fkp_k1": "16433.307", "desi_k1": "12011", "ap": "91.1",
            "dN_medio": "-56.494"},
}
BASI_K0 = {"NGC": {"N_mock": Dec("35436.686"), "N_DESI": Dec("28256"), "D": Dec("7180.686")},
           "SGC": {"N_mock": Dec("18712.9675"), "N_DESI": Dec("15122"), "D": Dec("3590.9675")}}

# cio' che la nota 1b afferma, e che il cancello 3 deve riprodurre
ATTESI = {
    "D_k1": {"NGC": "8123.568", "SGC": "4483.586"},
    "pct_k1": {"NGC": "1.210", "SGC": "2.032"},
    "pct_k0": {"NGC": "1.369", "SGC": "2.537"},
    "frazione_k1": {"NGC": "25.455", "SGC": "27.182"},
    "soglia_k1": {"NGC": "351.0", "SGC": "181.4"},
    "scarto_rami": {"NGC": "-0.008", "SGC": "0.2685"},
    "trappola_pct": {"NGC": "1.225", "SGC": "2.060"},
}
RICOSTRUITO = "8125.7"      # base ricostruita dal 25.46 % arrotondato
RICOSTRUITO_SCARTO = "2.2"

V_RIGA1_CODA = "**misura**, esito E2 | — | vedi nota 1 |"
N_RIGA1_CODA = "**misura**, esito E2 | — | **−1.210** / **−2.032** *derivato* (nota 1b) |"

V_NOTAC_1 = "| 1 | rimandata alla nota 1: la base va letta a *k*=1 | 1 | — |"
N_NOTAC_1 = ("| 1 | **misura Δ*D*/*D* su base *k*=1** = −1.210 / −2.032 % (nota 1b) | 1 | — |")

V_CODA_NOTA1 = ("~350 in NGC. **L'esito E2 non cambia**, perché −98.3 sta sotto entrambe; ma la "
                "base va dichiarata.\n")

NOTA_1B = """
**Nota 1b — la base a *k*=1, misurata (voce 6.2, punto 2 del §4; 17 settembre 2026).** La nota 1
chiedeva questa base e non l'aveva. Fonti: il ramo **`unit.N_H1_k1`** di
`results/paper2/ensemble_v2_{NGC,SGC}.jsonl`, 2000 record, e
`results/paper2/desi_ladder_{NGC,SGC}.json`, che porta *N*_DESI ai quattro livelli — il 23 790
della nota 1 viene da lì, e l'SGC, che la nota 1 non dava, vale 12 011.

| | ⟨*N*⟩_mock(*k*=1) | *N*_DESI(*k*=1) | *D*(*k*=1) | riga 1, Δ*D*/*D* | (sulla base *k*=0) |
|---|---:|---:|---:|---:|---:|
| NGC | 31 913.568 | 23 790 | **8 123.568** | **−1.210 %** | −1.369 % |
| SGC | 16 494.586 | 12 011 | **4 483.586** | **−2.032 %** | −2.537 % |

Quattro riscontri, misurati e non assunti. **(i)** Il ramo unitario del v2 riproduce il v1 a
*k*=0, che è la condizione perché la base non mescoli due ensemble: 35 436.678 contro il
35 436.686 della §0 in NGC (scarto −0.008 sulla media), 18 713.236 contro 18 712.9675 in SGC
(+0.27). L'SGC scarta circa **trentaquattro volte** più del NGC — vale la pena sapere perché, ma
su qualunque percentuale di questo documento lo scarto pesa meno dell'ultima cifra. **(ii)** Il
25.46 % citato dalla nota 1 si riproduce: *D*(*k*=1)/⟨*N*⟩(*k*=1) = 25.455 %, e la cautela della
nota 1 è quantificata — ricostruire la base da quel numero arrotondato darebbe 8 125.7, cioè
**2.2 generatori** di troppo. **(iii)** La soglia «~350» si riproduce a 351.0, e l'SGC vale 181.4:
−98.3 e −91.1 stanno sotto entrambe, quindi **E2 non cambia**, come la nota 1 anticipava.
**(iv)** media(`fkp.N_H1_k0`) − media(`unit.N_H1_k0`) dà **−89.147** in NGC e **−56.494** in SGC,
cioè esattamente i `dN_medio` della fonte della riga 4: quella riga è verificata una seconda
volta, per una via indipendente.

**Una trappola nel registro, ed è il motivo per cui questa nota nomina i rami per intero.** Al
primo livello del record `N_H1_k0…k3` **non è la linea base ma il ramo FKP**: coincide con
`fkp.N_H1_k*` in tutte le cifre stampate, in entrambi gli emisferi. Chi legge `N_H1_k1`
credendolo il riferimento ottiene *D*(*k*=1) = 8 026.209 e la riga 1 diventa −1.225 % invece di
−1.210 % (−2.060 % invece di −2.032 % in SGC). Il riferimento è **`unit.`**, e va scritto per
intero ogni volta.
"""

V_PUNTO1 = ("1. **Riga 9 — chiusa, ma da verificare con P1-12**: il ±11.9 % e il −14.3 % vanno "
            "riletti dal\n   ricalcolo, e il §8.2 del Paper 1 va corretto insieme (P1-12), "
            "altrimenti il budget e il\n   manoscritto porterebbero due numeri diversi per lo "
            "stesso termine.\n")
N_PUNTO1 = ("1. **Riga 9 — la verifica si fa in Fase 7, con P1-12**: il ±11.9 % e il −14.3 % "
            "vanno riletti\n   dal ricalcolo insieme al §8.2 del Paper 1, e le correzioni al "
            "Paper 1 si applicano come\n   ultimo punto della Fase 7 (decisione del 17 "
            "settembre). Rileggere qui e correggere là\n   lascerebbe il budget avanti e il "
            "manoscritto indietro, che è il difetto che questo punto\n   vuole evitare. Chiuso "
            "invece il percorso: i due registri stanno in `results/paper1/`,\n   248 record "
            "ciascuno, e il documento cita `n8b_masks_128_B.jsonl` senza cartella.\n")

V_PUNTO2 = ("2. **Nota 1**: leggere ⟨*N*⟩_mock(*k*=1) dal ramo unitario v1 e ricalcolare le % di "
            "(1) su quella base.\n")
N_PUNTO2 = ("2. **Nota 1 — fatto il 17 settembre**: base a *k*=1 misurata sul ramo `unit.` e su "
            "`desi_ladder`,\n   riga 1 ricalcolata su quella base (nota 1b).\n")

MODIFICHE = [
    ("riga 1, cella della misura", V_RIGA1_CODA, N_RIGA1_CODA),
    ("nota C, riga 1", V_NOTAC_1, N_NOTAC_1),
    ("nota 1b, in coda alla nota 1", V_CODA_NOTA1, V_CODA_NOTA1 + NOTA_1B),
    ("§4 punto 1, rimandato alla Fase 7", V_PUNTO1, N_PUNTO1),
    ("§4 punto 2, fatto", V_PUNTO2, N_PUNTO2),
]
DA_SPARIRE = ("| vedi nota 1 |", "rimandata alla nota 1", "chiusa, ma da verificare con P1-12",
              "leggere ⟨*N*⟩_mock(*k*=1) dal ramo unitario v1")
MARCA = "**Nota 1b — la base a *k*=1, misurata"
INTESTAZIONE = ("| # | termine | valore | fonte | denominatore | forma | limite, % di *D* | "
                "misura Δ*D*/*D*, col segno |")


class PatchError(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def q(x: Dec, d: str = "0.001") -> Dec:
    return x.quantize(Dec(d), rounding=ROUND_HALF_UP)


def carica(p: Path, controlla_ancora: bool = True) -> tuple:
    if not p.is_file():
        raise PatchError("documento assente: %s" % p)
    dati = p.read_bytes()
    if controlla_ancora:
        got = (sha256_bytes(dati), len(dati))
        if got != (ANCORA_SHA, ANCORA_BYTE):
            raise PatchError(
                "%s: ancora NON corrisponde.\n  atteso  %s  %d byte\n  trovato %s  %d byte\n"
                "  O il documento non e' quello uscito dalla patch del segno, o questa patch e' "
                "gia' applicata." % (p, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
    return dati.decode("utf-8"), dati


def basi_dal_documento(testo: str) -> dict:
    fuori = {}
    for emi in ("NGC", "SGC"):
        m = re.search(r"^\| %s \| ([\d ]+\.\d+) \| ([\d ]+) \| \*\*([\d ]+\.\d+)\*\* \|$" % emi,
                      testo, re.M)
        if not m:
            raise PatchError("la §0 non dichiara le basi per %s nella forma attesa" % emi)
        letto = {"N_mock": Dec(m.group(1).replace(" ", "")),
                 "N_DESI": Dec(m.group(2).replace(" ", "")),
                 "D": Dec(m.group(3).replace(" ", ""))}
        if letto != BASI_K0[emi]:
            raise PatchError("basi %s lette %r, attese %r" % (emi, letto, BASI_K0[emi]))
        fuori[emi] = letto
    return fuori


def cancello_numeri(basi0: dict) -> list:
    """Ricalcola ogni numero della nota 1b dalle misure dichiarate in MISURE."""
    esiti = []
    for emi in ("NGC", "SGC"):
        m = {k: Dec(v) for k, v in MISURE[emi].items()}
        prove = {
            "D_k1": q(m["unit_k1"] - m["desi_k1"]),
            "pct_k1": q(m["ap"] / (m["unit_k1"] - m["desi_k1"]) * 100),
            "pct_k0": q(m["ap"] / basi0[emi]["D"] * 100),
            "frazione_k1": q((m["unit_k1"] - m["desi_k1"]) / m["unit_k1"] * 100),
            "soglia_k1": q(m["unit_k1"] * Dec("0.011"), "0.1"),
            "scarto_rami": q(m["unit_k0"] - basi0[emi]["N_mock"], "0.0001").normalize(),
            "trappola_pct": q(m["ap"] / (m["fkp_k1"] - m["desi_k1"]) * 100),
        }
        for nome, calcolato in prove.items():
            atteso = Dec(ATTESI[nome][emi])
            if calcolato != atteso:
                raise PatchError("%s %s: ricalcolato %s, nella nota %s"
                                 % (nome, emi, calcolato, atteso))
        # il riscontro (iv): la differenza delle medie riproduce dN_medio della fonte
        diff = q(m["fkp_k0"] - m["unit_k0"])
        if diff != Dec(MISURE[emi]["dN_medio"]):
            raise PatchError("%s: media(fkp) - media(unit) = %s, ma dN_medio della fonte e' %s. "
                             "Il riscontro (iv) della nota 1b e' falso: fermarsi."
                             % (emi, diff, MISURE[emi]["dN_medio"]))
        esiti.append("%s: D(k=1) = %s, riga 1 = %s %%, e media(fkp)−media(unit) = %s riproduce "
                     "dN_medio" % (emi, prove["D_k1"], prove["pct_k1"], diff))
    rico = Dec("23790") / (1 - Dec("0.2546")) - Dec("23790")
    if q(rico, "0.1") != Dec(RICOSTRUITO) or \
            q(rico - Dec(ATTESI["D_k1"]["NGC"]), "0.1") != Dec(RICOSTRUITO_SCARTO):
        raise PatchError("il riscontro (ii) non si riproduce: dal 25.46 %% arrotondato viene %s, "
                         "scarto %s" % (q(rico, "0.1"), q(rico - Dec(ATTESI["D_k1"]["NGC"]),
                                                          "0.1")))
    esiti.append("riscontro (ii): dal 25.46 %% arrotondato verrebbe %s, cioe' %s generatori di "
                 "troppo" % (RICOSTRUITO, RICOSTRUITO_SCARTO))
    return esiti


def cancello_allineamento(testo: str) -> str:
    righe = testo.split("\n")
    try:
        i = righe.index(INTESTAZIONE)
    except ValueError:
        raise PatchError("l'intestazione della tabella della §1 non c'e' piu'")
    attese = len(INTESTAZIONE.split("|"))
    guardate = 0
    for l in righe[i:]:
        if not l.startswith("|"):
            break
        if len(l.split("|")) != attese:
            raise PatchError("la tabella della §1 non e' piu' allineata: %r ha %d celle invece "
                             "di %d" % (l[:60], len(l.split("|")), attese))
        guardate += 1
    if guardate != 12:
        raise PatchError("nella tabella della §1 ho contato %d righe, attese 12" % guardate)
    return "tabella della §1 ancora allineata: 12 righe, %d celle" % attese


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
    if MARCA not in fuori:
        raise PatchError("la nota 1b non c'e' nel testo nuovo")
    esiti.append(cancello_allineamento(fuori))
    vecchie, nuove = testo.split("\n"), fuori.split("\n")
    comuni = sum(l.size for l in
                 difflib.SequenceMatcher(None, vecchie, nuove).get_matching_blocks())
    esiti.append("%d righe su %d non toccate" % (comuni, len(vecchie)))
    return fuori, esiti


def scrivi(p: Path, dati: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".patch_nota1b_", suffix=".md")
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
    esiti = cancello_numeri(basi_dal_documento(testo))
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
        allineata = cancello_allineamento(testo) and "si"
    except PatchError:
        pass
    ok = (MARCA in testo and N_RIGA1_CODA in testo and N_PUNTO1 in testo and N_PUNTO2 in testo
          and allineata == "si" and not vecchia and not restati)
    print("%s: %s  %d byte  nota-1b=%s  riga-1=%s  punti-1-2=%s  tabella=%s  ancora-vecchia=%s  "
          "residui=%s"
          % (a.doc, sha256_bytes(dati), len(dati), "si" if MARCA in testo else "NO",
             "misurata" if N_RIGA1_CODA in testo else "NO",
             "chiusi" if (N_PUNTO1 in testo and N_PUNTO2 in testo) else "NO",
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

    controlla("cinque modifiche, cinque ancore distinte",
              len(MODIFICHE) == 5 and len({v for _, v, _ in MODIFICHE}) == 5)
    controlla("tutti i numeri della nota 1b si ricalcolano dalle misure",
              bool(cancello_numeri(BASI_K0)))
    controlla("la nota 1b nomina il ramo per intero, non il primo livello",
              "`unit.N_H1_k1`" in NOTA_1B and "non è la linea base ma il ramo FKP" in NOTA_1B)
    controlla("la nota 1b porta l'SGC, che la nota 1 non dava",
              "12 011" in NOTA_1B and "181.4" in NOTA_1B)
    controlla("la nota 1b dichiara il riscontro (iv) sulla riga 4",
              "−89.147" in NOTA_1B and "−56.494" in NOTA_1B)
    controlla("il punto 1 rimanda alla Fase 7 e non finge di chiudere",
              "Fase 7" in N_PUNTO1 and "P1-12" in N_PUNTO1)
    controlla("il punto 1 chiude almeno il percorso dei due registri",
              "results/paper1/" in N_PUNTO1 and "248 record" in N_PUNTO1)
    controlla("il punto 2 e' chiuso e cita la nota 1b",
              "fatto il 17 settembre" in N_PUNTO2 and "nota 1b" in N_PUNTO2)
    controlla("la riga 1 non dira' piu' «vedi nota 1»",
              "vedi nota 1" not in N_RIGA1_CODA and "−1.210" in N_RIGA1_CODA)

    # una misura falsata deve far crollare i riscontri, non passare inosservata
    salvato = MISURE["NGC"]["unit_k1"]
    try:
        MISURE["NGC"]["unit_k1"] = "31900.000"
        controlla("misura d'ingresso falsata: numeri rifiutati",
                  rifiuta(lambda: cancello_numeri(BASI_K0)))
    finally:
        MISURE["NGC"]["unit_k1"] = salvato
    salvato2 = MISURE["SGC"]["fkp_k0"]
    try:
        MISURE["SGC"]["fkp_k0"] = "18650.000"
        controlla("riscontro (iv) falsato: rifiutato, perche' dN_medio non torna",
                  rifiuta(lambda: cancello_numeri(BASI_K0)))
    finally:
        MISURE["SGC"]["fkp_k0"] = salvato2
    controlla("basi a k=0 falsate: rifiutate",
              rifiuta(lambda: cancello_numeri(
                  {"NGC": {"N_mock": Dec("35000"), "N_DESI": Dec("28256"), "D": Dec("7000")},
                   "SGC": BASI_K0["SGC"]})))

    finto = (INTESTAZIONE + "\n|---|\n"
             + "\n".join("| %d | a | b | c | d | e | f | g |" % i for i in range(10)) + "\n\n")
    controlla("allineamento: una riga corta e' rifiutata",
              rifiuta(lambda: cancello_allineamento(
                  finto.replace("| 3 | a | b | c | d | e | f | g |", "| 3 | a |"))))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        p = base / "d.md"
        p.write_bytes(b"prima")
        scrivi(p, b"dopo")
        controlla("scrivi: byte riletti coincidono", p.read_bytes() == b"dopo")
        controlla("scrivi: nessun temporaneo residuo",
                  not [x for x in os.listdir(td) if x.startswith(".patch_nota1b_")])
        p.write_bytes(b"x")
        controlla("ancora sbagliata: rifiutata", rifiuta(lambda: carica(p)))

    vero = Path(a.doc)
    if vero.is_file():
        dati = vero.read_bytes()
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            testo = dati.decode("utf-8")
            controlla("documento vero: ogni ancora c'e' una volta sola",
                      all(testo.count(v) == 1 for _, v, _ in MODIFICHE))
            controlla("documento vero: le basi della §0 coincidono",
                      bool(basi_dal_documento(testo)))
            controlla("documento vero: la tabella parte allineata",
                      bool(cancello_allineamento(testo)))
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
    ap = argparse.ArgumentParser(description="nota 1b: la base a k=1, misurata")
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
paper2_patch_checklist_331.py — la revisione della checklist alla chiusura della sessione del
17 settembre: rev. 3.30 -> 3.31.

SEI MODIFICHE, TUTTE CONTABILITA' DELLA CHECKLIST E NESSUN RECORD DEL LEDGER (lo dice la voce 6.0
stessa):
  - intestazione: rev. 3.31, con cio' che la sessione ha cambiato;
  - voce 5.1: i due «Aperti di 5.1» sono chiusi, e la nota su `n_clip_inmask` e' rimandata dove
    sta (practice 6 di 5.4, non 5.1);
  - voce 6.0 c): 4.2d RESTA RITIRATA, e la premessa e' MISURATA invece che assunta — il δ del
    ramo unitario esiste solo come digest su byte grezzi, in 2000 record su 2000, e non e' mai
    stato scritto; il file .npy su disco e' il δ del ramo FKP;
  - voce 6.0 d): CHIUSA, entrambi i residui sistemati;
  - voce 6.2: riga di stato, DUE sotto-voci su sei, e le sotto-voci ii, iii, iv marcate.

NON chiude la 6.2 e NON chiude la 6.0: la 6.0 resta aperta su a) (Fase 7) e su b) (la provenienza
di P1-2, che non e' una spunta), e la 6.2 su v) e vi).

E DICHIARA UN DOPPIONE: la 6.2-iv chiedeva alla voce 5.1 di togliere «denominatori conservativi
ovunque» e di aggiornare la banda. La voce 5.1 lo porta gia'. Terzo doppione della sessione, dopo
la «quattordicesima voce» del Paper 1 (era P1-9) e il censimento della colonna «fonte».

CANCELLI: ancora sha256 e dimensione; ogni testo vecchio una volta sola; nessun testo nuovo gia'
presente; dopo la patch la rev. 3.30 non c'e' piu' e la 3.31 c'e'; scrittura atomica.

Uso:
  python src\paper2_patch_checklist_331.py selftest
  python src\paper2_patch_checklist_331.py dry-run
  python src\paper2_patch_checklist_331.py apply
  python src\paper2_patch_checklist_331.py verify
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import os
import sys
import tempfile
from pathlib import Path

DOC = "papers/paper2/checklist_paper2.md"
ANCORA_SHA = "683986dba6d02251535a96a56fafb421faf9ff625aadb6a50710363fe2383d2e"
ANCORA_BYTE = 255152

MODIFICHE = [('intestazione, rev. 3.31',
  '### rev. 3.30 — 17 settembre 2026 (sera) — record 74; **la decisione è presa: via (A)**, '
  'quattro eccezioni dichiarate, tre col digest di ciò che la citazione intendeva; e la copia '
  'rimossa dal commit `352e024` è **BYTE-IDENTICA** al sopravvissuto, `ae733e1e…` — quel '
  "commit ha rimosso un'**etichetta**, non un dato. Il censimento a 74 record passa **quattro "
  'verdetti su cinque**; `citati_committati` si chiude col commit quattro, non con '
  "un'eccezione. La 6.7 è chiusa di nuovo (`09eb415f…`), dopo essere stata riaperta per una "
  'riga che aveva detto la cosa sbagliata **due volte, in direzioni opposte**',
  '### rev. 3.31 — 17 settembre 2026 (notte) — record 74; **la 6.2 è a due sotto-voci su '
  'sei**, non chiusa: fatte 6.2-i (righe 4, 5 e 6 del budget) e 6.2-ii (base a *k*=1), '
  'rimandata 6.2-iii alla Fase 7 col suo P1-12, **già soddisfatta** 6.2-iv dalla voce 5.1 di '
  'questa checklist, aperte 6.2-v e 6.2-vi. La **6.0 chiude su c) e d)** e resta aperta su a) '
  'e b). Il budget è a `47503c98…`, 19 108 byte, con sei note nuove — 4b, C, 5/6, S, 6b, 1b — '
  'e **due colonne di percentuali** al posto di una, perché la R3 vieta il solo valore '
  'centrale sotto 3σ. Un derivato era sbagliato: **1.242 calcolato su −89.15, la cella, invece '
  'che su −89.147, la fonte**; e il **+309 della riga 11 vale −309 su *D***, mentre la colonna '
  'senza segno li leggeva concordi'),
 ('voce 5.1, «Aperti di 5.1» chiusi',
  "      **Aperti di 5.1:** la nota 1 (le % dell'AP vanno su ⟨*N*⟩_mock a *k*=1, letto dal "
  'ramo\n'
  '      unitario, non ricostruito dal 25.46 % arrotondato) e i file sorgente di tre valori.\n',
  '      **Aperti di 5.1: CHIUSI il 17 set (sera), voce 6.2.** La nota 1 ha la sua base\n'
  '      misurata — *D*(*k*=1) = 8 123.568 / 4 483.586, dal ramo `unit.N_H1_k1` di\n'
  '      `ensemble_v2_{NGC,SGC}.jsonl` e da `desi_ladder_{NGC,SGC}.json`, con la riga 1 a\n'
  '      **−1.210 / −2.032 %** (nota 1b del budget). Dei tre valori con fonte-manoscritto o\n'
  '      fonte-strumento: **D2 su v2 è riletto** (`d2_v2_{NGC,SGC}.json`, campi `dN_medio` e\n'
  '      `dN_sem`, nota 4b), **NFW e snapshot non hanno registro** e sono dichiarati tali su '
  'due\n'
  '      metri (nota 5/6). Resta fuori `n_clip_inmask`, che è practice 6 di 5.4 e non 5.1: il '
  'ledger\n'
  '      la nomina una volta sola, al record 60, e ciò che il registro archivia è '
  '`d5c_n_clipped`\n'
  "      (2000 record su 2000), che è un'altra quantità.\n"),
 ('voce 6.0 c), decisa',
  '      **c) 4.2d va RIDEFINITA prima di poter essere eseguita, se si esegue.** La quantità\n'
  '      dichiarata non esiste: le righe 3–4 della Tab. 12 contano **pareggi di valore in ν '
  'dopo la\n'
  '      lisciatura**, non galassie per cella (voci P1-6 e P1-7). Tre tentativi di sostituirla '
  'sono\n'
  '      caduti, e il terzo era **corretto come argomento e vacuo come regola**. La forma '
  'corretta\n'
  '      esisterebbe — confrontare, sulla stessa realizzazione, i pareggi fra voxel a valore '
  'fisso\n'
  '      del ramo unitario e di quello FKP — ma il δ del ramo unitario non è in cache e '
  'servirebbe\n'
  '      rifare il carving. **Il criterio per decidere è già scritto** (record 50): tre '
  'formulazioni\n'
  "      cadute di fila dicono che l'oggetto non è capito abbastanza da farne un cancello. "
  'Quindi\n'
  '      **o si ridefinisce con una quantità che esiste, o resta ritirata** — non un quarto\n'
  '      tentativo sulla stessa strada.',
  '      **c) 4.2d va RIDEFINITA prima di poter essere eseguita, se si esegue.** La quantità\n'
  '      dichiarata non esiste: le righe 3–4 della Tab. 12 contano **pareggi di valore in ν '
  'dopo la\n'
  '      lisciatura**, non galassie per cella (voci P1-6 e P1-7). Tre tentativi di sostituirla '
  'sono\n'
  '      caduti, e il terzo era **corretto come argomento e vacuo come regola**. La forma '
  'corretta\n'
  '      esisterebbe — confrontare, sulla stessa realizzazione, i pareggi fra voxel a valore '
  'fisso\n'
  '      del ramo unitario e di quello FKP — ma il δ del ramo unitario non è in cache e '
  'servirebbe\n'
  '      rifare il carving. **Il criterio per decidere è già scritto** (record 50): tre '
  'formulazioni\n'
  "      cadute di fila dicono che l'oggetto non è capito abbastanza da farne un cancello. "
  'Quindi\n'
  '      **o si ridefinisce con una quantità che esiste, o resta ritirata** — non un quarto\n'
  '      tentativo sulla stessa strada.\n'
  '\n'
  '      **DECISO il 17 set (sera): RESTA RITIRATA, e la premessa è misurata.** La premessa '
  '«il δ\n'
  '      del ramo unitario non è in cache» è stata misurata invece che assunta: nel record v2\n'
  '      `delta_file` punta a `data/processed/paper2_mock_deltas_v2/<REG>/delta_NNNN.npy`, '
  'che\n'
  '      esiste su disco, ma è il δ del **primo livello**, cioè il ramo **FKP** — al primo '
  'livello\n'
  '      `N_H1_k*` non è la linea base (nota 1b del budget). Il δ unitario esiste solo come '
  'digest\n'
  '      su **byte grezzi** in `unit_1punto.delta_sha256`, in 2000 record su 2000, e non è '
  'mai\n'
  '      stato scritto. Rifare il carving resta quindi necessario, ed è **verificabile**: '
  'quel\n'
  '      digest dice se il δ rigenerato è lo stesso. La decisione del record 50 vale: '
  'ritirata, non\n'
  '      un quarto tentativo.'),
 ('voce 6.0 d), chiusa',
  '      **d) I due residui di 5.1, che valgono solo se chiusi qui.** Il budget è dichiarato, '
  'ma\n'
  '      due numeri non sono ancora sulla loro base:\n'
  '      - **la nota 1**: le percentuali del termine AP vanno calcolate su ⟨*N*⟩_mock a '
  '***k*=1**,\n'
  '        letto dal ramo unitario, **non** ricostruito dal 25.46 % arrotondato. Con le basi a '
  '*k*=0\n'
  '        si otterrebbero 1.369 / 2.537 %, **che non vanno usati**. Stessa osservazione per '
  'le\n'
  '        soglie di rilevanza 390 e 206, che sono 1.1 pp × ⟨*N*⟩ a *k*=0: a *k*=1 la soglia '
  'NGC\n'
  "        sarebbe ~350. **L'esito E2 non cambia** — −98.3 sta sotto entrambe — ma la base va\n"
  '        dichiarata;\n'
  '      - **i file sorgente di tre valori** che oggi hanno come fonte solo un manoscritto o '
  'solo lo\n'
  '        strumento: NFW (Paper 1 §7.1), snapshot (M26 §7 vi) e D2 su v2. Il punto 6.2 di '
  'questa\n'
  '        fase chiede esattamente questo, e questi tre sono i suoi primi casi.\n'
  '      *(Fuori da 5.1 ma della stessa famiglia: `n_clip_inmask`, che la sonda D5c calcola e '
  'il\n'
  '      registro non archivia — vedi practice 6 di 5.4.)*',
  '      **d) I due residui di 5.1, che valgono solo se chiusi qui.** Il budget è dichiarato, '
  'ma\n'
  '      due numeri non sono ancora sulla loro base:\n'
  '      - **la nota 1**: le percentuali del termine AP vanno calcolate su ⟨*N*⟩_mock a '
  '***k*=1**,\n'
  '        letto dal ramo unitario, **non** ricostruito dal 25.46 % arrotondato. Con le basi a '
  '*k*=0\n'
  '        si otterrebbero 1.369 / 2.537 %, **che non vanno usati**. Stessa osservazione per '
  'le\n'
  '        soglie di rilevanza 390 e 206, che sono 1.1 pp × ⟨*N*⟩ a *k*=0: a *k*=1 la soglia '
  'NGC\n'
  "        sarebbe ~350. **L'esito E2 non cambia** — −98.3 sta sotto entrambe — ma la base va\n"
  '        dichiarata;\n'
  '      - **i file sorgente di tre valori** che oggi hanno come fonte solo un manoscritto o '
  'solo lo\n'
  '        strumento: NFW (Paper 1 §7.1), snapshot (M26 §7 vi) e D2 su v2. Il punto 6.2 di '
  'questa\n'
  '        fase chiede esattamente questo, e questi tre sono i suoi primi casi.\n'
  '      *(Fuori da 5.1 ma della stessa famiglia: `n_clip_inmask`, che la sonda D5c calcola e '
  'il\n'
  '      registro non archivia — vedi practice 6 di 5.4.)*\n'
  '\n'
  '      **CHIUSA il 17 set (sera), voce 6.2.** Entrambi i residui sono sistemati: la nota 1 '
  'ha la\n'
  '      base misurata (nota 1b del budget, riga 1 a −1.210 / −2.032 %), e dei tre valori D2 '
  'su v2\n'
  '      è riletto dalla sua fonte (nota 4b) mentre NFW e snapshot sono dichiarati **senza\n'
  '      registro** su due metri (nota 5/6) — il manoscritto li descrive, §7.1 del Paper 1 '
  'non\n'
  '      nomina alcun file. La nota su `n_clip_inmask` resta esatta e resta dove sta: è '
  'practice 6\n'
  '      di 5.4.'),
 ('voce 6.2, riga di stato',
  '- [ ] **6.2** Ogni numero del manoscritto tracciabile a un singolo run verificato.\n',
  '- [ ] **6.2** Ogni numero del manoscritto tracciabile a un singolo run verificato.\n'
  '      **✦✦ Stato al 17 set (sera): DUE sotto-voci su sei.** Fatte **i** e **ii**;\n'
  '      **iii** rimandata alla Fase 7 col suo P1-12, perché rileggere qui e correggere\n'
  '      là lascerebbe budget e manoscritto disallineati; **iv** era già soddisfatta\n'
  '      dalla voce 5.1 di questa checklist — il ritiro e la banda 17.3–31.2 % ci sono\n'
  '      dalla rev. 3.2x, e il §4 del budget la chiedeva ancora; aperte **v** e **vi**.\n'),
 ('voce 6.2, sotto-voci ii, iii, iv',
  '      - **6.2-ii** nota 1: ⟨*N*⟩_mock a *k*=1 dal ramo unitario, e le % della riga 1\n'
  '        ricalcolate su quella base (con le basi a *k*=0 verrebbero 1.369 / 2.537 %, **da '
  'non\n'
  '        usare**);\n'
  '      - **6.2-iii** riga 9 riletta dal ricalcolo P1-12, col §8.2 del Paper 1 corretto '
  'insieme;\n'
  '      - **6.2-iv** voce 5.1: togliere «denominatori conservativi ovunque», banda da 17–29 '
  'a\n'
  '        17.3–31.2 %;',
  '      - **6.2-ii — FATTA** il 17 set: ⟨*N*⟩_mock a *k*=1 dal ramo unitario, e le % della '
  'riga 1\n'
  '        ricalcolate su quella base (con le basi a *k*=0 verrebbero 1.369 / 2.537 %, **da '
  'non\n'
  '        usare**);\n'
  '      - **6.2-iii — RIMANDATA alla Fase 7**: riga 9 riletta dal ricalcolo P1-12, col §8.2 '
  'del Paper 1 corretto insieme;\n'
  '      - **6.2-iv — GIÀ SODDISFATTA dalla voce 5.1**: togliere «denominatori conservativi '
  'ovunque», banda da 17–29 a\n'
  '        17.3–31.2 %;')]

DA_SPARIRE = ("### rev. 3.30", "**Aperti di 5.1:** la nota 1")
MARCA = "### rev. 3.31"


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
                "  La checklist e' alla rev. 3.30 del 17 set (sera), 255 152 byte: se e' cambiata,"
                " questa revisione va rifatta su cio' che c'e'."
                % (p, ANCORA_SHA, ANCORA_BYTE, got[0], got[1]))
    return dati.decode("utf-8"), dati


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
        raise PatchError("la rev. 3.31 non c'e' nel testo nuovo")
    if "RESTA RITIRATA" not in fuori or "CHIUSA il 17 set (sera), voce 6.2" not in fuori:
        raise PatchError("le chiusure di 6.0 c) e d) non ci sono")
    if "DUE sotto-voci su sei" not in fuori:
        raise PatchError("la 6.2 non porta la sua riga di stato: chiuderla per intero sarebbe "
                         "falso")
    esiti.append("rev. 3.31 presente, 6.0 c) e d) chiuse, 6.2 dichiarata a due su sei")
    vecchie, nuove = testo.split("\n"), fuori.split("\n")
    comuni = sum(l.size for l in
                 difflib.SequenceMatcher(None, vecchie, nuove).get_matching_blocks())
    esiti.append("%d righe su %d non toccate" % (comuni, len(vecchie)))
    return fuori, esiti


def scrivi(p: Path, dati: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".patch_cl331_", suffix=".md")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dati)
        os.replace(tmp, str(p))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if p.read_bytes() != dati:
        raise PatchError("%s: byte riletti diversi da quelli scritti" % p)


def cmd_dry_run(a) -> int:
    testo, _ = carica(Path(a.doc))
    nuovo, esiti = costruisci(testo)
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
    p = Path(a.doc)
    testo, _ = carica(p)
    nuovo, esiti = costruisci(testo)
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
    restati = [f[:30] for f in DA_SPARIRE if f in testo]
    ok = (MARCA in testo and not vecchia and not restati
          and "DUE sotto-voci su sei" in testo and "RESTA RITIRATA" in testo)
    print("%s: %s  %d byte  rev-3.31=%s  6.0c=%s  6.0d=%s  6.2=%s  ancora-vecchia=%s  "
          "residui=%s"
          % (a.doc, sha256_bytes(dati), len(dati), "si" if MARCA in testo else "NO",
             "decisa" if "RESTA RITIRATA" in testo else "NO",
             "chiusa" if "CHIUSA il 17 set (sera), voce 6.2" in testo else "NO",
             "due su sei" if "DUE sotto-voci su sei" in testo else "NO",
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

    controlla("sei modifiche, sei ancore distinte",
              len(MODIFICHE) == 6 and len({v for _, v, _ in MODIFICHE}) == 6)
    controlla("nessuna modifica e' un no-op",
              all(v != n for _, v, n in MODIFICHE))
    controlla("le due voci 6.0 conservano il testo originale e ci aggiungono la chiusura",
              all(MODIFICHE[i][2].startswith(MODIFICHE[i][1]) for i in (2, 3)))
    controlla("la 6.2 NON viene spuntata",
              all("- [x] **6.2**" not in n for _, _, n in MODIFICHE))
    controlla("la 6.0 non viene spuntata: a) e b) restano aperte",
              all("- [x] **✦✦ 6.0" not in n for _, _, n in MODIFICHE))
    controlla("l'intestazione dichiara due su sei e non «chiusa»",
              "DUE sotto-voci" in MODIFICHE[4][2] and "non chiusa" in MODIFICHE[0][2])
    controlla("la 6.0 c) porta la premessa misurata, non assunta",
              "byte grezzi" in MODIFICHE[2][2] and "2000 record su 2000" in MODIFICHE[2][2])
    controlla("la voce 5.1 rimanda n_clip_inmask alla practice 6",
              "practice 6 di 5.4" in MODIFICHE[1][2])
    controlla("il doppione 6.2-iv e' dichiarato",
              "GIÀ SODDISFATTA" in MODIFICHE[5][2])

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        p = base / "d.md"
        p.write_bytes(b"prima")
        scrivi(p, b"dopo")
        controlla("scrivi: byte riletti coincidono", p.read_bytes() == b"dopo")
        controlla("scrivi: nessun temporaneo residuo",
                  not [x for x in os.listdir(td) if x.startswith(".patch_cl331_")])
        p.write_bytes(b"x")
        controlla("ancora sbagliata: rifiutata", rifiuta(lambda: carica(p)))

    vero = Path(a.doc)
    if vero.is_file():
        dati = vero.read_bytes()
        if (sha256_bytes(dati), len(dati)) == (ANCORA_SHA, ANCORA_BYTE):
            testo = dati.decode("utf-8")
            controlla("documento vero: ogni ancora c'e' una volta sola",
                      all(testo.count(v) == 1 for _, v, _ in MODIFICHE))
            nuovo, esiti = costruisci(testo)
            controlla("documento vero: la patch si costruisce", len(esiti) == 8)
            controlla("documento vero: seconda costruzione rifiutata",
                      rifiuta(lambda: costruisci(nuovo)))
        else:
            print("  [--] documento vero non all'ancora attesa: controlli saltati")
    else:
        print("  [--] documento vero non trovato: controlli saltati")

    print("selftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="checklist rev. 3.31")
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

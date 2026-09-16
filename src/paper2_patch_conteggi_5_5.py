#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_patch_conteggi_5_5.py — i conteggi delle smentite, e le Q di D6 dove vanno.

Rimette i conteggi delle smentite dove il record 64 li ha rimessi — 12 / 1 / 5, invariati —
e porta le quattro Q di D6 in una sezione propria, dichiarata fuori dall'universo del
ledger. Apre la voce 6.9: il censimento dei verdetti emessi fuori dal registro.

Cinque modifiche su TRE file:

  checklist_paper2.md
    C1  6.8: i conteggi tornano 12/1/5, e le Q vanno in una sezione propria
    C2  voce 6.9 nuova: il censimento dei nove script che emettono verdetti

  paper2_stato.md
    S1  ottava revisione: i conteggi e la portata di 5.5
    S2  riassunto "Al 13 settembre": 12/1/5 piu' le Q fuori dal ledger

  paper2_5_5_smentite.md
    M1  sezione 3-bis: le quattro Q con i loro margini, e perche' non entrano in A ne' in B

Forma, invariata: ancore uniche o rifiuto; rifiuto se gia' applicata anche solo in parte;
BOM e fine riga preservati (le ancore si adattano alla fine riga del file, LF o CRLF);
**si valida TUTTO prima di scrivere QUALUNQUE cosa**, cosi' un file rotto non lascia
l'altro a meta'; l'inversa deve restituire gli originali byte per byte prima di scrivere;
scrittura atomica con backup; `verify` sui file riletti dal disco.

Uso:
    python src\\paper2_patch_chiusura_6_8.py selftest
    python src\\paper2_patch_chiusura_6_8.py ancore --checklist papers\\paper2\\checklist_paper2.md --stato papers\\paper2\\paper2_stato.md
    python src\\paper2_patch_chiusura_6_8.py apply --checklist papers\\paper2\\checklist_paper2.md --stato papers\\paper2\\paper2_stato.md --dry-run
    python src\\paper2_patch_chiusura_6_8.py apply --checklist papers\\paper2\\checklist_paper2.md --stato papers\\paper2\\paper2_stato.md
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

VERSIONE = "1.0"
CRLF = b"\r\n"
LF = b"\n"


class Rifiuto(Exception):
    pass


# ============================================================ testi

C1_OLD = """      **Smentite ricontate: 11 in A, 1 in A-bis, 6 in B.** Q1 è ritirata come falsificazione —
      0.29σ e 0.14σ dalla sua soglia — e passa al gruppo B accanto alla P1 di D3. Q2 cade a NGC
      (4.7σ) e **non è decidibile** a SGC (2.0σ): una smentita che non si replica si scrive così.
      Q3 tiene solo con la procedura attaccata, perché col kernel e il denominatore d'insieme sta
      a 2.6σ da 0.50.
      *(Residuo di contabilità, da chiudere: `paper2_5_5_smentite.md` e la voce 5.5 dicono ancora
      dodici in A e cinque in B.)*"""

C1_NEW = """      **Smentite: i conteggi restano 12 / 1 / 5, e le Q di D6 non erano mai state classificate**
      — record 64, che corregge il 63. Q1 **non è mai stata nel gruppo A**, e non può entrare in
      B: ogni voce di A e di B porta in colonna il **record del ledger** in cui è dichiarata o
      risolta, e le Q di D6 non ne hanno uno. La classificazione di 5.5 è stata costruita con
      `paper2_estrai.py` sui **59 record del ledger**, mentre le Q vivono nello script e nei
      risultati: è un limite di **portata**, non un errore di conteggio. Le quattro stanno ora in
      una sezione propria di `paper2_5_5_smentite.md`, dichiarata fuori da quell'universo: **Q1
      ritirata come falsificazione** (0.29σ e 0.14σ dalla sua soglia), **Q2 falsificata a NGC e
      non decidibile a SGC** (4.7σ e 2.0σ) — una smentita che non si replica non si arrotonda —
      **Q3** che tiene solo per la procedura su cui era dichiarata, perché col kernel e il
      denominatore d'insieme sta a 2.6σ da 0.50, e **Q4** falsificata su ogni base.
      **Conseguenza sul record 60:** «i 33 record esclusi sono stati controllati uno per uno,
      nessuna falsificazione è stata mancata» resta vero **dentro il registro**, e da qui in
      avanti va citato con la sua portata attaccata."""

C2_OLD = """
---

## Fase 7 — Scrittura"""

C2_NEW = """
- [ ] **✦✦ 6.9 — Censimento dei verdetti emessi FUORI dal ledger** *(aperto il 13 set, record 64)*.
      La classificazione di 5.5 copre i 59 record del registro. Un `Select-String` su `src\\*.py`
      trova **nove script** che emettono «confermata / SMENTITA» e che il registro non vede:
      `paper2_compD_nonlinear.py`, `paper2_compD_partialcorr.py`, `paper2_gate53.py`,
      `paper2_phase3_preflight.py`, `paper2_ripattern_analisi.py`, `paper2_item12b_wbar.py`,
      `paper2_pareggi.py`, `paper2_runner_fase3_mock.py`, `paper1_rev_v2g_frozen.py`.
      **Che cosa chiede:** aprirli uno per uno e decidere, voce per voce, se si tratta di una
      **predizione dichiarata con soglia** o di una semplice etichetta di **cancello**. Le prime
      vanno nella sezione fuori-ledger di `paper2_5_5_smentite.md` con il loro margine; le
      seconde no.
      **Che cosa non va fatto:** dichiarare un numero prima di aver aperto i nove file. Il record
      64 nasce esattamente da un conteggio dedotto da una descrizione invece che letto dal
      documento che lo tiene.

---

## Fase 7 — Scrittura"""

S1_OLD = """> realizzazioni, 2.8–3.8 volte più largo delle ripetizioni della CV. **Smentite ricontate
> 11/1/6**: Q1 è ritirata come falsificazione, Q2 cade a NGC e non è decidibile a SGC, Q3 tiene
> solo con la procedura attaccata. Il terzo residuo di Fase 4 **si colloca**, con tre limiti"""

S1_NEW = """> realizzazioni, 2.8–3.8 volte più largo delle ripetizioni della CV. **Smentite: i conteggi
> restano 12/1/5**, e le Q di D6 non erano mai state classificate — 5.5 copre i 59 record del
> ledger e le Q vivono fuori di esso (record 64, che corregge il 63): Q1 è ritirata come
> falsificazione, Q2 cade a NGC e non è decidibile a SGC, Q3 tiene solo per la procedura su cui
> era dichiarata. Il terzo residuo di Fase 4 **si colloca**, con tre limiti"""

S2_OLD = """collocato, con tre limiti · voci per il Paper 1 **tredici** · smentite **11 in A, 1 in A-bis, 6
in B**."""

S2_NEW = """collocato, con tre limiti · voci per il Paper 1 **tredici** · smentite **12 in A, 1 in A-bis, 5
in B**, più le quattro Q di D6, fuori dall'universo del ledger e classificate a parte."""

M1_OLD = """## 4. Verifica dei 33 record esclusi"""

M1_NEW = """## 3-bis. Predizioni dichiarate FUORI dal ledger — le Q di D6

Questa classificazione è stata costruita con `paper2_estrai.py` sui **59 record del ledger**. Le
predizioni della Componente D6 sono dichiarate nel §0 della pre-registrazione — la checklist le
elenca alla riga 602, «D2, D4, D5, D6 con P1 e Q1–Q4 smentite» — ed emesse da
`src/paper2_compD_nonlinear.py`: **non hanno un record del ledger**, quindi la ricerca non poteva
vederle e nessuna di esse è mai entrata nei gruppi A, A-bis o B. È un limite di **portata** di
questo documento, registrato nel **record 64**.

Non entrano nei gruppi sopra e non ne cambiano i conteggi: ogni riga di A e di B porta in colonna
il record in cui la predizione è dichiarata o risolta, e queste non ne hanno uno.

| # | soglia dichiarata | esito di agosto | esito con l'incertezza (record 63) |
|---|---|---|---|
| Q1 | guadagno dei quadrati < 0.05 | SMENTITA | **ritirata come falsificazione**: +0.0505 e +0.0503, a **0.29σ e 0.14σ** dalla soglia nei due emisferi. Stessa ragione della P1 di D3 (B1) |
| Q2 | guadagno delle interazioni < 0.03 | SMENTITA | **falsificata a NGC** (4.7σ), **non decidibile a SGC** (2.0σ). Una smentita che non si replica non si arrotonda |
| Q3 | *R*²cv di *P*(*k*) > 0.50 | SMENTITA | tiene **per la procedura su cui era dichiarata**; con lo stesso stimatore ai due lati *K* sta a **2.6σ** da 0.50, quindi «*P*(*k*) spiega meno della metà» non è un fatto stabilito senza la procedura attaccata |
| Q4 | quota del divario chiusa > 0.50 | SMENTITA | falsificata su ogni base: dal **12.9 %** al **21.6 %** contro il 50 |

I margini sono in unità della dispersione **d'insieme** — bootstrap sulle realizzazioni, fold per
realizzazione di origine — che è 2.8–3.8 volte più larga di quella fra partizioni della CV e non
si restringe ripetendo la misura.

**Aperto:** gli altri verdetti emessi fuori dal ledger, voce **6.9** della checklist. Nove script
da aprire uno per uno prima di dichiarare qualunque numero.

## 4. Verifica dei 33 record esclusi"""

MODIFICHE = [
    ("checklist", "C1 6.8, i conteggi tornano 12/1/5", C1_OLD, C1_NEW),
    ("checklist", "C2 voce 6.9, il censimento", C2_OLD, C2_NEW),
    ("stato", "S1 ottava revisione, i conteggi", S1_OLD, S1_NEW),
    ("stato", "S2 riassunto, i conteggi", S2_OLD, S2_NEW),
    ("smentite", "M1 sezione 3-bis, le Q fuori dal ledger", M1_OLD, M1_NEW),
]


# ============================================================ meccanica

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    return sha256_bytes(Path(p).read_bytes())


def adatta(testo: str, eol: bytes) -> bytes:
    """Il testo dell'ancora con la fine riga del file."""
    b = testo.encode("utf-8")
    return b.replace(LF, eol) if eol != LF else b


def eol_dominante(dati: bytes) -> bytes:
    """La fine riga del file. Serve al TESTO NUOVO quando l'ancora e' di una riga sola."""
    crlf = dati.count(CRLF)
    return CRLF if crlf and crlf >= (dati.count(LF) - crlf) else LF


def scegli_eol(dati: bytes, testo: str) -> bytes:
    """La fine riga con cui l'ancora compare UNA volta. Ambiguo o assente -> Rifiuto."""
    if LF not in testo.encode("utf-8"):
        # Ancora di una riga sola: la fine riga non la distingue. Conta una volta sola,
        # e il testo nuovo eredita la fine riga del file.
        n = dati.count(testo.encode("utf-8"))
        if n == 0:
            raise Rifiuto("ancora assente")
        if n > 1:
            raise Rifiuto("ancora non unica: %d occorrenze" % n)
        return eol_dominante(dati)
    n_lf = dati.count(adatta(testo, LF))
    n_crlf = dati.count(adatta(testo, CRLF)) if CRLF in dati else 0
    if n_lf == 1 and n_crlf == 0:
        return LF
    if n_crlf == 1 and n_lf == 0:
        return CRLF
    if n_lf == 0 and n_crlf == 0:
        raise Rifiuto("ancora assente (provata in LF e in CRLF)")
    raise Rifiuto("ancora non unica: %d in LF, %d in CRLF" % (n_lf, n_crlf))


def valida(dati: dict) -> list:
    """Tutti i controlli su tutte le modifiche, PRIMA di qualunque scrittura."""
    piano = []
    for chiave, nome, old, new in MODIFICHE:
        if chiave not in dati:
            raise Rifiuto("%s: file '%s' non fornito" % (nome, chiave))
        raw = dati[chiave]
        try:
            eol = scegli_eol(raw, old)
        except Rifiuto as e:
            raise Rifiuto("%s: %s" % (nome, e))
        b_new = adatta(new, eol)
        if raw.count(b_new):
            raise Rifiuto("%s: patch gia' applicata anche solo in parte" % nome)
        piano.append((chiave, nome, adatta(old, eol), b_new, eol))
    return piano


def applica(dati: dict, piano: list) -> dict:
    out = dict(dati)
    for chiave, _nome, old, new, _eol in piano:
        out[chiave] = out[chiave].replace(old, new, 1)
    return out


def inverti(dati: dict, piano: list) -> dict:
    out = dict(dati)
    for chiave, _nome, old, new, _eol in piano:
        if out[chiave].count(new) != 1:
            raise Rifiuto("inversa: il testo nuovo non compare una volta sola")
        out[chiave] = out[chiave].replace(new, old, 1)
    return out


def scrivi_atomico(path: Path, dati: bytes) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + ".bak_%s" % stamp)
    shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dati)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return backup


def verifica_su_disco(percorsi: dict, piano: list) -> list:
    esiti = []
    riletti = {k: Path(v).read_bytes() for k, v in percorsi.items()}
    for chiave, nome, old, new, _eol in piano:
        raw = riletti[chiave]
        # Due modifiche INGLOBANO il testo vecchio nel nuovo (C4 e S2: si aggiunge in coda
        # e si conserva il blocco precedente). Per quelle "vecchio assente" sarebbe falso.
        cond = raw.count(new) == 1 and (old in new or raw.count(old) == 0)
        esiti.append((cond, nome))
    return esiti


def comando_ancore(percorsi: dict) -> int:
    dati = {k: Path(v).read_bytes() for k, v in percorsi.items()}
    print("stato delle cinque ancore:\n")
    problemi = 0
    for chiave, nome, old, new in MODIFICHE:
        raw = dati[chiave]
        # Per un'ancora di una riga sola le due forme sono gli stessi byte: contarle
        # entrambe darebbe 1 LF + 1 CRLF e un falso allarme. Si conta una volta.
        una_riga = LF not in old.encode("utf-8")
        n_lf = raw.count(adatta(old, LF))
        n_crlf = 0 if una_riga else raw.count(adatta(old, CRLF))
        g_lf = raw.count(adatta(new, LF))
        g_crlf = 0 if (LF not in new.encode("utf-8")) else raw.count(adatta(new, CRLF))
        stato = "ok" if (n_lf + n_crlf == 1 and g_lf + g_crlf == 0) else "PROBLEMA"
        if stato != "ok":
            problemi += 1
        print("  [%s] %-40s ancora: %d%s   nuovo testo gia' presente: %d"
              % (stato, nome, n_lf + n_crlf,
                 " (riga sola)" if una_riga else " (%d LF / %d CRLF)" % (n_lf, n_crlf),
                 g_lf + g_crlf))
        if n_lf + n_crlf == 0:
            prima = old.split("\n")[0][:70]
            print("         prima riga cercata: %r" % prima)
    for chiave, p in percorsi.items():
        raw = dati[chiave]
        print("\n  %-10s %s\n             byte %d, sha %s, %d CRLF / %d LF isolati, BOM %s"
              % (chiave, p, len(raw), sha256_bytes(raw)[:16],
                 raw.count(CRLF), raw.count(LF) - raw.count(CRLF),
                 "sì" if raw.startswith(b"\xef\xbb\xbf") else "no"))
    return 0 if problemi == 0 else 3


def comando_apply(percorsi: dict, dry: bool) -> int:
    originali = {k: Path(v).read_bytes() for k, v in percorsi.items()}
    try:
        piano = valida(originali)
        patchati = applica(originali, piano)
        ritorno = inverti(patchati, piano)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        print("Nessun file toccato. `ancore` mostra lo stato di tutte e cinque.", file=sys.stderr)
        return 3
    for k in originali:
        if ritorno[k] != originali[k]:
            print("RIFIUTO: l'inversa non restituisce %s byte per byte" % k, file=sys.stderr)
            return 4

    for chiave, nome, old, new, eol in piano:
        print("  %-40s %s  %+d byte" % (nome, "CRLF" if eol == CRLF else "LF",
                                        len(new) - len(old)))
    for k in originali:
        print("\n%-10s %s\n           byte %d -> %d\n           sha  %s -> %s"
              % (k, percorsi[k], len(originali[k]), len(patchati[k]),
                 sha256_bytes(originali[k])[:16], sha256_bytes(patchati[k])[:16]))

    if dry:
        print("\n[dry-run] niente scritto.")
        return 0

    backup = {}
    for k, p in percorsi.items():
        backup[k] = scrivi_atomico(Path(p), patchati[k])
    esiti = verifica_su_disco(percorsi, piano)
    print()
    for c, nome in esiti:
        print(("  OK  " if c else "  KO  ") + nome)
    for k, b in backup.items():
        print("  backup %-10s %s" % (k, b))
    if not all(c for c, _ in esiti):
        return 5
    print("\nverify: OK sui due file riletti dal disco")
    return 0


# ============================================================ selftest

def _finto_smentite() -> str:
    return ("## 3. Gruppo B\n\n| B5 | 29 | cosa | esito |\n\n" + M1_OLD + "\n\n`paper2_estrai.py`\n")


def _finto_checklist() -> str:
    return (
        "# Paper 2 — Checklist\n\n"
        "## Fase 6 — Record congelato e riproducibilita'\n\n"
        "- [x] 6.8 — chiuso\n"
        + C1_OLD + "\n"
        + C2_OLD + "\n"
    )


def _finto_stato() -> str:
    return (
        "# Paper 2 — stato consolidato\n\n"
        "> **Cosa e' cambiato nell'ottava revisione.**\n"
        + S1_OLD + "\n> dichiarati.\n\n"
        "**Al 13 settembre (ottava revisione):** registro **64 record**\n"
        + S2_OLD + "\n"
    )


def _finto_smentite() -> str:
    return ("## 3. Gruppo B\n\n| B5 | 29 | cosa | esito |\n\n"
            + M1_OLD + "\n\n`paper2_estrai.py`\n")


def selftest() -> int:
    ok = 0
    tot = 0

    def check(cond, nome):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok]   %s" % nome)
        else:
            print("  [FAIL] %s" % nome)

    print("selftest paper2_patch_conteggi_5_5 v%s" % VERSIONE)

    for etichetta, eol in (("LF", LF), ("CRLF", CRLF)):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            pc, ps, pm = d / "checklist.md", d / "stato.md", d / "smentite.md"
            bom = b"\xef\xbb\xbf" if eol == CRLF else b""
            pc.write_bytes(bom + _finto_checklist().encode("utf-8").replace(LF, eol))
            ps.write_bytes(_finto_stato().encode("utf-8").replace(LF, eol))
            pm.write_bytes(_finto_smentite().encode("utf-8").replace(LF, eol))
            orig_c, orig_s = pc.read_bytes(), ps.read_bytes()
            perc = {"checklist": str(pc), "stato": str(ps), "smentite": str(pm)}

            piano = valida({"checklist": orig_c, "stato": orig_s, "smentite": pm.read_bytes()})
            check(len(piano) == 5, "%s: cinque modifiche validate su tre file" % etichetta)
            check(all(p[4] == eol for p in piano), "%s: fine riga riconosciuta su tutte" % etichetta)

            patch = applica({"checklist": orig_c, "stato": orig_s,
                             "smentite": pm.read_bytes()}, piano)
            check(adatta(C1_NEW, eol) in patch["checklist"], "%s: C1 applicata" % etichetta)
            check(adatta(C2_NEW, eol) in patch["checklist"], "%s: C2 applicata" % etichetta)
            check(adatta(M1_NEW, eol) in patch["smentite"], "%s: M1 applicata" % etichetta)
            check(patch["checklist"].startswith(bom) if bom else True, "%s: BOM preservato" % etichetta)
            n_altri = patch["checklist"].count(LF) - patch["checklist"].count(CRLF)
            check((n_altri == 0) if eol == CRLF else True, "%s: nessun LF isolato introdotto" % etichetta)
            check(adatta(M1_OLD, eol) in patch["smentite"],
                  "%s: la sezione 4 resta nel file, sotto la 3-bis" % etichetta)
            inv = inverti(patch, piano)
            check(inv["checklist"] == orig_c and inv["stato"] == orig_s
                  and inv["smentite"] == pm.read_bytes(),
                  "%s: l'inversa restituisce tutti e tre byte per byte" % etichetta)

            rc = comando_apply(perc, dry=True)
            check(rc == 0 and pc.read_bytes() == orig_c and ps.read_bytes() == orig_s,
                  "%s: dry-run non scrive" % etichetta)
            check(len(list(d.iterdir())) == 3, "%s: dry-run non lascia backup ne' temp" % etichetta)

            rc = comando_apply(perc, dry=False)
            check(rc == 0, "%s: apply esito 0" % etichetta)
            check(pc.read_bytes() == patch["checklist"] and ps.read_bytes() == patch["stato"],
                  "%s: i due file sul disco sono quelli attesi" % etichetta)
            baks = sorted(x.name for x in d.iterdir() if ".bak_" in x.name)
            check(len(baks) == 3, "%s: tre backup" % etichetta)
            check(comando_apply(perc, dry=False) == 3,
                  "%s: DIFETTO seconda applicazione rifiutata" % etichetta)

    # --- tutto o niente, e i rifiuti
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        pc, ps = d / "checklist.md", d / "stato.md"
        pc.write_bytes(_finto_checklist().encode("utf-8"))
        pm = d / "smentite.md"
        pm.write_bytes(_finto_smentite().encode("utf-8"))
        # nello stato manca l'ancora S2
        ps.write_bytes(_finto_stato().replace(S2_OLD, "riassunto diverso").encode("utf-8"))
        oc, os_ = pc.read_bytes(), ps.read_bytes()
        perc = {"checklist": str(pc), "stato": str(ps), "smentite": str(pm)}
        rc = comando_apply(perc, dry=False)
        check(rc == 3, "DIFETTO: un'ancora mancante nello stato -> rifiuto")
        check(pc.read_bytes() == oc and ps.read_bytes() == os_,
              "DIFETTO: e la checklist NON viene toccata (tutto o niente)")
        check(not [x for x in d.iterdir() if ".bak_" in x.name], "nessun backup su rifiuto")
        check(comando_ancore(perc) == 3, "ancore: segnala il problema con esito 3")
        pc.write_bytes(_finto_checklist().encode("utf-8").replace(LF, CRLF))
        ps.write_bytes(_finto_stato().encode("utf-8").replace(LF, CRLF))
        pm.write_bytes(_finto_smentite().encode("utf-8").replace(LF, CRLF))
        check(comando_ancore(perc) == 0,
              "DIFETTO: su file sani in CRLF, ancore NON grida al lupo (esito 0)")
        pc.write_bytes(_finto_checklist().encode("utf-8"))
        ps.write_bytes(_finto_stato().encode("utf-8"))
        pm.write_bytes(_finto_smentite().encode("utf-8"))
        check(comando_ancore(perc) == 0, "ancore: esito 0 anche in LF")

        # ancora duplicata
        pc.write_bytes((_finto_checklist() + C1_OLD + "\n").encode("utf-8"))
        ps.write_bytes(_finto_stato().encode("utf-8"))
        pm.write_bytes(_finto_smentite().encode("utf-8"))
        check(comando_apply(perc, dry=True) == 3, "DIFETTO: ancora duplicata -> rifiuto")

        # testo nuovo gia' presente
        pc.write_bytes(_finto_checklist().replace(C1_OLD, C1_NEW).encode("utf-8"))
        pm.write_bytes(_finto_smentite().encode("utf-8"))
        check(comando_apply(perc, dry=True) == 3, "DIFETTO: patch gia' applicata -> rifiuto")

    # --- la riga di comando, che il selftest prima non attraversava
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        pc, ps, pm = d / "checklist.md", d / "stato.md", d / "smentite.md"
        pc.write_bytes(_finto_checklist().encode("utf-8"))
        ps.write_bytes(_finto_stato().encode("utf-8"))
        pm.write_bytes(_finto_smentite().encode("utf-8"))
        argv = ["apply", "--checklist", str(pc), "--stato", str(ps), "--smentite", str(pm),
                "--dry-run"]
        check(main(argv) == 0, "DIFETTO: la riga di comando accetta un'opzione per OGNI file")
        check(main(["ancore", "--checklist", str(pc), "--stato", str(ps),
                    "--smentite", str(pm)]) == 0, "e `ancore` fa lo stesso giro")
        check(set(CHIAVI_FILE) == {m[0] for m in MODIFICHE},
              "le opzioni si derivano da MODIFICHE: un file nuovo non puo' restarne fuori")
        try:
            main(["apply", "--checklist", str(pc), "--stato", str(ps)])
            check(False, "un'opzione mancante deve fallire")
        except SystemExit:
            check(True, "DIFETTO: opzione mancante -> argparse fallisce, non si procede a meta'")

    # --- il contenuto dice le cose che deve dire
    check("12 / 1 / 5" in C1_NEW and "12/1/5" in S1_NEW, "i conteggi corretti in entrambi i documenti")
    check("11" not in C1_NEW.replace("**Q1", "") or "11/1/6" not in C1_NEW,
          "nessuna traccia del conteggio sbagliato")
    check("non è mai stata nel gruppo A" in C1_NEW, "si dice che Q1 non era in A")
    check("record del ledger" in C1_NEW and "non ne hanno uno" in C1_NEW,
          "e perché non può nemmeno entrare in B")
    check("portata" in C1_NEW and "59 record del ledger" in C1_NEW, "la portata di 5.5 è dichiarata")
    check("resta vero **dentro il registro**" in C1_NEW, "la conseguenza sul record 60")
    check("nove script" in C2_NEW and "cancello" in C2_NEW, "la voce 6.9 elenca e distingue")
    check("prima di aver aperto i nove file" in C2_NEW, "e vieta il numero dedotto")
    check("Q1" in M1_NEW and "Q4" in M1_NEW and "0.29σ e 0.14σ" in M1_NEW,
          "la sezione 3-bis porta le quattro Q coi margini")
    check("non decidibile a SGC" in M1_NEW, "Q2 con l'emisfero attaccato")
    check("bootstrap sulle realizzazioni" in M1_NEW, "e dichiara quale dispersione usa")
    print("\nselftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


# I file che le modifiche toccano: la riga di comando si DERIVA da qui, cosi' un file
# nuovo in MODIFICHE non puo' restare senza la sua opzione.
CHIAVI_FILE = sorted({m[0] for m in MODIFICHE})


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="conteggi di 5.5 e sezione delle Q di D6")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for nome in ("ancore", "apply"):
        s = sub.add_parser(nome)
        for chiave in CHIAVI_FILE:
            s.add_argument("--%s" % chiave, required=True)
        if nome == "apply":
            s.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    perc = {chiave: getattr(a, chiave) for chiave in CHIAVI_FILE}
    for k, v in perc.items():
        if not os.path.isfile(v):
            print("FALLIMENTO: %s non trovato: %s" % (k, v), file=sys.stderr)
            return 2
    if a.cmd == "ancore":
        return comando_ancore(perc)
    return comando_apply(perc, a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())

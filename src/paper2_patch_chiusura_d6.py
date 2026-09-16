#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_patch_chiusura_d6.py — checklist rev. 3.24 e stato ottava revisione.

Registra nei due documenti la chiusura di D6 e del punto 6.8 (record 63, freeze CLEAN a
63/63): la lettura di agosto era un artefatto di classe di modelli, il terzo residuo di
Fase 4 si colloca con tre limiti, e le smentite passano a 11/1/6.

Otto modifiche su due file:

  checklist_paper2.md
    C1  intestazione: rev. 3.23 -> rev. 3.24
    C2  D6: la voce si spunta
    C3  D6: l'esito che supera la riserva, e la lettura corretta
    C4  6.8: la voce si spunta
    C5  6.8: la chiusura, i tre limiti, la regola dei due denominatori, le smentite 11/1/6

  paper2_stato.md
    S1  titolo: settima -> ottava revisione
    S2  il blocco dell'ottava revisione, prima di quello della settima
    S3  il riassunto "Al 13 settembre": 63 record, rev. 3.24, D6 chiuso

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

C1_OLD = """### rev. 3.23 — 12 settembre 2026 — record 62; **LA PROVENIENZA DI `pk_matrix` È STABILITA** (tre righe riprodotte bit a bit): il punto 6.8 resta aperto sulla **sola convergenza** della sequenza di modelli"""

C1_NEW = """### rev. 3.24 — 13 settembre 2026 — record 63; **D6 È CHIUSO**, e la sua lettura di agosto era un artefatto di classe di modelli: con lo stesso stimatore ai due lati il vantaggio del polinomio su *P*(*k*) sparisce, e il terzo residuo di Fase 4 si colloca con tre limiti dichiarati"""

C2_OLD = """- [ ] **✦ D6 — Escludere la non linearità, PRIMA di rivendicare D5.**"""

C2_NEW = """- [x] **✧✦ D6 — Escludere la non linearità, PRIMA di rivendicare D5. CHIUSO il 13 set, record 63.**"""

C3_OLD = """      interpretabili finché non lo è."""

C3_NEW = """      interpretabili finché non lo è.

      **✦✦ ESITO, 13 set — record 63. La riserva è superata, e la lettura era sbagliata.** La
      provenienza di `pk_matrix` è chiusa (record 62). La sequenza di polinomi non satura
      nemmeno a SGC — `gain_int` = +0.053 e +0.038 — ma il polinomio non è più lo strumento:
      con **kernel ridge gaussiano ai due lati**, cioè la stessa classe di modelli per i sette
      parametri e per *P*(*k*), il vantaggio misurato in agosto **sparisce**. `K − P` vale
      +0.0015 a NGC e −0.0199 a SGC — 0.1σ e 1.7σ sulle partizioni, 0.8σ e 0.6σ sul bootstrap,
      **con segni opposti**. Quello che D6 aveva misurato era la differenza fra un polinomio di
      35 termini e una regressione lineare su 12 componenti principali, non fra due contenuti
      informativi. Il kernel batte anche il polinomio sul lato dei parametri, +0.023 in
      entrambi gli emisferi: la sequenza dichiarata troncava, e il suo 48–49 % era un limite
      superiore ottenuto con lo strumento sbagliato.
      **Il numero che resta:** *P* e *K* **assieme** lasciano non spiegato il **48.7 %** (NGC) e
      il **49.3 %** (SGC) del tetto 0.832, con dispersioni d'insieme di 6.4 e 5.8 punti.
      `PK − P` è +0.048 e +0.041, concordi di segno ma a **1.9σ e 1.1σ** sul bootstrap: «*P*(*k*)
      aggiunge informazione oltre i parametri» **non è stabilito**, e i 4–5σ delle partizioni non
      vanno citati per sostenerlo."""

C4_OLD = """- [ ] **✦✦ 6.8 — D6 e il terzo residuo di Fase 4, RINVIATI QUI con il loro motivo**"""

C4_NEW = """- [x] **✧✦✧ 6.8 — D6 e il terzo residuo di Fase 4. CHIUSO il 13 set, record 63**"""

C5_OLD = """      misurati sulla stessa realizzazione è **0.832**."""

C5_NEW = """      misurati sulla stessa realizzazione è **0.832**.

      **✧✦✧ CHIUSO il 13 set, record 63.** Il terzo residuo **esce da «rinviato» ed entra fra i
      risultati**, con tre limiti da riscrivere ovunque il numero compaia: il nucleo gaussiano a
      *n* = 2000 è una classe ampia ma **non universale**; **K è il *P*(*k*) della materia oscura
      nel box a *z* = 0**, non il due punti del campo di cui si misura la topologia; e **47 dei
      110 bin stanno sopra Nyquist**, quindi l'informazione a piccola scala in K è quella che una
      griglia 128³ può portare, non quella che la persistenza a *R* = 5 vede. Il legame col
      residuo beyond-two-point di 1710 generatori del Paper 1 è dichiarato **coerente e non
      stabilito**, perché gli ultimi due limiti cadono proprio lì.
      **Due denominatori, da qui in avanti.** Un margine da soglia si misura contro il **bootstrap
      sulle realizzazioni**, non contro le ripetizioni della CV, che si restringono con lo sforzo
      speso a misurarle e non contengono il campionamento della coorte. Il rapporto misurato fra
      le due dispersioni è **2.8–3.8**. È la stessa famiglia della regola R1 di 5.1: il
      denominatore si dichiara.
      **Smentite ricontate: 11 in A, 1 in A-bis, 6 in B.** Q1 è ritirata come falsificazione —
      0.29σ e 0.14σ dalla sua soglia — e passa al gruppo B accanto alla P1 di D3. Q2 cade a NGC
      (4.7σ) e **non è decidibile** a SGC (2.0σ): una smentita che non si replica si scrive così.
      Q3 tiene solo con la procedura attaccata, perché col kernel e il denominatore d'insieme sta
      a 2.6σ da 0.50.
      *(Residuo di contabilità, da chiudere: `paper2_5_5_smentite.md` e la voce 5.5 dicono ancora
      dodici in A e cinque in B.)*"""

S1_OLD = """### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **12 settembre 2026**, settima revisione"""

S1_NEW = """### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **13 settembre 2026**, ottava revisione"""

S2_OLD = """> **Cosa è cambiato nella settima revisione (12 settembre) — LA PROVENIENZA DI `pk_matrix` È"""

S2_NEW = """> **Cosa è cambiato nell'ottava revisione (13 settembre) — D6 È CHIUSO, E LA SUA LETTURA DI
> AGOSTO ERA UN ARTEFATTO DI CLASSE DI MODELLI.** Con lo stesso stimatore ai due lati — kernel
> ridge gaussiano sui sette parametri e sui 110 bin di log₁₀ *P*(*k*) — il vantaggio del
> polinomio **sparisce**: `K − P` sta a 0.1σ e 1.7σ **con segni opposti** nei due emisferi. Ciò
> che D6 aveva misurato in agosto era la differenza fra un polinomio di 35 termini e una
> regressione lineare su 12 componenti. Quel che resta, misurato ora in **entrambi** gli emisferi
> — D6 non era mai stato eseguito a SGC — è che i sette parametri e lo spettro di potenza
> **assieme** lasciano non spiegato il **48.7 %** e il **49.3 %** del tetto 0.832, con dispersioni
> d'insieme di 6.4 e 5.8 punti. `PK − P` è concorde di segno ma sta a **1.9σ e 1.1σ** sul
> bootstrap: **non stabilito**. **Regola nuova:** un margine da soglia si misura contro una
> dispersione che non si restringe con lo sforzo speso a misurarla — il bootstrap sulle
> realizzazioni, 2.8–3.8 volte più largo delle ripetizioni della CV. **Smentite ricontate
> 11/1/6**: Q1 è ritirata come falsificazione, Q2 cade a NGC e non è decidibile a SGC, Q3 tiene
> solo con la procedura attaccata. Il terzo residuo di Fase 4 **si colloca**, con tre limiti
> dichiarati, e il legame col beyond-two-point del Paper 1 resta **coerente e non stabilito**.
> Record 63, `freeze_verify` CLEAN a 63/63.

> **Cosa è cambiato nella settima revisione (12 settembre) — LA PROVENIENZA DI `pk_matrix` È"""

S3_OLD = """**Al 12 settembre (settima revisione):** registro **62 record**, CLEAN a 62/62 · checklist
**rev. 3.23** · Fase 4 **decisa** · Fase 5 **chiusa**, 5.1–5.6 tutte fatte · voci per il Paper 1
**tredici**, di cui quattro toccano un'affermazione (P1-7, P1-10, P1-11, P1-12) · provenienza di
`pk_matrix` **stabilita** (tre righe bit a bit, record 61 e 62) · il punto 6.8 aperto sulla **sola
convergenza** della sequenza di modelli."""

S3_NEW = """**Al 13 settembre (ottava revisione):** registro **63 record**, CLEAN a 63/63 · checklist
**rev. 3.24** · Fase 4 **decisa** · Fase 5 **chiusa** · provenienza di `pk_matrix` **stabilita**
(record 61 e 62) · **D6 chiuso** e il punto 6.8 con esso (record 63): il terzo residuo è
collocato, con tre limiti · voci per il Paper 1 **tredici** · smentite **11 in A, 1 in A-bis, 6
in B**."""

MODIFICHE = [
    ("checklist", "C1 intestazione rev. 3.23 -> 3.24", C1_OLD, C1_NEW),
    ("checklist", "C2 D6, la voce si spunta", C2_OLD, C2_NEW),
    ("checklist", "C3 D6, l'esito che supera la riserva", C3_OLD, C3_NEW),
    ("checklist", "C4 6.8, la voce si spunta", C4_OLD, C4_NEW),
    ("checklist", "C5 6.8, la chiusura e i tre limiti", C5_OLD, C5_NEW),
    ("stato", "S1 titolo, settima -> ottava", S1_OLD, S1_NEW),
    ("stato", "S2 blocco dell'ottava revisione", S2_OLD, S2_NEW),
    ("stato", "S3 riassunto al 13 settembre", S3_OLD, S3_NEW),
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
    print("stato delle otto ancore:\n")
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
        print("Nessun file toccato. `ancore` mostra lo stato di tutte e sette.", file=sys.stderr)
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

def _finto_checklist() -> str:
    return (
        "# Paper 2 — Checklist di sviluppo, da zero alla scrittura\n"
        + C1_OLD + "\n\n"
        "## Fase 4D — Componente D\n\n"
        + C2_OLD + " *R*² è lineare: una dipendenza\n"
        "      quadratica apparirebbe identica.\n"
        "      **Riserva dichiarata:** la sequenza di modelli **non converge** e i test B e C non sono\n"
        + C3_OLD + "\n\n"
        "## Fase 6 — Record congelato e riproducibilità\n\n"
        + C4_OLD + " *(12 set,\n"
        "      record 60)*.\n"
        "      **Il tetto da non sbagliare due volte:** per predittori misurati sulla stessa\n"
        "      realizzazione non è 0.698 ma **0.832**.\n"
        "      Il tetto per predittori\n"
        + C5_OLD + "\n\n"
        "## Fase 7 — Scrittura\n"
    )


def _finto_stato() -> str:
    return (
        "# Paper 2 — stato consolidato\n"
        + S1_OLD + "\n\n"
        "**Famiglie:** F · P · G · S · R · X · Y · Z\n\n"
        + S2_OLD + "\n"
        "> Ogni termine del budget porta ora tre dichiarazioni.\n\n"
        "| regole con soglia | — | 0 su 6 |\n\n"
        + S3_OLD + "\n\n---\n"
    )


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

    print("selftest paper2_patch_chiusura_6_8 v%s" % VERSIONE)

    for etichetta, eol in (("LF", LF), ("CRLF", CRLF)):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            pc, ps = d / "checklist.md", d / "stato.md"
            bom = b"\xef\xbb\xbf" if eol == CRLF else b""
            pc.write_bytes(bom + _finto_checklist().encode("utf-8").replace(LF, eol))
            ps.write_bytes(_finto_stato().encode("utf-8").replace(LF, eol))
            orig_c, orig_s = pc.read_bytes(), ps.read_bytes()
            perc = {"checklist": str(pc), "stato": str(ps)}

            piano = valida({"checklist": orig_c, "stato": orig_s})
            check(len(piano) == 8, "%s: otto modifiche validate" % etichetta)
            check(all(p[4] == eol for p in piano), "%s: fine riga riconosciuta su tutte" % etichetta)

            patch = applica({"checklist": orig_c, "stato": orig_s}, piano)
            check(adatta(C1_NEW, eol) in patch["checklist"], "%s: C1 applicata" % etichetta)
            check(adatta(C3_NEW, eol) in patch["checklist"], "%s: C3 applicata" % etichetta)
            check(adatta(S2_NEW, eol) in patch["stato"], "%s: S2 applicata" % etichetta)
            check(patch["checklist"].startswith(bom) if bom else True, "%s: BOM preservato" % etichetta)
            n_altri = patch["checklist"].count(LF) - patch["checklist"].count(CRLF)
            check((n_altri == 0) if eol == CRLF else True, "%s: nessun LF isolato introdotto" % etichetta)
            check(adatta(S2_OLD, eol) in patch["stato"],
                  "%s: il blocco della sesta revisione resta nel file" % etichetta)
            inv = inverti(patch, piano)
            check(inv["checklist"] == orig_c and inv["stato"] == orig_s,
                  "%s: l'inversa restituisce entrambi byte per byte" % etichetta)

            rc = comando_apply(perc, dry=True)
            check(rc == 0 and pc.read_bytes() == orig_c and ps.read_bytes() == orig_s,
                  "%s: dry-run non scrive" % etichetta)
            check(len(list(d.iterdir())) == 2, "%s: dry-run non lascia backup ne' temp" % etichetta)

            rc = comando_apply(perc, dry=False)
            check(rc == 0, "%s: apply esito 0" % etichetta)
            check(pc.read_bytes() == patch["checklist"] and ps.read_bytes() == patch["stato"],
                  "%s: i due file sul disco sono quelli attesi" % etichetta)
            baks = sorted(x.name for x in d.iterdir() if ".bak_" in x.name)
            check(len(baks) == 2, "%s: due backup" % etichetta)
            check(comando_apply(perc, dry=False) == 3,
                  "%s: DIFETTO seconda applicazione rifiutata" % etichetta)

    # --- tutto o niente, e i rifiuti
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        pc, ps = d / "checklist.md", d / "stato.md"
        pc.write_bytes(_finto_checklist().encode("utf-8"))
        # nello stato manca l'ancora S3
        ps.write_bytes(_finto_stato().replace(S3_OLD, "riassunto diverso").encode("utf-8"))
        oc, os_ = pc.read_bytes(), ps.read_bytes()
        perc = {"checklist": str(pc), "stato": str(ps)}
        rc = comando_apply(perc, dry=False)
        check(rc == 3, "DIFETTO: un'ancora mancante nello stato -> rifiuto")
        check(pc.read_bytes() == oc and ps.read_bytes() == os_,
              "DIFETTO: e la checklist NON viene toccata (tutto o niente)")
        check(not [x for x in d.iterdir() if ".bak_" in x.name], "nessun backup su rifiuto")
        check(comando_ancore(perc) == 3, "ancore: segnala il problema con esito 3")
        pc.write_bytes(_finto_checklist().encode("utf-8").replace(LF, CRLF))
        ps.write_bytes(_finto_stato().encode("utf-8").replace(LF, CRLF))
        check(comando_ancore(perc) == 0,
              "DIFETTO: su file sani in CRLF, ancore NON grida al lupo (esito 0)")
        pc.write_bytes(_finto_checklist().encode("utf-8"))
        ps.write_bytes(_finto_stato().encode("utf-8"))
        check(comando_ancore(perc) == 0, "ancore: esito 0 anche in LF")

        # ancora duplicata
        pc.write_bytes((_finto_checklist() + C1_OLD + "\n").encode("utf-8"))
        ps.write_bytes(_finto_stato().encode("utf-8"))
        check(comando_apply(perc, dry=True) == 3, "DIFETTO: ancora duplicata -> rifiuto")

        # testo nuovo gia' presente
        pc.write_bytes(_finto_checklist().replace(C1_OLD, C1_NEW).encode("utf-8"))
        check(comando_apply(perc, dry=True) == 3, "DIFETTO: patch gia' applicata -> rifiuto")

    # --- il contenuto dice le cose che deve dire
    check("48.7 %" in C3_NEW and "49.3 %" in C3_NEW, "il non spiegato dei due emisferi nel testo D6")
    check("non è stabilito" in C3_NEW and "non stabilito" in S2_NEW,
          "PK-P dichiarato non stabilito in entrambi i documenti")
    check("segni opposti" in C3_NEW and "segni opposti" in S2_NEW, "K-P: i segni opposti sono detti")
    check("47 dei\n      110 bin" in C5_NEW or "47 dei" in C5_NEW, "i 47 bin sopra Nyquist fra i limiti")
    check("coerente e non\n      stabilito" in C5_NEW or "coerente e non" in C5_NEW,
          "il legame col beyond-two-point e' coerente e non stabilito")
    check("11 in A" in C5_NEW and "11/1/6" in S2_NEW, "le smentite ricontate in entrambi")
    check("paper2_5_5_smentite.md" in C5_NEW, "il residuo di contabilita' e' nominato, non dimenticato")
    check("63 record" in S3_NEW and "rev. 3.24" in S3_NEW, "il riassunto porta 63 record e rev. 3.24")
    check("bootstrap" in C5_NEW and "2.8–3.8" in C5_NEW, "la regola dei due denominatori col rapporto")

    print("\nselftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="checklist rev. 3.23 e stato settima revisione")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for nome in ("ancore", "apply"):
        s = sub.add_parser(nome)
        s.add_argument("--checklist", required=True)
        s.add_argument("--stato", required=True)
        if nome == "apply":
            s.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    perc = {"checklist": a.checklist, "stato": a.stato}
    for k, v in perc.items():
        if not os.path.isfile(v):
            print("FALLIMENTO: %s non trovato: %s" % (k, v), file=sys.stderr)
            return 2
    if a.cmd == "ancore":
        return comando_ancore(perc)
    return comando_apply(perc, a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())

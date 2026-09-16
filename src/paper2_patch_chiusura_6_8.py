#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_patch_chiusura_6_8.py — checklist rev. 3.23 e stato settima revisione.

Registra nei due documenti la chiusura della PROVENIENZA di `pk_matrix` (record 61 e 62,
freeze CLEAN a 62/62), e lascia il punto 6.8 aperto sulla **sola convergenza** della
sequenza di modelli.

Sette modifiche su due file:

  checklist_paper2.md
    C1  intestazione: rev. 3.22 -> rev. 3.23
    C2  6.8, la clausola della riserva che ora e' falsa
    C3  6.8, "Da fare qui": la provenienza e' fatta, e arriva il blocco della prova
    C4  6.7, il kref come voce nuova della mappa, con l'asimmetria delle coperture

  paper2_stato.md
    S1  titolo: sesta -> settima revisione
    S2  il blocco della settima revisione, prima di quello della sesta
    S3  il riassunto "Al 12 settembre": 62 record, rev. 3.23, 6.8 sulla sola convergenza

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

C1_OLD = """### rev. 3.22 — 12 settembre 2026 — record 60; **LA FASE 5 È CHIUSA** (ogni denominatore dichiarato, quattro correzioni al Paper 1) **e le sue quattro voci aperte sono passate alla Fase 6, punto 6.0**"""

C1_NEW = """### rev. 3.23 — 12 settembre 2026 — record 62; **LA PROVENIENZA DI `pk_matrix` È STABILITA** (tre righe riprodotte bit a bit): il punto 6.8 resta aperto sulla **sola convergenza** della sequenza di modelli"""

C2_OLD = """      **provenienza di `pk_matrix` non è stabilita**, quindi i test B e C non sono interpretabili."""

C2_NEW = """      **provenienza di `pk_matrix` non era stabilita**, quindi i test B e C non erano
      interpretabili. **✦✦ Dal 12 set la provenienza è chiusa** (record 62): resta la sola
      convergenza, e la prova è nel blocco in fondo a questa voce."""

C3_OLD = """      **Da fare qui, in quest'ordine:** stabilire la provenienza di `pk_matrix`; far convergere la
      sequenza di modelli; poi decidere quale delle due letture è sostenuta."""

C3_NEW = """      **✦✦ La provenienza è stabilita, 12 set, record 61 e 62.** Tre righe del cache — **0, 1000,
      1999** — sono state riprodotte dal codice di HEAD **bit a bit**, `rel_max = 0.0`. La
      riproduzione chiude insieme le tre dichiarazioni che un digest non dà: codice scrivente,
      semantica e ordine delle righe. `git log --follow` su `phase7_r53_robustness.py` porta **un
      solo commit, del 2 luglio**, un mese DOPO l'mtime del cache (5 giu, 20:48): il versionamento
      non poteva datare lo scrivente, e solo la riproduzione poteva. L'ordine ha anche un argomento
      **strutturale**: `_compute_pk_matrix` non usa un glob, itera `for i in range(2000)` su
      `NWLH_DIR/str(i)`, quindi l'ordinamento lessicografico che ha prodotto gli errori di
      `per_mock` e n6 non può nascere qui. Il test statistico concorda — *R*² 0.897 / 0.899 / 0.766
      contro un nullo per permutazione il cui **massimo** su mille permutazioni è ~0.012 — e i segni
      sono coerenti: σ₈ sull'ampiezza, Ω_m e *n*_s sulla forma, *w*₀ invisibile a −7 × 10⁻⁵.

      **Tre voci testuali vengono con la chiusura, nessuna consequenziale per l'*R*²:**
      - il cache è **log₁₀ *P*(*k*)** e non *P*(*k*): per l'*R*² la base del logaritmo è un fattore
        moltiplicativo e non conta, il logaritmo sì. Il manoscritto deve scrivere ciò che è stato
        eseguito;
      - il campo è `df_m_128_PCS_z=0.npy` e il codice dichiara **`MAS='CIC'`**: Pylians deconvolve
        la finestra sbagliata. È un fattore per *k* identico in ogni riga, quindi si cancella in
        qualunque *R*² a pesi fissi sulle colonne; **non** si cancella in una frase che citi un
        valore o una forma di *P*(*k*), o che lo confronti con un *P*(*k*) esterno;
      - **47 dei 110 bin stanno sopra Nyquist** (*k* > 0.40212, e *k*_max/*k*_Nyq = 1.7253, la
        diagonale del cubo a meno dello 0.4 %). Come **predittori** quei modi restano funzioni del
        contenuto a due punti, quindi il test B è legittimo; come **misure** di *P*(*k*) no, e
        nessuna affermazione localizzata in *k* in quell'intervallo è difendibile.

      Il riempimento `mean_pk`, che avrebbe attenuato ogni *R*² in silenzio, **non è scattato**:
      zero righe duplicate, e zero anche nella forma **singola** — che il test sui duplicati non
      vede, perché un riempimento solo non ha gemelli — con la riga più vicina alla media delle
      altre a 1.8 × 10⁻² contro una soglia di 10⁻⁵. L'asse *k*, che il cache non conteneva, è ora
      `results/paper2/phase7_pk_nwlh_kref.npz` (record 61).

      **Da fare qui, e solo questo:** far convergere la sequenza di modelli; poi decidere quale
      delle due letture è sostenuta. **Interpretabile non è convergente:** il **48.3 % resta un
      limite superiore, non una misura**, oggi nessun numero sul 62.7 % / 60.3 % è citabile, il
      residuo 3 non entra nel budget di 5.1 né nella discussione, e il tetto per predittori
      misurati sulla stessa realizzazione è **0.832**."""

C4_OLD = """e l'emendamento 11 lo registra. Scrivibile adesso."""

C4_NEW = """e l'emendamento 11 lo registra. Scrivibile adesso.
      **✦✦ Voce nuova, 12 set:** `results/paper2/phase7_pk_nwlh_kref.npz` (record 61, sha
      `92679cbd…`), l'asse *k* delle 110 colonne di `pk_matrix`. Con un'asimmetria da scrivere: il
      cache è **nel corpo del manifest `features`** (riga 10, stesso digest) **e** nel record 5,
      quindi ha due coperture; il kref ne ha una sola, il record 61. E sta in `results/paper2/` e
      non nella radice di `results/` perché lì cadrebbe **dentro** le regole del tier `features` e
      il freeze lo segnalerebbe come file extra — due FAIL, visti e rientrati col trasloco."""

S1_OLD = """### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **12 settembre 2026**, sesta revisione"""

S1_NEW = """### Indice unico di tutto ciò che è aperto e chiuso — aggiornato **12 settembre 2026**, settima revisione"""

S2_OLD = """> **Cosa è cambiato nella sesta revisione (12 settembre) — LA FASE 5 È CHIUSA.**"""

S2_NEW = """> **Cosa è cambiato nella settima revisione (12 settembre) — LA PROVENIENZA DI `pk_matrix` È
> STABILITA.** Tre righe del cache `phase7_pk_nwlh_cache.npz` — 0, 1000, 1999 — riprodotte dal
> codice di HEAD **bit a bit**, `rel_max = 0.0`. La riproduzione chiude insieme codice scrivente,
> semantica e ordine delle righe, cioè le tre dichiarazioni che il digest congelato non dava: e
> `git log` non poteva chiuderle, perché l'unico commit sul file dello scrivente è di un mese
> **dopo** l'mtime del cache. Tre voci testuali vengono con essa, **nessuna consequenziale per
> l'*R*²**: il cache è **log₁₀ *P*** e non *P*; il codice dichiara `MAS='CIC'` su un campo `PCS`,
> un fattore per *k* uguale in ogni riga; **47 dei 110 bin stanno sopra Nyquist**. Il riempimento
> `mean_pk` **non è scattato**, controllato anche nella forma singola che il test sui duplicati non
> vede. Nasce `results/paper2/phase7_pk_nwlh_kref.npz`, l'asse *k* (record 61). **Il 6.8 resta
> aperto sulla sola convergenza:** il 48.3 % è ancora un **limite superiore** e il residuo 3 non
> entra né nel budget né nella discussione. Record 61 e 62, `freeze_verify` CLEAN a 62/62.
> *(Una nota sul record 61: il suo `reason` è incompleto — gli mancano le due frasi sul perché il
> kref sta in `results/paper2/` — per una sostituzione andata a vuoto in silenzio nello strumento
> che ha costruito il record. Il registro è append-only e il record non si riscrive: la ragione è
> qui e nel 6.7, e l'emendamento formale si appoggia al prossimo record sostanziale.)*

> **Cosa è cambiato nella sesta revisione (12 settembre) — LA FASE 5 È CHIUSA.**"""

S3_OLD = """**Al 12 settembre (sesta revisione):** registro **60 record**, CLEAN a 60/60 · checklist
**rev. 3.21** · Fase 4 **decisa** · Fase 5 **chiusa**, 5.1–5.6 tutte fatte · voci per il Paper 1
**tredici**, di cui quattro toccano un'affermazione (P1-7, P1-10, P1-11, P1-12) · un residuo
**rinviato** alla Fase 6."""

S3_NEW = """**Al 12 settembre (settima revisione):** registro **62 record**, CLEAN a 62/62 · checklist
**rev. 3.23** · Fase 4 **decisa** · Fase 5 **chiusa**, 5.1–5.6 tutte fatte · voci per il Paper 1
**tredici**, di cui quattro toccano un'affermazione (P1-7, P1-10, P1-11, P1-12) · provenienza di
`pk_matrix` **stabilita** (tre righe bit a bit, record 61 e 62) · il punto 6.8 aperto sulla **sola
convergenza** della sequenza di modelli."""

MODIFICHE = [
    ("checklist", "C1 intestazione rev. 3.22 -> 3.23", C1_OLD, C1_NEW),
    ("checklist", "C2 6.8, la clausola della riserva", C2_OLD, C2_NEW),
    ("checklist", "C3 6.8, la prova e cio' che resta", C3_OLD, C3_NEW),
    ("checklist", "C4 6.7, il kref nella mappa", C4_OLD, C4_NEW),
    ("stato", "S1 titolo, sesta -> settima", S1_OLD, S1_NEW),
    ("stato", "S2 blocco della settima revisione", S2_OLD, S2_NEW),
    ("stato", "S3 riassunto al 12 settembre", S3_OLD, S3_NEW),
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
    print("stato delle sette ancore:\n")
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
        "## Fase 6 — Record congelato e riproducibilità\n\n"
        "- [ ] **✧✧✧✧✧ 6.7 — `REPRODUCIBILITY.md` alla radice**: il tier\n"
        "      `records` è passato a 224 file e `5364cf2e…`, " + C4_OLD + "\n"
        "- [ ] **✦✦ 6.8 — D6 e il terzo residuo di Fase 4, RINVIATI QUI con il loro motivo**\n"
        "      **Perché non è collocabile adesso:** D6 è aperto con la sua riserva già dichiarata — la\n"
        "      sequenza di modelli **non converge** (il 48.3 % è un limite superiore, non una misura) e la\n"
        + C2_OLD + "\n"
        "      Senza D6 le due letture non si separano.\n"
        + C3_OLD + "\n\n"
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
            check(len(piano) == 7, "%s: sette modifiche validate" % etichetta)
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
    check("48.3 %" in C3_NEW and "limite superiore, non una misura" in C3_NEW,
          "il testo nuovo tiene il 48.3 % come limite superiore")
    check("0.832" in C3_NEW, "e il tetto a 0.832")
    check("47 dei 110 bin" in C3_NEW and "47 dei 110 bin" in S2_NEW, "i 47 bin in entrambi i file")
    check("log₁₀" in C3_NEW and "log₁₀" in S2_NEW, "log10 P e non P, in entrambi")
    check("reason` è incompleto" in S2_NEW, "lo stato dichiara il record 61 incompleto")
    check("non entra nel budget" in C3_NEW and "né nella discussione" in S2_NEW,
          "il residuo 3 resta fuori da budget e discussione")
    check("62 record" in S3_NEW and "rev. 3.23" in S3_NEW, "il riassunto porta 62 record e rev. 3.23")

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

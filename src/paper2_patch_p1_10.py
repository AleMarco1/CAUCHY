# -*- coding: utf-8 -*-
"""
paper2_patch_p1_10.py -- inserisce la voce P1-10 in modifiche_paper1.md.

Sei modifiche, atomiche (tutte o nessuna):
  E1  intestazione: "Nessuna voce cambia una conclusione" e' falsa (P1-7, P1-10) -> riscritta
  E2  "Stato in una riga": riga P1-10 dopo P1-9
  E3  sezione M26: titolo e "Praticamente accettato" -> accettato il 9 settembre 2026
  E4  sezione M26: esito del controllo di 5.6, e la voce aperta del +309 (§5.3)
  E5  "Cambiamenti a questo documento": riga dell'11 settembre, Fase 5
  E6  testo della voce P1-10, prima di "## P1-5 -- il residuo ... MISURATA"

Uso (dalla radice di cauchy_3.0 o con percorso assoluto):
  python paper2_patch_p1_10.py selftest
  python paper2_patch_p1_10.py dry-run --file modifiche_paper1.md
  python paper2_patch_p1_10.py apply   --file modifiche_paper1.md
  python paper2_patch_p1_10.py verify  --file modifiche_paper1.md

Garanzie:
  - ogni ancora deve comparire ESATTAMENTE una volta, altrimenti nessuna scrittura;
  - rifiuta se la patch risulta gia' applicata (anche parzialmente);
  - preserva BOM e fine riga (LF o CRLF) del file;
  - prima di scrivere, l'inversa delle sei modifiche deve restituire il testo originale
    byte per byte: prova che non cambia nient'altro;
  - scrittura atomica (tmp + fsync + os.replace) con backup accanto al file;
  - dopo la scrittura RILEGGE il file dal disco ed esegue verify.
"""
import argparse
import datetime as _dt
import hashlib
import os
import sys
import tempfile

# ---------------------------------------------------------------------------
# Testi
# ---------------------------------------------------------------------------

E1_OLD = (
    "> **Nessuna voce cambia una conclusione del Paper 1.** Sono tre correzioni di attribuzione e\n"
    "> una di provenienza. Il punto è detto una volta qui e non ripetuto in ciascuna: la lettura\n"
    "> fisica del §7.2 e della Tabella 12 regge sotto ogni verifica fatta."
)
E1_NEW = (
    "> **Due voci toccano un'affermazione fisica, e lo dichiarano:** P1-7 (§9, i «fingers of God»)\n"
    "> e P1-10 (§8.1, l'origine del massimo a *k*=1). Nessuna voce tocca la misura del deficit, il\n"
    "> suo rango o la scomposizione spettrale. La lettura fisica del §7.2 — che fa nascere i voxel a\n"
    "> copertura minima dall'asimmetria di pesatura — è **in verifica** contro gli esiti di 4.2c e\n"
    "> 4.2b-4 su v2; se non regge, entra qui come P1-11.\n"
    "> *(Riscritto l'11 settembre: la versione precedente diceva che nessuna voce cambiava una\n"
    "> conclusione, e P1-7 e P1-10 la smentiscono.)*"
)

E2_OLD = ("| **P1-9** | Δ*N*_H1 della ripesatura: da 60 a 2000 realizzazioni, in **tre punti** "
          "| **PRONTA** |")
E2_NEW = E2_OLD + "\n" + (
    "| **P1-10** | §8.1, didascalia Tab. 9, §10 (vii): il massimo a *k*=1 attribuito ai voxel "
    "«FKP-contaminated» — **smentito da 4.3b** | **PRONTA** — dipende da P1-9 |"
)

E3_OLD = ("## M26 (MN-26-2100-P R1) — nessuna modifica proposta\n\n"
          "Praticamente accettato, in attesa dei commenti dell'editore.")
E3_NEW = ("## M26 (MN-26-2100-P) — accettato; nessuna modifica dalla Fase 4, una voce aperta da 5.1\n\n"
          "**Accettato da MNRAS il 9 settembre 2026** (ricevuto in forma rivista il 23 agosto, in forma\n"
          "originale l'8 luglio).")

E4_OLD = ("Paper 1 (P1-3), e portarla in M26 aprirebbe una revisione per una cosa che il Paper 1 dice\n"
          "meglio.")
E4_NEW = E4_OLD + "\n\n" + (
    "**Controllo di 5.6, 11 settembre: la Fase 4 non richiede una nota su M26.** M26 non riporta\n"
    "*D*(*k*) per livello e non attribuisce il massimo a *k*=1; il §4.1 attribuisce i picchi di δ\n"
    "alla copertura quasi nulla, non ai pesi — cioè alla lettura che la Fase 4 conferma. La riga\n"
    "della Tabella 1, −78.0 ± 8.0, contro l'ensemble completo, −89.15 ± 1.25, sta a 1.4σ e vale\n"
    "l'1.24 % del deficit, dentro il «1–2 %» del §5.3.\n\n"
    "**Aperta l'11 settembre, da 5.1 e non dalla Fase 4: il +309 del §5.3 non è l'1 % del deficit.**\n"
    "Il §5.3 chiude con «Under either variant the systematic is bounded at 1–2% of the deficit».\n"
    "Il rebuild di DESI a pesi unitari sposta β₁^max di +309, cioè l'**1.09 % di β₁^max** (28 256) e\n"
    "il **4.30 % del deficit** (7181). Il «∼ 1%» accanto al +309 è di *N*, quello accanto al −78 è di\n"
    "*D*: coincidono alla seconda cifra (1.09 % e 1.09 %) e la frase li ha fusi. La conclusione —\n"
    "sotto-dominante — regge; il numero no. La stessa ambiguità sta nella riga «+309 (∼1 %)» della\n"
    "Tab. 8 del Paper 1. **Da decidere:** correzione in bozza o erratum; in ogni caso **una sola**\n"
    "nota."
)

E5_OLD = ("| 8 set 2026 | apertura. P1-1, P1-3, P1-4 PRONTE; P1-2 BLOCCATA sulla provenienza; "
          "P1-5 in attesa di 4.2a |")
E5_NEW = E5_OLD + "\n" + (
    "| 11 set 2026, Fase 5 | **P1-10**: 4.3b fallisce (record 59), il massimo a *k*=1 non cala con i "
    "mock pesati, e l'attribuzione del §8.1 ai voxel «FKP-contaminated» cade in **tre punti**. "
    "Seconda voce, dopo P1-7, che tocca un'affermazione fisica; nasce da 5.6. **Intestazione "
    "riscritta** di conseguenza. **M26 accettato il 9 settembre**: la Fase 4 non lo tocca, ma 5.1 "
    "trova nel §5.3 un +309 dato come «1–2 % del deficit» che ne vale il 4.30 % — voce aperta |"
)

P1_10_SECTION = """## P1-10 — §8.1: il massimo a *k*=1 non viene dai voxel contaminati

**Stato: PRONTA.** Dipende da **P1-9**: il nuovo testo del §8.1 rimanda all'ensemble appaiato
completo del §7.2, che esiste nel manoscritto solo dopo P1-9.

**Natura: correzione di attribuzione causale.** Le misure restano tutte; cade la *causa* che il
testo assegna al massimo.

### perché

**4.3b era la prova diretta di questa frase.** È la tensione F0.4 della Componente C: il §8.1
attribuisce il massimo alla rimozione dei voxel contaminati, il §7.2 misura l'effetto della
pesatura in −78 loop contro un'escursione *k*=0→1 di circa +1840 — fattore ~24. La regola,
dichiarata nel record 50, aveva due rami: se il massimo viene dalla pesatura, sui mock pesati il
picco si appiattisce; altrimenti è geometrico.

**Esito (record 59):**

| | *P*^v1 corretta | *P*^v2 corretta | soglia di fallimento |
|---|---:|---:|---:|
| NGC | 3.8161 pp | **3.8445 pp** | > 2.544 |
| SGC | 3.9716 pp | **3.9878 pp** | > 2.648 |

A 678σ e 554σ da zero, contro una clausola di successo che chiedeva compatibilità con zero entro
3σ. Il picco non cala in nessuno dei due emisferi: secondo ramo.

**E il Paper 1 si contraddiceva già da solo.** Il §7.2 dice che i voxel contaminati «carry
essentially no cycles» — tagliandoli al 1°, 5° e 10° percentile i mock conservano il 100.1, 100.1
e 98.7 % dei loop. Voxel che non portano cicli non possono spostare *N*_H1 di un livello di
erosione.

### cosa resta vero, e il testo conserva

Il massimo a *k*=1 (25.4 / 27.1 %), il rango 1/2001 a ogni livello, il 99.4 % dei voxel a
copertura minima entro due voxel dal bordo — co-localizzazione misurata, non spiegazione —, la
riconciliazione del segno della skewness, le escursioni 6.8/9.8 pp e la correzione del 2.0/2.7.

### cosa il testo NON afferma, di proposito

Il meccanismo geometrico. Il bordo degradato dei dati, che i cut-sky ritagliati da un cubo pieno
non riproducono, è un candidato e materia del Paper 2, ma **non è stabilito** come causa del picco.
Nel Paper 1 basta ritirare l'attribuzione e dire che il massimo non dipende dalla pesatura.

**Nessun numero di *P* nel testo.** La prominenza con la sottrazione della curvatura non è
definita nel Paper 1. «Does not reduce the maximum» è verificabile su *P*^v2 ≥ *P*^v1 in
entrambi gli emisferi, e basta.

### punto 1: §8.1, il corpo

**Da:**

> The favourable one: the deficit survives every boundary treatment with rank 1/2001, and its
> maximum occurs at *k* = 1 (25.4 per cent NGC, 27.1 SGC) — the erosion level that removes exactly
> the first boundary layer where the FKP-contaminated denominator voxels live (99.4 per cent of
> them lie within two voxels of the boundary; the same layer whose removal reconciles the
> hemispheres on the skewness sign, Section 5.3). Cleaning the boundary makes the anomaly larger,
> not smaller; at deeper erosions the deficit declines gently as true volume is removed.

**A:**

> The favourable one: the deficit survives every boundary treatment with rank 1/2001, and its
> maximum occurs at *k* = 1 (25.4 per cent NGC, 27.1 SGC) — the erosion level that removes the
> first boundary layer, the same layer whose removal reconciles the hemispheres on the skewness
> sign (Section 5.3). This layer also hosts the lowest-coverage denominator voxels of Section 7.2
> (99.4 per cent of them lie within two voxels of the boundary), but the coincidence does not
> explain the maximum: those voxels carry essentially no cycles (Section 7.2), and voxelizing the
> mocks with *w*_FKP(*z*) over the full paired ensemble does not reduce the maximum in either
> hemisphere. The maximum is a geometric property of the first boundary layer, not of the mock
> weighting. Removing that layer makes the anomaly larger, not smaller; at deeper erosions the
> deficit declines gently as true volume is removed.

Il resto del capoverso («The corrective one: …») resta invariato.

### punto 2: didascalia della Tabella 9

**Da:**

> The *k* = 1 level — absent from the submitted version — maximises the deficit in both
> hemispheres: the first boundary layer contains the FKP-contaminated voxels of Section 7.2, and
> removing it cleans the comparison.

**A:**

> The *k* = 1 level — absent from the submitted version — maximises the deficit in both
> hemispheres; the maximum is a geometric property of the first boundary layer and is not removed
> by FKP weighting of the mocks (Section 8.1).

### punto 3: §10, conclusione (vii)

**Da:**

> The deficit survives every boundary erosion with rank 1/2001 and is maximised when the
> FKP-contaminated first boundary layer is removed (complete-ladder excursion 6.8/9.8 percentage
> points, correcting the submitted 2.0/2.7).

**A:**

> The deficit survives every boundary erosion with rank 1/2001 and is maximised when the first
> boundary layer is removed — a geometric property of that layer, which FKP weighting of the mocks
> does not remove (complete-ladder excursion 6.8/9.8 percentage points, correcting the submitted
> 2.0/2.7).

### evidenza

Record 59 in `src/paper2_v1_amendments.jsonl` (`4.3b/prominenza_su_v2_sei_regole_su_sei_falliscono`);
soglia ricalibrata e dichiarata **prima** di leggere *P*^v2 nel record 58; strumento
`src/paper2_verdetto_v2.py` (67/67); ladder da `src/paper2_runner_4_2a.py`, ramo unitario e ramo FKP
a *k*=0–3 su 2000 realizzazioni per emisfero. I tre tagli in percentile sono nel §7.2 pubblicato.

### da rifare prima di applicare

1. Rileggere *P*^v1 e *P*^v2 dal record 59 e verificare *P*^v2 ≥ *P*^v1 in entrambi gli emisferi:
   è l'unica base di «does not reduce».
2. Controllare che «FKP-contaminated» non ricorra altrove nel PDF finale (nella bozza del 10
   settembre: solo in questi tre punti).
3. Se entra P1-11, allineare il nome dei voxel nel §7.2 a «lowest-coverage», che è quello usato qui."""

E6_OLD = "## P1-5 — il residuo beyond-two-point su v2: MISURATA"
E6_NEW = P1_10_SECTION + "\n\n" + E6_OLD

EDITS = [
    ("E1_intestazione", E1_OLD, E1_NEW),
    ("E2_stato_riga", E2_OLD, E2_NEW),
    ("E3_M26_accettato", E3_OLD, E3_NEW),
    ("E4_M26_controllo_5.6", E4_OLD, E4_NEW),
    ("E5_cambiamenti", E5_OLD, E5_NEW),
    ("E6_testo_P1-10", E6_OLD, E6_NEW),
]

# Marcatori che identificano la patch applicata: servono a verify e alla guardia di idempotenza.
MARKERS = [
    "## P1-10 — §8.1: il massimo a *k*=1 non viene dai voxel contaminati",
    "| **P1-10** | §8.1, didascalia Tab. 9",
    "**Accettato da MNRAS il 9 settembre 2026**",
    "**Controllo di 5.6, 11 settembre: la Fase 4 non richiede una nota su M26.**",
    "| 11 set 2026, Fase 5 | **P1-10**",
    "> **Due voci toccano un'affermazione fisica, e lo dichiarano:**",
]

BOM = b"\xef\xbb\xbf"


class PatchError(Exception):
    pass


# ---------------------------------------------------------------------------
# I/O che preserva BOM e fine riga
# ---------------------------------------------------------------------------

def decode(raw):
    bom = raw.startswith(BOM)
    body = raw[len(BOM):] if bom else raw
    text = body.decode("utf-8")  # solleva se non UTF-8: meglio che indovinare
    n_crlf = text.count("\r\n")
    n_lf = text.count("\n")
    if n_crlf and n_crlf != n_lf:
        raise PatchError(f"fine riga misti: {n_crlf} CRLF su {n_lf} LF; non scrivo")
    nl = "\r\n" if n_crlf else "\n"
    return text.replace("\r\n", "\n"), nl, bom


def encode(text, nl, bom):
    if "\r" in text:
        raise PatchError("CR spuri nel testo normalizzato")
    out = text.replace("\n", nl).encode("utf-8")
    return (BOM + out) if bom else out


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------------------
# Nucleo
# ---------------------------------------------------------------------------

def expected_line_delta():
    return sum(new.count("\n") - old.count("\n") for _, old, new in EDITS)


def patch_text(text):
    """Restituisce il testo patchato; solleva PatchError senza effetti se qualcosa non torna."""
    present = [m for m in MARKERS if m in text]
    if present:
        raise PatchError(f"patch già applicata (anche parzialmente): {len(present)} marcatori presenti, "
                         f"primo: {present[0][:60]!r}")
    for name, old, _ in EDITS:
        c = text.count(old)
        if c != 1:
            raise PatchError(f"{name}: ancora trovata {c} volte (attesa 1)")
    out = text
    for name, old, new in EDITS:
        out = out.replace(old, new, 1)
    # inversa: deve restituire l'originale byte per byte
    back = out
    for name, old, new in reversed(EDITS):
        c = back.count(new)
        if c != 1:
            raise PatchError(f"{name}: testo nuovo trovato {c} volte nel risultato (atteso 1)")
        back = back.replace(new, old, 1)
    if back != text:
        raise PatchError("l'inversa non restituisce l'originale: la patch toccherebbe altro")
    d = out.count("\n") - text.count("\n")
    if d != expected_line_delta():
        raise PatchError(f"delta righe {d} contro atteso {expected_line_delta()}")
    return out


def verify_text(text):
    """Controlli sul file patchato. Restituisce lista di (esito, messaggio)."""
    res = []
    for m in MARKERS:
        c = text.count(m)
        res.append((c == 1, f"marcatore presente una volta: {m[:55]!r} -> {c}"))
    for name, old, new in EDITS:
        c = text.count(new)
        res.append((c == 1, f"{name}: testo nuovo presente una volta -> {c}"))
    for name, old in (("E1", E1_OLD), ("E3", E3_OLD)):
        c = text.count(old)
        res.append((c == 0, f"{name}: testo sostituito assente -> {c}"))
    # ordine: P1-10 prima della voce P1-5 misurata, riga di stato dopo P1-9
    i10 = text.find(MARKERS[0]); i5 = text.find(E6_OLD)
    res.append((0 <= i10 < i5, "ordine: P1-10 precede '## P1-5 — ... MISURATA'"))
    i9r = text.find(E2_OLD); i10r = text.find(MARKERS[1])
    res.append((0 <= i9r < i10r, "ordine: riga di stato P1-10 dopo P1-9"))
    # l'inversa deve ridare un testo in cui ogni ancora torna una volta e nessun marcatore c'e'
    back = text
    ok_inv = True
    for name, old, new in reversed(EDITS):
        if back.count(new) != 1:
            ok_inv = False
            break
        back = back.replace(new, old, 1)
    if ok_inv:
        ok_inv = all(back.count(o) == 1 for _, o, _ in EDITS) and not any(m in back for m in MARKERS)
    res.append((ok_inv, "l'inversa ricostruisce un originale coerente"))
    return res


# ---------------------------------------------------------------------------
# Comandi
# ---------------------------------------------------------------------------

def cmd_dry_run(path):
    raw = open(path, "rb").read()
    text, nl, bom = decode(raw)
    out = patch_text(text)
    new_raw = encode(out, nl, bom)
    print(f"file:        {path}")
    print(f"fine riga:   {'CRLF' if nl == chr(13) + chr(10) else 'LF'}   BOM: {bom}")
    print(f"sha256 prima: {sha(raw)}")
    print(f"sha256 dopo:  {sha(new_raw)}")
    print(f"righe: {text.count(chr(10))} -> {out.count(chr(10))} (delta {out.count(chr(10)) - text.count(chr(10))}, atteso {expected_line_delta()})")
    for name, old, new in EDITS:
        print(f"  [ok] {name}: ancora unica, +{new.count(chr(10)) - old.count(chr(10))} righe")
    print("  [ok] inversa = originale byte per byte")
    print("DRY-RUN OK: nessuna scrittura")
    return 0


def atomic_write(path, data):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".p1_10_", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def cmd_apply(path):
    raw = open(path, "rb").read()
    text, nl, bom = decode(raw)
    out = patch_text(text)
    new_raw = encode(out, nl, bom)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = f"{path}.bak_p1_10_{stamp}"
    if os.path.exists(bak):
        raise PatchError(f"backup già esistente: {bak}")
    with open(bak, "xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    atomic_write(path, new_raw)
    # ESEGUIRE il risultato: rilettura dal disco e verify completo
    disk = open(path, "rb").read()
    if disk != new_raw:
        raise PatchError("il file su disco non coincide con quanto scritto")
    rc = cmd_verify(path, quiet=True)
    if rc != 0:
        raise PatchError("verify fallito dopo la scrittura; l'originale è nel backup")
    print(f"backup:  {bak}  sha256 {sha(raw)}")
    print(f"scritto: {path}  sha256 {sha(new_raw)}")
    print("APPLY OK: sei modifiche, verify superato sul file riletto")
    return 0


def cmd_verify(path, quiet=False):
    raw = open(path, "rb").read()
    text, nl, bom = decode(raw)
    res = verify_text(text)
    bad = [m for ok, m in res if not ok]
    if not quiet or bad:
        for ok, m in res:
            print(f"  [{'ok' if ok else 'FAIL'}] {m}")
    print(f"VERIFY: {len(res) - len(bad)}/{len(res)}" + ("" if not bad else "  -> FALLITO"))
    return 0 if not bad else 1


# ---------------------------------------------------------------------------
# Selftest: fixture sintetici costruiti dalle ancore, attese calcolate
# ---------------------------------------------------------------------------

def _fixture():
    parts = ["# titolo", "", E1_OLD, "", "| voce | x |", "|---|---|", E2_OLD,
             "| **P1-5** | y | z |", "", E3_OLD + " Le due cose", "",
             E4_OLD, "", "## Cambiamenti", "", E5_OLD, "| 10 set | w |", "",
             "## P1-9", "testo", "", E6_OLD, "coda", ""]
    return "\n".join(parts)


def selftest():
    import shutil
    checks = []

    def chk(cond, msg):
        checks.append((bool(cond), msg))

    base = _fixture()
    # 1. applicazione e inversa
    out = patch_text(base)
    chk(all(m in out for m in MARKERS), "tutti i marcatori presenti dopo la patch")
    chk(out.count("\n") - base.count("\n") == expected_line_delta(), "delta righe calcolato = misurato")
    chk(all(ok for ok, _ in verify_text(out)), "verify tutto verde sul fixture patchato")
    # 2. idempotenza
    try:
        patch_text(out); chk(False, "seconda applicazione rifiutata")
    except PatchError:
        chk(True, "seconda applicazione rifiutata")
    # 3. ancora mancante, per ciascuna delle sei
    for name, old, _ in EDITS:
        try:
            patch_text(base.replace(old, "XXX", 1)); chk(False, f"{name} mancante -> rifiuto")
        except PatchError:
            chk(True, f"{name} mancante -> rifiuto")
    # 4. ancora duplicata, per ciascuna delle sei
    for name, old, _ in EDITS:
        try:
            patch_text(base + "\n" + old + "\n"); chk(False, f"{name} duplicata -> rifiuto")
        except PatchError:
            chk(True, f"{name} duplicata -> rifiuto")
    # 5. patch parziale: un solo marcatore presente
    try:
        patch_text(base + "\n" + MARKERS[2] + "\n"); chk(False, "marcatore isolato -> rifiuto")
    except PatchError:
        chk(True, "marcatore isolato -> rifiuto")
    # 6. verify rileva un file con una modifica tolta
    broken = out.replace(E3_NEW, E3_OLD, 1)
    chk(not all(ok for ok, _ in verify_text(broken)), "verify rileva E3 mancante")
    # 7-10. su disco: LF, CRLF, BOM, dry-run non scrive, backup e sha
    tmpd = tempfile.mkdtemp(prefix="p1_10_selftest_")
    try:
        for label, nl, bom in (("LF", "\n", False), ("CRLF", "\r\n", True)):
            p = os.path.join(tmpd, f"m_{label}.md")
            raw0 = encode(base, nl, bom)
            open(p, "wb").write(raw0)
            m0 = (os.path.getmtime(p), sha(open(p, "rb").read()))
            _so = sys.stdout; sys.stdout = open(os.devnull, "w", encoding="utf-8")
            try:
                cmd_dry_run(p)
                m1 = (os.path.getmtime(p), sha(open(p, "rb").read()))
                rc = cmd_apply(p)
            finally:
                sys.stdout.close(); sys.stdout = _so
            chk(m0 == m1, f"{label}: dry-run non scrive")
            chk(rc == 0, f"{label}: apply rc=0")
            raw1 = open(p, "rb").read()
            chk(raw1.startswith(BOM) == bom, f"{label}: BOM preservato ({bom})")
            t1 = raw1[3:] if bom else raw1
            if nl == "\r\n":
                chk(t1.count(b"\n") == t1.count(b"\r\n"), f"{label}: nessun LF isolato")
            else:
                chk(b"\r" not in t1, f"{label}: nessun CR introdotto")
            baks = [f for f in os.listdir(tmpd) if f.startswith(f"m_{label}.md.bak_p1_10_")]
            chk(len(baks) == 1 and open(os.path.join(tmpd, baks[0]), "rb").read() == raw0,
                f"{label}: backup identico all'originale")
            # rifiuto su file già patchato, file intatto
            before = open(p, "rb").read()
            try:
                cmd_apply(p); chk(False, f"{label}: seconda apply rifiutata")
            except PatchError:
                chk(open(p, "rb").read() == before, f"{label}: seconda apply rifiutata, file intatto")
        # 11. fine riga misti -> rifiuto
        pm = os.path.join(tmpd, "misti.md")
        open(pm, "wb").write(encode(base, "\n", False).replace(b"\n", b"\r\n", 3))
        try:
            cmd_dry_run(pm); chk(False, "fine riga misti -> rifiuto")
        except PatchError:
            chk(True, "fine riga misti -> rifiuto")
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)

    n_ok = sum(ok for ok, _ in checks)
    for ok, m in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {m}")
    print(f"SELFTEST: {n_ok}/{len(checks)}")
    return 0 if n_ok == len(checks) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for c in ("dry-run", "apply", "verify"):
        s = sub.add_parser(c)
        s.add_argument("--file", required=True)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    try:
        if a.cmd == "selftest":
            return selftest()
        if not os.path.isfile(a.file):
            raise PatchError(f"file non trovato: {a.file}")
        return {"dry-run": cmd_dry_run, "apply": cmd_apply, "verify": cmd_verify}[a.cmd](a.file)
    except PatchError as e:
        print(f"RIFIUTO: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

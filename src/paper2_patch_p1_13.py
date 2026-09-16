# -*- coding: utf-8 -*-
"""
paper2_patch_p1_13.py -- inserisce P1-13 (Tabella 8 del Paper 1, quattro righe) in
modifiche_paper1.md e riscrive l'intestazione, che dichiara ancora due voci fisiche quando
ora sono quattro.

Quattro modifiche, atomiche, sul file gia' patchato da paper2_patch_p1_11.py:
  L1  intestazione: due voci fisiche -> quattro (P1-7, P1-10, P1-11, P1-12); il §7.2 non e'
      piu' "in verifica", P1-11 esiste
  L2  "Stato in una riga": riga P1-13, dopo P1-12
  L3  "Cambiamenti a questo documento": riga del 12 settembre
  L4  testo della voce P1-13, prima di "## P1-5 -- il residuo ... MISURATA" (in coda alle voci
      numerate, dove P1-12 ha lasciato il posto)

Uso:
  python paper2_patch_p1_13.py selftest
  python paper2_patch_p1_13.py dry-run --file <percorso>/modifiche_paper1.md
  python paper2_patch_p1_13.py apply   --file <percorso>/modifiche_paper1.md
  python paper2_patch_p1_13.py verify  --file <percorso>/modifiche_paper1.md

Dopo questa patch "paper2_patch_m26_limite.py verify" e "paper2_patch_p1_12.py verify"
falliscono PER COSTRUZIONE sull'intestazione (riscritta qui) e sulle righe di stato non piu'
adiacenti. Il verify di questo script controlla che P1-10, P1-11, P1-12 e la sezione M26
siano intatti.

Stesse garanzie degli altri patcher.
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

L1_OLD = (
    "> **Due voci toccano un'affermazione fisica, e lo dichiarano:** P1-7 (§9, i «fingers of God»)\n"
    "> e P1-10 (§8.1, l'origine del massimo a *k*=1). Nessuna voce tocca la misura del deficit, il\n"
    "> suo rango o la scomposizione spettrale. La lettura fisica del §7.2 — che fa nascere i voxel a\n"
    "> copertura minima dall'asimmetria di pesatura — è **in verifica** contro gli esiti di 4.2c e\n"
    "> 4.2b-4 su v2; se non regge, entra qui come P1-11.\n"
    "> *(Riscritto l'11 settembre: la versione precedente diceva che nessuna voce cambiava una\n"
    "> conclusione, e P1-7 e P1-10 la smentiscono.)*"
)
L1_NEW = (
    "> **Quattro voci toccano un'affermazione, e lo dichiarano:** P1-7 (§9, i «fingers of God»),\n"
    "> P1-10 (§8.1, l'origine del massimo a *k*=1), P1-11 (§7.2 e Tab. 12, l'origine dei voxel\n"
    "> estremi) e P1-12 (§8.2, il contrasto del test differenziale). Le prime tre sono correzioni\n"
    "> di **attribuzione causale**: la misura resta, cambia la causa che il testo le assegna. La\n"
    "> quarta corregge **tre numeri e un'etichetta**.\n"
    ">\n"
    "> **Nessuna voce tocca la misura del deficit, il suo rango o la scomposizione spettrale.** Il\n"
    "> 20.3 per cento, il rango 1/2001 e la ripartizione in persistenza restano quelli del\n"
    "> manoscritto. Cambia l'ampiezza di un sistematico propagato (P1-12: ±3.4 → ±11.9 per cento\n"
    "> del contrasto, cioè ±2.4 punti sul fiduciale), che resta dentro la banda dichiarata.\n"
    ">\n"
    "> *(Riscritto due volte: l'11 settembre, perché diceva che nessuna voce cambiava una\n"
    "> conclusione, e P1-7 e P1-10 la smentivano; il 12 settembre, perché ne dichiarava due quando\n"
    "> P1-11 e P1-12 le hanno portate a quattro.)*"
)

L2_OLD = ("| **P1-12** | §8.2, §7.4, §10 (iii), §11: il test differenziale accosta il contrasto di 240 "
          "configurazioni ai bias di 58 — **tre numeri e un'etichetta**, non una conclusione | **PRONTA** |")
L2_NEW = L2_OLD + "\n" + (
    "| **P1-13** | Tabella 8: **quattro righe** — AP, tiling, snapshot, ricostruzione a pesi unitari "
    "| **PRONTA** — la riga AP nella forma (B), senza numeri di Fase 3 |"
)

L3_OLD = ("| 12 set 2026 | **P1-11**: le attribuzioni sorelle di P1-10. Pesare i mock toglie **27 voxel "
          "patologici su 4048** (0.7 %, record da 4.2c) e **alza** la mediana di max δ da 27.80 a 28.47 "
          "volte DESI (4.2b-4), con il rango che resta 0/2000. Il §7.2 e la didascalia della Tab. 12 fanno "
          "nascere entrambi i fenomeni dalla pesatura: l'attribuzione cade, i numeri restano. **Quarta** "
          "voce che tocca un'affermazione, dopo P1-7, P1-10 e P1-12 |")
L3_NEW = L3_OLD + "\n" + (
    "| 12 set 2026 | **P1-13**, dalla voce 5.2: la Tab. 8 va corretta in **quattro** righe, non due. "
    "Oltre all'AP e al tiling, lo snapshot cita il valore centrale di un nullo (limite 97, 1.35 %) e "
    "il +309 porta un «∼1 %» che è di *N*, non di *D*, dove vale il **4.30 %** — prima riga della "
    "tabella sopra il 2 %. Riga AP nella forma **(B)**: la falsificazione, senza i numeri non "
    "pubblicati della Fase 3. **Intestazione riscritta**: le voci che toccano un'affermazione sono "
    "quattro |"
)

P1_13 = """## P1-13 — Tabella 8: quattro righe, non due

**Stato: PRONTA.** La riga «mock voxelisation weighting» **non è qui**: la aggiorna P1-9, e le due
voci vanno applicate insieme perché toccano la stessa tabella.

**Natura: tre correzioni di numero o di base, e una riga che si chiude.** Nessuna cambia la
conclusione del §7.4 — «none approaches the deficit» — ma una la mette alla prova, ed è detto
sotto.

### punto 1: riga «fiducial cosmology / AP distortion»

**Da:**

> fiducial cosmology / AP distortion | — | untested | open (Paper 2)

**A:**

> fiducial cosmology / AP distortion | scaling of the fiducial-to-true distance ratio *F* | the *F*
> required to erase the deficit lies 67–265× outside |*F*−1| ≤ 0.027 | falsified as sole cause;
> amplitude in preparation

**Perché in questa forma, e non con il numero.** La sensibilità è stata misurata — è l'esito della
Fase 3 del Paper 2 — ma quei numeri sono preregistrati e non ancora pubblicati, e metterli qui
legherebbe il Paper 1 a un manoscritto che può cambiare. La falsificazione, invece, non dipende da
nessun modello: il fattore che azzererebbe il deficit è fuori dal range fisico da due ordini di
grandezza, e non si muove se la Fase 5 rifinisce l'ampiezza. **Lo stato dice esplicitamente che
l'ampiezza è materia del lavoro in corso**, coerentemente col §7.3, che già chiama l'AP «the
subject of the next paper in this series».

### punto 2: riga «box tiling»

**Da:**

> box tiling (1 *h*⁻¹Gpc into 2 *h*⁻¹Gpc cube) | — | correlated-noise contribution, unquantified |
> open (minor)

**A:**

> box tiling (1 *h*⁻¹Gpc into 2 *h*⁻¹Gpc cube) | mock-mean shift under re-tiling, M26 §5.6 | −13 ± 20
> generators ⇒ < 73 (1.0 % of *D*) at 3σ | bounded

**Nota, da non mettere in tabella.** M26 misura anche un secondo effetto del tiling: un fattore 1.44
sulla varianza *per realizzazione*. Quello **non appartiene a questa tabella**, che raccoglie
spostamenti della media; tocca la dispersione, e quindi la significatività, non il valore del
deficit. Se un referee lo chiede, la risposta sta nel §5.6 di M26, non qui.

### punto 3: riga «snapshot vs. lightcone»

**Da:**

> ∂*N*_H1/∂*z* = −53 ± 112 per unit *z* ⇒ ∼13 loops (0.2 % of *D*) | sub-dominant

**A:**

> ∂*N*_H1/∂*z* = −53 ± 112 per unit *z* (consistent with zero) ⇒ < 97 loops (1.4 % of *D*) at 3σ
> over Δ*z* ≈ 0.25 | sub-dominant

Il 13 è il valore centrale di una misura compatibile con zero. Citarlo come effetto atteso, in una
colonna di limiti, sottostima il termine di un fattore sette. Il Δ*z* ≈ 0.25 è di M26 §7 (vi), non
ricostruito qui. Lo stato «sub-dominant» **resta vero**: 1.4 % è ancora ben sotto il deficit.

### punto 4: riga «observational weighting (data side)»

**Da:**

> unit-weight rebuild of DESI | +309 (∼1 %) | sub-dominant

**A:**

> unit-weight rebuild of DESI | +309, i.e. 1.1 % of *N*_H1 and 4.3 % of *D* | largest single entry;
> one-sided, data-side variant

**È la correzione più delicata della voce.** Ogni altra riga della tabella esprime l'effetto in
percentuale del **deficit**; questa lo esprime, senza dirlo, in percentuale del **conteggio**. Le
due basi differiscono di un fattore quattro, e con la base giusta questa è **la prima riga della
tabella a superare il 2 %**, quindi «sub-dominant» non è più la parola giusta.

Non cambia la conclusione del §7.4: il 4.3 % resta lontano dal deficit, e la variante è a un lato
solo — ricostruire DESI senza i suoi pesi non è un'ipotesi sul vero, è una verifica di robustezza.
Ma la tabella deve dire quanto vale, non farlo sembrare quattro volte più piccolo.

**La stessa ambiguità è in M26** (§5.3 e Tab. 1), dove però il testo è pubblicato: è una delle voci
della ricognizione per l'eventuale erratum, e le due correzioni vanno tenute coerenti.

### cosa resta vero

La conclusione del §7.3, «none approaches the deficit», regge su tutte e quattro le righe: il
massimo è il 4.3 %. Reggono anche le due righe sui surrogati di fibre, che vengono da M26 e non
sono toccate.

### evidenza

- **AP**: Fase 3 del Paper 2, `results/paper2/fase3_analisi.jsonl` (3.4). In tabella entra solo il
  rapporto fra il *F* richiesto e il range fisico, che è nel registro.
- **tiling**: `results/revision/rev1_r11_pilot.json`, −12.8 ± 20.1 su 100 mock; M26 §5.6.
- **snapshot**: M26 §7 (vi), −53 ± 112 per unità di *z*, Δ*z* ≈ 0.25.
- **+309**: M26 §5.3 e Tab. 1. Basi: *N*_H1 = 28 256, *D* = 7180.686 (bersagli del cancello,
  *n* = 2000).
- Denominatori e forme: voce 5.1 del Paper 2, `paper2_budget_5_1.md`, regole R2 e R3.

### da rifare prima di applicare

1. Rileggere dal registro di 3.4 i quattro d*F* richiesti e ricontrollare il rapporto 67–265 contro
   |*F*−1| ≤ 0.027, che è l'unico numero di Fase 3 che entra nel Paper 1.
2. Applicare **insieme a P1-9**, che aggiorna la quinta riga della stessa tabella.
3. Controllare che la didascalia della Tab. 8 — «the satellite-profile and mock-weighting rows are
   the paired measurements of this paper» — resti vera: le righe di questa voce vengono da M26 e
   dal Paper 2, non da misure appaiate del Paper 1."""

L4_OLD = "## P1-5 — il residuo beyond-two-point su v2: MISURATA"
L4_NEW = P1_13 + "\n\n" + L4_OLD

EDITS = [
    ("L1_intestazione", L1_OLD, L1_NEW),
    ("L2_stato_riga", L2_OLD, L2_NEW),
    ("L3_cambiamenti", L3_OLD, L3_NEW),
    ("L4_testo_P1-13", L4_OLD, L4_NEW),
]

MARKERS = [
    "> **Quattro voci toccano un'affermazione, e lo dichiarano:**",
    "| **P1-13** | Tabella 8: **quattro righe**",
    "| 12 set 2026 | **P1-13**, dalla voce 5.2:",
    "## P1-13 — Tabella 8: quattro righe, non due",
]

INTATTI = [
    "## P1-10 — §8.1: il massimo a *k*=1 non viene dai voxel contaminati",
    "## P1-11 — §7.2 e Tab. 12: i voxel estremi non nascono dalla pesatura",
    "## P1-12 — §8.2: il contrasto delle 240 configurazioni, i bias delle 58",
    "## M26 (MN-26-2100-P) — pubblicato;",
    "**M26 è pubblicato: la sola via rimasta è un erratum, e sarà uno solo.**",
    "## P1-9 — Δ*N*_H1 della ripesatura FKP: da 60 a 2000 realizzazioni",
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
    res.append((L1_OLD not in text, "L1: intestazione vecchia assente"))
    for m in INTATTI:
        c = text.count(m)
        res.append((c == 1, f"intatto: {m[:50]!r} -> {c}"))
    i12 = text.find(L2_OLD); i13 = text.find(MARKERS[1])
    res.append((0 <= i12 < i13, "ordine: riga di stato P1-13 dopo P1-12"))
    j13 = text.find(MARKERS[3]); j5 = text.find(L4_OLD)
    res.append((0 <= j13 < j5, "ordine: testo P1-13 prima di '## P1-5 ... MISURATA'"))
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
    fd, tmp = tempfile.mkstemp(prefix=".p1_13_", dir=d)
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
    bak = f"{path}.bak_p1_13_{stamp}"
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
    print("APPLY OK: quattro modifiche, verify superato sul file riletto")
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
    parts = ["# titolo", "", L1_OLD, "", "## Stato", "", L2_OLD, "", "## Cambiamenti", "", L3_OLD, ""]
    for m in INTATTI:
        parts += [m + " x", "corpo", ""]
    parts += [L4_OLD, "coda", ""]
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
        patch_text(base + "\n" + MARKERS[0] + "\n"); chk(False, "marcatore isolato -> rifiuto")
    except PatchError:
        chk(True, "marcatore isolato -> rifiuto")
    # 6. verify rileva un file con una modifica tolta
    broken = out.replace(L3_NEW, L3_OLD, 1)
    chk(not all(ok for ok, _ in verify_text(broken)), "verify rileva L3 mancante")
    # 7-10. su disco: LF, CRLF, BOM, dry-run non scrive, backup e sha
    tmpd = tempfile.mkdtemp(prefix="p1_13_selftest_")
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
            baks = [f for f in os.listdir(tmpd) if f.startswith(f"m_{label}.md.bak_p1_13_")]
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

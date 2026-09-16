# -*- coding: utf-8 -*-
"""
paper2_patch_p1_11.py -- inserisce P1-11 in modifiche_paper1.md: il §7.2 e la didascalia della
Tabella 12 attribuiscono alla pesatura unitaria dei mock due fenomeni che 4.2c e 4.2b-4 mostrano
indipendenti da essa.

Tre modifiche, atomiche, sul file gia' patchato da paper2_patch_p1_12.py:
  I1  "Stato in una riga": riga P1-11, inserita fra P1-10 e P1-12 (l'ordine numerico)

Dopo questa patch "paper2_patch_p1_12.py verify" fallisce PER COSTRUZIONE su H1: la riga di
stato di P1-12 resta intatta, ma non e' piu' adiacente a quella di P1-10, e H1 le controllava
insieme. Il verify di questo script controlla che P1-10, P1-12, M26 e l'intestazione siano
intatti, e che P1-11 preceda P1-12 sia nella tabella di stato sia nel corpo.
  I2  "Cambiamenti a questo documento": riga del 12 settembre
  I3  testo della voce P1-11, prima di "## P1-12 -- ..."

Uso:
  python paper2_patch_p1_11.py selftest
  python paper2_patch_p1_11.py dry-run --file <percorso>/modifiche_paper1.md
  python paper2_patch_p1_11.py apply   --file <percorso>/modifiche_paper1.md
  python paper2_patch_p1_11.py verify  --file <percorso>/modifiche_paper1.md

Stesse garanzie degli altri patcher: ancore uniche, rifiuto se gia' applicata, BOM e fine riga
preservati, inversa = originale byte per byte, scrittura atomica con backup, verify sul file
riletto dal disco.
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

I1_OLD = ("| **P1-12** | §8.2, §7.4, §10 (iii), §11: il test differenziale accosta il contrasto di 240 "
          "configurazioni ai bias di 58 — **tre numeri e un'etichetta**, non una conclusione | **PRONTA** |")
I1_NEW = (
    "| **P1-11** | §7.2 e didascalia Tab. 12: i ~4000 voxel e le punte di δ attribuiti alla "
    "pesatura unitaria dei mock — **smentito da 4.2c e 4.2b-4** | **PRONTA** |\n"
) + I1_OLD

I2_OLD = ("| 12 set 2026 | **P1-12**: ricalcolato il test differenziale del §8.2 dalle maschere A e B "
          "(riproduce il report al sesto decimale). Le 58 configurazioni del regime stanno tutte a "
          "σ = 0.3204, dove il contrasto vero è **23.9 %**, non il 36.9 % delle 240. Terza voce, dopo P1-7 "
          "e P1-10, che tocca un'affermazione; nasce dalla riga 9 del budget di 5.1 |")
I2_NEW = I2_OLD + "\n" + (
    "| 12 set 2026 | **P1-11**: le attribuzioni sorelle di P1-10. Pesare i mock toglie **27 voxel "
    "patologici su 4048** (0.7 %, record da 4.2c) e **alza** la mediana di max δ da 27.80 a 28.47 "
    "volte DESI (4.2b-4), con il rango che resta 0/2000. Il §7.2 e la didascalia della Tab. 12 fanno "
    "nascere entrambi i fenomeni dalla pesatura: l'attribuzione cade, i numeri restano. **Quarta** "
    "voce che tocca un'affermazione, dopo P1-7, P1-10 e P1-12 |"
)

P1_11 = """## P1-11 — §7.2 e Tab. 12: i voxel estremi non nascono dalla pesatura

**Stato: PRONTA.** Indipendente da P1-9 e da P1-10, ma **da applicare con P1-9**: quella riscrive
il Δ*N*_H1 dello stesso paragrafo, e le due frasi devono restare coerenti.

**Natura: correzione di attribuzione causale**, la stessa classe di P1-10 e nello stesso paragrafo
di origine. Le misure restano: ~4000 voxel, 1.3 % della maschera, densità 315 volte sotto la
mediana, un voxel dal bordo, 99.4 % entro due voxel, fattore 10³ sulla varianza di δ.

### perché

Il §7.2 costruisce una catena causale: la pesatura è asimmetrica → per i mock il peso non si
cancella → dove il campo dei random pesato è piccolo **il denominatore collassa** → di qui i ~4000
voxel con δ oltre il massimo di DESI. La didascalia della Tab. 12 chiude la stessa catena
altrove: le punte isolate di δ sono **«shot noise from unit-weight voxelisation»**. L'abstract la
riprende chiamando la voxelizzazione a peso unitario uno dei due difetti noti dei mock.

La Fase 4 ha voxelizzato i mock **con** *w*_FKP(*z*), su 2000 realizzazioni per emisfero. Se la
catena fosse giusta, i due fenomeni dovrebbero sparire o quasi. Non succede:

| | v1 (peso unitario) | v2 (pesato) | atteso se la causa fosse la pesatura |
|---|---|---|---|
| voxel patologici, NGC (4.2c) | 4048.21 ± 84.66 | **4021.1** | sotto 1349 |
| voxel patologici, SGC | 2811.56 ± 71.45 | **2795.1** | sotto 937 |
| mediana(max δ)/DESI, NGC (4.2b-4) | 27.80 | **28.47** | verso 1 |
| mediana(max δ)/DESI, SGC | 27.80 | **40.32** | verso 1 |
| rango di max δ di DESI fra i mock | 0/2000 | **0/2000** | dentro il 95 % centrale |

Appaiato contro il ramo unitario, il trattamento toglie **−27.09 ± 0.41** voxel su 4048 in NGC e
−16.45 ± 0.32 su 2812 in SGC: lo **0.7 %** e lo 0.6 %. E su max δ va nella direzione **opposta**:
i mock pesati hanno punte più estreme, non meno.

Le soglie erano dichiarate prima della misura (record 50, ricalibrate nel 58), e le regole sono
registrate come fallite: record 57 e 58 per 4.2b, il record di 4.2c per i voxel.

### cosa resta vero, e il testo conserva

Ogni numero del §7.2 e della Tab. 12. In particolare: i voxel estremi **esistono**, sono
**localizzati al bordo** e **non portano cicli** (100.1, 100.1 e 98.7 % dei loop sotto i tre tagli
in percentile) — che è il primo dei tre fatti del paragrafo e regge intatto. Restano anche il
fattore 10³ sulla varianza di δ e la scelta di riportare le statistiche a un punto sui soli voxel
puliti. Cambia da dove vengono quei voxel, non che ci siano né che siano innocui per *N*_H1.

### cosa il testo NON afferma

La causa vera. La co-localizzazione col bordo, già misurata nel paragrafo, la suggerisce; ma
stabilirla è materia del Paper 2, insieme al bordo degradato e al massimo geometrico di P1-10.
Nel Paper 1 basta dire che la pesatura non è la causa.

### punto 1: §7.2, la catena causale

**Da:**

> For the data the FKP weight largely cancels between the numerator and denominator of *δ*; for the
> mocks it does not, and where the weighted random field is small the denominator collapses. The
> effect is strongly localised: each mock realisation contains ∼4000 voxels (1.3 per cent of the
> mask) with *δ* exceeding the DESI maximum, whose median random-field density is a factor 315
> below the global median and whose median distance from the survey boundary is one voxel; 99.4 per
> cent of the lowest-percentile denominator voxels lie within two voxels of the boundary.

**A:**

> The effect is strongly localised: each mock realisation contains ∼4000 voxels (1.3 per cent of
> the mask) with *δ* exceeding the DESI maximum, whose median random-field density is a factor 315
> below the global median and whose median distance from the survey boundary is one voxel; 99.4 per
> cent of the lowest-percentile denominator voxels lie within two voxels of the boundary. These
> voxels are a property of the sparsely sampled boundary region rather than of the weighting:
> voxelizing the mock galaxies with *w*_FKP(*z*) over the full paired ensemble removes 0.7 per cent
> of them, and leaves their number, location and topological harmlessness unchanged.

### punto 2: didascalia della Tabella 12

**Da:**

> The mocks carry isolated high-*δ* spikes (shot noise from unit-weight voxelisation and diffuse
> satellite placement) that the data do not; the data concentrate more galaxies into shared cells.

**A:**

> The mocks carry isolated high-*δ* spikes that the data do not — a sampling property of the
> boundary region, not of the unit-weight voxelisation, which when corrected leaves them in place
> (Section 7.2); the data concentrate more galaxies into shared cells.

### punto 3: §9, la stessa attribuzione nel corpo

**Da:**

> …the mocks carry isolated shot-noise spikes that the data lack, while the data pack more galaxies
> into shared cells.

Il testo qui è già neutro sulla causa e **non va cambiato**. Va controllato che, dopo il punto 2, non
resti nel paragrafo un rimando che rimandi la causa alla pesatura.

### punto 4: abstract

**Da:**

> …paired-experiment bounds on the two known small-scale defects of the mocks (the uniform satellite
> profile and the unit-weight voxelisation).

**A:**

> …paired-experiment bounds on the two known small-scale asymmetries of the mocks (the uniform
> satellite profile and the unit-weight voxelisation).

Cambia una parola sola: «difetti» → «asimmetrie». La voxelizzazione a peso unitario **è** una
asimmetria fra i tre ingredienti, e il paragrafo la limita correttamente; chiamarla difetto
presuppone che produca i voxel estremi, che è ciò che cade.

### evidenza

- **4.2c**, voxel patologici: ⟨*n*_pat⟩^v2 = 4021.1 (NGC) e 2795.1 (SGC), contro soglie di
  fallimento a 2698.81 e 1874.37; appaiato −27.09 ± 0.41 e −16.45 ± 0.32. Riferimento v1
  4048.21 ± 84.66 e 2811.56 ± 71.45 su 2000 realizzazioni.
- **4.2b-4**, massimo di δ: rango 0/2000 su v1 e su v2; mediana(max δ)/DESI 27.80 → 28.47 (NGC) e
  → 40.32 (SGC). Record 58.
- Il primo dei tre fatti del §7.2 (i tagli in percentile, 100.1 / 100.1 / 98.7 %) è nel testo
  pubblicato e non viene toccato.

### da rifare prima di applicare

1. Rileggere dai record di 4.2c e 4.2b-4 i cinque numeri della tabella qui sopra, e confermare che
   4048.21 e 4021.1 siano lo stesso emisfero e lo stesso ensemble.
2. Verificare sul PDF finale che «unit-weight» e «shot noise from» non ricorrano altrove oltre ai
   quattro punti elencati.
3. Applicare **insieme a P1-9**, che riscrive il Δ*N*_H1 dello stesso paragrafo; e controllare che
   l'ordine dei capoversi del §7.2 resti leggibile una volta tolta la frase di apertura del punto 1
   (la frase sull'asimmetria dei tre ingredienti, che la precede, **resta** e regge il paragrafo)."""

I3_OLD = "## P1-12 — §8.2: il contrasto delle 240 configurazioni, i bias delle 58"
I3_NEW = P1_11 + "\n\n" + I3_OLD

EDITS = [
    ("I1_stato_riga", I1_OLD, I1_NEW),
    ("I2_cambiamenti", I2_OLD, I2_NEW),
    ("I3_testo_P1-11", I3_OLD, I3_NEW),
]

MARKERS = [
    "| **P1-11** | §7.2 e didascalia Tab. 12:",
    "| 12 set 2026 | **P1-11**:",
    "## P1-11 — §7.2 e Tab. 12: i voxel estremi non nascono dalla pesatura",
]

# Contenuti delle patch precedenti che questa NON tocca e che devono restare intatti
INTATTI = [
    "## P1-10 — §8.1: il massimo a *k*=1 non viene dai voxel contaminati",
    "## P1-12 — §8.2: il contrasto delle 240 configurazioni, i bias delle 58",
    "## M26 (MN-26-2100-P) — pubblicato;",
    "**M26 è pubblicato: la sola via rimasta è un erratum, e sarà uno solo.**",
    "limite nella forma dichiarata in 5.1, |Δ| + 3σ, vale **97 generatori",
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
    for m in INTATTI:
        c = text.count(m)
        res.append((c == 1, f"intatto: {m[:50]!r} -> {c}"))
    i11 = text.find(MARKERS[0]); i12 = text.find(I1_OLD)
    res.append((0 <= i11 < i12, "ordine: riga di stato P1-11 prima di P1-12"))
    j11 = text.find(MARKERS[2]); j12 = text.find(I3_OLD)
    res.append((0 <= j11 < j12, "ordine: testo P1-11 prima di P1-12"))
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
    fd, tmp = tempfile.mkstemp(prefix=".p1_11_", dir=d)
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
    bak = f"{path}.bak_p1_11_{stamp}"
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
    print("APPLY OK: tre modifiche, verify superato sul file riletto")
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
    parts = ["# titolo", "", INTATTI[5], "", INTATTI[0], "", INTATTI[2], "", INTATTI[3], "",
             INTATTI[4] + " x", "", "## Stato", "", I1_OLD, "", "## Cambiamenti", "", I2_OLD, "",
             I3_OLD, "corpo", ""]
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
        patch_text(base + "\n" + MARKERS[1] + "\n"); chk(False, "marcatore isolato -> rifiuto")
    except PatchError:
        chk(True, "marcatore isolato -> rifiuto")
    # 6. verify rileva un file con una modifica tolta
    broken = out.replace(I2_NEW, I2_OLD, 1)
    chk(not all(ok for ok, _ in verify_text(broken)), "verify rileva I2 mancante")
    # 7-10. su disco: LF, CRLF, BOM, dry-run non scrive, backup e sha
    tmpd = tempfile.mkdtemp(prefix="p1_11_selftest_")
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
            baks = [f for f in os.listdir(tmpd) if f.startswith(f"m_{label}.md.bak_p1_11_")]
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

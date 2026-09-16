# -*- coding: utf-8 -*-
"""
paper2_patch_p1_12.py -- inserisce P1-12 in modifiche_paper1.md e chiude la riga 9 in
paper2_budget_5_1.md.

DUE FILE, un solo comando. Le modifiche sono atomiche PER FILE: se uno dei due fallisce,
quel file non viene toccato e lo script lo dice; l'altro resta com'e'. Il verify controlla
entrambi.

modifiche_paper1.md (tre modifiche):
  H1  "Stato in una riga": riga P1-12 dopo P1-10
  H2  "Cambiamenti a questo documento": riga del 12 settembre
  H3  testo della voce P1-12, prima di "## P1-5 -- il residuo ... MISURATA"

paper2_budget_5_1.md (quattro modifiche):
  H4  intestazione: "dieci dichiarati; la riga 9 aspetta la sua fonte" -> undici dichiarati
  H5  R3: l'eccezione dichiarata per i sistematici di trasferimento
  H6  riga 9 della tabella: valore, fonte, denominatore, forma
  H7  sezione 4: il punto 1 diventa la verifica di P1-12, non piu' la ricerca della fonte

Uso:
  python paper2_patch_p1_12.py selftest
  python paper2_patch_p1_12.py dry-run --modifiche <percorso>/modifiche_paper1.md --budget <percorso>/paper2_budget_5_1.md
  python paper2_patch_p1_12.py apply   --modifiche ... --budget ...
  python paper2_patch_p1_12.py verify  --modifiche ... --budget ...

Stesse garanzie degli altri patcher: ancore uniche, rifiuto se gia' applicata, BOM e fine riga
preservati per file, inversa = originale byte per byte, scrittura atomica con backup, verify
sul file riletto dal disco.
"""
import argparse
import datetime as _dt
import hashlib
import os
import sys
import tempfile

# ---------------------------------------------------------------------------
# Testi -- modifiche_paper1.md
# ---------------------------------------------------------------------------

H1_OLD = ("| **P1-10** | §8.1, didascalia Tab. 9, §10 (vii): il massimo a *k*=1 attribuito ai voxel "
          "«FKP-contaminated» — **smentito da 4.3b** | **PRONTA** — dipende da P1-9 |")
H1_NEW = H1_OLD + "\n" + (
    "| **P1-12** | §8.2, §7.4, §10 (iii), §11: il test differenziale accosta il contrasto di 240 "
    "configurazioni ai bias di 58 — **tre numeri e un'etichetta**, non una conclusione | **PRONTA** |"
)

H2_OLD = ("| 11 set 2026, correzione | Snapshot: 84 → **97 generatori (1.35 % del deficit)**, per usare la "
          "forma di limite dichiarata in 5.1, \\|Δ\\| + 3σ, la stessa di NFW e tiling; la riga «M26 "
          "pubblicato» qui sotto resta come storia. Aggiunto alla ricognizione il −13 del tiling "
          "(−12.8 ± 20.1, limite 73 generatori, 1.02 %) |")
H2_NEW = H2_OLD + "\n" + (
    "| 12 set 2026 | **P1-12**: ricalcolato il test differenziale del §8.2 dalle maschere A e B "
    "(riproduce il report al sesto decimale). Le 58 configurazioni del regime stanno tutte a "
    "σ = 0.3204, dove il contrasto vero è **23.9 %**, non il 36.9 % delle 240. Terza voce, dopo P1-7 "
    "e P1-10, che tocca un'affermazione; nasce dalla riga 9 del budget di 5.1 |"
)

P1_12 = """## P1-12 — §8.2: il contrasto delle 240 configurazioni, i bias delle 58

**Stato: PRONTA.** Indipendente dalle altre voci. Tocca il §8.2 (tre punti), e il numero che
il §7.4, il §10 (iii) e il §11 ereditano da lì.

**Natura: correzione di tre numeri e di un'etichetta.** Il crollo della dipendenza dalla forma —
il risultato del test — resta intatto, e la conclusione del §7.4 pure.

### perché

Il test gira su **quattro valori di σ** e produce 240 configurazioni. Il regime di validità
w̄ ≥ 0.99 ne seleziona **58, tutte a σ = 0.3204**: alle altre tre σ nessuna configurazione qualifica.
E il contrasto vero fra i due campi cresce con σ.

| σ | Δ_vero (real 0 / real 1) | configurazioni con w̄ ≥ 0.99 |
|---|---|---:|
| 0.3204 | **23.96 / 23.79 %** | 58 su 60 |
| 0.5 | 34.73 / 35.52 % | 0 |
| 0.8 | 43.05 / 44.14 % | 0 |
| 1.2 | 45.24 / 44.84 % | 0 |

Il 36.9 % è la media su tutte e 240. Il testo lo accosta ai bias delle 58, che vivono a 23.9 %.
Da qui i tre numeri:

1. **«a true loop-density contrast of 36.9 per cent, 58 configurations»** — nel regime il contrasto
   vero è **23.9 %**;
2. **«of the true 36.9 per cent it measures 33.5, a relative −9 per cent»** — il 33.5 è 36.9 − 3.4,
   cioè il contrasto di un insieme meno il bias dell'altro. Nel regime: **23.9 → 20.5, relativo
   −14.3 %**. La compressione è più forte, non più debole; il verso non cambia;
3. **«±3.4 per cent of the measured contrast»** — il 3.4 è la **media** del bias, non la sua
   dispersione, ed è in punti percentuali di un contrasto del 23.9 %. In termini relativi, nel
   regime: media −14.3 %, **dispersione fra configurazioni 11.9 %**. Applicato al 20.3 fiduciale, il
   testo dà ±0.69 pp; la dispersione misurata dà **±2.4 pp**. Anche la lettura in punti percentuali
   non regge: 20.3 − 3.4 = 16.9 cade fuori dalla banda che il §7.4 dichiara di rispettare.

**Forma adottata (a), decisa il 12 settembre:** il termine entra come **banda di dispersione**,
±11.9 % relativo, e la compressione media si dichiara come **verso** senza correggerla. Scartata
(b), che avrebbe corretto il 20.3 per il −14.3 %: sarebbe una sottrazione a 1.2σ, vietata dalla
regola R3 del budget; sposterebbe un valore centrale presente nell'abstract, nel freeze e in M26;
e userebbe come stabilito proprio il trasferimento che il testo dichiara incerto («if the factor
transfers», con i due caveat che seguono). La direzione è quella comoda — la compressione gonfia
il deficit — e questo chiede uno standard più alto, non più basso.

### cosa resta vero, e il testo conserva

Il crollo della dipendenza dalla forma: escursione differenziale **0.019** contro **0.158**
assoluta, fattore **8.3**. Il bias assoluto −19.5 %. L'intervallo per forma da −8 a −24 %. La
conclusione del §7.4: con ±2.4 pp il fiduciale dà 17.9–22.7, dentro la banda.

### punto 1: §8.2, il capoverso del test

**Da:**

> A dedicated test — two Gaussian fields sharing the same white noise with spectral slopes −1.5 and
> −2.3, a true loop-density contrast of 36.9 per cent, 58 configurations in the *w̄* ≥ 0.99 regime —
> shows the shape dependence collapsing by a factor of eight: the differential bias is −3.4 ± 2.8
> per cent with a shape excursion of 0.019, against an absolute bias of −19.5 per cent with
> excursion 0.158.

**A:**

> A dedicated test — two Gaussian fields sharing the same white noise with spectral slopes −1.5 and
> −2.3, over four smoothing scales and 240 configurations — shows the shape dependence collapsing
> by a factor of eight: the differential bias has a shape excursion of 0.019, against an absolute
> bias of −19.5 per cent with excursion 0.158. Only the canonical scale qualifies under *w̄* ≥ 0.99,
> and the 58 configurations in that regime carry a true loop-density contrast of 23.9 per cent;
> across them the differential bias is −3.4 ± 2.8 percentage points of that contrast, that is
> −14.3 per cent of it with a dispersion of 11.9 per cent across mask geometries.

### punto 2: §8.2, la compressione del contrasto

**Da:**

> The criterion survives in this weaker, honest form: *w̄* ≳ 0.99 is a condition for reliable
> differential data–mock comparison, not for absolute generator counts, and it carries a residual
> mask systematic of ±3.4 per cent of the measured contrast, which we propagate to the band of
> Section 7.4. The same test shows the mask compressing contrast: of the true 36.9 per cent it
> measures 33.5, a relative −9 per cent; if the factor transfers, the measured 20.3 per cent deficit
> slightly understates the true one — one more systematic pointing away from a mundane resolution.

**A:**

> The criterion survives in this weaker, honest form: *w̄* ≳ 0.99 is a condition for reliable
> differential data–mock comparison, not for absolute generator counts, and it carries a residual
> mask systematic of ±11.9 per cent of the measured contrast — the dispersion of the differential
> bias across mask geometries, which we propagate to the band of Section 7.4. The same test shows
> the mask compressing contrast: in this regime it measures 20.5 per cent of a true 23.9, a relative
> −14.3 per cent. We quote the direction rather than a correction: with five synthetic shapes and
> two realizations the compression is a 1.2σ effect, and if the factor transfers at all, the
> measured 20.3 per cent deficit understates the true one — one more systematic pointing away from
> a mundane resolution.

### punto 3: didascalia della Figura 6

**Da:**

> …while the differential bias between two fields observed through the same mask (black) is
> −3.4 ± 2.8 per cent with a shape excursion eight times smaller.

**A:**

> …while the differential bias between two fields observed through the same mask (black) is
> −3.4 ± 2.8 percentage points of a 23.9 per cent true contrast, with a shape excursion eight times
> smaller.

### punto 4: i tre luoghi che ereditano il numero

Ovunque compaia «±3.4 per cent» come sistematico **propagato**, va sostituito con **±11.9 per
cent**, che su 20.3 vale ±2.4 punti percentuali:

- **§7.4**: «the ±3.4 per cent residual mask systematic of Section 8.2, applied to the fiducial
  20.3, both fall inside it» → ±11.9, cioè 17.9–22.7, che sta dentro la banda come prima;
- **§10 (iii)**: «it does control the differential bias between two fields behind the same mask, to
  ±3.4 per cent» → ±11.9 per cent of the contrast;
- **§11**: «with a ±3.4 per cent residual propagated to the error budget» → ±11.9 per cent.

Il ±3.4 **resta** nel §8.2 e nella Fig. 6, dove è corretto, purché detto in punti percentuali del
23.9.

### evidenza

Ricalcolo dalle maschere, indipendente dal report: `results/paper1/n8_masks_128.jsonl`
(`8dbaa60580e6…`) e `n8b_masks_128_B.jsonl` (`bd7a8fd91f02…`), con la stessa ricombinazione di
`src/paper1_rev_n8b_differential.py` (`aba90e159ec2…`). Riproduce `n8b_report_128.json`
(`fd70fdc659dc…`) al sesto decimale: 240 configurazioni, 58 nel regime, differenziale −0.034216,
deviazione standard 0.028497.

Il ±2.8 è la **deviazione standard fra le 58 configurazioni** (`bd99.std(ddof=1)` nel codice), non
una SEM. La SEM varrebbe 0.37 pp, ma non sarebbe definita in modo sensato: le 58 configurazioni
vengono da **due sole realizzazioni** (29 + 29) viste attraverso forme e spessori diversi, e per un
sistematico di trasferimento fra geometrie la dispersione è la quantità pertinente.

Provenienza verificata: `git status` pulito; l'unica modifica dopo il run del 26 luglio è `88f6bad`
(28 agosto), che parafrasa le citazioni dei referee nel docstring di `paper1_rev_n8_masks.py` e non
tocca la logica.

### da rifare prima di applicare

1. Rileggere i quattro Δ_vero per σ dalle righe `__full__` dei due JSONL, e verificare che nel
   regime non compaia nessuna σ diversa da 0.3204.
2. Verificare sul PDF finale che «3.4» non ricorra altrove oltre ai sei punti qui elencati.
3. Se il §7.4 viene toccato anche da P1-8 (la banda 17–29), coordinare le due voci: qui cambia
   l'ampiezza del residuo, là gli estremi della banda."""

H3_OLD = "## P1-5 — il residuo beyond-two-point su v2: MISURATA"
H3_NEW = P1_12 + "\n\n" + H3_OLD

# ---------------------------------------------------------------------------
# Testi -- paper2_budget_5_1.md
# ---------------------------------------------------------------------------

H4_OLD = "termine. **Undici termini, dieci dichiarati; la riga 9 aspetta la sua fonte.**"
H4_NEW = ("termine. **Undici termini, tutti dichiarati** (la riga 9 chiusa il 12 settembre, con la\n"
          "voce P1-12 sul Paper 1).")

H5_OLD = ("**R4 — «conservativo» non si usa.** Per un limite un σ più largo è prudente. Per una misura la\n"
          "quadratura, al posto della SEM appaiata, sottostima l'effetto e non è prudente affatto. La parola\n"
          "dice cose opposte nei due casi.")
H5_NEW = H5_OLD + "\n\n" + (
    "**R3-bis — eccezione dichiarata, per i sistematici di trasferimento.** Un termine misurato su un\n"
    "campione di *geometrie* (non di realizzazioni) e trasferito a una geometria nuova porta come\n"
    "incertezza la **dispersione fra le geometrie provate**, non la SEM e non il limite |Δ| + 3σ: la\n"
    "SEM direbbe quanto è nota la media delle forme provate, non quanto quella media predice la\n"
    "prossima. Vale oggi per la sola riga 9. Il limite |Δ| + 3σ darebbe lì il 50 % relativo, che\n"
    "inghiottirebbe ogni altro termine senza misurare nulla di più."
)

H6_OLD = ("| 9 | residuo di maschera | −3.4 ± 2.8 % **del contrasto** (relativo) | Paper 1 §8.2, 58 configurazioni "
          "| **DA DICHIARARE**: il 2.8 è dispersione fra configurazioni o SEM? | pubblicato come ±3.4 simmetrico, "
          "cioè **segno perso** | — |")
H6_NEW = ("| 9 | residuo di maschera | **−14.3 % ± 11.9 %** del contrasto (relativo); in punti percentuali del "
          "contrasto vero del regime, −3.4 ± 2.8 su 23.9 | `results/paper1/n8_masks_128.jsonl` e "
          "`n8b_masks_128_B.jsonl`, ricalcolo indipendente (P1-12) | **dispersione fra le 58 geometrie** "
          "(`std(ddof=1)`), non SEM: R3-bis. Due sole realizzazioni, 29 + 29 | **banda ±11.9 % relativo**, "
          "cioè **±2.4 pp** sul 20.3 fiduciale; la compressione media si dichiara come **verso**, non si "
          "sottrae (forma (a), decisa il 12 set; scartata (b), sottrazione a 1.2σ) | ±2.4 pp *derivato* |")

H7_OLD = "1. **Riga 9**: leggere nel codice del Paper 1 che cosa è il 2.8, e dichiararne il denominatore."
H7_NEW = ("1. **Riga 9 — chiusa, ma da verificare con P1-12**: il ±11.9 % e il −14.3 % vanno riletti dal\n"
          "   ricalcolo, e il §8.2 del Paper 1 va corretto insieme (P1-12), altrimenti il budget e il\n"
          "   manoscritto porterebbero due numeri diversi per lo stesso termine.")

EDITS_MOD = [
    ("H1_stato_riga", H1_OLD, H1_NEW),
    ("H2_cambiamenti", H2_OLD, H2_NEW),
    ("H3_testo_P1-12", H3_OLD, H3_NEW),
]
EDITS_BUD = [
    ("H4_intestazione", H4_OLD, H4_NEW),
    ("H5_R3bis", H5_OLD, H5_NEW),
    ("H6_riga9", H6_OLD, H6_NEW),
    ("H7_sezione4", H7_OLD, H7_NEW),
]

MARKERS_MOD = [
    "| **P1-12** | §8.2, §7.4, §10 (iii), §11:",
    "| 12 set 2026 | **P1-12**:",
    "## P1-12 — §8.2: il contrasto delle 240 configurazioni, i bias delle 58",
]
MARKERS_BUD = [
    "**Undici termini, tutti dichiarati**",
    "**R3-bis — eccezione dichiarata, per i sistematici di trasferimento.**",
    "| 9 | residuo di maschera | **−14.3 % ± 11.9 %**",
    "1. **Riga 9 — chiusa, ma da verificare con P1-12**",
]

# Contenuti delle patch precedenti che questa NON tocca e che devono restare intatti
INTATTI_MOD = [
    "## P1-10 — §8.1: il massimo a *k*=1 non viene dai voxel contaminati",
    "## M26 (MN-26-2100-P) — pubblicato;",
    "**M26 è pubblicato: la sola via rimasta è un erratum, e sarà uno solo.**",
    "- **il tiling, §5.6.** «the mock mean moves by −13 generators»",
    "limite nella forma dichiarata in 5.1, |Δ| + 3σ, vale **97 generatori",
]

FILES = [("modifiche", EDITS_MOD, MARKERS_MOD, INTATTI_MOD),
         ("budget", EDITS_BUD, MARKERS_BUD, [])]

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



# ---------------------------------------------------------------------------
# Nucleo -- generico su (edits, markers, intatti)
# ---------------------------------------------------------------------------

def delta_atteso(edits):
    return sum(new.count("\n") - old.count("\n") for _, old, new in edits)


def patch_text(text, edits, markers, etichetta):
    present = [m for m in markers if m in text]
    if present:
        raise PatchError(f"{etichetta}: patch già applicata (anche parzialmente): "
                         f"{len(present)} marcatori presenti, primo {present[0][:60]!r}")
    for name, old, _ in edits:
        c = text.count(old)
        if c != 1:
            raise PatchError(f"{etichetta}/{name}: ancora trovata {c} volte (attesa 1)")
    out = text
    for name, old, new in edits:
        out = out.replace(old, new, 1)
    back = out
    for name, old, new in reversed(edits):
        c = back.count(new)
        if c != 1:
            raise PatchError(f"{etichetta}/{name}: testo nuovo trovato {c} volte nel risultato")
        back = back.replace(new, old, 1)
    if back != text:
        raise PatchError(f"{etichetta}: l'inversa non restituisce l'originale: la patch toccherebbe altro")
    d = out.count("\n") - text.count("\n")
    if d != delta_atteso(edits):
        raise PatchError(f"{etichetta}: delta righe {d} contro atteso {delta_atteso(edits)}")
    return out


def verify_text(text, edits, markers, intatti):
    res = []
    for m in markers:
        c = text.count(m)
        res.append((c == 1, f"marcatore presente una volta: {m[:55]!r} -> {c}"))
    for name, old, new in edits:
        c = text.count(new)
        res.append((c == 1, f"{name}: testo nuovo presente una volta -> {c}"))
    for name, old, new in edits:
        if old not in new:  # sostituzioni vere, non inserimenti
            res.append((text.count(old) == 0, f"{name}: testo sostituito assente -> {text.count(old)}"))
    for m in intatti:
        c = text.count(m)
        res.append((c == 1, f"intatto: {m[:50]!r} -> {c}"))
    back = text
    ok_inv = True
    for name, old, new in reversed(edits):
        if back.count(new) != 1:
            ok_inv = False
            break
        back = back.replace(new, old, 1)
    if ok_inv:
        ok_inv = all(back.count(o) == 1 for _, o, _ in edits) and not any(m in back for m in markers)
    res.append((ok_inv, "l'inversa ricostruisce un originale coerente"))
    return res


def _blocchi(percorsi):
    """[(etichetta, percorso, edits, markers, intatti)] per i file passati."""
    out = []
    for (et, edits, markers, intatti) in FILES:
        p = percorsi.get(et)
        if p is not None:
            out.append((et, p, edits, markers, intatti))
    if not out:
        raise PatchError("nessun file indicato")
    return out


# ---------------------------------------------------------------------------
# Comandi
# ---------------------------------------------------------------------------

def cmd_dry_run(percorsi):
    for et, p, edits, markers, _ in _blocchi(percorsi):
        if not os.path.isfile(p):
            raise PatchError(f"file non trovato: {p}")
        raw = open(p, "rb").read()
        text, nl, bom = decode(raw)
        out = patch_text(text, edits, markers, et)
        new_raw = encode(out, nl, bom)
        print(f"\n--- {et}: {p}")
        print(f"  fine riga:    {'CRLF' if nl == chr(13) + chr(10) else 'LF'}   BOM: {bom}")
        print(f"  sha256 prima: {sha(raw)}")
        print(f"  sha256 dopo:  {sha(new_raw)}")
        print(f"  righe: {text.count(chr(10))} -> {out.count(chr(10))} "
              f"(delta {out.count(chr(10)) - text.count(chr(10))}, atteso {delta_atteso(edits)})")
        for name, old, new in edits:
            print(f"    [ok] {name}: ancora unica, +{new.count(chr(10)) - old.count(chr(10))} righe")
        print("    [ok] inversa = originale byte per byte")
    print("\nDRY-RUN OK: nessuna scrittura")
    return 0


def cmd_apply(percorsi):
    blocchi = _blocchi(percorsi)
    # prima si valida TUTTO, poi si scrive: un file rotto non lascia l'altro a metà
    pronti = []
    for et, p, edits, markers, intatti in blocchi:
        if not os.path.isfile(p):
            raise PatchError(f"file non trovato: {p}")
        raw = open(p, "rb").read()
        text, nl, bom = decode(raw)
        out = patch_text(text, edits, markers, et)
        pronti.append((et, p, raw, encode(out, nl, bom), edits, markers, intatti))
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scritti = []
    for et, p, raw, new_raw, edits, markers, intatti in pronti:
        bak = f"{p}.bak_p1_12_{stamp}"
        if os.path.exists(bak):
            raise PatchError(f"backup già esistente: {bak}")
        with open(bak, "xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        atomic_write(p, new_raw)
        disk = open(p, "rb").read()
        if disk != new_raw:
            raise PatchError(f"{et}: il file su disco non coincide con quanto scritto")
        text, _, _ = decode(disk)
        bad = [m for ok, m in verify_text(text, edits, markers, intatti) if not ok]
        if bad:
            raise PatchError(f"{et}: verify fallito dopo la scrittura ({bad[0]}); l'originale è in {bak}")
        scritti.append((et, p, bak, sha(raw), sha(new_raw)))
    for et, p, bak, s0, s1 in scritti:
        print(f"\n--- {et}")
        print(f"  backup:  {bak}  sha256 {s0}")
        print(f"  scritto: {p}  sha256 {s1}")
    print(f"\nAPPLY OK: {sum(len(b[2]) for b in blocchi)} modifiche su {len(blocchi)} file, "
          f"verify superato sui file riletti")
    return 0


def cmd_verify(percorsi, quiet=False):
    tot = bad_tot = 0
    for et, p, edits, markers, intatti in _blocchi(percorsi):
        if not os.path.isfile(p):
            raise PatchError(f"file non trovato: {p}")
        text, _, _ = decode(open(p, "rb").read())
        res = verify_text(text, edits, markers, intatti)
        bad = [m for ok, m in res if not ok]
        if not quiet or bad:
            print(f"\n--- {et}: {p}")
            for ok, m in res:
                print(f"  [{'ok' if ok else 'FAIL'}] {m}")
        tot += len(res)
        bad_tot += len(bad)
    print(f"\nVERIFY: {tot - bad_tot}/{tot}" + ("" if not bad_tot else "  -> FALLITO"))
    return 0 if not bad_tot else 1


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _fixture(edits, intatti):
    parts = ["# titolo", ""]
    for m in intatti:
        parts += [m + " x", ""]
    for _, old, _ in edits:
        parts += [old, ""]
    return "\n".join(parts)


def selftest():
    import shutil
    checks = []

    def chk(c, m):
        checks.append((bool(c), m))

    for et, edits, markers, intatti in FILES:
        base = _fixture(edits, intatti)
        out = patch_text(base, edits, markers, et)
        chk(all(m in out for m in markers), f"{et}: tutti i marcatori presenti dopo la patch")
        chk(out.count("\n") - base.count("\n") == delta_atteso(edits), f"{et}: delta righe calcolato = misurato")
        chk(all(ok for ok, _ in verify_text(out, edits, markers, intatti)), f"{et}: verify verde sul fixture")
        try:
            patch_text(out, edits, markers, et)
            chk(False, f"{et}: seconda applicazione rifiutata")
        except PatchError:
            chk(True, f"{et}: seconda applicazione rifiutata")
        for name, old, _ in edits:
            try:
                patch_text(base.replace(old, "XXX", 1), edits, markers, et)
                chk(False, f"{et}/{name} mancante -> rifiuto")
            except PatchError:
                chk(True, f"{et}/{name} mancante -> rifiuto")
            try:
                patch_text(base + "\n" + old + "\n", edits, markers, et)
                chk(False, f"{et}/{name} duplicata -> rifiuto")
            except PatchError:
                chk(True, f"{et}/{name} duplicata -> rifiuto")
        try:
            patch_text(base + "\n" + markers[0] + "\n", edits, markers, et)
            chk(False, f"{et}: marcatore isolato -> rifiuto")
        except PatchError:
            chk(True, f"{et}: marcatore isolato -> rifiuto")
        rotto = out.replace(edits[0][2], edits[0][1], 1)
        chk(not all(ok for ok, _ in verify_text(rotto, edits, markers, intatti)),
            f"{et}: verify rileva la prima modifica mancante")

    tmp = tempfile.mkdtemp(prefix="p1_12_selftest_")
    _so = sys.stdout
    try:
        for label, nl, bom in (("LF", "\n", False), ("CRLF", "\r\n", True)):
            perc, raws = {}, {}
            for et, edits, markers, intatti in FILES:
                p = os.path.join(tmp, f"{et}_{label}.md")
                raws[et] = encode(_fixture(edits, intatti), nl, bom)
                open(p, "wb").write(raws[et])
                perc[et] = p
            m0 = {et: sha(open(p, "rb").read()) for et, p in perc.items()}
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
            try:
                cmd_dry_run(perc)
                m1 = {et: sha(open(p, "rb").read()) for et, p in perc.items()}
                rc = cmd_apply(perc)
            finally:
                sys.stdout.close()
                sys.stdout = _so
            chk(m0 == m1, f"{label}: dry-run non scrive nessuno dei due file")
            chk(rc == 0, f"{label}: apply rc=0 su due file")
            for et, p in perc.items():
                raw1 = open(p, "rb").read()
                chk(raw1.startswith(BOM) == bom, f"{label}/{et}: BOM preservato")
                t1 = raw1[3:] if bom else raw1
                if nl == "\r\n":
                    chk(t1.count(b"\n") == t1.count(b"\r\n"), f"{label}/{et}: nessun LF isolato")
                else:
                    chk(b"\r" not in t1, f"{label}/{et}: nessun CR introdotto")
                baks = [f for f in os.listdir(tmp) if f.startswith(f"{et}_{label}.md.bak_p1_12_")]
                chk(len(baks) == 1 and open(os.path.join(tmp, baks[0]), "rb").read() == raws[et],
                    f"{label}/{et}: backup identico all'originale")
            prima = {et: open(p, "rb").read() for et, p in perc.items()}
            try:
                cmd_apply(perc)
                chk(False, f"{label}: seconda apply rifiutata")
            except PatchError:
                chk(all(open(p, "rb").read() == prima[et] for et, p in perc.items()),
                    f"{label}: seconda apply rifiutata, entrambi i file intatti")
        # un file valido e uno no: nessuno dei due viene scritto
        pv = os.path.join(tmp, "mod_ok.md")
        pb = os.path.join(tmp, "bud_rotto.md")
        open(pv, "wb").write(encode(_fixture(EDITS_MOD, INTATTI_MOD), "\n", False))
        open(pb, "wb").write(encode(_fixture(EDITS_BUD, []).replace(H6_OLD, "XXX", 1), "\n", False))
        s0 = (sha(open(pv, "rb").read()), sha(open(pb, "rb").read()))
        try:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
            try:
                cmd_apply({"modifiche": pv, "budget": pb})
            finally:
                sys.stdout.close()
                sys.stdout = _so
            chk(False, "un file rotto -> nessuna scrittura")
        except PatchError:
            s1 = (sha(open(pv, "rb").read()), sha(open(pb, "rb").read()))
            chk(s0 == s1, "un file rotto -> nessuna scrittura, entrambi intatti")
            chk(not [f for f in os.listdir(tmp) if f.startswith("mod_ok.md.bak")], "nessun backup creato")
        # un solo file passato: si patcha solo quello
        p1 = os.path.join(tmp, "solo_mod.md")
        open(p1, "wb").write(encode(_fixture(EDITS_MOD, INTATTI_MOD), "\n", False))
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        try:
            rc = cmd_apply({"modifiche": p1})
        finally:
            sys.stdout.close()
            sys.stdout = _so
        chk(rc == 0 and all(m in open(p1, encoding="utf-8").read() for m in MARKERS_MOD),
            "un solo file passato: patchato quello, senza l'altro")
    finally:
        sys.stdout = _so
        shutil.rmtree(tmp, ignore_errors=True)

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
        s.add_argument("--modifiche", default=None, help="percorso di modifiche_paper1.md")
        s.add_argument("--budget", default=None, help="percorso di paper2_budget_5_1.md")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    try:
        if a.cmd == "selftest":
            return selftest()
        perc = {k: v for k, v in (("modifiche", a.modifiche), ("budget", a.budget)) if v}
        return {"dry-run": cmd_dry_run, "apply": cmd_apply, "verify": cmd_verify}[a.cmd](perc)
    except PatchError as e:
        print(f"RIFIUTO: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

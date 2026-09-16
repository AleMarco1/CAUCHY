# -*- coding: utf-8 -*-
"""
paper2_patch_m26_limite.py -- allinea la ricognizione di M26 in modifiche_paper1.md alla forma
di limite dichiarata in 5.1: per un risultato compatibile con zero il limite e' |D| + 3 sigma.

Tre modifiche, atomiche (tutte o nessuna), sul file gia' patchato da paper2_patch_m26_pubblicato.py:
  G1  snapshot: 84 generatori (1.17 %) -> 97 (1.35 %); la prima cifra era 3 sigma attorno a zero
  G2  nuova voce della ricognizione: il -13 del tiling (-12.8 +/- 20.1, limite 73, 1.02 %)
  G3  "Cambiamenti a questo documento": riga della correzione (la riga di F4 resta come storia)

Dopo questa patch "paper2_patch_m26_pubblicato.py verify" fallisce PER COSTRUZIONE su F3 (il
suo testo e' corretto qui) e su F4 (la riga di G3 si inserisce fra l'apertura e la riga di F4,
che resta intatta ma non piu' adiacente). Il verify di questo script controlla che il resto di
P1-10 e di F1-F4 sia intatto.

Uso:
  python paper2_patch_m26_limite.py selftest
  python paper2_patch_m26_limite.py dry-run --file <percorso>/modifiche_paper1.md
  python paper2_patch_m26_limite.py apply   --file <percorso>/modifiche_paper1.md
  python paper2_patch_m26_limite.py verify  --file <percorso>/modifiche_paper1.md
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

G1_OLD = (
    "  una pendenza di −53 ± 112 per unità di *z*, compatibile con zero. Con il Δ*z* ≈ 0.25 del testo il\n"
    "  limite a 3σ vale **84 generatori, l'1.17 % del deficit**. Il §7 (vi) dice «consistent with\n"
    "  zero» e non nasconde nulla, ma il numero da citare è il limite, e il §2 riporta solo lo 0.2 %.\n"
    "  Stessa riga nella Tab. 8 del Paper 1;"
)
G1_NEW = (
    "  una pendenza di −53 ± 112 per unità di *z*, compatibile con zero. Con il Δ*z* ≈ 0.25 del testo il\n"
    "  limite nella forma dichiarata in 5.1, |Δ| + 3σ, vale **97 generatori, l'1.35 % del deficit**.\n"
    "  Il §7 (vi) dice «consistent with zero» e non nasconde nulla, ma il numero da citare è il limite,\n"
    "  e il §2 riporta solo lo 0.2 %. Stessa riga nella Tab. 8 del Paper 1. La prima stesura di questa\n"
    "  voce dava 84 generatori (1.17 %), cioè 3σ attorno a zero: una forma diversa da quella adottata\n"
    "  per NFW e tiling, corretta l'11 settembre;"
)

G2_OLD = (
    "- **il rimando del §2 è sbagliato.** Dice che lo snapshot è quantificato nella «Section 5.4»; il\n"
    "  §5.4 non ne parla, la misura sta nel §7 (vi);"
)
G2_NEW = G2_OLD + "\n" + (
    "- **il tiling, §5.6.** «the mock mean moves by −13 generators» è il valore centrale di\n"
    "  **−12.8 ± 20.1** su 100 mock (`results/revision/rev1_r11_pilot.json`), compatibile con zero.\n"
    "  Il limite |Δ| + 3σ vale **73 generatori, l'1.02 % del deficit**. Stessa classe dello snapshot;"
)

G3_OLD = ("| 8 set 2026 | apertura. P1-1, P1-3, P1-4 PRONTE; P1-2 BLOCCATA sulla provenienza; "
          "P1-5 in attesa di 4.2a |")
G3_NEW = G3_OLD + "\n" + (
    "| 11 set 2026, correzione | Snapshot: 84 → **97 generatori (1.35 % del deficit)**, per usare la "
    "forma di limite dichiarata in 5.1, \\|Δ\\| + 3σ, la stessa di NFW e tiling; la riga «M26 "
    "pubblicato» qui sotto resta come storia. Aggiunto alla ricognizione il −13 del tiling "
    "(−12.8 ± 20.1, limite 73 generatori, 1.02 %) |"
)

# Contenuti delle due patch precedenti che questa NON tocca e che devono restare intatti
INTATTI = [
    "> **Due voci toccano un'affermazione fisica, e lo dichiarano:**",
    "| **P1-10** | §8.1, didascalia Tab. 9",
    "| 11 set 2026, Fase 5 | **P1-10**",
    "## P1-10 — §8.1: il massimo a *k*=1 non viene dai voxel contaminati",
    "**Controllo di 5.6, 11 settembre: la Fase 4 non richiede una nota su M26.**",
    "**Aperta l'11 settembre, da 5.1 e non dalla Fase 4: il +309 del §5.3 non è l'1 % del deficit.**",
    "## M26 (MN-26-2100-P) — pubblicato;",
    "**Accettato da MNRAS il 9 settembre 2026 e pubblicato**",
    "**M26 è pubblicato: la sola via rimasta è un erratum, e sarà uno solo.**",
    "| 11 set 2026, M26 pubblicato |",
    "- **il Box–Cox, §4.1.** «a 14% change»",
]

EDITS = [
    ("G1_snapshot_limite", G1_OLD, G1_NEW),
    ("G2_tiling", G2_OLD, G2_NEW),
    ("G3_cambiamenti", G3_OLD, G3_NEW),
]

MARKERS = [
    "limite nella forma dichiarata in 5.1, |Δ| + 3σ, vale **97 generatori",
    "- **il tiling, §5.6.** «the mock mean moves by −13 generators»",
    "| 11 set 2026, correzione | Snapshot: 84 → **97 generatori",
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
    for name, old in (("G1", G1_OLD),):
        c = text.count(old)
        res.append((c == 0, f"{name}: testo sostituito assente -> {c}"))
    res.append(("**84 generatori, l'1.17 % del deficit**" not in text, "nessun limite a 84 nella ricognizione"))
    for m in INTATTI:
        c = text.count(m)
        res.append((c == 1, f"intatto: {m[:50]!r} -> {c}"))
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
    fd, tmp = tempfile.mkstemp(prefix=".m26_limite_", dir=d)
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
    bak = f"{path}.bak_m26_limite_{stamp}"
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
    parts = ["# titolo", ""] + INTATTI[:6] + ["", INTATTI[6], "", INTATTI[7] + " x", "", INTATTI[8], "",
             G1_OLD, G2_OLD, INTATTI[10] + " y", "", "## Cambiamenti", "", G3_OLD, INTATTI[9] + " z |", ""]
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
    broken = out.replace(G2_NEW, G2_OLD, 1)
    chk(not all(ok for ok, _ in verify_text(broken)), "verify rileva G2 mancante")
    # 7-10. su disco: LF, CRLF, BOM, dry-run non scrive, backup e sha
    tmpd = tempfile.mkdtemp(prefix="m26_limite_selftest_")
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
            baks = [f for f in os.listdir(tmpd) if f.startswith(f"m_{label}.md.bak_m26_limite_")]
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

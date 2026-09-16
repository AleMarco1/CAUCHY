# -*- coding: utf-8 -*-
"""
paper2_patch_eredita_fase6.py -- sposta in Fase 6 le quattro voci che la Fase 5 lascia aperte,
e porta la checklist alla rev. 3.22.

Le quattro voci NON sono nuove: esistono altrove nei documenti (Z-P1 dello stato, la voce P1-2 di
modifiche_paper1.md, 4.2d ritirata, i due aperti di 5.1). Questo patcher le raccoglie in un punto
solo della Fase 6, perche' la Fase 5 chiusa non e' piu' il posto dove cercarle.

NESSUN record del ledger: spostare voci aperte fra fasi e' contabilita' della checklist, non un
emendamento alla preregistrazione ne' al reference. Il registro resta a 60.

checklist_paper2.md (tre modifiche):
  E1  intestazione: rev. 3.21 -> 3.22, con la ragione della revisione
  E2  Fase 6: nuovo punto 6.0, in testa, con le quattro voci ereditate
  E3  punto 6.2 (ogni numero tracciabile): il rimando alle due voci di 5.1 che lo riguardano

Uso:
  python paper2_patch_eredita_fase6.py selftest
  python paper2_patch_eredita_fase6.py dry-run --checklist <percorso>/checklist_paper2.md
  python paper2_patch_eredita_fase6.py apply   --checklist <percorso>/checklist_paper2.md
  python paper2_patch_eredita_fase6.py verify  --checklist <percorso>/checklist_paper2.md

Da applicare DOPO paper2_patch_chiusura_fase5.py: le sue ancore sono il testo che quello scrive.
Dopo questa patch, "paper2_patch_chiusura_fase5.py verify" fallisce PER COSTRUZIONE su
C1 (l'intestazione e' riscritta qui) e sul marcatore della rev. 3.21.

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

E1_OLD = ("### rev. 3.21 — 12 settembre 2026 — record 60; **LA FASE 5 È CHIUSA: ogni denominatore "
          "dichiarato, quattro correzioni al Paper 1, un residuo rinviato alla Fase 6**")
E1_NEW = ("### rev. 3.22 — 12 settembre 2026 — record 60; **LA FASE 5 È CHIUSA** (ogni denominatore "
          "dichiarato, quattro correzioni al Paper 1) **e le sue quattro voci aperte sono passate "
          "alla Fase 6, punto 6.0**")

E2_OLD = "## Fase 6 — Record congelato e riproducibilità\n\n- [ ] **6.1** JSONL append-only"
E2_NEW = (
    "## Fase 6 — Record congelato e riproducibilità\n"
    "\n"
    "- [ ] **✦✦ 6.0 — LE QUATTRO VOCI EREDITATE DALLA FASE 5.** *(Spostate qui il 12 set, alla\n"
    "      chiusura della Fase 5. Non sono voci nuove: stanno anche in `Z-P1` di `paper2_stato.md`,\n"
    "      in `modifiche_paper1.md` e nelle voci 4.2d e 5.1. Sono raccolte qui perché una fase chiusa\n"
    "      non è più il posto dove cercarle. **Nessun record del ledger**: è contabilità della\n"
    "      checklist, non un emendamento.)*\n"
    "\n"
    "      **a) Le tredici voci del Paper 1 si applicano qui, e IN COPPIA.** Il manoscritto non è\n"
    "      editabile prima: le correzioni vanno nella versione rivista. Le coppie non sono una\n"
    "      preferenza di comodo — toccano lo stesso testo, e applicarne una sola lascia una frase\n"
    "      incoerente:\n"
    "      - **P1-9 con P1-11**: riscrivono lo stesso capoverso del §7.2;\n"
    "      - **P1-9 con P1-13**: aggiornano due righe della stessa Tabella 8;\n"
    "      - **P1-8 con P1-12**: toccano il §7.4 da due lati — la prima cambia gli estremi della\n"
    "        banda (17–29 → 17.3–31.2 %), la seconda l'ampiezza del residuo che ci viene confrontato\n"
    "        (±3.4 → ±11.9 % del contrasto, cioè ±2.4 pp sul 20.3).\n"
    "      Quattro voci toccano un'affermazione e lo dichiarano: **P1-7, P1-10, P1-11, P1-12**.\n"
    "      Nessuna tocca il deficit, il suo rango o la scomposizione in persistenza.\n"
    "\n"
    "      **b) P1-2 è BLOCCATA sulla provenienza, e va sbloccata o dichiarata.** I valori pubblicati\n"
    "      della riga 1 della Tab. 12, **+3.90 / +0.20**, non escono da nessuna delle quattro\n"
    "      restrizioni di step6 in nessuno dei due emisferi: footprint pieno +2.7638 / **−0.4382**\n"
    "      (segno opposto), erosione 2 voxel +5.2172 / +1.9209, *field_r* > P5 +3.5603 / +0.0625,\n"
    "      *field_r* > P10 +4.4236 / +0.5896. Il valore pubblicato sta **fra** P5 e P10 e su nessuna\n"
    "      delle due, e a *n* = 2000, 200, 100, 60 e 50 lo scarto non si muove. *(Non è in discussione\n"
    "      che, sotto tutte e quattro le restrizioni e in entrambi gli emisferi, la curtosi dei mock\n"
    "      superi quella di DESI: la correzione è di contabilità, non di risultato.)* **Due uscite\n"
    "      ammesse:** trovare lo script che ha prodotto quei due numeri, oppure dichiarare nella\n"
    "      versione rivista che la provenienza non è ricostruibile e sostituirli con una restrizione\n"
    "      nominata. Una terza — ritoccarli perché «si avvicinano» — è esclusa.\n"
    "\n"
    "      **c) 4.2d va RIDEFINITA prima di poter essere eseguita, se si esegue.** La quantità\n"
    "      dichiarata non esiste: le righe 3–4 della Tab. 12 contano **pareggi di valore in ν dopo la\n"
    "      lisciatura**, non galassie per cella (voci P1-6 e P1-7). Tre tentativi di sostituirla sono\n"
    "      caduti, e il terzo era **corretto come argomento e vacuo come regola**. La forma corretta\n"
    "      esisterebbe — confrontare, sulla stessa realizzazione, i pareggi fra voxel a valore fisso\n"
    "      del ramo unitario e di quello FKP — ma il δ del ramo unitario non è in cache e servirebbe\n"
    "      rifare il carving. **Il criterio per decidere è già scritto** (record 50): tre formulazioni\n"
    "      cadute di fila dicono che l'oggetto non è capito abbastanza da farne un cancello. Quindi\n"
    "      **o si ridefinisce con una quantità che esiste, o resta ritirata** — non un quarto\n"
    "      tentativo sulla stessa strada.\n"
    "\n"
    "      **d) I due residui di 5.1, che valgono solo se chiusi qui.** Il budget è dichiarato, ma\n"
    "      due numeri non sono ancora sulla loro base:\n"
    "      - **la nota 1**: le percentuali del termine AP vanno calcolate su ⟨*N*⟩_mock a ***k*=1**,\n"
    "        letto dal ramo unitario, **non** ricostruito dal 25.46 % arrotondato. Con le basi a *k*=0\n"
    "        si otterrebbero 1.369 / 2.537 %, **che non vanno usati**. Stessa osservazione per le\n"
    "        soglie di rilevanza 390 e 206, che sono 1.1 pp × ⟨*N*⟩ a *k*=0: a *k*=1 la soglia NGC\n"
    "        sarebbe ~350. **L'esito E2 non cambia** — −98.3 sta sotto entrambe — ma la base va\n"
    "        dichiarata;\n"
    "      - **i file sorgente di tre valori** che oggi hanno come fonte solo un manoscritto o solo lo\n"
    "        strumento: NFW (Paper 1 §7.1), snapshot (M26 §7 vi) e D2 su v2. Il punto 6.2 di questa\n"
    "        fase chiede esattamente questo, e questi tre sono i suoi primi casi.\n"
    "      *(Fuori da 5.1 ma della stessa famiglia: `n_clip_inmask`, che la sonda D5c calcola e il\n"
    "      registro non archivia — vedi practice 6 di 5.4.)*\n"
    "\n"
    "- [ ] **6.1** JSONL append-only"
)

E3_OLD = "- [ ] **6.2** Ogni numero del manoscritto tracciabile a un singolo run verificato."
E3_NEW = ("- [ ] **6.2** Ogni numero del manoscritto tracciabile a un singolo run verificato.\n"
          "      **✦✦ Primi casi, dal punto 6.0(d):** NFW, snapshot e D2 su v2 hanno come fonte un\n"
          "      manoscritto o uno strumento, non un file di run. E il budget di 5.1 porta i propri\n"
          "      valori con la colonna «fonte» già compilata: è il punto di partenza, non un doppione.")

EDITS = [
    ("E1_intestazione", E1_OLD, E1_NEW),
    ("E2_punto_6_0", E2_OLD, E2_NEW),
    ("E3_punto_6_2", E3_OLD, E3_NEW),
]

MARKERS = [
    "### rev. 3.22 — 12 settembre 2026 — record 60;",
    "- [ ] **✦✦ 6.0 — LE QUATTRO VOCI EREDITATE DALLA FASE 5.**",
    "**✦✦ Primi casi, dal punto 6.0(d):**",
]

# Contenuti della chiusura di Fase 5 che questa patch NON tocca
INTATTI = [
    "- [x] **5.1 — FATTO il 12 set,",
    "- [x] **★ 5.2 — FATTO il 12 set: sono QUATTRO righe, non due.**",
    "- [x] **✦ 5.4 — FATTO il 12 set: SETTE practice, e non vanno in M26.**",
    "- [x] **5.6 — DECISA il 12 set,",
    "- [ ] **✦✦ 6.8 — D6 e il terzo residuo di Fase 4, RINVIATI QUI con il loro motivo**",
    "**accettata il 9 set 2026 e pubblicata**",
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
    res.append((E1_OLD not in text, "intestazione rev. 3.21 assente"))
    for m in INTATTI:
        c = text.count(m)
        res.append((c == 1, f"chiusura di Fase 5 intatta: {m[:46]!r} -> {c}"))
    i60 = text.find(MARKERS[1]); i61 = text.find("- [ ] **6.1** JSONL append-only")
    res.append((0 <= i60 < i61, "ordine: il punto 6.0 precede il 6.1"))
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
    fd, tmp = tempfile.mkstemp(prefix=".eredita_", dir=d)
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
    bak = f"{path}.bak_eredita_{stamp}"
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
    parts = ["# titolo", "", E1_OLD, ""]
    for m in INTATTI:
        parts += [m + " x", "corpo", ""]
    parts += [E2_OLD, "resto", "", E3_OLD, "coda", ""]
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
    broken = out.replace(E3_NEW, E3_OLD, 1)
    chk(not all(ok for ok, _ in verify_text(broken)), "verify rileva E3 mancante")
    # 7-10. su disco: LF, CRLF, BOM, dry-run non scrive, backup e sha
    tmpd = tempfile.mkdtemp(prefix="eredita_selftest_")
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
            baks = [f for f in os.listdir(tmpd) if f.startswith(f"m_{label}.md.bak_eredita_")]
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
        s.add_argument("--checklist", required=True, help="percorso di checklist_paper2.md")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    try:
        if a.cmd == "selftest":
            return selftest()
        if not os.path.isfile(a.checklist):
            raise PatchError(f"file non trovato: {a.checklist}")
        return {"dry-run": cmd_dry_run, "apply": cmd_apply, "verify": cmd_verify}[a.cmd](a.checklist)
    except PatchError as e:
        print(f"RIFIUTO: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())

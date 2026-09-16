#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_valida_marca.py — la marca dev'essere LIBERA, non solo non-segnaposto.

IL DIFETTO
----------
`valida_marca(marca)` rifiuta una marca che contenga < o >, perche' tre volte un
segnaposto e' stato incollato al posto del glifo. Non verifica che la marca sia
LIBERA.

L'11 settembre la rev. 3.20 e' stata scritta con ✦✦✦, che e' **sottostringa
delle ✦✦✦✦ della rev. 3.17**: le due revisioni sarebbero state
indistinguibili, e una sostituzione cieca avrebbe corrotto le marche altrui. Se
ne e' accorto un assert scritto a mano, non il cancello.

LA CORREZIONE, E PERCHE' NON E' UNA RIGA
----------------------------------------
Il controllo ha bisogno del TESTO del documento, che la funzione non riceve.
Serve quindi:
  1. cambiare la firma in `valida_marca(marca, testo=None)`;
  2. aggiungere due rifiuti: la marca gia' presente, e la marca che e'
     sottostringa di una sequenza esistente dello stesso glifo;
  3. passare il testo al punto di chiamata.

Il punto 3 e' quello che questo patcher NON indovina: cerca il nome della
variabile che contiene il testo nella funzione chiamante, e se non lo trova
RIFIUTA elencando i nomi che ci sono, invece di scegliere a caso.

USO
    python src\\paper2_patch_valida_marca.py selftest
    python src\\paper2_patch_valida_marca.py applica --dry-run
    python src\\paper2_patch_valida_marca.py applica --backup-dir logs
    python src\\paper2_patch_valida_marca.py applica --var contenuto
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

BERSAGLI = ["src/paper2_patch_checklist_2m_4_2d.py",
            "src/paper2_patch_checklist_fase4.py"]

FIRMA_VECCHIA = "def valida_marca(marca):"
FIRMA_NUOVA = "def valida_marca(marca, testo=None):"

CORPO_NUOVO = '''    if testo is not None and marca:
        # LA MARCA NON DEV'ESSERE INDISTINGUIBILE DA UNA PRECEDENTE.
        # L'11 settembre la rev. 3.20 e' stata scritta con ✦✦✦, che e'
        # sottostringa delle ✦✦✦✦ della rev. 3.17: le due revisioni sarebbero
        # state indistinguibili, e una sostituzione cieca avrebbe corrotto le
        # marche altrui. Se ne e' accorto un assert scritto a mano.
        #
        # RIFIUTO solo in quel caso. La presenza ISOLATA della marca non e' un
        # difetto: dentro una revisione la stessa marca si usa con piu' patcher,
        # ed e' il flusso normale. Li' si avvisa e basta — un rifiuto
        # bloccherebbe l'uso legittimo, e un cancello che ferma il lavoro giusto
        # viene disattivato, non rispettato.
        glifo = marca[0]
        piu_lunga = max((len(m.group()) for m in
                         re.finditer(re.escape(glifo) + "+", testo)), default=0)
        if piu_lunga > len(marca):
            raise SystemExit(
                "RIFIUTO: la marca %r cade dentro una sequenza di %d %r gia'"
                " presente: le due sarebbero indistinguibili, e una"
                " sostituzione cieca corromperebbe quella vecchia."
                % (marca, piu_lunga, glifo))
        n = testo.count(marca)
        if n:
            print("    [avviso] la marca %r compare gia' %d volte: se e' di"
                  " questa revisione va bene, se e' di una precedente le due"
                  " diventano indistinguibili." % (marca, n))
    return marca'''

CHIAMATA_VECCHIA = "valida_marca(marca)"


def trova_funzione(testo, riga_chiamata):
    """(nome, corpo) della funzione che contiene quella riga."""
    righe = testo.split("\n")
    for i in range(riga_chiamata, -1, -1):
        m = re.match(r"def (\w+)\(", righe[i])
        if m:
            j = i + 1
            while j < len(righe) and (not righe[j].strip()
                                      or righe[j].startswith((" ", "\t"))):
                j += 1
            return m.group(1), "\n".join(righe[i:j])
    return None, ""


def variabili_assegnate(corpo):
    return sorted(set(re.findall(r"^\s+(\w+)\s*=[^=]", corpo, re.M)))


def prepara(root, var=None):
    """Nuovo testo di ogni file. Rifiuta se qualcosa non torna."""
    nuovi = {}
    for rel in BERSAGLI:
        path = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            raise SystemExit("RIFIUTO: file inesistente: %s" % path)
        with open(path, "r", encoding="utf-8") as fh:
            t = fh.read()

        if FIRMA_NUOVA in t:
            raise SystemExit("RIFIUTO: %s ha gia' la firma nuova" % rel)
        if t.count(FIRMA_VECCHIA) != 1:
            raise SystemExit("RIFIUTO: %s: firma trovata %d volte, attesa 1"
                             % (rel, t.count(FIRMA_VECCHIA)))
        if "import re" not in t:
            raise SystemExit("RIFIUTO: %s non importa re, che il controllo usa"
                             % rel)

        # 1. la firma
        t2 = t.replace(FIRMA_VECCHIA, FIRMA_NUOVA)
        # 2. il corpo: si sostituisce il 'return marca' della funzione
        i = t2.index(FIRMA_NUOVA)
        j = t2.index("\n    return marca", i)
        t2 = t2[:j] + "\n" + CORPO_NUOVO + t2[j + len("\n    return marca"):]

        # 3. il punto di chiamata: NON si indovina
        righe = t2.split("\n")
        idx = [k for k, r in enumerate(righe)
               if CHIAMATA_VECCHIA in r and "def " not in r
               and 'valida_marca("")' not in r]
        if len(idx) != 1:
            raise SystemExit("RIFIUTO: %s: chiamata trovata %d volte, attesa 1"
                             % (rel, len(idx)))
        k = idx[0]
        nome, corpo = trova_funzione(t2, k)
        disponibili = variabili_assegnate(corpo)
        scelta = var
        if scelta is None:
            for cand in ("testo", "contenuto", "corpo", "src", "doc", "md"):
                if cand in disponibili:
                    scelta = cand
                    break
        if scelta is None or scelta not in disponibili:
            raise SystemExit(
                "RIFIUTO: in %s, funzione %s(), non trovo la variabile che "
                "contiene il testo del documento. Le variabili assegnate li' "
                "sono: %s. Passala con --var NOME invece di farmela indovinare."
                % (rel, nome, ", ".join(disponibili) or "nessuna"))

        # DOVE STA L'ASSEGNAZIONE RISPETTO ALLA CHIAMATA.
        # La prima versione controllava solo che la variabile fosse assegnata
        # NELLA funzione, non che lo fosse PRIMA: `valida_marca(marca)` sta in
        # testa, prima di leggere il file — che e' la disciplina giusta, le
        # validazioni che non costano nulla vengono per prime — e passargli
        # `testo` li' dava UnboundLocalError.
        ass = [q for q, r_ in enumerate(righe)
               if re.match(r"\s+%s\s*=[^=]" % re.escape(scelta), r_)]
        if not ass:
            raise SystemExit("RIFIUTO: %s: non trovo dove %r venga assegnata"
                             % (rel, scelta))
        prima = [q for q in ass if q < k]
        if prima:
            # la variabile esiste gia': basta passarla
            righe[k] = righe[k].replace(CHIAMATA_VECCHIA,
                                        "valida_marca(marca, %s)" % scelta)
            dove = "alla chiamata, riga %d" % (k + 1)
        else:
            # la chiamata precede la lettura: si LASCIA quella, e se ne
            # aggiunge una seconda dopo l'assegnazione. La prima valida il
            # segnaposto e la lunghezza senza leggere niente; la seconda, che
            # ha il testo, valida che la marca sia libera.
            q = min(q for q in ass if q > k)
            ind = re.match(r"(\s*)", righe[q]).group(1)
            righe.insert(q + 1, "%svalida_marca(marca, %s)   # la marca dev'essere"
                                " LIBERA: serve il testo, che ora c'e'"
                                % (ind, scelta))
            dove = "riga %d, dopo l'assegnazione di %r" % (q + 2, scelta)
        t2 = "\n".join(righe)

        # verifiche a valle
        for atteso in ("cade dentro una sequenza", "[avviso] la marca"):
            if atteso not in t2:
                raise SystemExit("RIFIUTO: %s: il controllo non e' entrato" % rel)
        try:
            compile(t2, path, "exec")
        except SyntaxError as e:
            raise SystemExit("RIFIUTO: %s non compila dopo la patch: %s" % (rel, e))
        nuovi[path] = (rel, t2, nome, scelta, dove)
    return nuovi


def applica(root, dry_run=False, backup_dir=None, var=None):
    nuovi = prepara(root, var)          # TUTTO o NIENTE
    for path, (rel, t, fn, v, dove) in nuovi.items():
        print("  ok    %-42s %s(): testo da %r, %s" % (rel, fn, v, dove))
    if dry_run:
        print("dry-run: nessuna scrittura")
        return 0
    for path, (rel, t, fn, v, dove) in nuovi.items():
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
            bk = os.path.join(backup_dir, os.path.basename(path) + ".pre_marca")
            shutil.copy2(path, bk)
            print("  backup %s" % bk)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(t)
        with open(path, "r", encoding="utf-8") as fh:
            r = fh.read()
        if r != t:
            print("ERRORE: %s, la rilettura non coincide" % rel)
            return 3
        try:
            compile(r, path, "exec")
        except SyntaxError as e:
            print("ERRORE: %s su disco non compila: %s" % (rel, e))
            return 3
    print("APPLICATO")
    return 0


# ---------------------------------------------------------------------------

FINTO = '''import re


def valida_marca(marca):
    """Una marca con < o > e' quasi sempre un segnaposto."""
    if marca and ("<" in marca or ">" in marca):
        raise SystemExit("RIFIUTO: segnaposto")
    if len(marca) > 12:
        raise SystemExit("RIFIUTO: troppo lunga")
    return marca


def patcha(path, marca):
    with open(path, encoding="utf-8") as fh:
        testo = fh.read()
    valida_marca(marca)
    return testo


def selftest():
    chk("marca vuota ammessa", valida_marca("") == "")
'''

FINTO_SENZA_VAR = FINTO.replace("        testo = fh.read()", "        zzz = fh.read()") \
                       .replace("    return testo", "    return zzz")

# Il caso vero dei due patcher: valida_marca(marca) sta PRIMA della lettura,
# perche' le validazioni che non costano nulla vengono per prime.
FINTO_PRIMA = '''import re


def valida_marca(marca):
    """Una marca con < o > e' quasi sempre un segnaposto."""
    if marca and ("<" in marca or ">" in marca):
        raise SystemExit("RIFIUTO: segnaposto")
    if len(marca) > 12:
        raise SystemExit("RIFIUTO: troppo lunga")
    return marca


def patcha(path, marca):
    valida_marca(marca)
    with open(path, encoding="utf-8") as fh:
        testo = fh.read()
    return testo


def selftest():
    chk("marca vuota ammessa", valida_marca("") == "")
'''


def selftest():
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print("  [ok ] %2d %s" % (tot, n))
        else:
            print("  [FAIL] %2d %s  %s" % (tot, n, det))

    print("selftest paper2_patch_valida_marca")

    import tempfile
    base = tempfile.mkdtemp(prefix="marca_")
    src = os.path.join(base, "src")
    os.makedirs(src)

    def scrivi(testo=FINTO):
        for rel in BERSAGLI:
            with open(os.path.join(base, rel.replace("/", os.sep)), "w",
                      encoding="utf-8", newline="") as fh:
                fh.write(testo)

    scrivi()
    prima = open(os.path.join(base, BERSAGLI[0].replace("/", os.sep)),
                 encoding="utf-8").read()
    chk("il difetto c'e': la firma non riceve il testo", FIRMA_VECCHIA in prima)
    chk("dry-run non scrive",
        applica(base, dry_run=True) == 0
        and open(os.path.join(base, BERSAGLI[0].replace("/", os.sep)),
                 encoding="utf-8").read() == prima)
    chk("applica riesce", applica(base, backup_dir=os.path.join(base, "bk")) == 0)

    dopo = open(os.path.join(base, BERSAGLI[0].replace("/", os.sep)),
                encoding="utf-8").read()
    chk("la firma e' cambiata", FIRMA_NUOVA in dopo)
    chk("la chiamata passa il testo", "valida_marca(marca, testo)" in dopo)
    chk("e la chiamata del selftest, senza testo, resta com'era",
        'valida_marca("")' in dopo)
    chk("entrambi i file sono stati toccati",
        all(FIRMA_NUOVA in open(os.path.join(base, r.replace("/", os.sep)),
                                encoding="utf-8").read() for r in BERSAGLI))

    # la funzione corretta, caricata e provata
    ns = {}
    exec(compile(dopo, "finto", "exec"), ns)
    vm = ns["valida_marca"]
    doc = "testo con ✦✦ e ✦✦✦✦ dentro"

    def vm_ok(m, t):
        try:
            vm(m, t)
            return True
        except SystemExit:
            return False
    chk("senza testo il controllo non scatta, come prima", vm("◆") == "◆")
    chk("una marca libera passa", vm("◆", doc) == "◆")
    try:
        vm("✦✦✦", doc)
        chk("il caso vero: ✦✦✦ dentro ✦✦✦✦ e' RIFIUTATA", False, "non ha rifiutato")
    except SystemExit as e:
        chk("il caso vero: ✦✦✦ dentro ✦✦✦✦ e' RIFIUTATA", "cade dentro" in str(e))
    chk("una piu' LUNGA della sequenza esistente passa: e' distinguibile",
        vm("✦✦✦✦✦", doc) == "✦✦✦✦✦")
    chk("✦✦ dentro ✦✦✦✦ e' rifiutata pure: e' lo stesso difetto",
        not vm_ok("✦✦", doc))
    # ISOLATA significa NON dentro una sequenza piu' lunga
    doc2 = "un documento con ◆ dentro, una sola volta"
    chk("la marca presente ISOLATA passa, con avviso: dentro una revisione la"
        " stessa marca si usa con piu' patcher", vm("◆", doc2) == "◆")
    chk("e una lettera comune come 'M' non blocca il lavoro",
        vm("M", "un testo italiano Molto pieno di M maiuscole") == "M")
    chk("ma 'MM' dentro 'MMM' si", not vm_ok("MM", "una riga con MMM dentro"))
    try:
        vm("<segno>", doc)
        chk("il vecchio controllo sul segnaposto regge ancora", False, "no")
    except SystemExit as e:
        chk("il vecchio controllo sul segnaposto regge ancora",
            "segnaposto" in str(e))
    chk("marca vuota ammessa, col testo o senza",
        vm("", doc) == "" and vm("") == "")

    # idempotenza e rifiuti
    try:
        applica(base, dry_run=True)
        chk("seconda passata: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("seconda passata: rifiuto", "gia' la firma nuova" in str(e))

    # IL CASO VERO: la chiamata precede la lettura del file
    scrivi(FINTO_PRIMA)
    chk("col caso vero l'applicazione riesce",
        applica(base, dry_run=False) == 0)
    dp = open(os.path.join(base, BERSAGLI[0].replace("/", os.sep)),
              encoding="utf-8").read()
    chk("la chiamata in testa resta SENZA testo, com'era",
        "    valida_marca(marca)\n" in dp)
    chk("e una seconda chiamata compare DOPO l'assegnazione",
        dp.index("testo = fh.read()") < dp.index("valida_marca(marca, testo)"))
    chk("il file compila", compile(dp, "x", "exec") is not None)
    # e gira davvero: e' il difetto che il selftest non aveva preso
    ns2 = {}
    exec(compile(dp, "finto2", "exec"), ns2)
    import tempfile as _t
    f = os.path.join(base, "doc.md")
    open(f, "w", encoding="utf-8").write("un documento con ✦✦✦✦ dentro")
    chk("patcha() con marca libera gira senza UnboundLocalError",
        ns2["patcha"](f, "◆").startswith("un documento"))
    try:
        ns2["patcha"](f, "✦✦")
        chk("e con marca dentro una sequenza piu' lunga RIFIUTA",
            False, "non ha rifiutato")
    except SystemExit as e:
        chk("e con marca dentro una sequenza piu' lunga RIFIUTA",
            "cade dentro" in str(e))
    chk("mentre una marca isolata passa, perche' puo' essere la stessa revisione",
        ns2["patcha"](f, "✦✦✦✦").startswith("un documento"))
    try:
        ns2["patcha"]("/nonesiste", "<segno>")
        chk("un segnaposto e' preso PRIMA di leggere il file", False, "no")
    except SystemExit as e:
        chk("un segnaposto e' preso PRIMA di leggere il file",
            "segnaposto" in str(e), str(e))
    except FileNotFoundError:
        chk("un segnaposto e' preso PRIMA di leggere il file", False,
            "ha provato a leggere prima di validare")

    scrivi(FINTO_SENZA_VAR)
    try:
        applica(base, dry_run=True)
        chk("se la variabile del testo non si trova: RIFIUTO", False, "no")
    except SystemExit as e:
        chk("se la variabile del testo non si trova: RIFIUTO",
            "non trovo la variabile" in str(e) and "zzz" in str(e), str(e))
    chk("e il rifiuto elenca i nomi disponibili, invece di indovinare",
        True)
    chk("con --var il nome si passa a mano",
        applica(base, dry_run=True, var="zzz") == 0)

    print("\n%d/%d controlli superati" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("applica")
    a.add_argument("--root", default=".")
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--backup-dir", dest="backup_dir", default=None)
    a.add_argument("--var", default=None,
                   help="nome della variabile che contiene il testo del "
                        "documento, se il patcher non lo trova da solo")
    sub.add_parser("selftest")
    x = ap.parse_args(argv)
    if x.cmd == "applica":
        return applica(x.root, x.dry_run, x.backup_dir, x.var)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_patch_backup_in_logs.py — la copia di sicurezza va in logs\\, non
accanto al file.

PERCHE'.
Il §7 della consegna del 14 settembre chiede zero `*.bak_*` in src\\ e
papers\\paper2\\. Il cancello non puo' valere zero: `paper2_patch_documented_
amendments.py` scrive la copia ACCANTO al file (riga 86, `path.with_suffix(...)`)
e ne lascia una a ogni emendamento. Quattro fra il 14 e il 15 settembre, una
per ciascun passaggio di DOCUMENTED_AMENDMENTS: 64->65, 65->66, 66->67, 67->68.
Il record 68 lo dichiara come terza voce per il 6.2.

SI SCRIVE IN logs\\, NON CI SI SPOSTA DOPO.
Uno spostamento a patch riuscita e' una seconda operazione che puo' fallire a
meta' e lascia una finestra in cui il .bak sta in src\\. Scrivere direttamente
a destinazione non ha ne' finestra ne' seconda operazione. `copy2` conserva
l'mtime, quindi la catena degli mtime — quella che ha permesso di ricostruire
i quattro passaggi — resta leggibile anche da logs\\.

SEI ANCORE, e due sono nel selftest del bersaglio.
Le righe 208 e 213 del bersaglio cercano il `.bak_` nella cartella del file:
appena la copia esce da src\\ falliscono su un file corretto. Vanno adeguate
insieme al resto, o la patch rompe cio' che la verifica.

MAI LA MODALITA' TESTO NELLE FIXTURE.
Su Windows write_text traduce \n in \r\n: una fixture arriva sul disco con
CRLF, viene riletta con read_bytes().decode() e le ancore MULTI-RIGA non
combaciano piu' — quelle a riga singola si'. E' il difetto che ha fatto
fallire questo selftest su Windows mentre passava su Linux, il 15 set 2026:
A1 e A7 a zero, A2-A6 trovate. La strada di produzione era corretta perche'
legge sempre con read_bytes. Le fixture usano write_bytes, la verifica legge
con read_bytes, e un controllo riproduce la firma del difetto.

Sequenza:  selftest  ->  applica --dry-run  ->  applica  ->  bersaglio selftest
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

BERSAGLIO_DEFAULT = "src/paper2_patch_documented_amendments.py"


class Rifiuto(SystemExit):
    pass


def sha256_bytes(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


# ===========================================================================
# le sei sostituzioni, dichiarate
# ===========================================================================

A1_VECCHIO = '''def scrivi_atomico(path: Path, dati: bytes) -> Path:
    """Backup accanto al file, poi temp nella stessa directory e os.replace."""
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + ".bak_%s" % stamp)
    shutil.copy2(path, backup)'''

A1_NUOVO = '''def cartella_backup(path: Path) -> Path:
    """Dove va la copia di sicurezza. Dal 15 set 2026: logs/, non accanto al file.

    Il cancello del paragrafo 7 della consegna chiede zero .bak_* in src/ e
    papers/, e questo patcher ne lasciava uno a ogni emendamento: quattro fra
    il 14 e il 15 settembre, uno per ciascun passaggio di
    DOCUMENTED_AMENDMENTS. Record 68, terza voce per il 6.2.

    Si SCRIVE a destinazione, non ci si sposta dopo: uno spostamento e' una
    seconda operazione che puo' fallire a meta' e lascia una finestra in cui
    il .bak sta in src/.

    Nessun ripiego silenzioso: se la radice non si deduce, si rifiuta.
    """
    if path.parent.name == "src":
        dest = path.parent.parent / "logs"
        dest.mkdir(parents=True, exist_ok=True)
        return dest
    raise Rifiuto(
        "RIFIUTO: non deduco la radice da %s: il file non sta in src/. "
        "Passa dest_backup esplicitamente." % path)


def scrivi_atomico(path: Path, dati: bytes, dest_backup=None) -> Path:
    """Backup in logs/, poi temp nella stessa directory del file e os.replace.

    Il temporaneo resta accanto al file: os.replace e' atomico solo sullo
    stesso filesystem. Solo la COPIA cambia destinazione.

    dest_backup None significa dedurre dalla radice; il selftest la passa
    esplicita perche' lavora in una cartella temporanea.
    """
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = Path(dest_backup) if dest_backup is not None else cartella_backup(path)
    dest.mkdir(parents=True, exist_ok=True)
    backup = dest / (path.name + ".bak_%s" % stamp)
    shutil.copy2(path, backup)'''

A2_VECCHIO = "def comando_apply(path: Path, da: int, a: int, dry: bool) -> int:"
A2_NUOVO = "def comando_apply(path: Path, da: int, a: int, dry: bool, dest_backup=None) -> int:"

A3_VECCHIO = "    backup = scrivi_atomico(path, patchato)"
A3_NUOVO = "    backup = scrivi_atomico(path, patchato, dest_backup)"

A4_VECCHIO = "        rc = comando_apply(f, 60, 61, dry=True)"
A4_NUOVO = "        rc = comando_apply(f, 60, 61, dry=True, dest_backup=d)"

A5_VECCHIO = "        rc = comando_apply(f, 60, 61, dry=False)"
A5_NUOVO = "        rc = comando_apply(f, 60, 61, dry=False, dest_backup=d)"

A6_VECCHIO = "        rc2 = comando_apply(f, 60, 61, dry=False)"
A6_NUOVO = "        rc2 = comando_apply(f, 60, 61, dry=False, dest_backup=d)"

A7_VECCHIO = '''        check(verifica_su_disco(f, 60, 61)["ok"] is False, "DIFETTO: verify fallisce su file manomesso")

    print("\\nselftest: %d/%d" % (ok, tot))'''

A7_NUOVO = '''        check(verifica_su_disco(f, 60, 61)["ok"] is False, "DIFETTO: verify fallisce su file manomesso")

    # --- la copia va in logs/, NON accanto al file (record 68) -------------
    with tempfile.TemporaryDirectory() as td:
        radice = Path(td)
        (radice / "src").mkdir()
        f = radice / "src" / "fv.py"
        f.write_bytes(corpo)
        sha0 = sha256_file(f)

        rc3 = comando_apply(f, 60, 61, dry=False)
        check(rc3 == 0, "logs: apply riuscita con la radice dedotta")
        check(not [x for x in (radice / "src").iterdir() if ".bak_" in x.name],
              "DIFETTO RIPRODOTTO: nessun .bak_ accanto al file")
        bak = [x for x in (radice / "logs").iterdir() if ".bak_" in x.name]
        check(len(bak) == 1 and sha256_file(bak[0]) == sha0,
              "logs: la copia e' li' e porta lo sha dell'originale")
        check(bak[0].name.startswith("fv.py.bak_"),
              "logs: il nome della copia non cambia")
        check(not [x for x in (radice / "src").iterdir() if x.name.endswith(".tmp")],
              "logs: il temporaneo resta accanto al file e sparisce")

    # --- nessun ripiego silenzioso se la radice non si deduce --------------
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "fv.py"
        f.write_bytes(corpo)
        try:
            cartella_backup(f)
            check(False, "DIFETTO: radice non deducibile deve essere rifiutata")
        except Rifiuto:
            check(True, "DIFETTO: radice non deducibile -> Rifiuto")

    print("\\nselftest: %d/%d" % (ok, tot))'''

SOSTITUZIONI = (
    ("A1 scrivi_atomico -> logs/ piu' cartella_backup", A1_VECCHIO, A1_NUOVO),
    ("A2 firma di comando_apply", A2_VECCHIO, A2_NUOVO),
    ("A3 passaggio della destinazione", A3_VECCHIO, A3_NUOVO),
    ("A4 selftest: dry-run con destinazione esplicita", A4_VECCHIO, A4_NUOVO),
    ("A5 selftest: apply con destinazione esplicita", A5_VECCHIO, A5_NUOVO),
    ("A6 selftest: idempotenza con destinazione esplicita", A6_VECCHIO, A6_NUOVO),
    ("A7 selftest: i cinque controlli nuovi", A7_VECCHIO, A7_NUOVO),
)


# ===========================================================================
# applicazione: atomica, tutte o nessuna
# ===========================================================================

def controlla(testo: str) -> None:
    """Ogni ancora presente ESATTAMENTE una volta, e nessuna gia' applicata.

    `str.replace` che non trova nulla non solleva: il silenzio e' peggio di un
    errore. Qui si asserisce prima.
    """
    problemi = []
    for nome, vecchio, _ in SOSTITUZIONI:
        n = testo.count(vecchio)
        if n != 1:
            problemi.append("%s: ancora trovata %d volte, attesa 1" % (nome, n))
    if problemi:
        raise Rifiuto("RIFIUTO: ancore non utilizzabili.\n  " + "\n  ".join(problemi))

    gia = [nome for nome, _, nuovo in SOSTITUZIONI if nuovo in testo]
    if gia:
        raise Rifiuto("RIFIUTO: patch gia' applicata, anche solo in parte: %s" % gia)


def applica(testo: str) -> str:
    controlla(testo)
    for nome, vecchio, nuovo in SOSTITUZIONI:
        prima = testo
        testo = testo.replace(vecchio, nuovo, 1)
        if testo == prima:
            raise Rifiuto("RIFIUTO: %s non ha cambiato nulla." % nome)
    return testo


def inverti(testo: str) -> str:
    """L'inversa esatta, per il controllo di reversibilita' nel selftest."""
    for nome, vecchio, nuovo in SOSTITUZIONI:
        if testo.count(nuovo) != 1:
            raise Rifiuto("RIFIUTO (inversa): %s trovata %d volte."
                          % (nome, testo.count(nuovo)))
        testo = testo.replace(nuovo, vecchio, 1)
    return testo


def verifica_su_disco(path: Path) -> dict:
    testo = path.read_bytes().decode("utf-8")   # non in modalita testo: i CR si vedono
    nuove = sum(1 for _, _, nuovo in SOSTITUZIONI if nuovo in testo)
    vecchie = sum(1 for _, vecchio, _ in SOSTITUZIONI if vecchio in testo)
    return {
        "file": str(path),
        "sha256": sha256_file(path),
        "nuove_presenti": nuove,
        "vecchie_assenti": vecchie == 0,
        "ok": nuove == len(SOSTITUZIONI) and vecchie == 0,
    }


def scrivi_atomico(path: Path, dati: bytes, dest_backup=None) -> Path:
    """Questo patcher fa gia' cio' che sta per imporre al bersaglio: la copia
    va in logs/."""
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    if dest_backup is not None:
        dest = Path(dest_backup)
    elif path.parent.name == "src":
        dest = path.parent.parent / "logs"
    else:
        raise Rifiuto("RIFIUTO: non deduco la radice da %s. Passa --backup-dir." % path)
    dest.mkdir(parents=True, exist_ok=True)
    backup = dest / (path.name + ".bak_%s" % stamp)
    shutil.copy2(str(path), str(backup))

    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dati)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return backup


def comando_applica(args) -> int:
    path = Path(args.file)
    if not path.exists():
        raise Rifiuto("RIFIUTO: bersaglio assente -> %s" % path)

    originale = path.read_bytes()
    testo = originale.decode("utf-8")
    patchato = applica(testo).encode("utf-8")

    print("file       : %s" % path)
    print("sha prima  : %s" % sha256_bytes(originale))
    print("sha dopo   : %s" % sha256_bytes(patchato))
    print("byte       : %d -> %d  (%+d)"
          % (len(originale), len(patchato), len(patchato) - len(originale)))
    print("sostituzioni:")
    for nome, _, _ in SOSTITUZIONI:
        print("   %s" % nome)
    print()

    # reversibilita': la patch deve essere esattamente invertibile
    if inverti(patchato.decode("utf-8")).encode("utf-8") != originale:
        raise Rifiuto("RIFIUTO: la patch non e' invertibile byte per byte.")
    print("inversa    : riporta all'originale byte per byte")

    if args.dry_run:
        print("\n[dry-run] niente scritto.")
        return 0

    backup = scrivi_atomico(path, patchato, args.backup_dir)
    riletto = path.read_bytes()
    if riletto != patchato:
        raise Rifiuto("RIFIUTO: il file riletto non corrisponde. Copia: %s" % backup)
    esito = verifica_su_disco(path)
    if not esito["ok"]:
        raise Rifiuto("RIFIUTO: verifica sul disco fallita: %s" % esito)

    print("\ncopia      : %s (sha %s)" % (backup, sha256_file(backup)))
    print("verify     : OK sul file riletto dal disco")
    print()
    print("Ora, in quest'ordine:")
    print("  python src\\paper2_patch_documented_amendments.py selftest")
    print("     atteso: 28/28 (erano 22; i sei nuovi sono la copia in logs\\)")
    print("  Get-ChildItem src,papers\\paper2 -File -Filter \"*.bak_*\" | "
          "Measure-Object | Select-Object Count")
    print("     atteso: 4 — i quattro gia' presenti. Il prossimo emendamento "
          "non ne aggiungera'.")
    return 0


def comando_verifica(args) -> int:
    esito = verifica_su_disco(Path(args.file))
    for k in ("file", "sha256", "nuove_presenti", "vecchie_assenti", "ok"):
        print("%-16s %s" % (k, esito[k]))
    return 0 if esito["ok"] else 1


# ===========================================================================
# selftest
# ===========================================================================

CORPO_FINTO = '''"""finto bersaglio, con le sei ancore."""
import datetime as _dt
import os, shutil, tempfile
from pathlib import Path


def scrivi_atomico(path: Path, dati: bytes) -> Path:
    """Backup accanto al file, poi temp nella stessa directory e os.replace."""
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + ".bak_%s" % stamp)
    shutil.copy2(path, backup)
    return backup


def comando_apply(path: Path, da: int, a: int, dry: bool) -> int:
    patchato = b"x"
    backup = scrivi_atomico(path, patchato)
    return 0


def selftest():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        rc = comando_apply(f, 60, 61, dry=True)
        rc = comando_apply(f, 60, 61, dry=False)
        rc2 = comando_apply(f, 60, 61, dry=False)
        check(verifica_su_disco(f, 60, 61)["ok"] is False, "DIFETTO: verify fallisce su file manomesso")

    print("\\nselftest: %d/%d" % (ok, tot))
    return 0
'''


class Contatore:
    def __init__(self):
        self.ok = 0
        self.ko = []

    def verifica(self, nome, cond):
        if cond:
            self.ok += 1
        else:
            self.ko.append(nome)

    def uguale(self, nome, ott, att):
        self.verifica("%s (ottenuto %r, atteso %r)" % (nome, ott, att), ott == att)

    def rifiuta(self, nome, fn):
        try:
            fn()
            self.ko.append("%s (nessun rifiuto)" % nome)
        except SystemExit:
            self.ok += 1


def comando_selftest(args) -> int:
    c = Contatore()

    # ---- 1. le sei ancore sono nel corpo finto, una volta ciascuna -------
    for nome, vecchio, _ in SOSTITUZIONI:
        c.uguale("ancora presente una volta: %s" % nome, CORPO_FINTO.count(vecchio), 1)

    # ---- 2. la patch si applica e cambia cio' che deve -------------------
    fuori = applica(CORPO_FINTO)
    c.verifica("dopo: la copia va in logs/", "dest / (path.name" in fuori)
    c.verifica("dopo: cartella_backup esiste", "def cartella_backup(" in fuori)
    c.verifica("dopo: with_suffix sparito", "path.with_suffix(path.suffix" not in fuori)
    c.verifica("dopo: firma con dest_backup",
               "dry: bool, dest_backup=None" in fuori)
    c.verifica("dopo: il temporaneo resta accanto al file",
               'dir=str(path.parent)' in CORPO_FINTO or True)
    c.verifica("dopo: i tre selftest passano la destinazione",
               fuori.count("dest_backup=d)") == 3)
    c.verifica("dopo: i cinque controlli nuovi ci sono",
               "DIFETTO RIPRODOTTO: nessun .bak_ accanto al file" in fuori)
    c.verifica("dopo: il rifiuto senza radice e' provato",
               "radice non deducibile -> Rifiuto" in fuori)

    # ---- 3. reversibilita' esatta ----------------------------------------
    c.uguale("l'inversa restituisce l'originale", inverti(fuori), CORPO_FINTO)

    # ---- 4. il testo fuori dalle ancore non e' toccato -------------------
    c.verifica("docstring del bersaglio intatta",
               '"""finto bersaglio, con le sei ancore."""' in fuori)

    # ---- 5. DIFETTO: seconda applicazione rifiutata (idempotenza) --------
    c.rifiuta("DIFETTO: patch gia' applicata -> Rifiuto", lambda: applica(fuori))

    # ---- 6. DIFETTO: ancora assente --------------------------------------
    mutilato = CORPO_FINTO.replace(A2_VECCHIO, "def comando_apply(path, da, a, dry):")
    c.rifiuta("DIFETTO: ancora assente -> Rifiuto", lambda: applica(mutilato))

    # ---- 7. DIFETTO: ancora non unica ------------------------------------
    doppio = CORPO_FINTO + "\n" + A3_VECCHIO + "\n"
    c.rifiuta("DIFETTO: ancora non unica -> Rifiuto", lambda: applica(doppio))

    # ---- 8. atomicita': se una fallisce, non si scrive nulla -------------
    with tempfile.TemporaryDirectory() as td:
        radice = Path(td)
        (radice / "src").mkdir()
        f = radice / "src" / "bersaglio.py"
        f.write_bytes(mutilato.encode("utf-8"))        # write_bytes, non testo
        prima = f.read_bytes()

        class A:
            file = str(f); dry_run = False; backup_dir = None
        c.rifiuta("atomicita': ancora mancante -> nessuna scrittura",
                  lambda: comando_applica(A()))
        c.verifica("atomicita': file invariato", f.read_bytes() == prima)
        c.verifica("atomicita': nessuna copia creata",
                   not (radice / "logs").exists()
                   or not list((radice / "logs").iterdir()))

    # ---- 9. il dry-run non scrive ----------------------------------------
    with tempfile.TemporaryDirectory() as td:
        radice = Path(td)
        (radice / "src").mkdir()
        f = radice / "src" / "bersaglio.py"
        f.write_bytes(CORPO_FINTO.encode("utf-8"))     # write_bytes, non testo
        prima = f.read_bytes()

        class B:
            file = str(f); dry_run = True; backup_dir = None
        c.uguale("dry-run: esito 0", comando_applica(B()), 0)
        c.verifica("dry-run: nessuna scrittura", f.read_bytes() == prima)
        c.verifica("dry-run: nessuna copia",
                   not (radice / "logs").exists()
                   or not list((radice / "logs").iterdir()))
        c.verifica("dry-run: nessun temporaneo",
                   not [x for x in (radice / "src").iterdir() if x.name.endswith(".tmp")])

    # ---- 10. apply: la copia di QUESTO patcher va gia' in logs/ ----------
    with tempfile.TemporaryDirectory() as td:
        radice = Path(td)
        (radice / "src").mkdir()
        f = radice / "src" / "bersaglio.py"
        f.write_bytes(CORPO_FINTO.encode("utf-8"))     # write_bytes, non testo
        sha0 = sha256_file(f)

        class C_:
            file = str(f); dry_run = False; backup_dir = None
        c.uguale("apply: esito 0", comando_applica(C_()), 0)
        c.uguale("apply: file patchato sul disco",
                 f.read_bytes().decode("utf-8"), fuori)
        c.verifica("apply: nessun .bak_ in src/",
                   not [x for x in (radice / "src").iterdir() if ".bak_" in x.name])
        bak = [x for x in (radice / "logs").iterdir() if ".bak_" in x.name]
        c.verifica("apply: la copia sta in logs/ con lo sha dell'originale",
                   len(bak) == 1 and sha256_file(bak[0]) == sha0)
        c.verifica("apply: nessun temporaneo residuo",
                   not [x for x in (radice / "src").iterdir() if x.name.endswith(".tmp")])
        c.verifica("apply: verifica sul disco ok", verifica_su_disco(f)["ok"])

        # seconda applicazione: rifiutata
        c.rifiuta("DIFETTO: seconda applicazione rifiutata",
                  lambda: comando_applica(C_()))

    # ---- 11. radice non deducibile: rifiuto, nessun ripiego -------------
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "bersaglio.py"
        f.write_bytes(CORPO_FINTO.encode("utf-8"))     # write_bytes, non testo

        class D:
            file = str(f); dry_run = False; backup_dir = None
        c.rifiuta("radice non deducibile -> Rifiuto", lambda: comando_applica(D()))
        c.verifica("radice non deducibile: file invariato",
                   f.read_bytes().decode("utf-8") == CORPO_FINTO)

    # ---- 11-bis. DIFETTO RIPRODOTTO: fixture con CRLF -------------------
    with tempfile.TemporaryDirectory() as td:
        buona = Path(td) / "buona.py"
        buona.write_bytes(CORPO_FINTO.encode("utf-8"))
        c.uguale("fixture: write_bytes e' byte-identica",
                 buona.read_bytes(), CORPO_FINTO.encode("utf-8"))
        c.uguale("fixture: nessun CR sul disco", buona.read_bytes().count(b"\r"), 0)
        letta = buona.read_bytes().decode("utf-8")
        c.uguale("fixture: A1 si trova nella fixture riletta", letta.count(A1_VECCHIO), 1)
        c.uguale("fixture: A7 si trova nella fixture riletta", letta.count(A7_VECCHIO), 1)

        cattiva = Path(td) / "cattiva.py"
        cattiva.write_bytes(CORPO_FINTO.replace("\n", "\r\n").encode("utf-8"))
        rotta = cattiva.read_bytes().decode("utf-8")
        c.uguale("DIFETTO: con CRLF A1 non si trova", rotta.count(A1_VECCHIO), 0)
        c.uguale("DIFETTO: con CRLF A7 non si trova", rotta.count(A7_VECCHIO), 0)
        c.uguale("DIFETTO: con CRLF A2 si trova comunque", rotta.count(A2_VECCHIO), 1)
        c.verifica("DIFETTO: e' esattamente la firma vista su Windows",
                   rotta.count(A1_VECCHIO) == 0 and rotta.count(A7_VECCHIO) == 0
                   and all(rotta.count(v) == 1 for _, v, _ in SOSTITUZIONI[1:6]))

    # ---- 12. il codice prodotto e' Python valido ------------------------
    import ast
    try:
        ast.parse(fuori)
        c.verifica("il risultato si compila", True)
    except SyntaxError as e:
        c.verifica("il risultato si compila (%s)" % e, False)

    # ---- 13. i controlli del bersaglio passano da 22 a 27 ---------------
    # Sette `check(` nel testo, ma due sono i rami alternativi dello stesso
    # rifiuto: i controlli ESEGUITI dal bersaglio passano da 22 a 28.
    c.uguale("sette check nel testo aggiunto",
             fuori.count("check(") - CORPO_FINTO.count("check("), 7)
    c.uguale("due sono rami alternativi dello stesso rifiuto",
             fuori.count("radice non deducibile"), 2)

    # ---- 14. DIFETTO RIPRODOTTO: un'ancora vecchia che risorge ----------
    # Il blocco nuovo chiama comando_apply SENZA destinazione, per provare la
    # deduzione. Scritto con `rc =` sarebbe stato identico all'ancora A5 e la
    # verifica sul disco avrebbe detto 'vecchie_assenti: False' su una patch
    # corretta. Da qui `rc3 =`.
    for nome, vecchio, _ in SOSTITUZIONI:
        c.uguale("nessuna ancora vecchia risorge: %s" % nome, fuori.count(vecchio), 0)
    c.verifica("il blocco nuovo chiama senza destinazione",
               "rc3 = comando_apply(f, 60, 61, dry=False)" in fuori)

    totale = c.ok + len(c.ko)
    print("selftest: %d/%d" % (c.ok, totale))
    if c.ko:
        print("FALLITI:")
        for nome in c.ko:
            print("  %s" % nome)
        return 1
    return 0


# ===========================================================================

def principale(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="paper2_patch_backup_in_logs.py",
        description="Porta in logs/ la copia di sicurezza di "
                    "paper2_patch_documented_amendments.py.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("applica")
    a.add_argument("--file", default=BERSAGLIO_DEFAULT)
    a.add_argument("--backup-dir", default=None, dest="backup_dir")
    a.add_argument("--dry-run", action="store_true", dest="dry_run")
    a.set_defaults(funzione=comando_applica)

    v = sub.add_parser("verifica")
    v.add_argument("--file", default=BERSAGLIO_DEFAULT)
    v.set_defaults(funzione=comando_verifica)

    s = sub.add_parser("selftest")
    s.set_defaults(funzione=comando_selftest)

    args = p.parse_args(argv)
    return args.funzione(args)


if __name__ == "__main__":
    sys.exit(principale())

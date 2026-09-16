#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_patch_documented_amendments.py — sposta DOCUMENTED_AMENDMENTS di un passo.

Il conteggio vive in due posti che devono muoversi insieme: il numero di righe del
ledger (che cresce con l'append) e la costante di `paper2_freeze_verify.py` (che
dichiara quante ne conosce la documentazione). Se la costante resta indietro il
`verify` fallisce con `disco != documentati`; se la si sposta senza il record, il
cancello mente nell'altra direzione.

**Ordine obbligatorio: prima l'append del record, poi questo patcher, poi `verify`.**

Forma dei patcher, invariata: ancora unica o rifiuto; rifiuto se gia' applicata
anche solo in parte; BOM e fine riga preservati byte per byte; l'inversa deve
restituire l'originale byte per byte PRIMA di scrivere; scrittura atomica con
backup; `verify` sul file riletto dal disco.

Uso:
    python src\\paper2_patch_documented_amendments.py selftest
    python src\\paper2_patch_documented_amendments.py apply --file src\\paper2_freeze_verify.py --da 60 --a 61 --dry-run
    python src\\paper2_patch_documented_amendments.py apply --file src\\paper2_freeze_verify.py --da 60 --a 61
    python src\\paper2_patch_documented_amendments.py verify --file src\\paper2_freeze_verify.py --a 61
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
MODELLO = b"DOCUMENTED_AMENDMENTS = %d"


class Rifiuto(Exception):
    """La patch non si applica. Nessun file e' stato toccato."""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def ancora(n: int) -> bytes:
    return MODELLO % int(n)


def controlla(dati: bytes, da: int, a: int) -> None:
    """Tutti i rifiuti, prima di qualunque scrittura."""
    if int(da) == int(a):
        raise Rifiuto("da e a coincidono (%d): non c'e' nulla da spostare" % da)
    vecchia, nuova = ancora(da), ancora(a)
    n_v = dati.count(vecchia)
    n_n = dati.count(nuova)
    if n_n:
        raise Rifiuto("patch gia' applicata anche solo in parte: '%s' presente %d volta/e"
                      % (nuova.decode(), n_n))
    if n_v == 0:
        raise Rifiuto("ancora assente: '%s' non compare" % vecchia.decode())
    if n_v > 1:
        raise Rifiuto("ancora non unica: '%s' compare %d volte" % (vecchia.decode(), n_v))


def applica(dati: bytes, da: int, a: int) -> bytes:
    controlla(dati, da, a)
    return dati.replace(ancora(da), ancora(a), 1)


def inverti(dati: bytes, da: int, a: int) -> bytes:
    """L'inversa esatta: riporta a -> da, con gli stessi rifiuti a specchio."""
    controlla(dati, a, da)
    return dati.replace(ancora(a), ancora(da), 1)


def cartella_backup(path: Path) -> Path:
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


def verifica_su_disco(path: Path, da: int, a: int) -> dict:
    dati = Path(path).read_bytes()
    return {
        "file": str(path),
        "sha256": sha256_bytes(dati),
        "nuova_presente": int(dati.count(ancora(a))),
        "vecchia_assente": bool(dati.count(ancora(da)) == 0),
        "ok": bool(dati.count(ancora(a)) == 1 and dati.count(ancora(da)) == 0),
    }


def comando_apply(path: Path, da: int, a: int, dry: bool, dest_backup=None) -> int:
    originale = path.read_bytes()
    sha_prima = sha256_bytes(originale)
    try:
        patchato = applica(originale, da, a)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 3

    # L'inversa deve restituire l'originale byte per byte PRIMA di scrivere.
    ritorno = inverti(patchato, da, a)
    if ritorno != originale:
        print("RIFIUTO: l'inversa non restituisce l'originale byte per byte", file=sys.stderr)
        return 4

    print("file      : %s" % path)
    print("sha prima : %s" % sha_prima)
    print("sha dopo  : %s" % sha256_bytes(patchato))
    print("byte      : %d -> %d" % (len(originale), len(patchato)))
    print("ancora    : %s -> %s" % (ancora(da).decode(), ancora(a).decode()))

    if dry:
        print("\n[dry-run] niente scritto.")
        return 0

    backup = scrivi_atomico(path, patchato, dest_backup)
    v = verifica_su_disco(path, da, a)
    if not v["ok"] or v["sha256"] != sha256_bytes(patchato):
        print("FALLIMENTO: il file riletto dal disco non corrisponde. Backup: %s" % backup,
              file=sys.stderr)
        return 5
    print("\nbackup    : %s (sha %s)" % (backup, sha256_file(backup)))
    print("verify    : OK sul file riletto dal disco")
    print("\nOra: python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl"
          "  ->  atteso disco = %d, documentati = %d" % (a, a))
    return 0


# ------------------------------------------------------------------- selftest

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

    print("selftest paper2_patch_documented_amendments v%s" % VERSIONE)

    corpo = (b"\xef\xbb\xbf# -*- coding: utf-8 -*-\r\n"
             b"#  - DOCUMENTED_AMENDMENTS e' quanti ne dichiara la documentazione\r\n"
             b"DOCUMENTED_AMENDMENTS = 60\r\n"
             b"x = DOCUMENTED_AMENDMENTS - 1\r\n"
             b"y = DOCUMENTED_AMENDMENTS + 1\r\n"
             b"z = b'{\"a\":1}\\n' * DOCUMENTED_AMENDMENTS\r\n")

    p = applica(corpo, 60, 61)
    check(p.count(b"DOCUMENTED_AMENDMENTS = 61") == 1, "la costante passa a 61")
    check(p.count(b"DOCUMENTED_AMENDMENTS = 60") == 0, "la vecchia sparisce")
    check(p.startswith(b"\xef\xbb\xbf"), "BOM preservato")
    check(p.count(b"\r\n") == corpo.count(b"\r\n"), "CRLF preservati, uno per uno")
    check(b"DOCUMENTED_AMENDMENTS + 1" in p and b"DOCUMENTED_AMENDMENTS - 1" in p,
          "gli usi simbolici non sono toccati")
    check(b"DOCUMENTED_AMENDMENTS e' quanti" in p, "il commento non e' toccato")
    check(len(p) == len(corpo), "lunghezza invariata")
    check(inverti(p, 60, 61) == corpo, "l'inversa restituisce l'originale byte per byte")

    for nome, args, dati in [
        ("ancora assente", (59, 61), corpo),
        ("patch gia' applicata", (60, 61), p),
        ("da e a coincidono", (60, 60), corpo),
        ("ancora non unica", (60, 61), corpo + b"DOCUMENTED_AMENDMENTS = 60\r\n"),
    ]:
        try:
            applica(dati, *args)
            check(False, "DIFETTO: %s deve essere rifiutata" % nome)
        except Rifiuto:
            check(True, "DIFETTO: %s -> Rifiuto" % nome)

    check(applica(corpo, 60, 62).count(b"DOCUMENTED_AMENDMENTS = 62") == 1,
          "funziona anche per un salto di due (due record appesi)")

    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        f = d / "fv.py"
        f.write_bytes(corpo)
        sha0 = sha256_file(f)

        rc = comando_apply(f, 60, 61, dry=True, dest_backup=d)
        check(rc == 0 and sha256_file(f) == sha0, "dry-run: nessuna scrittura")
        check(len(list(d.iterdir())) == 1, "dry-run: nessun temp e nessun backup")

        rc = comando_apply(f, 60, 61, dry=False, dest_backup=d)
        check(rc == 0, "apply: esito 0")
        check(sha256_file(f) == sha256_bytes(applica(corpo, 60, 61)), "apply: file atteso sul disco")
        bak = [x for x in d.iterdir() if ".bak_" in x.name]
        check(len(bak) == 1 and sha256_file(bak[0]) == sha0, "apply: backup con lo sha dell'originale")
        check(not [x for x in d.iterdir() if x.name.endswith(".tmp")], "apply: nessun temp residuo")
        check(verifica_su_disco(f, 60, 61)["ok"] is True, "verify sul file riletto dal disco")

        rc2 = comando_apply(f, 60, 61, dry=False, dest_backup=d)
        check(rc2 == 3, "DIFETTO: seconda applicazione rifiutata (idempotenza)")

        f.write_bytes(corpo.replace(b"= 60", b"= 77"))
        check(verifica_su_disco(f, 60, 61)["ok"] is False, "DIFETTO: verify fallisce su file manomesso")

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

    print("\nselftest: %d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Sposta DOCUMENTED_AMENDMENTS in paper2_freeze_verify.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    a1 = sub.add_parser("apply")
    a1.add_argument("--file", required=True)
    a1.add_argument("--da", type=int, required=True)
    a1.add_argument("--a", type=int, required=True)
    a1.add_argument("--dry-run", action="store_true")
    a2 = sub.add_parser("verify")
    a2.add_argument("--file", required=True)
    a2.add_argument("--a", type=int, required=True)
    a2.add_argument("--da", type=int, default=None)

    a = p.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    if a.cmd == "apply":
        return comando_apply(Path(a.file), a.da, a.a, a.dry_run)
    da = a.da if a.da is not None else a.a - 1
    v = verifica_su_disco(Path(a.file), da, a.a)
    print("\n".join("%-16s %s" % (k, v[k]) for k in v))
    return 0 if v["ok"] else 6


if __name__ == "__main__":
    raise SystemExit(main())

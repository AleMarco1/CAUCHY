#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_patch_portata_censimento.py — la portata del censimento, detta per intero.

PERCHE' ESISTE
    La chiusura del §3-bis, scritta dal patcher del record 65, dice che «gli altri siti
    sono ipotesi di pilota, cancelli di formato e diagnosi». Omette la categoria piu'
    numerosa: i siti il cui verdetto E' nel registro, ma per ITEM e non per nome di file —
    phase3_preflight (record 13, il gruppo A1), compD_partialcorr (43 e 48),
    compD_nonlinear (63), intersezione_verdetto (25, il gruppo Ab1), fase3_budget, e
    ripattern_analisi (item 3.2d, record 44, 45 e 55).

    Quella frase e' la dichiarazione di PORTATA del censimento, ed e' lo stesso posto in
    cui il record 60 aveva detto «nessuna falsificazione e' stata mancata» senza la sua
    portata attaccata. Una portata dichiarata male e' peggio di una non dichiarata.

CHE COSA NON FA
    Non emenda il record 65: la sua affermazione — i due candidati rimasti non hanno un
    record — e' stata verificata per contenuto, e regge. Nessun record contiene
    l'intervallo [0.70, 0.82] con |z| > 3 di SGC_PRED, e nessuno contiene 0.005, 0.99,
    frac_below, 0.078 o 0.178 della scalinata di item12b. La parola «scalinata» compare in
    zero record.
    Non tocca i conteggi, i gruppi, la checklist o lo stato.

USO
    python src\\paper2_patch_portata_censimento.py selftest
    python src\\paper2_patch_portata_censimento.py apply --dir papers\\paper2 --dry-run
    python src\\paper2_patch_portata_censimento.py apply --dir papers\\paper2 --backup-dir logs
    python src\\paper2_patch_portata_censimento.py verifica --dir papers\\paper2
"""

import argparse
import hashlib
import os
import re
import sys
import tempfile

REV = "paper2_patch_portata_censimento rev.1"
SMENTITE = "paper2_5_5_smentite.md"

# lo sha del file DOPO il patcher del record 65, verificato su due macchine
SHA_ATTESO = "6be11773fff9be425e7bab6ca75de9890e822b90ff9b2345571ad3fefafb1695"

VECCHIO = """**Restano da classificare tre candidati**, tutti senza record nel registro: le due soglie di
`paper2_gate53.py` — frazione spettrale in [0.70, 0.82] e |*z*| > 3, dichiarate prima del run in
`SGC_PRED` — e l'escursione < 0.005 di `paper2_item12b_wbar.py`. Gli altri siti sono ipotesi di
pilota, cancelli di formato e diagnosi, e per metà appartengono a M26 e al Paper 1, non al Paper 2.
"""

NUOVO = """**Restano da classificare tre candidati**, tutti senza record nel registro: le due soglie di
`paper2_gate53.py` — frazione spettrale in [0.70, 0.82] e |*z*| > 3, dichiarate prima del run in
`SGC_PRED` — e l'escursione < 0.005 di `paper2_item12b_wbar.py`. La verifica è per **item**, non
per nome di file: i record citano l'item, e una ricerca sul nome dello script dà zero anche per
verdetti che nel registro ci sono. Per questi due si è cercato il contenuto della soglia, e non
c'è: nessun record contiene l'intervallo di `SGC_PRED`, nessuno contiene 0.005, 0.99 o
`frac_below`, e la parola «scalinata» compare in zero record.

Gli altri siti si dividono in due. **Verdetti emessi fuori dal ledger e risolti dentro, per item:**
`paper2_phase3_preflight.py` (record 13, la voce A1), `paper2_compD_partialcorr.py` (43 e 48),
`paper2_compD_nonlinear.py` (63), `paper2_intersezione_verdetto.py` (25, la voce Ab1),
`paper2_fase3_budget.py`, e `paper2_ripattern_analisi.py` — item 3.2d, record 44, 45 e 55, che
riporta −15.70 ± 18.75 al livello *k* = 0 contro la soglia dichiarata di 55. **E il resto:**
ipotesi di pilota, cancelli di formato e diagnosi, per metà appartenenti a M26 e al Paper 1, non al
Paper 2.
"""


class Rifiuto(Exception):
    pass


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def leggi(path):
    if not os.path.isfile(path):
        raise Rifiuto("file assente: %s" % path)
    with open(path, "rb") as fh:
        return fh.read()


def prepara(cartella, sha_atteso=None):
    path = os.path.join(cartella, SMENTITE)
    raw = leggi(path)
    sha = sha256_bytes(raw)
    atteso = sha_atteso or SHA_ATTESO
    if sha != atteso:
        raise Rifiuto(
            "%s: sha256 %s..., atteso %s.... L'ancora è costruita sul file COME LO HA "
            "LASCIATO il patcher del record 65. Se il file è diverso, l'ancora è sbagliata."
            % (SMENTITE, sha[:16], atteso[:16]))
    testo = raw.decode("utf-8")
    n = testo.count(VECCHIO)
    if n == 0:
        raise Rifiuto("ancora non trovata: la chiusura del §3-bis non è quella attesa")
    if n > 1:
        raise Rifiuto("ancora presente %d volte, non è univoca" % n)
    if NUOVO in testo:
        raise Rifiuto("il testo nuovo c'è già: patcher già applicato")
    nuovo_testo = testo.replace(VECCHIO, NUOVO, 1)
    return path, raw, nuovo_testo.encode("utf-8")


def controlli(nuovi_byte):
    t = nuovi_byte.decode("utf-8")
    return [
        (len(re.findall(r"^\|\s*A(\d+)\s*\|", t, re.M)) == 12, "il gruppo A ha ancora 12 righe"),
        (len(re.findall(r"^\|\s*Ab(\d+)\s*\|", t, re.M)) == 1, "il gruppo A-bis ha ancora una riga"),
        (len(re.findall(r"^\|\s*B(\d+)\s*\|", t, re.M)) == 5, "il gruppo B ha ancora cinque righe"),
        (len(re.findall(r"^\|\s*Q(\d)\s*\|", t, re.M)) == 5, "le Q nella 3-bis sono ancora cinque"),
        ("record 44, 45 e 55" in t, "i record che risolvono 3.2d sono nominati"),
        ("per **item**" in t, "la portata dice che la verifica è per item"),
        ("tre candidati" in t, "i tre candidati restano dichiarati"),
        (t.count("Restano da classificare") == 1, "la frase compare una volta sola"),
    ]


def cmd_apply(a):
    try:
        path, prima, dopo = prepara(a.dir, a.sha_atteso)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("=== %s ===" % REV)
    print("  %s   %d byte -> %d byte" % (SMENTITE, len(prima), len(dopo)))
    print("      - §3-bis: la portata del censimento, detta per intero")
    esiti = controlli(dopo)
    print("")
    print("  controlli sul risultato:")
    for ok, testo in esiti:
        print("    [%s] %s" % ("ok" if ok else "FALLITO", testo))
    if not all(ok for ok, _t in esiti):
        print("\nESITO: CONTROLLI FALLITI — niente scritto.")
        return 3

    if a.dry_run:
        print("\n[dry-run] niente scritto.")
        return 0

    if a.backup_dir:
        os.makedirs(a.backup_dir, exist_ok=True)
        with open(os.path.join(a.backup_dir, SMENTITE + ".prima_della_portata"), "wb") as fh:
            fh.write(prima)

    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=SMENTITE + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dopo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    raw = leggi(path)
    ok = raw == dopo
    print("")
    print("  [%s] scritto e riletto identico" % ("ok" if ok else "KO"))
    if not ok:
        return 5
    print("")
    print("  Nuovo sha, da riportare nella consegna:")
    print("    %-24s %s  %d byte" % (SMENTITE, sha256_bytes(raw), len(raw)))
    print("")
    print("ESITO: CLEAN")
    return 0


def cmd_verifica(a):
    print("=== %s — verifica ===" % REV)
    try:
        testo = leggi(os.path.join(a.dir, SMENTITE)).decode("utf-8")
    except Rifiuto as e:
        print("  [KO] %s" % e)
        print("\nESITO: FALLITO")
        return 1
    c_new, c_old = testo.count(NUOVO), testo.count(VECCHIO)
    ok = c_new == 1 and c_old == 0
    print("  [%s] %-24s §3-bis: portata per intero  (nuovo x%d, vecchio x%d)"
          % ("ok" if ok else "KO", SMENTITE, c_new, c_old))
    for c, t in controlli(testo.encode("utf-8")):
        ok = ok and c
        print("  [%s] %s" % ("ok" if c else "KO", t))
    print("")
    print("ESITO: %s" % ("CLEAN" if ok else "FALLITO"))
    return 0 if ok else 1


def cmd_selftest(a=None):
    import shutil
    esiti = []

    def check(nome, cond):
        esiti.append((bool(cond), nome))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", nome))

    class A(object):
        dry_run = False
        backup_dir = None
        sha_atteso = None

    td = tempfile.mkdtemp(prefix="portata_")
    try:
        cart = os.path.join(td, "papers")
        os.makedirs(cart)
        path = os.path.join(cart, SMENTITE)

        corpo = ("# finto\n\n"
                 + "".join("| A%d | x | y | z | w |\n" % i for i in range(1, 13))
                 + "| Ab1 | x | y | z | w |\n"
                 + "".join("| B%d | x | y | z |\n" % i for i in range(1, 6))
                 + "".join("| Q%d | a | b | c |\n" % i for i in range(1, 6))
                 + "\n" + VECCHIO)

        def scrivi(testo=corpo):
            with open(path, "wb") as fh:
                fh.write(testo.encode("utf-8"))
            return sha256_bytes(testo.encode("utf-8"))

        def args(dry=False, backup=None, sha=None):
            x = A()
            x.dir, x.dry_run, x.backup_dir, x.sha_atteso = cart, dry, backup, sha
            return x

        sha = scrivi()
        prima = leggi(path)
        check("01 dry-run esce con 0", cmd_apply(args(dry=True, sha=sha)) == 0)
        check("02 dry-run non scrive", leggi(path) == prima)
        check("03 apply esce con 0", cmd_apply(args(sha=sha)) == 0)
        t = leggi(path).decode("utf-8")
        check("04 i record che risolvono 3.2d sono nominati", "record 44, 45 e 55" in t)
        check("05 ripattern è dichiarato risolto dentro il registro",
              "paper2_ripattern_analisi.py" in t and "3.2d" in t)
        check("06 la verifica per item è dichiarata", "per **item**" in t)
        check("07 i tre candidati restano", "tre candidati" in t)
        check("08 i gruppi non sono cambiati",
              len(re.findall(r"^\|\s*A(\d+)\s*\|", t, re.M)) == 12
              and len(re.findall(r"^\|\s*B(\d+)\s*\|", t, re.M)) == 5)
        check("09 le cinque Q sono intatte",
              len(re.findall(r"^\|\s*Q(\d)\s*\|", t, re.M)) == 5)
        check("10 il file resta a fine riga LF puro", b"\r\n" not in leggi(path))
        check("11 verifica esce con 0", cmd_verifica(args()) == 0)

        nuovo_sha = sha256_bytes(leggi(path))
        check("12 riapplicare è rifiutato (sha diverso)", cmd_apply(args(sha=sha)) == 2)
        check("13 rifiutato anche con lo sha aggiornato (testo nuovo già presente)",
              cmd_apply(args(sha=nuovo_sha)) == 2)

        scrivi()
        check("14 sha diverso da quello atteso -> rifiuto", cmd_apply(args()) == 2)
        check("15 e il file non è stato toccato", leggi(path) == prima)

        scrivi(corpo.replace(VECCHIO, "una chiusura diversa\n"))
        sha2 = sha256_bytes(leggi(path))
        check("16 ancora assente -> rifiuto", cmd_apply(args(sha=sha2)) == 2)

        sha = scrivi()
        bdir = os.path.join(td, "logs")
        check("17 apply con backup esce con 0", cmd_apply(args(backup=bdir, sha=sha)) == 0)
        check("18 il file precedente è nel backup byte-identico",
              leggi(os.path.join(bdir, SMENTITE + ".prima_della_portata")) == prima)
        check("19 nessun temporaneo lasciato indietro",
              not [x for x in os.listdir(cart) if x.endswith(".tmp")])

        scrivi()
        check("20 verifica esce con 1 su file non ancora patchato", cmd_verifica(args()) == 1)

        check("21 lo sha atteso di default è quello post-record-65",
              SHA_ATTESO == "6be11773fff9be425e7bab6ca75de9890e822b90ff9b2345571ad3fefafb1695")

    finally:
        shutil.rmtree(td, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="paper2_patch_portata_censimento.py",
                                description="Una frase: la portata del censimento del 6.9.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("apply")
    q.add_argument("--dir", default=os.path.join("papers", "paper2"))
    q.add_argument("--backup-dir", default=None)
    q.add_argument("--sha-atteso", default=None,
                   help="solo per il selftest: lo sha del file su cui l'ancora è costruita")
    q.add_argument("--dry-run", action="store_true")
    q.set_defaults(func=cmd_apply)

    q = sub.add_parser("verifica")
    q.add_argument("--dir", default=os.path.join("papers", "paper2"))
    q.set_defaults(func=cmd_verifica)

    q = sub.add_parser("selftest")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_patch_soglie_q5.py — Q5 in SOGLIE, e lo schema del registro a v2.

PERCHE'
    Il dizionario SOGLIE di src/paper2_d6_incertezze.py contiene quattro voci, Q1-Q4. Le
    predizioni dichiarate di D6 sono cinque. Per questo il margine di Q5 non e' mai stato
    calcolato (record 65) e, finche' resta a quattro, la ripetizione su ensemble v2
    annunciata dal record 1 lo perderebbe di nuovo. Decisione dichiarata dal record 66.

LE CINQUE MODIFICHE
    1. docstring, punto 3: le soglie elencate diventano Q1-Q5;
    2. SOGLIE: voce Q5_sotto_il_tetto, con la soglia presa da CEIL_MEASURED IMPORTATO e non
       scritta come numero — se il tetto cambia, la soglia lo segue invece di restare
       indietro in un secondo posto;
    3. schema del record: v1 -> v2, con accanto una nota che dichiara che cosa cambia e che
       il margine di Q5 e' gia' registrato altrove;
    4. il blocco che costruisce rec["soglie"]: Q5 calcolata sulla STESSA quantita' di Q3 —
       B/ln_di_log10P_come_nel_codice/migliore — con soglia e verso letti da SOGLIE;
    5. la stampa a terminale: la soglia passa da %.2f a %.6f. Con un tetto di
       0.8320530984290949 il vecchio formato stampava «0.83», che e' la stessa
       approssimazione che il record 65 ha gia' dovuto respingere: una predizione e'
       dichiarata su UN valore.

CHE COSA NON CAMBIA
    Nessuna quantita', nessun calcolo, nessuna delle quattro soglie esistenti. Q5 e Q3
    CONDIVIDONO la quantita' e differiscono solo per soglia e verso: e' dichiarato in un
    commento accanto a entrambe, perche' senza quello sembra una duplicazione da ripulire.

UNA COSA CHE IL PATCHER NON PUO' IMPEDIRE, E CHE DICHIARA
    Dopo questa modifica una passata dello strumento produrra' un margine per Q5. Quel
    margine NON e' una seconda misura indipendente: quella e' nel record 66 e in
    results/paper2/q5_margine.jsonl. Se i numeri differiscono, e' una discordanza da
    spiegare, non un secondo risultato. La nota di schema lo scrive dentro ogni record
    prodotto da qui in avanti.

COME VERIFICA
    Dopo aver scritto, ricontrolla che il file si parsi E che si IMPORTI, e che SOGLIE
    contenga cinque voci con la soglia di Q5 uguale a CEIL_MEASURED. Se l'import fallisce,
    RIPRISTINA i byte originali e lo dice: un file di analisi che non si importa e' peggio
    di un file non patchato.

USO
    python src\\paper2_patch_soglie_q5.py selftest
    python src\\paper2_patch_soglie_q5.py apply --file src\\paper2_d6_incertezze.py --dry-run
    python src\\paper2_patch_soglie_q5.py apply --file src\\paper2_d6_incertezze.py --backup-dir logs
    python src\\paper2_patch_soglie_q5.py verifica --file src\\paper2_d6_incertezze.py
"""

import argparse
import ast
import hashlib
import os
import re
import subprocess
import sys
import tempfile

REV = "paper2_patch_soglie_q5 rev.1"
SHA_ATTESO = "478415bfb310be547eac5ea1a0b15c11f5a8127a408ad8e7d658c27c458a43ee"

MODIFICHE = [
    (
        "docstring: le soglie elencate diventano Q1-Q5",
        """  3. LE SOGLIE CON IL LORO MARGINE. Q1, Q2, Q3, Q4 sono predizioni dichiarate con una
     soglia; qui ognuna esce col margine misurato in unita' della propria dispersione.
""",
        """  3. LE SOGLIE CON IL LORO MARGINE. Q1, Q2, Q3, Q4 e Q5 sono predizioni dichiarate con
     una soglia; qui ognuna esce col margine misurato in unita' della propria dispersione.
""",
    ),
    (
        "SOGLIE: la voce Q5_sotto_il_tetto",
        """    "Q4_meta_divario": {"soglia": 0.50, "verso": ">", "quantita": "C_frac_parametri"},
}
""",
        """    "Q4_meta_divario": {"soglia": 0.50, "verso": ">", "quantita": "C_frac_parametri"},
    # Q5 CONDIVIDE la quantita' di Q3 e differisce solo per soglia e verso: non e' una
    # duplicazione da ripulire. La soglia non e' scritta qui come numero, e' CEIL_MEASURED
    # importato: se il tetto cambia, la soglia lo segue invece di restare indietro.
    "Q5_sotto_il_tetto": {"soglia": CEIL_MEASURED, "verso": "<", "quantita": "B_best"},
}
""",
    ),
    (
        "schema del record: v1 -> v2, con la nota di cosa cambia",
        """        "schema": "paper2_d6_incertezze_v1", "versione": VERSIONE, "region": region, "n": n,
""",
        """        "schema": "paper2_d6_incertezze_v2", "versione": VERSIONE, "region": region, "n": n,
        "nota_schema_v2": (
            "v2 differisce da v1 in un solo punto: rec['soglie'] contiene anche "
            "Q5_sotto_il_tetto, la quinta predizione dichiarata di D6, che v1 non calcolava "
            "perche' SOGLIE ne conteneva quattro. Il margine di Q5 e' GIA' registrato dal "
            "record 66 del ledger e da results/paper2/q5_margine.jsonl: un valore prodotto "
            "qui NON e' una seconda misura indipendente, e se differisce da quello e' una "
            "discordanza da spiegare, non un secondo risultato. Tutto il resto e' invariato."),
""",
    ),
    (
        "rec['soglie']: Q5 sulla stessa quantita' di Q3",
        """        mg = rec["B"]["ln_di_log10P_come_nel_codice"]["migliore"]
        q["Q3_B_sopra_mezzo"] = margine(mg["r2cv_media"], mg["r2cv_sd"], 0.50, ">")
""",
        """        mg = rec["B"]["ln_di_log10P_come_nel_codice"]["migliore"]
        q["Q3_B_sopra_mezzo"] = margine(mg["r2cv_media"], mg["r2cv_sd"], 0.50, ">")
        # STESSA quantita' di Q3, soglia e verso diversi: Q5 chiede che resti SOTTO il
        # tetto dei predittori misurati. Soglia e verso si leggono da SOGLIE, non si
        # riscrivono qui.
        q["Q5_sotto_il_tetto"] = margine(mg["r2cv_media"], mg["r2cv_sd"],
                                         SOGLIE["Q5_sotto_il_tetto"]["soglia"],
                                         SOGLIE["Q5_sotto_il_tetto"]["verso"])
""",
    ),
    (
        "stampa: la soglia da %.2f a %.6f",
        """        print("  %-20s %s  %.4f contro %.2f  -> %.1f sigma  %s"
""",
        """        print("  %-20s %s  %.4f contro %.6f  -> %.1f sigma  %s"
""",
    ),
]


class Rifiuto(Exception):
    pass


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def leggi(path):
    if not os.path.isfile(path):
        raise Rifiuto("file assente: %s" % path)
    with open(path, "rb") as fh:
        return fh.read()


def prepara(path, sha_atteso=None):
    raw = leggi(path)
    sha = sha256_bytes(raw)
    atteso = sha_atteso or SHA_ATTESO
    if sha != atteso:
        raise Rifiuto("%s: sha256 %s..., atteso %s.... Le ancore sono costruite su quel "
                      "file; su un altro sarebbero ancore sbagliate."
                      % (os.path.basename(path), sha[:16], atteso[:16]))
    testo = raw.decode("utf-8")
    fatte = []
    for etichetta, vecchio, nuovo in MODIFICHE:
        n = testo.count(vecchio)
        if n == 0:
            raise Rifiuto("ancora non trovata — %s" % etichetta)
        if n > 1:
            raise Rifiuto("ancora presente %d volte, non e' univoca — %s" % (n, etichetta))
        if nuovo in testo:
            raise Rifiuto("il testo nuovo c'e' gia' — %s. Patcher gia' applicato." % etichetta)
        testo = testo.replace(vecchio, nuovo, 1)
        fatte.append(etichetta)
    return raw, testo.encode("utf-8"), fatte


def controlli_statici(nuovi):
    t = nuovi.decode("utf-8")
    esiti = []
    try:
        ast.parse(t)
        esiti.append((True, "il file si parsa"))
    except SyntaxError as e:
        esiti.append((False, "il file NON si parsa: %s" % e))
        return esiti
    m = re.search(r"^SOGLIE\s*=\s*\{(.*?)^\}", t, re.M | re.S)
    voci = sorted(set(re.findall(r'"(Q\d)[^"]*"\s*:', m.group(1)))) if m else []
    esiti.append((voci == ["Q1", "Q2", "Q3", "Q4", "Q5"],
                  "SOGLIE ha cinque voci: %s" % ", ".join(voci)))
    esiti.append(('"soglia": CEIL_MEASURED' in t,
                  "la soglia di Q5 e' CEIL_MEASURED, non un numero scritto a mano"))
    esiti.append(("0.832" not in m.group(1) if m else False,
                  "nessun 0.832 cablato dentro SOGLIE"))
    esiti.append(('"paper2_d6_incertezze_v2"' in t
                  and '"paper2_d6_incertezze_v1"' not in t,
                  "lo schema e' v2 e il v1 non compare piu'"))
    esiti.append(("nota_schema_v2" in t, "la nota che dichiara il cambio c'e'"))
    esiti.append(("una seconda misura indipendente" in t,
                  "la nota dice che un valore prodotto qui non e' una misura nuova"))
    esiti.append((t.count('q["Q5_sotto_il_tetto"]') == 1,
                  "Q5 e' calcolata una volta sola"))
    esiti.append(('SOGLIE["Q5_sotto_il_tetto"]["soglia"]' in t,
                  "il calcolo legge la soglia da SOGLIE invece di riscriverla"))
    esiti.append(("CONDIVIDE la quantita' di Q3" in t and "STESSA quantita' di Q3" in t,
                  "la condivisione della quantita' con Q3 e' dichiarata in entrambi i punti"))
    esiti.append(("contro %.6f" in t and "contro %.2f" not in t,
                  "la stampa non arrotonda piu' la soglia a due decimali"))
    return esiti


def controllo_import(path):
    """Il file patchato deve IMPORTARSI, e SOGLIE deve avere cinque voci coerenti."""
    cartella = os.path.dirname(os.path.abspath(path))
    modulo = os.path.splitext(os.path.basename(path))[0]
    codice = (
        "import sys; sys.path.insert(0, %r)\n"
        "import %s as m\n"
        "assert sorted(m.SOGLIE) == ['Q1_quadrati','Q2_interazioni','Q3_B_sopra_mezzo',"
        "'Q4_meta_divario','Q5_sotto_il_tetto'], sorted(m.SOGLIE)\n"
        "q5 = m.SOGLIE['Q5_sotto_il_tetto']\n"
        "assert q5['soglia'] == m.CEIL_MEASURED, (q5['soglia'], m.CEIL_MEASURED)\n"
        "assert q5['verso'] == '<'\n"
        "assert q5['quantita'] == m.SOGLIE['Q3_B_sopra_mezzo']['quantita']\n"
        "print('IMPORT_OK %%.16f' %% q5['soglia'])\n" % (cartella, modulo))
    p = subprocess.run([sys.executable, "-c", codice], capture_output=True, text=True,
                       cwd=cartella)
    return p.returncode == 0 and "IMPORT_OK" in p.stdout, (p.stdout + p.stderr).strip()


def cmd_apply(a):
    try:
        prima, dopo, fatte = prepara(a.file, a.sha_atteso)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("=== %s ===" % REV)
    print("  file       : %s   %d byte -> %d byte" % (a.file, len(prima), len(dopo)))
    for et in fatte:
        print("      - %s" % et)
    esiti = controlli_statici(dopo)
    print("")
    print("  controlli statici:")
    for ok, testo in esiti:
        print("    [%s] %s" % ("ok" if ok else "FALLITO", testo))
    if not all(ok for ok, _t in esiti):
        print("\nESITO: CONTROLLI FALLITI — niente scritto.")
        return 3

    if a.dry_run:
        print("\n[dry-run] niente scritto. L'import si verifica solo dopo la scrittura.")
        return 0

    if a.backup_dir:
        os.makedirs(a.backup_dir, exist_ok=True)
        with open(os.path.join(a.backup_dir,
                               os.path.basename(a.file) + ".prima_di_q5"), "wb") as fh:
            fh.write(prima)

    d = os.path.dirname(os.path.abspath(a.file))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=os.path.basename(a.file) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(dopo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, a.file)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    ok_imp, uscita = controllo_import(a.file)
    print("")
    print("  controllo di import:")
    for linea in uscita.splitlines()[-6:]:
        print("    %s" % linea)
    if not ok_imp:
        with open(a.file, "wb") as fh:
            fh.write(prima)
        print("")
        print("  [RIPRISTINATO] i byte originali sono stati riscritti: sha256 %s"
              % sha256_bytes(leggi(a.file))[:16] + "...")
        print("ESITO: FALLITO — il file patchato non si importa. Meglio non patchato.")
        return 4
    print("    [ok] si importa, SOGLIE ha cinque voci, la soglia di Q5 e' CEIL_MEASURED")

    print("")
    print("  Nuovo sha, da riportare nella consegna:")
    print("    %-28s %s  %d byte"
          % (os.path.basename(a.file), sha256_bytes(leggi(a.file)), len(dopo)))
    print("")
    print("  Nota: la prossima passata dello strumento scrivera' record con schema v2 e un")
    print("  margine per Q5. Quel margine NON e' una misura nuova: sta nel record 66.")
    print("")
    print("ESITO: CLEAN")
    return 0


def cmd_verifica(a):
    print("=== %s — verifica ===" % REV)
    try:
        testo = leggi(a.file).decode("utf-8")
    except Rifiuto as e:
        print("  [KO] %s" % e)
        print("\nESITO: FALLITO")
        return 1
    tutto = True
    for etichetta, vecchio, nuovo in MODIFICHE:
        c_new, c_old = testo.count(nuovo), testo.count(vecchio)
        additiva = vecchio in nuovo
        ok = c_new == 1 and (additiva or c_old == 0)
        tutto = tutto and ok
        print("  [%s] %-46s (nuovo x%d, vecchio x%d%s)"
              % ("ok" if ok else "KO", etichetta, c_new, c_old,
                 ", additiva" if additiva else ""))
    for ok, t in controlli_statici(testo.encode("utf-8")):
        tutto = tutto and ok
        print("  [%s] %s" % ("ok" if ok else "KO", t))
    ok_imp, uscita = controllo_import(a.file)
    tutto = tutto and ok_imp
    print("  [%s] si importa%s" % ("ok" if ok_imp else "KO",
                                   "" if ok_imp else ": " + uscita.splitlines()[-1:][0]
                                   if uscita else ""))
    print("")
    print("ESITO: %s" % ("CLEAN" if tutto else "FALLITO"))
    return 0 if tutto else 1


# --------------------------------------------------------------------------------------

FINTO = '''"""finto.

  2. qualcosa.
  3. LE SOGLIE CON IL LORO MARGINE. Q1, Q2, Q3, Q4 sono predizioni dichiarate con una
     soglia; qui ognuna esce col margine misurato in unita' della propria dispersione.
  4. altro.
"""
import sys

CEIL_MEASURED = 0.8320530984290949
CEIL_PARAMS = 0.6979988567812268
VERSIONE = "1.0"

SOGLIE = {
    "Q1_quadrati": {"soglia": 0.05, "verso": "<", "quantita": "gain_quad"},
    "Q2_interazioni": {"soglia": 0.03, "verso": "<", "quantita": "gain_int"},
    "Q3_B_sopra_mezzo": {"soglia": 0.50, "verso": ">", "quantita": "B_best"},
    "Q4_meta_divario": {"soglia": 0.50, "verso": ">", "quantita": "C_frac_parametri"},
}


def margine(v, sd, soglia, verso):
    m = (v - soglia) / sd if verso == ">" else (soglia - v) / sd
    return {"valore": v, "sd": sd, "soglia": soglia, "verso": verso,
            "esito": "confermata" if m > 0 else "SMENTITA",
            "margine_in_sigma": m, "decidibile": abs(m) >= 1.0}


def misura(region, n, k, ripetizioni):
    rec = {
        "schema": "paper2_d6_incertezze_v1", "versione": VERSIONE, "region": region, "n": n,
        "ceil_measured": CEIL_MEASURED,
        "B": {"ln_di_log10P_come_nel_codice": {"migliore": {"r2cv_media": 0.3177,
                                                            "r2cv_sd": 0.0073}}},
        "C": {"base_divario_parametri": {"frazione_chiusa": 0.216, "sd": 0.031}},
        "A": {"gain_quad": {"media": 0.0505, "sd_appaiata": 0.0172},
              "gain_int": {"media": 0.0546, "sd_appaiata": 0.0091}},
    }
    q = {}
    q["Q1_quadrati"] = margine(rec["A"]["gain_quad"]["media"], rec["A"]["gain_quad"]["sd_appaiata"],
                               0.05, "<")
    q["Q2_interazioni"] = margine(rec["A"]["gain_int"]["media"], rec["A"]["gain_int"]["sd_appaiata"],
                                  0.03, "<")
    if "B" in rec:
        mg = rec["B"]["ln_di_log10P_come_nel_codice"]["migliore"]
        q["Q3_B_sopra_mezzo"] = margine(mg["r2cv_media"], mg["r2cv_sd"], 0.50, ">")
        cpar = rec["C"]["base_divario_parametri"]
        q["Q4_meta_divario"] = margine(cpar["frazione_chiusa"], cpar["sd"], 0.50, ">")
    rec["soglie"] = q
    return rec


def stampa(rec):
    for nome, d in rec["soglie"].items():
        print("  %-20s %s  %.4f contro %.2f  -> %.1f sigma  %s"
              % (nome, d["esito"], d["valore"], d["soglia"], d["margine_in_sigma"],
                 "" if d["decidibile"] else "<-- NON DECIDIBILE"), file=sys.stderr)
'''


def cmd_selftest(a=None):
    import shutil
    esiti = []

    def check(nome, cond):
        esiti.append((bool(cond), nome))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", nome))

    td = tempfile.mkdtemp(prefix="soglieq5_")
    try:
        f = os.path.join(td, "paper2_d6_incertezze.py")

        class A(object):
            dry_run = False
            backup_dir = None
            sha_atteso = None

        def scrivi(testo=FINTO):
            with open(f, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(testo)
            return sha256_bytes(leggi(f))

        def args(dry=False, backup=None, sha=None):
            x = A()
            x.file, x.dry_run, x.backup_dir, x.sha_atteso = f, dry, backup, sha
            return x

        sha = scrivi()
        prima = leggi(f)
        check("01 dry-run esce con 0", cmd_apply(args(dry=True, sha=sha)) == 0)
        check("02 dry-run non scrive", leggi(f) == prima)
        check("03 apply esce con 0", cmd_apply(args(sha=sha)) == 0)

        t = leggi(f).decode("utf-8")
        check("04 SOGLIE ha cinque voci",
              sorted(set(re.findall(r'"(Q\d)[^"]*"\s*:',
                                    re.search(r"^SOGLIE\s*=\s*\{(.*?)^\}", t,
                                              re.M | re.S).group(1))))
              == ["Q1", "Q2", "Q3", "Q4", "Q5"])
        check("05 lo schema e' v2", '"paper2_d6_incertezze_v2"' in t
              and '"paper2_d6_incertezze_v1"' not in t)
        check("06 la soglia di Q5 non e' un numero scritto a mano",
              '"soglia": CEIL_MEASURED' in t)
        check("07 il calcolo legge soglia e verso da SOGLIE",
              'SOGLIE["Q5_sotto_il_tetto"]["soglia"]' in t
              and 'SOGLIE["Q5_sotto_il_tetto"]["verso"]' in t)
        check("08 la stampa non arrotonda piu' a due decimali",
              "contro %.6f" in t and "contro %.2f" not in t)
        check("09 il file resta a fine riga LF puro", b"\r\n" not in leggi(f))

        # il file patchato si importa e produce davvero Q5
        cod = ("import sys; sys.path.insert(0, %r)\n"
               "import paper2_d6_incertezze as m\n"
               "r = m.misura('NGC', 2000, 5, 20)\n"
               "assert 'Q5_sotto_il_tetto' in r['soglie'], list(r['soglie'])\n"
               "q5 = r['soglie']['Q5_sotto_il_tetto']\n"
               "q3 = r['soglie']['Q3_B_sopra_mezzo']\n"
               "assert q5['soglia'] == m.CEIL_MEASURED\n"
               "assert q5['valore'] == q3['valore']\n"
               "assert q5['esito'] == 'confermata'\n"
               "assert r['schema'] == 'paper2_d6_incertezze_v2'\n"
               "assert 'nota_schema_v2' in r\n"
               "print('OK %%.4f' %% q5['margine_in_sigma'])\n" % td)
        p = subprocess.run([sys.executable, "-c", cod], capture_output=True, text=True)
        check("10 il file patchato si importa e calcola Q5", p.returncode == 0)
        check("11 Q5 usa lo stesso valore di Q3, con soglia e verso diversi",
              "OK " in p.stdout)
        check("12 e il record prodotto ha schema v2 e la nota", p.returncode == 0)

        check("13 verifica esce con 0", cmd_verifica(args()) == 0)
        check("14 riapplicare e' rifiutato", cmd_apply(args(sha=sha)) == 2)

        scrivi()
        check("15 sha diverso da quello atteso -> rifiuto", cmd_apply(args()) == 2)
        check("16 e il file non e' stato toccato", leggi(f) == prima)

        rotto = FINTO.replace('    "Q4_meta_divario": {"soglia": 0.50, "verso": ">", '
                              '"quantita": "C_frac_parametri"},\n}\n', "}\n")
        sha_r = scrivi(rotto)
        check("17 ancora mancante -> rifiuto", cmd_apply(args(sha=sha_r)) == 2)

        # se il patch producesse un file non importabile, si ripristina
        guasto = FINTO.replace("CEIL_MEASURED = 0.8320530984290949",
                               "del_CEIL = 1  # CEIL_MEASURED sparito")
        guasto = guasto.replace("CEIL_PARAMS", "CEIL_MEASURED_ALTRO")
        sha_g = scrivi(guasto)
        prima_g = leggi(f)
        rc = cmd_apply(args(sha=sha_g))
        check("18 un file che dopo il patch non si importa -> esito 4", rc == 4)
        check("19 e i byte originali sono stati RIPRISTINATI", leggi(f) == prima_g)

        sha = scrivi()
        bdir = os.path.join(td, "logs")
        check("20 apply con backup esce con 0",
              cmd_apply(args(backup=bdir, sha=sha)) == 0)
        check("21 il file precedente e' nel backup byte-identico",
              leggi(os.path.join(bdir, "paper2_d6_incertezze.py.prima_di_q5")) == prima)
        check("22 nessun temporaneo lasciato indietro",
              not [x for x in os.listdir(td) if x.endswith(".tmp")])

        scrivi()
        check("23 verifica esce con 1 su file non patchato", cmd_verifica(args()) == 1)
        check("24 lo sha atteso di default e' quello del file del 13 set",
              SHA_ATTESO ==
              "478415bfb310be547eac5ea1a0b15c11f5a8127a408ad8e7d658c27c458a43ee")

    finally:
        shutil.rmtree(td, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="paper2_patch_soglie_q5.py",
                                description="Q5 in SOGLIE e schema del registro a v2.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("apply")
    q.add_argument("--file", default=os.path.join("src", "paper2_d6_incertezze.py"))
    q.add_argument("--backup-dir", default=None)
    q.add_argument("--sha-atteso", default=None, help="solo per il selftest")
    q.add_argument("--dry-run", action="store_true")
    q.set_defaults(func=cmd_apply)

    q = sub.add_parser("verifica")
    q.add_argument("--file", default=os.path.join("src", "paper2_d6_incertezze.py"))
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

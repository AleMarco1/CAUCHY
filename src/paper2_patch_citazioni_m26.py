#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_citazioni_m26.py

Due file citano M26 al PRESENTE con numeri che la revisione R1 ha corretto.
E' lo stesso difetto in due posti, e va riparato in modo diverso nei due,
perche' le due costanti hanno RUOLI diversi.

  src/paper1_rev_n6_fkp.py, docstring
      Cita «M26 Tabella 1 mostra gia' che pesare i mock ... sposta la media di
      ~600 generatori ALLONTANANDOLA dai dati» come MOTIVAZIONE del lavoro. La
      riga e' corretta in R1, che oggi porta -78.0 +/- 8.0 «towards data»: e'
      proprio il risultato che questo script ha prodotto. La motivazione va
      messa al passato.
      (Il patcher paper2_patch_n6_m26.py aveva gia' tolto la costante e la
      logica di confronto, ma i suoi controlli cercavano M26_TAB1_SHIFT,
      «direzione OPPOSTA» e «NO - da chiarire»: nessuno dei tre e' in quel
      paragrafo, quindi la verifica e' passata mentre la prosa restava. E'
      stato controllato il codice e non il testo.)

  src/paper1_rev_m1_cosmo_response.py, riga ~322
      Stampa «M26 riga 735 riporta (su n=200 contaminato): Om +0.45, s8 +0.29,
      w0 -0.03». R1 non porta piu' quei numeri: le correlazioni sono rifatte
      sui 2000 e danno Om +0.154, s8 +0.182, n_s +0.376.
      MA il VALORE resta valido: e' il bersaglio di riproduzione dell'array
      contaminato, e lo sara' per sempre. Qui non si cambia il numero, si
      cambia il TEMPO DEL VERBO e si scrive il ruolo.

LA REGOLA CHE NE ESCE
---------------------
Una costante che cita un manoscritto in revisione scade se serve da CONFRONTO,
non se serve da RIPRODUZIONE. Il ruolo va scritto accanto al valore, o fra un
anno nessuno sapra' quale dei due e'.

USO
    python src\\paper2_patch_citazioni_m26.py selftest
    python src\\paper2_patch_citazioni_m26.py applica --root . --dry-run
    python src\\paper2_patch_citazioni_m26.py applica --root . --backup-dir logs

Uscita: 0 se applicato, 2 se rifiutato, 3 se la rilettura o la compilazione non
torna. Applica TUTTO o NIENTE: se un'ancora manca in uno dei due file, non
scrive nessuno dei due.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

N6_VECCHIO = """centrale e' un confronto dati-mock di precisione questo non basta: M26
Tabella 1 mostra gia' che pesare i mock in stile FKP sposta la media di ~600
generatori ALLONTANANDOLA dai dati, e quel limite va importato esplicitamente
nella banda sistematica di Sez. 6.3."""

N6_NUOVO = """centrale e' un confronto dati-mock di precisione questo non basta, e il limite
va importato esplicitamente nella banda sistematica di Sez. 6.3.
La motivazione originaria citava il +622 «away from the data» della Tabella 1 di
M26 PRE-REVISIONE. Questo script ha misurato -78.0 +/- 8.0, VERSO i dati; il
Paper 1 §7.2 nota (i) spiega perche' non era la stessa misura (base 35 838, peso
posizionale invece del w_FKP(z) radiale), e M26 R1 ha corretto la riga."""

M1_VECCHIO = """            print(f"\\n      M26 riga 735 riporta (su n=200 contaminato): "
                  f"Om {M26_QUOTED['Om']:+.2f}, s8 {M26_QUOTED['s8']:+.2f}, "
                  f"w0 {M26_QUOTED['w0']:+.2f}")"""

M1_NUOVO = """            print(f"\\n      M26 PRE-REVISIONE, riga 735, riportava (su n=200 "
                  f"contaminato): Om {M26_QUOTED['Om']:+.2f}, "
                  f"s8 {M26_QUOTED['s8']:+.2f}, w0 {M26_QUOTED['w0']:+.2f}")
            print("      M26 R1 li ha rifatti sui 2000: Om +0.154, s8 +0.182, "
                  "n_s +0.376.")
            print("      I valori sopra NON sono cio' che M26 dice oggi: sono il "
                  "bersaglio di")
            print("      RIPRODUZIONE dell'array contaminato, e in quel ruolo "
                  "restano validi.")"""

M1_COST_VECCHIO = """M26_QUOTED = {"Om": 0.45, "s8": 0.29, "w0": -0.03}"""

M1_COST_NUOVO = """# RUOLO: riproduzione, non confronto. Sono i valori che l'array contaminato
# produce, e lo produrra' sempre; NON sono cio' che M26 riporta oggi, perche' la
# revisione R1 li ha rifatti sui 2000 (Om +0.154, s8 +0.182, n_s +0.376).
# Una costante che cita un manoscritto in revisione scade se serve da CONFRONTO,
# non se serve da RIPRODUZIONE.
M26_QUOTED = {"Om": 0.45, "s8": 0.29, "w0": -0.03}"""

BERSAGLI = [
    ("src/paper1_rev_n6_fkp.py", [("docstring di n6", N6_VECCHIO, N6_NUOVO)]),
    ("src/paper1_rev_m1_cosmo_response.py",
     [("frase al presente", M1_VECCHIO, M1_NUOVO),
      ("ruolo di M26_QUOTED", M1_COST_VECCHIO, M1_COST_NUOVO)]),
]

SPARITI = {"src/paper1_rev_n6_fkp.py": ["ALLONTANANDOLA dai dati"],
           "src/paper1_rev_m1_cosmo_response.py": ["M26 riga 735 riporta"]}
PRESENTI = {"src/paper1_rev_n6_fkp.py": ["PRE-REVISIONE", "VERSO i dati"],
            "src/paper1_rev_m1_cosmo_response.py":
                ["riportava", "RIPRODUZIONE dell'array contaminato",
                 "RUOLO: riproduzione, non confronto"]}


def prepara(root):
    """Calcola il nuovo testo di ogni file. Rifiuta se un'ancora non e' unica."""
    nuovi = {}
    for rel, sost in BERSAGLI:
        path = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            raise SystemExit("RIFIUTO: file inesistente: %s" % path)
        with open(path, "rb") as fh:
            testo = fh.read().decode("utf-8")
        for nome, vecchio, nuovo in sost:
            n = testo.count(vecchio)
            if n != 1:
                raise SystemExit("RIFIUTO: ancora '%s' in %s trovata %d volte, "
                                 "attesa 1" % (nome, rel, n))
            testo = testo.replace(vecchio, nuovo)
        for f in SPARITI.get(rel, []):
            if f in testo:
                raise SystemExit("RIFIUTO: %s: '%s' ancora presente" % (rel, f))
        for f in PRESENTI.get(rel, []):
            if f not in testo:
                raise SystemExit("RIFIUTO: %s: '%s' manca" % (rel, f))
        if rel.endswith(".py"):
            try:
                compile(testo, path, "exec")
            except SyntaxError as e:
                raise SystemExit("RIFIUTO: %s non compila dopo la patch: %s"
                                 % (rel, e))
        nuovi[path] = (rel, testo)
    return nuovi


def applica(root, dry_run=False, backup_dir=None):
    nuovi = prepara(root)          # TUTTO o NIENTE: si calcola prima di scrivere
    for path, (rel, testo) in nuovi.items():
        vecchio = os.path.getsize(path)
        print("  ok    %-38s %d -> %d byte" % (rel, vecchio,
                                               len(testo.encode("utf-8"))))
    if dry_run:
        print("dry-run: nessuna scrittura")
        return 0
    for path, (rel, testo) in nuovi.items():
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
            bk = os.path.join(backup_dir, os.path.basename(path) + ".pre_m26")
            shutil.copy2(path, bk)
            print("  backup %s" % bk)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(testo)
        with open(path, "r", encoding="utf-8") as fh:
            riletto = fh.read()
        if riletto != testo:
            print("ERRORE: %s, la rilettura non coincide" % rel)
            return 3
        try:
            compile(riletto, path, "exec")
        except SyntaxError as e:
            print("ERRORE: %s su disco non compila: %s" % (rel, e))
            return 3
    print("APPLICATO")
    return 0


# ---------------------------------------------------------------------------

FINTO_N6 = '''"""
Roba iniziale.
centrale e' un confronto dati-mock di precisione questo non basta: M26
Tabella 1 mostra gia' che pesare i mock in stile FKP sposta la media di ~600
generatori ALLONTANANDOLA dai dati, e quel limite va importato esplicitamente
nella banda sistematica di Sez. 6.3. Il referee chiede altro.
"""
X = 1
'''

FINTO_M1 = '''M26_QUOTED = {"Om": 0.45, "s8": 0.29, "w0": -0.03}


def stampa(reg):
    if True:
        if reg == "NGC":
            print(f"\\n      M26 riga 735 riporta (su n=200 contaminato): "
                  f"Om {M26_QUOTED['Om']:+.2f}, s8 {M26_QUOTED['s8']:+.2f}, "
                  f"w0 {M26_QUOTED['w0']:+.2f}")
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

    print("selftest paper2_patch_citazioni_m26")

    base = tempfile.mkdtemp(prefix="m26_")
    src = os.path.join(base, "src")
    os.makedirs(src)

    def scrivi(n6=FINTO_N6, m1=FINTO_M1):
        with open(os.path.join(src, "paper1_rev_n6_fkp.py"), "w",
                  encoding="utf-8", newline="") as fh:
            fh.write(n6)
        with open(os.path.join(src, "paper1_rev_m1_cosmo_response.py"), "w",
                  encoding="utf-8", newline="") as fh:
            fh.write(m1)

    scrivi()
    # il difetto c'e', PRIMA di correggerlo
    chk("difetto: n6 cita M26 al presente con ~600 ALLONTANANDOLA",
        "ALLONTANANDOLA dai dati" in open(
            os.path.join(src, "paper1_rev_n6_fkp.py"), encoding="utf-8").read())
    chk("difetto: m1 dice «riporta», al presente",
        "M26 riga 735 riporta" in open(
            os.path.join(src, "paper1_rev_m1_cosmo_response.py"),
            encoding="utf-8").read())

    prima_n6 = open(os.path.join(src, "paper1_rev_n6_fkp.py"), "rb").read()
    chk("dry-run non scrive",
        applica(base, dry_run=True) == 0
        and open(os.path.join(src, "paper1_rev_n6_fkp.py"), "rb").read() == prima_n6)

    chk("applica riesce", applica(base, backup_dir=os.path.join(base, "bk")) == 0)
    n6 = open(os.path.join(src, "paper1_rev_n6_fkp.py"), encoding="utf-8").read()
    m1 = open(os.path.join(src, "paper1_rev_m1_cosmo_response.py"),
              encoding="utf-8").read()
    chk("n6: la cornice superata non c'e' piu'", "ALLONTANANDOLA" not in n6)
    chk("n6: il +622 e la direzione vera ci sono",
        "+622" in n6 and "VERSO i dati" in n6)
    chk("m1: il verbo e' al passato", "riportava" in m1
        and "M26 riga 735 riporta" not in m1)
    chk("m1: il VALORE non e' cambiato",
        'M26_QUOTED = {"Om": 0.45, "s8": 0.29, "w0": -0.03}' in m1)
    chk("m1: il ruolo e' scritto accanto alla costante",
        "RUOLO: riproduzione, non confronto" in m1)
    chk("m1: i valori di R1 sono riportati", "+0.154" in m1 and "+0.376" in m1)
    chk("entrambi compilano", all(
        compile(open(os.path.join(src, f), encoding="utf-8").read(), f, "exec")
        is not None for f in ("paper1_rev_n6_fkp.py",
                              "paper1_rev_m1_cosmo_response.py")))
    chk("il backup esiste per entrambi",
        os.path.isfile(os.path.join(base, "bk", "paper1_rev_n6_fkp.py.pre_m26"))
        and os.path.isfile(os.path.join(
            base, "bk", "paper1_rev_m1_cosmo_response.py.pre_m26")))

    # idempotenza e rifiuti
    try:
        applica(base, dry_run=True)
        chk("seconda passata: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("seconda passata: rifiuto", "0 volte" in str(e), str(e))

    scrivi(n6=FINTO_N6 + "\n" + FINTO_N6)
    try:
        applica(base, dry_run=True)
        chk("ancora doppia: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("ancora doppia: rifiuto", "2 volte" in str(e), str(e))

    # TUTTO o NIENTE: se m1 e' rotto, n6 non deve essere scritto
    scrivi(m1=FINTO_M1.replace("M26 riga 735 riporta", "qualcos'altro"))
    prima = open(os.path.join(src, "paper1_rev_n6_fkp.py"), "rb").read()
    try:
        applica(base)
    except SystemExit:
        pass
    chk("se un'ancora manca in UN file, l'altro non viene scritto",
        open(os.path.join(src, "paper1_rev_n6_fkp.py"), "rb").read() == prima)

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
    sub.add_parser("selftest")
    x = ap.parse_args(argv)
    if x.cmd == "applica":
        return applica(x.root, x.dry_run, x.backup_dir)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())

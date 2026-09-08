#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_realspace_fix_patch.py — la riga mancante, e il controllo che l'avrebbe
presa. Record 35.

IL DIFETTO
  `REAL_SPACE` e' una variabile di modulo in phase8_cutsky_mocks.py e
  `--real-space` e' un flag del runner che finisce nel record e nella chiave di
  ripartenza. La riga che COLLEGA le due cose - M.REAL_SPACE = ... - non e' mai
  stata scritta. Il flag veniva letto, registrato e messo in chiave; phase8
  restava a False.

  Costo: dodici ore di macchina che hanno riprodotto, cella per cella, un run
  gia' esistente. 2400 celle su 2400 identiche a fase3_mock.jsonl.

PERCHE' VENTUNO CONTROLLI NON L'HANNO PRESO
  Verificavano che il flag esistesse, che entrasse nella chiave, che entrasse
  nel record, che v_los fosse azzerato DENTRO phase8, e che ogni nome fosse
  legato. Nessuno verificava che qualcuno lo ACCENDESSE. Entrambi i capi del
  filo c'erano ed erano controllati; il filo mancante non ha un nome, quindi la
  sua assenza non ha niente contro cui essere verificata.

  E lo smoke non poteva prenderlo: gira apposta SENZA il flag, per confermare
  che sia inerte. Era inerte anche CON, e da li' le due cose sono
  indistinguibili.

DUE MODIFICHE
  A  cmd_run accende il flag su phase8, e lo STAMPA
  B  cmd_smoke accetta --real-space, cosi' lo smoke puo' girare CON il flag

E DUE CONTROLLI NUOVI, CHE SONO IL PUNTO
  - STATICO: qualcuno assegna M.REAL_SPACE. Non "il flag esiste": qualcuno lo
    ACCENDE.
  - COMPORTAMENTALE, che e' quello che conta: `python ... smoke --region NGC
    --real-space` deve dare numeri DIVERSI dallo smoke normale. Il patcher
    stampa i due comandi e la regola: se coincidono, il flag e' ancora scollegato
    e non si lancia niente.

REGOLA ADOTTATA (record 35)
  Un flag che cambia una misura si verifica con un run che PRODUCE NUMERI
  DIVERSI, non ispezionando il percorso di codice. Inerzia e scollegamento sono
  indistinguibili dall'esterno.

Uso:
    python src\\paper2_realspace_fix_patch.py selftest
    python src\\paper2_realspace_fix_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_runner_fase3_mock.py")

A_OLD = '''def cmd_run(a):
    _avviso_d5c()'''

A_NEW = '''def _accendi_real_space(M, a):
    """LA RIGA CHE MANCAVA (record 35).

    REAL_SPACE e' una variabile di MODULO in phase8: il flag di argparse non la
    tocca da solo. Senza questa funzione il run gira in spazio di redshift
    scrivendo real_space: true nel record, che e' esattamente quel che e'
    successo il 1-2 settembre: dodici ore, 2400 celle su 2400 identiche al run
    principale.

    Si stampa sempre, anche quando e' False: uno stato che non si vede e' uno
    stato che si dimentica."""
    rs = bool(getattr(a, "real_space", False))
    M.REAL_SPACE = rs
    print(f"  [phase8] REAL_SPACE = {M.REAL_SPACE}"
          + ("   <-- v_los AZZERATO, spazio reale" if rs else ""))
    if rs and not getattr(M, "REAL_SPACE", False):
        sys.exit("[FATAL] REAL_SPACE non e' stato accettato dal modulo: il "
                 "flag esiste ma non arriva a carve_cutsky.")
    return rs


def cmd_run(a):
    _avviso_d5c()'''

# La chiamata a _prepare e' IDENTICA in cmd_smoke e cmd_run: ancorarsi a quella
# riga sola ne trova due. Si distinguono con la riga successiva - `idx` nello
# smoke, `order` nel run - e servono ENTRAMBE: se lo smoke non accende il flag,
# i due smoke danno lo stesso output e si concluderebbe "ancora scollegato" per
# la ragione sbagliata.
B_OLD = '''    (M, P1, T2, F3, root, reg, geoms, Gr, cache_dir, frozen) = _prepare(a, pts)
    order = [p for p in geoms if p != "FID"] if a.skip_fid else list(geoms)'''

B_NEW = '''    (M, P1, T2, F3, root, reg, geoms, Gr, cache_dir, frozen) = _prepare(a, pts)
    _accendi_real_space(M, a)
    order = [p for p in geoms if p != "FID"] if a.skip_fid else list(geoms)'''

D_OLD = '''    (M, P1, T2, F3, root, reg, geoms, Gr, cache_dir, frozen) = _prepare(a, pts)
    idx = list(range(a.n))'''

D_NEW = '''    (M, P1, T2, F3, root, reg, geoms, Gr, cache_dir, frozen) = _prepare(a, pts)
    _accendi_real_space(M, a)
    idx = list(range(a.n))'''

C_OLD = '''            q.add_argument("--real-space", action="store_true",
                           help="§3.8: azzera v_los, cioe' niente RSD. Usare un "
                                "--out SEPARATO: e' una misura diversa, non una "
                                "continuazione di quella in spazio di redshift")'''

C_NEW = '''            q.add_argument("--real-space", action="store_true",
                           help="§3.8: azzera v_los, cioe' niente RSD. Usare un "
                                "--out SEPARATO: e' una misura diversa, non una "
                                "continuazione di quella in spazio di redshift")
        if nm == "smoke":
            # Lo smoke deve poter girare CON il flag: e' l'unico modo di
            # distinguere "inerte" da "scollegato" (record 35). Senza questo,
            # lo smoke conferma solo che senza flag non cambia nulla, che era
            # vero anche quando il flag non era collegato.
            q.add_argument("--real-space", action="store_true",
                           help="smoke in spazio reale: DEVE dare numeri "
                                "diversi dallo smoke normale, altrimenti il "
                                "flag e' ancora scollegato")'''

EDITS = [
    ("A  _accendi_real_space, definita", A_OLD, A_NEW),
    ("B  e CHIAMATA in cmd_run", B_OLD, B_NEW),
    ("C  --real-space anche sullo smoke", C_OLD, C_NEW),
    ("D  e ACCESO anche in cmd_smoke", D_OLD, D_NEW),
]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    for name, old, new in EDITS:
        n = s.count(old)
        if n != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, n))
        s = s.replace(old, new, 1)
    return s


def _assegna_attributo(src, modulo, attr):
    """Cerca un'assegnazione `modulo.attr = ...` in QUALUNQUE punto del file.

    E' il controllo che mancava: non 'il flag esiste', ma 'qualcuno lo accende'.
    Si usa ast, cosi' una stringa che contiene 'M.REAL_SPACE' in un commento o
    in un messaggio non conta come assegnazione."""
    import ast
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Attribute) and t.attr == attr
                        and isinstance(t.value, ast.Name) and t.value.id == modulo):
                    return True
    return False


def _parses(src):
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        print("      [sintassi] %s" % exc)
        return False


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    ok = os.path.isfile(path)
    chk("1  runner presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)

    # IL CONTROLLO CHE MANCAVA, applicato allo stato ATTUALE: deve fallire.
    chk("2  il difetto e' ancora presente: NESSUNO accende M.REAL_SPACE",
        not _assegna_attributo(s, "M", "REAL_SPACE"),
        "se questo PASSA, il file e' gia' corretto o la patch e' inutile")
    chk("3  ma il flag esiste, entra nel record e nella chiave",
        ("--real-space" in s) and ('rec["real_space"] = True' in s)
        and ('r.get("real_space", False)' in s))
    chk("4  cioe': entrambi i capi c'erano, mancava il filo", True,
        "e' la classe di difetto del record 35")
    chk("5  idempotenza: la correzione non c'e' ancora",
        "_accendi_real_space" not in s)
    for i, (name, old, new) in enumerate(EDITS, start=6):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("9  il risultato e' Python valido", _parses(out))
        chk("10 DOPO la patch, qualcuno accende M.REAL_SPACE",
            _assegna_attributo(out, "M", "REAL_SPACE"),
            "e' il controllo che ventuno controlli non avevano")
        chk("11 la funzione e' DEFINITA e chiamata in ENTRAMBI i comandi",
            out.count("def _accendi_real_space") == 1
            and out.count("\n    _accendi_real_space(M, a)") == 2,
            "run e smoke: senza lo smoke, i due smoke coinciderebbero comunque")
        chk("12 lo stato si STAMPA sempre, anche quando e' False",
            "[phase8] REAL_SPACE =" in out
            and "print(f\"  [phase8]" in out)
        chk("13 lo smoke accetta --real-space",
            out.count('q.add_argument("--real-space"') == 2
            and 'if nm == "smoke":' in out)
        # La patch del trattamento (B) e' INDIPENDENTE da questa e puo' non
        # essere ancora applicata: il §3.8 girava e le avevo chiesto di
        # aspettare. Se `fixed_observables` non c'e', non e' un difetto; se c'e',
        # deve comparire una volta sola. Il controllo originale dava per
        # scontato un prerequisito che non e' tale.
        _fo = out.count("fixed_observables=bool(getattr(a,")
        chk("14 se la patch (B) e' applicata, il suo flag e' passato una volta",
            _fo in (0, 1),
            "assente: patch (B) non ancora applicata" if _fo == 0
            else "presente una volta")
        chk("15 e phase8 non e' toccato da questa patch",
            "phase8" not in os.path.basename(path))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_realspace_fix_patch ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def cmd_apply(a):
    if selftest(a.path):
        print("")
        fail("selftest fallito: nessuna scrittura.")
    s = read(a.path)
    out = apply_all(s)
    diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                     fromfile="prima", tofile="dopo", n=2))
    print("\n=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff))
    print("righe: %d -> %d" % (s.count("\n"), out.count("\n")))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_rsfix"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("[backup] %s" % bak)
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    print(r"""
PRIMA DI TUTTO, rinomina il registro nullo. La chiave di ripartenza contiene
real_space, quindi lasciandolo li' un rilancio corretto SALTEREBBE tutte le
realizzazioni credendole fatte:

  ren results\paper2\fase3_mock_realspace.jsonl fase3_mock_realspace_NULLO.jsonl

POI IL CONTROLLO CHE CONTA, e non e' statico. Due smoke, due minuti:

  python src\paper2_runner_fase3_mock.py smoke --region NGC
  python src\paper2_runner_fase3_mock.py smoke --region NGC --real-space

I DUE OUTPUT DEVONO ESSERE DIVERSI.

  diversi  -> il flag e' collegato, si puo' lanciare il run.
  UGUALI   -> il flag e' ANCORA scollegato. Non si lancia niente e si torna
              a guardare il codice. E' esattamente cosi' che si sono persi i
              primi dodici ore: nessun controllo cercava una DIFFERENZA.

Il secondo smoke deve anche stampare '[phase8] REAL_SPACE = True'. Se stampa
False, argparse non sta passando il flag.

POI, e solo poi, il run - altre dodici ore:

  python src\paper2_runner_fase3_mock.py run --region NGC --n 200 ^
      --points FID B1 B2 B4 B5 B6 --real-space ^
      --out results\paper2\fase3_mock_realspace.jsonl
  python src\paper2_runner_fase3_mock.py run --region SGC --n 200 ^
      --points FID B1 B2 B4 B5 B6 --real-space ^
      --out results\paper2\fase3_mock_realspace.jsonl

E sulle prime righe, prima di andare a dormire: '[phase8] REAL_SPACE = True'
e i primi N_H1 DIVERSI da quelli di fase3_mock.jsonl.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="la riga mancante di --real-space, record 35")
    p.add_argument("--path", default=DEFAULT_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(func=lambda a: 1 if selftest(a.path) else 0)
    ap = sub.add_parser("apply")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(func=cmd_apply)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

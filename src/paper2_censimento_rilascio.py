#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""paper2_censimento_rilascio.py — la popolazione del rilascio si deriva dal ledger.

Il punto 6.3 chiede un tag e un DOI aggiornato. Ma un tag e' un'etichetta su un
commit, e la domanda vera e' quali file ci stanno dentro. Delimitare quella
popolazione per abitudine — "src e results" — e' l'errore che il record 68 ha
appena dichiarato per il censimento dei registri: i cinque tier del congelamento
erano rimasti fuori per svista, cioe' proprio cio' che freeze_verify legge.

Qui la popolazione si deriva: ogni percorso che un record del ledger nomina
DEVE stare nel rilascio, oppure esserne fuori con un motivo scritto. Lo
strumento non decide niente. Misura quattro cose e le stampa:

  1. ogni percorso citato dai record esiste su disco;
  2. ogni percorso citato e' tracciato da git;
  3. nessun percorso citato e' escluso da .gitignore (se lo e', la regola che
     lo esclude viene stampata, e serve un'eccezione dichiarata);
  4. nessun percorso citato e' tracciato ma non committato.

`NA` e' un esito stampato: un percorso con un metacarattere (`results/**`,
`per_mock_*.jsonl`) non e' un file e viene marcato, non passato in silenzio.

Sottocomandi:

    python src\paper2_censimento_rilascio.py selftest
    python src\paper2_censimento_rilascio.py censimento --attesi-record 68 --out logs\censimento_rilascio.jsonl

Uscita `0` solo se i quattro verdetti passano e nessun percorso resta in uno
stato non deciso. Finche' ci sono percorsi da aggiungere o esclusi senza
eccezione, l'uscita e' `1`: e' la lista di lavoro di 6.3a, non un errore.

Eccezioni dichiarate: un JSON `{"percorso": "motivo"}` passato con
`--eccezioni`. Un'eccezione senza motivo viene rifiutata.

LIMITI DICHIARATI, stampati a ogni passata:
  - Il rilevatore di percorso chiede un separatore: `gate53.jsonl` nominato
    senza cartella non viene riconosciuto come percorso. Lo stesso limite del
    censimento dei registri, e per la stessa ragione.
  - Serve un'estensione fra quelle note: una cartella nominata da sola
    (`results/paper2`) non e' un percorso di file.
  - Un percorso dentro la prosa che finisce su un troncamento resta troncato, e
    uscira' come `assente`: e' l'esito giusto, va letto come "da guardare".
  - Un modello scritto con LETTERE al posto dei numeri
    (`results/phase8_test2_fields/test2_NNNN.npz`) non e' riconosciuto come
    pattern e uscira' `assente`. I metacaratteri si vedono, i segnaposto no.
  - Un percorso assoluto viene reso relativo se sta dentro la radice; se sta
    fuori esce `NA_fuori_albero` e non produce verdetto.
  - Lo stato di esclusione si misura su `git status --untracked-files=all`, non
    su `check-ignore`: il primo dice che cosa git offrirebbe di aggiungere, il
    secondo dice solo quale regola esclude. `metri_concordi` FAIL vuol dire che
    i due non dicono la stessa cosa, ed e' un difetto dello strumento.
  - git e' case-sensitive nell'indice, Windows no sul filesystem: due percorsi
    che differiscono per maiuscole sono contati due volte.
  - Non entra nel merito di che cosa DEBBA essere rilasciato: un file che
    nessun record nomina non e' un difetto e non produce verdetto.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSIONE = "1.1"

ESTENSIONI = (
    "jsonl", "json", "py", "md", "npz", "npy", "csv", "txt", "tsv",
    "zip", "gz", "pdf", "sha256", "yml", "yaml", "tex", "bib", "cfg",
    "toml", "ini", "png", "pkl", "h5", "fits",
)

RE_PERCORSO = re.compile(
    r"(?:[A-Za-z]:[\\/])?(?:[A-Za-z0-9_.@+*?{}\[\]-]+[\\/])+"
    r"[A-Za-z0-9_.@+*?{}\[\]-]+\.(?:%s)\b"
    % "|".join(ESTENSIONI)
)

RE_ASSOLUTO = re.compile(r"^[A-Za-z]:/")

RE_META = re.compile(r"[*?\[\]{}]")

STATI = (
    "tracciato_pulito",
    "tracciato_modificato",
    "da_aggiungere",
    "escluso",
    "escluso_con_eccezione",
    "assente",
    "assente_con_eccezione",
    "NA_pattern",
    "NA_fuori_albero",
)


class Rifiuto(Exception):
    """Un cancello non e' passato."""


# --------------------------------------------------------------------------- #

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for blocco in iter(lambda: fh.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def normalizza(percorso: str) -> str:
    p = percorso.replace("\\", "/").strip()
    p = p.rstrip(".,;:)\u00bb\"'").lstrip("(\u00ab\"'")
    while p.startswith("./"):
        p = p[2:]
    return p


def relativizza(p: str, radice) -> str:
    """Un percorso assoluto dentro l'albero diventa relativo; fuori resta tale."""
    if radice is None or not RE_ASSOLUTO.match(p):
        return p
    base = str(Path(radice).resolve()).replace("\\", "/").rstrip("/")
    if p.lower().startswith(base.lower() + "/"):
        return p[len(base) + 1:]
    return p


def percorsi_da_record(rec, radice=None) -> set:
    """Cammina il record e raccoglie ogni stringa che sembri un percorso."""
    trovati = set()

    def cammina(nodo):
        if isinstance(nodo, str):
            for m in RE_PERCORSO.finditer(nodo):
                trovati.add(relativizza(normalizza(m.group(0)), radice))
        elif isinstance(nodo, dict):
            for v in nodo.values():
                cammina(v)
        elif isinstance(nodo, (list, tuple)):
            for v in nodo:
                cammina(v)

    cammina(rec)
    return trovati


def leggi_ledger(p: Path, attesi=None) -> list:
    if not p.is_file():
        raise Rifiuto("ledger assente: %s" % p)
    righe = [r for r in p.read_bytes().decode("utf-8").splitlines() if r.strip()]
    if attesi is not None and len(righe) != attesi:
        raise Rifiuto("ledger a %d record, attesi %d" % (len(righe), attesi))
    out = []
    for i, r in enumerate(righe, 1):
        try:
            out.append(json.loads(r))
        except Exception as e:
            raise Rifiuto("record %d non parsabile: %s" % (i, e))
    return out


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #

def git(radice: Path, *argomenti, ingresso=None, ammetti=(0,)) -> str:
    cmd = ["git", "-c", "core.quotepath=false"] + list(argomenti)
    dati = None
    if ingresso is not None:
        dati = ingresso.encode("utf-8")
        if b"\r" in dati:
            raise Rifiuto("ingresso a git con CR: git legge la riga col CR dentro")
    try:
        r = subprocess.run(cmd, cwd=str(radice), input=dati, capture_output=True)
    except FileNotFoundError:
        raise Rifiuto("git non trovato nel PATH")
    if r.returncode not in ammetti:
        raise Rifiuto(
            "git %s uscito %d: %s"
            % (" ".join(argomenti), r.returncode,
               r.stderr.decode("utf-8", "replace").strip()[:200])
        )
    return r.stdout.decode("utf-8", "replace")


def tracciati(radice: Path) -> set:
    return set(
        normalizza(r) for r in git(radice, "ls-files").splitlines() if r.strip()
    )


def sporchi(radice: Path) -> dict:
    """percorso -> due lettere di stato, dai soli file tracciati modificati."""
    out = {}
    for riga in git(radice, "status", "--porcelain", "--untracked-files=no").splitlines():
        if len(riga) < 4:
            continue
        stato, resto = riga[:2], riga[3:]
        if " -> " in resto:
            resto = resto.split(" -> ", 1)[1]
        out[normalizza(resto.strip('"'))] = stato.strip() or "??"
    return out


def non_tracciati_visibili(radice: Path) -> set:
    """I soli non tracciati che git offrirebbe di aggiungere: esclusi fuori."""
    out = set()
    for riga in git(radice, "status", "--porcelain", "--untracked-files=all").splitlines():
        if riga.startswith("?? "):
            out.add(normalizza(riga[3:].strip('"')))
    return out


def esclusi(radice: Path, candidati) -> dict:
    """percorso -> regola di .gitignore che lo esclude."""
    if not candidati:
        return {}
    ordinati = sorted(candidati)
    uscita = git(
        radice, "check-ignore", "-v", "--stdin",
        ingresso="\n".join(ordinati) + "\n", ammetti=(0, 1),
    )
    out = {}
    for riga in uscita.splitlines():
        if "\t" not in riga:
            continue
        regola, percorso = riga.rsplit("\t", 1)
        out[normalizza(percorso)] = regola.strip()
    return out


# --------------------------------------------------------------------------- #
# Censimento
# --------------------------------------------------------------------------- #

def classifica(radice: Path, percorsi: set, eccezioni: dict) -> dict:
    trac = tracciati(radice)
    mod = sporchi(radice)
    visibili = non_tracciati_visibili(radice)
    da_chiedere = [p for p in percorsi if not RE_META.search(p) and p not in trac]
    ign = esclusi(radice, da_chiedere)

    esito = {}
    for p in sorted(percorsi):
        if RE_META.search(p):
            esito[p] = ("NA_pattern", "metacarattere: non e' un file")
        elif RE_ASSOLUTO.match(p):
            esito[p] = ("NA_fuori_albero", "percorso assoluto fuori dalla radice")
        elif p in trac:
            if p in mod:
                esito[p] = ("tracciato_modificato", "git status: %s" % mod[p])
            else:
                esito[p] = ("tracciato_pulito", "")
        elif not (radice / p).exists():
            if p in eccezioni:
                esito[p] = ("assente_con_eccezione", eccezioni[p])
            else:
                esito[p] = ("assente", "citato ma non su disco")
        elif p in visibili:
            esito[p] = ("da_aggiungere", "su disco, non tracciato")
        else:
            regola = ign.get(p, "non fra i non tracciati di git status, regola non riportata")
            if p in eccezioni:
                esito[p] = ("escluso_con_eccezione", "%s | %s" % (regola, eccezioni[p]))
            else:
                esito[p] = ("escluso", regola)
    return esito, ign


def verdetti(esito: dict, ign: dict) -> list:
    per_stato = dict((s, [p for p, (st, _) in esito.items() if st == s]) for s in STATI)
    senza_regola = [p for p in per_stato["escluso"] + per_stato["escluso_con_eccezione"]
                    if p not in ign]
    v = [
        ("citati_esistono", not per_stato["assente"],
         "%d citati e non su disco" % len(per_stato["assente"])),
        ("citati_tracciati", not per_stato["da_aggiungere"],
         "%d da aggiungere" % len(per_stato["da_aggiungere"])),
        ("citati_non_esclusi", not per_stato["escluso"],
         "%d esclusi da .gitignore senza eccezione" % len(per_stato["escluso"])),
        ("citati_committati", not per_stato["tracciato_modificato"],
         "%d tracciati e modificati" % len(per_stato["tracciato_modificato"])),
        ("metri_concordi", not senza_regola,
         "%d esclusi da git status ma senza regola da check-ignore" % len(senza_regola)),
    ]
    return [(nome, "PASS" if ok else "FAIL", nota) for nome, ok, nota in v], per_stato


def carica_eccezioni(p) -> dict:
    if not p:
        return {}
    q = Path(p)
    if not q.is_file():
        raise Rifiuto("file delle eccezioni assente: %s" % q)
    dati = json.loads(q.read_text(encoding="utf-8"))
    if not isinstance(dati, dict):
        raise Rifiuto("le eccezioni devono essere un oggetto {percorso: motivo}")
    fuori = {}
    for k, val in dati.items():
        if not isinstance(val, str) or len(val.strip()) < 10:
            raise Rifiuto("eccezione senza motivo scritto: %r" % k)
        fuori[normalizza(k)] = val.strip()
    return fuori


def cmd_censimento(args) -> int:
    radice = Path(args.radice).resolve()
    p_ledger = radice / args.ledger
    records = leggi_ledger(p_ledger, args.attesi_record)
    eccezioni = carica_eccezioni(args.eccezioni)

    per_record = {}
    tutti = set()
    for i, rec in enumerate(records, 1):
        ps = percorsi_da_record(rec, radice)
        per_record[i] = sorted(ps)
        tutti |= ps

    esito, ign = classifica(radice, tutti, eccezioni)
    verd, per_stato = verdetti(esito, ign)

    print("=== paper2_censimento_rilascio v%s — %s ===" % (
        VERSIONE, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    print("ledger: %s  %d record  %s" % (
        args.ledger, len(records), sha256_file(p_ledger)[:16]))
    print("percorsi citati, distinti: %d" % len(tutti))
    print()
    print("  %-24s %5s" % ("stato", "n"))
    for s in STATI:
        print("  %-24s %5d" % (s, len(per_stato[s])))
    print()

    for s in ("assente", "da_aggiungere", "escluso", "tracciato_modificato",
              "escluso_con_eccezione", "assente_con_eccezione", "NA_pattern",
              "NA_fuori_albero"):
        if not per_stato[s]:
            continue
        print("--- %s (%d) ---" % (s, len(per_stato[s])))
        for p in sorted(per_stato[s]):
            citato_da = [i for i, ps in per_record.items() if p in ps]
            sigla = ",".join(str(i) for i in citato_da[:6])
            if len(citato_da) > 6:
                sigla += ",+%d" % (len(citato_da) - 6)
            nota = esito[p][1]
            print("  %-64s record %-18s %s" % (p, sigla, nota))
        print()

    print("verdetti:")
    for nome, stato, nota in verd:
        print("  [%s] %-22s %s" % (stato.lower(), nome, nota))
    print()
    print("limiti dichiarati:")
    for riga in __doc__.split("LIMITI DICHIARATI, stampati a ogni passata:")[1].strip().split("\n"):
        print("  " + riga.strip())

    esito_num = 0 if all(s == "PASS" for _, s, _ in verd) else 1

    if args.out:
        p_out = radice / args.out
        p_out.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "strumento": "paper2_censimento_rilascio.py",
            "versione": VERSIONE,
            "ledger": args.ledger,
            "ledger_sha256": sha256_file(p_ledger),
            "ledger_record": len(records),
            "percorsi_distinti": len(tutti),
            "conteggi": dict((s, len(per_stato[s])) for s in STATI),
            "per_stato": dict((s, sorted(per_stato[s])) for s in STATI),
            "motivi": dict((p, esito[p][1]) for p in sorted(esito) if esito[p][1]),
            "verdetti": dict((nome, stato) for nome, stato, _ in verd),
            "eccezioni_dichiarate": eccezioni,
            "esito": esito_num,
        }
        with p_out.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        print("\nrecord appeso a %s" % args.out)

    print("ESITO: %s" % ("PULITO" if esito_num == 0 else "DA DECIDERE"))
    return esito_num


# --------------------------------------------------------------------------- #
# Selftest
# --------------------------------------------------------------------------- #

def _rifiuta_cr(base) -> bool:
    try:
        git(base, "check-ignore", "-v", "--stdin", ingresso="logs/prova.jsonl\r\n",
            ammetti=(0, 1))
    except Rifiuto:
        return True
    return False


def _repo_finto(base: Path) -> None:
    (base / "src").mkdir(parents=True)
    (base / "results" / "paper2").mkdir(parents=True)
    (base / "logs").mkdir()
    (base / "papers" / "paper2").mkdir(parents=True)
    (base / ".gitignore").write_bytes(b"logs/\npapers/\n")
    (base / "src" / "tracciato_pulito.py").write_bytes(b"# a\n")
    (base / "src" / "tracciato_mod.py").write_bytes(b"# b\n")
    (base / "results" / "paper2" / "non_tracciato.jsonl").write_bytes(b'{"a":1}\n')
    (base / "logs" / "prova.jsonl").write_bytes(b'{"b":2}\n')
    (base / "papers" / "paper2" / "doc.md").write_bytes(b"# doc\n")
    git(base, "init", "-q")
    git(base, "config", "user.email", "t@t")
    git(base, "config", "user.name", "t")
    git(base, "add", ".gitignore", "src/tracciato_pulito.py", "src/tracciato_mod.py")
    git(base, "commit", "-q", "-m", "base")
    (base / "src" / "tracciato_mod.py").write_bytes(b"# b modificato\n")


def _ledger_finto(base: Path, righe) -> None:
    testo = "\n".join(json.dumps(r, ensure_ascii=False) for r in righe) + "\n"
    (base / "src" / "amend.jsonl").write_bytes(testo.encode("utf-8"))


def cmd_selftest(args) -> int:
    import tempfile
    ok, ko = 0, 0

    def controlla(nome, cond):
        nonlocal ok, ko
        if cond:
            ok += 1
        else:
            ko += 1
            print("  FAIL  %s" % nome)

    def rifiuta(nome, fn):
        nonlocal ok, ko
        try:
            fn()
        except Rifiuto:
            ok += 1
            return
        except Exception as e:
            ko += 1
            print("  FAIL  %s (eccezione sbagliata: %r)" % (nome, e))
            return
        ko += 1
        print("  FAIL  %s (non ha rifiutato)" % nome)

    # --- estrazione dei percorsi ------------------------------------------ #
    e = percorsi_da_record({"a": "prodotto da src/paper2_censimento_registri.py v1.4 il 15 set"})
    controlla("estrae da prosa", e == {"src/paper2_censimento_registri.py"})
    e = percorsi_da_record({"a": "src\\paper2_v1_amendments.jsonl su crashsafe"})
    controlla("normalizza il backslash", e == {"src/paper2_v1_amendments.jsonl"})
    e = percorsi_da_record({"a": "x: results/a.jsonl; results/b.npz; src/c.py"})
    controlla("lista separata da ;", e == {"results/a.jsonl", "results/b.npz", "src/c.py"})
    e = percorsi_da_record({"a": "finisce in src/paper2_deposit.py."})
    controlla("punto finale non entra", e == {"src/paper2_deposit.py"})
    e = percorsi_da_record({"a": "gate53.jsonl senza cartella"})
    controlla("limite: senza separatore non e' percorso", e == set())
    e = percorsi_da_record({"a": "la cartella results/paper2 da sola"})
    controlla("limite: senza estensione non e' percorso", e == set())
    e = percorsi_da_record({"a": "results/paper2/per_mock_*_erosion.jsonl"})
    controlla("pattern riconosciuto", e == {"results/paper2/per_mock_*_erosion.jsonl"})
    e = percorsi_da_record({"a": ["dentro/una/lista.json", {"b": "dentro/un/dizionario.md"}]})
    controlla("cammina liste e dizionari",
              e == {"dentro/una/lista.json", "dentro/un/dizionario.md"})
    e = percorsi_da_record({"a": "citato D:\\projects\\cauchy\\data\\raw\\x.txt qui"})
    controlla("assoluto col drive: intero", e == {"D:/projects/cauchy/data/raw/x.txt"})
    controlla("relativizza dentro la radice",
              relativizza("D:/p/c/data/x.txt", "/nulla") == "D:/p/c/data/x.txt")
    controlla("RE_ASSOLUTO riconosce il drive",
              bool(RE_ASSOLUTO.match("D:/x/y.py")) and not RE_ASSOLUTO.match("src/y.py"))
    e = percorsi_da_record({"a": "./src/x.py"})
    controlla("togli il ./ iniziale", e == {"src/x.py"})
    e = percorsi_da_record({"a": "due volte src/x.py e src/x.py"})
    controlla("deduplica", e == {"src/x.py"})
    controlla("normalizza(): virgola finale", normalizza("src/x.py,") == "src/x.py")
    controlla("RE_META: pattern", bool(RE_META.search("a/b*.py")))
    controlla("RE_META: normale", not RE_META.search("a/b.py"))

    # --- eccezioni -------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        q = Path(td) / "ecc.json"
        q.write_text(json.dumps({"logs/x.jsonl": "motivo abbastanza lungo"}), encoding="utf-8")
        controlla("eccezioni caricate", carica_eccezioni(str(q)) ==
                  {"logs/x.jsonl": "motivo abbastanza lungo"})
        q.write_text(json.dumps({"logs/x.jsonl": "corto"}), encoding="utf-8")
        rifiuta("eccezione senza motivo scritto", lambda: carica_eccezioni(str(q)))
        q.write_text(json.dumps(["lista"]), encoding="utf-8")
        rifiuta("eccezioni non oggetto", lambda: carica_eccezioni(str(q)))
        rifiuta("file delle eccezioni assente",
                lambda: carica_eccezioni(str(Path(td) / "non_c_e.json")))
        controlla("nessuna eccezione = dizionario vuoto", carica_eccezioni(None) == {})

    # --- pipeline su un repo finto ---------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _repo_finto(base)
        _ledger_finto(base, [
            {"json_path": "src/tracciato_pulito.py", "numbering_rule": "record 1."},
            {"json_path": "src/tracciato_mod.py; results/paper2/non_tracciato.jsonl",
             "numbering_rule": "record 2."},
            {"evidence": "logs/prova.jsonl e papers/paper2/doc.md",
             "numbering_rule": "record 3."},
            {"evidence": "results/paper2/mai_esistito.jsonl e results/x/*.jsonl",
             "numbering_rule": "record 4."},
        ])

        class A:
            radice = str(base)
            ledger = "src/amend.jsonl"
            attesi_record = 4
            eccezioni = None
            out = "logs/censimento_rilascio.jsonl"

        controlla("git: tracciati", tracciati(base) ==
                  {".gitignore", "src/tracciato_pulito.py", "src/tracciato_mod.py"})
        controlla("git: sporchi", sporchi(base) == {"src/tracciato_mod.py": "M"})
        controlla("git: ingresso con CR rifiutato",
                  _rifiuta_cr(base))
        controlla("git: non tracciati visibili",
                  non_tracciati_visibili(base) == {"results/paper2/non_tracciato.jsonl",
                                                   "src/amend.jsonl"})
        ign = esclusi(base, ["logs/prova.jsonl", "papers/paper2/doc.md",
                             "results/paper2/non_tracciato.jsonl"])
        controlla("git: esclusi trovati", set(ign) ==
                  {"logs/prova.jsonl", "papers/paper2/doc.md"})
        controlla("git: regola riportata", "logs/" in ign["logs/prova.jsonl"])
        controlla("git: check-ignore non inventa",
                  "results/paper2/non_tracciato.jsonl" not in ign)

        esito = cmd_censimento(A())
        controlla("censimento: uscita 1 con cose da decidere", esito == 1)

        reg = [json.loads(r) for r in
               (base / "logs" / "censimento_rilascio.jsonl").read_text(
                   encoding="utf-8").splitlines()]
        controlla("registro: una riga", len(reg) == 1)
        r = reg[0]
        controlla("registro: 7 percorsi distinti", r["percorsi_distinti"] == 7)
        c = r["conteggi"]
        controlla("classifica: 1 tracciato pulito", c["tracciato_pulito"] == 1)
        controlla("classifica: 1 tracciato modificato", c["tracciato_modificato"] == 1)
        controlla("classifica: 1 da aggiungere", c["da_aggiungere"] == 1)
        controlla("classifica: 2 esclusi", c["escluso"] == 2)
        controlla("classifica: 1 assente", c["assente"] == 1)
        controlla("classifica: 1 pattern", c["NA_pattern"] == 1)
        controlla("classifica: somma = distinti", sum(c.values()) == r["percorsi_distinti"])
        controlla("verdetto citati_esistono FAIL", r["verdetti"]["citati_esistono"] == "FAIL")
        controlla("verdetto citati_tracciati FAIL", r["verdetti"]["citati_tracciati"] == "FAIL")
        controlla("verdetto citati_non_esclusi FAIL",
                  r["verdetti"]["citati_non_esclusi"] == "FAIL")
        controlla("verdetto citati_committati FAIL",
                  r["verdetti"]["citati_committati"] == "FAIL")
        controlla("verdetto metri_concordi PASS",
                  r["verdetti"]["metri_concordi"] == "PASS")
        controlla("esclusi trovati dal secondo metro",
                  set(r["per_stato"]["escluso"]) ==
                  {"logs/prova.jsonl", "papers/paper2/doc.md"})
        controlla("la regola di .gitignore e' nel motivo",
                  "logs/" in r["motivi"]["logs/prova.jsonl"])
        controlla("registro: il ledger e' ancorato per sha",
                  len(r["ledger_sha256"]) == 64)
        controlla("registro: il pattern e' nominato",
                  r["per_stato"]["NA_pattern"] == ["results/x/*.jsonl"])
        controlla("registro: l'assente e' nominato",
                  r["per_stato"]["assente"] == ["results/paper2/mai_esistito.jsonl"])

        # con le eccezioni dichiarate, i due esclusi cambiano stato
        ecc = base / "logs" / "ecc.json"
        ecc.write_text(json.dumps({
            "logs/prova.jsonl": "prova del censimento, fuori dal tag per scelta",
            "papers/paper2/doc.md": "documento di lavoro, fuori dal versionamento",
        }, ensure_ascii=False), encoding="utf-8")

        class B(A):
            eccezioni = str(ecc)
            out = "logs/censimento2.jsonl"

        cmd_censimento(B())
        r2 = json.loads((base / "logs" / "censimento2.jsonl").read_text(
            encoding="utf-8").splitlines()[0])
        controlla("eccezioni: zero esclusi senza motivo", r2["conteggi"]["escluso"] == 0)
        controlla("eccezioni: due con motivo", r2["conteggi"]["escluso_con_eccezione"] == 2)
        controlla("eccezioni: verdetto citati_non_esclusi PASS",
                  r2["verdetti"]["citati_non_esclusi"] == "PASS")
        controlla("eccezioni: il motivo finisce nel registro",
                  "fuori dal tag" in r2["motivi"]["logs/prova.jsonl"])
        controlla("eccezioni: registrate nel record",
                  len(r2["eccezioni_dichiarate"]) == 2)
        controlla("eccezioni: non sanano l'assente",
                  r2["verdetti"]["citati_esistono"] == "FAIL")

        ecc.write_text(json.dumps({
            "results/paper2/mai_esistito.jsonl": "citato dal record per dire che non c'era",
        }, ensure_ascii=False), encoding="utf-8")

        class B2(A):
            eccezioni = str(ecc)
            out = "logs/censimento3.jsonl"

        cmd_censimento(B2())
        r3 = json.loads((base / "logs" / "censimento3.jsonl").read_text(
            encoding="utf-8").splitlines()[0])
        controlla("eccezione sull'assente: stato dedicato",
                  r3["conteggi"]["assente_con_eccezione"] == 1)
        controlla("eccezione sull'assente: verdetto PASS",
                  r3["verdetti"]["citati_esistono"] == "PASS")

        class C(A):
            attesi_record = 68

        rifiuta("cancello: numero di record sbagliato", lambda: cmd_censimento(C()))

        class D(A):
            ledger = "src/non_c_e.jsonl"

        rifiuta("cancello: ledger assente", lambda: cmd_censimento(D()))

        (base / "src" / "rotto.jsonl").write_bytes(b'{"a":1}\nnon json\n')

        class E(A):
            ledger = "src/rotto.jsonl"
            attesi_record = 2

        rifiuta("cancello: riga non parsabile", lambda: cmd_censimento(E()))

    # --- tutto pulito: uscita 0 ------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        _repo_finto(base)
        git(base, "add", "-A")
        git(base, "commit", "-q", "-m", "tutto")
        _ledger_finto(base, [
            {"json_path": "src/tracciato_pulito.py", "numbering_rule": "record 1."},
        ])
        git(base, "add", "src/amend.jsonl")
        git(base, "commit", "-q", "-m", "ledger")

        class F:
            radice = str(base)
            ledger = "src/amend.jsonl"
            attesi_record = 1
            eccezioni = None
            out = None

        controlla("censimento: uscita 0 quando tutto passa", cmd_censimento(F()) == 0)

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Censimento della popolazione del rilascio")
    ap.add_argument("comando", choices=["selftest", "censimento"])
    ap.add_argument("--radice", default=".")
    ap.add_argument("--ledger", default="src/paper2_v1_amendments.jsonl")
    ap.add_argument("--attesi-record", type=int, default=None,
                    help="rifiuta se il ledger non ha esattamente questi record")
    ap.add_argument("--eccezioni", default=None,
                    help="JSON {percorso: motivo} dei citati esclusi per scelta")
    ap.add_argument("--out", default=None, help="registro jsonl in append")
    args = ap.parse_args(argv)
    try:
        return (cmd_selftest if args.comando == "selftest" else cmd_censimento)(args)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

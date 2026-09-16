#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""paper2_patch_regole_git.py — ordine di `.gitattributes` e portata di `.gitignore`.

DUE DIFETTI, misurati il 15 settembre 2026.

1. `.gitattributes` dichiara in testa «Nessuna normalizzazione su NULLA dentro
   results/ e MANIFESTS/» e poi, in coda, `*.py text` / `*.md text` / `*.txt text`.
   In `.gitattributes` VINCE L'ULTIMA REGOLA CHE COMBACIA, quindi per ogni `.md`,
   `.txt` e `.py` dentro `results/` la regola larga e' scavalcata. Tre file del
   tier congelato `records` risultano `attr/text`:
       results/paper1/src_bundle_phase9.txt
       results/phase5_hod_variance_decomp_summary.md
       results/revision/env_versions.txt
   I loro byte sono in un manifest con un digest. Un checkout con
   `core.autocrlf=false` li scrive a LF e il congelamento esce MISMATCH.
   Rimedio: le regole di CARTELLA vanno in fondo, dopo quelle di tipo.

2. `.gitignore` esclude `papers/` e `logs/` con una riga secca ciascuno, piu'
   larga del motivo. Dentro ci sono cinque `.md` e tre registri che i record del
   ledger citano come prova: un rilascio il cui ledger cita documenti che il
   rilascio non contiene non e' verificabile. Rimedio: regole strette.
   git NON SCENDE in una cartella esclusa, quindi `papers/` va sostituita e non
   negata; `logs/` diventa `logs/*`, che si nega file per file.

In piu': `*.npz` esclude `results/paper2/phase7_pk_nwlh_kref.npz`, 1 684 byte di
provenienza (l'asse k delle 110 colonne di pk_matrix, records 61 e 62), per una
regola scritta per i cubi di campo. Riammesso per nome.

CANCELLO SHA ASSENTE, E PERCHE'. I patcher di questo progetto si ancorano allo
sha256 dei byte di partenza. Qui non si puo': `.gitignore` non e' mai stato letto
per intero. Al suo posto, tre cose: ogni ancora deve comparire ESATTAMENTE una
volta o il patcher rifiuta; `dryrun` stampa il diff e non scrive; `apply` scrive
la copia di sicurezza in `logs/` e riporta lo sha di prima e di dopo, perche' da
quel momento un'ancora esista.

Sottocomandi:

    python src\paper2_patch_regole_git.py selftest
    python src\paper2_patch_regole_git.py dryrun
    python src\paper2_patch_regole_git.py apply
    python src\paper2_patch_regole_git.py controlla

`controlla` verifica le conseguenze, non il testo: i tre file del tier tornano
`-text`, i sorgenti hanno `eol=lf`, e gli otto percorsi citati diventano
visibili a git. Va eseguito DOPO `apply`.

NON fa: non aggiunge niente all'indice, non committa, non tocca i byte di
nessun file di risultato. La riparazione dell'indice per i tre file del tier e'
una sequenza di comandi git, dichiarata in coda a `apply`.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSIONE = "1.3"

# --------------------------------------------------------------------------- #

FILE_TIER_TEXT = [
    "results/paper1/src_bundle_phase9.txt",
    "results/phase5_hod_variance_decomp_summary.md",
    "results/revision/env_versions.txt",
]

CITATI_DA_RIAMMETTERE = [
    "papers/paper2/paper2_5_5_smentite.md",
    "papers/paper2/paper2_budget_5_1.md",
    "papers/paper2/paper2_residui_fase4.md",
    "papers/paper2/paper2_5_4_practice.md",
    "papers/paper2/modifiche_paper1.md",
    "logs/censimento_v14.jsonl",
    "logs/prov_pk.jsonl",
    "logs/ladder_sigma.jsonl",
    "results/paper2/phase7_pk_nwlh_kref.npz",
]

SORGENTI_EOL_LF = ("*.py", "*.md")

CODA_ATTRIBUTI = """
# ============================================================
# ULTIME, e non prime: in .gitattributes vince l'ultima regola
# che combacia. Messe in testa venivano scavalcate da *.md,
# *.txt e *.py per i file di risultato che hanno quelle
# estensioni — tre dei quali sono nel tier congelato records,
# con un digest sui byte. Qui in coda riprendono la precedenza
# che il commento in testa gli attribuiva.
# ============================================================
results/**      -text
manifests/**    -text
"""

BLOCCO_PAPERS = """# papers/: i documenti di lavoro ENTRANO nel versionamento — cinque di essi sono
# citati dai record del ledger, e paper2_5_5_smentite.md da sei record. Restano
# fuori la corrispondenza coi referee e tutto cio' che e' compilato o ricostruibile.
papers/m26/
papers/*/MNRAS/
papers/**/*.pdf
papers/**/*.eml
papers/**/*.zip
papers/**/*.gz
papers/**/*.docx
papers/**/*.bbl"""

BLOCCO_LOGS = """# logs/: sentiero di lavoro, fuori dal rilascio — comprese tutte le copie .bak_*
# dei patcher. Entrano SOLO i registri che un record cita come prova: il
# censimento dei registri (record 68), la provenienza di pk_matrix (62), la
# scala sigma (51). `logs/*` e non `logs/`, perche' una cartella esclusa non si
# puo' negare file per file: git non ci scende.
logs/*
!logs/censimento_v14.jsonl
!logs/prov_pk.jsonl
!logs/ladder_sigma.jsonl"""

CODA_IGNORE = """
# ============================================================
# Riammissioni per nome, dopo ogni regola che le escluderebbe.
# ============================================================
# 1 684 byte: l'asse k delle 110 colonne di pk_matrix, records 61 e 62. La regola
# *.npz e' scritta per i cubi di campo (il tier fields pesa 18,4 GB); questo e'
# un artefatto di provenienza, e senza di esso chi verifica dall'esterno non ha
# l'asse k. Delimitare per estensione e' l'errore del record 68.
!results/paper2/phase7_pk_nwlh_kref.npz
"""


MARCA_ATTRIBUTI = "vince l'ultima regola"
NEG_KREF = "!results/paper2/phase7_pk_nwlh_kref.npz"


class Rifiuto(Exception):
    """Un cancello non e' passato. Nessun file e' stato scritto."""


# --------------------------------------------------------------------------- #

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def leggi(p: Path) -> bytes:
    if not p.is_file():
        raise Rifiuto("file assente: %s" % p)
    return p.read_bytes()


def profilo_eol(b: bytes):
    """(CRLF, LF, maggioranza). Un profilo misto si DICHIARA, non si normalizza."""
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    if crlf + lf == 0:
        raise Rifiuto("file senza fine riga: non e' quello atteso")
    return crlf, lf, ("\r\n" if crlf > lf else "\n")


def righe(b: bytes) -> list:
    """Righe CON il loro terminatore: cio' che non si tocca resta byte per byte."""
    return b.decode("utf-8").splitlines(keepends=True)


def term(riga: str) -> str:
    if riga.endswith("\r\n"):
        return "\r\n"
    return "\n" if riga.endswith("\n") else ""


def corpo(riga: str) -> str:
    t = term(riga)
    return riga[:len(riga) - len(t)] if t else riga


def blocco(testo: str, eol: str, terminatore: str) -> str:
    """Un blocco nuovo nasce col fine riga di maggioranza, e chiude come la riga
    che sostituisce."""
    if "\r" in testo:
        raise Rifiuto("CR dentro un blocco costruito")
    return eol.join(testo.split("\n")) + terminatore


def una_riga(rs: list, prova, nome: str) -> int:
    idx = [i for i, r in enumerate(rs) if prova(corpo(r))]
    if len(idx) != 1:
        raise Rifiuto("ancora %s trovata %d volte, attesa 1" % (nome, len(idx)))
    return idx[0]


def primo_token(riga: str) -> str:
    parti = riga.split()
    return parti[0] if parti else ""


# --------------------------------------------------------------------------- #
# .gitattributes
# --------------------------------------------------------------------------- #

def nuovo_gitattributes(b: bytes) -> bytes:
    if MARCA_ATTRIBUTI in b.decode("utf-8"):
        return None
    _, _, eol = profilo_eol(b)
    rs = righe(b)

    i_res = una_riga(rs, lambda r: primo_token(r) == "results/**", "results/** in attributes")
    i_man = una_riga(rs, lambda r: primo_token(r) == "manifests/**", "manifests/** in attributes")
    if "-text" not in corpo(rs[i_res]) or "-text" not in corpo(rs[i_man]):
        raise Rifiuto("le due regole di cartella non portano -text: non e' il file atteso")
    if i_man != i_res + 1:
        raise Rifiuto("results/** e manifests/** non sono righe consecutive")
    i_commento = i_res - 1
    if not corpo(rs[i_commento]).lstrip().startswith("#"):
        raise Rifiuto("sopra results/** non c'e' il commento atteso")

    # le regole di tipo devono stare PRIMA, altrimenti lo spostamento non serve
    for tipo in SORGENTI_EOL_LF:
        i = una_riga(rs, lambda r, t=tipo: primo_token(r) == t, "regola %s" % tipo)
        if i < i_res:
            raise Rifiuto(
                "%s e' gia' prima di results/**: l'ordine non e' quello misurato" % tipo
            )

    fuori = rs[:i_commento] + rs[i_man + 1:]

    for tipo in SORGENTI_EOL_LF:
        i = una_riga(fuori, lambda r, t=tipo: primo_token(r) == t, "regola %s" % tipo)
        if "eol=" in corpo(fuori[i]):
            raise Rifiuto("%s ha gia' un eol=: non lo tocco" % tipo)
        fuori[i] = "%-8s%s%s" % (tipo, "text eol=lf", term(fuori[i]) or eol)

    if fuori and not term(fuori[-1]):
        fuori[-1] += eol
    fuori.append(blocco("\n" + CODA_ATTRIBUTI.strip("\n"), eol, eol))
    return "".join(fuori).encode("utf-8")


# --------------------------------------------------------------------------- #
# .gitignore
# --------------------------------------------------------------------------- #

def _estensione_blocco(rs: list, testo: str, nome: str):
    """(inizio, fine) del blocco se c'e', None se non c'e'."""
    prima, ultima = testo.split("\n")[0], testo.split("\n")[-1]
    a = [i for i, r in enumerate(rs) if corpo(r) == prima]
    if not a:
        return None
    if len(a) > 1:
        raise Rifiuto("blocco %s trovato %d volte" % (nome, len(a)))
    z = [i for i, r in enumerate(rs) if corpo(r) == ultima and i >= a[0]]
    if not z:
        raise Rifiuto("blocco %s aperto e non chiuso: coda %r assente" % (nome, ultima))
    return a[0], z[0]


def _sezione(rs: list, testo: str, riga_secca: str, politica: str,
             eol: str, nome: str) -> bool:
    """Porta la sezione nello stato richiesto. True se ha cambiato qualcosa.

    dentro: la riga secca diventa il blocco stretto.
    fuori:  il blocco stretto torna la riga secca. Reversibile nei due versi,
            cosi' una decisione si puo' cambiare senza ripescare un backup."""
    if politica not in ("dentro", "fuori"):
        raise Rifiuto("politica %r sconosciuta per %s" % (politica, nome))
    esteso = _estensione_blocco(rs, testo, nome)
    if politica == "dentro":
        if esteso:
            return False
        i = una_riga(rs, lambda r: r.strip() == riga_secca, "riga %s" % riga_secca)
        rs[i] = blocco(testo, eol, term(rs[i]) or eol)
        return True
    if not esteso:
        return False
    a, z = esteso
    rs[a:z + 1] = [riga_secca + (term(rs[z]) or eol)]
    return True


def nuovo_gitignore(b: bytes, papers: str = "fuori", logs: str = "fuori"):
    _, _, eol = profilo_eol(b)
    rs = righe(b)
    cambiato = False

    cambiato |= _sezione(rs, BLOCCO_LOGS, "logs/", logs, eol, "logs")
    cambiato |= _sezione(rs, BLOCCO_PAPERS, "papers/", papers, eol, "papers")

    if not any(corpo(r).strip() == NEG_KREF for r in rs):
        una_riga(rs, lambda r: primo_token(r) == "*.npz", "regola *.npz")
        if rs and not term(rs[-1]):
            rs[-1] += eol
        rs.append(blocco("\n" + CODA_IGNORE.strip("\n"), eol, eol))
        cambiato = True

    return "".join(rs).encode("utf-8") if cambiato else None


# --------------------------------------------------------------------------- #

def prepara(radice: Path, papers="fuori", logs="fuori") -> tuple:
    coppie, salti = [], []
    for nome, fn in ((".gitattributes", lambda x: nuovo_gitattributes(x)),
                     (".gitignore", lambda x: nuovo_gitignore(x, papers, logs))):
        p = radice / nome
        vecchio = leggi(p)
        nuovo = fn(vecchio)
        if nuovo is None or nuovo == vecchio:
            salti.append(nome)
            continue
        coppie.append((p, vecchio, nuovo))
    if not coppie:
        raise Rifiuto("entrambi i file sono gia' nello stato richiesto: %s"
                      % ", ".join(salti))
    return coppie, salti


def cmd_dryrun(args) -> int:
    coppie, salti = prepara(Path(args.radice), args.papers, args.logs)
    print("politica: papers %s, logs %s" % (args.papers, args.logs))
    for nome in salti:
        print("  %s: gia' nello stato richiesto, non toccato" % nome)
    for p, vecchio, nuovo in coppie:
        print("=== %s ===" % p.name)
        for riga in difflib.unified_diff(
            vecchio.decode("utf-8").splitlines(), nuovo.decode("utf-8").splitlines(),
            fromfile="prima", tofile="dopo", lineterm="", n=2,
        ):
            print(riga)
        c, l, e = profilo_eol(vecchio)
        print("\n  fine riga: %d CRLF, %d LF  (le righe non toccate restano come sono;"
              " le nuove nascono %s)" % (c, l, "CRLF" if e == "\r\n" else "LF"))
        print("  prima: %s  %d byte" % (sha256(vecchio), len(vecchio)))
        print("  dopo:  %s  %d byte\n" % (sha256(nuovo), len(nuovo)))
    print("DRYRUN: nessun file scritto.")
    return 0


def cmd_apply(args) -> int:
    radice = Path(args.radice)
    coppie, salti = prepara(radice, args.papers, args.logs)
    print("politica: papers %s, logs %s" % (args.papers, args.logs))
    for nome in salti:
        print("  %s: gia' nello stato richiesto, non toccato" % nome)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cartella = radice / args.logs_dir
    cartella.mkdir(parents=True, exist_ok=True)
    for p, vecchio, _ in coppie:
        b = cartella / ("%s.bak_%s" % (p.name, marca))
        if b.exists():
            raise Rifiuto("backup gia' esistente: %s" % b)
        b.write_bytes(vecchio)
        print("backup   %s" % b)
    for p, vecchio, nuovo in coppie:
        p.write_bytes(nuovo)
        letto = leggi(p)
        if letto != nuovo:
            raise Rifiuto("%s: scritto ma rileggendo i byte non combaciano" % p.name)
        print("scritto  %-16s %s -> %s  %d byte"
              % (p.name, sha256(vecchio)[:12], sha256(letto)[:12], len(letto)))
    print("""
APPLY: OK. Restano DUE cose, e non le fa questo patcher.

1. L'INDICE dei tre file del tier `records` porta ancora i byte normalizzati a
   LF, mentre il manifest ha il digest dei byte su disco. Con le regole corrette
   vanno riletti dall'indice, una volta sola:

     git add -- results/paper1/src_bundle_phase9.txt results/phase5_hod_variance_decomp_summary.md results/revision/env_versions.txt
     git ls-files --eol -- results/paper1/src_bundle_phase9.txt results/phase5_hod_variance_decomp_summary.md results/revision/env_versions.txt

   Atteso: `i/crlf w/crlf attr/-text` su tutti tre. Poi `freeze_verify`, che
   deve restare CLEAN: se esce MISMATCH, i byte su disco sono cambiati e si
   ripristina dal backup.

2. La rinormalizzazione dei veri file di testo, nel SUO commit e prima dei
   contenuti:

     git add --renormalize .
     git status --short

   Atteso: tre soli file toccati — CAUCHY_Review_and_GATE.md,
   src/phase5bis_growth_factor.py, src/phase8_test2_masked.py — nessuno dei
   quali e' citato da un record. Se ne compaiono altri, fermarsi e leggere.
""")
    return 0


# --------------------------------------------------------------------------- #

def git(radice: Path, *arg, ammetti=(0,)) -> str:
    try:
        r = subprocess.run(["git"] + list(arg), cwd=str(radice), capture_output=True)
    except FileNotFoundError:
        raise Rifiuto("git non trovato nel PATH")
    if r.returncode not in ammetti:
        raise Rifiuto("git %s uscito %d" % (" ".join(arg), r.returncode))
    return r.stdout.decode("utf-8", "replace")


def cmd_controlla(args) -> int:
    radice = Path(args.radice)
    esito = 0

    print("--- i tre file del tier records devono essere -text ---")
    for riga in git(radice, "check-attr", "text", "--", *FILE_TIER_TEXT).splitlines():
        ok = riga.strip().endswith("unset")
        esito |= 0 if ok else 1
        print("  [%s] %s" % ("ok" if ok else "fail", riga))

    print("\n--- i sorgenti devono avere eol=lf ---")
    for riga in git(radice, "check-attr", "eol", "--",
                    "src/paper2_freeze_verify.py",
                    "papers/paper2/checklist_paper2.md").splitlines():
        ok = riga.strip().endswith("lf")
        esito |= 0 if ok else 1
        print("  [%s] %s" % ("ok" if ok else "fail", riga))

    attesi_visibili = ["results/paper2/phase7_pk_nwlh_kref.npz"]
    if args.papers == "dentro":
        attesi_visibili += [p for p in CITATI_DA_RIAMMETTERE if p.startswith("papers/")]
    if args.logs == "dentro":
        attesi_visibili += [p for p in CITATI_DA_RIAMMETTERE if p.startswith("logs/")]
    attesi_fuori = [p for p in CITATI_DA_RIAMMETTERE if p not in attesi_visibili]

    print("\n--- i citati attesi DENTRO devono essere visibili a git ---")
    visibili = set()
    for riga in git(radice, "-c", "core.quotepath=false", "status", "--porcelain",
                    "--untracked-files=all").splitlines():
        if riga.startswith("?? "):
            visibili.add(riga[3:].strip('"').replace("\\", "/"))
    for p in attesi_visibili:
        tracciato = bool(git(radice, "ls-files", "--", p).strip())
        ok = p in visibili or tracciato
        esito |= 0 if ok else 1
        print("  [%s] %-52s %s" % ("ok" if ok else "fail", p,
                                   "tracciato" if tracciato else
                                   ("visibile" if ok else "ancora escluso")))

    if attesi_fuori:
        print("\n--- i citati attesi FUORI devono restare esclusi ---")
        print("      (ognuno va dichiarato nelle eccezioni del censimento, con un")
        print("       motivo e, se non ha altro ancoraggio, un digest)")
        for p in attesi_fuori:
            tracciato = bool(git(radice, "ls-files", "--", p).strip())
            ok = not (p in visibili or tracciato)
            esito |= 0 if ok else 1
            print("  [%s] %-52s %s" % ("ok" if ok else "fail", p,
                                       "escluso" if ok else "VISIBILE, non atteso"))

    print("\n--- nessuna copia .bak_ o .pre deve essere entrata ---")
    intrusi = sorted(p for p in visibili if ".bak_" in p or "/.pre" in p or ".pre" in Path(p).suffix)
    esito |= 1 if intrusi else 0
    print("  [%s] %d intrusi" % ("ok" if not intrusi else "fail", len(intrusi)))
    for p in intrusi[:10]:
        print("      %s" % p)

    print("\nCONTROLLA: %s" % ("OK" if esito == 0 else "FALLITO"))
    return esito


# --------------------------------------------------------------------------- #

ATTRIBUTI_FINTO = """# CAUCHY - .gitattributes

# Nessuna normalizzazione su NULLA dentro results/ e MANIFESTS/.
results/**      -text
manifests/**    -text

# I formati append-only.
*.jsonl         -text
*.json          -text

# Binari.
*.npz   binary

# Sorgenti e documenti: normalizzazione normale.
*.py    text
*.md    text
*.txt   text
*.ps1   text eol=crlf
"""

IGNORE_FINTO = """# CAUCHY - .gitignore
__pycache__/
*.npz

prompts/
papers/m26/
papers/paper1/MNRAS/

backup/
logs/

deposit/

papers/

*.pre*
*.tmp
"""


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

    # --- .gitattributes --------------------------------------------------- #
    b = ATTRIBUTI_FINTO.encode("utf-8")
    n = nuovo_gitattributes(b)
    t = n.decode("utf-8")
    rs = t.split("\n")
    i_res = [i for i, r in enumerate(rs) if primo_token(r) == "results/**"]
    i_py = [i for i, r in enumerate(rs) if primo_token(r) == "*.py"]
    controlla("attributes: results/** resta una volta sola", len(i_res) == 1)
    controlla("attributes: results/** ora e' DOPO *.py", i_res[0] > i_py[0])
    controlla("attributes: manifests/** spostato",
              t.count("manifests/**") == 1 and t.index("manifests/**") > t.index("*.py"))
    controlla("attributes: *.py con eol=lf", "*.py     text eol=lf" in t or
              any(primo_token(r) == "*.py" and "eol=lf" in r for r in rs))
    controlla("attributes: *.md con eol=lf",
              any(primo_token(r) == "*.md" and "eol=lf" in r for r in rs))
    controlla("attributes: *.txt NON toccato",
              any(r.split() == ["*.txt", "text"] for r in rs))
    controlla("attributes: *.ps1 intatto", "*.ps1   text eol=crlf" in t)
    controlla("attributes: -text dei jsonl intatto",
              any(r.split() == ["*.jsonl", "-text"] for r in rs))
    controlla("attributes: il commento della coda c'e'",
              "vince l'ultima regola" in t)
    controlla("attributes: riga vuota prima della coda",
              "eol=crlf\n\n# ====" in t)
    controlla("ignore: riga vuota prima della coda",
              "*.tmp\n\n# ====" in nuovo_gitignore(IGNORE_FINTO.encode("utf-8"), "dentro", "dentro").decode("utf-8"))
    controlla("attributes: nessuna riga persa",
              len([r for r in rs if r.strip() and not r.startswith("#")]) ==
              len([r for r in ATTRIBUTI_FINTO.split("\n")
                   if r.strip() and not r.startswith("#")]))
    controlla("attributes: fine riga conservato (LF)", b"\r" not in n)
    crlf = ATTRIBUTI_FINTO.replace("\n", "\r\n").encode("utf-8")
    n_crlf = nuovo_gitattributes(crlf)
    controlla("attributes: fine riga conservato (CRLF)",
              b"\r\r" not in n_crlf and n_crlf.count(b"\r\n") == n.count(b"\n")
              and n_crlf.replace(b"\r\n", b"\n") == n)
    controlla("attributes: idempotenza = niente da fare", nuovo_gitattributes(n) is None)
    rifiuta("attributes: senza results/**",
            lambda: nuovo_gitattributes(
                ATTRIBUTI_FINTO.replace("results/**      -text\n", "").encode("utf-8")))
    rifiuta("attributes: results/** due volte",
            lambda: nuovo_gitattributes(
                (ATTRIBUTI_FINTO + "results/** -text\n").encode("utf-8")))
    rifiuta("attributes: righe non consecutive",
            lambda: nuovo_gitattributes(ATTRIBUTI_FINTO.replace(
                "results/**      -text\nmanifests/**    -text",
                "results/**      -text\n\nmanifests/**    -text").encode("utf-8")))
    misto = ATTRIBUTI_FINTO.replace("*.txt   text\n", "*.txt   text\r\n").encode("utf-8")
    n_misto = nuovo_gitattributes(misto)
    controlla("attributes: profilo misto accettato", profilo_eol(misto) == (1, 17, "\n"))
    controlla("attributes: la riga con CRLF resta intatta", b"*.txt   text\r\n" in n_misto)
    controlla("attributes: un solo CR, nessuno introdotto", n_misto.count(b"\r") == 1)
    controlla("attributes: la riga toccata conserva il suo terminatore",
              b"*.py    text eol=lf\n" in n_misto)
    controlla("attributes: i blocchi nuovi nascono con la maggioranza",
              b"results/**      -text\n" in n_misto)
    controlla("attributes: a meno del CRLF, identico al caso pulito",
              n_misto.replace(b"*.txt   text\r\n", b"*.txt   text\n") == n)
    rifiuta("attributes: file senza fine riga",
            lambda: nuovo_gitattributes(b"*.py text"))

    # --- .gitignore ------------------------------------------------------- #
    b2 = IGNORE_FINTO.encode("utf-8")
    n2 = nuovo_gitignore(b2, "dentro", "dentro")
    t2 = n2.decode("utf-8")
    controlla("ignore: papers/ secco sparito",
              not any(r.strip() == "papers/" for r in t2.split("\n")))
    controlla("ignore: papers/m26/ resta", "papers/m26/" in t2)
    controlla("ignore: i pdf di papers esclusi", "papers/**/*.pdf" in t2)
    controlla("ignore: logs/ secco sparito",
              not any(r.strip() == "logs/" for r in t2.split("\n")))
    controlla("ignore: logs/* c'e'",
              any(r.strip() == "logs/*" for r in t2.split("\n")))
    controlla("ignore: le tre prove riammesse",
              all("!logs/%s" % f in t2 for f in
                  ("censimento_v14.jsonl", "prov_pk.jsonl", "ladder_sigma.jsonl")))
    i_npz = t2.index("*.npz")
    i_neg = t2.index("!results/paper2/phase7_pk_nwlh_kref.npz")
    controlla("ignore: la riammissione del kref viene DOPO *.npz", i_neg > i_npz)
    controlla("ignore: le negazioni di logs vengono dopo logs/*",
              t2.index("!logs/censimento_v14.jsonl") > t2.index("logs/*"))
    controlla("ignore: *.pre* intatto",
              any(r.strip() == "*.pre*" for r in t2.split("\n")))
    controlla("ignore: deposit/ intatto",
              any(r.strip() == "deposit/" for r in t2.split("\n")))
    controlla("ignore: fine riga conservato", b"\r" not in n2)
    n2_crlf = nuovo_gitignore(IGNORE_FINTO.replace("\n", "\r\n").encode("utf-8"),
                              "dentro", "dentro")
    controlla("ignore: CRLF conservato", b"\r\r" not in n2_crlf
              and n2_crlf.count(b"\r\n") == n2.count(b"\n")
              and n2_crlf.replace(b"\r\n", b"\n") == n2)
    misto_ign = IGNORE_FINTO.replace("deposit/\n", "deposit/\r\n").encode("utf-8")
    n_mi = nuovo_gitignore(misto_ign, "dentro", "dentro")
    controlla("ignore: la riga con CRLF resta intatta", b"deposit/\r\n" in n_mi)
    controlla("ignore: nessun CR introdotto", n_mi.count(b"\r") == 1)
    controlla("ignore: a meno del CRLF, identico al caso pulito",
              n_mi.replace(b"deposit/\r\n", b"deposit/\n") == n2)
    controlla("ignore: idempotenza = niente da fare",
              nuovo_gitignore(n2, "dentro", "dentro") is None)
    rifiuta("ignore: senza riga papers/",
            lambda: nuovo_gitignore(IGNORE_FINTO.replace("\npapers/\n", "\n").encode("utf-8"), "dentro", "dentro"))
    rifiuta("ignore: senza *.npz",
            lambda: nuovo_gitignore(IGNORE_FINTO.replace("*.npz\n", "").encode("utf-8"), "dentro", "dentro"))
    rifiuta("ignore: logs/ due volte",
            lambda: nuovo_gitignore((IGNORE_FINTO + "logs/\n").encode("utf-8"), "dentro", "dentro"))

    # politica di default: papers e logs restano fuori, entra solo il kref
    n2f = nuovo_gitignore(b2)
    t2f = n2f.decode("utf-8")
    controlla("default: papers/ resta la riga secca",
              any(r.strip() == "papers/" for r in t2f.split("\n")))
    controlla("default: logs/ resta la riga secca",
              any(r.strip() == "logs/" for r in t2f.split("\n")))
    controlla("default: nessun blocco papers", "papers/**/*.eml" not in t2f)
    controlla("default: nessuna negazione logs", "!logs/" not in t2f)
    controlla("default: il kref entra comunque", NEG_KREF in t2f)
    controlla("default: cambia solo la coda",
              t2f[:len(IGNORE_FINTO.rstrip("\n"))] == IGNORE_FINTO.rstrip("\n"))
    controlla("default: idempotente", nuovo_gitignore(n2f) is None)

    # reversibilita': dentro -> fuori riporta il file com'era, kref a parte
    controlla("reversibile: da dentro a fuori", nuovo_gitignore(n2) == n2f)
    controlla("reversibile: da fuori a dentro",
              nuovo_gitignore(n2f, "dentro", "dentro") == n2)
    controlla("reversibile: una sola sezione per volta",
              b"papers/**/*.eml" in nuovo_gitignore(n2f, "dentro", "fuori")
              and b"!logs/" not in nuovo_gitignore(n2f, "dentro", "fuori"))
    rifiuta("politica sconosciuta rifiutata",
            lambda: nuovo_gitignore(b2, "forse", "fuori"))

    # --- pipeline --------------------------------------------------------- #
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / ".gitattributes").write_bytes(b)
        (base / ".gitignore").write_bytes(b2)

        class A:
            radice = str(base)
            logs_dir = "logs"
            papers = "dentro"
            logs = "dentro"

        controlla("dryrun: esce 0", cmd_dryrun(A()) == 0)
        controlla("dryrun: non scrive", (base / ".gitattributes").read_bytes() == b)
        controlla("dryrun: nessun backup", not (base / "logs").exists())
        controlla("apply: esce 0", cmd_apply(A()) == 0)
        controlla("apply: attributes scritto",
                  (base / ".gitattributes").read_bytes() == n)
        controlla("apply: ignore scritto", (base / ".gitignore").read_bytes() == n2)
        bak = sorted((base / "logs").glob("*.bak_*"))
        controlla("apply: due backup in logs/", len(bak) == 2)
        controlla("apply: backup fedele",
                  any(x.read_bytes() == b for x in bak))
        rifiuta("apply due volte: rifiutato", lambda: cmd_apply(A()))

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / ".gitattributes").write_bytes(b)

        class B:
            radice = str(base)
            logs_dir = "logs"
            papers = "dentro"
            logs = "dentro"

        rifiuta("apply: .gitignore assente", lambda: cmd_apply(B()))
        controlla("apply: nessuna scrittura parziale",
                  (base / ".gitattributes").read_bytes() == b
                  and not (base / "logs").exists())

    print("selftest: %d/%d" % (ok, ok + ko))
    return 0 if ko == 0 else 1


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("comando", choices=["selftest", "dryrun", "apply", "controlla"])
    ap.add_argument("--radice", default=".")
    ap.add_argument("--logs-dir", dest="logs_dir", default="logs")
    ap.add_argument("--papers", choices=["dentro", "fuori"], default="fuori",
                    help="papers/ dentro o fuori dal versionamento (default: fuori)")
    ap.add_argument("--logs", choices=["dentro", "fuori"], default="fuori",
                    help="i tre registri citati di logs/ dentro o fuori (default: fuori)")
    args = ap.parse_args(argv)
    fn = {"selftest": cmd_selftest, "dryrun": cmd_dryrun,
          "apply": cmd_apply, "controlla": cmd_controlla}[args.comando]
    try:
        return fn(args)
    except Rifiuto as e:
        print("RIFIUTO: %s" % e)
        print("Nessun file e' stato scritto.")
        return 2


if __name__ == "__main__":
    sys.exit(main())

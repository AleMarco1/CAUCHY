#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_censimento_verdetti.py  --  voce 6.9, censimento dei verdetti emessi negli script.

CHE COSA FA
    Cerca il vocabolario dei verdetti in ogni .py di una cartella e classifica OGNI SITO
    per il suo ruolo sintattico, letto dall'AST e non dal nome del file:

        commento      il termine sta in un commento '#'
        docstring     docstring di modulo, classe o funzione
        regex         letterale passato a re.compile (lo strumento che cerca, non il verdetto)
        emissione     letterale dentro una chiamata di stampa o di log
        confronto     letterale dentro un confronto o una chiamata di controllo (selftest, cancelli)
        dato          letterale dentro un dizionario, una lista o json.dumps (payload di record)
        altro         letterale che non cade in nessuna delle precedenti
        non_attribuito  occorrenza fuori da ogni token di stringa o commento (nome di variabile)

    Per i siti di classe 'emissione' estrae, quando esiste, la CONDIZIONE che sceglie fra i due
    esiti e le SOGLIE numeriche che vi compaiono.

CHE COSA NON FA
    Non decide se un sito sia una predizione dichiarata con soglia o l'etichetta di un cancello.
    Quella lettura richiede la pre-registrazione e il ledger, e resta umana. Lo strumento produce
    la popolazione, non il verdetto sul verdetto.

VOCABOLARI
    base    smentit|confermat|falsificat        (riproduce il Select-String del 13 set)
    esteso  aggiunge  ritirat|verdetto|regge|superato|fallito|PASS|FAIL
    Il vocabolario usato e' scritto nell'intestazione dell'inventario. Nessun default implicito.

NOTA SULLE MAIUSCOLE
    Select-String di PowerShell e' case-insensitive per default. Qui la ricerca e' case-insensitive
    e la cosa e' dichiarata, non ereditata.

COMANDI
    inventario   scansiona e scrive il JSONL
    mostra       stampa i siti di un file dall'inventario
    riassunto    tabella per file dall'inventario
    selftest     controlli, attraversando la riga di comando

ESEMPI
    python src\\paper2_censimento_verdetti.py inventario --src src --out logs\\verdetti.jsonl --attesi-file 76 --attese-righe 324
    python src\\paper2_censimento_verdetti.py riassunto --inventario logs\\verdetti.jsonl
    python src\\paper2_censimento_verdetti.py mostra --inventario logs\\verdetti.jsonl --file paper2_gate53.py
    python src\\paper2_censimento_verdetti.py selftest
"""

import argparse
import ast
import hashlib
import io
import json
import os
import re
import sys
import tokenize
from datetime import datetime, timezone

REV = "paper2_censimento_verdetti rev.3"

# pattern + se le maiuscole contano. 'esteso' e 'cancelli' sono nati dalla passata del
# 13 set, in cui 'PASS|FAIL' senza confini di parola pescava 'pass', 'passa', 'bypass':
# 1570 occorrenze non attribuite su 4013. I confini e il rispetto delle maiuscole
# servono proprio a questo, e sono dichiarati, non impliciti.
VOCABOLARI = {
    "base":     (r"smentit|confermat|falsificat", True),
    "esteso":   (r"smentit|confermat|falsificat|ritirat|regge|tiene", True),
    "cancelli": (r"SUPERATO|FALLITO|\bPASS\b|\bFAIL\b|CANCELLO|cancello|verdetto", False),
}

CLASSI = ["commento", "docstring", "regex", "emissione", "ritorno", "confronto",
          "assegnazione", "dato", "altro", "non_attribuito"]

# chiamate considerate di stampa o di log
NOMI_EMISSIONE = {"print", "write", "info", "warning", "warn", "error", "debug", "critical",
                  "log", "echo", "stampa"}
# chiamate considerate di controllo (selftest, cancelli)
NOMI_CONTROLLO = {"check", "chk", "ok", "assert_", "verifica", "dentro", "expect",
                  "assertEqual", "assertTrue", "assertIn"}


# --------------------------------------------------------------------------------------
# utilita'


def _versione_python():
    if sys.version_info < (3, 9):
        raise SystemExit("ERRORE: serve Python 3.9 o superiore (ast.unparse). "
                         "Trovato %d.%d" % sys.version_info[:2])


def _sha256(percorso):
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def _leggi(percorso):
    """Legge un sorgente. Fallisce esplicitamente: nessun fallback silenzioso di codifica."""
    with open(percorso, "rb") as f:
        grezzo = f.read()
    try:
        return grezzo.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError("codifica non utf-8 in %s: %s" % (percorso, e))


def _elenco_py(src, ricorsivo=False):
    """Elenco dei .py. Non ricorsivo per default: replica 'Get-ChildItem src\\*.py'."""
    fuori = []
    if ricorsivo:
        for radice, _dirs, files in os.walk(src):
            for n in sorted(files):
                if n.endswith(".py"):
                    fuori.append(os.path.join(radice, n))
    else:
        for n in sorted(os.listdir(src)):
            p = os.path.join(src, n)
            if n.endswith(".py") and os.path.isfile(p):
                fuori.append(p)
    return sorted(fuori)


# --------------------------------------------------------------------------------------
# analisi di un sorgente


class _TokenFinto(object):
    """Token sintetico che copre un'intera f-string, come la vedeva Python <= 3.11."""

    def __init__(self, start, end):
        self.type = tokenize.STRING
        self.start = start
        self.end = end


def _token_di(testo, monolitico=False):
    """Token STRING e COMMENT con i loro estremi. Se la tokenizzazione fallisce, si dichiara."""
    stringhe, commenti = [], []
    tipi_stringa = {tokenize.STRING}
    for nome in ("FSTRING_MIDDLE",):  # presente da Python 3.12
        if hasattr(tokenize, nome):
            tipi_stringa.add(getattr(tokenize, nome))
    inizio_f = getattr(tokenize, "FSTRING_START", None)
    fine_f = getattr(tokenize, "FSTRING_END", None)
    apertura, profondita = None, 0
    try:
        for tok in tokenize.generate_tokens(io.StringIO(testo).readline):
            if monolitico and inizio_f is not None:
                # Su 3.12+ si fondono i token di una f-string in uno solo, per riprodurre
                # il regime <= 3.11 e verificare che la classe non cambi con l'interprete.
                if tok.type == inizio_f:
                    profondita += 1
                    if profondita == 1:
                        apertura = tok.start
                    continue
                if tok.type == fine_f:
                    profondita -= 1
                    if profondita == 0:
                        stringhe.append(_TokenFinto(apertura, tok.end))
                        apertura = None
                    continue
                if profondita > 0:
                    continue
            if tok.type in tipi_stringa:
                stringhe.append(tok)
            elif tok.type == tokenize.COMMENT:
                commenti.append(tok)
    except (tokenize.TokenError, IndentationError, SyntaxError) as e:
        raise ValueError("tokenizzazione fallita: %s" % e)
    return stringhe, commenti


def _mappa_genitori(albero):
    genitori = {}
    for nodo in ast.walk(albero):
        for figlio in ast.iter_child_nodes(nodo):
            genitori[figlio] = nodo
    return genitori


def _posizioni_docstring(albero):
    """Nodi Constant che sono docstring di modulo, classe o funzione."""
    fuori = []
    for nodo in ast.walk(albero):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            corpo = getattr(nodo, "body", None)
            if corpo and isinstance(corpo[0], ast.Expr) and \
                    isinstance(corpo[0].value, ast.Constant) and \
                    isinstance(corpo[0].value.value, str):
                fuori.append(corpo[0].value)
    return fuori


def _nome_chiamata(nodo_call):
    f = nodo_call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _e_re_compile(nodo_call):
    f = nodo_call.func
    return isinstance(f, ast.Attribute) and f.attr == "compile" and \
        isinstance(f.value, ast.Name) and f.value.id == "re"


def _contiene(nodo, riga, col):
    """Il nodo copre la posizione (riga, col)?"""
    l0 = getattr(nodo, "lineno", None)
    l1 = getattr(nodo, "end_lineno", None)
    if l0 is None or l1 is None:
        return False
    c0 = getattr(nodo, "col_offset", 0)
    c1 = getattr(nodo, "end_col_offset", 0)
    if riga < l0 or riga > l1:
        return False
    if riga == l0 and col < c0:
        return False
    if riga == l1 and col > c1:
        return False
    return True


def _area(nodo):
    return (getattr(nodo, "end_lineno", 0) - getattr(nodo, "lineno", 0),
            getattr(nodo, "end_col_offset", 0) - getattr(nodo, "col_offset", 0))


def _nodo_piu_stretto(albero, riga, col):
    migliore, migliore_area = None, None
    for nodo in ast.walk(albero):
        if not _contiene(nodo, riga, col):
            continue
        a = _area(nodo)
        if migliore is None or a < migliore_area:
            migliore, migliore_area = nodo, a
    return migliore


def _sorgente(nodo):
    try:
        return ast.unparse(nodo)
    except Exception:
        return None


def _soglie(nodo):
    fuori = []
    for n in ast.walk(nodo):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and \
                not isinstance(n.value, bool):
            fuori.append(n.value)
    return fuori


def _stringhe_in(nodo):
    """Tutti i letterali di stringa nel sottoalbero di un nodo."""
    fuori = []
    for n in ast.walk(nodo):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            fuori.append(n.value)
    return fuori


def _ifexp_del_termine(radice, termine):
    """IfExp nel sottoalbero di 'radice' che porta 'termine' in uno dei due rami.

    Serve al regime <= 3.11, dove un'intera f-string e' UN token: il nodo piu' stretto
    e' il JoinedStr e l'IfExp non sta fra i suoi antenati ma fra i suoi discendenti.
    Senza questa ricerca la condizione veniva presa dall'if che racchiude la stampa —
    plausibile e sbagliata.
    """
    t = termine.lower()
    trovati = []
    for n in ast.walk(radice):
        if not isinstance(n, ast.IfExp):
            continue
        in_vero = any(t in x.lower() for x in _stringhe_in(n.body))
        in_falso = any(t in x.lower() for x in _stringhe_in(n.orelse))
        if in_vero or in_falso:
            ramo = "vero" if (in_vero and not in_falso) else \
                   ("falso" if (in_falso and not in_vero) else None)
            trovati.append((n, ramo))
    return trovati


def _classifica(albero, genitori, docstring_pos, riga, col, termine=""):
    """Ruolo del sito, salendo dai genitori del nodo piu' stretto che lo copre."""
    nodo = _nodo_piu_stretto(albero, riga, col)
    if nodo is None:
        return "altro", {}

    # docstring: il letterale stesso e' in posizione di docstring
    corrente = nodo
    catena = []
    while corrente is not None:
        catena.append(corrente)
        corrente = genitori.get(corrente)

    for c in docstring_pos:
        if _contiene(c, riga, col):
            return "docstring", {}

    # Si scorre dall'interno verso l'esterno. I contenitori (tuple, dizionari, liste) NON
    # fermano la ricerca: un letterale dentro print("..." % (...)) sta in una tuple ma e'
    # un'emissione. Contano solo chiamate e confronti; i contenitori sono il ripiego.
    for n in catena:
        if isinstance(n, ast.Call):
            if _e_re_compile(n):
                return "regex", {}
            nome = _nome_chiamata(n)
            if nome in NOMI_CONTROLLO:
                return "confronto", {}
            if nome in NOMI_EMISSIONE:
                return "emissione", _condizione(catena, termine)
            if nome == "dumps":
                return "dato", {}
        if isinstance(n, ast.Compare):
            return "confronto", {}
        if isinstance(n, ast.Dict):
            return "dato", {}
        if isinstance(n, ast.Return):
            return "ritorno", _condizione(catena, termine)
    for n in catena:
        if isinstance(n, (ast.Dict, ast.List, ast.Set, ast.Tuple)):
            return "dato", {}
    for n in catena:
        if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            return "assegnazione", {}
    return "altro", {}


def _condizione(catena, termine=""):
    """Condizione che sceglie l'esito, e soglie numeriche.

    Ordine, dal piu' vicino al verdetto al piu' lontano:
      1. IfExp fra gli ANTENATI            -> il ramo e' quello che contiene il letterale
      2. IfExp nel JoinedStr che racchiude -> regime <= 3.11, dove la f-string e' un token
      3. l'if che RACCHIUDE la stampa      -> dichiarato come tale, mai spacciato per ramo
    'fonte' dice sempre da dove viene, cosi' chi legge non deve indovinarlo.
    """
    figlio_prec = None
    for n in catena:
        if isinstance(n, ast.IfExp):
            ramo = None
            if figlio_prec is not None:
                if figlio_prec is n.body:
                    ramo = "vero"
                elif figlio_prec is n.orelse:
                    ramo = "falso"
            return {"condizione": _sorgente(n.test), "soglie": _soglie(n.test),
                    "ramo": ramo, "forma": "ifexp", "fonte": "ramo"}
        figlio_prec = n

    for n in catena:
        if isinstance(n, ast.JoinedStr):
            trovati = _ifexp_del_termine(n, termine)
            if len(trovati) == 1:
                nodo, ramo = trovati[0]
                return {"condizione": _sorgente(nodo.test), "soglie": _soglie(nodo.test),
                        "ramo": ramo, "forma": "ifexp", "fonte": "ramo"}
            if len(trovati) > 1:
                # Due rami nella stessa f-string portano lo stesso termine: quale dei due
                # sia non si deduce. Si dichiara ambiguo invece di scegliere.
                return {"condizione": None, "soglie": [], "ramo": None, "forma": "ifexp",
                        "fonte": "ambigua",
                        "candidate": [_sorgente(x.test) for x, _r in trovati]}
            break

    for n in catena:
        if isinstance(n, ast.If):
            return {"condizione": _sorgente(n.test), "soglie": _soglie(n.test),
                    "ramo": None, "forma": "if", "fonte": "if_racchiudente"}
    return {"condizione": None, "soglie": [], "ramo": None, "forma": None, "fonte": "nessuna"}


def analizza(percorso, rx, monolitico=False):
    """Siti di un singolo file. Restituisce (siti, statistiche)."""
    testo = _leggi(percorso)
    righe = testo.splitlines()
    stringhe, commenti = _token_di(testo, monolitico=monolitico)

    try:
        albero = ast.parse(testo, filename=percorso)
    except SyntaxError as e:
        raise ValueError("parsing fallito: %s" % e)
    genitori = _mappa_genitori(albero)
    docpos = _posizioni_docstring(albero)

    def dentro_token(tok, riga, col):
        (r0, c0), (r1, c1) = tok.start, tok.end
        if riga < r0 or riga > r1:
            return False
        if riga == r0 and col < c0:
            return False
        if riga == r1 and col > c1:
            return False
        return True

    siti = []
    righe_con_match = set()
    for i, testo_riga in enumerate(righe, start=1):
        for m in rx.finditer(testo_riga):
            col = m.start()
            righe_con_match.add(i)
            classe, dettagli = None, {}
            for tok in commenti:
                if dentro_token(tok, i, col):
                    classe = "commento"
                    break
            if classe is None:
                for tok in stringhe:
                    if dentro_token(tok, i, col):
                        classe, dettagli = _classifica(albero, genitori, docpos,
                                                       tok.start[0], tok.start[1],
                                                       m.group(0))
                        break
            if classe is None:
                classe = "non_attribuito"
            sito = {
                "file": os.path.basename(percorso),
                "riga": i,
                "colonna": col,
                "termine": m.group(0),
                "classe": classe,
                "testo": testo_riga.strip()[:240],
            }
            sito.update(dettagli)
            siti.append(sito)

    stat = {
        "file": os.path.basename(percorso),
        "percorso": percorso.replace("\\", "/"),
        "sha256": _sha256(percorso),
        "byte": os.path.getsize(percorso),
        "righe_con_match": len(righe_con_match),
        "occorrenze": len(siti),
    }
    for c in CLASSI:
        stat[c] = sum(1 for s in siti if s["classe"] == c)
    return siti, stat


# --------------------------------------------------------------------------------------
# comandi


def cmd_inventario(a):
    _versione_python()
    if a.vocabolario not in VOCABOLARI:
        raise SystemExit("ERRORE: vocabolario sconosciuto: %s" % a.vocabolario)
    pattern, ignora_maiuscole = VOCABOLARI[a.vocabolario]
    rx = re.compile(pattern, re.IGNORECASE if ignora_maiuscole else 0)

    files = _elenco_py(a.src, ricorsivo=a.ricorsivo)
    if not files:
        raise SystemExit("ERRORE: nessun .py in %s" % a.src)

    # Lo strumento contiene il vocabolario che cerca: se sta in src\ trova se stesso e
    # sposta i conteggi. L'esclusione e' DICHIARATA nell'intestazione e stampata, mai implicita.
    esclusi = list(a.escludi) if a.escludi else [os.path.basename(__file__)]
    prima = len(files)
    files = [f for f in files if os.path.basename(f) not in esclusi]
    esclusi_davvero = prima - len(files)

    tutti_siti, tutte_stat, illeggibili = [], [], []
    for p in files:
        try:
            siti, stat = analizza(p, rx, monolitico=a.fstring_monolitico)
        except ValueError as e:
            illeggibili.append({"file": os.path.basename(p), "errore": str(e)})
            continue
        if siti:
            tutti_siti.extend(siti)
            tutte_stat.append(stat)

    intestazione = {
        "tipo": "intestazione",
        "rev": REV,
        "quando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "src": os.path.abspath(a.src).replace("\\", "/"),
        "ricorsivo": bool(a.ricorsivo),
        "vocabolario": a.vocabolario,
        "pattern": pattern,
        "maiuscole": "ignorate (come Select-String)" if ignora_maiuscole else "rispettate",
        "fstring_monolitico": bool(a.fstring_monolitico),
        "esclusi_dichiarati": esclusi,
        "esclusi_trovati": esclusi_davvero,
        "file_scansionati": len(files),
        "file_con_match": len(tutte_stat),
        "righe_con_match": sum(s["righe_con_match"] for s in tutte_stat),
        "occorrenze": len(tutti_siti),
        "illeggibili": illeggibili,
    }
    for c in CLASSI:
        intestazione[c] = sum(1 for s in tutti_siti if s["classe"] == c)

    cartella = os.path.dirname(os.path.abspath(a.out))
    if cartella and not os.path.isdir(cartella):
        os.makedirs(cartella, exist_ok=True)
    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(intestazione, ensure_ascii=False) + "\n")
        for s in tutte_stat:
            s2 = dict(s)
            s2["tipo"] = "file"
            f.write(json.dumps(s2, ensure_ascii=False) + "\n")
        for s in tutti_siti:
            s2 = dict(s)
            s2["tipo"] = "sito"
            f.write(json.dumps(s2, ensure_ascii=False) + "\n")
    os.replace(tmp, a.out)

    print("=== %s ===" % REV)
    print("  src                : %s%s" % (a.src, "  (ricorsivo)" if a.ricorsivo else ""))
    print("  vocabolario        : %s   ->  %s" % (a.vocabolario, pattern))
    print("  maiuscole          : %s" % intestazione["maiuscole"])
    print("  esclusi (dichiarati): %s  -> %d trovati ed esclusi"
          % (", ".join(esclusi) if esclusi else "nessuno", esclusi_davvero))
    print("  file scansionati   : %d" % intestazione["file_scansionati"])
    print("  file con match     : %d" % intestazione["file_con_match"])
    print("  righe con match    : %d" % intestazione["righe_con_match"])
    print("  occorrenze         : %d" % intestazione["occorrenze"])
    print("")
    print("  per classe:")
    for c in CLASSI:
        print("    %-16s %5d" % (c, intestazione[c]))
    if illeggibili:
        print("")
        print("  ILLEGGIBILI (dichiarati, non ignorati):")
        for i in illeggibili:
            print("    %-40s %s" % (i["file"], i["errore"]))
    print("")
    print("  inventario -> %s" % a.out)

    esito = 0
    if a.attesi_file is not None:
        ok = intestazione["file_con_match"] == a.attesi_file
        print("  [%s] cancello file con match: trovati=%d attesi=%d"
              % ("ok" if ok else "FALLITO", intestazione["file_con_match"], a.attesi_file))
        esito |= 0 if ok else 1
    if a.attese_righe is not None:
        ok = intestazione["righe_con_match"] == a.attese_righe
        print("  [%s] cancello righe con match: trovate=%d attese=%d"
              % ("ok" if ok else "FALLITO", intestazione["righe_con_match"], a.attese_righe))
        esito |= 0 if ok else 1
    if intestazione["non_attribuito"]:
        print("  [nota] %d occorrenze non attribuite a un token: usare 'mostra --classe "
              "non_attribuito'" % intestazione["non_attribuito"])
    print("")
    print("ESITO: %s" % ("CLEAN" if esito == 0 else "CANCELLO FALLITO"))
    return esito


def _carica(percorso):
    intest, files, siti = None, [], []
    with open(percorso, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            r = json.loads(linea)
            if r.get("tipo") == "intestazione":
                intest = r
            elif r.get("tipo") == "file":
                files.append(r)
            elif r.get("tipo") == "sito":
                siti.append(r)
    if intest is None:
        raise SystemExit("ERRORE: inventario senza intestazione: %s" % percorso)
    return intest, files, siti


def cmd_riassunto(a):
    intest, files, siti = _carica(a.inventario)
    colonne = [c for c in CLASSI]
    print("=== riassunto — vocabolario '%s', %d file con match ==="
          % (intest["vocabolario"], intest["file_con_match"]))
    print("")
    testata = "  %-36s %4s" % ("file", "tot")
    for c in colonne:
        testata += " %5s" % c[:5]
    print(testata)
    print("  " + "-" * (len(testata) - 2))
    ordinati = sorted(files, key=lambda r: (-r.get("emissione", 0), r["file"]))
    for r in ordinati:
        if a.solo_emissione and not r.get("emissione", 0):
            continue
        linea = "  %-36s %4d" % (r["file"][:36], r["occorrenze"])
        for c in colonne:
            linea += " %5d" % r.get(c, 0)
        print(linea)
    print("")
    print("  file con almeno un'emissione: %d"
          % sum(1 for r in files if r.get("emissione", 0)))
    return 0


def cmd_mostra(a):
    intest, files, siti = _carica(a.inventario)
    sel = siti
    if a.file:
        sel = [s for s in sel if s["file"] == a.file]
    if a.classe:
        sel = [s for s in sel if s["classe"] == a.classe]
    if not sel:
        print("nessun sito con questi filtri.")
        return 0
    corrente = None
    for s in sorted(sel, key=lambda r: (r["file"], r["riga"], r["colonna"])):
        if s["file"] != corrente:
            corrente = s["file"]
            print("")
            print("=== %s ===" % corrente)
        print("  riga %-5d %-14s %s" % (s["riga"], s["classe"], s["testo"]))
        if s.get("condizione"):
            print("      condizione : %s   [%s]" % (s["condizione"], s.get("fonte", "?")))
            if s.get("soglie"):
                print("      soglie     : %s" % ", ".join(repr(x) for x in s["soglie"]))
            if s.get("ramo"):
                print("      ramo       : %s" % s["ramo"])
        elif s.get("fonte") == "ambigua":
            print("      condizione : AMBIGUA fra %s" % " | ".join(s.get("candidate") or []))
    print("")
    print("  %d siti." % len(sel))
    return 0


# --------------------------------------------------------------------------------------
# selftest


ESEMPI = {
    "e_commento.py": (
        "x = 1\n"
        "# PREDIZIONE SMENTITA, registrata e non riparata.\n"
    ),
    "e_docstring.py": (
        '"""Modulo.\n'
        "\n"
        "Se una qualunque e' smentita, va registrata come smentita.\n"
        '"""\n'
        "y = 2\n"
        "def f():\n"
        '    """La predizione e\' confermata dal run."""\n'
        "    return 1\n"
    ),
    "e_regex.py": (
        "import re\n"
        'PRED = re.compile(r"smentit[ao]|confermat[ao]")\n'
    ),
    "e_emissione_ifexp.py": (
        "gain_quad = 0.01\n"
        'print("    Q1 %s (%.4f)" % ("confermata" if gain_quad < 0.05 else "SMENTITA", gain_quad))\n'
    ),
    "e_emissione_if.py": (
        "tutti = False\n"
        "if not tutti:\n"
        '    print("La predizione dichiarata nell\'item 3.2d e\' SMENTITA.")\n'
    ),
    "e_dato.py": (
        "import json\n"
        'rec = {"esito": "falsificata", "n": 1}\n'
        "print(json.dumps(rec))\n"
    ),
    "e_dato_ritornato.py": (
        "def record():\n"
        '    return {"decision": "withdrawn as a falsification", "n": 1}\n'
    ),
    "e_confronto.py": (
        "def check(c, m):\n"
        "    return c\n"
        'm = {"esito": "SMENTITA"}\n'
        'check(m["esito"] == "SMENTITA", "verso letto correttamente")\n'
    ),
    "e_fstring.py": (
        "in_r = True\n"
        "print(f\"    frazione: {'CONFERMATA' if in_r else 'SMENTITA'}\")\n"
    ),
    "e_ritorno.py": (
        "def verdetto(n, tot):\n"
        '    return "falsificata" if n >= 0.5 * tot else "sostenuta"\n'
    ),
    "e_assegnazione.py": (
        'NUOVO = """La voce 5.5 passa a dodici smentite."""\n'
        "print(NUOVO)\n"
    ),
    "e_fstring_ambigua.py": (
        "a = True\n"
        "b = False\n"
        "print(f\"{'CONFERMATA' if a else 'x'} / {'CONFERMATA' if b else 'y'}\")\n"
    ),
    "e_nessuno.py": (
        "z = 3\n"
        "print('niente di pertinente')\n"
    ),
    "e_non_attribuito.py": (
        "lattice_verdetto_confermato = 1\n"
        "print(lattice_verdetto_confermato)\n"
    ),
}


def cmd_selftest(a):
    import subprocess
    import tempfile
    import shutil

    _versione_python()
    esiti = []

    def check(cond, testo):
        esiti.append((bool(cond), testo))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", testo))

    base = tempfile.mkdtemp(prefix="censimento_")
    try:
        src = os.path.join(base, "src")
        logs = os.path.join(base, "logs")
        os.makedirs(src)
        for nome, testo in ESEMPI.items():
            with open(os.path.join(src, nome), "w", encoding="utf-8", newline="\n") as f:
                f.write(testo)

        out = os.path.join(logs, "inv.jsonl")
        # il selftest attraversa la riga di comando, non la sola libreria
        cmd = [sys.executable, os.path.abspath(__file__), "inventario",
               "--src", src, "--out", out, "--vocabolario", "base"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        check(p.returncode == 0, "01 la CLI 'inventario' esce con 0")
        check("ESITO: CLEAN" in p.stdout, "02 la CLI stampa l'esito")
        check(os.path.isfile(out), "03 l'inventario e' stato scritto")
        check(not os.path.exists(out + ".tmp"), "04 nessun file temporaneo lasciato indietro")

        intest, files, siti = _carica(out)
        check(intest["vocabolario"] == "base", "05 il vocabolario e' dichiarato nell'intestazione")
        check(intest["pattern"] == VOCABOLARI["base"][0],
              "06 il pattern e' dichiarato per esteso")
        check(intest["file_scansionati"] == len(ESEMPI),
              "07 scansionati tutti i file (%d)" % len(ESEMPI))
        check(intest["file_con_match"] == len(ESEMPI) - 1,
              "08 il file senza match non entra nell'inventario")
        check(intest["altro"] == 0,
              "08b nessun esempio finisce nel secco 'altro'")

        per_file = {r["file"]: r for r in files}

        check(per_file["e_commento.py"]["commento"] == 1, "09 commento riconosciuto")
        check(per_file["e_commento.py"]["emissione"] == 0, "10 il commento non e' un'emissione")

        check(per_file["e_docstring.py"]["docstring"] == 3,
              "11 docstring di modulo e di funzione riconosciuti (3 occorrenze)")
        check(per_file["e_docstring.py"]["emissione"] == 0, "12 il docstring non e' un'emissione")

        check(per_file["e_regex.py"]["regex"] == 2,
              "13 re.compile riconosciuto (due termini nel pattern, due siti)")

        check(per_file["e_emissione_ifexp.py"]["emissione"] == 2,
              "14 i due rami dell'IfExp sono due emissioni")
        s = [x for x in siti if x["file"] == "e_emissione_ifexp.py"]
        check(all(x.get("condizione") == "gain_quad < 0.05" for x in s),
              "15 la condizione dell'IfExp e' estratta")
        check(all(x.get("soglie") == [0.05] for x in s), "16 la soglia numerica e' estratta")
        check(sorted(str(x.get("ramo")) for x in s) == ["falso", "vero"],
              "17 i due rami sono distinti")

        check(per_file["e_emissione_if.py"]["emissione"] == 1,
              "18 emissione dentro un if riconosciuta")
        s = [x for x in siti if x["file"] == "e_emissione_if.py"][0]
        check(s.get("condizione") == "not tutti", "19 la condizione dell'if e' estratta")
        check(s.get("forma") == "if", "20 la forma della condizione e' dichiarata")

        check(per_file["e_dato.py"]["dato"] == 1, "21 letterale di payload riconosciuto")
        check(per_file["e_dato_ritornato.py"]["dato"] == 1,
              "21b un payload dentro 'return {...}' resta 'dato', non 'ritorno': "
              "i costruttori di record del ledger hanno questa forma")
        check(per_file["e_dato_ritornato.py"]["ritorno"] == 0,
              "21c il Return non scavalca il dizionario")
        check(per_file["e_confronto.py"]["confronto"] >= 1, "22 confronto riconosciuto")
        check(per_file["e_confronto.py"]["emissione"] == 0,
              "23 un controllo di selftest non e' un'emissione")

        check(per_file["e_fstring.py"]["emissione"] == 2, "24 f-string: due emissioni")
        s = [x for x in siti if x["file"] == "e_fstring.py"]
        check(all(x.get("condizione") == "in_r" for x in s),
              "25 f-string: la condizione e' estratta")

        # Il difetto del 13 set: su Python <= 3.11 la f-string e' un token unico, il nodo
        # piu' stretto e' il JoinedStr e la condizione veniva presa dall'if che racchiude
        # la stampa. Qui il regime <= 3.11 si riproduce a comando, su qualunque interprete.
        out_mono = os.path.join(logs, "inv_mono.jsonl")
        pm = subprocess.run(cmd[:-2] + ["--vocabolario", "base", "--out", out_mono,
                                        "--fstring-monolitico"],
                            capture_output=True, text=True)
        check(pm.returncode == 0, "25a la CLI accetta --fstring-monolitico")
        im, fm, sm = _carica(out_mono)
        check(im["fstring_monolitico"] is True,
              "25b il regime della f-string e' dichiarato nell'intestazione")
        sf_mono = [x for x in sm if x["file"] == "e_fstring.py"]
        check(len(sf_mono) == 2 and all(x["classe"] == "emissione" for x in sf_mono),
              "25c regime <= 3.11: le due emissioni restano emissioni")
        check(all(x.get("condizione") == "in_r" for x in sf_mono),
              "25d regime <= 3.11: la condizione e' 'in_r', letta dal ramo")
        check(all(x.get("fonte") == "ramo" for x in sf_mono),
              "25e regime <= 3.11: la fonte della condizione e' dichiarata 'ramo'")
        sf_312 = [x for x in siti if x["file"] == "e_fstring.py"]
        check([x.get("condizione") for x in sf_312] == [x.get("condizione") for x in sf_mono],
              "25f i due regimi danno la STESSA condizione: non dipende dall'interprete")

        amb = [x for x in siti if x["file"] == "e_fstring_ambigua.py"]
        amb_m = [x for x in sm if x["file"] == "e_fstring_ambigua.py"]
        check(len(amb) == 2, "25g due termini nella f-string ambigua")
        ammesse = {"ramo", "ambigua"}
        check(all(x.get("fonte") in ammesse for x in amb),
              "25h la f-string ambigua da' 'ramo' (3.12+) o 'ambigua' (<= 3.11), "
              "mai altro: il controllo non impone l'interprete di chi l'ha scritto")
        check(all(x.get("condizione") in (None, "a", "b") for x in amb),
              "25h-bis se una condizione c'e', e' una delle due vere, mai l'if che "
              "racchiude la stampa")
        check(all(x.get("fonte") == "ambigua" and not x.get("condizione") for x in amb_m),
              "25i su <= 3.11 l'ambiguita' e' dichiarata, non risolta a indovinare")
        check(all(x.get("candidate") for x in amb_m),
              "25j l'ambiguita' elenca le condizioni candidate")

        check(per_file["e_non_attribuito.py"]["non_attribuito"] == 2,
              "26 le occorrenze fuori dai token sono dichiarate, non perse")

        check(per_file["e_ritorno.py"]["ritorno"] == 1,
              "26b un verdetto restituito da una funzione e' classificato 'ritorno'")
        s = [x for x in siti if x["file"] == "e_ritorno.py"][0]
        check(s.get("condizione") == "n >= 0.5 * tot",
              "26c la condizione del ritorno e' estratta")
        check(s.get("soglie") == [0.5], "26d la soglia del ritorno e' estratta")
        check(per_file["e_assegnazione.py"]["assegnazione"] == 1,
              "26e il testo assegnato a una costante e' 'assegnazione', non 'emissione'")

        # lo strumento non deve censire se stesso
        import shutil as _sh
        _sh.copy(os.path.abspath(__file__),
                 os.path.join(src, os.path.basename(__file__)))
        out_self = os.path.join(logs, "inv_self.jsonl")
        pp = subprocess.run([sys.executable, os.path.abspath(__file__), "inventario",
                             "--src", src, "--out", out_self], capture_output=True, text=True)
        i_self, f_self, _ = _carica(out_self)
        check(i_self["esclusi_trovati"] == 1,
              "26f lo strumento si esclude da solo se sta nella cartella scansionata")
        check(all(r["file"] != os.path.basename(__file__) for r in f_self),
              "26g lo strumento non compare nell'inventario")
        check(i_self["esclusi_dichiarati"] == [os.path.basename(__file__)],
              "26h l'esclusione e' dichiarata nell'intestazione, non implicita")
        check("esclusi (dichiarati)" in pp.stdout, "26i l'esclusione e' stampata a terminale")
        out_self2 = os.path.join(logs, "inv_self2.jsonl")
        pp = subprocess.run([sys.executable, os.path.abspath(__file__), "inventario",
                             "--src", src, "--out", out_self2, "--escludi", "e_commento.py"],
                            capture_output=True, text=True)
        i_self2, f_self2, _ = _carica(out_self2)
        check(any(r["file"] == os.path.basename(__file__) for r in f_self2),
              "26j --escludi esplicito sostituisce il default, e lo strumento rientra")
        check(all(r["file"] != "e_commento.py" for r in f_self2),
              "26k --escludi esplicito toglie quello che nomina")
        os.remove(os.path.join(src, os.path.basename(__file__)))

        tot_siti = sum(r["occorrenze"] for r in files)
        check(tot_siti == len(siti), "27 le somme per file tornano col numero di siti")
        check(intest["occorrenze"] == len(siti), "28 l'intestazione torna col corpo")
        somma_classi = sum(intest[c] for c in CLASSI)
        check(somma_classi == len(siti), "29 ogni sito ha esattamente una classe")

        # cancello di riproduzione: numeri giusti e numeri sbagliati
        cmd_ok = cmd + ["--attesi-file", str(len(ESEMPI) - 1),
                        "--attese-righe", str(intest["righe_con_match"])]
        p = subprocess.run(cmd_ok, capture_output=True, text=True)
        check(p.returncode == 0 and "ESITO: CLEAN" in p.stdout,
              "30 il cancello passa coi numeri giusti")
        cmd_ko = cmd + ["--attesi-file", "999"]
        p = subprocess.run(cmd_ko, capture_output=True, text=True)
        check(p.returncode != 0 and "CANCELLO FALLITO" in p.stdout,
              "31 il cancello fallisce coi numeri sbagliati, e lo dice")

        # vocabolario esteso: dichiarato, e piu' ampio
        out2 = os.path.join(logs, "inv_esteso.jsonl")
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "inventario",
                            "--src", src, "--out", out2, "--vocabolario", "esteso"],
                           capture_output=True, text=True)
        check(p.returncode == 0, "32 la CLI accetta il vocabolario esteso")
        i2, _f2, s2 = _carica(out2)
        check(i2["vocabolario"] == "esteso", "33 il vocabolario esteso e' dichiarato")
        check(len(s2) >= len(siti), "34 il vocabolario esteso non trova meno del base")

        with open(os.path.join(src, "e_cancello.py"), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write("def g(fails):\n"
                    "    if not fails:\n"
                    "        pass\n"
                    "    bypass = 1\n"
                    "    print('cancello: %s' % ('SUPERATO' if not fails else 'FALLITO'))\n"
                    "    return bypass\n")
        out_c = os.path.join(logs, "inv_canc.jsonl")
        pc = subprocess.run([sys.executable, os.path.abspath(__file__), "inventario",
                             "--src", src, "--out", out_c, "--vocabolario", "cancelli"],
                            capture_output=True, text=True)
        check(pc.returncode == 0, "35a la CLI accetta il vocabolario 'cancelli'")
        ic, fc, sc = _carica(out_c)
        check(ic["maiuscole"] == "rispettate",
              "35b 'cancelli' dichiara di rispettare le maiuscole")
        sel = [x for x in sc if x["file"] == "e_cancello.py"]
        check(sum(1 for x in sel if x["classe"] == "emissione") == 3,
              "35c tre emissioni: SUPERATO, FALLITO e la parola 'cancello' nel testo")
        con_ramo = [x for x in sel if x.get("ramo")]
        check(len(con_ramo) == 2 and all(x["condizione"] == "not fails" for x in con_ramo),
              "35d i due rami del cancello portano la loro condizione")
        check(sum(1 for x in sel if x.get("fonte") == "nessuna") == 1,
              "35d-bis il testo fisso non ha condizione, e lo dichiara")
        check(sum(1 for x in sel if x["termine"].lower() == "pass") == 0,
              "35e ne' 'pass' ne' 'bypass' entrano: i confini di parola e le maiuscole "
              "tengono fuori il rumore")
        os.remove(os.path.join(src, "e_cancello.py"))

        p = subprocess.run([sys.executable, os.path.abspath(__file__), "inventario",
                            "--src", src, "--out", out2, "--vocabolario", "inesistente"],
                           capture_output=True, text=True)
        check(p.returncode != 0, "35 un vocabolario sconosciuto fa fallire, non ripiega")

        # sorgente illeggibile: dichiarato, non ignorato
        with open(os.path.join(src, "e_rotto.py"), "w", encoding="utf-8", newline="\n") as f:
            f.write("def f(:\n    return 'smentita'\n")
        out3 = os.path.join(logs, "inv_rotto.jsonl")
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "inventario",
                            "--src", src, "--out", out3], capture_output=True, text=True)
        i3, _f3, _s3 = _carica(out3)
        check(len(i3["illeggibili"]) == 1 and i3["illeggibili"][0]["file"] == "e_rotto.py",
              "36 un file che non si parsa e' dichiarato illeggibile, non saltato in silenzio")
        check("ILLEGGIBILI" in p.stdout, "37 gli illeggibili compaiono a terminale")
        os.remove(os.path.join(src, "e_rotto.py"))

        # mostra e riassunto attraversano la CLI
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "mostra",
                            "--inventario", out, "--file", "e_emissione_ifexp.py"],
                           capture_output=True, text=True)
        check(p.returncode == 0 and "gain_quad < 0.05" in p.stdout,
              "38 'mostra' stampa la condizione")
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "mostra",
                            "--inventario", out, "--classe", "commento"],
                           capture_output=True, text=True)
        check(p.returncode == 0 and "e_commento.py" in p.stdout,
              "39 'mostra --classe' filtra per classe")
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "riassunto",
                            "--inventario", out], capture_output=True, text=True)
        check(p.returncode == 0 and "e_emissione_ifexp.py" in p.stdout,
              "40 'riassunto' stampa la tabella")
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "riassunto",
                            "--inventario", out, "--solo-emissione"],
                           capture_output=True, text=True)
        check(p.returncode == 0 and "e_commento.py" not in p.stdout,
              "41 'riassunto --solo-emissione' esclude chi non emette")

        # lettura di sola lettura: i sorgenti non vengono toccati
        sha_prima = {n: _sha256(os.path.join(src, n)) for n in ESEMPI}
        subprocess.run(cmd, capture_output=True, text=True)
        sha_dopo = {n: _sha256(os.path.join(src, n)) for n in ESEMPI}
        check(sha_prima == sha_dopo, "42 i sorgenti non sono modificati (sola lettura)")

        # idempotenza
        with open(out, "r", encoding="utf-8") as f:
            a1 = [json.loads(x) for x in f if x.strip()]
        subprocess.run(cmd, capture_output=True, text=True)
        with open(out, "r", encoding="utf-8") as f:
            a2 = [json.loads(x) for x in f if x.strip()]
        for r1, r2 in zip(a1, a2):
            r1.pop("quando", None)
            r2.pop("quando", None)
        check(a1 == a2, "43 due passate danno lo stesso inventario (a meno dell'ora)")

        p = subprocess.run([sys.executable, os.path.abspath(__file__), "inventario",
                            "--src", os.path.join(base, "inesistente"), "--out", out],
                           capture_output=True, text=True)
        check(p.returncode != 0, "44 una cartella inesistente fa fallire")

    finally:
        shutil.rmtree(base, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


# --------------------------------------------------------------------------------------


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="paper2_censimento_verdetti.py",
        description="Censimento dei verdetti emessi negli script (voce 6.9). "
                    "Classifica i siti; non decide predizione contro cancello.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("inventario", help="scansiona i .py e scrive il JSONL")
    q.add_argument("--src", required=True, help="cartella dei sorgenti (es. src)")
    q.add_argument("--out", required=True, help="JSONL di uscita")
    q.add_argument("--vocabolario", default="base", choices=sorted(VOCABOLARI),
                   help="vocabolario dei verdetti (default: base)")
    q.add_argument("--fstring-monolitico", action="store_true",
                   help="tratta ogni f-string come un token unico, cioe' come la vede "
                        "Python <= 3.11 (PEP 701). Serve a verificare che la classificazione "
                        "non dipenda dall'interprete.")
    q.add_argument("--escludi", action="append", default=None, metavar="NOME",
                   help="nome di file da escludere, ripetibile. Se omesso si esclude solo "
                        "questo stesso script (che contiene il vocabolario che cerca). "
                        "L'esclusione e' scritta nell'intestazione dell'inventario.")
    q.add_argument("--ricorsivo", action="store_true",
                   help="scendi nelle sottocartelle (default: no, come Get-ChildItem src\\*.py)")
    q.add_argument("--attesi-file", type=int, default=None,
                   help="cancello: numero atteso di file con match")
    q.add_argument("--attese-righe", type=int, default=None,
                   help="cancello: numero atteso di righe con match")
    q.set_defaults(func=cmd_inventario)

    q = sub.add_parser("riassunto", help="tabella per file")
    q.add_argument("--inventario", required=True)
    q.add_argument("--solo-emissione", action="store_true",
                   help="mostra solo i file con almeno un sito di classe 'emissione'")
    q.set_defaults(func=cmd_riassunto)

    q = sub.add_parser("mostra", help="siti di un file o di una classe")
    q.add_argument("--inventario", required=True)
    q.add_argument("--file", default=None)
    q.add_argument("--classe", default=None, choices=CLASSI)
    q.set_defaults(func=cmd_mostra)

    q = sub.add_parser("selftest", help="controlli, attraversando la riga di comando")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

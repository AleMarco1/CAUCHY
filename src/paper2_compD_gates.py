#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_compD_gates.py — i tre cancelli di tracciabilita' della Componente D.

  D-T1  digest    calcola e riporta lo SHA-256 degli INGRESSI (file dei
                  parametri, registri per_mock). Sola lettura.
  D-T3  patch     installa in paper2_compD_partialcorr.py i due cancelli che
                  mancano sulle ETICHETTE: l'intestazione del file come terza
                  fonte, e una soglia ASSOLUTA sul punteggio di infer_names,
                  con arresto invece di avviso. Scrive solo con --apply.
  D-T2  compare   confronta le correlazioni parziali di due record compD a
                  precisione piena. Sola lettura.

ORDINE OBBLIGATO: D-T3 prima di D-T2. Una riproduzione fatta con la stessa
tabella di etichette hard-coded riprodurrebbe fedelmente anche un'etichetta
sbagliata: non convalida un'assunzione che entrambe le esecuzioni condividono.

LA PATCH NON REIMPLEMENTA NIENTE. Avvolge load_params, non la riscrive: la
logica di etichettatura resta una sola, e i cancelli la verificano dall'esterno.

SOGLIA, dichiarata dal disegno e non dall'output
------------------------------------------------
infer_names assegna i nomi confrontando (min, max) di ogni colonna con gli
intervalli nominali, e il punteggio e' (|lo-a| + |hi-b|) / (b-a). Con 2000
campioni un Latin hypercube lascia ai bordi lacune dell'ordine di 1/2000 dello
span, quindi il punteggio vero sta sotto 1e-2. Sulla suite nwLH il concorrente
piu' vicino e' M_nu contro Omega_m, a (0.10+0.50)/1.00 = 0.60. La soglia 0.10 e'
un ordine di grandezza sopra il primo e sei volte sotto il secondo.

Sottocomandi
------------
  digest    SHA-256 degli ingressi. Non scrive.
  inspect   mostra le quattro ancore e la loro unicita'. Non scrive.
  patch     applica le quattro modifiche. Scrive solo con --apply.
  verify    ricontrolla il file dopo la patch. Non scrive.
  compare   D-T2 fra due registri compD. Non scrive.
  selftest  costruisce un modulo sintetico, lo patcha, e prova che i cancelli
            MORDONO su colonne permutate. Non tocca i file veri.

Uscita ASCII pura: console Windows cp1252 senza UnicodeEncodeError.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys

DEFAULT_TARGET = os.path.join("src", "paper2_compD_partialcorr.py")
DEFAULT_PARAMS = os.path.join("data", "raw", "quijote", "3D_cubes",
                              "latin_hypercube_nwLH", "latin_hypercube_nwLH_params.txt")
DEFAULT_NH1 = {
    "NGC": os.path.join("results", "paper1", "per_mock_NGC_R5.jsonl"),
    "SGC": os.path.join("results", "paper1", "per_mock_SGC_R5.jsonl"),
}
DEFAULT_COMPD = {
    "NGC": os.path.join("results", "paper2", "compD_NGC.jsonl"),
    "SGC": os.path.join("results", "paper2", "compD_SGC.jsonl"),
}

# Digest atteso del file dei parametri, misurato il 5 set 2026.
EXPECTED_PARAMS_SHA = ("bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e")

INFER_SCORE_MAX = 0.10
MARKER = "D-T3"


# ---------------------------------------------------------------------------
# Le quattro modifiche. Ogni `old` deve comparire ESATTAMENTE una volta.
# ---------------------------------------------------------------------------

EDITS = []

EDITS.append((
    "1. costante di soglia",
    '    "w0":      (-1.30, -0.70),\n}\n',
    '    "w0":      (-1.30, -0.70),\n}\n'
    '\n'
    '# D-T3: soglia ASSOLUTA sul punteggio di infer_names, dichiarata dal disegno\n'
    '# e non dall\'output. Con 2000 campioni un Latin hypercube lascia ai bordi\n'
    '# lacune dell\'ordine di 1/2000 dello span, quindi il punteggio vero sta sotto\n'
    '# 1e-2; sulla suite nwLH il concorrente piu\' vicino (M_nu contro Omega_m) sta\n'
    '# a 0.60. La soglia e\' un ordine di grandezza sopra il primo, sei volte sotto\n'
    '# il secondo. Oltre la soglia si ARRESTA: non si avvisa.\n'
    'INFER_SCORE_MAX = %r\n' % INFER_SCORE_MAX,
))

EDITS.append((
    "2. terza fonte e cancelli, avvolgendo load_params",
    "\n\n# --------------------------------------------------------------------------\n"
    "# statistica\n"
    "# --------------------------------------------------------------------------\n",
    '''

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_param_header(path):
    """LA TERZA FONTE: i nomi scritti nel file.

    DEFAULT_NAMES guarda la POSIZIONE, infer_names guarda gli ESTREMI delle
    colonne. L'intestazione non e' ne' l'uno ne' l'altro, ed e' l'unica delle
    tre verificabile da fuori senza fidarsi di PARAM_RANGES. Il file la porta
    ('#Omega_m Omega_b h n_s sigma_8 M_nu w0') e finora non veniva letta:
    np.genfromtxt la scarta come commento.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                toks = s.lstrip("#").split()
                return toks or None
            return None
    return None


def load_params_checked(path, names=None):
    """D-T3. Avvolge load_params e aggiunge i due cancelli che mancavano.

    Che cosa NON aggiunge, e va detto per non rivendicare troppo: infer_names
    difende gia' da una permutazione di colonne, perche' guarda gli ESTREMI e non
    la posizione, e su questa suite gli intervalli sono separabili - Omega_m
    contro M_nu, la coppia piu' vicina, da' 0.60 contro ~0. La difesa c'e'.

    Quello che aggiunge:

    (a) UNA TERZA FONTE INDIPENDENTE DA PARAM_RANGES. Posizione e valori non sono
        indipendenti dalla tabella degli intervalli: se PARAM_RANGES fosse
        sbagliata, l'identificazione dai valori sarebbe sbagliata insieme a lei e
        nessuno se ne accorgerebbe. L'intestazione del file e' l'unica delle tre
        che non dipende da quella tabella. Il risultato citabile della Componente
        D e' un ORDINAMENTO di parametri: uno scambio lascia intatta la
        conclusione negativa su w0 e distrugge quella positiva.

    (b) SOGLIA CON ARRESTO. Il verdetto di infer_names era sempre completo e mai
        gated: ogni colonna riceveva un nome qualunque fosse il punteggio, e
        l'ultima colonna non sceglieva affatto perche' le restava un solo nome.

    (c) L'ESITO NEL RECORD. Quale fonte abbia deciso le etichette finiva a
        terminale; ora e' un campo depositato.

    Non reimplementa l'etichettatura: chiama load_params e la verifica.
    """
    raw, nm = load_params(path, names)
    ncol = raw.shape[1]
    inferred = infer_names(raw)
    scores = [round(float(sc), 12) for _, sc in inferred]
    by_values = [g for g, _ in inferred]
    by_position = list(DEFAULT_NAMES.get(ncol, [])) or None
    header = read_param_header(path)

    print("\\n[D-T3] confronto a tre fonti")
    print("    usate       : %s" % ", ".join(nm))
    print("    posizionali : %s" % (", ".join(by_position) if by_position else "assenti"))
    print("    dai valori  : %s" % ", ".join(by_values))
    print("    intestazione: %s" % (", ".join(header) if header else "assente"))
    print("    punteggi    : %s   (max %.4g, soglia %.4g)"
          % (" ".join("%.3g" % s for s in scores), max(scores), INFER_SCORE_MAX))

    if max(scores) > INFER_SCORE_MAX:
        raise SystemExit(
            "[D-T3] CANCELLO FALLITO: punteggio massimo di infer_names %.4g > soglia %.4g.\\n"
            "    L'identificazione dai valori non e' netta su questo file, quindi la\\n"
            "    difesa contro una permutazione di colonne non regge. Arresto."
            % (max(scores), INFER_SCORE_MAX))

    if header is not None and len(header) == ncol and list(header) != list(nm):
        raise SystemExit(
            "[D-T3] CANCELLO FALLITO: l'intestazione del file dice %s\\n"
            "    ma le etichette in uso sono %s.\\n"
            "    Il risultato della Componente D e' un ordinamento di parametri: una\\n"
            "    permutazione lo distrugge senza toccare la conclusione su w0. Arresto."
            % (", ".join(header), ", ".join(nm)))

    if header is not None and len(header) != ncol:
        raise SystemExit(
            "[D-T3] CANCELLO FALLITO: l'intestazione ha %d nomi e il file %d colonne."
            % (len(header), ncol))

    agree = [s for s, v in (("header", header), ("position", by_position),
                            ("values", by_values)) if v is not None and list(v) == list(nm)]
    source = "+".join(agree) if agree else "explicit"
    print("    -> fonti che concordano con le etichette in uso: %s" % source)

    diag = {
        "names_used": list(nm),
        "names_by_position": by_position,
        "names_by_values": by_values,
        "names_from_header": list(header) if header else None,
        "names_source": source,
        "infer_scores": scores,
        "infer_score_max": max(scores),
        "infer_score_threshold": INFER_SCORE_MAX,
    }
    return raw, nm, diag


# --------------------------------------------------------------------------
# statistica
# --------------------------------------------------------------------------
''',
))

EDITS.append((
    "3. sito di chiamata",
    "    P_all, names = load_params(args.params, args.names)\n",
    "    P_all, names, names_diag = load_params_checked(args.params, args.names)\n",
))

EDITS.append((
    "4. diagnostica e digest degli ingressi nel record",
    '           "rows": rows, "deficit_gen": gap}\n    rec.update(extra)\n',
    '           "rows": rows, "deficit_gen": gap}\n'
    '    # D-T3: quale fonte ha deciso le etichette non e\' piu\' un messaggio a\n'
    '    # terminale. D-T1: config_hash riassume PERCORSI e conteggio, non i byte;\n'
    '    # questi due campi sono i byte, e sono nuovi per non cambiare il\n'
    '    # significato di config_hash ne\' il suo valore sui record depositati.\n'
    '    rec.update(names_diag)\n'
    '    rec["params_sha256"] = sha256_file(args.params)\n'
    '    rec["nh1_sha256"] = sha256_file(nh1_path)\n'
    '    rec.update(extra)\n',
))


# ---------------------------------------------------------------------------
# Utilita'
# ---------------------------------------------------------------------------

def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")


def split_jsonl(raw):
    parts = raw.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    return [p[:-1] if p.endswith(b"\r") else p for p in parts if p.strip()]


def read_compd(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    return [json.loads(l.decode("utf-8")) for l in split_jsonl(raw)]


def resolve_positional(recs):
    """La regola del record 42: superato se una riga SUCCESSIVA lo cita."""
    live = []
    for i, r in enumerate(recs):
        key = (r.get("schema"), r.get("utc"))
        dead = False
        for later in recs[i + 1:]:
            sup = later.get("supersedes")
            if isinstance(sup, dict) and (sup.get("schema"), sup.get("utc")) == key:
                dead = True
                break
        if not dead:
            live.append(i + 1)
    return live


def canonical(recs):
    """L'ultima riga viva, come dichiara il record 42."""
    live = resolve_positional(recs)
    return recs[live[-1] - 1] if live else None


def check_anchors(txt):
    """(nome, n_occorrenze_old, gia_applicata) per ogni modifica."""
    out = []
    for name, old, new in EDITS:
        out.append((name, txt.count(old), txt.count(new) > 0))
    return out


def apply_edits(txt):
    """Applica tutte le modifiche o nessuna. Fallisce se un'ancora non e' unica."""
    bad = []
    for name, old, new in EDITS:
        if txt.count(new):
            bad.append("%s: gia' applicata" % name)
        elif txt.count(old) != 1:
            bad.append("%s: %d occorrenze dell'ancora" % (name, txt.count(old)))
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    for name, old, new in EDITS:
        txt = txt.replace(old, new, 1)
    return txt


# ---------------------------------------------------------------------------
# Sottocomandi
# ---------------------------------------------------------------------------

def cmd_digest(args):
    print("=== D-T1  digest degli ingressi ===")
    ok = True
    p = args.params
    if os.path.isfile(p):
        sha = sha256_file(p)
        size = os.path.getsize(p)
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.readline().rstrip("\n")
            nrows = 1 + sum(1 for _ in fh)
        print("  parametri : %s" % p)
        print("      sha256: %s" % sha)
        print("      atteso: %s   %s"
              % (EXPECTED_PARAMS_SHA, "OK" if sha == EXPECTED_PARAMS_SHA else "DIVERSO"))
        print("      byte  : %d   righe: %d (intestazione inclusa)" % (size, nrows))
        print("      testa : %s" % head)
        ok &= sha == EXPECTED_PARAMS_SHA
    else:
        print("  parametri : ASSENTE  %s" % p)
        ok = False
    for region, path in sorted(DEFAULT_NH1.items()):
        if os.path.isfile(path):
            print("  N_H1 %s  : %s" % (region, sha256_file(path)))
            print("             %s  (%d byte)" % (path, os.path.getsize(path)))
        else:
            print("  N_H1 %s  : ASSENTE  %s" % (region, path))
            ok = False
    print("  esito     : %s" % ("OK" if ok else "INCOMPLETO"))
    return 0 if ok else 3


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt = read_text(args.target)
    print("=== ANCORE in %s ===" % args.target)
    allgood = True
    for name, n_old, done in check_anchors(txt):
        state = "GIA' APPLICATA" if done else ("unica" if n_old == 1
                                               else "%d occorrenze" % n_old)
        print("  [%s] %s" % ("ok" if (done or n_old == 1) else "NO", name))
        print("       %s" % state)
        allgood &= (done or n_old == 1)
    print("  soglia dichiarata: INFER_SCORE_MAX = %r" % INFER_SCORE_MAX)
    return 0 if allgood else 3


DEFAULT_EDIT = (
    "5. default di --params (percorso che non esiste)",
    '"data/raw/quijote/latin_hypercube_nwLH_params.txt"',
    '"data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt"',
)


def cmd_patch_default(args):
    """Il default a riga 484 punta a un percorso che NON ESISTE. Non e' mai stato
    usato - i run sono partiti con --params esplicito, e i quattro record lo
    depositano - ma un default sbagliato e' una trappola che aspetta il primo che
    lo ometta. Modifica separata dalle altre quattro: e' un difetto diverso."""
    name, old, new = DEFAULT_EDIT
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt = read_text(args.target)
    print("=== PATCH DEFAULT %s ===" % args.target)
    print("  %s" % name)
    print("  vecchio: %d occorrenze   nuovo: %d occorrenze"
          % (txt.count(old), txt.count(new)))
    if txt.count(new) and not txt.count(old):
        print("  [OK] gia' corretto, nulla da fare.")
        return 0
    if txt.count(old) != 1:
        fail("l'ancora non e' unica (%d occorrenze): non tocco il file." % txt.count(old))
    new_txt = txt.replace(old, new, 1)
    try:
        ast.parse(new_txt)
    except SyntaxError as exc:
        fail("il risultato non e' Python valido (%s): nulla scritto." % exc)
    target_path = new.strip('"')
    esiste = os.path.isfile(target_path)
    print("  il nuovo default esiste su disco: %s" % esiste)
    if not esiste and not args.force:
        fail("il nuovo default non esiste su disco: non lo installo (--force per forzare).")
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    tmp = args.target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(new_txt.encode("utf-8"))
    os.replace(tmp, args.target)
    print("  [OK] default corretto")
    return 0


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt = read_text(args.target)
    before = sha256_file(args.target)
    new_txt = apply_edits(txt)
    try:
        ast.parse(new_txt)
    except SyntaxError as exc:
        fail("il risultato non e' Python valido (%s): nulla scritto." % exc)
    print("=== PATCH %s ===" % args.target)
    print("  sha256 prima : %s" % before)
    print("  quattro modifiche pronte, AST valido, %d -> %d byte"
          % (len(txt.encode("utf-8")), len(new_txt.encode("utf-8"))))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    if args.backup:
        bak = args.target + ".prepatch"
        if not os.path.exists(bak):
            with open(bak, "wb") as fh:
                fh.write(txt.encode("utf-8"))
            print("  copia    : %s" % bak)
    tmp = args.target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(new_txt.encode("utf-8"))
    os.replace(tmp, args.target)
    print("  sha256 dopo  : %s" % sha256_file(args.target))
    print("  [OK] patch applicata")
    return cmd_verify(args)


def cmd_verify(args):
    txt = read_text(args.target)
    ok = True
    print("")
    print("=== VERIFY ===")
    for name, n_old, done in check_anchors(txt):
        print("  [%s] %s" % ("ok" if done else "NO", name))
        ok &= done
    try:
        ast.parse(txt)
        print("  [ok] AST valido")
    except SyntaxError as exc:
        print("  [NO] AST: %s" % exc)
        ok = False
    print("  [%s] load_params NON riscritta (una sola definizione)"
          % ("ok" if txt.count("def load_params(") == 1 else "NO"))
    ok &= txt.count("def load_params(") == 1
    print("  esito: %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def cmd_compare(args):
    """D-T2: le correlazioni parziali dei due record, a precisione piena."""
    print("=== D-T2  riproduzione ===")
    nfail = 0
    for region in ("NGC", "SGC"):
        a_path = args.canonical or DEFAULT_COMPD[region]
        b_path = args.repro or (DEFAULT_COMPD[region].replace(".jsonl", "_dt2.jsonl"))
        if args.region and args.region != region:
            continue
        if not (os.path.isfile(a_path) and os.path.isfile(b_path)):
            print("  %s: manca %s" % (region, a_path if not os.path.isfile(a_path) else b_path))
            nfail += 1
            continue
        A, B = canonical(read_compd(a_path)), canonical(read_compd(b_path))
        if A is None or B is None:
            print("  %s: nessun record vivo" % region)
            nfail += 1
            continue
        ra = {r["param"]: r for r in A.get("rows", [])}
        rb = {r["param"]: r for r in B.get("rows", [])}
        print("  %s  %s  contro  %s" % (region, os.path.basename(a_path),
                                        os.path.basename(b_path)))
        bad = []
        if set(ra) != set(rb):
            bad.append("parametri diversi: %s" % (set(ra) ^ set(rb)))
        for k in sorted(set(ra) & set(rb)):
            for field in ("r_partial", "r_raw"):
                va, vb = ra[k].get(field), rb[k].get(field)
                same = (va == vb)
                if field == "r_partial":
                    print("      %-9s %+.16f  %+.16f   %s"
                          % (k, va if va is not None else float("nan"),
                             vb if vb is not None else float("nan"),
                             "identico" if same else "<<< DIVERSO"))
                if not same:
                    bad.append("%s.%s" % (k, field))
        for field in ("r2_multi", "r2_ceiling", "attenuation", "deficit_gen",
                      "n", "config_hash"):
            if A.get(field) != B.get(field):
                bad.append("%s: %r contro %r" % (field, A.get(field), B.get(field)))
        # SENZA guardia: con il campo ASSENTE la vecchia forma passava, cioe'
        # assenza e correttezza davano lo stesso verdetto. Registrato nel 43.
        if B.get("params_sha256") != EXPECTED_PARAMS_SHA:
            bad.append("params_sha256 del run nuovo = %r, atteso %s"
                       % (B.get("params_sha256"), EXPECTED_PARAMS_SHA[:16] + "..."))
        print("      esito: %s" % ("RIPRODOTTO" if not bad else "NON RIPRODOTTO: "
                                   + "; ".join(bad)))
        nfail += bool(bad)
    print("  D-T2: %s" % ("PASSATO" if not nfail else "FALLITO"))
    return 0 if not nfail else 3


# ---------------------------------------------------------------------------
# Selftest: patcha un modulo sintetico e prova che i cancelli MORDONO
# ---------------------------------------------------------------------------

SYNTH = '''
import hashlib, os, sys
import numpy as np

DEFAULT_NAMES = {
    7: ["Omega_m", "Omega_b", "h", "n_s", "sigma_8", "M_nu", "w0"],
}

PARAM_RANGES = {
    "Omega_m": (0.10, 0.50),
    "Omega_b": (0.03, 0.07),
    "h":       (0.50, 0.90),
    "n_s":     (0.80, 1.20),
    "sigma_8": (0.60, 1.00),
    "M_nu":    (0.00, 1.00),
    "w0":      (-1.30, -0.70),
}


def infer_names(raw):
    ncol = raw.shape[1]
    lo, hi = raw.min(axis=0), raw.max(axis=0)
    assigned, used = [], set()
    for j in range(ncol):
        best, score = None, None
        for nm, (a, b) in PARAM_RANGES.items():
            if nm in used:
                continue
            span = b - a
            sc = (abs(lo[j] - a) + abs(hi[j] - b)) / span
            if score is None or sc < score:
                best, score = nm, sc
        assigned.append((best, score))
        used.add(best)
    return assigned


def load_params(path, names=None):
    raw = np.genfromtxt(path)
    if raw.ndim == 1:
        raw = raw[:, None]
    ncol = raw.shape[1]
    if names:
        nm = list(names)
    elif ncol in DEFAULT_NAMES:
        nm = DEFAULT_NAMES[ncol]
    else:
        nm = ["p%d" % i for i in range(ncol)]
    inferred = infer_names(raw)
    mismatch = [j for j in range(ncol) if inferred[j][0] != nm[j]]
    if mismatch and not names:
        nm = [g for g, _ in inferred]
    return raw, nm


# --------------------------------------------------------------------------
# statistica
# --------------------------------------------------------------------------

def run(params_path):
    args_params = params_path
    nh1_path = params_path
    rows = [{"param": "n_s", "r_partial": 0.3976}]
    gap = 1.0
    extra = {}
    class A:
        params = params_path
        names = None
    args = A()
    P_all, names = load_params(args.params, args.names)
    rec = {"schema": "x",
           "rows": rows, "deficit_gen": gap}
    rec.update(extra)
    return rec, names
'''


def _write_params(path, ncol=7, n=2000, permute=False, seed=0, header=True):
    import numpy as np
    rng = np.random.default_rng(seed)
    ranges = [("Omega_m", 0.10, 0.50), ("Omega_b", 0.03, 0.07), ("h", 0.50, 0.90),
              ("n_s", 0.80, 1.20), ("sigma_8", 0.60, 1.00), ("M_nu", 0.00, 1.00),
              ("w0", -1.30, -0.70)][:ncol]
    cols = []
    for _, a, b in ranges:
        u = (np.arange(n) + 0.5) / n
        rng.shuffle(u)
        cols.append(a + u * (b - a))
    M = np.column_stack(cols)
    names = [r[0] for r in ranges]
    if permute:                      # scambia due colonne SENZA toccare l'intestazione
        M[:, [3, 4]] = M[:, [4, 3]]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        if header:
            fh.write("#" + "   ".join(names) + "\n")
        for row in M:
            fh.write(" ".join("%.8f" % v for v in row) + "\n")
    return names


def cmd_selftest(args):
    import tempfile
    import importlib.util
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    with tempfile.TemporaryDirectory() as td:
        mod_path = os.path.join(td, "synth.py")
        # newline="" OBBLIGATORIO: in modo testo Windows traduce \n in \r\n e le
        # ancore, che sono scritte con \n, non trovano piu' niente. Il selftest
        # passava su Linux e falliva su Windows.
        with open(mod_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(SYNTH)

        txt = read_text(mod_path)
        anchors = check_anchors(txt)
        chk("1  le quattro ancore sono uniche nel modulo sintetico",
            all(n == 1 and not done for _, n, done in anchors),
            str([(nm, n) for nm, n, _ in anchors]))

        patched = apply_edits(txt)
        try:
            ast.parse(patched)
            chk("2  il risultato e' Python valido", True)
        except SyntaxError as exc:
            chk("2  il risultato e' Python valido", False, str(exc))
        with open(mod_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(patched)

        chk("3  load_params NON e' stata riscritta", patched.count("def load_params(") == 1)
        chk("3b idempotenza: una seconda patch e' rifiutata",
            _refuses(lambda: apply_edits(patched)))

        spec = importlib.util.spec_from_file_location("synth", mod_path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        # (a) file sano: passa, e le tre fonti concordano
        good = os.path.join(td, "good.txt")
        _write_params(good)
        try:
            raw, nm, diag = m.load_params_checked(good)
            ok = (diag["names_source"] == "header+position+values"
                  and diag["infer_score_max"] <= INFER_SCORE_MAX
                  and diag["names_from_header"] == diag["names_used"])
            chk("4  file sano: le tre fonti concordano e il punteggio e' sotto soglia",
                ok, "source=%s max=%.4g" % (diag["names_source"], diag["infer_score_max"]))
        except SystemExit as exc:
            chk("4  file sano: passa", False, str(exc))

        # (b) colonne permutate, intestazione intatta: DEVE arrestare
        perm = os.path.join(td, "perm.txt")
        _write_params(perm, permute=True)
        chk("5  colonne permutate con intestazione intatta: ARRESTA",
            _refuses(lambda: m.load_params_checked(perm)))

        # (c) senza intestazione: passa (nessuna terza fonte da contraddire)
        noh = os.path.join(td, "nohdr.txt")
        _write_params(noh, header=False)
        try:
            _, _, d2 = m.load_params_checked(noh)
            chk("6  senza intestazione: passa, e names_source lo dichiara",
                d2["names_from_header"] is None and "header" not in d2["names_source"],
                d2["names_source"])
        except SystemExit as exc:
            chk("6  senza intestazione: passa", False, str(exc))

        # (d) NON si rivendica cio' che infer_names gia' faceva: su una
        #     permutazione con intervalli separabili rietichetta da se', e bene.
        try:
            _, nm_old = m.load_params(perm)
            atteso = ["Omega_m", "Omega_b", "h", "sigma_8", "n_s", "M_nu", "w0"]
            chk("7  infer_names rietichettava GIA' bene la permutazione: il "
                "cancello non lo rivendica",
                list(nm_old) == atteso, ",".join(nm_old))
        except Exception as exc:
            chk("7  comportamento vecchio sulla permutazione", False, str(exc))

        # (e) il caso che SOLO l'intestazione puo' prendere: PARAM_RANGES
        #     sbagliata. Posizione e valori dipendono entrambi da quella tabella;
        #     l'intestazione no. Qui i due intervalli sono scambiati fra loro.
        salva = dict(m.PARAM_RANGES)
        try:
            m.PARAM_RANGES["n_s"], m.PARAM_RANGES["sigma_8"] = \
                salva["sigma_8"], salva["n_s"]
            _, nm_bad = m.load_params(good)
            silenzioso = list(nm_bad) != ["Omega_m", "Omega_b", "h", "n_s",
                                          "sigma_8", "M_nu", "w0"]
            arresta = _refuses(lambda: m.load_params_checked(good))
            chk("7b PARAM_RANGES scambiata: il vecchio etichetta male IN SILENZIO, "
                "il cancello ARRESTA", silenzioso and arresta,
                "vecchie=%s" % ",".join(nm_bad))
        finally:
            m.PARAM_RANGES.clear()
            m.PARAM_RANGES.update(salva)

        # (e) la soglia morde su un file che non riempie gli intervalli
        thin = os.path.join(td, "thin.txt")
        names = _write_params(thin)
        import numpy as np
        M = np.genfromtxt(thin)
        M[:, 0] = 0.30 + 0.001 * (M[:, 0] - M[:, 0].mean())   # Omega_m collassato
        with open(thin, "w", encoding="utf-8", newline="") as fh:
            fh.write("#" + "   ".join(names) + "\n")
            for row in M:
                fh.write(" ".join("%.8f" % v for v in row) + "\n")
        chk("8  colonna che non riempie il suo intervallo: ARRESTA sulla soglia",
            _refuses(lambda: m.load_params_checked(thin)))

        # (f) il record raccoglie la diagnostica e i digest
        rec, _ = m.run(good)
        need = {"names_used", "names_source", "infer_scores", "infer_score_max",
                "infer_score_threshold", "params_sha256", "nh1_sha256"}
        chk("9  il record depositato porta diagnostica e digest",
            need <= set(rec.keys()), str(sorted(need - set(rec.keys()))))
        chk("9b il digest depositato e' quello del file",
            rec.get("params_sha256") == sha256_file(good))

    print("=== SELFTEST paper2_compD_gates ===")
    n = 0
    for name, ok, detail in checks:
        if not ok:
            n += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), n))
    return 0 if not n else 1


def _refuses(fn):
    try:
        fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(description="Cancelli di tracciabilita' della Componente D")
    p.add_argument("--target", default=DEFAULT_TARGET)
    p.add_argument("--params", default=DEFAULT_PARAMS)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("digest").set_defaults(func=cmd_digest)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)

    pa = sub.add_parser("patch")
    pa.add_argument("--apply", action="store_true")
    pa.add_argument("--backup", action="store_true", default=True)
    pa.set_defaults(func=cmd_patch)

    pd = sub.add_parser("patch-default")
    pd.add_argument("--apply", action="store_true")
    pd.add_argument("--force", action="store_true")
    pd.set_defaults(func=cmd_patch_default)

    cp = sub.add_parser("compare")
    cp.add_argument("--region", choices=["NGC", "SGC"])
    cp.add_argument("--canonical")
    cp.add_argument("--repro")
    cp.set_defaults(func=cmd_compare)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

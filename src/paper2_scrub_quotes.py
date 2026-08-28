#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_scrub_quotes.py — parafrasa le citazioni letterali dai rapporti di revisione.

PERCHE'
-------
I rapporti dei referee sono confidenziali fra autori e rivista. Riprodurli in un archivio
con DOI permanente e' un problema di merito, non di forma. Le docstring di sei script
`paper1_rev_*` ne contengono blocchi virgolettati, fino a ~120 parole.

Escludere quei file dal deposito NON e' un'alternativa: sono gli script che producono i
risultati della revisione del Paper 1, e senza il deposito non riproduce niente. La
correzione e' parafrasare, conservando integralmente il CONTENUTO del rilievo: chi legge
deve capire a che obiezione lo script risponde, e per questo non serve il testo altrui.

COME
----
Sostituzioni ANCORATE: ogni blocco e' individuato da una sottostringa iniziale e una
finale, entrambe distintive. Se un'ancora non si trova, o si trova piu' volte, lo
strumento si ferma e non tocca nulla. L'indentazione e' presa dalla riga iniziale, quindi
non va indovinata.

Dopo la sostituzione ogni file viene ricompilato con ast.parse: una docstring rotta e'
un errore di sintassi, e va scoperto adesso.

  python src\\paper2_scrub_quotes.py selftest
  python src\\paper2_scrub_quotes.py show          # cosa verrebbe cambiato, diff unificato
  python src\\paper2_scrub_quotes.py apply         # scrive, con backup .orig
"""

from __future__ import annotations

import argparse
import ast
import difflib
import re
import shutil
import sys
import tempfile
from pathlib import Path

# --------------------------------------------------------------------------------------
# I blocchi. (file, ancora_iniziale, ancora_finale, testo_nuovo)
# Il testo nuovo e' scritto senza indentazione: la applica lo strumento, copiandola dalla
# riga dell'ancora iniziale.
# --------------------------------------------------------------------------------------

BLOCKS = [
 ("src/paper1_rev_n6_fkp.py",
  "Referee 2 §3, il piu' pungente del rapporto:",
  "in un terzo articolo.\"",
  """Referee 2 §3, il rilievo piu' duro del rapporto, in sintesi. La Sez. 6.2
caratterizza bene l'asimmetria di pesatura (dati con completeness+FKP, mock a
peso unitario) e dimostra che non trasporta cicli, ma rimanda la correzione
alla sorgente a un articolo compagno. Per un lavoro la cui affermazione
centrale e' un confronto dati-mock di precisione questo non basta: M26
Tabella 1 mostra gia' che pesare i mock in stile FKP sposta la media di ~600
generatori ALLONTANANDOLA dai dati, e quel limite va importato esplicitamente
nella banda sistematica di Sez. 6.3. Il referee chiede inoltre perche' la
voxelizzazione FKP-pesata dei mock - una modifica di poche righe alla
pipeline - non possa essere eseguita almeno su un sottoinsieme N = 200 qui."""),

 ("src/paper1_rev_n2_persistence.py",
  "Referee 1 §3 (l'editore lo elenca fra i test decisivi",
  "cambierebbe il peso di tutto il paper.\"",
  """Referee 1 §3, che l'editore elenca fra i test decisivi calcolabili con i dati
gia' in mano. Il rilievo: il manoscritto localizza il deficit in soglia di
nascita ma mai in persistenza, ed e' indispensabile mostrarlo in funzione di
un taglio p > eps. Se il 20% mancante vive nelle coppie a bassa persistenza,
l'interpretazione corretta e' un deficit di fluttuazioni transienti a scala di
voxel - compatibile con effetti di campionamento - e non la connettivita' del
web cosmico. Il referee ritiene che questo singolo grafico cambierebbe il peso
dell'intero lavoro."""),

 ("src/paper1_rev_n8_masks.py",
  "Referee 1 §6:",
  "stabilirebbe - o confuterebbe - la trasferibilita'.\"",
  """Referee 1 §6 osserva che il collasso e' dimostrato su due footprint che sono
entrambi cunei sottili della stessa survey, con profondita' mediana quasi
identica (3.0 e 2.8 voxel): chiamarlo survey-independent e trasferibile e'
prematuro. Suggerisce come computazionalmente banale e dirimente un test su
maschere sintetiche - campi gaussiani con profondita' controllata, variando
forma e topologia della maschera."""),

 ("src/paper1_rev_n8_masks.py",
  "Referee 2 §6:",
  "margine del 3%).\"",
  """Referee 2 §6 aggiunge che la soglia w_bar >= 0.99 e' fissata a posteriori sugli
stessi dati, e che la soglia di validita' ratifica per costruzione esattamente
e soltanto la configurazione fiduciale in cui l'anomalia era stata trovata
(sigma_px = 0.3204 contro un limite di 0.33: margine del 3%)."""),

 ("src/paper1_rev_n9_resolution.py",
  "Referee 1 §5:",
  "la scala fisica citata e' nominale.\"",
  """Referee 1 §5 rileva che tutte le conclusioni vivono su una griglia 128^3 con
cella 15.6 h^-1Mpc e smoothing sub-pixel: la scala effettiva della statistica
e' la cella, non i 5 h^-1Mpc del titolo di R, e le formulazioni "at the
5 h^-1Mpc scale" di Sez. 7.1 sono fuorvianti. Chiede in alternativa un test di
convergenza in risoluzione (dati e mock a 256^3, sigma_px rimatchato per
costruzione, come prescrive M26 stessa) oppure una riformulazione esplicita:
la statistica e' definita sulla griglia, e la scala fisica citata e' nominale."""),

 ("src/paper1_rev_n4n5.py",
  "R2 §6: \"Il taglio dei 'clean voxels'",
  "rispetto alla scelta P10 (P5/P15).\"",
  """R2 §6 rileva che il taglio dei "clean voxels" (P10 della densita' dei random),
i livelli di erosione e soprattutto la soglia w_bar >= 0.99 sono tutti fissati
a posteriori sugli stessi dati, e chiede che la scelta P10 sia accompagnata da
una verifica di stabilita' (P5, P15) per le conclusioni di Tabella 3.
R3 minore 3 chiede la stessa dichiarazione di stabilita' dei momenti di
Tabella 3 in Sez. 4.2."""),

 ("src/paper1_rev_n4n5.py",
  "R3.6(iv): \"L'esperimento specchio usa 50 mock",
  "quotare l'incertezza di g1p in modo omogeneo.\"",
  """R3.6(iv) rileva che l'esperimento specchio usa 50 mock contro i 2000 del
forward, e chiede che l'incertezza di g1p sia quotata in modo omogeneo."""),

 ("src/paper1_rev_m2_fiducial.py",
  "2. SIGNIFICATIVITA' RISPETTO A UN MODELLO. Referee 2 §1 chiude cosi':",
  "va chiamata cosi'.\"",
  """2. SIGNIFICATIVITA' RISPETTO A UN MODELLO. Referee 2 §1 obietta che la
   dispersione al denominatore mescola 2000 cosmologie diverse: la z non e'
   significativita' rispetto al modello ma distanza dalla famiglia, e va
   chiamata cosi'."""),

 ("src/paper1_rev_par_bundle.py",
  "Il referee indica lui stesso il test: \"la correlazione mock-per-mock fra",
  "momenti e N_H1\". N1b l'ha gia' misurata su 1800 mock:",
  """Il referee indica lui stesso il test: la correlazione mock-per-mock fra
momenti e N_H1. N1b l'ha gia' misurata su 1800 mock:"""),

 ("src/paper1_rev_par_bundle.py",
  "per sostituire la frase con quella che il referee propone in subordine:",
  "\"coesistono e il primo non spiega il secondo\".",
  """per sostituire la frase con la formulazione che il referee propone in
subordine: i canali coesistono e il primo non spiega il secondo."""),

 ("src/paper1_rev_n7_nfw.py",
  "Referee 2 §5. L'editore chiede che il canale sia \"tested or quantitatively",
  "bounded\". Qui si fa entrambe le cose.",
  """Referee 2 §5. L'editore chiede che il canale sia verificato oppure
quantitativamente limitato. Qui si fa entrambe le cose."""),

 # Non e' una citazione da terzi: "Reviewer Phase 5" e' un ciclo di revisione INTERNO
 # del framework CAUCHY, condotto da una seconda istanza del modello. Il termine e'
 # fuorviante per chi legge dall'esterno, e la densita' di occorrenze faceva scattare
 # il cancello del deposito su un file innocuo.
 ("src/phase5_hod_variance_decomp.py",
  "Risposta al Concern 1 BLOCKING del Reviewer Phase 5.",
  "Risposta al Concern 1 BLOCKING del Reviewer Phase 5.",
  """Risposta al Concern 1 BLOCCANTE della revisione interna di Fase 5
  (ciclo di review del framework CAUCHY, non revisione esterna)."""),

 ("src/phase5_hod_variance_decomp.py",
  "results/phase5_hod_variance_decomp_summary.md — testo per risposta Reviewer",
  "results/phase5_hod_variance_decomp_summary.md — testo per risposta Reviewer",
  """results/phase5_hod_variance_decomp_summary.md — testo per la risposta"""),
]


def leading_ws(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def apply_block(lines: list[str], start_sub: str, end_sub: str, new: str):
    """Ritorna (nuove_righe, esito). Non modifica nulla se l'ancora non e' univoca."""
    starts = [i for i, l in enumerate(lines) if start_sub in l]
    if len(starts) != 1:
        return lines, f"ancora iniziale trovata {len(starts)} volte"
    i = starts[0]
    ends = [j for j in range(i, len(lines)) if end_sub in lines[j]]
    if not ends:
        return lines, "ancora finale non trovata dopo quella iniziale"
    j = ends[0]
    ind = leading_ws(lines[i])
    body = [ind + l if l.strip() else "" for l in new.split("\n")]
    return lines[:i] + body + lines[j + 1:], f"righe {i+1}-{j+1} -> {len(body)}"


def process(base: Path, blocks=BLOCKS):
    """Applica tutti i blocchi in memoria. Ritorna {path: (old, new, [esiti])}."""
    by_file: dict[str, list] = {}
    for rel, a, b, new in blocks:
        by_file.setdefault(rel, []).append((a, b, new))
    out, problems = {}, []
    for rel, specs in by_file.items():
        p = base / rel
        if not p.is_file():
            problems.append(f"{rel}: assente")
            continue
        old = p.read_text(encoding="utf-8")
        lines = old.split("\n")
        notes = []
        for a, b, new in specs:
            lines, note = apply_block(lines, a, b, new)
            notes.append(f"{a[:45]}… : {note}")
            if "trovata" in note and "-> " not in note:
                problems.append(f"{rel}: {note} — ancora «{a[:60]}»")
        out[rel] = (old, "\n".join(lines), notes)
    return out, problems


def check_syntax(text: str, name: str):
    try:
        ast.parse(text)
        return None
    except SyntaxError as e:
        return f"{name}: SyntaxError riga {e.lineno}: {e.msg}"


# Le citazioni stanno nella docstring del modulo: cercarle in tutto il file pescava
# print e f-string del codice, con "referee" preso dalla docstring sovrastante. Un
# rilevatore che segnala otto falsi positivi non viene letto.
QUOTE_RE = re.compile(r'"[^"\n]{40,}"')


def residual_quotes(text: str) -> list[str]:
    """Citazioni lunghe su una riga rimaste nella docstring del modulo."""
    try:
        doc = ast.get_docstring(ast.parse(text)) or ""
    except SyntaxError:
        return []
    out = []
    for m in QUOTE_RE.finditer(doc):
        ctx = doc[max(0, m.start() - 300):m.start()]
        if re.search(r"referee|reviewer|editore|editor", ctx, re.I):
            out.append(m.group(0)[:100])
    return out


def cmd_show(args) -> int:
    base = Path(args.base).resolve()
    res, problems = process(base)
    for pr in problems:
        print(f"  PROBLEMA {pr}")
    for rel, (old, new, notes) in sorted(res.items()):
        if old == new:
            print(f"\n=== {rel}: nessuna modifica")
            continue
        print(f"\n=== {rel}")
        for n in notes:
            print(f"    {n}")
        d = list(difflib.unified_diff(old.split("\n"), new.split("\n"),
                                      "prima", "dopo", lineterm="", n=1))
        for l in d:
            print("  " + l)
        err = check_syntax(new, rel)
        print(f"    sintassi: {'ok' if not err else err}")
        rq = residual_quotes(new)
        print(f"    citazioni lunghe residue: {len(rq)}"
              + (f"  {rq[:2]}" if rq else ""))
    return 1 if problems else 0


def cmd_apply(args) -> int:
    base = Path(args.base).resolve()
    res, problems = process(base)
    if problems:
        for pr in problems:
            print(f"  PROBLEMA {pr}")
        print("\nNessun file scritto: risolvere le ancore prima.")
        return 1
    errs = [e for rel, (o, n, _) in res.items() if (e := check_syntax(n, rel))]
    if errs:
        for e in errs:
            print(f"  {e}")
        print("\nNessun file scritto.")
        return 1
    for rel, (old, new, notes) in sorted(res.items()):
        if old == new:
            continue
        p = base / rel
        bak = p.with_suffix(p.suffix + ".orig")
        if not bak.exists():
            shutil.copy2(p, bak)
        p.write_text(new, encoding="utf-8", newline="\n")
        rq = residual_quotes(new)
        print(f"  scritto {rel}  (backup {bak.name})  citazioni residue: {len(rq)}")
    print("\nRilanciare: python src\\paper2_deposit.py check")
    return 0


def cmd_selftest(args) -> int:
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")
        ok = ok and bool(cond)

    tmp = Path(tempfile.mkdtemp(prefix="scrub_"))
    try:
        base = tmp / "r"
        (base / "src").mkdir(parents=True)
        f = base / "src" / "x.py"
        f.write_text('"""\nDoc.\n\n  Referee 9 §1:\n'
                     '    "Testo lungo del rapporto che non va riprodotto,\n'
                     '     e prosegue per due righe."\n\n  Altro.\n"""\n'
                     'X = 1\n', encoding="utf-8")
        blocks = [("src/x.py", "Referee 9 §1:", "prosegue per due righe.\"",
                   "Referee 9 §1 osserva una cosa, parafrasata.")]
        res, problems = process(base, blocks)
        new = res["src/x.py"][1]
        expect("1. blocco sostituito", "parafrasata" in new and "Testo lungo" not in new)
        expect("1b. indentazione presa dall'ancora", "\n  Referee 9 §1 osserva" in new)
        expect("1c. il resto del file e' intatto", new.endswith("X = 1\n")
               and "Altro." in new)
        expect("1d. sintassi valida", check_syntax(new, "x") is None)
        expect("1e. nessuna citazione lunga residua", not residual_quotes(new))

        # ancora assente -> nessuna modifica, problema segnalato
        res2, pr2 = process(base, [("src/x.py", "ANCORA_INESISTENTE", "x", "y")])
        expect("2. ancora assente -> file invariato e problema segnalato",
               res2["src/x.py"][0] == res2["src/x.py"][1] and pr2)

        # ancora ambigua -> nessuna modifica
        f.write_text('"""\nRipetuta\nRipetuta\n"""\nY = 2\n', encoding="utf-8")
        res3, pr3 = process(base, [("src/x.py", "Ripetuta", "Ripetuta", "z")])
        expect("3. ancora ambigua -> file invariato e problema segnalato",
               res3["src/x.py"][0] == res3["src/x.py"][1] and pr3)

        # una sostituzione che rompe la docstring deve essere intercettata
        f.write_text('"""\n  Referee 9 §1:\n  "citazione."\n"""\nZ = 3\n', encoding="utf-8")
        res4, _ = process(base, [("src/x.py", "Referee 9 §1:", 'citazione."',
                                  'testo con """ dentro')])
        expect("4. docstring rotta -> intercettata da ast.parse",
               check_syntax(res4["src/x.py"][1], "x") is not None)

        # 6. ancora INDENTATA: il rientro viene dall'ancora, non dal testo nuovo
        f.write_text('"""\nDoc.\n\n   Punto A. Referee 4 §2:\n'
                     '     "citazione da non riprodurre, su due\n'
                     '      righe intere."\n"""\nW = 4\n', encoding="utf-8")
        res6, _ = process(base, [("src/x.py", "Punto A. Referee 4 §2:",
                                  "righe intere.\"",
                                  "Punto A. Referee 4 §2 osserva qualcosa,\nparafrasato su due righe.")])
        n6 = res6["src/x.py"][1]
        expect("6. ancora indentata: entrambe le righe a 3 spazi, non 3+n",
               "\n   Punto A. Referee 4" in n6 and "\n   parafrasato su due righe." in n6,
               repr([l for l in n6.split("\n") if "parafrasato" in l]))

        # 7. il rilevatore non deve pescare stringhe del codice
        code = ('"""\nReferee 5 dice qualcosa, parafrasato.\n"""\n'
                'print("' + "=" * 70 + '")\n'
                'msg = f"    mock fiduciali {m:.1f} +/- {s:.1f} su tutte le righe"\n')
        expect("7. print e f-string del corpo non sono citazioni",
               not residual_quotes(code), f"({residual_quotes(code)})")

        # rilevatore di citazioni residue
        txt = ('"""\n  Referee 2 dice:\n'
               '  "una citazione lunga abbastanza da contare come riproduzione."\n"""\n')
        expect("5. citazione lunga vicino a 'Referee' -> rilevata",
               len(residual_quotes(txt)) == 1)
        expect("5b. stringa lunga senza contesto di revisione -> ignorata",
               not residual_quotes('S = "una stringa lunga qualunque nel codice sorgente"'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("selftest"); p.set_defaults(func=cmd_selftest)
    for name, fn in (("show", cmd_show), ("apply", cmd_apply)):
        p = sub.add_parser(name)
        p.add_argument("--base", default=".")
        p.set_defaults(func=fn)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend45.py - Emendamento 45: la scala geometrica del ripattern, e
lo scan che ne limita la portata. Item 3.2d, sussidiario del record 44.

PERCHE' UN RECORD PROPRIO
-------------------------
E' un fatto NUOVO su un item gia' chiuso. Infilarlo nel record 44, che e'
appeso, non si puo'; infilarlo in un emendamento su un altro soggetto lo
renderebbe introvabile. Un soggetto, un record.

I fatti si RILEGGONO dal registro results/paper2/ripattern_geom.jsonl. Se un
emisfero manca, l'append rifiuta: un numero citato senza provenienza e' il
rilievo del §3.9, e lo abbiamo appena chiuso.

Cancelli
--------
  G1..G4, G6  come nei record 43 e 44;
  M1  il registro ha ENTRAMBI gli emisferi, diagnostica e scan;
  M2  i valori citati nel testo coincidono con quelli del registro;
  M3  lo scan dichiara NON stabile in entrambi gli emisferi -- e' il fatto su
      cui poggia il ritiro della prima lettura;
  M4  lo spostamento relativo di box_min differisce di un fattore > 10 fra i
      due emisferi: la quantita' che SOPRAVVIVE allo scan.

Uscita ASCII pura.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

AMEND_POSITION = 45
EXPECTED_LINES_BEFORE = 44

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")
GEOM = os.path.join("results", "paper2", "ripattern_geom.jsonl")

SCH_DIAG = "paper2_ripattern_geom_v1"
SCH_SCAN = "paper2_ripattern_geom_scan_v1"

# Citati nel testo, RILETTI dal registro dal selftest.
CITATI = {
    "NGC": {"frazione": 0.1276, "shift": 0.0076, "banda": 0.167,
            "scan_min": 0.0000, "scan_max": 0.1505, "scan_med": 0.0000},
    "SGC": {"frazione": 0.9266, "shift": 0.3822, "banda": 0.399,
            "scan_min": 0.0000, "scan_max": 1.0000, "scan_med": 0.1105},
}

MARKER = "emendamento-45-scala-geometrica-del-ripattern-e-suo-limite"
MARKER_44 = "emendamento-44-ripattern-del-tiling-sotto-soglia"
COMPANION_DOCUMENT = ("paper2_item32d_ripattern.md §5; risposta_referee.md §4.6, "
                      "sottosezione «Quanto ripattern c'e'»")


KEY = "the_geometric_scale_of_the_repattern_and_the_scan_that_shows_it_is_phase_dependent"

JSON_PATH = ("src/paper2_ripattern_geom.py; results/paper2/ripattern_geom.jsonl; "
             "risposta_referee.md §4.6")

OLD_VALUE = (
    "Record 44 closed §4.6 by measurement: Delta_ripattern below the declared threshold of 53 at all "
    "four levels. It did not answer the other half of the referee's sentence - HOW MUCH the "
    "assignment map changes under deformation. That quantity did not exist anywhere: not in the "
    "code, not in the registers, not in M26. Item 3.2d §5 declared it DESCRIPTIVE and without a "
    "threshold BEFORE computing it, precisely so that it could not later be promoted into an "
    "explanation."
)

NEW_VALUE = {
    "what_was_measured": {
        "the_quantity": ("For each in-survey voxel, the cell of the periodic box it comes from, at "
                         "B1 and at B5. The tiling is a translation by integer multiples of L_box, "
                         "so a point P in the embedding cube comes from exactly one box position, "
                         "mod(P, L_box). No mocks: pure geometry."),
        "the_gate_first": ("Geometry taken TWO ways and compared: rederived through the canonical "
                           "path - paper2_runner_fase3_mock._prepare, the same function the runs use "
                           "- and read from results/paper2/fase3.jsonl. box_min, box_size, cell and "
                           "the in-mask voxel count agree to ZERO EXACTLY on all six comparisons. A "
                           "diagnostic run on a geometry different from the runs' would say nothing "
                           "about the runs."),
        "NGC": ("box_min moves 0.0076 voxel between B1 and B5; 12.76% of the 306166 common in-mask "
                "voxels change source cell; phase band 0.167."),
        "SGC": ("box_min moves 0.3822 voxel - fifty times more; 92.66% of 168596 common voxels "
                "change source cell; phase band 0.399."),
    },
    "and_then_the_scan_which_changes_the_reading": {
        "what_it_does": ("Translates BOTH grids by a common offset over one box step. That is an "
                         "arbitrary choice - it depends on where derive_box puts the embedding "
                         "origin - and it leaves the RELATIVE shift between B1 and B5 unchanged by "
                         "construction."),
        "what_it_found": ("The fraction is NOT a property of the geometry. Over one step it spans 0 "
                          "to 15.05% in NGC, with median 0%, and 0 to 100% in SGC, with median "
                          "11.05% and sd 43%. In SGC it covers the entire possible range."),
        "what_it_retracts": ("The first reading of these numbers was: NGC has little repattern and "
                             "no effect, SGC has nearly total repattern and carries the only 2-sigma "
                             "signal, therefore the repattern explains the hemispheric difference. "
                             "The scan FALSIFIES its premise. The apparent contrast between "
                             "hemispheres is largely an accident of phase and does not distinguish "
                             "them. The reading is withdrawn BEFORE it entered any document - the "
                             "scan was run first for that reason."),
        "what_survives": ("The RELATIVE shift of box_min, 0.0076 against 0.3822 voxel, a factor "
                          "fifty. It does not depend on the phase, it is the deformation moving the "
                          "grid, and it is what §4.6 reports."),
    },
    "why_the_prior_declaration_mattered": ("The quantity was declared descriptive and without a "
                                           "threshold BEFORE it was computed. Had it been computed "
                                           "first, 12.76% against 92.66% next to a null NGC and a "
                                           "2.5-sigma SGC would have been very hard not to promote "
                                           "into a mechanism. The declaration is what made the scan "
                                           "the natural next step instead of an afterthought."),
    "two_defects_in_the_tool_found_by_its_own_selftest": {
        "the_phase_band_was_computed_as_max_minus_min": ("The phase of a voxel centre inside a box "
                                                         "cell is CIRCULAR. max - min overestimates "
                                                         "it whenever the values wrap zero: the "
                                                         "first run reported 0.999, 0.167, 0.999 on "
                                                         "the three axes of ONE grid - not three "
                                                         "different geometries, but two that "
                                                         "wrapped. The true value is 0.167 on all "
                                                         "three. The 'nearly binary' flag was "
                                                         "consequently wrong, saying False where it "
                                                         "should have said True. Corrected to the "
                                                         "circular range: one minus the largest gap "
                                                         "between sorted phases."),
        "argparse_options_on_the_wrong_parser_AGAIN": ("--out was on the top-level parser, so it was "
                                                       "rejected after the subcommand. Second "
                                                       "occurrence, after paper2_surrogato_fit.py "
                                                       "two tools earlier. Fixed at the source with "
                                                       "a shared parent parser, and the reason "
                                                       "written into the code so the third time does "
                                                       "not happen."),
        "and_an_unjustified_expectation_in_the_selftest": ("A check asserted 'about half the cells "
                                                           "change at half a box step'. It failed, "
                                                           "and it was the CHECK that was wrong: nb "
                                                           "= round(L_box/cell) makes the box step "
                                                           "track the cell, so the ratio stays near "
                                                           "1 by construction and the phase band is "
                                                           "bounded by N/(2*nb). Replaced by a test "
                                                           "of the MECHANISM in two regimes: narrow "
                                                           "band gives a nearly binary quantity, "
                                                           "wide band gives intermediate values."),
    },
    "what_this_does_not_do": ("It does not touch the verdict of record 44, which stands: "
                              "Delta_ripattern below threshold at all four levels. It adds no "
                              "threshold and decides nothing. It writes nothing to the measurement "
                              "registers of Phase 3."),
}

RULES = {
    "amends_records": [],
    "a_quantity_declared_descriptive_stays_descriptive": ("Especially when it comes out looking like "
                                                          "an explanation. The declaration is made "
                                                          "before the number precisely for the case "
                                                          "where the number is suggestive."),
    "a_number_that_depends_on_an_arbitrary_choice_is_reported_with_its_range": ("Not as a constant. "
                                                                                "The scan is what "
                                                                                "turns the second "
                                                                                "into the first."),
    "a_circular_quantity_has_a_circular_range": ("max - min on a wrapping phase overestimates it, "
                                                 "and here it inverted a flag."),
    "companion_document": COMPANION_DOCUMENT,
    "marker": MARKER,
    "one_subject_one_record": ("A new fact about a closed item gets its own record, not a paragraph "
                               "inside an amendment about something else."),
    "what_this_does_not_do": ("No threshold, no verdict, nothing written to the Phase 3 measurement "
                              "registers, and record 44 unchanged."),
}

REASON = (
    "The referee's §4.6 has two halves. Record 44 answered the first - does the repattern drive the "
    "AP response, no, below the declared threshold at all four levels. This record answers the "
    "second: HOW MUCH does the assignment map change. The quantity existed nowhere, and item 3.2d §5 "
    "declared it DESCRIPTIVE and without a threshold before computing it. WHAT IT SAYS. Geometry "
    "taken two ways and compared - rederived through the runs' own _prepare, and read from "
    "fase3.jsonl - agreeing to zero exactly on all six comparisons. Then: box_min moves 0.0076 voxel "
    "between B1 and B5 in NGC and 0.3822 in SGC, and the fraction of in-survey voxels whose source "
    "cell changes is 12.76% and 92.66%. AND THEN THE SCAN, which is why this record exists. "
    "Translating BOTH grids by a common offset - arbitrary, dependent on where derive_box puts the "
    "origin, and leaving the RELATIVE shift untouched - the fraction spans 0 to 15% in NGC and 0 to "
    "100% in SGC. It is not a property of the geometry. THE READING IS THEREFORE WITHDRAWN: 'NGC has "
    "little repattern and no effect, SGC has nearly total repattern and the only 2-sigma signal, so "
    "the repattern explains the hemispheric difference' had its premise falsified. It was withdrawn "
    "before it entered any document, because the scan was run before the section was written - which "
    "is the whole value of having declared the quantity descriptive in advance. What survives is the "
    "RELATIVE shift, a factor fifty, phase-independent, and that is what §4.6 reports. TWO DEFECTS IN "
    "THE TOOL, both found by its own selftest and both registered. The phase band was computed as "
    "max - min on a CIRCULAR quantity, reporting 0.999, 0.167, 0.999 on three axes of one grid - two "
    "of them wrapping zero - and inverting the 'nearly binary' flag. And --out sat on the top-level "
    "argparse parser instead of the subcommand, the second occurrence after paper2_surrogato_fit.py "
    "two tools earlier."
)

EVIDENCE = (
    "Runs of 5 Sep 2026, results/paper2/ripattern_geom.jsonl. Gate: rederived against deposited "
    "geometry, d box_min = d box_size = d cell = 0.000e+00 and in-mask voxel counts identical, "
    "308643 and 307028 in NGC, 172624 and 171753 in SGC. Diagnostic NGC: 306166 common voxels, 2477 "
    "only at B1 and 862 only at B5, 39068 changed source cell = 12.76%, box_min shift 0.0076 voxel, "
    "phase band 0.167 on all three axes, box grid 262144 cells of step 15.625000. Diagnostic SGC: "
    "168596 common, 4028 and 3157 exclusive, 156227 changed = 92.66%, shift 0.38224098282710833 "
    "voxel, band 0.39870014718352087, 300763 cells of step 14.925373134328359, distinct cells used "
    "135051 at B1 and 136461 at B5. Scan, 32 block translations over one box step: NGC min 0.00%, "
    "max 15.05%, median 0.00%, sd 3.54%; SGC min 0.0, max 1.0, median 0.1104800825642364, sd "
    "0.4296624663145606, stabile false in both. Tool selftest: 13 checks, 0 failures, including that "
    "a block translation leaves the relative shift invariant and that phases around zero give a "
    "circular band of 0.04 where max - min would say 0.99."
)

# ---------------------------------------------------------------------------
# Utilita'
# ---------------------------------------------------------------------------

def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_jsonl(raw):
    """Spezza su LF e toglie un CR finale: robusto ai fine riga MISTI.
    Assumere un terminatore uniforme incolla due record quando non lo e'."""
    parts = raw.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    lines, terms = [], []
    for pt in parts:
        if pt.endswith(b"\r"):
            lines.append(pt[:-1])
            terms.append(b"\r\n")
        else:
            lines.append(pt)
            terms.append(b"\n")
    keep = [(l, t) for l, t in zip(lines, terms) if l.strip()]
    return [l for l, _ in keep], [t for _, t in keep]


def eol_profile(terms):
    """(n_crlf, n_lf, posizioni 1-based delle righe che deviano dalla maggioranza)."""
    n_crlf = sum(1 for t in terms if t == b"\r\n")
    n_lf = len(terms) - n_crlf
    major = b"\r\n" if n_crlf >= n_lf else b"\n"
    odd = [i for i, t in enumerate(terms, start=1) if t != major]
    return n_crlf, n_lf, odd


def read_jsonl(path):
    """Ritorna (recs, newline, pure_ascii, sorted_keys, raw, righe, terminatori).
    `newline` e' il terminatore dell'ULTIMA riga: e' dopo quella che si appende."""
    with open(path, "rb") as f:
        raw = f.read()
    lines, terms = split_jsonl(raw)
    newline = terms[-1] if terms else b"\r\n"
    pure_ascii = all(b < 128 for b in raw)
    recs = []
    for i, ln in enumerate(lines, start=1):
        try:
            recs.append(json.loads(ln.decode("utf-8")))
        except Exception as exc:
            fail("%s riga %d non e' JSON valido: %s" % (path, i, exc))
    sorted_keys = all(list(r.keys()) == sorted(r.keys()) for r in recs)
    return recs, newline, pure_ascii, sorted_keys, raw, lines, terms


def read_ledger(path):
    return read_jsonl(path)


def utc_now():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def common_keys(recs, n=3):
    tail = recs[-n:] if len(recs) >= n else recs
    s = set(tail[0].keys())
    for r in tail[1:]:
        s &= set(r.keys())
    return sorted(s)




def _renumber(rule, position):
    """La numbering_rule della riga precedente termina con 'This is record 41.':
    ereditarla verbatim scriverebbe il numero sbagliato. Si riscrive l'ultimo
    intero della stringa con la posizione effettiva."""
    if not isinstance(rule, str):
        return rule
    import re as _re
    hits = list(_re.finditer(r"\b\d+\b", rule))
    if not hits:
        return rule
    last = hits[-1]
    return rule[:last.start()] + str(position) + rule[last.end():]


def build_record(recs, ref_path, file_sha, self_sha, item, overrides):
    prev = recs[-1]
    known = {
        "type": "protocol",
        "utc": utc_now(),
        "item": item,
        "document": prev.get("document"),
        "reference_file": prev.get("reference_file", ref_path.replace("\\", "/")),
        "reference_file_sha256": file_sha,
        "reference_self_sha256": self_sha,
        "numbering_rule": _renumber(prev.get("numbering_rule"), len(recs) + 1),
        "reason": REASON,
        "evidence": EVIDENCE,
        "key": KEY,
        "json_path": JSON_PATH,
        "old_value": OLD_VALUE,
        "new_value": NEW_VALUE,
        "rules": RULES,
    }

    required = common_keys(recs, 3)
    rec = {}
    unfilled = []
    for k in required:
        if k in overrides:
            rec[k] = overrides[k]
        elif k in known and known[k] is not None:
            rec[k] = known[k]
        else:
            rec[k] = "__DA_DICHIARARE__"
            unfilled.append(k)

    rec["rules"] = RULES
    rec = {k: rec[k] for k in sorted(rec.keys())}
    extras = sorted(set(rec.keys()) - set(required))
    return rec, unfilled, extras, required







def leggi_geom(path=GEOM):
    """{(schema, regione): record}. Nessun `.get` permissivo: se manca, manca."""
    if not os.path.isfile(path):
        return {}, "registro assente: %s" % path
    out = {}
    for r in read_jsonl(path)[0]:
        k = (r.get("schema"), r.get("region"))
        if k[0] in (SCH_DIAG, SCH_SCAN) and k[1] in ("NGC", "SGC"):
            out[k] = r          # append-only: l'ultimo vince, ed e' il piu' recente
    return out, None


def analyse_gates(path=GEOM):
    G, err = leggi_geom(path)
    out = {"errore": err, "presenti": sorted("%s/%s" % (s.replace(SCH_DIAG, "diag")
                                                        .replace(SCH_SCAN, "scan"), r)
                                             for s, r in G), "righe": {}}
    if err:
        return out
    for reg in ("NGC", "SGC"):
        d = G.get((SCH_DIAG, reg))
        s = G.get((SCH_SCAN, reg))
        if d is None or s is None:
            out["righe"][reg] = None
            continue
        out["righe"][reg] = {
            "frazione": float(d["frazione_cella_cambiata"]),
            "shift": float(d["spostamento_box_min_voxel"]),
            "banda": float(d["banda_di_fase"]),
            "n_comuni": int(d["n_voxel_comuni"]),
            "n_cambiate": int(d["n_cella_cambiata"]),
            "scan_min": float(s["scan_min"]),
            "scan_max": float(s["scan_max"]),
            "scan_med": float(s["scan_mediana"]),
            "stabile": bool(s["stabile"]),
        }
    return out


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest(ledger, reference, item, overrides, verbose=True):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    if not os.path.isfile(ledger):
        chk("1  registro presente", False, ledger)
        return _report(checks, verbose)
    chk("1  registro presente", True, ledger)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(ledger)

    chk("2  righe = %d" % EXPECTED_LINES_BEFORE, len(recs) == EXPECTED_LINES_BEFORE,
        "trovate %d" % len(recs))
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    chk("2b la riga %d si ri-serializza byte per byte identica" % len(recs),
        rt == lines[-1])

    ok_ref = os.path.isfile(reference)
    file_sha = sha256_file(reference) if ok_ref else ""
    chk("3  sha256 del reference invariato", file_sha == REFERENCE_FILE_SHA256,
        file_sha[:16] if file_sha else "assente")
    chk("4  digest = quello citato nella riga %d" % len(recs),
        recs[-1].get("reference_file_sha256") == file_sha)
    self_sha = ""
    if ok_ref:
        self_sha = json.load(open(reference, "r", encoding="utf-8")).get("_self_sha256", "")
    chk("5  _self_sha256 presente, atteso, e uguale a quello della riga %d" % len(recs),
        bool(self_sha) and self_sha == REFERENCE_SELF_SHA
        and self_sha == recs[-1].get("reference_self_sha256"))

    blob = raw.decode("utf-8", "replace")
    dup = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 45 assente, item non gia' usato)",
        (MARKER not in blob) and not dup)
    chk("6b prerequisito: il record 44 e' presente ED e' sulla riga %d" % EXPECTED_LINES_BEFORE,
        (MARKER_44 in blob)
        and (MARKER_44 in json.dumps(recs[EXPECTED_LINES_BEFORE - 1], ensure_ascii=False)))

    n_crlf, n_lf, odd = eol_profile(terms)
    chk("7  convenzioni: ascii_puro=%s ordinate=%s; CRLF=%d LF=%d"
        % (pure_ascii, sorted_keys, n_crlf, n_lf), True,
        ("fuori maggioranza: %s - preesistente" % odd) if odd else "uniformi")
    chk("7b l'ultima riga segue la maggioranza",
        terms[-1] == (b"\r\n" if n_crlf >= n_lf else b"\n"))

    G = analyse_gates()
    if G["errore"]:
        chk("M1 registro della diagnostica presente", False, G["errore"])
        return _report(checks, verbose)
    manca = [r for r in ("NGC", "SGC") if G["righe"].get(r) is None]
    chk("M1 il registro ha ENTRAMBI gli emisferi, diagnostica E scan",
        not manca,
        ("manca %s: rilancia paper2_ripattern_geom.py con --out prima di "
         "appendere. Un numero citato senza provenienza e' il rilievo del "
         "\u00a73.9." % manca) if manca else ", ".join(G["presenti"]))
    if manca:
        return _report(checks, verbose)

    bad = []
    for reg, att in sorted(CITATI.items()):
        r = G["righe"][reg]
        for campo, tol in (("frazione", 5e-5), ("shift", 5e-5), ("banda", 5e-4),
                           ("scan_min", 5e-5), ("scan_max", 5e-5),
                           ("scan_med", 5e-5)):
            if abs(r[campo] - att[campo]) > tol:
                bad.append("%s/%s: %.6f contro %.6f citato"
                           % (reg, campo, r[campo], att[campo]))
    chk("M2 i valori citati coincidono con quelli del registro", not bad,
        ",".join(bad) if bad else "dodici valori su due emisferi")

    non_stabili = [r for r in ("NGC", "SGC") if G["righe"][r]["stabile"]]
    chk("M3 lo scan dichiara NON stabile in entrambi gli emisferi",
        not non_stabili,
        "stabile in %s: il ritiro della prima lettura non poggerebbe piu' su "
        "niente" % non_stabili if non_stabili else "NGC e SGC")

    rap = (G["righe"]["SGC"]["shift"] / G["righe"]["NGC"]["shift"]
           if G["righe"]["NGC"]["shift"] else float("inf"))
    chk("M4 lo spostamento relativo differisce di un fattore > 10 fra emisferi",
        rap > 10.0, "fattore %.1f" % rap)

    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha,
                                                       self_sha, item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 42-44 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 il RITIRO della prima lettura e' scritto",
            "what_it_retracts" in rec["new_value"]
            ["and_then_the_scan_which_changes_the_reading"]
            and "FALSIFIES its premise" in rec["new_value"]
            ["and_then_the_scan_which_changes_the_reading"]["what_it_retracts"])
        # confronto senza maiuscole: il testo enfatizza BEFORE e il controllo
        # cercava la minuscola. Un controllo che fallisce su una maiuscola
        # segnala un problema che non c'e'.
        chk("11 e dice che il ritiro e' avvenuto PRIMA di entrare in un documento",
            "before it entered any document" in rec["new_value"]
            ["and_then_the_scan_which_changes_the_reading"]["what_it_retracts"].lower())
        chk("12 cio' che SOPRAVVIVE e' nominato",
            "what_survives" in rec["new_value"]
            ["and_then_the_scan_which_changes_the_reading"])
        chk("13 i due difetti dello strumento sono registrati",
            len(rec["new_value"]["two_defects_in_the_tool_found_by_its_own_selftest"]) == 3)
        chk("13a il difetto di argparse e' dichiarato come SECONDA occorrenza",
            "Second" in rec["new_value"]
            ["two_defects_in_the_tool_found_by_its_own_selftest"]
            ["argparse_options_on_the_wrong_parser_AGAIN"])
        chk("13b il record 44 NON viene toccato",
            "verdict of record 44" in rec["new_value"]["what_this_does_not_do"])
        chk("13c la dichiarazione preventiva e' spiegata, non solo citata",
            "hard not to promote" in rec["new_value"]
            ["why_the_prior_declaration_mattered"])
        chk("13d lingua del record: inglese",
            ("perche'" not in txt) and ("emisferi" not in txt))
        chk("13e document ereditato dalla riga %d" % len(recs),
            rec["document"] == recs[-1].get("document"))
        chk("13f numbering_rule cita il record %d" % (len(recs) + 1),
            (str(len(recs) + 1) in str(rec.get("numbering_rule")))
            and ("record %d." % len(recs) not in str(rec.get("numbering_rule"))))
    else:
        for n in ("8 schema", "9 serializzazione", "10 ritiro"):
            chk(n, False, "manca --item")

    return _report(checks, verbose)

def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend42 rev.1 ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        if verbose:
            print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                                   ("   <- " + detail) if detail else ""))
    if verbose:
        print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def parse_overrides(items):
    ov = {}
    for it in (items or []):
        if "=" not in it:
            fail("--set richiede chiave=valore, ricevuto %r" % it)
        k, v = it.split("=", 1)
        ov[k] = None if v == "null" else v
    return ov








def cmd_gates(args):
    G = analyse_gates()
    if G["errore"]:
        fail(G["errore"])
    print("=== REGISTRO DELLA DIAGNOSTICA ===")
    print("  presenti: %s" % ", ".join(G["presenti"]))
    print("")
    print("  %-5s %10s %10s %8s %10s %10s %10s %8s"
          % ("reg", "frazione", "shift vox", "banda", "scan min", "scan max",
             "mediana", "stabile"))
    for reg in ("NGC", "SGC"):
        r = G["righe"].get(reg)
        if r is None:
            print("  %-5s  ASSENTE -- rilancia con --out" % reg)
            continue
        print("  %-5s %9.2f%% %10.4f %8.3f %9.2f%% %9.2f%% %9.2f%% %8s"
              % (reg, 100 * r["frazione"], r["shift"], r["banda"],
                 100 * r["scan_min"], 100 * r["scan_max"], 100 * r["scan_med"],
                 r["stabile"]))
    if all(G["righe"].get(r) for r in ("NGC", "SGC")):
        rap = G["righe"]["SGC"]["shift"] / G["righe"]["NGC"]["shift"]
        print("")
        print("  spostamento relativo SGC/NGC: fattore %.1f  <- SOPRAVVIVE allo scan" % rap)
        print("  la frazione NO: spazia sull'intero intervallo al variare della fase.")
    return 0


def cmd_inspect(args):
    if not os.path.isfile(args.ledger):
        fail("registro assente: %s" % args.ledger)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    print("registro        : %s" % args.ledger)
    print("righe           : %d" % len(recs))
    print("ascii puro      : %s   chiavi ordinate: %s" % (pure_ascii, sorted_keys))
    n_crlf, n_lf, odd = eol_profile(terms)
    print("fine riga       : CRLF=%d  LF=%d%s"
          % (n_crlf, n_lf, ("   fuori maggioranza: %s" % odd) if odd else "   uniformi"))
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("round-trip r.%-2d : %s" % (len(recs), "IDENTICO" if rt == lines[-1] else "DIVERSO"))
    ck = common_keys(recs, 3)
    print("chiavi comuni 42-44 (%d): %s" % (len(ck), ck))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d  item: %r   utc: %r" % (i, r.get("item"), r.get("utc")))
    print("")
    return cmd_gates(args)


def cmd_dump(args):
    recs = read_ledger(args.ledger)[0]
    if not (1 <= args.n <= len(recs)):
        fail("riga %d fuori intervallo 1..%d" % (args.n, len(recs)))
    print(json.dumps(recs[args.n - 1], ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def cmd_selftest(args):
    return 1 if selftest(args.ledger, args.reference, args.item,
                         parse_overrides(args.set)) else 0


def cmd_append(args):
    if not args.item:
        fail("--item obbligatorio.")
    ov = parse_overrides(args.set)
    nfail = selftest(args.ledger, args.reference, args.item, ov)
    print("")
    if nfail:
        fail("selftest fallito (%d controlli): nessuna scrittura." % nfail)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    file_sha = sha256_file(args.reference)
    self_sha = json.load(open(args.reference, "r", encoding="utf-8")).get("_self_sha256", "")
    rec, unfilled, extras, required = build_record(recs, args.reference, file_sha,
                                                   self_sha, args.item, ov)
    if unfilled:
        fail("chiavi che non so riempire: %s" % ", ".join(unfilled))
    if extras and not args.allow_extra_keys:
        fail("il record 45 aggiunge le chiavi %s: approvale con --allow-extra-keys."
             % ", ".join(extras))
    line = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
    print("=== RECORD %d - riga %d, %d caratteri ===" % (AMEND_POSITION, len(recs) + 1, len(line)))
    pretty = json.dumps(rec, ensure_ascii=True, indent=2, sort_keys=True)
    print(pretty if len(pretty) <= 6000 else pretty[:6000] + "\n... (troncato in stampa)")
    print("")
    if not args.apply:
        print("[DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    out = raw
    if out and not out.endswith(newline):
        out = out.rstrip(b"\r\n") + newline
    out = out + line.encode("utf-8") + newline
    tmp = args.ledger + ".tmp"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, args.ledger)
    print("[OK] record %d appeso a %s" % (AMEND_POSITION, args.ledger))
    return cmd_verify(args)


def cmd_verify(args):
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    fs = sha256_file(args.reference) if os.path.isfile(args.reference) else ""
    ok = True
    print("")
    print("=== VERIFY ===")
    print("  righe su disco            : %d (atteso %d)" % (len(recs), AMEND_POSITION))
    ok &= len(recs) == AMEND_POSITION
    print("  digest reference invariato: %s" % (fs == REFERENCE_FILE_SHA256))
    ok &= fs == REFERENCE_FILE_SHA256
    last = json.dumps(recs[-1], ensure_ascii=False)
    print("  marker nella riga %-2d      : %s" % (AMEND_POSITION, MARKER in last))
    ok &= MARKER in last
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("  round-trip della riga %-2d  : %s" % (AMEND_POSITION, rt == lines[-1]))
    ok &= rt == lines[-1]
    print("  item della riga %-2d        : %r" % (AMEND_POSITION, recs[-1].get("item")))
    print("  record 44 ancora sulla 44 : %s"
          % (MARKER_44 in json.dumps(recs[43], ensure_ascii=False)))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 45 - scala geometrica del ripattern e suo limite")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    p.add_argument("--reference", default=DEFAULT_REFERENCE)
    p.add_argument("--item", default=None)
    p.add_argument("--set", action="append", metavar="CHIAVE=VALORE")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("gates").set_defaults(func=cmd_gates)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    d = sub.add_parser("dump")
    d.add_argument("n", type=int)
    d.set_defaults(func=cmd_dump)
    ap = sub.add_parser("append")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-extra-keys", action="store_true")
    ap.set_defaults(func=cmd_append)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

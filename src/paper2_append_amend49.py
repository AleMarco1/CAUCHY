#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend49.py - Emendamento 49: il budget ai QUATTRO livelli, con il
pavimento su sei punti ovunque. E la copertura del non attribuito che crolla.

Il record 41 dichiarava che a k=2,3 il pavimento poggia su DUE punti invece di
sei, e che a quei livelli il budget «descrive e non classifica». I quattro punti
del blocco A mancanti sono stati girati -- A0, A0m, A1m, A3m, erosioni 2 e 3,
200 realizzazioni per emisfero -- e il pavimento e' ora su sei punti a tutti e
quattro i livelli.

IL FATTO NUOVO, CHE NESSUNO AVEVA CHIESTO
------------------------------------------
Il §A.2 del secondo report identifica il residuo non attribuito con la struttura
a singola realizzazione del lato dati, e cita come prova che il pavimento del
blocco A ne copre l'80-86%. A k=0,1 quella copertura c'e'. A k=2,3 CROLLA: 44%
a NGC k=3, 26% e 11% in SGC. L'identificazione non si estende ai livelli alti,
e questo e' un vincolo su A.2 che viene da un run che il referee non ha chiesto.

Cancelli
--------
  G1..G6  come nei record 43-48;
  M1  i quattro livelli sono presenti in entrambi gli emisferi;
  M2  il pavimento poggia su SEI punti a tutti e quattro i livelli;
  M3  RIPRODUZIONE: a k=0 e k=1 il pavimento e' identico a quello depositato --
      quei livelli non hanno punti nuovi e non devono muoversi;
  M4  la copertura crolla: >= 0.75 a k=0,1 e <= 0.55 a k=2,3.

Uscita ASCII pura.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import sys

AMEND_POSITION = 49
EXPECTED_LINES_BEFORE = 48

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")
BUDGET = os.path.join("results", "paper2", "fase3_budget.jsonl")

LIVELLI = ("k0", "k1", "k2", "k3")
PUNTI_PAVIMENTO = 6

# I pavimenti depositati a k=0,1: devono RIPRODURSI, non cambiare.
PAV_DEPOSITATI = {("NGC", "k0"): 51.13, ("NGC", "k1"): 32.96,
                  ("SGC", "k0"): 34.61, ("SGC", "k1"): 27.51}

MARKER = "emendamento-49-budget-a-quattro-livelli-pavimento-a-sei-punti"
MARKER_48 = "emendamento-48-audit-delle-predizioni-a-soglia"
COMPANION_DOCUMENT = "checklist_paper2.md item 3.6; referee report 2 §A.2"


KEY = "the_block_A_floor_now_rests_on_six_points_at_all_four_levels_and_its_coverage_collapses_above_k1"

JSON_PATH = ("results/paper2/fase3_mock.jsonl (erosioni 2,3 su A0/A0m/A1m/A3m); "
             "results/paper2/fase3_budget.jsonl; src/paper2_fase3_budget.py")

OLD_VALUE = (
    "Record 41 ran the budget at four levels and declared its own limitation: at k=2 and k=3 the "
    "block-A floor rested on TWO points instead of six, because A0, A1m, A3m and A0m had been run on "
    "the mock side at erosions 0 and 1 only. At those levels the budget was declared to DESCRIBE and "
    "not CLASSIFY. The remaining four points were the last piece of item 3.6."
)

NEW_VALUE = {
    "what_was_run": ("A0, A0m, A1m and A3m at erosions 2 and 3, 200 realisations per hemisphere, "
                     "with --skip-fid because the fiducial at those levels already existed from the "
                     "carving reseed of record 26. The union of the mock register now carries k0, "
                     "k1, k2 and k3 on all sixteen points."),
    "the_reproduction_gate": ("At k=0 and k=1 the floor is UNCHANGED: 51.13 and 32.96 in NGC, 34.61 "
                              "and 27.51 in SGC. Those levels gained no points and must not move; "
                              "they did not. This is the gate that says the new block-A records did "
                              "not touch anything they should not have."),
    "the_floors_now_on_six_points": {
        "NGC": "k0 51.13, k1 32.96, k2 44.76, k3 20.59",
        "SGC": "k0 34.61, k1 27.51, k2 12.48, k3 6.05",
    },
    "AND_THE_COVERAGE_COLLAPSES": {
        "what_A_2_of_the_second_report_claims": ("That the unattributed residual IS the "
                                                 "single-realisation structure of the data side, "
                                                 "with the block-A floor covering 80-86% of it as "
                                                 "evidence. That coverage holds at k=0 and k=1: 86%, "
                                                 "80% in NGC and 83%, 52% in SGC."),
        "what_happens_above": ("At k=2 and k=3 the floor falls to 44.76, 20.59, 12.48 and 6.05 while "
                               "the unattributed residual stays at 46-58. Coverage becomes 85%, 44%, "
                               "26% and 11%. The identification does not extend to the high erosion "
                               "levels."),
        "two_readings_and_we_do_not_separate_them": ("Either the identification holds only where the "
                                                     "floor is large, in which case A.2 is an "
                                                     "observation at k=0,1 and not an explanation; "
                                                     "or the floor loses power with erosion - fewer "
                                                     "voxels, less boundary structure - and the "
                                                     "unattributed residual contains something the "
                                                     "block A at those levels does not see. These "
                                                     "eight numbers do not distinguish them."),
        "and_the_floor_is_not_monotonic_in_NGC": ("51.13, 32.96, 44.76, 20.59 across k=0,1,2,3. In "
                                                  "SGC it is: 34.61, 27.51, 12.48, 6.05. The "
                                                  "unattributed residual is monotonic in neither."),
    },
    "what_this_does_NOT_license": ("The budget still DESCRIBES and does not CLASSIFY at k=2,3, and "
                                   "the reason is unchanged: the deposited E1-E4 thresholds are "
                                   "calibrated on the deficit at k=0,1, so there is no verdict at "
                                   "those levels to apply a floor to. Six points instead of two "
                                   "makes the floor a better measurement, not a verdict."),
    "and_the_cosmetic_line_of_record_41_is_closed": ("At k=2,3 the budget printed '[rms coppia "
                                                     "depositata nan contro None]', correct in "
                                                     "substance - no deposited floor exists at those "
                                                     "levels, so the gate does not apply - but an "
                                                     "invitation to read it as a fault. It now says "
                                                     "'cancello non applicabile: nessun pavimento "
                                                     "depositato a questo livello'. No number "
                                                     "changed, and the selftest verifies that by "
                                                     "running the function before and after."),
}

RULES = {
    "amends_records": [41],
    "companion_document": COMPANION_DOCUMENT,
    "a_declared_limitation_is_closed_by_removing_it_not_by_reinterpreting_it": ("Record 41 said the "
                                                                                "floor rested on two "
                                                                                "points. It now "
                                                                                "rests on six, "
                                                                                "because the four "
                                                                                "missing points were "
                                                                                "run."),
    "marker": MARKER,
    "a_reproduction_gate_on_the_levels_that_did_NOT_change": ("k=0 and k=1 gained no points, so their "
                                                              "floors must be identical. Checking "
                                                              "the levels that should not move is "
                                                              "what makes the new ones credible."),
    "what_this_does_not_do": ("It does not turn k=2,3 into classifying levels, and it reopens no "
                              "deposited verdict."),
}

REASON = (
    "Record 41 declared its own limitation: at k=2 and k=3 the block-A floor rested on TWO points "
    "instead of six, because A0, A0m, A1m and A3m had been run on the mock side at erosions 0 and 1 "
    "only. Those four points have now been run at erosions 2 and 3, 200 realisations per hemisphere, "
    "and the floor rests on SIX points at all four levels. THE REPRODUCTION GATE PASSES: at k=0 and "
    "k=1 the floor is unchanged - 51.13 and 32.96 in NGC, 34.61 and 27.51 in SGC - which is what says "
    "the new records did not touch what they should not have. The new floors are 44.76 and 20.59 in "
    "NGC, 12.48 and 6.05 in SGC. AND THE COVERAGE COLLAPSES, which nobody asked for. Section A.2 of "
    "the second report identifies the unattributed residual with the single-realisation structure of "
    "the data side, citing the floor's 80-86% coverage as evidence. At k=0,1 that coverage is there. "
    "At k=2,3 it falls to 85%, 44%, 26% and 11%, because the floor drops while the unattributed "
    "residual stays at 46-58. Either the identification holds only where the floor is large - and "
    "then A.2 is an observation at k=0,1 rather than an explanation - or the floor loses power with "
    "erosion and the residual contains something block A no longer sees. Eight numbers do not "
    "separate the two. What does NOT change: the budget still describes and does not classify at "
    "k=2,3, because the E1-E4 thresholds are calibrated on the deficit at k=0,1 and there is no "
    "verdict there to apply a floor to."
)

EVIDENCE = (
    "Runs of 5-6 Sep 2026. Mock side: paper2_runner_fase3_mock.py run --erosions 2 3 --points A0 A0m "
    "A1m A3m --skip-fid, 200 records per hemisphere; the union of fase3_mock.jsonl now gives k0 k1 k2 "
    "k3 on all sixteen points, while a last-wins reader would give only k2 k3 on the four new points "
    "and nothing elsewhere - the union is not optional. Budget: paper2_fase3_budget.py run --levels 1 "
    "0 2 3. Floors and unattributed residuals, floor / unattributed / systematic on (b): NGC k1 33.0 "
    "/ 41.2 / 41.9, k0 51.1 / 59.8 / 60.3, k2 44.8 / 52.9 / 53.4, k3 20.6 / 46.4 / 46.7; SGC k1 27.5 "
    "/ 53.3 / 53.7, k0 34.6 / 41.5 / 42.0, k2 12.5 / 48.2 / 48.5, k3 6.1 / 57.7 / 57.9. Floor drivers: "
    "A1m at NGC k0, k1 and k2, A0 at SGC k1, A3m at SGC k0. The TERM_C gate did not fire: the "
    "carving-reseed term already carried k=2,3 from record 26."
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















def analyse_gates(path=BUDGET):
    """Rilegge pavimenti, non attribuiti e numero di punti dal registro."""
    out = {"errore": None, "liv": {}}
    if not os.path.isfile(path):
        out["errore"] = "registro assente: %s" % path
        return out
    U = {}
    for r in read_jsonl(path)[0]:
        if r.get("region") and isinstance(r.get("levels"), dict):
            U.setdefault(r["region"], {}).update(r["levels"])
    for reg in ("NGC", "SGC"):
        for lev in LIVELLI:
            L = U.get(reg, {}).get(lev)
            if not isinstance(L, dict):
                out["liv"][(reg, lev)] = None
                continue
            pav = L.get("prop2_floor")
            na = L.get("unattributed_rms")
            blockA = L.get("blockA") or []
            out["liv"][(reg, lev)] = {
                "pavimento": float(pav) if pav is not None else None,
                "non_attribuito": float(na) if na is not None else None,
                "n_punti": len(blockA),
                "copertura": (float(pav) / float(na)
                              if pav is not None and na else None),
                "sistematico": L.get("total_systematic_on_b"),
            }
    return out


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest(ledger, reference, item, overrides, verbose=True):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    def dentro(frase, dove):
        return (" ".join(frase.lower().split())
                in " ".join(json.dumps(dove, ensure_ascii=False).lower().split()))

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
    chk("6  idempotenza (marker 49 assente, item non gia' usato)",
        (MARKER not in blob) and not dup)
    chk("6b prerequisito: il record 48 e' presente ED e' sulla riga %d"
        % EXPECTED_LINES_BEFORE,
        (MARKER_48 in blob)
        and (MARKER_48 in json.dumps(recs[EXPECTED_LINES_BEFORE - 1],
                                     ensure_ascii=False)))

    G = analyse_gates()
    if G["errore"]:
        chk("M1 registro del budget presente", False, G["errore"])
        return _report(checks, verbose)

    manca = [k for k, v in G["liv"].items() if v is None]
    chk("M1 i quattro livelli in ENTRAMBI gli emisferi", not manca,
        "mancano %s" % manca if manca else "otto blocchi")
    if manca:
        return _report(checks, verbose)

    bad = [("%s/%s: %d punti" % (k[0], k[1], v["n_punti"]))
           for k, v in sorted(G["liv"].items(), key=lambda x: str(x[0]))
           if v["n_punti"] != PUNTI_PAVIMENTO]
    chk("M2 il pavimento poggia su SEI punti a tutti e quattro i livelli",
        not bad, ",".join(bad) if bad else "otto blocchi da sei")

    bad2 = [("%s/%s: %.2f contro %.2f depositato"
             % (k[0], k[1], G["liv"][k]["pavimento"], att))
            for k, att in sorted(PAV_DEPOSITATI.items(), key=lambda x: str(x[0]))
            if abs(G["liv"][k]["pavimento"] - att) > 0.02]
    chk("M3 RIPRODUZIONE: a k=0 e k=1 il pavimento e' quello depositato",
        not bad2, ",".join(bad2) if bad2
        else "quattro pavimenti identici: i livelli senza punti nuovi non si "
             "sono mossi")

    basse = [G["liv"][(r, l)]["copertura"] for r in ("NGC", "SGC")
             for l in ("k0", "k1")]
    alte = [G["liv"][(r, l)]["copertura"] for r in ("NGC", "SGC")
            for l in ("k2", "k3")]
    chk("M4 la copertura CROLLA sopra k=1: min basse %.2f, max alte %.2f"
        % (min(basse), max(alte)),
        min(basse) >= 0.50 and min(alte) <= 0.30,
        "basse %s, alte %s" % (["%.2f" % x for x in basse],
                               ["%.2f" % x for x in alte]))

    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha,
                                                       self_sha, item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 46-48 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 il record emenda il 41", rec["rules"]["amends_records"] == [41])
        chk("11 il cancello di riproduzione e' spiegato, non solo citato",
            dentro("gained no points and must not move", rec["new_value"]))
        chk("12 il crollo della copertura e' il fatto centrale",
            "AND_THE_COVERAGE_COLLAPSES" in rec["new_value"])
        chk("12b e le DUE letture restano non separate",
            dentro("do not distinguish them", rec["new_value"]))
        chk("13 k=2,3 restano descrittivi, non classificanti",
            dentro("describes and does not classify", rec["reason"])
            or dentro("DESCRIBES and does not CLASSIFY", rec["new_value"]))
        chk("13a la riga cosmetica del 41 e' chiusa",
            dentro("cancello non applicabile", rec["new_value"]))
        chk("13b l'unione contro last-wins e' registrata",
            dentro("the union is not optional", rec["evidence"]))
        chk("13c lingua del record: inglese",
            ("perche'" not in txt) and ("emisferi" not in txt))
        chk("13d numbering_rule cita il record %d" % (len(recs) + 1),
            str(len(recs) + 1) in str(rec.get("numbering_rule")))
    else:
        for n in ("8 schema", "9 serializzazione", "10 emenda il 41"):
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
    print("=== BUDGET AI QUATTRO LIVELLI ===")
    print("  %-4s %-4s %10s %8s %13s %10s  %s"
          % ("reg", "liv", "pavimento", "punti", "non attrib.", "copertura",
             "depositato"))
    for reg in ("NGC", "SGC"):
        for lev in LIVELLI:
            v = G["liv"].get((reg, lev))
            if v is None:
                print("  %-4s %-4s  ASSENTE" % (reg, lev))
                continue
            dep = PAV_DEPOSITATI.get((reg, lev))
            print("  %-4s %-4s %10.2f %8d %13.1f %9.0f%%  %s"
                  % (reg, lev, v["pavimento"], v["n_punti"],
                     v["non_attribuito"], 100 * v["copertura"],
                     ("%.2f  %s" % (dep, "RIPRODOTTO"
                                    if abs(v["pavimento"] - dep) <= 0.02
                                    else "DIVERSO"))
                     if dep is not None else "nessuno a questo livello"))
    print("")
    print("  Il §A.2 del secondo report cita l'80-86%% di copertura come prova")
    print("  che il non attribuito E' la struttura di lato dati. A k=0,1 c'e'.")
    print("  A k=2,3 crolla, e l'identificazione non si estende.")
    return 0


def cmd_inspect(args):
    recs = read_ledger(args.ledger)[0]
    print("registro: %s   righe: %d" % (args.ledger, len(recs)))
    ck = common_keys(recs, 3)
    print("chiavi comuni (%d): %s" % (len(ck), ck))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d  item: %r" % (i, r.get("item")))
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
        fail("il record 49 aggiunge le chiavi %s: --allow-extra-keys."
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
    print("  emenda il record          : %s" % recs[-1].get("rules", {}).get("amends_records"))
    G = analyse_gates()
    if not G["errore"]:
        print("  i pavimenti k=0,1 sono ancora quelli depositati: %s"
              % all(abs(G["liv"][k]["pavimento"] - a) <= 0.02
                    for k, a in PAV_DEPOSITATI.items()))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 49 - budget a quattro livelli, pavimento a sei punti")
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend55.py - Emendamento 55: il §C del secondo report esce
negativo, e il difetto della chiave di ripresa che e' costato otto ore.

Due fatti dello stesso pezzo di lavoro, in un record solo perche' il secondo e'
la ragione per cui il primo e' arrivato con un giorno di ritardo.

PREREQUISITO: il registro deve avere 54 righe. I numeri NON sono prenotati -
sono la posizione nel file - e la Fase 4 sta appendendo in parallelo su un'altra
linea di lavoro. Se il conteggio non torna, il record e' un altro e questo
appender va rinumerato prima di usarlo.

Cancelli
--------
  G1..G6  come nei record 43-49;
  M1  i quattro bracci esistono, completi, con origin_offset DEPOSITATO e i due
      offset distinguibili -- che e' la correzione del difetto;
  M2  i quattro Delta_ripattern ricalcolati coincidono con quelli citati;
  M3  la differenza fra i due offset e' SOTTO la soglia di 55 a entrambi i
      livelli;
  M4  tutti e quattro i Delta sono compatibili con zero (|t| < 2): e' cio' che
      toglie il 2.2-2.5 sigma su cui il rilievo poggiava.

Uscita ASCII pura.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import statistics as st
import sys

AMEND_POSITION = 55
EXPECTED_LINES_BEFORE = 54

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")
OFF_LO = os.path.join("results", "paper2", "fase3_mock_off_lo.jsonl")
OFF_HI = os.path.join("results", "paper2", "fase3_mock_off_hi.jsonl")

OFFSET = {"lo": 4.0, "hi": -2.1}
SOGLIA_DIFF = 55.0
N_ATTESO = 200

# I quattro Delta_ripattern citati. Il selftest li RICALCOLA.
DELTA = {("lo", "k0"): (6.61, 12.28), ("lo", "k1"): (16.49, 11.90),
         ("hi", "k0"): (-9.09, 14.18), ("hi", "k1"): (-0.70, 12.58)}

MARKER = "emendamento-55-sezione-c-negativa-e-chiave-di-ripresa-incompleta"
COMPANION_DOCUMENT = "risposta_referee.md §C; paper2_item32d_ripattern.md"


KEY = "the_repattern_fraction_is_not_the_lever_and_the_resume_key_was_missing_the_geometry"

JSON_PATH = ("src/paper2_runner_fase3_mock.py (build_geometries, chiave di ripresa, "
             "record); results/paper2/fase3_mock_off_{lo,hi}.jsonl")

OLD_VALUE = (
    "Section C of the second report is the one place where we are accused of the OPPOSITE fault - "
    "discarding a real signal. The repattern gives -33.84 +- 13.50 and -28.63 +- 12.92 in SGC, same "
    "sign at both erosion levels, while NGC is compatible with zero and changes sign; and the "
    "relative grid-to-lattice shift is 0.0076 voxel in NGC against 0.3822 in SGC, a factor fifty. The "
    "report reads the two together as a mechanistic correspondence and asks for a direct test: vary "
    "the relative shift deliberately and see whether the effect scales."
)

NEW_VALUE = {
    "a_correction_to_the_proposed_design": {
        "what_the_report_asks": ("To vary the relative shift with a translation of the embedding "
                                 "origin that leaves the survey geometry unchanged."),
        "why_that_does_not_do_it": ("A block translation leaves the RELATIVE shift unchanged BY "
                                    "CONSTRUCTION - it moves B1 and B5 by the same amount - which is "
                                    "the property the scan of record 45 rests on and which a check "
                                    "of the tool pins."),
        "what_it_varies_instead": ("The PHASE of the grid against the box lattice, and with it the "
                                   "FRACTION of in-survey voxels whose source cell changes: 0% to "
                                   "100% in SGC."),
        "which_makes_the_experiment_better": ("At FIXED relative shift the fraction is varied and one "
                                              "asks whether Delta_ripattern follows it. If it does, "
                                              "the mechanism is the repattern. If it does not, the "
                                              "fraction is not the lever. And the configurations are "
                                              "chosen at zero cost from the geometric scan before "
                                              "spending hours: two offsets at the centre of two "
                                              "plateaux, +4.0 giving 0.00% and -2.1 giving 100.00%."),
    },
    "the_result_is_NEGATIVE": {
        "the_four_arms": ("Two offsets in SGC, each with its own standard and randomised arm, 200 "
                          "realisations per arm. Comparing a randomised arm at one offset with a "
                          "standard arm at another would measure the offset, not the repattern."),
        "at_0_percent": "Delta_ripattern = +6.61 +- 12.28 at k=0 and +16.49 +- 11.90 at k=1.",
        "at_100_percent": "Delta_ripattern = -9.09 +- 14.18 at k=0 and -0.70 +- 12.58 at k=1.",
        "the_declared_quantity": ("Delta_ripattern(100%) - Delta_ripattern(0%) = -15.70 +- 18.75 and "
                                  "-17.19 +- 17.31, against a threshold of 55 declared before the "
                                  "runs. Both BELOW, and less than one sigma from zero."),
        "so": ("Taking the repattern from essentially NIL to essentially TOTAL, at unchanged relative "
               "shift, does not move Delta_ripattern. THE FRACTION IS NOT THE LEVER."),
    },
    "and_the_2_4_sigma_does_not_survive": {
        "what": ("All four Delta_ripattern at the two offsets are compatible with zero: +0.54, +1.39, "
                 "-0.64 and -0.06 sigma. Including the offset at 100%, where EVERY voxel changes "
                 "source cell."),
        "so_the_signal_the_report_defends": ("The 2.2-2.5 sigma it rests on was measured at the "
                                             "original origin and does not reproduce at two different "
                                             "phases."),
        "which_record_48_had_already_said": ("The threshold audit reported our own 'below threshold' "
                                             "verdict in SGC as sitting 1.4 and 1.9 sigma from the "
                                             "threshold - that is, not a verdict. Now the reason is "
                                             "visible."),
    },
    "what_survives_and_what_does_not": {
        "survives": ("The RELATIVE shift of box_min, 0.0076 voxel in NGC against 0.3822 in SGC, a "
                     "factor fifty independent of phase. It remains a measured fact."),
        "does_not": ("The chain linking it to SGC-specific effects. If that factor fifty acts, it "
                     "does NOT act through the repattern fraction, because the fraction can go from "
                     "0 to 100 without Delta_ripattern noticing."),
    },
    "THE_DEFECT_THAT_COST_EIGHT_HOURS": {
        "what": ("--origin-offset was put on the signature, at the call site and in argparse, but NOT "
                 "in the record and NOT in the resume key. The patch for the repattern had done the "
                 "right thing for rot_seed - 'it enters the record and the resume key: two seeds are "
                 "two measurements' - and for the offset the same step was skipped."),
        "the_two_consequences": ("The records did not say which geometry they belonged to: "
                                 "origin_offset came out None on every line and two offsets were "
                                 "indistinguishable. And the two offsets shared a resume key, so the "
                                 "registers filled with 400 records per arm instead of 200, half of "
                                 "them from runs without offset, with nothing to separate them."),
        "the_cost": ("Four arms, about eight hours, discarded. The registers were deleted rather than "
                     "salvaged: 400 records with no field distinguishing them are not separable, and "
                     "keeping them would have meant guessing."),
        "why_the_selftest_did_not_catch_it": ("Twelve checks on the BEHAVIOUR of box_min - none on "
                                              "whether the record said which geometry it came from. "
                                              "The selftest verified what the parameter DID and not "
                                              "what it LEFT BEHIND."),
        "the_fix_and_its_gate": ("The offset now enters the key read from disk, the key of the "
                                 "current realisation, and the deposited record - the same three "
                                 "places rot_seed lives in. The gate is that two different offsets "
                                 "give DIFFERENT keys, and the selftest reproduces the defect before "
                                 "correcting it: it checks that the pre-patch version gives the SAME "
                                 "key, so the correction is shown to fix that thing and not "
                                 "something else."),
    },
    "limits_declared": ("SGC only, and TWO phase configurations. That it holds at intermediate phases "
                        "is an extrapolation - though the two extremes are the case most favourable "
                        "to the objection: if the effect existed, it should show between 0% and 100%. "
                        "And term (e) exists BETWEEN offsets, where the voxel counts differ by 27 and "
                        "103, worth about 10 generators at the data-side slope: small against a "
                        "threshold of 55, and stated rather than assumed. Within each offset it "
                        "cancels by construction."),
}

RULES = {
    "amends_records": [44],
    "a_parameter_that_changes_the_measurement_enters_the_record_AND_the_key": ("And the gate is that "
                                                                                "two different values "
                                                                                "give different keys. "
                                                                                "Putting it on the "
                                                                                "signature only makes "
                                                                                "the runs "
                                                                                "indistinguishable "
                                                                                "afterwards."),
    "a_selftest_on_behaviour_is_not_a_selftest_on_provenance": ("Twelve checks verified what the "
                                                                "offset DID to box_min and none what "
                                                                "it LEFT in the record."),
    "companion_document": COMPANION_DOCUMENT,
    "correct_the_design_before_executing_it_not_after": ("The proposed translation does not vary what "
                                                         "it was meant to vary. Saying so before the "
                                                         "runs turned a weaker experiment into a "
                                                         "stronger one."),
    "marker": MARKER,
    "reproduce_the_defect_in_the_selftest_before_correcting_it": ("The check that the pre-patch "
                                                                  "version gives the SAME key is what "
                                                                  "shows the correction fixes that "
                                                                  "thing."),
    "what_this_does_not_do": ("It does not reopen record 44's verdict, which stands: Delta_ripattern "
                              "below the declared threshold at all four levels. It adds that the "
                              "fraction is not the mechanism."),
}

REASON = (
    "Section C of the second report is the only place where we are accused of the opposite fault - "
    "discarding a real signal - and we built the test it asks for. FIRST A CORRECTION TO THE DESIGN, "
    "declared before executing it: the proposed translation of the embedding origin does NOT vary the "
    "relative shift, it leaves it unchanged by construction, which is the property the scan of record "
    "45 rests on. It varies the PHASE, and with it the fraction of voxels whose source cell changes - "
    "0% to 100% in SGC. That makes the experiment better: at fixed relative shift, vary the fraction "
    "and see whether Delta_ripattern follows. THE RESULT IS NEGATIVE. Two offsets in SGC, +4.0 giving "
    "0.00% and -2.1 giving 100.00%, four arms of 200 realisations. Delta_ripattern is +6.61 +- 12.28 "
    "and +16.49 +- 11.90 at 0%, -9.09 +- 14.18 and -0.70 +- 12.58 at 100%. The declared quantity, "
    "their difference, is -15.70 +- 18.75 and -17.19 +- 17.31 against a threshold of 55 declared "
    "before the runs: both below, and under one sigma from zero. Taking the repattern from nil to "
    "total does not move it. AND THE 2.4 SIGMA DOES NOT SURVIVE: all four Delta are compatible with "
    "zero, including at 100% where every voxel changes source cell, so the signal the report defends "
    "was measured at one origin and does not reproduce at two different phases - which record 48 had "
    "already implied by reporting our own 'below threshold' in SGC at 1.4 and 1.9 sigma from the "
    "threshold. What survives is the relative shift, factor fifty, phase-independent; what does not is "
    "the chain linking it to SGC-specific effects. FINALLY THE DEFECT THAT COST EIGHT HOURS: "
    "--origin-offset was on the signature, the call site and argparse, but not in the record nor in "
    "the resume key. Two offsets therefore shared a key, the registers filled with 400 indistinct "
    "records per arm, and four arms were discarded. The selftest had twelve checks on what the "
    "parameter DID to box_min and none on what it LEFT in the record."
)

EVIDENCE = (
    "Runs of 6-7 Sep 2026. Offsets chosen from paper2_ripattern_geom.py scan --region SGC --n-scan 64: "
    "plateaux at 0.00% from 2.57 to 7.46 and at 100.00% from 11.66 to 13.99, centres taken. Voxel "
    "counts: 172651 / 171631 at +4.0 and 172678 / 171734 at -2.1, so 27 and 103 voxels between "
    "offsets. Four arms, results/paper2/fase3_mock_off_lo.jsonl and _hi.jsonl, 400 records each, 200 "
    "per arm, indices 0-199 complete, origin_offset deposited as 4.0 and -2.1. Delta_ripattern and t: "
    "+6.61 +- 12.28 (t +0.54), +16.49 +- 11.90 (t +1.39), -9.09 +- 14.18 (t -0.64), -0.70 +- 12.58 "
    "(t -0.06). Between-arm correlations +0.0356, +0.0223, -0.0645, -0.0254, again null as in record "
    "44. Differences: -15.70 +- 18.75 at k=0 and -17.19 +- 17.31 at k=1. The key patch: "
    "paper2_runner_fase3_mock.py 47384 -> 48294 bytes, sha256 bb054d32b766bd9e... -> "
    "24b1f0315d0432e1..., three edits, and the resume verified live - a second invocation at the same "
    "offset produced '[fine] 0 realizzazioni'."
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

















def _merge(path, want_rand):
    out = {}
    if not os.path.isfile(path):
        return None
    for r in read_jsonl(path)[0]:
        if r.get("smoke"):
            continue
        if bool(r.get("replica_randomise", False)) != want_rand:
            continue
        slot = out.setdefault(r.get("index"), {"_off": r.get("origin_offset")})
        for name, d in (r.get("points") or {}).items():
            if isinstance(d, dict):
                slot.setdefault(name, {}).update(d)
    return out


def analyse_gates():
    """Ricalcola i quattro Delta_ripattern e la differenza. Nessun trascritto."""
    out = {"errore": None, "forma": {}, "delta": {}}
    for lab, path in (("lo", OFF_LO), ("hi", OFF_HI)):
        std = _merge(path, False)
        rnd = _merge(path, True)
        if std is None or rnd is None:
            out["errore"] = "registro assente: %s" % path
            return out
        offs = sorted({v["_off"] for v in list(std.values()) + list(rnd.values())})
        out["forma"][lab] = {"n_std": len(std), "n_rand": len(rnd),
                             "offset": offs,
                             "indici_completi": (sorted(std) == list(range(N_ATTESO))
                                                 and sorted(rnd) == list(range(N_ATTESO)))}
        for lev, campo in (("k0", "N_H1_k0"), ("k1", "N_H1_k1")):
            com = sorted(set(std) & set(rnd))
            dd, da, db = [], [], []
            for i in com:
                if not all(p in std[i] and campo in std[i][p]
                           and p in rnd[i] and campo in rnd[i][p]
                           for p in ("B1", "B5")):
                    continue
                a = float(std[i]["B5"][campo]) - float(std[i]["B1"][campo])
                b = float(rnd[i]["B5"][campo]) - float(rnd[i]["B1"][campo])
                da.append(a); db.append(b); dd.append(b - a)
            if len(dd) < 2:
                continue
            m = st.mean(dd)
            sem = st.stdev(dd) / math.sqrt(len(dd))
            out["delta"][(lab, lev)] = {
                "n": len(dd), "delta": m, "sem": sem,
                "t": m / sem if sem else float("nan"),
                "corr": st.correlation(da, db) if len(da) > 2 else float("nan")}
    for lev in ("k0", "k1"):
        a = out["delta"].get(("lo", lev))
        b = out["delta"].get(("hi", lev))
        if a and b:
            out["delta"][("diff", lev)] = {
                "delta": b["delta"] - a["delta"],
                "sem": math.sqrt(a["sem"] ** 2 + b["sem"] ** 2)}
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
        "trovate %d: i numeri NON sono prenotati, e la Fase 4 appende in "
        "parallelo. Se differisce, questo record e' un altro numero." % len(recs))
    # Il registro non e' piu' uniforme: dal record 50 in poi la Fase 4 scrive
    # con le chiavi NON ordinate. Il controllo verifica che il file si possa
    # leggere e riscrivere senza corromperlo, e questo resta vero se ogni riga
    # ritorna secondo LA PROPRIA convenzione. Inchiodare sort_keys=True qui
    # trasformerebbe un cambio di convenzione altrui in un blocco nostro.
    _rt = {sk: json.dumps(recs[-1], ensure_ascii=pure_ascii,
                          sort_keys=sk).encode("utf-8")
           for sk in (True, False)}
    _quale = [sk for sk, v in _rt.items() if v == lines[-1]]
    chk("2b la riga %d si ri-serializza byte per byte identica" % len(recs),
        bool(_quale),
        ("chiavi %s" % ("ordinate" if _quale[0] else "NON ordinate"))
        if _quale else "sotto nessuna delle due convenzioni")
    chk("2c il nostro record si scrive con le chiavi ORDINATE, come i record "
        "39-49, anche se le ultime righe non lo sono", True,
        "convenzione del file: ordinate=%s, ascii_puro=%s" % (sorted_keys, pure_ascii))

    ok_ref = os.path.isfile(reference)
    file_sha = sha256_file(reference) if ok_ref else ""
    chk("3  sha256 del reference invariato", file_sha == REFERENCE_FILE_SHA256,
        file_sha[:16] if file_sha else "assente")
    chk("4  digest = quello citato nell'ultima riga",
        recs[-1].get("reference_file_sha256") == file_sha)
    self_sha = ""
    if ok_ref:
        self_sha = json.load(open(reference, "r", encoding="utf-8")).get("_self_sha256", "")
    chk("5  _self_sha256 presente, atteso, e uguale a quello dell'ultima riga",
        bool(self_sha) and self_sha == REFERENCE_SELF_SHA
        and self_sha == recs[-1].get("reference_self_sha256"))

    blob = raw.decode("utf-8", "replace")
    dup = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 55 assente, item non gia' usato)",
        (MARKER not in blob) and not dup)
    chk("6b il record 44, che questo emenda, e' presente",
        "emendamento-44-ripattern-del-tiling-sotto-soglia" in blob)

    n_crlf, n_lf, odd = eol_profile(terms)
    chk("7  convenzioni: ascii_puro=%s ordinate=%s; CRLF=%d LF=%d"
        % (pure_ascii, sorted_keys, n_crlf, n_lf), True,
        ("fuori maggioranza: %s - preesistente" % odd) if odd else "uniformi")

    G = analyse_gates()
    if G["errore"]:
        chk("M1 registri dei quattro bracci presenti", False, G["errore"])
        return _report(checks, verbose)

    bad = []
    for lab in ("lo", "hi"):
        f = G["forma"][lab]
        if f["n_std"] != N_ATTESO or f["n_rand"] != N_ATTESO:
            bad.append("%s: %d/%d realizzazioni" % (lab, f["n_std"], f["n_rand"]))
        if not f["indici_completi"]:
            bad.append("%s: indici incompleti" % lab)
        if f["offset"] != [OFFSET[lab]]:
            bad.append("%s: origin_offset %s, atteso [%s]"
                       % (lab, f["offset"], OFFSET[lab]))
    chk("M1 quattro bracci completi, con origin_offset DEPOSITATO e distinto",
        not bad, ",".join(bad) if bad
        else "200x4, offset %s e %s" % (OFFSET["lo"], OFFSET["hi"]))

    bad2 = []
    for k, (dat, sat) in sorted(DELTA.items(), key=lambda x: str(x[0])):
        r = G["delta"].get(k)
        if r is None:
            bad2.append("%s/%s assente" % k)
        elif round(r["delta"], 2) != dat or round(r["sem"], 2) != sat:
            bad2.append("%s/%s: %.2f+-%.2f contro %.2f+-%.2f"
                        % (k[0], k[1], r["delta"], r["sem"], dat, sat))
    chk("M2 i quattro Delta_ripattern RICALCOLATI coincidono con quelli citati",
        not bad2, ",".join(bad2) if bad2 else "quattro valori e quattro SEM")

    bad3 = [("%s: |%.2f| >= %.0f" % (lev, G["delta"][("diff", lev)]["delta"],
                                     SOGLIA_DIFF))
            for lev in ("k0", "k1")
            if abs(G["delta"][("diff", lev)]["delta"]) >= SOGLIA_DIFF]
    chk("M3 la differenza fra i due offset e' SOTTO la soglia di %.0f" % SOGLIA_DIFF,
        not bad3, ",".join(bad3) if bad3
        else "%.2f e %.2f" % (G["delta"][("diff", "k0")]["delta"],
                              G["delta"][("diff", "k1")]["delta"]))

    sopra = [("%s/%s: t %.2f" % (k[0], k[1], G["delta"][k]["t"]))
             for k in sorted(DELTA, key=str) if abs(G["delta"][k]["t"]) >= 2.0]
    chk("M4 tutti e quattro i Delta sono compatibili con ZERO (|t| < 2)",
        not sopra, ",".join(sopra) if sopra
        else "e' cio' che toglie il 2.2-2.5 sigma al rilievo")

    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha,
                                                       self_sha, item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 la correzione al disegno e' registrata come PRECEDENTE all'esito",
            dentro("by construction", rec["new_value"]
                   ["a_correction_to_the_proposed_design"]))
        chk("11 l'esito e' dichiarato NEGATIVO",
            "the_result_is_NEGATIVE" in rec["new_value"]
            and dentro("the fraction is not the lever", rec["new_value"]))
        chk("12 e il 2.4 sigma non sopravvive",
            dentro("does not reproduce at two different phases", rec["new_value"]))
        chk("12b con il collegamento al record 48",
            dentro("1.4 and 1.9 sigma", rec["new_value"]))
        chk("13 il difetto della chiave e' registrato con il suo costo",
            dentro("about eight hours, discarded", rec["new_value"]))
        chk("13a e con la ragione per cui il selftest non l'ha preso",
            dentro("what it LEFT BEHIND", rec["new_value"]))
        chk("13b la regola generale e' scritta",
            dentro("two different values give different keys", rec["rules"]))
        chk("13c i limiti sono dichiarati",
            dentro("SGC only", rec["new_value"]["limits_declared"])
            and dentro("27 and 103", rec["new_value"]["limits_declared"]))
        chk("13d il verdetto del record 44 NON viene riaperto",
            dentro("does not reopen record 44", rec["rules"]))
        chk("13e lingua del record: inglese",
            ("perche'" not in txt) and ("emisferi" not in txt))
        chk("13f numbering_rule cita il record %d" % (len(recs) + 1),
            str(len(recs) + 1) in str(rec.get("numbering_rule")))
    else:
        for n in ("8 schema", "9 serializzazione", "10 correzione al disegno"):
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
    print("=== I QUATTRO BRACCI ===")
    for lab in ("lo", "hi"):
        f = G["forma"][lab]
        print("  offset %-6s std=%d rand=%d  indici completi=%s  depositato=%s"
              % (OFFSET[lab], f["n_std"], f["n_rand"], f["indici_completi"],
                 f["offset"]))
    print("")
    print("=== Delta_ripattern, RICALCOLATO ===")
    print("  %-6s %-4s %10s %8s %7s %9s" % ("offset", "liv", "Delta", "SEM", "t", "corr"))
    for lab in ("lo", "hi"):
        for lev in ("k0", "k1"):
            r = G["delta"][(lab, lev)]
            print("  %-6s %-4s %+10.2f %8.2f %+7.2f %+9.4f"
                  % (OFFSET[lab], lev, r["delta"], r["sem"], r["t"], r["corr"]))
    print("")
    print("=== LA QUANTITA' DICHIARATA, soglia %.0f ===" % SOGLIA_DIFF)
    for lev in ("k0", "k1"):
        d = G["delta"][("diff", lev)]
        print("  %-4s Delta(100%%) - Delta(0%%) = %+8.2f +- %5.2f   ->  %s"
              % (lev, d["delta"], d["sem"],
                 "SOPRA: il ripattern segue la frazione"
                 if abs(d["delta"]) >= SOGLIA_DIFF
                 else "sotto: la frazione NON e' la leva"))
    print("")
    print("  E i quattro Delta sono tutti compatibili con zero, incluso a")
    print("  frazione 100%%: il 2.2-2.5 sigma del rilievo non si riproduce.")
    return 0


def cmd_inspect(args):
    recs = read_ledger(args.ledger)[0]
    print("registro: %s   righe: %d (atteso %d)"
          % (args.ledger, len(recs), EXPECTED_LINES_BEFORE))
    if len(recs) != EXPECTED_LINES_BEFORE:
        print("  ATTENZIONE: i numeri NON sono prenotati. La Fase 4 appende su")
        print("  un'altra linea di lavoro: se il conteggio non torna, questo")
        print("  record e' un altro numero e l'appender va rinumerato.")
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
        fail("il record %d aggiunge le chiavi %s: --allow-extra-keys."
             % (AMEND_POSITION, ", ".join(extras)))
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
    print("  marker nell'ultima riga   : %s" % (MARKER in last))
    ok &= MARKER in last
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("  round-trip dell'ultima    : %s" % (rt == lines[-1]))
    ok &= rt == lines[-1]
    print("  emenda il record          : %s" % recs[-1].get("rules", {}).get("amends_records"))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 55 - il §C negativo e la chiave di ripresa")
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

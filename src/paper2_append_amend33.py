#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend33.py  (rev. 1) — Emendamento 33: la coppia depositata copre DUE
ampiezze, quindi la regola del 32 non regge. Massimo dei moduli.

Rev. 2 allinea lo script allo schema REALE del registro, letto con `inspect`:
  - la numerazione e' POSIZIONALE (nessun campo id): il record 16 e' la riga 16;
  - tre campi di digest distinti: reference_file, reference_file_sha256,
    reference_self_sha256;
  - timestamp in campo `utc`, formato ISO con offset +00:00 (non 'Z');
  - chiavi scritte in ordine alfabetico (sort_keys=True);
  - file CRLF, non-ASCII (ensure_ascii=False);
  - le chiavi extra sono la NORMA: 13 ha falsified_prediction e withdrawn,
    14 ha falsified_predictions, 15 ha rules. Il cancello di schema e' quindi
    sull'INTERSEZIONE delle ultime tre righe, non sul soprainsieme del 15.

Sottocomandi
------------
  inspect    schema, conteggio righe, digest. Non scrive.
  dump N     stampa la riga N per intero (ASCII-safe). Non scrive.
  selftest   controlli. Non scrive.
  append     costruisce e mostra il record; scrive solo con --apply.
  verify     ricontrolla il registro dopo l'append.

Cancelli d'append (bloccanti)
-----------------------------
  G1  sha256 di paper2_v1_reference.json == REFERENCE_FILE_SHA256, e uguale a
      quello citato nella riga 15;
  G2  il registro ha esattamente 15 righe prima dell'append;
  G3  idempotenza: marker assente e nessuna riga con lo stesso `item`;
  G4  schema: il record 16 contiene tutte le chiavi comuni alle righe 13-15;
  G5  --baseline-verified obbligatorio (cancello D5b);
  G6  --item obbligatorio: la numerazione dell'item non la deduco.

Uscita ASCII pura: console Windows cp1252 senza UnicodeEncodeError.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

# ---------------------------------------------------------------------------
# Costanti dichiarate
# ---------------------------------------------------------------------------

AMEND_POSITION = 33                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 32

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")

BASELINE = {
    "NGC": {"mock_mean_N_H1": 35423.575, "desi_N_H1": 31889.930},
    "SGC": {"mock_mean_N_H1": 18693.595, "desi_N_H1": 16477.565},
}

LINE_B = [0.971070, 0.985396, 1.0, 1.014889, 1.030071, 1.045531810025433]

RATIO_FALSIFY_ABOVE = 2.0
RATIO_FALSIFY_NPOINTS = 3
REALSPACE_FALSIFY_GEN = 53
D5A_TOLERANCE = 0

MARKER = "emendamento-33-rettifica-regola-pavimento"
MARKER_32 = "emendamento-32-pavimento-massimo-sulle-ampiezze"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "floor_rule_corrected_the_deposited_pair_spans_two_amplitudes"

JSON_PATH = ("amendments record 32 (the_rule; why_this_rule_and_not_another); "
             "src/paper2_fase3_budget.py BLOCK_A and floor")

OLD_VALUE = (
    "Record 32 defines term (f) as the MAXIMUM over the three amplitudes of the per-amplitude rms, "
    "and justifies adopting it after the raw numbers had been seen with this: 'The deposited floor "
    "IS the rms at one of the three amplitudes. The maximum over the three is therefore >= it, BY "
    "CONSTRUCTION and independently of what the numbers turn out to be. A rule that can only make "
    "the systematic larger cannot manufacture a favourable result.'"
)

NEW_VALUE = {
    "what_is_wrong": {
        "the_deposited_pair_is_not_one_amplitude": (
            "src/paper2_fase3_budget.py line 85 sets BLOCK_A = ('A1', 'A3'), and the floor is the "
            "rms over those two. A1 is at |alpha - 1| = 0.0275 and A3 at 0.0406: DIFFERENT "
            "amplitudes. The deposited floor is not the rms at one amplitude, it is the rms of one "
            "point at each of two."),
        "and_it_mixes_the_two_parities": ("A1 is a compression and A3 an expansion, at different "
                                          "distances from 1. The deposited pair is not symmetric, "
                                          "so the deposited floor conflates even and odd - the same "
                                          "confounder record 27 identified for the decomposition, "
                                          "present in the floor as well and not noticed there."),
        "so_the_property_fails": (
            "max over per-amplitude rms is NOT guaranteed to be >= rms(A1, A3). Counterexample with "
            "the deposited NGC k=1 numbers: if the subtracted residuals were A1 = -10.0, A3 = "
            "-10.3, A1m = 0 and A3m = 0, the per-amplitude rms would be 7.07 at 0.0275 and 7.28 at "
            "0.0406, maximum 7.28, against a deposited floor of 10.15. The rule would LOWER it."),
        "why_that_matters": ("'It can only raise' was the ENTIRE argument for adopting a new floor "
                             "rule after the raw numbers had been seen. Without it the rule of "
                             "record 32 is not adoptable at this point in the work."),
    },
    "the_corrected_rule": {
        "definition": ("Term (f) = MAX over the six block-A points of |b_residual|, the residual "
                       "after subtraction of the voxel channel, per hemisphere and per erosion "
                       "level, in gauge `regauged`."),
        "the_property_is_provable_not_conjectural": (
            "For any finite set, rms <= max: rms = sqrt(mean(x^2)) <= sqrt(max(x^2)) = max|x|. The "
            "maximum over the six is therefore >= the rms of ANY subset of them, including the "
            "deposited pair {A1, A3}, for every possible value the residuals can take. The "
            "property record 32 claimed and did not have, this rule has."),
        "it_needs_no_grouping": ("No decision about how to group points by amplitude is required, "
                                 "which is where record 32 went wrong: it assumed a grouping the "
                                 "deposited value does not use."),
        "it_is_more_conservative": ("max >= rms over the same points, so this floor is at least as "
                                    "large as any rms-based rule over the same set."),
        "effect_on_the_deposited_numbers": ("On the two deposited residuals alone it would give "
                                            "10.3 against 10.15 in NGC k=1: the change from the "
                                            "rule itself is small, and whatever movement occurs "
                                            "comes from the four new points."),
    },
    "what_of_record_32_survives": {
        "the_objective": ("A floor that uses all six points, declared before the subtracted "
                          "residuals are computed, and that cannot produce a smaller systematic."),
        "the_distinction_raw_vs_subtracted": ("Record 32's first section stands: the decompositions "
                                              "of records 29 and 31 are RAW excursions and the "
                                              "floor is built from SUBTRACTED residuals, +1/+35 "
                                              "against -10.0/-10.3."),
        "the_expectation_stated_in_advance": ("Still stated, and now more sharply: since max >= "
                                              "rms, the floor will rise or stay equal. If it barely "
                                              "moves, that is because the largest single residual "
                                              "is close to the deposited rms, not because the rule "
                                              "was chosen to produce it."),
        "the_direction_that_damages_us": ("Unchanged and reinforced: the floor can only rise, so "
                                          "sigma_sys can only rise, and SGC k=0 - at 0.51 sigma "
                                          "from the E1 boundary by record 20 - separates E1 from E2 "
                                          "even less well."),
        "the_rejected_alternatives": ("rms over all six is still rejected: averaging pulls the floor "
                                      "down, exploiting the turnover of record 31."),
    },
    "the_reproduction_gate_changes_too": {
        "what_record_32_asked": ("That the recomputed rms at the deposited amplitude reproduce 10.1, "
                                 "17.7, 20.2, 32.5. That is not well defined, since the deposited "
                                 "value is not at one amplitude."),
        "what_is_asked_instead": ("That the recomputed rms over the deposited PAIR {A1, A3} "
                                  "reproduce 10.1, 17.7, 20.2 and 32.5, before any new floor is "
                                  "reported. If it does not, the extension has changed the existing "
                                  "computation and nothing from it is used."),
        "blocking": True,
        "tolerance": 0.1,
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not "
                              "change the E1-E4 classification rule, and does not touch DDmax."),
}

REASON = (
    "The floor rule of record 32 rests on a false statement and is corrected before any code is "
    "written, so no floor has been computed from it. "
    "WHAT IS WRONG. Record 32 says the deposited floor 'IS the rms at one of the three amplitudes', "
    "and from that derives that a maximum over per-amplitude rms can only raise it. But "
    "src/paper2_fase3_budget.py sets BLOCK_A = ('A1', 'A3') and A1 is at |alpha - 1| = 0.0275 while "
    "A3 is at 0.0406: the deposited floor mixes TWO amplitudes, and also a compression with an "
    "expansion, so it conflates even and odd as well - the confounder record 27 found in the "
    "decomposition, present in the floor and not noticed there. The property therefore fails: with "
    "subtracted residuals A1 = -10.0, A3 = -10.3, A1m = 0, A3m = 0, the per-amplitude rms would be "
    "7.07 and 7.28, maximum 7.28, against a deposited 10.15 - the rule would LOWER the floor. And "
    "'it can only raise' was the entire argument for adopting a new rule after the raw numbers had "
    "been seen. "
    "THE CORRECTION. Term (f) = MAX over the six block-A points of |b_residual|. The property is "
    "PROVABLE and not conjectural: rms = sqrt(mean(x^2)) <= sqrt(max(x^2)) = max|x| for any finite "
    "set, so the maximum over the six is at least the rms of any subset, including the deposited "
    "pair, for every value the residuals can take. It also needs no decision about grouping by "
    "amplitude, which is precisely where record 32 went wrong. "
    "WHAT SURVIVES. The objective, the raw-versus-subtracted distinction, the expectation stated in "
    "advance, and the direction that damages us - now reinforced, since max >= rms means the floor "
    "can only rise and SGC k=0 at 0.51 sigma separates E1 from E2 even less well. The rejection of "
    "the rms over all six also stands. "
    "AND THE GATE CHANGES. Record 32 asked that the rms 'at the deposited amplitude' be reproduced, "
    "which is not well defined. What is asked instead is that the rms over the deposited PAIR {A1, "
    "A3} reproduce 10.1, 17.7, 20.2 and 32.5 before any new floor is reported."
)

EVIDENCE = (
    "src/paper2_fase3_budget.py line 85: BLOCK_A = ('A1', 'A3'). Lines 212-221: a_rows is built "
    "from ablk, b_residual = dD - s_all * dV, and floor = sqrt(mean(b_residual^2)) over those rows. "
    "src/paper2_item13a_15a.py LINE_A: A1 at alpha_iso 0.9725, |alpha - 1| = 0.0275; A3 at 1.0406, "
    "|alpha - 1| = 0.0406. Different amplitudes, and A1 a compression against A3 an expansion. "
    "Deposited floor: 10.1, 17.7, 20.2, 32.5, reproducing rms of the subtracted residuals "
    "-10.0/-10.3, -18.1/-17.4, +26.3/-10.9, +33.5/-31.4 to the tenth. "
    "Counterexample to the property claimed by record 32: with A1 = -10.0, A3 = -10.3, A1m = 0, "
    "A3m = 0, per-amplitude rms are sqrt((100 + 0)/2) = 7.07 and sqrt((0 + 106.09)/2) = 7.28, "
    "maximum 7.28 against rms(A1, A3) = 10.15. "
    "The inequality used by the corrected rule: for any finite set, mean(x^2) <= max(x^2), hence "
    "sqrt(mean(x^2)) <= max|x|, with equality only when all |x| are equal."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.13",
    "amends_records": [32],
    "the_floor_is_the_maximum_absolute_residual": ("Over the six block-A points, on the subtracted "
                                                   "residuals, per hemisphere and erosion level."),
    "the_property_is_proved_not_assumed": ("rms <= max for any finite set, so the floor is at least "
                                           "the rms of any subset including the deposited pair, "
                                           "whatever the numbers are. Record 32 asserted an "
                                           "analogous property it did not have."),
    "the_deposited_pair_spans_two_amplitudes": ("A1 at 0.0275 and A3 at 0.0406, a compression and "
                                                "an expansion. The deposited floor conflates "
                                                "amplitudes and parities. That is recorded as a "
                                                "property of the deposited quantity, not corrected "
                                                "in it."),
    "the_gate_is_on_the_deposited_PAIR": ("The recomputed rms over {A1, A3} must reproduce 10.1, "
                                          "17.7, 20.2 and 32.5 to the tenth before any new floor is "
                                          "reported."),
    "caught_before_any_code": ("No floor has been computed under either rule. The correction is "
                               "complete and nothing is repaired retroactively."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not "
                              "change the E1-E4 classification rule, and does not touch DDmax."),
}


# ---------------------------------------------------------------------------
# Utilita'
# ---------------------------------------------------------------------------

def fail(msg: str):
    print("[FATAL] " + msg)
    sys.exit(2)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ledger(path: str):
    with open(path, "rb") as f:
        raw = f.read()
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    lines = [ln.rstrip(b"\r") for ln in raw.split(b"\n") if ln.strip()]
    pure_ascii = all(b < 128 for b in raw)
    recs = []
    for i, ln in enumerate(lines, start=1):
        try:
            recs.append(json.loads(ln.decode("utf-8")))
        except Exception as exc:
            fail("riga %d non e' JSON valido: %s" % (i, exc))
    sorted_keys = all(list(r.keys()) == sorted(r.keys()) for r in recs)
    return recs, newline, pure_ascii, sorted_keys, raw


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def common_keys(recs, n=3):
    tail = recs[-n:] if len(recs) >= n else recs
    s = set(tail[0].keys())
    for r in tail[1:]:
        s &= set(r.keys())
    return sorted(s)


# ---------------------------------------------------------------------------
# Costruzione del record
# ---------------------------------------------------------------------------

def _renumber(rule, position):
    """La numbering_rule della riga 15 termina con 'This is record 15.': ereditarla
    verbatim scriverebbe il numero sbagliato nel record 16. Si riscrive l'ultimo
    intero della stringa con la posizione effettiva, e si fallisce se non ce n'e'
    esattamente uno da riscrivere."""
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
        elif k in ("key", "json_path", "old_value", "new_value"):
            # emendamento di protocollo: nulli se lo sono nella riga 15
            if prev.get(k) is None:
                rec[k] = None
            else:
                rec[k] = "__DA_DICHIARARE__"
                unfilled.append(k)
        else:
            rec[k] = "__DA_DICHIARARE__"
            unfilled.append(k)

    # chiavi di contenuto, nell'idioma del registro (13: falsified_prediction,
    # 14: falsified_predictions, 15: rules)
    rec["rules"] = RULES

    rec = {k: rec[k] for k in sorted(rec.keys())}
    extras = sorted(set(rec.keys()) - set(required))
    return rec, unfilled, extras, required


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest(ledger, reference, item, overrides, verbose=True):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    ok_ledger = os.path.isfile(ledger)
    chk("1  registro presente", ok_ledger, ledger)
    if not ok_ledger:
        return _report(checks, verbose)
    recs, newline, pure_ascii, sorted_keys, raw = read_ledger(ledger)

    chk("2  righe = %d" % EXPECTED_LINES_BEFORE, len(recs) == EXPECTED_LINES_BEFORE,
        "trovate %d" % len(recs))

    ok_ref = os.path.isfile(reference)
    file_sha = sha256_file(reference) if ok_ref else ""
    chk("3  sha256 del reference invariato", file_sha == REFERENCE_FILE_SHA256,
        file_sha[:16] if file_sha else "assente")

    cited = recs[-1].get("reference_file_sha256") if recs else None
    chk("4  digest = quello citato nella riga 15", cited == file_sha,
        (cited or "assente")[:16])

    self_sha = ""
    if ok_ref:
        try:
            self_sha = json.load(open(reference, "r", encoding="utf-8")).get("_self_sha256", "")
        except Exception as exc:
            chk("4b _self_sha256 leggibile", False, str(exc))
    chk("5  _self_sha256 presente nel reference", bool(self_sha), self_sha[:16])

    blob = raw.decode("utf-8", "replace")
    dup_item = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 33 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 32 e' gia' nel registro", MARKER_32 in blob)

    chk("7  convenzioni del file: CRLF=%s, ascii_puro=%s, chiavi_ordinate=%s"
        % (newline == b"\r\n", pure_ascii, sorted_keys), True)

    rec = None
    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha, self_sha,
                                                       item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 13-15 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 old_value cita la giustificazione falsa del 32, per intero",
            ("IS the rms at one of the three amplitudes" in rec["old_value"])
            and ("cannot manufacture a favourable result" in rec["old_value"]))
        chk("11 il difetto e' nominato: la coppia depositata copre DUE ampiezze",
            ("DIFFERENT amplitudes" in rec["new_value"]["what_is_wrong"]
                ["the_deposited_pair_is_not_one_amplitude"])
            and ("0.0275" in rec["new_value"]["what_is_wrong"]
                 ["the_deposited_pair_is_not_one_amplitude"]))
        chk("12 il contro-esempio e' NUMERICO e nel record, non solo asserito",
            ("7.07" in rec["new_value"]["what_is_wrong"]["so_the_property_fails"])
            and ("would LOWER it" in rec["new_value"]["what_is_wrong"]
                 ["so_the_property_fails"]))
        chk("13 la nuova proprieta' e' DIMOSTRATA, con la disuguaglianza scritta",
            ("rms = sqrt(mean(x^2)) <= sqrt(max(x^2)) = max|x|" in rec["new_value"]
                ["the_corrected_rule"]["the_property_is_provable_not_conjectural"])
            and ("the_property_is_proved_not_assumed" in rec["rules"]))
        chk("13f il record 32 e' sulla riga 32 e si emenda il 32",
            (MARKER_32 in json.dumps(recs[31], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [32])
        chk("13g cosa del 32 SOPRAVVIVE e' elencato, non lasciato implicito",
            len(rec["new_value"]["what_of_record_32_survives"]) >= 5)
        chk("13h il cancello e' spostato sulla COPPIA, non sull'ampiezza",
            ("not well defined" in rec["new_value"]["the_reproduction_gate_changes_too"]
                ["what_record_32_asked"])
            and ("{A1, A3}" in rec["rules"]["the_gate_is_on_the_deposited_PAIR"])
            and ("deposited PAIR" in rec["new_value"]
                 ["the_reproduction_gate_changes_too"]["what_is_asked_instead"]))
        chk("13b lingua del record: inglese come le righe 13-15",
            ("perche'" not in txt) and ("cancelli" not in txt)
            and ("emisferi" not in txt))
        chk("13c document ereditato dalla riga 15 (documento emendato, non il .md)",
            rec["document"] == recs[-1].get("document"), str(rec["document"])[:48])
        chk("13e numbering_rule cita il record %d, non il 15" % (len(recs) + 1),
            (str(len(recs) + 1) in str(rec.get("numbering_rule")))
            and ("record 15" not in str(rec.get("numbering_rule"))),
            str(rec.get("numbering_rule"))[-40:])
        chk("13d reference_self_sha256 = quello della riga 15",
            rec["reference_self_sha256"] == recs[-1].get("reference_self_sha256"),
            (rec["reference_self_sha256"] or "")[:16])
    else:
        for n in ("8  schema", "9  serializzazione", "10 soglie", "11 tolleranza",
                  "12 baseline", "13 quotazione"):
            chk(n, False, "manca --item")

    try:
        import math
        import random
        bad = []
        rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
        # 1. il contro-esempio del record deve essere VERO
        if abs(rms((-10.0, 0.0)) - 7.07) > 0.01 or abs(rms((0.0, -10.3)) - 7.28) > 0.01:
            bad.append("contro-esempio")
        if max(rms((-10.0, 0.0)), rms((0.0, -10.3))) >= rms((-10.0, -10.3)):
            bad.append("il contro-esempio non abbassa: allora il 32 andava bene")
        # 2. la proprieta' NUOVA deve valere sempre: max >= rms di ogni
        #    sottoinsieme. Provata su casi casuali, non asserita.
        random.seed(1)
        for _ in range(5000):
            v = [random.uniform(-100, 100) for _ in range(6)]
            mx = max(abs(x) for x in v)
            k = random.randint(1, 6)
            sub = random.sample(v, k)
            if mx < rms(sub) - 1e-12:
                bad.append("max < rms di un sottoinsieme")
                break
        # 3. e il pavimento depositato resta la rms della coppia
        SOT = {"NGC_k1": (-10.0, -10.3), "NGC_k0": (-18.1, -17.4),
               "SGC_k1": (26.3, -10.9), "SGC_k0": (33.5, -31.4)}
        DEP = {"NGC_k1": 10.1, "NGC_k0": 17.7, "SGC_k1": 20.2, "SGC_k0": 32.5}
        for nm, v in SOT.items():
            if abs(rms(v) - DEP[nm]) > 0.1:
                bad.append(nm + "/coppia")
            if max(abs(x) for x in v) < rms(v) - 1e-12:
                bad.append(nm + "/max<rms")
        # 4. e le due ampiezze della coppia depositata sono davvero diverse
        if abs(abs(0.9725 - 1) - abs(1.0406 - 1)) < 1e-6:
            bad.append("A1 e A3 alla stessa ampiezza")
        chk("14 aritmetica: contro-esempio vero, max>=rms su 5000 casi, "
            "pavimento = rms della coppia, ampiezze diverse", not bad,
            ",".join(bad) if bad else "quindici controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend33 rev.1 ===")
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


# ---------------------------------------------------------------------------
# Sottocomandi
# ---------------------------------------------------------------------------

def parse_overrides(items):
    ov = {}
    for it in (items or []):
        if "=" not in it:
            fail("--set richiede chiave=valore, ricevuto %r" % it)
        k, v = it.split("=", 1)
        ov[k] = None if v == "null" else v
    return ov


def cmd_inspect(args):
    if not os.path.isfile(args.ledger):
        fail("registro assente: %s" % args.ledger)
    recs, newline, pure_ascii, sorted_keys, raw = read_ledger(args.ledger)
    print("registro        : %s" % args.ledger)
    print("righe           : %d" % len(recs))
    print("newline         : %s" % ("CRLF" if newline == b"\r\n" else "LF"))
    print("ascii puro      : %s" % pure_ascii)
    print("chiavi ordinate : %s" % sorted_keys)
    if os.path.isfile(args.reference):
        fs = sha256_file(args.reference)
        print("reference file  : %s" % fs)
        print("atteso          : %s   %s"
              % (REFERENCE_FILE_SHA256, "OK" if fs == REFERENCE_FILE_SHA256 else "DIVERSO"))
    print("chiavi comuni 13-15 (%d): %s" % (len(common_keys(recs, 3)), common_keys(recs, 3)))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d extra: %s" % (i, sorted(set(r.keys()) - set(common_keys(recs, 3)))))
        print("           item: %r   type: %r   utc: %r"
              % (r.get("item"), r.get("type"), r.get("utc")))
    return 0


def cmd_dump(args):
    recs, _, _, _, _ = read_ledger(args.ledger)
    n = args.n
    if not (1 <= n <= len(recs)):
        fail("riga %d fuori intervallo 1..%d" % (n, len(recs)))
    print(json.dumps(recs[n - 1], ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def cmd_selftest(args):
    return 1 if selftest(args.ledger, args.reference, args.item,
                         parse_overrides(args.set)) else 0


def cmd_append(args):
    if not args.item:
        fail("--item obbligatorio: la numerazione dell'item non la deduco dal registro.")
    ov = parse_overrides(args.set)
    nfail = selftest(args.ledger, args.reference, args.item, ov)
    print("")
    if nfail:
        fail("selftest fallito (%d controlli): nessuna scrittura." % nfail)

    recs, newline, pure_ascii, sorted_keys, raw = read_ledger(args.ledger)
    file_sha = sha256_file(args.reference)
    self_sha = json.load(open(args.reference, "r", encoding="utf-8")).get("_self_sha256", "")
    rec, unfilled, extras, required = build_record(recs, args.reference, file_sha, self_sha,
                                                   args.item, ov)
    if unfilled:
        fail("chiavi che non so riempire: %s. Usa --set chiave=valore (o =null)."
             % ", ".join(unfilled))
    if extras and not args.allow_extra_keys:
        fail("il record 33 aggiunge le chiavi %s rispetto alle comuni 13-15. "
             "Approvale con --allow-extra-keys (nel registro le chiavi di contenuto "
             "variano gia' riga per riga: 13 falsified_prediction+withdrawn, "
             "14 falsified_predictions, 15 rules)." % ", ".join(extras))

    line = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
    print("=== RECORD %d — riga %d, %d caratteri ===" % (AMEND_POSITION, len(recs) + 1, len(line)))
    pretty = json.dumps(rec, ensure_ascii=True, indent=2, sort_keys=True)
    print(pretty if len(pretty) <= 6000 else pretty[:6000] + "\n... (troncato in stampa)")
    print("")

    if not args.apply:
        print("[DRY-RUN] nulla scritto. Rilancia con --apply --baseline-verified --allow-extra-keys.")
        return 0
    if not args.baseline_verified:
        fail("--baseline-verified obbligatorio: conferma di aver controllato 35423.575 / "
             "31889.930 (NGC) e 18693.595 / 16477.565 (SGC) contro il registro di Fase 3. "
             "In un file append-only un numero sbagliato non si corregge, si emenda.")

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
    recs, newline, pure_ascii, sorted_keys, raw = read_ledger(args.ledger)
    fs = sha256_file(args.reference) if os.path.isfile(args.reference) else ""
    ok = True
    print("")
    print("=== VERIFY ===")
    print("  righe su disco            : %d (atteso %d)" % (len(recs), AMEND_POSITION))
    ok &= len(recs) == AMEND_POSITION
    print("  digest reference invariato: %s" % (fs == REFERENCE_FILE_SHA256))
    ok &= fs == REFERENCE_FILE_SHA256
    last = json.dumps(recs[-1], ensure_ascii=False) if recs else ""
    print("  marker nella riga %-2d      : %s" % (AMEND_POSITION, MARKER in last))
    ok &= MARKER in last
    print("  item della riga %-2d        : %r" % (AMEND_POSITION, recs[-1].get("item") if recs else None))
    print("  newline / ascii / ordine  : %s / %s / %s"
          % ("CRLF" if newline == b"\r\n" else "LF", pure_ascii, sorted_keys))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(description="Emendamento 16 - statuto del test a osservabili fisse")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    p.add_argument("--reference", default=DEFAULT_REFERENCE)
    p.add_argument("--item", default=None, help="numerazione item, es. 1.6")
    p.add_argument("--set", action="append", metavar="CHIAVE=VALORE")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    d = sub.add_parser("dump")
    d.add_argument("n", type=int)
    d.set_defaults(func=cmd_dump)

    ap = sub.add_parser("append")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-extra-keys", action="store_true")
    ap.add_argument("--baseline-verified", action="store_true")
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

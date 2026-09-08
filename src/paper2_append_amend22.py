#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend22.py  (rev. 1) — Emendamento 22: il valore sbagliato di D5b
era un baseline gia' dichiarato superseded.

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

AMEND_POSITION = 22                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 21

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

MARKER = "emendamento-22-valore-superseded-rientrato"
MARKER_21 = "emendamento-21-rettifica-valori-d5b"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE, salvo la citazione verbatim della voce 2.1-E)
# ---------------------------------------------------------------------------

KEY = "d5b_wrong_value_traced_to_a_superseded_baseline"

JSON_PATH = ("amendments record 21 (new_value.provenance_of_the_error; evidence); "
             "checklist item 2.1-E (M26 frozen_reference.mock_baseline, superseded)")

OLD_VALUE = (
    "Record 21 attributes the two wrong D5b values to transcription: 'The four numbers were taken "
    "from a session handover document, not from the register produced by paper2_due_lati.py. No "
    "file on disk carries 18693.595 or 16477.565.' It adopts the rule that a value entering a gate "
    "is read from the register and never transcribed."
)

NEW_VALUE = {
    "the_real_provenance": {
        "what_18693595_is": ("It is the SGC half of M26's frozen_reference.mock_baseline, "
                             "35467.15 / 18693.595. Checklist item 2.1-E, closed on 27 Aug 2026, "
                             "declares that baseline SUPERSEDED on the ground of a 0.10 sigma "
                             "discrepancy WITH OPPOSITE SIGN IN THE TWO HEMISPHERES, identified "
                             "there as the signature of the path-collision defect, and places it "
                             "outside the verdict, quoted for the record."),
        "so_the_error_is_not_transcription": ("The number was not merely copied from a summary: it "
                             "is a value this programme had already identified as contaminated, "
                             "declared superseded, and explicitly placed outside the verdict four "
                             "days earlier. It was then re-admitted as the reference of a blocking "
                             "gate."),
        "the_defect_it_carries": ("The contamination is the path-collision defect documented in "
                                  "Paper 1 section 2.5, in which the first 200 records of the "
                                  "ensemble had been overwritten by a run with a different HOD. It "
                                  "is the same defect the referee cites in his section 3.7 as the "
                                  "reason to ask which 200 mocks are used."),
        "ngc_was_unaffected_and_that_is_the_signature": (
            "The superseded M26 baseline is 35467.15 in NGC, which is NOT the value recorded in "
            "D5b: there the figure was 35423.575, the correct one. Only SGC carried the "
            "contaminated number. That is precisely the opposite-sign-between-hemispheres pattern "
            "that item 2.1-E used to identify the defect, reappearing in the error itself."),
    },
    "corrections_to_record_21": {
        "provenance_of_the_error": ("Record 21's account is true but incomplete. The proximate "
                                    "route was a handover document; the ULTIMATE source is the "
                                    "superseded M26 baseline. The two are different failures and "
                                    "the second is the serious one."),
        "evidence_statement": ("Record 21 states that no file on disk carries 18693.595. That "
                               "remains true of the results tree. The number IS present in "
                               "checklist_paper2.md, at item 2.1-E, where it is labelled "
                               "superseded. The record's search was too narrow."),
        "what_is_not_corrected": ("The four D5b values restated in record 21 - 35423.575, "
                                  "31889.925, 18694.420, 16477.950 - are correct and are not "
                                  "touched. This record corrects the ACCOUNT of how the wrong ones "
                                  "got there, not the right ones."),
    },
    "rule_strengthened": {
        "record_21_rule_was_insufficient": ("'Read from the register, never transcribe' would not "
                                            "have prevented this. The wrong value did come from a "
                                            "document, but its defect was that it had been "
                                            "DECLARED SUPERSEDED, and a rule about transcription "
                                            "says nothing about that."),
        "rule_added": ("A value that any record, gate or checklist entry has declared SUPERSEDED, "
                       "WITHDRAWN or CONTAMINATED does not re-enter the programme by any route, "
                       "including as the reference of a new gate. Before a value becomes a gate "
                       "reference, it is searched for in the amendments ledger and in the "
                       "checklist, not only in the results tree."),
        "why_this_is_checkable": ("Unlike 'read from the register', this rule is mechanical: the "
                                  "superseded values are written down, and a search is a search. "
                                  "It can be enforced by a script rather than by care."),
    },
    "scope": {
        "no_run_has_used_d5b": ("Treatment (B) has still not been executed. Neither the wrong "
                                "values nor the wrong account has entered any measurement."),
        "gate_d5b_unchanged": ("D5b stands as restated in record 21: zero tolerance, blocking, four "
                               "values read from due_lati.jsonl."),
        "m26_is_not_reopened": ("Item 2.1-E already superseded the M26 baseline on 27 Aug and that "
                                "closure is not touched. This record concerns only the re-entry of "
                                "a superseded number into a Paper 2 gate."),
    },
}

REASON = (
    "Record 21 gives the wrong account of its own error, and the right account carries a rule that "
    "record 21 does not. "
    "WHAT WAS ACTUALLY DONE. The value 18693.595 written into gate D5b is the SGC half of M26's "
    "frozen_reference.mock_baseline, 35467.15 / 18693.595. Checklist item 2.1-E, closed on 27 "
    "August 2026, declares that baseline SUPERSEDED because of a 0.10 sigma discrepancy with "
    "OPPOSITE SIGN IN THE TWO HEMISPHERES, identified there as the signature of the path-collision "
    "defect of Paper 1 section 2.5, and places it outside the verdict. Four days later that number "
    "was re-admitted as the reference of a blocking gate. This is not transcription from a summary, "
    "which is what record 21 says: it is the re-entry of a value the programme had already "
    "identified as contaminated. "
    "THE SIGNATURE REAPPEARS IN THE ERROR. The superseded NGC figure is 35467.15, which is NOT what "
    "D5b recorded; there the value was 35423.575, the correct one. Only SGC carried the "
    "contaminated number - the same one-hemisphere-only pattern that item 2.1-E used to detect the "
    "defect in the first place. "
    "THE RULE OF RECORD 21 IS INSUFFICIENT. 'Read from the register, never transcribe' would not "
    "have caught this, because the failure was not the copying but the status of what was copied. "
    "Added here: a value declared SUPERSEDED, WITHDRAWN or CONTAMINATED does not re-enter by any "
    "route, and before a value becomes a gate reference it is searched for in the ledger and in the "
    "checklist, not only in the results tree. That rule is mechanical and can be enforced by a "
    "script. "
    "The four corrected D5b values are not touched. Treatment (B) has still not run."
)

EVIDENCE = (
    "checklist_paper2.md, item 2.1-E, closed 27 Aug 2026 with src/paper2_gate21.py and "
    "results/paper2/gate21.jsonl. Verbatim, in the original Italian: 'Riferimento operativo = "
    "Paper 1. M26 (frozen_reference.mock_baseline 35 467.15 / 18 693.595) e' superseded: scarto "
    "0.10 sigma con segno opposto nei due emisferi, firma della collisione di percorsi. Fuori dal "
    "verdetto, citato per memoria.' The same entry records the operative reference as the Paper 1 "
    "values, 35436.686 / 312.9891651683112 and 18712.9675 / 197.7873817207103, at rel 0.000e+00, "
    "confirmed by three independent routes. "
    "Record 16, new_value.gates.D5b.values, SGC: 18693.595 - identical to the superseded M26 SGC "
    "baseline. NGC: 35423.575, which differs from the superseded M26 NGC baseline of 35467.15 and "
    "matches the register. "
    "results/paper2/due_lati.jsonl, two_sides[FID].mock_mean: 18694.420 (SGC k=0), the correct "
    "value, 0.825 above the superseded one. "
    "Paper 1 section 2.5 documents the path-collision defect in which the first 200 records of the "
    "ensemble were overwritten by a run with a different HOD, discovered only because someone "
    "compared the dispersions."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, items 2.1-E and 1.4b",
    "amends_records": [21],
    "d5b_values_unchanged": ("The four values restated in record 21 are correct and stand. Only the "
                             "account of the error and the rule drawn from it are corrected."),
    "superseded_values_do_not_return": ("A value declared SUPERSEDED, WITHDRAWN or CONTAMINATED by "
                                        "any record, gate or checklist entry does not re-enter the "
                                        "programme by any route, including as the reference of a "
                                        "new gate."),
    "search_before_a_value_becomes_a_gate": ("Before a value becomes a gate reference it is "
                                             "searched for in the amendments ledger and in the "
                                             "checklist, not only in the results tree. Record 21's "
                                             "search covered results/paper2 alone and therefore "
                                             "reported that the number appeared nowhere."),
    "the_defect_detected_itself_twice": ("The opposite-sign-between-hemispheres pattern identified "
                                         "the path-collision defect in item 2.1-E, and the same "
                                         "pattern - NGC correct, SGC contaminated - marks its "
                                         "re-entry here."),
    "m26_closure_not_reopened": ("Item 2.1-E stands. This record concerns the re-entry of a "
                                 "superseded number into a Paper 2 gate, not the supersession "
                                 "itself."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3 or item 2.1-E, "
                              "does not change the E1-E4 verdict, and does not alter the corrected "
                              "D5b values."),
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
    chk("6  idempotenza (marker 22 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 21 e' gia' nel registro", MARKER_21 in blob)

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
        chk("10 old_value cita il racconto sbagliato del record 21",
            ("never transcribed" in rec["old_value"])
            and ("No file on disk carries 18693.595" in rec["old_value"]))
        chk("11 la voce 2.1-E e' citata VERBATIM, con data e motivazione",
            ("2.1-E" in rec["evidence"]) and ("27 Aug 2026" in rec["evidence"])
            and ("segno opposto nei due emisferi" in rec["evidence"]))
        chk("12 i quattro valori corretti NON sono toccati",
            ("are correct and stand" in rec["rules"]["d5b_values_unchanged"])
            and ("not touched" in rec["new_value"]["corrections_to_record_21"]
                 ["what_is_not_corrected"]))
        chk("13 la regola del record 21 e' dichiarata INSUFFICIENTE, con la ragione",
            ("would not have prevented this" in rec["new_value"]["rule_strengthened"]
                ["record_21_rule_was_insufficient"])
            and ("DECLARED SUPERSEDED" in rec["new_value"]["rule_strengthened"]
                 ["record_21_rule_was_insufficient"]))
        chk("13f il record 21 e' sulla riga 21 e si emenda il 21",
            (MARKER_21 in json.dumps(recs[20], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [21])
        chk("13g la nuova regola e' meccanica, non di diligenza",
            ("does not re-enter" in rec["rules"]["superseded_values_do_not_return"])
            and ("enforced by a script" in rec["new_value"]["rule_strengthened"]
                 ["why_this_is_checkable"]))
        chk("13h la firma NGC-corretto / SGC-contaminato e' registrata",
            ("35467.15" in rec["new_value"]["the_real_provenance"]
                ["ngc_was_unaffected_and_that_is_the_signature"])
            and ("opposite-sign" in rec["rules"]["the_defect_detected_itself_twice"]))
        # La voce 2.1-E si cita VERBATIM, in italiano: e' una citazione, non
        # una svista di lingua. Quel tratto si esclude dal controllo.
        _a, _b = "Riferimento operativo", "citato per memoria."
        _nq = txt if _a not in txt else txt[:txt.index(_a)] + txt[txt.index(_b) + len(_b):]
        chk("13b lingua: inglese fuori dalla citazione verbatim",
            ("perche'" not in _nq) and ("cancelli" not in _nq)
            and ("emisferi" not in _nq) and (_a in txt))
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
        bad = []
        M26_SUPERSEDED = {"NGC": 35467.15, "SGC": 18693.595}
        D5B_AS_WRITTEN = {"NGC": 35423.575, "SGC": 18693.595}
        REGISTER = {"NGC": 35423.575, "SGC": 18694.420}
        if D5B_AS_WRITTEN["SGC"] != M26_SUPERSEDED["SGC"]:
            bad.append("SGC non coincide col superseded")
        if D5B_AS_WRITTEN["NGC"] == M26_SUPERSEDED["NGC"]:
            bad.append("NGC coincide col superseded")
        if D5B_AS_WRITTEN["NGC"] != REGISTER["NGC"]:
            bad.append("NGC non coincide col registro")
        if abs((REGISTER["SGC"] - D5B_AS_WRITTEN["SGC"]) - 0.825) > 5e-4:
            bad.append("scarto SGC")
        chk("14 identita': SGC = superseded, NGC = registro, scarto +0.825",
            not bad, ",".join(bad) if bad else "quattro identita' verificate")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend22 rev.1 ===")
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
        fail("il record 22 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

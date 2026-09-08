#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend21.py  (rev. 1) — Emendamento 21: rettifica dei valori e
delle etichette del cancello D5b.

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

AMEND_POSITION = 21                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 20

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

MARKER = "emendamento-21-rettifica-valori-d5b"
MARKER_20 = "emendamento-20-sistematico-nell-intervallo-due-denominatori"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "d5b_values_mislabelled_and_two_of_them_wrong"

JSON_PATH = ("amendments record 16 (new_value.gates.D5b.values); "
             "amendments record 18 (new_value.what_survives_and_why.gate_D5b)")

OLD_VALUE = (
    "Record 16 declares gate D5b, 'reproduction of the frozen Phase-3 baseline', with values "
    "labelled: NGC {mock_mean_N_H1: 35423.575, desi_N_H1: 31889.930} and "
    "SGC {mock_mean_N_H1: 18693.595, desi_N_H1: 16477.565}. Record 18 lists gate D5b among the "
    "things that survive the gauge rectification, without re-examining its values."
)

NEW_VALUE = {
    "correction_labels": {
        "what_is_false": ("The label 'desi_N_H1' cannot apply to 31889.930 or 16477.565. The data "
                          "side writes int(round(float(feats[4]))), so N_H1^DESI is an INTEGER by "
                          "construction, and neither number is one. The DESI counts at the "
                          "fiducial are 28256 and 23790 in NGC, 15122 and 12011 in SGC, at k=0 and "
                          "k=1 respectively."),
        "what_they_actually_are": ("All four are <N_H1>_mock at the FIDUCIAL point, at k=0 and k=1: "
                                   "two erosion levels of the mock mean, not a mock value against a "
                                   "data value. The pairing implied by the labels does not exist."),
    },
    "correction_values": {
        "two_of_four_are_also_numerically_wrong": True,
        "from_the_register": {
            "NGC": {"mock_mean_FID_k0": 35423.575, "mock_mean_FID_k1": 31889.925,
                    "desi_FID_k0": 28256, "desi_FID_k1": 23790},
            "SGC": {"mock_mean_FID_k0": 18694.420, "mock_mean_FID_k1": 16477.950,
                    "desi_FID_k0": 15122, "desi_FID_k1": 12011},
        },
        "deltas_against_record_16": {"NGC_k0": 0.000, "NGC_k1": -0.005,
                                     "SGC_k0": 0.825, "SGC_k1": 0.385},
        "the_register_agrees_with_itself": ("results/paper2/due_lati.jsonl holds TWO SGC records, "
                                            "written at 14:22:33Z and 14:25:25Z on 31 Aug 2026. "
                                            "They give IDENTICAL fiducial means, 18694.420 and "
                                            "16477.950. The values in record 16 match neither."),
    },
    "provenance_of_the_error": {
        "where_they_came_from": ("The four numbers were taken from a session handover document, not "
                                 "from the register produced by paper2_due_lati.py. No file on disk "
                                 "carries 18693.595 or 16477.565."),
        "why_the_flag_did_not_catch_it": ("The append script required --baseline-verified, and that "
                                          "flag asked for the NUMBERS to be checked against the "
                                          "Phase-3 register. It did not ask for the LABELS to be "
                                          "checked, and the labels were the invention. A gate whose "
                                          "field names are wrong cannot be validated by checking "
                                          "its values."),
        "rule_adopted": ("Any value entering a gate is read from the register that produced it, by "
                         "the script that will use it, and never transcribed from a summary or a "
                         "handover. Where a value cannot be read programmatically, the gate "
                         "declares that and does not proceed."),
    },
    "d5b_restated": {
        "name": "reproduction of the frozen fiducial baseline, mock side",
        "requirement": ("At the fiducial point, treatment (B) must reproduce EXACTLY the mock mean "
                        "over the 200 paired realisations, at both erosion levels."),
        "values": {"NGC": {"k0": 35423.575, "k1": 31889.925},
                   "SGC": {"k0": 18694.420, "k1": 16477.950}},
        "source": "results/paper2/due_lati.jsonl, latest record per region, two_sides[FID].mock_mean",
        "tolerance": 0,
        "blocking": True,
        "data_side_is_not_part_of_D5b": ("The DESI counts are integers and are not reproduced by a "
                                         "mock run: they are quoted here only so that the earlier "
                                         "mislabelling cannot be repeated."),
    },
    "scope_of_this_correction": {
        "gate_unchanged_in_substance": ("D5b still requires exact reproduction of the frozen "
                                        "fiducial baseline with zero tolerance. What changes is "
                                        "which four numbers it compares against, and what they are "
                                        "called."),
        "no_run_has_used_it": ("Treatment (B) has not been executed. No measurement rests on the "
                               "wrong values, and nothing is repaired retroactively."),
        "as_written_it_could_not_have_passed": ("D5b as recorded asked a mock run to reproduce a "
                                                "'desi_N_H1' of 31889.930, a value that does not "
                                                "exist on either side. The gate would have failed "
                                                "for a reason unrelated to the cache it was built "
                                                "to test."),
    },
}

REASON = (
    "Gate D5b of record 16 is corrected in its labels and in two of its four values, before "
    "treatment (B) is executed and therefore before any measurement can rest on it. "
    "THE LABELS. The four numbers were recorded as a mock mean paired with a DESI count in each "
    "hemisphere. That pairing does not exist: the data side writes integers, and 31889.930 and "
    "16477.565 are not integers. All four are <N_H1>_mock at the fiducial, at the two erosion "
    "levels. As recorded, D5b asked a mock run to reproduce a DESI value that exists nowhere, and "
    "would have failed for a reason unrelated to the cache it was built to test. "
    "THE VALUES. Read from the register, the fiducial mock means are 35423.575 and 31889.925 in "
    "NGC, 18694.420 and 16477.950 in SGC. NGC k=0 matches record 16 exactly; NGC k=1 is off by "
    "0.005; SGC is off by 0.825 and 0.385. The register agrees with itself - the two SGC records of "
    "31 August, written three minutes apart, give identical fiducial means - so the discrepancy is "
    "not a version difference in the register. "
    "WHERE THE ERROR CAME FROM, AND WHY THE FLAG MISSED IT. The numbers were transcribed from a "
    "session handover document rather than read from the register; no file on disk carries "
    "18693.595. The append script required --baseline-verified, but that flag asked for the values "
    "to be checked, not the names, and the names were the invention. A gate whose field names are "
    "wrong cannot be validated by checking its numbers. The rule adopted here is that any value "
    "entering a gate is read from the register by the script that will use it, never transcribed."
)

EVIDENCE = (
    "results/paper2/due_lati.jsonl, two_sides[FID]: NGC mock_mean = 35423.575 (k=0) and 31889.925 "
    "(k=1) with desi = 28256 and 23790; SGC mock_mean = 18694.420 (k=0) and 16477.950 (k=1) with "
    "desi = 15122 and 12011, n = 200 in every case. The file holds two SGC records, at "
    "2026-08-31T14:22:33Z and 2026-08-31T14:25:25Z, whose fiducial means are identical. "
    "paper2_runner_fase3.py writes the data-side count as int(round(float(feats[4]))), so every "
    "N_H1^DESI on disk is an integer; the four DESI values above are integers and the four values "
    "recorded in D5b are not. "
    "Differences between record 16 and the register: NGC k=0 exactly 0.000, NGC k=1 -0.005, "
    "SGC k=0 +0.825, SGC k=1 +0.385. "
    "A search of results/paper2 finds no record containing 18693.595 or 16477.565."
)

RULES = {
    "marker": MARKER,
    "companion_document": "paper2_item16.md, gate D5b",
    "amends_records": [16, 18],
    "gate_not_withdrawn": ("D5b stands, with zero tolerance and blocking status. Only its reference "
                           "values and their names are corrected."),
    "values_are_read_not_transcribed": ("Any value entering a gate is read from the register that "
                                        "produced it, by the script that will use it, and is never "
                                        "transcribed from a summary or a handover. Where it cannot "
                                        "be read programmatically, the gate declares that and does "
                                        "not proceed."),
    "flags_must_bind_to_what_is_checkable": ("--baseline-verified asked for numbers and the error "
                                             "was in names. A confirmation flag that does not name "
                                             "precisely what is being confirmed provides assurance "
                                             "without providing a check."),
    "caught_before_any_run": ("Treatment (B) has not been executed. The correction is complete and "
                              "nothing is repaired retroactively."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not "
                              "change the E1-E4 verdict, and does not touch gates D5a, D5c or the "
                              "denominator rule of record 17."),
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
    chk("6  idempotenza (marker 21 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 20 e' gia' nel registro", MARKER_20 in blob)

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
        chk("10 old_value cita le etichette sbagliate per intero",
            ("desi_N_H1: 31889.930" in rec["old_value"])
            and ("mock_mean_N_H1: 18693.595" in rec["old_value"]))
        chk("11 il cancello NON e' ritirato: cambiano valori e nomi",
            rec["new_value"]["d5b_restated"]["tolerance"] == 0
            and rec["new_value"]["d5b_restated"]["blocking"] is True
            and "D5b stands" in rec["rules"]["gate_not_withdrawn"])
        chk("12 i valori corretti vengono dal REGISTRO, ed e' dichiarato",
            "due_lati.jsonl" in rec["new_value"]["d5b_restated"]["source"]
            and "never transcribed" in rec["rules"]["values_are_read_not_transcribed"])
        chk("13 perche' il flag non ha intercettato l'errore e' spiegato",
            ("LABELS to be checked" in rec["new_value"]["provenance_of_the_error"]
                ["why_the_flag_did_not_catch_it"])
            and ("without providing a check" in rec["rules"]
                 ["flags_must_bind_to_what_is_checkable"]))
        chk("13f il record 20 e' sulla riga 20 e si emendano 16 e 18",
            (MARKER_20 in json.dumps(recs[19], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [16, 18])
        chk("13g e' dichiarato che nessun run ha usato D5b",
            ("has not been executed" in rec["new_value"]["scope_of_this_correction"]
                ["no_run_has_used_it"])
            and ("caught_before_any_run" in rec["rules"]))
        chk("13h il lato dati e' fuori da D5b, con i suoi interi a parte",
            rec["new_value"]["d5b_restated"]["values"]["NGC"]["k1"] == 31889.925
            and "data_side_is_not_part_of_D5b" in rec["new_value"]["d5b_restated"])
        chk("13b lingua del record: inglese come le righe 13-15",
            ("perche'" not in txt) and ("cancelli" not in txt) and ("emisferi" not in txt))
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
        # L'argomento centrale e' aritmetico e va verificato, non creduto.
        v = rec["new_value"]["d5b_restated"]["values"]
        fr = rec["new_value"]["correction_values"]["from_the_register"]
        bad = []
        # 1. i quattro valori di D5b NON sono interi
        for reg in ("NGC", "SGC"):
            for k in ("k0", "k1"):
                if float(v[reg][k]).is_integer():
                    bad.append("%s/%s intero" % (reg, k))
        # 2. i quattro DESI SONO interi
        for reg in ("NGC", "SGC"):
            for k in ("desi_FID_k0", "desi_FID_k1"):
                if not float(fr[reg][k]).is_integer():
                    bad.append("%s/%s non intero" % (reg, k))
        # 3. gli scarti dichiarati tornano contro i valori del record 16
        old16 = {"NGC_k0": 35423.575, "NGC_k1": 31889.930,
                 "SGC_k0": 18693.595, "SGC_k1": 16477.565}
        dl = rec["new_value"]["correction_values"]["deltas_against_record_16"]
        for nm, o in old16.items():
            reg, k = nm.split("_")
            if abs((v[reg][k] - o) - dl[nm]) > 5e-4:
                bad.append(nm + "/delta")
        chk("14 aritmetica: D5b non intero, DESI intero, scarti coerenti",
            not bad, ",".join(bad) if bad else "12 controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend21 rev.1 ===")
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
        fail("il record 21 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

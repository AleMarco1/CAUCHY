#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend41.py  (rev. 1) — Emendamento 41: il budget gira ai quattro livelli.
Voce 3.9 chiusa, e un difetto silenzioso intercettato.

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

AMEND_POSITION = 41                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 40

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

MARKER = "emendamento-41-budget-a-quattro-livelli"
MARKER_40 = "emendamento-40-pavimento-sei-punti"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "the_budget_now_runs_at_k2_and_k3_and_it_describes_without_classifying"

JSON_PATH = ("src/paper2_fase3_budget.py (TERM_C, gather, cmd_run); "
             "checklist item 3.9")

OLD_VALUE = (
    "TERM_C had only the keys 0 and 1, because the carving reseed had been run before k=2 and k=3 "
    "existed, and the budget's level loop was hard-wired to (1, 0). Checklist item 3.9 records the "
    "budget at those levels as BLOCKED since 1 Sep 2026. gather also computed the data side as "
    "dkey = 'N_H1' if ki == 1 else 'N_H1_k0'."
)

NEW_VALUE = {
    "what_was_needed_and_in_what_order": [
        "the FID-only carving reseed at erosions 2 and 3 (record 26), run 4 Sep in 1.49 h + 1.48 h",
        "TERM_C extended to four levels, with a gate that k=0 and k=1 recomputed from the same "
        "register reproduce the deposited 7.69, 7.73, 6.78 and 6.29",
        "selection_channel made robust to points lacking the level, and its metadata moved out of "
        "the data dictionary",
        "gather given a per-level data source, and the block-A points filtered",
        "--levels on the budget itself",
    ],
    # Chiavi STRINGA: JSON non ha chiavi intere e le convertirebbe comunque,
    # rompendo il round-trip che il cancello di serializzazione verifica.
    "term_c_at_four_levels": {"NGC": {"k0": 7.69, "k1": 7.73, "k2": 7.00, "k3": 5.80},
                              "SGC": {"k0": 6.78, "k1": 6.29, "k2": 5.54, "k3": 4.41}},
    "the_silent_defect_that_was_caught": {
        "what": ("gather computed the data side as dkey = 'N_H1' if ki == 1 else 'N_H1_k0'. At "
                 "ki = 2 and 3 that takes the data side at k=0."),
        "why_it_is_worse_than_a_crash": ("It raises nothing. It would have produced a Delta D "
                                         "computed between a mock side at k=2 and a data side at "
                                         "k=0, and written it into the register as a measurement. "
                                         "The KeyError on the block-A points crashed the run first "
                                         "and made the code visible; without that crash the wrong "
                                         "number would have been reported."),
        "the_correction": ("The data side is read from the `ladder` field, which carries the full "
                           "erosion scale. If the level is absent the run STOPS rather than falling "
                           "back to k=0."),
    },
    "the_results": {
        "NGC": {"k1": {"floor": 32.96, "points": 6, "driver": "A1m"},
                "k0": {"floor": 51.13, "points": 6, "driver": "A1m"},
                "k2": {"floor": 39.43, "points": 2, "driver": "A3"},
                "k3": {"floor": 12.10, "points": 2, "driver": "A1"}},
        "k0_and_k1_unchanged": ("32.96, 51.13, 27.51 and 34.61, identical to the run before these "
                                "four patches. The corrections touch only the choice of source and "
                                "the filtering of points, and at k=0,1 the source is the same and "
                                "nothing is filtered."),
        "the_floor_at_k2_and_k3_rests_on_TWO_points": ("A0, A1m, A3m and A0m were run on the mock "
                                                       "side at erosions 0 and 1 only, because they "
                                                       "serve the floor and the floor is computed "
                                                       "at the budget's levels. At k=2,3 the floor "
                                                       "is therefore the maximum over the two "
                                                       "DEPOSITED points and is quoted as such."),
        "an_observation_without_a_verdict": ("The floor falls with erosion: 51.13 at k=0 against "
                                             "12.10 at k=3 in NGC. It goes the same way as TERM_C, "
                                             "which falls from 7.69 to 5.80 - fewer boundary "
                                             "voxels, less artefact - but more steeply. On two "
                                             "points it is not comparable with the six of the other "
                                             "levels. No threshold was declared on it."),
    },
    "describes_without_classifying": {
        "the_rule": ("At k=2 and k=3 the analysis emits neither the E1-E4 outcome nor the section "
                     "5.4 verdict, because the deposited thresholds are calibrated on the deficit "
                     "at k=0,1. The budget there therefore produces a floor and a systematic with "
                     "no threshold to compare them against."),
        "and_the_code_says_so": ("The budget prints, at every level outside (0,1): 'Il budget a "
                                 "questo livello DESCRIVE e non CLASSIFICA'. Written into the "
                                 "output rather than left to be deduced, so that in a month these "
                                 "numbers are not read on a par with the others."),
    },
    "one_cosmetic_defect_left": {
        "what": ("At k=2,3 the gate line prints '[rms coppia depositata nan contro None]'. It is "
                 "correct in substance - there is no deposited floor at those levels, so the gate "
                 "does not apply - but printing nan and None invites reading it as a fault."),
        "what_it_should_say": ("'cancello non applicabile: nessun pavimento depositato a questo "
                               "livello'. Registered here so it is not forgotten; it changes no "
                               "number."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not change the budget at k=0 or k=1."),
}

REASON = (
    "The budget runs at all four erosion levels and checklist item 3.9, open since 1 September, is "
    "closed. "
    "WHAT IT TOOK, in order: the FID-only carving reseed at erosions 2 and 3; TERM_C extended to "
    "four levels with a gate that k=0 and k=1, recomputed from the same register and the same code, "
    "reproduce the deposited 7.69, 7.73, 6.78 and 6.29; selection_channel made robust to points "
    "lacking the level; gather given a per-level data source; and --levels on the budget. "
    "A SILENT DEFECT WAS CAUGHT ON THE WAY, and it is the part worth recording. gather computed the "
    "data side as dkey = 'N_H1' if ki == 1 else 'N_H1_k0', which at ki = 2 and 3 takes the data "
    "side at k=0. It raises nothing: it would have produced a Delta D between a mock side at k=2 and "
    "a data side at k=0 and written it into the register as a measurement. It was visible only "
    "because the block-A points crashed the run first with a KeyError. A crash is seen; that is not. "
    "The data side is now read from the `ladder` field, and if the level is absent the run STOPS "
    "rather than falling back. "
    "THE RESULTS. k=0 and k=1 are UNCHANGED - 32.96, 51.13, 27.51, 34.61 - which is what the four "
    "patches had to leave alone. At k=2 and k=3 the floor is 39.43 and 12.10 in NGC, on TWO points: "
    "the four new block-A points were run at erosions 0 and 1 only, because they serve the floor "
    "and the floor is computed at the budget's levels. It is quoted as 'maximum over the two "
    "deposited points'. "
    "AND THE BUDGET THERE DESCRIBES WITHOUT CLASSIFYING. The analysis emits no E1-E4 outcome and no "
    "section 5.4 verdict at those levels, so the floor and the systematic have no threshold to be "
    "compared against. The code prints this at every level outside (0,1), rather than leaving it to "
    "be deduced, so that in a month these numbers are not read on a par with the others."
)

EVIDENCE = (
    "Run of 4 Sep 2026. '(f) pavimento = 32.96 su 6 punti, determinato da A1m [rms coppia "
    "depositata 10.12 contro 10.1]' and 51.13, 27.51, 34.61 - identical to the run before the four "
    "patches. "
    "At k=2: '[blocco A] 4 punti saltati a k=2, senza N_H1_k2 sul lato mock: A0, A0m, A1m, A3m' "
    "then '(f) pavimento = 39.43 su 2 punti, determinato da A3' and '[k=2] Il budget a questo "
    "livello DESCRIVE e non CLASSIFICA'. At k=3: 12.10 on 2 points, driven by A1. "
    "TERM_C = {'NGC': {0: 7.69, 1: 7.73, 2: 7.00, 3: 5.80}, 'SGC': {0: 6.78, 1: 6.29, 2: 5.54, "
    "3: 4.41}}, from sd(dN)/sqrt(2)/sqrt(200) at the fiducial with sd = 153.739, 154.502, 140.018, "
    "115.980 (NGC) and 135.694, 125.758, 110.731, 88.176 (SGC). "
    "The reseed at erosions 2 and 3 ran in 1.49 h and 1.48 h, FID only, 200 realisations per "
    "hemisphere. "
    "Patches applied: paper2_termc_k23_patch, paper2_selection_channel_patch, "
    "paper2_selchan_fix_patch, paper2_gather_k23_patch, paper2_budget_levels_patch."
)

RULES = {
    "marker": MARKER,
    "companion_document": "checklist_paper2.md, item 3.9",
    "amends_records": [],
    "item_3_9_is_closed": ("The budget runs at k=0, 1, 2 and 3. Open since 1 September."),
    "the_data_side_is_read_from_the_ladder": ("Never from a flat field chosen by a conditional on "
                                              "the level. If the ladder lacks the level the run "
                                              "stops; it does not fall back to k=0."),
    "a_silent_wrong_number_is_worse_than_a_crash": ("The fallback to k=0 raised nothing and would "
                                                    "have written a Delta D between two different "
                                                    "levels into the register. It was found only "
                                                    "because an unrelated KeyError crashed the run "
                                                    "first."),
    "the_floor_at_k2_k3_is_over_two_points": ("Quoted as such. The four new block-A points have "
                                              "only erosions 0 and 1."),
    "at_k2_and_k3_the_budget_describes": ("No E1-E4 outcome and no section 5.4 verdict exist at "
                                          "those levels, so floor and systematic have no threshold. "
                                          "The code prints this at every diagnostic level."),
    "a_cosmetic_line_is_left_to_fix": ("'[rms coppia depositata nan contro None]' should read "
                                       "'cancello non applicabile: nessun pavimento depositato a "
                                       "questo livello'. It changes no number."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not change the budget at k=0 or k=1."),
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
    chk("6  idempotenza (marker 41 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 40 e' gia' nel registro", MARKER_40 in blob)

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
        chk("10 old_value cita la forma sbagliata di dkey, per intero",
            ("dkey = 'N_H1' if ki == 1 else 'N_H1_k0'" in rec["old_value"])
            and ("BLOCKED since 1 Sep" in rec["old_value"]))
        chk("11 TERM_C ha quattro livelli per emisfero",
            all(set(rec["new_value"]["term_c_at_four_levels"][r])
                == {"k0", "k1", "k2", "k3"} for r in ("NGC", "SGC")))
        chk("12 il difetto SILENZIOSO e' registrato, e perche' e' peggio di un crash",
            ("raises nothing" in rec["new_value"]["the_silent_defect_that_was_caught"]
                ["why_it_is_worse_than_a_crash"])
            and ("A crash is seen; that is not" in rec["reason"]))
        chk("13 k=0 e k=1 sono INVARIATI, ed e' quel che le patch dovevano lasciare stare",
            ("32.96, 51.13, 27.51 and 34.61" in rec["new_value"]["the_results"]
                ["k0_and_k1_unchanged"]))
        chk("13f il record 40 e' sulla riga 40",
            MARKER_40 in json.dumps(recs[39], ensure_ascii=False))
        chk("13g a k=2,3 il budget DESCRIVE, e il codice lo stampa",
            ("DESCRIVE e non CLASSIFICA" in rec["new_value"]
                ["describes_without_classifying"]["and_the_code_says_so"])
            and ("left to be deduced" in rec["new_value"]
                 ["describes_without_classifying"]["and_the_code_says_so"]))
        chk("13h il difetto cosmetico e' registrato per non dimenticarlo",
            ("nan contro None" in rec["new_value"]["one_cosmetic_defect_left"]["what"])
            and ("changes no number" in rec["rules"]["a_cosmetic_line_is_left_to_fix"]))
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
        bad = []
        T = rec["new_value"]["term_c_at_four_levels"]
        # 1. TERM_C si ricalcola dalle sd misurate, col sqrt(2)
        SD = {("NGC", 0): 153.739, ("NGC", 1): 154.502, ("NGC", 2): 140.018,
              ("NGC", 3): 115.980, ("SGC", 0): 135.694, ("SGC", 1): 125.758,
              ("SGC", 2): 110.731, ("SGC", 3): 88.176}
        for (reg, k), sd in SD.items():
            if abs(sd / math.sqrt(2) / math.sqrt(200) - T[reg]["k%d" % k]) > 0.01:
                bad.append("%s/k%d" % (reg, k))
        # 2. TERM_C decresce da k=1 in poi, in entrambi
        for reg in ("NGC", "SGC"):
            if not (T[reg]["k1"] > T[reg]["k2"] > T[reg]["k3"]):
                bad.append(reg + "/non decresce")
        # 3. il difetto silenzioso: la vecchia forma a ki=2 dava k=0
        if ("N_H1" if 2 == 1 else "N_H1_k0") != "N_H1_k0":
            bad.append("il difetto non si riproduce: la rettifica sarebbe ingiustificata")
        # 4. il pavimento a k=2,3 poggia su DUE punti, non sei
        R = rec["new_value"]["the_results"]["NGC"]
        if not (R["k2"]["points"] == 2 and R["k3"]["points"] == 2
                and R["k1"]["points"] == 6 and R["k0"]["points"] == 6):
            bad.append("conteggio punti")
        # 5. e scende con l'erosione, come TERM_C ma piu' ripido
        if not (R["k0"]["floor"] / R["k3"]["floor"]
                > T["NGC"]["k0"] / T["NGC"]["k3"]):
            bad.append("il pavimento non scende piu' ripido di TERM_C")
        chk("14 aritmetica: TERM_C dalle sd, decrescente, difetto riprodotto, "
            "due punti a k=2,3, pavimento piu' ripido di TERM_C",
            not bad, ",".join(bad) if bad else "sedici controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend41 rev.1 ===")
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
        fail("il record 41 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

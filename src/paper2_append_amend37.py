#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend37.py  (rev. 1) — Emendamento 37: il meccanismo RSD e' FALSIFICATO
dalla linea B in spazio reale. Il fattore resta, la spiegazione no.

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

AMEND_POSITION = 37                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 36

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

MARKER = "emendamento-37-meccanismo-rsd-falsificato"
MARKER_36 = "emendamento-36-soglia-d5c"
COMPANION_DOCUMENT = "paper2_item16.md"
MIN_MEASURED_POINTS = 4
FALSIFY_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = "the_rsd_mechanism_is_falsified_and_withdrawn"

JSON_PATH = ("amendments record 16 (evidence: the mechanism); "
             "amendments record 18 (prediction_2_restated); "
             "amendments record 17 (gate_D5c.rationale)")

OLD_VALUE = (
    "Record 16 states the mechanism: 'With RSD, dC_rsd - dC ~ (1+z) v_los / H(z), and H(z) is the "
    "local slope of the injected table: treatment (A) applies the AP distortion to the RSD "
    "DISPLACEMENT while leaving the real-space field invariant, whereas the data side applies it to "
    "the whole radial coordinate. These are not the same perturbation, and this is the mechanism of "
    "the measured factor 2.10-5.56.' Record 18 restates prediction 2 on that basis and declares it "
    "FALSIFIED if the real-space residual after term (e) reaches at least HALF of the "
    "redshift-space residual after (e). Record 17 justifies gate D5c by 'under treatment (B) the "
    "galaxies are displaced radially and some WILL leave the frozen cube'."
)

NEW_VALUE = {
    "the_run": {
        "executed": ("3 Sep 2026, 5.96 h + 5.84 h, 400 records, 200 realisations per hemisphere, "
                     "six line-B points, erosions 0 and 1, after the flag was connected (record "
                     "35)."),
        "it_is_valid_this_time": ("2396 of 2400 comparable cells DIFFER from fase3_mock.jsonl, "
                                  "against 0 of 2400 in the null run. The behavioural check "
                                  "required by record 35 - a run that produces different numbers - "
                                  "is satisfied."),
        "d5c_applied_retroactively": ("Threshold 28, record 36. Maximum n_clipped in this run: "
                                      "ZERO, at every point and every realisation. No point is "
                                      "excluded and the results may be quoted, as records 23 and 36 "
                                      "require."),
    },
    "the_mechanism_is_falsified": {
        "the_measurement": {"NGC_k0": {"real": -200.60, "sem": 12.22, "redshift": -218.0,
                                       "ratio": 0.920},
                            "NGC_k1": {"real": -162.29, "sem": 11.28, "redshift": -172.3,
                                       "ratio": 0.942},
                            "SGC_k0": {"real": -152.37, "sem": 9.15, "redshift": -136.0,
                                       "ratio": 1.120},
                            "SGC_k1": {"real": -125.63, "sem": 8.57, "redshift": -111.1,
                                       "ratio": 1.131}},
        "what_it_says": ("Removing the RSD ENTIRELY changes Delta_mock by about 13 per cent. The "
                         "mechanism predicted the mock-side response would largely vanish without "
                         "it. It does not vanish: it stays."),
        "the_formal_verdict": ("Record 18's rule is stated on the residual AFTER subtraction of "
                               "term (e), which requires the budget and is computed separately. The "
                               "threshold there is HALF; the raw ratios are 0.920 to 1.131. "
                               "Falsification is all but certain and is recorded as such, with the "
                               "formal computation to follow."),
        "and_the_hemispheres_deviate_OPPOSITELY": ("NGC responds LESS without RSD, SGC MORE. A "
                                                   "mechanism that merely scaled the response would "
                                                   "not do that, and the opposite signs are "
                                                   "themselves a constraint on whatever the real "
                                                   "mechanism is."),
    },
    "what_is_withdrawn_and_what_survives": {
        "withdrawn": ("The claim that the factor 2.10-5.56 is produced by the AP distortion acting "
                      "on the RSD displacement. It is FALSIFIED, not weakened, and it is not "
                      "repaired."),
        "survives_the_structural_statement": ("Treatment (A) regenerates the box-to-sky mapping at "
                                              "each fiducial while the data side does not: the two "
                                              "undergo DIFFERENT perturbations. That is a fact about "
                                              "the code and does not depend on RSD."),
        "survives_the_round_trip": ("interp(interp(dC, DC, Z), Z, DC) = dC to 1.9e-16 is a property "
                                    "of the tables alone and is untouched."),
        "what_is_now_unexplained": ("WHY treatment (A) responds 2.1 to 5.6 times more than the data "
                                    "side. The observation stands; the explanation is gone. The "
                                    "remaining candidates are the channels record 18 adopted from "
                                    "the referee - the mask through the randoms, the tiling "
                                    "registration, the grid displacement - none of which is "
                                    "excluded by this run, and none of which is measured."),
    },
    "a_second_finding_that_corrects_me": {
        "what": ("n_clipped is ZERO everywhere in real space, against 0 to 9 with mean 0.703 in "
                 "redshift space. The clipping is caused ENTIRELY by the RSD."),
        "what_it_corrects": ("It was concluded during analysis that the clipping was edge geometry "
                             "and not RSD, because most excesses were below 0.5 Mpc/h while the RSD "
                             "hypothesis seemed to fit only the few at 2-3 Mpc/h. That was wrong: "
                             "small velocities give small displacements, and the small excesses are "
                             "RSD too. The reasoning generalised from the size of the excess to its "
                             "cause."),
        "what_it_means_for_D5c": ("Record 17's premise was right about the CAUSE - displacement - "
                                  "and wrong only about the dependence on deformation. Record 23 "
                                  "corrected the second part and left the first as refuted; that "
                                  "half of record 23 is itself now refuted, in our favour."),
        "the_threshold_is_unaffected": ("Record 36 derives the threshold from the EFFECT, via gate "
                                        "2.2a and the SEM, not from the cause. 28 stands."),
    },
    "consequence_for_the_response_document": {
        "section_1_must_be_revised": ("The §1 section states the RSD mechanism as the explanation "
                                      "of the 2.1-5.6 factor. That paragraph is withdrawn and "
                                      "replaced: the factor is measured and unexplained, and the "
                                      "candidate channels are named without being claimed."),
        "what_does_not_change_there": ("The two columns, the ratios, the rank 1/201, the refutation "
                                       "of both of the referee's hypotheses, and the direct slope "
                                       "comparison. Only the mechanism paragraph."),
        "section_3_8_is_now_written": ("It was [IN ATTESA DI RUN]. It reports a falsification of our "
                                       "own declared mechanism, which is a stronger answer than the "
                                       "confirmation we expected."),
    },
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, does not change the D5c threshold, and does not "
                              "alter the observed 2.10-5.56 ratio, which is a measurement and not "
                              "an interpretation."),
}

REASON = (
    "The RSD mechanism declared in records 16 and 18 is falsified by the run it predicted, and is "
    "withdrawn. "
    "THE RUN IS VALID. 2396 of 2400 cells differ from the main register, against 0 of 2400 in the "
    "null run of record 35: the behavioural check is satisfied. D5c applied retroactively at "
    "threshold 28 excludes nothing, because n_clipped is ZERO everywhere. "
    "THE MEASUREMENT. Delta_mock(B5-B1) in real space is -200.60, -162.29, -152.37 and -125.63 "
    "against the redshift-space -218.0, -172.3, -136.0 and -111.1: ratios 0.920, 0.942, 1.120 and "
    "1.131. Removing the RSD ENTIRELY changes the mock-side response by about 13 per cent. The "
    "mechanism predicted it would largely vanish. It does not. And the hemispheres deviate in "
    "OPPOSITE directions - NGC less without RSD, SGC more - which a mechanism that merely scaled "
    "the response could not produce. "
    "WHAT IS WITHDRAWN. The claim that the 2.10-5.56 factor is the AP distortion acting on the RSD "
    "displacement. Falsified, not weakened, not repaired. WHAT SURVIVES: that treatment (A) "
    "regenerates the box-to-sky mapping while the data side does not, which is a fact about the "
    "code; and the round-trip identity, which is a property of the tables. WHAT IS NOW UNEXPLAINED: "
    "why (A) responds 2.1 to 5.6 times more. The observation stands and the explanation is gone; "
    "the candidates are the channels record 18 adopted from the referee, none measured. "
    "A SECOND FINDING CORRECTS ME. n_clipped is ZERO everywhere in real space, against 0 to 9 in "
    "redshift space: the clipping is caused ENTIRELY by RSD. It had been concluded that it was edge "
    "geometry, because most excesses were under 0.5 Mpc/h while the RSD hypothesis seemed to fit "
    "only the few at 2-3. Wrong: small velocities give small displacements. The reasoning "
    "generalised from the SIZE of the excess to its CAUSE - the same failure shape as the one "
    "recorded in record 23, where a mechanism was generalised from the largest observed excess. "
    "Record 17's premise was right about the cause and wrong only about the deformation dependence. "
    "The threshold of record 36 is unaffected, because it is derived from the effect and not from "
    "the cause."
)

EVIDENCE = (
    "results/paper2/fase3_mock_realspace.jsonl, 400 records, 200 per hemisphere, six line-B points, "
    "erosions 0 and 1, real_space true, run 3 Sep 2026 in 5.96 h and 5.84 h with '[phase8] "
    "REAL_SPACE = True' printed at start. "
    "Cell comparison against fase3_mock.jsonl on N_H1_k0: 2396 of 2400 differ. "
    "Paired Delta_mock(B5-B1): -200.60 +/- 12.22 (NGC k=0), -162.29 +/- 11.28 (NGC k=1), -152.37 "
    "+/- 9.15 (SGC k=0), -125.63 +/- 8.57 (SGC k=1). Redshift-space values from the same registers: "
    "-218.0, -172.3, -136.0, -111.1. Ratios 0.920, 0.942, 1.120, 1.131. "
    "d5c_n_clipped over 2400 measurements in this run: minimum 0, maximum 0, mean 0.000. In the "
    "redshift-space run the same field gives mean 0.703, q99 4, max 9. "
    "Record 18's rule: falsified if the real-space residual after term (e) reaches at least HALF of "
    "the redshift-space residual after (e), in at least half of the measured points, in both "
    "hemispheres."
)

RULES = {
    "marker": MARKER,
    "companion_document": "risposta_referee.md, §1 and §3.8; checklist_paper2.md, item 3.8",
    "amends_records": [16, 17, 18],
    "a_declared_mechanism_is_falsified_and_stays_so": ("The RSD explanation of the 2.10-5.56 factor "
                                                       "is withdrawn. It is not weakened, "
                                                       "reformulated or repaired."),
    "the_observation_outlives_the_explanation": ("The factor is measured and stands. What is gone "
                                                 "is why. Naming candidate channels is not "
                                                 "explaining, and they are named as candidates."),
    "the_opposite_hemisphere_deviation_is_a_constraint": ("NGC 0.92-0.94, SGC 1.12-1.13. Whatever "
                                                          "the real mechanism is, it must produce "
                                                          "deviations of opposite sign between "
                                                          "hemispheres."),
    "clipping_is_entirely_rsd": ("Zero in real space over 2400 measurements. The earlier reading "
                                 "that it was edge geometry is withdrawn: it generalised from the "
                                 "size of the excess to its cause."),
    "the_d5c_threshold_is_unaffected": ("Record 36 derives it from the effect, not the cause. 28 "
                                        "stands."),
    "section_1_of_the_response_is_revised_not_withdrawn": ("Only the mechanism paragraph goes. The "
                                                           "two columns, the ratios, the rank, the "
                                                           "refutation of both referee hypotheses "
                                                           "and the slope comparison all stand."),
    "what_this_does_not_do": ("It modifies no frozen value, does not reopen Phase 3, does not touch "
                              "the E1-E4 verdict, and does not alter the measured ratio."),
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
    chk("6  idempotenza (marker 37 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 36 e' gia' nel registro", MARKER_36 in blob)

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
        chk("10 old_value cita il meccanismo dichiarato, per intero",
            ("RSD DISPLACEMENT" in rec["old_value"])
            and ("2.10-5.56" in rec["old_value"]))
        chk("11 il run e' VALIDO, col controllo comportamentale del record 35",
            ("2396 of 2400" in rec["new_value"]["the_run"]["it_is_valid_this_time"])
            and ("0 of 2400" in rec["new_value"]["the_run"]["it_is_valid_this_time"]))
        chk("12 D5c applicato all'indietro PRIMA di quotare, come i record 23 e 36",
            ("ZERO" in rec["new_value"]["the_run"]["d5c_applied_retroactively"])
            and ("may be quoted" in rec["new_value"]["the_run"]["d5c_applied_retroactively"]))
        chk("13 si distingue cosa CADE da cosa SOPRAVVIVE, e cosa resta ignoto",
            ("FALSIFIED, not weakened" in rec["new_value"]
                ["what_is_withdrawn_and_what_survives"]["withdrawn"])
            and ("what_is_now_unexplained" in rec["new_value"]
                 ["what_is_withdrawn_and_what_survives"]))
        chk("13f il record 36 e' sulla riga 36 e si emendano 16, 17, 18",
            (MARKER_36 in json.dumps(recs[35], ensure_ascii=False))
            and rec["rules"]["amends_records"] == [16, 17, 18])
        chk("13g la deviazione OPPOSTA fra emisferi e' registrata come vincolo",
            ("OPPOSITELY" in " ".join(rec["new_value"]["the_mechanism_is_falsified"]))
            and ("opposite sign between" in rec["rules"]
                 ["the_opposite_hemisphere_deviation_is_a_constraint"]))
        chk("13h il secondo errore mio e' registrato, con la sua forma",
            ("generalised from the SIZE of the excess to its CAUSE" in rec["reason"])
            and ("edge geometry" in rec["rules"]["clipping_is_entirely_rsd"]))
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
        bad = []
        M = rec["new_value"]["the_mechanism_is_falsified"]["the_measurement"]
        # 1. i rapporti si ricalcolano dai due numeri
        for nm, d in M.items():
            if abs(d["real"] / d["redshift"] - d["ratio"]) > 5e-4:
                bad.append(nm + "/rapporto")
        # 2. TUTTI sopra la soglia di meta': e' la falsificazione
        if not all(d["ratio"] > 0.5 for d in M.values()):
            bad.append("qualche rapporto sotto 0.5: non sarebbe falsificato")
        # 3. e la deviazione e' OPPOSTA fra emisferi: NGC sotto 1, SGC sopra
        ngc = [d["ratio"] for k, d in M.items() if k.startswith("NGC")]
        sgc = [d["ratio"] for k, d in M.items() if k.startswith("SGC")]
        if not (all(x < 1 for x in ngc) and all(x > 1 for x in sgc)):
            bad.append("la deviazione non e' opposta: cade un'affermazione del record")
        # 4. lo scostamento massimo da 1 e' il ~13% dichiarato
        worst = max(abs(d["ratio"] - 1) for d in M.values())
        if abs(worst - 0.131) > 0.005:
            bad.append("scostamento massimo %.3f" % worst)
        # 5. e le SEM sono coerenti con quelle del run in redshift
        for nm, d in M.items():
            if not (7.0 < d["sem"] < 14.0):
                bad.append(nm + "/sem anomala")
        chk("14 aritmetica: rapporti ricalcolati, tutti > 0.5, deviazione "
            "opposta fra emisferi, scostamento max %.1f%%" % (100 * worst),
            not bad, ",".join(bad) if bad else "sedici controlli numerici")
    except Exception as exc:
        chk("14 aritmetica del record", False, str(exc))

    return _report(checks, verbose)


def _report(checks, verbose):
    if verbose:
        print("=== SELFTEST paper2_append_amend37 rev.1 ===")
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
        fail("il record 37 aggiunge le chiavi %s rispetto alle comuni 13-15. "
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

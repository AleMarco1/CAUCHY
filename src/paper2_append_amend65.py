#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_append_amend65.py — record 65: il censimento del 6.9, e Q5.

CHE COSA REGISTRA
    1. La popolazione del censimento non e' nove script. Lo stesso `Select-String` del
       13 set, riprodotto, trova 39 file col pattern stretto e 76 col pattern largo; il
       filtro che portava a nove non era dichiarato e non era coerente. I siti che
       EMETTONO un verdetto da codice che gira sono 55, su 25 file.
    2. Q5 di D6 esiste, e' dichiarata con la sua soglia, e' emessa, e non e' mai stata
       raccolta. Compare una volta in tutto il ledger, nel record 1, come predizione che
       sara' ripetuta su v2.
    3. Q5 e' stata misurata su entrambe le procedure e REGGE su tutte le basi.
    4. La causa: il dizionario `SOGLIE` di src/paper2_d6_incertezze.py contiene quattro
       voci. Finche' ne contiene quattro, la prossima ripetizione su v2 perdera' Q5 di
       nuovo. Questo record NON la corregge: lo dichiara.

I NUMERI NON SONO SCRITTI QUI
    Vengono letti da results/paper2/q5_margine.jsonl, il registro che li tiene. E' la
    forma del record 64: un conteggio si legge dal documento che lo tiene, non da una
    descrizione. Se il registro non c'e' o non ha le due regioni, il tool rifiuta.

CANCELLI PRIMA DI COSTRUIRE
    - il ledger ha esattamente --attesi record e l'ultimo e' il 64;
    - l'item non e' gia' presente;
    - nel file delle smentite i gruppi sono ancora 12 / 1 / 5, Q1-Q4 ci sono e
      Q5 NON c'e': questo record asserisce che manca, quindi va appeso PRIMA del
      patcher sui documenti;
    - la dichiarazione di Q5 e' davvero nel docstring di src/paper2_compD_nonlinear.py
      e la riga di emissione c'e';
    - `SOGLIE` di src/paper2_d6_incertezze.py NON contiene Q5, che e' la causa che il
      record dichiara. Se qualcuno l'ha gia' aggiunta, il record e' da riscrivere.

USO
    python src\\paper2_append_amend65.py selftest
    python src\\paper2_append_amend65.py append --ledger src\\paper2_v1_amendments.jsonl ^
        --reference src\\paper2_v1_reference.json --q5 results\\paper2\\q5_margine.jsonl ^
        --smentite papers\\paper2\\paper2_5_5_smentite.md --attesi 64 --dry-run
    (poi la stessa riga senza --dry-run)

NOTA SULL'IMPORT
    sha256_file, leggi_ledger e Rifiuto si importano da paper2_append_amend50, non si
    riscrivono. Il contratto assunto e' quello che paper2_append_amend64.py usa:
    sha256_file(path) -> hex, leggi_ledger(path) -> (raw, recs, _, _, _), Rifiuto
    eccezione. Se non fosse quello, il selftest lo dice invece di ripiegare.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

CRLF = chr(13).encode() + chr(10).encode()
LF = chr(10).encode()
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"

ITEM_PREV = "5.5/correzione_del_63_i_gruppi_delle_smentite_sono_ancorati_al_ledger"
ITEM_65 = "6.9/censimento_dei_verdetti_e_Q5_dichiarata_emessa_e_mai_raccolta"

ATTESI_A, ATTESI_ABIS, ATTESI_B = 12, 1, 5
SMENTITE = "papers/paper2/paper2_5_5_smentite.md"
FONTE_Q5 = "src/paper2_compD_nonlinear.py"
FONTE_SOGLIE = "src/paper2_d6_incertezze.py"

# Il censimento del 14 set, con lo strumento paper2_censimento_verdetti.py rev.3.
CENSIMENTO = {
    "strumento": "src/paper2_censimento_verdetti.py rev.3",
    "file_scansionati": 328,
    "vocabolario_base": "smentit|confermat|falsificat, maiuscole ignorate",
    "file_con_match": 76,
    "righe_con_match": 324,
    "occorrenze": 372,
    "siti_che_emettono": 55,
    "file_che_emettono": 25,
    "perche_non_nove": (
        "The nine of record 64 came from a Select-String whose filter was never declared. "
        "The same pattern returns 39 files; the wider pattern returns 76. Two of the nine "
        "emit nothing at all: src/paper2_pareggi.py has the words in a docstring describing "
        "a rule, src/paper2_runner_fase3_mock.py in a comment recording a verdict that IS "
        "in the ledger. src/paper1_rev_v2h_monotone.py carries the same line as "
        "src/paper1_rev_v2g_frozen.py and was outside the nine; "
        "src/paper2_d6_incertezze.py computes a verdict from a threshold and was outside too."),
    "select_string_e_case_insensitive": (
        "PowerShell's Select-String ignores case by default, so 'confermata|SMENTITA' also "
        "matched 'smentita' and 'Confermata'. Case-sensitively the same pattern returns 66 "
        "lines, not 112. The pattern that ran was not the pattern that was written down."),
}

TESTO_Q5 = ("R^2_cv(P(k)) resta SOTTO il tetto 0.832 dei predittori misurati. Se lo superasse, "
            "P(k) starebbe catturando anche il termine HOD, il che significherebbe che il cache "
            "non e' quello che credo.")


def analizza_eol(raw):
    crlf = raw.count(CRLF)
    lf_isolati = raw.count(LF) - crlf
    termina = None if (not raw or not raw.endswith(LF)) else (CRLF if raw.endswith(CRLF) else LF)
    return {"crlf": crlf, "lf_isolati": lf_isolati, "termina": termina,
            "misto": bool(crlf and lf_isolati)}


def leggi_reference(path):
    sha_file = sha256_file(path)
    with open(path, "rb") as fh:
        ref = json.loads(fh.read().decode("utf-8"))
    self_sha = ref.get("_self_sha256") if isinstance(ref, dict) else None
    if not isinstance(self_sha, str) or len(self_sha) != 64:
        raise Rifiuto("'_self_sha256' non leggibile dal reference; usa --self-sha")
    return sha_file, self_sha


# --------------------------------------------------------------------------- cancelli


def cancello_smentite(path):
    """I gruppi non cambiano, Q1-Q4 ci sono, Q5 NON c'e' ancora."""
    if not os.path.isfile(path):
        raise Rifiuto("file delle smentite assente: %s" % path)
    testo = open(path, "r", encoding="utf-8").read()
    c = {
        "A": len(re.findall(r"^\|\s*A(\d+)\s*\|", testo, re.M)),
        "A_bis": len(re.findall(r"^\|\s*Ab(\d+)\s*\|", testo, re.M)),
        "B": len(re.findall(r"^\|\s*B(\d+)\s*\|", testo, re.M)),
        "sha256": sha256_file(path),
    }
    if (c["A"], c["A_bis"], c["B"]) != (ATTESI_A, ATTESI_ABIS, ATTESI_B):
        raise Rifiuto("gruppi nel documento: A=%d A-bis=%d B=%d, attesi %d/%d/%d"
                      % (c["A"], c["A_bis"], c["B"], ATTESI_A, ATTESI_ABIS, ATTESI_B))
    presenti = sorted({m for m in re.findall(r"^\|\s*(Q[1-5])\s*\|", testo, re.M)})
    c["Q_in_tabella"] = presenti
    if presenti != ["Q1", "Q2", "Q3", "Q4"]:
        raise Rifiuto("righe Q nella 3-bis: %s. Attese esattamente Q1-Q4: se Q5 c'e' gia', "
                      "questo record non ha piu' senso; se mancano le altre, il patcher del "
                      "record 64 non e' stato applicato" % (presenti or "nessuna"))
    return c


def cancello_dichiarazione(path_fonte, path_soglie):
    """Q5 e' dichiarata ed emessa nel codice, e SOGLIE non la contiene."""
    if not os.path.isfile(path_fonte):
        raise Rifiuto("sorgente assente: %s" % path_fonte)
    testo = open(path_fonte, "r", encoding="utf-8").read()
    if not re.search(r"^\s*Q5\s", testo, re.M):
        raise Rifiuto("nel docstring di %s non trovo la dichiarazione di Q5" % path_fonte)
    if "CEIL_MEASURED" not in testo:
        raise Rifiuto("in %s non trovo CEIL_MEASURED: la soglia di Q5" % path_fonte)
    emissioni = len(re.findall(r'"confermata" if .* else "SMENTITA"', testo))
    if emissioni < 5:
        raise Rifiuto("in %s trovo %d emissioni di verdetto, attese almeno 5 (Q1-Q5)"
                      % (path_fonte, emissioni))

    if not os.path.isfile(path_soglie):
        raise Rifiuto("sorgente assente: %s" % path_soglie)
    t2 = open(path_soglie, "r", encoding="utf-8").read()
    m = re.search(r"^SOGLIE\s*=\s*\{(.*?)^\}", t2, re.M | re.S)
    if not m:
        raise Rifiuto("in %s non trovo il dizionario SOGLIE" % path_soglie)
    voci = sorted(set(re.findall(r'"(Q\d)[^"]*"\s*:', m.group(1))))
    if voci != ["Q1", "Q2", "Q3", "Q4"]:
        raise Rifiuto("SOGLIE contiene %s. Questo record dichiara che ne contiene quattro, "
                      "Q1-Q4: se e' stato corretto, il record va riscritto" % voci)
    return {"emissioni_di_verdetto": emissioni, "soglie_presenti": voci,
            "sha256_fonte": sha256_file(path_fonte), "sha256_soglie": sha256_file(path_soglie)}


def cancello_q5(path):
    """I numeri si leggono dal registro che li tiene, non si scrivono qui."""
    if not os.path.isfile(path):
        raise Rifiuto("registro di Q5 assente: %s. Eseguire prima paper2_q5.py margine "
                      "sulle due regioni." % path)
    recs = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, linea in enumerate(fh, 1):
            if not linea.strip():
                continue
            try:
                recs.append(json.loads(linea))
            except json.JSONDecodeError as e:
                raise Rifiuto("riga %d di %s malformata: %s" % (i, path, e))
    per_regione = {}
    for r in recs:
        if r.get("schema") != "paper2_q5_v1":
            raise Rifiuto("schema inatteso in %s: %s" % (path, r.get("schema")))
        if r.get("predizione") != "Q5":
            raise Rifiuto("record non su Q5 in %s" % path)
        per_regione[r.get("region")] = r      # append-only: l'ultimo vince, dichiarato
    mancanti = [x for x in ("NGC", "SGC") if x not in per_regione]
    if mancanti:
        raise Rifiuto("il registro di Q5 non copre %s" % ", ".join(mancanti))

    fuori = {}
    soglie = set()
    for reg, r in per_regione.items():
        if r.get("verso") != "<":
            raise Rifiuto("%s: verso '%s', atteso '<'" % (reg, r.get("verso")))
        soglie.add(float(r["soglia"]))
        a = r["a_procedura_dichiarata"]["forme"]["ln_di_log10P_come_nel_codice"]
        b = r.get("b_stesso_stimatore_ai_due_lati")
        if not b:
            raise Rifiuto("%s: il registro non porta il denominatore che decide. Rieseguire "
                          "paper2_q5.py con --registro-kernel." % reg)
        bd = b["sul_denominatore_che_decide"]
        if a["esito"] != "confermata" or bd["esito"] != "confermata":
            raise Rifiuto("%s: esiti '%s' e '%s'. Questo record dichiara che Q5 REGGE: se "
                          "non regge, va riscritto." % (reg, a["esito"], bd["esito"]))
        if not (a["decidibile"] and bd["decidibile"]):
            raise Rifiuto("%s: margine non decidibile. Un margine non decidibile non si "
                          "arrotonda a un esito." % reg)
        fuori[reg] = {
            "procedura_dichiarata_lineare": {
                "valore": a["valore"], "sd_partizione": a["sd"],
                "margine_in_sigma": a["margine_in_sigma"],
                "denominatore_che_decide": "absent for this procedure: no bootstrap over "
                                           "realisations exists for the linear model"},
            "stesso_stimatore_ai_due_lati_K": {
                "valore": b["valore"], "sd_ensemble": bd["sd"],
                "margine_in_sigma": bd["margine_in_sigma"],
                "rapporto_sd_ensemble_su_partizione": b["rapporto_sd"],
                "rapporto_dentro_il_dichiarato_2_8_3_8": b["rapporto_dentro_il_dichiarato"]},
            "esito": "HOLDS",
            "registro_kernel": b["registro"],
            "utc_misura": r.get("utc"),
        }
    if len(soglie) != 1:
        raise Rifiuto("le due regioni portano soglie diverse: %s" % sorted(soglie))
    return {"soglia": soglie.pop(), "regioni": fuori, "sha256": sha256_file(path),
            "record_letti": len(recs)}


# ------------------------------------------------------------------------ costruzione


def costruisci(n_prima, ref_file_sha, ref_self_sha, smentite, dichiarazione, q5, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM_65,
        "key": "the_census_of_out_of_ledger_verdicts_and_the_fifth_prediction_of_D6",
        "json_path": "%s; checklist items 6.9 and 5.5; records 1, 60, 63 and 64" % SMENTITE,
        "old_value": (
            "Record 64 opened item 6.9 naming nine scripts that emit a verdict the ledger does "
            "not see, and enumerated the declared predictions of D6 as P1 and Q1 to Q4. "
            "Record 63 re-read four of them. The prereg summary at §0 states 'Q1, Q2, Q3 and Q4 "
            "are all FALSIFIED'. Checklist line 602 reads 'D6 con P1 e Q1-Q4 smentite'. "
            "Section 3-bis of %s carries four rows." % SMENTITE),
        "new_value": {
            "i_the_population_is_not_nine": CENSIMENTO,
            "ii_Q5_exists_and_was_never_collected": {
                "text_as_declared": TESTO_Q5,
                "declared_in": ("the PREDICTIONS docstring of %s, written before the run; "
                                "emitted by the same file as the fifth of five verdicts "
                                "('confermata' if R2 < CEIL_MEASURED else 'SMENTITA')" % FONTE_Q5),
                "threshold": "CEIL_MEASURED = (SIGMA_COS^2 + SIGMA_REAL^2) / SIGMA_TOT^2",
                "threshold_value": q5["soglia"],
                "direction": "<",
                "note_on_the_rounded_form": ("the docstring cites the ceiling as 0.832; the "
                                             "constant is %.16f and that is the value the "
                                             "verdict was emitted against. A prediction is "
                                             "declared on ONE value." % q5["soglia"]),
                "absent_from": [
                    "the SOGLIE dictionary of %s, which holds four entries" % FONTE_SOGLIE,
                    "record 63, which re-read Q1 to Q4",
                    "record 64, which enumerated P1 and Q1 to Q4",
                    "checklist line 602",
                    "section 3-bis of %s" % SMENTITE,
                    "the prereg §0 summary",
                ],
                "present_in_the_ledger": ("once, in record 1: 'D2 e D6 saranno ripetute su "
                                          "ensemble v2 con le predizioni P1-P5 e Q1-Q5 "
                                          "invariate'. A forward statement about v2, not the "
                                          "declaration of the prediction with its threshold."),
            },
            "iii_Q5_measured_and_it_holds": {
                "measured_by": "src/paper2_q5.py rev.2, read-only on the measurement registers",
                "registro": "results/paper2/q5_margine.jsonl",
                "registro_sha256": q5["sha256"],
                "reproduction_gate": ("the margins of Q1 to Q4 were recomputed from the "
                                      "quantities in results/paper2/d6_incertezze.jsonl with "
                                      "the same margine() and matched the recorded ones at "
                                      "rel = 0.0 on value, sd, threshold, margin and verdict, "
                                      "in both hemispheres"),
                "two_procedures_not_mixed": (
                    "Q5 speaks of R^2_cv(P(k)) and two such quantities exist: (a) the procedure "
                    "on which Q5 was declared, a LINEAR regression on principal components, and "
                    "(b) the same estimator on both sides, kernel ridge on 110 bins. The "
                    "ensemble dispersion belongs to (b) and is not attached to the value of (a). "
                    "Same discipline record 63 imposed on Q3."),
                "per_region": q5["regioni"],
                "verdict": ("HOLDS on every basis. The direction is 'stays below' and the "
                            "measured value sits at 0.31 to 0.38 against a ceiling of 0.832: "
                            "no denominator brings it near the threshold."),
                "consequence_declared_with_the_prediction": (
                    "Q5 was written to exclude the possibility that P(k) is also capturing the "
                    "HOD term, i.e. that the cache is not what it was believed to be. Q5 "
                    "holding is the direct empirical argument against that, and it is now "
                    "recorded instead of implicit."),
            },
            "iv_why_the_counts_do_not_change": {
                "counts": {"A": smentite["A"], "A_bis": smentite["A_bis"], "B": smentite["B"]},
                "reason": ("Group membership is anchored to the ledger record that DECLARES the "
                           "prediction, not to the one that resolves it. Q1 to Q5 are declared "
                           "in the docstrings of the analysis scripts and in prereg §0; record 1 "
                           "names Q1-Q5 but as a forward statement about v2. So Q5 joins section "
                           "3-bis and the counts stay 12 / 1 / 5, exactly as record 64 ruled for "
                           "Q1 to Q4. Appending THIS record does not move Q5 into group A."),
                "what_section_3bis_becomes": ("five rows: four falsifications re-read with their "
                                              "uncertainty, and one prediction that holds. A "
                                              "section of failures only is as selected as one of "
                                              "successes only — the reason A12 is kept in §1."),
            },
            "v_the_cause_still_in_place": {
                "where": "%s, dictionary SOGLIE" % FONTE_SOGLIE,
                "state": ("four entries, Q1 to Q4, verified at the time of this record: %s"
                          % ", ".join(dichiarazione["soglie_presenti"])),
                "consequence": ("the margin of Q5 was never computed because the table of "
                                "thresholds did not contain it. While it contains four entries, "
                                "the repetition on ensemble v2 announced by record 1 will lose "
                                "Q5 again."),
                "this_record_does_not_fix_it": True,
                "sha256_of_the_file_as_read": dichiarazione["sha256_soglie"],
            },
            "vi_what_this_record_does_not_do": [
                "it does not classify the remaining out-of-ledger candidates: the two thresholds "
                "of src/paper2_gate53.py (spectral fraction in [0.70, 0.82] and |z| > 3, declared "
                "before the run in SGC_PRED) and the 0.005 excursion of "
                "src/paper2_item12b_wbar.py, none of which has a ledger record",
                "it does not add Q5 to section 3-bis: that is the document patcher, which must "
                "run after this record",
                "it does not add Q5 to the SOGLIE dictionary",
                "it does not reopen the reading of record 60, whose scope was already attached "
                "by record 64: 'no falsification was missed' is true INSIDE the register",
            ],
        },
        "reason": (
            "Item 6.9 asked for a census of the verdicts emitted outside the ledger, and forbade "
            "declaring a number before opening the files. Opening them showed two things: the "
            "population of nine was a filtered list whose filter was never declared, and one of "
            "the five declared predictions of D6 had never been collected. Q5 was declared with "
            "its threshold and its consequence, emitted by the analysis script, and absent from "
            "every document that enumerates the predictions of D6. It has now been measured on "
            "both procedures, with the reproduction gate on Q1 to Q4 passing at rel = 0.0, and "
            "it holds. Recorded as a prediction that held, not repaired and not rewritten."),
        "evidence": (
            "Census: %s over %d .py files; 76 files and 324 lines with the base vocabulary, "
            "reproducing the Select-String of 13 Sept; %d sites that emit a verdict from running "
            "code, over %d files. Q5: %s (sha256 %s), %d records, both hemispheres. Declared "
            "procedure, linear: NGC %.6f +- %.6f at %.1f sigma below the ceiling, SGC %.6f +- "
            "%.6f at %.1f sigma. Same estimator both sides, K with the ensemble bootstrap: NGC "
            "%.6f +- %.6f at %.1f sigma, SGC %.6f +- %.6f at %.1f sigma. Ratio of the two "
            "dispersions %.3f and %.3f, inside the declared 2.8-3.8. Source of the declaration: "
            "%s (sha256 %s), %d verdict emissions. Cause: %s (sha256 %s), SOGLIE with four "
            "entries. Counts read from %s (sha256 %s): A=%d, A-bis=%d, B=%d, rows Q1-Q4 present "
            "and Q5 absent."
            % (CENSIMENTO["strumento"], CENSIMENTO["file_scansionati"],
               CENSIMENTO["siti_che_emettono"], CENSIMENTO["file_che_emettono"],
               "results/paper2/q5_margine.jsonl", q5["sha256"], q5["record_letti"],
               q5["regioni"]["NGC"]["procedura_dichiarata_lineare"]["valore"],
               q5["regioni"]["NGC"]["procedura_dichiarata_lineare"]["sd_partizione"],
               q5["regioni"]["NGC"]["procedura_dichiarata_lineare"]["margine_in_sigma"],
               q5["regioni"]["SGC"]["procedura_dichiarata_lineare"]["valore"],
               q5["regioni"]["SGC"]["procedura_dichiarata_lineare"]["sd_partizione"],
               q5["regioni"]["SGC"]["procedura_dichiarata_lineare"]["margine_in_sigma"],
               q5["regioni"]["NGC"]["stesso_stimatore_ai_due_lati_K"]["valore"],
               q5["regioni"]["NGC"]["stesso_stimatore_ai_due_lati_K"]["sd_ensemble"],
               q5["regioni"]["NGC"]["stesso_stimatore_ai_due_lati_K"]["margine_in_sigma"],
               q5["regioni"]["SGC"]["stesso_stimatore_ai_due_lati_K"]["valore"],
               q5["regioni"]["SGC"]["stesso_stimatore_ai_due_lati_K"]["sd_ensemble"],
               q5["regioni"]["SGC"]["stesso_stimatore_ai_due_lati_K"]["margine_in_sigma"],
               q5["regioni"]["NGC"]["stesso_stimatore_ai_due_lati_K"][
                   "rapporto_sd_ensemble_su_partizione"],
               q5["regioni"]["SGC"]["stesso_stimatore_ai_due_lati_K"][
                   "rapporto_sd_ensemble_su_partizione"],
               FONTE_Q5, dichiarazione["sha256_fonte"], dichiarazione["emissioni_di_verdetto"],
               FONTE_SOGLIE, dichiarazione["sha256_soglie"],
               SMENTITE, smentite["sha256"], smentite["A"], smentite["A_bis"], smentite["B"])),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": ("The number of an amendment is its 1-based POSITION in this file. "
                           "This is record %d." % numero),
        "rules": {
            "amends_records": [63, 64],
            "scope_of_the_amendment": ("records 63 and 64 enumerate the declared predictions of "
                                       "D6 as P1 and Q1 to Q4. There are five Q. Their verdicts "
                                       "stand; the enumeration was short by one."),
            "counts_unchanged": [ATTESI_A, ATTESI_ABIS, ATTESI_B],
            "a_prediction_that_holds_is_recorded_too": (
                "Q5 held. It is recorded with the same weight as a falsification, because a "
                "section of failures only is as selected as one of successes only."),
            "order_of_operations": ("this record first; then "
                                    "paper2_patch_documented_amendments.py from %d to %d; then "
                                    "freeze_verify; then the document patcher that adds the Q5 "
                                    "row to section 3-bis." % (n_prima, numero)),
        },
    }


def serializza(rec):
    return json.dumps(rec, ensure_ascii=False, sort_keys=False).encode("utf-8")


def cmd_append(args):
    try:
        if not os.path.isfile(args.reference):
            raise Rifiuto("reference inesistente: %s" % args.reference)
        if not os.path.isfile(args.ledger):
            raise Rifiuto("ledger inesistente: %s" % args.ledger)
        ref_file_sha, ref_self_sha = ((sha256_file(args.reference), args.self_sha)
                                      if args.self_sha else leggi_reference(args.reference))
        raw, recs, _e, _c, _l = leggi_ledger(args.ledger)
        if not all(isinstance(r, dict) for r in recs):
            raise Rifiuto("leggi_ledger non restituisce dizionari")
        if len(recs) != args.attesi:
            raise Rifiuto("disco=%d attesi=%d" % (len(recs), args.attesi))
        eol = analizza_eol(raw)
        if eol["termina"] is None:
            raise Rifiuto("l'ultima riga del ledger non termina con un a capo")
        if recs[-1].get("item") != ITEM_PREV:
            raise Rifiuto("l'ultimo record non e' il 64: item='%s'" % recs[-1].get("item"))
        if any(r.get("item") == ITEM_65 for r in recs):
            raise Rifiuto("item gia' presente: %s" % ITEM_65)

        # tutti i cancelli PRIMA di scrivere qualunque cosa
        smentite = cancello_smentite(args.smentite)
        dichiarazione = cancello_dichiarazione(args.fonte_q5, args.fonte_soglie)
        q5 = cancello_q5(args.q5)

        rec = costruisci(len(recs), ref_file_sha, ref_self_sha, smentite, dichiarazione, q5)
        b = serializza(rec)
        if CRLF in b or LF in b:
            raise Rifiuto("il record serializzato contiene un fine riga")
        json.loads(b.decode("utf-8"))
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("ledger     : %s" % args.ledger)
    print("record     : %d (disco ora: %d)" % (len(recs) + 1, len(recs)))
    print("smentite   : A=%d  A-bis=%d  B=%d, Q in tabella %s"
          % (smentite["A"], smentite["A_bis"], smentite["B"],
             ", ".join(smentite["Q_in_tabella"])))
    print("             Q5 assente dalla tabella, come il record asserisce")
    print("SOGLIE     : %s  (quattro voci, la causa dichiarata)"
          % ", ".join(dichiarazione["soglie_presenti"]))
    print("Q5         : soglia %.16f, verso '<'" % q5["soglia"])
    for reg in ("NGC", "SGC"):
        d = q5["regioni"][reg]
        print("             %s  lineare %.6f a %.1f sigma   |   K %.6f a %.1f sigma "
              "sul bootstrap"
              % (reg, d["procedura_dichiarata_lineare"]["valore"],
                 d["procedura_dichiarata_lineare"]["margine_in_sigma"],
                 d["stesso_stimatore_ai_due_lati_K"]["valore"],
                 d["stesso_stimatore_ai_due_lati_K"]["margine_in_sigma"]))
    print("byte       : %d -> %d" % (len(raw), len(raw) + len(b) + len(eol["termina"])))

    if args.dry_run:
        print("\n[dry-run] niente scritto.")
        return 0

    nuovo = raw + b + eol["termina"]
    if args.backup:
        with open(args.backup, "wb") as fh:
            fh.write(raw)
    d = os.path.dirname(os.path.abspath(args.ledger))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=os.path.basename(args.ledger) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(nuovo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, args.ledger)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    raw2, recs2, _e2, _c2, _l2 = leggi_ledger(args.ledger)
    esiti = [
        (len(recs2) == args.attesi + 1, "conteggio %d -> %d" % (args.attesi, len(recs2))),
        (raw2.startswith(raw), "i %d record precedenti sono byte-identici" % args.attesi),
        (analizza_eol(raw2)["lf_isolati"] == eol["lf_isolati"] + (1 if eol["termina"] == LF
                                                                  else 0),
         "i fini riga preesistenti sono intatti, e il nuovo e' quello ereditato (%s)"
         % ("LF" if eol["termina"] == LF else "CRLF")),
        (analizza_eol(raw2)["crlf"] == eol["crlf"] + (1 if eol["termina"] == CRLF else 0),
         "nessun CRLF preesistente e' stato normalizzato"),
        (recs2[-1].get("item") == ITEM_65, "l'item e' quello nuovo"),
        ("record %d." % (args.attesi + 1) in recs2[-1]["numbering_rule"], "numbering_rule"),
        (recs2[-1]["rules"]["amends_records"] == [63, 64], "emenda 63 e 64"),
        (recs2[-1]["rules"]["counts_unchanged"] == [ATTESI_A, ATTESI_ABIS, ATTESI_B],
         "i conteggi restano 12/1/5"),
    ]
    print()
    for c, nome in esiti:
        print(("  OK  " if c else "  KO  ") + nome)
    if not all(c for c, _ in esiti):
        return 5
    print("\nOra: python src\\paper2_patch_documented_amendments.py apply --file "
          "src\\paper2_freeze_verify.py --da %d --a %d" % (args.attesi, args.attesi + 1))
    print("     python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    print("     e SOLO DOPO il patcher sui documenti, che aggiunge la riga Q5 alla 3-bis.")
    return 0


# --------------------------------------------------------------------------- selftest


FINTA_3BIS = """# smentite

| # | dichiarata in | esito in | predizione | esito |
|---|---:|---:|---|---|
| A1 | prereg | 13 | x | y |
| A2 | 15 | 19 | x | y |
| A3 | 16 | 37 | x | y |
| A4 | 16 | 38 | x | y |
| A5 | 18 | 37 | x | y |
| A6 | 19 | 19 | x | y |
| A7 | 30 | 31 | x | y |
| A8 | 3.2e | 46 | x | y |
| A9 | 50 | 57 | x | y |
| A10 | 50 | 58 | x | y |
| A11 | 58 | 59 | x | y |
| A12 | 26 | 39 | x | y |

| # | dichiarata in | esito in | predizione | esito |
|---|---:|---:|---|---|
| Ab1 | 24 | 25 | x | y |

| # | riga | che cosa | esito |
|---|---:|---|---|
| B1 | 48 | x | y |
| B2 | 50 | x | y |
| B3 | 54 | x | y |
| B4 | 13 | x | y |
| B5 | 29 | x | y |

## 3-bis

| # | soglia dichiarata | esito di agosto | esito con l'incertezza |
|---|---|---|---|
| Q1 | a | SMENTITA | b |
| Q2 | a | SMENTITA | b |
| Q3 | a | SMENTITA | b |
| Q4 | a | SMENTITA | b |
"""

FINTA_FONTE = '''"""x"""
PREDICTIONS = """
PREDIZIONI DICHIARATE PRIMA DEL RUN
  Q1  I termini quadratici aggiungono < 0.05.
  Q2  Le interazioni aggiungono < 0.03.
  Q3  R^2_cv(P(k)) > 0.50.
  Q4  Chiude piu' della meta' del divario.
  Q5  R^2_cv(P(k)) resta SOTTO il tetto 0.832 dei predittori misurati.
"""
CEIL_MEASURED = 0.8320530984290949
print("%s" % ("confermata" if a < 0.05 else "SMENTITA"))
print("%s" % ("confermata" if b < 0.03 else "SMENTITA"))
print("%s" % ("confermata" if c > 0.50 else "SMENTITA"))
print("%s" % ("confermata" if d < CEIL_MEASURED else "SMENTITA"))
print("%s" % ("confermata" if e > 0.5 else "SMENTITA"))
'''

FINTE_SOGLIE = '''SOGLIE = {
    "Q1_quadrati": {"soglia": 0.05, "verso": "<", "quantita": "gain_quad"},
    "Q2_interazioni": {"soglia": 0.03, "verso": "<", "quantita": "gain_int"},
    "Q3_B_sopra_mezzo": {"soglia": 0.50, "verso": ">", "quantita": "B_best"},
    "Q4_meta_divario": {"soglia": 0.50, "verso": ">", "quantita": "C_frac_parametri"},
}
'''


def _finto_q5(region, lin, sdl, sigl, k, sde, sigk, rapp=3.0, soglia=0.8320530984290949):
    return {
        "schema": "paper2_q5_v1", "rev": "paper2_q5 rev.2", "region": region,
        "predizione": "Q5", "soglia": soglia, "verso": "<",
        "utc": "2026-09-14T09:00:00Z",
        "a_procedura_dichiarata": {"forme": {"ln_di_log10P_come_nel_codice": {
            "valore": lin, "sd": sdl, "esito": "confermata",
            "margine_in_sigma": sigl, "decidibile": True}}},
        "b_stesso_stimatore_ai_due_lati": {
            "registro": "results/paper2/d6bis.jsonl", "valore": k,
            "rapporto_sd": rapp, "rapporto_dentro_il_dichiarato": True,
            "sul_denominatore_che_decide": {
                "valore": k, "sd": sde, "esito": "confermata",
                "margine_in_sigma": sigk, "decidibile": True}},
    }


def cmd_selftest(args=None):
    import shutil
    esiti = []

    def ok(nome, cond):
        esiti.append((bool(cond), nome))
        print("  [%s] %s" % ("ok" if cond else "FALLITO", nome))

    class A(object):
        self_sha = None
        backup = None
        dry_run = False

    td = tempfile.mkdtemp(prefix="amend65_")
    try:
        led = os.path.join(td, "ledger.jsonl")
        ref = os.path.join(td, "reference.json")
        sm = os.path.join(td, "smentite.md")
        fonte = os.path.join(td, "compD.py")
        soglie = os.path.join(td, "d6inc.py")
        q5 = os.path.join(td, "q5.jsonl")

        with open(ref, "wb") as fh:
            fh.write(json.dumps({"_self_sha256": "a" * 64}).encode("utf-8"))

        def scrivi_ledger(n=64, ultimo=ITEM_PREV, termina=CRLF, lf_isolati=6):
            """Imita il ledger vero: misto, 6 LF isolati fra i primi record, e l'ultima
            riga che termina come `termina`."""
            fuori = b""
            for i in range(1, n + 1):
                it = ultimo if i == n else "item_%d" % i
                b = json.dumps({"item": it, "n": i}, ensure_ascii=False).encode("utf-8")
                if i == n:
                    fuori += b + termina
                else:
                    fuori += b + (LF if i <= lf_isolati else CRLF)
            with open(led, "wb") as fh:
                fh.write(fuori)

        def scrivi(p, testo):
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(testo)

        def scrivi_q5(recs=None):
            recs = recs if recs is not None else [
                _finto_q5("NGC", 0.317658, 0.007325, 70.2, 0.380761, 0.046725, 9.7, 3.078),
                _finto_q5("SGC", 0.308124, 0.005898, 88.8, 0.361249, 0.042977, 11.0, 3.036)]
            with open(q5, "w", encoding="utf-8", newline="\n") as fh:
                for r in recs:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")

        def args_di(attesi=64, dry=False):
            x = A()
            x.ledger, x.reference, x.smentite = led, ref, sm
            x.fonte_q5, x.fonte_soglie, x.q5 = fonte, soglie, q5
            x.attesi, x.dry_run = attesi, dry
            return x

        def tutto_buono():
            scrivi_ledger()
            scrivi(sm, FINTA_3BIS)
            scrivi(fonte, FINTA_FONTE)
            scrivi(soglie, FINTE_SOGLIE)
            scrivi_q5()

        # --- il contratto dell'import, prima di tutto
        ok("01 sha256_file importata, non riscritta",
           sys.modules["paper2_append_amend50"].sha256_file is sha256_file)
        tutto_buono()
        r = leggi_ledger(led)
        ok("02 leggi_ledger restituisce (raw, recs, ...) come atteso da amend64",
           isinstance(r, tuple) and len(r) >= 2 and isinstance(r[0], bytes)
           and isinstance(r[1], list) and len(r[1]) == 64)

        # --- dry-run
        prima = open(led, "rb").read()
        ok("03 dry-run esce con 0", cmd_append(args_di(dry=True)) == 0)
        ok("04 dry-run non scrive nulla", open(led, "rb").read() == prima)

        # --- apply
        ok("05 apply esce con 0", cmd_append(args_di()) == 0)
        raw2, recs2, _a, _b, _c = leggi_ledger(led)
        ok("06 il ledger ha 65 record", len(recs2) == 65)
        ok("07 i 64 precedenti sono byte-identici", raw2.startswith(prima))
        rec = recs2[-1]
        ok("08 l'item e' quello del 6.9", rec["item"] == ITEM_65)
        ok("09 numbering_rule dice 65", "record 65." in rec["numbering_rule"])
        ok("10 emenda 63 e 64", rec["rules"]["amends_records"] == [63, 64])
        ok("11 i conteggi restano 12/1/5", rec["rules"]["counts_unchanged"] == [12, 1, 5])
        nv = rec["new_value"]
        ok("12 il record dice che la popolazione non e' nove",
           nv["i_the_population_is_not_nine"]["file_con_match"] == 76)
        ok("13 e che Select-String ignora le maiuscole",
           "ignores case" in nv["i_the_population_is_not_nine"][
               "select_string_e_case_insensitive"])
        q = nv["ii_Q5_exists_and_was_never_collected"]
        ok("14 la soglia nel record e' quella del registro, non 0.832",
           q["threshold_value"] == 0.8320530984290949)
        ok("15 il record spiega che 0.832 e' la forma arrotondata",
           "ONE value" in q["note_on_the_rounded_form"])
        ok("16 e che Q5 compare una volta sola, nel record 1",
           "record 1" in q["present_in_the_ledger"])
        m = nv["iii_Q5_measured_and_it_holds"]
        ok("17 i numeri per regione vengono dal registro",
           m["per_region"]["NGC"]["stesso_stimatore_ai_due_lati_K"]["valore"] == 0.380761
           and m["per_region"]["SGC"]["procedura_dichiarata_lineare"]["valore"] == 0.308124)
        ok("18 il verdetto e' HOLDS", m["per_region"]["NGC"]["esito"] == "HOLDS")
        ok("19 le due procedure sono dichiarate non mescolabili",
           "not attached" in m["two_procedures_not_mixed"])
        ok("20 la causa e' dichiarata e non corretta",
           nv["v_the_cause_still_in_place"]["this_record_does_not_fix_it"] is True)
        ok("21 cio' che il record NON fa e' elencato",
           len(nv["vi_what_this_record_does_not_do"]) == 4)
        ok("22 gate53 e item12b restano non classificati, e il record lo dice",
           "gate53" in nv["vi_what_this_record_does_not_do"][0])
        ok("23 l'evidence porta gli sha dei registri letti",
           len(re.findall(r"sha256 [0-9a-f]{64}", rec["evidence"])) >= 4)
        ok("24 il reference e' ancorato", rec["reference_self_sha256"] == "a" * 64)

        # --- rifiuti
        ok("25 un secondo apply e' rifiutato (item presente)",
           cmd_append(args_di(attesi=65)) == 2)

        tutto_buono()
        ok("26 attesi sbagliati -> rifiuto", cmd_append(args_di(attesi=63)) == 2)

        tutto_buono()
        scrivi(sm, FINTA_3BIS.replace("| Q4 | a | SMENTITA | b |",
                                      "| Q4 | a | SMENTITA | b |\n| Q5 | a | x | y |"))
        ok("27 se Q5 e' GIA' nella 3-bis -> rifiuto: il record asserisce che manca",
           cmd_append(args_di()) == 2)

        tutto_buono()
        scrivi(sm, FINTA_3BIS.replace("| A12 | 26 | 39 | x | y |\n", ""))
        ok("28 gruppi diversi da 12/1/5 -> rifiuto", cmd_append(args_di()) == 2)

        tutto_buono()
        scrivi(soglie, FINTE_SOGLIE.replace(
            '    "Q4_meta_divario"',
            '    "Q5_sotto_il_tetto": {"soglia": 0.832, "verso": "<", "quantita": "B_best"},\n'
            '    "Q4_meta_divario"'))
        ok("29 se SOGLIE contiene gia' Q5 -> rifiuto: la causa dichiarata non c'e' piu'",
           cmd_append(args_di()) == 2)

        tutto_buono()
        scrivi(fonte, FINTA_FONTE.replace(
            "  Q5  R^2_cv(P(k)) resta SOTTO il tetto 0.832 dei predittori misurati.\n", ""))
        ok("30 senza la dichiarazione di Q5 nel sorgente -> rifiuto",
           cmd_append(args_di()) == 2)

        tutto_buono()
        scrivi_q5([_finto_q5("NGC", 0.317658, 0.007325, 70.2, 0.380761, 0.046725, 9.7)])
        ok("31 registro di Q5 con una sola regione -> rifiuto", cmd_append(args_di()) == 2)

        tutto_buono()
        r_ko = _finto_q5("NGC", 0.317658, 0.007325, 70.2, 0.380761, 0.046725, 9.7)
        r_ko["b_stesso_stimatore_ai_due_lati"] = None
        scrivi_q5([r_ko, _finto_q5("SGC", 0.308124, 0.005898, 88.8, 0.361249, 0.042977, 11.0)])
        ok("32 senza il denominatore che decide -> rifiuto", cmd_append(args_di()) == 2)

        tutto_buono()
        r_ko = _finto_q5("NGC", 0.90, 0.0073, 9.0, 0.90, 0.046, 1.5)
        r_ko["a_procedura_dichiarata"]["forme"][
            "ln_di_log10P_come_nel_codice"]["esito"] = "SMENTITA"
        scrivi_q5([r_ko, _finto_q5("SGC", 0.308124, 0.005898, 88.8, 0.361249, 0.042977, 11.0)])
        ok("33 se Q5 NON reggesse -> rifiuto: il record dichiara che regge",
           cmd_append(args_di()) == 2)

        tutto_buono()
        r_ko = _finto_q5("NGC", 0.317658, 0.007325, 70.2, 0.380761, 0.046725, 9.7)
        r_ko["a_procedura_dichiarata"]["forme"][
            "ln_di_log10P_come_nel_codice"]["decidibile"] = False
        scrivi_q5([r_ko, _finto_q5("SGC", 0.308124, 0.005898, 88.8, 0.361249, 0.042977, 11.0)])
        ok("34 un margine non decidibile -> rifiuto, non si arrotonda",
           cmd_append(args_di()) == 2)

        tutto_buono()
        scrivi_q5([_finto_q5("NGC", 0.317658, 0.007325, 70.2, 0.380761, 0.046725, 9.7,
                             soglia=0.832),
                   _finto_q5("SGC", 0.308124, 0.005898, 88.8, 0.361249, 0.042977, 11.0)])
        ok("35 due soglie diverse fra le regioni -> rifiuto", cmd_append(args_di()) == 2)

        tutto_buono()
        os.remove(q5)
        ok("36 registro di Q5 assente -> rifiuto con l'istruzione",
           cmd_append(args_di()) == 2)

        tutto_buono()
        scrivi_ledger(ultimo="item_altro")
        ok("37 se l'ultimo record non e' il 64 -> rifiuto", cmd_append(args_di()) == 2)

        # --- fine riga: si eredita, non si normalizza. Due regimi, entrambi provati.
        tutto_buono()                      # misto, ultima riga CRLF, come il ledger vero
        prima = open(led, "rb").read()
        e0 = analizza_eol(prima)
        ok("38a ledger misto con ultima riga CRLF: apply passa", cmd_append(args_di()) == 0)
        dopo = open(led, "rb").read()
        e1 = analizza_eol(dopo)
        ok("38b i LF isolati preesistenti non sono toccati",
           e1["lf_isolati"] == e0["lf_isolati"] == 6)
        ok("38c il nuovo fine riga e' CRLF, ereditato",
           dopo[len(prima):].endswith(CRLF) and e1["crlf"] == e0["crlf"] + 1)

        scrivi_ledger(termina=LF)          # stesso ledger, ma l'ultima riga finisce in LF
        scrivi(sm, FINTA_3BIS)
        scrivi(fonte, FINTA_FONTE)
        scrivi(soglie, FINTE_SOGLIE)
        scrivi_q5()
        prima = open(led, "rb").read()
        e0 = analizza_eol(prima)
        ok("39a ledger misto con ultima riga LF: apply passa", cmd_append(args_di()) == 0)
        dopo = open(led, "rb").read()
        e1 = analizza_eol(dopo)
        ok("39b il nuovo fine riga e' LF, ereditato",
           dopo[len(prima):].endswith(LF) and not dopo[len(prima):].endswith(CRLF))
        ok("39c i CRLF preesistenti non sono normalizzati", e1["crlf"] == e0["crlf"])
        ok("39d il controllo tiene conto del terminatore: un LF in piu' e' atteso, "
           "non un allarme", e1["lf_isolati"] == e0["lf_isolati"] + 1)

        # --- niente temporanei, niente record spezzato
        avanzi = [x for x in os.listdir(td) if x.endswith(".tmp") or ".jsonl." in x]
        ok("41 nessun temporaneo lasciato indietro", not avanzi)
        _r, recs3, _x, _y, _z = leggi_ledger(led)
        ok("42 il record appeso e' JSON valido e sta su una riga sola", len(recs3) == 65)

        tutto_buono()
        x = args_di()
        x.backup = os.path.join(td, "ledger.bak")
        ok("43 con --backup il ledger precedente e' salvato", cmd_append(x) == 0
           and os.path.isfile(x.backup))

    finally:
        shutil.rmtree(td, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="paper2_append_amend65.py",
                                description="Record 65: il censimento del 6.9 e Q5 di D6.")
    sub = p.add_subparsers(dest="comando")

    p_a = sub.add_parser("append", help="appende il record 65")
    p_a.add_argument("--ledger", required=True)
    p_a.add_argument("--reference", required=True)
    p_a.add_argument("--q5", default="results/paper2/q5_margine.jsonl")
    p_a.add_argument("--smentite", default=SMENTITE.replace("/", os.sep))
    p_a.add_argument("--fonte-q5", default=FONTE_Q5.replace("/", os.sep))
    p_a.add_argument("--fonte-soglie", default=FONTE_SOGLIE.replace("/", os.sep))
    p_a.add_argument("--attesi", type=int, required=True)
    p_a.add_argument("--self-sha", default=None)
    p_a.add_argument("--backup", default=None)
    p_a.add_argument("--dry-run", action="store_true")
    p_a.set_defaults(func=cmd_append)

    p_s = sub.add_parser("selftest", help="controlli")
    p_s.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper2_append_amend66.py — record 66: SGC_PRED risolta, e tre decisioni di protocollo.

CHE COSA REGISTRA
  1. SGC_PRED e' stata RISOLTA il 14 settembre, per la prima volta. Non era «un verdetto
     emesso fuori dal ledger», come il record 65 l'aveva classificata leggendo il codice:
     il verdetto non esisteva affatto. `gate53.jsonl` portava solo NGC, perche' il 31
     agosto `results/paper1/n10_phases_SGC.jsonl` non esisteva e lo script stampava «il
     file SGC va PRODOTTO». Gli ingressi sono comparsi il 9 settembre. E' quindi una prova
     cieca vera: la predizione e' stata scritta quando il dato non era producibile.
  2. Frazione spettrale: SMENTITA, e non marginalmente.
  3. |z| > 3: NON DECIDIBILE, non «confermata». Va nel gruppo B, fra le soglie mal poste:
     la clausola non ha mai avuto l'incertezza della quantita' testata, e z e' un rapporto
     a una dispersione stimata su 100 mock.
  4. Q5 entra in SOGLIE e lo schema del registro passa a v2. Il quinto margine e' quello
     gia' registrato dal record 65, NON una misura nuova.
  5. item12b: margine non misurabile, con la ragione — la quantita' testata e' gia' una
     dispersione su cosmologie fiduciali, e per essa non esiste un insieme di realizzazioni.
  6. Due osservazioni NUOVE, fuori dalla predizione, da non presentare come previste: il
     `nan` della deconvoluzione in SGC, e la quota spettrale diversa fra gli emisferi.

  E il limite del censimento: l'AST distingue i siti che POSSONO emettere un verdetto, non
  quelli che l'hanno emesso.

I NUMERI NON SONO SCRITTI QUI
  Vengono da results/paper2/gate53.jsonl, gate53_margini.jsonl e q5_margine.jsonl, con i
  loro sha nell'evidence. Se un registro cambia, il record cambia con lui invece di
  contraddirlo. Il record NON contiene nessun valore non finito: la serializzazione usa
  allow_nan=False e fallisce se qualcosa prova a entrare.

CANCELLI PRIMA DI COSTRUIRE
  - ledger a --attesi record, ultimo = il 65, item 66 non presente;
  - `SOGLIE` di src/paper2_d6_incertezze.py ha ancora QUATTRO voci: questo record dichiara
    la decisione, il patcher la applica DOPO;
  - gate53.jsonl ha un record SGC la cui `source` e' il file di coppie materializzato, e
    un record NGC con cui confrontare la quota spettrale;
  - gate53_margini.jsonl: frazione spettrale SMENTITA su entrambe le varianti, e |z| con
    `decidibile: false`. Se |z| fosse decidibile questo record va riscritto;
  - q5_margine.jsonl copre le due regioni;
  - nel file delle smentite i gruppi sono 12/1/5 e Q1-Q5 ci sono tutte.

USO
  python src\\paper2_append_amend66.py selftest
  python src\\paper2_append_amend66.py append --ledger src\\paper2_v1_amendments.jsonl ^
      --reference src\\paper2_v1_reference.json --attesi 65 --dry-run
"""

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

CRLF = chr(13).encode() + chr(10).encode()
LF = chr(10).encode()
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"

ITEM_PREV = "6.9/censimento_dei_verdetti_e_Q5_dichiarata_emessa_e_mai_raccolta"
ITEM_66 = "6.9/SGC_PRED_risolta_e_tre_decisioni_di_protocollo"

ATTESI_A, ATTESI_ABIS, ATTESI_B = 12, 1, 5
SMENTITE = "papers/paper2/paper2_5_5_smentite.md"
FONTE_SOGLIE = "src/paper2_d6_incertezze.py"
COPPIE = "results/paper2/coppie_fase5_SGC.jsonl"


def analizza_eol(raw):
    crlf = raw.count(CRLF)
    lf_isolati = raw.count(LF) - crlf
    termina = None if (not raw or not raw.endswith(LF)) else (CRLF if raw.endswith(CRLF) else LF)
    return {"crlf": crlf, "lf_isolati": lf_isolati, "termina": termina}


def leggi_reference(path):
    sha_file = sha256_file(path)
    with open(path, "rb") as fh:
        ref = json.loads(fh.read().decode("utf-8"))
    self_sha = ref.get("_self_sha256") if isinstance(ref, dict) else None
    if not isinstance(self_sha, str) or len(self_sha) != 64:
        raise Rifiuto("'_self_sha256' non leggibile dal reference; usa --self-sha")
    return sha_file, self_sha


def _jsonl(path):
    if not os.path.isfile(path):
        raise Rifiuto("file assente: %s" % path)
    fuori = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, linea in enumerate(fh, 1):
            s = linea.strip()
            if not s:
                continue
            try:
                fuori.append(json.loads(s))
            except json.JSONDecodeError as e:
                raise Rifiuto("riga %d di %s malformata: %s" % (i, path, e))
    return fuori


def _ultimo(recs, region, path):
    sel = [r for r in recs if r.get("region") == region]
    if not sel:
        raise Rifiuto("nessun record con region=%s in %s" % (region, path))
    return sel[-1]


# --------------------------------------------------------------------------- cancelli


def cancello_soglie(path):
    if not os.path.isfile(path):
        raise Rifiuto("sorgente assente: %s" % path)
    t = open(path, "r", encoding="utf-8").read()
    m = re.search(r"^SOGLIE\s*=\s*\{(.*?)^\}", t, re.M | re.S)
    if not m:
        raise Rifiuto("in %s non trovo il dizionario SOGLIE" % path)
    voci = sorted(set(re.findall(r'"(Q\d)[^"]*"\s*:', m.group(1))))
    if voci != ["Q1", "Q2", "Q3", "Q4"]:
        raise Rifiuto("SOGLIE contiene %s. Questo record DICHIARA la decisione di "
                      "aggiungere Q5: se e' gia' stata applicata, il record va riscritto "
                      "come constatazione." % voci)
    return {"voci": voci, "sha256": sha256_file(path)}


def cancello_smentite(path):
    if not os.path.isfile(path):
        raise Rifiuto("file delle smentite assente: %s" % path)
    t = open(path, "r", encoding="utf-8").read()
    c = {"A": len(re.findall(r"^\|\s*A(\d+)\s*\|", t, re.M)),
         "A_bis": len(re.findall(r"^\|\s*Ab(\d+)\s*\|", t, re.M)),
         "B": len(re.findall(r"^\|\s*B(\d+)\s*\|", t, re.M)),
         "sha256": sha256_file(path)}
    if (c["A"], c["A_bis"], c["B"]) != (ATTESI_A, ATTESI_ABIS, ATTESI_B):
        raise Rifiuto("gruppi: A=%d A-bis=%d B=%d, attesi %d/%d/%d"
                      % (c["A"], c["A_bis"], c["B"], ATTESI_A, ATTESI_ABIS, ATTESI_B))
    q = sorted(set(re.findall(r"^\|\s*(Q[1-5])\s*\|", t, re.M)))
    if q != ["Q1", "Q2", "Q3", "Q4", "Q5"]:
        raise Rifiuto("righe Q nella 3-bis: %s. Attese Q1-Q5: il patcher del record 65 "
                      "deve essere stato applicato." % (q or "nessuna"))
    c["Q_in_tabella"] = q
    return c


def cancello_q5(path):
    recs = _jsonl(path)
    regioni = sorted({r.get("region") for r in recs if r.get("schema") == "paper2_q5_v1"})
    if regioni != ["NGC", "SGC"]:
        raise Rifiuto("%s copre %s, attese NGC e SGC" % (path, regioni or "niente"))
    return {"sha256": sha256_file(path), "regioni": regioni, "record": len(recs)}


def cancello_gate53(path_reg, path_marg):
    reg = _jsonl(path_reg)
    sgc = _ultimo(reg, "SGC", path_reg)
    ngc = _ultimo(reg, "NGC", path_reg)
    if COPPIE.split("/")[-1] not in str(sgc.get("source", "")):
        raise Rifiuto("il record SGC dichiara source='%s': atteso il file di coppie "
                      "materializzato (%s)" % (sgc.get("source"), COPPIE))

    marg = _jsonl(path_marg)
    m = [r for r in marg
         if r.get("schema") == "paper2_gate53_margini_v1" and r.get("region") == "SGC"]
    if not m:
        raise Rifiuto("nessun record SGC in %s: eseguire prima paper2_gate53_margini.py"
                      % path_marg)
    m = m[-1]

    m1 = m["margine_1_z"]
    if m1.get("decidibile") is not False:
        raise Rifiuto("|z| risulta decidibile (margine %.4f sigma). Questo record dichiara "
                      "che NON lo e': se lo e', va riscritto."
                      % float(m1.get("margine_in_sigma", float("nan"))))
    v2 = m["margine_2_frazione_spettrale"]
    for et in ("a_solo_mock", "b_mock_e_estrazioni_desi"):
        if et not in v2:
            raise Rifiuto("variante '%s' assente dal record dei margini" % et)
        if v2[et].get("esito") != "SMENTITA":
            raise Rifiuto("la frazione spettrale risulta '%s' nella variante %s. Questo "
                          "record dichiara che e' SMENTITA su entrambe."
                          % (v2[et].get("esito"), et))

    # il nan della deconvoluzione: si verifica che ci sia, e non entra mai nel record
    sd_dec = sgc.get("sd_deconvolved")
    nan_deconv = isinstance(sd_dec, float) and math.isnan(sd_dec)
    n_mock = int(sgc["n_mock"])
    inc_rel = 100.0 / math.sqrt(2 * (n_mock - 1))
    return {
        "registro_sha256": sha256_file(path_reg),
        "margini_sha256": sha256_file(path_marg),
        "sgc": sgc, "ngc": ngc, "margini": m,
        "nan_deconvoluzione": bool(nan_deconv),
        "incertezza_relativa_sd_percento": inc_rel,
        "z_piu_meno": abs(float(sgc["z_residual"])) * inc_rel / 100.0,
    }


# ------------------------------------------------------------------------ costruzione


def costruisci(n_prima, ref_file_sha, ref_self_sha, soglie, smentite, q5, g53, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    sgc, ngc, m = g53["sgc"], g53["ngc"], g53["margini"]
    m1 = m["margine_1_z"]
    va = m["margine_2_frazione_spettrale"]["a_solo_mock"]
    vb = m["margine_2_frazione_spettrale"]["b_mock_e_estrazioni_desi"]

    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM_66,
        "key": "SGC_PRED_first_resolution_and_three_protocol_decisions",
        "json_path": "%s; checklist item 6.9; records 1, 63, 64 and 65" % SMENTITE,
        "old_value": (
            "Record 65 listed SGC_PRED among the out-of-ledger verdicts still to be "
            "classified, on the strength of the emission sites found in the source by AST. "
            "results/paper2/gate53.jsonl held only NGC."),
        "new_value": {
            "i_SGC_PRED_had_never_been_resolved_at_all": {
                "what_record_65_said": ("an out-of-ledger verdict awaiting classification, "
                                        "with no ledger record — the second half of which "
                                        "remains true"),
                "what_is_actually_the_case": (
                    "no verdict existed. On 31 Aug, when gate53 ran, "
                    "results/paper1/n10_phases_SGC.jsonl did not exist and the script "
                    "printed that the SGC file had to be PRODUCED. Its inputs appeared on "
                    "9 Sept, from the Phase 5 chain. gate53 was never re-run."),
                "limit_of_the_census_this_exposes": (
                    "the AST tells which sites CAN emit a verdict, not which ones DID. "
                    "Execution is checked against registers, not against code. The census "
                    "of record 65 stands as a census of sites; it is not a census of "
                    "verdicts produced."),
                "why_this_makes_it_a_blind_test": (
                    "the prediction was written on 31 Aug, when the datum was not even "
                    "producible. It is the only genuinely blind test in Phase 6."),
                "how_the_inputs_were_made_usable": {
                    "problem": ("load_pairs filters rows on the field `tipo`; the Phase 5 "
                                "files do not have it, because the split into two files "
                                "replaced the discriminator. Hence mock_pr=0 desi_pr=0."),
                    "what_was_done": ("src/paper2_fase5_a_coppie.py rewrites the single "
                                      "field `tipo` and nothing else: no quantity "
                                      "recomputed, no unit converted. Output %s." % COPPIE),
                    "gate_on_whether_that_is_legitimate": (
                        "the two producers were compared on NGC, where a frozen record "
                        "exists: 21 fields plus the rank reproduced at rel = 0.0, and "
                        "gate53's own gate against TARGETS_NGC passed. Only then were the "
                        "Phase 5 files used for SGC."),
                    "desi_orig_verified_not_assumed": (
                        "15122.0 was cabled in the code, not read from a file. Confirmed "
                        "in results/paper2/fase2.jsonl for SGC, and cross-checked against "
                        "the canonical 2000-mock ensemble: rank 1/2001 and a 19.2%% "
                        "deficit against the mock mean, the same shape as NGC's 1/2001 and "
                        "20.3%%."),
                },
            },
            "ii_spectral_fraction_FALSIFIED": {
                "declared": "spectral fraction within [0.70, 0.82], before the run, in SGC_PRED",
                "measured": float(sgc["spectral_fraction"]),
                "verdict": "FALSIFIED",
                "margin_above_the_upper_edge": {
                    "mocks_resampled_only_PRIMARY": {
                        "sd": float(va["sd"]),
                        "sigma": float(va["dall_estremo_superiore"]["margine_in_sigma"])},
                    "mocks_and_desi_draws_resampled": {
                        "sd": float(vb["sd"]),
                        "sigma": float(vb["dall_estremo_superiore"]["margine_in_sigma"])},
                },
                "denominator": ("bootstrap over the paired mocks, pairs resampled together. "
                                "The spectral fraction is a ratio of ensemble means and has "
                                "no per-mock version, so its dispersion is obtainable only "
                                "by resampling."),
                "not_marginal": True,
            },
            "iii_the_z_threshold_is_NOT_DECIDABLE_and_moves_to_group_B": {
                "declared": "|z_residual| > 3.0, before the run, in SGC_PRED",
                "measured_z": abs(float(sgc["z_residual"])),
                "what_the_tool_printed": ("gate53 printed CONFERMATA; the margin is %.4f "
                                          "sigma and decidibile is false"
                                          % float(m1["margine_in_sigma"])),
                "verdict": "NOT DECIDABLE — not a confirmation",
                "why": (
                    "a threshold crossed by %.2f sigma is the class record 48 already "
                    "retired for P1 of D3, reported as falsified at 0.22 sigma from its "
                    "threshold. Here the sign is reversed: a CONFIRMATION inside the noise."
                    % float(m1["margine_in_sigma"])),
                "structural_reason": (
                    "the adopted rule is that no threshold is crossed without the "
                    "uncertainty of the tested quantity declared when the rule is written. "
                    "The |z| > 3 clause never had one. z = residual / sigma_Delta, and "
                    "sigma_Delta is estimated on %d mocks, carrying a relative uncertainty "
                    "of %.1f%%: z = %.2f +- %.2f from that component alone, before the "
                    "uncertainty of the residual itself."
                    % (int(sgc["n_mock"]), g53["incertezza_relativa_sd_percento"],
                       abs(float(sgc["z_residual"])), g53["z_piu_meno"])),
                "placement": ("group B of %s — thresholds badly posed. Not nature giving "
                              "way, but the way the clause was written." % SMENTITE),
                "note_on_sd_equal_one": (
                    "the margin is in units of the mock-to-mock dispersion because z is "
                    "already a ratio to it; sd = 1 is a construction, not an assumption. "
                    "That is what makes the missing uncertainty ON z visible."),
            },
            "iv_Q5_enters_SOGLIE_and_the_register_schema_becomes_v2": {
                "decision": ("add Q5 to the SOGLIE dictionary of %s and move the record "
                             "schema to paper2_d6_incertezze_v2, with a note declaring "
                             "what changed." % FONTE_SOGLIE),
                "state_at_the_time_of_this_record": ("four entries, %s"
                                                     % ", ".join(soglie["voci"])),
                "why": ("while it holds four entries, the repetition on ensemble v2 "
                        "announced by record 1 loses Q5 again."),
                "the_fifth_margin_is_not_a_new_measurement": (
                    "it is the one already registered by record 65, from "
                    "results/paper2/q5_margine.jsonl. A run of the patched tool must not "
                    "be read as a second, independent measurement of Q5: if the numbers "
                    "differ from record 65, that is a discrepancy to explain, not a new "
                    "result."),
                "this_record_does_not_apply_it": True,
            },
            "v_item12b_margin_is_not_measurable": {
                "threshold": "excursion of frac_below_0.99 across levels < 0.005",
                "decision": "recorded with threshold, value and outcome; margin NOT MEASURED",
                "reason": (
                    "not cost. The quantity is computed on the DESI mask, and the excursion "
                    "is max - min across the AP GRID POINTS: it is already a dispersion, and "
                    "over fiducial cosmologies, not over realisations. An ensemble "
                    "denominator would need mock masks, which for this quantity do not "
                    "exist — the mocks share the survey mask by construction. Re-running is "
                    "deterministic and returns the same numbers: the information gain is "
                    "zero."),
            },
            "vi_two_new_observations_outside_the_prediction": {
                "declared_as_new_not_as_predicted": True,
                "a_deconvolution_is_impossible_in_SGC": {
                    "published_draw_sd": float(sgc["sd_draw_published"]),
                    "mock_to_mock_sd_SGC": float(sgc["gain_mock_sd"]),
                    "consequence": ("the published draw dispersion EXCEEDS the total "
                                    "mock-to-mock dispersion of SGC, so the deconvolution "
                                    "asks for the root of a negative number and returns a "
                                    "non-finite value. It worked in NGC, where the "
                                    "mock-to-mock sd is %.3f."
                                    % float(ngc["gain_mock_sd"])),
                    "with_the_exact_value_measured_in_this_run": {
                        "draw_sd": float(sgc["sd_draw_exact"]),
                        "deconvolved_sd": float(sgc["sd_deconvolved_exact"]),
                        "z": float(sgc["z_deconvolved_exact"])},
                    "to_check": ("157.0 is a PUBLISHED number. Wherever it appears in the "
                                 "manuscript as the draw dispersion, it is a value that "
                                 "cannot be used in SGC."),
                    "non_finite_never_written_here": ("the register holds a non-finite "
                                                      "value; this record states the fact "
                                                      "in words and stores no non-finite "
                                                      "number."),
                },
                "b_the_spectral_share_differs_between_hemispheres": {
                    "NGC": float(ngc["spectral_fraction"]),
                    "SGC": float(sgc["spectral_fraction"]),
                    "reading": (
                        "the declared band [0.70, 0.82] contains NGC and excludes SGC. The "
                        "two hemispheres are statistically independent (r = 0.016 on paired "
                        "realisations), so this is a measured difference, not a paired "
                        "fluctuation: in SGC the deficit is more spectral, and the "
                        "beyond-two-point residual falls to %.1f%% against %.1f%% in NGC."
                        % (100 * (1 - float(sgc["spectral_fraction"])),
                           100 * (1 - float(ngc["spectral_fraction"])))),
                    "touches_paper_1": ("the 76.3%% spectral share is a reported result "
                                        "there. This does not contradict it — that is NGC — "
                                        "but it says the figure is not "
                                        "hemisphere-independent, and it must not be quoted "
                                        "as if it were."),
                    "not_a_prediction_that_held": ("nobody predicted this. It is an "
                                                   "observation, and it is recorded as one."),
                },
            },
            "vii_what_this_record_does_not_do": [
                "it does not apply the change to SOGLIE, nor the schema bump: that is a "
                "separate patcher on a separate file",
                "it does not patch the documents: smentite, checklist rev. 3.26 and the "
                "tenth revision of paper2_stato.md follow this record, in one pass",
                "it does not change the counts 12 / 1 / 5 of the falsification groups; the "
                "placement of the |z| clause in group B is declared here and written there",
                "it does not re-run anything and does not revisit the verdict: the "
                "prediction was blind, and it is recorded as it came out",
            ],
        },
        "reason": (
            "Item 6.9 left three candidates to classify. Opening them showed that one was "
            "not a candidate at all: SGC_PRED had never been resolved, because its input "
            "did not exist when the tool ran. Resolving it required making the Phase 5 files "
            "readable by load_pairs, which was legitimate only after the two producers were "
            "shown to agree on NGC at 21 fields with rel = 0.0. The prediction then fell: "
            "the spectral fraction is falsified and not marginally, while the |z| clause "
            "turns out to be crossed by less than one sigma and therefore not decidable — "
            "the same defect record 48 retired for P1 of D3, with the sign reversed. Two "
            "facts came out that nobody had predicted, and they are recorded as "
            "observations. The remaining decisions of protocol are declared here so that "
            "the patchers that follow have something to be checked against."),
        "evidence": (
            "gate53: %s (sha256 %s), SGC record, source %s, %d mocks and %d DESI draws, "
            "desi = %s, rank %s. Gates: z_residual recomputed from residual/gain_mock_sd at "
            "rel = 0.0; 21 fields plus rank reproduced by compute() from the frozen paired "
            "file at rel = 0.0. Margins: %s (sha256 %s). Spectral fraction %.6f against "
            "[0.70, 0.82]: %.2f sigma above the upper edge with mocks resampled only "
            "(sd %.6f), %.2f sigma with the draws resampled too (sd %.6f), 20000 bootstrap "
            "draws, seed declared in the register. |z| = %.4f against 3.0: margin %.4f "
            "sigma, decidibile false, sigma_Delta = %.4f on %d mocks, relative uncertainty "
            "%.1f%%. Producer gate on NGC: 21 fields at rel = 0.0 plus gate53's own gate "
            "against TARGETS_NGC. desi_orig for SGC confirmed in fase2.jsonl and by rank "
            "1/2001 on the canonical ensemble. Q5: %s (sha256 %s), %d records, both "
            "hemispheres. SOGLIE at %s (sha256 %s): four entries, %s. Counts read from %s "
            "(sha256 %s): A=%d, A-bis=%d, B=%d, rows %s in section 3-bis."
            % ("results/paper2/gate53.jsonl", g53["registro_sha256"], sgc.get("source"),
               int(sgc["n_mock"]), int(sgc["n_desi_draws"]), sgc.get("desi"),
               sgc.get("rank"),
               "results/paper2/gate53_margini.jsonl", g53["margini_sha256"],
               float(sgc["spectral_fraction"]),
               float(va["dall_estremo_superiore"]["margine_in_sigma"]), float(va["sd"]),
               float(vb["dall_estremo_superiore"]["margine_in_sigma"]), float(vb["sd"]),
               abs(float(sgc["z_residual"])), float(m1["margine_in_sigma"]),
               float(sgc["gain_mock_sd"]), int(sgc["n_mock"]),
               g53["incertezza_relativa_sd_percento"],
               "results/paper2/q5_margine.jsonl", q5["sha256"], q5["record"],
               FONTE_SOGLIE, soglie["sha256"], ", ".join(soglie["voci"]),
               SMENTITE, smentite["sha256"], smentite["A"], smentite["A_bis"],
               smentite["B"], ", ".join(smentite["Q_in_tabella"]))),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": ("The number of an amendment is its 1-based POSITION in this file. "
                           "This is record %d." % numero),
        "rules": {
            "amends_records": [65],
            "scope_of_the_amendment": (
                "record 65 classified SGC_PRED as an out-of-ledger verdict on the strength "
                "of emission sites in the source. There was no verdict. The census itself "
                "stands; its scope was sites, not verdicts produced."),
            "counts_unchanged": [ATTESI_A, ATTESI_ABIS, ATTESI_B],
            "a_blind_test_is_recorded_as_it_came_out": (
                "SGC_PRED was written on 31 Aug, when its input was not producible. The "
                "verdict is not revisited, the parameters are not retried, and the falsified "
                "half is not repaired."),
            "a_confirmation_inside_the_noise_is_not_a_confirmation": (
                "the |z| clause is placed in group B, alongside the thresholds retired for "
                "being badly posed, not among the predictions that held."),
            "order_of_operations": (
                "this record first; then paper2_patch_documented_amendments.py from %d to "
                "%d; then freeze_verify; then the patcher on %s for Q5 and the v2 schema; "
                "then, in one pass, smentite, checklist rev. 3.26 and the tenth revision of "
                "paper2_stato.md." % (n_prima, numero, FONTE_SOGLIE)),
        },
    }


def serializza(rec):
    # allow_nan=False: se un valore non finito provasse a entrare, questo fallisce
    # invece di scrivere NaN, che non e' JSON valido.
    return json.dumps(rec, ensure_ascii=False, sort_keys=False,
                      allow_nan=False).encode("utf-8")


def cmd_append(args):
    try:
        if not os.path.isfile(args.reference):
            raise Rifiuto("reference inesistente: %s" % args.reference)
        if not os.path.isfile(args.ledger):
            raise Rifiuto("ledger inesistente: %s" % args.ledger)
        ref_file_sha, ref_self_sha = ((sha256_file(args.reference), args.self_sha)
                                      if args.self_sha else leggi_reference(args.reference))
        raw, recs, _e, _c, _l = leggi_ledger(args.ledger)
        if len(recs) != args.attesi:
            raise Rifiuto("disco=%d attesi=%d" % (len(recs), args.attesi))
        eol = analizza_eol(raw)
        if eol["termina"] is None:
            raise Rifiuto("l'ultima riga del ledger non termina con un a capo")
        if recs[-1].get("item") != ITEM_PREV:
            raise Rifiuto("l'ultimo record non e' il 65: item='%s'" % recs[-1].get("item"))
        if any(r.get("item") == ITEM_66 for r in recs):
            raise Rifiuto("item gia' presente: %s" % ITEM_66)

        soglie = cancello_soglie(args.fonte_soglie)
        smentite = cancello_smentite(args.smentite)
        q5 = cancello_q5(args.q5)
        g53 = cancello_gate53(args.gate53, args.margini)

        rec = costruisci(len(recs), ref_file_sha, ref_self_sha, soglie, smentite, q5, g53)
        try:
            b = serializza(rec)
        except ValueError as e:
            raise Rifiuto("un valore non finito ha provato a entrare nel record: %s" % e)
        if CRLF in b or LF in b:
            raise Rifiuto("il record serializzato contiene un fine riga")
        json.loads(b.decode("utf-8"))
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    sgc, ngc = g53["sgc"], g53["ngc"]
    m1 = g53["margini"]["margine_1_z"]
    va = g53["margini"]["margine_2_frazione_spettrale"]["a_solo_mock"]
    vb = g53["margini"]["margine_2_frazione_spettrale"]["b_mock_e_estrazioni_desi"]

    print("ledger     : %s" % args.ledger)
    print("record     : %d (disco ora: %d)" % (len(recs) + 1, len(recs)))
    print("SOGLIE     : %s  (quattro voci: la decisione e' dichiarata, non applicata)"
          % ", ".join(soglie["voci"]))
    print("smentite   : A=%d  A-bis=%d  B=%d, Q %s"
          % (smentite["A"], smentite["A_bis"], smentite["B"],
             ", ".join(smentite["Q_in_tabella"])))
    print("SGC_PRED   : risolta per la prima volta, source %s" % sgc.get("source"))
    print("  frazione spettrale %.6f in [0.70, 0.82] -> SMENTITA a %.2f sigma "
          "(solo mock) e %.2f sigma (con le estrazioni)"
          % (float(sgc["spectral_fraction"]),
             float(va["dall_estremo_superiore"]["margine_in_sigma"]),
             float(vb["dall_estremo_superiore"]["margine_in_sigma"])))
    print("  |z| = %.4f > 3.0 -> NON DECIDIBILE, margine %.4f sigma  (sigma_Delta %.3f "
          "su %d mock, +-%.1f%%)"
          % (abs(float(sgc["z_residual"])), float(m1["margine_in_sigma"]),
             float(sgc["gain_mock_sd"]), int(sgc["n_mock"]),
             g53["incertezza_relativa_sd_percento"]))
    print("  deconvoluzione : %s (sd pubblicata %.1f > sigma mock-to-mock %.3f); con la sd "
          "esatta %.3f viene %.3f, z = %.4f"
          % ("NON CALCOLABILE" if g53["nan_deconvoluzione"] else "calcolabile",
             float(sgc["sd_draw_published"]), float(sgc["gain_mock_sd"]),
             float(sgc["sd_draw_exact"]), float(sgc["sd_deconvolved_exact"]),
             float(sgc["z_deconvolved_exact"])))
    print("  quota spettrale: NGC %.6f (dentro la banda), SGC %.6f (fuori)"
          % (float(ngc["spectral_fraction"]), float(sgc["spectral_fraction"])))
    print("byte       : %d -> %d" % (len(raw), len(raw) + len(b) + len(eol["termina"])))

    if args.dry_run:
        print("\n[dry-run] niente scritto.")
        return 0

    nuovo = raw + b + eol["termina"]
    if args.backup:
        with open(args.backup, "wb") as fh:
            fh.write(raw)
    d = os.path.dirname(os.path.abspath(args.ledger))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=os.path.basename(args.ledger) + ".",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(nuovo)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, args.ledger)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)

    raw2, recs2, _a, _b, _c = leggi_ledger(args.ledger)
    e2 = analizza_eol(raw2)
    esiti = [
        (len(recs2) == args.attesi + 1, "conteggio %d -> %d" % (args.attesi, len(recs2))),
        (raw2.startswith(raw), "i %d record precedenti sono byte-identici" % args.attesi),
        (e2["lf_isolati"] == eol["lf_isolati"] + (1 if eol["termina"] == LF else 0),
         "i fini riga preesistenti sono intatti, il nuovo e' ereditato (%s)"
         % ("LF" if eol["termina"] == LF else "CRLF")),
        (e2["crlf"] == eol["crlf"] + (1 if eol["termina"] == CRLF else 0),
         "nessun CRLF preesistente e' stato normalizzato"),
        (recs2[-1].get("item") == ITEM_66, "l'item e' quello nuovo"),
        ("record %d." % (args.attesi + 1) in recs2[-1]["numbering_rule"], "numbering_rule"),
        (recs2[-1]["rules"]["amends_records"] == [65], "emenda il 65"),
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
    print("     poi il patcher su %s, e SOLO DOPO i documenti in un colpo." % FONTE_SOGLIE)
    return 0


# --------------------------------------------------------------------------- selftest


FINTE_SOGLIE = '''SOGLIE = {
    "Q1_quadrati": {"soglia": 0.05, "verso": "<"},
    "Q2_interazioni": {"soglia": 0.03, "verso": "<"},
    "Q3_B_sopra_mezzo": {"soglia": 0.50, "verso": ">"},
    "Q4_meta_divario": {"soglia": 0.50, "verso": ">"},
}
'''


def _finta_3bis():
    t = "# smentite\n\n"
    t += "".join("| A%d | x | y | z | w |\n" % i for i in range(1, 13))
    t += "| Ab1 | x | y | z | w |\n"
    t += "".join("| B%d | x | y | z |\n" % i for i in range(1, 6))
    t += "".join("| Q%d | a | b | c |\n" % i for i in range(1, 6))
    return t


def _finto_gate53(sf_sgc=0.8431707582648605, z=3.6648669323709337, nan=True):
    ngc = {"schema": "paper2_gate53_v1", "region": "NGC", "spectral_fraction": 0.762528,
           "gain_mock_sd": 250.479, "sd_draw_published": 157.0,
           "sd_deconvolved": 195.168, "z_residual": 6.8289, "n_mock": 100,
           "n_desi_draws": 50, "desi": 28256.0, "rank": "1/101",
           "source": "results/paper1/n10_phases_NGC.jsonl"}
    sgc = {"schema": "paper2_gate53_v1", "region": "SGC", "spectral_fraction": sf_sgc,
           "gain_mock_sd": 153.27159494890702, "residual": 561.7200000000012,
           "z_residual": z, "sd_draw_published": 157.0,
           "sd_deconvolved": float("nan") if nan else 120.0,
           "sd_draw_exact": 113.13582950757619,
           "sd_deconvolved_exact": 103.40438046724361,
           "z_deconvolved_exact": 5.4322650303769535, "n_mock": 100, "n_desi_draws": 50,
           "desi": 15122.0, "rank": "1/101", "source": COPPIE}
    return [ngc, sgc]


def _finti_margini(esito="SMENTITA", decidibile=False, m1=0.6648669323709337):
    def intervallo(sd, sup):
        return {"sd": sd, "esito": esito,
                "dall_estremo_inferiore": {"margine_in_sigma": 34.49},
                "dall_estremo_superiore": {"margine_in_sigma": sup}}
    return [{"schema": "paper2_gate53_margini_v1", "region": "SGC",
             "margine_1_z": {"valore": 3.6648669323709337, "soglia": 3.0,
                             "margine_in_sigma": m1, "decidibile": decidibile,
                             "esito": "confermata", "sd": 1.0},
             "margine_2_frazione_spettrale": {
                 "a_solo_mock": intervallo(0.004151, 5.58),
                 "b_mock_e_estrazioni_desi": intervallo(0.006034, 3.84)}}]


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

    td = tempfile.mkdtemp(prefix="amend66_")
    try:
        led = os.path.join(td, "ledger.jsonl")
        ref = os.path.join(td, "reference.json")
        sm = os.path.join(td, "smentite.md")
        soglie = os.path.join(td, "d6inc.py")
        q5 = os.path.join(td, "q5.jsonl")
        g53 = os.path.join(td, "gate53.jsonl")
        marg = os.path.join(td, "margini.jsonl")

        with open(ref, "wb") as fh:
            fh.write(json.dumps({"_self_sha256": "b" * 64}).encode("utf-8"))

        def scrivi(p, testo):
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(testo)

        def scrivi_jsonl(p, recs):
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                for r in recs:
                    fh.write(json.dumps(r) + "\n")

        def scrivi_ledger(n=65, ultimo=ITEM_PREV, termina=CRLF, lf_isolati=6):
            fuori = b""
            for i in range(1, n + 1):
                it = ultimo if i == n else "item_%d" % i
                b = json.dumps({"item": it, "n": i}).encode("utf-8")
                fuori += b + (termina if i == n else (LF if i <= lf_isolati else CRLF))
            with open(led, "wb") as fh:
                fh.write(fuori)

        def tutto_buono():
            scrivi_ledger()
            scrivi(sm, _finta_3bis())
            scrivi(soglie, FINTE_SOGLIE)
            scrivi_jsonl(q5, [{"schema": "paper2_q5_v1", "region": "NGC"},
                              {"schema": "paper2_q5_v1", "region": "SGC"}])
            scrivi_jsonl(g53, _finto_gate53())
            scrivi_jsonl(marg, _finti_margini())

        def argomenti(attesi=65, dry=False):
            x = A()
            x.ledger, x.reference, x.smentite = led, ref, sm
            x.fonte_soglie, x.q5, x.gate53, x.margini = soglie, q5, g53, marg
            x.attesi, x.dry_run = attesi, dry
            return x

        tutto_buono()
        prima = open(led, "rb").read()
        ok("01 dry-run esce con 0", cmd_append(argomenti(dry=True)) == 0)
        ok("02 dry-run non scrive nulla", open(led, "rb").read() == prima)
        ok("03 apply esce con 0", cmd_append(argomenti()) == 0)

        raw2, recs2, _a, _b, _c = leggi_ledger(led)
        rec = recs2[-1]
        ok("04 il ledger ha 66 record", len(recs2) == 66)
        ok("05 i 65 precedenti sono byte-identici", raw2.startswith(prima))
        ok("06 l'item e' quello del 66", rec["item"] == ITEM_66)
        ok("07 numbering_rule dice 66", "record 66." in rec["numbering_rule"])
        ok("08 emenda il 65", rec["rules"]["amends_records"] == [65])
        ok("09 i conteggi restano 12/1/5", rec["rules"]["counts_unchanged"] == [12, 1, 5])

        nv = rec["new_value"]
        i = nv["i_SGC_PRED_had_never_been_resolved_at_all"]
        ok("10 il record dice che nessun verdetto esisteva",
           "no verdict existed" in i["what_is_actually_the_case"])
        ok("11 e dichiara il limite del censimento: CAN emit, non DID",
           "CAN emit" in i["limit_of_the_census_this_exposes"])
        ok("12 la prova cieca e' motivata dalla data dell'ingresso",
           "not even" in i["why_this_makes_it_a_blind_test"])
        ok("13 il cancello sui due produttori e' nel record",
           "rel = 0.0" in i["how_the_inputs_were_made_usable"][
               "gate_on_whether_that_is_legitimate"])
        ok("14 desi_orig e' dichiarato verificato, non assunto",
           "1/2001" in i["how_the_inputs_were_made_usable"]["desi_orig_verified_not_assumed"])

        ii = nv["ii_spectral_fraction_FALSIFIED"]
        ok("15 la frazione spettrale e' FALSIFIED", ii["verdict"] == "FALSIFIED")
        ok("16 i due margini vengono dal registro, non scritti a mano",
           ii["margin_above_the_upper_edge"]["mocks_resampled_only_PRIMARY"]["sigma"] == 5.58
           and ii["margin_above_the_upper_edge"][
               "mocks_and_desi_draws_resampled"]["sigma"] == 3.84)
        iii = nv["iii_the_z_threshold_is_NOT_DECIDABLE_and_moves_to_group_B"]
        ok("17 |z| e' NOT DECIDABLE, non una conferma",
           iii["verdict"].startswith("NOT DECIDABLE"))
        ok("18 il record cita il precedente del 48 col segno rovesciato",
           "record 48" in iii["why"] and "reversed" in iii["why"])
        ok("19 la ragione strutturale e' la regola sulla soglia senza incertezza",
           "never had one" in iii["structural_reason"])
        ok("20 l'incertezza su z e' quantificata dai mock del registro",
           "7.1%" in iii["structural_reason"])
        ok("21 la collocazione nel gruppo B e' dichiarata", "group B" in iii["placement"])

        iv = nv["iv_Q5_enters_SOGLIE_and_the_register_schema_becomes_v2"]
        ok("22 il quinto margine e' dichiarato NON una misura nuova",
           "must not be read as a second, independent measurement" in
           iv["the_fifth_margin_is_not_a_new_measurement"]
           and "record 65" in iv["the_fifth_margin_is_not_a_new_measurement"])
        ok("23 e il record non applica la modifica",
           iv["this_record_does_not_apply_it"] is True)
        ok("24 item12b: la ragione non e' il costo",
           "not cost" in nv["v_item12b_margin_is_not_measurable"]["reason"])

        vi = nv["vi_two_new_observations_outside_the_prediction"]
        ok("25 le due osservazioni sono dichiarate nuove, non previste",
           vi["declared_as_new_not_as_predicted"] is True)
        ok("26 il 157.0 e' segnalato come numero pubblicato da verificare",
           "PUBLISHED" in vi["a_deconvolution_is_impossible_in_SGC"]["to_check"])
        ok("27 e la quota spettrale diversa fra emisferi tocca il Paper 1",
           "hemisphere-independent" in
           vi["b_the_spectral_share_differs_between_hemispheres"]["touches_paper_1"])
        ok("28 dichiarata come osservazione, non come predizione retta",
           "recorded as one" in
           vi["b_the_spectral_share_differs_between_hemispheres"]["not_a_prediction_that_held"])
        ok("29 cio' che il record NON fa e' elencato",
           len(nv["vii_what_this_record_does_not_do"]) == 4)

        # nessun valore non finito nel record, benche' il registro ne abbia uno
        testo = json.dumps(rec, allow_nan=False)
        ok("30 il record non contiene NaN, pur leggendo un registro che ne ha uno",
           "NaN" not in testo and "Infinity" not in testo)
        ok("31 e dichiara a parole che il registro ne ha uno",
           "non-finite" in vi["a_deconvolution_is_impossible_in_SGC"][
               "non_finite_never_written_here"])
        ok("32 l'evidence porta gli sha dei registri letti",
           len(re.findall(r"sha256 [0-9a-f]{64}", rec["evidence"])) >= 5)

        # rifiuti
        ok("33 un secondo apply e' rifiutato", cmd_append(argomenti(attesi=66)) == 2)
        tutto_buono()
        ok("34 attesi sbagliati -> rifiuto", cmd_append(argomenti(attesi=64)) == 2)

        tutto_buono()
        scrivi_jsonl(marg, _finti_margini(decidibile=True, m1=4.2))
        ok("35 se |z| fosse DECIDIBILE -> rifiuto: il record dichiara che non lo e'",
           cmd_append(argomenti()) == 2)

        tutto_buono()
        scrivi_jsonl(marg, _finti_margini(esito="confermata"))
        ok("36 se la frazione spettrale NON fosse smentita -> rifiuto",
           cmd_append(argomenti()) == 2)

        tutto_buono()
        g = _finto_gate53()
        g[1]["source"] = "results/paper1/n10_phases_SGC.jsonl"
        scrivi_jsonl(g53, g)
        ok("37 source diversa dal file di coppie materializzato -> rifiuto",
           cmd_append(argomenti()) == 2)

        tutto_buono()
        scrivi_jsonl(g53, [_finto_gate53()[0]])
        ok("38 senza il record SGC -> rifiuto", cmd_append(argomenti()) == 2)

        tutto_buono()
        scrivi(soglie, FINTE_SOGLIE.replace(
            '    "Q4_meta_divario"',
            '    "Q5_sotto_il_tetto": {"soglia": 0.832, "verso": "<"},\n    "Q4_meta_divario"'))
        ok("39 se SOGLIE contiene gia' Q5 -> rifiuto: la decisione e' gia' applicata",
           cmd_append(argomenti()) == 2)

        tutto_buono()
        scrivi(sm, _finta_3bis().replace("| Q5 | a | b | c |\n", ""))
        ok("40 se Q5 non e' nella 3-bis -> rifiuto: manca il patcher del 65",
           cmd_append(argomenti()) == 2)

        tutto_buono()
        scrivi_jsonl(q5, [{"schema": "paper2_q5_v1", "region": "NGC"}])
        ok("41 registro di Q5 con una sola regione -> rifiuto", cmd_append(argomenti()) == 2)

        tutto_buono()
        scrivi_ledger(ultimo="item_altro")
        ok("42 se l'ultimo record non e' il 65 -> rifiuto", cmd_append(argomenti()) == 2)

        # fine riga: due regimi
        tutto_buono()
        prima = open(led, "rb").read()
        e0 = analizza_eol(prima)
        ok("43 ledger misto con ultima riga CRLF: apply passa", cmd_append(argomenti()) == 0)
        e1 = analizza_eol(open(led, "rb").read())
        ok("44 i LF isolati preesistenti non sono toccati",
           e1["lf_isolati"] == e0["lf_isolati"] == 6)
        ok("45 il nuovo fine riga e' CRLF, ereditato", e1["crlf"] == e0["crlf"] + 1)

        tutto_buono()
        scrivi_ledger(termina=LF)
        prima = open(led, "rb").read()
        e0 = analizza_eol(prima)
        ok("46 ledger misto con ultima riga LF: apply passa", cmd_append(argomenti()) == 0)
        e1 = analizza_eol(open(led, "rb").read())
        ok("47 il nuovo fine riga e' LF, e i CRLF non sono normalizzati",
           e1["lf_isolati"] == e0["lf_isolati"] + 1 and e1["crlf"] == e0["crlf"])

        ok("48 nessun temporaneo lasciato indietro",
           not [x for x in os.listdir(td) if x.endswith(".tmp")])

        tutto_buono()
        x = argomenti()
        x.backup = os.path.join(td, "ledger.bak")
        ok("49 con --backup il ledger precedente e' salvato",
           cmd_append(x) == 0 and os.path.isfile(x.backup))

    finally:
        shutil.rmtree(td, ignore_errors=True)

    passati = sum(1 for c, _ in esiti if c)
    print("")
    print("  selftest: %d/%d" % (passati, len(esiti)))
    print("ESITO: %s" % ("CLEAN" if passati == len(esiti) else "FALLITO"))
    return 0 if passati == len(esiti) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="paper2_append_amend66.py",
                                description="Record 66: SGC_PRED risolta e tre decisioni "
                                            "di protocollo.")
    sub = p.add_subparsers(dest="comando")

    q = sub.add_parser("append")
    q.add_argument("--ledger", required=True)
    q.add_argument("--reference", required=True)
    q.add_argument("--attesi", type=int, required=True)
    q.add_argument("--gate53", default=os.path.join("results", "paper2", "gate53.jsonl"))
    q.add_argument("--margini",
                   default=os.path.join("results", "paper2", "gate53_margini.jsonl"))
    q.add_argument("--q5", default=os.path.join("results", "paper2", "q5_margine.jsonl"))
    q.add_argument("--smentite", default=SMENTITE.replace("/", os.sep))
    q.add_argument("--fonte-soglie", default=FONTE_SOGLIE.replace("/", os.sep))
    q.add_argument("--self-sha", default=None)
    q.add_argument("--backup", default=None)
    q.add_argument("--dry-run", action="store_true")
    q.set_defaults(func=cmd_append)

    q = sub.add_parser("selftest")
    q.set_defaults(func=cmd_selftest)

    a = p.parse_args(argv)
    if not getattr(a, "func", None):
        p.print_help()
        return 2
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())

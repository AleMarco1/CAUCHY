#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend63.py — appende il record 63: D6 e' chiuso, e la sua lettura di agosto
era un artefatto di classe di modelli.

Che cosa registra: la stessa classe di stimatori ai due lati (kernel ridge gaussiano), che
annulla il vantaggio misurato in agosto del polinomio su P(k); i due denominatori, con la
regola che i margini da soglia si misurano sul bootstrap delle realizzazioni e non sulle
ripetizioni della CV; la prima misura di D6 in SGC; Q1 spostata al gruppo B delle smentite;
le tre correzioni di base e di codice trovate leggendo il consumatore del cache; e il terzo
residuo di Fase 4, che dopo questo si colloca invece di restare rinviato.

I cancelli sull'append si importano da paper2_append_amend50, come per i record 59-62.

Cancelli, tutti prima di scrivere:
  1. reference leggibile, ledger a --attesi record, fine riga ereditata dall'ultima riga;
  2. l'ULTIMO record e' la chiusura della provenienza (record 62);
  3. l'item nuovo non e' gia' presente;
  4. **i numeri di questo record devono coincidere con i registri di misura**: l'ultimo
     record NGC e l'ultimo record SGC di d6bis.jsonl e di d6_incertezze.jsonl, a rel <=
     1e-12. Un record che diverge dalla propria evidenza non si appende.

Uso:
    python paper2_append_amend63.py selftest
    python paper2_append_amend63.py append --ledger src\\paper2_v1_amendments.jsonl --reference src\\paper2_v1_reference.json --attesi 62 --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

CRLF = chr(13).encode() + chr(10).encode()
LF = chr(10).encode()
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"

ITEM_PREV = "6.8/provenienza_pk_matrix_stabilita_per_riproduzione_bit_a_bit"
ITEM_63 = "6.8/D6_chiuso_stesso_stimatore_ai_due_lati_e_terzo_residuo_collocato"

TETTO_PARAM = 0.6979988567812268
TETTO_MISURATO = 0.8320530984290949

# --- i valori quotati, che devono coincidere coi registri di misura ------------
D6BIS = {
    "NGC": {"P": 0.37924253080750336, "K": 0.38076075876550064, "PK": 0.4268411552048682,
            "A3_poly": 0.3559646009029426,
            "P_sd_ens": 0.05503350227611075, "K_sd_ens": 0.04672508810184475,
            "PK_sd_ens": 0.05316585869042974,
            "K_meno_P_sigma_part": 0.08840844817317127,
            "K_meno_P_sigma_ens": 0.8024689933969004,
            "PK_meno_P_sigma_part": 4.063114483171849,
            "PK_meno_P_sigma_ens": 1.8861435041964514},
    "SGC": {"P": 0.3811445224068282, "K": 0.3612488303744278, "PK": 0.4222056542087594,
            "A3_poly": 0.35785206311664003,
            "P_sd_ens": 0.03231369890123339, "K_sd_ens": 0.04297726114507549,
            "PK_sd_ens": 0.047994533148401415,
            "K_meno_P_sigma_part": 1.7222634370725454,
            "K_meno_P_sigma_ens": 0.5807903847596653,
            "PK_meno_P_sigma_part": 4.870663635418386,
            "PK_meno_P_sigma_ens": 1.1362940131351906},
}
D6INC = {
    "NGC": {"gain_quad": 0.05045023294113125, "gain_quad_sd": 0.0015771686252411675,
            "gain_int": 0.05310718432113877,
            "C_par": 0.19661025772699597, "C_tot": 0.15114036252484525},
    "SGC": {"gain_quad": 0.050262924018415124, "gain_quad_sd": 0.001849832696677099,
            "gain_int": 0.03823430736950656,
            "C_par": 0.1698675891032491, "C_tot": 0.12939923832740957},
}
REL = 1e-12


def non_spiegato(v, tetto):
    return 1.0 - v / tetto


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


def ultimi_per_regione(path):
    """L'ultimo record di ciascuna regione in un registro di misura append-only."""
    if not os.path.isfile(path):
        raise Rifiuto("registro di misura assente: %s" % path)
    fuori = {}
    with open(path, "r", encoding="utf-8") as fh:
        for riga in fh:
            if riga.strip():
                r = json.loads(riga)
                if "region" in r:
                    fuori[r["region"]] = r
    return fuori


def confronta(nome, atteso, ottenuto):
    if ottenuto is None:
        raise Rifiuto("%s: valore assente nel registro di misura" % nome)
    rel = abs(ottenuto - atteso) / abs(atteso) if atteso else abs(ottenuto)
    if rel > REL:
        raise Rifiuto("%s: il record direbbe %.17g, il registro dice %.17g (rel %.2e)"
                      % (nome, atteso, ottenuto, rel))


def cancello_evidenza(d6bis_path, d6inc_path):
    """I numeri del record devono venire dai registri, non dalla memoria di chi scrive."""
    bis = ultimi_per_regione(d6bis_path)
    inc = ultimi_per_regione(d6inc_path)
    controlli = 0
    for reg, att in D6BIS.items():
        if reg not in bis:
            raise Rifiuto("d6bis: nessun record per %s" % reg)
        st = bis[reg]["stime"]
        for chiave in ("P", "K", "PK", "A3_poly"):
            confronta("d6bis/%s/%s" % (reg, chiave), att[chiave], st[chiave]["r2cv_media"])
            controlli += 1
        for chiave in ("P", "K", "PK"):
            confronta("d6bis/%s/%s sd_ens" % (reg, chiave), att["%s_sd_ens" % chiave],
                      st[chiave].get("sd_ensemble"))
            controlli += 1
        c = bis[reg]["confronti"]
        cb = bis[reg]["confronti_bootstrap"]
        confronta("d6bis/%s/K-P part" % reg, att["K_meno_P_sigma_part"], c["K_meno_P"]["in_sigma"])
        confronta("d6bis/%s/K-P ens" % reg, att["K_meno_P_sigma_ens"], cb["K_meno_P"]["in_sigma"])
        confronta("d6bis/%s/PK-P part" % reg, att["PK_meno_P_sigma_part"], c["PK_meno_P"]["in_sigma"])
        confronta("d6bis/%s/PK-P ens" % reg, att["PK_meno_P_sigma_ens"], cb["PK_meno_P"]["in_sigma"])
        controlli += 4
        if any(d.get("sul_bordo") and not d.get("scambiato_con_interno")
               for d in bis[reg]["bordo_griglia"].values()):
            raise Rifiuto("d6bis/%s: un iperparametro sta ancora sul bordo della griglia" % reg)
        controlli += 1
    for reg, att in D6INC.items():
        if reg not in inc:
            raise Rifiuto("d6_incertezze: nessun record per %s" % reg)
        r = inc[reg]
        confronta("d6inc/%s/gain_quad" % reg, att["gain_quad"], r["A"]["gain_quad"]["media"])
        confronta("d6inc/%s/gain_quad sd" % reg, att["gain_quad_sd"],
                  r["A"]["gain_quad"]["sd_appaiata"])
        confronta("d6inc/%s/gain_int" % reg, att["gain_int"], r["A"]["gain_int"]["media"])
        confronta("d6inc/%s/C par" % reg, att["C_par"],
                  r["C"]["base_divario_parametri"]["frazione_chiusa"])
        confronta("d6inc/%s/C tot" % reg, att["C_tot"],
                  r["C"]["base_divario_totale"]["frazione_chiusa"])
        controlli += 5
    if not inc["NGC"]["cancello_riproduzione"]["superato"]:
        raise Rifiuto("d6_incertezze/NGC: il cancello di riproduzione non risulta superato")
    controlli += 1
    return controlli


# ------------------------------------------------------------------ il record

def costruisci(n_prima, ref_file_sha, ref_self_sha, utc=None):
    numero = n_prima + 1
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    ns = {r: {k: non_spiegato(D6BIS[r][k], TETTO_PARAM if k in ("P", "A3_poly") else TETTO_MISURATO)
              for k in ("P", "K", "PK", "A3_poly")} for r in ("NGC", "SGC")}
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM_63,
        "key": "D6_closed_same_estimator_on_both_sides_and_residue_3_placed",
        "json_path": ("results/paper2/d6bis.jsonl; results/paper2/d6_incertezze.jsonl; "
                      "checklist item 6.8 and D6; records 60 and 62"),
        "old_value": (
            "D6 compared a 35-term polynomial in the seven parameters against a LINEAR regression "
            "on 12 principal components of P(k), found the polynomial ahead, and read that as P(k) "
            "failing to close the gap. Record 60 deferred residue 3 for two reasons, one of which "
            "(provenance) fell with record 62; the other was that the model sequence does not "
            "converge and the 48.3 per cent is an upper bound. All the D6 numbers were single-split "
            "values without any dispersion, and D6 had never been run on SGC."
        ),
        "new_value": {
            "i_the_august_comparison_was_an_artefact_of_the_model_class": {
                "what_was_done": ("Kernel ridge with a Gaussian kernel applied to BOTH sides: P = the "
                                  "seven parameters (ceiling 0.698), K = the 110 bins of log10 P(k) "
                                  "(ceiling 0.832), PK = both together (0.832). Same estimator, same "
                                  "partitions, paired differences."),
                "outcome": {
                    "K_minus_P_NGC_sigma_partition": D6BIS["NGC"]["K_meno_P_sigma_part"],
                    "K_minus_P_SGC_sigma_partition": D6BIS["SGC"]["K_meno_P_sigma_part"],
                    "K_minus_P_NGC_sigma_ensemble": D6BIS["NGC"]["K_meno_P_sigma_ens"],
                    "K_minus_P_SGC_sigma_ensemble": D6BIS["SGC"]["K_meno_P_sigma_ens"],
                    "sign": "opposite in the two hemispheres (+0.0015 north, -0.0199 south)",
                },
                "reading": ("With the same model class the polynomial's advantage disappears: P(k) and "
                            "the seven parameters explain the same amount, with no consistent ordering. "
                            "What August measured was the difference between a 35-term polynomial and a "
                            "linear model on 12 components, not a difference of information."),
                "the_kernel_also_beats_the_polynomial_on_the_parameter_side": (
                    "P vs A3: +0.023 in both hemispheres, 1.6 sigma (NGC) and 4.3 sigma (SGC) on the "
                    "partition dispersion. The declared polynomial sequence was truncating, so its "
                    "unexplained fraction was an upper bound obtained with the wrong instrument."),
            },
            "ii_two_denominators_and_the_rule_that_follows": {
                "the_problem": ("The dispersion across CV partitions of a FIXED cohort shrinks with the "
                                "number of repetitions, so a margin measured against it can be "
                                "manufactured by running longer; and it omits the uncertainty of having "
                                "these 2000 realisations and not others, which never shrinks."),
                "rule_adopted": ("A margin from a declared threshold is measured against the ENSEMBLE "
                                 "dispersion: a bootstrap over the 2000 realisations with folds assigned "
                                 "by the realisation of origin. The partition dispersion is reported "
                                 "beside it and never used for a verdict. Same family as the denominator "
                                 "rule of 5.1: which denominator is declared, not chosen afterwards."),
                "ratio_measured": "the ensemble sd is 2.8 to 3.8 times the partition sd in every case",
                "bootstrap_mean_is_not_the_estimate": ("a bootstrap trains on about 63 per cent unique "
                                                       "rows, so its level is biased low; only its "
                                                       "dispersion is used"),
            },
            "iii_what_is_established_and_what_is_not": {
                "established": {
                    "unexplained_by_P_and_K_together_NGC": ns["NGC"]["PK"],
                    "unexplained_by_P_and_K_together_SGC": ns["SGC"]["PK"],
                    "statement": ("About half the variance of N_H1 available to a predictor measured on "
                                  "the same realisation is a function of neither the seven cosmological "
                                  "parameters nor the dark-matter power spectrum, taken together, under a "
                                  "flexible estimator. 48.7 per cent (NGC) and 49.3 per cent (SGC), with "
                                  "ensemble dispersions of 6.4 and 5.8 percentage points."),
                },
                "NOT_established": {
                    "P_k_adds_information_beyond_the_parameters": (
                        "PK - P is +0.048 and +0.041, consistent in sign, but 1.9 and 1.1 sigma on the "
                        "ensemble denominator. Under the rule adopted here it is not decidable, and the "
                        "4.1 and 4.9 sigma on the partition denominator must not be quoted for it."),
                    "the_hemispheres_are_not_a_replication": ("same suite of 2000 simulations on both "
                                                              "sides; only the footprint changes. Their "
                                                              "agreement is expected by construction, as "
                                                              "residue 2 of record 60 already states."),
                },
                "three_limits_to_be_written_wherever_this_is_quoted": {
                    "a_estimator": ("a Gaussian kernel at n = 2000 is a wide class, not a universal one: "
                                    "'not captured by this estimator' is not 'not present'"),
                    "b_which_P_of_k": ("K is the DARK MATTER P(k) of the box at z = 0, not the two-point "
                                       "function of the field whose topology is measured. The question "
                                       "answered is narrower than 'is N_H1 a two-point statistic'"),
                    "c_the_k_range": ("47 of the 110 bins lie above Nyquist (k > 0.40212, record 62), so "
                                      "the small-scale two-point information in K is what a 128^3 grid "
                                      "can carry, not what persistence at R = 5 sees. This limit alone "
                                      "can account for part of the unexplained half"),
                },
            },
            "iv_Q1_moves_to_group_B_and_Q3_needs_its_procedure_attached": {
                "Q1": {
                    "threshold": 0.05, "verso": "<",
                    "NGC": {"value": D6INC["NGC"]["gain_quad"], "sigma_from_threshold": 0.2855},
                    "SGC": {"value": D6INC["SGC"]["gain_quad"], "sigma_from_threshold": 0.1421},
                    "decision": ("withdrawn AS A FALSIFICATION and moved to group B, the same place as the "
                                 "P1 of D3 and for the same reason: a threshold crossed by a fraction of a "
                                 "sigma, declared without the uncertainty of the tested quantity."),
                    "counts_of_5_5_change": "A: 12 -> 11, A-bis: 1, B: 5 -> 6",
                },
                "Q2": {"NGC_sigma": 4.73, "SGC_sigma": 2.00,
                       "decision": ("falsified at NGC, NOT decidable at SGC. Written as such: a "
                                    "falsification that does not replicate is not rounded up.")},
                "Q3": {"as_declared": "falsified, and it stays falsified for the procedure it was declared on",
                       "but": ("with the kernel and the ensemble denominator, K sits 2.6 sigma below 0.50. "
                               "The sentence 'P(k) explains less than half' cannot enter the manuscript as "
                               "an established fact without the procedure attached to it.")},
                "Q4": {"decision": "falsified on every base: 12.9 to 21.6 per cent against a threshold of 50"},
            },
            "v_three_defects_found_by_reading_the_consumer_of_the_cache": {
                "a_the_second_logarithm": ("the cache is already log10 P(k) (record 62) and "
                                           "paper2_compD_nonlinear.py applies np.log to it, so test B ran "
                                           "on ln(log10 P). PCA is not invariant under a non-linear "
                                           "transform, so the component basis was not the declared one. "
                                           "Both forms are now measured: the accidental one is BETTER by "
                                           "0.009 (NGC) and 0.013 (SGC), so correcting the defect lowers B "
                                           "and the conclusion does not rest on it."),
                "b_the_gap_had_two_undeclared_bases": (
                    "C_gap_closed_frac was reconstructed exactly: r2_res * (1 - R2 RAW of the linear fit) "
                    "/ (0.698 - R2 CV of the linear fit). Numerator in-sample, denominator out-of-sample, "
                    "and the 0.698 ceiling in the denominator of a predictor whose ceiling is 0.832 - which "
                    "the script's own header calls incorrect. On consistent bases the closed share is "
                    "19.7 / 17.0 per cent (parameter gap) or 15.1 / 12.9 per cent (total gap)."),
                "c_the_dtype_is_an_input": ("pk_matrix is float32 on disk and the August path computes log, "
                                            "PCA and SVD in float32. Loading it as float64 moves B by "
                                            "4.4e-08 and breaks reproduction. With the dtype preserved all "
                                            "seven frozen NGC values reproduce at rel = 0.00e+00."),
                "d_the_second_positional_join": ("P = raw[:n, :] joins the parameters to N_H1 by position, "
                                                 "the same class as pk_matrix. Tested with the same "
                                                 "permutation null and supported: observed R2cv 0.2554 "
                                                 "(NGC) against a null maximum of 0.0048 over 200 "
                                                 "permutations."),
                "e_SGC_had_never_been_run": ("D6 existed for one hemisphere only; figure F9 promises the "
                                             "decomposition per hemisphere. Both hemispheres now exist."),
            },
            "vi_residue_3_is_placed": {
                "where": ("It becomes a measured statement of Paper 2 with its three limits, not a deferred "
                          "item: about half the available variance of N_H1 is not a function of the seven "
                          "parameters nor of the box's dark-matter P(k) at z = 0, under a flexible "
                          "estimator, in both hemispheres."),
                "what_it_does_not_become": ("It is NOT a term of the 5.1 budget - not a shift of the mean "
                                            "(column A), not a factor on the dispersion (column B) - and it "
                                            "is NOT a confirmation of the beyond-two-point residual of "
                                            "Paper 1. The connection with the 1710 generators is stated as "
                                            "CONSISTENT and not as established, because limits (b) and (c) "
                                            "above bear precisely on it."),
                "the_ceiling_not_to_get_wrong": "0.832 for predictors measured on the same realisation, not 0.698",
            },
            "vii_what_this_record_does_not_do": {
                "it_does_not_confirm_the_anomaly": ("Nothing here is evidence for the physical claim of "
                                                    "M26 or Paper 1."),
                "it_does_not_close_6_2": ("the traceability item keeps its other open cases; D6 is now one "
                                          "of the closed ones, reproduced at rel = 0.00e+00"),
                "it_does_not_rewrite_the_manuscript": "the sentences above go into Paper 2 at Phase 7",
            },
        },
        "reason": (
            "D6's reading of August was an artefact of the model class: a 35-term polynomial on one side "
            "and a linear model on 12 principal components on the other. Given the same estimator the "
            "difference between P(k) and the seven parameters vanishes - 0.1 sigma at NGC, 1.7 at SGC, "
            "with opposite signs - so 'P(k) fails to close the gap' was never measured. What survives, "
            "and is now measured in both hemispheres with the uncertainty that matters, is that about "
            "half the available variance escapes both predictors together. The threshold margins are "
            "measured from here on against the bootstrap over realisations, which is 2.8 to 3.8 times "
            "wider than the partition dispersion and changes verdicts: Q1 is withdrawn as a falsification "
            "and moves to group B, Q2 falsifies at NGC and not at SGC, and Q3 keeps its verdict only with "
            "its procedure attached. Residue 3, deferred by record 60, is placed with three declared "
            "limits, of which two - the dark-matter P(k) at z = 0 and the 47 bins above Nyquist - bear "
            "directly on the beyond-two-point reading and forbid calling it established."
        ),
        "evidence": (
            "results/paper2/d6bis.jsonl (last NGC and SGC records, grid v2, no hyperparameter on the grid "
            "boundary) and results/paper2/d6_incertezze.jsonl (both hemispheres, 20 repetitions, 100 "
            "bootstraps, reproduction gate against the 26 Aug record passed at rel = 0.00e+00 on all seven "
            "values). Tools: src/paper2_d6_incertezze.py (selftest 18/18) and src/paper2_d6bis_kernel.py "
            "(selftest 19/19, which reproduces before avoiding them the two defects that matter: folds "
            "assigned to the bootstrap COPY instead of the realisation of origin, which inflates R2, and "
            "the ridge applied to the kernel instead of the resampled block, which makes the system "
            "singular). Both import their regressions from paper2_compD_nonlinear.py rather than "
            "reimplementing them. This record's numbers are gated against those two registers at rel <= 1e-12."
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": ("The number of an amendment is its 1-based POSITION in this file. "
                           "This is record %d." % numero),
        "rules": {
            "marker": "emendamento-%d-d6-chiuso" % numero,
            "amends_records": [43, 60, 62],
            "companion_document": ("checklist items 6.8 and D6; papers/paper2/paper2_residui_fase4.md; "
                                   "papers/paper2/paper2_5_5_smentite.md; paper2_stato.md"),
            "same_class_on_both_sides": ("Two predictors are compared only under the same class of models. "
                                         "A difference measured between a rich model and a poor one is a "
                                         "property of the models, not of the predictors."),
            "which_dispersion": ("A margin from a declared threshold is measured against a dispersion that "
                                 "does not shrink with the effort spent measuring it."),
            "what_this_does_not_do": ("It does not confirm the anomaly, it does not make the "
                                      "beyond-two-point reading established, and it does not turn "
                                      "PK - P into a result."),
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
        ref_file_sha, ref_self_sha = ((sha256_file(args.reference), args.self_sha) if args.self_sha
                                      else leggi_reference(args.reference))
        raw, recs, _e, _c, _l = leggi_ledger(args.ledger)
        if not all(isinstance(r, dict) for r in recs):
            raise Rifiuto("leggi_ledger non restituisce dizionari: mi fermo invece di indovinare")
        if len(recs) != args.attesi:
            raise Rifiuto("disco=%d attesi=%d" % (len(recs), args.attesi))
        eol = analizza_eol(raw)
        if eol["termina"] is None:
            raise Rifiuto("l'ultima riga del ledger non termina con un a capo")
        if recs[-1].get("item") != ITEM_PREV:
            raise Rifiuto("l'ultimo record non e' la chiusura della provenienza: item='%s'"
                          % recs[-1].get("item"))
        if any(r.get("item") == ITEM_63 for r in recs):
            raise Rifiuto("item gia' presente: %s" % ITEM_63)

        n_controlli = cancello_evidenza(args.d6bis, args.d6inc)

        rec = costruisci(len(recs), ref_file_sha, ref_self_sha)
        b = serializza(rec)
        if CRLF in b or LF in b:
            raise Rifiuto("il record serializzato contiene un fine riga")
        json.loads(b.decode("utf-8"))
    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("ledger     : %s" % args.ledger)
    print("record     : %d (disco ora: %d)" % (len(recs) + 1, len(recs)))
    print("evidenza   : %d controlli contro i registri di misura, tutti a rel <= %g"
          % (n_controlli, REL))
    print("fine riga  : %d CRLF + %d LF isolati%s" % (eol["crlf"], eol["lf_isolati"],
                                                      " (misto, preesistente)" if eol["misto"] else ""))
    print("byte       : %d -> %d" % (len(raw), len(raw) + len(b) + len(eol["termina"])))
    nv = rec["new_value"]
    print("\nnon spiegato da P e K assieme: NGC %.1f %%  SGC %.1f %%"
          % (100 * nv["iii_what_is_established_and_what_is_not"]["established"]
             ["unexplained_by_P_and_K_together_NGC"],
             100 * nv["iii_what_is_established_and_what_is_not"]["established"]
             ["unexplained_by_P_and_K_together_SGC"]))

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
    eol2 = analizza_eol(raw2)
    esiti = [
        (len(recs2) == args.attesi + 1, "conteggio %d -> %d" % (args.attesi, len(recs2))),
        (raw2.startswith(raw), "i %d record precedenti sono byte-identici" % args.attesi),
        (eol2["lf_isolati"] == eol["lf_isolati"], "la mistura di fini riga e' intatta"),
        (recs2[-1].get("item") == ITEM_63, "l'item e' quello nuovo"),
        ("record %d." % (args.attesi + 1) in recs2[-1]["numbering_rule"], "numbering_rule"),
    ]
    print()
    for c, nome in esiti:
        print(("  OK  " if c else "  KO  ") + nome)
    if not all(c for c, _ in esiti):
        return 5
    print("\nOra: python src\\paper2_patch_documented_amendments.py apply --file "
          "src\\paper2_freeze_verify.py --da %d --a %d" % (args.attesi, args.attesi + 1))
    print("     python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    return 0


# ------------------------------------------------------------------ selftest

def cmd_selftest(args=None):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "amendments.jsonl")
        ref = os.path.join(td, "reference.json")
        bis = os.path.join(td, "d6bis.jsonl")
        inc = os.path.join(td, "d6inc.jsonl")
        with open(ref, "wb") as fh:
            fh.write(json.dumps({"_self_sha256": "a" * 64}).encode("utf-8"))

        def scrivi_bis(mod=None, bordo=False):
            with open(bis, "w", encoding="utf-8", newline="\n") as fh:
                for reg, v in D6BIS.items():
                    r = {"region": reg,
                         "stime": {k: {"r2cv_media": v[k]} for k in ("P", "K", "PK", "A3_poly")},
                         "confronti": {"K_meno_P": {"in_sigma": v["K_meno_P_sigma_part"]},
                                       "PK_meno_P": {"in_sigma": v["PK_meno_P_sigma_part"]}},
                         "confronti_bootstrap": {"K_meno_P": {"in_sigma": v["K_meno_P_sigma_ens"]},
                                                 "PK_meno_P": {"in_sigma": v["PK_meno_P_sigma_ens"]}},
                         "bordo_griglia": {"P": {"sul_bordo": bordo, "scambiato_con_interno": False}}}
                    for k in ("P", "K", "PK"):
                        r["stime"][k]["sd_ensemble"] = v["%s_sd_ens" % k]
                    if mod and reg == "NGC":
                        r["stime"]["P"]["r2cv_media"] *= 1.0000001
                    fh.write(json.dumps(r) + "\n")

        def scrivi_inc(superato=True):
            with open(inc, "w", encoding="utf-8", newline="\n") as fh:
                for reg, v in D6INC.items():
                    r = {"region": reg,
                         "A": {"gain_quad": {"media": v["gain_quad"], "sd_appaiata": v["gain_quad_sd"]},
                               "gain_int": {"media": v["gain_int"]}},
                         "C": {"base_divario_parametri": {"frazione_chiusa": v["C_par"]},
                               "base_divario_totale": {"frazione_chiusa": v["C_tot"]}},
                         "cancello_riproduzione": {"superato": superato if reg == "NGC" else None}}
                    fh.write(json.dumps(r) + "\n")

        def scrivi_ledger(n, prev=True):
            with open(led, "wb") as fh:
                for i in range(n):
                    r = {"item": ITEM_PREV if (prev and i == n - 1) else "x%d" % i}
                    fh.write(json.dumps(r).encode("utf-8") + (LF if i < 6 else CRLF))

        class A:
            pass

        def a(attesi=62, dry=False, backup=None):
            x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi; x.dry_run = dry
            x.backup = backup; x.self_sha = None; x.d6bis = bis; x.d6inc = inc
            return x

        scrivi_bis(); scrivi_inc(); scrivi_ledger(62)
        raw_prima = open(led, "rb").read()

        ok("1 il dry-run passa con evidenza concorde", cmd_append(a(dry=True)) == 0)
        ok("2 e non scrive", open(led, "rb").read() == raw_prima)
        ok("3 conteggio sbagliato: rifiuto", cmd_append(a(attesi=61, dry=True)) == 2)

        scrivi_ledger(62, prev=False)
        ok("4 senza il record 62 in coda: rifiuto", cmd_append(a(dry=True)) == 2)
        scrivi_ledger(62)

        scrivi_bis(mod=True)
        ok("5 DIFETTO: un valore che diverge dal registro di 1e-7 -> rifiuto",
           cmd_append(a(dry=True)) == 2)
        scrivi_bis()

        scrivi_bis(bordo=True)
        ok("6 DIFETTO: iperparametro sul bordo non scambiato -> rifiuto", cmd_append(a(dry=True)) == 2)
        scrivi_bis()

        scrivi_inc(superato=False)
        ok("7 DIFETTO: cancello di riproduzione non superato -> rifiuto", cmd_append(a(dry=True)) == 2)
        scrivi_inc()

        os.remove(bis)
        ok("8 DIFETTO: registro di misura assente -> rifiuto", cmd_append(a(dry=True)) == 2)
        scrivi_bis()

        ok("9 append: esito 0", cmd_append(a()) == 0)
        raw2, recs2, _e, _c, _l = leggi_ledger(led)
        ok("10 il conteggio cambia: 62 -> 63", len(recs2) == 63)
        ok("11 i 62 precedenti sono byte-identici", raw2.startswith(raw_prima))
        ok("12 la mistura di fini riga e' intatta",
           analizza_eol(raw2)["lf_isolati"] == analizza_eol(raw_prima)["lf_isolati"])
        ok("13 numbering_rule dice 63", "record 63." in recs2[-1]["numbering_rule"])
        ok("14 secondo append rifiutato", cmd_append(a(attesi=63)) == 2)

        nv = recs2[-1]["new_value"]
        est = nv["iii_what_is_established_and_what_is_not"]
        ok("15 il non spiegato e' calcolato, non scritto a mano",
           abs(est["established"]["unexplained_by_P_and_K_together_NGC"]
               - (1 - D6BIS["NGC"]["PK"] / TETTO_MISURATO)) < 1e-12)
        ok("16 PK-P e' dichiarato NON stabilito",
           "not decidable" in est["NOT_established"]["P_k_adds_information_beyond_the_parameters"])
        ok("17 i tre limiti ci sono tutti", len(est["three_limits_to_be_written_wherever_this_is_quoted"]) == 3)
        ok("18 Q1 passa al gruppo B con i conteggi",
           "A: 12 -> 11" in nv["iv_Q1_moves_to_group_B_and_Q3_needs_its_procedure_attached"]["Q1"]["counts_of_5_5_change"])
        ok("19 Q2 non si arrotonda",
           "not replicate" in nv["iv_Q1_moves_to_group_B_and_Q3_needs_its_procedure_attached"]["Q2"]["decision"]
           or "does not replicate" in nv["iv_Q1_moves_to_group_B_and_Q3_needs_its_procedure_attached"]["Q2"]["decision"])
        ok("20 il doppio logaritmo e' registrato col suo verso",
           "lowers B" in nv["v_three_defects_found_by_reading_the_consumer_of_the_cache"]["a_the_second_logarithm"])
        ok("21 il residuo 3 e' collocato ma non conferma il due punti",
           "CONSISTENT and not as established" in nv["vi_residue_3_is_placed"]["what_it_does_not_become"])
        ok("22 emenda 43, 60 e 62", recs2[-1]["rules"]["amends_records"] == [43, 60, 62])
        ok("23 i cancelli importati sono quelli del 50",
           sys.modules["paper2_append_amend50"].sha256_file is sha256_file)

    passati = sum(1 for _, c in controlli if c)
    print()
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print("selftest: %d/%d" % (passati, len(controlli)))
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_a = sub.add_parser("append")
    p_a.add_argument("--ledger", required=True)
    p_a.add_argument("--reference", required=True)
    p_a.add_argument("--attesi", type=int, default=62)
    p_a.add_argument("--d6bis", default="results/paper2/d6bis.jsonl")
    p_a.add_argument("--d6inc", default="results/paper2/d6_incertezze.jsonl")
    p_a.add_argument("--self-sha", default=None, dest="self_sha")
    p_a.add_argument("--dry-run", action="store_true")
    p_a.add_argument("--backup", default=None)
    p_a.set_defaults(func=cmd_append)
    p_t = sub.add_parser("selftest")
    p_t.set_defaults(func=cmd_selftest)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

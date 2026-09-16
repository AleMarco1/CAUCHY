#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_append_amend61_62.py — appende DUE record: l'input hash del kref (61) e la
chiusura della provenienza di `pk_matrix` (62).

Perche' due. Il record 62 e' la chiusura: codice scrivente, semantica e ordine delle
righe, stabiliti riproducendo tre righe del cache bit a bit. Il record 61 esiste perche'
`results/phase7_pk_nwlh_kref.npz` e' un file NUOVO con estensione `.npz` sotto
`results\\`: la stessa condizione che l'item 0.13 aveva rilevato per il cache, cioe'
fuori dalle estensioni del tier `records`. Per il cache la copertura e' il record 5,
`type: "input_hash"`, e per il kref deve essere la stessa cosa. Un digest che il gate
non legge non rende citabile il file.

I due record si appendono in UNA scrittura atomica: non esiste uno stato in cui il 61
c'e' e il 62 no.

I cancelli sull'append si importano da paper2_append_amend50, come per i record 59 e 60.

Cancelli, tutti prima di scrivere:
  1. il reference esiste e i suoi due sha sono leggibili;
  2. il ledger ha esattamente --attesi record e nessun LF isolato;
  3. l'ULTIMO record e' la chiusura della Fase 5 (record 60): senza quello, rifiuto;
  4. nessuno dei due item nuovi e' gia' presente (idempotenza);
  5. il cache E il kref sul disco hanno gli sha dichiarati qui: se uno dei due e'
     cambiato, la prova di riproduzione non vale piu' e l'append e' rifiutato;
  6. la geometria del record si RICALCOLA dal kref (n_k, Nyquist, bin sopra Nyquist,
     rapporto con la diagonale), non si scrive a mano.

Uso:
    python paper2_append_amend61_62.py selftest
    python paper2_append_amend61_62.py append --ledger src\\paper2_v1_amendments.jsonl --reference src\\paper2_v1_reference.json --attesi 60 --dry-run
    python paper2_append_amend61_62.py append --ledger src\\paper2_v1_amendments.jsonl --reference src\\paper2_v1_reference.json --attesi 60
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paper2_append_amend50 import sha256_file, leggi_ledger, Rifiuto  # noqa: E402

CRLF = chr(13).encode() + chr(10).encode()
DOCUMENT = "paper2_prereg_v1.md v1.1 — version DOI 10.5281/zenodo.22148444"

ITEM_PREV = "5.1-5.6/fase_5_chiusa_denominatori_dichiarati_e_quattro_correzioni_al_paper_1"
ITEM_61 = "0.13/6.8-kref/input_hash_phase7_pk_nwlh_kref"
ITEM_62 = "6.8/provenienza_pk_matrix_stabilita_per_riproduzione_bit_a_bit"

# --- gli oggetti, con i loro digest dichiarati -------------------------------
CACHE_PATH = "results/phase7_pk_nwlh_cache.npz"
CACHE_SHA = "d148f63ff9c4fbc5570d69ef6cf15bfc9dda543a5923950eafa5b01f394a6a7c"
CACHE_BYTES = 880272
CACHE_MTIME = "2026-06-05T20:48:52"

KREF_NAME = "phase7_pk_nwlh_kref"
KREF_PATH = "results/paper2/phase7_pk_nwlh_kref.npz"
KREF_SHA = "92679cbd4ced4c405e46ca2e111c9edd981eccf3c01f4a73840fc047639e7b14"

PARAMS_PATH = "data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt"
PARAMS_SHA = "bf0519c623cc262a3e58749036a30fd0c3b828945ea948b37acdf5f2718d9e3e"

# --- geometria della griglia, per il ricalcolo -------------------------------
BOX = 1000.0
NGRID = 128

# --- esiti misurati, dai run registrati in logs/prov_pk.jsonl ----------------
RIGHE_RIPRODOTTE = (0, 1000, 1999)
RIEMPIMENTO = {"soglia": 1e-5, "rel_minima": 0.017968259987315372, "riga_minima": 1859,
               "mediana_rel": 0.11804213310780977, "sospette": 0}
ALLINEAMENTO = {
    "nperm": 1000, "seed": 20260912,
    "bin_0": {"r2": 0.8968261307781457, "nullo_max": 0.012026824130497382},
    "media_colonne": {"r2": 0.8993426284450239, "nullo_max": 0.012607525073411119},
    "inclinazione": {"r2": 0.7655500750338788, "nullo_max": 0.011491829908363282},
    "beta_media_sigma8": 0.8511271752770738,
    "beta_bin0_omega_m": -0.857458092692038,
    "beta_incl_omega_m": -0.8028936484925191,
    "beta_incl_n_s": -0.2032219249604443,
    "beta_media_w0": -7.390352446684852e-05,
}
GIT = {"file": "src/phase7_r53_robustness.py", "commit": "8a2e140", "data": "2026-07-02"}


# ------------------------------------------------------------------ ricalcolo

def geometria_da_kref(kref_path):
    """Tutto cio' che del record e' geometria si legge dal kref, non dal testo."""
    with np.load(kref_path, allow_pickle=False) as f:
        if "k3D" not in f.files:
            raise Rifiuto("il kref non contiene 'k3D' (chiavi: %s)" % list(f.files))
        k = np.asarray(f["k3D"], dtype=np.float64)
        sorgente = str(f["sorgente"][0]) if "sorgente" in f.files else None
    if k.ndim != 1 or k.size < 2 or not np.all(np.diff(k) > 0):
        raise Rifiuto("la griglia k non e' un asse crescente")
    k_f = 2.0 * math.pi / BOX
    k_nyq = math.pi * NGRID / BOX
    sopra = int(np.count_nonzero(k > k_nyq))
    return {
        "n_k": int(k.size),
        "k_min": float(k[0]),
        "k_max": float(k[-1]),
        "k_fundamental": k_f,
        "k_nyquist": k_nyq,
        "primo_bin_in_k_f": float(k[0] / k_f),
        "bins_above_nyquist": sopra,
        "fraction_above_nyquist": float(sopra) / float(k.size),
        "k_max_over_k_nyquist": float(k[-1] / k_nyq),
        "ratio_to_cube_diagonal": float(k[-1] / k_nyq / math.sqrt(3.0)),
        "source_string": sorgente,
    }


def analizza_eol(raw):
    """Distribuzione delle fini riga, e quella da ereditare. Non normalizza nulla."""
    crlf = raw.count(CRLF)
    lf_isolati = raw.count(b"\n") - crlf
    if not raw or not raw.endswith(b"\n"):
        termina = None
    else:
        termina = CRLF if raw.endswith(CRLF) else b"\n"
    return {"crlf": crlf, "lf_isolati": lf_isolati, "termina": termina,
            "misto": bool(crlf and lf_isolati)}


def leggi_reference(path):
    sha_file = sha256_file(path)
    with open(path, "rb") as fh:
        ref = json.loads(fh.read().decode("utf-8"))
    self_sha = ref.get("_self_sha256") if isinstance(ref, dict) else None
    if not isinstance(self_sha, str) or len(self_sha) != 64:
        raise Rifiuto(
            "'_self_sha256' non leggibile dal reference (chiavi di primo livello: %s). "
            "Passalo con --self-sha se vive altrove."
            % (sorted(ref)[:12] if isinstance(ref, dict) else type(ref).__name__)
        )
    return sha_file, self_sha


# ------------------------------------------------------------------- i record

def record_61(n_prima, ref_file_sha, ref_self_sha, geo, kref_bytes, utc):
    return {
        "document": DOCUMENT,
        "type": "input_hash",
        "utc": utc,
        "item": ITEM_61,
        "name": KREF_NAME,
        "path": KREF_PATH,
        "bytes": int(kref_bytes),
        "sha256": KREF_SHA,
        "reason": (
            "The k axis of the 110 columns of pk_matrix did not exist anywhere. The writer code "
            "(phase7_r53_robustness.py::_compute_pk_matrix) sets k_ref from the k3D of the first "
            "successful realisation and never saves it, so the cache carries a single member and no "
            "axis. This file is that axis, regenerated from realisation %d and frozen here. It is "
            "registered as an input hash for the same reason the cache was in item 0.13: extension "
            ".npz under results/, outside the extensions of the records tier, therefore invisible to "
            "the freeze unless declared. Item string differs from '0.13' because the duplicate-item "
            "gate would otherwise refuse the append against record 5."
            % RIGHE_RIPRODOTTE[0]
        ),
        "produced_by": "src/paper2_prov_pk_riproduci.py riproduci --out-kref",
        "geometry_recomputed_from_this_file": geo,
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": ("The number of an amendment is its 1-based POSITION in this file. "
                           "This is record %d." % (n_prima + 1)),
    }


def record_62(n_prima, ref_file_sha, ref_self_sha, geo, utc):
    a = ALLINEAMENTO
    return {
        "document": DOCUMENT,
        "type": "protocol",
        "utc": utc,
        "item": ITEM_62,
        "key": "provenance_of_pk_matrix_established_by_bit_for_bit_reproduction",
        "json_path": ("%s; %s; %s; checklist item 6.8 (component D6); records 5 and 60; "
                      "logs/prov_pk.jsonl" % (CACHE_PATH, KREF_PATH, PARAMS_PATH)),
        "old_value": (
            "Record 60 deferred residue 3 to Phase 6 with two reasons: the model sequence does not "
            "converge, and 'the provenance of pk_matrix is not established, so tests B and C are not "
            "interpretable'. The second reason is now removed. The first is not."
        ),
        "new_value": {
            "i_what_provenance_was_taken_to_mean": {
                "statement": (
                    "Four declarations, none of which implies the others: integrity (the file has not "
                    "changed), writing code (which script, in which state, ran the savez), semantics "
                    "(what quantity, in what units, from which field), row alignment (row i is "
                    "realisation i of the parameter table, not an assumption)."
                ),
                "why_the_digest_was_not_enough": (
                    "A frozen digest proves integrity only. The failure mode of Phase 6 is declaring a "
                    "number traceable because a file exists that contains it; the per_mock and n6 "
                    "precedent of this same week is that class of error, and it lives in declaration "
                    "four, not in declaration one."
                ),
            },
            "ii_integrity": {
                "cache_sha256": CACHE_SHA,
                "cache_bytes": CACHE_BYTES,
                "cache_mtime": CACHE_MTIME,
                "matches_record_5": True,
                "note": ("Byte-identical to the hash frozen under item 0.13 on 2026-08-26, which was "
                         "itself taken 82 days after the file was written."),
            },
            "iii_git_cannot_date_the_writer": {
                "finding": ("git log --follow on %s returns a single commit, %s of %s, one month AFTER "
                            "the cache mtime of %s. There is no history before it: the release commit "
                            "imported the file already written."
                            % (GIT["file"], GIT["commit"], GIT["data"], CACHE_MTIME)),
                "consequence": ("No git command can show whether HEAD is the code that ran on 5 June. "
                                "Version control was not able to close this point, and only "
                                "reproduction was."),
            },
            "iv_the_proof_reproduction_of_three_rows": {
                "rule_declared_before_running": (
                    "Indices 0, 1000, 1999. Bit-for-bit on all three closes declarations 2, 3 and 4 "
                    "together; rel <= 1e-6 closes them with a library-version note; anything larger "
                    "means provenance is not reconstructible, and then the second exit of P1-2 applies: "
                    "declare it and REMOVE tests B and C, not keep them with a caveat."
                ),
                "outcome": "bit-for-bit on all three rows, rel_max = 0.0",
                "indices": list(RIGHE_RIPRODOTTE),
                "code_path": ("src/phase7_r53_robustness.py::_compute_pk_matrix at HEAD, field "
                              "df_m_128_PCS_z=0.npy, box 1000, axis=0, MAS='CIC', threads=1, "
                              "log10(clip(Pk[:,0], 1e-10)) cast to float32"),
                "what_it_closes": ("Declaration 2 (HEAD IS the code of 5 June), declaration 3 (the "
                                   "semantics read in the code was the semantics executed) and "
                                   "declaration 4 (row i is realisation i) in one measurement."),
                "tool": "src/paper2_prov_pk_riproduci.py, selftest 21/21, cache never opened for writing",
            },
            "v_row_alignment_also_has_a_structural_argument": {
                "structural": ("_compute_pk_matrix does not glob: it iterates for i in range(2000) over "
                               "NWLH_DIR/str(i)/df_m_128_PCS_z=0.npy, so the lexicographic ordering "
                               "0, 1, 10, 100 that produced the per_mock and n6 errors cannot arise here."),
                "statistical": {
                    "rule": ("declared before the numbers: the join is supported only if the observed "
                             "R^2 falls outside the ENTIRE support of a permutation null"),
                    "nperm": a["nperm"], "seed": a["seed"],
                    "bin_0": a["bin_0"], "media_colonne": a["media_colonne"],
                    "inclinazione_primo_meno_ultimo": a["inclinazione"],
                    "outcome": "outside the support for all three summaries, by about two orders of magnitude",
                    "coefficients_are_physically_coherent": {
                        "sigma_8_on_the_column_mean": a["beta_media_sigma8"],
                        "Omega_m_on_the_largest_scale_bin": a["beta_bin0_omega_m"],
                        "Omega_m_on_the_tilt": a["beta_incl_omega_m"],
                        "n_s_on_the_tilt": a["beta_incl_n_s"],
                        "w0_on_the_column_mean": a["beta_media_w0"],
                        "reading": ("amplitude goes with sigma_8, shape with Omega_m and n_s, and w0 is "
                                    "invisible - which is D4 seen from another direction. Descriptive "
                                    "support, declared as such, not a second gate."),
                    },
                },
                "params_file_sha256": PARAMS_SHA,
            },
            "vi_the_mean_pk_fill_did_not_fire": {
                "mechanism": ("The writer replaces a failed realisation with the MEAN of the successful "
                              "ones: pk_matrix = np.array([x if x is not None else mean_pk for x in "
                              "pk_list]). In the file such a row is indistinguishable from a datum, and "
                              "any R^2 including it is attenuated."),
                "duplicate_test": "0 duplicate rows over 2000",
                "single_fill_test": {
                    "why_it_was_needed": ("The duplicate test only sees a fill if there are at least two: "
                                          "a single fill has no twin and is a unique row. Each row was "
                                          "therefore compared with the mean of the other 1999."),
                    "threshold": RIEMPIMENTO["soglia"],
                    "closest_row": RIEMPIMENTO["riga_minima"],
                    "closest_rel": RIEMPIMENTO["rel_minima"],
                    "median_rel": RIEMPIMENTO["mediana_rel"],
                    "rows_flagged": RIEMPIMENTO["sospette"],
                },
                "conclusion": ("All 2000 rows are their own realisation. The clip at 1e-10 did not fire "
                              "either: the minimum of the matrix is 2.8785, not -10."),
            },
            "vii_three_things_that_change_the_text_not_the_numbers": {
                "a_it_is_log10_P_not_P": (
                    "The cache stores log10 of P(k). Checklist item D6 says 'regression on P(k)'. For R^2 "
                    "the base of the logarithm is irrelevant, being a multiplicative constant; the "
                    "logarithm itself is not. The manuscript must write what was executed."
                ),
                "b_MAS_declared_does_not_match_the_field_name": (
                    "The field is df_m_128_PCS_z=0.npy and the code passes MAS='CIC', so Pylians "
                    "deconvolves the wrong assignment window. The error is a per-k factor identical in "
                    "every row, so it cancels in any R^2 with fixed weights on the columns: NOT "
                    "consequential for D5 or D6. It IS consequential for any sentence quoting a value or "
                    "a shape of P(k) from this cache, or comparing it with an external P(k), and it is "
                    "largest exactly where the above-Nyquist bins are."
                ),
                "c_part_of_the_k_axis_is_above_nyquist": {
                    "recomputed_from_kref": geo,
                    "reading": ("Those bins are corner modes, anisotropically sampled and with the "
                                "assignment window at its largest. As PREDICTORS they remain functions "
                                "of the two-point content of the field, so test B is legitimate; as "
                                "MEASUREMENTS of P(k) they are not, and no k-localised claim in that "
                                "range is defensible. The ratio k_max/k_Nyq reproduces the cube diagonal "
                                "to better than half a per cent, which is an independent confirmation of "
                                "N=128 and L=1000 taken from the file and not from the code."),
                },
            },
            "viii_what_this_record_does_not_do": {
                "D6_still_does_not_converge": ("Record 60 gave D6 two reserves. One falls. The model "
                                               "sequence still does not converge and the 48.3 per cent "
                                               "remains an UPPER BOUND, not a measurement. Interpretable "
                                               "is not the same as converged."),
                "residue_3_stays_out": ("The 62.7 per cent (NGC) and 60.3 per cent (SGC) still do not "
                                        "enter the 5.1 budget as a term and do not enter the discussion "
                                        "as a result. Nothing here makes any number about them quotable "
                                        "today."),
                "the_ceiling": "For predictors measured on the same realisation the ceiling is 0.832, not 0.698.",
                "it_does_not_confirm_the_anomaly": ("Establishing where a file came from is not evidence "
                                                    "for a physical claim, and nothing here should be read "
                                                    "as such."),
                "provenance_of_the_cache_is_not_provenance_of_the_suite": ("What is established is that the "
                                                                           "cache is the log10 P(k) of the "
                                                                           "nwLH fields as computed by that "
                                                                           "code. The correctness of the "
                                                                           "fields themselves is not in "
                                                                           "question here and was not tested."),
            },
        },
        "reason": (
            "The provenance of pk_matrix, the second of the two reserves on D6, is established by "
            "reproducing three rows of the cache from the code at HEAD, bit for bit, at declared "
            "indices. Git could not do it: the only commit touching the writer is one month later than "
            "the file. The reproduction closes the writing code, the semantics and the row alignment "
            "together, and it yields the k axis the cache never contained, now frozen as record %d. "
            "Three findings come with it, all textual and none consequential for the R^2: the cache is "
            "log10 P and not P, the declared mass-assignment window does not match the field name, and "
            "part of the k axis lies above Nyquist. The mean_pk fill, which would have attenuated every "
            "R^2 silently, did not fire - checked also in the single-row form that the duplicate test "
            "cannot see. D6's first reserve stands: the model sequence does not converge and the 48.3 "
            "per cent is still an upper bound." % (n_prima + 1)
        ),
        "evidence": (
            "logs/prov_pk.jsonl, three records: inspection (integrity CONFIRMED against record 5), "
            "alignment (nperm=1000, seed=20260912, R^2 outside the whole null support on three "
            "summaries), reproduction (rel_max = 0.0 on rows 0, 1000, 1999, cache sha unchanged before "
            "and after). Tools: src/paper2_prov_pk.py (selftest 51/51, read-only, sha and mtime "
            "re-verified after every read) and src/paper2_prov_pk_riproduci.py (selftest 21/21, refuses "
            "to overwrite the kref, fails explicitly if Pylians3 is missing rather than falling back to "
            "the one-bin scipy branch). Code read: src/phase7_r53_robustness.py lines 229-249 and "
            "324-370. Geometry in this record recomputed from %s at append time."
            % KREF_PATH
        ),
        "reference_file": "src/paper2_v1_reference.json",
        "reference_file_sha256": ref_file_sha,
        "reference_self_sha256": ref_self_sha,
        "numbering_rule": ("The number of an amendment is its 1-based POSITION in this file. "
                           "This is record %d." % (n_prima + 1)),
        "rules": {
            "marker": "emendamento-%d-provenienza-pk-matrix" % (n_prima + 1),
            "amends_records": [5, 60],
            "companion_document": ("checklist item 6.8; paper2_stato.md; papers/paper2/"
                                   "paper2_residui_fase4.md (residue 3); logs/prov_pk.jsonl"),
            "a_digest_is_not_a_provenance": ("Integrity and provenance are separate declarations. For a "
                                             "number to be traceable it is not enough that a file "
                                             "containing it exists and is unchanged: the file must be "
                                             "reproducible from the code being cited."),
            "what_this_does_not_do": ("It does not close D6, it does not place residue 3, and it does not "
                                      "make the 48.3 per cent a measurement."),
            "line_endings_of_this_ledger_are_mixed_and_stay_mixed": (
                "The ledger carries LF on its first six records and CRLF from there on. These two "
                "records inherit the terminator of the last line, CRLF, and the file is NOT "
                "normalised: rewriting the endings would change bytes of records already appended, "
                "which is what append-only forbids. Same decision as F3.17 on key ordering - it is "
                "recorded, not made uniform."),
        },
    }


# --------------------------------------------------------------------- append

def costruisci(n_prima, ref_file_sha, ref_self_sha, geo, kref_bytes, utc=None):
    utc = utc or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    r61 = record_61(n_prima, ref_file_sha, ref_self_sha, geo, kref_bytes, utc)
    r62 = record_62(n_prima + 1, ref_file_sha, ref_self_sha, geo, utc)
    return r61, r62


def serializza(rec):
    """Chiavi NON riordinate: dal record 50 in avanti la convenzione e' l'ordine di inserimento."""
    return json.dumps(rec, ensure_ascii=False, sort_keys=False).encode("utf-8")


def cmd_append(args):
    try:
        if not os.path.isfile(args.reference):
            raise Rifiuto("reference inesistente: %s" % args.reference)
        if not os.path.isfile(args.ledger):
            raise Rifiuto("ledger inesistente: %s" % args.ledger)

        ref_file_sha, ref_self_sha = (
            (sha256_file(args.reference), args.self_sha) if args.self_sha
            else leggi_reference(args.reference)
        )

        raw, recs, _eol, _crlf, _lf = leggi_ledger(args.ledger)
        if not all(isinstance(r, dict) for r in recs):
            raise Rifiuto("leggi_ledger non restituisce record come dizionari: questo appender "
                          "non sa leggere il ledger e si ferma invece di indovinare")
        if len(recs) != args.attesi:
            raise Rifiuto("disco=%d attesi=%d" % (len(recs), args.attesi))

        # Fine riga: si EREDITA da quella dell'ultima riga e non si normalizza il file.
        # Il ledger e' misto dai primi record; riscriverlo cambierebbe byte di record
        # gia' appesi, che e' esattamente cio' che l'append-only vieta. Stessa forma
        # della decisione F3.17 sull'ordine delle chiavi: si registra, non si uniforma.
        eol = analizza_eol(raw)
        if eol["termina"] is None:
            raise Rifiuto("l'ultima riga del ledger non termina con un a capo: un append "
                          "incollerebbe due record")
        if recs[-1].get("item") != ITEM_PREV:
            raise Rifiuto("l'ultimo record non e' la chiusura della Fase 5: item='%s'"
                          % recs[-1].get("item"))
        for it in (ITEM_61, ITEM_62):
            if any(r.get("item") == it for r in recs):
                raise Rifiuto("item gia' presente nel ledger: %s" % it)

        kref_norm = args.kref.replace("\\", "/")
        if kref_norm.startswith("results/") and kref_norm.count("/") == 1:
            raise Rifiuto(
                "il kref non va nella radice di results/: quel percorso cade DENTRO le regole "
                "del tier features, e il freeze lo segnala come file extra (due FAIL su "
                "C_regole_riproducono_n_files e C_file_fuori_manifest_altrove). Va in "
                "results/paper2/, la directory dei manifest, che il controllo esenta."
            )

        for path, sha, nome in ((args.cache, CACHE_SHA, "cache"), (args.kref, KREF_SHA, "kref")):
            if not os.path.isfile(path):
                raise Rifiuto("%s inesistente: %s" % (nome, path))
            got = sha256_file(path)
            if got != sha:
                raise Rifiuto("%s cambiato: sha su disco %s, dichiarato %s. La prova di "
                              "riproduzione non vale piu'." % (nome, got, sha))

        geo = geometria_da_kref(args.kref)
        if geo["n_k"] != args.n_k_atteso:
            raise Rifiuto("il kref ha %d bin, il cache ne ha %d" % (geo["n_k"], args.n_k_atteso))

        r61, r62 = costruisci(len(recs), ref_file_sha, ref_self_sha, geo,
                              os.path.getsize(args.kref))
        b61, b62 = serializza(r61), serializza(r62)
        for b in (b61, b62):
            if CRLF in b or b"\n" in b:
                raise Rifiuto("un record serializzato contiene un fine riga")
            json.loads(b.decode("utf-8"))  # rileggibile

    except Rifiuto as e:
        print("RIFIUTO: %s" % e, file=sys.stderr)
        return 2

    print("ledger    : %s" % args.ledger)
    print("record    : %d e %d (disco ora: %d)" % (len(recs) + 1, len(recs) + 2, len(recs)))
    print("kref      : %d bin, %d sopra Nyquist (%.1f %%), k_max/k_Nyq = %.5f"
          % (geo["n_k"], geo["bins_above_nyquist"], 100.0 * geo["fraction_above_nyquist"],
             geo["k_max_over_k_nyquist"]))
    print("fine riga : %d CRLF + %d LF isolati%s; i due record nuovi usano %s"
          % (eol["crlf"], eol["lf_isolati"],
             " (misto, preesistente: non si normalizza)" if eol["misto"] else "",
             "CRLF" if eol["termina"] == CRLF else "LF"))
    print("byte      : %d -> %d" % (len(raw), len(raw) + len(b61) + len(b62) + 2 * len(eol["termina"])))
    if args.dry_run:
        print("\n--- record %d ---" % (len(recs) + 1))
        print(json.dumps(r61, ensure_ascii=False, indent=2)[:2000])
        print("\n--- record %d (estratto) ---" % (len(recs) + 2))
        print(json.dumps(r62["new_value"]["vii_three_things_that_change_the_text_not_the_numbers"],
                         ensure_ascii=False, indent=2)[:2000])
        print("\n[dry-run] niente scritto.")
        return 0

    nuovo = raw + b61 + eol["termina"] + b62 + eol["termina"]
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
    atteso_crlf = eol["crlf"] + (2 if eol["termina"] == CRLF else 0)
    atteso_lf = eol["lf_isolati"] + (0 if eol["termina"] == CRLF else 2)
    esiti = [
        (len(recs2) == args.attesi + 2, "conteggio %d -> %d" % (args.attesi, len(recs2))),
        (raw2.startswith(raw), "i %d record precedenti sono byte-identici" % args.attesi),
        (eol2["crlf"] == atteso_crlf and eol2["lf_isolati"] == atteso_lf,
         "fini riga: %d CRLF + %d LF, la mistura preesistente e' intatta"
         % (eol2["crlf"], eol2["lf_isolati"])),
        (recs2[-2].get("item") == ITEM_61 and recs2[-1].get("item") == ITEM_62, "gli item sono i due nuovi"),
        ("record %d." % (args.attesi + 1) in recs2[-2]["numbering_rule"], "numbering_rule del primo"),
        ("record %d." % (args.attesi + 2) in recs2[-1]["numbering_rule"], "numbering_rule del secondo"),
    ]
    print()
    for c, nome in esiti:
        print(("  OK  " if c else "  KO  ") + nome)
    if not all(c for c, _ in esiti):
        return 5
    print("\nOra, in quest'ordine:")
    print("  python src\\paper2_patch_documented_amendments.py apply --file src\\paper2_freeze_verify.py --da %d --a %d"
          % (args.attesi, args.attesi + 2))
    print("  python src\\paper2_freeze_verify.py verify --jobs 4 --out logs\\fv.jsonl")
    return 0


# ------------------------------------------------------------------- selftest

def cmd_selftest(args=None):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    with tempfile.TemporaryDirectory() as td:
        led = os.path.join(td, "amendments.jsonl")
        ref = os.path.join(td, "reference.json")
        cache = os.path.join(td, "cache.npz")
        kref = os.path.join(td, "kref.npz")

        self_sha = "a" * 64
        with open(ref, "wb") as fh:
            fh.write(json.dumps({"_self_sha256": self_sha, "x": 1}).encode("utf-8"))
        ref_sha = sha256_file(ref)

        # kref sintetico: griglia sferica media su gusci, 110 bin come il vero
        k_f = 2.0 * math.pi / BOX
        k = (np.arange(110) + 1.4164) * k_f
        np.savez(kref, k3D=k, sorgente=np.array(["prova"]))
        np.savez(cache, pk_matrix=np.zeros((4, 110), dtype=np.float32))

        global KREF_SHA, CACHE_SHA
        KREF_SHA, CACHE_SHA = sha256_file(kref), sha256_file(cache)

        def scrivi_ledger(n, con60=True, inietta=None, chiudi=True, lf_iniziali=6, tutto_lf=False):
            """Riproduce la forma del ledger vero: i primi record in LF, il resto in CRLF."""
            with open(led, "wb") as fh:
                for i in range(n):
                    r = {"item": "x%d" % i, "type": "protocol"}
                    if inietta and i == 10:
                        r["item"] = inietta
                    if con60 and i == n - 1:
                        r["item"] = ITEM_PREV
                    fine = b"\n" if (tutto_lf or i < lf_iniziali) else CRLF
                    fh.write(json.dumps(r).encode("utf-8") + (fine if (chiudi or i < n - 1) else b""))

        class A:
            pass

        def a(attesi=60, dry=False, backup=None, self_sha_=None, n_k=110, kref_=None, cache_=None):
            x = A(); x.ledger = led; x.reference = ref; x.attesi = attesi
            x.dry_run = dry; x.backup = backup; x.self_sha = self_sha_
            x.cache = cache_ or cache; x.kref = kref_ or kref; x.n_k_atteso = n_k
            return x

        # --- geometria ricalcolata
        geo = geometria_da_kref(kref)
        ok("1 il kref da' 110 bin", geo["n_k"] == 110)
        ok("2 Nyquist e' pi*N/L", abs(geo["k_nyquist"] - math.pi * NGRID / BOX) < 1e-12)
        ok("3 i bin sopra Nyquist si contano dal file",
           geo["bins_above_nyquist"] == int((k > math.pi * NGRID / BOX).sum()))
        ok("4 il primo bin sta a 1.4164 k_F", abs(geo["primo_bin_in_k_f"] - 1.4164) < 1e-3)
        ok("5 il rapporto con la diagonale e' calcolato",
           abs(geo["ratio_to_cube_diagonal"] - geo["k_max_over_k_nyquist"] / math.sqrt(3)) < 1e-12)
        try:
            np.savez(os.path.join(td, "storto.npz"), k3D=np.array([3.0, 1.0, 2.0]))
            geometria_da_kref(os.path.join(td, "storto.npz"))
            ok("6 DIFETTO: griglia non crescente rifiutata", False)
        except Rifiuto:
            ok("6 DIFETTO: griglia non crescente rifiutata", True)
        try:
            np.savez(os.path.join(td, "senza.npz"), altro=np.arange(3))
            geometria_da_kref(os.path.join(td, "senza.npz"))
            ok("7 DIFETTO: kref senza k3D rifiutato", False)
        except Rifiuto:
            ok("7 DIFETTO: kref senza k3D rifiutato", True)

        # --- i cancelli sull'append
        scrivi_ledger(60, con60=False)
        ok("8 senza il record 60 l'append e' RIFIUTATO", cmd_append(a(dry=True)) == 2)
        scrivi_ledger(60, con60=True)
        raw_prima = open(led, "rb").read()
        ok("9 col record 60 presente, il dry-run passa", cmd_append(a(dry=True)) == 0)
        ok("10 e non scrive", open(led, "rb").read() == raw_prima)
        ok("11 conteggio sbagliato: rifiuto", cmd_append(a(attesi=59)) == 2)
        ok("12 reference inesistente: rifiuto", cmd_append(
            type("B", (), {"ledger": led, "reference": ref + ".no", "attesi": 60, "dry_run": True,
                           "backup": None, "self_sha": None, "cache": cache, "kref": kref,
                           "n_k_atteso": 110})()) == 2)
        ok("13 kref inesistente: rifiuto", cmd_append(a(dry=True, kref_=kref + ".no")) == 2)
        ok("14 n_k discordante col cache: rifiuto", cmd_append(a(dry=True, n_k=111)) == 2)

        sha_vero = KREF_SHA
        KREF_SHA = "0" * 64
        ok("15 DIFETTO: kref con sha diverso da quello dichiarato -> rifiuto",
           cmd_append(a(dry=True)) == 2)
        KREF_SHA = sha_vero
        sha_cache = CACHE_SHA
        CACHE_SHA = "0" * 64
        ok("16 DIFETTO: cache cambiato -> rifiuto", cmd_append(a(dry=True)) == 2)
        CACHE_SHA = sha_cache

        with open(ref, "wb") as fh:
            fh.write(json.dumps({"x": 1}).encode("utf-8"))
        ok("17 DIFETTO: reference senza _self_sha256 -> rifiuto", cmd_append(a(dry=True)) == 2)
        ok("18 ma --self-sha lo aggira in modo dichiarato",
           cmd_append(a(dry=True, self_sha_="b" * 64)) == 0)
        with open(ref, "wb") as fh:
            fh.write(json.dumps({"_self_sha256": self_sha, "x": 1}).encode("utf-8"))
        ref_sha = sha256_file(ref)

        # --- l'append vero
        bak = os.path.join(td, "bak.jsonl")
        ok("19 append: esito 0", cmd_append(a(backup=bak)) == 0)
        raw2, recs2, _e, _c, _l = leggi_ledger(led)
        ok("20 il conteggio cambia: 60 -> 62", len(recs2) == 62)
        ok("21 i 60 record precedenti sono byte-identici", raw2.startswith(raw_prima))
        ok("22 backup identico all'originale", open(bak, "rb").read() == raw_prima)
        e2 = analizza_eol(raw2)
        ok("23 la mistura preesistente e' intatta: 6 LF, e i due nuovi in CRLF",
           e2["lf_isolati"] == 6 and e2["crlf"] == 56 and e2["misto"] is True)
        ok("24 il 61 e' l'input_hash del kref",
           recs2[-2]["type"] == "input_hash" and recs2[-2]["name"] == KREF_NAME)
        ok("25 il 62 e' la chiusura, di tipo protocol",
           recs2[-1]["type"] == "protocol" and recs2[-1]["item"] == ITEM_62)
        ok("26 numbering_rule: record 61 e record 62",
           "record 61." in recs2[-2]["numbering_rule"] and "record 62." in recs2[-1]["numbering_rule"])
        ok("27 secondo append sullo stato nuovo: rifiutato", cmd_append(a(attesi=62)) == 2)

        # --- i due cancelli che il test precedente non isolava
        scrivi_ledger(60, con60=True, inietta=ITEM_62)
        ok("27b DIFETTO: item 62 gia' nel ledger -> rifiuto, anche col record 60 in coda",
           cmd_append(a(dry=True)) == 2)
        scrivi_ledger(60, con60=True, inietta=ITEM_61)
        ok("27c DIFETTO: item 61 gia' nel ledger -> rifiuto", cmd_append(a(dry=True)) == 2)
        scrivi_ledger(60, con60=True, chiudi=False)
        ok("27d DIFETTO: ledger senza a capo finale -> rifiuto", cmd_append(a(dry=True)) == 2)

        # --- il kref nella radice di results: il trappolone del tier features
        ok("27e DIFETTO: kref in results/ radice -> rifiuto",
           cmd_append(a(dry=True, kref_=kref)) == 2 if False else
           cmd_append(type("C", (), dict(ledger=led, reference=ref, attesi=60, dry_run=True,
                                         backup=None, self_sha=None, cache=cache,
                                         kref="results/phase7_pk_nwlh_kref.npz",
                                         n_k_atteso=110))()) == 2)

        # --- fine riga tutta LF: si eredita LF
        scrivi_ledger(60, con60=True, tutto_lf=True)
        raw_lf = open(led, "rb").read()
        ok("27f ledger tutto LF: append accettato", cmd_append(a()) == 0)
        raw_lf2 = open(led, "rb").read()
        ok("27g e i due record nuovi finiscono in LF, non in CRLF",
           raw_lf2.startswith(raw_lf) and raw_lf2.count(CRLF) == 0
           and raw_lf2.count(b"\n") == 62)
        scrivi_ledger(60, con60=True)

        nv = recs2[-1]["new_value"]
        ok("28 il record dichiara che D6 NON converge",
           "does not converge" in nv["viii_what_this_record_does_not_do"]["D6_still_does_not_converge"])
        ok("29 e che il 48.3 % resta un limite superiore",
           "UPPER BOUND" in nv["viii_what_this_record_does_not_do"]["D6_still_does_not_converge"])
        ok("30 il residuo 3 resta fuori dal budget e dalla discussione",
           "do not enter the discussion" in nv["viii_what_this_record_does_not_do"]["residue_3_stays_out"])
        ok("31 il tetto giusto e' 0.832", "0.832" in nv["viii_what_this_record_does_not_do"]["the_ceiling"])
        ok("32 la prova e' la riproduzione bit a bit di tre righe",
           nv["iv_the_proof_reproduction_of_three_rows"]["indices"] == [0, 1000, 1999]
           and "bit-for-bit" in nv["iv_the_proof_reproduction_of_three_rows"]["outcome"])
        ok("33 la regola era dichiarata prima, con la sua uscita negativa",
           "REMOVE tests B and C" in nv["iv_the_proof_reproduction_of_three_rows"]["rule_declared_before_running"])
        ok("34 git e' dichiarato incapace di datare lo scrivente",
           "No git command" in nv["iii_git_cannot_date_the_writer"]["consequence"])
        ok("35 log10 P e non P", "log10 of P(k)" in
           nv["vii_three_things_that_change_the_text_not_the_numbers"]["a_it_is_log10_P_not_P"])
        ok("36 la discordanza MAS dichiara il suo confine",
           "NOT" in nv["vii_three_things_that_change_the_text_not_the_numbers"]["b_MAS_declared_does_not_match_the_field_name"]
           and "consequential" in nv["vii_three_things_that_change_the_text_not_the_numbers"]["b_MAS_declared_does_not_match_the_field_name"])
        ok("37 la geometria nel record viene dal kref, non dal testo",
           nv["vii_three_things_that_change_the_text_not_the_numbers"]["c_part_of_the_k_axis_is_above_nyquist"]["recomputed_from_kref"]["n_k"] == 110)
        ok("38 il riempimento singolo e' registrato come test a se",
           nv["vi_the_mean_pk_fill_did_not_fire"]["single_fill_test"]["rows_flagged"] == 0)
        ok("39 l'allineamento porta nperm e seed",
           nv["v_row_alignment_also_has_a_structural_argument"]["statistical"]["seed"] == 20260912)
        ok("40 l'argomento strutturale e' nel record",
           "does not glob" in nv["v_row_alignment_also_has_a_structural_argument"]["structural"])
        ok("41 il record dichiara che l'anomalia non e' confermata",
           "not evidence" in nv["viii_what_this_record_does_not_do"]["it_does_not_confirm_the_anomaly"])
        ok("42 emenda i record 5 e 60", recs2[-1]["rules"]["amends_records"] == [5, 60])
        ok("43 i cancelli importati sono quelli del 50",
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
    p_a.add_argument("--attesi", type=int, default=60)
    p_a.add_argument("--cache", default=CACHE_PATH)
    p_a.add_argument("--kref", default=KREF_PATH)
    p_a.add_argument("--n-k-atteso", type=int, default=110, dest="n_k_atteso")
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend42.py — Emendamento 42: la vitalita' nel registro compD e'
POSIZIONALE, perche' i record emendati supersedono se stessi; e il duplicato
e' una riesecuzione identica, registrata come riproduzione.

Clona il meccanismo di paper2_append_amend40.py:
  - numerazione POSIZIONALE (nessun campo id): il record 42 e' la riga 42;
  - tre campi di digest: reference_file, reference_file_sha256,
    reference_self_sha256;
  - timestamp in `utc`, ISO con offset +00:00 (non 'Z');
  - chiavi in ordine alfabetico (sort_keys=True);
  - ensure_ascii DERIVATO dal file, non assunto;
  - lo schema del record e' l'INTERSEZIONE delle chiavi delle ultime tre righe.

Differenza rispetto al 40: niente --baseline-verified. I fatti che il record
afferma sui registri compD sono verificati MECCANICAMENTE dal selftest, che
legge i due registri e ricalcola il difetto invece di fidarsi di una conferma.

Sottocomandi
------------
  inspect          schema, conteggio righe, digest, stato dei registri compD. Non scrive.
  dump N           stampa la riga N per intero. Non scrive.
  registers        stampa l'analisi dei due registri compD. Non scrive.
  selftest         tutti i controlli. Non scrive.
  append           costruisce e mostra il record; scrive solo con --apply.
  verify           ricontrolla il registro dopo l'append.
  patch-verifier   porta DOCUMENTED_AMENDMENTS da 41 a 42. Scrive solo con --apply.

Cancelli d'append (bloccanti)
-----------------------------
  G1  sha256 di paper2_v1_reference.json == REFERENCE_FILE_SHA256, e uguale a
      quello citato nella riga 41;
  G2  il registro ha esattamente 41 righe prima dell'append;
  G2b la riga 41 si RI-SERIALIZZA byte per byte identica a se stessa: la
      convenzione di scrittura e' derivata dal file, non assunta;
  G3  idempotenza: marker assente e nessuna riga con lo stesso `item`;
  G3b prerequisito: il record 41 e' presente ED E' sulla riga 41;
  G4  schema: il record 42 contiene tutte le chiavi comuni alle righe 39-41;
  G5  reference_self_sha256 == quello della riga 41 == REFERENCE_SELF_SHA;
  G6  --item obbligatorio: la numerazione dell'item non la deduco;
  M1..M9  cancelli MECCANICI sui registri compD (vedi cmd_registers).

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

AMEND_POSITION = 42                    # riga attesa dopo l'append
EXPECTED_LINES_BEFORE = 41

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")
DEFAULT_VERIFIER = os.path.join("src", "paper2_freeze_verify.py")

COMPD = {
    "NGC": os.path.join("results", "paper2", "compD_NGC.jsonl"),
    "SGC": os.path.join("results", "paper2", "compD_SGC.jsonl"),
}

COMPD_SCHEMA = "paper2_compD_v1"
COMPD_EXPECTED_LINES = 4
COMPD_LIVE_POSITIONAL = [3, 4]         # atteso sotto la regola posizionale
COMPD_LIVE_BY_KEY = []                 # atteso sotto la regola per chiave: VUOTO

# Fatti letti dal registro NGC il 5 set 2026. Il selftest li RICONTROLLA
# contro il file: se il registro cambia, il record non si appende.
NGC_UTCS = ["2026-08-26T04:06:32Z", "2026-08-26T04:10:14Z",
            "2026-08-26T04:06:32Z", "2026-08-26T04:10:14Z"]
SGC_UTCS = ["2026-08-26T04:06:36Z", "2026-08-26T04:10:18Z",
            "2026-08-26T04:06:36Z", "2026-08-26T04:10:18Z"]
NGC_CONFIG_HASH = "32af0533ef8c6da2"
NGC_AMENDED_UTC = "2026-08-26T07:20:59Z"
NGC_QUANTITIES = {
    "r2_multi": 0.2605774275605681,
    "r2_ceiling": 0.6979988567812268,
    "w0_sigma1_implied": 3.126978868610808,
    "w0_excursion_gen": 60.02794002998501,
    "deficit_gen": 7180.6860000000015,
    "attenuation": 0.8354632587859425,
    "design_worst_r": -0.03728949032237257,
}
NGC_N = 2000
NGC_ENSEMBLE = "v1"
NGC_PARAMS_PATH_TAIL = "latin_hypercube_nwLH_params.txt"
NGC_NH1_PATH = "results/paper1/per_mock_NGC_R5.jsonl"

# Chiavi che possono differire fra i due record vivi senza che siano due misure.
DUPLICATE_ALLOWED_DIFFS = {"utc", "supersedes"}

MARKER = "emendamento-42-vitalita-posizionale-nel-registro-compD"
MARKER_41 = "emendamento-41-budget-a-quattro-livelli"
COMPANION_DOCUMENT = "checklist_paper2.md, items D2-D5"

VERIFIER_ANCHOR_OLD = "DOCUMENTED_AMENDMENTS = %d" % EXPECTED_LINES_BEFORE
VERIFIER_ANCHOR_NEW = "DOCUMENTED_AMENDMENTS = %d" % AMEND_POSITION


# ---------------------------------------------------------------------------
# Contenuto del record (in INGLESE: e' la lingua del registro)
# ---------------------------------------------------------------------------

KEY = ("vitality_in_the_compD_register_is_positional_because_the_amended_"
       "records_supersede_themselves")

JSON_PATH = ("results/paper2/compD_NGC.jsonl; results/paper2/compD_SGC.jsonl; "
             "checklist_paper2.md items D2-D5")

OLD_VALUE = (
    "results/paper2/compD_NGC.jsonl and compD_SGC.jsonl hold four records each. Lines 3 and 4 "
    "amend lines 1 and 2 with amend_reason 'item 0.9: i numeri della Componente D leggono "
    "per_mock_*_R5.jsonl -> base.N_H1, che e' ensemble v1. L'etichetta mancava.', and carry "
    "amended_utc 2026-08-26T07:20:59Z. Each amending record KEEPS the utc of the run it amends "
    "instead of taking its own: line 3 has utc 2026-08-26T04:06:32Z, which is the utc of line 1; "
    "line 4 has utc 2026-08-26T04:10:14Z, which is the utc of line 2. Same in SGC at 04:06:36Z and "
    "04:10:18Z. The pair (schema, utc) is therefore NOT unique in either file, and no rule of "
    "vitality was ever declared for this register."
)

NEW_VALUE = {
    "the_defect": {
        "where_it_is_NOT": ("The supersedes block is CORRECT. On line 4 it names (paper2_compD_v1, "
                            "2026-08-26T04:10:14Z), which is line 2, the record it is meant to "
                            "amend. Nothing in it is wrong."),
        "where_it_IS": ("In the utc field. The amending record inherited the timestamp of its "
                        "target instead of taking its own, so its OWN key collides with the key it "
                        "supersedes. Line 4 and line 2 are both (paper2_compD_v1, "
                        "2026-08-26T04:10:14Z)."),
        "the_two_readings_are_the_same_bytes": ("Because of the collision, 'line 4 supersedes line "
                                                "2' and 'line 4 supersedes itself' are the same "
                                                "record. Rewriting supersedes to point at line 2 "
                                                "changes nothing - it already does. The intent "
                                                "cannot be recovered from the record, which is why "
                                                "the reading rule has to be declared rather than "
                                                "inferred."),
        "what_it_costs": ("Under the natural reading of the field - collect every (schema, utc) "
                          "named in a supersedes block, then drop the records holding those keys - "
                          "all four records are marked superseded and the register resolves to the "
                          "EMPTY SET, in both hemispheres."),
        "why_it_matters": ("It raises nothing. A consumer would report no Component D record at "
                           "all, or would silently fall back to whichever line it reached first. "
                           "Same class as record 41: not a crash, a silently wrong result. The "
                           "defect is in the rule of reading, not in the numbers."),
        "why_it_has_not_bitten": ("No such consumer has been written, and the four records carry "
                                  "identical numbers, so nothing derived from them is wrong today. "
                                  "It is registered before it can be."),
    },
    "the_vitality_rule": {
        "the_rule": ("A record in compD_*.jsonl is superseded if and only if a LATER LINE in the "
                     "same file carries a supersedes block equal to its (schema, utc). Resolution "
                     "by key alone is FORBIDDEN in this register."),
        "under_it": "Lines 1 and 2 are superseded; lines 3 and 4 are live, in both hemispheres.",
        "the_canonical_record": ("The canonical record for a hemisphere is the LAST live line: NGC "
                                 "line 4 (utc 2026-08-26T04:10:14Z), SGC line 4 (utc "
                                 "2026-08-26T04:10:18Z). Two live records remain by construction "
                                 "and the rule picks one. The choice is inconsequential here "
                                 "because the two are identical, and it is declared so that it "
                                 "stays inconsequential."),
    },
    "the_duplicate_is_a_repeat_execution": {
        "what": ("Lines 3 and 4 differ in NO field except utc and supersedes.utc: identical "
                 "ensemble v1, n = 2000, nh1_path, "
                 "params_path, and all deposited quantities to full precision. The config_hash is 32af0533ef8c6da2 in NGC and 8e548c4d5ff892a0 in SGC - the two hemispheres take different inputs, so they are expected to differ; what matters is that it is CONSTANT across the four records within a hemisphere. NGC deposited values: r2_multi "
                 "0.2605774275605681, r2_ceiling 0.6979988567812268, w0_sigma1_implied "
                 "3.126978868610808, w0_excursion_gen 60.02794002998501, deficit_gen "
                 "7180.6860000000015, attenuation 0.8354632587859425, design_worst_r "
                 "-0.03728949032237257. Four minutes apart."),
        "how_it_is_read": ("Not as a discrepancy and not as noise: as an UNREQUESTED REPRODUCTION "
                           "of the Component D run, two separate executions agreeing bit for bit "
                           "with the same config_hash. It is evidence, and it is kept."),
        "what_is_not_claimed": ("Four minutes apart is not nine days apart. This reproduction says "
                                "the computation is deterministic given the inputs; it says nothing "
                                "about whether the input file is the same one today."),
    },
    "the_schema_defect_not_to_repeat": ("An amending record takes its OWN utc and points to the "
                                        "superseded one. Carrying the superseded utc forward is "
                                        "what collided the two keys here, and it is not "
                                        "repairable after the fact: the supersedes block is "
                                        "already right, so there is nothing in it to correct."),
    "what_this_does_not_do": ("It writes NOTHING to compD_*.jsonl - those registers are append-only "
                              "and are left untouched. It changes no number: r2_multi 0.2606 and "
                              "w0_sigma1_implied +-3.13 remain the values of checklist items D5 and "
                              "D4. It does NOT address the traceability of the parameter file - the "
                              "absent digest, the manifest path at phase0_data_manifest.json line "
                              "8043 which resolves to no file, and the wrong default at "
                              "paper2_compD_partialcorr.py:484 - which is a separate record."),
}

RULES = {
    "amends_records": [],
    "an_amending_record_takes_its_own_utc": ("It points to the superseded record; it does not "
                                             "inherit its timestamp. Inheriting it collides the "
                                             "amending key with the amended one, and no later "
                                             "edit of the supersedes block can undo that: the "
                                             "block is already correct. The cure is in the utc "
                                             "field or nowhere."),
    "an_identical_repeat_is_evidence_not_noise": ("Same config_hash, same output, separate "
                                                  "execution: recorded as a reproduction rather "
                                                  "than removed as a duplicate."),
    "companion_document": COMPANION_DOCUMENT,
    "marker": MARKER,
    "the_canonical_record_is_the_last_live_line": ("Declared per hemisphere, so that a register "
                                                   "with more than one live record is never read "
                                                   "by whichever line the reader happens to reach "
                                                   "first."),
    "vitality_is_positional_never_by_key": ("In any register where an amending record may repeat "
                                            "the utc of the record it supersedes, vitality is "
                                            "resolved by POSITION in the file. A key-based "
                                            "resolver returns an EMPTY register and raises "
                                            "nothing."),
    "what_this_does_not_do": ("It writes nothing to compD_*.jsonl, changes no number, and does not "
                              "address the traceability of the parameter file."),
}

REASON = (
    "The Component D registers had no declared rule of vitality, and the obvious rule is the wrong "
    "one. Lines 3 and 4 of compD_NGC.jsonl and compD_SGC.jsonl amend lines 1 and 2, but each "
    "amending record kept the utc of the run it amends and repeated that utc in its own supersedes "
    "block. So the records supersede THEMSELVES, the pair (schema, utc) is not unique, and a "
    "consumer that resolves supersedes by key - the natural reading - marks all four superseded and "
    "returns an EMPTY register in both hemispheres. It raises nothing. This is the class of record "
    "41: not a crash, a silently wrong result. It has not bitten because no such consumer exists "
    "yet and the four records carry the same numbers, so it is registered before it can. THE RULE, "
    "declared here: a record is superseded if and only if a LATER LINE carries a supersedes block "
    "equal to its (schema, utc); resolution by key alone is forbidden; the canonical record is the "
    "last live line, NGC line 4 and SGC line 4. AND THE DUPLICATE. Lines 3 and 4 differ in no field "
    "except utc and supersedes.utc - identical config_hash 32af0533ef8c6da2 and identical deposited "
    "quantities to full precision, four minutes apart. That is not a discrepancy to be removed but "
    "an unrequested reproduction of the Component D run, and it is kept as evidence. What it does "
    "NOT establish: four minutes apart is not nine days apart, so it says the computation is "
    "deterministic given its inputs and nothing about whether the parameter file is the same one "
    "today. That question - the absent digest, the manifest path that resolves to no file, the "
    "wrong default in the script - is a separate record. NOTHING IS WRITTEN to compD_*.jsonl: the "
    "defect is in the rule of reading, and rules live here."
)

EVIDENCE = (
    "Read on 5 Sep 2026 from results/paper2/compD_NGC.jsonl and compD_SGC.jsonl, four records each. "
    "NGC utc in file order: 2026-08-26T04:06:32Z, 04:10:14Z, 04:06:32Z, 04:10:14Z; supersedes on "
    "lines 3 and 4: {'schema': 'paper2_compD_v1', 'utc': '2026-08-26T04:06:32Z'} and {'schema': "
    "'paper2_compD_v1', 'utc': '2026-08-26T04:10:14Z'} - each equal to the utc of the record that "
    "carries it. SGC: 04:06:36Z, 04:10:18Z, 04:06:36Z, 04:10:18Z, same structure. amend_reason on "
    "lines 3 and 4, both hemispheres: 'item 0.9: i numeri della Componente D leggono "
    "per_mock_*_R5.jsonl -> base.N_H1, che e' ensemble v1. L'etichetta mancava.', amended_utc "
    "2026-08-26T07:20:59Z. Lines 1 and 2 have ensemble null; lines 3 and 4 have ensemble 'v1', which "
    "is what item 0.9 supplied. Lines 3 and 4 of NGC are equal field by field outside {utc, "
    "supersedes}: config_hash 32af0533ef8c6da2, n 2000, nh1_path results/paper1/per_mock_NGC_R5.jsonl, "
    "params_path data\\\\raw\\\\quijote\\\\3D_cubes\\\\latin_hypercube_nwLH\\\\latin_hypercube_nwLH_params.txt, "
    "r2_multi 0.2605774275605681, r2_ceiling 0.6979988567812268, w0_sigma1_implied 3.126978868610808, "
    "w0_excursion_gen 60.02794002998501, deficit_gen 7180.6860000000015, attenuation "
    "0.8354632587859425, design_worst_r -0.03728949032237257, design_worst_pair ['Omega_b', "
    "'sigma_8']. The two resolvers were run over both registers by the selftest of this script: "
    "resolution by key yields [] live records in NGC and [] in SGC; resolution by position yields "
    "lines [3, 4] in both. Two mutations were run against a synthetic copy to check that the gates "
    "bite. Rewriting line 4's supersedes to name line 2 changed NOTHING - by-key still returned [] "
    "- because line 4 and line 2 share a utc and the block already named line 2. Giving line 4 its "
    "own utc (its amended_utc) made by-key and positional AGREE at [3, 4], which locates the defect "
    "in the utc field and not in the supersedes block."
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


# ---------------------------------------------------------------------------
# I due risolutori. Sono il cuore del record: il primo e' quello sbagliato.
# ---------------------------------------------------------------------------

def resolve_by_key(recs):
    """Regola VIETATA: raccoglie le chiavi citate in supersedes e scarta i record
    che le portano. Su questo registro restituisce l'insieme vuoto."""
    dead = set()
    for r in recs:
        sup = r.get("supersedes")
        if isinstance(sup, dict):
            dead.add((sup.get("schema"), sup.get("utc")))
    return [i for i, r in enumerate(recs, start=1)
            if (r.get("schema"), r.get("utc")) not in dead]


def resolve_positional(recs):
    """Regola DICHIARATA: un record e' superato se una riga SUCCESSIVA lo cita."""
    live = []
    for i, r in enumerate(recs):
        key = (r.get("schema"), r.get("utc"))
        dead = False
        for later in recs[i + 1:]:
            sup = later.get("supersedes")
            if isinstance(sup, dict) and (sup.get("schema"), sup.get("utc")) == key:
                dead = True
                break
        if not dead:
            live.append(i + 1)
    return live


def self_superseding(recs):
    """Posizioni (1-based) dei record che citano la propria stessa chiave."""
    out = []
    for i, r in enumerate(recs, start=1):
        sup = r.get("supersedes")
        if isinstance(sup, dict) and (sup.get("schema"), sup.get("utc")) == \
                (r.get("schema"), r.get("utc")):
            out.append(i)
    return out


def diff_keys(a, b):
    """Chiavi in cui due record differiscono (presenza o valore)."""
    out = set()
    for k in set(a.keys()) | set(b.keys()):
        if a.get(k, "__MISSING__") != b.get(k, "__MISSING__"):
            out.add(k)
    return out


def analyse_registers(paths=None):
    """Legge i due registri compD e ne ricalcola i fatti. Non scrive nulla."""
    paths = paths or COMPD
    out = {}
    for region, path in sorted(paths.items()):
        if not os.path.isfile(path):
            out[region] = {"error": "assente: %s" % path}
            continue
        recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_jsonl(path)
        info = {
            "path": path,
            "n_records": len(recs),
            "utcs": [r.get("utc") for r in recs],
            "schemas": sorted({r.get("schema") for r in recs}),
            "config_hashes": sorted({r.get("config_hash") for r in recs}),
            "ensembles": [r.get("ensemble") for r in recs],
            "self_superseding": self_superseding(recs),
            "live_by_key": resolve_by_key(recs),
            "live_positional": resolve_positional(recs),
            "newline": "CRLF" if newline == b"\r\n" else "LF",
        }
        if len(recs) >= 2:
            info["diff_last_two"] = sorted(diff_keys(recs[-2], recs[-1]))
        out[region] = info
    return out


# ---------------------------------------------------------------------------
# Costruzione del record
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest(ledger, reference, item, overrides, compd=None, verbose=True):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    ok_ledger = os.path.isfile(ledger)
    chk("1  registro presente", ok_ledger, ledger)
    if not ok_ledger:
        return _report(checks, verbose)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(ledger)

    chk("2  righe = %d" % EXPECTED_LINES_BEFORE, len(recs) == EXPECTED_LINES_BEFORE,
        "trovate %d" % len(recs))

    # La convenzione di scrittura e' DERIVATA: la riga 41 deve ri-serializzarsi
    # byte per byte identica a se stessa.
    round_trip = json.dumps(recs[-1], ensure_ascii=pure_ascii,
                            sort_keys=True).encode("utf-8")
    chk("2b la riga %d si ri-serializza byte per byte identica" % len(recs),
        round_trip == lines[-1],
        "%d byte contro %d" % (len(round_trip), len(lines[-1])))

    ok_ref = os.path.isfile(reference)
    file_sha = sha256_file(reference) if ok_ref else ""
    chk("3  sha256 del reference invariato", file_sha == REFERENCE_FILE_SHA256,
        file_sha[:16] if file_sha else "assente")

    cited = recs[-1].get("reference_file_sha256") if recs else None
    chk("4  digest = quello citato nella riga %d" % len(recs), cited == file_sha,
        (cited or "assente")[:16])

    self_sha = ""
    if ok_ref:
        try:
            self_sha = json.load(open(reference, "r", encoding="utf-8")).get("_self_sha256", "")
        except Exception as exc:
            chk("4b _self_sha256 leggibile", False, str(exc))
    chk("5  _self_sha256 presente e uguale a quello atteso e a quello della riga %d" % len(recs),
        bool(self_sha) and self_sha == REFERENCE_SELF_SHA
        and self_sha == recs[-1].get("reference_self_sha256"),
        self_sha[:16])

    blob = raw.decode("utf-8", "replace")
    dup_item = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 42 assente, item non gia' usato)",
        (MARKER not in blob) and not dup_item,
        "item %s gia' presente" % item if dup_item else "")
    chk("6b prerequisito: il record 41 e' presente ED e' sulla riga %d" % EXPECTED_LINES_BEFORE,
        (MARKER_41 in blob)
        and (MARKER_41 in json.dumps(recs[EXPECTED_LINES_BEFORE - 1], ensure_ascii=False)))

    n_crlf, n_lf, odd = eol_profile(terms)
    chk("7  convenzioni: ascii_puro=%s chiavi_ordinate=%s; fine riga CRLF=%d LF=%d"
        % (pure_ascii, sorted_keys, n_crlf, n_lf), True,
        ("righe fuori maggioranza: %s - PREESISTENTE, da registrare a parte; "
         "non blocca, il contenuto JSON e' integro" % odd) if odd else "uniformi")
    chk("7b l'ultima riga e' terminata come la maggioranza (e' dopo di essa che si appende)",
        terms[-1] == (b"\r\n" if n_crlf >= n_lf else b"\n"),
        "ultima=%r" % terms[-1])

    # -----------------------------------------------------------------------
    # Cancelli MECCANICI sui registri compD: il record afferma dei fatti, e
    # questi li ricalcolano dal file invece di chiedere una conferma.
    # -----------------------------------------------------------------------
    A = analyse_registers(compd)
    bad = []
    for region in ("NGC", "SGC"):
        info = A.get(region, {})
        if "error" in info:
            bad.append("%s: %s" % (region, info["error"]))
            continue
        if info["n_records"] != COMPD_EXPECTED_LINES:
            bad.append("%s/n=%d" % (region, info["n_records"]))
        if info["schemas"] != [COMPD_SCHEMA]:
            bad.append("%s/schema=%s" % (region, info["schemas"]))
        if info["self_superseding"] != COMPD_LIVE_POSITIONAL:
            bad.append("%s/auto-supersessione=%s" % (region, info["self_superseding"]))
        if info["live_by_key"] != COMPD_LIVE_BY_KEY:
            bad.append("%s/per-chiave=%s" % (region, info["live_by_key"]))
        if info["live_positional"] != COMPD_LIVE_POSITIONAL:
            bad.append("%s/posizionale=%s" % (region, info["live_positional"]))
        if len(info["config_hashes"]) != 1:
            bad.append("%s/config_hash multipli=%s" % (region, info["config_hashes"]))
        if set(info.get("diff_last_two", [])) != DUPLICATE_ALLOWED_DIFFS:
            bad.append("%s/i due vivi differiscono in %s" % (region, info.get("diff_last_two")))
        if info["ensembles"][:2] != [None, None] or info["ensembles"][2:] != ["v1", "v1"]:
            bad.append("%s/ensemble=%s" % (region, info["ensembles"]))
    chk("M1 registri compD: 4 record, auto-supersessione su 3 e 4, un solo "
        "config_hash, i due vivi differiscono SOLO in {utc, supersedes}",
        not bad, ",".join(bad) if bad else "due emisferi, otto controlli ciascuno")

    bad2 = []
    if A.get("NGC", {}).get("utcs") != NGC_UTCS:
        bad2.append("NGC utcs=%s" % A.get("NGC", {}).get("utcs"))
    if A.get("SGC", {}).get("utcs") != SGC_UTCS:
        bad2.append("SGC utcs=%s" % A.get("SGC", {}).get("utcs"))
    chk("M2 i timestamp citati nel record sono quelli sul disco", not bad2,
        ",".join(bad2) if bad2 else "otto timestamp")

    bad3 = []
    ngc_path = (compd or COMPD)["NGC"]
    if os.path.isfile(ngc_path):
        nrecs, _, _, _, _, _, _ = read_jsonl(ngc_path)
        last = nrecs[-1]
        for k, v in NGC_QUANTITIES.items():
            if last.get(k) != v:
                bad3.append("%s=%r" % (k, last.get(k)))
        if last.get("config_hash") != NGC_CONFIG_HASH:
            bad3.append("config_hash=%r" % last.get("config_hash"))
        if last.get("amended_utc") != NGC_AMENDED_UTC:
            bad3.append("amended_utc=%r" % last.get("amended_utc"))
        if last.get("n") != NGC_N or last.get("ensemble") != NGC_ENSEMBLE:
            bad3.append("n/ensemble=%r/%r" % (last.get("n"), last.get("ensemble")))
        if last.get("nh1_path") != NGC_NH1_PATH:
            bad3.append("nh1_path=%r" % last.get("nh1_path"))
        if not str(last.get("params_path", "")).endswith(NGC_PARAMS_PATH_TAIL):
            bad3.append("params_path=%r" % last.get("params_path"))
    else:
        bad3.append("registro NGC assente")
    chk("M3 le quantita' citate nel record sono quelle depositate, a precisione piena",
        not bad3, ",".join(bad3) if bad3 else "dodici valori")

    rec = None
    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha, self_sha,
                                                       item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 39-41 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 old_value dice che l'utc e' ereditato, e che la chiave non e' unica",
            ("the utc of line 1" in rec["old_value"])
            and ("the utc of line 2" in rec["old_value"])
            and ("NOT unique" in rec["old_value"]))
        chk("10b il record NON accusa il blocco supersedes, e dice perche' non "
            "e' riparabile a posteriori",
            ("CORRECT" in rec["new_value"]["the_defect"]["where_it_is_NOT"])
            and ("utc field" in rec["new_value"]["the_defect"]["where_it_IS"])
            and ("changes nothing" in rec["new_value"]["the_defect"]
                 ["the_two_readings_are_the_same_bytes"])
            and ("utc field or nowhere" in rec["rules"]
                 ["an_amending_record_takes_its_own_utc"]))
        chk("11 la regola vietata e quella dichiarata sono entrambe nominate",
            ("FORBIDDEN" in rec["new_value"]["the_vitality_rule"]["the_rule"])
            and ("LATER LINE" in rec["new_value"]["the_vitality_rule"]["the_rule"])
            and ("EMPTY" in rec["rules"]["vitality_is_positional_never_by_key"]))
        chk("12 il canonico e' dichiarato per emisfero",
            ("NGC line 4" in rec["new_value"]["the_vitality_rule"]["the_canonical_record"])
            and ("SGC line 4" in rec["new_value"]["the_vitality_rule"]["the_canonical_record"]))
        chk("13 il duplicato e' registrato come RIPRODUZIONE, con il suo limite",
            ("REPRODUCTION" in rec["new_value"]["the_duplicate_is_a_repeat_execution"]
                ["how_it_is_read"])
            and ("not nine days apart" in rec["new_value"]
                 ["the_duplicate_is_a_repeat_execution"]["what_is_not_claimed"]))
        chk("13a la tracciabilita' del file dei parametri e' esplicitamente ESCLUSA",
            ("separate record" in rec["new_value"]["what_this_does_not_do"])
            and ("8043" in rec["new_value"]["what_this_does_not_do"]))
        chk("13b lingua del record: inglese come le righe 39-41",
            ("perche'" not in txt) and ("cancelli" not in txt) and ("emisferi" not in txt)
            and ("pavimento" not in txt))
        chk("13c document ereditato dalla riga %d" % len(recs),
            rec["document"] == recs[-1].get("document"), str(rec["document"])[:48])
        chk("13d reference_self_sha256 = quello della riga %d" % len(recs),
            rec["reference_self_sha256"] == recs[-1].get("reference_self_sha256"),
            (rec["reference_self_sha256"] or "")[:16])
        chk("13e numbering_rule cita il record %d, non il %d"
            % (len(recs) + 1, len(recs)),
            (str(len(recs) + 1) in str(rec.get("numbering_rule")))
            and ("record %d." % len(recs) not in str(rec.get("numbering_rule"))),
            str(rec.get("numbering_rule"))[-40:])
        chk("13f niente numeri scritti nei registri compD: il record e' di sola regola",
            rec["rules"]["amends_records"] == []
            and ("writes NOTHING" in rec["new_value"]["what_this_does_not_do"]))
    else:
        for n in ("8  schema", "9  serializzazione", "10 old_value", "11 regole",
                  "12 canonico", "13 duplicato"):
            chk(n, False, "manca --item")

    # I due risolutori su un caso costruito: la regola vietata deve svuotare,
    # quella dichiarata no. Indipendente dai file su disco.
    try:
        synth = [
            {"schema": "s", "utc": "T1"},
            {"schema": "s", "utc": "T2"},
            {"schema": "s", "utc": "T1", "supersedes": {"schema": "s", "utc": "T1"}},
            {"schema": "s", "utc": "T2", "supersedes": {"schema": "s", "utc": "T2"}},
        ]
        sane = [
            {"schema": "s", "utc": "T1"},
            {"schema": "s", "utc": "T3", "supersedes": {"schema": "s", "utc": "T1"}},
        ]
        ok = (resolve_by_key(synth) == [] and resolve_positional(synth) == [3, 4]
              and resolve_by_key(sane) == [2] and resolve_positional(sane) == [2]
              and self_superseding(synth) == [3, 4] and self_superseding(sane) == [])
        chk("14 i due risolutori su un caso costruito: per chiave svuota, "
            "posizionale no; e su un registro sano coincidono", ok)
    except Exception as exc:
        chk("14 risolutori", False, str(exc))

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
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    print("registro        : %s" % args.ledger)
    print("righe           : %d" % len(recs))
    print("newline         : %s" % ("CRLF" if newline == b"\r\n" else "LF"))
    print("ascii puro      : %s" % pure_ascii)
    print("chiavi ordinate : %s" % sorted_keys)
    n_crlf, n_lf, odd = eol_profile(terms)
    print("fine riga       : CRLF=%d  LF=%d%s"
          % (n_crlf, n_lf, ("   righe fuori maggioranza: %s" % odd) if odd else "   uniformi"))
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("round-trip r.%-2d : %s" % (len(recs), "IDENTICO" if rt == lines[-1] else "DIVERSO"))
    if os.path.isfile(args.reference):
        fs = sha256_file(args.reference)
        print("reference file  : %s" % fs)
        print("atteso          : %s   %s"
              % (REFERENCE_FILE_SHA256, "OK" if fs == REFERENCE_FILE_SHA256 else "DIVERSO"))
    ck = common_keys(recs, 3)
    print("chiavi comuni 39-41 (%d): %s" % (len(ck), ck))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d extra: %s" % (i, sorted(set(r.keys()) - set(ck))))
        print("           item: %r   type: %r   utc: %r"
              % (r.get("item"), r.get("type"), r.get("utc")))
    print("")
    return cmd_registers(args)


def cmd_registers(args):
    A = analyse_registers()
    print("=== REGISTRI compD ===")
    for region in ("NGC", "SGC"):
        info = A.get(region, {})
        print("  %s  %s" % (region, info.get("path", "")))
        if "error" in info:
            print("      %s" % info["error"])
            continue
        print("      record            : %d   newline: %s" % (info["n_records"], info["newline"]))
        print("      utc               : %s" % ", ".join(str(u) for u in info["utcs"]))
        print("      ensemble          : %s" % info["ensembles"])
        print("      config_hash       : %s" % info["config_hashes"])
        print("      auto-supersessione: righe %s" % info["self_superseding"])
        print("      vivi PER CHIAVE   : %s   <- la regola vietata" % info["live_by_key"])
        print("      vivi POSIZIONALI  : %s   <- la regola dichiarata" % info["live_positional"])
        print("      i due vivi differiscono in: %s" % info.get("diff_last_two"))
    return 0


def cmd_dump(args):
    recs, _, _, _, _, _, _ = read_ledger(args.ledger)
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

    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    file_sha = sha256_file(args.reference)
    self_sha = json.load(open(args.reference, "r", encoding="utf-8")).get("_self_sha256", "")
    rec, unfilled, extras, required = build_record(recs, args.reference, file_sha, self_sha,
                                                   args.item, ov)
    if unfilled:
        fail("chiavi che non so riempire: %s. Usa --set chiave=valore (o =null)."
             % ", ".join(unfilled))
    if extras and not args.allow_extra_keys:
        fail("il record 42 aggiunge le chiavi %s rispetto alle comuni 39-41. "
             "Approvale con --allow-extra-keys." % ", ".join(extras))

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
    last = json.dumps(recs[-1], ensure_ascii=False) if recs else ""
    print("  marker nella riga %-2d      : %s" % (AMEND_POSITION, MARKER in last))
    ok &= MARKER in last
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("  round-trip della riga %-2d  : %s" % (AMEND_POSITION, rt == lines[-1]))
    ok &= rt == lines[-1]
    print("  item della riga %-2d        : %r" % (AMEND_POSITION, recs[-1].get("item")))
    print("  newline / ascii / ordine  : %s / %s / %s"
          % ("CRLF" if newline == b"\r\n" else "LF", pure_ascii, sorted_keys))
    print("  registri compD intatti    : %s"
          % all(analyse_registers().get(r, {}).get("n_records") == COMPD_EXPECTED_LINES
                for r in ("NGC", "SGC")))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def cmd_patch_verifier(args):
    """Porta DOCUMENTED_AMENDMENTS da 41 a 42. Ancora unica, o non tocca nulla."""
    path = args.verifier
    if not os.path.isfile(path):
        fail("verificatore assente: %s" % path)
    with open(path, "rb") as f:
        raw = f.read()
    txt = raw.decode("utf-8")
    # IL CANCELLO CHE MANCAVA: la costante documenta il registro, quindi il
    # registro deve gia' avere le righe che la costante dichiarera'.
    target = EXPECTED_LINES_BEFORE if args.revert else AMEND_POSITION
    n_disk = None
    if os.path.isfile(args.ledger):
        n_disk = len(read_ledger(args.ledger)[0])
    if n_disk != target and not args.force:
        fail("il registro ha %s righe, la costante ne dichiarerebbe %d. "
             "Appendi prima, documenta poi (o --force se sai cosa stai facendo)."
             % (n_disk, target))
    n_old = txt.count(VERIFIER_ANCHOR_OLD)
    n_new = txt.count(VERIFIER_ANCHOR_NEW)
    print("=== PATCH VERIFIER ===")
    print("  file            : %s" % path)
    print("  ancora %-24r: %d occorrenze" % (VERIFIER_ANCHOR_OLD, n_old))
    print("  gia' aggiornato %-16r: %d occorrenze" % (VERIFIER_ANCHOR_NEW, n_new))
    src_a, dst_a = ((VERIFIER_ANCHOR_NEW, VERIFIER_ANCHOR_OLD) if args.revert
                    else (VERIFIER_ANCHOR_OLD, VERIFIER_ANCHOR_NEW))
    n_src, n_dst = txt.count(src_a), txt.count(dst_a)
    if n_dst and not n_src:
        print("  [OK] gia' a %d, nulla da fare." % target)
        return 0
    if n_src != 1:
        fail("l'ancora %r non e' unica (%d occorrenze): non tocco il file." % (src_a, n_src))
    new_txt = txt.replace(src_a, dst_a)
    if not args.apply:
        print("  [DRY-RUN] sostituzione pronta, nulla scritto. Rilancia con --apply.")
        return 0
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(new_txt.encode("utf-8"))
    os.replace(tmp, path)
    print("  [OK] DOCUMENTED_AMENDMENTS -> %d   (registro su disco: %s righe)"
          % (target, n_disk))
    return 0


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 42 - vitalita' posizionale nel registro compD")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    p.add_argument("--reference", default=DEFAULT_REFERENCE)
    p.add_argument("--verifier", default=DEFAULT_VERIFIER)
    p.add_argument("--item", default=None, help="numerazione item, es. D2")
    p.add_argument("--set", action="append", metavar="CHIAVE=VALORE")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("registers").set_defaults(func=cmd_registers)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    d = sub.add_parser("dump")
    d.add_argument("n", type=int)
    d.set_defaults(func=cmd_dump)

    ap = sub.add_parser("append")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-extra-keys", action="store_true")
    ap.set_defaults(func=cmd_append)

    pv = sub.add_parser("patch-verifier")
    pv.add_argument("--apply", action="store_true")
    pv.add_argument("--revert", action="store_true",
                    help="riporta la costante da %d a %d" % (AMEND_POSITION,
                                                             EXPECTED_LINES_BEFORE))
    pv.add_argument("--force", action="store_true",
                    help="salta il cancello sul numero di righe del registro")
    pv.set_defaults(func=cmd_patch_verifier)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()

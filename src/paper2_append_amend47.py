#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend47.py - Emendamento 47: sei righe del registro degli
emendamenti hanno un fine riga anomalo, e quattro condividono un utc segnaposto.

PERCHE' ORA, VISTO CHE OGGI E' INERTE
-------------------------------------
Il registro sta in src/, nessun tier lo hasha byte per byte -- il verificatore
legge RECORD, non byte -- e .gitattributes copre results/**, non src/. Quindi
oggi non morde. Diventa una mina il giorno che si aggiunge un digest del
registro, e quel giorno chi lo aggiunge non sapra' che quelle sei righe sono
diverse. Si registra PRIMA che serva, non quando serve.

I fatti si RILEGGONO dal registro stesso: il profilo dei fine riga e gli utc
si ricalcolano, non si citano.

Cancelli
--------
  G1..G6  come nei record 43-46;
  M1  il profilo dei fine riga e' quello citato: sei righe fuori maggioranza,
      alle posizioni citate;
  M2  le quattro righe con l'utc segnaposto sono quelle citate, e l'utc e'
      quello;
  M3  il registro resta LEGGIBILE: il numero di record non cambia, ed e' cio'
      che rende l'anomalia inerte oggi.

Uscita ASCII pura.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

AMEND_POSITION = 47
EXPECTED_LINES_BEFORE = 46

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")

RIGHE_LF = [8, 9, 10, 11, 13, 14]
UTC_SEGNAPOSTO = "2026-08-27T00:00:00Z"
RIGHE_SEGNAPOSTO = [8, 9, 10, 11]

MARKER = "emendamento-47-fine-riga-anomalo-nel-registro-degli-emendamenti"
MARKER_46 = "emendamento-46-terzo-canale-misurato-firma-smentita"
COMPANION_DOCUMENT = "checklist_paper2.md rev. 3.18, punto 11"


KEY = "six_lines_of_the_amendments_ledger_have_a_lone_LF_and_four_share_a_placeholder_utc"

JSON_PATH = "src/paper2_v1_amendments.jsonl; src/paper2_freeze_verify.py; .gitattributes"

OLD_VALUE = (
    "The amendments ledger was assumed to be uniformly CRLF. It is not: six of its lines - 8, 9, 10, "
    "11, 13 and 14 - are terminated by a lone LF while the other forty carry CRLF. The anomaly was "
    "found by a reader that assumed uniformity and glued lines 8 and 9 together, reporting them as "
    "one malformed record; the ledger itself was fine and the reader was wrong. Nothing had "
    "registered the mixture."
)

NEW_VALUE = {
    "what_it_is": {
        "the_line_endings": ("Six lines out of forty-six end with a lone LF: 8, 9, 10, 11, 13 and "
                             "14. A contiguous band with line 12 CRLF in the middle, so it is not a "
                             "whole-file conversion by a tool - it is one appender, or one session, "
                             "writing LF where the others write CRLF."),
        "and_the_placeholder_utc": ("Lines 8 to 11 also share the SAME utc, 2026-08-27T00:00:00Z - "
                                    "midnight exactly, a placeholder and not a run time. Four "
                                    "records with one temporal key. Line 12 carries "
                                    "2026-08-28T12:30:00Z, also a round hour, and from line 13 the "
                                    "format changes from Z to +00:00."),
        "which_is_the_collision_record_42_regulated": ("Record 42 declared, for the compD register, "
                                                       "that vitality is POSITIONAL because (schema, "
                                                       "utc) is not unique there. The same collision "
                                                       "is present in the amendments ledger itself. "
                                                       "It does not bite here because the "
                                                       "numbering_rule already declares identity by "
                                                       "POSITION - the number of an amendment is its "
                                                       "1-based position in the file - but the rule "
                                                       "of record 42 was general and this is the "
                                                       "proof."),
    },
    "why_it_is_inert_today": ("The ledger lives in src/. No tier hashes it byte for byte: the freeze "
                              "verifier reads RECORDS - it reports 'JSONL integro: disco=46 righe "
                              "malformate=0' - not bytes. And .gitattributes covers results/**, not "
                              "src/, so a checkout with core.autocrlf could normalise those six "
                              "lines and change the file's bytes with nothing noticing. Today "
                              "nothing depends on those bytes."),
    "why_it_is_registered_anyway": ("It becomes a landmine the day a digest of the ledger is added - "
                                    "and whoever adds it will not know that six lines differ. "
                                    "Registering it now costs one record; registering it then costs "
                                    "an investigation. The rule this programme keeps arriving at: "
                                    "the moment to write something down is BEFORE it matters."),
    "what_is_NOT_done": ("The six lines are NOT rewritten. The ledger is append-only: normalising "
                         "them would change forty-six records' worth of file to fix a cosmetic "
                         "property of six, and it would be the first time anything in this file was "
                         "edited rather than appended. The anomaly stays; what changes is that it is "
                         "now known."),
    "what_to_do_if_a_digest_is_ever_added": ("Compute it over the RECORDS - the sorted JSON of each "
                                             "line - not over the raw bytes. That is invariant to "
                                             "line endings and to the BOM that "
                                             "results/revision/rev1_r11_tiling.json turned out to "
                                             "carry. A byte digest of a text file in src/ is hostage "
                                             "to git's newline handling."),
}

RULES = {
    "amends_records": [],
    "a_digest_of_a_text_file_in_src_is_hostage_to_git": ("Hash the records, not the bytes. Line "
                                                         "endings and BOMs change bytes without "
                                                         "changing content."),
    "companion_document": COMPANION_DOCUMENT,
    "marker": MARKER,
    "the_moment_to_write_something_down_is_before_it_matters": ("This anomaly is inert. It is "
                                                                "registered because the day it is "
                                                                "not, nobody will remember it."),
    "vitality_by_position_is_general": ("Record 42 declared it for the compD register. The same "
                                        "utc collision exists in the amendments ledger, where the "
                                        "numbering_rule already handles it."),
    "what_this_does_not_do": ("It rewrites nothing. The ledger is append-only and the six lines stay "
                              "as they are."),
}

REASON = (
    "Six lines of the amendments ledger - 8, 9, 10, 11, 13 and 14 - end with a lone LF while the "
    "other forty carry CRLF, and lines 8 to 11 additionally share one placeholder utc, "
    "2026-08-27T00:00:00Z, midnight exactly. The band is contiguous with line 12 CRLF in the middle, "
    "so it is not a tool converting the whole file: it is one appender writing LF. THE UTC COLLISION "
    "IS THE ONE RECORD 42 REGULATED for the compD register, present here in the amendments ledger "
    "itself; it does not bite because numbering_rule already declares identity by POSITION, but the "
    "rule was general and this is the proof. TODAY IT IS INERT: the ledger lives in src/, no tier "
    "hashes it byte for byte - the verifier reads records and reports zero malformed - and "
    ".gitattributes covers results/** and not src/, so a checkout with core.autocrlf could normalise "
    "those six lines with nothing noticing. IT IS REGISTERED ANYWAY because it becomes a landmine the "
    "day a digest of the ledger is added, and whoever adds it then will not know. NOTHING IS "
    "REWRITTEN: the file is append-only, and normalising six lines would be the first edit ever made "
    "to it. What changes is that the anomaly is now known, together with what to do about it - hash "
    "the RECORDS, not the bytes, which is invariant to line endings and to the BOM that "
    "rev1_r11_tiling.json turned out to carry."
)

EVIDENCE = (
    "Read on 5-6 Sep 2026 from src/paper2_v1_amendments.jsonl. Splitting on LF and stripping a "
    "trailing CR gives 46 records and zero malformed lines; splitting on CRLF alone glues lines 8 and "
    "9 and reports 'Extra data: line 2 column 1 (char 1490)' at line 8, which is how the anomaly was "
    "found. Profile: CRLF 40, LF 6, lines outside the majority [8, 9, 10, 11, 13, 14]. Timestamps and "
    "items of lines 7 to 15: 7 CRLF 2026-08-26T11:58:03Z 1.2b-rettifica; 8 LF 2026-08-27T00:00:00Z "
    "0.5.3 / 2.1-M; 9 LF same utc 0.5.3 / 2.1-M; 10 LF same utc 0.5.3 / 0.2 (R2.6); 11 LF same utc "
    "0.1; 12 CRLF 2026-08-28T12:30:00Z 0.1; 13 LF 2026-08-29T09:45:47+00:00 0.14; 14 LF "
    "2026-08-29T22:31:03+00:00 3.2/D4; 15 CRLF 2026-08-31T07:57:47+00:00 1.3/B6. The freeze verifier "
    "reports 'emendamenti: JSONL integro: disco=46 righe malformate=0', which is what makes the "
    "anomaly inert today."
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











def analyse_gates(ledger=DEFAULT_LEDGER):
    """Ricalcola il profilo dei fine riga e gli utc. Nessun numero trascritto."""
    if not os.path.isfile(ledger):
        return {"errore": "registro assente: %s" % ledger}
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(ledger)
    n_crlf, n_lf, odd = eol_profile(terms)
    utcs = {i: r.get("utc") for i, r in enumerate(recs, start=1)}
    segnaposto = sorted(i for i, u in utcs.items() if u == UTC_SEGNAPOSTO)
    return {"errore": None, "n_record": len(recs), "n_crlf": n_crlf, "n_lf": n_lf,
            "righe_fuori": odd, "segnaposto": segnaposto,
            "utcs_7_15": {i: utcs.get(i) for i in range(7, 16)},
            "terminatori_7_15": {i: ("CRLF" if terms[i - 1] == b"\r\n" else "LF")
                                 for i in range(7, 16) if i <= len(terms)}}


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest(ledger, reference, item, overrides, verbose=True):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    if not os.path.isfile(ledger):
        chk("1  registro presente", False, ledger)
        return _report(checks, verbose)
    chk("1  registro presente", True, ledger)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(ledger)

    chk("2  righe = %d" % EXPECTED_LINES_BEFORE, len(recs) == EXPECTED_LINES_BEFORE,
        "trovate %d" % len(recs))
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    chk("2b la riga %d si ri-serializza byte per byte identica" % len(recs),
        rt == lines[-1])

    ok_ref = os.path.isfile(reference)
    file_sha = sha256_file(reference) if ok_ref else ""
    chk("3  sha256 del reference invariato", file_sha == REFERENCE_FILE_SHA256,
        file_sha[:16] if file_sha else "assente")
    chk("4  digest = quello citato nella riga %d" % len(recs),
        recs[-1].get("reference_file_sha256") == file_sha)
    self_sha = ""
    if ok_ref:
        self_sha = json.load(open(reference, "r", encoding="utf-8")).get("_self_sha256", "")
    chk("5  _self_sha256 presente, atteso, e uguale a quello della riga %d" % len(recs),
        bool(self_sha) and self_sha == REFERENCE_SELF_SHA
        and self_sha == recs[-1].get("reference_self_sha256"))

    blob = raw.decode("utf-8", "replace")
    dup = any(r.get("item") == item for r in recs) if item else False
    chk("6  idempotenza (marker 47 assente, item non gia' usato)",
        (MARKER not in blob) and not dup)
    chk("6b prerequisito: il record 46 e' presente ED e' sulla riga %d"
        % EXPECTED_LINES_BEFORE,
        (MARKER_46 in blob)
        and (MARKER_46 in json.dumps(recs[EXPECTED_LINES_BEFORE - 1],
                                     ensure_ascii=False)))

    G = analyse_gates(ledger)
    chk("M1 il profilo dei fine riga e' quello citato: %d CRLF, %d LF, righe %s"
        % (G["n_crlf"], G["n_lf"], G["righe_fuori"]),
        G["righe_fuori"] == RIGHE_LF and G["n_lf"] == len(RIGHE_LF),
        "citate %s" % RIGHE_LF)
    chk("M2 le quattro righe con l'utc segnaposto sono quelle citate",
        G["segnaposto"] == RIGHE_SEGNAPOSTO,
        "trovate %s, citate %s" % (G["segnaposto"], RIGHE_SEGNAPOSTO))
    chk("M3 il registro resta LEGGIBILE: %d record, zero malformati"
        % G["n_record"], G["n_record"] == EXPECTED_LINES_BEFORE,
        "e' cio' che rende l'anomalia inerte oggi")

    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha,
                                                       self_sha, item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 44-46 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 il record dice che NULLA viene riscritto",
            "rewrites nothing" in json.dumps(rec["rules"])
            and "NOT rewritten" in rec["new_value"]["what_is_NOT_done"])
        chk("11 dice perche' e' inerte oggi",
            "reads RECORDS" in rec["new_value"]["why_it_is_inert_today"])
        chk("12 e perche' si registra lo stesso",
            "BEFORE it matters" in json.dumps(rec["new_value"]))
        chk("13 collega la collisione di utc al record 42",
            "record 42" in json.dumps(rec["new_value"]["what_it_is"]))
        chk("13a dice cosa fare se un digest verra' aggiunto",
            "Hash the records, not the bytes" in json.dumps(rec["rules"])
            or "over the RECORDS" in rec["new_value"]
            ["what_to_do_if_a_digest_is_ever_added"])
        chk("13b cita il BOM come secondo esempio",
            "BOM" in json.dumps(rec["new_value"]))
        chk("13c lingua del record: inglese",
            ("perche'" not in txt) and ("emisferi" not in txt))
        chk("13d document ereditato dalla riga %d" % len(recs),
            rec["document"] == recs[-1].get("document"))
        chk("13e numbering_rule cita il record %d" % (len(recs) + 1),
            (str(len(recs) + 1) in str(rec.get("numbering_rule")))
            and ("record %d." % len(recs) not in str(rec.get("numbering_rule"))))
    else:
        for n in ("8 schema", "9 serializzazione", "10 nulla riscritto"):
            chk(n, False, "manca --item")

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


def parse_overrides(items):
    ov = {}
    for it in (items or []):
        if "=" not in it:
            fail("--set richiede chiave=valore, ricevuto %r" % it)
        k, v = it.split("=", 1)
        ov[k] = None if v == "null" else v
    return ov












def cmd_gates(args):
    G = analyse_gates(args.ledger)
    if G["errore"]:
        fail(G["errore"])
    print("=== PROFILO DEL REGISTRO ===")
    print("  record            : %d" % G["n_record"])
    print("  fine riga         : CRLF=%d  LF=%d" % (G["n_crlf"], G["n_lf"]))
    print("  righe fuori magg. : %s   (citate %s)" % (G["righe_fuori"], RIGHE_LF))
    print("  utc segnaposto %s : righe %s   (citate %s)"
          % (UTC_SEGNAPOSTO, G["segnaposto"], RIGHE_SEGNAPOSTO))
    print("")
    print("  riga  term   utc")
    for i in sorted(G["terminatori_7_15"]):
        print("  %4d  %-5s %s" % (i, G["terminatori_7_15"][i], G["utcs_7_15"].get(i)))
    print("")
    print("  Il registro resta LEGGIBILE - %d record, zero malformati - ed e'"
          % G["n_record"])
    print("  cio' che rende l'anomalia inerte OGGI. Nulla viene riscritto.")
    return 0


def cmd_inspect(args):
    if not os.path.isfile(args.ledger):
        fail("registro assente: %s" % args.ledger)
    recs = read_ledger(args.ledger)[0]
    print("registro: %s   righe: %d" % (args.ledger, len(recs)))
    ck = common_keys(recs, 3)
    print("chiavi comuni (%d): %s" % (len(ck), ck))
    for i, r in enumerate(recs[-3:], start=len(recs) - 2):
        print("  riga %2d  item: %r" % (i, r.get("item")))
    print("")
    return cmd_gates(args)


def cmd_dump(args):
    recs = read_ledger(args.ledger)[0]
    if not (1 <= args.n <= len(recs)):
        fail("riga %d fuori intervallo 1..%d" % (args.n, len(recs)))
    print(json.dumps(recs[args.n - 1], ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def cmd_selftest(args):
    return 1 if selftest(args.ledger, args.reference, args.item,
                         parse_overrides(args.set)) else 0


def cmd_append(args):
    if not args.item:
        fail("--item obbligatorio.")
    ov = parse_overrides(args.set)
    nfail = selftest(args.ledger, args.reference, args.item, ov)
    print("")
    if nfail:
        fail("selftest fallito (%d controlli): nessuna scrittura." % nfail)
    recs, newline, pure_ascii, sorted_keys, raw, lines, terms = read_ledger(args.ledger)
    file_sha = sha256_file(args.reference)
    self_sha = json.load(open(args.reference, "r", encoding="utf-8")).get("_self_sha256", "")
    rec, unfilled, extras, required = build_record(recs, args.reference, file_sha,
                                                   self_sha, args.item, ov)
    if unfilled:
        fail("chiavi che non so riempire: %s" % ", ".join(unfilled))
    if extras and not args.allow_extra_keys:
        fail("il record 47 aggiunge le chiavi %s: --allow-extra-keys."
             % ", ".join(extras))
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
    last = json.dumps(recs[-1], ensure_ascii=False)
    print("  marker nella riga %-2d      : %s" % (AMEND_POSITION, MARKER in last))
    ok &= MARKER in last
    rt = json.dumps(recs[-1], ensure_ascii=pure_ascii, sort_keys=True).encode("utf-8")
    print("  round-trip della riga %-2d  : %s" % (AMEND_POSITION, rt == lines[-1]))
    ok &= rt == lines[-1]
    n_crlf, n_lf, odd = eol_profile(terms)
    print("  le sei righe LF sono ANCORA li': %s" % (odd == RIGHE_LF))
    ok &= odd == RIGHE_LF
    print("  la riga nuova segue la maggioranza: %s" % (terms[-1] == b"\r\n"))
    ok &= terms[-1] == b"\r\n"
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 47 - fine riga anomalo nel registro")
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    p.add_argument("--reference", default=DEFAULT_REFERENCE)
    p.add_argument("--item", default=None)
    p.add_argument("--set", action="append", metavar="CHIAVE=VALORE")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    sub.add_parser("gates").set_defaults(func=cmd_gates)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    d = sub.add_parser("dump")
    d.add_argument("n", type=int)
    d.set_defaults(func=cmd_dump)
    ap = sub.add_parser("append")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-extra-keys", action="store_true")
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

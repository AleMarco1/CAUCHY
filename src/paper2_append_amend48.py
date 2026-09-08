#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_append_amend48.py - Emendamento 48: l'audit delle predizioni decise da un
attraversamento di soglia. Rilievo B.4 del secondo report.

Il referee osserva che P1 e' riportata come falsificata mentre dista 0.22 sigma
dalla soglia, e chiede di applicare retroattivamente la disciplina gia' adottata
per B6. L'audit e' stato fatto su TUTTE le regole di decisione dichiarate, e P1
non e' l'unica.

I numeri si RILEGGONO: le sigma delle correlazioni parziali dal registro compD,
i Delta_ripattern dal registro della passata randomizzata. Nessun numero
trascritto salvo le soglie, che sono dichiarazioni e non misure.

Cancelli
--------
  G1..G6  come nei record 43-47;
  M1  P1: |r(w0)| ricalcolato dal registro compD, e la sua distanza dalla
      soglia in unita' di 1/sqrt(n-k-3), sotto 1 sigma;
  M2  le altre predizioni compD stanno OLTRE 2 sigma dalla loro soglia: l'audit
      non le tocca, e questo va verificato non asserito;
  M3  il ripattern: la distanza dalla soglia e' > 2 sigma in NGC e < 2 in SGC,
      che e' la correzione al record 44.

Uscita ASCII pura.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import sys

AMEND_POSITION = 48
EXPECTED_LINES_BEFORE = 47

REFERENCE_FILE_SHA256 = "332939bc2c7889f6cea369cb98535333c712fb1f7c0c89858061dedbb95d1d9d"
REFERENCE_SELF_SHA = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"

DEFAULT_LEDGER = os.path.join("src", "paper2_v1_amendments.jsonl")
DEFAULT_REFERENCE = os.path.join("src", "paper2_v1_reference.json")
COMPD = {"NGC": os.path.join("results", "paper2", "compD_NGC.jsonl"),
         "SGC": os.path.join("results", "paper2", "compD_SGC.jsonl")}
RIPATTERN = os.path.join("results", "paper2", "fase3_mock_ripattern.jsonl")
STD = os.path.join("results", "paper2", "fase3_mock.jsonl")

N_COMPD = 2000
K_CONTROLLI = 6                    # parziali su 7 parametri: 6 controlli
SOGLIA_P1 = 0.05
SOGLIA_RIPATTERN = 53.0

MARKER = "emendamento-48-audit-delle-predizioni-a-soglia"
MARKER_47 = "emendamento-47-fine-riga-anomalo-nel-registro-degli-emendamenti"
COMPANION_DOCUMENT = "referee report 2 §B.4; risposta_referee.md §3.9 e §4.6"


KEY = "no_threshold_is_crossed_without_the_uncertainty_of_the_quantity_tested"

JSON_PATH = ("paper2_prereg_v1.md §5.3, §5.4, §5.6; src/paper2_compD_partialcorr.py "
             "(PREDICTIONS); results/paper2/compD_{NGC,SGC}.jsonl; "
             "results/paper2/fase3_mock_ripattern.jsonl")

OLD_VALUE = (
    "Section 4.1 of the response already accepted, for the second B6 prediction, that a branch is not "
    "declared falsified without an error bar on the quantity tested: the 'stays around 45' verdict "
    "was withdrawn because 45 sits 0.94 sigma away. The same discipline was NOT applied elsewhere. "
    "Section 3.9 reports 'P1 - |r(w0)| < 0.05 - fails again in NGC at +0.0549' and record 43 presents "
    "the reproduction of that failure as a methodological virtue: 'a falsified prediction that "
    "reproduces identically is better evidence than a confirmed one'."
)

NEW_VALUE = {
    "P1_is_withdrawn_as_a_falsification": {
        "the_arithmetic": ("With n = 2000 and six controlled parameters the standard error of a "
                           "partial correlation is 1/sqrt(n - k - 3) = 0.0224. The observed +0.0549 "
                           "sits 0.22 sigma from the 0.05 threshold, and the run's own CI, [+0.0111, "
                           "+0.0985], straddles it."),
        "so_what_it_is": ("P1 is neither confirmed nor falsified. It DOES NOT DECIDE. A value that "
                          "does not distinguish the two sides of a threshold is not evidence about "
                          "the threshold."),
        "and_the_two_hemispheres_land_on_OPPOSITE_sides": ("NGC gives +0.0549, formally a FAILURE; "
                                                           "SGC gives +0.0474, formally a PASS. The "
                                                           "two sit 0.22 and 0.12 sigma from the "
                                                           "threshold. The same undecidable quantity "
                                                           "produces opposite verdicts in the two "
                                                           "hemispheres, which is not a hemispheric "
                                                           "signature but a demonstration that the "
                                                           "threshold has no discriminating power. "
                                                           "Had SGC been reported first, P1 would "
                                                           "have been recorded as CONFIRMED and "
                                                           "reproduced - the mirror image of the "
                                                           "error actually made."),
        "and_the_celebration_in_record_43_is_corrected": ("What reproduced identically was a "
                                                          "threshold crossing without power. "
                                                          "Reproducibility of an undecidable "
                                                          "quantity is reproducibility, not "
                                                          "evidence. Record 43 is not rewritten - "
                                                          "the ledger is append-only - it is "
                                                          "corrected here."),
    },
    "the_audit_of_every_declared_decision_rule": {
        "what_was_asked": ("For each declared rule: how far is the measurement from the threshold, "
                           "in units of the uncertainty of the quantity tested?"),
        "decided_comfortably": ("P2 at 6.6 sigma above 0.25; P3 at about 6; P4 at 8.2 sigma below "
                                "0.40. These stand and are untouched."),
        "decided_but_narrowly_and_without_a_declared_sigma": ("P5, orthogonality of the design, 2.8 "
                                                              "sigma below 0.10; and section 4.5 "
                                                              "term (c), 2.8 sigma below 0.212. Both "
                                                              "hold. Neither declared its "
                                                              "uncertainty at the moment of "
                                                              "deciding, and both are to be reported "
                                                              "with their sigma rather than "
                                                              "reopened."),
        "no_declared_uncertainty_AT_ALL": ("Prereg section 5.4, |F_req - 1| against 0.027, where "
                                           "F_req comes from a linear extrapolation of a response "
                                           "carrying about 100 generators of realisation "
                                           "uncertainty; and section 5.6, |D_obs - D_pred| against "
                                           "53. Neither can be evaluated as stated. Section 5.6's "
                                           "declared signature is falsified anyway (record 46)."),
        "and_the_E1_E4_rule_itself": ("Delta D_max against 53. With the denominator the referee's "
                                      "A.3 establishes - the per-realisation dispersion, because the "
                                      "claim is about the observed field, which has N = 1 - the "
                                      "measurement is not distinguishable from zero and the "
                                      "threshold is crossed by nothing. The four-outcome rule "
                                      "decides on a quantity it cannot resolve."),
    },
    "a_correction_to_record_44_that_the_audit_found": {
        "what_44_says": ("All four Delta_ripattern below the declared threshold of 53. True as a "
                         "point reading."),
        "what_the_audit_adds": ("The DISTANCE from the threshold is 2.8 sigma in NGC (6.96 +- 16.40 "
                                "and -9.38 +- 15.72) but only 1.4 and 1.9 sigma in SGC (-33.84 +- "
                                "13.50 and -28.63 +- 12.92). In SGC the repattern is not shown to be "
                                "below threshold: it is NOT DISTINGUISHABLE from the threshold."),
        "and_it_cuts_the_way_the_referee_says": ("Section C of the second report argues we are "
                                                 "discarding a real SGC signal. The audit agrees "
                                                 "from the inside: our own 'below threshold' does "
                                                 "not hold there."),
    },
    "the_rule": ("No threshold is crossed without the uncertainty of the quantity tested, stated at "
                 "the moment the rule is declared and not afterwards. A rule whose threshold cannot "
                 "be compared to an uncertainty is not a decision rule: it is a number with a "
                 "comparison operator."),
    "what_this_does_not_do": ("It reopens no measurement and changes no deposited value. P2, P3, P4 "
                              "stand. P5 and term (c) stand and gain a sigma. What changes is which "
                              "verdicts the programme is entitled to state."),
}

RULES = {
    "amends_records": [43, 44],
    "companion_document": COMPANION_DOCUMENT,
    "marker": MARKER,
    "no_threshold_without_the_uncertainty_of_the_quantity_tested": ("Stated when the rule is "
                                                                    "declared, not when the result "
                                                                    "arrives. Otherwise the verdict "
                                                                    "inherits the significance of "
                                                                    "the denominator chosen "
                                                                    "afterwards."),
    "reproducing_an_undecidable_quantity_is_not_evidence": ("Record 43 called the reproduction of "
                                                            "P1's failure better evidence than a "
                                                            "confirmation. What reproduced was a "
                                                            "threshold crossing without power."),
    "a_verdict_NEAR_its_threshold_is_reported_with_its_distance": ("Record 44's 'all four below 53' "
                                                                   "is 2.8 sigma in NGC and 1.4 in "
                                                                   "SGC. The two are not the same "
                                                                   "verdict."),
    "what_this_does_not_do": ("No measurement reopened, no deposited value changed."),
}

REASON = (
    "The second referee report, B.4, observes that P1 is reported as falsified while sitting 0.22 "
    "sigma from its threshold, and asks that the discipline already adopted for B6 in section 4.1 be "
    "applied retroactively. It was, to every declared decision rule, and P1 is not the only case. P1 "
    "IS WITHDRAWN AS A FALSIFICATION: with n = 2000 and six controls the standard error on a partial "
    "correlation is 0.0224, the observed +0.0549 is 0.22 sigma from 0.05, and the run's own CI "
    "straddles the threshold. It does not decide. And the celebration in record 43 - that a "
    "reproduced falsification is better evidence than a confirmation - is corrected: what reproduced "
    "identically was a threshold crossing without power. THE AUDIT. P2, P3 and P4 are decided "
    "comfortably at 6.6, ~6 and 8.2 sigma and are untouched. P5 and section 4.5's term (c) hold at "
    "2.8 sigma each but declared no uncertainty when they decided; they are reported with their sigma "
    "rather than reopened. Prereg sections 5.4 and 5.6 declare NO uncertainty at all - F_req against "
    "0.027, where F_req extrapolates a response carrying ~100 generators of realisation uncertainty, "
    "and |D_obs - D_pred| against 53 - and cannot be evaluated as stated. And the E1-E4 rule itself "
    "decides Delta D_max against 53 with a denominator that, by the referee's A.3, is the wrong one "
    "for a claim about a field with N = 1. AND THE AUDIT FOUND SOMETHING IN RECORD 44: 'all four "
    "below threshold' is 2.8 sigma in NGC but 1.4 and 1.9 in SGC. In SGC the repattern is not shown "
    "to be below threshold - it is not distinguishable FROM the threshold - which cuts the way "
    "section C of the report argues, from the inside."
)

EVIDENCE = (
    "Audit of 6 Sep 2026. Partial-correlation standard error 1/sqrt(2000 - 6 - 3) = 0.02240. P1: "
    "NGC r(w0) = +0.0548663663566655, |r - 0.05| / sigma = 0.22; run CI [+0.0111, +0.0985]. P2: "
    "r(n_s) = +0.3976203530942741, (r - 0.25)/sigma = 6.59. P3: |r(sigma_8)| = 0.1897288421845145 "
    "against |r(n_s)|. P4: R^2 = 0.2605774275605681 against 0.40, SE(R^2) ~ 2R(1-R^2)/sqrt(n) = "
    "0.0169, distance 8.2. P5: worst |r| between parameters 0.0372894903 against 0.10, distance 2.80. "
    "Section 4.5 term (c): worst deviation 0.0735 against 0.212, sigma of an sd ratio on 200 "
    "1/sqrt(2*199) = 0.0501, distance 2.76. Repattern, distance to the 53 threshold: NGC k=0 "
    "(53-6.96)/16.40 = 2.81, NGC k=1 (53-9.38)/15.72 = 2.77, SGC k=0 (53-33.84)/13.50 = 1.42, SGC "
    "k=1 (53-28.63)/12.92 = 1.89."
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













def _merge(records, want_rand):
    out = {}
    for r in records:
        if r.get("smoke"):
            continue
        if bool(r.get("replica_randomise", False)) != want_rand:
            continue
        slot = out.setdefault((r.get("region"), r.get("index")), {})
        for name, d in (r.get("points") or {}).items():
            if isinstance(d, dict):
                slot.setdefault(name, {}).update(d)
    return out


def analyse_gates():
    """Ricalcola le distanze dalle soglie. Nessun numero trascritto."""
    import statistics as st
    out = {"errore": None, "sigma_r": 1.0 / math.sqrt(N_COMPD - K_CONTROLLI - 3),
           "compD": {}, "ripattern": {}}
    for reg, path in sorted(COMPD.items()):
        if not os.path.isfile(path):
            out["errore"] = "registro assente: %s" % path
            return out
        recs = read_jsonl(path)[0]
        vivi = []
        for i, r in enumerate(recs):
            key = (r.get("schema"), r.get("utc"))
            if not any(isinstance(l.get("supersedes"), dict)
                       and (l["supersedes"].get("schema"),
                            l["supersedes"].get("utc")) == key
                       for l in recs[i + 1:]):
                vivi.append(r)
        if not vivi:
            out["errore"] = "%s: nessun record vivo" % path
            return out
        r = vivi[-1]
        rows = {x["param"]: float(x["r_partial"]) for x in r.get("rows", [])}
        out["compD"][reg] = {"r": rows, "r2": float(r["r2_multi"])}
    for lev, campo in (("k0", "N_H1_k0"), ("k1", "N_H1")):
        pass
    if not (os.path.isfile(RIPATTERN) and os.path.isfile(STD)):
        out["errore"] = "registri del ripattern assenti"
        return out
    std = _merge(read_jsonl(STD)[0], False)
    rnd = _merge(read_jsonl(RIPATTERN)[0], True)
    for reg in ("NGC", "SGC"):
        for lev, campo in (("k0", "N_H1_k0"), ("k1", "N_H1_k1")):
            a, b = {}, {}
            for src_, dst in ((std, a), (rnd, b)):
                for (g, i), pts in src_.items():
                    if g == reg and all(p in pts and campo in pts[p]
                                        for p in ("B1", "B5")):
                        dst[i] = float(pts["B5"][campo]) - float(pts["B1"][campo])
            com = sorted(set(a) & set(b))
            if len(com) < 2:
                continue
            dd = [b[i] - a[i] for i in com]
            m = st.mean(dd)
            sem = st.stdev(dd) / math.sqrt(len(dd))
            out["ripattern"][(reg, lev)] = {
                "delta": m, "sem": sem,
                "distanza": (SOGLIA_RIPATTERN - abs(m)) / sem if sem else float("nan")}
    return out


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
    chk("6  idempotenza (marker 48 assente, item non gia' usato)",
        (MARKER not in blob) and not dup)
    chk("6b prerequisito: il record 47 e' presente ED e' sulla riga %d"
        % EXPECTED_LINES_BEFORE,
        (MARKER_47 in blob)
        and (MARKER_47 in json.dumps(recs[EXPECTED_LINES_BEFORE - 1],
                                     ensure_ascii=False)))

    def dentro(frase, dove):
        """Confronto di PROSA: minuscole e spazi collassati. Le maiuscole di
        enfasi hanno gia' fatto fallire due controlli sani, nel record 45 e
        qui: si toglie la causa invece dei sintomi."""
        return (" ".join(frase.lower().split())
                in " ".join(json.dumps(dove, ensure_ascii=False).lower().split()))

    G = analyse_gates()
    if G["errore"]:
        chk("M1 registri di misura presenti", False, G["errore"])
        return _report(checks, verbose)

    s = G["sigma_r"]
    r_w0 = G["compD"]["NGC"]["r"].get("w0")
    d_p1 = abs(abs(r_w0) - SOGLIA_P1) / s if r_w0 is not None else None
    chk("M1 P1: |r(w0)| dista MENO di 1 sigma dalla soglia -> non decide",
        d_p1 is not None and d_p1 < 1.0,
        "r=%.7f, sigma=%.5f, distanza %.2f sigma" % (r_w0, s, d_p1)
        if d_p1 is not None else "r(w0) assente")

    bad = []
    for reg in ("NGC", "SGC"):
        rr = G["compD"][reg]["r"]
        if (rr["n_s"] - 0.25) / s < 2:
            bad.append("%s P2 a %.1f sigma" % (reg, (rr["n_s"] - 0.25) / s))
        r2 = G["compD"][reg]["r2"]
        se_r2 = 2 * math.sqrt(r2) * (1 - r2) / math.sqrt(N_COMPD)
        if (0.40 - r2) / se_r2 < 2:
            bad.append("%s P4 a %.1f sigma" % (reg, (0.40 - r2) / se_r2))
    r_w0_sgc = G["compD"]["SGC"]["r"].get("w0")
    opposti = (r_w0 is not None and r_w0_sgc is not None
               and (abs(r_w0) - SOGLIA_P1) * (abs(r_w0_sgc) - SOGLIA_P1) < 0)
    d_sgc = abs(abs(r_w0_sgc) - SOGLIA_P1) / s if r_w0_sgc is not None else None
    chk("M1b i due emisferi cadono su LATI OPPOSTI della soglia, entrambi sotto "
        "1 sigma: la soglia non discrimina",
        opposti and d_sgc is not None and d_sgc < 1.0 and d_p1 < 1.0,
        "NGC %.4f (%.2f sigma, %s), SGC %.4f (%.2f sigma, %s)"
        % (abs(r_w0), d_p1, "fallisce" if abs(r_w0) > SOGLIA_P1 else "passa",
           abs(r_w0_sgc), d_sgc, "fallisce" if abs(r_w0_sgc) > SOGLIA_P1 else "passa")
        if d_sgc is not None else "r(w0) SGC assente")

    chk("M2 P2 e P4 stanno OLTRE 2 sigma dalla soglia: l'audit non le tocca",
        not bad, ",".join(bad) if bad else "quattro confronti")

    ng = [G["ripattern"][k]["distanza"] for k in G["ripattern"] if k[0] == "NGC"]
    sg = [G["ripattern"][k]["distanza"] for k in G["ripattern"] if k[0] == "SGC"]
    chk("M3 ripattern: NGC oltre 2 sigma dalla soglia, SGC sotto",
        ng and sg and min(ng) > 2.0 and max(sg) < 2.0,
        "NGC %s, SGC %s" % (["%.2f" % x for x in ng], ["%.2f" % x for x in sg]))

    if item:
        rec, unfilled, extras, required = build_record(recs, reference, file_sha,
                                                       self_sha, item, overrides)
        txt = json.dumps(rec, ensure_ascii=False)
        chk("8  schema: chiavi comuni 45-47 tutte riempite (%d)" % len(required),
            not unfilled, ",".join(unfilled) if unfilled else "")
        one = json.dumps(rec, ensure_ascii=pure_ascii, sort_keys=True)
        chk("9  serializzazione su una riga e round-trip identico",
            ("\n" not in one) and json.loads(one) == rec)
        chk("10 P1 e' RITIRATA come falsificazione, non riclassificata",
            dentro("does not decide", rec["new_value"]
                   ["P1_is_withdrawn_as_a_falsification"]))
        chk("11 la celebrazione del record 43 e' corretta qui, non riscritta li'",
            dentro("append-only", rec["new_value"]["P1_is_withdrawn_as_a_falsification"]))
        chk("12 il record dichiara di emendare 43 e 44",
            rec["rules"]["amends_records"] == [43, 44])
        chk("13 le predizioni che REGGONO sono nominate",
            all(dentro(x, rec["new_value"]
                       ["the_audit_of_every_declared_decision_rule"])
                for x in ("P2 at 6.6 sigma", "P4 at 8.2 sigma", "These stand")))
        chk("13g i lati opposti sono registrati come dimostrazione di non-potere",
            dentro("opposite verdicts in the two hemispheres", rec["new_value"])
            and dentro("would have been recorded as confirmed", rec["new_value"]))
        chk("13a i due casi SENZA incertezza dichiarata sono nominati",
            "5.4" in json.dumps(rec["new_value"]) and "5.6" in json.dumps(rec["new_value"]))
        chk("13b la correzione al record 44 e' esplicita",
            dentro("not distinguishable from the threshold", rec["new_value"]))
        chk("13c e riconosce che taglia come dice il referee",
            dentro("from the inside", rec["new_value"]))
        chk("13d la regola e' scritta come regola, in RULES e in new_value",
            dentro("stated when the rule is declared", rec["rules"])
            and dentro("at the moment the rule is declared", rec["new_value"]))
        chk("13e lingua del record: inglese",
            ("perche'" not in txt) and ("emisferi" not in txt))
        chk("13f numbering_rule cita il record %d" % (len(recs) + 1),
            str(len(recs) + 1) in str(rec.get("numbering_rule")))
    else:
        for n in ("8 schema", "9 serializzazione", "10 ritiro di P1"):
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
    G = analyse_gates()
    if G["errore"]:
        fail(G["errore"])
    s = G["sigma_r"]
    print("=== AUDIT DELLE SOGLIE ===")
    print("  sigma di una correlazione parziale, n=%d, %d controlli: %.5f"
          % (N_COMPD, K_CONTROLLI, s))
    print("")
    print("  %-4s %-10s %10s %9s %9s  %s"
          % ("reg", "predizione", "soglia", "misurato", "distanza", "esito"))
    for reg in ("NGC", "SGC"):
        rr = G["compD"][reg]["r"]
        r2 = G["compD"][reg]["r2"]
        righe = [("P1 |r(w0)|", SOGLIA_P1, abs(rr["w0"]),
                  abs(abs(rr["w0"]) - SOGLIA_P1) / s),
                 ("P2 r(n_s)", 0.25, rr["n_s"], (rr["n_s"] - 0.25) / s),
                 ("P4 R^2", 0.40, r2,
                  (0.40 - r2) / (2 * math.sqrt(r2) * (1 - r2) / math.sqrt(N_COMPD)))]
        for nome, soglia, val, dist in righe:
            print("  %-4s %-10s %10.4f %9.4f %9.2f  %s"
                  % (reg, nome, soglia, val, dist,
                     "NON DECIDE" if dist < 1 else
                     ("stretto" if dist < 2 else "deciso")))
    print("")
    print("  %-4s %-10s %10s %9s %9s  %s"
          % ("reg", "livello", "soglia", "|Delta|", "distanza", "esito"))
    for (reg, lev), v in sorted(G["ripattern"].items()):
        print("  %-4s %-10s %10.0f %9.2f %9.2f  %s"
              % (reg, lev, SOGLIA_RIPATTERN, abs(v["delta"]), v["distanza"],
                 "NON DISTINGUIBILE dalla soglia" if v["distanza"] < 2
                 else "sotto soglia"))
    print("")
    rn = G["compD"]["NGC"]["r"]["w0"]; rs = G["compD"]["SGC"]["r"]["w0"]
    if (abs(rn) - SOGLIA_P1) * (abs(rs) - SOGLIA_P1) < 0:
        print("  P1 cade su LATI OPPOSTI nei due emisferi -- NGC %s, SGC %s -- a"
              % ("fallisce" if abs(rn) > SOGLIA_P1 else "passa",
                 "fallisce" if abs(rs) > SOGLIA_P1 else "passa"))
        print("  %.2f e %.2f sigma dalla soglia. Non e' una firma emisferica: e'"
              % (abs(abs(rn) - SOGLIA_P1) / s, abs(abs(rs) - SOGLIA_P1) / s))
        print("  la dimostrazione che la soglia non discrimina.")
        print("")
    print("  Il verdetto «tutti e quattro sotto» del record 44 e' a 2.8 sigma in")
    print("  NGC e a 1.4-1.9 in SGC. Non sono lo stesso verdetto.")
    return 0


def cmd_inspect(args):
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
        fail("il record 48 aggiunge le chiavi %s: --allow-extra-keys."
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
    print("  emenda i record           : %s" % recs[-1].get("rules", {}).get("amends_records"))
    print("  i record 43 e 44 sono INTATTI: %s"
          % (("emendamento-43" in json.dumps(recs[42], ensure_ascii=False))
             and ("emendamento-44" in json.dumps(recs[43], ensure_ascii=False))))
    print("  esito                     : %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def main():
    p = argparse.ArgumentParser(
        description="Emendamento 48 - audit delle predizioni a soglia")
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_tex_7_2.py -- Paper 2, manoscritto: il §7.2 (Zero by theorem, zero by measurement) e la
didascalia di F7.

Tre sostituzioni atomiche in papers/paper2/MNRAS/paper2_mnras.tex, ognuna su un'ancora che deve
comparire UNA volta:
  1. la nota di stesura del §7.2 -> quattro capoversi e mezzo di testo, con il commento '% Fonti:';
  2. la nota del segnaposto di F7 ("Normalizzazione da dichiarare") -> script e registro;
  3. la didascalia di F7 -> la normalizzazione decisa il 25 set, dichiarata.

Prima di scrivere:
  - sha del tex = 934b31a2... (quello della consegna del 25 set); se e' gia' quello dopo la patch, lo dice;
  - la figura F7 esiste e un record di results/paper2/fig_F7.jsonl la descrive (lanciare prima
    'python src/paper2_fig_F7.py run');
  - ogni numero del testo nuovo e' riscontrato su quel record: formattato dal registro, deve comparire
    nel testo cosi' come e' scritto. Nessun numero e' riscritto a mano da qui.
Fine riga: quello del file (LF o CRLF), mai misto. Scrittura atomica (temporaneo + os.replace).
Ricevuta: logs/patch_tex_7_2.json.

Sottocomandi: selftest | dry-run | apply | verify. Dalla radice del repository.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

J = os.path.join
TEX = J("papers", "paper2", "MNRAS", "paper2_mnras.tex")
REG = J("results", "paper2", "fig_F7.jsonl")
PDF = J("papers", "paper2", "MNRAS", "figures", "F7_response_function.pdf")
RECEIPT = J("logs", "patch_tex_7_2.json")
SHA_BEFORE = "934b31a28e808cb3e07f6e048e9d8fad0a00d1f9e3a3e40db92d44eecb06f25b"

OLD_TODO = r"""\todo{la funzione di risposta: barre a zero per teorema e a zero per misura.
Citare la Fig.~\ref{fig:response}.}
"""

NEW_TEXT = r"""% Fonti: results/paper2/fig_F7.jsonl (src/paper2_fig_F7.py, cancelli C1-C8), il record che descrive
% figures/F7_response_function.pdf: result.nwlh (excursion_gen di compD_{NGC,SGC}.jsonl diviso per la
% dispersione della calotta; errore di Fisher a 1 sigma sulla r grezza), result.fap
% (fase3_analisi.jsonl, levels.k0.DD_max_B5_B1: mock_mean_diff, desi_offset, estimate, sem),
% result.alpha_iso (fase3.jsonl, dodici record 'derived'), result.zsigma, result.deficit_in_dispersions.
% Normalizzazione decisa il 25 set (checklist 3.39, Z-F7): 312.989 / 197.787 a k = 0 (budget, riga B0).
% Larghezze: linea B da B1 a B5, 0.0590 in F_AP; inviluppo fisico 0.0666 (Section 4.2).

Figure~\ref{fig:response} puts the three levers on one scale. For each parameter
$\theta$ it shows the change of the mean mock count across the interval that this
analysis samples, in units of the per-realization dispersion of the count in each
cap at $k = 0$, 313.0 generators in NGC and 197.8 in SGC (Table~\ref{tab:budget},
row B0). For the seven parameters of the nwLH suite the interval is the prior of
the Latin hypercube, and the change is the slope of the regression of $\NH$ on
$\theta$ over the 2000 mocks of each cap times the width of the prior. In these
units a bar is the raw correlation of the count with $\theta$ times the ratio of
the width of the prior to its standard deviation, 3.46 for every parameter of the
hypercube: the bars are raw correlations on a scale shared with the geometry, not
the partial correlations of Table~\ref{tab:partial}. For $\FAP$ the interval is
line B from B1 to B5, and the change is the paired difference of the mean over
200 mocks at $k = 0$, the level at which the dispersion is defined; the primary
level of Section~\ref{sec:apdeficit} is $k = 1$.

One response is zero by theorem. A dilation of the comoving positions leaves the
count unchanged when the grid is dilated with them
(Proposition~\ref{prop:dilation}), so the response to $\aiso$ is zero, and the six
points of the isotropic line reproduce the fiducial count of the data in both caps
and at both erosion levels (Section~\ref{sec:isotropic}).
Proposition~\ref{prop:monotone} adds no bar: no parameter of the suite acts on the
filtered field through its amplitude alone (Section~\ref{sec:variance}).

Two responses are bounded by measurement. Those to $w_0$ and $M_\nu$ stay below
three standard errors in both caps: $+0.19 \pm 0.08$ and $+0.17 \pm 0.08$
dispersions for $w_0$ in NGC and SGC, $-0.17 \pm 0.08$ and $-0.03 \pm 0.08$ for
$M_\nu$, with the standard error of the raw correlation. As limits
$|\Delta| + 3\sigma$, the count moves by less than 0.42 and 0.40 dispersions
across the whole prior of $w_0$, and by less than 0.40 and 0.26 across that of
$M_\nu$. For $w_0$ this is the statement of Section~\ref{sec:ceiling} in another
form: a prior 0.6 wide against half-widths of 3.1 and 3.6.

The other responses are measured, each at five standard errors or more. The
spectral index leads, with 1.30 and 1.36 dispersions across its prior, followed
by $h$ (0.73 and 0.67), $\sigma_8$ (0.63 and 0.81), $\Omega_m$ (0.53 and 0.47)
and $\Omega_b$ ($-0.44$ and $-0.42$). From B1 to B5 the mock count falls by
$0.70 \pm 0.04$ dispersions in NGC and $0.69 \pm 0.05$ in SGC. Unlike the
parameters of the suite, $\FAP$ also moves the data, whose count falls by 104 and
61 generators over the same interval, so the deficit moves by $-0.36$ and $-0.38$
dispersions, about half the mock-side response (Section~\ref{sec:factortwo}).
For the parameters of the suite the data do not change, and the response of $D$
is that of the mock count.

The heights depend on the intervals. The priors of the suite are wide, while the
interval of $\FAP$ is that of the pre-registered statistic, comparable in width to
the physical envelope (Section~\ref{sec:anisotropic}); the figure ranks responses
over the ranges this analysis samples and does not compare derivatives. On the
same scale the deficit is 22.9 dispersions in NGC and 18.2 in SGC. No parameter
of the suite, moved across its whole prior, and no deformation along line B
changes the mean mock count by more than 1.4 dispersions.
"""

OLD_NOTE = r"""\figura{F7_response_function}{\columnwidth}{Script: src/paper2\_fig\_F7.py. Normalizzazione da dichiarare.}"""
NEW_NOTE = r"""\figura{F7_response_function}{\columnwidth}{Script pronto: src/paper2\_fig\_F7.py (selftest, run, verify); registro results/paper2/fig\_F7.jsonl.}"""

OLD_CAPTION = r"""\caption{The response function of $\NH$: $|\partial\NH/\partial\theta|$, normalized,
for $\theta \in \{\sigma_8, \Omega_m, \Omega_b, h, n_s, M_\nu, w_0, \aiso,
\FAP\}$. Bars that are zero by theorem are drawn differently from bars that are
zero, or bounded, by measurement.}"""

NEW_CAPTION = r"""\caption{The response function of $\NH$: the change of the mean mock count across
the interval sampled for each parameter $\theta$, in units of the per-realization
dispersion of the count at $k = 0$ (313.0 generators in NGC, 197.8 in SGC); NGC in
black, SGC in grey. Negative values: the count falls as $\theta$ increases, for
$\FAP$ from B1 to B5 (Section~\ref{sec:anisotropic}). For the seven parameters of
the nwLH suite the interval is the prior and the change is the regression slope
over 2000 mocks times its width, with $1\sigma$ errors from the raw correlation;
$w_0$ and $M_\nu$, below $3\sigma$, are drawn as the interval
$\pm(|\Delta| + 3\sigma)$ with the measured value marked. For $\FAP$, 200 paired
mocks; open diamonds mark the change of the deficit $D$, since $\FAP$ also moves
the data. $\aiso$ is zero by theorem (Proposition~\ref{prop:dilation}). Heights
compare responses over the sampled intervals, not derivatives.}"""

EDITS = [("nota del §7.2", OLD_TODO, NEW_TEXT),
         ("segnaposto di F7", OLD_NOTE, NEW_NOTE),
         ("didascalia di F7", OLD_CAPTION, NEW_CAPTION)]


class PatchError(Exception):
    pass


# ----------------------------------------------------------------------------- testo

def eol_of(text):
    crlf = text.count("\r\n")
    lf = text.count("\n")
    if crlf and crlf != lf:
        raise PatchError("fine riga misti nel tex: %d CRLF su %d LF" % (crlf, lf))
    return "\r\n" if crlf else "\n"


def patch_text(text):
    """Le tre sostituzioni, tutte o nessuna."""
    eol = eol_of(text)
    out = text
    for nome, old, new in EDITS:
        o, n = old.replace("\n", eol), new.replace("\n", eol)
        c = out.count(o)
        if c != 1:
            raise PatchError("ancora '%s': %d occorrenze invece di 1" % (nome, c))
        if n in out:
            raise PatchError("'%s': il testo nuovo e' gia' presente" % nome)
        out = out.replace(o, n)
    return out


def flat(s):
    return re.sub(r"\s+", " ", s)


# ----------------------------------------------------------------------------- numeri

def f2(x):
    return "%.2f" % x


def checks_from(res, disp):
    """(etichetta, frase attesa nel testo) costruite DAL REGISTRO; piu' condizioni sui numeri."""
    nw, fap, zs = res["nwlh"], res["fap"], res["zsigma"]
    N, S = nw["NGC"], nw["SGC"]
    pm = lambda q: "$%+.2f \\pm %.2f$" % (q["value"], q["sigma"])
    fr = []
    fr.append(("dispersioni", "cap at $k = 0$, %.1f generators in NGC and %.1f in SGC" % (disp["NGC"], disp["SGC"])))
    fr.append(("dispersioni, didascalia", "(%.1f generators in NGC, %.1f in SGC)" % (disp["NGC"], disp["SGC"])))
    ks = {round(v, 2) for v in res["span_over_sd"].values()}
    if len(ks) != 1:
        raise PatchError("span/sd non uguale per tutti i parametri: %r" % ks)
    fr.append(("span/sd", "deviation, %.2f for every parameter" % ks.pop()))
    fr.append(("w0", "%s and %s dispersions for $w_0$" % (pm(N["w0"]), pm(S["w0"]))))
    fr.append(("M_nu", "%s and %s for $M_\\nu$" % (pm(N["M_nu"]), pm(S["M_nu"]))))
    fr.append(("limiti w0", "less than %s and %s dispersions across the whole prior of $w_0$"
               % (f2(N["w0"]["limit"]), f2(S["w0"]["limit"]))))
    fr.append(("limiti M_nu", "less than %s and %s across that of $M_\\nu$"
               % (f2(N["M_nu"]["limit"]), f2(S["M_nu"]["limit"]))))
    fr.append(("semi-ampiezze", "a prior %.1f wide against half-widths of %.1f and %.1f"
               % (N["w0"]["span"], zs["NGC"]["halfwidth_cap_dispersion"], zs["SGC"]["halfwidth_cap_dispersion"])))
    fr.append(("n_s", "with %s and %s dispersions" % (f2(N["n_s"]["value"]), f2(S["n_s"]["value"]))))
    fr.append(("h", "$h$ (%s and %s)" % (f2(N["h"]["value"]), f2(S["h"]["value"]))))
    fr.append(("sigma_8", "$\\sigma_8$ (%s and %s)" % (f2(N["sigma_8"]["value"]), f2(S["sigma_8"]["value"]))))
    fr.append(("Omega_m", "$\\Omega_m$ (%s and %s)" % (f2(N["Omega_m"]["value"]), f2(S["Omega_m"]["value"]))))
    fr.append(("Omega_b", "$\\Omega_b$ ($%s$ and $%s$)" % (f2(N["Omega_b"]["value"]), f2(S["Omega_b"]["value"]))))
    fr.append(("F_AP lato mock", "falls by $%s \\pm %s$ dispersions in NGC and $%s \\pm %s$ in SGC" % (
        f2(-fap["NGC"]["value_mock"]), f2(fap["NGC"]["sigma"]), f2(-fap["SGC"]["value_mock"]), f2(fap["SGC"]["sigma"]))))
    fr.append(("F_AP dati", "whose count falls by %d and %d generators" % (-fap["NGC"]["desi_offset"], -fap["SGC"]["desi_offset"])))
    fr.append(("F_AP deficit", "the deficit moves by $%s$ and $%s$ dispersions" % (f2(fap["NGC"]["value_D"]), f2(fap["SGC"]["value_D"]))))
    d = res["deficit_in_dispersions"]
    fr.append(("deficit", "the deficit is %.1f dispersions in NGC and %.1f in SGC" % (d["NGC"], d["SGC"])))
    cond = []
    meas = [nw[c][p]["n_sigma"] for c in ("NGC", "SGC") for p in nw[c] if nw[c][p]["class"] == "measured"]
    bnd = sorted({p for c in ("NGC", "SGC") for p in nw[c] if nw[c][p]["class"] == "bounded"})
    cond.append(("misurati a cinque errori o piu'", min(meas) >= 5.0, "min %.2f" % min(meas)))
    cond.append(("limitati = {M_nu, w0}", bnd == ["M_nu", "w0"], str(bnd)))
    half = [fap[c]["value_D"] / fap[c]["value_mock"] for c in ("NGC", "SGC")]
    cond.append(("D circa meta' del lato mock", all(0.45 <= h <= 0.60 for h in half), "%.3f / %.3f" % tuple(half)))
    mx = max(res["max_abs_nwlh"], res["max_abs_fap_mock"])
    cond.append(("nessuna barra oltre 1.4", mx <= 1.4, "max %.3f" % mx))
    cond.append(("nessun limite oltre 1.4", all(nw[c][p]["limit"] <= 1.4 for c in ("NGC", "SGC") for p in nw[c]
                                                if nw[c][p]["limit"] is not None), "-"))
    return fr, cond


def check_numbers(text, res, disp):
    fr, cond = checks_from(res, disp)
    t = flat(text)
    bad = [(lab, s) for lab, s in fr if s not in t]
    badc = [(lab, info) for lab, ok, info in cond if not ok]
    if bad or badc:
        raise PatchError("riscontro fallito: frasi assenti %s; condizioni false %s" % (bad, badc))
    return len(fr), len(cond)


# ----------------------------------------------------------------------------- disco

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha_bytes(open(p, "rb").read())


def register_record():
    if not os.path.exists(PDF) or not os.path.exists(REG):
        raise PatchError("figura o registro di F7 assenti: lanciare prima 'python src/paper2_fig_F7.py run'")
    h = sha_file(PDF)
    recs = [json.loads(l) for l in open(REG, encoding="utf-8") if l.strip()]
    m = [r for r in recs if r.get("pdf", {}).get(PDF) == h]
    if not m:
        raise PatchError("nessun record di %s descrive la figura su disco (%s)" % (REG, h[:12]))
    return m[-1], h


def prepare():
    if not os.path.isdir("papers"):
        raise PatchError("lanciare dalla radice del repository")
    raw = open(TEX, "rb").read()
    sha = sha_bytes(raw)
    if os.path.exists(RECEIPT):
        rc = json.load(open(RECEIPT, encoding="utf-8"))
        if sha == rc.get("sha_after"):
            raise PatchError("gia' applicata: il tex ha lo sha registrato dopo la patch (%s)" % sha[:12])
    if sha != SHA_BEFORE:
        raise PatchError("sha del tex %s..., atteso %s...: il manoscritto non e' quello della consegna" % (sha[:12], SHA_BEFORE[:12]))
    text = raw.decode("utf-8")
    new = patch_text(text)
    rec, pdf_sha = register_record()
    n_fr, n_cond = check_numbers(new, rec["result"], rec["choices"]["dispersion"])
    new_raw = new.encode("utf-8")
    return raw, new_raw, rec, pdf_sha, n_fr, n_cond


def report(raw, new_raw, rec, pdf_sha, n_fr, n_cond):
    print("tex: %s  %d -> %d byte" % (TEX, len(raw), len(new_raw)))
    print("sha: %s... -> %s..." % (sha_bytes(raw)[:12], sha_bytes(new_raw)[:12]))
    print("ancore: 3/3 sostituite; note di stesura: %d -> %d" % (
        raw.decode("utf-8").count("\\todo{"), new_raw.decode("utf-8").count("\\todo{")))
    print("riscontro sul registro F7 (record %s, figura %s...): %d frasi e %d condizioni PASS"
          % (rec["utc"][:19], pdf_sha[:12], n_fr, n_cond))


def cmd_dry():
    raw, new_raw, rec, pdf_sha, n_fr, n_cond = prepare()
    report(raw, new_raw, rec, pdf_sha, n_fr, n_cond)
    print("ESITO: DRY-RUN PASS (nulla scritto)")


def cmd_apply():
    raw, new_raw, rec, pdf_sha, n_fr, n_cond = prepare()
    tmp = TEX + ".tmp_patch_7_2"
    with open(tmp, "wb") as fh:
        fh.write(new_raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, TEX)
    if sha_file(TEX) != sha_bytes(new_raw):
        raise PatchError("dopo la scrittura lo sha non coincide")
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    rc = {"schema": "paper2_patch_tex_7_2_v1", "utc": datetime.now(timezone.utc).isoformat(),
          "tex": TEX, "sha_before": sha_bytes(raw), "sha_after": sha_bytes(new_raw),
          "bytes_before": len(raw), "bytes_after": len(new_raw),
          "fig_F7_record_utc": rec["utc"], "fig_F7_pdf_sha": pdf_sha,
          "numbers_checked": n_fr, "conditions_checked": n_cond,
          "script_sha": sha_file(os.path.abspath(__file__))}
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    report(raw, new_raw, rec, pdf_sha, n_fr, n_cond)
    print("ricevuta: %s" % RECEIPT)
    print("ESITO: APPLICATA")


def cmd_verify():
    if not os.path.exists(RECEIPT):
        raise PatchError("ricevuta assente: la patch non e' stata applicata")
    rc = json.load(open(RECEIPT, encoding="utf-8"))
    sha = sha_file(TEX)
    rec, pdf_sha = register_record()
    text = open(TEX, "rb").read().decode("utf-8")
    n_fr, n_cond = check_numbers(text, rec["result"], rec["choices"]["dispersion"])
    same = sha == rc["sha_after"]
    print("tex: %s...  %s" % (sha[:12], "= sha dopo la patch" if same else "DIVERSO da %s... (modificato dopo)" % rc["sha_after"][:12]))
    print("riscontro sul registro F7: %d frasi e %d condizioni PASS" % (n_fr, n_cond))
    print("ESITO: %s" % ("PASS" if same else "PASS SUI NUMERI, tex modificato dopo la patch"))
    return 0


# ----------------------------------------------------------------------------- selftest

def _fixture(eol="\n"):
    body = ("\\subsection{Zero by theorem, zero by measurement}\n\\label{sec:zeros}\n" + OLD_TODO +
            "\\begin{figure}\n\\centering\n" + OLD_NOTE + "\n" + OLD_CAPTION + "\n\\label{fig:response}\n\\end{figure}\n")
    return body.replace("\n", eol)


def _res_fixture():
    def q(v, s, cls="measured", lim=None, span=0.3998):
        return {"value": v, "sigma": s, "n_sigma": abs(v) / s, "class": cls, "limit": lim, "span": span}
    # valori del registro a sei cifre (run su compD e fase3_analisi del 25 set): il selftest non arrotonda
    N = {"n_s": q(1.301962, 0.066495), "h": q(0.726514, 0.074037), "sigma_8": q(0.630757, 0.074876),
         "Omega_m": q(0.533467, 0.075608), "Omega_b": q(-0.442194, 0.076184),
         "M_nu": q(-0.165766, 0.077269, "bounded", 0.397574), "w0": q(0.191789, 0.077209, "bounded", 0.423417, 0.5997)}
    S = {"n_s": q(1.364972, 0.065409), "h": q(0.670010, 0.074547), "sigma_8": q(0.807535, 0.073234),
         "Omega_m": q(0.472622, 0.076004), "Omega_b": q(-0.424271, 0.076284),
         "M_nu": q(-0.027928, 0.077442, "bounded", 0.260254), "w0": q(0.166297, 0.077268, "bounded", 0.398102, 0.5997)}
    fap = {"NGC": {"value_mock": -0.696494, "sigma": 0.037130, "value_D": -0.364214, "desi_offset": -104},
           "SGC": {"value_mock": -0.687507, "sigma": 0.046360, "value_D": -0.379095, "desi_offset": -61}}
    return {"nwlh": {"NGC": N, "SGC": S}, "fap": fap,
            "zsigma": {"NGC": {"halfwidth_cap_dispersion": 3.126869}, "SGC": {"halfwidth_cap_dispersion": 3.606194}},
            "span_over_sd": {p: 3.461506 for p in N}, "deficit_in_dispersions": {"NGC": 22.942295, "SGC": 18.155733},
            "max_abs_nwlh": 1.364972, "max_abs_fap_mock": 0.696494}


DISP = {"NGC": 312.989, "SGC": 197.787}


def _t_lf():
    new = patch_text(_fixture())
    ok = NEW_NOTE in new and NEW_CAPTION in new and "Figure~\\ref{fig:response} puts" in new and "\\todo{" not in new
    try:
        patch_text(new)
    except PatchError:
        return ok
    return False


def _t_crlf():
    new = patch_text(_fixture("\r\n"))
    return new.count("\r\n") == new.count("\n") and NEW_CAPTION.replace("\n", "\r\n") in new


def _t_ancore():
    t = _fixture()
    try:
        patch_text(t.replace(OLD_NOTE, OLD_NOTE[:-3] + "xx}"))
    except PatchError:
        pass
    else:
        return False
    try:
        patch_text(t + OLD_CAPTION)
    except PatchError:
        return True
    return False


def _t_misti():
    try:
        patch_text(_fixture().replace("\n", "\r\n", 1))
    except PatchError:
        return True
    return False


def _t_numeri():
    new = patch_text(_fixture())
    n_fr, n_cond = check_numbers(new, _res_fixture(), DISP)
    ok = n_fr == 17 and n_cond == 5
    r = _res_fixture()
    r["nwlh"]["SGC"]["n_s"]["value"] = 1.3650001     # 1.37 invece di 1.36: l'errore che questo riscontro ha preso
    try:
        check_numbers(new, r, DISP)
    except PatchError:
        pass
    else:
        return False
    r = _res_fixture()
    r["nwlh"]["NGC"]["M_nu"]["class"] = "measured"
    try:
        check_numbers(new, r, DISP)
    except PatchError:
        return ok
    return False


def _t_ascii_graffe():
    for _, _, new in EDITS:
        try:
            new.encode("ascii")
        except UnicodeEncodeError:
            return False
        body = "\n".join(l for l in new.splitlines() if not l.lstrip().startswith("%"))
        if body.count("{") != body.count("}") or body.count("$") % 2:
            return False
    return True


TESTS = [
    ("tre sostituzioni su LF; seconda applicazione -> errore", _t_lf),
    ("CRLF conservato, nessun fine riga misto", _t_crlf),
    ("ancora assente o doppia -> errore", _t_ancore),
    ("fine riga misti nel file -> errore", _t_misti),
    ("riscontro: 17 frasi e 5 condizioni; un numero spostato o una classe diversa -> errore", _t_numeri),
    ("testo nuovo ASCII, graffe e dollari bilanciati", _t_ascii_graffe),
]


def selftest():
    ok = 0
    for nome, fn in TESTS:
        try:
            esito = bool(fn())
        except Exception as e:
            esito = False
            nome += " [%s: %s]" % (type(e).__name__, e)
        ok += esito
        if not esito:
            print("  FAIL  " + nome)
    print("selftest: %d/%d %s" % (ok, len(TESTS), "PASS" if ok == len(TESTS) else "FAIL"))
    return ok == len(TESTS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("comando", choices=["selftest", "dry-run", "apply", "verify"])
    a = ap.parse_args()
    try:
        if a.comando == "selftest":
            return 0 if selftest() else 1
        if not selftest():
            raise PatchError("selftest non superato")
        if a.comando == "dry-run":
            cmd_dry()
            return 0
        if a.comando == "apply":
            cmd_apply()
            return 0
        return cmd_verify()
    except PatchError as e:
        print("ERRORE: %s" % e)
        print("ESITO: FALLITO")
        return 2


if __name__ == "__main__":
    sys.exit(main())

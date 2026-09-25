#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_tex_10.py -- Paper 2, manoscritto: il §10 (Conclusions).

Un elenco numerato, come Marconi (2026a) section 8: sei contributi e un capoverso di chiusura. Nessun
numero nuovo: ogni numero del testo deve comparire altrove nel manoscritto (il patcher lo verifica), ogni
rimando e' a un'etichetta esistente, ogni chiave citata sta in bibliografia. I blocchi TESTO DECISO
restano identici byte per byte; nessuna sigla di citazione.

File: papers/paper2/MNRAS/paper2_mnras.tex, 2dab2a0b... (dopo la patch del §8). La bibliografia si legge
soltanto (2df3a499...).

Sottocomandi: selftest | dry-run | apply | verify. Dalla radice del repository.
Ricevuta: logs/patch_tex_10.json.
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
BIB = J("papers", "paper2", "MNRAS", "paper2.bib")
RECEIPT = J("logs", "patch_tex_10.json")
SHA_TEX = "2dab2a0bfb49ac296927a9f759fff57af6e6f821ad0b92444f8cf19ff49d3998"
SHA_BIB = "2df3a499447aff9e98a3c25060f4ddeeaf531e26aa98ab1cb88d90929ba7b58d"

OLD_10 = r"""\todo{elenco numerato, come M26 section 8.}
"""

NEW_10 = r"""% Fonti: nessun numero nuovo (verificato dal patcher). (i) par. 3; (ii) par. 4.4 e 4.5; (iii) par. 5.1-5.3;
% (iv) par. 6.1-6.3; (v) par. 7.1 e 7.2; (vi) par. 8.2. Forma: elenco come Marconi (2026a) section 8.
We have measured what the persistent-homology loop count of DESI BGS responds
to, along the three levers of the title, and separated what is invariant by
theorem from what is bounded or measured. Our contributions are:

(i) Two exact invariances and the parametrization they impose. An increasing
map of the filtered field leaves the persistence diagram unchanged
(Proposition~\ref{prop:monotone}), and so does an isotropic dilation of the
survey when the grid is dilated with it and the smoothing is fixed in grid units
(Proposition~\ref{prop:dilation}); the implementation departs from the second
by at most 0.0141 voxel (Proposition~2$'$). Lemma~\ref{lem:gauge} fixes the
Alcock--Paczy\'{n}ski parameter by a formula and the split between isotropic and
anisotropic parts by a Chebyshev gauge, so that only the anisotropic part of a
change of fiducial cosmology can act on the count.

(ii) The Alcock--Paczy\'{n}ski response of the deficit, measured. In both caps
and at both erosion levels the pre-registered statistic falls in the outcome of
a sub-dominant sensitivity, $\Dmax = -98.3 \pm 11.2$ generators in NGC and
$-91.1 \pm 8.7$ in SGC at $k = 1$, and over a sampled set that brackets the
physical envelope the deficit moves by at most 3.2 per cent of its value.
Limitation (ix) of \citet{M26} closes with a measurement. The mock count
responds about twice as strongly as the data, under either treatment of the
selection and without redshift-space distortions, and the reason is not known.

(iii) The weighting of the mocks, measured on the full ensemble. Assigning the
mock galaxies the radial weight of the data moves the count by
$-89.15 \pm 1.25$ and $-56.49 \pm 0.83$ generators, 1.24 and 1.57 per cent of
the deficit, towards the data. It explains neither the one-point disagreement
between mocks and data nor the maximum of the deficit under erosion: the six
rules declared before the ensemble was read fail in both caps.

(iv) The response to the parameters of the nwLH suite. The spectral index leads,
with partial correlations of $+0.398$ and $+0.416$. The slope in $w_0$ is
measured, and the dispersion of each cap divided by it gives a half-width of 3.1
and 3.6 on $w_0$, five and six times the range the suite samples. About half of
the variance of the count available to a predictor measured on the same
realization is a function neither of the parameters nor of the dark-matter power
spectrum, under the estimator used.

(v) The response function of the count (Fig.~\ref{fig:response}). On the scale
of the per-realization dispersion, no lever moves the mean mock count by more
than 1.4 within the ranges sampled, against a deficit of 22.9 in NGC and 18.2 in
SGC. In the updated budget no term approaches the deficit, and every measured
shift shortens it (Section~\ref{sec:budget}).

(vi) Five practices that extend those of \citet[section~6.2]{M26}
(Section~\ref{sec:practices}): state the units of the smoothing scale; weight
the mocks as the data are weighted; state the gauge of the decomposition; check
the admissibility of the smoothing for every geometry and every cap; and state
the convention of the Alcock--Paczy\'{n}ski parameter with its formula.

The deficit of \citet{M26} survives every lever this paper could move. What the
response function establishes is where it does not come from: not from the
geometry that a fiducial cosmology imposes on the survey, not from the weighting
of the mocks, and not from the parameters of the suite. The protocol under which
these statements were measured, its ledger and the failed predictions that
belong with them are released with the pipeline (Data Availability).
"""

TEX_EDITS = [("nota del par. 10", OLD_10, NEW_10)]
NEW_LABELS = set()


class PatchError(Exception):
    pass


def eol_of(text):
    crlf = text.count("\r\n")
    lf = text.count("\n")
    if crlf and crlf != lf:
        raise PatchError("fine riga misti: %d CRLF su %d LF" % (crlf, lf))
    return "\r\n" if crlf else "\n"


def apply_edits(text, edits):
    eol = eol_of(text)
    out = text
    for nome, old, new in edits:
        o, n = old.replace("\n", eol), new.replace("\n", eol)
        c = out.count(o)
        if c != 1:
            raise PatchError("ancora '%s': %d occorrenze invece di 1" % (nome, c))
        if n in out:
            raise PatchError("'%s': il testo nuovo e' gia' presente" % nome)
        out = out.replace(o, n)
    return out


def decided_blocks(text):
    return re.findall(r"% >>> TESTO DECISO.*?% <<< TESTO DECISO", text, flags=re.S)


def flat(s):
    return re.sub(r"\s+", " ", s)


def strip_comments(text):
    lines = [l for l in text.replace("\r\n", "\n").split("\n") if not l.lstrip().startswith("%")]
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", l) for l in lines)


def numbers_of(text):
    """I numeri del testo (non dei commenti), esclusi quelli dentro \\ref, \\label, \\cite e le opzioni."""
    t = strip_comments(text)
    t = re.sub(r"\\(ref|label|cite\w*)(\[[^\]]*\])?\{[^}]*\}", " ", t)
    t = re.sub(r"\\citet\[[^\]]*\]", " ", t)
    return set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?", t))


def check_all(old_tex, new_tex, new_bib):
    new_body = NEW_10
    rest = new_tex.replace(NEW_10.replace("\n", eol_of(new_tex)), " ")
    nums = numbers_of(new_body)
    allowed = {"9"}                        # d_med/9: la regola del par. 4.2, scritta come frazione
    rest_flat = flat(strip_comments(rest))
    missing = sorted(n for n in nums - allowed if not re.search(r"(?<![\w.])" + re.escape(n) + r"(?![\d])", rest_flat))
    labels = set(re.findall(r"\\label\{([^}]+)\}", new_tex))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", new_body))
    keys = set()
    for m in re.finditer(r"\\cite\w*(?:\[[^\]]*\])*\{([^}]+)\}", strip_comments(new_body)):
        keys |= {k.strip() for k in m.group(1).split(",")}
    bibkeys = set(re.findall(r"@\w+\{([^,]+),", new_bib))
    cond = [("numeri del par. 10 presenti altrove nel manoscritto", not missing, str(missing)),
            ("rimandi a etichette esistenti", refs <= labels, str(sorted(refs - labels))),
            ("etichette nuove presenti una volta", all(new_tex.count("\\label{%s}" % l) == 1 for l in NEW_LABELS), "-"),
            ("chiavi citate in bibliografia", keys <= bibkeys, str(sorted(keys - bibkeys))),
            ("nessuna sigla di citazione", not re.search(r"\\cite[tp]alias|\\defcitealias", new_tex), "-"),
            ("testi decisi invariati", decided_blocks(old_tex) == decided_blocks(new_tex), "-"),
            ("una sola nota di stesura in meno", old_tex.count("\\todo{") - new_tex.count("\\todo{") == 1, "-")]
    bad = [(lab, info) for lab, ok, info in cond if not ok]
    if bad:
        raise PatchError("controlli falliti: %s" % bad)
    return len(nums), sorted(keys), len(cond)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha_bytes(open(p, "rb").read())


def prepare():
    if not os.path.isdir("papers"):
        raise PatchError("lanciare dalla radice del repository")
    rt, rb = open(TEX, "rb").read(), open(BIB, "rb").read()
    if os.path.exists(RECEIPT):
        rc = json.load(open(RECEIPT, encoding="utf-8"))
        if sha_bytes(rt) == rc.get("tex_sha_after"):
            raise PatchError("gia' applicata: il tex ha lo sha registrato dopo la patch")
    if sha_bytes(rt) != SHA_TEX:
        raise PatchError("sha del tex %s..., atteso %s..." % (sha_bytes(rt)[:12], SHA_TEX[:12]))
    if sha_bytes(rb) != SHA_BIB:
        raise PatchError("sha della bib %s..., atteso %s..." % (sha_bytes(rb)[:12], SHA_BIB[:12]))
    t, b = rt.decode("utf-8"), rb.decode("utf-8")
    nt = apply_edits(t, TEX_EDITS)
    n_num, keys, n_cond = check_all(t, nt, b)
    return rt, nt.encode("utf-8"), n_num, keys, n_cond


def report(rt, nt, n_num, keys, n_cond):
    print("tex: %d -> %d byte, %s... -> %s...; note di stesura: %d -> %d" % (
        len(rt), len(nt), sha_bytes(rt)[:12], sha_bytes(nt)[:12],
        rt.decode("utf-8").count("\\todo{"), nt.decode("utf-8").count("\\todo{")))
    print("controlli: %d numeri del par. 10 tutti gia' nel manoscritto; chiavi citate %s; %d condizioni PASS"
          % (n_num, ", ".join(keys), n_cond))


def cmd_dry():
    report(*prepare())
    print("ESITO: DRY-RUN PASS (nulla scritto)")


def cmd_apply():
    rt, nt, n_num, keys, n_cond = prepare()
    tmp = TEX + ".tmp_patch_10"
    with open(tmp, "wb") as fh:
        fh.write(nt)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, TEX)
    if sha_file(TEX) != sha_bytes(nt):
        raise PatchError("dopo la scrittura lo sha non coincide")
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    rc = {"schema": "paper2_patch_tex_10_v1", "utc": datetime.now(timezone.utc).isoformat(),
          "tex_sha_before": sha_bytes(rt), "tex_sha_after": sha_bytes(nt), "bib_sha_read": SHA_BIB,
          "numbers_checked": n_num, "keys": keys, "conditions": n_cond,
          "script_sha": sha_file(os.path.abspath(__file__))}
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    report(rt, nt, n_num, keys, n_cond)
    print("ricevuta: %s" % RECEIPT)
    print("ESITO: APPLICATA")


def cmd_verify():
    if not os.path.exists(RECEIPT):
        raise PatchError("ricevuta assente: la patch non e' stata applicata")
    rc = json.load(open(RECEIPT, encoding="utf-8"))
    t = open(TEX, "rb").read()
    same = sha_bytes(t) == rc["tex_sha_after"]
    present = flat(NEW_10) in flat(t.decode("utf-8"))
    print("tex %s; testo nuovo presente: %s" % ("= dopo la patch" if same else "MODIFICATO dopo", "si'" if present else "NO"))
    if not present:
        raise PatchError("testo della patch assente")
    print("ESITO: %s" % ("PASS" if same else "PASS, tex modificato dopo la patch"))
    return 0


# ----------------------------------------------------------------------------- selftest

def _fx_tex(eol="\n"):
    body = ("% >>> TESTO DECISO: D8\nA box pilot, ratio ${\\sim}22$.\n% <<< TESTO DECISO\n"
            "\\label{prop:monotone}\\label{prop:dilation}\\label{lem:gauge}\\label{fig:response}\\label{sec:budget}"
            "\\label{sec:practices}\n"
            "numbers: 0.0141 98.3 11.2 91.1 8.7 3.2 89.15 1.25 56.49 0.83 1.24 1.57 0.398 0.416 3.1 3.6 1.4 22.9 18.2 1 2\n"
            "\\todo{altra nota}\n\\section{Conclusions}\n\\label{sec:conclusions}\n" + OLD_10 + "\n\\section*{Ack}\n")
    return body.replace("\n", eol)


BIB_FX = "@article{M26,\n}\n@article{Paper1,\n}\n"


def _t_lf():
    t = _fx_tex()
    nt = apply_edits(t, TEX_EDITS)
    n_num, keys, n_cond = check_all(t, nt, BIB_FX)
    try:
        apply_edits(nt, TEX_EDITS)
    except PatchError:
        return keys == ["M26"] and n_cond == 7 and nt.count("\\todo{") == 1
    return False


def _t_crlf():
    nt = apply_edits(_fx_tex("\r\n"), TEX_EDITS)
    return nt.count("\r\n") == nt.count("\n")


def _t_numero_nuovo():
    t = _fx_tex().replace(" 0.416 ", " 0.417 ")
    nt = apply_edits(t, TEX_EDITS)
    try:
        check_all(t, nt, BIB_FX)
    except PatchError as e:
        return "0.416" in str(e)
    return False


def _t_etichetta_mancante():
    t = _fx_tex().replace("\\label{sec:practices}", "")
    nt = apply_edits(t, TEX_EDITS)
    try:
        check_all(t, nt, BIB_FX)
    except PatchError as e:
        return "sec:practices" in str(e)
    return False


def _t_chiave_mancante():
    t = _fx_tex()
    nt = apply_edits(t, TEX_EDITS)
    try:
        check_all(t, nt, "@article{Paper1,\n}\n")
    except PatchError as e:
        return "M26" in str(e)
    return False


def _t_ascii():
    for _, _, new in TEX_EDITS:
        try:
            new.encode("ascii")
        except UnicodeEncodeError:
            return False
        body = "\n".join(l for l in new.splitlines() if not l.lstrip().startswith("%"))
        if body.count("{") != body.count("}") or body.count("$") % 2:
            return False
    return True


TESTS = [
    ("testo su LF; seconda applicazione -> errore; sette condizioni", _t_lf),
    ("CRLF conservato", _t_crlf),
    ("un numero del par. 10 assente altrove -> errore", _t_numero_nuovo),
    ("un rimando a un'etichetta assente -> errore", _t_etichetta_mancante),
    ("una chiave citata assente dalla bibliografia -> errore", _t_chiave_mancante),
    ("testo nuovo ASCII, graffe e dollari bilanciati", _t_ascii),
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

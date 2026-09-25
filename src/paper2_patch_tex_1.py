#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_tex_1.py -- Paper 2, manoscritto: il §1 (Introduction), la domanda e i contributi.

1.1: la domanda della funzione di risposta; le tre leve; la limitazione (ix) e il limite su w0 di Marconi
(2026a), con la (ii), che e' w_a, dichiarata aperta; che cosa aggiunge il Paper 2 al section 6 di Marconi
(2026b) (Z-P1 par. 6, voce P1-5). 1.2: sei contributi numerati, come Marconi (2026a) section 1.1.

Nessun numero nuovo: ogni numero del testo deve comparire altrove nel manoscritto (il patcher lo verifica),
ogni rimando e' a un'etichetta esistente, ogni chiave citata sta in bibliografia. I blocchi TESTO DECISO
restano identici byte per byte; nessuna sigla di citazione.

File: papers/paper2/MNRAS/paper2_mnras.tex, c7cb915a... (dopo la patch del §10). La bibliografia si legge
soltanto (2df3a499...).

Sottocomandi: selftest | dry-run | apply | verify. Dalla radice del repository.
Ricevuta: logs/patch_tex_1.json.
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
RECEIPT = J("logs", "patch_tex_1.json")
SHA_TEX = "c7cb915a819fdae86bbb55ffa5519cfad24a8858761bf04789e8ab1a059880f3"
SHA_BIB = "2df3a499447aff9e98a3c25060f4ddeeaf531e26aa98ab1cb88d90929ba7b58d"

OLD_11 = r"""\todo{la domanda della funzione di risposta; la limitazione (ix) e il limite su
$w_0$ (non ``(ix) e (ii)'': la (ii) \`e $w_a$). Citazioni autore-anno,
senza abbreviazioni: \citet{M26} e \citet{Paper1} (decisione del 25 set). Dire che cosa aggiunge il Paper~2 al section~6 di
\citet{Paper1}, ``What $\NH$ responds to'' (Z-P1\S6).}
"""

NEW_11 = r"""% Fonti: Marconi 2026a, sections 1, 4, 5.3, 5.5 e 7 (limitazioni (ii) e (ix)); Marconi 2026b, abstract e
% section 6 (Z-P1 par. 6: la voce P1-5 tocca il section 6 e non ne cambia il testo). Numeri: par. 2.2 e 6.2.
Persistent homology describes a density field by the connected components,
loops and cavities of its superlevel sets, tracked across all thresholds at
once, and forecasts and inference on simulated periodic boxes make it a
candidate cosmological statistic beyond the two-point function
\citep{Yip2024,Calles2025}. On an observed survey the comparison with
simulations carries the systematics of the observation. \citet{M26} built a
construction under which it becomes meaningful: cut-sky mocks matched to the
survey in footprint, selection, redshift-space distortions, density and
smoothing scale, analysed with a filtration that excludes the exterior of the
survey on both sides. Applied to the Bright Galaxy Survey of DESI, it found that
the observed field contains fewer loops than every mock, in both galactic caps;
over the 2000 realizations of each cap the deficit is 20.26 and 19.19 per cent
of the mean mock count (Section~\ref{sec:ensembles}). \citet{Paper1} asked what
statistical information the deficit encodes, and in its section~6 what the
count responds to across the cosmologies of the suite.

This paper asks the second question in full. A statistic compared with
simulations is only as well understood as its response function: what it
responds to, by how much, and what it cannot respond to at all. Three levers act
on the count between the survey and the mocks. The first is the geometry that a
fiducial cosmology imposes on the survey when redshifts are converted into
distances, which \citet{M26} left untested as limitation (ix) of its
section~7. The second is the weighting of the mocks, which carry no
observational weights while the data do; \citet{M26} bounded its effect on 60
paired realizations in one cap. The third is the cosmology of the suite, and in
particular $w_0$, whose partial correlation with the count \citet{M26} found
compatible with zero on 200 mocks, with a slope known only to lie in
$[-1050, +929]$ generators per unit $w_0$. Limitation (ii) of the same list, an
equation of state with $w_a \neq 0$, is out of reach of a suite that varies
$w_0$ alone, and remains open here.

The answer separates what is invariant by theorem from what is bounded or
measured. \citet[section~6]{Paper1} ordered the parameters of the suite by
their correlation with the count and read the count as a probe of the shape of
the power spectrum. This paper adds the two levers that the suite does not
vary, the geometry and the weighting; conditions the response to each parameter
on the other six, in both caps; and states for each response whether it is zero
by theorem, bounded by measurement or measured.
"""

OLD_12 = r"""\todo{contributi numerati, come M26 section 1.1.}
"""

NEW_12 = r"""% Fonti: nessun numero nuovo (verificato dal patcher); forma come Marconi 2026a section 1.1.
The paper makes six contributions.

(i) Two invariances of the count, one standard and one new, and the
parametrization of the fiducial cosmology that they impose
(Section~\ref{sec:theory}). The count is exactly invariant under any increasing
map of the filtered field and under an isotropic dilation of the survey together
with its grid, so that only the anisotropic part of a change of fiducial
cosmology, fixed by a Chebyshev gauge, can act on it.

(ii) The Alcock--Paczy\'{n}ski response of the deficit, measured under a
protocol declared in advance (Sections~\ref{sec:protocol}
and~\ref{sec:geometry}): a sub-dominant sensitivity in both caps,
$\Dmax = -98.3 \pm 11.2$ and $-91.1 \pm 8.7$ generators at $k = 1$, which closes
limitation (ix).

(iii) The weighting of the mocks, measured on the full ensemble of both caps
(Section~\ref{sec:weighting}): 1.24 and 1.57 per cent of the deficit, towards
the data. The hypothesis that it explains the one-point disagreement between
mocks and data and the maximum of the deficit under erosion fails every rule
declared for it before the measurement.

(iv) The response to the parameters of the suite on 2000 realizations per cap
(Section~\ref{sec:cosmology}): the spectral index leads in partial correlation,
the slope in $w_0$ is measured, and about half of the variance available to a
predictor measured on the same realization is explained neither by the
parameters nor by the dark-matter power spectrum.

(v) The response function of the count and an updated systematic budget
(Section~\ref{sec:response}): within the ranges sampled, no lever moves the mean
mock count by more than 1.4 per-realization dispersions, against a deficit of
22.9 in NGC and 18.2 in SGC.

(vi) Five practices that extend those of \citet{M26} for topological analyses
of observed fields (Section~\ref{sec:practices}).

Predictions that failed, and those withdrawn, are reported with the reasons for
which their thresholds were mis-set (Appendix~\ref{app:predictions}).
"""

TEX_EDITS = [("nota del par. 1.1", OLD_11, NEW_11), ("nota del par. 1.2", OLD_12, NEW_12)]
NEW_ALL = NEW_11 + NEW_12
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
    new_body = NEW_ALL
    rest = new_tex
    for n in (NEW_11, NEW_12):
        rest = rest.replace(n.replace("\n", eol_of(new_tex)), " ")
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
    cond = [("numeri del par. 1 presenti altrove nel manoscritto", not missing, str(missing)),
            ("rimandi a etichette esistenti", refs <= labels, str(sorted(refs - labels))),
            ("etichette nuove presenti una volta", all(new_tex.count("\\label{%s}" % l) == 1 for l in NEW_LABELS), "-"),
            ("chiavi citate in bibliografia", keys <= bibkeys, str(sorted(keys - bibkeys))),
            ("nessuna sigla di citazione", not re.search(r"\\cite[tp]alias|\\defcitealias", new_tex), "-"),
            ("testi decisi invariati", decided_blocks(old_tex) == decided_blocks(new_tex), "-"),
            ("due note di stesura in meno", old_tex.count("\\todo{") - new_tex.count("\\todo{") == 2, "-")]
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
    print("controlli: %d numeri del par. 1 tutti gia' nel manoscritto; chiavi citate %s; %d condizioni PASS"
          % (n_num, ", ".join(keys), n_cond))


def cmd_dry():
    report(*prepare())
    print("ESITO: DRY-RUN PASS (nulla scritto)")


def cmd_apply():
    rt, nt, n_num, keys, n_cond = prepare()
    tmp = TEX + ".tmp_patch_1"
    with open(tmp, "wb") as fh:
        fh.write(nt)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, TEX)
    if sha_file(TEX) != sha_bytes(nt):
        raise PatchError("dopo la scrittura lo sha non coincide")
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    rc = {"schema": "paper2_patch_tex_1_v1", "utc": datetime.now(timezone.utc).isoformat(),
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
    present = all(flat(n) in flat(t.decode("utf-8")) for n in (NEW_11, NEW_12))
    print("tex %s; testo nuovo presente: %s" % ("= dopo la patch" if same else "MODIFICATO dopo", "si'" if present else "NO"))
    if not present:
        raise PatchError("testo della patch assente")
    print("ESITO: %s" % ("PASS" if same else "PASS, tex modificato dopo la patch"))
    return 0


# ----------------------------------------------------------------------------- selftest

def _fx_tex(eol="\n"):
    body = ("% >>> TESTO DECISO: D8\nA box pilot.\n% <<< TESTO DECISO\n"
            "\\label{sec:ensembles}\\label{sec:theory}\\label{sec:protocol}\\label{sec:geometry}\\label{sec:weighting}"
            "\\label{sec:cosmology}\\label{sec:response}\\label{sec:practices}\\label{app:predictions}\n"
            "numbers: 2000 20.26 19.19 60 200 -1050 +929 0 6 7 98.3 11.2 91.1 8.7 1 1.24 1.57 1.4 22.9 18.2\n"
            "\\todo{altra nota}\n\\subsection{The question}\n" + OLD_11 + "\n\\subsection{This work}\n" + OLD_12 + "\n")
    return body.replace("\n", eol)


BIB_FX = "@article{M26,\n}\n@article{Paper1,\n}\n@article{Yip2024,\n}\n@article{Calles2025,\n}\n"


def _t_lf():
    t = _fx_tex()
    nt = apply_edits(t, TEX_EDITS)
    n_num, keys, n_cond = check_all(t, nt, BIB_FX)
    try:
        apply_edits(nt, TEX_EDITS)
    except PatchError:
        return keys == ["Calles2025", "M26", "Paper1", "Yip2024"] and n_cond == 7 and nt.count("\\todo{") == 1
    return False


def _t_crlf():
    nt = apply_edits(_fx_tex("\r\n"), TEX_EDITS)
    return nt.count("\r\n") == nt.count("\n")


def _t_numero_nuovo():
    t = _fx_tex().replace(" 19.19 ", " 19.2 ")
    nt = apply_edits(t, TEX_EDITS)
    try:
        check_all(t, nt, BIB_FX)
    except PatchError as e:
        return "19.19" in str(e)
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
        check_all(t, nt, BIB_FX.replace("@article{Yip2024,\n}\n", ""))
    except PatchError as e:
        return "Yip2024" in str(e)
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
    ("un numero del par. 1 assente altrove -> errore", _t_numero_nuovo),
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

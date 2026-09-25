#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_tex_8.py -- Paper 2, manoscritto: il §8 (Discussion) e una voce nuova di bibliografia.

Decisioni del 25 set: tre sottosezioni (che cosa dice la funzione di risposta; le practice, le tre di
Marconi 2026a section 6.2 piu' cinque nuove; il rapporto con il lavoro precedente), practice 1-5 di
paper2_5_4_practice.md nel testo (6 e 7 in REPRODUCIBILITY.md), e l'AP topologico nella letteratura.

Due file, entrambi ancorati per sha:
  - papers/paper2/MNRAS/paper2_mnras.tex, 29f81c85... (dopo la patch del §2): la nota di stesura del §8
    diventa tre sottosezioni;
  - papers/paper2/MNRAS/paper2.bib, 8d1d4016...: aggiunta Park & Kim (2010), verificata alla fonte il 25 set
    (titolo e autori su arXiv:0905.2268, rivista, volume, pagina e DOI sulla pagina dell'editore, anno
    nell'elenco delle pubblicazioni del KIAS), e aggiornato il commento di testa.

Il §8 non porta numeri nuovi: ogni numero del testo nuovo deve comparire altrove nel manoscritto (il
patcher lo verifica), e ogni rimando a una sezione e' a un'etichetta esistente. Ogni chiave citata deve
stare nella bibliografia dopo la patch. I blocchi TESTO DECISO restano identici byte per byte; nessuna
sigla di citazione.

Sottocomandi: selftest | dry-run | apply | verify. Dalla radice del repository.
Ricevuta: logs/patch_tex_8.json.
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
RECEIPT = J("logs", "patch_tex_8.json")
SHA_TEX = "29f81c85af779d90a5db161e0c8aeae5eb261315389a0e5d74375358a5970ac4"
SHA_BIB = "8d1d4016e85beaa8e17098af7915c8e4bff8236504b80f93117e1c4fa05d9758"

OLD_8 = r"""\todo{che cosa significa la funzione di risposta; rapporto con
\citet{M26}, \citet{Paper1} e la letteratura.}
"""

NEW_8 = r"""
\subsection{What the response function says}
\label{sec:meaning}
% Fonti: nessun numero nuovo. Par. 7.2 (fig_F7.jsonl: limiti 0.42 / 0.40 per w0, 0.40 / 0.26 per M_nu;
% 0.70 / 0.69 da B1 a B5; deficit 22.9 / 18.2 dispersioni; massimo 1.4), par. 4.4 (0.9-3.2 per cento,
% 3.7 agli estremi degli intervalli), par. 5.1 (1.24 / 1.57 per cento), par. 2.2 (nessuna realizzazione
% raggiunge i dati), par. 4.5 e 6.3.
The count responds to the three levers of the title in three ways
(Fig.~\ref{fig:response}). Two responses are zero by theorem. An isotropic
dilation of the survey reaches $\NH$ only through the smoothing scale in grid
units (Proposition~\ref{prop:dilation}), and in the constant-cube gauge of this
paper it does not reach it at all; an increasing map of the filtered field
leaves the diagram unchanged (Proposition~\ref{prop:monotone}). Two responses
are bounded by measurement: across the whole prior of the suite, $w_0$ moves
the mean mock count by less than 0.42 dispersions and $M_\nu$ by less than
0.40, in either cap. The others are measured, led by the spectral index, and
the anisotropic distortion is among them: from B1 to B5 the mock count falls by
0.70 dispersions in NGC and 0.69 in SGC.

Set against the deficit, these responses are small. On the same scale the
deficit is 22.9 dispersions in NGC and 18.2 in SGC, and nothing that the three
levers do within the ranges sampled here moves the mean mock count by more than
1.4. The budget of Section~\ref{sec:budget} reaches the same conclusion term by
term: the anisotropic distortion moves $D$ by at most 3.2 per cent of its value,
3.7 per cent at the edge of the 95 per cent intervals; the weighting of the
mocks moves it by 1.24 and 1.57 per cent, towards the data; and no realization
of the suite, whatever its parameters, reaches the data
(Section~\ref{sec:ensembles}). The response function therefore says where the
deficit is not: not in the geometry that a fiducial cosmology imposes on the
survey, not in the weighting, and not in the parameters that the suite varies.
It does not say where the deficit is.

Two observations of this paper remain unexplained, and both concern the mocks.
The mock count responds to an anisotropic deformation about twice as strongly as
the data, with the selection frozen and without redshift-space distortions
(Section~\ref{sec:factortwo}). And about half of the variance of the count that
a predictor measured on the same realization could explain is a function
neither of the seven parameters nor of the dark-matter power spectrum of the
box, under the estimator used (Section~\ref{sec:r2}). Neither enters the
statements above, which bound the deficit directly.

\subsection{Practices, extended}
\label{sec:practices}
% Fonti: paper2_5_4_practice.md (12 set), practice 1-5, rimotivazione della 2 come in checklist 5.4;
% decisione del 25 set: 6 e 7 in REPRODUCIBILITY.md. Numeri dai par. 4.1, 4.2, 5.1.
\citet[section~6.2]{M26} lists three practices as mandatory for persistent
homology on observed fields: (i) report $\sigmapx$ and match it on a common
grid; (ii) carve the mocks by the geometry of the survey and exclude the
exterior from the filtration on both sides; (iii) verify that the transformation
of the field is applied, where, and identically on both sides. The measurements
of this paper add five, in the order of the size of what they control.

(iv) State whether the smoothing scale is fixed in physical or in grid units.
Under a change of fiducial cosmology the two are not equivalent: in grid units
an isotropic dilation cannot reach the count (Proposition~\ref{prop:dilation});
in physical units it reaches it through $\sigmapx$, by $+357$ and $+248$
generators for a change of $\sigmapx$ of $-4.74$ per cent
(Section~\ref{sec:isotropic}).

(v) Weight the mocks as the data are weighted. A paired comparison requires it
whatever the effect. Here the effect is 1.24 and 1.57 per cent of the deficit,
towards the data (Section~\ref{sec:v2}), and it is not the one expected: the
weighting leaves the extreme voxels of $\delta$ and the one-point disagreement
between mocks and data in place (Section~\ref{sec:onepoint}).

(vi) State the gauge of the split between the isotropic and the anisotropic part
of a deformation. A least-squares split overstates the anisotropic displacement
by up to 26.4 per cent against the minimax one (Lemma~\ref{lem:gauge};
Section~\ref{sec:anisotropic}).

(vii) Check the admissibility of the smoothing, $\sigmapx \lesssim
d_{\mathrm{med}}/9$, for every geometry and in every cap rather than once: the
limit depends on the footprint, and in SGC the fiducial $\sigmapx$ sits at it
(Section~\ref{sec:anisotropic}).

(viii) State the convention of the Alcock--Paczy\'{n}ski parameter with its
formula, as in equation~(\ref{eq:fap}): the two conventions in use are
reciprocal, and reading one for the other inverts the sign of the response.

\subsection{Relation to previous work}
\label{sec:previous}
% Fonti: par. 9 (limitazioni), par. 5.3 (Marconi 2026b, section 8.1: P1-10), par. 6.2 (D8, rapporto
% ~22); Marconi 2026a section 6.2 per le filtrazioni sulla nuvola di punti (Xu 2019, Biagetti 2021,
% Wilding 2021) e 6.3 per le previsioni su scatole periodiche (Yip 2024, Calles 2025). Park & Kim
% (2010): il genere per unita' di volume, a lisciatura fissa nelle unita' comoventi della cosmologia
% assunta, come righello standard (arXiv:0905.2268, letto il 25 set).
This paper closes one of the limitations of \citet{M26}, the dependence on the
fiducial cosmology, with a measurement, and bounds the sensitivity of the count
to $w_0$ (Section~\ref{sec:limitations}). The deficit reported there survives
both, and survives the weighting of the full ensemble in both caps. With
\citet[section~8.1]{Paper1}, it places the maximum of the deficit under erosion
in the first boundary layer rather than in the weighting of the mocks
(Section~\ref{sec:erosion}).

The invariances of Section~\ref{sec:theory} are not specific to this pipeline.
Proposition~\ref{prop:monotone} holds for any superlevel filtration
\citep{EdelsbrunnerHarer2010}. Proposition~\ref{prop:dilation} applies to any
analysis that voxelizes a survey on a grid derived from its own extent, and has
no object in a periodic box, where the grid is fixed. For filtrations built on
the point cloud \citep{Xu2019,Biagetti2021,Wilding2021}, whose values are
lengths, a dilation multiplies every filtration value by the same factor, an
increasing map, and Proposition~\ref{prop:monotone} alone makes the count
invariant, with no convention of the grid; what such a filtration would still
see of a change of fiducial cosmology is its anisotropic part.

The response to the cosmological parameters is weak compared with forecasts
made on periodic boxes \citep{Yip2024,Calles2025}. The cut-sky construction
matches the density and the redshift distribution of the data, and on the count
this compresses the cosmological dispersion by a factor that the box pilot of
Section~\ref{sec:ceiling} bounds at about 22. The two sets of numbers answer
different questions and do not contradict each other.

Topology has been used on the Alcock--Paczy\'{n}ski problem before, in the
opposite direction. \citet{ParkKim2010} proposed the genus of the smoothed
galaxy field as a standard ruler: measured per unit volume, with a smoothing
length fixed in the comoving units of an assumed cosmology, it drifts with
redshift when the assumed expansion history is wrong. That use rests on the two
quantities that carry a physical length, the smoothing scale and the
normalization by volume, which are what Proposition~\ref{prop:dilation}
isolates: a count on a grid dilated with the survey, smoothed in grid units, is
blind to the isotropic part of the error by construction. The standard ruler
measures the dilation that this paper removes, and the loop count, freed of it,
measures the anisotropic remainder.
"""

OLD_BIB_HEAD = """% Changes: DESI DR1 now published (AJ 171, 285, 2026); M26, Paper 1 and the
% Alcock & Paczynski (1979), Feldman, Kaiser & Peacock (1994) and Box & Cox (1964)
% added."""
NEW_BIB_HEAD = """% Changes: DESI DR1 now published (AJ 171, 285, 2026); M26, Paper 1 and the
% Alcock & Paczynski (1979), Feldman, Kaiser & Peacock (1994), Box & Cox (1964)
% and Park & Kim (2010) added."""

OLD_BIB_TAIL = """@article{BoxCox1964,
  author        = {Box, G. E. P. and Cox, D. R.},
  title         = {{An analysis of transformations}},
  journal       = {J. R. Stat. Soc. B},
  volume        = {26},
  pages         = {211},
  year          = {1964},
  doi           = {10.1111/j.2517-6161.1964.tb00553.x}
}
"""
NEW_BIB_TAIL = OLD_BIB_TAIL + """
% Verified on 25 Sep 2026: title and authors at arXiv:0905.2268; journal, volume, page and DOI at the
% publisher page (iopscience, 10.1088/2041-8205/715/2/L185); year in the KIAS publication list.
@article{ParkKim2010,
  author        = {Park, C. and Kim, Y.-R.},
  title         = {{Large-scale Structure of the Universe as a Cosmic Standard Ruler}},
  journal       = apjl,
  volume        = {715},
  number        = {2},
  pages         = {L185},
  year          = {2010},
  doi           = {10.1088/2041-8205/715/2/L185},
  eprint        = {0905.2268},
  archivePrefix = {arXiv},
  primaryClass  = {astro-ph.CO}
}
"""

TEX_EDITS = [("nota del par. 8", OLD_8, NEW_8)]
BIB_EDITS = [("testa della bibliografia", OLD_BIB_HEAD, NEW_BIB_HEAD), ("voce Park & Kim", OLD_BIB_TAIL, NEW_BIB_TAIL)]
NEW_LABELS = {"sec:meaning", "sec:practices", "sec:previous"}


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
    new_body = NEW_8
    rest = new_tex.replace(NEW_8.replace("\n", eol_of(new_tex)), " ")
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
    cond = [("numeri del par. 8 presenti altrove nel manoscritto", not missing, str(missing)),
            ("rimandi a etichette esistenti", refs <= labels, str(sorted(refs - labels))),
            ("etichette nuove presenti una volta", all(new_tex.count("\\label{%s}" % l) == 1 for l in NEW_LABELS), "-"),
            ("chiavi citate in bibliografia", keys <= bibkeys, str(sorted(keys - bibkeys))),
            ("nessuna sigla di citazione", not re.search(r"\\cite[tp]alias|\\defcitealias", new_tex), "-"),
            ("testi decisi invariati", decided_blocks(old_tex) == decided_blocks(new_tex), "-"),
            ("una sola voce ParkKim2010", new_bib.count("@article{ParkKim2010,") == 1, "-")]
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
    nt, nb = apply_edits(t, TEX_EDITS), apply_edits(b, BIB_EDITS)
    n_num, keys, n_cond = check_all(t, nt, nb)
    return rt, rb, nt.encode("utf-8"), nb.encode("utf-8"), n_num, keys, n_cond


def report(rt, rb, nt, nb, n_num, keys, n_cond):
    print("tex: %d -> %d byte, %s... -> %s...; note di stesura: %d -> %d" % (
        len(rt), len(nt), sha_bytes(rt)[:12], sha_bytes(nt)[:12],
        rt.decode("utf-8").count("\\todo{"), nt.decode("utf-8").count("\\todo{")))
    print("bib: %d -> %d byte, %s... -> %s...; voce nuova: ParkKim2010" % (len(rb), len(nb), sha_bytes(rb)[:12], sha_bytes(nb)[:12]))
    print("controlli: %d numeri del par. 8 tutti gia' nel manoscritto; chiavi citate %s; %d condizioni PASS"
          % (n_num, ", ".join(keys), n_cond))


def write_atomic(path, data):
    tmp = path + ".tmp_patch_8"
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    if sha_file(path) != sha_bytes(data):
        raise PatchError("dopo la scrittura lo sha di %s non coincide" % path)


def cmd_dry():
    report(*prepare())
    print("ESITO: DRY-RUN PASS (nulla scritto)")


def cmd_apply():
    rt, rb, nt, nb, n_num, keys, n_cond = prepare()
    write_atomic(BIB, nb)
    write_atomic(TEX, nt)
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    rc = {"schema": "paper2_patch_tex_8_v1", "utc": datetime.now(timezone.utc).isoformat(),
          "tex_sha_before": sha_bytes(rt), "tex_sha_after": sha_bytes(nt),
          "bib_sha_before": sha_bytes(rb), "bib_sha_after": sha_bytes(nb),
          "numbers_checked": n_num, "keys": keys, "conditions": n_cond,
          "script_sha": sha_file(os.path.abspath(__file__))}
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    report(rt, rb, nt, nb, n_num, keys, n_cond)
    print("ricevuta: %s" % RECEIPT)
    print("ESITO: APPLICATA")


def cmd_verify():
    if not os.path.exists(RECEIPT):
        raise PatchError("ricevuta assente: la patch non e' stata applicata")
    rc = json.load(open(RECEIPT, encoding="utf-8"))
    t, b = open(TEX, "rb").read(), open(BIB, "rb").read()
    same_t, same_b = sha_bytes(t) == rc["tex_sha_after"], sha_bytes(b) == rc["bib_sha_after"]
    present = flat(NEW_8) in flat(t.decode("utf-8")) and "@article{ParkKim2010," in b.decode("utf-8")
    print("tex %s, bib %s; testo e voce nuovi presenti: %s" % (
        "= dopo la patch" if same_t else "MODIFICATO dopo", "= dopo la patch" if same_b else "MODIFICATA dopo",
        "si'" if present else "NO"))
    if not present:
        raise PatchError("testo o voce della patch assenti")
    print("ESITO: %s" % ("PASS" if same_t and same_b else "PASS, file modificati dopo la patch"))
    return 0


# ----------------------------------------------------------------------------- selftest

def _fx_tex(eol="\n"):
    body = ("% >>> TESTO DECISO: D8\nA box pilot, ratio ${\\sim}22$.\n% <<< TESTO DECISO\n"
            "\\label{sec:theory}\\label{prop:monotone}\\label{prop:dilation}\\label{lem:gauge}\\label{eq:fap}\n"
            "\\label{sec:ensembles}\\label{sec:isotropic}\\label{sec:anisotropic}\\label{sec:factortwo}\\label{sec:v2}\n"
            "\\label{sec:onepoint}\\label{sec:erosion}\\label{sec:r2}\\label{sec:ceiling}\\label{sec:budget}\n"
            "\\label{fig:response}\\label{sec:limitations}\n"
            "numbers: 0.42 0.40 0.26 0.70 0.69 22.9 18.2 1.4 3.2 3.7 95 1.24 1.57 357 248 4.74 26.4 6.2 8.1 1 2 3\n"
            "\\section{Discussion}\n\\label{sec:discussion}\n" + OLD_8 + "\n\\section{Limitations}\n")
    return body.replace("\n", eol)


def _fx_bib():
    keys = ["M26", "Paper1", "EdelsbrunnerHarer2010", "Xu2019", "Biagetti2021", "Wilding2021", "Yip2024", "Calles2025"]
    return OLD_BIB_HEAD + "\n\n" + "".join("@article{%s,\n}\n" % k for k in keys) + OLD_BIB_TAIL


def _t_lf():
    t, b = _fx_tex(), _fx_bib()
    nt, nb = apply_edits(t, TEX_EDITS), apply_edits(b, BIB_EDITS)
    n_num, keys, n_cond = check_all(t, nt, nb)
    try:
        apply_edits(nt, TEX_EDITS)
    except PatchError:
        return "ParkKim2010" in keys and n_cond == 7 and "\\todo{" not in nt
    return False


def _t_crlf():
    t = _fx_tex("\r\n")
    nt = apply_edits(t, TEX_EDITS)
    return nt.count("\r\n") == nt.count("\n")


def _t_numero_nuovo():
    t, b = _fx_tex().replace(" 26.4 ", " 26.5 "), _fx_bib()
    nt, nb = apply_edits(t, TEX_EDITS), apply_edits(b, BIB_EDITS)
    try:
        check_all(t, nt, nb)
    except PatchError as e:
        return "26.4" in str(e)
    return False


def _t_chiave_mancante():
    t, b = _fx_tex(), _fx_bib().replace("@article{Wilding2021,\n}\n", "")
    nt, nb = apply_edits(t, TEX_EDITS), apply_edits(b, BIB_EDITS)
    try:
        check_all(t, nt, nb)
    except PatchError as e:
        return "Wilding2021" in str(e)
    return False


def _t_etichetta_mancante():
    t, b = _fx_tex().replace("\\label{sec:ceiling}", ""), _fx_bib()
    nt, nb = apply_edits(t, TEX_EDITS), apply_edits(b, BIB_EDITS)
    try:
        check_all(t, nt, nb)
    except PatchError as e:
        return "sec:ceiling" in str(e)
    return False


def _t_ascii():
    for _, _, new in TEX_EDITS + BIB_EDITS:
        try:
            new.encode("ascii")
        except UnicodeEncodeError:
            return False
        body = "\n".join(l for l in new.splitlines() if not l.lstrip().startswith("%"))
        if body.count("{") != body.count("}") or body.count("$") % 2:
            return False
    return True


TESTS = [
    ("testo e voce su LF; seconda applicazione -> errore; sette condizioni", _t_lf),
    ("CRLF conservato", _t_crlf),
    ("un numero del par. 8 assente altrove -> errore", _t_numero_nuovo),
    ("una chiave citata assente dalla bibliografia -> errore", _t_chiave_mancante),
    ("un rimando a un'etichetta assente -> errore", _t_etichetta_mancante),
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

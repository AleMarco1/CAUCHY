#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_tex_abs.py -- Paper 2, manoscritto: l'abstract, e le sigle alla prima occorrenza.

L'abstract: al massimo 220 parole (contate qui, un'espressione matematica = una parola), una frase per leva
(geometria, pesatura, cosmologia), nessun numero nuovo. Le correzioni di bozza di Marconi (2026a) chiedono
ogni sigla definita alla prima occorrenza e «Galactic» maiuscolo per la nostra Galassia: DESI, BGS, DR1,
NGC e SGC nel par. 1.1; FKP nel par. 2.1; HOD nel par. 6.1; «AP» e «E2» tolti dal budget, dove comparivano
senza definizione.

File: papers/paper2/MNRAS/paper2_mnras.tex, 9596edaf... (dopo la patch del §1); bibliografia letta soltanto.

Sottocomandi: selftest | dry-run | apply | verify. Dalla radice del repository.
Ricevuta: logs/patch_tex_abs.json.
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
RECEIPT = J("logs", "patch_tex_abs.json")
SHA_TEX = "9596edaf4fb578ce12e257cf4412139787f231875871db07707f2cadb6a4ad44"
SHA_BIB = "2df3a499447aff9e98a3c25060f4ddeeaf531e26aa98ab1cb88d90929ba7b58d"

OLD_AB = r"""\todo{abstract: al massimo 220 parole, una frase per leva (geometria,
pesatura, cosmologia), scritto per ultimo.}
"""

NEW_AB = r"""% Fonti: nessun numero nuovo (verificato dal patcher); al massimo 220 parole (contate dal patcher, una
% espressione matematica = una parola); una frase per leva: geometria, pesatura, cosmologia.
The persistent-homology loop count of the DESI Bright Galaxy Survey, the number
$\NH$ of finite $H_1$ pairs of a masked filtration, lies 20.26 and 19.19 per
cent below the mean of 2000 like-for-like mocks in the two Galactic caps. We
measure what it responds to, and what by theorem it cannot. The count is
invariant under any increasing map of the filtered field and, as we prove, under an isotropic dilation of the survey with
its grid, leaving only the anisotropic part of a change of fiducial cosmology
to act on it. Geometry: under a pre-registered protocol the
Alcock--Paczy\'{n}ski response of the deficit is measured: $-98.3 \pm 11.2$ and
$-91.1 \pm 8.7$ generators between the ends of the sampled line, and at most 3.2
per cent of the deficit along it. Weighting: giving the mocks the radial weight of the data closes 1.24
and 1.57 per cent of the deficit, and explains neither the one-point
disagreement nor the maximum of the deficit under erosion. Cosmology: the
spectral index leads, the slope in $w_0$ implies half-widths of 3.1 and 3.6 on
it, and no parameter moves the mean mock count by more than 1.4
per-realization dispersions, against a deficit of 22.9 and 18.2. The deficit
survives every lever; the response of the mocks to anisotropic deformation,
about twice that of the data, remains unexplained.
"""

# le sigle alla prima occorrenza nel corpo, e Galactic maiuscolo (correzioni di bozza di Marconi 2026a)
OLD_S1 = r"""survey on both sides. Applied to the Bright Galaxy Survey of DESI, it found that
the observed field contains fewer loops than every mock, in both galactic caps;
"""
NEW_S1 = r"""survey on both sides. Applied to the first data release (DR1) of the Bright
Galaxy Survey (BGS) of the Dark Energy Spectroscopic Instrument (DESI), it found
that the observed field contains fewer loops than every mock, in both the North
and the South Galactic Cap (NGC and SGC);
"""
OLD_S2 = r"""\citep{DESI2026DR1}, in both galactic caps and in the absolute-magnitude-limited
"""
NEW_S2 = r"""\citep{DESI2026DR1}, in both Galactic caps and in the absolute-magnitude-limited
"""
OLD_S3 = r"""weights $w_{\rm sys}\,w_{\rm comp}\,w_{\rm FKP}$, to a $128^3$ grid on the
"""
NEW_S3 = r"""weights $w_{\rm sys}\,w_{\rm comp}\,w_{\rm FKP}$ for imaging systematics, completeness
and the radial weighting of \citet[FKP]{FKP1994}, to a $128^3$ grid on the
"""
OLD_S4 = r"""per cent), HOD and downsampling (16.8 per cent)"""
NEW_S4 = r"""per cent), the halo occupation distribution (HOD) and downsampling (16.8 per cent)"""
OLD_S5 = r"""1 & AP distortion, $\Dmax$"""
NEW_S5 = r"""1 & Alcock--Paczy\'{n}ski distortion, $\Dmax$"""
OLD_S6 = r"""& measurement, outcome E2 &"""
NEW_S6 = r"""& measurement, second outcome &"""

ACRONYMS = ("DESI", "BGS", "DR1", "NGC", "SGC", "FKP", "HOD")
TEX_EDITS = [("nota dell'abstract", OLD_AB, NEW_AB), ("sigle nel par. 1.1", OLD_S1, NEW_S1),
             ("Galactic nel par. 2.1", OLD_S2, NEW_S2), ("FKP nel par. 2.1", OLD_S3, NEW_S3),
             ("HOD nel par. 6.1", OLD_S4, NEW_S4), ("AP nel budget", OLD_S5, NEW_S5), ("E2 nel budget", OLD_S6, NEW_S6)]
NEW_ALL = NEW_AB
MAX_WORDS = 220

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


def words(text):
    t = strip_comments(text)
    t = re.sub(r"\$[^$]*\$", "X", t)
    t = re.sub(r"\\'\{(\w)\}", r"\1", t).replace("--", "-")
    return len(t.split())


def body_from_abstract(text):
    t = text.replace("\r\n", "\n")
    i = t.index("\\begin{abstract}")
    return strip_comments(t[i:])


def first_use_ok(text, acr):
    """Nel corpo (dal par. 1, fuori dai commenti) la prima occorrenza della sigla e' la sua definizione:
    '(SIGLA', 'SIGLA)' o '[SIGLA]' entro la stessa frase (40 caratteri prima, 120 dopo)."""
    body = body_from_abstract(text)
    j = body.index("\\section{Introduction}")
    m = re.search(r"(?<![A-Za-z\\])" + acr + r"(?![A-Za-z])", body[j:])
    if not m:
        return False
    ctx = body[j + m.start() - 1: j + m.end() + 1]
    win = body[max(0, j + m.start() - 40): j + m.end() + 120]
    return ctx.startswith("(") or ctx.endswith(")") or ("(" + acr) in win or ("[" + acr + "]") in win


def check_all(old_tex, new_tex, new_bib):
    eol = eol_of(new_tex)
    rest = new_tex.replace(NEW_AB.replace("\n", eol), " ")
    nums = numbers_of(NEW_AB)
    rest_flat = flat(strip_comments(rest))
    missing = sorted(n for n in nums if not re.search(r"(?<![\w.])" + re.escape(n) + r"(?![\d])", rest_flat))
    keys = set()
    for _, _, n in TEX_EDITS:
        for m in re.finditer(r"\\cite\w*(?:\[[^\]]*\])*\{([^}]+)\}", strip_comments(n)):
            keys |= {k.strip() for k in m.group(1).split(",")}
    bibkeys = set(re.findall(r"@\w+\{([^,]+),", new_bib))
    body = body_from_abstract(new_tex)
    nw = words(NEW_AB)
    bad_acr = [a for a in ACRONYMS if not first_use_ok(new_tex, a)]
    cond = [("numeri dell'abstract presenti altrove nel manoscritto", not missing, str(missing)),
            ("abstract entro %d parole" % MAX_WORDS, nw <= MAX_WORDS, "%d parole" % nw),
            ("sigle definite alla prima occorrenza nel corpo", not bad_acr, str(bad_acr)),
            ("nessun 'galactic' minuscolo", not re.search(r"\bgalactic\b", body), "-"),
            ("nessun AP o E2 isolato nel testo", not re.search(r"(?<![A-Za-z{\\])(AP|E2)(?![A-Za-z}])", body), "-"),
            ("chiavi citate in bibliografia", keys <= bibkeys, str(sorted(keys - bibkeys))),
            ("nessuna sigla di citazione", not re.search(r"\\cite[tp]alias|\\defcitealias", new_tex), "-"),
            ("testi decisi invariati", decided_blocks(old_tex) == decided_blocks(new_tex), "-"),
            ("una nota di stesura in meno", old_tex.count("\\todo{") - new_tex.count("\\todo{") == 1, "-")]
    bad = [(lab, info) for lab, ok, info in cond if not ok]
    if bad:
        raise PatchError("controlli falliti: %s" % bad)
    return len(nums), sorted(keys), len(cond), nw


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
    n_num, keys, n_cond, nw = check_all(t, nt, b)
    return rt, nt.encode("utf-8"), n_num, keys, n_cond, nw


def report(rt, nt, n_num, keys, n_cond, nw):
    print("tex: %d -> %d byte, %s... -> %s...; note di stesura: %d -> %d" % (
        len(rt), len(nt), sha_bytes(rt)[:12], sha_bytes(nt)[:12],
        rt.decode("utf-8").count("\\todo{"), nt.decode("utf-8").count("\\todo{")))
    print("abstract: %d parole su %d; %d numeri tutti gia' nel manoscritto; sigle %s definite alla prima occorrenza"
          % (nw, MAX_WORDS, n_num, ", ".join(ACRONYMS)))
    print("controlli: chiavi citate %s; %d condizioni PASS" % (", ".join(keys), n_cond))


def cmd_dry():
    report(*prepare())
    print("ESITO: DRY-RUN PASS (nulla scritto)")


def cmd_apply():
    rt, nt, n_num, keys, n_cond, nw = prepare()
    tmp = TEX + ".tmp_patch_abs"
    with open(tmp, "wb") as fh:
        fh.write(nt)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, TEX)
    if sha_file(TEX) != sha_bytes(nt):
        raise PatchError("dopo la scrittura lo sha non coincide")
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    rc = {"schema": "paper2_patch_tex_abs_v1", "utc": datetime.now(timezone.utc).isoformat(),
          "tex_sha_before": sha_bytes(rt), "tex_sha_after": sha_bytes(nt), "bib_sha_read": SHA_BIB,
          "numbers_checked": n_num, "keys": keys, "conditions": n_cond, "abstract_words": nw,
          "script_sha": sha_file(os.path.abspath(__file__))}
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    report(rt, nt, n_num, keys, n_cond, nw)
    print("ricevuta: %s" % RECEIPT)
    print("ESITO: APPLICATA")


def cmd_verify():
    if not os.path.exists(RECEIPT):
        raise PatchError("ricevuta assente: la patch non e' stata applicata")
    rc = json.load(open(RECEIPT, encoding="utf-8"))
    t = open(TEX, "rb").read()
    same = sha_bytes(t) == rc["tex_sha_after"]
    present = all(flat(n) in flat(t.decode("utf-8")) for _, _, n in TEX_EDITS)
    print("tex %s; testo nuovo presente: %s" % ("= dopo la patch" if same else "MODIFICATO dopo", "si'" if present else "NO"))
    if not present:
        raise PatchError("testo della patch assente")
    print("ESITO: %s" % ("PASS" if same else "PASS, tex modificato dopo la patch"))
    return 0


# ----------------------------------------------------------------------------- selftest

def _fx_tex(eol="\n"):
    body = ("\\begin{abstract}\n" + OLD_AB + "\\end{abstract}\n\\section{Introduction}\n"
            "% >>> TESTO DECISO: D8\nA box pilot.\n% <<< TESTO DECISO\n"
            "construction under which it becomes meaningful: excludes the exterior of the\n" + OLD_S1 +
            "numbers: 20.26 19.19 2000 98.3 11.2 91.1 8.7 3.2 1.24 1.57 0 3.1 3.6 1.4 22.9 18.2 1\n" + OLD_S2 + OLD_S3 +
            "in NGC and in SGC; w_FKP again.\n" + OLD_S4 + " and HOD again.\n" + OLD_S5 + " & -98.3 " + OLD_S6 + " x \\\\\n"
            "\\todo{altra nota}\n")
    return body.replace("\n", eol)


BIB_FX = "@article{FKP1994,\n}\n@article{DESI2026DR1,\n}\n"


def _t_lf():
    t = _fx_tex()
    nt = apply_edits(t, TEX_EDITS)
    n_num, keys, n_cond, nw = check_all(t, nt, BIB_FX)
    try:
        apply_edits(nt, TEX_EDITS)
    except PatchError:
        return keys == ["DESI2026DR1", "FKP1994"] and n_cond == 9 and nw <= 220 and nt.count("\\todo{") == 1
    return False


def _t_crlf():
    nt = apply_edits(_fx_tex("\r\n"), TEX_EDITS)
    return nt.count("\r\n") == nt.count("\n")


def _t_numero_nuovo():
    t = _fx_tex().replace(" 22.9 ", " 23.0 ")
    nt = apply_edits(t, TEX_EDITS)
    try:
        check_all(t, nt, BIB_FX)
    except PatchError as e:
        return "22.9" in str(e)
    return False


def _t_sigla_non_definita():
    t = _fx_tex()
    nt = apply_edits(t, TEX_EDITS).replace("numbers:", "HOD numbers:")
    try:
        check_all(t, nt, BIB_FX)
    except PatchError as e:
        return "HOD" in str(e)
    return False


def _t_parole():
    global NEW_AB
    t = _fx_tex()
    salvato = NEW_AB
    try:
        NEW_AB = salvato.replace("remains unexplained.", "remains unexplained, " + "and more " * 5 + "words.")
        TEX_EDITS[0] = ("nota dell'abstract", OLD_AB, NEW_AB)
        nt = apply_edits(t, TEX_EDITS)
        try:
            check_all(t, nt, BIB_FX)
        except PatchError as e:
            return "parole" in str(e)
        return False
    finally:
        NEW_AB = salvato
        TEX_EDITS[0] = ("nota dell'abstract", OLD_AB, NEW_AB)


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
    ("sette sostituzioni su LF; seconda applicazione -> errore; nove condizioni", _t_lf),
    ("CRLF conservato", _t_crlf),
    ("un numero dell'abstract assente altrove -> errore", _t_numero_nuovo),
    ("una sigla usata prima della sua definizione -> errore", _t_sigla_non_definita),
    ("abstract oltre 220 parole -> errore", _t_parole),
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_tex_2.py -- Paper 2, manoscritto: il §2 (Data, ensembles and protocol), la tabella dei
record del ledger citati nel testo (appendice C) e le citazioni della serie in forma autore-anno.

Versione 2 (25 set): la prima si fermava su git, perche' il commit 22124cc (quello del push del 27 agosto)
non e' nella storia locale; la v1.0 del protocollo vi sta nel commit 73c8213, stessi byte. In piu', su
decisione del 25 set, M26 e Paper 1 si citano autore-anno (Marconi 2026a e 2026b) invece che con le sigle.

Prima di tutto, le citazioni: \citetalias{M26} (section~4.1) -> \citet[section~4.1]{M26};
(\citetalias{Paper1}, section~7.2) -> (\citealt[section~7.2]{Paper1}); \citepalias -> \citep; il resto
\citet. Tolte le \defcitealias; il preambolo dichiara la modifica di forma, che tocca anche due testi
decisi (limitazioni e 3-bis). Controlli: nessuna sigla residua, stesso numero di citazioni per chiave,
testi decisi uguali alla conversione di se stessi. L'ordine a/b lo fissa gia' il campo `number` di
paper2.bib (M26 = 2026a, Paper 1 = 2026b).

Poi quattro sostituzioni atomiche in papers/paper2/MNRAS/paper2_mnras.tex, ognuna su un'ancora che deve
comparire UNA volta:
  1. §2.1, DESI BGS DR1 nelle due calotte, il campo, N_H1 = beta_1^max di M26, i conteggi congelati;
  2. §2.2, l'ensemble cut-sky di M26 su nwLH, v1 di riferimento e v2 pesato, i momenti a k = 0;
  3. §2.3, il protocollo: che cosa fissa, le tre clausole, la datazione (v1.0 nel commit 73c8213, v1.1
     identica nelle regole), che cosa non era ignoto, il ledger (decisione del 25 set: tabella dei citati);
  4. appendice C: la sottosezione del ledger con la tabella dei record citati (la nota di stesura
     dell'appendice C resta).

Prima di scrivere:
  - sha del tex = 3cf3d9a7... (quello dopo la patch del §3);
  - i numeri del testo nuovo sono riscontrati su src/paper2_v1_reference.json (digest di contenuto
    865aa2ef...), results/paper2/desi_ladder_{NGC,SGC}.json, il protocollo v1.1
    (papers/paper2/paper2_prereg_v1.md, 607708e8...) e il ledger (src/paper2_v1_amendments.jsonl, fb70459f...);
  - le righe della tabella (numero e UTC) vengono dal ledger, e l'insieme dei record citati nel testo
    (commenti esclusi, tabella esclusa) deve coincidere con quello della tabella;
  - git: il commit 73c8213 esiste, e' antenato di HEAD, ha data d'autore 27 agosto 2026 e porta la v1.0
    del protocollo (05cd32b2..., 21 430 byte); fra v1.0 e v1.1 differiscono solo le sezioni 2 e 9 (e
    l'intestazione). La data del committer si stampa e non e' un cancello;
  - i blocchi TESTO DECISO restano identici, a meno della forma delle citazioni.
Fine riga: quello del file (LF o CRLF), mai misto. Scrittura atomica (temporaneo + os.replace).
Ricevuta: logs/patch_tex_2.json.

Sottocomandi: selftest | dry-run | apply | verify. Dalla radice del repository.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

J = os.path.join
TEX = J("papers", "paper2", "MNRAS", "paper2_mnras.tex")
REF = J("src", "paper2_v1_reference.json")
LADDER = {c: J("results", "paper2", "desi_ladder_%s.json" % c) for c in ("NGC", "SGC")}
PROT = J("papers", "paper2", "paper2_prereg_v1.md")
LEDGER = J("src", "paper2_v1_amendments.jsonl")
RECEIPT = J("logs", "patch_tex_2.json")

SHA_BEFORE = "3cf3d9a7c9b1318a476708133b16039680b439b02f20fe5929421af12d5a78b4"
REF_SELF = "865aa2ef16f299d8653e770d1fb587448f1c455e8c498c2b0db10cd20743f1bc"
PROT_V11 = "607708e8c00c6fd0186f48eb179dd35e36f9586a6c0a6a66d138c159412dfb86"
PROT_V10 = "05cd32b20388fffd5372711880d4c11ef6dda32ff2ff7767e898d667e2a6c115"
LEDGER_SHA = "fb70459fca476145a791407e3bd1f5bd82f0dbc04e3f3d250309930bcf3f20a5"
COMMIT = "73c8213"
PROT_IN_GIT = "papers/paper2/paper2_prereg_v1.md"
CAPS = ("NGC", "SGC")

# ----------------------------------------------------------------------------- testo

OLD_21 = r"""\todo{DESI BGS DR1 \citep{DESI2026DR1}, NGC e SGC; campo congelato;
corrispondenza fra $\betamax$ di \citetalias{M26} e $\NH$.}
"""

NEW_21 = r"""% Fonti: M26 section 2.1 (campione, pesi, fiduciale, griglia), 3.1 (campo, filtrazione, beta_1^max) e 4 (v);
% protocollo v1.1, section 2.3 (N_data / N_rand, celle, sigma_px, voxel in maschera, occupazione) e 3
% (cancello 2.1: 28 256 / 15 122 riprodotti a scarto zero); results/paper2/desi_ladder_{NGC,SGC}.json
% (N_H1 a k = 0 e 1, voxel in maschera, sigma_px); src/paper2_v1_reference.json, geometry.
The data are the Bright Galaxy Survey of the first data release of DESI
\citep{DESI2026DR1}, in both galactic caps and in the absolute-magnitude-limited
sample used by \citet{M26}, with $M_r < -21.5$ and $0.1 \le z \le 0.4$:
217\,614 galaxies in NGC and 82\,429 in SGC, with random catalogues of
13\,248\,857 and 5\,432\,939 points. Positions are converted to comoving
coordinates with the fiducial cosmology of the Quijote simulations
($\Omega_m = 0.3175$, $h = 0.6711$) and assigned by cloud-in-cell, with the
weights $w_{\rm sys}\,w_{\rm comp}\,w_{\rm FKP}$, to a $128^3$ grid on the
embedding cube of each cap (Section~\ref{sec:dilation}), with cells of 15.60 and
14.88\,$h^{-1}$\,Mpc; the smoothing scale, $R = 5\,h^{-1}$\,Mpc, is
$\sigmapx = 0.320$ and 0.336 cells. The mask keeps the voxels whose random
density exceeds 1 per cent of its mean over the cube, 307\,805 in NGC and
172\,225 in SGC, with 0.71 and 0.48 galaxies per voxel. The field is built as in
\citet[sections~3.1 and 4]{M26}: the density contrast against the random
field, the transform $\nu = \log(1 + \delta)$, Gaussian smoothing and mean
subtraction in the mask, and a superlevel filtration of the cubical complex,
computed with \sw{gudhi} \citep{gudhi}, from which the exterior of the mask is
excluded.

The statistic is the number of finite pairs in the $H_1$ persistence diagram of
that filtration, $\NH$, called $\betamax$ by \citet[section~3.1]{M26}. At
erosion level $k$ the filtration is restricted to the voxels more than $k$ grid
units from the boundary of the mask, the field being built on the full mask;
$k = 0$ is the original statistic. The data side is deterministic, and its
counts at $k = 0$ are frozen values, which our pipeline reproduces to the unit
in both caps (protocol, section~3):
$\NH = 28\,256$ in NGC and $15\,122$ in SGC, and $23\,790$ and $12\,011$ at
$k = 1$.
"""

OLD_22 = r"""\todo{Quijote nwLH \citep{Villaescusa2020}; ensemble v1 di riferimento, v2
pesato FKP; 2000 realizzazioni per calotta.}
"""

NEW_22 = r"""% Fonti: M26 section 2.2 (nwLH, z = 0.5, occupazione di base) e 4 (costruzione cut-sky); protocollo v1.1,
% section 2.1 (congelamento di v1: cinque tier, 34 836 file, verificati file per file) e 2.2 (momenti);
% src/paper2_v1_reference.json, primary (NGC e SGC_n2000: media, dispersione, n, rango, deficit).
The mocks are the cut-sky ensemble of \citet{M26}, built on the Quijote
nwLH suite \citep{Villaescusa2020}: 2000 simulations in periodic boxes of
$1\,h^{-1}$\,Gpc, whose cosmologies fill a Latin hypercube in $\Omega_m$,
$\Omega_b$, $h$, $n_s$, $\sigma_8$, $M_\nu$ and $w_0$, with $w_0$ from $-1.3$
to $-0.7$ at $w_a = 0$. The halo catalogue of each simulation at $z = 0.5$ is
populated with the baseline halo occupation of that ensemble, tiled into the
embedding cube of each cap, placed in redshift space, carved by the angular
mask and the radial selection of the data, and downsampled to the galaxy count
of the data \citep[sections~2.2 and 4]{M26}; field and count are then built as
on the data side. Each cap has 2000 realizations, one per
simulation, carved from the same boxes and differing only in footprint.

Ensemble v1 is the original one, with the mock galaxies assigned at unit
weight. It is frozen, 34\,836 files in five tiers verified one by one against
their manifests, and it is the reference for every number in this paper that
carries no other label. Over its 2000 realizations the mean count at $k = 0$ is
35\,436.7 in NGC and 18\,713.0 in SGC, with per-realization dispersions of 313.0
and 197.8. The data lie below every realization in both caps, at rank 1/2001,
and the deficits $D$, the mean mock count minus the data count, are
7180.7 generators (20.26 per cent) and 3591.0 (19.19 per cent). Ensemble v2
assigns the same mock galaxies with the radial weight $w_{\rm FKP}$ of the data
and changes nothing else (Section~\ref{sec:v2}); it is used to measure the
weighting, and every value taken from it is labelled v2.
"""

OLD_23 = r"""\todo{protocollo pre-registrato (citato solo nella Data Availability, non in bibliografia): regole dichiarate prima delle
misure, registri congelati, ledger degli emendamenti; i test di simmetria
(protocollo, section 5.5) e di completezza (section 5.6).}
"""

NEW_23 = r"""% Fonti: protocollo v1.1 (papers/paper2/paper2_prereg_v1.md, 607708e8..., 25 319 byte), sections 0, 1, 5,
% 7, 8 e 9. v1.0 nel commit 73c8213 (05cd32b2..., 21 430 byte; data d'autore 27 ago 2026, 13:38 +0200),
% nella storia di main, come nel record 72. Il push del 27 ago alle 11:41:53Z, nel registro degli eventi
% di GitHub (letto il 25 set), porta la stessa v1.0 nel commit 22124cc, che la storia attuale non
% contiene. Fra v1.0 e v1.1 identiche le sezioni 0, 1 e 3-8 (verificato dal patcher). Il version DOI
% 10.5281/zenodo.22148444 non contiene il protocollo (record 73). Ledger: src/paper2_v1_amendments.jsonl,
% fb70459f..., 78 record, 12 alla v1.1. I record citati sono nella Table tab:ledger (appendice C);
% decisione del 25 set: tabella dei citati, non dei 66 successivi.
The measurements of Sections~\ref{sec:geometry} and \ref{sec:weighting} follow
a protocol fixed before them, cited as `the protocol' with its section numbers.
It pre-registers the measurement of the geometry, its Phase~3, and the phases
that follow it. It sets the grid of deformations of
Section~\ref{sec:geometry}, the statistic and its two thresholds, detectability
and relevance, the four outcomes of the Alcock--Paczy\'{n}ski measurement, the
symmetry and completeness tests (protocol, sections~5.5 and 5.6), the terms of
the error budget and the procedure of every run. Three of its clauses govern
how results are reported: no threshold is renegotiated once a run has started;
a null or dissolving result is a reportable outcome; and a falsified prediction
stays falsified, recorded with the reason its threshold was mis-set.

Version 1.0 of the protocol is in the history of the public repository of the
project, in a commit of 27 August 2026 (73c8213), before the first run it
governs. Version 1.1,
of the next day, differs only in its header, in the frozen inputs of its
section~2 and in the amendment record of its section~9; every other section,
the rules included, is identical line by line. The version DOI named in its
header identifies the archive of the pipeline at that date, which does not
contain the protocol; the protocol is deposited with the archive of this paper
(Data Availability). Not everything reported here was unknown when the protocol
was fixed, and the protocol says what was not (protocol, section~1): the gates
of Section~\ref{sec:isotropic} had been run, two of them falsifying their
predictions, and the response to the parameters of the nwLH suite had been
measured on ensemble v1 with linear estimators, its predictions fixed in the
analysis scripts but not deposited. The kernel regressions of
Section~\ref{sec:r2} came later, and the rules of Section~\ref{sec:weighting}
were written into the ledger before the v2 ensemble was read.

Every later change is a record of an append-only ledger, with its UTC time and
the digest of the frozen reference that it amends; `record 15' in the text is
its fifteenth entry. The ledger held twelve records when version 1.1 was written
and holds 78 at the time of writing; Table~\ref{tab:ledger} lists those cited in
the text, and the complete ledger is in the archive. The numerical records are
append-only as well, and every script reproduces at least one frozen value
before it reports a new one (protocol, section~7).
"""

OLD_APPC = r"""\label{app:technical}
\todo{griglia, esclusioni, tiling (F8). I valori di $\FAP$ eseguiti contro quelli
del protocollo (al pi\`u $2.2\times10^{-5}$). La colonna in voxel degli angoli nel
protocollo, section~4, usa la cella del gauge a cubo variabile: nel gauge a cubo
costante gli stessi residui sono 0.569, 0.105, 0.135 e 0.360 voxel.}
"""

# righe della tabella: (record, contenuto). Numero e UTC sono riscontrati sul ledger dal patcher.
LEDGER_ROWS = [
    (6, r"The practical limit on the smoothing, $\sigmapx \lesssim d_{\rm med}/9$: definition of $d_{\rm med}$ corrected, 3.000 voxels in NGC."),
    (7, r"The same limit in SGC, $d_{\rm med} = 2\sqrt{2}$: $\sigmapx$ sits at it, a caveat and not a rule of exclusion."),
    (15, r"Sixth point of line B, B6, added after the first results; $\Dmax$ stays defined on B1--B5."),
    (16, r"Treatment with fixed observables and the redshift-space mechanism declared with their predictions, before any run of either."),
    (18, r"The constant-cube gauge fixes the side of the cube, not its origin: two statements rectified and a prediction restated, before any run."),
    (19, r"Two overclaims withdrawn: the extrapolated $\FAP$ that would remove the deficit, and a falsification that the test had no power to establish."),
    (37, r"The redshift-space mechanism falsified by the run it predicted, and withdrawn."),
    (38, r"Treatment with fixed observables executed; its first prediction, that the ratio of the mock to the data response falls towards one, falsified."),
    (44, r"Replicas of the simulation box randomized in orientation at every point: the tiling term is zero by measurement."),
    (54, r"Four decisions on measured v1 values before the v2 run, among them the withdrawal of the width of $\nu$ as a falsification."),
    (55, r"Two phases of the grid against the box lattice: the fraction of reassigned voxels does not drive the response."),
]


def utc_short(u):
    """'2026-08-31T07:57:47+00:00' o '...Z' -> '2026-08-31 07:57'."""
    m = re.match(r"(\d{4}-\d\d-\d\d)T(\d\d:\d\d)", u)
    if not m:
        raise PatchError("utc non leggibile: %r" % u)
    return "%s %s" % (m.group(1), m.group(2))


def build_appc(utc_by_rec, n_ledger):
    rows = "\n".join("%d & %s & %s \\\\" % (r, utc_short(utc_by_rec[r]), txt) for r, txt in LEDGER_ROWS)
    return OLD_APPC + APPC_TEMPLATE.replace("@@N@@", "%d" % n_ledger).replace("@@ROWS@@", rows)


APPC_TEMPLATE = r"""
\subsection{The protocol ledger}
\label{app:ledger}
% Fonti: src/paper2_v1_amendments.jsonl (fb70459f...), campo utc dei record citati; il contenuto riassume
% il campo reason. La tabella elenca esattamente i record citati nel testo, commenti esclusi: il patcher
% del par. 2 lo verifica, e ogni patch che cita un record nuovo lo aggiunge qui.
Table~\ref{tab:ledger} lists the records of the ledger cited in the text
(Section~\ref{sec:protocol}), with their UTC times.

\begin{table*}
\caption{Records of the protocol ledger cited in the text. Records 6 and 7 are
earlier than the protocol; the complete ledger, @@N@@ records, is in the archive
(Data Availability).}
\label{tab:ledger}
\centering
\begin{tabular}{@{}rl>{\raggedright\arraybackslash}p{13.2cm}@{}}
\hline
Record & UTC & Content \\
\hline
@@ROWS@@
\hline
\end{tabular}
\end{table*}
"""


class PatchError(Exception):
    pass


# ----------------------------------------------------------------------------- citazioni

KEYS = ("M26", "Paper1")

# sostituzioni testuali, ognuna UNA volta, prima delle regole
SPECIALS = [
    ("preambolo, intestazione",
     "% and checked word by word and number by number against it; declared\n"
     "% edits (cross-references only) are listed next to each block.\n",
     "% and checked word by word and number by number against it; declared\n"
     "% edits (cross-references only) are listed next to each block. One edit of\n"
     "% form applies to all of them: M26 and Paper 1 are cited author-year, as\n"
     "% Marconi (2026a) and (2026b), in place of the shorthands (25 Sep 2026).\n"),
    ("preambolo, sigle",
     "% --- series shorthands ------------------------------------------------------\n"
     "\\defcitealias{M26}{M26}\n"
     "\\defcitealias{Paper1}{Paper~1}\n",
     "% --- the CAUCHY series is cited author-year: M26 is Marconi (2026a), Paper 1\n"
     "% is Marconi (2026b); the order is fixed by the `number' field in paper2.bib.\n"),
    ("nota del par. 1.1",
     "Definire le abbreviazioni:\n"
     "\\citet{M26}, hereafter \\citetalias{M26}; \\citet{Paper1}, hereafter\n"
     "\\citetalias{Paper1}. Dire",
     "Citazioni autore-anno,\n"
     "senza abbreviazioni: \\citet{M26} e \\citet{Paper1} (decisione del 25 set). Dire"),
    ("Proposition 1",
     "\\begin{proposition}[\\citetalias{Paper1}, section 2.3]",
     "\\begin{proposition}[{\\citealt[section~2.3]{Paper1}}]"),
]

_POST = r"((?:sections?|tables?)~[^()]*?)"
_K = r"\{(M26|Paper1)\}"


def _ws(x):
    return re.sub(r"\s+", " ", x)


def convert_rules(text):
    """Le quattro regole, nell'ordine: sigla + virgola + sezione -> \citealt; sigla + (sezione) -> \citet[];
    \citepalias -> \citep; sigla sola -> \citet."""
    t = re.sub(r"\\citetalias" + _K + r",\s+" + _POST + r"\)",
               lambda m: "\\citealt[%s]{%s})" % (_ws(m.group(2)), m.group(1)), text)
    t = re.sub(r"\\citetalias" + _K + r"\s+\(" + _POST + r"\)",
               lambda m: "\\citet[%s]{%s}" % (_ws(m.group(2)), m.group(1)), t)
    t = re.sub(r"\\citepalias\[([^\]]*)\]" + _K, lambda m: "\\citep[%s]{%s}" % (m.group(1), m.group(2)), t)
    return re.sub(r"\\citetalias" + _K, lambda m: "\\citet{%s}" % m.group(1), t)


def cite_count(text, key):
    body = "\n".join(l for l in text.replace("\r\n", "\n").split("\n") if not l.lstrip().startswith("%"))
    return len(re.findall(r"\\cite\w*(?:\[[^\]]*\])?\{" + key + r"\}", body))


def aliases_left(text):
    return len(re.findall(r"\\cite[tp]alias|\\defcitealias", text))


def convert_citations(text):
    """(testo convertito, conteggi per chiave prima e dopo)."""
    eol = eol_of(text)
    t = text
    for nome, old, new in SPECIALS:
        o, n = old.replace("\n", eol), new.replace("\n", eol)
        c = t.count(o)
        if c != 1:
            raise PatchError("citazioni, '%s': %d occorrenze invece di 1" % (nome, c))
        t = t.replace(o, n)
    before = {k: cite_count(t, k) for k in KEYS}
    t = convert_rules(t)
    after = {k: cite_count(t, k) for k in KEYS}
    if aliases_left(t):
        raise PatchError("citazioni: %d sigle residue dopo la conversione" % aliases_left(t))
    if before != after:
        raise PatchError("citazioni: conteggi per chiave cambiati %s -> %s" % (before, after))
    return t, after


def edits(utc_by_rec, n_ledger):
    return [("§2.1", OLD_21, NEW_21), ("§2.2", OLD_22, NEW_22), ("§2.3", OLD_23, NEW_23),
            ("appendice C, ledger", OLD_APPC, build_appc(utc_by_rec, n_ledger))]


def eol_of(text):
    crlf = text.count("\r\n")
    lf = text.count("\n")
    if crlf and crlf != lf:
        raise PatchError("fine riga misti nel tex: %d CRLF su %d LF" % (crlf, lf))
    return "\r\n" if crlf else "\n"


def decided_blocks(text):
    return re.findall(r"% >>> TESTO DECISO.*?% <<< TESTO DECISO", text, flags=re.S)


def check_decided(before, after):
    """I blocchi decisi dopo la patch sono quelli di prima, convertiti nella forma delle citazioni."""
    b, a = [convert_rules(x) for x in decided_blocks(before)], decided_blocks(after)
    if b != a:
        raise PatchError("un blocco TESTO DECISO e' cambiato (%d prima, %d dopo)" % (len(b), len(a)))
    return len(b)


def patch_text(text, utc_by_rec, n_ledger):
    eol = eol_of(text)
    out, _ = convert_citations(text)
    for nome, old, new in edits(utc_by_rec, n_ledger):
        o, n = convert_rules(old).replace("\n", eol), new.replace("\n", eol)
        c = out.count(o)
        if c != 1:
            raise PatchError("ancora '%s': %d occorrenze invece di 1" % (nome, c))
        if "\\label{tab:ledger}" in out and nome.startswith("appendice"):
            raise PatchError("'%s': la tabella del ledger e' gia' presente" % nome)
        out = out.replace(o, n)
    check_decided(text, out)
    if aliases_left(out):
        raise PatchError("sigle di citazione nel testo nuovo")
    return out


def flat(s):
    return re.sub(r"\s+", " ", s)


def body_of(text):
    """Testo senza commenti e senza la tabella del ledger."""
    lines = [l for l in text.replace("\r\n", "\n").split("\n") if not l.lstrip().startswith("%")]
    t = "\n".join(re.sub(r"(?<!\\)%.*$", "", l) for l in lines)
    return re.sub(r"\\begin\{table\*?\}(?:(?!\\end\{table\*?\}).)*?\\label\{tab:ledger\}.*?\\end\{table\*?\}", " ", t, flags=re.S)


def cited_records(text):
    t = flat(body_of(text))
    out = set()
    for m in re.finditer(r"[Rr]ecords?~?\s+(\d+(?:\s*(?:,|and|--)\s*\d+)*)", t):
        out |= {int(x) for x in re.findall(r"\d+", m.group(1))}
    return out


def table_records(text):
    m = re.search(r"\\label\{tab:ledger\}.*?\\end\{tabular\}", text, flags=re.S)
    if not m:
        raise PatchError("tabella del ledger assente")
    return [int(x) for x in re.findall(r"(?m)^(\d+) & \d{4}-\d\d-\d\d \d\d:\d\d &", m.group(0).replace("\r\n", "\n"))]


# ----------------------------------------------------------------------------- numeri

def th(n):
    """28256 -> '28\\,256'; 13248857 -> '13\\,248\\,857'."""
    s = "%d" % n
    parts = []
    while len(s) > 3:
        parts.insert(0, s[-3:])
        s = s[:-3]
    parts.insert(0, s)
    return "\\,".join(parts)


def th1(x):
    ip, fp = ("%.1f" % x).split(".")
    return th(int(ip)) + "." + fp


def prot_nrand_sgc(prot_text):
    m = re.search(r"`N_data` / `N_rand` \| ([\d ]+) / ([\d ]+) \| ([\d ]+) / ([\d ]+) \|", prot_text)
    if not m:
        raise PatchError("riga N_data / N_rand non trovata nel protocollo")
    return [int(g.replace(" ", "")) for g in m.groups()]


def checks_from(ref, lad, prot_text, ledger, facts):
    P, G = ref["primary"], ref["geometry"]
    N, S = P["NGC"], P["SGC_n2000"]
    nd_n, nr_n, nd_s, nr_s = prot_nrand_sgc(prot_text)
    cell = {c: 5.0 / lad[c]["sigma_px"] for c in CAPS}
    occ = {c: (nd_n if c == "NGC" else nd_s) / lad[c]["n_voxel_maschera"] for c in CAPS}
    fr = [("galassie", "%s galaxies in NGC and %s in SGC" % (th(nd_n), th(nd_s))),
          ("random", "random catalogues of %s and %s points" % (th(nr_n), th(nr_s))),
          ("celle", "with cells of %.2f and %.2f\\,$h^{-1}$\\,Mpc" % (cell["NGC"], cell["SGC"])),
          ("sigma_px", "$\\sigmapx = %.3f$ and %.3f cells" % (lad["NGC"]["sigma_px"], lad["SGC"]["sigma_px"])),
          ("voxel in maschera", "%s in NGC and %s in SGC, with %.2f and %.2f galaxies per voxel"
           % (th(lad["NGC"]["n_voxel_maschera"]), th(lad["SGC"]["n_voxel_maschera"]), occ["NGC"], occ["SGC"])),
          ("N_H1 dei dati", "$\\NH = %s$ in NGC and $%s$ in SGC, and $%s$ and $%s$ at $k = 1$"
           % (th(lad["NGC"]["N_H1_k0"]), th(lad["SGC"]["N_H1_k0"]), th(lad["NGC"]["N_H1_k1"]), th(lad["SGC"]["N_H1_k1"]))),
          ("medie v1", "is %s in NGC and %s in SGC, with per-realization dispersions of %.1f and %.1f"
           % (th1(N["mock_mean"]), th1(S["mock_mean"]), N["mock_sd"], S["mock_sd"])),
          ("rango", "in both caps, at rank %s," % N["empirical_rank"]),
          ("deficit", "%.1f generators (%.2f per cent) and %.1f (%.2f per cent)"
           % (N["deficit_abs"], 100 * N["deficit_frac"], S["deficit_abs"], 100 * S["deficit_frac"])),
          ("tier di v1", "%s files in five tiers" % th(facts["v1_files"])),
          ("ledger", "holds %d at the time of writing" % len(ledger)),
          ("ledger, didascalia", "the complete ledger, %d records," % len(ledger)),
          ("commit", "in a commit of 27 August 2026 (%s)" % COMMIT)]
    cond = [("n = 2000 e rango 1/2001 nei due emisferi",
             N["n_mocks"] == S["n_mocks"] == 2000 and N["empirical_rank"] == S["empirical_rank"] == "1/2001", "-"),
            ("N_H1 k0 = primario del riferimento", N["N_H1_DESI"] == lad["NGC"]["N_H1_k0"] and S["N_H1_DESI"] == lad["SGC"]["N_H1_k0"], "-"),
            ("galassie = geometria del riferimento", G["NGC"]["n_gal"] == nd_n and G["SGC"]["n_gal"] == nd_s and G["NGC"]["n_rand"] == nr_n, "-"),
            ("voxel = geometria del riferimento", all(G[c]["mask_voxels"] == lad[c]["n_voxel_maschera"] for c in CAPS), "-"),
            ("dodici record alla v1.1", facts["twelve_in_protocol"] and all(utc_short(ledger[i]["utc"]) < "2026-08-28 18:13" for i in range(12))
             and utc_short(ledger[12]["utc"]) > "2026-08-28 18:13", "-"),
            ("commit del 27 agosto, antenato di HEAD", facts["commit_date"].startswith("2026-08-27") and facts["commit_is_ancestor"],
             "%s / %s" % (facts["commit_date"], facts["commit_is_ancestor"])),
            ("v1.0 nel commit = 05cd32b2", facts["v10_sha"] == PROT_V10, facts["v10_sha"][:12]),
            ("v1.0 contro v1.1: diverse solo le sezioni 2 e 9", facts["sections_differ"] == ["2", "9"], str(facts["sections_differ"])),
            ("primo record dopo la v1.0 posteriore al commit", utc_short(ledger[12]["utc"]) > facts["commit_date"][:10] + " 23:59", "-")]
    return fr, cond


def check_numbers(text, ref, lad, prot_text, ledger, facts):
    fr, cond = checks_from(ref, lad, prot_text, ledger, facts)
    t = flat(text)
    bad = [(lab, s) for lab, s in fr if s not in t]
    utc = {i + 1: r["utc"] for i, r in enumerate(ledger)}
    rows = table_records(text)
    for r in rows:
        if "%d & %s &" % (r, utc_short(utc[r])) not in t:
            bad.append(("riga %d della tabella" % r, utc_short(utc[r])))
    cit = cited_records(text)
    extra = [("record citati = record in tabella", cit == set(rows), "citati %s, tabella %s" % (sorted(cit), rows)),
             ("tabella in ordine, senza doppioni", rows == sorted(set(rows)), str(rows))]
    badc = [(lab, info) for lab, ok, info in cond + extra if not ok]
    if bad or badc:
        raise PatchError("riscontro fallito: frasi assenti %s; condizioni false %s" % (bad, badc))
    return len(fr) + len(rows), len(cond) + len(extra)


# ----------------------------------------------------------------------------- disco

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha_bytes(open(p, "rb").read())


def sections(md):
    parts = re.split(r"(?m)^## (\d+)\.", md.replace("\r\n", "\n"))
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def git(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True)
    return r.returncode, r.stdout


def load_inputs():
    for p in [REF, PROT, LEDGER] + list(LADDER.values()):
        if not os.path.exists(p):
            raise PatchError("file assente: %s" % p)
    ref = json.load(open(REF, encoding="utf-8"))
    d = dict(ref)
    d.pop("_self_sha256", None)
    if sha_bytes(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")) != REF_SELF:
        raise PatchError("digest di contenuto di %s diverso da %s..." % (REF, REF_SELF[:12]))
    lad = {c: json.load(open(LADDER[c], encoding="utf-8")) for c in CAPS}
    pb = open(PROT, "rb").read()
    if sha_bytes(pb) != PROT_V11:
        raise PatchError("%s non e' la v1.1 ancorata (%s..., atteso %s...)" % (PROT, sha_bytes(pb)[:12], PROT_V11[:12]))
    lb = open(LEDGER, "rb").read()
    if sha_bytes(lb) != LEDGER_SHA:
        raise PatchError("ledger %s... invece di %s..." % (sha_bytes(lb)[:12], LEDGER_SHA[:12]))
    ledger = [json.loads(l) for l in lb.decode("utf-8").splitlines() if l.strip()]
    prot = pb.decode("utf-8")
    rc, typ = git("cat-file", "-t", COMMIT)
    if rc != 0 or typ.strip() != b"commit":
        raise PatchError("git: il commit %s non esiste in questo repository" % COMMIT)
    rc_anc, _ = git("merge-base", "--is-ancestor", COMMIT, "HEAD")
    _, date = git("show", "-s", "--format=%aI", COMMIT)
    _, cdate = git("show", "-s", "--format=%cI", COMMIT)
    rc, v10 = git("show", "%s:%s" % (COMMIT, PROT_IN_GIT))
    if rc != 0:
        raise PatchError("git: %s non e' nel commit %s" % (PROT_IN_GIT, COMMIT))
    s10, s11 = sections(v10.decode("utf-8")), sections(prot)
    facts = {"commit_is_ancestor": rc_anc == 0, "commit_date": date.decode().strip(),
             "committer_date": cdate.decode().strip(),
             "v10_sha": sha_bytes(v10),
             "sections_differ": sorted(k for k in set(s10) | set(s11) if s10.get(k) != s11.get(k)),
             "twelve_in_protocol": "**Twelve records exist at the date of this version.**" in prot,
             "v1_files": int(re.search(r"Ensemble v1 is 5 tiers, ([\d ]+) files", prot).group(1).replace(" ", ""))}
    return ref, lad, prot, ledger, facts


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
        raise PatchError("sha del tex %s..., atteso %s...: il manoscritto non e' quello dopo il §3" % (sha[:12], SHA_BEFORE[:12]))
    ref, lad, prot, ledger, facts = load_inputs()
    utc = {i + 1: r["utc"] for i, r in enumerate(ledger)}
    text = raw.decode("utf-8")
    new = patch_text(text, utc, len(ledger))
    n_fr, n_cond = check_numbers(new, ref, lad, prot, ledger, facts)
    return raw, new.encode("utf-8"), facts, len(ledger), n_fr, n_cond, check_decided(text, new)


def report(raw, new_raw, facts, n_led, n_fr, n_cond, n_dec):
    print("tex: %s  %d -> %d byte" % (TEX, len(raw), len(new_raw)))
    print("sha: %s... -> %s..." % (sha_bytes(raw)[:12], sha_bytes(new_raw)[:12]))
    print("ancore: 4/4 sostituite; note di stesura: %d -> %d; testi decisi invariati (citazioni a parte): %d" % (
        raw.decode("utf-8").count("\\todo{"), new_raw.decode("utf-8").count("\\todo{"), n_dec))
    print("git: %s, autore %s, committer %s, antenato di HEAD; v1.0 %s...; sezioni diverse da v1.1: %s" % (
        COMMIT, facts["commit_date"][:16], facts.get("committer_date", "?")[:16], facts["v10_sha"][:12],
        ", ".join(facts["sections_differ"])))
    print("citazioni: M26 %d, Paper 1 %d, in forma autore-anno; sigle residue 0" % (
        cite_count(new_raw.decode("utf-8"), "M26"), cite_count(new_raw.decode("utf-8"), "Paper1")))
    print("riscontro su riferimento, scala DESI, protocollo e ledger (%d record): %d frasi e %d condizioni PASS"
          % (n_led, n_fr, n_cond))


def cmd_dry():
    report(*prepare())
    print("ESITO: DRY-RUN PASS (nulla scritto)")


def cmd_apply():
    raw, new_raw, facts, n_led, n_fr, n_cond, n_dec = prepare()
    tmp = TEX + ".tmp_patch_2"
    with open(tmp, "wb") as fh:
        fh.write(new_raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, TEX)
    if sha_file(TEX) != sha_bytes(new_raw):
        raise PatchError("dopo la scrittura lo sha non coincide")
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    rc = {"schema": "paper2_patch_tex_2_v1", "utc": datetime.now(timezone.utc).isoformat(),
          "tex": TEX, "sha_before": sha_bytes(raw), "sha_after": sha_bytes(new_raw),
          "bytes_before": len(raw), "bytes_after": len(new_raw), "git_facts": facts,
          "ledger_records": n_led, "numbers_checked": n_fr, "conditions_checked": n_cond,
          "decided_blocks_unchanged": n_dec, "script_sha": sha_file(os.path.abspath(__file__))}
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    report(raw, new_raw, facts, n_led, n_fr, n_cond, n_dec)
    print("ricevuta: %s" % RECEIPT)
    print("ESITO: APPLICATA")


def cmd_verify():
    if not os.path.exists(RECEIPT):
        raise PatchError("ricevuta assente: la patch non e' stata applicata")
    rc = json.load(open(RECEIPT, encoding="utf-8"))
    sha = sha_file(TEX)
    ref, lad, prot, ledger, facts = load_inputs()
    text = open(TEX, "rb").read().decode("utf-8")
    n_fr, n_cond = check_numbers(text, ref, lad, prot, ledger, facts)
    utc = {i + 1: r["utc"] for i, r in enumerate(ledger)}
    present = all(flat(new) in flat(text) for _, _, new in edits(utc, len(ledger)))
    same = sha == rc["sha_after"]
    print("tex: %s...  %s" % (sha[:12], "= sha dopo la patch" if same else "DIVERSO da %s... (modificato dopo)" % rc["sha_after"][:12]))
    print("testi nuovi presenti: %s; riscontro: %d frasi e %d condizioni PASS" % ("4/4" if present else "NO", n_fr, n_cond))
    if not present:
        raise PatchError("uno dei testi della patch non e' piu' nel tex")
    print("ESITO: %s" % ("PASS" if same else "PASS SUI NUMERI, tex modificato dopo la patch"))
    return 0


# ----------------------------------------------------------------------------- selftest

DECIDED = ("% >>> TESTO DECISO: ancore-SGC\nIn the northern cap every stage of the pipeline reproduces a frozen value.\n"
           "% <<< TESTO DECISO\n")
CITES = ("(records 6 and 7). amendment to the protocol (record 15). declared before execution (record 16). "
         "(records 16 and 18). the data reject (record 19). It is withdrawn (record 37). precision (record 38). "
         "every point (record 44). before the runs (record 55).\n"
         "% commento: record 99 non conta\n\\todo{la larghezza di $\\nu$ ritirata come falsificazione (record 54)}\n")


FX_HEAD = ("% and checked word by word and number by number against it; declared\n"
           "% edits (cross-references only) are listed next to each block.\n\n"
           "% --- series shorthands ------------------------------------------------------\n"
           "\\defcitealias{M26}{M26}\n\\defcitealias{Paper1}{Paper~1}\n\n"
           "\\todo{Definire le abbreviazioni:\n\\citet{M26}, hereafter \\citetalias{M26}; \\citet{Paper1}, hereafter\n"
           "\\citetalias{Paper1}. Dire che cosa aggiunge.}\n\n"
           "\\begin{proposition}[\\citetalias{Paper1}, section 2.3]\nx\n\\end{proposition}\n")
FX_CITES = ("As in \\citetalias{M26}\n(section~5.6), about. (\\citetalias{Paper1},\nsection~7.2). by\n"
            "\\citetalias{Paper1}, and bounded. \\citepalias[section~4]{M26}. "
            "(Section~\\ref{sec:erosion}; \\citetalias{Paper1}, section~7.1). "
            "listed by \\citetalias{Paper1} (table~8) as. table~1 of \\citetalias{M26}, and.\n")
DECIDED2 = ("% >>> TESTO DECISO: limitazioni\nOf the eleven limitations listed in \\citetalias{M26} (section~7), "
            "this paper.\n% <<< TESTO DECISO\n")


def _fixture(eol="\n"):
    body = (FX_HEAD + "\n" + FX_CITES + "\n" + DECIDED2 + "\n\\subsection{DESI}\n\\label{sec:desi}\n" + OLD_21 + "\n\\subsection{Mock}\n\\label{sec:ensembles}\n" + OLD_22 +
            "\n\\subsection{Pre-registered protocol and frozen records}\n\\label{sec:protocol}\n" + OLD_23 + "\n" + DECIDED +
            "\n" + CITES + "\n\\section{Technical details}\n" + OLD_APPC + "\n\\bsp\n")
    return body.replace("\n", eol)


def _ledger_fx():
    utc = {i: "2026-08-26T07:20:59Z" for i in range(1, 6)}
    utc.update({6: "2026-08-26T11:58:03Z", 7: "2026-08-26T11:58:03Z", 8: "2026-08-27T00:00:00Z", 9: "2026-08-27T00:00:00Z",
                10: "2026-08-27T00:00:00Z", 11: "2026-08-27T00:00:00Z", 12: "2026-08-28T12:30:00Z"})
    for i in range(13, 79):
        utc[i] = "2026-09-%02dT%02d:%02d:00+00:00" % (min(24, 1 + i // 4), i % 24, i % 60)
    utc.update({13: "2026-08-29T09:45:47+00:00", 15: "2026-08-31T07:57:47+00:00", 16: "2026-08-31T19:59:15+00:00",
                18: "2026-09-01T06:04:11+00:00", 19: "2026-09-01T12:37:45+00:00", 37: "2026-09-03T17:52:00+00:00",
                38: "2026-09-04T10:37:34+00:00", 44: "2026-09-06T04:30:06+00:00", 54: "2026-09-08T03:21:26+00:00",
                55: "2026-09-08T04:26:17+00:00"})
    return [{"utc": utc[i], "type": "protocol"} for i in range(1, 79)]


def _ref_fx():
    return {"primary": {"NGC": {"N_H1_DESI": 28256, "mock_mean": 35436.7, "mock_sd": 313.0, "n_mocks": 2000,
                                "empirical_rank": "1/2001", "deficit_abs": 7180.7, "deficit_frac": 0.2026},
                        "SGC_n2000": {"N_H1_DESI": 15122, "mock_mean": 18713.0, "mock_sd": 197.8, "n_mocks": 2000,
                                      "empirical_rank": "1/2001", "deficit_abs": 3591.0, "deficit_frac": 0.1919}},
            "geometry": {"NGC": {"n_gal": 217614, "n_rand": 13248857, "mask_voxels": 307805},
                         "SGC": {"n_gal": 82429, "mask_voxels": 172225}}}


def _lad_fx():
    return {"NGC": {"n_voxel_maschera": 307805, "sigma_px": 0.32042249039652254, "N_H1_k0": 28256, "N_H1_k1": 23790},
            "SGC": {"n_voxel_maschera": 172225, "sigma_px": 0.3360550006514459, "N_H1_k0": 15122, "N_H1_k1": 12011}}


PROT_FX = ("| `N_data` / `N_rand` | 217 614 / 13 248 857 | 82 429 / 5 432 939 |\n"
           "Ensemble v1 is 5 tiers, 34 836 files\n**Twelve records exist at the date of this version.**\n")


def _facts_fx():
    return {"commit_is_ancestor": True, "commit_date": "2026-08-27T13:38:06+02:00",
            "committer_date": "2026-08-27T13:38:06+02:00", "v10_sha": PROT_V10,
            "sections_differ": ["2", "9"], "twelve_in_protocol": True, "v1_files": 34836}


def _utc():
    return {i + 1: r["utc"] for i, r in enumerate(_ledger_fx())}


def _t_lf():
    new = patch_text(_fixture(), _utc(), 78)
    ok = new.count("\\todo{") == 3 and "\\label{tab:ledger}" in new and "(73c8213)" in new
    try:
        patch_text(new, _utc(), 78)
    except PatchError:
        return ok
    return False


def _t_crlf():
    new = patch_text(_fixture("\r\n"), _utc(), 78)
    return new.count("\r\n") == new.count("\n") and table_records(new) == [r for r, _ in LEDGER_ROWS]


def _t_ancore():
    t = _fixture()
    try:
        patch_text(t.replace("campo congelato;", "campo congelato,"), _utc(), 78)
    except PatchError:
        pass
    else:
        return False
    try:
        patch_text(t + OLD_22, _utc(), 78)
    except PatchError:
        return True
    return False


def _t_misti():
    try:
        patch_text(_fixture().replace("\n", "\r\n", 1), _utc(), 78)
    except PatchError:
        return True
    return False


def _t_decisi():
    t = _fixture()
    n = check_decided(t, patch_text(t, _utc(), 78))
    try:
        check_decided(t, t.replace("every stage", "each stage"))
    except PatchError:
        pass
    else:
        return False
    try:
        check_decided(t, patch_text(t, _utc(), 78).replace("\\citet[section~7]{M26}", "\\citet{M26}"))
    except PatchError:
        return n == 2
    return False


def _t_citazioni():
    t = _fixture()
    out, cnt = convert_citations(t)
    attesi = ["As in \\citet[section~5.6]{M26}, about", "(\\citealt[section~7.2]{Paper1})",
              "\\citet{Paper1}, and bounded", "\\citep[section~4]{M26}",
              "(Section~\\ref{sec:erosion}; \\citealt[section~7.1]{Paper1})", "listed by \\citet[table~8]{Paper1} as",
              "table~1 of \\citet{M26}, and", "\\begin{proposition}[{\\citealt[section~2.3]{Paper1}}]",
              "listed in \\citet[section~7]{M26}, this paper", "senza abbreviazioni: \\citet{M26} e \\citet{Paper1}",
              "Marconi (2026a) and (2026b), in place of the shorthands"]
    ok = all(a in out for a in attesi) and aliases_left(out) == 0 and convert_rules(out) == out
    ok = ok and cnt == {"M26": 6, "Paper1": 6}
    try:
        convert_citations(t.replace("\\defcitealias{Paper1}{Paper~1}\n", ""))
    except PatchError:
        return ok
    return False


def _t_numeri():
    new = patch_text(_fixture(), _utc(), 78)
    n_fr, n_cond = check_numbers(new, _ref_fx(), _lad_fx(), PROT_FX, _ledger_fx(), _facts_fx())
    ok = (n_fr, n_cond) == (13 + len(LEDGER_ROWS), 11)
    guasti = []
    r = _ref_fx(); r["primary"]["SGC_n2000"]["mock_mean"] = 18713.04 + 0.1; guasti.append((r, _lad_fx(), PROT_FX, _ledger_fx(), _facts_fx()))
    l = _lad_fx(); l["SGC"]["N_H1_k1"] = 12012; guasti.append((_ref_fx(), l, PROT_FX, _ledger_fx(), _facts_fx()))
    guasti.append((_ref_fx(), _lad_fx(), PROT_FX, _ledger_fx() + [{"utc": "2026-09-25T00:00:00Z"}], _facts_fx()))
    guasti.append((_ref_fx(), _lad_fx(), PROT_FX.replace("5 432 939", "5 432 940"), _ledger_fx(), _facts_fx()))
    for g in guasti:
        try:
            check_numbers(new, *g)
        except PatchError:
            continue
        return False
    return ok


def _t_git():
    new = patch_text(_fixture(), _utc(), 78)
    for key, val in (("commit_date", "2026-08-29T10:00:00+02:00"), ("commit_is_ancestor", False),
                     ("v10_sha", "0" * 64), ("sections_differ", ["2", "5", "9"])):
        f = _facts_fx()
        f[key] = val
        try:
            check_numbers(new, _ref_fx(), _lad_fx(), PROT_FX, _ledger_fx(), f)
        except PatchError:
            continue
        return False
    return True


def _t_citati():
    new = patch_text(_fixture(), _utc(), 78)
    ok = cited_records(new) == set(table_records(new)) and 99 not in cited_records(new)
    try:
        check_numbers(new.replace("(record 55).", "(record 55). Also record 61."), _ref_fx(), _lad_fx(), PROT_FX,
                      _ledger_fx(), _facts_fx())
    except PatchError:
        pass
    else:
        return False
    try:
        check_numbers(new.replace("every point (record 44).", "every point."), _ref_fx(), _lad_fx(), PROT_FX,
                      _ledger_fx(), _facts_fx())
    except PatchError:
        return ok
    return False


def _t_sezioni():
    a = "# t\n\n## 0. A\nx\n## 1. B\ny\n## 2. C\nz\n"
    b = "# u\n\n## 0. A\nx\n## 1. B\ny\n## 2. C\nw\n"
    s0, s1 = sections(a), sections(b)
    return sorted(k for k in set(s0) | set(s1) if s0.get(k) != s1.get(k)) == ["2"]


def _t_ascii_graffe():
    for _, _, new in edits(_utc(), 78):
        try:
            new.encode("ascii")
        except UnicodeEncodeError:
            return False
        body = "\n".join(l for l in new.splitlines() if not l.lstrip().startswith("%"))
        if body.count("{") != body.count("}") or body.count("$") % 2 or body.count("\\begin{") != body.count("\\end{"):
            return False
    return True


def _t_etichette():
    known = {"sec:dilation", "sec:v2", "sec:geometry", "sec:weighting", "sec:isotropic", "sec:r2", "sec:protocol",
             "app:technical", "tab:ledger", "app:ledger"}
    txt = "".join(n for _, _, n in edits(_utc(), 78))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", txt))
    labels = set(re.findall(r"\\label\{([^}]+)\}", txt))
    return refs <= known and labels == {"app:technical", "app:ledger", "tab:ledger"}


def _t_migliaia():
    return th(13248857) == "13\\,248\\,857" and th(307805) == "307\\,805" and th1(35436.7) == "35\\,436.7" and th(2000) == "2\\,000"


TESTS = [
    ("quattro sostituzioni su LF; seconda applicazione -> errore", _t_lf),
    ("CRLF conservato; tabella con gli undici record", _t_crlf),
    ("ancora assente o doppia -> errore", _t_ancore),
    ("fine riga misti nel file -> errore", _t_misti),
    ("testi decisi invariati a meno delle citazioni; uno toccato -> errore", _t_decisi),
    ("citazioni autore-anno: sette forme, preambolo, nota del par. 1.1; una speciale mancante -> errore", _t_citazioni),
    ("riscontro: 24 frasi e 11 condizioni; media, N_H1, ledger o protocollo spostati -> errore", _t_numeri),
    ("git: data, ascendenza, v1.0 o sezioni diverse -> errore", _t_git),
    ("record citati = tabella; un citato in piu' o in meno -> errore; i commenti non contano", _t_citati),
    ("confronto per sezioni del protocollo", _t_sezioni),
    ("testo nuovo ASCII, graffe, dollari e ambienti bilanciati", _t_ascii_graffe),
    ("riferimenti a etichette note; due etichette nuove", _t_etichette),
    ("separatore delle migliaia", _t_migliaia),
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

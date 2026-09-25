#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_tex_3.py -- Paper 2, manoscritto: il §3 (Theory: invariances of the count) e l'appendice A.

Sei sostituzioni atomiche in papers/paper2/MNRAS/paper2_mnras.tex, ognuna su un'ancora che deve
comparire UNA volta:
  1. l'apertura del §3: un capoverso che dichiara la numerazione continua dal Paper 1 (rimandi, D7);
  2. l'enunciato della Proposition 1 (Paper 1, section 2.3), con f -> phi (f e' la mappa del Lemma 3);
  3. la Proposition 2, con la notazione della griglia (eq. grid) e il capoverso che la segue;
  4. la Proposition 2', con il limite sulle dilatazioni campionate;
  5. il Lemma 3 (convenzione della pipeline, F_AP = r f'/f), il gauge di Chebyshev, la decomposizione
     a sei termini e il posizionamento rispetto a M26 section 4.1 e Paper 1 section 2.3;
  6. le dimostrazioni dell'appendice A.

Prima di scrivere:
  - sha del tex = 12e3baf7... (quello dopo la patch del §7.2); se e' gia' quello dopo questa patch, lo dice;
  - ogni numero del testo nuovo e' riscontrato: il limite della Prop. 2' e' CALCOLATO qui dalle celle di
    results/paper2/fig_F1.jsonl alle sei alpha del blocco A (lette nel §4.2 del tex), lo spostamento
    misurato viene dallo stesso registro, alpha_iso = 1 della linea B da alpha_minimax;
  - i blocchi TESTO DECISO restano identici byte per byte.
Il selftest verifica anche, su nuvole di punti sintetiche, le forme chiuse della Prop. 2 e 2' e le tre
parti del Lemma 3: il testo non afferma nulla che lo script non abbia rifatto.
Fine riga: quello del file (LF o CRLF), mai misto. Scrittura atomica (temporaneo + os.replace).
Ricevuta: logs/patch_tex_3.json.

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
REG = J("results", "paper2", "fig_F1.jsonl")
RECEIPT = J("logs", "patch_tex_3.json")
SHA_BEFORE = "12e3baf7d5878df0f4e6d85e95d5c943fffc460d209c7a53e412f460eeda28a5"

N_GRID = 128
PAD = 5.0
CAPS = ("NGC", "SGC")
LINE_B = ("B1", "B2", "B4", "B5", "B6")
# la frase del §4.2 da cui si leggono le sei alpha del blocco A (non si riscrivono qui)
ALPHA_SENTENCE = ("A1 and A3 at $\\aiso = 0.9725$ and 1.0406, their mirrors A1m and A3m at 1.0275 and 0.9594, "
                  "and A0 and A0m at 0.981373 and 1.018627")

# ----------------------------------------------------------------------------- testo

OLD_LEAD = r"""\section{Theory: invariances of the count}
\label{sec:theory}

\subsection{Monotone invariance}
"""

NEW_LEAD = r"""\section{Theory: invariances of the count}
\label{sec:theory}
% Fonti: checklist, tabella dei rimandi (D7): la Prop. 1 e' del Paper 1, section 2.3; Prop. 2, 2' e
% Lemma 3 ne continuano la numerazione, e il testo lo dichiara.

This section collects the exact statements on which the rest of the paper
relies. The first is Proposition~1 of \citetalias{Paper1} (section~2.3),
restated with its number; the results of this paper continue that numbering,
with Proposition~2, its implemented form 2$'$ and Lemma~3. Proposition~1
concerns the values of the filtered field, Proposition~2 the cells that carry
them, and Lemma~3 the map that a change of fiducial cosmology applies to the
positions. The proofs of the last three are in Appendix~\ref{app:proofs}.

\subsection{Monotone invariance}
"""

OLD_P1 = r"""\todo{riportare l'enunciato della Proposition~1 del Paper~1, section 2.3.}
"""

NEW_P1 = r"""% Enunciato del Paper 1, section 2.3 (proof MN262388P, p. 2), con f -> \phi: qui f e' la
% rimappatura radiale del Lemma 3.
Let $\phi$ be a real-valued function on the top-dimensional cells of a finite
cubical complex, filtered by superlevel sets, and let $g$ be a strictly
increasing function on the real line. Then the persistence diagram of
$g \circ \phi$ is the image under $g$ of the diagram of $\phi$. In particular
the number of finite pairs in every homological dimension, including $\NH$, is
exactly invariant, and every Betti curve is invariant up to the
reparametrization $\nu \to g(\nu)$ of the threshold axis.
"""

OLD_P2 = r"""\begin{proposition}
\label{prop:dilation}
\todo{Proposition 2: stesso campo, due dilatazioni isotrope, diagrammi identici.}
\end{proposition}
"""

NEW_P2 = r"""% Fonti: paper2_item11.md (25 ago 2026), 1.1a: Lemma A, Proposizione 2, testo per il manoscritto;
% passi P1-P7 della pipeline (derive_box: o_k = min_j R_jk - p, L = E + 2p, dx = L/N); N = 128, p = 5.
The pipeline carries physical lengths in one step only. From the comoving
positions of the galaxies, $\mathbf{r}_i$, and of the randoms, $\mathbf{R}_j$,
it derives the embedding cube: on each axis $k$ the origin
$o_k = \min_j R_{jk} - p$, where $p$ is a padding; the side $L = E + 2p$, where
$E$ is the largest extent of the randoms over the three axes; and the cell
$\Delta x = L/N$ of an $N^3$ grid, here with $N = 128$ and
$p = 5\,h^{-1}$\,Mpc. Every later step (mass assignment, mask, density
contrast, smoothing and superlevel filtration) sees the positions only through
their grid coordinates,
\begin{equation}
u_{ik} = \frac{r_{ik} - o_k}{\Delta x}.
\label{eq:grid}
\end{equation}

\begin{proposition}
\label{prop:dilation}
Let the embedding cube be derived from the bounding box of the randoms with a
padding that is zero or proportional to the extent of the box, and let the
smoothing scale $\sigmapx$ be fixed in grid units. Then an isotropic dilation
$\mathbf{r} \to \alpha\mathbf{r}$, $\alpha > 0$, applied to galaxies and
randoms alike leaves the grid coordinates of every object unchanged, and with
them the mask, the smoothed field and its persistence diagram. In particular
$\NH$ is exactly invariant.
\end{proposition}

The proof (Appendix~\ref{app:proofs}) uses no property of persistent homology:
it concerns the parametrization of the field, not the statistic, and holds for
any mass-assignment scheme, any kernel specified in grid units and any
homological degree. Fig.~\ref{fig:prop2} shows it at work. The pipeline of
\citetalias{M26}, used here, specifies the smoothing in physical units instead,
$R = 5\,h^{-1}$\,Mpc, so that $\sigmapx = R/\Delta x$. A dilation of the survey
together with its grid can then reach $\NH$ through $\sigmapx$ and through
nothing else: the isotropic part of a change of fiducial cosmology is a
convention of the grid, which Section~\ref{sec:isotropic} measures and removes.
"""

OLD_P2P = r"""\begin{propositionprime}{2}
\todo{Proposition 2$'$: il residuo dell'implementazione. Citare la
Fig.~\ref{fig:prop2}.}
\end{propositionprime}
"""

NEW_P2P = r"""% Fonti: paper2_item11.md, 1.1a' (forma chiusa, punto fisso N/2); checklist 1.1a (il termine p/dx,
% che predice a 1e-4). Numeri: results/paper2/fig_F1.jsonl, cells e block_A_max_grid_shift_voxel
% (fase3.jsonl, gauge 'regauged'); il limite e' calcolato dal patcher alle sei alpha del blocco A
% (Section 4.2): 0.013489 (NGC) e 0.014143 (SGC) a alpha = 0.9594, misurati 0.013487 e 0.014092.
% Gauge a cubo costante: checklist 0.14b (derive_box con pad = 5, poi dc_tab * c e pad = 5 c).
The implementation pads the cube by a fixed length, whatever the dilation, so
the side scales as $\alpha E + 2p$ rather than $\alpha(E + 2p)$ and
Proposition~\ref{prop:dilation} does not apply as stated. The residual has a
closed form.

\begin{propositionprime}{2}
With a padding of fixed length $p$, and otherwise the hypotheses of
Proposition~\ref{prop:dilation}, the grid coordinates after the dilation
$\mathbf{r} \to \alpha\mathbf{r}$ are an affine function of those before it,
the same on the three axes:
\begin{equation}
\begin{aligned}
&u_k(\alpha) = a\,u_k(1) + b,\\
&a = \frac{\alpha(E + 2p)}{\alpha E + 2p}, \qquad
b = \frac{Np\,(1 - \alpha)}{\alpha E + 2p}.
\end{aligned}
\label{eq:prop2p}
\end{equation}
The map is an isotropic dilation of the grid coordinates by the factor $a$
about the centre of the cube, $u = N/2$. No grid coordinate of an object inside
the bounding box of the randoms moves by more than
$(N/2 - p/\Delta x)\,|a - 1|$, where $\Delta x$ is the cell before the
dilation.
\end{propositionprime}

Two properties separate this residual from the signal. It is isotropic, a
dilation about the centre of the cube, and cannot imitate an anisotropic
deformation; and it is known in closed form. On the isotropic line, the
constant-cube gauge of Section~\ref{sec:isotropic}, which derives the cube of
each point with the same fixed padding before rescaling it, leaves the same
map. Over the dilations sampled in this paper, $|1 - \alpha| \le 0.0406$, the
bound is largest at $\alpha = 0.9594$: 0.0135 voxel in NGC and 0.0141 in SGC.
The largest displacements measured object by object on the data, 0.0135 and
0.0141 voxel, lie within 0.4 per cent of it (Section~\ref{sec:anisotropic}).
Proposition~\ref{prop:dilation} therefore holds for the pipeline as
implemented to that accuracy, and exactly when the padding is dilated with the
survey (Section~\ref{sec:isotropic}). What the residual does to the count is
measured on the isotropic line, where Proposition~\ref{prop:dilation} leaves no
signal (Section~\ref{sec:apdeficit}).
"""

OLD_L3 = r"""\begin{lemma}
\label{lem:gauge}
\todo{Lemma 3; il gauge di Chebyshev della decomposizione; posizionamento
rispetto a M26 section 4.1 e Paper~1 section 2.3. Dimostrazioni in
Appendix~\ref{app:proofs}.}
\end{lemma}
"""

NEW_L3 = r"""% Fonti: paper2_item13.md, 1 (Lemma 3), scritto qui nella convenzione della pipeline (checklist 1.3a:
% F_AP = alpha_par/alpha_perp = r f'/f, dunque f = A r^{F_0}; item13 usa lo standard, f/(r f')); checklist
% 0.14b(d) (invarianza sotto f -> c f); checklist 1.2 (gauge minimax); results/paper2/fig_F1.jsonl,
% alpha_minimax = 1 sulla linea B; sei termini: checklist 3.3 e 1.1b. Posizionamento: checklist 1.1c;
% M26 section 4.1 (28 256 invariato sotto tre rimappature monotone; 4272 gruppi di pareggi rotti,
% 3 generatori); Paper 1 section 2.3 (enunciato standard, nessuna novita' rivendicata).
A change of fiducial cosmology enters the pipeline as a single radial
remapping of the comoving distance, $r \to f(r)$, applied to galaxies and
randoms alike and the same in every direction. At distance $r$ it dilates
separations across the line of sight by $f(r)/r$ and along it by $f'(r)$.

\begin{lemma}
\label{lem:gauge}
Let $f$ be a positive, increasing and differentiable remapping of the comoving
distance on an interval $[r_1, r_2]$ with $r_1 > 0$, and write the
Alcock--Paczy\'{n}ski parameter as the ratio of the line-of-sight to the
transverse dilation,
\begin{equation}
\FAP(r) = \frac{r f'(r)}{f(r)} = \frac{{\rm d}\ln f}{{\rm d}\ln r}.
\label{eq:fap}
\end{equation}
(i) $\FAP$ is constant and equal to $F_0$ on the interval if and only if
$f(r) = A r^{F_0}$ with $A > 0$; in particular $\FAP \equiv 1$ if and only if
$f$ is a dilation. (ii) $\FAP$ is unchanged by $f \to cf$ for any $c > 0$.
(iii) Exactly one dilation $r \to \alpha r$ minimizes the largest residual
$\max_{[r_1, r_2]} |f(r) - \alpha r|$, and it is the only one at which the
residual reaches its largest modulus with both signs.
\end{lemma}

Part~(i) fixes the parametrization of the grid. The isotropic channel of
Proposition~\ref{prop:dilation} is the power law of unit exponent and needs no
separate argument; a line of constant $\FAP$ is the explicit family
$f = A r^{F_0}$, so no pivot redshift has to be chosen; and
equation~(\ref{eq:fap}) fixes the convention by a formula, not by a name. The
usual Alcock--Paczy\'{n}ski parameter, the ratio of the transverse to the
line-of-sight dilation, is its reciprocal, and reading one for the other
inverts the sign of the response. Part~(ii) keeps the labels of the grid under
a global rescaling of the distances, such as the one that holds the side of the
cube fixed in the constant-cube gauge (Section~\ref{sec:isotropic}).

Part~(iii) fixes the isotropic coordinate. The split of a remapping into an
isotropic and an anisotropic part, $f(r) = \alpha r + [f(r) - \alpha r]$, is
not unique: each $\alpha$ leaves a different residual. By
Proposition~\ref{prop:dilation} the grid absorbs the isotropic part at no cost,
so what a remapping can do to the count depends on it only up to a dilation,
and the measure of its anisotropic content that respects this freedom is its
distance from the dilations in the uniform norm, over the radial range of the
survey. We define $\aiso$ as the minimizer of part~(iii), a Chebyshev (minimax)
criterion, and the minimax residual of a deformation as the largest value of
$|f(r) - \aiso r|$. The points that carry the signal have $\aiso = 1$ by
construction (Section~\ref{sec:anisotropic}). A least-squares fit would give
instead a weighted mean of $f/r$, whose largest residual cannot be smaller and
depends on the weighting; Section~\ref{sec:anisotropic} gives the size of the
difference.

Proposition~\ref{prop:dilation} and Lemma~\ref{lem:gauge} say what can act:
once the gauge is fixed, only the anisotropic residual of $f$ carries physical
content. The construction adds other ways for the count to move, and the
response to a deformation is decomposed accordingly into six terms: (a) the
convention for $\sigmapx$, set in physical units; (b) the anisotropic response,
the signal; (c) the carving of the mocks, which selects galaxies in redshift
and so changes which of them enter when the distance--redshift relation
changes; (d) the tiling of the periodic simulation box, whose replicas a
deformation maps onto different voxels; (e) the number of voxels in the mask,
which a deformation changes at the boundary; and (f) the residual of
Proposition~2$'$. What none of them describes is a remainder.
Section~\ref{sec:apdeficit} measures the terms.

The three results act on different objects. Proposition~\ref{prop:monotone}
concerns the codomain of the field, the order of the cell values.
\citetalias{M26} (section~4.1) states it for the count and verifies it on the
DESI field: three monotone remappings of the filtered field leave
$\NH = 28\,256$ unchanged, and a variant of the rank remapping that breaks the
exact ties between cells moves it by three generators, which no strictly
increasing map can do. \citetalias{Paper1} (section~2.3) states it for any
function on a cubical complex, as a standard fact.
Proposition~\ref{prop:dilation} concerns the domain, which object falls in
which cell, and Lemma~\ref{lem:gauge} the map that the fiducial cosmology
applies to the positions. The two propositions compose: an increasing map of
the values of a field whose cells are unchanged leaves the diagram unchanged.
Proposition~\ref{prop:dilation} closes the isotropic channel of the geometry,
Proposition~\ref{prop:monotone} the channel of any increasing map of the
filtered field, and no explanation of the deficit can act through either. In
this pipeline one operation escapes the second, the transform of the density
contrast, which acts before the smoothing; \citetalias{M26} (section~4.1)
bounds it. What neither proposition covers is the subject of the next three
sections: the anisotropic part of the geometry, the weighting and the
cosmology.
"""

OLD_APP = r"""\todo{dimostrazioni di Proposition~\ref{prop:dilation}, della 2$'$ e del
Lemma~\ref{lem:gauge}.}
"""

NEW_APP = r"""% Fonti: paper2_item11.md, 1.1a e 1.1a' (Lemma A, dimostrazioni); paper2_item13.md, 1 (Lemma 3, i).
% La parte (iii) del Lemma 3 e' l'alternanza di Chebyshev per la sola funzione r, positiva
% sull'intervallo; la dimostrazione e' completa qui. Tutte e tre rifatte numericamente nel selftest
% di src/paper2_patch_tex_3.py.
We use the notation of Section~\ref{sec:dilation}: $N$ cells per side, padding
$p$, largest extent $E$ of the randoms over the three axes, origin
$o_k = \min_j R_{jk} - p$, side $L = E + 2p$, cell $\Delta x = L/N$ and grid
coordinates $u_{ik}$ from equation~(\ref{eq:grid}).

\medskip\noindent\textit{Proposition~\ref{prop:dilation}.} For $\alpha > 0$ the
dilation preserves the order of the coordinates on each axis, so the minimum
and the maximum of the randoms on every axis are multiplied by $\alpha$, and so
is every extent: $E \to \alpha E$ exactly. With $p \to \alpha p$, including
$p = 0$, it follows that $L \to \alpha L$, $\Delta x \to \alpha\Delta x$ and
$o_k \to \alpha o_k$, hence
$u_{ik} \to (\alpha r_{ik} - \alpha o_k)/(\alpha\Delta x) = u_{ik}$ for every
object and axis. Mass assignment, the mask, the normalization of the random
field, the density contrast, the smoothing with $\sigmapx$ in grid units and
the superlevel filtration depend on the positions only through the $u_{ik}$,
and the weights are attached to the objects. The field is therefore the same
cell by cell, and so is its persistence diagram.

\medskip\noindent\textit{Proposition~2$'$.} Write $s_k = r_k - \min_j R_{jk}$
for an object, so that $u_k(1) = (s_k + p)N/(E + 2p)$. Under the dilation
$s_k \to \alpha s_k$ and $E \to \alpha E$, while $p$ does not change, so
$u_k(\alpha) = (\alpha s_k + p)N/(\alpha E + 2p)$. Eliminating
$s_k = u_k(1)(E + 2p)/N - p$ gives equation~(\ref{eq:prop2p}), with the same
$a$ and $b$ on every axis. Since $1 - a = 2p(1 - \alpha)/(\alpha E + 2p)$, the
fixed point $b/(1 - a)$ is $N/2$, and
$u_k(\alpha) - u_k(1) = (a - 1)\,[u_k(1) - N/2]$. For an object inside the
bounding box of the randoms, $p/\Delta x \le u_k(1) \le (E_k + p)/\Delta x$ on
each axis, where $E_k \le E$ is the extent of the randoms along axis $k$. Since
$(E + p)/\Delta x = N - p/\Delta x$, it follows that
$|u_k(1) - N/2| \le N/2 - p/\Delta x$, with equality at the extreme randoms of
the longest axis.

\medskip\noindent\textit{Lemma~\ref{lem:gauge}.} (i) $\FAP = F_0$ on the
interval is the equation ${\rm d}\ln f/{\rm d}\ln r = F_0$, whose solutions are
$\ln f = F_0 \ln r + {\rm const}$, that is $f = A r^{F_0}$ with $A > 0$;
conversely, this $f$ has $\FAP = F_0$. For $F_0 = 1$, $f = Ar$ is a dilation.
(ii) ${\rm d}\ln(cf) = {\rm d}\ln f$. (iii) Let
$\epsilon_\alpha(r) = f(r) - \alpha r$ and
$M(\alpha) = \max_{[r_1, r_2]} |\epsilon_\alpha|$. The function $M$ is
continuous and grows without bound as $|\alpha| \to \infty$, because
$r \ge r_1 > 0$, so it has a minimum. Suppose that at $\alpha_*$ the residual reaches $+M(\alpha_*)$ at
$r_+$ and $-M(\alpha_*)$ at $r_-$. For $\alpha > \alpha_*$,
$\epsilon_\alpha(r_-) = -M(\alpha_*) - (\alpha - \alpha_*)\,r_- < -M(\alpha_*)$;
for $\alpha < \alpha_*$,
$\epsilon_\alpha(r_+) = M(\alpha_*) + (\alpha_* - \alpha)\,r_+ > M(\alpha_*)$.
Every other $\alpha$ has a larger maximum, and $\alpha_*$ is the only
minimizer. Suppose instead that at some $\alpha$ the largest modulus
$M = M(\alpha)$ is reached with the positive sign only, so that
$m = \min \epsilon_\alpha > -M$. For $0 < \delta < (M + m)/r_2$, the residual
$\epsilon_{\alpha + \delta}(r) = \epsilon_\alpha(r) - \delta r$ lies between
$m - \delta r_2 > -M$ and $M - \delta r_1 < M$, so $M(\alpha + \delta) < M$
and $\alpha$ is not a minimizer; the negative sign is symmetric, with
$\delta < 0$. The minimizer therefore reaches both signs, and by the first
argument it is the only $\alpha$ that does.
"""

EDITS = [("apertura del §3", OLD_LEAD, NEW_LEAD),
         ("Proposition 1", OLD_P1, NEW_P1),
         ("Proposition 2", OLD_P2, NEW_P2),
         ("Proposition 2'", OLD_P2P, NEW_P2P),
         ("Lemma 3 e gauge", OLD_L3, NEW_L3),
         ("appendice A", OLD_APP, NEW_APP)]


class PatchError(Exception):
    pass


def eol_of(text):
    crlf = text.count("\r\n")
    lf = text.count("\n")
    if crlf and crlf != lf:
        raise PatchError("fine riga misti nel tex: %d CRLF su %d LF" % (crlf, lf))
    return "\r\n" if crlf else "\n"


def patch_text(text):
    """Le sei sostituzioni, tutte o nessuna."""
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
    check_decided(text, out)
    return out


def flat(s):
    return re.sub(r"\s+", " ", s)


def decided_blocks(text):
    return re.findall(r"% >>> TESTO DECISO.*?% <<< TESTO DECISO", text, flags=re.S)


def check_decided(before, after):
    b, a = decided_blocks(before), decided_blocks(after)
    if b != a:
        raise PatchError("un blocco TESTO DECISO e' cambiato (%d prima, %d dopo)" % (len(b), len(a)))
    return len(b)


# ----------------------------------------------------------------------------- numeri

def alphas_from_tex(text):
    t = flat(text)
    if ALPHA_SENTENCE not in t:
        raise PatchError("frase del §4.2 con le alpha del blocco A non trovata")
    return [float(x) for x in re.findall(r"\d\.\d+", ALPHA_SENTENCE)]


def bound(alpha, cell, N=N_GRID, p=PAD):
    """(N/2 - p/dx)|a - 1| della Prop. 2', con E dal cubo fiduciale: E = N dx - 2p."""
    E = N * cell - 2 * p
    a = alpha * (E + 2 * p) / (alpha * E + 2 * p)
    return (N / 2.0 - p / cell) * abs(a - 1.0)


def fmt_alpha(x):
    s = ("%.6f" % x).rstrip("0")
    return s if len(s.split(".")[1]) >= 4 else "%.4f" % x


def checks_from(rec, alphas):
    cells, meas = rec["cells"], rec["block_A_max_grid_shift_voxel"]
    bnd, argm = {}, {}
    for c in CAPS:
        vals = [(bound(a, cells[c]), a) for a in alphas]
        bnd[c], argm[c] = max(vals)
    amax = max(abs(1 - a) for a in alphas)
    fr = [("|1-alpha| massimo", "$|1 - \\alpha| \\le %.4f$" % amax),
          ("limite della Prop. 2'", "the bound is largest at $\\alpha = %s$: %.4f voxel in NGC and %.4f in SGC"
           % (fmt_alpha(argm["NGC"]), bnd["NGC"], bnd["SGC"])),
          ("spostamento misurato", "measured object by object on the data, %.4f and %.4f voxel,"
           % (meas["NGC"], meas["SGC"])),
          ("N e p", "here with $N = %d$ and $p = %d\\,h^{-1}$\\,Mpc" % (N_GRID, int(PAD))),
          ("M26 section 4.1", "leave $\\NH = 28\\,256$ unchanged")]
    rel = {c: (bnd[c] - meas[c]) / bnd[c] for c in CAPS}
    amm = [rec["points"][b]["alpha_minimax"] for b in LINE_B]
    cond = [("stessa alpha di massimo nei due emisferi", argm["NGC"] == argm["SGC"], "%s / %s" % (argm["NGC"], argm["SGC"])),
            ("misurato <= limite, entro 0.4 per cento", all(0.0 <= rel[c] <= 0.004 for c in CAPS),
             "%.2e / %.2e" % (rel["NGC"], rel["SGC"])),
            ("alpha_iso = 1 sulla linea B", all(abs(x - 1.0) < 1e-12 for x in amm), str(amm)),
            ("padding 5 h^-1 Mpc nel registro", all(abs(rec["pad_voxel"][c] * cells[c] - PAD) < 1e-9 for c in CAPS), "-"),
            ("§4.2 'at most 0.014 voxel' coerente", round(max(meas.values()), 3) == 0.014, "%.5f" % max(meas.values()))]
    return fr, cond


def check_numbers(text, rec):
    alphas = alphas_from_tex(text)
    fr, cond = checks_from(rec, alphas)
    t = flat(text)
    bad = [(lab, s) for lab, s in fr if s not in t]
    extra = [("§4.2 'at most 0.014 voxel'", "most 0.014 voxel" in t),
             ("§4.1 '$\\NH = 28\\,256$' due volte", t.count("$\\NH = 28\\,256$") >= 2),
             ("vecchio limite 1.4e-2 assente", "1.4 \\times 10^{-2}" not in t and "1.4\\times10^{-2}" not in t)]
    badc = [(lab, info) for lab, ok, info in cond if not ok] + [(lab, "-") for lab, ok in extra if not ok]
    if bad or badc:
        raise PatchError("riscontro fallito: frasi assenti %s; condizioni false %s" % (bad, badc))
    return len(fr), len(cond) + len(extra)


# ----------------------------------------------------------------------------- disco

def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    return sha_bytes(open(p, "rb").read())


def register_record():
    if not os.path.exists(REG):
        raise PatchError("registro assente: %s" % REG)
    recs = [json.loads(l) for l in open(REG, encoding="utf-8") if l.strip()]
    recs = [r for r in recs if r.get("schema") == "paper2_fig_F1_v1"]
    if not recs:
        raise PatchError("nessun record paper2_fig_F1_v1 in %s" % REG)
    last = recs[-1]
    for r in recs:
        for key in ("cells", "block_A_max_grid_shift_voxel"):
            for c in CAPS:
                if abs(r[key][c] - last[key][c]) > 1e-12:
                    raise PatchError("record di %s discordi su %s.%s" % (REG, key, c))
    return last, len(recs), sha_file(REG)


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
        raise PatchError("sha del tex %s..., atteso %s...: il manoscritto non e' quello dopo il §7.2" % (sha[:12], SHA_BEFORE[:12]))
    text = raw.decode("utf-8")
    new = patch_text(text)
    rec, n_rec, reg_sha = register_record()
    n_fr, n_cond = check_numbers(new, rec)
    return raw, new.encode("utf-8"), rec, n_rec, reg_sha, n_fr, n_cond, check_decided(text, new)


def report(raw, new_raw, rec, n_rec, reg_sha, n_fr, n_cond, n_dec):
    print("tex: %s  %d -> %d byte" % (TEX, len(raw), len(new_raw)))
    print("sha: %s... -> %s..." % (sha_bytes(raw)[:12], sha_bytes(new_raw)[:12]))
    print("ancore: %d/%d sostituite; note di stesura: %d -> %d; testi decisi invariati: %d" % (
        len(EDITS), len(EDITS), raw.decode("utf-8").count("\\todo{"), new_raw.decode("utf-8").count("\\todo{"), n_dec))
    print("riscontro su %s (%s..., %d record concordi, ultimo %s): %d frasi e %d condizioni PASS"
          % (REG, reg_sha[:12], n_rec, rec["utc"][:19], n_fr, n_cond))


def cmd_dry():
    report(*prepare())
    print("ESITO: DRY-RUN PASS (nulla scritto)")


def cmd_apply():
    raw, new_raw, rec, n_rec, reg_sha, n_fr, n_cond, n_dec = prepare()
    tmp = TEX + ".tmp_patch_3"
    with open(tmp, "wb") as fh:
        fh.write(new_raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, TEX)
    if sha_file(TEX) != sha_bytes(new_raw):
        raise PatchError("dopo la scrittura lo sha non coincide")
    os.makedirs(os.path.dirname(RECEIPT), exist_ok=True)
    rc = {"schema": "paper2_patch_tex_3_v1", "utc": datetime.now(timezone.utc).isoformat(),
          "tex": TEX, "sha_before": sha_bytes(raw), "sha_after": sha_bytes(new_raw),
          "bytes_before": len(raw), "bytes_after": len(new_raw),
          "fig_F1_register_sha": reg_sha, "fig_F1_record_utc": rec["utc"],
          "numbers_checked": n_fr, "conditions_checked": n_cond, "decided_blocks_unchanged": n_dec,
          "script_sha": sha_file(os.path.abspath(__file__))}
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    report(raw, new_raw, rec, n_rec, reg_sha, n_fr, n_cond, n_dec)
    print("ricevuta: %s" % RECEIPT)
    print("ESITO: APPLICATA")


def cmd_verify():
    if not os.path.exists(RECEIPT):
        raise PatchError("ricevuta assente: la patch non e' stata applicata")
    rc = json.load(open(RECEIPT, encoding="utf-8"))
    sha = sha_file(TEX)
    rec, n_rec, reg_sha = register_record()
    text = open(TEX, "rb").read().decode("utf-8")
    n_fr, n_cond = check_numbers(text, rec)
    present = all(flat(new) in flat(text) for _, _, new in EDITS)
    same = sha == rc["sha_after"]
    print("tex: %s...  %s" % (sha[:12], "= sha dopo la patch" if same else "DIVERSO da %s... (modificato dopo)" % rc["sha_after"][:12]))
    print("testi nuovi presenti: %s; riscontro su fig_F1.jsonl: %d frasi e %d condizioni PASS"
          % ("6/6" if present else "NO", n_fr, n_cond))
    if not present:
        raise PatchError("uno dei testi della patch non e' piu' nel tex")
    print("ESITO: %s" % ("PASS" if same else "PASS SUI NUMERI, tex modificato dopo la patch"))
    return 0


# ----------------------------------------------------------------------------- selftest: testo

DECIDED = "% >>> TESTO DECISO: D7\nProposition~\\ref{prop:monotone} is usually read as a restriction.\n% <<< TESTO DECISO\n"
SEC42 = ("Two further sets of points lie off line B. Block A lies on the isotropic line\nat $\\FAP = 1$: "
         "A1 and A3 at $\\aiso = 0.9725$ and 1.0406, their mirrors A1m and\nA3m at 1.0275 and 0.9594, and A0 and "
         "A0m at 0.981373 and 1.018627.\nthe same measurement gives at\nmost 0.014 voxel, the residual.\n"
         "reproduce the fiducial count: $\\NH = 28\\,256$ and $23\\,790$ in NGC.\n")


def _fixture(eol="\n"):
    body = (OLD_LEAD + "\n\\begin{proposition}[\\citetalias{Paper1}, section 2.3]\n\\label{prop:monotone}\n" + OLD_P1 +
            "\\end{proposition}\n\n" + DECIDED + "\n\\subsection{Isotropic dilation}\n\\label{sec:dilation}\n\n" + OLD_P2 +
            "\n" + OLD_P2P + "\n\\subsection{The decomposition and its gauge}\n\\label{sec:lemma}\n\n" + OLD_L3 +
            "\n" + SEC42 + "\n\\section{Proofs}\n\\label{app:proofs}\n" + OLD_APP)
    return body.replace("\n", eol)


def _rec_fixture():
    pts = {b: {"alpha_minimax": 1.0} for b in LINE_B}
    pts["B2"]["alpha_minimax"] = 0.9999999999999998
    return {"cells": {"NGC": 15.604397786848558, "SGC": 14.878516880592318},
            "block_A_max_grid_shift_voxel": {"NGC": 0.013487321102000516, "SGC": 0.014092162666905939},
            "pad_voxel": {"NGC": 0.32042249039652254, "SGC": 0.3360550006514459},
            "points": pts, "utc": "2026-09-24T19:44:27"}


def _t_lf():
    new = patch_text(_fixture())
    ok = "\\todo{" not in new and all(n in new for _, _, n in EDITS)
    try:
        patch_text(new)
    except PatchError:
        return ok
    return False


def _t_crlf():
    new = patch_text(_fixture("\r\n"))
    return new.count("\r\n") == new.count("\n") and NEW_L3.replace("\n", "\r\n") in new


def _t_ancore():
    t = _fixture()
    try:
        patch_text(t.replace(OLD_P1, OLD_P1.replace("riportare", "riporta")))
    except PatchError:
        pass
    else:
        return False
    try:
        patch_text(t + OLD_APP)
    except PatchError:
        return True
    return False


def _t_misti():
    try:
        patch_text(_fixture().replace("\n", "\r\n", 1))
    except PatchError:
        return True
    return False


def _t_decisi():
    t = _fixture()
    n = check_decided(t, patch_text(t))
    try:
        check_decided(t, t.replace("usually read", "often read"))
    except PatchError:
        return n == 1
    return False


def _t_numeri():
    new = patch_text(_fixture())
    n_fr, n_cond = check_numbers(new, _rec_fixture())
    ok = (n_fr, n_cond) == (5, 8)
    r = _rec_fixture()
    r["block_A_max_grid_shift_voxel"]["SGC"] = 0.014151          # 0.0142: frase e condizione cadono
    try:
        check_numbers(new, r)
    except PatchError:
        pass
    else:
        return False
    r = _rec_fixture()
    r["points"]["B4"]["alpha_minimax"] = 1.0001
    try:
        check_numbers(new, r)
    except PatchError:
        pass
    else:
        return False
    try:
        check_numbers(new.replace("1.0406, their", "1.0407, their"), _rec_fixture())
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
        if body.count("\\begin{") != body.count("\\end{"):
            return False
    return True


def _t_etichette():
    """Ogni \\ref del testo nuovo punta a un'etichetta del manoscritto o del testo nuovo."""
    known = {"sec:theory", "sec:monotone", "sec:dilation", "sec:lemma", "sec:isotropic", "sec:anisotropic",
             "sec:apdeficit", "prop:monotone", "prop:dilation", "lem:gauge", "fig:prop2", "app:proofs"}
    txt = "".join(n for _, _, n in EDITS)
    labels = set(re.findall(r"\\label\{([^}]+)\}", txt))
    refs = set(re.findall(r"\\ref\{([^}]+)\}", txt))
    return refs <= (known | labels) and labels == {"sec:theory", "prop:dilation", "lem:gauge", "eq:grid", "eq:prop2p", "eq:fap"}


# ----------------------------------------------------------------------------- selftest: matematica

def _cloud(seed=7, n=4000):
    import random
    rnd = random.Random(seed)
    # una calotta lontana dall'osservatore, estensioni diverse sui tre assi (l'asse y domina)
    pts = [(300 + 700 * rnd.random(), -900 + 1900 * rnd.random(), 100 + 500 * rnd.random()) for _ in range(n)]
    return pts


def _grid(pts, pad, N=N_GRID):
    mins = [min(p[k] for p in pts) for k in range(3)]
    maxs = [max(p[k] for p in pts) for k in range(3)]
    E = max(maxs[k] - mins[k] for k in range(3))
    L = E + 2 * pad
    dx = L / N
    o = [mins[k] - pad for k in range(3)]
    return [[(p[k] - o[k]) / dx for k in range(3)] for p in pts], E, dx


def _t_prop2():
    pts = _cloud()
    u1, E, dx = _grid(pts, PAD)
    worst = 0.0
    for al in (0.9594, 1.0406, 1.05):
        pa = [(al * x, al * y, al * z) for x, y, z in pts]
        ua, _, _ = _grid(pa, PAD * al)                       # padding proporzionale: identita'
        worst = max(worst, max(abs(ua[i][k] - u1[i][k]) for i in range(len(pts)) for k in range(3)))
    return worst < 1e-9


def _t_prop2p():
    pts = _cloud()
    u1, E, dx = _grid(pts, PAD)
    for al in (0.9594, 0.9725, 1.0406):
        pa = [(al * x, al * y, al * z) for x, y, z in pts]
        ua, _, _ = _grid(pa, PAD)                            # padding additivo
        a = al * (E + 2 * PAD) / (al * E + 2 * PAD)
        b = N_GRID * PAD * (1 - al) / (al * E + 2 * PAD)
        aff = max(abs(ua[i][k] - (a * u1[i][k] + b)) for i in range(len(pts)) for k in range(3))
        if aff > 1e-9 or abs(b / (1 - a) - N_GRID / 2.0) > 1e-6:
            return False
        shift = max(abs(ua[i][k] - u1[i][k]) for i in range(len(pts)) for k in range(3))
        lim = (N_GRID / 2.0 - PAD / dx) * abs(a - 1)
        if not (shift <= lim + 1e-12 and shift >= lim * (1 - 1e-9)):   # raggiunto dai punti estremi
            return False
    return True


def _minimax(r, f):
    g = [fi / ri for fi, ri in zip(f, r)]
    lo, hi = min(g), max(g)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        d = [fi - mid * ri for fi, ri in zip(f, r)]
        if max(d) - max(-x for x in d) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _t_lemma3():
    import math
    r = [300.0 + 780.0 * i / 2000 for i in range(2001)]
    for F0 in (0.971070, 1.030071):
        f = [1.3 * x ** F0 for x in r]
        # (i): la pendenza di ln f su ln r e' F0, e r f'/f e' costante (differenze centrali)
        fap = [(r[i] * (f[i + 1] - f[i - 1]) / (r[i + 1] - r[i - 1])) / f[i] for i in range(1, 2000)]
        if max(abs(x - F0) for x in fap) > 1e-5:
            return False
        # (ii): invariante sotto f -> c f
        fc = [2.7 * x for x in f]
        fapc = [(r[i] * (fc[i + 1] - fc[i - 1]) / (r[i + 1] - r[i - 1])) / fc[i] for i in range(1, 2000)]
        if max(abs(x - y) for x, y in zip(fap, fapc)) > 1e-9:
            return False
        # (iii): il minimax equioscilla, ed e' l'unico minimo; i minimi quadrati non fanno meglio
        am = _minimax(r, f)
        d = [fi - am * ri for fi, ri in zip(f, r)]
        M = max(abs(x) for x in d)
        if abs(max(d) + min(d)) > 1e-8 * M:
            return False
        for da in (1e-6, -1e-6):
            if max(abs(fi - (am + da) * ri) for fi, ri in zip(f, r)) <= M:
                return False
        als = sum(ri * fi for ri, fi in zip(r, f)) / sum(ri * ri for ri in r)
        if max(abs(fi - als * ri) for fi, ri in zip(f, r)) < M:
            return False
        if not math.isfinite(M):
            return False
    return True


def _t_convenzione():
    """F_AP nella convenzione della pipeline = pendenza di ln f su ln r, non il suo reciproco."""
    import math
    r = [300.0 + 7.8 * i for i in range(101)]
    f = [x ** 1.03 for x in r]
    X = [math.log(x) for x in r]
    Y = [math.log(y) for y in f]
    mx, my = sum(X) / len(X), sum(Y) / len(Y)
    s = sum((x - mx) * (y - my) for x, y in zip(X, Y)) / sum((x - mx) ** 2 for x in X)
    return abs(s - 1.03) < 1e-12 and "\\frac{r f'(r)}{f(r)}" in NEW_L3


TESTS = [
    ("sei sostituzioni su LF; seconda applicazione -> errore", _t_lf),
    ("CRLF conservato, nessun fine riga misto", _t_crlf),
    ("ancora assente o doppia -> errore", _t_ancore),
    ("fine riga misti nel file -> errore", _t_misti),
    ("testi decisi invariati; uno toccato -> errore", _t_decisi),
    ("riscontro: 5 frasi e 8 condizioni; misura, alpha_minimax o alpha del §4.2 spostati -> errore", _t_numeri),
    ("testo nuovo ASCII, graffe, dollari e ambienti bilanciati", _t_ascii_graffe),
    ("riferimenti a etichette note; tre etichette nuove (eq:grid, eq:prop2p, eq:fap)", _t_etichette),
    ("Prop. 2: padding proporzionale, coordinate identiche a 1e-9", _t_prop2),
    ("Prop. 2': affinita', punto fisso N/2, limite raggiunto dagli estremi", _t_prop2p),
    ("Lemma 3: (i) potenza, (ii) f -> c f, (iii) minimax unico e non peggiore dei minimi quadrati", _t_lemma3),
    ("convenzione: F_AP = pendenza di ln f su ln r = r f'/f", _t_convenzione),
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

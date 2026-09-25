#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_revisione_24set_d.py -- quarta passata documentaria del 24 settembre 2026.

Porta nei documenti il §5 scritto e cinque cose trovate scrivendolo:
  * checklist rev. 3.37 -> 3.38: blocco del §5 nella «Struttura», rimandi al Paper 1 e a M26 del §5,
    4.3c scritta, lo «0.2 %» della frazione indipendente (3.2b e 3.3 (d)) e Z-bib annotati;
  * stato dalla 21a alla 22a revisione: paragrafo, righe del par. 0, «convessa» -> concava (par. 4),
    cella v1 SGC di mediana(max delta)/DESI, «ventiquattro esiti indipendenti», Z-bib, tre voci
    aperte nuove, due strumenti nel par. 9;
  * modifiche_paper1.md: P1-11, cella v1 SGC; una riga nel registro delle modifiche.

Ogni numero dei testi nuovi si RICALCOLA dai registri (ledger, d2_v2, item15a_g13, fig_F1) e ogni
numero del §5 derivato da quei registri deve comparire nel manoscritto con la cifra quotata: se uno
non torna, nulla si scrive. I tre documenti devono essere quelli lasciati dalla passata c: si
confrontano con le uscite della sua ricevuta. Nessun record nuovo nel ledger: il protocollo non cambia.

Sequenza: selftest -> dry-run -> apply -> verify. Comandi dalla radice del repository.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

J = os.path.join
P2 = J("papers", "paper2")
DOC = {
    "chk": J(P2, "checklist_paper2.md"),
    "sta": J(P2, "paper2_stato.md"),
    "mod": J(P2, "modifiche_paper1.md"),
}
REG = {
    "ledger": J("src", "paper2_v1_amendments.jsonl"),
    "i15N": J("results", "paper2", "item15a_g13_NGC.jsonl"),
    "i15S": J("results", "paper2", "item15a_g13_SGC.jsonl"),
    "tex": J(P2, "MNRAS", "paper2_mnras.tex"),
    "bib": J(P2, "MNRAS", "paper2.bib"),
    "f1py": J("src", "paper2_fig_F1.py"),
}
# Ancorati per valore, non per sha (gli sha non sono noti qui): i campi letti devono dare i numeri.
D2 = {"NGC": J("results", "paper2", "d2_v2_NGC.json"), "SGC": J("results", "paper2", "d2_v2_SGC.json")}
FIGREG = J("results", "paper2", "fig_F1.jsonl")
FIGPDF = J(P2, "MNRAS", "figures", "F1_anisotropic_residual.pdf")
FIG_PREFISSO = "91e31bd60a9e"          # stampato dal run del 24 set, sera
RICEVUTA_C = J("logs", "patch_revisione_24set_c.json")
RICEVUTA = J("logs", "patch_revisione_24set_d.json")
BACKUP = J("logs", "patch_revisione_24set_d_backup")

PRE = {
    DOC["chk"]: ("270326bbc42287a51b9a646de587f280db75e05ad75fc4858f13f06cb2dc5948", 292095),
    REG["ledger"]: ("fb70459fca476145a791407e3bd1f5bd82f0dbc04e3f3d250309930bcf3f20a5", 663194),
    REG["i15N"]: ("80ebc9f617762aa4626542e5f9462cd6943452499dee6eeb56553f1d91d201ba", 6236),
    REG["i15S"]: ("1c13a09619cf9fb23ad33efbc91e63901e9b9d5aba02f18505bd167e3429c339", 6288),
    REG["tex"]: ("fe2414d97c9fbb4e7fad516b9f6414c69b75ee86f6fca4fdeb9696920a9e25ae", 60399),
    REG["bib"]: ("8d1d4016e85beaa8e17098af7915c8e4bff8236504b80f93117e1c4fa05d9758", 12613),
    REG["f1py"]: ("23dbdb98d52726abba6ead04a3f9878682a3598194b02fde39d7507df9ac3b1e", 21795),
}

# Basi del deficit a k=0, bersagli del cancello a n = 2000 (budget 5.1, par. 0).
D_BASE = {"NGC": 7180.686, "SGC": 3590.9675}

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]
MESI_BREVI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
DATA_DECISIONI = datetime.date(2026, 9, 24)

# Attesi dei gettoni che entrano nei documenti, dichiarati prima di leggere il disco
# (misurati il 24 set sui registri caricati).
ATTESI = {
    "FI_NGC": "0.16", "FI_SGC": "2.4", "FI_NGC_MIN": "0.6955", "FI_NGC_MAX": "0.6966",
    "FI_SGC_MIN": "0.789", "FI_SGC_MAX": "0.809",
    "DIV_N_DIV": "60", "DIV_S_DIV": "28", "DIV_N_OLTRE": "23", "DIV_S_OLTRE": "14",
    "DIV_N_MEDIA": "−0.0085", "DIV_S_MEDIA": "+0.268",
    "DIV58_N": "23", "DIV58_S": "11", "BIAS58_N": "0.152", "BIAS58_S": "0.175",
    "DN_N": "−89.15 ± 1.25", "DN_S": "−56.49 ± 0.83", "PD_N": "1.24", "PD_S": "1.57",
}


class PatchError(Exception):
    pass


# ----------------------------------------------------------------------------- utilita'

def sha_file(p):
    h = hashlib.sha256()
    n = 0
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
            n += len(blk)
    return h.hexdigest(), n


def sha_testo(t):
    b = t.encode("utf-8")
    return hashlib.sha256(b).hexdigest(), len(b)


def leggi(p):
    with open(p, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def eol_di(t):
    """Terminatore del testo; errore se misto."""
    if "\r\n" in t:
        if t.count("\r\n") != t.count("\n") or t.count("\r") != t.count("\r\n"):
            raise PatchError("terminatori misti (CRLF e LF insieme)")
        return "\r\n"
    if "\r" in t:
        raise PatchError("CR isolato in un testo LF")
    return "\n"


def data_it(d):
    return "%d %s %d" % (d.day, MESI[d.month - 1], d.year)


def migliaia(n):
    return "{:,}".format(n).replace(",", " ")


def meno(s):
    """Segno meno tipografico nei documenti; il tex usa il trattino ASCII."""
    return s.replace("-", "−")


def riempi(tpl, tok):
    out = tpl
    for k, v in tok.items():
        out = out.replace("@%s@" % k, v)
    resto = re.findall(r"@[A-Z0-9_]+@", out)
    if resto:
        raise PatchError("token non sostituiti: %s" % sorted(set(resto)))
    return out


def normalizza(t):
    return re.sub(r"\s+", " ", t)


# ----------------------------------------------------------------------------- numeri dai registri

def _jsonl(testo, cosa):
    out = []
    for i, riga in enumerate(testo.splitlines(), 1):
        if riga.strip():
            try:
                out.append(json.loads(riga))
            except Exception as e:
                raise PatchError("%s, riga %d illeggibile: %s" % (cosa, i, e))
    return out


def trova_chiave(obj, chiave):
    """Tutti i valori di una chiave a qualunque profondita'."""
    trov = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == chiave:
                trov.append(v)
            trov += trova_chiave(v, chiave)
    elif isinstance(obj, list):
        for v in obj:
            trov += trova_chiave(v, chiave)
    return trov


def unico(obj, chiave, cosa):
    v = trova_chiave(obj, chiave)
    if len(v) != 1:
        raise PatchError("%s: la chiave %r compare %d volte (attesa 1)" % (cosa, chiave, len(v)))
    if not isinstance(v[0], (int, float)):
        raise PatchError("%s: %r non e' un numero (%r)" % (cosa, chiave, v[0]))
    return float(v[0])


def _rec(led, n):
    if len(led) < n:
        raise PatchError("ledger: %d record, serve il %d" % (len(led), n))
    return led[n - 1]["new_value"]


def _frazione(testo, cosa):
    rec = [r for r in _jsonl(testo, cosa) if r.get("gauge") == "amend13"]
    fr = {r["point"]: float(r["independent_fraction"]) for r in rec}
    if len(fr) != len(rec) or len(rec) != 11 or "FID" not in fr:
        raise PatchError("%s: attesi undici punti amend13 col fiduciale, trovati %d" % (cosa, len(rec)))
    lo, hi = min(fr.values()), max(fr.values())
    return lo, hi, 100.0 * (hi - lo) / fr["FID"]


def numeri(t_ledger, t_d2, t_i15N, t_i15S):
    """Gettoni per i documenti e controlli sul tex; tutto dai registri."""
    led = _jsonl(t_ledger, "ledger")
    r50, r54, r57, r58, r59, r78 = (_rec(led, k) for k in (50, 54, 57, 58, 59, 78))
    tok, chk = {}, []

    # frazione indipendente (item15a_g13, gauge amend13), escursione relativa al fiduciale
    lo, hi, rel = _frazione(t_i15N, "item15a_g13_NGC")
    tok["FI_NGC_MIN"], tok["FI_NGC_MAX"], tok["FI_NGC"] = "%.4f" % lo, "%.4f" % hi, "%.2f" % rel
    lo, hi, rel = _frazione(t_i15S, "item15a_g13_SGC")
    tok["FI_SGC_MIN"], tok["FI_SGC_MAX"], tok["FI_SGC"] = "%.3f" % lo, "%.3f" % hi, "%.1f" % rel
    chk += ["from %s to %s in NGC" % (tok["FI_NGC_MIN"], tok["FI_NGC_MAX"]),
            "a relative excursion of %s per cent" % tok["FI_NGC"],
            "from %s to %s in SGC, %s per cent" % (tok["FI_SGC_MIN"], tok["FI_SGC_MAX"], tok["FI_SGC"])]

    # divergenze fra catene: record 78 (voce D) e record 58
    d78 = r78["D_7_12_trentaquattro_volte"]
    tok["DIV_N_DIV"], tok["DIV_S_DIV"] = str(d78["NGC"]["diversi"]), str(d78["SGC"]["diversi"])
    tok["DIV_N_OLTRE"], tok["DIV_S_OLTRE"] = str(d78["NGC"]["oltre_3"]), str(d78["SGC"]["oltre_3"])
    for reg, t in (("NGC", "DIV_N_MEDIA"), ("SGC", "DIV_S_MEDIA")):
        if abs(d78[reg]["somma"] / 2000.0 - d78[reg]["media"]) > 1e-12:
            raise PatchError("record 78 %s: media diversa da somma/2000" % reg)
    tok["DIV_N_MEDIA"] = meno("%.4f" % d78["NGC"]["media"])
    tok["DIV_S_MEDIA"] = "%+.3f" % d78["SGC"]["media"]
    c58 = r58["v_what_the_gates_caught_and_what_they_cost"]["what_the_diagnostics_then_measured"]
    tok["DIV58_N"], tok["DIV58_S"] = str(c58["cross_chain_divergence_NGC"]["n"]), str(c58["cross_chain_divergence_SGC"]["n"])
    tok["BIAS58_N"] = "%.3f" % c58["cross_chain_divergence_NGC"]["bias_in_sem"]
    tok["BIAS58_S"] = "%.3f" % c58["cross_chain_divergence_SGC"]["bias_in_sem"]
    chk += ["%s (NGC) and %s (SGC) of the 2000 counts differ, %s and %s of them"
            % (tok["DIV_N_DIV"], tok["DIV_S_DIV"], tok["DIV_N_OLTRE"], tok["DIV_S_OLTRE"]),
            "$%.4f$ and $%s$" % (d78["NGC"]["media"], tok["DIV_S_MEDIA"])]

    # d2_v2: Delta N_H1 a k=0, per cento di N e di D
    dn = {}
    for reg in ("NGC", "SGC"):
        obj = t_d2[reg]
        m, s, r = (unico(obj, k, "d2_v2_" + reg) for k in ("dN_medio", "dN_sem", "dN_su_N_medio"))
        dn[reg] = (m, s, r)
    tok["DN_N"] = meno("%.2f ± %.2f" % dn["NGC"][:2])
    tok["DN_S"] = meno("%.2f ± %.2f" % dn["SGC"][:2])
    tok["PD_N"] = "%.2f" % (100 * abs(dn["NGC"][0]) / D_BASE["NGC"])
    tok["PD_S"] = "%.2f" % (100 * abs(dn["SGC"][0]) / D_BASE["SGC"])
    chk += [r"$\Delta\NH = %.2f \pm %.2f$ in NGC and $%.2f \pm %.2f$ in SGC" % (dn["NGC"][:2] + dn["SGC"][:2]),
            "%.2f and %.2f per cent of $\\NH$" % (100 * abs(dn["NGC"][2]), 100 * abs(dn["SGC"][2])),
            "%s and %s per cent of the deficit" % (tok["PD_N"], tok["PD_S"])]

    # voxel patologici: v1 (record 54), v2 e appaiato NGC (record 58)
    v1 = r54["ii_measured_v1_values_n_2000"]
    ii = r58["ii_five_rules_of_six_and_all_five_fail"]
    iii = r58["iii_the_pairing_earned_the_twenty_three_extra_hours"]
    chk += ["%.0f per realization in NGC and %.0f in SGC" % (v1["NGC"]["n_pathological"]["mock_mean"],
                                                            v1["SGC"]["n_pathological"]["mock_mean"]),
            "On v2 it is %.0f and %.0f" % (ii["4.2c_pathological_voxels"]["NGC"]["mean"],
                                           ii["4.2c_pathological_voxels"]["SGC"]["mean"]),
            r"removes $%.2f \pm %.2f$" % (abs(iii["n_pat_NGC"]["delta"]), iii["n_pat_NGC"]["sem_paired"])]

    # curtosi appaiata (record 58, iii)
    k = iii["kurtosis_NGC"]
    chk.append(r"moves by $%.4f$ with a paired error of $%d\times10^{-5}$, against $%.3f$"
               % (k["delta"], round(k["sem_paired"] / 1e-5), k["sem_unpaired"]))

    # Box-Cox (record 50, 57)
    s1 = r57["ii_s_v1_reproduced_exactly_in_NGC_and_measured_for_the_first_time_in_SGC"]
    s2 = r57["iv_the_outcome_is_FAILURE_in_both_hemispheres"]
    sp = r57["v_the_shift_is_measured_with_the_PAIRED_denominator"]
    vi = r57["vi_the_non_monotonicity_in_eps_is_confirmed_independently_and_survives"]
    nm = r50["iii_box_cox_84_percent_of_it_is_the_data_side"]["and_the_mock_side_is_NOT_MONOTONIC_in_eps"]
    n_v1 = [float(x) for x in re.findall(r"([+-]\d+\.\d+) \+- ", nm)[:3]]
    if len(n_v1) != 3:
        raise PatchError("record 50, iii: lato mock NGC v1 non letto")
    f3 = lambda xs: "$%+.0f$, $%+.0f$ and $%+.0f$" % tuple(xs)
    chk += [r"$s = %.1f \pm %.1f$ in NGC" % (s1["NGC"]["s"], s1["NGC"]["sem_paired"]),
            r"and $%.1f \pm %.1f$ in SGC" % (s1["SGC"]["s"], s1["SGC"]["sem_paired"]),
            r"$s = %.1f \pm %.1f$ and $%.1f \pm %.1f$" % (s2["NGC"]["s_v2"], s2["NGC"]["sem"],
                                                        s2["SGC"]["s_v2"], s2["SGC"]["sem"]),
            r"$%.1f \pm %.1f$ and $%.1f \pm %.1f$" % (sp["NGC"]["delta_s"], sp["NGC"]["sem_paired"],
                                                    sp["SGC"]["delta_s"], sp["SGC"]["sem_paired"]),
            f3(n_v1) + " generators", f3(vi["SGC_v1"]) + " in SGC",
            "(" + f3(vi["NGC_v2"]) + "; " + f3(vi["SGC_v2"]) + ")"]

    # massimo di delta (record 50, 58)
    if "27.80" not in r50["ii_max_delta_an_ensemble_extremum"]["replaced_by"]:
        raise PatchError("record 50: il 27.80 su v1 non c'e'")
    md = ii["4.2b-4_maximum_of_delta"]
    chk += ["from 27.80 to %.2f" % md["NGC"]["median_over_desi"], "is %.2f times" % md["SGC"]["median_over_desi"]]

    # prominenza (record 58, curvatura; record 59, esito)
    cv = r58["iv_4_3b_the_threshold_is_recalibrated_and_DECLARED_HERE"]["the_curvature_term_is_NOT_small_on_real_data"]
    p = r59["ii_4_3b_fails_in_both_hemispheres"]
    g = r59["iii_the_prominence_does_not_move_and_if_anything_grows"]
    chk += ["%.2f percentage points in NGC and %.2f in SGC, %.0f and %.0f per cent"
            % (cv["NGC"]["P_curvature_pp"], cv["SGC"]["P_curvature_pp"],
               cv["NGC"]["percent_of_uncorrected_P"], cv["SGC"]["percent_of_uncorrected_P"]),
            "On v1, $P = %.2f$ and %.2f" % (p["NGC"]["P_v1_pp"], p["SGC"]["P_v1_pp"]),
            "two thirds, %.2f and %.2f" % (p["NGC"]["failure_above_pp"], p["SGC"]["failure_above_pp"]),
            "On v2, $P = %.2f$ and %.2f, %.0f and %.0f standard errors"
            % (p["NGC"]["P_v2_pp"], p["SGC"]["P_v2_pp"], p["NGC"]["sigma_from_zero"], p["SGC"]["sigma_from_zero"]),
            "by %.3f and %.3f percentage points, with errors of %.3f and %.3f"
            % (g["NGC"]["delta_pp"], g["SGC"]["delta_pp"], g["NGC"]["sem_in_quadrature"], g["SGC"]["sem_in_quadrature"])]

    # la parola del record 50 che lo stato riprende
    if "convex in N" not in r50["vi_4_3b_the_statistic_is_named"]["a_curvature_term_belongs_to_the_DEFINITION"]:
        raise PatchError("record 50, vi: «convex in N» non c'e'")

    diff = [k for k in ATTESI if tok.get(k) != ATTESI[k]]
    if diff:
        raise PatchError("numeri ricalcolati diversi dagli attesi in %r: %r" % (diff, {k: tok.get(k) for k in diff}))
    return tok, chk


def controlla_tex(tex, chk):
    t = normalizza(tex)
    return [c for c in chk if normalizza(c) not in t]


def figura(t_reg, sha_pdf, sha_f1py):
    recs = _jsonl(t_reg, "fig_F1.jsonl")
    if not recs:
        raise PatchError("fig_F1.jsonl vuoto")
    ult = recs[-1]
    if ult.get("pdf", {}).get(FIGPDF) != sha_pdf:
        raise PatchError("l'ultimo record di fig_F1.jsonl non descrive la figura su disco (%s)" % sha_pdf[:12])
    if not sha_pdf.startswith(FIG_PREFISSO):
        raise PatchError("figura %s, attesa %s… (run del 24 set)" % (sha_pdf[:12], FIG_PREFISSO))
    if ult.get("inputs", {}).get(REG["f1py"]) != sha_f1py:
        raise PatchError("l'ultimo record di fig_F1.jsonl viene da un altro paper2_fig_F1.py")
    return {"FIG12": sha_pdf[:12], "NREC_F1": str(len(recs))}


# ----------------------------------------------------------------------------- testi: checklist (LF)

O_C1 = "\n### rev. 3.37 — 24 settembre 2026 — **le decisioni del §4 nei documenti"
T_C1 = (
    "\n### rev. 3.38 — @DATA@ — **il §5 scritto, e cinque cose trovate scrivendolo.** §5.1–§5.3 nel"
    " manoscritto (`paper2_mnras.tex` `@TEX8@…`, `paper2.bib` `@BIB8@…`); @NTEX@ numeri del §5 e del §4.2 riscontrati"
    " dal patcher su ledger, `d2_v2` e `item15a_g13`; testi decisi 8/8 invariati. F1 rifatta (etichette"
    " fuori dal padding). Bibliografia +2, verificate alla fonte. Trovati: lo «0.2 %» della frazione"
    " indipendente è NGC (SGC @FI_SGC@ %); «ventiquattro esiti indipendenti» non regge alla collinearità;"
    " *D* è concava, non convessa, nel conteggio dei mock; la cella v1 SGC di mediana(max δ)/DESI portava"
    " il valore NGC; le divergenze fra catene in SGC sono @DIV_S_OLTRE@ oltre ±3 nel record 78 e"
    " @DIV58_S@ nel 58. Nessun record nuovo: il protocollo non cambia."
    + O_C1
)

O_C2 = "      come il criterio del limite pratico.\n"
T_C2 = O_C2 + (
    "      **✦ rev. 3.38:** lo «0.2%» è l'escursione di **NGC** (da @FI_NGC_MIN@ a @FI_NGC_MAX@, @FI_NGC@ %\n"
    "      del fiduciale); in **SGC** la frazione va da @FI_SGC_MIN@ a @FI_SGC_MAX@, **@FI_SGC@ %**\n"
    "      (`item15a_g13_{NGC,SGC}.jsonl`, gauge `amend13`). Le repliche restano costanti, 15 e 10, e la\n"
    "      conclusione non cambia; il manoscritto (§4.2) porta entrambi i valori.\n"
)

O_C3 = "| (d) | tiling | **0** — repliche costanti, escursione 0.2% | verificato |"
T_C3 = ("| (d) | tiling | **0** — repliche costanti, escursione 0.2% *(NGC; SGC @FI_SGC@ %, rev. 3.38)* |"
        " verificato |")

O_C4 = ("- [ ] **◆ 4.3c** Il risultato è pubblicabile e la sezione va scritta: **la\n"
        "      ripesatura FKP non spiega il deficit**, su ventiquattro esiti indipendenti.\n")
T_C4 = ("- [x] **◆ 4.3c** Il risultato è pubblicabile e la sezione va scritta: **la\n"
        "      ripesatura FKP non spiega il deficit**, su ventiquattro esiti indipendenti.\n"
        "      **✦ rev. 3.38 — SCRITTA**, §5 del manoscritto. «Indipendenti» non regge: le cinque regole a un\n"
        "      punto coprono tre direzioni (Z-collinearità, Fase 7 punto 7), e il manoscritto scrive «none\n"
        "      falls in its zone of indecision», non un conteggio di esiti indipendenti.\n")

O_C5 = ("| struttura, §5.3 | tensione §7.2/§8.1 | Paper 1 §7.2 e §8.1, toccati da P1-1, P1-4, P1-11 e P1-10 |"
        " si scrive sul Paper 1 corretto |\n")
T_C5 = O_C5 + (
    "| §5.1 (rev. 3.38) | Δ*N*_H1 su 2000 realizzazioni, «quoted in Paper 1 (section 7.2)» | Paper 1 §7.2 |"
    " **P1-9**; M26 §5.3 e table 1 (−78.0 ± 8.0) citati come concordi, a 1.4σ |\n"
    "| §5.2 (rev. 3.38) | ~4000 voxel, 1.3 % della maschera, fattore 315, un voxel dal bordo | Paper 1 §7.2 |"
    " **P1-11** (numeri conservati, attribuzione caduta); M26 §4.1 citato come concorde |\n"
    "| §5.2 (rev. 3.38) | Box–Cox, *T*_ε e 35 446 → 35 262 | M26 §4.1 e table 1 | nessuna voce: M26"
    " riprodotto, non smentito |\n"
    "| §5.3 (rev. 3.38) | 99.4 % entro due voxel; tagli al 1, 5 e 10 percentile, 100.1 / 100.1 / 98.7 % |"
    " Paper 1 §7.2 | **P1-10**, **P1-11** (numeri conservati) |\n"
    "| §5.3 (rev. 3.38) | il massimo a *k* = 1 è geometrico | Paper 1 §8.1 | **P1-10** |\n"
    "| §5.3 (rev. 3.38) | bordo degradato: 1.65 % contro 0.21–0.27 % (tre realizzazioni), 52 voxel vuoti,"
    " copertura 0.08 contro 16.6 | Paper 1 §9 | **P1-7**, **P1-6** |\n"
    "| — (rev. 3.38) | residuo oltre i due punti su v2 | Paper 1 §6 | **non citato**: P1-5 è una misura"
    " senza correzione, e il vincolo del 24 non lo ammette |\n"
    "| — (rev. 3.38) | *D*(*k*) della Tab. 9 | Paper 1 §8.1 | **non citata**: porta i valori a *n* = 200"
    " (stato §0, «deficit del ladder contro Tab. 9»), il §5.3 quelli a *n* = 2000 del ramo unitario; le"
    " due serie differiscono nell'ultima cifra (25.4 contro 25.46, 27.1 contro 27.19) |\n"
)

O_C6 = ("- **Z-bib**, in `cauchy.bib`: `DESI2025DR1` → AJ 171, 285 (2026); data di accesso a `gudhi`;\n"
        "  aggiungere M26 (`stag1730`) e il Paper 1, con la forma della citazione da decidere;\n")
T_C6 = O_C6 + (
    "  **✦ rev. 3.38:** fatto in `paper2.bib` per DESI DR1, M26 e Paper 1 («MNRAS, submitted»); il\n"
    "  protocollo è fuori dalla bibliografia e sta solo nella Data Availability (24 set); aggiunte,\n"
    "  verificate alla fonte, Feldman, Kaiser & Peacock (1994; arXiv:astro-ph/9304022) e Box & Cox (1964;\n"
    "  pagina dell'editore); tolta una graffa isolata dopo `Paper1`. Resta la data di accesso a GUDHI.\n"
)

O_C7 = ("  *k* = 2, 3 (cade a *k* = 3). Con D-7 SGC, nel gruppo 3-bis di `paper2_5_5_smentite.md`.\n"
        "\n1. Introduzione:")
T_C7 = (
    "  *k* = 2, 3 (cade a *k* = 3). Con D-7 SGC, nel gruppo 3-bis di `paper2_5_5_smentite.md`.\n"
    "\n"
    "**✦ rev. 3.38 — il §5, scritto il 24 set.** `paper2_mnras.tex` `@TEX8@…` (@TEXB@ byte), `paper2.bib`\n"
    "`@BIB8@…` (@BIBB@); 24 note di stesura, 8 pagine, zero errori; in modalità finale restano solo le\n"
    "note e le 8 figure mancanti. Testi decisi 8/8 identici. Il patcher della rev. 3.38 riscontra\n"
    "@NTEX@ numeri del manoscritto, del §5 sul ledger (record 50, 54, 57, 58, 59, 78) e su\n"
    "`d2_v2_{NGC,SGC}.json`, del §4.2 su `item15a_g13_{NGC,SGC}.jsonl`.\n"
    "\n"
    "- **§5.1.** Costruzione del v2 (*w*_FKP, niente completezza), pesi medi, invarianza di δ, due rami\n"
    "  per realizzazione, cancelli; Δ*N*_H1 @DN_N@ / @DN_S@ (@PD_N@ / @PD_S@ % di *D* a *k* = 0),\n"
    "  concorde con M26 a 1.4σ, riportato e non sottratto. **Divergenze fra catene dal record 78**:\n"
    "  @DIV_N_DIV@ e @DIV_S_DIV@ conteggi diversi, @DIV_N_OLTRE@ e @DIV_S_OLTRE@ oltre ±3, media\n"
    "  @DIV_N_MEDIA@ e @DIV_S_MEDIA@. Il record 58 ne dava @DIV58_N@ e **@DIV58_S@**, con bias @BIAS58_N@ e\n"
    "  @BIAS58_S@ SEM: in SGC @DIV_S_OLTRE@ contro @DIV58_S@ (**Z-divergenze**).\n"
    "- **§5.2.** Sei regole in vigore e la larghezza di ν ritirata; voxel patologici e Box–Cox, col lato\n"
    "  mock non monotono in ε che sopravvive alla ripesatura in entrambi gli emisferi (record 57, vi). Il\n"
    "  «same values to two digits» dello stesso record vale per SGC, non per NGC, dove −183 diventa −190.\n"
    "  La tabella delle soglie va nell'appendice B (nota nel tex). Un numero senza registro letto:\n"
    "  l'appaiato SGC dei voxel patologici, −16.45 ± 0.32, che sta in P1-11 e nella 4.2c e non nel\n"
    "  ledger (**Z-nPat-SGC**).\n"
    "- **§5.3.** Scala *k* = 0–3 sul ramo unitario, prominenza, massimo geometrico; bordo degradato come\n"
    "  candidato, non verificato. Il testo dice «nonlinear»: il record 50 e lo stato (§4) dicono *D*\n"
    "  «convessa in *N*», ma nel conteggio dei mock *D* = 1 − *N*_DESI/*N* è **concava**\n"
    "  (d²*D*/d*N*² = −2*N*_DESI/*N*³ < 0), e il termine di curvatura positivo lo conferma. Il record 50 non\n"
    "  si riscrive; lo stato è annotato.\n"
    "- **Mediana(max δ)/DESI in SGC su v1**: il §7-quater dello stato e P1-11 portano 27.80, che è il\n"
    "  valore di NGC (record 50: «27.80 on v1», con 125 al denominatore); il v1 SGC non è in un registro\n"
    "  letto. Corretta a «—» nei due documenti; il manoscritto non la usa.\n"
    "- **F1** rifatta: etichette di B2 e C4 fuori dalle linee di padding. `paper2_fig_F1.py` `@F18@…`,\n"
    "  selftest 10/10; figura `@FIG12@…`; `results/paper2/fig_F1.jsonl` a @NREC_F1@ record, registro nato\n"
    "  il 24 set: il censimento dei registri va rieseguito (**Z-censimento-fig**).\n"
    "- **`papers/` è fuori dal versionamento dal 28 agosto** (record 70 e 72): il commit `d14dded` porta\n"
    "  script e registro di F1, non manoscritto, bibliografia e figura. Previsto, non un difetto: il\n"
    "  manoscritto si ancora come i documenti, per sha.\n"
    "\n1. Introduzione:"
)

# ----------------------------------------------------------------------------- testi: stato (CRLF sul disco)

O_S1 = "aggiornato **24 settembre 2026**, ventunesima revisione"
T_S1 = "aggiornato **@DATA@**, ventiduesima revisione"

O_S2 = "`d44bd6e9…`, `paper2.bib` `3d474399…` · ledger invariato a 78 record: nessun record nuovo.\n"
T_S2 = O_S2 + (
    "\n"
    "**Al 24 settembre, sera (ventiduesima revisione):** **§5 scritto** (5.1–5.3), @NTEX@ numeri del\n"
    "manoscritto riscontrati dal patcher sul ledger, su `d2_v2` e su `item15a_g13` · `paper2_mnras.tex` `@TEX8@…`, `paper2.bib`\n"
    "`@BIB8@…` (+ Feldman, Kaiser & Peacock 1994; + Box & Cox 1964), 24 note, 8 pagine · F1 rifatta,\n"
    "figura `@FIG12@…` · cinque correzioni ai documenti, nessuna al protocollo: lo «0.2 %» della frazione\n"
    "indipendente è NGC, SGC @FI_SGC@ % (checklist 3.2b e 3.3 (d)); «ventiquattro esiti indipendenti» non\n"
    "regge alla collinearità (§7-quater, §8, checklist 4.3c); *D* è concava nel conteggio dei mock, non\n"
    "convessa (§4); la cella v1 SGC di mediana(max δ)/DESI portava il valore NGC (§7-quater e P1-11); le\n"
    "divergenze fra catene in SGC sono @DIV_S_OLTRE@ oltre ±3 nel record 78 e @DIV58_S@ nel 58 (Z-divergenze) ·\n"
    "`papers/` fuori dal versionamento dal 28 agosto: il commit `d14dded` porta solo script e registro di F1\n"
    "· ledger invariato a 78 record.\n"
)

O_S3 = "| (24 set) `fa_sha256` di `forma_lato_mock_v3.json` | è lo sha di `src/paper2_fase3_analisi.py` |\n"
T_S3 = O_S3 + (
    "| (24 set, sera) numeri del §5 e del §4.2 contro ledger, `d2_v2` e `item15a_g13` | **@NTEX@/@NTEX@** presenti nel"
    " tex con la cifra quotata |\n"
    "| (24 set, sera) testi decisi dopo il §5 | **8/8 identici** alla versione di prima |\n"
    "| (24 set, sera) divergenze fra catene, record 58 contro 78 | NGC @DIV58_N@ e @DIV_N_OLTRE@ oltre ±3;"
    " SGC **@DIV58_S@ contro @DIV_S_OLTRE@**: da riconciliare |\n"
    "| (24 set, sera) frazione indipendente, escursione relativa al fiduciale | NGC @FI_NGC@ %, SGC"
    " **@FI_SGC@ %**: lo «0.2 %» della checklist è NGC |\n"
    "| (24 set, sera) mediana(max δ)/DESI su v1 in SGC | **non in un registro letto**: il 27.80 è NGC |\n"
)

O_S4 = "è convessa in *N*: una rampa perfettamente lineare in *N*_H1"
T_S4 = ("è convessa in *N* *(sic, dal record 50: nel conteggio dei mock è **concava**, d²*D*/d*N*² ="
        " −2*N*_DESI/*N*³ < 0; 22ª revisione)*: una rampa perfettamente lineare in *N*_H1")

O_S5 = "| mediana(max δ)/DESI, SGC | 27.80 | **40.32** |"
T_S5 = ("| mediana(max δ)/DESI, SGC | — *(qui c'era 27.80, il valore NGC; il v1 SGC non è in un registro"
        " letto — 22ª rev.)* | **40.32** |")

O_S6 = ("**Ventiquattro esiti indipendenti** — sei regole, due emisferi, due rami appaiati — e nessuno\n"
        "cade nella zona che non decide, nessuno incontra la propria condizione di invalidazione.\n")
T_S6 = O_S6 + (
    "*(22ª revisione: «indipendenti» non regge — le cinque regole a un punto coprono tre direzioni,\n"
    "Z-collinearità. Il manoscritto scrive «none falls in its zone of indecision».)*\n"
)

O_S7 = ("| **Z-bib** | `cauchy.bib` da aggiornare | scrittura | DESI DR1 → AJ 171, 285 (2026); accesso a"
        " GUDHI; M26 `stag1730`; Paper 1, forma della citazione da decidere |")
T_S7 = ("| **Z-bib** | bibliografia del Paper 2 | scrittura | *(22ª rev.)* in `paper2.bib`: DESI DR1 (AJ 171,"
        " 285), M26 `stag1730`, Paper 1 «MNRAS, submitted», Feldman, Kaiser & Peacock 1994, Box & Cox 1964,"
        " verificate alla fonte; il protocollo solo nella Data Availability. **Resta** la data di accesso a"
        " GUDHI, e l'arricchimento durante e alla fine della stesura |")

O_S8 = ("| **Z-rango-201** | «il rango resta 1/201 in ogni punto» (record 19) | scrittura | da verificare su"
        " `fase3_mock.jsonl` prima di citarlo; D-1 non lo usa |\n")
T_S8 = O_S8 + (
    "| **Z-divergenze** | il record 58 conta @DIV58_S@ divergenze fra catene in SGC (bias @BIAS58_S@ SEM),"
    " il record 78 @DIV_S_OLTRE@ oltre ±3 e @DIV_S_DIV@ in tutto | lettura | il §5.1 usa il 78 (due vie"
    " concordi); va capito quale soglia usasse il 58 prima di citarlo altrove |\n"
    "| **Z-censimento-fig** | `results/paper2/fig_F1.jsonl` è un registro nuovo | censimento | rieseguire il"
    " censimento dei registri; l'esito non si prevede |\n"
    "| **Z-nPat-SGC** | l'appaiato SGC dei voxel patologici, −16.45 ± 0.32, non è nel ledger | lettura |"
    " sta in P1-11 e nella 4.2c; il registro va nominato prima che il numero resti nel §5 |\n"
)

O_S9 = ("| `paper2_patch_revisione_24set_c.py` | checklist 3.37, questo documento alla 21ª, P1-13 punto 1,"
        " tre smentite nel 3-bis, nota sull'inventario; numeri ricalcolati da cinque registri e log |"
        " 11/11 |\n")
T_S9 = O_S9 + (
    "| `paper2_fig_F1.py` | figura F1, residuo anisotropo; dieci cancelli sui registri, etichette con"
    " ostacoli fissi (24 set) | 10/10 |\n"
    "| `paper2_patch_revisione_24set_d.py` | checklist 3.38, questo documento alla 22ª, P1-11; @NTEX@ numeri"
    " del §5 e del §4.2 riscontrati su ledger, `d2_v2` e `item15a_g13` | @NST@/@NST@ |\n"
)

# ----------------------------------------------------------------------------- testi: modifiche_paper1 (LF)

O_M1 = "| mediana(max δ)/DESI, SGC | 27.80 | **40.32** | verso 1 |"
T_M1 = ("| mediana(max δ)/DESI, SGC | — *(qui c'era 27.80, il valore NGC; il v1 SGC non è in un registro"
        " letto — 24 set, sera)* | **40.32** | verso 1 |")

O_M2 = "| data | cosa |\n|---|---|\n"
T_M2 = O_M2 + (
    "| @DATAB@, sera | P1-11: la cella v1 SGC di mediana(max δ)/DESI portava il valore NGC (27.80),"
    " corretta a «—». Il §5 del Paper 2 cita il Paper 1 solo nei §7.2, §8.1 e §9, dove toccano P1-6,"
    " P1-7, P1-9, P1-10 e P1-11; P1-5 non è citato. Nessuna voce cambia stato |\n"
)

EDITS = [
    ("chk", "C1 intestazione rev. 3.38", O_C1, T_C1),
    ("chk", "C2 voce 3.2b: frazione indipendente", O_C2, T_C2),
    ("chk", "C3 voce 3.3: riga (d)", O_C3, T_C3),
    ("chk", "C4 voce 4.3c scritta", O_C4, T_C4),
    ("chk", "C5 rimandi del par. 5", O_C5, T_C5),
    ("chk", "C6 Z-bib", O_C6, T_C6),
    ("chk", "C7 blocco del par. 5", O_C7, T_C7),
    ("sta", "S1 riga 2", O_S1, T_S1),
    ("sta", "S2 ventiduesima revisione", O_S2, T_S2),
    ("sta", "S3 righe del par. 0", O_S3, T_S3),
    ("sta", "S4 convessa -> concava (par. 4)", O_S4, T_S4),
    ("sta", "S5 cella v1 SGC (par. 7-quater)", O_S5, T_S5),
    ("sta", "S6 ventiquattro esiti indipendenti", O_S6, T_S6),
    ("sta", "S7 Z-bib", O_S7, T_S7),
    ("sta", "S8 voci aperte nuove", O_S8, T_S8),
    ("sta", "S9 strumenti nel par. 9", O_S9, T_S9),
    ("mod", "M1 P1-11 cella v1 SGC", O_M1, T_M1),
    ("mod", "M2 registro delle modifiche", O_M2, T_M2),
]


def postcondizioni(testi):
    attese = [
        ("chk", "### rev. 3.38 —", 1),
        ("chk", "**✦ rev. 3.38 — il §5, scritto il 24 set.**", 1),
        ("chk", "- [ ] **◆ 4.3c**", 0),
        ("chk", "| §5.3 (rev. 3.38) |", 3),
        ("sta", "ventiduesima revisione", 2),
        ("sta", "`paper2_patch_revisione_24set_d.py`", 1),
        ("sta", O_S1, 0),
        ("sta", O_S5, 0),
        ("sta", "| **Z-divergenze** |", 1),
        ("mod", O_M1, 0),
        ("mod", "P1-5 non è citato", 1),
    ]
    return ["%s: %r compare %d volte, attese %d" % (f, s, testi[f].count(s), k)
            for f, s, k in attese if testi[f].count(s) != k]


def costruisci(testi, tok):
    if "### rev. 3.38" in testi["chk"] or "ventiduesima revisione" in testi["sta"]:
        raise PatchError("passata gia' applicata (marcatori della rev. 3.38 o della 22a presenti)")
    out = dict(testi)
    eol = {k: eol_di(v) for k, v in out.items()}
    fatte = []
    for f, lab, old, new in EDITS:
        o = old.replace("\n", eol[f])
        nn = riempi(new, tok).replace("\n", eol[f])
        k = out[f].count(o)
        if k != 1:
            raise PatchError("%s: ancora trovata %d volte (attesa 1)" % (lab, k))
        out[f] = out[f].replace(o, nn)
        fatte.append(lab)
    for f in out:
        if eol_di(out[f]) != eol[f]:
            raise PatchError("%s: terminatore cambiato dalla patch" % f)
    falliti = postcondizioni(out)
    if falliti:
        raise PatchError("postcondizioni: " + "; ".join(falliti))
    return out, fatte


def scrivi_atomico(testi, backup_dir):
    os.makedirs(backup_dir, exist_ok=True)
    for p in testi:
        if os.path.exists(p):
            shutil.copy2(p, J(backup_dir, os.path.basename(p)))
    tmp = {}
    try:
        for p, t in testi.items():
            d = os.path.dirname(p) or "."
            fd, tp = tempfile.mkstemp(prefix=".tmp_patch_", dir=d)
            tmp[p] = tp
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
                fh.write(t)
                fh.flush()
                os.fsync(fh.fileno())
    except Exception:
        for tp in tmp.values():
            if os.path.exists(tp):
                os.remove(tp)
        raise
    fatti = []
    try:
        for p, tp in tmp.items():
            os.replace(tp, p)
            fatti.append(p)
    except Exception:
        for p in fatti:
            shutil.copy2(J(backup_dir, os.path.basename(p)), p)
        for tp in tmp.values():
            if os.path.exists(tp):
                os.remove(tp)
        raise


# ----------------------------------------------------------------------------- selftest

def _gettoni_finti():
    t = dict(ATTESI)
    t.update({"DATA": "24 settembre 2026", "DATAB": "24 set 2026", "TEX8": "a" * 8, "BIB8": "b" * 8,
              "TEXB": "1", "BIBB": "2", "F18": "c" * 8, "FIG12": "d" * 12, "NREC_F1": "2",
              "NTEX": "30", "NST": "12"})
    return t


def _fixtures():
    out = {}
    for chiave in DOC:
        parti = ["# fixture " + chiave, "x"] + [old for f, lab, old, new in EDITS if f == chiave]
        t = "\n".join(parti) + "\nfine\n"
        out[chiave] = t.replace("\n", "\r\n") if chiave == "sta" else t
    return out


def _ledger_sintetico(delta_md=0.0):
    rec = [{"new_value": {}} for _ in range(78)]
    rec[49]["new_value"] = {
        "ii_max_delta_an_ensemble_extremum": {"replaced_by": "Reported always: ... which is 27.80 on v1."},
        "iii_box_cox_84_percent_of_it_is_the_data_side": {
            "and_the_mock_side_is_NOT_MONOTONIC_in_eps": "+129.00 +- 4.19 at eps=0.25, +124.52 +- 7.08 at eps=0.5,"
                                                          " then -183.32 +- 11.12 at eps=1."},
        "vi_4_3b_the_statistic_is_named": {"a_curvature_term_belongs_to_the_DEFINITION": "D is convex in N, so"}}
    rec[53]["new_value"] = {"ii_measured_v1_values_n_2000": {
        "NGC": {"n_pathological": {"mock_mean": 4048.21}}, "SGC": {"n_pathological": {"mock_mean": 2811.56}}}}
    rec[56]["new_value"] = {
        "ii_s_v1_reproduced_exactly_in_NGC_and_measured_for_the_first_time_in_SGC": {
            "NGC": {"s": -183.32, "sem_paired": 11.124}, "SGC": {"s": -109.32, "sem_paired": 9.4125}},
        "iv_the_outcome_is_FAILURE_in_both_hemispheres": {
            "NGC": {"s_v2": -190.02, "sem": 11.488}, "SGC": {"s_v2": -109.62, "sem": 9.2368}},
        "v_the_shift_is_measured_with_the_PAIRED_denominator": {
            "NGC": {"delta_s": -6.7, "sem_paired": 6.14}, "SGC": {"delta_s": -0.3, "sem_paired": 5.13}},
        "vi_the_non_monotonicity_in_eps_is_confirmed_independently_and_survives": {
            "SGC_v1": [144.0, 136.52, -109.32], "NGC_v2": [125.62, 122.1, -190.02],
            "SGC_v2": [142.94, 140.02, -109.62]}}
    rec[57]["new_value"] = {
        "ii_five_rules_of_six_and_all_five_fail": {
            "4.2c_pathological_voxels": {"NGC": {"mean": 4021.077}, "SGC": {"mean": 2795.108}},
            "4.2b-4_maximum_of_delta": {"NGC": {"median_over_desi": 28.469 + delta_md},
                                        "SGC": {"median_over_desi": 40.3185}}},
        "iii_the_pairing_earned_the_twenty_three_extra_hours": {
            "kurtosis_NGC": {"delta": -0.012872, "sem_paired": 5.848e-05, "sem_unpaired": 0.01445},
            "n_pat_NGC": {"delta": -27.092, "sem_paired": 0.41126}},
        "iv_4_3b_the_threshold_is_recalibrated_and_DECLARED_HERE": {"the_curvature_term_is_NOT_small_on_real_data": {
            "NGC": {"P_curvature_pp": 1.1912, "percent_of_uncorrected_P": 23.79},
            "SGC": {"P_curvature_pp": 3.5882, "percent_of_uncorrected_P": 47.46}}},
        "v_what_the_gates_caught_and_what_they_cost": {"what_the_diagnostics_then_measured": {
            "cross_chain_divergence_NGC": {"n": 23, "bias_in_sem": 0.152},
            "cross_chain_divergence_SGC": {"n": 11, "bias_in_sem": 0.175}}}}
    rec[58]["new_value"] = {
        "ii_4_3b_fails_in_both_hemispheres": {
            "NGC": {"P_v1_pp": 3.81608, "P_v2_pp": 3.84452, "failure_above_pp": 2.54405, "sigma_from_zero": 678.03},
            "SGC": {"P_v1_pp": 3.97164, "P_v2_pp": 3.98775, "failure_above_pp": 2.64776, "sigma_from_zero": 554.26}},
        "iii_the_prominence_does_not_move_and_if_anything_grows": {
            "NGC": {"delta_pp": 0.028438, "sem_in_quadrature": 0.00794},
            "SGC": {"delta_pp": 0.016114, "sem_in_quadrature": 0.010121}}}
    rec[77]["new_value"] = {"D_7_12_trentaquattro_volte": {
        "NGC": {"diversi": 60, "oltre_3": 23, "somma": -17, "media": -0.0085},
        "SGC": {"diversi": 28, "oltre_3": 14, "somma": 536, "media": 0.268}}}
    return "\n".join(json.dumps(r) for r in rec) + "\n"


def _d2_sintetici():
    return {"NGC": {"schema": "paper2_d2_v2_v1", "n": 2000, "dN_medio": -89.147, "dN_sem": 1.2475,
                    "dN_su_N_medio": -0.0025129},
            "SGC": {"schema": "paper2_d2_v2_v1", "n": 2000, "dN_medio": -56.494, "dN_sem": 0.8312,
                    "dN_su_N_medio": -0.003016}}


def _i15_sintetici():
    fr = {"NGC": {"FID": 0.69594386, "A1": 0.69647303, "A3": 0.69561829, "B1": 0.69580713, "B2": 0.69565316,
                  "B4": 0.69597562, "B5": 0.69631760, "C1": 0.69655061, "C2": 0.69629649, "C3": 0.69545645,
                  "C4": 0.69657907},
          "SGC": {"FID": 0.80747278, "A1": 0.80669819, "A3": 0.80882558, "B1": 0.79893873, "B2": 0.78936744,
                  "B4": 0.80739251, "B5": 0.80701356, "C1": 0.79566567, "C2": 0.80698096, "C3": 0.80190081,
                  "C4": 0.80672401}}
    return {reg: "\n".join(json.dumps({"point": p, "gauge": "amend13", "independent_fraction": v})
                           for p, v in d.items()) + "\n" for reg, d in fr.items()}


def _tex_sintetico(chk):
    return "\\section{x}\n" + "\n".join(c.replace(" ", "\n", 1) for c in chk) + "\n"


def _t_ancora_mancante():
    fx = _fixtures()
    fx["mod"] = fx["mod"].replace(O_M2, "niente\n")
    try:
        costruisci(fx, _gettoni_finti())
    except PatchError as e:
        return "M2" in str(e)
    return False


def _t_ancora_doppia():
    fx = _fixtures()
    fx["chk"] += O_C3
    try:
        costruisci(fx, _gettoni_finti())
    except PatchError as e:
        return "2 volte" in str(e)
    return False


def _t_terminatori():
    out, _ = costruisci(_fixtures(), _gettoni_finti())
    s = out["sta"]
    ok = s.count("\r\n") == s.count("\n") and all("\r" not in out[k] for k in ("chk", "mod"))
    try:
        eol_di("a\r\nb\n")
    except PatchError:
        return ok
    return False


def _t_catena_completa():
    out, fatte = costruisci(_fixtures(), _gettoni_finti())
    tutto = "".join(out.values())
    return (len(fatte) == len(EDITS) and not postcondizioni(out) and " 12/12 |" in out["sta"]
            and not re.search(r"@[A-Z0-9_]+@", tutto))


def _t_idempotenza():
    out, _ = costruisci(_fixtures(), _gettoni_finti())
    try:
        costruisci(out, _gettoni_finti())
    except PatchError as e:
        return "gia' applicata" in str(e)
    return False


def _t_numeri_attesi():
    i15 = _i15_sintetici()
    tok, chk = numeri(_ledger_sintetico(), _d2_sintetici(), i15["NGC"], i15["SGC"])
    return all(tok[k] == v for k, v in ATTESI.items()) and len(chk) >= 25


def _t_tex_riscontro():
    i15 = _i15_sintetici()
    tok, chk = numeri(_ledger_sintetico(), _d2_sintetici(), i15["NGC"], i15["SGC"])
    tex = _tex_sintetico(chk)
    if controlla_tex(tex, chk):
        return False
    tok2, chk2 = numeri(_ledger_sintetico(delta_md=0.02), _d2_sintetici(), i15["NGC"], i15["SGC"])
    manc = controlla_tex(tex, chk2)
    return len(manc) == 1 and "28.49" in manc[0]


def _t_attesi_diversi():
    d2 = _d2_sintetici()
    d2["SGC"]["dN_medio"] = -56.60
    i15 = _i15_sintetici()
    try:
        numeri(_ledger_sintetico(), d2, i15["NGC"], i15["SGC"])
    except PatchError as e:
        return "diversi dagli attesi" in str(e)
    return False


def _t_chiave_d2():
    d2 = _d2_sintetici()
    d2["NGC"]["per_parametro"] = {"dN_medio": -1.0}
    i15 = _i15_sintetici()
    try:
        numeri(_ledger_sintetico(), d2, i15["NGC"], i15["SGC"])
    except PatchError as e:
        return "compare 2 volte" in str(e)
    return False


def _t_figura():
    buono = json.dumps({"pdf": {FIGPDF: FIG_PREFISSO + "0" * 52}, "inputs": {REG["f1py"]: "f" * 64}}) + "\n"
    ok = figura(buono, FIG_PREFISSO + "0" * 52, "f" * 64) == {"FIG12": FIG_PREFISSO, "NREC_F1": "1"}
    for args in ((buono, "1" * 64, "f" * 64), (buono, FIG_PREFISSO + "0" * 52, "e" * 64)):
        try:
            figura(*args)
        except PatchError:
            continue
        return False
    return ok


def _t_atomicita():
    d = tempfile.mkdtemp(prefix="st_patch_")
    try:
        a = J(d, "a.md")
        with open(a, "w", encoding="utf-8", newline="") as fh:
            fh.write("originale\n")
        try:
            scrivi_atomico({a: "nuovo\n", J(d, "manca", "b.md"): "nuovo\n"}, J(d, "bak"))
        except Exception:
            pass
        else:
            return False
        return leggi(a) == "originale\n" and not [x for x in os.listdir(d) if x.startswith(".tmp_patch_")]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _t_verify():
    d = tempfile.mkdtemp(prefix="st_verify_")
    try:
        p = J(d, "f.md")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write("contenuto\n")
        h, n = sha_file(p)
        return (confronta_ricevuta({p: {"sha256": h, "byte": n}}) == []
                and len(confronta_ricevuta({p: {"sha256": "0" * 64, "byte": n}})) == 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)


TESTS = [
    ("ancora mancante -> errore col nome della modifica", _t_ancora_mancante),
    ("ancora doppia -> errore", _t_ancora_doppia),
    ("terminatori: CRLF dello stato e LF degli altri conservati; misti -> errore", _t_terminatori),
    ("catena completa su fixture: 18 modifiche, postcondizioni, nessun token residuo", _t_catena_completa),
    ("seconda applicazione -> errore esplicito", _t_idempotenza),
    ("numeri da registri sintetici = attesi dichiarati", _t_numeri_attesi),
    ("riscontro sul tex: tutto presente; un valore alterato -> manca proprio quello", _t_tex_riscontro),
    ("un valore di d2_v2 alterato -> errore sugli attesi", _t_attesi_diversi),
    ("chiave di d2_v2 ripetuta -> errore", _t_chiave_d2),
    ("figura: sha diverso dal registro o script diverso -> errore", _t_figura),
    ("scrittura atomica: errore sul secondo file lascia intatto il primo", _t_atomicita),
    ("verify rileva uno sha diverso dalla ricevuta", _t_verify),
]


def selftest(verboso=True):
    ok = 0
    for nome, fn in TESTS:
        try:
            esito = bool(fn())
        except Exception as e:
            esito = False
            nome += " [%s: %s]" % (type(e).__name__, e)
        ok += esito
        if verboso and not esito:
            print("  FAIL  " + nome)
    if verboso:
        print("selftest: %d/%d %s" % (ok, len(TESTS), "PASS" if ok == len(TESTS) else "FAIL"))
    return ok == len(TESTS)


# ----------------------------------------------------------------------------- disco

def confronta_ricevuta(uscite):
    scarti = []
    for p, att in uscite.items():
        if not os.path.exists(p):
            scarti.append("%s: assente" % p)
            continue
        h, n = sha_file(p)
        if h != att["sha256"] or n != att["byte"]:
            scarti.append("%s: %s… %d byte, ricevuta %s… %d" % (p, h[:12], n, att["sha256"][:12], att["byte"]))
    return scarti


def radice_ok():
    if not (os.path.isdir("src") and os.path.isdir("papers") and os.path.isdir("logs")):
        raise PatchError("lanciare dalla radice del repository (servono src/, papers/, logs/)")


def precondizioni():
    fallite = []
    for p, (sha, size) in PRE.items():
        if not os.path.exists(p):
            fallite.append("%s: assente" % p)
            continue
        h, n = sha_file(p)
        if h != sha or n != size:
            fallite.append("%s: %s… %d byte, atteso %s… %d" % (p, h[:12], n, sha[:12], size))
    if not os.path.exists(RICEVUTA_C):
        fallite.append("%s: assente (serve a dire che i documenti sono quelli della passata c)" % RICEVUTA_C)
    else:
        with open(RICEVUTA_C, encoding="utf-8") as fh:
            usc = json.load(fh)["uscite"]
        for k in DOC:
            if DOC[k] not in usc:
                fallite.append("%s: non fra le uscite della ricevuta c" % DOC[k])
        fallite += ["dopo la passata c, " + s for s in confronta_ricevuta({DOC[k]: usc[DOC[k]] for k in DOC
                                                                             if DOC[k] in usc})]
    for p in list(D2.values()) + [FIGREG, FIGPDF]:
        if not os.path.exists(p):
            fallite.append("%s: assente" % p)
    return fallite


def prepara():
    radice_ok()
    if not selftest(verboso=False):
        raise PatchError("selftest non superato: lanciare 'selftest' per il dettaglio")
    fallite = precondizioni()
    if fallite:
        raise PatchError("precondizioni:\n  " + "\n  ".join(fallite))
    d2 = {}
    for reg, p in D2.items():
        with open(p, encoding="utf-8") as fh:
            d2[reg] = json.load(fh)
    tok, chk = numeri(leggi(REG["ledger"]), d2, leggi(REG["i15N"]), leggi(REG["i15S"]))
    manc = controlla_tex(leggi(REG["tex"]), chk)
    if manc:
        raise PatchError("numeri del §5 assenti dal manoscritto (%d su %d):\n  %s"
                         % (len(manc), len(chk), "\n  ".join(manc)))
    tok.update(figura(leggi(FIGREG), sha_file(FIGPDF)[0], PRE[REG["f1py"]][0]))
    oggi = datetime.date.today()
    data = data_it(oggi)
    tok.update({"DATA": data, "DATAB": "%d %s %d" % (oggi.day, MESI_BREVI[oggi.month - 1], oggi.year),
                "TEX8": PRE[REG["tex"]][0][:8], "BIB8": PRE[REG["bib"]][0][:8],
                "TEXB": migliaia(PRE[REG["tex"]][1]), "BIBB": migliaia(PRE[REG["bib"]][1]),
                "F18": PRE[REG["f1py"]][0][:8], "NTEX": str(len(chk)), "NST": str(len(TESTS))})
    testi = {k: leggi(p) for k, p in DOC.items()}
    pre_doc = {DOC[k]: sha_testo(testi[k]) for k in DOC}
    out, fatte = costruisci(testi, tok)
    return {"oggi": oggi, "data": data, "tok": tok, "nchk": len(chk), "fatte": fatte, "out": out,
            "pre_doc": pre_doc}


def stampa(r, scritto):
    print("precondizioni: %d/%d PASS (sha e byte) + documenti = uscite della passata c" % (len(PRE), len(PRE)))
    print("selftest: %d/%d PASS" % (len(TESTS), len(TESTS)))
    print("data dall'orologio: %s%s" % (r["data"], "" if r["oggi"] == DATA_DECISIONI else
                                         "  (attenzione: diversa dal 24 set del §5)"))
    t = r["tok"]
    print("numeri dai registri = attesi: frazione indipendente %s %% / %s %%; divergenze r78 %s / %s oltre 3, r58 %s / %s;"
          " dN %s / %s" % (t["FI_NGC"], t["FI_SGC"], t["DIV_N_OLTRE"], t["DIV_S_OLTRE"], t["DIV58_N"], t["DIV58_S"],
                           t["DN_N"], t["DN_S"]))
    print("numeri del §5 e del §4.2 nel manoscritto: %d/%d con la cifra quotata" % (r["nchk"], r["nchk"]))
    print("figura: %s…, fig_F1.jsonl a %s record" % (t["FIG12"], t["NREC_F1"]))
    print("modifiche: %d/%d ancore trovate una volta sola" % (len(r["fatte"]), len(EDITS)))
    for k, p in DOC.items():
        h, b = sha_testo(r["out"][k])
        print("%s: %s -> %s byte, sha %s…" % (os.path.basename(p), migliaia(r["pre_doc"][p][1]), migliaia(b), h[:12]))
    print("postcondizioni: PASS")
    print("ESITO: %s" % ("APPLICATA" if scritto else "DRY-RUN, nessun file scritto"))


def cmd_apply():
    r = prepara()
    scrivi_atomico({DOC[k]: r["out"][k] for k in DOC}, BACKUP)
    uscite = {}
    for p in DOC.values():
        h, n = sha_file(p)
        uscite[p] = {"sha256": h, "byte": n}
    ingressi = {p: {"sha256": s, "byte": b} for p, (s, b) in PRE.items()}
    ingressi.update({p: {"sha256": s, "byte": b} for p, (s, b) in r["pre_doc"].items()})
    for p in list(D2.values()) + [FIGREG, FIGPDF]:
        h, n = sha_file(p)
        ingressi[p] = {"sha256": h, "byte": n}
    ric = {"strumento": "paper2_patch_revisione_24set_d.py", "data": r["data"],
           "ingressi": ingressi, "uscite": uscite, "modifiche": r["fatte"], "gettoni": r["tok"],
           "numeri_tex": r["nchk"], "selftest": "%d/%d" % (len(TESTS), len(TESTS))}
    with open(RICEVUTA, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ric, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    stampa(r, True)
    print("ricevuta: %s" % RICEVUTA)


def cmd_verify():
    radice_ok()
    if not os.path.exists(RICEVUTA):
        raise PatchError("ricevuta assente: la passata non risulta applicata")
    with open(RICEVUTA, encoding="utf-8") as fh:
        ric = json.load(fh)
    scarti = confronta_ricevuta(ric["uscite"])
    esterni = [p for p in ric["ingressi"] if p not in DOC.values()]
    scarti += confronta_ricevuta({p: ric["ingressi"][p] for p in esterni})
    testi = {k: leggi(p) for k, p in DOC.items()}
    scarti += postcondizioni(testi)
    for k, p in DOC.items():
        eol_di(testi[k])
        h, n = sha_file(p)
        print("%s: %s… %s byte" % (os.path.basename(p), h[:12], migliaia(n)))
    for s in scarti:
        print("  FAIL  " + s)
    print("ESITO: %s" % ("PASS" if not scarti else "FAIL (%d)" % len(scarti)))
    return 0 if not scarti else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("comando", choices=["selftest", "dry-run", "apply", "verify"])
    a = ap.parse_args()
    try:
        if a.comando == "selftest":
            return 0 if selftest() else 1
        if a.comando == "dry-run":
            stampa(prepara(), False)
            return 0
        if a.comando == "apply":
            cmd_apply()
            return 0
        return cmd_verify()
    except PatchError as e:
        print("ERRORE: %s" % e)
        print("ESITO: FALLITO, nessun file scritto" if a.comando != "verify" else "ESITO: FAIL")
        return 2


if __name__ == "__main__":
    sys.exit(main())

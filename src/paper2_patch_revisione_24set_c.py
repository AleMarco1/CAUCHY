#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_revisione_24set_c.py -- terza passata documentaria del 24 settembre 2026.

Porta nei documenti le decisioni sul par. 4 e il ritiro del record 19:
  * checklist rev. 3.36 -> 3.37: B' definitivo; D-1..D-10; il fattore 67-265 (e 61-247), ritirato
    dal record 19 del 1 set, annotato dove sopravviveva (voci 3.4 e 5.2, struttura);
  * stato dalla 20a alla 21a revisione; tre voci aperte nuove, Z-titolo chiusa;
  * paper2_5_5_smentite.md: tre predizioni fuori dal ledger (D-7 SGC, D-10);
  * modifiche_paper1.md: P1-13 punto 1 corretto (riga AP senza il fattore ritirato);
  * paper2_inventario_s4.md: nota in testa (D-1 superata).

Ogni numero dei testi nuovi si RICALCOLA dai registri sul disco (fase3_analisi, fase3_budget,
fase3, forma_lato_mock_v3) contro attesi dichiarati qui; se un numero non torna, nulla si scrive.
Nessun record nuovo nel ledger: il protocollo non cambia (il ledger e' fra le precondizioni).

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
    "sme": J(P2, "paper2_5_5_smentite.md"),
    "mod": J(P2, "modifiche_paper1.md"),
    "inv": J(P2, "paper2_inventario_s4.md"),
}
REG = {
    "analisi": J("results", "paper2", "fase3_analisi.jsonl"),
    "budget": J("results", "paper2", "fase3_budget.jsonl"),
    "dati": J("results", "paper2", "fase3.jsonl"),
    "forma": J("logs", "forma_lato_mock_v3.json"),
    "b1": J("logs", "b1_decomposizione_v2.json"),
    "fa_py": J("src", "paper2_fase3_analisi.py"),
}
RICEVUTA = J("logs", "patch_revisione_24set_c.json")
BACKUP = J("logs", "patch_revisione_24set_c_backup")

PRE = {
    DOC["chk"]: ("5eafea853d42cd05e73f6fc23b48e9f93d63adc748d64050ce99a516f1f85a47", 287521),
    DOC["sta"]: ("31290224cd73f16878c3b0fa2dbac674616cf44e1b724783545ddb287e75b11a", 116027),
    DOC["sme"]: ("82b2878d001509f837609ebfef588c334353de1e11bec175ffb53bc3d1efb44c", 15129),
    DOC["mod"]: ("2425045c373ed22c04be649835814419cad3306dc5c3d442fc3b47fd89b0600f", 83564),
    DOC["inv"]: ("d008ff0a8adefa5a6291c5c82e4a4b2b3180e265d1405b7910a522964f809de3", 11962),
    REG["analisi"]: ("c307fb30bda6870625dfa1e8fcdf7ead4bc70b49a03787316383cb52646b0d51", 97333),
    REG["budget"]: ("f5aec09b051c95fcec18825d6f23bf521f2eb593ae50e425bfa95ead664acfcb", 191371),
    REG["dati"]: ("c8dde1c683eb52febee99271daf2d32545b4618cd445a2f3a7449e1b3e76b84f", 101983),
    REG["forma"]: ("f164e4d25ec0bb8f51873c6439501f8460e66347c2bda89381eb1f0f3c4be9cc", 9401),
    REG["fa_py"]: ("31bc9d0a2799820ef4f00681aa1c6663739872cf98eefac7acfb37bcf7dce762", 39773),
    REG["b1"]: ("1eacf1baf57c855a8cdc1521748317946cce3bcf7da6f12f5fe2b09562d8053c", 3274),
    J(P2, "MNRAS", "paper2_mnras.tex"):
        ("d44bd6e9923797f78e9bb4658793e1bb88c71e5622a3edea651414f9285113fb", 22859),
    J(P2, "MNRAS", "paper2.bib"):
        ("3d47439946b9a9beae66bcd744fe6de5b42ddb706922717abae94f489f2c21c2", 11439),
    J("src", "paper2_v1_amendments.jsonl"):
        ("fb70459fca476145a791407e3bd1f5bd82f0dbc04e3f3d250309930bcf3f20a5", 663194),
}

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]
DATA_DECISIONI = datetime.date(2026, 9, 24)

# Selezione delle passate, dichiarata: una per emisfero.
UTC_ANALISI_ULTIMA = "2026-09-05T04:20"   # passate 8/9, sei punti, k0-k3
UTC_ANALISI_5PT = "2026-08-31T04:22:3"    # passate 4/5, GLS a cinque punti
UTC_ANALISI_6PT = "2026-08-31T12:53:48"   # passate 6/7, GLS a sei punti
UTC_BUDGET_ULTIMA = "2026-09-06T18:29:40"  # passate 19/20, blocco A a sei punti, k0-k3
F_DEPOSITATO = 0.027
INVILUPPO_PIPELINE = (0.973869, 1.040504)  # src/paper2_fase3_analisi.py, F_PHYS_ENVELOPE

# Attesi, dichiarati prima di leggere il disco (misurati il 24 set sui registri caricati).
ATTESI = {
    "D1": {"NGC_k0": ("153.2", "174.9", "2.14", "2.44"), "NGC_k1": ("73.6", "95.8", "0.91", "1.18"),
           "SGC_k0": ("114.8", "133.5", "3.21", "3.74"), "SGC_k1": ("124.9", "142.9", "2.80", "3.20")},
    "D1_MIN": "0.9", "D1_MAX": "3.2", "D1_CI_MAX": "3.7",
    "F5": ("67", "265"), "F6": ("61", "247"),
    "D7": {"NGC": ("59.79", "46.36", "0.776"), "SGC": ("41.46", "57.71", "1.392")},
    "B1_F": "0.97107", "B6_F": "1.04553",
    "QB1": ("135.9", "141.9", "6.0"), "QFORMA": ("12.4", "16.6"),
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


def riempi(tpl, tok):
    out = tpl
    for k, v in tok.items():
        out = out.replace("@%s@" % k, v)
    resto = re.findall(r"@[A-Z0-9_]+@", out)
    if resto:
        raise PatchError("token non sostituiti: %s" % sorted(set(resto)))
    return out




# ----------------------------------------------------------------------------- numeri dai registri

def _jsonl(testo):
    out = []
    for i, riga in enumerate(testo.splitlines(), 1):
        if riga.strip():
            try:
                out.append(json.loads(riga))
            except Exception as e:
                raise PatchError("riga %d illeggibile: %s" % (i, e))
    return out


def _una_per_emisfero(rec, prefisso, cosa):
    sel = [r for r in rec if str(r.get("utc", "")).startswith(prefisso)]
    reg = sorted(r["region"] for r in sel)
    if reg != ["NGC", "SGC"]:
        raise PatchError("%s: attese una passata NGC e una SGC con utc %s*, trovate %r" % (cosa, prefisso, reg))
    return {r["region"]: r for r in sel}


def numeri_registri(t_analisi, t_budget, t_dati, t_forma, t_b1, sha_fa_py):
    """Ricalcola dai registri ogni numero dei testi nuovi; errore se uno non torna."""
    an = _jsonl(t_analisi)
    bu = _jsonl(t_budget)
    da = _jsonl(t_dati)
    fo = json.loads(t_forma)
    n = {}
    # D-1: affermazione dentro il range, passate del 5 set
    ult = _una_per_emisfero(an, UTC_ANALISI_ULTIMA, "fase3_analisi (ultima)")
    d1, rel, relci = {}, [], []
    for reg in ("NGC", "SGC"):
        for k in ("k0", "k1"):
            L = ult[reg]["levels"][k]
            Df = L["D_fiducial"]
            pp = L["per_point"]
            m = max(abs(q["estimate"]) for q in pp.values())
            ci = max(max(abs(q["ci95"][0]), abs(q["ci95"][1])) for q in pp.values())
            d1["%s_%s" % (reg, k)] = ("%.1f" % m, "%.1f" % ci, "%.2f" % (100 * m / Df), "%.2f" % (100 * ci / Df))
            rel.append(100 * m / Df)
            relci.append(100 * ci / Df)
    n["D1"] = d1
    n["D1_MIN"], n["D1_MAX"], n["D1_CI_MAX"] = "%.1f" % min(rel), "%.1f" % max(rel), "%.1f" % max(relci)
    # il fattore ritirato: D_fid / |a| del fit quadratico, cinque e sei punti
    for chiave, pref in (("F5", UTC_ANALISI_5PT), ("F6", UTC_ANALISI_6PT)):
        sel = _una_per_emisfero(an, pref, "fase3_analisi " + chiave)
        fatt = []
        for reg in ("NGC", "SGC"):
            for k in ("k0", "k1"):
                L = sel[reg]["levels"][k]
                if L["symmetry"].get("model_adequate", True):
                    raise PatchError("%s %s %s: il fit risulta adeguato, contro quanto annotato" % (chiave, reg, k))
                fatt.append(abs(L["D_fiducial"] / L["symmetry"]["a"]) / F_DEPOSITATO)
                if L.get("required_F") is not None:
                    raise PatchError("%s %s %s: required_F presente, contro il record 19" % (chiave, reg, k))
        n[chiave] = ("%d" % round(min(fatt)), "%d" % round(max(fatt)))
    # D-7: rms del non attribuito da k=0 a k=3, passate del 6 set
    bsel = _una_per_emisfero(bu, UTC_BUDGET_ULTIMA, "fase3_budget")
    n["D7"] = {}
    for reg in ("NGC", "SGC"):
        u0 = bsel[reg]["levels"]["k0"]["unattributed_rms"]
        u3 = bsel[reg]["levels"]["k3"]["unattributed_rms"]
        n["D7"][reg] = ("%.2f" % u0, "%.2f" % u3, "%.3f" % (u3 / u0))
    # la linea campionata racchiude l'inviluppo fisico (convenzione pipeline)
    fb = {}
    for r in da:
        if r.get("point") in ("B1", "B6"):
            fb.setdefault(r["point"], set()).add(r["F_ap"])
    if any(len(v) != 1 for v in fb.values()) or set(fb) != {"B1", "B6"}:
        raise PatchError("fase3.jsonl: F_ap di B1 e B6 non univoci: %r" % fb)
    b1, b6 = fb["B1"].pop(), fb["B6"].pop()
    if not (b1 < INVILUPPO_PIPELINE[0] and b6 > INVILUPPO_PIPELINE[1]):
        raise PatchError("la linea B non racchiude l'inviluppo: B1 %r, B6 %r" % (b1, b6))
    n["B1_F"], n["B6_F"] = "%.5f" % b1, "%.5f" % b6
    # D-8: il fa_sha256 del log e' lo sha dello strumento
    if fo.get("fa_sha256") != sha_fa_py:
        raise PatchError("forma_lato_mock_v3.json: fa_sha256 %r diverso dallo sha di paper2_fase3_analisi.py"
                         % fo.get("fa_sha256"))
    # D-10: le due predizioni del 23 set, dai due log
    b1 = json.loads(t_b1)["esito"]
    if not (b1["parte_dati"] < 0 and b1.get("verificata") is False):
        raise PatchError("b1_decomposizione_v2.json: esito non come annotato (%r)" % b1)
    n["QB1"] = ("%.1f" % b1["eccesso_dD"], "%.1f" % b1["parte_mock"], "%.1f" % abs(b1["parte_dati"]))
    casi = fo["casi"]
    lim = casi["NGC_k3"]["limite"]
    if not (casi["NGC_k2"]["chi2_mock"] < lim and casi["SGC_k2"]["chi2_mock"] < lim
            and casi["NGC_k3"]["chi2_mock"] > lim and casi["SGC_k3"]["chi2_mock"] > lim):
        raise PatchError("forma_lato_mock_v3.json: la forma del lato mock non e' come annotata")
    n["QFORMA"] = ("%.1f" % casi["NGC_k3"]["chi2_mock"], "%.1f" % casi["SGC_k3"]["chi2_mock"])
    if n != ATTESI:
        diff = [k for k in ATTESI if n.get(k) != ATTESI[k]]
        raise PatchError("numeri ricalcolati diversi dagli attesi in %r: %r" % (diff, {k: n.get(k) for k in diff}))
    return n


# ----------------------------------------------------------------------------- testi: checklist

O_C1 = "\n### rev. 3.36 — 24 settembre 2026 — **la scrittura comincia.**"
T_C1 = (
    "\n### rev. 3.37 — @DATA@ — **le decisioni del §4 nei documenti, e il ritiro del record 19 dove non"
    " era arrivato.** Titolo **B′** definitivo; «The symmetry test of the protocol (Section 2.3)»"
    " confermato; D-1–D-10 decisi o chiusi (Fase 7, «Struttura»). **Il fattore di estrapolazione"
    " 67–265 (e 61–247) era ritirato dal record 19 del 1° settembre** e sopravviveva nelle voci 3.4 e"
    " 5.2 e in P1-13: annotato qui, corretto in P1-13. Al suo posto l'affermazione dentro il range,"
    " @D1_MIN@–@D1_MAX@ % del deficit (estremi IC95 fino a @D1_CI_MAX@ %). La predizione bordo/volume della 3.6,"
    " **mai letta**: NGC ×@R_NGC@ (volume), SGC ×@R_SGC@ (nessuno dei due rami). §4.5 nuova. Compilazione"
    " locale con MiKTeX. Nessun record nuovo: il protocollo non cambia."
    "\n### rev. 3.36 — 24 settembre 2026 — **la scrittura comincia.**"
)

O_C2 = "reproduced by its power spectrum; one quarter is not».\n"
T_C2 = O_C2 + "**✦ rev. 3.37:** **B′ è il titolo definitivo** (24 set); Z-titolo chiusa.\n"

O_C3 = "va data nel §2.\n\n1. Introduzione:"
T_C3 = (
    "va data nel §2.\n\n"
    "**✦ rev. 3.37 — decisioni del 24 set sul §4.** Inventario `paper2_inventario_s4.md`; i dodici\n"
    "registri e log del §4, caricati, coincidono sha per sha con `logs/schema_s4.txt`. Ogni numero qui\n"
    "sotto è ricalcolato dai registri dal patcher della rev. 3.37.\n"
    "\n"
    "- **D-1.** Il fattore di estrapolazione non entra in nessun paper. È *D*_fid/|*a*| col coefficiente\n"
    "  lineare del fit quadratico: @F5A@–@F5B@ a cinque punti, @F6A@–@F6B@ a sei, e in tutti e quattro i casi il\n"
    "  fit è inadeguato. Il **record 19** (1 set) lo ha ritirato per questo e perché divide per 0.027,\n"
    "  lato piccolo di un intervallo asimmetrico (deviazione massima 0.0389); lo strumento lo sopprime\n"
    "  (`required_F` = `None` a *k* = 0, 1). Al suo posto l'affermazione dentro il range campionato,\n"
    "  sulle passate del 5 set: max|Δ*D*| sui punti campionati @M_NGC_k0@, @M_NGC_k1@, @M_SGC_k0@, @M_SGC_k1@\n"
    "  (NGC *k*=0, *k*=1; SGC *k*=0, *k*=1), cioè @PM_NGC_k0@, @PM_NGC_k1@, @PM_SGC_k0@, @PM_SGC_k1@ % di *D*_fid;\n"
    "  estremi IC95 @C_NGC_k0@, @C_NGC_k1@, @C_SGC_k0@, @C_SGC_k1@, cioè @PC_NGC_k0@, @PC_NGC_k1@, @PC_SGC_k0@,\n"
    "  @PC_SGC_k1@ %. Nel paper: «*D* si sposta al più dello @D1_MIN@–@D1_MAX@ per cento del deficit, e gli\n"
    "  estremi al 95 per cento restano sotto il @D1_CI_MAX@». Il «172.5 generatori, 2.0–4.8 %» che il codice\n"
    "  stampa è una stringa scritta a mano e non si riproduce: non si usa. La linea campionata\n"
    "  racchiude l'inviluppo fisico in convenzione pipeline: B1 = @B1_F@ < 0.973869, B6 = @B6_F@ > 1.040504.\n"
    "- **D-2.** Sei contributi, (a)–(f), più il non attribuito.\n"
    "- **D-3.** Nessun verdetto di simmetria a *k* = 2: il registro lo porta emesso in NGC, il paper no.\n"
    "- **D-4.** Nuova §4.5, «The mock side responds twice as strongly»: il fattore ~2 fra le risposte\n"
    "  dei due lati; selezione congelata, spazio reale, clipping (voci 3.7, 3.8, 3.14, 3.15).\n"
    "- **D-5.** Copertura del non attribuito col denominatore `unattributed_rms`, carving escluso,\n"
    "  dichiarato nel testo.\n"
    "- **D-6.** Il confronto «sulla linea *F*_AP» non è mai stato fatto: il §4.1 usa i cancelli di\n"
    "  Fase 2.\n"
    "- **D-7.** La predizione dichiarata prima della 3.6 **non era mai stata letta**. Passate del 6 set:\n"
    "  rms del non attribuito da *k*=0 a *k*=3, NGC @U0_NGC@ → @U3_NGC@ (×@R_NGC@, ramo «volume»), SGC\n"
    "  @U0_SGC@ → @U3_SGC@ (×@R_SGC@, **nessuno dei due rami**). SGC va nell'appendice B.\n"
    "- **D-8.** Chiuso: gli script della 3.10 leggono solo `results/paper2/{fase3_mock,fase3,\n"
    "  fase3_analisi}.jsonl`, e il `fa_sha256` di `forma_lato_mock_v3.json` è lo sha di\n"
    "  `src/paper2_fase3_analisi.py`. Le docstring dei due script nominano ancora il log della rev. 1\n"
    "  (Z-docstring-3.10).\n"
    "- **D-9.** Chiuso dalla nota F del budget: nel paper il pavimento a sei punti; il ±25 è lo stadio\n"
    "  a due punti.\n"
    "- **D-10.** Due predizioni falsificate il 23 set, fuori dal ledger: la quota del lato dati\n"
    "  nell'eccesso di B1 (almeno 2/3 dichiarati; −@QB1_D@ su +@QB1_E@) e la forma quadratica del lato mock a\n"
    "  *k* = 2, 3 (cade a *k* = 3). Con D-7 SGC, nel gruppo 3-bis di `paper2_5_5_smentite.md`.\n"
    "\n"
    "1. Introduzione:"
)

O_C4 = "      **✧✧✦ E la falsificazione pulita, che non dipende da nessun modello.**"
T_C4 = (
    "      **✦ rev. 3.37 — RITIRATO dal record 19 (1 set), mai annotato qui.** Il fattore che segue\n"
    "      inverte il coefficiente lineare di un fit quadratico che il fit stesso dichiara inadeguato\n"
    "      (*D*_fid/|*a*|: @F5A@–@F5B@ a cinque punti, @F6A@–@F6B@ a sei), e divide per 0.027, lato piccolo di un\n"
    "      intervallo la cui deviazione massima vale 0.0389. Al suo posto l'affermazione dentro il range\n"
    "      (Fase 7, «Struttura», D-1). Il testo resta come storia.\n"
    + O_C4
)

O_C5 = "pendenza (247, 139, 71, 61 volte il range fisico) ma la conclusione no.\n"
T_C5 = ("pendenza (247, 139, 71, 61 volte il range fisico) ma la conclusione no. *(Ritirato dal record 19:\n"
        "      vedi la nota della rev. 3.37 sopra.)*\n")

O_C6 = "         \\|*F*−1\\| ≤ 0.027», stato «falsified as sole cause; amplitude in preparation»;\n"
T_C6 = O_C6 + (
    "         **✦ rev. 3.37:** quel fattore era ritirato dal record 19; P1-13 punto 1 è corretto il 24 set\n"
    "         (riga senza numeri, col campionamento che racchiude l'intervallo fisico).\n"
)

O_C7 = ("3. Il canale isotropo è una convenzione di griglia; le due convenzioni di σ_px a confronto sulla\n"
        "   linea *F*_AP.\n")
T_C7 = ("3. Il canale isotropo è una convenzione di griglia; ~~le due convenzioni di σ_px a confronto sulla\n"
        "   linea *F*_AP~~ **(rev. 3.37, D-6: tolto; il §4.1 usa i cancelli di Fase 2)**.\n")

O_C8 = "5. Risposta AP del deficit: decomposizione a cinque contributi, ranghi empirici.\n"
T_C8 = "5. Risposta AP del deficit: decomposizione a ~~cinque~~ **sei** contributi (rev. 3.37, D-2), ranghi empirici.\n"

# ----------------------------------------------------------------------------- testi: stato (LF qui)

O_S1 = "aggiornato **24 settembre 2026**, ventesima revisione"
T_S1 = "aggiornato **@DATA@**, ventunesima revisione"

O_S2 = "`v3.1-paper2`, letto finora solo come nome.\n\n---\n\n## 1. Il risultato principale"
T_S2 = (
    "`v3.1-paper2`, letto finora solo come nome.\n\n"
    "**Al @DATAB@ (ventunesima revisione):** decisioni del §4 nei documenti · titolo **B′** definitivo ·\n"
    "**il fattore di estrapolazione era ritirato dal record 19** (1 set) e sopravviveva nelle voci 3.4 e\n"
    "5.2 della checklist e in P1-13: annotato nella checklist 3.37, **P1-13 punto 1 corretto** (riga AP\n"
    "senza numeri, col campionamento che racchiude l'intervallo fisico) · affermazione dentro il range\n"
    "ricalcolata dal registro: @D1_MIN@–@D1_MAX@ % del deficit, estremi IC95 fino a @D1_CI_MAX@ %; il «172.5, 2.0–4.8 %»\n"
    "stampato dal codice è una stringa scritta a mano e non si riproduce · **predizione bordo/volume della\n"
    "3.6, mai letta**: NGC ×@R_NGC@ (volume), SGC ×@R_SGC@ (nessuno dei due rami) · due predizioni del 23 set\n"
    "falsificate fuori dal ledger (quota del lato dati in B1, forma del lato mock a *k* = 3); le tre nel\n"
    "gruppo 3-bis di `paper2_5_5_smentite.md` · §4.5 nuova · compilazione locale con MiKTeX 25.12,\n"
    "reinstallato dopo un aggiornamento interrotto: classe v3.3 nostra, font `newtx`; `paper2_mnras.tex`\n"
    "`@TEX8@…`, `paper2.bib` `@BIB8@…` · ledger invariato a 78 record: nessun record nuovo.\n"
    "\n---\n\n## 1. Il risultato principale"
)

O_S3 = ("| (24 set) numeri del testo delle limitazioni contro il budget | **tre da correggere**, corretti nella"
        " checklist rev. 3.36 |\n")
T_S3 = O_S3 + (
    "| (24 set) i dodici registri e log del §4 caricati contro `schema_s4.txt` | **identici**, sha per sha |\n"
    "| (24 set) da dove vengono 67–265 e 61–247 | *D*_fid/\\|*a*\\| col fit quadratico a cinque e sei punti, inadeguato in tutti e quattro i casi; ritirati dal record 19; `required_F` = `None` a *k* = 0, 1 |\n"
    "| (24 set) «172.5 generatori, 2.0–4.8 %» del record 19 | **stringa scritta a mano nel codice**, non riprodotta: max\\|Δ*D*\\| @M_NGC_k0@ / @M_NGC_k1@ / @M_SGC_k0@ / @M_SGC_k1@, estremi IC95 @C_NGC_k0@ / @C_NGC_k1@ / @C_SGC_k0@ / @C_SGC_k1@ |\n"
    "| (24 set) predizione bordo/volume della 3.6 | **mai letta**: NGC ×@R_NGC@, SGC ×@R_SGC@ (passate 19/20 del 6 set) |\n"
    "| (24 set) `fa_sha256` di `forma_lato_mock_v3.json` | è lo sha di `src/paper2_fase3_analisi.py` |\n"
)

O_S4 = ("| **Z-titolo** | B o B′ | scrittura | Si chiude con abstract e introduzione. B′ toglie dal titolo il"
        " «responds to», già titolo del §6 del Paper 1 |")
T_S4 = ("| ~~**Z-titolo**~~ | ~~B o B′~~ **CHIUSA il 24 set: B′** | scrittura | B′ toglie dal titolo il"
        " «responds to», già titolo del §6 del Paper 1 |")

O_S5 = ("| **Z-P1§6** | il §6 del Paper 1 si intitola «What *N*_H1 responds to» | introduzione | L'introduzione"
        " dice che cosa aggiunge il Paper 2: geometria, pesatura, separazione fra teorema e misura |\n")
T_S5 = O_S5 + (
    "| ~~**Z-record19**~~ | ~~il fattore ritirato sopravviveva in 3.4, 5.2 e P1-13~~ **CHIUSA il 24 set** | documenti | annotato nella checklist 3.37; P1-13 punto 1 corretto |\n"
    "| **Z-rango-201** | «il rango resta 1/201 in ogni punto» (record 19) | scrittura | da verificare su `fase3_mock.jsonl` prima di citarlo; D-1 non lo usa |\n"
    "| **Z-docstring-3.10** | le docstring di `paper2_b1_decomposizione.py` e `paper2_forma_lato_mock.py` nominano il log della rev. 1 | rilascio | difetto minore: gli script scrivono `_v2` e `_v3` |\n"
)

O_S6 = ("| `paper2_patch_revisione_24set_b.py` | checklist 3.36, questo documento alla 20ª: struttura e rimandi"
        " del manoscritto, tre numeri del testo delle limitazioni ricalcolati dal budget, ancore misurate |"
        " 11/11 |\n")
T_S6 = O_S6 + (
    "| `paper2_patch_revisione_24set_c.py` | checklist 3.37, questo documento alla 21ª, P1-13 punto 1, tre"
    " smentite nel 3-bis, nota sull'inventario; numeri ricalcolati da cinque registri e log | @NST@/@NST@ |\n"
)

# ----------------------------------------------------------------------------- testi: smentite

O_SM = "Paper 2.\n\n## 4. Verifica dei 33 record esclusi"
T_SM = (
    "Paper 2.\n\n"
    "**✦ Aggiunte del 24 settembre (checklist rev. 3.37, D-7 e D-10).** Tre predizioni dichiarate fuori\n"
    "dal ledger, posteriori alla prima stesura di questo documento. Nessuna ha un record: non cambiano il\n"
    "protocollo, e stanno qui per entrare nell'appendice B.\n"
    "\n"
    "| id | dichiarata | predizione | esito |\n"
    "|---|---|---|---|\n"
    "| Q-B1 | 23 set, `paper2_b1_decomposizione.py` rev. 2 (checklist 3.10) | l'eccesso di B1 a *k* = 0 in NGC sulla media di B2, B4, B5 è portato dal lato dati per almeno 2/3 | **FALSIFICATA**: su +@QB1_E@ il lato mock porta +@QB1_M@, il lato dati −@QB1_D@ (`b1_decomposizione_v2.json`) |\n"
    "| Q-forma | 23 set, `paper2_forma_lato_mock.py` rev. 3 (checklist 3.6, rev. 3.34) | il lato mock resta quadratico entro il rumore anche a *k* = 2, 3 | **FALSIFICATA a *k* = 3**: χ² @QF_N@ (NGC) e @QF_S@ (SGC) contro 11.34; regge a *k* = 2 (`forma_lato_mock_v3.json`) |\n"
    "| Q-bordo | 6 set, checklist 3.6, prima del run | rms del non attribuito a *k* = 3 sotto metà di quella a *k* = 0 se è bordo; entro il 30 % se è volume | **letta solo il 24 set**: NGC ×@R_NGC@, ramo «volume»; SGC ×@R_SGC@, **nessuno dei due rami** (`fase3_budget.jsonl`, passate 19/20) |\n"
    "\n"
    "## 4. Verifica dei 33 record esclusi"
)

# ----------------------------------------------------------------------------- testi: modifiche_paper1

O_M1 = (
    "**A:**\n\n"
    "> fiducial cosmology / AP distortion | scaling of the fiducial-to-true distance ratio *F* | the *F*\n"
    "> required to erase the deficit lies 67–265× outside |*F*−1| ≤ 0.027 | falsified as sole cause;\n"
    "> amplitude in preparation\n\n"
    "**Perché in questa forma, e non con il numero.** La sensibilità è stata misurata — è l'esito della\n"
    "Fase 3 del Paper 2 — ma quei numeri sono preregistrati e non ancora pubblicati, e metterli qui\n"
    "legherebbe il Paper 1 a un manoscritto che può cambiare. La falsificazione, invece, non dipende da\n"
    "nessun modello: il fattore che azzererebbe il deficit è fuori dal range fisico da due ordini di\n"
    "grandezza, e non si muove se la Fase 5 rifinisce l'ampiezza. **Lo stato dice esplicitamente che\n"
    "l'ampiezza è materia del lavoro in corso**, coerentemente col §7.3, che già chiama l'AP «the\n"
    "subject of the next paper in this series».\n"
)
T_M1 = (
    "**A:** *(corretta il 24 set, checklist del Paper 2 rev. 3.37)*\n\n"
    "> fiducial cosmology / AP distortion | scaling of the fiducial-to-true distance ratio *F*, sampled\n"
    "> across its physical range | no sampled *F* removes the deficit | falsified as sole cause;\n"
    "> amplitude in preparation\n\n"
    "**Che cosa è cambiato, e perché.** La versione del 12 set diceva «the *F* required to erase the\n"
    "deficit lies 67–265× outside |*F*−1| ≤ 0.027». Quel fattore era già stato ritirato dal record 19 del\n"
    "Paper 2, il 1° settembre: inverte il coefficiente lineare di un fit quadratico che lo stesso fit\n"
    "dichiara inadeguato, e divide per 0.027, che è il lato piccolo di un intervallo asimmetrico\n"
    "(deviazione massima 0.0389). Non entra in nessuno dei due paper.\n\n"
    "**Perché in questa forma, e non con il numero.** La sensibilità è misurata dalla Fase 3 del Paper 2,\n"
    "ma quei numeri sono preregistrati e non ancora pubblicati, e metterli qui legherebbe il Paper 1 a un\n"
    "manoscritto che può cambiare. La falsificazione non ha bisogno di estrapolare: i punti campionati\n"
    "racchiudono l'intero intervallo fisico di *F* (in convenzione pipeline B1 = @B1_F@ sta sotto\n"
    "l'estremo 0.973869 dell'inviluppo dei dodici angoli, B6 = @B6_F@ sopra l'estremo 1.040504), e in\n"
    "nessuno di essi *D* si sposta di più del @D1_MAX@ per cento. **Lo stato dice esplicitamente che\n"
    "l'ampiezza è materia del lavoro in corso**, coerentemente col §7.3, che già chiama l'AP «the\n"
    "subject of the next paper in this series».\n"
)

O_M2 = ("1. Rileggere dal registro di 3.4 i quattro d*F* richiesti e ricontrollare il rapporto 67–265 contro\n"
        "   |*F*−1| ≤ 0.027, che è l'unico numero di Fase 3 che entra nel Paper 1.\n")
T_M2 = ("1. ~~Rileggere dal registro di 3.4 i quattro d*F* richiesti e ricontrollare il rapporto 67–265 contro\n"
        "   |*F*−1| ≤ 0.027~~ **Fatto il 24 set, e superato:** il rapporto era ritirato dal record 19, e la riga\n"
        "   corretta non porta più numeri di Fase 3.\n")

O_M3 = "| data | cosa |\n|---|---|\n"
T_M3 = O_M3 + (
    "| 24 set 2026 | **P1-13, punto 1 corretto**: la riga AP portava il fattore 67–265, ritirato dal record 19"
    " del Paper 2 il 1° settembre. Ora «no sampled *F* removes the deficit», col campionamento che racchiude"
    " l'intervallo fisico. Lo stato di P1-13 resta PRONTA |\n"
)

# ----------------------------------------------------------------------------- testi: inventario

O_I = "# Paper 2 — §4 «Geometry: the Alcock–Paczyński response». Inventario per la stesura\n"
T_I = O_I + (
    "\n> **Nota del 24 set (checklist rev. 3.37).** Le decisioni D-1–D-10 sono nella checklist. **La\n"
    "> proposta D-1 di questo documento è superata:** 67–265 e 61–247 erano entrambi ritirati dal record\n"
    "> 19; vale l'affermazione dentro il range. Il rapporto NGC di D-7 è ×@R_NGC@.\n"
)

EDITS = [
    ("chk", "C1 intestazione rev. 3.37", O_C1, T_C1),
    ("chk", "C2 titolo definitivo", O_C2, T_C2),
    ("chk", "C3 decisioni D-1..D-10", O_C3, T_C3),
    ("chk", "C4 voce 3.4: ritiro del record 19", O_C4, T_C4),
    ("chk", "C5 voce 3.4: 247, 139, 71, 61", O_C5, T_C5),
    ("chk", "C6 voce 5.2: P1-13", O_C6, T_C6),
    ("chk", "C7 struttura punto 3 (D-6)", O_C7, T_C7),
    ("chk", "C8 struttura punto 5 (D-2)", O_C8, T_C8),
    ("sta", "S1 riga 2", O_S1, T_S1),
    ("sta", "S2 ventunesima revisione", O_S2, T_S2),
    ("sta", "S3 righe del par. 0", O_S3, T_S3),
    ("sta", "S4 Z-titolo chiusa", O_S4, T_S4),
    ("sta", "S5 voci aperte nuove", O_S5, T_S5),
    ("sta", "S6 strumento nel par. 9", O_S6, T_S6),
    ("sme", "SM gruppo 3-bis", O_SM, T_SM),
    ("mod", "M1 P1-13 punto 1", O_M1, T_M1),
    ("mod", "M2 P1-13, da rifare", O_M2, T_M2),
    ("mod", "M3 registro delle modifiche", O_M3, T_M3),
    ("inv", "I nota in testa", O_I, T_I),
]


def gettoni(n):
    t = {}
    for k, v in n["D1"].items():
        t["M_" + k], t["C_" + k], t["PM_" + k], t["PC_" + k] = v
    for k in ("D1_MIN", "D1_MAX", "D1_CI_MAX", "B1_F", "B6_F"):
        t[k] = n[k]
    t["F5A"], t["F5B"] = n["F5"]
    t["F6A"], t["F6B"] = n["F6"]
    for reg in ("NGC", "SGC"):
        t["U0_" + reg], t["U3_" + reg], t["R_" + reg] = n["D7"][reg]
    t["QB1_E"], t["QB1_M"], t["QB1_D"] = n["QB1"]
    t["QF_N"], t["QF_S"] = n["QFORMA"]
    return t


def postcondizioni(testi, n):
    attese = [
        ("chk", "### rev. 3.37 —", 1),
        ("chk", "**✦ rev. 3.37 — decisioni del 24 set sul §4.**", 1),
        ("chk", "RITIRATO dal record 19 (1 set), mai annotato qui", 1),
        ("chk", "**B′ è il titolo definitivo**", 1),
        ("sta", "ventunesima revisione", 2),
        ("sta", "`paper2_patch_revisione_24set_c.py`", 1),
        ("sta", O_S1, 0),
        ("sta", "| **Z-titolo** |", 0),
        ("sme", "| Q-bordo |", 1),
        ("mod", "> across its physical range | no sampled *F* removes the deficit", 1),
        ("mod", "> required to erase the deficit lies 67–265×", 0),
        ("inv", "Nota del 24 set (checklist rev. 3.37)", 1),
    ]
    return ["%s: %r compare %d volte, attese %d" % (f, s, testi[f].count(s), k)
            for f, s, k in attese if testi[f].count(s) != k]


def costruisci(testi, n, data, tex8, bib8, nst):
    """Tutto in memoria. testi: dict chiave -> testo. Errore alla prima ancora mancante o doppia."""
    if "### rev. 3.37" in testi["chk"] or "ventunesima revisione" in testi["sta"]:
        raise PatchError("passata gia' applicata (marcatori della rev. 3.37 o della 21a presenti)")
    tok = gettoni(n)
    tok.update({"DATA": data, "DATAB": data.rsplit(" ", 1)[0], "TEX8": tex8, "BIB8": bib8, "NST": str(nst)})
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
    falliti = postcondizioni(out, n)
    if falliti:
        raise PatchError("postcondizioni: " + "; ".join(falliti))
    return out, fatte


def scrivi_atomico(nuovi, backup_dir):
    """Scrive tutti i file o nessuno: temporanei prima, poi sostituzioni; rollback dal backup."""
    os.makedirs(backup_dir, exist_ok=True)
    tmp = {}
    try:
        for p, t in nuovi.items():
            shutil.copy2(p, J(backup_dir, os.path.basename(p)))
            fd, tp = tempfile.mkstemp(dir=os.path.dirname(p) or ".", prefix=".tmp_patch_", suffix=".md")
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

def _fixture(chiave):
    parti = ["# fixture " + chiave, "x"] + [old for f, lab, old, new in EDITS if f == chiave]
    t = "\n".join(parti) + "\nfine\n"
    return t.replace("\n", "\r\n") if chiave == "sta" else t


def _fixtures():
    return {k: _fixture(k) for k in DOC}


def _registri_sintetici(delta=0.0):
    """Registri minimi coerenti con lo schema; i numeri che producono diventano gli attesi del test."""
    def livelli(dfid, pp, a):
        return {"D_fiducial": dfid, "required_F": None,
                "symmetry": {"a": a, "model_adequate": False},
                "per_point": {p: {"estimate": e, "ci95": [e - 10, e + 10]} for p, e in pp.items()}}
    an = []
    for utc in ("2026-08-31T04:22:36Z", "2026-08-31T12:53:48Z", "2026-09-05T04:20:19Z"):
        for reg, dfid in (("NGC", 8000.0), ("SGC", 4000.0)):
            an.append({"utc": utc, "region": reg, "levels": {
                "k0": livelli(dfid, {"B1": 100.0 + delta, "B2": -50.0}, -1000.0),
                "k1": livelli(dfid, {"B1": 60.0, "B2": -20.0}, -2000.0)}})
    bu = [{"utc": "2026-09-06T18:29:40Z", "region": reg, "levels": {
        "k0": {"unattributed_rms": u0}, "k3": {"unattributed_rms": u3}}}
        for reg, u0, u3 in (("NGC", 50.0, 40.0), ("SGC", 40.0, 60.0))]
    da = [{"point": p, "region": r, "F_ap": f} for p, f in (("B1", 0.97107), ("B6", 1.045531810025433))
          for r in ("NGC", "SGC")]
    fo = {"fa_sha256": "f" * 64, "casi": {
        "NGC_k2": {"chi2_mock": 6.8, "limite": 11.34}, "SGC_k2": {"chi2_mock": 1.3, "limite": 11.34},
        "NGC_k3": {"chi2_mock": 12.4, "limite": 11.34}, "SGC_k3": {"chi2_mock": 16.6, "limite": 11.34}}}
    b1 = {"esito": {"eccesso_dD": 135.868, "parte_mock": 141.868, "parte_dati": -6, "verificata": False}}
    j = lambda rs: "\n".join(json.dumps(r) for r in rs) + "\n"
    return j(an), j(bu), j(da), json.dumps(fo), json.dumps(b1)


def _con_attesi(attesi, fn):
    global ATTESI
    salva = ATTESI
    ATTESI = attesi
    try:
        return fn()
    finally:
        ATTESI = salva


def _calcola_sintetici(delta=0.0):
    """Numeri dai registri sintetici, senza confronto: un finto atteso cattura il dizionario."""
    an, bu, da, fo, b1 = _registri_sintetici(delta)
    catturato = {}

    class _Cattura(dict):
        def __ne__(self, altro):
            catturato.update(altro)
            return False
    _con_attesi(_Cattura(), lambda: numeri_registri(an, bu, da, fo, b1, "f" * 64))
    return dict(catturato)


def _t_ancora_mancante():
    fx = _fixtures()
    fx["mod"] = fx["mod"].replace(O_M2, "niente\n")
    try:
        costruisci(fx, ATTESI, "24 settembre 2026", "a" * 8, "b" * 8, 1)
    except PatchError as e:
        return "M2" in str(e)
    return False


def _t_ancora_doppia():
    fx = _fixtures()
    fx["chk"] += O_C8
    try:
        costruisci(fx, ATTESI, "24 settembre 2026", "a" * 8, "b" * 8, 1)
    except PatchError as e:
        return "2 volte" in str(e)
    return False


def _t_terminatori():
    out, _ = costruisci(_fixtures(), ATTESI, "24 settembre 2026", "a" * 8, "b" * 8, 12)
    s = out["sta"]
    ok = s.count("\r\n") == s.count("\n") and all("\r" not in out[k] for k in ("chk", "sme", "mod", "inv"))
    try:
        eol_di("a\r\nb\n")
    except PatchError:
        return ok
    return False


def _t_catena_completa():
    out, fatte = costruisci(_fixtures(), ATTESI, "24 settembre 2026", "a" * 8, "b" * 8, 12)
    tutto = "".join(out.values())
    return (len(fatte) == len(EDITS) and not postcondizioni(out, ATTESI)
            and "`aaaaaaaa…`" in out["sta"] and " 12/12 |" in out["sta"]
            and not re.search(r"@[A-Z0-9_]+@", tutto))


def _t_idempotenza():
    out, _ = costruisci(_fixtures(), ATTESI, "24 settembre 2026", "a" * 8, "b" * 8, 1)
    try:
        costruisci(out, ATTESI, "24 settembre 2026", "a" * 8, "b" * 8, 1)
    except PatchError as e:
        return "gia' applicata" in str(e)
    return False


def _t_numeri_sintetici():
    n = _calcola_sintetici()
    an, bu, da, fo, b1 = _registri_sintetici()
    ok = _con_attesi(n, lambda: numeri_registri(an, bu, da, fo, b1, "f" * 64)) == n
    an2, bu2, da2, fo2, b12 = _registri_sintetici(delta=7.0)
    try:
        _con_attesi(n, lambda: numeri_registri(an2, bu2, da2, fo2, b12, "f" * 64))
    except PatchError as e:
        return ok and "diversi dagli attesi" in str(e)
    return False


def _t_passata_mancante():
    an, bu, da, fo, b1 = _registri_sintetici()
    an = "\n".join(r for r in an.splitlines() if "SGC" not in r or "2026-09-05" not in r) + "\n"
    try:
        _con_attesi(None, lambda: numeri_registri(an, bu, da, fo, b1, "f" * 64))
    except PatchError as e:
        return "una passata NGC e una SGC" in str(e)
    return False


def _t_fa_sha():
    an, bu, da, fo, b1 = _registri_sintetici()
    try:
        _con_attesi(None, lambda: numeri_registri(an, bu, da, fo, b1, "0" * 64))
    except PatchError as e:
        return "fa_sha256" in str(e)
    return False


def _t_inviluppo():
    an, bu, da, fo, b1 = _registri_sintetici()
    da = da.replace("1.045531810025433", "1.03")
    try:
        _con_attesi(None, lambda: numeri_registri(an, bu, da, fo, b1, "f" * 64))
    except PatchError as e:
        return "non racchiude" in str(e)
    return False


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
    ("catena completa su fixture: 19 modifiche, postcondizioni, nessun token residuo", _t_catena_completa),
    ("seconda applicazione -> errore esplicito", _t_idempotenza),
    ("numeri da registri sintetici = attesi; un valore alterato -> errore", _t_numeri_sintetici),
    ("passata di un emisfero mancante -> errore", _t_passata_mancante),
    ("fa_sha256 diverso dallo sha dello strumento -> errore", _t_fa_sha),
    ("linea B che non racchiude l'inviluppo -> errore", _t_inviluppo),
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
    return fallite


def prepara():
    radice_ok()
    if not selftest(verboso=False):
        raise PatchError("selftest non superato: lanciare 'selftest' per il dettaglio")
    fallite = precondizioni()
    if fallite:
        raise PatchError("precondizioni:\n  " + "\n  ".join(fallite))
    n = numeri_registri(leggi(REG["analisi"]), leggi(REG["budget"]), leggi(REG["dati"]),
                        leggi(REG["forma"]), leggi(REG["b1"]), sha_file(REG["fa_py"])[0])
    oggi = datetime.date.today()
    data = data_it(oggi)
    tex8 = PRE[J(P2, "MNRAS", "paper2_mnras.tex")][0][:8]
    bib8 = PRE[J(P2, "MNRAS", "paper2.bib")][0][:8]
    testi = {k: leggi(p) for k, p in DOC.items()}
    out, fatte = costruisci(testi, n, data, tex8, bib8, len(TESTS))
    return {"oggi": oggi, "data": data, "n": n, "fatte": fatte, "out": out}


def stampa(r, scritto):
    print("precondizioni: %d/%d PASS (sha e byte)" % (len(PRE), len(PRE)))
    print("selftest: %d/%d PASS" % (len(TESTS), len(TESTS)))
    print("data dall'orologio: %s%s" % (r["data"], "" if r["oggi"] == DATA_DECISIONI else
                                         "  (attenzione: diversa dal 24 set delle decisioni)"))
    n = r["n"]
    print("numeri dai registri = attesi: D-1 %s–%s %% (IC95 %s %%); fattore ritirato %s–%s / %s–%s; D-7 x%s / x%s"
          % (n["D1_MIN"], n["D1_MAX"], n["D1_CI_MAX"], n["F5"][0], n["F5"][1], n["F6"][0], n["F6"][1],
             n["D7"]["NGC"][2], n["D7"]["SGC"][2]))
    print("modifiche: %d/%d ancore trovate una volta sola" % (len(r["fatte"]), len(EDITS)))
    for k, p in DOC.items():
        h, b = sha_testo(r["out"][k])
        print("%s: %s -> %s byte, sha %s…" % (os.path.basename(p), migliaia(PRE[p][1]), migliaia(b), h[:12]))
    print("postcondizioni: PASS")
    print("ESITO: %s" % ("APPLICATA" if scritto else "DRY-RUN, nessun file scritto"))


def cmd_apply():
    r = prepara()
    scrivi_atomico({DOC[k]: r["out"][k] for k in DOC}, BACKUP)
    uscite = {}
    for p in DOC.values():
        h, n = sha_file(p)
        uscite[p] = {"sha256": h, "byte": n}
    ric = {"strumento": "paper2_patch_revisione_24set_c.py", "data": r["data"],
           "ingressi": {p: {"sha256": s, "byte": b} for p, (s, b) in PRE.items()},
           "uscite": uscite, "modifiche": r["fatte"], "numeri": r["n"],
           "selftest": "%d/%d" % (len(TESTS), len(TESTS))}
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
    for p in list(REG.values()) + [J("src", "paper2_v1_amendments.jsonl")]:
        scarti += confronta_ricevuta({p: ric["ingressi"][p]})
    testi = {k: leggi(p) for k, p in DOC.items()}
    scarti += postcondizioni(testi, ric["numeri"])
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

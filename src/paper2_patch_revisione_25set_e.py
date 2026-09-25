#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_revisione_25set_e.py -- passata documentaria del 25 settembre 2026, chiusura di sessione.

Porta nei documenti il §6 e il §7.1 scritti, e la correzione del vincolo su w0:
  * checklist rev. 3.38 -> 3.39: blocco del §6 e del §7.1 nella «Struttura», rimandi al Paper 1 del
    §7.1, testo deciso delle limitazioni corretto (punto 10), D4 e D5 annotate;
  * stato dalla 22a alla 23a revisione: paragrafo, righe del par. 0, quattro voci aperte nuove,
    strumento nel par. 9;
  * modifiche_paper1.md: data della riga della passata d corretta; riga nuova.

Il vincolo su w0 in SGC (5.71) divide per SIGMA_TOT = 313.0, la dispersione di NGC: il patcher lo
ricalcola dai registri compD e dalla costante dello strumento, e verifica che il manoscritto porti il
valore con la dispersione di SGC. I tre documenti devono essere quelli lasciati dalla passata d (ricevuta).
Nessun record nuovo nel ledger: il protocollo non cambia.

Sequenza: selftest -> dry-run -> apply -> verify. Comandi dalla radice del repository.
"""
import argparse
import datetime
import glob
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
    "tex": J(P2, "MNRAS", "paper2_mnras.tex"),
    "bib": J(P2, "MNRAS", "paper2.bib"),
    "compd_py": J("src", "paper2_compD_partialcorr.py"),
    "ledger": J("src", "paper2_v1_amendments.jsonl"),
}
COMPD_SHA = {
    "NGC": ("23f86735022b5c345229f689ba0f24931470d0d16ef50b18210d242b703de1dd", 12010),
    "SGC": ("ee7648f34826a04c468de02a6fd1d73de9295ee284a19e4345be174dc25c90b6", 12010),
}
RICEVUTA_D = J("logs", "patch_revisione_24set_d.json")
RICEVUTA = J("logs", "patch_revisione_25set_e.json")
BACKUP = J("logs", "patch_revisione_25set_e_backup")

PRE = {
    DOC["chk"]: ("a37075f5ba4e9554e6ca20b1707f89fe88b2506ce0ad9b5a5a24892a6e751653", 298007),
    REG["tex"]: ("934b31a28e808cb3e07f6e048e9d8fad0a00d1f9e3a3e40db92d44eecb06f25b", 76125),
    REG["bib"]: ("8d1d4016e85beaa8e17098af7915c8e4bff8236504b80f93117e1c4fa05d9758", 12613),
    REG["compd_py"]: ("9321d7ec04845fbd40aff0f6356cae8d67599a936bb5569f4613f2b6061d873b", 26442),
    REG["ledger"]: ("fb70459fca476145a791407e3bd1f5bd82f0dbc04e3f3d250309930bcf3f20a5", 663194),
}

# Dispersione per realizzazione di ciascuna calotta: budget, riga B0 (mock_baseline_std di paper1_remap),
# la stessa che lo strumento dichiara in FROZEN[...]["sd"].
SD_CALOTTA = {"NGC": 312.989, "SGC": 197.787}
SIGMA_TOT_STRUMENTO = 313.0      # costante unica dello strumento, di NGC
PAROLE = {5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
PAROLE_IT = {5: "cinque", 6: "sei", 7: "sette", 8: "otto", 9: "nove", 10: "dieci"}

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]
MESI_BREVI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
DATA_DECISIONI = datetime.date(2026, 9, 25)

ATTESI = {
    "SL_N": "100.1", "SL_S": "54.8", "SIG_N": "3.13", "SIG_S_REC": "5.71", "SIG_S": "3.61",
    "VOLTE_N": "five", "VOLTE_S": "six", "R2_N": "0.261", "R2_S": "0.277", "SPAN": "0.600",
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


def _compd(testo, reg):
    """Riga w0 e R^2: identiche in tutti i record del registro (lettura per unione)."""
    recs = [r for r in _jsonl(testo, "compD_" + reg) if "rows" in r]
    if not recs:
        raise PatchError("compD_%s: nessun record con le righe" % reg)
    vis = set()
    for r in recs:
        w = [x for x in r["rows"] if x.get("param") == "w0"]
        if len(w) != 1:
            raise PatchError("compD_%s: riga w0 assente o ripetuta" % reg)
        w = w[0]
        vis.add((r["n"], r["r2_multi"], r["r2_ceiling"], w["r_raw"], w["slope_gen_per_unit"], w["span"],
                 r["w0_sigma1_implied"]))
    if len(vis) != 1:
        raise PatchError("compD_%s: i record non concordano sui campi letti (%d varianti)" % (reg, len(vis)))
    n, r2, ceil, r_raw, slope, span, sig_rec = vis.pop()
    if n != 2000:
        raise PatchError("compD_%s: n = %r, attesi 2000" % (reg, n))
    return {"r2": r2, "ceil": ceil, "r_raw": r_raw, "slope": slope, "span": span, "sig_rec": sig_rec}


def numeri(t_compd, t_py):
    """Gettoni e controlli sul tex, dai registri compD e dal sorgente dello strumento."""
    if "SIGMA_COS, SIGMA_FIXED, SIGMA_TOT = 261.5, 172.0, 313.0" not in t_py:
        raise PatchError("paper2_compD_partialcorr.py: le costanti di NGC non sono quelle attese")
    if 'sig1 = (SIGMA_TOT / abs(rw["slope_gen_per_unit"]))' not in t_py:
        raise PatchError("paper2_compD_partialcorr.py: il vincolo non e' calcolato come atteso")
    c = {reg: _compd(t_compd[reg], reg) for reg in ("NGC", "SGC")}
    for reg in c:
        if abs(c[reg]["sig_rec"] - SIGMA_TOT_STRUMENTO / abs(c[reg]["slope"])) > 1e-9:
            raise PatchError("compD_%s: il vincolo registrato non e' 313.0 / pendenza" % reg)
        if abs(c[reg]["ceil"] - (261.5 / 313.0) ** 2) > 1e-12:
            raise PatchError("compD_%s: il tetto registrato non e' quello di NGC" % reg)
    sig = {reg: SD_CALOTTA[reg] / abs(c[reg]["slope"]) for reg in c}
    volte = {reg: int(round(sig[reg] / c[reg]["span"])) for reg in c}
    if any(v not in PAROLE for v in volte.values()):
        raise PatchError("rapporti vincolo / intervallo fuori tabella: %r" % volte)
    tok = {
        "SL_N": "%.1f" % c["NGC"]["slope"], "SL_S": "%.1f" % c["SGC"]["slope"],
        "SIG_N": "%.2f" % sig["NGC"], "SIG_S_REC": "%.2f" % c["SGC"]["sig_rec"], "SIG_S": "%.2f" % sig["SGC"],
        "VOLTE_N": PAROLE[volte["NGC"]], "VOLTE_S": PAROLE[volte["SGC"]],
        "VOLTE_N_IT": PAROLE_IT[volte["NGC"]], "VOLTE_S_IT": PAROLE_IT[volte["SGC"]],
        "R2_N": "%.3f" % c["NGC"]["r2"], "R2_S": "%.3f" % c["SGC"]["r2"], "SPAN": "%.3f" % c["NGC"]["span"],
        "SIG_N_1": "%.1f" % sig["NGC"], "SIG_S_1": "%.1f" % sig["SGC"],
    }
    diff = [k for k in ATTESI if tok.get(k) != ATTESI[k]]
    if diff:
        raise PatchError("numeri ricalcolati diversi dagli attesi in %r: %r" % (diff, {k: tok.get(k) for k in diff}))
    frase = ("%.1f in NGC and %.1f in SGC, %s and %s times"
             % (sig["NGC"], sig["SGC"], tok["VOLTE_N"], tok["VOLTE_S"]))
    chk = [("%.0f generators per unit $w_0$ in NGC and %.0f in SGC" % (c["NGC"]["slope"], c["SGC"]["slope"]), 1),
           (frase, 2),
           ("%s in NGC and %s in SGC, 37 and 40 per cent" % (tok["R2_N"], tok["R2_S"]), 1),
           ("the SGC fractions below assume the same shares", 1),
           ("%.1f in SGC" % c["SGC"]["sig_rec"], 0),
           (r"about $\pm 0.6$", 0)]
    return tok, chk


def controlla_tex(tex, chk):
    t = re.sub(r"\s+", " ", tex)
    return ["%r compare %d volte, attese %d" % (s, t.count(re.sub(r"\s+", " ", s)), k)
            for s, k in chk if t.count(re.sub(r"\s+", " ", s)) != k]


# ----------------------------------------------------------------------------- testi: checklist (LF)

O_C1 = "\n### rev. 3.38 — 25 settembre 2026 — **il §5 scritto"
T_C1 = (
    "\n### rev. 3.39 — @DATA@ — **il §6 e il §7.1 scritti; il vincolo su *w*₀ corretto due volte.** §6"
    " (risposta ai parametri di nwLH, Tabella 1 delle correlazioni parziali, tetti di *R*²) e §7.1"
    " (Tabella 2 del budget, riga 11 a due basi per decisione del 25 set). Il testo deciso delle"
    " limitazioni portava il ±0.6 del canovaccio: sostituito dal misurato (decisione del 25 set); e il"
    " misurato di SGC, ±@SIG_S_REC@, divide per la dispersione di NGC: con quella di SGC vale ±@SIG_S@. I"
    " tetti di *R*² di SGC sono quelli della scomposizione di NGC, e il §6.3 lo dice. Normalizzazione di F7"
    " decisa. Nessun record nuovo: il protocollo non cambia."
    + O_C1
)

O_C2 = ("      questione CPL e il prodotto citabile per chiunque proponga statistiche topologiche per\n"
        "      vincolare la cosmologia.\n")
T_C2 = O_C2 + (
    "      **✦ rev. 3.39 — il ±@SIG_S_REC@ di SGC è sbagliato.** `paper2_compD_partialcorr.py` (righe 502–513)\n"
    "      calcola il vincolo come `SIGMA_TOT / |pendenza|`, con `SIGMA_TOT = 313.0`, la dispersione di NGC,\n"
    "      anche in SGC: con quella di SGC, 197.787, vale **±@SIG_S@**, e i due vincoli sono @VOLTE_N_IT@ e @VOLTE_S_IT@\n"
    "      volte l'intervallo campionato di *w*₀ (@SPAN@), non «52× e 95×» un numero BAO. La pendenza viene\n"
    "      dalla *r* **grezza** (@SL_N@ e @SL_S@ generatori per unità di *w*₀), non dalla parziale. Il «±0.06\n"
    "      di BAO DESI» è una stringa dello strumento senza fonte: il manoscritto non lo usa. Il record 43\n"
    "      riporta «±3.13 and ±5.71» e non si riscrive; lo strumento non si rilancia (Z-sigma-SGC).\n"
)

O_C3 = ("Non spiegato: il **62.7%** e **60.3% della\n"
        "      varianza cosmologica**.\n")
T_C3 = O_C3 + (
    "      **✦ rev. 3.39:** il tetto 0.698 di SGC è quello di NGC: lo strumento ha `SIGMA_COS`, `SIGMA_TOT`\n"
    "      e `R2_CEILING` come costanti uniche, e la scomposizione di M26 è misurata in NGC. La dispersione\n"
    "      di SGC non è scomposta; il §6.3 lo dichiara, e lo stesso vale per lo 0.832 di D6.\n"
)

O_C4 = "about ±0.6, an order of magnitude weaker than DESI BAO"
T_C4 = ("~~about ±0.6, an order of magnitude weaker than DESI BAO~~ **[rev. 3.39, deciso il 25 set: half-width"
        " is @SIG_N_1@ in NGC and @SIG_S_1@ in SGC, @VOLTE_N@ and @VOLTE_S@ times the range the suite samples]**")

O_C5 = "due serie differiscono nell'ultima cifra (25.4 contro 25.46, 27.1 contro 27.19) |\n"
T_C5 = O_C5 + (
    "| §7.1 (rev. 3.39) | riga 5, NFW: −56.5 ± 23.5 | Paper 1 §7.1 | **P1-14** tocca la stessa frase («47 per"
    " cent»), non il numero |\n"
    "| §7.1 (rev. 3.39) | riga 9, residuo di maschera ±11.9 % | Paper 1 §8.2 | **P1-12** |\n"
    "| §7.1 (rev. 3.39) | riga 10, 31.2 % al P25 di SGC | Paper 1 §7.1 | **P1-8** |\n"
    "| §7.1 (rev. 3.39) | riga AP della Tab. 8, «amplitude in preparation» | Paper 1 Tab. 8 | **P1-13** |\n"
    "| §6, §7.1 (rev. 3.39) | selezione dei mock (§4), scomposizione e correlazioni grezze (§5.5), −0.015 e"
    " [−1050, +929] (§5.5), 1.44 e rapporto 0.97 (§5.6), crescita (§7), +309 (§5.3) | M26 | concordi; la riga"
    " 11 porta anche il 4.30 % di *D* (decisione del 25 set: due basi, M26 non commentato) |\n"
)

O_C6 = ("  manoscritto si ancora come i documenti, per sha.\n"
        "\n1. Introduzione:")
T_C6 = (
    "  manoscritto si ancora come i documenti, per sha.\n"
    "\n"
    "**✦ rev. 3.39 — il §6 e il §7.1, scritti il 25 set.** `paper2_mnras.tex` `@TEX8@…` (@TEXB@ byte);\n"
    "18 note di stesura, 10 pagine, zero errori; in modalità finale restano solo le note e le 8 figure\n"
    "mancanti. Dei testi decisi sette sono identici e uno, le limitazioni, è corretto come dichiarato qui.\n"
    "\n"
    "- **§6.1.** Il meccanismo prima dei numeri (campionamento del cut-sky, Prop. 1); la scomposizione di M26\n"
    "  §5.5; **Tabella 1**, correlazioni parziali a *n* = 2000 da `compD_{NGC,SGC}.jsonl` (*n*_s +0.398 e\n"
    "  +0.416); tre limiti: calotte non indipendenti, σ₈ non nullo, un ordinamento non è un vincolo.\n"
    "- **§6.2.** *w*₀: il −0.015 di M26 (200 mock) contro +0.055 / +0.047 (2000, sei parametri); P1\n"
    "  ritirata come falsificazione; pendenza @SL_N@ / @SL_S@ dalla *r* grezza, dentro l'intervallo di M26;\n"
    "  vincolo ±@SIG_N@ / ±@SIG_S@, @VOLTE_N_IT@ e @VOLTE_S_IT@ volte l'intervallo campionato. Poi il testo deciso D8.\n"
    "- **§6.3.** Tetti 0.698 (parametri) e 0.832 (predittori sulla stessa realizzazione), entrambi dalla\n"
    "  scomposizione di NGC; *R*² lineare @R2_N@ / @R2_S@; il kernel ai due lati; metà della varianza\n"
    "  disponibile non spiegata; Q5 regge; i tre limiti del record 63.\n"
    "- **§7.1.** Due capoversi (R1–R5 in prosa, tre letture) e la **Tabella 2** a larghezza di pagina, con la\n"
    "  numerazione del budget. Riga 11: +309, 1.1 % di *N*_DESI e −4.30 % di *D* (decisione del 25 set).\n"
    "  La riga AP della Tab. 8 del Paper 1 è chiusa dalla riga 1.\n"
    "- **§9, testo deciso corretto** (punto 10 qui sotto): il ±0.6 veniva dal canovaccio (stima a *n* = 200\n"
    "  da un limite superiore su *r*), anche nel record 78 E; al suo posto il misurato, col valore di SGC\n"
    "  ricalcolato con la dispersione di SGC; tolto il confronto coi BAO, che non ha fonte.\n"
    "- **F7, normalizzazione decisa il 25 set:** per ogni θ lo spostamento di *N*_H1 sull'intervallo\n"
    "  campionato, diviso per la dispersione per realizzazione **della calotta**; α_iso zero per teorema;\n"
    "  *w*₀ e *M*_ν zero entro la misura. Per i sette parametri, `excursion_gen` di compD (pendenza grezza ×\n"
    "  intervallo), divisa per 312.989 / 197.787 e non per la costante dello strumento. Script da scrivere.\n"
    "\n1. Introduzione:"
)

# ----------------------------------------------------------------------------- testi: stato (CRLF sul disco)

O_S1 = "aggiornato **25 settembre 2026**, ventiduesima revisione"
T_S1 = "aggiornato **@DATA@**, ventitreesima revisione"

O_S2 = ("`papers/` fuori dal versionamento dal 28 agosto: il commit `d14dded` porta solo script e registro di F1\n"
        "· ledger invariato a 78 record.\n")
T_S2 = O_S2 + (
    "\n"
    "**Al 25 settembre (ventitreesima revisione):** **§6 e §7.1 scritti** · `paper2_mnras.tex` `@TEX8@…`,\n"
    "18 note, 10 pagine · **Tabella 1** (correlazioni parziali) e **Tabella 2** (budget, riga 11 a due basi per\n"
    "decisione del 25 set) · **vincolo su *w*₀ corretto due volte**: il ±0.6 del testo deciso delle limitazioni\n"
    "e del record 78 E era la stima del canovaccio; il ±@SIG_S_REC@ di SGC del record 43 e della D4 divide per la\n"
    "dispersione di NGC (`SIGMA_TOT = 313.0` in `paper2_compD_partialcorr.py`): con quella di SGC vale ±@SIG_S@ ·\n"
    "i tetti di *R*² di SGC sono quelli di NGC, dichiarato nel §6.3 · normalizzazione di F7 decisa · ledger\n"
    "invariato a 78 record.\n"
)

O_S3 = "| (24 set, sera) mediana(max δ)/DESI su v1 in SGC | **non in un registro letto**: il 27.80 è NGC |\n"
T_S3 = O_S3 + (
    "| (25 set) vincolo su *w*₀ di `compD` | NGC 312.989 / @SL_N@ = @SIG_N@; SGC registrato @SIG_S_REC@ = 313.0 /"
    " @SL_S@, con la dispersione di SGC **@SIG_S@** |\n"
    "| (25 set) tetto di *R*² registrato in SGC | **0.698 = (261.5 / 313.0)², costante di NGC** |\n"
    "| (25 set) testi decisi dopo §6 e §7.1 | sette identici; le limitazioni corrette come deciso |\n"
)

O_S4 = ("| **Z-nPat-SGC** | l'appaiato SGC dei voxel patologici, −16.45 ± 0.32, non è nel ledger | lettura |"
        " sta in P1-11 e nella 4.2c; il registro va nominato prima che il numero resti nel §5 |\n")
T_S4 = O_S4 + (
    "| **Z-sigma-SGC** | `paper2_compD_partialcorr.py` usa costanti di NGC (`SIGMA_COS`, `SIGMA_TOT`,"
    " `R2_CEILING`, `ATTEN`) anche in SGC: vincolo su *w*₀ ±@SIG_S_REC@ invece di ±@SIG_S@, tetto 0.698 | strumento |"
    " il manoscritto porta i valori giusti e dichiara i tetti; lo strumento non si rilancia finché un numero"
    " del paper non ne dipende. Stessa forma degli errori 37 e 41 |\n"
    "| **Z-w0-78E** | il record 78 E porta «circa ±0.6», stima del canovaccio | ledger | non si riscrive: la"
    " correzione entra nel prossimo record scritto per altre ragioni |\n"
    "| **Z-F7** | la funzione di risposta: script e §7.2 | scrittura | normalizzazione decisa il 25 set"
    " (checklist 3.39); `excursion_gen` di compD divisa per la dispersione della calotta |\n"
    "| **Z-DESI-w0** | un confronto coi vincoli di DESI su *w*₀ | bibliografia | facoltativo; solo con un numero"
    " verificato alla fonte |\n"
)

O_S5 = ("| `paper2_patch_revisione_24set_d.py` | checklist 3.38, questo documento alla 22ª, P1-11; 26 numeri"
        " del §5 e del §4.2 riscontrati su ledger, `d2_v2` e `item15a_g13` | 12/12 |\n")
T_S5 = O_S5 + (
    "| `paper2_patch_revisione_25set_e.py` | checklist 3.39, questo documento alla 23ª; vincolo su *w*₀ ricalcolato"
    " da compD e dal sorgente dello strumento | @NST@/@NST@ |\n"
)

# ----------------------------------------------------------------------------- testi: modifiche_paper1 (LF)

O_M1 = "| 25 set 2026, sera | P1-11: la cella v1 SGC di mediana(max δ)/DESI"
T_M1 = "| 24 set 2026, sera (passata applicata il 25) | P1-11: la cella v1 SGC di mediana(max δ)/DESI"

O_M2 = "| data | cosa |\n|---|---|\n"
T_M2 = O_M2 + (
    "| @DATAB@ | Nessuna voce cambia. Il §7.1 del Paper 2 cita il Paper 1 al §7.1 (riga 5, NFW: P1-14 tocca"
    " la stessa frase, non il numero; riga 10, P1-8), al §8.2 (riga 9, P1-12) e nella Tab. 8 (riga AP,"
    " P1-13); il §6 non lo cita |\n"
)

EDITS = [
    ("chk", "C1 intestazione rev. 3.39", O_C1, T_C1),
    ("chk", "C2 D4: vincolo di SGC", O_C2, T_C2),
    ("chk", "C3 D5: tetto di SGC", O_C3, T_C3),
    ("chk", "C4 punto 10: testo deciso corretto", O_C4, T_C4),
    ("chk", "C5 rimandi del §6 e del §7.1", O_C5, T_C5),
    ("chk", "C6 blocco del §6 e del §7.1", O_C6, T_C6),
    ("sta", "S1 riga 2", O_S1, T_S1),
    ("sta", "S2 ventitreesima revisione", O_S2, T_S2),
    ("sta", "S3 righe del par. 0", O_S3, T_S3),
    ("sta", "S4 voci aperte nuove", O_S4, T_S4),
    ("sta", "S5 strumento nel par. 9", O_S5, T_S5),
    ("mod", "M1 data della passata d", O_M1, T_M1),
    ("mod", "M2 registro delle modifiche", O_M2, T_M2),
]


def postcondizioni(testi):
    attese = [
        ("chk", "### rev. 3.39 —", 1),
        ("chk", "**✦ rev. 3.39 — il §6 e il §7.1, scritti il 25 set.**", 1),
        ("chk", "~~about ±0.6, an order of magnitude weaker than DESI BAO~~", 1),
        ("chk", "| §7.1 (rev. 3.39) |", 4),
        ("sta", "ventitreesima revisione", 2),
        ("sta", "`paper2_patch_revisione_25set_e.py`", 1),
        ("sta", O_S1, 0),
        ("sta", "| **Z-sigma-SGC** |", 1),
        ("mod", O_M1, 0),
        ("mod", "il §6 non lo cita", 1),
    ]
    return ["%s: %r compare %d volte, attese %d" % (f, s, testi[f].count(s), k)
            for f, s, k in attese if testi[f].count(s) != k]


def costruisci(testi, tok):
    if "### rev. 3.39" in testi["chk"] or "ventitreesima revisione" in testi["sta"]:
        raise PatchError("passata gia' applicata (marcatori della rev. 3.39 o della 23a presenti)")
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
    t.update({"SIG_N_1": "3.1", "SIG_S_1": "3.6", "VOLTE_N_IT": "cinque", "VOLTE_S_IT": "sei", "DATA": "25 settembre 2026", "DATAB": "25 set 2026",
              "TEX8": "a" * 8, "TEXB": "1", "NST": "11"})
    return t


def _fixtures():
    out = {}
    for chiave in DOC:
        parti = ["# fixture " + chiave, "x"] + [old for f, lab, old, new in EDITS if f == chiave]
        t = "\n".join(parti) + "\nfine\n"
        out[chiave] = t.replace("\n", "\r\n") if chiave == "sta" else t
    return out


PY_FINTO = ('SIGMA_COS, SIGMA_FIXED, SIGMA_TOT = 261.5, 172.0, 313.0\n'
            '        sig1 = (SIGMA_TOT / abs(rw["slope_gen_per_unit"])) if x else y\n')


def _compd_sintetico(reg, slope=None, righe=2):
    s = {"NGC": 100.097, "SGC": 54.846}[reg] if slope is None else slope
    r2 = {"NGC": 0.2605774, "SGC": 0.2772825}[reg]
    rec = {"n": 2000, "r2_multi": r2, "r2_ceiling": (261.5 / 313.0) ** 2, "w0_sigma1_implied": 313.0 / s,
           "rows": [{"param": "n_s"}, {"param": "w0", "r_raw": 0.05, "slope_gen_per_unit": s, "span": 0.5997}]}
    return "\n".join(json.dumps(rec) for _ in range(righe)) + "\n"


def _tex_sintetico(chk):
    return "\n".join(s.replace(" ", "\n", 1) + " " for s, k in chk for _ in range(k)) + "\n"


def _t_ancora_mancante():
    fx = _fixtures()
    fx["mod"] = fx["mod"].replace(O_M1, "niente")
    try:
        costruisci(fx, _gettoni_finti())
    except PatchError as e:
        return "M1" in str(e)
    return False


def _t_ancora_doppia():
    fx = _fixtures()
    fx["chk"] += O_C4
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
    return (len(fatte) == len(EDITS) and not postcondizioni(out) and " 11/11 |" in out["sta"]
            and not re.search(r"@[A-Z0-9_]+@", tutto))


def _t_idempotenza():
    out, _ = costruisci(_fixtures(), _gettoni_finti())
    try:
        costruisci(out, _gettoni_finti())
    except PatchError as e:
        return "gia' applicata" in str(e)
    return False


def _t_numeri_attesi():
    tok, chk = numeri({r: _compd_sintetico(r) for r in ("NGC", "SGC")}, PY_FINTO)
    return all(tok[k] == v for k, v in ATTESI.items()) and tok["SIG_S_1"] == "3.6" and len(chk) == 6


def _t_tex_riscontro():
    tok, chk = numeri({r: _compd_sintetico(r) for r in ("NGC", "SGC")}, PY_FINTO)
    tex = _tex_sintetico(chk)
    if controlla_tex(tex, chk):
        return False
    manc = controlla_tex(tex + " 5.7 in SGC ", chk)
    return len(manc) == 1 and "5.7 in SGC" in manc[0]


def _t_costante_cambiata():
    try:
        numeri({r: _compd_sintetico(r) for r in ("NGC", "SGC")}, PY_FINTO.replace("313.0", "312.989"))
    except PatchError as e:
        return "costanti" in str(e)
    return False


def _t_record_discordi():
    t = _compd_sintetico("SGC") + _compd_sintetico("SGC", slope=55.0, righe=1)
    try:
        numeri({"NGC": _compd_sintetico("NGC"), "SGC": t}, PY_FINTO)
    except PatchError as e:
        return "non concordano" in str(e)
    return False


TESTS = [
    ("ancora mancante -> errore col nome della modifica", _t_ancora_mancante),
    ("ancora doppia -> errore", _t_ancora_doppia),
    ("terminatori: CRLF dello stato e LF degli altri conservati; misti -> errore", _t_terminatori),
    ("catena completa su fixture: 13 modifiche, postcondizioni, nessun token residuo", _t_catena_completa),
    ("seconda applicazione -> errore esplicito", _t_idempotenza),
    ("numeri da registri sintetici = attesi dichiarati", _t_numeri_attesi),
    ("riscontro sul tex: tutto presente; il 5.7 residuo -> errore", _t_tex_riscontro),
    ("costante dello strumento diversa da quella letta -> errore", _t_costante_cambiata),
    ("record di compD discordi -> errore", _t_record_discordi),
]


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



TESTS += [
    ("scrittura atomica: errore sul secondo file lascia intatto il primo", _t_atomicita),
    ("verify rileva uno sha diverso dalla ricevuta", _t_verify),
]


def trova_compd():
    trov = {}
    for reg in ("NGC", "SGC"):
        c = sorted(set(glob.glob(J("results", "**", "compD_%s.jsonl" % reg), recursive=True)))
        if len(c) != 1:
            raise PatchError("compD_%s.jsonl: trovati %d file sotto results/ (atteso 1): %r" % (reg, len(c), c))
        trov[reg] = c[0]
    return trov


def precondizioni():
    fallite = []
    for p, (sha, size) in PRE.items():
        if not os.path.exists(p):
            fallite.append("%s: assente" % p)
            continue
        h, n = sha_file(p)
        if h != sha or n != size:
            fallite.append("%s: %s… %d byte, atteso %s… %d" % (p, h[:12], n, sha[:12], size))
    try:
        cp = trova_compd()
        for reg, p in cp.items():
            h, n = sha_file(p)
            if (h, n) != COMPD_SHA[reg]:
                fallite.append("%s: %s… %d byte, atteso %s… %d" % (p, h[:12], n, COMPD_SHA[reg][0][:12],
                                                                  COMPD_SHA[reg][1]))
    except PatchError as e:
        fallite.append(str(e))
    if not os.path.exists(RICEVUTA_D):
        fallite.append("%s: assente (serve a dire che i documenti sono quelli della passata d)" % RICEVUTA_D)
    else:
        with open(RICEVUTA_D, encoding="utf-8") as fh:
            usc = json.load(fh)["uscite"]
        mancano = [DOC[k] for k in DOC if DOC[k] not in usc]
        fallite += ["%s: non fra le uscite della ricevuta d" % p for p in mancano]
        fallite += ["dopo la passata d, " + s for s in confronta_ricevuta({DOC[k]: usc[DOC[k]] for k in DOC
                                                                             if DOC[k] in usc})]
    return fallite


def prepara():
    radice_ok()
    if not selftest(verboso=False):
        raise PatchError("selftest non superato: lanciare 'selftest' per il dettaglio")
    fallite = precondizioni()
    if fallite:
        raise PatchError("precondizioni:\n  " + "\n  ".join(fallite))
    cp = trova_compd()
    tok, chk = numeri({reg: leggi(p) for reg, p in cp.items()}, leggi(REG["compd_py"]))
    manc = controlla_tex(leggi(REG["tex"]), chk)
    if manc:
        raise PatchError("manoscritto non coerente coi registri (%d su %d):\n  %s"
                         % (len(manc), len(chk), "\n  ".join(manc)))
    oggi = datetime.date.today()
    data = data_it(oggi)
    tok.update({"DATA": data, "DATAB": "%d %s %d" % (oggi.day, MESI_BREVI[oggi.month - 1], oggi.year),
                "TEX8": PRE[REG["tex"]][0][:8], "TEXB": migliaia(PRE[REG["tex"]][1]), "NST": str(len(TESTS))})
    testi = {k: leggi(p) for k, p in DOC.items()}
    pre_doc = {DOC[k]: sha_testo(testi[k]) for k in DOC}
    out, fatte = costruisci(testi, tok)
    return {"oggi": oggi, "data": data, "tok": tok, "nchk": len(chk), "fatte": fatte, "out": out,
            "pre_doc": pre_doc, "compd": cp}


def stampa(r, scritto):
    print("precondizioni: %d/%d PASS (sha e byte) + compD 2/2 + documenti = uscite della passata d" % (len(PRE), len(PRE)))
    print("selftest: %d/%d PASS" % (len(TESTS), len(TESTS)))
    print("data dall'orologio: %s%s" % (r["data"], "" if r["oggi"] == DATA_DECISIONI else
                                         "  (attenzione: diversa dal 25 set)"))
    t = r["tok"]
    print("compD: pendenze %s / %s; vincolo NGC %s; SGC registrato %s = 313.0 / pendenza, con la dispersione di SGC %s;"
          " %s e %s volte l'intervallo" % (t["SL_N"], t["SL_S"], t["SIG_N"], t["SIG_S_REC"], t["SIG_S"],
                                           t["VOLTE_N_IT"], t["VOLTE_S_IT"]))
    print("manoscritto coerente coi registri: %d/%d controlli" % (r["nchk"], r["nchk"]))
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
    for reg, p in r["compd"].items():
        ingressi[p] = {"sha256": COMPD_SHA[reg][0], "byte": COMPD_SHA[reg][1]}
    ric = {"strumento": "paper2_patch_revisione_25set_e.py", "data": r["data"],
           "ingressi": ingressi, "uscite": uscite, "modifiche": r["fatte"], "gettoni": r["tok"],
           "controlli_tex": r["nchk"], "selftest": "%d/%d" % (len(TESTS), len(TESTS))}
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

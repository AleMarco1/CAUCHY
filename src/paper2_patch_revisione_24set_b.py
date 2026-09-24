#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_revisione_24set_b.py -- seconda passata documentaria del 24 settembre 2026.

checklist rev. 3.35 -> 3.36 e stato dalla 19a alla 20a revisione:
  * struttura del manoscritto, titolo di lavoro, abstract, ordine di stesura, sorgenti in MNRAS/;
  * rimandi degli otto testi decisi della Fase 7, verificati;
  * tre numeri corretti nel testo delle limitazioni (Fase 7, punto 10), RICALCOLATI dal budget;
  * ancore di SGC nel par. 2.3; censimento dei registri dopo il record 78; ancore misurate.

Nessun record nuovo nel ledger: il protocollo non cambia. Il ledger e' fra le precondizioni.

Sequenza: selftest -> dry-run -> apply -> verify. Comandi dalla radice del repository.
Regole: ogni ancora compare una volta sola (altrimenti errore); i due documenti si scrivono
insieme o nessuno; terminatori di riga ereditati dal file (lo stato e' CRLF, la checklist LF);
le date si leggono dall'orologio; ogni file citato con un digest e' misurato, non trascritto.
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
CHK = J("papers", "paper2", "checklist_paper2.md")
STA = J("papers", "paper2", "paper2_stato.md")
BUD = J("papers", "paper2", "paper2_budget_5_1.md")
CENS = J("logs", "censimento_v17.jsonl")
RICEVUTA = J("logs", "patch_revisione_24set_b.json")
BACKUP = J("logs", "patch_revisione_24set_b_backup")

# Precondizioni: (sha256, byte). Misurate il 24 set (Get-FileHash e sandbox).
PRE = {
    CHK: ("d4fcdb963229992bf2df653133d2d5c6859acb8206fc5a9629e8a12155e09b6d", 279564),
    STA: ("c99be01367c400745b7e6604b09ab9610e288b8c8e052483e76ae5456c5e8454", 112752),
    BUD: ("0c7eef5b083cc443bc26cff9488164d21b13e00b46731f491ee85ec52e9427a7", 28066),
    J("papers", "paper2", "paper2_5_5_smentite.md"):
        ("82b2878d001509f837609ebfef588c334353de1e11bec175ffb53bc3d1efb44c", 15129),
    J("papers", "paper2", "canovaccio_paper4.md"):
        ("e25cc888aaad07b66882f16e11084b1c1787b58189b4403b8b53f3a8a26313ec", 9554),
    J("logs", "censimento_rilascio_78.jsonl"):
        ("44c58bdb80569edd547c7c987a6393979b15579e9bce1025259f3e77d25fbb5d", 35141),
    J("logs", "censimento_rilascio_78b.jsonl"):
        ("7145ac574145112aa0b8c576c122090c0f8d31a770c3932b31820b20c4a15e00", 35044),
    J("papers", "paper2", "MNRAS", "mnras.cls"):
        ("ece8db40940f3d0230f9a6029e9291e32c57f5bc965b35c6cb927f6658049002", 62877),
    J("papers", "paper2", "MNRAS", "mnras.bst"):
        ("8dd7405398edf44e97c055b1e5b9b5ba1420102f1315dbf22d23c06f0d56f314", 43376),
    J("src", "paper2_v1_amendments.jsonl"):
        ("fb70459fca476145a791407e3bd1f5bd82f0dbc04e3f3d250309930bcf3f20a5", 663194),
}

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]
DATA_DECISIONI = datetime.date(2026, 9, 24)

# Numeri del testo delle limitazioni: attesi dichiarati qui, ricalcolati dal budget.
BUDGET_ANCORE = [
    "| NGC | 35 436.686 | 28 256 | **7 180.686** |",
    "NGC −56.5 ± 23.5, 40 coppie",
    "−53 ± 112 per unità di *z*, Δ*z* ≈ 0.25",
    "97.25/*D* = 1.354 %",
    "127/*D* = 1.769 %",
]
ATTESI = {"P6": "1.4", "P6X": "1.354", "P5": "1.8", "P5X": "1.769", "C5": "0.8", "E5": "0.3",
          "SIG5": "2.4"}


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


def numeri_budget(bud):
    for a in BUDGET_ANCORE:
        if bud.count(a) != 1:
            raise PatchError("budget: ancora %r trovata %d volte (attesa 1)" % (a, bud.count(a)))
    D = 7180.686
    d5, s5 = 56.5, 23.5            # riga 5, profilo dei satelliti, NGC
    g, sg, dz = 53.0, 112.0, 0.25  # riga 6, crescita per unita' di z, e Delta z
    lim5 = d5 + 3 * s5
    lim6 = g * dz + 3 * sg * dz
    if abs(lim5 - 127.0) > 1e-9 or abs(lim6 - 97.25) > 1e-9:
        raise PatchError("limiti ricalcolati diversi da 127 e 97.25: %r %r" % (lim5, lim6))
    r = {
        "P6": "%.1f" % (100 * lim6 / D), "P6X": "%.3f" % (100 * lim6 / D),
        "P5": "%.1f" % (100 * lim5 / D), "P5X": "%.3f" % (100 * lim5 / D),
        "C5": "%.1f" % (100 * d5 / D), "E5": "%.1f" % (100 * s5 / D),
        "SIG5": "%.1f" % (d5 / s5),
    }
    if r != ATTESI:
        raise PatchError("numeri ricalcolati %r diversi dagli attesi %r" % (r, ATTESI))
    return r


# ----------------------------------------------------------------------------- testi

T_REV = (
    "\n### rev. 3.36 — @DATA@ — **la scrittura comincia.** Struttura del manoscritto decisa: dieci "
    "sezioni sul telaio di M26, le tre leve del titolo nei §4–§6, un §2.3 nuovo sul protocollo; "
    "sorgenti in `papers/paper2/MNRAS/`; titolo di lavoro **B** (alternativa B′ aperta); abstract "
    "entro 220 parole; stesura dal cuore. **Rimandi dei testi decisi verificati**: il «§5.5» della "
    "3.10 è del protocollo, la «Table 8, row 4» dei ritirati è il budget del Paper 2, la Prop. 1 è "
    "del Paper 1 §2.3. **Tre numeri corretti nel testo delle limitazioni**: (vi) sotto @P6@ % a 3σ, "
    "non 0.2 %; (viii) −@C5@ ± @E5@ % con limite @P5@ %; (vii) «largely closed», non «closed». "
    "Ancore di SGC nel §2.3. Nessun record nuovo: nessuna di queste cose cambia il protocollo."
    "\n### rev. 3.35 — 24 settembre 2026 — record 78;"
)
O_REV = "\n### rev. 3.35 — 24 settembre 2026 — record 78;"

O_TIT = (
    '**✦ Titolo di lavoro:** *"What does the loop count respond to? Geometry, weighting and cosmology in\n'
    'persistent homology of voxelized redshift surveys"*\n'
)
T_TIT = (
    '**✦ Titolo di lavoro (fino alla rev. 3.35):** ~~*"What does the loop count respond to? Geometry,\n'
    'weighting and cosmology in persistent homology of voxelized redshift surveys"*~~\n'
    '\n'
    '**✦ rev. 3.36 — titolo, 24 set.** Scelto **B**: *"Invariant by theorem, bounded by measurement: what\n'
    'the persistent-homology loop count responds to in DESI BGS"*. Proposta lo stesso giorno\n'
    "l'alternativa **B′**: *\"Invariant by theorem, bounded by measurement: geometry, weighting and\n"
    'cosmology in the persistent-homology loop count of DESI BGS"*, che toglie dal titolo il «responds\n'
    'to», già titolo del §6 del Paper 1 («What *N*_H1 responds to»). **Z-titolo**: la scelta fra B e B′\n'
    'si chiude con abstract e introduzione, ultimi nella stesura. Scartati: «blind» e «immune», che\n'
    "rimetterebbero l'eccesso tolto da D7; «rescaling», che si leggerebbe contro il σ_px di M26 §3.2.\n"
    'Il titolo sottomesso del Paper 1 non è una domanda: «Three quarters of the DESI BGS H1 deficit is\n'
    'reproduced by its power spectrum; one quarter is not».\n'
)

O_STR = "### Struttura\n\n1. Introduzione:"
T_STR = (
    "### Struttura\n\n"
    "**✦ rev. 3.36 — struttura del manoscritto, decisa il 24 set.** La lista 1–10 qui sotto resta il\n"
    "deposito dei contenuti e dei testi decisi; le sezioni del manoscritto sono quelle della tabella, sul\n"
    "telaio di M26 (Data; Discussion; Limitations come sezione a sé, con le voci (i)–(xi) di M26 §7;\n"
    "Conclusions numerate; dettagli in appendice), con le tre leve del titolo nei §4–§6. Lo schema\n"
    "Methods I / Methods II / Results di M26 non si adatta: M26 è un caso di studio con un risultato, qui\n"
    "ogni leva ha il suo metodo e il suo esito.\n"
    "\n"
    "| sezione del manoscritto | sottosezioni | punti qui sotto |\n"
    "|---|---|---|\n"
    "| 1 Introduction | 1.1 la domanda; 1.2 contributi numerati, come M26 §1.1 | 1 |\n"
    "| 2 Data, ensembles and protocol | 2.1 DESI BGS DR1, due calotte, campo congelato; 2.2 ensemble v1 e v2; **2.3 protocollo pre-registrato e registri congelati** (nuovo) | ancore di SGC, dal 4 |\n"
    "| 3 Theory: invariances of the count | 3.1 Prop. 1 (Paper 1 §2.3) e D7; 3.2 Prop. 2 e 2′; 3.3 Lemma 3 e gauge di Chebyshev | 2 |\n"
    "| 4 Geometry: the Alcock–Paczyński response | 4.1 canale isotropo; 4.2 canale anisotropo; 4.3 completezza della parametrizzazione; 4.4 risposta AP del deficit | 3, 4, 5 |\n"
    "| 5 Weighting: the v2 ensemble | 5.1 voxelizzazione pesata dei mock; 5.2 predizioni a un punto, ritirati, collinearità; 5.3 erosione su v2 e tensione col Paper 1 §7.2/§8.1 | 7, 8 |\n"
    "| 6 Cosmology: response to the nwLH parameters | 6.1 decomposizione della varianza e *n*_s; 6.2 *w*₀ a *n* = 2000, tetto di sensibilità, D8; 6.3 tetto di *R*² | 6 |\n"
    "| 7 The response function of *N*_H1 | 7.1 budget sistematico aggiornato; 7.2 zero per teorema e zero per misura (F7) | 9, 10 |\n"
    "| 8 Discussion | funzione di risposta; rapporto con M26, Paper 1 e letteratura | 10 |\n"
    "| 9 Limitations and future work | testo delle limitazioni e nota sul «3-bis» | 10 |\n"
    "| 10 Conclusions | elenco numerato | — |\n"
    "| Appendici | A dimostrazioni; B predizioni smentite e ritirate (tabelle); C dettagli tecnici (griglia, esclusioni, tiling) | 7, F8 |\n"
    "\n"
    "**Decisioni di contorno, 24 set:**\n"
    "- sorgenti in `papers/paper2/MNRAS/`, figure in `papers/paper2/MNRAS/figures/`;\n"
    "- `mnras.cls` e `mnras.bst` di M26 riusati. La `.bst` è identica byte per byte a quella di CTAN; la\n"
    "  `.cls` differisce dalla v3.2 di CTAN solo per versione, data, copyright e una riga di registro di\n"
    "  OUP (v3.3 del 23 apr 2024), e l'intestazione, rimasta a «v3.0», è corretta a «v3.3» (un byte,\n"
    "  `ece8db40…`);\n"
    "- `cauchy_mnras_v3.tex` precede le bozze di M26: se ne riprende il preambolo, ma affiliazione\n"
    "  (37026 Pescantina), nomi dei programmi in maiuscoletto (macro `\\sw{}`) e ordine delle parole\n"
    "  chiave vengono dalla versione pubblicata;\n"
    "- **Z-bib**, in `cauchy.bib`: `DESI2025DR1` → AJ 171, 285 (2026); data di accesso a `gudhi`;\n"
    "  aggiungere M26 (`stag1730`) e il Paper 1, con la forma della citazione da decidere;\n"
    "- abstract entro **220 parole** (M26 pubblicato: circa 225, contro il limite MNRAS di 250), una\n"
    "  frase per leva, scritto per ultimo;\n"
    "- ordine di stesura: §4–§7, poi §3, poi §2 e §8–§10; per ultimi introduzione e abstract;\n"
    "- **Z-P1§6**: il §6 del Paper 1 si intitola «What *N*_H1 responds to»; l'introduzione dice che cosa\n"
    "  aggiunge il Paper 2 (geometria, pesatura, separazione fra teorema e misura).\n"
    "\n"
    "**Rimandi dei testi decisi, verificati il 24 set** su M26 pubblicato e sul Paper 1 sottomesso. Nessun\n"
    "testo deciso cita figure, né di questo paper né di altri.\n"
    "\n"
    "| testo | rimando | punta a | nel manoscritto |\n"
    "|---|---|---|---|\n"
    "| D7 | «Proposition 1» | **Paper 1, §2.3** | «Proposition 1 (Paper 1, §2.3)»; Prop. 2, 2′ e Lemma 3 ne continuano la numerazione, e il testo lo dichiara |\n"
    "| 3.10 | «the symmetry test of §5.5» | **protocollo pre-registrato**, §5.5 | rimando al protocollo (§2.3); lo stesso per il test di completezza, protocollo §5.6 |\n"
    "| ritirati | «(Table 8, row 4)» | **budget del Paper 2**, riga 4 (ripesatura FKP dei mock); nella Tab. 8 del Paper 1 la riga 4 è il profilo dei satelliti | `\\ref` al budget; la tabella del Paper 1 si scrive sempre «Paper 1, Table 8» |\n"
    "| collinearità | «the five one-point rules» | regole pre-registrate, appendice B | `\\ref` all'appendice B |\n"
    "| limitazioni | «M26 (§7)», «(§5.6)» | M26 pubblicato, §7 (voci (i)–(xi) una per una) e §5.6 | — |\n"
    "| limitazioni | «Paper 1 (§5.2)»; «(viii) … Paper 1» | Paper 1 §5.2; §7.1 e riga dei satelliti della Tab. 8, non toccata da P1-9 né da P1-13 | — |\n"
    "| «3-bis» | «M26 (§7) … (limitation x)»; «20.3 to 14.2» | M26 §7 (x); Paper 1 §8.3 | — |\n"
    "| struttura, §5.3 | tensione §7.2/§8.1 | Paper 1 §7.2 e §8.1, toccati da P1-1, P1-4, P1-11 e P1-10 | si scrive sul Paper 1 corretto |\n"
    "\n"
    "Il vincolo del 24 sul Paper 1 si legge così: vale dove il Paper 2 dice che cosa afferma il Paper 1, e\n"
    "per ogni punto citato si registra se una voce di `modifiche_paper1.md` lo tocca. I testi della 3.10\n"
    "presuppongono definiti nel §4 B1–B6, Δ*D*_max, il pavimento del blocco A, il livello primario *k* = 1\n"
    "e i livelli diagnostici; la corrispondenza fra β₁^max di M26 e *N*_H1 va data nel §2.\n"
    "\n"
    "1. Introduzione:"
)

O_SGC = "   > are anchored in both caps.*\n5. Risposta AP"
T_SGC = (
    "   > are anchored in both caps.*\n"
    "   **✦ rev. 3.36:** nel manoscritto questo testo va nel **§2.3** (protocollo e registri congelati):\n"
    "   dice quali stadi riproducono un valore congelato. Nel canale anisotropo interromperebbe\n"
    "   l'argomento AP.\n"
    "5. Risposta AP"
)

O_LIM = (
    "    > *Of the eleven limitations listed in M26 (§7), this paper closes (ix), the dependence on the\n"
    "    > fiducial cosmology through the Alcock–Paczyński response. It bounds, without closing, the\n"
    "    > sensitivity of the statistic to w₀: across the nwLH hypercube (w₀ from −1.3 to −0.7) the implied\n"
    "    > 1σ constraint is about ±0.6, an order of magnitude weaker than DESI BAO. Limitation (ii) concerns\n"
    "    > w_a ≠ 0, which that suite does not vary, and remains open. Limitation (vii) was closed in the\n"
    "    > revised M26, and (xi) largely by Paper 1 (§5.2). Open after this paper are fiber assignment (i),\n"
    "    > a single survey (iii), the error budget beyond cosmic variance (iv), the HOD calibration (v),\n"
    "    > the snapshot treatment (vi), and satellite profiles and redshift-space distortions (viii). For\n"
    "    > (vi) we bound only the growth term, at 0.2 per cent of the deficit, from two snapshots; (viii)\n"
    "    > is bounded at −0.8 per cent by Paper 1. Limitations (x) and (xi) are the subject of a\n"
    "    > forthcoming paper on point-cloud filtrations; (i), (iii)–(vi) and (viii) of one on survey\n"
    "    > systematics and additional tracers.*\n"
)
T_LIM = (
    "    > *Of the eleven limitations listed in M26 (§7), this paper closes (ix), the dependence on the\n"
    "    > fiducial cosmology through the Alcock–Paczyński response. It bounds, without closing, the\n"
    "    > sensitivity of the statistic to w₀: across the nwLH hypercube (w₀ from −1.3 to −0.7) the implied\n"
    "    > 1σ constraint is about ±0.6, an order of magnitude weaker than DESI BAO. Limitation (ii) concerns\n"
    "    > w_a ≠ 0, which that suite does not vary, and remains open.\n"
    "    > Limitation (vii) was largely closed in the revised M26 (§5.6), which leaves only modes larger\n"
    "    > than the periodic box untested; (xi) was largely closed by Paper 1 (§5.2). Open after this paper\n"
    "    > are fiber assignment (i), a single survey (iii), the error budget beyond cosmic variance (iv),\n"
    "    > the HOD calibration (v), the snapshot treatment (vi), and satellite profiles and redshift-space\n"
    "    > distortions (viii). For (vi) we bound only the growth term,\n"
    "    > below @P6@ per cent of the deficit at 3σ, from two snapshots; (viii) is measured at\n"
    "    > −@C5@ ± @E5@ per cent by Paper 1, and bounded below @P5@ per cent. Limitations (x) and (xi) are\n"
    "    > the subject of a forthcoming paper on point-cloud filtrations; (i), (iii)–(vi) and (viii) of\n"
    "    > one on survey systematics and additional tracers.*\n"
    "    **✦ rev. 3.36 — tre correzioni, accettate il 24 set.** (vi): «at 0.2 per cent» era il valore\n"
    "    centrale di un nullo (−53 ± 112 per unità di *z*); il limite è 97.25 generatori, @P6X@ % di *D*\n"
    "    (riga 6 del budget), la stessa correzione che P1-13, punto 3, porta nel Paper 1. (viii): «bounded\n"
    "    at −0.8 per cent» era il valore centrale di una misura a @SIG5@σ (−56.5 ± 23.5); con la regola del\n"
    "    budget, |Δ| + 3σ con la misura accanto, il limite è 127, @P5X@ % (riga 5). (vii): «was closed»\n"
    "    diceva più di M26, che al §7 (vii) lascia non quantificata l'assenza di modi più grandi della\n"
    "    scatola. Per reggere la relativa, «and (xi) largely by Paper 1» diventa «; (xi) was largely\n"
    "    closed by Paper 1». Numeri ricalcolati dal budget (`0c7eef5b…`) dal patcher della rev. 3.36.\n"
)

# --- stato (scritto in LF qui, convertito al terminatore del file)
O_S1 = "aggiornato **24 settembre 2026**, diciannovesima revisione"
T_S1 = "aggiornato **@DATA@**, ventesima revisione"

O_S2 = "`gate_preinvio`, Zenodo.\n\n---\n\n## 1. Il risultato principale"
T_S2 = (
    "`gate_preinvio`, Zenodo.\n\n"
    "**Al @DATAB@ (ventesima revisione):** **la scrittura comincia** · censimento dei **registri** dopo\n"
    "il record 78: uscita **0**, 121 file coperti, 0 senza copertura, 0 falliti, cancello di\n"
    "riproduzione PASS; nel ledger resta il solo FAIL `crashsafe`, già noto (`logs/censimento_v17.jsonl`,\n"
    "`@CENS8@…`, @CENSB@ byte) · ancore misurate sul disco: `censimento_rilascio_78b.jsonl` `7145ac57…`\n"
    "(35 044 byte, quello che vale), `censimento_rilascio_78.jsonl` `44c58bdb…` (35 141, superato),\n"
    "`paper2_5_5_smentite.md` `82b2878d…` (15 129), `canovaccio_paper4.md` `e25cc888…` (9 554) ·\n"
    "manoscritto in `papers/paper2/MNRAS/`: `mnras.cls` `ece8db40…` (intestazione corretta a v3.3, un\n"
    "byte), `mnras.bst` `8dd74053…`, identica a CTAN · checklist **rev. 3.36**: struttura in dieci\n"
    "sezioni sul telaio di M26, titolo di lavoro B con l'alternativa B′ aperta, abstract entro 220\n"
    "parole, rimandi dei testi decisi verificati, **tre numeri corretti nel testo delle limitazioni**\n"
    "((vi) sotto @P6@ % a 3σ; (viii) −@C5@ ± @E5@ %, limite @P5@ %; (vii) «largely closed») · ledger\n"
    "invariato a 78 record (`fb70459f…`): nessun record nuovo · da misurare: il commit del tag\n"
    "`v3.1-paper2`, letto finora solo come nome.\n"
    "\n---\n\n## 1. Il risultato principale"
)

O_S3 = ("| (22 set) censimento a 75 record, con 22 eccezioni | **PULITO 5/5**, 141 percorsi, 117 tracciati"
        " / 16 esclusi con eccezione / 6 assenti con eccezione / 2 pattern |\n")
T_S3 = O_S3 + (
    "| (24 set) censimento dei registri dopo il record 78 | **uscita 0**: 121 file coperti, 0 senza copertura, 0 falliti, cancello PASS; nel ledger il solo FAIL `crashsafe`, già noto |\n"
    "| (24 set) copie nel project contro le ancore della consegna del 24 | **coincidenti** tutte; `paper2_5_5_smentite.md` e `canovaccio_paper4.md` coincidono anche col disco |\n"
    "| (24 set) `mnras.cls` e `mnras.bst` contro CTAN | `.bst` **identica**; `.cls` diversa solo in versione, data, copyright e una riga di registro di OUP (v3.3); l'intestazione «v3.0» è corretta |\n"
    "| (24 set) rimandi degli otto testi decisi della Fase 7 | **verificati** su M26 pubblicato e Paper 1 sottomesso; tre puntano fuori in modo non ovvio: Prop. 1 → Paper 1 §2.3, «§5.5» → protocollo, «Table 8, row 4» → budget del Paper 2 |\n"
    "| (24 set) numeri del testo delle limitazioni contro il budget | **tre da correggere**, corretti nella checklist rev. 3.36 |\n"
)

O_S4 = "il lato mock è ancorato in entrambi. Testo nella checklist, Fase 7 punto 4 |"
T_S4 = ("il lato mock è ancorato in entrambi. Testo nella checklist, Fase 7 punto 4; nel manoscritto va"
        " nel §2.3 (rev. 3.36) |")

O_S5 = ("| ~~**Z-collinearità**~~ | ~~tre direzioni, non cinque~~ **MISURATA il 24 set** | scrittura | Il «tre»"
        " non aveva sorgente. Su `onepoint_v1_*`: larghezza standardizzata–curtosi *r* = 0.999/0.998, "
        "varianza–massimo di δ 0.88/0.83 (0.63 in rango, NGC), `n_patologici` a parte; prima componente"
        " 70/68 %, tre 98/97 %. Testo nella checklist, Fase 7 punto 7 |\n")
T_S5 = O_S5 + (
    "| ~~**Z-limitazioni-numeri**~~ | ~~tre numeri nel testo delle limitazioni~~ **CORRETTI il 24 set** | scrittura | (vi) lo 0.2 % era il centrale di un nullo: sotto @P6@ % a 3σ; (viii) il −0.8 % era il centrale: −@C5@ ± @E5@ %, limite @P5@ %; (vii) «closed» → «largely closed», come M26 §7 (vii). Checklist rev. 3.36, Fase 7 punto 10 |\n"
    "| **Z-titolo** | B o B′ | scrittura | Si chiude con abstract e introduzione. B′ toglie dal titolo il «responds to», già titolo del §6 del Paper 1 |\n"
    "| **Z-bib** | `cauchy.bib` da aggiornare | scrittura | DESI DR1 → AJ 171, 285 (2026); accesso a GUDHI; M26 `stag1730`; Paper 1, forma della citazione da decidere |\n"
    "| **Z-P1§6** | il §6 del Paper 1 si intitola «What *N*_H1 responds to» | introduzione | L'introduzione dice che cosa aggiunge il Paper 2: geometria, pesatura, separazione fra teorema e misura |\n"
)

O_S6 = ("| `paper2_patch_revisione_24set.py` | checklist 3.35, questo documento alla 19ª, budget righe 6 e"
        " riscontro (i) | 7/7 |\n")
T_S6 = O_S6 + (
    "| `paper2_patch_revisione_24set_b.py` | checklist 3.36, questo documento alla 20ª: struttura e rimandi"
    " del manoscritto, tre numeri del testo delle limitazioni ricalcolati dal budget, ancore misurate |"
    " @NST@/@NST@ |\n"
)

EDITS = [
    ("chk", "C1 intestazione rev. 3.36", O_REV, T_REV),
    ("chk", "C2 titolo", O_TIT, T_TIT),
    ("chk", "C3 struttura e rimandi", O_STR, T_STR),
    ("chk", "C4 ancore di SGC al 2.3", O_SGC, T_SGC),
    ("chk", "C5 testo delle limitazioni", O_LIM, T_LIM),
    ("sta", "S1 riga 2", O_S1, T_S1),
    ("sta", "S2 ventesima revisione", O_S2, T_S2),
    ("sta", "S3 righe del par. 0", O_S3, T_S3),
    ("sta", "S4 Z-ancore-SGC", O_S4, T_S4),
    ("sta", "S5 voci aperte", O_S5, T_S5),
    ("sta", "S6 strumento nel par. 9", O_S6, T_S6),
]


def postcondizioni(chk, sta, num):
    attese = [
        ("chk", "### rev. 3.36 —", 1),
        ("chk", "at 0.2 per cent of the deficit", 0),
        ("chk", "is bounded at −0.8 per cent by Paper 1", 0),
        ("chk", "Limitation (vii) was closed in the", 0),
        ("chk", "below %s per cent of the deficit at 3σ" % num["P6"], 1),
        ("chk", "−%s ± %s per cent by Paper 1, and bounded below %s per cent" % (num["C5"], num["E5"], num["P5"]), 1),
        ("chk", "Limitation (vii) was largely closed in the revised M26 (§5.6)", 1),
        ("chk", "**✦ rev. 3.36 — struttura del manoscritto", 1),
        ("sta", "ventesima revisione", 2),
        ("sta", "`paper2_patch_revisione_24set_b.py`", 1),
        ("sta", O_S1, 0),
    ]
    testi = {"chk": chk, "sta": sta}
    return ["%s: %r compare %d volte, attese %d" % (f, s, testi[f].count(s), n)
            for f, s, n in attese if testi[f].count(s) != n]


def costruisci(chk, sta, bud, data, cens_sha, cens_byte, nst):
    """Tutto in memoria: nessuna scrittura. Errore alla prima ancora mancante o doppia."""
    if "### rev. 3.36" in chk or "ventesima revisione" in sta:
        raise PatchError("passata gia' applicata (marcatori della rev. 3.36 o della 20a presenti)")
    num = numeri_budget(bud)
    tok = dict(num)
    tok.update({"DATA": data, "DATAB": data.rsplit(" ", 1)[0], "CENS8": cens_sha[:8], "CENSB": migliaia(cens_byte), "NST": str(nst)})
    testi = {"chk": chk, "sta": sta}
    eol = {k: eol_di(v) for k, v in testi.items()}
    applicate = []
    for f, lab, old, new in EDITS:
        o = old.replace("\n", eol[f])
        n = riempi(new, tok).replace("\n", eol[f])
        k = testi[f].count(o)
        if k != 1:
            raise PatchError("%s: ancora trovata %d volte (attesa 1)" % (lab, k))
        testi[f] = testi[f].replace(o, n)
        applicate.append(lab)
    for f in testi:
        if eol_di(testi[f]) != eol[f]:
            raise PatchError("%s: terminatore cambiato dalla patch" % f)
    falliti = postcondizioni(testi["chk"], testi["sta"], num)
    if falliti:
        raise PatchError("postcondizioni: " + "; ".join(falliti))
    return testi["chk"], testi["sta"], num, applicate


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

def _fixture_chk():
    parti = ["# Paper 2 — Checklist", "x"]
    parti += [old for f, lab, old, new in EDITS if f == "chk"]
    return "\n".join(parti) + "\nfine\n"


def _fixture_sta():
    parti = ["# Paper 2 — stato", "y"]
    parti += [old for f, lab, old, new in EDITS if f == "sta"]
    return ("\n".join(parti) + "\nfine\n").replace("\n", "\r\n")


def _fixture_bud():
    return "\n".join(["budget"] + BUDGET_ANCORE) + "\n"


def _t_ancora_mancante():
    try:
        costruisci(_fixture_chk().replace(O_TIT, "niente\n"), _fixture_sta(), _fixture_bud(),
                   "24 settembre 2026", "0" * 64, 1, 1)
    except PatchError as e:
        return "C2 titolo" in str(e)
    return False


def _t_ancora_doppia():
    try:
        costruisci(_fixture_chk() + O_SGC + "\n", _fixture_sta(), _fixture_bud(),
                   "24 settembre 2026", "0" * 64, 1, 1)
    except PatchError as e:
        return "2 volte" in str(e)
    return False


def _t_crlf_conservato():
    c, s, _, _ = costruisci(_fixture_chk(), _fixture_sta(), _fixture_bud(), "24 settembre 2026",
                            "a" * 64, 35000, 11)
    return s.count("\r\n") == s.count("\n") and "\r" not in c and "\r\n" in s


def _t_terminatori_misti():
    try:
        eol_di("a\r\nb\nc\r\n")
    except PatchError:
        pass
    else:
        return False
    try:
        eol_di("a\rb\n")
    except PatchError:
        return True
    return False


def _t_numeri_budget():
    if numeri_budget(_fixture_bud()) != ATTESI:
        return False
    try:
        numeri_budget(_fixture_bud().replace("127/*D* = 1.769 %", "127/*D* = 1.77 %"))
    except PatchError:
        return True
    return False


def _t_data():
    return (data_it(datetime.date(2026, 9, 24)) == "24 settembre 2026"
            and data_it(datetime.date(2026, 10, 1)) == "1 ottobre 2026")


def _t_catena_completa():
    c, s, num, app = costruisci(_fixture_chk(), _fixture_sta(), _fixture_bud(), "24 settembre 2026",
                                "b" * 64, 35000, 11)
    return (len(app) == len(EDITS) and not postcondizioni(c, s, num)
            and "`bbbbbbbb…`, 35 000 byte" in s and " 11/11 |" in s
            and not re.search(r"@[A-Z0-9_]+@", c + s))


def _t_idempotenza():
    c, s, _, _ = costruisci(_fixture_chk(), _fixture_sta(), _fixture_bud(), "24 settembre 2026",
                            "c" * 64, 1, 1)
    try:
        costruisci(c, s, _fixture_bud(), "24 settembre 2026", "c" * 64, 1, 1)
    except PatchError as e:
        return "gia' applicata" in str(e)
    return False


def _t_atomicita():
    d = tempfile.mkdtemp(prefix="st_patch_")
    try:
        a = J(d, "a.md")
        with open(a, "w", encoding="utf-8", newline="") as fh:
            fh.write("originale\n")
        manca = J(d, "non_esiste", "b.md")
        try:
            scrivi_atomico({a: "nuovo\n", manca: "nuovo\n"}, J(d, "bak"))
        except Exception:
            pass
        else:
            return False
        resti = [x for x in os.listdir(d) if x.startswith(".tmp_patch_")]
        return leggi(a) == "originale\n" and not resti
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _t_token_residuo():
    try:
        riempi("x @NONDICHIARATO@ y", {"DATA": "z"})
    except PatchError:
        return True
    return False


def _t_verify_rileva_scarto():
    d = tempfile.mkdtemp(prefix="st_verify_")
    try:
        p = J(d, "f.md")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write("contenuto\n")
        h, n = sha_file(p)
        return confronta_ricevuta({p: {"sha256": h, "byte": n}}) == [] and \
            len(confronta_ricevuta({p: {"sha256": "0" * 64, "byte": n}})) == 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


TESTS = [
    ("ancora mancante -> errore col nome della modifica", _t_ancora_mancante),
    ("ancora doppia -> errore", _t_ancora_doppia),
    ("CRLF dello stato conservato, LF della checklist conservato", _t_crlf_conservato),
    ("terminatori misti e CR isolato -> errore", _t_terminatori_misti),
    ("numeri ricalcolati dal budget = attesi; ancora alterata -> errore", _t_numeri_budget),
    ("data in italiano dall'orologio", _t_data),
    ("catena completa su fixture: 11 modifiche, postcondizioni, token", _t_catena_completa),
    ("seconda applicazione -> errore esplicito", _t_idempotenza),
    ("scrittura atomica: errore sul secondo file lascia intatto il primo", _t_atomicita),
    ("token non dichiarato -> errore", _t_token_residuo),
    ("verify rileva uno sha diverso dalla ricevuta", _t_verify_rileva_scarto),
]


def selftest(verboso=True):
    ok = 0
    for nome, fn in TESTS:
        try:
            esito = bool(fn())
        except Exception as e:  # un test che solleva e' un test fallito
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
    if not os.path.exists(CENS):
        fallite.append("%s: assente" % CENS)
    elif os.path.getsize(CENS) == 0:
        fallite.append("%s: vuoto" % CENS)
    return fallite


def prepara():
    radice_ok()
    if not selftest(verboso=False):
        raise PatchError("selftest non superato: lanciare 'selftest' per il dettaglio")
    fallite = precondizioni()
    if fallite:
        raise PatchError("precondizioni:\n  " + "\n  ".join(fallite))
    oggi = datetime.date.today()
    data = data_it(oggi)
    cens_sha, cens_byte = sha_file(CENS)
    chk0, sta0, bud = leggi(CHK), leggi(STA), leggi(BUD)
    chk1, sta1, num, app = costruisci(chk0, sta0, bud, data, cens_sha, cens_byte, len(TESTS))
    return {"oggi": oggi, "data": data, "cens": (cens_sha, cens_byte), "num": num, "app": app,
            "chk": chk1, "sta": sta1}


def stampa(r, scritto):
    print("precondizioni: %d/%d PASS (sha e byte)" % (len(PRE), len(PRE)))
    print("selftest: %d/%d PASS" % (len(TESTS), len(TESTS)))
    print("data dall'orologio: %s%s" % (r["data"], "" if r["oggi"] == DATA_DECISIONI else
                                         "  (attenzione: diversa dal 24 set delle decisioni)"))
    print("censimento_v17: %s… %s byte" % (r["cens"][0][:12], migliaia(r["cens"][1])))
    n = r["num"]
    print("numeri dal budget: (vi) %s %% -> %s ; (viii) %s ± %s %%, limite %s %% -> %s"
          % (n["P6X"], n["P6"], n["C5"], n["E5"], n["P5X"], n["P5"]))
    print("modifiche: %d/%d ancore trovate una volta sola" % (len(r["app"]), len(EDITS)))
    for p, t in ((CHK, r["chk"]), (STA, r["sta"])):
        h, b = sha_testo(t)
        print("%s: %s -> %s byte, sha %s…" % (os.path.basename(p), migliaia(PRE[p][1]), migliaia(b), h[:12]))
    print("postcondizioni: PASS")
    print("ESITO: %s" % ("APPLICATA" if scritto else "DRY-RUN, nessun file scritto"))


def cmd_apply():
    r = prepara()
    scrivi_atomico({CHK: r["chk"], STA: r["sta"]}, BACKUP)
    uscite = {}
    for p in (CHK, STA):
        h, n = sha_file(p)
        uscite[p] = {"sha256": h, "byte": n}
    ric = {
        "strumento": "paper2_patch_revisione_24set_b.py",
        "data": r["data"],
        "ingressi": {p: {"sha256": s, "byte": b} for p, (s, b) in PRE.items()},
        "censimento_v17": {"sha256": r["cens"][0], "byte": r["cens"][1]},
        "uscite": uscite,
        "modifiche": r["app"],
        "numeri": r["num"],
        "selftest": "%d/%d" % (len(TESTS), len(TESTS)),
    }
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
    scarti += confronta_ricevuta({CENS: ric["censimento_v17"]})
    led = J("src", "paper2_v1_amendments.jsonl")
    scarti += confronta_ricevuta({led: ric["ingressi"][led]})
    num = numeri_budget(leggi(BUD))
    scarti += postcondizioni(leggi(CHK), leggi(STA), num)
    for p in (CHK, STA):
        eol_di(leggi(p))
    for p in (CHK, STA):
        h, n = sha_file(p)
        print("%s: %s… %s byte" % (os.path.basename(p), h[:12], migliaia(n)))
    print("ledger invariato: %s" % ("sì" if not confronta_ricevuta({led: ric["ingressi"][led]}) else "NO"))
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

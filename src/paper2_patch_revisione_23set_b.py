#!/usr/bin/env python3
"""
paper2_patch_revisione_23set_b.py  -  seconda passata documentale del 23 settembre

Quattro file, un passaggio:
  checklist_paper2.md   rev. 3.33 -> 3.34: 3.10 DECISA; forma di D misurata sui due lati (3.6);
                        Z-P1-curtosi fatta (6.0a, 6.5); testi per il §5 del manoscritto (Fase 7 p. 5)
  paper2_stato.md       17a -> 18a revisione: paragrafo della sera, §8 (F3.10, F-copertura,
                        Z-rilascio-r50, Z-P1-curtosi), §9 (cinque strumenti)
  modifiche_paper1.md   P1-11 punto 5 (§5.3), passo 2 esteso ed eseguito, una riga di changelog
  eccezioni_rilascio.json  voce di modifiche_paper1.md senza digest (regola del file stesso);
                        voce del budget: la 6.2-iii e' in Fase 7

Stesso motore di paper2_patch_revisione_23set.py: ancora «prima» o «dopo»; ogni testo trovato
esattamente una volta; sha «dopo» atteso; inversa che ridà «prima»; fine riga e BOM misurati e
conservati. Per il JSON, in piu': il risultato si rilegge e la sua riserializzazione ridà i byte.
Precondizioni = i fatti che la 18a revisione dichiara.

Uso:
  python src\\paper2_patch_revisione_23set_b.py selftest
  python src\\paper2_patch_revisione_23set_b.py dry-run
  python src\\paper2_patch_revisione_23set_b.py apply
  python src\\paper2_patch_revisione_23set_b.py verify
"""
import argparse, hashlib, json, os, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"

PRECONDIZIONI = {
 "src/paper2_v1_amendments.jsonl":   ("9e178837aca9e56a16cf006e3ffe6e25b424ecca2cf94bf18dc40ec05982a923", 651850),
 "src/paper2_freeze_verify.py":      ("a9a918c2c9bc55fc3772d36753ad94e310e80833c99fb9f58367a620a9d5394a", 52181),
 "logs/b1_decomposizione_v2.json":   ("1eacf1baf57c855a8cdc1521748317946cce3bcf7da6f12f5fe2b09562d8053c", 3274),
 "logs/forma_lato_mock_v3.json":     ("f164e4d25ec0bb8f51873c6439501f8460e66347c2bda89381eb1f0f3c4be9cc", 9401),
 "papers/paper2/paper2_6_5_ritirati.md": ("517e72095feb376b359f3b67df754a33ff3a048a98716a09d4466d80873d1770", 4868),
}
COMMIT = "5344b96"
DIGEST_RECORD_70 = "c6350fd4423edc4f2529e37f694d0c4a7e867bf00e5a8552a495297de17a9922"
CENSIMENTO_77C = ROOT / "logs" / "censimento_rilascio_77c.jsonl"

P_310 = ("   > *At k = 0 in NGC the two-point statistic is dominated by a single geometry: B1 lies +153.2 ± 11.7\n"
         "   > generators from the fiducial, while B2, B4 and B5 lie between +5.3 and +39.2. Decomposing D = mock −\n"
         "   > data shows where the irregularity lives. Along the B line the mock mean responds monotonically to the\n"
         "   > deformation at both erosion levels and in both hemispheres; the data side, a single deterministic\n"
         "   > realization, does not. At B1 the mock mean gains 91.2 ± 11.7 generators while the data lose 62. The\n"
         "   > quoted uncertainties belong to the mock mean alone: the data side carries none, so a departure of the\n"
         "   > data from the mock trend enters D at full weight. At k = 1, the primary level, the departure sits at\n"
         "   > B4 (data −121, mock mean −53.2 ± 10.9), and in SGC at B2 at both levels; neither point enters ΔD_max,\n"
         "   > which uses B1 and B5.*\n")
P_FORMA = ("   > *The quadratic family describes the mock-side response within its noise at both erosion levels and in\n"
           "   > both hemispheres (χ² from 0.7 to 5.6 on 3 degrees of freedom, against a 99 per cent limit of 11.34).\n"
           "   > The inadequacy of the fit to D, χ² from 74.6 to 149.7, comes entirely from the data side, a single\n"
           "   > deterministic realization whose departures from a quadratic in F reach 4.8 times the standard error\n"
           "   > of the mock mean. The symmetry test of §5.5 therefore remains without a verdict, and the reason is\n"
           "   > now known: its model treats the data side as exact, and the data carry structure of one realization\n"
           "   > that the covariance of the fit does not contain.*\n")
P_K23 = ("   > *Repeating the split at the diagnostic levels, at k = 2 the fit to D is adequate in NGC (χ² = 6.9)\n"
         "   > and fails in SGC (χ² = 149.4), where the mock side remains quadratic within its noise (χ² = 1.3): the\n"
         "   > non-smooth part is again carried by the data side, at a level where the block-A floor covers only 26\n"
         "   > per cent of the unattributed residual. At k = 3 the mock side itself departs from a quadratic in both\n"
         "   > hemispheres (χ² = 12.4 and 16.6 against 11.34), while the data side still dominates the misfit (χ² of\n"
         "   > D = 90.4 and 264.1). This test locates the non-smooth part of the response; it does not establish\n"
         "   > that this part is the unattributed residual.*\n")

CHECKLIST = [
 ("### rev. 3.33 \u2014 23 settembre 2026 \u2014 record 77;",
  "### rev. 3.34 \u2014 23 settembre 2026, sera \u2014 Fase 7 aperta: **3.10 DECISA** (B1 a *k* = 0 in NGC \u00e8 lato mock +91.2 meno lato dati \u221262; numero depositato, escursione accanto, un paragrafo nel \u00a75); **forma di *D* misurata sui due lati** a *k* = 0\u20133 con lo stesso fit del 3.4; **Z-rilascio-r50** chiusa (limite dichiarato del censimento); **Z-P1-curtosi** chiusa (il Paper 1 non attribuisce la curtosi alla pesatura; P1-11 riceve un punto 5 nel \u00a75.3); rilascio PULITO dopo il record 77: 152 percorsi, 25 eccezioni. Nessun record nuovo: nessuna di queste cose cambia il protocollo.\n"
  "### rev. 3.33 \u2014 23 settembre 2026 \u2014 record 77;"),
 ("- [~] **\u2726\u2727\u2726 3.10 \u2014 B1 \u00e8 anomalo a *k* = 0 in NGC. RIMANDATO, con una data.**",
  "- [x] **\u2726\u2727\u2726 3.10 \u2014 B1 \u00e8 anomalo a *k* = 0 in NGC. DECISA il 23 set** *(era: RIMANDATO, con una data)*."),
 ("      la stessa cosa: gli estremi non sono B1 e B5. Non \u00e8 nel referee report e va deciso prima di\n      scriverne.\n",
  "      la stessa cosa: gli estremi non sono B1 e B5. Non \u00e8 nel referee report e va deciso prima di\n      scriverne.\n"
  "      **\u2726 rev. 3.34 \u2014 DECISA il 23 set.** `paper2_b1_decomposizione.py` rev. 2 (log\n"
  "      `b1_decomposizione_v2.json`, `1eacf1ba\u2026`) spezza \u0394*D* = \u0394m \u2212 \u0394d sui registri grezzi, col\n"
  "      cancello che riproduce i numeri pubblicati e il `per_point` di `fase3_analisi.jsonl`. B1 a *k* = 0\n"
  "      in NGC: lato mock **+91.2 \u00b1 11.7**, lato dati **\u221262**. La previsione dichiarata (eccesso portato\n"
  "      dal lato dati per almeno 2/3) \u00e8 **FALSIFICATA**: dell'eccesso di B1 sulla media di B2, B4, B5,\n"
  "      +135.9, il mock porta +141.9 e i dati \u22126.0. Seconda misura, dichiarata come tale: lungo *F* il\n"
  "      lato mock \u00e8 monotono in 4 casi su 4, il lato dati in 0 su 4. **Correzione:** a *k* = 1 la risposta\n"
  "      non \u00abscende da B1 a B6\u00bb: B4 sta a +67.8 contro lo 0 del fiduciale (dati \u2212121, mock \u221253.2).\n"
  "      **Decisione:** esito E2 e riga 1 del budget invariati (*k* = 1); a *k* = 0 il numero depositato,\n"
  "      \u2212114.0 \u00b1 11.6, con l'escursione accanto (153.2 NGC, 146.8 SGC), e il paragrafo della Fase 7,\n"
  "      punto 5. Nessun cambio di protocollo: sta qui, non nel ledger.\n"),
 ("      separano.** Si riprende in Fase 7, punto 5.\n",
  "      separano.** Si riprende in Fase 7, punto 5.\n"
  "      **\u2726 rev. 3.34 \u2014 misurato il 23 set** (`paper2_forma_lato_mock.py` rev. 3, log\n"
  "      `forma_lato_mock_v3.json`, `f164e4d2\u2026`: lo stesso `symmetry_fit` del 3.4, col lato dati a\n"
  "      zero). Il \u03c7\u00b2 del lato mock sta sotto 11.34 a *k* = 0, 1 (da 0.7 a 5.6) e a *k* = 2 (6.8, 1.3); lo\n"
  "      supera a *k* = 3 (12.4 NGC, 16.6 SGC: seconda previsione FALSIFICATA). Su *D*: NGC *k* = 2 regge\n"
  "      (6.9), SGC *k* = 2 no (149.4) col lato mock quadratico. Le due letture restano, ora con numeri:\n"
  "      SGC *k* = 2 va contro \u00abvale solo dove il pavimento \u00e8 grande\u00bb; *k* = 3 aggiunge un contributo\n"
  "      del lato mock che nessuna delle due prevedeva. Il test dice dove vive la parte non liscia di *D*,\n"
  "      non che sia il residuo non attribuito. **Da verificare sul registro:** l'ordine delle otto\n"
  "      coperture, letto qui come NGC, NGC, SGC, SGC (da cui il 26 % di SGC *k* = 2).\n"),
 ("      dell'applicazione. E un controllo dalla 6.5 (riga 11): se il Paper 1 attribuisce alla\n      pesatura anche la curtosi, in una frase che P1-11 non tocca, serve una voce in pi\u00f9.\n",
  "      dell'applicazione. E un controllo dalla 6.5 (riga 11): se il Paper 1 attribuisce alla\n      pesatura anche la curtosi, in una frase che P1-11 non tocca, serve una voce in pi\u00f9.\n"
  "      **Fatto il 23 set (rev. 3.34):** non la attribuisce. Trovato invece un quinto punto della\n"
  "      stessa attribuzione, \u00a75.3 (statistiche di coda): P1-11 riceve il punto 5, e le voci restano\n"
  "      sedici.\n"),
 ("      manoscritto alla sezione 7 della Fase 7.",
  "      manoscritto alla sezione 7 della Fase 7.\n"
  "      **\u2726 rev. 3.34:** la riga 11 \u00e8 verificata sul Paper 1 (proof di `MN-26-2388-P`): la curtosi non\n"
  "      \u00e8 attribuita alla pesatura. Il documento 6.5 \u00e8 chiuso e ancorato dal record 77: non si riscrive."),
 ("   numeri. Va detto nel paper con entrambe le letture, non con una sola.",
  "   numeri. Va detto nel paper con entrambe le letture, non con una sola. **\u2726 rev. 3.34:** misurato\n"
  "   il 23 set, vedi 3.6: le letture restano due, ora con numeri."),
 ("   *k* = 2 \u00e8 monotono. **Decidere come riportarlo prima di sottomettere la revisione.**",
  "   *k* = 2 \u00e8 monotono. *(Superato: a k = 1 B4 sta a +67.8, vedi 3.10.)* **DECISO il 23 set (3.10).**\n"
  "   Testi per il \u00a75, nell'ordine; ogni numero esce dai log `b1_decomposizione_v2.json` e\n"
  "   `forma_lato_mock_v3.json`, e il 26 % dell'ultimo aspetta la verifica dell'ordine delle coperture:\n"
  + P_310 + "   >\n" + P_FORMA + "   >\n" + P_K23.rstrip("\n")),
]

STATO = [
 ("aggiornato **23 settembre 2026**, diciassettesima revisione", "aggiornato **23 settembre 2026**, diciottesima revisione"),
 ("Fase 7: 6.0a (sedici voci), 6.2-iii, `gate_preinvio`, deposito Zenodo.",
  "Fase 7: 6.0a (sedici voci), 6.2-iii, `gate_preinvio`, deposito Zenodo.\n"
  "\n"
  "**Al 23 settembre, sera (diciottesima revisione):** **Fase 7 aperta** \u00b7 **3.10 DECISA**: B1 a *k* = 0\n"
  "in NGC \u00e8 lato mock +91.2 \u00b1 11.7 e lato dati \u221262; numero depositato con l'escursione accanto, e un\n"
  "paragrafo nel \u00a75 (checklist, Fase 7 punto 5) \u00b7 **forma di *D***: con lo stesso fit del 3.4 il lato\n"
  "mock \u00e8 quadratico entro il rumore a *k* = 0\u20132 e lo scarto viene dal lato dati; a *k* = 3 si discosta\n"
  "anche il lato mock (12.4, 16.6) \u00b7 **Z-rilascio-r50** chiusa: limite dichiarato del censimento \u00b7\n"
  "**Z-P1-curtosi** chiusa: il Paper 1 non attribuisce la curtosi alla pesatura, e P1-11 riceve un\n"
  "punto 5 (\u00a75.3) \u00b7 censimenti dopo il 77: registri uscita 0 su 121 file, rilascio **PULITO** su 152\n"
  "percorsi con 25 eccezioni (`fd571c50\u2026` dopo questa revisione, che ne aggiorna due voci) \u00b7\n"
  "checklist **rev. 3.34** (`32560222\u2026`) \u00b7 `modifiche_paper1.md` `2425045c\u2026` \u00b7 commit fino a `5344b96`."),
 ("| **F3.10** | **B1 anomalo a *k*=0 in NGC** | scrittura | +153.2 \u00b1 11.7 contro il fiduciale (13\u03c3) mentre gli altri quattro stanno entro \u00b140. Si scioglie in **Fase 7, punto 5** |",
  "| ~~**F3.10**~~ | ~~B1 anomalo a *k*=0 in NGC~~ **DECISA il 23 set** | scrittura | Lato mock +91.2 \u00b1 11.7, lato dati \u221262 (`paper2_b1_decomposizione.py`); numero depositato, escursione accanto, paragrafo nel \u00a75 |"),
 ("| **F-copertura** | il crollo a *k*=2,3 | scrittura | Da riprendere in **Fase 7, punto 5**, con **entrambe** le letture |",
  "| **F-copertura** | il crollo a *k*=2,3 | scrittura | Da riprendere in **Fase 7, punto 5**, con **entrambe** le letture. **Misurato il 23 set** (`paper2_forma_lato_mock.py`): SGC *k* = 2 va contro la prima lettura, *k* = 3 aggiunge un contributo del lato mock. Resta aperta, con numeri; l'ordine delle coperture \u00e8 da verificare sul registro |"),
 ("| **Z-rilascio-r50** | la citazione di `canovaccio_paper2.md` nel record 50 non compare nel censimento del rilascio | misura | 0 righe su 255 363 byte: pattern voluto o limite dell'estrattore (record 77, voce H) |",
  "| ~~**Z-rilascio-r50**~~ | ~~la citazione di `canovaccio_paper2.md` nel record 50~~ **CHIUSA il 23 set** | misura | Il record 50 la scrive senza cartella: limite dichiarato dello strumento, \u00abil rilevatore di percorso chiede un separatore\u00bb |"),
 ("| **Z-P1-curtosi** | la curtosi attribuita alla pesatura nel Paper 1? | lettura | Riga 11 della 6.5: se una frase del Paper 1 la attribuisce e P1-11 non la tocca, serve una voce in pi\u00f9 per la 6.0a |",
  "| ~~**Z-P1-curtosi**~~ | ~~la curtosi attribuita alla pesatura nel Paper 1?~~ **CHIUSA il 23 set** | lettura | No, non \u00e8 attribuita. Un quinto punto della stessa attribuzione nel \u00a75.3 (statistiche di coda): P1-11 punto 5, voci sempre sedici |"),
 ("| `paper2_patch_revisione_23set.py` | checklist 3.33, questo documento alla 17\u00aa, date di budget e `modifiche_paper1.md` | 8/8 |",
  "| `paper2_patch_revisione_23set.py` | checklist 3.33, questo documento alla 17\u00aa, date di budget e `modifiche_paper1.md` | 8/8 |\n"
  "| `paper2_b1_decomposizione.py` rev. 2 | item 3.10: \u0394*D* di B1 spezzato in lato mock e lato dati, cancello di riproduzione | 6/6 |\n"
  "| `paper2_forma_lato_mock.py` rev. 3 | forma di *D*(*F*) sui due lati col `symmetry_fit` del 3.4, *k* = 0\u20133 | 4/4 |\n"
  "| `paper2_patch_eccezioni_77.py` | eccezioni del rilascio 22 \u2192 23 (documento 6.5) | 4/4 |\n"
  "| `paper2_patch_eccezioni_77b.py` | eccezioni 23 \u2192 25 (i due canovacci citati per intero dal 77) | 3/3 |\n"
  "| `paper2_patch_revisione_23set_b.py` | checklist 3.34, questo documento alla 18\u00aa, P1-11 punto 5, due voci delle eccezioni | 8/8 |"),
]

MODIFICHE = [
 ("presuppone che produca i voxel estremi, che \u00e8 ci\u00f2 che cade.\n\n### evidenza\n",
  "presuppone che produca i voxel estremi, che \u00e8 ci\u00f2 che cade.\n\n"
  "### punto 5: \u00a75.3, le statistiche di coda *(aggiunto il 23 set 2026)*\n\n"
  "**Da:**\n\n"
  "> \u2026tail statistics (the 99th percentile and the maximum) are excluded, as they are dominated by the\n"
  "> weighting systematic of Section 7.2 and, once cleaned, are consistent between data and mocks (DESI\n"
  "> maximum at rank 182/200 NGC, 134/200 SGC).\n\n"
  "**A:**\n\n"
  "> \u2026tail statistics (the 99th percentile and the maximum) are excluded, as they are dominated by the\n"
  "> lowest-coverage boundary voxels of Section 7.2 and, once cleaned, are consistent between data and\n"
  "> mocks (DESI maximum at rank 182/200 NGC, 134/200 SGC).\n\n"
  "La stessa attribuzione del punto 1, in una frase che non dice \u00abunit-weight\u00bb n\u00e9 \u00abshot noise\u00bb: per\n"
  "questo il passo 2 qui sotto, com'era scritto, non la trovava. Trovata il 23 set leggendo il proof\n"
  "per la riga 11 della 6.5. \u00ablowest-coverage\u00bb \u00e8 il nome che P1-10 chiede di usare (suo passo 3).\n"
  "Nel PDF la frase \u00e8 spezzata dalla Tabella 5, a pagina 8.\n\n"
  "### evidenza\n"),
 ("2. Verificare sul PDF finale che \u00abunit-weight\u00bb e \u00abshot noise from\u00bb non ricorrano altrove oltre ai\n   quattro punti elencati.",
  "2. Verificare sul PDF finale che \u00abunit-weight\u00bb, \u00abshot noise from\u00bb e \u00abweighting systematic\u00bb non\n"
  "   ricorrano altrove oltre ai cinque punti elencati. *(Fatto sul proof il 23 set: \u00abunit-weight\u00bb 4\n"
  "   volte \u2014 abstract, \u00a77.2, la riga della tabella dei canali a pagina 11 sul lato dati, che non\n"
  "   attribuisce, e la didascalia della Tab. 12; \u00abshot noise from\u00bb 1; \u00abweighting systematic\u00bb 1, il\n"
  "   punto 5.)*"),
 ("| 23 set 2026 | Record 77: le date",
  "| 23 set 2026 | P1-11, punto 5: la stessa attribuzione nel \u00a75.3 (statistiche di coda), trovata leggendo il proof per la riga 11 della 6.5. Le voci restano sedici |\n"
  "| 23 set 2026 | Record 77: le date"),
]

ECCEZIONI = [
 ("Citato dal record 60. Ancorato per byte: sha256 c6350fd4423edc4f2529e37f694d0c4a7e867bf00e5a8552a495297de17a9922, 74973 byte al 16 set 2026.",
  "Citato dal record 60. NESSUN DIGEST QUI, per la regola che questo file applica a checklist, stato e budget: e' un documento che si muove (sedici voci al 23 set 2026, e P1-11 riceve un punto 5). Questa voce ne portava uno, misurato il 16 set 2026 \u2014 sha256 c6350fd4423edc4f2529e37f694d0c4a7e867bf00e5a8552a495297de17a9922, 74973 byte \u2014 invecchiato alla prima voce aggiunta: quella misura resta nel record 70, e un ledger append-only non la riscrive. Lo ancora il record che lo nomina; a che punto stia lo dice il suo changelog."),
 ("cio' che lo ancora e' il record che lo nomina, e a che punto stia lo dice la sua intestazione.",
  "cio' che lo ancora e' il record che lo nomina, e a che punto stia lo dice la sua intestazione. Al 23 set 2026 la 6.2 e' chiusa in Fase 6 (record 76), ma la 6.2-iii, che riscrive la riga 9, e' passata alla Fase 7: il documento si muove ancora, e il digest resta fuori fino al record che chiude la 6.2-iii."),
]

FILE = {  # percorso -> (sha prima, sha dopo, fine riga, sostituzioni, json)
 "papers/paper2/checklist_paper2.md": ("9d8aeda07c5daf1fc90e9142464304842a17b49ec380b9ba801fe8615f0c87e5", "325602227db36512532df562e4901efc22d7b854010bec20913bb6e7328d7391", "\n", CHECKLIST, False),
 "papers/paper2/modifiche_paper1.md": ("3f5a5b4e08e267232e104bfafa2989aa97d97ba8fd1ab2d019d362052d164f02", "2425045c373ed22c04be649835814419cad3306dc5c3d442fc3b47fd89b0600f", "\n", MODIFICHE, False),
 "logs/eccezioni_rilascio.json":      ("abe6c63d5fe7c58a7472ba2e1b16710088e558b330be26d2ae428c84315522f3", "fd571c50004fa2746ff8fd58f9dca6a287744b5b3a3b174b195cf10cb2e12fcd", "\n", ECCEZIONI, True),
 "papers/paper2/paper2_stato.md":     ("eadb4efcd92de81eb671ba43c892a11a23740e55330deeabcbf8d2403faa14e3", "9d5014c43f58c00277c2845bb1536a80070b9cd7a87052459c2914b69315f40e", "\r\n", STATO, False),
}

BOM = b"\xef\xbb\xbf"
def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def serializza(d): return (json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

def misura_eol(raw: bytes) -> str:
    crlf, lf = raw.count(b"\r\n"), raw.count(b"\n")
    if crlf and crlf == lf: return "\r\n"
    if not crlf and b"\r" not in raw: return "\n"
    raise ValueError(f"fine riga misti: {crlf} CRLF su {lf} LF")

def trasforma(raw: bytes, eol: str, sost: list, inversa=False, is_json=False) -> bytes:
    bom = raw.startswith(BOM)
    if misura_eol(raw) != eol: raise ValueError(f"fine riga misurata diversa da {eol!r}")
    if is_json and serializza(json.loads(raw.decode("utf-8"))) != raw: raise ValueError("JSON: formato non riprodotto")
    t = raw[len(BOM) if bom else 0:].decode("utf-8")
    passi = [(b, a) for a, b in reversed(sost)] if inversa else sost
    for i, (a, b) in enumerate(passi):
        a2, b2 = a.replace("\n", eol), b.replace("\n", eol)
        k = t.count(a2)
        if k != 1: raise ValueError(f"sostituzione {i}: {k} occorrenze di «{a[:50]}»")
        t = t.replace(a2, b2)
    out = (BOM if bom else b"") + t.encode("utf-8")
    if is_json and serializza(json.loads(out.decode("utf-8"))) != out: raise ValueError("JSON: il risultato non si riserializza uguale")
    return out

def precondizioni() -> list:
    err = []
    for rel, (s, n) in PRECONDIZIONI.items():
        p = ROOT / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        raw = p.read_bytes()
        if sha(raw) != s or len(raw) != n: err.append(f"diverso dall'atteso: {rel}")
    righe = [l for l in (ROOT / "src/paper2_v1_amendments.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if DIGEST_RECORD_70 not in righe[69]: err.append("record 70: non porta il digest del 16 set di modifiche_paper1.md")
    c = [json.loads(l) for l in CENSIMENTO_77C.read_text(encoding="utf-8").splitlines() if l.strip()][-1] if CENSIMENTO_77C.exists() else {}
    if c.get("esito") != 0 or c.get("percorsi_distinti") != 152 or c.get("conteggi", {}).get("escluso_con_eccezione") != 19:
        err.append("censimento del rilascio 77c: non e' PULITO su 152 percorsi con 19 esclusi con eccezione")
    r = subprocess.run(["git", "merge-base", "--is-ancestor", COMMIT, "HEAD"], cwd=ROOT)
    if r.returncode != 0: err.append(f"git: {COMMIT} non e' antenato di HEAD")
    return err

def prepara() -> dict:
    piano, err = {}, []
    for rel, (prima, dopo, eol, sost, js) in FILE.items():
        p = ROOT / rel
        if not p.exists(): err.append(f"assente: {rel}"); continue
        raw = p.read_bytes(); s = sha(raw)
        if s == dopo: piano[rel] = None; continue
        if s != prima: err.append(f"{rel}: sha {s[:12]}..., ne' prima ne' dopo"); continue
        try:
            nuovo = trasforma(raw, eol, sost, is_json=js)
            if sha(nuovo) != dopo: err.append(f"{rel}: risultato {sha(nuovo)[:12]}..., atteso {dopo[:12]}..."); continue
            if sha(trasforma(nuovo, eol, sost, inversa=True, is_json=js)) != prima: err.append(f"{rel}: l'inversa non ridà il file"); continue
        except ValueError as e:
            err.append(f"{rel}: {e}"); continue
        piano[rel] = (raw, nuovo)
    if err:
        print("STOP:"); [print("  -", e) for e in err]; raise SystemExit(1)
    return piano

def dry_run(scrivi=False):
    err = precondizioni()
    if err:
        print("STOP, precondizioni:"); [print("  -", e) for e in err]; raise SystemExit(1)
    piano = prepara()
    for rel, v in piano.items():
        if v is None: print(f"{rel}: gia' all'ancora «dopo», non si tocca"); continue
        raw, nuovo = v
        print(f"{rel}: {sha(raw)[:12]}... {len(raw)} B -> {sha(nuovo)[:12]}... {len(nuovo)} B, {len(FILE[rel][3])} sostituzioni, inversa OK")
    if not scrivi: print("[dry-run] niente scritto."); return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for rel, v in piano.items():
        if v is None: continue
        raw, nuovo = v; p = ROOT / rel
        (LOGS / f"{p.name}.bak_{ts}").write_bytes(raw)
        tmp = p.with_name(p.name + ".tmp"); tmp.write_bytes(nuovo); os.replace(tmp, p)
        if sha(p.read_bytes()) != FILE[rel][1]: raise SystemExit(f"STOP: {rel} riletto non coincide")
        print(f"[apply] {rel}: scritto e riletto; backup logs\\{p.name}.bak_{ts}")

def verify():
    ok = True
    for rel, (prima, dopo, _, _, _) in FILE.items():
        s = sha((ROOT / rel).read_bytes())
        st = "dopo" if s == dopo else ("prima" if s == prima else "ALTRO")
        ok &= st == "dopo"; print(f"{rel}: {st} ({s[:12]}...)")
    print("verify", "OK" if ok else "ANOMALIA"); sys.exit(0 if ok else 1)

def selftest():
    ok = 0
    lf = "a\nuno X due\nb\n".encode(); crlf = lf.replace(b"\n", b"\r\n"); s = [("uno X", "uno Y\nriga nuova")]
    assert trasforma(lf, "\n", s) == b"a\nuno Y\nriga nuova due\nb\n"; ok += 1
    assert trasforma(crlf, "\r\n", s) == b"a\r\nuno Y\r\nriga nuova due\r\nb\r\n"; ok += 1
    assert trasforma(trasforma(crlf, "\r\n", s), "\r\n", s, inversa=True) == crlf; ok += 1
    for doppio in (b"X X\n", b"niente\n"):
        try: trasforma(doppio, "\n", [("X", "Y")]); raise AssertionError
        except ValueError: pass
    ok += 1
    j = serializza({"k": "testo e' vecchio"})
    assert trasforma(j, "\n", [("e' vecchio", "e' nuovo \u2014 «ok»")], is_json=True) == serializza({"k": "testo e' nuovo \u2014 «ok»"}); ok += 1
    try: trasforma(j, "\n", [("vecchio", 'rotto"')], is_json=True); raise AssertionError
    except (ValueError, json.JSONDecodeError): pass
    ok += 1
    for rel, (prima, dopo, eol, sost, js) in FILE.items():
        assert len(prima) == 64 and len(dopo) == 64 and prima != dopo and all(a != b and "\r" not in a + b for a, b in sost)
        if js: assert all('"' not in b and "\\" not in b for _, b in sost)
    ok += 1
    assert DIGEST_RECORD_70 in ECCEZIONI[0][0] and DIGEST_RECORD_70 in ECCEZIONI[0][1]; ok += 1
    print(f"selftest: {ok}/8 OK")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "dry-run", "apply", "verify"])
    {"selftest": selftest, "dry-run": lambda: dry_run(False), "apply": lambda: dry_run(True), "verify": verify}[ap.parse_args().cmd]()
